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
from contextlib import closing
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Protocol, cast
from urllib.parse import parse_qsl, unquote, urljoin, urlparse

import httpx
import structlog
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from eidp.config import MAX_SUPPORTED_TARGET_FISCAL_YEAR, MIN_SUPPORTED_TARGET_FISCAL_YEAR, settings
from eidp.db.models import CrawlJob, Document, SchoolSite
from eidp.fiscal_year import fiscal_year_from_japanese_era_text, fiscal_year_search_tokens, has_fiscal_year_text
from eidp.scraper.discovery_evidence import EvidenceRecorder, RejectionEvidence
from eidp.scraper.url_discovery import _is_safe_url
from eidp.scraper.url_normalization import normalize_candidate_url

log = structlog.get_logger()

PdfDiscoveryProgressCallback = Callable[[dict[str, int], int], None]
MIN_SUPPORTED_FISCAL_YEAR = MIN_SUPPORTED_TARGET_FISCAL_YEAR
MAX_SUPPORTED_FISCAL_YEAR = MAX_SUPPORTED_TARGET_FISCAL_YEAR
_DISCLOSURE_PATH_YEAR_RE = re.compile(
    r"(?:/(?:public[_-]?info(?:rmation)?|disclosure)[_/-]|/pdf[_/-]?)(20\d{2})(?=[/_-])",
    re.IGNORECASE,
)
RUN_SCOPED_METADATA_CACHE_MAX_BYTES = 2_000_000
RUN_SCOPED_PDF_CACHE_MAX_BYTES = 5_000_000
MAX_BULK_REJECTION_EVIDENCE_PER_SCHOOL = 10


class HttpGetClient(Protocol):
    def get(self, url: str | httpx.URL, **kwargs: Any) -> httpx.Response: ...


def _is_supported_fiscal_year(fiscal_year: int) -> bool:
    return MIN_SUPPORTED_FISCAL_YEAR <= fiscal_year <= MAX_SUPPORTED_FISCAL_YEAR


def _is_candidate_hint_year(fiscal_year: int, *, target_year: int) -> bool:
    return max(MIN_SUPPORTED_FISCAL_YEAR, target_year - 8) <= fiscal_year <= min(
        MAX_SUPPORTED_FISCAL_YEAR,
        target_year + 2,
    )


def _safe_get(client: HttpGetClient, url: str, **kwargs: Any) -> httpx.Response:
    """GET with manual redirect following + SSRF check on each hop.

    Raises httpx.HTTPStatusError on SSRF-blocked redirect or redirect loop.
    Fails closed: if max hops exceeded, raises instead of returning last 3xx.
    """
    if not _is_safe_url(url):
        raise httpx.InvalidURL("Unsafe URL")
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


def _origin_key(url: str) -> str | None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return f"{parsed.scheme.lower()}://{parsed.netloc.lower()}"


def _main_page_response_with_root_fallback(client: HttpGetClient, site_url: str) -> tuple[httpx.Response, str]:
    """Fetch the registered page, retrying one transient timeout before root fallback."""

    last_timeout: httpx.TimeoutException | None = None
    for attempt in range(2):
        try:
            return _main_page_response_with_root_fallback_once(client, site_url)
        except httpx.TimeoutException as exc:
            last_timeout = exc
            if attempt == 0:
                time.sleep(1.0)
                continue
            break
    assert last_timeout is not None
    raise last_timeout


def _main_page_response_with_root_fallback_once(client: HttpGetClient, site_url: str) -> tuple[httpx.Response, str]:
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
    "subject_",
    "subject-",
    "info_",
    "grade_manage",
    "goal_policies",
    "curriculum",
    "財務",
    "zaimu",
    "収支計算書",
    "incomeandexpenditurestatement",
    "正味財産増減計算書",
    "calculationofchangesinassets",
    "貸借対照表",
    "balancesheet",
    "財産目録",
    "inventoryofassets",
    "監査報告書",
    "auditreport",
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
    "学則",
    "regulation.pdf",
    "寄付行為",
    "寄附行為",
    "kifu",
    "donation.pdf",
    "報酬",
    "remuneration.pdf",
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
    "客観的な指標",
    "kyakkantekishihyo",
    "kyakangpa",
    "シラバス",
    "syllabus",
    "教育課程表",
    "教育課程",
    "教育課程編成",
    "議事録",
    "成績分布",
    "seiseki",
    "kamoku",
    "classsubject",
    "indexing_rule",
    "学年暦",
    "学年歴",
    "年間計画表",
    "年間計画",
    "nenkan",
    "学修評価",
    "learningassessment",
    "教育理念",
    "educationalphilosophy",
    "必要経費",
    "gakuinannai",
    "卒業認定",
    "卒業の認定",
    "進級",
    "卒業の要件",
    "sotugyo",
    "sotsugyo",
    "graduation",
    "diploma-policy",
    "成績評価",
    "grading",
    "給付金",
    "kyufukin",
    "実習施設",
    "インターンシップ",
    "internshipreport",
    "学校の現況",
    "gakkou_genjyou",
    "gakkou_genjo",
    "諸心得",
    "knowledge",
    "細則",
    "通期",
    "前期",
    "後期",
    "お知らせ",
    "ニュース",
    "/news/",
    "イベント",
    "オープンキャンパス",
    "open-campus",
    "opencampus",
    "進路相談会",
    "防災訓練",
    "防犯講話",
    "ハラスメント",
    "harassment",
    "planreport",
    "securitypolicy",
    "事業報告",
    "teikitenkenhokoku",
    "sihyosanshutu",
    "証明書",
    "推薦書",
    "個人票",
    "アルバイト",
    "外泊",
    "student_support_guidelines",
    "入学試験",
    "入試",
    "ao入試",
)

# User-Agent mimicking a real browser (institutional research)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) EIDP-DataCollector/1.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ja,en;q=0.5",
}

MAX_CANDIDATE_DOWNLOAD_ATTEMPTS = 10
MAX_GENERAL_CANDIDATE_SCAN = 80
PREFECTURE_INDEX_TRUST_MAX_AGE_DAYS = 370
MAX_DISCOVERY_EXTRA_PAGES = 6
SITEMAP_DISCOVERY_RESERVED_PAGES = 2
MAX_DISCOVERY_ELAPSED_SECONDS = 45.0
MAX_RENDERED_DISCOVERY_PAGES = 3
SHARED_ORIGIN_DERIVED_FALLBACK_THRESHOLD = 20
SHARED_ORIGIN_DERIVED_FALLBACK_PROBE_SITES = 3
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
HOST_SPECIFIC_DERIVED_DISCLOSURE_PATHS = {
    "o-hara.ac.jp": ("/about/joho/",),
    "www.o-hara.ac.jp": ("/about/joho/",),
}
DISCLOSURE_DERIVATION_FILE_SUFFIXES = (".html", ".htm", ".php", ".aspx", ".jsp")


@dataclass
class PdfCandidate:
    pdf_url: str
    page_url: str
    anchor_text: str = ""
    pattern_type: str = ""
    score: float = 0.0
    detected_fiscal_year: int | None = None
    detected_school_name: str = ""
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
    error_code: str = ""
    error_retryable: bool = False


@dataclass(frozen=True)
class CachedPdfRejection:
    pdf_type: str
    reason: str


class RenderedHtmlFetcher(Protocol):
    def fetch_html(self, url: str) -> str | None: ...


class _RunScopedHttpCache:
    """Small GET cache for one PDF discovery run.

    Corporation roots often appear once per school. Cache HTML, robots, sitemap,
    and 404 responses so each school still gets its own scoring path without
    re-requesting identical shared pages.
    """

    def __init__(self, client: HttpGetClient, *, stats: dict[str, int]) -> None:
        self._client = client
        self._stats = stats
        self._cache: dict[str, httpx.Response] = {}

    def get(self, url: str | httpx.URL, **kwargs: Any) -> httpx.Response:
        url_str = str(url)
        cache_key = self._cache_key(url_str, kwargs)
        if cache_key is not None and cache_key in self._cache:
            self._stats["http_cache_hits"] += 1
            return self._cache[cache_key]

        response = self._client.get(url_str, **kwargs)
        if cache_key is not None and self._should_cache_response(response, url_str):
            self._cache[cache_key] = response
            self._stats["http_cache_misses"] += 1
        return response

    def has_cached_get(self, url: str, **kwargs: Any) -> bool:
        cache_key = self._cache_key(url, kwargs)
        return cache_key is not None and cache_key in self._cache

    @staticmethod
    def _cache_key(url: str, kwargs: dict[str, Any]) -> str | None:
        if kwargs:
            return None
        return _without_url_fragment(url)

    @staticmethod
    def _is_public_discovery_metadata_url(url: str) -> bool:
        path = urlparse(url).path.lower().rstrip("/")
        filename = path.rsplit("/", 1)[-1]
        return filename == "robots.txt" or (filename.endswith(".xml") and "sitemap" in filename)

    @staticmethod
    def _should_cache_response(response: httpx.Response, request_url: str) -> bool:
        headers = response.headers
        content_type = str(headers.get("content-type", "")).split(";", 1)[0].strip().lower()
        response_url = str(response.url or request_url)
        content_length = headers.get("content-length")
        parsed_content_length: int | None = None
        if content_length:
            try:
                parsed_content_length = int(content_length)
            except ValueError:
                return False
        is_pdf = urlparse(response_url).path.lower().endswith(".pdf") or content_type == "application/pdf"
        response_content = getattr(response, "content", None)
        if isinstance(response_content, bytes | bytearray):
            actual_content_length = len(response_content)
            if actual_content_length > 0:
                parsed_content_length = (
                    actual_content_length
                    if parsed_content_length is None
                    else max(parsed_content_length, actual_content_length)
                )
        if is_pdf:
            return (
                response.status_code == 200
                and parsed_content_length is not None
                and 0 < parsed_content_length <= RUN_SCOPED_PDF_CACHE_MAX_BYTES
            )
        if parsed_content_length is not None and parsed_content_length > RUN_SCOPED_METADATA_CACHE_MAX_BYTES:
            return False
        is_public_metadata = _RunScopedHttpCache._is_public_discovery_metadata_url(
            request_url
        ) or _RunScopedHttpCache._is_public_discovery_metadata_url(response_url)
        if is_public_metadata and response.status_code in {200, 404, 410}:
            return True
        # The run-scoped cache only serves unauthenticated discovery GETs inside
        # one batch. Some public school disclosure pages attach routing/CSRF
        # cookies to otherwise static HTML; do not let those headers force a
        # shared corporation page to be fetched once per school.
        if response.status_code == 200 and content_type in {"", "text/html", "application/xhtml+xml"}:
            text = getattr(response, "text", "")
            if 0 < len(text) < 500:
                return False
        return response.status_code < 500


def _sleep_before_uncached_get(client: HttpGetClient, url: str, seconds: float = 1.0) -> None:
    if seconds <= 0:
        return
    if isinstance(client, _RunScopedHttpCache) and client.has_cached_get(url):
        return
    time.sleep(seconds)


