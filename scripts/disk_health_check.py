"""Report EIDP disk usage against conservative retention thresholds.

This helper is read-only. It never deletes files; use the reported cleanup
hints to run the explicit pruning scripts after reviewing the candidates.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def mib(value: int) -> int:
    return value * 1024 * 1024


def gib(value: int) -> int:
    return value * 1024 * 1024 * 1024


@dataclass(frozen=True)
class DiskTarget:
    name: str
    path: Path
    warn_bytes: int
    block_bytes: int | None
    protected: bool = False
    cleanup_hint: str = ""


def _local_dev_targets() -> tuple[DiskTarget, ...]:
    return (
        DiskTarget(
            "project_total",
            Path("."),
            gib(5),
            gib(10),
            cleanup_hint="Inspect large ignored dirs before pruning; do not delete protected data.",
        ),
        DiskTarget(
            "_temp",
            Path("_temp"),
            mib(200),
            mib(500),
            cleanup_hint="Review generated test artifacts and remove only confirmed disposable files.",
        ),
        DiskTarget(
            "logs",
            Path("logs"),
            mib(200),
            mib(500),
            cleanup_hint="Review logs/ and keep only recent Linux/Web release evidence.",
        ),
        DiskTarget(
            "data",
            Path("data"),
            gib(1),
            None,
            protected=True,
            cleanup_hint="Protected: review manually; never delete eidp.sqlite3, manual-actions.jsonl, or master.xlsx.",
        ),
        DiskTarget(
            ".claude/worktrees",
            Path(".claude") / "worktrees",
            gib(1),
            gib(2),
            cleanup_hint="Remove completed worktrees through the owning tool, then run git worktree prune.",
        ),
    )


def _linux_server_targets() -> tuple[DiskTarget, ...]:
    return (
        DiskTarget(
            "app_root_total",
            Path("."),
            gib(10),
            gib(20),
            cleanup_hint="Review application data, logs, uploads, and generated exports below the project root.",
        ),
        DiskTarget(
            "data/pdfs",
            Path("data") / "pdfs",
            gib(5),
            gib(10),
            protected=True,
            cleanup_hint=(
                "Protected: run python scripts/prune_pdf_storage.py --json first; "
                "use --apply only after owner confirms candidates."
            ),
        ),
        DiskTarget(
            "data/output",
            Path("data") / "output",
            gib(1),
            gib(2),
            cleanup_hint="Archive or remove old Excel outputs after owner sign-off.",
        ),
        DiskTarget(
            "logs",
            Path("logs"),
            mib(200),
            mib(500),
            cleanup_hint="Weekly and structlog retention should keep this bounded; investigate if it grows.",
        ),
        DiskTarget(
            "data/audit/manual-actions.jsonl",
            Path("data") / "audit" / "manual-actions.jsonl",
            mib(100),
            None,
            protected=True,
            cleanup_hint=(
                "Protected append-only audit outbox; rotate only through "
                "python scripts/rotate_audit_outbox.py --json."
            ),
        ),
    )


PROFILES = {
    "linux-server": _linux_server_targets,
    "local-dev": _local_dev_targets,
}


def _path_size(path: Path) -> int:
    if not path.exists() or path.is_symlink():
        return 0
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


def _human_bytes(value: int) -> str:
    units = ("B", "KiB", "MiB", "GiB", "TiB")
    amount = float(value)
    for unit in units:
        if amount < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(amount)} {unit}"
            return f"{amount:.1f} {unit}"
        amount /= 1024
    return f"{value} B"


def evaluate_target(root: Path, target: DiskTarget) -> dict[str, Any]:
    path = (root / target.path).resolve()
    size = _path_size(path)
    if not path.exists():
        status = "missing"
    elif target.block_bytes is not None and size >= target.block_bytes:
        status = "block"
    elif size >= target.warn_bytes:
        status = "warn"
    else:
        status = "ok"
    return {
        "name": target.name,
        "path": str(target.path),
        "exists": path.exists(),
        "bytes": size,
        "human": _human_bytes(size),
        "warn_bytes": target.warn_bytes,
        "block_bytes": target.block_bytes,
        "status": status,
        "protected": target.protected,
        "cleanup_hint": target.cleanup_hint,
    }


def evaluate_profile(root: Path, profile: str) -> dict[str, Any]:
    targets = PROFILES[profile]()
    entries = [evaluate_target(root, target) for target in targets]
    block_count = sum(1 for entry in entries if entry["status"] == "block")
    warn_count = sum(1 for entry in entries if entry["status"] == "warn")
    return {
        "ok": block_count == 0,
        "profile": profile,
        "root": str(root.resolve()),
        "warn_count": warn_count,
        "block_count": block_count,
        "entries": entries,
    }


def _default_profile() -> str:
    return "local-dev"


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--profile", choices=sorted(PROFILES), default=_default_profile())
    parser.add_argument("--fail-on-warn", action="store_true")
    parser.add_argument("--fail-on-block", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def _print_text(summary: dict[str, Any]) -> None:
    print(
        f"disk health profile={summary['profile']} "
        f"warn={summary['warn_count']} block={summary['block_count']}"
    )
    for entry in summary["entries"]:
        print(f"- {entry['status']}: {entry['path']} {entry['human']}")
        if entry["status"] in {"warn", "block"} and entry["cleanup_hint"]:
            print(f"  cleanup: {entry['cleanup_hint']}")
        if entry["protected"]:
            print("  protected: true")


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    summary = evaluate_profile(args.root, args.profile)
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        _print_text(summary)
    if args.fail_on_block and summary["block_count"]:
        return 1
    if args.fail_on_warn and (summary["warn_count"] or summary["block_count"]):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
