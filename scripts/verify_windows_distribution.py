"""Verify Windows distribution ZIPs before the Windows VM gate.

This verifier is intentionally stricter than a manifest smoke test. It
answers a release question: "is this ZIP complete enough to hand to the
Windows VM offline validation step?"

It does not execute Windows binaries. That remains the Sprint 8.5.b VM gate.
"""

from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import importlib.util
import json
import sys
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from _packaging_lib import sha256_file  # noqa: E402,F401  (re-exported for tests/callers)
from windows_path_safety import check_windows_safe_paths, issues_by_kind  # noqa: E402


def _load_accepted_wheel_suffixes() -> tuple[str, ...]:
    """Load the wheel suffix contract from build_windows_zip.py.

    This script can be executed directly from any cwd, so do a file-based
    import instead of relying on PYTHONPATH.
    """
    build_script = SCRIPT_DIR / "build_windows_zip.py"
    spec = importlib.util.spec_from_file_location("build_windows_zip_for_verify", build_script)
    if not spec or not spec.loader:
        raise RuntimeError(f"cannot load {build_script}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return tuple(module.ACCEPTED_WHEEL_SUFFIXES)


ACCEPTED_WHEEL_SUFFIXES = _load_accepted_wheel_suffixes()


@dataclass
class ZipCheck:
    name: str
    path: Path
    ok: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)

    def fail(self, message: str) -> None:
        self.ok = False
        self.errors.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)


CORE_REQUIRED_EXACT = (
    "BUILD_INFO.json",
    ".streamlit/config.toml",
    "EIDP-setup.bat",
    "EIDP-start.bat",
    "EIDP-diagnose.bat",
    "README.md",
    "requirements-windows.txt",
    "pyproject.toml",
    "alembic.ini",
    "docs/runbooks/eidp-windows.md",
    "scripts/first_setup.bat",
    "scripts/launch.bat",
    "scripts/weekly_run.bat",
    "scripts/diagnose.bat",
    "scripts/uninstall.bat",
    "scripts/validate_install.bat",
    "scripts/run_weekly_target_year_discovery.py",
    "scripts/run_r8_rediscovery_weekly.py",
    "scripts/validate_windows_install.py",
    "scripts/bootstrap_pdf_pipeline.py",
    "scripts/download_prefecture_artifacts.py",
    "data/prefecture-aggregators/seed.csv",
    "data/url-discovery/discovered-urls-50.csv",
    "data/url-discovery/corporation_domains.csv",
    "src/eidp/review/app.py",
    "src/eidp/review/operator_pages.py",
    "src/eidp/review/_pages/audit_log.py",
    "src/eidp/review/_pages/settings_page.py",
    "src/eidp/review/_pages/school_year_tasks.py",
    "src/eidp/review/_pages/pdf_manual_entry.py",
    "src/eidp/review/_pages/prefecture_remarks.py",
    "src/eidp/review/_pages/fiscal_year_override.py",
    "src/eidp/review/_pages/excel_preview.py",
    "src/eidp/scraper/prefecture_aggregator.py",
    "runtime/python/python.exe",
    "runtime/uv.exe",
)

CORE_REQUIRED_PREFIXES = (
    "src/eidp/",
    "migrations/",
    "wheelhouse/",
)

EXPECTED_PREFECTURE_KEYS = frozenset(
    {
        "aichi",
        "akita",
        "aomori",
        "chiba",
        "ehime",
        "fukui",
        "fukuoka",
        "fukushima",
        "gifu",
        "gunma",
        "hiroshima",
        "hokkaido",
        "hyogo",
        "ibaraki",
        "ishikawa",
        "iwate",
        "kagawa",
        "kagoshima",
        "kanagawa",
        "kochi",
        "kumamoto",
        "kyoto",
        "mie",
        "miyagi",
        "miyazaki",
        "nagano",
        "nagasaki",
        "nara",
        "niigata",
        "oita",
        "okayama",
        "okinawa",
        "osaka",
        "saga",
        "saitama",
        "shiga",
        "shimane",
        "shizuoka",
        "tochigi",
        "tokushima",
        "tokyo",
        "tottori",
        "toyama",
        "wakayama",
        "yamagata",
        "yamaguchi",
        "yamanashi",
    }
)

