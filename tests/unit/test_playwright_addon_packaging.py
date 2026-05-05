"""Sprint 8.7.d — optional Playwright/Chromium add-on ZIP layout.

The Windows core ZIP is HTTP-first. Playwright and Chromium stay outside the
core package and can be distributed later as a separate add-on. These tests pin
the add-on shape without downloading Chromium on macOS.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import zipfile
from pathlib import Path

import pytest

SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "build_playwright_addon_zip.py"
spec = importlib.util.spec_from_file_location("build_playwright_addon_zip", SCRIPT_PATH)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)

PlaywrightAddonError = module.PlaywrightAddonError
build_playwright_addon_zip = module.build_playwright_addon_zip
collect_playwright_addon_members = module.collect_playwright_addon_members


def _fixture_layout(tmp_path: Path) -> tuple[Path, Path]:
    wheelhouse = tmp_path / "wheelhouse-src"
    wheelhouse.mkdir()
    (wheelhouse / "playwright-1.58.0-py3-none-win_amd64.whl").write_bytes(b"wheel")
    (wheelhouse / "greenlet-3.2.0-cp312-cp312-win_amd64.whl").write_bytes(b"greenlet")
    (wheelhouse / "notes.txt").write_text("ignored", encoding="utf-8")

    browsers = tmp_path / "ms-playwright-src"
    chrome_dir = browsers / "chromium-1234" / "chrome-win"
    chrome_dir.mkdir(parents=True)
    (chrome_dir / "chrome.exe").write_bytes(b"PE")
    (chrome_dir / "chrome.dll").write_bytes(b"DLL")
    (browsers / "__pycache__").mkdir()
    (browsers / "__pycache__" / "junk.pyc").write_bytes(b"x")
    return wheelhouse, browsers


def test_collect_playwright_addon_members_matches_expected_layout(tmp_path: Path) -> None:
    wheelhouse, browsers = _fixture_layout(tmp_path)

    members = collect_playwright_addon_members(wheelhouse=wheelhouse, browsers_dir=browsers)
    arcs = {arc for _, arc in members}

    assert "playwright-addon/wheelhouse/playwright-1.58.0-py3-none-win_amd64.whl" in arcs
    assert "playwright-addon/wheelhouse/greenlet-3.2.0-cp312-cp312-win_amd64.whl" in arcs
    assert "playwright-addon/ms-playwright/chromium-1234/chrome-win/chrome.exe" in arcs
    assert "playwright-addon/ms-playwright/chromium-1234/chrome-win/chrome.dll" in arcs
    assert "playwright-addon/wheelhouse/notes.txt" not in arcs
    assert all("__pycache__" not in arc for arc in arcs)


def test_build_playwright_addon_zip_writes_manifest(tmp_path: Path) -> None:
    wheelhouse, browsers = _fixture_layout(tmp_path)
    out_zip = tmp_path / "eidp-playwright-addon-windows.zip"

    build_playwright_addon_zip(wheelhouse=wheelhouse, browsers_dir=browsers, out_zip=out_zip)

    with zipfile.ZipFile(out_zip) as zf:
        names = set(zf.namelist())
        assert "playwright-addon/MANIFEST.json" in names
        assert "playwright-addon/ms-playwright/chromium-1234/chrome-win/chrome.exe" in names
        manifest = json.loads(zf.read("playwright-addon/MANIFEST.json").decode("utf-8"))

    assert manifest["layout_version"] == 1
    assert manifest["required"]["browsers"] == "playwright-addon/ms-playwright"
    assert manifest["required"]["wheelhouse"] == "playwright-addon/wheelhouse"
    manifest_paths = {entry["path"] for entry in manifest["files"]}
    assert "playwright-addon/ms-playwright/chromium-1234/chrome-win/chrome.exe" in manifest_paths
    assert all(not path.startswith(str(tmp_path)) for path in manifest_paths)


def test_playwright_addon_requires_wheel(tmp_path: Path) -> None:
    wheelhouse, browsers = _fixture_layout(tmp_path)
    for wheel in wheelhouse.glob("*.whl"):
        wheel.unlink()

    with pytest.raises(PlaywrightAddonError, match="playwright wheel"):
        collect_playwright_addon_members(wheelhouse=wheelhouse, browsers_dir=browsers)


def test_playwright_addon_requires_chromium_executable(tmp_path: Path) -> None:
    wheelhouse, browsers = _fixture_layout(tmp_path)
    (browsers / "chromium-1234" / "chrome-win" / "chrome.exe").unlink()

    with pytest.raises(PlaywrightAddonError, match="chrome.exe"):
        collect_playwright_addon_members(wheelhouse=wheelhouse, browsers_dir=browsers)
