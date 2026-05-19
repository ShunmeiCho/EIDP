"""Repair a stale Windows Streamlit launcher in an extracted EIDP root.

Runs as dry-run by default. Use --apply only after checking the reported target
path.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

LEGACY_TOKENS = ("-m streamlit.main run", "-m streamlit.main")
EXPECTED_TOKEN = "-m streamlit run"


def _write_text_atomic(path: Path, text: str) -> None:
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    try:
        tmp_path.write_text(text, encoding="utf-8", newline="")
        tmp_path.replace(path)
    finally:
        tmp_path.unlink(missing_ok=True)


def _launcher_path(root: Path) -> Path:
    return root / "scripts" / "launch.bat"


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
    if not launch_bat.is_file():
        result["errors"].append(f"launcher not found: {launch_bat}")
        return result

    body = launch_bat.read_text(encoding="utf-8")
    repaired, changed = _repair_body(body)
    result["would_update"] = changed

    if not changed:
        result["ok"] = EXPECTED_TOKEN in body and not any(token in body for token in LEGACY_TOKENS)
        if not result["ok"]:
            result["errors"].append(f"launcher missing expected token: {EXPECTED_TOKEN}")
        return result

    result["ok"] = True
    if not apply:
        return result

    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    backup = launch_bat.with_name(f"{launch_bat.name}.{stamp}.bak")
    backup.write_text(body, encoding="utf-8", newline="")
    _write_text_atomic(launch_bat, repaired)
    result["applied"] = True
    result["backup"] = str(backup)
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
