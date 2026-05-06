from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from eidp.db.models import Base, CrawlJob, Document, SchoolSite
from eidp.scraper.pdf_discovery import (
    MAX_CANDIDATE_DOWNLOAD_ATTEMPTS,
    DiscoveryResult,
    PdfCandidate,
    _download_attempt_urls,
    _extract_pdf_links,
    _score_candidate,
    _sitemap_urls_for_site,
    discover_pdfs_for_site,
    download_pdf,
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


def test_score_candidate_uses_configured_target_fiscal_year() -> None:
    target = PdfCandidate(
        pdf_url="https://example.ac.jp/r9.pdf",
        page_url="https://example.ac.jp/disclosure/",
        anchor_text="令和9年度 確認申請書",
    )
    previous = PdfCandidate(
        pdf_url="https://example.ac.jp/r8.pdf",
        page_url="https://example.ac.jp/disclosure/",
        anchor_text="令和8年度 確認申請書",
    )

    assert _score_candidate(target, target_fiscal_year=2027) > _score_candidate(
        previous, target_fiscal_year=2027
    )


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


def test_download_attempt_urls_resolves_tmu_download_wrapper(monkeypatch) -> None:
    """TMU-style download wrappers carry the real PDF path in a query value."""

    monkeypatch.setattr("eidp.scraper.pdf_discovery._is_safe_url", lambda _url: True)

    urls = _download_attempt_urls(
        "https://www.tmu.ac.jp/extra/download.html"
        "?dd=assets%2Ffiles%2Fdownload%2FInformation_disclosure%2F2025_syugakusien_shinseisyo_1.pdf"
    )

    assert urls == [
        "https://www.tmu.ac.jp/assets/files/download/Information_disclosure/2025_syugakusien_shinseisyo_1.pdf",
        (
            "https://www.tmu.ac.jp/extra/download.html"
            "?dd=assets%2Ffiles%2Fdownload%2FInformation_disclosure%2F2025_syugakusien_shinseisyo_1.pdf"
        ),
    ]


class _HtmlResponse:
    def __init__(self, text: str, *, status_code: int = 200, url: str = "https://example.ac.jp/") -> None:
        self.text = text
        self.status_code = status_code
        self.headers: dict[str, str] = {}
        self.url = url
        self.request = None

    def raise_for_status(self) -> None:
        return None


class _HtmlClient:
    def __init__(self, pages: dict[str, _HtmlResponse]) -> None:
        self.pages = pages

    def get(self, url: str, **_kwargs):  # noqa: ANN001
        return self.pages.get(url, _HtmlResponse("", status_code=404, url=url))


def test_sitemap_urls_for_site_filters_same_domain_disclosure_pages(monkeypatch) -> None:
    monkeypatch.setattr("eidp.scraper.pdf_discovery._is_safe_url", lambda _url: True)
    client = _HtmlClient(
        {
            "https://example.ac.jp/sitemap.xml": _HtmlResponse(
                """
                <urlset>
                  <url><loc>https://example.ac.jp/school/public_info/</loc></url>
                  <url><loc>https://example.ac.jp/news/</loc></url>
                  <url><loc>https://other.example.jp/disclosure/</loc></url>
                </urlset>
                """,
                url="https://example.ac.jp/sitemap.xml",
            )
        }
    )

    urls = _sitemap_urls_for_site(client, "https://example.ac.jp/")

    assert urls == ["https://example.ac.jp/school/public_info/"]


def test_sitemap_urls_for_site_follows_robots_sitemap_index(monkeypatch) -> None:
    """WordPress-style sites often advertise sitemap_index.xml only in robots.txt."""

    monkeypatch.setattr("eidp.scraper.pdf_discovery._is_safe_url", lambda _url: True)
    client = _HtmlClient(
        {
            "https://example.ac.jp/robots.txt": _HtmlResponse(
                "User-agent: *\nDisallow:\nSitemap: https://example.ac.jp/sitemap_index.xml\n",
                url="https://example.ac.jp/robots.txt",
            ),
            "https://example.ac.jp/sitemap_index.xml": _HtmlResponse(
                """
                <sitemapindex>
                  <sitemap><loc>https://example.ac.jp/page-sitemap.xml</loc></sitemap>
                </sitemapindex>
                """,
                url="https://example.ac.jp/sitemap_index.xml",
            ),
            "https://example.ac.jp/page-sitemap.xml": _HtmlResponse(
                """
                <urlset>
                  <url><loc>https://example.ac.jp/about/valuation/</loc></url>
                  <url><loc>https://example.ac.jp/news/</loc></url>
                </urlset>
                """,
                url="https://example.ac.jp/page-sitemap.xml",
            ),
        }
    )

    urls = _sitemap_urls_for_site(client, "https://example.ac.jp/")

    assert urls == ["https://example.ac.jp/about/valuation/"]


def test_discover_pdfs_uses_sitemap_when_site_has_no_disclosure_links(monkeypatch) -> None:
    monkeypatch.setattr("eidp.scraper.pdf_discovery.time.sleep", lambda _seconds: None)
    monkeypatch.setattr("eidp.scraper.pdf_discovery._is_safe_url", lambda _url: True)
    client = _HtmlClient(
        {
            "https://example.ac.jp/robots.txt": _HtmlResponse("", status_code=404),
            "https://example.ac.jp/": _HtmlResponse("<html><a href='/news/'>news</a></html>"),
            "https://example.ac.jp/sitemap.xml": _HtmlResponse(
                """
                <urlset>
                  <url><loc>https://example.ac.jp/school/public_info/</loc></url>
                </urlset>
                """,
                url="https://example.ac.jp/sitemap.xml",
            ),
            "https://example.ac.jp/school/public_info/": _HtmlResponse(
                """
                <a href="/docs/r8-kakunin.pdf">
                  令和8年度 高等教育の修学支援新制度 確認申請書
                </a>
                """,
                url="https://example.ac.jp/school/public_info/",
            ),
        }
    )

    result = discover_pdfs_for_site(client, 1, "https://example.ac.jp/")

    assert result.error is None
    assert result.best is not None
    assert result.best.pdf_url == "https://example.ac.jp/docs/r8-kakunin.pdf"
    assert result.best.page_url == "https://example.ac.jp/school/public_info/"


def test_discover_pdfs_uses_sitemap_even_when_root_has_stale_pdf(monkeypatch) -> None:
    monkeypatch.setattr("eidp.scraper.pdf_discovery.time.sleep", lambda _seconds: None)
    monkeypatch.setattr("eidp.scraper.pdf_discovery._is_safe_url", lambda _url: True)
    client = _HtmlClient(
        {
            "https://example.ac.jp/robots.txt": _HtmlResponse("", status_code=404),
            "https://example.ac.jp/": _HtmlResponse(
                """
                <html>
                  <a href="/docs/r7-kakunin.pdf">令和7年度 確認申請書</a>
                </html>
                """,
                url="https://example.ac.jp/",
            ),
            "https://example.ac.jp/sitemap.xml": _HtmlResponse(
                """
                <urlset>
                  <url><loc>https://example.ac.jp/school/public_info/</loc></url>
                </urlset>
                """,
                url="https://example.ac.jp/sitemap.xml",
            ),
            "https://example.ac.jp/school/public_info/": _HtmlResponse(
                """
                <a href="/docs/r8-kakunin.pdf">
                  令和8年度 高等教育の修学支援新制度 確認申請書
                </a>
                """,
                url="https://example.ac.jp/school/public_info/",
            ),
        }
    )

    result = discover_pdfs_for_site(client, 1, "https://example.ac.jp/")

    assert result.error is None
    assert result.best is not None
    assert result.best.pdf_url == "https://example.ac.jp/docs/r8-kakunin.pdf"
    assert {candidate.pdf_url for candidate in result.candidates} == {
        "https://example.ac.jp/docs/r7-kakunin.pdf",
        "https://example.ac.jp/docs/r8-kakunin.pdf",
    }


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


def _make_pdf_bytes(text: str) -> bytes:
    import fitz  # type: ignore[import-not-found]

    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text, fontsize=10, fontname="japan")
    data = doc.tobytes()
    doc.close()
    return data


