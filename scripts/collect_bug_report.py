"""Build a sanitized local bug-report ZIP.

This is Phase 1 only: local bundle generation for tester/operator handoff.
It never uploads data and never writes to the application database.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from eidp.bug_signals.bundle import build_bug_report_bundle, scrub_json_value  # noqa: E402
from eidp.config import settings  # noqa: E402


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=settings.app_root, help="Extracted EIDP app root.")
    parser.add_argument("--out", type=Path, default=None, help="Output ZIP path.")
    parser.add_argument("--note", default="", help="Operator note to include in sanitized manifest.")
    parser.add_argument("--json", action="store_true", help="Emit compact JSON.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    result = build_bug_report_bundle(args.root, out_path=args.out, operator_note=args.note)
    display_result = scrub_json_value(result)
    if args.json:
        print(json.dumps(display_result, ensure_ascii=False, sort_keys=True))
    else:
        print(json.dumps(display_result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
