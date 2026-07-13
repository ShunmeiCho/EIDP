from __future__ import annotations

import ast
import contextlib
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from eidp.db.locking import LockBusyError, acquire_lock
from eidp.db.models import Base
from eidp.web.locking import acquire_web_write_lock, web_write_lock_path


def test_web_write_lock_uses_shared_data_lock(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    intake_root = data_dir / "web-intake"

    assert web_write_lock_path(intake_root, data_dir=data_dir) == data_dir / ".lock"


def test_web_write_lock_rejects_concurrent_writer(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    intake_root = data_dir / "web-intake"
    lock_path = data_dir / ".lock"

    with acquire_lock(lock_path, owner="background_job"):
        with pytest.raises(LockBusyError, match="background_job"):
            with acquire_web_write_lock(intake_root, owner="web_pdf_intake", data_dir=data_dir):
                pytest.fail("concurrent Web writer entered the critical section")


@pytest.mark.parametrize(
    ("page", "mutators"),
    [
        (
            Path("src/eidp/web/views/pdf_intake.py"),
            {"store_pdf_upload", "store_zip_upload", "register_url_csv", "ensure_extraction_queue"},
        ),
        (Path("src/eidp/web/views/extraction_queue.py"), {"ensure_extraction_queue", "run_extraction"}),
        (Path("src/eidp/web/views/extraction_review.py"), {"ensure_review_records"}),
    ],
)
def test_direct_web_mutations_are_inside_shared_write_lock(page: Path, mutators: set[str]) -> None:
    tree = ast.parse(page.read_text(encoding="utf-8"), filename=str(page))
    assert _unlocked_calls(tree, mutators) == []


def test_review_action_callable_runs_inside_shared_write_lock(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from eidp.web.views import extraction_review

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    lock_held = False

    @contextlib.contextmanager
    def fake_lock(*_args: Any, **_kwargs: Any):
        nonlocal lock_held
        lock_held = True
        try:
            yield
        finally:
            lock_held = False

    called = False

    def action(session: Session) -> None:
        nonlocal called
        assert lock_held
        assert session.bind is engine
        called = True

    monkeypatch.setattr(extraction_review, "acquire_web_write_lock", fake_lock)
    monkeypatch.setattr(extraction_review, "flush_audit_outbox", lambda *_args, **_kwargs: {"failed": 0})
    monkeypatch.setattr(extraction_review.st, "success", lambda _message: None)
    monkeypatch.setattr(extraction_review.st, "rerun", lambda: None)

    extraction_review._run_action(tmp_path, session_factory=session_factory, action=action)

    assert called
    assert lock_held is False
    engine.dispose()


def _call_name(node: ast.Call) -> str | None:
    return node.func.id if isinstance(node.func, ast.Name) else None


def _unlocked_calls(tree: ast.AST, mutators: set[str]) -> list[str]:
    violations: list[str] = []

    def visit(node: ast.AST, *, locked: bool) -> None:
        if isinstance(node, ast.With):
            for item in node.items:
                visit(item.context_expr, locked=locked)
            enters_lock = any(
                isinstance(item.context_expr, ast.Call)
                and _call_name(item.context_expr) == "acquire_web_write_lock"
                for item in node.items
            )
            for statement in node.body:
                visit(statement, locked=locked or enters_lock)
            return
        if isinstance(node, ast.Call):
            name = _call_name(node)
            if name in mutators and not locked:
                violations.append(f"{name}@{node.lineno}")
        for child in ast.iter_child_nodes(node):
            visit(child, locked=locked)

    visit(tree, locked=False)
    return violations
