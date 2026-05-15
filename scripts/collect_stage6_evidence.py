"""Build a read-only Stage 6 evidence bundle for operator-PC handoff.

The bundle intentionally includes logs and operational evidence only. It excludes
the SQLite database, WAL/SHM sidecars, downloaded PDFs, Excel exports, runtime
files, and wheelhouse contents so the operator can share one small ZIP without
copying live application state or personal data.
"""

from __future__ import annotations

import argparse
import json
import sys
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class EvidencePattern:
    label: str
    glob: str
    limit: int


BASE_EVIDENCE_PATTERNS: tuple[EvidencePattern, ...] = (
    EvidencePattern("build_info", "BUILD_INFO.json", 1),
    EvidencePattern("diagnostics", "logs/diagnostics-*.txt", 5),
    EvidencePattern("stage6_recovery", "logs/stage6-recovery-*.json", 5),
    EvidencePattern("stage6_residual_cleanup", "logs/stage6-residual-cleanup-*.json", 5),
    EvidencePattern("weekly_run_logs", "logs/run-*.log", 5),
    EvidencePattern("bootstrap_progress", "logs/bootstrap-pdfs-*.json", 5),
    EvidencePattern("bootstrap_logs", "logs/bootstrap-pdfs-*.log", 3),
    EvidencePattern("last_run", "data/output/last_run.json", 1),
    EvidencePattern("discovery_evidence", "data/output/target-year-discovery/*-discovery-rejections.jsonl", 5),
    EvidencePattern("discovery_rca", "data/output/target-year-discovery/*-discovery-rca-batch-plan.json", 5),
)
EXCEL_EVIDENCE_PATTERN = EvidencePattern("excel_exports", "data/output/**/*.xlsx", 5)

EXCLUDED_TOP_LEVEL_PARTS = {
    ".venv",
    "runtime",
    "wheelhouse",
}
EXCLUDED_DATA_PARTS = {
    "eidp.sqlite3",
    "eidp.sqlite3-shm",
    "eidp.sqlite3-wal",
    "pdfs",
}


def _relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _is_excluded(path: Path, root: Path) -> bool:
    rel_parts = path.relative_to(root).parts
    if not rel_parts:
        return True
    if rel_parts[0] in EXCLUDED_TOP_LEVEL_PARTS:
        return True
    if rel_parts[0] == "data" and len(rel_parts) > 1 and rel_parts[1] in EXCLUDED_DATA_PARTS:
        return True
    return False


def _latest_matches(root: Path, pattern: EvidencePattern) -> list[Path]:
    matches = [path for path in root.glob(pattern.glob) if path.is_file() and not _is_excluded(path, root)]
    matches.sort(key=lambda path: (path.stat().st_mtime, _relative(path, root)), reverse=True)
    return matches[: pattern.limit]


def build_evidence_bundle(root: Path, out_path: Path | None = None, *, include_excel: bool = False) -> dict[str, Any]:
    root = root.resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"app root does not exist: {root}")

    logs_dir = root / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    archive_path = out_path or logs_dir / f"stage6-evidence-{stamp}.zip"
    archive_path = archive_path.resolve()
    archive_path.parent.mkdir(parents=True, exist_ok=True)

    included: list[dict[str, Any]] = []
    missing_patterns: list[str] = []
    seen: set[Path] = set()

    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        patterns = (*BASE_EVIDENCE_PATTERNS, EXCEL_EVIDENCE_PATTERN) if include_excel else BASE_EVIDENCE_PATTERNS
        for pattern in patterns:
            matches = _latest_matches(root, pattern)
            if not matches:
                missing_patterns.append(pattern.label)
                continue
            for path in matches:
                resolved = path.resolve()
                if resolved in seen or resolved == archive_path:
                    continue
                seen.add(resolved)
                arcname = _relative(path, root)
                zf.write(path, arcname)
                included.append(
                    {
                        "label": pattern.label,
                        "path": arcname,
                        "size": path.stat().st_size,
                    }
                )

        manifest = {
            "generated_at_utc": datetime.now(UTC).isoformat(),
            "app_root": str(root),
            "archive": str(archive_path),
            "included": included,
            "missing_patterns": missing_patterns,
            "excluded": {
                "top_level": sorted(EXCLUDED_TOP_LEVEL_PARTS),
                "data": sorted(EXCLUDED_DATA_PARTS),
                "excel_exports": not include_excel,
            },
        }
        zf.writestr("stage6-evidence-manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))

    return {
        "ok": True,
        "archive": str(archive_path),
        "included_count": len(included),
        "missing_patterns": missing_patterns,
    }


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", default=".", help="Extracted EIDP app root.")
    parser.add_argument("--out", help="Output ZIP path. Defaults to logs/stage6-evidence-<timestamp>.zip.")
    parser.add_argument(
        "--include-excel",
        action="store_true",
        help="Include data/output/**/*.xlsx. Use only for internal handoff; Excel exports may contain personal data.",
    )
    parser.add_argument("--json", action="store_true", help="Emit compact JSON.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    result = build_evidence_bundle(
        Path(args.root),
        out_path=Path(args.out) if args.out else None,
        include_excel=args.include_excel,
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
