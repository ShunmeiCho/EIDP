"""Tests for silent-failure replacement in operator-facing UI (P0).

Each previously bare ``except Exception: ...`` site should now surface a
user-visible message and emit ``log.exception`` so we can find it in
structured logs / silent-failure audits (G5).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest


class FakeStreamlit:
    def __init__(self) -> None:
        self.calls: list[tuple[str, Any]] = []

    def warning(self, value: str, **kwargs: Any) -> None:
        self.calls.append(("warning", value))

    def error(self, value: str, **kwargs: Any) -> None:
        self.calls.append(("error", value))

    def caption(self, value: str, **kwargs: Any) -> None:
        self.calls.append(("caption", value))

    def columns(self, _spec: Any) -> Any:  # pragma: no cover - unused here
        raise AssertionError("columns should not be called when scan raises")


class FakeLogger:
    def __init__(self) -> None:
        self.exception_calls: list[tuple[str, dict[str, Any]]] = []

    def exception(self, event: str, **kwargs: Any) -> None:
        self.exception_calls.append((event, kwargs))


def test_render_bug_signal_banner_logs_and_warns_when_scan_raises(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    """FIX 1 (P0-1): scan failure must surface to operator and to logs."""
    from eidp.bug_signals import detector as detector_mod
    from eidp.review import app as review_app

    fake_st = FakeStreamlit()
    fake_log = FakeLogger()

    def raising_scan(_root: Path, *, check_sqlite: bool = True) -> list[Any]:
        raise RuntimeError("simulated scan failure")

    monkeypatch.setattr(detector_mod, "scan_bug_signals", raising_scan)
    monkeypatch.setattr(review_app, "st", fake_st)
    monkeypatch.setattr(review_app, "log", fake_log)

    # Must return without raising (early return semantics preserved).
    review_app._render_bug_signal_banner(tmp_path)

    assert any(name == "warning" for name, _ in fake_st.calls), fake_st.calls
    assert fake_log.exception_calls, "log.exception must be emitted"
    event, kwargs = fake_log.exception_calls[0]
    assert event == "bug_signal_scan_failed"
    assert kwargs.get("error_type") == "RuntimeError"


def test_safe_compute_todo_counts_logs_and_returns_error_label(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FIX 2 (P0-2): compute_todo_counts failure becomes (None, error_label)."""
    from eidp.review import operator_pages

    fake_log = FakeLogger()

    def raising_compute(_session: Any) -> Any:
        raise ValueError("boom")

    monkeypatch.setattr(operator_pages, "compute_todo_counts", raising_compute)
    monkeypatch.setattr(operator_pages, "log", fake_log)

    value, err = operator_pages.safe_compute_todo_counts(session=object())

    assert value is None
    assert err == "ValueError"
    assert fake_log.exception_calls
    assert fake_log.exception_calls[0][0] == "todo_counts_failed"


def test_safe_compute_todo_counts_passes_through_on_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from eidp.review import operator_pages

    sentinel = object()
    monkeypatch.setattr(
        operator_pages, "compute_todo_counts", lambda _session: sentinel,
    )

    value, err = operator_pages.safe_compute_todo_counts(session=object())

    assert value is sentinel
    assert err is None


def test_safe_school_task_summary_logs_and_returns_error_label(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FIX 3 (P0-3): sidebar school_task_summary failure must log + return error label."""
    from eidp.review import operator_pages

    fake_log = FakeLogger()

    def raising_summary(*_args: Any, **_kwargs: Any) -> Any:
        raise KeyError("fy")

    # The page-level module attribute is what the helper imports lazily; we patch
    # the source so the lazy import resolves to the raising stub.
    from eidp.review._pages import school_year_tasks as syt
    monkeypatch.setattr(syt, "school_task_summary", raising_summary)
    monkeypatch.setattr(operator_pages, "log", fake_log)

    value, err = operator_pages.safe_school_task_summary(
        session=object(), fiscal_year=2025, school_type="専門学校",
    )

    assert value is None
    assert err == "KeyError"
    assert fake_log.exception_calls
    assert fake_log.exception_calls[0][0] == "sidebar_school_task_summary_failed"


def test_safe_school_task_summary_passes_through_on_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from eidp.review import operator_pages
    from eidp.review._pages import school_year_tasks as syt

    sentinel = object()
    monkeypatch.setattr(
        syt, "school_task_summary",
        lambda _s, *, fiscal_year, school_type: sentinel,
    )

    value, err = operator_pages.safe_school_task_summary(
        session=object(), fiscal_year=2025, school_type="専門学校",
    )

    assert value is sentinel
    assert err is None
