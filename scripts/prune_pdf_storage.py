"""Prune generated PDF storage under data/pdfs after reviewing candidates.

Dry-run by default. The safe default only targets PDF files that are not
referenced by the SQLite ``document.file_path`` table. Referenced historical
PDFs are listed only when ``--include-obsolete-referenced`` is passed.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

DEFAULT_PDF_ROOT = Path("data") / "pdfs"
DEFAULT_SQLITE_PATH = Path("data") / "eidp.sqlite3"


@dataclass(frozen=True)
class PdfCandidate:
    path: str
    reason: str
    bytes: int
    document_id: int | None = None
    fiscal_year: int | None = None


@dataclass(frozen=True)
class DocumentPdfRef:
    document_id: int
    path: Path
    fiscal_year: int | None
    fiscal_year_override: int | None
    is_current_year: bool | None

    @property
    def effective_fiscal_year(self) -> int | None:
        return self.fiscal_year_override if self.fiscal_year_override is not None else self.fiscal_year


def _relative(path: Path, base: Path) -> str:
    try:
        return path.resolve().relative_to(base.resolve()).as_posix()
    except ValueError:
        return str(path)


def _is_under(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def _resolve_stored_path(raw: str, app_root: Path) -> Path:
    path = Path(raw)
    return path.resolve() if path.is_absolute() else (app_root / path).resolve()


def load_document_pdf_refs(sqlite_path: Path, app_root: Path) -> list[DocumentPdfRef]:
    if not sqlite_path.exists():
        return []
    with sqlite3.connect(sqlite_path) as conn:
        rows = conn.execute(
            """
            SELECT id, file_path, fiscal_year, fiscal_year_override, is_current_year
            FROM document
            WHERE file_path IS NOT NULL AND file_path != ''
            """
        ).fetchall()
    refs: list[DocumentPdfRef] = []
    for doc_id, raw_path, fiscal_year, fiscal_year_override, is_current_year in rows:
        refs.append(
            DocumentPdfRef(
                document_id=int(doc_id),
                path=_resolve_stored_path(str(raw_path), app_root),
                fiscal_year=fiscal_year,
                fiscal_year_override=fiscal_year_override,
                is_current_year=bool(is_current_year) if is_current_year is not None else None,
            )
        )
    return refs


def _kept_by_retention(ref: DocumentPdfRef, keep_from_fiscal_year: int | None) -> bool:
    if ref.is_current_year:
        return True
    effective_fy = ref.effective_fiscal_year
    return keep_from_fiscal_year is not None and effective_fy is not None and effective_fy >= keep_from_fiscal_year


def collect_candidates(
    *,
    app_root: Path,
    pdf_root: Path = DEFAULT_PDF_ROOT,
    sqlite_path: Path = DEFAULT_SQLITE_PATH,
    keep_from_fiscal_year: int | None = None,
    include_obsolete_referenced: bool = False,
) -> list[PdfCandidate]:
    root = app_root.resolve()
    resolved_pdf_root = (root / pdf_root).resolve() if not pdf_root.is_absolute() else pdf_root.resolve()
    resolved_sqlite = (root / sqlite_path).resolve() if not sqlite_path.is_absolute() else sqlite_path.resolve()
    if resolved_pdf_root.is_symlink() or not _is_under(resolved_pdf_root, root):
        return []
    if not resolved_pdf_root.is_dir():
        return []

    refs = load_document_pdf_refs(resolved_sqlite, root)
    refs_by_path: dict[Path, list[DocumentPdfRef]] = {}
    for ref in refs:
        refs_by_path.setdefault(ref.path.resolve(), []).append(ref)

    candidates: list[PdfCandidate] = []
    for path in sorted(resolved_pdf_root.rglob("*.pdf")):
        if path.is_symlink() or not path.is_file() or not _is_under(path, resolved_pdf_root):
            continue
        size = path.stat().st_size
        path_refs = refs_by_path.get(path.resolve(), [])
        if not path_refs:
            candidates.append(
                PdfCandidate(
                    path=_relative(path, root),
                    reason="unreferenced PDF under data/pdfs",
                    bytes=size,
                )
            )
            continue
        if not include_obsolete_referenced:
            continue
        kept_refs = [ref for ref in path_refs if _kept_by_retention(ref, keep_from_fiscal_year)]
        if kept_refs:
            continue
        newest_ref = max(path_refs, key=lambda ref: (ref.effective_fiscal_year or -1, ref.document_id))
        candidates.append(
            PdfCandidate(
                path=_relative(path, root),
                reason=f"referenced only by obsolete documents before fiscal year {keep_from_fiscal_year}",
                bytes=size,
                document_id=newest_ref.document_id,
                fiscal_year=newest_ref.effective_fiscal_year,
            )
        )
    return candidates


def apply_cleanup(app_root: Path, candidates: list[PdfCandidate]) -> list[dict[str, Any]]:
    root = app_root.resolve()
    pdf_root = (root / DEFAULT_PDF_ROOT).resolve()
    actions: list[dict[str, Any]] = []
    for candidate in candidates:
        path = (root / candidate.path).resolve()
        action: dict[str, Any] = {**asdict(candidate), "deleted": False, "error": None}
        if path.is_symlink():
            action["error"] = "refusing symlink"
        elif not _is_under(path, pdf_root):
            action["error"] = "refusing path outside data/pdfs"
        elif path.is_file():
            try:
                path.unlink()
                action["deleted"] = True
            except OSError as exc:
                action["error"] = str(exc)
        elif path.exists():
            action["error"] = "candidate is not a file"
        actions.append(action)
    return actions


def summarize(candidates: list[PdfCandidate], actions: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {
        "ok": actions is None or all(action.get("error") is None for action in actions),
        "candidate_count": len(candidates),
        "candidate_bytes": sum(candidate.bytes for candidate in candidates),
        "deleted_count": sum(1 for action in actions or [] if action.get("deleted")),
        "deleted_bytes": sum(int(action["bytes"]) for action in actions or [] if action.get("deleted")),
        "candidates": [asdict(candidate) for candidate in candidates],
        "actions": actions or [],
    }


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app-root", type=Path, default=Path.cwd())
    parser.add_argument("--pdf-root", type=Path, default=DEFAULT_PDF_ROOT)
    parser.add_argument("--sqlite-path", type=Path, default=DEFAULT_SQLITE_PATH)
    parser.add_argument("--keep-from-fiscal-year", type=int, default=None)
    parser.add_argument(
        "--include-obsolete-referenced",
        action="store_true",
        help="Also list/delete referenced PDFs older than the fiscal-year retention boundary.",
    )
    parser.add_argument("--apply", action="store_true", help="Delete candidates. Default is dry-run.")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    candidates = collect_candidates(
        app_root=args.app_root,
        pdf_root=args.pdf_root,
        sqlite_path=args.sqlite_path,
        keep_from_fiscal_year=args.keep_from_fiscal_year,
        include_obsolete_referenced=args.include_obsolete_referenced,
    )
    actions = apply_cleanup(args.app_root, candidates) if args.apply else None
    summary = summarize(candidates, actions)
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    else:
        mode = "deleted" if args.apply else "would delete"
        mib = summary["candidate_bytes"] / 1024 / 1024
        print(f"{mode} {summary['candidate_count']} PDF(s), {mib:.1f} MiB candidate data")
        for candidate in candidates:
            print(f"- {candidate.path} ({candidate.reason})")
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
