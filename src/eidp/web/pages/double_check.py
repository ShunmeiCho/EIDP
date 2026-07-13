"""Persistent external double-check and audited resolution page."""

from __future__ import annotations

from collections.abc import Sequence
from hashlib import sha256
from pathlib import Path

import streamlit as st
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from eidp.config import settings
from eidp.db.audit_outbox import flush_audit_outbox
from eidp.db.locking import LockBusyError
from eidp.db.models import DoubleCheckResolution, ExternalComparisonResult, ExternalComparisonRun
from eidp.identity import ResolvedIdentity
from eidp.pipeline.double_check_resolution import (
    DoubleCheckPersistenceError,
    DoubleCheckResolutionError,
    ResolutionOutcome,
    create_external_comparison_run,
    latest_double_check_resolutions,
    load_external_comparison_results,
    resolve_double_check,
)
from eidp.pipeline.external_extraction_import import (
    ExternalExtractionImportError,
    ExternalExtractionRow,
    ExternalSourceSystem,
    load_external_extraction_file,
)
from eidp.pipeline.extraction_review import load_review_records
from eidp.pipeline.review_decision import overlay_review_decisions
from eidp.pipeline.review_report import reviewed_rows_from_records
from eidp.web.locking import acquire_web_write_lock, web_write_lock_path


def render_double_check_page(
    *,
    identity: ResolvedIdentity,
    session_factory: sessionmaker[Session],
    intake_root: Path | None = None,
) -> None:
    resolved_root = intake_root or Path(settings.data_dir) / "web-intake"

    st.title("EIDP Double Check")
    st.caption(
        "Create an immutable comparison snapshot, then record an explicit reasoned resolution. "
        "External values are never applied directly."
    )

    review_records = load_review_records(resolved_root)
    with session_factory() as session:
        reviewed_rows = reviewed_rows_from_records(overlay_review_decisions(session, review_records))
    st.metric("Reviewed rows", len(reviewed_rows))

    source_system = ExternalSourceSystem(
        str(
            st.selectbox(
                "source_system",
                [system.value for system in ExternalSourceSystem],
                index=0,
            )
        )
    )
    uploaded_file = st.file_uploader("External extraction CSV/XLSX", type=["csv", "xlsx", "xlsm"])
    if uploaded_file is None:
        st.info("Upload a file to create a new comparison run. The latest persisted run remains available below.")
    else:
        external_file_bytes = uploaded_file.getvalue()
        try:
            external_rows = load_external_extraction_file(
                external_file_bytes,
                filename=uploaded_file.name,
                source_system=source_system,
            )
        except ExternalExtractionImportError as exc:
            st.error(str(exc))
        else:
            _render_external_summary(external_rows)
            if st.button("Create comparison run", type="primary"):
                _create_comparison_run(
                    resolved_root,
                    session_factory=session_factory,
                    identity=identity,
                    external_file_bytes=external_file_bytes,
                    original_filename=uploaded_file.name,
                    source_system=source_system,
                )

    _render_latest_run(
        resolved_root,
        session_factory=session_factory,
        identity=identity,
    )


def _create_comparison_run(
    intake_root: Path,
    *,
    session_factory: sessionmaker[Session],
    identity: ResolvedIdentity,
    external_file_bytes: bytes,
    original_filename: str,
    source_system: ExternalSourceSystem,
) -> None:
    try:
        with acquire_web_write_lock(intake_root, owner="web_double_check_run"):
            with session_factory() as session:
                try:
                    create_external_comparison_run(
                        session,
                        intake_root=intake_root,
                        review_records=load_review_records(intake_root),
                        external_file_bytes=external_file_bytes,
                        original_filename=original_filename,
                        source_system=source_system,
                        identity=identity,
                    )
                    session.commit()
                except Exception:
                    session.rollback()
                    raise
    except (DoubleCheckPersistenceError, ExternalExtractionImportError, LockBusyError) as exc:
        st.error(str(exc))
        return
    except Exception:
        st.error("Comparison run could not be saved. No run was recorded.")
        return
    st.success("Comparison run saved.")
    st.rerun()


def _render_latest_run(
    intake_root: Path,
    *,
    session_factory: sessionmaker[Session],
    identity: ResolvedIdentity,
) -> None:
    with session_factory() as session:
        run = session.scalar(select(ExternalComparisonRun).order_by(ExternalComparisonRun.id.desc()).limit(1))
        if run is None:
            st.info("No persisted comparison run yet.")
            return
        results = load_external_comparison_results(session, run_id=run.run_id)
        resolutions = latest_double_check_resolutions(
            session,
            comparison_result_ids=[result.id for result in results],
        )

    st.subheader("Latest persisted comparison run")
    st.caption(
        f"Run {run.run_id} · {run.source_system} · {run.original_filename} · "
        f"actor {run.actor} ({run.identity_source})"
    )
    st.dataframe([_persisted_summary(run, results)], hide_index=True, use_container_width=True)
    st.dataframe(
        [_display_persisted_result(result, resolutions.get(result.id)) for result in results],
        hide_index=True,
        use_container_width=True,
    )
    _render_report_download(intake_root, run)
    if not results:
        st.info("This comparison run contains no result rows.")
        return

    labels = [_result_label(result) for result in results]
    selected_label = str(st.selectbox("comparison_result", labels))
    selected = results[labels.index(selected_label)]
    current = resolutions.get(selected.id)
    st.write(
        {
            "comparison_result_id": selected.id,
            "comparison_status": selected.comparison_status,
            "eidp_value": selected.eidp_value,
            "external_value": selected.external_value,
            "mismatch_reason": selected.mismatch_reason,
            "latest_resolution": current.outcome if current is not None else None,
        }
    )

    outcome = ResolutionOutcome(
        str(
            st.selectbox(
                "resolution_outcome",
                [candidate.value for candidate in ResolutionOutcome],
                key=f"double_check_outcome_{selected.id}",
            )
        )
    )
    reason = st.text_area(
        "resolution_reason",
        max_chars=500,
        key=f"double_check_reason_{selected.id}",
        help="Required for every outcome (1–500 characters).",
    )
    corrected_value: int | None = None
    if outcome in {ResolutionOutcome.ACCEPT_EXTERNAL, ResolutionOutcome.CORRECT}:
        default_value = _resolution_value_default(selected, outcome=outcome)
        corrected_value = int(
            st.number_input(
                "resolution_value",
                value=default_value,
                step=1,
                key=f"double_check_value_{selected.id}_{outcome.value}",
            )
        )
    if st.button("Save resolution", key=f"save_double_check_resolution_{selected.id}"):
        _save_resolution(
            intake_root,
            session_factory=session_factory,
            identity=identity,
            comparison_result_id=selected.id,
            outcome=outcome,
            corrected_value=corrected_value,
            reason=reason,
        )


