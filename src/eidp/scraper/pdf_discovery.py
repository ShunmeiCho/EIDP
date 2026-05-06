"""PDF discovery + download — Step 8.

Crawls school disclosure pages, finds target PDF links using 4 patterns,
scores candidates, downloads best match, stores in document table.

4 delivery patterns (verified from reference sites):
1. Direct PDF links: a[href$=".pdf"]
2. WordPress asset: a[href*="/wp-content/"] + .pdf
3. Cache-busted: a[href*=".pdf?"]
4. Two-tier embed: subpage -> embed[src*=".pdf"]
"""

import hashlib
import html as html_lib
import re
import time
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, unquote, urljoin, urlparse

import httpx
import structlog
from sqlalchemy.orm import Session

from eidp.config import settings
from eidp.db.models import CrawlJob, Document, SchoolSite
from eidp.fiscal_year import fiscal_year_from_japanese_era_text, fiscal_year_search_tokens
from eidp.scraper.discovery_evidence import EvidenceRecorder, RejectionEvidence
from eidp.scraper.url_discovery import _is_safe_url

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
    "attachment", "appendix", "添付資料",
]

# User-Agent mimicking a real browser (institutional research)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) EIDP-DataCollector/1.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ja,en;q=0.5",
}

MAX_CANDIDATE_DOWNLOAD_ATTEMPTS = 10
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
    "kikanyouken",
    "valuation",
    "情報公開",
    "公開情報",
    "修学支援",
    "高等教育",
    "無償化",
    "機関要件",
)


@dataclass
class PdfCandidate:
    pdf_url: str
    page_url: str
    anchor_text: str = ""
    pattern_type: str = ""  # direct, wordpress, cache_busted, embed
    score: float = 0.0


@dataclass
class DiscoveryResult:
    school_id: int
    candidates: list[PdfCandidate] = field(default_factory=list)
    best: PdfCandidate | None = None
    downloaded_path: str | None = None
    file_hash: str | None = None
    file_size: int = 0
    error: str | None = None


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


def _detect_fiscal_year_from_text(text: str, *, max_fiscal_year: int | None = None) -> int | None:
    """Best-effort fiscal-year detector for disclosure PDFs."""
    normed = unicodedata.normalize("NFKC", text)

    # Prefer explicit fiscal-year labels over filing dates.
    fiscal_year = fiscal_year_from_japanese_era_text(
        normed,
        include_fiscal_year_labels=True,
        include_filing_dates=False,
    )
    if fiscal_year is not None:
        return fiscal_year

    m = re.search(r"(20\d{2})\s*年度", normed)
    if m:
        return int(m.group(1))

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
    target_markers = ["様式第2号", "機関要件", "修学支援", "生徒総定員", "学科名"]
    hits = sum(1 for m in target_markers if m in normed)
    if hits >= 2:
        return "target"

    if "(cid:" in sample_text:
        return "image_only"
    return "non_target"


