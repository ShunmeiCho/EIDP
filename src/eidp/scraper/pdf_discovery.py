"""PDF discovery + download — Step 8.

Crawls school disclosure pages, finds target PDF links using 4 patterns,
scores candidates, downloads best match, stores in document table.

5 delivery patterns (verified from reference sites):
1. Direct PDF links: a[href$=".pdf"]
2. WordPress asset: a[href*="/wp-content/"] + .pdf
3. Cache-busted: a[href*=".pdf?"]
4. WordPress Download Manager wrappers: a[href*="?wpdmdl="]
5. Two-tier embed: subpage -> embed[src*=".pdf"]
"""

import hashlib
import html as html_lib
import re
import time
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Protocol, cast
from urllib.parse import parse_qsl, unquote, urljoin, urlparse

import httpx
import structlog
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from eidp.config import settings
from eidp.db.models import CrawlJob, Document, SchoolSite
from eidp.fiscal_year import current_fiscal_year, fiscal_year_from_japanese_era_text, fiscal_year_search_tokens
from eidp.scraper.discovery_evidence import EvidenceRecorder, RejectionEvidence
from eidp.scraper.url_discovery import _is_safe_url
from eidp.scraper.url_normalization import normalize_candidate_url

log = structlog.get_logger()

PdfDiscoveryProgressCallback = Callable[[dict[str, int], int], None]


def _safe_get(client: httpx.Client, url: str, **kwargs: Any) -> httpx.Response:
    """GET with manual redirect following + SSRF check on each hop.

    Raises httpx.HTTPStatusError on SSRF-blocked redirect or redirect loop.
    Fails closed: if max hops exceeded, raises instead of returning last 3xx.
    """
    resp = client.get(url, **kwargs)
    visited = {url}
    for _ in range(5):
        if resp.status_code not in (301, 302, 303, 307, 308):
            return resp
        location = resp.headers.get("location", "")
        if not location:
            return resp
        location = urljoin(str(resp.url), location)
        if location in visited:
            log.warning("redirect_loop", url=location, origin=url)
            raise httpx.HTTPStatusError(
                "Redirect loop detected", request=resp.request, response=resp
            )
        if not _is_safe_url(location):
            log.warning("ssrf_blocked_redirect", url=location, origin=url)
            raise httpx.HTTPStatusError(
                "SSRF blocked redirect", request=resp.request, response=resp
            )
        visited.add(location)
        resp = client.get(location, **kwargs)
    # Max hops exceeded — fail closed
    log.warning("redirect_max_hops", url=url, hops=5)
    raise httpx.HTTPStatusError(
        "Too many redirects", request=resp.request, response=resp
    )


def _origin_root_url(url: str) -> str | None:
    """Return the same-origin root URL when ``url`` points below root."""

    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    if parsed.path in {"", "/"} and not parsed.query and not parsed.fragment:
        return None
    return f"{parsed.scheme}://{parsed.netloc}/"


def _main_page_response_with_root_fallback(client: httpx.Client, site_url: str) -> tuple[httpx.Response, str]:
    """Fetch the registered page, falling back to origin root for stale 404 paths."""

    resp = _safe_get(client, site_url)
    try:
        resp.raise_for_status()
        final_url = str(resp.url or site_url)
        content_type = resp.headers.get("content-type", "").split(";", 1)[0].strip().lower()
        if content_type and content_type not in {"text/html", "application/xhtml+xml", "application/pdf"}:
            root_url = _origin_root_url(final_url)
            if root_url is not None and _is_safe_url(root_url):
                root_resp = _safe_get(client, root_url)
                root_resp.raise_for_status()
                log.info(
                    "pdf_discovery_root_fallback",
                    original_url=site_url,
                    fallback_url=root_url,
                    content_type=content_type,
                )
                return root_resp, str(root_resp.url or root_url)
        return resp, final_url
    except httpx.HTTPStatusError as exc:
        status_code = exc.response.status_code if exc.response is not None else 0
        if status_code not in {404, 410}:
            raise
        root_url = _origin_root_url(site_url)
        if root_url is None or not _is_safe_url(root_url):
            raise
        root_resp = _safe_get(client, root_url)
        root_resp.raise_for_status()
        log.info("pdf_discovery_root_fallback", original_url=site_url, fallback_url=root_url, status_code=status_code)
        return root_resp, str(root_resp.url or root_url)


# Keywords that indicate the target document (高等教育修学支援新制度 確認申請書)
POSITIVE_KEYWORDS = [
    "修学支援", "高等教育", "無償化", "確認申請", "機関要件",
    "様式第2号", "様式2", "学校教育法", "情報公開",
]

NEGATIVE_KEYWORDS = [
    "シラバス", "syllabus", "募集要項", "パンフレット",
    "入学案内", "カリキュラム", "時間割",
    "規程", "規則", "規定", "就業規則", "学則",
    "事業計画", "事業報告", "財務諸表", "決算",
    "自己点検", "自己評価", "学校案内", "ガイドブック",
    "attachment", "appendix", "添付資料", "別紙", "bessi", "besshi",
]

PRE_DOWNLOAD_NEGATIVE_TOKENS = (
    "実務経験",
    "授業科目",
    "jitsumukeiken",
    "course-subject",
    "course_subject",
    "curriculum",
    "財務",
    "zaimu",
    "理事名簿",
    "rijimeibo",
    "役員名簿",
    "yakuinmeibo",
    "役員一覧",
    "executive-list",
    "executive_list",
    "board-member",
    "board_member",
    "学校情報",
    "学校紹介",
    "学校案内",
    "school-info",
    "schoolinfo",
    "gakkouinfo",
    "school-guide",
    "schoolguide",
    "学校評価",
    "gakkouuneihyouka",
    "学校関係者評価",
    "kankeishahyouka",
    "職業実践",
    "shokugyouzissen",
    "shokugyojissen",
    "外部評価",
    "gaibuhyouka",
    "内部評価",
    "naibuhyouka",
    "自己点検",
    "自己評価",
    "jikohyoka",
    "evaluation",
    "hyoukahokoku",
    "daigakuhyouka",
    "客観的指標",
    "kyakkantekishihyo",
    "シラバス",
    "syllabus",
    "卒業認定",
    "卒業の認定",
    "sotugyo",
    "sotsugyo",
    "graduation",
    "成績評価",
    "grading",
    "給付金",
    "kyufukin",
    "学校の現況",
    "gakkou_genjyou",
    "gakkou_genjo",
    "諸心得",
    "knowledge",
)

# User-Agent mimicking a real browser (institutional research)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) EIDP-DataCollector/1.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ja,en;q=0.5",
}

MAX_CANDIDATE_DOWNLOAD_ATTEMPTS = 10
PREFECTURE_INDEX_TRUST_MAX_AGE_DAYS = 370
MAX_DISCOVERY_EXTRA_PAGES = 6
SITEMAP_DISCOVERY_RESERVED_PAGES = 2
MAX_DISCOVERY_ELAPSED_SECONDS = 45.0
MAX_RENDERED_DISCOVERY_PAGES = 3
SITEMAP_PAGE_KEYWORDS = (
    "disclosure",
    "public",
    "public_info",
    "info",
    "information",
    "koukai",
    "joho",
    "jyoho",
    "kakunin",
    "shugaku",
    "syugaku",
    "support",
    "school-support",
    "kikanyouken",
    "valuation",
    "情報公開",
    "公開情報",
    "修学支援",
    "高等教育",
    "無償化",
    "機関要件",
)
DERIVED_DISCLOSURE_PATHS = (
    "/disclosure/{slug}",
    "{path}/information",
    "{path}/school-support",
    "{path}/guidelines",
    "{path}/disclosure",
    "{path}/public",
    "{path}/public_info",
    "/information/",
    "/school-support/",
    "/disclosure/",
    "/guidelines/",
    "/public/",
    "/public_info/",
)


@dataclass
class PdfCandidate:
    pdf_url: str
    page_url: str
    anchor_text: str = ""
    pattern_type: str = ""  # direct, wordpress, cache_busted, wordpress_download_manager, embed
    score: float = 0.0
    detected_fiscal_year: int | None = None
    year_evidence: str = ""
    trusted_year_evidence: str = ""


@dataclass
class DiscoveryResult:
    school_id: int
    candidates: list[PdfCandidate] = field(default_factory=list)
    best: PdfCandidate | None = None
    downloaded_path: str | None = None
    file_hash: str | None = None
    file_size: int = 0
    error: str | None = None


@dataclass(frozen=True)
class CachedPdfRejection:
    pdf_type: str
    reason: str


class RenderedHtmlFetcher(Protocol):
    def fetch_html(self, url: str) -> str | None: ...


def _is_target_year_rejection(reason: str) -> bool:
    return reason == "target_fiscal_year_not_detected" or reason.startswith("fiscal_year_mismatch:")


def _is_cacheable_pdf_rejection(pdf_type: str, reason: str | None) -> bool:
    """Return whether a rejected candidate is deterministic enough to reuse.

    Do not cache HTTP failures: those are often transient. Cache content-based
    decisions so corporation/common disclosure pages do not download and parse
    the same stale PDF once per school.
    """
    if reason is None:
        return False
    if pdf_type == "non_target":
        return True
    if _is_target_year_rejection(reason):
        return True
    return reason in {
        "not_pdf_magic",
        "target_fiscal_year_not_detected",
        "too_large_body",
        "too_large_header",
        "too_small",
        "target_application_not_detected",
        "unsafe_resolved_url",
        "unsafe_url",
    }


