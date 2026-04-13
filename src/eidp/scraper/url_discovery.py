"""URL discovery module — Step 7.

Discovers disclosure page URLs for each school via:
1. Seed import from existing discovered-urls CSV
2. Corporation-based pattern inference (大原, 三幸, etc.)
3. HTTP verification of candidate URLs

Stores results in school_site table.
"""

import csv
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import httpx
import structlog
from sqlalchemy import func
from sqlalchemy.orm import Session

from eidp.db.models import School, SchoolSite

log = structlog.get_logger()

# SSRF prevention: only allow http(s) to public hosts
_BLOCKED_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "::1", "169.254.169.254", "metadata.google.internal"}


def _is_safe_url(url: str) -> bool:
    """Validate URL is http(s) and not targeting internal/cloud metadata endpoints.

    Performs DNS resolution to block rebinding-style hostnames (e.g.
    169.254.169.254.nip.io) that resolve to private/metadata IPs.
    """
    from urllib.parse import urlparse
    import ipaddress
    import socket

    try:
        parsed = urlparse(url)
    except Exception:
        return False
    if parsed.scheme not in ("http", "https"):
        return False
    hostname = (parsed.hostname or "").lower()
    if not hostname:
        return False
    if hostname in _BLOCKED_HOSTS:
        return False

    # Check if hostname is a literal IP
    try:
        ip = ipaddress.ip_address(hostname)
        if ip.is_private or ip.is_loopback or ip.is_link_local:
            return False
    except ValueError:
        # hostname is not an IP, resolve DNS to check actual IP
        try:
            resolved = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
            for _, _, _, _, sockaddr in resolved:
                addr = sockaddr[0]
                ip = ipaddress.ip_address(addr)
                if ip.is_private or ip.is_loopback or ip.is_link_local:
                    return False
        except (socket.gaierror, OSError):
            # DNS resolution failed, reject the URL
            return False

    return True

