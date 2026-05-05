"""Sprint 8.7.c — OCR add-on ZIP layout.

The runtime detector looks for:

    ocr-addon/tesseract/tesseract.exe
    ocr-addon/tessdata/jpn.traineddata

These tests pin the packaging side of that contract without downloading any
real Tesseract binaries on Mac.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import zipfile
from pathlib import Path

import pytest

SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "build_ocr_addon_zip.py"
spec = importlib.util.spec_from_file_location("build_ocr_addon_zip", SCRIPT_PATH)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)

OcrAddonError = module.OcrAddonError
build_ocr_addon_zip = module.build_ocr_addon_zip
collect_ocr_addon_members = module.collect_ocr_addon_members


def _fixture_layout(tmp_path: Path) -> tuple[Path, Path]:
    tess = tmp_path / "tesseract-src"
    tess.mkdir()
    (tess / "tesseract.exe").write_bytes(b"PE")
    (tess / "libtesseract.dll").write_bytes(b"DLL")
    (tess / "doc.txt").write_text("ignored? no, included", encoding="utf-8")
    (tess / "__pycache__").mkdir()
    (tess / "__pycache__" / "junk.pyc").write_bytes(b"x")

    tessdata = tmp_path / "tessdata-src"
    tessdata.mkdir()
    (tessdata / "jpn.traineddata").write_bytes(b"jpn")
    (tessdata / "eng.traineddata").write_bytes(b"eng")
    (tessdata / "README").write_text("ignored", encoding="utf-8")
    return tess, tessdata


def test_collect_ocr_addon_members_matches_runtime_layout(tmp_path: Path) -> None:
    tess, tessdata = _fixture_layout(tmp_path)

    members = collect_ocr_addon_members(tesseract_dir=tess, tessdata_dir=tessdata)
    arcs = {arc for _, arc in members}

    assert "ocr-addon/tesseract/tesseract.exe" in arcs
    assert "ocr-addon/tesseract/libtesseract.dll" in arcs
    assert "ocr-addon/tesseract/doc.txt" in arcs
    assert "ocr-addon/tessdata/jpn.traineddata" in arcs
    assert "ocr-addon/tessdata/eng.traineddata" in arcs
    assert "ocr-addon/tessdata/README" not in arcs
    assert all("__pycache__" not in arc for arc in arcs)


def test_build_ocr_addon_zip_writes_manifest_and_expected_files(tmp_path: Path) -> None:
    tess, tessdata = _fixture_layout(tmp_path)
    out_zip = tmp_path / "eidp-ocr-addon-windows.zip"

    build_ocr_addon_zip(tesseract_dir=tess, tessdata_dir=tessdata, out_zip=out_zip)

    with zipfile.ZipFile(out_zip) as zf:
        names = set(zf.namelist())
        assert "ocr-addon/tesseract/tesseract.exe" in names
        assert "ocr-addon/tessdata/jpn.traineddata" in names
        assert "ocr-addon/MANIFEST.json" in names
        manifest = json.loads(zf.read("ocr-addon/MANIFEST.json").decode("utf-8"))

    assert manifest["layout_version"] == 1
    assert manifest["required"]["tesseract"] == "ocr-addon/tesseract/tesseract.exe"
    assert manifest["required"]["jpn_traineddata"] == "ocr-addon/tessdata/jpn.traineddata"
    manifest_paths = {entry["path"] for entry in manifest["files"]}
    assert "ocr-addon/tesseract/tesseract.exe" in manifest_paths
    assert "ocr-addon/tessdata/jpn.traineddata" in manifest_paths
    assert all(not path.startswith(str(tmp_path)) for path in manifest_paths)


def test_ocr_addon_requires_tesseract_exe(tmp_path: Path) -> None:
    tess, tessdata = _fixture_layout(tmp_path)
    (tess / "tesseract.exe").unlink()

    with pytest.raises(OcrAddonError, match="tesseract.exe"):
        collect_ocr_addon_members(tesseract_dir=tess, tessdata_dir=tessdata)


def test_ocr_addon_requires_jpn_traineddata(tmp_path: Path) -> None:
    tess, tessdata = _fixture_layout(tmp_path)
    (tessdata / "jpn.traineddata").unlink()

    with pytest.raises(OcrAddonError, match="jpn.traineddata"):
        collect_ocr_addon_members(tesseract_dir=tess, tessdata_dir=tessdata)
