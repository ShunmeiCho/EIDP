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
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx
import structlog
from sqlalchemy.orm import Session

from eidp.db.models import CrawlJob, Document, SchoolSite
from eidp.scraper.url_discovery import _is_safe_url

log = structlog.get_logger()


def _safe_get(client: httpx.Client, url: str, **kwargs) -> httpx.Response:
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
]

# User-Agent mimicking a real browser (institutional research)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) EIDP-DataCollector/1.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ja,en;q=0.5",
}


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


def _score_candidate(candidate: PdfCandidate) -> float:
    """Score a PDF candidate by keyword relevance."""
    score = 0.0
    text = (candidate.anchor_text + " " + candidate.pdf_url).lower()

    for kw in POSITIVE_KEYWORDS:
        if kw.lower() in text:
            score += 2.0

    for kw in NEGATIVE_KEYWORDS:
        if kw.lower() in text:
            score -= 3.0

    # Bonus for current year references
    if "令和8" in text or "令和08" in text or "2026" in text or "r8" in text:
        score += 3.0
    if "令和7" in text or "2025" in text or "r7" in text:
        score += 1.0

    # Bonus for pattern type reliability
    if candidate.pattern_type == "direct":
        score += 0.5
    elif candidate.pattern_type == "embed":
        score += 0.3

    candidate.score = score
    return score


def _extract_pdf_links(html: str, base_url: str) -> list[PdfCandidate]:
    """Extract PDF link candidates from HTML using 4 patterns."""
    candidates: list[PdfCandidate] = []
    seen_urls: set[str] = set()

    # Pattern 1: Direct PDF links — a[href*=".pdf"]
    for m in re.finditer(
        r'<a\s[^>]*href=["\']([^"\']*\.pdf(?:\?[^"\']*)?)["\'][^>]*>(.*?)</a>',
        html, re.IGNORECASE | re.DOTALL,
    ):
        url = urljoin(base_url, m.group(1))
        if url not in seen_urls:
            seen_urls.add(url)
            anchor = re.sub(r"<[^>]+>", "", m.group(2)).strip()
            pattern = "cache_busted" if "?" in m.group(1) else "direct"
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
                url = urljoin(base_url, m.group(1))
                if url not in seen_urls:
                    seen_urls.add(url)
                    candidates.append(PdfCandidate(
                        pdf_url=url, page_url=base_url, anchor_text="", pattern_type="embed",
                    ))

    return candidates


def _find_subpage_links(html: str, base_url: str) -> list[str]:
    """Find disclosure subpage links to follow (two-tier pattern)."""
    subpages: list[str] = []
    keywords = ["情報公開", "公開情報", "修学支援", "高等教育", "無償化", "確認申請"]

    for m in re.finditer(
        r'<a\s[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
        html, re.IGNORECASE | re.DOTALL,
    ):
        href = m.group(1)
        text = re.sub(r"<[^>]+>", "", m.group(2)).strip()

        if any(kw in text for kw in keywords) and not href.endswith(".pdf"):
            url = urljoin(base_url, href)
            parsed = urlparse(url)
            base_parsed = urlparse(base_url)
            # Only follow links on the same domain
            if parsed.netloc == base_parsed.netloc or not parsed.netloc:
                subpages.append(url)

    return subpages[:5]  # Limit to 5 subpages


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
                        candidates.extend(sub_candidates)
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
        import pdfplumber
        import io
        import unicodedata
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            sample_text = ""
            # Scan up to 5 pages (some formats put markers on later pages)
            for page in pdf.pages[:5]:
                sample_text += (page.extract_text() or "") + "\n"

        if not sample_text.strip() or "(cid:" in sample_text:
            return "image_only"

        # NFKC normalize to handle full-width digits (２→2, etc.)
        normed = unicodedata.normalize("NFKC", sample_text)

        # Check for target document markers
        target_markers = ["様式第2号", "機関要件", "修学支援", "生徒総定員", "学科名"]
        hits = sum(1 for m in target_markers if m in normed)
        if hits >= 2:
            return "target"

        return "non_target"
    except Exception as e:
        log.warning("pdf_classify_failed", error=str(e), error_type=type(e).__name__)
        return "unknown"


def download_pdf(
    client: httpx.Client,
    candidate: PdfCandidate,
    storage_dir: Path,
    school_id: int,
) -> tuple[str | None, str | None, int, str]:
    """Download PDF and return (file_path, sha256_hash, file_size, pdf_type).

    Max download size: 50MB. Larger files are skipped.
    """
    MAX_PDF_SIZE = 50 * 1024 * 1024  # 50 MB

    if not _is_safe_url(candidate.pdf_url):
        return None, None, 0, "unknown"
    try:
        resp = _safe_get(client, candidate.pdf_url)
        resp.raise_for_status()

        # Check Content-Length before reading body
        content_length = resp.headers.get("content-length")
        if content_length and int(content_length) > MAX_PDF_SIZE:
            log.warning("pdf_too_large", url=candidate.pdf_url, size=content_length)
            return None, None, 0, "unknown"

        content = resp.content
        if len(content) > MAX_PDF_SIZE:
            log.warning("pdf_too_large_actual", url=candidate.pdf_url, size=len(content))
            return None, None, 0, "unknown"
        if len(content) < 1000:  # Too small to be a real PDF
            return None, None, 0, "unknown"

        # Verify it's actually a PDF
        if not content[:5] == b"%PDF-":
            return None, None, 0, "unknown"

        file_hash = hashlib.sha256(content).hexdigest()
        file_size = len(content)

        # Quick content validation: check if extractable text contains target keywords
        pdf_type = _classify_pdf_content(content)

        # Storage path: data/pdfs/{school_id}/{hash[:8]}.pdf
        school_dir = storage_dir / str(school_id)
        school_dir.mkdir(parents=True, exist_ok=True)
        file_path = school_dir / f"{file_hash[:8]}.pdf"
        file_path.write_bytes(content)

        # Clean up non-target files to prevent orphaned disk usage
        if pdf_type == "non_target":
            file_path.unlink(missing_ok=True)
            log.info("non_target_pdf_removed", url=candidate.pdf_url, path=str(file_path))
            return None, None, 0, "non_target"

        return str(file_path), file_hash, file_size, pdf_type

    except httpx.HTTPError:
        return None, None, 0, "unknown"


