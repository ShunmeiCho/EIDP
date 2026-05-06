"""Streamlit page: PDF確認・手入力 (Sprint 8.4.c.1).

Business-user main battlefield. Image PDFs / parse_failed / review_pending /
school_mismatch documents land in this page; the operator views the PDF
and types numbers into a form. All saves go through
``pipeline.manual_entry.save_manual_entries`` — the page MUST NOT issue
INSERTs against ``DepartmentYearly`` directly.

Architecture
------------
The render function is a thin Streamlit shell. The testable surface
lives in pure helpers:

  * ``list_pending_documents`` — queue query.
  * ``build_pdf_preview``      — local PDF → first-page PNG + download bytes.
  * ``form_data_to_entries``   — UI dict → ``DepartmentEntry`` list,
    with validation that mirrors ``save_manual_entries`` constraints
    so the user gets feedback before we try to save.
  * ``save_with_lock``         — acquires the shared lock
    non-blocking; on lock-busy returns a status without writing.
  * ``LockBusy`` / ``SaveOk``  — return type for the save call.

Lock contract (8.4.b): UI MUST NOT block on the lock. If the weekly
runner holds it, the page surfaces a banner ("週次処理中、編集は一時停止")
and refuses the save attempt. Read-only listing is unaffected.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

from sqlalchemy.orm import Session

from eidp.db.locking import LockBusyError, acquire_lock, probe_lock
from eidp.db.models import Department, DepartmentYearly, Document, School, SupportRecipient
from eidp.extraction_confidence import ConfidenceVerdict
from eidp.pipeline.manual_entry import (
    ALLOWED_METHODS,
    DepartmentEntry,
    DeptChangeType,
    ManualEntryResult,
    save_manual_entries,
)
from eidp.review.confidence_panels import (
    ConfidencePanel,
    build_panel,
    panel_summary_line,
)
from eidp.review.school_scope import OPERATOR_SCHOOL_SCOPE_LABEL, OPERATOR_SCHOOL_TYPE_SCOPE

# Statuses we surface in the manual-entry queue. Mirrors
# ``manual_entry._QUEUED_INGEST_STATUSES`` plus ``school_mismatch`` which
# the operator can resolve here too (by reassigning to the correct
# school via override / re-ingest workflows — outside this page's scope,
# but its presence in the queue lets the operator see it).
QUEUE_STATUSES: tuple[str, ...] = (
    "ocr_pending",
    "parse_failed",
    "review_pending",
    "school_mismatch",
)
MANUAL_ENTRY_DOCUMENT_ID_STATE_KEY = "pdf_manual_entry_document_id"
MANUAL_QUEUE_VIEW_TARGET = "target_year"
MANUAL_QUEUE_VIEW_TARGET_WITH_INGESTED = "target_year_with_ingested"
MANUAL_QUEUE_VIEW_ALL = "all_documents"


@dataclass(frozen=True)
class QueueRow:
    """Minimal projection of a queued Document for table display."""

    document_id: int
    school_id: int
    school_name: str
    prefecture: str
    fiscal_year: int | None
    ingest_status: str
    file_path: str | None
    source_url: str
    discovered_from: str | None
    pdf_type: str | None
    confidence: float | None


@dataclass(frozen=True)
class DiscoveryEvidenceRow:
    """One candidate decision from output/discovery_rejections.jsonl."""

    pdf_url: str
    page_url: str
    reason: str
    anchor_text: str
    pattern_type: str
    score: float
    pdf_type: str | None
    timestamp: str


@dataclass(frozen=True)
class PdfPreview:
    """Preview payload for a local PDF attached to a queued document."""

    path: Path | None
    exists: bool
    page_index: int = 0
    page_count: int | None = None
    image_png: bytes | None = None
    pdf_bytes: bytes | None = None
    error: str | None = None

    @property
    def filename(self) -> str:
        return self.path.name if self.path else "document.pdf"


@dataclass
class ValidationError:
    field: str
    message: str


@dataclass
class FormValidation:
    entries: list[DepartmentEntry] = field(default_factory=list)
    errors: list[ValidationError] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


@dataclass
class SaveOutcome:
    """Return type from save_with_lock."""

    ok: bool
    lock_busy: bool = False
    lock_owner: str | None = None
    lock_started_at: str | None = None
    error: str | None = None
    result: ManualEntryResult | None = None


# ---------------------------------------------------------------------------
# Confidence summary
# ---------------------------------------------------------------------------


_VERDICT_RANK: dict[ConfidenceVerdict, int] = {
    "rejected": 3,
    "review_pending": 2,
    "auto_flag": 1,
    "auto": 0,
}


def _verdict_rank(verdict: ConfidenceVerdict | None) -> int:
    if verdict is None:
        return 0
    return _VERDICT_RANK.get(verdict, 0)


@dataclass(frozen=True)
class RowPanel:
    """One DY/SR row's confidence panel attached to a human-readable label."""

    kind: str  # "department" | "support_recipient"
    label: str
    is_current: bool
    panel: ConfidencePanel


