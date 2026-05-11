from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from eidp.db.models import Base, CrawlJob, Document, School, SchoolSite
from eidp.scraper.pdf_discovery import (
    MAX_CANDIDATE_DOWNLOAD_ATTEMPTS,
    DiscoveryResult,
    PdfCandidate,
    _append_unique_candidates,
    _detect_fiscal_year_from_text,
    _download_attempt_urls,
    _extract_pdf_links,
    _pre_download_rejection,
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


def test_confirmation_application_japanese_attachment_is_ranked_below_main_pdf() -> None:
    main = PdfCandidate(
        pdf_url="https://example.ac.jp/data/2025/kakunin_shinsei.pdf",
        page_url="https://example.ac.jp/disclosure/",
        anchor_text="確認申請書(様式第2号)",
    )
    attachment = PdfCandidate(
        pdf_url="https://example.ac.jp/data/2025/kakunin2025_bessi.pdf",
        page_url="https://example.ac.jp/disclosure/",
        anchor_text="確認申請書(様式第2号の4別紙)",
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


def test_pre_download_rejects_adjacent_school_information_tokens() -> None:
    token_cases = [
        ("https://example.ac.jp/disclosure/yakuinmeibo.pdf", "役員名簿"),
        ("https://example.ac.jp/disclosure/schoolinfo.pdf", "学校情報"),
        ("https://example.ac.jp/disclosure/gakkouinfo.pdf", "学校紹介"),
        ("https://example.ac.jp/disclosure/school-guide.pdf", "学校案内"),
        ("https://example.ac.jp/disclosure/schoolguide.pdf", "School Guide"),
        ("https://example.ac.jp/disclosure/shokugyouzissen_sweets.pdf", "職業実践専門課程"),
        ("https://example.ac.jp/disclosure/2026/subject_it-business.pdf", "ITビジネス学科"),
        ("https://example.ac.jp/disclosure/2026/subject-houritsu.pdf", "法律学科"),
        ("https://example.ac.jp/disclosure/2026/info_it-business.pdf", "ITビジネス学科"),
        ("https://example.ac.jp/disclosure/2026/grade_manage.pdf", "厳格かつ適正な成績管理"),
        ("https://example.ac.jp/disclosure/2026/goal_policies.pdf", "専門課程の教育目標"),
        ("https://example.ac.jp/disclosure/2026/regulation.pdf", "学則"),
        ("https://example.ac.jp/disclosure/2026/donation.pdf", "寄付行為"),
        ("https://example.ac.jp/disclosure/2026/remuneration.pdf", "役員及び評議員の報酬等の支給基準"),
        ("https://example.ac.jp/disclosure/r6-balancesheet.pdf", "令和6年度 貸借対照表"),
        ("https://example.ac.jp/disclosure/r6-inventoryofassets.pdf", "令和6年度 財産目録"),
        ("https://example.ac.jp/disclosure/r6-auditreport.pdf", "令和6年度 監査報告書"),
        ("https://example.ac.jp/disclosure/indexing_rule.pdf", "客観的な指標の算出方法"),
        ("https://example.ac.jp/disclosure/08_seiseki.pdf", "成績分布資料"),
        ("https://example.ac.jp/disclosure/11_nenkan.pdf", "年間計画表"),
        ("https://example.ac.jp/disclosure/K令和6年度教育課程議事録.pdf", "教育課程編成委員会議事録"),
        ("https://example.ac.jp/disclosure/learningassessment.pdf", "学修評価等"),
        ("https://example.ac.jp/disclosure/planreport2024.pdf", "事業計画・報告"),
        ("https://example.ac.jp/disclosure/securitypolicy.pdf", "情報セキュリティポリシー"),
        ("https://example.ac.jp/disclosure/kifu2027.pdf", "寄附行為"),
        ("https://example.ac.jp/disclosure/r4_teikitenkenhokoku.pdf", "定期点検報告書"),
        ("https://example.ac.jp/disclosure/kamoku_s_20250727.pdf", "授業科目一覧"),
        ("https://example.ac.jp/disclosure/2025classsubject.pdf", "2025年度開講科目"),
        ("https://example.ac.jp/disclosure/diploma-policy.pdf", "卒業認定方針"),
        ("https://example.ac.jp/disclosure/OT1-tsuuki.pdf", "1年 通期"),
        ("https://example.ac.jp/disclosure/PT3-zenki.pdf", "3年 前期"),
        ("https://example.ac.jp/disclosure/2021internshipreport.pdf", "実習・就職アンケート調査結果報告書"),
        ("https://example.ac.jp/disclosure/student_support_guidelines.pdf", "学生支援ガイドライン"),
        ("https://example.ac.jp/disclosure/推薦書.pdf", "推薦書"),
    ]

    for url, anchor_text in token_cases:
        candidate = PdfCandidate(
            pdf_url=url,
            page_url="https://example.ac.jp/disclosure/",
            anchor_text=anchor_text,
            score=10.0,
        )

        rejection = _pre_download_rejection(candidate, target_year=2026)

        assert rejection is not None, url
        assert rejection.reason == "pre_filtered_non_target_hint"
        assert rejection.pdf_type == "non_target"


def test_pre_download_keeps_target_form_when_path_contains_school_information_token() -> None:
    candidate = PdfCandidate(
        pdf_url="https://example.ac.jp/学校案内/2026/r8-shugakushien-shinsei.pdf",
        page_url="https://example.ac.jp/学校案内/",
        anchor_text="高等教育の修学支援新制度 確認申請書 様式第2号",
        score=10.0,
    )

    rejection = _pre_download_rejection(candidate, target_year=2026)

    assert rejection is None


def test_pre_download_keeps_target_form_when_subject_path_has_target_hint() -> None:
    candidate = PdfCandidate(
        pdf_url="https://example.ac.jp/disclosure/2026/subject_academic_support.pdf",
        page_url="https://example.ac.jp/disclosure/",
        anchor_text="令和8年度 高等教育の修学支援新制度 確認申請書 様式第2号",
        score=9.0,
    )

    rejection = _pre_download_rejection(candidate, target_year=2026)

    assert rejection is None


def test_pre_download_rejects_subject_pdf_with_adjacent_target_context() -> None:
    candidate = PdfCandidate(
        pdf_url="https://storage-production.all-japan.dev/www.all-japan.ac.jp/2026/04/subject_kango.pdf",
        page_url="https://www.all-japan.ac.jp/about/disclosure/",
        anchor_text=(
            "動物看護学科（3年制） "
            'href="https://storage-production.all-japan.dev/www.all-japan.ac.jp/2026/04/academic_support.pdf" '
            "2025年修学支援新制度様式2号 実務教員の授業科目"
        ),
        score=5.5,
    )

    rejection = _pre_download_rejection(candidate, target_year=2026)

    assert rejection is not None
    assert rejection.reason == "pre_filtered_non_target_hint"
    assert rejection.pdf_type == "non_target"


def test_pre_download_rejects_current_year_news_without_target_hint() -> None:
    candidate = PdfCandidate(
        pdf_url="https://example.ac.jp/files/news/2026/05/open-campus-thanks.pdf",
        page_url="https://example.ac.jp/news/",
        anchor_text="2026.05.08 お知らせ オープンキャンパス参加の皆様ありがとうございました",
        score=9.0,
    )

    rejection = _pre_download_rejection(candidate, target_year=2026)

    assert rejection is not None
    assert rejection.reason == "pre_filtered_non_target_hint"
    assert rejection.pdf_type == "non_target"


def test_pre_download_keeps_target_form_when_news_path_has_target_hint() -> None:
    candidate = PdfCandidate(
        pdf_url="https://example.ac.jp/news/2026/r8-kakunin-shinsei.pdf",
        page_url="https://example.ac.jp/news/",
        anchor_text="令和8年度 高等教育の修学支援新制度 確認申請書 様式第2号",
        score=9.0,
    )

    rejection = _pre_download_rejection(candidate, target_year=2026)

    assert rejection is None


def test_pre_download_rejects_student_support_application_form() -> None:
    candidate = PdfCandidate(
        pdf_url="https://example.ac.jp/pdf/applicationform-r8.pdf",
        page_url="https://example.ac.jp/support/",
        anchor_text="授業料等減免の対象者の認定に関する申請書（A様式1） 令和8年度",
        score=9.0,
    )

    rejection = _pre_download_rejection(candidate, target_year=2026)

    assert rejection is not None
    assert rejection.reason == "pre_filtered_non_target_hint"
    assert rejection.pdf_type == "non_target"


def test_pre_download_prioritizes_stale_target_form_year_over_evaluation_path() -> None:
    candidate = PdfCandidate(
        pdf_url="https://ndac.ac.jp/about/evaluation/uploads/info-2025.pdf",
        page_url="https://ndac.ac.jp/about/evaluation/",
        anchor_text="大学等における修学の支援に関する法律第７条第１項 確認申請書",
        score=3.5,
    )

    rejection = _pre_download_rejection(candidate, target_year=2026)

    assert rejection is not None
    assert rejection.pdf_type == "target"
    assert rejection.reason == "fiscal_year_mismatch:2025"


def test_pre_download_keeps_renewal_confirmation_application_on_evaluation_path() -> None:
    candidate = PdfCandidate(
        pdf_url="https://www.saijidai.ac.jp/sys/wp-content/themes/saijidai/pdf/evaluation/koutoumusyou.pdf",
        page_url="https://www.saijidai.ac.jp/info/evaluation/",
        anchor_text="更新確認申請書",
        score=2.0,
    )

    rejection = _pre_download_rejection(candidate, target_year=2026)

    assert rejection is None


def test_pre_download_detects_stale_renewal_confirmation_application_year() -> None:
    candidate = PdfCandidate(
        pdf_url="https://example.ac.jp/wp-content/uploads/2025/06/2025koushinshinseisyo.pdf",
        page_url="https://example.ac.jp/assessment/",
        anchor_text="2025年度 更新確認申請書(PDF形式)",
        score=3.0,
    )

    rejection = _pre_download_rejection(candidate, target_year=2026)

    assert rejection is not None
    assert rejection.pdf_type == "target"
    assert rejection.reason == "fiscal_year_mismatch:2025"


def test_pre_download_detects_stale_full_form_range_without_support_system_words() -> None:
    candidate = PdfCandidate(
        pdf_url="https://aiko.ac.jp/data/ybc/2025/2-1_2-4.pdf",
        page_url="https://aiko.ac.jp/data/",
        anchor_text="様式第2号の1～4 [PDF] 2025年度",
        score=3.0,
    )

    rejection = _pre_download_rejection(candidate, target_year=2026)

    assert rejection is not None
    assert rejection.pdf_type == "target"
    assert rejection.reason == "fiscal_year_mismatch:2025"


def test_pre_download_does_not_treat_english_renewal_form_alone_as_target() -> None:
    candidate = PdfCandidate(
        pdf_url="https://example.ac.jp/files/2025-renewal-confirmation-application.pdf",
        page_url="https://example.ac.jp/international/",
        anchor_text="Visa renewal confirmation application",
        score=1.0,
    )

    rejection = _pre_download_rejection(candidate, target_year=2026)

    assert rejection is None


def test_pre_download_keeps_english_renewal_form_with_support_system_hint() -> None:
    candidate = PdfCandidate(
        pdf_url="https://example.ac.jp/files/2026-renewal-confirmation-application.pdf",
        page_url="https://example.ac.jp/disclosure/",
        anchor_text="Higher education tuition support renewal confirmation application",
        score=1.0,
    )

    rejection = _pre_download_rejection(candidate, target_year=2026)

    assert rejection is None


def test_pre_download_detects_stale_year_prefix_serial_filename_for_target_form() -> None:
    candidate = PdfCandidate(
        pdf_url="http://www.atg-web.ac.jp/img/educational/2025007.pdf",
        page_url="http://www.atg-web.ac.jp/educational/practice.php",
        anchor_text="７. 大学等における修学の支援に関する確認申請書",
        score=3.5,
    )

    rejection = _pre_download_rejection(candidate, target_year=2026)

    assert rejection is not None
    assert rejection.pdf_type == "target"
    assert rejection.reason == "fiscal_year_mismatch:2025"


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


def test_extract_pdf_links_deduplicates_encoded_and_unencoded_paths() -> None:
    encoded_path = (
        "/wp-content/uploads/2025/07/"
        "%E8%A3%9C%E6%AD%A3%E2%9E%85%E7%A2%BA%E8%AA%8D%E7%94%B3%E8%AB%8B%E6%9B%B8"
        "%EF%BC%88%E6%A7%98%E5%BC%8F%E7%AC%AC2%E5%8F%B7%EF%BC%89.pdf"
    )
    html = f"""
    <a href="/wp-content/uploads/2025/07/補正➅確認申請書（様式第2号）.pdf">raw</a>
    <a href="{encoded_path}">encoded</a>
    """

    candidates = _extract_pdf_links(html, "https://www.saitama-cmcc.ac.jp/school/disclosure/")

    assert [candidate.anchor_text for candidate in candidates] == ["raw"]


def test_extract_pdf_links_includes_wordpress_download_manager_wrappers() -> None:
    html = """
    <p>令和6年度分申請</p>
    <p>
      <a href="#" data-downloadurl="/download/yousiki2/?wpdmdl=5471&amp;refresh=abc">ダウンロード</a>
    </p>
    <p>
      <a href="https://files.example.net/download/yousiki2/?wpdmdl=5471">外部コピー</a>
    </p>
    """

    candidates = _extract_pdf_links(html, "https://i-heiseigakuen.ac.jp/youshiki/")

    assert len(candidates) == 1
    assert candidates[0].pdf_url == "https://i-heiseigakuen.ac.jp/download/yousiki2/?wpdmdl=5471&refresh=abc"
    assert candidates[0].pattern_type == "wordpress_download_manager"
    assert "令和6年度分申請" in candidates[0].anchor_text
    assert "ダウンロード" in candidates[0].anchor_text


def test_append_unique_candidates_deduplicates_encoded_and_unencoded_paths() -> None:
    target = [
        PdfCandidate(
            pdf_url="https://example.ac.jp/wp-content/uploads/2025/07/補正➅確認申請書（様式第2号）.pdf",
            page_url="https://example.ac.jp/disclosure/",
            anchor_text="raw",
        )
    ]
    additions = [
        PdfCandidate(
            pdf_url=(
                "https://example.ac.jp/wp-content/uploads/2025/07/"
                "%E8%A3%9C%E6%AD%A3%E2%9E%85%E7%A2%BA%E8%AA%8D%E7%94%B3%E8%AB%8B%E6%9B%B8"
                "%EF%BC%88%E6%A7%98%E5%BC%8F%E7%AC%AC2%E5%8F%B7%EF%BC%89.pdf"
            ),
            page_url="https://example.ac.jp/disclosure/",
            anchor_text="encoded",
        )
    ]

    _append_unique_candidates(target, additions)

    assert [candidate.anchor_text for candidate in target] == ["raw"]


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


def test_download_attempt_urls_keeps_bare_filename_wrapper_original(monkeypatch) -> None:
    """Bare filename query values are often parameters for the wrapper itself."""

    monkeypatch.setattr("eidp.scraper.pdf_discovery._is_safe_url", lambda _url: True)

    url = (
        "https://www.tokyo-nissin.ac.jp/albums/abm.php"
        "?d=16&f=abm00001256.pdf&n=%E6%94%B9_HP%E5%85%AC%E9%96%8B.pdf"
    )

    assert _download_attempt_urls(url) == [url]


class _AttemptPdfResponse:
    def __init__(self, url: str, *, status_code: int, content: bytes) -> None:
        self.text = ""
        self.status_code = status_code
        self.headers: dict[str, str] = {}
        self.url = url
        self.request = httpx.Request("GET", url)
        self.content = content

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                f"HTTP {self.status_code}",
                request=self.request,
                response=httpx.Response(self.status_code, request=self.request),
            )


class _AttemptPdfClient:
    def __init__(self, responses: dict[str, _AttemptPdfResponse]) -> None:
        self.responses = responses
        self.calls: list[str] = []

    def get(self, url: str, **_kwargs):  # noqa: ANN001
        self.calls.append(url)
        return self.responses[url]


def test_download_pdf_continues_after_failed_attempt(monkeypatch, tmp_path: Path) -> None:
    """A failed resolved URL must not prevent trying the original wrapper URL."""

    bad_url = "https://example.ac.jp/misresolved.pdf"
    good_url = "https://example.ac.jp/albums/abm.php?d=16&f=abm00001256.pdf"
    client = _AttemptPdfClient(
        {
            bad_url: _AttemptPdfResponse(bad_url, status_code=404, content=b""),
            good_url: _AttemptPdfResponse(good_url, status_code=200, content=b"%PDF-" + (b"x" * 2000)),
        }
    )
    candidate = PdfCandidate(pdf_url=good_url, page_url="https://example.ac.jp/disclosure/")

    monkeypatch.setattr("eidp.scraper.pdf_discovery._is_safe_url", lambda _url: True)
    monkeypatch.setattr("eidp.scraper.pdf_discovery._download_attempt_urls", lambda _url: [bad_url, good_url])
    monkeypatch.setattr(
        "eidp.scraper.pdf_discovery._extract_pdf_sample_text",
        lambda _content: "様式第2号 機関要件 令和8年度",
    )

    file_path, file_hash, file_size, pdf_type, reason = download_pdf(
        client,
        candidate,
        tmp_path,
        123,
        target_fiscal_year=2026,
        strict_target_fiscal_year=True,
    )

    assert client.calls == [bad_url, good_url]
    assert candidate.pdf_url == good_url
    assert file_path is not None
    assert file_hash is not None
    assert file_size == 2005
    assert pdf_type == "target"
    assert reason is None


def test_download_pdf_keeps_image_target_hint_for_ocr_queue(monkeypatch, tmp_path: Path) -> None:
    """Image-only target-looking forms should be retained for OCR/manual review."""

    url = "https://example.ac.jp/albums/abm.php?d=16&f=abm00001256.pdf"
    client = _AttemptPdfClient(
        {
            url: _AttemptPdfResponse(url, status_code=200, content=b"%PDF-" + (b"x" * 2000)),
        }
    )
    candidate = PdfCandidate(
        pdf_url=url,
        page_url="https://example.ac.jp/disclosure/",
        anchor_text="高等教育の修学支援新制度（高等教育無償化）申請書様式第２号",
    )

    monkeypatch.setattr("eidp.scraper.pdf_discovery._is_safe_url", lambda _url: True)
    monkeypatch.setattr("eidp.scraper.pdf_discovery._extract_pdf_sample_text", lambda _content: "")

    file_path, file_hash, file_size, pdf_type, reason = download_pdf(
        client,
        candidate,
        tmp_path,
        123,
        target_fiscal_year=2026,
        strict_target_fiscal_year=True,
    )

    assert file_path is not None
    assert file_hash is not None
    assert file_size == 2005
    assert pdf_type == "image_only"
    assert reason is None


def test_download_pdf_keeps_image_with_strong_form_year_anchor(monkeypatch, tmp_path: Path) -> None:
    """Opaque WordPress PDFs may carry the target-year evidence only in anchor text."""

    url = "https://example.ac.jp/wp-content/uploads/2025/07/b1b74768f7ce7b4c01670b76f27bb275.pdf"
    client = _AttemptPdfClient(
        {
            url: _AttemptPdfResponse(url, status_code=200, content=b"%PDF-" + (b"x" * 2000)),
        }
    )
    candidate = PdfCandidate(
        pdf_url=url,
        page_url="https://example.ac.jp/2025/07/18/information/",
        anchor_text="令和８年度機関要件確認申請書20250718（様式第２号）",
    )

    monkeypatch.setattr("eidp.scraper.pdf_discovery._is_safe_url", lambda _url: True)
    monkeypatch.setattr("eidp.scraper.pdf_discovery._extract_pdf_sample_text", lambda _content: "")

    file_path, file_hash, file_size, pdf_type, reason = download_pdf(
        client,
        candidate,
        tmp_path,
        123,
        target_fiscal_year=2026,
        strict_target_fiscal_year=True,
    )

    assert file_path is not None
    assert file_hash is not None
    assert file_size == 2005
    assert pdf_type == "image_only"
    assert reason is None
    assert candidate.year_evidence == "url_hint"


def test_download_pdf_rejects_image_without_target_hint_in_strict_mode(monkeypatch, tmp_path: Path) -> None:
    """Generic image PDFs still need target-form evidence before retention."""

    url = "https://example.ac.jp/photo.pdf"
    client = _AttemptPdfClient(
        {
            url: _AttemptPdfResponse(url, status_code=200, content=b"%PDF-" + (b"x" * 2000)),
        }
    )
    candidate = PdfCandidate(
        pdf_url=url,
        page_url="https://example.ac.jp/disclosure/",
        anchor_text="学校案内",
    )

    monkeypatch.setattr("eidp.scraper.pdf_discovery._is_safe_url", lambda _url: True)
    monkeypatch.setattr("eidp.scraper.pdf_discovery._extract_pdf_sample_text", lambda _content: "")

    file_path, file_hash, file_size, pdf_type, reason = download_pdf(
        client,
        candidate,
        tmp_path,
        123,
        target_fiscal_year=2026,
        strict_target_fiscal_year=True,
    )

    assert file_path is None
    assert file_hash is None
    assert file_size == 0
    assert pdf_type == "image_only"
    assert reason == "target_fiscal_year_not_detected"


def test_download_pdf_rejects_image_with_target_year_but_no_target_form_hint(
    monkeypatch, tmp_path: Path
) -> None:
    """A target-year admission guide is not a target confirmation form."""

    url = "https://example.ac.jp/wp-content/uploads/2025/05/2026-admission-guide.pdf"
    client = _AttemptPdfClient(
        {
            url: _AttemptPdfResponse(url, status_code=200, content=b"%PDF-" + (b"x" * 2000)),
        }
    )
    candidate = PdfCandidate(
        pdf_url=url,
        page_url="https://example.ac.jp/application-guidelines/",
        anchor_text="社会人・医療機関推薦選抜 募集要項",
    )

    monkeypatch.setattr("eidp.scraper.pdf_discovery._is_safe_url", lambda _url: True)
    monkeypatch.setattr(
        "eidp.scraper.pdf_discovery._extract_pdf_sample_text",
        lambda _content: "2026年度 社会人・医療機関推薦選抜募集要項 (cid:1234)",
    )

    file_path, file_hash, file_size, pdf_type, reason = download_pdf(
        client,
        candidate,
        tmp_path,
        123,
        target_fiscal_year=2026,
        strict_target_fiscal_year=True,
    )

    assert file_path is None
    assert file_hash is None
    assert file_size == 0
    assert pdf_type == "image_only"
    assert reason == "target_application_not_detected"
    assert not list((tmp_path / "123").glob("*.pdf"))


def test_download_pdf_does_not_turn_support_only_image_year_into_publication_lag(
    monkeypatch, tmp_path: Path
) -> None:
    """Support-only image PDFs need review; old year labels alone are not target-form proof."""

    url = "https://urasen.jp/wp/wp-content/themes/urawa/assets/pdf/about/report/09_shugakushien_r7.pdf"
    client = _AttemptPdfClient(
        {
            url: _AttemptPdfResponse(url, status_code=200, content=b"%PDF-" + (b"x" * 2000)),
        }
    )
    candidate = PdfCandidate(
        pdf_url=url,
        page_url="https://urasen.jp/about/report/",
        anchor_text="R7修学支援に関する資料",
    )

    monkeypatch.setattr("eidp.scraper.pdf_discovery._is_safe_url", lambda _url: True)
    monkeypatch.setattr("eidp.scraper.pdf_discovery._extract_pdf_sample_text", lambda _content: "")

    file_path, file_hash, file_size, pdf_type, reason = download_pdf(
        client,
        candidate,
        tmp_path,
        761,
        target_fiscal_year=2026,
        strict_target_fiscal_year=True,
    )

    assert file_path is None
    assert file_hash is None
    assert file_size == 0
    assert pdf_type == "image_only"
    assert reason == "target_fiscal_year_not_detected"
    assert not list((tmp_path / "761").glob("*.pdf"))


def test_download_pdf_does_not_turn_boilerplate_year_image_into_publication_lag(
    monkeypatch, tmp_path: Path
) -> None:
    """Generic MEXT support years in page context are not stale target-form evidence."""

    url = "https://example.ac.jp/support/koutou202507.pdf?20250711"
    client = _AttemptPdfClient(
        {
            url: _AttemptPdfResponse(url, status_code=200, content=b"%PDF-" + (b"x" * 2000)),
        }
    )
    candidate = PdfCandidate(
        pdf_url=url,
        page_url="https://example.ac.jp/support/",
        anchor_text="2020年度から対象 本校の申請内容について",
    )

    monkeypatch.setattr("eidp.scraper.pdf_discovery._is_safe_url", lambda _url: True)
    monkeypatch.setattr("eidp.scraper.pdf_discovery._extract_pdf_sample_text", lambda _content: "")

    file_path, file_hash, file_size, pdf_type, reason = download_pdf(
        client,
        candidate,
        tmp_path,
        763,
        target_fiscal_year=2026,
        strict_target_fiscal_year=True,
    )

    assert file_path is None
    assert file_hash is None
    assert file_size == 0
    assert pdf_type == "image_only"
    assert reason == "target_fiscal_year_not_detected"
    assert not list((tmp_path / "763").glob("*.pdf"))


class _HtmlResponse:
    def __init__(self, text: str, *, status_code: int = 200, url: str = "https://example.ac.jp/") -> None:
        self.text = text
        self.status_code = status_code
        self.headers: dict[str, str] = {}
        self.url = url
        self.request = None

    def raise_for_status(self) -> None:
        return None


class _RaisingHtmlResponse(_HtmlResponse):
    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            request = httpx.Request("GET", str(self.url))
            raise httpx.HTTPStatusError(
                f"HTTP {self.status_code}",
                request=request,
                response=httpx.Response(self.status_code, request=request),
            )


class _HtmlClient:
    def __init__(self, pages: dict[str, _HtmlResponse]) -> None:
        self.pages = pages
        self.calls: list[str] = []

    def get(self, url: str, **_kwargs):  # noqa: ANN001
        self.calls.append(url)
        return self.pages.get(url, _HtmlResponse("", status_code=404, url=url))


class _RenderedHtmlFetcher:
    def __init__(self, pages: dict[str, str]) -> None:
        self.pages = pages
        self.calls: list[str] = []

    def fetch_html(self, url: str) -> str | None:
        self.calls.append(url)
        return self.pages.get(url)


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


def test_discover_pdfs_falls_back_to_origin_root_when_registered_path_is_404(monkeypatch) -> None:
    """Official indexes can contain stale disclosure paths while the root nav still links the live page."""

    monkeypatch.setattr("eidp.scraper.pdf_discovery.time.sleep", lambda _seconds: None)
    monkeypatch.setattr("eidp.scraper.pdf_discovery._is_safe_url", lambda _url: True)
    client = _HtmlClient(
        {
            "https://example.ac.jp/robots.txt": _HtmlResponse("", status_code=404),
            "https://example.ac.jp/old/disclosure/": _RaisingHtmlResponse(
                """
                <html>
                  <a href="/about/disclosure/">情報公開</a>
                </html>
                """,
                status_code=404,
                url="https://example.ac.jp/old/disclosure/",
            ),
            "https://example.ac.jp/": _HtmlResponse(
                """
                <html>
                  <a href="/about/disclosure/">情報公開</a>
                </html>
                """,
                url="https://example.ac.jp/",
            ),
            "https://example.ac.jp/about/disclosure/": _HtmlResponse(
                """
                <a href="/files/r8-kakunin.pdf">
                  令和8年度 高等教育の修学支援新制度 確認申請書
                </a>
                """,
                url="https://example.ac.jp/about/disclosure/",
            ),
            "https://example.ac.jp/sitemap.xml": _HtmlResponse("", status_code=404),
        }
    )

    result = discover_pdfs_for_site(
        client,
        1,
        "https://example.ac.jp/old/disclosure/",
        target_fiscal_year=2026,
    )

    assert result.error is None
    assert result.best is not None
    assert result.best.pdf_url == "https://example.ac.jp/files/r8-kakunin.pdf"
    assert "https://example.ac.jp/" in client.calls
    assert "https://example.ac.jp/about/disclosure/" in client.calls


def test_discover_pdfs_prioritizes_school_named_disclosure_link_from_group_root(monkeypatch) -> None:
    """Dense corporation roots must spend the bounded crawl budget on the matching school first."""

    monkeypatch.setattr("eidp.scraper.pdf_discovery.time.sleep", lambda _seconds: None)
    monkeypatch.setattr("eidp.scraper.pdf_discovery._is_safe_url", lambda _url: True)
    generic_links = "\n".join(
        f'<a href="/disclosure/generic-{idx}/">Generic school {idx}</a>'
        for idx in range(8)
    )
    client = _HtmlClient(
        {
            "https://www.sanko.ac.jp/robots.txt": _HtmlResponse("", status_code=404),
            "https://www.sanko.ac.jp/omiya-med/disclosure/": _RaisingHtmlResponse(
                "<html>stale</html>",
                status_code=404,
                url="https://www.sanko.ac.jp/omiya-med/disclosure/",
            ),
            "https://www.sanko.ac.jp/": _HtmlResponse(
                f"""
                <html>
                  {generic_links}
                  <a href="/disclosure/omiya-med/">大宮医療秘書専門学校</a>
                </html>
                """,
                url="https://www.sanko.ac.jp/",
            ),
            "https://www.sanko.ac.jp/disclosure/omiya-med/": _HtmlResponse(
                """
                <a href="/disclosure/omiya-med/docs/r8-kakunin.pdf">
                  令和8年度 高等教育の修学支援新制度 確認申請書
                </a>
                """,
                url="https://www.sanko.ac.jp/disclosure/omiya-med/",
            ),
            "https://www.sanko.ac.jp/sitemap.xml": _HtmlResponse("", status_code=404),
        }
    )

    result = discover_pdfs_for_site(
        client,
        15,
        "https://www.sanko.ac.jp/omiya-med/disclosure/",
        max_extra_pages=1,
        school_name="大宮医療秘書専門学校",
        target_fiscal_year=2026,
    )

    assert result.error is None
    assert result.best is not None
    assert result.best.pdf_url == "https://www.sanko.ac.jp/disclosure/omiya-med/docs/r8-kakunin.pdf"
    assert result.best.page_url == "https://www.sanko.ac.jp/disclosure/omiya-med/"
    assert "https://www.sanko.ac.jp/disclosure/generic-0/" not in client.calls


def test_discover_pdfs_inverts_stale_school_disclosure_path(monkeypatch) -> None:
    """Official indexes can carry /school/disclosure while live group pages use /disclosure/school."""

    monkeypatch.setattr("eidp.scraper.pdf_discovery.time.sleep", lambda _seconds: None)
    monkeypatch.setattr("eidp.scraper.pdf_discovery._is_safe_url", lambda _url: True)
    client = _HtmlClient(
        {
            "https://www.sanko.ac.jp/robots.txt": _HtmlResponse("", status_code=404),
            "https://www.sanko.ac.jp/omiya-med/disclosure/": _RaisingHtmlResponse(
                "<html>stale</html>",
                status_code=404,
                url="https://www.sanko.ac.jp/omiya-med/disclosure/",
            ),
            "https://www.sanko.ac.jp/": _HtmlResponse(
                "<html><a href='/disclosure/'>学校法人情報公開</a></html>",
                url="https://www.sanko.ac.jp/",
            ),
            "https://www.sanko.ac.jp/disclosure/": _HtmlResponse(
                "<html><a href='/disclosure/generic/'>別の学校</a></html>",
                url="https://www.sanko.ac.jp/disclosure/",
            ),
            "https://www.sanko.ac.jp/disclosure/omiya-med": _HtmlResponse(
                """
                <a href="/disclosure/omiya-med/docs/r8-kakunin.pdf">
                  令和8年度 高等教育の修学支援新制度 確認申請書
                </a>
                """,
                url="https://www.sanko.ac.jp/disclosure/omiya-med",
            ),
            "https://www.sanko.ac.jp/sitemap.xml": _HtmlResponse("", status_code=404),
        }
    )

    result = discover_pdfs_for_site(
        client,
        15,
        "https://www.sanko.ac.jp/omiya-med/disclosure/",
        max_extra_pages=6,
        school_name="大宮医療秘書専門学校",
        target_fiscal_year=2026,
    )

    assert result.error is None
    assert result.best is not None
    assert result.best.pdf_url == "https://www.sanko.ac.jp/disclosure/omiya-med/docs/r8-kakunin.pdf"
    assert result.best.page_url == "https://www.sanko.ac.jp/disclosure/omiya-med"
    assert "https://www.sanko.ac.jp/information/omiya-med" not in client.calls


def test_discover_pdfs_does_not_fetch_pdf_query_links_as_subpages(monkeypatch) -> None:
    monkeypatch.setattr("eidp.scraper.pdf_discovery.time.sleep", lambda _seconds: None)
    monkeypatch.setattr("eidp.scraper.pdf_discovery._is_safe_url", lambda _url: True)
    client = _HtmlClient(
        {
            "https://example.ac.jp/robots.txt": _HtmlResponse("", status_code=404),
            "https://example.ac.jp/disclosure/": _HtmlResponse(
                """
                <a href="/docs/info.pdf?report=202604">情報公開 PDF</a>
                <a href="/public/">情報公開</a>
                """,
                url="https://example.ac.jp/disclosure/",
            ),
            "https://example.ac.jp/public/": _HtmlResponse(
                """
                <a href="/docs/r8-kakunin.pdf">
                  令和8年度 高等教育の修学支援新制度 確認申請書
                </a>
                """,
                url="https://example.ac.jp/public/",
            ),
            "https://example.ac.jp/sitemap.xml": _HtmlResponse("", status_code=404),
        }
    )

    result = discover_pdfs_for_site(
        client,
        1,
        "https://example.ac.jp/disclosure/",
        max_extra_pages=1,
        target_fiscal_year=2026,
    )

    assert result.error is None
    assert result.best is not None
    assert result.best.pdf_url == "https://example.ac.jp/docs/r8-kakunin.pdf"
    assert "https://example.ac.jp/docs/info.pdf?report=202604" not in client.calls


def test_discover_pdfs_follows_school_named_homepage_from_umbrella_root(monkeypatch) -> None:
    """Stale official-index group URLs can recover via a school-named external homepage link."""

    monkeypatch.setattr("eidp.scraper.pdf_discovery.time.sleep", lambda _seconds: None)
    monkeypatch.setattr("eidp.scraper.pdf_discovery._is_safe_url", lambda _url: True)
    client = _HtmlClient(
        {
            "https://group.example/robots.txt": _HtmlResponse("", status_code=404),
            "https://group.example/old/nsb.html": _RaisingHtmlResponse(
                "<html>stale</html>",
                status_code=404,
                url="https://group.example/old/nsb.html",
            ),
            "https://group.example/": _HtmlResponse(
                """
                <html>
                  <a href="https://school.example/">名古屋ビジネス・アカデミー</a>
                  <a href="https://other.example/">別の学校</a>
                </html>
                """,
                url="https://group.example/",
            ),
            "https://school.example/": _HtmlResponse(
                """
                <html>
                  <a href="/about/evaluation/">情報公開</a>
                </html>
                """,
                url="https://school.example/",
            ),
            "https://school.example/about/evaluation/": _HtmlResponse(
                """
                <a href="/docs/info-2025.pdf">
                  大学等における修学の支援に関する法律第7条第1項 確認申請書
                </a>
                """,
                url="https://school.example/about/evaluation/",
            ),
            "https://group.example/sitemap.xml": _HtmlResponse("", status_code=404),
        }
    )

    result = discover_pdfs_for_site(
        client,
        1,
        "https://group.example/old/nsb.html",
        school_name="専門学校名古屋ビジネス・アカデミー",
        target_fiscal_year=2026,
    )

    assert result.error is None
    assert result.best is not None
    assert result.best.pdf_url == "https://school.example/docs/info-2025.pdf"
    assert "https://school.example/" in client.calls
    assert "https://school.example/about/evaluation/" in client.calls
    assert "https://other.example/" not in client.calls


def test_discover_pdfs_tries_derived_disclosure_pages_from_school_slug(monkeypatch) -> None:
    monkeypatch.setattr("eidp.scraper.pdf_discovery.time.sleep", lambda _seconds: None)
    monkeypatch.setattr("eidp.scraper.pdf_discovery._is_safe_url", lambda _url: True)
    client = _HtmlClient(
        {
            "https://www.sanko.ac.jp/robots.txt": _HtmlResponse("", status_code=404),
            "https://www.sanko.ac.jp/omiya-med": _HtmlResponse(
                "<html><a href='/news/'>news</a></html>",
                url="https://www.sanko.ac.jp/omiya-med",
            ),
            "https://www.sanko.ac.jp/disclosure/omiya-med": _HtmlResponse(
                """
                <a href="/docs/r8-kakunin.pdf">
                  令和8年度 高等教育の修学支援新制度 確認申請書
                </a>
                """,
                url="https://www.sanko.ac.jp/disclosure/omiya-med",
            ),
            "https://www.sanko.ac.jp/sitemap.xml": _HtmlResponse("", status_code=404),
        }
    )

    result = discover_pdfs_for_site(
        client,
        1,
        "https://www.sanko.ac.jp/omiya-med",
        rendered_html_fetcher=_RenderedHtmlFetcher({}),
        target_fiscal_year=2026,
    )

    assert result.error is None
    assert result.best is not None
    assert result.best.pdf_url == "https://www.sanko.ac.jp/docs/r8-kakunin.pdf"
    assert result.best.page_url == "https://www.sanko.ac.jp/disclosure/omiya-med"
    assert "https://www.sanko.ac.jp/disclosure/omiya-med" in client.calls


def test_discover_pdfs_tries_gold_set_derived_support_pages(monkeypatch) -> None:
    """Gold-set traces include root-level school-support/information pages."""

    monkeypatch.setattr("eidp.scraper.pdf_discovery.time.sleep", lambda _seconds: None)
    monkeypatch.setattr("eidp.scraper.pdf_discovery._is_safe_url", lambda _url: True)
    client = _HtmlClient(
        {
            "https://example.ac.jp/robots.txt": _HtmlResponse("", status_code=404),
            "https://example.ac.jp/": _HtmlResponse("<html><a href='/news/'>news</a></html>"),
            "https://example.ac.jp/school-support/": _HtmlResponse(
                """
                <a href="/files/school_support_R8.pdf">
                  令和８年度 機関要件確認申請書 様式第２号
                </a>
                """,
                url="https://example.ac.jp/school-support/",
            ),
            "https://example.ac.jp/sitemap.xml": _HtmlResponse("", status_code=404),
        }
    )

    result = discover_pdfs_for_site(
        client,
        1,
        "https://example.ac.jp/",
        rendered_html_fetcher=_RenderedHtmlFetcher({}),
        target_fiscal_year=2026,
    )

    assert result.error is None
    assert result.best is not None
    assert result.best.pdf_url == "https://example.ac.jp/files/school_support_R8.pdf"
    assert result.best.page_url == "https://example.ac.jp/school-support/"
    assert "https://example.ac.jp/school-support/" in client.calls


def test_discover_pdfs_follows_application_form_page_with_wordpress_download_manager(monkeypatch) -> None:
    """Some WordPress sites link application-form pages that expose only wpdmdl download wrappers."""

    monkeypatch.setattr("eidp.scraper.pdf_discovery.time.sleep", lambda _seconds: None)
    monkeypatch.setattr("eidp.scraper.pdf_discovery._is_safe_url", lambda _url: True)
    redirect = _HtmlResponse("", status_code=301, url="https://www.i-heiseigakuen.ac.jp/kokai/")
    redirect.headers["location"] = "https://i-heiseigakuen.ac.jp/kokai/"
    client = _HtmlClient(
        {
            "https://www.i-heiseigakuen.ac.jp/robots.txt": _HtmlResponse("", status_code=404),
            "https://www.i-heiseigakuen.ac.jp/kokai/": redirect,
            "https://i-heiseigakuen.ac.jp/kokai/": _HtmlResponse(
                """
                <html>
                  <a href="/youshiki/">申請様式</a>
                </html>
                """,
                url="https://i-heiseigakuen.ac.jp/kokai/",
            ),
            "https://i-heiseigakuen.ac.jp/youshiki/": _HtmlResponse(
                """
                <p>令和8年度分申請</p>
                <p>
                  <a href="#" data-downloadurl="/download/yousiki2/?wpdmdl=5471&amp;refresh=abc">
                    高等教育の修学支援新制度 確認申請書 様式２
                  </a>
                </p>
                """,
                url="https://i-heiseigakuen.ac.jp/youshiki/",
            ),
            "https://i-heiseigakuen.ac.jp/sitemap.xml": _HtmlResponse("", status_code=404),
        }
    )

    result = discover_pdfs_for_site(
        client,
        1,
        "https://www.i-heiseigakuen.ac.jp/kokai/",
        target_fiscal_year=2026,
    )

    assert result.error is None
    assert result.best is not None
    assert result.best.pdf_url == "https://i-heiseigakuen.ac.jp/download/yousiki2/?wpdmdl=5471&refresh=abc"
    assert result.best.pattern_type == "wordpress_download_manager"
    assert result.best.page_url == "https://i-heiseigakuen.ac.jp/youshiki/"
    assert "https://i-heiseigakuen.ac.jp/youshiki/" in client.calls


def test_discover_pdfs_falls_back_to_root_when_registered_page_is_non_html(monkeypatch) -> None:
    """Official index URLs can rot into image/media assets while root nav still exposes disclosure."""

    monkeypatch.setattr("eidp.scraper.pdf_discovery.time.sleep", lambda _seconds: None)
    monkeypatch.setattr("eidp.scraper.pdf_discovery._is_safe_url", lambda _url: True)
    image_response = _HtmlResponse("not html", url="https://www.akikusa-wf.ac.jp/wp-content/uploads/cover.jpg")
    image_response.headers["content-type"] = "image/jpeg"
    client = _HtmlClient(
        {
            "https://www.akikusa-wf.ac.jp/robots.txt": _HtmlResponse("", status_code=404),
            "https://www.akikusa-wf.ac.jp/?page_id=712": image_response,
            "https://www.akikusa-wf.ac.jp/": _HtmlResponse(
                """
                <html>
                  <a href="/school-top/disclosure/">情報公開</a>
                </html>
                """,
                url="https://www.akikusa-wf.ac.jp/",
            ),
            "https://www.akikusa-wf.ac.jp/school-top/disclosure/": _HtmlResponse(
                """
                <a href="/wp-content/uploads/2025/08/令和7年度-様式第2号.pdf">
                  令和7年度 様式第2号
                </a>
                """,
                url="https://www.akikusa-wf.ac.jp/school-top/disclosure/",
            ),
            "https://www.akikusa-wf.ac.jp/sitemap.xml": _HtmlResponse("", status_code=404),
        }
    )

    result = discover_pdfs_for_site(
        client,
        754,
        "https://www.akikusa-wf.ac.jp/?page_id=712",
        target_fiscal_year=2026,
    )

    assert result.error is None
    assert result.best is not None
    assert result.best.pdf_url == "https://www.akikusa-wf.ac.jp/wp-content/uploads/2025/08/令和7年度-様式第2号.pdf"
    assert result.best.page_url == "https://www.akikusa-wf.ac.jp/school-top/disclosure/"
    assert "https://www.akikusa-wf.ac.jp/" in client.calls


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


def test_discover_pdfs_uses_rendered_html_when_static_candidates_are_stale(monkeypatch) -> None:
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
            "https://example.ac.jp/sitemap.xml": _HtmlResponse("", status_code=404),
        }
    )
    rendered = _RenderedHtmlFetcher(
        {
            "https://example.ac.jp/": """
                <html>
                  <a href="/docs/r8-kakunin.pdf">
                    令和8年度 高等教育の修学支援新制度 確認申請書
                  </a>
                </html>
            """,
        }
    )

    result = discover_pdfs_for_site(
        client,
        1,
        "https://example.ac.jp/",
        rendered_html_fetcher=rendered,
        target_fiscal_year=2026,
    )

    assert rendered.calls == ["https://example.ac.jp/"]
    assert result.error is None
    assert result.best is not None
    assert result.best.pdf_url == "https://example.ac.jp/docs/r8-kakunin.pdf"
    assert {candidate.pdf_url for candidate in result.candidates} == {
        "https://example.ac.jp/docs/r7-kakunin.pdf",
        "https://example.ac.jp/docs/r8-kakunin.pdf",
    }