DOWNLOADABLE_PREFECTURE_STATUSES = frozenset({"spiked", "downloaded", "url_found"})
PREFECTURE_ARTIFACT_FORMATS = frozenset({"pdf", "xlsx", "html", "htm"})

OCR_REQUIRED_EXACT = (
    "ocr-addon/tesseract/tesseract.exe",
    "ocr-addon/tessdata/jpn.traineddata",
    "ocr-addon/MANIFEST.json",
)

PLAYWRIGHT_REQUIRED_EXACT = (
    "playwright-addon/MANIFEST.json",
)

PLAYWRIGHT_REQUIRED_PREFIXES = (
    "playwright-addon/wheelhouse/",
    "playwright-addon/ms-playwright/",
)


def _read_zip_names(check: ZipCheck) -> set[str] | None:
    if not check.path.is_file():
        check.fail(f"zip does not exist: {check.path}")
        return None
    check.details["size_bytes"] = check.path.stat().st_size
    check.details["sha256"] = sha256_file(check.path)
    if not zipfile.is_zipfile(check.path):
        check.fail(f"not a zip file: {check.path}")
        return None
    with zipfile.ZipFile(check.path) as zf:
        names = zf.namelist()
    seen: set[str] = set()
    duplicates: list[str] = []
    for name in names:
        if name in seen:
            duplicates.append(name)
        else:
            seen.add(name)
    if duplicates:
        check.fail(f"zip contains duplicate entries: {duplicates[:5]}")
    # Reuse the dedupe set we already paid for; the prior `set(names)`
    # at the return site discarded that work and walked the list a second
    # time. Same membership semantics, half the iteration cost on a
    # 50k-entry Chromium ZIP.
    return seen


def _check_exact(check: ZipCheck, names: set[str], required: tuple[str, ...]) -> None:
    for entry in required:
        if entry not in names:
            check.fail(f"missing required entry: {entry}")


def _check_prefixes(check: ZipCheck, names: set[str], required: tuple[str, ...]) -> None:
    for prefix in required:
        if not any(name.startswith(prefix) and name != prefix for name in names):
            check.fail(f"missing required prefix content: {prefix}")


def _check_no_pycache(check: ZipCheck, names: set[str]) -> None:
    pycache = sorted(name for name in names if "__pycache__" in name)
    if pycache:
        check.fail(f"zip contains __pycache__ entries: {pycache[:5]}")


def _check_windows_safe_paths(check: ZipCheck, names: set[str]) -> None:
    """Reject names that are valid in ZIPs but unsafe on Windows.

    Windows treats paths case-insensitively and reserves device names
    like CON/PRN/AUX/NUL even when an extension is present. Catch these
    before handing artifacts to the VM.
    """
    grouped = issues_by_kind(check_windows_safe_paths(names))
    if collisions := grouped.get("case-collision"):
        check.fail(f"zip contains Windows case-insensitive path collisions: {collisions[:5]}")
    if reserved := grouped.get("reserved-name"):
        check.fail(f"zip contains Windows reserved path components: {reserved[:5]}")
    absolute_or_parent = [
        *grouped.get("absolute-path", []),
        *grouped.get("parent-directory", []),
    ]
    if absolute_or_parent:
        check.fail(f"zip contains absolute or parent-directory paths: {absolute_or_parent[:5]}")
    if trailing := grouped.get("trailing-dot-space"):
        check.fail(f"zip contains Windows trailing-dot/space path components: {trailing[:5]}")


