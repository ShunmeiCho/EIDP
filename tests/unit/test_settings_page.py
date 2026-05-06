from __future__ import annotations

from pathlib import Path

from eidp.config import apply_fiscal_era_settings, apply_runtime_env_settings, settings
from eidp.review._pages.settings_page import (
    build_info_summary,
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


def test_save_operator_settings_writes_runtime_variables(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
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
            tesseract_bin="C:/EIDP/tesseract.exe",
            ocr_provider="tesseract",
            ocr_device="cpu",
            search_provider="serper",
            serper_api_key="serper-key",
            brave_api_key="",
            google_api_key="",
            google_cx="",
            firecrawl_api_key="firecrawl-key",
        )
    finally:
        for key, value in original.items():
            setattr(settings, key, value)
        apply_fiscal_era_settings(settings)
        apply_runtime_env_settings(settings)

    body = env_path.read_text(encoding="utf-8")
    assert updates["EIDP_TARGET_FISCAL_YEAR"] == "2027"
    assert "EIDP_OCR_AUTO_ENABLE=off" in body
    assert "EIDP_SEARCH_PROVIDER=serper" in body
    assert "EIDP_FIRECRAWL_API_KEY=firecrawl-key" in body