def test_discover_pdfs_uses_rendered_html_when_static_current_year_candidate_is_not_target(
    monkeypatch,
) -> None:
    """A current-year guide PDF must not suppress JS discovery of the target form."""

    monkeypatch.setattr("eidp.scraper.pdf_discovery.time.sleep", lambda _seconds: None)
    monkeypatch.setattr("eidp.scraper.pdf_discovery._is_safe_url", lambda _url: True)
    client = _HtmlClient(
        {
            "https://example.ac.jp/robots.txt": _HtmlResponse("", status_code=404),
            "https://example.ac.jp/": _HtmlResponse(
                """
                <html>
                  <a href="/docs/2026-school-guide.pdf">2026年度 学校案内</a>
                </html>
                """,
                url="https://example.ac.jp/",
            ),
            "https://example.ac.jp/sitemap.xml": _HtmlResponse("", status_code=404),
        }
    )
    rendered = _RenderedHtmlFetcher(
        {
            "https://example.ac.jp/": """
                <html>
                  <a href="/docs/r8-kakunin.pdf">
                    令和8年度 高等教育の修学支援新制度 確認申請書
                  </a>
                </html>
            """,
        }
    )

    result = discover_pdfs_for_site(
        client,
        1,
        "https://example.ac.jp/",
        rendered_html_fetcher=rendered,
        target_fiscal_year=2026,
    )

    assert rendered.calls == ["https://example.ac.jp/"]
    assert result.error is None
    assert result.best is not None
    assert result.best.pdf_url == "https://example.ac.jp/docs/r8-kakunin.pdf"
    assert {candidate.pdf_url for candidate in result.candidates} == {
        "https://example.ac.jp/docs/2026-school-guide.pdf",
        "https://example.ac.jp/docs/r8-kakunin.pdf",
    }


