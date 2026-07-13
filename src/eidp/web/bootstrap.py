"""Shared fail-closed bootstrap for every Streamlit entrypoint."""

from __future__ import annotations

import streamlit as st
import structlog

from eidp.config import settings
from eidp.identity import ResolvedIdentity
from eidp.web.identity import (
    IdentityConfigurationError,
    IdentityRejectedError,
    resolve_request_identity,
    validate_identity_configuration,
)

GENERIC_REJECTION_MESSAGE = "This EIDP request cannot be authenticated."

log = structlog.get_logger(__name__)


def bootstrap_web_request() -> ResolvedIdentity:
    """Resolve the request identity or render one generic rejection and stop."""
    try:
        validate_identity_configuration(settings)
        return resolve_request_identity(headers=st.context.headers, config=settings)
    except IdentityConfigurationError:
        log.error("web_identity_configuration_invalid")
    except IdentityRejectedError:
        log.warning("web_request_identity_rejected")

    st.error(GENERIC_REJECTION_MESSAGE)
    st.stop()


__all__ = ["bootstrap_web_request"]
