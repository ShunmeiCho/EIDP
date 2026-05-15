from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

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


@pytest.mark.parametrize("target_fiscal_year", ["2018", "2100"])
def test_target_fiscal_year_rejects_unsupported_env_range(monkeypatch, target_fiscal_year: str) -> None:
    monkeypatch.setenv("EIDP_TARGET_FISCAL_YEAR", target_fiscal_year)

    with pytest.raises(ValidationError, match=r"target_fiscal_year outside supported range \[2019, 2099\]"):
        Settings(_env_file=None)


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


def test_runtime_url_search_settings_can_be_pinned_by_env(monkeypatch) -> None:
    monkeypatch.setenv("EIDP_SEARCH_PROVIDER", "serper")
    monkeypatch.setenv("EIDP_URL_SEARCH_AUTO_ENABLE", "on")
    monkeypatch.setenv("EIDP_URL_SEARCH_BATCH_SIZE", "300")

    settings = Settings(_env_file=None)

    assert settings.search_provider == "serper"
    assert settings.url_search_auto_enable == "on"
    assert settings.url_search_batch_size == 300


def test_default_database_url_follows_data_dir_env(monkeypatch, tmp_path: Path) -> None:
    data_dir = tmp_path / "operator-data"
    monkeypatch.setenv("EIDP_DATA_DIR", str(data_dir))
    monkeypatch.delenv("EIDP_DATABASE_URL", raising=False)

    settings = Settings(_env_file=None)

    assert settings.data_dir == data_dir
    assert settings.database_url == f"sqlite:///{(data_dir / 'eidp.sqlite3').as_posix()}"


def test_env_example_lets_database_url_follow_data_dir() -> None:
    body = Path(".env.example").read_text(encoding="utf-8")
    active_lines = [
        line.strip() for line in body.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]

    assert not any(line.startswith("EIDP_DATABASE_URL=") for line in active_lines)
    assert "EIDP_DATA_DIR=C:/EIDP/data" in body
    assert "# EIDP_TARGET_FISCAL_YEAR=2026" in body
    assert "EIDP_FISCAL_ERA_NAME=令和" in body
    assert "EIDP_OCR_AUTO_ENABLE=auto" in body
    assert "EIDP_URL_SEARCH_AUTO_ENABLE=auto" in body
    assert "EIDP_URL_SEARCH_BATCH_SIZE=200" in body
    assert "${APP_ROOT}" not in body
    assert not any(line.startswith("EIDP_DATABASE_URL=postgresql") for line in active_lines), (
        "operator .env example must not default to the old Venus/Postgres URL"
    )
