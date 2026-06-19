from __future__ import annotations

from collections.abc import Iterable, Mapping
from enum import StrEnum

from eidp.domain.document_kind import DOCUMENT_KIND_JA_LABELS, LEGACY_PDF_TYPE_TO_DOCUMENT_KIND, DocumentKind
from eidp.domain.review_task_kind import (
    LEGACY_BLOCKING_REASON_TO_REVIEW_TASK_KIND,
    REVIEW_TASK_KIND_JA_LABELS,
    REVIEW_TASK_NEXT_ACTIONS,
    ReviewTaskKind,
)
from eidp.domain.source_trust import (
    DISCOVERY_METHOD_TRUST_TIERS,
    EVIDENCE_SOURCE_TYPE_JA_LABELS,
    REGISTERED_DISCOVERY_METHODS,
    SOURCE_TRUST_POLICIES,
    EvidenceSourceType,
    EvidenceTrustTier,
    trust_policy_for_discovery_method,
)
from eidp.domain.workflow_status import (
    LEGACY_BLOCKING_REASON_TO_WORKFLOW_STATUS,
    LEGACY_EXTRACT_STATUS_TO_EXTRACTION_STATUS,
    LEGACY_PDF_STATUS_TO_TARGET_DOCUMENT_STATUS,
    LEGACY_URL_STATUS_TO_SITE_ENTRY_STATUS,
    WORKFLOW_STATUS_JA_LABELS,
    WORKFLOW_STATUS_NEXT_ACTIONS,
    ExtractionStatus,
    ProgramReconciliationStatus,
    SiteEntryStatus,
    TargetDocumentStatus,
    WorkbookReadinessStatus,
    WorkflowStatus,
)


def _enum_values(enum_cls: type[StrEnum]) -> set[StrEnum]:
    return set(enum_cls)


def _workflow_statuses() -> set[WorkflowStatus]:
    return (
        set(SiteEntryStatus)
        | set(TargetDocumentStatus)
        | set(ExtractionStatus)
        | set(ProgramReconciliationStatus)
        | set(WorkbookReadinessStatus)
    )


def _assert_full_mapping(enum_values: Iterable[StrEnum], mapping: Mapping[StrEnum, object]) -> None:
    assert set(enum_values) == set(mapping)
    assert all(mapping[value] for value in enum_values)


def test_all_document_kinds_have_operator_labels() -> None:
    _assert_full_mapping(_enum_values(DocumentKind), DOCUMENT_KIND_JA_LABELS)


def test_legacy_pdf_types_map_to_registered_document_kinds() -> None:
    assert LEGACY_PDF_TYPE_TO_DOCUMENT_KIND["target"] is DocumentKind.TARGET_APPLICATION_FORM
    assert LEGACY_PDF_TYPE_TO_DOCUMENT_KIND["image_only"] is DocumentKind.TARGET_APPLICATION_FORM
    assert set(LEGACY_PDF_TYPE_TO_DOCUMENT_KIND.values()) <= set(DocumentKind)


def test_all_review_task_kinds_have_labels_and_next_actions() -> None:
    _assert_full_mapping(_enum_values(ReviewTaskKind), REVIEW_TASK_KIND_JA_LABELS)
    _assert_full_mapping(_enum_values(ReviewTaskKind), REVIEW_TASK_NEXT_ACTIONS)


def test_legacy_blocking_reasons_map_to_review_tasks() -> None:
    expected = {
        "no_url",
        "no_target_pdf",
        "publication_lag_latest_public",
        "target_year_unverified",
        "tls_certificate_verify_failed",
        "stale_pdf_only",
        "ocr_pending",
        "parse_failed",
        "not_extracted",
        "review_required",
        "dept_change_review",
    }

    assert expected <= set(LEGACY_BLOCKING_REASON_TO_REVIEW_TASK_KIND)
    assert set(LEGACY_BLOCKING_REASON_TO_REVIEW_TASK_KIND.values()) <= set(ReviewTaskKind)


def test_all_source_trust_tiers_have_policies() -> None:
    _assert_full_mapping(_enum_values(EvidenceTrustTier), SOURCE_TRUST_POLICIES)
    assert all(policy.tier is tier for tier, policy in SOURCE_TRUST_POLICIES.items())


def test_all_evidence_source_types_have_labels() -> None:
    _assert_full_mapping(_enum_values(EvidenceSourceType), EVIDENCE_SOURCE_TYPE_JA_LABELS)


def test_external_research_methods_are_not_auto_accepted() -> None:
    candidate_methods = {
        "web_search",
        "external_search",
        "firecrawl_map",
        "scrapling_stealth",
        "agent_reach",
        "corporation_pattern",
    }

    assert candidate_methods <= REGISTERED_DISCOVERY_METHODS
    for method in candidate_methods:
        policy = trust_policy_for_discovery_method(method)
        assert policy.tier is EvidenceTrustTier.T4_SEARCH_CANDIDATE
        assert policy.auto_accept_allowed is False
        assert policy.requires_official_confirmation is True


def test_known_discovery_methods_have_trust_tiers() -> None:
    known_methods = {
        "prefecture_aggregator",
        "seed_csv",
        "corporation_pattern",
        "school_domain_override",
        "web_search",
        "operator_manual",
        "scrapling_stealth",
        "firecrawl_map",
        "agent_reach",
    }

    assert known_methods <= REGISTERED_DISCOVERY_METHODS
    assert set(DISCOVERY_METHOD_TRUST_TIERS.values()) <= set(EvidenceTrustTier)


def test_workflow_statuses_have_labels_and_next_actions() -> None:
    statuses = _workflow_statuses()

    assert statuses == set(WORKFLOW_STATUS_JA_LABELS)
    assert statuses == set(WORKFLOW_STATUS_NEXT_ACTIONS)
    assert all(WORKFLOW_STATUS_JA_LABELS[status] for status in statuses)
    assert all(WORKFLOW_STATUS_NEXT_ACTIONS[status] for status in statuses)


def test_legacy_statuses_map_to_workflow_statuses() -> None:
    assert LEGACY_URL_STATUS_TO_SITE_ENTRY_STATUS["no_url"] is SiteEntryStatus.MISSING
    assert LEGACY_PDF_STATUS_TO_TARGET_DOCUMENT_STATUS["target_year_unverified"] is (
        TargetDocumentStatus.YEAR_UNVERIFIED
    )
    assert LEGACY_EXTRACT_STATUS_TO_EXTRACTION_STATUS["parse_failed"] is ExtractionStatus.PARSE_FAILED
    assert set(LEGACY_BLOCKING_REASON_TO_WORKFLOW_STATUS.values()) <= _workflow_statuses()
