"""Build operator-review school-alias proposals from PDF school-name mismatches.

This script is intentionally read-only with respect to the database. It turns
``pdf_school_mismatch`` discovery evidence into the same proposal JSONL shape
that the existing operator UI already knows how to review. Approval still goes
through ``apply_school_alias_proposal`` and writes ``ManualActionLog``.

Usage:
    uv run python scripts/pdf_school_mismatch_alias_proposals.py \
        --rejections output/target-year-discovery/latest-discovery-rejections.jsonl
"""

from __future__ import annotations

import argparse
import json
import unicodedata
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy.exc import SQLAlchemyError

from eidp.db.models import School, SchoolAlias
from eidp.db.session import SessionLocal
from eidp.scraper.pdf_discovery import _school_link_label

_LOW_RISK_SCHOOL_NAME_EXPANSION_SUFFIXES = frozenset({"it", "aiit", "ict", "dx"})


@dataclass
class PdfSchoolMismatchAliasProposal:
    template_name: str
    template_rows: int
    proposal_type: str
    matched_school_id: int | None = None
    matched_school_name: str | None = None
    matched_corporation: str | None = None
    candidates: list[dict[str, object]] = field(default_factory=list)
    reasoning: str = ""
    source: str = "pdf_school_mismatch_alias_proposals"
    evidence: list[dict[str, object]] = field(default_factory=list)


def _norm(value: str | None) -> str:
    normalized = unicodedata.normalize("NFKC", value or "")
    return "".join(normalized.split())


def _payload_extra(row: dict[str, Any]) -> dict[str, Any]:
    extra = row.get("extra") or row.get("detail") or {}
    return extra if isinstance(extra, dict) else {}


def _is_low_risk_alias_expansion(parsed_name: str, target_name: str) -> tuple[bool, str]:
    parsed_label = _school_link_label(parsed_name)
    target_label = _school_link_label(target_name)
    if not parsed_label or not target_label:
        return False, "missing normalized label"
    if parsed_label == target_label:
        return True, "same normalized school label"

    for base, expanded in ((target_label, parsed_label), (parsed_label, target_label)):
        if len(base) < 4 or not expanded.startswith(base):
            continue
        suffix = expanded[len(base):]
        if suffix in _LOW_RISK_SCHOOL_NAME_EXPANSION_SUFFIXES:
            return True, f"low-risk school-name expansion suffix: {suffix}"

    return False, f"not a low-risk school-name expansion: {target_label!r} vs {parsed_label!r}"


