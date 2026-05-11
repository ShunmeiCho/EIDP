"""Summarize PDF discovery evidence into release-relevant failure buckets."""

from __future__ import annotations

import json
import re
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse


@dataclass(frozen=True)
class EvidenceScopeSite:
    """One expected school/site in a bounded discovery run."""

    school_id: int
    school_name: str = ""
    site_url: str = ""


@dataclass(frozen=True)
class SchoolEvidenceSummary:
    """Per-school PDF discovery evidence bucket."""

    school_id: int
    school_name: str
    site_url: str
    bucket: str
    candidate_count: int
    top_reasons: list[tuple[str, int]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "school_id": self.school_id,
            "school_name": self.school_name,
            "site_url": self.site_url,
            "bucket": self.bucket,
            "candidate_count": self.candidate_count,
            "top_reasons": [[reason, count] for reason, count in self.top_reasons],
        }


@dataclass(frozen=True)
class PdfDiscoveryEvidenceSummary:
    """Rollup used to distinguish URL coverage failures from PDF discovery failures."""

    evidence_rows: int
    schools_with_evidence: int
    site_scope_schools: int
    school_bucket_counts: dict[str, int]
    reason_counts: dict[str, int]
    pdf_type_counts: dict[str, int]
    pattern_type_counts: dict[str, int]
    top_hosts: dict[str, int]
    school_summaries: list[SchoolEvidenceSummary]

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_rows": self.evidence_rows,
            "schools_with_evidence": self.schools_with_evidence,
            "site_scope_schools": self.site_scope_schools,
            "school_bucket_counts": self.school_bucket_counts,
            "reason_counts": self.reason_counts,
            "pdf_type_counts": self.pdf_type_counts,
            "pattern_type_counts": self.pattern_type_counts,
            "top_hosts": self.top_hosts,
            "school_summaries": [summary.to_dict() for summary in self.school_summaries],
        }


def load_pdf_discovery_evidence(evidence_path: Path) -> list[dict[str, Any]]:
    """Load append-only ``discover-pdfs`` evidence JSONL."""

    rows: list[dict[str, Any]] = []
    for line in evidence_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def load_pdf_discovery_site_scope(
    session: Any,
    *,
    prefecture: str = "",
    discovery_method: str = "",
    school_type: str | None = None,
) -> list[EvidenceScopeSite]:
    """Load expected crawlable school sites from the configured DB."""

    from eidp.db.models import School, SchoolSite

    query = session.query(SchoolSite, School).join(School, School.id == SchoolSite.school_id)
    if prefecture:
        query = query.filter(School.prefecture == prefecture)
    if discovery_method:
        query = query.filter(SchoolSite.discovery_method == discovery_method)
    if school_type is not None:
        query = query.filter(School.school_type == school_type)

    return [
        EvidenceScopeSite(
            school_id=int(site.school_id),
            school_name=str(school.school_name or ""),
            site_url=str(site.url or ""),
        )
        for site, school in query.order_by(SchoolSite.school_id.asc()).all()
    ]


def summarize_pdf_discovery_evidence(
    rows: list[dict[str, Any]],
    *,
    site_scope: list[EvidenceScopeSite] | None = None,
) -> PdfDiscoveryEvidenceSummary:
    """Summarize evidence rows into school-level RCA buckets."""

    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        school_id = _int_or_none(row.get("school_id"))
        if school_id is not None:
            grouped[school_id].append(row)

    scope_by_school = {site.school_id: site for site in site_scope or []}
    school_ids = sorted(set(grouped) | set(scope_by_school))
    school_summaries: list[SchoolEvidenceSummary] = []
    for school_id in school_ids:
        school_rows = grouped.get(school_id, [])
        site = scope_by_school.get(school_id)
        school_summaries.append(
            SchoolEvidenceSummary(
                school_id=school_id,
                school_name=site.school_name if site else "",
                site_url=site.site_url if site else "",
                bucket=_classify_school_bucket(school_rows),
                candidate_count=len(school_rows),
                top_reasons=_reason_counter(school_rows).most_common(5),
            )
        )

    bucket_counts = Counter(summary.bucket for summary in school_summaries)
    return PdfDiscoveryEvidenceSummary(
        evidence_rows=len(rows),
        schools_with_evidence=len(grouped),
        site_scope_schools=len(scope_by_school) if site_scope is not None else len(grouped),
        school_bucket_counts=dict(sorted(bucket_counts.items())),
        reason_counts=dict(_reason_counter(rows).most_common()),
        pdf_type_counts=dict(_pdf_type_counter(rows).most_common()),
        pattern_type_counts=dict(_pattern_type_counter(rows).most_common()),
        top_hosts=dict(_host_counter(rows).most_common(20)),
        school_summaries=school_summaries,
    )