def test_discover_pdfs_follows_subpage_revealed_by_rendered_html(monkeypatch) -> None:
    monkeypatch.setattr("eidp.scraper.pdf_discovery.time.sleep", lambda _seconds: None)
    monkeypatch.setattr("eidp.scraper.pdf_discovery._is_safe_url", lambda _url: True)
    client = _HtmlClient(
        {
            "https://example.ac.jp/robots.txt": _HtmlResponse("", status_code=404),
            "https://example.ac.jp/": _HtmlResponse("<html><main id='app'></main></html>", url="https://example.ac.jp/"),
            "https://example.ac.jp/sitemap.xml": _HtmlResponse("", status_code=404),
        }
    )
    rendered = _RenderedHtmlFetcher(
        {
            "https://example.ac.jp/": '<a href="/public/">情報公開</a>',
            "https://example.ac.jp/public/": """
                <a href="/docs/r8-kakunin.pdf">
                  令和8年度 高等教育の修学支援新制度 確認申請書
                </a>
            """,
        }
    )

    result = discover_pdfs_for_site(
        client,
        1,
        "https://example.ac.jp/",
        rendered_html_fetcher=rendered,
        target_fiscal_year=2026,
    )

    assert rendered.calls == ["https://example.ac.jp/", "https://example.ac.jp/public/"]
    assert result.error is None
    assert result.best is not None
    assert result.best.pdf_url == "https://example.ac.jp/docs/r8-kakunin.pdf"


