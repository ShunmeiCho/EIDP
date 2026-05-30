"""Unit tests for the shared two-stage confirm gate (G11)."""
from __future__ import annotations

from eidp.review.confirm_gate import EXECUTE, IDLE, PENDING, resolve_confirm_gate


def test_first_request_returns_pending_and_does_not_execute() -> None:
    state: dict[str, object] = {}

    result = resolve_confirm_gate(
        state, key="confirm_foo", requested=True, confirmed=False, cancelled=False,
    )

    assert result == PENDING
    assert state.get("confirm_foo") is True


def test_confirmed_while_pending_returns_execute_and_clears_key() -> None:
    state: dict[str, object] = {"confirm_foo": True}

    result = resolve_confirm_gate(
        state, key="confirm_foo", requested=False, confirmed=True, cancelled=False,
    )

    assert result == EXECUTE
    assert "confirm_foo" not in state


def test_execute_is_returned_exactly_once_then_idle_on_subsequent_passes() -> None:
    state: dict[str, object] = {"confirm_foo": True}

    first = resolve_confirm_gate(
        state, key="confirm_foo", requested=False, confirmed=True, cancelled=False,
    )
    assert first == EXECUTE

    second = resolve_confirm_gate(
        state, key="confirm_foo", requested=False, confirmed=True, cancelled=False,
    )
    assert second == IDLE


def test_cancelled_clears_pending_and_returns_idle() -> None:
    state: dict[str, object] = {"confirm_foo": True}

    result = resolve_confirm_gate(
        state, key="confirm_foo", requested=False, confirmed=False, cancelled=True,
    )

    assert result == IDLE
    assert "confirm_foo" not in state


def test_cancelled_dominates_confirmed_when_both_set() -> None:
    state: dict[str, object] = {"confirm_foo": True}

    result = resolve_confirm_gate(
        state, key="confirm_foo", requested=False, confirmed=True, cancelled=True,
    )

    assert result == IDLE
    assert "confirm_foo" not in state


def test_confirmed_without_prior_pending_returns_idle() -> None:
    state: dict[str, object] = {}

    result = resolve_confirm_gate(
        state, key="confirm_foo", requested=False, confirmed=True, cancelled=False,
    )

    assert result == IDLE
    assert "confirm_foo" not in state


def test_plain_rerun_while_pending_stays_pending() -> None:
    state: dict[str, object] = {"confirm_foo": True}

    result = resolve_confirm_gate(
        state, key="confirm_foo", requested=False, confirmed=False, cancelled=False,
    )

    assert result == PENDING
    assert state.get("confirm_foo") is True


def test_idle_when_nothing_pending_and_nothing_requested() -> None:
    state: dict[str, object] = {}

    result = resolve_confirm_gate(
        state, key="confirm_foo", requested=False, confirmed=False, cancelled=False,
    )

    assert result == IDLE
    assert state == {}


def test_distinct_keys_do_not_interfere() -> None:
    state: dict[str, object] = {}

    resolve_confirm_gate(
        state, key="confirm_a", requested=True, confirmed=False, cancelled=False,
    )
    resolve_confirm_gate(
        state, key="confirm_b", requested=True, confirmed=False, cancelled=False,
    )

    assert state == {"confirm_a": True, "confirm_b": True}

    a_exec = resolve_confirm_gate(
        state, key="confirm_a", requested=False, confirmed=True, cancelled=False,
    )

    assert a_exec == EXECUTE
    assert "confirm_a" not in state
    assert state.get("confirm_b") is True
