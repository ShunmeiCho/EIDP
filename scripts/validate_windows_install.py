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
    "scripts/first_setup.bat",
    "scripts/launch.bat",
    "scripts/weekly_run.bat",
    "scripts/uninstall.bat",
    "scripts/validate_install.bat",
    "scripts/run_weekly_target_year_discovery.py",
    "scripts/run_r8_rediscovery_weekly.py",
    "runtime/python/python.exe",
    "runtime/uv.exe",
    "requirements-windows.txt",
    "alembic.ini",
    "docs/runbooks/eidp-windows.md",
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


def validate_install(
    app_root: Path,
    *,
    after_setup: bool = False,
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

    wheel_count = _count_wheels(root)
    check.details["wheel_count"] = wheel_count
    if wheel_count == 0:
        check.fail("wheelhouse contains no wheels")
    if not any(path.name.startswith("eidp-") for path in (root / "wheelhouse").glob("*.whl")):
        check.fail("wheelhouse missing project wheel eidp-*.whl")

    master = root / "data" / "master.xlsx"
    check.details["master_xlsx_present"] = master.is_file()
    if not master.is_file():
        check.warn("data/master.xlsx is missing; first_setup.bat can continue but master import must be completed")

    if after_setup:
        for rel in SETUP_DIRS:
            if not _exists_dir(root, rel):
                check.fail(f"missing setup directory: {rel}")
        for rel in SETUP_FILES:
            if not _exists_file(root, rel):
                check.fail(f"missing setup file: {rel}")
        _validate_sqlite_schema(check, root / "data" / "eidp.sqlite3")

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
            for key in ("target_missing_school_count", "new_document_count"):
                if key in last_run and not isinstance(last_run.get(key), int):
                    check.fail(f"last_run.json {key} must be an integer")

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
    parser.add_argument("--after-weekly", action="store_true", help="Require weekly_run.bat output artifacts")
    parser.add_argument("--require-ocr-addon", action="store_true")
    parser.add_argument("--require-playwright-addon", action="store_true")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    args = parser.parse_args(argv)

    check = validate_install(
        args.app_root,
        after_setup=args.after_setup,
        after_weekly=args.after_weekly,
        require_ocr_addon=args.require_ocr_addon,
        require_playwright_addon=args.require_playwright_addon,
    )
    print(check_to_json(check) if args.json else render_text(check))
    return 0 if check.ok else 1


if __name__ == "__main__":
    sys.exit(main())
