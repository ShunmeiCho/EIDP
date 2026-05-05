"""Build the optional Playwright/Chromium add-on ZIP.

The Windows core package is HTTP-first. Playwright is kept outside the core ZIP
because the Python package and browser payload are large and not required for
the standard prefecture-aggregator flow.

This script packages already-prepared assets; it does not download Chromium or
resolve wheels. Release engineering should prepare:

* a wheelhouse containing the Playwright Windows wheels;
* an ``ms-playwright`` browser directory containing Chromium.

The resulting ZIP layout is:

    playwright-addon/wheelhouse/*.whl
    playwright-addon/ms-playwright/...
    playwright-addon/MANIFEST.json
"""

from __future__ import annotations

import argparse
import json
import sys
import zipfile
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_ZIP = REPO_ROOT / "dist" / "eidp-playwright-addon-windows.zip"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _packaging_lib import iter_payload_files, sha256_file  # noqa: E402


class PlaywrightAddonError(RuntimeError):
    """Raised when the prepared Playwright add-on assets are incomplete."""


def _has_chromium_executable(browsers_dir: Path) -> bool:
    for path in browsers_dir.rglob("chrome.exe"):
        if path.is_file() and "chromium" in path.as_posix().lower():
            return True
    return False


def collect_playwright_addon_members(
    *,
    wheelhouse: Path,
    browsers_dir: Path,
) -> list[tuple[Path, str]]:
    if not wheelhouse.is_dir():
        raise PlaywrightAddonError(f"wheelhouse does not exist: {wheelhouse}")
    if not browsers_dir.is_dir():
        raise PlaywrightAddonError(f"ms-playwright browser dir does not exist: {browsers_dir}")

    wheels = sorted(wheelhouse.glob("*.whl"))
    if not any(path.name.startswith("playwright-") for path in wheels):
        raise PlaywrightAddonError(f"missing playwright wheel in {wheelhouse}")
    if not _has_chromium_executable(browsers_dir):
        raise PlaywrightAddonError(f"missing Chromium chrome.exe under {browsers_dir}")

    members: list[tuple[Path, str]] = []
    for path in wheels:
        members.append((path, f"playwright-addon/wheelhouse/{path.name}"))
    for path in iter_payload_files(browsers_dir):
        arc = "playwright-addon/ms-playwright/" + path.relative_to(browsers_dir).as_posix()
        members.append((path, arc))
    return members


def build_manifest(members: list[tuple[Path, str]]) -> dict[str, Any]:
    return {
        "layout_version": 1,
        "required": {
            "wheelhouse": "playwright-addon/wheelhouse",
            "browsers": "playwright-addon/ms-playwright",
        },
        "files": [
            {
                "path": arc,
                "size": src.stat().st_size,
                "sha256": sha256_file(src),
            }
            for src, arc in sorted(members, key=lambda item: item[1])
        ],
    }


def build_playwright_addon_zip(
    *,
    wheelhouse: Path,
    browsers_dir: Path,
    out_zip: Path = DEFAULT_OUT_ZIP,
) -> Path:
    members = collect_playwright_addon_members(
        wheelhouse=wheelhouse,
        browsers_dir=browsers_dir,
    )
    manifest = build_manifest(members)

    out_zip.parent.mkdir(parents=True, exist_ok=True)
    if out_zip.exists():
        out_zip.unlink()
    with zipfile.ZipFile(out_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for src, arc in members:
            zf.write(src, arc)
        zf.writestr(
            "playwright-addon/MANIFEST.json",
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        )
    return out_zip


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheelhouse", type=Path, required=True)
    parser.add_argument("--browsers-dir", type=Path, required=True)
    parser.add_argument("--out-zip", type=Path, default=DEFAULT_OUT_ZIP)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    out = build_playwright_addon_zip(
        wheelhouse=args.wheelhouse,
        browsers_dir=args.browsers_dir,
        out_zip=args.out_zip,
    )
    print(json.dumps({"out_zip": str(out)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
