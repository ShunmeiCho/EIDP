"""Validate an extracted EIDP Windows install directory.

This script is for the Windows VM / operator-PC gates after ZIP extraction.
It checks the evidence that should exist after setup and optionally after a
weekly run. It does not execute Windows binaries unless an explicit runtime
smoke flag is used.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ship_gate_contract import (
    BOOTSTRAP_SHIP_GATE_METRIC_BASIS,
    SHIP_GATE_OPERATOR_COVERAGE_PCT,
    SHIP_GATE_STATUSES,
    WEEKLY_SHIP_GATE_METRIC_BASIS,
    ship_gate_status_from_yield,
)


@dataclass
class InstallCheck:
    app_root: Path
    ok: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)

    def fail(self, message: str) -> None:
        self.ok = False
        self.errors.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)


CORE_FILES = (
    "BUILD_INFO.json",
    ".streamlit/config.toml",
    "EIDP-setup.bat",
    "EIDP-start.bat",
    "EIDP-diagnose.bat",
    "scripts/first_setup.bat",
    "scripts/launch.bat",
    "scripts/weekly_run.bat",
    "scripts/diagnose.bat",
    "scripts/uninstall.bat",
    "scripts/validate_install.bat",
    "scripts/offline_pip_install.py",
    "scripts/run_weekly_target_year_discovery.py",
    "scripts/run_r8_rediscovery_weekly.py",
    "scripts/bootstrap_pdf_pipeline.py",
    "scripts/ship_gate_contract.py",
    "scripts/download_prefecture_artifacts.py",
    "src/eidp/windows_platform.py",
    "src/sitecustomize.py",
    "runtime/python/python.exe",
    "runtime/uv.exe",
    "requirements-windows.txt",
    "alembic.ini",
    "docs/runbooks/eidp-windows.md",
    "data/prefecture-aggregators/seed.csv",
    "data/url-discovery/discovered-urls-50.csv",
    "data/url-discovery/corporation_domains.csv",
    "src/eidp/review/app.py",
    "src/eidp/review/operator_pages.py",
    "src/eidp/review/_pages/audit_log.py",
    "src/eidp/review/_pages/excel_preview.py",
    "src/eidp/review/_pages/fiscal_year_override.py",
    "src/eidp/review/_pages/pdf_manual_entry.py",
    "src/eidp/review/_pages/prefecture_remarks.py",
    "src/eidp/review/_pages/school_year_tasks.py",
    "src/eidp/review/_pages/settings_page.py",
)

CORE_DIRS = (
    "src/eidp",
    "migrations",
    "wheelhouse",
)

SETUP_FILES = (
    ".venv/Scripts/python.exe",
    "data/eidp.sqlite3",
)
OPERATOR_REVIEWABLE_PDF_STATUSES = frozenset({"publication_lag", "target_year_unverified"})

SETUP_DIRS = (
    "data",
    "data/pdfs",
    "data/output",
    "data/audit",
    "logs",
)

LAST_RUN_REQUIRED_KEYS = (
    "status",
    "run_id",
    "started_at",
    "finished_at",
    "current_fy",
    "selection_mode",
    "target_missing_school_count",
    "new_document_count",
    "target_pdf_auto_acquired_count",
    "target_pdf_auto_denominator_count",
    "target_pdf_auto_denominator_scope",
    "target_pdf_auto_yield_pct",
    "operator_reviewable_count",
    "operator_reviewable_yield_pct",
    "ship_gate_auto_yield_pct",
    "ship_gate_operator_coverage_pct",
    "ship_gate_metric_basis",
    "ship_gate_status",
    "discovery_stats",
    "ingest_stats",
)

SQLITE_REQUIRED_TABLES = (
    "school",
    "school_site",
    "document",
    "department",
    "department_change",
    "department_yearly",
    "review_item",
    "support_recipient",
    "school_fiscal_year_status",
    "manual_action_log",
)

SQLITE_DEPARTMENT_CHANGE_VOID_COLUMNS = (
    "voided",
    "voided_at",
    "voided_by",
    "void_reason",
)

TARGET_FY_SCHOOL_TYPE = "専門学校"

BUILD_INFO_REQUIRED_KEYS = (
    "app",
    "built_at_utc",
    "git_commit",
    "git_branch",
    "git_dirty",
)

def _posix_rel(path: str) -> Path:
    return Path(*path.split("/"))


def _exists_file(root: Path, rel: str) -> bool:
    return (root / _posix_rel(rel)).is_file()


def _exists_dir(root: Path, rel: str) -> bool:
    return (root / _posix_rel(rel)).is_dir()


def _count_wheels(root: Path) -> int:
    wheelhouse = root / "wheelhouse"
    if not wheelhouse.is_dir():
        return 0
    return len(list(wheelhouse.glob("*.whl")))


def _duplicate_wheel_distributions(root: Path) -> dict[str, list[str]]:
    wheelhouse = root / "wheelhouse"
    if not wheelhouse.is_dir():
        return {}
    by_distribution: dict[str, list[str]] = {}
    for wheel in sorted(wheelhouse.glob("*.whl")):
        distribution = wheel.name.split("-", 1)[0].lower().replace("_", "-")
        by_distribution.setdefault(distribution, []).append(wheel.name)
    return {
        distribution: wheels
        for distribution, wheels in by_distribution.items()
        if len(wheels) > 1
    }


def _validate_build_info(check: InstallCheck, path: Path) -> None:
    if not path.is_file():
        return
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        check.fail(f"BUILD_INFO.json is not readable UTF-8 JSON: {exc}")
        return
    if not isinstance(payload, dict):
        check.fail("BUILD_INFO.json must contain a JSON object")
        return

    for key in BUILD_INFO_REQUIRED_KEYS:
        value = payload.get(key)
        if not isinstance(value, str) or not value:
            check.fail(f"BUILD_INFO.json missing string field: {key}")

    if payload.get("app") != "EIDP":
        check.fail("BUILD_INFO.json app must be EIDP")
    commit = payload.get("git_commit")
    if isinstance(commit, str) and commit != "unknown" and len(commit) != 40:
        check.fail("BUILD_INFO.json git_commit must be a full 40-character commit hash or unknown")
    if payload.get("git_dirty") != "false":
        check.fail("BUILD_INFO.json git_dirty must be false")

    check.details["build_commit"] = payload.get("git_commit")
    check.details["build_branch"] = payload.get("git_branch")
    check.details["build_dirty"] = payload.get("git_dirty")
    check.details["built_at_utc"] = payload.get("built_at_utc")


def _load_last_run(check: InstallCheck, path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        check.fail("missing data/output/last_run.json")
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        check.fail(f"last_run.json is not readable UTF-8 JSON: {exc}")
        return None
    if not isinstance(payload, dict):
        check.fail("last_run.json must contain a JSON object")
        return None
    return payload


def _resolve_install_path(root: Path, raw_path: str) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        return path
    parts = [part for part in raw_path.replace("\\", "/").split("/") if part]
    return root.joinpath(*parts)


def _validate_rca_batch_plan_file(
    check: InstallCheck,
    root: Path,
    *,
    raw_path: str,
    expected_items: object,
    error_prefix: str,
) -> None:
    if not raw_path:
        return

    plan_path = _resolve_install_path(root, raw_path)
    check.details[f"{error_prefix}_batch_plan_path"] = str(plan_path)
    if not plan_path.is_file():
        check.fail(f"{error_prefix} batch plan is missing: {raw_path}")
        return
    try:
        payload = json.loads(plan_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        check.fail(f"{error_prefix} batch plan is not readable UTF-8 JSON: {exc}")
        return
    if not isinstance(payload, dict):
        check.fail(f"{error_prefix} batch plan must contain a JSON object")
        return
    items = payload.get("items")
    if not isinstance(items, list):
        check.fail(f"{error_prefix} batch plan items must be a list")
        return
    total_candidates = payload.get("total_candidates")
    check.details[f"{error_prefix}_batch_plan_item_count"] = len(items)
    if isinstance(total_candidates, int):
        check.details[f"{error_prefix}_batch_plan_total_candidates"] = total_candidates
    if isinstance(expected_items, int) and expected_items != len(items):
        check.fail(
            f"{error_prefix}.batch_plan_item_count does not match batch plan items: "
            f"{expected_items} != {len(items)}"
        )


def _validate_discovery_rca_batch_plan(
    check: InstallCheck,
    root: Path,
    discovery_rca: object,
) -> None:
    if not isinstance(discovery_rca, dict):
        return
    raw_path = str(discovery_rca.get("batch_plan_path") or "")
    if not raw_path:
        return
    _validate_rca_batch_plan_file(
        check,
        root,
        raw_path=raw_path,
        expected_items=discovery_rca.get("batch_plan_item_count"),
        error_prefix="discovery_rca",
    )


def _current_fiscal_year() -> int:
    now = datetime.now()
    return now.year if now.month >= 4 else now.year - 1


def _coerce_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None


def _target_fiscal_year_from_env(root: Path) -> int | None:
    env_path = root / ".env"
    if not env_path.is_file():
        return None
    try:
        lines = env_path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return None
    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, raw_value = line.split("=", 1)
        if key.strip() != "EIDP_TARGET_FISCAL_YEAR":
            continue
        return _coerce_int(raw_value.strip().strip("'\""))
    return None


def _resolve_target_fiscal_year(root: Path, *candidates: object) -> int:
    for candidate in candidates:
        value = _coerce_int(candidate)
        if value is not None:
            return value
    return _target_fiscal_year_from_env(root) or _current_fiscal_year()


def _sqlite_target_fy_coverage(
    check: InstallCheck,
    root: Path,
    fiscal_year: int,
) -> dict[str, int | float | None] | None:
    db_path = root / "data" / "eidp.sqlite3"
    if not db_path.is_file():
        check.fail("missing setup file: data/eidp.sqlite3")
        return None
    try:
        with sqlite3.connect(db_path) as conn:
            school_count = int(
                conn.execute(
                    "SELECT COUNT(*) FROM school WHERE status = 'active' AND school_type = ?",
                    (TARGET_FY_SCHOOL_TYPE,),
                ).fetchone()[0]
                or 0
            )
            target_pdf_school_count = int(
                conn.execute(
                    """
                    SELECT COUNT(DISTINCT school.id)
                    FROM school
                    JOIN document ON document.school_id = school.id
                    WHERE school.status = 'active'
                      AND school.school_type = ?
                      AND document.fiscal_year = ?
                      AND document.ingest_status = 'ingested'
                      AND document.pdf_type = 'target'
                    """,
                    (TARGET_FY_SCHOOL_TYPE, fiscal_year),
                ).fetchone()[0]
                or 0
            )
            operator_reviewable_school_count = int(
                conn.execute(
                    """
                    SELECT COUNT(DISTINCT school_id)
                    FROM (
                        SELECT school.id AS school_id
                        FROM school
                        JOIN document ON document.school_id = school.id
                        WHERE school.status = 'active'
                          AND school.school_type = ?
                          AND document.fiscal_year = ?
                          AND document.ingest_status = 'ingested'
                          AND document.pdf_type = 'target'
                        UNION
                        SELECT school.id AS school_id
                        FROM school
                        JOIN school_fiscal_year_status AS status
                          ON status.school_id = school.id
                         AND status.fiscal_year = ?
                        WHERE school.status = 'active'
                          AND school.school_type = ?
                          AND status.pdf_status IN ('publication_lag', 'target_year_unverified')
                    )
                    """,
                    (TARGET_FY_SCHOOL_TYPE, fiscal_year, fiscal_year, TARGET_FY_SCHOOL_TYPE),
                ).fetchone()[0]
                or 0
            )
    except sqlite3.Error as exc:
        check.fail(f"data/eidp.sqlite3 cannot compute target-FY coverage: {exc}")
        return None

    yield_pct = round(target_pdf_school_count / school_count * 100.0, 1) if school_count else None
    operator_reviewable_yield_pct = (
        round(operator_reviewable_school_count / school_count * 100.0, 1) if school_count else None
    )
    coverage = {
        "fiscal_year": fiscal_year,
        "schools_total": school_count,
        "schools_with_target_pdf_current_fy": target_pdf_school_count,
        "operator_reviewable_school_count": operator_reviewable_school_count,
        "yield_pct": yield_pct,
        "operator_reviewable_yield_pct": operator_reviewable_yield_pct,
    }
    check.details["sqlite_target_fy"] = fiscal_year
    check.details["sqlite_target_fy_school_type"] = TARGET_FY_SCHOOL_TYPE
    check.details["sqlite_target_fy_specialty_school_count"] = school_count
    check.details["sqlite_target_fy_target_pdf_school_count"] = target_pdf_school_count
    check.details["sqlite_target_fy_yield_pct"] = yield_pct
    check.details["sqlite_target_fy_operator_reviewable_school_count"] = operator_reviewable_school_count
    check.details["sqlite_target_fy_operator_reviewable_yield_pct"] = operator_reviewable_yield_pct
    return coverage


def _validate_bootstrap_ship_gate_against_sqlite(
    check: InstallCheck,
    root: Path,
    details: dict[str, Any],
    *,
    require_ship_gate: bool,
) -> None:
    fiscal_year = _resolve_target_fiscal_year(root, details.get("current_fy"))
    coverage = _sqlite_target_fy_coverage(check, root, fiscal_year)
    if coverage is None:
        return

    reported_denominator = details.get("target_pdf_auto_denominator_count")
    reported_acquired = details.get("target_pdf_auto_acquired_count")
    if isinstance(reported_denominator, int) and reported_denominator != coverage["schools_total"]:
        check.warn(
            "bootstrap target_pdf_auto_denominator_count does not match SQLite active specialty school count: "
            f"{reported_denominator} != {coverage['schools_total']}"
        )
    if isinstance(reported_acquired, int) and reported_acquired != coverage["schools_with_target_pdf_current_fy"]:
        check.warn(
            "bootstrap target_pdf_auto_acquired_count does not match SQLite target-FY target PDF count: "
            f"{reported_acquired} != {coverage['schools_with_target_pdf_current_fy']}"
        )
    reported_reviewable = details.get("operator_reviewable_count")
    if isinstance(reported_reviewable, int) and reported_reviewable != coverage["operator_reviewable_school_count"]:
        check.warn(
            "bootstrap operator_reviewable_count does not match SQLite operator-reviewable count: "
            f"{reported_reviewable} != {coverage['operator_reviewable_school_count']}"
        )

    sqlite_status = ship_gate_status_from_yield(coverage["operator_reviewable_yield_pct"])
    check.details["sqlite_target_fy_operator_reviewable_ship_gate_status"] = sqlite_status
    if require_ship_gate and sqlite_status != "pass":
        check.fail(
            "bootstrap ship_gate_status pass does not match SQLite operator-reviewable coverage: "
            f"{coverage['operator_reviewable_school_count']}/{coverage['schools_total']} "
            f"({coverage['operator_reviewable_yield_pct']}%, gate={SHIP_GATE_OPERATOR_COVERAGE_PCT}%)"
        )


def _load_json_file(check: InstallCheck, path: Path, *, label: str) -> dict[str, Any] | None:
    if not path.is_file():
        check.fail(f"{label} is missing: {path}")
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        check.fail(f"{label} is not readable UTF-8 JSON: {exc}")
        return None
    if not isinstance(payload, dict):
        check.fail(f"{label} must contain a JSON object")
        return None
    return payload


def _validate_weekly_ship_gate_against_sqlite(
    check: InstallCheck,
    root: Path,
    last_run: dict[str, Any],
    *,
    require_ship_gate: bool,
) -> None:
    if last_run.get("status") == "lock_busy":
        return
    fiscal_year = _resolve_target_fiscal_year(root, last_run.get("current_fy"))
    coverage = _sqlite_target_fy_coverage(check, root, fiscal_year)
    if coverage is None:
        return

    raw_summary_path = last_run.get("summary_path")
    if not isinstance(raw_summary_path, str) or not raw_summary_path:
        if require_ship_gate:
            check.fail("last_run.json summary_path is required when --require-ship-gate is used")
        return
    summary_path = _resolve_install_path(root, raw_summary_path)
    check.details["weekly_summary_path"] = str(summary_path)
    summary = _load_json_file(check, summary_path, label="weekly summary")
    if summary is None:
        return

    summary_fy = _coerce_int(summary.get("current_fy"))
    if summary_fy is not None and summary_fy != fiscal_year:
        check.fail(f"weekly summary current_fy does not match last_run.json current_fy: {summary_fy} != {fiscal_year}")

    after = summary.get("after")
    after_coverage = after.get("coverage") if isinstance(after, dict) else None
    if not isinstance(after_coverage, dict):
        check.fail("weekly summary after.coverage must contain a JSON object")
        return

    summary_total = _coerce_int(after_coverage.get("schools_total"))
    summary_target = _coerce_int(after_coverage.get("schools_with_target_pdf_current_fy"))
    if summary_total != coverage["schools_total"] or summary_target != coverage["schools_with_target_pdf_current_fy"]:
        check.fail(
            "weekly summary after.coverage does not match SQLite target-FY coverage: "
            f"summary={summary_target}/{summary_total}, "
            f"sqlite={coverage['schools_with_target_pdf_current_fy']}/{coverage['schools_total']}"
        )

    denominator = _coerce_int(last_run.get("target_pdf_auto_denominator_count"))
    acquired = _coerce_int(last_run.get("target_pdf_auto_acquired_count"))
    reviewable = _coerce_int(last_run.get("operator_reviewable_count"))
    if denominator is None or reviewable is None:
        return
    summary_delta = summary.get("delta")
    status_delta = summary_delta.get("school_fiscal_year_status") if isinstance(summary_delta, dict) else None
    if acquired is not None and isinstance(status_delta, dict):
        reviewable_delta = sum(
            max(_coerce_int(status_delta.get(status)) or 0, 0) for status in OPERATOR_REVIEWABLE_PDF_STATUSES
        )
        expected_reviewable = min(max(acquired, 0) + reviewable_delta, denominator)
        if reviewable != expected_reviewable:
            check.fail(
                "last_run.json operator_reviewable_count does not match acquired plus "
                "operator-reviewable status delta: "
                f"{reviewable} != {expected_reviewable}"
            )
    expected_yield = round(max(reviewable, 0) / denominator * 100.0, 1) if denominator > 0 else None
    expected_status = ship_gate_status_from_yield(expected_yield)
    if last_run.get("ship_gate_status") != expected_status:
        check.fail(
            "last_run.json ship_gate_status does not match operator_reviewable/denominator counts: "
            f"{last_run.get('ship_gate_status')} != {expected_status}"
        )


def _validate_sqlite_schema(check: InstallCheck, db_path: Path) -> None:
    if not db_path.is_file():
        check.fail("missing setup file: data/eidp.sqlite3")
        return
    try:
        with sqlite3.connect(db_path) as conn:
            rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            integrity = str(conn.execute("PRAGMA integrity_check").fetchone()[0])
    except sqlite3.Error as exc:
        check.fail(f"data/eidp.sqlite3 is not a readable SQLite DB: {exc}")
        return

    check.details["sqlite_integrity_check"] = integrity
    if integrity != "ok":
        check.fail(f"data/eidp.sqlite3 SQLite integrity_check failed: {integrity}")

    tables = {str(name) for (name,) in rows}
    check.details["sqlite_table_count"] = len(tables)
    check.details["sqlite_required_tables_present"] = sorted(tables & set(SQLITE_REQUIRED_TABLES))
    missing_tables = []
    for table in SQLITE_REQUIRED_TABLES:
        if table not in tables:
            missing_tables.append(table)
            check.fail(f"data/eidp.sqlite3 missing required table: {table}")
    if missing_tables:
        return

    try:
        with sqlite3.connect(db_path) as conn:
            dept_change_columns = {
                str(row[1])
                for row in conn.execute("PRAGMA table_info(department_change)").fetchall()
            }
            document_indexes = {
                str(row[1]): bool(row[2])
                for row in conn.execute("PRAGMA index_list(document)").fetchall()
            }

            school_count = int(conn.execute("SELECT COUNT(*) FROM school").fetchone()[0] or 0)
            task_count = int(
                conn.execute("SELECT COUNT(*) FROM school_fiscal_year_status").fetchone()[0] or 0
            )
    except sqlite3.Error as exc:
        check.fail(f"data/eidp.sqlite3 cannot inspect setup rows/schema: {exc}")
        return

    check.details["document_unique_indexes"] = sorted(
        name for name, unique in document_indexes.items() if unique
    )
    if not document_indexes.get("uq_document_file_hash"):
        check.fail("data/eidp.sqlite3 document missing unique index: uq_document_file_hash")

    check.details["department_change_columns_present"] = sorted(
        dept_change_columns & set(SQLITE_DEPARTMENT_CHANGE_VOID_COLUMNS)
    )
    for column in SQLITE_DEPARTMENT_CHANGE_VOID_COLUMNS:
        if column not in dept_change_columns:
            check.fail(f"data/eidp.sqlite3 department_change missing column: {column}")

    check.details["school_count"] = school_count
    check.details["school_fiscal_year_status_count"] = task_count
    if school_count > 0 and task_count == 0:
        check.fail(
            "data/eidp.sqlite3 has schools but no school_fiscal_year_status rows; "
            "run first_setup.bat or rebuild-school-year-tasks"
        )


def _load_latest_bootstrap_progress(check: InstallCheck, root: Path) -> dict[str, Any] | None:
    logs_dir = root / "logs"
    progress_files = sorted(
        logs_dir.glob("bootstrap-pdfs-*.json") if logs_dir.is_dir() else [],
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    check.details["bootstrap_progress_count"] = len(progress_files)
    if not progress_files:
        check.fail("missing logs/bootstrap-pdfs-*.json after initial bootstrap")
        return None

    progress_path = progress_files[0]
    check.details["bootstrap_progress_path"] = str(progress_path)
    try:
        payload = json.loads(progress_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        check.fail(f"bootstrap progress is not readable UTF-8 JSON: {exc}")
        return None
    if not isinstance(payload, dict):
        check.fail("bootstrap progress must contain a JSON object")
        return None
    return payload


def _validate_bootstrap_progress_payload(
    check: InstallCheck,
    root: Path,
    payload: dict[str, Any],
    *,
    require_ship_gate: bool = False,
) -> None:
    check.details["bootstrap_status"] = payload.get("status")
    if payload.get("status") != "succeeded":
        check.fail("bootstrap progress status must be succeeded for the after-bootstrap gate")

    details = payload.get("details")
    if not isinstance(details, dict):
        check.fail("bootstrap progress details must contain a JSON object")
        return

    required_keys = (
        "target_pdf_auto_acquired_count",
        "target_pdf_auto_denominator_count",
        "target_pdf_auto_denominator_scope",
        "target_pdf_auto_yield_pct",
        "operator_reviewable_count",
        "operator_reviewable_yield_pct",
        "ship_gate_auto_yield_pct",
        "ship_gate_operator_coverage_pct",
        "ship_gate_metric_basis",
        "ship_gate_status",
    )
    for key in required_keys:
        if key not in details:
            check.fail(f"bootstrap progress details missing key: {key}")

    for key in ("target_pdf_auto_acquired_count", "target_pdf_auto_denominator_count", "operator_reviewable_count"):
        if key in details and not isinstance(details.get(key), int):
            check.fail(f"bootstrap progress details {key} must be an integer")
    target_yield = details.get("target_pdf_auto_yield_pct")
    if "target_pdf_auto_yield_pct" in details:
        if target_yield is None:
            if details.get("ship_gate_status") != "not_measured":
                check.fail("bootstrap target_pdf_auto_yield_pct can be null only when not_measured")
        elif not isinstance(target_yield, int | float):
            check.fail("bootstrap progress details target_pdf_auto_yield_pct must be numeric")
    operator_yield = details.get("operator_reviewable_yield_pct")
    if "operator_reviewable_yield_pct" in details:
        if operator_yield is None:
            if details.get("ship_gate_status") != "not_measured":
                check.fail("bootstrap operator_reviewable_yield_pct can be null only when not_measured")
        elif not isinstance(operator_yield, int | float):
            check.fail("bootstrap progress details operator_reviewable_yield_pct must be numeric")
    for key in ("ship_gate_auto_yield_pct", "ship_gate_operator_coverage_pct"):
        if key in details and not isinstance(details.get(key), int | float):
            check.fail(f"bootstrap progress details {key} must be numeric")
    if "ship_gate_status" in details and not isinstance(details.get("ship_gate_status"), str):
        check.fail("bootstrap progress details ship_gate_status must be a string")
    bootstrap_gate_status = details.get("ship_gate_status")
    if isinstance(bootstrap_gate_status, str) and bootstrap_gate_status not in SHIP_GATE_STATUSES:
        check.fail("bootstrap progress details ship_gate_status must be pass, below_gate, or not_measured")
    if (
        "target_pdf_auto_denominator_scope" in details
        and not isinstance(details.get("target_pdf_auto_denominator_scope"), str)
    ):
        check.fail("bootstrap progress details target_pdf_auto_denominator_scope must be a string")
    if "ship_gate_metric_basis" in details:
        if not isinstance(details.get("ship_gate_metric_basis"), str):
            check.fail("bootstrap progress details ship_gate_metric_basis must be a string")
        elif details.get("ship_gate_metric_basis") != BOOTSTRAP_SHIP_GATE_METRIC_BASIS:
            check.fail(
                "bootstrap progress details ship_gate_metric_basis must be "
                f"{BOOTSTRAP_SHIP_GATE_METRIC_BASIS}"
            )
    if require_ship_gate and bootstrap_gate_status != "pass":
        check.fail("bootstrap ship_gate_status must be pass when --require-ship-gate is used")
    _validate_bootstrap_ship_gate_against_sqlite(
        check,
        root,
        details,
        require_ship_gate=require_ship_gate and bootstrap_gate_status == "pass",
    )

    raw_path = str(details.get("discovery_rca_batch_plan_path") or "")
    if raw_path:
        _validate_rca_batch_plan_file(
            check,
            root,
            raw_path=raw_path,
            expected_items=details.get("discovery_rca_batch_plan_item_count"),
            error_prefix="bootstrap_discovery_rca",
        )


def validate_install(
    app_root: Path,
    *,
    after_setup: bool = False,
    after_bootstrap: bool = False,
    after_weekly: bool = False,
    require_ship_gate: bool = False,
    require_ocr_addon: bool = False,
    require_ocr_runtime: bool = False,
    require_playwright_addon: bool = False,
) -> InstallCheck:
    root = app_root.resolve()
    check = InstallCheck(app_root=root)
    check.details["app_root"] = str(root)

    if not root.is_dir():
        check.fail(f"app root does not exist or is not a directory: {root}")
        return check
    if require_ship_gate and not (after_bootstrap or after_weekly):
        check.fail("--require-ship-gate requires --after-bootstrap or --after-weekly")

    for rel in CORE_FILES:
        if not _exists_file(root, rel):
            check.fail(f"missing core file: {rel}")
    for rel in CORE_DIRS:
        if not _exists_dir(root, rel):
            check.fail(f"missing core directory: {rel}")
    _validate_build_info(check, root / "BUILD_INFO.json")

    wheel_count = _count_wheels(root)
    check.details["wheel_count"] = wheel_count
    if wheel_count == 0:
        check.fail("wheelhouse contains no wheels")
    if not any(path.name.startswith("eidp-") for path in (root / "wheelhouse").glob("*.whl")):
        check.fail("wheelhouse missing project wheel eidp-*.whl")
    duplicate_wheels = _duplicate_wheel_distributions(root)
    check.details["duplicate_wheel_distributions"] = duplicate_wheels
    if duplicate_wheels:
        check.fail(f"wheelhouse contains duplicate distributions: {duplicate_wheels}")

    master = root / "data" / "master.xlsx"
    check.details["master_xlsx_present"] = master.is_file()
    if not master.is_file():
        check.warn("data/master.xlsx is missing; EIDP-setup.bat will fail until master.xlsx is present")

    if after_setup:
        for rel in SETUP_DIRS:
            if not _exists_dir(root, rel):
                check.fail(f"missing setup directory: {rel}")
        for rel in SETUP_FILES:
            if not _exists_file(root, rel):
                check.fail(f"missing setup file: {rel}")
        _validate_sqlite_schema(check, root / "data" / "eidp.sqlite3")

    if after_bootstrap:
        bootstrap_progress = _load_latest_bootstrap_progress(check, root)
        if bootstrap_progress is not None:
            _validate_bootstrap_progress_payload(check, root, bootstrap_progress, require_ship_gate=require_ship_gate)
        logs_dir = root / "logs"
        bootstrap_logs = sorted(logs_dir.glob("bootstrap-pdfs-*.log")) if logs_dir.is_dir() else []
        check.details["bootstrap_log_count"] = len(bootstrap_logs)
        if not bootstrap_logs:
            check.fail("missing logs/bootstrap-pdfs-*.log after initial bootstrap")

    if after_weekly:
        last_run = _load_last_run(check, root / "data" / "output" / "last_run.json")
        if last_run is not None:
            check.details["last_run_status"] = last_run.get("status")
            for key in LAST_RUN_REQUIRED_KEYS:
                if key not in last_run:
                    check.fail(f"last_run.json missing key: {key}")
            last_run_status = last_run.get("status")
            if last_run_status not in {"success", "lock_busy"}:
                check.fail("last_run.json status must be success or lock_busy for the weekly validation gate")
            if last_run_status == "lock_busy":
                if last_run.get("selection_mode") != "lock_busy":
                    check.fail("last_run.json selection_mode must be lock_busy when status is lock_busy")
            elif last_run.get("selection_mode") not in {"target_missing", "stale_only"}:
                check.fail("last_run.json selection_mode must be target_missing or stale_only")
            for key in (
                "target_missing_school_count",
                "new_document_count",
                "target_pdf_auto_acquired_count",
                "target_pdf_auto_denominator_count",
                "operator_reviewable_count",
            ):
                if key in last_run and not isinstance(last_run.get(key), int):
                    check.fail(f"last_run.json {key} must be an integer")
            if "target_pdf_auto_yield_pct" in last_run:
                target_yield = last_run.get("target_pdf_auto_yield_pct")
                if target_yield is None:
                    if last_run.get("ship_gate_status") != "not_measured":
                        check.fail("last_run.json target_pdf_auto_yield_pct can be null only when not_measured")
                elif not isinstance(target_yield, int | float):
                    check.fail("last_run.json target_pdf_auto_yield_pct must be numeric")
            operator_yield = last_run.get("operator_reviewable_yield_pct")
            if "operator_reviewable_yield_pct" in last_run:
                if operator_yield is None:
                    if last_run.get("ship_gate_status") != "not_measured":
                        check.fail("last_run.json operator_reviewable_yield_pct can be null only when not_measured")
                elif not isinstance(operator_yield, int | float):
                    check.fail("last_run.json operator_reviewable_yield_pct must be numeric")
            for key in ("ship_gate_auto_yield_pct", "ship_gate_operator_coverage_pct"):
                if key in last_run and not isinstance(last_run.get(key), int | float):
                    check.fail(f"last_run.json {key} must be numeric")
            if "ship_gate_status" in last_run and not isinstance(last_run.get("ship_gate_status"), str):
                check.fail("last_run.json ship_gate_status must be a string")
            weekly_gate_status = last_run.get("ship_gate_status")
            if isinstance(weekly_gate_status, str) and weekly_gate_status not in SHIP_GATE_STATUSES:
                check.fail("last_run.json ship_gate_status must be pass, below_gate, or not_measured")
            if (
                "target_pdf_auto_denominator_scope" in last_run
                and not isinstance(last_run.get("target_pdf_auto_denominator_scope"), str)
            ):
                check.fail("last_run.json target_pdf_auto_denominator_scope must be a string")
            if "ship_gate_metric_basis" in last_run:
                if not isinstance(last_run.get("ship_gate_metric_basis"), str):
                    check.fail("last_run.json ship_gate_metric_basis must be a string")
                elif last_run.get("ship_gate_metric_basis") != WEEKLY_SHIP_GATE_METRIC_BASIS:
                    check.fail(f"last_run.json ship_gate_metric_basis must be {WEEKLY_SHIP_GATE_METRIC_BASIS}")
            if require_ship_gate and weekly_gate_status != "pass":
                check.fail("last_run.json ship_gate_status must be pass when --require-ship-gate is used")
            _validate_weekly_ship_gate_against_sqlite(
                check,
                root,
                last_run,
                require_ship_gate=require_ship_gate and weekly_gate_status == "pass",
            )
            _validate_discovery_rca_batch_plan(check, root, last_run.get("discovery_rca"))

        logs_dir = root / "logs"
        run_logs = sorted(logs_dir.glob("run-*.log")) if logs_dir.is_dir() else []
        check.details["run_log_count"] = len(run_logs)
        if not run_logs:
            check.fail("missing logs/run-*.log after weekly run")

    if require_ocr_addon or require_ocr_runtime:
        tesseract_exe = root / "ocr-addon" / "tesseract" / "tesseract.exe"
        tessdata_dir = root / "ocr-addon" / "tessdata"
        jpn_traineddata = tessdata_dir / "jpn.traineddata"
        if not tesseract_exe.is_file():
            check.fail("missing OCR add-on file: ocr-addon/tesseract/tesseract.exe")
        if not jpn_traineddata.is_file():
            check.fail("missing OCR add-on file: ocr-addon/tessdata/jpn.traineddata")
        if require_ocr_runtime and tesseract_exe.is_file() and jpn_traineddata.is_file():
            _validate_ocr_runtime(check, tesseract_exe=tesseract_exe, tessdata_dir=tessdata_dir)

    if require_playwright_addon:
        if not _exists_dir(root, "playwright-addon/ms-playwright"):
            check.fail("missing Playwright add-on directory: playwright-addon/ms-playwright")
        if not _exists_dir(root, "playwright-addon/wheelhouse"):
            check.fail("missing Playwright add-on directory: playwright-addon/wheelhouse")
        addon_wheelhouse = root / "playwright-addon" / "wheelhouse"
        if addon_wheelhouse.is_dir():
            if not any(addon_wheelhouse.glob("playwright-*.whl")):
                check.fail("missing Playwright add-on wheel: playwright-addon/wheelhouse/playwright-*.whl")
            if not any(addon_wheelhouse.glob("scrapling-*.whl")):
                check.fail("missing Playwright add-on wheel: playwright-addon/wheelhouse/scrapling-*.whl")

    return check


def _run_ocr_probe(check: InstallCheck, args: list[str], label: str) -> subprocess.CompletedProcess[str] | None:
    try:
        result = subprocess.run(
            args,
            capture_output=True,
            check=False,
            encoding="utf-8",
            errors="replace",
            timeout=20,
        )
    except subprocess.TimeoutExpired:
        check.fail(f"OCR runtime command timed out: {label}")
        return None
    except OSError as exc:
        check.fail(f"OCR runtime command failed to start: {label}: {exc}")
        return None
    if result.returncode != 0:
        stderr = result.stderr.strip().splitlines()
        stdout = result.stdout.strip().splitlines()
        snippet = (stderr or stdout or ["<no output>"])[0]
        check.fail(f"OCR runtime command failed: {label} rc={result.returncode}: {snippet}")
        return None
    return result


def _validate_ocr_runtime(check: InstallCheck, *, tesseract_exe: Path, tessdata_dir: Path) -> None:
    check.details["ocr_tesseract_path"] = str(tesseract_exe)
    check.details["ocr_tessdata_dir"] = str(tessdata_dir)

    version = _run_ocr_probe(check, [str(tesseract_exe), "--version"], "tesseract --version")
    if version is not None:
        first_line = next((line.strip() for line in version.stdout.splitlines() if line.strip()), "")
        check.details["ocr_tesseract_version"] = first_line

    langs = _run_ocr_probe(
        check,
        [str(tesseract_exe), "--tessdata-dir", str(tessdata_dir), "--list-langs"],
        "tesseract --list-langs",
    )
    if langs is None:
        return
    detected = [line.strip() for line in langs.stdout.splitlines() if line.strip() and not line.startswith("List of")]
    check.details["ocr_tesseract_languages"] = detected
    if "jpn" not in detected:
        check.fail("OCR runtime language list missing jpn")


def render_text(check: InstallCheck) -> str:
    state = "OK" if check.ok else "FAIL"
    lines = [f"{state} install: {check.app_root}"]
    for key, value in sorted(check.details.items()):
        lines.append(f"  {key}: {value}")
    for warning in check.warnings:
        lines.append(f"  warning: {warning}")
    for error in check.errors:
        lines.append(f"  error: {error}")
    return "\n".join(lines)


def check_to_json(check: InstallCheck) -> str:
    return json.dumps(
        {
            "app_root": str(check.app_root),
            "ok": check.ok,
            "errors": check.errors,
            "warnings": check.warnings,
            "details": check.details,
        },
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate an extracted EIDP Windows install directory.")
    parser.add_argument("app_root", type=Path, help="Path to extracted EIDP app root, e.g. C:\\EIDP")
    parser.add_argument("--after-setup", action="store_true", help="Require first_setup.bat output artifacts")
    parser.add_argument("--after-bootstrap", action="store_true", help="Require initial bootstrap progress artifacts")
    parser.add_argument("--after-weekly", action="store_true", help="Require weekly_run.bat output artifacts")
    parser.add_argument(
        "--require-ship-gate",
        action="store_true",
        help="Fail after-bootstrap/after-weekly validation unless ship_gate_status is pass.",
    )
    parser.add_argument("--require-ocr-addon", action="store_true")
    parser.add_argument(
        "--require-ocr-runtime",
        action="store_true",
        help="Require OCR add-on files and execute packaged tesseract.exe runtime probes",
    )
    parser.add_argument("--require-playwright-addon", action="store_true")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    args = parser.parse_args(argv)

    check = validate_install(
        args.app_root,
        after_setup=args.after_setup,
        after_bootstrap=args.after_bootstrap,
        after_weekly=args.after_weekly,
        require_ship_gate=args.require_ship_gate,
        require_ocr_addon=args.require_ocr_addon,
        require_ocr_runtime=args.require_ocr_runtime,
        require_playwright_addon=args.require_playwright_addon,
    )
    print(check_to_json(check) if args.json else render_text(check))
    return 0 if check.ok else 1


if __name__ == "__main__":
    sys.exit(main())
