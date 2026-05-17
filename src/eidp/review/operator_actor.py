"""Operator actor helpers for audit-writing Streamlit pages."""

from __future__ import annotations

from typing import Any, cast

DEFAULT_OPERATOR_ACTOR = "operator"
OPERATOR_NAME_STATE_KEY = "operator_name"


def operator_actor_from_state(state: object | None) -> str:
    """Return the audit actor from Streamlit session state."""

    raw = cast(Any, state).get(OPERATOR_NAME_STATE_KEY) if state is not None else None
    if isinstance(raw, str):
        actor = raw.strip()
        if actor:
            return actor
    return DEFAULT_OPERATOR_ACTOR