class _PdfResponse:
    def __init__(self, content: bytes) -> None:
        self.content = content
        self.headers: dict[str, str] = {}
        self.url = "https://example.ac.jp/r7.pdf"
        self.request = None

    def raise_for_status(self) -> None:
        return None


def test_download_pdf_rejects_stale_fiscal_year_in_strict_target_mode(
    monkeypatch, tmp_path: Path
) -> None:
    """Strict current-FY discovery must not store a clearly older PDF."""

    content = _make_pdf_bytes("令和7年度 修学支援 機関要件 学科名 生徒総定員")
    candidate = PdfCandidate(
        pdf_url="https://example.ac.jp/r7.pdf",
        page_url="https://example.ac.jp/disclosure/",
        anchor_text="令和7年度 確認申請書",
    )

    monkeypatch.setattr(
        "eidp.scraper.pdf_discovery._safe_get",
        lambda _client, _url: _PdfResponse(content),
    )
    monkeypatch.setattr("eidp.scraper.pdf_discovery._is_safe_url", lambda _url: True)

    file_path, file_hash, file_size, pdf_type, reason = download_pdf(
        object(),  # type: ignore[arg-type]
        candidate,
        tmp_path,
        school_id=1,
        target_fiscal_year=2026,
        strict_target_fiscal_year=True,
    )

    assert file_path is None
    assert file_hash is None
    assert file_size == 0
    assert pdf_type in {"target", "unknown"}
    assert reason == "fiscal_year_mismatch:2025"
    assert not list((tmp_path / "1").glob("*.pdf"))


