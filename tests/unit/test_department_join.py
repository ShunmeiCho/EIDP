from __future__ import annotations

from eidp.pipeline.department_join import (
    COURSE_GRANULARITY_COLLISION_REASON,
    comparable_value,
    is_course_granularity_collision,
    join_key_label,
    make_join_key,
    values_equal,
)


def test_make_join_key_normalizes_all_parts() -> None:
    key = make_join_key("　東京テスト　", "文化・教養", "情報システム学科", 2025, " enrollment ")
    assert key == ("東京テスト", "文化教養", "情報システム", 2025, "enrollment")


def test_join_key_label_is_pipe_joined() -> None:
    key = make_join_key("東京", "商業実務", "会計学科", 2025, "enrollment")
    assert join_key_label(key) == "東京|商業実務|会計|2025|enrollment"


def test_comparable_value_coerces_numeric_blank_and_text() -> None:
    assert comparable_value("1,234") == 1234
    assert comparable_value("40") == comparable_value(40)
    assert comparable_value(None) is None
    assert comparable_value("-") is None
    assert comparable_value("―") is None  # full-width dash reads as blank
    assert comparable_value("　未定　") == "未定"


def test_values_equal_uses_comparable_coercion() -> None:
    assert values_equal("1,000", 1000)
    assert values_equal("-", None)
    assert not values_equal(40, 41)


def test_is_course_granularity_collision_flags_bare_course_only() -> None:
    # A bare コース vs its parent 科: the loose key merged them, the strict key did not.
    assert is_course_granularity_collision("ビジネスコース", "ビジネス")
    # Identity-preserving 学科/科 suffix variation is NOT a collision.
    assert not is_course_granularity_collision("情報システム学科", "情報システム")
    assert not is_course_granularity_collision("会計", "会計学科")
    # A blank/None name never certifies against a real department.
    assert is_course_granularity_collision(None, "ビジネス")


def test_collision_reason_names_granularity() -> None:
    assert "granularity collision" in COURSE_GRANULARITY_COLLISION_REASON
