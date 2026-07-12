"""Shared department-join correctness core for the Linux/Web review and
double-check diff engines.

``review_master_diff`` and ``double_check_compare`` join reviewed rows against a
master subset / an external extraction using an IDENTICAL stable key and value
equality, and both must refuse a loose-key merge that only survives via the
identity-changing bare-コース fold (see ``department_key_strict``). Those primitives
live here in ONE place so a correctness guard can never again exist in one engine
but not the other -- the class of defect that produced the 2026-07 コース false-merge
(a guard present in ``excel/master_diff`` but missing from both pipeline engines).

Only the keying, value coercion, and collision test are shared. Each engine keeps
its own status vocabulary (``MatchStatus`` / ``DoubleCheckStatus``); this module
deliberately does NOT unify those, because the acceptance-gate, review-report, and
TRUE/FALSE double-check consumers are genuinely different.
"""

from __future__ import annotations

from eidp.pdf.master_ground_truth import (
    canonical_field_category,
    department_key,
    department_key_strict,
    normalize_text,
)

__all__ = [
    "COURSE_GRANULARITY_COLLISION_REASON",
    "JoinKey",
    "comparable_value",
    "is_course_granularity_collision",
    "join_key_label",
    "make_join_key",
    "values_equal",
]

# (school, 分野, 学科, fiscal_year, metric) -- all normalized.
JoinKey = tuple[str, str, str, int, str]

# Emitted when a loose-key 1:1 join is refused because the two department names only
# collapse together via the bare-コース fold (their strict keys differ). Contains the
# substring "granularity collision" that the engine regression tests assert on.
COURSE_GRANULARITY_COLLISION_REASON = (
    "department granularity collision: loose 学科 key merged distinct コース-level "
    "names (strict keys differ); not comparable"
)

_EMPTY_VALUE_TOKENS = frozenset({"", "-", "‐", "―"})


def make_join_key(
    school_name: str,
    field_category: str | None,
    department_name: str,
    fiscal_year: int,
    metric: str,
) -> JoinKey:
    """The stable within-school join key: (school, 分野, 学科, FY, metric), all normalized."""
    return (
        normalize_text(school_name),
        canonical_field_category(field_category),
        department_key(department_name),
        fiscal_year,
        normalize_text(metric),
    )


def join_key_label(key: JoinKey) -> str:
    """Render a JoinKey as the '|'-joined label used in diff report rows."""
    return f"{key[0]}|{key[1]}|{key[2]}|{key[3]}|{key[4]}"


def comparable_value(value: object) -> object:
    """Coerce a cell to a comparable form: an integer when numeric, ``None`` when
    blank/dash, otherwise the NFKC-normalized string. Shared so both engines compare
    values identically."""
    if value is None:
        return None
    text = str(value).strip().replace(",", "")
    if text in _EMPTY_VALUE_TOKENS:
        return None
    try:
        return int(float(text))
    except ValueError:
        return normalize_text(str(value))


def values_equal(left: object, right: object) -> bool:
    """True when two cells are equal under ``comparable_value`` coercion."""
    return comparable_value(left) == comparable_value(right)


def is_course_granularity_collision(name_a: str | None, name_b: str | None) -> bool:
    """True when two department names share the loose ``department_key`` but NOT the
    strict key -- i.e. they only merged via the identity-changing bare-コース fold and
    must not be certified as the same department. Callers apply this to a pair the loose
    key ALREADY joined; a True result means "refuse the match, surface for human
    disambiguation" rather than emit a MATCH / TRUE."""
    return department_key_strict(name_a or "") != department_key_strict(name_b or "")
