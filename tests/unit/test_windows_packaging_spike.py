"""Sprint 8.5.a — Mac-side packaging guards.

These tests prove the wheelhouse rejection logic works and that the
``.bat`` skeletons obey the contract owners care about (cwd anchoring
via ``cd /d "%~dp0\\.."``, ``EIDP_APP_ROOT`` exported, UTF-8 forced
for the launcher and weekly runner).

We deliberately do NOT try to execute any ``.bat`` from Mac — that is
Sprint 8.5.b (Windows VM offline validation). Mac side proves the
asset is well-formed; Windows side proves it actually runs.
"""

from __future__ import annotations

import hashlib
import importlib.util
import sys
import types
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"
OPERATOR_RUNBOOK_PATH = REPO_ROOT / "docs" / "runbooks" / "eidp-windows.md"


def _load_build_script():
    spec = importlib.util.spec_from_file_location(
        "build_windows_zip", SCRIPTS_DIR / "build_windows_zip.py",
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _load_offline_pip_script():
    spec = importlib.util.spec_from_file_location(
        "offline_pip_install", SCRIPTS_DIR / "offline_pip_install.py",
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _load_windows_platform_module():
    spec = importlib.util.spec_from_file_location(
        "eidp.windows_platform", REPO_ROOT / "src" / "eidp" / "windows_platform.py",
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# Wheelhouse verification
# ---------------------------------------------------------------------------


def _make_empty_wheel(path: Path) -> None:
    path.write_bytes(b"")


def test_verify_wheelhouse_accepts_cp312_win_amd64(tmp_path: Path):
    bw = _load_build_script()
    wh = tmp_path / "wh"
    wh.mkdir()
    _make_empty_wheel(wh / "pymupdf-1.25.0-cp312-cp312-win_amd64.whl")
    _make_empty_wheel(wh / "structlog-25.0.0-py3-none-any.whl")

    accepted = bw.verify_wheelhouse(wh)
    assert {p.name for p in accepted} == {
        "pymupdf-1.25.0-cp312-cp312-win_amd64.whl",
        "structlog-25.0.0-py3-none-any.whl",
    }


def test_verify_wheelhouse_accepts_abi3_wheel(tmp_path: Path):
    bw = _load_build_script()
    wh = tmp_path / "wh"
    wh.mkdir()
    _make_empty_wheel(wh / "cryptography-44.0.0-cp312-abi3-win_amd64.whl")
    accepted = bw.verify_wheelhouse(wh)
    assert len(accepted) == 1


def test_verify_wheelhouse_rejects_macosx_wheel(tmp_path: Path):
    bw = _load_build_script()
    wh = tmp_path / "wh"
    wh.mkdir()
    _make_empty_wheel(wh / "pymupdf-1.25.0-cp312-cp312-macosx_11_0_arm64.whl")
    _make_empty_wheel(wh / "structlog-25.0.0-py3-none-any.whl")

    with pytest.raises(bw.WheelhouseError, match="cp312/win_amd64"):
        bw.verify_wheelhouse(wh)


def test_verify_wheelhouse_rejects_cp311_wheel(tmp_path: Path):
    bw = _load_build_script()
    wh = tmp_path / "wh"
    wh.mkdir()
    _make_empty_wheel(wh / "pymupdf-1.25.0-cp311-cp311-win_amd64.whl")
    with pytest.raises(bw.WheelhouseError):
        bw.verify_wheelhouse(wh)


def test_verify_wheelhouse_rejects_linux_manylinux(tmp_path: Path):
    bw = _load_build_script()
    wh = tmp_path / "wh"
    wh.mkdir()
    _make_empty_wheel(wh / "psycopg2_binary-2.9-cp312-cp312-manylinux_2_17_x86_64.whl")
    with pytest.raises(bw.WheelhouseError):
        bw.verify_wheelhouse(wh)


def test_verify_wheelhouse_rejects_unexpected_files(tmp_path: Path):
    bw = _load_build_script()
    wh = tmp_path / "wh"
    wh.mkdir()
    _make_empty_wheel(wh / "structlog-25.0.0-py3-none-any.whl")
    (wh / "stray.txt").write_text("oops", encoding="utf-8")
    with pytest.raises(bw.WheelhouseError):
        bw.verify_wheelhouse(wh)


def test_verify_wheelhouse_rejects_duplicate_distribution_versions(tmp_path: Path):
    bw = _load_build_script()
    wh = tmp_path / "wh"
    wh.mkdir()
    _make_empty_wheel(wh / "gitpython-3.1.49-py3-none-any.whl")
    _make_empty_wheel(wh / "gitpython-3.1.50-py3-none-any.whl")

    with pytest.raises(bw.WheelhouseError, match="duplicate distributions"):
        bw.verify_wheelhouse(wh)


def test_verify_wheelhouse_rejects_empty_directory(tmp_path: Path):
    bw = _load_build_script()
    wh = tmp_path / "wh"
    wh.mkdir()
    with pytest.raises(bw.WheelhouseError, match="empty"):
        bw.verify_wheelhouse(wh)


def test_verify_wheelhouse_rejects_missing_directory(tmp_path: Path):
    bw = _load_build_script()
    with pytest.raises(bw.WheelhouseError, match="does not exist"):
        bw.verify_wheelhouse(tmp_path / "nope")


def test_accepted_wheel_suffixes_includes_pure_python(tmp_path: Path):
    """py3-none-any and py2.py3-none-any must both be accepted because
    requirements-windows.txt includes pure-Python deps like structlog
    and tenacity."""
    bw = _load_build_script()
    assert "-py3-none-any.whl" in bw.ACCEPTED_WHEEL_SUFFIXES
    assert "-py2.py3-none-any.whl" in bw.ACCEPTED_WHEEL_SUFFIXES


def test_build_info_records_commit_branch_and_tracked_dirty_state(tmp_path: Path, monkeypatch):
    bw = _load_build_script()

    calls: list[tuple[str, ...]] = []

    def fake_git_output(_repo_root: Path, *args: str) -> str:
        calls.append(args)
        if args == ("rev-parse", "HEAD"):
            return "b" * 40
        if args == ("rev-parse", "--abbrev-ref", "HEAD"):
            return "release/test"
        if args == ("status", "--porcelain", "--untracked-files=no"):
            return " M src/eidp/review/app.py"
        return ""

    monkeypatch.setattr(bw, "_git_output", fake_git_output)

    info = bw.build_info(tmp_path)

    assert info["app"] == "EIDP"
    assert info["git_commit"] == "b" * 40
    assert info["git_branch"] == "release/test"
    assert info["git_dirty"] == "true"
    assert ("status", "--porcelain", "--untracked-files=no") in calls


def test_build_info_release_refuses_unknown_git_commit(tmp_path: Path, monkeypatch):
    """Release builds (allow_unknown_git=False) must hard-fail when the git
    commit cannot be resolved. Otherwise the resulting ZIP carries
    ``git_commit="unknown"`` and silently bypasses the source-commit gate in
    ``run_non_windows_release_gates.verify_package_source_commit``."""
    bw = _load_build_script()

    monkeypatch.setattr(bw, "_git_output", lambda *_a, **_k: "")

    with pytest.raises(RuntimeError, match="resolvable git commit"):
        bw.build_info(tmp_path)


def test_build_info_diagnostic_allows_unknown_git_commit(tmp_path: Path, monkeypatch):
    """Diagnostic builds (--allow-dirty / allow_unknown_git=True) keep the
    pre-existing escape hatch of writing ``git_commit="unknown"`` so engineers
    can still produce throwaway ZIPs from worktrees without a resolvable HEAD."""
    bw = _load_build_script()

    monkeypatch.setattr(bw, "_git_output", lambda *_a, **_k: "")

    info = bw.build_info(tmp_path, allow_unknown_git=True)

    assert info["git_commit"] == "unknown"
    assert info["git_branch"] == "unknown"
    assert info["git_dirty"] == "false"


def test_build_windows_zip_rejects_dirty_tracked_source_by_default(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bw = _load_build_script()
    wheelhouse = tmp_path / "wheelhouse"
    wheelhouse.mkdir()

    def fake_git_output(_repo_root: Path, *args: str) -> str:
        if args == ("status", "--porcelain", "--untracked-files=no"):
            return " M src/eidp/review/app.py"
        return ""

    def fail_build_project_wheel(**_kwargs):  # noqa: ANN003
        raise AssertionError("dirty source must fail before building wheels")

    monkeypatch.setattr(bw, "_git_output", fake_git_output)
    monkeypatch.setattr(bw, "build_project_wheel", fail_build_project_wheel)

    with pytest.raises(RuntimeError, match="uncommitted tracked changes"):
        bw.main([
            "--wheelhouse",
            str(wheelhouse),
            "--out-zip",
            str(tmp_path / "eidp-windows.zip"),
            "--skip-download",
            "--skip-zip",
        ])


def test_build_windows_zip_allows_dirty_source_when_explicit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bw = _load_build_script()
    wheelhouse = tmp_path / "wheelhouse"
    wheelhouse.mkdir()
    (wheelhouse / "structlog-25.0.0-py3-none-any.whl").write_bytes(b"dep")

    def fake_git_output(_repo_root: Path, *args: str) -> str:
        if args == ("status", "--porcelain", "--untracked-files=no"):
            return " M docs/reports/current-release-status.md"
        return ""

    def stub_build_project_wheel(*, repo_root: Path, out_dir: Path) -> Path:
        assert repo_root == REPO_ROOT
        wheel = out_dir / "eidp-0.2.0-py3-none-any.whl"
        wheel.write_bytes(b"project")
        return wheel

    monkeypatch.setattr(bw, "_git_output", fake_git_output)
    monkeypatch.setattr(bw, "build_project_wheel", stub_build_project_wheel)

    rc = bw.main([
        "--wheelhouse",
        str(wheelhouse),
        "--out-zip",
        str(tmp_path / "eidp-windows.zip"),
        "--skip-download",
        "--skip-zip",
        "--allow-dirty",
    ])

    assert rc == 0


def test_build_windows_zip_dirty_zip_requires_diagnostic_name(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bw = _load_build_script()
    wheelhouse = tmp_path / "wheelhouse"
    wheelhouse.mkdir()
    (wheelhouse / "structlog-25.0.0-py3-none-any.whl").write_bytes(b"dep")

    def fail_build_project_wheel(**_kwargs):  # noqa: ANN003
        raise AssertionError("release-like dirty ZIP must fail before building wheels")

    monkeypatch.setattr(bw, "build_project_wheel", fail_build_project_wheel)

    with pytest.raises(RuntimeError, match="diagnostic.*dirty"):
        bw.main([
            "--wheelhouse",
            str(wheelhouse),
            "--out-zip",
            str(tmp_path / "eidp-windows-v466.zip"),
            "--skip-download",
            "--allow-dirty",
        ])


def test_dirty_build_diagnostic_name_allows_explicit_diagnostic_names(tmp_path: Path) -> None:
    bw = _load_build_script()

    bw.assert_dirty_build_diagnostic_name(tmp_path / "eidp-windows-v466-diagnostic.zip")
    bw.assert_dirty_build_diagnostic_name(tmp_path / "eidp-windows-v466-dirty.zip")

    with pytest.raises(RuntimeError, match="diagnostic.*dirty"):
        bw.assert_dirty_build_diagnostic_name(tmp_path / "eidp-windows-v466.zip")


def test_write_sha256_sidecar_records_relative_repo_path(tmp_path: Path):
    bw = _load_build_script()
    artifact = tmp_path / "dist" / "eidp-windows.zip"
    artifact.parent.mkdir()
    artifact.write_bytes(b"zip payload")

    sidecar = bw.write_sha256_sidecar(artifact, repo_root=tmp_path)

    expected = hashlib.sha256(b"zip payload").hexdigest()
    assert sidecar == tmp_path / "dist" / "eidp-windows.zip.sha256"
    assert sidecar.read_text(encoding="utf-8") == f"{expected}  dist/eidp-windows.zip\n"


def test_copy_latest_alias_copies_zip_and_refreshes_sidecar(tmp_path: Path):
    bw = _load_build_script()
    source = tmp_path / "dist" / "eidp-windows-v102.zip"
    latest = tmp_path / "dist" / "eidp-windows.zip"
    source.parent.mkdir()
    source.write_bytes(b"new zip")
    latest.write_bytes(b"old zip")

    result = bw.copy_latest_alias(source, latest_zip=latest, repo_root=tmp_path)

    expected = hashlib.sha256(b"new zip").hexdigest()
    assert result == latest
    assert latest.read_bytes() == b"new zip"
    assert (tmp_path / "dist" / "eidp-windows.zip.sha256").read_text(encoding="utf-8") == (
        f"{expected}  dist/eidp-windows.zip\n"
    )


# ---------------------------------------------------------------------------
# .bat skeleton static review
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def bat_files() -> dict[str, str]:
    """Read all Windows launcher / utility scripts once."""
    out: dict[str, str] = {}
    for name in (
        "first_setup.bat", "launch.bat", "weekly_run.bat",
        "diagnose.bat", "uninstall.bat", "validate_install.bat", "bootstrap_pdfs.bat",
        "collect_stage6_evidence.bat", "collect_bug_report.bat", "verify_stage6_evidence.bat",
        "stage6_recovery_check.bat", "stage6_residual_cleanup.bat",
    ):
        path = SCRIPTS_DIR / name
        out[name] = path.read_text(encoding="utf-8")
    return out


def test_bat_skeletons_all_present(bat_files: dict[str, str]):
    assert set(bat_files.keys()) == {
        "first_setup.bat", "launch.bat", "weekly_run.bat",
        "diagnose.bat", "uninstall.bat", "validate_install.bat", "bootstrap_pdfs.bat",
        "collect_stage6_evidence.bat", "collect_bug_report.bat", "verify_stage6_evidence.bat",
        "stage6_recovery_check.bat", "stage6_residual_cleanup.bat",
    }


@pytest.mark.parametrize(
    "name",
    [
        "first_setup.bat",
        "launch.bat",
        "weekly_run.bat",
        "diagnose.bat",
        "validate_install.bat",
        "collect_stage6_evidence.bat",
        "collect_bug_report.bat",
        "verify_stage6_evidence.bat",
        "stage6_recovery_check.bat",
        "stage6_residual_cleanup.bat",
    ],
)
def test_bat_anchors_cwd_to_app_root(bat_files: dict[str, str], name: str):
    """All write-capable launchers MUST cd to the script parent so
    EIDP_APP_ROOT is anchored regardless of who invoked them
    (Explorer, Task Scheduler, terminal). Owner ruled this in v6
    Constraint #1."""
    body = bat_files[name]
    assert 'cd /d "%~dp0\\.."' in body, f"{name} must anchor cwd via cd /d %~dp0\\.."
    assert 'set "EIDP_APP_ROOT=%CD%"' in body, f"{name} must export EIDP_APP_ROOT"


@pytest.mark.parametrize(
    "name",
    [
        "first_setup.bat",
        "launch.bat",
        "weekly_run.bat",
        "diagnose.bat",
        "validate_install.bat",
        "collect_stage6_evidence.bat",
        "collect_bug_report.bat",
        "verify_stage6_evidence.bat",
        "stage6_recovery_check.bat",
        "stage6_residual_cleanup.bat",
    ],
)
def test_python_bat_forces_utf8(bat_files: dict[str, str], name: str):
    """Streamlit logs and run_weekly_target_year_discovery print Japanese.
    Default Windows console is cp932 in JP, which corrupts text and
    breaks downstream log scrapers. first_setup also runs Python CLI
    commands that may read/write Japanese data. v6 Constraint #6
    mandates UTF-8."""
    body = bat_files[name]
    assert 'PYTHONIOENCODING=utf-8' in body
    assert 'PYTHONUTF8=1' in body


def test_first_setup_bootstraps_db(bat_files: dict[str, str]):
    body = bat_files["first_setup.bat"]
    assert "db-bootstrap --sqlite" in body, (
        "first_setup must call eidp db-bootstrap --sqlite to create "
        "data/eidp.sqlite3 from a clean install"
    )


def test_first_setup_uses_offline_install(bat_files: dict[str, str]):
    """No-network install is the entire reason we ship a wheelhouse."""
    body = bat_files["first_setup.bat"]
    assert "offline_pip_install.py" in body
    assert "VENV_SITE_PACKAGES=%EIDP_APP_ROOT%\\.venv\\Lib\\site-packages" in body
    assert '"%RUNTIME_PY%" "%OFFLINE_PIP%" install' in body
    assert '--target "%VENV_SITE_PACKAGES%"' in body
    assert "--no-index" in body
    assert "wheelhouse" in body
    assert "EIDP_WHEEL" in body
    assert "eidp-*.whl" in body
    assert "--no-cache-dir" in body
    assert "--upgrade" in body
    assert "--force-reinstall" in body
    assert "--no-deps" in body
    assert "--reinstall-package eidp" not in body


def test_offline_pip_install_disables_wmi_before_importing_pip(monkeypatch: pytest.MonkeyPatch):
    module = _load_offline_pip_script()
    monkeypatch.setattr(module.platform, "_wmi_query", lambda *_args, **_kwargs: [], raising=False)
    for key in ("PIP_DISABLE_PIP_VERSION_CHECK", "PIP_NO_INPUT", "PIP_NO_CACHE_DIR"):
        monkeypatch.delenv(key, raising=False)

    captured: list[list[str]] = []

    def fake_pip_main(argv: list[str]) -> int:
        captured.append(argv)
        module.platform._wmi_query("Win32_OperatingSystem", (), ())  # type: ignore[attr-defined]
        return 7

    pip_pkg = types.ModuleType("pip")
    pip_pkg.__path__ = []  # type: ignore[attr-defined]
    internal_pkg = types.ModuleType("pip._internal")
    internal_pkg.__path__ = []  # type: ignore[attr-defined]
    cli_pkg = types.ModuleType("pip._internal.cli")
    cli_pkg.__path__ = []  # type: ignore[attr-defined]
    main_mod = types.ModuleType("pip._internal.cli.main")
    main_mod.main = fake_pip_main  # type: ignore[attr-defined]

    monkeypatch.setitem(sys.modules, "pip", pip_pkg)
    monkeypatch.setitem(sys.modules, "pip._internal", internal_pkg)
    monkeypatch.setitem(sys.modules, "pip._internal.cli", cli_pkg)
    monkeypatch.setitem(sys.modules, "pip._internal.cli.main", main_mod)

    with pytest.raises(OSError, match="WMI disabled"):
        module.main(["install", "--no-index"])
    assert captured == [["install", "--no-index"]]
    assert module.os.environ["PIP_DISABLE_PIP_VERSION_CHECK"] == "1"
    assert module.os.environ["PIP_NO_INPUT"] == "1"
    assert module.os.environ["PIP_NO_CACHE_DIR"] == "1"


def test_windows_platform_disables_wmi_queries(monkeypatch: pytest.MonkeyPatch):
    module = _load_windows_platform_module()
    monkeypatch.setattr(module.platform, "_wmi_query", lambda *_args, **_kwargs: [], raising=False)

    module.disable_wmi_platform_queries()

    with pytest.raises(OSError, match="WMI disabled"):
        module.platform._wmi_query("Win32_OperatingSystem", (), ())  # type: ignore[attr-defined]
    patched = module.platform._wmi_query  # type: ignore[attr-defined]
    module.disable_wmi_platform_queries()
    assert module.platform._wmi_query is patched  # type: ignore[attr-defined]


def test_first_setup_installs_optional_playwright_addon_when_extracted(bat_files: dict[str, str]):
    body = bat_files["first_setup.bat"]
    assert "playwright-addon\\wheelhouse" in body
    assert "--find-links \"%EIDP_APP_ROOT%\\playwright-addon\\wheelhouse\"" in body
    assert "scrapling[fetchers]" in body
    assert "playwright" in body


def test_first_setup_registers_weekly_task(bat_files: dict[str, str]):
    body = bat_files["first_setup.bat"]
    assert "schtasks" in body
    assert "EIDP Weekly Run" in body
    assert "EIDP_REGISTER_WEEKLY_TASK" in body


def test_first_setup_can_skip_weekly_task_for_side_by_side_preflight(bat_files: dict[str, str]):
    body = bat_files["first_setup.bat"]
    assert 'if /I "%EIDP_REGISTER_WEEKLY_TASK%"=="0"' in body
    assert "skipping Task Scheduler registration because EIDP_REGISTER_WEEKLY_TASK=0" in body
    assert ":after_weekly_task_registration" in body


def test_uninstall_does_not_delete_data(bat_files: dict[str, str]):
    """Owner data is precious. uninstall.bat must NEVER rmdir data\\."""
    body = bat_files["uninstall.bat"]
    assert "rmdir" not in body.lower()
    assert "del " not in body.lower() or "data" not in body.lower()


# ---------------------------------------------------------------------------
# Sprint 8.5.a.1 — venv + actual CLI command tokens
# ---------------------------------------------------------------------------


def test_first_setup_creates_isolated_venv(bat_files: dict[str, str]):
    """Owner finding 8.5.a P0: install must target an isolated env, not
    rely on the runtime's site-packages."""
    body = bat_files["first_setup.bat"]
    assert '"%RUNTIME_PY%" -m venv --without-pip ".venv"' in body, (
        "first_setup must create .venv with the stdlib venv module; a live "
        "operator-PC v394 probe showed `uv venv` can hang while checking "
        "the bundled Python interpreter"
    )
    assert '"%UV_EXE%" venv' not in body, "first_setup must not use `uv venv` on Windows"
    assert '"%UV_EXE%" pip install' not in body, "first_setup must not use uv pip install on Windows"
    assert '--python "%VENV_PY%"' not in body, "offline pip install must avoid uv's interpreter check"
    assert '"%RUNTIME_PY%" "%OFFLINE_PIP%" install' in body
    assert '--target "%VENV_SITE_PACKAGES%"' in body
    assert "venv" in body and ".venv" in body, "first_setup must create .venv"
    assert ".venv\\Scripts\\python.exe" in body, (
        "subsequent commands must run via .venv python so they see the "
        "wheelhouse-installed packages"
    )
    assert "--clear" not in body, (
        "first_setup must not delete an existing .venv because Windows can "
        "hold .venv\\Scripts files open while the app is running"
    )


def test_first_setup_uses_existing_cli_command_for_master(bat_files: dict[str, str]):
    """Owner finding 8.5.a P0: there is no `import-master`. The CLI
    only exposes `import-excel`."""
    body = bat_files["first_setup.bat"]
    assert "import-master" not in body, "import-master is not a real CLI command"
    assert "import-excel" in body, "use eidp import-excel for master.xlsx"


def test_first_setup_rebuilds_school_year_tasks(bat_files: dict[str, str]):
    """The first UI screen is 学校別タスク, so setup must prebuild it.

    Otherwise a clean Windows install passes schema validation but the
    operator lands on "初回は再計算してください", which breaks the
    ZIP解凍 -> ダブルクリック promise.
    """
    body = bat_files["first_setup.bat"]
    assert "rebuild-school-year-tasks" in body
    assert "school year task rebuild failed" in body


def test_first_setup_has_concurrent_run_lock(bat_files: dict[str, str]):
    """Re-running setup in the same extracted folder while another setup is
    clearing .venv can corrupt the install on Windows. first_setup must
    acquire a local lock before mutating .venv and must clean it up before
    exiting.
    """
    body = bat_files["first_setup.bat"]

    assert '.setup.lock' in body
    assert "SETUP_LOCK_STALE_HOURS=2" in body
    assert "Removed stale setup lock" in body
    assert "Remove-Item -LiteralPath $p -Recurse -Force" in body
    assert 'mkdir "%SETUP_LOCK_DIR%"' in body
    assert "setup is already running in this folder" in body
    assert 'rmdir "%SETUP_LOCK_DIR%"' in body
    assert "endlocal & exit /b %SETUP_RC%" in body


def test_first_setup_runs_after_setup_validator(bat_files: dict[str, str]):
    """A non-technical operator should not reach the UI with a half-broken
    install. first_setup must run the packaged after-setup validator
    before printing completion."""
    body = bat_files["first_setup.bat"]

    assert 'call "%EIDP_APP_ROOT%\\scripts\\validate_install.bat" --after-setup' in body
    assert "after-setup validation failed" in body


def test_first_setup_does_not_run_aggregate_or_discovery(bat_files: dict[str, str]):
    """Sprint 8.7.e: first_setup.bat must stay OFFLINE. Prefecture
    aggregate, discover-pdfs, ingest-pdfs all need internet access; we
    leave them behind the Streamlit first-run button so first_setup
    remains a clean offline install (works inside corp networks while
    waiting for proxy approval)."""
    body = bat_files["first_setup.bat"]
    assert "prefecture-aggregate" not in body, (
        "first_setup.bat must NOT call prefecture-aggregate — that step "
        "is online and belongs behind the UI first-run button"
    )
    assert "discover-pdfs" not in body, (
        "first_setup.bat must NOT call discover-pdfs"
    )
    assert "ingest-pdfs" not in body, (
        "first_setup.bat must NOT call ingest-pdfs"
    )
    assert "EIDP-start.bat" in body, (
        "first_setup.bat must point non-technical operators back to the root UI launcher"
    )
    assert "initial URL/PDF acquisition button" in body, (
        "first_setup.bat must not require non-technical operators to find "
        "bootstrap scripts in Explorer"
    )


def test_root_launchers_delegate_to_script_contracts():
    """The ZIP root must expose app-like double-click entry points so
    operators do not need to browse into scripts/."""
    setup = (REPO_ROOT / "EIDP-setup.bat").read_text(encoding="utf-8")
    start = (REPO_ROOT / "EIDP-start.bat").read_text(encoding="utf-8")
    diagnose = (REPO_ROOT / "EIDP-diagnose.bat").read_text(encoding="utf-8")
    stage6_evidence = (REPO_ROOT / "EIDP-stage6-evidence.bat").read_text(encoding="utf-8")
    stage6_verify_evidence = (REPO_ROOT / "EIDP-stage6-verify-evidence.bat").read_text(encoding="utf-8")
    stage6_recovery = (REPO_ROOT / "EIDP-stage6-recovery.bat").read_text(encoding="utf-8")

    assert 'cd /d "%~dp0"' in setup
    assert 'call "%~dp0scripts\\first_setup.bat"' in setup
    assert "EIDP-start.bat" in setup
    assert "pause" in setup
    assert "endlocal & exit /b %RC%" in setup

    assert 'cd /d "%~dp0"' in start
    assert 'call "%~dp0scripts\\launch.bat"' in start
    assert "EIDP-setup.bat" in start
    assert "pause" in start
    assert "endlocal & exit /b %RC%" in start

    assert 'cd /d "%~dp0"' in diagnose
    assert 'call "%~dp0scripts\\diagnose.bat"' in diagnose
    assert "Diagnostics collected" in diagnose
    assert "pause" in diagnose
    assert "endlocal & exit /b %RC%" in diagnose

    assert 'cd /d "%~dp0"' in stage6_evidence
    assert 'call "%~dp0scripts\\collect_stage6_evidence.bat"' in stage6_evidence
    assert "Stage 6 evidence bundle created" in stage6_evidence
    assert "logs\\stage6-evidence-*.zip" in stage6_evidence
    assert "pause" in stage6_evidence
    assert "endlocal & exit /b %RC%" in stage6_evidence

    assert 'cd /d "%~dp0"' in stage6_verify_evidence
    assert 'call "%~dp0scripts\\verify_stage6_evidence.bat"' in stage6_verify_evidence
    assert "Stage 6 evidence ZIP verified" in stage6_verify_evidence
    assert "pause" in stage6_verify_evidence
    assert "endlocal & exit /b %RC%" in stage6_verify_evidence

    assert 'cd /d "%~dp0"' in stage6_recovery
    assert 'call "%~dp0scripts\\stage6_recovery_check.bat" %*' in stage6_recovery
    assert "Stage 6 recovery check passed" in stage6_recovery
    assert "pause" in stage6_recovery
    assert "endlocal & exit /b %RC%" in stage6_recovery


def test_diagnose_bat_collects_operator_evidence_without_mutating_data(bat_files: dict[str, str]):
    body = bat_files["diagnose.bat"]

    assert "diagnostics-%DIAG_STAMP%.txt" in body
    assert "validate_windows_install.py" in body
    assert "--after-setup" in body
    assert "--after-bootstrap" in body
    assert "validate_after_bootstrap_rc" in body
    assert 'set "VALIDATE_BOOTSTRAP_RC=!ERRORLEVEL!"' in body
    assert 'set "VALIDATE_BOOTSTRAP_SHIP_GATE_RC=!ERRORLEVEL!"' in body
    assert "--after-weekly" in body
    assert "validate_after_weekly_rc" in body
    assert 'set "VALIDATE_WEEKLY_RC=!ERRORLEVEL!"' in body
    assert 'set "VALIDATE_WEEKLY_SHIP_GATE_RC=!ERRORLEVEL!"' in body
    assert "BUILD_INFO.json" in body
    assert "last_run.json" in body
    assert "final objective ship readiness" in body
    assert "report ship-readiness --json --fail-on-missing-goal" in body
    assert "ship_readiness_rc" in body
    assert "retroactive fiscal-year ship readiness" in body
    assert "settings.target_fiscal_year" in body
    assert "'ship-readiness', '--fy'" in body
    assert "retroactive_ship_readiness_rc" in body
    assert "stage6 recovery check" in body
    assert "stage6_recovery_check.py" in body
    assert "stage6_recovery_rc" in body
    assert "latest discovery RCA batch plan" in body
    assert "discovery-rca-batch-plan.json" in body
    assert "discovery_rca" in body
    assert "latest bootstrap progress" in body
    assert "latest bootstrap log tail" in body
    assert "del " not in body.lower()
    assert "rmdir" not in body.lower()


def test_operator_runbook_documents_diagnose_validation_rcs():
    body = OPERATOR_RUNBOOK_PATH.read_text(encoding="utf-8")

    assert "validate_after_bootstrap_rc" in body
    assert "validate_after_weekly_rc" in body
    assert "ship_readiness_rc" in body
    assert "report ship-readiness --json --fail-on-missing-goal" in body
    assert "--after-bootstrap" in body
    assert "--after-weekly" in body


def test_operator_runbook_documents_side_by_side_scheduler_skip():
    body = OPERATOR_RUNBOOK_PATH.read_text(encoding="utf-8")

    assert "side-by-side preflight" in body
    assert "EIDP_REGISTER_WEEKLY_TASK" in body
    assert 'EIDP_REGISTER_WEEKLY_TASK = "0"' in body
    assert "旧 production root" in body


def test_bootstrap_pdfs_bat_invokes_pipeline_script(bat_files: dict[str, str]):
    """Sprint 8.7.e: bootstrap_pdfs.bat is a thin wrapper over
    scripts/bootstrap_pdf_pipeline.py, which runs all four steps."""
    body = bat_files["bootstrap_pdfs.bat"]
    assert "bootstrap_pdf_pipeline.py" in body
    assert ".venv\\Scripts\\python.exe" in body, (
        "bootstrap_pdfs.bat must use the venv python created by first_setup"
    )
    assert "cd /d \"%~dp0\\..\"" in body, (
        "bootstrap_pdfs.bat must anchor at the application root"
    )
    assert "bootstrap-pdfs-%RUN_ID%.log" in body
    assert "bootstrap-pdfs-%RUN_ID%.json" in body
    assert "--progress-file \"%PROGRESS_PATH%\"" in body
    assert "> \"%LOG_PATH%\" 2>&1" in body
    assert "set \"RC=%ERRORLEVEL%\"" in body
    assert "endlocal & exit /b %RC%" in body


def test_first_setup_fails_loud_when_master_missing(bat_files: dict[str, str]):
    """Sprint 8.7.d data-visibility gate: master.xlsx is mandatory for
    v1. A schema-OK DB without master rows leaves every UI page blank,
    which violates the 'ZIP unzip → it works' promise. first_setup.bat
    must fail with a non-zero exit code rather than continue with a
    soft warning."""
    body = bat_files["first_setup.bat"]
    assert "WARNING: data\\master.xlsx is missing" not in body, (
        "first_setup must NOT silently continue when master.xlsx is "
        "missing — fail loud so the operator notices"
    )
    assert "ERROR: data\\master.xlsx is missing" in body
    assert "SETUP_RC=3" in body, (
        "first_setup must surface a distinct exit code (3) when master "
        "is missing so Task Scheduler / VM validator can detect it"
    )


@pytest.mark.parametrize("name", ["launch.bat", "weekly_run.bat"])
def test_runtime_bats_use_venv_python(bat_files: dict[str, str], name: str):
    body = bat_files[name]
    assert ".venv\\Scripts\\python.exe" in body, (
        f"{name} must use the venv python created by first_setup.bat"
    )


@pytest.mark.parametrize("name", ["first_setup.bat", "launch.bat", "weekly_run.bat"])
def test_runtime_bats_prefer_packaged_src_over_stale_wheel(bat_files: dict[str, str], name: str):
    body = bat_files[name]
    assert 'set "PYTHONPATH=%EIDP_APP_ROOT%\\src;%PYTHONPATH%"' in body


def test_weekly_run_uses_locale_safe_datestamp(bat_files: dict[str, str]):
    """Windows %DATE% is locale-dependent (JP console can include
    separators/day text). The log filename must come from a stable date
    formatter, not substring slicing."""
    body = bat_files["weekly_run.bat"]
    assert "Get-Date -Format yyyyMMdd" in body
    assert "%DATE:~" not in body


def test_weekly_run_preserves_python_exit_code_after_endlocal(bat_files: dict[str, str]):
    body = bat_files["weekly_run.bat"]
    assert "set \"RC=%ERRORLEVEL%\"" in body
    assert "endlocal & exit /b %RC%" in body


def test_weekly_run_supports_bounded_smoke_env_vars(bat_files: dict[str, str]):
    """Stage 6 can run the real weekly launcher with a bounded scope.

    The defaults stay production-sized, but SSH/operator-PC validation can set
    these trusted environment variables before invoking weekly_run.bat to avoid
    unbounded network and disk usage during smoke tests.
    """
    body = bat_files["weekly_run.bat"]
    assert "EIDP_WEEKLY_LIMIT" in body
    assert "--limit %EIDP_WEEKLY_LIMIT%" in body
    assert "EIDP_WEEKLY_BATCH_SIZE" in body
    assert "--batch-size %EIDP_WEEKLY_BATCH_SIZE%" in body
    assert "EIDP_WEEKLY_RATE_LIMIT" in body
    assert "--rate-limit %EIDP_WEEKLY_RATE_LIMIT%" in body
    assert "EIDP_WEEKLY_REQUEST_TIMEOUT" in body
    assert "--request-timeout %EIDP_WEEKLY_REQUEST_TIMEOUT%" in body
    assert "EIDP_WEEKLY_DRY_RUN" in body
    assert "--dry-run" in body


def test_launch_preserves_streamlit_exit_code_after_endlocal(bat_files: dict[str, str]):
    """Delayed expansion is not enabled in launch.bat. Capture the
    Streamlit return code before `endlocal` so Task Scheduler / manual
    runs observe the real failure status instead of a stale expansion."""
    body = bat_files["launch.bat"]
    assert "set \"RC=%ERRORLEVEL%\"" in body
    assert "endlocal & exit /b %RC%" in body


def test_launch_opens_browser_for_double_click_users(bat_files: dict[str, str]):
    """EIDP-start.bat should feel app-like: double-clicking must open the UI,
    not leave a non-technical operator staring at a console."""
    body = bat_files["launch.bat"]
    assert "Start-Sleep -Seconds 3" in body
    assert "Start-Process 'http://localhost:8501'" in body
    assert "--server.address 127.0.0.1" in body
    assert "--server.headless true" in body


def test_validate_install_bat_runs_packaged_validator(bat_files: dict[str, str]):
    """The VM checklist must be runnable from the extracted ZIP without
    a dev checkout or `uv run`. The wrapper chooses .venv after setup,
    falls back to the bundled runtime before setup, forwards all flags,
    and preserves the validator exit code."""
    body = bat_files["validate_install.bat"]
    assert "validate_windows_install.py" in body
    assert ".venv\\Scripts\\python.exe" in body
    assert "runtime\\python\\python.exe" in body
    assert '"%EIDP_APP_ROOT%" %*' in body
    assert "set \"RC=%ERRORLEVEL%\"" in body
    assert "endlocal & exit /b %RC%" in body


def test_stage6_recovery_check_bat_runs_packaged_helper(bat_files: dict[str, str]):
    body = bat_files["stage6_recovery_check.bat"]
    assert "stage6_recovery_check.py" in body
    assert "--expected-weekly-action" in body
    assert "--probe-weekly-dry-run" in body
    assert "--probe-lock" in body
    assert "EIDP_EXPECTED_WEEKLY_ACTION" in body
    assert "EIDP_RECOVERY_PROBE_WEEKLY_DRY_RUN" in body
    assert "EIDP_RECOVERY_PROBE_LOCK" in body
    assert "CLI_RECOVERY_ARGS" in body
    assert "%*" not in body
    assert "expected weekly action: skipped" in body
    assert "%EIDP_APP_ROOT%\\scripts\\weekly_run.bat" not in body
    assert "expected weekly action" in body
    assert "stage6-recovery-%RECOVERY_STAMP%.json" in body
    assert "set \"RC=%ERRORLEVEL%\"" in body
    assert "endlocal & exit /b %RC%" in body


def test_stage6_residual_cleanup_bat_runs_packaged_helper(bat_files: dict[str, str]):
    body = bat_files["stage6_residual_cleanup.bat"]
    assert "stage6_residual_cleanup.py" in body
    assert "--app-root" in body
    assert "--apply" in body
    assert "dry-run unless --apply" in body
    assert "stage6_residual_cleanup" in body
    assert ".venv\\Scripts\\python.exe" in body
    assert "runtime\\python\\python.exe" in body
    assert "set \"RC=%ERRORLEVEL%\"" in body
    assert "endlocal & exit /b %RC%" in body


def test_collect_stage6_evidence_bat_runs_packaged_helper(bat_files: dict[str, str]):
    body = bat_files["collect_stage6_evidence.bat"]
    assert "collect_stage6_evidence.py" in body
    assert "diagnose.bat" in body
    assert "--json" in body
    assert "logs\\stage6-evidence-*.zip" in body
    assert "live SQLite database" in body
    assert "downloaded PDFs" in body
    assert "endlocal & exit /b %BUNDLE_RC%" in body


def test_collect_bug_report_bat_runs_packaged_helper(bat_files: dict[str, str]):
    body = bat_files["collect_bug_report.bat"]
    assert "collect_bug_report.py" in body
    assert '--root "%EIDP_APP_ROOT%"' in body
    assert ".venv\\Scripts\\python.exe" in body
    assert "runtime\\python\\python.exe" in body
    assert "[collect_bug_report] ERROR: no Python found" in body
    assert "exit /b %ERRORLEVEL%" in body


def test_verify_stage6_evidence_bat_runs_latest_zip_verifier(bat_files: dict[str, str]):
    body = bat_files["verify_stage6_evidence.bat"]
    assert "verify_stage6_evidence.py" in body
    assert "stage6-evidence-*.zip" in body
    assert "stage6-evidence-verify-%VERIFY_STAMP%.json" in body
    assert "--require-label last_run" in body
    assert "set \"RC=%ERRORLEVEL%\"" in body
    assert "endlocal & exit /b %RC%" in body


def test_first_setup_calls_db_bootstrap_via_python_module(bat_files: dict[str, str]):
    body = bat_files["first_setup.bat"]
    # `python -m eidp.cli db-bootstrap --sqlite` is the actual command
    # that exists, not a bare `eidp` invocation that may not be on PATH.
    assert "-m eidp.cli db-bootstrap --sqlite" in body


# ---------------------------------------------------------------------------
# pip download command surface
# ---------------------------------------------------------------------------


def test_build_project_wheel_removes_stale_project_wheels(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    """The wheelhouse must contain one project wheel matching this source tree.

    A stale same-version wheel can otherwise survive long enough for Windows
    setup to install code that lacks newly added CLI commands.
    """
    bw = _load_build_script()
    stale = tmp_path / "eidp-0.1.0-py3-none-any.whl"
    stale.write_bytes(b"old")

    def _stub_run(cmd, cwd, check):  # noqa: ANN001
        assert cmd[:3] == ["uv", "build", "--wheel"]
        assert cwd == REPO_ROOT
        assert check is True
        (tmp_path / "eidp-0.2.0-py3-none-any.whl").write_bytes(b"new")

    monkeypatch.setattr(bw.subprocess, "run", _stub_run)

    wheel = bw.build_project_wheel(repo_root=REPO_ROOT, out_dir=tmp_path)

    assert wheel.name == "eidp-0.2.0-py3-none-any.whl"
    assert not stale.exists()


def test_skip_download_still_refreshes_project_wheel(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    """``--skip-download`` must not reuse a stale same-version project wheel.

    The flag is a dependency-download optimization for handoff rebuilds; it
    must still rebuild ``eidp`` itself so BUILD_INFO and installed code match.
    """
    bw = _load_build_script()
    wheelhouse = tmp_path / "wheelhouse"
    wheelhouse.mkdir()
    (wheelhouse / "structlog-25.0.0-py3-none-any.whl").write_bytes(b"dep")

    calls: list[str] = []

    def _stub_reset(_wheelhouse: Path) -> None:
        calls.append("reset")

    def _stub_build_project_wheel(*, repo_root: Path, out_dir: Path) -> Path:
        calls.append("build")
        assert repo_root == REPO_ROOT
        assert out_dir == wheelhouse
        wheel = wheelhouse / "eidp-0.2.0-py3-none-any.whl"
        wheel.write_bytes(b"project")
        return wheel

    def _stub_download_windows_wheels(**_kwargs):  # noqa: ANN003
        calls.append("download")

    monkeypatch.setattr(bw, "_git_output", lambda _repo_root, *args: "")
    monkeypatch.setattr(bw, "reset_wheelhouse", _stub_reset)
    monkeypatch.setattr(bw, "build_project_wheel", _stub_build_project_wheel)
    monkeypatch.setattr(bw, "download_windows_wheels", _stub_download_windows_wheels)

    rc = bw.main([
        "--wheelhouse",
        str(wheelhouse),
        "--out-zip",
        str(tmp_path / "eidp-windows.zip"),
        "--skip-download",
        "--skip-zip",
    ])

    assert rc == 0
    assert calls == ["build"]


def test_download_uses_pip_not_uv(monkeypatch: pytest.MonkeyPatch):
    """The CI packaging contract shells out to ``python -m pip download``."""
    bw = _load_build_script()
    captured: dict[str, list[str]] = {}

    def _stub_run(cmd, check):  # noqa: ANN001
        captured["cmd"] = list(cmd)

        class _R:
            returncode = 0
        return _R()

    monkeypatch.setattr(bw.subprocess, "run", _stub_run)
    bw.download_windows_wheels(
        requirements=Path("requirements-windows.txt"),
        dest=Path("/tmp/wh-test-stub"),
        python_executable="/usr/bin/fake-python",
    )

    cmd = captured["cmd"]
    # Tokens must include "-m pip download" because the CI smoke path
    # exercises this exact command surface.
    assert "-m" in cmd and "pip" in cmd and "download" in cmd
    assert "uv" not in cmd[0:1], "uv is not the entrypoint here"
    # Platform / abi tokens must be carried through.
    assert "--platform" in cmd
    assert "win_amd64" in cmd
    assert "--abi" in cmd
    assert "cp312" in cmd


# ---------------------------------------------------------------------------
# ZIP manifest must include alembic + weekly runner
# ---------------------------------------------------------------------------


def test_collect_zip_members_includes_alembic_and_weekly_runner(tmp_path: Path):
    """Owner finding 8.5.a P0/P1: the ZIP manifest was missing
    alembic.ini, migrations/, and the weekly target-year runner.
    Recreate a faux repo and assert the new collector picks them up."""
    bw = _load_build_script()

    fake_repo = tmp_path / "repo"
    (fake_repo / "src" / "eidp").mkdir(parents=True)
    (fake_repo / "src" / "eidp" / "__init__.py").write_text("", encoding="utf-8")
    (fake_repo / "src" / "sitecustomize.py").write_text("print('startup')", encoding="utf-8")
    (fake_repo / "EIDP-setup.bat").write_text("@echo off", encoding="utf-8")
    (fake_repo / "EIDP-start.bat").write_text("@echo off", encoding="utf-8")
    (fake_repo / "EIDP-diagnose.bat").write_text("@echo off", encoding="utf-8")
    (fake_repo / "EIDP-stage6-evidence.bat").write_text("@echo off", encoding="utf-8")
    (fake_repo / "EIDP-stage6-verify-evidence.bat").write_text("@echo off", encoding="utf-8")
    (fake_repo / "EIDP-stage6-recovery.bat").write_text("@echo off", encoding="utf-8")
    (fake_repo / "scripts").mkdir()
    (fake_repo / "scripts" / "first_setup.bat").write_text("@echo off", encoding="utf-8")
    (fake_repo / "scripts" / "diagnose.bat").write_text("@echo off", encoding="utf-8")
    (fake_repo / "scripts" / "collect_stage6_evidence.bat").write_text("@echo off", encoding="utf-8")
    (fake_repo / "scripts" / "verify_stage6_evidence.bat").write_text("@echo off", encoding="utf-8")
    (fake_repo / "scripts" / "run_weekly_target_year_discovery.py").write_text(
        "print('weekly')", encoding="utf-8",
    )
    (fake_repo / "scripts" / "run_r8_rediscovery_weekly.py").write_text(
        "from run_weekly_target_year_discovery import main\n", encoding="utf-8",
    )
    (fake_repo / "scripts" / "offline_pip_install.py").write_text("print('pip')", encoding="utf-8")
    (fake_repo / "scripts" / "validate_windows_install.py").write_text(
        "print('validate')", encoding="utf-8",
    )
    (fake_repo / "scripts" / "stage6_recovery_check.py").write_text(
        "print('recovery')", encoding="utf-8",
    )
    (fake_repo / "scripts" / "stage6_residual_cleanup.py").write_text(
        "print('cleanup')", encoding="utf-8",
    )
    (fake_repo / "scripts" / "collect_stage6_evidence.py").write_text("print('bundle')", encoding="utf-8")
    (fake_repo / "scripts" / "verify_stage6_evidence.py").write_text("print('verify bundle')", encoding="utf-8")
    (fake_repo / "scripts" / "verify_stage6_return.py").write_text("print('verify return')", encoding="utf-8")
    (fake_repo / "scripts" / "build_mature_year_acquisition_proof.py").write_text(
        "print('mature proof')",
        encoding="utf-8",
    )
    (fake_repo / "scripts" / "stage6_recovery_check.bat").write_text("@echo off", encoding="utf-8")
    (fake_repo / "scripts" / "stage6_residual_cleanup.bat").write_text("@echo off", encoding="utf-8")
    (fake_repo / "scripts" / "validate_install.bat").write_text("@echo off", encoding="utf-8")
    (fake_repo / "alembic.ini").write_text("[alembic]\n", encoding="utf-8")
    migrations = fake_repo / "migrations"
    (migrations / "versions").mkdir(parents=True)
    (migrations / "env.py").write_text("# env", encoding="utf-8")
    (migrations / "versions" / "abcd_initial.py").write_text("# rev", encoding="utf-8")
    (fake_repo / "docs" / "runbooks").mkdir(parents=True)
    (fake_repo / "docs" / "runbooks" / "eidp-windows.md").write_text("# runbook", encoding="utf-8")
    (fake_repo / "docs" / "runbooks" / "eidp-operator-e2e-template.md").write_text(
        "# E2E\nship_readiness_rc\n",
        encoding="utf-8",
    )
    (fake_repo / "docs" / "runbooks" / "eidp-v460-real-cycle-card.md").write_text(
        r"%USERPROFILE%\EIDP-v460-01e4427",
        encoding="utf-8",
    )
    (fake_repo / "README.md").write_text("# EIDP", encoding="utf-8")
    (fake_repo / "requirements-windows.txt").write_text("structlog\n", encoding="utf-8")
    (fake_repo / "pyproject.toml").write_text("[project]\nname='eidp'\n", encoding="utf-8")
    (fake_repo / ".streamlit").mkdir(parents=True)
    (fake_repo / ".streamlit" / "config.toml").write_text(
        '[server]\naddress = "127.0.0.1"\nheadless = true\n[browser]\ngatherUsageStats = false\n',
        encoding="utf-8",
    )

    wheelhouse = tmp_path / "wh"
    wheelhouse.mkdir()
    (wheelhouse / "structlog-25.0.0-py3-none-any.whl").write_bytes(b"")

    # Sprint 8.7.d: master.xlsx must be carried into the ZIP so
    # first_setup.bat → eidp import-excel populates the DB on day 1.
    (fake_repo / "data").mkdir(parents=True, exist_ok=True)
    (fake_repo / "data" / "master.xlsx").write_bytes(b"PK\x03\x04 fake xlsx")

    # Sprint 8.7.e: prefecture seed.csv must be carried so the
    # bootstrap_pdfs.bat pipeline can read artifact URLs and run the
    # download → aggregate → discover-pdfs → ingest chain on the
    # operator PC.
    (fake_repo / "data" / "prefecture-aggregators").mkdir(parents=True, exist_ok=True)
    (fake_repo / "data" / "prefecture-aggregators" / "seed.csv").write_text(
        "pref_key,pref_jp\nfukuoka,福岡県\n", encoding="utf-8",
    )
    # Artifacts directory must NOT be in the ZIP (downloaded at runtime).
    (fake_repo / "data" / "prefecture-aggregators" / "artifacts").mkdir(parents=True, exist_ok=True)
    (fake_repo / "data" / "prefecture-aggregators" / "artifacts" / "fukuoka.pdf").write_bytes(b"%PDF-fake")
    # Sprint 8.7.f: bootstrap Step 2b also depends on known URL and
    # corporation-domain seed CSVs. These are static seed inputs and must
    # be shipped, unlike downloaded artifact PDFs.
    (fake_repo / "data" / "url-discovery").mkdir(parents=True, exist_ok=True)
    (fake_repo / "data" / "url-discovery" / "discovered-urls-50.csv").write_text(
        "school_name,url\n東京都立大学,https://www.tmu.ac.jp/\n",
        encoding="utf-8",
    )
    (fake_repo / "data" / "url-discovery" / "corporation_domains.csv").write_text(
        "corporation_name,domain\n東京都公立大学法人,tmu.ac.jp\n",
        encoding="utf-8",
    )
    (fake_repo / "data" / "url-discovery" / "school_domain_overrides.csv").write_text(
        "prefecture,corporation_name,school_name,domain_url,url_type,confidence\n"
        "東京都,東京都公立大学法人,東京都立大学,https://www.tmu.ac.jp/,school,0.95\n",
        encoding="utf-8",
    )
    # Developer-only fixture must stay out of the operator ZIP.
    (fake_repo / "data" / "url-discovery" / "test-schools-50.csv").write_text(
        "school_name\nfixture only\n",
        encoding="utf-8",
    )
    # Discovery gold-set demonstrations are small deterministic release
    # fixtures. They should travel with the ZIP so bounded acquisition
    # regressions can be evaluated from the handed-off artifact.
    gold_entries = fake_repo / "data" / "discovery-gold-set" / "entries"
    gold_entries.mkdir(parents=True, exist_ok=True)
    (fake_repo / "data" / "discovery-gold-set" / "README.md").write_text(
        "# Discovery Gold Set\n",
        encoding="utf-8",
    )
    (fake_repo / "data" / "discovery-gold-set" / "schema.json").write_text(
        '{"title": "test discovery gold-set schema"}\n',
        encoding="utf-8",
    )
    (gold_entries / "sample.json").write_text(
        '{"entry_id": "sample", "outcome": "no_target_candidate_found"}\n',
        encoding="utf-8",
    )
    # Bootstrap pipeline scripts must be in the ZIP.
    (fake_repo / "scripts" / "bootstrap_pdf_pipeline.py").write_text("print('boot')", encoding="utf-8")
    (fake_repo / "scripts" / "bootstrap_pdfs.bat").write_text("@echo off", encoding="utf-8")
    (fake_repo / "scripts" / "download_prefecture_artifacts.py").write_text(
        "print('download')", encoding="utf-8",
    )
    (fake_repo / "scripts" / "prune_release_artifacts.py").write_text("print('prune')", encoding="utf-8")
    (fake_repo / "scripts" / "evaluate_strict_yield_bound.py").write_text("print('bound')", encoding="utf-8")
    (fake_repo / "scripts" / "rotate_audit_outbox.py").write_text("print('audit rotate')", encoding="utf-8")
    (fake_repo / "scripts" / "prune_pdf_storage.py").write_text("print('pdf prune')", encoding="utf-8")
    (fake_repo / "scripts" / "disk_health_check.py").write_text("print('disk')", encoding="utf-8")

    members = bw.collect_zip_members(repo_root=fake_repo, wheelhouse=wheelhouse)
    arcs = {arc for _, arc in members}

    assert "alembic.ini" in arcs, "alembic.ini must be in the Windows ZIP"
    assert "EIDP-setup.bat" in arcs, (
        "root-level setup launcher must be in the Windows ZIP so operators "
        "do not browse into scripts/"
    )
    assert "EIDP-start.bat" in arcs, (
        "root-level app launcher must be in the Windows ZIP so startup feels app-like"
    )
    assert "EIDP-diagnose.bat" in arcs, (
        "root-level diagnostics launcher must be in the Windows ZIP so operators "
        "can collect evidence without browsing into scripts/"
    )
    assert "EIDP-stage6-evidence.bat" in arcs, (
        "root-level Stage 6 evidence launcher must be in the Windows ZIP so operators "
        "can share one evidence bundle without browsing into scripts/"
    )
    assert "EIDP-stage6-verify-evidence.bat" in arcs, (
        "root-level Stage 6 evidence verifier must be in the Windows ZIP so operators "
        "can verify the newest evidence bundle without browsing into scripts/"
    )
    assert "EIDP-stage6-recovery.bat" in arcs, (
        "root-level Stage 6 recovery launcher must be in the Windows ZIP so operators "
        "can collect SSH recovery evidence without browsing into scripts/"
    )
    assert ".streamlit/config.toml" in arcs, (
        "Streamlit config must ship at app root to keep the operator UI headless "
        "and telemetry-free"
    )
    assert "migrations/env.py" in arcs
    assert "migrations/versions/abcd_initial.py" in arcs
    assert "src/sitecustomize.py" in arcs, (
        "Windows launchers set PYTHONPATH=src, so sitecustomize.py must ship "
        "to patch platform WMI before third-party imports"
    )
    assert "scripts/run_weekly_target_year_discovery.py" in arcs, (
        "weekly_run.bat depends on this Python entrypoint"
    )
    assert "scripts/run_r8_rediscovery_weekly.py" in arcs, (
        "legacy Task Scheduler entries depend on this compatibility wrapper"
    )
    assert "scripts/offline_pip_install.py" in arcs, (
        "first_setup.bat depends on this wrapper to avoid pip's Windows WMI hang"
    )
    assert "scripts/validate_windows_install.py" in arcs, (
        "Windows VM checklist depends on this validation entrypoint"
    )
    assert "scripts/collect_stage6_evidence.py" in arcs, (
        "Stage 6 evidence bundle depends on this read-only helper"
    )
    assert "scripts/verify_stage6_evidence.py" in arcs, (
        "Stage 6 evidence bundle must have a mechanical receiver-side verifier"
    )
    assert "scripts/verify_stage6_return.py" in arcs, (
        "Stage 6 returned owner/operator artifacts must have a mechanical release verifier"
    )
    assert "scripts/build_mature_year_acquisition_proof.py" in arcs, (
        "publication-lag release exceptions need a mechanical mature-year acquisition proof builder"
    )
    assert "scripts/verify_stage6_evidence.bat" in arcs, (
        "Stage 6 evidence verifier must have a Windows-local wrapper"
    )
    assert "scripts/stage6_recovery_check.py" in arcs, (
        "Stage 6 SSH recovery checklist depends on this read-only helper"
    )
    assert "scripts/stage6_recovery_check.bat" in arcs, (
        "Stage 6 recovery must have a Windows-local wrapper when SSH is unavailable"
    )
    assert "scripts/stage6_residual_cleanup.py" in arcs, (
        "Stage 6 residual cleanup depends on this dry-run-first helper"
    )
    assert "scripts/stage6_residual_cleanup.bat" in arcs, (
        "Stage 6 residual cleanup must have a Windows-local wrapper"
    )
    assert "scripts/collect_stage6_evidence.bat" in arcs, (
        "Stage 6 evidence bundle must have a Windows-local wrapper"
    )
    assert "scripts/validate_install.bat" in arcs, (
        "Windows VM checklist must run the validator from the extracted ZIP"
    )
    assert "scripts/first_setup.bat" in arcs
    assert "scripts/diagnose.bat" in arcs
    assert "wheelhouse/structlog-25.0.0-py3-none-any.whl" in arcs
    assert "docs/runbooks/eidp-windows.md" in arcs
    assert "docs/runbooks/eidp-operator-e2e-template.md" in arcs
    historical_runbook_arcs = {
        arc for arc in arcs
        if arc.startswith("docs/runbooks/eidp-v")
    }
    assert historical_runbook_arcs == set(), (
        "Historical handoff/runbook cards can contain tester-specific paths; "
        "the operator ZIP must ship only current operator docs. Found: "
        f"{sorted(historical_runbook_arcs)}"
    )
    assert "README.md" in arcs
    assert "requirements-windows.txt" in arcs
    assert "data/master.xlsx" in arcs, (
        "Sprint 8.7.d data-visibility gate: master.xlsx must be in the "
        "Windows ZIP so the operator's first launch shows real data"
    )
    assert "data/prefecture-aggregators/seed.csv" in arcs, (
        "Sprint 8.7.e: prefecture seed.csv carries artifact URLs and "
        "must be in the ZIP for bootstrap_pdfs.bat to use"
    )
    assert "data/url-discovery/discovered-urls-50.csv" in arcs, (
        "Sprint 8.7.f: known school URL seeds must be in the ZIP so "
        "bootstrap_pdf_pipeline.py Step 2b can register fallback crawl entry points"
    )
    assert "data/url-discovery/corporation_domains.csv" in arcs, (
        "Sprint 8.7.f: corporation-domain fallbacks must be in the ZIP so "
        "schools without prefecture-provided URLs still get deterministic discovery seeds"
    )
    assert "data/url-discovery/school_domain_overrides.csv" in arcs, (
        "School-specific URL overrides must ship so multi-brand corporations "
        "do not poison PDF discovery with a wrong corporation root"
    )
    assert "data/discovery-gold-set/README.md" in arcs
    assert "data/discovery-gold-set/schema.json" in arcs
    assert "data/discovery-gold-set/entries/sample.json" in arcs, (
        "Discovery gold-set entries must ship so bounded crawler regression "
        "evaluation can be reproduced from the Windows handoff artifact"
    )
    assert "data/url-discovery/test-schools-50.csv" not in arcs, (
        "Developer-only URL discovery fixtures must not ship in the operator ZIP"
    )
    artifact_arcs = {
        a for a in arcs
        if a.startswith("data/prefecture-aggregators/artifacts/")
    }
    assert artifact_arcs == set(), (
        "Sprint 8.7.e: artifact PDFs must NOT be in the ZIP — they are "
        "downloaded at runtime so the operator picks up newer prefecture "
        "publications without a fresh ZIP build. Found: "
        f"{sorted(artifact_arcs)}"
    )
    assert "scripts/bootstrap_pdfs.bat" in arcs, (
        "Sprint 8.7.e: bootstrap_pdfs.bat is the operator entry point "
        "for the discovery pipeline"
    )
    assert "scripts/bootstrap_pdf_pipeline.py" in arcs, (
        "Sprint 8.7.e: bootstrap_pdf_pipeline.py is the Python "
        "implementation behind bootstrap_pdfs.bat"
    )
    assert "scripts/download_prefecture_artifacts.py" in arcs, (
        "Sprint 8.7.e: download_prefecture_artifacts.py is imported "
        "by bootstrap_pdf_pipeline.py at runtime"
    )
    assert "scripts/prune_release_artifacts.py" in arcs, (
        "Release artifact pruning must ship so the operator PC can dry-run "
        "and prune stale staging ZIPs and deploy directories after handoff"
    )
    assert "scripts/rotate_audit_outbox.py" in arcs, (
        "Audit outbox rotation must ship so the operator PC can dry-run "
        "append-only audit JSONL maintenance without touching protected data directly"
    )
    assert "scripts/prune_pdf_storage.py" in arcs, (
        "PDF storage pruning must ship so the operator PC can dry-run "
        "old PDF cleanup without deleting referenced evidence"
    )
    assert "scripts/disk_health_check.py" in arcs, (
        "Disk health checks must ship so Mac/Win can detect artifact growth "
        "without deleting protected operator data"
    )


def test_resolve_master_xlsx_prefers_data_master(tmp_path: Path):
    """Sprint 8.7.d: when both candidates exist, data/master.xlsx wins."""
    bw = _load_build_script()
    fake_repo = tmp_path / "repo"
    (fake_repo / "data").mkdir(parents=True)
    (fake_repo / "sample").mkdir(parents=True)
    (fake_repo / "data" / "master.xlsx").write_bytes(b"data-version")
    (fake_repo / "sample" / "◆2025専門学校無償化情報公開まとめ.xlsx").write_bytes(b"sample-version")

    resolved = bw._resolve_master_xlsx(fake_repo)

    assert resolved is not None
    assert resolved.read_bytes() == b"data-version"


def test_resolve_master_xlsx_falls_back_to_sample(tmp_path: Path):
    """Sprint 8.7.d: a fresh clone without data/master.xlsx still resolves
    to the source spreadsheet team's filename."""
    bw = _load_build_script()
    fake_repo = tmp_path / "repo"
    (fake_repo / "sample").mkdir(parents=True)
    (fake_repo / "sample" / "◆2025専門学校無償化情報公開まとめ.xlsx").write_bytes(b"sample-version")

    resolved = bw._resolve_master_xlsx(fake_repo)

    assert resolved is not None
    assert resolved.name == "◆2025専門学校無償化情報公開まとめ.xlsx"


def test_assert_master_xlsx_present_raises_when_absent(tmp_path: Path):
    """Sprint 8.7.d: build must fail loud when no master Excel exists."""
    bw = _load_build_script()
    fake_repo = tmp_path / "repo"
    fake_repo.mkdir()

    with pytest.raises(RuntimeError, match="master Excel is missing"):
        bw.assert_master_xlsx_present(fake_repo)


def test_collect_zip_members_skips_pycache(tmp_path: Path):
    bw = _load_build_script()
    fake_repo = tmp_path / "repo"
    (fake_repo / "src" / "eidp" / "__pycache__").mkdir(parents=True)
    (fake_repo / "src" / "eidp" / "__pycache__" / "junk.pyc").write_bytes(b"")
    (fake_repo / "src" / "eidp" / "__init__.py").write_text("", encoding="utf-8")
    (fake_repo / "migrations" / "__pycache__").mkdir(parents=True)
    (fake_repo / "migrations" / "__pycache__" / "stale.pyc").write_bytes(b"")
    (fake_repo / "migrations" / "env.py").write_text("# env", encoding="utf-8")

    wheelhouse = tmp_path / "wh"
    wheelhouse.mkdir()
    (wheelhouse / "structlog-25.0.0-py3-none-any.whl").write_bytes(b"")

    members = bw.collect_zip_members(repo_root=fake_repo, wheelhouse=wheelhouse)
    arcs = {arc for _, arc in members}
    assert all("__pycache__" not in a for a in arcs)


# ---------------------------------------------------------------------------
# CLI command existence sanity
# ---------------------------------------------------------------------------


def test_resolve_alembic_ini_prefers_app_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Sprint 8.5.a.1 — db-bootstrap must read alembic.ini from
    settings.app_root first so the operator ZIP layout works."""
    from eidp.db import sqlite_bootstrap

    fake_root = tmp_path / "EIDP"
    fake_root.mkdir()
    (fake_root / "alembic.ini").write_text("[alembic]\n", encoding="utf-8")

    class _FakeSettings:
        app_root = fake_root

    import eidp.config as cfg

    monkeypatch.setattr(cfg, "settings", _FakeSettings(), raising=True)
    resolved = sqlite_bootstrap._resolve_alembic_ini()
    assert resolved == fake_root / "alembic.ini"


def test_resolve_alembic_ini_falls_back_to_repo(monkeypatch: pytest.MonkeyPatch):
    """If app_root has no alembic.ini, fallback to the repo source
    layout (parents[3] of sqlite_bootstrap.py)."""
    from eidp.db import sqlite_bootstrap

    class _NoFile:
        app_root = Path("/path/that/does/not/exist")

    import eidp.config as cfg

    monkeypatch.setattr(cfg, "settings", _NoFile(), raising=True)
    resolved = sqlite_bootstrap._resolve_alembic_ini()
    # Must point to a real alembic.ini somewhere in the repo.
    assert resolved.is_file(), f"fallback resolution did not land on a real file: {resolved}"
    assert resolved.name == "alembic.ini"


def test_first_setup_only_uses_existing_cli_subcommands():
    """Static parse first_setup.bat for ``-m eidp.cli <name>`` tokens
    and assert each name is exposed by the actual CLI. Prevents future
    drift — if someone removes a CLI subcommand the .bat will fail
    here before it fails on a Windows VM."""
    body = (SCRIPTS_DIR / "first_setup.bat").read_text(encoding="utf-8")
    import re

    used = set(re.findall(r"-m eidp\.cli\s+([a-z][a-z0-9-]+)", body))
    assert used, "first_setup.bat must invoke at least one eidp.cli subcommand"

    from eidp.cli import app

    # typer derives the CLI command name from the callback function
    # name, mapping underscores to hyphens. Use the same transform here.
    registered: set[str] = set()
    for cmd in app.registered_commands:
        if cmd.name:
            registered.add(cmd.name)
        elif cmd.callback is not None:
            registered.add(cmd.callback.__name__.replace("_", "-"))
    missing = used - registered
    assert not missing, f"first_setup.bat references unknown CLI commands: {missing}"
