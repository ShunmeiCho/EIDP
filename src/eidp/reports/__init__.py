"""Acceptance-criteria report module.

Provides verifiable metrics for EIDP completion progress:
- coverage: school/URL/PDF coverage rollup by prefecture
- extraction: fiscal-year extraction rate + prev-year delta outliers
- gaps: actionable gap counters by kind (url|pdf|extraction|competition)
"""

from eidp.reports.coverage import CoverageReport, ExportGapReport, compute_coverage, gap_report_for_export
from eidp.reports.extraction import ExtractionReport, compute_extraction
from eidp.reports.gaps import GapsReport, compute_gaps
from eidp.reports.ship_readiness import ShipReadinessReport, compute_ship_readiness

__all__ = [
    "CoverageReport",
    "ExportGapReport",
    "ExtractionReport",
    "GapsReport",
    "ShipReadinessReport",
    "compute_coverage",
    "compute_extraction",
    "compute_gaps",
    "compute_ship_readiness",
    "gap_report_for_export",
]
