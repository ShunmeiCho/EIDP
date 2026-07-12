from __future__ import annotations

import os
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
    assert "EIDP_WEB_PORT" not in launcher
    assert "--server.port" not in launcher
    assert '${STREAMLIT_SERVER_PORT:?' in launcher
    assert "${STREAMLIT_SERVER_PORT:-" not in launcher


def test_eidpctl_is_exact_thin_boundary_and_delegation() -> None:
    controller = Path("deploy/linux/eidpctl.sh")

    assert controller.read_text(encoding="utf-8") == """#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=project_env.sh
source "${SCRIPT_DIR}/project_env.sh"
cd "${APP_ROOT}"
exec uv run --frozen --no-sync python -m eidp.ops.runtime_controller "$@"
"""
    assert os.access(controller, os.X_OK)


def test_runtime_artifact_directories_are_ignored() -> None:
    ignored = Path(".gitignore").read_text(encoding="utf-8").splitlines()

    assert "/run/" in ignored
    assert "/backups/" in ignored
    assert "/evidence/runtime/" in ignored
    assert "/restore-drills/" in ignored


def test_runtime_design_states_the_deployment_uid_trust_boundary() -> None:
    design = Path("docs/superpowers/specs/2026-07-12-linux-web-v1-venus-design.md").read_text(encoding="utf-8")
    process_boundary = design.split("### 6.2 Project boundary", maxsplit=1)[1].split(
        "### 6.4 Deployment manifest", maxsplit=1
    )[0]

    assert "deployment Unix UID and its processes are the v1 runtime trust boundary" in process_boundary
    assert "must not be shared with untrusted workloads" in process_boundary
    assert "does not make every Venus local account trusted" in process_boundary
    assert "deployment is not accepted" in process_boundary
    assert "dedicated service account" in process_boundary
    assert "cgroup" in process_boundary
    assert "fd-aware import" in process_boundary


def test_operator_docs_use_only_eidpctl_for_runtime_lifecycle() -> None:
    operator_docs = (
        "README.md",
        "docs/runbooks/linux-web-dev-run.md",
        "deploy/linux/server-requirements.md",
    )
    for path in operator_docs:
        body = Path(path).read_text(encoding="utf-8")
        normalized = " ".join(body.split())

        for command in ("start", "status", "health", "stop", "restart"):
            assert f"deploy/linux/eidpctl.sh {command}" in body
        assert "EIDP_WEB_PORT" in body
        assert ".env" in body
        assert "run_web.sh` is reserved for the internal CI smoke" in normalized


def test_venus_runbook_marks_runtime_controller_available_without_changing_release_forecast() -> None:
    runbook = Path("docs/runbooks/venus-init-and-acceptance.md").read_text(encoding="utf-8")

    assert "Release forecast: **NOT_READY**" in runbook
    assert "**AVAILABLE — project-local controller.**" in runbook
    assert "**AVAILABLE:** the project-local controller parses only" in runbook
    assert "**AVAILABLE:** `deploy/linux/eidpctl.sh` is the runtime lifecycle entrypoint" in runbook
    assert "**PENDING — project-local controller.**" not in runbook
    assert "**PENDING:** the project-local controller must parse only" not in runbook
    assert "**PENDING:** implement `deploy/linux/eidpctl.sh`" not in runbook


def test_reverse_proxy_doc_marks_runtime_url_settings_available_but_ict_pending() -> None:
    requirements = Path("deploy/linux/reverse-proxy-requirements.md").read_text(encoding="utf-8")

    assert "ICT CONFIGURATION AND APP IDENTITY SUPPORT PENDING" in requirements
    assert "EIDP remains `NOT_READY`" in requirements
    assert (
        "Application support for the base path, public browser address and explicit CORS origins is **AVAILABLE**"
        in requirements
    )
    assert "the runtime controller passes the validated settings to `run_web.sh`" in requirements
    assert "Application support for `baseUrlPath`" not in requirements


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
    assert "STREAMLIT_SERVER_PORT=8502 deploy/linux/run_web.sh" in workflow