@dataclass(frozen=True)
class DocConfidenceSummary:
    """Per-document aggregate of every DY+SR row's confidence panel.

    ``worst_verdict`` is the bucket with the highest priority across
    all rows. The queue line surfaces just this summary; expanding the
    row reveals every panel.
    """

    document_id: int
    rows: list[RowPanel]
    worst_verdict: ConfidenceVerdict | None
    summary_line: str


def summarize_confidence_for_document(
    session: Session, document_id: int,
) -> DocConfidenceSummary:
    """Walk every DepartmentYearly + SupportRecipient row written by
    ``document_id``, build a confidence panel for each, and return the
    aggregate. Rows without a ``confidence_breakdown`` (e.g. legacy
    pre-8.6.b data) are silently skipped — they pre-date the contract.
    """
    panels: list[RowPanel] = []

    dy_rows = (
        session.query(DepartmentYearly, Department)
        .join(Department, Department.id == DepartmentYearly.department_id)
        .filter(DepartmentYearly.document_id == document_id)
        .all()
    )
    for dy, dept in dy_rows:
        if not dy.confidence_breakdown:
            continue
        try:
            panel = build_panel(dy.confidence_breakdown)
        except Exception:
            # Bad blob shouldn't poison the whole row; skip and log
            # via the operator-visible queue rather than crashing.
            continue
        panels.append(RowPanel(
            kind="department",
            label=f"{dept.canonical_name or '(無名学科)'} fy={dy.fiscal_year}",
            is_current=bool(dy.is_current),
            panel=panel,
        ))

    sr_rows = (
        session.query(SupportRecipient)
        .filter(SupportRecipient.document_id == document_id)
        .all()
    )
    for sr in sr_rows:
        if not sr.confidence_breakdown:
            continue
        try:
            panel = build_panel(sr.confidence_breakdown)
        except Exception:
            continue
        panels.append(RowPanel(
            kind="support_recipient",
            label=f"対象比率 fy={sr.fiscal_year}",
            is_current=bool(sr.is_current),
            panel=panel,
        ))

    worst = _worst_verdict(panels)
    summary = _summary_line(panels, worst)
    return DocConfidenceSummary(
        document_id=document_id,
        rows=panels,
        worst_verdict=worst,
        summary_line=summary,
    )


def _worst_verdict(panels: list[RowPanel]) -> ConfidenceVerdict | None:
    if not panels:
        return None
    return max(
        (p.panel.verdict for p in panels),
        key=_verdict_rank,
    )


def _summary_line(panels: list[RowPanel], worst: ConfidenceVerdict | None) -> str:
    if not panels:
        return "(信頼度情報なし)"
    n_total = len(panels)
    n_review = sum(1 for p in panels if p.panel.verdict in ("review_pending", "rejected"))
    # Pick the panel with the worst verdict to render the inline line.
    target = max(panels, key=lambda p: _verdict_rank(p.panel.verdict))
    base = panel_summary_line(target.panel)
    if n_review > 0:
        return f"{base}  / 要レビュー {n_review}/{n_total}"
    return f"{base}  / 全{n_total}件"


# ---------------------------------------------------------------------------
# Queue listing
# ---------------------------------------------------------------------------


def list_pending_documents(
    session: Session,
    *,
    statuses: Iterable[str] = QUEUE_STATUSES,
    fiscal_year: int | None = None,
    include_unknown_fiscal_year: bool = False,
    document_id: int | None = None,
    limit: int = 200,
) -> list[QueueRow]:
    """Return the manual-entry queue, ordered by oldest-first.

    The page calls this on every render. Limited to 200 rows by default
    so a large parse_failed backlog doesn't kill Streamlit's rendering
    budget; the operator can drill in via filters once the basic page
    works.
    """
    query = (
        session.query(Document, School)
        .join(School, School.id == Document.school_id)
        .filter(Document.ingest_status.in_(list(statuses)))
        .order_by(Document.id.asc())
    )
    if document_id is not None:
        query = query.filter(Document.id == document_id)
    if fiscal_year is not None:
        if include_unknown_fiscal_year:
            from sqlalchemy import or_

            query = query.filter(or_(Document.fiscal_year == fiscal_year, Document.fiscal_year.is_(None)))
        else:
            query = query.filter(Document.fiscal_year == fiscal_year)
    rows = query.limit(limit).all()
    return [
        QueueRow(
            document_id=doc.id,
            school_id=school.id,
            school_name=school.school_name,
            prefecture=school.prefecture,
            fiscal_year=doc.fiscal_year,
            ingest_status=doc.ingest_status or "",
            file_path=doc.file_path,
            source_url=doc.source_url,
            discovered_from=doc.discovered_from,
            pdf_type=doc.pdf_type,
            confidence=float(doc.confidence) if doc.confidence is not None else None,
        )
        for doc, school in rows
    ]


