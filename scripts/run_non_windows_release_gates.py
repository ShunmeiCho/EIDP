"""Run the non-Windows release gates for a Windows ZIP snapshot.

This script intentionally stops before the Windows setup/UI gates. It is a
developer-side reproducibility helper for the checks that can run on macOS or
Linux before a package is handed to a Windows operator machine.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import zipfile
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_ONLY_STALE_PREFIXES = ("docs/",)


@dataclass(frozen=True)
class GateCommand:
    name: str
    command: tuple[str, ...]
    env: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class GateResult:
    name: str
    command: tuple[str, ...]
    returncode: int
    duration_s: float
    stdout_tail: str
    stderr_tail: str


def build_gate_commands(
    package_zip: Path,
    *,
    include_full_unit: bool,
    pdf_evidence_paths: Sequence[Path] = (),
) -> list[GateCommand]:
    """Return the ordered non-Windows release gates for a package ZIP."""

    py = sys.executable
    commands: list[GateCommand] = []
    if include_full_unit:
        commands.append(
            GateCommand(
                "unit_full",
                (py, "-m", "pytest", "tests/unit", "-q"),
            )
        )
    commands.extend(
        [
            GateCommand(
                "validator_distribution_unit",
                (
                    py,
                    "-m",
                    "pytest",
                    "tests/unit/test_windows_install_validator.py",
                    "tests/unit/test_windows_distribution_verifier.py",
                    "tests/unit/test_stage6_evidence_bundle.py",
                    "-q",
                ),
            ),
            GateCommand(
                "validator_distribution_mypy",
                (
                    py,
                    "-m",
                    "mypy",
                    "scripts/validate_windows_install.py",
                    "scripts/verify_windows_distribution.py",
                    "scripts/verify_stage6_evidence.py",
                ),
            ),
            GateCommand(
                "validator_distribution_ruff",
                (
                    py,
                    "-m",
                    "ruff",
                    "check",
                    "scripts/validate_windows_install.py",
                    "scripts/verify_windows_distribution.py",
                    "scripts/verify_stage6_evidence.py",
                    "tests/unit/test_windows_install_validator.py",
                    "tests/unit/test_windows_distribution_verifier.py",
                    "tests/unit/test_stage6_evidence_bundle.py",
                ),
            ),
            GateCommand(
                "discovery_gold_summary",
                (py, "-m", "eidp.cli", "discovery-gold-set", "--json"),
            ),
            GateCommand(
                "discovery_gold_expected_predictions",
                (
                    py,
                    "-m",
                    "eidp.cli",
                    "eval-discovery-gold",
                    "--predictions",
                    "data/discovery-gold-set/expected-predictions.jsonl",
                    "--fail-on-regression",
                    "--json",
                ),
            ),
            *[
                GateCommand(
                    f"discovery_gold_pdf_evidence_{index}",
                    (
                        py,
                        "-m",
                        "eidp.cli",
                        "eval-discovery-gold",
                        "--pdf-evidence",
                        str(path),
                        "--json",
                    ),
                )
                for index, path in enumerate(pdf_evidence_paths, start=1)
            ],
            GateCommand(
                "package_verify",
                (py, "scripts/verify_windows_distribution.py", str(package_zip)),
            ),
            GateCommand(
                "package_verify_demonstrated_patterns",
                (
                    py,
                    "scripts/verify_windows_distribution.py",
                    str(package_zip),
                    "--require-demonstrated-discovery-patterns",
                ),
            ),
        ]
    )
    return commands


def default_retroactive_excel_app_root(*, fiscal_year: int) -> Path:
    """Return a fresh local app root for an isolated retroactive Excel gate."""

    stamp = time.strftime("%Y%m%d-%H%M%S")
    return REPO_ROOT / "_temp" / f"non-windows-retroactive-fy{fiscal_year}-{stamp}"


def cleanup_retroactive_excel_app_root(app_root: Path) -> dict[str, Any]:
    """Remove an auto-generated retroactive gate app root after a gate run."""

    temp_root = (REPO_ROOT / "_temp").resolve()
    root = app_root.resolve()
    try:
        root.relative_to(temp_root)
    except ValueError:
        return {
            "ok": False,
            "removed": False,
            "app_root": str(app_root),
            "error": f"refusing to clean retroactive app root outside _temp: {app_root}",
        }
    if root.is_symlink():
        return {
            "ok": False,
            "removed": False,
            "app_root": str(app_root),
            "error": f"refusing to clean symlink retroactive app root: {app_root}",
        }
    if not root.name.startswith("non-windows-retroactive-"):
        return {
            "ok": False,
            "removed": False,
            "app_root": str(app_root),
            "error": f"refusing to clean non-retroactive app root: {app_root}",
        }
    if not root.exists():
        return {"ok": True, "removed": False, "app_root": str(app_root)}
    shutil.rmtree(root)
    return {"ok": True, "removed": True, "app_root": str(app_root)}


def build_retroactive_excel_gate_commands(
    *,
    app_root: Path,
    master_xlsx: Path,
    reference_xlsx: Path,
    fiscal_year: int,
    numeric_tolerance: float = 0.0,
) -> list[GateCommand]:
    """Return isolated import/export/diff gates for a retroactive workbook check."""

    if numeric_tolerance < 0:
        raise ValueError("numeric_tolerance must be non-negative")

    py = sys.executable
    data_master = app_root / "data" / "master.xlsx"
    database_path = app_root / "data" / "eidp.sqlite3"
    exported = app_root / "output" / f"retroactive-fy{fiscal_year}-export.xlsx"
    env = (
        ("EIDP_APP_ROOT", str(app_root)),
        ("EIDP_DATABASE_URL", f"sqlite:///{database_path}"),
        ("EIDP_TARGET_FISCAL_YEAR", str(fiscal_year)),
    )
    prepare_code = (
        "from pathlib import Path\n"
        "import shutil\n"
        "import sys\n"
        "root = Path(sys.argv[1])\n"
        "master = Path(sys.argv[2])\n"
        "if root.exists() and any(root.iterdir()):\n"
        "    raise SystemExit(f'retroactive app root is not empty: {root}')\n"
        "data = root / 'data'\n"
        "output = root / 'output'\n"
        "logs = root / 'logs'\n"
        "data.mkdir(parents=True, exist_ok=True)\n"
        "output.mkdir(parents=True, exist_ok=True)\n"
        "logs.mkdir(parents=True, exist_ok=True)\n"
        "shutil.copy2(master, data / 'master.xlsx')\n"
        "print(f'retroactive app root prepared: {root}')\n"
    )
    diff_command = [
        py,
        "-m",
        "eidp.cli",
        "diff-excel",
        str(exported),
        "--original",
        str(reference_xlsx),
        "--business-values",
        "--fail-on-diff",
    ]
    if numeric_tolerance > 0:
        diff_command.extend(("--numeric-tolerance", str(numeric_tolerance)))

    return [
        GateCommand(
            "retroactive_excel_prepare",
            (py, "-c", prepare_code, str(app_root), str(master_xlsx)),
        ),
        GateCommand(
            "retroactive_excel_db_bootstrap",
            (py, "-m", "eidp.cli", "db-bootstrap", "--sqlite"),
            env,
        ),
        GateCommand(
            "retroactive_excel_import",
            (py, "-m", "eidp.cli", "import-excel", str(data_master)),
            env,
        ),
        GateCommand(
            "retroactive_excel_export",
            (py, "-m", "eidp.cli", "export-excel", "--output", str(exported)),
            env,
        ),
        GateCommand(
            "retroactive_excel_diff_reference",
            tuple(diff_command),
            env,
        ),
    ]


def verify_sha256_sidecar(package_zip: Path) -> dict[str, Any]:
    """Verify ``<package>.sha256`` against the package bytes."""

    sidecar = package_zip.with_suffix(package_zip.suffix + ".sha256")
    if not package_zip.is_file():
        return {"ok": False, "error": f"package ZIP is missing: {package_zip}"}
    if not sidecar.is_file():
        return {"ok": False, "error": f"checksum sidecar is missing: {sidecar}"}

    expected = sidecar.read_text(encoding="utf-8").split()[0].strip().lower()
    actual = hashlib.sha256(package_zip.read_bytes()).hexdigest()
    return {
        "ok": actual == expected,
        "actual": actual,
        "expected": expected,
        "sidecar": str(sidecar),
    }


def _current_git_commit() -> str:
    completed = subprocess.run(
        ("git", "rev-parse", "HEAD"),
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    return completed.stdout.strip() if completed.returncode == 0 else "unknown"


def _current_git_dirty() -> bool:
    completed = subprocess.run(
        ("git", "status", "--porcelain", "--untracked-files=no"),
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    return bool(completed.stdout.strip()) if completed.returncode == 0 else True


def _docs_only_stale_check(package_commit: str, source_commit: str) -> dict[str, Any]:
    """Return whether stale package drift is limited to tracked docs files."""

    ancestor = subprocess.run(
        ("git", "merge-base", "--is-ancestor", package_commit, source_commit),
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if ancestor.returncode != 0:
        return {
            "ok": False,
            "changed_paths": [],
            "error": f"package commit {package_commit} is not an ancestor of source HEAD {source_commit}",
        }

    completed = subprocess.run(
        ("git", "diff", "--name-only", f"{package_commit}..{source_commit}"),
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or "git diff failed"
        return {"ok": False, "changed_paths": [], "error": detail}

    changed_paths = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
    non_doc_paths = [
        path for path in changed_paths if not path.startswith(DOCS_ONLY_STALE_PREFIXES)
    ]
    if non_doc_paths:
        preview = ", ".join(non_doc_paths[:5])
        suffix = "" if len(non_doc_paths) <= 5 else ", ..."
        return {
            "ok": False,
            "changed_paths": changed_paths,
            "error": f"stale package has non-doc changes: {preview}{suffix}",
        }
    return {"ok": True, "changed_paths": changed_paths}


def verify_package_source_commit(
    package_zip: Path,
    *,
    allow_stale_package: bool = False,
    allow_docs_only_stale_package: bool = False,
) -> dict[str, Any]:
    """Verify the ZIP BUILD_INFO commit matches the source tree being gated."""

    if not package_zip.is_file():
        return {"ok": False, "error": f"package ZIP is missing: {package_zip}"}
    if not zipfile.is_zipfile(package_zip):
        return {"ok": False, "error": f"package ZIP is not a valid ZIP file: {package_zip}"}
    with zipfile.ZipFile(package_zip) as zf:
        try:
            payload = json.loads(zf.read("BUILD_INFO.json").decode("utf-8"))
        except (KeyError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            return {"ok": False, "error": f"BUILD_INFO.json is not readable: {exc}"}
    if not isinstance(payload, dict):
        return {"ok": False, "error": "BUILD_INFO.json must contain an object"}
    package_commit = payload.get("git_commit")
    if not isinstance(package_commit, str) or not package_commit:
        return {"ok": False, "error": "BUILD_INFO.json missing string field: git_commit"}

    source_commit = _current_git_commit()
    source_dirty = _current_git_dirty()
    # "unknown" is the sentinel build_info() / _current_git_commit() write when
    # git metadata lookup failed. Treat it as stale on either side, never as a
    # wildcard that matches anything. Otherwise a release ZIP carrying
    # git_commit="unknown" (or a source tree with no resolvable HEAD) silently
    # bypasses commit verification. allow_stale_package is the explicit override
    # for historical package replays.
    unknown_commit = package_commit == "unknown" or source_commit == "unknown"
    stale = unknown_commit or package_commit != source_commit
    docs_only_check: dict[str, Any] | None = None
    if stale and allow_docs_only_stale_package and not unknown_commit:
        docs_only_check = _docs_only_stale_check(package_commit, source_commit)
    docs_only_stale = bool(docs_only_check and docs_only_check.get("ok"))
    stale_allowed = allow_stale_package or docs_only_stale
    result = {
        "ok": (not source_dirty) and (stale_allowed or not stale),
        "package_commit": package_commit,
        "source_commit": source_commit,
        "source_dirty": source_dirty,
        "stale": stale,
    }
    if allow_docs_only_stale_package:
        result["docs_only_stale"] = docs_only_stale
        if docs_only_check is not None:
            result["changed_paths"] = docs_only_check.get("changed_paths", [])
        if docs_only_stale:
            result["allowed_stale_reason"] = "docs_only"
    if source_dirty:
        result["error"] = "current source tree has uncommitted tracked changes"
        return result
    if stale and not stale_allowed:
        if docs_only_check and docs_only_check.get("error"):
            result["error"] = docs_only_check["error"]
            return result
        if unknown_commit:
            result["error"] = (
                f"package BUILD_INFO git_commit {package_commit} vs source HEAD {source_commit}: "
                "unresolved git commit cannot be verified; rebuild the package with a resolvable HEAD "
                "or pass --allow-stale-package for an audited historical replay"
            )
        else:
            result["error"] = (
                f"package BUILD_INFO git_commit {package_commit} does not match current source HEAD {source_commit}"
            )
    return result


def _tail(text: str, *, limit: int = 4000) -> str:
    if len(text) <= limit:
        return text
    return text[-limit:]


def _pdf_evidence_gate_error(stdout: str) -> str | None:
    """Return an error when a bounded evidence replay has mismatches.

    Evidence logs are often bounded samples, so missing gold entries are normal.
    Failed or unexpected predictions are not normal and should fail this helper.
    """

    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError as exc:
        return f"could not parse pdf-evidence evaluation JSON: {exc}"
    failed = int(payload.get("failed_predictions", 0))
    unexpected = int(payload.get("unexpected_predictions", 0))
    if failed or unexpected:
        return f"pdf-evidence replay had failed_predictions={failed}, unexpected_predictions={unexpected}"
    return None


def run_gate(command: GateCommand) -> GateResult:
    started = time.monotonic()
    env = None
    if command.env:
        env = os.environ.copy()
        env.update(dict(command.env))
    completed = subprocess.run(
        command.command,
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    validation_error = None
    if completed.returncode == 0 and command.name.startswith("discovery_gold_pdf_evidence_"):
        validation_error = _pdf_evidence_gate_error(completed.stdout)
    returncode = 1 if validation_error else completed.returncode
    stderr = completed.stderr
    if validation_error:
        stderr = f"{stderr}\n{validation_error}".lstrip()
    return GateResult(
        name=command.name,
        command=command.command,
        returncode=returncode,
        duration_s=round(time.monotonic() - started, 3),
        stdout_tail=_tail(completed.stdout),
        stderr_tail=_tail(stderr),
    )


def run_gates(commands: Sequence[GateCommand], *, keep_going: bool) -> list[GateResult]:
    results: list[GateResult] = []
    for command in commands:
        result = run_gate(command)
        results.append(result)
        if result.returncode != 0 and not keep_going:
            break
    return results


def _summary_ok(
    sha256_check: dict[str, Any],
    package_source_check: dict[str, Any],
    results: Sequence[GateResult],
    retroactive_excel_cleanup: dict[str, Any] | None = None,
) -> bool:
    cleanup_ok = retroactive_excel_cleanup is None or bool(retroactive_excel_cleanup.get("ok"))
    return (
        bool(sha256_check.get("ok"))
        and bool(package_source_check.get("ok"))
        and all(result.returncode == 0 for result in results)
        and cleanup_ok
    )


def _print_text_summary(summary: dict[str, Any]) -> None:
    print(f"package: {summary['package_zip']}")
    print(f"sha256_sidecar_ok: {summary['sha256_check'].get('ok')}")
    package_source_check = summary.get("package_source_check", {})
    print(f"package_source_check_ok: {package_source_check.get('ok')}")
    if package_source_check.get("error"):
        print(f"package_source_check_error: {package_source_check['error']}")
    for result in summary["results"]:
        status = "OK" if result["returncode"] == 0 else f"FAIL rc={result['returncode']}"
        print(f"{status}: {result['name']} ({result['duration_s']}s)")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package_zip", type=Path, help="Windows ZIP package to verify")
    parser.add_argument(
        "--pdf-evidence",
        type=Path,
        action="append",
        default=[],
        help="Optional discovery evidence JSONL to replay with eval-discovery-gold",
    )
    parser.add_argument("--skip-full-unit", action="store_true", help="Skip the full unit suite")
    parser.add_argument("--keep-going", action="store_true", help="Continue after a failed gate")
    parser.add_argument(
        "--allow-stale-package",
        action="store_true",
        help="Allow BUILD_INFO git_commit to differ from the current source HEAD for historical package checks",
    )
    parser.add_argument(
        "--allow-docs-only-stale-package",
        action="store_true",
        help=(
            "Allow BUILD_INFO git_commit to lag source HEAD only when the tracked diff from "
            "package commit to HEAD is limited to docs/ files"
        ),
    )
    parser.add_argument(
        "--retroactive-excel-reference",
        type=Path,
        help=(
            "Optional reference workbook for an isolated retroactive Excel business-value gate. "
            "When set, the helper bootstraps a temporary SQLite app root, imports master.xlsx, "
            "exports the retroactive FY workbook, and diffs it against this reference."
        ),
    )
    parser.add_argument(
        "--retroactive-fiscal-year",
        type=int,
        default=2025,
        help="Fiscal year for --retroactive-excel-reference (default: 2025).",
    )
    parser.add_argument(
        "--retroactive-master",
        type=Path,
        default=Path("data/master.xlsx"),
        help="Master workbook to import for --retroactive-excel-reference.",
    )
    parser.add_argument(
        "--retroactive-numeric-tolerance",
        type=float,
        default=0.0,
        help=(
            "Absolute numeric tolerance for the retroactive Excel business-value diff "
            "(default: 0.0, exact numeric match)."
        ),
    )
    parser.add_argument(
        "--retroactive-app-root",
        type=Path,
        help="Optional empty app root for --retroactive-excel-reference. Defaults to _temp/non-windows-retroactive-*.",
    )
    parser.add_argument(
        "--keep-retroactive-app-root",
        action="store_true",
        help=(
            "Keep the auto-generated retroactive app root after the gate run. "
            "By default, roots created under _temp/non-windows-retroactive-* are removed."
        ),
    )
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    parser.add_argument("--output", type=Path, help="Optional JSON summary output path")
    args = parser.parse_args(argv)

    package_zip = args.package_zip
    if args.retroactive_numeric_tolerance < 0:
        parser.error("--retroactive-numeric-tolerance must be non-negative")
    sha256_check = verify_sha256_sidecar(package_zip)
    package_source_check = verify_package_source_commit(
        package_zip,
        allow_stale_package=args.allow_stale_package,
        allow_docs_only_stale_package=args.allow_docs_only_stale_package,
    )
    commands = build_gate_commands(
        package_zip,
        include_full_unit=not args.skip_full_unit,
        pdf_evidence_paths=args.pdf_evidence,
    )
    retroactive_excel_gate = None
    retroactive_app_root: Path | None = None
    cleanup_retroactive_root = False
    retroactive_excel_cleanup = None
    if args.retroactive_excel_reference is not None:
        retroactive_app_root = args.retroactive_app_root or default_retroactive_excel_app_root(
            fiscal_year=args.retroactive_fiscal_year,
        )
        cleanup_retroactive_root = args.retroactive_app_root is None and not args.keep_retroactive_app_root
        retroactive_excel_gate = {
            "enabled": True,
            "app_root": str(retroactive_app_root),
            "fiscal_year": args.retroactive_fiscal_year,
            "master_xlsx": str(args.retroactive_master),
            "reference_xlsx": str(args.retroactive_excel_reference),
            "numeric_tolerance": args.retroactive_numeric_tolerance,
            "cleanup_after_run": cleanup_retroactive_root,
        }
        commands.extend(
            build_retroactive_excel_gate_commands(
                app_root=retroactive_app_root,
                master_xlsx=args.retroactive_master,
                reference_xlsx=args.retroactive_excel_reference,
                fiscal_year=args.retroactive_fiscal_year,
                numeric_tolerance=args.retroactive_numeric_tolerance,
            )
        )
    try:
        results = (
            run_gates(commands, keep_going=args.keep_going)
            if sha256_check.get("ok") and package_source_check.get("ok")
            else []
        )
    finally:
        if cleanup_retroactive_root and retroactive_app_root is not None:
            retroactive_excel_cleanup = cleanup_retroactive_excel_app_root(retroactive_app_root)
    summary = {
        "ok": _summary_ok(sha256_check, package_source_check, results, retroactive_excel_cleanup),
        "package_zip": str(package_zip),
        "sha256_check": sha256_check,
        "package_source_check": package_source_check,
        "retroactive_excel_gate": retroactive_excel_gate,
        "retroactive_excel_cleanup": retroactive_excel_cleanup,
        "results": [asdict(result) for result in results],
    }

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        _print_text_summary(summary)
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
