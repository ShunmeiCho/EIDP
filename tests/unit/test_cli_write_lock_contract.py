from __future__ import annotations

import ast
from pathlib import Path

CLI_SOURCE = Path("src/eidp/cli.py")


def _function_node(module: ast.Module, name: str) -> ast.FunctionDef:
    for node in module.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"missing function: {name}")


def _calls_require_app_lock(node: ast.FunctionDef) -> bool:
    for child in ast.walk(node):
        if not isinstance(child, ast.Call):
            continue
        func = child.func
        if isinstance(func, ast.Name) and func.id == "_require_app_lock":
            return True
    return False


def test_write_cli_commands_acquire_shared_app_lock() -> None:
    """All operator-facing write commands must coordinate with the UI lock."""

    module = ast.parse(CLI_SOURCE.read_text(encoding="utf-8"))
    for name in (
        "import_excel",
        "db_bootstrap",
        "rebuild_school_year_tasks",
        "weekly_update",
    ):
        assert _calls_require_app_lock(_function_node(module, name)), name
