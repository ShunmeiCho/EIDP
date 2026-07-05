"""Rung 1a (RED->GREEN): melt extractor TableDepartmentRecord rows into ACTUAL
MasterMetricRow rows keyed by the PINNED (school, campus, fiscal_year) identity.

Contract asserted here (synthetic records only; no PDF or Excel I/O):
- department_key MUST equal ``master_loader.compose_department_key`` so an all-present
  school collapses to exact_match under ``diff_metric_rows``.
- Identity (school_key/campus_key/fiscal_year) is PINNED from the human-confirmed PDF,
  never reverse-inferred from master, and lands in the loader's normalized key space.
- Every metric emits a row -- INCLUDING value=None -- mirroring master_loader's
  unconditional 3-rows-per-department shape, so a None-on-both-sides metric diffs as
  exact_match instead of a phantom missing_actual.
- CellEvidence page/table/row/col flows into source_cell so provenance survives.
"""

from pathlib import Path

import pytest

from eidp.excel.actual_row_converter import convert_to_master_metric_rows
from eidp.excel.master_loader import MasterMetricRow, compose_department_key, load_master_metric_rows
from eidp.pdf.master_ground_truth import normalize_text
from eidp.pdf.table_grid_extractor import CellEvidence, TableDepartmentRecord


def _evidence(metric: str, *, page_no: int, table_index: int, row_index: int,
              col_index: int) -> CellEvidence:
    return CellEvidence(
        page_no=page_no,
        table_index=table_index,
        row_index=row_index,
        col_index=col_index,
        raw_label=metric,
        raw_value="x",
        canonical_metric=metric,
        confidence=1.0,
    )


def _operator_master_path() -> Path | None:
    repo_root = Path(__file__).resolve().parents[2]
    candidates = [repo_root / "data" / "master.xlsx"]
    if repo_root.parent.name == ".worktrees":
        candidates.append(repo_root.parent.parent / "data" / "master.xlsx")
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _record(**overrides: object) -> TableDepartmentRecord:
    base: dict[str, object] = {
        "field_category": "商業実務",
        "course_name": "専門課程",
        "department_name": "会計2年制学科",
        "capacity": 140,
        "enrollment": 120,
        "intl_students": 3,
        "evidence": (
            _evidence("capacity", page_no=0, table_index=1, row_index=3, col_index=2),
            _evidence("enrollment", page_no=0, table_index=1, row_index=3, col_index=3),
            _evidence("intl_students", page_no=0, table_index=1, row_index=3, col_index=4),
        ),
    }
    base.update(overrides)
    return TableDepartmentRecord(**base)  # type: ignore[arg-type]


def test_emits_three_melted_rows_per_record() -> None:
    rows = convert_to_master_metric_rows(
        [_record(), _record(department_name="情報システム学科")],
        school_key="S", campus_key="C", fiscal_year=2025,
    )
    assert len(rows) == 6
    assert [r.metric for r in rows[:3]] == ["capacity", "enrollment", "intl_students"]


def test_empty_records_yield_no_rows() -> None:
    assert convert_to_master_metric_rows(
        [], school_key="S", campus_key="C", fiscal_year=2025
    ) == []


def test_department_key_matches_compose_department_key() -> None:
    # 分野 with a middle-dot and a 学科名 with a suffix -- both must be canonicalized
    # exactly the way the read-only loader does, or the diff cannot join.
    record = _record(field_category="文化・教養", department_name="ビジネスキャリア2年制学科")
    rows = convert_to_master_metric_rows(
        [record], school_key="S", campus_key="C", fiscal_year=2025
    )
    expected_key = compose_department_key("文化・教養", "ビジネスキャリア2年制学科")
    assert {r.department_key for r in rows} == {expected_key}


def test_uses_pinned_identity_not_master() -> None:
    rows = convert_to_master_metric_rows(
        [_record()], school_key="大原学園", campus_key="札幌校", fiscal_year=2025
    )
    assert {r.school_key for r in rows} == {"大原学園"}
    assert {r.campus_key for r in rows} == {"札幌校"}
    assert {r.fiscal_year for r in rows} == {2025}


def test_pinned_identity_normalized_into_loader_key_space() -> None:
    # load_master_metric_rows keys on normalize_text(corp)/normalize_text(school). The
    # converter MUST fold into that same space (full-width / stray whitespace) or the
    # tuple keys will not join under diff_metric_rows.
    rows = convert_to_master_metric_rows(
        [_record()], school_key="大原 学園", campus_key="札幌　校", fiscal_year=2025
    )
    assert {r.school_key for r in rows} == {normalize_text("大原 学園")}
    assert {r.campus_key for r in rows} == {normalize_text("札幌　校")}


def test_campus_key_none_is_preserved() -> None:
    rows = convert_to_master_metric_rows(
        [_record()], school_key="S", campus_key=None, fiscal_year=2025
    )
    assert all(r.campus_key is None for r in rows)


def test_source_sheet_is_extractor() -> None:
    rows = convert_to_master_metric_rows(
        [_record()], school_key="S", campus_key="C", fiscal_year=2025
    )
    assert {r.source_sheet for r in rows} == {"extractor"}


