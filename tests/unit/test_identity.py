"""Identity domain and configuration contracts."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest
from pydantic import SecretStr, ValidationError

from eidp.config import Settings
from eidp.identity import (
    LEGACY_OPERATOR_IDENTITY,
    SYSTEM_IDENTITY,
    IdentitySource,
    ResolvedIdentity,
)


def test_identity_source_is_closed_to_the_four_audit_values() -> None:
    assert [(source.name, source.value) for source in IdentitySource] == [
        ("TRUSTED_PROXY", "trusted_proxy"),
        ("CONFIGURED_FALLBACK", "configured_fallback"),
        ("SYSTEM", "system"),
        ("LEGACY_UNSPECIFIED", "legacy_unspecified"),
    ]


def test_resolved_identity_is_frozen_and_constants_are_typed() -> None:
    assert SYSTEM_IDENTITY == ResolvedIdentity(
        actor="system",
        source=IdentitySource.SYSTEM,
    )
    assert LEGACY_OPERATOR_IDENTITY == ResolvedIdentity(
        actor="operator",
        source=IdentitySource.LEGACY_UNSPECIFIED,
    )
    with pytest.raises(FrozenInstanceError):
        SYSTEM_IDENTITY.actor = "changed"


def test_identity_settings_accept_only_explicit_modes_and_redact_proxy_secret() -> None:
    secret = "must-never-appear"
    config = Settings(
        identity_mode="trusted_proxy",
        fallback_actor="pilot-operator",
        proxy_shared_secret=secret,
        _env_file=None,
    )

    assert config.identity_mode == "trusted_proxy"
    assert config.fallback_actor == "pilot-operator"
    assert isinstance(config.proxy_shared_secret, SecretStr)
    assert config.proxy_shared_secret.get_secret_value() == secret
    assert secret not in repr(config)
    assert secret not in config.model_dump_json()

    with pytest.raises(ValidationError):
        Settings(identity_mode="implicit_header_trust", _env_file=None)