def coerce_focus_document_id(value: object) -> int | None:
    if not isinstance(value, int | str):
        return None
    try:
        document_id = int(value)
    except ValueError:
        return None
    return document_id if document_id > 0 else None


def prioritize_queue_document(
    queue: list[QueueRow],
    *,
    document_id: int | None,
) -> list[QueueRow]:
    """Move the focused document to the top without duplicating it."""
    if document_id is None:
        return queue
    for index, row in enumerate(queue):
        if row.document_id == document_id:
            return [row, *queue[:index], *queue[index + 1:]]
    return queue


def manual_queue_view_options(target_label: str) -> dict[str, str]:
    """Return operator-facing queue labels keyed by stable view ids."""
    return {
        MANUAL_QUEUE_VIEW_TARGET: f"{target_label}の要確認だけ",
        MANUAL_QUEUE_VIEW_TARGET_WITH_INGESTED: f"{target_label}の自動採録済も含める",
        MANUAL_QUEUE_VIEW_ALL: "全年の診断表示",
    }


def list_documents_for_manual_queue_view(
    session: Session,
    *,
    view: str,
    target_fiscal_year: int,
    focus_document_id: int | None = None,
) -> list[QueueRow]:
    """Return the PDF確認 queue for the selected operator view.

    The default view intentionally hides old-year PDFs. Stale documents are
    useful diagnostics, but showing them as the normal queue makes operators
    think they must manually fix every old PDF.
    """
    if view == MANUAL_QUEUE_VIEW_TARGET_WITH_INGESTED:
        queue = list_pending_documents(
            session,
            statuses=[*QUEUE_STATUSES, "ingested"],
            fiscal_year=target_fiscal_year,
            include_unknown_fiscal_year=True,
        )
    elif view == MANUAL_QUEUE_VIEW_ALL:
        queue = list_pending_documents(session, statuses=[*QUEUE_STATUSES, "ingested"])
    else:
        queue = list_pending_documents(
            session,
            fiscal_year=target_fiscal_year,
            include_unknown_fiscal_year=True,
        )

    if focus_document_id is None:
        return queue

    queue = prioritize_queue_document(queue, document_id=focus_document_id)
    if queue and queue[0].document_id == focus_document_id:
        return queue

    focused_rows = list_pending_documents(
        session,
        statuses=[*QUEUE_STATUSES, "ingested"],
        document_id=focus_document_id,
        limit=1,
    )
    if focused_rows:
        return [focused_rows[0], *queue]
    return queue


def latest_discovery_evidence(
    *,
    app_root: Path,
    school_id: int,
    source_url: str | None = None,
    limit: int = 8,
) -> list[DiscoveryEvidenceRow]:
    """Read recent discovery evidence for a school/source URL.

    The JSONL file records both accepted and rejected candidates. This helper is
    intentionally best-effort; malformed lines are skipped so a bad log cannot
    break the operator page.
    """
    path = app_root / "output" / "discovery_rejections.jsonl"
    if limit <= 0 or not path.is_file():
        return []

    rows: list[DiscoveryEvidenceRow] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if payload.get("school_id") != school_id:
                continue
            if source_url and payload.get("reason") == "accepted_downloaded" and payload.get("pdf_url") != source_url:
                continue
            rows.append(DiscoveryEvidenceRow(
                pdf_url=str(payload.get("pdf_url") or ""),
                page_url=str(payload.get("page_url") or ""),
                reason=str(payload.get("reason") or ""),
                anchor_text=str(payload.get("anchor_text") or ""),
                pattern_type=str(payload.get("pattern_type") or ""),
                score=float(payload.get("score") or 0.0),
                pdf_type=payload.get("pdf_type"),
                timestamp=str(payload.get("timestamp") or ""),
            ))

    return list(reversed(rows[-limit:]))


# ---------------------------------------------------------------------------
# PDF preview
# ---------------------------------------------------------------------------


def resolve_pdf_path(file_path: str | None, *, app_root: Path | None = None) -> Path | None:
    """Resolve a document file_path for preview/download.

    ``Document.file_path`` is typically stored as a relative path such as
    ``data/pdfs/1/abcd.pdf``. Windows launchers set cwd to app root, but
    tests and installed wheels may not, so callers can pass ``app_root``
    explicitly. Absolute paths are returned unchanged.
    """
    if not file_path:
        return None
    path = Path(file_path)
    if path.is_absolute():
        return path
    return (app_root or Path.cwd()) / path


