"""Validate an extracted EIDP Windows install directory.

This script is for the Windows VM / operator-PC gates after ZIP extraction.
It checks the evidence that should exist after setup and optionally after a
weekly run. It does not execute Windows binaries.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


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
    "scripts/run_weekly_target_year_discovery.py",
    "scripts/run_r8_rediscovery_weekly.py",
    "scripts/bootstrap_pdf_pipeline.py",
    "scripts/download_prefecture_artifacts.py",
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
    "target_pdf_auto_yield_pct",
    "ship_gate_auto_yield_pct",
    "ship_gate_status",
    "discovery_stats",
    "ingest_stats",
)

SQLITE_REQUIRED_TABLES = (
    "school",
    "school_site",
    "document",
    "department",
    "department_yearly",
    "school_fiscal_year_status",
    "manual_action_log",
)

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


def _validate_sqlite_schema(check: InstallCheck, db_path: Path) -> None:
    if not db_path.is_file():
        check.fail("missing setup file: data/eidp.sqlite3")
        return
    try:
        with sqlite3.connect(db_path) as conn:
            rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
    except sqlite3.Error as exc:
        check.fail(f"data/eidp.sqlite3 is not a readable SQLite DB: {exc}")
        return

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
        school_count = int(conn.execute("SELECT COUNT(*) FROM school").fetchone()[0] or 0)
        task_count = int(
            conn.execute("SELECT COUNT(*) FROM school_fiscal_year_status").fetchone()[0] or 0
        )
    except sqlite3.Error as exc:
        check.fail(f"data/eidp.sqlite3 cannot count setup rows: {exc}")
        return

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


def _validate_bootstrap_progress_payload(check: InstallCheck, root: Path, payload: dict[str, Any]) -> None:
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
        "target_pdf_auto_yield_pct",
        "ship_gate_auto_yield_pct",
        "ship_gate_status",
    )
    for key in required_keys:
        if key not in details:
            check.fail(f"bootstrap progress details missing key: {key}")

    for key in ("target_pdf_auto_acquired_count", "target_pdf_auto_denominator_count"):
        if key in details and not isinstance(details.get(key), int):
            check.fail(f"bootstrap progress details {key} must be an integer")
    target_yield = details.get("target_pdf_auto_yield_pct")
    if "target_pdf_auto_yield_pct" in details:
        if target_yield is None:
            if details.get("ship_gate_status") != "not_measured":
                check.fail("bootstrap target_pdf_auto_yield_pct can be null only when not_measured")
        elif not isinstance(target_yield, int | float):
            check.fail("bootstrap progress details target_pdf_auto_yield_pct must be numeric")
    if "ship_gate_auto_yield_pct" in details and not isinstance(details.get("ship_gate_auto_yield_pct"), int | float):
        check.fail("bootstrap progress details ship_gate_auto_yield_pct must be numeric")
    if "ship_gate_status" in details and not isinstance(details.get("ship_gate_status"), str):
        check.fail("bootstrap progress details ship_gate_status must be a string")

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
    require_ocr_addon: bool = False,
    require_playwright_addon: bool = False,
) -> InstallCheck:
    root = app_root.resolve()
    check = InstallCheck(app_root=root)
    check.details["app_root"] = str(root)

    if not root.is_dir():
        check.fail(f"app root does not exist or is not a directory: {root}")
        return check

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
            _validate_bootstrap_progress_payload(check, root, bootstrap_progress)
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
            if last_run.get("status") != "success":
                check.fail("last_run.json status must be success for the weekly validation gate")
            if last_run.get("selection_mode") not in {"target_missing", "stale_only"}:
                check.fail("last_run.json selection_mode must be target_missing or stale_only")
            for key in ("target_missing_school_count", "new_document_count", "target_pdf_auto_acquired_count"):
                if key in last_run and not isinstance(last_run.get(key), int):
                    check.fail(f"last_run.json {key} must be an integer")
            if "target_pdf_auto_yield_pct" in last_run:
                target_yield = last_run.get("target_pdf_auto_yield_pct")
                if target_yield is None:
                    if last_run.get("ship_gate_status") != "not_measured":
                        check.fail("last_run.json target_pdf_auto_yield_pct can be null only when not_measured")
                elif not isinstance(target_yield, int | float):
                    check.fail("last_run.json target_pdf_auto_yield_pct must be numeric")
            for key in ("ship_gate_auto_yield_pct",):
                if key in last_run and not isinstance(last_run.get(key), int | float):
                    check.fail(f"last_run.json {key} must be numeric")
            if "ship_gate_status" in last_run and not isinstance(last_run.get("ship_gate_status"), str):
                check.fail("last_run.json ship_gate_status must be a string")
            _validate_discovery_rca_batch_plan(check, root, last_run.get("discovery_rca"))

        logs_dir = root / "logs"
        run_logs = sorted(logs_dir.glob("run-*.log")) if logs_dir.is_dir() else []
        check.details["run_log_count"] = len(run_logs)
        if not run_logs:
            check.fail("missing logs/run-*.log after weekly run")

    if require_ocr_addon:
        if not _exists_file(root, "ocr-addon/tesseract/tesseract.exe"):
            check.fail("missing OCR add-on file: ocr-addon/tesseract/tesseract.exe")
        if not _exists_file(root, "ocr-addon/tessdata/jpn.traineddata"):
            check.fail("missing OCR add-on file: ocr-addon/tessdata/jpn.traineddata")

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
    parser.add_argument("--require-ocr-addon", action="store_true")
    parser.add_argument("--require-playwright-addon", action="store_true")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    args = parser.parse_args(argv)

    check = validate_install(
        args.app_root,
        after_setup=args.after_setup,
        after_bootstrap=args.after_bootstrap,
        after_weekly=args.after_weekly,
        require_ocr_addon=args.require_ocr_addon,
        require_playwright_addon=args.require_playwright_addon,
    )
    print(check_to_json(check) if args.json else render_text(check))
    return 0 if check.ok else 1


if __name__ == "__main__":
    sys.exit(main())
