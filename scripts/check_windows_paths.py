"""Check repository/worktree paths for Windows-incompatible names."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from windows_path_safety import check_windows_safe_paths, render_issues  # noqa: E402

REPO_ROOT = SCRIPT_DIR.parent


def collect_git_paths(repo_root: Path, *, include_temp: bool = False) -> list[str]:
    """Collect tracked and untracked non-ignored paths from git."""
    cmd = ["git", "ls-files", "--cached", "--others", "--exclude-standard"]
    proc = subprocess.run(cmd, cwd=repo_root, check=True, text=True, capture_output=True)
    paths = [line for line in proc.stdout.splitlines() if line]
    if not include_temp:
        paths = [path for path in paths if not path.startswith("_temp/")]
    return paths


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check paths for Windows filesystem compatibility.")
    parser.add_argument("paths", nargs="*", help="Paths to check. Defaults to git tracked/untracked paths.")
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--include-temp", action="store_true", help="Include _temp/ in default git path collection")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    args = parser.parse_args(argv)

    paths = list(args.paths) if args.paths else collect_git_paths(args.repo_root, include_temp=args.include_temp)
    issues = check_windows_safe_paths(paths)

    if args.json:
        print(json.dumps([asdict(issue) for issue in issues], ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(render_issues(issues))
        print(f"checked_paths: {len(paths)}")
    return 0 if not issues else 1


if __name__ == "__main__":
    sys.exit(main())
