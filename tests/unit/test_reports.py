"""Tests for the eidp.reports module (Sprint 0 acceptance criteria)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import eidp.reports.coverage as coverage_module
import eidp.reports.gaps as gaps_module
from eidp.db.models import (
    Base,
    Department,
    DepartmentYearly,
    Document,
    School,
    SchoolFiscalYearStatus,
    SchoolSite,
)
from eidp.fiscal_year import current_fiscal_year
from eidp.reports import (
    compute_coverage,
    compute_extraction,
    compute_gaps,
    compute_ship_readiness,
    gap_report_for_export,
)


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def _school(session: Session, id: int, pref: str, school_type: str = "専門学校") -> School:
    s = School(
        id=id,
        prefecture=pref,
        corporation_name=f"C{id}",
        school_name=f"S{id}",
        school_type=school_type,
        status="active",
    )
    session.add(s)
    session.flush()
    return s


def _dept(session: Session, id: int, school_id: int) -> Department:
    d = Department(id=id, school_id=school_id, canonical_name=f"D{id}")
    session.add(d)
    session.flush()
    return d


def _doc(
    session: Session,
    id: int,
    school_id: int,
    fy: int,
    status: str = "ingested",
    pdf_type: str | None = "target",
) -> Document:
    d = Document(
        id=id,
        school_id=school_id,
        source_url=f"https://x/{id}.pdf",
        fiscal_year=fy,
        ingest_status=status,
        pdf_type=pdf_type,
    )
    session.add(d)
    session.flush()
    return d


def _yearly(
    session: Session,
    id: int,
    dept_id: int,
    fy: int,
    *,
    document_id: int | None = None,
    capacity: int | None = 80,
    enrollment: int | None = 70,
) -> DepartmentYearly:
    y = DepartmentYearly(
        id=id,
        department_id=dept_id,
        document_id=document_id,
        fiscal_year=fy,
        revision=1,
        is_current=True,
        capacity=capacity,
        enrollment=enrollment,
    )
    session.add(y)
    session.flush()
    return y


# --- current_fiscal_year ---------------------------------------------------


def test_current_fiscal_year_april_returns_calendar_year() -> None:
    assert current_fiscal_year(datetime(2026, 4, 1)) == 2026


def test_current_fiscal_year_march_returns_prev_calendar_year() -> None:
    assert current_fiscal_year(datetime(2026, 3, 31)) == 2025


# --- coverage --------------------------------------------------------------


def test_coverage_counts_only_active_schools_of_requested_type() -> None:
    s = _session()
    _school(s, 1, "東京", "専門学校")
    _school(s, 2, "東京", "大学")  # excluded
    s.flush()

    rep = compute_coverage(s, school_type="専門学校", fiscal_year=2026)
    assert rep.totals.schools_total == 1


def test_coverage_aggregates_url_pdf_and_extraction() -> None:
    s = _session()
    _school(s, 1, "東京")
    _school(s, 2, "東京")
    _school(s, 3, "大阪")
    s.add(SchoolSite(school_id=1, url="https://a", verified=True))
    s.add(SchoolSite(school_id=2, url="https://b", verified=False))
    _doc(s, 10, 1, 2026, "ingested", pdf_type="target")
    d1 = _dept(s, 100, 1)
    _yearly(s, 1000, d1.id, 2026, document_id=10, capacity=80)
    s.flush()

    rep = compute_coverage(s, school_type="専門学校", fiscal_year=2026)
    assert rep.totals.schools_total == 3
    assert rep.totals.schools_with_url == 2
    assert rep.totals.schools_with_verified_url == 1
    assert rep.totals.schools_with_any_pdf == 1
    assert rep.totals.schools_with_target_pdf_any_fy == 1
    assert rep.totals.schools_with_target_pdf_current_fy == 1
    assert rep.totals.schools_with_current_fy_doc == 1
    assert rep.totals.schools_with_current_fy_extracted == 1
    pref_map = {p.prefecture: p for p in rep.by_prefecture}
    assert pref_map["東京"].schools_total == 2
    assert pref_map["大阪"].schools_total == 1


def test_coverage_target_pdf_excludes_non_target_and_failed() -> None:
    s = _session()
    _school(s, 1, "東京")
    _school(s, 2, "東京")
    _school(s, 3, "東京")
    _doc(s, 10, 1, 2026, "ingested", pdf_type="non_target")
    _doc(s, 11, 2, 2026, "parse_failed", pdf_type="target")
    _doc(s, 12, 3, 2026, "ingested", pdf_type="target")
    s.flush()

    rep = compute_coverage(s, school_type="専門学校", fiscal_year=2026)
    assert rep.totals.schools_with_any_pdf == 3
    assert rep.totals.schools_with_target_pdf_any_fy == 1
    assert rep.totals.schools_with_target_pdf_current_fy == 1


def test_coverage_target_pdf_distinguishes_any_fy_vs_current_fy() -> None:
    """Reviewer fix: target_pdf_rate must split any-FY (discovery health)
    vs current-FY target coverage; they were conflated before."""
    s = _session()
    _school(s, 1, "東京")  # only 2025 target → counts in any_fy, not current_fy
    _school(s, 2, "東京")  # has 2026 target → counts in both
    _doc(s, 10, 1, 2025, "ingested", pdf_type="target")
    _doc(s, 11, 2, 2026, "ingested", pdf_type="target")
    s.flush()

    rep = compute_coverage(s, school_type="専門学校", fiscal_year=2026)
    assert rep.totals.schools_with_target_pdf_any_fy == 2
    assert rep.totals.schools_with_target_pdf_current_fy == 1


def test_coverage_default_fiscal_year_uses_configured_target(monkeypatch: pytest.MonkeyPatch) -> None:
    s = _session()
    _school(s, 1, "東京")
    _doc(s, 10, 1, 2099, "ingested", pdf_type="target")
    s.flush()
    monkeypatch.setattr(coverage_module.settings, "target_fiscal_year", 2099)

    rep = compute_coverage(s, school_type="専門学校")

    assert rep.fiscal_year == 2099
    assert rep.totals.schools_with_target_pdf_current_fy == 1


def test_coverage_extraction_requires_capacity_not_null() -> None:
    s = _session()
    _school(s, 1, "東京")
    _doc(s, 10, 1, 2026, "ingested")
    d1 = _dept(s, 100, 1)
    _yearly(s, 1000, d1.id, 2026, document_id=10, capacity=None)
    s.flush()

    rep = compute_coverage(s, school_type="専門学校", fiscal_year=2026)
    assert rep.totals.schools_with_current_fy_doc == 1
    assert rep.totals.schools_with_current_fy_extracted == 0


def test_gap_report_for_export_uses_target_fy_not_historical_data() -> None:
    s = _session()
    _school(s, 1, "東京")
    _school(s, 2, "東京")
    s.add(SchoolSite(school_id=1, url="https://a", verified=True))
    _doc(s, 10, 1, 2025, "ingested", pdf_type="target")
    d1 = _dept(s, 100, 1)
    _yearly(s, 1000, d1.id, 2025, document_id=10, capacity=80)
    s.add(
        SchoolFiscalYearStatus(
            school_id=1,
            fiscal_year=2026,
            url_status="pref_url",
            pdf_status="rejected_stale",
            extract_status="none",
            blocking_reason="stale_pdf_only",
            evidence_level="pdf_text",
            excel_ready=False,
        )
    )
    s.flush()

    rep = gap_report_for_export(s, fiscal_year=2026, school_type="専門学校")

    assert rep.total_schools == 2
    assert rep.schools_with_url == 1
    assert rep.no_url_schools == 1
    assert rep.target_pdf_schools == 0
    assert rep.stale_fallback_schools == 1
    assert rep.missing_target_pdf_schools == 2
    assert rep.extracted_schools == 0
    assert rep.excel_ready_schools == 0
    assert rep.target_yearly_rows == 0
    assert rep.has_target_year_data is False


def test_gap_report_for_export_counts_ready_target_year_data() -> None:
    s = _session()
    _school(s, 1, "東京")
    s.add(SchoolSite(school_id=1, url="https://a", verified=True))
    _doc(s, 9, 1, 2025, "ingested", pdf_type="target")
    _doc(s, 10, 1, 2026, "ingested", pdf_type="target")
    d1 = _dept(s, 100, 1)
    _yearly(s, 1000, d1.id, 2026, document_id=10, capacity=80)
    s.add(
        SchoolFiscalYearStatus(
            school_id=1,
            fiscal_year=2026,
            url_status="pref_url",
            pdf_status="confirmed_target",
            extract_status="parsed",
            evidence_level="pdf_text",
            excel_ready=True,
        )
    )
    s.flush()

    rep = gap_report_for_export(s, fiscal_year=2026, school_type="専門学校")

    assert rep.target_pdf_schools == 1
    assert rep.stale_fallback_schools == 0
    assert rep.extracted_schools == 1
    assert rep.excel_ready_schools == 1
    assert rep.target_yearly_rows == 1
    assert rep.target_pdf_rate == pytest.approx(1.0)
    assert rep.excel_ready_rate == pytest.approx(1.0)


# --- ship readiness --------------------------------------------------------


def test_ship_readiness_requires_strict_target_pdf_and_manual_workload_thresholds() -> None:
    s = _session()
    for school_id in range(1, 11):
        _school(s, school_id, "東京")
        s.add(SchoolSite(school_id=school_id, url=f"https://school{school_id}.example/"))
        pdf_status = "confirmed_target" if school_id <= 5 else "publication_lag" if school_id <= 7 else "none"
        s.add(
            SchoolFiscalYearStatus(
                school_id=school_id,
                fiscal_year=2026,
                pdf_status=pdf_status,
                excel_ready=school_id <= 4,
            )
        )
    for school_id in range(1, 6):
        _doc(s, 100 + school_id, school_id, 2026, "ingested", pdf_type="target")
        dept = _dept(s, 200 + school_id, school_id)
        _yearly(s, 300 + school_id, dept.id, 2026, document_id=100 + school_id)
    s.flush()

    rep = compute_ship_readiness(s, fiscal_year=2026, school_type="専門学校")

    assert rep.total_schools == 10
    assert rep.strict_target_pdf_schools == 5
    assert rep.strict_target_pdf_rate == pytest.approx(0.5)
    assert rep.operator_reviewable_schools == 7
    assert rep.operator_reviewable_rate == pytest.approx(0.7)
    assert rep.estimated_manual_workload_rate == pytest.approx(0.3)
    assert rep.excel_ready_schools == 4
    assert rep.ok is False
    assert {criterion.name: criterion.passed for criterion in rep.criteria} == {
        "strict_target_pdf_auto_acquisition": False,
        "estimated_manual_workload": True,
        "excel_ready": False,
    }


def test_ship_readiness_passes_when_final_business_thresholds_are_met() -> None:
    s = _session()
    for school_id in range(1, 11):
        _school(s, school_id, "東京")
        s.add(SchoolSite(school_id=school_id, url=f"https://school{school_id}.example/"))
        s.add(
            SchoolFiscalYearStatus(
                school_id=school_id,
                fiscal_year=2026,
                pdf_status="confirmed_target" if school_id <= 7 else "none",
                excel_ready=school_id <= 7,
            )
        )
    for school_id in range(1, 8):
        _doc(s, 100 + school_id, school_id, 2026, "ingested", pdf_type="target")
        dept = _dept(s, 200 + school_id, school_id)
        _yearly(s, 300 + school_id, dept.id, 2026, document_id=100 + school_id)
    s.flush()

    rep = compute_ship_readiness(s, fiscal_year=2026, school_type="専門学校")

    assert rep.strict_target_pdf_rate == pytest.approx(0.7)
    assert rep.estimated_manual_workload_rate == pytest.approx(0.3)
    assert rep.excel_ready_rate == pytest.approx(0.7)
    assert rep.ok is True


# --- extraction ------------------------------------------------------------


def test_extraction_rate_zero_when_no_documents() -> None:
    s = _session()
    rep = compute_extraction(s, fiscal_year=2026)
    assert rep.documents_ingested == 0
    assert rep.extraction_rate == 0.0


def test_extraction_rate_counts_distinct_documents_with_yearly() -> None:
    s = _session()
    _school(s, 1, "東京")
    _doc(s, 10, 1, 2026, "ingested")
    _doc(s, 11, 1, 2026, "ingested")
    _doc(s, 12, 1, 2026, "parse_failed")  # not counted in ingested
    d1 = _dept(s, 100, 1)
    _yearly(s, 1000, d1.id, 2026, document_id=10)
    s.flush()

    rep = compute_extraction(s, fiscal_year=2026)
    assert rep.documents_ingested == 2
    assert rep.documents_with_yearly_rows == 1
    assert rep.extraction_rate == pytest.approx(0.5)


def test_extraction_outliers_flag_large_delta_vs_prev_fy() -> None:
    s = _session()
    _school(s, 1, "東京")
    d1 = _dept(s, 100, 1)
    _yearly(s, 1000, d1.id, 2025, enrollment=100, capacity=100)
    _yearly(s, 1001, d1.id, 2026, enrollment=200, capacity=100)  # +100%
    s.flush()

    rep = compute_extraction(s, fiscal_year=2026, delta_threshold_pct=50.0)
    assert len(rep.delta_outliers) == 1
    o = rep.delta_outliers[0]
    assert o.department_id == d1.id
    assert o.prev_value == 100
    assert o.curr_value == 200
    assert o.delta_pct == pytest.approx(100.0)


def test_extraction_outliers_skip_when_within_threshold() -> None:
    s = _session()
    _school(s, 1, "東京")
    d1 = _dept(s, 100, 1)
    _yearly(s, 1000, d1.id, 2025, enrollment=100)
    _yearly(s, 1001, d1.id, 2026, enrollment=120)  # +20%
    s.flush()

    rep = compute_extraction(s, fiscal_year=2026, delta_threshold_pct=50.0)
    assert rep.delta_outliers == ()


# --- gaps ------------------------------------------------------------------


def test_gaps_url_lists_schools_without_school_site() -> None:
    s = _session()
    _school(s, 1, "東京")
    _school(s, 2, "大阪")
    s.add(SchoolSite(school_id=1, url="https://a", verified=False))
    s.flush()

    rep = compute_gaps(s, "url", school_type="専門学校")
    assert rep.total == 1
    assert rep.sample[0].school_id == 2
    assert rep.by_reason == {"no_school_site": 1}


def test_gaps_pdf_distinguishes_site_known_vs_no_site() -> None:
    s = _session()
    _school(s, 1, "東京")
    _school(s, 2, "東京")
    s.add(SchoolSite(school_id=1, url="https://a", verified=False))
    s.flush()

    rep = compute_gaps(s, "pdf", school_type="専門学校", fiscal_year=2026)
    assert rep.total == 2
    assert rep.by_reason == {"site_known_no_pdf": 1, "no_site_no_pdf": 1}


def test_gaps_pdf_classifies_stale_non_target_mismatch_failed() -> None:
    s = _session()
    # School 1: only prev-year target ingested → stale_pdf_only
    _school(s, 1, "東京")
    _doc(s, 10, 1, 2025, "ingested", pdf_type="target")
    # School 2: only non_target ingested → non_target_only
    _school(s, 2, "東京")
    _doc(s, 11, 2, 2026, "ingested", pdf_type="non_target")
    # School 3: only school_mismatch → mismatch_only
    _school(s, 3, "東京")
    _doc(s, 12, 3, 2026, "school_mismatch", pdf_type="target")
    # School 4: only parse_failed → parse_failed_only
    _school(s, 4, "東京")
    _doc(s, 13, 4, 2026, "parse_failed", pdf_type="target")
    # School 5: target ingested for current FY → no gap
    _school(s, 5, "東京")
    _doc(s, 14, 5, 2026, "ingested", pdf_type="target")
    s.flush()

    rep = compute_gaps(s, "pdf", school_type="専門学校", fiscal_year=2026)
    assert rep.by_reason == {
        "stale_pdf_only": 1,
        "non_target_only": 1,
        "mismatch_only": 1,
        "parse_failed_only": 1,
    }
    assert rep.total == 4


def test_gaps_pdf_classifies_extended_status_buckets() -> None:
    """Reviewer fix: ocr_pending, support_only, no_file, permanent_error,
    transient_error, in_progress used to silently fall to non_target_only.
    Each must now report its own reason."""
    s = _session()
    cases = [
        ("ocr_pending", "ocr_pending_only"),
        ("support_only", "support_only"),
        ("no_file", "no_file_only"),
        ("permanent_error", "permanent_error_only"),
        ("transient_error", "transient_error_only"),
        ("in_progress", "in_progress_only"),
    ]
    for i, (status, _) in enumerate(cases, start=1):
        _school(s, i, "東京")
        _doc(s, 100 + i, i, 2026, status=status, pdf_type="target")
    s.flush()

    rep = compute_gaps(s, "pdf", school_type="専門学校", fiscal_year=2026)
    expected = {expected_reason: 1 for _, expected_reason in cases}
    assert rep.by_reason == expected
    assert rep.total == len(cases)


def test_gaps_pdf_default_fy_does_not_crash() -> None:
    s = _session()
    _school(s, 1, "東京")
    s.flush()

    rep = compute_gaps(s, "pdf", school_type="専門学校")
    assert rep.total == 1
    assert rep.by_reason == {"no_site_no_pdf": 1}


def test_gaps_pdf_default_fiscal_year_uses_configured_target(monkeypatch: pytest.MonkeyPatch) -> None:
    s = _session()
    _school(s, 1, "東京")
    _doc(s, 10, 1, 2099, "ingested", pdf_type="target")
    s.flush()
    monkeypatch.setattr(gaps_module.settings, "target_fiscal_year", 2099)

    rep = compute_gaps(s, "pdf", school_type="専門学校")

    assert rep.total == 0
    assert rep.by_reason == {}


def test_gaps_extraction_lists_ingested_docs_without_yearly() -> None:
    s = _session()
    _school(s, 1, "東京")
    _doc(s, 10, 1, 2026, "ingested")  # no yearly rows
    _doc(s, 11, 1, 2026, "ingested")
    d1 = _dept(s, 100, 1)
    _yearly(s, 1000, d1.id, 2026, document_id=11)
    s.flush()

    rep = compute_gaps(s, "extraction", fiscal_year=2026)
    assert rep.total == 1
    assert rep.sample[0].detail == "document_id=10"


def test_gaps_extraction_requires_fiscal_year() -> None:
    s = _session()
    with pytest.raises(ValueError):
        compute_gaps(s, "extraction")


def test_gaps_competition_reads_csv(tmp_path: Path) -> None:
    csv_path = tmp_path / "gap.csv"
    csv_path.write_text(
        "gap_reason,gap_detail,sheet,row,block_id,school_name,dept_name,duration,school_id,matched_via\n"
        "school_no_document,,A,1,0,東京X,X科,2年制,1,exact\n"
        "school_missing,,A,2,0,東京Y,Y科,3年制,,unmatched\n",
        encoding="utf-8",
    )
    s = _session()
    rep = compute_gaps(s, "competition", competition_csv=csv_path)
    assert rep.total == 2
    assert rep.by_reason == {"school_no_document": 1, "school_missing": 1}
    assert rep.sample[0].school_id == 1
    assert rep.sample[1].school_id is None


def test_gaps_competition_default_uses_exporter_gap_name(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    gap_dir = tmp_path / "output"
    gap_dir.mkdir()
    csv_path = gap_dir / "競合校gap-report.csv"
    csv_path.write_text(
        "gap_reason,gap_detail,sheet,row,block_id,school_name,dept_name,duration,school_id,matched_via\n"
        "school_no_document,,A,1,0,東京X,X科,2年制,1,exact\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    s = _session()
    rep = compute_gaps(s, "competition")
    assert rep.total == 1
    assert rep.by_reason == {"school_no_document": 1}


def test_gaps_competition_missing_csv_is_visible(tmp_path: Path) -> None:
    s = _session()
    missing = tmp_path / "missing.csv"

    rep = compute_gaps(s, "competition", competition_csv=missing)

    assert rep.total == 1
    assert rep.by_reason == {"_csv_missing": 1}
    assert rep.sample[0].detail == str(missing)


def test_gaps_unknown_kind_raises() -> None:
    s = _session()
    with pytest.raises(ValueError):
        compute_gaps(s, "bogus")  # type: ignore[arg-type]
