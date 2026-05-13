"""Run the non-Windows release gates for a Windows ZIP snapshot.

This script intentionally stops before the Windows setup/UI gates. It is a
developer-side reproducibility helper for the checks that can run on macOS or
Linux before a package is handed to a Windows operator machine.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class GateCommand:
    name: str
    command: tuple[str, ...]


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
                    "tests/unit/test_windows_install_validator.py",
                    "tests/unit/test_windows_distribution_verifier.py",
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
    completed = subprocess.run(
        command.command,
        cwd=REPO_ROOT,
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


def _summary_ok(sha256_check: dict[str, Any], results: Sequence[GateResult]) -> bool:
    return bool(sha256_check.get("ok")) and all(result.returncode == 0 for result in results)


def _print_text_summary(summary: dict[str, Any]) -> None:
    print(f"package: {summary['package_zip']}")
    print(f"sha256_sidecar_ok: {summary['sha256_check'].get('ok')}")
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
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    parser.add_argument("--output", type=Path, help="Optional JSON summary output path")
    args = parser.parse_args(argv)

    package_zip = args.package_zip
    sha256_check = verify_sha256_sidecar(package_zip)
    commands = build_gate_commands(
        package_zip,
        include_full_unit=not args.skip_full_unit,
        pdf_evidence_paths=args.pdf_evidence,
    )
    results = run_gates(commands, keep_going=args.keep_going) if sha256_check.get("ok") else []
    summary = {
        "ok": _summary_ok(sha256_check, results),
        "package_zip": str(package_zip),
        "sha256_check": sha256_check,
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