def _check_wheelhouse(check: ZipCheck, names: set[str], *, require_project: bool) -> None:
    wheels = sorted(name for name in names if name.startswith("wheelhouse/") and name.endswith(".whl"))
    check.details["wheel_count"] = len(wheels)
    if not wheels:
        check.fail("wheelhouse contains no wheels")
        return

    rejected = [
        wheel for wheel in wheels
        if not any(Path(wheel).name.endswith(suffix) for suffix in ACCEPTED_WHEEL_SUFFIXES)
    ]
    if rejected:
        check.fail(f"wheelhouse contains rejected wheel names: {rejected[:5]}")

    by_distribution: dict[str, list[str]] = {}
    for wheel in wheels:
        distribution = Path(wheel).name.split("-", 1)[0].lower().replace("_", "-")
        by_distribution.setdefault(distribution, []).append(wheel)
    duplicates = {
        distribution: values
        for distribution, values in by_distribution.items()
        if len(values) > 1
    }
    if duplicates:
        sample = {
            distribution: values[:5]
            for distribution, values in sorted(duplicates.items())[:5]
        }
        check.fail(f"wheelhouse contains duplicate distributions: {sample}")

    project_wheels = [wheel for wheel in wheels if Path(wheel).name.startswith("eidp-")]
    check.details["project_wheel_count"] = len(project_wheels)
    if require_project and not project_wheels:
        check.fail("wheelhouse missing project wheel eidp-*.whl")
    if require_project and len(project_wheels) > 1:
        check.fail(f"wheelhouse contains multiple project wheels: {project_wheels[:5]}")


def _read_zip_text(check: ZipCheck, member: str) -> str | None:
    if not zipfile.is_zipfile(check.path):
        return None
    with zipfile.ZipFile(check.path) as zf:
        try:
            raw = zf.read(member)
        except KeyError:
            return None
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        check.fail(f"{member} is not UTF-8 text: {exc}")
        return None


