from __future__ import annotations

import importlib.util
import json
import sys
import zipfile
from pathlib import Path


def _load_module():
    script = Path(__file__).resolve().parents[2] / "scripts" / "summarize_stage6_rca.py"
    spec = importlib.util.spec_from_file_location("summarize_stage6_rca", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_stage6_archive(path: Path) -> Path:
    entries = {
        "BUILD_INFO.json": '{"git_commit": "abc"}\n',
        "logs/diagnostics-20260620-000000.txt": "diag\n",
        "data/output/last_run.json": json.dumps(
            {
                "current_fy": 2026,
                "target_pdf_auto_denominator_count": 5,
                "target_pdf_excel_ready_acquired_count": 2,
                "target_pdf_excel_ready_yield_pct": 40.0,
                "operator_reviewable_count": 4,
                "operator_reviewable_yield_pct": 80.0,
                "ship_gate_status": "below_gate",
                "discovery_stats": {
                    "crawled": 6,
                    "found": 5,
                    "downloaded": 2,
                },
                "ingest_stats": {
                    "processed": 2,
                    "departments_created": 7,
                    "yearly_upserted": 8,
                },
            },
            ensure_ascii=False,
        ),
        "data/output/target-year-discovery/20260620_000000-discovery-rejections.jsonl": "\n".join(
            [
                json.dumps({"school_id": 1, "reason": "target_fiscal_year_not_detected"}, ensure_ascii=False),
                json.dumps({"school_id": 1, "reason": "pre_filtered_non_target_hint"}, ensure_ascii=False),
                json.dumps({"school_id": 2, "reason": "pre_filtered_non_target_hint"}, ensure_ascii=False),
                json.dumps({"school_id": 3, "reason": "pdf_school_mismatch"}, ensure_ascii=False),
            ]
        )
        + "\n",
        "data/output/target-year-discovery/20260620_000000-discovery-rca-batch-plan.json": json.dumps(
            {
                "target_fiscal_year": 2026,
                "total_candidates": 3,
                "items": [
                    {
                        "bucket": "target_form_without_year_evidence",
                        "candidate_count": 2,
                        "actionable_candidate_count": 2,
                        "packet": {
                            "school_id": 1,
                            "school_name": "Alpha専門学校",
                            "prefecture": "東京都",
                            "official_index_url": "https://alpha.example/disclosure",
                            "registered_sites": [],
                        },
                    },
                    {
                        "bucket": "school_identity_mismatch",
                        "candidate_count": 1,
                        "actionable_candidate_count": 1,
                        "packet": {
                            "school_id": 3,
                            "school_name": "Gamma専門学校",
                            "prefecture": "埼玉県",
                            "official_index_url": "",
                            "registered_sites": [{"url": "https://gamma.example/", "confidence": 0.8}],
                        },
                    },
                ],
            },
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
                "size": len(
                    entries["data/output/target-year-discovery/20260620_000000-discovery-rejections.jsonl"]
                ),
            },
            {
                "label": "discovery_rca",
                "path": "data/output/target-year-discovery/20260620_000000-discovery-rca-batch-plan.json",
                "size": len(
                    entries[
                        "data/output/target-year-discovery/20260620_000000-discovery-rca-batch-plan.json"
                    ]
                ),
            },
        ],
        "missing_patterns": [],
    }
    with zipfile.ZipFile(path, "w") as zf:
        for name, content in entries.items():
            zf.writestr(name, content)
        zf.writestr("stage6-evidence-manifest.json", json.dumps(manifest))
    return path


def test_stage6_rca_summary_reads_zip_without_extracting(tmp_path: Path) -> None:
    module = _load_module()
    archive = _write_stage6_archive(tmp_path / "stage6-evidence.zip")

    result = module.summarize_stage6_rca_bundle(archive)

    assert result["ok"] is True
    assert result["strict_yield"] == {
        "target_fiscal_year": 2026,
        "denominator": 5,
        "excel_ready_acquired_count": 2,
        "excel_ready_yield_pct": 40.0,
        "required_yield_pct": 60.0,
        "ship_gate_status": "below_gate",
        "ship_gate_met": False,
        "conclusion": "BELOW_GATE",
        "operator_reviewable_count": 4,
        "operator_reviewable_yield_pct": 80.0,
    }
    assert result["run_counters"] == {
        "crawled": 6,
        "found": 5,
        "downloaded": 2,
        "processed": 2,
        "departments_created": 7,
        "yearly_upserted": 8,
    }
    assert result["rca_batch"]["item_count"] == 2
    assert result["rca_batch"]["root_total_candidates"] == 3
    assert result["rca_batch"]["candidate_rows"] == 3
    assert result["rca_batch"]["bucket_summary"][:2] == [
        {
            "bucket": "target_form_without_year_evidence",
            "schools": 1,
            "candidate_rows": 2,
            "actionable_candidate_rows": 2,
            "interpretation": (
                "Target-form-like candidates exist, but machine-verifiable target-year evidence is insufficient."
            ),
        },
        {
            "bucket": "school_identity_mismatch",
            "schools": 1,
            "candidate_rows": 1,
            "actionable_candidate_rows": 1,
            "interpretation": (
                "Candidate evidence may belong to a sibling or corporate site; school identity must be confirmed."
            ),
        },
    ]
    assert result["rejection_reasons"][:3] == [
        {"reason": "pre_filtered_non_target_hint", "count": 2},
        {"reason": "pdf_school_mismatch", "count": 1},
        {"reason": "target_fiscal_year_not_detected", "count": 1},
    ]
    assert result["school_queue"][0]["registered_source"] == "https://alpha.example/disclosure"
    assert result["school_queue"][1]["registered_source"] == "https://gamma.example/"


def test_stage6_rca_summary_cli_json_and_below_gate_exit(tmp_path: Path, capsys) -> None:
    module = _load_module()
    archive = _write_stage6_archive(tmp_path / "stage6-evidence.zip")

    assert module.main([str(archive), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["strict_yield"]["conclusion"] == "BELOW_GATE"

    assert module.main([str(archive), "--fail-on-below-gate"]) == 1
