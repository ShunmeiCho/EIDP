"""Join-key normalizers + schema for diffing PDF-extracted department records
against data/master.xlsx 学科別 rows (Slice 4).

Reconciles the verified mismatch shapes between the PDF table and the master sheet:
- master 課程名 holds the 8-value 分野 taxonomy; PDF ``field_category`` is that 分野
  (PDF ``course_name``=専門課程 is the level and is excluded from the join).
- master 学科名 carries a 学科/科 suffix and half-width digits; the PDF gives no suffix
  and originally full-width digits with embedded newlines.
- master metric columns are FY-blocked with a NON-uniform stride (2019 has no 備考) and
  top out at FY2025.

This module is READ-ONLY logic; the loader that reads data/master.xlsx (red-line, never
written) is added in a later step and reuses these normalizers.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass

__all__ = [
    "FY_TO_CAPACITY_COLUMN",
    "ExpectedDepartmentRow",
    "canonical_field_category",
    "department_key",
    "fy_metric_columns",
    "normalize_text",
]

# The 収定 (capacity) column index per fiscal year in the 学科別 sheet (0-based).
# 在籍 (enrollment) = +1, 留学生 (intl_students) = +2. Stride is NON-uniform: 2019 has
# no 備考 column (offset +10 to 2020), 2020+ carry 備考 (+11). master tops out at FY2025.
FY_TO_CAPACITY_COLUMN: dict[int, int] = {
    2019: 7,
    2020: 17,
    2021: 28,
    2022: 39,
    2023: 50,
    2024: 61,
    2025: 72,
}

# 分野 canonicalized to its 中点-stripped form; a few surface spellings alias to it.
_FIELD_ALIASES: dict[str, str] = {"看護": "医療"}

# Middle-dot / separator variants to drop from 分野 (NFKC already folds ･ -> ・, ／ -> /).
_FIELD_SEPARATORS = str.maketrans("", "", "・/")

# Longest-first so 学科 is stripped before the bare 科.
_DEPT_SUFFIXES = ("学科", "科")


def normalize_text(text: str | None) -> str:
    """NFKC-fold (full-width -> half-width) and strip all whitespace/newlines."""
    if not text:
        return ""
    return "".join(unicodedata.normalize("NFKC", text).split())


def canonical_field_category(value: str | None) -> str:
    """Canonicalize a 分野 (PDF field_category or master 課程名) for joining.

    Drops middle-dot separators (文化・教養 == 文化教養) and folds known aliases
    (看護 -> 医療) so the PDF's 分野 lands on the master 課程名 column.
    """
    normalized = normalize_text(value).translate(_FIELD_SEPARATORS)
    return _FIELD_ALIASES.get(normalized, normalized)


def department_key(name: str | None) -> str:
    """Normalize a 学科名 and strip exactly one trailing 学科/科 suffix.

    master stores 'ビジネスキャリア2年制学科'; the PDF gives 'ビジネスキャリア２年制'
    (full-width, newline, no suffix). Both key to 'ビジネスキャリア2年制'. Names with no
    学科/科 suffix (end in 年制 or a parenthetical spec) are kept verbatim after NFKC.
    """
    normalized = normalize_text(name)
    stripped = normalized
    # Drop a trailing コース qualifier: the PDF writes '(ビジネスコース)' where master writes
    # '（ビジネス）'; after NFKC the only residue is コース. Only at the trailing edge or just
    # before a closing paren, never mid-name.
    if stripped.endswith("コース"):
        stripped = stripped[: -len("コース")]
    elif stripped.endswith("コース)"):
        stripped = stripped[: -len("コース)")] + ")"
    for suffix in _DEPT_SUFFIXES:
        if stripped.endswith(suffix) and len(stripped) > len(suffix):
            stripped = stripped[: -len(suffix)]
            break
    # Empty-key guard (pre-Rung1c): a name that is nothing but strippable suffixes must not
    # collapse to '' -- an empty key would false-merge unrelated departments. Fall back to the
    # pre-strip normalized form so the identity is never lost.
    return stripped or normalized


def fy_metric_columns(fiscal_year: int) -> tuple[int, int, int]:
    """Return the (capacity, enrollment, intl_students) column indices for a fiscal year.

    Raises ``KeyError`` for years the master sheet does not cover (e.g. 2026).
    """
    base = FY_TO_CAPACITY_COLUMN[fiscal_year]
    return base, base + 1, base + 2


@dataclass(frozen=True)
class ExpectedDepartmentRow:
    """One master 学科別 row projected to the metrics the extractor produces."""

    prefecture: str
    corporation_name: str
    school_name: str
    field_category: str
    department_name: str
    day_night: str
    duration: str
    capacity: int | None
    enrollment: int | None
    intl_students: int | None

    @property
    def join_key(self) -> tuple[str, str]:
        """(canonical 分野, department key) -- the within-school department join key."""
        return canonical_field_category(self.field_category), department_key(self.department_name)
