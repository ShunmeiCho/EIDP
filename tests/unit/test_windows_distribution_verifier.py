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
    expected_result: dict[str, object] = {"pdf_url": "", "pdf_type": "", "fiscal_year": None}
    if outcome == "accepted_target_pdf":
        expected_result = {
            "pdf_url": f"https://example.test/{entry_id}.pdf",
            "pdf_type": "target",
            "fiscal_year": 2026,
            "strict_target_year_success": True,
        }
    elif outcome == "publication_lag_latest_public":
        expected_result = {
            "pdf_url": f"https://example.test/{entry_id}-r7.pdf",
            "pdf_type": "target",
            "fiscal_year": 2025,
            "strict_target_year_success": False,
            "pattern_type": "wordpress_download_manager",
        }
    elif outcome == "needs_operator_review":
        expected_result = {
            "pdf_url": f"https://example.test/{entry_id}.pdf",
            "pdf_type": "image_only",
            "fiscal_year": None,
            "strict_target_year_success": False,
        }
    else:
        expected_result["strict_target_year_success"] = False

    return json.dumps(
        {
            "schema_version": "discovery-gold-set/v0.1",
            "entry_id": entry_id,
            "outcome": outcome,
            "school": {"school_id": 1, "school_name": "学校", "prefecture": "東京都"},
            "target_fiscal_year": 2026,
            "manual_demonstration": {"operator_goal": "test", "steps": ["open page"]},
            "expected_result": expected_result,
            "automation_pattern": {"reusable_rules": ["test rule"]},
            "evidence": {"source_kind": "manual_web", "source_paths": ["https://example.test/"]},
        },
        ensure_ascii=False,
    ) + "\n"


