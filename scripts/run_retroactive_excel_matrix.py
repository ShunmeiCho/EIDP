"""Run a retroactive Excel release-gate matrix for one Windows ZIP.

This is a thin orchestrator around ``run_non_windows_release_gates.py``. It
keeps the authoritative single-year gate in one place while removing the manual
copy/paste needed to run FY2025/FY2024/FY2023 backtests.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
RELEASE_GATE_SCRIPT = REPO_ROOT / "scripts" / "run_non_windows_release_gates.py"


@dataclass(frozen=True)
class MatrixCase:
    fiscal_year: int
    reference_xlsx: Path


@dataclass(frozen=True)
class MatrixCaseResult:
    fiscal_year: int
    reference_xlsx: str
    output_json: str
    command: tuple[str, ...]
    returncode: int
    duration_s: float
    ok: bool | None
    stdout_tail: str
    stderr_tail: str


def parse_case(value: str) -> MatrixCase:
    """Parse ``FY=reference.xlsx`` into a matrix case."""

    year_text, separator, reference_text = value.partition("=")
    if not separator:
        raise argparse.ArgumentTypeError("case must use YEAR=REFERENCE_XLSX")
    try:
        fiscal_year = int(year_text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"case year must be an integer: {year_text}") from exc
    if fiscal_year < 2000 or fiscal_year > 2100:
        raise argparse.ArgumentTypeError(f"case year is outside the supported range: {fiscal_year}")
    reference_xlsx = Path(reference_text)
    if not reference_text:
        raise argparse.ArgumentTypeError("case reference workbook path is empty")
    return MatrixCase(fiscal_year=fiscal_year, reference_xlsx=reference_xlsx)


def package_label(package_zip: Path) -> str:
    """Return a compact label such as ``v419`` for default output names."""

    stem = package_zip.stem
    prefix = "eidp-windows-"
    return stem[len(prefix):] if stem.startswith(prefix) else stem


def default_case_output(*, package_zip: Path, fiscal_year: int, output_dir: Path) -> Path:
    label = package_label(package_zip)
    return output_dir / f"release-gate-{label}-retroactive-fy{fiscal_year}-reference.json"


def build_case_command(
    *,
    package_zip: Path,
    case: MatrixCase,
    output_json: Path,
    skip_full_unit: bool,
    allow_stale_package: bool,
    allow_docs_only_stale_package: bool,
    retroactive_master: Path,
    numeric_tolerance: float,
) -> tuple[str, ...]:
    command = [
        sys.executable,
        str(RELEASE_GATE_SCRIPT),
        str(package_zip),
    ]
    if skip_full_unit:
        command.append("--skip-full-unit")
    if allow_stale_package:
        command.append("--allow-stale-package")
    if allow_docs_only_stale_package:
        command.append("--allow-docs-only-stale-package")
    command.extend(
        [
            "--retroactive-excel-reference",
            str(case.reference_xlsx),
            "--retroactive-fiscal-year",
            str(case.fiscal_year),
            "--retroactive-master",
            str(retroactive_master),
        ]
    )
    if numeric_tolerance > 0:
        command.extend(("--retroactive-numeric-tolerance", str(numeric_tolerance)))
    command.extend(("--json", "--output", str(output_json)))
    return tuple(command)


def _tail(text: str, *, limit: int = 4000) -> str:
    return text if len(text) <= limit else text[-limit:]


def _read_gate_ok(output_json: Path) -> bool | None:
    if not output_json.is_file():
        return None
    try:
        payload: Any = json.loads(output_json.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict) or "ok" not in payload:
        return None
    return bool(payload["ok"])


def run_case(command: tuple[str, ...], *, output_json: Path, case: MatrixCase) -> MatrixCaseResult:
    started = time.monotonic()
    output_json.parent.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    return MatrixCaseResult(
        fiscal_year=case.fiscal_year,
        reference_xlsx=str(case.reference_xlsx),
        output_json=str(output_json),
        command=command,
        returncode=completed.returncode,
        duration_s=round(time.monotonic() - started, 3),
        ok=_read_gate_ok(output_json),
        stdout_tail=_tail(completed.stdout),
        stderr_tail=_tail(completed.stderr),
    )


def run_matrix(
    *,
    package_zip: Path,
    cases: Sequence[MatrixCase],
    output_dir: Path,
    skip_full_unit: bool,
    full_unit_each_case: bool,
    allow_stale_package: bool,
    allow_docs_only_stale_package: bool,
    retroactive_master: Path,
    numeric_tolerance: float,
    keep_going: bool,
) -> list[MatrixCaseResult]:
    results: list[MatrixCaseResult] = []
    for index, case in enumerate(cases):
        case_skip_full_unit = skip_full_unit or (index > 0 and not full_unit_each_case)
        output_json = default_case_output(
            package_zip=package_zip,
            fiscal_year=case.fiscal_year,
            output_dir=output_dir,
        )
        command = build_case_command(
            package_zip=package_zip,
            case=case,
            output_json=output_json,
            skip_full_unit=case_skip_full_unit,
            allow_stale_package=allow_stale_package,
            allow_docs_only_stale_package=allow_docs_only_stale_package,
            retroactive_master=retroactive_master,
            numeric_tolerance=numeric_tolerance,
        )
        result = run_case(command, output_json=output_json, case=case)
        results.append(result)
        if result.returncode != 0 and not keep_going:
            break
    return results


def summarize(*, package_zip: Path, results: Sequence[MatrixCaseResult]) -> dict[str, Any]:
    return {
        "ok": bool(results) and all(result.returncode == 0 and result.ok is True for result in results),
        "package_zip": str(package_zip),
        "case_count": len(results),
        "results": [asdict(result) for result in results],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package_zip", type=Path, help="Windows ZIP package to verify")
    parser.add_argument(
        "--case",
        dest="cases",
        action="append",
        type=parse_case,
        required=True,
        help="Retroactive case as YEAR=REFERENCE_XLSX. Repeat for FY2025/FY2024/FY2023.",
    )
    parser.add_argument("--output-dir", type=Path, default=Path("logs"), help="Directory for per-case gate JSON files")
    parser.add_argument("--output", type=Path, help="Optional matrix summary JSON path")
    parser.add_argument("--skip-full-unit", action="store_true", help="Skip the full unit suite for every case")
    parser.add_argument(
        "--full-unit-each-case",
        action="store_true",
        help="Run the full unit suite for every case. By default only the first case runs it.",
    )
    parser.add_argument("--keep-going", action="store_true", help="Continue after a failed case")
    parser.add_argument("--allow-stale-package", action="store_true")
    parser.add_argument("--allow-docs-only-stale-package", action="store_true")
    parser.add_argument("--retroactive-master", type=Path, default=Path("data/master.xlsx"))
    parser.add_argument("--retroactive-numeric-tolerance", type=float, default=0.0)
    parser.add_argument("--json", action="store_true", help="Print matrix summary JSON")
    args = parser.parse_args(argv)

    if args.retroactive_numeric_tolerance < 0:
        parser.error("--retroactive-numeric-tolerance must be non-negative")

    results = run_matrix(
        package_zip=args.package_zip,
        cases=args.cases,
        output_dir=args.output_dir,
        skip_full_unit=args.skip_full_unit,
        full_unit_each_case=args.full_unit_each_case,
        allow_stale_package=args.allow_stale_package,
        allow_docs_only_stale_package=args.allow_docs_only_stale_package,
        retroactive_master=args.retroactive_master,
        numeric_tolerance=args.retroactive_numeric_tolerance,
        keep_going=args.keep_going,
    )
    summary = summarize(package_zip=args.package_zip, results=results)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        status = "OK" if summary["ok"] else "FAIL"
        print(f"{status}: {args.package_zip} ({len(results)} case(s))")
        for result in results:
            case_status = "OK" if result.returncode == 0 and result.ok is True else f"FAIL rc={result.returncode}"
            print(f"{case_status}: FY{result.fiscal_year} -> {result.output_json}")
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
