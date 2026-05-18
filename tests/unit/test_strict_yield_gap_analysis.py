from __future__ import annotations

import importlib.util
import sqlite3
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "analyze_strict_yield_gaps.py"
spec = importlib.util.spec_from_file_location("analyze_strict_yield_gaps", SCRIPT_PATH)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def _db(path: Path) -> Path:
    with sqlite3.connect(path) as conn:
        conn.executescript(
            """
            create table school (
                id integer primary key,
                school_type text,
                status text
            );
            create table school_fiscal_year_status (
                school_id integer,
                fiscal_year integer,
                url_status text,
                pdf_status text,
                extract_status text,
                excel_ready integer,
                blocking_reason text
            );
            create table document (
                id integer primary key,
                school_id integer,
                fiscal_year integer,
                pdf_type text,
                ingest_status text
            );
            create table department_yearly (
                id integer primary key,
                document_id integer,
                fiscal_year integer,
                is_current integer,
                capacity integer,
                extraction_confidence real
            );
            create table support_recipient (
                id integer primary key,
                school_id integer,
                document_id integer,
                fiscal_year integer,
                is_current integer,
                extraction_confidence real
            );
            """
        )
        conn.executemany(
            "insert into school (id, school_type, status) values (?, ?, ?)",
            [
                (1, "専門学校", "active"),
                (2, "専門学校", "active"),
                (3, "専門学校", "active"),
                (4, "大学", "active"),
                (5, "専門学校", "inactive"),
            ],
        )
        conn.executemany(
            """
            insert into school_fiscal_year_status
              (school_id, fiscal_year, url_status, pdf_status, extract_status, excel_ready, blocking_reason)
            values (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (1, 2025, "pref_url", "confirmed_target", "parsed", 1, None),
                (2, 2025, "pref_url", "confirmed_target", "manual_entered", 0, "review_required"),
                (3, 2025, "unknown", "image_pending", "ocr_pending", 0, "ocr_pending"),
                (4, 2025, "pref_url", "confirmed_target", "parsed", 1, None),
                (5, 2025, "pref_url", "confirmed_target", "parsed", 1, None),
            ],
        )
        conn.executemany(
            "insert into document (id, school_id, fiscal_year, pdf_type, ingest_status) values (?, ?, ?, ?, ?)",
            [
                (1, 1, 2025, "target", "ingested"),
                (2, 2, 2025, "target", "review_pending"),
                (3, 3, 2025, "image_only", "parse_failed"),
            ],
        )
        conn.executemany(
            """
            insert into department_yearly
              (id, document_id, fiscal_year, is_current, capacity, extraction_confidence)
            values (?, ?, ?, ?, ?, ?)
            """,
            [
                (1, 1, 2025, 1, 40, 0.94),
                (2, 2, 2025, 1, 30, 0.94),
                (3, 2, 2025, 0, 20, 0.54),
            ],
        )
        conn.executemany(
            """
            insert into support_recipient
              (id, school_id, document_id, fiscal_year, is_current, extraction_confidence)
            values (?, ?, ?, ?, ?, ?)
            """,
            [
                (1, 1, 1, 2025, 1, 0.94),
                (2, 2, 2, 2025, 0, 0.54),
                (3, 4, None, 2025, 0, 0.54),
            ],
        )
    return path


def test_analyze_database_reports_strict_broad_excel_and_reviewable_rates(tmp_path: Path) -> None:
    result = module.analyze_database(_db(tmp_path / "eidp.sqlite3"), fiscal_year=2025, school_type="専門学校")

    assert result["schools_total"] == 3
    assert result["strict_target_parsed_schools"] == 1
    assert result["strict_target_parsed_rate_pct"] == 33.3
    assert result["broad_confirmed_target_schools"] == 2
    assert result["broad_confirmed_target_rate_pct"] == 66.7
    assert result["excel_ready_schools"] == 1
    assert result["operator_reviewable_schools"] == 3
    assert result["operator_reviewable_rate_pct"] == 100.0
    assert result["estimated_manual_workload_rate_pct"] == 0.0
    assert result["non_ready_buckets"][0]["pdf_status"] == "confirmed_target"
    assert result["url_pdf_gap_buckets"][:3] == [
        {
            "url_status": "pref_url",
            "pdf_status": "confirmed_target",
            "blocking_reason": None,
            "schools": 1,
        },
        {
            "url_status": "pref_url",
            "pdf_status": "confirmed_target",
            "blocking_reason": "review_required",
            "schools": 1,
        },
        {
            "url_status": "unknown",
            "pdf_status": "image_pending",
            "blocking_reason": "ocr_pending",
            "schools": 1,
        },
    ]
    assert result["document_buckets"][0] == {
        "pdf_type": "image_only",
        "ingest_status": "parse_failed",
        "fiscal_year": 2025,
        "count": 1,
    }
    assert result["yearly_row_buckets"][:2] == [
        {
            "ingest_status": "ingested",
            "documents": 1,
            "yearly_rows": 1,
            "current_rows": 1,
            "current_rows_with_capacity": 1,
            "avg_current_confidence": 0.94,
        },
        {
            "ingest_status": "parse_failed",
            "documents": 1,
            "yearly_rows": 0,
            "current_rows": 0,
            "current_rows_with_capacity": 0,
            "avg_current_confidence": None,
        },
    ]
    assert result["low_confidence_business_row_buckets"] == [
        {
            "table": "department_yearly",
            "ingest_status": "review_pending",
            "is_current": False,
            "rows": 1,
            "schools": 1,
            "min_confidence": 0.54,
            "max_confidence": 0.54,
        },
        {
            "table": "support_recipient",
            "ingest_status": "review_pending",
            "is_current": False,
            "rows": 1,
            "schools": 1,
            "min_confidence": 0.54,
            "max_confidence": 0.54,
        },
    ]


def test_analyze_database_can_include_all_school_types(tmp_path: Path) -> None:
    result = module.analyze_database(_db(tmp_path / "eidp.sqlite3"), fiscal_year=2025, school_type=None)

    assert result["schools_total"] == 4
    assert result["strict_target_parsed_schools"] == 2
    assert result["excel_ready_schools"] == 2


def test_analyze_database_counts_discovered_candidates_as_operator_reviewable(tmp_path: Path) -> None:
    db_path = _db(tmp_path / "eidp.sqlite3")
    with sqlite3.connect(db_path) as conn:
        conn.execute("insert into school (id, school_type, status) values (?, ?, ?)", (6, "専門学校", "active"))
        conn.execute(
            """
            insert into school_fiscal_year_status
              (school_id, fiscal_year, url_status, pdf_status, extract_status, excel_ready, blocking_reason)
            values (?, ?, ?, ?, ?, ?, ?)
            """,
            (6, 2025, "pref_url", "discovered", "none", 0, "not_extracted"),
        )

    result = module.analyze_database(db_path, fiscal_year=2025, school_type="専門学校")

    assert result["schools_total"] == 4
    assert result["operator_reviewable_schools"] == 4
    assert result["estimated_manual_workload_rate_pct"] == 0.0


def test_analyze_database_can_scope_to_school_ids_file(tmp_path: Path) -> None:
    school_ids = tmp_path / "school_ids.txt"
    school_ids.write_text("# replay denominator\n1\n3\n", encoding="utf-8")

    result = module.analyze_database(
        _db(tmp_path / "eidp.sqlite3"),
        fiscal_year=2025,
        school_type="専門学校",
        school_ids=module.load_school_ids(school_ids),
    )

    assert result["school_ids_filter_count"] == 2
    assert result["schools_total"] == 2
    assert result["strict_target_parsed_schools"] == 1
    assert result["broad_confirmed_target_schools"] == 1
    assert result["operator_reviewable_schools"] == 2
    assert result["document_buckets"] == [
        {
            "pdf_type": "image_only",
            "ingest_status": "parse_failed",
            "fiscal_year": 2025,
            "count": 1,
        },
        {
            "pdf_type": "target",
            "ingest_status": "ingested",
            "fiscal_year": 2025,
            "count": 1,
        },
    ]
