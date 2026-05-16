from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "rotate_audit_outbox.py"
spec = importlib.util.spec_from_file_location("rotate_audit_outbox", SCRIPT_PATH)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def test_plan_rotation_is_dry_when_below_threshold(tmp_path: Path) -> None:
    outbox = tmp_path / "data" / "audit" / "manual-actions.jsonl"
    outbox.parent.mkdir(parents=True)
    outbox.write_text("{}\n", encoding="utf-8")

    plan = module.plan_rotation(app_root=tmp_path, max_bytes=100)

    assert plan.rotate is False
    assert plan.reason == "below max_bytes 100"


def test_apply_rotation_moves_active_outbox_to_matching_archive(tmp_path: Path) -> None:
    outbox = tmp_path / "data" / "audit" / "manual-actions.jsonl"
    outbox.parent.mkdir(parents=True)
    outbox.write_text('{"action_id":"a"}\n', encoding="utf-8")

    plan = module.plan_rotation(app_root=tmp_path, max_bytes=1, stamp="20260516-010203")
    action = module.apply_rotation(tmp_path, plan)

    archive = tmp_path / "data" / "audit" / "manual-actions-20260516-010203.jsonl"
    assert action["rotated"] is True
    assert action["error"] is None
    assert archive.read_text(encoding="utf-8") == '{"action_id":"a"}\n'
    assert outbox.read_text(encoding="utf-8") == ""


def test_plan_rotation_refuses_symlink_outbox(tmp_path: Path) -> None:
    outside = tmp_path / "outside.jsonl"
    outside.write_text("{}\n", encoding="utf-8")
    outbox = tmp_path / "data" / "audit" / "manual-actions.jsonl"
    outbox.parent.mkdir(parents=True)
    outbox.symlink_to(outside)

    plan = module.plan_rotation(app_root=tmp_path, max_bytes=1)

    assert plan.rotate is False
    assert plan.reason == "refusing symlink"


def test_plan_rotation_refuses_non_audit_path(tmp_path: Path) -> None:
    outbox = tmp_path / "manual-actions.jsonl"
    outbox.write_text("{}\n", encoding="utf-8")

    plan = module.plan_rotation(app_root=tmp_path, jsonl_path=outbox, max_bytes=1)

    assert plan.rotate is False
    assert plan.reason == "refusing path outside data/audit"