def _discovery_gold_expected_predictions() -> str:
    lines = []
    for entry_id, outcome in (
        ("accepted", "accepted_target_pdf"),
        ("review", "needs_operator_review"),
        ("no-target", "no_target_candidate_found"),
        ("publication-lag", "publication_lag_latest_public"),
        ("site-fetch-error", "site_fetch_error"),
    ):
        payload = json.loads(_discovery_gold_entry(entry_id, outcome))
        expected = payload["expected_result"]
        lines.append(
            json.dumps(
                {
                    "entry_id": payload["entry_id"],
                    "outcome": payload["outcome"],
                    "pdf_url": expected.get("pdf_url") or "",
                    "fiscal_year": expected.get("fiscal_year"),
                    "strict_target_year_success": bool(expected.get("strict_target_year_success", False)),
                    **({"pattern_type": expected["pattern_type"]} if expected.get("pattern_type") else {}),
                },
                sort_keys=True,
            )
        )
    return "\n".join(lines) + "\n"


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
        "EIDP-stage6-evidence.bat": (REPO_ROOT / "EIDP-stage6-evidence.bat").read_text(encoding="utf-8"),
        "EIDP-stage6-verify-evidence.bat": (REPO_ROOT / "EIDP-stage6-verify-evidence.bat").read_text(
            encoding="utf-8"
        ),
        "EIDP-stage6-recovery.bat": (REPO_ROOT / "EIDP-stage6-recovery.bat").read_text(encoding="utf-8"),
        "README.md": "# EIDP\n",
        "requirements-windows.txt": "structlog\njsonschema>=4.0,<5.0\n",
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
            "logs\\stage6-recovery-*.json\n"
            "EIDP-stage6-recovery.bat\n"
            "stage6_residual_cleanup.bat\n"
            "logs\\stage6-residual-cleanup-*.json\n"
            "logs\\stage6-residual-archive\\<timestamp>\n"
            "ClearAllForwardings=no\n"
            "ExitOnForwardFailure=yes\n"
            "127.0.0.1:18501:127.0.0.1:8501\n"
            "127.0.0.1:18501/_stcore/health\n"
            "127.0.0.1:18502:127.0.0.1:8502\n"
            "logs\\stage6-evidence-*.zip\n"
            "EIDP-stage6-evidence.bat\n"
            "EIDP-stage6-verify-evidence.bat\n"
            "stage6-evidence-verify-*.json\n"
            "scripts\\stage6_recovery_check.bat\n"
            "verify_stage6_evidence.py\n"
            "--require-label last_run\n"
            "アンチウイルスにより隔離された\n"
            "新しい ZIP へ更新する場合\n"
            "data\\eidp.sqlite3-wal\n"
            "data\\eidp.sqlite3-shm\n"
            "PRAGMA wal_checkpoint(TRUNCATE)\n"
            "VACUUM INTO\n"
            "db-backup --output $dbBackup\n"
            "eidp-backup-$ts.sqlite3\n"
            'Get-ChildItem "$old\\data" -Force\n'
            '$_.Name -notlike "eidp-backup-*.sqlite3"\n'
            "data\\.lock\n"
            '/XF ".lock" "eidp.sqlite3-wal" "eidp.sqlite3-shm" "eidp-backup-*.sqlite3"\n'
        ),
        "docs/runbooks/eidp-operator-e2e-template.md": (
            "# E2E\n"
            "ship_readiness_rc\n"
            "retroactive_fiscal_year\n"
            "is_retroactive_fiscal_year\n"
            "retroactive_ship_readiness_rc\n"
            "stage6_recovery_rc\n"
            "stage6 recovery check\n"
            "task.execute\n"
            "task.expected_action\n"
            "task.action_matches_expected\n"
            "residual_paths\n"
            "logs\\stage6-residual-cleanup-*.json\n"
            "recommendations\n"
            "strict target PDF 自動取得率\n"
            "推定手作業率\n"
            "release exception reason\n"
            "mature-year proof JSON\n"
            "mature-year proof years\n"
            "Excel ready 率\n"
            "logs\\diagnostics-*.txt\n"
            "127.0.0.1:18501:127.0.0.1:8501\n"
            "127.0.0.1:18501/_stcore/health\n"
            "Mac tunnel health\n"
            "logs\\stage6-evidence-*.zip\n"
            "logs\\stage6-evidence-verify-*.json\n"
            "logs\\stage6-recovery-*.json\n"
            "Get-Volume C\n"
            "ipconfig /flushdns\n"
            "data\\.lock.meta\n"
            "Get-ScheduledTaskInfo -TaskName\n"
            "Task Scheduler retry\n"
            "現行投入候補（Mac / non-Windows gate 済み、Windows 未実証）:\n"
            "| core ZIP | `dist/eidp-windows-vXXX.zip` |\n"
            "| core ZIP sha256 sidecar note | `.sha256` は repo-relative path を記録する。 |\n"
            "| non-Windows gate log | `logs/release-gate-vXXX-retroactive.json` |\n"
            "## 3. 証跡採取コマンド\n"
            '$zip = "C:\\EIDP-staging\\<core-zip-file-name>"\n'
            '$expected = "<copy SHA256 from .sha256 sidecar or current-release-status>"\n'
            "Get-FileHash $zip -Algorithm SHA256\n"
            "v1.0-rc\n"
            "FY2026/R8 の current-year yield gate\n"
        ),
        "scripts/first_setup.bat": (SCRIPTS_DIR / "first_setup.bat").read_text(encoding="utf-8"),
        "scripts/launch.bat": (SCRIPTS_DIR / "launch.bat").read_text(encoding="utf-8"),
        "scripts/weekly_run.bat": (SCRIPTS_DIR / "weekly_run.bat").read_text(encoding="utf-8"),
        "scripts/bootstrap_pdfs.bat": (SCRIPTS_DIR / "bootstrap_pdfs.bat").read_text(encoding="utf-8"),
        "scripts/diagnose.bat": (SCRIPTS_DIR / "diagnose.bat").read_text(encoding="utf-8"),
        "scripts/collect_stage6_evidence.bat": (SCRIPTS_DIR / "collect_stage6_evidence.bat").read_text(
            encoding="utf-8"
        ),
        "scripts/collect_bug_report.bat": (SCRIPTS_DIR / "collect_bug_report.bat").read_text(encoding="utf-8"),
        "scripts/verify_stage6_evidence.bat": (SCRIPTS_DIR / "verify_stage6_evidence.bat").read_text(
            encoding="utf-8"
        ),
        "scripts/uninstall.bat": (SCRIPTS_DIR / "uninstall.bat").read_text(encoding="utf-8"),
        "scripts/validate_install.bat": (SCRIPTS_DIR / "validate_install.bat").read_text(encoding="utf-8"),
        "scripts/stage6_recovery_check.bat": (SCRIPTS_DIR / "stage6_recovery_check.bat").read_text(
            encoding="utf-8"
        ),
        "scripts/stage6_residual_cleanup.bat": (SCRIPTS_DIR / "stage6_residual_cleanup.bat").read_text(
            encoding="utf-8"
        ),
        "scripts/atomic_write.py": (SCRIPTS_DIR / "atomic_write.py").read_text(encoding="utf-8"),
        "scripts/run_weekly_target_year_discovery.py": (
            SCRIPTS_DIR / "run_weekly_target_year_discovery.py"
        ).read_text(encoding="utf-8"),
        "scripts/run_r8_rediscovery_weekly.py": (
            SCRIPTS_DIR / "run_r8_rediscovery_weekly.py"
        ).read_text(encoding="utf-8"),
        "scripts/offline_pip_install.py": (SCRIPTS_DIR / "offline_pip_install.py").read_text(encoding="utf-8"),
        "scripts/validate_windows_install.py": (SCRIPTS_DIR / "validate_windows_install.py").read_text(
            encoding="utf-8"
        ),
        "scripts/collect_stage6_evidence.py": (SCRIPTS_DIR / "collect_stage6_evidence.py").read_text(
            encoding="utf-8"
        ),
        "scripts/collect_bug_report.py": (SCRIPTS_DIR / "collect_bug_report.py").read_text(encoding="utf-8"),
        "scripts/verify_stage6_evidence.py": (SCRIPTS_DIR / "verify_stage6_evidence.py").read_text(
            encoding="utf-8"
        ),
        "scripts/verify_stage6_return.py": (SCRIPTS_DIR / "verify_stage6_return.py").read_text(encoding="utf-8"),
        "scripts/build_mature_year_acquisition_proof.py": (
            SCRIPTS_DIR / "build_mature_year_acquisition_proof.py"
        ).read_text(encoding="utf-8"),
        "scripts/stage6_recovery_check.py": (SCRIPTS_DIR / "stage6_recovery_check.py").read_text(
            encoding="utf-8"
        ),
        "scripts/stage6_residual_cleanup.py": (SCRIPTS_DIR / "stage6_residual_cleanup.py").read_text(
            encoding="utf-8"
        ),
        "scripts/bootstrap_pdf_pipeline.py": (SCRIPTS_DIR / "bootstrap_pdf_pipeline.py").read_text(
            encoding="utf-8"
        ),
        "scripts/ship_gate_contract.py": (SCRIPTS_DIR / "ship_gate_contract.py").read_text(encoding="utf-8"),
        "scripts/download_prefecture_artifacts.py": (SCRIPTS_DIR / "download_prefecture_artifacts.py").read_text(
            encoding="utf-8"
        ),
        "scripts/prune_release_artifacts.py": (SCRIPTS_DIR / "prune_release_artifacts.py").read_text(
            encoding="utf-8"
        ),
        "scripts/rotate_audit_outbox.py": (SCRIPTS_DIR / "rotate_audit_outbox.py").read_text(
            encoding="utf-8"
        ),
        "scripts/prune_pdf_storage.py": (SCRIPTS_DIR / "prune_pdf_storage.py").read_text(encoding="utf-8"),
        "scripts/disk_health_check.py": (SCRIPTS_DIR / "disk_health_check.py").read_text(encoding="utf-8"),
        "src/eidp/windows_platform.py": (REPO_ROOT / "src" / "eidp" / "windows_platform.py").read_text(
            encoding="utf-8"
        ),
        "src/sitecustomize.py": (REPO_ROOT / "src" / "sitecustomize.py").read_text(encoding="utf-8"),
        "data/prefecture-aggregators/seed.csv": _prefecture_seed_csv(),
        "data/url-discovery/discovered-urls-50.csv": (
            "school_name,url\n東京都立大学,https://www.tmu.ac.jp/\n"
        ),
        "data/url-discovery/corporation_domains.csv": (
            "corporation_name,domain\n東京都公立大学法人,tmu.ac.jp\n"
        ),
        "data/url-discovery/school_domain_overrides.csv": (
            "prefecture,corporation_name,school_name,domain_url,url_type,confidence\n"
            "東京都,東京都公立大学法人,東京都立大学,https://www.tmu.ac.jp/,school,0.95\n"
        ),
        "data/discovery-gold-set/README.md": "# Discovery Gold Set\n",
        "data/discovery-gold-set/schema.json": '{"title": "test discovery gold-set schema"}\n',
        "data/discovery-gold-set/expected-predictions.jsonl": _discovery_gold_expected_predictions(),
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
        "src/eidp/review/_pages/bug_report.py": (
            REPO_ROOT / "src" / "eidp" / "review" / "_pages" / "bug_report.py"
        ).read_text(encoding="utf-8"),
        "src/eidp/bug_signals/detector.py": (
            REPO_ROOT / "src" / "eidp" / "bug_signals" / "detector.py"
        ).read_text(encoding="utf-8"),
        "src/eidp/bug_signals/bundle.py": (
            REPO_ROOT / "src" / "eidp" / "bug_signals" / "bundle.py"
        ).read_text(encoding="utf-8"),
        "src/eidp/review/_pages/audit_log.py": "def render(session, *, lock_path, jsonl_path): pass\n",
        "src/eidp/review/_pages/settings_page.py": (
            REPO_ROOT / "src" / "eidp" / "review" / "_pages" / "settings_page.py"
        ).read_text(encoding="utf-8"),
        "src/eidp/review/_pages/school_year_tasks.py": (
            REPO_ROOT / "src" / "eidp" / "review" / "_pages" / "school_year_tasks.py"
        ).read_text(encoding="utf-8"),
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
        "src/eidp/config.py": (REPO_ROOT / "src" / "eidp" / "config.py").read_text(encoding="utf-8"),
        "src/eidp/fiscal_year.py": (REPO_ROOT / "src" / "eidp" / "fiscal_year.py").read_text(encoding="utf-8"),
        "src/eidp/excel/exporter.py": (
            "from eidp.extraction_confidence import thresholds_from_env\n"
            "def excel_confidence_thresholds(): pass\n"
            "def excel_min_extraction_confidence(): pass\n"
            "def excel_auto_flag_extraction_confidence(): pass\n"
            'LOW_CONFIDENCE_EXCLUSION_SHEET = "出力除外_低信頼"\n'
            "def _exportable_confidence_sql(alias):\n"
            "    return excel_min_extraction_confidence()\n"
            "def export_quality_warnings(session): pass\n"
            "def _low_confidence_reason(): pass\n"
        ),
        "src/eidp/excel/competition_exporter.py": (
            REPO_ROOT / "src" / "eidp" / "excel" / "competition_exporter.py"
        ).read_text(encoding="utf-8"),
        "src/eidp/reports/coverage.py": (REPO_ROOT / "src" / "eidp" / "reports" / "coverage.py").read_text(
            encoding="utf-8"
        ),
        "src/eidp/reports/gaps.py": (REPO_ROOT / "src" / "eidp" / "reports" / "gaps.py").read_text(
            encoding="utf-8"
        ),
        "src/eidp/reports/ship_readiness.py": (
            REPO_ROOT / "src" / "eidp" / "reports" / "ship_readiness.py"
        ).read_text(encoding="utf-8"),
        "src/eidp/db/audit.py": (
            "from eidp.db.models import ManualActionLog\n"
            "def log_manual_action(session):\n"
            "    action_id=str(uuid.uuid4())\n"
            "    row = ManualActionLog()\n"
            "    session.flush()\n"
        ),
        "src/eidp/db/audit_outbox.py": (
            REPO_ROOT / "src" / "eidp" / "db" / "audit_outbox.py"
        ).read_text(encoding="utf-8"),
        "src/eidp/db/sqlite_bootstrap.py": (
            REPO_ROOT / "src" / "eidp" / "db" / "sqlite_bootstrap.py"
        ).read_text(encoding="utf-8"),
        "src/eidp/scraper/pdf_discovery.py": (
            REPO_ROOT / "src" / "eidp" / "scraper" / "pdf_discovery.py"
        ).read_text(encoding="utf-8"),
        "src/eidp/scraper/url_discovery.py": (
            REPO_ROOT / "src" / "eidp" / "scraper" / "url_discovery.py"
        ).read_text(encoding="utf-8"),
        "src/eidp/scraper/discovery_gold_set.py": (
            REPO_ROOT / "src" / "eidp" / "scraper" / "discovery_gold_set.py"
        ).read_text(encoding="utf-8"),
        "src/eidp/scraper/discovery_evidence_summary.py": (
            REPO_ROOT / "src" / "eidp" / "scraper" / "discovery_evidence_summary.py"
        ).read_text(encoding="utf-8"),
        "src/eidp/pdf/extractor.py": (REPO_ROOT / "src" / "eidp" / "pdf" / "extractor.py").read_text(
            encoding="utf-8"
        ),
        "src/eidp/pipeline/ingest.py": (
            "DepartmentYearly\n"
            "SupportRecipient\n"
            "compute_pdf_parse_breakdown\n"
            "breakdown_to_json\n"
            "verdict = classify(breakdown.composite, thresholds_from_env())\n"
            'is_current_row = verdict in ("auto", "auto_flag")\n'
            "revision=next_revision\n"
            "if is_current_row:\n                dy = DepartmentYearly(\n"
            "is_current=True\n"
            'stats["yearly_review_pending"] += 1\n'
            'sr_is_current = sr_verdict in ("auto", "auto_flag")\n'
            "if sr_is_current:\n            sr = SupportRecipient(\n"
            "support_recipient_review_pending\n"
            'stats["support_recipient_review_pending"] = 1\n'
            "if yearly_review > 0 or sr_review > 0:\n"
            'doc.ingest_status = "review_pending"\n'
            "from eidp.config import settings\n"
            "target_fiscal_year: int | None = None\n"
            "fiscal_year_cap = target_fiscal_year if target_fiscal_year is not None else settings.target_fiscal_year\n"
            "doc.is_current_year = fiscal_year >= fiscal_year_cap\n"
            "target_fiscal_year=target_fiscal_year\n"
            "max_fiscal_year=fiscal_year_cap\n"
            "has_fiscal_year_text\n"
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
        "src/eidp/cli_discovery.py": (REPO_ROOT / "src" / "eidp" / "cli_discovery.py").read_text(
            encoding="utf-8"
        ),
        "src/eidp/cli_reports.py": (REPO_ROOT / "src" / "eidp" / "cli_reports.py").read_text(
            encoding="utf-8"
        ),
        "src/eidp/cli_tools.py": (REPO_ROOT / "src" / "eidp" / "cli_tools.py").read_text(
            encoding="utf-8"
        ),
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


def test_verify_core_zip_rejects_dirty_build_info(tmp_path: Path) -> None:
    entries = _core_entries()
    build_info = json.loads(entries["BUILD_INFO.json"])
    build_info["git_dirty"] = "true"
    entries["BUILD_INFO.json"] = json.dumps(build_info)
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("BUILD_INFO.json git_dirty must be false" in error for error in check.errors)


def test_verify_core_zip_rejects_unknown_build_commit(tmp_path: Path) -> None:
    entries = _core_entries()
    build_info = json.loads(entries["BUILD_INFO.json"])
    build_info["git_commit"] = "unknown"
    entries["BUILD_INFO.json"] = json.dumps(build_info)
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("BUILD_INFO.json git_commit must be a full 40-character commit hash" in error for error in check.errors)


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
    entries.pop("EIDP-stage6-evidence.bat")
    entries.pop("EIDP-stage6-recovery.bat")
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("EIDP-setup.bat" in error for error in check.errors)
    assert any("EIDP-start.bat" in error for error in check.errors)
    assert any("EIDP-diagnose.bat" in error for error in check.errors)
    assert any("EIDP-stage6-evidence.bat" in error for error in check.errors)
    assert any("EIDP-stage6-recovery.bat" in error for error in check.errors)


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


def test_verify_core_zip_validates_root_stage6_recovery_launcher_contract(tmp_path: Path) -> None:
    entries = _core_entries()
    entries["EIDP-stage6-recovery.bat"] = entries["EIDP-stage6-recovery.bat"].replace(
        'call "%~dp0scripts\\stage6_recovery_check.bat" %*',
        'call "%~dp0scripts\\missing_recovery.bat" %*',
    )
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("EIDP-stage6-recovery.bat missing required token" in error for error in check.errors)


def test_verify_core_zip_validates_root_stage6_evidence_launcher_contract(tmp_path: Path) -> None:
    entries = _core_entries()
    entries["EIDP-stage6-evidence.bat"] = entries["EIDP-stage6-evidence.bat"].replace(
        'call "%~dp0scripts\\collect_stage6_evidence.bat"',
        'call "%~dp0scripts\\missing_evidence.bat"',
    )
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("EIDP-stage6-evidence.bat missing required token" in error for error in check.errors)


def test_verify_core_zip_validates_root_stage6_verify_evidence_launcher_contract(tmp_path: Path) -> None:
    entries = _core_entries()
    entries["EIDP-stage6-verify-evidence.bat"] = entries["EIDP-stage6-verify-evidence.bat"].replace(
        'call "%~dp0scripts\\verify_stage6_evidence.bat"',
        'call "%~dp0scripts\\missing_verify_evidence.bat"',
    )
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("EIDP-stage6-verify-evidence.bat missing required token" in error for error in check.errors)


def test_verify_core_zip_validates_collect_bug_report_launcher_contract(tmp_path: Path) -> None:
    entries = _core_entries()
    entries["scripts/collect_bug_report.bat"] = entries["scripts/collect_bug_report.bat"].replace(
        'set "PYTHONUTF8=1"\n',
        "",
    )
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("scripts/collect_bug_report.bat missing required token: PYTHONUTF8=1" in error for error in check.errors)


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
    entries.pop("data/url-discovery/school_domain_overrides.csv")
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("data/url-discovery/discovered-urls-50.csv" in error for error in check.errors)
    assert any("data/url-discovery/corporation_domains.csv" in error for error in check.errors)
    assert any("data/url-discovery/school_domain_overrides.csv" in error for error in check.errors)


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
    assert check.details["discovery_gold_pattern_types"] == {"wordpress_download_manager": 1}
    assert check.details["discovery_gold_pattern_sources"] == {"wordpress_download_manager": 1}
    assert "embed" in check.details["discovery_gold_undemonstrated_pattern_sources"]
    assert "wordpress_download_manager" not in check.details["discovery_gold_undemonstrated_pattern_sources"]
    assert check.details["discovery_gold_expected_predictions"] == 5
    assert any("lack gold-set demonstrations" in warning for warning in check.warnings)


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


def test_verify_core_zip_rejects_semantically_invalid_discovery_gold_entry(tmp_path: Path) -> None:
    entries = _core_entries()
    payload = json.loads(str(entries["data/discovery-gold-set/entries/accepted.json"]))
    payload["expected_result"]["strict_target_year_success"] = False
    entries["data/discovery-gold-set/entries/accepted.json"] = json.dumps(payload)
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("accepted_target_pdf requires strict_target_year_success=true" in error for error in check.errors)


def test_verify_core_zip_rejects_missing_discovery_gold_expected_predictions(tmp_path: Path) -> None:
    entries = _core_entries()
    entries.pop("data/discovery-gold-set/expected-predictions.jsonl")
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("data/discovery-gold-set/expected-predictions.jsonl" in error for error in check.errors)


def test_verify_core_zip_rejects_mismatched_discovery_gold_expected_predictions(tmp_path: Path) -> None:
    entries = _core_entries()
    lines = str(entries["data/discovery-gold-set/expected-predictions.jsonl"]).splitlines()
    first = json.loads(lines[0])
    first["strict_target_year_success"] = False
    lines[0] = json.dumps(first, sort_keys=True)
    entries["data/discovery-gold-set/expected-predictions.jsonl"] = "\n".join(lines) + "\n"
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("prediction mismatch for accepted" in error for error in check.errors)


def test_verify_core_zip_rejects_missing_discovery_gold_pattern_prediction(tmp_path: Path) -> None:
    entries = _core_entries()
    lines = str(entries["data/discovery-gold-set/expected-predictions.jsonl"]).splitlines()
    for index, line in enumerate(lines):
        payload = json.loads(line)
        if payload.get("entry_id") == "publication-lag":
            payload.pop("pattern_type", None)
            lines[index] = json.dumps(payload, sort_keys=True)
            break
    entries["data/discovery-gold-set/expected-predictions.jsonl"] = "\n".join(lines) + "\n"
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any(
        "prediction mismatch for publication-lag: pattern_type=None, expected 'wordpress_download_manager'" in error
        for error in check.errors
    )


def test_verify_core_zip_requires_discovery_gold_eval_regression_gate(tmp_path: Path) -> None:
    entries = _core_entries()
    entries["src/eidp/cli_discovery.py"] = "def register_discovery_commands(app): pass\n"
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("src/eidp/cli_discovery.py missing required token" in error for error in check.errors)
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


def test_verify_core_zip_requires_target_fiscal_year_config_bound(tmp_path: Path) -> None:
    entries = _core_entries()
    entries["src/eidp/config.py"] = "class Settings: target_fiscal_year = 2026\n"
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("src/eidp/config.py missing required token" in error for error in check.errors)
    assert any("_validate_target_fiscal_year" in error for error in check.errors)
    assert any("SUPPORTED_TARGET_FISCAL_YEAR_RANGE_LABEL" in error for error in check.errors)
    assert any("pdf_discovery_experimental_extractors: bool = False" in error for error in check.errors)


def test_verify_core_zip_requires_configurable_fiscal_year_text_helper(tmp_path: Path) -> None:
    entries = _core_entries()
    entries["src/eidp/fiscal_year.py"] = "def fiscal_year_search_tokens(year): return (str(year),)\n"
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("src/eidp/fiscal_year.py missing required token" in error for error in check.errors)
    assert any("has_fiscal_year_text" in error for error in check.errors)
    assert any("era.initial" in error for error in check.errors)
    assert any("era.romanized" in error for error in check.errors)


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
    assert any(
        "def excel_min_extraction_confidence()" in error
        for error in check.errors
    )


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


def test_verify_core_zip_requires_report_defaults_to_configured_target_year(tmp_path: Path) -> None:
    entries = _core_entries()
    entries["src/eidp/reports/coverage.py"] = (
        "def compute_coverage(session, school_type='専門学校', fiscal_year=None):\n"
        "    fy = fiscal_year if fiscal_year is not None else current_fiscal_year()\n"
    )
    entries["src/eidp/reports/gaps.py"] = (
        "def _gaps_pdf(session, school_type, fiscal_year):\n"
        "    fy = fiscal_year if fiscal_year is not None else current_fiscal_year()\n"
    )
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any(
        "src/eidp/reports/coverage.py" in error and "settings.target_fiscal_year" in error
        for error in check.errors
    )
    assert any(
        "src/eidp/reports/gaps.py" in error and "settings.target_fiscal_year" in error
        for error in check.errors
    )


def test_verify_core_zip_requires_ship_readiness_strict_target_pdf_criterion(tmp_path: Path) -> None:
    entries = _core_entries()
    entries["src/eidp/reports/ship_readiness.py"] = entries["src/eidp/reports/ship_readiness.py"].replace(
        'name="strict_target_pdf"',
        'name="excel_ready_only"',
    )
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any(
        'src/eidp/reports/ship_readiness.py missing required token: name="strict_target_pdf"' in error
        for error in check.errors
    )


def test_verify_core_zip_requires_publication_lag_release_exception_contract(tmp_path: Path) -> None:
    entries = _core_entries()
    entries["scripts/verify_stage6_return.py"] = (
        entries["scripts/verify_stage6_return.py"]
        .replace("release_exception_reason", "release_override_reason")
        .replace("mature_year_proof_json", "historical_year_proof_json")
        .replace("release exception requires --mature-year-proof-json", "release exception requires proof")
        .replace("min_target_pdf_auto_denominator_count", "min_target_pdf_auto_sample_count")
        .replace("target_pdf_auto_denominator_count", "target_pdf_auto_sample_count")
        .replace("target_pdf_auto_denominator_scope", "target_pdf_auto_sample_scope")
        .replace("SHIP_GATE_EXCEPTION_REASONS", "SHIP_GATE_RELEASE_EXCEPTIONS")
        .replace("publication_lag", "publication_delay")
    )
    entries["scripts/ship_gate_contract.py"] = (
        entries["scripts/ship_gate_contract.py"]
        .replace("MATURE_YEAR_SHIP_GATE_METRIC_BASIS", "MATURE_YEAR_METRIC_BASIS")
        .replace("MATURE_YEAR_PROOF_MIN_DENOMINATOR", "MATURE_YEAR_PROOF_MIN_SAMPLE")
        .replace("WEEKLY_SHIP_GATE_DENOMINATOR_SCOPE", "WEEKLY_SHIP_GATE_SAMPLE_SCOPE")
        .replace("target_missing_schools_before_run", "target_missing_small_sample")
        .replace("SHIP_GATE_EXCEPTION_REASONS", "SHIP_GATE_RELEASE_EXCEPTIONS")
        .replace("publication_lag", "publication_delay")
    )
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any(
        "scripts/verify_stage6_return.py missing required token: release_exception_reason" in error
        for error in check.errors
    )
    assert any(
        "scripts/verify_stage6_return.py missing required token: mature_year_proof_json" in error
        for error in check.errors
    )
    assert any(
        "scripts/verify_stage6_return.py missing required token: release exception requires --mature-year-proof-json"
        in error
        for error in check.errors
    )
    assert any(
        "scripts/verify_stage6_return.py missing required token: min_target_pdf_auto_denominator_count" in error
        for error in check.errors
    )
    assert any(
        "scripts/verify_stage6_return.py missing required token: target_pdf_auto_denominator_scope" in error
        for error in check.errors
    )
    assert any(
        "scripts/ship_gate_contract.py missing required token: MATURE_YEAR_SHIP_GATE_METRIC_BASIS" in error
        for error in check.errors
    )
    assert any(
        "scripts/ship_gate_contract.py missing required token: MATURE_YEAR_PROOF_MIN_DENOMINATOR" in error
        for error in check.errors
    )
    assert any(
        "scripts/ship_gate_contract.py missing required token: WEEKLY_SHIP_GATE_DENOMINATOR_SCOPE" in error
        for error in check.errors
    )
    assert any(
        "scripts/ship_gate_contract.py missing required token: target_missing_schools_before_run" in error
        for error in check.errors
    )
    assert any(
        "scripts/ship_gate_contract.py missing required token: SHIP_GATE_EXCEPTION_REASONS" in error
        for error in check.errors
    )
    assert any(
        "scripts/ship_gate_contract.py missing required token: publication_lag" in error
        for error in check.errors
    )


def test_verify_core_zip_requires_current_target_fy_coverage_contract(tmp_path: Path) -> None:
    entries = _core_entries()
    entries["src/eidp/reports/coverage.py"] = (
        "from eidp.config import settings\n"
        "def compute_coverage(session, school_type='専門学校', fiscal_year=None): pass\n"
    )
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("schools_with_target_pdf_current_fy" in error for error in check.errors)
    assert any("target_pdf_current_fy_rate" in error for error in check.errors)
    assert any("d_fy == fy" in error for error in check.errors)
    assert any("Document.fiscal_year == fiscal_year" in error for error in check.errors)
    assert any("Document.fiscal_year < fiscal_year" in error for error in check.errors)
    assert any("stale_fallback_schools" in error for error in check.errors)
    assert any("target_pdf = int(coverage.schools_with_target_pdf_current_fy)" in error for error in check.errors)


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
    assert any("OUTBOX_ARCHIVE_GLOB" in error for error in check.errors)
    assert any("os.fsync" in error for error in check.errors)
    assert any("_candidate_outbox_paths" in error for error in check.errors)


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


def test_verify_core_zip_requires_review_coverage_gate_labels(tmp_path: Path) -> None:
    entries = _core_entries()
    entries["src/eidp/review/_pages/school_year_tasks.py"] = entries[
        "src/eidp/review/_pages/school_year_tasks.py"
    ].replace("レビュー判定", "出荷判定").replace("OCR add-on 未導入", "OCR 設定未完了")
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any(
        "src/eidp/review/_pages/school_year_tasks.py missing required token: レビュー判定" in error
        for error in check.errors
    )
    assert any(
        "src/eidp/review/_pages/school_year_tasks.py missing required token: OCR add-on 未導入" in error
        for error in check.errors
    )


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
    assert any("MIN_SUPPORTED_FISCAL_YEAR" in error for error in check.errors)
    assert any("MAX_SUPPORTED_FISCAL_YEAR" in error for error in check.errors)
    assert any("target_year - 8" in error for error in check.errors)
    assert any("candidate.detected_fiscal_year >= target_year" in error for error in check.errors)
    assert any("has_fiscal_year_text" in error for error in check.errors)
    assert any("_candidate_download_year_rank" in error for error in check.errors)
    assert any("PDF_LINK_ATTRIBUTE_NAMES" in error for error in check.errors)
    assert any("PDF_DATA_ATTRIBUTE_TAG_PATTERN" in error for error in check.errors)
    assert any("PDF_SCRIPT_URL_PATTERN" in error for error in check.errors)
    assert any("PDF_META_REFRESH_PATTERN" in error for error in check.errors)
    assert any("PDF_OPTION_VALUE_PATTERN" in error for error in check.errors)
    assert any("PDF_FORM_ACTION_PATTERN" in error for error in check.errors)
    assert any("PDF_INPUT_TAG_PATTERN" in error for error in check.errors)
    assert any("PDF_EMBED_TAG_NAMES" in error for error in check.errors)
    assert any("PDF_EMBED_ATTRIBUTE_NAMES" in error for error in check.errors)
    assert any("_pdf_delivery_pattern" in error for error in check.errors)
    assert any('source="meta_refresh"' in error for error in check.errors)
    assert any('source="select_option"' in error for error in check.errors)
    assert any('source="form_action"' in error for error in check.errors)
    assert any('source="data_attribute"' in error for error in check.errors)
    assert any('source="onclick"' in error for error in check.errors)
    assert any('source="input_control"' in error for error in check.errors)
    assert any('endswith("_direct")' in error for error in check.errors)
    assert any("_pdf_url_from_meta_refresh_content" in error for error in check.errors)
    assert any('"http-equiv"' in error for error in check.errors)
    assert any("_pdf_element_context_text" in error for error in check.errors)
    assert any('pattern_type="embed"' in error for error in check.errors)
    assert any('"value"' in error for error in check.errors)
    assert any('"action"' in error for error in check.errors)
    assert any("_pdf_urls_from_script_attribute" in error for error in check.errors)
    assert any('"onclick"' in error for error in check.errors)
    assert any("button|span|div" in error for error in check.errors)
    assert any('"data-href"' in error for error in check.errors)
    assert any('"data-url"' in error for error in check.errors)
    assert any('"data-file"' in error for error in check.errors)
    assert any('"data-pdf"' in error for error in check.errors)
    assert any('"data-src"' in error for error in check.errors)
    assert any("_candidate_dedupe_preference" in error for error in check.errors)
    assert any("_candidate_dedupe_year_preference" in error for error in check.errors)
    assert any("candidate_year == target_year" in error for error in check.errors)
    assert any("target_fiscal_year=target_year" in error for error in check.errors)
    assert any("(?:[?#][^\"\\']*)?" in error for error in check.errors)
    assert any("_without_url_fragment" in error for error in check.errors)
    assert any("_append_or_upgrade_candidate" in error for error in check.errors)
    assert any("candidate_budget_dropped" in error for error in check.errors)
    assert any("max_general_candidate_scan=" in error for error in check.errors)
    assert any("SchoolSite.school_id.asc()" in error for error in check.errors)
    assert any("SchoolSite.id.asc()" in error for error in check.errors)


def test_verify_core_zip_requires_pdf_delivery_pattern_provenance(tmp_path: Path) -> None:
    entries = _core_entries()
    entries["src/eidp/scraper/pdf_discovery.py"] = str(entries["src/eidp/scraper/pdf_discovery.py"]).replace(
        'source="onclick"',
        'source="script"',
    )
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any(
        'src/eidp/scraper/pdf_discovery.py missing required token: source="onclick"' in error
        for error in check.errors
    )


def test_verify_core_zip_rejects_english_renewal_tokens_in_pdf_discovery(tmp_path: Path) -> None:
    entries = _core_entries()
    entries["src/eidp/scraper/pdf_discovery.py"] = (
        str(entries["src/eidp/scraper/pdf_discovery.py"])
        + "\nrenewalconfirmationapplication\n"
        + "renewal-confirmation-application\n"
        + "renewal confirmation application\n"
    )
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("contains forbidden token: renewalconfirmationapplication" in error for error in check.errors)
    assert any("contains forbidden token: renewal-confirmation-application" in error for error in check.errors)
    assert any("contains forbidden token: renewal confirmation application" in error for error in check.errors)


def test_verify_core_zip_rejects_current_fiscal_year_literals_in_pdf_discovery(tmp_path: Path) -> None:
    entries = _core_entries()
    entries["src/eidp/scraper/pdf_discovery.py"] = (
        str(entries["src/eidp/scraper/pdf_discovery.py"])
        + "\n2026\n"
        + "令和8\n"
        + "令和８\n"
        + "R8\n"
        + "r8\n"
    )
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("contains forbidden token: 2026" in error for error in check.errors)
    assert any("contains forbidden token: 令和8" in error for error in check.errors)
    assert any("contains forbidden token: 令和８" in error for error in check.errors)
    assert any("contains forbidden token: R8" in error for error in check.errors)
    assert any("contains forbidden token: r8" in error for error in check.errors)


@pytest.mark.parametrize(
    "member",
    [
        "scripts/bootstrap_pdf_pipeline.py",
        "scripts/run_weekly_target_year_discovery.py",
        "scripts/validate_windows_install.py",
        "src/eidp/pdf/extractor.py",
        "src/eidp/reports/coverage.py",
        "src/eidp/reports/gaps.py",
        "src/eidp/reports/ship_readiness.py",
    ],
)
def test_verify_core_zip_rejects_current_fiscal_year_literals_in_runtime_paths(
    tmp_path: Path,
    member: str,
) -> None:
    entries = _core_entries()
    entries[member] = str(entries[member]) + "\n2026\n"
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any(f"{member} contains forbidden token: 2026" in error for error in check.errors)


def test_verify_core_zip_requires_url_normalization_tracking_dedupe_contract(tmp_path: Path) -> None:
    entries = _core_entries()
    entries["src/eidp/scraper/url_normalization.py"] = "def normalize_candidate_url(url): return url\n"
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("src/eidp/scraper/url_normalization.py missing required token" in error for error in check.errors)
    assert any("TRACKING_QUERY_PARAMS" in error for error in check.errors)
    assert any("utm_source" in error for error in check.errors)
    assert any("gclid" in error for error in check.errors)
    assert any("wpdmdl" in error for error in check.errors)


def test_verify_core_zip_requires_stable_url_discovery_order(tmp_path: Path) -> None:
    entries = _core_entries()
    entries["src/eidp/scraper/url_discovery.py"] = "def search_and_discover(): pass\n"
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("src/eidp/scraper/url_discovery.py missing required token" in error for error in check.errors)
    assert any("School.prefecture.asc()" in error for error in check.errors)
    assert any("School.id.asc()" in error for error in check.errors)
    assert any("SchoolSite.school_id.asc()" in error for error in check.errors)
    assert any("SchoolSite.id.asc()" in error for error in check.errors)


def test_verify_core_zip_requires_rolling_year_discovery_gold_evidence_contract(tmp_path: Path) -> None:
    entries = _core_entries()
    entries["src/eidp/scraper/discovery_gold_set.py"] = (
        "def load_discovery_gold_predictions_from_pdf_evidence(evidence_path, entries):\n"
        "    entries_by_school_id = {entry.school_id: entry for entry in entries}\n"
        "    return []\n"
    )
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("src/eidp/scraper/discovery_gold_set.py missing required token" in error for error in check.errors)
    assert any("_target_fiscal_year_from_evidence_payload" in error for error in check.errors)
    assert any("json.JSONDecodeError" in error for error in check.errors)
    assert any("line_number" in error for error in check.errors)


def test_verify_core_zip_requires_deterministic_discovery_evidence_summary(tmp_path: Path) -> None:
    entries = _core_entries()
    entries["src/eidp/scraper/discovery_evidence_summary.py"] = "def summarize_pdf_discovery_evidence(): pass\n"
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any(
        "src/eidp/scraper/discovery_evidence_summary.py missing required token" in error
        for error in check.errors
    )
    assert any("_sorted_counter_items" in error for error in check.errors)
    assert any("key=lambda item: (-item[1], item[0])" in error for error in check.errors)
    assert any("json.JSONDecodeError" in error for error in check.errors)
    assert any("line_number" in error for error in check.errors)


def test_verify_core_zip_requires_discovery_gold_replay_semantics_contract(tmp_path: Path) -> None:
    entries = _core_entries()
    entries["src/eidp/scraper/discovery_gold_set.py"] = (
        "entries_by_key = {}\n"
        "(entry.school_id, entry.target_fiscal_year)\n"
        "_target_fiscal_year_from_evidence_payload\n"
        "school_id_counts\n"
    )
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("src/eidp/scraper/discovery_gold_set.py missing required token" in error for error in check.errors)
    assert any("detected_fiscal_year" in error for error in check.errors)
    assert any("DISCOVERY_GOLD_NO_TARGET_EVIDENCE_REASONS" in error for error in check.errors)
    assert any('"needs_operator_review": 3' in error for error in check.errors)
    assert any('"site_fetch_error": 2' in error for error in check.errors)
    assert any("_is_better_tie_break_prediction" in error for error in check.errors)
    assert any("candidate.fiscal_year" in error for error in check.errors)
    assert any("pattern_type_mismatch" in error for error in check.errors)
    assert any("pattern_type=str(payload.get(\"pattern_type\")" in error for error in check.errors)


def test_verify_core_zip_requires_rolling_pdf_fiscal_year_extractor_contract(tmp_path: Path) -> None:
    entries = _core_entries()
    entries["src/eidp/pdf/extractor.py"] = (
        "def _extract_fiscal_year(full_text):\n"
        "    filing_dates = re.findall(r\"(202[0-9])[./]\\d{1,2}[./]\\d{1,2}\", full_text)\n"
        "    all_years = re.findall(r\"(202[0-9])[\\.\\s年/]\", full_text)\n"
        "    return ''\n"
    )
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("src/eidp/pdf/extractor.py missing required token" in error for error in check.errors)
    assert any("20\\d{2}" in error for error in check.errors)
    assert any("MIN_SUPPORTED_FISCAL_YEAR" in error for error in check.errors)
    assert any("MAX_SUPPORTED_FISCAL_YEAR" in error for error in check.errors)
    assert any("fiscal_year_from_japanese_era_text" in error for error in check.errors)
    assert any("settings.target_fiscal_year" in error for error in check.errors)
    assert any("format_fiscal_year_as_japanese_era" in error for error in check.errors)


def test_verify_core_zip_requires_append_only_confidence_ingest(tmp_path: Path) -> None:
    entries = _core_entries()
    entries["src/eidp/pipeline/ingest.py"] = "def ingest_document(): pass\n"
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("src/eidp/pipeline/ingest.py missing required token" in error for error in check.errors)
    assert any("compute_pdf_parse_breakdown" in error for error in check.errors)
    assert any('is_current_row = verdict in ("auto", "auto_flag")' in error for error in check.errors)
    assert any('stats["yearly_review_pending"] += 1' in error for error in check.errors)
    assert any("if yearly_review > 0 or sr_review > 0:" in error for error in check.errors)
    assert any("target_fiscal_year: int | None = None" in error for error in check.errors)
    assert any("fiscal_year_cap = target_fiscal_year" in error for error in check.errors)
    assert any("doc.is_current_year = fiscal_year >= fiscal_year_cap" in error for error in check.errors)
    assert any("target_fiscal_year=target_fiscal_year" in error for error in check.errors)
    assert any("settings.target_fiscal_year" in error for error in check.errors)
    assert any("has_fiscal_year_text" in error for error in check.errors)


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
    assert any("--require-ocr-runtime" in error for error in check.errors)
    assert any("support_recipient" in error for error in check.errors)
    assert any("sqlite_integrity_check" in error for error in check.errors)
    assert any("uq_document_file_hash" in error for error in check.errors)
    assert any("sqlite_target_fy_yield_pct" in error for error in check.errors)
    assert any("weekly summary after.coverage" in error for error in check.errors)


def test_verify_core_zip_requires_weekly_artifact_pruning_contract(tmp_path: Path) -> None:
    entries = _core_entries()
    entries["scripts/run_weekly_target_year_discovery.py"] = (
        "acquire_lock\n"
        "last_run.json\n"
        "write_last_run\n"
        "prune_run_logs\n"
        "run_pdf_discovery\n"
        "run_ingestion\n"
        "write_text_atomic\n"
    )
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("scripts/run_weekly_target_year_discovery.py missing required token" in error for error in check.errors)
    assert any("write_progress" in error for error in check.errors)
    assert any("--progress-file" in error for error in check.errors)
    assert any("prune_run_artifacts" in error for error in check.errors)
    assert any("RUN_ARTIFACT_PATTERNS" in error for error in check.errors)


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


def test_verify_core_zip_requires_settings_page_target_year_bounds(tmp_path: Path) -> None:
    entries = _core_entries()
    entries["src/eidp/review/_pages/settings_page.py"] = (
        "def render(session, *, lock_path):\n"
        "    st.number_input('対象年度（西暦）', min_value=2000, max_value=2100)\n"
    )
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("MIN_SUPPORTED_TARGET_FISCAL_YEAR" in error for error in check.errors)
    assert any("MAX_SUPPORTED_TARGET_FISCAL_YEAR" in error for error in check.errors)


def test_verify_core_zip_requires_cli_report_database_not_ready_gate(tmp_path: Path) -> None:
    entries = _core_entries()
    entries["src/eidp/cli_reports.py"] = '@report_app.command("ship-readiness")\n--fail-on-missing-goal\n'
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("src/eidp/cli_reports.py missing required token" in error for error in check.errors)
    assert any("database_not_ready" in error for error in check.errors)


def test_verify_core_zip_requires_import_excel_invalid_year_warning(tmp_path: Path) -> None:
    entries = _core_entries()
    entries["src/eidp/cli.py"] = (
        '_require_app_lock("cli_import_excel")\n'
        '_require_app_lock("cli_db_bootstrap")\n'
        '_require_app_lock("cli_rebuild_school_year_tasks")\n'
        '_require_app_lock("cli_weekly_update")\n'
    )
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("_echo_import_excel_results" in error for error in check.errors)
    assert any("invalid_year" in error for error in check.errors)
    assert any("想定外の年度" in error for error in check.errors)


def test_verify_core_zip_requires_cli_write_lock_contracts(tmp_path: Path) -> None:
    entries = _core_entries()
    entries["src/eidp/cli.py"] = str(entries["src/eidp/cli.py"]).replace(
        '_require_app_lock("cli_audit_flush")',
        '# missing audit flush lock',
    )
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any('_require_app_lock("cli_audit_flush")' in error for error in check.errors)


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
        "prefecture_aggregator,seed_csv,corporation_pattern,school_domain_override,scrapling_stealth",
        "prefecture_aggregator",
    )
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any(
        "prefecture_aggregator,seed_csv,corporation_pattern,school_domain_override,scrapling_stealth" in error
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


@pytest.mark.parametrize(
    "runtime_member",
    [
        "data/.lock",
        "data/eidp.sqlite3",
        "data/eidp.sqlite3-wal",
        "data/eidp.sqlite3-shm",
        "data/audit/manual-actions.jsonl",
        "data/output/last_run.json",
        "data/pdfs/1234/abcd.pdf",
        "data/prefecture-aggregators/artifacts/tokyo.pdf",
    ],
)
def test_verify_core_zip_rejects_mutable_runtime_data(tmp_path: Path, runtime_member: str) -> None:
    entries = _core_entries()
    entries[runtime_member] = "runtime state must not ship"
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("mutable runtime data" in error for error in check.errors)


@pytest.mark.parametrize(
    "secret_member",
    [
        ".env",
        ".env.local",
        "config/.env.production",
        "secrets/id_rsa",
        "secrets/id_ed25519",
        "secrets/operator_private_key.pem",
    ],
)
def test_verify_core_zip_rejects_local_secret_files(tmp_path: Path, secret_member: str) -> None:
    entries = _core_entries()
    entries[secret_member] = "local secret material must not ship"
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("local secret/key files" in error for error in check.errors)


def test_verify_core_zip_allows_env_example_template(tmp_path: Path) -> None:
    entries = _core_entries()
    entries["docs/.env.example"] = "FIRECRAWL_API_KEY=your-api-key-here\n"
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert check.ok


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


def test_verify_core_zip_rejects_launcher_without_localhost_bind(tmp_path: Path) -> None:
    entries = _core_entries()
    entries["scripts/launch.bat"] = entries["scripts/launch.bat"].replace(
        "--server.address 127.0.0.1",
        "REM stale launcher missing localhost bind",
    )
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("--server.address 127.0.0.1" in error for error in check.errors)


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


def test_verify_core_zip_rejects_diagnose_without_strict_ship_gate_validation(tmp_path: Path) -> None:
    entries = _core_entries()
    entries["scripts/diagnose.bat"] = (
        entries["scripts/diagnose.bat"]
        .replace(" --require-ship-gate", "")
        .replace("validate_after_bootstrap_ship_gate_rc", "validate_after_bootstrap_rc")
        .replace("validate_after_weekly_ship_gate_rc", "validate_after_weekly_rc")
    )
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("--require-ship-gate" in error for error in check.errors)
    assert any("validate_after_bootstrap_ship_gate_rc" in error for error in check.errors)
    assert any("validate_after_weekly_ship_gate_rc" in error for error in check.errors)


def test_verify_core_zip_rejects_diagnose_without_retroactive_fiscal_year_snapshot(tmp_path: Path) -> None:
    entries = _core_entries()
    entries["scripts/diagnose.bat"] = entries["scripts/diagnose.bat"].replace(
        "retroactive fiscal-year ship readiness",
        "stale previous-year diagnostic",
    )
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("retroactive fiscal-year ship readiness" in error for error in check.errors)


def test_verify_core_zip_rejects_diagnose_without_stage6_recovery_snapshot(tmp_path: Path) -> None:
    entries = _core_entries()
    entries["scripts/diagnose.bat"] = entries["scripts/diagnose.bat"].replace(
        "stage6 recovery check",
        "stale recovery diagnostic",
    )
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("stage6 recovery check" in error for error in check.errors)


def test_verify_core_zip_rejects_diagnose_with_parse_time_errorlevel_capture(tmp_path: Path) -> None:
    entries = _core_entries()
    entries["scripts/diagnose.bat"] = (
        entries["scripts/diagnose.bat"]
        .replace('set "VALIDATE_BOOTSTRAP_RC=!ERRORLEVEL!"', 'set "VALIDATE_BOOTSTRAP_RC=%ERRORLEVEL%"')
        .replace(
            'set "VALIDATE_BOOTSTRAP_SHIP_GATE_RC=!ERRORLEVEL!"',
            'set "VALIDATE_BOOTSTRAP_SHIP_GATE_RC=%ERRORLEVEL%"',
        )
        .replace('set "VALIDATE_WEEKLY_RC=!ERRORLEVEL!"', 'set "VALIDATE_WEEKLY_RC=%ERRORLEVEL%"')
        .replace(
            'set "VALIDATE_WEEKLY_SHIP_GATE_RC=!ERRORLEVEL!"',
            'set "VALIDATE_WEEKLY_SHIP_GATE_RC=%ERRORLEVEL%"',
        )
    )
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("VALIDATE_BOOTSTRAP_RC=!ERRORLEVEL!" in error for error in check.errors)
    assert any("VALIDATE_BOOTSTRAP_SHIP_GATE_RC=!ERRORLEVEL!" in error for error in check.errors)
    assert any("VALIDATE_WEEKLY_RC=!ERRORLEVEL!" in error for error in check.errors)
    assert any("VALIDATE_WEEKLY_SHIP_GATE_RC=!ERRORLEVEL!" in error for error in check.errors)


def test_verify_core_zip_rejects_bootstrap_bat_without_log_capture(tmp_path: Path) -> None:
    entries = _core_entries()
    entries["scripts/bootstrap_pdfs.bat"] = (
        entries["scripts/bootstrap_pdfs.bat"]
        .replace("bootstrap-pdfs-%RUN_ID%.log", "")
        .replace('> "%LOG_PATH%" 2>&1', "")
    )
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("scripts/bootstrap_pdfs.bat missing required token" in error for error in check.errors)
    assert any("bootstrap-pdfs-%RUN_ID%.log" in error for error in check.errors)


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
    assert any("アンチウイルスにより隔離" in error for error in check.errors)
    assert any("weekly_run.bat" in error for error in check.errors)
    assert any("data\\.lock" in error for error in check.errors)


def test_verify_core_zip_rejects_local_user_path_in_packaged_operator_docs(tmp_path: Path) -> None:
    entries = _core_entries()
    entries["docs/runbooks/eidp-windows.md"] += "\nC:\\Users\\private_user\\EIDP-v999\n"
    entries["docs/runbooks/eidp-operator-e2e-template.md"] += "\n/Users/private_user/workspace/EIDP\n"
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    local_user_errors = [error for error in check.errors if "local-user path token" in error]
    assert len(local_user_errors) == 2
    assert all("docs/runbooks/" in error for error in local_user_errors)


def test_verify_core_zip_rejects_eidp_operator_example_in_packaged_operator_docs(tmp_path: Path) -> None:
    entries = _core_entries()
    entries["docs/runbooks/eidp-windows.md"] += "\nC:\\Users\\eidp_operator\\EIDP-vXXX-abcdef0\n"
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("docs/runbooks/eidp-windows.md contains local-user path token" in error for error in check.errors)


def test_verify_core_zip_rejects_packaged_historical_runbooks(tmp_path: Path) -> None:
    entries = _core_entries()
    entries["docs/runbooks/eidp-v460-real-cycle-card.md"] = r"%USERPROFILE%\EIDP-v460-01e4427"
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("historical handoff runbooks" in error for error in check.errors)
    assert any("eidp-v460-real-cycle-card.md" in error for error in check.errors)


def test_verify_core_zip_requires_retroactive_fy_e2e_template_fields(tmp_path: Path) -> None:
    entries = _core_entries()
    entries["docs/runbooks/eidp-operator-e2e-template.md"] = entries[
        "docs/runbooks/eidp-operator-e2e-template.md"
    ].replace("retroactive_ship_readiness_rc", "previous_year_readiness_rc")
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("retroactive_ship_readiness_rc" in error for error in check.errors)


def test_verify_core_zip_requires_stage6_recovery_e2e_template_fields(tmp_path: Path) -> None:
    entries = _core_entries()
    entries["docs/runbooks/eidp-operator-e2e-template.md"] = entries[
        "docs/runbooks/eidp-operator-e2e-template.md"
    ].replace("stage6_recovery_rc", "stage6_status_rc")
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("stage6_recovery_rc" in error for error in check.errors)


def test_verify_core_zip_requires_operator_e2e_preflight_fields(tmp_path: Path) -> None:
    entries = _core_entries()
    entries["docs/runbooks/eidp-operator-e2e-template.md"] = entries[
        "docs/runbooks/eidp-operator-e2e-template.md"
    ].replace("Get-Volume C", "Get-PSDrive C")
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("Get-Volume C" in error for error in check.errors)


def test_verify_core_zip_requires_default_stage6_tunnel_guidance(tmp_path: Path) -> None:
    entries = _core_entries()
    entries["docs/runbooks/eidp-windows.md"] = entries["docs/runbooks/eidp-windows.md"].replace(
        "127.0.0.1:18501:127.0.0.1:8501",
        "127.0.0.1:18502:127.0.0.1:8502",
    )
    entries["docs/runbooks/eidp-operator-e2e-template.md"] = entries[
        "docs/runbooks/eidp-operator-e2e-template.md"
    ].replace("127.0.0.1:18501/_stcore/health", "127.0.0.1:18502/_stcore/health")
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("127.0.0.1:18501:127.0.0.1:8501" in error for error in check.errors)
    assert any("127.0.0.1:18501/_stcore/health" in error for error in check.errors)


def test_verify_core_zip_rejects_hardcoded_current_e2e_package_fields(tmp_path: Path) -> None:
    entries = _core_entries()
    member = "docs/runbooks/eidp-operator-e2e-template.md"
    entries[member] = (
        str(entries[member])
        .replace("dist/eidp-windows-vXXX.zip", "dist/eidp-windows-v999.zip")
        .replace(
            "<copy SHA256 from .sha256 sidecar or current-release-status>",
            "b" * 64,
        )
    )
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("hard-coded Windows ZIP version" in error for error in check.errors)
    assert any("hard-coded SHA256" in error for error in check.errors)


def test_verify_core_zip_allows_historical_e2e_package_evidence(tmp_path: Path) -> None:
    entries = _core_entries()
    member = "docs/runbooks/eidp-operator-e2e-template.md"
    entries[member] = (
        str(entries[member])
        + "\n## 4. Historical evidence\n"
        + "| core ZIP | `dist/eidp-windows-v408.zip` |\n"
        + "| core ZIP sha256 | `61fe233e41c08b8684560778b25c36f12ad0848135e8930ef07d8fa265fbbbe2` |\n"
    )
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert check.ok


def test_verify_ocr_addon_accepts_manifest(tmp_path: Path) -> None:
    tesseract = b"PE"
    tessdata = b"jpn"
    tsv_config = b"tessedit_create_tsv 1\n"
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
            {
                "path": "ocr-addon/tessdata/configs/tsv",
                "size": len(tsv_config),
                "sha256": hashlib.sha256(tsv_config).hexdigest(),
            },
        ],
    }
    zip_path = _write_zip(
        tmp_path / "eidp-ocr-addon-windows.zip",
        {
            "ocr-addon/tesseract/tesseract.exe": tesseract,
            "ocr-addon/tessdata/jpn.traineddata": tessdata,
            "ocr-addon/tessdata/configs/tsv": tsv_config,
            "ocr-addon/MANIFEST.json": json.dumps(manifest),
        },
    )

    check = module.verify_ocr_addon_zip(zip_path)

    assert check.ok, check.errors
    assert check.details["manifest_files"] == 3


