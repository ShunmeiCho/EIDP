"""Fail-closed identity resolution for Streamlit requests."""

from __future__ import annotations

import secrets
from collections.abc import Mapping

from eidp.config import Settings
from eidp.identity import IdentitySource, ResolvedIdentity

MAX_ACTOR_LENGTH = 50


class IdentityConfigurationError(RuntimeError):
    """Raised when the selected Web identity mode is unsafe to start."""


class IdentityRejectedError(RuntimeError):
    """Raised when a request does not carry a valid trusted identity."""


def validate_identity_configuration(config: Settings) -> None:
    """Reject incomplete trusted mode and invalid configured fallback actors."""
    if config.identity_mode == "trusted_proxy":
        if not config.proxy_shared_secret.get_secret_value():
            raise IdentityConfigurationError("identity configuration invalid")
        return

    actor = config.fallback_actor.strip()
    if not actor or len(actor) > MAX_ACTOR_LENGTH:
        raise IdentityConfigurationError("identity configuration invalid")


def resolve_request_identity(*, headers: Mapping[str, str], config: Settings) -> ResolvedIdentity:
    """Resolve one typed identity without ever trusting headers in fallback mode."""
    if config.identity_mode == "configured_fallback":
        actor = config.fallback_actor.strip()
        if not actor or len(actor) > MAX_ACTOR_LENGTH:
            raise IdentityConfigurationError("identity configuration invalid")
        return ResolvedIdentity(actor, IdentitySource.CONFIGURED_FALLBACK)

    supplied_secret = headers.get("X-EIDP-Proxy-Secret", "")
    expected_secret = config.proxy_shared_secret.get_secret_value()
    actor = headers.get("X-Auth-User", "").strip()
    secret_matches = secrets.compare_digest(supplied_secret, expected_secret)
    if not expected_secret or not secret_matches or not actor or len(actor) > MAX_ACTOR_LENGTH:
        raise IdentityRejectedError("request identity rejected")
    return ResolvedIdentity(actor, IdentitySource.TRUSTED_PROXY)


__all__ = [
    "IdentityConfigurationError",
    "IdentityRejectedError",
    "resolve_request_identity",
    "validate_identity_configuration",
]
