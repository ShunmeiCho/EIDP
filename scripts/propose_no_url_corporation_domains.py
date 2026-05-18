"""Propose auditable corporation-domain seeds for no-url schools.

The script is read-only. It cross-checks strict-yield gap output against the
checked-in ``discovered-urls-50.csv`` evidence and proposes only corporation
roots that:

* belong to a corporation still present in ``no_url_corporation_buckets``;
* are marked ``url_type=corporation`` in the discovered URL evidence; and
* are not already present in ``corporation_domains.csv``.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any


def _read_existing_domains(path: Path) -> set[str]:
    if not path.is_file():
        return set()
    with path.open(encoding="utf-8-sig", newline="") as fh:
        return {
            str(row.get("corporation_name", "")).strip()
            for row in csv.DictReader(fh)
            if str(row.get("corporation_name", "")).strip()
        }


def _float_or_none(value: str) -> float | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _load_no_url_buckets(path: Path) -> dict[str, dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    buckets = data.get("no_url_corporation_buckets", [])
    if not isinstance(buckets, list):
        raise ValueError("gap analysis JSON does not contain a list no_url_corporation_buckets")
    out: dict[str, dict[str, Any]] = {}
    for bucket in buckets:
        if not isinstance(bucket, dict):
            continue
        corporation_name = str(bucket.get("corporation_name", "")).strip()
        if corporation_name:
            out[corporation_name] = bucket
    return out


def propose_candidates(
    *,
    gap_analysis_json: Path,
    discovered_urls_csv: Path,
    corporation_domains_csv: Path,
) -> list[dict[str, Any]]:
    no_url_buckets = _load_no_url_buckets(gap_analysis_json)
    existing_domains = _read_existing_domains(corporation_domains_csv)
    proposals: dict[tuple[str, str], dict[str, Any]] = {}

    with discovered_urls_csv.open(encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            corporation_name = str(row.get("corporation", "")).strip()
            candidate_url = str(row.get("url_candidate_1", "")).strip()
            if (
                not corporation_name
                or not candidate_url
                or corporation_name in existing_domains
                or corporation_name not in no_url_buckets
                or str(row.get("url_type", "")).strip() != "corporation"
            ):
                continue

            bucket = no_url_buckets[corporation_name]
            key = (corporation_name, candidate_url)
            if key in proposals:
                continue
            proposals[key] = {
                "corporation_name": corporation_name,
                "candidate_url": candidate_url,
                "no_url_schools": int(bucket.get("schools", 0) or 0),
                "prefectures": dict(bucket.get("prefectures", {}) or {}),
                "examples": list(bucket.get("examples", []) or [])[:5],
                "evidence_school_name": str(row.get("school_name", "")).strip(),
                "evidence_prefecture": str(row.get("prefecture", "")).strip(),
                "evidence_confidence": _float_or_none(str(row.get("confidence", ""))),
                "evidence_http_status": str(row.get("http_status", "")).strip() or None,
                "evidence_notes": str(row.get("notes", "")).strip(),
            }

    return sorted(
        proposals.values(),
        key=lambda item: (-int(item["no_url_schools"]), str(item["corporation_name"]), str(item["candidate_url"])),
    )


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("gap_analysis_json", type=Path)
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--json", action="store_true", help="Print compact JSON.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    discovered_urls_csv = args.data_dir / "url-discovery" / "discovered-urls-50.csv"
    corporation_domains_csv = args.data_dir / "url-discovery" / "corporation_domains.csv"
    proposals = propose_candidates(
        gap_analysis_json=args.gap_analysis_json,
        discovered_urls_csv=discovered_urls_csv,
        corporation_domains_csv=corporation_domains_csv,
    )

    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(proposals, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.json:
        print(json.dumps(proposals, ensure_ascii=False, sort_keys=True))
    else:
        print(f"proposals={len(proposals)}")
        for proposal in proposals:
            print(
                "{schools}\t{corp}\t{url}\tvia={school}".format(
                    schools=proposal["no_url_schools"],
                    corp=proposal["corporation_name"],
                    url=proposal["candidate_url"],
                    school=proposal["evidence_school_name"],
                )
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
