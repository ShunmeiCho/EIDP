from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from eidp.db.models import School

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "school_missing_resolver.py"
SPEC = importlib.util.spec_from_file_location("school_missing_resolver", SCRIPT)
assert SPEC is not None
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
# Dataclass @ dataclass needs the module in sys.modules to resolve __dict__
sys.modules["school_missing_resolver"] = MODULE
SPEC.loader.exec_module(MODULE)

classify = MODULE.classify


def _school(id: int, name: str, corp: str = "A", pref: str = "東京都") -> School:
    return School(id=id, school_name=name, corporation_name=corp, prefecture=pref)


def test_paren_template_matches_db_branch_name() -> None:
    """Template '日本工学院(八王子)' → DB '日本工学院八王子専門学校'."""
    schools = [
        _school(1, "日本工学院専門学校", corp="片柳学園"),
        _school(2, "日本工学院八王子専門学校", corp="片柳学園"),
    ]
    p = classify("日本工学院(八王子)", 33, schools)
    assert p.proposal_type == "alias_existing_school"
    assert p.matched_school_id == 2
    assert p.paren_content == "八王子"


def test_abbreviated_template_matches_full_db_name() -> None:
    """'東京テクニカルカレッジ' → '専門学校東京テクニカルカレッジ'."""
    schools = [_school(573, "専門学校東京テクニカルカレッジ")]
    p = classify("東京テクニカルカレッジ", 12, schools)
    assert p.proposal_type == "alias_existing_school"
    assert p.matched_school_id == 573


def test_ambiguous_when_multiple_schools_same_short_name() -> None:
    """'東京ビジュアルアーツ' matches both Adachi学園 and 21世紀アカデメイア."""
    schools = [
        _school(163, "専門学校東京ビジュアルアーツ・アカデミー", corp="21世紀アカデメイア"),
        _school(2239, "専門学校東京ビジュアルアーツ", corp="Adachi学園"),
    ]
    p = classify("東京ビジュアルアーツ", 6, schools)
    assert p.proposal_type == "ambiguous_candidates"
    assert len(p.candidates) >= 2
    assert {c["school_id"] for c in p.candidates} == {163, 2239}


def test_branch_marker_detected_when_parent_exists() -> None:
    """'東京スクールオブミュージック&ダンス専門学校澁谷' with parent in DB."""
    schools = [_school(104, "東京スクールオブミュージック＆ダンス専門学校", corp="滋慶")]
    p = classify("東京スクールオブミュージック&ダンス専門学校澁谷", 4, schools)
    # '澁谷' + parent '東京スクールオブミュージック...' matches substring
    assert p.proposal_type in ("branch_of_existing", "alias_existing_school")
    # Either way, parent school 104 should be in candidates or matched
    if p.matched_school_id:
        assert p.matched_school_id == 104
    else:
        assert any(c["school_id"] == 104 for c in p.candidates)


def test_truly_missing_when_no_match_no_branch() -> None:
    schools = [_school(1, "全然違う学校")]
    p = classify("東京デザイナーアカデミー", 8, schools)
    assert p.proposal_type == "truly_missing"
    assert p.matched_school_id is None


def test_empty_candidates_for_branch_with_no_parent() -> None:
    schools = [_school(1, "全然違う学校")]
    p = classify("存在しない校澁谷", 1, schools)
    assert p.proposal_type == "truly_missing"
    assert "澁谷" in p.reasoning
