"""Source trust tiers for official evidence and external candidates."""

from dataclasses import dataclass
from enum import StrEnum


class EvidenceSourceType(StrEnum):
    AUTHORITY_INDEX = "authority_index"
    OFFICIAL_SITE = "official_site"
    TARGET_DOCUMENT = "target_document"
    EXTRACTED_TEXT = "extracted_text"
    OCR_TEXT = "ocr_text"
    OPERATOR_DECISION = "operator_decision"
    WORKBOOK_EXPORT = "workbook_export"
    SEARCH_CANDIDATE = "search_candidate"
    EXTERNAL_RESEARCH = "external_research"
    UNTRUSTED = "untrusted"


class EvidenceTrustTier(StrEnum):
    T0_MEXT = "t0_mext"
    T1_AUTHORITY_INDEX = "t1_authority_index"
    T2_OFFICIAL_SITE = "t2_official_site"
    T3_OPERATOR_APPROVED = "t3_operator_approved"
    T4_SEARCH_CANDIDATE = "t4_search_candidate"
    T5_UNTRUSTED = "t5_untrusted"


@dataclass(frozen=True, slots=True)
class SourceTrustPolicy:
    tier: EvidenceTrustTier
    ja_label: str
    auto_accept_allowed: bool
    requires_official_confirmation: bool


SOURCE_TRUST_POLICIES: dict[EvidenceTrustTier, SourceTrustPolicy] = {
    EvidenceTrustTier.T0_MEXT: SourceTrustPolicy(
        tier=EvidenceTrustTier.T0_MEXT,
        ja_label="文科省公式",
        auto_accept_allowed=True,
        requires_official_confirmation=False,
    ),
    EvidenceTrustTier.T1_AUTHORITY_INDEX: SourceTrustPolicy(
        tier=EvidenceTrustTier.T1_AUTHORITY_INDEX,
        ja_label="確認機関公式索引",
        auto_accept_allowed=True,
        requires_official_confirmation=False,
    ),
    EvidenceTrustTier.T2_OFFICIAL_SITE: SourceTrustPolicy(
        tier=EvidenceTrustTier.T2_OFFICIAL_SITE,
        ja_label="学校・法人公式サイト",
        auto_accept_allowed=True,
        requires_official_confirmation=False,
    ),
    EvidenceTrustTier.T3_OPERATOR_APPROVED: SourceTrustPolicy(
        tier=EvidenceTrustTier.T3_OPERATOR_APPROVED,
        ja_label="担当者確認済",
        auto_accept_allowed=True,
        requires_official_confirmation=False,
    ),
    EvidenceTrustTier.T4_SEARCH_CANDIDATE: SourceTrustPolicy(
        tier=EvidenceTrustTier.T4_SEARCH_CANDIDATE,
        ja_label="検索・外部調査候補",
        auto_accept_allowed=False,
        requires_official_confirmation=True,
    ),
    EvidenceTrustTier.T5_UNTRUSTED: SourceTrustPolicy(
        tier=EvidenceTrustTier.T5_UNTRUSTED,
        ja_label="未信頼",
        auto_accept_allowed=False,
        requires_official_confirmation=True,
    ),
}

EVIDENCE_SOURCE_TYPE_JA_LABELS: dict[EvidenceSourceType, str] = {
    EvidenceSourceType.AUTHORITY_INDEX: "公式索引",
    EvidenceSourceType.OFFICIAL_SITE: "公式サイト",
    EvidenceSourceType.TARGET_DOCUMENT: "申請書PDF",
    EvidenceSourceType.EXTRACTED_TEXT: "抽出テキスト",
    EvidenceSourceType.OCR_TEXT: "OCRテキスト",
    EvidenceSourceType.OPERATOR_DECISION: "担当者判断",
    EvidenceSourceType.WORKBOOK_EXPORT: "Excel出力",
    EvidenceSourceType.SEARCH_CANDIDATE: "検索候補",
    EvidenceSourceType.EXTERNAL_RESEARCH: "外部調査",
    EvidenceSourceType.UNTRUSTED: "未信頼",
}

DISCOVERY_METHOD_TRUST_TIERS: dict[str, EvidenceTrustTier] = {
    "mext_authority_index": EvidenceTrustTier.T0_MEXT,
    "prefecture_aggregator": EvidenceTrustTier.T1_AUTHORITY_INDEX,
    "authority_index": EvidenceTrustTier.T1_AUTHORITY_INDEX,
    "official_site": EvidenceTrustTier.T2_OFFICIAL_SITE,
    "school_domain_override": EvidenceTrustTier.T3_OPERATOR_APPROVED,
    "seed_csv": EvidenceTrustTier.T3_OPERATOR_APPROVED,
    "operator_manual": EvidenceTrustTier.T3_OPERATOR_APPROVED,
    "corporation_pattern": EvidenceTrustTier.T4_SEARCH_CANDIDATE,
    "web_search": EvidenceTrustTier.T4_SEARCH_CANDIDATE,
    "external_search": EvidenceTrustTier.T4_SEARCH_CANDIDATE,
    "firecrawl_map": EvidenceTrustTier.T4_SEARCH_CANDIDATE,
    "scrapling_stealth": EvidenceTrustTier.T4_SEARCH_CANDIDATE,
    "agent_reach": EvidenceTrustTier.T4_SEARCH_CANDIDATE,
    "untrusted": EvidenceTrustTier.T5_UNTRUSTED,
}

REGISTERED_DISCOVERY_METHODS: frozenset[str] = frozenset(DISCOVERY_METHOD_TRUST_TIERS)


def trust_policy_for_discovery_method(discovery_method: str) -> SourceTrustPolicy:
    tier = DISCOVERY_METHOD_TRUST_TIERS.get(discovery_method, EvidenceTrustTier.T5_UNTRUSTED)
    return SOURCE_TRUST_POLICIES[tier]
