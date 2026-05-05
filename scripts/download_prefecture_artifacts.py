"""Download prefecture-aggregator artifact PDFs/XLSX into the repo.

Sprint 8.7.e — bootstrap automation gate. ``eidp prefecture-aggregate``
needs ``data/prefecture-aggregators/artifacts/{pref}.pdf`` (or
``.xlsx``) already on disk before it can extract URLs into school_site.

This script is dev-side: it reads ``data/prefecture-aggregators/seed.csv``,
selects rows whose parser is registered AND whose ``verified_status`` is
``spiked`` or ``downloaded`` (i.e. we have a confirmed artifact URL), then
downloads each artifact under ``data/prefecture-aggregators/artifacts/``
using the same idiomatic name the CLI expects.

We deliberately keep this offline-friendly for the operator PC: the
ZIP build folds the resulting artifacts into ``data/...artifacts/``
inside the ZIP, so first_setup.bat can run ``eidp
prefecture-aggregate --apply`` with no network.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import httpx

REPO_ROOT = Path(__file__).resolve().parents[1]
SEED_CSV = REPO_ROOT / "data" / "prefecture-aggregators" / "seed.csv"
ARTIFACT_DIR = REPO_ROOT / "data" / "prefecture-aggregators" / "artifacts"

# Parsers that exist in src/eidp/scraper/prefecture_aggregator.py PARSERS.
SUPPORTED_PARSERS = frozenset({
    "tokyo", "kanagawa", "saitama", "miyagi", "fukuoka",
    "hyogo", "shizuoka", "okinawa",
})

# verified_status values that indicate the artifact_url is real.
DOWNLOADABLE_STATUSES = frozenset({"spiked", "downloaded"})


def load_seed_rows(seed_csv: Path) -> list[dict[str, str]]:
    with seed_csv.open("r", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def select_targets(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """Pick rows that have a parser AND a confirmed artifact URL."""
    return [
        row
        for row in rows
        if row.get("pref_key") in SUPPORTED_PARSERS
        and row.get("verified_status") in DOWNLOADABLE_STATUSES
        and row.get("artifact_url", "").startswith("http")
    ]


def download_artifact(url: str, dest: Path, *, timeout: float = 60.0) -> None:
    """Stream-download a single artifact. Overwrites existing files."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    with httpx.Client(follow_redirects=True, timeout=timeout) as client:
        response = client.get(url)
        response.raise_for_status()
        dest.write_bytes(response.content)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pref",
        default="",
        help=(
            "Comma-separated prefecture keys. Empty = every supported parser "
            "with verified_status in {spiked, downloaded}."
        ),
    )
    parser.add_argument(
        "--seed-csv", type=Path, default=SEED_CSV,
        help=f"Override the seed CSV path. Default: {SEED_CSV}",
    )
    parser.add_argument(
        "--artifact-dir", type=Path, default=ARTIFACT_DIR,
        help=f"Override the artifact output dir. Default: {ARTIFACT_DIR}",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Overwrite existing artifact files (default skips them).",
    )
    args = parser.parse_args(argv)

    rows = load_seed_rows(args.seed_csv)
    targets = select_targets(rows)
    if args.pref:
        wanted = {p.strip() for p in args.pref.split(",") if p.strip()}
        targets = [r for r in targets if r["pref_key"] in wanted]

    if not targets:
        print("No targets selected.")
        return 1

    args.artifact_dir.mkdir(parents=True, exist_ok=True)

    failures: list[tuple[str, str]] = []
    for row in targets:
        pref = row["pref_key"]
        url = row["artifact_url"]
        suffix = ".xlsx" if row.get("artifact_format") == "xlsx" else ".pdf"
        dest = args.artifact_dir / f"{pref}{suffix}"
        if dest.exists() and not args.force:
            print(f"[skip] {pref} → {dest.name} already exists")
            continue
        print(f"[get ] {pref}: {url} → {dest.name}")
        try:
            download_artifact(url, dest)
            size_kb = dest.stat().st_size / 1024
            print(f"[ok  ] {pref}: {size_kb:.1f} KB")
        except Exception as exc:
            print(f"[fail] {pref}: {exc}")
            failures.append((pref, str(exc)))

    if failures:
        print("\nFailures:")
        for pref, msg in failures:
            print(f"  {pref}: {msg}")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
