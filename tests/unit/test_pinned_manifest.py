"""Tests for the human-confirmed pinned-manifest loader (Rung 1a).

The pin is the operator-confirmed identity contract: which disclosure page +
which PDF(s) carry a school's enrollment tables for a fiscal year. The loader
reads stdlib JSON into frozen rows and validates required fields + the
authority_basis.source_type enum. master.xlsx is EXPECTED-OUTPUT authority and
must never appear as a PDF-identity source_type.
"""

from __future__ import annotations

import copy
import dataclasses
import json
from pathlib import Path

import pytest

from eidp.pdf.pinned_manifest import (
    ALLOWED_SOURCE_TYPES,
    PinnedManifestError,
    PinnedManifestRow,
    load_pinned_manifest,
)

_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "ohara" / "ohara_rung1a_manifest.json"


def _valid_row() -> dict:
    """A minimal but complete pin row, as it appears inside the JSON manifest."""
    return {
        "school_key": "大原学園",
        "campus_key": "大原簿記情報専門学校札幌校",
        "school_name": "大原簿記情報専門学校札幌校",
        "fiscal_year": 2025,
        "pdf_paths": ["pdf/2025-1-01-01-5.pdf"],
        "pdf_url": "https://www.o-hara.ac.jp/about/joho/pdf/2025-1-01-01-5.pdf",
        "source_page_url": "https://www.o-hara.ac.jp/about/joho/",
        "authority_basis": {
            "source_type": "human_confirmed_official_pdf",
            "confirmed_by": "operator",
            "confirmed_at": "2026-07-05",
            "evidence": [
                {"kind": "pdf_url", "value": "https://www.o-hara.ac.jp/about/joho/pdf/2025-1-01-01-5.pdf"},
            ],
        },
        "status": "pinned",
        "notes": "test row",
    }


def _write_manifest(path: Path, rows: list[dict]) -> Path:
    path.write_text(json.dumps({"schools": rows}, ensure_ascii=False), encoding="utf-8")
    return path


# --------------------------------------------------------------------------- #
# Happy path against the committed Rung-1a fixture
# --------------------------------------------------------------------------- #


def test_load_rung1a_fixture_pins_school_01() -> None:
    rows = load_pinned_manifest(_FIXTURE)

    assert len(rows) == 1
    row = rows[0]
    assert isinstance(row, PinnedManifestRow)
    assert row.school_key == "大原学園"
    assert row.campus_key == "大原簿記情報専門学校札幌校"
    assert row.school_name == "大原簿記情報専門学校札幌校"
    assert row.fiscal_year == 2025
    assert row.pdf_paths == ["pdf/2025-1-01-01-5.pdf"]
    assert row.pdf_url == "https://www.o-hara.ac.jp/about/joho/pdf/2025-1-01-01-5.pdf"
    assert row.source_page_url == "https://www.o-hara.ac.jp/about/joho/"
    assert row.status == "pinned"


def test_rung1a_fixture_uses_human_confirmed_official_pdf_authority() -> None:
    row = load_pinned_manifest(_FIXTURE)[0]

    assert row.authority_basis["source_type"] == "human_confirmed_official_pdf"
    assert row.authority_basis["confirmed_by"]
    assert row.authority_basis["confirmed_at"]


def test_rung1a_fixture_evidence_lists_all_required_hints() -> None:
    row = load_pinned_manifest(_FIXTURE)[0]
    evidence = row.authority_basis["evidence"]
    by_kind = {item["kind"]: item["value"] for item in evidence}

    assert set(by_kind) == {
        "source_page",
        "pdf_url",
        "url_year_hint",
        "filename_hint",
        "pdf_text_school_hint",
        "master_school_name",
    }
    assert by_kind["source_page"] == "https://www.o-hara.ac.jp/about/joho/"
    assert by_kind["pdf_url"] == "https://www.o-hara.ac.jp/about/joho/pdf/2025-1-01-01-5.pdf"
    assert by_kind["url_year_hint"] == "2025"
    assert by_kind["filename_hint"] == "2025-1-01-01-5.pdf"
    assert by_kind["pdf_text_school_hint"] == "大原簿記情報専門学校札幌校"
    assert by_kind["master_school_name"] == "大原簿記情報専門学校札幌校"


def test_row_is_frozen() -> None:
    row = load_pinned_manifest(_FIXTURE)[0]

    with pytest.raises(dataclasses.FrozenInstanceError):
        row.school_key = "tampered"  # type: ignore[misc]


# --------------------------------------------------------------------------- #
# Shape flexibility: bare list vs. {"schools": [...]} wrapper
# --------------------------------------------------------------------------- #


def test_accepts_bare_list_manifest(tmp_path: Path) -> None:
    path = tmp_path / "bare.json"
    path.write_text(json.dumps([_valid_row()], ensure_ascii=False), encoding="utf-8")

    rows = load_pinned_manifest(path)

    assert len(rows) == 1
    assert rows[0].school_key == "大原学園"


def test_accepts_schools_wrapper_manifest(tmp_path: Path) -> None:
    path = _write_manifest(tmp_path / "wrapped.json", [_valid_row()])

    rows = load_pinned_manifest(path)

    assert len(rows) == 1