def test_download_pdf_rejects_url_only_target_hint_in_strict_target_mode(
    monkeypatch, tmp_path: Path
) -> None:
    """URL/anchor hints rank candidates but must not prove the PDF fiscal year."""

    content = _make_pdf_bytes("高等教育の修学支援新制度 確認申請書 機関要件 学科名 生徒総定員")
    candidate = PdfCandidate(
        pdf_url="https://example.ac.jp/2026/r8-kakunin.pdf",
        page_url="https://example.ac.jp/disclosure/",
        anchor_text="令和8年度 確認申請書",
    )

    monkeypatch.setattr(
        "eidp.scraper.pdf_discovery._safe_get",
        lambda _client, _url: _PdfResponse(content),
    )
    monkeypatch.setattr("eidp.scraper.pdf_discovery._is_safe_url", lambda _url: True)

    file_path, file_hash, file_size, pdf_type, reason = download_pdf(
        object(),  # type: ignore[arg-type]
        candidate,
        tmp_path,
        school_id=1,
        target_fiscal_year=2026,
        strict_target_fiscal_year=True,
    )

    assert file_path is None
    assert file_hash is None
    assert file_size == 0
    assert pdf_type == "target"
    assert reason == "target_fiscal_year_not_detected"
    assert not list((tmp_path / "1").glob("*.pdf"))


def test_download_pdf_accepts_pdf_text_target_year_in_strict_target_mode(
    monkeypatch, tmp_path: Path
) -> None:
    content = _make_pdf_bytes("令和8年度 高等教育の修学支援新制度 確認申請書 機関要件 学科名 生徒総定員")
    candidate = PdfCandidate(
        pdf_url="https://example.ac.jp/r8-kakunin.pdf",
        page_url="https://example.ac.jp/disclosure/",
        anchor_text="確認申請書",
    )

    monkeypatch.setattr(
        "eidp.scraper.pdf_discovery._safe_get",
        lambda _client, _url: _PdfResponse(content),
    )
    monkeypatch.setattr("eidp.scraper.pdf_discovery._is_safe_url", lambda _url: True)

    file_path, file_hash, file_size, pdf_type, reason = download_pdf(
        object(),  # type: ignore[arg-type]
        candidate,
        tmp_path,
        school_id=1,
        target_fiscal_year=2026,
        strict_target_fiscal_year=True,
    )

    assert file_path is not None
    assert file_hash is not None
    assert file_size > 1000
    assert pdf_type == "target"
    assert reason is None
    assert Path(file_path).is_file()


