"""Sprint 8.6.c — runtime detection + OCR auto-enable thresholds."""

from __future__ import annotations

import pytest

from eidp.ocr.runtime_detect import (
    DEFAULT_MIN_CPUS,
    DEFAULT_MIN_FREE_RAM_MB,
    RuntimeProfile,
    _default_cpu_count_reader,
    _default_free_ram_reader,
    _posix_available_memory_mb,
    detect_runtime,
    ocr_auto_enable,
)


def test_runtime_profile_meets_default_threshold():
    assert RuntimeProfile(cpu_count=4, free_ram_mb=8 * 1024).meets_threshold()


def test_runtime_profile_below_cpu_floor():
    assert not RuntimeProfile(cpu_count=1, free_ram_mb=8 * 1024).meets_threshold()


def test_runtime_profile_below_ram_floor():
    """Plan v6 — 4GB Atom-class PCs must auto-OFF OCR even when CPU is
    plentiful, because OCR throughput is the I/O+RAM bottleneck."""
    assert not RuntimeProfile(cpu_count=8, free_ram_mb=2 * 1024).meets_threshold()


def test_runtime_profile_custom_thresholds():
    profile = RuntimeProfile(cpu_count=4, free_ram_mb=3 * 1024)
    assert profile.meets_threshold(min_cpus=2, min_free_ram_mb=2 * 1024)
    assert not profile.meets_threshold(min_cpus=2, min_free_ram_mb=4 * 1024)


def test_detect_runtime_uses_injected_readers():
    profile = detect_runtime(
        cpu_count_reader=lambda: 6,
        free_ram_reader=lambda: 10 * 1024,
    )
    assert profile == RuntimeProfile(cpu_count=6, free_ram_mb=10 * 1024)


@pytest.mark.parametrize("cpu_count", [None, 0])
def test_default_cpu_count_reader_falls_back_to_single_core(monkeypatch: pytest.MonkeyPatch, cpu_count: int | None):
    import eidp.ocr.runtime_detect as runtime_detect

    monkeypatch.setattr(runtime_detect.os, "cpu_count", lambda: cpu_count)

    assert _default_cpu_count_reader() == 1


def test_default_free_ram_reader_prefers_psutil_probe(monkeypatch: pytest.MonkeyPatch):
    import eidp.ocr.runtime_detect as runtime_detect

    monkeypatch.setattr(runtime_detect, "_psutil_available_memory_mb", lambda: 8 * 1024)
    monkeypatch.setattr(runtime_detect, "_posix_available_memory_mb", lambda: None)

    assert _default_free_ram_reader() == 8 * 1024


def test_default_free_ram_reader_uses_posix_probe(monkeypatch: pytest.MonkeyPatch):
    import eidp.ocr.runtime_detect as runtime_detect

    monkeypatch.setattr(runtime_detect, "_psutil_available_memory_mb", lambda: None)
    monkeypatch.setattr(runtime_detect, "_posix_available_memory_mb", lambda: 2 * 1024)
    assert _default_free_ram_reader() == 2 * 1024


def test_posix_available_memory_returns_none_for_non_positive_values(monkeypatch: pytest.MonkeyPatch):
    import eidp.ocr.runtime_detect as runtime_detect

    monkeypatch.setattr(
        runtime_detect.os,
        "sysconf",
        lambda name: 0 if name == "SC_AVPHYS_PAGES" else 4096,
    )

    assert _posix_available_memory_mb() is None


# ---------------------------------------------------------------------------
# ocr_auto_enable
# ---------------------------------------------------------------------------


def test_auto_enable_passes_with_strong_hardware():
    profile = RuntimeProfile(cpu_count=8, free_ram_mb=16 * 1024)
    assert ocr_auto_enable(profile=profile, env={}) is True


def test_auto_enable_fails_on_weak_hardware():
    profile = RuntimeProfile(cpu_count=1, free_ram_mb=2 * 1024)
    assert ocr_auto_enable(profile=profile, env={}) is False


@pytest.mark.parametrize("forced", ["1", "true", "yes", "on", "TRUE"])
def test_auto_enable_env_force_on_overrides_weak_hardware(forced: str):
    profile = RuntimeProfile(cpu_count=1, free_ram_mb=512)
    assert ocr_auto_enable(profile=profile, env={"EIDP_OCR_AUTO_ENABLE": forced}) is True


@pytest.mark.parametrize("forced", ["0", "false", "no", "off", "OFF"])
def test_auto_enable_env_force_off_overrides_strong_hardware(forced: str):
    profile = RuntimeProfile(cpu_count=16, free_ram_mb=64 * 1024)
    assert ocr_auto_enable(profile=profile, env={"EIDP_OCR_AUTO_ENABLE": forced}) is False


def test_auto_enable_unknown_env_falls_through_to_hardware():
    profile = RuntimeProfile(cpu_count=8, free_ram_mb=16 * 1024)
    assert ocr_auto_enable(
        profile=profile, env={"EIDP_OCR_AUTO_ENABLE": "maybe"},
    ) is True


def test_auto_enable_overrideable_thresholds_via_env():
    """Operator on a marginal PC (1 core, 3 GB free) can still
    opt-in by lowering the floor — useful for "just try it for one
    PDF" tuning before committing to the add-on."""
    profile = RuntimeProfile(cpu_count=1, free_ram_mb=3 * 1024)
    assert ocr_auto_enable(profile=profile, env={
        "EIDP_OCR_MIN_CPUS": "1",
        "EIDP_OCR_MIN_FREE_RAM_MB": "2048",
    }) is True


def test_auto_enable_garbage_threshold_falls_back_to_default():
    profile = RuntimeProfile(cpu_count=1, free_ram_mb=512)
    # Bad env values must NOT promote a weak PC. Fall back to the
    # default (2 cpus / 4 GB) which still rejects this profile.
    assert ocr_auto_enable(profile=profile, env={
        "EIDP_OCR_MIN_CPUS": "abc",
        "EIDP_OCR_MIN_FREE_RAM_MB": "",
    }) is False


def test_module_constants_match_plan_v6():
    """Lock the documented thresholds — a future bumper changing these
    needs to update the runbook and the operator-facing UI copy."""
    assert DEFAULT_MIN_CPUS == 2
    assert DEFAULT_MIN_FREE_RAM_MB == 4 * 1024
