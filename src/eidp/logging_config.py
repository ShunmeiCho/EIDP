"""Structured logging setup for CLI, Streamlit, and scheduled runs."""

from __future__ import annotations

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Final

import structlog
from structlog.typing import Processor

DEFAULT_LOG_FILENAME: Final = "eidp.jsonl"
DEFAULT_MAX_BYTES: Final = 10 * 1024 * 1024
DEFAULT_BACKUP_COUNT: Final = 12
_HANDLER_MARKER: Final = "_eidp_managed_logging_handler"

_configured_signature: tuple[str, int] | None = None


def _level_number(level: str | int | None) -> int:
    if isinstance(level, int):
        return level
    if level:
        value = logging.getLevelName(level.upper())
        if isinstance(value, int):
            return value
    return logging.INFO


def _configured_level(level: str | int | None) -> str | int:
    if level is not None:
        return level
    if env_level := os.environ.get("EIDP_LOG_LEVEL"):
        return env_level

    from eidp.config import settings

    return settings.log_level


def _remove_managed_handlers(logger: logging.Logger) -> None:
    for handler in list(logger.handlers):
        if bool(getattr(handler, _HANDLER_MARKER, False)):
            logger.removeHandler(handler)
            handler.close()


def _managed_formatter() -> logging.Formatter:
    return structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=[
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
        ],
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.JSONRenderer(ensure_ascii=False, sort_keys=True),
        ],
    )


def _mark_managed(handler: logging.Handler) -> logging.Handler:
    setattr(handler, _HANDLER_MARKER, True)
    return handler


def _configure_structlog(level: int) -> None:
    processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
    ]
    logging.getLogger().setLevel(level)
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def default_log_path(app_root: Path | None = None) -> Path:
    """Return the default structured log file under the configured app root."""
    if app_root is not None:
        root = app_root
    else:
        from eidp.config import settings

        root = Path(settings.app_root)
    return root / "logs" / DEFAULT_LOG_FILENAME


def configure_logging(
    *,
    app_root: Path | None = None,
    log_path: Path | None = None,
    level: str | int | None = None,
) -> Path:
    """Configure structlog and stdlib logging once for operator evidence.

    Logs are emitted as JSON lines to ``logs/eidp.jsonl`` with a 10 MB x 12
    rotating file policy. A stderr handler uses the same JSON renderer so
    ``weekly_run.bat`` still captures structured events in its per-day log.
    """
    global _configured_signature

    resolved_log_path = (log_path or default_log_path(app_root)).expanduser().resolve()
    resolved_level = _level_number(_configured_level(level))
    signature = (str(resolved_log_path), resolved_level)

    root_logger = logging.getLogger()
    if _configured_signature == signature and any(
        bool(getattr(handler, _HANDLER_MARKER, False)) for handler in root_logger.handlers
    ):
        return resolved_log_path

    _remove_managed_handlers(root_logger)
    resolved_log_path.parent.mkdir(parents=True, exist_ok=True)

    file_handler = _mark_managed(
        RotatingFileHandler(
            resolved_log_path,
            maxBytes=DEFAULT_MAX_BYTES,
            backupCount=DEFAULT_BACKUP_COUNT,
            encoding="utf-8",
        )
    )
    file_handler.setLevel(resolved_level)
    file_handler.setFormatter(_managed_formatter())

    stream_handler = _mark_managed(logging.StreamHandler(sys.stderr))
    stream_handler.setLevel(resolved_level)
    stream_handler.setFormatter(_managed_formatter())

    root_logger.addHandler(file_handler)
    root_logger.addHandler(stream_handler)
    _configure_structlog(resolved_level)
    _configured_signature = signature
    return resolved_log_path


def reset_logging_for_tests() -> None:
    """Remove EIDP-managed handlers so tests do not keep temp files open."""
    global _configured_signature

    _remove_managed_handlers(logging.getLogger())
    structlog.reset_defaults()
    _configured_signature = None
