"""Prune generated EIDP release ZIPs and extracted Windows deploy dirs.

Dry-run by default. The script only matches versioned EIDP release artifacts:

* dist/eidp-windows-vNNN.zip and .zip.sha256
* staging/eidp-windows-vNNN.zip and .zip.sha256
* deploy-parent/EIDP-vNNN-<commit>

It never scans data/, logs/, output/, SQLite files, master.xlsx, or audit JSONL.
Use --keep-version for non-latest fallback packages that must be retained.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

PACKAGE_RE = re.compile(r"^eidp-windows-v(?P<version>\d+)\.zip(?:\.sha256)?$")
DEPLOY_RE = re.compile(r"^EIDP-v(?P<version>\d+)-[0-9A-Za-z]+$")


@dataclass(frozen=True)
class ReleaseArtifact:
    path: str
    version: int
    kind: str
    bytes: int
    reason: str


def _is_safe_direct_child(path: Path, root: Path) -> bool:
    try:
        resolved = path.resolve()
        resolved.relative_to(root.resolve())
    except ValueError:
        return False
    return resolved.parent == root.resolve()


def _path_size(path: Path) -> int:
    if path.is_file():
        return path.stat().st_size
    total = 0
    for child in path.rglob("*"):
        try:
            if child.is_file() and not child.is_symlink():
                total += child.stat().st_size
        except OSError:
            continue
    return total


def _relative(path: Path, base: Path) -> str:
    try:
        return path.resolve().relative_to(base.resolve()).as_posix()
    except ValueError:
        return str(path)


def _versions_under(root: Path, regex: re.Pattern[str]) -> set[int]:
    if not root.is_dir():
        return set()
    versions: set[int] = set()
    for path in root.iterdir():
        match = regex.match(path.name)
        if match:
            versions.add(int(match.group("version")))
    return versions


def _kept_versions(
    versions: set[int],
    *,
    keep_latest: int,
    keep_versions: set[int],
) -> set[int]:
    kept = set(keep_versions)
    kept.update(sorted(versions, reverse=True)[: max(0, keep_latest)])
    return kept


def collect_candidates(
    *,
    base: Path,
    dist_dir: Path | None = None,
    staging_dir: Path | None = None,
    deploy_parent: Path | None = None,
    keep_latest: int = 2,
    keep_versions: set[int] | None = None,
) -> list[ReleaseArtifact]:
    keep_versions = keep_versions or set()
    candidates: list[ReleaseArtifact] = []

    package_roots = [root for root in (dist_dir, staging_dir) if root is not None]
    package_versions: set[int] = set()
    for root in package_roots:
        package_versions.update(_versions_under(root, PACKAGE_RE))
    kept_packages = _kept_versions(package_versions, keep_latest=keep_latest, keep_versions=keep_versions)

    for root in package_roots:
        if not root.is_dir():
            continue
        for path in root.iterdir():
            match = PACKAGE_RE.match(path.name)
            if not match:
                continue
            version = int(match.group("version"))
            if version in kept_packages:
                continue
            if path.is_symlink() or not _is_safe_direct_child(path, root):
                continue
            candidates.append(
                ReleaseArtifact(
                    path=_relative(path, base),
                    version=version,
                    kind="file",
                    bytes=_path_size(path),
                    reason=f"older than kept package versions {sorted(kept_packages)}",
                )
            )

    if deploy_parent is not None and deploy_parent.is_dir():
        deploy_versions = _versions_under(deploy_parent, DEPLOY_RE)
        kept_deploys = _kept_versions(deploy_versions, keep_latest=keep_latest, keep_versions=keep_versions)
        for path in deploy_parent.iterdir():
            match = DEPLOY_RE.match(path.name)
            if not match:
                continue
            version = int(match.group("version"))
            if version in kept_deploys:
                continue
            if path.is_symlink() or not path.is_dir() or not _is_safe_direct_child(path, deploy_parent):
                continue
            candidates.append(
                ReleaseArtifact(
                    path=_relative(path, base),
                    version=version,
                    kind="dir",
                    bytes=_path_size(path),
                    reason=f"older than kept deploy versions {sorted(kept_deploys)}",
                )
            )

    return sorted(candidates, key=lambda item: (item.version, item.path))


def apply_cleanup(base: Path, candidates: list[ReleaseArtifact]) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    for candidate in candidates:
        path = (base / candidate.path).resolve()
        action: dict[str, Any] = {**asdict(candidate), "deleted": False, "error": None}
        if path.is_symlink():
            action["error"] = "refusing symlink"
        elif candidate.kind == "dir" and path.is_dir():
            shutil.rmtree(path)
            action["deleted"] = True
        elif candidate.kind == "file" and path.is_file():
            path.unlink()
            action["deleted"] = True
        elif path.exists():
            action["error"] = "candidate kind mismatch"
        actions.append(action)
    return actions


def summarize(candidates: list[ReleaseArtifact], actions: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {
        "ok": actions is None or all(not action["error"] for action in actions),
        "candidate_count": len(candidates),
        "candidate_bytes": sum(candidate.bytes for candidate in candidates),
        "deleted_count": sum(1 for action in actions or [] if action.get("deleted")),
        "deleted_bytes": sum(int(action["bytes"]) for action in actions or [] if action.get("deleted")),
        "candidates": [asdict(candidate) for candidate in candidates],
        "actions": actions or [],
    }


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, default=Path.cwd(), help="Base path for relative output.")
    parser.add_argument("--dist-dir", type=Path, default=Path("dist"))
    parser.add_argument("--staging-dir", type=Path, default=None)
    parser.add_argument("--deploy-parent", type=Path, default=None)
    parser.add_argument("--keep-latest", type=int, default=2)
    parser.add_argument("--keep-version", action="append", type=int, default=[])
    parser.add_argument("--apply", action="store_true", help="Delete candidates. Default is dry-run.")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    if args.keep_latest < 0:
        raise SystemExit("--keep-latest must be non-negative")
    base = args.base.resolve()
    candidates = collect_candidates(
        base=base,
        dist_dir=args.dist_dir,
        staging_dir=args.staging_dir,
        deploy_parent=args.deploy_parent,
        keep_latest=args.keep_latest,
        keep_versions=set(args.keep_version),
    )
    actions = apply_cleanup(base, candidates) if args.apply else None
    summary = summarize(candidates, actions)
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    else:
        mode = "deleted" if args.apply else "would delete"
        mib = summary["candidate_bytes"] / 1024 / 1024
        print(f"{mode} {summary['candidate_count']} release artifact(s), {mib:.1f} MiB candidate data")
        for candidate in candidates:
            print(f"- {candidate.path} ({candidate.reason})")
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
