"""Slice 4b (RED->GREEN): pure 5-category diff of extracted vs master metric rows.

Categories: exact_match / value_mismatch / missing_actual (master has it, extractor
does not) / unexpected_actual (the "89 unmatched" class) / ambiguous_key (a key that
cannot map uniquely). ambiguous_key is BLOCKING. Synthetic rows only; no file I/O.
"""

from eidp.excel.master_diff import (
    DepartmentCollisionRow,
    ReconciliationArtifacts,
    TaxonomyReconciliationRow,
    align_department_fields,
    build_reconciliation_artifacts,
    detect_department_key_collisions,
    diff_metric_rows,
)
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


def test_align_collapses_bunya_when_gakka_unique_and_records_taxonomy() -> None:
    # 8 山形校: master files 公務員2年制 under 文化教養, PDF under 商業実務; the 学科 is unique
    # on each side -> collapse to a 分野-agnostic key so equal values still join, and record
    # the 分野 divergence as a non-blocking taxonomy reconciliation.
    expected = [_row("文化教養|公務員2年制", "enrollment", 115, campus="山形校")]
    actual = [_row("商業実務|公務員2年制", "enrollment", 115, campus="山形校")]
    exp2, act2, taxonomy = align_department_fields(expected, actual)
    result = diff_metric_rows(exp2, act2)
    assert result.counts["exact_match"] == 1
    assert result.counts["missing_actual"] == 0
    assert result.counts["unexpected_actual"] == 0
    assert len(taxonomy) == 1
    assert isinstance(taxonomy[0], TaxonomyReconciliationRow)
    assert taxonomy[0].master_field == "文化教養"
    assert taxonomy[0].pdf_field == "商業実務"
    assert taxonomy[0].department_gakka == "公務員2年制"
    assert taxonomy[0].operator_decision == "needs_owner_decision"


def test_align_keeps_full_key_when_gakka_collides_under_two_bunya() -> None:
    # same 学科 情報 filed under two 分野 = genuine collision -> not collapsed, kept distinct
    # (compose_department_key's 分野| prefix protection is preserved).
    expected = [_row("商業実務|情報", "enrollment", 50, campus="X"),
                _row("工業|情報", "enrollment", 30, campus="X")]
    actual = list(expected)
    exp2, act2, taxonomy = align_department_fields(expected, actual)
    result = diff_metric_rows(exp2, act2)
    assert result.counts["exact_match"] == 2
    assert not taxonomy


def test_align_no_taxonomy_when_bunya_agree() -> None:
    # 分野 agree on both sides -> collapse is a harmless no-op, no reconciliation row.
    expected = [_row("商業実務|会計2年制", "enrollment", 70)]
    actual = list(expected)
    exp2, act2, taxonomy = align_department_fields(expected, actual)
    assert diff_metric_rows(exp2, act2).counts["exact_match"] == 1
    assert not taxonomy


# ----- Guardrail G2: loose-key uniqueness invariant -----


def test_detect_collision_when_gakka_maps_to_two_bunya_on_a_side() -> None:
    # 情報 filed under two 分野 on the master side is NOT a unique loose key -> collision.
    # A loose (分野-agnostic) join cannot be trusted for it; the ambiguity must block.
    expected = [_row("商業実務|情報", "enrollment", 50, campus="X"),
                _row("工業|情報", "enrollment", 30, campus="X")]
    actual = [_row("商業実務|情報", "enrollment", 50, campus="X")]
    collisions = detect_department_key_collisions(expected, actual)
    assert len(collisions) == 1
    assert isinstance(collisions[0], DepartmentCollisionRow)
    assert collisions[0].department_gakka == "情報"
    assert set(collisions[0].fields) == {"商業実務", "工業"}


def test_no_collision_when_every_gakka_is_unique_per_side() -> None:
    expected = [_row("商業実務|会計2年制", "enrollment", 70),
                _row("文化教養|公務員2年制", "enrollment", 115)]
    actual = list(expected)
    assert detect_department_key_collisions(expected, actual) == []


# ----- Guardrail G4: structured reconciliation artifacts -----


def test_reconciliation_artifacts_group_capacity_taxonomy_and_hard_gate() -> None:
    expected = [_row("文化教養|公務員2年制", "enrollment", 115),  # 分野 divergence -> taxonomy
                _row("商業実務|会計2年制", "enrollment", 104),  # hard-gate value_mismatch (06 class)
                _row("商業実務|会計2年制", "capacity", 140)]  # capacity -> reconciliation
    actual = [_row("商業実務|公務員2年制", "enrollment", 115),
              _row("商業実務|会計2年制", "enrollment", 100),
              _row("商業実務|会計2年制", "capacity", 120)]
    exp2, act2, taxonomy = align_department_fields(expected, actual)
    result = diff_metric_rows(exp2, act2)
    artifacts = build_reconciliation_artifacts(result, taxonomy)
    assert isinstance(artifacts, ReconciliationArtifacts)
    assert len(artifacts.capacity) == 1
    assert len(artifacts.taxonomy) == 1
    assert len(artifacts.hard_gate_discrepancies) == 1
    assert artifacts.hard_gate_discrepancies[0].metric == "enrollment"
    assert artifacts.hard_gate_discrepancies[0].expected_value == 104
    assert artifacts.hard_gate_discrepancies[0].actual_value == 100
