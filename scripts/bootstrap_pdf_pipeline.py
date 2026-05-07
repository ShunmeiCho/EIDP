"""Sprint 8.7.e — end-to-end PDF discovery bootstrap on the operator PC.

This script runs the four-step PDF acquisition pipeline against the
local SQLite database. It is the production entrypoint behind
``bootstrap_pdfs.bat`` and also reusable as a manual recovery path:

    Step 1  download prefecture artifact PDFs / XLSX from URLs in
            data/prefecture-aggregators/seed.csv
    Step 2  ``eidp prefecture-aggregate --apply`` parses each artifact
            and inserts school_site rows
    Step 2b known seed URLs, corporation-domain patterns, and optional Web
            search are registered as fallback crawl entry points
    Step 3  ``eidp discover-pdfs`` crawls trusted school_site methods and
            downloads PDFs into data/pdfs/
    Step 4  ``eidp ingest-pdfs`` parses downloaded PDFs into
            ``DepartmentYearly`` / ``SchoolYearStatus`` / ``SupportRecipient``
            rows, gated by the confidence thresholds.
    Step 5  rebuild ``SchoolFiscalYearStatus`` rows for the operator UI.

Scope note:
    The prefecture-aggregator layer starts from official prefectural
    確認大学等 index artifacts. Those artifacts may include universities,
    prefectural vocational schools, and private vocational schools. Coverage
    still depends on which prefectures have a supported parser and a current
    artifact URL in ``data/prefecture-aggregators/seed.csv``.

Why not bake artifacts into the ZIP at build time?
    Prefectures publish new disclosures every fiscal year.
    A ZIP that ships pre-downloaded artifacts is frozen against the
    build date. Running the pipeline on the operator PC keeps the data
    fresh.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path
from typing import Any


def _configure_utf8_stdio(stdout: Any = sys.stdout, stderr: Any = sys.stderr) -> None:
    """Keep Windows manual runs from crashing on Japanese log text."""

    for stream in (stdout, stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="replace")


_configure_utf8_stdio()

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(SCRIPTS_DIR))

from download_prefecture_artifacts import (  # noqa: E402
    DOWNLOADABLE_STATUSES,
    SUPPORTED_PARSERS,
    artifact_download_targets,
    download_artifact,
    load_seed_rows,
    remove_stale_sibling_artifacts,
    write_source_url_sidecar,
)

TOTAL_BOOTSTRAP_STEPS = 5
URL_SEARCH_PERCENT_START = 0.45
URL_SEARCH_PERCENT_END = 0.60
PDF_DISCOVERY_PERCENT_START = URL_SEARCH_PERCENT_END
PDF_DISCOVERY_PERCENT_END = 0.75


def _bounded_step_percent(start: float, end: float, done: int, total: int) -> float:
    """Map a per-item stage count into the stage's progress range."""
    if total <= 0:
        return end
    ratio = max(0.0, min(done / total, 1.0))
    return start + ((end - start) * ratio)


def ingest_progress_details(stats: dict[str, int]) -> dict[str, int]:
    """Namespace ingest counters so they do not overwrite discovery counters.

    The progress writer accumulates details across steps. Step 3 and Step 4
    both produce a ``skipped`` key, but the operator cares about Step 3's
    rejected/old-year PDF count while acquisition is being diagnosed. Keep
    the ingest value available under ``ingest_*`` without hiding discovery.
    """
    return {f"ingest_{key}": int(value) for key, value in stats.items()}


def discovery_progress_details(total_sites: int, stats: dict[str, int]) -> dict[str, int]:
    """Return progress details with a stable discovery rejection counter."""
    details = {"sites_total": total_sites, **stats}
    if "skipped" in stats:
        details["discovery_skipped"] = int(stats["skipped"])
    return details


