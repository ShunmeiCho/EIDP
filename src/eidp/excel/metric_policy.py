"""Metric gate policy for the master-diff acceptance (Rung 1+).

Enrollment is the business-critical output (競合校の在校生数); it and 留学生数 are the
HARD gate. 定員 (capacity) diverges across sources -- master 収容定員 (authorized) vs the
確認申請書 生徒/学生総定員数 (reported) -- so it is a RECONCILIATION metric: surfaced for
operator/owner review, never a silent pass/fail and never auto-overwriting master.
卒業/中退 become gate metrics once the extractor produces them.
"""

from __future__ import annotations

__all__ = ["FUTURE_GATE_METRICS", "HARD_GATE_METRICS", "RECONCILIATION_METRICS"]

HARD_GATE_METRICS: frozenset[str] = frozenset({"enrollment", "intl_students"})
RECONCILIATION_METRICS: frozenset[str] = frozenset({"capacity"})
FUTURE_GATE_METRICS: frozenset[str] = frozenset({"graduates", "dropouts"})