def build_pdf_preview(
    file_path: str | None,
    *,
    app_root: Path | None = None,
    page_index: int = 0,
    dpi: int = 144,
) -> PdfPreview:
    """Load a local PDF and render one page as PNG for the operator UI.

    The helper is deliberately self-contained and returns errors as data
    so the Streamlit shell can show a business-readable message instead
    of crashing the whole page.
    """
    path = resolve_pdf_path(file_path, app_root=app_root)
    if path is None:
        return PdfPreview(path=None, exists=False, error="PDF file path is missing")
    if not path.exists():
        return PdfPreview(path=path, exists=False, error=f"PDF file does not exist: {path}")
    if page_index < 0:
        return PdfPreview(path=path, exists=True, error=f"page_index must be >= 0; got {page_index}")

    try:
        import fitz  # PyMuPDF

        pdf_bytes = path.read_bytes()
        with fitz.open(str(path)) as doc:
            page_count = doc.page_count
            if page_count == 0:
                return PdfPreview(
                    path=path, exists=True, page_index=page_index,
                    page_count=0, pdf_bytes=pdf_bytes,
                    error="PDF has no pages",
                )
            if page_index >= page_count:
                return PdfPreview(
                    path=path, exists=True, page_index=page_index,
                    page_count=page_count, pdf_bytes=pdf_bytes,
                    error=f"page_index {page_index} out of range for {page_count} pages",
                )
            page = doc.load_page(page_index)
            scale = dpi / 72
            pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
            image_png = pix.tobytes("png")
        return PdfPreview(
            path=path, exists=True, page_index=page_index,
            page_count=page_count, image_png=image_png, pdf_bytes=pdf_bytes,
        )
    except Exception as exc:
        return PdfPreview(path=path, exists=True, page_index=page_index, error=str(exc))


# ---------------------------------------------------------------------------
# Form → DepartmentEntry conversion
# ---------------------------------------------------------------------------


def _coerce_int(value: Any, field_name: str, errors: list[ValidationError]) -> int | None:
    if value is None or value == "":
        return None
    try:
        i = int(value)
    except (TypeError, ValueError):
        errors.append(ValidationError(field=field_name, message=f"must be an integer; got {value!r}"))
        return None
    if i < 0:
        errors.append(ValidationError(field=field_name, message=f"must be non-negative; got {i}"))
        return None
    return i


def _coerce_float(value: Any, field_name: str, errors: list[ValidationError], *, lo: float, hi: float) -> float | None:
    if value is None or value == "":
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        errors.append(ValidationError(field=field_name, message=f"must be numeric; got {value!r}"))
        return None
    if not (lo <= f <= hi):
        errors.append(ValidationError(field=field_name, message=f"must be in [{lo}, {hi}]; got {f}"))
        return None
    return f


_VALID_DEPT_CHANGE = {"新設", "廃科", "名称変更", "統合", None, ""}


