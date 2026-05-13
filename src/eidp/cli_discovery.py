"""Top-level discovery/gold-set/RCA CLI command handlers."""

from __future__ import annotations

import json
from pathlib import Path

import typer


def register_discovery_commands(app: typer.Typer) -> None:
    app.command("discovery-gold-set")(discovery_gold_set)
    app.command("discovery-gold-run-plan")(discovery_gold_run_plan)
    app.command("discovery-gold-expected-predictions")(discovery_gold_expected_predictions)
    app.command("eval-discovery-gold")(eval_discovery_gold)
    app.command("summarize-discovery-evidence")(summarize_discovery_evidence)
    app.command("discovery-rca-packet")(discovery_rca_packet)
    app.command("discovery-rca-batch-plan")(discovery_rca_batch_plan)
    app.command("discovery-rca-outcome-validate")(discovery_rca_outcome_validate)


def discovery_gold_set(
    gold_set_dir: Path = typer.Option(Path("data/discovery-gold-set"), help="Discovery gold-set directory"),
    output_json: bool = typer.Option(False, "--json", help="Emit JSON instead of a short text summary"),
    fail_on_undemonstrated_pattern_sources: bool = typer.Option(
        False,
        "--fail-on-undemonstrated-pattern-sources",
        help="Exit non-zero when tracked extractor sources lack discovery gold-set demonstrations",
    ),
) -> None:
    """Summarize discovery demonstration coverage."""
    from eidp.scraper.discovery_gold_set import (
        load_discovery_gold_entries,
        render_discovery_gold_summary,
        summarize_discovery_gold_entries,
    )

    entries = load_discovery_gold_entries(gold_set_dir)
    summary = summarize_discovery_gold_entries(entries)
    if output_json:
        typer.echo(render_discovery_gold_summary(summary))
        if fail_on_undemonstrated_pattern_sources and summary.undemonstrated_pattern_sources:
            raise typer.Exit(1)
        return

    typer.echo(f"Discovery gold set: {summary.total_entries} entries")
    typer.echo(f"  strict target-year success: {summary.strict_target_year_successes}")
    typer.echo(f"  operator review:            {summary.operator_review_entries}")
    typer.echo(f"  publication lag:            {summary.publication_lag_entries}")
    typer.echo("  outcomes:")
    for outcome, count in summary.outcome_counts.items():
        typer.echo(f"    {outcome}: {count}")
    if summary.pattern_type_counts:
        typer.echo("  extractor patterns:")
        for pattern_type, count in summary.pattern_type_counts.items():
            typer.echo(f"    {pattern_type}: {count}")
    if summary.undemonstrated_pattern_sources:
        typer.echo("  extractor sources without gold demonstrations:")
        for source in summary.undemonstrated_pattern_sources:
            typer.echo(f"    {source}")
    if fail_on_undemonstrated_pattern_sources and summary.undemonstrated_pattern_sources:
        raise typer.Exit(1)


def discovery_gold_run_plan(
    gold_set_dir: Path = typer.Option(Path("data/discovery-gold-set"), help="Discovery gold-set directory"),
    output_json: bool = typer.Option(False, "--json", help="Emit JSON instead of a short text summary"),
) -> None:
    """Emit bounded PDF discovery inputs from the discovery gold set."""
    from eidp.scraper.discovery_gold_set import (
        build_discovery_gold_run_plan,
        load_discovery_gold_entries,
        render_discovery_gold_run_plan,
    )

    plan = build_discovery_gold_run_plan(load_discovery_gold_entries(gold_set_dir))
    if output_json:
        typer.echo(render_discovery_gold_run_plan(plan))
        return

    typer.echo(f"Discovery gold run plan: {len(plan)} entries")
    for item in plan:
        typer.echo(f"  {item.entry_id}: school_id={item.school_id} site_url={item.site_url}")


def discovery_gold_expected_predictions(
    gold_set_dir: Path = typer.Option(Path("data/discovery-gold-set"), help="Discovery gold-set directory"),
) -> None:
    """Emit the canonical expected-predictions JSONL fixture for the discovery gold set."""
    from eidp.scraper.discovery_gold_set import (
        build_discovery_gold_expected_predictions,
        load_discovery_gold_entries,
        render_discovery_gold_predictions,
    )

    entries = load_discovery_gold_entries(gold_set_dir)
    predictions = build_discovery_gold_expected_predictions(entries)
    typer.echo(render_discovery_gold_predictions(predictions), nl=False)


