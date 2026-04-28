from __future__ import annotations

from eidp.scraper.pdf_discovery import (
    MAX_CANDIDATE_DOWNLOAD_ATTEMPTS,
    PdfCandidate,
    _extract_pdf_links,
    _score_candidate,
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
