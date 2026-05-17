from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from eidp.db.locking import LockBusyError, acquire_lock
from eidp.db.models import Base, Department, DepartmentYearly, Document, School, SchoolSite

script = Path(__file__).resolve().parents[2] / "scripts" / "run_weekly_target_year_discovery.py"
spec = importlib.util.spec_from_file_location("run_weekly_target_year_discovery", script)
assert spec is not None
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules["run_weekly_target_year_discovery"] = module
spec.loader.exec_module(module)

select_stale_school_ids = module.select_stale_school_ids
select_target_missing_school_ids = module.select_target_missing_school_ids
count_no_crawlable_url_schools = module.count_no_crawlable_url_schools
snapshot_reports = module._snapshot_reports
resolve_weekly_paths = module.resolve_weekly_paths
write_last_run = module.write_last_run
prune_run_logs = module.prune_run_logs
prune_run_artifacts = module.prune_run_artifacts
run_weekly = module.run_weekly


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def _school(session: Session, school_id: int, school_type: str = "専門学校") -> None:
    session.add(
        School(
            id=school_id,
            prefecture="東京",
            corporation_name=f"C{school_id}",
            school_name=f"S{school_id}",
            school_type=school_type,
            status="active",
        )
    )


def _site(session: Session, school_id: int, method: str, http_status: int | None = 200) -> None:
    session.add(
        SchoolSite(
            school_id=school_id,
            url=f"https://example{school_id}.ac.jp/disclosure/",
            discovery_method=method,
            http_status=http_status,
        )
    )


def _doc(
    session: Session,
    doc_id: int,
    school_id: int,
    fy: int,
    *,
    pdf_type: str = "target",
    ingest_status: str = "ingested",
) -> None:
    session.add(
        Document(
            id=doc_id,
            school_id=school_id,
            source_url=f"https://example{school_id}.ac.jp/{doc_id}.pdf",
            fiscal_year=fy,
            pdf_type=pdf_type,
            ingest_status=ingest_status,
        )
    )


def test_select_stale_school_ids_filters_to_current_work_queue() -> None:
    session = _session()
    try:
        _school(session, 1)
        _site(session, 1, "prefecture_aggregator")
        _doc(session, 10, 1, 2025)

        _school(session, 2)
        _site(session, 2, "prefecture_aggregator")
        _doc(session, 20, 2, 2026)

        _school(session, 3)
        _site(session, 3, "prefecture_aggregator")

        _school(session, 4, "大学")
        _site(session, 4, "prefecture_aggregator")
        _doc(session, 40, 4, 2025)

        _school(session, 5)
        _site(session, 5, "web_search")
        _doc(session, 50, 5, 2025)

        _school(session, 6)
        _site(session, 6, "prefecture_aggregator", http_status=404)
        _doc(session, 60, 6, 2025)
        session.flush()

        ids = select_stale_school_ids(
            session,
            current_fy=2026,
            methods=["prefecture_aggregator"],
            school_type="専門学校",
        )

        assert ids == [1]
    finally:
        session.close()


def test_select_target_missing_school_ids_includes_never_ingested_schools() -> None:
    """The weekly runner must crawl every active school missing current FY,
    not only schools that already had an older-year PDF."""
    session = _session()
    try:
        _school(session, 1)
        _site(session, 1, "prefecture_aggregator")
        _doc(session, 10, 1, 2025)

        _school(session, 2)
        _site(session, 2, "prefecture_aggregator")
        _doc(session, 20, 2, 2026)

        _school(session, 3)
        _site(session, 3, "prefecture_aggregator")

        _school(session, 4, "大学")
        _site(session, 4, "prefecture_aggregator")

        _school(session, 5)
        _site(session, 5, "web_search")

        _school(session, 6)
        _site(session, 6, "prefecture_aggregator", http_status=404)
        session.flush()

        ids = select_target_missing_school_ids(
            session,
            current_fy=2026,
            methods=["prefecture_aggregator"],
            school_type="専門学校",
        )

        assert ids == [1, 3]
    finally:
        session.close()


