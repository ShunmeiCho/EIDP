"""Run pip for the Windows offline installer without WMI lookups.

pip 26 imports vendored ``truststore`` even for ``--no-index`` installs.
On the operator Windows host used for Sprint 8 validation, that import
called ``platform._wmi_query`` and hung before pip reached wheel
resolution. The installer does not need WMI; make ``platform`` use its
stdlib fallback path before importing pip.
"""

from __future__ import annotations

import os
import platform
import sys


def _disable_platform_wmi() -> None:
    if not hasattr(platform, "_wmi_query"):
        return

    def _raise_oserror(*_args: object, **_kwargs: object) -> None:
        raise OSError("WMI disabled for EIDP offline pip install")

    platform._wmi_query = _raise_oserror


def main(argv: list[str] | None = None) -> int:
    os.environ.setdefault("PIP_DISABLE_PIP_VERSION_CHECK", "1")
    os.environ.setdefault("PIP_NO_INPUT", "1")
    os.environ.setdefault("PIP_NO_CACHE_DIR", "1")
    _disable_platform_wmi()

    from pip._internal.cli.main import main as pip_main

    return int(pip_main(sys.argv[1:] if argv is None else argv))


if __name__ == "__main__":
    raise SystemExit(main())
