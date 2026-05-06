"""Sprint 8.3.1 — CLI write-safety regression for `eidp prefecture-aggregate`.

The 8.3 commit shipped both ``--apply`` and ``--dry-run/--no-dry-run`` flags;
the actual write predicate was ``not dry_run``, so a user could bypass the
``--apply`` gate by passing ``--no-dry-run`` alone. That violated the v6
contract that ``--apply`` is the single switch authorising a DB write.

This test file pins the new contract:

  * Default invocation       → no apply call, no commit, session rolled back.
  * ``--apply`` invocation   → exactly one apply call, exactly one commit.
  * (Removed) ``--no-dry-run`` is no longer a recognised option, so the CLI
    rejects it.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import fitz  # type: ignore[import-not-found]
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from typer.testing import CliRunner

from eidp.cli import app
from eidp.db.sqlite_bootstrap import bootstrap_sqlite


def _make_minimal_5col_pdf(path: Path) -> None:
    """Tiny single-row 5col PDF — enough for parse_5col to return one
    PrefSchool. The aggregator path runs end-to-end against this."""
    doc = fitz.open()
    page = doc.new_page(width=600, height=400)
    headers = ["学校名", "住所", "設置者の名称", "設置者の住所", "備考"]
    rows = [headers, ["テスト専門学校", "東京都", "学校法人T", "東京都", ""]]
    col_widths = [180, 110, 110, 110, 90]
    x = 20.0
    col_xs = []
    for w in col_widths:
        col_xs.append(x)
        x += w
    y = 50
    row_h = 30
    for row in rows:
        for ci, value in enumerate(row):
            r = fitz.Rect(col_xs[ci], y, col_xs[ci] + col_widths[ci], y + row_h)
            page.draw_rect(r, color=(0, 0, 0), width=0.5)
            page.insert_text((col_xs[ci] + 4, y + 18), str(value), fontsize=8, fontname="japan")
        y += row_h
    doc.save(str(path))
    doc.close()


@pytest.fixture()
def sqlite_db_url(tmp_path: Path) -> str:
    db_path = tmp_path / "cli_safety.sqlite3"
    engine = create_engine(f"sqlite:///{db_path}", future=True)
    bootstrap_sqlite(engine)
    engine.dispose()
    return f"sqlite:///{db_path}"


@pytest.fixture()
def artifact_dir(tmp_path: Path) -> Path:
    d = tmp_path / "artifacts"
    d.mkdir()
    _make_minimal_5col_pdf(d / "saitama.pdf")
    return d


@pytest.fixture()
def output_dir(tmp_path: Path) -> Path:
    d = tmp_path / "out"
    d.mkdir()
    return d


@pytest.fixture()
def patched_session(monkeypatch, sqlite_db_url):
    """Replace eidp.cli.SessionLocal-resolved engine with a SessionLocal
    bound to our temp SQLite, AND wrap the resulting Session so we can
    count commit() / rollback() / apply_writer_plan() invocations."""
    engine = create_engine(sqlite_db_url, future=True)
    session_local = sessionmaker(bind=engine, expire_on_commit=False)

    counters = {"commit": 0, "rollback": 0, "apply": 0}

    real_session_factory = session_local

    class CountingSession(Session):
        def commit(self):  # type: ignore[override]
            counters["commit"] += 1
            return super().commit()

        def rollback(self):  # type: ignore[override]
            counters["rollback"] += 1
            return super().rollback()

    session_local_counting = sessionmaker(
        bind=engine, expire_on_commit=False, class_=CountingSession,
    )

    # Patch the *symbol* `SessionLocal` resolved inside the CLI command.
    import eidp.db.session as session_mod
    monkeypatch.setattr(session_mod, "SessionLocal", session_local_counting)

    # Patch apply_writer_plan to count invocations without touching DB.
    import eidp.scraper.prefecture_aggregator as agg_mod
    apply_mock = MagicMock(return_value={"added": 0, "upgraded": 0, "skipped": 0})
    monkeypatch.setattr(agg_mod, "apply_writer_plan", apply_mock)
    counters["apply_calls"] = apply_mock  # pyright: ignore[reportArgumentType]

    yield counters
    engine.dispose()
    # Suppress unused warning for real_session_factory
    _ = real_session_factory


def _invoke(args: list[str], output_dir: Path, artifact_dir: Path) -> object:
    return _invoke_pref("saitama", args, output_dir, artifact_dir)


def _invoke_pref(pref: str, args: list[str], output_dir: Path, artifact_dir: Path) -> object:
    runner = CliRunner()
    return runner.invoke(
        app,
        [
            "prefecture-aggregate",
            "--pref", pref,
            "--artifact-dir", str(artifact_dir),
            "--output-dir", str(output_dir),
            *args,
        ],
        catch_exceptions=False,
    )


def test_default_invocation_is_strict_dry_run(patched_session, artifact_dir, output_dir):
    """No --apply: must NOT call apply_writer_plan, must NOT commit."""
    result = _invoke([], output_dir, artifact_dir)
    assert result.exit_code == 0, result.output
    apply_mock = patched_session["apply_calls"]
    assert apply_mock.call_count == 0, (
        f"default invocation must not call apply_writer_plan; "
        f"got {apply_mock.call_count} calls. Output:\n{result.output}"
    )
    assert patched_session["commit"] == 0, (
        f"default invocation must not commit; got {patched_session['commit']} commits"
    )
    assert patched_session["rollback"] >= 1
    # Writer-plan JSON should still be emitted.
    assert (output_dir / "saitama.json").exists()


def test_cli_accepts_html_prefecture_artifacts(monkeypatch, patched_session, tmp_path: Path, output_dir: Path) -> None:
    """HTML-type prefecture pages are first-class aggregator artifacts."""
    artifact_dir = tmp_path / "html-artifacts"
    artifact_dir.mkdir()
    (artifact_dir / "gunma.html").write_text("<html><table></table></html>", encoding="utf-8")
    seen: list[tuple[str, str]] = []

    def fake_aggregate(_session, pref: str, artifact: Path):  # noqa: ANN001
        seen.append((pref, artifact.name))
        return SimpleNamespace(
            pref=pref,
            pdf_path=str(artifact),
            extracted_total=1,
            db_matched=1,
            db_unmatched=0,
            action_distribution={"noop": 1},
            writer_plan=[],
            review_items=[],
        )

    import eidp.scraper.prefecture_aggregator as agg_mod

    monkeypatch.setattr(agg_mod, "aggregate", fake_aggregate)

    result = _invoke_pref("gunma", [], output_dir, artifact_dir)

    assert result.exit_code == 0, result.output
    assert seen == [("gunma", "gunma.html")]
    assert (output_dir / "gunma.json").exists()
    assert patched_session["commit"] == 0
    assert patched_session["rollback"] >= 1


def test_apply_invocation_calls_apply_writer_plan_and_commits(patched_session, artifact_dir, output_dir):
    """--apply: exactly one apply_writer_plan call and exactly one commit."""
    result = _invoke(["--apply"], output_dir, artifact_dir)
    assert result.exit_code == 0, result.output
    apply_mock = patched_session["apply_calls"]
    assert apply_mock.call_count == 1, (
        f"--apply must trigger exactly one apply_writer_plan call; "
        f"got {apply_mock.call_count}. Output:\n{result.output}"
    )
    assert patched_session["commit"] == 1, (
        f"--apply must commit once; got {patched_session['commit']}. "
        f"Output:\n{result.output}"
    )


def test_no_dry_run_flag_is_no_longer_recognised(patched_session, artifact_dir, output_dir):
    """The previously-allowed ``--no-dry-run`` bypass must now fail at
    argument parsing — it is no longer a valid option. This is the
    headline contract of 8.3.1: --apply is the single write switch."""
    result = _invoke(["--no-dry-run"], output_dir, artifact_dir)
    # Typer/Click reports unknown options with exit code 2.
    assert result.exit_code != 0, (
        f"--no-dry-run must be rejected; got exit_code={result.exit_code}, "
        f"output={result.output!r}"
    )
    apply_mock = patched_session["apply_calls"]
    assert apply_mock.call_count == 0
    assert patched_session["commit"] == 0