def test_discover_pdfs_respects_extra_page_budget(monkeypatch) -> None:
    monkeypatch.setattr("eidp.scraper.pdf_discovery.time.sleep", lambda _seconds: None)
    monkeypatch.setattr("eidp.scraper.pdf_discovery._is_safe_url", lambda _url: True)
    client = _HtmlClient(
        {
            "https://example.ac.jp/robots.txt": _HtmlResponse("", status_code=404),
            "https://example.ac.jp/": _HtmlResponse(
                """
                <a href="/public/one/">情報公開 1</a>
                <a href="/public/two/">情報公開 2</a>
                <a href="/public/three/">情報公開 3</a>
                """,
                url="https://example.ac.jp/",
            ),
            "https://example.ac.jp/public/one/": _HtmlResponse(
                '<a href="/docs/one.pdf">令和8年度 確認申請書</a>',
                url="https://example.ac.jp/public/one/",
            ),
            "https://example.ac.jp/public/two/": _HtmlResponse(
                '<a href="/docs/two.pdf">令和8年度 確認申請書</a>',
                url="https://example.ac.jp/public/two/",
            ),
            "https://example.ac.jp/public/three/": _HtmlResponse(
                '<a href="/docs/three.pdf">令和8年度 確認申請書</a>',
                url="https://example.ac.jp/public/three/",
            ),
        }
    )

    result = discover_pdfs_for_site(
        client,
        1,
        "https://example.ac.jp/",
        max_extra_pages=2,
        max_elapsed_seconds=999,
    )

    assert "https://example.ac.jp/public/one/" in client.calls
    assert "https://example.ac.jp/public/two/" in client.calls
    assert "https://example.ac.jp/public/three/" not in client.calls
    assert {candidate.pdf_url for candidate in result.candidates} == {
        "https://example.ac.jp/docs/one.pdf",
        "https://example.ac.jp/docs/two.pdf",
    }


