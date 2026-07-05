"""Local PDF intake primitives for the Linux/Web MVP.

This module intentionally stops at file and metadata registration. It does
not discover PDFs, judge target fiscal years, write Excel, or hand records to
the extraction review workflow.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import zipfile
from collections.abc import Callable, Iterable
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from enum import StrEnum
from importlib import import_module
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from uuid import uuid4

from eidp.config import MAX_SUPPORTED_TARGET_FISCAL_YEAR, MIN_SUPPORTED_TARGET_FISCAL_YEAR


class PdfIntakeValidationError(ValueError):
    """Raised when intake metadata or uploaded bytes fail validation."""

    def __init__(self, errors: Iterable[str]) -> None:
        self.errors = tuple(errors)
        super().__init__("; ".join(self.errors))


class IntakeSource(StrEnum):
    PDF_UPLOAD = "pdf_upload"
    ZIP_UPLOAD = "zip_upload"
    URL_CSV = "url_csv"


class PdfKind(StrEnum):
    TEXT = "text_pdf"
    IMAGE = "image_pdf"
    UNKNOWN = "unknown_pdf"


class IntakeLane(StrEnum):
    TEXT_MAIN = "text_pdf_main"
    MANUAL_OCR = "exception_manual_ocr"
    MANUAL_REVIEW = "exception_manual_review"
    URL_REGISTERED = "url_registered"


PdfKindDetector = Callable[[bytes], PdfKind]

URL_CSV_REQUIRED_COLUMNS: tuple[str, ...] = (
    "school_name",
    "fiscal_year",
    "source_page_url",
    "pdf_url",
)


@dataclass(frozen=True)
class PdfIntakeMetadata:
    school_name: str
    fiscal_year: int
    source_page_url: str
    school_id: str | None = None
    pdf_url: str | None = None
    uploaded_filename: str | None = None


@dataclass(frozen=True)
class PdfIntakeRecord:
    record_id: str
    source_type: IntakeSource
    school_name: str
    fiscal_year: int
    source_page_url: str
    school_id: str | None
    pdf_url: str | None
    original_filename: str | None
    stored_path: str | None
    sha256: str | None
    byte_size: int | None
    pdf_kind: PdfKind | None
    lane: IntakeLane
    created_at_utc: str


def clean_optional_text(value: str | None) -> str | None:
    text = (value or "").strip()
    return text or None


def compute_sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def parse_fiscal_year(value: int | str) -> int:
    if isinstance(value, bool):
        raise PdfIntakeValidationError(("fiscal_year must be a western-year integer",))
    if isinstance(value, int):
        fiscal_year = value
    else:
        text = value.strip()
        if not text.isdigit():
            raise PdfIntakeValidationError(("fiscal_year must be a western-year integer",))
        fiscal_year = int(text)
    if fiscal_year < MIN_SUPPORTED_TARGET_FISCAL_YEAR or fiscal_year > MAX_SUPPORTED_TARGET_FISCAL_YEAR:
        raise PdfIntakeValidationError(
            (
                "fiscal_year must be within "
                f"[{MIN_SUPPORTED_TARGET_FISCAL_YEAR}, {MAX_SUPPORTED_TARGET_FISCAL_YEAR}]",
            )
        )
    return fiscal_year


def _is_http_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def validate_intake_metadata(
    *,
    school_name: str,
    fiscal_year: int | str,
    source_page_url: str,
    school_id: str | None = None,
    pdf_url: str | None = None,
    uploaded_filename: str | None = None,
) -> PdfIntakeMetadata:
    errors: list[str] = []
    normalized_school_name = school_name.strip()
    normalized_source_page_url = source_page_url.strip()
    normalized_school_id = clean_optional_text(school_id)
    normalized_pdf_url = clean_optional_text(pdf_url)
    normalized_uploaded_filename = clean_optional_text(uploaded_filename)

    if not normalized_school_name:
        errors.append("school_name is required")
    try:
        normalized_fiscal_year = parse_fiscal_year(fiscal_year)
    except PdfIntakeValidationError as exc:
        errors.extend(exc.errors)
        normalized_fiscal_year = MIN_SUPPORTED_TARGET_FISCAL_YEAR
    if not normalized_source_page_url:
        errors.append("source_page_url is required")
    elif not _is_http_url(normalized_source_page_url):
        errors.append("source_page_url must be an http(s) URL")
    if normalized_pdf_url is not None and not _is_http_url(normalized_pdf_url):
        errors.append("pdf_url must be an http(s) URL when provided")
    if normalized_pdf_url is None and normalized_uploaded_filename is None:
        errors.append("pdf_url or uploaded filename is required")
    if errors:
        raise PdfIntakeValidationError(errors)

    return PdfIntakeMetadata(
        school_name=normalized_school_name,
        school_id=normalized_school_id,
        fiscal_year=normalized_fiscal_year,
        source_page_url=normalized_source_page_url,
        pdf_url=normalized_pdf_url,
        uploaded_filename=normalized_uploaded_filename,
    )


def detect_pdf_kind(pdf_bytes: bytes, *, max_pages: int = 3) -> PdfKind:
    """Classify a PDF as text-bearing or image-only using pdfplumber.

    A PDF with extractable text on any sampled page is considered the main
    text-PDF path. Empty or image-only pages go to the manual/OCR lane.
    """
    _require_pdf_magic(pdf_bytes)
    pdfplumber: Any = import_module("pdfplumber")
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        pages: list[Any] = list(pdf.pages[:max_pages])
        if not pages:
            return PdfKind.IMAGE
        for page in pages:
            text = page.extract_text() or ""
            if text.strip():
                return PdfKind.TEXT
    return PdfKind.IMAGE


def lane_for_pdf_kind(pdf_kind: PdfKind | None) -> IntakeLane:
    if pdf_kind == PdfKind.TEXT:
        return IntakeLane.TEXT_MAIN
    if pdf_kind == PdfKind.IMAGE:
        return IntakeLane.MANUAL_OCR
    return IntakeLane.MANUAL_REVIEW


def store_pdf_upload(
    *,
    metadata: PdfIntakeMetadata,
    pdf_bytes: bytes,
    intake_root: Path,
    source_type: IntakeSource = IntakeSource.PDF_UPLOAD,
    detect_pdf_kind_func: PdfKindDetector | None = None,
) -> PdfIntakeRecord:
    _require_pdf_magic(pdf_bytes)
    detector = detect_pdf_kind_func or detect_pdf_kind
    sha256 = compute_sha256(pdf_bytes)
    original_filename = metadata.uploaded_filename or "uploaded.pdf"
    relative_path = _pdf_storage_relative_path(
        fiscal_year=metadata.fiscal_year,
        sha256=sha256,
        filename=original_filename,
    )
    root = Path(intake_root)
    stored_path = root / relative_path
    _write_bytes_atomic(stored_path, pdf_bytes)

    try:
        pdf_kind = detector(pdf_bytes)
    except Exception:
        pdf_kind = PdfKind.UNKNOWN

    record = PdfIntakeRecord(
        record_id=uuid4().hex,
        source_type=source_type,
        school_name=metadata.school_name,
        school_id=metadata.school_id,
        fiscal_year=metadata.fiscal_year,
        source_page_url=metadata.source_page_url,
        pdf_url=metadata.pdf_url,
        original_filename=original_filename,
        stored_path=relative_path.as_posix(),
        sha256=sha256,
        byte_size=len(pdf_bytes),
        pdf_kind=pdf_kind,
        lane=lane_for_pdf_kind(pdf_kind),
        created_at_utc=_utc_now_iso(),
    )
    _write_record(root, record)
    return record


def store_zip_upload(
    *,
    metadata: PdfIntakeMetadata,
    zip_bytes: bytes,
    intake_root: Path,
    detect_pdf_kind_func: PdfKindDetector | None = None,
) -> list[PdfIntakeRecord]:
    try:
        archive = zipfile.ZipFile(io.BytesIO(zip_bytes))
    except zipfile.BadZipFile as exc:
        raise PdfIntakeValidationError(("uploaded ZIP is not readable",)) from exc

    records: list[PdfIntakeRecord] = []
    with archive:
        for info in archive.infolist():
            if info.is_dir() or not info.filename.lower().endswith(".pdf"):
                continue
            pdf_bytes = archive.read(info)
            item_metadata = replace(metadata, uploaded_filename=info.filename)
            records.append(
                store_pdf_upload(
                    metadata=item_metadata,
                    pdf_bytes=pdf_bytes,
                    intake_root=intake_root,
                    source_type=IntakeSource.ZIP_UPLOAD,
                    detect_pdf_kind_func=detect_pdf_kind_func,
                )
            )
    if not records:
        raise PdfIntakeValidationError(("ZIP contains no PDF files",))
    return records


def parse_url_csv(csv_bytes: bytes) -> list[PdfIntakeMetadata]:
    try:
        text = csv_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise PdfIntakeValidationError(("URL CSV must be UTF-8 or UTF-8-SIG encoded",)) from exc

    reader = csv.DictReader(io.StringIO(text))
    fieldnames = tuple(reader.fieldnames or ())
    missing = [column for column in URL_CSV_REQUIRED_COLUMNS if column not in fieldnames]
    if missing:
        raise PdfIntakeValidationError((f"URL CSV missing required columns: {', '.join(missing)}",))

    rows: list[PdfIntakeMetadata] = []
    errors: list[str] = []
    for row_number, row in enumerate(reader, start=2):
        if _is_blank_csv_row(row.values()):
            continue
        try:
            rows.append(
                validate_intake_metadata(
                    school_name=_csv_value(row, "school_name"),
                    school_id=_csv_value(row, "school_id"),
                    fiscal_year=_csv_value(row, "fiscal_year"),
                    source_page_url=_csv_value(row, "source_page_url"),
                    pdf_url=_csv_value(row, "pdf_url"),
                )
            )
        except PdfIntakeValidationError as exc:
            errors.extend(f"row {row_number}: {error}" for error in exc.errors)
    if errors:
        raise PdfIntakeValidationError(errors)
    return rows


def register_url_csv(*, csv_bytes: bytes, intake_root: Path) -> list[PdfIntakeRecord]:
    metadata_rows = parse_url_csv(csv_bytes)
    records: list[PdfIntakeRecord] = []
    root = Path(intake_root)
    for metadata in metadata_rows:
        record = PdfIntakeRecord(
            record_id=uuid4().hex,
            source_type=IntakeSource.URL_CSV,
            school_name=metadata.school_name,
            school_id=metadata.school_id,
            fiscal_year=metadata.fiscal_year,
            source_page_url=metadata.source_page_url,
            pdf_url=metadata.pdf_url,
            original_filename=None,
            stored_path=None,
            sha256=None,
            byte_size=None,
            pdf_kind=None,
            lane=IntakeLane.URL_REGISTERED,
            created_at_utc=_utc_now_iso(),
        )
        _write_record(root, record)
        records.append(record)
    return records


def load_intake_queue(intake_root: Path) -> list[PdfIntakeRecord]:
    records_dir = Path(intake_root) / "records"
    if not records_dir.exists():
        return []
    records: list[PdfIntakeRecord] = []
    for path in records_dir.glob("*.json"):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            records.append(_record_from_mapping(payload))
        except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError):
            continue
    records.sort(key=lambda record: record.created_at_utc, reverse=True)
    return records


def _record_to_dict(record: PdfIntakeRecord) -> dict[str, object]:
    return {
        "record_id": record.record_id,
        "source_type": record.source_type.value,
        "school_name": record.school_name,
        "school_id": record.school_id,
        "fiscal_year": record.fiscal_year,
        "source_page_url": record.source_page_url,
        "pdf_url": record.pdf_url,
        "original_filename": record.original_filename,
        "stored_path": record.stored_path,
        "sha256": record.sha256,
        "byte_size": record.byte_size,
        "pdf_kind": record.pdf_kind.value if record.pdf_kind is not None else None,
        "lane": record.lane.value,
        "created_at_utc": record.created_at_utc,
    }


def _record_from_mapping(payload: dict[str, object]) -> PdfIntakeRecord:
    pdf_kind_value = _optional_str(payload.get("pdf_kind"))
    return PdfIntakeRecord(
        record_id=_required_str(payload, "record_id"),
        source_type=IntakeSource(_required_str(payload, "source_type")),
        school_name=_required_str(payload, "school_name"),
        school_id=_optional_str(payload.get("school_id")),
        fiscal_year=_required_int(payload, "fiscal_year"),
        source_page_url=_required_str(payload, "source_page_url"),
        pdf_url=_optional_str(payload.get("pdf_url")),
        original_filename=_optional_str(payload.get("original_filename")),
        stored_path=_optional_str(payload.get("stored_path")),
        sha256=_optional_str(payload.get("sha256")),
        byte_size=_optional_int(payload.get("byte_size")),
        pdf_kind=PdfKind(pdf_kind_value) if pdf_kind_value is not None else None,
        lane=IntakeLane(_required_str(payload, "lane")),
        created_at_utc=_required_str(payload, "created_at_utc"),
    )


def _require_pdf_magic(pdf_bytes: bytes) -> None:
    if not pdf_bytes.lstrip().startswith(b"%PDF"):
        raise PdfIntakeValidationError(("uploaded file is not a PDF",))


def _pdf_storage_relative_path(*, fiscal_year: int, sha256: str, filename: str) -> Path:
    safe_name = _safe_filename(filename)
    return Path("files") / str(fiscal_year) / f"{sha256[:12]}-{safe_name}"


def _safe_filename(filename: str) -> str:
    name = Path(filename.replace("\\", "/")).name.strip()
    if not name:
        name = "uploaded.pdf"
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._-")
    if not cleaned:
        cleaned = "uploaded.pdf"
    if not cleaned.lower().endswith(".pdf"):
        cleaned = f"{cleaned}.pdf"
    return cleaned


def _write_bytes_atomic(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    tmp.write_bytes(payload)
    tmp.replace(path)


def _write_record(intake_root: Path, record: PdfIntakeRecord) -> None:
    records_dir = intake_root / "records"
    records_dir.mkdir(parents=True, exist_ok=True)
    target = records_dir / f"{record.record_id}.json"
    tmp = target.with_name(f".{target.name}.{uuid4().hex}.tmp")
    tmp.write_text(
        json.dumps(_record_to_dict(record), ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    tmp.replace(target)


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _csv_value(row: dict[str, str | None], key: str) -> str:
    return row.get(key) or ""


def _is_blank_csv_row(values: Iterable[str | None]) -> bool:
    return all((value or "").strip() == "" for value in values)


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


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("value must be an integer or null")
    return value