def _save_resolution(
    intake_root: Path,
    *,
    session_factory: sessionmaker[Session],
    identity: ResolvedIdentity,
    comparison_result_id: int,
    outcome: ResolutionOutcome,
    corrected_value: int | None,
    reason: str,
) -> None:
    decision_committed = False
    outbox_stats: dict[str, int] | None = None
    try:
        with acquire_web_write_lock(intake_root, owner="web_double_check_resolution"):
            with session_factory() as session:
                try:
                    resolve_double_check(
                        session,
                        comparison_result_id=comparison_result_id,
                        outcome=outcome,
                        corrected_value=corrected_value,
                        reason=reason,
                        identity=identity,
                    )
                    session.commit()
                    decision_committed = True
                except Exception:
                    session.rollback()
                    raise
                outbox_stats = flush_audit_outbox(
                    session,
                    jsonl_path=web_write_lock_path(intake_root).parent / "audit" / "manual-actions.jsonl",
                )
    except (DoubleCheckResolutionError, LockBusyError) as exc:
        st.error(str(exc))
        return
    except Exception:
        if decision_committed:
            st.warning(
                "Resolution saved in the database, but audit JSONL projection is pending retry. "
                "The database decision is preserved."
            )
        else:
            st.error("Resolution could not be saved. No resolution was recorded.")
        return
    assert outbox_stats is not None
    if outbox_stats["failed"]:
        st.warning(
            "Resolution saved in the database, but audit JSONL projection is pending retry. "
            "The database decision is preserved."
        )
        return
    st.success("Resolution saved.")
    st.rerun()


def _render_external_summary(rows: Sequence[ExternalExtractionRow]) -> None:
    by_source: dict[str, int] = {}
    for row in rows:
        by_source[row.source_system.value] = by_source.get(row.source_system.value, 0) + 1
    st.metric("External metric rows", len(rows))
    st.dataframe([by_source], hide_index=True, use_container_width=True)


def _persisted_summary(
    run: ExternalComparisonRun,
    results: Sequence[ExternalComparisonResult],
) -> dict[str, object]:
    by_status: dict[str, int] = {}
    for result in results:
        by_status[result.comparison_status] = by_status.get(result.comparison_status, 0) + 1
    return {
        "run_id": run.run_id,
        "source_system": run.source_system,
        "results": len(results),
        **by_status,
    }


def _display_persisted_result(
    result: ExternalComparisonResult,
    resolution: DoubleCheckResolution | None,
) -> dict[str, object]:
    return {
        "comparison_result_id": result.id,
        "comparison_key": result.comparison_key,
        "comparison_status": result.comparison_status,
        "eidp_value": result.eidp_value,
        "external_value": result.external_value,
        "mismatch_reason": result.mismatch_reason,
        "review_id": result.review_id or "",
        "review_decision_revision": result.review_decision_revision or "",
        "resolution_outcome": resolution.outcome if resolution is not None else "",
        "effective_value": resolution.effective_value if resolution is not None else None,
        "resolution_reason": resolution.reason if resolution is not None else "",
        "resolution_revision": resolution.revision if resolution is not None else "",
    }


def _result_label(result: ExternalComparisonResult) -> str:
    return f"{result.id} / {result.comparison_key} / {result.comparison_status}"


def _resolution_value_default(
    result: ExternalComparisonResult,
    *,
    outcome: ResolutionOutcome,
) -> int:
    if outcome is ResolutionOutcome.ACCEPT_EXTERNAL:
        value = result.external_value
        if isinstance(value, int) and not isinstance(value, bool):
            return value
    return 0


def _render_report_download(intake_root: Path, run: ExternalComparisonRun) -> None:
    root = intake_root.resolve()
    relative_path = Path(run.report_path)
    if relative_path.is_absolute() or ".." in relative_path.parts:
        st.warning("Persisted comparison report is unavailable.")
        return
    try:
        candidate = root
        for part in relative_path.parts:
            candidate /= part
            if candidate.is_symlink():
                st.warning("Persisted comparison report is unavailable.")
                return
        report_path = candidate.resolve(strict=True)
        if not report_path.is_relative_to(root) or not report_path.is_file():
            st.warning("Persisted comparison report is unavailable.")
            return
        report_bytes = report_path.read_bytes()
    except OSError:
        st.warning("Persisted comparison report is unavailable.")
        return
    if sha256(report_bytes).hexdigest() != run.report_sha256:
        st.warning("Persisted comparison report is unavailable.")
        return
    st.download_button(
        "Download double_check_report.csv",
        data=report_bytes,
        file_name="double_check_report.csv",
        mime="text/csv",
    )
