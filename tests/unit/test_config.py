from __future__ import annotations

from eidp.config import Settings


def test_firecrawl_api_key_uses_eidp_env_prefix(monkeypatch) -> None:
    monkeypatch.setenv("EIDP_FIRECRAWL_API_KEY", "test-key")

    settings = Settings(_env_file=None)

    assert settings.firecrawl_api_key == "test-key"
