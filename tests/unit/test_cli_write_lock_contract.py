from __future__ import annotations

import ast
from pathlib import Path

CLI_SOURCE = Path("src/eidp/cli.py")
WRITE_HELPER_CALLS = frozenset(
    {
        "apply_prefecture_artifact",
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


def _calls_require_app_lock(node: ast.FunctionDef) -> bool:
    for child in ast.walk(node):
        if not isinstance(child, ast.Call):
            continue
        func = child.func
        if isinstance(func, ast.Name) and func.id == "_require_app_lock":
            return True
    return False


def _contains_db_write_call(node: ast.FunctionDef) -> bool:
    for child in ast.walk(node):
        if not isinstance(child, ast.Call):
            continue
        func = child.func
        if isinstance(func, ast.Attribute) and func.attr == "commit":
            return True
        if isinstance(func, ast.Name) and func.id in WRITE_HELPER_CALLS:
            return True
    return False


def _calls_session_local(node: ast.FunctionDef) -> bool:
    for child in ast.walk(node):
        if not isinstance(child, ast.Call):
            continue
        func = child.func
        if isinstance(func, ast.Name) and func.id == "SessionLocal":
            return True
    return False


def test_write_cli_commands_acquire_shared_app_lock() -> None:
    """Every Typer command that writes the DB must coordinate with the UI lock."""

    module = ast.parse(CLI_SOURCE.read_text(encoding="utf-8"))
    missing = [
        node.name
        for node in module.body
        if isinstance(node, ast.FunctionDef)
        and _is_typer_command(node)
        and _contains_db_write_call(node)
        and not _calls_require_app_lock(node)
    ]

    assert missing == []


def test_session_cli_commands_are_classified_as_locked_write_or_read_only() -> None:
    """Future DB-backed CLI commands must not silently bypass lock review."""

    module = ast.parse(CLI_SOURCE.read_text(encoding="utf-8"))
    unclassified = [
        node.name
        for node in module.body
        if isinstance(node, ast.FunctionDef)
        and _is_typer_command(node)
        and _calls_session_local(node)
        and not _calls_require_app_lock(node)
        and node.name not in READ_ONLY_SESSION_COMMANDS
    ]

    assert unclassified == []
