"""Acceptance-criteria report module.

Provides verifiable metrics for EIDP completion progress:
- coverage: school/URL/PDF coverage rollup by prefecture
- extraction: fiscal-year extraction rate + prev-year delta outliers
- gaps: actionable gap counters by kind (url|pdf|extraction|competition)
"""

from eidp.reports.coverage import CoverageReport, compute_coverage
from eidp.reports.extraction import ExtractionReport, compute_extraction
from eidp.reports.gaps import GapsReport, compute_gaps

__all__ = [
    "CoverageReport",
    "ExtractionReport",
    "GapsReport",
    "compute_coverage",
    "compute_extraction",
    "compute_gaps",
]
