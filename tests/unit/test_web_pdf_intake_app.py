from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest

from eidp.db.locking import acquire_lock
from eidp.pipeline.pdf_intake import load_intake_queue

PDF_BYTES = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n%%EOF\n"


def _render_pdf_intake_for_test(intake_root):  # noqa: ANN001, ANN201
    from eidp.identity import IdentitySource, ResolvedIdentity
    from eidp.web.pages.pdf_intake import render_pdf_intake_page

    render_pdf_intake_page(
        identity=ResolvedIdentity("app-test-operator", IdentitySource.CONFIGURED_FALLBACK),
        intake_root=intake_root,
    )


def _configured_pdf_intake_app(intake_root: Path, *, filename: str) -> AppTest:
    app = AppTest.from_function(_render_pdf_intake_for_test, args=(intake_root,)).run(timeout=5)
    assert not app.exception

    next(widget for widget in app.text_input if widget.key == "pdf_school_name").set_value("東京テスト専門学校")
    next(widget for widget in app.text_input if widget.key == "pdf_school_id").set_value("S-001")
    next(widget for widget in app.text_input if widget.key == "pdf_source_page_url").set_value(
        "https://example.ac.jp/disclosure/"
    )
    next(widget for widget in app.file_uploader if widget.label == "PDF file").upload(
        filename,
        PDF_BYTES,
        "application/pdf",
    )
    return app


def test_pdf_intake_app_sanitizes_uploaded_filename_before_writing(tmp_path: Path) -> None:
    app = _configured_pdf_intake_app(tmp_path, filename="../../outside/evil file.pdf")

    next(button for button in app.button if button.label == "Register PDF").click()
    app.run(timeout=5)

    assert not app.exception
    assert any("Registered" in message.value for message in app.success)
    records = load_intake_queue(tmp_path)
    assert len(records) == 1
    assert records[0].stored_path is not None
    stored_path = (tmp_path / records[0].stored_path).resolve()
    assert stored_path.is_relative_to(tmp_path.resolve())
    assert stored_path.name.endswith("-evil_file.pdf")
    assert stored_path.read_bytes() == PDF_BYTES


def test_pdf_intake_app_reports_busy_lock_without_writing(tmp_path: Path) -> None:
    app = _configured_pdf_intake_app(tmp_path, filename="form.pdf")

    with acquire_lock(tmp_path / ".lock", owner="background_job"):
        next(button for button in app.button if button.label == "Register PDF").click()
        app.run(timeout=5)

    assert not app.exception
    assert any("background_job" in message.value for message in app.error)
    assert not app.success
    assert load_intake_queue(tmp_path) == []
