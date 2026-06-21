from __future__ import annotations

import csv
import importlib.util
import io
import json
import sys
from pathlib import Path
from typing import Any


def _load_mapper_module():
    script = Path(__file__).resolve().parents[2] / "scripts" / "apply_owner_short_form_return.py"
    spec = importlib.util.spec_from_file_location("apply_owner_short_form_return", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _load_audit_module():
    script = Path(__file__).resolve().parents[2] / "scripts" / "build_false_reject_audit.py"
    spec = importlib.util.spec_from_file_location("build_false_reject_audit", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _packet() -> dict[str, Any]:
    return {
        "archive": "stage6-evidence.zip",
        "strict_yield": {
            "release_forecast": "NOT_READY",
            "target_fiscal_year": 2026,
            "excel_ready_acquired_count": 1,
            "denominator": 2,
            "excel_ready_yield_pct": 50.0,
            "required_yield_pct": 60.0,
            "ship_gate_status": "below_gate",
        },
        "audit_buckets": [
            {
                "bucket": "fiscal_year_mismatch",
                "review_question": "Old-year target form?",
                "false_reject_signal": "Trusted FY2026 evidence exists.",
                "rows": [
                    {
                        "audit_row_id": "row-old-year",
                        "school_id": 10,
                        "reason": "fiscal_year_mismatch:2025",
                        "pdf_type": "target",
                        "detected_fiscal_year": 2025,
                        "year_evidence": "pdf_body:2025",
                        "trusted_year_evidence": "school_domain_override_disclosure",
                        "discovery_method": "school_domain_override",
                        "anchor_text": "2025年度 様式第2号",
                        "page_url": "https://alpha.example/disclosure",
                        "pdf_url": "https://alpha.example/r7.pdf",
                    }
                ],
            },
            {
                "bucket": "target_fiscal_year_not_detected",
                "review_question": "Target form with missing trusted year?",
                "false_reject_signal": "FY2026/R8 official evidence exists.",
                "rows": [
                    {
                        "audit_row_id": "row-yearless",
                        "school_id": 11,
                        "reason": "target_fiscal_year_not_detected",
                        "pdf_type": "target",
                        "year_evidence": "target_application_no_year",
                        "trusted_year_evidence": "official_disclosure_page",
                        "discovery_method": "official_site",
                        "anchor_text": "確認申請書",
                        "page_url": "https://beta.example/disclosure",
                        "pdf_url": "https://beta.example/form.pdf",
                    }
                ],
            },
        ],
    }


def _short_form_from_review_csv(review_csv: str, decisions: dict[str, tuple[str, str]]) -> str:
    rows = list(csv.DictReader(io.StringIO(review_csv)))
    output = io.StringIO()
    fieldnames = [
        "pack",
        "audit_row_id",
        "school",
        "school_id",
        "page_url",
        "pdf_url",
        "rejection_bucket",
        "system_suggested_decision",
        "owner_decision",
        "owner_notes",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        decision, notes = decisions.get(row["audit_row_id"], ("", ""))
        writer.writerow(
            {
                "pack": "Pack A",
                "audit_row_id": row["audit_row_id"],
                "school": f"school_id {row['school_id']}",
                "school_id": row["school_id"],
                "page_url": row["page_url"],
                "pdf_url": row["pdf_url"],
                "rejection_bucket": row["bucket"],
                "system_suggested_decision": row["suggested_decision"],
                "owner_decision": decision,
                "owner_notes": notes,
            }
        )
    return output.getvalue()


def test_owner_short_form_maps_to_canonical_review_csv_and_still_requires_validator(tmp_path: Path, capsys) -> None:
    mapper = _load_mapper_module()
    audit = _load_audit_module()
    packet = _packet()
    canonical_csv = audit.render_review_csv(packet)
    short_form_csv = _short_form_from_review_csv(
        canonical_csv,
        {
            "row-old-year": ("correct_reject", ""),
            "row-yearless": ("needs_operator_review", "Owner needs to inspect the official FY2026 page."),
        },
    )

    mapped_csv, summary = mapper.apply_owner_short_form_return(
        canonical_csv_text=canonical_csv,
        short_form_csv_text=short_form_csv,
        reviewer="owner",
        reviewed_at="2026-06-21T23:00:00+09:00",
        require_complete=True,
    )

    assert summary["ok"] is True
    assert summary["release_forecast"] == "NOT_READY"
    assert summary["completed_decisions"] == 2
    assert "does not allow rejected rows into Excel" in summary["excel_gate_warning"]

    validation = audit.validate_review_csv(packet, mapped_csv, require_decisions=True)
    assert validation["ok"] is True
    assert validation["review_status"] == "complete"
    assert validation["context_mismatch_count"] == 0
    assert validation["decision_counts"] == {"correct_reject": 1, "needs_operator_review": 1}
    assert validation["defect_framing"]["status"] == "inconclusive_operator_review"

    canonical_path = tmp_path / "canonical.csv"
    short_form_path = tmp_path / "short-form.csv"
    output_path = tmp_path / "mapped.csv"
    canonical_path.write_text(canonical_csv, encoding="utf-8")
    short_form_path.write_text(short_form_csv, encoding="utf-8")
    assert (
        mapper.main(
            [
                "--canonical-review-csv",
                str(canonical_path),
                "--owner-short-form-csv",
                str(short_form_path),
                "--reviewer",
                "owner",
                "--reviewed-at",
                "2026-06-21T23:00:00+09:00",
                "--require-complete",
                "--output",
                str(output_path),
                "--json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert output_path.read_text(encoding="utf-8") == mapped_csv


def test_owner_short_form_mapping_rejects_context_changes() -> None:
    mapper = _load_mapper_module()
    audit = _load_audit_module()
    canonical_csv = audit.render_review_csv(_packet())
    short_form_csv = _short_form_from_review_csv(canonical_csv, {"row-old-year": ("correct_reject", "")})
    rows = list(csv.DictReader(io.StringIO(short_form_csv)))
    rows[0]["page_url"] = "https://tampered.example/disclosure"
    rendered = io.StringIO()
    writer = csv.DictWriter(rendered, fieldnames=rows[0].keys(), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)

    mapped_csv, summary = mapper.apply_owner_short_form_return(
        canonical_csv_text=canonical_csv,
        short_form_csv_text=rendered.getvalue(),
        reviewer="owner",
        reviewed_at="2026-06-21T23:00:00+09:00",
    )

    assert mapped_csv == ""
    assert summary["ok"] is False
    assert "page_url changed" in summary["errors"][0]


def test_owner_short_form_mapping_requires_reviewer_and_timestamp_for_decisions() -> None:
    mapper = _load_mapper_module()
    audit = _load_audit_module()
    canonical_csv = audit.render_review_csv(_packet())
    short_form_csv = _short_form_from_review_csv(canonical_csv, {"row-old-year": ("correct_reject", "")})

    mapped_csv, summary = mapper.apply_owner_short_form_return(
        canonical_csv_text=canonical_csv,
        short_form_csv_text=short_form_csv,
        reviewer="",
        reviewed_at="",
    )

    assert mapped_csv == ""
    assert summary["ok"] is False
    assert "reviewer is required" in summary["errors"][0]
    assert "reviewed_at is required" in summary["errors"][1]
