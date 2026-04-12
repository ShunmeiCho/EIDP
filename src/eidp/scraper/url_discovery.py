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

# Known corporation domain roots (for pattern-based initial discovery)
CORPORATION_DOMAINS: dict[str, str] = {
    "大原学園": "https://www.o-hara.ac.jp/",
    "名古屋大原学園": "https://www.o-hara.ac.jp/",
    "三幸学園": "https://www.sanko.ac.jp/",
    "穴吹学園": "https://www.anabuki.ac.jp/",
    "滋慶学園": "https://www.jikeigroup.net/",
    "東京滋慶学園": "https://www.jikeigroup.net/",
    "大阪滋慶学園": "https://www.jikeigroup.net/",
    "国際総合学園": "https://nsg.gr.jp/",
    "片柳学園": "https://www.neec.ac.jp/",
    "瀧澤学館": "https://www.takizawa.ac.jp/",
    "巨樹の会": "https://www.kyojunokai.or.jp/",
}

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
            if not url:
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

    These are NOT exact page URLs. They are corporation-level entry points
    that Step 8 (PDF discovery) will crawl to find disclosure pages.
    """
    stats = {"inferred": 0, "skipped_has_url": 0}

    for corp_name, domain in CORPORATION_DOMAINS.items():
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

    Requires EIDP_BRAVE_API_KEY or EIDP_GOOGLE_API_KEY in environment.
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
        # Build search query: school name + 情報公開 (disclosure page keyword)
        query = f"{school.school_name} 情報公開 高等教育無償化"

        try:
            results = provider.search(query, count=3)
        except Exception as e:
            log.warning("search_error", school=school.school_name, error=str(e))
            stats["errors"] += 1
            continue

        stats["searched"] += 1

        if not results:
            stats["no_result"] += 1
            continue

        # Take top result as primary URL
        top = results[0]

        # Score confidence based on title match
        confidence = 0.5
        if school.school_name in top.title:
            confidence = 0.9
        elif any(kw in top.title for kw in ["情報公開", "公開情報", "学校情報"]):
            confidence = 0.8
        elif school.corporation_name in top.title:
            confidence = 0.7

        site = SchoolSite(
            school_id=school.id,
            url=top.url,
            url_type="school" if school.school_name in top.url else "corporation_subpage",
            discovery_method="web_search",
            confidence=confidence,
        )
        session.add(site)
        stats["found"] += 1

        # Rate limiting: respect 1 req/sec
        time.sleep(rate_limit_delay)

    session.flush()
    log.info("search_discovery_complete", **stats)
    return stats


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
        follow_redirects=True,
        headers={"User-Agent": "EIDP-DataCollector/1.0 (institutional research)"},
    ) as client:
        for site in unverified:
            try:
                resp = await client.head(site.url)
                site.http_status = resp.status_code
                site.verified = resp.status_code == 200
                if resp.status_code == 200:
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
        follow_redirects=True,
        headers={"User-Agent": "EIDP-DataCollector/1.0 (institutional research)"},
    ) as client:
        for site in unverified:
            from datetime import datetime, timezone

            try:
                # Try HEAD first, fall back to GET if 405/403
                resp = client.head(site.url)
                if resp.status_code in (405, 403):
                    resp = client.get(site.url)
                site.http_status = resp.status_code
                site.verified = resp.status_code == 200
                site.last_checked = datetime.now(timezone.utc)
                if resp.status_code == 200:
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


def get_discovery_stats(session: Session) -> dict[str, int]:
    """Report URL discovery coverage."""
    total_schools = session.query(func.count(School.id)).scalar() or 0
    schools_with_url = (
        session.query(func.count(func.distinct(SchoolSite.school_id))).scalar() or 0
    )
    verified_ok = (
        session.query(func.count(SchoolSite.id))
        .filter(SchoolSite.http_status == 200)
        .scalar()
        or 0
    )
    high_confidence = (
        session.query(func.count(SchoolSite.id))
        .filter(SchoolSite.confidence >= 0.8)
        .scalar()
        or 0
    )

    return {
        "total_schools": total_schools,
        "schools_with_url": schools_with_url,
        "coverage": f"{schools_with_url / total_schools * 100:.1f}%" if total_schools > 0 else "0%",
        "verified_ok": verified_ok,
        "high_confidence": high_confidence,
    }
