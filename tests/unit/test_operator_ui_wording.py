"""Guard operator-facing UI wording for the current production console."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PRODUCTION_UI_PATHS = [
    REPO_ROOT / "src" / "eidp" / "review" / "operator_pages.py",
    *sorted((REPO_ROOT / "src" / "eidp" / "review" / "_pages").glob("*.py")),
]

LEGACY_OPERATOR_TERMS = {
    "要確認キュー": "Use 人の確認が必要 for the business queue.",
    "待機キュー": "Use a concrete review bucket label instead of a generic queue.",
    "Excelプレビュー": "Use Excel出力 for the current export gate.",
    "Excel プレビュー": "Use Excel出力 for the current export gate.",
    "年度判定・修正": "Use 対象年度確認 or a specific fiscal-year review label.",
    "DB転記済": "Use 採録済み for accepted production data.",
}


def test_current_operator_ui_does_not_reintroduce_legacy_terms() -> None:
    offenders: list[str] = []
    for path in PRODUCTION_UI_PATHS:
        text = path.read_text(encoding="utf-8")
        for term, replacement_note in LEGACY_OPERATOR_TERMS.items():
            if term in text:
                offenders.append(f"{path.relative_to(REPO_ROOT)} contains {term!r}: {replacement_note}")

    assert not offenders, "\n".join(offenders)
