"""Two-stage confirm gate for irreversible operator actions (G11).

Pure state machine over a Streamlit-style session_state mapping so a
destructive write helper only fires on an explicit second confirmation.
render() shells stay thin (# pragma: no cover); this helper carries the
tested logic. Reused by fiscal_year_override, dept-alias void, and the
run_now auto-pipeline.
"""
from __future__ import annotations

from typing import Any

PENDING = "pending"
EXECUTE = "execute"
IDLE = "idle"


def resolve_confirm_gate(
    session_state: Any,
    *,
    key: str,
    requested: bool,
    confirmed: bool,
    cancelled: bool,
) -> str:
    """Resolve one render pass of a two-stage confirm.

    cancelled            -> clear pending, IDLE
    confirmed & pending  -> clear pending, EXECUTE (caller runs the action)
    requested            -> set pending, PENDING (caller shows confirm UI; action NOT run)
    already pending      -> PENDING (rerun while awaiting confirmation)
    otherwise            -> IDLE
    """
    if cancelled:
        session_state.pop(key, None)
        return IDLE
    if confirmed and session_state.get(key):
        session_state.pop(key, None)
        return EXECUTE
    if requested:
        session_state[key] = True
        return PENDING
    if session_state.get(key):
        return PENDING
    return IDLE
