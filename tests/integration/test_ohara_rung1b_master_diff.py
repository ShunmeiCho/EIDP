"""Rung 1b acceptance (env-gated): 3 risk-typed 大原 schools -> table extraction ->
actual MasterMetricRow (pinned identity) -> 学科-identity alignment -> master diff.

Acceptance (Rung 1b decision): for the 3 gated schools (03 obvious / 08 sibling+taxonomy /
16 label-variation) enrollment + intl_students are the hard gate (diff=0), no ambiguity,
no missing/unexpected; capacity and 分野-taxonomy divergences are non-blocking
reconciliations. 06 (盛岡校) is 08's sibling pair-mate carried as a documented
master_expected_error (extractor proven correct; master red-line, not editable here) --
it proves pin discrimination and is asserted to fail on exactly the known master Δ1.

Skipped unless EIDP_OHARA_SAMPLE_DIR is set and data/master.xlsx (read-only) is present.
The manifest-structure test runs unconditionally.
"""

import json
import os
from pathlib import Path

import pytest

from eidp.excel.actual_row_converter import convert_to_master_metric_rows
from eidp.excel.master_diff import align_department_fields, diff_metric_rows, rung_gate
from eidp.excel.master_loader import load_master_metric_rows
from eidp.pdf.master_ground_truth import normalize_text
from eidp.pdf.pinned_manifest import PinnedManifestRow, load_pinned_manifest
from eidp.pdf.table_grid_extractor import extract_table_grid_records

_SAMPLE = os.environ.get("EIDP_OHARA_SAMPLE_DIR")
_MASTER = Path("data/master.xlsx")
_MANIFEST = Path("tests/fixtures/ohara/rung1b_manifest.json")
_ALLOWED_RISK_FLAGS = {"obvious_match", "sibling_school_risk", "field_label_variation"}
_HARD_GATE = ("enrollment", "intl_students")

_needs_data = pytest.mark.skipif(
    not _SAMPLE or not _MASTER.exists() or not _MANIFEST.exists(),
    reason="needs EIDP_OHARA_SAMPLE_DIR + data/master.xlsx + the Rung-1b manifest fixture",
)


def _run(row: PinnedManifestRow):
    pdf = Path(_SAMPLE or ".") / Path(row.pdf_paths[0]).name
    records = extract_table_grid_records(pdf)
    actual = convert_to_master_metric_rows(
        records,
        school_key=normalize_text(row.school_key),
        campus_key=normalize_text(row.campus_key),
        fiscal_year=row.fiscal_year,
    )
    expected = load_master_metric_rows(
        _MASTER, corporation_name=row.school_key, school_name=row.campus_key,
        fiscal_year=row.fiscal_year,
    )
    exp2, act2, taxonomy = align_department_fields(expected, actual)
    result = diff_metric_rows(exp2, act2)
    return result, rung_gate(result), taxonomy


def _row(campus_key: str) -> PinnedManifestRow:
    return next(r for r in load_pinned_manifest(_MANIFEST) if r.campus_key == campus_key)


def test_rung1b_manifest_declares_risk_flags_and_official_authority() -> None:
    """Fixture contract (no data needed): every pin declares a valid risk_flag set, a
    human-confirmed official-PDF authority, and an expected_master_filter."""
    raw = json.loads(_MANIFEST.read_text(encoding="utf-8"))
    schools = raw["schools"]
    assert len(schools) == 4  # 3 gated + 1 sibling pair-mate finding
    for school in schools:
        assert school["risk_flags"], school["campus_key"]
        assert set(school["risk_flags"]) <= _ALLOWED_RISK_FLAGS, school["campus_key"]
        assert school["authority_basis"]["source_type"] == "human_confirmed_official_pdf"
        assert "expected_master_filter" in school
    gated = [s for s in schools if s["status"] == "pinned"]
    assert len(gated) == 3


@_needs_data
def test_rung1b_three_gated_schools_pass_enrollment_intl_hard_gate() -> None:
    gated = [r for r in load_pinned_manifest(_MANIFEST) if r.status == "pinned"]
    assert len(gated) == 3
    for row in gated:
        if not (Path(_SAMPLE or ".") / Path(row.pdf_paths[0]).name).exists():
            pytest.skip(f"sample not found for {row.campus_key}")
        result, gate, _taxonomy = _run(row)
        assert gate.passed, (row.campus_key, [(e.key, e.category) for e in gate.gate_failures])
        assert result.counts["ambiguous_key"] == 0, row.campus_key
        assert result.counts["missing_actual"] == 0, row.campus_key
        assert result.counts["unexpected_actual"] == 0, row.campus_key
        hard = [e for e in result.entries if e.metric in _HARD_GATE]
        assert hard, row.campus_key
        assert all(e.category == "exact_match" for e in hard), (
            row.campus_key, [(e.key, e.category) for e in hard if e.category != "exact_match"]
        )


@_needs_data
def test_rung1b_yamagata_bunya_taxonomy_is_reconciled_not_blocking() -> None:
    row = _row("大原ビジネス公務員専門学校山形校")
    if not (Path(_SAMPLE or ".") / Path(row.pdf_paths[0]).name).exists():
        pytest.skip("山形校 sample not found")
    _result, gate, taxonomy = _run(row)
    assert gate.passed  # 分野 divergence must NOT fail the hard gate
    gakka = {t.department_gakka: t for t in taxonomy}
    assert "公務員学科2年制" in gakka
    entry = gakka["公務員学科2年制"]
    assert {entry.master_field, entry.pdf_field} == {"文化教養", "商業実務"}
    assert entry.operator_decision == "needs_owner_decision"


@_needs_data
def test_rung1b_morioka_is_a_documented_master_expected_error() -> None:
    """06 pin is correct (all other hard-gate metrics exact); it fails ONLY on the known
    master Δ1 (在籍 master=91 vs official PDF 92) -- a master_expected_error, not extraction."""
    row = _row("大原ビジネス公務員専門学校盛岡校")
    assert row.status == "pinned_master_finding"
    if not (Path(_SAMPLE or ".") / Path(row.pdf_paths[0]).name).exists():
        pytest.skip("盛岡校 sample not found")
    result, gate, _taxonomy = _run(row)
    assert not gate.passed
    hard_fail = [e for e in gate.gate_failures if e.metric in _HARD_GATE]
    assert len(hard_fail) == 1
    only = hard_fail[0]
    assert only.metric == "enrollment"
    assert only.category == "value_mismatch"
    assert only.expected_value == 91  # master (stale)
    assert only.actual_value == 92  # official PDF (authoritative, raw '92人')
    # every OTHER hard-gate comparison is exact -> pin binds 盛岡校, only the master Δ1 fails.
    others = [e for e in result.entries if e.metric in _HARD_GATE and e.key != only.key]
    assert others
    assert all(e.category == "exact_match" for e in others)
