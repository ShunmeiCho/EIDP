"""Analyze strict target-PDF yield gaps from an EIDP SQLite database."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

OPERATOR_REVIEWABLE_PDF_STATUSES = frozenset(
    {
        "confirmed_target",
        "discovered",
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


def _url_pdf_gap_buckets(
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
          coalesce(s.url_status, ''),
          coalesce(s.pdf_status, ''),
          coalesce(s.blocking_reason, ''),
          count(*)
        from school_fiscal_year_status s
        join school sc on sc.id = s.school_id
        where s.fiscal_year = ?
          and sc.status = 'active'
          {school_type_sql}
          {school_ids_sql}
        group by s.url_status, s.pdf_status, s.blocking_reason
        order by count(*) desc, s.url_status, s.pdf_status, s.blocking_reason
        """,
        (fiscal_year, *school_type_params, *school_ids_params),
    ).fetchall()
    return [
        {
            "url_status": str(url_status),
            "pdf_status": str(pdf_status),
            "blocking_reason": str(blocking_reason) or None,
            "schools": int(count),
        }
        for url_status, pdf_status, blocking_reason, count in rows
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


def _source_host(source_url: str) -> str:
    if not source_url:
        return ""
    return urlparse(source_url).netloc.lower()


def _school_mismatch_source_buckets(
    conn: sqlite3.Connection,
    *,
    fiscal_year: int,
    school_type: str | None,
    school_ids: set[int] | None,
) -> list[dict[str, Any]]:
    school_type_sql, school_type_params = _school_type_clause(school_type)
    school_ids_sql, school_ids_params = _school_ids_clause("d.school_id", school_ids)
    rows = conn.execute(
        f"""
        select
          d.id,
          d.school_id,
          coalesce(sc.school_name, ''),
          coalesce(d.source_url, '')
        from document d
        join school sc on sc.id = d.school_id
        where d.fiscal_year = ?
          and d.ingest_status = 'school_mismatch'
          and sc.status = 'active'
          {school_type_sql}
          {school_ids_sql}
        order by d.school_id, d.id
        """,
        (fiscal_year, *school_type_params, *school_ids_params),
    ).fetchall()

    grouped: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"documents": 0, "school_ids": set(), "examples": []}
    )
    for doc_id, school_id, school_name, source_url in rows:
        source_host = _source_host(str(source_url)) or "unknown"
        bucket = grouped[source_host]
        bucket["documents"] += 1
        bucket["school_ids"].add(int(school_id))
        examples = bucket["examples"]
        if len(examples) < 5:
            examples.append(
                {
                    "doc_id": int(doc_id),
                    "school_id": int(school_id),
                    "school_name": str(school_name),
                    "source_url": str(source_url),
                }
            )

    return [
        {
            "source_host": source_host,
            "documents": int(bucket["documents"]),
            "schools": len(bucket["school_ids"]),
            "examples": bucket["examples"],
        }
        for source_host, bucket in sorted(
            grouped.items(),
            key=lambda item: (-int(item[1]["documents"]), item[0]),
        )
    ]


