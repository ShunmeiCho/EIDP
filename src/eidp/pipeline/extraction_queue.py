"""Local extraction queue bridge for Linux/Web PDF intake.

This slice connects already-registered intake metadata to a local extraction
queue. It intentionally does not implement review UI, Copilot/NotebookLM
import, final Excel export, background scheduling, or production deployment.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from uuid import uuid4

from eidp.pdf.table_grid_extractor import CellEvidence, TableDepartmentRecord, extract_table_grid_records
from eidp.pipeline.pdf_intake import IntakeLane, PdfIntakeRecord, load_intake_queue


class ExtractionQueueType(StrEnum):
    TEXT_EXTRACTION = "text_extraction"
    MANUAL_OCR_EXCEPTION = "manual_ocr_exception"
    NOT_APPLICABLE = "not_applicable"


class ExtractionStatus(StrEnum):
    NOT_APPLICABLE = "not_applicable"
    PENDING_EXTRACTION = "pending_extraction"
    EXTRACTING = "extracting"
    EXTRACTION_COMPLETED = "extraction_completed"
    NEEDS_REVIEW = "needs_review"
    EXTRACTION_FAILED = "extraction_failed"


class NextAction(StrEnum):
    RUN_EXTRACTION = "run_extraction"
    REVIEW_EXTRACTED_ROWS = "review_extracted_rows"
    UPLOAD_OCR_TEXT_PDF = "upload_ocr_text_pdf"
    MANUAL_ENTRY = "manual_entry"
    EXCLUDE_FROM_CURRENT_EXPORT = "exclude_from_current_export"


ExtractorFunc = Callable[[Path], list[TableDepartmentRecord]]


@dataclass(frozen=True)
class ExtractionQueueItem:
    intake_record_id: str
    queue_type: ExtractionQueueType
    status: ExtractionStatus
    next_action: NextAction | None
    school_name: str
    school_id: str | None
    fiscal_year: int
    source_page_url: str
    pdf_path: str | None
    sha256: str | None
    pdf_url: str | None
    error_reason: str | None
    rows_written: int
    created_at_utc: str
    updated_at_utc: str


@dataclass(frozen=True)
class ExtractedMetricRow:
    intake_record_id: str
    school_name: str
    school_id: str | None
    fiscal_year: int
    source_page_url: str
    pdf_path: str
    sha256: str
    field_category: str
    course_name: str
    department_name: str
    metric: str
    value: int
    page_no: int
    table_index: int
    row_index: int
    col_index: int
    raw_label: str
    raw_value: str


def ensure_extraction_queue(intake_root: Path) -> list[ExtractionQueueItem]:
    """Create missing local queue items for current intake records."""
    root = Path(intake_root)
    existing = {item.intake_record_id: item for item in load_extraction_queue(root)}
    for record in load_intake_queue(root):
        if record.record_id in existing:
            continue
        item = _queue_item_for_record(record)
        _write_queue_item(root, item)
        existing[item.intake_record_id] = item
    items = list(existing.values())
    items.sort(key=lambda item: item.created_at_utc, reverse=True)
    return items


def load_extraction_queue(intake_root: Path) -> list[ExtractionQueueItem]:
    jobs_dir = _jobs_dir(Path(intake_root))
    if not jobs_dir.exists():
        return []
    items: list[ExtractionQueueItem] = []
    for path in jobs_dir.glob("*.json"):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            items.append(_queue_item_from_mapping(payload))
        except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError):
            continue
    items.sort(key=lambda item: item.created_at_utc, reverse=True)
    return items


def process_intake_record(
    *,
    intake_root: Path,
    intake_record_id: str,
    extractor_func: ExtractorFunc = extract_table_grid_records,
) -> ExtractionQueueItem:
    """Process one intake record by id when it is a pending text-PDF job."""
    root = Path(intake_root)
    items = {item.intake_record_id: item for item in ensure_extraction_queue(root)}
    item = items.get(intake_record_id)
    if item is None:
        raise KeyError(f"intake record {intake_record_id!r} not found")
    if item.queue_type != ExtractionQueueType.TEXT_EXTRACTION:
        return item
    if item.status not in {ExtractionStatus.PENDING_EXTRACTION, ExtractionStatus.EXTRACTION_FAILED}:
        return item
    if item.pdf_path is None:
        failed = _update_item(
            item,
            status=ExtractionStatus.EXTRACTION_FAILED,
            next_action=NextAction.RUN_EXTRACTION,
            error_reason="missing pdf_path",
        )
        _write_queue_item(root, failed)
        return failed

    extracting = _update_item(
        item,
        status=ExtractionStatus.EXTRACTING,
        next_action=None,
        error_reason=None,
        rows_written=0,
    )
    _write_queue_item(root, extracting)
    try:
        pdf_path = root / item.pdf_path
        extracted_records = extractor_func(pdf_path)
        rows = normalize_extracted_rows(extracting, extracted_records)
        _write_extracted_rows(root, intake_record_id, rows)
        status = _status_for_extracted_records(extracted_records, rows)
        completed = _update_item(
            extracting,
            status=status,
            next_action=NextAction.REVIEW_EXTRACTED_ROWS,
            rows_written=len(rows),
        )
        _write_queue_item(root, completed)
        return completed
    except Exception as exc:
        failed = _update_item(
            extracting,
            status=ExtractionStatus.EXTRACTION_FAILED,
            next_action=NextAction.RUN_EXTRACTION,
            error_reason=str(exc)[:500],
        )
        _write_queue_item(root, failed)
        return failed


def process_pending_text_pdf_records(
    *,
    intake_root: Path,
    extractor_func: ExtractorFunc = extract_table_grid_records,
) -> list[ExtractionQueueItem]:
    results: list[ExtractionQueueItem] = []
    for item in ensure_extraction_queue(intake_root):
        if item.queue_type != ExtractionQueueType.TEXT_EXTRACTION:
            continue
        if item.status != ExtractionStatus.PENDING_EXTRACTION:
            continue
        results.append(
            process_intake_record(
                intake_root=intake_root,
                intake_record_id=item.intake_record_id,
                extractor_func=extractor_func,
            )
        )
    return results


def load_extracted_rows(intake_root: Path, intake_record_id: str) -> list[ExtractedMetricRow]:
    path = _results_dir(Path(intake_root)) / f"{intake_record_id}.json"
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        return []
    rows: list[ExtractedMetricRow] = []
    for row in payload:
        if isinstance(row, dict):
            rows.append(_extracted_row_from_mapping(row))
    return rows


def normalize_extracted_rows(
    item: ExtractionQueueItem,
    records: list[TableDepartmentRecord],
) -> list[ExtractedMetricRow]:
    if item.pdf_path is None or item.sha256 is None:
        return []
    rows: list[ExtractedMetricRow] = []
    for record in records:
        evidence_by_metric = {evidence.canonical_metric: evidence for evidence in record.evidence}
        for metric in ("capacity", "enrollment", "intl_students"):
            value = getattr(record, metric)
            evidence = evidence_by_metric.get(metric)
            if value is None or evidence is None:
                continue
            rows.append(_metric_row_from_evidence(item, record, metric, value, evidence))
    return rows


def extraction_status_label(item: ExtractionQueueItem | None) -> str:
    if item is None:
        return "未キュー"
    if item.queue_type == ExtractionQueueType.MANUAL_OCR_EXCEPTION:
        return "画像PDF: OCR済みPDFアップロード or 手入力"
    labels = {
        ExtractionStatus.NOT_APPLICABLE: "対象外",
        ExtractionStatus.PENDING_EXTRACTION: "抽出待ち",
        ExtractionStatus.EXTRACTING: "抽出中",
        ExtractionStatus.EXTRACTION_COMPLETED: "抽出済み",
        ExtractionStatus.NEEDS_REVIEW: "要確認",
        ExtractionStatus.EXTRACTION_FAILED: "失敗",
    }
    return labels[item.status]


def _queue_item_for_record(record: PdfIntakeRecord) -> ExtractionQueueItem:
    now = _utc_now_iso()
    if record.lane == IntakeLane.TEXT_MAIN and record.stored_path is not None:
        queue_type = ExtractionQueueType.TEXT_EXTRACTION
        status = ExtractionStatus.PENDING_EXTRACTION
        next_action: NextAction | None = NextAction.RUN_EXTRACTION
    elif record.lane == IntakeLane.MANUAL_OCR:
        queue_type = ExtractionQueueType.MANUAL_OCR_EXCEPTION
        status = ExtractionStatus.NOT_APPLICABLE
        next_action = NextAction.UPLOAD_OCR_TEXT_PDF
    else:
        queue_type = ExtractionQueueType.NOT_APPLICABLE
        status = ExtractionStatus.NOT_APPLICABLE
        next_action = None
    return ExtractionQueueItem(
        intake_record_id=record.record_id,
        queue_type=queue_type,
        status=status,
        next_action=next_action,
        school_name=record.school_name,
        school_id=record.school_id,
        fiscal_year=record.fiscal_year,
        source_page_url=record.source_page_url,
        pdf_path=record.stored_path,
        sha256=record.sha256,
        pdf_url=record.pdf_url,
        error_reason=None,
        rows_written=0,
        created_at_utc=now,
        updated_at_utc=now,
    )


def _status_for_extracted_records(
    records: list[TableDepartmentRecord],
    rows: list[ExtractedMetricRow],
) -> ExtractionStatus:
    if not records or not rows:
        return ExtractionStatus.NEEDS_REVIEW
    for record in records:
        if record.capacity is None or record.enrollment is None:
            return ExtractionStatus.NEEDS_REVIEW
    return ExtractionStatus.EXTRACTION_COMPLETED


def _metric_row_from_evidence(
    item: ExtractionQueueItem,
    record: TableDepartmentRecord,
    metric: str,
    value: int,
    evidence: CellEvidence,
) -> ExtractedMetricRow:
    if item.pdf_path is None or item.sha256 is None:
        raise ValueError("pdf_path and sha256 are required for extracted rows")
    return ExtractedMetricRow(
        intake_record_id=item.intake_record_id,
        school_name=item.school_name,
        school_id=item.school_id,
        fiscal_year=item.fiscal_year,
        source_page_url=item.source_page_url,
        pdf_path=item.pdf_path,
        sha256=item.sha256,
        field_category=record.field_category,
        course_name=record.course_name,
        department_name=record.department_name,
        metric=metric,
        value=value,
        page_no=evidence.page_no,
        table_index=evidence.table_index,
        row_index=evidence.row_index,
        col_index=evidence.col_index,
        raw_label=evidence.raw_label,
        raw_value=evidence.raw_value,
    )


def _update_item(
    item: ExtractionQueueItem,
    *,
    status: ExtractionStatus,
    next_action: NextAction | None,
    error_reason: str | None = None,
    rows_written: int | None = None,
) -> ExtractionQueueItem:
    return replace(
        item,
        status=status,
        next_action=next_action,
        error_reason=error_reason,
        rows_written=item.rows_written if rows_written is None else rows_written,
        updated_at_utc=_utc_now_iso(),
    )


def _write_queue_item(intake_root: Path, item: ExtractionQueueItem) -> None:
    jobs_dir = _jobs_dir(intake_root)
    jobs_dir.mkdir(parents=True, exist_ok=True)
    target = jobs_dir / f"{item.intake_record_id}.json"
    _write_json_atomic(target, _queue_item_to_dict(item))


def _write_extracted_rows(intake_root: Path, intake_record_id: str, rows: list[ExtractedMetricRow]) -> None:
    results_dir = _results_dir(intake_root)
    results_dir.mkdir(parents=True, exist_ok=True)
    _write_json_atomic(results_dir / f"{intake_record_id}.json", [_extracted_row_to_dict(row) for row in rows])


def _write_json_atomic(path: Path, payload: object) -> None:
    tmp = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _jobs_dir(intake_root: Path) -> Path:
    return intake_root / "extraction" / "jobs"


def _results_dir(intake_root: Path) -> Path:
    return intake_root / "extraction" / "results"


def _queue_item_to_dict(item: ExtractionQueueItem) -> dict[str, object]:
    return {
        "intake_record_id": item.intake_record_id,
        "queue_type": item.queue_type.value,
        "status": item.status.value,
        "next_action": item.next_action.value if item.next_action is not None else None,
        "school_name": item.school_name,
        "school_id": item.school_id,
        "fiscal_year": item.fiscal_year,
        "source_page_url": item.source_page_url,
        "pdf_path": item.pdf_path,
        "sha256": item.sha256,
        "pdf_url": item.pdf_url,
        "error_reason": item.error_reason,
        "rows_written": item.rows_written,
        "created_at_utc": item.created_at_utc,
        "updated_at_utc": item.updated_at_utc,
    }


def _queue_item_from_mapping(payload: dict[str, object]) -> ExtractionQueueItem:
    next_action = _optional_str(payload.get("next_action"))
    return ExtractionQueueItem(
        intake_record_id=_required_str(payload, "intake_record_id"),
        queue_type=ExtractionQueueType(_required_str(payload, "queue_type")),
        status=ExtractionStatus(_required_str(payload, "status")),
        next_action=NextAction(next_action) if next_action is not None else None,
        school_name=_required_str(payload, "school_name"),
        school_id=_optional_str(payload.get("school_id")),
        fiscal_year=_required_int(payload, "fiscal_year"),
        source_page_url=_required_str(payload, "source_page_url"),
        pdf_path=_optional_str(payload.get("pdf_path")),
        sha256=_optional_str(payload.get("sha256")),
        pdf_url=_optional_str(payload.get("pdf_url")),
        error_reason=_optional_str(payload.get("error_reason")),
        rows_written=_required_int(payload, "rows_written"),
        created_at_utc=_required_str(payload, "created_at_utc"),
        updated_at_utc=_required_str(payload, "updated_at_utc"),
    )


def _extracted_row_to_dict(row: ExtractedMetricRow) -> dict[str, object]:
    return {
        "intake_record_id": row.intake_record_id,
        "school_name": row.school_name,
        "school_id": row.school_id,
        "fiscal_year": row.fiscal_year,
        "source_page_url": row.source_page_url,
        "pdf_path": row.pdf_path,
        "sha256": row.sha256,
        "field_category": row.field_category,
        "course_name": row.course_name,
        "department_name": row.department_name,
        "metric": row.metric,
        "value": row.value,
        "page_no": row.page_no,
        "table_index": row.table_index,
        "row_index": row.row_index,
        "col_index": row.col_index,
        "raw_label": row.raw_label,
        "raw_value": row.raw_value,
    }


def _extracted_row_from_mapping(payload: dict[str, object]) -> ExtractedMetricRow:
    return ExtractedMetricRow(
        intake_record_id=_required_str(payload, "intake_record_id"),
        school_name=_required_str(payload, "school_name"),
        school_id=_optional_str(payload.get("school_id")),
        fiscal_year=_required_int(payload, "fiscal_year"),
        source_page_url=_required_str(payload, "source_page_url"),
        pdf_path=_required_str(payload, "pdf_path"),
        sha256=_required_str(payload, "sha256"),
        field_category=_required_str(payload, "field_category"),
        course_name=_required_str(payload, "course_name"),
        department_name=_required_str(payload, "department_name"),
        metric=_required_str(payload, "metric"),
        value=_required_int(payload, "value"),
        page_no=_required_int(payload, "page_no"),
        table_index=_required_int(payload, "table_index"),
        row_index=_required_int(payload, "row_index"),
        col_index=_required_int(payload, "col_index"),
        raw_label=_required_str(payload, "raw_label"),
        raw_value=_required_str(payload, "raw_value"),
    )


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _required_str(payload: dict[str, object], key: str) -> str:
    value = payload[key]
    if not isinstance(value, str) or not value:
        raise ValueError(f"{key} must be a non-empty string")
    return value


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("value must be a string or null")
    return value


def _required_int(payload: dict[str, object], key: str) -> int:
    value = payload[key]
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{key} must be an integer")
    return value
