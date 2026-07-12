"""Melt extractor ``TableDepartmentRecord`` rows into ACTUAL ``MasterMetricRow`` rows
for the ground-truth diff (Rung 1a).

Pins school_key/campus_key/fiscal_year from the human-confirmed PDF identity -- NEVER
reverse-inferred from data/master.xlsx (that would be fake success). Reuses
``master_loader.compose_department_key`` and ``master_ground_truth.normalize_text`` so
the actual-side key tuple lands in the SAME canonical space as the read-only master
loader, letting ``diff_metric_rows`` collapse an all-present school to exact_match with
zero missing/unexpected/ambiguous rows.

Metric emission -- DESIGN CHOICE: EMIT one ``MasterMetricRow`` per (department, metric)
for ALL THREE metrics (capacity/enrollment/intl_students), INCLUDING metrics whose value
is None. Rationale: ``load_master_metric_rows`` unconditionally emits 3 rows per
department (value may be None). A None-on-both-sides metric then diffs as exact_match.
SKIPPING the None row instead would leave the loader's always-present None row unmatched
-> a phantom ``missing_actual`` failure that breaks the clean-diff acceptance. So the
actual side must be symmetric with the loader: always 3 rows per department.

``source_cell`` carries page/table/row/col provenance from the record's ``CellEvidence``
for that metric (None when the metric has no evidence -- value-absent implies
provenance-absent, since the extractor records evidence only for parsed values).
"""

from __future__ import annotations

from eidp.excel.master_loader import MasterMetricRow, compose_department_key
from eidp.pdf.master_ground_truth import normalize_text
from eidp.pdf.table_grid_extractor import CellEvidence, TableDepartmentRecord

__all__ = ["convert_to_master_metric_rows"]

# Melt order mirrors master_loader._METRIC_LABELS and the extractor's enrollment metrics.
_METRICS = ("capacity", "enrollment", "intl_students")
_SOURCE_SHEET = "extractor"


def _source_cell(evidence: CellEvidence | None) -> str | None:
    """Compact, greppable page/table/row/col provenance string for one metric cell."""
    if evidence is None:
        return None
    return (
        f"page={evidence.page_no};table={evidence.table_index};"
        f"row={evidence.row_index};col={evidence.col_index}"
    )


def convert_to_master_metric_rows(
    records: list[TableDepartmentRecord],
    *,
    school_key: str,
    campus_key: str | None,
    fiscal_year: int,
) -> list[MasterMetricRow]:
    """Melt extractor records into actual metric rows under the PINNED identity.

    Each record yields exactly 3 rows (one per metric, None values included). The pinned
    school_key/campus_key are folded into the loader's normalized key space; the
    department_key is composed via ``compose_department_key`` so the diff can join. The
    fiscal_year is the pinned value, never taken from master.
    """
    pinned_school = normalize_text(school_key)
    pinned_campus = normalize_text(campus_key) if campus_key is not None else None

    rows: list[MasterMetricRow] = []
    for record in records:
        dept = compose_department_key(record.field_category, record.department_name)
        evidence_by_metric = {ev.canonical_metric: ev for ev in record.evidence}
        for metric in _METRICS:
            rows.append(
                MasterMetricRow(
                    school_key=pinned_school,
                    campus_key=pinned_campus,
                    department_key=dept,
                    fiscal_year=fiscal_year,
                    metric=metric,
                    value=getattr(record, metric),
                    source_sheet=_SOURCE_SHEET,
                    source_cell=_source_cell(evidence_by_metric.get(metric)),
                )
            )
    return rows
