"""EIDP CLI entrypoint."""

from pathlib import Path

import typer

app = typer.Typer(name="eidp", help="Education Institution Data Pipeline")


@app.command()
def import_excel(
    excel_path: Path = typer.Argument(..., help="Path to master Excel file"),
) -> None:
    """Import master Excel into database."""
    from eidp.db.session import get_session
    from eidp.excel.importer import import_all

    session_gen = get_session()
    session = next(session_gen)
    try:
        results = import_all(excel_path, session)
        next(session_gen, None)  # trigger commit
        for sheet, stats in results.items():
            typer.echo(f"  {sheet}: {stats}")
        typer.echo("Import complete.")
    except Exception:
        try:
            next(session_gen, None)
        except Exception:
            pass
        raise


@app.command()
def db_info() -> None:
    """Show database statistics."""
    from sqlalchemy import func

    from eidp.db.models import Department, DepartmentYearly, School, SchoolYearStatus, SupportRecipient
    from eidp.db.session import SessionLocal

    session = SessionLocal()
    try:
        typer.echo(f"Schools:            {session.query(func.count(School.id)).scalar()}")
        typer.echo(f"Departments:        {session.query(func.count(Department.id)).scalar()}")
        typer.echo(f"DepartmentYearly:   {session.query(func.count(DepartmentYearly.id)).scalar()}")
        typer.echo(f"SchoolYearStatus:   {session.query(func.count(SchoolYearStatus.id)).scalar()}")
        typer.echo(f"SupportRecipient:   {session.query(func.count(SupportRecipient.id)).scalar()}")
    finally:
        session.close()


if __name__ == "__main__":
    app()
