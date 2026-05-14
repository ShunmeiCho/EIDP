from __future__ import annotations

import sys
from types import ModuleType

import pytest


@pytest.fixture(autouse=True)
def restore_main_module_after_test() -> None:
    """Streamlit AppTest installs a fake __main__; keep later spawn tests isolated."""
    original_main: ModuleType | None = sys.modules.get("__main__")
    yield
    if original_main is None:
        sys.modules.pop("__main__", None)
    else:
        sys.modules["__main__"] = original_main
