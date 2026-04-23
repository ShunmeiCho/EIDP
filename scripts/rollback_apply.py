"""Rollback a previous apply_writer_plan.py --apply run.

Addresses Codex adversarial review finding [high]:
  "Snapshot backup is not an executable rollback strategy"

Strategy:
  1. Read apply-report-*.json to identify which prefectures/timestamp were applied
  2. Find the matching school_site_backup_{pref}_{ts} tables
  3. Compute diff: school_site now vs snapshot → rows inserted by the apply
     Also detect rows whose discovery_method / confidence / verified were
     mutated by "update on duplicate" path
  4. Generate rollback SQL (idempotent, transactional):
     - DELETE newly-inserted rows (by (school_id, url) not in snapshot)
     - RESTORE mutated rows from snapshot
  5. Dry-run by default; --apply to execute

Safety:
  - Dry-run prints rollback SQL without executing
  - --apply runs in transaction, ROLLBACK on any error
  - Produces rollback-report-{ts}.json with counts

Usage:
    # See what would be rolled back from latest apply
    uv run python scripts/rollback_apply.py

    # Target a specific apply timestamp
    uv run python scripts/rollback_apply.py --apply-ts 20260423_181143

    # Actually execute rollback
    uv run python scripts/rollback_apply.py --apply-ts 20260423_181143 --apply
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy import text

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from eidp.db.session import SessionLocal  # noqa: E402

PLAN_DIR = REPO_ROOT / "output" / "pref-aggregator"


def latest_apply_report() -> Path | None:
    reports = sorted(PLAN_DIR.glob("apply-report-202*.json"))
    return reports[-1] if reports else None


def find_snapshot_tables(session, apply_ts: str) -> list[str]:
    """Return list of snapshot table names matching the apply timestamp."""
    rows = session.execute(text("""
        SELECT tablename FROM pg_tables
        WHERE schemaname = 'public'
          AND tablename LIKE 'school_site_backup_%' || :ts
    """), {"ts": apply_ts}).fetchall()
    return [r[0] for r in rows]


def rollback_pref(session, snapshot_table: str, *, apply: bool) -> dict:
    """Rollback one prefecture's apply."""
    # Parse pref name from table: school_site_backup_{pref}_{ts}
    m = re.match(r"school_site_backup_([a-z]+)_(\d{8}_\d{6})", snapshot_table)
    if not m:
        return {"error": f"cannot parse table name: {snapshot_table}"}
    pref, ts = m.groups()

    stats = {"pref": pref, "snapshot_table": snapshot_table, "apply": apply,
             "deleted_inserts": 0, "restored_updates": 0,
             "new_rows_found": 0, "updated_rows_found": 0}

    # Find rows inserted by apply = in school_site but not in snapshot
    # (match on (school_id, url) which is the UNIQUE key)
    new_rows = session.execute(text(f"""
        SELECT ss.id, ss.school_id, ss.url, ss.discovery_method
        FROM school_site ss
        WHERE ss.school_id IN (SELECT DISTINCT school_id FROM "{snapshot_table}")
          AND NOT EXISTS (
            SELECT 1 FROM "{snapshot_table}" b
            WHERE b.school_id = ss.school_id AND b.url = ss.url
          )
    """)).fetchall()
    stats["new_rows_found"] = len(new_rows)

    # Find rows that were updated (same school_id+url in both, but metadata differs)
    updated_rows = session.execute(text(f"""
        SELECT ss.id, ss.discovery_method AS now_method,
               b.discovery_method AS old_method,
               ss.url_type AS now_type, b.url_type AS old_type,
               ss.confidence AS now_conf, b.confidence AS old_conf,
               ss.verified AS now_verified, b.verified AS old_verified
        FROM school_site ss
        JOIN "{snapshot_table}" b ON b.school_id = ss.school_id AND b.url = ss.url
        WHERE (ss.discovery_method IS DISTINCT FROM b.discovery_method
            OR ss.url_type IS DISTINCT FROM b.url_type
            OR ss.confidence IS DISTINCT FROM b.confidence
            OR ss.verified IS DISTINCT FROM b.verified)
    """)).fetchall()
    stats["updated_rows_found"] = len(updated_rows)

    print(f"[{pref}] snapshot={snapshot_table} "
          f"new={stats['new_rows_found']} updated={stats['updated_rows_found']}")

    if apply:
        # Delete newly-inserted rows (rollback apply inserts)
        if new_rows:
            ids = tuple(r[0] for r in new_rows)
            session.execute(text(
                "DELETE FROM school_site WHERE id = ANY(:ids)"
            ), {"ids": list(ids)})
            stats["deleted_inserts"] = len(ids)

        # Restore mutated rows from snapshot
        if updated_rows:
            session.execute(text(f"""
                UPDATE school_site ss
                SET discovery_method = b.discovery_method,
                    url_type = b.url_type,
                    confidence = b.confidence,
                    verified = b.verified,
                    verified_at = b.verified_at,
                    http_status = b.http_status,
                    last_checked = b.last_checked
                FROM "{snapshot_table}" b
                WHERE ss.school_id = b.school_id AND ss.url = b.url
                  AND (ss.discovery_method IS DISTINCT FROM b.discovery_method
                    OR ss.url_type IS DISTINCT FROM b.url_type
                    OR ss.confidence IS DISTINCT FROM b.confidence
                    OR ss.verified IS DISTINCT FROM b.verified)
            """))
            stats["restored_updates"] = len(updated_rows)
    return stats


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply-ts", type=str, default=None,
                    help="timestamp suffix of apply run (e.g. 20260423_181143). "
                         "If omitted, uses latest apply-report.")
    ap.add_argument("--apply", action="store_true",
                    help="actually execute rollback (default: dry-run)")
    args = ap.parse_args()

    # Resolve timestamp
    apply_ts = args.apply_ts
    if not apply_ts:
        report = latest_apply_report()
        if report:
            # parse apply-report-20260423_181143.json
            m = re.search(r"apply-report-(\d{8}_\d{6})\.json", report.name)
            if m:
                apply_ts = m.group(1)
                print(f"[auto] using latest apply-report timestamp: {apply_ts} ({report.name})")
        if not apply_ts:
            print("ERROR: no apply-report found and no --apply-ts given", file=sys.stderr)
            sys.exit(1)

    session = SessionLocal()
    try:
        snapshots = find_snapshot_tables(session, apply_ts)
        if not snapshots:
            print(f"ERROR: no snapshot tables found for timestamp {apply_ts}", file=sys.stderr)
            print(f"Looked for pattern: school_site_backup_%_{apply_ts}")
            sys.exit(1)

        print(f"[rollback] apply_ts={apply_ts} snapshots={len(snapshots)} dry_run={not args.apply}")

        results = []
        total = {"new_rows_found": 0, "updated_rows_found": 0,
                 "deleted_inserts": 0, "restored_updates": 0}
        for table in snapshots:
            r = rollback_pref(session, table, apply=args.apply)
            results.append(r)
            for k in total:
                total[k] += r.get(k, 0)

        if args.apply:
            session.commit()
            print(f"[rollback] COMMITTED: deleted={total['deleted_inserts']} "
                  f"restored={total['restored_updates']}")
        else:
            session.rollback()
            print(f"[rollback] DRY-RUN: would delete={total['new_rows_found']} "
                  f"restore={total['updated_rows_found']}")

        report = {
            "apply_ts": apply_ts,
            "executed": args.apply,
            "totals": total,
            "per_pref": results,
            "generated_at": datetime.now().isoformat(),
        }
        out_path = PLAN_DIR / f"rollback-report-{apply_ts}.json"
        out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2))
        print(f"Report: {out_path}")

    finally:
        session.close()


if __name__ == "__main__":
    main()
