"""Loader for the human-confirmed pinned PDF-identity manifest (Rung 1a).

A pinned manifest records, per school, the operator-confirmed authoritative
source: which disclosure page and which PDF(s) carry that school's enrollment
tables for a given fiscal year. It is the PIN that turns extraction into a
closed, auditable problem instead of a discovery gamble.

Authority hierarchy (per operator decision):
- primary = ``human_confirmed_official_pdf`` (URL + source page, human-confirmed).
- URL / path / filename are strong corroborating evidence.
- PDF body text is identity corroboration only.
- ``master.xlsx`` is EXPECTED-OUTPUT authority and is NEVER a source of PDF
  identity, so it has no place in ``ALLOWED_SOURCE_TYPES``.

The manifest is stdlib JSON (no PyYAML dependency). This module reads it into
frozen :class:`PinnedManifestRow` rows and validates required fields plus the
``authority_basis.source_type`` enum, raising :class:`PinnedManifestError`
with a clear, field-named message otherwise.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

__all__ = [
    "ALLOWED_SOURCE_TYPES",
    "PinnedManifestError",
    "PinnedManifestRow",
    "load_pinned_manifest",
]

# The only source_type values a pin may declare. ``human_confirmed_official_pdf``
# is the primary Rung-1a authority; the rest are lower-tier fallbacks that must
# never silently upgrade to primary. master.xlsx is intentionally absent.
ALLOWED_SOURCE_TYPES = frozenset(
    {
        "human_confirmed_official_pdf",
        "official_source_page",
        "official_index_entry",
        "manual_exception",
    }
)

# Row fields that must be present and non-empty (notes is optional; it defaults
# to "" so absence is not a validation failure).
_REQUIRED_STR_FIELDS = (
    "school_key",
    "campus_key",
    "school_name",
    "prefecture",
    "pdf_url",
    "source_page_url",
    "status",
)
_REQUIRED_AUTHORITY_FIELDS = ("source_type", "confirmed_by", "confirmed_at", "evidence")


class PinnedManifestError(ValueError):
    """Raised when a pinned manifest is missing, malformed, or fails validation."""


@dataclass(frozen=True)
class PinnedManifestRow:
    """One operator-confirmed school pin.

    ``authority_basis`` is kept as the raw dict (source_type, confirmed_by,
    confirmed_at, evidence list) so it round-trips 1:1 with the JSON and stays
    open for richer evidence kinds without a schema migration.
    """

    school_key: str  # 法人名 (e.g. 大原学園)
    campus_key: str  # 学校名 (e.g. 大原簿記情報専門学校札幌校)
    school_name: str  # human-readable school/campus name
    prefecture: str  # 都道府県 -- required so sibling-campus discrimination has a second key
    fiscal_year: int
    pdf_paths: list[str]  # PDF path(s) on the disclosure page (relative hrefs)
    pdf_url: str  # resolved absolute URL of the primary pinned PDF
    source_page_url: str  # the disclosure/index page the PDFs were listed on
    authority_basis: dict[str, Any]  # source_type + confirmed_by/at + evidence list
    status: str
    notes: str = ""


def load_pinned_manifest(path: Path | str) -> list[PinnedManifestRow]:
    """Read a JSON pinned manifest into validated :class:`PinnedManifestRow` rows.

    Accepts either a bare JSON list of row objects or a ``{"schools": [...]}``
    wrapper (which may also carry manifest-level metadata). Raises
    :class:`PinnedManifestError` with a field-named message on any structural or
    field-level violation, including an ``authority_basis.source_type`` outside
    :data:`ALLOWED_SOURCE_TYPES`.
    """
    manifest_path = Path(path)
    if not manifest_path.is_file():
        raise PinnedManifestError(f"pinned manifest not found: {manifest_path}")

    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise PinnedManifestError(f"pinned manifest is not valid JSON: {manifest_path} ({exc})") from exc

    raw_rows = _extract_rows(payload, manifest_path)
    return [_parse_row(raw, index) for index, raw in enumerate(raw_rows)]


def _extract_rows(payload: Any, manifest_path: Path) -> list[Any]:
    if isinstance(payload, list):
        return payload
    schools = payload.get("schools") if isinstance(payload, dict) else None
    if isinstance(schools, list):
        return schools
    raise PinnedManifestError(
        f'pinned manifest must be a JSON list or a {{"schools": [...]}} object: {manifest_path}'
    )


def _parse_row(raw: Any, index: int) -> PinnedManifestRow:
    where = f"row[{index}]"
    if not isinstance(raw, dict):
        raise PinnedManifestError(f"{where}: each pin must be a JSON object, got {type(raw).__name__}")

    for field_name in _REQUIRED_STR_FIELDS:
        value = raw.get(field_name)
        if not isinstance(value, str) or not value.strip():
            raise PinnedManifestError(f"{where}: field '{field_name}' must be a non-empty string")

    fiscal_year = raw.get("fiscal_year")
    # bool is an int subclass; reject it so a stray true/false is not read as a year.
    if not isinstance(fiscal_year, int) or isinstance(fiscal_year, bool):
        raise PinnedManifestError(f"{where}: field 'fiscal_year' must be an integer")

    pdf_paths = raw.get("pdf_paths")
    if "pdf_paths" not in raw:
        raise PinnedManifestError(f"{where}: field 'pdf_paths' is required")
    if not isinstance(pdf_paths, list) or not pdf_paths:
        raise PinnedManifestError(f"{where}: field 'pdf_paths' must be a non-empty list")
    if not all(isinstance(entry, str) and entry.strip() for entry in pdf_paths):
        raise PinnedManifestError(f"{where}: field 'pdf_paths' must contain only non-empty strings")

    if "authority_basis" not in raw:
        raise PinnedManifestError(f"{where}: field 'authority_basis' is required")
    authority_basis = _validate_authority_basis(raw["authority_basis"], where)

    notes = raw.get("notes", "")
    if not isinstance(notes, str):
        raise PinnedManifestError(f"{where}: field 'notes' must be a string when present")

    return PinnedManifestRow(
        school_key=raw["school_key"],
        campus_key=raw["campus_key"],
        school_name=raw["school_name"],
        prefecture=raw["prefecture"],
        fiscal_year=fiscal_year,
        pdf_paths=list(pdf_paths),
        pdf_url=raw["pdf_url"],
        source_page_url=raw["source_page_url"],
        authority_basis=authority_basis,
        status=raw["status"],
        notes=notes,
    )


def _validate_authority_basis(authority_basis: Any, where: str) -> dict[str, Any]:
    if not isinstance(authority_basis, dict):
        raise PinnedManifestError(f"{where}: field 'authority_basis' must be a JSON object")

    for field_name in _REQUIRED_AUTHORITY_FIELDS:
        if field_name not in authority_basis:
            raise PinnedManifestError(f"{where}: authority_basis.{field_name} is required")

    source_type = authority_basis["source_type"]
    if source_type not in ALLOWED_SOURCE_TYPES:
        allowed = ", ".join(sorted(ALLOWED_SOURCE_TYPES))
        raise PinnedManifestError(
            f"{where}: authority_basis.source_type '{source_type}' is not one of: {allowed}"
        )

    if not isinstance(authority_basis["evidence"], list):
        raise PinnedManifestError(f"{where}: authority_basis.evidence must be a list")

    return authority_basis