def _site_source_gap_buckets(
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
          s.school_id,
          coalesce(sc.school_name, ''),
          coalesce(s.url_status, ''),
          coalesce(s.pdf_status, ''),
          coalesce(s.blocking_reason, ''),
          coalesce(ss.url, '')
        from school_fiscal_year_status s
        join school sc on sc.id = s.school_id
        left join school_site ss on ss.school_id = s.school_id
        where s.fiscal_year = ?
          and sc.status = 'active'
          and case when s.excel_ready then 1 else 0 end = 0
          {school_type_sql}
          {school_ids_sql}
        order by s.school_id
        """,
        (fiscal_year, *school_type_params, *school_ids_params),
    ).fetchall()

    grouped: dict[tuple[str, str, str, str], dict[str, Any]] = defaultdict(
        lambda: {"school_ids": set(), "examples": []}
    )
    seen_school_host_keys: set[tuple[str, str, str, str, int]] = set()
    for school_id, school_name, url_status, pdf_status, blocking_reason, site_url in rows:
        source_host = _source_host(str(site_url)) or "no_site"
        key = (str(url_status), str(pdf_status), str(blocking_reason), source_host)
        dedupe_key = (*key, int(school_id))
        if dedupe_key in seen_school_host_keys:
            continue
        seen_school_host_keys.add(dedupe_key)

        bucket = grouped[key]
        bucket["school_ids"].add(int(school_id))
        examples = bucket["examples"]
        if len(examples) < 5:
            examples.append(
                {
                    "school_id": int(school_id),
                    "school_name": str(school_name),
                    "site_url": str(site_url),
                }
            )

    return [
        {
            "url_status": url_status,
            "pdf_status": pdf_status,
            "blocking_reason": blocking_reason or None,
            "source_host": source_host,
            "schools": len(bucket["school_ids"]),
            "examples": bucket["examples"],
        }
        for (url_status, pdf_status, blocking_reason, source_host), bucket in sorted(
            grouped.items(),
            key=lambda item: (-len(item[1]["school_ids"]), item[0]),
        )
    ]


def _no_url_corporation_buckets(
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
          s.school_id,
          coalesce(sc.prefecture, ''),
          coalesce(sc.corporation_name, ''),
          coalesce(sc.school_name, '')
        from school_fiscal_year_status s
        join school sc on sc.id = s.school_id
        where s.fiscal_year = ?
          and sc.status = 'active'
          and s.url_status = 'no_url'
          and s.pdf_status = 'none'
          and s.blocking_reason = 'no_url'
          {school_type_sql}
          {school_ids_sql}
        order by sc.corporation_name, sc.prefecture, s.school_id
        """,
        (fiscal_year, *school_type_params, *school_ids_params),
    ).fetchall()

    grouped: dict[str, dict[str, Any]] = defaultdict(lambda: {"prefectures": defaultdict(int), "examples": []})
    for school_id, prefecture, corporation_name, school_name in rows:
        corp = str(corporation_name) or "unknown"
        bucket = grouped[corp]
        bucket["prefectures"][str(prefecture)] += 1
        examples = bucket["examples"]
        if len(examples) < 5:
            examples.append(
                {
                    "school_id": int(school_id),
                    "prefecture": str(prefecture),
                    "school_name": str(school_name),
                }
            )

    return [
        {
            "corporation_name": corporation_name,
            "schools": sum(int(count) for count in bucket["prefectures"].values()),
            "prefectures": dict(
                sorted(
                    bucket["prefectures"].items(),
                    key=lambda item: (-int(item[1]), item[0]),
                )
            ),
            "examples": bucket["examples"],
        }
        for corporation_name, bucket in sorted(
            grouped.items(),
            key=lambda item: (-sum(int(count) for count in item[1]["prefectures"].values()), item[0]),
        )
    ]


def _yearly_row_buckets(
    conn: sqlite3.Connection,
    *,
    fiscal_year: int,
    school_type: str | None,
    school_ids: set[int] | None,
) -> list[dict[str, Any]]:
    school_type_sql, school_type_params = _school_type_clause(school_type)
    school_ids_sql, school_ids_params = _school_ids_clause("d.school_id", school_ids)
    rows = conn.execute(
        f"""
        select
          coalesce(d.ingest_status, ''),
          count(distinct d.id),
          count(dy.id),
          sum(case when dy.is_current then 1 else 0 end),
          sum(case when dy.is_current and dy.capacity is not null then 1 else 0 end),
          round(avg(case when dy.is_current then dy.extraction_confidence end), 3)
        from document d
        join school sc on sc.id = d.school_id
        left join department_yearly dy on dy.document_id = d.id
        where d.fiscal_year = ?
          and sc.status = 'active'
          {school_type_sql}
          {school_ids_sql}
        group by d.ingest_status
        order by count(distinct d.id) desc, d.ingest_status
        """,
        (fiscal_year, *school_type_params, *school_ids_params),
    ).fetchall()
    return [
        {
            "ingest_status": str(ingest_status),
            "documents": int(documents),
            "yearly_rows": int(yearly_rows),
            "current_rows": int(current_rows or 0),
            "current_rows_with_capacity": int(current_rows_with_capacity or 0),
            "avg_current_confidence": float(avg_current_confidence) if avg_current_confidence is not None else None,
        }
        for (
            ingest_status,
            documents,
            yearly_rows,
            current_rows,
            current_rows_with_capacity,
            avg_current_confidence,
        ) in rows
    ]


