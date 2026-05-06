from __future__ import annotations

from pathlib import Path

from eidp.config import Settings
from eidp.fiscal_year import current_fiscal_year


def test_firecrawl_api_key_uses_eidp_env_prefix(monkeypatch) -> None:
    monkeypatch.setenv("EIDP_FIRECRAWL_API_KEY", "test-key")

    settings = Settings(_env_file=None)

    assert settings.firecrawl_api_key == "test-key"


def test_target_fiscal_year_defaults_to_current_japanese_fiscal_year(monkeypatch) -> None:
    monkeypatch.delenv("EIDP_TARGET_FISCAL_YEAR", raising=False)

    settings = Settings(_env_file=None)

    assert settings.target_fiscal_year == current_fiscal_year()


def test_target_fiscal_year_can_be_pinned_by_env(monkeypatch) -> None:
    monkeypatch.setenv("EIDP_TARGET_FISCAL_YEAR", "2027")

    settings = Settings(_env_file=None)

    assert settings.target_fiscal_year == 2027


def test_fiscal_era_settings_can_be_pinned_by_env(monkeypatch) -> None:
    monkeypatch.setenv("EIDP_FISCAL_ERA_NAME", "令和")
    monkeypatch.setenv("EIDP_FISCAL_ERA_ROMANIZED", "reiwa")
    monkeypatch.setenv("EIDP_FISCAL_ERA_INITIAL", "r")
    monkeypatch.setenv("EIDP_FISCAL_ERA_START_YEAR", "2019")

    settings = Settings(_env_file=None)

    assert settings.fiscal_era_name == "令和"
    assert settings.fiscal_era_romanized == "reiwa"
    assert settings.fiscal_era_initial == "r"
    assert settings.fiscal_era_start_year == 2019


def test_runtime_ocr_settings_can_be_pinned_by_env(monkeypatch) -> None:
    monkeypatch.setenv("EIDP_OCR_AUTO_ENABLE", "off")
    monkeypatch.setenv("EIDP_OCR_MIN_CPUS", "4")
    monkeypatch.setenv("EIDP_OCR_MIN_FREE_RAM_MB", "8192")
    monkeypatch.setenv("EIDP_TESSERACT_BIN", "C:/EIDP/tesseract.exe")

    settings = Settings(_env_file=None)

    assert settings.ocr_auto_enable == "off"
    assert settings.ocr_min_cpus == 4
    assert settings.ocr_min_free_ram_mb == 8192
    assert settings.tesseract_bin == "C:/EIDP/tesseract.exe"


def test_env_example_is_windows_sqlite_operator_default() -> None:
    body = Path(".env.example").read_text(encoding="utf-8")

    assert "EIDP_DATABASE_URL=sqlite:///C:/EIDP/data/eidp.sqlite3" in body
    assert "EIDP_DATA_DIR=C:/EIDP/data" in body
    assert "# EIDP_TARGET_FISCAL_YEAR=2026" in body
    assert "EIDP_FISCAL_ERA_NAME=令和" in body
    assert "EIDP_OCR_AUTO_ENABLE=auto" in body
    assert "${APP_ROOT}" not in body
    assert not body.splitlines()[0].startswith("EIDP_DATABASE_URL=postgresql"), (
        "operator .env example must not default to the old Venus/Postgres URL"
    )
