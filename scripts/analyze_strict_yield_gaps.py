"""Analyze strict target-PDF yield gaps from an EIDP SQLite database."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

OPERATOR_REVIEWABLE_PDF_STATUSES = frozenset(
    {
        "confirmed_target",
        "publication_lag",
        "target_year_unverified",
        "image_pending",
    }
)


def _rate(count: int, total: int) -> float | None:
    return round(count / total * 100.0, 1) if total else None


def _connect_readonly(path: Path) -> sqlite3.Connection:
    if not path.is_file():
        raise FileNotFoundError(f"database does not exist: {path}")
    return sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)


def _school_type_clause(school_type: str | None) -> tuple[str, tuple[object, ...]]:
    if school_type is None:
        return "", ()
    return " and sc.school_type = ?", (school_type,)


def _school_ids_clause(column: str, school_ids: set[int] | None) -> tuple[str, tuple[object, ...]]:
    if school_ids is None:
        return "", ()
    if not school_ids:
        return " and 1 = 0", ()
    placeholders = ", ".join("?" for _ in school_ids)
    return f" and {column} in ({placeholders})", tuple(sorted(school_ids))


def load_school_ids(path: Path) -> set[int]:
    ids: set[int] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if not text or text.startswith("#"):
            continue
        try:
            ids.add(int(text))
        except ValueError as exc:
            raise ValueError(f"school id file contains a non-integer line: {text!r}") from exc
    return ids


def _status_buckets(
    conn: sqlite3.Connection,
    *,
    fiscal_year: int,
    school_type: str | None,
    school_ids: set[int] | None,
) -> list[dict[str, Any]]:
    school_type_sql, school_type_params = _school_type_clause(school_type)
    school_ids_sql, school_ids_params = _school_ids_clause("s.school_id", school_ids)
    rows = conn.execute(
        f"""
        select
          coalesce(s.pdf_status, ''),
          coalesce(s.extract_status, ''),
          case when s.excel_ready then 1 else 0 end,
          coalesce(s.blocking_reason, ''),
          count(*)
        from school_fiscal_year_status s
        join school sc on sc.id = s.school_id
        where s.fiscal_year = ?
          and sc.status = 'active'
          {school_type_sql}
          {school_ids_sql}
        group by s.pdf_status, s.extract_status, s.excel_ready, s.blocking_reason
        order by count(*) desc, s.pdf_status, s.extract_status, s.blocking_reason
        """,
        (fiscal_year, *school_type_params, *school_ids_params),
    ).fetchall()
    return [
        {
            "pdf_status": str(pdf_status),
            "extract_status": str(extract_status),
            "excel_ready": bool(excel_ready),
            "blocking_reason": str(blocking_reason) or None,
            "count": int(count),
        }
        for pdf_status, extract_status, excel_ready, blocking_reason, count in rows
    ]


def _document_buckets(
    conn: sqlite3.Connection,
    *,
    fiscal_year: int,
    school_ids: set[int] | None,
) -> list[dict[str, Any]]:
    school_ids_sql, school_ids_params = _school_ids_clause("school_id", school_ids)
    rows = conn.execute(
        f"""
        select
          coalesce(pdf_type, ''),
          coalesce(ingest_status, ''),
          fiscal_year,
          count(*)
        from document
        where fiscal_year = ?
        {school_ids_sql}
        group by pdf_type, ingest_status, fiscal_year
        order by count(*) desc, pdf_type, ingest_status
        """,
        (fiscal_year, *school_ids_params),
    ).fetchall()
    return [
        {
            "pdf_type": str(pdf_type),
            "ingest_status": str(ingest_status),
            "fiscal_year": int(row_fiscal_year),
            "count": int(count),
        }
        for pdf_type, ingest_status, row_fiscal_year, count in rows
    ]


def analyze_database(
    database: Path,
    *,
    fiscal_year: int,
    school_type: str | None = "専門学校",
    school_ids: set[int] | None = None,
) -> dict[str, Any]:
    with _connect_readonly(database) as conn:
        status_buckets = _status_buckets(
            conn,
            fiscal_year=fiscal_year,
            school_type=school_type,
            school_ids=school_ids,
        )
        document_buckets = _document_buckets(conn, fiscal_year=fiscal_year, school_ids=school_ids)

    total = sum(bucket["count"] for bucket in status_buckets)
    strict = sum(
        bucket["count"]
        for bucket in status_buckets
        if bucket["pdf_status"] == "confirmed_target" and bucket["extract_status"] == "parsed"
    )
    broad = sum(bucket["count"] for bucket in status_buckets if bucket["pdf_status"] == "confirmed_target")
    excel_ready = sum(bucket["count"] for bucket in status_buckets if bucket["excel_ready"])
    operator_reviewable = sum(
        bucket["count"] for bucket in status_buckets if bucket["pdf_status"] in OPERATOR_REVIEWABLE_PDF_STATUSES
    )
    non_ready_buckets = [bucket for bucket in status_buckets if not bucket["excel_ready"]]

    return {
        "basis": "strict_yield_gap_analysis",
        "database": str(database),
        "fiscal_year": fiscal_year,
        "school_type": school_type,
        "school_ids_filter_count": len(school_ids) if school_ids is not None else None,
        "schools_total": total,
        "strict_target_parsed_schools": strict,
        "strict_target_parsed_rate_pct": _rate(strict, total),
        "broad_confirmed_target_schools": broad,
        "broad_confirmed_target_rate_pct": _rate(broad, total),
        "excel_ready_schools": excel_ready,
        "excel_ready_rate_pct": _rate(excel_ready, total),
        "operator_reviewable_schools": operator_reviewable,
        "operator_reviewable_rate_pct": _rate(operator_reviewable, total),
        "estimated_manual_workload_rate_pct": (
            round(100.0 - (operator_reviewable / total * 100.0), 1) if total else None
        ),
        "status_buckets": status_buckets,
        "non_ready_buckets": non_ready_buckets,
        "document_buckets": document_buckets,
    }


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database", type=Path, help="Path to data/eidp.sqlite3 or a replay DB copy.")
    parser.add_argument("--fiscal-year", type=int, required=True)
    parser.add_argument("--school-type", default="専門学校", help="School type filter; use ALL to include all types.")
    parser.add_argument("--school-ids-file", type=Path, help="Optional newline-delimited school-id scope file.")
    parser.add_argument("--output", type=Path, help="Write JSON output to this path.")
    parser.add_argument("--json", action="store_true", help="Print compact JSON instead of a readable summary.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    school_type = None if args.school_type == "ALL" else str(args.school_type)
    school_ids = load_school_ids(args.school_ids_file) if args.school_ids_file is not None else None
    result = analyze_database(
        args.database,
        fiscal_year=args.fiscal_year,
        school_type=school_type,
        school_ids=school_ids,
    )

    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.json:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    else:
        print(
            "strict={strict}/{total} ({strict_rate}%) broad={broad}/{total} ({broad_rate}%) "
            "excel_ready={excel}/{total} ({excel_rate}%) operator_reviewable={review}/{total} ({review_rate}%)".format(
                strict=result["strict_target_parsed_schools"],
                total=result["schools_total"],
                strict_rate=result["strict_target_parsed_rate_pct"],
                broad=result["broad_confirmed_target_schools"],
                broad_rate=result["broad_confirmed_target_rate_pct"],
                excel=result["excel_ready_schools"],
                excel_rate=result["excel_ready_rate_pct"],
                review=result["operator_reviewable_schools"],
                review_rate=result["operator_reviewable_rate_pct"],
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
