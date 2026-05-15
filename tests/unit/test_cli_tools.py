from __future__ import annotations

import sys
from pathlib import Path

import eidp.cli_tools as cli_tools


def test_review_ui_binds_streamlit_to_localhost(monkeypatch) -> None:
    commands: list[list[str]] = []

    def fake_run(command: list[str], *, check: bool) -> None:
        commands.append(command)
        assert check is True

    monkeypatch.setattr(cli_tools.subprocess, "run", fake_run)

    cli_tools.review_ui(port=8765)

    assert commands == [
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            str(Path(cli_tools.__file__).parent / "review" / "app.py"),
            "--server.address",
            "127.0.0.1",
            "--server.port",
            "8765",
        ]
    ]


def test_operator_ui_binds_streamlit_to_localhost(monkeypatch) -> None:
    commands: list[list[str]] = []

    def fake_run(command: list[str], *, check: bool) -> None:
        commands.append(command)
        assert check is True

    monkeypatch.setattr(cli_tools.subprocess, "run", fake_run)

    cli_tools.operator_ui(port=8766)

    assert commands[0][0:6] == [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(Path(cli_tools.__file__).parent / "review" / "app.py"),
        "--server.address",
    ]
    assert commands[0][6:] == ["127.0.0.1", "--server.port", "8766"]
