"""Summarize strict-yield RCA evidence from a Stage 6 evidence ZIP.

The tool is read-only. It does not extract files to disk and does not touch the
EIDP database. Use it to turn a Stage 6 evidence bundle into an owner-facing
strict-yield action summary.
"""

from __future__ import annotations

import argparse
import json
import sys
import zipfile
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parent))

from verify_stage6_evidence import verify_stage6_evidence_bundle

REQUIRED_RCA_LABELS = (
    "build_info",
    "diagnostics",
    "last_run",
    "discovery_evidence",
    "discovery_rca",
)

BUCKET_ORDER = {
    "publication_lag_or_old_target_pdf": 0,
    "target_form_without_year_evidence": 1,
    "school_identity_mismatch": 2,
    "non_target_candidates_only": 3,
}

BUCKET_INTERPRETATIONS = {
    "publication_lag_or_old_target_pdf": (
        "Current-FY strict success cannot rise without newly published target evidence "
        "or an approved publication-lag exception."
    ),
    "target_form_without_year_evidence": (
        "Target-form-like candidates exist, but machine-verifiable target-year evidence is insufficient."
    ),
    "school_identity_mismatch": (
        "Candidate evidence may belong to a sibling or corporate site; school identity must be confirmed."
    ),
    "non_target_candidates_only": (
        "Official site was reached, but only non-target candidates were found."
    ),
}


def _rate(count: int, denominator: int) -> float | None:
    return round(count / denominator * 100.0, 1) if denominator else None


def _entry_by_suffix(names: list[str], suffix: str) -> str:
    matches = sorted(name for name in names if name.replace("\\", "/").endswith(suffix))
    if not matches:
        raise ValueError(f"archive is missing an entry ending with {suffix!r}")
    if len(matches) > 1:
        raise ValueError(f"archive has multiple entries ending with {suffix!r}: {matches}")
    return matches[0]