def eval_discovery_gold(
    predictions: Path | None = typer.Option(None, help="JSONL predictions to compare against the discovery gold set"),
    pdf_evidence: Path | None = typer.Option(
        None,
        help="discover-pdfs evidence JSONL to convert into predictions before evaluation",
    ),
    gold_set_dir: Path = typer.Option(Path("data/discovery-gold-set"), help="Discovery gold-set directory"),
    output_json: bool = typer.Option(False, "--json", help="Emit JSON instead of a short text summary"),
    fail_on_regression: bool = typer.Option(
        False,
        "--fail-on-regression",
        help="Exit non-zero when predictions are missing, unexpected, or mismatched",
    ),
) -> None:
    """Evaluate crawler or agent predictions against discovery gold-set entries."""
    from eidp.scraper.discovery_gold_set import (
        evaluate_discovery_gold_predictions,
        load_discovery_gold_entries,
        load_discovery_gold_predictions,
        load_discovery_gold_predictions_from_pdf_evidence,
        render_discovery_gold_eval_report,
    )

    entries = load_discovery_gold_entries(gold_set_dir)
    if predictions is None and pdf_evidence is None:
        typer.echo("Either --predictions or --pdf-evidence is required.", err=True)
        raise typer.Exit(2)
    if predictions is not None and pdf_evidence is not None:
        typer.echo("Use only one of --predictions or --pdf-evidence.", err=True)
        raise typer.Exit(2)
    if predictions is not None:
        predicted = load_discovery_gold_predictions(predictions)
    else:
        assert pdf_evidence is not None
        predicted = load_discovery_gold_predictions_from_pdf_evidence(pdf_evidence, entries)
    report = evaluate_discovery_gold_predictions(entries, predicted)
    if output_json:
        typer.echo(render_discovery_gold_eval_report(report))
        if fail_on_regression and _discovery_gold_gate_failed(report):
            raise typer.Exit(1)
        return

    typer.echo(f"Discovery gold evaluation: {report.exact_matches}/{report.total_gold_entries} exact")
    typer.echo(f"  predictions: {report.predicted_entries}")
    typer.echo(f"  failed:      {report.failed_predictions}")
    typer.echo(f"  missing:     {report.missing_entries}")
    typer.echo(f"  unexpected:  {report.unexpected_predictions}")
    if fail_on_regression and _discovery_gold_gate_failed(report):
        typer.echo("Discovery gold gate failed")
        raise typer.Exit(1)


def _discovery_gold_gate_failed(report: object) -> bool:
    return (
        int(getattr(report, "failed_predictions", 0)) > 0
        or int(getattr(report, "missing_entries", 0)) > 0
        or int(getattr(report, "unexpected_predictions", 0)) > 0
    )


def _reject_relative_path_traversal(path: Path, *, label: str) -> None:
    if not path.is_absolute() and any(part == ".." for part in path.parts):
        typer.echo(f"{label} relative path must not contain '..': {path}", err=True)
        raise typer.Exit(1)


def summarize_discovery_evidence(
    evidence_log: Path = typer.Option(..., help="discover-pdfs evidence JSONL to summarize"),
    prefecture: str = typer.Option("", help="Optional DB scope: school.prefecture"),
    discovery_method: str = typer.Option("", help="Optional DB scope: school_site.discovery_method"),
    output_json: bool = typer.Option(False, "--json", help="Emit JSON instead of a short text summary"),
) -> None:
    """Summarize PDF discovery evidence into school-level RCA buckets."""
    _reject_relative_path_traversal(evidence_log, label="--evidence-log")

    from eidp.scraper.discovery_evidence_summary import (
        load_pdf_discovery_evidence,
        load_pdf_discovery_site_scope,
        render_pdf_discovery_evidence_summary,
        summarize_pdf_discovery_evidence,
    )

    rows = load_pdf_discovery_evidence(evidence_log)
    site_scope = None
    if prefecture or discovery_method:
        from eidp.db.session import SessionLocal

        session = SessionLocal()
        try:
            site_scope = load_pdf_discovery_site_scope(
                session,
                prefecture=prefecture,
                discovery_method=discovery_method,
            )
        finally:
            session.close()

    summary = summarize_pdf_discovery_evidence(rows, site_scope=site_scope)
    if output_json:
        typer.echo(render_pdf_discovery_evidence_summary(summary))
        return

    typer.echo("Discovery evidence summary:")
    typer.echo(f"  evidence rows:         {summary.evidence_rows}")
    typer.echo(f"  schools with evidence: {summary.schools_with_evidence}")
    typer.echo(f"  site scope schools:    {summary.site_scope_schools}")
    typer.echo("  school buckets:")
    for bucket, count in summary.school_bucket_counts.items():
        typer.echo(f"    {bucket}: {count}")


