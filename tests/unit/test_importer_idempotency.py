"""Sprint 8.2.2 — re-import idempotency for SR import path.

After 8.2.1 the import_taisho_hiritu path became append-only, but missed
the equality short-circuit that import_sairoku already had. A re-import
of identical 対象比率 content would silently churn revisions:
rev 1 -> demoted, rev 2 -> current with the same values. This commit's
fix makes the second import a no-op when the prior current row already
matches; this test pins that contract.
"""

from __future__ import annotations

from pathlib import Path

import openpyxl
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from eidp.db.models import Department, DepartmentYearly, School, SupportRecipient
from eidp.db.sqlite_bootstrap import bootstrap_sqlite
from eidp.excel.importer import (
    SAIROKU_YEARS,
    YEAR_BLOCK_FIELDS_NO_BIKO,
    YEAR_BLOCK_FIELDS_WITH_BIKO,
    SchoolResolver,
    _parse_fiscal_year,
    import_gakka,
    import_taisho_hiritu,
)


@pytest.fixture()
def engine(tmp_path: Path):
    db_path = tmp_path / "import_idempotency.sqlite3"
    engine = create_engine(f"sqlite:///{db_path}", future=True)
    bootstrap_sqlite(engine)
    yield engine
    engine.dispose()


def _build_taisho_hiritu_ws(rows: list[dict]) -> openpyxl.worksheet.worksheet.Worksheet:
    """Build a 22-column 対象比率 sheet from a list of row dicts."""
    wb = openpyxl.Workbook()
    ws = wb.active
    headers = [
        "番号", "年度", "学校番号", "都道府県", "法人名", "学校名",
        "前年在籍", "前半期", "第I区分", "第II区分", "第III区分", "第IV区分",
        "後半期", "第I区分", "第II区分", "第III区分", "第IV区分",
        "年間", "家計急変多子世帯", "総計", "備考", "受給比率",
    ]
    ws.append(headers)
    for r in rows:
        ws.append([
            r.get("number", 1),
            r["year"],
            r.get("school_number", ""),
            r["prefecture"],
            r["corp"],
            r["school"],
            r.get("prev_enrollment"),
            r.get("first_half_total"),
            r.get("first_half_cat1"),
            r.get("first_half_cat2"),
            r.get("first_half_cat3"),
            r.get("first_half_cat4"),
            r.get("second_half_total"),
            r.get("second_half_cat1"),
            r.get("second_half_cat2"),
            r.get("second_half_cat3"),
            r.get("second_half_cat4"),
            r.get("annual_total"),
            r.get("household_change"),
            r.get("grand_total"),
            r.get("notes", ""),
            r.get("recipient_rate"),
        ])
    return ws


def _build_gakka_ws(rows: list[dict]) -> openpyxl.worksheet.worksheet.Worksheet:
    wb = openpyxl.Workbook()
    ws = wb.active
    total_columns = 7 + sum(10 if year == 2019 else 11 for year in SAIROKU_YEARS)
    ws.append([""] * total_columns)
    ws.append([""] * total_columns)
    for r in rows:
        row = [
            r["prefecture"],
            r["corp"],
            r["school"],
            r.get("course_name", "専門課程"),
            r["department"],
            r.get("day_night", "昼"),
            r.get("duration", 2),
        ]
        for year in SAIROKU_YEARS:
            fields = YEAR_BLOCK_FIELDS_NO_BIKO if year == 2019 else YEAR_BLOCK_FIELDS_WITH_BIKO
            if year == r["year"]:
                row.extend(r.get(field) for field in fields)
            else:
                row.extend([None] * len(fields))
        ws.append(row)
    return ws


def test_taisho_hiritu_reimport_with_identical_content_does_not_churn(engine):
    with Session(engine) as session:
        school = School(
            prefecture="東京都",
            corporation_name="テスト法人",
            school_name="テスト専門学校",
            school_type="専門学校",
            status="active",
        )
        session.add(school)
        session.commit()

        resolver = SchoolResolver(session)
        resolver.build()
        ws = _build_taisho_hiritu_ws([
            {
                "year": "令和7年度",
                "prefecture": "東京都",
                "corp": "テスト法人",
                "school": "テスト専門学校",
                "first_half_total": 50,
                "annual_total": 100,
                "grand_total": 100,
            },
        ])

        import_taisho_hiritu(ws, session, resolver)
        session.commit()

        import_taisho_hiritu(ws, session, resolver)
        session.commit()

        rows = (
            session.query(SupportRecipient)
            .filter(SupportRecipient.school_id == school.id)
            .all()
        )
        assert len(rows) == 1, (
            f"identical re-import must be a no-op, got {len(rows)} revisions: "
            f"{[(r.revision, r.is_current) for r in rows]}"
        )
        assert rows[0].revision == 1
        assert rows[0].is_current is True


