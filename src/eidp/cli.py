"""EIDP CLI entrypoint."""

from pathlib import Path

import typer

app = typer.Typer(name="eidp", help="Education Institution Data Pipeline")


@app.command()
def import_excel(
    excel_path: Path = typer.Argument(..., help="Path to master Excel file"),
) -> None:
    """Import master Excel into database."""
    from eidp.db.session import SessionLocal
    from eidp.excel.importer import import_all

    session = SessionLocal()
    try:
        results = import_all(excel_path, session)
        session.commit()
        for sheet, stats in results.items():
            typer.echo(f"  {sheet}: {stats}")
        typer.echo("Import complete.")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@app.command()
def match_mext(
    data_dir: Path = typer.Option(Path("data/mext"), help="MEXT data directory"),
    dry_run: bool = typer.Option(False, help="Show matches without writing to DB"),
) -> None:
    """Match schools against MEXT school codes (Step 3)."""
    from eidp.matcher.school_matcher import apply_matches, match_schools
    from eidp.db.session import SessionLocal

    session = SessionLocal()
    try:
        report = match_schools(session, data_dir)

        typer.echo(f"\nMatch Results:")
        typer.echo(f"  Exact:        {len(report.exact)}")
        typer.echo(f"  NFKC:         {len(report.nfkc)}")
        typer.echo(f"  Pref+Partial: {len(report.pref_partial)}")
        typer.echo(f"  Unmatched:    {len(report.unmatched)}")
        typer.echo(f"  Match rate:   {report.total_matched / report.total * 100:.1f}%")

        if not dry_run:
            stats = apply_matches(session, report)
            session.commit()
            typer.echo(f"\nApplied:")
            typer.echo(f"  Codes assigned: {stats['codes_assigned']}")
            typer.echo(f"  Aliases created: {stats['aliases_created']}")
            typer.echo(f"  Conflicts:      {stats['conflicts']}")
        else:
            typer.echo("\n(dry run — no DB writes)")
            session.rollback()

        if report.unmatched:
            typer.echo(f"\nTop unmatched corporations:")
            from collections import Counter
            corps = Counter(r.corporation_name for r in report.unmatched)
            for corp, count in corps.most_common(10):
                typer.echo(f"  {corp}: {count}")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@app.command()
def reconcile(
    data_dir: Path = typer.Option(Path("data/mext"), help="MEXT data directory"),
    dry_run: bool = typer.Option(False, help="Show results without writing to DB"),
) -> None:
    """Reconcile unmatched schools against target institution list (Step 4)."""
    from eidp.db.session import SessionLocal
    from eidp.matcher.reconciler import apply_reconciliation, reconcile as do_reconcile

    session = SessionLocal()
    try:
        report = do_reconcile(session, data_dir)

        typer.echo(f"\nReconciliation Results:")
        typer.echo(f"  Already resolved:   {report.already_resolved}")
        typer.echo(f"  Auto-assigned:      {len(report.auto_assigned)}")
        typer.echo(f"  Excluded:           {len(report.excluded)}")
        typer.echo(f"  Needs manual:       {len(report.needs_manual)}")
        typer.echo(f"  Missing from DB:    {len(report.missing_from_db)}")

        if not dry_run:
            stats = apply_reconciliation(session, report)
            session.commit()
            typer.echo(f"\nApplied:")
            typer.echo(f"  Codes assigned: {stats['codes_assigned']}")
            typer.echo(f"  Aliases created: {stats['aliases_created']}")
        else:
            typer.echo("\n(dry run)")
            session.rollback()

        if report.needs_manual:
            typer.echo(f"\nManual resolution needed ({len(report.needs_manual)}):")
            from collections import Counter
            corps = Counter(c.corporation_name for c in report.needs_manual)
            for corp, count in corps.most_common(10):
                typer.echo(f"  {corp}: {count}")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@app.command()
def verify_identity(
    data_dir: Path = typer.Option(Path("data/mext"), help="MEXT data directory"),
) -> None:
    """Verify all schools have stable IDs (Step 4 gate)."""
    from eidp.db.session import SessionLocal
    from eidp.matcher.reconciler import verify_identity as do_verify

    session = SessionLocal()
    try:
        result = do_verify(session, data_dir)
        typer.echo(f"\nIdentity Verification:")
        for k, v in result.items():
            typer.echo(f"  {k}: {v}")
        if result["pass"]:
            typer.echo("\nGATE: PASS")
        else:
            typer.echo(f"\nGATE: FAIL ({result['unresolved']} unresolved)")
    finally:
        session.close()


@app.command()
def db_info() -> None:
    """Show database statistics."""
    from sqlalchemy import func

    from eidp.db.models import Department, DepartmentYearly, School, SchoolAlias, SchoolYearStatus, SupportRecipient
    from eidp.db.session import SessionLocal

    session = SessionLocal()
    try:
        typer.echo(f"Schools:            {session.query(func.count(School.id)).scalar()}")
        typer.echo(f"  with school_code: {session.query(func.count(School.id)).filter(School.school_code.isnot(None)).scalar()}")
        typer.echo(f"Departments:        {session.query(func.count(Department.id)).scalar()}")
        typer.echo(f"DepartmentYearly:   {session.query(func.count(DepartmentYearly.id)).scalar()}")
        typer.echo(f"SchoolYearStatus:   {session.query(func.count(SchoolYearStatus.id)).scalar()}")
        typer.echo(f"SupportRecipient:   {session.query(func.count(SupportRecipient.id)).scalar()}")
        typer.echo(f"SchoolAlias:        {session.query(func.count(SchoolAlias.id)).scalar()}")
    finally:
        session.close()


if __name__ == "__main__":
    app()
