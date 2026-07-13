from __future__ import annotations

from pathlib import Path

import pdfplumber
import pytest
from streamlit.testing.v1 import AppTest
from structlog.testing import capture_logs

from eidp.db.locking import acquire_lock
from eidp.pipeline.extraction_queue import ExtractionStatus, load_extracted_rows, load_extraction_queue
from eidp.pipeline.pdf_intake import PdfIntakeRecord, PdfKind, store_pdf_upload, validate_intake_metadata

REPO_ROOT = Path(__file__).resolve().parents[2]
TEXT_PDF_BYTES = (REPO_ROOT / "data" / "sample-pdfs" / "tca.pdf").read_bytes()


def _render_extraction_queue_for_test(intake_root):  # noqa: ANN001, ANN201
    from eidp.identity import IdentitySource, ResolvedIdentity
    from eidp.web.pages.extraction_queue import render_extraction_queue_page

    render_extraction_queue_page(
        identity=ResolvedIdentity("app-test-operator", IdentitySource.CONFIGURED_FALLBACK),
        intake_root=intake_root,
    )


def _store_intake(intake_root: Path, *, pdf_kind: PdfKind, school_name: str = "東京テスト専門学校") -> PdfIntakeRecord:
    metadata = validate_intake_metadata(
        school_name=school_name,
        school_id="S-001",
        fiscal_year=2026,
        source_page_url="https://example.ac.jp/disclosure/",
        uploaded_filename="form.pdf",
    )
    return store_pdf_upload(
        metadata=metadata,
        pdf_bytes=TEXT_PDF_BYTES,
        intake_root=intake_root,
        detect_pdf_kind_func=lambda _content: pdf_kind,
    )


def _run_queue_app(intake_root: Path) -> AppTest:
    app = AppTest.from_function(_render_extraction_queue_for_test, args=(intake_root,)).run(timeout=30)
    assert not app.exception
    return app


def _button(app: AppTest, *, label: str):  # noqa: ANN202
    return next(button for button in app.button if button.label == label)


def _queue_item(intake_root: Path, intake_record_id: str):  # noqa: ANN202
    return next(item for item in load_extraction_queue(intake_root) if item.intake_record_id == intake_record_id)


def test_text_queue_run_reaches_core_and_persists_evidence(tmp_path: Path) -> None:
    record = _store_intake(tmp_path, pdf_kind=PdfKind.TEXT)
    app = _run_queue_app(tmp_path)

    assert _button(app, label="Run").key == f"run_extraction_{record.record_id}"
    with capture_logs() as logs:
        _button(app, label="Run").click()
        app.run(timeout=30)

    assert not app.exception
    item = _queue_item(tmp_path, record.record_id)
    assert item.status == ExtractionStatus.EXTRACTION_COMPLETED
    assert load_extracted_rows(tmp_path, record.record_id)
    requested = [event for event in logs if event.get("event") == "served_extraction_requested"]
    assert len(requested) == 1
    assert requested[0]["actor"] == "app-test-operator"
    assert requested[0]["identity_source"] == "configured_fallback"
    assert set(requested[0]) <= {"event", "actor", "identity_source", "intake_record_id", "log_level"}
    assert not (tmp_path / "audit" / "manual-actions.jsonl").exists()


def test_failed_text_extraction_retains_source_and_error_then_retries(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    record = _store_intake(tmp_path, pdf_kind=PdfKind.TEXT)
    source_path = tmp_path / (record.stored_path or "")
    source_bytes = source_path.read_bytes()
    real_pdfplumber_open = pdfplumber.open
    attempts = 0

    def flaky_pdfplumber_open(*args: object, **kwargs: object):  # noqa: ANN202
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise RuntimeError("parser exploded")
        return real_pdfplumber_open(*args, **kwargs)

    monkeypatch.setattr(pdfplumber, "open", flaky_pdfplumber_open)
    app = _run_queue_app(tmp_path)

    _button(app, label="Run").click()
    app.run(timeout=30)

    failed = _queue_item(tmp_path, record.record_id)
    assert failed.status == ExtractionStatus.EXTRACTION_FAILED
    assert failed.error_reason == "parser exploded"
    assert failed.pdf_path == record.stored_path
    assert source_path.read_bytes() == source_bytes
    assert any("parser exploded" in message.value for message in app.error)
    assert _button(app, label="Retry").key == f"retry_extraction_{record.record_id}"

    _button(app, label="Retry").click()
    app.run(timeout=30)

    assert not app.exception
    retried = _queue_item(tmp_path, record.record_id)
    assert retried.status == ExtractionStatus.EXTRACTION_COMPLETED
    assert retried.error_reason is None
    assert load_extracted_rows(tmp_path, record.record_id)


def test_image_queue_has_no_run_or_retry_action(tmp_path: Path) -> None:
    record = _store_intake(tmp_path, pdf_kind=PdfKind.IMAGE, school_name="大阪テスト専門学校")

    app = _run_queue_app(tmp_path)

    assert not [button for button in app.button if button.label in {"Run", "Retry"}]
    item = _queue_item(tmp_path, record.record_id)
    assert item.status == ExtractionStatus.NOT_APPLICABLE
    assert load_extracted_rows(tmp_path, record.record_id) == []


def test_busy_lock_shows_banner_and_changes_no_queue_or_result_state(tmp_path: Path) -> None:
    record = _store_intake(tmp_path, pdf_kind=PdfKind.TEXT)
    app = _run_queue_app(tmp_path)
    before_item = _queue_item(tmp_path, record.record_id)
    before_job_bytes = (tmp_path / "extraction" / "jobs" / f"{record.record_id}.json").read_bytes()

    with capture_logs() as logs, acquire_lock(tmp_path / ".lock", owner="background_job"):
        _button(app, label="Run").click()
        app.run(timeout=30)

    assert not app.exception
    assert any("background_job" in message.value for message in app.warning)
    assert _queue_item(tmp_path, record.record_id) == before_item
    assert (tmp_path / "extraction" / "jobs" / f"{record.record_id}.json").read_bytes() == before_job_bytes
    assert load_extracted_rows(tmp_path, record.record_id) == []
    assert not [event for event in logs if event.get("event") == "served_extraction_requested"]