def test_taisho_hiritu_reimport_with_changed_content_creates_revision_2(engine):
    """Sanity check the other side: when content actually changes, the
    append-only path still kicks in."""
    with Session(engine) as session:
        school = School(
            prefecture="東京都",
            corporation_name="テスト法人",
            school_name="テスト専門学校",
            school_type="専門学校",
            status="active",
        )
        session.add(school)
        session.commit()

        resolver = SchoolResolver(session)
        resolver.build()

        ws_v1 = _build_taisho_hiritu_ws([
            {"year": "令和7年度", "prefecture": "東京都",
             "corp": "テスト法人", "school": "テスト専門学校",
             "annual_total": 100, "grand_total": 100},
        ])
        import_taisho_hiritu(ws_v1, session, resolver)
        session.commit()

        ws_v2 = _build_taisho_hiritu_ws([
            {"year": "令和7年度", "prefecture": "東京都",
             "corp": "テスト法人", "school": "テスト専門学校",
             "annual_total": 120, "grand_total": 120},
        ])
        import_taisho_hiritu(ws_v2, session, resolver)
        session.commit()

        rows = (
            session.query(SupportRecipient)
            .filter(SupportRecipient.school_id == school.id)
            .order_by(SupportRecipient.revision)
            .all()
        )
        assert [r.revision for r in rows] == [1, 2]
        assert [r.is_current for r in rows] == [False, True]
        assert rows[1].annual_total == 120


def test_taisho_hiritu_skips_unrealistic_future_fiscal_year(engine):
    with Session(engine) as session:
        school = School(
            prefecture="東京都",
            corporation_name="テスト法人",
            school_name="テスト専門学校",
            school_type="専門学校",
            status="active",
        )
        session.add(school)
        session.commit()

        resolver = SchoolResolver(session)
        resolver.build()
        ws = _build_taisho_hiritu_ws([
            {
                "year": "2099年度",
                "prefecture": "東京都",
                "corp": "テスト法人",
                "school": "テスト専門学校",
                "annual_total": 100,
                "grand_total": 100,
            },
        ])

        stats = import_taisho_hiritu(ws, session, resolver)

        assert stats["rows"] == 0
        assert stats["invalid_year"] == 1
        assert session.query(SupportRecipient).count() == 0


def test_taisho_hiritu_name_only_match_does_not_reconcile_school_prefecture(engine):
    with Session(engine) as session:
        school = School(
            prefecture="愛知県",
            corporation_name="テスト法人",
            school_name="テスト専門学校",
            school_type="専門学校",
            status="active",
        )
        session.add(school)
        session.commit()

        resolver = SchoolResolver(session)
        resolver.build()
        ws = _build_taisho_hiritu_ws([
            {
                "year": "令和7年度",
                "prefecture": "東京都",
                "corp": "テスト法人",
                "school": "テスト専門学校",
                "annual_total": 100,
                "grand_total": 100,
            },
        ])

        import_taisho_hiritu(ws, session, resolver)
        session.flush()

        session.refresh(school)
        assert school.prefecture == "愛知県"


def test_parse_fiscal_year_rejects_unrealistic_future_era_label() -> None:
    assert _parse_fiscal_year("令和99年度", max_fiscal_year=2027) is None
    assert _parse_fiscal_year("令和9年度", max_fiscal_year=2027) == 2027


def test_gakka_reimport_with_changed_excel_content_creates_revision_2(engine):
    with Session(engine) as session:
        school = School(
            prefecture="東京都",
            corporation_name="テスト法人",
            school_name="テスト専門学校",
            school_type="専門学校",
            status="active",
        )
        session.add(school)
        session.commit()

        resolver = SchoolResolver(session)
        resolver.build()

        base = {
            "year": 2026,
            "prefecture": "東京都",
            "corp": "テスト法人",
            "school": "テスト専門学校",
            "department": "情報処理学科",
            "capacity": 40,
            "enrollment": 80,
        }
        import_gakka(_build_gakka_ws([base]), session, resolver)
        session.commit()

        changed = dict(base, capacity=50, enrollment=90)
        import_gakka(_build_gakka_ws([changed]), session, resolver)
        session.commit()

        dept = session.query(Department).filter(Department.school_id == school.id).one()
        rows = (
            session.query(DepartmentYearly)
            .filter(DepartmentYearly.department_id == dept.id, DepartmentYearly.fiscal_year == 2026)
            .order_by(DepartmentYearly.revision)
            .all()
        )
        assert [r.revision for r in rows] == [1, 2]
        assert [r.is_current for r in rows] == [False, True]
        assert [r.capacity for r in rows] == [40, 50]
        assert rows[1].extraction_method == "excel_import"


