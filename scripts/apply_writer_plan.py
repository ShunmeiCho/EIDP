"""Stage 2 APPLY: write prefecture aggregator plan to school_site.

Consumes output/pref-aggregator/{pref}-writer-plan.json and performs:
- op=add      : INSERT new SchoolSite row
- op=upgrade  : INSERT new SchoolSite row (existing rows preserved)
- op=noop     : skip
- op=review   : append to review_item (if table exists) or write review CSV

Safety:
- Default is --dry-run (no DB writes). Must explicitly pass --apply.
- All writes in a single transaction per prefecture; rollback on any error.
- Before first apply run: snapshot affected school_site rows to
  school_site_backup_{timestamp} for rollback.
- Skips insert if (school_id, url) unique constraint would be violated.
- discovery_method='prefecture_aggregator'
- verified=false initially (Stage 3 will HTTP-verify + ownership-check
  before flipping to true).

Usage:
    # Dry-run (default): no DB writes, prints plan
    uv run python scripts/apply_writer_plan.py --pref tokyo

    # Small batch test (10 ops):
    uv run python scripts/apply_writer_plan.py --pref tokyo --apply --limit 10

    # Full apply:
    uv run python scripts/apply_writer_plan.py --pref tokyo --apply

    # All prefs:
    uv run python scripts/apply_writer_plan.py --all --apply
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from eidp.db.models import SchoolSite  # noqa: E402
from eidp.db.session import SessionLocal  # noqa: E402

PLAN_DIR = REPO_ROOT / "output" / "pref-aggregator"
REVIEW_DIR = REPO_ROOT / "output" / "pref-aggregator" / "review-queue"
VerifiedEntry = tuple[str, int, str]


def load_plan(pref: str) -> dict:
    p = PLAN_DIR / f"{pref}-writer-plan.json"
    if not p.exists():
        raise FileNotFoundError(
            f"plan missing: {p} — run generate_writer_plan.py first"
        )
    return json.loads(p.read_text())


def snapshot_school_site(session, pref: str, op_timestamp: str) -> int:
    """Backup school_site rows for affected schools before apply."""
    from sqlalchemy import text
    backup_table = f"school_site_backup_{pref}_{op_timestamp}"
    # Only backup rows for schools in this pref
    pref_jp_map = {
        "tokyo": "東京都", "kanagawa": "神奈川県", "saitama": "埼玉県",
        "osaka": "大阪府", "fukuoka": "福岡県", "hyogo": "兵庫県",
        "shizuoka": "静岡県", "okinawa": "沖縄県", "miyagi": "宮城県",
        "hokkaido": "北海道", "niigata": "新潟県", "aichi": "愛知県",
    }
    pref_jp = pref_jp_map.get(pref, pref)
    session.execute(text(f"""
        CREATE TABLE IF NOT EXISTS "{backup_table}" AS
        SELECT ss.* FROM school_site ss
        JOIN school s ON s.id = ss.school_id
        WHERE s.prefecture = :pref_jp
    """), {"pref_jp": pref_jp})
    session.commit()
    count = session.execute(text(f'SELECT COUNT(*) FROM "{backup_table}"')).scalar() or 0
    return int(count)


def _verified_entry(record: dict) -> VerifiedEntry | None:
    if not record.get("ownership_ok"):
        return None
    try:
        pref = str(record["pref"])
        school_id = int(record["school_id"])
        url = str(record["url"])
    except (KeyError, TypeError, ValueError):
        return None
    if not pref or not url:
        return None
    return (pref, school_id, url)


def resolve_verification_file(verification_file: Path | None = None) -> Path | None:
    if verification_file is None:
        candidates = sorted(PLAN_DIR.glob("url-verification-202*.json"))
        return candidates[-1] if candidates else None
    if verification_file.exists():
        return verification_file
    if not verification_file.is_absolute():
        plan_path = PLAN_DIR / verification_file
        if plan_path.exists():
            return plan_path
    return verification_file


def load_verified_entries(verification_file: Path | None = None) -> set[VerifiedEntry] | None:
    """Return (pref, school_id, url) rows marked ownership_ok=True.

    Returns None if no verification file exists (disables --verified-only gating).
    """
    latest = resolve_verification_file(verification_file)
    if latest is None:
        return None
    data = json.loads(latest.read_text())
    return {
        entry
        for r in data.get("results", [])
        if (entry := _verified_entry(r)) is not None
    }


def apply_plan(
    pref: str,
    *,
    apply: bool,
    limit: int | None = None,
    verified_only: bool = False,
    verification_file: Path | None = None,
) -> dict:
    plan = load_plan(pref)
    stats = {"add": 0, "upgrade": 0, "noop": 0, "review": 0,
             "skipped_duplicate": 0, "skipped_missing_url": 0,
             "skipped_not_verified": 0, "errors": 0}

    # Load HTTP verification set if --verified-only
    verified_entries: set[VerifiedEntry] | None = None
    if verified_only:
        verification_path = resolve_verification_file(verification_file)
        if verification_path is None:
            raise RuntimeError(
                "--verified-only requested but no url-verification-*.json found. "
                "Run scripts/http_verify_plan_urls.py first."
            )
        verified_entries = load_verified_entries(verification_path)
        if verified_entries is None:
            raise RuntimeError(f"verification file missing: {verification_path}")
        print(
            f"[{pref}] --verified-only: {len(verified_entries)} ownership-ok rows "
            f"loaded from {verification_path}"
        )

    session = SessionLocal()
    try:
        ops = plan.get("operations", [])
        actionable = [op for op in ops if op.get("op") in ("add", "upgrade")]
        reviews = [op for op in ops if op.get("op") == "review"]

        if limit is not None:
            actionable = actionable[:limit]

        print(f"[{pref}] plan: actionable={len(actionable)} review={len(reviews)} "
              f"dry_run={not apply} limit={limit} verified_only={verified_only}")

        if apply:
            ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
            snapshot_count = snapshot_school_site(session, pref, ts)
            print(f"[{pref}] snapshot: {snapshot_count} rows backed up for rollback")

        for op in actionable:
            op_type = op["op"]
            school_id = op.get("school_id")
            url = op.get("new_url")
            url_type = op.get("new_url_type") or "unknown"
            confidence = op.get("new_confidence") or 0.0

            if not url or not school_id:
                stats["skipped_missing_url"] += 1
                continue

            # --verified-only gating: only apply URLs that passed HTTP ownership check
            url_is_verified = False
            if verified_entries is not None:
                try:
                    verified_key = (pref, int(school_id), url)
                except (TypeError, ValueError):
                    stats["skipped_not_verified"] += 1
                    continue
                if verified_key not in verified_entries:
                    stats["skipped_not_verified"] += 1
                    continue
                url_is_verified = True

            # Check for UNIQUE (school_id, url) conflict
            existing = session.query(SchoolSite).filter(
                SchoolSite.school_id == school_id,
                SchoolSite.url == url,
            ).first()
            if existing:
                if apply:
                    existing.discovery_method = "prefecture_aggregator"
                    existing.url_type = url_type
                    existing.confidence = confidence
                    if url_is_verified:
                        existing.verified = True
                stats["skipped_duplicate"] += 1
                continue

            if apply:
                site = SchoolSite(
                    school_id=school_id,
                    url=url,
                    url_type=url_type,
                    discovery_method="prefecture_aggregator",
                    confidence=confidence,
                    # verified=true only when HTTP ownership check passed
                    verified=url_is_verified,
                )
                session.add(site)

            stats[op_type] += 1

        # Write review queue to CSV regardless of apply flag
        if reviews:
            REVIEW_DIR.mkdir(parents=True, exist_ok=True)
            review_csv = REVIEW_DIR / f"{pref}-review.csv"
            with review_csv.open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=[
                    "pdf_school_name", "pdf_school_code", "pdf_operator",
                    "match_strategy", "reason", "pref_url",
                ])
                writer.writeheader()
                for op in reviews:
                    writer.writerow({
                        "pdf_school_name": op.get("pdf_school_name") or "",
                        "pdf_school_code": op.get("pdf_school_code") or "",
                        "pdf_operator": op.get("pdf_operator") or "",
                        "match_strategy": op.get("match_strategy") or "",
                        "reason": op.get("reason") or "",
                        "pref_url": op.get("new_url") or "",
                    })
            stats["review"] = len(reviews)
            print(f"[{pref}] review queue -> {review_csv}")

        if apply:
            session.commit()
            print(f"[{pref}] COMMITTED: add={stats['add']} upgrade={stats['upgrade']} "
                  f"skipped_dup={stats['skipped_duplicate']}")
        else:
            session.rollback()
            print(f"[{pref}] DRY-RUN: would add={stats['add']} upgrade={stats['upgrade']} "
                  f"skipped_dup={stats['skipped_duplicate']}")

    except Exception as e:
        session.rollback()
        stats["errors"] += 1
        print(f"[{pref}] ERROR: {type(e).__name__}: {e} — rolled back")
        raise
    finally:
        session.close()

    return stats


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pref", type=str, help="prefecture key (e.g. tokyo)")
    ap.add_argument("--all", action="store_true", help="apply all available plans")
    ap.add_argument("--apply", action="store_true", help="actually write to DB (default: dry-run)")
    ap.add_argument("--limit", type=int, default=None, help="limit ops (for testing)")
    ap.add_argument("--verified-only", action="store_true",
                    help="only apply URLs that passed HTTP ownership verification "
                         "(requires scripts/http_verify_plan_urls.py output)")
    ap.add_argument(
        "--verification-file",
        type=Path,
        default=None,
        help="specific url-verification-*.json to use with --verified-only; defaults to latest",
    )
    args = ap.parse_args()

    if not args.pref and not args.all:
        ap.error("must pass --pref X or --all")

    prefs: list[str]
    if args.all:
        prefs = sorted(
            p.stem.replace("-writer-plan", "")
            for p in PLAN_DIR.glob("*-writer-plan.json")
        )
    else:
        prefs = [args.pref]

    verification_file = resolve_verification_file(args.verification_file) if args.verified_only else None
    master = {
        "apply": args.apply,
        "limit": args.limit,
        "verified_only": args.verified_only,
        "verification_file": str(verification_file) if verification_file else None,
        "prefs": {},
    }
    for pref in prefs:
        try:
            stats = apply_plan(pref, apply=args.apply, limit=args.limit,
                               verified_only=args.verified_only,
                               verification_file=verification_file)
            master["prefs"][pref] = stats
        except FileNotFoundError as e:
            print(f"[skip] {e}", file=sys.stderr)
            continue

    # Roll up totals
    totals = {"add": 0, "upgrade": 0, "review": 0,
              "skipped_duplicate": 0, "skipped_not_verified": 0, "errors": 0}
    for st in master["prefs"].values():
        for k in totals:
            totals[k] = totals[k] + st.get(k, 0)
    master["totals"] = totals

    report_name = (
        "apply-report-dryrun.json"
        if not args.apply
        else f"apply-report-{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    report_path = PLAN_DIR / report_name
    report_path.write_text(json.dumps(master, ensure_ascii=False, indent=2))
    print("\n=== TOTALS ===")
    print(json.dumps(totals, indent=2))
    print(f"Report: {report_path}")


if __name__ == "__main__":
    main()
