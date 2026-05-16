from __future__ import annotations

import json
from pathlib import Path

from eidp.scraper.discovery_evidence import EvidenceRecorder, RejectionEvidence


def test_recorder_writes_one_jsonl_line_per_record(tmp_path: Path) -> None:
    log_path = tmp_path / "rejections.jsonl"
    with EvidenceRecorder(log_path) as rec:
        rec.record(RejectionEvidence(
            school_id=42,
            pdf_url="https://x.example/foo.pdf",
            page_url="https://x.example/disclosure/",
            anchor_text="案内",
            pattern_type="direct",
            score=-3.0,
            reason="all_negative_score",
        ))
        rec.record(RejectionEvidence(
            school_id=42,
            pdf_url="https://x.example/bar.pdf",
            reason="classified_non_target",
            pdf_type="non_target",
        ))

    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    first = json.loads(lines[0])
    assert first["school_id"] == 42
    assert first["reason"] == "all_negative_score"
    assert first["pdf_url"] == "https://x.example/foo.pdf"
    assert "timestamp" in first
    second = json.loads(lines[1])
    assert second["pdf_type"] == "non_target"


def test_recorder_appends_to_existing_file(tmp_path: Path) -> None:
    log_path = tmp_path / "rejections.jsonl"
    log_path.write_text(
        json.dumps({"school_id": 1, "pdf_url": "old", "reason": "x"}) + "\n",
        encoding="utf-8",
    )
    with EvidenceRecorder(log_path) as rec:
        rec.record(RejectionEvidence(school_id=2, pdf_url="new", reason="y"))

    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["school_id"] == 1
    assert json.loads(lines[1])["school_id"] == 2


def test_recorder_path_none_is_silent_noop() -> None:
    with EvidenceRecorder(None) as rec:
        rec.record(RejectionEvidence(school_id=99, pdf_url="x", reason="r"))
        # No file, no exception


def test_recorder_without_context_does_not_keep_file_handle(tmp_path: Path) -> None:
    log_path = tmp_path / "rejections.jsonl"
    rec = EvidenceRecorder(log_path)

    rec.record(RejectionEvidence(school_id=1, pdf_url="x", reason="r"))

    assert rec._fh is None
    assert log_path.read_text(encoding="utf-8").strip()