def _rejection_reason_stat_key(reason: str) -> str:
    """Return the stable stats key used for operator-facing rejection counts."""
    normalized = (reason or "unknown").strip() or "unknown"
    if normalized.startswith("fiscal_year_mismatch:"):
        normalized = "fiscal_year_mismatch"
    normalized = re.sub(r"[^0-9A-Za-z_]+", "_", normalized).strip("_").lower()
    return f"rejection_reason_{normalized or 'unknown'}"


def _increment_rejection_reason(stats: dict[str, int], reason: str) -> None:
    if reason == "accepted_downloaded":
        return
    key = _rejection_reason_stat_key(reason)
    stats[key] = int(stats.get(key, 0)) + 1


def _rejection_cache_key(
    candidate_url: str,
    *,
    target_year: int,
    strict_target_fiscal_year: bool,
    trusted_year_evidence: str = "",
) -> tuple[str, int | None, bool, str]:
    attempt_urls = _download_attempt_urls(candidate_url)
    canonical_url = attempt_urls[0] if attempt_urls else candidate_url
    return (
        canonical_url,
        target_year if strict_target_fiscal_year else None,
        strict_target_fiscal_year,
        trusted_year_evidence if strict_target_fiscal_year else "",
    )


def _trusted_year_evidence_for_site(site: SchoolSite) -> str:
    """Return trusted current-year evidence supplied by the registered site source.

    Prefecture official indexes are current target-year artifacts in the
    packaged seed. If such an index points at a school's disclosure page and
    the PDF body is a target confirmation form, the index itself can prove the
    year when the school omits year labels from the PDF/link text.
    """
    if (
        site.discovery_method == "prefecture_aggregator"
        and site.url_type == "disclosure"
        and _has_recent_prefecture_index_refresh(site)
    ):
        return "prefecture_index_current_year"
    return ""


def _has_recent_prefecture_index_refresh(site: SchoolSite, *, now: datetime | None = None) -> bool:
    """Return whether a prefecture-derived SchoolSite was freshly refreshed.

    The prefecture index can prove the target year only when the row comes from
    the current bootstrap/weekly artifact refresh. Stale rows remain useful as
    crawl URLs, but they cannot silently turn a yearless target-form body into
    current-FY success.
    """
    timestamp = site.verified_at
    if timestamp is None:
        return False
    now = now or datetime.now(UTC)
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=UTC)
    return timedelta(0) <= now - timestamp <= timedelta(days=PREFECTURE_INDEX_TRUST_MAX_AGE_DAYS)


def _candidate_hint_text(candidate: PdfCandidate) -> str:
    return unicodedata.normalize(
        "NFKC",
        f"{candidate.anchor_text} {candidate.pdf_url} {unquote(candidate.pdf_url)}",
    )


def _fiscal_year_from_strong_candidate_hint(text: str, *, target_year: int) -> int | None:
    text = unicodedata.normalize("NFKC", text)
    detected = fiscal_year_from_japanese_era_text(
        text,
        include_fiscal_year_labels=True,
        include_filing_dates=False,
    )
    if detected is not None:
        return detected

    western = re.search(r"(?<!\d)(20\d{2})\s*年度", text)
    if western is not None:
        return int(western.group(1))

    strong_form_context = any(
        token in text
        for token in (
            "確認申請",
            "更新確認申請",
            "機関要件",
            "様式第2号",
            "様式第２号",
            "様式2号",
        )
    )
    if strong_form_context:
        western_year = re.search(r"(?<!\d)(20\d{2})\s*年(?!\s*度)", text)
        if western_year is not None:
            return int(western_year.group(1))
        filename_year = re.search(r"(?<!\d)(20\d{2})(?!\d)", text)
        if filename_year is not None:
            return int(filename_year.group(1))
        serial_filename_year = re.search(r"(?<!\d)(20\d{2})(?=\d{2,4}[^/\s]*\.pdf\b)", text, re.IGNORECASE)
        if serial_filename_year is not None:
            return int(serial_filename_year.group(1))
        era_year = fiscal_year_from_japanese_era_text(
            text,
            include_fiscal_year_labels=False,
            include_filing_dates=True,
        )
        if era_year is not None:
            return era_year

    lowered = text.lower()
    for year in range(target_year - 8, target_year + 3):
        for token in fiscal_year_search_tokens(year):
            if token == str(year):
                continue
            token_lower = token.lower()
            if token_lower.startswith("r"):
                pattern = rf"(?<![a-z0-9]){re.escape(token_lower)}(?![a-z0-9])"
                if re.search(pattern, lowered):
                    return year
            elif token_lower in lowered:
                return year
    return None


def _stale_fiscal_year_from_candidate_hint(candidate: PdfCandidate, *, target_year: int) -> int | None:
    """Return a past year from URL/anchor hints for rejection diagnostics only."""

    if _has_target_year_hint(candidate, target_year=target_year):
        return None

    text = _candidate_hint_text(candidate)
    detected_year = _fiscal_year_from_strong_candidate_hint(text, target_year=target_year)
    if detected_year is not None and target_year - 8 <= detected_year < target_year:
        return detected_year
    for match in re.finditer(r"(?<!\d)(20\d{2})(?!\d)", text):
        year = int(match.group(1))
        if target_year - 8 <= year < target_year:
            return year
    return None


def _pre_download_rejection(candidate: PdfCandidate, *, target_year: int) -> CachedPdfRejection | None:
    """Reject adjacent disclosure PDFs that are clearly not current target forms."""

    text = _candidate_hint_text(candidate)
    lowered = text.lower()
    detected_year = _fiscal_year_from_strong_candidate_hint(text, target_year=target_year)
    if detected_year is not None and detected_year != target_year and _has_target_application_hint(candidate):
        return CachedPdfRejection(
            pdf_type="target",
            reason=f"fiscal_year_mismatch:{detected_year}",
        )
    if _has_target_application_hint(candidate):
        return None
    if any(token.lower() in lowered for token in PRE_DOWNLOAD_NEGATIVE_TOKENS):
        return CachedPdfRejection(
            pdf_type="non_target",
            reason="pre_filtered_non_target_hint",
        )
    return None


def _has_target_application_hint(candidate: PdfCandidate) -> bool:
    """Return whether link text/URL strongly names the target application form."""

    text = _candidate_hint_text(candidate).lower()
    system_hint = any(token in text for token in ("修学支援", "修学の支援", "高等教育", "無償化"))
    form_hint = any(token in text for token in ("確認申請", "申請書", "様式第2号", "様式第２号", "様式2号", "機関要件"))
    full_form_range_hint = re.search(r"様式第[2２]号の?[1１]\s*[〜～~\-－−ー―]\s*[4４]", text) is not None
    renewal_form_hint = any(
        token in text
        for token in (
            "更新確認申請",
            "koushinshinsei",
            "koushin-shinsei",
        )
    )
    english_renewal_form_hint = any(
        token in text
        for token in (
            "renewalconfirmationapplication",
            "renewal-confirmation-application",
            "renewal confirmation application",
        )
    )
    strong_form_hint = "機関要件" in text and any(
        token in text for token in ("確認申請", "様式第2号", "様式第２号", "様式2号")
    )
    return (
        (system_hint and form_hint)
        or full_form_range_hint
        or renewal_form_hint
        or (system_hint and english_renewal_form_hint)
        or strong_form_hint
    )


def _has_target_year_hint(candidate: PdfCandidate, *, target_year: int) -> bool:
    """Return whether URL/anchor text explicitly names the target fiscal year."""
    return _fiscal_year_from_strong_candidate_hint(
        _candidate_hint_text(candidate),
        target_year=target_year,
    ) == target_year


def _score_candidate(candidate: PdfCandidate, *, target_fiscal_year: int | None = None) -> float:
    """Score a PDF candidate by keyword relevance."""
    score = 0.0
    text = (candidate.anchor_text + " " + candidate.pdf_url).lower()
    target_year = target_fiscal_year or settings.target_fiscal_year

    for kw in POSITIVE_KEYWORDS:
        if kw.lower() in text:
            score += 2.0

    for kw in NEGATIVE_KEYWORDS:
        if kw.lower() in text:
            score -= 3.0

    # Bonus for configured target-year references. EIDP is a rolling
    # target-fiscal-year system, not a single Reiwa-year crawler.
    if any(token.lower() in text for token in fiscal_year_search_tokens(target_year)):
        score += 3.0
    if any(token.lower() in text for token in fiscal_year_search_tokens(target_year - 1)):
        score += 1.0

    # Bonus for pattern type reliability
    if candidate.pattern_type == "direct":
        score += 0.5
    elif candidate.pattern_type == "embed":
        score += 0.3

    candidate.score = score
    return score


def _extract_pdf_sample_text(content: bytes) -> str:
    """Extract a small text sample from the first pages of a PDF."""
    import io

    import pdfplumber

    with pdfplumber.open(io.BytesIO(content)) as pdf:
        sample_text = ""
        for page in pdf.pages[:5]:
            sample_text += (page.extract_text() or "") + "\n"
    return sample_text


