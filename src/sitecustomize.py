"""Startup hook for the Windows ZIP launcher environment."""

from __future__ import annotations

from eidp.windows_platform import disable_wmi_platform_queries

disable_wmi_platform_queries()
