"""Department natural-key normalization shared by import and PDF ingest."""

from __future__ import annotations

import re
import unicodedata

SPECIALIZED_COURSE_FIELDS = {
    "工業",
    "農業",
    "医療",
    "衛生",
    "教育・社会福祉",
    "商業実務",
    "服飾・家政",
    "文化・教養",
}

COURSE_FIELD_ALIASES = {
    "看護": "医療",
}


def normalize_course_name(course_name: str | None) -> str | None:
    """Normalize 課程名 variants into the Department natural-key label."""

    course = unicodedata.normalize("NFKC", course_name or "").strip()
    if not course:
        return None
    compact = re.sub(r"\s+", "", course)
    suffix = "専門課程"
    if compact.endswith(suffix):
        field = compact[: -len(suffix)]
        field = COURSE_FIELD_ALIASES.get(field, field)
        if field in SPECIALIZED_COURSE_FIELDS:
            return field
    return compact
