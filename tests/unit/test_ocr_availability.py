"""Sprint 8.6.d.3 — OCR availability detection."""

from __future__ import annotations

from pathlib import Path

import pytest

from eidp.ocr.availability import (
    OcrAvailability,
    availability_banner_severity,
    availability_banner_text,
    detect_ocr_availability,
)
from eidp.ocr.runtime_detect import RuntimeProfile

# ---------------------------------------------------------------------------
# Fixture: build a fake project-local Linux runtime
# ---------------------------------------------------------------------------


def _make_runtime(tmp_path: Path, *, binary: bool, jpn: bool) -> Path:
    """Build an optional OCR runtime under ``tmp_path`` and return the app root."""
    runtime = tmp_path / "ocr"
    if binary:
        bin_dir = runtime / "tesseract" / "bin"
        bin_dir.mkdir(parents=True)
        (bin_dir / "tesseract").write_bytes(b"ELF")
    if jpn:
        td = runtime / "tessdata"
        td.mkdir(parents=True)
        (td / "jpn.traineddata").write_bytes(b"x")
    return tmp_path


# ---------------------------------------------------------------------------
# detect_ocr_availability
# ---------------------------------------------------------------------------


def test_detect_full_setup(tmp_path: Path):
    """Binary + jpn data + strong hardware → fully ready."""
    app_root = _make_runtime(tmp_path, binary=True, jpn=True)
    profile = RuntimeProfile(cpu_count=8, free_ram_mb=16 * 1024)
    detection = detect_ocr_availability(
        app_root=app_root, env={}, profile=profile,
    )
    assert detection.binary_path is not None
    assert detection.binary_path.name == "tesseract"
    assert detection.tessdata_dir is not None
    assert detection.has_jpn_traineddata is True
    assert detection.auto_enabled is True
    assert detection.can_run is True
    assert detection.auto_can_run is True


def test_detect_no_binary(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """No project runtime and no system tesseract means can_run is false."""
    monkeypatch.setattr("eidp.ocr.tesseract.shutil.which", lambda _name: None)
    detection = detect_ocr_availability(
        app_root=tmp_path, env={},
        profile=RuntimeProfile(cpu_count=8, free_ram_mb=16 * 1024),
    )
    assert detection.binary_path is None
    assert detection.can_run is False
    assert detection.auto_can_run is False


def test_detect_binary_but_no_jpn(tmp_path: Path):
    """Tesseract installed, jpn missing → can_run False with a warning
    severity. The server runtime needs its language data restored."""
    app_root = _make_runtime(tmp_path, binary=True, jpn=False)
    detection = detect_ocr_availability(
        app_root=app_root, env={},
        profile=RuntimeProfile(cpu_count=8, free_ram_mb=16 * 1024),
    )
    assert detection.binary_path is not None
    assert detection.has_jpn_traineddata is False
    assert detection.can_run is False


def test_detect_full_install_but_low_spec_pc(tmp_path: Path):
    """OCR runtime installed but hardware below threshold means can_run True
    (a reviewer can manually trigger), auto_can_run False (weekly run
    won't auto-OCR)."""
    app_root = _make_runtime(tmp_path, binary=True, jpn=True)
    detection = detect_ocr_availability(
        app_root=app_root, env={},
        profile=RuntimeProfile(cpu_count=1, free_ram_mb=2 * 1024),
    )
    assert detection.can_run is True
    assert detection.auto_enabled is False
    assert detection.auto_can_run is False


def test_detect_env_force_off_overrides_strong_hardware(tmp_path: Path):
    app_root = _make_runtime(tmp_path, binary=True, jpn=True)
    detection = detect_ocr_availability(
        app_root=app_root,
        env={"EIDP_OCR_AUTO_ENABLE": "off"},
        profile=RuntimeProfile(cpu_count=16, free_ram_mb=64 * 1024),
    )
    assert detection.auto_enabled is False
    assert detection.auto_can_run is False
    # Manual OCR still possible.
    assert detection.can_run is True


def test_tessdata_dir_without_jpn_marks_has_jpn_false(tmp_path: Path):
    """``locate_tessdata`` may return a directory that's missing
    jpn.traineddata. Owner P2 from 8.6.c review — handle that case
    explicitly in availability."""
    app_root = _make_runtime(tmp_path, binary=True, jpn=False)
    # Manually create the tessdata dir without jpn.traineddata.
    (app_root / "ocr" / "tessdata").mkdir(parents=True)
    detection = detect_ocr_availability(
        app_root=app_root, env={},
        profile=RuntimeProfile(cpu_count=8, free_ram_mb=16 * 1024),
    )
    assert detection.tessdata_dir is not None
    assert detection.has_jpn_traineddata is False
    assert detection.can_run is False


# ---------------------------------------------------------------------------
# Banner text + severity
# ---------------------------------------------------------------------------


def test_banner_for_no_binary():
    detection = OcrAvailability(
        binary_path=None, tessdata_dir=None,
        has_jpn_traineddata=False, auto_enabled=False,
    )
    assert "未インストール" in availability_banner_text(detection)
    assert availability_banner_severity(detection) == "info"


def test_banner_for_missing_jpn():
    detection = OcrAvailability(
        binary_path=Path("/x/tesseract"),
        tessdata_dir=Path("/x/tessdata"),
        has_jpn_traineddata=False,
        auto_enabled=False,
    )
    assert "jpn.traineddata" in availability_banner_text(detection)
    assert availability_banner_severity(detection) == "warning"


def test_banner_for_auto_off_low_hardware():
    detection = OcrAvailability(
        binary_path=Path("/x/tesseract"),
        tessdata_dir=Path("/x/tessdata"),
        has_jpn_traineddata=True,
        auto_enabled=False,
    )
    text = availability_banner_text(detection)
    assert "自動実行は OFF" in text
    assert "手動" in text
    assert availability_banner_severity(detection) == "info"


def test_banner_for_full_ready():
    detection = OcrAvailability(
        binary_path=Path("/x/tesseract"),
        tessdata_dir=Path("/x/tessdata"),
        has_jpn_traineddata=True,
        auto_enabled=True,
    )
    assert "自動実行 ON" in availability_banner_text(detection)
    assert availability_banner_severity(detection) == "success"


def test_locate_tessdata_export_still_present():
    from eidp import ocr

    assert "detect_ocr_availability" in ocr.__all__
    assert "OcrAvailability" in ocr.__all__
    assert "availability_banner_text" in ocr.__all__
