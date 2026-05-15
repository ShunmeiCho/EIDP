from pathlib import Path

WORKFLOW = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")


def test_ci_runs_bandit_security_gate() -> None:
    assert "uv run --with bandit bandit" in WORKFLOW
    assert "--severity-level high" in WORKFLOW
    assert "src/eidp" in WORKFLOW


def test_ci_builds_windows_zip_before_release_gate() -> None:
    assert "scripts/download_windows_runtime.py" in WORKFLOW
    assert "scripts/build_windows_zip.py" in WORKFLOW
    assert "dist/eidp-windows-ci.zip" in WORKFLOW


def test_ci_runs_non_windows_release_gate_on_built_zip() -> None:
    assert "scripts/run_non_windows_release_gates.py" in WORKFLOW
    assert "dist/eidp-windows-ci.zip" in WORKFLOW
    assert "--skip-full-unit" in WORKFLOW
    assert "logs/release-gate-ci.json" in WORKFLOW
