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
from eidp.scraper import pdf_discovery
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


def test_batch_continues_when_download_returns_http_error_for_one_school(monkeypatch, tmp_path) -> None:
    """RED #2 (G6/G10 isolation): one school's PDF download hits a 404/5xx at the
    HTTP layer, exercising the REAL ``download_pdf`` validation chain.

    For the bad school we leave ``download_pdf`` real and patch ``_safe_get`` to
    return ``httpx.Response(404)``: ``raise_for_status`` raises
    ``HTTPStatusError`` -> caught at the per-attempt ``except`` -> the single
    attempt URL is exhausted -> the for/else returns
    ``(None, None, 0, "unknown", "http_error:HTTPStatusError")``. The batch must
    record that as evidence, finalize the bad school's CrawlJob as 'failed' (not
    dup/cross/target_year), and the good school AFTER it must still download.
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
            page = bad_page if school_id == bad_id else good_page
            cand = _target_candidate(f"{page}target-kakunin.pdf", page)
            return DiscoveryResult(school_id=school_id, candidates=[cand], best=cand)

        # Capture the REAL download_pdf so the bad school runs the genuine
        # validation chain (resp.raise_for_status -> HTTPStatusError); the good
        # school short-circuits to a deterministic stub to avoid pdfplumber noise.
        real_download = pdf_discovery.download_pdf

        def fake_download(client, candidate, storage_dir, school_id, **kwargs):
            if school_id == good_id:
                out = tmp_path / f"{school_id}.pdf"
                out.write_bytes(b"%PDF ok")
                candidate.detected_fiscal_year = 2025
                candidate.year_evidence = "pdf_text"
                return str(out), f"hash-{school_id}", 3000, "target", None
            return real_download(client, candidate, storage_dir, school_id, **kwargs)

        def fake_safe_get(_client, url, **_kwargs):
            # Only the bad school reaches _safe_get; request must be set or
            # raise_for_status raises RuntimeError instead of HTTPStatusError.
            return httpx.Response(404, request=httpx.Request("GET", url))

        monkeypatch.setattr("eidp.scraper.pdf_discovery._is_safe_url", lambda _url: True)
        monkeypatch.setattr("eidp.scraper.pdf_discovery.discover_pdfs_for_site", fake_discover)
        monkeypatch.setattr("eidp.scraper.pdf_discovery.download_pdf", fake_download)
        monkeypatch.setattr("eidp.scraper.pdf_discovery._safe_get", fake_safe_get)

        evidence = tmp_path / "rejections.jsonl"
        # Must not raise: a single bad download may not abort the whole batch.
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

        # Returned stats lock the batch outcome: both crawled, the bad one failed
        # via the real http_error chain, the good one downloaded.
        assert stats["crawled"] == 2
        assert stats["failed"] == 1
        assert stats["downloaded"] == 1
        # Reason + stat key are empirically verified: ":" in
        # "http_error:HTTPStatusError" normalizes to "_" and lowercases.
        assert stats["rejection_reason_http_error_httpstatuserror"] == 1

        # The bad school's CrawlJob is finalized to the terminal 'failed' path
        # (not dup/cross/target_year) -- never left stuck at 'running'.
        bad_job = (
            session.query(CrawlJob)
            .filter(CrawlJob.school_id == bad_id)
            .order_by(CrawlJob.id.desc())
            .first()
        )
        assert bad_job is not None
        assert bad_job.status == "failed"
        assert bad_job.finished_at is not None

        # Stats and evidence agree: exactly one http_error row for the bad school
        # classified as "unknown" pdf_type.
        payloads = [
            json.loads(line)
            for line in evidence.read_text(encoding="utf-8").splitlines()
        ]
        http_errors = [
            p
            for p in payloads
            if p["reason"] == "http_error:HTTPStatusError" and p["school_id"] == bad_id
        ]
        assert len(http_errors) == 1, "the faulty school must emit one http_error evidence row"
        assert http_errors[0]["pdf_type"] == "unknown"

        # No orphan PDF for the rejected http_error candidate: download_pdf
        # returns at the for/else before any file is written, so the bad
        # school's storage dir holds no .pdf (and likely never gets created).
        bad_dir = tmp_path / str(bad_id)
        assert (not bad_dir.exists()) or list(bad_dir.rglob("*.pdf")) == []
    finally:
        session.close()


def test_batch_isolates_redirect_loop_during_download(monkeypatch, tmp_path) -> None:
    """RED #3 (G6/G10 isolation): one school's download hits a redirect LOOP, so
    the REAL ``_safe_get`` raises ``httpx.HTTPStatusError`` ("Redirect loop
    detected") -- the production behavior its own docstring documents.

    Unlike case #2 (404 -> ``raise_for_status``), here ``_safe_get`` raises the
    redirect-loop error itself, and BOTH schools run the genuine ``download_pdf``
    (no ``download_pdf`` mock): the bad school's loop is caught at the per-attempt
    ``except (httpx.HTTPError, httpx.InvalidURL)`` (HTTPStatusError is a subclass)
    -> ``last_reject_reason="http_error:HTTPStatusError"`` -> for/else returns
    ``(None, None, 0, "unknown", "http_error:HTTPStatusError")`` with NO file
    written. The good school AFTER it must still download a real Document.
    """

    session = _session()
    bad_id, good_id = 1, 2
    bad_page = "https://bad.example.ac.jp/disclosure/"
    good_page = "https://good.example.ac.jp/disclosure/"
    try:
        _add_school(session, bad_id, url=bad_page)
        _add_school(session, good_id, url=good_page)
        session.flush()
        bad_pdf = f"{bad_page}target-kakunin.pdf"
        good_pdf = f"{good_page}target-kakunin.pdf"

        def fake_discover(_client, school_id, _url, **_kwargs):
            cand = _target_candidate(
                bad_pdf if school_id == bad_id else good_pdf,
                bad_page if school_id == bad_id else good_page,
            )
            return DiscoveryResult(school_id=school_id, candidates=[cand], best=cand)

        def fake_safe_get(_client, url, **_kwargs):
            # Bad school: mirror exactly what the real _safe_get raises on a
            # redirect loop (302 whose Location points back to itself).
            if url.startswith(bad_page):
                req = httpx.Request("GET", url)
                resp = httpx.Response(302, headers={"location": url}, request=req)
                raise httpx.HTTPStatusError("Redirect loop detected", request=req, response=resp)
            # Good school: a valid >=1000-byte PDF body so the REAL download_pdf
            # passes the magic-byte and size gates.
            return httpx.Response(200, content=b"%PDF-" + b"a" * 2000, request=httpx.Request("GET", url))

        monkeypatch.setattr("eidp.scraper.pdf_discovery._is_safe_url", lambda _url: True)
        monkeypatch.setattr("eidp.scraper.pdf_discovery.discover_pdfs_for_site", fake_discover)
        monkeypatch.setattr("eidp.scraper.pdf_discovery._safe_get", fake_safe_get)
        # The good school runs the REAL download_pdf; pin the classify seams so
        # the synthetic body (not a real PDF) is deterministically accepted as a
        # target doc instead of depending on pdfplumber's behavior.
        monkeypatch.setattr(
            "eidp.scraper.pdf_discovery._extract_pdf_sample_text",
            lambda content: "確認申請書 様式第2号 機関要件",
        )
        monkeypatch.setattr("eidp.scraper.pdf_discovery._classify_pdf_sample_text", lambda text: "target")
        monkeypatch.setattr("eidp.scraper.pdf_discovery._extract_pdf_sample_school_name", lambda text: "")
        monkeypatch.setattr(
            "eidp.scraper.pdf_discovery._detect_fiscal_year_from_text",
            lambda text, max_fiscal_year=None: None,
        )

        evidence = tmp_path / "rejections.jsonl"
        # Must not raise: a single redirect-loop download may not abort the batch.
        stats = run_pdf_discovery(
            session,
            tmp_path,
            batch_size=10,
            rate_limit=0,
            evidence_path=evidence,
        )

        # The good school (processed AFTER the redirect-loop school) still
        # produced a Document -- non-strict run accepts it with no FY gate.
        good_docs = session.query(Document).filter(Document.school_id == good_id).count()
        assert good_docs == 1, "school after the redirect-loop school must still download"

        # Returned stats lock the batch outcome: both crawled, the bad one failed
        # via the real redirect-loop http_error chain, the good one downloaded.
        assert stats["crawled"] == 2
        assert stats["failed"] == 1
        assert stats["downloaded"] == 1
        # Reason + stat key empirically verified: the injected exception is
        # httpx.HTTPStatusError, so last_reject_reason = "http_error:HTTPStatusError"
        # and _rejection_reason_stat_key normalizes ":" -> "_" and lowercases.
        assert stats["rejection_reason_http_error_httpstatuserror"] == 1

        # The bad school's CrawlJob is finalized to the terminal 'failed' path
        # (not dup/cross/target_year) -- never left stuck at 'running'.
        bad_job = (
            session.query(CrawlJob)
            .filter(CrawlJob.school_id == bad_id)
            .order_by(CrawlJob.id.desc())
            .first()
        )
        assert bad_job is not None
        assert bad_job.status == "failed"
        assert bad_job.finished_at is not None
        assert "download failed" in (bad_job.error_message or "")

        # Stats and evidence agree: exactly one http_error row for the bad school
        # classified as "unknown" pdf_type.
        payloads = [
            json.loads(line)
            for line in evidence.read_text(encoding="utf-8").splitlines()
        ]
        redirect_rows = [
            p
            for p in payloads
            if p["school_id"] == bad_id and p["reason"] == "http_error:HTTPStatusError"
        ]
        assert len(redirect_rows) == 1, (
            "redirect-loop school must emit exactly one http_error:HTTPStatusError evidence row"
        )
        assert redirect_rows[0]["pdf_type"] == "unknown"

        # No orphan PDF for the redirect-loop candidate: download_pdf returns at
        # the for/else before any file is written, so the bad school's storage
        # dir holds no .pdf (and likely never gets created).
        bad_dir = tmp_path / str(bad_id)
        orphans = list(bad_dir.glob("*.pdf")) if bad_dir.exists() else []
        assert orphans == [], "a redirect-loop (failed download) must leave no orphan PDF on disk"
    finally:
        session.close()


# HTML body served as a PDF: >=1000 bytes (clears the too_small gate at line
# 3425) but the first 5 bytes are not b"%PDF-" (trips the magic-byte gate at
# line 3430). The 1100-byte filler guarantees the magic check -- not too_small --
# is the rejection that fires.
_HTML_AS_PDF = (
    b"<!DOCTYPE html><html><head><title>x</title></head><body>"
    + b"a" * 1100
    + b"</body></html>"
)


def test_batch_continues_when_one_pdf_is_html_body(monkeypatch, tmp_path) -> None:
    """RED #4 (G6/G10 isolation): one school's URL serves an HTML body dressed up
    as a PDF (magic-byte mismatch), exercising the REAL ``download_pdf`` content
    validation.

    For the bad school we leave ``download_pdf`` real and patch ``_safe_get`` to
    return ``httpx.Response(200, content=<HTML body >=1000 bytes>)``: the body
    clears the size gate but ``content[:5] != b"%PDF-"`` ->
    ``last_reject_reason="not_pdf_magic"`` -> the single attempt URL is exhausted
    -> the for/else returns ``(None, None, 0, "unknown", "not_pdf_magic")`` with
    NO file written. An HTML body served as PDF must NEVER become a Document, the
    bad school's CrawlJob must finalize as 'failed' (not dup/cross/target_year),
    and the good school AFTER it must still download a real Document.
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
            page = bad_page if school_id == bad_id else good_page
            cand = _target_candidate(f"{page}target-kakunin.pdf", page)
            return DiscoveryResult(school_id=school_id, candidates=[cand], best=cand)

        # Capture the REAL download_pdf BEFORE patching so the bad school runs the
        # genuine validation chain and the magic-byte check at pdf_discovery.py
        # line 3430 fires. Referencing the name after patching would recurse.
        real_download = pdf_discovery.download_pdf

        def fake_download_good(client, candidate, storage_dir, school_id, **kwargs):
            out = tmp_path / f"{school_id}.pdf"
            out.write_bytes(b"%PDF ok")
            candidate.detected_fiscal_year = 2025
            candidate.year_evidence = "pdf_text"
            return str(out), f"hash-{school_id}", 3000, "target", None

        def routed_download(client, candidate, storage_dir, school_id, **kwargs):
            if school_id == bad_id:
                return real_download(client, candidate, storage_dir, school_id, **kwargs)
            return fake_download_good(client, candidate, storage_dir, school_id, **kwargs)

        def fake_safe_get(_client, url, **_kwargs):
            # Only the bad school reaches _safe_get (the good school is stubbed at
            # download_pdf). Serve an HTML body that clears the size gate but
            # fails the %PDF- magic check.
            return httpx.Response(200, content=_HTML_AS_PDF, request=httpx.Request("GET", url))

        monkeypatch.setattr("eidp.scraper.pdf_discovery._is_safe_url", lambda _url: True)
        monkeypatch.setattr("eidp.scraper.pdf_discovery.discover_pdfs_for_site", fake_discover)
        monkeypatch.setattr("eidp.scraper.pdf_discovery.download_pdf", routed_download)
        monkeypatch.setattr("eidp.scraper.pdf_discovery._safe_get", fake_safe_get)

        evidence = tmp_path / "rejections.jsonl"
        # Must not raise: a single HTML-as-PDF download may not abort the batch.
        stats = run_pdf_discovery(
            session,
            tmp_path,
            batch_size=10,
            rate_limit=0,
            evidence_path=evidence,
        )

        # The good school (processed AFTER the bad one) still produced a Document.
        good_docs = session.query(Document).filter(Document.school_id == good_id).count()
        assert good_docs == 1, "school after the HTML-as-PDF one must still be processed"

        # An HTML body served as PDF must never become a Document.
        assert (
            session.query(Document).filter(Document.school_id == bad_id).count() == 0
        ), "an HTML body served as PDF must never become a Document"

        # Returned stats lock the batch outcome: both crawled, the bad one failed
        # via the real not_pdf_magic chain, the good one downloaded.
        assert stats["crawled"] == 2
        assert stats["found"] == 2
        assert stats["failed"] == 1
        assert stats["downloaded"] == 1
        # Reason + stat key empirically verified: "not_pdf_magic" has no ":" so
        # it normalizes unchanged (lowercased) to rejection_reason_not_pdf_magic.
        assert stats["rejection_reason_not_pdf_magic"] == 1

        # The bad school's CrawlJob is finalized to the terminal 'failed' path
        # (not dup/cross/target_year) -- never left stuck at 'running'.
        bad_job = (
            session.query(CrawlJob)
            .filter(CrawlJob.school_id == bad_id)
            .order_by(CrawlJob.id.desc())
            .first()
        )
        assert bad_job is not None
        assert bad_job.status == "failed"
        assert bad_job.finished_at is not None

        # The good school's CrawlJob is a finalized success.
        good_job = (
            session.query(CrawlJob)
            .filter(CrawlJob.school_id == good_id)
            .order_by(CrawlJob.id.desc())
            .first()
        )
        assert good_job is not None
        assert good_job.status == "success"
        assert good_job.finished_at is not None

        # Stats and evidence agree: exactly one not_pdf_magic row for the bad
        # school classified as "unknown" pdf_type, and the good school records
        # its accepted download.
        payloads = [
            json.loads(line)
            for line in evidence.read_text(encoding="utf-8").splitlines()
        ]
        magic_rows = [
            p
            for p in payloads
            if p["reason"] == "not_pdf_magic" and p["school_id"] == bad_id
        ]
        assert len(magic_rows) == 1, (
            "the HTML-as-PDF school must emit exactly one not_pdf_magic evidence row"
        )
        assert magic_rows[0]["pdf_type"] == "unknown"
        assert any(
            p["reason"] == "accepted_downloaded" and p["school_id"] == good_id
            for p in payloads
        ), "good school evidence must record the accepted download"

        # No orphan PDF for the rejected HTML-as-PDF candidate: download_pdf
        # returns at the for/else before any file is written, so the bad school's
        # storage dir is never created and the only on-disk files are the
        # evidence log and the good school's stub PDF.
        assert not (tmp_path / str(bad_id)).exists(), (
            "rejected HTML-as-PDF candidate must leave no per-school storage dir / orphan file"
        )
        orphans = [
            p
            for p in tmp_path.rglob("*")
            if p.is_file()
            and p.name != "rejections.jsonl"
            and p != (tmp_path / f"{good_id}.pdf")
        ]
        assert orphans == [], f"no orphan PDF for the rejected candidate: {orphans}"
    finally:
        session.close()


def test_batch_continues_when_pdf_body_too_small(monkeypatch, tmp_path) -> None:
    """RED #5 (G6/G10 isolation): one school's URL serves a truncated PDF body
    (valid %PDF- magic but < 1000 bytes), exercising the REAL ``download_pdf``
    size validation.

    For the bad school we leave ``download_pdf`` real and patch ``_safe_get`` to
    return ``httpx.Response(200, content=b"%PDF-1.4 truncated")`` (18 bytes):
    ``raise_for_status`` passes (200), the body clears the magic-byte gate but
    ``len(content) < 1000`` (pdf_discovery.py line 3425) ->
    ``last_reject_reason="too_small"`` -> the single attempt URL is exhausted ->
    the for/else returns ``(None, None, 0, "unknown", "too_small")`` BEFORE any
    file is written. A truncated body must NEVER become a Document, the bad
    school's CrawlJob must finalize as 'failed' (not dup/cross/target_year), and
    the good school AFTER it must still download a real Document.

    The bad school's site URL ends in ``.pdf`` so ``_download_attempt_urls``
    yields a single canonical attempt -> exactly one ``too_small`` evidence row.
    """

    session = _session()
    bad_id, good_id = 1, 2
    # Direct .pdf site URL: deterministic candidate pdf_url, single download
    # attempt, so the truncated body is rejected with exactly one too_small row.
    bad_page = "https://bad.example.ac.jp/disclosure/doc.pdf"
    good_page = "https://good.example.ac.jp/disclosure/"
    try:
        _add_school(session, bad_id, url=bad_page)
        _add_school(session, good_id, url=good_page)
        session.flush()

        def fake_discover(_client, school_id, _url, **_kwargs):
            if school_id == bad_id:
                cand = _target_candidate(bad_page, bad_page)
            else:
                cand = _target_candidate(f"{good_page}target.pdf", good_page)
            return DiscoveryResult(school_id=school_id, candidates=[cand], best=cand)

        # Capture the REAL download_pdf BEFORE patching so the bad school runs the
        # genuine validation chain and the size check at pdf_discovery.py line
        # 3425 fires. Referencing the name after patching would recurse.
        real_download = pdf_discovery.download_pdf

        def fake_download_good(client, candidate, storage_dir, school_id, **kwargs):
            out = tmp_path / f"{school_id}.pdf"
            out.write_bytes(b"%PDF ok")
            candidate.detected_fiscal_year = 2025
            candidate.year_evidence = "pdf_text"
            return str(out), f"hash-{school_id}", 3000, "target", None

        def routed_download(client, candidate, storage_dir, school_id, **kwargs):
            if school_id == bad_id:
                return real_download(client, candidate, storage_dir, school_id, **kwargs)
            return fake_download_good(client, candidate, storage_dir, school_id, **kwargs)

        def fake_safe_get(_client, url, **_kwargs):
            # Only the bad school reaches _safe_get (the good school is stubbed at
            # download_pdf). Serve a truncated 18-byte body: valid %PDF- magic but
            # well under the 1000-byte minimum -> too_small.
            return httpx.Response(
                200,
                content=b"%PDF-1.4 truncated",
                request=httpx.Request("GET", url),
            )

        monkeypatch.setattr("eidp.scraper.pdf_discovery._is_safe_url", lambda _url: True)
        monkeypatch.setattr("eidp.scraper.pdf_discovery.discover_pdfs_for_site", fake_discover)
        monkeypatch.setattr("eidp.scraper.pdf_discovery.download_pdf", routed_download)
        monkeypatch.setattr("eidp.scraper.pdf_discovery._safe_get", fake_safe_get)

        evidence = tmp_path / "rejections.jsonl"
        # Must not raise: a single truncated-body download may not abort the batch.
        stats = run_pdf_discovery(
            session,
            tmp_path,
            batch_size=10,
            rate_limit=0,
            evidence_path=evidence,
        )

        # The good school (processed AFTER the bad one) still produced a Document.
        good_docs = session.query(Document).filter(Document.school_id == good_id).count()
        assert good_docs == 1, "school after the truncated-body one must still be processed"

        # A truncated body must never become a Document (no silent accept).
        assert (
            session.query(Document).filter(Document.school_id == bad_id).count() == 0
        ), "a truncated PDF body must never become a Document"

        # Returned stats lock the batch outcome: both crawled, the bad one failed
        # via the real too_small chain, the good one downloaded.
        assert stats["crawled"] == 2
        assert stats["downloaded"] == 1
        assert stats["failed"] == 1
        # Reason + stat key empirically verified: "too_small" has no ":" so it
        # normalizes unchanged (lowercased) to rejection_reason_too_small.
        assert stats["rejection_reason_too_small"] == 1

        # The bad school's CrawlJob is finalized to the terminal 'failed' path
        # (not dup/cross/target_year) -- never left stuck at 'running'.
        bad_job = (
            session.query(CrawlJob)
            .filter(CrawlJob.school_id == bad_id)
            .order_by(CrawlJob.id.desc())
            .first()
        )
        assert bad_job is not None
        assert bad_job.status == "failed"
        assert bad_job.finished_at is not None

        # Stats and evidence agree: exactly one too_small row for the bad school
        # classified as "unknown" pdf_type (download_pdf returns pdf_type=
        # "unknown" on the for/else too_small path, line 3437).
        payloads = [
            json.loads(line)
            for line in evidence.read_text(encoding="utf-8").splitlines()
        ]
        too_small_rows = [
            p
            for p in payloads
            if p["reason"] == "too_small" and p["school_id"] == bad_id
        ]
        assert len(too_small_rows) == 1, (
            "the truncated-body school must emit exactly one too_small evidence row"
        )
        assert too_small_rows[0]["pdf_type"] == "unknown"

        # No orphan PDF for the rejected too_small candidate: download_pdf returns
        # at the for/else before any file is written, so the bad school's storage
        # dir holds no .pdf (and is never created).
        bad_dir = tmp_path / str(bad_id)
        assert (not bad_dir.exists()) or not any(bad_dir.glob("*.pdf")), (
            "a truncated body (failed download) must leave no orphan PDF on disk"
        )
    finally:
        session.close()


def test_image_only_pdf_is_queued_with_image_routing(monkeypatch, tmp_path) -> None:
    """REGRESSION-LOCK #6 (G11 image routing): one school's PDF has no text layer
    (an image-only scan), so ``download_pdf`` classifies it ``image_only``. Unlike
    the rejection cases above, an ``image_only`` PDF is ACCEPTED into the queue
    for OCR-stage handling, not rejected -- the discovery-level half of the G11
    ``image_pending`` contract.

    The non-strict run inserts a Document with ``content_type="image"`` /
    ``pdf_type="image_only"`` (pdf_discovery.py:4161 maps image_only ->
    content_type=image) and counts it as ``downloaded`` (NOT a rejection: there is
    no ``rejection_reason_*`` key for ``accepted_downloaded``). The good school
    AFTER it must still download a normal target Document, and BOTH CrawlJobs must
    finalize to ``success``.

    This mirrors case #1's mock-download seam (the CASE HINT-authorized fallback):
    a global ``download_pdf`` mock cannot coexist with the real ``download_pdf``
    for one school in the same batch, and there is no pure-python PDF builder to
    synthesize a clean text-extractable target body for the good school, so the
    deterministic, low-noise choice is to mock ``download_pdf`` for both. Each
    mock writes a real >=1KB body under ``tmp_path/<school_id>/`` so the
    accepted-file-kept-on-disk assert is meaningful.
    """

    session = _session()
    img_id, good_id = 1, 2
    img_page = "https://img.example.ac.jp/disclosure/"
    good_page = "https://good.example.ac.jp/disclosure/"
    try:
        _add_school(session, img_id, url=img_page)
        _add_school(session, good_id, url=good_page)
        session.flush()

        def fake_discover(_client, school_id, _url, **_kwargs):
            page = img_page if school_id == img_id else good_page
            cand = _target_candidate(f"{page}x.pdf", page)
            return DiscoveryResult(school_id=school_id, candidates=[cand], best=cand)

        def fake_download(_client, candidate, storage_dir, school_id, **_kwargs):
            # Real file under tmp_path/<school_id>/ so the kept-on-disk assert is
            # meaningful (only rejected candidates get unlinked).
            school_dir = tmp_path / str(school_id)
            school_dir.mkdir(parents=True, exist_ok=True)
            out = school_dir / "doc.pdf"
            if school_id == img_id:
                # image-only PDF: no text layer -> OCR queue semantics (G11). FY
                # stays None (no detected_fiscal_year) -> non-strict insert keeps
                # fiscal_year/is_current_year None.
                out.write_bytes(b"%PDF-1.4 image-only scan, no text layer " + b"0" * 1100)
                return str(out), f"imghash-{school_id}", 5000, "image_only", None
            out.write_bytes(b"%PDF-1.4 target form " + b"0" * 1100)
            candidate.detected_fiscal_year = 2025
            candidate.year_evidence = "pdf_text"
            return str(out), f"tgt-{school_id}", 3000, "target", None

        monkeypatch.setattr("eidp.scraper.pdf_discovery._is_safe_url", lambda _url: True)
        monkeypatch.setattr("eidp.scraper.pdf_discovery.discover_pdfs_for_site", fake_discover)
        monkeypatch.setattr("eidp.scraper.pdf_discovery.download_pdf", fake_download)

        evidence = tmp_path / "rejections.jsonl"
        # Must not raise: the image_only school is accepted, the batch continues.
        stats = run_pdf_discovery(
            session,
            tmp_path,
            batch_size=10,
            rate_limit=0,
            evidence_path=evidence,
        )

        # G11 image routing at discovery level: image_only PDF is accepted into
        # the queue, batch continues. Both crawled and found; nothing failed; both
        # downloaded (image_only is NOT rejected).
        assert stats["crawled"] == 2
        assert stats["found"] == 2
        assert stats["failed"] == 0
        assert stats["downloaded"] == 2

        # The image_only school produced a Document routed for image/OCR semantics.
        img_doc = session.query(Document).filter(Document.school_id == img_id).one()
        assert img_doc.content_type == "image"  # pdf_discovery.py:4161 image_only -> image
        assert img_doc.pdf_type == "image_only"

        # The good school AFTER the image one still produced a normal target
        # Document (batch did not abort). Keep this minimal to avoid coupling to
        # the rolling target fiscal year -- the case is about image routing, not FY.
        good_doc = session.query(Document).filter(Document.school_id == good_id).one()
        assert good_doc.content_type == "text"
        assert good_doc.pdf_type == "target"

        # Both CrawlJobs finalized to success (never stuck at 'running').
        img_job = (
            session.query(CrawlJob)
            .filter(CrawlJob.school_id == img_id)
            .order_by(CrawlJob.id.desc())
            .first()
        )
        assert img_job is not None and img_job.status == "success" and img_job.finished_at is not None
        good_job = (
            session.query(CrawlJob)
            .filter(CrawlJob.school_id == good_id)
            .order_by(CrawlJob.id.desc())
            .first()
        )
        assert good_job is not None and good_job.status == "success" and good_job.finished_at is not None

        # Stats and evidence JSONL agree: the image_only download is recorded as
        # accepted_downloaded with pdf_type=image_only (the success-path evidence
        # row at pdf_discovery.py:4236-4252 -- NOT a rejection reason).
        payloads = [
            json.loads(line)
            for line in evidence.read_text(encoding="utf-8").splitlines()
        ]
        img_accepted = [
            p for p in payloads if p["school_id"] == img_id and p["reason"] == "accepted_downloaded"
        ]
        assert len(img_accepted) == 1
        assert img_accepted[0]["pdf_type"] == "image_only"

        # Accepted image_only file is KEPT on disk (only rejected candidates are
        # unlinked) -- the discovery-level half of the OCR queue contract.
        img_dir = tmp_path / str(img_id)
        assert any(img_dir.glob("*.pdf")), "accepted image_only PDF must remain on disk"
    finally:
        session.close()


# A wrong school name whose stripped ``_school_link_label`` is >=4 chars and
# distinct from the bad school's target label. The target ``テスト専門学校1``
# strips ``専門学校`` to label ``テスト1`` (len 4); ``別の専門学校九州`` strips to
# ``別の九州`` (len 4, distinct), so _candidate_pdf_mentions_different_school
# (pdf_discovery.py:1405) returns True. Empirically verified before writing.
_WRONG_SCHOOL_NAME = "別の専門学校九州"


def test_batch_skips_pdf_naming_a_different_school(monkeypatch, tmp_path) -> None:
    """REGRESSION-LOCK #7 (G3/G10 isolation): one school's downloaded PDF is a
    valid 'target' file on disk, but its BODY names a DIFFERENT school. The
    batch-loop gate ``_candidate_pdf_mentions_different_school`` (pdf_discovery.py
    :4079) must trip True, unlink the file (line 4080), bump ``skipped``, and emit
    a ``pdf_school_mismatch`` evidence row -- the bad PDF must NEVER become a
    Document, and the control good school AFTER it must still download.

    The fault is injected at ``download_pdf``'s RETURN: a clean 'target' PDF whose
    ``candidate.detected_school_name`` is the wrong school. The pre-download
    URL/anchor gate ``_candidate_mentions_different_school`` (line 3858) inspects
    only anchor_text + pdf_url (the neutral _TARGET_ANCHOR + a clean URL), so the
    candidate survives to the download loop; the prerank classify loop (line 3882)
    needs len(priority) >= 2 and a single candidate cannot reach it, so no network
    GET fires. This mirrors case #1's mock-download seam.

    Costs ~0.5s real time: the pdf_school_mismatch branch has a time.sleep(0.5)
    at line 4096 that is NOT gated by rate_limit (matches the duplicate/mismatch
    sleeps already in the loop) -- acceptable, not suppressed.
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
            page = bad_page if school_id == bad_id else good_page
            cand = _target_candidate(f"{page}x-kakunin.pdf", page)
            return DiscoveryResult(school_id=school_id, candidates=[cand], best=cand)

        def fake_download(_client, candidate, storage_dir, school_id, **_kwargs):
            # Write a real 'target' PDF on disk under tmp_path/<school_id>/. For
            # the bad school only, set the body school name to the WRONG school so
            # the batch-loop mismatch gate trips and unlinks the file.
            school_dir = tmp_path / str(school_id)
            school_dir.mkdir(parents=True, exist_ok=True)
            out = school_dir / "x.pdf"
            out.write_bytes(b"%PDF-1.4 body")
            candidate.detected_fiscal_year = 2025
            candidate.year_evidence = "pdf_text"
            if school_id == bad_id:
                candidate.detected_school_name = _WRONG_SCHOOL_NAME
            return str(out), f"hash-{school_id}", 3000, "target", None

        monkeypatch.setattr("eidp.scraper.pdf_discovery._is_safe_url", lambda _url: True)
        monkeypatch.setattr("eidp.scraper.pdf_discovery.discover_pdfs_for_site", fake_discover)
        monkeypatch.setattr("eidp.scraper.pdf_discovery.download_pdf", fake_download)

        evidence = tmp_path / "rejections.jsonl"
        # Must not raise: a single wrong-school PDF may not abort the whole batch.
        stats = run_pdf_discovery(
            session,
            tmp_path,
            batch_size=10,
            rate_limit=0,
            evidence_path=evidence,
        )

        # Both schools crawled and found a candidate; the bad one is skipped (its
        # file unlinked + failed terminal status), the good control downloads.
        assert stats["crawled"] == 2
        assert stats["found"] == 2
        assert stats["downloaded"] == 1
        assert stats["failed"] == 1
        assert stats["skipped"] == 1
        # Reason + stat key empirically verified: "pdf_school_mismatch" has no ":"
        # so it normalizes unchanged (lowercased) to the stat key below.
        assert stats["rejection_reason_pdf_school_mismatch"] == 1

        # A PDF whose body names a different school must NEVER become a Document
        # for the faulty school (no silent accept).
        assert (
            session.query(Document).filter(Document.school_id == bad_id).count() == 0
        ), "a PDF naming a different school must never become a Document"
        # The control good school (processed AFTER the faulty one) still downloads.
        assert (
            session.query(Document).filter(Document.school_id == good_id).count() == 1
        ), "school after the wrong-school one must still be processed"

        # The bad school's CrawlJob is finalized to the terminal 'failed' path
        # (the generic else branch at line 4279) -- never stuck at 'running'.
        bad_job = (
            session.query(CrawlJob)
            .filter(CrawlJob.school_id == bad_id)
            .order_by(CrawlJob.id.desc())
            .first()
        )
        assert bad_job is not None
        assert bad_job.status == "failed"
        assert bad_job.finished_at is not None

        # The control good school's CrawlJob is a finalized success.
        good_job = (
            session.query(CrawlJob)
            .filter(CrawlJob.school_id == good_id)
            .order_by(CrawlJob.id.desc())
            .first()
        )
        assert good_job is not None
        assert good_job.status == "success"
        assert good_job.finished_at is not None

        # No orphan PDF: the rejected candidate's file is unlinked (line 4080).
        # The per-school dir itself remains (empty), so assert the file is gone.
        assert not (tmp_path / str(bad_id) / "x.pdf").exists(), (
            "rejected wrong-school candidate file must be unlinked, no orphan PDF"
        )

        # Stats and evidence agree: exactly one pdf_school_mismatch row for the bad
        # school, carrying the parsed (wrong) and target (real) school names. The
        # bad PDF must never be recorded as accepted_downloaded.
        payloads = [
            json.loads(line)
            for line in evidence.read_text(encoding="utf-8").splitlines()
        ]
        mismatches = [
            p
            for p in payloads
            if p["reason"] == "pdf_school_mismatch" and p["school_id"] == bad_id
        ]
        assert len(mismatches) == 1, (
            "the wrong-school school must emit exactly one pdf_school_mismatch row"
        )
        assert mismatches[0]["extra"]["parsed_school_name"] == _WRONG_SCHOOL_NAME
        assert mismatches[0]["extra"]["target_school_name"] == f"テスト専門学校{bad_id}"
        assert not any(
            p["reason"] == "accepted_downloaded" and p["school_id"] == bad_id
            for p in payloads
        ), "the wrong-school PDF must never be recorded as accepted_downloaded"
    finally:
        session.close()


# 64 hex chars: file_hash is String(64) and the uq_document_file_hash index is
# UNIQUE on file_hash alone, so a cross-school collision is a real DB violation.
_DUP_HASH = "deadbeef" * 8


class _RaceProxy:
    """One-shot delegating proxy over a real ``session.query(Document)`` chain.

    Forces the FIRST duplicate-hash pre-check ``.first()`` (pdf_discovery.py
    :4100-4104) to MISS (return None) so the ``begin_nested()`` INSERT at line
    4189 trips the real UNIQUE IntegrityError against a pre-seeded row -- the
    exact race the code's IntegrityError branch (4192-4234) defends against.
    After the first miss it disarms, so ``.filter(...)`` returns the real chain
    and the ``no_autoflush`` re-query at 4197-4202 finds the existing row,
    selecting the existing-found reason at 4203-4213 (not the
    duplicate_hash_integrity_error fallback).
    """

    def __init__(self, query, race):  # type: ignore[no-untyped-def]
        self._query = query
        self._race = race

    def filter(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        chain = self._query.filter(*args, **kwargs)
        if self._race["on"]:
            self._race["on"] = False
            return _RaceFirstNone(chain)
        return chain

    def __getattr__(self, name):  # type: ignore[no-untyped-def]
        return getattr(self._query, name)


class _RaceFirstNone:
    """Wraps a filtered chain so ``.first()`` returns None once; delegates rest."""

    def __init__(self, chain):  # type: ignore[no-untyped-def]
        self._chain = chain

    def first(self):  # type: ignore[no-untyped-def]
        return None

    def __getattr__(self, name):  # type: ignore[no-untyped-def]
        return getattr(self._chain, name)


def test_batch_isolates_cross_school_duplicate_hash_race(monkeypatch, tmp_path) -> None:
    """REGRESSION-LOCK #8 (G2/G10): a duplicate ``file_hash`` RACE where the
    ``.first()`` pre-check misses but the INSERT hits the ``uq_document_file_hash``
    UNIQUE index. A pre-seeded Document on a DIFFERENT school (id=99) already owns
    ``_DUP_HASH``; the dup school's pre-check is forced to return None (one-shot),
    so ``begin_nested()`` (pdf_discovery.py:4189) raises ``IntegrityError`` ->
    caught at 4192 -> the ``no_autoflush`` re-query at 4197-4202 finds the existing
    cross-school row -> reason ``duplicate_hash_other_school`` with
    ``integrity_error="true"`` (4203-4213).

    Contract: no crash, exactly ONE Document per unique hash (UNIQUE upheld, the
    racing insert rolled back via begin_nested), the dup job finalizes to ``review``
    (cross_school_dup_seen terminal branch 4262-4266, NOT counted as ``failed``),
    the racing download file is unlinked (no orphan), the pre-seeded canonical file
    is preserved, and the control good school AFTER the dup still downloads.
    """

    session = _session()
    dup_id, good_id, owner_id = 1, 2, 99
    dup_page = "https://dup.example.ac.jp/disclosure/"
    good_page = "https://good.example.ac.jp/disclosure/"
    try:
        _add_school(session, dup_id, url=dup_page)
        _add_school(session, good_id, url=good_page)
        # Owner school (id=99) already holds a Document carrying _DUP_HASH, with a
        # CANONICAL file at a path distinct from the racing download so the
        # orphan-unlink assert is meaningful (_remove_duplicate_candidate_file
        # only skips the unlink when the two paths resolve equal). It is added as a
        # bare School (NO SchoolSite) so it is the cross-school FK owner of the
        # pre-seeded Document and is NOT itself crawled in the batch.
        session.add(
            School(
                id=owner_id,
                school_name=f"テスト専門学校{owner_id}",
                prefecture="東京都",
                corporation_name=f"学校法人テスト{owner_id}",
                school_type="専門学校",
                status="active",
            )
        )
        existing_file = tmp_path / "owner_existing.pdf"
        existing_file.write_bytes(b"%PDF-1.4 canonical owner copy " + b"0" * 1100)
        session.add(
            Document(
                school_id=owner_id,
                source_url="https://owner.example.ac.jp/disclosure/owner.pdf",
                file_path=str(existing_file),
                file_hash=_DUP_HASH,
                file_size=2000,
                fiscal_year=2025,
                pdf_type="target",
                ingest_status="ingested",
            )
        )
        session.flush()

        def fake_discover(_client, school_id, _url, **_kwargs):
            page = dup_page if school_id == dup_id else good_page
            cand = _target_candidate(f"{page}target-kakunin.pdf", page)
            return DiscoveryResult(school_id=school_id, candidates=[cand], best=cand)

        def fake_download(_client, candidate, storage_dir, school_id, **_kwargs):
            candidate.detected_fiscal_year = 2025
            candidate.year_evidence = "pdf_text"
            if school_id == dup_id:
                out = tmp_path / "dup_download.pdf"
                out.write_bytes(b"%PDF-1.4 racing dup body " + b"0" * 1100)
                return str(out), _DUP_HASH, 2500, "target", None
            out = tmp_path / f"{school_id}.pdf"
            out.write_bytes(b"%PDF-1.4 good body " + b"0" * 1100)
            return str(out), f"hash-{school_id}", 3000, "target", None

        # Wrap session.query so ONLY the first Document pre-check .first() misses;
        # everything else (the no_autoflush re-query, the good school, CrawlJob /
        # School lookups) delegates to the real query.
        real_query = session.query
        race = {"on": True}

        def patched_query(*args, **kwargs):  # type: ignore[no-untyped-def]
            q = real_query(*args, **kwargs)
            if args and args[0] is Document and race["on"]:
                return _RaceProxy(q, race)
            return q

        session.query = patched_query  # type: ignore[method-assign,assignment]

        monkeypatch.setattr("eidp.scraper.pdf_discovery._is_safe_url", lambda _url: True)
        monkeypatch.setattr("eidp.scraper.pdf_discovery.discover_pdfs_for_site", fake_discover)
        monkeypatch.setattr("eidp.scraper.pdf_discovery.download_pdf", fake_download)

        evidence = tmp_path / "rejections.jsonl"
        # Must not raise: a duplicate-hash race is graceful, not a batch abort.
        stats = run_pdf_discovery(
            session,
            tmp_path,
            batch_size=10,
            rate_limit=0,
            evidence_path=evidence,
        )

        # Restore the real query BEFORE any assertion runs.
        session.query = real_query  # type: ignore[method-assign]

        # G2 UNIQUE upheld: exactly one Document per unique hash. The racing insert
        # was rolled back via begin_nested, so the dup school has NO Document and
        # the pre-seeded owner row is the sole holder of _DUP_HASH.
        assert session.query(Document).filter(Document.file_hash == _DUP_HASH).count() == 1
        assert session.query(Document).filter(Document.school_id == dup_id).count() == 0
        # Batch isolation: the school AFTER the dup still produced a Document.
        assert session.query(Document).filter(Document.school_id == good_id).count() == 1

        # Returned stats lock the batch outcome: both crawled, the dup race is
        # gracefully skipped (NOT failed), the good control downloaded.
        assert stats["crawled"] == 2
        assert stats["downloaded"] == 1
        assert stats["skipped"] == 1
        assert stats["failed"] == 0, "a duplicate-hash race is graceful, not a failure"
        assert stats["rejection_reason_duplicate_hash_other_school"] == 1

        # The dup school's CrawlJob finalizes to 'review' (cross_school_dup_seen
        # terminal branch 4262-4266) -- never stuck at 'running'.
        dup_job = (
            session.query(CrawlJob)
            .filter(CrawlJob.school_id == dup_id)
            .order_by(CrawlJob.id.desc())
            .first()
        )
        assert dup_job is not None
        assert dup_job.status == "review"
        assert dup_job.finished_at is not None
        assert dup_job.error_message == (
            "candidate PDFs are duplicates of documents already attached to other schools"
        )

        # The control good school's CrawlJob is a finalized success.
        good_job = (
            session.query(CrawlJob)
            .filter(CrawlJob.school_id == good_id)
            .order_by(CrawlJob.id.desc())
            .first()
        )
        assert good_job is not None
        assert good_job.status == "success"
        assert good_job.finished_at is not None

        # No orphan: the rejected racing download is unlinked. The canonical
        # pre-seeded owner file is preserved (distinct path, not unlinked).
        assert not (tmp_path / "dup_download.pdf").exists(), (
            "rejected race download must be unlinked, no orphan file"
        )
        assert existing_file.exists(), "the canonical pre-seeded file must be preserved"

        # Stats and evidence agree: exactly one duplicate_hash_other_school row for
        # the dup school, flagged integrity_error=true and pointing at owner id 99.
        payloads = [
            json.loads(line)
            for line in evidence.read_text(encoding="utf-8").splitlines()
        ]
        dup_ev = [
            p
            for p in payloads
            if p["school_id"] == dup_id and p["reason"] == "duplicate_hash_other_school"
        ]
        assert len(dup_ev) == 1, (
            "the racing dup school must emit exactly one duplicate_hash_other_school row"
        )
        assert dup_ev[0]["extra"]["integrity_error"] == "true"
        assert dup_ev[0]["extra"]["existing_school_id"] == str(owner_id)
        assert "existing_doc_id" in dup_ev[0]["extra"]
    finally:
        session.close()


def test_batch_isolates_same_school_duplicate_hash_race(monkeypatch, tmp_path) -> None:
    """REGRESSION-LOCK #9 (G2/G10): same race as #8 but the pre-seeded duplicate is
    on the SAME school (ingest_status='ingested' so the no_file restore branch at
    4106 is skipped). The IntegrityError re-query at 4197-4202 finds a same-school
    row -> reason ``duplicate_hash`` with ``integrity_error="true"`` (4207-4213),
    and the terminal branch is the ``duplicate_seen`` path (4271-4273) -> job
    ``success`` with error_message 'all viable candidates already downloaded'.

    Contract mirrors #8: no crash, exactly ONE Document per unique hash, the racing
    insert rolled back, no orphan, the control good school still downloads.
    """

    session = _session()
    dup_id, good_id = 1, 2
    dup_page = "https://dup.example.ac.jp/disclosure/"
    good_page = "https://good.example.ac.jp/disclosure/"
    try:
        _add_school(session, dup_id, url=dup_page)
        _add_school(session, good_id, url=good_page)
        # Pre-seed the duplicate on the SAME school. ingest_status='ingested'
        # (NOT 'no_file') so _restore_same_school_no_file_duplicate (4106) does
        # not hijack the flow; the IntegrityError branch runs instead.
        existing_file = tmp_path / "same_existing.pdf"
        existing_file.write_bytes(b"%PDF-1.4 canonical same-school copy " + b"0" * 1100)
        session.add(
            Document(
                school_id=dup_id,
                source_url="https://dup.example.ac.jp/disclosure/canonical.pdf",
                file_path=str(existing_file),
                file_hash=_DUP_HASH,
                file_size=2000,
                fiscal_year=2025,
                pdf_type="target",
                ingest_status="ingested",
            )
        )
        session.flush()

        def fake_discover(_client, school_id, _url, **_kwargs):
            page = dup_page if school_id == dup_id else good_page
            cand = _target_candidate(f"{page}target-kakunin.pdf", page)
            return DiscoveryResult(school_id=school_id, candidates=[cand], best=cand)

        def fake_download(_client, candidate, storage_dir, school_id, **_kwargs):
            candidate.detected_fiscal_year = 2025
            candidate.year_evidence = "pdf_text"
            if school_id == dup_id:
                out = tmp_path / "dup_download.pdf"
                out.write_bytes(b"%PDF-1.4 racing dup body " + b"0" * 1100)
                return str(out), _DUP_HASH, 2500, "target", None
            out = tmp_path / f"{school_id}.pdf"
            out.write_bytes(b"%PDF-1.4 good body " + b"0" * 1100)
            return str(out), f"hash-{school_id}", 3000, "target", None

        real_query = session.query
        race = {"on": True}

        def patched_query(*args, **kwargs):  # type: ignore[no-untyped-def]
            q = real_query(*args, **kwargs)
            if args and args[0] is Document and race["on"]:
                return _RaceProxy(q, race)
            return q

        session.query = patched_query  # type: ignore[method-assign,assignment]

        monkeypatch.setattr("eidp.scraper.pdf_discovery._is_safe_url", lambda _url: True)
        monkeypatch.setattr("eidp.scraper.pdf_discovery.discover_pdfs_for_site", fake_discover)
        monkeypatch.setattr("eidp.scraper.pdf_discovery.download_pdf", fake_download)

        evidence = tmp_path / "rejections.jsonl"
        # Must not raise: a same-school duplicate-hash race is graceful.
        stats = run_pdf_discovery(
            session,
            tmp_path,
            batch_size=10,
            rate_limit=0,
            evidence_path=evidence,
        )

        session.query = real_query  # type: ignore[method-assign]

        # G2 UNIQUE upheld: exactly one Document holds _DUP_HASH (the pre-seeded
        # canonical row); the racing insert was rolled back. Same-school dedup
        # keeps the single canonical row for the dup school.
        assert session.query(Document).filter(Document.file_hash == _DUP_HASH).count() == 1
        assert session.query(Document).filter(Document.school_id == dup_id).count() == 1
        # Batch isolation: the good control school still produced a Document.
        assert session.query(Document).filter(Document.school_id == good_id).count() == 1

        # Same-school race is a graceful skip, not a failure.
        assert stats["crawled"] == 2
        assert stats["downloaded"] == 1
        assert stats["skipped"] == 1
        assert stats["failed"] == 0
        assert stats["rejection_reason_duplicate_hash"] == 1

        # Same-school terminal branch (4271-4273): job 'success' with the
        # all-viable-already-downloaded message.
        dup_job = (
            session.query(CrawlJob)
            .filter(CrawlJob.school_id == dup_id)
            .order_by(CrawlJob.id.desc())
            .first()
        )
        assert dup_job is not None
        assert dup_job.status == "success"
        assert dup_job.finished_at is not None
        assert dup_job.error_message == "all viable candidates already downloaded"

        good_job = (
            session.query(CrawlJob)
            .filter(CrawlJob.school_id == good_id)
            .order_by(CrawlJob.id.desc())
            .first()
        )
        assert good_job is not None
        assert good_job.status == "success"
        assert good_job.finished_at is not None

        # No orphan; canonical preserved.
        assert not (tmp_path / "dup_download.pdf").exists()
        assert existing_file.exists()

        # Evidence: one duplicate_hash row for the dup school, integrity_error=true.
        payloads = [
            json.loads(line)
            for line in evidence.read_text(encoding="utf-8").splitlines()
        ]
        dup_ev = [
            p for p in payloads if p["school_id"] == dup_id and p["reason"] == "duplicate_hash"
        ]
        assert len(dup_ev) == 1
        assert dup_ev[0]["extra"]["integrity_error"] == "true"
        assert dup_ev[0]["extra"]["existing_school_id"] == str(dup_id)
    finally:
        session.close()