_FILING_DATE_CONTEXT_RE = re.compile(r"(提出日|提出年月日|申請日|申請年月日|届出日|届出年月日|作成日|作成年月日)")
_FILING_DATE_REJECT_CONTEXT_RE = re.compile(r"(から|まで|任期|期間|在任|現職|前職|卒業|終了|修了)")
_YEAR_LABEL_REJECT_CONTEXT_RE = re.compile(
    r"(完成年度|から|まで|任期|期間|在任|現職|前職|卒業|終了|修了|就職|進学|退学)"
)


def _within_detectable_year(fiscal_year: int | None, max_fiscal_year: int | None) -> int | None:
    if fiscal_year is None:
        return None
    if max_fiscal_year is not None and fiscal_year > max_fiscal_year:
        return None
    return fiscal_year


def _detect_contextual_filing_year(normed_text: str, *, max_fiscal_year: int | None) -> int | None:
    """Return a filing-date year only when the local line clearly describes filing.

    Target application PDFs often carry a cover-page filing date, but the same
    PDFs also contain future dates for officer terms or accreditation periods.
    Treating every era date as the document year makes valid older PDFs look
    like impossible future-year PDFs, so this fallback accepts only dated lines
    with explicit filing context.
    """
    for line in normed_text.splitlines():
        if not _FILING_DATE_CONTEXT_RE.search(line):
            continue
        if _FILING_DATE_REJECT_CONTEXT_RE.search(line):
            continue
        fiscal_year = fiscal_year_from_japanese_era_text(
            line,
            include_fiscal_year_labels=False,
            include_filing_dates=True,
        )
        fiscal_year = _within_detectable_year(fiscal_year, max_fiscal_year)
        if fiscal_year is not None:
            return fiscal_year
    return None


def _detect_explicit_fiscal_year_label(normed_text: str, *, max_fiscal_year: int | None) -> int | None:
    """Return an explicit fiscal-year label unless its local line is a non-filing year."""

    for line in normed_text.splitlines():
        if _YEAR_LABEL_REJECT_CONTEXT_RE.search(line):
            continue
        fiscal_year = fiscal_year_from_japanese_era_text(
            line,
            include_fiscal_year_labels=True,
            include_filing_dates=False,
        )
        fiscal_year = _within_detectable_year(fiscal_year, max_fiscal_year)
        if fiscal_year is not None:
            return fiscal_year

        for match in re.finditer(r"(20\d{2})\s*年度", line):
            fiscal_year = _within_detectable_year(int(match.group(1)), max_fiscal_year)
            if fiscal_year is not None:
                return fiscal_year
    return None


def _detect_fiscal_year_from_text(text: str, *, max_fiscal_year: int | None = None) -> int | None:
    """Best-effort fiscal-year detector for disclosure PDFs."""
    normed = unicodedata.normalize("NFKC", text)

    # Prefer explicit fiscal-year labels over filing dates.
    fiscal_year = _detect_explicit_fiscal_year_label(normed, max_fiscal_year=max_fiscal_year)
    if fiscal_year is not None:
        return fiscal_year

    # Most application forms carry a filing date on the cover page. In this
    # domain that date is useful only when the surrounding text says it is a
    # filing/submission date; future term dates are not fiscal-year evidence.
    fiscal_year = _detect_contextual_filing_year(normed, max_fiscal_year=max_fiscal_year)
    if fiscal_year is not None:
        return fiscal_year

    return None


def _classify_pdf_sample_text(sample_text: str) -> str:
    """Classify a PDF body sample as ``target`` / ``non_target`` / ``image_only``.

    Marker check beats the cid-leak heuristic: real Japanese 申請書 PDFs
    routinely contain ``(cid:1234)`` glyph fallbacks alongside extractable
    ``様式第2号`` etc. text, and rejecting them as ``image_only`` would
    silently drop legitimate target documents from the queue.
    """
    if not sample_text.strip():
        return "image_only"

    normed = unicodedata.normalize("NFKC", sample_text)
    strong_target_markers = ("確認申請", "機関要件", "修学支援", "修学の支援", "高等教育", "無償化")
    vocational_practice_basic_info = (
        "職業実践専門課程等の基本情報" in normed
        or "職業実践専門課程の基本情報" in normed
        or "別紙様式4" in normed
        or "別紙様式４" in normed
    )
    if vocational_practice_basic_info and not any(marker in normed for marker in strong_target_markers):
        return "non_target"

    target_markers = ["様式第2号", "機関要件", "修学支援", "生徒総定員", "学科名"]
    hits = sum(1 for m in target_markers if m in normed)
    if hits >= 2:
        return "target"

    if "(cid:" in sample_text:
        return "image_only"
    return "non_target"


def _pdf_candidate_dedupe_key(url: str) -> str:
    """Return a stable key for duplicate PDF links without changing download URL."""

    normalized = normalize_candidate_url(url)
    parsed = urlparse(normalized)
    if not parsed.scheme or not parsed.netloc:
        return normalized
    return parsed._replace(path=unquote(parsed.path)).geturl()


def _html_text(fragment: str) -> str:
    text = html_lib.unescape(re.sub(r"<[^>]+>", " ", fragment))
    return re.sub(r"\s+", " ", text).strip()


def _enclosing_html_block(html: str, start: int, end: int) -> tuple[str, int, int, str] | None:
    """Return the closest simple HTML block containing an anchor match."""

    prefix = html[:start]
    for tag in ("p", "li", "tr"):
        open_matches = list(re.finditer(rf"<{tag}\b[^>]*>", prefix, re.IGNORECASE))
        if not open_matches:
            continue
        open_match = open_matches[-1]
        if re.search(rf"</{tag}\s*>", prefix[open_match.end():], re.IGNORECASE):
            continue
        close_match = re.search(rf"</{tag}\s*>", html[end:], re.IGNORECASE)
        if close_match is None:
            continue
        close_end = end + close_match.end()
        return tag, open_match.start(), close_end, html[open_match.start():close_end]
    return None


def _previous_html_block_text(html: str, before: int, tag: str) -> str:
    previous_blocks = list(
        re.finditer(rf"<{tag}\b[^>]*>.*?</{tag}\s*>", html[:before], re.IGNORECASE | re.DOTALL)
    )
    for previous in reversed(previous_blocks):
        text = _html_text(previous.group(0))
        if text:
            return text
    return ""


def _has_fiscal_year_context(text: str) -> bool:
    normalized = unicodedata.normalize("NFKC", text)
    return bool(re.search(r"(令和\s*\d+|20\d{2}\s*年度|(?<![a-z0-9])r0?\d{1,2}(?![a-z0-9]))", normalized.lower()))


def _pdf_anchor_context_text(html: str, match: re.Match[str]) -> str:
    """Return anchor text plus nearby fiscal-year context when the CMS splits it.

    Some CMS pages, notably Goope, render a year header in one paragraph and the
    PDF link in the next paragraph. Keeping that adjacent context lets strict
    discovery classify old target forms as publication-lag evidence instead of
    sending them to the target-year-unverified manual queue.
    """

    anchor = _html_text(match.group(2))
    parts = [anchor] if anchor else []
    block = _enclosing_html_block(html, match.start(), match.end())
    if block is not None:
        tag, block_start, _, block_fragment = block
        current_text = _html_text(block_fragment)
        if current_text and _has_fiscal_year_context(current_text) and current_text not in parts:
            parts.append(current_text)
        previous_text = (
            _previous_fiscal_year_context(html, block_start)
            if tag == "li"
            else _previous_html_block_text(html, block_start, tag)
        )
        has_current_year_context = any(_has_fiscal_year_context(part) for part in parts)
        if previous_text and not has_current_year_context and _has_fiscal_year_context(previous_text):
            parts.append(previous_text)
    elif previous_text := _previous_fiscal_year_context(html, match.start()):
        parts.append(previous_text)
    return " ".join(dict.fromkeys(part for part in parts if part))


def _previous_fiscal_year_context(html: str, before: int) -> str:
    """Return nearby preceding year context for CMS download widgets."""

    window = html[max(0, before - 2000):before]
    block_re = r"<(?:p|li|dt|dd|h[1-6])\b[^>]*>.*?</(?:p|li|dt|dd|h[1-6])\s*>"
    for match in reversed(list(re.finditer(block_re, window, re.IGNORECASE | re.DOTALL))):
        text = _html_text(match.group(0))
        if text and _has_fiscal_year_context(text):
            return text

    text = _html_text(window)
    for line in reversed(re.split(r"[\n。]+", text)):
        line = line.strip()
        if line and _has_fiscal_year_context(line):
            return line
    return ""


def _anchor_attr(attrs: str, name: str) -> str | None:
    match = re.search(rf"\b{re.escape(name)}\s*=\s*([\"'])(.*?)\1", attrs, re.IGNORECASE | re.DOTALL)
    if match is None:
        return None
    return html_lib.unescape(match.group(2))


