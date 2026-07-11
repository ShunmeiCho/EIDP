"""Canonical metric-label aliases for disclosure-table extraction.

Verified motivation: ``extractor.py`` hard-codes 生徒総定員/生徒実員 (seito), but
the 大原 part-5 表 uses 学生総定員数/学生実員 (gakusei); substring matching on the
seito spelling silently misses those rows. This module folds spelling variants and
common synonyms to a single canonical metric, and returns ``None`` for
teacher-staffing / non-target labels so they can never be misread as an enrollment
or capacity number.

Deployment-agnostic (no-regret): usable by both the current pipeline and the
proposed Linux/Web extractor.
"""

from __future__ import annotations

import unicodedata

__all__ = ["CanonicalMetric", "METRIC_ALIASES", "canonicalize_metric_label"]

CanonicalMetric = str

# canonical metric -> surface spellings observed in 機関要件確認申請書 / 情報公開 tables.
# NOTE: 入学定員 (annual admission quota) is deliberately a DISTINCT metric from
# 収容定員/総定員 (total capacity); conflating them would corrupt the capacity value.
METRIC_ALIASES: dict[CanonicalMetric, tuple[str, ...]] = {
    "capacity": ("生徒総定員数", "学生総定員数", "生徒総定員", "学生総定員", "収容定員", "総定員数", "総定員"),
    "admission_capacity": ("入学定員",),
    "enrollment": ("生徒実員", "学生実員", "在籍者数", "在籍学生数", "在籍生徒数", "実員"),
    "intl_students": ("うち留学生数", "うち外国人留学生数", "外国人留学生数", "留学生数"),
    "graduates": ("卒業者数",),
    "dropouts": ("退学者の数", "中途退学者数", "中退者数"),
}

# (alias, canonical) sorted by alias length desc so the most specific spelling wins
# (e.g. 学生総定員数 before 総定員; 学生実員 before 実員).
_ALIAS_INDEX: tuple[tuple[str, CanonicalMetric], ...] = tuple(
    sorted(
        ((alias, metric) for metric, aliases in METRIC_ALIASES.items() for alias in aliases),
        key=lambda pair: len(pair[0]),
        reverse=True,
    )
)


def _normalize(label: str | None) -> str:
    """NFKC-fold (full-width -> half-width) and strip all whitespace.

    Broken table cells emit spacing like "学 生 実 員"; removing whitespace lets the
    alias match survive that fragmentation.
    """
    if not label:
        return ""
    return "".join(unicodedata.normalize("NFKC", label).split())


def canonicalize_metric_label(label: str | None) -> CanonicalMetric | None:
    """Return the canonical metric for a table label, or ``None`` if not a target.

    Matching is longest-alias-first substring over the normalized label, so header
    cells that carry trailing units or merged text still resolve, while unknown
    labels (teacher counts, 分野, headers) return ``None`` rather than a wrong metric.
    """
    normed = _normalize(label)
    if not normed:
        return None
    for alias, metric in _ALIAS_INDEX:
        if alias in normed:
            return metric
    return None
