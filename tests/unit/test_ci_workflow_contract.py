from pathlib import Path

WORKFLOW = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")


def test_ci_runs_linux_python_quality_gates() -> None:
    assert "uv run ruff check ." in WORKFLOW
    assert "uv run --with bandit bandit" in WORKFLOW
    assert "--severity-level high" in WORKFLOW
    assert "uv run mypy src" in WORKFLOW
    assert "uv run pytest --cov=src/eidp" in WORKFLOW


def test_ci_uses_node24_github_actions() -> None:
    assert "actions/checkout@v6" in WORKFLOW
    assert "actions/setup-python@v6" in WORKFLOW
    assert "actions/checkout@v4" not in WORKFLOW
    assert "actions/setup-python@v5" not in WORKFLOW


def test_ci_preserves_required_check_name_with_linux_web_contract() -> None:
    assert "name: Ship gate contract" in WORKFLOW
    assert "Linux/Web served-app contract tests" in WORKFLOW
    assert "tests/unit/test_linux_web_release_contract.py" in WORKFLOW
    assert "tests/unit/test_web_write_lock_contract.py" in WORKFLOW
    assert "tests/integration/test_linux_web_e2e_chain.py" in WORKFLOW
    assert "Web entry-point import smoke" in WORKFLOW
    assert "Streamlit loopback health smoke" in WORKFLOW
    assert "http://127.0.0.1:8502/_stcore/health" in WORKFLOW


def test_ci_does_not_run_retired_windows_or_stage6_assets() -> None:
    forbidden = (
        "download_windows_runtime.py",
        "build_windows_zip.py",
        "run_non_windows_release_gates.py",
        "verify_windows_distribution.py",
        "verify_stage6_return.py",
        "stage6_residual_cleanup.py",
        "eidp-windows-ci.zip",
    )
    assert all(token not in WORKFLOW for token in forbidden)
