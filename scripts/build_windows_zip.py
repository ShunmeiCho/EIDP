"""Sprint 8.5.a — produce a Windows operator ZIP from a Mac dev box.

What this script does
---------------------
1. Builds the project wheel via ``uv build --wheel`` so ``eidp`` itself
   is installable from the wheelhouse without pulling from PyPI.
2. Downloads every transitive dependency listed in
   ``requirements-windows.txt`` constrained to
   ``--platform win_amd64 --python-version 3.12 --implementation cp
   --abi cp312 --only-binary :all:`` so we never accidentally embed a
   Mac wheel or a wheel with the wrong ABI.
3. Verifies the resulting wheelhouse: every file must end in
   ``-cp312-cp312-win_amd64.whl`` or be a pure ``-py3-none-any.whl``
   wheel. Anything else fails the build with a non-zero exit so a
   future maintainer can't ship a poisoned wheelhouse by accident.
4. Optionally assembles ``dist/eidp-windows.zip`` containing the
   wheelhouse, scripts/, src/, requirements-windows.txt, and a few
   docs. The actual Windows runtime (``python-build-standalone`` and
   ``uv.exe``) is downloaded separately and added to ``runtime/``.

The output of this script is the input to the Windows VM offline
validation gate (Sprint 8.5.b). Mac alone cannot prove "first_setup.bat
works on Windows" — this script only proves the assets are well-formed.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import zipfile
from datetime import UTC, datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from _packaging_lib import sha256_file  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REQUIREMENTS = REPO_ROOT / "requirements-windows.txt"
DEFAULT_WHEELHOUSE = REPO_ROOT / "dist" / "wheelhouse"
DEFAULT_OUT_ZIP = REPO_ROOT / "dist" / "eidp-windows.zip"

# Wheel filenames we consider safe to ship to Windows operator PCs.
#
# abi3 wheels (PEP 384 stable ABI) are forward-compatible: a wheel
# built with cp310-abi3 / cp311-abi3 / cp312-abi3 runs on every cp
# interpreter ≥ that minimum. cryptography, pymupdf, primp, protobuf
# routinely ship as cp310-abi3 to avoid republishing per minor release.
ACCEPTED_WHEEL_SUFFIXES = (
    "-cp312-cp312-win_amd64.whl",
    "-cp310-abi3-win_amd64.whl",
    "-cp311-abi3-win_amd64.whl",
    "-cp312-abi3-win_amd64.whl",
    "-py3-none-any.whl",
    "-py2.py3-none-any.whl",
    "-py312-none-any.whl",
    "-py3-none-win_amd64.whl",
    "-py2.py3-none-win_amd64.whl",
)


class WheelhouseError(RuntimeError):
    """Raised when the wheelhouse contains a wheel that would break on
    the operator PC (wrong platform, ABI, or Python version)."""


def build_project_wheel(*, repo_root: Path, out_dir: Path) -> Path:
    """Run ``uv build --wheel`` and return the path of the produced wheel."""
    out_dir.mkdir(parents=True, exist_ok=True)
    for stale_wheel in out_dir.glob("eidp-*.whl"):
        stale_wheel.unlink()
    cmd = ["uv", "build", "--wheel", "--out-dir", str(out_dir)]
    print(f"$ {' '.join(cmd)}")
    subprocess.run(cmd, cwd=repo_root, check=True)
    wheels = sorted(out_dir.glob("eidp-*.whl"))
    if not wheels:
        raise RuntimeError(f"uv build --wheel produced no eidp wheel in {out_dir}")
    return wheels[-1]


def reset_wheelhouse(wheelhouse: Path) -> None:
    """Remove stale wheelhouse contents before a fresh dependency download.

    ``pip download`` does not prune older versions that are already in the
    destination directory. Without an explicit reset, a later ZIP can carry
    both old and new versions of the same distribution, leaving the operator
    install dependent on resolver tie-breaking.
    """
    wheelhouse.mkdir(parents=True, exist_ok=True)
    for child in wheelhouse.iterdir():
        if child.name == ".gitignore":
            continue
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def download_windows_wheels(
    *,
    requirements: Path,
    dest: Path,
    python_executable: str | None = None,
    python_version: str = "3.12",
    abi: str = "cp312",
    implementation: str = "cp",
    platform: str = "win_amd64",
) -> None:
    """Download every transitive dep into ``dest`` constrained to a
    Windows / cp312 / abi cp312 wheel set.

    ``uv`` does not yet ship a ``pip download`` subcommand (only
    ``install`` / ``compile`` / ``sync``), so we use ``pip`` directly
    via ``python -m pip download``. The build host needs a Python with
    pip available; the resolved wheelhouse is platform-tagged so it is
    safe to ship to Windows regardless of build host OS.
    """
    dest.mkdir(parents=True, exist_ok=True)
    py = python_executable or sys.executable
    cmd = [
        py, "-m", "pip", "download",
        "-r", str(requirements),
        "--dest", str(dest),
        "--platform", platform,
        "--python-version", python_version,
        "--implementation", implementation,
        "--abi", abi,
        "--only-binary", ":all:",
    ]
    print(f"$ {' '.join(cmd)}")
    subprocess.run(cmd, check=True)


def verify_wheelhouse(wheelhouse: Path) -> list[Path]:
    """Return the list of accepted wheels and raise on any rejected
    file. The check is suffix-based and intentionally strict — we'd
    rather fail loud here than discover a Mac wheel on the operator PC."""
    if not wheelhouse.is_dir():
        raise WheelhouseError(f"wheelhouse does not exist: {wheelhouse}")

    accepted: list[Path] = []
    rejected: list[Path] = []
    for wheel in sorted(wheelhouse.glob("*.whl")):
        if any(wheel.name.endswith(suffix) for suffix in ACCEPTED_WHEEL_SUFFIXES):
            accepted.append(wheel)
        else:
            rejected.append(wheel)

    # pip download writes a .gitignore into its dest dir as a side effect;
    # ignore that and only flag genuinely unexpected files.
    other = [
        p for p in wheelhouse.iterdir()
        if p.suffix != ".whl" and p.name != ".gitignore"
    ]
    if rejected or other:
        rejected_str = "\n".join(f"  rejected: {p.name}" for p in rejected)
        other_str = "\n".join(f"  unexpected: {p.name}" for p in other)
        raise WheelhouseError(
            "wheelhouse contains files that do not match cp312/win_amd64 "
            "or pure-Python wheel naming:\n"
            f"{rejected_str}\n{other_str}".strip()
        )
    if not accepted:
        raise WheelhouseError(f"wheelhouse is empty: {wheelhouse}")

    by_distribution: dict[str, list[Path]] = {}
    for wheel in accepted:
        distribution = wheel.name.split("-", 1)[0].lower().replace("_", "-")
        by_distribution.setdefault(distribution, []).append(wheel)
    duplicates = {
        distribution: wheels
        for distribution, wheels in by_distribution.items()
        if len(wheels) > 1
    }
    if duplicates:
        details = "\n".join(
            f"  {distribution}: {', '.join(wheel.name for wheel in wheels)}"
            for distribution, wheels in sorted(duplicates.items())
        )
        raise WheelhouseError(f"wheelhouse contains duplicate distributions:\n{details}")
    return accepted


def _resolve_master_xlsx(repo_root: Path) -> Path | None:
    """Locate the master Excel file the Windows ZIP must ship.

    Priority order:
      1. data/master.xlsx                       — preferred canonical name
      2. sample/◆2025専門学校無償化情報公開まとめ.xlsx
                                                 — source spreadsheet
                                                   team's filename, used
                                                   when a fresh clone has
                                                   not yet been renamed

    Returns ``None`` when no candidate exists; the caller decides whether
    that should be a build failure or a soft skip.
    """
    candidates = (
        repo_root / "data" / "master.xlsx",
        repo_root / "sample" / "◆2025専門学校無償化情報公開まとめ.xlsx",
    )
    for path in candidates:
        if path.is_file():
            return path
    return None


def _to_crlf(data: bytes) -> bytes:
    """Convert any LF / mixed line endings to CRLF.

    Windows cmd.exe parses .bat files line by line — when a .bat is
    saved with Unix LF endings, cmd treats the whole file as one giant
    line and emits the cascade of "'X' is not recognized" errors that
    block first_setup.bat. Discovered live on the 2026-05-06 Win VM
    dry run; folded back into the build pipeline so source files can
    stay LF-friendly on Mac/Linux while the shipped artifact is correct.
    """
    return data.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")


def assemble_zip(
    *,
    out_zip: Path,
    repo_root: Path,
    wheelhouse: Path,
    allow_unknown_git: bool = False,
) -> Path:
    """Build a self-contained ZIP. ``runtime/`` (python-build-standalone
    + uv.exe) is appended later by a separate step that downloads the
    Windows runtime archive."""
    out_zip.parent.mkdir(parents=True, exist_ok=True)
    if out_zip.exists():
        out_zip.unlink()

    members = collect_zip_members(repo_root=repo_root, wheelhouse=wheelhouse)

    metadata = build_info(repo_root, allow_unknown_git=allow_unknown_git)
    with zipfile.ZipFile(out_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("BUILD_INFO.json", json.dumps(metadata, ensure_ascii=False, indent=2))
        for src, arc in members:
            if arc.endswith(".bat"):
                # Windows cmd.exe needs CRLF; rewrite on-the-fly.
                zf.writestr(arc, _to_crlf(src.read_bytes()))
            else:
                zf.write(src, arc)
    return out_zip


def _sidecar_display_path(path: Path, *, repo_root: Path) -> str:
    """Return a portable path for checksum sidecars.

    Absolute paths make handoff archives machine-specific. If the artifact
    lives under the repo root, record a relative path like ``dist/foo.zip``.
    """
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def write_sha256_sidecar(path: Path, *, repo_root: Path = REPO_ROOT) -> Path:
    """Write ``<artifact>.sha256`` beside the ZIP and return its path."""
    sidecar = path.with_suffix(path.suffix + ".sha256")
    digest = sha256_file(path)
    sidecar.write_text(
        f"{digest}  {_sidecar_display_path(path, repo_root=repo_root)}\n",
        encoding="utf-8",
    )
    return sidecar


def copy_latest_alias(
    source_zip: Path,
    *,
    latest_zip: Path = DEFAULT_OUT_ZIP,
    repo_root: Path = REPO_ROOT,
) -> Path:
    """Copy ``source_zip`` to the generic latest ZIP path and refresh its sidecar."""
    source_resolved = source_zip.resolve()
    latest_resolved = latest_zip.resolve()
    latest_zip.parent.mkdir(parents=True, exist_ok=True)
    if source_resolved != latest_resolved:
        shutil.copyfile(source_zip, latest_zip)
    write_sha256_sidecar(latest_zip, repo_root=repo_root)
    return latest_zip


def _git_output(repo_root: Path, *args: str) -> str:
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=repo_root,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return ""
    if proc.returncode != 0:
        return ""
    return proc.stdout.strip()


def build_info(repo_root: Path, *, allow_unknown_git: bool = False) -> dict[str, str]:
    """Build metadata shown in the operator UI and checked during handoff.

    Release builds (``allow_unknown_git=False``) refuse to write the
    ``"unknown"`` sentinel for ``git_commit``: a ZIP carrying ``"unknown"``
    bypasses the source-commit gate in
    ``run_non_windows_release_gates.verify_package_source_commit``, so we
    fail loud at build time instead of producing a stale-friendly artefact.
    Diagnostic builds opt in via ``allow_unknown_git=True`` (wired through
    ``--allow-dirty`` on the CLI).
    """
    commit = _git_output(repo_root, "rev-parse", "HEAD")
    branch = _git_output(repo_root, "rev-parse", "--abbrev-ref", "HEAD")
    dirty = "true" if _git_output(repo_root, "status", "--porcelain", "--untracked-files=no") else "false"
    if not commit and not allow_unknown_git:
        raise RuntimeError(
            "release build requires resolvable git commit; `git rev-parse HEAD` "
            "returned empty. Run inside a git checkout, or pass --allow-dirty "
            "for a diagnostic build that records git_commit=unknown."
        )
    return {
        "app": "EIDP",
        "built_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "git_commit": commit or "unknown",
        "git_branch": branch or "unknown",
        "git_dirty": dirty,
    }


def assert_clean_tracked_source(repo_root: Path) -> None:
    """Refuse release-style ZIP builds from uncommitted tracked source."""
    dirty = _git_output(repo_root, "status", "--porcelain", "--untracked-files=no")
    if not dirty:
        return
    raise RuntimeError(
        "refusing to build Windows ZIP with uncommitted tracked changes; "
        "commit or stash tracked changes, or pass --allow-dirty for a diagnostic build"
    )


def collect_zip_members(*, repo_root: Path, wheelhouse: Path) -> list[tuple[Path, str]]:
    """Enumerate every (source_path, arcname) pair the Windows ZIP must
    carry. Tested in isolation so we can assert on the manifest without
    actually building a ZIP.

    Layout:
      EIDP-setup.bat              root-level operator first setup launcher
      EIDP-start.bat              root-level operator app launcher
      EIDP-diagnose.bat           root-level diagnostics launcher
      EIDP-stage6-evidence.bat    root-level Stage 6 evidence bundle launcher
      EIDP-stage6-verify-evidence.bat root-level Stage 6 evidence verifier
      EIDP-stage6-recovery.bat    root-level Stage 6 recovery launcher
      wheelhouse/                  every accepted wheel
      src/eidp/...                 importable source layout
      src/sitecustomize.py          Windows startup compatibility hook
      scripts/*.bat                .bat launchers
      scripts/run_weekly_target_year_discovery.py weekly runner
      scripts/run_r8_rediscovery_weekly.py        backward-compatible wrapper
      scripts/validate_windows_install.py    VM/operator evidence checker
      scripts/verify_stage6_evidence.py      Stage 6 evidence bundle checker
      scripts/validate_install.bat           VM/operator wrapper for the checker
      alembic.ini                  required by db-bootstrap
      migrations/...               required by alembic stamp head
      docs/runbooks/eidp-windows.md operator runbook
      README.md                    top-level operator/developer entrypoint
      requirements-windows.txt     used by first_setup.bat
      pyproject.toml               kept for parity with dev-side config
    """
    members: list[tuple[Path, str]] = []

    # Root-level operator launchers. These make the ZIP feel like an app:
    # after extraction, the operator can double-click from C:\EIDP without
    # browsing into scripts/.
    for name in (
        "EIDP-setup.bat",
        "EIDP-start.bat",
        "EIDP-diagnose.bat",
        "EIDP-stage6-evidence.bat",
        "EIDP-stage6-verify-evidence.bat",
        "EIDP-stage6-recovery.bat",
    ):
        launcher = repo_root / name
        if launcher.is_file():
            members.append((launcher, name))

    # Streamlit config belongs at the app root. It keeps the operator UI in
    # headless/light mode and disables first-run telemetry prompts.
    streamlit_config = repo_root / ".streamlit" / "config.toml"
    if streamlit_config.is_file():
        members.append((streamlit_config, ".streamlit/config.toml"))

    # wheelhouse/
    for wheel in sorted(wheelhouse.glob("*.whl")):
        members.append((wheel, f"wheelhouse/{wheel.name}"))

    # src/eidp/ — packaged so Streamlit can run from src layout if the
    # operator prefers ``streamlit run src/eidp/review/app.py`` instead
    # of relying solely on the installed wheel.
    src_root = repo_root / "src" / "eidp"
    if src_root.is_dir():
        for path in src_root.rglob("*"):
            if path.is_file() and "__pycache__" not in path.parts:
                arcname = "src/" + path.relative_to(repo_root / "src").as_posix()
                members.append((path, arcname))
    sitecustomize = repo_root / "src" / "sitecustomize.py"
    if sitecustomize.is_file():
        members.append((sitecustomize, "src/sitecustomize.py"))

    # scripts/*.bat + production/validation Python entrypoints.
    scripts_root = repo_root / "scripts"
    if scripts_root.is_dir():
        for path in sorted(scripts_root.glob("*.bat")):
            members.append((path, f"scripts/{path.name}"))
        for name in (
            "run_weekly_target_year_discovery.py",
            "run_r8_rediscovery_weekly.py",
            "offline_pip_install.py",
            "atomic_write.py",
            "validate_windows_install.py",
            "collect_stage6_evidence.py",
            "verify_stage6_evidence.py",
            "stage6_recovery_check.py",
            "stage6_residual_cleanup.py",
            "bootstrap_pdf_pipeline.py",
            "ship_gate_contract.py",
            "download_prefecture_artifacts.py",
            "prune_release_artifacts.py",
            "rotate_audit_outbox.py",
            "prune_pdf_storage.py",
            "disk_health_check.py",
        ):
            script = scripts_root / name
            if script.is_file():
                members.append((script, f"scripts/{name}"))

    # alembic.ini + migrations/ — db-bootstrap stamps head against this.
    alembic_ini = repo_root / "alembic.ini"
    if alembic_ini.is_file():
        members.append((alembic_ini, "alembic.ini"))
    migrations_root = repo_root / "migrations"
    if migrations_root.is_dir():
        for path in migrations_root.rglob("*"):
            if path.is_file() and "__pycache__" not in path.parts:
                arcname = "migrations/" + path.relative_to(migrations_root).as_posix()
                members.append((path, arcname))

    # Operator-facing docs. Keep this narrow: historical reports/plans are
    # useful in git, but the Windows operator ZIP should carry only the
    # current runbook, E2E evidence template, and top-level entrypoint.
    runbook = repo_root / "docs" / "runbooks" / "eidp-windows.md"
    if runbook.is_file():
        members.append((runbook, "docs/runbooks/eidp-windows.md"))
    e2e_template = repo_root / "docs" / "runbooks" / "eidp-operator-e2e-template.md"
    if e2e_template.is_file():
        members.append((e2e_template, "docs/runbooks/eidp-operator-e2e-template.md"))

    # runtime/ — python-build-standalone + uv.exe. Sprint 8.5.a.2.
    # The download_windows_runtime.py script populates this directory.
    # If it's missing the build is intentionally a soft fail unless
    # --skip-runtime is passed; collect_zip_members itself just enumerates.
    runtime_root = repo_root / "runtime"
    if runtime_root.is_dir():
        for path in runtime_root.rglob("*"):
            if path.is_file() and "__pycache__" not in path.parts:
                arcname = "runtime/" + path.relative_to(runtime_root).as_posix()
                members.append((path, arcname))

    # data/master.xlsx — bootstrap school + department + support_recipient
    # rows so the operator's first launch.bat shows a populated task board.
    # first_setup.bat calls `eidp import-excel` against
    # this file. Discovered live on the 2026-05-06 Win VM dry run: a
    # schema-OK DB without master rows leaves every page blank, which
    # breaks the "ZIP unzip → it works" promise.
    #
    # The xlsx is NOT tracked in git (4.8 MB, exceeds the repo's secret /
    # large-file pre-commit threshold). Build hosts must place a current
    # master Excel at data/master.xlsx before running this script — see
    # docs/runbooks/eidp-windows.md for the canonical source. We resolve
    # via _resolve_master_xlsx so a build host that only has the sample
    # copy from the source spreadsheet team can still produce a valid
    # ZIP without a manual rename step.
    master_xlsx = _resolve_master_xlsx(repo_root)
    if master_xlsx is not None:
        members.append((master_xlsx, "data/master.xlsx"))

    # data/prefecture-aggregators/seed.csv — Sprint 8.7.e bootstrap
    # automation gate. seed.csv carries the 47-prefecture metadata
    # (artifact URLs, parser keys, verified status). The operator PC
    # downloads the per-prefecture artifact PDFs at runtime via
    # `bootstrap_pdfs.bat` so the ZIP isn't frozen against the date it
    # was packed — when prefectures publish new target-year PDFs the
    # operator picks them up automatically without a new ZIP build.
    #
    # Artifacts/ is intentionally NOT in the ZIP. They live in the
    # operator's data/prefecture-aggregators/artifacts/ after
    # bootstrap_pdfs.bat first run.
    pref_seed = repo_root / "data" / "prefecture-aggregators" / "seed.csv"
    if pref_seed.is_file():
        members.append((pref_seed, "data/prefecture-aggregators/seed.csv"))

    # data/url-discovery/*.csv — bootstrap_pdf_pipeline.py Step 2b imports
    # known school URL seeds and corporation-domain fallbacks before PDF
    # discovery. These are deterministic seed inputs, unlike downloaded
    # prefecture artifacts, so they must travel with the Windows ZIP.
    for name in ("discovered-urls-50.csv", "corporation_domains.csv", "school_domain_overrides.csv"):
        seed = repo_root / "data" / "url-discovery" / name
        if seed.is_file():
            members.append((seed, f"data/url-discovery/{name}"))

    # data/discovery-gold-set/ — bounded acquisition demonstrations used by
    # release/debug flows to evaluate crawler regressions without broad live
    # crawling. These are tiny deterministic JSON fixtures, unlike downloaded
    # prefecture artifacts, so they should travel with the handoff ZIP.
    discovery_gold_root = repo_root / "data" / "discovery-gold-set"
    if discovery_gold_root.is_dir():
        for path in discovery_gold_root.rglob("*"):
            if path.is_file() and "__pycache__" not in path.parts:
                arcname = "data/discovery-gold-set/" + path.relative_to(discovery_gold_root).as_posix()
                members.append((path, arcname))

    # top-level files
    for name in ("README.md", "requirements-windows.txt", "pyproject.toml"):
        candidate = repo_root / name
        if candidate.is_file():
            members.append((candidate, name))

    return members


def assert_master_xlsx_present(repo_root: Path) -> None:
    """Sprint 8.7.d data-visibility gate: refuse to build a Windows ZIP
    without a master Excel. A schema-OK DB without master rows leaves
    every UI page blank, so we'd rather fail at build time than ship a
    silent regression to the operator PC."""
    if _resolve_master_xlsx(repo_root) is not None:
        return
    raise RuntimeError(
        "master Excel is missing — looked for "
        "data/master.xlsx and sample/◆2025専門学校無償化情報公開まとめ.xlsx. "
        "Place a current master Excel at data/master.xlsx (preferred) or "
        "use --skip-master to build a ZIP for a build host that supplies "
        "master.xlsx out-of-band."
    )


def assert_runtime_present(repo_root: Path) -> None:
    """Sprint 8.5.a.2 — refuse to build a ZIP without the Windows runtime
    unless the caller passes --skip-runtime explicitly. Mac side cannot
    execute the binaries, but it can verify the layout matches what
    first_setup.bat expects."""
    runtime_root = repo_root / "runtime"
    py_exe = runtime_root / "python" / "python.exe"
    uv_exe = runtime_root / "uv.exe"
    missing = [p for p in (py_exe, uv_exe) if not p.is_file()]
    if missing:
        raise RuntimeError(
            "runtime files missing — run scripts/download_windows_runtime.py "
            "first, or pass --skip-runtime to build a ZIP without the "
            f"Windows runtime. Missing: {[str(p) for p in missing]}"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the Windows operator ZIP.")
    parser.add_argument("--requirements", type=Path, default=DEFAULT_REQUIREMENTS)
    parser.add_argument("--wheelhouse", type=Path, default=DEFAULT_WHEELHOUSE)
    parser.add_argument("--out-zip", type=Path, default=DEFAULT_OUT_ZIP)
    parser.add_argument("--skip-download", action="store_true",
                        help="Skip dependency download; still rebuild the EIDP project wheel")
    parser.add_argument("--skip-zip", action="store_true",
                        help="Skip assembling the ZIP — useful in CI")
    parser.add_argument("--skip-runtime", action="store_true",
                        help="Build a ZIP without runtime/. Operator must "
                             "extract a runtime ZIP separately. Mac-only "
                             "convenience flag — production ZIPs include runtime.")
    parser.add_argument("--skip-master", action="store_true",
                        help="Build a ZIP without data/master.xlsx. Use when "
                             "a downstream pipeline injects master.xlsx after "
                             "build. Production ZIPs always include master.")
    parser.add_argument("--latest-alias", action="store_true",
                        help="Also refresh dist/eidp-windows.zip and its "
                             ".sha256 sidecar from --out-zip. Use for handoff "
                             "builds with a versioned output name.")
    parser.add_argument("--allow-dirty", action="store_true",
                        help="Allow a diagnostic build from uncommitted tracked source.")
    args = parser.parse_args(argv)

    if not args.allow_dirty:
        assert_clean_tracked_source(REPO_ROOT)

    if args.skip_download:
        build_project_wheel(repo_root=REPO_ROOT, out_dir=args.wheelhouse)
    else:
        reset_wheelhouse(args.wheelhouse)
        build_project_wheel(repo_root=REPO_ROOT, out_dir=args.wheelhouse)
        download_windows_wheels(requirements=args.requirements, dest=args.wheelhouse)

    accepted = verify_wheelhouse(args.wheelhouse)
    print(f"OK: wheelhouse contains {len(accepted)} accepted wheels")

    if not args.skip_zip:
        if not args.skip_runtime:
            assert_runtime_present(REPO_ROOT)
        if not args.skip_master:
            assert_master_xlsx_present(REPO_ROOT)
        out = assemble_zip(
            out_zip=args.out_zip,
            repo_root=REPO_ROOT,
            wheelhouse=args.wheelhouse,
            allow_unknown_git=args.allow_dirty,
        )
        sidecar = write_sha256_sidecar(out, repo_root=REPO_ROOT)
        size_mb = out.stat().st_size / 1024 / 1024
        print(f"OK: wrote {out} ({size_mb:.1f} MB)")
        print(f"OK: wrote checksum sidecar {sidecar}")
        if args.latest_alias:
            latest = copy_latest_alias(out, latest_zip=DEFAULT_OUT_ZIP, repo_root=REPO_ROOT)
            print(f"OK: refreshed latest alias {latest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
