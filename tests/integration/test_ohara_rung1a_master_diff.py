"""Rung 1a end-to-end acceptance (env-gated): one human-confirmed 大原 official PDF ->
table extraction -> actual MasterMetricRow (pinned identity) -> master diff.

Acceptance (Rung 1a decision): enrollment + intl_students are the hard gate (diff=0),
no ambiguity, full dept coverage; capacity (収容定員 vs 生徒総定員数) is surfaced as a
reconciliation item, never forced to zero. Skipped unless EIDP_OHARA_SAMPLE_DIR is set and
data/master.xlsx (red-line, read-only) is present.
"""

import os
from pathlib import Path

import pytest

from eidp.excel.actual_row_converter import convert_to_master_metric_rows
from eidp.excel.master_diff import build_reconciliation_report, diff_metric_rows, rung_gate
from eidp.excel.master_loader import load_master_metric_rows
from eidp.pdf.master_ground_truth import normalize_text
from eidp.pdf.pinned_manifest import load_pinned_manifest
from eidp.pdf.table_grid_extractor import extract_table_grid_records

_SAMPLE = os.environ.get("EIDP_OHARA_SAMPLE_DIR")
_MASTER = Path("data/master.xlsx")
_MANIFEST = Path("tests/fixtures/ohara/ohara_rung1a_manifest.json")


@pytest.mark.skipif(
    not _SAMPLE or not _MASTER.exists() or not _MANIFEST.exists(),
    reason="needs EIDP_OHARA_SAMPLE_DIR + data/master.xlsx + the Rung-1a manifest fixture",
)
def test_rung1a_enrollment_gate_passes_capacity_reconciled() -> None:
    row = load_pinned_manifest(_MANIFEST)[0]
    pdf = Path(_SAMPLE or ".") / Path(row.pdf_paths[0]).name
    if not pdf.exists():
        pytest.skip(f"sample not found: {pdf}")

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
    result = diff_metric_rows(expected, actual)
    gate = rung_gate(result)

    # Hard gate: enrollment + intl_students diff=0, no ambiguity, complete dept coverage.
    assert gate.passed, [(e.key, e.category) for e in gate.gate_failures]
    assert result.counts["ambiguous_key"] == 0
    assert result.counts["missing_actual"] == 0
    assert result.counts["unexpected_actual"] == 0
    assert gate.status in ("pass", "pass_with_reconciliation")

    # capacity divergence (if any) is surfaced with the official PDF value, never dropped.
    for recon in build_reconciliation_report(result):
        assert recon.pdf_value is not None
        assert recon.operator_decision == "needs_owner_decision"
