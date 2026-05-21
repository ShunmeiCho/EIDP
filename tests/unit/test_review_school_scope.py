from __future__ import annotations

from eidp.review.school_scope import OPERATOR_SCHOOL_SCOPE_LABEL, OPERATOR_SCHOOL_TYPE_SCOPE


def test_operator_scope_tracks_v1_vocational_ship_gate() -> None:
    assert OPERATOR_SCHOOL_TYPE_SCOPE == "専門学校"
    assert OPERATOR_SCHOOL_SCOPE_LABEL == "専門学校"
