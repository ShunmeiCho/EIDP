from __future__ import annotations

import importlib


def test_package_import_installs_windows_platform_guard() -> None:
    import eidp

    reloaded = importlib.reload(eidp)

    assert hasattr(reloaded, "disable_wmi_platform_queries")