def form_data_to_entries(rows: list[dict[str, Any]]) -> FormValidation:
    """Convert the per-department UI form dict list to validated entries.

    Each input row is a dict with keys::

        canonical_name, course_type, course_name, duration_years,
        capacity, enrollment, intl_students, graduates,
        advanced, employed, other, prev_enrollment,
        dropouts, dropout_rate, notes,
        dept_change ('新設'/'廃科'/'名称変更'/'統合'/None),
        old_name, related_dept_id

    Returns a ``FormValidation`` carrying any validation errors so the
    page can render them inline. ``form_validation.ok`` is True iff the
    list is safe to pass to ``save_manual_entries``.
    """
    fv = FormValidation()

    for idx, row in enumerate(rows):
        prefix = f"row[{idx}]"
        canonical = (row.get("canonical_name") or "").strip()
        if not canonical:
            fv.errors.append(ValidationError(
                field=f"{prefix}.canonical_name",
                message="学科名 is required",
            ))
            continue

        dept_change_raw = row.get("dept_change") or None
        if dept_change_raw not in _VALID_DEPT_CHANGE:
            fv.errors.append(ValidationError(
                field=f"{prefix}.dept_change",
                message=f"must be one of 新設/廃科/名称変更/統合/None; got {dept_change_raw!r}",
            ))
            continue
        dept_change = cast("DeptChangeType | None", dept_change_raw)

        capacity = _coerce_int(row.get("capacity"), f"{prefix}.capacity", fv.errors)
        enrollment = _coerce_int(row.get("enrollment"), f"{prefix}.enrollment", fv.errors)
        intl_students = _coerce_int(row.get("intl_students"), f"{prefix}.intl_students", fv.errors)
        graduates = _coerce_int(row.get("graduates"), f"{prefix}.graduates", fv.errors)
        advanced = _coerce_int(row.get("advanced"), f"{prefix}.advanced", fv.errors)
        employed = _coerce_int(row.get("employed"), f"{prefix}.employed", fv.errors)
        other = _coerce_int(row.get("other"), f"{prefix}.other", fv.errors)
        prev_enrollment = _coerce_int(row.get("prev_enrollment"), f"{prefix}.prev_enrollment", fv.errors)
        dropouts = _coerce_int(row.get("dropouts"), f"{prefix}.dropouts", fv.errors)
        dropout_rate = _coerce_float(
            row.get("dropout_rate"), f"{prefix}.dropout_rate", fv.errors, lo=0.0, hi=1.0,
        )
        duration_years_raw = row.get("duration_years")
        duration_years: float | None = None
        if duration_years_raw not in (None, ""):
            try:
                duration_years = float(str(duration_years_raw))
            except (TypeError, ValueError):
                fv.errors.append(ValidationError(
                    field=f"{prefix}.duration_years",
                    message=f"must be numeric; got {duration_years_raw!r}",
                ))

        if any(e.field.startswith(prefix) for e in fv.errors):
            continue

        fv.entries.append(DepartmentEntry(
            canonical_name=canonical,
            course_type=(row.get("course_type") or "").strip() or None,
            course_name=(row.get("course_name") or "").strip() or None,
            duration_years=duration_years,
            capacity=capacity,
            enrollment=enrollment,
            intl_students=intl_students,
            graduates=graduates,
            advanced=advanced,
            employed=employed,
            other=other,
            prev_enrollment=prev_enrollment,
            dropouts=dropouts,
            dropout_rate=dropout_rate,
            notes=(row.get("notes") or "").strip() or None,
            dept_change=dept_change,
            old_name=(row.get("old_name") or "").strip() or None,
            related_dept_id=row.get("related_dept_id") or None,
        ))

    return fv


# ---------------------------------------------------------------------------
# Save with lock
# ---------------------------------------------------------------------------


def save_with_lock(
    session: Session,
    *,
    document_id: int,
    fiscal_year: int,
    entries: list[DepartmentEntry],
    method: str = "manual",
    confidence_breakdown: dict[str, Any] | None = None,
    actor: str = "operator",
    reason: str | None = None,
    lock_path: Path,
) -> SaveOutcome:
    """Acquire the shared advisory lock non-blocking, then save.

    Returns ``SaveOutcome``:
      * ``ok=True``                   — lock acquired, save committed.
      * ``lock_busy=True``            — weekly runner has the lock; the
        page renders a banner and tells the operator to retry.
      * ``ok=False, error=...``      — lock was free but the underlying
        ``save_manual_entries`` raised (e.g. invalid method, fiscal
        mismatch, negative numeric). The transaction is rolled back so
        the page can re-render with the error message.

    UI MUST NOT call ``save_manual_entries`` directly — always go
    through this wrapper so lock + commit boundaries stay aligned.
    """
    if method not in ALLOWED_METHODS:
        return SaveOutcome(ok=False, error=f"method must be one of {sorted(ALLOWED_METHODS)}; got {method!r}")

    try:
        with acquire_lock(lock_path, owner="ui_manual_entry"):
            try:
                result = save_manual_entries(
                    session,
                    document_id=document_id,
                    fiscal_year=fiscal_year,
                    entries=entries,
                    method=method,  # type: ignore[arg-type]
                    confidence_breakdown=confidence_breakdown,
                    actor=actor,
                    reason=reason,
                )
            except Exception as exc:
                session.rollback()
                return SaveOutcome(ok=False, error=str(exc))
            session.commit()
            return SaveOutcome(ok=True, result=result)
    except LockBusyError:
        status = probe_lock(lock_path)
        return SaveOutcome(
            ok=False,
            lock_busy=True,
            lock_owner=status.owner,
            lock_started_at=status.started_at,
        )


# ---------------------------------------------------------------------------
# Submit handler — tested via monkeypatch
# ---------------------------------------------------------------------------


# Statuses where the operator CAN save data here. ``school_mismatch``
# documents are listed read-only; the operator must resolve school
# binding via a separate workflow before manual data entry is safe.
SAVE_ELIGIBLE_STATUSES: frozenset[str] = frozenset({
    "ocr_pending",
    "parse_failed",
    "review_pending",
})