def _low_confidence_business_row_buckets(
    conn: sqlite3.Connection,
    *,
    fiscal_year: int,
    school_type: str | None,
    school_ids: set[int] | None,
    min_confidence: float = 0.70,
) -> list[dict[str, Any]]:
    school_type_sql, school_type_params = _school_type_clause(school_type)
    dy_school_ids_sql, dy_school_ids_params = _school_ids_clause("d.school_id", school_ids)
    sr_school_ids_sql, sr_school_ids_params = _school_ids_clause("sr.school_id", school_ids)

    rows = conn.execute(
        f"""
        select
          'department_yearly' as table_name,
          coalesce(d.ingest_status, '') as ingest_status,
          case when dy.is_current then 1 else 0 end as is_current,
          count(*) as row_count,
          count(distinct d.school_id) as school_count,
          round(min(dy.extraction_confidence), 3) as min_confidence,
          round(max(dy.extraction_confidence), 3) as max_confidence
        from department_yearly dy
        join document d on d.id = dy.document_id
        join school sc on sc.id = d.school_id
        where dy.fiscal_year = ?
          and sc.status = 'active'
          and dy.extraction_confidence is not null
          and dy.extraction_confidence < ?
          {school_type_sql}
          {dy_school_ids_sql}
        group by d.ingest_status, dy.is_current
        union all
        select
          'support_recipient' as table_name,
          coalesce(d.ingest_status, '') as ingest_status,
          case when sr.is_current then 1 else 0 end as is_current,
          count(*) as row_count,
          count(distinct sr.school_id) as school_count,
          round(min(sr.extraction_confidence), 3) as min_confidence,
          round(max(sr.extraction_confidence), 3) as max_confidence
        from support_recipient sr
        left join document d on d.id = sr.document_id
        join school sc on sc.id = sr.school_id
        where sr.fiscal_year = ?
          and sc.status = 'active'
          and sr.extraction_confidence is not null
          and sr.extraction_confidence < ?
          {school_type_sql}
          {sr_school_ids_sql}
        group by d.ingest_status, sr.is_current
        order by table_name, row_count desc, ingest_status, is_current
        """,
        (
            fiscal_year,
            min_confidence,
            *school_type_params,
            *dy_school_ids_params,
            fiscal_year,
            min_confidence,
            *school_type_params,
            *sr_school_ids_params,
        ),
    ).fetchall()
    return [
        {
            "table": str(table_name),
            "ingest_status": str(ingest_status) or None,
            "is_current": bool(is_current),
            "rows": int(row_count),
            "schools": int(school_count),
            "min_confidence": float(row_min_confidence) if row_min_confidence is not None else None,
            "max_confidence": float(row_max_confidence) if row_max_confidence is not None else None,
        }
        for (
            table_name,
            ingest_status,
            is_current,
            row_count,
            school_count,
            row_min_confidence,
            row_max_confidence,
        ) in rows
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
        url_pdf_gap_buckets = _url_pdf_gap_buckets(
            conn,
            fiscal_year=fiscal_year,
            school_type=school_type,
            school_ids=school_ids,
        )
        document_buckets = _document_buckets(conn, fiscal_year=fiscal_year, school_ids=school_ids)
        school_mismatch_source_buckets = _school_mismatch_source_buckets(
            conn,
            fiscal_year=fiscal_year,
            school_type=school_type,
            school_ids=school_ids,
        )
        site_source_gap_buckets = _site_source_gap_buckets(
            conn,
            fiscal_year=fiscal_year,
            school_type=school_type,
            school_ids=school_ids,
        )
        no_url_corporation_buckets = _no_url_corporation_buckets(
            conn,
            fiscal_year=fiscal_year,
            school_type=school_type,
            school_ids=school_ids,
        )
        yearly_row_buckets = _yearly_row_buckets(
            conn,
            fiscal_year=fiscal_year,
            school_type=school_type,
            school_ids=school_ids,
        )
        low_confidence_business_row_buckets = _low_confidence_business_row_buckets(
            conn,
            fiscal_year=fiscal_year,
            school_type=school_type,
            school_ids=school_ids,
        )

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
        "finished_at": datetime.now(UTC).isoformat(),
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
        "url_pdf_gap_buckets": url_pdf_gap_buckets,
        "school_mismatch_source_buckets": school_mismatch_source_buckets,
        "site_source_gap_buckets": site_source_gap_buckets,
        "no_url_corporation_buckets": no_url_corporation_buckets,
        "non_ready_buckets": non_ready_buckets,
        "document_buckets": document_buckets,
        "yearly_row_buckets": yearly_row_buckets,
        "low_confidence_business_row_buckets": low_confidence_business_row_buckets,
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
