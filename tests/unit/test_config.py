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


def test_env_example_is_windows_sqlite_operator_default() -> None:
    body = Path(".env.example").read_text(encoding="utf-8")

    assert "EIDP_DATABASE_URL=sqlite:///C:/EIDP/data/eidp.sqlite3" in body
    assert "EIDP_DATA_DIR=C:/EIDP/data" in body
    assert "# EIDP_TARGET_FISCAL_YEAR=2026" in body
    assert "${APP_ROOT}" not in body
    assert not body.splitlines()[0].startswith("EIDP_DATABASE_URL=postgresql"), (
        "operator .env example must not default to the old Venus/Postgres URL"
    )