def _is_wordpress_download_manager_url(url: str, base_url: str) -> bool:
    """Return whether ``url`` is a same-origin WordPress Download Manager PDF wrapper."""

    parsed = urlparse(url)
    base_parsed = urlparse(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return False
    if parsed.netloc != base_parsed.netloc:
        return False
    return any(key.lower() == "wpdmdl" and value.strip() for key, value in parse_qsl(parsed.query))


def _extract_pdf_links(html: str, base_url: str) -> list[PdfCandidate]:
    """Extract PDF link candidates from HTML using known PDF delivery patterns."""
    candidates: list[PdfCandidate] = []
    seen_urls: set[str] = set()

    # Pattern 1: Direct PDF links — a[href*=".pdf"]
    for m in re.finditer(
        r'<a\s[^>]*href=["\']([^"\']*\.pdf(?:\?[^"\']*)?)["\'][^>]*>(.*?)</a>',
        html, re.IGNORECASE | re.DOTALL,
    ):
        href = html_lib.unescape(m.group(1))
        url = urljoin(base_url, href)
        dedupe_key = _pdf_candidate_dedupe_key(url)
        if dedupe_key not in seen_urls:
            seen_urls.add(dedupe_key)
            anchor = _pdf_anchor_context_text(html, m)
            pattern = "cache_busted" if "?" in href else "direct"
            if "/wp-content/" in url:
                pattern = "wordpress"
            candidates.append(PdfCandidate(
                pdf_url=url, page_url=base_url, anchor_text=anchor, pattern_type=pattern,
            ))

    # Pattern 2b: WordPress Download Manager wrappers.
    #
    # These URLs do not contain ".pdf", but the wrapper returns a PDF when the
    # ``wpdmdl`` query parameter is present.
    for m in re.finditer(
        r"<a\s([^>]*)>(.*?)</a>",
        html, re.IGNORECASE | re.DOTALL,
    ):
        href = _anchor_attr(m.group(1), "data-downloadurl") or _anchor_attr(m.group(1), "href")
        if not href:
            continue
        url = urljoin(base_url, href)
        if not _is_wordpress_download_manager_url(url, base_url):
            continue
        dedupe_key = _pdf_candidate_dedupe_key(url)
        if dedupe_key not in seen_urls:
            seen_urls.add(dedupe_key)
            candidates.append(PdfCandidate(
                pdf_url=url,
                page_url=base_url,
                anchor_text=_pdf_anchor_context_text(html, m),
                pattern_type="wordpress_download_manager",
            ))

    # Pattern 4: Embedded PDFs — embed/object/iframe with .pdf src
    for tag in ("embed", "object", "iframe"):
        for attr in ("src", "data"):
            for m in re.finditer(
                rf'<{tag}\s[^>]*{attr}=["\']([^"\']*\.pdf(?:\?[^"\']*)?)["\']',
                html, re.IGNORECASE,
            ):
                href = html_lib.unescape(m.group(1))
                url = urljoin(base_url, href)
                dedupe_key = _pdf_candidate_dedupe_key(url)
                if dedupe_key not in seen_urls:
                    seen_urls.add(dedupe_key)
                    candidates.append(PdfCandidate(
                        pdf_url=url, page_url=base_url, anchor_text="", pattern_type="embed",
                    ))

    return candidates


def _pdf_url_from_query_value(url: str) -> str | None:
    """Resolve download-wrapper URLs whose query contains the real PDF path.

    Tokyo Metropolitan University exposes links like
    ``/extra/download.html?dd=assets%2F...%2Ffile.pdf``. The wrapper returns
    HTML, while the query value points to the actual PDF on the same host.
    """
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc or ".pdf" not in parsed.query.lower():
        return None

    base = f"{parsed.scheme}://{parsed.netloc}/"
    for _key, value in parse_qsl(parsed.query, keep_blank_values=True):
        decoded = unquote(value).strip()
        if ".pdf" not in decoded.lower():
            continue
        if not decoded.startswith(("http://", "https://", "/")) and "/" not in decoded:
            continue
        candidate_url = urljoin(base, decoded.lstrip("/"))
        if _is_safe_url(candidate_url):
            return candidate_url
    return None


def _download_attempt_urls(url: str) -> list[str]:
    """Return candidate download URLs, preferring resolved direct PDFs."""
    urls: list[str] = []
    resolved = _pdf_url_from_query_value(url)
    if resolved:
        urls.append(resolved)
    if url not in urls:
        urls.append(url)
    return urls


def _find_subpage_links(html: str, base_url: str, *, school_name: str = "") -> list[str]:
    """Find disclosure subpage links to follow (two-tier pattern)."""
    subpages: list[tuple[int, int, str]] = []
    seen: set[str] = set()
    keywords = [
        "情報公開",
        "公開情報",
        "教育情報",
        "公表",
        "修学支援",
        "高等教育",
        "無償化",
        "確認申請",
        "申請様式",
        "機関要件",
        "youshiki",
        "disclosure",
        "public",
        "public_info",
        "arbitrary-matter",
        "kyouikujouhou",
        "kikanyouken",
        "valuation",
    ]

    for m in re.finditer(
        r'<a\s[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
        html, re.IGNORECASE | re.DOTALL,
    ):
        href = html_lib.unescape(m.group(1))
        text = html_lib.unescape(re.sub(r"<[^>]+>", "", m.group(2))).strip()
        haystack = f"{text} {href}".lower()

        if any(kw.lower() in haystack for kw in keywords):
            url = urljoin(base_url, href)
            parsed = urlparse(url)
            if parsed.path.lower().endswith(".pdf"):
                continue
            base_parsed = urlparse(base_url)
            # Only follow links on the same domain
            if (parsed.netloc == base_parsed.netloc or not parsed.netloc) and url not in seen:
                seen.add(url)
                priority = 0 if school_name and _school_name_matches_link(f"{text} {href}", school_name) else 1
                subpages.append((priority, len(subpages), url))

    subpages.sort()
    return [url for _, _, url in subpages[:12]]  # Keep bounded while covering dense institutional navs.


_EXTERNAL_SCHOOL_LINK_BLOCKED_HOST_PARTS = (
    "facebook.",
    "instagram.",
    "youtube.",
    "youtu.be",
    "x.com",
    "twitter.",
    "line.me",
    "google.",
)


def _school_link_label(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text).lower()
    normalized = normalized.replace("専門学校", "")
    return re.sub(r"[\s　・･\-ー–—_/／|｜()（）［］\\[\\]{}]+", "", normalized)


def _school_name_matches_link(text: str, school_name: str) -> bool:
    school_label = _school_link_label(school_name)
    link_label = _school_link_label(text)
    return len(school_label) >= 4 and school_label in link_label


def _find_school_homepage_links(html: str, base_url: str, school_name: str, *, limit: int = 3) -> list[str]:
    """Find school-named external homepage links from umbrella/corporation roots."""

    if not school_name or limit <= 0:
        return []

    base_parsed = urlparse(base_url)
    links: list[str] = []
    seen: set[str] = set()
    for m in re.finditer(
        r'<a\s[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
        html,
        re.IGNORECASE | re.DOTALL,
    ):
        href = html_lib.unescape(m.group(1))
        if href.lower().endswith(".pdf"):
            continue
        text = html_lib.unescape(re.sub(r"<[^>]+>", "", m.group(2))).strip()
        if not _school_name_matches_link(f"{text} {href}", school_name):
            continue
        url = urljoin(base_url, href)
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            continue
        if parsed.netloc == base_parsed.netloc:
            continue
        if any(blocked in parsed.netloc.lower() for blocked in _EXTERNAL_SCHOOL_LINK_BLOCKED_HOST_PARTS):
            continue
        key = normalize_candidate_url(url)
        if key in seen or not _is_safe_url(url):
            continue
        seen.add(key)
        links.append(url)
        if len(links) >= limit:
            break
    return links


def _derived_disclosure_page_urls(site_url: str, *, limit: int = 6) -> list[str]:
    """Return conservative same-host disclosure URL guesses from a school homepage URL."""
    if limit <= 0:
        return []

    parsed = urlparse(site_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return []

    path = parsed.path.rstrip("/")
    raw_segments = [segment for segment in path.split("/") if segment]
    slug = raw_segments[-1] if raw_segments else ""
    root = f"{parsed.scheme}://{parsed.netloc}"
    path_or_root = path or ""
    seen: set[str] = {normalize_candidate_url(site_url)}
    urls: list[str] = []

    if len(raw_segments) >= 2 and raw_segments[-1].lower() in {"disclosure", "information", "public", "public_info"}:
        inverted_path = f"/{raw_segments[-1]}/{raw_segments[-2]}"
        inverted_url = urljoin(root + "/", inverted_path.lstrip("/"))
        seen.add(normalize_candidate_url(inverted_url))
        urls.append(inverted_url)
        if len(urls) >= limit:
            return urls

    for pattern in DERIVED_DISCLOSURE_PATHS:
        if "{slug}" in pattern and not slug:
            continue
        if "{path}" in pattern and not path_or_root:
            continue
        candidate_path = pattern.format(slug=slug, path=path_or_root)
        candidate_url = urljoin(root + "/", candidate_path.lstrip("/"))
        key = normalize_candidate_url(candidate_url)
        if key in seen:
            continue
        seen.add(key)
        urls.append(candidate_url)
        if len(urls) >= limit:
            break
    return urls


def _sitemap_urls_for_site(
    client: httpx.Client,
    site_url: str,
    *,
    limit: int = 5,
) -> list[str]:
    """Return same-domain disclosure-like URLs from ``/sitemap.xml``.

    This is a conservative fallback for schools whose information-disclosure
    page is indexed in the sitemap but not linked from the supplied site URL.
    """
    if limit <= 0:
        return []

    parsed = urlparse(site_url)
    if not parsed.scheme or not parsed.netloc:
        return []

    urls: list[str] = []
    sitemap_urls = _sitemap_entry_urls_for_site(client, site_url)
    sitemap_seen: set[str] = set()
    sitemap_queue = list(sitemap_urls)
    seen: set[str] = set()

    while sitemap_queue and len(urls) < limit:
        sitemap_url = sitemap_queue.pop(0)
        if sitemap_url in sitemap_seen or not _is_safe_url(sitemap_url):
            continue
        sitemap_seen.add(sitemap_url)
        try:
            resp = _safe_get(client, sitemap_url)
        except httpx.HTTPError:
            continue
        if resp.status_code != 200:
            continue

        for loc in _extract_sitemap_locs(resp.text):
            loc_url = urljoin(sitemap_url, loc)
            loc_parsed = urlparse(loc_url)
            if loc_parsed.netloc != parsed.netloc or not _is_safe_url(loc_url):
                continue
            if loc_url in seen:
                continue
            text = html_lib.unescape(loc_url).lower()
            if loc_parsed.path.lower().endswith(".xml"):
                if len(sitemap_seen) + len(sitemap_queue) < 12:
                    sitemap_queue.append(loc_url)
                continue
            if any(keyword.lower() in text for keyword in SITEMAP_PAGE_KEYWORDS):
                seen.add(loc_url)
                urls.append(loc_url)
                if len(urls) >= limit:
                    break
    return urls


def _sitemap_entry_urls_for_site(client: httpx.Client, site_url: str) -> list[str]:
    """Return sitemap URLs advertised by a site.

    Many school/corporation sites expose ``/sitemap_index.xml`` only via
    robots.txt, not at ``/sitemap.xml``. Treat robots Sitemap directives as
    the primary low-cost discovery hint, while keeping the conventional root
    sitemap as a fallback.
    """
    parsed = urlparse(site_url)
    if not parsed.scheme or not parsed.netloc:
        return []

    entries: list[str] = []
    seen: set[str] = set()

    def add(url: str) -> None:
        resolved = urljoin(site_url, url.strip())
        if not resolved or resolved in seen or not _is_safe_url(resolved):
            return
        entry_parsed = urlparse(resolved)
        if entry_parsed.netloc != parsed.netloc:
            return
        seen.add(resolved)
        entries.append(resolved)

    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    if _is_safe_url(robots_url):
        try:
            robots_resp = _safe_get(client, robots_url)
        except httpx.HTTPError:
            robots_resp = None
        if robots_resp is not None and robots_resp.status_code == 200:
            for sitemap_url in _extract_robots_sitemaps(robots_resp.text):
                add(sitemap_url)

    add(f"{parsed.scheme}://{parsed.netloc}/sitemap.xml")
    return entries


def _extract_robots_sitemaps(robots_txt: str) -> list[str]:
    sitemaps: list[str] = []
    for line in robots_txt.splitlines():
        stripped = line.strip()
        if not stripped.lower().startswith("sitemap:"):
            continue
        sitemap = stripped.split(":", 1)[1].strip()
        if sitemap:
            sitemaps.append(sitemap)
    return sitemaps


def _extract_sitemap_locs(xml: str) -> list[str]:
    return [
        html_lib.unescape(match.group(1).strip())
        for match in re.finditer(r"<loc>\s*(.*?)\s*</loc>", xml, re.IGNORECASE | re.DOTALL)
        if match.group(1).strip()
    ]


def _append_unique_candidates(target: list[PdfCandidate], additions: list[PdfCandidate]) -> None:
    """Append candidates not already present by PDF URL."""
    seen = {_pdf_candidate_dedupe_key(candidate.pdf_url) for candidate in target}
    for candidate in additions:
        candidate_key = _pdf_candidate_dedupe_key(candidate.pdf_url)
        if candidate_key in seen:
            continue
        seen.add(candidate_key)
        target.append(candidate)


def _needs_rendered_html_fallback(candidates: list[PdfCandidate], *, target_fiscal_year: int) -> bool:
    """Return whether JS-rendered HTML may add missing current-year candidates."""

    if not candidates:
        return True
    return not any(_has_target_year_hint(candidate, target_year=target_fiscal_year) for candidate in candidates)


def _default_rendered_html_fetcher() -> RenderedHtmlFetcher | None:
    mode = settings.pdf_discovery_rendered_html_auto_enable.strip().lower()
    if mode == "off":
        return None

    try:
        from eidp.scraper.scrapling_fetcher import (
            ScraplingFetchMode,
            ScraplingHtmlFetcher,
            scrapling_available,
        )
    except Exception as exc:
        log.warning("rendered_html_fetcher_import_failed", error=str(exc), error_type=type(exc).__name__)
        return None

    if not scrapling_available():
        if mode == "on":
            log.warning("rendered_html_fetcher_unavailable", mode=mode)
        return None

    fetch_mode = settings.pdf_discovery_rendered_html_fetch_mode.strip().lower()
    if fetch_mode not in {"static", "dynamic", "stealthy"}:
        fetch_mode = "dynamic"
    return ScraplingHtmlFetcher(mode=cast(ScraplingFetchMode, fetch_mode))


def _append_rendered_html_candidates(
    candidates: list[PdfCandidate],
    *,
    page_urls: list[str],
    rendered_html_fetcher: RenderedHtmlFetcher,
    max_pages: int = MAX_RENDERED_DISCOVERY_PAGES,
    max_elapsed_seconds: float = MAX_DISCOVERY_ELAPSED_SECONDS,
    started_at: float | None = None,
) -> int:
    """Fetch rendered HTML pages and append PDF candidates found after JS execution."""

    fetched = 0
    queue = list(page_urls)
    seen_pages: set[str] = set()
    started = started_at if started_at is not None else time.monotonic()

    while queue and fetched < max_pages:
        if max_elapsed_seconds > 0 and time.monotonic() - started >= max_elapsed_seconds:
            break
        page_url = queue.pop(0)
        page_key = normalize_candidate_url(page_url)
        if page_key in seen_pages or not _is_safe_url(page_url):
            continue
        seen_pages.add(page_key)

        try:
            html = rendered_html_fetcher.fetch_html(page_url)
        except Exception as exc:
            log.warning(
                "rendered_html_fetch_failed",
                url=page_url,
                error=str(exc),
                error_type=type(exc).__name__,
            )
            continue
        fetched += 1
        if not html:
            continue

        _append_unique_candidates(candidates, _extract_pdf_links(html, page_url))

        for sub_url in _find_subpage_links(html, page_url):
            sub_key = normalize_candidate_url(sub_url)
            if sub_key in seen_pages or any(normalize_candidate_url(queued) == sub_key for queued in queue):
                continue
            if len(queue) + fetched >= max_pages:
                break
            queue.append(sub_url)

    return fetched


def discover_pdfs_for_site(
    client: httpx.Client,
    school_id: int,
    site_url: str,
    max_depth: int = 2,
    max_extra_pages: int = MAX_DISCOVERY_EXTRA_PAGES,
    max_elapsed_seconds: float = MAX_DISCOVERY_ELAPSED_SECONDS,
    rendered_html_fetcher: RenderedHtmlFetcher | None = None,
    target_fiscal_year: int | None = None,
    school_name: str = "",
) -> DiscoveryResult:
    """Discover PDF candidates from a school site URL."""
    result = DiscoveryResult(school_id=school_id)
    started_at = time.monotonic()
    extra_pages_fetched = 0
    target_year = target_fiscal_year or settings.target_fiscal_year
    registered_site_url = site_url

    def extra_page_budget_remaining() -> int:
        if max_elapsed_seconds > 0 and time.monotonic() - started_at >= max_elapsed_seconds:
            return 0
        return max(max_extra_pages - extra_pages_fetched, 0)

    try:
        # SSRF validation: reject internal/metadata URLs
        if not _is_safe_url(site_url):
            result.error = "unsafe_url"
            return result

        # Check robots.txt (best effort, non-blocking)
        from urllib.parse import urlparse
        parsed = urlparse(site_url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        try:
            robots_resp = client.get(robots_url)
            if robots_resp.status_code == 200:
                # Only block on full-site disallow for all user agents
                lines = robots_resp.text.strip().split("\n")
                in_wildcard = False
                for line in lines:
                    line = line.strip()
                    if line.lower().startswith("user-agent:") and "*" in line:
                        in_wildcard = True
                    elif line.lower().startswith("user-agent:"):
                        in_wildcard = False
                    elif in_wildcard and line.strip() == "Disallow: /":
                        result.error = "robots.txt disallows all crawling"
                        return result
        except httpx.HTTPError:
            pass  # No robots.txt or unreachable, proceed

        time.sleep(1.0)  # Per-request delay (design: max 1 req/sec per domain)

        # Fetch main page (with safe redirect following)
        resp, site_url = _main_page_response_with_root_fallback(client, site_url)
        html = resp.text

        # Short/truncated HTML retry (TCA pattern)
        if len(html) < 500 and resp.status_code == 200:
            time.sleep(1.0)
            resp = _safe_get(client, site_url)
            html = resp.text

        # Extract PDF candidates from main page
        candidates = _extract_pdf_links(html, site_url)

        # Always try subpage links (two-tier pattern)
        # Even if root has PDFs, target docs may be on subpages
        subpages: list[str] = []
        if max_depth > 0:
            subpages = _find_subpage_links(html, site_url, school_name=school_name)
            for sub_url in subpages:
                if extra_page_budget_remaining() <= 0:
                    break
                if not _is_safe_url(sub_url):
                    continue
                try:
                    time.sleep(1.0)  # Per-request delay
                    extra_pages_fetched += 1
                    sub_resp = _safe_get(client, sub_url)
                    if sub_resp.status_code == 200:
                        sub_base_url = str(sub_resp.url or sub_url)
                        sub_candidates = _extract_pdf_links(sub_resp.text, sub_base_url)
                        _append_unique_candidates(candidates, sub_candidates)
                except httpx.HTTPError:
                    continue

        school_homepage_page_urls: list[str] = []
        if max_depth > 0 and not candidates and school_name:
            for homepage_url in _find_school_homepage_links(html, site_url, school_name):
                if extra_page_budget_remaining() <= 0:
                    break
                try:
                    time.sleep(1.0)
                    extra_pages_fetched += 1
                    homepage_resp = _safe_get(client, homepage_url)
                    if homepage_resp.status_code != 200:
                        continue
                    homepage_base_url = str(homepage_resp.url or homepage_url)
                    school_homepage_page_urls.append(homepage_base_url)
                    homepage_html = homepage_resp.text
                    _append_unique_candidates(candidates, _extract_pdf_links(homepage_html, homepage_base_url))
                    for sub_url in _find_subpage_links(homepage_html, homepage_base_url, school_name=school_name):
                        if extra_page_budget_remaining() <= 0:
                            break
                        if not _is_safe_url(sub_url):
                            continue
                        try:
                            time.sleep(1.0)
                            extra_pages_fetched += 1
                            sub_resp = _safe_get(client, sub_url)
                            if sub_resp.status_code == 200:
                                sub_base_url = str(sub_resp.url or sub_url)
                                school_homepage_page_urls.append(sub_base_url)
                                _append_unique_candidates(candidates, _extract_pdf_links(sub_resp.text, sub_base_url))
                        except httpx.HTTPError:
                            continue
                except httpx.HTTPError:
                    continue

        derived_budget = max(extra_page_budget_remaining() - SITEMAP_DISCOVERY_RESERVED_PAGES, 0)
        derived_urls: list[str] = []
        derived_seen: set[str] = set()
        for derived_source_url in (registered_site_url, site_url):
            for derived_url in _derived_disclosure_page_urls(derived_source_url, limit=derived_budget):
                derived_key = normalize_candidate_url(derived_url)
                if derived_key in derived_seen:
                    continue
                derived_seen.add(derived_key)
                derived_urls.append(derived_url)
                if len(derived_urls) >= derived_budget:
                    break
            if len(derived_urls) >= derived_budget:
                break

        for derived_url in derived_urls:
            if extra_page_budget_remaining() <= 0:
                break
            if not _is_safe_url(derived_url):
                continue
            try:
                time.sleep(1.0)
                extra_pages_fetched += 1
                derived_resp = _safe_get(client, derived_url)
                if derived_resp.status_code == 200:
                    derived_base_url = str(derived_resp.url or derived_url)
                    _append_unique_candidates(candidates, _extract_pdf_links(derived_resp.text, derived_base_url))
            except httpx.HTTPError:
                continue

        # Sitemap discovery is not just a last resort. Many school homepages
        # expose stale PDFs on the visible page while the current disclosure page
        # is only reachable through sitemap.xml / robots Sitemap entries.
        sitemap_page_urls: list[str] = []
        for sitemap_url in _sitemap_urls_for_site(client, site_url, limit=extra_page_budget_remaining()):
            if extra_page_budget_remaining() <= 0:
                break
            if sitemap_url.lower().split("?", 1)[0].endswith(".pdf"):
                _append_unique_candidates(
                    candidates,
                    [PdfCandidate(
                        pdf_url=sitemap_url,
                        page_url=sitemap_url,
                        anchor_text="sitemap",
                        pattern_type="sitemap_pdf",
                    )],
                )
                continue
            sitemap_page_urls.append(sitemap_url)
            try:
                time.sleep(1.0)
                extra_pages_fetched += 1
                sitemap_resp = _safe_get(client, sitemap_url)
                if sitemap_resp.status_code == 200:
                    sitemap_base_url = str(sitemap_resp.url or sitemap_url)
                    _append_unique_candidates(candidates, _extract_pdf_links(sitemap_resp.text, sitemap_base_url))
            except httpx.HTTPError:
                continue

        if _needs_rendered_html_fallback(candidates, target_fiscal_year=target_year):
            fetcher = rendered_html_fetcher or _default_rendered_html_fetcher()
            if fetcher is not None:
                rendered_page_urls = [site_url, *subpages, *school_homepage_page_urls, *sitemap_page_urls]
                rendered_seen: set[str] = set()
                unique_rendered_page_urls: list[str] = []
                for url in rendered_page_urls:
                    key = normalize_candidate_url(url)
                    if key in rendered_seen:
                        continue
                    rendered_seen.add(key)
                    unique_rendered_page_urls.append(url)
                _append_rendered_html_candidates(
                    candidates,
                    page_urls=unique_rendered_page_urls,
                    rendered_html_fetcher=fetcher,
                    max_elapsed_seconds=max_elapsed_seconds,
                    started_at=started_at,
                )

        # Score all candidates
        for c in candidates:
            _score_candidate(c, target_fiscal_year=target_year)

        # Sort by score descending
        candidates.sort(key=lambda c: c.score, reverse=True)
        result.candidates = candidates

        if candidates:
            result.best = candidates[0]

    except httpx.TimeoutException:
        result.error = "timeout"
    except httpx.HTTPError as e:
        result.error = str(e)

    return result


def _classify_pdf_content(content: bytes) -> str:
    """Quick-classify PDF content type by sampling first 3 pages.

    Returns: 'target' (申請書), 'non_target' (wrong document), 'image_only' (needs OCR).
    """
    try:
        return _classify_pdf_sample_text(_extract_pdf_sample_text(content))
    except Exception as e:
        log.warning("pdf_classify_failed", error=str(e), error_type=type(e).__name__)
        return "unknown"


def download_pdf(
    client: httpx.Client,
    candidate: PdfCandidate,
    storage_dir: Path,
    school_id: int,
    *,
    target_fiscal_year: int | None = None,
    strict_target_fiscal_year: bool = False,
) -> tuple[str | None, str | None, int, str, str | None]:
    """Download PDF and return (file_path, sha256_hash, file_size, pdf_type, reason).

    `reason` is None on success, otherwise a short string identifying why the
    candidate was rejected (used for evidence trail).

    Max download size: 50MB. Larger files are skipped.
    """
    max_pdf_size = 50 * 1024 * 1024  # 50 MB

    if not _is_safe_url(candidate.pdf_url):
        return None, None, 0, "unknown", "unsafe_url"
    try:
        last_reject_reason = "unknown"
        for download_url in _download_attempt_urls(candidate.pdf_url):
            if not _is_safe_url(download_url):
                last_reject_reason = "unsafe_resolved_url"
                continue
            try:
                resp = _safe_get(client, download_url)
                resp.raise_for_status()
            except httpx.HTTPError as e:
                last_reject_reason = f"http_error:{type(e).__name__}"
                continue

            # Check Content-Length before reading body
            content_length = resp.headers.get("content-length")
            if content_length and int(content_length) > max_pdf_size:
                log.warning("pdf_too_large", url=download_url, size=content_length)
                return None, None, 0, "unknown", "too_large_header"

            content = resp.content
            if len(content) > max_pdf_size:
                log.warning("pdf_too_large_actual", url=download_url, size=len(content))
                return None, None, 0, "unknown", "too_large_body"
            if len(content) < 1000:  # Too small to be a real PDF
                last_reject_reason = "too_small"
                continue

            # Verify it's actually a PDF
            if not content[:5] == b"%PDF-":
                last_reject_reason = "not_pdf_magic"
                continue

            candidate.pdf_url = download_url
            break
        else:
            return None, None, 0, "unknown", last_reject_reason

        file_hash = hashlib.sha256(content).hexdigest()
        file_size = len(content)

        detected_fiscal_year: int | None = None
        try:
            sample_text = _extract_pdf_sample_text(content)
            pdf_type = _classify_pdf_sample_text(sample_text)
            max_detectable_year = None
            if strict_target_fiscal_year:
                max_detectable_year = target_fiscal_year or settings.target_fiscal_year
            detected_fiscal_year = _detect_fiscal_year_from_text(
                sample_text,
                max_fiscal_year=max_detectable_year,
            )
            candidate.detected_fiscal_year = detected_fiscal_year
        except Exception as e:
            log.warning("pdf_classify_failed", error=str(e), error_type=type(e).__name__)
            pdf_type = "unknown"

        if strict_target_fiscal_year:
            target_year = target_fiscal_year or settings.target_fiscal_year
            if pdf_type == "non_target":
                return None, None, 0, "non_target", "classified_non_target"
            if detected_fiscal_year is not None and detected_fiscal_year != target_year:
                return None, None, 0, pdf_type, f"fiscal_year_mismatch:{detected_fiscal_year}"
            stale_hint_year = _stale_fiscal_year_from_candidate_hint(candidate, target_year=target_year)
            if detected_fiscal_year is None and stale_hint_year is not None:
                return None, None, 0, pdf_type, f"fiscal_year_mismatch:{stale_hint_year}"
            if (
                detected_fiscal_year == target_year
                and pdf_type == "image_only"
                and not _has_target_application_hint(candidate)
            ):
                return None, None, 0, pdf_type, "target_application_not_detected"
            trusted_year_evidence = candidate.trusted_year_evidence.strip()
            if detected_fiscal_year is None and not (
                pdf_type == "image_only" and _has_target_application_hint(candidate)
            ) and not (
                pdf_type == "target" and _has_target_year_hint(candidate, target_year=target_year)
            ) and not (
                pdf_type == "target" and trusted_year_evidence
            ):
                return None, None, 0, pdf_type, "target_fiscal_year_not_detected"
            if detected_fiscal_year == target_year:
                candidate.year_evidence = "pdf_text"
            elif _has_target_year_hint(candidate, target_year=target_year):
                candidate.year_evidence = "url_hint"
            elif pdf_type == "target" and trusted_year_evidence:
                candidate.year_evidence = trusted_year_evidence
            elif pdf_type == "image_only" and _has_target_application_hint(candidate):
                candidate.year_evidence = "target_application_no_year"
            else:
                candidate.year_evidence = "none"
        elif detected_fiscal_year is not None:
            candidate.year_evidence = "pdf_text"

        # Storage path: data/pdfs/{school_id}/{hash[:8]}.pdf
        school_dir = storage_dir / str(school_id)
        school_dir.mkdir(parents=True, exist_ok=True)
        file_path = school_dir / f"{file_hash[:8]}.pdf"
        file_path.write_bytes(content)

        # Clean up non-target files to prevent orphaned disk usage
        if pdf_type == "non_target":
            file_path.unlink(missing_ok=True)
            log.info("non_target_pdf_removed", url=candidate.pdf_url, path=str(file_path))
            return None, None, 0, "non_target", "classified_non_target"

        return str(file_path), file_hash, file_size, pdf_type, None

    except httpx.HTTPError as e:
        return None, None, 0, "unknown", f"http_error:{type(e).__name__}"


def run_pdf_discovery(
    session: Session,
    storage_dir: Path,
    batch_size: int = 50,
    rate_limit: float = 1.0,
    request_timeout: float = 30.0,
    discovery_methods: list[str] | None = None,
    school_ids: list[int] | None = None,
    evidence_path: Path | None = None,
    target_fiscal_year: int | None = None,
    strict_target_fiscal_year: bool = False,
    progress_callback: PdfDiscoveryProgressCallback | None = None,
) -> dict[str, int]:
    """Run PDF discovery for schools with verified URLs but no documents.

    Args:
        discovery_methods: optional list of school_site.discovery_method values
            to restrict which URLs are crawled. E.g. ["prefecture_aggregator"]
            to crawl ONLY the trusted pref aggregator URLs (per Codex P0-6b:
            isolate polluted web_search URLs from pdf_discovery).
        school_ids: optional list of school.id to restrict discovery to a
            specific set (used for targeted gap-filling, e.g. 滋慶 group).
        evidence_path: optional JSONL path that captures every rejected
            candidate (URL/score/anchor/reason) per school for debug.
        target_fiscal_year: fiscal year to treat as current. Defaults to
            ``settings.target_fiscal_year``.
        strict_target_fiscal_year: when True, downloads are accepted only when
            PDF text, a body-confirmed target form plus URL/anchor evidence, or
            trusted current-year official-index evidence confirms
            ``target_fiscal_year``. Year-like text alone is not enough for
            image-only or ambiguous non-target application guides.
        progress_callback: optional callback invoked after each crawled school
            site with a snapshot of stats and the total site count. Used by the
            Windows operator UI so the long-running crawl does not sit at one
            frozen percentage.
    """
    stats = {
        "crawled": 0,
        "found": 0,
        "downloaded": 0,
        "failed": 0,
        "skipped": 0,
        "cached_rejections": 0,
        "prefiltered": 0,
    }
    recorder = EvidenceRecorder(evidence_path)

    def record_discovery_evidence(evidence: RejectionEvidence) -> None:
        _increment_rejection_reason(stats, evidence.reason)
        recorder.record(evidence)

    target_year = target_fiscal_year or settings.target_fiscal_year
    rejected_candidate_cache: dict[tuple[str, int | None, bool, str], CachedPdfRejection] = {}

    # Get school_sites, excluding:
    # - schools with a document for the current target fiscal year
    # - schools whose CURRENT revision in their latest fiscal year is excluded
    #   (Sprint 8.2.1: stale demoted revisions must NOT keep a school out).
    from sqlalchemy import or_

    from eidp.db.current_helpers import latest_excluded_school_ids

    excluded_school_ids = latest_excluded_school_ids(session)

    # Only skip schools that already have a document for the configured target year
    # (allow re-discovery if previous docs were from a different year or failed)
    # Only skip schools that have a FULLY ingested target-year document
    # support_only and partial docs should NOT suppress rediscovery
    schools_with_current_docs = (
        session.query(Document.school_id)
        .filter(
            Document.fiscal_year == target_year,
            Document.pdf_type == "target",
            Document.ingest_status == "ingested",
        )
        .distinct()
    )

    site_query = (
        session.query(SchoolSite)
        .filter(
            or_(SchoolSite.http_status == 200, SchoolSite.http_status.is_(None)),
            ~SchoolSite.school_id.in_(schools_with_current_docs),
            ~SchoolSite.school_id.in_(excluded_school_ids),
        )
    )
    if discovery_methods:
        site_query = site_query.filter(SchoolSite.discovery_method.in_(discovery_methods))
    if school_ids:
        site_query = site_query.filter(SchoolSite.school_id.in_(school_ids))
    sites = (
        site_query
        .order_by(SchoolSite.confidence.desc())
        .limit(batch_size)
        .all()
    )

    log.info("pdf_discovery_start", sites=len(sites))
    if progress_callback is not None:
        progress_callback(dict(stats), len(sites))

    with httpx.Client(
        timeout=max(float(request_timeout), 1.0),
        follow_redirects=False,
        headers=HEADERS,
    ) as client:
        for index, site in enumerate(sites, start=1):
            if progress_callback is not None:
                progress_callback(
                    {
                        **stats,
                        "active_index": index,
                        "active_school_id": int(site.school_id),
                    },
                    len(sites),
                )
            # Create crawl job
            job = CrawlJob(
                school_id=site.school_id,
                job_type="pdf_search",
                status="running",
                started_at=datetime.now(UTC),
            )
            session.add(job)
            session.flush()

            # Handle direct PDF URLs (e.g., from Firecrawl) — download directly
            site_path = urlparse(site.url).path.lower()
            if site_path.endswith(".pdf"):
                candidate = PdfCandidate(
                    pdf_url=site.url,
                    anchor_text="direct_pdf_url",
                    page_url=site.url,
                )
                candidate.score = 1.0
                result = DiscoveryResult(school_id=site.school_id)
                result.candidates = [candidate]
                result.best = candidate
            else:
                result = discover_pdfs_for_site(
                    client,
                    site.school_id,
                    site.url,
                    school_name=site.school.school_name if site.school is not None else "",
                    target_fiscal_year=target_year,
                )
            stats["crawled"] += 1

            if result.error:
                job.status = "failed"
                job.error_message = result.error
                job.finished_at = datetime.now(UTC)
                stats["failed"] += 1
                record_discovery_evidence(RejectionEvidence(
                    school_id=site.school_id,
                    pdf_url=site.url,
                    page_url=site.url,
                    reason="discovery_error",
                    extra={"error": str(result.error)},
                ))
                if progress_callback is not None:
                    progress_callback(dict(stats), len(sites))
                time.sleep(rate_limit)
                continue

            if not result.best:
                job.status = "success"
                job.finished_at = datetime.now(UTC)
                stats["skipped"] += 1
                record_discovery_evidence(RejectionEvidence(
                    school_id=site.school_id,
                    pdf_url=site.url,
                    page_url=site.url,
                    reason="no_candidates_found",
                ))
                if progress_callback is not None:
                    progress_callback(dict(stats), len(sites))
                time.sleep(rate_limit)
                continue

            stats["found"] += 1

            # Filter out negative-score candidates
            if target_fiscal_year is not None:
                for c in result.candidates:
                    _score_candidate(c, target_fiscal_year=target_year)
                result.candidates.sort(key=lambda c: c.score, reverse=True)
            viable = [c for c in result.candidates if c.score >= 0]
            if not viable:
                job.status = "review"
                job.error_message = "all candidates have negative score"
                job.finished_at = datetime.now(UTC)
                stats["failed"] += 1
                for c in result.candidates:
                    record_discovery_evidence(RejectionEvidence(
                        school_id=site.school_id,
                        pdf_url=c.pdf_url,
                        page_url=c.page_url,
                        anchor_text=c.anchor_text,
                        pattern_type=c.pattern_type,
                        score=c.score,
                        reason="all_negative_score",
                    ))
                if progress_callback is not None:
                    progress_callback(dict(stats), len(sites))
                time.sleep(rate_limit)
                continue

            # Try downloading top candidates (fallback on 404)
            downloaded = False
            duplicate_seen = False
            cross_school_dup_seen = False
            target_year_rejection_seen = False
            for candidate in viable[:MAX_CANDIDATE_DOWNLOAD_ATTEMPTS]:
                if strict_target_fiscal_year and not candidate.trusted_year_evidence:
                    candidate.trusted_year_evidence = _trusted_year_evidence_for_site(site)
                cache_key = _rejection_cache_key(
                    candidate.pdf_url,
                    target_year=target_year,
                    strict_target_fiscal_year=strict_target_fiscal_year,
                    trusted_year_evidence=candidate.trusted_year_evidence,
                )
                cached_rejection = rejected_candidate_cache.get(cache_key)
                if cached_rejection is not None:
                    stats["cached_rejections"] += 1
                    if cached_rejection.pdf_type == "non_target":
                        stats["skipped"] += 1
                    if _is_target_year_rejection(cached_rejection.reason):
                        target_year_rejection_seen = True
                    record_discovery_evidence(RejectionEvidence(
                        school_id=site.school_id,
                        pdf_url=candidate.pdf_url,
                        page_url=candidate.page_url,
                        anchor_text=candidate.anchor_text,
                        pattern_type=candidate.pattern_type,
                        score=candidate.score,
                        reason=cached_rejection.reason,
                        pdf_type=cached_rejection.pdf_type,
                        extra={"cached_rejection": "true"},
                    ))
                    continue

                pre_download_rejection = _pre_download_rejection(candidate, target_year=target_year)
                if pre_download_rejection is not None:
                    stats["prefiltered"] += 1
                    stats["skipped"] += 1
                    if _is_target_year_rejection(pre_download_rejection.reason):
                        target_year_rejection_seen = True
                    rejected_candidate_cache[cache_key] = CachedPdfRejection(
                        pdf_type=pre_download_rejection.pdf_type,
                        reason=pre_download_rejection.reason,
                    )
                    record_discovery_evidence(RejectionEvidence(
                        school_id=site.school_id,
                        pdf_url=candidate.pdf_url,
                        page_url=candidate.page_url,
                        anchor_text=candidate.anchor_text,
                        pattern_type=candidate.pattern_type,
                        score=candidate.score,
                        reason=pre_download_rejection.reason,
                        pdf_type=pre_download_rejection.pdf_type,
                        extra={"pre_download": "true"},
                    ))
                    continue

                if strict_target_fiscal_year:
                    file_path, file_hash, file_size, pdf_type, reject_reason = download_pdf(
                        client,
                        candidate,
                        storage_dir,
                        site.school_id,
                        target_fiscal_year=target_year,
                        strict_target_fiscal_year=True,
                    )
                else:
                    file_path, file_hash, file_size, pdf_type, reject_reason = download_pdf(
                        client, candidate, storage_dir, site.school_id,
                    )
                # non_target PDFs already cleaned up in download_pdf(), skip them
                if pdf_type == "non_target":
                    log.info("non_target_pdf_skipped", school_id=site.school_id, url=candidate.pdf_url)
                    stats["skipped"] += 1
                    if _is_cacheable_pdf_rejection(pdf_type, reject_reason):
                        rejected_candidate_cache[cache_key] = CachedPdfRejection(
                            pdf_type=pdf_type,
                            reason=reject_reason or "classified_non_target",
                        )
                    record_discovery_evidence(RejectionEvidence(
                        school_id=site.school_id,
                        pdf_url=candidate.pdf_url,
                        page_url=candidate.page_url,
                        anchor_text=candidate.anchor_text,
                        pattern_type=candidate.pattern_type,
                        score=candidate.score,
                        reason=reject_reason or "classified_non_target",
                        pdf_type=pdf_type,
                    ))
                    continue

                if file_path is None and reject_reason is not None:
                    if (
                        _is_target_year_rejection(reject_reason)
                    ):
                        target_year_rejection_seen = True
                    if _is_cacheable_pdf_rejection(pdf_type, reject_reason):
                        rejected_candidate_cache[cache_key] = CachedPdfRejection(
                            pdf_type=pdf_type,
                            reason=reject_reason,
                        )
                    record_discovery_evidence(RejectionEvidence(
                        school_id=site.school_id,
                        pdf_url=candidate.pdf_url,
                        page_url=candidate.page_url,
                        anchor_text=candidate.anchor_text,
                        pattern_type=candidate.pattern_type,
                        score=candidate.score,
                        reason=reject_reason,
                        pdf_type=pdf_type,
                    ))

                if file_path:
                    # Check for duplicate hash
                    existing = (
                        session.query(Document)
                        .filter(Document.file_hash == file_hash)
                        .first()
                    )
                    if existing:
                        duplicate_seen = True
                        stats["skipped"] += 1
                        if existing.school_id != site.school_id:
                            cross_school_dup_seen = True
                            reason = "duplicate_hash_other_school"
                        else:
                            reason = "duplicate_hash"
                        Path(file_path).unlink(missing_ok=True)
                        record_discovery_evidence(RejectionEvidence(
                            school_id=site.school_id,
                            pdf_url=candidate.pdf_url,
                            page_url=candidate.page_url,
                            anchor_text=candidate.anchor_text,
                            pattern_type=candidate.pattern_type,
                            score=candidate.score,
                            reason=reason,
                            pdf_type=pdf_type,
                            extra={
                                "existing_doc_id": str(existing.id),
                                "existing_school_id": str(existing.school_id),
                            },
                        ))
                        time.sleep(0.5)
                        continue
                    else:
                        content_type = "image" if pdf_type == "image_only" else "text"
                        doc = Document(
                            school_id=site.school_id,
                            source_url=candidate.pdf_url,
                            discovered_from=candidate.page_url,
                            file_path=file_path,
                            file_hash=file_hash,
                            file_size=file_size,
                            fiscal_year=target_year if strict_target_fiscal_year else candidate.detected_fiscal_year,
                            is_current_year=(
                                target_year >= current_fiscal_year()
                                if strict_target_fiscal_year
                                else (
                                    candidate.detected_fiscal_year >= current_fiscal_year()
                                    if candidate.detected_fiscal_year is not None
                                    else None
                                )
                            ),
                            content_type=content_type,
                            pdf_type=pdf_type,
                            confidence=min(candidate.score / 10.0, 0.99),
                            downloaded_at=datetime.now(UTC),
                        )
                        try:
                            with session.begin_nested():
                                session.add(doc)
                                session.flush()
                        except IntegrityError as exc:
                            duplicate_seen = True
                            stats["skipped"] += 1
                            if doc in session:
                                session.expunge(doc)
                            with session.no_autoflush:
                                existing = (
                                    session.query(Document)
                                    .filter(Document.file_hash == file_hash)
                                    .first()
                                )
                            if existing is not None:
                                if existing.school_id != site.school_id:
                                    cross_school_dup_seen = True
                                    reason = "duplicate_hash_other_school"
                                else:
                                    reason = "duplicate_hash"
                                extra = {
                                    "existing_doc_id": str(existing.id),
                                    "existing_school_id": str(existing.school_id),
                                    "integrity_error": "true",
                                }
                            else:
                                cross_school_dup_seen = True
                                reason = "duplicate_hash_integrity_error"
                                extra = {
                                    "integrity_error": "true",
                                    "error": str(exc.orig or exc),
                                }
                            Path(file_path).unlink(missing_ok=True)
                            record_discovery_evidence(RejectionEvidence(
                                school_id=site.school_id,
                                pdf_url=candidate.pdf_url,
                                page_url=candidate.page_url,
                                anchor_text=candidate.anchor_text,
                                pattern_type=candidate.pattern_type,
                                score=candidate.score,
                                reason=reason,
                                pdf_type=pdf_type,
                                extra=extra,
                            ))
                            time.sleep(0.5)
                            continue
                        stats["downloaded"] += 1
                        record_discovery_evidence(RejectionEvidence(
                            school_id=site.school_id,
                            pdf_url=candidate.pdf_url,
                            page_url=candidate.page_url,
                            anchor_text=candidate.anchor_text,
                            pattern_type=candidate.pattern_type,
                            score=candidate.score,
                            reason="accepted_downloaded",
                            pdf_type=pdf_type,
                            extra={
                                "site_url": site.url,
                                "discovery_method": site.discovery_method or "",
                                "target_fiscal_year": str(target_year),
                                "detected_fiscal_year": str(candidate.detected_fiscal_year or ""),
                                "year_evidence": candidate.year_evidence,
                            },
                        ))

                    job.status = "success"
                    job.finished_at = datetime.now(UTC)
                    downloaded = True
                    break

                time.sleep(0.5)

            if not downloaded:
                if cross_school_dup_seen:
                    # PDF is already on disk under another school. The
                    # operator console must surface this for manual
                    # alias / reassignment. "success" would mislead.
                    job.status = "review"
                    job.error_message = (
                        "candidate PDFs are duplicates of documents "
                        "already attached to other schools"
                    )
                elif duplicate_seen:
                    job.status = "success"
                    job.error_message = "all viable candidates already downloaded"
                elif target_year_rejection_seen:
                    job.status = "review"
                    job.error_message = f"no {target_year} PDF candidate confirmed"
                    stats["skipped"] += 1
                else:
                    job.status = "failed"
                    job.error_message = f"download failed for {len(result.candidates)} candidates"
                job.finished_at = datetime.now(UTC)
                if not (duplicate_seen or cross_school_dup_seen or target_year_rejection_seen):
                    stats["failed"] += 1

            session.flush()
            if progress_callback is not None:
                progress_callback(dict(stats), len(sites))
            time.sleep(rate_limit)

    log.info("pdf_discovery_complete", **stats)
    recorder.close()
    return stats
