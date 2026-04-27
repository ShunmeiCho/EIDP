"""Read-only simulation of `discover-pdfs` on the verified prefecture
aggregator URLs.

Uses the **real** production pipeline `discover_pdfs_for_site`
(includes sub-page following) so results match what
`eidp discover-pdfs --school-id ...` would produce — except no DB writes
and no PDF download.

Reviewer note (2026-04-27): the previous version of this script only
called `_extract_pdf_links` + `_score_candidate` on the disclosure URL
itself, missing the sub-page two-tier pattern, which caused 12/22
"no_pdf_found" classifications to be misleading. The real production
discovery follows sub-page links once.

Output:
- output/pref-aggregator/sim-discover-{ts}.json — per-school audit trail
- stdout summary

Usage:
    uv run python scripts/sim_discover_verified.py \\
        [--input output/pref-aggregator/url-verification-{ts}.json]
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import httpx

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from eidp.scraper.pdf_discovery import (  # noqa: E402
    HEADERS,
    PdfCandidate,
    discover_pdfs_for_site,
)


def classify_pdf_target(top: PdfCandidate | None) -> str:
    """Match production target/non_target heuristic at candidate level."""
    if top is None:
        return "no_pdf_found"
    if top.score >= 5.0:
        return "target_likely"
    if top.score >= 2.0:
        return "target_marginal"
    if top.score <= -1.0:
        return "non_target"
    return "ambiguous"


def has_r8_signal(top: PdfCandidate | None) -> bool:
    if top is None:
        return False
    text = (top.anchor_text + " " + top.pdf_url).lower()
    return any(s in text for s in ("令和8", "令和08", "2026", "r8"))


def simulate(records: list[dict]) -> list[dict]:
    """Use fresh httpx.Client per record to match production's per-site
    isolation in run_pdf_discovery's `for site in sites` loop. Sharing a
    single Client across 22 sequential calls produces empty candidate
    lists for several URLs (server-side rate limiting or pool reuse
    artifacts), even though production-exact isolated calls return
    candidates. Production uses one Client for many sites too, but
    operates with a real `time.sleep(rate_limit)` cadence — sim does not."""
    out: list[dict] = []
    # follow_redirects MUST be False to match _safe_get's manual handling.
    client_kwargs = {"timeout": 30.0, "follow_redirects": False, "headers": HEADERS}
    for r in records:
        url = r.get("final_url") or r.get("url")
        sid = r.get("school_id") or 0
        name = r.get("school_name")
        pref = r.get("pref")
        op = r.get("op")
        with httpx.Client(**client_kwargs) as client:
            result = discover_pdfs_for_site(client, sid, url, max_depth=2)
        top = result.best
        out.append({
            "school_id": sid,
            "school_name": name,
            "pref": pref,
            "op": op,
            "url": url,
            "fetch_error": result.error,
            "candidates": len(result.candidates),
            "top_pdf_url": top.pdf_url if top else None,
            "top_anchor": (top.anchor_text or "")[:80] if top else None,
            "top_score": top.score if top else None,
            "classification": classify_pdf_target(top),
            "r8_signal": has_r8_signal(top),
        })
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=REPO_ROOT / "output/pref-aggregator/url-verification-summary.json",
        help="Path to url-verification-*.json (NOT -summary.json). "
             "Defaults to summary if no detail file path is supplied.",
    )
    args = parser.parse_args()

    in_path = args.input
    if not in_path.exists():
        # Fallback: pick the latest detail file
        candidates = sorted(
            (REPO_ROOT / "output/pref-aggregator").glob("url-verification-2*.json")
        )
        if not candidates:
            print(f"[sim] no verification file found at {in_path} or via glob", file=sys.stderr)
            sys.exit(1)
        in_path = candidates[-1]
        print(f"[sim] using latest detail file: {in_path}")

    raw = json.loads(in_path.read_text())
    records = raw if isinstance(raw, list) else raw.get("records", raw.get("results", []))
    if not records:
        print(f"[sim] no records in {in_path}", file=sys.stderr)
        sys.exit(1)

    oks = [r for r in records if r.get("classification") == "html_ok"]
    print(f"[sim] verified ownership_ok URLs: {len(oks)} (from {len(records)} total)")
    print("[sim] using REAL pipeline discover_pdfs_for_site (with sub-page follow)")

    results = simulate(oks)

    by_class: dict[str, int] = {}
    r8_hits = 0
    for r in results:
        by_class[r["classification"]] = by_class.get(r["classification"], 0) + 1
        if r["r8_signal"]:
            r8_hits += 1

    print("\n[sim] classification distribution:")
    for k, v in sorted(by_class.items(), key=lambda x: -x[1]):
        print(f"  {k:<20} {v}")
    print(f"\n[sim] PDFs with R8 signal in URL/anchor: {r8_hits}/{len(oks)}")

    print("\n[sim] target_likely + target_marginal sample (top score):")
    targets = sorted(
        [r for r in results if r["classification"].startswith("target")],
        key=lambda r: r["top_score"] or 0,
        reverse=True,
    )
    for r in targets[:20]:
        r8 = "R8" if r["r8_signal"] else "  "
        print(
            f"  [{r['classification']:<16}] {r8} score={r['top_score']:>4.1f} "
            f"sid={r['school_id']} {r['school_name']}"
        )
        print(f"    -> {r['top_pdf_url']}")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = REPO_ROOT / f"output/pref-aggregator/sim-discover-{ts}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(
        {
            "sim_at": ts,
            "input": str(in_path),
            "by_classification": by_class,
            "r8_hits": r8_hits,
            "results": results,
        },
        ensure_ascii=False,
        indent=2,
    ))
    print(f"\n[sim] full audit -> {out_path}")


if __name__ == "__main__":
    main()