def test_default_methods_include_reusable_bootstrap_and_operator_urls() -> None:
    session = _session()
    try:
        _school(session, 1)
        _site(session, 1, "prefecture_aggregator")
        _school(session, 2)
        _site(session, 2, "operator_manual")
        _school(session, 3)
        _site(session, 3, "web_search")
        _school(session, 4)
        _site(session, 4, "seed_csv")
        _school(session, 5)
        _site(session, 5, "corporation_pattern")
        _school(session, 6)
        _site(session, 6, "school_domain_override")
        session.flush()

        ids = select_target_missing_school_ids(
            session,
            current_fy=2026,
            methods=list(module.DEFAULT_METHODS),
            school_type="専門学校",
        )

        assert ids == [1, 2, 4, 5, 6]
    finally:
        session.close()


def test_count_no_crawlable_url_schools_ignores_method_filter() -> None:
    session = _session()
    try:
        _school(session, 1)
        _school(session, 2)
        _site(session, 2, "prefecture_aggregator")
        _school(session, 3)
        _site(session, 3, "prefecture_aggregator", http_status=404)
        _school(session, 4)
        _site(session, 4, "operator_manual")
        _school(session, 5, "大学")
        session.flush()

        count = count_no_crawlable_url_schools(
            session,
            methods=["prefecture_aggregator"],
            school_type="専門学校",
        )

        assert count == 2
    finally:
        session.close()


def test_select_stale_school_ids_can_include_all_methods_and_limit() -> None:
    session = _session()
    try:
        for school_id in (1, 2, 3):
            _school(session, school_id)
            _doc(session, school_id, school_id, 2025)
        _site(session, 1, "web_search")
        _site(session, 2, "prefecture_aggregator")
        _site(session, 3, "corporation_pattern")
        session.flush()

        ids = select_stale_school_ids(
            session,
            current_fy=2026,
            methods=None,
            school_type="専門学校",
            limit=2,
        )

        assert ids == [1, 2]
    finally:
        session.close()


def test_snapshot_reports_preserves_target_vs_any_current_fy_distinction() -> None:
    session = _session()
    try:
        _school(session, 1)
        _doc(session, 10, 1, 2026, pdf_type="image_only", ingest_status="ingested")
        session.add(Department(id=100, school_id=1, canonical_name="歯科衛生士科"))
        session.add(
            DepartmentYearly(
                department_id=100,
                document_id=10,
                fiscal_year=2026,
                revision=1,
                is_current=True,
                capacity=80,
                enrollment=70,
            )
        )
        session.flush()

        snapshot = snapshot_reports(session, 2026, "専門学校")

        assert snapshot["coverage"]["schools_with_target_pdf_current_fy"] == 0
        assert snapshot["coverage"]["schools_with_current_fy_doc"] == 1
        assert snapshot["extraction"]["documents_ingested"] == 1
        assert snapshot["extraction"]["yearly_rows_total"] == 1
    finally:
        session.close()


def test_resolve_weekly_paths_anchors_to_app_root(tmp_path: Path) -> None:
    """Sprint 8.7.a — Windows Task Scheduler can invoke the .bat from an
    arbitrary cwd. The Python runner must derive all operational paths from
    the app root, not from process cwd."""

    paths = resolve_weekly_paths(tmp_path)

    assert paths.storage_dir == tmp_path / "data" / "pdfs"
    assert paths.output_dir == tmp_path / "data" / "output" / "target-year-discovery"
    assert paths.last_run_path == tmp_path / "data" / "output" / "last_run.json"
    assert paths.lock_path == tmp_path / "data" / ".lock"
    assert paths.logs_dir == tmp_path / "logs"


def test_parse_args_defaults_to_configured_target_fiscal_year(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "argv", ["run_weekly_target_year_discovery.py"])
    monkeypatch.setattr(module.settings, "target_fiscal_year", 2027)

    args = module.parse_args()

    assert args.current_fy == 2027
    assert args.methods == [
        "prefecture_aggregator",
        "seed_csv",
        "corporation_pattern",
        "school_domain_override",
        "operator_manual",
        "scrapling_stealth",
    ]
    assert args.school_type == "専門学校"
    assert args.request_timeout == 12.0


def test_parse_args_allows_explicit_all_school_types(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "argv", ["run_weekly_target_year_discovery.py", "--school-type", "all"])

    args = module.parse_args()

    assert args.school_type == "all"


