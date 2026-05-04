"""Sprint 8.6.c — runtime detection for OCR auto-enable.

Plan v6 chose a hardware-aware default: OCR auto-enables only when the
operator PC has at least 2 logical CPU cores AND at least 4 GB free
RAM. Below that threshold OCR is forced OFF (UI may still let the
operator manually trigger OCR on a single PDF, but the auto path stays
quiet so a 4GB Atom-class PC doesn't grind for an hour during weekly
ingestion).

The whole module is pure data + a couple of stdlib calls, written so
tests can inject fake CPU / memory readings without depending on
``psutil``.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass

#: Defaults from Sprint 8 v6 plan. ``EIDP_OCR_MIN_CPUS`` /
#: ``EIDP_OCR_MIN_FREE_RAM_MB`` env vars override per operator PC.
DEFAULT_MIN_CPUS = 2
DEFAULT_MIN_FREE_RAM_MB = 4 * 1024  # 4 GB


@dataclass(frozen=True)
class RuntimeProfile:
    """Snapshot of the runtime resources OCR cares about."""

    cpu_count: int
    free_ram_mb: int

    def meets_threshold(self, *, min_cpus: int = DEFAULT_MIN_CPUS,
                        min_free_ram_mb: int = DEFAULT_MIN_FREE_RAM_MB) -> bool:
        return self.cpu_count >= min_cpus and self.free_ram_mb >= min_free_ram_mb


def _default_cpu_count_reader() -> int:
    """``os.cpu_count`` returns ``None`` on some platforms; treat that
    as the conservative single-core case."""
    n = os.cpu_count()
    return n if n and n > 0 else 1


def _default_free_ram_reader() -> int:
    """Best-effort free-memory probe in MB.

    Tries ``psutil.virtual_memory().available`` first because that is
    what the operator install actually has. Falls back to
    ``os.sysconf("SC_AVPHYS_PAGES")`` on POSIX. Worst case (Windows
    without psutil) returns 0 so ``meets_threshold`` will fail closed.
    """
    try:
        import psutil  # type: ignore[import-not-found]

        return int(psutil.virtual_memory().available // (1024 * 1024))
    except Exception:
        pass

    try:
        page_size = os.sysconf("SC_PAGESIZE")
        avail_pages = os.sysconf("SC_AVPHYS_PAGES")
        if page_size > 0 and avail_pages > 0:
            return int((page_size * avail_pages) // (1024 * 1024))
    except (AttributeError, ValueError, OSError):
        pass

    return 0


def detect_runtime(
    *,
    cpu_count_reader: Callable[[], int] | None = None,
    free_ram_reader: Callable[[], int] | None = None,
) -> RuntimeProfile:
    """Build a ``RuntimeProfile`` from injectable readers.

    Production callers omit both readers and we fall back to the
    stdlib + best-effort psutil. Tests pass tiny lambdas to lock in
    a deterministic profile."""
    cpu_reader = cpu_count_reader or _default_cpu_count_reader
    ram_reader = free_ram_reader or _default_free_ram_reader
    return RuntimeProfile(
        cpu_count=int(cpu_reader()),
        free_ram_mb=int(ram_reader()),
    )


def ocr_auto_enable(
    *,
    profile: RuntimeProfile | None = None,
    env: dict[str, str] | None = None,
) -> bool:
    """Top-level decision the ingest pipeline calls.

    * ``EIDP_OCR_AUTO_ENABLE=1`` → on, regardless of hardware. Operator
      override for "I know what I'm doing".
    * ``EIDP_OCR_AUTO_ENABLE=0`` → off, regardless of hardware.
    * Otherwise consult the runtime profile against the (overridable)
      thresholds.

    Returns False rather than raising when the env var is mis-typed —
    OCR is opt-in by design and a typo should never escalate.
    """
    env_map = env if env is not None else os.environ

    forced = env_map.get("EIDP_OCR_AUTO_ENABLE")
    if forced is not None:
        normalized = forced.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
        # Unknown value — fall through to hardware check.

    snapshot = profile if profile is not None else detect_runtime()
    min_cpus = _int_or_default(env_map.get("EIDP_OCR_MIN_CPUS"), DEFAULT_MIN_CPUS)
    min_ram = _int_or_default(env_map.get("EIDP_OCR_MIN_FREE_RAM_MB"), DEFAULT_MIN_FREE_RAM_MB)
    return snapshot.meets_threshold(min_cpus=min_cpus, min_free_ram_mb=min_ram)


def _int_or_default(value: str | None, default: int) -> int:
    if value is None or value.strip() == "":
        return default
    try:
        return int(value)
    except ValueError:
        return default
