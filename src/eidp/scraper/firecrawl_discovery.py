"""Firecrawl-based PDF discovery for corporation root URLs.

Uses Firecrawl MCP's map endpoint to discover school-specific
disclosure pages and PDF URLs from corporation root domains.

This replaces the traditional httpx + regex approach for corp roots,
where the old approach can't navigate multi-level sites effectively.
"""

import os
import re
import unicodedata
from dataclasses import dataclass

import httpx
import structlog
from sqlalchemy.orm import Session

from eidp.db.models import School, SchoolSite
from eidp.scraper.url_discovery import _is_safe_url

log = structlog.get_logger()

FIRECRAWL_API_URL = "https://api.firecrawl.dev/v1"


def _norm(s: str) -> str:
    if not s:
        return ""
    return unicodedata.normalize("NFKC", re.sub(r"\s+", "", s))


@dataclass
class DiscoveredPdf:
    school_id: int
    school_name: str
    pdf_url: str
    page_title: str
    confidence: float


def _firecrawl_map(
    base_url: str,
    search: str,
    limit: int = 50,
    api_key: str = "",
) -> list[dict]:
    """Call Firecrawl map API to discover URLs on a site."""
    if not api_key:
        from eidp.config import settings
        api_key = settings.firecrawl_api_key or os.environ.get("FIRECRAWL_API_KEY", "")
    if not api_key:
        log.warning("firecrawl_api_key_missing", hint="Set EIDP_FIRECRAWL_API_KEY in .env")
        return []

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "url": base_url,
        "search": search,
        "limit": limit,
    }

    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                f"{FIRECRAWL_API_URL}/map",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            # API returns list of URL strings
            links = data.get("links", [])
            return [url if isinstance(url, str) else url.get("url", "") for url in links]
    except httpx.HTTPStatusError as e:
        log.warning("firecrawl_map_http_error", url=base_url, status=e.response.status_code, error=str(e))
        return []
    except Exception as e:
        log.warning("firecrawl_map_error", url=base_url, error=str(e), error_type=type(e).__name__)
        return []


