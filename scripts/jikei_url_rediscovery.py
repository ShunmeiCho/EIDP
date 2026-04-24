"""Jikei URL rediscovery v2 — targeted probe for FY2025/2026 申請書 PDFs.

Scope: the 6 Jikei-group schools already in DB (100/103/104/107/108/111).
Does NOT modify DB. Produces:

  1. stdout evidence table: (school_id, url, http_status, size, verdict)
  2. SQL INSERT block for school_site rows that look like real申請書 PDFs
  3. JSONL evidence: output/jikei_url_rediscovery.jsonl

A candidate counts as 'likely_target' when the URL:
  - returns HTTP 200
  - size > 10KB (not an HTML 404 page served as 200)
  - filename matches positive keywords (confirmation_application /
    support_YYYY / 11_*)
  - not in NEGATIVE_KEYWORDS (admission, syllabus, curriculum, etc.)

The operator reviews the printed INSERT block, then runs it manually
(or via an authorized DML tool) to write the new SchoolSite rows.
discover-pdfs --school-id then picks them up normally.

Usage:
    uv run python scripts/jikei_url_rediscovery.py
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import httpx

from eidp.scraper.pdf_discovery import (
    NEGATIVE_KEYWORDS,
    POSITIVE_KEYWORDS,
    _classify_pdf_content,
)


# Known Jikei disclosure-page roots (per SchoolSite discovery_method=prefecture_aggregator)
JIKEI_SITES: dict[int, tuple[str, str]] = {
    100: ("東京アニメ・声優＆eスポーツ", "https://www.anime.ac.jp/school/public_info/"),
    103: ("東京コミュニケーションアート", "https://www.tca.ac.jp/creative/school/public_info/"),
    104: ("東京スクールオブミュージック＆ダンス", "https://www.tsm.ac.jp/school/public-info/"),
    107: ("東京ダンス・俳優＆舞台芸術", "https://www.da-tokyo.ac.jp/school/public_info.html"),
    108: ("東京デザインテクノロジーセンター", "https://www.tech.ac.jp/info/"),
    111: ("東京俳優・映画＆放送", "https://www.movie.ac.jp/school/public_info/"),
}

# Positive PDF filename markers that hint 'main 申請書'
FILENAME_POSITIVE_RE = re.compile(
    r"(confirmation[_-]?application|11[_-]?confirmation|"
    r"support[_-]?20\d{2}|"
    r"kakunin|機関要件)",
    re.IGNORECASE,
)

HEADERS = {
    "User-Agent": "Mozilla/5.0 EIDP-URL-Rediscovery/1.0",
    "Accept-Language": "ja,en;q=0.5",
}
OUT_JSONL = Path("output/jikei_url_rediscovery.jsonl")


@dataclass
class ProbeResult:
    school_id: int
    school_short: str
    disclosure_url: str
    candidate_url: str
    http_status: int
    size_bytes: int
    anchor_text: str
    verdict: str  # likely_target | rejected_negative | rejected_small | unreachable
    reason: str
    timestamp: str
    # Set by _classify_likely: runs same classifier as discover-pdfs
    # ('target' / 'non_target' / 'image_only' / 'unknown'). Only emitted
    # for candidates that passed the filename/size/keyword pre-filter.
    classifier: str = ""


def _negative_hit(url: str, anchor: str) -> str | None:
    haystack = f"{url} {anchor}".lower()
    for kw in NEGATIVE_KEYWORDS:
        if kw.lower() in haystack:
            return kw
    return None


def _positive_hit(url: str, anchor: str) -> str | None:
    if FILENAME_POSITIVE_RE.search(url):
        return "filename_pattern"
    for kw in POSITIVE_KEYWORDS:
        if kw in anchor:
            return kw
    return None


_HREF_RE = re.compile(r'href=["\']([^"\']+\.pdf[^"\']*)["\']')
_ANCHOR_RE = re.compile(
    r'<a[^>]*href=["\']([^"\']+\.pdf[^"\']*)["\'][^>]*>([^<]{0,80})</a>',
    re.IGNORECASE,
)


def _extract_pdf_anchors(html: str, base: str) -> list[tuple[str, str]]:
    """Return list of (absolute_url, anchor_text) from HTML."""
    seen: set[str] = set()
    out: list[tuple[str, str]] = []
    for m in _ANCHOR_RE.finditer(html):
        href, text = m.group(1), m.group(2).strip()
        absolute = urljoin(base, href)
        if absolute in seen:
            continue
        seen.add(absolute)
        out.append((absolute, text))
    # Fallback: unanchored hrefs
    for m in _HREF_RE.finditer(html):
        href = m.group(1)
        absolute = urljoin(base, href)
        if absolute in seen:
            continue
        seen.add(absolute)
        out.append((absolute, ""))
    return out


def _probe(client: httpx.Client, url: str) -> tuple[int, int]:
    """Return (http_status, size_bytes). 0/0 on error."""
    try:
        resp = client.head(url, follow_redirects=True, timeout=10.0)
        if resp.status_code == 200:
            cl = resp.headers.get("content-length")
            if cl and cl.isdigit():
                return 200, int(cl)
            # No content-length; fall back to GET
            g = client.get(url, follow_redirects=True, timeout=15.0)
            return g.status_code, len(g.content)
        return resp.status_code, 0
    except httpx.HTTPError:
        return 0, 0


def _classify(url: str, anchor: str, status: int, size: int) -> tuple[str, str]:
    if status != 200:
        return "unreachable", f"http={status}"
    if size < 10_000:
        return "rejected_small", f"size={size}"
    neg = _negative_hit(url, anchor)
    if neg:
        return "rejected_negative", f"negative_keyword={neg}"
    pos = _positive_hit(url, anchor)
    if pos:
        return "likely_target", f"positive={pos}"
    return "rejected_no_signal", ""


def _classify_body(client: httpx.Client, url: str) -> str:
    """Download candidate PDF and run the same classifier discover-pdfs uses.

    Returns 'target' / 'non_target' / 'image_only' / 'unknown' / 'fetch_error'.
    50 MB cap matches download_pdf.
    """
    try:
        resp = client.get(url, follow_redirects=True, timeout=30.0)
        if resp.status_code != 200:
            return "fetch_error"
        content = resp.content
        if len(content) < 1000 or len(content) > 50 * 1024 * 1024:
            return "unknown"
        if not content[:5] == b"%PDF-":
            return "unknown"
        return _classify_pdf_content(content)
    except httpx.HTTPError:
        return "fetch_error"


def rediscover_all() -> list[ProbeResult]:
    OUT_JSONL.parent.mkdir(parents=True, exist_ok=True)
    results: list[ProbeResult] = []
    with httpx.Client(headers=HEADERS, timeout=30.0) as client:
        for school_id, (short, disclosure_url) in JIKEI_SITES.items():
            try:
                r = client.get(disclosure_url, follow_redirects=True, timeout=20.0)
                html = r.text if r.status_code == 200 else ""
            except httpx.HTTPError:
                html = ""
            anchors = _extract_pdf_anchors(html, disclosure_url)
            for cand_url, anchor_text in anchors:
                status, size = _probe(client, cand_url)
                verdict, reason = _classify(cand_url, anchor_text, status, size)
                classifier = ""
                if verdict == "likely_target":
                    classifier = _classify_body(client, cand_url)
                results.append(ProbeResult(
                    school_id=school_id,
                    school_short=short,
                    disclosure_url=disclosure_url,
                    candidate_url=cand_url,
                    http_status=status,
                    size_bytes=size,
                    anchor_text=anchor_text,
                    verdict=verdict,
                    reason=reason,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    classifier=classifier,
                ))
    return results


def _print_report(results: list[ProbeResult]) -> None:
    print(f"# Jikei URL rediscovery — {len(results)} candidates probed")
    print()
    by_school: dict[int, list[ProbeResult]] = {}
    for r in results:
        by_school.setdefault(r.school_id, []).append(r)

    classifier_target: list[ProbeResult] = []
    for sid, items in sorted(by_school.items()):
        short = items[0].school_short
        print(f"## school_id={sid} — {short}")
        for r in sorted(items, key=lambda x: (x.verdict, x.candidate_url)):
            marker = "✓" if r.classifier == "target" else (
                "?" if r.verdict == "likely_target" else " "
            )
            classifier_tag = f" classifier={r.classifier}" if r.classifier else ""
            print(f"  {marker} [{r.verdict:22s}] {r.size_bytes:>8} bytes  {r.candidate_url[:75]}{classifier_tag}")
            if r.classifier == "target":
                classifier_target.append(r)
        print()

    if classifier_target:
        print("# Proposed INSERT — only classifier='target' (pre-validated):")
        print("INSERT INTO school_site (school_id, url, url_type, discovery_method, verified, http_status) VALUES")
        lines = []
        for r in classifier_target:
            esc = r.candidate_url.replace("'", "''")
            lines.append(f"  ({r.school_id}, '{esc}', 'pdf', 'pattern_probe', true, 200)")
        print(",\n".join(lines) + "\nON CONFLICT (school_id, url) DO NOTHING;")
    else:
        print("# No candidates passed the content classifier as 'target'.")


def main() -> None:
    results = rediscover_all()
    _print_report(results)

    with OUT_JSONL.open("w", encoding="utf-8") as fh:
        for r in results:
            fh.write(json.dumps(asdict(r), ensure_ascii=False) + "\n")
    print(f"\nFull evidence: {OUT_JSONL}")


if __name__ == "__main__":
    main()
