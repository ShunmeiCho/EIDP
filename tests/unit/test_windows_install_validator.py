"""Validate extracted Windows install evidence before/after VM steps."""

from __future__ import annotations

import importlib.util
import json
import sqlite3
import sys
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "validate_windows_install.py"
VM_RUNBOOK_PATH = Path(__file__).resolve().parents[2] / "docs" / "runbooks" / "eidp-windows-vm-validation.md"
spec = importlib.util.spec_from_file_location("validate_windows_install", SCRIPT_PATH)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def _write(root: Path, rel: str, body: bytes | str = "") -> None:
    path = root / Path(*rel.split("/"))
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(body, bytes):
        path.write_bytes(body)
    else:
        path.write_text(body, encoding="utf-8")


def _mkdir(root: Path, rel: str) -> None:
    (root / Path(*rel.split("/"))).mkdir(parents=True, exist_ok=True)


def _core_install(root: Path) -> Path:
    for rel in module.CORE_FILES:
        if rel == "BUILD_INFO.json":
            _write(
                root,
                rel,
                json.dumps(
                    {
                        "app": "EIDP",
                        "built_at_utc": "2026-05-07T04:33:48+00:00",
                        "git_commit": "830ae68ce7242fd0c34b8794b02e0a8ce27139fc",
                        "git_branch": "sprint8-handoff-finalize",
                        "git_dirty": "false",
                    }
                ),
            )
        else:
            _write(root, rel, b"PE" if rel.endswith(".exe") else "")
    for rel in module.CORE_DIRS:
        _mkdir(root, rel)
    _write(root, "src/eidp/__init__.py", "")
    _write(root, "migrations/env.py", "")
    _write(root, "wheelhouse/eidp-0.2.0-py3-none-any.whl", b"wheel")
    _write(root, "wheelhouse/structlog-25.5.0-py3-none-any.whl", b"wheel")
    _write(root, "data/master.xlsx", b"xlsx")
    return root


def _setup_artifacts(root: Path) -> None:
    for rel in module.SETUP_DIRS:
        _mkdir(root, rel)
    for rel in module.SETUP_FILES:
        if rel.endswith(".sqlite3"):
            _write_sqlite_schema(root / Path(*rel.split("/")))
        else:
            _write(root, rel, b"PE")


