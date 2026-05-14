"""Archive known interrupted Stage 6 smoke artifacts.

The default mode is a dry run. Passing ``--apply`` moves only the configured
residual paths into a timestamped archive directory; it never deletes files.
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

from stage6_recovery_check import DEFAULT_INTERRUPTED_STAGE6_PATHS


@dataclass
class CleanupAction:
    raw_path: str
    path: str
    exists: bool
    destination: str | None = None
    moved: bool = False
    error: str | None = None


def _expand_windows_vars(raw_path: str) -> Path:
    expanded = raw_path
    user_profile = os.environ.get("USERPROFILE")
    if user_profile:
        expanded = expanded.replace("%USERPROFILE%", user_profile)
    if os.name != "nt":
        expanded = expanded.replace("\\", os.sep)
    return Path(os.path.expandvars(expanded))


def _is_under_user_profile(path: Path) -> bool:
    user_profile = os.environ.get("USERPROFILE")
    if not user_profile:
        return False
    try:
        path.resolve().relative_to(Path(user_profile).resolve())
    except ValueError:
        return False
    return True


def _unique_destination(archive_dir: Path, source: Path) -> Path:
    destination = archive_dir / source.name
    if not destination.exists():
        return destination
    stem = source.stem
    suffix = source.suffix
    if source.is_dir():
        stem = source.name
        suffix = ""
    for idx in range(2, 1000):
        candidate = archive_dir / f"{stem}-{idx}{suffix}"
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"could not choose unique archive path for {source}")


def _is_symlink_or_junction(path: Path) -> bool:
    if path.is_symlink():
        return True
    if os.name != "nt":
        return False
    try:
        return bool(getattr(path.stat(follow_symlinks=False), "st_file_attributes", 0) & 0x400)
    except OSError:
        return False


def _archive_by_rename(source: Path, destination: Path) -> None:
    try:
        source.replace(destination)
    except OSError as exc:
        raise OSError(f"rename failed; refusing copy/delete fallback: {exc}") from exc


def cleanup_residuals(
    *,
    app_root: Path,
    check_paths: list[str],
    archive_dir: Path | None,
    apply: bool,
    allow_outside_userprofile: bool = False,
) -> dict[str, Any]:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    resolved_archive_dir = archive_dir or (app_root / "logs" / "stage6-residual-archive" / stamp)
    actions: list[CleanupAction] = []

    for raw_path in check_paths:
        source = _expand_windows_vars(raw_path)
        action = CleanupAction(raw_path=raw_path, path=str(source), exists=source.exists())
        if not action.exists:
            actions.append(action)
            continue
        if not allow_outside_userprofile and not _is_under_user_profile(source):
            action.error = "refusing to move path outside USERPROFILE"
            actions.append(action)
            continue
        if _is_symlink_or_junction(source):
            action.error = "refusing to move symlink or junction"
            actions.append(action)
            continue
        destination = _unique_destination(resolved_archive_dir, source)
        action.destination = str(destination)
        if apply:
            try:
                resolved_archive_dir.mkdir(parents=True, exist_ok=True)
                _archive_by_rename(source, destination)
                action.moved = True
                action.exists = source.exists()
            except OSError as exc:
                action.error = str(exc)
        actions.append(action)

    existing = [action for action in actions if action.exists]
    errors = [action.error for action in actions if action.error]
    report = {
        "ok": not existing and not errors,
        "mode": "apply" if apply else "dry_run",
        "archive_dir": str(resolved_archive_dir),
        "actions": [asdict(action) for action in actions],
        "existing_count": len(existing),
        "moved_count": sum(1 for action in actions if action.moved),
        "errors": errors,
    }
    return report


def write_cleanup_log(app_root: Path, report: dict[str, Any]) -> Path:
    logs_dir = app_root / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    log_path = logs_dir / f"stage6-residual-cleanup-{stamp}.json"
    log_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return log_path


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app-root", default=".", help="Extracted EIDP application root.")
    parser.add_argument("--archive-dir", help="Destination directory for moved residual artifacts.")
    parser.add_argument("--check-path", action="append", default=[], help="Additional residual path to check.")
    parser.add_argument("--apply", action="store_true", help="Move residual artifacts into the archive directory.")
    parser.add_argument(
        "--allow-outside-userprofile",
        action="store_true",
        help="Allow archiving explicitly supplied paths outside USERPROFILE.",
    )
    parser.add_argument("--no-log", action="store_true", help="Do not write logs/stage6-residual-cleanup-*.json.")
    parser.add_argument("--json", action="store_true", help="Emit compact JSON.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    app_root = Path(args.app_root).resolve()
    check_paths = [*DEFAULT_INTERRUPTED_STAGE6_PATHS, *args.check_path]
    report = cleanup_residuals(
        app_root=app_root,
        check_paths=check_paths,
        archive_dir=Path(args.archive_dir).resolve() if args.archive_dir else None,
        apply=bool(args.apply),
        allow_outside_userprofile=bool(args.allow_outside_userprofile),
    )
    if not args.no_log:
        report["log_path"] = str(write_cleanup_log(app_root, report))
    output = (
        json.dumps(report, ensure_ascii=False, sort_keys=True)
        if args.json
        else json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    )
    print(output)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
