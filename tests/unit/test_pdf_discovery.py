from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from eidp.db.models import Base, CrawlJob, Document, SchoolSite
from eidp.scraper.pdf_discovery import (
    MAX_CANDIDATE_DOWNLOAD_ATTEMPTS,
    DiscoveryResult,
    PdfCandidate,
    _extract_pdf_links,
    _score_candidate,
    run_pdf_discovery,
)


def test_confirmation_application_attachment_is_ranked_below_main_pdf() -> None:
    main = PdfCandidate(
        pdf_url="https://example.ac.jp/data/2025/11_confirmation_application.pdf",
        page_url="https://example.ac.jp/disclosure/",
        anchor_text="高等教育の修学支援新制度 確認申請書",
    )
    attachment = PdfCandidate(
        pdf_url="https://example.ac.jp/data/2025/11_confirmation_application_attachment.pdf",
        page_url="https://example.ac.jp/disclosure/",
        anchor_text="高等教育の修学支援新制度 確認申請書",
    )

    assert _score_candidate(main) > _score_candidate(attachment)


def test_extract_pdf_links_decodes_html_entities_in_query_string() -> None:
    html = """
    <a href="/albums/abm.php?d=16&amp;f=abm00001256.pdf&amp;n=%E6%94%B9.pdf">
      高等教育の修学支援新制度（高等教育無償化）申請書様式第２号
    </a>
    """

    candidates = _extract_pdf_links(html, "https://www.tokyo-nissin.ac.jp/schoolguide/disclosure.html")

    assert candidates[0].pdf_url == (
        "https://www.tokyo-nissin.ac.jp/albums/abm.php"
        "?d=16&f=abm00001256.pdf&n=%E6%94%B9.pdf"
    )
    assert "&amp;" not in candidates[0].pdf_url
    assert candidates[0].pattern_type == "cache_busted"
    assert "高等教育の修学支援新制度" in candidates[0].anchor_text


def test_discovery_attempt_window_reaches_buried_confirmation_pdf() -> None:
    """Target forms can rank below the first three candidates on disclosure pages."""

    assert MAX_CANDIDATE_DOWNLOAD_ATTEMPTS >= 8


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_run_pdf_discovery_continues_after_duplicate_hash(monkeypatch, tmp_path: Path) -> None:
    """Sprint 4 rediscovery must not stop on an old already-downloaded PDF.

    Stale disclosure pages often list both old and new target PDFs. If the old
    PDF still ranks first, duplicate-hash handling must continue to the next
    candidate so the newly-published R8 file can be stored.
    """
    session = _session()
    try:
        session.add(SchoolSite(school_id=1, url="https://example.ac.jp/disclosure/", http_status=200))
        session.add(
            Document(
                school_id=1,
                source_url="https://example.ac.jp/r7.pdf",
                file_hash="oldhash",
                file_path="data/pdfs/1/old.pdf",
                pdf_type="target",
                ingest_status="ingested",
                fiscal_year=2025,
            )
        )
        session.flush()

        old = PdfCandidate(
            pdf_url="https://example.ac.jp/r7.pdf",
            page_url="https://example.ac.jp/disclosure/",
            anchor_text="R7 確認申請書",
            score=10.0,
        )
        new = PdfCandidate(
            pdf_url="https://example.ac.jp/r8.pdf",
            page_url="https://example.ac.jp/disclosure/",
            anchor_text="R8 確認申請書",
            score=9.0,
        )

        def fake_discover(_client, school_id: int, _url: str) -> DiscoveryResult:
            return DiscoveryResult(school_id=school_id, candidates=[old, new], best=old)

        def fake_download(_client, candidate: PdfCandidate, _storage_dir: Path, _school_id: int):
            if candidate.pdf_url.endswith("r7.pdf"):
                return str(tmp_path / "old.pdf"), "oldhash", 2000, "target", None
            return str(tmp_path / "new.pdf"), "newhash", 3000, "target", None

        monkeypatch.setattr("eidp.scraper.pdf_discovery.discover_pdfs_for_site", fake_discover)
        monkeypatch.setattr("eidp.scraper.pdf_discovery.download_pdf", fake_download)

        stats = run_pdf_discovery(session, tmp_path, batch_size=10, rate_limit=0)

        assert stats["downloaded"] == 1
        assert stats["skipped"] == 1
        got = session.query(Document).filter(Document.file_hash == "newhash").one()
        assert got.source_url == "https://example.ac.jp/r8.pdf"
        job = session.query(CrawlJob).one()
        assert job.status == "success"
    finally:
        session.close()


def test_run_pdf_discovery_duplicate_only_is_success_not_failed(monkeypatch, tmp_path: Path) -> None:
    session = _session()
    try:
        session.add(SchoolSite(school_id=1, url="https://example.ac.jp/disclosure/", http_status=200))
        session.add(
            Document(
                school_id=1,
                source_url="https://example.ac.jp/r7.pdf",
                file_hash="oldhash",
                file_path="data/pdfs/1/old.pdf",
                pdf_type="target",
                ingest_status="ingested",
                fiscal_year=2025,
            )
        )
        session.flush()
        old = PdfCandidate(
            pdf_url="https://example.ac.jp/r7.pdf",
            page_url="https://example.ac.jp/disclosure/",
            anchor_text="R7 確認申請書",
            score=10.0,
        )

        def fake_discover(_client, school_id: int, _url: str) -> DiscoveryResult:
            return DiscoveryResult(school_id=school_id, candidates=[old], best=old)

        def fake_download(_client, _candidate: PdfCandidate, _storage_dir: Path, _school_id: int):
            return str(tmp_path / "old.pdf"), "oldhash", 2000, "target", None

        monkeypatch.setattr("eidp.scraper.pdf_discovery.discover_pdfs_for_site", fake_discover)
        monkeypatch.setattr("eidp.scraper.pdf_discovery.download_pdf", fake_download)

        stats = run_pdf_discovery(session, tmp_path, batch_size=10, rate_limit=0)

        assert stats["downloaded"] == 0
        assert stats["skipped"] == 1
        assert stats["failed"] == 0
        assert session.query(Document).count() == 1
        job = session.query(CrawlJob).one()
        assert job.status == "success"
        assert job.error_message == "all viable candidates already downloaded"
    finally:
        session.close()
