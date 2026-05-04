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

from eidp.db.models import School, SupportRecipient
from eidp.db.sqlite_bootstrap import bootstrap_sqlite
from eidp.excel.importer import SchoolResolver, import_taisho_hiritu


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
