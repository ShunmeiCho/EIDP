from __future__ import annotations

import json
import logging
from pathlib import Path

import structlog

from eidp.logging_config import configure_logging, reset_logging_for_tests


def _flush_root_handlers() -> None:
    for handler in logging.getLogger().handlers:
        handler.flush()


def teardown_function() -> None:
    reset_logging_for_tests()


def test_configure_logging_writes_structlog_jsonl(tmp_path: Path) -> None:
    log_path = tmp_path / "logs" / "eidp.jsonl"

    configured_path = configure_logging(log_path=log_path)
    structlog.get_logger("eidp.test").info("stage6_probe", answer=42)
    _flush_root_handlers()

    assert configured_path == log_path
    payload = json.loads(log_path.read_text(encoding="utf-8").splitlines()[0])
    assert payload["event"] == "stage6_probe"
    assert payload["answer"] == 42
    assert payload["level"] == "info"
    assert payload["logger"] == "eidp.test"
    assert "timestamp" in payload


def test_configure_logging_formats_stdlib_records_as_jsonl(tmp_path: Path) -> None:
    log_path = tmp_path / "logs" / "eidp.jsonl"

    configure_logging(log_path=log_path)
    logging.getLogger("eidp.stdlib").warning("stdlib_probe")
    _flush_root_handlers()

    payload = json.loads(log_path.read_text(encoding="utf-8").splitlines()[0])
    assert payload["event"] == "stdlib_probe"
    assert payload["level"] == "warning"
    assert payload["logger"] == "eidp.stdlib"


def test_configure_logging_is_idempotent_for_same_target(tmp_path: Path) -> None:
    log_path = tmp_path / "logs" / "eidp.jsonl"

    configure_logging(log_path=log_path)
    configure_logging(log_path=log_path)
    structlog.get_logger("eidp.test").info("once")
    _flush_root_handlers()

    assert len(log_path.read_text(encoding="utf-8").splitlines()) == 1


def test_configure_logging_defaults_under_app_root(tmp_path: Path) -> None:
    configured_path = configure_logging(app_root=tmp_path)

    assert configured_path == tmp_path / "logs" / "eidp.jsonl"
