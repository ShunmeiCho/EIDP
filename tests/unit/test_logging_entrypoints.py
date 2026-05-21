from __future__ import annotations

import importlib.util
import sys
import tomllib
from pathlib import Path

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


def test_review_main_configures_logging_before_streamlit(monkeypatch) -> None:
    events: list[str] = []

    monkeypatch.setattr(review_app, "configure_logging", lambda: events.append("configure"))
    monkeypatch.setattr(review_app.st, "set_page_config", lambda **_: events.append("page_config"))
    monkeypatch.setattr(review_app.operator_pages, "inject_v1_theme", lambda: events.append("theme"))

    class FakeSidebar:
        def divider(self) -> None:
            pass

        def caption(self, _: str) -> None:
            pass

        def text_input(self, *args: object, **kwargs: object) -> str:
            return ""

    class FakeSession:
        def __enter__(self) -> FakeSession:
            return self

        def __exit__(self, *_: object) -> None:
            pass

    monkeypatch.setattr(review_app.st, "markdown", lambda *_, **__: None)
    monkeypatch.setattr(review_app, "_get_session", lambda: FakeSession())
    monkeypatch.setattr(review_app.operator_pages, "render_sidebar_todo", lambda _: None)
    monkeypatch.setattr(review_app, "_render_sidebar_navigation", lambda: review_app.PAGE_GAPS)
    monkeypatch.setattr(review_app.operator_pages, "page_gap_report", lambda: None)
    monkeypatch.setattr(review_app.st, "sidebar", FakeSidebar())
    monkeypatch.setattr(review_app, "_build_info_caption", lambda _: "build: test")

    review_app.main()

    assert events[:2] == ["configure", "page_config"]


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