# --------------------------------------------------------------------------- #
# Validation: source_type enum
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("source_type", sorted(ALLOWED_SOURCE_TYPES))
def test_all_allowed_source_types_accepted(tmp_path: Path, source_type: str) -> None:
    row = _valid_row()
    row["authority_basis"]["source_type"] = source_type
    path = _write_manifest(tmp_path / f"{source_type}.json", [row])

    rows = load_pinned_manifest(path)

    assert rows[0].authority_basis["source_type"] == source_type


def test_unknown_source_type_raises_clear_error(tmp_path: Path) -> None:
    row = _valid_row()
    row["authority_basis"]["source_type"] = "master_xlsx_reverse_inferred"
    path = _write_manifest(tmp_path / "bad_source.json", [row])

    with pytest.raises(PinnedManifestError) as excinfo:
        load_pinned_manifest(path)

    message = str(excinfo.value)
    assert "source_type" in message
    assert "master_xlsx_reverse_inferred" in message


def test_missing_source_type_raises(tmp_path: Path) -> None:
    row = _valid_row()
    del row["authority_basis"]["source_type"]
    path = _write_manifest(tmp_path / "no_source.json", [row])

    with pytest.raises(PinnedManifestError, match="source_type"):
        load_pinned_manifest(path)


# --------------------------------------------------------------------------- #
# Validation: required fields + types
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "field",
    [
        "school_key",
        "campus_key",
        "school_name",
        "fiscal_year",
        "pdf_paths",
        "pdf_url",
        "source_page_url",
        "authority_basis",
        "status",
    ],
)
def test_missing_required_field_raises(tmp_path: Path, field: str) -> None:
    row = _valid_row()
    del row[field]
    path = _write_manifest(tmp_path / f"missing_{field}.json", [row])

    with pytest.raises(PinnedManifestError, match=field):
        load_pinned_manifest(path)


def test_fiscal_year_must_be_int(tmp_path: Path) -> None:
    row = _valid_row()
    row["fiscal_year"] = "2025"
    path = _write_manifest(tmp_path / "fy_str.json", [row])

    with pytest.raises(PinnedManifestError, match="fiscal_year"):
        load_pinned_manifest(path)


def test_pdf_paths_must_be_nonempty_list(tmp_path: Path) -> None:
    row = _valid_row()
    row["pdf_paths"] = []
    path = _write_manifest(tmp_path / "no_pdfs.json", [row])

    with pytest.raises(PinnedManifestError, match="pdf_paths"):
        load_pinned_manifest(path)


def test_pdf_paths_entries_must_be_strings(tmp_path: Path) -> None:
    row = _valid_row()
    row["pdf_paths"] = ["ok.pdf", 123]
    path = _write_manifest(tmp_path / "bad_pdf_entry.json", [row])

    with pytest.raises(PinnedManifestError, match="pdf_paths"):
        load_pinned_manifest(path)


def test_authority_basis_must_be_dict(tmp_path: Path) -> None:
    row = _valid_row()
    row["authority_basis"] = "human_confirmed_official_pdf"
    path = _write_manifest(tmp_path / "ab_str.json", [row])

    with pytest.raises(PinnedManifestError, match="authority_basis"):
        load_pinned_manifest(path)


def test_evidence_must_be_list(tmp_path: Path) -> None:
    row = _valid_row()
    row["authority_basis"]["evidence"] = {"kind": "pdf_url"}
    path = _write_manifest(tmp_path / "ev_dict.json", [row])

    with pytest.raises(PinnedManifestError, match="evidence"):
        load_pinned_manifest(path)


def test_notes_is_optional(tmp_path: Path) -> None:
    row = _valid_row()
    del row["notes"]
    path = _write_manifest(tmp_path / "no_notes.json", [row])

    rows = load_pinned_manifest(path)

    assert rows[0].notes == ""


# --------------------------------------------------------------------------- #
# Validation: file / structure errors
# --------------------------------------------------------------------------- #


def test_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(PinnedManifestError, match="not found"):
        load_pinned_manifest(tmp_path / "does_not_exist.json")


def test_malformed_json_raises(tmp_path: Path) -> None:
    path = tmp_path / "broken.json"
    path.write_text("{not: valid json", encoding="utf-8")

    with pytest.raises(PinnedManifestError, match="JSON"):
        load_pinned_manifest(path)


def test_row_must_be_object(tmp_path: Path) -> None:
    path = tmp_path / "scalar_row.json"
    path.write_text(json.dumps({"schools": ["not-an-object"]}), encoding="utf-8")

    with pytest.raises(PinnedManifestError):
        load_pinned_manifest(path)


def test_valid_row_helper_round_trips(tmp_path: Path) -> None:
    # Guards the negative-test helper: the baseline must actually load clean,
    # so each deletion/mutation above is the sole cause of its failure.
    path = _write_manifest(tmp_path / "baseline.json", [copy.deepcopy(_valid_row())])

    rows = load_pinned_manifest(path)

    assert len(rows) == 1
