"""Slice 4b (RED->GREEN): pure 5-category diff of extracted vs master metric rows.

Categories: exact_match / value_mismatch / missing_actual (master has it, extractor
does not) / unexpected_actual (the "89 unmatched" class) / ambiguous_key (a key that
cannot map uniquely). ambiguous_key is BLOCKING. Synthetic rows only; no file I/O.
"""

from eidp.excel.master_diff import diff_metric_rows
from eidp.excel.master_loader import MasterMetricRow


def _row(dept: str, metric: str, value: object, *, school: str = "大原学園",
         campus: str | None = "札幌校", fy: int = 2025) -> MasterMetricRow:
    return MasterMetricRow(
        school_key=school, campus_key=campus, department_key=dept, fiscal_year=fy,
        metric=metric, value=value, source_sheet="学科別", source_cell=None,
    )


def test_exact_match_has_no_failures() -> None:
    expected = [_row("商業実務|会計2年制", "enrollment", 120),
                _row("商業実務|会計2年制", "capacity", 140)]
    actual = list(expected)
    result = diff_metric_rows(expected, actual)
    assert result.counts["exact_match"] == 2
    assert result.has_failures is False
    assert result.is_blocking is False


def test_reports_value_mismatch() -> None:
    expected = [_row("商業実務|会計2年制", "enrollment", 120)]
    actual = [_row("商業実務|会計2年制", "enrollment", 113)]
    result = diff_metric_rows(expected, actual)
    assert result.counts["value_mismatch"] == 1
    assert result.has_failures is True


def test_reports_missing_and_unexpected_rows() -> None:
    expected = [_row("商業実務|会計2年制", "enrollment", 120)]
    actual = [_row("工業|情報システム", "enrollment", 50)]
    result = diff_metric_rows(expected, actual)
    assert result.counts["missing_actual"] == 1
    assert result.counts["unexpected_actual"] == 1


def test_ambiguous_key_is_blocking() -> None:
    # A key that maps to >1 rows on either side (e.g. 昼/夜 collapsed into one key).
    expected = [_row("商業実務|会計2年制", "enrollment", 120),
                _row("商業実務|会計2年制", "enrollment", 130)]
    actual = [_row("商業実務|会計2年制", "enrollment", 120)]
    result = diff_metric_rows(expected, actual)
    assert result.counts["ambiguous_key"] == 1
    assert result.is_blocking is True
    assert result.has_failures is True


def test_none_versus_number_is_value_mismatch() -> None:
    result = diff_metric_rows(
        [_row("工業|情報システム", "enrollment", 30)],
        [_row("工業|情報システム", "enrollment", None)],
    )
    assert result.counts["value_mismatch"] == 1


def test_numeric_tolerance() -> None:
    strict = diff_metric_rows(
        [_row("工業|情報システム", "enrollment", 30)],
        [_row("工業|情報システム", "enrollment", 31)],
    )
    assert strict.counts["value_mismatch"] == 1
    lenient = diff_metric_rows(
        [_row("工業|情報システム", "enrollment", 30)],
        [_row("工業|情報システム", "enrollment", 31)],
        numeric_tolerance=1,
    )
    assert lenient.counts["exact_match"] == 1