def submit_form(
    session: Session,
    *,
    document_id: int,
    fiscal_year: int,
    rows: list[dict[str, Any]],
    reason: str | None,
    lock_path: Path,
) -> tuple[FormValidation, SaveOutcome | None]:
    """Validate UI form rows then save through the locked pipeline.

    Returns ``(validation, outcome)``. If validation fails, outcome is
    None and the page renders the inline errors. If validation succeeds,
    outcome carries the SaveOutcome from save_with_lock.

    This is the unit-test seam: tests monkeypatch save_with_lock and
    invoke submit_form to verify the page wires through to it instead
    of writing directly.
    """
    fv = form_data_to_entries(rows)
    if not fv.ok:
        return fv, None
    if not fv.entries:
        # Form had only invalid rows — surface as a generic error.
        fv.errors.append(ValidationError(field="form", message="no valid rows to save"))
        return fv, None

    outcome = save_with_lock(
        session,
        document_id=document_id,
        fiscal_year=fiscal_year,
        entries=fv.entries,
        reason=reason,
        lock_path=lock_path,
    )
    return fv, outcome


# ---------------------------------------------------------------------------
# Streamlit render
# ---------------------------------------------------------------------------


def _render_save_eligible_form(  # pragma: no cover - thin streamlit shell
    session: Session,
    row: QueueRow,
    *,
    lock_path: Path,
) -> None:
    """Render the actual editable form for one save-eligible queue row."""
    import streamlit as st

    from eidp.config import settings

    fy_default = row.fiscal_year or settings.target_fiscal_year
    state_key = f"manual_entry_rows__{row.document_id}"

    if state_key not in st.session_state:
        st.session_state[state_key] = [
            {"canonical_name": "", "enrollment": "", "graduates": ""},
        ]

    cols = st.columns([1, 1, 1])
    if cols[0].button("行を追加", key=f"add_{row.document_id}"):
        st.session_state[state_key].append(
            {"canonical_name": "", "enrollment": "", "graduates": ""}
        )
    if cols[1].button("最終行を削除", key=f"del_{row.document_id}"):
        if len(st.session_state[state_key]) > 1:
            st.session_state[state_key].pop()

    with st.form(key=f"form_{row.document_id}"):
        fiscal_year = st.number_input(
            "年度 (fiscal_year)",
            min_value=2019, max_value=2030, value=fy_default, step=1,
            key=f"fy_{row.document_id}",
        )
        reason = st.text_input("操作メモ (reason)", key=f"reason_{row.document_id}")

        form_rows: list[dict[str, Any]] = []
        for i, _ in enumerate(st.session_state[state_key]):
            st.markdown(f"**学科 #{i + 1}**")
            c = st.columns([2, 1, 1, 1, 1, 1, 1])
            canonical = c[0].text_input("学科名", key=f"name_{row.document_id}_{i}")
            capacity = c[1].text_input("収定", key=f"cap_{row.document_id}_{i}")
            enrollment = c[2].text_input("在籍", key=f"enr_{row.document_id}_{i}")
            intl = c[3].text_input("留学生", key=f"intl_{row.document_id}_{i}")
            graduates = c[4].text_input("卒業", key=f"grad_{row.document_id}_{i}")
            advanced = c[5].text_input("進学", key=f"adv_{row.document_id}_{i}")
            employed = c[6].text_input("就職", key=f"emp_{row.document_id}_{i}")
            d = st.columns([1, 1, 1, 1, 1, 1])
            other = d[0].text_input("その他", key=f"oth_{row.document_id}_{i}")
            prev_enrollment = d[1].text_input("前年在籍", key=f"prev_{row.document_id}_{i}")
            dropouts = d[2].text_input("中退", key=f"drp_{row.document_id}_{i}")
            dropout_rate = d[3].text_input("中退率(0-1)", key=f"drprate_{row.document_id}_{i}")
            duration_years = d[4].text_input("年限", key=f"dur_{row.document_id}_{i}")
            dept_change = d[5].selectbox(
                "学科改編", options=["", "新設", "廃科", "名称変更", "統合"],
                key=f"chg_{row.document_id}_{i}",
            )
            form_rows.append({
                "canonical_name": canonical,
                "capacity": capacity,
                "enrollment": enrollment,
                "intl_students": intl,
                "graduates": graduates,
                "advanced": advanced,
                "employed": employed,
                "other": other,
                "prev_enrollment": prev_enrollment,
                "dropouts": dropouts,
                "dropout_rate": dropout_rate,
                "duration_years": duration_years,
                "dept_change": dept_change or None,
            })

        submitted = st.form_submit_button("保存", type="primary")

    if submitted:
        validation, outcome = submit_form(
            session,
            document_id=row.document_id,
            fiscal_year=int(fiscal_year),
            rows=form_rows,
            reason=reason or None,
            lock_path=lock_path,
        )
        if not validation.ok:
            for err in validation.errors:
                st.error(f"{err.field}: {err.message}")
            return
        if outcome is None:  # defensive — submit_form returned validation-only path
            return
        if outcome.lock_busy:
            st.warning(
                f"週次処理中、編集は一時停止しています。少し待ってから再度保存してください "
                f"(owner={outcome.lock_owner}, started_at={outcome.lock_started_at})"
            )
            return
        if not outcome.ok:
            st.error(f"保存できませんでした: {outcome.error}")
            return
        if outcome.result is None:
            st.error("保存結果を確認できませんでした。再読み込みして確認してください。")
            return
        st.success(
            f"保存しました。学科 {outcome.result.rows_written} 件、"
            f"監査ログ {len(outcome.result.audit_actions)} 件。"
        )
        # Clear form state so the next render starts fresh.
        st.session_state.pop(state_key, None)
        st.rerun()


