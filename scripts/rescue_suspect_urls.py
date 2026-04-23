"""Second-pass verify for html_suspect URLs.

The initial http_verify_plan_urls.py marked URLs as html_suspect when
the first HTTP response body didn't contain school name tokens in
title/H1/og:site_name. But many are legitimate disclosure subpages
whose parent site clearly has the school.

Rescue strategy:
  1. For each suspect URL: also fetch root path (https://<domain>/)
  2. Also look for school name in body (not just title/H1 — broader scope)
  3. Match on domain-level signal: if root page contains school name
     → assume the subpage legitimately belongs to that school
  4. Promote suspect → rescued (ownership_ok=True)

Output: output/pref-aggregator/url-rescue-{ts}.json
Updates: merges into latest url-verification-*.json (rewrites ownership_ok)
"""

from __future__ import annotations

import asyncio
import json
import re
import sys
import time
import unicodedata
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import urlparse

import httpx

REPO_ROOT = Path(__file__).resolve().parent.parent
PLAN_DIR = REPO_ROOT / "output" / "pref-aggregator"

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 EIDP-Rescue/1.0"


def nfkc(s: str) -> str:
    return unicodedata.normalize("NFKC", s) if s else ""


def latest_verification_file() -> Path:
    files = sorted(PLAN_DIR.glob("url-verification-202*.json"))
    if not files:
        raise FileNotFoundError("run scripts/http_verify_plan_urls.py first")
    return files[-1]


async def fetch_text(client: httpx.AsyncClient, url: str, timeout: float = 15.0) -> str:
    try:
        resp = await client.get(url, timeout=timeout, follow_redirects=True)
        if resp.status_code != 200:
            return ""
        ct = (resp.headers.get("content-type") or "").lower()
        if "html" not in ct and not resp.content[:200].lstrip().startswith(b"<"):
            return ""
        try:
            return resp.content.decode(resp.encoding or "utf-8", errors="replace")
        except Exception:
            return resp.content.decode("utf-8", errors="replace")
    except Exception:
        return ""


def tokens_in(text: str, tokens: list[str]) -> list[str]:
    if not text or not tokens:
        return []
    normed = nfkc(text[:300_000])
    return [t for t in tokens if t and t in normed]


async def rescue_one(client: httpx.AsyncClient, sem: asyncio.Semaphore, rec: dict) -> dict:
    url = rec["url"]
    tokens = rec.get("tokens_searched") or []
    parsed = urlparse(url)
    root = f"{parsed.scheme}://{parsed.netloc}/"

    async with sem:
        # Fetch root + reuse first-pass subpage body via re-fetch (cheap)
        root_text, sub_text = await asyncio.gather(
            fetch_text(client, root),
            fetch_text(client, url),
        )
        await asyncio.sleep(1.0)  # polite

    # Broader body search (not just title/H1)
    root_hits = tokens_in(root_text, tokens)
    sub_hits = tokens_in(sub_text, tokens)

    ownership_ok = bool(root_hits or sub_hits)
    return {
        "url": url,
        "school_name": rec.get("school_name"),
        "tokens_searched": tokens,
        "root_hits": root_hits,
        "subpage_body_hits": sub_hits,
        "ownership_ok_after_rescue": ownership_ok,
        "promoted": ownership_ok and not rec.get("ownership_ok"),
    }


async def run_rescue() -> dict:
    verify_path = latest_verification_file()
    data = json.loads(verify_path.read_text())
    suspect_records = [r for r in data["results"] if r["classification"] == "html_suspect"]

    print(f"[rescue] suspect count: {len(suspect_records)}")

    sem = asyncio.Semaphore(6)
    async with httpx.AsyncClient(
        timeout=15.0,
        headers={"User-Agent": UA, "Accept-Language": "ja,en;q=0.5"},
    ) as client:
        results = await asyncio.gather(*(rescue_one(client, sem, r) for r in suspect_records))

    promoted = [r for r in results if r["promoted"]]
    still_suspect = [r for r in results if not r["ownership_ok_after_rescue"]]

    print(f"[rescue] promoted: {len(promoted)} / {len(results)}")
    for r in promoted:
        print(f"  [RESCUED] {r['school_name']} — root_hits={r['root_hits']} sub_hits={r['subpage_body_hits']}")
    for r in still_suspect:
        print(f"  [STILL SUSPECT] {r['school_name']} — url={r['url']}")

    # Merge: update the original verification file's ownership_ok for promoted URLs
    promoted_urls = {r["url"] for r in promoted}
    for rec in data["results"]:
        if rec["url"] in promoted_urls:
            rec["ownership_ok"] = True
            rec["classification"] = "html_ok_rescued"

    # Recompute summary
    from collections import defaultdict
    by_class: dict[str, int] = defaultdict(int)
    for r in data["results"]:
        by_class[r["classification"]] += 1
    data["summary"]["verified_ownership_ok"] = sum(1 for r in data["results"] if r["ownership_ok"])
    data["summary"]["suspect"] = len(data["results"]) - data["summary"]["verified_ownership_ok"]
    data["summary"]["by_classification"] = dict(by_class)
    data["summary"]["rescued_from_suspect"] = len(promoted)

    verify_path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    summary_path = PLAN_DIR / "url-verification-summary.json"
    summary_path.write_text(json.dumps(data["summary"], ensure_ascii=False, indent=2))

    rescue_path = PLAN_DIR / f"url-rescue-{time.strftime('%Y%m%d_%H%M%S')}.json"
    rescue_path.write_text(json.dumps({"rescue_results": results}, ensure_ascii=False, indent=2))

    return data["summary"]


def main() -> None:
    summary = asyncio.run(run_rescue())
    print("\n=== RESCUE SUMMARY ===")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
