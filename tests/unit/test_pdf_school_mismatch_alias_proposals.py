from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

from eidp.db.models import School, SchoolAlias

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "pdf_school_mismatch_alias_proposals.py"
SPEC = importlib.util.spec_from_file_location("pdf_school_mismatch_alias_proposals", SCRIPT)
assert SPEC is not None
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules["pdf_school_mismatch_alias_proposals"] = MODULE
SPEC.loader.exec_module(MODULE)

build_proposals = MODULE.build_proposals
write_merged_proposals = MODULE.write_merged_proposals


def _school(id: int, name: str, corp: str = "学校法人三幸学園", pref: str = "東京都") -> School:
    return School(id=id, school_name=name, corporation_name=corp, prefecture=pref)


def _pdf_mismatch_row(school_id: int, parsed: str, target: str) -> dict[str, object]:
    return {
        "school_id": school_id,
        "reason": "pdf_school_mismatch",
        "pdf_url": "https://www.sanko.ac.jp/disclosure/example/yoshiki2026.pdf",
        "page_url": "https://www.sanko.ac.jp/example/disclosure/",
        "anchor_text": "2026年度 高等教育の修学支援新制度 申請様式",
        "extra": {
            "parsed_school_name": parsed,
            "target_school_name": target,
        },
    }


def test_build_proposals_emits_low_risk_sanko_it_expansion_aliases() -> None:
    rows = [
        _pdf_mismatch_row(
            20,
            "横浜医療秘書&IT専門学校",
            "横浜医療秘書専門学校",
        ),
        _pdf_mismatch_row(
            25,
            "福岡医療秘書福祉&IT専門学校",
            "福岡医療秘書福祉専門学校",
        ),
    ]
    schools = [
        _school(20, "横浜医療秘書専門学校", pref="神奈川県"),
        _school(25, "福岡医療秘書福祉専門学校", pref="福岡県"),
    ]

    proposals, stats = build_proposals(rows, schools, [])

    assert stats["proposals"] == 2
    by_name = {p.template_name: p for p in proposals}
    assert by_name["横浜医療秘書&IT専門学校"].proposal_type == "alias_existing_school"
    assert by_name["横浜医療秘書&IT専門学校"].matched_school_id == 20
    assert by_name["福岡医療秘書福祉&IT専門学校"].matched_school_id == 25
    assert "Operator approval is required" in by_name["福岡医療秘書福祉&IT専門学校"].reasoning


def test_build_proposals_skips_when_parsed_name_matches_another_school() -> None:
    rows = [
        _pdf_mismatch_row(
            20,
            "横浜医療秘書&IT専門学校",
            "横浜医療秘書専門学校",
        )
    ]
    schools = [
        _school(20, "横浜医療秘書専門学校", pref="神奈川県"),
        _school(99, "横浜医療秘書&IT専門学校", pref="神奈川県"),
    ]

    proposals, stats = build_proposals(rows, schools, [])

    assert proposals == []
    assert stats["conflict_existing_school"] == 1


def test_build_proposals_skips_unrelated_school_mismatch() -> None:
    rows = [
        _pdf_mismatch_row(
            1,
            "東京ITプログラミング＆会計専門学校杉並校",
            "東京ITプログラミング＆会計専門学校",
        )
    ]
    schools = [_school(1, "東京ITプログラミング＆会計専門学校", corp="立志舎")]

    proposals, stats = build_proposals(rows, schools, [])

    assert proposals == []
    assert stats["unsafe_expansion"] == 1


def test_build_proposals_skips_existing_alias() -> None:
    rows = [
        _pdf_mismatch_row(
            25,
            "福岡医療秘書福祉&IT専門学校",
            "福岡医療秘書福祉専門学校",
        )
    ]
    schools = [_school(25, "福岡医療秘書福祉専門学校", pref="福岡県")]
    aliases = [
        SchoolAlias(
            school_id=25,
            alias_name="福岡医療秘書福祉&IT専門学校",
            alias_type="pdf_school_name",
            source="proposal_review_queue",
        )
    ]

    proposals, stats = build_proposals(rows, schools, aliases)

    assert proposals == []
    assert stats["already_has_alias"] == 1


def test_write_merged_proposals_preserves_existing_and_dedupes(tmp_path: Path) -> None:
    path = tmp_path / "school_missing_proposals.jsonl"
    path.write_text(
        json.dumps(
            {
                "template_name": "既存校",
                "proposal_type": "alias_existing_school",
                "matched_school_id": 1,
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    proposals = [
        MODULE.PdfSchoolMismatchAliasProposal(
            template_name="既存校",
            template_rows=2,
            proposal_type="alias_existing_school",
            matched_school_id=1,
            matched_school_name="既存校",
            matched_corporation="C",
        ),
        MODULE.PdfSchoolMismatchAliasProposal(
            template_name="新規校&IT専門学校",
            template_rows=1,
            proposal_type="alias_existing_school",
            matched_school_id=2,
            matched_school_name="新規校専門学校",
            matched_corporation="C",
        ),
    ]

    stats = write_merged_proposals(path, proposals)

    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert stats == {"preserved": 1, "appended": 1, "written": 2}
    assert [row["template_name"] for row in rows] == ["既存校", "新規校&IT専門学校"]
