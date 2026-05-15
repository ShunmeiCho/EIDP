from pathlib import Path

import openpyxl
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from eidp.db.models import School, SchoolAlias, SchoolYearStatus
from eidp.db.sqlite_bootstrap import bootstrap_sqlite
from eidp.matcher.reconciler import (
    ReconcileCandidate,
    ReconcileReport,
    apply_reconciliation,
    load_target_institutions,
    reconcile,
    verify_identity,
)


def _session(tmp_path: Path) -> Session:
    engine = create_engine(f"sqlite:///{tmp_path / 'reconciler.sqlite3'}", future=True)
    bootstrap_sqlite(engine)
    return Session(engine)


def _school(
    session: Session,
    school_id: int,
    *,
    name: str,
    corp: str = "法人",
    code: str | None = None,
) -> School:
    school = School(
        id=school_id,
        prefecture="東京都",
        corporation_name=corp,
        school_name=name,
        school_type="専門学校",
        status="active",
        school_code=code,
    )
    session.add(school)
    session.flush()
    return school


def _write_target_list(data_dir: Path, rows: list[dict[str, str]]) -> Path:
    wb = openpyxl.Workbook()
    ws = wb.active
    for _ in range(4):
        ws.append([])
    for row in rows:
        values = [""] * 9
        values[0] = row.get("code", "")
        values[1] = row.get("category", "私立")
        values[2] = row.get("school_type", "専門学校")
        values[3] = row.get("name", "")
        values[6] = row.get("prefecture", "東京都")
        values[8] = row.get("setter", "")
        ws.append(values)
    path = data_dir / "target_institutions.xlsx"
    wb.save(path)
    wb.close()
    return path


def test_load_target_institutions_filters_specialty_schools(tmp_path: Path) -> None:
    path = _write_target_list(
        tmp_path,
        [
            {"code": "1001", "school_type": "専門学校", "name": "東京テスト専門学校", "setter": "法人A"},
            {"code": "2001", "school_type": "大学", "name": "東京大学", "setter": "法人B"},
        ],
    )

    targets = load_target_institutions(path)

    assert [(target.school_code, target.school_type, target.name, target.prefecture) for target in targets] == [
        ("1001", "専門学校", "東京テスト専門学校", "東京都")
    ]


def test_reconcile_assigns_exact_candidates_and_routes_fuzzy_or_excluded_to_manual(
    tmp_path: Path,
) -> None:
    _write_target_list(
        tmp_path,
        [
            {"code": "1001", "name": "東京テスト専門学校", "setter": "法人A"},
            {"code": "1002", "name": "大阪テスト専門学校", "setter": "法人B"},
            {"code": "1003", "name": "未収録専門学校", "setter": "法人C"},
        ],
    )

    with _session(tmp_path) as session:
        _school(session, 1, name="東京テスト専門学校", corp="法人A")
        _school(session, 2, name="大阪テスト専門", corp="法人B")
        excluded = _school(session, 3, name="閉校専門学校", corp="法人X")
        _school(session, 4, name="解決済み専門学校", corp="法人Y", code="9999")
        session.add(
            SchoolYearStatus(
                school_id=excluded.id,
                fiscal_year=2026,
                revision=1,
                is_current=True,
                status="excluded",
                excluded_reason="閉校",
            )
        )
        session.commit()

        report = reconcile(session, tmp_path)

    assert report.already_resolved == 1
    assert [(row.school_id, row.candidate_code, row.match_method) for row in report.auto_assigned] == [
        (1, "1001", "target_exact")
    ]
    assert [(row.school_id, row.candidate_code, row.match_method) for row in report.needs_manual] == [
        (2, "1002", "setter_containment")
    ]
    assert [(row.school_id, row.resolution, row.match_method) for row in report.excluded] == [
        (3, "excluded", "excluded:閉校")
    ]
    assert [target.school_code for target in report.missing_from_db] == ["1002", "1003"]


def test_apply_reconciliation_assigns_auto_codes_aliases_and_skips_conflicts(tmp_path: Path) -> None:
    report = ReconcileReport(
        auto_assigned=[
            ReconcileCandidate(
                school_id=1,
                school_name="東京テスト",
                prefecture="東京都",
                corporation_name="法人A",
                candidate_code="1001",
                candidate_name="東京テスト専門学校",
                match_method="target_exact",
                confidence=1.0,
            ),
            ReconcileCandidate(
                school_id=2,
                school_name="競合校",
                prefecture="東京都",
                corporation_name="法人B",
                candidate_code="9999",
                candidate_name="競合専門学校",
                match_method="target_exact",
                confidence=1.0,
            ),
            ReconcileCandidate(
                school_id=404,
                school_name="存在しない学校",
                prefecture="東京都",
                corporation_name="法人C",
                candidate_code="4040",
            ),
        ]
    )

    with _session(tmp_path) as session:
        _school(session, 1, name="東京テスト")
        _school(session, 2, name="競合校")
        _school(session, 3, name="既存コード校", code="9999")
        session.commit()

        stats = apply_reconciliation(session, report)
        session.commit()

        assigned = session.get(School, 1)
        conflicted = session.get(School, 2)
        aliases = session.query(SchoolAlias).all()

    assert stats == {"codes_assigned": 1, "aliases_created": 1}
    assert assigned is not None and assigned.school_code == "1001"
    assert conflicted is not None and conflicted.school_code is None
    assert [(alias.school_id, alias.alias_name, alias.source) for alias in aliases] == [
        (1, "東京テスト専門学校", "target_list")
    ]


def test_verify_identity_reports_target_gap_and_current_exclusion(tmp_path: Path) -> None:
    _write_target_list(
        tmp_path,
        [
            {"code": "1001", "name": "コードあり専門学校", "setter": "法人A"},
            {"code": "1002", "name": "DB未収録専門学校", "setter": "法人B"},
        ],
    )

    with _session(tmp_path) as session:
        _school(session, 1, name="コードあり専門学校", code="1001")
        _school(session, 2, name="未解決専門学校")
        excluded = _school(session, 3, name="閉校専門学校")
        session.add(
            SchoolYearStatus(
                school_id=excluded.id,
                fiscal_year=2026,
                revision=1,
                is_current=True,
                status="excluded",
                excluded_reason="閉校",
            )
        )
        session.commit()

        report = verify_identity(session, tmp_path)

    assert report == {
        "total_schools": 3,
        "with_code": 1,
        "without_code": 2,
        "excluded_no_code_needed": 1,
        "truly_unresolved": 1,
        "duplicate_codes": 0,
        "target_list_gap": 1,
        "pass": False,
    }
