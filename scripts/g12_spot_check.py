"""G12 cost / SLO spot-check for weekly PDF discovery.

Runs ``run_pdf_discovery`` on a representative SAMPLE of target-missing schools
while measuring wall-clock and real network bandwidth, then extrapolates to the
full weekly denominator and compares against the G12 SLOs:

  - weekly run wall-clock  < 30 min   (G12_WEEKLY_WALLCLOCK_SECONDS)
  - single-weekly bandwidth < 2 GB    (G12_WEEKLY_BANDWIDTH_BYTES)

It also surfaces the B1 bounded pre-rank cost (``prerank_*`` counters) so a
regression in the pre-rank pass — which is what made G12 a watch item — is
visible against the rest of the run.

Design notes
------------
* NON-INVASIVE: network bytes are measured by wrapping ``httpx.Client.send`` at
  runtime. No production code is changed. Cache hits return inside
  ``_RunScopedHttpCache.get`` before the base client is touched, so they are not
  counted as network bytes (correct: a cache hit costs no bandwidth).
* SIDE-EFFECT-FREE: PDFs download to a TEMP dir that is always removed, and the
  DB session is ALWAYS rolled back, so a spot-check never persists Documents or
  files. To actually acquire PDFs, use the weekly runner
  ``run_weekly_target_year_discovery.py --limit N`` instead.
* LIVE NETWORK: this hits real school servers and is run by the maintainer /
  operator. It is NOT part of CI. Point ``EIDP_DATABASE_URL`` at a real
  (ideally copied) DB that already has crawlable SchoolSite rows.
* Stealth / rendered (Scrapling) fetches that bypass httpx are not byte-counted;
  the bandwidth figure covers httpx GETs (HTML, sitemap, PDF), which is the bulk
  of weekly traffic. This caveat is reported in the output.

Usage
-----
    uv run python scripts/g12_spot_check.py --limit 40 --json
    uv run python scripts/g12_spot_check.py --limit 60 --out report.json
"""

from __future__ import annotations

import argparse
import contextlib
import json
import shutil
import sys
import tempfile
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import httpx

SCRIPTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPTS_DIR.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(SCRIPTS_DIR))

from run_weekly_target_year_discovery import (  # noqa: E402
    DEFAULT_METHODS,
    count_crawlable_sites_for_school_ids,
    select_target_missing_school_ids,
)
from sqlalchemy.exc import OperationalError  # noqa: E402

from eidp.config import settings  # noqa: E402
from eidp.db.locking import LockBusyError, acquire_lock  # noqa: E402
from eidp.db.session import SessionLocal  # noqa: E402
from eidp.logging_config import configure_logging  # noqa: E402
from eidp.scraper.pdf_discovery import run_pdf_discovery  # noqa: E402

# G12 SLO thresholds (CLAUDE.md Engineering Goals). Bandwidth is decimal GB to
# match the "<2 GB" / "~2418 schools x <1 MB" phrasing.
G12_WEEKLY_WALLCLOCK_SECONDS = 30 * 60
G12_WEEKLY_BANDWIDTH_BYTES = 2 * 1000**3
# Fallback denominator when the live DB cannot produce a target-missing count
# (matches the CLAUDE.md master-school estimate).
FALLBACK_TOTAL_SCHOOLS = 2418
# A spot-check whose extrapolation lands within this fraction of an SLO is a
# MARGIN (watch), not a clean PASS.
MARGIN_FRACTION = 0.8


class _NetworkMeter:
    """Accumulates real network response bytes and request count."""

    def __init__(self) -> None:
        self.bytes = 0
        self.requests = 0


@contextlib.contextmanager
def measure_network() -> Iterator[_NetworkMeter]:
    """Wrap ``httpx.Client.send`` to tally response bytes for the duration.

    Discovery issues plain (non-streaming) GETs, so ``response.content`` is
    already buffered by the time ``send`` returns and reading it here is a
    cached, side-effect-free access.
    """
    meter = _NetworkMeter()
    original_send = httpx.Client.send

    def patched_send(self: httpx.Client, request: httpx.Request, **kwargs: Any) -> httpx.Response:
        response = original_send(self, request, **kwargs)
        meter.requests += 1
        try:
            meter.bytes += len(response.content)
        except Exception:  # noqa: BLE001 - measurement must never break the run
            pass
        return response

    httpx.Client.send = patched_send  # type: ignore[method-assign]
    try:
        yield meter
    finally:
        httpx.Client.send = original_send  # type: ignore[method-assign]


