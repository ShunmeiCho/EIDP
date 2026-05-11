"""Shared operator-facing school scope constants."""

from __future__ import annotations

# v1 operator workflows ship for vocational schools only. Universities remain
# out of scope here so UI coverage denominators match the ship-gate contract.
OPERATOR_SCHOOL_TYPE_SCOPE: str | None = "専門学校"
OPERATOR_SCHOOL_SCOPE_LABEL = "専門学校"
