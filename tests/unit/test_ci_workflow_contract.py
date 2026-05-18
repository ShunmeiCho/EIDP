import tomllib
from pathlib import Path

PYPROJECT = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
WORKFLOW = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

RELEASE_CRITICAL_SCRIPTS = (
    "scripts/bootstrap_pdf_pipeline.py",
    "scripts/build_mature_year_acquisition_proof.py",
    "scripts/collect_bug_report.py",
    "scripts/verify_stage6_return.py",
    "scripts/ship_gate_contract.py",
)

RELEASE_CRITICAL_TESTS = (
    "tests/unit/test_bootstrap_pdf_pipeline.py",
    "tests/unit/test_bug_signals.py",
    "tests/unit/test_mature_year_acquisition_proof.py",
    "tests/unit/test_review_bug_report.py",
    "tests/unit/test_stage6_return_verifier.py",
    "tests/unit/test_ship_gate_contract.py",
    "tests/unit/test_portability_contract.py",
)


def test_ci_runs_bandit_security_gate() -> None:
    assert "uv run --with bandit bandit" in WORKFLOW
    assert "--severity-level high" in WORKFLOW
    assert "src/eidp" in WORKFLOW


def test_ci_uses_node24_github_actions() -> None:
    assert "actions/checkout@v6" in WORKFLOW
    assert "actions/setup-python@v6" in WORKFLOW
    assert "actions/checkout@v4" not in WORKFLOW
    assert "actions/setup-python@v5" not in WORKFLOW


def test_ci_builds_windows_zip_before_release_gate() -> None:
    assert "scripts/download_windows_runtime.py" in WORKFLOW
    assert "scripts/build_windows_zip.py" in WORKFLOW
    assert "dist/eidp-windows-ci.zip" in WORKFLOW


def test_ci_dev_extra_installs_pip_for_windows_wheel_download() -> None:
    dev_deps = PYPROJECT["project"]["optional-dependencies"]["dev"]
    assert any(dep.startswith("pip") for dep in dev_deps)
    assert "uv sync --locked --extra dev" in WORKFLOW


def test_ci_runs_non_windows_release_gate_on_built_zip() -> None:
    assert "scripts/run_non_windows_release_gates.py" in WORKFLOW
    assert "dist/eidp-windows-ci.zip" in WORKFLOW
    assert "--skip-full-unit" in WORKFLOW
    assert "logs/release-gate-ci.json" in WORKFLOW


def test_ci_exposes_ship_gate_contract_as_required_check_candidate() -> None:
    assert "name: Ship gate contract" in WORKFLOW
    assert "tests/unit/test_ship_gate_contract.py" in WORKFLOW
    assert "tests/unit/test_run_weekly_target_year_discovery.py" in WORKFLOW
    assert "tests/unit/test_mature_year_acquisition_proof.py" in WORKFLOW
    assert "scripts/build_mature_year_acquisition_proof.py" in WORKFLOW
    assert "logs/ship-gate-contract-ci.json" in WORKFLOW
    assert '"target_pdf_auto_denominator_scope": "target_missing_schools_before_run"' in WORKFLOW
    assert '"target_pdf_auto_yield_pct": 62.5' in WORKFLOW


def test_ci_quality_gates_cover_release_critical_scripts() -> None:
    for path in RELEASE_CRITICAL_SCRIPTS:
        assert path in WORKFLOW


def test_ci_ruff_gate_covers_release_critical_tests() -> None:
    for path in RELEASE_CRITICAL_TESTS:
        assert path in WORKFLOW