def build_proposals(
    rejection_rows: list[dict[str, Any]],
    schools: list[School],
    aliases: list[SchoolAlias],
) -> tuple[list[PdfSchoolMismatchAliasProposal], dict[str, int]]:
    schools_by_id = {int(s.id): s for s in schools}
    school_label_to_ids: dict[str, set[int]] = {}
    for school in schools:
        label = _school_link_label(school.school_name)
        if label:
            school_label_to_ids.setdefault(label, set()).add(int(school.id))

    alias_owner_by_name: dict[str, int] = {}
    for alias in aliases:
        alias_name = _norm(alias.alias_name)
        if alias_name:
            alias_owner_by_name[alias_name] = int(alias.school_id)

    grouped: dict[tuple[int, str], dict[str, Any]] = {}
    stats = {
        "input_rows": 0,
        "pdf_school_mismatch_rows": 0,
        "missing_detail": 0,
        "missing_school": 0,
        "unsafe_expansion": 0,
        "conflict_existing_school": 0,
        "conflict_existing_alias": 0,
        "already_has_alias": 0,
        "proposals": 0,
    }

    for row in rejection_rows:
        stats["input_rows"] += 1
        if row.get("reason") != "pdf_school_mismatch":
            continue
        stats["pdf_school_mismatch_rows"] += 1
        school_id_raw = row.get("school_id")
        extra = _payload_extra(row)
        parsed_name = str(extra.get("parsed_school_name") or "").strip()
        target_name = str(extra.get("target_school_name") or "").strip()
        if school_id_raw is None or not parsed_name or not target_name:
            stats["missing_detail"] += 1
            continue

        school_id = int(school_id_raw)
        school = schools_by_id.get(school_id)
        if school is None:
            stats["missing_school"] += 1
            continue

        ok, reason = _is_low_risk_alias_expansion(parsed_name, target_name)
        if not ok:
            stats["unsafe_expansion"] += 1
            continue

        parsed_label = _school_link_label(parsed_name)
        conflicting_school_ids = school_label_to_ids.get(parsed_label, set()) - {school_id}
        if conflicting_school_ids:
            stats["conflict_existing_school"] += 1
            continue

        alias_key = _norm(parsed_name)
        existing_alias_owner = alias_owner_by_name.get(alias_key)
        if existing_alias_owner == school_id:
            stats["already_has_alias"] += 1
            continue
        if existing_alias_owner is not None:
            stats["conflict_existing_alias"] += 1
            continue

        key = (school_id, parsed_name)
        bucket = grouped.setdefault(
            key,
            {
                "school": school,
                "parsed_name": parsed_name,
                "target_name": target_name,
                "count": 0,
                "reason": reason,
                "evidence": [],
            },
        )
        bucket["count"] += 1
        evidence = {
            "school_id": school_id,
            "target_school_name": target_name,
            "parsed_school_name": parsed_name,
            "pdf_url": row.get("pdf_url"),
            "page_url": row.get("page_url"),
            "anchor_text": row.get("anchor_text"),
        }
        bucket["evidence"].append({k: v for k, v in evidence.items() if v})

    proposals: list[PdfSchoolMismatchAliasProposal] = []
    for bucket in grouped.values():
        school = bucket["school"]
        evidence = bucket["evidence"]
        proposals.append(
            PdfSchoolMismatchAliasProposal(
                template_name=bucket["parsed_name"],
                template_rows=int(bucket["count"]),
                proposal_type="alias_existing_school",
                matched_school_id=int(school.id),
                matched_school_name=school.school_name,
                matched_corporation=school.corporation_name,
                reasoning=(
                    "PDF body school-name mismatch looks like an official rename/expansion; "
                    f"{bucket['reason']}. Operator approval is required before SchoolAlias is written."
                ),
                evidence=evidence[:5],
            )
        )

    proposals.sort(key=lambda p: (-p.template_rows, p.template_name))
    stats["proposals"] = len(proposals)
    return proposals, stats


def load_rejection_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict):
                rows.append(row)
    return rows


def write_merged_proposals(path: Path, proposals: list[PdfSchoolMismatchAliasProposal]) -> dict[str, int]:
    existing: list[dict[str, Any]] = []
    seen_template_names: set[str] = set()
    if path.exists():
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(row, dict):
                    continue
                existing.append(row)
                template_name = str(row.get("template_name") or "")
                if template_name:
                    seen_template_names.add(template_name)

    now = datetime.now(UTC).isoformat()
    appended = 0
    for proposal in proposals:
        if proposal.template_name in seen_template_names:
            continue
        row = asdict(proposal)
        row["timestamp"] = now
        existing.append(row)
        seen_template_names.add(proposal.template_name)
        appended += 1

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in existing:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    return {"preserved": len(existing) - appended, "appended": appended, "written": len(existing)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--rejections",
        type=Path,
        default=Path("output/discovery_rejections.jsonl"),
        help="Discovery rejection JSONL containing pdf_school_mismatch rows.",
    )
    parser.add_argument(
        "--out-jsonl",
        type=Path,
        default=Path("output/school_missing_proposals.jsonl"),
        help="Existing operator proposal JSONL consumed by the review UI.",
    )
    args = parser.parse_args()

    rows = load_rejection_rows(args.rejections)
    session = SessionLocal()
    try:
        schools = session.query(School).all()
        aliases = session.query(SchoolAlias).all()
        proposals, stats = build_proposals(rows, schools, aliases)
    except SQLAlchemyError as exc:
        session.rollback()
        raise SystemExit(
            "Database is not initialized or not reachable. Run this inside an EIDP operator environment "
            "with a valid EIDP_DATABASE_URL/EIDP_DATA_DIR before generating alias proposals."
        ) from exc
    finally:
        session.close()

    write_stats = write_merged_proposals(args.out_jsonl, proposals)
    print(json.dumps({"proposal_stats": stats, "write_stats": write_stats}, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
