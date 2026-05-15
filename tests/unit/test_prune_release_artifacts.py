from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "prune_release_artifacts.py"
spec = importlib.util.spec_from_file_location("prune_release_artifacts", SCRIPT_PATH)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def _touch(path: Path, size: int = 1) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x" * size)


def test_collect_candidates_prunes_old_dist_packages_while_keeping_explicit_fallback(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    for version in [442, 444, 445]:
        _touch(dist / f"eidp-windows-v{version}.zip", 10)
        _touch(dist / f"eidp-windows-v{version}.zip.sha256", 1)
    _touch(dist / "eidp-windows.zip", 10)

    candidates = module.collect_candidates(
        base=tmp_path,
        dist_dir=dist,
        keep_latest=1,
        keep_versions={442},
    )

    assert [candidate.path for candidate in candidates] == [
        "dist/eidp-windows-v444.zip",
        "dist/eidp-windows-v444.zip.sha256",
    ]


def test_collect_candidates_prunes_old_windows_staging_and_deploy_dirs(tmp_path: Path) -> None:
    staging = tmp_path / "EIDP-staging"
    deploy_parent = tmp_path / "Users" / "cyo20"
    for version in [442, 444, 445]:
        _touch(staging / f"eidp-windows-v{version}.zip", 10)
        _touch(staging / f"eidp-windows-v{version}.zip.sha256", 1)
        _touch(deploy_parent / f"EIDP-v{version}-abcdef0" / "BUILD_INFO.json", 2)
    _touch(deploy_parent / "EIDP-not-a-release" / "marker.txt", 2)

    candidates = module.collect_candidates(
        base=tmp_path,
        staging_dir=staging,
        deploy_parent=deploy_parent,
        keep_latest=1,
        keep_versions={442},
    )

    assert [candidate.path for candidate in candidates] == [
        "EIDP-staging/eidp-windows-v444.zip",
        "EIDP-staging/eidp-windows-v444.zip.sha256",
        "Users/cyo20/EIDP-v444-abcdef0",
    ]


def test_apply_cleanup_deletes_only_reported_release_artifacts(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    old_zip = dist / "eidp-windows-v444.zip"
    keep_zip = dist / "eidp-windows-v445.zip"
    _touch(old_zip)
    _touch(keep_zip)

    candidates = module.collect_candidates(base=tmp_path, dist_dir=dist, keep_latest=1)
    actions = module.apply_cleanup(tmp_path, candidates)

    assert actions == [
        {
            "path": "dist/eidp-windows-v444.zip",
            "version": 444,
            "kind": "file",
            "bytes": 1,
            "reason": "older than kept package versions [445]",
            "deleted": True,
            "error": None,
        }
    ]
    assert not old_zip.exists()
    assert keep_zip.exists()


def test_collect_candidates_refuses_symlink(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    outside = tmp_path / "outside.zip"
    _touch(outside)
    dist.mkdir()
    (dist / "eidp-windows-v444.zip").symlink_to(outside)
    _touch(dist / "eidp-windows-v445.zip")

    candidates = module.collect_candidates(base=tmp_path, dist_dir=dist, keep_latest=1)

    assert candidates == []
