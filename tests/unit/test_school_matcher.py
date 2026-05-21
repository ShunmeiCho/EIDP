from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from eidp.db.models import School, SchoolAlias
from eidp.db.sqlite_bootstrap import bootstrap_sqlite
from eidp.matcher.school_matcher import (
    MatchReport,
    MatchResult,
    apply_matches,
    build_indices,
    load_mext_entries,
    match_schools,
)


def _session(tmp_path: Path) -> Session:
    engine = create_engine(f"sqlite:///{tmp_path / 'school_matcher.sqlite3'}", future=True)
    bootstrap_sqlite(engine)
    return Session(engine)


def _write_mext_csv(data_dir: Path, name: str, rows: list[list[str]]) -> None:
    header = ["code", "type", "pref", "unused1", "unused2", "name", "address", "u3", "u4", "abolished"]
    content = "\n".join(",".join(row) for row in [header, *rows]) + "\n"
    (data_dir / name).write_bytes(content.encode("cp932"))


def _add_school(session: Session, *, school_id: int, name: str, prefecture: str = "東京都") -> None:
    session.add(
        School(
            id=school_id,
            prefecture=prefecture,
            corporation_name=f"法人{school_id}",
            school_name=name,
            school_type="専門学校",
            status="active",
        )
    )


def test_load_mext_entries_filters_to_active_senshu_schools(tmp_path: Path) -> None:
    _write_mext_csv(
        tmp_path,
        "school_code_east.csv",
        [
            ["1001", "H1", "13(東京)", "", "", "東京テスト専門学校", "addr", "", "", ""],
            ["1002", "A1", "13(東京)", "", "", "大学", "addr", "", "", ""],
            ["1003", "H1", "13(東京)", "", "", "閉校専門学校", "addr", "", "", "2025-03-31"],
            ["1004", "H1", "02(青森)", "", "", "青森テスト専門学校", "addr", "", "", ""],
        ],
    )

    entries = load_mext_entries(tmp_path)

    assert [(entry.code, entry.prefecture, entry.name) for entry in entries] == [
        ("1001", "東京都", "東京テスト専門学校"),
        ("1004", "青森県", "青森テスト専門学校"),
    ]


def test_match_schools_covers_exact_nfkc_aggressive_partial_and_empty_db(tmp_path: Path) -> None:
    _write_mext_csv(
        tmp_path,
        "school_code_east.csv",
        [
            ["1001", "H1", "13(東京)", "", "", "東京テスト専門学校", "addr", "", "", ""],
            ["1002", "H1", "13(東京)", "", "", "東京デザイン専門学校", "addr", "", "", ""],
            ["1003", "H1", "13(東京)", "", "", "学校法人東京&AI専門学校", "addr", "", "", ""],
            ["1004", "H1", "13(東京)", "", "", "東京医療福祉専門学校", "addr", "", "", ""],
        ],
    )

    with _session(tmp_path) as session:
        assert match_schools(session, tmp_path).total == 0

        _add_school(session, school_id=1, name="東京テスト専門学校")
        _add_school(session, school_id=2, name="東京デザイン 専門学校")
        _add_school(session, school_id=3, name="東京専門学校")
        _add_school(session, school_id=4, name="東京医療福祉専門")
        _add_school(session, school_id=5, name="未登録専門学校")
        session.commit()

        report = match_schools(session, tmp_path)

    assert [(row.school_id, row.mext_code, row.match_method) for row in report.exact] == [
        (1, "1001", "exact")
    ]
    assert [(row.school_id, row.mext_code, row.match_method) for row in report.nfkc] == [
        (2, "1002", "nfkc")
    ]
    assert (3, "1003", "aggressive") in [
        (row.school_id, row.mext_code, row.match_method) for row in report.pref_partial
    ]
    assert (4, "1004", "pref_partial") in [
        (row.school_id, row.mext_code, row.match_method) for row in report.pref_partial
    ]
    assert [row.school_id for row in report.unmatched] == [5]


def test_build_indices_prefers_prefecture_candidate_for_duplicate_names() -> None:
    entries = [
        load_entry("1001", "東京都", "同名専門学校"),
        load_entry("2001", "大阪府", "同名専門学校"),
    ]

    idx = build_indices(entries)

    assert [entry.code for entry in idx.by_name["同名専門学校"]] == ["1001", "2001"]
    assert [entry.code for entry in idx.by_pref["大阪府"]] == ["2001"]


def load_entry(code: str, prefecture: str, name: str):
    from eidp.matcher.school_matcher import MextEntry

    return MextEntry(
        code=code,
        school_type="H1",
        prefecture=prefecture,
        name=name,
        address="addr",
        abolished_date="",
    )


def test_apply_matches_assigns_codes_creates_aliases_and_skips_conflicts(tmp_path: Path) -> None:
    report = MatchReport(
        exact=[
            MatchResult(
                school_id=1,
                school_name="東京テスト",
                prefecture="東京都",
                corporation_name="A",
                mext_code="1001",
                mext_name="東京テスト専門学校",
                match_method="exact",
                confidence=1.0,
            ),
            MatchResult(
                school_id=2,
                school_name="競合A",
                prefecture="東京都",
                corporation_name="B",
                mext_code="9999",
                mext_name="競合専門学校A",
                match_method="exact",
                confidence=1.0,
            ),
        ],
        nfkc=[
            MatchResult(
                school_id=3,
                school_name="競合B",
                prefecture="東京都",
                corporation_name="C",
                mext_code="9999",
                mext_name="競合専門学校B",
                match_method="nfkc",
                confidence=0.95,
            )
        ],
        pref_partial=[
            MatchResult(
                school_id=4,
                school_name="手動候補",
                prefecture="東京都",
                corporation_name="D",
                mext_code="4001",
                mext_name="手動候補専門学校",
                match_method="pref_partial",
                confidence=0.8,
            )
        ],
    )

    with _session(tmp_path) as session:
        for school_id, name in [(1, "東京テスト"), (2, "競合A"), (3, "競合B"), (4, "手動候補")]:
            _add_school(session, school_id=school_id, name=name)
        session.commit()

        stats = apply_matches(session, report)
        session.commit()

        assigned = session.get(School, 1)
        conflicted = session.get(School, 2)
        review_only = session.get(School, 4)
        aliases = session.query(SchoolAlias).all()

    assert stats == {"codes_assigned": 1, "aliases_created": 1, "conflicts": 2, "needs_review": 1}
    assert assigned is not None and assigned.school_code == "1001"
    assert conflicted is not None and conflicted.school_code is None
    assert review_only is not None and review_only.school_code is None
    assert [(alias.school_id, alias.alias_name, alias.source) for alias in aliases] == [
        (1, "東京テスト専門学校", "mext")
    ]