def _extract_pdf_links(html: str, base_url: str) -> list[PdfCandidate]:
    """Extract PDF link candidates from HTML using 4 patterns."""
    candidates: list[PdfCandidate] = []
    seen_urls: set[str] = set()

    # Pattern 1: Direct PDF links — a[href*=".pdf"]
    for m in re.finditer(
        r'<a\s[^>]*href=["\']([^"\']*\.pdf(?:\?[^"\']*)?)["\'][^>]*>(.*?)</a>',
        html, re.IGNORECASE | re.DOTALL,
    ):
        href = html_lib.unescape(m.group(1))
        url = urljoin(base_url, href)
        if url not in seen_urls:
            seen_urls.add(url)
            anchor = html_lib.unescape(re.sub(r"<[^>]+>", "", m.group(2))).strip()
            pattern = "cache_busted" if "?" in href else "direct"
            if "/wp-content/" in url:
                pattern = "wordpress"
            candidates.append(PdfCandidate(
                pdf_url=url, page_url=base_url, anchor_text=anchor, pattern_type=pattern,
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
                if url not in seen_urls:
                    seen_urls.add(url)
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


def _find_subpage_links(html: str, base_url: str) -> list[str]:
    """Find disclosure subpage links to follow (two-tier pattern)."""
    subpages: list[str] = []
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
        "機関要件",
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

        if any(kw.lower() in haystack for kw in keywords) and not href.lower().endswith(".pdf"):
            url = urljoin(base_url, href)
            parsed = urlparse(url)
            base_parsed = urlparse(base_url)
            # Only follow links on the same domain
            if (parsed.netloc == base_parsed.netloc or not parsed.netloc) and url not in seen:
                seen.add(url)
                subpages.append(url)

    return subpages[:12]  # Keep bounded while covering dense institutional navs.


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
    seen = {candidate.pdf_url for candidate in target}
    for candidate in additions:
        if candidate.pdf_url in seen:
            continue
        seen.add(candidate.pdf_url)
        target.append(candidate)


def discover_pdfs_for_site(
    client: httpx.Client,
    school_id: int,
    site_url: str,
    max_depth: int = 2,
) -> DiscoveryResult:
    """Discover PDF candidates from a school site URL."""
    result = DiscoveryResult(school_id=school_id)

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
        resp = _safe_get(client, site_url)
        resp.raise_for_status()
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
        if max_depth > 0:
            subpages = _find_subpage_links(html, site_url)
            for sub_url in subpages:
                if not _is_safe_url(sub_url):
                    continue
                try:
                    time.sleep(1.0)  # Per-request delay
                    sub_resp = _safe_get(client, sub_url)
                    if sub_resp.status_code == 200:
                        sub_candidates = _extract_pdf_links(sub_resp.text, sub_url)
                        _append_unique_candidates(candidates, sub_candidates)
                except httpx.HTTPError:
                    continue

        # Sitemap discovery is not just a last resort. Many school homepages
        # expose stale PDFs on the visible page while the current disclosure page
        # is only reachable through sitemap.xml / robots Sitemap entries.
        for sitemap_url in _sitemap_urls_for_site(client, site_url):
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
            try:
                time.sleep(1.0)
                sitemap_resp = _safe_get(client, sitemap_url)
                if sitemap_resp.status_code == 200:
                    _append_unique_candidates(candidates, _extract_pdf_links(sitemap_resp.text, sitemap_url))
            except httpx.HTTPError:
                continue

        # Score all candidates
        for c in candidates:
            _score_candidate(c)

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
            resp = _safe_get(client, download_url)
            resp.raise_for_status()

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
        except Exception as e:
            log.warning("pdf_classify_failed", error=str(e), error_type=type(e).__name__)
            pdf_type = "unknown"

        if strict_target_fiscal_year:
            target_year = target_fiscal_year or settings.target_fiscal_year
            if detected_fiscal_year is not None and detected_fiscal_year != target_year:
                return None, None, 0, pdf_type, f"fiscal_year_mismatch:{detected_fiscal_year}"
            if detected_fiscal_year is None:
                return None, None, 0, pdf_type, "target_fiscal_year_not_detected"

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
            PDF text confirms ``target_fiscal_year``. URL/anchor text ranks
            candidates but is not evidence strong enough to store a document.
        progress_callback: optional callback invoked after each crawled school
            site with a snapshot of stats and the total site count. Used by the
            Windows operator UI so the long-running crawl does not sit at one
            frozen percentage.
    """
    stats = {"crawled": 0, "found": 0, "downloaded": 0, "failed": 0, "skipped": 0}
    recorder = EvidenceRecorder(evidence_path)
    target_year = target_fiscal_year or settings.target_fiscal_year

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
                result = discover_pdfs_for_site(client, site.school_id, site.url)
            stats["crawled"] += 1

            if result.error:
                job.status = "failed"
                job.error_message = result.error
                job.finished_at = datetime.now(UTC)
                stats["failed"] += 1
                recorder.record(RejectionEvidence(
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
                recorder.record(RejectionEvidence(
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
                    recorder.record(RejectionEvidence(
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
                    recorder.record(RejectionEvidence(
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
                        reject_reason == "target_fiscal_year_not_detected"
                        or reject_reason.startswith("fiscal_year_mismatch:")
                    ):
                        target_year_rejection_seen = True
                    recorder.record(RejectionEvidence(
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
                        recorder.record(RejectionEvidence(
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
                            content_type=content_type,
                            pdf_type=pdf_type,
                            confidence=min(candidate.score / 10.0, 0.99),
                            downloaded_at=datetime.now(UTC),
                        )
                        session.add(doc)
                        stats["downloaded"] += 1
                        recorder.record(RejectionEvidence(
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
