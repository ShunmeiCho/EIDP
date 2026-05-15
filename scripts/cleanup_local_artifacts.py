"""Prune local release/test artifacts that are safe to regenerate.

The script is intentionally conservative:

* dry-run by default;
* only scans one top-level temp directory;
* only removes known generated artifact name patterns;
* refuses symlinks and paths outside the temp directory;
* keeps the newest retroactive Excel app roots per fiscal year.
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

DEFAULT_TEMP_DIR = Path("_temp")
DEFAULT_KEEP_LATEST_RETROACTIVE_PER_FY = 2

GENERATED_TOP_LEVEL_PATTERNS = (
    "verify-v*",
    "v*-extract-*",
    "eidp-v*-verify.*",
    "eidp-v*-validate",
    "v*_vendor_build",
    "v*_vendor.zip",
    "ocr-addon-src",
    "playwright-addon-src",
)
AGGRESSIVE_TOP_LEVEL_PATTERNS = (
    "*-gold*",
    "*.json",
    "*.jsonl",
    "*.pdf",
    "*.html",
    "*.out",
    "*.bat",
    "*.code",
    "*.py",
    "*.ps1",
    "*.sqlite3",
    "*.txt",
    "*.whl",
    "*.xlsx",
    ".DS_Store",
    "__pycache__",
    "*-manual-v*",
    "*-no-candidate-current",
    "anime-*",
    "bootstrap-*",
    "chrome-*-profile*",
    "eidp-v*-smoke",
    "live-discovery-*",
    "mac-smoke-*",
    "manual-probes",
    "manual-rca*",
    "pdf-rca",
    "prefecture-*",
    "latest-*",
    "pdf-probes",
    "r7-window-check-*",
    "saitama-*",
    "school*-manual-*",
    "stage6-*",
    "tools",
    "ui-*",
    "v*_*",
    "v*_bounded*",
    "v*-mac-*",
    "v*-manual-rca",
    "v*-ohara-*",
    "v*-rca-*",
    "v*-retroactive",
    "v*-school*",
    "v*-targeted-replay*",
    "v*-windows-replay",
    "v*-windows-evidence",
    "windows-validation-progress",
    "win-v*-evidence",
    "win-v*-tokyo-probe",
    "eidp_v*.sqlite3",
)
RETROACTIVE_RE = re.compile(r"^non-windows-retroactive-fy(?P<fy>\d{4})-(?P<stamp>\d{8}-\d{6})$")


@dataclass(frozen=True)
class CleanupCandidate:
    path: str
    reason: str
    kind: str
    bytes: int


def _relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _is_safe_child(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return path.parent.resolve() == root.resolve()


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


def _retroactive_groups(temp_dir: Path) -> dict[str, list[Path]]:
    groups: dict[str, list[Path]] = {}
    for path in temp_dir.iterdir():
        match = RETROACTIVE_RE.match(path.name)
        if not match:
            continue
        groups.setdefault(match.group("fy"), []).append(path)
    for paths in groups.values():
        paths.sort(key=lambda item: item.name, reverse=True)
    return groups


def collect_candidates(
    temp_dir: Path,
    *,
    keep_paths: set[Path] | None = None,
    keep_latest_retroactive_per_fy: int = DEFAULT_KEEP_LATEST_RETROACTIVE_PER_FY,
    aggressive: bool = False,
) -> list[CleanupCandidate]:
    """Return top-level generated artifacts that can be pruned."""

    temp_dir = temp_dir.resolve()
    if not temp_dir.is_dir():
        return []
    keep_resolved = {path.resolve() for path in (keep_paths or set())}
    candidates: dict[Path, str] = {}

    patterns = (
        (*GENERATED_TOP_LEVEL_PATTERNS, *AGGRESSIVE_TOP_LEVEL_PATTERNS)
        if aggressive
        else GENERATED_TOP_LEVEL_PATTERNS
    )
    for pattern in patterns:
        for path in temp_dir.glob(pattern):
            candidates[path.resolve()] = f"generated pattern {pattern}"

    for paths in _retroactive_groups(temp_dir).values():
        for path in paths[max(0, keep_latest_retroactive_per_fy) :]:
            candidates[path.resolve()] = f"older than latest {keep_latest_retroactive_per_fy} retroactive roots"

    result: list[CleanupCandidate] = []
    for resolved, reason in sorted(candidates.items(), key=lambda item: item[0].name):
        if resolved in keep_resolved:
            continue
        if not _is_safe_child(resolved, temp_dir):
            continue
        if resolved.is_symlink():
            continue
        result.append(
            CleanupCandidate(
                path=_relative(resolved, temp_dir.parent.resolve()),
                reason=reason,
                kind="dir" if resolved.is_dir() else "file",
                bytes=_path_size(resolved),
            )
        )
    return result


def apply_cleanup(temp_dir: Path, candidates: list[CleanupCandidate]) -> list[dict[str, Any]]:
    temp_dir = temp_dir.resolve()
    actions: list[dict[str, Any]] = []
    for candidate in candidates:
        path = (temp_dir.parent / candidate.path).resolve()
        action: dict[str, Any] = {**asdict(candidate), "deleted": False, "error": None}
        unresolved_path = temp_dir.parent / candidate.path
        if unresolved_path.is_symlink():
            action["error"] = "refusing symlink"
            actions.append(action)
            continue
        if not _is_safe_child(path, temp_dir):
            action["error"] = "refusing path outside temp dir"
            actions.append(action)
            continue
        try:
            if path.is_dir():
                shutil.rmtree(path)
            elif path.exists():
                path.unlink()
            action["deleted"] = True
        except OSError as exc:
            action["error"] = str(exc)
        actions.append(action)
    return actions


def summarize(candidates: list[CleanupCandidate], *, actions: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    total_bytes = sum(candidate.bytes for candidate in candidates)
    deleted_bytes = 0
    if actions is not None:
        deleted_bytes = sum(int(action["bytes"]) for action in actions if action.get("deleted"))
    return {
        "ok": actions is None or all(not action.get("error") for action in actions),
        "candidate_count": len(candidates),
        "candidate_bytes": total_bytes,
        "deleted_count": sum(1 for action in actions or [] if action.get("deleted")),
        "deleted_bytes": deleted_bytes,
        "candidates": [asdict(candidate) for candidate in candidates],
        "actions": actions or [],
    }


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--temp-dir", type=Path, default=DEFAULT_TEMP_DIR)
    parser.add_argument("--keep", action="append", type=Path, default=[], help="Top-level artifact path to preserve.")
    parser.add_argument(
        "--keep-latest-retroactive-per-fy",
        type=int,
        default=DEFAULT_KEEP_LATEST_RETROACTIVE_PER_FY,
        help="How many non-windows-retroactive roots to keep per fiscal year.",
    )
    parser.add_argument("--apply", action="store_true", help="Delete candidates. Default is dry-run.")
    parser.add_argument(
        "--aggressive",
        action="store_true",
        help="Also prune probe/RCA/evidence/browser-profile temp artifacts. Still top-level-only and keep-aware.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    if args.keep_latest_retroactive_per_fy < 0:
        raise SystemExit("--keep-latest-retroactive-per-fy must be non-negative")
    candidates = collect_candidates(
        args.temp_dir,
        keep_paths=set(args.keep),
        keep_latest_retroactive_per_fy=args.keep_latest_retroactive_per_fy,
        aggressive=args.aggressive,
    )
    actions = apply_cleanup(args.temp_dir, candidates) if args.apply else None
    summary = summarize(candidates, actions=actions)
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    else:
        mode = "deleted" if args.apply else "would delete"
        mib = summary["candidate_bytes"] / 1024 / 1024
        print(f"{mode} {summary['candidate_count']} artifact(s), {mib:.1f} MiB candidate data")
        for candidate in candidates:
            print(f"- {candidate.path} ({candidate.reason})")
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