def test_discovery_attempt_window_reaches_buried_confirmation_pdf() -> None:
    """Target forms can rank below the first three candidates on disclosure pages."""

    assert MAX_CANDIDATE_DOWNLOAD_ATTEMPTS >= 8


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_run_pdf_discovery_passes_school_name_to_site_crawler(monkeypatch, tmp_path: Path) -> None:
    session = _session()
    seen: dict[str, str] = {}

    def fake_discover(_client, _school_id, _site_url, **kwargs):  # noqa: ANN001
        seen["school_name"] = kwargs.get("school_name", "")
        return DiscoveryResult(school_id=1)

    try:
        session.add(
            School(
                id=1,
                prefecture="愛知県",
                corporation_name="法人",
                school_name="専門学校名古屋ビジネス・アカデミー",
                school_type="専門学校",
                status="active",
            )
        )
        session.add(SchoolSite(school_id=1, url="https://group.example/old/nsb.html", http_status=200))
        session.flush()
        monkeypatch.setattr("eidp.scraper.pdf_discovery.discover_pdfs_for_site", fake_discover)

        stats = run_pdf_discovery(session, tmp_path, batch_size=1, rate_limit=0)

        assert stats["crawled"] == 1
        assert seen["school_name"] == "専門学校名古屋ビジネス・アカデミー"
    finally:
        session.close()


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
                source_url="https://example.ac.jp/old.pdf",
                file_hash="oldhash",
                file_path="data/pdfs/1/old.pdf",
                pdf_type="target",
                ingest_status="ingested",
                fiscal_year=2025,
            )
        )
        session.flush()

        old = PdfCandidate(
            pdf_url="https://example.ac.jp/old.pdf",
            page_url="https://example.ac.jp/disclosure/",
            anchor_text="確認申請書",
            score=10.0,
        )
        new = PdfCandidate(
            pdf_url="https://example.ac.jp/r8.pdf",
            page_url="https://example.ac.jp/disclosure/",
            anchor_text="R8 確認申請書",
            score=9.0,
        )

        def fake_discover(_client, school_id: int, _url: str, **_kwargs: object) -> DiscoveryResult:
            return DiscoveryResult(school_id=school_id, candidates=[old, new], best=old)

        def fake_download(
            _client,
            candidate: PdfCandidate,
            _storage_dir: Path,
            _school_id: int,
            **_kwargs: object,
        ):
            if candidate.pdf_url.endswith("old.pdf"):
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
                source_url="https://example.ac.jp/kakunin.pdf",
                file_hash="oldhash",
                file_path="data/pdfs/1/old.pdf",
                pdf_type="target",
                ingest_status="ingested",
                fiscal_year=2025,
            )
        )
        session.flush()
        old = PdfCandidate(
            pdf_url="https://example.ac.jp/kakunin.pdf",
            page_url="https://example.ac.jp/disclosure/",
            anchor_text="確認申請書",
            score=10.0,
        )

        def fake_discover(_client, school_id: int, _url: str, **_kwargs: object) -> DiscoveryResult:
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


def test_run_pdf_discovery_reuses_rejected_candidate_within_run(monkeypatch, tmp_path: Path) -> None:
    """Common corporation sites can expose the same stale PDF for many schools.

    Re-downloading and re-classifying that identical rejected URL for each
    school makes the Windows bootstrap appear frozen during the PDF crawl.
    """

    session = _session()
    evidence = tmp_path / "rejections.jsonl"
    download_calls: list[str] = []
    try:
        session.add(SchoolSite(school_id=1, url="https://group.example.ac.jp/school-a/", http_status=200))
        session.add(SchoolSite(school_id=2, url="https://group.example.ac.jp/school-b/", http_status=200))
        session.flush()

        stale_pdf_url = "https://group.example.ac.jp/about/joho/pdf/kakunin.pdf"

        def fake_discover(_client, school_id: int, url: str, **_kwargs: object) -> DiscoveryResult:
            candidate = PdfCandidate(
                pdf_url=stale_pdf_url,
                page_url=url,
                anchor_text="確認申請書",
                score=10.0,
            )
            return DiscoveryResult(school_id=school_id, candidates=[candidate], best=candidate)

        def fake_download(_client, candidate: PdfCandidate, _storage_dir: Path, _school_id: int):
            download_calls.append(candidate.pdf_url)
            return None, None, 0, "target", "fiscal_year_mismatch:2025"

        monkeypatch.setattr("eidp.scraper.pdf_discovery.discover_pdfs_for_site", fake_discover)
        monkeypatch.setattr("eidp.scraper.pdf_discovery.download_pdf", fake_download)

        stats = run_pdf_discovery(
            session,
            tmp_path,
            batch_size=10,
            rate_limit=0,
            evidence_path=evidence,
        )

        assert download_calls == [stale_pdf_url]
        assert stats["cached_rejections"] == 1
        assert stats["skipped"] == 2
        assert stats["rejection_reason_fiscal_year_mismatch"] == 2

        payloads = [
            json.loads(line)
            for line in evidence.read_text(encoding="utf-8").splitlines()
        ]
        assert [payload["reason"] for payload in payloads] == [
            "fiscal_year_mismatch:2025",
            "fiscal_year_mismatch:2025",
        ]
        assert payloads[1]["extra"]["cached_rejection"] == "true"
    finally:
        session.close()