def _load_corporation_domains() -> dict[str, str]:
    """Load corporation -> domain mapping from external CSV.

    CSV path: data/url-discovery/corporation_domains.csv
    Columns: corporation_name, domain_url, notes
    """
    from eidp.config import settings

    csv_path = settings.data_dir / "url-discovery" / "corporation_domains.csv"
    domains: dict[str, str] = {}

    if not csv_path.exists():
        log.warning("corporation_domains_csv_not_found", path=str(csv_path))
        return domains

    with open(csv_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            corp = row.get("corporation_name", "").strip()
            url = row.get("domain_url", "").strip()
            if corp and url:
                domains[corp] = url

    log.info("corporation_domains_loaded", count=len(domains), path=str(csv_path))
    return domains

# Common disclosure page path patterns
DISCLOSURE_PATHS = [
    "/about/valuation/",
    "/school-outline/disclose/",
    "/school/public_info/",
    "/disclosure/",
    "/info/",
    "/joho/",
    "/about/disclosure/",
    "/about/info/",
    "/about/public/",
]


@dataclass
class DiscoveredUrl:
    school_id: int
    url: str
    url_type: str  # school, corporation_subpage, government
    discovery_method: str  # seed_csv, corporation_pattern, web_search
    confidence: float
    http_status: int | None = None


def import_seed_urls(
    session: Session,
    csv_path: Path,
) -> dict[str, int]:
    """Import pre-discovered URLs from the 50-school CSV into school_site."""
    stats = {"imported": 0, "skipped_no_school": 0, "skipped_existing": 0}

    with open(csv_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            prefecture = row.get("prefecture", "").strip()
            corp_name = row.get("corporation", "").strip()
            school_name = row.get("school_name", "").strip()

            if not school_name:
                continue

            school = (
                session.query(School)
                .filter(
                    School.prefecture == prefecture,
                    School.corporation_name == corp_name,
                    School.school_name == school_name,
                )
                .first()
            )
            if school is None:
                stats["skipped_no_school"] += 1
                continue

            url = row.get("url_candidate_1", "").strip()
            if not url or not _is_safe_url(url):
                continue

            # Check if already exists
            existing = (
                session.query(SchoolSite)
                .filter(SchoolSite.school_id == school.id, SchoolSite.url == url)
                .first()
            )
            if existing:
                stats["skipped_existing"] += 1
                continue

            confidence = float(row.get("confidence", 0.5))
            url_type = row.get("url_type", "school").strip()

            site = SchoolSite(
                school_id=school.id,
                url=url,
                url_type=url_type,
                discovery_method="seed_csv",
                confidence=confidence,
                http_status=int(row["http_status"]) if row.get("http_status") else None,
            )
            session.add(site)
            stats["imported"] += 1

    session.flush()
    log.info("seed_urls_imported", **stats)
    return stats


def infer_corporation_urls(session: Session) -> dict[str, int]:
    """Register corporation domain roots for schools in known groups.

    Reads corporation->domain mapping from data/url-discovery/corporation_domains.csv.
    These are NOT exact page URLs. They are corporation-level entry points
    that Step 8 (PDF discovery) will crawl to find disclosure pages.
    """
    stats = {"inferred": 0, "skipped_has_url": 0}

    corporation_domains = _load_corporation_domains()
    for corp_name, domain in corporation_domains.items():
        schools = (
            session.query(School)
            .filter(School.corporation_name == corp_name)
            .all()
        )

        for school in schools:
            existing = session.query(SchoolSite).filter(SchoolSite.school_id == school.id).first()
            if existing:
                stats["skipped_has_url"] += 1
                continue

            site = SchoolSite(
                school_id=school.id,
                url=domain,
                url_type="corporation",
                discovery_method="corporation_pattern",
                confidence=0.5,  # Low: domain root, not exact disclosure page
            )
            session.add(site)
            stats["inferred"] += 1

    session.flush()
    log.info("corporation_urls_inferred", **stats)
    return stats


def search_and_discover(
    session: Session,
    batch_size: int = 100,
    rate_limit_delay: float = 1.0,
) -> dict[str, int]:
    """Use search API to discover URLs for schools without any URL.

    Uses cascading query strategy:
    1. "{school_name} 情報公開 高等教育無償化" (most specific)
    2. "{school_name} 情報公開" (broader)
    3. "{school_name} 専門学校" (find school homepage)
    """
    import time

    from eidp.config import settings
    from eidp.scraper.search_provider import create_provider

    api_key_map = {
        "brave": settings.brave_api_key,
        "google": settings.google_api_key,
        "serper": settings.serper_api_key,
        "duckduckgo": "",
    }
    provider = create_provider(
        provider_name=settings.search_provider,
        api_key=api_key_map.get(settings.search_provider, ""),
        google_cx=settings.google_cx,
    )

    stats = {"searched": 0, "found": 0, "no_result": 0, "errors": 0}

    # Schools without any URL
    schools_with_url = session.query(SchoolSite.school_id).distinct()
    schools_without = (
        session.query(School)
        .filter(~School.id.in_(schools_with_url))
        .filter(School.status == "active")
        .limit(batch_size)
        .all()
    )

    log.info("search_discovery_start", provider=provider.name(), schools=len(schools_without))

    for school in schools_without:
        # Cascading query strategy — try specific first, broaden on failure
        queries = [
            f"{school.school_name} 情報公開 高等教育無償化",
            f"{school.school_name} 情報公開",
            f"{school.school_name} 専門学校",
        ]

        found = False
        for query in queries:
            try:
                results = provider.search(query, count=3)
            except Exception as e:
                log.warning("search_error", school=school.school_name, error=str(e))
                stats["errors"] += 1
                time.sleep(rate_limit_delay)
                break

            if results:
                # Find the best result (prefer .ac.jp domains and title matches)
                best = _pick_best_result(results, school)
                if best and _is_safe_url(best.url):
                    confidence = _score_search_result(best, school)
                    site = SchoolSite(
                        school_id=school.id,
                        url=best.url,
                        url_type="school" if school.school_name in best.url else "corporation_subpage",
                        discovery_method="web_search",
                        confidence=confidence,
                    )
                    session.add(site)
                    stats["found"] += 1
                    found = True
                    break

            time.sleep(rate_limit_delay)

        if not found and stats.get("errors", 0) == 0:
            stats["no_result"] += 1

        stats["searched"] += 1
        time.sleep(rate_limit_delay)

    session.flush()
    log.info("search_discovery_complete", **stats)
    return stats


def _pick_best_result(
    results: list,
    school: "School",
) -> object | None:
    """Pick the best search result for a school, preferring .ac.jp domains."""
    from eidp.scraper.search_provider import SearchResult

    scored: list[tuple[float, SearchResult]] = []
    for r in results:
        score = _score_search_result(r, school)
        scored.append((score, r))

    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[0][1] if scored else None


def _score_search_result(result: object, school: "School") -> float:
    """Score a search result for relevance to the target school."""
    score = 0.5
    title = getattr(result, "title", "")
    url = getattr(result, "url", "")

    # Name match in title
    if school.school_name in title:
        score = 0.9
    elif school.corporation_name and school.corporation_name in title:
        score = 0.7

    # Keyword match
    if any(kw in title for kw in ["情報公開", "公開情報", "学校情報", "機関要件"]):
        score = min(score + 0.1, 0.99)

    # Domain preference
    if ".ac.jp" in url:
        score = min(score + 0.05, 0.99)
    elif ".ed.jp" in url or ".go.jp" in url:
        score = min(score + 0.03, 0.99)

    return score


async def verify_urls_async(
    session: Session,
    batch_size: int = 50,
    timeout: float = 10.0,
) -> dict[str, int]:
    """Verify URLs by checking HTTP status. Updates school_site.http_status."""
    stats = {"checked": 0, "ok": 0, "failed": 0, "timeout": 0}

    unverified = (
        session.query(SchoolSite)
        .filter(SchoolSite.http_status.is_(None))
        .limit(batch_size)
        .all()
    )

    async with httpx.AsyncClient(
        timeout=timeout,
        follow_redirects=False,
        headers={"User-Agent": "EIDP-DataCollector/1.0 (institutional research)"},
    ) as client:
        for site in unverified:
            if not _is_safe_url(site.url):
                site.http_status = -2
                stats["failed"] += 1
                stats["checked"] += 1
                log.warning("ssrf_blocked_verify", url=site.url, school_id=site.school_id)
                continue
            try:
                resp = await client.head(site.url)
                # Follow redirects manually with SSRF check + cycle detection
                final_status = resp.status_code
                visited = {site.url}
                for _ in range(5):
                    if resp.status_code not in (301, 302, 303, 307, 308):
                        final_status = resp.status_code
                        break
                    location = resp.headers.get("location", "")
                    if not location:
                        final_status = resp.status_code
                        break
                    from urllib.parse import urljoin
                    location = urljoin(str(resp.url), location)
                    if location in visited or not _is_safe_url(location):
                        log.warning("ssrf_or_loop_blocked", url=location, origin=site.url)
                        final_status = -2
                        break
                    visited.add(location)
                    resp = await client.head(location)
                    final_status = resp.status_code
                site.http_status = final_status
                site.verified = final_status == 200
                if final_status == 200:
                    stats["ok"] += 1
                else:
                    stats["failed"] += 1
            except httpx.TimeoutException:
                site.http_status = 0
                stats["timeout"] += 1
            except httpx.HTTPError:
                site.http_status = -1
                stats["failed"] += 1
            stats["checked"] += 1

    session.flush()
    log.info("urls_verified", **stats)
    return stats


def verify_urls_sync(
    session: Session,
    batch_size: int = 50,
    timeout: float = 10.0,
) -> dict[str, int]:
    """Synchronous URL verification fallback."""
    stats = {"checked": 0, "ok": 0, "failed": 0, "timeout": 0}

    unverified = (
        session.query(SchoolSite)
        .filter(SchoolSite.http_status.is_(None))
        .limit(batch_size)
        .all()
    )

    with httpx.Client(
        timeout=timeout,
        follow_redirects=False,
        headers={"User-Agent": "EIDP-DataCollector/1.0 (institutional research)"},
    ) as client:
        for site in unverified:
            from datetime import datetime, timezone

            if not _is_safe_url(site.url):
                site.http_status = -2
                site.last_checked = datetime.now(timezone.utc)
                stats["failed"] += 1
                stats["checked"] += 1
                log.warning("ssrf_blocked_verify", url=site.url, school_id=site.school_id)
                continue
            try:
                # Try HEAD first, follow redirects with SSRF + cycle check
                resp = client.head(site.url)
                final_status = resp.status_code
                visited = {site.url}
                ssrf_blocked = False
                for _ in range(5):
                    if resp.status_code not in (301, 302, 303, 307, 308):
                        final_status = resp.status_code
                        break
                    location = resp.headers.get("location", "")
                    if not location:
                        final_status = resp.status_code
                        break
                    from urllib.parse import urljoin
                    location = urljoin(str(resp.url), location)
                    if location in visited or not _is_safe_url(location):
                        log.warning("ssrf_or_loop_blocked", url=location, origin=site.url)
                        final_status = -2
                        ssrf_blocked = True
                        break
                    visited.add(location)
                    resp = client.head(location)
                    final_status = resp.status_code
                # Fall back to GET only if HEAD returned 405/403 and not SSRF blocked
                if final_status in (405, 403) and not ssrf_blocked:
                    resp = client.get(site.url)
                    final_status = resp.status_code
                site.http_status = final_status
                site.verified = final_status == 200
                site.last_checked = datetime.now(timezone.utc)
                if final_status == 200:
                    site.verified_at = datetime.now(timezone.utc)
                    stats["ok"] += 1
                else:
                    stats["failed"] += 1
            except httpx.TimeoutException:
                site.http_status = 0
                site.last_checked = datetime.now(timezone.utc)
                stats["timeout"] += 1
            except httpx.HTTPError:
                site.http_status = -1
                site.last_checked = datetime.now(timezone.utc)
                stats["failed"] += 1
            stats["checked"] += 1

    session.flush()
    log.info("urls_verified", **stats)
    return stats


def get_discovery_stats(session: Session) -> dict[str, int | str]:
    """Report URL discovery coverage with verified/unverified breakdown.

    Distinguishes:
    - verified_disclosure: HTTP 200, school-specific URL (not corporation root)
    - unverified_root: corporation root or unchecked URL
    - total coverage: any URL (inflated, includes roots)
    """
    total_schools = session.query(func.count(School.id)).scalar() or 0
    schools_with_url = (
        session.query(func.count(func.distinct(SchoolSite.school_id))).scalar() or 0
    )

    # Verified school-specific disclosure pages (the real coverage number)
    verified_disclosure = (
        session.query(func.count(func.distinct(SchoolSite.school_id)))
        .filter(
            SchoolSite.http_status == 200,
            SchoolSite.url_type != "corporation",
        )
        .scalar() or 0
    )

    # Unverified or corporation-root-only schools
    verified_any = (
        session.query(func.count(func.distinct(SchoolSite.school_id)))
        .filter(SchoolSite.http_status == 200)
        .scalar() or 0
    )

    corp_only = (
        session.query(func.count(func.distinct(SchoolSite.school_id)))
        .filter(SchoolSite.url_type == "corporation")
        .scalar() or 0
    )

    unverified = (
        session.query(func.count(SchoolSite.id))
        .filter(SchoolSite.http_status.is_(None))
        .scalar() or 0
    )

    pct = lambda n: f"{n / total_schools * 100:.1f}%" if total_schools > 0 else "0%"

    return {
        "total_schools": total_schools,
        "schools_with_any_url": schools_with_url,
        "coverage_any": pct(schools_with_url),
        "verified_disclosure": verified_disclosure,
        "coverage_verified": pct(verified_disclosure),
        "verified_any_200": verified_any,
        "corporation_root_only": corp_only,
        "unverified_urls": unverified,
    }