def test_gakka_import_normalizes_specialized_course_suffix_to_field_label(engine):
    """Excel master and PDF parser must use the same Department natural key.

    Some master rows carry ``医療専門課程`` while PDF ingest normalizes the
    same concept to ``医療``. Import must normalize too, otherwise the next
    target-FY PDF creates a parallel Department instead of attaching yearly
    data to the master row.
    """
    with Session(engine) as session:
        school = School(
            prefecture="東京都",
            corporation_name="テスト法人",
            school_name="テスト専門学校",
            school_type="専門学校",
            status="active",
        )
        session.add(school)
        session.commit()

        resolver = SchoolResolver(session)
        resolver.build()
        import_gakka(
            _build_gakka_ws([
                {
                    "year": 2026,
                    "prefecture": "東京都",
                    "corp": "テスト法人",
                    "school": "テスト専門学校",
                    "course_name": "医療専門課程",
                    "department": "第一学科",
                    "duration": 3,
                    "capacity": 40,
                    "enrollment": 80,
                }
            ]),
            session,
            resolver,
        )
        session.commit()

        dept = session.query(Department).filter(Department.school_id == school.id).one()
        assert dept.course_name == "医療"


def test_gakka_import_reconciles_unique_school_prefecture_from_department_sheet(engine):
    with Session(engine) as session:
        school = School(
            prefecture="東京都",
            corporation_name="片柳学園",
            school_name="日本工学院北海道専門学校",
            school_type="専門学校",
            status="active",
        )
        session.add(school)
        session.commit()

        resolver = SchoolResolver(session)
        resolver.build()
        import_gakka(
            _build_gakka_ws([
                {
                    "year": 2026,
                    "prefecture": "北海道",
                    "corp": "片柳学園",
                    "school": "日本工学院北海道専門学校",
                    "department": "情報処理科",
                    "capacity": 40,
                    "enrollment": 80,
                }
            ]),
            session,
            resolver,
        )
        session.flush()

        session.refresh(school)
        assert school.prefecture == "北海道"

        resolved = resolver.resolve("北海道", "片柳学園", "日本工学院北海道専門学校")
        assert resolved == school.id


def test_gakka_reimport_does_not_overwrite_pdf_current_revision(engine):
    with Session(engine) as session:
        school = School(
            prefecture="東京都",
            corporation_name="テスト法人",
            school_name="テスト専門学校",
            school_type="専門学校",
            status="active",
        )
        session.add(school)
        session.commit()

        resolver = SchoolResolver(session)
        resolver.build()

        excel_row = {
            "year": 2026,
            "prefecture": "東京都",
            "corp": "テスト法人",
            "school": "テスト専門学校",
            "department": "情報処理学科",
            "capacity": 40,
            "enrollment": 80,
        }
        import_gakka(_build_gakka_ws([excel_row]), session, resolver)
        session.commit()

        dept = session.query(Department).filter(Department.school_id == school.id).one()
        session.query(DepartmentYearly).filter(
            DepartmentYearly.department_id == dept.id,
            DepartmentYearly.fiscal_year == 2026,
            DepartmentYearly.is_current.is_(True),
        ).update({"is_current": False}, synchronize_session="fetch")
        session.add(
            DepartmentYearly(
                department_id=dept.id,
                fiscal_year=2026,
                revision=2,
                is_current=True,
                capacity=55,
                enrollment=95,
                extraction_method="pdf_ingest",
                extraction_confidence=0.92,
            )
        )
        session.commit()

        import_gakka(_build_gakka_ws([excel_row]), session, resolver)
        session.commit()

        rows = (
            session.query(DepartmentYearly)
            .filter(DepartmentYearly.department_id == dept.id, DepartmentYearly.fiscal_year == 2026)
            .order_by(DepartmentYearly.revision)
            .all()
        )
        assert [r.revision for r in rows] == [1, 2]
        assert [r.is_current for r in rows] == [False, True]
        assert rows[1].capacity == 55
        assert rows[1].enrollment == 95
        assert rows[1].extraction_method == "pdf_ingest"