def discovery_rca_packet(
    school_id: int = typer.Option(..., help="School.id to prepare for single-school RCA"),
    target_fiscal_year: int | None = typer.Option(
        None,
        help="Target fiscal year. Defaults to settings.target_fiscal_year.",
    ),
    evidence_log: Path | None = typer.Option(
        None,
        help="Optional discover-pdfs evidence JSONL used to fill latest_bucket.",
    ),
    known_operator_note: str = typer.Option("", help="Optional operator note to preserve in the packet"),
    output_prompt: bool = typer.Option(False, "--prompt", help="Emit a copy-paste Codex RCA prompt"),
    output_json: bool = typer.Option(False, "--json", help="Emit JSON input packet"),
) -> None:
    """Build a read-only single-school RCA packet for Codex-assisted discovery."""
    if output_json and output_prompt:
        typer.echo("--json and --prompt are mutually exclusive", err=True)
        raise typer.Exit(1)
    if evidence_log is not None:
        _reject_relative_path_traversal(evidence_log, label="--evidence-log")

    from eidp.config import settings
    from eidp.db.session import SessionLocal
    from eidp.scraper.discovery_rca_packet import (
        build_single_school_rca_packet,
        render_single_school_rca_packet,
        render_single_school_rca_prompt,
    )

    session = SessionLocal()
    try:
        packet = build_single_school_rca_packet(
            session,
            school_id=school_id,
            target_fiscal_year=target_fiscal_year or int(settings.target_fiscal_year),
            evidence_log=evidence_log,
            known_operator_note=known_operator_note,
        )
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc
    finally:
        session.close()

    if output_json:
        typer.echo(render_single_school_rca_packet(packet))
        return
    if output_prompt:
        typer.echo(render_single_school_rca_prompt(packet))
        return

    typer.echo(f"RCA packet for school_id={packet['school_id']}: {packet['school_name']}")
    typer.echo(f"  prefecture:        {packet['prefecture']}")
    typer.echo(f"  target_fiscal_year:{packet['target_fiscal_year']}")
    typer.echo(f"  latest_bucket:     {packet['latest_bucket']}")
    typer.echo(f"  official URL:      {packet['official_index_url'] or '(none)'}")
    typer.echo(f"  registered sites:  {len(packet['registered_sites'])}")


def discovery_rca_batch_plan(
    evidence_log: Path = typer.Option(..., help="discover-pdfs evidence JSONL used to prioritize schools"),
    target_fiscal_year: int | None = typer.Option(
        None,
        help="Target fiscal year. Defaults to settings.target_fiscal_year.",
    ),
    prefecture: str = typer.Option("", help="Optional DB scope: school.prefecture"),
    discovery_method: str = typer.Option("", help="Optional DB scope: school_site.discovery_method"),
    limit: int = typer.Option(10, help="Maximum number of RCA packet items to emit"),
    known_operator_note: str = typer.Option("", help="Optional operator note copied into every packet"),
    include_prompts: bool = typer.Option(False, "--include-prompts", help="Embed copy-paste Codex prompts per item"),
    output_json: bool = typer.Option(False, "--json", help="Emit JSON batch plan"),
) -> None:
    """Build a prioritized read-only batch of single-school RCA packets."""
    _reject_relative_path_traversal(evidence_log, label="--evidence-log")

    from eidp.config import settings
    from eidp.db.session import SessionLocal
    from eidp.scraper.discovery_rca_packet import (
        build_single_school_rca_batch_plan,
        render_single_school_rca_batch_plan,
    )

    session = SessionLocal()
    try:
        plan = build_single_school_rca_batch_plan(
            session,
            evidence_log=evidence_log,
            target_fiscal_year=target_fiscal_year or int(settings.target_fiscal_year),
            prefecture=prefecture,
            discovery_method=discovery_method,
            limit=limit,
            known_operator_note=known_operator_note,
            include_prompts=include_prompts,
        )
    finally:
        session.close()

    if output_json:
        typer.echo(render_single_school_rca_batch_plan(plan))
        return

    typer.echo(f"RCA batch plan: {len(plan['items'])}/{plan['total_candidates']} candidates")
    for item in plan["items"]:
        packet = item["packet"]
        typer.echo(f"  [{item['bucket']}] school_id={packet['school_id']} {packet['school_name']}")