def render_pdf_discovery_evidence_summary(summary: PdfDiscoveryEvidenceSummary) -> str:
    """Render a deterministic JSON summary for CLI and audit logs."""

    return json.dumps(summary.to_dict(), ensure_ascii=False, indent=2, sort_keys=True)


def _classify_school_bucket(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "no_evidence"
    if any(str(row.get("reason") or "") == "accepted_downloaded" for row in rows):
        return "accepted_target_pdf"
    if any(_is_old_year_target(row) for row in rows):
        return "publication_lag_or_old_target_pdf"
    if any(str(row.get("reason") or "") == "target_fiscal_year_not_detected" for row in rows):
        return "target_form_without_year_evidence"
    if any(_is_image_only_review_candidate(row) for row in rows):
        return "target_form_without_year_evidence"
    if any(str(row.get("reason") or "") == "no_candidates_found" for row in rows):
        return "no_pdf_candidates"
    if all(str(row.get("reason") or "") == "discovery_error" for row in rows) and any(
        _is_tls_certificate_verify_failure(row) for row in rows
    ):
        return "tls_certificate_verify_failed"
    if all(str(row.get("reason") or "") == "discovery_error" for row in rows):
        return "site_fetch_error_only"
    if any(str(row.get("reason") or "") == "discovery_error" for row in rows):
        return "mixed_with_site_fetch_error"
    return "non_target_candidates_only"


def _is_old_year_target(row: dict[str, Any]) -> bool:
    if not str(row.get("reason") or "").startswith("fiscal_year_mismatch:"):
        return False
    pdf_type = str(row.get("pdf_type") or "")
    if pdf_type == "target":
        return True
    return pdf_type == "image_only" and _has_stale_image_target_form_hint(row)


def _has_stale_image_target_form_hint(row: dict[str, Any]) -> bool:
    text = _candidate_hint_text(row)
    support_hint = any(token in text for token in ("修学支援", "修学の支援", "shugakushien", "syugakushien"))
    form_hint = any(token in text for token in ("機関要件", "確認申請", "申請書", "様式第2号", "様式2"))
    form_file_hint = bool(re.search(r"(?:^|[/_-])j20\d{2}[_-]?0?5[a-z]?(?:\.pdf|$)", text))
    return support_hint or form_hint or form_file_hint


def _is_image_only_review_candidate(row: dict[str, Any]) -> bool:
    if str(row.get("pdf_type") or "") != "image_only":
        return False
    text = _candidate_hint_text(row)
    return any(
        token in text
        for token in (
            "申請内容",
            "高等教育",
            "無償化",
            "修学支援",
            "修学の支援",
            "koutou",
            "hutankeigen",
            "shugakushien",
            "syugakushien",
        )
    )


def _candidate_hint_text(row: dict[str, Any]) -> str:
    text = unicodedata.normalize(
        "NFKC",
        f"{row.get('anchor_text') or ''} {row.get('pdf_url') or ''} {unquote(str(row.get('pdf_url') or ''))}",
    ).lower()
    return text


def _is_tls_certificate_verify_failure(row: dict[str, Any]) -> bool:
    extra = row.get("extra")
    error = ""
    if isinstance(extra, dict):
        error = str(extra.get("error") or "")
    haystack = f"{row.get('reason') or ''} {error}".lower()
    return "certificate_verify_failed" in haystack or "certificate verify failed" in haystack


def _reason_counter(rows: list[dict[str, Any]]) -> Counter[str]:
    return Counter(str(row.get("reason") or "") for row in rows)


def _pdf_type_counter(rows: list[dict[str, Any]]) -> Counter[str]:
    return Counter("null" if row.get("pdf_type") is None else str(row.get("pdf_type")) for row in rows)


def _pattern_type_counter(rows: list[dict[str, Any]]) -> Counter[str]:
    return Counter(str(row.get("pattern_type") or "") for row in rows)


def _host_counter(rows: list[dict[str, Any]]) -> Counter[str]:
    return Counter(urlparse(str(row.get("pdf_url") or "")).netloc for row in rows)


def _int_or_none(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(str(value))
    except ValueError:
        return None
