"""Typed identities recorded by EIDP audit events."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class IdentitySource(StrEnum):
    TRUSTED_PROXY = "trusted_proxy"
    CONFIGURED_FALLBACK = "configured_fallback"
    SYSTEM = "system"
    LEGACY_UNSPECIFIED = "legacy_unspecified"


@dataclass(frozen=True)
class ResolvedIdentity:
    actor: str
    source: IdentitySource


SYSTEM_IDENTITY = ResolvedIdentity(actor="system", source=IdentitySource.SYSTEM)
LEGACY_OPERATOR_IDENTITY = ResolvedIdentity(
    actor="operator",
    source=IdentitySource.LEGACY_UNSPECIFIED,
)