def discovery_rca_outcome_validate(
    input_path: Path = typer.Option(
        ...,
        "--input",
        help="Path to one Required Output Block JSON file, or a directory of *.json outcome files",
    ),
    batch_plan_path: Path | None = typer.Option(
        None,
        "--batch-plan",
        help="Optional discovery-rca-batch-plan JSON; require exact school/FY coverage",
    ),
) -> None:
    """Validate a Codex-assisted single-school RCA output block."""
    _reject_relative_path_traversal(input_path, label="--input")
    if batch_plan_path is not None:
        _reject_relative_path_traversal(batch_plan_path, label="--batch-plan")

    from eidp.scraper.discovery_rca_packet import (
        validate_rca_outcome_batch_plan_coverage,
        validate_single_school_rca_outcome,
    )

    is_directory = input_path.is_dir()
    input_files = sorted(input_path.glob("*.json")) if is_directory else [input_path]
    if not input_files:
        typer.echo(f"no JSON outcome files found in {input_path}", err=True)
        raise typer.Exit(1)

    valid_count = 0
    failed = False
    last_payload: dict[str, object] | None = None
    valid_payloads: list[dict[str, object]] = []
    for path in input_files:
        label = path.name if is_directory else str(path)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except OSError as exc:
            typer.echo(f"failed to read {label}: {exc}", err=True)
            failed = True
            continue
        except json.JSONDecodeError as exc:
            typer.echo(f"invalid JSON in {label}: {exc}", err=True)
            failed = True
            continue

        if not isinstance(payload, dict):
            typer.echo(f"Invalid discovery RCA outcome: {label}", err=True)
            typer.echo("  - RCA outcome must be one JSON object", err=True)
            failed = True
            continue

        errors = validate_single_school_rca_outcome(payload)
        if errors:
            typer.echo(f"Invalid discovery RCA outcome: {label}", err=True)
            for error in errors:
                typer.echo(f"  - {error}", err=True)
            failed = True
            continue
        valid_count += 1
        last_payload = payload
        valid_payloads.append(payload)

    if failed:
        raise typer.Exit(1)

    batch_plan_item_count: int | None = None
    if batch_plan_path is not None:
        try:
            batch_plan = json.loads(batch_plan_path.read_text(encoding="utf-8"))
        except OSError as exc:
            typer.echo(f"failed to read batch plan {batch_plan_path}: {exc}", err=True)
            raise typer.Exit(1) from exc
        except json.JSONDecodeError as exc:
            typer.echo(f"invalid JSON in batch plan {batch_plan_path}: {exc}", err=True)
            raise typer.Exit(1) from exc
        if not isinstance(batch_plan, dict):
            typer.echo("batch plan must be one JSON object", err=True)
            raise typer.Exit(1)
        coverage_errors = validate_rca_outcome_batch_plan_coverage(valid_payloads, batch_plan)
        if coverage_errors:
            typer.echo("Invalid discovery RCA batch coverage:", err=True)
            for error in coverage_errors:
                typer.echo(f"  - {error}", err=True)
            raise typer.Exit(1)
        items = batch_plan.get("items")
        batch_plan_item_count = len(items) if isinstance(items, list) else 0

    if is_directory:
        message = f"OK discovery RCA outcomes: files={valid_count}"
        if batch_plan_item_count is not None:
            message += f" batch_plan_items={batch_plan_item_count}"
        typer.echo(message)
        return

    assert last_payload is not None
    typer.echo(
        "OK discovery RCA outcome: "
        f"school_id={last_payload['school_id']} "
        f"outcome={last_payload['outcome']} "
        f"layer={last_payload['layer']}"
    )