PDF_LINK_ATTRIBUTE_NAMES = ("data-downloadurl", "data-href", "data-url", "data-file", "data-pdf", "data-src")
PDF_DATA_ATTRIBUTE_TAG_PATTERN = r"(?:a|button|span|div)"
PDF_SCRIPT_URL_PATTERN = re.compile(r"([\"'])([^\"']*?\.pdf(?:[?#][^\"']*)?)\1", re.IGNORECASE)
PDF_META_REFRESH_PATTERN = r"<meta\s([^>]*)>"
PDF_OPTION_VALUE_PATTERN = r"<option\s([^>]*)>(.*?)</option\s*>"
PDF_FORM_ACTION_PATTERN = r"<form\s([^>]*)>(.*?)</form\s*>"
PDF_INPUT_TAG_PATTERN = r"<input\s([^>]*)>"
PDF_EMBED_TAG_NAMES = ("embed", "object", "iframe")
PDF_EMBED_ATTRIBUTE_NAMES = ("src", "data")


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


def _discovery_error_extra(result: DiscoveryResult) -> dict[str, str]:
    """Return machine-readable metadata for a site-level discovery failure."""

    error = str(result.error or "")
    extra = {"error": error}
    if result.error_code:
        extra["error_code"] = result.error_code
    elif error == "timeout":
        extra["error_code"] = "timeout"
    elif error == "unsafe_url":
        extra["error_code"] = "unsafe_url"
    elif "robots.txt disallows" in error:
        extra["error_code"] = "robots_disallow_all"
    elif error:
        extra["error_code"] = "http_error"
    extra["retryable"] = "true" if result.error_retryable or extra.get("error_code") == "timeout" else "false"
    return extra


