"""Fail-closed Web request identity contracts."""

from __future__ import annotations

from typing import Literal

import pytest

from eidp.config import Settings
from eidp.identity import IdentitySource, ResolvedIdentity
from eidp.web.identity import (
    IdentityConfigurationError,
    IdentityRejectedError,
    resolve_request_identity,
    validate_identity_configuration,
)


def identity_settings(
    *,
    mode: Literal["trusted_proxy", "configured_fallback"],
    fallback_actor: str = "operator",
    proxy_shared_secret: str = "",
) -> Settings:
    return Settings(
        identity_mode=mode,
        fallback_actor=fallback_actor,
        proxy_shared_secret=proxy_shared_secret,
        _env_file=None,
        _env_prefix="TEST_EIDP_",
    )


def test_fallback_ignores_spoofed_headers() -> None:
    config = identity_settings(mode="configured_fallback", fallback_actor="  pilot-operator  ")

    identity = resolve_request_identity(
        headers={"X-Auth-User": "attacker", "X-EIDP-Proxy-Secret": "spoof"},
        config=config,
    )

    assert identity == ResolvedIdentity("pilot-operator", IdentitySource.CONFIGURED_FALLBACK)


@pytest.mark.parametrize("fallback_actor", ["   ", "a" * 51])
def test_invalid_fallback_actor_fails_configuration(fallback_actor: str) -> None:
    config = identity_settings(mode="configured_fallback", fallback_actor=fallback_actor)

    with pytest.raises(IdentityConfigurationError, match="identity configuration invalid"):
        validate_identity_configuration(config)


def test_missing_trusted_secret_fails_configuration_without_secret_text() -> None:
    config = identity_settings(mode="trusted_proxy")

    with pytest.raises(IdentityConfigurationError, match="identity configuration invalid") as exc_info:
        validate_identity_configuration(config)

    assert "secret" not in str(exc_info.value).lower()


def test_valid_trusted_identity_uses_constant_time_secret_comparison(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, str]] = []

    def compare_digest(supplied: str, expected: str) -> bool:
        calls.append((supplied, expected))
        return supplied == expected

    monkeypatch.setattr("eidp.web.identity.secrets.compare_digest", compare_digest)
    config = identity_settings(mode="trusted_proxy", proxy_shared_secret="expected")

    identity = resolve_request_identity(
        headers={"X-Auth-User": "  user-1  ", "X-EIDP-Proxy-Secret": "expected"},
        config=config,
    )

    assert identity == ResolvedIdentity("user-1", IdentitySource.TRUSTED_PROXY)
    assert calls == [("expected", "expected")]


@pytest.mark.parametrize(
    "headers",
    [
        {"X-Auth-User": "user-1"},
        {"X-Auth-User": "user-1", "X-EIDP-Proxy-Secret": "wrong"},
        {"X-EIDP-Proxy-Secret": "expected"},
        {"X-Auth-User": "   ", "X-EIDP-Proxy-Secret": "expected"},
        {"X-Auth-User": "a" * 51, "X-EIDP-Proxy-Secret": "expected"},
    ],
    ids=["missing-secret", "wrong-secret", "missing-actor", "blank-actor", "oversized-actor"],
)
def test_invalid_trusted_identity_rejects_entire_request_without_sensitive_text(
    headers: dict[str, str],
) -> None:
    expected_secret = "expected"
    supplied_secret = headers.get("X-EIDP-Proxy-Secret", "")
    actor = headers.get("X-Auth-User", "")
    config = identity_settings(mode="trusted_proxy", proxy_shared_secret=expected_secret)

    with pytest.raises(IdentityRejectedError, match="request identity rejected") as exc_info:
        resolve_request_identity(headers=headers, config=config)

    error_text = str(exc_info.value)
    assert expected_secret not in error_text
    assert supplied_secret not in error_text or not supplied_secret
    assert actor not in error_text or not actor.strip()
