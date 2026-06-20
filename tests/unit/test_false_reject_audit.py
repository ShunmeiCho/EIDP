from __future__ import annotations

import importlib.util
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