def _write_sqlite_schema(path: Path, *, omit: str | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        for table in module.SQLITE_REQUIRED_TABLES:
            if table == omit:
                continue
            if table == "school":
                conn.execute(
                    "CREATE TABLE school ("
                    "id INTEGER PRIMARY KEY, "
                    "status TEXT DEFAULT 'active', "
                    "school_type TEXT"
                    ")"
                )
            elif table == "school_site":
                conn.execute(
                    "CREATE TABLE school_site ("
                    "id INTEGER PRIMARY KEY, "
                    "school_id INTEGER, "
                    "verified BOOLEAN"
                    ")"
                )
            elif table == "document":
                conn.execute(
                    "CREATE TABLE document ("
                    "id INTEGER PRIMARY KEY, "
                    "file_hash TEXT, "
                    "school_id INTEGER, "
                    "fiscal_year INTEGER, "
                    "ingest_status TEXT, "
                    "pdf_type TEXT"
                    ")"
                )
            elif table == "department_change":
                conn.execute(
                    "CREATE TABLE department_change ("
                    "id INTEGER PRIMARY KEY, "
                    "voided BOOLEAN NOT NULL DEFAULT 0, "
                    "voided_at DATETIME, "
                    "voided_by VARCHAR(50), "
                    "void_reason TEXT"
                    ")"
                )
            elif table == "school_fiscal_year_status":
                conn.execute(
                    "CREATE TABLE school_fiscal_year_status ("
                    "school_id INTEGER, "
                    "fiscal_year INTEGER"
                    ")"
                )
            else:
                conn.execute(f"CREATE TABLE {table} (id INTEGER PRIMARY KEY)")
        if omit != "document":
            conn.execute("CREATE UNIQUE INDEX uq_document_file_hash ON document (file_hash)")
        conn.commit()


def _seed_target_fy_coverage(root: Path, *, total: int = 10, acquired: int = 6, fy: int = 2026) -> None:
    db_path = root / "data" / "eidp.sqlite3"
    with sqlite3.connect(db_path) as conn:
        conn.execute("DELETE FROM document")
        conn.execute("DELETE FROM school_fiscal_year_status")
        conn.execute("DELETE FROM school")
        for school_id in range(1, total + 1):
            conn.execute(
                "INSERT INTO school (id, status, school_type) VALUES (?, 'active', '専門学校')",
                (school_id,),
            )
            conn.execute(
                "INSERT INTO school_fiscal_year_status (school_id, fiscal_year) VALUES (?, ?)",
                (school_id, fy),
            )
        for school_id in range(1, acquired + 1):
            conn.execute(
                "INSERT INTO document (id, file_hash, school_id, fiscal_year, ingest_status, pdf_type) "
                "VALUES (?, ?, ?, ?, 'ingested', 'target')",
                (school_id, f"hash-{school_id}", school_id, fy),
            )
        conn.commit()


def _weekly_artifacts(root: Path) -> None:
    _seed_target_fy_coverage(root, total=10, acquired=6, fy=2026)
    summary_rel = "data/output/target-year-discovery/20260505_010203-summary.json"
    _write(
        root,
        summary_rel,
        json.dumps(
            {
                "run_id": "20260505_010203",
                "current_fy": 2026,
                "school_type": "専門学校",
                "target_missing_school_count": 10,
                "before": {"coverage": {"schools_total": 10, "schools_with_target_pdf_current_fy": 0}},
                "after": {"coverage": {"schools_total": 10, "schools_with_target_pdf_current_fy": 6}},
                "delta": {"coverage": {"schools_with_target_pdf_current_fy": 6}},
            }
        ),
    )
    _write(
        root,
        "data/output/last_run.json",
        json.dumps(
            {
                "status": "success",
                "run_id": "20260505_010203",
                "started_at": "2026-05-05T01:02:03+00:00",
                "finished_at": "2026-05-05T01:02:10+00:00",
                "current_fy": 2026,
                "selection_mode": "target_missing",
                "target_missing_school_count": 10,
                "new_document_count": 6,
                "target_pdf_auto_acquired_count": 6,
                "target_pdf_auto_denominator_count": 10,
                "target_pdf_auto_denominator_scope": "target_missing_schools_before_run",
                "target_pdf_auto_yield_pct": 60.0,
                "ship_gate_auto_yield_pct": 60.0,
                "ship_gate_metric_basis": "weekly_missing_school_acquisition",
                "ship_gate_status": "pass",
                "discovery_stats": {"downloaded": 2},
                "ingest_stats": {"processed": 2},
                "summary_path": summary_rel,
            }
        ),
    )
    _write(root, "logs/run-20260505.log", "ok")


def _bootstrap_artifacts(root: Path) -> None:
    _seed_target_fy_coverage(root, total=10, acquired=6, fy=2026)
    _write(
        root,
        "logs/bootstrap-pdfs-20260505-010203.json",
        json.dumps(
            {
                "status": "succeeded",
                "current_step": 5,
                "total_steps": 5,
                "percent": 1.0,
                "message": "初回URL/PDF取得が完了しました。",
                "details": {
                    "target_pdf_auto_acquired_count": 6,
                    "target_pdf_auto_denominator_count": 10,
                    "target_pdf_auto_denominator_scope": "active_specialty_schools",
                    "target_pdf_auto_yield_pct": 60.0,
                    "ship_gate_auto_yield_pct": 60.0,
                    "ship_gate_metric_basis": "post_bootstrap_current_target_fy_coverage",
                    "ship_gate_status": "pass",
                    "current_fy": 2026,
                },
            }
        ),
    )
    _write(root, "logs/bootstrap-pdfs-20260505-010203.log", "ok")


def test_validate_core_install_accepts_unzipped_layout(tmp_path: Path) -> None:
    root = _core_install(tmp_path / "EIDP")

    check = module.validate_install(root)

    assert check.ok, check.errors
    assert check.details["wheel_count"] == 2
    assert check.details["master_xlsx_present"] is True
    assert check.details["build_commit"] == "830ae68ce7242fd0c34b8794b02e0a8ce27139fc"
    assert check.details["build_branch"] == "sprint8-handoff-finalize"
    assert check.details["build_dirty"] == "false"


def test_validate_core_install_rejects_bad_build_info(tmp_path: Path) -> None:
    root = _core_install(tmp_path / "EIDP")
    _write(
        root,
        "BUILD_INFO.json",
        json.dumps(
            {
                "app": "Wrong",
                "built_at_utc": "2026-05-07T04:33:48+00:00",
                "git_commit": "short",
                "git_branch": "sprint8-handoff-finalize",
                "git_dirty": "false",
            }
        ),
    )

    check = module.validate_install(root)

    assert not check.ok
    assert any("app must be EIDP" in error for error in check.errors)
    assert any("full 40-character commit" in error for error in check.errors)


def test_validate_core_install_requires_project_wheel(tmp_path: Path) -> None:
    root = _core_install(tmp_path / "EIDP")
    (root / "wheelhouse" / "eidp-0.2.0-py3-none-any.whl").unlink()

    check = module.validate_install(root)

    assert not check.ok
    assert any("project wheel" in error for error in check.errors)


def test_validate_core_install_rejects_duplicate_dependency_wheels(tmp_path: Path) -> None:
    root = _core_install(tmp_path / "EIDP")
    _write(root, "wheelhouse/structlog-25.6.0-py3-none-any.whl", b"wheel")

    check = module.validate_install(root)

    assert not check.ok
    assert any("duplicate distributions" in error for error in check.errors)


def test_validate_core_install_requires_bootstrap_and_version_files(tmp_path: Path) -> None:
    root = _core_install(tmp_path / "EIDP")
    for rel in (
        "BUILD_INFO.json",
        "scripts/bootstrap_pdf_pipeline.py",
        "data/url-discovery/discovered-urls-50.csv",
        "data/url-discovery/corporation_domains.csv",
    ):
        (root / Path(*rel.split("/"))).unlink()

    check = module.validate_install(root)

    assert not check.ok
    assert any("BUILD_INFO.json" in error for error in check.errors)
    assert any("scripts/bootstrap_pdf_pipeline.py" in error for error in check.errors)
    assert any("data/url-discovery/discovered-urls-50.csv" in error for error in check.errors)
    assert any("data/url-discovery/corporation_domains.csv" in error for error in check.errors)


def test_validate_core_install_requires_operator_route_modules(tmp_path: Path) -> None:
    root = _core_install(tmp_path / "EIDP")
    for rel in (
        "src/eidp/review/operator_pages.py",
        "src/eidp/review/_pages/audit_log.py",
        "src/eidp/review/_pages/prefecture_remarks.py",
        "src/eidp/review/_pages/settings_page.py",
    ):
        (root / Path(*rel.split("/"))).unlink()

    check = module.validate_install(root)

    assert not check.ok
    assert any("src/eidp/review/operator_pages.py" in error for error in check.errors)
    assert any("src/eidp/review/_pages/audit_log.py" in error for error in check.errors)
    assert any("src/eidp/review/_pages/prefecture_remarks.py" in error for error in check.errors)
    assert any("src/eidp/review/_pages/settings_page.py" in error for error in check.errors)


def test_validate_after_setup_requires_venv_and_sqlite(tmp_path: Path) -> None:
    root = _core_install(tmp_path / "EIDP")

    check = module.validate_install(root, after_setup=True)

    assert not check.ok
    assert any(".venv/Scripts/python.exe" in error for error in check.errors)
    assert any("data/eidp.sqlite3" in error for error in check.errors)


def test_validate_after_setup_accepts_setup_artifacts(tmp_path: Path) -> None:
    root = _core_install(tmp_path / "EIDP")
    _setup_artifacts(root)

    check = module.validate_install(root, after_setup=True)

    assert check.ok, check.errors
    assert "school_fiscal_year_status" in check.details["sqlite_required_tables_present"]
    assert "support_recipient" in check.details["sqlite_required_tables_present"]
    assert check.details["sqlite_integrity_check"] == "ok"


def test_validate_after_setup_rejects_sqlite_missing_school_fiscal_year_status(tmp_path: Path) -> None:
    root = _core_install(tmp_path / "EIDP")
    _setup_artifacts(root)
    db_path = root / "data" / "eidp.sqlite3"
    db_path.unlink()
    _write_sqlite_schema(db_path, omit="school_fiscal_year_status")

    check = module.validate_install(root, after_setup=True)

    assert not check.ok
    assert any("school_fiscal_year_status" in error for error in check.errors)


def test_validate_after_setup_rejects_sqlite_missing_support_recipient(tmp_path: Path) -> None:
    root = _core_install(tmp_path / "EIDP")
    _setup_artifacts(root)
    db_path = root / "data" / "eidp.sqlite3"
    db_path.unlink()
    _write_sqlite_schema(db_path, omit="support_recipient")

    check = module.validate_install(root, after_setup=True)

    assert not check.ok
    assert any("support_recipient" in error for error in check.errors)


def test_validate_after_setup_rejects_failed_sqlite_integrity_check(tmp_path: Path, monkeypatch) -> None:
    root = _core_install(tmp_path / "EIDP")
    _setup_artifacts(root)

    real_connect = module.sqlite3.connect

    class BrokenIntegrityConnection:
        def __init__(self, path: Path) -> None:
            self._conn = real_connect(path)

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
            self._conn.close()

        def execute(self, statement: str, *args, **kwargs):  # noqa: ANN002, ANN003
            if statement == "PRAGMA integrity_check":
                return self._conn.execute("SELECT '*** in database main *** simulated corruption'")
            return self._conn.execute(statement, *args, **kwargs)

    monkeypatch.setattr(module.sqlite3, "connect", lambda path: BrokenIntegrityConnection(path))

    check = module.validate_install(root, after_setup=True)

    assert not check.ok
    assert check.details["sqlite_integrity_check"] == "*** in database main *** simulated corruption"
    assert any("SQLite integrity_check failed" in error for error in check.errors)


def test_validate_after_setup_rejects_missing_department_change_void_columns(tmp_path: Path) -> None:
    root = _core_install(tmp_path / "EIDP")
    _setup_artifacts(root)
    db_path = root / "data" / "eidp.sqlite3"
    with sqlite3.connect(db_path) as conn:
        conn.execute("DROP TABLE department_change")
        conn.execute("CREATE TABLE department_change (id INTEGER PRIMARY KEY)")
        conn.commit()

    check = module.validate_install(root, after_setup=True)

    assert not check.ok
    assert any("department_change missing column: voided" in error for error in check.errors)
    assert any("department_change missing column: void_reason" in error for error in check.errors)


def test_validate_after_setup_rejects_missing_document_hash_unique_index(tmp_path: Path) -> None:
    root = _core_install(tmp_path / "EIDP")
    _setup_artifacts(root)
    db_path = root / "data" / "eidp.sqlite3"
    with sqlite3.connect(db_path) as conn:
        conn.execute("DROP INDEX uq_document_file_hash")
        conn.commit()

    check = module.validate_install(root, after_setup=True)

    assert not check.ok
    assert any("document missing unique index: uq_document_file_hash" in error for error in check.errors)


def test_validate_after_setup_rejects_empty_school_year_tasks_when_schools_exist(tmp_path: Path) -> None:
    root = _core_install(tmp_path / "EIDP")
    _setup_artifacts(root)
    db_path = root / "data" / "eidp.sqlite3"
    with sqlite3.connect(db_path) as conn:
        conn.execute("INSERT INTO school (id) VALUES (1)")
        conn.commit()

    check = module.validate_install(root, after_setup=True)

    assert not check.ok
    assert check.details["school_count"] == 1
    assert check.details["school_fiscal_year_status_count"] == 0
    assert any("no school_fiscal_year_status rows" in error for error in check.errors)


def test_validate_after_setup_rejects_unreadable_sqlite(tmp_path: Path) -> None:
    root = _core_install(tmp_path / "EIDP")
    _setup_artifacts(root)
    _write(root, "data/eidp.sqlite3", b"not sqlite")

    check = module.validate_install(root, after_setup=True)

    assert not check.ok
    assert any("readable SQLite" in error for error in check.errors)


def test_validate_after_weekly_requires_last_run_and_log(tmp_path: Path) -> None:
    root = _core_install(tmp_path / "EIDP")
    _setup_artifacts(root)

    check = module.validate_install(root, after_setup=True, after_weekly=True)

    assert not check.ok
    assert any("last_run.json" in error for error in check.errors)
    assert any("logs/run-*.log" in error for error in check.errors)


def test_validate_after_weekly_accepts_last_run_schema(tmp_path: Path) -> None:
    root = _core_install(tmp_path / "EIDP")
    _setup_artifacts(root)
    _weekly_artifacts(root)

    check = module.validate_install(root, after_setup=True, after_weekly=True)

    assert check.ok, check.errors
    assert check.details["last_run_status"] == "success"
    assert check.details["run_log_count"] == 1


def test_validate_after_weekly_accepts_lock_busy_last_run(tmp_path: Path) -> None:
    root = _core_install(tmp_path / "EIDP")
    _setup_artifacts(root)
    _weekly_artifacts(root)
    payload = json.loads((root / "data" / "output" / "last_run.json").read_text(encoding="utf-8"))
    payload.update(
        {
            "status": "lock_busy",
            "selection_mode": "lock_busy",
            "target_missing_school_count": 0,
            "new_document_count": 0,
            "target_pdf_auto_acquired_count": 0,
            "target_pdf_auto_denominator_count": 0,
            "target_pdf_auto_yield_pct": None,
            "ship_gate_status": "not_measured",
            "error": "LockBusyError: data lock is held by ui",
        }
    )
    _write(root, "data/output/last_run.json", json.dumps(payload))

    check = module.validate_install(root, after_setup=True, after_weekly=True)

    assert check.ok, check.errors
    assert check.details["last_run_status"] == "lock_busy"


def test_validate_after_weekly_accepts_not_measured_yield(tmp_path: Path) -> None:
    root = _core_install(tmp_path / "EIDP")
    _setup_artifacts(root)
    _weekly_artifacts(root)
    payload = json.loads((root / "data" / "output" / "last_run.json").read_text(encoding="utf-8"))
    payload["target_missing_school_count"] = 0
    payload["target_pdf_auto_acquired_count"] = 0
    payload["target_pdf_auto_denominator_count"] = 0
    payload["target_pdf_auto_yield_pct"] = None
    payload["ship_gate_status"] = "not_measured"
    _write(root, "data/output/last_run.json", json.dumps(payload))

    check = module.validate_install(root, after_setup=True, after_weekly=True)

    assert check.ok, check.errors
    assert check.details["last_run_status"] == "success"


def test_validate_after_bootstrap_accepts_progress_yield_and_rca_plan(tmp_path: Path) -> None:
    root = _core_install(tmp_path / "EIDP")
    _setup_artifacts(root)
    _bootstrap_artifacts(root)
    plan_rel = "data/output/target-year-discovery/bootstrap-20260505-discovery-rca-batch-plan.json"
    _write(
        root,
        plan_rel,
        json.dumps(
            {
                "total_candidates": 2,
                "items": [
                    {
                        "bucket": "target_form_without_year_evidence",
                        "packet": {"school_id": 95},
                        "prompt": "Investigate this EIDP school as a single-school RCA packet.",
                    }
                ],
            }
        ),
    )
    payload = json.loads((root / "logs" / "bootstrap-pdfs-20260505-010203.json").read_text(encoding="utf-8"))
    payload["details"]["discovery_rca_batch_plan_path"] = plan_rel
    payload["details"]["discovery_rca_batch_plan_item_count"] = 1
    payload["details"]["discovery_rca_batch_plan_total_candidates"] = 2
    _write(root, "logs/bootstrap-pdfs-20260505-010203.json", json.dumps(payload))

    check = module.validate_install(root, after_setup=True, after_bootstrap=True)

    assert check.ok, check.errors
    assert check.details["bootstrap_status"] == "succeeded"
    assert check.details["bootstrap_log_count"] == 1
    assert check.details["bootstrap_discovery_rca_batch_plan_item_count"] == 1
    assert check.details["bootstrap_discovery_rca_batch_plan_total_candidates"] == 2


def test_validate_after_bootstrap_rejects_missing_progress(tmp_path: Path) -> None:
    root = _core_install(tmp_path / "EIDP")
    _setup_artifacts(root)

    check = module.validate_install(root, after_bootstrap=True)

    assert not check.ok
    assert any("bootstrap-pdfs-*.json" in error for error in check.errors)
    assert any("bootstrap-pdfs-*.log" in error for error in check.errors)


def test_validate_after_bootstrap_requires_yield_gate_keys(tmp_path: Path) -> None:
    root = _core_install(tmp_path / "EIDP")
    _setup_artifacts(root)
    _bootstrap_artifacts(root)
    _write(
        root,
        "logs/bootstrap-pdfs-20260505-010203.json",
        json.dumps(
            {
                "status": "succeeded",
                "current_step": 5,
                "total_steps": 5,
                "percent": 1.0,
                "message": "done",
                "details": {},
            }
        ),
    )

    check = module.validate_install(root, after_bootstrap=True)

    assert not check.ok
    assert any("target_pdf_auto_yield_pct" in error for error in check.errors)
    assert any("ship_gate_status" in error for error in check.errors)


def test_validate_after_bootstrap_rejects_unknown_ship_gate_status(tmp_path: Path) -> None:
    root = _core_install(tmp_path / "EIDP")
    _setup_artifacts(root)
    _bootstrap_artifacts(root)
    payload = json.loads((root / "logs" / "bootstrap-pdfs-20260505-010203.json").read_text(encoding="utf-8"))
    payload["details"]["ship_gate_status"] = "passed"
    _write(root, "logs/bootstrap-pdfs-20260505-010203.json", json.dumps(payload))

    check = module.validate_install(root, after_bootstrap=True)

    assert not check.ok
    assert any("ship_gate_status must be pass, below_gate, or not_measured" in error for error in check.errors)


def test_validate_after_bootstrap_release_gate_rejects_below_gate(tmp_path: Path) -> None:
    root = _core_install(tmp_path / "EIDP")
    _setup_artifacts(root)
    _bootstrap_artifacts(root)
    payload = json.loads((root / "logs" / "bootstrap-pdfs-20260505-010203.json").read_text(encoding="utf-8"))
    payload["details"]["target_pdf_auto_acquired_count"] = 5
    payload["details"]["target_pdf_auto_yield_pct"] = 50.0
    payload["details"]["ship_gate_status"] = "below_gate"
    _write(root, "logs/bootstrap-pdfs-20260505-010203.json", json.dumps(payload))

    structure_only = module.validate_install(root, after_bootstrap=True)
    release_gate = module.validate_install(root, after_bootstrap=True, require_ship_gate=True)

    assert structure_only.ok, structure_only.errors
    assert not release_gate.ok
    assert any("bootstrap ship_gate_status must be pass" in error for error in release_gate.errors)


def test_validate_after_bootstrap_release_gate_rejects_pass_log_when_sqlite_coverage_is_low(
    tmp_path: Path,
) -> None:
    root = _core_install(tmp_path / "EIDP")
    _setup_artifacts(root)
    _bootstrap_artifacts(root)
    _seed_target_fy_coverage(root, total=10, acquired=5, fy=2026)

    check = module.validate_install(root, after_bootstrap=True, require_ship_gate=True)

    assert not check.ok
    assert check.details["sqlite_target_fy_specialty_school_count"] == 10
    assert check.details["sqlite_target_fy_target_pdf_school_count"] == 5
    assert any(
        "bootstrap ship_gate_status pass does not match SQLite target-FY coverage" in error
        for error in check.errors
    )


def test_validate_after_weekly_accepts_discovery_rca_batch_plan(tmp_path: Path) -> None:
    root = _core_install(tmp_path / "EIDP")
    _setup_artifacts(root)
    _weekly_artifacts(root)
    plan_rel = "data/output/target-year-discovery/20260505-discovery-rca-batch-plan.json"
    _write(
        root,
        plan_rel,
        json.dumps(
            {
                "total_candidates": 2,
                "items": [
                    {
                        "bucket": "target_form_without_year_evidence",
                        "packet": {"school_id": 95},
                        "prompt": "Investigate this EIDP school as a single-school RCA packet.",
                    }
                ],
            }
        ),
    )
    payload = json.loads((root / "data" / "output" / "last_run.json").read_text(encoding="utf-8"))
    payload["discovery_rca"] = {
        "batch_plan_path": plan_rel,
        "batch_plan_item_count": 1,
        "batch_plan_total_candidates": 2,
    }
    _write(root, "data/output/last_run.json", json.dumps(payload))

    check = module.validate_install(root, after_weekly=True)

    assert check.ok, check.errors
    assert check.details["discovery_rca_batch_plan_item_count"] == 1
    assert check.details["discovery_rca_batch_plan_total_candidates"] == 2


def test_validate_after_weekly_rejects_missing_discovery_rca_batch_plan(tmp_path: Path) -> None:
    root = _core_install(tmp_path / "EIDP")
    _setup_artifacts(root)
    _weekly_artifacts(root)
    payload = json.loads((root / "data" / "output" / "last_run.json").read_text(encoding="utf-8"))
    payload["discovery_rca"] = {
        "batch_plan_path": "data/output/target-year-discovery/missing-discovery-rca-batch-plan.json",
        "batch_plan_item_count": 1,
        "batch_plan_total_candidates": 1,
    }
    _write(root, "data/output/last_run.json", json.dumps(payload))

    check = module.validate_install(root, after_weekly=True)

    assert not check.ok
    assert any("discovery_rca batch plan is missing" in error for error in check.errors)


def test_validate_after_weekly_rejects_bad_last_run_status(tmp_path: Path) -> None:
    root = _core_install(tmp_path / "EIDP")
    _setup_artifacts(root)
    _weekly_artifacts(root)
    _write(
        root,
        "data/output/last_run.json",
        json.dumps(
            {
                "status": "running",
                "run_id": "20260505_010203",
                "started_at": "2026-05-05T01:02:03+00:00",
                "finished_at": "2026-05-05T01:02:10+00:00",
                "current_fy": 2026,
                "selection_mode": "target_missing",
                "target_missing_school_count": 7,
                "new_document_count": 2,
                "discovery_stats": {},
                "ingest_stats": {},
            }
        ),
    )

    check = module.validate_install(root, after_weekly=True)

    assert not check.ok
    assert any("status must be success" in error for error in check.errors)


def test_validate_after_weekly_rejects_failed_last_run(tmp_path: Path) -> None:
    root = _core_install(tmp_path / "EIDP")
    _setup_artifacts(root)
    _weekly_artifacts(root)
    _write(
        root,
        "data/output/last_run.json",
        json.dumps(
            {
                "status": "failed",
                "run_id": "20260505_010203",
                "started_at": "2026-05-05T01:02:03+00:00",
                "finished_at": "2026-05-05T01:02:10+00:00",
                "current_fy": 2026,
                "selection_mode": "target_missing",
                "target_missing_school_count": 7,
                "new_document_count": 2,
                "discovery_stats": {},
                "ingest_stats": {},
            }
        ),
    )

    check = module.validate_install(root, after_weekly=True)

    assert not check.ok
    assert any("status must be success" in error for error in check.errors)


def test_validate_after_weekly_requires_target_year_runner_keys(tmp_path: Path) -> None:
    root = _core_install(tmp_path / "EIDP")
    _setup_artifacts(root)
    _weekly_artifacts(root)
    _write(
        root,
        "data/output/last_run.json",
        json.dumps(
            {
                "status": "success",
                "run_id": "20260505_010203",
                "started_at": "2026-05-05T01:02:03+00:00",
                "finished_at": "2026-05-05T01:02:10+00:00",
            }
        ),
    )

    check = module.validate_install(root, after_weekly=True)

    assert not check.ok
    assert any("current_fy" in error for error in check.errors)
    assert any("target_missing_school_count" in error for error in check.errors)
    assert any("target_pdf_auto_yield_pct" in error for error in check.errors)
    assert any("ship_gate_status" in error for error in check.errors)


def test_validate_after_weekly_rejects_invalid_selection_mode(tmp_path: Path) -> None:
    root = _core_install(tmp_path / "EIDP")
    _setup_artifacts(root)
    _weekly_artifacts(root)
    payload = json.loads((root / "data" / "output" / "last_run.json").read_text(encoding="utf-8"))
    payload["selection_mode"] = "r8_legacy"
    _write(root, "data/output/last_run.json", json.dumps(payload))

    check = module.validate_install(root, after_weekly=True)

    assert not check.ok
    assert any("selection_mode" in error for error in check.errors)


def test_validate_after_weekly_rejects_unknown_ship_gate_status(tmp_path: Path) -> None:
    root = _core_install(tmp_path / "EIDP")
    _setup_artifacts(root)
    _weekly_artifacts(root)
    payload = json.loads((root / "data" / "output" / "last_run.json").read_text(encoding="utf-8"))
    payload["ship_gate_status"] = "passed"
    _write(root, "data/output/last_run.json", json.dumps(payload))

    check = module.validate_install(root, after_weekly=True)

    assert not check.ok
    assert any("ship_gate_status must be pass, below_gate, or not_measured" in error for error in check.errors)


def test_validate_after_weekly_release_gate_rejects_below_gate(tmp_path: Path) -> None:
    root = _core_install(tmp_path / "EIDP")
    _setup_artifacts(root)
    _weekly_artifacts(root)
    payload = json.loads((root / "data" / "output" / "last_run.json").read_text(encoding="utf-8"))
    payload["target_pdf_auto_acquired_count"] = 3
    payload["target_pdf_auto_yield_pct"] = 42.9
    payload["ship_gate_status"] = "below_gate"
    _write(root, "data/output/last_run.json", json.dumps(payload))

    structure_only = module.validate_install(root, after_weekly=True)
    release_gate = module.validate_install(root, after_weekly=True, require_ship_gate=True)

    assert structure_only.ok, structure_only.errors
    assert not release_gate.ok
    assert any("last_run.json ship_gate_status must be pass" in error for error in release_gate.errors)


def test_validate_after_weekly_release_gate_rejects_pass_log_when_summary_after_mismatches_sqlite(
    tmp_path: Path,
) -> None:
    root = _core_install(tmp_path / "EIDP")
    _setup_artifacts(root)
    _weekly_artifacts(root)
    _seed_target_fy_coverage(root, total=10, acquired=5, fy=2026)

    check = module.validate_install(root, after_weekly=True, require_ship_gate=True)

    assert not check.ok
    assert check.details["sqlite_target_fy_specialty_school_count"] == 10
    assert check.details["sqlite_target_fy_target_pdf_school_count"] == 5
    assert any(
        "weekly summary after.coverage does not match SQLite target-FY coverage" in error
        for error in check.errors
    )


def test_validate_requires_release_gate_source_when_ship_gate_required(tmp_path: Path) -> None:
    root = _core_install(tmp_path / "EIDP")

    check = module.validate_install(root, require_ship_gate=True)

    assert not check.ok
    assert any("--require-ship-gate requires --after-bootstrap or --after-weekly" in error for error in check.errors)


def test_validate_optional_ocr_addon(tmp_path: Path) -> None:
    root = _core_install(tmp_path / "EIDP")

    missing = module.validate_install(root, require_ocr_addon=True)
    assert not missing.ok

    _write(root, "ocr-addon/tesseract/tesseract.exe", b"PE")
    _write(root, "ocr-addon/tessdata/jpn.traineddata", b"jpn")
    present = module.validate_install(root, require_ocr_addon=True)
    assert present.ok, present.errors


def test_validate_optional_playwright_addon(tmp_path: Path) -> None:
    root = _core_install(tmp_path / "EIDP")

    missing = module.validate_install(root, require_playwright_addon=True)
    assert not missing.ok

    _mkdir(root, "playwright-addon/ms-playwright")
    _mkdir(root, "playwright-addon/wheelhouse")
    _write(root, "playwright-addon/wheelhouse/playwright-1.58.0-py3-none-win_amd64.whl", b"wheel")
    _write(root, "playwright-addon/wheelhouse/scrapling-0.4.7-py3-none-any.whl", b"wheel")
    present = module.validate_install(root, require_playwright_addon=True)
    assert present.ok, present.errors


def test_validate_optional_playwright_addon_requires_scrapling_and_playwright_wheels(tmp_path: Path) -> None:
    root = _core_install(tmp_path / "EIDP")
    _mkdir(root, "playwright-addon/ms-playwright")
    _mkdir(root, "playwright-addon/wheelhouse")

    missing_wheels = module.validate_install(root, require_playwright_addon=True)
    assert not missing_wheels.ok
    assert any("playwright-*.whl" in error for error in missing_wheels.errors)
    assert any("scrapling-*.whl" in error for error in missing_wheels.errors)


def test_cli_json_returns_nonzero_for_missing_setup_artifacts(tmp_path: Path, capsys) -> None:  # noqa: ANN001
    root = _core_install(tmp_path / "EIDP")

    rc = module.main([str(root), "--after-setup", "--json"])

    assert rc == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert any(".venv/Scripts/python.exe" in error for error in payload["errors"])


def test_vm_runbook_uses_packaged_validator_wrapper() -> None:
    """The Windows VM checklist is executed from the extracted operator
    ZIP, not from a Mac/dev checkout. Keep validation commands routed
    through validate_install.bat and keep the path-with-spaces scenario
    consistent across OCR / Playwright add-on stages."""
    body = VM_RUNBOOK_PATH.read_text(encoding="utf-8")

    assert "uv run python scripts/validate_windows_install.py" not in body
    assert '"C:\\Program Files\\EIDP\\scripts\\validate_install.bat" --after-setup' in body
    assert '"C:\\Program Files\\EIDP\\scripts\\validate_install.bat" --after-setup --after-bootstrap' in body
    assert (
        '"C:\\Program Files\\EIDP\\scripts\\validate_install.bat" '
        "--after-setup --after-bootstrap --require-ship-gate"
    ) in body
    assert '"C:\\Program Files\\EIDP\\scripts\\validate_install.bat" --after-setup --after-weekly' in body
    assert (
        '"C:\\Program Files\\EIDP\\scripts\\validate_install.bat" '
        "--after-setup --after-weekly --require-ship-gate"
    ) in body
    assert (
        '"C:\\Program Files\\EIDP\\scripts\\validate_install.bat" '
        "--after-setup --require-ocr-addon"
    ) in body
    assert (
        '"C:\\Program Files\\EIDP\\scripts\\validate_install.bat" '
        "--after-setup --require-playwright-addon"
    ) in body
