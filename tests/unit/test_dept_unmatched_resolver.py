from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from eidp.db.models import Department

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "dept_unmatched_resolver.py"
SPEC = importlib.util.spec_from_file_location("dept_unmatched_resolver", SCRIPT)
assert SPEC is not None
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules["dept_unmatched_resolver"] = MODULE
SPEC.loader.exec_module(MODULE)

_paren_tracks = MODULE._paren_tracks
_dept_alias_search = MODULE._dept_alias_search
_dept_group_search = MODULE._dept_group_search
_strip_suffix_pair = MODULE._strip_suffix_pair


def _dept(id: int, name: str) -> Department:
    return Department(id=id, canonical_name=name, school_id=1)


def test_paren_tracks_splits_lumped_dept_name() -> None:
    stem, tracks = _paren_tracks("高度情報学科(情報処理・WEB開発・AI)")
    assert stem == "高度情報学科"
    assert tracks == ["情報処理", "WEB開発", "AI"]


def test_suffix_swap_学科_to_科() -> None:
    v = _strip_suffix_pair("プロミュージシャン学科")
    assert "プロミュージシャン学科" in v
    assert "プロミュージシャン科" in v


def test_alias_match_suffix_swap_学科_to_科() -> None:
    """TSM real case: template 'プロミュージシャン学科' → DB 'プロミュージシャン科'"""
    depts = [_dept(521, "プロミュージシャン科（昼一）"),
             _dept(522, "プロミュージシャン科（昼二）")]
    hits = _dept_alias_search("プロミュージシャン学科", depts)
    # Both depts match (same stem different session) — ambiguous but real candidates
    ids = {d.id for d in hits}
    assert 521 in ids or 522 in ids


def test_group_match_hal_lumped_name() -> None:
    """HAL real case: template '高度情報学科(情報処理・WEB開発・AI)' →
    DB 高度情報学科（AIシステム開発） / （WEB開発） / （高度情報処理）"""
    depts = [
        _dept(2743, "高度情報学科（高度情報処理）"),
        _dept(2744, "高度情報学科（WEB開発）"),
        _dept(2745, "高度情報学科（AIシステム開発）"),
        _dept(2751, "情報処理学科"),  # different stem — must NOT match
    ]
    hits = _dept_group_search("高度情報学科(情報処理・WEB開発・AI)", depts)
    hit_ids = {d.id for d in hits}
    # All 3 高度情報学科 should match; 情報処理学科 (different stem) must not
    assert 2744 in hit_ids  # WEB開発 matches WEB開発
    assert 2745 in hit_ids  # AIシステム開発 overlaps AI
    # 高度情報処理 overlaps with 情報処理
    assert 2743 in hit_ids
    assert 2751 not in hit_ids


def test_group_search_returns_empty_when_no_parens() -> None:
    depts = [_dept(1, "情報学科")]
    assert _dept_group_search("情報学科", depts) == []
