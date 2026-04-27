"""Tests for prefecture aggregator writer-plan application safety gates."""

from __future__ import annotations

import json
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


def _load_apply_writer_plan():
    path = Path(__file__).resolve().parents[2] / "scripts" / "apply_writer_plan.py"
    spec = spec_from_file_location("apply_writer_plan", path)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


apply_writer_plan = _load_apply_writer_plan()


def test_load_verified_entries_uses_row_identity_for_shared_urls(monkeypatch, tmp_path) -> None:
    plan_dir = tmp_path / "pref-aggregator"
    plan_dir.mkdir()
    shared_url = "https://www.ndanma.ac.jp/information/disclose/"
    detail = {
        "results": [
            {
                "pref": "aichi",
                "school_id": 1390,
                "url": shared_url,
                "ownership_ok": False,
            },
            {
                "pref": "aichi",
                "school_id": 1391,
                "url": shared_url,
                "ownership_ok": True,
            },
            {
                "pref": "tokyo",
                "school_id": "10",
                "url": "https://tokyo.example/disclosure/",
                "ownership_ok": True,
            },
            {
                "pref": "aichi",
                "school_id": "not-an-int",
                "url": "https://invalid.example/disclosure/",
                "ownership_ok": True,
            },
            {
                "pref": "aichi",
                "school_id": 1392,
                "ownership_ok": True,
            },
        ]
    }
    (plan_dir / "url-verification-20260427_000000.json").write_text(
        json.dumps(detail),
        encoding="utf-8",
    )
    monkeypatch.setattr(apply_writer_plan, "PLAN_DIR", plan_dir)

    entries = apply_writer_plan.load_verified_entries()

    assert entries == {
        ("aichi", 1391, shared_url),
        ("tokyo", 10, "https://tokyo.example/disclosure/"),
    }
    assert ("aichi", 1390, shared_url) not in entries


def test_resolve_verification_file_accepts_plan_dir_basename(monkeypatch, tmp_path) -> None:
    plan_dir = tmp_path / "pref-aggregator"
    plan_dir.mkdir()
    detail_path = plan_dir / "url-verification-20260427_120000.json"
    detail_path.write_text('{"results": []}', encoding="utf-8")
    monkeypatch.setattr(apply_writer_plan, "PLAN_DIR", plan_dir)

    assert apply_writer_plan.resolve_verification_file(Path(detail_path.name)) == detail_path
