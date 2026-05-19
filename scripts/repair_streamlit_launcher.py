"""Repair a stale Windows Streamlit launcher in an extracted EIDP root.

Runs as dry-run by default. Use --apply only after checking the reported target
path.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import sys
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

LEGACY_TOKENS = ("-m streamlit.main run", "-m streamlit.main")
EXPECTED_TOKEN = "-m streamlit run"


def _write_text_atomic(path: Path, text: str) -> None:
    tmp_path = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        tmp_path.write_text(text, encoding="utf-8", newline="")
        tmp_path.replace(path)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise


def _launcher_path(root: Path) -> Path:
    return root / "scripts" / "launch.bat"


def _launcher_body_ok(body: str) -> bool:
    return EXPECTED_TOKEN in body and not any(token in body for token in LEGACY_TOKENS)


def _resolve_launcher(root: Path) -> tuple[Path, Path]:
    root_resolved = root.resolve(strict=True)
    launch_bat = _launcher_path(root_resolved)
    try:
        launch_resolved = launch_bat.resolve(strict=True)
    except FileNotFoundError as exc:
        raise ValueError(f"launcher not found: {launch_bat}") from exc
    if launch_resolved != launch_bat:
        raise ValueError(f"launcher must not be a symlink or escape root: {launch_bat} -> {launch_resolved}")
    if not launch_resolved.is_file():
        raise ValueError(f"launcher not found: {launch_bat}")
    return root_resolved, launch_resolved


def _unique_backup_path(launch_bat: Path) -> Path:
    for _ in range(10):
        stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S-%f")
        candidate = launch_bat.with_name(f"{launch_bat.name}.{stamp}-{uuid.uuid4().hex[:8]}.bak")
        if not candidate.exists():
            return candidate
    raise FileExistsError(f"could not allocate unique backup path for {launch_bat}")


def _write_backup(backup: Path, body: str) -> None:
    with backup.open("x", encoding="utf-8", newline="") as handle:
        handle.write(body)


@contextlib.contextmanager
def _repair_lock(root: Path) -> Iterator[None]:
    src_path = root / "src"
    if src_path.is_dir():
        sys.path.insert(0, str(src_path))
    try:
        from eidp.db.locking import LockBusyError, acquire_lock
    except Exception as exc:
        raise RuntimeError(f"could not load EIDP app lock for launcher repair: {type(exc).__name__}: {exc}") from exc
    finally:
        if src_path.is_dir():
            try:
                sys.path.remove(str(src_path))
            except ValueError:
                pass

    try:
        with acquire_lock(root / "data" / ".lock", owner="repair_streamlit_launcher"):
            yield
    except LockBusyError as exc:
        raise RuntimeError(f"could not acquire EIDP app lock for launcher repair: {exc}") from exc


def _repair_body(body: str) -> tuple[str, bool]:
    repaired = body
    for token in LEGACY_TOKENS:
        repaired = repaired.replace(token, EXPECTED_TOKEN)
    return repaired, repaired != body


def repair_launcher(root: Path, *, apply: bool = False) -> dict[str, Any]:
    """Inspect or repair root/scripts/launch.bat for the streamlit.main bug."""

    launch_bat = _launcher_path(root)
    result: dict[str, Any] = {
        "ok": False,
        "applied": False,
        "would_update": False,
        "root": str(root),
        "launcher": str(launch_bat),
        "backup": None,
        "errors": [],
    }
    try:
        root_resolved, launch_bat = _resolve_launcher(root)
    except (OSError, ValueError) as exc:
        result["errors"].append(str(exc))
        return result
    result["root"] = str(root_resolved)
    result["launcher"] = str(launch_bat)

    body = launch_bat.read_text(encoding="utf-8")
    repaired, changed = _repair_body(body)
    result["would_update"] = changed

    if not changed:
        result["ok"] = _launcher_body_ok(body)
        if not result["ok"]:
            result["errors"].append(f"launcher missing expected token: {EXPECTED_TOKEN}")
        return result

    result["ok"] = True
    if not apply:
        return result

    result["ok"] = False
    try:
        with _repair_lock(root_resolved):
            body = launch_bat.read_text(encoding="utf-8")
            repaired, changed = _repair_body(body)
            result["would_update"] = changed
            if not changed:
                result["ok"] = _launcher_body_ok(body)
                if not result["ok"]:
                    result["errors"].append(f"launcher missing expected token: {EXPECTED_TOKEN}")
                return result

            backup = _unique_backup_path(launch_bat)
            if backup.exists():
                raise FileExistsError(f"backup already exists: {backup}")
            _write_backup(backup, body)
            result["backup"] = str(backup)
            _write_text_atomic(launch_bat, repaired)

            final_body = launch_bat.read_text(encoding="utf-8")
            if not _launcher_body_ok(final_body):
                try:
                    _write_text_atomic(launch_bat, backup.read_text(encoding="utf-8"))
                except OSError as restore_exc:
                    result["errors"].append(
                        "post-repair validation failed and rollback failed: "
                        f"{type(restore_exc).__name__}: {restore_exc}"
                    )
                    return result
                result["errors"].append("post-repair validation failed; restored original launcher from backup")
                return result

            result["ok"] = True
            result["applied"] = True
    except FileExistsError as exc:
        result["errors"].append(str(exc))
    except (OSError, RuntimeError) as exc:
        result["errors"].append(str(exc))
    return result


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", type=Path, default=Path.cwd(), help="Extracted EIDP root.")
    parser.add_argument("--apply", action="store_true", help="Rewrite scripts/launch.bat and create a .bak backup.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    result = repair_launcher(args.root, apply=args.apply)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    else:
        if result["applied"]:
            print(f"repaired launcher: {result['launcher']}")
            print(f"backup: {result['backup']}")
        elif result["would_update"]:
            print(f"would repair launcher: {result['launcher']}")
            print("rerun with --apply to write the fix")
        elif result["ok"]:
            print(f"launcher already ok: {result['launcher']}")
        else:
            print("; ".join(str(error) for error in result["errors"]), file=sys.stderr)
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