def run_pdf_discovery(
    session: Session,
    storage_dir: Path,
    batch_size: int = 50,
    rate_limit: float = 1.0,
    discovery_methods: list[str] | None = None,
    school_ids: list[int] | None = None,
) -> dict[str, int]:
    """Run PDF discovery for schools with verified URLs but no documents.

    Args:
        discovery_methods: optional list of school_site.discovery_method values
            to restrict which URLs are crawled. E.g. ["prefecture_aggregator"]
            to crawl ONLY the trusted pref aggregator URLs (per Codex P0-6b:
            isolate polluted web_search URLs from pdf_discovery).
        school_ids: optional list of school.id to restrict discovery to a
            specific set (used for targeted gap-filling, e.g. 滋慶 group).
    """
    stats = {"crawled": 0, "found": 0, "downloaded": 0, "failed": 0, "skipped": 0}

    # Get school_sites, excluding:
    # - schools with a document for the current target fiscal year
    # - schools excluded in their LATEST fiscal year only (not historical exclusions)
    from sqlalchemy import and_, func, or_
    from eidp.db.models import SchoolYearStatus

    # Only exclude schools where the most recent year is excluded
    latest_year_subq = (
        session.query(
            SchoolYearStatus.school_id,
            func.max(SchoolYearStatus.fiscal_year).label("max_fy"),
        )
        .group_by(SchoolYearStatus.school_id)
        .subquery()
    )
    excluded_school_ids = (
        session.query(SchoolYearStatus.school_id)
        .join(
            latest_year_subq,
            and_(
                SchoolYearStatus.school_id == latest_year_subq.c.school_id,
                SchoolYearStatus.fiscal_year == latest_year_subq.c.max_fy,
            ),
        )
        .filter(SchoolYearStatus.excluded_reason.isnot(None))
    )

    # Only skip schools that already have a document for the current target year
    # (allow re-discovery if previous docs were from a different year or failed)
    # Japanese fiscal year runs April-March: in Jan-Mar, target FY is previous calendar year
    now = datetime.now()
    current_target_year = now.year if now.month >= 4 else now.year - 1
    # Only skip schools that have a FULLY ingested current-year document
    # support_only and partial docs should NOT suppress rediscovery
    schools_with_current_docs = (
        session.query(Document.school_id)
        .filter(
            Document.fiscal_year == current_target_year,
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

    with httpx.Client(
        timeout=30.0,
        follow_redirects=False,
        headers=HEADERS,
    ) as client:
        for site in sites:
            # Create crawl job
            job = CrawlJob(
                school_id=site.school_id,
                job_type="pdf_search",
                status="running",
                started_at=datetime.now(timezone.utc),
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
                job.finished_at = datetime.now(timezone.utc)
                stats["failed"] += 1
                time.sleep(rate_limit)
                continue

            if not result.best:
                job.status = "success"
                job.finished_at = datetime.now(timezone.utc)
                stats["skipped"] += 1
                time.sleep(rate_limit)
                continue

            stats["found"] += 1

            # Filter out negative-score candidates
            viable = [c for c in result.candidates if c.score >= 0]
            if not viable:
                job.status = "review"
                job.error_message = "all candidates have negative score"
                job.finished_at = datetime.now(timezone.utc)
                stats["failed"] += 1
                time.sleep(rate_limit)
                continue

            # Try downloading top candidates (fallback on 404)
            downloaded = False
            for candidate in viable[:3]:
                file_path, file_hash, file_size, pdf_type = download_pdf(
                    client, candidate, storage_dir, site.school_id,
                )
                # non_target PDFs already cleaned up in download_pdf(), skip them
                if pdf_type == "non_target":
                    log.info("non_target_pdf_skipped", school_id=site.school_id, url=candidate.pdf_url)
                    stats["skipped"] += 1
                    continue

                if file_path:
                    # Check for duplicate hash
                    existing = (
                        session.query(Document)
                        .filter(Document.school_id == site.school_id, Document.file_hash == file_hash)
                        .first()
                    )
                    if existing:
                        stats["skipped"] += 1
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
                            downloaded_at=datetime.now(timezone.utc),
                        )
                        session.add(doc)
                        stats["downloaded"] += 1

                    job.status = "success"
                    job.finished_at = datetime.now(timezone.utc)
                    downloaded = True
                    break

                time.sleep(0.5)

            if not downloaded:
                job.status = "failed"
                job.error_message = f"download failed for {len(result.candidates)} candidates"
                job.finished_at = datetime.now(timezone.utc)
                stats["failed"] += 1

            session.flush()
            time.sleep(rate_limit)

    log.info("pdf_discovery_complete", **stats)
    return stats