def _rejection_cache_key(
    school_id: int,
    candidate_url: str,
    *,
    target_year: int,
    strict_target_fiscal_year: bool,
    trusted_year_evidence: str = "",
) -> tuple[int, str, int | None, bool, str]:
    attempt_urls = _download_attempt_urls(candidate_url)
    canonical_url = attempt_urls[0] if attempt_urls else candidate_url
    return (
        school_id,
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
    if site.discovery_method == "school_domain_override" and site.url_type in {"disclosure", "disclosure_page"}:
        return "school_domain_override_disclosure"
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


def _candidate_url_hint_text(candidate: PdfCandidate) -> str:
    return unicodedata.normalize("NFKC", unquote(candidate.pdf_url)).lower()


def _has_subject_pdf_url(candidate: PdfCandidate) -> bool:
    filename = Path(urlparse(_candidate_url_hint_text(candidate)).path).name
    return "subject_" in filename or "subject-" in filename


def _has_target_application_url_hint(candidate: PdfCandidate) -> bool:
    text = _candidate_url_hint_text(candidate)
    return any(
        token in text
        for token in (
            "修学支援",
            "高等教育",
            "無償化",
            "確認申請",
            "更新確認申請",
            "機関要件",
            "様式第2号",
            "様式第２号",
            "様式2号",
            "academic_support",
            "shugakushien",
            "syugakusien",
            "kakunin",
            "shinsei",
            "koushinshinsei",
            "koushin-shinsei",
            "confirmation_application",
            "confirmationapplication",
            "kikanyoken",
        )
    )


def _has_site_family_non_target_url(candidate: PdfCandidate) -> bool:
    """Return whether the URL is a known disclosure-family non-target shape.

    These patterns are intentionally host-scoped and run only after target-form
    hints have had a chance to keep the candidate. They capture stable public
    disclosure sub-documents that otherwise require a download before being
    classified as non-target.
    """

    parsed = urlparse(_candidate_url_hint_text(candidate))
    host = parsed.netloc.lower()
    path = parsed.path.lower()
    filename = Path(path).name

    if host == "www.o-hara.ac.jp" and re.search(
        r"/about/joho/pdf/\d{4}-\d-\d{2}-\d{2}-\d\.pdf$",
        path,
    ):
        return True

    if host == "www.sanko.ac.jp":
        if re.search(r"/disclosure/[^/]+/docs/", path) and not re.fullmatch(r"yoshiki\d{4}\.pdf", filename):
            return True
        if "/pdf/share/disclosure/measure/japanese/" in path and (
            re.fullmatch(r"r\d+_hokoku\.pdf", filename) or "teikitenkenhokoku" in filename
        ):
            return True

    if host == "kanto-koudai.com" and re.search(r"/school/johokokai/j\d{4}_\d{2}(?:_\d{2})?\.pdf$", path):
        return True

    if host == "www.yoshikawa-fukushi.ac.jp" and re.search(
        r"/about/pdf/\d{4}-\d{2}-\d(?:-\d)?(?:-\d)?\.pdf$",
        path,
    ):
        return True

    if host == "www.hondacollege.ac.jp" and re.search(r"/about/disclosure/pdf/htece_report_\d{2}\.pdf$", path):
        return True

    if host == "www.arsnet.ac.jp" and re.search(
        r"/uploads/20\d{2}/\d{2}/r\d+_(?:\d[a-z]\d|[a-z]{2})_\d{4}\.pdf$",
        path,
    ):
        return True

    if host == "www.saitama-cmcc.ac.jp" and re.search(r"/uploads/20\d{2}/\d{2}/\d[a-z]\d{2}\.pdf$", path):
        return True

    return False


def _fiscal_year_from_strong_candidate_hint(text: str, *, target_year: int) -> int | None:
    """Return fiscal-year evidence from URL/anchor text, not publication dates."""

    text = unicodedata.normalize("NFKC", text)
    detected = fiscal_year_from_japanese_era_text(
        text,
        include_fiscal_year_labels=True,
        include_filing_dates=False,
    )
    if detected is not None:
        return detected if _is_supported_fiscal_year(detected) else None

    western = re.search(r"(?<!\d)(20\d{2})\s*年度", text)
    if western is not None:
        year = int(western.group(1))
        return year if _is_supported_fiscal_year(year) else None

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
    romanized_form_context = any(
        token in text.lower()
        for token in (
            "kakunin",
            "shinsei",
            "koushinshinsei",
            "koushin-shinsei",
            "confirmation_application",
        )
    )
    if strong_form_context or romanized_form_context:
        western_start_month = re.search(r"(?<!\d)(20\d{2})(?=\s*年\s*0?4\s*月)", text)
        if western_start_month is not None:
            year = int(western_start_month.group(1))
            if _is_candidate_hint_year(year, target_year=target_year) and _is_support_system_start_month_hint(
                text,
                western_start_month.start(1),
                western_start_month.end(1),
            ):
                return year
        western_year = re.search(r"(?<!\d)(20\d{2})\s*年(?!\s*(?:度|\d{1,2}\s*月))", text)
        if western_year is not None:
            year = int(western_year.group(1))
            if _is_candidate_hint_year(year, target_year=target_year):
                return year
        filename_year = re.search(r"(?<!\d)(20\d{2})(?=[^/\s]*\.pdf\b)", text, re.IGNORECASE)
        if filename_year is not None:
            year = int(filename_year.group(1))
            if _is_candidate_hint_year(year, target_year=target_year):
                return year
        serial_filename_year = re.search(r"(?<!\d)(20\d{2})(?=\d{2,4}[^/\s]*\.pdf\b)", text, re.IGNORECASE)
        if serial_filename_year is not None:
            year = int(serial_filename_year.group(1))
            if _is_candidate_hint_year(year, target_year=target_year):
                return year
        school_prefixed_year = re.search(
            r"(?<!\d)(20\d{2})(?!\s*(?:年|年度|月|日|\d|[./-]\d))(?=\s*[\u3040-\u30ff\u3400-\u9fff])",
            text,
        )
        if school_prefixed_year is not None:
            year = int(school_prefixed_year.group(1))
            if _is_candidate_hint_year(year, target_year=target_year):
                return year
        for path_year in _DISCLOSURE_PATH_YEAR_RE.finditer(text):
            year = int(path_year.group(1))
            if _is_candidate_hint_year(year, target_year=target_year):
                return year

    lowered = text.lower()
    for year in range(
        max(MIN_SUPPORTED_FISCAL_YEAR, target_year - 8),
        min(MAX_SUPPORTED_FISCAL_YEAR + 1, target_year + 3),
    ):
        for token in fiscal_year_search_tokens(year):
            if token == str(year):
                continue
            token_lower = token.lower()
            if token_lower.startswith("r"):
                pattern = rf"(?<![a-z0-9]){re.escape(token_lower)}(?![a-z0-9])"
                if re.search(pattern, lowered):
                    return year
            else:
                for match in re.finditer(re.escape(token_lower), lowered):
                    if _is_followed_by_year_month_date(lowered, match.end()):
                        if strong_form_context and _is_support_system_start_month_hint(
                            lowered,
                            match.start(),
                            match.end(),
                        ):
                            return year
                        continue
                    if _is_followed_by_law_reference(lowered, match.end()):
                        continue
                    return year
    return None


def _stale_fiscal_year_from_candidate_hint(candidate: PdfCandidate, *, target_year: int) -> int | None:
    """Return a past year from URL/anchor hints for rejection diagnostics only."""

    if _has_target_year_hint(candidate, target_year=target_year):
        return None

    text = _candidate_hint_text(candidate)
    detected_year = _fiscal_year_from_strong_candidate_hint(text, target_year=target_year)
    if detected_year is not None and max(MIN_SUPPORTED_FISCAL_YEAR, target_year - 8) <= detected_year < target_year:
        return detected_year
    for match in re.finditer(r"(?<!\d)(20\d{2})(?=[^/\s]*\.pdf\b)", text, re.IGNORECASE):
        year = int(match.group(1))
        if max(MIN_SUPPORTED_FISCAL_YEAR, target_year - 8) <= year < target_year:
            return year
    return None


def _has_explicit_stale_fiscal_year_label(candidate: PdfCandidate, *, target_year: int) -> bool:
    """Return whether URL/anchor text explicitly labels a stale fiscal year."""

    text = _candidate_hint_text(candidate)
    detected_year = _fiscal_year_from_strong_candidate_hint(text, target_year=target_year)
    if detected_year is not None and max(MIN_SUPPORTED_FISCAL_YEAR, target_year - 8) <= detected_year < target_year:
        return True

    detected_year = fiscal_year_from_japanese_era_text(
        text,
        include_fiscal_year_labels=True,
        include_filing_dates=False,
    )
    if detected_year is not None and max(MIN_SUPPORTED_FISCAL_YEAR, target_year - 8) <= detected_year < target_year:
        return True
    lowered = unicodedata.normalize("NFKC", text).lower()
    for year in range(max(MIN_SUPPORTED_FISCAL_YEAR, target_year - 8), target_year):
        for token in fiscal_year_search_tokens(year):
            token_lower = token.lower()
            if not token_lower.startswith("r"):
                continue
            if re.search(rf"(?<![a-z0-9]){re.escape(token_lower)}\s*年度", lowered):
                return True
        for token in fiscal_year_search_tokens(year):
            token_lower = token.lower()
            if token_lower.startswith("r") or token == str(year):
                continue
            for match in re.finditer(re.escape(token_lower), lowered):
                if _is_followed_by_year_month_date(lowered, match.end()):
                    continue
                if re.match(r"\s*年度", lowered[match.end() :]):
                    return True
    for match in re.finditer(r"(?<!\d)(20\d{2})\s*年度", text):
        year = int(match.group(1))
        if max(MIN_SUPPORTED_FISCAL_YEAR, target_year - 8) <= year < target_year:
            return True
    return False


def _pre_download_rejection(candidate: PdfCandidate, *, target_year: int) -> CachedPdfRejection | None:
    """Reject adjacent disclosure PDFs that are clearly not current target forms."""

    text = _candidate_hint_text(candidate)
    lowered = text.lower()
    detected_year = _fiscal_year_from_strong_candidate_hint(text, target_year=target_year)
    if "a様式1" in lowered or "対象者の認定に関する申請書" in lowered:
        return CachedPdfRejection(
            pdf_type="non_target",
            reason="pre_filtered_non_target_hint",
        )
    if any(token in lowered for token in ("授業料減免", "授業料等減免", "jyugyoryo", "jugyoryo", "genmen")) and not (
        _has_target_application_hint(candidate)
    ):
        return CachedPdfRejection(
            pdf_type="non_target",
            reason="pre_filtered_non_target_hint",
        )
    if _has_subject_pdf_url(candidate) and not _has_target_application_url_hint(candidate):
        return CachedPdfRejection(
            pdf_type="non_target",
            reason="pre_filtered_non_target_hint",
        )
    if detected_year is not None and detected_year != target_year and _has_target_application_hint(candidate):
        if _has_disclosure_path_target_year_hint(
            candidate,
            target_year=target_year,
        ) and not _has_explicit_stale_fiscal_year_label(candidate, target_year=target_year):
            return None
        return CachedPdfRejection(
            pdf_type="target",
            reason=f"fiscal_year_mismatch:{detected_year}",
        )
    if _has_target_application_hint(candidate):
        return None
    if _has_site_family_non_target_url(candidate):
        return CachedPdfRejection(
            pdf_type="non_target",
            reason="pre_filtered_non_target_hint",
        )
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
    form_hint = any(
        token in text
        for token in ("確認申請", "申請書", "申請様式", "様式第2号", "様式第２号", "様式2号", "機関要件")
    )
    full_form_range_hint = re.search(r"様式第[2２]号の?[1１]\s*[〜～~\-－−ー―]\s*[4４]", text) is not None
    japanese_renewal_form_hint = "更新確認申請" in text
    romanized_renewal_form_hint = any(
        token in text
        for token in (
            "koushinshinsei",
            "koushin-shinsei",
            "confirmation_application",
            "confirmationapplication",
        )
    ) and (system_hint or form_hint)
    strong_form_hint = "機関要件" in text and any(
        token in text for token in ("確認申請", "様式第2号", "様式第２号", "様式2号")
    )
    return (
        (system_hint and form_hint)
        or full_form_range_hint
        or japanese_renewal_form_hint
        or romanized_renewal_form_hint
        or strong_form_hint
    )


def _has_target_form_hint(candidate: PdfCandidate) -> bool:
    """Return whether URL/anchor text names an application-form shape."""

    text = _candidate_hint_text(candidate).lower()
    return _has_target_application_hint(candidate) or any(
        token in text
        for token in (
            "確認申請",
            "様式第2号",
            "様式第２号",
            "様式2号",
            "機関要件",
            "更新確認申請",
        )
    )


def _has_specific_target_form_hint(candidate: PdfCandidate) -> bool:
    """Return whether URL/anchor text specifically names the target form."""

    text = _candidate_hint_text(candidate).lower()
    return _has_target_application_hint(candidate) or any(
        token in text
        for token in (
            "様式第2号",
            "様式第２号",
            "様式2号",
            "機関要件確認申請",
            "confirmation_application",
            "confirmationapplication",
            "kakuninshinsei",
            "koushinshinsei",
        )
    )


def _has_known_embedded_study_support_target_form(candidate: PdfCandidate) -> bool:
    """Return whether an embedded school override URL is a known yearless target form."""

    parsed = urlparse(_candidate_url_hint_text(candidate))
    return (
        parsed.netloc == "www.nkz.ac.jp"
        and re.search(r"/clginfo/[^/]+/pdf/[^/]+z-studyspt_13\.pdf$", parsed.path) is not None
    )


def _has_formish_candidate_hint(candidate: PdfCandidate) -> bool:
    """Return whether URL/anchor text is worth trying ahead of generic PDFs."""

    if _has_target_form_hint(candidate):
        return True
    text = _candidate_hint_text(candidate).lower()
    return any(
        token in text
        for token in (
            "様式",
            "kakunin",
            "shinsei",
            "申請",
            "確認",
            "機関要件",
            "wpdmdl",
        )
    )


def _has_target_year_hint(candidate: PdfCandidate, *, target_year: int) -> bool:
    """Return whether URL/anchor text explicitly names the target fiscal year."""
    return _fiscal_year_from_strong_candidate_hint(
        _candidate_hint_text(candidate),
        target_year=target_year,
    ) == target_year


def _has_disclosure_path_target_year_hint(candidate: PdfCandidate, *, target_year: int) -> bool:
    """Return whether the PDF URL itself carries a disclosure/public-info target-year path."""

    for match in _DISCLOSURE_PATH_YEAR_RE.finditer(_candidate_url_hint_text(candidate)):
        if int(match.group(1)) == target_year:
            return True
    return False


def _is_support_law_reference_year(sample_text: str, *, fiscal_year: int) -> bool:
    """Return whether a detected year is the support-law citation rather than the PDF year."""

    if fiscal_year != 2019:
        return False
    normed = unicodedata.normalize("NFKC", sample_text)
    return "修学の支援に関する法律" in normed and ("令和元年度" in normed or "令和元年" in normed)


def _sample_has_explicit_stale_target_document_year(sample_text: str, *, target_year: int) -> bool:
    """Return whether the PDF body itself labels the target form as a stale fiscal year."""

    normed = unicodedata.normalize("NFKC", sample_text)
    target_form_markers = ("確認申請", "更新確認申請", "様式第2号", "様式2号", "機関要件")
    lines = normed.splitlines()

    def _line_has_stale_year(line: str) -> bool:
        if _YEAR_LABEL_REJECT_CONTEXT_RE.search(line):
            return False
        fiscal_year = fiscal_year_from_japanese_era_text(
            line,
            include_fiscal_year_labels=True,
            include_filing_dates=False,
        )
        if fiscal_year is not None and max(MIN_SUPPORTED_FISCAL_YEAR, target_year - 8) <= fiscal_year < target_year:
            return True
        for match in re.finditer(r"(?<!\d)(20\d{2})\s*年度", line):
            year = int(match.group(1))
            if max(MIN_SUPPORTED_FISCAL_YEAR, target_year - 8) <= year < target_year:
                return True
        return False

    for index, line in enumerate(lines):
        if not any(marker in line for marker in target_form_markers):
            continue
        for nearby in lines[max(0, index - 1) : min(len(lines), index + 2)]:
            if _line_has_stale_year(nearby):
                return True
    return False


def _target_url_hint_can_override_detected_year(
    candidate: PdfCandidate,
    sample_text: str,
    *,
    pdf_type: str,
    detected_fiscal_year: int,
    target_year: int,
) -> bool:
    """Return whether current-year URL evidence should beat noisy body years."""

    if pdf_type != "target":
        return False
    if detected_fiscal_year >= target_year:
        return False
    if not _has_target_year_hint(candidate, target_year=target_year):
        return False
    if not _has_target_form_hint(candidate):
        return False
    if _has_explicit_stale_fiscal_year_label(candidate, target_year=target_year):
        return False
    return not _sample_has_explicit_stale_target_document_year(sample_text, target_year=target_year)


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
    hinted_year = _fiscal_year_from_strong_candidate_hint(text, target_year=target_year)
    if hinted_year == target_year:
        score += 3.0
    if hinted_year == target_year - 1:
        score += 1.0

    # Bonus for pattern type reliability. Source-prefixed direct candidates
    # preserve extractor provenance without losing the old direct-link score.
    if candidate.pattern_type == "direct" or candidate.pattern_type.endswith("_direct"):
        score += 0.5
    elif candidate.pattern_type == "embed":
        score += 0.3

    candidate.score = score
    return score


def _candidate_download_tier(candidate: PdfCandidate, *, target_year: int) -> int:
    """Return a coarse download priority before score sorting.

    Dense disclosure pages often list hundreds of adjacent public PDFs. A raw
    score sort lets those generic files crowd out low-score form links such as
    WordPress Download Manager wrappers whose URL only contains ``様式``.
    """

    if _has_target_application_hint(candidate):
        return 0
    if _has_formish_candidate_hint(candidate):
        return 1
    return 2


def _candidate_download_year_rank(candidate: PdfCandidate, *, target_year: int) -> tuple[int, int]:
    """Prefer current target-year form links over stale or yearless form links."""

    hinted_year = _fiscal_year_from_strong_candidate_hint(_candidate_hint_text(candidate), target_year=target_year)
    if hinted_year == target_year:
        return (0, 0)
    if hinted_year is None:
        return (1, 0)
    return (2, -hinted_year)


def _prioritize_viable_candidates(
    candidates: list[PdfCandidate],
    *,
    target_year: int,
    school_name: str = "",
) -> tuple[list[PdfCandidate], list[PdfCandidate]]:
    """Prioritize target-like candidates and cap generic PDF scanning."""

    priority: list[tuple[int, int, tuple[int, int], int, PdfCandidate]] = []
    general: list[tuple[int, int, PdfCandidate]] = []
    for index, candidate in enumerate(candidates):
        tier = _candidate_download_tier(candidate, target_year=target_year)
        year_rank = _candidate_download_year_rank(candidate, target_year=target_year)
        school_rank = (
            0
            if school_name and _school_name_matches_link(f"{candidate.anchor_text} {candidate.pdf_url}", school_name)
            else 1
        )
        if tier < 2:
            priority.append((tier, school_rank, year_rank, index, candidate))
        else:
            general.append((school_rank, index, candidate))

    priority.sort(key=lambda item: (item[0], item[1], item[2], -item[4].score, item[3]))
    general.sort(key=lambda item: (item[0], -item[2].score, item[1]))
    ordered = [candidate for _, _, _, _, candidate in priority]
    ordered.extend(candidate for _, _, candidate in general[:MAX_GENERAL_CANDIDATE_SCAN])
    dropped = [candidate for _, _, candidate in general[MAX_GENERAL_CANDIDATE_SCAN:]]
    return ordered, dropped


def _extract_pdf_sample_text(content: bytes) -> str:
    """Extract a small text sample from the first pages of a PDF."""
    import io

    import pdfplumber

    with pdfplumber.open(io.BytesIO(content)) as pdf:
        sample_text = ""
        for page in pdf.pages[:5]:
            sample_text += (page.extract_text() or "") + "\n"
    return sample_text


def _extract_pdf_sample_school_name(sample_text: str) -> str:
    """Extract the declared school name from a target-form PDF sample."""

    normed = unicodedata.normalize("NFKC", sample_text)
    match = re.search(r"学校名(?:\(学部等名\))?[\s:：]*(.+?)(?:\n|$)", normed)
    if match is None:
        return ""
    school_name = match.group(1).strip()
    school_name = re.sub(r"\s*(?:設置者名|設置者|学校法人).*$", "", school_name)
    school_name = re.sub(r"^(?:名称】|称】|名】|】|\])+\s*", "", school_name)
    school_name = re.sub(r"\s*校長\s*.*$", "", school_name)
    return school_name.strip()


def _candidate_pdf_mentions_different_school(candidate: PdfCandidate, school_names: list[str]) -> bool:
    if not candidate.detected_school_name or not school_names:
        return False
    candidate_label = _school_link_label(candidate.detected_school_name)
    if len(candidate_label) < 4:
        return False
    for school_name in school_names:
        school_label = _school_link_label(school_name)
        if candidate_label == school_label:
            return False
    return True


_FILING_DATE_CONTEXT_RE = re.compile(r"(提出日|提出年月日|申請日|申請年月日|届出日|届出年月日|作成日|作成年月日)")
_FILING_DATE_REJECT_CONTEXT_RE = re.compile(r"(から|まで|任期|期間|在任|現職|前職|卒業|終了|修了)")
_YEAR_LABEL_REJECT_CONTEXT_RE = re.compile(
    r"(完成年度|から|まで|任期|期間|在任|現職|前職|卒業|終了|修了|就職|進学|退学|時間)"
)
_YEAR_MONTH_DATE_SUFFIX_RE = re.compile(r"\s*年\s*\d{1,2}\s*月")
_LAW_REFERENCE_SUFFIX_RE = re.compile(r"\s*年\s*法律\s*第?\s*\d+\s*号")
_SUPPORT_SYSTEM_START_MONTH_SUFFIX_RE = re.compile(r"\s*年\s*0?4\s*月\s*(?:から|より|以降)?")
_SUPPORT_SYSTEM_START_MONTH_REJECT_CONTEXT_RE = re.compile(
    r"(任期|期間|在任|現職|前職|卒業|終了|修了|就職|進学|退学)"
)


def _is_followed_by_year_month_date(text: str, end_index: int) -> bool:
    """Return whether a year token is followed by a month, i.e. a date."""

    return _YEAR_MONTH_DATE_SUFFIX_RE.match(text[end_index:]) is not None


def _is_followed_by_law_reference(text: str, end_index: int) -> bool:
    """Return whether an era-year token is part of a legal citation."""

    return _LAW_REFERENCE_SUFFIX_RE.match(text[end_index:]) is not None


def _is_support_system_start_month_hint(text: str, start_index: int, end_index: int) -> bool:
    """Return whether a year-month token denotes the target support-system start."""

    suffix = _SUPPORT_SYSTEM_START_MONTH_SUFFIX_RE.match(text[end_index:])
    if suffix is None:
        return False
    window = text[max(0, start_index - 80): min(len(text), end_index + suffix.end() + 100)]
    if _SUPPORT_SYSTEM_START_MONTH_REJECT_CONTEXT_RE.search(window):
        return False
    return _has_support_system_context(window)


def _within_detectable_year(fiscal_year: int | None, max_fiscal_year: int | None) -> int | None:
    if fiscal_year is None:
        return None
    if not _is_supported_fiscal_year(fiscal_year):
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


def _candidate_dedupe_year_preference(candidate: PdfCandidate, *, target_fiscal_year: int | None = None) -> int:
    """Return whether a duplicate candidate carries explicit fiscal-year context."""

    target_year = target_fiscal_year or settings.target_fiscal_year
    candidate_year = _fiscal_year_from_strong_candidate_hint(_candidate_hint_text(candidate), target_year=target_year)
    if candidate_year == target_year:
        return 2
    if candidate_year is not None or has_fiscal_year_text(_candidate_hint_text(candidate)):
        return 1
    return 0


def _candidate_dedupe_preference(candidate: PdfCandidate, *, target_fiscal_year: int | None = None) -> tuple[int, int]:
    """Return how useful a duplicate candidate's own URL/anchor context is."""

    if _has_target_application_hint(candidate):
        hint_preference = 3
    elif _has_target_form_hint(candidate):
        hint_preference = 2
    elif _has_formish_candidate_hint(candidate):
        hint_preference = 1
    else:
        hint_preference = 0
    return hint_preference, _candidate_dedupe_year_preference(candidate, target_fiscal_year=target_fiscal_year)


def _append_or_upgrade_candidate(
    candidates: list[PdfCandidate],
    index_by_key: dict[str, int],
    candidate: PdfCandidate,
    *,
    target_fiscal_year: int | None = None,
) -> None:
    """Append a PDF candidate, replacing weak duplicate anchor context."""

    key = _pdf_candidate_dedupe_key(candidate.pdf_url)
    existing_index = index_by_key.get(key)
    if existing_index is None:
        index_by_key[key] = len(candidates)
        candidates.append(candidate)
        return
    if _candidate_dedupe_preference(candidate, target_fiscal_year=target_fiscal_year) > _candidate_dedupe_preference(
        candidates[existing_index],
        target_fiscal_year=target_fiscal_year,
    ):
        candidates[existing_index] = candidate


def _pdf_delivery_pattern(url: str, raw_url: str, *, source: str | None = None) -> str:
    """Return a stable evidence pattern that preserves extractor provenance."""

    if "/wp-content/" in url:
        pattern = "wordpress"
    elif "?" in raw_url:
        pattern = "cache_busted"
    else:
        pattern = "direct"
    if source is None:
        return pattern
    return f"{source}_{pattern}"


def _html_text(fragment: str) -> str:
    text = html_lib.unescape(re.sub(r"<[^>]+>", " ", fragment))
    return re.sub(r"\s+", " ", text).strip()


def _html_title_text(html: str) -> str:
    title_match = re.search(r"<title\b[^>]*>(.*?)</title\s*>", html, re.IGNORECASE | re.DOTALL)
    if title_match is None:
        return ""
    return _html_text(title_match.group(1))


def _enclosing_html_block(html: str, start: int, end: int) -> tuple[str, int, int, str] | None:
    """Return the closest simple HTML block containing an anchor match."""

    prefix = html[:start]
    for tag in ("p", "li", "tr", "dd", "div"):
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


def _previous_definition_term_context(html: str, before: int) -> str:
    """Return the active fiscal-year term for a ``dd`` link."""

    prefix = html[:before]
    dl_start = prefix.lower().rfind("<dl")
    dl_end = prefix.lower().rfind("</dl")
    if dl_start == -1 or dl_end > dl_start:
        return ""

    dl_prefix = html[dl_start:before]
    for match in reversed(list(re.finditer(r"<dt\b[^>]*>.*?</dt\s*>", dl_prefix, re.IGNORECASE | re.DOTALL))):
        text = _html_text(match.group(0))
        if text and _has_strong_fiscal_year_context(text):
            return text
    return ""


def _has_fiscal_year_context(text: str) -> bool:
    return has_fiscal_year_text(text)


def _has_strong_fiscal_year_context(text: str) -> bool:
    """Return whether nearby HTML text names a fiscal year, not a date."""

    normed = unicodedata.normalize("NFKC", text)
    if re.search(r"(?<!\d)20\d{2}\s*年度", normed):
        return True
    return fiscal_year_from_japanese_era_text(
        normed,
        include_fiscal_year_labels=True,
        include_filing_dates=False,
    ) is not None


_WEAK_PUBLICATION_DATE_CONTEXT_RE = re.compile(r"(更新日|掲載日|公開日|投稿日|作成日|改定日|最終更新)")


def _is_weak_publication_date_context(text: str) -> bool:
    """Return whether text contains only date-like context for discovery use."""

    return _has_fiscal_year_context(text) and not _has_strong_fiscal_year_context(text) and bool(
        _WEAK_PUBLICATION_DATE_CONTEXT_RE.search(text)
    )


def _has_support_system_context(text: str) -> bool:
    return any(token in text for token in ("修学支援", "修学の支援", "高等教育", "無償化"))


def _has_application_form_context(text: str) -> bool:
    return any(
        token in text
        for token in (
            "確認申請",
            "確認申請書",
            "申請書",
            "申請様式",
            "様式第2号",
            "様式第２号",
            "様式2号",
            "機関要件",
        )
    )


def _previous_support_fiscal_year_context(html: str, before: int) -> str:
    """Return a nearby support-system paragraph that supplies fiscal-year context."""

    window = html[max(0, before - 3000):before]
    blocks = list(
        re.finditer(
            r"<(?:h[1-6]|p|li|dd)\b[^>]*>.*?</(?:h[1-6]|p|li|dd)\s*>",
            window,
            re.IGNORECASE | re.DOTALL,
        )
    )
    for block in reversed(blocks):
        text = _html_text(block.group(0))
        if text and _has_fiscal_year_context(text) and _has_support_system_context(text):
            return text
    return ""


def _section_heading_context(html: str, block_start: int) -> str:
    """Return heading context from the current HTML section."""

    prefix = html[:block_start]
    section_start = prefix.lower().rfind("<section")
    if section_start == -1:
        return ""
    section_end = prefix.lower().rfind("</section")
    if section_end > section_start:
        return ""

    section_prefix = html[section_start:block_start]
    headings: list[str] = []
    for heading in re.finditer(r"<h[1-6]\b[^>]*>.*?</h[1-6]\s*>", section_prefix, re.IGNORECASE | re.DOTALL):
        text = _html_text(heading.group(0))
        if text:
            headings.append(text)
    return " ".join(dict.fromkeys(headings))


def _div_heading_context(html: str, before: int) -> str:
    """Return the nearest WordPress group school heading for CMS sections."""

    window = html[max(0, before - 6000):before]
    group_starts = list(re.finditer(r"<div\b[^>]*\bwp-block-group\b[^>]*>", window, re.IGNORECASE | re.DOTALL))
    if not group_starts:
        return ""

    fragment = window[group_starts[-1].start():]
    headings = [
        _html_text(heading.group(0))
        for heading in re.finditer(r"<h[1-6]\b[^>]*>.*?</h[1-6]\s*>", fragment, re.IGNORECASE | re.DOTALL)
    ]
    for text in reversed([heading for heading in headings if heading]):
        if _candidate_named_school_labels(text):
            return text
    return ""


def _html_table_cells(row_fragment: str) -> list[tuple[int, int, str]]:
    return [
        (match.start(), match.end(), match.group(0))
        for match in re.finditer(r"<t[dh]\b[^>]*>.*?</t[dh]\s*>", row_fragment, re.IGNORECASE | re.DOTALL)
    ]


def _table_column_header_context(html: str, block_start: int, block_fragment: str, match: re.Match[str]) -> str:
    """Return same-column table header text for generic PDF links.

    Some school groups render disclosure tables with column headers such as
    ``確認申請書`` while each link's visible text is only ``PDF``. Without the
    header, the candidate looks generic and site-family prefilters can discard
    the target-form column together with syllabus and grade-policy columns.
    """

    local_anchor_start = match.start() - block_start
    current_cells = _html_table_cells(block_fragment)
    cell_index: int | None = None
    for index, (cell_start, cell_end, _) in enumerate(current_cells):
        if cell_start <= local_anchor_start < cell_end:
            cell_index = index
            break
    if cell_index is None:
        return ""

    prefix = html[:block_start]
    table_start = prefix.lower().rfind("<table")
    table_end = prefix.lower().rfind("</table")
    if table_start == -1 or table_end > table_start:
        return ""

    table_prefix = html[table_start:block_start]
    previous_rows = list(re.finditer(r"<tr\b[^>]*>.*?</tr\s*>", table_prefix, re.IGNORECASE | re.DOTALL))
    for row in reversed(previous_rows):
        cells = _html_table_cells(row.group(0))
        if cell_index >= len(cells):
            continue
        header_text = _html_text(cells[cell_index][2])
        if not header_text or not _has_application_form_context(header_text):
            continue
        title = _html_title_text(html)
        if title and _has_support_system_context(title):
            return f"{title} {header_text}"
        return header_text
    return ""


def _table_section_heading_context(html: str, block_start: int) -> str:
    """Return the closest school/section table heading before a row.

    O-Hara-style group disclosure pages put many schools into one table. The
    current row's nearest column header identifies the document type, while the
    nearest preceding colspan header identifies the school section.
    """

    prefix = html[:block_start]
    table_start = prefix.lower().rfind("<table")
    table_end = prefix.lower().rfind("</table")
    if table_start == -1 or table_end > table_start:
        return ""

    table_prefix = html[table_start:block_start]
    for heading in reversed(list(re.finditer(r"<th\b([^>]*)>(.*?)</th\s*>", table_prefix, re.IGNORECASE | re.DOTALL))):
        attrs = heading.group(1)
        if not re.search(r"\bcolspan\s*=", attrs, re.IGNORECASE):
            continue
        text = _html_text(heading.group(2))
        if text:
            return text
    return ""


def _has_visible_anchor_text(fragment: str) -> bool:
    return any(
        bool(_html_text(match.group(1)))
        for match in re.finditer(r"<a\b[^>]*>(.*?)</a\s*>", fragment, re.IGNORECASE | re.DOTALL)
    )


def _pdf_element_context_text(html: str, match: re.Match[str], element_text: str = "") -> str:
    """Return element text plus nearby fiscal-year context when the CMS splits it.

    Some CMS pages, notably Goope, render a year header in one paragraph and the
    PDF link in the next paragraph. Keeping that adjacent context lets strict
    discovery classify old target forms as publication-lag evidence instead of
    sending them to the target-year-unverified manual queue.
    """

    anchor = _html_text(element_text)
    parts = [anchor] if anchor else []
    block = _enclosing_html_block(html, match.start(), match.end())
    if block is not None:
        tag, block_start, _, block_fragment = block
        if not anchor and _has_visible_anchor_text(block_fragment):
            return ""
        current_text = _html_text(block_fragment)
        if (
            current_text
            and not _has_strong_fiscal_year_context(anchor)
            and _has_strong_fiscal_year_context(current_text)
            and current_text not in parts
        ):
            parts.append(current_text)
        previous_text = ""
        if tag == "li":
            previous_text = _previous_fiscal_year_context(html, block_start)
        elif tag in {"p", "tr", "dd"}:
            previous_text = _previous_html_block_text(html, block_start, tag)
            if tag == "dd" and not _has_strong_fiscal_year_context(previous_text):
                previous_text = _previous_definition_term_context(html, block_start) or _previous_fiscal_year_context(
                    html,
                    block_start,
                )
            elif tag == "p" and not _has_strong_fiscal_year_context(previous_text):
                previous_text = _previous_fiscal_year_context(html, block_start)
        has_current_year_context = any(_has_strong_fiscal_year_context(part) for part in parts)
        if previous_text and not has_current_year_context and _has_strong_fiscal_year_context(previous_text):
            parts.append(previous_text)
            has_current_year_context = True
        if not has_current_year_context and anchor and _has_application_form_context(anchor):
            support_year_text = _previous_support_fiscal_year_context(html, block_start)
            if support_year_text and support_year_text not in parts:
                parts.append(support_year_text)
                has_current_year_context = True
        if (
            anchor
            and _has_strong_fiscal_year_context(anchor)
            and not _has_target_application_hint(PdfCandidate(pdf_url="", page_url="", anchor_text=" ".join(parts)))
        ):
            section_context = _section_heading_context(html, block_start)
            if (
                section_context
                and _has_support_system_context(section_context)
                and _has_application_form_context(section_context)
                and section_context not in parts
            ):
                parts.append(section_context)
        div_heading = _div_heading_context(html, block_start)
        if div_heading and div_heading not in parts:
            parts.append(div_heading)
        if tag == "tr":
            if current_text and _candidate_named_school_labels(current_text) and current_text not in parts:
                parts.append(current_text)
            section_heading = _table_section_heading_context(html, block_start)
            if section_heading and section_heading not in parts:
                parts.append(section_heading)
            table_header = _table_column_header_context(html, block_start, block_fragment, match)
            if table_header and table_header not in parts:
                parts.append(table_header)
    else:
        div_heading = _div_heading_context(html, match.start())
        if div_heading and div_heading not in parts:
            parts.append(div_heading)
        if previous_text := _previous_fiscal_year_context(html, match.start()):
            parts.append(previous_text)
    return " ".join(dict.fromkeys(part for part in parts if part))


def _pdf_anchor_context_text(html: str, match: re.Match[str]) -> str:
    return _pdf_element_context_text(html, match, match.group(2))


def _wordpress_download_manager_anchor_context_text(html: str, match: re.Match[str]) -> str:
    parts = [_pdf_anchor_context_text(html, match)]
    block_text = _nearest_wordpress_download_manager_block_text(html, match.start())
    if block_text:
        parts.append(block_text)
    return " ".join(dict.fromkeys(part for part in parts if part))


def _nearest_wordpress_download_manager_block_text(html: str, anchor_start: int) -> str:
    window_start = max(0, anchor_start - 2000)
    prefix = html[window_start:anchor_start]
    div_matches = list(re.finditer(r"<div\b([^>]*)>", prefix, re.IGNORECASE | re.DOTALL))
    for div_match in reversed(div_matches):
        class_attr = _anchor_attr(div_match.group(1), "class") or ""
        classes = set(class_attr.lower().split())
        if "media" not in classes:
            continue
        fragment = _balanced_div_fragment(html, window_start + div_match.start())
        text = _html_text(fragment)
        if text:
            return text
    return ""


def _balanced_div_fragment(html: str, start: int) -> str:
    depth = 0
    for tag in re.finditer(r"</?div\b[^>]*>", html[start:], re.IGNORECASE | re.DOTALL):
        if tag.group(0).lower().startswith("</div"):
            depth -= 1
        else:
            depth += 1
        if depth == 0:
            return html[start:start + tag.end()]
    return html[start:min(len(html), start + 2000)]


def _previous_fiscal_year_context(html: str, before: int) -> str:
    """Return nearby preceding year context for CMS download widgets."""

    window = html[max(0, before - 2000):before]
    block_re = r"<(?:p|li|dt|dd|h[1-6])\b[^>]*>.*?</(?:p|li|dt|dd|h[1-6])\s*>"
    for match in reversed(list(re.finditer(block_re, window, re.IGNORECASE | re.DOTALL))):
        text = _html_text(match.group(0))
        if not text:
            continue
        if _has_strong_fiscal_year_context(text):
            return text
        if _is_weak_publication_date_context(text):
            continue
        return ""

    text = _html_text(window)
    for line in reversed(re.split(r"[\n。]+", text)):
        line = line.strip()
        if not line:
            continue
        if _has_strong_fiscal_year_context(line):
            return line
        if _is_weak_publication_date_context(line):
            continue
        break
    return ""


def _anchor_attr(attrs: str, name: str) -> str | None:
    match = re.search(rf"(?:^|\s){re.escape(name)}\s*=\s*([\"'])(.*?)\1", attrs, re.IGNORECASE | re.DOTALL)
    if match is None:
        return None
    return html_lib.unescape(match.group(2))


def _pdf_url_from_meta_refresh_content(content: str, base_url: str) -> str | None:
    """Extract a PDF target from a meta refresh content attribute."""

    match = re.search(r"(?:^|;)\s*url\s*=\s*(.+?)\s*$", html_lib.unescape(content), re.IGNORECASE)
    if match is None:
        return None
    href = match.group(1).strip().strip("\"'")
    if not href or ".pdf" not in unquote(href).lower():
        return None
    return str(urljoin(base_url, href))


def _pdf_urls_from_script_attribute(value: str, base_url: str) -> list[str]:
    """Extract quoted PDF URLs from static click-handler attributes."""

    urls: list[str] = []
    seen: set[str] = set()
    for match in PDF_SCRIPT_URL_PATTERN.finditer(html_lib.unescape(value)):
        href = match.group(2).strip()
        if not href or ".pdf" not in unquote(href).lower():
            continue
        url = urljoin(base_url, href)
        key = normalize_candidate_url(url)
        if key in seen:
            continue
        seen.add(key)
        urls.append(url)
    return urls


def _pdf_form_control_text(fragment: str) -> str:
    """Return visible form text plus labels from void controls."""

    parts = [_html_text(fragment)]
    for match in re.finditer(r"<(?:input|button)\s([^>]*)>", fragment, re.IGNORECASE | re.DOTALL):
        attrs = match.group(1)
        for attr_name in ("value", "aria-label", "title"):
            value = _anchor_attr(attrs, attr_name)
            if value:
                parts.append(value)
                break
    return " ".join(dict.fromkeys(part for part in parts if part))


def _is_wordpress_download_manager_url(url: str, base_url: str) -> bool:
    """Return whether ``url`` is a same-origin WordPress Download Manager PDF wrapper."""

    parsed = urlparse(url)
    base_parsed = urlparse(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return False
    if parsed.netloc != base_parsed.netloc:
        return False
    return any(key.lower() == "wpdmdl" and value.strip() for key, value in parse_qsl(parsed.query))


def _trusted_year_evidence_can_fill_missing_pdf_year(
    candidate: PdfCandidate,
    *,
    pdf_type: str,
    trusted_year_evidence: str,
    target_year: int,
) -> bool:
    """Return whether source freshness may replace PDF/link year evidence.

    Current prefecture indexes prove that the registered disclosure URL is
    worth crawling, but not that a yearless PDF is the current target form.
    Exact school-domain disclosure overrides are narrower: when they point to
    a disclosure page and the candidate itself names the target form shape,
    the override can fill the missing PDF year unless the candidate carries an
    explicit stale-year label.
    """

    if pdf_type != "target":
        return False
    if _has_explicit_stale_fiscal_year_label(candidate, target_year=target_year):
        return False
    if trusted_year_evidence == "school_domain_override_disclosure":
        return _has_specific_target_form_hint(candidate) or _has_known_embedded_study_support_target_form(candidate)
    if trusted_year_evidence == "prefecture_index_current_year":
        return _has_specific_target_form_hint(candidate) or _has_known_embedded_study_support_target_form(candidate)
    return False


def _extract_pdf_links(
    html: str,
    base_url: str,
    *,
    target_fiscal_year: int | None = None,
    experimental_extractors: bool | None = None,
) -> list[PdfCandidate]:
    """Extract PDF link candidates from HTML using known PDF delivery patterns."""
    html = re.sub(r"<!--.*?-->", "", html, flags=re.DOTALL)
    candidates: list[PdfCandidate] = []
    candidate_index_by_key: dict[str, int] = {}
    experimental_enabled = (
        settings.pdf_discovery_experimental_extractors
        if experimental_extractors is None
        else experimental_extractors
    )

    # Pattern 1: Direct PDF links — a href values that point at PDFs.
    # Parse the full attribute block so ``data-href`` is not misclassified as
    # a plain direct link.
    for m in re.finditer(
        r"<a\s([^>]*)>(.*?)</a\s*>",
        html, re.IGNORECASE | re.DOTALL,
    ):
        href = _anchor_attr(m.group(1), "href")
        if not href or ".pdf" not in unquote(href).lower():
            continue
        url = urljoin(base_url, href)
        anchor = _pdf_anchor_context_text(html, m)
        pattern = _pdf_delivery_pattern(url, href)
        _append_or_upgrade_candidate(
            candidates,
            candidate_index_by_key,
            PdfCandidate(
                pdf_url=url, page_url=base_url, anchor_text=anchor, pattern_type=pattern,
            ),
            target_fiscal_year=target_fiscal_year,
        )

    # The patterns below are intentionally opt-in. They are covered by
    # synthetic parser tests but still lack real school-page gold-set
    # demonstrations, so production discovery keeps them out of the default
    # release surface until a manual success case exists.
    if experimental_enabled:
        # Pattern 1a: HTML redirect pages whose meta refresh points directly at a PDF.
        for m in re.finditer(PDF_META_REFRESH_PATTERN, html, re.IGNORECASE | re.DOTALL):
            http_equiv = _anchor_attr(m.group(1), "http-equiv")
            if not http_equiv or http_equiv.strip().lower() != "refresh":
                continue
            content = _anchor_attr(m.group(1), "content")
            if not content:
                continue
            meta_url = _pdf_url_from_meta_refresh_content(content, base_url)
            if not meta_url:
                continue
            pattern = _pdf_delivery_pattern(meta_url, meta_url, source="meta_refresh")
            _append_or_upgrade_candidate(
                candidates,
                candidate_index_by_key,
                PdfCandidate(
                    pdf_url=meta_url,
                    page_url=base_url,
                    anchor_text=_html_title_text(html),
                    pattern_type=pattern,
                ),
                target_fiscal_year=target_fiscal_year,
            )

        # Pattern 1b: year/select dropdowns whose option values are PDF URLs.
        for m in re.finditer(
            PDF_OPTION_VALUE_PATTERN,
            html,
            re.IGNORECASE | re.DOTALL,
        ):
            href = _anchor_attr(m.group(1), "value")
            if not href or ".pdf" not in unquote(href).lower():
                continue
            url = urljoin(base_url, href)
            pattern = _pdf_delivery_pattern(url, href, source="select_option")
            _append_or_upgrade_candidate(
                candidates,
                candidate_index_by_key,
                PdfCandidate(
                    pdf_url=url,
                    page_url=base_url,
                    anchor_text=_pdf_anchor_context_text(html, m),
                    pattern_type=pattern,
                ),
                target_fiscal_year=target_fiscal_year,
            )

        # Pattern 1c: form submit buttons whose action points directly at a PDF.
        for m in re.finditer(
            PDF_FORM_ACTION_PATTERN,
            html,
            re.IGNORECASE | re.DOTALL,
        ):
            href = _anchor_attr(m.group(1), "action")
            if not href or ".pdf" not in unquote(href).lower():
                continue
            url = urljoin(base_url, href)
            pattern = _pdf_delivery_pattern(url, href, source="form_action")
            _append_or_upgrade_candidate(
                candidates,
                candidate_index_by_key,
                PdfCandidate(
                    pdf_url=url,
                    page_url=base_url,
                    anchor_text=_pdf_element_context_text(html, m, _pdf_form_control_text(m.group(2))),
                    pattern_type=pattern,
                ),
                target_fiscal_year=target_fiscal_year,
            )

        # Pattern 1d: JavaScript/download-button elements with direct PDF data attributes.
        for m in re.finditer(
            rf"<{PDF_DATA_ATTRIBUTE_TAG_PATTERN}\s([^>]*)>(.*?)</{PDF_DATA_ATTRIBUTE_TAG_PATTERN}\s*>",
            html, re.IGNORECASE | re.DOTALL,
        ):
            attrs = m.group(1)
            for attr_name in PDF_LINK_ATTRIBUTE_NAMES:
                href = _anchor_attr(attrs, attr_name)
                if not href or ".pdf" not in unquote(href).lower():
                    continue
                url = urljoin(base_url, href)
                pattern = _pdf_delivery_pattern(url, href, source="data_attribute")
                _append_or_upgrade_candidate(
                    candidates,
                    candidate_index_by_key,
                    PdfCandidate(
                        pdf_url=url,
                        page_url=base_url,
                        anchor_text=_pdf_anchor_context_text(html, m),
                        pattern_type=pattern,
                    ),
                    target_fiscal_year=target_fiscal_year,
                )
                break

        # Pattern 1e: static click handlers such as window.open('/docs/form.pdf').
        for m in re.finditer(
            rf"<{PDF_DATA_ATTRIBUTE_TAG_PATTERN}\s([^>]*)>(.*?)</{PDF_DATA_ATTRIBUTE_TAG_PATTERN}\s*>",
            html,
            re.IGNORECASE | re.DOTALL,
        ):
            onclick = _anchor_attr(m.group(1), "onclick")
            if not onclick:
                continue
            for url in _pdf_urls_from_script_attribute(onclick, base_url):
                pattern = _pdf_delivery_pattern(url, url, source="onclick")
                _append_or_upgrade_candidate(
                    candidates,
                    candidate_index_by_key,
                    PdfCandidate(
                        pdf_url=url,
                        page_url=base_url,
                        anchor_text=_pdf_anchor_context_text(html, m),
                        pattern_type=pattern,
                    ),
                    target_fiscal_year=target_fiscal_year,
                )

        # Pattern 1f: void input controls with direct PDF data attributes or click handlers.
        for m in re.finditer(PDF_INPUT_TAG_PATTERN, html, re.IGNORECASE | re.DOTALL):
            attrs = m.group(1)
            element_text = (
                _anchor_attr(attrs, "value")
                or _anchor_attr(attrs, "aria-label")
                or _anchor_attr(attrs, "title")
                or ""
            )
            for attr_name in PDF_LINK_ATTRIBUTE_NAMES:
                href = _anchor_attr(attrs, attr_name)
                if not href or ".pdf" not in unquote(href).lower():
                    continue
                url = urljoin(base_url, href)
                pattern = _pdf_delivery_pattern(url, href, source="input_control")
                _append_or_upgrade_candidate(
                    candidates,
                    candidate_index_by_key,
                    PdfCandidate(
                        pdf_url=url,
                        page_url=base_url,
                        anchor_text=_pdf_element_context_text(html, m, element_text),
                        pattern_type=pattern,
                    ),
                    target_fiscal_year=target_fiscal_year,
                )
                break
            onclick = _anchor_attr(attrs, "onclick")
            if not onclick:
                continue
            for url in _pdf_urls_from_script_attribute(onclick, base_url):
                pattern = _pdf_delivery_pattern(url, url, source="input_control")
                _append_or_upgrade_candidate(
                    candidates,
                    candidate_index_by_key,
                    PdfCandidate(
                        pdf_url=url,
                        page_url=base_url,
                        anchor_text=_pdf_element_context_text(html, m, element_text),
                        pattern_type=pattern,
                    ),
                    target_fiscal_year=target_fiscal_year,
                )

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
        _append_or_upgrade_candidate(
            candidates,
            candidate_index_by_key,
            PdfCandidate(
                pdf_url=url,
                page_url=base_url,
                anchor_text=_wordpress_download_manager_anchor_context_text(html, m),
                pattern_type="wordpress_download_manager",
            ),
            target_fiscal_year=target_fiscal_year,
        )

    # Pattern 4: Embedded PDFs — embed/object/iframe with .pdf src/data
    for tag in PDF_EMBED_TAG_NAMES:
        for attr in PDF_EMBED_ATTRIBUTE_NAMES:
            for m in re.finditer(
                rf'<{tag}\s[^>]*{attr}=["\']([^"\']*\.pdf(?:[?#][^"\']*)?)["\']',
                html, re.IGNORECASE,
            ):
                href = html_lib.unescape(m.group(1))
                url = urljoin(base_url, href)
                _append_or_upgrade_candidate(
                    candidates,
                    candidate_index_by_key,
                    PdfCandidate(
                        pdf_url=url,
                        page_url=base_url,
                        anchor_text=_pdf_element_context_text(html, m),
                        pattern_type="embed",
                    ),
                    target_fiscal_year=target_fiscal_year,
                )

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
        urls.append(_without_url_fragment(resolved))
    direct_url = _without_url_fragment(url)
    if direct_url not in urls:
        urls.append(direct_url)
    return urls


def _without_url_fragment(url: str) -> str:
    parsed = urlparse(url)
    if not parsed.fragment:
        return url
    return parsed._replace(fragment="").geturl()


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
_SCHOOL_ENTITY_RE = re.compile(
    r"[一-龯ぁ-んァ-ヶA-Za-z0-9&・･ー－\-（）()]{2,}"
    r"(?:専門学校|大学校|短期大学|高等専門学校)",
    re.IGNORECASE,
)
_LEADING_SPECIALIZED_SCHOOL_ENTITY_RE = re.compile(
    r"専門学校[一-龯ぁ-んァ-ヶA-Za-z0-9&・･ー－\-]{2,}",
    re.IGNORECASE,
)
_GENERIC_SCHOOL_ENTITY_CONTEXT_RE = re.compile(r"(?:における|に関する|対象となる|学校一覧)")


def _school_link_label(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text).lower()
    normalized = normalized.replace("専門学校", "")
    return re.sub(r"[\s　・･\-ー–—_/／|｜()（）［］\\[\\]{}]+", "", normalized)


def _school_name_matches_link(text: str, school_name: str) -> bool:
    school_label = _school_link_label(school_name)
    link_label = _school_link_label(text)
    return len(school_label) >= 4 and school_label in link_label


def _school_name_matches_homepage_link(text: str, school_name: str) -> bool:
    if not _school_name_matches_link(text, school_name):
        return False

    school_label = _school_link_label(school_name)
    for candidate_label in _candidate_named_school_labels(text):
        if candidate_label == school_label:
            return True
        if school_label in candidate_label:
            return False
    return True


def _school_label_is_same_or_campus_variant(candidate_label: str, school_label: str) -> bool:
    """Return whether two normalized school labels refer to the same school.

    Plain substring matching is too broad for dense corporation pages:
    ``大原法律`` must not match ``大原法律公務員``.  We only allow containment
    when the extra suffix is a campus/location suffix such as ``大宮校``.
    """

    if candidate_label == school_label:
        return True
    if len(candidate_label) < 4 or len(school_label) < 4:
        return False
    for base, extended in ((candidate_label, school_label), (school_label, candidate_label)):
        if not extended.startswith(base):
            continue
        suffix = extended[len(base):]
        if suffix and re.fullmatch(r"[\u3040-\u30ff\u3400-\u9fffA-Za-z0-9]+校", suffix):
            return True
    return False


def _candidate_mentions_different_school(candidate: PdfCandidate, school_name: str) -> bool:
    if not school_name:
        return False
    text = unicodedata.normalize(
        "NFKC",
        f"{candidate.anchor_text or ''} {candidate.pdf_url or ''} {unquote(candidate.pdf_url or '')}",
    )
    school_label = _school_link_label(school_name)
    for candidate_label in _candidate_named_school_labels(text):
        if _school_label_is_same_or_campus_variant(candidate_label, school_label):
            return False
        return True
    return False


def _candidate_named_school_labels(text: str) -> list[str]:
    labels: list[str] = []
    normalized = unicodedata.normalize("NFKC", text)
    for pattern in (_SCHOOL_ENTITY_RE, _LEADING_SPECIALIZED_SCHOOL_ENTITY_RE):
        for match in pattern.finditer(normalized):
            raw_label = match.group(0)
            if _GENERIC_SCHOOL_ENTITY_CONTEXT_RE.search(raw_label):
                continue
            if raw_label.startswith("専門学校"):
                prefix = raw_label.removeprefix("専門学校")
            else:
                prefix = re.split(r"専門学校|大学校|短期大学|高等専門学校", raw_label, maxsplit=1)[0]
            if not re.search(r"[一-龯ァ-ヶA-Za-z0-9]", prefix):
                continue
            label = _school_link_label(raw_label)
            if len(label) >= 4 and label not in labels:
                labels.append(label)
    return labels


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
        if not _school_name_matches_homepage_link(f"{text} {href}", school_name):
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


def _is_file_like_disclosure_path(path_segment: str) -> bool:
    lowered = path_segment.lower()
    return any(lowered.endswith(suffix) for suffix in DISCLOSURE_DERIVATION_FILE_SUFFIXES)


def _derived_disclosure_page_urls(site_url: str, *, limit: int = 6) -> list[str]:
    """Return conservative same-host disclosure URL guesses from a school homepage URL."""
    if limit <= 0:
        return []

    parsed = urlparse(site_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return []

    path = parsed.path.rstrip("/")
    raw_segments = [segment for segment in path.split("/") if segment]
    file_like_path = bool(raw_segments) and _is_file_like_disclosure_path(raw_segments[-1])
    slug = "" if file_like_path else raw_segments[-1] if raw_segments else ""
    root = f"{parsed.scheme}://{parsed.netloc}"
    path_or_root = "" if file_like_path else path or ""
    seen: set[str] = {normalize_candidate_url(site_url)}
    urls: list[str] = []

    if len(raw_segments) >= 2 and raw_segments[-1].lower() in {"disclosure", "information", "public", "public_info"}:
        inverted_path = f"/{raw_segments[-1]}/{raw_segments[-2]}"
        inverted_url = urljoin(root + "/", inverted_path.lstrip("/"))
        seen.add(normalize_candidate_url(inverted_url))
        urls.append(inverted_url)
        if len(urls) >= limit:
            return urls

    for host_path in HOST_SPECIFIC_DERIVED_DISCLOSURE_PATHS.get((parsed.hostname or "").lower(), ()):
        candidate_url = urljoin(root + "/", host_path.lstrip("/"))
        key = normalize_candidate_url(candidate_url)
        if key in seen:
            continue
        seen.add(key)
        urls.append(candidate_url)
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


def _has_inverted_disclosure_url_probe(site_url: str) -> bool:
    """Return whether the first derived URL is a school-specific path inversion.

    Large corporation domains often publish official-index URLs as
    ``/school/disclosure/`` while the live page is ``/disclosure/school``.
    Shared-origin throttling may skip generic derived probing for performance,
    but this one inverted URL is per-school rather than shared root work.
    """

    parsed = urlparse(site_url)
    raw_segments = [segment for segment in parsed.path.rstrip("/").split("/") if segment]
    return len(raw_segments) >= 2 and raw_segments[-1].lower() in {
        "disclosure",
        "information",
        "public",
        "public_info",
    }


def _has_host_specific_disclosure_url_probe(site_url: str) -> bool:
    parsed = urlparse(site_url)
    return (parsed.hostname or "").lower() in HOST_SPECIFIC_DERIVED_DISCLOSURE_PATHS


def _has_priority_derived_disclosure_url_probe(site_url: str) -> bool:
    """Return whether one derived disclosure URL should bypass shared-origin throttling."""

    return _has_inverted_disclosure_url_probe(site_url) or _has_host_specific_disclosure_url_probe(site_url)


def _sitemap_urls_for_site(
    client: HttpGetClient,
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


def _sitemap_entry_urls_for_site(client: HttpGetClient, site_url: str) -> list[str]:
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


def _append_unique_candidates(
    target: list[PdfCandidate],
    additions: list[PdfCandidate],
    *,
    target_fiscal_year: int | None = None,
) -> None:
    """Append candidates not already present by PDF URL."""
    index_by_key = {_pdf_candidate_dedupe_key(candidate.pdf_url): index for index, candidate in enumerate(target)}
    for candidate in additions:
        _append_or_upgrade_candidate(target, index_by_key, candidate, target_fiscal_year=target_fiscal_year)


def _needs_rendered_html_fallback(candidates: list[PdfCandidate], *, target_fiscal_year: int) -> bool:
    """Return whether JS-rendered HTML may add missing current-year candidates."""

    if not candidates:
        return True
    return not any(
        _has_target_year_hint(candidate, target_year=target_fiscal_year)
        and _has_target_application_hint(candidate)
        for candidate in candidates
    )


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
    target_fiscal_year: int | None = None,
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

        _append_unique_candidates(
            candidates,
            _extract_pdf_links(html, page_url, target_fiscal_year=target_fiscal_year),
            target_fiscal_year=target_fiscal_year,
        )

        for sub_url in _find_subpage_links(html, page_url):
            sub_key = normalize_candidate_url(sub_url)
            if sub_key in seen_pages or any(normalize_candidate_url(queued) == sub_key for queued in queue):
                continue
            if len(queue) + fetched >= max_pages:
                break
            queue.append(sub_url)

    return fetched


def discover_pdfs_for_site(
    client: HttpGetClient,
    school_id: int,
    site_url: str,
    max_depth: int = 2,
    max_extra_pages: int = MAX_DISCOVERY_EXTRA_PAGES,
    max_elapsed_seconds: float = MAX_DISCOVERY_ELAPSED_SECONDS,
    derived_disclosure_limit: int | None = None,
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
            result.error_code = "unsafe_url"
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
                        result.error_code = "robots_disallow_all"
                        return result
        except httpx.HTTPError:
            pass  # No robots.txt or unreachable, proceed

        _sleep_before_uncached_get(client, site_url)  # Design: max 1 uncached req/sec per domain.

        # Fetch main page (with safe redirect following)
        resp, site_url = _main_page_response_with_root_fallback(client, site_url)
        html = resp.text

        # Short/truncated HTML retry (TCA pattern)
        if len(html) < 500 and resp.status_code == 200:
            time.sleep(1.0)
            resp = _safe_get(client, site_url)
            html = resp.text

        # Extract PDF candidates from main page
        candidates = _extract_pdf_links(html, site_url, target_fiscal_year=target_year)

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
                    _sleep_before_uncached_get(client, sub_url)
                    extra_pages_fetched += 1
                    sub_resp = _safe_get(client, sub_url)
                    if sub_resp.status_code == 200:
                        sub_base_url = str(sub_resp.url or sub_url)
                        sub_candidates = _extract_pdf_links(
                            sub_resp.text,
                            sub_base_url,
                            target_fiscal_year=target_year,
                        )
                        _append_unique_candidates(candidates, sub_candidates, target_fiscal_year=target_year)
                except httpx.HTTPError:
                    continue

        school_homepage_page_urls: list[str] = []
        if max_depth > 0 and school_name:
            for homepage_url in _find_school_homepage_links(html, site_url, school_name):
                if extra_page_budget_remaining() <= 0:
                    break
                try:
                    _sleep_before_uncached_get(client, homepage_url)
                    extra_pages_fetched += 1
                    homepage_resp = _safe_get(client, homepage_url)
                    if homepage_resp.status_code != 200:
                        continue
                    homepage_base_url = str(homepage_resp.url or homepage_url)
                    school_homepage_page_urls.append(homepage_base_url)
                    homepage_html = homepage_resp.text
                    _append_unique_candidates(
                        candidates,
                        _extract_pdf_links(homepage_html, homepage_base_url, target_fiscal_year=target_year),
                        target_fiscal_year=target_year,
                    )
                    for sub_url in _find_subpage_links(homepage_html, homepage_base_url, school_name=school_name):
                        if extra_page_budget_remaining() <= 0:
                            break
                        if not _is_safe_url(sub_url):
                            continue
                        try:
                            _sleep_before_uncached_get(client, sub_url)
                            extra_pages_fetched += 1
                            sub_resp = _safe_get(client, sub_url)
                            if sub_resp.status_code == 200:
                                sub_base_url = str(sub_resp.url or sub_url)
                                school_homepage_page_urls.append(sub_base_url)
                                _append_unique_candidates(
                                    candidates,
                                    _extract_pdf_links(sub_resp.text, sub_base_url, target_fiscal_year=target_year),
                                    target_fiscal_year=target_year,
                                )
                        except httpx.HTTPError:
                            continue
                except httpx.HTTPError:
                    continue

        derived_budget = max(extra_page_budget_remaining() - SITEMAP_DISCOVERY_RESERVED_PAGES, 0)
        if derived_disclosure_limit is not None:
            derived_budget = min(derived_budget, max(derived_disclosure_limit, 0))
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
                _sleep_before_uncached_get(client, derived_url)
                extra_pages_fetched += 1
                derived_resp = _safe_get(client, derived_url)
                if derived_resp.status_code == 200:
                    derived_base_url = str(derived_resp.url or derived_url)
                    _append_unique_candidates(
                        candidates,
                        _extract_pdf_links(derived_resp.text, derived_base_url, target_fiscal_year=target_year),
                        target_fiscal_year=target_year,
                    )
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
                    target_fiscal_year=target_year,
                )
                continue
            sitemap_page_urls.append(sitemap_url)
            try:
                _sleep_before_uncached_get(client, sitemap_url)
                extra_pages_fetched += 1
                sitemap_resp = _safe_get(client, sitemap_url)
                if sitemap_resp.status_code == 200:
                    sitemap_base_url = str(sitemap_resp.url or sitemap_url)
                    _append_unique_candidates(
                        candidates,
                        _extract_pdf_links(sitemap_resp.text, sitemap_base_url, target_fiscal_year=target_year),
                        target_fiscal_year=target_year,
                    )
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
                    target_fiscal_year=target_year,
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
        result.error_code = "timeout"
        result.error_retryable = True
    except httpx.HTTPError as e:
        result.error = str(e)
        result.error_code = type(e).__name__

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
    client: HttpGetClient,
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
            except (httpx.HTTPError, httpx.InvalidURL) as e:
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
            candidate.detected_school_name = _extract_pdf_sample_school_name(sample_text)
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
            trusted_year_evidence = candidate.trusted_year_evidence.strip()
            target_year_hint = _has_target_year_hint(candidate, target_year=target_year)
            trusted_year_can_fill_missing_pdf_year = _trusted_year_evidence_can_fill_missing_pdf_year(
                candidate,
                pdf_type=pdf_type,
                trusted_year_evidence=trusted_year_evidence,
                target_year=target_year,
            )
            image_only_target_year_form_hint = (
                pdf_type == "image_only"
                and target_year_hint
                and _has_specific_target_form_hint(candidate)
            )
            if pdf_type == "non_target":
                return None, None, 0, "non_target", "classified_non_target"
            if detected_fiscal_year is not None and detected_fiscal_year != target_year:
                if (
                    pdf_type == "target"
                    and target_year_hint
                    and _has_disclosure_path_target_year_hint(candidate, target_year=target_year)
                    and _is_support_law_reference_year(sample_text, fiscal_year=detected_fiscal_year)
                ) or _target_url_hint_can_override_detected_year(
                    candidate,
                    sample_text,
                    pdf_type=pdf_type,
                    detected_fiscal_year=detected_fiscal_year,
                    target_year=target_year,
                ):
                    detected_fiscal_year = None
                    candidate.detected_fiscal_year = None
                else:
                    return None, None, 0, pdf_type, f"fiscal_year_mismatch:{detected_fiscal_year}"
            stale_hint_year = _stale_fiscal_year_from_candidate_hint(candidate, target_year=target_year)
            if (
                detected_fiscal_year is None
                and stale_hint_year is not None
                and (pdf_type == "target" or _has_target_form_hint(candidate))
            ):
                if pdf_type == "target" and trusted_year_evidence and not _has_explicit_stale_fiscal_year_label(
                    candidate,
                    target_year=target_year,
                ):
                    stale_hint_year = None
                else:
                    return None, None, 0, pdf_type, f"fiscal_year_mismatch:{stale_hint_year}"
            if (
                detected_fiscal_year == target_year
                and pdf_type == "image_only"
                and not _has_target_application_hint(candidate)
            ):
                return None, None, 0, pdf_type, "target_application_not_detected"
            if detected_fiscal_year is None and not image_only_target_year_form_hint and not (
                pdf_type == "target" and target_year_hint
            ) and not (
                trusted_year_can_fill_missing_pdf_year
            ):
                return None, None, 0, pdf_type, "target_fiscal_year_not_detected"
            if detected_fiscal_year == target_year:
                candidate.year_evidence = "pdf_text"
            elif target_year_hint:
                candidate.year_evidence = "url_hint"
            elif trusted_year_can_fill_missing_pdf_year:
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


def _remove_duplicate_candidate_file(file_path: str, existing: Document | None) -> None:
    """Remove a duplicate candidate download without deleting the canonical stored file."""

    if existing is not None and existing.file_path:
        candidate_path = Path(file_path)
        existing_path = Path(existing.file_path)
        if candidate_path == existing_path:
            return
        if candidate_path.resolve(strict=False) == existing_path.resolve(strict=False):
            return
    Path(file_path).unlink(missing_ok=True)


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
        "cached_rejection_evidence_suppressed": 0,
        "prefiltered": 0,
        "candidate_budget_limited": 0,
        "candidate_budget_dropped": 0,
        "candidate_school_mismatch": 0,
        "http_cache_hits": 0,
        "http_cache_misses": 0,
        "shared_origin_derived_fallback_skipped": 0,
    }
    recorder = EvidenceRecorder(evidence_path)

    def record_discovery_evidence(evidence: RejectionEvidence, *, persist: bool = True) -> None:
        if "target_fiscal_year" not in evidence.extra:
            evidence = replace(evidence, extra={**evidence.extra, "target_fiscal_year": str(target_year)})
        _increment_rejection_reason(stats, evidence.reason)
        if persist:
            recorder.record(evidence)

    target_year = target_fiscal_year or settings.target_fiscal_year
    rejected_candidate_cache: dict[tuple[int, str, int | None, bool, str], CachedPdfRejection] = {}

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
        .order_by(SchoolSite.confidence.desc(), SchoolSite.school_id.asc(), SchoolSite.id.asc())
        .limit(batch_size)
        .all()
    )
    origin_site_counts: dict[str, int] = {}
    for site in sites:
        origin = _origin_key(site.url)
        if origin is not None:
            origin_site_counts[origin] = origin_site_counts.get(origin, 0) + 1
    origin_derived_probe_counts: dict[str, int] = {}

    log.info("pdf_discovery_start", sites=len(sites))
    if progress_callback is not None:
        progress_callback(dict(stats), len(sites))

    with closing(recorder), httpx.Client(
        timeout=max(float(request_timeout), 1.0),
        follow_redirects=False,
        headers=HEADERS,
    ) as base_client:
        client = _RunScopedHttpCache(cast(HttpGetClient, base_client), stats=stats)
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
                derived_disclosure_limit: int | None = None
                origin = _origin_key(site.url)
                if (
                    origin is not None
                    and origin_site_counts.get(origin, 0) >= SHARED_ORIGIN_DERIVED_FALLBACK_THRESHOLD
                ):
                    probe_count = origin_derived_probe_counts.get(origin, 0)
                    if probe_count >= SHARED_ORIGIN_DERIVED_FALLBACK_PROBE_SITES:
                        if _has_priority_derived_disclosure_url_probe(site.url):
                            derived_disclosure_limit = 1
                        else:
                            derived_disclosure_limit = 0
                            stats["shared_origin_derived_fallback_skipped"] += 1
                    else:
                        origin_derived_probe_counts[origin] = probe_count + 1
                result = discover_pdfs_for_site(
                    client,
                    site.school_id,
                    site.url,
                    school_name=site.school.school_name if site.school is not None else "",
                    target_fiscal_year=target_year,
                    derived_disclosure_limit=derived_disclosure_limit,
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
                    extra=_discovery_error_extra(result),
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
            school_name = site.school.school_name if site.school is not None else ""
            school_names = [school_name] if school_name else []
            if site.school is not None:
                school_names.extend(alias.alias_name for alias in site.school.aliases if alias.alias_name)
            viable = [c for c in result.candidates if c.score >= 0 or _has_target_application_hint(c)]
            school_mismatch_candidates = [
                c for c in viable if _candidate_mentions_different_school(c, school_name)
            ]
            if school_mismatch_candidates:
                stats["candidate_school_mismatch"] += len(school_mismatch_candidates)
                mismatch_ids = {id(c) for c in school_mismatch_candidates}
                viable = [c for c in viable if id(c) not in mismatch_ids]
                for evidence_index, c in enumerate(school_mismatch_candidates):
                    record_discovery_evidence(RejectionEvidence(
                        school_id=site.school_id,
                        pdf_url=c.pdf_url,
                        page_url=c.page_url,
                        anchor_text=c.anchor_text,
                        pattern_type=c.pattern_type,
                        score=c.score,
                        reason="candidate_school_mismatch",
                        pdf_type="non_target",
                    ), persist=evidence_index < MAX_BULK_REJECTION_EVIDENCE_PER_SCHOOL)
            viable, candidate_budget_dropped_candidates = _prioritize_viable_candidates(
                viable,
                target_year=target_year,
                school_name=school_name,
            )
            if candidate_budget_dropped_candidates:
                stats["candidate_budget_limited"] += 1
                stats["candidate_budget_dropped"] += len(candidate_budget_dropped_candidates)
                for evidence_index, c in enumerate(candidate_budget_dropped_candidates):
                    record_discovery_evidence(RejectionEvidence(
                        school_id=site.school_id,
                        pdf_url=c.pdf_url,
                        page_url=c.page_url,
                        anchor_text=c.anchor_text,
                        pattern_type=c.pattern_type,
                        score=c.score,
                        reason="candidate_budget_dropped",
                        extra={
                            "candidate_budget": f"max_general_candidate_scan={MAX_GENERAL_CANDIDATE_SCAN}",
                        },
                    ), persist=evidence_index < MAX_BULK_REJECTION_EVIDENCE_PER_SCHOOL)
            if not viable and school_mismatch_candidates:
                job.status = "review"
                job.error_message = "all viable candidates name a different school"
                job.finished_at = datetime.now(UTC)
                stats["skipped"] += 1
                if progress_callback is not None:
                    progress_callback(dict(stats), len(sites))
                time.sleep(rate_limit)
                continue

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
            download_attempts = 0
            for candidate in viable:
                if strict_target_fiscal_year and not candidate.trusted_year_evidence:
                    candidate.trusted_year_evidence = _trusted_year_evidence_for_site(site)
                cache_key = _rejection_cache_key(
                    site.school_id,
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
                    if cached_rejection.pdf_type == "non_target":
                        stats["cached_rejection_evidence_suppressed"] += 1
                        _increment_rejection_reason(stats, cached_rejection.reason)
                    else:
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

                if download_attempts >= MAX_CANDIDATE_DOWNLOAD_ATTEMPTS:
                    break
                download_attempts += 1

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
                    if _candidate_pdf_mentions_different_school(candidate, school_names):
                        Path(file_path).unlink(missing_ok=True)
                        stats["skipped"] += 1
                        record_discovery_evidence(RejectionEvidence(
                            school_id=site.school_id,
                            pdf_url=candidate.pdf_url,
                            page_url=candidate.page_url,
                            anchor_text=candidate.anchor_text,
                            pattern_type=candidate.pattern_type,
                            score=candidate.score,
                            reason="pdf_school_mismatch",
                            pdf_type=pdf_type,
                            extra={
                                "parsed_school_name": candidate.detected_school_name,
                                "target_school_name": school_name,
                            },
                        ))
                        time.sleep(0.5)
                        continue

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
                        _remove_duplicate_candidate_file(file_path, existing)
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
                            fiscal_year=(
                                target_year
                                if strict_target_fiscal_year
                                else candidate.detected_fiscal_year
                            ),
                            is_current_year=(
                                True
                                if strict_target_fiscal_year
                                else (
                                    candidate.detected_fiscal_year >= target_year
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
                            _remove_duplicate_candidate_file(file_path, existing)
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
    return stats
