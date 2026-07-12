from __future__ import annotations

from pathlib import Path


def test_linux_launcher_sets_app_root_and_stays_loopback_bound() -> None:
    launcher = Path("deploy/linux/run_web.sh").read_text(encoding="utf-8")
    environment = Path("deploy/linux/project_env.sh").read_text(encoding="utf-8")
    sync = Path("deploy/linux/sync_venv.sh").read_text(encoding="utf-8")

    assert 'source "${SCRIPT_DIR}/project_env.sh"' in launcher
    assert 'source "${SCRIPT_DIR}/project_env.sh"' in sync
    assert "uv sync --frozen --extra pdf --extra scraper-basic" in sync
    assert 'export EIDP_APP_ROOT="${APP_ROOT}"' in environment
    assert 'export EIDP_DATA_DIR="${APP_ROOT}/data"' in environment
    assert 'export EIDP_DATABASE_URL="sqlite:///${APP_ROOT}/data/eidp.sqlite3"' in environment
    assert 'export UV_PROJECT_ENVIRONMENT="${APP_ROOT}/.venv"' in environment
    assert 'export UV_CACHE_DIR="${APP_ROOT}/.cache/uv"' in environment
    assert 'export UV_PYTHON_INSTALL_DIR="${APP_ROOT}/.cache/uv/python"' in environment
    assert 'export PLAYWRIGHT_BROWSERS_PATH="${APP_ROOT}/.cache/ms-playwright"' in environment
    assert 'export XDG_CACHE_HOME="${APP_ROOT}/.cache"' in environment
    assert 'export TMPDIR="${APP_ROOT}/.cache/tmp"' in environment
    assert 'export HOME="${APP_ROOT}/.home"' in environment
    assert "src/eidp/web/app.py" in launcher
    assert "--server.address 127.0.0.1" in launcher


def test_venus_environment_template_uses_authorized_project_root() -> None:
    environment = Path("deploy/linux/env.example").read_text(encoding="utf-8")

    assert "EIDP_APP_ROOT=/home/junming/EIDP" in environment
    assert "EIDP_DATA_DIR=/home/junming/EIDP/data" in environment
    assert "/srv/eidp" not in environment


def test_ci_has_no_windows_packaging_or_stage6_gate() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    forbidden = (
        "download_windows_runtime.py",
        "build_windows_zip.py",
        "run_non_windows_release_gates.py",
        "verify_stage6_return.py",
    )
    assert all(token not in workflow for token in forbidden)
    assert "tests/integration/test_linux_web_e2e_chain.py" in workflow
    assert "Streamlit loopback health smoke" in workflow
