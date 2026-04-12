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

log = structlog.get_logger()

# Keywords that indicate the target document (高等教育修学支援新制度 確認申請書)
POSITIVE_KEYWORDS = [
    "修学支援", "高等教育", "無償化", "確認申請", "機関要件",
    "様式第2号", "様式2", "学校教育法", "情報公開",
]

NEGATIVE_KEYWORDS = [
    "シラバス", "syllabus", "募集要項", "パンフレット",
    "入学案内", "カリキュラム", "時間割",
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

        # Fetch main page
        resp = client.get(site_url)
        resp.raise_for_status()
        html = resp.text

        # Short/truncated HTML retry (TCA pattern)
        if len(html) < 500 and resp.status_code == 200:
            time.sleep(1.0)
            resp = client.get(site_url)
            html = resp.text

        # Extract PDF candidates from main page
        candidates = _extract_pdf_links(html, site_url)

        # If no PDFs found, try subpage links (two-tier pattern)
        if not candidates and max_depth > 0:
            subpages = _find_subpage_links(html, site_url)
            for sub_url in subpages:
                try:
                    time.sleep(1.0)  # Per-request delay
                    sub_resp = client.get(sub_url)
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


def download_pdf(
    client: httpx.Client,
    candidate: PdfCandidate,
    storage_dir: Path,
    school_id: int,
) -> tuple[str | None, str | None, int]:
    """Download PDF and return (file_path, sha256_hash, file_size)."""
    try:
        resp = client.get(candidate.pdf_url)
        resp.raise_for_status()

        content = resp.content
        if len(content) < 1000:  # Too small to be a real PDF
            return None, None, 0

        # Verify it's actually a PDF
        if not content[:5] == b"%PDF-":
            return None, None, 0

        file_hash = hashlib.sha256(content).hexdigest()
        file_size = len(content)

        # Storage path: data/pdfs/{school_id}/{hash[:8]}.pdf
        school_dir = storage_dir / str(school_id)
        school_dir.mkdir(parents=True, exist_ok=True)
        file_path = school_dir / f"{file_hash[:8]}.pdf"
        file_path.write_bytes(content)

        return str(file_path), file_hash, file_size

    except httpx.HTTPError:
        return None, None, 0


def run_pdf_discovery(
    session: Session,
    storage_dir: Path,
    batch_size: int = 50,
    rate_limit: float = 1.0,
) -> dict[str, int]:
    """Run PDF discovery for schools with verified URLs but no documents."""
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
    current_target_year = datetime.now().year  # approximate fiscal year
    schools_with_current_docs = (
        session.query(Document.school_id)
        .filter(Document.fiscal_year == current_target_year)
        .distinct()
    )

    sites = (
        session.query(SchoolSite)
        .filter(
            or_(SchoolSite.http_status == 200, SchoolSite.http_status.is_(None)),
            ~SchoolSite.school_id.in_(schools_with_current_docs),
            ~SchoolSite.school_id.in_(excluded_school_ids),
        )
        .order_by(SchoolSite.confidence.desc())
        .limit(batch_size)
        .all()
    )

    log.info("pdf_discovery_start", sites=len(sites))

    with httpx.Client(
        timeout=30.0,
        follow_redirects=True,
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
                file_path, file_hash, file_size = download_pdf(
                    client, candidate, storage_dir, site.school_id,
                )
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
                        doc = Document(
                            school_id=site.school_id,
                            source_url=candidate.pdf_url,
                            discovered_from=candidate.page_url,
                            file_path=file_path,
                            file_hash=file_hash,
                            file_size=file_size,
                            content_type="text",  # assumed; OCR fallback updates later
                            pdf_type="機関要件確認申請書" if candidate.score >= 2.0 else None,
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
