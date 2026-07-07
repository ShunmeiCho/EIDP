"""End-to-end Linux/Web chain proof on a REAL disclosure PDF.

Drives a single PDF through the whole pipeline the browser pages sit on top of:

    intake -> extraction queue -> table extraction -> review (accept) ->
    reviewed rows -> master diff (page 04) -> external double-check (page 05) ->
    Excel-ready invariant

The unit suites cover each stage in isolation and the Ohara rung tests cover
extraction -> excel/master_diff, but nothing proved the Linux/Web stages actually
feed one another. This is that missing full-chain regression guard.

Fixtures: the git-tracked ``data/sample-pdfs/nkz.pdf`` (a real 専門学校 disclosure
PDF whose ``ゲーム4年制学科(...コース)`` rows exercise the parenthesized-コース structure
that MUST stay distinct). ``data/master.xlsx`` is red-line / untracked, so the
expected (04) and external (05) sides are built from the REAL extracted values --
the point here is chain wiring plus the Excel-ready invariant, not re-deriving
master. No network, no red-line files; all writes land under pytest ``tmp_path``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from eidp.pdf.table_grid_extractor import extract_table_grid_records
from eidp.pipeline.double_check_compare import DoubleCheckStatus, compare_external_to_reviewed
from eidp.pipeline.external_extraction_import import ExternalExtractionRow, ExternalSourceSystem
from eidp.pipeline.extraction_queue import (
    ExtractionStatus,
    load_extracted_rows,
    process_intake_record,
)
from eidp.pipeline.extraction_review import (
    ReviewTaskType,
    accept_review_record,
    ensure_review_records,
)
from eidp.pipeline.pdf_intake import PdfKind, store_pdf_upload, validate_intake_metadata
from eidp.pipeline.review_master_diff import (
    MasterExpectedRow,
    MatchStatus,
    diff_reviewed_against_master,
)
from eidp.pipeline.review_report import ReviewedExtractionRow, reviewed_rows_from_records

_SAMPLE = Path("data/sample-pdfs/nkz.pdf")
_needs_sample = pytest.mark.skipif(not _SAMPLE.exists(), reason="needs data/sample-pdfs/nkz.pdf")

_SCHOOL = "E2Eテスト電子専門学校"  # supplied at intake; the PDF gives departments, not the school
_SCHOOL_ID = "S-E2E"
_FY = 2025


def _run_chain_to_reviewed(tmp_path: Path) -> list[ReviewedExtractionRow]:
    """intake -> extract (REAL) -> accept every metric review -> reviewed rows."""
    metadata = validate_intake_metadata(
        school_name=_SCHOOL,
        school_id=_SCHOOL_ID,
        fiscal_year=_FY,
        source_page_url="https://example.ac.jp/disclosure/",
        uploaded_filename="nkz.pdf",
    )
    record = store_pdf_upload(
        metadata=metadata,
        pdf_bytes=_SAMPLE.read_bytes(),
        intake_root=tmp_path,
        detect_pdf_kind_func=lambda _content: PdfKind.TEXT,
    )
    item = process_intake_record(
        intake_root=tmp_path,
        intake_record_id=record.record_id,
        extractor_func=extract_table_grid_records,
    )
    assert item.status == ExtractionStatus.EXTRACTION_COMPLETED
    extracted = load_extracted_rows(tmp_path, record.record_id)
    assert extracted, "the real PDF must yield extracted metric rows"
    assert item.rows_written == len(extracted)
    # No Excel is written anywhere along the extraction path.
    assert list(tmp_path.rglob("*.xlsx")) == []

    for review in ensure_review_records(tmp_path):
        if review.task_type == ReviewTaskType.EXTRACTED_METRIC:
            accept_review_record(
                intake_root=tmp_path, review_id=review.review_id, reviewed_by="op-e2e"
            )
    reviewed = reviewed_rows_from_records(ensure_review_records(tmp_path))
    assert all(row.school_name == _SCHOOL for row in reviewed)
    return reviewed


def _enrollment_rows(reviewed: list[ReviewedExtractionRow]) -> list[ReviewedExtractionRow]:
    return [
        row
        for row in reviewed
        if row.metric == "enrollment" and row.final_review_value is not None
    ]


@_needs_sample
def test_e2e_intake_extraction_review_carry_real_evidence(tmp_path: Path) -> None:
    reviewed = _run_chain_to_reviewed(tmp_path)
    enrollment = _enrollment_rows(reviewed)
    assert len(enrollment) >= 2
    # Every accepted enrollment row keeps its page/table/row/col provenance end to end.
    for row in enrollment:
        assert row.page_no is not None
        assert row.table_index is not None
        assert row.row_index is not None
        assert row.col_index is not None
    # The real ゲーム4年制学科(...コース) departments survive intake+extraction+review.
    assert any(
        (row.department_name or "").startswith("ゲーム4年制学科(") for row in enrollment
    )


@_needs_sample
def test_e2e_diff_and_double_check_hold_the_excel_ready_invariant(tmp_path: Path) -> None:
    reviewed = _run_chain_to_reviewed(tmp_path)
    enrollment = _enrollment_rows(reviewed)

    # ----- page 04: review vs a master subset built from the real values -----
    row_match, row_mismatch = enrollment[0], enrollment[1]
    expected = [
        MasterExpectedRow(
            school_name=_SCHOOL, school_id=_SCHOOL_ID, fiscal_year=_FY,
            department_name=row_match.department_name or "", metric="enrollment",
            expected_value=row_match.final_review_value, field_category=row_match.field_category,
        ),
        MasterExpectedRow(
            school_name=_SCHOOL, school_id=_SCHOOL_ID, fiscal_year=_FY,
            department_name=row_mismatch.department_name or "", metric="enrollment",
            expected_value=(row_mismatch.final_review_value or 0) + 1,
            field_category=row_mismatch.field_category,
        ),
    ]
    diff = diff_reviewed_against_master([row_match, row_mismatch], expected)
    statuses = [entry.match_status for entry in diff]
    assert statuses.count(MatchStatus.MATCH) == 1  # exact real value
    assert statuses.count(MatchStatus.VALUE_MISMATCH) == 1  # deliberately off by one
    # Two distinct real departments must NOT false-merge under the loose key.
    assert MatchStatus.AMBIGUOUS_KEY not in statuses

    # ----- page 05: distinct コース siblings must double-check independently -----
    siblings = [
        row
        for row in enrollment
        if (row.department_name or "").startswith("ゲーム4年制学科(")
    ]
    assert len(siblings) >= 2, "nkz carries multiple distinct game-course siblings"
    external = [
        ExternalExtractionRow(
            school_name=_SCHOOL, school_id=_SCHOOL_ID, corporation_name="E2E",
            prefecture="東京都", field_category=sibling.field_category,
            course_name=sibling.course_name, department_name=sibling.department_name or "",
            metric="enrollment", value=sibling.final_review_value, fiscal_year=_FY,
            source_system=ExternalSourceSystem.COPILOT, source_file="external.csv",
            source_row_number=index,
        )
        for index, sibling in enumerate(siblings)
    ]
    double_check = compare_external_to_reviewed(siblings, external)
    # Each コース sibling compares as its own clean TRUE -- the granularity guard must
    # neither collapse them into one another nor flag the parenthesized コース as ambiguous.
    assert len(double_check) == len(siblings)
    assert all(row.comparison_status == DoubleCheckStatus.MATCH for row in double_check)
    assert all(row.comparison_result == "TRUE" for row in double_check)
    # Load-bearing invariant: nothing on the double-check lane is ever Excel-ready.
    assert all(row.excel_ready is False for row in double_check)