def test_write_last_run_json_operator_summary(tmp_path: Path) -> None:
    """last_run.json is the Streamlit banner contract. Keep it small,
    stable, and independent from the full timestamped summary."""

    summary = {
        "run_id": "20260505_010203",
        "started_at": "2026-05-05T01:02:03+00:00",
        "finished_at": "2026-05-05T01:02:10+00:00",
        "dry_run": False,
        "current_fy": 2026,
        "stale_school_count": 3,
        "no_crawlable_url_school_count": 9,
        "target_missing_school_count": 10,
        "new_document_ids": [10, 11],
        "discovery_stats": {"downloaded": 2},
        "ingest_stats": {"processed": 2},
        "delta": {
            "coverage": {
                "schools_with_target_pdf_current_fy": 6,
            },
            "school_fiscal_year_status": {
                "publication_lag": 0,
            },
        },
        "summary_path": str(tmp_path / "summary.json"),
    }
    out = tmp_path / "data" / "output" / "last_run.json"

    write_last_run(summary, out, status="success")

    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["status"] == "success"
    assert payload["run_id"] == "20260505_010203"
    assert payload["current_fy"] == 2026
    assert payload["stale_school_count"] == 3
    assert payload["no_crawlable_url_school_count"] == 9
    assert payload["target_pdf_auto_acquired_count"] == 6
    assert payload["target_pdf_auto_denominator_count"] == 10
    assert payload["target_pdf_auto_denominator_scope"] == "target_missing_schools_before_run"
    assert payload["target_pdf_auto_yield_pct"] == 60.0
    assert payload["operator_reviewable_count"] == 6
    assert payload["operator_reviewable_yield_pct"] == 60.0
    assert payload["ship_gate_auto_yield_pct"] == 60.0
    assert payload["ship_gate_operator_coverage_pct"] == 60.0
    assert payload["ship_gate_metric_basis"] == "weekly_operator_reviewable_acquisition"
    assert payload["ship_gate_status"] == "pass"
    assert payload["new_document_count"] == 2
    assert payload["new_document_ids"] == [10, 11]
    assert payload["summary_path"].endswith("summary.json")
    assert payload["error"] is None


def test_weekly_yield_metrics_count_review_candidate_statuses_as_operator_reviewable() -> None:
    payload = module._weekly_target_pdf_yield_metrics(
        {
            "target_missing_school_count": 10,
            "delta": {
                "coverage": {"schools_with_target_pdf_current_fy": 2},
                "school_fiscal_year_status": {"publication_lag": 3, "target_year_unverified": 2},
            },
        }
    )

    assert payload["target_pdf_auto_acquired_count"] == 2
    assert payload["target_pdf_auto_yield_pct"] == 20.0
    assert payload["operator_reviewable_count"] == 7
    assert payload["operator_reviewable_yield_pct"] == 70.0
    assert payload["ship_gate_metric_basis"] == "weekly_operator_reviewable_acquisition"
    assert payload["ship_gate_status"] == "pass"


def test_write_last_run_uses_atomic_replace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    summary = {
        "run_id": "20260505_010203",
        "started_at": "2026-05-05T01:02:03+00:00",
        "finished_at": "2026-05-05T01:02:10+00:00",
        "dry_run": False,
        "current_fy": 2026,
        "selection_mode": "target_missing",
        "target_missing_school_count": 1,
        "new_document_ids": [],
        "summary_path": str(tmp_path / "summary.json"),
    }
    out = tmp_path / "data" / "output" / "last_run.json"
    calls: list[Path] = []

    def fake_write_text_atomic(path: Path, text: str, *, encoding: str = "utf-8") -> None:
        calls.append(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding=encoding)

    monkeypatch.setattr(module, "write_text_atomic", fake_write_text_atomic)

    write_last_run(summary, out, status="success")

    assert calls == [out]


def test_prune_run_logs_keeps_latest_twelve_by_name(tmp_path: Path) -> None:
    logs = tmp_path / "logs"
    logs.mkdir()
    for day in range(1, 15):
        (logs / f"run-202605{day:02d}.log").write_text(str(day), encoding="utf-8")
    (logs / "ui.log").write_text("keep", encoding="utf-8")

    removed, failed = prune_run_logs(logs, keep=12)

    assert [p.name for p in removed] == ["run-20260501.log", "run-20260502.log"]
    assert failed == []
    remaining = sorted(p.name for p in logs.glob("run-*.log"))
    assert remaining[0] == "run-20260503.log"
    assert remaining[-1] == "run-20260514.log"
    assert (logs / "ui.log").exists()


