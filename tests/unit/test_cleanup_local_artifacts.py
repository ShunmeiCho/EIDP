from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "cleanup_local_artifacts.py"
spec = importlib.util.spec_from_file_location("cleanup_local_artifacts", SCRIPT_PATH)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def _touch(path: Path, size: int = 1) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x" * size)


def test_collect_candidates_matches_generated_top_level_artifacts(tmp_path: Path) -> None:
    temp = tmp_path / "_temp"
    _touch(temp / "verify-v211-install-abc" / "marker.txt", 3)
    _touch(temp / "v99-extract-abc" / "marker.txt", 5)
    _touch(temp / "eidp-v161-verify.abc" / "marker.txt", 7)
    _touch(temp / "v396_vendor.zip", 11)
    _touch(temp / "manual-reference" / "marker.txt", 13)

    candidates = module.collect_candidates(temp)

    assert [candidate.path for candidate in candidates] == [
        "_temp/eidp-v161-verify.abc",
        "_temp/v396_vendor.zip",
        "_temp/v99-extract-abc",
        "_temp/verify-v211-install-abc",
    ]
    assert sum(candidate.bytes for candidate in candidates) == 26


def test_collect_candidates_keeps_latest_retroactive_per_fy(tmp_path: Path) -> None:
    temp = tmp_path / "_temp"
    for stamp in ["20260515-120000", "20260515-130000", "20260516-090000"]:
        _touch(temp / f"non-windows-retroactive-fy2025-{stamp}" / "output" / "export.xlsx")
    _touch(temp / "non-windows-retroactive-fy2024-20260516-090000" / "output" / "export.xlsx")

    candidates = module.collect_candidates(temp, keep_latest_retroactive_per_fy=1)

    assert [candidate.path for candidate in candidates] == [
        "_temp/non-windows-retroactive-fy2025-20260515-120000",
        "_temp/non-windows-retroactive-fy2025-20260515-130000",
    ]


def test_collect_candidates_honors_explicit_keep_path(tmp_path: Path) -> None:
    temp = tmp_path / "_temp"
    kept = temp / "verify-v211-install-abc"
    removed = temp / "verify-v212-install-abc"
    _touch(kept / "marker.txt")
    _touch(removed / "marker.txt")

    candidates = module.collect_candidates(temp, keep_paths={kept})

    assert [candidate.path for candidate in candidates] == ["_temp/verify-v212-install-abc"]


def test_collect_candidates_aggressive_matches_probe_artifacts(tmp_path: Path) -> None:
    temp = tmp_path / "_temp"
    _touch(temp / "kousei-application_form2.pdf")
    _touch(temp / "v408-r7-browser-eidp_master.xlsx")
    _touch(temp / "pdf-rca" / "sample.pdf")
    _touch(temp / "win-v342-evidence" / "eidp.sqlite3")
    _touch(temp / "saitama-current51-rerun-20260511-071951" / "output.xlsx")
    _touch(temp / "kousei-gold-v2" / "eidp.sqlite3")
    _touch(temp / "r7-window-check-db-abc" / "eidp.sqlite3")
    _touch(temp / "ui-smoke-20260507-120558" / "data" / "master.xlsx")
    _touch(temp / "v140_all_japan" / "evidence.jsonl")
    _touch(temp / "win_setup_v104.code")
    _touch(temp / "eidp-v109-wheel.whl")
    _touch(temp / "manual-reference" / "marker.txt")

    conservative = module.collect_candidates(temp)
    aggressive = module.collect_candidates(temp, aggressive=True)

    assert conservative == []
    assert [candidate.path for candidate in aggressive] == [
        "_temp/eidp-v109-wheel.whl",
        "_temp/kousei-application_form2.pdf",
        "_temp/kousei-gold-v2",
        "_temp/pdf-rca",
        "_temp/r7-window-check-db-abc",
        "_temp/saitama-current51-rerun-20260511-071951",
        "_temp/ui-smoke-20260507-120558",
        "_temp/v140_all_japan",
        "_temp/v408-r7-browser-eidp_master.xlsx",
        "_temp/win-v342-evidence",
        "_temp/win_setup_v104.code",
    ]


def test_apply_cleanup_deletes_only_reported_candidates(tmp_path: Path) -> None:
    temp = tmp_path / "_temp"
    generated = temp / "v99-extract-abc"
    keep = temp / "manual-reference"
    _touch(generated / "marker.txt")
    _touch(keep / "marker.txt")
    candidates = module.collect_candidates(temp)

    actions = module.apply_cleanup(temp, candidates)

    assert actions == [
        {
            "path": "_temp/v99-extract-abc",
            "reason": "generated pattern v*-extract-*",
            "kind": "dir",
            "bytes": 1,
            "deleted": True,
            "error": None,
        }
    ]
    assert not generated.exists()
    assert keep.exists()


def test_apply_cleanup_refuses_symlink(tmp_path: Path) -> None:
    temp = tmp_path / "_temp"
    target = tmp_path / "outside"
    target.mkdir()
    link = temp / "v99-extract-link"
    temp.mkdir()
    link.symlink_to(target, target_is_directory=True)
    candidate = module.CleanupCandidate(
        path="_temp/v99-extract-link",
        reason="generated pattern v*-extract-*",
        kind="dir",
        bytes=0,
    )

    actions = module.apply_cleanup(temp, [candidate])

    assert actions[0]["deleted"] is False
    assert actions[0]["error"] == "refusing symlink"
    assert link.is_symlink()
