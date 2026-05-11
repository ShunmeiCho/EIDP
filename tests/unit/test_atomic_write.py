from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

script = Path(__file__).resolve().parents[2] / "scripts" / "atomic_write.py"
spec = importlib.util.spec_from_file_location("atomic_write", script)
assert spec is not None
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules["atomic_write"] = module
spec.loader.exec_module(module)


def test_write_text_atomic_preserves_existing_file_when_replace_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "queue.json"
    target.write_text("old\n", encoding="utf-8")

    def fail_replace(self: Path, target_path: Path) -> None:
        raise OSError("replace failed")

    monkeypatch.setattr(Path, "replace", fail_replace)

    with pytest.raises(OSError, match="replace failed"):
        module.write_text_atomic(target, "new\n")

    assert target.read_text(encoding="utf-8") == "old\n"
    assert list(tmp_path.glob("*.tmp")) == []


def test_write_text_atomic_creates_parent_and_replaces_target(tmp_path: Path) -> None:
    target = tmp_path / "nested" / "queue.json"

    module.write_text_atomic(target, "new\n")

    assert target.read_text(encoding="utf-8") == "new\n"