def _parser_keys_from_source(check: ZipCheck, source: str, member: str) -> set[str]:
    """Extract parser registry keys from the packaged source file.

    Do not import the local checkout here: the release question is whether
    the ZIP itself carries parser support for every official seed row.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        check.fail(f"{member} cannot be parsed for prefecture parser registry: {exc}")
        return set()

    for node in tree.body:
        value: ast.expr | None = None
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "PARSERS"
            for target in node.targets
        ):
            value = node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == "PARSERS":
            value = node.value
        if value is None:
            continue
        if not isinstance(value, ast.Dict):
            check.fail(f"{member} PARSERS must be a literal dict for ZIP verification")
            return set()
        keys: set[str] = set()
        for key_node in value.keys:
            if isinstance(key_node, ast.Constant) and isinstance(key_node.value, str):
                keys.add(key_node.value)
        return keys

    check.fail(f"{member} missing PARSERS registry")
    return set()


def _truthy_csv_value(value: str | None) -> bool:
    normalized = (value or "").strip().lower()
    return bool(normalized) and normalized not in {"no", "n/a", "unknown", "tbd", "false", "0"}


def _split_artifact_urls(raw: str | None) -> list[str]:
    return [
        part.strip()
        for part in (raw or "").replace("\n", "|").replace(";", "|").split("|")
        if part.strip()
    ]


def _check_prefecture_seed_contract(check: ZipCheck, names: set[str]) -> None:
    """Validate the official-prefecture bootstrap surface shipped in the ZIP.

    The product objective depends on starting from the 47 government/prefecture
    confirmation indexes. A ZIP can be structurally complete while silently
    shipping a partial seed or missing parser registration, so make that a
    release gate rather than a report-only observation.
    """
    seed_member = "data/prefecture-aggregators/seed.csv"
    parser_member = "src/eidp/scraper/prefecture_aggregator.py"
    if seed_member not in names or parser_member not in names:
        return

    seed_body = _read_zip_text(check, seed_member)
    parser_body = _read_zip_text(check, parser_member)
    if seed_body is None or parser_body is None:
        return

    records = list(csv.DictReader(seed_body.splitlines()))
    parser_keys = _parser_keys_from_source(check, parser_body, parser_member)
    if not records or not parser_keys:
        return

    pref_keys = [(record.get("pref_key") or "").strip() for record in records]
    pref_key_set = set(pref_keys)
    duplicates = sorted({pref for pref in pref_keys if pref and pref_keys.count(pref) > 1})
    if duplicates:
        check.fail(f"{seed_member} contains duplicate pref_key values: {duplicates}")

    missing_rows = sorted(EXPECTED_PREFECTURE_KEYS - pref_key_set)
    unexpected_rows = sorted(pref_key_set - EXPECTED_PREFECTURE_KEYS)
    if missing_rows or unexpected_rows or len(records) != len(EXPECTED_PREFECTURE_KEYS):
        check.fail(
            f"{seed_member} must contain exactly {len(EXPECTED_PREFECTURE_KEYS)} current prefecture rows; "
            f"missing={missing_rows} unexpected={unexpected_rows} actual={len(records)}"
        )

    unsupported = sorted(pref for pref in pref_key_set if pref and pref not in parser_keys)
    if unsupported:
        check.fail(f"{parser_member} PARSERS missing seed prefectures: {unsupported}")

    non_downloadable: list[str] = []
    missing_artifact_url: list[str] = []
    bad_artifact_format: list[str] = []
    with_school_link_signal = 0
    supplemental_rows = 0
    school_total = 0
    for record in records:
        pref = (record.get("pref_key") or "").strip()
        artifact_url = (record.get("artifact_url") or "").strip()
        status = (record.get("verified_status") or "").strip()
        artifact_format = (record.get("artifact_format") or "").strip().lower()
        if status not in DOWNLOADABLE_PREFECTURE_STATUSES:
            non_downloadable.append(f"{pref}:{status or '<blank>'}")
        if not artifact_url.startswith("http"):
            missing_artifact_url.append(pref or "<blank>")
        if artifact_format not in PREFECTURE_ARTIFACT_FORMATS:
            bad_artifact_format.append(f"{pref}:{artifact_format or '<blank>'}")
        if _truthy_csv_value(record.get("has_url_col")) or _truthy_csv_value(record.get("has_hyperlink_annot")):
            with_school_link_signal += 1
        if any(url.startswith("http") for url in _split_artifact_urls(record.get("supplemental_artifact_urls"))):
            supplemental_rows += 1
        raw_school_count = (record.get("schools_in_db") or "").strip()
        if raw_school_count and raw_school_count.lower() != "unknown":
            try:
                school_total += int(raw_school_count)
            except ValueError:
                check.warn(f"{seed_member} has non-integer schools_in_db for {pref}")

    if non_downloadable:
        check.fail(f"{seed_member} has non-downloadable prefecture statuses: {non_downloadable}")
    if missing_artifact_url:
        check.fail(f"{seed_member} has missing artifact URLs: {missing_artifact_url}")
    if bad_artifact_format:
        check.fail(f"{seed_member} has unsupported artifact formats: {bad_artifact_format}")

    check.details["prefecture_seed_rows"] = len(records)
    check.details["prefecture_seed_parser_supported"] = len(pref_key_set & parser_keys)
    check.details["prefecture_seed_downloadable"] = sum(
        1
        for record in records
        if (record.get("verified_status") or "").strip() in DOWNLOADABLE_PREFECTURE_STATUSES
        and (record.get("artifact_url") or "").strip().startswith("http")
    )
    check.details["prefecture_seed_school_rows_total"] = school_total
    check.details["prefecture_seed_with_school_link_signal"] = with_school_link_signal
    check.details["prefecture_seed_supplemental_rows"] = supplemental_rows


def _require_text(check: ZipCheck, body: str, member: str, needle: str) -> None:
    if needle not in body:
        check.fail(f"{member} missing required token: {needle}")


def _reject_text(check: ZipCheck, body: str, member: str, needle: str) -> None:
    if needle in body:
        check.fail(f"{member} contains forbidden token: {needle}")


def _reject_bare_rc_assignment(check: ZipCheck, body: str, member: str) -> None:
    """Catch stale launcher lines like ``"RC=-1"`` that cmd tries to execute."""
    for lineno, line in enumerate(body.splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith('"RC='):
            check.fail(f"{member} line {lineno} has bare RC assignment; use set \"RC=%ERRORLEVEL%\"")


def _check_bat_common(check: ZipCheck, member: str, body: str) -> None:
    _require_text(check, body, member, 'cd /d "%~dp0\\.."')
    _require_text(check, body, member, 'set "EIDP_APP_ROOT=%CD%"')
    _require_text(check, body, member, "PYTHONIOENCODING=utf-8")
    _require_text(check, body, member, "PYTHONUTF8=1")


def _check_bat_contracts(check: ZipCheck, names: set[str]) -> None:
    """Validate packaged .bat launchers, not just their filenames.

    Unit tests already pin the source files. This verifier catches a stale
    or hand-edited ZIP before it reaches the Windows VM gate.
    """
    required_tokens: dict[str, tuple[str, ...]] = {
        "EIDP-setup.bat": (
            'cd /d "%~dp0"',
            'call "%~dp0scripts\\first_setup.bat"',
            'set "RC=%ERRORLEVEL%"',
            "EIDP-start.bat",
            "pause",
            "endlocal & exit /b %RC%",
        ),
        "EIDP-start.bat": (
            'cd /d "%~dp0"',
            'call "%~dp0scripts\\launch.bat"',
            'set "RC=%ERRORLEVEL%"',
            "EIDP-setup.bat",
            "pause",
            "endlocal & exit /b %RC%",
        ),
        "EIDP-diagnose.bat": (
            'cd /d "%~dp0"',
            'call "%~dp0scripts\\diagnose.bat"',
            'set "RC=%ERRORLEVEL%"',
            "Diagnostics collected",
            "pause",
            "endlocal & exit /b %RC%",
        ),
        "scripts/first_setup.bat": (
            "runtime\\python\\python.exe",
            "runtime\\uv.exe",
            ".setup.lock",
            "SETUP_LOCK_STALE_HOURS=2",
            "Removed stale setup lock",
            "setup is already running in this folder",
            "endlocal & exit /b %SETUP_RC%",
            "PYTHONPATH=%EIDP_APP_ROOT%\\src",
            "uv.exe",
            "venv",
            ".venv\\Scripts\\python.exe",
            "--no-index",
            "--no-cache",
            "--reinstall-package eidp",
            "EIDP_WHEEL",
            "eidp-*.whl",
            "wheelhouse",
            "-m eidp.cli db-bootstrap --sqlite",
            "import-excel",
            "rebuild-school-year-tasks",
            "schtasks",
            "validate_install.bat",
            "--after-setup",
        ),
        "scripts/launch.bat": (
            ".venv\\Scripts\\python.exe",
            "PYTHONPATH=%EIDP_APP_ROOT%\\src",
            "Start-Process 'http://localhost:8501'",
            "streamlit run",
            "--server.headless true",
            "--browser.gatherUsageStats false",
            'set "RC=%ERRORLEVEL%"',
            "endlocal & exit /b %RC%",
        ),
        "scripts/weekly_run.bat": (
            ".venv\\Scripts\\python.exe",
            "PYTHONPATH=%EIDP_APP_ROOT%\\src",
            "Get-Date -Format yyyyMMdd",
            "run_weekly_target_year_discovery.py",
            'set "RC=%ERRORLEVEL%"',
            "endlocal & exit /b %RC%",
        ),
        "scripts/diagnose.bat": (
            ".venv\\Scripts\\python.exe",
            "runtime\\python\\python.exe",
            "diagnostics-%DIAG_STAMP%.txt",
            "validate_windows_install.py",
            "--after-setup",
            "BUILD_INFO.json",
            "last_run.json",
            "latest bootstrap progress",
            "latest bootstrap log tail",
            "endlocal & exit /b 0",
        ),
        "scripts/validate_install.bat": (
            ".venv\\Scripts\\python.exe",
            "runtime\\python\\python.exe",
            "validate_windows_install.py",
            '"%EIDP_APP_ROOT%" %*',
            'set "RC=%ERRORLEVEL%"',
            "endlocal & exit /b %RC%",
        ),
        "scripts/uninstall.bat": (
            "schtasks /Delete",
            "EIDP Weekly Run",
            "data\\",
        ),
    }
    forbidden_tokens: dict[str, tuple[str, ...]] = {
        "scripts/first_setup.bat": ("import-master",),
        "scripts/weekly_run.bat": ("%date:~",),
        "scripts/uninstall.bat": ("rmdir", "del ", "erase ", "rd "),
    }

    for member, tokens in required_tokens.items():
        if member not in names:
            continue
        body = _read_zip_text(check, member)
        if body is None:
            continue
        _reject_bare_rc_assignment(check, body, member)
        if member.startswith("scripts/") and member != "scripts/uninstall.bat":
            _check_bat_common(check, member, body)
        for token in tokens:
            _require_text(check, body, member, token)
        lowered = body.lower()
        for token in forbidden_tokens.get(member, ()):
            _reject_text(check, lowered, member, token)


def _check_python_entrypoint_contracts(check: ZipCheck, names: set[str]) -> None:
    """Validate packaged Python helper scripts that the VM gate relies on."""
    required_tokens: dict[str, tuple[str, ...]] = {
        "scripts/validate_windows_install.py": (
            "CORE_FILES",
            "build_commit",
            "scripts/validate_install.bat",
            "--after-setup",
            "--after-weekly",
            "--require-ocr-addon",
            "--require-playwright-addon",
            "last_run.json status must be success",
        ),
        "scripts/run_weekly_target_year_discovery.py": (
            "acquire_lock",
            "last_run.json",
            "write_last_run",
            "prune_run_logs",
            "run_pdf_discovery",
            "run_ingestion",
        ),
        "scripts/bootstrap_pdf_pipeline.py": (
            "Step 2b",
            "known URL / corporation fallback discovery",
            "discovered-urls-50.csv",
            "prefecture_aggregator,seed_csv,corporation_pattern,scrapling_stealth",
            "progress_callback",
        ),
    }
    forbidden_tokens: dict[str, tuple[str, ...]] = {
        "scripts/run_weekly_target_year_discovery.py": ("export_excel",),
    }

    for member, tokens in required_tokens.items():
        if member not in names:
            continue
        body = _read_zip_text(check, member)
        if body is None:
            continue
        for token in tokens:
            _require_text(check, body, member, token)
        for token in forbidden_tokens.get(member, ()):
            _reject_text(check, body, member, token)


def _check_operator_runbook_contract(check: ZipCheck, names: set[str]) -> None:
    """Catch stale operator-facing instructions in the packaged runbook.

    The Windows ZIP can pass structural checks while still shipping old
    navigation guidance. That is a release blocker because the target user
    launches from the runbook, not from the source tree.
    """
    member = "docs/runbooks/eidp-windows.md"
    if member not in names:
        return
    body = _read_zip_text(check, member)
    if body is None:
        return
    for token in (
        "業務員クイック",
        "学校別タスク",
        "実行中のパッケージ",
        "詳細 operator",
        "週次URL/PDF再取得",
        "対象年度を変更して保存すると、学校別タスクも同時に再計算されます",
        "scripts\\weekly_run.bat` は管理者向けの復旧入口",
    ):
        _require_text(check, body, member, token)
    for token in (
        "画面左のサイドバーに 12 ページ",
    ):
        _reject_text(check, body, member, token)


def _check_build_info(check: ZipCheck, names: set[str]) -> None:
    if "BUILD_INFO.json" not in names:
        return
    if not zipfile.is_zipfile(check.path):
        return
    with zipfile.ZipFile(check.path) as zf:
        try:
            payload = json.loads(zf.read("BUILD_INFO.json").decode("utf-8"))
        except (KeyError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            check.fail(f"BUILD_INFO.json is not valid JSON: {exc}")
            return
    if not isinstance(payload, dict):
        check.fail("BUILD_INFO.json must contain an object")
        return
    for key in ("app", "built_at_utc", "git_commit", "git_branch", "git_dirty"):
        value = payload.get(key)
        if not isinstance(value, str) or not value:
            check.fail(f"BUILD_INFO.json missing string field: {key}")
    if payload.get("app") != "EIDP":
        check.fail("BUILD_INFO.json app must be EIDP")
    commit = payload.get("git_commit")
    if isinstance(commit, str) and commit != "unknown" and len(commit) != 40:
        check.fail("BUILD_INFO.json git_commit must be a full 40-character commit hash or unknown")
    check.details["build_info"] = payload


def _read_manifest(check: ZipCheck, member: str) -> dict[str, Any] | None:
    if not zipfile.is_zipfile(check.path):
        return None
    with zipfile.ZipFile(check.path) as zf:
        try:
            raw = zf.read(member)
        except KeyError:
            return None
    try:
        manifest = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        check.fail(f"manifest is not valid UTF-8 JSON: {member}: {exc}")
        return None
    if not isinstance(manifest, dict):
        check.fail(f"manifest is not a JSON object: {member}")
        return None
    return manifest


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _manifest_file_entries(check: ZipCheck, manifest: dict[str, Any], *, manifest_path: str) -> list[dict[str, Any]]:
    files = manifest.get("files")
    if not isinstance(files, list):
        check.fail(f"{manifest_path} missing files list")
        return []
    entries: list[dict[str, Any]] = []
    seen_paths: set[str] = set()
    for index, entry in enumerate(files):
        if not isinstance(entry, dict):
            check.fail(f"{manifest_path} files[{index}] is not an object")
            continue
        path = entry.get("path")
        size = entry.get("size")
        sha256 = entry.get("sha256")
        if not isinstance(path, str) or not path:
            check.fail(f"{manifest_path} files[{index}] missing path")
            continue
        if path in seen_paths:
            check.fail(f"{manifest_path} contains duplicate file path: {path}")
        seen_paths.add(path)
        if not isinstance(size, int) or size < 0:
            check.fail(f"{manifest_path} file has invalid size: {path}")
        if not isinstance(sha256, str) or len(sha256) != 64:
            check.fail(f"{manifest_path} file has invalid sha256: {path}")
        entries.append(entry)
    return entries


def _check_manifest_integrity(
    check: ZipCheck,
    names: set[str],
    *,
    manifest_path: str,
    required_paths: tuple[str, ...],
) -> None:
    """Validate add-on MANIFEST.json against actual ZIP member bytes."""
    manifest = _read_manifest(check, manifest_path)
    if manifest is None:
        return

    entries = _manifest_file_entries(check, manifest, manifest_path=manifest_path)
    by_path = {entry["path"]: entry for entry in entries if isinstance(entry.get("path"), str)}

    for required in required_paths:
        if required not in by_path:
            check.fail(f"manifest missing required file path: {required}")

    zip_payload_names = sorted(name for name in names if name != manifest_path and not name.endswith("/"))
    missing_from_manifest = [name for name in zip_payload_names if name not in by_path]
    if missing_from_manifest:
        check.fail(f"manifest missing ZIP payload entries: {missing_from_manifest[:5]}")

    manifest_only = sorted(path for path in by_path if path not in names)
    if manifest_only:
        check.fail(f"manifest references missing ZIP entries: {manifest_only[:5]}")

    with zipfile.ZipFile(check.path) as zf:
        for path, entry in sorted(by_path.items()):
            if path not in names:
                continue
            payload = zf.read(path)
            expected_size = entry.get("size")
            expected_sha = entry.get("sha256")
            if isinstance(expected_size, int) and len(payload) != expected_size:
                check.fail(
                    f"manifest size mismatch for {path}: "
                    f"expected={expected_size} actual={len(payload)}"
                )
            if isinstance(expected_sha, str) and len(expected_sha) == 64:
                actual_sha = _sha256_bytes(payload)
                if actual_sha != expected_sha:
                    check.fail(
                        f"manifest sha256 mismatch for {path}: "
                        f"expected={expected_sha} actual={actual_sha}"
                    )

    check.details["manifest_files"] = len(entries)


def verify_core_zip(path: Path) -> ZipCheck:
    check = ZipCheck(name="core", path=path)
    names = _read_zip_names(check)
    if names is None:
        return check

    _check_exact(check, names, CORE_REQUIRED_EXACT)
    _check_prefixes(check, names, CORE_REQUIRED_PREFIXES)
    _check_no_pycache(check, names)
    _check_windows_safe_paths(check, names)
    _check_wheelhouse(check, names, require_project=True)
    _check_bat_contracts(check, names)
    _check_python_entrypoint_contracts(check, names)
    _check_operator_runbook_contract(check, names)
    _check_prefecture_seed_contract(check, names)
    _check_build_info(check, names)

    check.details["entry_count"] = len(names)
    check.details["has_runtime"] = (
        "runtime/python/python.exe" in names and "runtime/uv.exe" in names
    )
    return check


def verify_ocr_addon_zip(path: Path) -> ZipCheck:
    check = ZipCheck(name="ocr-addon", path=path)
    names = _read_zip_names(check)
    if names is None:
        return check

    _check_exact(check, names, OCR_REQUIRED_EXACT)
    _check_no_pycache(check, names)
    _check_windows_safe_paths(check, names)
    _check_manifest_integrity(
        check,
        names,
        manifest_path="ocr-addon/MANIFEST.json",
        required_paths=OCR_REQUIRED_EXACT[:-1],
    )

    check.details["entry_count"] = len(names)
    return check


def verify_playwright_addon_zip(path: Path) -> ZipCheck:
    check = ZipCheck(name="playwright-addon", path=path)
    names = _read_zip_names(check)
    if names is None:
        return check

    _check_exact(check, names, PLAYWRIGHT_REQUIRED_EXACT)
    _check_prefixes(check, names, PLAYWRIGHT_REQUIRED_PREFIXES)
    _check_no_pycache(check, names)
    _check_windows_safe_paths(check, names)

    if not any(name.startswith("playwright-addon/ms-playwright/") and name.endswith("chrome.exe") for name in names):
        check.fail("playwright add-on missing Chromium chrome.exe")
    if not any(
        name.startswith("playwright-addon/wheelhouse/")
        and Path(name).name.startswith("playwright-")
        and name.endswith(".whl")
        for name in names
    ):
        check.fail("playwright add-on missing playwright-*.whl")
    if not any(
        name.startswith("playwright-addon/wheelhouse/")
        and Path(name).name.startswith("scrapling-")
        and name.endswith(".whl")
        for name in names
    ):
        check.fail("playwright add-on missing scrapling-*.whl")

    _check_manifest_integrity(
        check,
        names,
        manifest_path="playwright-addon/MANIFEST.json",
        required_paths=(),
    )

    check.details["entry_count"] = len(names)
    return check


def render_text(checks: list[ZipCheck]) -> str:
    lines: list[str] = []
    for check in checks:
        state = "OK" if check.ok else "FAIL"
        lines.append(f"{state} {check.name}: {check.path}")
        for key, value in sorted(check.details.items()):
            lines.append(f"  {key}: {value}")
        for warning in check.warnings:
            lines.append(f"  warning: {warning}")
        for error in check.errors:
            lines.append(f"  error: {error}")
    return "\n".join(lines)


def checks_to_json(checks: list[ZipCheck]) -> str:
    payload = [
        {
            "name": check.name,
            "path": str(check.path),
            "ok": check.ok,
            "errors": check.errors,
            "warnings": check.warnings,
            "details": check.details,
        }
        for check in checks
    ]
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify EIDP Windows distribution ZIPs.")
    parser.add_argument("core_zip", type=Path, help="Path to eidp-windows.zip")
    parser.add_argument("--ocr-addon", type=Path, default=None)
    parser.add_argument("--playwright-addon", type=Path, default=None)
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    args = parser.parse_args(argv)

    checks = [verify_core_zip(args.core_zip)]
    if args.ocr_addon is not None:
        checks.append(verify_ocr_addon_zip(args.ocr_addon))
    if args.playwright_addon is not None:
        checks.append(verify_playwright_addon_zip(args.playwright_addon))

    print(checks_to_json(checks) if args.json else render_text(checks))
    return 0 if all(check.ok for check in checks) else 1


if __name__ == "__main__":
    sys.exit(main())
