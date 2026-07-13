from __future__ import annotations

import importlib.util
import runpy
import sys
import tomllib
from pathlib import Path

import pytest

from eidp import cli
from eidp.review import app as review_app


def test_console_script_targets_logging_wrapper() -> None:
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    assert pyproject["project"]["scripts"]["eidp"] == "eidp.cli:main"


def test_cli_main_configures_logging_before_invoking_typer(monkeypatch) -> None:
    events: list[str] = []

    monkeypatch.setattr(cli, "configure_logging", lambda: events.append("configure"))
    monkeypatch.setattr(cli, "app", lambda: events.append("app"))

    cli.main()

    assert events == ["configure", "app"]


def test_review_main_retires_before_configuring_logging_or_streamlit(monkeypatch) -> None:
    events: list[str] = []

    monkeypatch.setattr(review_app, "configure_logging", lambda: events.append("configure"), raising=False)
    monkeypatch.setattr(review_app.st, "set_page_config", lambda **_: events.append("page_config"))
    monkeypatch.setattr(review_app, "_get_session", lambda: events.append("session"))

    with pytest.raises(RuntimeError, match="Legacy review app is retired") as exc_info:
        review_app.main()

    message = str(exc_info.value)
    assert "deploy/linux/run_web.sh" in message
    assert "src/eidp/web/app.py" in message
    assert events == []


def test_direct_legacy_review_entrypoint_retires_before_logging_ui_or_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import eidp.db.session as db_session
    import eidp.logging_config as logging_config
    from eidp.review import operator_pages

    events: list[str] = []
    secret = "must-not-appear-proxy-secret"
    monkeypatch.setenv("EIDP_PROXY_SHARED_SECRET", secret)
    monkeypatch.setattr(logging_config, "configure_logging", lambda: events.append("configure"))
    monkeypatch.setattr(review_app.st, "set_page_config", lambda **_: events.append("page_config"))
    monkeypatch.setattr(review_app.st, "markdown", lambda *_, **__: events.append("markdown"))
    monkeypatch.setattr(operator_pages, "inject_v1_theme", lambda: events.append("theme"))
    monkeypatch.setattr(operator_pages, "render_sidebar_todo", lambda _: events.append("sidebar_todo"))
    monkeypatch.setattr(db_session, "SessionLocal", lambda: events.append("session"))

    with pytest.raises(RuntimeError, match="Legacy review app is retired") as exc_info:
        runpy.run_path("src/eidp/review/app.py", run_name="__main__")

    message = str(exc_info.value)
    assert "deploy/linux/run_web.sh" in message
    assert "src/eidp/web/app.py" in message
    assert secret not in message
    assert events == []


def test_weekly_runner_main_configures_logging_before_parse_args(monkeypatch) -> None:
    script = Path("scripts/run_weekly_target_year_discovery.py").resolve()
    spec = importlib.util.spec_from_file_location("weekly_runner_logging_contract", script)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules["weekly_runner_logging_contract"] = module
    spec.loader.exec_module(module)

    events: list[str] = []
    monkeypatch.setattr(module, "configure_logging", lambda *_, **__: events.append("configure"))
    monkeypatch.setattr(module, "parse_args", lambda: events.append("parse") or (_ for _ in ()).throw(SystemExit(0)))

    try:
        module.main()
    except SystemExit:
        pass

    assert events == ["configure", "parse"]
