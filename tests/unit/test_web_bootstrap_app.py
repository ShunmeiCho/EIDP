"""Streamlit identity bootstrap and entrypoint wiring contracts."""

from __future__ import annotations

import importlib
import inspect
import runpy
from pathlib import Path
from typing import Any, Literal

import pytest
from streamlit.testing.v1 import AppTest
from structlog.testing import capture_logs

from eidp.config import Settings
from eidp.identity import IdentitySource, ResolvedIdentity

REPO_ROOT = Path(__file__).resolve().parents[2]
GENERIC_REJECTION_MESSAGE = "This EIDP request cannot be authenticated."
PAGE_ENTRYPOINTS = [
    ("01_pdf_intake.py", "eidp.web.pages.pdf_intake", "render_pdf_intake_page"),
    ("02_extraction_queue.py", "eidp.web.pages.extraction_queue", "render_extraction_queue_page"),
    ("03_extraction_review.py", "eidp.web.pages.extraction_review", "render_extraction_review_page"),
    ("04_review_diff.py", "eidp.web.pages.review_diff", "render_review_diff_page"),
    ("05_double_check.py", "eidp.web.pages.double_check", "render_double_check_page"),
]


def _render_bootstrap_for_test() -> None:
    import streamlit as st

    import eidp.web.bootstrap as bootstrap_module

    identity = bootstrap_module.bootstrap_web_request()
    st.success(f"body:{identity.actor}:{identity.source.value}")


def _run_bootstrap_app(config: Settings) -> AppTest:
    import eidp.web.bootstrap as bootstrap_module

    original_settings = bootstrap_module.settings
    bootstrap_module.settings = config
    try:
        return AppTest.from_function(_render_bootstrap_for_test).run(timeout=5)
    finally:
        bootstrap_module.settings = original_settings


def _identity_settings(
    *,
    mode: Literal["trusted_proxy", "configured_fallback"],
    fallback_actor: str = "operator",
    proxy_shared_secret: str = "",
) -> Settings:
    return Settings(
        identity_mode=mode,
        fallback_actor=fallback_actor,
        proxy_shared_secret=proxy_shared_secret,
        _env_file=None,
        _env_prefix="TEST_EIDP_",
    )


def test_missing_trusted_startup_config_renders_only_generic_rejection() -> None:
    app = _run_bootstrap_app(_identity_settings(mode="trusted_proxy"))

    assert not app.exception
    assert [error.value for error in app.error] == [GENERIC_REJECTION_MESSAGE]
    assert not app.success


def test_invalid_trusted_request_does_not_leak_configured_secret_to_ui() -> None:
    configured_secret = "must-never-appear-in-ui"
    app = _run_bootstrap_app(
        _identity_settings(
            mode="trusted_proxy",
            proxy_shared_secret=configured_secret,
        )
    )

    assert not app.exception
    assert [error.value for error in app.error] == [GENERIC_REJECTION_MESSAGE]
    assert configured_secret not in str(app)
    assert not app.success


def test_invalid_trusted_request_logs_only_generic_event_without_secret() -> None:
    configured_secret = "must-never-appear-in-logs"

    with capture_logs() as logs:
        app = _run_bootstrap_app(
            _identity_settings(
                mode="trusted_proxy",
                proxy_shared_secret=configured_secret,
            )
        )

    assert not app.exception
    assert [event["event"] for event in logs] == ["web_request_identity_rejected"]
    assert configured_secret not in str(logs)


def test_fallback_bootstrap_reaches_body_with_configured_identity() -> None:
    app = _run_bootstrap_app(
        _identity_settings(
            mode="configured_fallback",
            fallback_actor="pilot-operator",
        )
    )

    assert not app.exception
    assert not app.error
    assert [message.value for message in app.success] == [
        "body:pilot-operator:configured_fallback"
    ]


@pytest.mark.parametrize(("filename", "body_module_name", "render_name"), PAGE_ENTRYPOINTS)
def test_direct_multipage_entry_bootstraps_once_and_passes_same_typed_identity(
    monkeypatch: pytest.MonkeyPatch,
    filename: str,
    body_module_name: str,
    render_name: str,
) -> None:
    bootstrap_module = importlib.import_module("eidp.web.bootstrap")
    body_module = importlib.import_module(body_module_name)
    identity = ResolvedIdentity("entry-user", IdentitySource.TRUSTED_PROXY)
    bootstrap_calls: list[None] = []
    received: list[ResolvedIdentity] = []

    def fake_bootstrap() -> ResolvedIdentity:
        bootstrap_calls.append(None)
        return identity

    def fake_render(*, identity: ResolvedIdentity, **_kwargs: Any) -> None:
        received.append(identity)

    monkeypatch.setattr(bootstrap_module, "bootstrap_web_request", fake_bootstrap)
    monkeypatch.setattr(body_module, render_name, fake_render)

    runpy.run_path(
        str(REPO_ROOT / "src" / "eidp" / "web" / "pages" / filename),
        run_name="__main__",
    )

    assert bootstrap_calls == [None]
    assert received == [identity]
    assert received[0] is identity


def test_root_app_bootstraps_once_and_passes_same_typed_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    import streamlit as st

    import eidp.logging_config as logging_config_module
    import eidp.web.bootstrap as bootstrap_module
    import eidp.web.pages.pdf_intake as body_module

    identity = ResolvedIdentity("root-user", IdentitySource.TRUSTED_PROXY)
    bootstrap_calls: list[None] = []
    received: list[ResolvedIdentity] = []

    def fake_bootstrap() -> ResolvedIdentity:
        bootstrap_calls.append(None)
        return identity

    def fake_render(*, identity: ResolvedIdentity, **_kwargs: Any) -> None:
        received.append(identity)

    monkeypatch.setattr(bootstrap_module, "bootstrap_web_request", fake_bootstrap)
    monkeypatch.setattr(body_module, "render_pdf_intake_page", fake_render)
    monkeypatch.setattr(logging_config_module, "configure_logging", lambda **_kwargs: None)
    monkeypatch.setattr(st, "set_page_config", lambda **_kwargs: None)

    runpy.run_path(str(REPO_ROOT / "src" / "eidp" / "web" / "app.py"), run_name="__main__")

    assert bootstrap_calls == [None]
    assert received == [identity]
    assert received[0] is identity


@pytest.mark.parametrize(("_filename", "body_module_name", "render_name"), PAGE_ENTRYPOINTS)
def test_page_body_requires_keyword_only_typed_identity(
    _filename: str,
    body_module_name: str,
    render_name: str,
) -> None:
    render = getattr(importlib.import_module(body_module_name), render_name)
    parameter = inspect.signature(render).parameters["identity"]

    assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
    assert parameter.default is inspect.Parameter.empty
    assert parameter.annotation in {ResolvedIdentity, "ResolvedIdentity"}