class BootstrapProgressWriter:
    """Small JSON status writer for the Streamlit operator UI."""

    def __init__(self, path: Path | None) -> None:
        self.path = path
        self.started_at = datetime.now()
        self._accumulated_details: dict[str, Any] = {}

    def write(
        self,
        *,
        status: str,
        current_step: int,
        message: str,
        percent: float,
        error: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        if self.path is None:
            return

        now = datetime.now()
        payload: dict[str, Any] = {
            "status": status,
            "current_step": max(0, min(current_step, TOTAL_BOOTSTRAP_STEPS)),
            "total_steps": TOTAL_BOOTSTRAP_STEPS,
            "percent": max(0.0, min(percent, 1.0)),
            "message": message,
            "started_at": self.started_at.isoformat(timespec="seconds"),
            "updated_at": now.isoformat(timespec="seconds"),
            "log_path": str(self.path.with_suffix(".log")),
        }
        if status in {"succeeded", "failed"}:
            payload["completed_at"] = now.isoformat(timespec="seconds")
        if error:
            payload["error"] = error
        if details:
            self._accumulated_details.update(details)
            payload["details"] = details
        elif status in {"succeeded", "failed"} and self._accumulated_details:
            payload["details"] = dict(self._accumulated_details)

        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp_path.replace(self.path)


def select_artifact_targets(
    rows: Iterable[dict[str, str]],
    *,
    only: Iterable[str] | None,
) -> list[dict[str, str]]:
    """Pick rows to download. ``only`` filters by pref_key, defaulting
    to every supported parser whose seed entry has a verified URL."""
    wanted = set(only) if only else None
    return [
        row
        for row in rows
        if row.get("pref_key") in SUPPORTED_PARSERS
        and row.get("verified_status") in DOWNLOADABLE_STATUSES
        and row.get("artifact_url", "").startswith("http")
        and (wanted is None or row.get("pref_key") in wanted)
    ]


def step_download_artifacts(
    *,
    seed_csv: Path,
    artifact_dir: Path,
    only: Iterable[str] | None,
    force: bool,
    progress: BootstrapProgressWriter | None = None,
) -> tuple[list[str], list[tuple[str, str]]]:
    """Step 1: ensure each pref artifact is on disk. Returns
    ``(downloaded_or_present, failed)``."""
    rows = load_seed_rows(seed_csv)
    targets = select_artifact_targets(rows, only=only)
    artifact_dir.mkdir(parents=True, exist_ok=True)

    ok: list[str] = []
    failed: list[tuple[str, str]] = []
    total = len(targets)
    for index, row in enumerate(targets, start=1):
        pref = row["pref_key"]
        pref_ok = False
        for url, filename in artifact_download_targets(row):
            dest = artifact_dir / filename
            if dest.exists() and not force:
                remove_stale_sibling_artifacts(dest)
                write_source_url_sidecar(dest, url)
                print(f"[step1] {pref}: already on disk ({dest.name})")
                pref_ok = True
                continue
            print(f"[step1] {pref}: downloading {url}")
            try:
                download_artifact(url, dest)
                print(f"[step1] {pref}: ok ({dest.name}, {dest.stat().st_size // 1024} KB)")
                pref_ok = True
            except Exception as exc:
                print(f"[step1] {pref}: FAILED {url}: {exc}")
                failed.append((pref, f"{url}: {exc}"))
        if pref_ok:
            ok.append(pref)
        if progress is not None:
            progress.write(
                status="running",
                current_step=1,
                percent=_bounded_step_percent(0.05, 0.25, index, total),
                message=f"都道府県公開データを取得しています。{index}/{total}件: {pref}",
                details={
                    "prefectures_total": total,
                    "prefectures_done": index,
                    "prefecture": pref,
                    "prefectures_ok": len(ok),
                    "prefectures_failed": len(failed),
                },
            )
    return ok, failed


def step_aggregate(
    *,
    pref_keys: list[str],
    artifact_dir: Path,
    output_dir: Path,
    progress: BootstrapProgressWriter | None = None,
) -> dict[str, dict[str, int]]:
    """Step 2: invoke prefecture-aggregate apply for each prefecture."""
    from eidp.db.session import SessionLocal
    from eidp.scraper.prefecture_aggregator import (
        aggregate,
        apply_writer_plan,
        resolve_prefecture_artifacts,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    results: dict[str, dict[str, int]] = {}
    session = SessionLocal()
    try:
        total = len(pref_keys)
        for index, pref in enumerate(pref_keys, start=1):
            artifacts = resolve_prefecture_artifacts(artifact_dir, pref)
            if not artifacts:
                print(f"[step2] {pref}: skip (no artifact)")
                if progress is not None:
                    progress.write(
                        status="running",
                        current_step=2,
                        percent=_bounded_step_percent(0.25, 0.45, index, total),
                        message=f"都道府県データから学校URLを登録しています。{index}/{total}件: {pref}",
                        details={
                            "prefectures_total": total,
                            "prefectures_done": index,
                            "prefecture": pref,
                            "prefectures_aggregated": len(results),
                        },
                )
                continue
            merged = {
                "extracted": 0,
                "matched": 0,
                "added": 0,
                "upgraded": 0,
                "skipped": 0,
                "artifacts": len(artifacts),
            }
            for artifact in artifacts:
                report = aggregate(session, pref, artifact)
                stats = apply_writer_plan(session, report)
                print(
                    f"[step2] {pref}/{artifact.name}: "
                    f"extracted={report.extracted_total} matched={report.db_matched} applied={stats}"
                )
                merged["extracted"] += int(report.extracted_total)
                merged["matched"] += int(report.db_matched)
                merged["added"] += int(stats.get("added", 0))
                merged["upgraded"] += int(stats.get("upgraded", 0))
                merged["skipped"] += int(stats.get("skipped", 0))
            results[pref] = {
                "extracted": merged["extracted"],
                "matched": merged["matched"],
                "added": merged["added"],
                "upgraded": merged["upgraded"],
                "skipped": merged["skipped"],
                "artifacts": merged["artifacts"],
            }
            if progress is not None:
                progress.write(
                    status="running",
                    current_step=2,
                    percent=_bounded_step_percent(0.25, 0.45, index, total),
                    message=f"都道府県データから学校URLを登録しています。{index}/{total}件: {pref}",
                    details={
                        "prefectures_total": total,
                        "prefectures_done": index,
                        "prefecture": pref,
                        "prefectures_aggregated": len(results),
                        "artifacts": merged["artifacts"],
                        "extracted": merged["extracted"],
                        "matched": merged["matched"],
                        "added": merged["added"],
                        "upgraded": merged["upgraded"],
                    },
                )
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
    return results


def aggregate_yield_details(aggregate_stats: dict[str, dict[str, int]]) -> dict[str, int]:
    """Flatten prefecture aggregation yield into operator progress details."""
    total_prefs = len(aggregate_stats)
    no_new_url_prefs = sum(
        1
        for stats in aggregate_stats.values()
        if int(stats.get("matched", 0)) > 0
        and int(stats.get("added", 0)) == 0
        and int(stats.get("upgraded", 0)) == 0
    )
    return {
        "official_prefectures_aggregated": total_prefs,
        "official_artifacts_parsed": sum(int(stats.get("artifacts", 0)) for stats in aggregate_stats.values()),
        "official_index_rows_extracted": sum(int(stats.get("extracted", 0)) for stats in aggregate_stats.values()),
        "official_index_rows_matched": sum(int(stats.get("matched", 0)) for stats in aggregate_stats.values()),
        "official_school_sites_added": sum(int(stats.get("added", 0)) for stats in aggregate_stats.values()),
        "official_school_sites_upgraded": sum(int(stats.get("upgraded", 0)) for stats in aggregate_stats.values()),
        "official_index_rows_skipped": sum(int(stats.get("skipped", 0)) for stats in aggregate_stats.values()),
        "official_prefectures_without_new_urls": no_new_url_prefs,
    }


def provider_ready_for_url_search(
    *,
    provider: str,
    serper_api_key: str = "",
    brave_api_key: str = "",
    google_api_key: str = "",
    google_cx: str = "",
) -> bool:
    """Return whether the configured search provider can run without prompting."""
    normalized = provider.strip().lower()
    if normalized == "duckduckgo":
        return True
    if normalized == "serper":
        return bool(serper_api_key.strip())
    if normalized == "brave":
        return bool(brave_api_key.strip())
    if normalized == "google":
        return bool(google_api_key.strip() and google_cx.strip())
    return False


def resolve_url_search_mode(
    *,
    configured_mode: str,
    provider: str,
    batch_size: int,
    serper_api_key: str = "",
    brave_api_key: str = "",
    google_api_key: str = "",
    google_cx: str = "",
) -> tuple[bool, int, str]:
    """Resolve operator settings into a safe URL-search execution decision."""
    mode = configured_mode.strip().lower()
    if mode not in {"auto", "on", "off"}:
        mode = "auto"
    bounded_batch_size = max(int(batch_size), 0)
    if mode == "off" or bounded_batch_size == 0:
        return False, bounded_batch_size, mode
    provider_ready = provider_ready_for_url_search(
        provider=provider,
        serper_api_key=serper_api_key,
        brave_api_key=brave_api_key,
        google_api_key=google_api_key,
        google_cx=google_cx,
    )
    if mode == "on":
        return True, bounded_batch_size, "on"
    return provider_ready, bounded_batch_size, "auto_ready" if provider_ready else "auto_not_ready"


def step_known_url_discovery(
    *,
    seed_url_csv: Path | None,
    search_missing_urls: bool = False,
    search_batch_size: int = 0,
    url_search_evidence_log: Path | None = None,
    progress: BootstrapProgressWriter | None = None,
) -> dict[str, int]:
    """Step 2b: register known URL seeds, corporation fallbacks, and optional Web search."""
    from eidp.db.session import SessionLocal
    from eidp.scraper.url_discovery import import_seed_urls, infer_corporation_urls, search_and_discover

    stats = {
        "seed_imported": 0,
        "seed_skipped_no_school": 0,
        "seed_skipped_existing": 0,
        "corporation_inferred": 0,
        "corporation_skipped_has_url": 0,
        "search_enabled": 0,
        "search_searched": 0,
        "search_found": 0,
        "search_no_result": 0,
        "search_errors": 0,
    }
    session = SessionLocal()
    try:
        if seed_url_csv is not None and seed_url_csv.is_file():
            seed_stats = import_seed_urls(session, seed_url_csv)
            stats["seed_imported"] = int(seed_stats.get("imported", 0))
            stats["seed_skipped_no_school"] = int(seed_stats.get("skipped_no_school", 0))
            stats["seed_skipped_existing"] = int(seed_stats.get("skipped_existing", 0))

        corporation_stats = infer_corporation_urls(session)
        stats["corporation_inferred"] = int(corporation_stats.get("inferred", 0))
        stats["corporation_skipped_has_url"] = int(corporation_stats.get("skipped_has_url", 0))
        if search_missing_urls and search_batch_size > 0:
            stats["search_enabled"] = 1

            def update_search_progress(search_stats: dict[str, int], total_schools: int) -> None:
                if progress is None:
                    return
                searched = int(search_stats.get("searched", 0))
                progress.write(
                    status="running",
                    current_step=2,
                    percent=_bounded_step_percent(
                        URL_SEARCH_PERCENT_START,
                        URL_SEARCH_PERCENT_END,
                        searched,
                        total_schools,
                    ),
                    message=(
                        "不足URLをWeb検索で補完しています。"
                        f"{searched}/{total_schools}校確認済み / "
                        f"入口候補 {search_stats.get('found', 0)}件"
                    ),
                    details={
                        **stats,
                        "search_searched": searched,
                        "search_found": int(search_stats.get("found", 0)),
                        "search_no_result": int(search_stats.get("no_result", 0)),
                        "search_errors": int(search_stats.get("errors", 0)),
                    },
                )

            try:
                search_stats = search_and_discover(
                    session,
                    batch_size=search_batch_size,
                    evidence_path=url_search_evidence_log,
                    progress_callback=update_search_progress,
                )
            except Exception as exc:
                stats["search_errors"] += 1
                print(f"[step2b] web search fallback skipped after error: {exc}")
            else:
                stats["search_searched"] = int(search_stats.get("searched", 0))
                stats["search_found"] = int(search_stats.get("found", 0))
                stats["search_no_result"] = int(search_stats.get("no_result", 0))
                stats["search_errors"] = int(search_stats.get("errors", 0))
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
    print(f"[step2b] {stats}")
    return stats


def step_discover_pdfs(
    *,
    storage_dir: Path,
    batch_size: int,
    rate_limit: float,
    request_timeout: float,
    evidence_log: Path | None,
    discovery_methods: list[str],
    progress: BootstrapProgressWriter | None = None,
    allow_stale_fallback: bool = False,
) -> dict[str, int]:
    """Step 3: crawl school sites and download disclosure PDFs."""
    from eidp.config import settings
    from eidp.db.session import SessionLocal
    from eidp.scraper.pdf_discovery import run_pdf_discovery

    storage_dir.mkdir(parents=True, exist_ok=True)
    session = SessionLocal()
    try:
        def update_progress(stats: dict[str, int], total_sites: int) -> None:
            if progress is None:
                return
            crawled = stats.get("crawled", 0)
            active_index = stats.get("active_index", 0)
            ratio = (crawled / total_sites) if total_sites else 1.0
            # Step 3 owns the 60% -> 75% range. Leave 75% for the transition
            # into ingest so the UI does not imply Step 4 has started early.
            percent = min(
                PDF_DISCOVERY_PERCENT_END - 0.01,
                PDF_DISCOVERY_PERCENT_START
                + ((PDF_DISCOVERY_PERCENT_END - PDF_DISCOVERY_PERCENT_START - 0.01) * ratio),
            )
            active_note = f"（{active_index}件目を確認中）" if active_index and active_index > crawled else ""
            progress.write(
                status="running",
                current_step=3,
                percent=percent,
                message=(
                    "学校サイトから対象年度PDFを探索しています。"
                    f"{crawled}/{total_sites}件確認済み{active_note} / PDF {stats.get('downloaded', 0)}件"
                ),
                details=discovery_progress_details(total_sites, stats),
            )

        stats = run_pdf_discovery(
            session,
            storage_dir,
            batch_size=batch_size,
            rate_limit=rate_limit,
            request_timeout=request_timeout,
            discovery_methods=discovery_methods,
            evidence_path=evidence_log,
            target_fiscal_year=settings.target_fiscal_year,
            strict_target_fiscal_year=not allow_stale_fallback,
            progress_callback=update_progress,
        )
        if "skipped" in stats:
            stats["discovery_skipped"] = int(stats["skipped"])
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
    print(f"[step3] {stats}")
    return stats


def step_ingest(
    *,
    batch_size: int,
    evidence_log: Path | None,
) -> dict[str, int]:
    """Step 4: parse downloaded PDFs into DB rows."""
    from eidp.db.session import SessionLocal
    from eidp.pipeline.ingest import run_ingestion

    session = SessionLocal()
    try:
        stats = run_ingestion(
            session,
            batch_size=batch_size,
            evidence_path=evidence_log,
        )
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
    print(f"[step4] {stats}")
    return stats


def step_rebuild_status() -> dict[str, int]:
    """Step 5: rebuild School x target fiscal-year status rows for the UI."""
    from eidp.config import settings
    from eidp.db.session import SessionLocal
    from eidp.pipeline.school_fiscal_year_status import rebuild_school_fiscal_year_status

    session = SessionLocal()
    try:
        stats = rebuild_school_fiscal_year_status(
            session,
            fiscal_year=settings.target_fiscal_year,
            school_type=None,
        )
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
    out = {"rebuilt": stats.rebuilt, "excel_ready": stats.excel_ready}
    print(f"[step5] {out}")
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pref", default="", help="Comma-separated pref_keys. Empty = every supported.")
    parser.add_argument("--seed-csv", type=Path, default=REPO_ROOT / "data" / "prefecture-aggregators" / "seed.csv")
    parser.add_argument(
        "--seed-url-csv",
        type=Path,
        default=REPO_ROOT / "data" / "url-discovery" / "discovered-urls-50.csv",
        help="Known school URL CSV imported before PDF discovery.",
    )
    parser.add_argument(
        "--skip-known-url-discovery",
        action="store_true",
        help="Skip known seed URL import and corporation-domain fallback registration.",
    )
    parser.add_argument(
        "--url-search",
        choices=("settings", "auto", "on", "off"),
        default="settings",
        help=(
            "Whether Step 2b should use the configured search provider for schools still missing a URL. "
            "'settings' reads EIDP_URL_SEARCH_AUTO_ENABLE from .env."
        ),
    )
    parser.add_argument(
        "--url-search-batch-size",
        type=int,
        default=None,
        help="Override EIDP_URL_SEARCH_BATCH_SIZE for Step 2b. 0 disables the Web search fallback.",
    )
    parser.add_argument(
        "--artifact-dir", type=Path, default=REPO_ROOT / "data" / "prefecture-aggregators" / "artifacts"
    )
    parser.add_argument("--aggregate-output", type=Path, default=REPO_ROOT / "output" / "pref-aggregator")
    parser.add_argument("--storage-dir", type=Path, default=REPO_ROOT / "data" / "pdfs")
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10000,
        help="Max sites to crawl in step 3 / docs to ingest in step 4. "
        "Default 10000 = effectively unlimited for v1 corpus (~700 sites). "
        "Set lower to bound a single bootstrap session.",
    )
    parser.add_argument("--rate-limit", type=float, default=1.5)
    parser.add_argument(
        "--request-timeout",
        type=float,
        default=12.0,
        help=(
            "Per HTTP request timeout for Step 3 PDF discovery. "
            "Initial bootstrap uses a shorter default than developer CLI runs "
            "so one slow school site does not freeze the UI."
        ),
    )
    parser.add_argument(
        "--force-redownload", action="store_true", help="Re-download prefecture artifacts even if cached."
    )
    parser.add_argument(
        "--skip-discover", action="store_true", help="Stop after aggregate. Useful for offline-only bootstrap."
    )
    parser.add_argument(
        "--skip-ingest", action="store_true", help="Stop after discover. Useful when ingest will run separately."
    )
    parser.add_argument(
        "--allow-stale-fallback",
        action="store_true",
        help=(
            "Allow older-year PDFs to be downloaded when the target fiscal year "
            "is not confirmed. Default rejects stale fallback candidates."
        ),
    )
    parser.add_argument(
        "--discovery-methods",
        default="prefecture_aggregator,seed_csv,corporation_pattern",
        help=(
            "Comma-separated school_site.discovery_method values crawled in Step 3. "
            "Default includes official prefecture URLs plus known seed/corporation fallbacks."
        ),
    )
    parser.add_argument(
        "--evidence-log",
        type=Path,
        default=REPO_ROOT / "output" / "discovery_rejections.jsonl",
    )
    parser.add_argument(
        "--url-search-evidence-log",
        type=Path,
        default=REPO_ROOT / "output" / "url_search_evidence.jsonl",
        help="Append-only JSONL evidence for Web-search URL discovery decisions.",
    )
    parser.add_argument(
        "--lock-path",
        type=Path,
        default=REPO_ROOT / "data" / ".lock",
        help="Advisory lock path used to pause UI writes while bootstrap runs.",
    )
    parser.add_argument(
        "--progress-file",
        type=Path,
        default=None,
        help="JSON status file written for the Streamlit operator UI.",
    )
    parser.add_argument("--no-lock", action="store_true", help="Developer-only: run without the app lock.")
    args = parser.parse_args(argv)
    progress = BootstrapProgressWriter(args.progress_file)

    if not args.no_lock:
        from eidp.db.locking import LockBusyError, acquire_lock

        try:
            with acquire_lock(args.lock_path, owner="bootstrap_pdfs"):
                return run_bootstrap_with_progress(args, progress)
        except LockBusyError as exc:
            print(f"ERROR: another EIDP process is running: {exc}")
            progress.write(
                status="failed",
                current_step=0,
                percent=0.0,
                message="別の処理が実行中のため、初回取得を開始できませんでした。",
                error=str(exc),
            )
            return 5
    return run_bootstrap_with_progress(args, progress)


def run_bootstrap_with_progress(args: argparse.Namespace, progress: BootstrapProgressWriter) -> int:
    try:
        progress.write(
            status="running",
            current_step=0,
            percent=0.0,
            message="初回取得を準備中です。",
        )
        rc = run_bootstrap(args, progress=progress)
    except Exception as exc:
        progress.write(
            status="failed",
            current_step=TOTAL_BOOTSTRAP_STEPS,
            percent=1.0,
            message="初回取得中にエラーが発生しました。診断ログを確認してください。",
            error=str(exc),
        )
        raise

    if rc == 0:
        progress.write(
            status="succeeded",
            current_step=TOTAL_BOOTSTRAP_STEPS,
            percent=1.0,
            message="初回URL/PDF取得が完了しました。画面を更新してください。",
        )
    else:
        progress.write(
            status="failed",
            current_step=TOTAL_BOOTSTRAP_STEPS,
            percent=1.0,
            message=f"初回取得が終了コード {rc} で停止しました。診断ログを確認してください。",
            error=f"exit_code={rc}",
        )
    return rc


def run_bootstrap(args: argparse.Namespace, *, progress: BootstrapProgressWriter | None = None) -> int:
    only = [p.strip() for p in args.pref.split(",") if p.strip()] or None

    if progress is not None:
        progress.write(
            status="running",
            current_step=1,
            percent=0.05,
            message="対応済みの都道府県公開データを取得しています。",
        )
    print("=== Step 1: download prefecture artifacts ===")
    ok, failed = step_download_artifacts(
        seed_csv=args.seed_csv,
        artifact_dir=args.artifact_dir,
        only=only,
        force=args.force_redownload,
        progress=progress,
    )
    if not ok:
        print("ERROR: no prefecture artifacts available. Cannot proceed.")
        return 2
    if failed:
        print(f"WARNING: {len(failed)} prefecture downloads failed; continuing with the rest.")

    if progress is not None:
        progress.write(
            status="running",
            current_step=2,
            percent=0.25,
            message="都道府県データから学校URLを登録しています。",
            details={"prefectures_ok": len(ok), "prefectures_failed": len(failed)},
        )
    print("\n=== Step 2: prefecture-aggregate --apply ===")
    aggregate_stats = step_aggregate(
        pref_keys=ok,
        artifact_dir=args.artifact_dir,
        output_dir=args.aggregate_output,
        progress=progress,
    )
    aggregate_details = aggregate_yield_details(aggregate_stats)
    if progress is not None:
        progress.write(
            status="running",
            current_step=2,
            percent=URL_SEARCH_PERCENT_START,
            message="既知URL、法人ドメイン、不足URL検索を補助的に登録しています。",
            details=aggregate_details,
        )
    from eidp.config import settings

    url_search_mode = str(settings.url_search_auto_enable)
    if args.url_search != "settings":
        url_search_mode = args.url_search
    configured_search_batch_size = (
        int(settings.url_search_batch_size) if args.url_search_batch_size is None else int(args.url_search_batch_size)
    )
    search_missing_urls, search_batch_size, url_search_reason = resolve_url_search_mode(
        configured_mode=url_search_mode,
        provider=str(settings.search_provider),
        batch_size=configured_search_batch_size,
        serper_api_key=str(settings.serper_api_key),
        brave_api_key=str(settings.brave_api_key),
        google_api_key=str(settings.google_api_key),
        google_cx=str(settings.google_cx),
    )
    if args.skip_known_url_discovery:
        print("\n[skip] Step 2b — --skip-known-url-discovery requested.")
        known_url_stats = {
            "seed_imported": 0,
            "seed_skipped_no_school": 0,
            "seed_skipped_existing": 0,
            "corporation_inferred": 0,
            "corporation_skipped_has_url": 0,
            "search_enabled": 0,
            "search_searched": 0,
            "search_found": 0,
            "search_no_result": 0,
            "search_errors": 0,
        }
    else:
        print("\n=== Step 2b: known URL / corporation fallback discovery ===")
        print(
            "[step2b] url_search="
            f"{url_search_reason} provider={settings.search_provider} batch_size={search_batch_size}"
        )
        known_url_stats = step_known_url_discovery(
            seed_url_csv=args.seed_url_csv,
            search_missing_urls=search_missing_urls,
            search_batch_size=search_batch_size,
            url_search_evidence_log=args.url_search_evidence_log,
            progress=progress,
        )
    post_url_details = {**aggregate_details, **known_url_stats}
    if progress is not None:
        progress.write(
            status="running",
            current_step=2,
            percent=URL_SEARCH_PERCENT_END if known_url_stats.get("search_enabled", 0) else URL_SEARCH_PERCENT_START,
            message="公式一覧、既知URL、法人ドメインの入口登録が完了しました。",
            details=post_url_details,
        )

    if args.skip_discover:
        print("\n[skip] Step 3 / 4 — --skip-discover requested.")
        return 0

    if progress is not None:
        progress.write(
            status="running",
            current_step=3,
            percent=PDF_DISCOVERY_PERCENT_START,
            message="学校サイトから対象年度PDFを探索しています。",
            details=post_url_details,
        )
    print("\n=== Step 3: discover-pdfs ===")
    discovery_methods = [method.strip() for method in args.discovery_methods.split(",") if method.strip()]
    if known_url_stats.get("search_found", 0) > 0 and "web_search" not in discovery_methods:
        discovery_methods.append("web_search")
    discovery_stats = step_discover_pdfs(
        storage_dir=args.storage_dir,
        batch_size=args.batch_size,
        rate_limit=args.rate_limit,
        request_timeout=args.request_timeout,
        evidence_log=args.evidence_log if str(args.evidence_log) else None,
        discovery_methods=discovery_methods,
        progress=progress,
        allow_stale_fallback=args.allow_stale_fallback,
    )

    if args.skip_ingest:
        print("\n[skip] Step 4 — --skip-ingest requested.")
        return 0

    if progress is not None:
        progress.write(
            status="running",
            current_step=4,
            percent=0.75,
            message="取得したPDFを読み取り、DBへ登録しています。",
            details=discovery_stats,
        )
    print("\n=== Step 4: ingest-pdfs ===")
    ingest_stats = step_ingest(
        batch_size=args.batch_size,
        evidence_log=None,
    )
    if progress is not None:
        progress.write(
            status="running",
            current_step=5,
            percent=0.9,
            message="学校別タスクを再計算しています。",
            details=ingest_progress_details(ingest_stats),
        )
    print("\n=== Step 5: rebuild school fiscal-year status ===")
    status_stats = step_rebuild_status()

    print("\n=== Bootstrap pipeline summary ===")
    print(f"  prefectures: {len(ok)} ok / {len(failed)} failed")
    print(f"  aggregate:   {sum(s.get('added', 0) for s in aggregate_stats.values())} school_sites added")
    print(f"  known URLs:  {known_url_stats}")
    print(f"  discover:    {discovery_stats}")
    print(f"  ingest:      {ingest_stats}")
    print(f"  status:      {status_stats}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
