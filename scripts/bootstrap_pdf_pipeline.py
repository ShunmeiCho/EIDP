"""Sprint 8.7.e — end-to-end PDF discovery bootstrap on the operator PC.

This script runs the four-step PDF acquisition pipeline against the
local SQLite database. It is the production entrypoint behind
``bootstrap_pdfs.bat`` and also reusable as a manual recovery path:

    Step 1  download prefecture artifact PDFs / XLSX from URLs in
            data/prefecture-aggregators/seed.csv
    Step 2  ``eidp prefecture-aggregate --apply`` parses each artifact
            and inserts school_site rows
    Step 2b known seed URLs and corporation-domain patterns are registered
            as fallback crawl entry points
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

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(SCRIPTS_DIR))

from download_prefecture_artifacts import (  # noqa: E402
    DOWNLOADABLE_STATUSES,
    SUPPORTED_PARSERS,
    artifact_suffix,
    download_artifact,
    load_seed_rows,
    remove_stale_sibling_artifacts,
    write_source_url_sidecar,
)

TOTAL_BOOTSTRAP_STEPS = 5


def _bounded_step_percent(start: float, end: float, done: int, total: int) -> float:
    """Map a per-item stage count into the stage's progress range."""
    if total <= 0:
        return end
    ratio = max(0.0, min(done / total, 1.0))
    return start + ((end - start) * ratio)


class BootstrapProgressWriter:
    """Small JSON status writer for the Streamlit operator UI."""

    def __init__(self, path: Path | None) -> None:
        self.path = path
        self.started_at = datetime.now()

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
            payload["details"] = details

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
        url = row["artifact_url"]
        dest = artifact_dir / f"{pref}{artifact_suffix(row)}"
        if dest.exists() and not force:
            remove_stale_sibling_artifacts(dest)
            write_source_url_sidecar(dest, url)
            print(f"[step1] {pref}: already on disk ({dest.name})")
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
            continue
        print(f"[step1] {pref}: downloading {url}")
        try:
            download_artifact(url, dest)
            print(f"[step1] {pref}: ok ({dest.stat().st_size // 1024} KB)")
            ok.append(pref)
        except Exception as exc:
            print(f"[step1] {pref}: FAILED {exc}")
            failed.append((pref, str(exc)))
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
        resolve_prefecture_artifact,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    results: dict[str, dict[str, int]] = {}
    session = SessionLocal()
    try:
        total = len(pref_keys)
        for index, pref in enumerate(pref_keys, start=1):
            artifact = resolve_prefecture_artifact(artifact_dir, pref)
            if artifact is None:
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
            report = aggregate(session, pref, artifact)
            stats = apply_writer_plan(session, report)
            print(f"[step2] {pref}: extracted={report.extracted_total} matched={report.db_matched} applied={stats}")
            results[pref] = {
                "extracted": report.extracted_total,
                "matched": report.db_matched,
                "added": int(stats.get("added", 0)),
                "upgraded": int(stats.get("upgraded", 0)),
                "skipped": int(stats.get("skipped", 0)),
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
                        "extracted": int(report.extracted_total),
                        "matched": int(report.db_matched),
                        "added": int(stats.get("added", 0)),
                        "upgraded": int(stats.get("upgraded", 0)),
                    },
                )
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
    return results


def step_known_url_discovery(*, seed_url_csv: Path | None) -> dict[str, int]:
    """Step 2b: register known URL seeds and corporation-domain fallbacks."""
    from eidp.db.session import SessionLocal
    from eidp.scraper.url_discovery import import_seed_urls, infer_corporation_urls

    stats = {
        "seed_imported": 0,
        "seed_skipped_no_school": 0,
        "seed_skipped_existing": 0,
        "corporation_inferred": 0,
        "corporation_skipped_has_url": 0,
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
            ratio = (crawled / total_sites) if total_sites else 1.0
            # Step 3 owns the 45% -> 75% range. Leave 75% for the transition
            # into ingest so the UI does not imply Step 4 has started early.
            percent = min(0.74, 0.45 + (0.29 * ratio))
            progress.write(
                status="running",
                current_step=3,
                percent=percent,
                message=(
                    "学校サイトから対象年度PDFを探索しています。"
                    f"{crawled}/{total_sites}件確認済み / PDF {stats.get('downloaded', 0)}件"
                ),
                details={"sites_total": total_sites, **stats},
            )

        stats = run_pdf_discovery(
            session,
            storage_dir,
            batch_size=batch_size,
            rate_limit=rate_limit,
            discovery_methods=discovery_methods,
            evidence_path=evidence_log,
            target_fiscal_year=settings.target_fiscal_year,
            strict_target_fiscal_year=not allow_stale_fallback,
            progress_callback=update_progress,
        )
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
    if progress is not None:
        progress.write(
            status="running",
            current_step=2,
            percent=0.45,
            message="既知URLと法人ドメインを補助的に登録しています。",
            details={"school_sites_added": sum(s.get("added", 0) for s in aggregate_stats.values())},
        )
    if args.skip_known_url_discovery:
        print("\n[skip] Step 2b — --skip-known-url-discovery requested.")
        known_url_stats = {
            "seed_imported": 0,
            "seed_skipped_no_school": 0,
            "seed_skipped_existing": 0,
            "corporation_inferred": 0,
            "corporation_skipped_has_url": 0,
        }
    else:
        print("\n=== Step 2b: known URL / corporation fallback discovery ===")
        known_url_stats = step_known_url_discovery(seed_url_csv=args.seed_url_csv)

    if args.skip_discover:
        print("\n[skip] Step 3 / 4 — --skip-discover requested.")
        return 0

    if progress is not None:
        progress.write(
            status="running",
            current_step=3,
            percent=0.45,
            message="学校サイトから対象年度PDFを探索しています。",
            details={
                "school_sites_added": sum(s.get("added", 0) for s in aggregate_stats.values()),
                **known_url_stats,
            },
        )
    print("\n=== Step 3: discover-pdfs ===")
    discovery_methods = [method.strip() for method in args.discovery_methods.split(",") if method.strip()]
    discovery_stats = step_discover_pdfs(
        storage_dir=args.storage_dir,
        batch_size=args.batch_size,
        rate_limit=args.rate_limit,
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
            details=ingest_stats,
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
