"""Sprint 8 release-gate verifier for final Windows ZIP artifacts."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import zipfile
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"
REPO_ROOT = SCRIPTS_DIR.parents[0]
SCRIPT_PATH = SCRIPTS_DIR / "verify_windows_distribution.py"
spec = importlib.util.spec_from_file_location("verify_windows_distribution", SCRIPT_PATH)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def _write_zip(path: Path, entries: dict[str, bytes | str]) -> Path:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, body in entries.items():
            data = body.encode("utf-8") if isinstance(body, str) else body
            zf.writestr(name, data)
    return path


def _prefecture_seed_csv(*, omit: set[str] | None = None, status: str = "url_found") -> str:
    omit = omit or set()
    header = (
        "pref_key,pref_jp,schools_in_db,index_url,artifact_url,artifact_format,"
        "table_cols,has_url_col,has_hyperlink_annot,as_of_date,verified_status,notes,"
        "supplemental_artifact_urls"
    )
    rows = [header]
    for index, pref in enumerate(sorted(module.EXPECTED_PREFECTURE_KEYS), start=1):
        if pref in omit:
            continue
        rows.append(
            ",".join(
                [
                    pref,
                    f"{pref}県",
                    "1",
                    f"https://example.test/{pref}/index",
                    f"https://example.test/{pref}/artifact.pdf",
                    "pdf",
                    "5",
                    "yes" if index % 2 == 0 else "no",
                    "yes" if index % 3 == 0 else "no",
                    "2026-04-01",
                    status,
                    "test seed",
                    "https://example.test/hyogo/extra.pdf" if pref == "hyogo" else "",
                ]
            )
        )
    return "\n".join(rows) + "\n"


def _prefecture_parser_source(*, omit: set[str] | None = None) -> str:
    omit = omit or set()
    entries = [
        f"    {pref!r}: lambda p: [],"
        for pref in sorted(module.EXPECTED_PREFECTURE_KEYS)
        if pref not in omit
    ]
    return "PARSERS: dict[str, object] = {\n" + "\n".join(entries) + "\n}\n"


def _discovery_gold_entry(entry_id: str, outcome: str) -> str:
    return json.dumps(
        {
            "schema_version": "discovery-gold-set/v0.1",
            "entry_id": entry_id,
            "outcome": outcome,
            "school": {"school_id": 1, "school_name": "学校", "prefecture": "東京都"},
            "target_fiscal_year": 2026,
            "manual_demonstration": {"operator_goal": "test", "steps": ["open page"]},
            "expected_result": {"pdf_url": "", "pdf_type": "", "fiscal_year": None},
            "automation_pattern": {"reusable_rules": ["test rule"]},
            "evidence": {"source_kind": "manual_web", "source_paths": ["https://example.test/"]},
        },
        ensure_ascii=False,
    ) + "\n"


def _core_entries() -> dict[str, bytes | str]:
    return {
        "BUILD_INFO.json": json.dumps(
            {
                "app": "EIDP",
                "built_at_utc": "2026-05-06T12:00:00+00:00",
                "git_commit": "a" * 40,
                "git_branch": "test",
                "git_dirty": "false",
            }
        ),
        ".streamlit/config.toml": (
            "[server]\n"
            "headless = true\n"
            "\n"
            "[browser]\n"
            "gatherUsageStats = false\n"
        ),
        "EIDP-setup.bat": (REPO_ROOT / "EIDP-setup.bat").read_text(encoding="utf-8"),
        "EIDP-start.bat": (REPO_ROOT / "EIDP-start.bat").read_text(encoding="utf-8"),
        "EIDP-diagnose.bat": (REPO_ROOT / "EIDP-diagnose.bat").read_text(encoding="utf-8"),
        "README.md": "# EIDP\n",
        "requirements-windows.txt": "structlog\n",
        "pyproject.toml": "[project]\nname='eidp'\n",
        "alembic.ini": "[alembic]\n",
        "docs/runbooks/eidp-windows.md": (
            "# runbook\n"
            "業務員クイック\n"
            "学校別タスク\n"
            "実行中のパッケージ\n"
            "詳細 operator\n"
            "週次URL/PDF再取得\n"
            "対象年度を変更して保存すると、学校別タスクも同時に再計算されます\n"
            "scripts\\weekly_run.bat` は管理者向けの復旧入口\n"
        ),
        "scripts/first_setup.bat": (SCRIPTS_DIR / "first_setup.bat").read_text(encoding="utf-8"),
        "scripts/launch.bat": (SCRIPTS_DIR / "launch.bat").read_text(encoding="utf-8"),
        "scripts/weekly_run.bat": (SCRIPTS_DIR / "weekly_run.bat").read_text(encoding="utf-8"),
        "scripts/diagnose.bat": (SCRIPTS_DIR / "diagnose.bat").read_text(encoding="utf-8"),
        "scripts/uninstall.bat": (SCRIPTS_DIR / "uninstall.bat").read_text(encoding="utf-8"),
        "scripts/validate_install.bat": (SCRIPTS_DIR / "validate_install.bat").read_text(encoding="utf-8"),
        "scripts/atomic_write.py": (SCRIPTS_DIR / "atomic_write.py").read_text(encoding="utf-8"),
        "scripts/run_weekly_target_year_discovery.py": (
            SCRIPTS_DIR / "run_weekly_target_year_discovery.py"
        ).read_text(encoding="utf-8"),
        "scripts/run_r8_rediscovery_weekly.py": (
            SCRIPTS_DIR / "run_r8_rediscovery_weekly.py"
        ).read_text(encoding="utf-8"),
        "scripts/validate_windows_install.py": (SCRIPTS_DIR / "validate_windows_install.py").read_text(
            encoding="utf-8"
        ),
        "scripts/bootstrap_pdf_pipeline.py": (SCRIPTS_DIR / "bootstrap_pdf_pipeline.py").read_text(
            encoding="utf-8"
        ),
        "scripts/ship_gate_contract.py": (SCRIPTS_DIR / "ship_gate_contract.py").read_text(encoding="utf-8"),
        "scripts/download_prefecture_artifacts.py": (SCRIPTS_DIR / "download_prefecture_artifacts.py").read_text(
            encoding="utf-8"
        ),
        "data/prefecture-aggregators/seed.csv": _prefecture_seed_csv(),
        "data/url-discovery/discovered-urls-50.csv": (
            "school_name,url\n東京都立大学,https://www.tmu.ac.jp/\n"
        ),
        "data/url-discovery/corporation_domains.csv": (
            "corporation_name,domain\n東京都公立大学法人,tmu.ac.jp\n"
        ),
        "data/discovery-gold-set/README.md": "# Discovery Gold Set\n",
        "data/discovery-gold-set/schema.json": '{"title": "test discovery gold-set schema"}\n',
        "data/discovery-gold-set/entries/accepted.json": _discovery_gold_entry(
            "accepted",
            "accepted_target_pdf",
        ),
        "data/discovery-gold-set/entries/review.json": _discovery_gold_entry(
            "review",
            "needs_operator_review",
        ),
        "data/discovery-gold-set/entries/no-target.json": _discovery_gold_entry(
            "no-target",
            "no_target_candidate_found",
        ),
        "data/discovery-gold-set/entries/publication-lag.json": _discovery_gold_entry(
            "publication-lag",
            "publication_lag_latest_public",
        ),
        "data/discovery-gold-set/entries/site-fetch-error.json": _discovery_gold_entry(
            "site-fetch-error",
            "site_fetch_error",
        ),
        "src/eidp/review/app.py": (REPO_ROOT / "src" / "eidp" / "review" / "app.py").read_text(
            encoding="utf-8"
        ),
        "src/eidp/review/operator_pages.py": (
            REPO_ROOT / "src" / "eidp" / "review" / "operator_pages.py"
        ).read_text(encoding="utf-8"),
        "src/eidp/review/_pages/audit_log.py": "def render(session, *, lock_path, jsonl_path): pass\n",
        "src/eidp/review/_pages/settings_page.py": "def render(session, *, lock_path): pass\n",
        "src/eidp/review/_pages/school_year_tasks.py": "def render(session, *, lock_path): pass\n",
        "src/eidp/review/_pages/pdf_manual_entry.py": "def render(session, *, lock_path): pass\n",
        "src/eidp/review/_pages/prefecture_remarks.py": "def render(session, *, lock_path): pass\n",
        "src/eidp/review/_pages/url_candidate_review.py": (
            REPO_ROOT / "src" / "eidp" / "review" / "_pages" / "url_candidate_review.py"
        ).read_text(encoding="utf-8"),
        "src/eidp/review/_pages/fiscal_year_override.py": "def render(session, *, lock_path): pass\n",
        "src/eidp/review/_pages/excel_preview.py": "def render(session, *, lock_path): pass\n",
        "src/eidp/review/school_scope.py": (
            'OPERATOR_SCHOOL_TYPE_SCOPE: str | None = "専門学校"\n'
            'OPERATOR_SCHOOL_SCOPE_LABEL = "専門学校"\n'
        ),
        "src/eidp/excel/exporter.py": (
            "EXCEL_MIN_EXTRACTION_CONFIDENCE = 0.70\n"
            'LOW_CONFIDENCE_EXCLUSION_SHEET = "出力除外_低信頼"\n'
            "def _exportable_confidence_sql(alias): pass\n"
            "def export_quality_warnings(session): pass\n"
            "confidence<0.70\n"
        ),
        "src/eidp/excel/competition_exporter.py": (
            REPO_ROOT / "src" / "eidp" / "excel" / "competition_exporter.py"
        ).read_text(encoding="utf-8"),
        "src/eidp/db/audit.py": (
            "from eidp.db.models import ManualActionLog\n"
            "def log_manual_action(session):\n"
            "    action_id=str(uuid.uuid4())\n"
            "    row = ManualActionLog()\n"
            "    session.flush()\n"
        ),
        "src/eidp/db/audit_outbox.py": (
            "DEFAULT_OUTBOX_PATH = Path(\"data/audit/manual-actions.jsonl\")\n"
            "def flush_audit_outbox(session):\n"
            "    ManualActionLog\n"
            "    jsonl_exported_at\n"
            "    jsonl_export_error\n"
        ),
        "src/eidp/db/sqlite_bootstrap.py": (
            REPO_ROOT / "src" / "eidp" / "db" / "sqlite_bootstrap.py"
        ).read_text(encoding="utf-8"),
        "src/eidp/scraper/pdf_discovery.py": (
            "strict_target_fiscal_year\n"
            "target_fiscal_year_not_detected\n"
            "fiscal_year_mismatch:\n"
            "target_application_not_detected\n"
            "prefecture_index_current_year\n"
            "trusted_year_evidence if strict_target_fiscal_year else \"\"\n"
        ),
        "src/eidp/pipeline/ingest.py": (
            "DepartmentYearly\n"
            "SupportRecipient\n"
            "compute_pdf_parse_breakdown\n"
            "breakdown_to_json\n"
            "revision=next_revision\n"
            "is_current=is_current_row\n"
            "support_recipient_review_pending\n"
            'doc.ingest_status = "review_pending"\n'
        ),
        "src/eidp/pipeline/manual_entry.py": (
            REPO_ROOT / "src" / "eidp" / "pipeline" / "manual_entry.py"
        ).read_text(encoding="utf-8"),
        "src/eidp/pipeline/fiscal_year_override.py": (
            REPO_ROOT / "src" / "eidp" / "pipeline" / "fiscal_year_override.py"
        ).read_text(encoding="utf-8"),
        "src/eidp/ocr/tesseract.py": (REPO_ROOT / "src" / "eidp" / "ocr" / "tesseract.py").read_text(
            encoding="utf-8"
        ),
        "src/eidp/ocr/availability.py": (REPO_ROOT / "src" / "eidp" / "ocr" / "availability.py").read_text(
            encoding="utf-8"
        ),
        "src/eidp/cli.py": (REPO_ROOT / "src" / "eidp" / "cli.py").read_text(encoding="utf-8"),
        "src/eidp/scraper/prefecture_aggregator.py": _prefecture_parser_source(),
        "runtime/python/python.exe": b"PE",
        "runtime/uv.exe": b"PE",
        "src/eidp/__init__.py": "",
        "migrations/env.py": "",
        "wheelhouse/eidp-0.2.0-py3-none-any.whl": b"wheel",
        "wheelhouse/structlog-25.5.0-py3-none-any.whl": b"wheel",
    }


def test_verify_core_zip_accepts_complete_distribution(tmp_path: Path) -> None:
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", _core_entries())

    check = module.verify_core_zip(zip_path)

    assert check.ok, check.errors
    assert check.details["has_runtime"] is True
    assert check.details["wheel_count"] == 2
    assert check.details["size_bytes"] == zip_path.stat().st_size
    assert check.details["sha256"] == hashlib.sha256(zip_path.read_bytes()).hexdigest()
    assert check.details["build_info"]["git_commit"] == "a" * 40


def test_verify_core_zip_requires_runtime(tmp_path: Path) -> None:
    entries = _core_entries()
    entries.pop("runtime/python/python.exe")
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("runtime/python/python.exe" in error for error in check.errors)


def test_verify_core_zip_requires_root_launchers(tmp_path: Path) -> None:
    entries = _core_entries()
    entries.pop("EIDP-setup.bat")
    entries.pop("EIDP-start.bat")
    entries.pop("EIDP-diagnose.bat")
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("EIDP-setup.bat" in error for error in check.errors)
    assert any("EIDP-start.bat" in error for error in check.errors)
    assert any("EIDP-diagnose.bat" in error for error in check.errors)


def test_verify_core_zip_validates_root_launcher_contract(tmp_path: Path) -> None:
    entries = _core_entries()
    entries["EIDP-start.bat"] = entries["EIDP-start.bat"].replace(
        'call "%~dp0scripts\\launch.bat"',
        'call "%~dp0scripts\\missing.bat"',
    )
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("EIDP-start.bat missing required token" in error for error in check.errors)


def test_verify_core_zip_rejects_macos_wheel(tmp_path: Path) -> None:
    entries = _core_entries()
    entries["wheelhouse/pymupdf-1.25.0-cp312-cp312-macosx_11_0_arm64.whl"] = b"wheel"
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("rejected wheel" in error for error in check.errors)


def test_verify_core_zip_requires_project_wheel(tmp_path: Path) -> None:
    entries = _core_entries()
    entries.pop("wheelhouse/eidp-0.2.0-py3-none-any.whl")
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("project wheel" in error for error in check.errors)


def test_verify_core_zip_requires_bootstrap_seed_csvs(tmp_path: Path) -> None:
    entries = _core_entries()
    entries.pop("data/url-discovery/discovered-urls-50.csv")
    entries.pop("data/url-discovery/corporation_domains.csv")
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("data/url-discovery/discovered-urls-50.csv" in error for error in check.errors)
    assert any("data/url-discovery/corporation_domains.csv" in error for error in check.errors)


def test_verify_core_zip_requires_discovery_gold_set(tmp_path: Path) -> None:
    entries = _core_entries()
    entries.pop("data/discovery-gold-set/schema.json")
    for name in list(entries):
        if name.startswith("data/discovery-gold-set/entries/"):
            entries.pop(name)
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("data/discovery-gold-set/schema.json" in error for error in check.errors)
    assert any("data/discovery-gold-set/entries/" in error for error in check.errors)


def test_verify_core_zip_reports_discovery_gold_set_summary(tmp_path: Path) -> None:
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", _core_entries())

    check = module.verify_core_zip(zip_path)

    assert check.ok, check.errors
    assert check.details["discovery_gold_set_entries"] == 5
    assert check.details["discovery_gold_set_outcomes"] == {
        "accepted_target_pdf": 1,
        "needs_operator_review": 1,
        "no_target_candidate_found": 1,
        "publication_lag_latest_public": 1,
        "site_fetch_error": 1,
    }


def test_verify_core_zip_rejects_invalid_discovery_gold_set_json(tmp_path: Path) -> None:
    entries = _core_entries()
    entries["data/discovery-gold-set/entries/accepted.json"] = "{not json"
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("invalid discovery gold-set JSON" in error for error in check.errors)


def test_verify_core_zip_requires_release_relevant_discovery_gold_outcomes(tmp_path: Path) -> None:
    entries = _core_entries()
    entries.pop("data/discovery-gold-set/entries/publication-lag.json")
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("missing discovery gold-set outcomes" in error for error in check.errors)
    assert any("publication_lag_latest_public" in error for error in check.errors)


def test_verify_core_zip_requires_discovery_gold_eval_regression_gate(tmp_path: Path) -> None:
    entries = _core_entries()
    entries["src/eidp/cli.py"] = "@app.command('eval-discovery-gold')\ndef eval_discovery_gold(): pass\n"
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("src/eidp/cli.py missing required token" in error for error in check.errors)
    assert any("--fail-on-regression" in error for error in check.errors)


def test_verify_core_zip_requires_operator_scope_vocational_only(tmp_path: Path) -> None:
    entries = _core_entries()
    entries["src/eidp/review/school_scope.py"] = (
        "OPERATOR_SCHOOL_TYPE_SCOPE: str | None = None\n"
        'OPERATOR_SCHOOL_SCOPE_LABEL = "大学・専門学校"\n'
    )
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("src/eidp/review/school_scope.py missing required token" in error for error in check.errors)
    assert any('OPERATOR_SCHOOL_TYPE_SCOPE: str | None = "専門学校"' in error for error in check.errors)


def test_verify_core_zip_requires_excel_confidence_export_gate(tmp_path: Path) -> None:
    entries = _core_entries()
    entries["src/eidp/excel/exporter.py"] = (
        "EXCEL_MIN_EXTRACTION_CONFIDENCE = 0.0\n"
        "def export_master_workbook(): pass\n"
    )
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("src/eidp/excel/exporter.py missing required token" in error for error in check.errors)
    assert any("EXCEL_MIN_EXTRACTION_CONFIDENCE = 0.70" in error for error in check.errors)


def test_verify_core_zip_requires_competition_export_target_year_gate(tmp_path: Path) -> None:
    entries = _core_entries()
    entries["src/eidp/excel/competition_exporter.py"] = (
        "def export_competition_workbook(session, template_path, output_path, fiscal_year=None):\n"
        "    fiscal_year = fiscal_year or 2025\n"
        "    return {'fiscal_year': fiscal_year}\n"
    )
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("src/eidp/excel/competition_exporter.py missing required token" in error for error in check.errors)
    assert any("TargetFiscalYearDataMissingError" in error for error in check.errors)
    assert any("settings.target_fiscal_year" in error for error in check.errors)


def test_verify_core_zip_requires_manual_action_audit_contract(tmp_path: Path) -> None:
    entries = _core_entries()
    entries["src/eidp/db/audit.py"] = "def log_manual_action(session): pass\n"
    entries["src/eidp/db/audit_outbox.py"] = "def flush_audit_outbox(session): pass\n"
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("src/eidp/db/audit.py missing required token" in error for error in check.errors)
    assert any("src/eidp/db/audit_outbox.py missing required token" in error for error in check.errors)
    assert any("ManualActionLog" in error for error in check.errors)


def test_verify_core_zip_requires_operator_action_audit_contracts(tmp_path: Path) -> None:
    entries = _core_entries()
    entries["src/eidp/review/app.py"] = "def main(): pass\n"
    entries["src/eidp/review/operator_pages.py"] = "def inject_v1_theme(): pass\n"
    entries["src/eidp/review/_pages/url_candidate_review.py"] = "def render(session): pass\n"
    entries["src/eidp/pipeline/manual_entry.py"] = "def submit_manual_entry(): pass\n"
    entries["src/eidp/pipeline/fiscal_year_override.py"] = "def override_fiscal_year(): pass\n"
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("school_code_approved" in error for error in check.errors)
    assert any("url_candidate_approved" in error for error in check.errors)
    assert any("dept_alias_approved" in error for error in check.errors)
    assert any("manual_entry" in error for error in check.errors)
    assert any("fiscal_year_override" in error for error in check.errors)


def test_verify_core_zip_requires_sqlite_bootstrap_data_loss_guards(tmp_path: Path) -> None:
    entries = _core_entries()
    entries["src/eidp/db/sqlite_bootstrap.py"] = "def bootstrap_sqlite(engine): pass\n"
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("src/eidp/db/sqlite_bootstrap.py missing required token" in error for error in check.errors)
    assert any("PRAGMA integrity_check" in error for error in check.errors)
    assert any("ensure_sqlite_additive_columns" in error for error in check.errors)
    assert any("_refuse_orphaned_sqlite_sidecars" in error for error in check.errors)


def test_verify_core_zip_requires_strict_target_year_pdf_discovery(tmp_path: Path) -> None:
    entries = _core_entries()
    entries["src/eidp/scraper/pdf_discovery.py"] = "def run_pdf_discovery(): pass\n"
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("src/eidp/scraper/pdf_discovery.py missing required token" in error for error in check.errors)
    assert any("target_fiscal_year_not_detected" in error for error in check.errors)


def test_verify_core_zip_requires_append_only_confidence_ingest(tmp_path: Path) -> None:
    entries = _core_entries()
    entries["src/eidp/pipeline/ingest.py"] = "def ingest_document(): pass\n"
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("src/eidp/pipeline/ingest.py missing required token" in error for error in check.errors)
    assert any("compute_pdf_parse_breakdown" in error for error in check.errors)


def test_verify_core_zip_requires_ocr_tesseract_runtime_contract(tmp_path: Path) -> None:
    entries = _core_entries()
    entries["src/eidp/ocr/tesseract.py"] = "def locate_tesseract(): pass\n"
    entries["src/eidp/ocr/availability.py"] = "def detect_ocr_availability(): pass\n"
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("src/eidp/ocr/tesseract.py missing required token" in error for error in check.errors)
    assert any("src/eidp/ocr/availability.py missing required token" in error for error in check.errors)
    assert any("tesseract.exe" in error for error in check.errors)
    assert any("jpn.traineddata" in error for error in check.errors)


def test_verify_core_zip_requires_validator_sqlite_integrity_contract(tmp_path: Path) -> None:
    entries = _core_entries()
    entries["scripts/validate_windows_install.py"] = (
        "CORE_FILES\n"
        "build_commit\n"
        "scripts/validate_install.bat\n"
        "--after-setup\n"
        "--after-bootstrap\n"
        "--after-weekly\n"
        "--require-ocr-addon\n"
        "--require-playwright-addon\n"
        "last_run.json status must be success\n"
    )
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("scripts/validate_windows_install.py missing required token" in error for error in check.errors)
    assert any("support_recipient" in error for error in check.errors)
    assert any("sqlite_integrity_check" in error for error in check.errors)


def test_verify_core_zip_requires_all_prefecture_seed_rows(tmp_path: Path) -> None:
    entries = _core_entries()
    entries["data/prefecture-aggregators/seed.csv"] = _prefecture_seed_csv(omit={"tokyo"})
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("must contain exactly 47 current prefecture rows" in error for error in check.errors)
    assert any("tokyo" in error for error in check.errors)


def test_verify_core_zip_requires_parser_for_every_prefecture_seed(tmp_path: Path) -> None:
    entries = _core_entries()
    entries["src/eidp/scraper/prefecture_aggregator.py"] = _prefecture_parser_source(omit={"tokyo"})
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("PARSERS missing seed prefectures" in error and "tokyo" in error for error in check.errors)


def test_verify_core_zip_requires_downloadable_prefecture_artifacts(tmp_path: Path) -> None:
    entries = _core_entries()
    entries["data/prefecture-aggregators/seed.csv"] = _prefecture_seed_csv(status="todo")
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("non-downloadable prefecture statuses" in error for error in check.errors)


def test_verify_core_zip_requires_settings_page_module(tmp_path: Path) -> None:
    entries = _core_entries()
    entries.pop("src/eidp/review/_pages/settings_page.py")
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("src/eidp/review/_pages/settings_page.py" in error for error in check.errors)


def test_verify_core_zip_requires_cli_report_database_not_ready_gate(tmp_path: Path) -> None:
    entries = _core_entries()
    entries["src/eidp/cli.py"] = (
        '@app.command("eval-discovery-gold")\n'
        "--fail-on-regression\n"
        "_discovery_gold_gate_failed\n"
    )
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("src/eidp/cli.py missing required token" in error for error in check.errors)
    assert any("database_not_ready" in error for error in check.errors)


def test_verify_core_zip_requires_all_navigated_operator_modules(tmp_path: Path) -> None:
    entries = _core_entries()
    for rel in (
        "src/eidp/review/operator_pages.py",
        "src/eidp/review/_pages/audit_log.py",
        "src/eidp/review/_pages/prefecture_remarks.py",
    ):
        entries.pop(rel)
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("src/eidp/review/operator_pages.py" in error for error in check.errors)
    assert any("src/eidp/review/_pages/audit_log.py" in error for error in check.errors)
    assert any("src/eidp/review/_pages/prefecture_remarks.py" in error for error in check.errors)


def test_verify_core_zip_validates_bootstrap_pipeline_contract(tmp_path: Path) -> None:
    entries = _core_entries()
    entries["scripts/bootstrap_pdf_pipeline.py"] = entries["scripts/bootstrap_pdf_pipeline.py"].replace(
        "prefecture_aggregator,seed_csv,corporation_pattern,scrapling_stealth",
        "prefecture_aggregator",
    )
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any(
        "prefecture_aggregator,seed_csv,corporation_pattern,scrapling_stealth" in error
        for error in check.errors
    )


def test_verify_core_zip_rejects_multiple_project_wheels(tmp_path: Path) -> None:
    entries = _core_entries()
    entries["wheelhouse/eidp-0.2.1-py3-none-any.whl"] = b"wheel"
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("multiple project wheels" in error for error in check.errors)


def test_verify_core_zip_rejects_duplicate_dependency_wheels(tmp_path: Path) -> None:
    entries = _core_entries()
    entries["wheelhouse/structlog-25.6.0-py3-none-any.whl"] = b"wheel"
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("duplicate distributions" in error for error in check.errors)


def test_verify_core_zip_rejects_case_insensitive_path_collision(tmp_path: Path) -> None:
    entries = _core_entries()
    entries["docs/Runbooks/eidp-windows.md"] = "# duplicate by case\n"
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("case-insensitive path collisions" in error for error in check.errors)


def test_verify_core_zip_rejects_windows_reserved_component(tmp_path: Path) -> None:
    entries = _core_entries()
    entries["docs/runbooks/CON.txt"] = "bad"
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("reserved path components" in error for error in check.errors)


def test_verify_core_zip_rejects_parent_directory_entry(tmp_path: Path) -> None:
    entries = _core_entries()
    entries["../escape.txt"] = "bad"
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("parent-directory" in error for error in check.errors)


def test_verify_core_zip_rejects_duplicate_entries(tmp_path: Path) -> None:
    zip_path = tmp_path / "eidp-windows.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, body in _core_entries().items():
            data = body.encode("utf-8") if isinstance(body, str) else body
            zf.writestr(name, data)
        with pytest.warns(UserWarning, match="Duplicate name"):
            zf.writestr("README.md", "# duplicate\n")

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("duplicate entries" in error for error in check.errors)


def test_verify_core_zip_rejects_stale_launch_bat_contract(tmp_path: Path) -> None:
    entries = _core_entries()
    entries["scripts/launch.bat"] = entries["scripts/launch.bat"].replace(
        'set "RC=%ERRORLEVEL%"',
        "REM stale launcher missing rc capture",
    )
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("scripts/launch.bat missing required token" in error for error in check.errors)


def test_verify_core_zip_rejects_bare_rc_assignment_in_root_launcher(tmp_path: Path) -> None:
    entries = _core_entries()
    entries["EIDP-start.bat"] = entries["EIDP-start.bat"].replace(
        'set "RC=%ERRORLEVEL%"',
        '"RC=-1"',
    )
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("bare RC assignment" in error for error in check.errors)


def test_verify_core_zip_rejects_launcher_that_does_not_open_browser(tmp_path: Path) -> None:
    entries = _core_entries()
    entries["scripts/launch.bat"] = entries["scripts/launch.bat"].replace(
        "Start-Process 'http://localhost:8501'",
        "REM stale launcher missing browser open",
    )
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("http://localhost:8501" in error for error in check.errors)


def test_verify_core_zip_rejects_locale_dependent_weekly_bat(tmp_path: Path) -> None:
    entries = _core_entries()
    entries["scripts/weekly_run.bat"] = entries["scripts/weekly_run.bat"] + "\nset DATESTAMP=%DATE:~0,8%\n"
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("%date:~" in error for error in check.errors)


def test_verify_core_zip_rejects_uninstall_that_deletes_data(tmp_path: Path) -> None:
    entries = _core_entries()
    entries["scripts/uninstall.bat"] = entries["scripts/uninstall.bat"] + "\nrmdir /s /q data\n"
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("scripts/uninstall.bat contains forbidden token: rmdir" in error for error in check.errors)


def test_verify_core_zip_rejects_stale_validator_missing_playwright_flag(tmp_path: Path) -> None:
    entries = _core_entries()
    entries["scripts/validate_windows_install.py"] = entries["scripts/validate_windows_install.py"].replace(
        "--require-playwright-addon",
        "--missing-playwright-addon",
    )
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("--require-playwright-addon" in error for error in check.errors)


def test_verify_core_zip_rejects_stale_validator_missing_bootstrap_flag(tmp_path: Path) -> None:
    entries = _core_entries()
    entries["scripts/validate_windows_install.py"] = entries["scripts/validate_windows_install.py"].replace(
        "--after-bootstrap",
        "--missing-bootstrap",
    )
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("--after-bootstrap" in error for error in check.errors)


def test_verify_core_zip_rejects_diagnose_without_bootstrap_validation(tmp_path: Path) -> None:
    entries = _core_entries()
    entries["scripts/diagnose.bat"] = entries["scripts/diagnose.bat"].replace(
        "--after-setup --after-bootstrap",
        "--after-setup",
    )
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("--after-bootstrap" in error for error in check.errors)


def test_verify_core_zip_rejects_diagnose_without_weekly_validation(tmp_path: Path) -> None:
    entries = _core_entries()
    entries["scripts/diagnose.bat"] = entries["scripts/diagnose.bat"].replace(
        "--after-setup --after-weekly",
        "--after-setup",
    )
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("--after-weekly" in error for error in check.errors)


def test_verify_core_zip_rejects_weekly_runner_export_excel(tmp_path: Path) -> None:
    entries = _core_entries()
    entries["scripts/run_weekly_target_year_discovery.py"] = (
        entries["scripts/run_weekly_target_year_discovery.py"] + "\nexport_excel()\n"
    )
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("export_excel" in error for error in check.errors)


def test_verify_core_zip_rejects_stale_operator_runbook(tmp_path: Path) -> None:
    entries = _core_entries()
    entries["docs/runbooks/eidp-windows.md"] = (
        "# runbook\n"
        "画面左のサイドバーに 12 ページが表示されます。\n"
        "データ状況\n"
    )
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("学校別タスク" in error for error in check.errors)
    assert any("12 ページ" in error for error in check.errors)


def test_verify_core_zip_requires_current_operator_runbook_guidance(tmp_path: Path) -> None:
    entries = _core_entries()
    entries["docs/runbooks/eidp-windows.md"] = (
        "# runbook\n"
        "業務員クイック\n"
        "学校別タスク\n"
        "詳細 operator\n"
    )
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("週次URL/PDF再取得" in error for error in check.errors)
    assert any("学校別タスクも同時に再計算" in error for error in check.errors)
    assert any("weekly_run.bat" in error for error in check.errors)


def test_verify_ocr_addon_accepts_manifest(tmp_path: Path) -> None:
    tesseract = b"PE"
    tessdata = b"jpn"
    manifest = {
        "layout_version": 1,
        "files": [
            {
                "path": "ocr-addon/tesseract/tesseract.exe",
                "size": len(tesseract),
                "sha256": hashlib.sha256(tesseract).hexdigest(),
            },
            {
                "path": "ocr-addon/tessdata/jpn.traineddata",
                "size": len(tessdata),
                "sha256": hashlib.sha256(tessdata).hexdigest(),
            },
        ],
    }
    zip_path = _write_zip(
        tmp_path / "eidp-ocr-addon-windows.zip",
        {
            "ocr-addon/tesseract/tesseract.exe": tesseract,
            "ocr-addon/tessdata/jpn.traineddata": tessdata,
            "ocr-addon/MANIFEST.json": json.dumps(manifest),
        },
    )

    check = module.verify_ocr_addon_zip(zip_path)

    assert check.ok, check.errors
    assert check.details["manifest_files"] == 2


def test_verify_ocr_addon_requires_manifest_paths(tmp_path: Path) -> None:
    zip_path = _write_zip(
        tmp_path / "eidp-ocr-addon-windows.zip",
        {
            "ocr-addon/tesseract/tesseract.exe": b"PE",
            "ocr-addon/tessdata/jpn.traineddata": b"jpn",
            "ocr-addon/MANIFEST.json": json.dumps({"layout_version": 1, "files": []}),
        },
    )

    check = module.verify_ocr_addon_zip(zip_path)

    assert not check.ok
    assert any("manifest missing required file path" in error for error in check.errors)


def test_verify_ocr_addon_rejects_manifest_checksum_mismatch(tmp_path: Path) -> None:
    manifest = {
        "layout_version": 1,
        "files": [
            {
                "path": "ocr-addon/tesseract/tesseract.exe",
                "size": 2,
                "sha256": hashlib.sha256(b"wrong").hexdigest(),
            },
            {
                "path": "ocr-addon/tessdata/jpn.traineddata",
                "size": 3,
                "sha256": hashlib.sha256(b"jpn").hexdigest(),
            },
        ],
    }
    zip_path = _write_zip(
        tmp_path / "eidp-ocr-addon-windows.zip",
        {
            "ocr-addon/tesseract/tesseract.exe": b"PE",
            "ocr-addon/tessdata/jpn.traineddata": b"jpn",
            "ocr-addon/MANIFEST.json": json.dumps(manifest),
        },
    )

    check = module.verify_ocr_addon_zip(zip_path)

    assert not check.ok
    assert any("manifest sha256 mismatch" in error for error in check.errors)


def test_verify_ocr_addon_rejects_unlisted_payload_entry(tmp_path: Path) -> None:
    manifest = {
        "layout_version": 1,
        "files": [
            {
                "path": "ocr-addon/tesseract/tesseract.exe",
                "size": 2,
                "sha256": hashlib.sha256(b"PE").hexdigest(),
            },
            {
                "path": "ocr-addon/tessdata/jpn.traineddata",
                "size": 3,
                "sha256": hashlib.sha256(b"jpn").hexdigest(),
            },
        ],
    }
    zip_path = _write_zip(
        tmp_path / "eidp-ocr-addon-windows.zip",
        {
            "ocr-addon/tesseract/tesseract.exe": b"PE",
            "ocr-addon/tesseract/extra.dll": b"dll",
            "ocr-addon/tessdata/jpn.traineddata": b"jpn",
            "ocr-addon/MANIFEST.json": json.dumps(manifest),
        },
    )

    check = module.verify_ocr_addon_zip(zip_path)

    assert not check.ok
    assert any("manifest missing ZIP payload entries" in error for error in check.errors)


def test_verify_ocr_addon_rejects_duplicate_manifest_path(tmp_path: Path) -> None:
    entry = {
        "path": "ocr-addon/tesseract/tesseract.exe",
        "size": 2,
        "sha256": hashlib.sha256(b"PE").hexdigest(),
    }
    manifest = {
        "layout_version": 1,
        "files": [
            entry,
            entry,
            {
                "path": "ocr-addon/tessdata/jpn.traineddata",
                "size": 3,
                "sha256": hashlib.sha256(b"jpn").hexdigest(),
            },
        ],
    }
    zip_path = _write_zip(
        tmp_path / "eidp-ocr-addon-windows.zip",
        {
            "ocr-addon/tesseract/tesseract.exe": b"PE",
            "ocr-addon/tessdata/jpn.traineddata": b"jpn",
            "ocr-addon/MANIFEST.json": json.dumps(manifest),
        },
    )

    check = module.verify_ocr_addon_zip(zip_path)

    assert not check.ok
    assert any("duplicate file path" in error for error in check.errors)


def test_verify_playwright_addon_accepts_chromium_and_wheel(tmp_path: Path) -> None:
    wheel = b"wheel"
    scrapling_wheel = b"scrapling"
    chrome = b"PE"
    manifest = {
        "layout_version": 1,
        "files": [
            {
                "path": "playwright-addon/wheelhouse/playwright-1.58.0-py3-none-win_amd64.whl",
                "size": len(wheel),
                "sha256": hashlib.sha256(wheel).hexdigest(),
            },
            {
                "path": "playwright-addon/wheelhouse/scrapling-0.4.7-py3-none-any.whl",
                "size": len(scrapling_wheel),
                "sha256": hashlib.sha256(scrapling_wheel).hexdigest(),
            },
            {
                "path": "playwright-addon/ms-playwright/chromium-1234/chrome-win/chrome.exe",
                "size": len(chrome),
                "sha256": hashlib.sha256(chrome).hexdigest(),
            },
        ],
    }
    zip_path = _write_zip(
        tmp_path / "eidp-playwright-addon-windows.zip",
        {
            "playwright-addon/wheelhouse/playwright-1.58.0-py3-none-win_amd64.whl": wheel,
            "playwright-addon/wheelhouse/scrapling-0.4.7-py3-none-any.whl": scrapling_wheel,
            "playwright-addon/ms-playwright/chromium-1234/chrome-win/chrome.exe": chrome,
            "playwright-addon/MANIFEST.json": json.dumps(manifest),
        },
    )

    check = module.verify_playwright_addon_zip(zip_path)

    assert check.ok, check.errors
    assert check.details["manifest_files"] == 3


def test_verify_playwright_addon_requires_chrome_exe(tmp_path: Path) -> None:
    zip_path = _write_zip(
        tmp_path / "eidp-playwright-addon-windows.zip",
        {
            "playwright-addon/wheelhouse/playwright-1.58.0-py3-none-win_amd64.whl": b"wheel",
            "playwright-addon/wheelhouse/scrapling-0.4.7-py3-none-any.whl": b"scrapling",
            "playwright-addon/ms-playwright/chromium-1234/chrome-win/chrome.dll": b"dll",
            "playwright-addon/MANIFEST.json": json.dumps({"layout_version": 1, "files": []}),
        },
    )

    check = module.verify_playwright_addon_zip(zip_path)

    assert not check.ok
    assert any("chrome.exe" in error for error in check.errors)


def test_verify_playwright_addon_requires_scrapling_wheel(tmp_path: Path) -> None:
    zip_path = _write_zip(
        tmp_path / "eidp-playwright-addon-windows.zip",
        {
            "playwright-addon/wheelhouse/playwright-1.58.0-py3-none-win_amd64.whl": b"wheel",
            "playwright-addon/ms-playwright/chromium-1234/chrome-win/chrome.exe": b"PE",
            "playwright-addon/MANIFEST.json": json.dumps({"layout_version": 1, "files": []}),
        },
    )

    check = module.verify_playwright_addon_zip(zip_path)

    assert not check.ok
    assert any("scrapling-*.whl" in error for error in check.errors)


def test_cli_returns_nonzero_for_failed_distribution(tmp_path: Path, capsys) -> None:  # noqa: ANN001
    entries = _core_entries()
    entries.pop("runtime/uv.exe")
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    rc = module.main([str(zip_path)])

    assert rc == 1
    output = capsys.readouterr().out
    assert "FAIL core" in output
    assert "runtime/uv.exe" in output


def test_cli_json_includes_distribution_checksum(tmp_path: Path, capsys) -> None:  # noqa: ANN001
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", _core_entries())

    rc = module.main([str(zip_path), "--json"])

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload[0]["ok"] is True
    assert payload[0]["details"]["sha256"] == hashlib.sha256(zip_path.read_bytes()).hexdigest()
    assert payload[0]["details"]["size_bytes"] == zip_path.stat().st_size