def _render_confidence_breakdown(  # pragma: no cover - thin streamlit shell
    summary: DocConfidenceSummary,
) -> None:
    """Render every per-row confidence panel for one document. Each
    panel surfaces the verdict glyph, composite, and the F1/F2/F3 table."""
    import streamlit as st

    from eidp.review.confidence_panels import panel_to_table_rows

    if not summary.rows:
        st.caption("(信頼度情報なし — 8.6.b 以前のデータ)")
        return

    for row_panel in summary.rows:
        cur_glyph = "🟢" if row_panel.is_current else "⚪"
        st.markdown(
            f"{cur_glyph}  **{row_panel.label}**  "
            f"— {row_panel.panel.label.glyph} {row_panel.panel.label.japanese}  "
            f"composite={row_panel.panel.composite:.2f}"
        )
        st.table(panel_to_table_rows(row_panel.panel))


def _render_pdf_panel(row: QueueRow) -> None:  # pragma: no cover - thin streamlit shell
    """Render source metadata plus lazy PDF preview/download controls."""
    import streamlit as st

    from eidp.config import settings

    st.markdown("**取得経路**")
    st.caption(
        "都道府県一覧から登録した学校URLを起点に、学校/法人ページ内のPDF候補をスコアリングし、"
        "対象年度がPDF本文で確認できたものだけを保存します。"
    )
    st.write(f"選択PDF: {row.source_url}")
    if row.discovered_from:
        st.write(f"PDFリンク掲載ページ: {row.discovered_from}")
    confidence_label = row.confidence if row.confidence is not None else "(なし)"
    st.write(f"判定: pdf_type={row.pdf_type or '(未分類)'} / confidence={confidence_label}")
    evidence_rows = latest_discovery_evidence(
        app_root=Path(settings.app_root),
        school_id=row.school_id,
        source_url=row.source_url,
    )
    if evidence_rows:
        with st.expander("探索ログ（候補PDFと採否理由）"):
            st.dataframe(
                [
                    {
                        "reason": e.reason,
                        "score": e.score,
                        "pdf_type": e.pdf_type or "",
                        "anchor": e.anchor_text,
                        "pdf_url": e.pdf_url,
                        "page_url": e.page_url,
                    }
                    for e in evidence_rows
                ],
                use_container_width=True,
                hide_index=True,
            )
    if not row.file_path:
        st.warning("PDF ファイルが保存されていません。source_url から原本を確認してください。")
        return

    st.write(f"file: {row.file_path}")
    state_key = f"show_pdf_preview__{row.document_id}"
    if st.button("PDF を表示 / ダウンロード準備", key=f"load_pdf_{row.document_id}"):
        st.session_state[state_key] = True

    if not st.session_state.get(state_key):
        st.caption("必要な文書だけ読み込みます。")
        return

    page_num = st.number_input(
        "ページ", min_value=1, max_value=999, value=1, step=1,
        key=f"pdf_page_{row.document_id}",
    )
    preview = build_pdf_preview(row.file_path, page_index=int(page_num) - 1)
    if preview.error:
        st.warning(preview.error)
        return

    if preview.pdf_bytes:
        st.download_button(
            "PDF ダウンロード",
            data=preview.pdf_bytes,
            file_name=preview.filename,
            mime="application/pdf",
            key=f"download_pdf_{row.document_id}",
        )
    if preview.image_png:
        caption = f"{preview.filename} p.{preview.page_index + 1}"
        if preview.page_count:
            caption += f" / {preview.page_count}"
        st.image(preview.image_png, caption=caption, use_container_width=True)