def _load_json_entry(zf: zipfile.ZipFile, name: str) -> dict[str, Any]:
    payload = json.loads(zf.read(name).decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{name} must contain a JSON object")
    return payload


def _load_jsonl_entry(zf: zipfile.ZipFile, name: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(zf.read(name).decode("utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        payload = json.loads(line)
        if not isinstance(payload, dict):
            raise ValueError(f"{name}:{line_number} must contain a JSON object")
        rows.append(payload)
    return rows


def _as_int(value: object, default: int = 0) -> int:
    return value if isinstance(value, int) else default


def _as_float(value: object) -> float | None:
    return float(value) if isinstance(value, int | float) else None


def _first_registered_source(packet: dict[str, Any]) -> str:
    official_index_url = packet.get("official_index_url")
    if isinstance(official_index_url, str) and official_index_url:
        return official_index_url
    registered_sites = packet.get("registered_sites")
    if isinstance(registered_sites, list):
        for site in registered_sites:
            if isinstance(site, dict) and isinstance(site.get("url"), str) and site["url"]:
                return str(site["url"])
    return ""


def _bucket_sort_key(bucket: dict[str, Any]) -> tuple[int, str]:
    name = str(bucket["bucket"])
    return BUCKET_ORDER.get(name, 100), name


def _school_queue_sort_key(row: dict[str, Any]) -> tuple[int, int, int]:
    return (
        BUCKET_ORDER.get(str(row["bucket"]), 100),
        -_as_int(row["candidate_rows"]),
        _as_int(row["school_id"]),
    )


def summarize_stage6_rca_bundle(
    archive: Path,
    *,
    required_yield_pct: float = 60.0,
) -> dict[str, Any]:
    """Return a strict-yield RCA summary for a Stage 6 evidence ZIP."""

    verification = verify_stage6_evidence_bundle(archive, required_labels=REQUIRED_RCA_LABELS)
    errors: list[str] = []
    source_files: dict[str, str] = {}

    try:
        with zipfile.ZipFile(archive) as zf:
            names = zf.namelist()
            last_run_name = _entry_by_suffix(names, "data/output/last_run.json")
            rejections_name = _entry_by_suffix(names, "-discovery-rejections.jsonl")
            rca_name = _entry_by_suffix(names, "-discovery-rca-batch-plan.json")
            source_files = {
                "last_run": last_run_name,
                "discovery_evidence": rejections_name,
                "discovery_rca": rca_name,
            }

            last_run = _load_json_entry(zf, last_run_name)
            rca = _load_json_entry(zf, rca_name)
            rejection_rows = _load_jsonl_entry(zf, rejections_name)
    except (OSError, zipfile.BadZipFile, json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
        errors.append(str(exc))
        return {
            "ok": False,
            "basis": "stage6_strict_yield_rca_summary",
            "generated_at": datetime.now(UTC).isoformat(),
            "archive": str(archive),
            "verification": verification,
            "source_files": source_files,
            "errors": errors,
        }

    discovery_stats = last_run.get("discovery_stats") if isinstance(last_run.get("discovery_stats"), dict) else {}
    ingest_stats = last_run.get("ingest_stats") if isinstance(last_run.get("ingest_stats"), dict) else {}

    denominator = _as_int(last_run.get("target_pdf_auto_denominator_count"))
    excel_ready_count = _as_int(last_run.get("target_pdf_excel_ready_acquired_count"))
    excel_ready_yield_pct = _as_float(last_run.get("target_pdf_excel_ready_yield_pct"))
    if excel_ready_yield_pct is None:
        excel_ready_yield_pct = _rate(excel_ready_count, denominator)

    ship_gate_status = str(last_run.get("ship_gate_status") or "")
    ship_gate_met = (
        excel_ready_yield_pct is not None
        and excel_ready_yield_pct >= required_yield_pct
        and ship_gate_status not in {"below_gate", "failed", "fail"}
    )

    rca_items = rca.get("items")
    if not isinstance(rca_items, list):
        errors.append("discovery RCA batch plan must contain an items list")
        rca_items = []

    bucket_accumulator: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"bucket": "", "schools": 0, "candidate_rows": 0, "actionable_candidate_rows": 0}
    )
    school_queue: list[dict[str, Any]] = []
    for item in rca_items:
        if not isinstance(item, dict):
            continue
        bucket_name = str(item.get("bucket") or "unknown")
        candidate_count = _as_int(item.get("candidate_count"))
        actionable_candidate_count = _as_int(item.get("actionable_candidate_count"))
        bucket = bucket_accumulator[bucket_name]
        bucket["bucket"] = bucket_name
        bucket["schools"] += 1
        bucket["candidate_rows"] += candidate_count
        bucket["actionable_candidate_rows"] += actionable_candidate_count

        packet = item.get("packet")
        if isinstance(packet, dict):
            school_queue.append(
                {
                    "school_id": _as_int(packet.get("school_id")),
                    "school_name": str(packet.get("school_name") or ""),
                    "prefecture": str(packet.get("prefecture") or ""),
                    "bucket": bucket_name,
                    "candidate_rows": candidate_count,
                    "actionable_candidate_rows": actionable_candidate_count,
                    "registered_source": _first_registered_source(packet),
                }
            )

    bucket_summary = sorted(bucket_accumulator.values(), key=_bucket_sort_key)
    for bucket in bucket_summary:
        bucket["interpretation"] = BUCKET_INTERPRETATIONS.get(str(bucket["bucket"]), "")

    reason_counts = Counter(str(row.get("reason") or "unknown") for row in rejection_rows)

    summary: dict[str, Any] = {
        "ok": verification.get("ok") is True and not errors,
        "basis": "stage6_strict_yield_rca_summary",
        "generated_at": datetime.now(UTC).isoformat(),
        "archive": str(archive),
        "verification": verification,
        "source_files": source_files,
        "strict_yield": {
            "target_fiscal_year": last_run.get("current_fy") or rca.get("target_fiscal_year"),
            "denominator": denominator,
            "excel_ready_acquired_count": excel_ready_count,
            "excel_ready_yield_pct": excel_ready_yield_pct,
            "required_yield_pct": required_yield_pct,
            "ship_gate_status": ship_gate_status,
            "ship_gate_met": ship_gate_met,
            "conclusion": "PASS" if ship_gate_met else "BELOW_GATE",
            "operator_reviewable_count": _as_int(last_run.get("operator_reviewable_count")),
            "operator_reviewable_yield_pct": _as_float(last_run.get("operator_reviewable_yield_pct")),
        },
        "run_counters": {
            "crawled": _as_int(discovery_stats.get("crawled")),
            "found": _as_int(discovery_stats.get("found")),
            "downloaded": _as_int(discovery_stats.get("downloaded")),
            "processed": _as_int(ingest_stats.get("processed")),
            "departments_created": _as_int(ingest_stats.get("departments_created")),
            "yearly_upserted": _as_int(ingest_stats.get("yearly_upserted")),
        },
        "rca_batch": {
            "item_count": len(rca_items),
            "root_total_candidates": _as_int(rca.get("total_candidates")),
            "candidate_rows": sum(_as_int(item.get("candidate_count")) for item in rca_items if isinstance(item, dict)),
            "actionable_candidate_rows": sum(
                _as_int(item.get("actionable_candidate_count")) for item in rca_items if isinstance(item, dict)
            ),
            "bucket_summary": bucket_summary,
        },
        "rejection_reasons": [
            {"reason": reason, "count": count}
            for reason, count in sorted(reason_counts.items(), key=lambda item: (-item[1], item[0]))
        ],
        "school_queue": sorted(school_queue, key=_school_queue_sort_key),
        "errors": errors,
    }
    return summary


def _md_cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def render_markdown(summary: dict[str, Any]) -> str:
    strict_yield = summary.get("strict_yield", {})
    rca_batch = summary.get("rca_batch", {})
    run_counters = summary.get("run_counters", {})

    lines = [
        "# Stage 6 Strict-Yield RCA Summary",
        "",
        f"Archive: `{summary.get('archive', '')}`",
        "",
    ]
    if summary.get("ok") is not True:
        lines.extend(["Status: `INVALID_OR_INCOMPLETE_EVIDENCE`", ""])
    else:
        lines.extend(
            [
                f"Status: `{strict_yield.get('conclusion')}` (`{strict_yield.get('ship_gate_status')}`)",
                (
                    "Strict Excel-ready yield: "
                    f"`{strict_yield.get('excel_ready_acquired_count')}/{strict_yield.get('denominator')}` "
                    f"(`{strict_yield.get('excel_ready_yield_pct')}%`), "
                    f"required `{strict_yield.get('required_yield_pct')}%`."
                ),
                (
                    "Operator-reviewable coverage: "
                    f"`{strict_yield.get('operator_reviewable_count')}` "
                    f"(`{strict_yield.get('operator_reviewable_yield_pct')}%`)."
                ),
                "",
            ]
        )

    lines.extend(
        [
            "## Run Counters",
            "",
            "| Counter | Value |",
            "| --- | ---: |",
        ]
    )
    for key in ("crawled", "found", "downloaded", "processed", "departments_created", "yearly_upserted"):
        lines.append(f"| `{key}` | {_md_cell(run_counters.get(key, 0))} |")

    lines.extend(
        [
            "",
            "## RCA Batch",
            "",
            (
                f"School packets: `{rca_batch.get('item_count', 0)}`; "
                f"candidate rows: `{rca_batch.get('candidate_rows', 0)}`; "
                f"root `total_candidates`: `{rca_batch.get('root_total_candidates', 0)}`."
            ),
            "",
            "| Bucket | Schools | Candidate rows | Interpretation |",
            "| --- | ---: | ---: | --- |",
        ]
    )
    for bucket in rca_batch.get("bucket_summary", []):
        lines.append(
            "| "
            f"`{_md_cell(bucket.get('bucket', ''))}` | "
            f"{_md_cell(bucket.get('schools', 0))} | "
            f"{_md_cell(bucket.get('candidate_rows', 0))} | "
            f"{_md_cell(bucket.get('interpretation', ''))} |"
        )

    lines.extend(["", "## Rejection Reasons", "", "| Reason | Count |", "| --- | ---: |"])
    for reason in summary.get("rejection_reasons", [])[:20]:
        lines.append(f"| `{_md_cell(reason.get('reason', ''))}` | {_md_cell(reason.get('count', 0))} |")

    lines.extend(
        [
            "",
            "## School Queue",
            "",
            "| School ID | School | Bucket | Candidate rows | Registered source |",
            "| ---: | --- | --- | ---: | --- |",
        ]
    )
    for row in summary.get("school_queue", []):
        lines.append(
            "| "
            f"{_md_cell(row.get('school_id', 0))} | "
            f"{_md_cell(row.get('school_name', ''))} | "
            f"`{_md_cell(row.get('bucket', ''))}` | "
            f"{_md_cell(row.get('candidate_rows', 0))} | "
            f"`{_md_cell(row.get('registered_source', ''))}` |"
        )

    if summary.get("errors"):
        lines.extend(["", "## Errors", ""])
        lines.extend(f"- `{_md_cell(error)}`" for error in summary["errors"])

    return "\n".join(lines) + "\n"


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path, help="Path to logs/stage6-evidence-*.zip.")
    parser.add_argument("--required-yield-pct", type=float, default=60.0)
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--json", action="store_true", help="Alias for --format json.")
    parser.add_argument("--output", type=Path, help="Write the summary to this path.")
    parser.add_argument(
        "--fail-on-below-gate",
        action="store_true",
        help="Return exit code 1 when parsed evidence is below the strict-yield gate.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    output_format = "json" if args.json else args.format
    summary = summarize_stage6_rca_bundle(args.archive, required_yield_pct=args.required_yield_pct)
    if output_format == "json":
        rendered = json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    else:
        rendered = render_markdown(summary)

    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")

    if summary.get("ok") is not True:
        return 1
    if args.fail_on_below_gate and summary.get("strict_yield", {}).get("ship_gate_met") is not True:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