def test_source_cell_carries_page_table_row_col_evidence() -> None:
    record = _record(
        capacity=None,
        intl_students=None,
        evidence=(_evidence("enrollment", page_no=4, table_index=2, row_index=7, col_index=5),),
    )
    rows = convert_to_master_metric_rows(
        [record], school_key="S", campus_key="C", fiscal_year=2025
    )
    enrollment_row = next(r for r in rows if r.metric == "enrollment")
    assert enrollment_row.source_cell is not None
    assert "page=4" in enrollment_row.source_cell
    assert "table=2" in enrollment_row.source_cell
    assert "row=7" in enrollment_row.source_cell
    assert "col=5" in enrollment_row.source_cell


def test_metric_values_come_from_the_record() -> None:
    rows = convert_to_master_metric_rows(
        [_record(capacity=140, enrollment=120, intl_students=3)],
        school_key="S", campus_key="C", fiscal_year=2025,
    )
    by_metric = {r.metric: r.value for r in rows}
    assert by_metric == {"capacity": 140, "enrollment": 120, "intl_students": 3}


def test_none_metric_row_is_emitted_with_no_provenance() -> None:
    # DESIGN CHOICE: EMIT the None row (do not skip). intl_students has no evidence, so
    # its source_cell is None -- value-absent implies provenance-absent, symmetrically.
    record = _record(
        intl_students=None,
        evidence=(
            _evidence("capacity", page_no=0, table_index=0, row_index=2, col_index=1),
            _evidence("enrollment", page_no=0, table_index=0, row_index=2, col_index=2),
        ),
    )
    rows = convert_to_master_metric_rows(
        [record], school_key="S", campus_key="C", fiscal_year=2025
    )
    intl_rows = [r for r in rows if r.metric == "intl_students"]
    assert len(intl_rows) == 1
    assert intl_rows[0].value is None
    assert intl_rows[0].source_cell is None


def test_converted_rows_diff_clean_against_symmetric_master_rows() -> None:
    from eidp.excel.master_diff import diff_metric_rows

    record = _record()
    actual = convert_to_master_metric_rows(
        [record], school_key="大原学園", campus_key="札幌校", fiscal_year=2025
    )
    dept = compose_department_key(record.field_category, record.department_name)
    expected = [
        MasterMetricRow(
            school_key="大原学園", campus_key="札幌校", department_key=dept,
            fiscal_year=2025, metric=m, value=v, source_sheet="学科別", source_cell=None,
        )
        for m, v in (("capacity", 140), ("enrollment", 120), ("intl_students", 3))
    ]
    result = diff_metric_rows(expected, actual)
    assert result.counts["exact_match"] == 3
    assert result.has_failures is False
    assert result.is_blocking is False


def test_none_metric_diffs_as_exact_match_not_missing() -> None:
    # The load-bearing reason to EMIT None: master_loader ALWAYS emits an intl_students
    # row (value None when the master has none). If the converter SKIPPED None, the diff
    # would see expected-present/actual-absent -> phantom missing_actual and fail the
    # clean-diff acceptance. Emitting keeps None-on-both-sides an exact_match.
    from eidp.excel.master_diff import diff_metric_rows

    record = _record(
        intl_students=None,
        evidence=(
            _evidence("capacity", page_no=0, table_index=0, row_index=2, col_index=1),
            _evidence("enrollment", page_no=0, table_index=0, row_index=2, col_index=2),
        ),
    )
    actual_intl = [
        r
        for r in convert_to_master_metric_rows(
            [record], school_key="大原学園", campus_key="札幌校", fiscal_year=2025
        )
        if r.metric == "intl_students"
    ]
    dept = compose_department_key(record.field_category, record.department_name)
    expected_intl = [
        MasterMetricRow(
            school_key="大原学園", campus_key="札幌校", department_key=dept,
            fiscal_year=2025, metric="intl_students", value=None,
            source_sheet="学科別", source_cell=None,
        )
    ]
    result = diff_metric_rows(expected_intl, actual_intl)
    assert result.counts["exact_match"] == 1
    assert result.counts["missing_actual"] == 0
    assert result.counts["unexpected_actual"] == 0


@pytest.mark.skipif(_operator_master_path() is None, reason="operator data/master.xlsx absent")
def test_real_master_diff_matches_small_ohara_subset_read_only() -> None:
    master_path = _operator_master_path()
    assert master_path is not None
    before = master_path.read_bytes()
    record = _record(
        department_name="ビジネスキャリア2年制",
        capacity=140,
        enrollment=113,
        intl_students=0,
        evidence=(
            _evidence("capacity", page_no=8, table_index=2, row_index=7, col_index=0),
            _evidence("enrollment", page_no=8, table_index=2, row_index=7, col_index=2),
            _evidence("intl_students", page_no=8, table_index=2, row_index=7, col_index=3),
        ),
    )

    expected = load_master_metric_rows(
        master_path,
        corporation_name="大原学園",
        school_name="大原簿記情報専門学校札幌校",
        fiscal_year=2025,
    )
    expected_subset = [
        row for row in expected if row.department_key == "商業実務|ビジネスキャリア2年制"
    ]
    actual = convert_to_master_metric_rows(
        [record],
        school_key="大原学園",
        campus_key="大原簿記情報専門学校札幌校",
        fiscal_year=2025,
    )

    from eidp.excel.master_diff import diff_metric_rows

    result = diff_metric_rows(expected_subset, actual)

    assert len(expected_subset) == 3
    assert result.counts["exact_match"] == 3
    assert result.has_failures is False
    assert master_path.read_bytes() == before
