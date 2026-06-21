from __future__ import annotations

import csv
import importlib.util
import io
import json
import sys
import zipfile
from pathlib import Path


def _load_module():
    script = Path(__file__).resolve().parents[2] / "scripts" / "build_false_reject_audit.py"
    spec = importlib.util.spec_from_file_location("build_false_reject_audit", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_stage6_archive(path: Path) -> Path:
    rejection_rows = [
        {
            "school_id": 1,
            "reason": "fiscal_year_mismatch:2025",
            "pdf_type": "target",
            "detected_fiscal_year": 2025,
            "year_evidence": "pdf_body:2025",
            "anchor_text": "2025年度 様式第2号",
            "page_url": "https://alpha.example/disclosure",
            "pdf_url": "https://alpha.example/r7.pdf",
        },
        {
            "school_id": 2,
            "reason": "pre_filtered_non_target_hint",
            "pdf_type": "non_target",
            "anchor_text": "GPA",
            "page_url": "https://beta.example/disclosure",
            "pdf_url": "https://beta.example/gpa.pdf",
        },
        {
            "school_id": 2,
            "reason": "pre_filtered_non_target_hint",
            "pdf_type": "non_target",
            "anchor_text": "GPA duplicate",
            "page_url": "https://beta.example/disclosure",
            "pdf_url": "https://beta.example/gpa-2.pdf",
        },
        {
            "school_id": 3,
            "reason": "classified_non_target",
            "pdf_type": "non_target",
            "anchor_text": "学校評価",
            "page_url": "https://gamma.example/disclosure",
            "pdf_url": "https://gamma.example/eval.pdf",
        },
        {
            "school_id": 8,
            "reason": "classified_non_target",
            "pdf_type": "non_target",
            "anchor_text": "令和8年度 申請関係書類",
            "page_url": "https://theta.example/disclosure",
            "pdf_url": "https://theta.example/form-candidate.pdf",
        },
        {
            "school_id": 4,
            "reason": "target_fiscal_year_not_detected",
            "pdf_type": "target",
            "year_evidence": "target_application_no_year",
            "anchor_text": "大学等における修学の支援に関する法律第7条第1項の確認に係る申請書",
            "page_url": "https://delta.example/disclosure",
            "pdf_url": "https://delta.example/form.pdf",
        },
        {
            "school_id": 5,
            "reason": "no_candidates_found",
            "page_url": "https://epsilon.example/disclosure",
        },
        {
            "school_id": 6,
            "reason": "discovery_error",
            "page_url": "https://zeta.example/disclosure",
        },
        {
            "school_id": 7,
            "reason": "pdf_school_mismatch",
            "pdf_type": "target",
            "page_url": "https://eta.example/disclosure",
            "pdf_url": "https://sibling.example/form.pdf",
        },
    ]
    entries = {
        "BUILD_INFO.json": '{"git_commit": "abc"}\n',
        "logs/diagnostics-20260620-000000.txt": "diag\n",
        "data/output/last_run.json": json.dumps(
            {
                "current_fy": 2026,
                "target_pdf_auto_denominator_count": 5,
                "target_pdf_excel_ready_acquired_count": 2,
                "target_pdf_excel_ready_yield_pct": 40.0,
                "ship_gate_status": "below_gate",
            },
            ensure_ascii=False,
        ),
        "data/output/target-year-discovery/20260620_000000-discovery-rejections.jsonl": "\n".join(
            json.dumps(row, ensure_ascii=False) for row in rejection_rows
        )
        + "\n",
        "data/output/target-year-discovery/20260620_000000-discovery-rca-batch-plan.json": json.dumps(
            {"target_fiscal_year": 2026, "total_candidates": 8, "items": []},
            ensure_ascii=False,
        ),
    }
    manifest = {
        "included": [
            {"label": "build_info", "path": "BUILD_INFO.json", "size": len(entries["BUILD_INFO.json"])},
            {
                "label": "diagnostics",
                "path": "logs/diagnostics-20260620-000000.txt",
                "size": len(entries["logs/diagnostics-20260620-000000.txt"]),
            },
            {
                "label": "last_run",
                "path": "data/output/last_run.json",
                "size": len(entries["data/output/last_run.json"]),
            },
            {
                "label": "discovery_evidence",
                "path": "data/output/target-year-discovery/20260620_000000-discovery-rejections.jsonl",
                "size": len(entries["data/output/target-year-discovery/20260620_000000-discovery-rejections.jsonl"]),
            },
            {
                "label": "discovery_rca",
                "path": "data/output/target-year-discovery/20260620_000000-discovery-rca-batch-plan.json",
                "size": len(entries["data/output/target-year-discovery/20260620_000000-discovery-rca-batch-plan.json"]),
            },
        ],
        "missing_patterns": [],
    }
    with zipfile.ZipFile(path, "w") as zf:
        for name, content in entries.items():
            zf.writestr(name, content)
        zf.writestr("stage6-evidence-manifest.json", json.dumps(manifest))
    return path


def test_false_reject_audit_packet_groups_rejection_buckets(tmp_path: Path) -> None:
    module = _load_module()
    archive = _write_stage6_archive(tmp_path / "stage6-evidence.zip")

    packet = module.build_false_reject_audit_packet(archive, sample_size=1)

    assert packet["ok"] is True
    assert packet["strict_yield"]["release_forecast"] == "NOT_READY"
    assert packet["strict_yield"]["ship_gate_met"] is False
    assert packet["model_failure_framing"]["generic_model_failure_supported"] is False
    assert [bucket["bucket"] for bucket in packet["audit_buckets"]] == [
        "fiscal_year_mismatch",
        "pre_filtered_non_target_hint",
        "classified_non_target",
        "target_fiscal_year_not_detected",
        "site_entry_fetch_identity",
    ]
    assert packet["audit_buckets"][0]["total_rows"] == 1
    assert packet["audit_buckets"][1]["total_rows"] == 2
    assert packet["audit_buckets"][1]["sampled_rows"] == 1
    assert packet["audit_buckets"][4]["total_rows"] == 3
    assert packet["audit_buckets"][4]["rows"][0]["reason"] == "no_candidates_found"
    assert len(packet["audit_buckets"][0]["rows"][0]["audit_row_id"]) == 16


def test_false_reject_audit_cli_renders_markdown_and_json(tmp_path: Path, capsys) -> None:
    module = _load_module()
    archive = _write_stage6_archive(tmp_path / "stage6-evidence.zip")

    assert module.main([str(archive), "--sample-size", "2"]) == 0
    markdown = capsys.readouterr().out
    assert "Stage 6 False-Reject Audit Packet" in markdown
    assert "Generic algorithm/model failure supported: `False`" in markdown
    assert "fiscal_year_mismatch" in markdown

    assert module.main([str(archive), "--json", "--sample-size", "2"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["basis"] == "stage6_false_reject_audit_packet"
    assert payload["audit_buckets"][3]["bucket"] == "target_fiscal_year_not_detected"


def test_false_reject_audit_review_csv_can_be_validated(tmp_path: Path, capsys) -> None:
    module = _load_module()
    archive = _write_stage6_archive(tmp_path / "stage6-evidence.zip")
    packet = module.build_false_reject_audit_packet(archive, sample_size=2)

    review_csv = module.render_review_csv(packet)
    assert "audit_row_id,bucket,decision,reviewer,reviewed_at" in review_csv
    assert "suggested_decision,suggested_decision_basis" in review_csv

    validation = module.validate_review_csv(packet, review_csv)
    assert validation["ok"] is True
    assert validation["review_status"] == "incomplete"
    assert validation["defect_framing"]["status"] == "pending_review"
    assert validation["defect_framing"]["specific_algorithm_or_rule_defect_supported"] is False
    assert validation["submitted_rows"] == validation["expected_rows"]
    assert validation["completed_decisions"] == 0
    assert validation["blank_decisions"] == validation["expected_rows"]

    rows = list(csv.DictReader(io.StringIO(review_csv)))
    fiscal_row = next(row for row in rows if row["bucket"] == "fiscal_year_mismatch")
    assert fiscal_row["decision"] == ""
    assert fiscal_row["suggested_decision"] == "correct_reject"
    assert "Detected fiscal year 2025 is not FY2026" in fiscal_row["suggested_decision_basis"]
    yearless_row = next(row for row in rows if row["bucket"] == "target_fiscal_year_not_detected")
    assert yearless_row["decision"] == ""
    assert yearless_row["suggested_decision"] == "needs_operator_review"
    ambiguous_non_target_row = next(row for row in rows if row["school_id"] == "8")
    assert ambiguous_non_target_row["decision"] == ""
    assert ambiguous_non_target_row["suggested_decision"] == "needs_operator_review"
    assert "not obviously safe" in ambiguous_non_target_row["suggested_decision_basis"]
    legacy_csv = io.StringIO()
    legacy_columns = [
        column
        for column in module.REVIEW_CSV_COLUMNS
        if column not in {"suggested_decision", "suggested_decision_basis"}
    ]
    legacy_writer = csv.DictWriter(
        legacy_csv,
        fieldnames=legacy_columns,
        extrasaction="ignore",
        lineterminator="\n",
    )
    legacy_writer.writeheader()
    legacy_writer.writerows(rows)
    legacy_validation = module.validate_review_csv(packet, legacy_csv.getvalue())
    assert legacy_validation["ok"] is True
    assert legacy_validation["review_status"] == "incomplete"
    for row in rows:
        row["decision"] = "correct_reject"
        row["reviewer"] = "owner"
        row["reviewed_at"] = "2026-06-21T00:00:00+09:00"

    def render_rows(rows_to_render: list[dict[str, str]]) -> str:
        rendered = io.StringIO()
        writer = csv.DictWriter(rendered, fieldnames=module.REVIEW_CSV_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows_to_render)
        return rendered.getvalue()

    completed = io.StringIO()
    writer = csv.DictWriter(completed, fieldnames=module.REVIEW_CSV_COLUMNS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)

    completed_validation = module.validate_review_csv(packet, completed.getvalue(), require_decisions=True)
    assert completed_validation["ok"] is True
    assert completed_validation["review_status"] == "complete"
    assert completed_validation["completed_decisions"] == len(rows)
    assert completed_validation["decision_counts"] == {"correct_reject": len(rows)}
    assert completed_validation["context_mismatch_count"] == 0
    assert completed_validation["bucket_decision_counts"]["fiscal_year_mismatch"] == {"correct_reject": 1}
    assert completed_validation["bucket_decision_counts"]["site_entry_fetch_identity"] == {"correct_reject": 2}
    assert completed_validation["defect_framing"] == {
        "generic_model_failure_supported": False,
        "specific_algorithm_or_rule_defect_supported": False,
        "status": "not_supported",
        "false_reject_rows": 0,
        "needs_operator_review_rows": 0,
        "correct_reject_rows": len(rows),
        "reason": (
            "Completed review found no false-reject rows; below-gate yield remains better "
            "explained by correct strict rejects unless new evidence appears."
        ),
    }
    completed_rca_summary = module.render_review_rca_summary(packet, completed_validation)
    assert "False-Reject RCA Summary" in completed_rca_summary
    assert "RCA conclusion: `GENERIC_MODEL_FAILURE_NOT_SUPPORTED`" in completed_rca_summary
    assert "Specific algorithm/rule defect supported: `False`" in completed_rca_summary
    assert "full owner return gate must still pass" in completed_rca_summary
    blank_audit_log = module.render_review_audit_log(packet, review_csv, validation)
    assert blank_audit_log == ""
    audit_log = module.render_review_audit_log(packet, completed.getvalue(), completed_validation)
    audit_events = [json.loads(line) for line in audit_log.splitlines()]
    assert len(audit_events) == len(rows)
    assert audit_events[0]["event_type"] == "false_reject_review_decision"
    assert audit_events[0]["basis"] == "false_reject_review_decision_audit_log"
    assert audit_events[0]["decision"] == "correct_reject"
    assert audit_events[0]["reviewer"] == "owner"
    assert audit_events[0]["reviewed_at"] == "2026-06-21T00:00:00+09:00"
    assert len(audit_events[0]["context_hash_sha256"]) == 64
    assert "decision" not in audit_events[0]["context"]
    assert "reviewer" not in audit_events[0]["context"]
    assert audit_events[0]["context"]["reason"] == rows[0]["reason"]
    assert audit_events[0]["release_forecast"] == "NOT_READY"
    assert "does not accept rejected rows into Excel" in audit_events[0]["excel_gate_effect"]

    false_reject_rows = [dict(row) for row in rows]
    false_reject_rows[0]["decision"] = "false_reject"
    false_reject_rows[0]["notes"] = "Official page carries trusted FY2026/R8 target-form evidence."
    false_reject_validation = module.validate_review_csv(
        packet, render_rows(false_reject_rows), require_decisions=True
    )
    assert false_reject_validation["ok"] is True
    assert false_reject_validation["defect_framing"]["status"] == "specific_false_rejects_found"
    assert false_reject_validation["defect_framing"]["specific_algorithm_or_rule_defect_supported"] is True
    assert false_reject_validation["defect_framing"]["generic_model_failure_supported"] is False
    assert false_reject_validation["defect_framing"]["false_reject_rows"] == 1
    false_reject_rca_summary = module.render_review_rca_summary(packet, false_reject_validation)
    assert "RCA conclusion: `SPECIFIC_RULE_DEFECTS_FOUND`" in false_reject_rca_summary
    assert "Fix the specific false-reject causes" in false_reject_rca_summary

    operator_review_rows = [dict(row) for row in rows]
    operator_review_rows[0]["decision"] = "needs_operator_review"
    operator_review_rows[0]["notes"] = "Evidence exists but needs owner confirmation."
    operator_review_validation = module.validate_review_csv(
        packet, render_rows(operator_review_rows), require_decisions=True
    )
    assert operator_review_validation["ok"] is True
    assert operator_review_validation["defect_framing"]["status"] == "inconclusive_operator_review"
    assert operator_review_validation["defect_framing"]["specific_algorithm_or_rule_defect_supported"] is False

    tampered_rows = [dict(row) for row in rows]
    tampered_rows[0]["reason"] = "accepted_downloaded"
    tampered = io.StringIO()
    tampered_writer = csv.DictWriter(tampered, fieldnames=module.REVIEW_CSV_COLUMNS, lineterminator="\n")
    tampered_writer.writeheader()
    tampered_writer.writerows(tampered_rows)
    tampered_validation = module.validate_review_csv(packet, tampered.getvalue(), require_decisions=True)
    assert tampered_validation["ok"] is False
    assert tampered_validation["context_mismatch_count"] == 1
    assert "reason changed" in tampered_validation["errors"][0]

    tampered_suggestion_rows = [dict(row) for row in rows]
    tampered_suggestion_rows[0]["suggested_decision"] = "false_reject"
    tampered_suggestion_validation = module.validate_review_csv(
        packet, render_rows(tampered_suggestion_rows), require_decisions=True
    )
    assert tampered_suggestion_validation["ok"] is False
    assert tampered_suggestion_validation["context_mismatch_count"] == 1
    assert "suggested_decision changed" in tampered_suggestion_validation["errors"][0]

    unsigned_rows = [dict(row) for row in rows]
    unsigned_rows[0]["reviewer"] = ""
    unsigned_validation = module.validate_review_csv(packet, render_rows(unsigned_rows), require_decisions=True)
    assert unsigned_validation["ok"] is False
    assert "reviewer is required" in unsigned_validation["errors"][0]

    bad_timestamp_rows = [dict(row) for row in rows]
    bad_timestamp_rows[0]["reviewed_at"] = "2026-06-21"
    bad_timestamp_validation = module.validate_review_csv(
        packet, render_rows(bad_timestamp_rows), require_decisions=True
    )
    assert bad_timestamp_validation["ok"] is False
    assert "reviewed_at must be an ISO timestamp" in bad_timestamp_validation["errors"][0]

    unsupported_rows = [dict(row) for row in rows]
    unsupported_rows[0]["decision"] = "false_reject"
    unsupported_rows[0]["notes"] = ""
    unsupported_validation = module.validate_review_csv(packet, render_rows(unsupported_rows), require_decisions=True)
    assert unsupported_validation["ok"] is False
    assert "notes are required" in unsupported_validation["errors"][0]

    review_path = tmp_path / "review.csv"
    review_path.write_text(review_csv, encoding="utf-8")
    completed_review_path = tmp_path / "completed-review.csv"
    completed_review_path.write_text(completed.getvalue(), encoding="utf-8")
    assert module.main([str(archive), "--sample-size", "2", "--format", "csv"]) == 0
    csv_output = capsys.readouterr().out
    assert "false_reject_signal,notes" in csv_output.splitlines()[0]

    assert module.main([str(archive), "--sample-size", "2", "--validate-review-csv", str(review_path)]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["basis"] == "false_reject_review_decision_validation"
    assert payload["review_status"] == "incomplete"

    assert (
        module.main(
            [
                str(archive),
                "--sample-size",
                "2",
                "--validate-review-csv",
                str(review_path),
                "--require-decisions",
            ]
        )
        == 1
    )
    required_payload = json.loads(capsys.readouterr().out)
    assert required_payload["review_status"] == "invalid"

    validation_summary = module.render_review_validation_summary(packet, required_payload)
    assert "False-Reject Review Validation Summary" in validation_summary
    assert "Release Forecast: `NOT_READY`" in validation_summary
    assert "Validation OK: `False`" in validation_summary
    assert f"Completed decisions: `0/{len(rows)}`" in validation_summary
    assert f"Blank decisions: `{len(rows)}`" in validation_summary
    assert "Context mismatches: `0`" in validation_summary
    assert "line 2: decision is required" in validation_summary
    assert "This summary is read-only" in validation_summary
    assert "allow any row into Excel" in validation_summary
    assert "Fix the listed CSV errors" in validation_summary
    invalid_rca_summary = module.render_review_rca_summary(packet, required_payload)
    assert "RCA conclusion: `INVALID_RETURN`" in invalid_rca_summary
    assert "Fix the returned CSV errors" in invalid_rca_summary
    assert "does not allow rejected rows into Excel" in invalid_rca_summary

    assert (
        module.main(
            [
                str(archive),
                "--sample-size",
                "2",
                "--validate-review-csv",
                str(review_path),
                "--require-decisions",
                "--format",
                "review-validation-summary",
            ]
        )
        == 1
    )
    cli_validation_summary = capsys.readouterr().out
    assert "False-Reject Review Validation Summary" in cli_validation_summary
    assert "Review status: `invalid`" in cli_validation_summary

    assert (
        module.main(
            [
                str(archive),
                "--sample-size",
                "2",
                "--validate-review-csv",
                str(review_path),
                "--require-decisions",
                "--format",
                "review-rca-summary",
            ]
        )
        == 1
    )
    cli_rca_summary = capsys.readouterr().out
    assert "False-Reject RCA Summary" in cli_rca_summary
    assert "RCA conclusion: `INVALID_RETURN`" in cli_rca_summary

    assert (
        module.main(
            [
                str(archive),
                "--sample-size",
                "2",
                "--validate-review-csv",
                str(completed_review_path),
                "--format",
                "review-audit-log",
            ]
        )
        == 2
    )
    missing_required = capsys.readouterr()
    assert missing_required.out == ""
    assert "--format review-audit-log requires --require-decisions" in missing_required.err

    assert (
        module.main(
            [
                str(archive),
                "--sample-size",
                "2",
                "--validate-review-csv",
                str(completed_review_path),
                "--require-decisions",
                "--format",
                "review-audit-log",
            ]
        )
        == 0
    )
    cli_audit_events = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert len(cli_audit_events) == len(rows)
    assert cli_audit_events[0]["audit_row_id"] == audit_events[0]["audit_row_id"]
    assert cli_audit_events[0]["context_hash_sha256"] == audit_events[0]["context_hash_sha256"]


def test_false_reject_audit_review_summary_prioritizes_non_obvious_rows(tmp_path: Path, capsys) -> None:
    module = _load_module()
    archive = _write_stage6_archive(tmp_path / "stage6-evidence.zip")
    packet = module.build_false_reject_audit_packet(archive, sample_size=2)

    summary = module.render_review_summary(packet)

    assert "False-Reject Review Summary" in summary
    assert "Release Forecast: `NOT_READY`" in summary
    assert "This is read-only triage guidance" in summary
    assert "| `correct_reject` | 4 |" in summary
    assert "| `needs_operator_review` | 4 |" in summary
    assert "## Priority Review Rows" in summary
    assert "`target_fiscal_year_not_detected`" in summary
    assert "`site_entry_fetch_identity`" in summary
    assert "`fiscal_year_mismatch`" not in summary.partition("## Priority Review Rows")[2]
    assert "does not fill the worksheet" in summary

    assert module.main([str(archive), "--sample-size", "2", "--format", "review-summary"]) == 0
    cli_summary = capsys.readouterr().out
    assert "Suggested Decisions By Bucket" in cli_summary
    assert "context_mismatch_count=0" in cli_summary


def test_false_reject_audit_review_worklist_lists_owner_next_actions(tmp_path: Path, capsys) -> None:
    module = _load_module()
    archive = _write_stage6_archive(tmp_path / "stage6-evidence.zip")
    packet = module.build_false_reject_audit_packet(archive, sample_size=2)

    worklist = module.render_review_worklist(packet)

    assert "Owner False-Reject Review Worklist" in worklist
    assert "Release Forecast: `NOT_READY`" in worklist
    assert "Rows requiring owner worksheet decision: `8`" in worklist
    assert "This worklist is read-only" in worklist
    assert "does not fill decisions" in worklist
    assert "## 1. Inspect official evidence before deciding (`4` rows)" in worklist
    assert "## 2. Confirm suggested correct rejects (`4` rows)" in worklist
    assert worklist.index("Inspect official evidence") < worklist.index("Confirm suggested correct rejects")
    assert "https://theta.example/form-candidate.pdf" in worklist
    assert "https://delta.example/disclosure" in worklist
    assert "`fiscal_year_mismatch`" in worklist

    assert module.main([str(archive), "--sample-size", "2", "--format", "review-worklist"]) == 0
    cli_worklist = capsys.readouterr().out
    assert "Owner False-Reject Review Worklist" in cli_worklist
    assert "Suggested Decision Counts" in cli_worklist


def test_false_reject_audit_triage_marks_explicit_non_target_years_correct_reject() -> None:
    module = _load_module()

    detected_decision, detected_basis = module._suggested_triage_decision(
        bucket_name="classified_non_target",
        row={"detected_fiscal_year": 2025, "anchor_text": ""},
        target_fiscal_year=2026,
    )
    assert detected_decision == "correct_reject"
    assert "Explicit fiscal year 2025 is not FY2026" in detected_basis

    western_decision, western_basis = module._suggested_triage_decision(
        bucket_name="target_fiscal_year_not_detected",
        row={"anchor_text": "2021年度"},
        target_fiscal_year=2026,
    )
    assert western_decision == "correct_reject"
    assert "Explicit fiscal year 2021 is not FY2026" in western_basis

    reiwa_decision, reiwa_basis = module._suggested_triage_decision(
        bucket_name="classified_non_target",
        row={"anchor_text": "情報処理科 令和6年度"},
        target_fiscal_year=2026,
    )
    assert reiwa_decision == "correct_reject"
    assert "Explicit fiscal year 2024 is not FY2026" in reiwa_basis

    target_year_decision, target_year_basis = module._suggested_triage_decision(
        bucket_name="classified_non_target",
        row={"anchor_text": "令和8年度 申請関係書類"},
        target_fiscal_year=2026,
    )
    assert target_year_decision == "needs_operator_review"
    assert "not obviously safe" in target_year_basis


def test_false_reject_audit_validation_summary_requires_review_csv(tmp_path: Path, capsys) -> None:
    module = _load_module()
    archive = _write_stage6_archive(tmp_path / "stage6-evidence.zip")

    assert module.main([str(archive), "--format", "review-validation-summary"]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "--format review-validation-summary requires --validate-review-csv" in captured.err

    assert module.main([str(archive), "--format", "review-rca-summary"]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "--format review-rca-summary requires --validate-review-csv" in captured.err

    assert module.main([str(archive), "--format", "review-audit-log"]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "--format review-audit-log requires --validate-review-csv" in captured.err
