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

from eidp.fiscal_year import JapaneseEra, configure_japanese_eras, current_fiscal_year


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

    # Japanese-era aliases used for operator labels and official-page search
    # tokens. Western fiscal year integers remain the canonical value. These
    # settings are intentionally manual so EIDP does not predict future era
    # changes.
    fiscal_era_enabled: bool = True
    fiscal_era_name: str = "令和"
    fiscal_era_romanized: str = "reiwa"
    fiscal_era_initial: str = "r"
    fiscal_era_start_year: int = 2019

    # Search API (switch provider by changing search_provider)
    search_provider: str = "duckduckgo"  # duckduckgo | brave | google | serper
    url_search_auto_enable: str = "auto"  # auto | on | off
    url_search_batch_size: int = 200
    brave_api_key: str = ""
    google_api_key: str = ""
    google_cx: str = ""
    serper_api_key: str = ""

    # Optional Scrapling-backed school website URL completion. This is a
    # bounded fallback for schools still missing SchoolSite rows after the
    # official prefecture index, seed CSV, corporation patterns, and regular
    # search provider have run.
    school_url_crawl_auto_enable: str = "auto"  # auto | on | off
    school_url_crawl_batch_size: int = 25
    school_url_crawl_fetch_mode: str = "static"  # static | dynamic | stealthy
    school_url_crawl_min_seconds_per_domain: float = 5.0
    school_url_crawl_min_jitter: float = 0.5
    school_url_crawl_max_jitter: float = 1.5

    # Optional rendered-HTML fallback for PDF discovery. This is separate
    # from school URL discovery: once a SchoolSite is known, some disclosure
    # pages still hide the current PDF behind JavaScript tabs.
    pdf_discovery_rendered_html_auto_enable: str = "auto"  # auto | on | off
    pdf_discovery_rendered_html_fetch_mode: str = "dynamic"  # dynamic | stealthy | static

    # Firecrawl API (for corporation root URL expansion)
    firecrawl_api_key: str = ""

    # OCR runtime settings. Some OCR modules read environment variables
    # directly, so apply_runtime_env_settings mirrors these values into
    # ``os.environ`` after Settings is loaded.
    ocr_auto_enable: str = "auto"  # auto | on | off
    ocr_min_cpus: int = 2
    ocr_min_free_ram_mb: int = 4096
    tesseract_bin: str = ""
    ocr_provider: str = ""
    ocr_device: str = ""

    model_config = {"env_prefix": "EIDP_", "env_file": ".env", "extra": "ignore"}

    @field_validator("data_dir", "app_root", mode="before")
    @classmethod
    def _expand_path(cls, v: Any) -> Any:
        if isinstance(v, str):
            return Path(v).expanduser()
        return v


settings = Settings()


def apply_fiscal_era_settings(config: Settings = settings) -> None:
    """Apply configured fiscal-year era aliases to helper functions."""
    if not config.fiscal_era_enabled:
        configure_japanese_eras(())
        return
    era_name = config.fiscal_era_name.strip()
    era_romanized = config.fiscal_era_romanized.strip().lower()
    era_initial = config.fiscal_era_initial.strip().lower()
    if not era_name or not era_romanized or not era_initial:
        configure_japanese_eras(())
        return
    configure_japanese_eras(
        (
            JapaneseEra(
                name=era_name,
                romanized=era_romanized,
                initial=era_initial,
                start_fiscal_year=config.fiscal_era_start_year,
            ),
        )
    )


apply_fiscal_era_settings(settings)


def apply_runtime_env_settings(config: Settings = settings) -> None:
    """Mirror settings that legacy runtime helpers read from ``os.environ``."""
    env_updates = {
        "EIDP_OCR_AUTO_ENABLE": config.ocr_auto_enable,
        "EIDP_OCR_MIN_CPUS": str(config.ocr_min_cpus),
        "EIDP_OCR_MIN_FREE_RAM_MB": str(config.ocr_min_free_ram_mb),
        "EIDP_TESSERACT_BIN": config.tesseract_bin,
        "EIDP_OCR_PROVIDER": config.ocr_provider,
        "EIDP_OCR_DEVICE": config.ocr_device,
        "EIDP_SEARCH_PROVIDER": config.search_provider,
        "EIDP_URL_SEARCH_AUTO_ENABLE": config.url_search_auto_enable,
        "EIDP_URL_SEARCH_BATCH_SIZE": str(config.url_search_batch_size),
        "EIDP_SERPER_API_KEY": config.serper_api_key,
        "EIDP_BRAVE_API_KEY": config.brave_api_key,
        "EIDP_GOOGLE_API_KEY": config.google_api_key,
        "EIDP_GOOGLE_CX": config.google_cx,
        "EIDP_SCHOOL_URL_CRAWL_AUTO_ENABLE": config.school_url_crawl_auto_enable,
        "EIDP_SCHOOL_URL_CRAWL_BATCH_SIZE": str(config.school_url_crawl_batch_size),
        "EIDP_SCHOOL_URL_CRAWL_FETCH_MODE": config.school_url_crawl_fetch_mode,
        "EIDP_SCHOOL_URL_CRAWL_MIN_SECONDS_PER_DOMAIN": str(config.school_url_crawl_min_seconds_per_domain),
        "EIDP_SCHOOL_URL_CRAWL_MIN_JITTER": str(config.school_url_crawl_min_jitter),
        "EIDP_SCHOOL_URL_CRAWL_MAX_JITTER": str(config.school_url_crawl_max_jitter),
        "EIDP_PDF_DISCOVERY_RENDERED_HTML_AUTO_ENABLE": config.pdf_discovery_rendered_html_auto_enable,
        "EIDP_PDF_DISCOVERY_RENDERED_HTML_FETCH_MODE": config.pdf_discovery_rendered_html_fetch_mode,
        "EIDP_FIRECRAWL_API_KEY": config.firecrawl_api_key,
    }
    for key, value in env_updates.items():
        os.environ[key] = value


apply_runtime_env_settings(settings)
