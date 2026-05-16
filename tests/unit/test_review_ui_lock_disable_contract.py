from __future__ import annotations

from pathlib import Path


def _source(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_operator_write_pages_disable_or_hide_actions_when_app_lock_is_held() -> None:
    source = _source("src/eidp/review/operator_pages.py")
    app_source = _source("src/eidp/review/app.py")

    assert "def _operator_lock_held" in source
    assert "lock_held = _operator_lock_held(lock_path)" in source
    assert 'disabled=uploaded_csv is None or lock_held' in source
    assert 'disabled=selected_school_id is None or lock_held' in source
    assert 'disabled=lock_held' in source
    assert "if _operator_lock_held(lock_path):\n        return" in source
    assert 'page_exports(session, lock_path=Path(settings.data_dir) / ".lock")' in app_source


def test_quick_operator_pages_disable_primary_write_buttons_when_app_lock_is_held() -> None:
    excel_source = _source("src/eidp/review/_pages/excel_preview.py")
    fiscal_source = _source("src/eidp/review/_pages/fiscal_year_override.py")
    manual_source = _source("src/eidp/review/_pages/pdf_manual_entry.py")
    school_tasks_source = _source("src/eidp/review/_pages/school_year_tasks.py")

    assert "disabled=status.held or not can_generate" in excel_source
    assert 'st.form_submit_button("年度を確定", type="primary", disabled=status.held)' in fiscal_source
    assert 'st.form_submit_button("保存", type="primary", disabled=lock_held)' in manual_source
    assert "lock_held=status.held" in manual_source
    assert 'st.button("年度タスクを再計算", type="primary", disabled=lock_held' in school_tasks_source
