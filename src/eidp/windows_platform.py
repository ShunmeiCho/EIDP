"""Windows platform compatibility hooks for EIDP entrypoints."""

from __future__ import annotations

import platform
from typing import NoReturn


def disable_wmi_platform_queries() -> None:
    """Avoid Windows WMI calls from stdlib ``platform`` during startup.

    On the Sprint 8 validation host, ``platform._wmi_query`` can hang. Some
    dependencies call ``platform.machine()`` during import, so fail the WMI
    branch fast and let ``platform`` use its registry/sys fallback path.
    """

    wmi_query = getattr(platform, "_wmi_query", None)
    if wmi_query is None or getattr(wmi_query, "_eidp_wmi_disabled", False):
        return

    def _raise_oserror(*_args: object, **_kwargs: object) -> NoReturn:
        raise OSError("WMI disabled for EIDP Windows platform detection")

    setattr(_raise_oserror, "_eidp_wmi_disabled", True)
    setattr(platform, "_wmi_query", _raise_oserror)
