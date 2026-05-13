from __future__ import annotations

import importlib.util
import json
import sys
import zipfile
from pathlib import Path


def _load_module():
    script = Path(__file__).resolve().parents[2] / "scripts" / "collect_stage6_evidence.py"
    spec = importlib.util.spec_from_file_location("collect_stage6_evidence", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _load_verify_module():
    script = Path(__file__).resolve().parents[2] / "scripts" / "verify_stage6_evidence.py"
    spec = importlib.util.spec_from_file_location("verify_stage6_evidence", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_build_evidence_bundle_includes_stage6_artifacts_without_db_or_pdfs(tmp_path: Path) -> None:
    module = _load_module()
    root = tmp_path / "eidp"
    (root / "logs").mkdir(parents=True)
    (root / "data" / "output" / "target-year-discovery").mkdir(parents=True)
    (root / "data" / "pdfs" / "1").mkdir(parents=True)

    (root / "BUILD_INFO.json").write_text('{"git_commit": "abc"}\n', encoding="utf-8")
    (root / "logs" / "diagnostics-20260514-010000.txt").write_text("diag\n", encoding="utf-8")
    (root / "logs" / "stage6-recovery-20260514-010001.json").write_text('{"ok": true}\n', encoding="utf-8")
    (root / "logs" / "bootstrap-pdfs-20260514-010002.json").write_text('{"ok": true}\n', encoding="utf-8")
    (root / "logs" / "bootstrap-pdfs-20260514-010003.log").write_text("tail\n", encoding="utf-8")
    (root / "data" / "output" / "last_run.json").write_text('{"status": "success"}\n', encoding="utf-8")
    (root / "data" / "output" / "eidp_master.xlsx").write_bytes(b"PK fake xlsx")
    (root / "data" / "output" / "target-year-discovery" / "x-discovery-rca-batch-plan.json").write_text(
        '{"items": []}\n',
        encoding="utf-8",
    )
    (root / "data" / "eidp.sqlite3").write_bytes(b"sqlite")
    (root / "data" / "eidp.sqlite3-wal").write_bytes(b"wal")
    (root / "data" / "pdfs" / "1" / "target.pdf").write_bytes(b"%PDF")

    result = module.build_evidence_bundle(root)

    assert result["ok"] is True
    archive = Path(result["archive"])
    assert archive.name.startswith("stage6-evidence-")

    with zipfile.ZipFile(archive) as zf:
        names = set(zf.namelist())
        assert "BUILD_INFO.json" in names
        assert "logs/diagnostics-20260514-010000.txt" in names
        assert "logs/stage6-recovery-20260514-010001.json" in names
        assert "logs/bootstrap-pdfs-20260514-010002.json" in names
        assert "logs/bootstrap-pdfs-20260514-010003.log" in names
        assert "data/output/last_run.json" in names
        assert "data/output/eidp_master.xlsx" in names
        assert "data/output/target-year-discovery/x-discovery-rca-batch-plan.json" in names
        assert "stage6-evidence-manifest.json" in names
        assert "data/eidp.sqlite3" not in names
        assert "data/eidp.sqlite3-wal" not in names
        assert "data/pdfs/1/target.pdf" not in names

        manifest = json.loads(zf.read("stage6-evidence-manifest.json").decode("utf-8"))
        assert manifest["excluded"]["data"] == ["eidp.sqlite3", "eidp.sqlite3-shm", "eidp.sqlite3-wal", "pdfs"]

    verify_module = _load_verify_module()
    verification = verify_module.verify_stage6_evidence_bundle(
        archive,
        required_labels=("build_info", "diagnostics", "last_run"),
    )
    assert verification["ok"] is True
    assert verification["missing_required_labels"] == []
    assert verification["forbidden_entries"] == []


def test_build_evidence_bundle_limits_latest_diagnostics(tmp_path: Path) -> None:
    module = _load_module()
    root = tmp_path / "eidp"
    (root / "logs").mkdir(parents=True)
    for index in range(7):
        path = root / "logs" / f"diagnostics-20260514-01000{index}.txt"
        path.write_text(str(index), encoding="utf-8")

    result = module.build_evidence_bundle(root)

    with zipfile.ZipFile(Path(result["archive"])) as zf:
        diagnostics = sorted(name for name in zf.namelist() if name.startswith("logs/diagnostics-"))
        assert len(diagnostics) == 5
        assert "logs/diagnostics-20260514-010000.txt" not in diagnostics
        assert "logs/diagnostics-20260514-010001.txt" not in diagnostics


def test_verify_stage6_evidence_rejects_db_pdf_and_runtime_entries(tmp_path: Path) -> None:
    module = _load_verify_module()
    archive = tmp_path / "stage6-evidence-bad.zip"
    manifest = {
        "included": [
            {"label": "build_info", "path": "BUILD_INFO.json", "size": 2},
            {"label": "diagnostics", "path": "logs/diagnostics-20260514-010000.txt", "size": 5},
        ],
        "missing_patterns": [],
    }
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("stage6-evidence-manifest.json", json.dumps(manifest))
        zf.writestr("BUILD_INFO.json", "{}")
        zf.writestr("logs/diagnostics-20260514-010000.txt", "diag\n")
        zf.writestr("data/eidp.sqlite3", "sqlite")
        zf.writestr("data/pdfs/1/target.pdf", "%PDF")
        zf.writestr("runtime/python/python.exe", "exe")

    result = module.verify_stage6_evidence_bundle(archive)

    assert result["ok"] is False
    assert "archive contains forbidden runtime data" in result["errors"]
    assert result["forbidden_entries"] == [
        "data/eidp.sqlite3",
        "data/pdfs/1/target.pdf",
        "runtime/python/python.exe",
    ]


def test_verify_stage6_evidence_rejects_missing_manifest_and_required_label(tmp_path: Path) -> None:
    module = _load_verify_module()
    archive = tmp_path / "stage6-evidence-missing.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("BUILD_INFO.json", "{}")

    result = module.verify_stage6_evidence_bundle(archive, required_labels=("build_info", "diagnostics"))

    assert result["ok"] is False
    assert "missing stage6-evidence-manifest.json" in result["errors"]
    assert "archive is missing required evidence labels" in result["errors"]
    assert result["missing_required_labels"] == ["build_info", "diagnostics"]


def test_verify_stage6_evidence_rejects_manifest_path_not_in_zip(tmp_path: Path) -> None:
    module = _load_verify_module()
    archive = tmp_path / "stage6-evidence-missing-path.zip"
    manifest = {
        "included": [
            {"label": "build_info", "path": "BUILD_INFO.json", "size": 2},
            {"label": "diagnostics", "path": "logs/diagnostics-20260514-010000.txt", "size": 5},
        ],
        "missing_patterns": [],
    }
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("stage6-evidence-manifest.json", json.dumps(manifest))
        zf.writestr("BUILD_INFO.json", "{}")

    result = module.verify_stage6_evidence_bundle(archive)

    assert result["ok"] is False
    assert "manifest references files that are not in the archive" in result["errors"]
    assert result["warnings"] == ["missing manifest path: logs/diagnostics-20260514-010000.txt"]
