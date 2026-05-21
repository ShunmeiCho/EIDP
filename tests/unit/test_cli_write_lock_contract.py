from __future__ import annotations

import ast
from pathlib import Path

CLI_SOURCES = (
    Path("src/eidp/cli.py"),
    Path("src/eidp/cli_discovery.py"),
    Path("src/eidp/cli_reports.py"),
    Path("src/eidp/cli_tools.py"),
)
EXPECTED_CLI_SOURCES = {
    Path("src/eidp/cli.py"),
    Path("src/eidp/cli_discovery.py"),
    Path("src/eidp/cli_reports.py"),
    Path("src/eidp/cli_tools.py"),
}
WRITE_HELPER_CALLS = frozenset(
    {
        "apply_prefecture_artifact",
        "backup_sqlite_database",
        "bootstrap_sqlite",
        "crawl_missing_school_urls",
        "create_review_items_for_documents",
        "discover_pdfs_for_sites",
        "discover_school_urls",
        "flush_audit_outbox",
        "import_excel_file",
        "ingest_documents",
        "populate_review_items",
        "rebuild_school_year_tasks",
        "reconcile_mext_rows",
        "run_firecrawl_discovery",
        "seed_discovery_gold_sites",
        "update_school_matches",
    }
)
READ_ONLY_SESSION_COMMANDS = frozenset(
    {
        "db_info",
        "discovery_rca_batch_plan",
        "discovery_rca_packet",
        "export_competition_excel",
        "export_excel",
        "report_coverage",
        "report_extraction",
        "report_gaps",
        "report_ship_readiness",
        "summarize_discovery_evidence",
        "verify_identity",
    }
)


def _is_typer_command(node: ast.FunctionDef) -> bool:
    for decorator in node.decorator_list:
        if not isinstance(decorator, ast.Call):
            continue
        func = decorator.func
        if not isinstance(func, ast.Attribute) or func.attr != "command":
            continue
        if isinstance(func.value, ast.Name) and func.value.id in {"app", "report_app"}:
            return True
    return False


def _registered_typer_command_names(module: ast.Module) -> set[str]:
    names: set[str] = set()
    for child in ast.walk(module):
        if not isinstance(child, ast.Call) or not isinstance(child.func, ast.Call):
            continue
        inner = child.func
        if not isinstance(inner.func, ast.Attribute) or inner.func.attr != "command":
            continue
        if child.args and isinstance(child.args[0], ast.Name):
            names.add(child.args[0].id)
    return names


def _typer_command_function_names(module: ast.Module) -> set[str]:
    decorated = {
        node.name
        for node in module.body
        if isinstance(node, ast.FunctionDef) and _is_typer_command(node)
    }
    return decorated | _registered_typer_command_names(module)


def _typer_command_functions(module: ast.Module) -> list[ast.FunctionDef]:
    command_names = _typer_command_function_names(module)
    return [
        node
        for node in module.body
        if isinstance(node, ast.FunctionDef) and node.name in command_names
    ]


def _calls_require_app_lock(node: ast.FunctionDef) -> bool:
    for child in ast.walk(node):
        if not isinstance(child, ast.Call):
            continue
        if _call_name(child.func) == "_require_app_lock":
            return True
    return False


def _call_name(func: ast.expr) -> str | None:
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _contains_db_write_call(node: ast.FunctionDef) -> bool:
    for child in ast.walk(node):
        if not isinstance(child, ast.Call):
            continue
        call_name = _call_name(child.func)
        if call_name == "commit":
            return True
        if call_name in WRITE_HELPER_CALLS:
            return True
    return False


def test_cli_write_lock_contract_scans_all_command_modules() -> None:
    assert set(CLI_SOURCES) == EXPECTED_CLI_SOURCES


def test_registered_cli_command_callbacks_are_classified_as_commands() -> None:
    discovery_module = ast.parse(Path("src/eidp/cli_discovery.py").read_text(encoding="utf-8"))
    tools_module = ast.parse(Path("src/eidp/cli_tools.py").read_text(encoding="utf-8"))

    assert "discovery_rca_packet" in _typer_command_function_names(discovery_module)
    assert "export_excel" in _typer_command_function_names(tools_module)


def test_attribute_write_helper_calls_are_classified_as_writes() -> None:
    module = ast.parse(
        """
def command():
    audit_outbox.flush_audit_outbox(session)
"""
    )
    node = module.body[0]
    assert isinstance(node, ast.FunctionDef)
    assert _contains_db_write_call(node)


def _calls_session_local(node: ast.FunctionDef) -> bool:
    for child in ast.walk(node):
        if not isinstance(child, ast.Call):
            continue
        if _call_name(child.func) == "SessionLocal":
            return True
    return False


def test_write_cli_commands_acquire_shared_app_lock() -> None:
    """Every Typer command that writes the DB must coordinate with the UI lock."""

    missing = [
        node.name
        for source in CLI_SOURCES
        for node in _typer_command_functions(ast.parse(source.read_text(encoding="utf-8")))
        if _contains_db_write_call(node)
        and not _calls_require_app_lock(node)
    ]

    assert missing == []


def test_session_cli_commands_are_classified_as_locked_write_or_read_only() -> None:
    """Future DB-backed CLI commands must not silently bypass lock review."""

    unclassified = [
        node.name
        for source in CLI_SOURCES
        for node in _typer_command_functions(ast.parse(source.read_text(encoding="utf-8")))
        if _calls_session_local(node)
        and not _calls_require_app_lock(node)
        and node.name not in READ_ONLY_SESSION_COMMANDS
    ]

    assert unclassified == []
