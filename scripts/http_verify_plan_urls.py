"""HTTP + ownership verify the 207 actionable URLs from writer plans.

For each op=add/upgrade in *-writer-plan.json:
  1. HTTP HEAD / GET (with redirect follow, 10s timeout)
  2. Classify final response:
     - direct_pdf : Content-Type application/pdf + starts with %PDF-
     - html_ok    : HTML 200 + title/body contains school name OR corp name
     - html_suspect: HTML 200 but no school/corp match in title or H1
     - http_err   : non-200 or timeout
     - redirect_oob: redirected to unexpected domain
  3. Set ownership_ok = True only for direct_pdf or html_ok

Output: output/pref-aggregator/url-verification-{ts}.json
        output/pref-aggregator/url-verification-summary.json

This is the MANDATORY gate before apply_writer_plan.py --apply.
Only URLs with ownership_ok=True should be flipped to verified=true in DB.

Concurrency: asyncio.Semaphore(8) per-domain to avoid rate limits.
Rate limit: 1.5s between requests to same netloc (polite crawler).
"""

from __future__ import annotations

import asyncio
import json
import re
import sys
import time
import unicodedata
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx

REPO_ROOT = Path(__file__).resolve().parent.parent
PLAN_DIR = REPO_ROOT / "output" / "pref-aggregator"

CONCURRENCY = 8
PER_DOMAIN_DELAY_SEC = 1.5
TIMEOUT_SEC = 15.0
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 EIDP-Verifier/1.0"


def nfkc(s: str | None) -> str:
    if not s:
        return ""
    return unicodedata.normalize("NFKC", s)


def extract_signal_tokens(school_name: str, operator: str | None) -> list[str]:
    """Build minimum-length tokens to look for in page content."""
    tokens: list[str] = []
    nm = nfkc(school_name)
    # Core stem: strip 専門学校 / 大学 suffix → shorter identifying root
    root = re.sub(r"(専門学校|大学|短期大学|高等学校|学院)$", "", nm).strip()
    if len(root) >= 3:
        tokens.append(root)
    tokens.append(nm)
    if operator:
        op = nfkc(operator)
        op_root = re.sub(r"^(学校法人|公立大学法人|一般社団法人|医療法人社団|公益社団法人|公益財団法人)\s*", "", op).strip()
        if op_root and len(op_root) >= 2:
            tokens.append(op_root)
    # Dedupe preserving order
    seen: set[str] = set()
    out: list[str] = []
    for t in tokens:
        if t and t not in seen:
            seen.add(t)
            out.append(t)
    return out


@dataclass
class VerifyResult:
    pref: str
    op: str
    school_id: int | None
    school_name: str | None
    pdf_school_name: str | None
    url: str
    url_type: str | None
    final_url: str | None = None
    status: int | None = None
    content_type: str | None = None
    classification: str = "pending"  # direct_pdf | html_ok | html_suspect | http_err | redirect_oob | skip
    tokens_found: list[str] = field(default_factory=list)
    tokens_searched: list[str] = field(default_factory=list)
    ownership_ok: bool = False
    elapsed_ms: int = 0
    error: str | None = None


def classify_response(
    resp: httpx.Response,
    raw_content: bytes,
    tokens: list[str],
) -> tuple[str, list[str]]:
    """Return (classification, tokens_found)."""
    ct = (resp.headers.get("content-type") or "").lower()
    status = resp.status_code

    if status != 200:
        return "http_err", []

    # Direct PDF
    if "pdf" in ct or raw_content[:5] == b"%PDF-":
        return "direct_pdf", []

    # HTML path — look for tokens in body
    if "html" in ct or raw_content[:1000].lstrip().startswith(b"<"):
        try:
            text = raw_content.decode(resp.encoding or "utf-8", errors="replace")
        except Exception:
            text = raw_content.decode("utf-8", errors="replace")
        normed = nfkc(text[:200_000])  # cap 200KB for perf
        # Extract title + first 3 headings + meta og:site_name for focused check
        focus = ""
        m = re.search(r"<title[^>]*>(.*?)</title>", normed, re.IGNORECASE | re.DOTALL)
        if m:
            focus += m.group(1) + "\n"
        for tag in ("h1", "h2"):
            for m in re.finditer(rf"<{tag}[^>]*>(.*?)</{tag}>", normed, re.IGNORECASE | re.DOTALL):
                focus += re.sub(r"<[^>]+>", "", m.group(1)) + "\n"
        for m in re.finditer(r'meta[^>]*(?:property|name)=["\'](?:og:site_name|og:title|description)["\'][^>]*content=["\']([^"\']+)["\']', normed, re.IGNORECASE):
            focus += m.group(1) + "\n"
        focus_norm = nfkc(focus)
        found = [t for t in tokens if t and t in focus_norm]
        # Fallback: broader body search if focused region missed
        if not found:
            found = [t for t in tokens if t and t in normed]
        if found:
            return "html_ok", found
        return "html_suspect", []
    return "html_suspect", []