def render(session: Session, *, lock_path: Path) -> None:  # pragma: no cover - thin streamlit shell
    """Top-level Streamlit render for the PDF確認・手入力 page."""
    import streamlit as st

    from eidp.config import settings
    from eidp.fiscal_year import format_fiscal_year_label
    from eidp.ocr import (
        availability_banner_severity,
        availability_banner_text,
        detect_ocr_availability,
    )
    from eidp.review.target_year_status import target_year_overview

    st.subheader("PDF確認・手入力")
    target_label = format_fiscal_year_label(settings.target_fiscal_year)
    target = target_year_overview(
        session,
        target_fiscal_year=settings.target_fiscal_year,
        school_type=OPERATOR_SCHOOL_TYPE_SCOPE,
    )
    st.caption(f"対象範囲: {OPERATOR_SCHOOL_SCOPE_LABEL}")
    mcols = st.columns(4)
    mcols[0].metric("対象校", target.active_schools)
    mcols[1].metric(f"{target_label} PDF", target.current_target_schools)
    mcols[2].metric("旧年度fallback", target.stale_target_documents)
    mcols[3].metric("要確認", target.review_queue_documents)
    if target.current_target_documents == 0 and target.stale_target_documents > 0:
        st.error(
            f"{target_label} の自動採録は 0 件です。旧年度PDFは参考情報として確認し、"
            "現在年度PDFは URL追加 または週次再取得で集めてください。"
        )

    status = probe_lock(lock_path)
    if status.held:
        st.warning(
            f"週次処理中、編集は一時停止しています "
            f"(owner={status.owner}, started_at={status.started_at})"
        )

    # Sprint 8.6.d.3 — OCR add-on availability banner. Operators on a
    # PC without the add-on still see image PDFs in the queue; the
    # banner makes it obvious whether they can press an OCR button.
    ocr_detection = detect_ocr_availability(app_root=Path(settings.app_root))
    severity = availability_banner_severity(ocr_detection)
    banner = availability_banner_text(ocr_detection)
    severity_fn = {
        "error": st.error,
        "warning": st.warning,
        "info": st.info,
        "success": st.success,
    }.get(severity, st.info)
    severity_fn(banner)

    view_options = manual_queue_view_options(target_label)
    selected_view_label = st.radio(
        "表示範囲",
        options=list(view_options.values()),
        horizontal=True,
    )
    selected_view = next(key for key, label in view_options.items() if label == selected_view_label)
    focus_document_id = coerce_focus_document_id(st.session_state.get(MANUAL_ENTRY_DOCUMENT_ID_STATE_KEY))
    queue = list_documents_for_manual_queue_view(
        session,
        view=selected_view,
        target_fiscal_year=settings.target_fiscal_year,
        focus_document_id=focus_document_id,
    )
    if focus_document_id is not None:
        if queue and queue[0].document_id == focus_document_id:
            st.info(f"学校別タスクから doc#{focus_document_id} を先頭表示しています。")
            if st.button("通常順に戻す"):
                st.session_state.pop(MANUAL_ENTRY_DOCUMENT_ID_STATE_KEY, None)
                st.rerun()
        else:
            st.warning(f"doc#{focus_document_id} は現在のPDF確認キューにありません。")

    if not queue:
        st.success("この表示範囲の文書はありません。PDF確認は学校別タスクから必要な学校を選んで開いてください。")
        return

    st.caption(f"待機 {len(queue)} 件")
    for row in queue[:20]:
        # Sprint 8.6.d.2 — confidence summary surfaces in the queue
        # title so the operator sees worst-case verdict before
        # expanding the row.
        confidence = summarize_confidence_for_document(session, row.document_id)
        if row.fiscal_year == settings.target_fiscal_year:
            year_badge = "現在年度"
        elif row.fiscal_year is None:
            year_badge = "年度未確定"
        elif row.fiscal_year < settings.target_fiscal_year:
            year_badge = "旧年度"
        else:
            year_badge = "未来年度"
        title = (
            f"[{row.ingest_status} / {year_badge}] {row.school_name} ({row.prefecture}) "
            f"— fy={row.fiscal_year} doc#{row.document_id} | {confidence.summary_line}"
        )
        with st.expander(title):
            _render_confidence_breakdown(confidence)
            pdf_col, form_col = st.columns([1, 2])
            with pdf_col:
                _render_pdf_panel(row)

            if row.ingest_status not in SAVE_ELIGIBLE_STATUSES:
                if row.ingest_status == "ingested":
                    st.info("自動採録済です。PDF原本と抽出結果の確認用として表示しています。")
                elif row.ingest_status == "school_mismatch":
                    st.warning(
                        "この文書は ``school_mismatch`` です。学校マッピングを"
                        "先に修正してください。手入力は無効化されています。"
                    )
                else:
                    st.info("この状態の文書は確認専用です。")
                continue

            with form_col:
                _render_save_eligible_form(session, row, lock_path=lock_path)