def test_run_pdf_discovery_prefilters_obvious_non_target_before_download(
    monkeypatch, tmp_path: Path
) -> None:
    """Disclosure pages often list adjacent public PDFs before the target form."""

    session = _session()
    evidence = tmp_path / "rejections.jsonl"
    download_calls: list[str] = []
    try:
        session.add(SchoolSite(school_id=1, url="https://example.ac.jp/disclosure/", http_status=200))
        session.flush()

        non_target = PdfCandidate(
            pdf_url="https://example.ac.jp/R7_jitsumukeiken_design.pdf",
            page_url="https://example.ac.jp/disclosure/",
            anchor_text="令和7年度 実務経験のある教員等による授業科目の一覧表",
            score=10.0,
        )
        target = PdfCandidate(
            pdf_url="https://example.ac.jp/r8-kakunin.pdf",
            page_url="https://example.ac.jp/disclosure/",
            anchor_text="令和8年度 確認申請書",
            score=9.0,
        )

        def fake_discover(_client, school_id: int, _url: str, **_kwargs: object) -> DiscoveryResult:
            return DiscoveryResult(school_id=school_id, candidates=[non_target, target], best=non_target)

        def fake_download(_client, candidate: PdfCandidate, _storage_dir: Path, _school_id: int):
            download_calls.append(candidate.pdf_url)
            candidate.detected_fiscal_year = None
            candidate.year_evidence = "url_hint"
            return str(tmp_path / "target.pdf"), "targethash", 3000, "target", None

        monkeypatch.setattr("eidp.scraper.pdf_discovery.discover_pdfs_for_site", fake_discover)
        monkeypatch.setattr("eidp.scraper.pdf_discovery.download_pdf", fake_download)

        stats = run_pdf_discovery(
            session,
            tmp_path,
            batch_size=10,
            rate_limit=0,
            evidence_path=evidence,
        )

        assert download_calls == ["https://example.ac.jp/r8-kakunin.pdf"]
        assert stats["prefiltered"] == 1
        assert stats["skipped"] == 1
        assert stats["downloaded"] == 1
        assert stats["rejection_reason_pre_filtered_non_target_hint"] == 1

        payloads = [
            json.loads(line)
            for line in evidence.read_text(encoding="utf-8").splitlines()
        ]
        assert payloads[0]["reason"] == "pre_filtered_non_target_hint"
        assert payloads[0]["pdf_type"] == "non_target"
        assert payloads[-1]["reason"] == "accepted_downloaded"
        assert payloads[-1]["extra"]["year_evidence"] == "url_hint"
        assert payloads[-1]["extra"]["detected_fiscal_year"] == ""
    finally:
        session.close()


def test_run_pdf_discovery_prefiltered_candidates_do_not_exhaust_download_attempts(
    monkeypatch, tmp_path: Path
) -> None:
    """Pre-filtered adjacent PDFs should not hide a lower-ranked target form."""

    session = _session()
    evidence = tmp_path / "rejections.jsonl"
    download_calls: list[str] = []
    try:
        session.add(SchoolSite(school_id=1, url="https://example.ac.jp/disclosure/", http_status=200))
        session.flush()

        non_targets = [
            PdfCandidate(
                pdf_url=f"https://example.ac.jp/files/news/2026/05/open-campus-{idx}.pdf",
                page_url="https://example.ac.jp/news/",
                anchor_text=(
                    f"2026.05.{idx:02d} お知らせ 高等教育 修学支援 無償化 "
                    "オープンキャンパス"
                ),
                score=20.0,
            )
            for idx in range(MAX_CANDIDATE_DOWNLOAD_ATTEMPTS)
        ]
        target = PdfCandidate(
            pdf_url="https://example.ac.jp/r8-kakunin.pdf",
            page_url="https://example.ac.jp/disclosure/",
            anchor_text="令和8年度 確認申請書",
            score=1.0,
        )

        def fake_discover(_client, school_id: int, _url: str, **_kwargs: object) -> DiscoveryResult:
            candidates = [*non_targets, target]
            return DiscoveryResult(school_id=school_id, candidates=candidates, best=non_targets[0])

        def fake_download(_client, candidate: PdfCandidate, _storage_dir: Path, _school_id: int, **_kwargs: object):
            download_calls.append(candidate.pdf_url)
            candidate.detected_fiscal_year = 2026
            candidate.year_evidence = "pdf_text"
            return str(tmp_path / "target.pdf"), "targethash", 3000, "target", None

        monkeypatch.setattr("eidp.scraper.pdf_discovery.discover_pdfs_for_site", fake_discover)
        monkeypatch.setattr("eidp.scraper.pdf_discovery.download_pdf", fake_download)

        stats = run_pdf_discovery(
            session,
            tmp_path,
            batch_size=10,
            rate_limit=0,
            evidence_path=evidence,
            target_fiscal_year=2026,
            strict_target_fiscal_year=True,
        )

        assert download_calls == ["https://example.ac.jp/r8-kakunin.pdf"]
        assert stats["prefiltered"] == MAX_CANDIDATE_DOWNLOAD_ATTEMPTS
        assert stats["downloaded"] == 1
        payloads = [
            json.loads(line)
            for line in evidence.read_text(encoding="utf-8").splitlines()
        ]
        assert [payload["reason"] for payload in payloads].count("pre_filtered_non_target_hint") == (
            MAX_CANDIDATE_DOWNLOAD_ATTEMPTS
        )
        assert payloads[-1]["reason"] == "accepted_downloaded"
    finally:
        session.close()


def test_run_pdf_discovery_sets_target_year_on_strict_downloaded_document(
    monkeypatch, tmp_path: Path
) -> None:
    """Strict discovery has already proven the target year; persist it immediately."""

    session = _session()
    try:
        session.add(SchoolSite(school_id=1, url="https://example.ac.jp/disclosure/", http_status=200))
        session.flush()

        target = PdfCandidate(
            pdf_url="https://example.ac.jp/r8-kakunin.pdf",
            page_url="https://example.ac.jp/disclosure/",
            anchor_text="令和8年度 確認申請書",
            score=9.0,
        )

        def fake_discover(_client, school_id: int, _url: str, **_kwargs: object) -> DiscoveryResult:
            return DiscoveryResult(school_id=school_id, candidates=[target], best=target)

        def fake_download(
            _client,
            candidate: PdfCandidate,
            _storage_dir: Path,
            _school_id: int,
            **_kwargs: object,
        ):
            candidate.detected_fiscal_year = None
            candidate.year_evidence = "url_hint"
            return str(tmp_path / "target.pdf"), "targethash", 3000, "target", None

        monkeypatch.setattr("eidp.scraper.pdf_discovery.discover_pdfs_for_site", fake_discover)
        monkeypatch.setattr("eidp.scraper.pdf_discovery.download_pdf", fake_download)

        stats = run_pdf_discovery(
            session,
            tmp_path,
            batch_size=10,
            rate_limit=0,
            target_fiscal_year=2026,
            strict_target_fiscal_year=True,
        )

        assert stats["downloaded"] == 1
        doc = session.query(Document).one()
        assert doc.fiscal_year == 2026
        assert doc.is_current_year is True
    finally:
        session.close()


def test_run_pdf_discovery_marks_prefecture_disclosure_as_trusted_year_evidence(
    monkeypatch, tmp_path: Path
) -> None:
    """Current-year prefecture indexes can prove the year for yearless target forms."""

    session = _session()
    evidence = tmp_path / "evidence.jsonl"
    seen_trusted_evidence: list[str] = []
    try:
        session.add(SchoolSite(
            school_id=1,
            url="https://example.ac.jp/admission/support.php",
            url_type="disclosure",
            discovery_method="prefecture_aggregator",
            http_status=200,
            verified_at=datetime.now(UTC),
            last_checked=datetime.now(UTC),
        ))
        session.flush()

        target = PdfCandidate(
            pdf_url="https://example.ac.jp/files/study_support_system.pdf",
            page_url="https://example.ac.jp/admission/support.php",
            anchor_text="確認申請",
            score=3.0,
        )

        def fake_discover(_client, school_id: int, _url: str, **_kwargs: object) -> DiscoveryResult:
            return DiscoveryResult(school_id=school_id, candidates=[target], best=target)

        def fake_download(
            _client,
            candidate: PdfCandidate,
            _storage_dir: Path,
            _school_id: int,
            **_kwargs: object,
        ):
            seen_trusted_evidence.append(candidate.trusted_year_evidence)
            candidate.year_evidence = candidate.trusted_year_evidence
            return str(tmp_path / "target.pdf"), "targethash", 3000, "target", None

        monkeypatch.setattr("eidp.scraper.pdf_discovery.discover_pdfs_for_site", fake_discover)
        monkeypatch.setattr("eidp.scraper.pdf_discovery.download_pdf", fake_download)

        stats = run_pdf_discovery(
            session,
            tmp_path,
            batch_size=10,
            rate_limit=0,
            evidence_path=evidence,
            target_fiscal_year=2026,
            strict_target_fiscal_year=True,
            discovery_methods=["prefecture_aggregator"],
        )

        assert stats["downloaded"] == 1
        assert seen_trusted_evidence == ["prefecture_index_current_year"]
        payload = json.loads(evidence.read_text(encoding="utf-8").splitlines()[-1])
        assert payload["reason"] == "accepted_downloaded"
        assert payload["extra"]["year_evidence"] == "prefecture_index_current_year"
    finally:
        session.close()


def test_run_pdf_discovery_does_not_trust_stale_prefecture_disclosure_year_evidence(
    monkeypatch, tmp_path: Path
) -> None:
    session = _session()
    evidence = tmp_path / "evidence.jsonl"
    seen_trusted_evidence: list[str] = []
    try:
        stale_checked = datetime.now(UTC) - timedelta(days=500)
        session.add(SchoolSite(
            school_id=1,
            url="https://example.ac.jp/admission/support.php",
            url_type="disclosure",
            discovery_method="prefecture_aggregator",
            http_status=200,
            verified_at=stale_checked,
            last_checked=stale_checked,
        ))
        session.flush()

        target = PdfCandidate(
            pdf_url="https://example.ac.jp/files/study_support_system.pdf",
            page_url="https://example.ac.jp/admission/support.php",
            anchor_text="確認申請",
            score=3.0,
        )

        def fake_discover(_client, school_id: int, _url: str, **_kwargs: object) -> DiscoveryResult:
            return DiscoveryResult(school_id=school_id, candidates=[target], best=target)

        def fake_download(
            _client,
            candidate: PdfCandidate,
            _storage_dir: Path,
            _school_id: int,
            **_kwargs: object,
        ):
            seen_trusted_evidence.append(candidate.trusted_year_evidence)
            return None, None, 0, "target", "target_fiscal_year_not_detected"

        monkeypatch.setattr("eidp.scraper.pdf_discovery.discover_pdfs_for_site", fake_discover)
        monkeypatch.setattr("eidp.scraper.pdf_discovery.download_pdf", fake_download)

        stats = run_pdf_discovery(
            session,
            tmp_path,
            batch_size=10,
            rate_limit=0,
            evidence_path=evidence,
            target_fiscal_year=2026,
            strict_target_fiscal_year=True,
            discovery_methods=["prefecture_aggregator"],
        )

        assert stats["downloaded"] == 0
        assert seen_trusted_evidence == [""]
        payload = json.loads(evidence.read_text(encoding="utf-8").splitlines()[-1])
        assert payload["reason"] == "target_fiscal_year_not_detected"
    finally:
        session.close()