def discover_pdfs_for_corporation(
    session: Session,
    corp_domain: str,
    schools: list[School],
) -> dict[str, int]:
    """Discover PDF URLs for all schools under a corporation domain.

    Uses Firecrawl map to find 確認申請書 PDFs, then matches each PDF
    to a specific school by school_name substring matching.
    """
    stats = {"searched": 0, "matched": 0, "unmatched": 0, "errors": 0}

    # Validate corp domain before sending to Firecrawl API
    if not _is_safe_url(corp_domain):
        log.warning("ssrf_blocked_corp_domain", domain=corp_domain)
        stats["errors"] += 1
        return stats

    # Search for disclosure PDFs on the corporation site
    pdf_urls = _firecrawl_map(
        corp_domain,
        search="確認申請書 様式第2号 機関要件 情報公開",
        limit=200,
    )
    stats["searched"] = 1

    if not pdf_urls:
        pdf_urls = _firecrawl_map(
            corp_domain,
            search="情報公開 高等教育 修学支援",
            limit=200,
        )

    # Split into PDF URLs and page URLs, filtering unsafe URLs
    # Handle .pdf?query and .PDF uppercase variants
    def _is_pdf_url(url: str) -> bool:
        from urllib.parse import urlparse
        path = urlparse(url).path.lower()
        return path.endswith(".pdf")

    pdf_links = [u for u in pdf_urls if u and _is_pdf_url(u) and _is_safe_url(u)]
    page_links = [u for u in pdf_urls if u and not _is_pdf_url(u) and _is_safe_url(u)]

    log.info("firecrawl_corp_results",
             domain=corp_domain,
             total=len(pdf_urls),
             pdfs=len(pdf_links),
             pages=len(page_links))

    # For each school, try to find a matching PDF or disclosure page
    for school in schools:
        school_norm = _norm(school.school_name)
        # Also try shorter name variants for matching
        # e.g., "大原簿記情報専門学校札幌校" → try "札幌校", "札幌"
        short_names = [school_norm]
        if len(school.school_name) > 6:
            # Extract location suffix (last 2-4 chars before 校)
            m = re.search(r"(.{2,6}校)$", school.school_name)
            if m:
                short_names.append(_norm(m.group(1)))

        matched = False

        # First: match PDF URLs by school name in URL path
        # Store as SchoolSite (not Document) because the PDF isn't downloaded yet.
        # pdf_discovery will later find these URLs and create proper Documents.
        for pdf_url in pdf_links:
            url_norm = _norm(pdf_url)
            if any(sn in url_norm for sn in short_names if len(sn) >= 4):
                existing = session.query(SchoolSite).filter(
                    SchoolSite.school_id == school.id, SchoolSite.url == pdf_url
                ).first()
                if not existing:
                    site = SchoolSite(
                        school_id=school.id,
                        url=pdf_url,
                        url_type="school",
                        discovery_method="firecrawl_map",
                        confidence=0.9,
                    )
                    session.add(site)
                matched = True
                stats["matched"] += 1
                break

        # Second: match disclosure pages by school name in URL
        if not matched:
            for page_url in page_links:
                url_norm = _norm(page_url)
                if any(sn in url_norm for sn in short_names if len(sn) >= 4):
                    existing = session.query(SchoolSite).filter(
                        SchoolSite.school_id == school.id, SchoolSite.url == page_url
                    ).first()
                    if not existing:
                        site = SchoolSite(
                            school_id=school.id,
                            url=page_url,
                            url_type="school",
                            discovery_method="firecrawl_map",
                            confidence=0.85,
                        )
                        session.add(site)
                    matched = True
                    stats["matched"] += 1
                    break

        # Third: if corp has a standard joho/pdf/ directory, save all PDFs
        # and let ingest's school-identity check handle matching
        if not matched and pdf_links:
            # Store the disclosure page directory as school URL
            # The PDFs will be matched during ingest via school_name verification
            joho_dirs = set()
            for pdf_url in pdf_links:
                dir_url = pdf_url.rsplit("/", 1)[0] + "/"
                joho_dirs.add(dir_url)

            if joho_dirs:
                best_dir = sorted(joho_dirs, key=len)[0]  # Shortest path = most general
                existing = session.query(SchoolSite).filter(
                    SchoolSite.school_id == school.id,
                    SchoolSite.url_type == "school",
                    SchoolSite.discovery_method == "firecrawl_map",
                ).first()
                if not existing:
                    site = SchoolSite(
                        school_id=school.id,
                        url=best_dir,
                        url_type="school",
                        discovery_method="firecrawl_map",
                        confidence=0.6,
                    )
                    session.add(site)
                stats["matched"] += 1
                matched = True

        if not matched:
            stats["unmatched"] += 1

    session.flush()
    log.info("firecrawl_corp_complete", domain=corp_domain, **stats)
    return stats


def run_firecrawl_discovery(
    session: Session,
    batch_size: int = 10,
) -> dict[str, int]:
    """Run Firecrawl-based discovery for all corporation root URLs.

    Groups schools by corporation domain, then uses firecrawl_map
    to find school-specific PDFs for each group.
    """
    from eidp.scraper.url_discovery import _load_corporation_domains

    total_stats = {"corps_processed": 0, "schools_matched": 0, "schools_unmatched": 0}

    corp_domains = _load_corporation_domains()

    for corp_name, domain in list(corp_domains.items())[:batch_size]:
        # Get all schools under this corporation
        schools = (
            session.query(School)
            .filter(School.corporation_name == corp_name, School.status == "active")
            .all()
        )

        if not schools:
            continue

        log.info("firecrawl_corp_start", corp=corp_name, domain=domain, schools=len(schools))

        stats = discover_pdfs_for_corporation(session, domain, schools)
        session.commit()

        total_stats["corps_processed"] += 1
        total_stats["schools_matched"] += stats["matched"]
        total_stats["schools_unmatched"] += stats["unmatched"]

    log.info("firecrawl_discovery_complete", **total_stats)
    return total_stats
