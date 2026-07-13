from __future__ import annotations

import subprocess

from typer.testing import CliRunner

from eidp.cli import app


def _assert_legacy_ui_command_is_retired(command: str, monkeypatch) -> None:  # noqa: ANN001
    subprocess_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def fake_run(*args: object, **kwargs: object) -> None:
        subprocess_calls.append((args, kwargs))

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = CliRunner().invoke(app, [command])

    assert result.exit_code == 2
    assert f"No such command '{command}'" in result.output
    assert subprocess_calls == []


def test_review_ui_is_unregistered_and_cannot_spawn_streamlit(monkeypatch) -> None:  # noqa: ANN001
    _assert_legacy_ui_command_is_retired("review-ui", monkeypatch)


def test_operator_ui_is_unregistered_and_cannot_spawn_streamlit(monkeypatch) -> None:  # noqa: ANN001
    _assert_legacy_ui_command_is_retired("operator-ui", monkeypatch)