def test_run_pdf_discovery_does_not_trust_prefecture_url_health_check_as_year_evidence(
    monkeypatch, tmp_path: Path
) -> None:
    session = _session()
    seen_trusted_evidence: list[str] = []
    try:
        session.add(SchoolSite(
            school_id=1,
            url="https://example.ac.jp/admission/support.php",
            url_type="disclosure",
            discovery_method="prefecture_aggregator",
            http_status=200,
            verified=True,
            verified_at=None,
            last_checked=datetime.now(UTC),
        ))
        session.flush()

        target = PdfCandidate(
            pdf_url="https://example.ac.jp/files/study_support_system.pdf",
            page_url="https://example.ac.jp/admission/support.php",
            anchor_text="確認申請",
            score=3.0,
        )

        def fake_discover(_client, school_id: int, _url: str, **_kwargs: object) -> DiscoveryResult:
            return DiscoveryResult(school_id=school_id, candidates=[target], best=target)

        def fake_download(
            _client,
            candidate: PdfCandidate,
            _storage_dir: Path,
            _school_id: int,
            **_kwargs: object,
        ):
            seen_trusted_evidence.append(candidate.trusted_year_evidence)
            return None, None, 0, "target", "target_fiscal_year_not_detected"

        monkeypatch.setattr("eidp.scraper.pdf_discovery.discover_pdfs_for_site", fake_discover)
        monkeypatch.setattr("eidp.scraper.pdf_discovery.download_pdf", fake_download)

        stats = run_pdf_discovery(
            session,
            tmp_path,
            batch_size=10,
            rate_limit=0,
            target_fiscal_year=2026,
            strict_target_fiscal_year=True,
            discovery_methods=["prefecture_aggregator"],
        )

        assert stats["downloaded"] == 0
        assert seen_trusted_evidence == [""]
    finally:
        session.close()


def test_run_pdf_discovery_prefilters_encoded_non_target_query_before_download(
    monkeypatch, tmp_path: Path
) -> None:
    """Wrapper URLs can hide the visible PDF filename in an encoded query value."""

    session = _session()
    evidence = tmp_path / "rejections.jsonl"
    download_calls: list[str] = []
    try:
        session.add(SchoolSite(school_id=1, url="https://example.ac.jp/disclosure/", http_status=200))
        session.flush()

        non_target = PdfCandidate(
            pdf_url=(
                "https://example.ac.jp/albums/abm.php?d=16&f=abm00001166.pdf"
                "&n=%E5%AE%9F%E5%8B%99%E7%B5%8C%E9%A8%93_%E5%85%AC%E5%8B%99%E5%93%A1.pdf"
            ),
            page_url="https://example.ac.jp/disclosure/",
            anchor_text="公務員学科",
            score=10.0,
        )
        target = PdfCandidate(
            pdf_url="https://example.ac.jp/r8-kakunin.pdf",
            page_url="https://example.ac.jp/disclosure/",
            anchor_text="令和8年度 確認申請書",
            score=9.0,
        )

        def fake_discover(_client, school_id: int, _url: str, **_kwargs: object) -> DiscoveryResult:
            return DiscoveryResult(school_id=school_id, candidates=[non_target, target], best=non_target)

        def fake_download(_client, candidate: PdfCandidate, _storage_dir: Path, _school_id: int):
            download_calls.append(candidate.pdf_url)
            candidate.detected_fiscal_year = 2026
            candidate.year_evidence = "pdf_text"
            return str(tmp_path / "target.pdf"), "targethash", 3000, "target", None

        monkeypatch.setattr("eidp.scraper.pdf_discovery.discover_pdfs_for_site", fake_discover)
        monkeypatch.setattr("eidp.scraper.pdf_discovery.download_pdf", fake_download)

        stats = run_pdf_discovery(
            session,
            tmp_path,
            batch_size=10,
            rate_limit=0,
            evidence_path=evidence,
        )

        assert download_calls == ["https://example.ac.jp/r8-kakunin.pdf"]
        assert stats["prefiltered"] == 1
        assert stats["downloaded"] == 1

        first = json.loads(evidence.read_text(encoding="utf-8").splitlines()[0])
        assert first["reason"] == "pre_filtered_non_target_hint"
        assert first["extra"]["pre_download"] == "true"
    finally:
        session.close()


def test_run_pdf_discovery_prefilters_explicit_old_fiscal_year_before_download(
    monkeypatch, tmp_path: Path
) -> None:
    """Strong R-era/year labels in links are enough to skip stale PDFs."""

    session = _session()
    evidence = tmp_path / "rejections.jsonl"
    download_calls: list[str] = []
    try:
        session.add(SchoolSite(school_id=1, url="https://example.ac.jp/disclosure/", http_status=200))
        session.flush()

        stale = PdfCandidate(
            pdf_url="https://example.ac.jp/disclosure/s_tf_application_2_r07.pdf",
            page_url="https://example.ac.jp/disclosure/",
            anchor_text="令和7年度 修学支援 高等教育 無償化 確認申請 機関要件 様式第2号",
            score=10.0,
        )
        target = PdfCandidate(
            pdf_url="https://example.ac.jp/disclosure/kakunin_r08.pdf",
            page_url="https://example.ac.jp/disclosure/",
            anchor_text="令和8年度 確認申請書",
            score=9.0,
        )

        def fake_discover(_client, school_id: int, _url: str, **_kwargs: object) -> DiscoveryResult:
            return DiscoveryResult(school_id=school_id, candidates=[stale, target], best=stale)

        def fake_download(_client, candidate: PdfCandidate, _storage_dir: Path, _school_id: int):
            download_calls.append(candidate.pdf_url)
            candidate.detected_fiscal_year = 2026
            candidate.year_evidence = "pdf_text"
            return str(tmp_path / "target.pdf"), "targethash", 3000, "target", None

        monkeypatch.setattr("eidp.scraper.pdf_discovery.discover_pdfs_for_site", fake_discover)
        monkeypatch.setattr("eidp.scraper.pdf_discovery.download_pdf", fake_download)

        stats = run_pdf_discovery(
            session,
            tmp_path,
            batch_size=10,
            rate_limit=0,
            evidence_path=evidence,
            target_fiscal_year=2026,
        )

        assert download_calls == ["https://example.ac.jp/disclosure/kakunin_r08.pdf"]
        assert stats["prefiltered"] == 1
        assert stats["skipped"] == 1
        assert stats["downloaded"] == 1

        payloads = [
            json.loads(line)
            for line in evidence.read_text(encoding="utf-8").splitlines()
        ]
        assert payloads[0]["reason"] == "fiscal_year_mismatch:2025"
        assert payloads[0]["pdf_type"] == "target"
        assert payloads[0]["extra"]["pre_download"] == "true"
        assert payloads[-1]["reason"] == "accepted_downloaded"
        assert payloads[-1]["extra"]["year_evidence"] == "pdf_text"
        assert payloads[-1]["extra"]["detected_fiscal_year"] == "2026"
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


def test_detect_fiscal_year_ignores_future_term_dates_without_filing_context() -> None:
    text = (
        "様式第2号 高等教育の修学支援新制度 確認申請書\n"
        "役員の任期 令和7年4月1日から令和11年3月31日まで\n"
        "機関要件 学科名 生徒総定員"
    )

    assert _detect_fiscal_year_from_text(text, max_fiscal_year=2026) is None


def test_detect_fiscal_year_uses_contextual_filing_date() -> None:
    text = (
        "様式第2号 高等教育の修学支援新制度 確認申請書\n"
        "提出日 令和8年6月1日\n"
        "機関要件 学科名 生徒総定員"
    )

    assert _detect_fiscal_year_from_text(text, max_fiscal_year=2026) == 2026


def test_detect_fiscal_year_ignores_future_western_fiscal_year_labels() -> None:
    text = (
        "様式第2号 高等教育の修学支援新制度 確認申請書\n"
        "非常勤 損害保険事務所 所長 2025.6.6～2029年度定時評議員会終結時"
    )

    assert _detect_fiscal_year_from_text(text, max_fiscal_year=2026) is None


def test_detect_fiscal_year_ignores_completion_year_label() -> None:
    text = (
        "様式第2号 高等教育の修学支援新制度 確認申請書\n"
        "学科設置3年目。完成年度は2026年度\n"
        "機関要件 学科名 生徒総定員"
    )

    assert _detect_fiscal_year_from_text(text, max_fiscal_year=2026) is None


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