def test_download_pdf_uses_resolved_download_wrapper_url(monkeypatch, tmp_path: Path) -> None:
    content = _make_pdf_bytes("令和8年度 高等教育の修学支援新制度 確認申請書 機関要件 学科名 生徒総定員")
    wrapper_url = (
        "https://www.tmu.ac.jp/extra/download.html"
        "?dd=assets%2Ffiles%2Fdownload%2FInformation_disclosure%2F2026_syugakusien_shinseisyo_1.pdf"
    )
    direct_url = "https://www.tmu.ac.jp/assets/files/download/Information_disclosure/2026_syugakusien_shinseisyo_1.pdf"
    candidate = PdfCandidate(
        pdf_url=wrapper_url,
        page_url="https://www.tmu.ac.jp/kyouikujouhoutop/arbitrary-matter/22202.html",
        anchor_text="令和8年度 確認申請書",
    )
    called_urls: list[str] = []

    def fake_safe_get(_client, url: str) -> _PdfResponse:  # noqa: ANN001
        called_urls.append(url)
        return _PdfResponse(content)

    monkeypatch.setattr("eidp.scraper.pdf_discovery._safe_get", fake_safe_get)
    monkeypatch.setattr("eidp.scraper.pdf_discovery._is_safe_url", lambda _url: True)

    file_path, _file_hash, _file_size, pdf_type, reason = download_pdf(
        object(),  # type: ignore[arg-type]
        candidate,
        tmp_path,
        school_id=1,
        target_fiscal_year=2026,
        strict_target_fiscal_year=True,
    )

    assert file_path is not None
    assert called_urls == [direct_url]
    assert candidate.pdf_url == direct_url
    assert pdf_type == "target"
    assert reason is None


def test_run_pdf_discovery_skips_duplicate_hash_from_other_school(
    monkeypatch, tmp_path: Path
) -> None:
    session = _session()
    evidence = tmp_path / "rejections.jsonl"
    duplicate_pdf = tmp_path / "candidate.pdf"
    duplicate_pdf.write_bytes(b"%PDF-" + b"x" * 2000)
    try:
        session.add(SchoolSite(school_id=1, url="https://example.ac.jp/disclosure/", http_status=200))
        session.add(
            Document(
                school_id=99,
                source_url="https://other.example.ac.jp/r8.pdf",
                file_hash="sharedhash",
                file_path="data/pdfs/99/shared.pdf",
                pdf_type="target",
                ingest_status="ingested",
                fiscal_year=2026,
            )
        )
        session.flush()

        candidate = PdfCandidate(
            pdf_url="https://example.ac.jp/r8.pdf",
            page_url="https://example.ac.jp/disclosure/",
            anchor_text="令和8年度 確認申請書",
            score=10.0,
        )

        def fake_discover(_client, school_id: int, _url: str) -> DiscoveryResult:
            return DiscoveryResult(school_id=school_id, candidates=[candidate], best=candidate)

        def fake_download(_client, _candidate: PdfCandidate, _storage_dir: Path, _school_id: int):
            return str(duplicate_pdf), "sharedhash", 2005, "target", None

        monkeypatch.setattr("eidp.scraper.pdf_discovery.discover_pdfs_for_site", fake_discover)
        monkeypatch.setattr("eidp.scraper.pdf_discovery.download_pdf", fake_download)

        stats = run_pdf_discovery(
            session,
            tmp_path,
            batch_size=10,
            rate_limit=0,
            evidence_path=evidence,
        )

        assert stats["downloaded"] == 0
        assert stats["skipped"] == 1
        assert stats["failed"] == 0
        assert session.query(Document).count() == 1
        # Sprint 8.7.f: cross-school duplicate must surface as ``review`` so
        # the operator can resolve via alias / reassignment. ``success``
        # would mislead the queue into thinking this school is covered.
        job = session.query(CrawlJob).one()
        assert job.status == "review"
        assert "other schools" in (job.error_message or "")
        assert not duplicate_pdf.exists()
        payload = json.loads(evidence.read_text(encoding="utf-8").strip())
        assert payload["reason"] == "duplicate_hash_other_school"
        assert payload["extra"]["existing_school_id"] == "99"
    finally:
        session.close()
