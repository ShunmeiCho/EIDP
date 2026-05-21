from eidp.review.operator_actor import operator_actor_from_state


def test_operator_actor_from_state_strips_session_operator_name() -> None:
    assert operator_actor_from_state({"operator_name": "  山田  "}) == "山田"


def test_operator_actor_from_state_falls_back_when_missing_or_blank() -> None:
    assert operator_actor_from_state({}) == "operator"
    assert operator_actor_from_state({"operator_name": "   "}) == "operator"
    assert operator_actor_from_state(None) == "operator"
