"""Local bug-report bundle page."""

from __future__ import annotations

from pathlib import Path

import streamlit as st
from sqlalchemy.orm import Session

from eidp.bug_signals.bundle import build_bug_report_bundle, scrub_json_value
from eidp.bug_signals.detector import scan_bug_signals
from eidp.config import settings
from eidp.db.audit import log_manual_action
from eidp.db.models import ManualActionLog


def audit_bug_report_generated(
    session: Session,
    *,
    archive: Path,
    signal_count: int,
    operator_note_present: bool,
    actor: str = "operator",
) -> ManualActionLog:
    """Audit a locally generated support ZIP without storing free-text notes."""
    return log_manual_action(
        session,
        action_type="bug_report_generated",
        target_table="bug_report",
        old_value=None,
        new_value={
            "archive_name": archive.name,
            "archive_path": archive.as_posix(),
            "operator_note_present": operator_note_present,
            "signal_count": signal_count,
        },
        reason="Operator generated local bug report ZIP",
        actor=actor,
    )


def render(session: Session | None, *, app_root: Path | None = None) -> None:
    root = app_root or settings.app_root
    st.header("不具合レポート")
    st.caption("ローカルZIPを作成します。アップロードやGitHub連携は行いません。")

    try:
        signals = scan_bug_signals(root, check_sqlite=True)
    except Exception as exc:
        st.error(f"異常検出の確認に失敗しました: {type(exc).__name__}: {exc}")
        signals = []

    if signals:
        st.error(f"異常を {len(signals)} 件検出しました。レポートZIPを作成してください。")
        st.json(scrub_json_value([signal.to_dict() for signal in signals]))
    else:
        st.success("現在、異常は検出されていません。必要に応じて手動レポートを作成できます。")

    note = st.text_area("補足コメント（任意）", key="bug_report_operator_note", height=100)
    if st.button("ローカルレポートZIPを作成", type="primary", key="build_bug_report_zip"):
        try:
            result = build_bug_report_bundle(root, signals=signals, operator_note=note)
        except Exception as exc:
            st.error(f"レポート作成に失敗しました: {type(exc).__name__}: {exc}")
            return
        archive = Path(str(result["archive"]))
        if session is not None:
            try:
                audit_bug_report_generated(
                    session,
                    archive=archive,
                    signal_count=len(signals),
                    operator_note_present=bool(note.strip()),
                )
                session.commit()
            except Exception:
                session.rollback()
                raise
        st.success(f"作成完了: {archive.name}")
        if archive.is_file():
            st.download_button(
                "レポートZIPを保存",
                data=archive.read_bytes(),
                file_name=archive.name,
                mime="application/zip",
                key="download_bug_report_zip",
            )
