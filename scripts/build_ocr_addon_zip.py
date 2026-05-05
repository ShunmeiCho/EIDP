"""Build the optional OCR add-on ZIP for Windows operator installs.

The core EIDP ZIP intentionally does not bundle Tesseract. When the OCR
add-on is approved for beta distribution, this script packages a prepared
Windows Tesseract directory and tessdata directory into the runtime layout
that ``eidp.ocr.tesseract`` already detects:

    ocr-addon/tesseract/tesseract.exe
    ocr-addon/tessdata/jpn.traineddata

The script does not download binaries. That keeps licensing/source selection
as an explicit release-engineering step and makes this packager fully
testable on macOS.
"""

from __future__ import annotations

import argparse
import json
import sys
import zipfile
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_ZIP = REPO_ROOT / "dist" / "eidp-ocr-addon-windows.zip"

# Shared with build_playwright_addon_zip + verify_windows_distribution.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _packaging_lib import iter_payload_files, sha256_file  # noqa: E402


class OcrAddonError(RuntimeError):
    """Raised when the source layout cannot satisfy the runtime contract."""


def collect_ocr_addon_members(
    *,
    tesseract_dir: Path,
    tessdata_dir: Path,
) -> list[tuple[Path, str]]:
    """Return ``(source, arcname)`` pairs for the OCR add-on ZIP.

    ``tesseract_dir`` is copied recursively because Windows Tesseract
    distributions ship DLLs next to ``tesseract.exe``. ``tessdata_dir`` is
    restricted to ``*.traineddata`` files so local READMEs/cache files do not
    leak into the operator package.
    """
    if not tesseract_dir.is_dir():
        raise OcrAddonError(f"tesseract dir does not exist: {tesseract_dir}")
    if not tessdata_dir.is_dir():
        raise OcrAddonError(f"tessdata dir does not exist: {tessdata_dir}")

    tesseract_exe = tesseract_dir / "tesseract.exe"
    if not tesseract_exe.is_file():
        raise OcrAddonError(f"missing required tesseract.exe: {tesseract_exe}")
    jpn = tessdata_dir / "jpn.traineddata"
    if not jpn.is_file():
        raise OcrAddonError(f"missing required jpn.traineddata: {jpn}")

    members: list[tuple[Path, str]] = []
    for path in iter_payload_files(tesseract_dir):
        arc = "ocr-addon/tesseract/" + path.relative_to(tesseract_dir).as_posix()
        members.append((path, arc))
    for path in iter_payload_files(tessdata_dir):
        if path.suffix == ".traineddata":
            arc = "ocr-addon/tessdata/" + path.relative_to(tessdata_dir).as_posix()
            members.append((path, arc))
    return members


def build_manifest(members: list[tuple[Path, str]]) -> dict[str, Any]:
    files = [
        {
            "path": arc,
            "size": src.stat().st_size,
            "sha256": sha256_file(src),
        }
        for src, arc in sorted(members, key=lambda item: item[1])
    ]
    return {
        "layout_version": 1,
        "required": {
            "tesseract": "ocr-addon/tesseract/tesseract.exe",
            "jpn_traineddata": "ocr-addon/tessdata/jpn.traineddata",
        },
        "files": files,
    }


def build_ocr_addon_zip(
    *,
    tesseract_dir: Path,
    tessdata_dir: Path,
    out_zip: Path = DEFAULT_OUT_ZIP,
) -> Path:
    members = collect_ocr_addon_members(
        tesseract_dir=tesseract_dir,
        tessdata_dir=tessdata_dir,
    )
    manifest = build_manifest(members)

    out_zip.parent.mkdir(parents=True, exist_ok=True)
    if out_zip.exists():
        out_zip.unlink()
    with zipfile.ZipFile(out_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for src, arc in members:
            zf.write(src, arc)
        zf.writestr(
            "ocr-addon/MANIFEST.json",
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        )
    return out_zip


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tesseract-dir", type=Path, required=True)
    parser.add_argument("--tessdata-dir", type=Path, required=True)
    parser.add_argument("--out-zip", type=Path, default=DEFAULT_OUT_ZIP)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    out = build_ocr_addon_zip(
        tesseract_dir=args.tesseract_dir,
        tessdata_dir=args.tessdata_dir,
        out_zip=args.out_zip,
    )
    print(json.dumps({"out_zip": str(out)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
