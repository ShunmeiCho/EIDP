"""Sprint 8.7.e — end-to-end PDF discovery bootstrap on the operator PC.

This script runs the four-step PDF acquisition pipeline against the
local SQLite database. It is the production entrypoint behind
``bootstrap_pdfs.bat`` and also reusable as a manual recovery path:

    Step 1  download prefecture artifact PDFs / XLSX from URLs in
            data/prefecture-aggregators/seed.csv
    Step 2  ``eidp prefecture-aggregate --apply`` parses each artifact
            and inserts school_site rows
    Step 3  ``eidp discover-pdfs --discovery-method prefecture_aggregator``
            crawls each school site and downloads PDFs into data/pdfs/
    Step 4  ``eidp ingest-pdfs`` parses downloaded PDFs into
            ``DepartmentYearly`` / ``SchoolYearStatus`` / ``SupportRecipient``
            rows, gated by the confidence thresholds.

Why not bake artifacts into the ZIP at build time?
    Prefectures publish new disclosures every fiscal year (R8, R9, ...).
    A ZIP that ships pre-downloaded artifacts is frozen against the
    build date. Running the pipeline on the operator PC keeps the data
    fresh.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Iterable
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(SCRIPTS_DIR))

from download_prefecture_artifacts import (  # type: ignore[import-not-found]  # noqa: E402
    DOWNLOADABLE_STATUSES,
    SUPPORTED_PARSERS,
    download_artifact,
    load_seed_rows,
)


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
) -> tuple[list[str], list[tuple[str, str]]]:
    """Step 1: ensure each pref artifact is on disk. Returns
    ``(downloaded_or_present, failed)``."""
    rows = load_seed_rows(seed_csv)
    targets = select_artifact_targets(rows, only=only)
    artifact_dir.mkdir(parents=True, exist_ok=True)

    ok: list[str] = []
    failed: list[tuple[str, str]] = []
    for row in targets:
        pref = row["pref_key"]
        url = row["artifact_url"]
        suffix = ".xlsx" if row.get("artifact_format") == "xlsx" else ".pdf"
        dest = artifact_dir / f"{pref}{suffix}"
        if dest.exists() and not force:
            print(f"[step1] {pref}: already on disk ({dest.name})")
            ok.append(pref)
            continue
        print(f"[step1] {pref}: downloading {url}")
        try:
            download_artifact(url, dest)
            print(f"[step1] {pref}: ok ({dest.stat().st_size // 1024} KB)")
            ok.append(pref)
        except Exception as exc:
            print(f"[step1] {pref}: FAILED {exc}")
            failed.append((pref, str(exc)))
    return ok, failed


def step_aggregate(
    *,
    pref_keys: list[str],
    artifact_dir: Path,
    output_dir: Path,
) -> dict[str, dict[str, int]]:
    """Step 2: invoke prefecture-aggregate apply for each prefecture."""
    from eidp.db.session import SessionLocal
    from eidp.scraper.prefecture_aggregator import (
        aggregate,
        apply_writer_plan,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    results: dict[str, dict[str, int]] = {}
    session = SessionLocal()
    try:
        for pref in pref_keys:
            artifact = artifact_dir / f"{pref}.pdf"
            if not artifact.is_file():
                xlsx = artifact_dir / f"{pref}.xlsx"
                if xlsx.is_file():
                    artifact = xlsx
                else:
                    print(f"[step2] {pref}: skip (no artifact)")
                    continue
            report = aggregate(session, pref, artifact)
            stats = apply_writer_plan(session, report)
            print(
                f"[step2] {pref}: extracted={report.extracted_total} "
                f"matched={report.db_matched} applied={stats}"
            )
            results[pref] = {
                "extracted": report.extracted_total,
                "matched": report.db_matched,
                "added": int(stats.get("added", 0)),
                "upgraded": int(stats.get("upgraded", 0)),
                "skipped": int(stats.get("skipped", 0)),
            }
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
    return results


def step_discover_pdfs(
    *,
    storage_dir: Path,
    batch_size: int,
    rate_limit: float,
    evidence_log: Path | None,
) -> dict[str, int]:
    """Step 3: crawl school sites and download disclosure PDFs."""
    from eidp.db.session import SessionLocal
    from eidp.scraper.pdf_discovery import run_pdf_discovery

    storage_dir.mkdir(parents=True, exist_ok=True)
    session = SessionLocal()
    try:
        stats = run_pdf_discovery(
            session,
            storage_dir,
            batch_size=batch_size,
            rate_limit=rate_limit,
            discovery_methods=["prefecture_aggregator"],
            evidence_path=evidence_log,
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pref", default="", help="Comma-separated pref_keys. Empty = every supported.")
    parser.add_argument("--seed-csv", type=Path,
                        default=REPO_ROOT / "data" / "prefecture-aggregators" / "seed.csv")
    parser.add_argument("--artifact-dir", type=Path,
                        default=REPO_ROOT / "data" / "prefecture-aggregators" / "artifacts")
    parser.add_argument("--aggregate-output", type=Path,
                        default=REPO_ROOT / "output" / "pref-aggregator")
    parser.add_argument("--storage-dir", type=Path,
                        default=REPO_ROOT / "data" / "pdfs")
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--rate-limit", type=float, default=1.5)
    parser.add_argument("--force-redownload", action="store_true",
                        help="Re-download prefecture artifacts even if cached.")
    parser.add_argument("--skip-discover", action="store_true",
                        help="Stop after aggregate. Useful for offline-only bootstrap.")
    parser.add_argument("--skip-ingest", action="store_true",
                        help="Stop after discover. Useful when ingest will run separately.")
    parser.add_argument(
        "--evidence-log", type=Path,
        default=REPO_ROOT / "output" / "discovery_rejections.jsonl",
    )
    args = parser.parse_args(argv)

    only = [p.strip() for p in args.pref.split(",") if p.strip()] or None

    print("=== Step 1: download prefecture artifacts ===")
    ok, failed = step_download_artifacts(
        seed_csv=args.seed_csv,
        artifact_dir=args.artifact_dir,
        only=only,
        force=args.force_redownload,
    )
    if not ok:
        print("ERROR: no prefecture artifacts available. Cannot proceed.")
        return 2
    if failed:
        print(f"WARNING: {len(failed)} prefecture downloads failed; continuing with the rest.")

    print("\n=== Step 2: prefecture-aggregate --apply ===")
    aggregate_stats = step_aggregate(
        pref_keys=ok,
        artifact_dir=args.artifact_dir,
        output_dir=args.aggregate_output,
    )

    if args.skip_discover:
        print("\n[skip] Step 3 / 4 — --skip-discover requested.")
        return 0

    print("\n=== Step 3: discover-pdfs ===")
    discovery_stats = step_discover_pdfs(
        storage_dir=args.storage_dir,
        batch_size=args.batch_size,
        rate_limit=args.rate_limit,
        evidence_log=args.evidence_log if str(args.evidence_log) else None,
    )

    if args.skip_ingest:
        print("\n[skip] Step 4 — --skip-ingest requested.")
        return 0

    print("\n=== Step 4: ingest-pdfs ===")
    ingest_stats = step_ingest(
        batch_size=args.batch_size,
        evidence_log=None,
    )

    print("\n=== Bootstrap pipeline summary ===")
    print(f"  prefectures: {len(ok)} ok / {len(failed)} failed")
    print(f"  aggregate:   {sum(s.get('added', 0) for s in aggregate_stats.values())} school_sites added")
    print(f"  discover:    {discovery_stats}")
    print(f"  ingest:      {ingest_stats}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