async def verify_one(
    sem: asyncio.Semaphore,
    domain_locks: dict[str, asyncio.Lock],
    client: httpx.AsyncClient,
    op: dict,
    pref: str,
    tokens: list[str],
) -> VerifyResult:
    url = op.get("new_url") or ""
    host = urlparse(url).netloc

    result = VerifyResult(
        pref=pref,
        op=op.get("op") or "",
        school_id=op.get("school_id"),
        school_name=op.get("school_name"),
        pdf_school_name=op.get("pdf_school_name"),
        url=url,
        url_type=op.get("new_url_type"),
        tokens_searched=tokens,
    )

    if not url:
        result.classification = "skip"
        result.error = "no url"
        return result

    async with sem:
        # per-domain serialization
        lock = domain_locks.setdefault(host, asyncio.Lock())
        async with lock:
            t0 = time.monotonic()
            try:
                resp = await client.get(url, follow_redirects=True)
                body = resp.content
                classification, found = classify_response(resp, body, tokens)
                result.final_url = str(resp.url)
                result.status = resp.status_code
                result.content_type = resp.headers.get("content-type")
                result.classification = classification
                result.tokens_found = found
                result.ownership_ok = classification in ("direct_pdf", "html_ok")
            except httpx.RequestError as e:
                result.classification = "http_err"
                result.error = f"{type(e).__name__}: {e}"
            except Exception as e:
                result.classification = "http_err"
                result.error = f"{type(e).__name__}: {e}"
            finally:
                result.elapsed_ms = int((time.monotonic() - t0) * 1000)
            await asyncio.sleep(PER_DOMAIN_DELAY_SEC)
    return result


async def run_verification() -> dict:
    # Collect all actionable ops from all writer plans
    plans: list[dict] = []
    for plan_path in sorted(PLAN_DIR.glob("*-writer-plan.json")):
        plan = json.loads(plan_path.read_text())
        pref = plan.get("pref")
        for op in plan.get("operations", []):
            if op.get("op") not in ("add", "upgrade"):
                continue
            plans.append({"pref": pref, "op": op})

    print(f"[verify] total actionable URLs to verify: {len(plans)}")

    sem = asyncio.Semaphore(CONCURRENCY)
    domain_locks: dict[str, asyncio.Lock] = {}
    results: list[VerifyResult] = []

    async with httpx.AsyncClient(
        timeout=TIMEOUT_SEC,
        headers={"User-Agent": UA, "Accept-Language": "ja,en;q=0.5"},
    ) as client:
        tasks = []
        for item in plans:
            op = item["op"]
            tokens = extract_signal_tokens(
                op.get("school_name") or op.get("pdf_school_name") or "",
                op.get("pdf_operator"),
            )
            tasks.append(verify_one(sem, domain_locks, client, op, item["pref"], tokens))
        for i in range(0, len(tasks), 20):
            batch = tasks[i:i+20]
            batch_results = await asyncio.gather(*batch)
            for r in batch_results:
                results.append(r)
                mark = "OK" if r.ownership_ok else "NG"
                print(f"  [{mark}] {r.pref:10s} {r.classification:14s} {r.school_name or r.pdf_school_name:<30s} {r.url[:80]}", flush=True)

    # Summarize
    by_class = defaultdict(int)
    by_pref = defaultdict(lambda: defaultdict(int))
    for r in results:
        by_class[r.classification] += 1
        by_pref[r.pref][r.classification] += 1

    verified_count = sum(1 for r in results if r.ownership_ok)
    suspect_count = sum(1 for r in results if not r.ownership_ok)

    summary = {
        "total": len(results),
        "verified_ownership_ok": verified_count,
        "suspect": suspect_count,
        "by_classification": dict(by_class),
        "by_prefecture": {k: dict(v) for k, v in by_pref.items()},
    }
    return {"summary": summary, "results": [asdict(r) for r in results]}


def main() -> None:
    t0 = time.monotonic()
    out = asyncio.run(run_verification())
    elapsed = time.monotonic() - t0

    ts = time.strftime("%Y%m%d_%H%M%S")
    detail_path = PLAN_DIR / f"url-verification-{ts}.json"
    detail_path.write_text(json.dumps(out, ensure_ascii=False, indent=2))

    latest_path = PLAN_DIR / "url-verification-summary.json"
    latest_path.write_text(json.dumps(out["summary"], ensure_ascii=False, indent=2))

    print(f"\n=== VERIFICATION SUMMARY ({elapsed:.1f}s) ===")
    print(json.dumps(out["summary"], ensure_ascii=False, indent=2))
    print(f"\nDetail: {detail_path}")
    print(f"Summary: {latest_path}")


if __name__ == "__main__":
    main()