def test_prune_run_logs_surfaces_unlink_failures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Owner-banned silent failure: when ``unlink`` fails (e.g. log file
    held open by Notepad on Windows) the function must report the path
    + reason so the runner can fold it into its JSON output."""
    logs = tmp_path / "logs"
    logs.mkdir()
    for day in range(1, 4):
        (logs / f"run-202605{day:02d}.log").write_text("x", encoding="utf-8")

    real_unlink = Path.unlink

    def flaky_unlink(self: Path, *args, **kwargs):  # noqa: ANN001
        if self.name == "run-20260501.log":
            raise PermissionError("held open by another process")
        return real_unlink(self, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", flaky_unlink)
    removed, failed = prune_run_logs(logs, keep=1)

    removed_names = {p.name for p in removed}
    failed_names = {p.name for p, _ in failed}
    assert removed_names == {"run-20260502.log"}
    assert failed_names == {"run-20260501.log"}
    assert all("held open" in reason for _, reason in failed)


def test_prune_run_artifacts_keeps_latest_twelve_per_artifact_kind(tmp_path: Path) -> None:
    output = tmp_path / "data" / "output" / "target-year-discovery"
    output.mkdir(parents=True)
    suffixes = (
        "summary.json",
        "discovery-rca-batch-plan.json",
        "discovery-rejections.jsonl",
        "ingest-rejections.jsonl",
    )
    for day in range(1, 15):
        for suffix in suffixes:
            (output / f"weekly-202605{day:02d}-{suffix}").write_text(str(day), encoding="utf-8")
    (output / "manual-note.json").write_text("keep", encoding="utf-8")

    removed, failed = prune_run_artifacts(output, keep=12)

    assert failed == []
    assert len(removed) == 8
    assert all("20260501" in p.name or "20260502" in p.name for p in removed)
    for suffix in suffixes:
        remaining = sorted(p.name for p in output.glob(f"*-{suffix}"))
        assert remaining[0] == f"weekly-20260503-{suffix}"
        assert remaining[-1] == f"weekly-20260514-{suffix}"
    assert (output / "manual-note.json").exists()


def test_run_weekly_respects_shared_lock(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """If UI/manual work is holding data/.lock, the weekly runner must not
    proceed. This is the Windows single-user exclusion contract."""

    session = _session()
    monkeypatch.setattr(module, "SessionLocal", lambda: session)

    lock_path = tmp_path / "data" / ".lock"
    last_run_path = tmp_path / "data" / "output" / "last_run.json"
    with acquire_lock(lock_path, owner="ui"):
        with pytest.raises(LockBusyError):
            run_weekly(
                current_fy=2026,
                methods=["prefecture_aggregator"],
                school_type="専門学校",
                storage_dir=tmp_path / "data" / "pdfs",
                output_dir=tmp_path / "data" / "output" / "target-year-discovery",
                batch_size=10,
                rate_limit=1.5,
                request_timeout=12.0,
                ingest_batch_size=10,
                limit=None,
                dry_run=True,
                lock_path=lock_path,
                last_run_path=last_run_path,
            )

    payload = json.loads(last_run_path.read_text(encoding="utf-8"))
    assert payload["status"] == "lock_busy"
    assert payload["current_fy"] == 2026
    assert payload["school_type"] == "専門学校"
    assert payload["methods"] == ["prefecture_aggregator"]
    assert payload["target_pdf_auto_yield_pct"] is None
    assert "LockBusyError" in payload["error"]


def test_run_weekly_writes_last_run_json_under_lock(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _session()
    monkeypatch.setattr(module, "SessionLocal", lambda: session)

    last_run = tmp_path / "data" / "output" / "last_run.json"
    summary = run_weekly(
        current_fy=2026,
        methods=["prefecture_aggregator"],
        school_type="専門学校",
        storage_dir=tmp_path / "data" / "pdfs",
        output_dir=tmp_path / "data" / "output" / "target-year-discovery",
        batch_size=10,
        rate_limit=1.5,
        request_timeout=12.0,
        ingest_batch_size=10,
        limit=None,
        dry_run=True,
        lock_path=tmp_path / "data" / ".lock",
        last_run_path=last_run,
    )

    assert Path(summary["summary_path"]).is_file()
    payload = json.loads(last_run.read_text(encoding="utf-8"))
    assert payload["status"] == "success"
    assert payload["run_id"] == summary["run_id"]
    assert payload["dry_run"] is True


def test_run_weekly_writes_ui_progress_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _session()
    monkeypatch.setattr(module, "SessionLocal", lambda: session)
    _school(session, 1)
    _site(session, 1, "prefecture_aggregator")
    session.commit()

    progress_path = tmp_path / "logs" / "weekly-rediscovery-20260517-120000.json"
    log_path = tmp_path / "logs" / "weekly-rediscovery-20260517-120000.log"

    run_weekly(
        current_fy=2026,
        methods=["prefecture_aggregator"],
        school_type="専門学校",
        storage_dir=tmp_path / "data" / "pdfs",
        output_dir=tmp_path / "data" / "output" / "target-year-discovery",
        batch_size=10,
        rate_limit=1.5,
        request_timeout=12.0,
        ingest_batch_size=10,
        limit=None,
        dry_run=True,
        lock_path=tmp_path / "data" / ".lock",
        last_run_path=tmp_path / "data" / "output" / "last_run.json",
        progress_path=progress_path,
        progress_log_path=log_path,
    )

    payload = json.loads(progress_path.read_text(encoding="utf-8"))
    assert payload["status"] == "succeeded"
    assert payload["current_step"] == 5
    assert payload["total_steps"] == 5
    assert payload["percent"] == 1.0
    assert payload["message"] == "週次URL/PDF再取得が完了しました。"
    assert payload["log_path"] == str(log_path)
    assert payload["details"]["sites_total"] == 1
    assert payload["details"]["target_pdf_auto_denominator_count"] == 1
    assert payload["details"]["operator_reviewable_yield_pct"] == 0.0


def test_run_weekly_writes_summary_and_last_run_atomically(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _session()
    monkeypatch.setattr(module, "SessionLocal", lambda: session)
    calls: list[Path] = []

    def fake_write_text_atomic(path: Path, text: str, *, encoding: str = "utf-8") -> None:
        calls.append(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding=encoding)

    monkeypatch.setattr(module, "write_text_atomic", fake_write_text_atomic)

    last_run = tmp_path / "data" / "output" / "last_run.json"
    summary = run_weekly(
        current_fy=2026,
        methods=["prefecture_aggregator"],
        school_type="専門学校",
        storage_dir=tmp_path / "data" / "pdfs",
        output_dir=tmp_path / "data" / "output" / "target-year-discovery",
        batch_size=10,
        rate_limit=1.5,
        request_timeout=12.0,
        ingest_batch_size=10,
        limit=None,
        dry_run=True,
        lock_path=tmp_path / "data" / ".lock",
        last_run_path=last_run,
    )

    assert Path(summary["summary_path"]) in calls
    assert last_run in calls


def test_run_weekly_separates_target_missing_from_stale_count(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Default weekly work queue includes never-ingested schools, but stale
    fallback count must remain a narrower diagnostic so the UI does not present
    all target-missing schools as old-year fallback."""
    session = _session()
    monkeypatch.setattr(module, "SessionLocal", lambda: session)
    _school(session, 1)
    _site(session, 1, "prefecture_aggregator")
    _doc(session, 10, 1, 2025)
    _school(session, 2)
    _site(session, 2, "prefecture_aggregator")
    session.commit()

    summary = run_weekly(
        current_fy=2026,
        methods=["prefecture_aggregator"],
        school_type="専門学校",
        storage_dir=tmp_path / "data" / "pdfs",
        output_dir=tmp_path / "data" / "output" / "target-year-discovery",
        batch_size=10,
        rate_limit=1.5,
        request_timeout=12.0,
        ingest_batch_size=10,
        limit=None,
        dry_run=True,
        lock_path=None,
        last_run_path=None,
    )

    assert summary["selection_mode"] == "target_missing"
    assert summary["target_missing_school_count"] == 2
    assert summary["stale_school_count"] == 1
    assert summary["no_crawlable_url_school_count"] == 0


