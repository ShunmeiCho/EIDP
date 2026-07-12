from __future__ import annotations

import inspect
import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from eidp.config import apply_fiscal_era_settings, apply_runtime_env_settings, settings
from eidp.db.models import Base, ManualActionLog, School, SchoolFiscalYearStatus
from eidp.review._pages import settings_page
from eidp.review._pages.settings_page import (
    audit_operator_settings_saved,
    build_info_summary,
    maybe_rebuild_school_year_tasks_after_target_change,
    read_build_info,
    save_operator_settings,
    update_env_text,
    validate_operator_settings,
)


def test_update_env_text_updates_existing_keys_and_appends_missing() -> None:
    body = "A=1\nEIDP_TARGET_FISCAL_YEAR=2026\n# comment\n"

    updated = update_env_text(
        body,
        {
            "EIDP_TARGET_FISCAL_YEAR": "2027",
            "EIDP_FISCAL_ERA_NAME": "令和",
        },
    )

    assert "A=1" in updated
    assert "EIDP_TARGET_FISCAL_YEAR=2027" in updated
    assert "EIDP_TARGET_FISCAL_YEAR=2026" not in updated
    assert "EIDP_FISCAL_ERA_NAME=令和" in updated


def test_validate_operator_settings_requires_alias_fields_when_enabled() -> None:
    errors = validate_operator_settings(
        fiscal_era_enabled=True,
        fiscal_era_name="",
        fiscal_era_romanized="",
        fiscal_era_initial="",
    )

    assert len(errors) == 3


def test_read_build_info_returns_display_fields(tmp_path: Path) -> None:
    (tmp_path / "BUILD_INFO.json").write_text(
        """
        {
          "app": "EIDP",
          "git_commit": "48d860a829b294719ed2f781f4d509a10e844c6b",
          "git_branch": "sprint8-handoff-finalize",
          "git_dirty": "false",
          "built_at_utc": "2026-05-06T18:02:34+00:00",
          "ignored": 123
        }
        """,
        encoding="utf-8",
    )

    info = read_build_info(tmp_path)

    assert info == {
        "git_commit": "48d860a829b294719ed2f781f4d509a10e844c6b",
        "git_branch": "sprint8-handoff-finalize",
        "built_at_utc": "2026-05-06T18:02:34+00:00",
        "git_dirty": "false",
    }
    assert build_info_summary(info).startswith("commit=48d860a")


def test_read_build_info_tolerates_missing_or_invalid_file(tmp_path: Path) -> None:
    assert read_build_info(tmp_path) == {}
    (tmp_path / "BUILD_INFO.json").write_text("{bad json", encoding="utf-8")
    assert read_build_info(tmp_path) == {}


def test_render_uses_supported_target_fiscal_year_bounds() -> None:
    source = inspect.getsource(settings_page.render)

    assert "min_value=MIN_SUPPORTED_TARGET_FISCAL_YEAR" in source
    assert "max_value=MAX_SUPPORTED_TARGET_FISCAL_YEAR" in source


def test_target_fiscal_year_is_not_a_persistent_setting_key() -> None:
    assert "EIDP_TARGET_FISCAL_YEAR" not in settings_page.SETTING_ENV_KEYS


def test_external_search_command_is_env_only_not_operator_setting_key() -> None:
    assert "EIDP_EXTERNAL_SEARCH_COMMAND" not in settings_page.SETTING_ENV_KEYS


