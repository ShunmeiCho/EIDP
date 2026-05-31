"""Phase A fault-injection harness for ``run_pdf_discovery`` (G6/G9/G10).

Local, deterministic, ZERO real network. Each test wires a fake
``discover_pdfs_for_site`` / ``download_pdf`` over an in-memory SQLite session
and a ``tmp_path`` storage dir, then asserts the BATCH-level robustness
contract: one bad school or one bad PDF must NOT take down the whole batch.

This complements the existing single-handler unit tests in
``tests/unit/test_pdf_discovery.py`` by proving graceful degradation across a
multi-school batch (the systematic gap: tests/integration was empty).

Per-test contract (asserted incrementally as cases are added):
  - ``run_pdf_discovery`` does not raise for the whole batch
  - schools AFTER the faulty one are still processed
  - the faulty school's ``CrawlJob`` lands in its expected terminal status
    (never stuck at ``running``)
  - returned stats and evidence JSONL agree on what happened
  - no orphan files remain under the temp storage dir
"""

from __future__ import annotations

import json

import httpx
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from eidp.db.models import Base, CrawlJob, Document, School, SchoolSite
from eidp.scraper.pdf_discovery import (
    DiscoveryResult,
    PdfCandidate,
    run_pdf_discovery,
)

# Neutral target-form anchor (no school name): scores positive, never trips the
# candidate_school_mismatch gate. Reused from the B1 fixtures.
_TARGET_ANCHOR = "確認申請書 様式第2号 機関要件 修学支援"


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def _add_school(session: Session, school_id: int, *, url: str) -> None:
    session.add(
        School(
            id=school_id,
            school_name=f"テスト専門学校{school_id}",
            prefecture="東京都",
            corporation_name=f"学校法人テスト{school_id}",
            school_type="専門学校",
            status="active",
        )
    )
    session.add(SchoolSite(school_id=school_id, url=url, http_status=200))


def _target_candidate(url: str, page_url: str) -> PdfCandidate:
    return PdfCandidate(
        pdf_url=url,
        page_url=page_url,
        anchor_text=_TARGET_ANCHOR,
        score=5.0,
    )


def test_batch_continues_when_discovery_raises_for_one_school(monkeypatch, tmp_path) -> None:
    """RED #1 (G6/G10 isolation): one school's ``discover_pdfs_for_site`` raises
    an UNEXPECTED error (a network failure not wrapped as ``result.error``).

    The batch must isolate it: the next school still downloads, and the faulty
    school's CrawlJob must be finalized (not left stuck at 'running'). On the
    current code the exception propagates out of run_pdf_discovery (no per-site
    guard), so the whole batch dies -> RED.
    """

    session = _session()
    bad_id, good_id = 1, 2
    bad_page = "https://bad.example.ac.jp/disclosure/"
    good_page = "https://good.example.ac.jp/disclosure/"
    try:
        _add_school(session, bad_id, url=bad_page)
        _add_school(session, good_id, url=good_page)
        session.flush()

        def fake_discover(_client, school_id, _url, **_kwargs):
            if school_id == bad_id:
                raise httpx.ConnectError("simulated unexpected network failure")
            cand = _target_candidate(f"{good_page}target-kakunin.pdf", good_page)
            return DiscoveryResult(school_id=school_id, candidates=[cand], best=cand)

        def fake_download(_client, candidate, storage_dir, school_id, **_kwargs):
            out = tmp_path / f"{school_id}.pdf"
            out.write_bytes(b"%PDF ok")
            candidate.detected_fiscal_year = 2025
            candidate.year_evidence = "pdf_text"
            return str(out), f"hash-{school_id}", 3000, "target", None

        monkeypatch.setattr("eidp.scraper.pdf_discovery._is_safe_url", lambda _url: True)
        monkeypatch.setattr("eidp.scraper.pdf_discovery.discover_pdfs_for_site", fake_discover)
        monkeypatch.setattr("eidp.scraper.pdf_discovery.download_pdf", fake_download)

        evidence = tmp_path / "rejections.jsonl"
        # Must not raise: a single bad school may not abort the whole batch.
        stats = run_pdf_discovery(
            session,
            tmp_path,
            batch_size=10,
            rate_limit=0,
            evidence_path=evidence,
        )

        # The good school (processed AFTER the bad one) still produced a Document.
        good_docs = session.query(Document).filter(Document.school_id == good_id).count()
        assert good_docs == 1, "school after the faulty one must still be processed"

        # Returned stats lock the batch outcome: both schools crawled, the bad
        # one counted as failed with a discovery_error reason, the good one
        # downloaded.
        assert stats["crawled"] == 2
        assert stats["failed"] == 1
        assert stats["downloaded"] == 1
        assert stats["rejection_reason_discovery_error"] == 1

        # The bad school's CrawlJob is finalized to the exact 'failed' path the
        # result.error branch takes (not merely 'not running').
        bad_job = (
            session.query(CrawlJob)
            .filter(CrawlJob.school_id == bad_id)
            .order_by(CrawlJob.id.desc())
            .first()
        )
        assert bad_job is not None
        assert bad_job.status == "failed"
        assert bad_job.finished_at is not None

        # Evidence contract: the isolated failure is recorded as discovery_error
        # with the captured exception text, so a broken evidence write is caught.
        payloads = [
            json.loads(line)
            for line in evidence.read_text(encoding="utf-8").splitlines()
        ]
        discovery_errors = [
            p for p in payloads if p["reason"] == "discovery_error" and p["school_id"] == bad_id
        ]
        assert len(discovery_errors) == 1, "the faulty school must emit one discovery_error evidence row"
        extra = discovery_errors[0]["extra"]
        assert "ConnectError" in extra["error"]
        assert extra["error_code"] == "http_error"
    finally:
        session.close()