def test_run_weekly_passes_current_fy_to_ingestion(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Manual FY overrides must reach ingestion, not stop at discovery."""

    session = _session()
    monkeypatch.setattr(module, "SessionLocal", lambda: session)
    _school(session, 1)
    _site(session, 1, "prefecture_aggregator")
    session.commit()
    captured: dict[str, object] = {}

    def fake_run_pdf_discovery(session_arg, **_kwargs):  # noqa: ANN001, ANN003
        _doc(session_arg, 20, 1, 2025, ingest_status="pending")
        session_arg.flush()
        return {"crawled": 1, "downloaded": 1, "skipped": 0, "failed": 0}

    def fake_run_ingestion(session_arg, **kwargs):  # noqa: ANN001, ANN003
        captured["session"] = session_arg
        captured["kwargs"] = kwargs
        return {"processed": 1, "departments_created": 0, "yearly_upserted": 0, "skipped": 0}

    monkeypatch.setattr(module, "run_pdf_discovery", fake_run_pdf_discovery)
    monkeypatch.setattr(module, "run_ingestion", fake_run_ingestion)

    run_weekly(
        current_fy=2025,
        methods=["prefecture_aggregator"],
        school_type="専門学校",
        storage_dir=tmp_path / "data" / "pdfs",
        output_dir=tmp_path / "data" / "output" / "target-year-discovery",
        batch_size=10,
        rate_limit=1.5,
        request_timeout=12.0,
        ingest_batch_size=10,
        limit=None,
        dry_run=False,
        lock_path=None,
        last_run_path=None,
    )

    assert captured["session"] is session
    assert captured["kwargs"]["document_ids"] == [20]
    assert captured["kwargs"]["target_fiscal_year"] == 2025


def test_run_weekly_writes_discovery_rca_batch_plan_artifact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Weekly discovery should leave a ready Codex RCA queue next to the
    evidence log, so a disconnected Windows session can be continued from
    artifacts alone."""
    session = _session()
    monkeypatch.setattr(module, "SessionLocal", lambda: session)
    _school(session, 1)
    _site(session, 1, "prefecture_aggregator")
    session.commit()

    def fake_run_pdf_discovery(*args, **kwargs):  # noqa: ANN002, ANN003
        evidence_path = kwargs["evidence_path"]
        evidence_path.write_text(
            json.dumps(
                {
                    "school_id": 1,
                    "reason": "target_fiscal_year_not_detected",
                    "pdf_type": "target",
                    "pdf_url": "https://example1.ac.jp/support.pdf",
                },
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        return {"processed": 1, "downloaded": 0}

    monkeypatch.setattr(module, "run_pdf_discovery", fake_run_pdf_discovery)
    last_run = tmp_path / "data" / "output" / "last_run.json"

    summary = run_weekly(
        current_fy=2026,
        methods=["prefecture_aggregator"],
        school_type="専門学校",
        storage_dir=tmp_path / "data" / "pdfs",
        output_dir=tmp_path / "data" / "output" / "target-year-discovery",
        batch_size=10,
        rate_limit=1.5,
        request_timeout=12.0,
        ingest_batch_size=10,
        limit=None,
        dry_run=False,
        lock_path=None,
        last_run_path=last_run,
    )

    rca = summary["discovery_rca"]
    assert rca["batch_plan_item_count"] == 1
    plan_path = Path(rca["batch_plan_path"])
    assert plan_path.name.endswith("-discovery-rca-batch-plan.json")
    assert plan_path.is_file()
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    assert plan["items"][0]["packet"]["school_id"] == 1
    assert plan["items"][0]["bucket"] == "target_form_without_year_evidence"
    assert "Investigate this EIDP school as a single-school RCA packet." in plan["items"][0]["prompt"]

    last_run_payload = json.loads(last_run.read_text(encoding="utf-8"))
    assert last_run_payload["discovery_rca"]["batch_plan_path"] == str(plan_path)
    assert last_run_payload["discovery_rca"]["batch_plan_item_count"] == 1