def _slo_verdict(extrapolated: float, threshold: float) -> str:
    if extrapolated >= threshold:
        return "FAIL"
    if extrapolated >= threshold * MARGIN_FRACTION:
        return "MARGIN"
    return "PASS"


def _round(value: float, digits: int = 2) -> float:
    return round(value, digits)


def run_spot_check(
    *,
    current_fy: int,
    methods: list[str] | None,
    school_type: str | None,
    limit: int,
    rate_limit: float,
    request_timeout: float,
    total_schools_override: int | None,
) -> dict[str, Any]:
    """Run discovery on a sample, measure cost, extrapolate vs G12 SLOs.

    Always side-effect-free: the DB session is rolled back and the temp storage
    dir is removed, regardless of outcome.
    """
    session = SessionLocal()
    temp_storage = Path(tempfile.mkdtemp(prefix="eidp-g12-spotcheck-"))
    try:
        try:
            sample_ids = select_target_missing_school_ids(
                session,
                current_fy=current_fy,
                methods=methods,
                school_type=school_type,
                limit=limit,
            )
            total_target_missing = len(
                select_target_missing_school_ids(
                    session,
                    current_fy=current_fy,
                    methods=methods,
                    school_type=school_type,
                    limit=None,
                )
            )
        except OperationalError as exc:
            session.rollback()
            return {
                "status": "db_not_ready",
                "error": f"{type(exc).__name__}: {exc}",
                "hint": (
                    "The database has no schema or is unreachable. Run "
                    "`eidp db-bootstrap` or point EIDP_DATABASE_URL at a ready DB "
                    "that already has crawlable SchoolSite rows."
                ),
            }

        denominator = total_schools_override or total_target_missing or FALLBACK_TOTAL_SCHOOLS

        if not sample_ids:
            return {
                "status": "no_sample",
                "message": (
                    "No crawlable target-missing schools found for the given "
                    "filters; seed SchoolSite rows or relax --methods/--school-type."
                ),
                "current_fy": current_fy,
                "methods": methods,
                "school_type": school_type,
                "total_target_missing_schools": total_target_missing,
            }

        sample_site_count = count_crawlable_sites_for_school_ids(
            session, school_ids=sample_ids, methods=methods
        )
        effective_batch_size = max(len(sample_ids), sample_site_count)

        started = time.monotonic()
        with measure_network() as meter:
            stats = run_pdf_discovery(
                session,
                storage_dir=temp_storage,
                batch_size=effective_batch_size,
                rate_limit=rate_limit,
                request_timeout=request_timeout,
                discovery_methods=methods,
                school_ids=sample_ids,
                target_fiscal_year=current_fy,
                strict_target_fiscal_year=True,
            )
        elapsed = time.monotonic() - started
        # Always discard: this is a measurement, never an acquisition.
        session.rollback()

        sample_size = len(sample_ids)
        per_school_seconds = elapsed / sample_size
        per_school_bytes = meter.bytes / sample_size
        extrapolated_seconds = per_school_seconds * denominator
        extrapolated_bytes = per_school_bytes * denominator

        prerank = {
            key: int(stats.get(key, 0))
            for key in (
                "prerank_classified",
                "prerank_skipped",
                "prerank_failed",
                "prerank_uncached_large",
            )
        }
        prerank_probes = sum(prerank.values())

        wallclock_verdict = _slo_verdict(extrapolated_seconds, G12_WEEKLY_WALLCLOCK_SECONDS)
        bandwidth_verdict = _slo_verdict(extrapolated_bytes, G12_WEEKLY_BANDWIDTH_BYTES)
        overall = (
            "FAIL"
            if "FAIL" in (wallclock_verdict, bandwidth_verdict)
            else "MARGIN"
            if "MARGIN" in (wallclock_verdict, bandwidth_verdict)
            else "PASS"
        )

        return {
            "status": "ok",
            "side_effect_free": True,
            "current_fy": current_fy,
            "methods": methods,
            "school_type": school_type,
            "rate_limit_seconds": rate_limit,
            "sample": {
                "schools": sample_size,
                "crawlable_sites": sample_site_count,
            },
            "denominator": {
                "schools": denominator,
                "source": (
                    "override"
                    if total_schools_override
                    else "target_missing"
                    if total_target_missing
                    else "fallback_2418"
                ),
                "total_target_missing_schools": total_target_missing,
            },
            "measured": {
                "wallclock_seconds": _round(elapsed),
                "network_bytes": meter.bytes,
                "network_requests": meter.requests,
                "http_cache_hits": int(stats.get("http_cache_hits", 0)),
                "http_cache_misses": int(stats.get("http_cache_misses", 0)),
                "downloaded": int(stats.get("downloaded", 0)),
            },
            "per_school": {
                "seconds": _round(per_school_seconds, 3),
                "bytes": int(per_school_bytes),
            },
            "extrapolated_weekly": {
                "wallclock_seconds": _round(extrapolated_seconds),
                "wallclock_minutes": _round(extrapolated_seconds / 60, 1),
                "bytes": int(extrapolated_bytes),
                "gigabytes": _round(extrapolated_bytes / 1000**3, 3),
            },
            "g12_slo": {
                "wallclock": {
                    "threshold_minutes": G12_WEEKLY_WALLCLOCK_SECONDS / 60,
                    "verdict": wallclock_verdict,
                },
                "bandwidth": {
                    "threshold_gigabytes": G12_WEEKLY_BANDWIDTH_BYTES / 1000**3,
                    "verdict": bandwidth_verdict,
                },
                "overall": overall,
            },
            "b1_prerank": {
                **prerank,
                "total_probes": prerank_probes,
            },
            "discovery_stats": {k: int(v) for k, v in stats.items() if isinstance(v, int)},
            "caveats": [
                "Bandwidth counts httpx GETs only; Scrapling/stealth fetches are not measured.",
                "Extrapolation is linear in school count and assumes the sample is representative.",
                "Wall-clock is dominated by rate_limit sleeps on cache misses; tune --rate-limit to match production.",
            ],
        }
    finally:
        session.close()
        shutil.rmtree(temp_storage, ignore_errors=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--limit", type=int, default=40, help="Sample size: number of target-missing schools to crawl."
    )
    parser.add_argument("--current-fy", type=int, default=settings.target_fiscal_year)
    parser.add_argument("--methods", nargs="+", default=list(DEFAULT_METHODS))
    parser.add_argument("--school-type", default="専門学校")
    parser.add_argument(
        "--rate-limit", type=float, default=1.5, help="Per-request throttle seconds (match production weekly)."
    )
    parser.add_argument("--request-timeout", type=float, default=12.0)
    parser.add_argument(
        "--total-schools",
        type=int,
        default=None,
        help="Override the extrapolation denominator (default: live target-missing count).",
    )
    parser.add_argument("--no-lock", action="store_true", help="Skip the shared app lock.")
    parser.add_argument("--lock-path", type=Path, default=settings.app_root / "data" / ".lock")
    parser.add_argument("--out", type=Path, default=None, help="Also write the JSON report to this path.")
    parser.add_argument("--json", action="store_true", help="Print JSON (default output is JSON regardless).")
    return parser.parse_args()


def main() -> int:
    configure_logging(app_root=settings.app_root)
    args = parse_args()
    school_type = None if args.school_type == "all" else args.school_type

    def _run() -> dict[str, Any]:
        return run_spot_check(
            current_fy=args.current_fy,
            methods=args.methods,
            school_type=school_type,
            limit=args.limit,
            rate_limit=args.rate_limit,
            request_timeout=args.request_timeout,
            total_schools_override=args.total_schools,
        )

    try:
        if args.no_lock:
            report = _run()
        else:
            with acquire_lock(args.lock_path, owner="g12_spot_check"):
                report = _run()
    except LockBusyError as exc:
        report = {"status": "lock_busy", "error": f"{type(exc).__name__}: {exc}"}

    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)

    slo = report.get("g12_slo")
    overall = slo.get("overall") if isinstance(slo, dict) else None
    return 1 if overall == "FAIL" or report.get("status") not in {"ok", "no_sample"} else 0


if __name__ == "__main__":
    raise SystemExit(main())