def test_save_operator_settings_writes_runtime_variables(tmp_path: Path, monkeypatch) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("EIDP_TARGET_FISCAL_YEAR=2026\n", encoding="utf-8")
    monkeypatch.setenv("EIDP_TARGET_FISCAL_YEAR", "2026")
    original = {key: getattr(settings, key) for key in (
        "target_fiscal_year",
        "fiscal_era_enabled",
        "fiscal_era_name",
        "fiscal_era_romanized",
        "fiscal_era_initial",
        "fiscal_era_start_year",
        "ocr_auto_enable",
        "ocr_min_cpus",
        "ocr_min_free_ram_mb",
        "tesseract_bin",
        "ocr_provider",
        "ocr_device",
        "search_provider",
        "url_search_auto_enable",
        "url_search_batch_size",
        "serper_api_key",
        "brave_api_key",
        "google_api_key",
        "google_cx",
        "firecrawl_api_key",
    )}

    try:
        updates = save_operator_settings(
            env_path,
            target_fiscal_year=2027,
            fiscal_era_enabled=True,
            fiscal_era_name="令和",
            fiscal_era_romanized="reiwa",
            fiscal_era_initial="r",
            fiscal_era_start_year=2019,
            ocr_auto_enable="off",
            ocr_min_cpus=4,
            ocr_min_free_ram_mb=8192,
            tesseract_bin="/home/junming/EIDP/ocr/tesseract/bin/tesseract",
            ocr_provider="tesseract",
            ocr_device="cpu",
            search_provider="serper",
            url_search_auto_enable="on",
            url_search_batch_size=300,
            serper_api_key="serper-key",
            brave_api_key="",
            google_api_key="",
            google_cx="",
            firecrawl_api_key="firecrawl-key",
        )
        assert settings.target_fiscal_year == 2027
    finally:
        for key, value in original.items():
            setattr(settings, key, value)
        apply_fiscal_era_settings(settings)
        apply_runtime_env_settings(settings)

    body = env_path.read_text(encoding="utf-8")
    assert "EIDP_TARGET_FISCAL_YEAR" not in updates
    assert "EIDP_TARGET_FISCAL_YEAR=2026" in body
    assert "EIDP_TARGET_FISCAL_YEAR=2027" not in body
    assert os.environ["EIDP_TARGET_FISCAL_YEAR"] == "2026"
    assert "EIDP_OCR_AUTO_ENABLE=off" in body
    assert "EIDP_SEARCH_PROVIDER=serper" in body
    assert "EIDP_URL_SEARCH_AUTO_ENABLE=on" in body
    assert "EIDP_URL_SEARCH_BATCH_SIZE=300" in body
    assert "EIDP_FIRECRAWL_API_KEY=firecrawl-key" in body


def test_audit_operator_settings_saved_redacts_secret_values() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        audit_operator_settings_saved(
            session,
            old_target_fiscal_year=2026,
            target_fiscal_year=2027,
            updates={
                "EIDP_SEARCH_PROVIDER": "serper",
                "EIDP_SERPER_API_KEY": "super-secret",
                "EIDP_GOOGLE_API_KEY": "",
                "EIDP_URL_SEARCH_BATCH_SIZE": "300",
            },
            rebuild_stats=None,
        )
        session.commit()

        audit = session.query(ManualActionLog).one()
        assert audit.action_type == "operator_settings_saved"
        assert audit.target_table == "operator_settings"
        assert audit.target_id is None
        assert audit.old_value == '{"target_fiscal_year": 2026}'
        assert '"target_fiscal_year": 2027' in (audit.new_value or "")
        assert '"EIDP_SEARCH_PROVIDER": "serper"' in (audit.new_value or "")
        assert '"EIDP_SERPER_API_KEY": "[set]"' in (audit.new_value or "")
        assert "super-secret" not in (audit.new_value or "")
        assert audit.reason == "Operator saved runtime settings"


def test_render_records_settings_save_in_manual_action_log_contract() -> None:
    source = inspect.getsource(settings_page.render)

    assert "audit_operator_settings_saved(" in source


def test_target_year_change_rebuilds_school_task_rows_for_all_school_types() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add_all(
            [
                School(
                    id=1,
                    school_code="S1",
                    prefecture="東京都",
                    corporation_name="法人1",
                    school_name="専門学校テスト",
                    school_type="専門学校",
                    status="active",
                ),
                School(
                    id=2,
                    school_code="U1",
                    prefecture="東京都",
                    corporation_name="法人2",
                    school_name="大学テスト",
                    school_type="大学",
                    status="active",
                ),
            ]
        )
        session.add(
            SchoolFiscalYearStatus(
                school_id=1,
                fiscal_year=2026,
                url_status="no_url",
                pdf_status="none",
                extract_status="none",
                yoy_diff_status="unchecked",
                evidence_level="none",
                excel_ready=False,
                blocking_reason="no_url",
            )
        )
        session.commit()

        stats = maybe_rebuild_school_year_tasks_after_target_change(
            session,
            old_target_fiscal_year=2026,
            target_fiscal_year=2027,
        )
        session.commit()

        assert stats is not None
        assert stats.rebuilt == 2
        assert (
            session.query(SchoolFiscalYearStatus)
            .filter(SchoolFiscalYearStatus.fiscal_year == 2027)
            .count()
            == 2
        )


def test_target_year_unchanged_does_not_rebuild_school_task_rows() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        assert (
            maybe_rebuild_school_year_tasks_after_target_change(
                session,
                old_target_fiscal_year=2026,
                target_fiscal_year=2026,
            )
            is None
        )