def test_download_pdf_does_not_treat_future_term_date_as_pdf_year(
    monkeypatch, tmp_path: Path
) -> None:
    content = _make_pdf_bytes(
        "様式第2号 高等教育の修学支援新制度 確認申請書 機関要件 学科名 生徒総定員\n"
        "役員の任期 令和7年4月1日から令和11年3月31日まで"
    )
    candidate = PdfCandidate(
        pdf_url="https://example.ac.jp/syugakusien.pdf",
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

    assert file_path is None
    assert file_hash is None
    assert file_size == 0
    assert pdf_type == "target"
    assert reason == "target_fiscal_year_not_detected"
    assert not list((tmp_path / "1").glob("*.pdf"))


def test_download_pdf_rejects_stale_link_when_only_body_year_is_completion_year(
    monkeypatch, tmp_path: Path
) -> None:
    content = _make_pdf_bytes(
        "様式第2号 高等教育の修学支援新制度 確認申請書 機関要件 学科名 生徒総定員\n"
        "学科設置3年目。完成年度は2026年度"
    )
    candidate = PdfCandidate(
        pdf_url="https://example.ac.jp/wp-content/uploads/2025/shugakushien_shinsei2025.pdf",
        page_url="https://example.ac.jp/disclosure/",
        anchor_text="2025年度申請書（様式第2号）",
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
    assert reason == "fiscal_year_mismatch:2025"
    assert not list((tmp_path / "1").glob("*.pdf"))


def test_download_pdf_uses_candidate_stale_year_when_body_only_has_future_term_year(
    monkeypatch, tmp_path: Path
) -> None:
    content = _make_pdf_bytes(
        "様式第2号 高等教育の修学支援新制度 確認申請書 機関要件 学科名 生徒総定員\n"
        "非常勤 損害保険事務所 所長 2025.6.6～2029年度定時評議員会終結時"
    )
    candidate = PdfCandidate(
        pdf_url="https://example.ac.jp/wp-content/uploads/2025/06/2025koushinshinseisyo.pdf",
        page_url="https://example.ac.jp/assessment/",
        anchor_text="2025年度 更新確認申請書(PDF形式)",
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
    assert reason == "fiscal_year_mismatch:2025"
    assert not list((tmp_path / "1").glob("*.pdf"))


def test_download_pdf_rejects_stale_year_in_candidate_filename(
    monkeypatch, tmp_path: Path
) -> None:
    content = _make_pdf_bytes("高等教育の修学支援新制度 確認申請書 機関要件 学科名 生徒総定員")
    candidate = PdfCandidate(
        pdf_url="https://example.ac.jp/jyugyoryo-genmen2025_2.pdf",
        page_url="https://example.ac.jp/support/",
        anchor_text="授業料減免申請書ダウンロード（PDF版）",
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
    assert reason == "fiscal_year_mismatch:2025"
    assert not list((tmp_path / "1").glob("*.pdf"))


def test_download_pdf_rejects_stale_reiwa_year_from_anchor_when_body_has_no_year(
    monkeypatch, tmp_path: Path
) -> None:
    content = _make_pdf_bytes("高等教育の修学支援新制度 確認申請書 機関要件 学科名 生徒総定員")
    candidate = PdfCandidate(
        pdf_url="https://example.ac.jp/school/pdf/0809.pdf",
        page_url="https://example.ac.jp/disclosure/",
        anchor_text="10．令和7年度確認申請書",
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
    assert reason == "fiscal_year_mismatch:2025"
    assert not list((tmp_path / "1").glob("*.pdf"))


def test_download_pdf_rejects_reiwa_first_year_anchor_for_image_only_target(
    monkeypatch, tmp_path: Path
) -> None:
    url = "https://example.ac.jp/school/pdf/0703.pdf"
    client = _AttemptPdfClient(
        {
            url: _AttemptPdfResponse(url, status_code=200, content=b"%PDF-" + (b"x" * 2000)),
        }
    )
    candidate = PdfCandidate(
        pdf_url=url,
        page_url="https://example.ac.jp/disclosure/",
        anchor_text="3．令和元年度確認申請書",
    )

    monkeypatch.setattr("eidp.scraper.pdf_discovery._is_safe_url", lambda _url: True)
    monkeypatch.setattr("eidp.scraper.pdf_discovery._extract_pdf_sample_text", lambda _content: "")

    file_path, file_hash, file_size, pdf_type, reason = download_pdf(
        client,
        candidate,
        tmp_path,
        school_id=1,
        target_fiscal_year=2026,
        strict_target_fiscal_year=True,
    )

    assert file_path is None
    assert file_hash is None
    assert file_size == 0
    assert pdf_type == "image_only"
    assert reason == "fiscal_year_mismatch:2019"
    assert not list((tmp_path / "1").glob("*.pdf"))


def test_download_pdf_rejects_stale_year_from_adjacent_html_context(
    monkeypatch, tmp_path: Path
) -> None:
    html = """
    <p><span>◆2025年度(令和7年度)</span></p>
    <p><a href="https://cdn.goope.jp/42190/250702074943-68646607e0c51.pdf">確認申請様式</a></p>
    """
    candidate = _extract_pdf_links(html, "https://r.goope.jp/penginweb/menu/c370087")[0]
    content = _make_pdf_bytes("高等教育の修学支援新制度 確認申請書 機関要件 学科名 生徒総定員")

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
    assert reason == "fiscal_year_mismatch:2025"
    assert not list((tmp_path / "1").glob("*.pdf"))


def test_extract_pdf_links_does_not_append_previous_year_when_anchor_has_year() -> None:
    html = """
    <p><a href="/docs/r6.pdf">9．令和6年度確認申請書</a></p>
    <p><a href="/docs/r7.pdf">10．令和7年度確認申請書</a></p>
    """

    candidates = _extract_pdf_links(html, "https://example.ac.jp/disclosure/")

    assert candidates[1].anchor_text == "10．令和7年度確認申請書"


def test_extract_pdf_links_does_not_mix_sibling_text_when_anchor_has_year() -> None:
    html = """
    <div class="linkBtn_item">
      <a href="/about/report/09_shugakushien_r6.pdf">R6修学支援に関する資料</a>
    </div>
    <div class="linkBtn_item">
      <a href="/about/report/09_shugakushien_r7.pdf">R7修学支援に関する資料</a>
    </div>
    <div class="linkBtn_item">
      <a href="/about/report/08_jitsumu.pdf">実務経験のある教員の授業一覧</a>
    </div>
    """

    candidates = _extract_pdf_links(html, "https://urasen.jp/")

    target = next(c for c in candidates if c.pdf_url.endswith("/about/report/09_shugakushien_r7.pdf"))
    assert target.anchor_text == "R7修学支援に関する資料"


def test_extract_pdf_links_uses_nearest_year_heading_for_first_list_item() -> None:
    html = """
    <h3>2026年度</h3>
    <ul>
      <li><a href="./ybc/2026/2026_syllabus.pdf">2026年度 授業概要（シラバス） [PDF]</a></li>
    </ul>
    <h3>2025年度</h3>
    <ul>
      <li><a href="./ybc/2025/2-1_2-4.pdf">様式第2号の1～4 [PDF]</a></li>
      <li><a href="./ybc/2025/2-4_bessi.pdf">様式第2号の4（別紙） [PDF]</a></li>
    </ul>
    """

    candidates = _extract_pdf_links(html, "https://aiko.ac.jp/data/")

    target = next(c for c in candidates if c.pdf_url.endswith("/ybc/2025/2-1_2-4.pdf"))
    assert "2025年度" in target.anchor_text
    assert "2026年度" not in target.anchor_text


def test_download_pdf_accepts_url_target_hint_when_body_is_target_form(
    monkeypatch, tmp_path: Path
) -> None:
    """URL/anchor year hints are enough to retain a body-confirmed target form."""

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

    assert file_path is not None
    assert file_hash is not None
    assert file_size > 1000
    assert pdf_type == "target"
    assert reason is None
    assert Path(file_path).is_file()
    assert candidate.detected_fiscal_year is None
    assert candidate.year_evidence == "url_hint"


def test_download_pdf_accepts_western_year_anchor_when_body_is_target_form(
    monkeypatch, tmp_path: Path
) -> None:
    """School sites often label confirmation forms as 2026年 rather than 2026年度."""

    content = _make_pdf_bytes("高等教育の修学支援新制度 確認申請書 機関要件 学科名 生徒総定員")
    candidate = PdfCandidate(
        pdf_url="https://example.ac.jp/kakunin-2026.pdf",
        page_url="https://example.ac.jp/disclosure/",
        anchor_text="2026年更新確認申請書",
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
    assert candidate.year_evidence == "url_hint"


def test_download_pdf_accepts_reiwa_year_anchor_when_body_is_target_form(
    monkeypatch, tmp_path: Path
) -> None:
    """令和8年更新確認申請書 is strong link evidence even without 年度."""

    content = _make_pdf_bytes("高等教育の修学支援新制度 確認申請書 機関要件 学科名 生徒総定員")
    candidate = PdfCandidate(
        pdf_url="https://example.ac.jp/kakunin-r8.pdf",
        page_url="https://example.ac.jp/disclosure/",
        anchor_text="令和8年更新確認申請書",
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
    assert candidate.year_evidence == "url_hint"


def test_download_pdf_accepts_trusted_prefecture_year_evidence_for_target_body(
    monkeypatch, tmp_path: Path
) -> None:
    """A current prefecture index can be year evidence when the PDF body is target."""

    content = _make_pdf_bytes("高等教育の修学支援新制度 確認申請書 機関要件 学科名 生徒総定員")
    candidate = PdfCandidate(
        pdf_url="https://example.ac.jp/files/study_support_system.pdf",
        page_url="https://example.ac.jp/admission/support.php",
        anchor_text="確認申請",
    )
    candidate.trusted_year_evidence = "prefecture_index_current_year"

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
    assert candidate.detected_fiscal_year is None
    assert candidate.year_evidence == "prefecture_index_current_year"


def test_download_pdf_rejects_vocational_practice_basic_info_even_with_trusted_year(
    monkeypatch, tmp_path: Path
) -> None:
    """別紙様式4 職業実践基本情報 is not the support-system confirmation form."""

    content = _make_pdf_bytes(
        "（別紙様式４）\n"
        "令和7年7月31日\n"
        "職業実践専門課程等の基本情報について\n"
        "学校名 設置認可年月日 校長名 所在地\n"
        "大宮スイーツ＆カフェ専門学校\n"
        "分野 認定課程名 認定学科名\n"
        "生徒総定員 生徒実員 学科名"
    )
    candidate = PdfCandidate(
        pdf_url="https://example.ac.jp/disclosure/shokugyouzissen_sweets_patissier_.pdf",
        page_url="https://example.ac.jp/disclosure/",
        anchor_text="職業実践専門課程等の基本情報",
    )
    candidate.trusted_year_evidence = "prefecture_index_current_year"

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
    assert pdf_type == "non_target"
    assert reason == "classified_non_target"


def test_download_pdf_rejects_url_target_hint_when_body_is_not_target_form(
    monkeypatch, tmp_path: Path
) -> None:
    """R8 in the URL is not enough for student forms, syllabi, or other PDFs.

    Non-target bodies must be classified as non-target instead of inflating the
    strict target-year rejection bucket.
    """

    content = _make_pdf_bytes("大学等における修学の支援に関する法律による 授業料等減免 A様式1 申請者")
    candidate = PdfCandidate(
        pdf_url="https://example.ac.jp/2026/applicationform-r8.pdf",
        page_url="https://example.ac.jp/disclosure/",
        anchor_text="令和8年度 授業料等減免申請書",
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
    assert pdf_type == "non_target"
    assert reason == "classified_non_target"
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
    assert candidate.detected_fiscal_year == 2026
    assert candidate.year_evidence == "pdf_text"


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

        def fake_discover(_client, school_id: int, _url: str, **_kwargs: object) -> DiscoveryResult:
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


def test_run_pdf_discovery_records_duplicate_when_file_hash_insert_races(
    monkeypatch, tmp_path: Path
) -> None:
    session = _session()
    evidence = tmp_path / "rejections.jsonl"
    duplicate_pdf = tmp_path / "candidate.pdf"
    duplicate_pdf.write_bytes(b"%PDF-" + b"x" * 2000)
    try:
        session.add(SchoolSite(school_id=1, url="https://example.ac.jp/disclosure/", http_status=200))
        session.flush()

        candidate = PdfCandidate(
            pdf_url="https://example.ac.jp/r8.pdf",
            page_url="https://example.ac.jp/disclosure/",
            anchor_text="令和8年度 確認申請書",
            score=10.0,
        )

        def fake_discover(_client, school_id: int, _url: str, **_kwargs: object) -> DiscoveryResult:
            return DiscoveryResult(school_id=school_id, candidates=[candidate], best=candidate)

        def fake_download(_client, _candidate: PdfCandidate, _storage_dir: Path, _school_id: int):
            return str(duplicate_pdf), "racehash", 2005, "target", None

        real_flush = session.flush

        def race_flush(*args: object, **kwargs: object) -> None:
            from sqlalchemy.exc import IntegrityError

            if any(isinstance(obj, Document) and obj.file_hash == "racehash" for obj in session.new):
                raise IntegrityError("INSERT INTO document", {}, RuntimeError("unique file_hash"))
            real_flush(*args, **kwargs)

        monkeypatch.setattr("eidp.scraper.pdf_discovery.discover_pdfs_for_site", fake_discover)
        monkeypatch.setattr("eidp.scraper.pdf_discovery.download_pdf", fake_download)
        monkeypatch.setattr(session, "flush", race_flush)

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
        assert session.query(Document).count() == 0
        job = session.query(CrawlJob).one()
        assert job.status == "review"
        assert "duplicates" in (job.error_message or "")
        assert not duplicate_pdf.exists()
        payload = json.loads(evidence.read_text(encoding="utf-8").strip())
        assert payload["reason"] == "duplicate_hash_integrity_error"
        assert payload["extra"]["integrity_error"] == "true"
    finally:
        session.close()
