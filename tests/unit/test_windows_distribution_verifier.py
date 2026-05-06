"""Sprint 8 release-gate verifier for final Windows ZIP artifacts."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import zipfile
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"
SCRIPT_PATH = SCRIPTS_DIR / "verify_windows_distribution.py"
spec = importlib.util.spec_from_file_location("verify_windows_distribution", SCRIPT_PATH)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def _write_zip(path: Path, entries: dict[str, bytes | str]) -> Path:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, body in entries.items():
            data = body.encode("utf-8") if isinstance(body, str) else body
            zf.writestr(name, data)
    return path


def _core_entries() -> dict[str, bytes | str]:
    return {
        "README.md": "# EIDP\n",
        "requirements-windows.txt": "structlog\n",
        "pyproject.toml": "[project]\nname='eidp'\n",
        "alembic.ini": "[alembic]\n",
        "docs/runbooks/eidp-windows.md": "# runbook\n",
        "scripts/first_setup.bat": (SCRIPTS_DIR / "first_setup.bat").read_text(encoding="utf-8"),
        "scripts/launch.bat": (SCRIPTS_DIR / "launch.bat").read_text(encoding="utf-8"),
        "scripts/weekly_run.bat": (SCRIPTS_DIR / "weekly_run.bat").read_text(encoding="utf-8"),
        "scripts/uninstall.bat": (SCRIPTS_DIR / "uninstall.bat").read_text(encoding="utf-8"),
        "scripts/validate_install.bat": (SCRIPTS_DIR / "validate_install.bat").read_text(encoding="utf-8"),
        "scripts/run_weekly_target_year_discovery.py": (
            SCRIPTS_DIR / "run_weekly_target_year_discovery.py"
        ).read_text(encoding="utf-8"),
        "scripts/run_r8_rediscovery_weekly.py": (
            SCRIPTS_DIR / "run_r8_rediscovery_weekly.py"
        ).read_text(encoding="utf-8"),
        "scripts/validate_windows_install.py": (SCRIPTS_DIR / "validate_windows_install.py").read_text(
            encoding="utf-8"
        ),
        "runtime/python/python.exe": b"PE",
        "runtime/uv.exe": b"PE",
        "src/eidp/__init__.py": "",
        "migrations/env.py": "",
        "wheelhouse/eidp-0.2.0-py3-none-any.whl": b"wheel",
        "wheelhouse/structlog-25.5.0-py3-none-any.whl": b"wheel",
    }


def test_verify_core_zip_accepts_complete_distribution(tmp_path: Path) -> None:
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", _core_entries())

    check = module.verify_core_zip(zip_path)

    assert check.ok, check.errors
    assert check.details["has_runtime"] is True
    assert check.details["wheel_count"] == 2
    assert check.details["size_bytes"] == zip_path.stat().st_size
    assert check.details["sha256"] == hashlib.sha256(zip_path.read_bytes()).hexdigest()


def test_verify_core_zip_requires_runtime(tmp_path: Path) -> None:
    entries = _core_entries()
    entries.pop("runtime/python/python.exe")
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("runtime/python/python.exe" in error for error in check.errors)


def test_verify_core_zip_rejects_macos_wheel(tmp_path: Path) -> None:
    entries = _core_entries()
    entries["wheelhouse/pymupdf-1.25.0-cp312-cp312-macosx_11_0_arm64.whl"] = b"wheel"
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("rejected wheel" in error for error in check.errors)


def test_verify_core_zip_requires_project_wheel(tmp_path: Path) -> None:
    entries = _core_entries()
    entries.pop("wheelhouse/eidp-0.2.0-py3-none-any.whl")
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("project wheel" in error for error in check.errors)


def test_verify_core_zip_rejects_case_insensitive_path_collision(tmp_path: Path) -> None:
    entries = _core_entries()
    entries["docs/Runbooks/eidp-windows.md"] = "# duplicate by case\n"
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("case-insensitive path collisions" in error for error in check.errors)


def test_verify_core_zip_rejects_windows_reserved_component(tmp_path: Path) -> None:
    entries = _core_entries()
    entries["docs/runbooks/CON.txt"] = "bad"
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("reserved path components" in error for error in check.errors)


def test_verify_core_zip_rejects_parent_directory_entry(tmp_path: Path) -> None:
    entries = _core_entries()
    entries["../escape.txt"] = "bad"
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("parent-directory" in error for error in check.errors)


def test_verify_core_zip_rejects_duplicate_entries(tmp_path: Path) -> None:
    zip_path = tmp_path / "eidp-windows.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, body in _core_entries().items():
            data = body.encode("utf-8") if isinstance(body, str) else body
            zf.writestr(name, data)
        with pytest.warns(UserWarning, match="Duplicate name"):
            zf.writestr("README.md", "# duplicate\n")

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("duplicate entries" in error for error in check.errors)


def test_verify_core_zip_rejects_stale_launch_bat_contract(tmp_path: Path) -> None:
    entries = _core_entries()
    entries["scripts/launch.bat"] = entries["scripts/launch.bat"].replace(
        'set "RC=%ERRORLEVEL%"',
        "REM stale launcher missing rc capture",
    )
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("scripts/launch.bat missing required token" in error for error in check.errors)


def test_verify_core_zip_rejects_locale_dependent_weekly_bat(tmp_path: Path) -> None:
    entries = _core_entries()
    entries["scripts/weekly_run.bat"] = entries["scripts/weekly_run.bat"] + "\nset DATESTAMP=%DATE:~0,8%\n"
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("%date:~" in error for error in check.errors)


def test_verify_core_zip_rejects_uninstall_that_deletes_data(tmp_path: Path) -> None:
    entries = _core_entries()
    entries["scripts/uninstall.bat"] = entries["scripts/uninstall.bat"] + "\nrmdir /s /q data\n"
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("scripts/uninstall.bat contains forbidden token: rmdir" in error for error in check.errors)


def test_verify_core_zip_rejects_stale_validator_missing_playwright_flag(tmp_path: Path) -> None:
    entries = _core_entries()
    entries["scripts/validate_windows_install.py"] = entries["scripts/validate_windows_install.py"].replace(
        "--require-playwright-addon",
        "--missing-playwright-addon",
    )
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("--require-playwright-addon" in error for error in check.errors)


def test_verify_core_zip_rejects_weekly_runner_export_excel(tmp_path: Path) -> None:
    entries = _core_entries()
    entries["scripts/run_weekly_target_year_discovery.py"] = (
        entries["scripts/run_weekly_target_year_discovery.py"] + "\nexport_excel()\n"
    )
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    check = module.verify_core_zip(zip_path)

    assert not check.ok
    assert any("export_excel" in error for error in check.errors)


def test_verify_ocr_addon_accepts_manifest(tmp_path: Path) -> None:
    tesseract = b"PE"
    tessdata = b"jpn"
    manifest = {
        "layout_version": 1,
        "files": [
            {
                "path": "ocr-addon/tesseract/tesseract.exe",
                "size": len(tesseract),
                "sha256": hashlib.sha256(tesseract).hexdigest(),
            },
            {
                "path": "ocr-addon/tessdata/jpn.traineddata",
                "size": len(tessdata),
                "sha256": hashlib.sha256(tessdata).hexdigest(),
            },
        ],
    }
    zip_path = _write_zip(
        tmp_path / "eidp-ocr-addon-windows.zip",
        {
            "ocr-addon/tesseract/tesseract.exe": tesseract,
            "ocr-addon/tessdata/jpn.traineddata": tessdata,
            "ocr-addon/MANIFEST.json": json.dumps(manifest),
        },
    )

    check = module.verify_ocr_addon_zip(zip_path)

    assert check.ok, check.errors
    assert check.details["manifest_files"] == 2


def test_verify_ocr_addon_requires_manifest_paths(tmp_path: Path) -> None:
    zip_path = _write_zip(
        tmp_path / "eidp-ocr-addon-windows.zip",
        {
            "ocr-addon/tesseract/tesseract.exe": b"PE",
            "ocr-addon/tessdata/jpn.traineddata": b"jpn",
            "ocr-addon/MANIFEST.json": json.dumps({"layout_version": 1, "files": []}),
        },
    )

    check = module.verify_ocr_addon_zip(zip_path)

    assert not check.ok
    assert any("manifest missing required file path" in error for error in check.errors)


def test_verify_ocr_addon_rejects_manifest_checksum_mismatch(tmp_path: Path) -> None:
    manifest = {
        "layout_version": 1,
        "files": [
            {
                "path": "ocr-addon/tesseract/tesseract.exe",
                "size": 2,
                "sha256": hashlib.sha256(b"wrong").hexdigest(),
            },
            {
                "path": "ocr-addon/tessdata/jpn.traineddata",
                "size": 3,
                "sha256": hashlib.sha256(b"jpn").hexdigest(),
            },
        ],
    }
    zip_path = _write_zip(
        tmp_path / "eidp-ocr-addon-windows.zip",
        {
            "ocr-addon/tesseract/tesseract.exe": b"PE",
            "ocr-addon/tessdata/jpn.traineddata": b"jpn",
            "ocr-addon/MANIFEST.json": json.dumps(manifest),
        },
    )

    check = module.verify_ocr_addon_zip(zip_path)

    assert not check.ok
    assert any("manifest sha256 mismatch" in error for error in check.errors)


def test_verify_ocr_addon_rejects_unlisted_payload_entry(tmp_path: Path) -> None:
    manifest = {
        "layout_version": 1,
        "files": [
            {
                "path": "ocr-addon/tesseract/tesseract.exe",
                "size": 2,
                "sha256": hashlib.sha256(b"PE").hexdigest(),
            },
            {
                "path": "ocr-addon/tessdata/jpn.traineddata",
                "size": 3,
                "sha256": hashlib.sha256(b"jpn").hexdigest(),
            },
        ],
    }
    zip_path = _write_zip(
        tmp_path / "eidp-ocr-addon-windows.zip",
        {
            "ocr-addon/tesseract/tesseract.exe": b"PE",
            "ocr-addon/tesseract/extra.dll": b"dll",
            "ocr-addon/tessdata/jpn.traineddata": b"jpn",
            "ocr-addon/MANIFEST.json": json.dumps(manifest),
        },
    )

    check = module.verify_ocr_addon_zip(zip_path)

    assert not check.ok
    assert any("manifest missing ZIP payload entries" in error for error in check.errors)


def test_verify_ocr_addon_rejects_duplicate_manifest_path(tmp_path: Path) -> None:
    entry = {
        "path": "ocr-addon/tesseract/tesseract.exe",
        "size": 2,
        "sha256": hashlib.sha256(b"PE").hexdigest(),
    }
    manifest = {
        "layout_version": 1,
        "files": [
            entry,
            entry,
            {
                "path": "ocr-addon/tessdata/jpn.traineddata",
                "size": 3,
                "sha256": hashlib.sha256(b"jpn").hexdigest(),
            },
        ],
    }
    zip_path = _write_zip(
        tmp_path / "eidp-ocr-addon-windows.zip",
        {
            "ocr-addon/tesseract/tesseract.exe": b"PE",
            "ocr-addon/tessdata/jpn.traineddata": b"jpn",
            "ocr-addon/MANIFEST.json": json.dumps(manifest),
        },
    )

    check = module.verify_ocr_addon_zip(zip_path)

    assert not check.ok
    assert any("duplicate file path" in error for error in check.errors)


def test_verify_playwright_addon_accepts_chromium_and_wheel(tmp_path: Path) -> None:
    wheel = b"wheel"
    chrome = b"PE"
    manifest = {
        "layout_version": 1,
        "files": [
            {
                "path": "playwright-addon/wheelhouse/playwright-1.58.0-py3-none-win_amd64.whl",
                "size": len(wheel),
                "sha256": hashlib.sha256(wheel).hexdigest(),
            },
            {
                "path": "playwright-addon/ms-playwright/chromium-1234/chrome-win/chrome.exe",
                "size": len(chrome),
                "sha256": hashlib.sha256(chrome).hexdigest(),
            },
        ],
    }
    zip_path = _write_zip(
        tmp_path / "eidp-playwright-addon-windows.zip",
        {
            "playwright-addon/wheelhouse/playwright-1.58.0-py3-none-win_amd64.whl": wheel,
            "playwright-addon/ms-playwright/chromium-1234/chrome-win/chrome.exe": chrome,
            "playwright-addon/MANIFEST.json": json.dumps(manifest),
        },
    )

    check = module.verify_playwright_addon_zip(zip_path)

    assert check.ok, check.errors
    assert check.details["manifest_files"] == 2


def test_verify_playwright_addon_requires_chrome_exe(tmp_path: Path) -> None:
    zip_path = _write_zip(
        tmp_path / "eidp-playwright-addon-windows.zip",
        {
            "playwright-addon/wheelhouse/playwright-1.58.0-py3-none-win_amd64.whl": b"wheel",
            "playwright-addon/ms-playwright/chromium-1234/chrome-win/chrome.dll": b"dll",
            "playwright-addon/MANIFEST.json": json.dumps({"layout_version": 1, "files": []}),
        },
    )

    check = module.verify_playwright_addon_zip(zip_path)

    assert not check.ok
    assert any("chrome.exe" in error for error in check.errors)


def test_cli_returns_nonzero_for_failed_distribution(tmp_path: Path, capsys) -> None:  # noqa: ANN001
    entries = _core_entries()
    entries.pop("runtime/uv.exe")
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", entries)

    rc = module.main([str(zip_path)])

    assert rc == 1
    output = capsys.readouterr().out
    assert "FAIL core" in output
    assert "runtime/uv.exe" in output


def test_cli_json_includes_distribution_checksum(tmp_path: Path, capsys) -> None:  # noqa: ANN001
    zip_path = _write_zip(tmp_path / "eidp-windows.zip", _core_entries())

    rc = module.main([str(zip_path), "--json"])

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload[0]["ok"] is True
    assert payload[0]["details"]["sha256"] == hashlib.sha256(zip_path.read_bytes()).hexdigest()
    assert payload[0]["details"]["size_bytes"] == zip_path.stat().st_size
