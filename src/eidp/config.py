"""Application configuration via pydantic-settings.

Sprint 8.5.a — application root resolution that survives Windows
deployment.

The repo originally defaulted to a relative ``./data`` and Postgres URL,
which assumes a developer-style cwd. On a Windows operator PC the cwd
is whatever Explorer / Task Scheduler / a ``.bat`` decides, so relative
paths and a Postgres default both fail.

Resolution order for the application root (used to anchor data_dir,
default SQLite path, etc.) — first match wins:

1. ``EIDP_APP_ROOT`` environment variable (set by ``.bat`` launchers
   via ``set "EIDP_APP_ROOT=%~dp0\\.."``).
2. The current working directory if it looks like the app root
   (heuristic: a ``data`` folder or ``.env`` is present beside it).
3. ``Path(__file__).resolve().parents[2]`` — the repo root when running
   from a source checkout. This is the last resort because in an
   installed wheel ``__file__`` lives under ``site-packages`` and that
   would not be a usable application root.

The default ``database_url`` resolves to a SQLite file under the
resolved app root unless the user sets ``EIDP_DATABASE_URL`` explicitly
(absolute Postgres URL on dev, absolute SQLite path on Win).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings

from eidp.fiscal_year import current_fiscal_year


def resolve_app_root(*, env: dict[str, str] | None = None, cwd: Path | None = None) -> Path:
    """Resolve the application root directory.

    ``env`` and ``cwd`` are injection seams used by tests; production
    callers pass nothing and we read ``os.environ`` and ``Path.cwd()``.
    """
    env_map = env if env is not None else os.environ
    explicit = env_map.get("EIDP_APP_ROOT")
    if explicit:
        candidate = Path(explicit).expanduser().resolve()
        return candidate

    here = (cwd if cwd is not None else Path.cwd()).resolve()
    if (here / "data").is_dir() or (here / ".env").is_file() or (here / "pyproject.toml").is_file():
        return here

    # Last resort — repo source layout: src/eidp/config.py → parents[2] = repo root.
    return Path(__file__).resolve().parents[2]


_DEFAULT_APP_ROOT = resolve_app_root()


def _default_database_url() -> str:
    """SQLite under the resolved app root by default."""
    sqlite_path = (_DEFAULT_APP_ROOT / "data" / "eidp.sqlite3").as_posix()
    return f"sqlite:///{sqlite_path}"


class Settings(BaseSettings):
    database_url: str = _default_database_url()
    log_level: str = "INFO"
    data_dir: Path = _DEFAULT_APP_ROOT / "data"
    app_root: Path = _DEFAULT_APP_ROOT

    # Operational year currently in scope. Defaults to the Japanese fiscal
    # year for today, while EIDP_TARGET_FISCAL_YEAR remains available for
    # explicit operator/admin override.
    target_fiscal_year: int = Field(default_factory=current_fiscal_year)

    # Search API (switch provider by changing search_provider)
    search_provider: str = "duckduckgo"  # duckduckgo | brave | google | serper
    brave_api_key: str = ""
    google_api_key: str = ""
    google_cx: str = ""
    serper_api_key: str = ""

    # Firecrawl API (for corporation root URL expansion)
    firecrawl_api_key: str = ""

    model_config = {"env_prefix": "EIDP_", "env_file": ".env", "extra": "ignore"}

    @field_validator("data_dir", "app_root", mode="before")
    @classmethod
    def _expand_path(cls, v: Any) -> Any:
        if isinstance(v, str):
            return Path(v).expanduser()
        return v


settings = Settings()
