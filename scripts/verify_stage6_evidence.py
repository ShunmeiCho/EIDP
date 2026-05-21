"""Verify a Stage 6 evidence ZIP before treating it as release evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path
from typing import Any

DEFAULT_REQUIRED_LABELS = ("build_info", "diagnostics")

FORBIDDEN_EXACT_ENTRIES = {
    "data/eidp.sqlite3",
    "data/eidp.sqlite3-shm",
    "data/eidp.sqlite3-wal",
}
FORBIDDEN_PREFIXES = (
    ".venv/",
    "runtime/",
    "wheelhouse/",
    "data/pdfs/",
)
EXCEL_EXPORT_PREFIX = "data/output/"


def _is_unsafe_name(name: str) -> bool:
    normalized = name.replace("\\", "/")
    parts = [part for part in normalized.split("/") if part]
    return (
        name.startswith("/")
        or "\\" in name
        or any(part == ".." for part in parts)
        or normalized.startswith("../")
    )


def _is_forbidden_entry(name: str) -> bool:
    normalized = name.replace("\\", "/")
    return normalized in FORBIDDEN_EXACT_ENTRIES or any(
        normalized == prefix.rstrip("/") or normalized.startswith(prefix) for prefix in FORBIDDEN_PREFIXES
    )


def _is_excel_export(name: str) -> bool:
    normalized = name.replace("\\", "/")
    return normalized.startswith(EXCEL_EXPORT_PREFIX) and normalized.lower().endswith(".xlsx")


def _load_manifest(zf: zipfile.ZipFile, errors: list[str]) -> dict[str, Any] | None:
    try:
        raw = zf.read("stage6-evidence-manifest.json")
    except KeyError:
        errors.append("missing stage6-evidence-manifest.json")
        return None
    try:
        manifest = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        errors.append(f"invalid stage6-evidence-manifest.json: {exc}")
        return None
    if not isinstance(manifest, dict):
        errors.append("stage6-evidence-manifest.json must contain a JSON object")
        return None
    return manifest


def _manifest_included_paths(manifest: dict[str, Any], errors: list[str]) -> tuple[set[str], set[str]]:
    included = manifest.get("included")
    if not isinstance(included, list):
        errors.append("manifest included must be a list")
        return set(), set()

    labels: set[str] = set()
    paths: set[str] = set()
    for index, item in enumerate(included):
        if not isinstance(item, dict):
            errors.append(f"manifest included[{index}] must be an object")
            continue
        label = item.get("label")
        path = item.get("path")
        if not isinstance(label, str) or not label:
            errors.append(f"manifest included[{index}].label must be a non-empty string")
        else:
            labels.add(label)
        if not isinstance(path, str) or not path:
            errors.append(f"manifest included[{index}].path must be a non-empty string")
        else:
            paths.add(path.replace("\\", "/"))
    return labels, paths


def _check_manifest_entry_hashes(
    zf: zipfile.ZipFile,
    manifest: dict[str, Any],
    errors: list[str],
) -> None:
    included = manifest.get("included")
    if not isinstance(included, list):
        return
    for index, item in enumerate(included):
        if not isinstance(item, dict):
            continue
        path = item.get("path")
        expected_sha = item.get("sha256")
        if not isinstance(path, str) or not isinstance(expected_sha, str):
            continue
        normalized_path = path.replace("\\", "/")
        try:
            raw = zf.read(normalized_path)
        except KeyError:
            continue
        actual_sha = hashlib.sha256(raw).hexdigest()
        if actual_sha != expected_sha:
            errors.append(f"manifest included[{index}].sha256 mismatch for {normalized_path}")


def verify_stage6_evidence_bundle(
    archive: Path,
    *,
    required_labels: tuple[str, ...] = DEFAULT_REQUIRED_LABELS,
    allow_excel: bool = False,
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    archive = archive.resolve()

    if not archive.is_file():
        return {
            "ok": False,
            "archive": str(archive),
            "entry_count": 0,
            "required_labels": list(required_labels),
            "present_labels": [],
            "missing_required_labels": list(required_labels),
            "manifest_missing_patterns": [],
            "forbidden_entries": [],
            "errors": [f"archive does not exist: {archive}"],
            "warnings": [],
        }

    try:
        with zipfile.ZipFile(archive) as zf:
            names = zf.namelist()
            normalized_names = {name.replace("\\", "/") for name in names}
            forbidden_runtime_entries = sorted(name for name in normalized_names if _is_forbidden_entry(name))
            forbidden_excel_entries = sorted(
                name for name in normalized_names if not allow_excel and _is_excel_export(name)
            )
            forbidden_entries = [*forbidden_runtime_entries, *forbidden_excel_entries]
            unsafe_names = sorted(name for name in names if _is_unsafe_name(name))

            if forbidden_runtime_entries:
                errors.append("archive contains forbidden runtime data")
            if forbidden_excel_entries:
                errors.append("archive contains forbidden Excel exports")
            if unsafe_names:
                errors.append("archive contains unsafe entry names")

            manifest = _load_manifest(zf, errors)
            present_labels: set[str] = set()
            manifest_paths: set[str] = set()
            manifest_missing_patterns: list[str] = []
            if manifest is not None:
                present_labels, manifest_paths = _manifest_included_paths(manifest, errors)
                missing = manifest.get("missing_patterns", [])
                if isinstance(missing, list) and all(isinstance(item, str) for item in missing):
                    manifest_missing_patterns = sorted(missing)
                else:
                    errors.append("manifest missing_patterns must be a list of strings")

                missing_manifest_paths = sorted(path for path in manifest_paths if path not in normalized_names)
                if missing_manifest_paths:
                    errors.append("manifest references files that are not in the archive")
                    warnings.extend(f"missing manifest path: {path}" for path in missing_manifest_paths)
                _check_manifest_entry_hashes(zf, manifest, errors)

            missing_required_labels = sorted(label for label in required_labels if label not in present_labels)
            if missing_required_labels:
                errors.append("archive is missing required evidence labels")

            return {
                "ok": not errors,
                "archive": str(archive),
                "entry_count": len(names),
                "required_labels": list(required_labels),
                "present_labels": sorted(present_labels),
                "missing_required_labels": missing_required_labels,
                "manifest_missing_patterns": manifest_missing_patterns,
                "forbidden_entries": forbidden_entries,
                "unsafe_entries": unsafe_names,
                "errors": errors,
                "warnings": warnings,
            }
    except zipfile.BadZipFile as exc:
        return {
            "ok": False,
            "archive": str(archive),
            "entry_count": 0,
            "required_labels": list(required_labels),
            "present_labels": [],
            "missing_required_labels": list(required_labels),
            "manifest_missing_patterns": [],
            "forbidden_entries": [],
            "errors": [f"invalid zip file: {exc}"],
            "warnings": [],
        }


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", help="Path to logs/stage6-evidence-*.zip.")
    parser.add_argument(
        "--require-label",
        action="append",
        default=[],
        help="Manifest evidence label that must be present. Defaults to build_info and diagnostics.",
    )
    parser.add_argument(
        "--allow-excel",
        action="store_true",
        help="Allow data/output/**/*.xlsx in the evidence ZIP. Use only for internal handoff.",
    )
    parser.add_argument("--json", action="store_true", help="Emit compact JSON.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    required = tuple(dict.fromkeys((*DEFAULT_REQUIRED_LABELS, *args.require_label)))
    result = verify_stage6_evidence_bundle(Path(args.archive), required_labels=required, allow_excel=args.allow_excel)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
