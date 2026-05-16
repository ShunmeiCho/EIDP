from __future__ import annotations

import json
from pathlib import Path

import pytest

from eidp.pipeline.ingest_evidence import (
    IngestEvidenceRecorder,
    IngestRejection,
)


def test_recorder_writes_jsonl_per_record(tmp_path: Path) -> None:
    log = tmp_path / "ingest_rej.jsonl"
    with IngestEvidenceRecorder(log) as rec:
        rec.record(IngestRejection(
            doc_id=406,
            school_id=107,
            file_path="data/pdfs/107/abc.pdf",
            source_url="https://da-tokyo.ac.jp/x.pdf",
            pdf_type="target",
            reason="school_mismatch",
            detail={
                "parsed_school_name": "東京ダンス&アクターズ専門学校",
                "target_school_name": "東京ダンス・俳優＆舞台芸術専門学校",
                "alias_count": "0",
            },
        ))

    lines = log.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    row = json.loads(lines[0])
    assert row["doc_id"] == 406
    assert row["reason"] == "school_mismatch"
    assert row["detail"]["parsed_school_name"] == "東京ダンス&アクターズ専門学校"
    assert "timestamp" in row


def test_recorder_appends_to_existing(tmp_path: Path) -> None:
    log = tmp_path / "ingest_rej.jsonl"
    log.write_text(
        json.dumps({"doc_id": 1, "reason": "no_file"}) + "\n",
        encoding="utf-8",
    )
    with IngestEvidenceRecorder(log) as rec:
        rec.record(IngestRejection(doc_id=2, school_id=None, file_path=None,
                                   source_url=None, pdf_type=None, reason="non_target_pdf"))

    lines = log.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2


def test_recorder_none_path_is_silent_noop() -> None:
    with IngestEvidenceRecorder(None) as rec:
        rec.record(IngestRejection(doc_id=1, school_id=1, file_path=None,
                                   source_url=None, pdf_type=None, reason="x"))


def test_recorder_without_context_does_not_keep_file_handle(tmp_path: Path) -> None:
    log = tmp_path / "ingest_rej.jsonl"
    rec = IngestEvidenceRecorder(log)

    rec.record(IngestRejection(doc_id=1, school_id=1, file_path=None,
                               source_url=None, pdf_type=None, reason="x"))

    assert rec._fh is None
    assert log.read_text(encoding="utf-8").strip()


def test_recorder_context_closes_handle_when_caller_raises(tmp_path: Path) -> None:
    log = tmp_path / "ingest_rej.jsonl"
    rec = IngestEvidenceRecorder(log)

    with pytest.raises(RuntimeError, match="boom"):
        with rec:
            rec.record(IngestRejection(doc_id=1, school_id=1, file_path=None,
                                       source_url=None, pdf_type=None, reason="x"))
            assert rec._fh is not None
            raise RuntimeError("boom")

    assert rec._fh is None
    assert log.read_text(encoding="utf-8").strip()
