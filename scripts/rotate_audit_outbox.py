"""Rotate the derived manual-action JSONL outbox when it grows too large.

Dry-run by default. The database remains authoritative; this script only moves
``data/audit/manual-actions.jsonl`` to a sibling archive name that
``eidp.db.audit_outbox`` already scans for deduplication.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

DEFAULT_JSONL_PATH = Path("data") / "audit" / "manual-actions.jsonl"
DEFAULT_MAX_BYTES = 100 * 1024 * 1024
PROTECTED_OUTBOX_NAME = "manual-actions.jsonl"


@dataclass(frozen=True)
class RotationPlan:
    jsonl_path: str
    archive_path: str | None
    bytes: int
    rotate: bool
    reason: str


def _relative(path: Path, base: Path) -> str:
    try:
        return path.resolve().relative_to(base.resolve()).as_posix()
    except ValueError:
        return str(path)


def _is_under(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def _fsync_file(path: Path) -> None:
    with path.open("ab") as fh:
        fh.flush()
        os.fsync(fh.fileno())


def _fsync_directory(path: Path) -> None:
    try:
        fd = os.open(path, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _unique_archive_path(jsonl_path: Path, stamp: str | None = None) -> Path:
    stamp = stamp or datetime.now().strftime("%Y%m%d-%H%M%S")
    base = jsonl_path.with_name(f"{jsonl_path.stem}-{stamp}.jsonl")
    if not base.exists():
        return base
    for idx in range(2, 1000):
        candidate = jsonl_path.with_name(f"{jsonl_path.stem}-{stamp}-{idx}.jsonl")
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"could not choose unique archive path for {jsonl_path}")


def plan_rotation(
    *,
    app_root: Path,
    jsonl_path: Path = DEFAULT_JSONL_PATH,
    max_bytes: int = DEFAULT_MAX_BYTES,
    force: bool = False,
    stamp: str | None = None,
) -> RotationPlan:
    if max_bytes < 0:
        raise ValueError("max_bytes must be non-negative")
    root = app_root.resolve()
    target = root / jsonl_path if not jsonl_path.is_absolute() else jsonl_path
    audit_root = (root / "data" / "audit").resolve()
    target_label = _relative(target, root)

    if target.name != PROTECTED_OUTBOX_NAME:
        return RotationPlan(target_label, None, 0, False, "refusing non manual-actions.jsonl path")
    if target.is_symlink():
        return RotationPlan(target_label, None, 0, False, "refusing symlink")
    if not _is_under(target, audit_root):
        return RotationPlan(target_label, None, 0, False, "refusing path outside data/audit")
    if not target.exists():
        return RotationPlan(target_label, None, 0, False, "missing outbox")
    if not target.is_file():
        return RotationPlan(target_label, None, 0, False, "outbox is not a file")

    size = target.stat().st_size
    if not force and size < max_bytes:
        return RotationPlan(target_label, None, size, False, f"below max_bytes {max_bytes}")

    archive_path = _unique_archive_path(target, stamp=stamp)
    return RotationPlan(
        target_label,
        _relative(archive_path, root),
        size,
        True,
        "forced rotation" if force else f"at or above max_bytes {max_bytes}",
    )


def apply_rotation(app_root: Path, plan: RotationPlan) -> dict[str, Any]:
    action: dict[str, Any] = {**asdict(plan), "rotated": False, "error": None}
    if not plan.rotate or plan.archive_path is None:
        return action

    root = app_root.resolve()
    target = (root / plan.jsonl_path).resolve()
    archive = (root / plan.archive_path).resolve()
    try:
        if target.is_symlink():
            action["error"] = "refusing symlink"
            return action
        if archive.exists():
            action["error"] = "archive already exists"
            return action
        archive.parent.mkdir(parents=True, exist_ok=True)
        target.replace(archive)
        target.touch(exist_ok=False)
        _fsync_file(archive)
        _fsync_file(target)
        _fsync_directory(target.parent)
        action["rotated"] = True
    except OSError as exc:
        action["error"] = str(exc)
    return action


def summarize(plan: RotationPlan, action: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "ok": action is None or action.get("error") is None,
        "plan": asdict(plan),
        "action": action or {},
    }


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app-root", type=Path, default=Path.cwd())
    parser.add_argument("--jsonl-path", type=Path, default=DEFAULT_JSONL_PATH)
    parser.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES)
    parser.add_argument("--force", action="store_true", help="Rotate even when below max-bytes.")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Move the active outbox to an archive. Default is dry-run.",
    )
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    plan = plan_rotation(
        app_root=args.app_root,
        jsonl_path=args.jsonl_path,
        max_bytes=args.max_bytes,
        force=args.force,
    )
    action = apply_rotation(args.app_root, plan) if args.apply else None
    summary = summarize(plan, action)
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    else:
        mode = "rotated" if args.apply else "would rotate"
        if plan.rotate:
            print(f"{mode} {plan.jsonl_path} -> {plan.archive_path} ({plan.bytes} bytes)")
        else:
            print(f"no rotation for {plan.jsonl_path}: {plan.reason}")
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