def test_verify_ocr_addon_requires_manifest_paths(tmp_path: Path) -> None:
    zip_path = _write_zip(
        tmp_path / "eidp-ocr-addon-windows.zip",
        {
            "ocr-addon/tesseract/tesseract.exe": b"PE",
            "ocr-addon/tessdata/jpn.traineddata": b"jpn",
            "ocr-addon/tessdata/configs/tsv": b"tsv",
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
            {
                "path": "ocr-addon/tessdata/configs/tsv",
                "size": 3,
                "sha256": hashlib.sha256(b"tsv").hexdigest(),
            },
        ],
    }
    zip_path = _write_zip(
        tmp_path / "eidp-ocr-addon-windows.zip",
        {
            "ocr-addon/tesseract/tesseract.exe": b"PE",
            "ocr-addon/tessdata/jpn.traineddata": b"jpn",
            "ocr-addon/tessdata/configs/tsv": b"tsv",
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
            {
                "path": "ocr-addon/tessdata/configs/tsv",
                "size": 3,
                "sha256": hashlib.sha256(b"tsv").hexdigest(),
            },
        ],
    }
    zip_path = _write_zip(
        tmp_path / "eidp-ocr-addon-windows.zip",
        {
            "ocr-addon/tesseract/tesseract.exe": b"PE",
            "ocr-addon/tesseract/extra.dll": b"dll",
            "ocr-addon/tessdata/jpn.traineddata": b"jpn",
            "ocr-addon/tessdata/configs/tsv": b"tsv",
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
            {
                "path": "ocr-addon/tessdata/configs/tsv",
                "size": 3,
                "sha256": hashlib.sha256(b"tsv").hexdigest(),
            },
        ],
    }
    zip_path = _write_zip(
        tmp_path / "eidp-ocr-addon-windows.zip",
        {
            "ocr-addon/tesseract/tesseract.exe": b"PE",
            "ocr-addon/tessdata/jpn.traineddata": b"jpn",
            "ocr-addon/tessdata/configs/tsv": b"tsv",
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


def test_cli_can_require_demonstrated_discovery_patterns(tmp_path: Path, capsys) -> None:  # noqa: ANN001
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", _core_entries())

    rc = module.main([str(zip_path), "--require-demonstrated-discovery-patterns"])

    assert rc == 1
    output = capsys.readouterr().out
    assert "undemonstrated discovery extractor sources" in output
    assert "embed" in output
    assert "warning: tracked PDF discovery extractor sources lack gold-set demonstrations" in output
