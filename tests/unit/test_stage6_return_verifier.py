from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

PACKAGE_SHA = "a" * 64
SOURCE_COMMIT = "b" * 40


def _load_module():
    script = Path(__file__).resolve().parents[2] / "scripts" / "verify_stage6_return.py"
    spec = importlib.util.spec_from_file_location("verify_stage6_return", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def _complete_template() -> str:
    return """# EIDP 業務員 PC E2E 記録テンプレート

| KPI | Target | Actual | 判定 |
| --- | ---: | ---: | --- |
| `ship_readiness_rc` | 0 | 0 | pass |
| strict target PDF 自動取得率 | >= 60% | 67.5 | pass |
| 推定手作業率 | <= 30% | 28.0 | pass |
| Excel ready 率 | >= 60% | 67.5 | pass |
| Excel 整合性 | 100% | 100 | pass |

出力ファイル:

```text
data\\output\\eidp-master.xlsx
```

| 項目 | 結果 |
| --- | --- |
| 監査ログページ表示 | pass |
| manual_action_log 件数 | 12 |
| JSONL outbox 未送信件数 | after flush 0 |
| audit-flush 実行 | pass |
| JSONL action_id 重複 | none |

| 判定項目 | 結果 |
| --- | --- |
| Stage 2-5c Windows VM gate 済み | yes |
| 業務員 PC 1 サイクル完了 | yes |
| KPI owner 承認 | yes |
| Runbook 修正反映済み | yes |
| 残 P0/P1 bug | none |
| OCR scope 決定 | core_non_ocr_only |

結論:

```text
READY
```

Owner sign-off:

```text
Name: Aiko Tanaka
Date: 2026-05-17
Decision: READY
```

業務員 sign-off:

```text
Name: Kenji Sato
Date: 2026-05-17
Decision: READY
```
"""


def _complete_exception_template() -> str:
    return (
        _complete_template()
        .replace("```text\nREADY\n```", "```text\nRC_ONLY\n```")
        .replace("Decision: READY", "Decision: RC_ONLY")
        .replace(
            "| 推定手作業率 | <= 30% | 28.0 | pass |",
            "| 推定手作業率 | <= 30% | 28.0 | pass |\n"
            "| release exception reason | `publication_lag` | publication_lag | pass |\n"
            "| mature-year proof JSON | ok=true | logs/mature-year-proof.json | pass |\n"
            "| mature-year proof years | at least one FY before target_fy | 2025 | pass |",
        )
        .replace("Date: 2026-05-17", "Date: 2026-05-19")
    )


def _write_owner_signoff(
    tmp_path: Path,
    *,
    package_sha: str = PACKAGE_SHA,
    source_commit: str = SOURCE_COMMIT,
    current_release_conclusion: str = "READY",
    decision: str = "READY",
    owner_name: str = "Aiko Tanaka",
    signoff_date: str = "2026-05-17",
    signature: str = "Aiko Tanaka",
) -> Path:
    signoff = tmp_path / "owner-signoff.md"
    signoff.write_text(
        f"""# EIDP Owner Sign-off

| Field | Value |
| --- | --- |
| Package | `dist/eidp-windows-test.zip` |
| SHA256 | `{package_sha}` |
| Source commit | `{source_commit}` |
| Current release conclusion | `{current_release_conclusion}` |

## Sign-off

Owner name: {owner_name}

Date: {signoff_date}

Decision: {decision}

Notes:

Signature: {signature}
""",
        encoding="utf-8",
    )
    return signoff


def _write_complete_artifacts(tmp_path: Path) -> tuple[Path, Path, Path]:
    template = tmp_path / "eidp-operator-e2e-template.md"
    template.write_text(_complete_template(), encoding="utf-8")
    last_run = tmp_path / "last_run.json"
    _write_json(
        last_run,
        {
            "status": "success",
            "finished_at": "2026-05-17T01:02:03+00:00",
            "dry_run": False,
            "current_fy": 2026,
            "school_type": "専門学校",
            "target_pdf_auto_yield_pct": 67.5,
            "operator_reviewable_yield_pct": 72.0,
            "target_pdf_excel_ready_yield_pct": 67.5,
            "ship_gate_status": "pass",
        },
    )
    verify_json = tmp_path / "stage6-evidence-verify.json"
    _write_json(
        verify_json,
        {
            "ok": True,
            "missing_required_labels": [],
            "present_labels": ["build_info", "diagnostics", "last_run", "stage6_recovery", "weekly_run_logs"],
        },
    )
    return template, last_run, verify_json


def _write_mature_year_proof(
    tmp_path: Path,
    *,
    ok: bool = True,
    write_evidence: bool = True,
    evidence_overrides: dict[str, object] | None = None,
    **case_overrides: object,
) -> Path:
    proof = tmp_path / "mature-year-proof.json"
    evidence_path = tmp_path / "logs" / "fy2025-last_run.json"
    case = {
        "fiscal_year": 2025,
        "ok": ok,
        "last_run": "logs/fy2025-last_run.json",
        "finished_at": "2026-05-17T01:02:03+00:00",
        "target_pdf_auto_denominator_count": 1625,
        "target_pdf_auto_denominator_scope": "target_missing_schools_before_run",
        "school_type": "専門学校",
        "target_pdf_auto_yield_pct": 67.5,
        "operator_reviewable_yield_pct": 72.0,
        "ship_gate_status": "pass",
        "results": [
            {"name": "retroactive_weekly_discovery", "returncode": 0},
        ],
    }
    case.update(case_overrides)
    if write_evidence and isinstance(case.get("last_run"), str) and case["last_run"]:
        evidence_path = tmp_path / case["last_run"]
        evidence_path.parent.mkdir(parents=True, exist_ok=True)
        evidence_payload = {
            "status": "success",
            "finished_at": case.get("finished_at"),
            "dry_run": False,
            "current_fy": case.get("fiscal_year"),
            "school_type": case.get("school_type"),
            "target_pdf_auto_denominator_count": case.get("target_pdf_auto_denominator_count"),
            "target_pdf_auto_denominator_scope": case.get("target_pdf_auto_denominator_scope"),
            "target_missing_school_count": case.get("target_pdf_auto_denominator_count"),
            "target_pdf_auto_yield_pct": case.get("target_pdf_auto_yield_pct"),
            "operator_reviewable_yield_pct": case.get("operator_reviewable_yield_pct"),
            "ship_gate_status": case.get("ship_gate_status"),
        }
        if evidence_overrides:
            evidence_payload.update(evidence_overrides)
        evidence_path.write_text(json.dumps(evidence_payload), encoding="utf-8")
    _write_json(
        proof,
        {
            "ok": ok,
            "basis": "mature_year_retroactive_strict_target_pdf_and_operator_reviewable_acquisition",
            "cases": [case],
        },
    )
    return proof


def _write_approved_exception_record(tmp_path: Path, *, decision: str = "APPROVED") -> Path:
    record = tmp_path / "release-exception.md"
    record.write_text(
        f"""# Publication-Lag Release Exception Record

Date: 2026-05-19
Status: `{decision}`

| Field | Value |
| --- | --- |
| Exception reason | `publication_lag` |
| Decision | `{decision}` |
| Approver | Aiko Tanaka |
| Approval date | 2026-05-19 |
| Release scope | v1.0 may ship on mature FY2025 production-scale proof only |
| FY2026/R8 status acknowledged | yes |
| Required follow-up | Re-run FY2026/R8 strict-yield upper-bound proof when R8 target-form publication baseline exists |
""",
        encoding="utf-8",
    )
    return record


def _write_publication_lag_decision_brief(tmp_path: Path, *, body: str | None = None) -> Path:
    brief = tmp_path / "publication-lag.md"
    brief.write_text(
        body
        or """# Publication-lag Owner Decision Brief

It is not approval by itself.

- `APPROVE_RC_ONLY`
- at most `RC_ONLY`
- unconfirmed rows must not enter final Excel output
- successful `scripts/verify_stage6_return.py` result
""",
        encoding="utf-8",
    )
    return brief


def _write_ocr_scope_decision_brief(tmp_path: Path, *, body: str | None = None) -> Path:
    brief = tmp_path / "ocr-scope.md"
    brief.write_text(
        body
        or """# OCR Scope Owner Decision Brief

It is not approval by itself.

- `CORE_TEXT_PDF_ONLY`
- image-only PDFs must be visible as OCR/manual-review work
- `OCR_ADDON_REQUIRED`
- current Windows OCR proof is present
- missing OCR runtime proof remains a release blocker
- unreviewed OCR rows must not enter final Excel output
- With no OCR scope decision: `NOT_READY`
""",
        encoding="utf-8",
    )
    return brief


def test_verify_stage6_return_accepts_completed_owner_artifacts(tmp_path: Path) -> None:
    module = _load_module()
    template, last_run, verify_json = _write_complete_artifacts(tmp_path)

    result = module.verify_stage6_return(
        e2e_template=template,
        last_run=last_run,
        evidence_verify_json=verify_json,
        target_fy=2026,
    )

    assert result["ok"] is True
    assert result["errors"] == []
    assert result["selected_ocr_scope"] == "core_non_ocr_only"
    assert result["inputs"]["ocr_scope_decision_brief"].endswith("docs/release/owner-decisions/ocr-scope.md")


def test_verify_stage6_return_accepts_completed_false_reject_review(tmp_path: Path, monkeypatch) -> None:
    module = _load_module()
    template, last_run, verify_json = _write_complete_artifacts(tmp_path)
    evidence_zip = tmp_path / "stage6-evidence.zip"
    evidence_zip.write_text("fake", encoding="utf-8")
    review_csv = tmp_path / "false-reject-review.csv"
    review_csv.write_text("audit_row_id,decision\nrow-1,correct_reject\n", encoding="utf-8")
    calls: dict[str, object] = {}

    class FakeFalseRejectAudit:
        @staticmethod
        def build_false_reject_audit_packet(
            archive: Path,
            *,
            sample_size: int,
            required_yield_pct: float,
        ) -> dict[str, object]:
            calls["archive"] = archive
            calls["sample_size"] = sample_size
            calls["required_yield_pct"] = required_yield_pct
            return {"ok": True, "errors": [], "strict_yield": {"release_forecast": "NOT_READY"}}

        @staticmethod
        def validate_review_csv(
            packet: dict[str, object],
            csv_text: str,
            *,
            require_decisions: bool,
        ) -> dict[str, object]:
            calls["packet"] = packet
            calls["csv_text"] = csv_text
            calls["require_decisions"] = require_decisions
            return {
                "ok": True,
                "basis": "false_reject_review_decision_validation",
                "review_status": "complete",
                "completed_decisions": 1,
                "context_mismatch_count": 0,
                "errors": [],
            }

    monkeypatch.setattr(module, "_load_false_reject_audit_module", lambda: FakeFalseRejectAudit)

    result = module.verify_stage6_return(
        e2e_template=template,
        last_run=last_run,
        evidence_verify_json=verify_json,
        target_fy=2026,
        false_reject_evidence_zip=evidence_zip,
        false_reject_review_csv=review_csv,
        false_reject_sample_size=12,
    )

    assert result["ok"] is True
    assert result["errors"] == []
    assert result["false_reject_review"]["review_status"] == "complete"
    assert result["inputs"]["false_reject_evidence_zip"] == str(evidence_zip)
    assert result["inputs"]["false_reject_review_csv"] == str(review_csv)
    assert calls["archive"] == evidence_zip
    assert calls["sample_size"] == 12
    assert calls["required_yield_pct"] == 60.0
    assert calls["require_decisions"] is True


def test_verify_stage6_return_rejects_incomplete_false_reject_review(tmp_path: Path, monkeypatch) -> None:
    module = _load_module()
    template, last_run, verify_json = _write_complete_artifacts(tmp_path)
    evidence_zip = tmp_path / "stage6-evidence.zip"
    evidence_zip.write_text("fake", encoding="utf-8")
    review_csv = tmp_path / "false-reject-review.csv"
    review_csv.write_text("audit_row_id,decision\nrow-1,\n", encoding="utf-8")

    class FakeFalseRejectAudit:
        @staticmethod
        def build_false_reject_audit_packet(
            archive: Path,
            *,
            sample_size: int,
            required_yield_pct: float,
        ) -> dict[str, object]:
            return {"ok": True, "errors": [], "strict_yield": {"release_forecast": "NOT_READY"}}

        @staticmethod
        def validate_review_csv(
            packet: dict[str, object],
            csv_text: str,
            *,
            require_decisions: bool,
        ) -> dict[str, object]:
            return {
                "ok": False,
                "basis": "false_reject_review_decision_validation",
                "review_status": "incomplete",
                "completed_decisions": 0,
                "context_mismatch_count": 0,
                "errors": ["line 2: decision is required"],
            }

    monkeypatch.setattr(module, "_load_false_reject_audit_module", lambda: FakeFalseRejectAudit)

    result = module.verify_stage6_return(
        e2e_template=template,
        last_run=last_run,
        evidence_verify_json=verify_json,
        target_fy=2026,
        false_reject_evidence_zip=evidence_zip,
        false_reject_review_csv=review_csv,
    )

    assert result["ok"] is False
    assert result["false_reject_review"]["review_status"] == "incomplete"
    assert "false-reject review CSV is invalid" in result["errors"]
    assert "false-reject review CSV error: line 2: decision is required" in result["errors"]
    incomplete_error = "false-reject review CSV must be complete before it can support owner-return RCA evidence"
    assert incomplete_error in result["errors"]


def test_verify_stage6_return_requires_false_reject_zip_with_review_csv(tmp_path: Path) -> None:
    module = _load_module()
    template, last_run, verify_json = _write_complete_artifacts(tmp_path)
    review_csv = tmp_path / "false-reject-review.csv"
    review_csv.write_text("audit_row_id,decision\nrow-1,correct_reject\n", encoding="utf-8")

    result = module.verify_stage6_return(
        e2e_template=template,
        last_run=last_run,
        evidence_verify_json=verify_json,
        target_fy=2026,
        false_reject_review_csv=review_csv,
    )

    assert result["ok"] is False
    assert "--false-reject-review-csv requires --false-reject-evidence-zip" in result["errors"]


def test_verify_stage6_return_accepts_short_owner_signoff_for_ready_path(tmp_path: Path) -> None:
    module = _load_module()
    template, last_run, verify_json = _write_complete_artifacts(tmp_path)
    owner_signoff = _write_owner_signoff(tmp_path)

    result = module.verify_stage6_return(
        e2e_template=template,
        last_run=last_run,
        evidence_verify_json=verify_json,
        target_fy=2026,
        owner_signoff=owner_signoff,
        expected_package_sha256=PACKAGE_SHA,
        expected_source_commit=SOURCE_COMMIT,
    )

    assert result["ok"] is True
    assert result["errors"] == []
    assert result["inputs"]["owner_signoff"] == str(owner_signoff)
    assert result["inputs"]["expected_package_sha256"] == PACKAGE_SHA
    assert result["inputs"]["expected_source_commit"] == SOURCE_COMMIT


def test_verify_stage6_return_rejects_owner_signoff_package_identity_mismatch(tmp_path: Path) -> None:
    module = _load_module()
    template, last_run, verify_json = _write_complete_artifacts(tmp_path)
    owner_signoff = _write_owner_signoff(tmp_path, package_sha="c" * 64, source_commit="d" * 40)

    result = module.verify_stage6_return(
        e2e_template=template,
        last_run=last_run,
        evidence_verify_json=verify_json,
        target_fy=2026,
        owner_signoff=owner_signoff,
        expected_package_sha256=PACKAGE_SHA,
        expected_source_commit=SOURCE_COMMIT,
    )

    assert result["ok"] is False
    assert (
        f"owner sign-off SHA256 must match expected package SHA256: {'c' * 64} != {PACKAGE_SHA}"
        in result["errors"]
    )
    assert (
        f"owner sign-off Source commit must match expected source commit: {'d' * 40} != {SOURCE_COMMIT}"
        in result["errors"]
    )


def test_verify_stage6_return_rejects_missing_excel_and_audit_proof_rows(tmp_path: Path) -> None:
    module = _load_module()
    template, last_run, verify_json = _write_complete_artifacts(tmp_path)
    template.write_text(
        _complete_template()
        .replace("| Excel ready 率 | >= 60% | 67.5 | pass |\n", "")
        .replace("| Excel 整合性 | 100% | 100 | pass |\n", "")
        .replace(
            """出力ファイル:

```text
data\\output\\eidp-master.xlsx
```

""",
            "",
        )
        .replace(
            """| 項目 | 結果 |
| --- | --- |
| 監査ログページ表示 | pass |
| manual_action_log 件数 | 12 |
| JSONL outbox 未送信件数 | after flush 0 |
| audit-flush 実行 | pass |
| JSONL action_id 重複 | none |

""",
            "",
        ),
        encoding="utf-8",
    )

    result = module.verify_stage6_return(
        e2e_template=template,
        last_run=last_run,
        evidence_verify_json=verify_json,
        target_fy=2026,
    )

    assert result["ok"] is False
    assert "E2E template KPI row missing or malformed: Excel ready 率" in result["errors"]
    assert "E2E template KPI row missing or malformed: Excel 整合性" in result["errors"]
    assert "E2E template Excel output file proof is missing or blank" in result["errors"]
    assert "E2E template audit row missing or malformed: manual_action_log 件数" in result["errors"]
    assert "E2E template audit row missing or malformed: JSONL outbox 未送信件数" in result["errors"]


def test_verify_stage6_return_rejects_invalid_last_run_finished_at(tmp_path: Path) -> None:
    module = _load_module()
    template, last_run, verify_json = _write_complete_artifacts(tmp_path)
    _write_json(
        last_run,
        {
            "status": "success",
            "finished_at": "after weekly run",
            "dry_run": False,
            "current_fy": 2026,
            "school_type": "専門学校",
            "target_pdf_auto_yield_pct": 67.5,
            "operator_reviewable_yield_pct": 72.0,
            "target_pdf_excel_ready_yield_pct": 67.5,
            "ship_gate_status": "pass",
        },
    )

    result = module.verify_stage6_return(
        e2e_template=template,
        last_run=last_run,
        evidence_verify_json=verify_json,
        target_fy=2026,
    )

    assert result["ok"] is False
    assert "last_run finished_at must be ISO datetime" in result["errors"]


def test_verify_stage6_return_rejects_future_last_run_finished_at(tmp_path: Path) -> None:
    module = _load_module()
    template, last_run, verify_json = _write_complete_artifacts(tmp_path)
    _write_json(
        last_run,
        {
            "status": "success",
            "finished_at": "2999-01-01T01:02:03+00:00",
            "dry_run": False,
            "current_fy": 2026,
            "school_type": "専門学校",
            "target_pdf_auto_yield_pct": 67.5,
            "operator_reviewable_yield_pct": 72.0,
            "target_pdf_excel_ready_yield_pct": 67.5,
            "ship_gate_status": "pass",
        },
    )

    result = module.verify_stage6_return(
        e2e_template=template,
        last_run=last_run,
        evidence_verify_json=verify_json,
        target_fy=2026,
    )

    assert result["ok"] is False
    assert "last_run finished_at must not be in the future" in result["errors"]


def test_verify_stage6_return_rejects_excel_output_proof_without_workbook_path(tmp_path: Path) -> None:
    module = _load_module()
    template, last_run, verify_json = _write_complete_artifacts(tmp_path)
    template.write_text(
        _complete_template().replace(
            "data\\output\\eidp-master.xlsx",
            "shared drive upload complete",
        ),
        encoding="utf-8",
    )

    result = module.verify_stage6_return(
        e2e_template=template,
        last_run=last_run,
        evidence_verify_json=verify_json,
        target_fy=2026,
    )

    assert result["ok"] is False
    assert "E2E template Excel output file proof must include a generated data/output/*.xlsx workbook path" in result[
        "errors"
    ]


def test_verify_stage6_return_rejects_sample_workbook_as_excel_output_proof(tmp_path: Path) -> None:
    module = _load_module()
    template, last_run, verify_json = _write_complete_artifacts(tmp_path)
    template.write_text(
        _complete_template().replace(
            "data\\output\\eidp-master.xlsx",
            "sample/20250826更新版_競合校の在校生数.xlsx",
        ),
        encoding="utf-8",
    )

    result = module.verify_stage6_return(
        e2e_template=template,
        last_run=last_run,
        evidence_verify_json=verify_json,
        target_fy=2026,
    )

    assert result["ok"] is False
    assert "E2E template Excel output file proof must include a generated data/output/*.xlsx workbook path" in result[
        "errors"
    ]


def test_verify_stage6_return_cli_emits_json_and_success(tmp_path: Path, capsys) -> None:
    module = _load_module()
    template, last_run, verify_json = _write_complete_artifacts(tmp_path)
    owner_signoff = _write_owner_signoff(tmp_path)

    rc = module.main(
        [
            "--e2e-template",
            str(template),
            "--last-run",
            str(last_run),
            "--evidence-verify-json",
            str(verify_json),
            "--target-fy",
            "2026",
            "--owner-signoff",
            str(owner_signoff),
            "--expected-package-sha256",
            PACKAGE_SHA,
            "--expected-source-commit",
            SOURCE_COMMIT,
            "--json",
        ]
    )

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["inputs"]["min_target_pdf_auto_yield"] == 60.0
    assert payload["inputs"]["max_manual_workload"] == 30.0
    assert payload["inputs"]["owner_signoff"] == str(owner_signoff)
    assert payload["release_conclusions"] == ["READY", "RC_ONLY", "NOT_READY"]


def test_verify_stage6_return_accepts_publication_lag_exception_with_measured_threshold_miss(
    tmp_path: Path,
) -> None:
    module = _load_module()
    template, last_run, verify_json = _write_complete_artifacts(tmp_path)
    mature_year_proof = _write_mature_year_proof(tmp_path)
    exception_record = _write_approved_exception_record(tmp_path)
    template.write_text(
        _complete_exception_template()
        .replace("| `ship_readiness_rc` | 0 | 0 | pass |", "| `ship_readiness_rc` | 0 | 1 | watch |")
        .replace(
            "| strict target PDF 自動取得率 | >= 60% | 67.5 | pass |",
            "| strict target PDF 自動取得率 | >= 60% | 22.0 | watch |",
        )
        .replace(
            "| 推定手作業率 | <= 30% | 28.0 | pass |",
            "| 推定手作業率 | <= 30% | 100.0 | watch |",
        )
        .replace(
            "| Excel ready 率 | >= 60% | 67.5 | pass |",
            "| Excel ready 率 | >= 60% | 22.0 | watch |",
        ),
        encoding="utf-8",
    )
    _write_json(
        last_run,
        {
            "status": "success",
            "finished_at": "2026-05-17T01:02:03+00:00",
            "dry_run": False,
            "current_fy": 2026,
            "school_type": "専門学校",
            "target_pdf_auto_yield_pct": 22.0,
            "operator_reviewable_yield_pct": 0.0,
            "target_pdf_excel_ready_yield_pct": 22.0,
            "ship_gate_status": "below_gate",
        },
    )

    result = module.verify_stage6_return(
        e2e_template=template,
        last_run=last_run,
        evidence_verify_json=verify_json,
        target_fy=2026,
        release_exception_reason="publication_lag",
        mature_year_proof_json=mature_year_proof,
        release_exception_record=exception_record,
    )

    assert result["ok"] is True
    assert result["errors"] == []
    assert result["inputs"]["release_exception_reason"] == "publication_lag"
    assert result["inputs"]["mature_year_proof_json"] == str(mature_year_proof)
    assert result["inputs"]["release_exception_record"] == str(exception_record)
    assert result["mature_year_proof_years"] == [2025]
    assert "publication_lag" in result["release_exception_reasons"]
    assert any("target_pdf_auto_yield_pct below release threshold" in warning for warning in result["warnings"])
    assert any("estimated manual workload above release threshold" in warning for warning in result["warnings"])
    assert any("target_pdf_excel_ready_yield_pct below release threshold" in warning for warning in result["warnings"])
    assert any("accepted KPI verdict watch: strict target PDF 自動取得率" in warning for warning in result["warnings"])


def test_verify_stage6_return_rejects_ready_decision_for_publication_lag_exception(tmp_path: Path) -> None:
    module = _load_module()
    template, last_run, verify_json = _write_complete_artifacts(tmp_path)
    mature_year_proof = _write_mature_year_proof(tmp_path)
    exception_record = _write_approved_exception_record(tmp_path)
    owner_signoff = _write_owner_signoff(
        tmp_path,
        current_release_conclusion="READY",
        decision="READY",
        signoff_date="2026-05-19",
    )
    template.write_text(
        _complete_exception_template()
        .replace("```text\nRC_ONLY\n```", "```text\nREADY\n```")
        .replace("Decision: RC_ONLY", "Decision: READY"),
        encoding="utf-8",
    )

    result = module.verify_stage6_return(
        e2e_template=template,
        last_run=last_run,
        evidence_verify_json=verify_json,
        target_fy=2026,
        release_exception_reason="publication_lag",
        mature_year_proof_json=mature_year_proof,
        release_exception_record=exception_record,
        owner_signoff=owner_signoff,
        expected_package_sha256=PACKAGE_SHA,
        expected_source_commit=SOURCE_COMMIT,
    )

    assert result["ok"] is False
    assert "E2E template release conclusion must be RC_ONLY for the selected release path" in result["errors"]
    assert "E2E template Owner sign-off: Decision must be RC_ONLY for the selected release path" in result["errors"]
    assert "owner sign-off Decision must be RC_ONLY for the selected release path" in result["errors"]


def test_verify_stage6_return_accepts_owner_signoff_for_publication_lag_rc_only_path(tmp_path: Path) -> None:
    module = _load_module()
    template, last_run, verify_json = _write_complete_artifacts(tmp_path)
    mature_year_proof = _write_mature_year_proof(tmp_path)
    exception_record = _write_approved_exception_record(tmp_path)
    owner_signoff = _write_owner_signoff(
        tmp_path,
        current_release_conclusion="RC_ONLY",
        decision="RC_ONLY",
        signoff_date="2026-05-19",
    )
    template.write_text(_complete_exception_template(), encoding="utf-8")

    result = module.verify_stage6_return(
        e2e_template=template,
        last_run=last_run,
        evidence_verify_json=verify_json,
        target_fy=2026,
        release_exception_reason="publication_lag",
        mature_year_proof_json=mature_year_proof,
        release_exception_record=exception_record,
        owner_signoff=owner_signoff,
        expected_package_sha256=PACKAGE_SHA,
        expected_source_commit=SOURCE_COMMIT,
    )

    assert result["ok"] is True
    assert result["errors"] == []
    assert result["inputs"]["owner_signoff"] == str(owner_signoff)


def test_verify_stage6_return_rejects_template_kpi_actual_mismatch_with_last_run_under_exception(
    tmp_path: Path,
) -> None:
    module = _load_module()
    template, last_run, verify_json = _write_complete_artifacts(tmp_path)
    mature_year_proof = _write_mature_year_proof(tmp_path)
    exception_record = _write_approved_exception_record(tmp_path)
    template.write_text(_complete_exception_template(), encoding="utf-8")
    _write_json(
        last_run,
        {
            "status": "success",
            "finished_at": "2026-05-17T01:02:03+00:00",
            "dry_run": False,
            "current_fy": 2026,
            "school_type": "専門学校",
            "target_pdf_auto_yield_pct": 22.0,
            "operator_reviewable_yield_pct": 72.0,
            "target_pdf_excel_ready_yield_pct": 67.5,
            "ship_gate_status": "below_gate",
        },
    )

    result = module.verify_stage6_return(
        e2e_template=template,
        last_run=last_run,
        evidence_verify_json=verify_json,
        target_fy=2026,
        release_exception_reason="publication_lag",
        mature_year_proof_json=mature_year_proof,
        release_exception_record=exception_record,
    )

    assert result["ok"] is False
    assert (
        "E2E template KPI actual must match last_run target_pdf_auto_yield_pct: "
        "strict target PDF 自動取得率 67.5 != 22.0"
    ) in result["errors"]


def test_verify_stage6_return_exception_still_rejects_unmeasured_kpi(tmp_path: Path) -> None:
    module = _load_module()
    template, last_run, verify_json = _write_complete_artifacts(tmp_path)
    mature_year_proof = _write_mature_year_proof(tmp_path)
    exception_record = _write_approved_exception_record(tmp_path)
    template.write_text(_complete_exception_template(), encoding="utf-8")
    _write_json(
        last_run,
        {
            "status": "success",
            "finished_at": "2026-05-17T01:02:03+00:00",
            "dry_run": False,
            "current_fy": 2026,
            "school_type": "専門学校",
            "target_pdf_auto_yield_pct": None,
            "operator_reviewable_yield_pct": None,
            "target_pdf_excel_ready_yield_pct": None,
            "ship_gate_status": "not_measured",
        },
    )

    result = module.verify_stage6_return(
        e2e_template=template,
        last_run=last_run,
        evidence_verify_json=verify_json,
        target_fy=2026,
        release_exception_reason="publication_lag",
        mature_year_proof_json=mature_year_proof,
        release_exception_record=exception_record,
    )

    assert result["ok"] is False
    assert "last_run target_pdf_auto_yield_pct must be numeric for final return evidence" in result["errors"]
    assert "last_run operator_reviewable_yield_pct must be numeric for final return evidence" in result["errors"]
    assert "last_run ship_gate_status must be measured" in result["errors"]


def test_verify_stage6_return_rejects_non_specialty_current_last_run_scope(tmp_path: Path) -> None:
    module = _load_module()
    template, last_run, verify_json = _write_complete_artifacts(tmp_path)
    _write_json(
        last_run,
        {
            "status": "success",
            "finished_at": "2026-05-17T01:02:03+00:00",
            "dry_run": False,
            "current_fy": 2026,
            "school_type": "大学",
            "target_pdf_auto_yield_pct": 67.5,
            "operator_reviewable_yield_pct": 72.0,
            "target_pdf_excel_ready_yield_pct": 67.5,
            "ship_gate_status": "pass",
        },
    )

    result = module.verify_stage6_return(
        e2e_template=template,
        last_run=last_run,
        evidence_verify_json=verify_json,
        target_fy=2026,
    )

    assert result["ok"] is False
    assert "last_run school_type must be 専門学校" in result["errors"]


def test_verify_stage6_return_rejects_mature_year_template_year_mismatch(tmp_path: Path) -> None:
    module = _load_module()
    template, last_run, verify_json = _write_complete_artifacts(tmp_path)
    mature_year_proof = _write_mature_year_proof(tmp_path)
    exception_record = _write_approved_exception_record(tmp_path)
    template.write_text(
        _complete_exception_template().replace(
            "| mature-year proof years | at least one FY before target_fy | 2025 | pass |",
            "| mature-year proof years | at least one FY before target_fy | 2024 | pass |",
        ),
        encoding="utf-8",
    )

    result = module.verify_stage6_return(
        e2e_template=template,
        last_run=last_run,
        evidence_verify_json=verify_json,
        target_fy=2026,
        release_exception_reason="publication_lag",
        mature_year_proof_json=mature_year_proof,
        release_exception_record=exception_record,
    )

    assert result["ok"] is False
    assert (
        "E2E template mature-year proof years must match passing proof JSON years: [2024] != [2025]"
        in result["errors"]
    )


def test_verify_stage6_return_rejects_mature_year_proof_json_filename_mismatch(tmp_path: Path) -> None:
    module = _load_module()
    template, last_run, verify_json = _write_complete_artifacts(tmp_path)
    mature_year_proof = _write_mature_year_proof(tmp_path)
    exception_record = _write_approved_exception_record(tmp_path)
    template.write_text(
        _complete_exception_template().replace(
            "| mature-year proof JSON | ok=true | logs/mature-year-proof.json | pass |",
            "| mature-year proof JSON | ok=true | logs/old-proof.json | pass |",
        ),
        encoding="utf-8",
    )

    result = module.verify_stage6_return(
        e2e_template=template,
        last_run=last_run,
        evidence_verify_json=verify_json,
        target_fy=2026,
        release_exception_reason="publication_lag",
        mature_year_proof_json=mature_year_proof,
        release_exception_record=exception_record,
    )

    assert result["ok"] is False
    assert (
        "E2E template mature-year proof JSON must reference verifier proof JSON file: "
        "logs/old-proof.json does not include mature-year-proof.json"
    ) in result["errors"]


def test_verify_stage6_return_rejects_ship_gate_status_inconsistent_with_operator_coverage(
    tmp_path: Path,
) -> None:
    module = _load_module()
    template, last_run, verify_json = _write_complete_artifacts(tmp_path)
    mature_year_proof = _write_mature_year_proof(tmp_path)
    exception_record = _write_approved_exception_record(tmp_path)
    template.write_text(
        _complete_exception_template()
        .replace("| `ship_readiness_rc` | 0 | 0 | pass |", "| `ship_readiness_rc` | 0 | 1 | watch |")
        .replace(
            "| strict target PDF 自動取得率 | >= 60% | 67.5 | pass |",
            "| strict target PDF 自動取得率 | >= 60% | 22.0 | watch |",
        )
        .replace(
            "| 推定手作業率 | <= 30% | 28.0 | pass |",
            "| 推定手作業率 | <= 30% | 100.0 | watch |",
        )
        .replace(
            "| Excel ready 率 | >= 60% | 67.5 | pass |",
            "| Excel ready 率 | >= 60% | 22.0 | watch |",
        ),
        encoding="utf-8",
    )
    _write_json(
        last_run,
        {
            "status": "success",
            "finished_at": "2026-05-17T01:02:03+00:00",
            "dry_run": False,
            "current_fy": 2026,
            "school_type": "専門学校",
            "target_pdf_auto_yield_pct": 22.0,
            "operator_reviewable_yield_pct": 0.0,
            "target_pdf_excel_ready_yield_pct": 22.0,
            "ship_gate_status": "pass",
        },
    )

    result = module.verify_stage6_return(
        e2e_template=template,
        last_run=last_run,
        evidence_verify_json=verify_json,
        target_fy=2026,
        release_exception_reason="publication_lag",
        mature_year_proof_json=mature_year_proof,
        release_exception_record=exception_record,
    )

    assert result["ok"] is False
    assert (
        "last_run ship_gate_status does not match target_pdf_auto_yield_pct/operator_reviewable_yield_pct: "
        "pass != below_gate"
        in result["errors"]
    )


def test_verify_stage6_return_exception_requires_mature_year_proof(tmp_path: Path) -> None:
    module = _load_module()
    template, last_run, verify_json = _write_complete_artifacts(tmp_path)
    exception_record = _write_approved_exception_record(tmp_path)
    template.write_text(_complete_exception_template(), encoding="utf-8")

    result = module.verify_stage6_return(
        e2e_template=template,
        last_run=last_run,
        evidence_verify_json=verify_json,
        target_fy=2026,
        release_exception_reason="publication_lag",
        release_exception_record=exception_record,
    )

    assert result["ok"] is False
    assert "release exception requires --mature-year-proof-json" in result["errors"]


def test_verify_stage6_return_exception_requires_approved_exception_record(tmp_path: Path) -> None:
    module = _load_module()
    template, last_run, verify_json = _write_complete_artifacts(tmp_path)
    mature_year_proof = _write_mature_year_proof(tmp_path)
    template.write_text(_complete_exception_template(), encoding="utf-8")

    result = module.verify_stage6_return(
        e2e_template=template,
        last_run=last_run,
        evidence_verify_json=verify_json,
        target_fy=2026,
        release_exception_reason="publication_lag",
        mature_year_proof_json=mature_year_proof,
    )

    assert result["ok"] is False
    assert "release exception requires --release-exception-record" in result["errors"]


def test_verify_stage6_return_exception_requires_publication_lag_decision_brief(tmp_path: Path) -> None:
    module = _load_module()
    template, last_run, verify_json = _write_complete_artifacts(tmp_path)
    mature_year_proof = _write_mature_year_proof(tmp_path)
    exception_record = _write_approved_exception_record(tmp_path)
    template.write_text(_complete_exception_template(), encoding="utf-8")

    result = module.verify_stage6_return(
        e2e_template=template,
        last_run=last_run,
        evidence_verify_json=verify_json,
        target_fy=2026,
        release_exception_reason="publication_lag",
        mature_year_proof_json=mature_year_proof,
        release_exception_record=exception_record,
        publication_lag_decision_brief=tmp_path / "missing-publication-lag.md",
    )

    assert result["ok"] is False
    assert any("publication-lag owner decision brief does not exist" in error for error in result["errors"])


def test_verify_stage6_return_exception_rejects_publication_lag_brief_that_relaxes_gate(
    tmp_path: Path,
) -> None:
    module = _load_module()
    template, last_run, verify_json = _write_complete_artifacts(tmp_path)
    mature_year_proof = _write_mature_year_proof(tmp_path)
    exception_record = _write_approved_exception_record(tmp_path)
    decision_brief = _write_publication_lag_decision_brief(
        tmp_path,
        body="""# Publication-lag Owner Decision Brief

It is not approval by itself.

- `APPROVE_RC_ONLY`
- unconfirmed rows must not enter final Excel output
- successful `scripts/verify_stage6_return.py` result
""",
    )
    template.write_text(_complete_exception_template(), encoding="utf-8")

    result = module.verify_stage6_return(
        e2e_template=template,
        last_run=last_run,
        evidence_verify_json=verify_json,
        target_fy=2026,
        release_exception_reason="publication_lag",
        mature_year_proof_json=mature_year_proof,
        release_exception_record=exception_record,
        publication_lag_decision_brief=decision_brief,
    )

    assert result["ok"] is False
    assert "publication-lag owner decision brief missing required marker: at most `RC_ONLY`" in result["errors"]


def test_verify_stage6_return_rejects_ocr_scope_brief_without_selected_scope(tmp_path: Path) -> None:
    module = _load_module()
    template, last_run, verify_json = _write_complete_artifacts(tmp_path)
    ocr_brief = _write_ocr_scope_decision_brief(
        tmp_path,
        body="""# OCR Scope Owner Decision Brief

It is not approval by itself.

- `OCR_ADDON_REQUIRED`
- current Windows OCR proof is present
- unreviewed OCR rows must not enter final Excel output
- With no OCR scope decision: `NOT_READY`
""",
    )

    result = module.verify_stage6_return(
        e2e_template=template,
        last_run=last_run,
        evidence_verify_json=verify_json,
        target_fy=2026,
        ocr_scope_decision_brief=ocr_brief,
    )

    assert result["ok"] is False
    assert (
        "OCR scope owner decision brief missing marker for core_non_ocr_only: `CORE_TEXT_PDF_ONLY`"
        in result["errors"]
    )


def test_verify_stage6_return_exception_rejects_not_approved_exception_record(tmp_path: Path) -> None:
    module = _load_module()
    template, last_run, verify_json = _write_complete_artifacts(tmp_path)
    mature_year_proof = _write_mature_year_proof(tmp_path)
    exception_record = _write_approved_exception_record(tmp_path, decision="NOT_APPROVED")
    template.write_text(_complete_exception_template(), encoding="utf-8")

    result = module.verify_stage6_return(
        e2e_template=template,
        last_run=last_run,
        evidence_verify_json=verify_json,
        target_fy=2026,
        release_exception_reason="publication_lag",
        mature_year_proof_json=mature_year_proof,
        release_exception_record=exception_record,
    )

    assert result["ok"] is False
    assert "release exception record Status must be APPROVED" in result["errors"]
    assert "release exception record Decision must be APPROVED" in result["errors"]


def test_verify_stage6_return_exception_rejects_invalid_approval_date(tmp_path: Path) -> None:
    module = _load_module()
    template, last_run, verify_json = _write_complete_artifacts(tmp_path)
    mature_year_proof = _write_mature_year_proof(tmp_path)
    exception_record = _write_approved_exception_record(tmp_path)
    exception_record.write_text(
        exception_record.read_text(encoding="utf-8").replace(
            "| Approval date | 2026-05-19 |",
            "| Approval date | 2026/05/19 |",
        ),
        encoding="utf-8",
    )
    template.write_text(_complete_exception_template(), encoding="utf-8")

    result = module.verify_stage6_return(
        e2e_template=template,
        last_run=last_run,
        evidence_verify_json=verify_json,
        target_fy=2026,
        release_exception_reason="publication_lag",
        mature_year_proof_json=mature_year_proof,
        release_exception_record=exception_record,
    )

    assert result["ok"] is False
    assert "release exception record Approval date must be YYYY-MM-DD" in result["errors"]


def test_verify_stage6_return_exception_rejects_blank_approval_date(tmp_path: Path) -> None:
    module = _load_module()
    template, last_run, verify_json = _write_complete_artifacts(tmp_path)
    mature_year_proof = _write_mature_year_proof(tmp_path)
    exception_record = _write_approved_exception_record(tmp_path)
    exception_record.write_text(
        exception_record.read_text(encoding="utf-8").replace(
            "| Approval date | 2026-05-19 |",
            "| Approval date |  |",
        ),
        encoding="utf-8",
    )
    template.write_text(_complete_exception_template(), encoding="utf-8")

    result = module.verify_stage6_return(
        e2e_template=template,
        last_run=last_run,
        evidence_verify_json=verify_json,
        target_fy=2026,
        release_exception_reason="publication_lag",
        mature_year_proof_json=mature_year_proof,
        release_exception_record=exception_record,
    )

    assert result["ok"] is False
    assert "release exception record Approval date is required" in result["errors"]


def test_verify_stage6_return_exception_rejects_future_approval_date(tmp_path: Path) -> None:
    module = _load_module()
    template, last_run, verify_json = _write_complete_artifacts(tmp_path)
    mature_year_proof = _write_mature_year_proof(tmp_path)
    exception_record = _write_approved_exception_record(tmp_path)
    exception_record.write_text(
        exception_record.read_text(encoding="utf-8").replace(
            "| Approval date | 2026-05-19 |",
            "| Approval date | 2999-01-01 |",
        ),
        encoding="utf-8",
    )
    template.write_text(_complete_exception_template(), encoding="utf-8")

    result = module.verify_stage6_return(
        e2e_template=template,
        last_run=last_run,
        evidence_verify_json=verify_json,
        target_fy=2026,
        release_exception_reason="publication_lag",
        mature_year_proof_json=mature_year_proof,
        release_exception_record=exception_record,
    )

    assert result["ok"] is False
    assert "release exception record Approval date must not be in the future" in result["errors"]


def test_verify_stage6_return_exception_rejects_missing_record_date(tmp_path: Path) -> None:
    module = _load_module()
    template, last_run, verify_json = _write_complete_artifacts(tmp_path)
    mature_year_proof = _write_mature_year_proof(tmp_path)
    exception_record = _write_approved_exception_record(tmp_path)
    exception_record.write_text(
        exception_record.read_text(encoding="utf-8").replace("Date: 2026-05-19\n", ""),
        encoding="utf-8",
    )
    template.write_text(_complete_exception_template(), encoding="utf-8")

    result = module.verify_stage6_return(
        e2e_template=template,
        last_run=last_run,
        evidence_verify_json=verify_json,
        target_fy=2026,
        release_exception_reason="publication_lag",
        mature_year_proof_json=mature_year_proof,
        release_exception_record=exception_record,
    )

    assert result["ok"] is False
    assert "release exception record Date is required" in result["errors"]


def test_verify_stage6_return_exception_rejects_invalid_record_date(tmp_path: Path) -> None:
    module = _load_module()
    template, last_run, verify_json = _write_complete_artifacts(tmp_path)
    mature_year_proof = _write_mature_year_proof(tmp_path)
    exception_record = _write_approved_exception_record(tmp_path)
    exception_record.write_text(
        exception_record.read_text(encoding="utf-8").replace(
            "Date: 2026-05-19",
            "Date: 2026/05/19",
        ),
        encoding="utf-8",
    )
    template.write_text(_complete_exception_template(), encoding="utf-8")

    result = module.verify_stage6_return(
        e2e_template=template,
        last_run=last_run,
        evidence_verify_json=verify_json,
        target_fy=2026,
        release_exception_reason="publication_lag",
        mature_year_proof_json=mature_year_proof,
        release_exception_record=exception_record,
    )

    assert result["ok"] is False
    assert "release exception record Date must be YYYY-MM-DD" in result["errors"]


def test_verify_stage6_return_exception_rejects_future_record_date(tmp_path: Path) -> None:
    module = _load_module()
    template, last_run, verify_json = _write_complete_artifacts(tmp_path)
    mature_year_proof = _write_mature_year_proof(tmp_path)
    exception_record = _write_approved_exception_record(tmp_path)
    exception_record.write_text(
        exception_record.read_text(encoding="utf-8").replace(
            "Date: 2026-05-19",
            "Date: 2999-01-01",
        ),
        encoding="utf-8",
    )
    template.write_text(_complete_exception_template(), encoding="utf-8")

    result = module.verify_stage6_return(
        e2e_template=template,
        last_run=last_run,
        evidence_verify_json=verify_json,
        target_fy=2026,
        release_exception_reason="publication_lag",
        mature_year_proof_json=mature_year_proof,
        release_exception_record=exception_record,
    )

    assert result["ok"] is False
    assert "release exception record Date must not be in the future" in result["errors"]
    assert "release exception record Date must match Approval date" not in result["errors"]


def test_verify_stage6_return_exception_rejects_record_date_mismatch(tmp_path: Path) -> None:
    module = _load_module()
    template, last_run, verify_json = _write_complete_artifacts(tmp_path)
    mature_year_proof = _write_mature_year_proof(tmp_path)
    exception_record = _write_approved_exception_record(tmp_path)
    exception_record.write_text(
        exception_record.read_text(encoding="utf-8").replace(
            "Date: 2026-05-19",
            "Date: 2026-05-18",
        ),
        encoding="utf-8",
    )
    template.write_text(_complete_exception_template(), encoding="utf-8")

    result = module.verify_stage6_return(
        e2e_template=template,
        last_run=last_run,
        evidence_verify_json=verify_json,
        target_fy=2026,
        release_exception_reason="publication_lag",
        mature_year_proof_json=mature_year_proof,
        release_exception_record=exception_record,
    )

    assert result["ok"] is False
    assert "release exception record Date must match Approval date" in result["errors"]


def test_verify_stage6_return_exception_rejects_placeholder_approver(tmp_path: Path) -> None:
    module = _load_module()
    template, last_run, verify_json = _write_complete_artifacts(tmp_path)
    mature_year_proof = _write_mature_year_proof(tmp_path)
    exception_record = _write_approved_exception_record(tmp_path)
    exception_record.write_text(
        exception_record.read_text(encoding="utf-8").replace(
            "| Approver | Aiko Tanaka |",
            "| Approver | Example Owner |",
        ),
        encoding="utf-8",
    )
    template.write_text(_complete_exception_template(), encoding="utf-8")

    result = module.verify_stage6_return(
        e2e_template=template,
        last_run=last_run,
        evidence_verify_json=verify_json,
        target_fy=2026,
        release_exception_reason="publication_lag",
        mature_year_proof_json=mature_year_proof,
        release_exception_record=exception_record,
    )

    assert result["ok"] is False
    assert "release exception record Approver must not be a placeholder" in result["errors"]


def test_verify_stage6_return_exception_rejects_shorthand_placeholder_approver(tmp_path: Path) -> None:
    module = _load_module()
    template, last_run, verify_json = _write_complete_artifacts(tmp_path)
    mature_year_proof = _write_mature_year_proof(tmp_path)
    exception_record = _write_approved_exception_record(tmp_path)
    exception_record.write_text(
        exception_record.read_text(encoding="utf-8").replace(
            "| Approver | Aiko Tanaka |",
            "| Approver | N/A |",
        ),
        encoding="utf-8",
    )
    template.write_text(_complete_exception_template(), encoding="utf-8")

    result = module.verify_stage6_return(
        e2e_template=template,
        last_run=last_run,
        evidence_verify_json=verify_json,
        target_fy=2026,
        release_exception_reason="publication_lag",
        mature_year_proof_json=mature_year_proof,
        release_exception_record=exception_record,
    )

    assert result["ok"] is False
    assert "release exception record Approver must not be a placeholder" in result["errors"]


def test_verify_stage6_return_exception_rejects_signoff_dates_before_approval(
    tmp_path: Path,
) -> None:
    module = _load_module()
    template, last_run, verify_json = _write_complete_artifacts(tmp_path)
    mature_year_proof = _write_mature_year_proof(tmp_path)
    exception_record = _write_approved_exception_record(tmp_path)
    template.write_text(
        _complete_exception_template().replace("Date: 2026-05-19", "Date: 2026-05-18"),
        encoding="utf-8",
    )

    result = module.verify_stage6_return(
        e2e_template=template,
        last_run=last_run,
        evidence_verify_json=verify_json,
        target_fy=2026,
        release_exception_reason="publication_lag",
        mature_year_proof_json=mature_year_proof,
        release_exception_record=exception_record,
    )

    assert result["ok"] is False
    assert (
        "E2E template Owner sign-off: Date must be on or after release exception Approval date"
        in result["errors"]
    )
    assert (
        "E2E template 業務員 sign-off: Date must be on or after release exception Approval date"
        in result["errors"]
    )


def test_verify_stage6_return_exception_rejects_approval_date_before_last_run(
    tmp_path: Path,
) -> None:
    module = _load_module()
    template, last_run, verify_json = _write_complete_artifacts(tmp_path)
    mature_year_proof = _write_mature_year_proof(tmp_path)
    exception_record = _write_approved_exception_record(tmp_path)
    template.write_text(
        _complete_exception_template().replace("Date: 2026-05-19", "Date: 2026-05-20"),
        encoding="utf-8",
    )
    _write_json(
        last_run,
        {
            "status": "success",
            "finished_at": "2026-05-20T01:02:03+00:00",
            "dry_run": False,
            "current_fy": 2026,
            "school_type": "専門学校",
            "target_pdf_auto_yield_pct": 67.5,
            "operator_reviewable_yield_pct": 72.0,
            "target_pdf_excel_ready_yield_pct": 67.5,
            "ship_gate_status": "pass",
        },
    )

    result = module.verify_stage6_return(
        e2e_template=template,
        last_run=last_run,
        evidence_verify_json=verify_json,
        target_fy=2026,
        release_exception_reason="publication_lag",
        mature_year_proof_json=mature_year_proof,
        release_exception_record=exception_record,
    )

    assert result["ok"] is False
    assert "release exception record Approval date must be on or after last_run finished_at date" in result[
        "errors"
    ]
    assert not any("Date must be on or after last_run finished_at date" in error for error in result["errors"])


def test_verify_stage6_return_exception_rejects_approval_date_before_mature_year_proof(
    tmp_path: Path,
) -> None:
    module = _load_module()
    template, last_run, verify_json = _write_complete_artifacts(tmp_path)
    mature_year_proof = _write_mature_year_proof(
        tmp_path,
        finished_at="2026-05-20T01:02:03+00:00",
    )
    exception_record = _write_approved_exception_record(tmp_path)
    template.write_text(_complete_exception_template(), encoding="utf-8")

    result = module.verify_stage6_return(
        e2e_template=template,
        last_run=last_run,
        evidence_verify_json=verify_json,
        target_fy=2026,
        release_exception_reason="publication_lag",
        mature_year_proof_json=mature_year_proof,
        release_exception_record=exception_record,
    )

    assert result["ok"] is False
    assert (
        "release exception record Approval date must be on or after mature-year proof finished_at date"
        in result["errors"]
    )


def test_verify_stage6_return_rejects_invalid_mature_year_proof_finished_at(tmp_path: Path) -> None:
    module = _load_module()
    template, last_run, verify_json = _write_complete_artifacts(tmp_path)
    mature_year_proof = _write_mature_year_proof(tmp_path, finished_at="after retroactive proof")
    exception_record = _write_approved_exception_record(tmp_path)
    template.write_text(_complete_exception_template(), encoding="utf-8")

    result = module.verify_stage6_return(
        e2e_template=template,
        last_run=last_run,
        evidence_verify_json=verify_json,
        target_fy=2026,
        release_exception_reason="publication_lag",
        mature_year_proof_json=mature_year_proof,
        release_exception_record=exception_record,
    )

    assert result["ok"] is False
    assert "mature-year proof case FY2025 finished_at must be ISO datetime" in result["errors"]
    assert "mature-year proof JSON must include at least one passing fiscal year before target_fy" in result[
        "errors"
    ]


def test_verify_stage6_return_rejects_missing_mature_year_proof_finished_at(tmp_path: Path) -> None:
    module = _load_module()
    template, last_run, verify_json = _write_complete_artifacts(tmp_path)
    mature_year_proof = _write_mature_year_proof(tmp_path, finished_at="")
    exception_record = _write_approved_exception_record(tmp_path)
    template.write_text(_complete_exception_template(), encoding="utf-8")

    result = module.verify_stage6_return(
        e2e_template=template,
        last_run=last_run,
        evidence_verify_json=verify_json,
        target_fy=2026,
        release_exception_reason="publication_lag",
        mature_year_proof_json=mature_year_proof,
        release_exception_record=exception_record,
    )

    assert result["ok"] is False
    assert "mature-year proof case FY2025 finished_at is required" in result["errors"]
    assert "mature-year proof JSON must include at least one passing fiscal year before target_fy" in result[
        "errors"
    ]


def test_verify_stage6_return_rejects_non_integer_mature_year_proof_fiscal_year(tmp_path: Path) -> None:
    module = _load_module()
    template, last_run, verify_json = _write_complete_artifacts(tmp_path)
    mature_year_proof = _write_mature_year_proof(tmp_path, fiscal_year=2025.9)
    exception_record = _write_approved_exception_record(tmp_path)
    template.write_text(_complete_exception_template(), encoding="utf-8")

    result = module.verify_stage6_return(
        e2e_template=template,
        last_run=last_run,
        evidence_verify_json=verify_json,
        target_fy=2026,
        release_exception_reason="publication_lag",
        mature_year_proof_json=mature_year_proof,
        release_exception_record=exception_record,
    )

    assert result["ok"] is False
    assert "mature-year proof case fiscal_year must be an integer: 2025.9" in result["errors"]
    assert "mature-year proof JSON must include at least one passing fiscal year before target_fy" in result[
        "errors"
    ]


def test_verify_stage6_return_rejects_missing_mature_year_proof_evidence_source(tmp_path: Path) -> None:
    module = _load_module()
    template, last_run, verify_json = _write_complete_artifacts(tmp_path)
    mature_year_proof = _write_mature_year_proof(tmp_path, last_run="")
    exception_record = _write_approved_exception_record(tmp_path)
    template.write_text(_complete_exception_template(), encoding="utf-8")

    result = module.verify_stage6_return(
        e2e_template=template,
        last_run=last_run,
        evidence_verify_json=verify_json,
        target_fy=2026,
        release_exception_reason="publication_lag",
        mature_year_proof_json=mature_year_proof,
        release_exception_record=exception_record,
    )

    assert result["ok"] is False
    assert "mature-year proof case FY2025 evidence source is required" in result["errors"]
    assert "mature-year proof JSON must include at least one passing fiscal year before target_fy" in result[
        "errors"
    ]


def test_verify_stage6_return_rejects_unknown_mature_year_proof_evidence_source(tmp_path: Path) -> None:
    module = _load_module()
    template, last_run, verify_json = _write_complete_artifacts(tmp_path)
    mature_year_proof = _write_mature_year_proof(tmp_path, evidence_source="manual_note")
    exception_record = _write_approved_exception_record(tmp_path)
    template.write_text(_complete_exception_template(), encoding="utf-8")

    result = module.verify_stage6_return(
        e2e_template=template,
        last_run=last_run,
        evidence_verify_json=verify_json,
        target_fy=2026,
        release_exception_reason="publication_lag",
        mature_year_proof_json=mature_year_proof,
        release_exception_record=exception_record,
    )

    assert result["ok"] is False
    assert (
        "mature-year proof case FY2025 evidence source must be last_run or strict_gap_analysis"
        in result["errors"]
    )
    assert "mature-year proof JSON must include at least one passing fiscal year before target_fy" in result[
        "errors"
    ]


def test_verify_stage6_return_rejects_missing_last_run_mature_year_proof_evidence_file(tmp_path: Path) -> None:
    module = _load_module()
    template, last_run, verify_json = _write_complete_artifacts(tmp_path)
    mature_year_proof = _write_mature_year_proof(
        tmp_path,
        write_evidence=False,
        last_run="logs/missing-last_run.json",
    )
    exception_record = _write_approved_exception_record(tmp_path)
    template.write_text(_complete_exception_template(), encoding="utf-8")

    result = module.verify_stage6_return(
        e2e_template=template,
        last_run=last_run,
        evidence_verify_json=verify_json,
        target_fy=2026,
        release_exception_reason="publication_lag",
        mature_year_proof_json=mature_year_proof,
        release_exception_record=exception_record,
    )

    assert result["ok"] is False
    assert (
        "mature-year proof case FY2025 last_run evidence path does not exist: logs/missing-last_run.json"
        in result["errors"]
    )
    assert "mature-year proof JSON must include at least one passing fiscal year before target_fy" in result[
        "errors"
    ]


def test_verify_stage6_return_rejects_mature_year_proof_metric_mismatch_with_last_run_evidence(
    tmp_path: Path,
) -> None:
    module = _load_module()
    template, last_run, verify_json = _write_complete_artifacts(tmp_path)
    mature_year_proof = _write_mature_year_proof(
        tmp_path,
        evidence_overrides={"target_pdf_auto_yield_pct": 12.0},
    )
    exception_record = _write_approved_exception_record(tmp_path)
    template.write_text(_complete_exception_template(), encoding="utf-8")

    result = module.verify_stage6_return(
        e2e_template=template,
        last_run=last_run,
        evidence_verify_json=verify_json,
        target_fy=2026,
        release_exception_reason="publication_lag",
        mature_year_proof_json=mature_year_proof,
        release_exception_record=exception_record,
    )

    assert result["ok"] is False
    assert (
        "mature-year proof case FY2025 target_pdf_auto_yield_pct must match last_run evidence: 67.5 != 12.0"
        in result["errors"]
    )
    assert "mature-year proof JSON must include at least one passing fiscal year before target_fy" in result[
        "errors"
    ]


def test_verify_stage6_return_rejects_non_specialty_mature_year_last_run_proof_scope(
    tmp_path: Path,
) -> None:
    module = _load_module()
    template, last_run, verify_json = _write_complete_artifacts(tmp_path)
    mature_year_proof = _write_mature_year_proof(
        tmp_path,
        school_type="大学",
        evidence_overrides={"school_type": "大学"},
    )
    exception_record = _write_approved_exception_record(tmp_path)
    template.write_text(_complete_exception_template(), encoding="utf-8")

    result = module.verify_stage6_return(
        e2e_template=template,
        last_run=last_run,
        evidence_verify_json=verify_json,
        target_fy=2026,
        release_exception_reason="publication_lag",
        mature_year_proof_json=mature_year_proof,
        release_exception_record=exception_record,
    )

    assert result["ok"] is False
    assert "mature-year proof case FY2025 last_run evidence school_type must be 専門学校" in result["errors"]
    assert "mature-year proof case FY2025 school_type must be 専門学校: '大学'" in result["errors"]
    assert "mature-year proof JSON must include at least one passing fiscal year before target_fy" in result[
        "errors"
    ]


def test_verify_stage6_return_rejects_mature_year_proof_metric_mismatch_with_strict_gap_evidence(
    tmp_path: Path,
) -> None:
    module = _load_module()
    template, last_run, verify_json = _write_complete_artifacts(tmp_path)
    strict_gap_path = tmp_path / "logs" / "strict-gap-analysis.json"
    strict_gap_path.parent.mkdir(parents=True, exist_ok=True)
    _write_json(
        strict_gap_path,
        {
            "basis": "strict_yield_gap_analysis",
            "fiscal_year": 2025,
            "school_type": "専門学校",
            "finished_at": "2026-05-17T01:02:03+00:00",
            "schools_total": 1000,
            "strict_target_parsed_schools": 120,
            "strict_target_parsed_rate_pct": 12.0,
            "excel_ready_schools": 675,
            "excel_ready_rate_pct": 67.5,
            "operator_reviewable_schools": 720,
            "operator_reviewable_rate_pct": 72.0,
            "estimated_manual_workload_rate_pct": 28.0,
        },
    )
    proof = tmp_path / "mature-year-proof.json"
    _write_json(
        proof,
        {
            "ok": True,
            "basis": "mature_year_retroactive_strict_target_pdf_and_operator_reviewable_acquisition",
            "cases": [
                {
                    "fiscal_year": 2025,
                    "ok": True,
                    "evidence_source": "strict_gap_analysis",
                    "strict_gap_analysis": "logs/strict-gap-analysis.json",
                    "school_type": "専門学校",
                    "finished_at": "2026-05-17T01:02:03+00:00",
                    "target_pdf_auto_denominator_count": 1000,
                    "target_pdf_auto_denominator_scope": "target_missing_schools_before_run",
                    "target_pdf_auto_yield_pct": 67.5,
                    "excel_ready_yield_pct": 67.5,
                    "operator_reviewable_yield_pct": 72.0,
                    "ship_gate_status": "pass",
                }
            ],
        },
    )
    exception_record = _write_approved_exception_record(tmp_path)
    template.write_text(_complete_exception_template(), encoding="utf-8")

    result = module.verify_stage6_return(
        e2e_template=template,
        last_run=last_run,
        evidence_verify_json=verify_json,
        target_fy=2026,
        release_exception_reason="publication_lag",
        mature_year_proof_json=proof,
        release_exception_record=exception_record,
    )

    assert result["ok"] is False
    assert (
        "mature-year proof case FY2025 target_pdf_auto_yield_pct/strict_target_parsed_rate_pct "
        "must match strict_gap_analysis evidence: 67.5 != 12.0"
    ) in result["errors"]
    assert "mature-year proof JSON must include at least one passing fiscal year before target_fy" in result[
        "errors"
    ]


def test_verify_stage6_return_rejects_strict_gap_evidence_rate_mismatch_with_counts(
    tmp_path: Path,
) -> None:
    module = _load_module()
    template, last_run, verify_json = _write_complete_artifacts(tmp_path)
    strict_gap_path = tmp_path / "logs" / "strict-gap-analysis.json"
    strict_gap_path.parent.mkdir(parents=True, exist_ok=True)
    _write_json(
        strict_gap_path,
        {
            "basis": "strict_yield_gap_analysis",
            "fiscal_year": 2025,
            "school_type": "専門学校",
            "finished_at": "2026-05-17T01:02:03+00:00",
            "schools_total": 1000,
            "strict_target_parsed_schools": 600,
            "strict_target_parsed_rate_pct": 67.5,
            "excel_ready_schools": 675,
            "excel_ready_rate_pct": 67.5,
            "operator_reviewable_schools": 720,
            "operator_reviewable_rate_pct": 72.0,
            "estimated_manual_workload_rate_pct": 28.0,
        },
    )
    proof = tmp_path / "mature-year-proof.json"
    _write_json(
        proof,
        {
            "ok": True,
            "basis": "mature_year_retroactive_strict_target_pdf_and_operator_reviewable_acquisition",
            "cases": [
                {
                    "fiscal_year": 2025,
                    "ok": True,
                    "evidence_source": "strict_gap_analysis",
                    "strict_gap_analysis": "logs/strict-gap-analysis.json",
                    "school_type": "専門学校",
                    "finished_at": "2026-05-17T01:02:03+00:00",
                    "target_pdf_auto_denominator_count": 1000,
                    "target_pdf_auto_denominator_scope": "target_missing_schools_before_run",
                    "target_pdf_auto_yield_pct": 67.5,
                    "excel_ready_yield_pct": 67.5,
                    "operator_reviewable_yield_pct": 72.0,
                    "ship_gate_status": "pass",
                }
            ],
        },
    )
    exception_record = _write_approved_exception_record(tmp_path)
    template.write_text(_complete_exception_template(), encoding="utf-8")

    result = module.verify_stage6_return(
        e2e_template=template,
        last_run=last_run,
        evidence_verify_json=verify_json,
        target_fy=2026,
        release_exception_reason="publication_lag",
        mature_year_proof_json=proof,
        release_exception_record=exception_record,
    )

    assert result["ok"] is False
    assert (
        "mature-year proof case FY2025 strict_gap_analysis evidence strict_target_parsed_rate_pct "
        "must match strict_target_parsed_schools/schools_total: 67.5 != 60.0"
    ) in result["errors"]
    assert "mature-year proof JSON must include at least one passing fiscal year before target_fy" in result[
        "errors"
    ]


def test_verify_stage6_return_rejects_strict_gap_mature_year_proof_for_non_specialty_school_scope(
    tmp_path: Path,
) -> None:
    module = _load_module()
    template, last_run, verify_json = _write_complete_artifacts(tmp_path)
    strict_gap_path = tmp_path / "logs" / "strict-gap-analysis.json"
    strict_gap_path.parent.mkdir(parents=True, exist_ok=True)
    _write_json(
        strict_gap_path,
        {
            "basis": "strict_yield_gap_analysis",
            "fiscal_year": 2025,
            "school_type": "大学",
            "finished_at": "2026-05-17T01:02:03+00:00",
            "schools_total": 1000,
            "strict_target_parsed_schools": 675,
            "strict_target_parsed_rate_pct": 67.5,
            "excel_ready_schools": 675,
            "excel_ready_rate_pct": 67.5,
            "operator_reviewable_schools": 720,
            "operator_reviewable_rate_pct": 72.0,
            "estimated_manual_workload_rate_pct": 28.0,
        },
    )
    proof = tmp_path / "mature-year-proof.json"
    _write_json(
        proof,
        {
            "ok": True,
            "basis": "mature_year_retroactive_strict_target_pdf_and_operator_reviewable_acquisition",
            "cases": [
                {
                    "fiscal_year": 2025,
                    "ok": True,
                    "evidence_source": "strict_gap_analysis",
                    "strict_gap_analysis": "logs/strict-gap-analysis.json",
                    "school_type": "大学",
                    "finished_at": "2026-05-17T01:02:03+00:00",
                    "target_pdf_auto_denominator_count": 1000,
                    "target_pdf_auto_denominator_scope": "target_missing_schools_before_run",
                    "target_pdf_auto_yield_pct": 67.5,
                    "excel_ready_yield_pct": 67.5,
                    "operator_reviewable_yield_pct": 72.0,
                    "ship_gate_status": "pass",
                }
            ],
        },
    )
    exception_record = _write_approved_exception_record(tmp_path)
    template.write_text(_complete_exception_template(), encoding="utf-8")

    result = module.verify_stage6_return(
        e2e_template=template,
        last_run=last_run,
        evidence_verify_json=verify_json,
        target_fy=2026,
        release_exception_reason="publication_lag",
        mature_year_proof_json=proof,
        release_exception_record=exception_record,
    )

    assert result["ok"] is False
    assert (
        "mature-year proof case FY2025 strict_gap_analysis evidence school_type must be 専門学校"
        in result["errors"]
    )
    assert "mature-year proof case FY2025 school_type must be 専門学校: '大学'" in result["errors"]
    assert "mature-year proof JSON must include at least one passing fiscal year before target_fy" in result[
        "errors"
    ]


def test_verify_stage6_return_rejects_strict_gap_mature_year_proof_without_excel_ready_yield(
    tmp_path: Path,
) -> None:
    module = _load_module()
    template, last_run, verify_json = _write_complete_artifacts(tmp_path)
    strict_gap_path = tmp_path / "logs" / "strict-gap-analysis.json"
    strict_gap_path.parent.mkdir(parents=True, exist_ok=True)
    _write_json(
        strict_gap_path,
        {
            "basis": "strict_yield_gap_analysis",
            "fiscal_year": 2025,
            "school_type": "専門学校",
            "finished_at": "2026-05-17T01:02:03+00:00",
            "schools_total": 1000,
            "strict_target_parsed_schools": 675,
            "strict_target_parsed_rate_pct": 67.5,
            "excel_ready_schools": 675,
            "excel_ready_rate_pct": 67.5,
            "operator_reviewable_schools": 720,
            "operator_reviewable_rate_pct": 72.0,
            "estimated_manual_workload_rate_pct": 28.0,
        },
    )
    proof = tmp_path / "mature-year-proof.json"
    _write_json(
        proof,
        {
            "ok": True,
            "basis": "mature_year_retroactive_strict_target_pdf_and_operator_reviewable_acquisition",
            "cases": [
                {
                    "fiscal_year": 2025,
                    "ok": True,
                    "evidence_source": "strict_gap_analysis",
                    "strict_gap_analysis": "logs/strict-gap-analysis.json",
                    "school_type": "専門学校",
                    "finished_at": "2026-05-17T01:02:03+00:00",
                    "target_pdf_auto_denominator_count": 1000,
                    "target_pdf_auto_denominator_scope": "target_missing_schools_before_run",
                    "target_pdf_auto_yield_pct": 67.5,
                    "operator_reviewable_yield_pct": 72.0,
                    "ship_gate_status": "pass",
                }
            ],
        },
    )
    exception_record = _write_approved_exception_record(tmp_path)
    template.write_text(_complete_exception_template(), encoding="utf-8")

    result = module.verify_stage6_return(
        e2e_template=template,
        last_run=last_run,
        evidence_verify_json=verify_json,
        target_fy=2026,
        release_exception_reason="publication_lag",
        mature_year_proof_json=proof,
        release_exception_record=exception_record,
    )

    assert result["ok"] is False
    assert "mature-year proof case FY2025 excel_ready_yield_pct must be numeric" in result["errors"]
    assert (
        "mature-year proof case FY2025 excel_ready_yield_pct/excel_ready_rate_pct "
        "must match strict_gap_analysis evidence: None != 67.5"
    ) in result["errors"]
    assert "mature-year proof JSON must include at least one passing fiscal year before target_fy" in result[
        "errors"
    ]


def test_verify_stage6_return_rejects_low_strict_gap_mature_year_excel_ready_yield(
    tmp_path: Path,
) -> None:
    module = _load_module()
    template, last_run, verify_json = _write_complete_artifacts(tmp_path)
    strict_gap_path = tmp_path / "logs" / "strict-gap-analysis.json"
    strict_gap_path.parent.mkdir(parents=True, exist_ok=True)
    _write_json(
        strict_gap_path,
        {
            "basis": "strict_yield_gap_analysis",
            "fiscal_year": 2025,
            "school_type": "専門学校",
            "finished_at": "2026-05-17T01:02:03+00:00",
            "schools_total": 1000,
            "strict_target_parsed_schools": 675,
            "strict_target_parsed_rate_pct": 67.5,
            "excel_ready_schools": 599,
            "excel_ready_rate_pct": 59.9,
            "operator_reviewable_schools": 720,
            "operator_reviewable_rate_pct": 72.0,
            "estimated_manual_workload_rate_pct": 28.0,
        },
    )
    proof = tmp_path / "mature-year-proof.json"
    _write_json(
        proof,
        {
            "ok": True,
            "basis": "mature_year_retroactive_strict_target_pdf_and_operator_reviewable_acquisition",
            "cases": [
                {
                    "fiscal_year": 2025,
                    "ok": True,
                    "evidence_source": "strict_gap_analysis",
                    "strict_gap_analysis": "logs/strict-gap-analysis.json",
                    "school_type": "専門学校",
                    "finished_at": "2026-05-17T01:02:03+00:00",
                    "target_pdf_auto_denominator_count": 1000,
                    "target_pdf_auto_denominator_scope": "target_missing_schools_before_run",
                    "target_pdf_auto_yield_pct": 67.5,
                    "excel_ready_yield_pct": 59.9,
                    "operator_reviewable_yield_pct": 72.0,
                    "ship_gate_status": "pass",
                }
            ],
        },
    )
    exception_record = _write_approved_exception_record(tmp_path)
    template.write_text(_complete_exception_template(), encoding="utf-8")

    result = module.verify_stage6_return(
        e2e_template=template,
        last_run=last_run,
        evidence_verify_json=verify_json,
        target_fy=2026,
        release_exception_reason="publication_lag",
        mature_year_proof_json=proof,
        release_exception_record=exception_record,
    )

    assert result["ok"] is False
    assert (
        "mature-year proof case FY2025 excel_ready_yield_pct below release threshold: 59.9 < 60.0"
        in result["errors"]
    )
    assert "mature-year proof JSON must include at least one passing fiscal year before target_fy" in result[
        "errors"
    ]


def test_verify_stage6_return_rejects_missing_strict_gap_mature_year_proof_evidence_file(
    tmp_path: Path,
) -> None:
    module = _load_module()
    template, last_run, verify_json = _write_complete_artifacts(tmp_path)
    mature_year_proof = _write_mature_year_proof(
        tmp_path,
        evidence_source="strict_gap_analysis",
        last_run="",
        strict_gap_analysis="logs/missing-strict-gap.json",
    )
    exception_record = _write_approved_exception_record(tmp_path)
    template.write_text(_complete_exception_template(), encoding="utf-8")

    result = module.verify_stage6_return(
        e2e_template=template,
        last_run=last_run,
        evidence_verify_json=verify_json,
        target_fy=2026,
        release_exception_reason="publication_lag",
        mature_year_proof_json=mature_year_proof,
        release_exception_record=exception_record,
    )

    assert result["ok"] is False
    assert (
        "mature-year proof case FY2025 strict_gap_analysis evidence path does not exist: "
        "logs/missing-strict-gap.json"
    ) in result["errors"]
    assert "mature-year proof JSON must include at least one passing fiscal year before target_fy" in result[
        "errors"
    ]


def test_verify_stage6_return_rejects_future_mature_year_proof_finished_at(tmp_path: Path) -> None:
    module = _load_module()
    template, last_run, verify_json = _write_complete_artifacts(tmp_path)
    mature_year_proof = _write_mature_year_proof(tmp_path, finished_at="2999-01-01T01:02:03+00:00")
    exception_record = _write_approved_exception_record(tmp_path)
    template.write_text(_complete_exception_template(), encoding="utf-8")

    result = module.verify_stage6_return(
        e2e_template=template,
        last_run=last_run,
        evidence_verify_json=verify_json,
        target_fy=2026,
        release_exception_reason="publication_lag",
        mature_year_proof_json=mature_year_proof,
        release_exception_record=exception_record,
    )

    assert result["ok"] is False
    assert "mature-year proof case FY2025 finished_at must not be in the future" in result["errors"]
    assert "mature-year proof JSON must include at least one passing fiscal year before target_fy" in result[
        "errors"
    ]


def test_verify_stage6_return_exception_requires_r8_status_acknowledgement(tmp_path: Path) -> None:
    module = _load_module()
    template, last_run, verify_json = _write_complete_artifacts(tmp_path)
    mature_year_proof = _write_mature_year_proof(tmp_path)
    exception_record = _write_approved_exception_record(tmp_path)
    exception_record.write_text(
        exception_record.read_text(encoding="utf-8").replace(
            "| FY2026/R8 status acknowledged | yes |",
            "| FY2026/R8 status acknowledged | no |",
        ),
        encoding="utf-8",
    )
    template.write_text(_complete_exception_template(), encoding="utf-8")

    result = module.verify_stage6_return(
        e2e_template=template,
        last_run=last_run,
        evidence_verify_json=verify_json,
        target_fy=2026,
        release_exception_reason="publication_lag",
        mature_year_proof_json=mature_year_proof,
        release_exception_record=exception_record,
    )

    assert result["ok"] is False
    assert "release exception record FY2026/R8 status acknowledged must be yes" in result["errors"]


def test_verify_stage6_return_exception_requires_scope_and_follow_up(tmp_path: Path) -> None:
    module = _load_module()
    template, last_run, verify_json = _write_complete_artifacts(tmp_path)
    mature_year_proof = _write_mature_year_proof(tmp_path)
    exception_record = _write_approved_exception_record(tmp_path)
    exception_record.write_text(
        exception_record.read_text(encoding="utf-8")
        .replace("| Release scope | v1.0 may ship on mature FY2025 production-scale proof only |\n", "")
        .replace(
            "| Required follow-up | Re-run FY2026/R8 strict-yield upper-bound proof "
            "when R8 target-form publication baseline exists |\n",
            "",
        ),
        encoding="utf-8",
    )
    template.write_text(_complete_exception_template(), encoding="utf-8")

    result = module.verify_stage6_return(
        e2e_template=template,
        last_run=last_run,
        evidence_verify_json=verify_json,
        target_fy=2026,
        release_exception_reason="publication_lag",
        mature_year_proof_json=mature_year_proof,
        release_exception_record=exception_record,
    )

    assert result["ok"] is False
    assert "release exception record row missing or malformed: Release scope" in result["errors"]
    assert "release exception record row missing or malformed: Required follow-up" in result["errors"]


def test_verify_stage6_return_exception_rejects_overbroad_scope_and_weak_follow_up(tmp_path: Path) -> None:
    module = _load_module()
    template, last_run, verify_json = _write_complete_artifacts(tmp_path)
    mature_year_proof = _write_mature_year_proof(tmp_path)
    exception_record = _write_approved_exception_record(tmp_path)
    exception_record.write_text(
        exception_record.read_text(encoding="utf-8")
        .replace(
            "| Release scope | v1.0 may ship on mature FY2025 production-scale proof only |",
            "| Release scope | Ship v1.0 for all remaining source classes |",
        )
        .replace(
            "| Required follow-up | Re-run FY2026/R8 strict-yield upper-bound proof "
            "when R8 target-form publication baseline exists |",
            "| Required follow-up | Monitor later |",
        ),
        encoding="utf-8",
    )
    template.write_text(_complete_exception_template(), encoding="utf-8")

    result = module.verify_stage6_return(
        e2e_template=template,
        last_run=last_run,
        evidence_verify_json=verify_json,
        target_fy=2026,
        release_exception_reason="publication_lag",
        mature_year_proof_json=mature_year_proof,
        release_exception_record=exception_record,
    )

    assert result["ok"] is False
    assert (
        "release exception record Release scope must limit approval to v1.0 mature-year proof only"
        in result["errors"]
    )
    assert (
        "release exception record Required follow-up must require FY2026/R8 strict-yield rerun"
        in result["errors"]
    )


def test_verify_stage6_return_rejects_failed_mature_year_proof(tmp_path: Path) -> None:
    module = _load_module()
    template, last_run, verify_json = _write_complete_artifacts(tmp_path)
    mature_year_proof = _write_mature_year_proof(tmp_path, ok=False)
    exception_record = _write_approved_exception_record(tmp_path)

    result = module.verify_stage6_return(
        e2e_template=template,
        last_run=last_run,
        evidence_verify_json=verify_json,
        target_fy=2026,
        release_exception_reason="publication_lag",
        mature_year_proof_json=mature_year_proof,
        release_exception_record=exception_record,
    )

    assert result["ok"] is False
    assert "mature-year proof JSON ok must be true" in result["errors"]
    assert "mature-year proof JSON must include at least one passing fiscal year before target_fy" in result["errors"]


def test_verify_stage6_return_rejects_small_mature_year_proof_denominator(tmp_path: Path) -> None:
    module = _load_module()
    template, last_run, verify_json = _write_complete_artifacts(tmp_path)
    mature_year_proof = _write_mature_year_proof(
        tmp_path,
        target_pdf_auto_denominator_count=5,
    )
    exception_record = _write_approved_exception_record(tmp_path)

    result = module.verify_stage6_return(
        e2e_template=template,
        last_run=last_run,
        evidence_verify_json=verify_json,
        target_fy=2026,
        release_exception_reason="publication_lag",
        mature_year_proof_json=mature_year_proof,
        release_exception_record=exception_record,
    )

    assert result["ok"] is False
    assert (
        "mature-year proof case FY2025 target_pdf_auto_denominator_count below production-scale "
        "threshold: 5 < 1000"
    ) in result["errors"]
    assert "mature-year proof JSON must include at least one passing fiscal year before target_fy" in result["errors"]


def test_verify_stage6_return_rejects_fractional_mature_year_proof_denominator(tmp_path: Path) -> None:
    module = _load_module()
    template, last_run, verify_json = _write_complete_artifacts(tmp_path)
    mature_year_proof = _write_mature_year_proof(
        tmp_path,
        target_pdf_auto_denominator_count=1000.5,
    )
    exception_record = _write_approved_exception_record(tmp_path)

    result = module.verify_stage6_return(
        e2e_template=template,
        last_run=last_run,
        evidence_verify_json=verify_json,
        target_fy=2026,
        release_exception_reason="publication_lag",
        mature_year_proof_json=mature_year_proof,
        release_exception_record=exception_record,
    )

    assert result["ok"] is False
    assert (
        "mature-year proof case FY2025 target_pdf_auto_denominator_count must be an integer"
        in result["errors"]
    )
    assert "mature-year proof JSON must include at least one passing fiscal year before target_fy" in result["errors"]


def test_verify_stage6_return_rejects_excel_diff_as_publication_lag_mature_year_proof(tmp_path: Path) -> None:
    module = _load_module()
    template, last_run, verify_json = _write_complete_artifacts(tmp_path)
    exception_record = _write_approved_exception_record(tmp_path)
    template.write_text(
        _complete_exception_template()
        .replace("| `ship_readiness_rc` | 0 | 0 | pass |", "| `ship_readiness_rc` | 0 | 1 | watch |")
        .replace(
            "| strict target PDF 自動取得率 | >= 60% | 67.5 | pass |",
            "| strict target PDF 自動取得率 | >= 60% | 22.0 | watch |",
        )
        .replace(
            "| 推定手作業率 | <= 30% | 28.0 | pass |",
            "| 推定手作業率 | <= 30% | 100.0 | watch |",
        )
        .replace(
            "| Excel ready 率 | >= 60% | 67.5 | pass |",
            "| Excel ready 率 | >= 60% | 22.0 | watch |",
        ),
        encoding="utf-8",
    )
    _write_json(
        last_run,
        {
            "status": "success",
            "finished_at": "2026-05-17T01:02:03+00:00",
            "dry_run": False,
            "current_fy": 2026,
            "school_type": "専門学校",
            "target_pdf_auto_yield_pct": 22.0,
            "operator_reviewable_yield_pct": 0.0,
            "target_pdf_excel_ready_yield_pct": 22.0,
            "ship_gate_status": "below_gate",
        },
    )
    proof = tmp_path / "excel-business-diff-proof.json"
    _write_json(
        proof,
        {
            "ok": True,
            "basis": "current_source_retroactive_excel_business_value_diff",
            "cases": [
                {
                    "fiscal_year": 2025,
                    "ok": True,
                    "results": [
                        {"name": "retroactive_excel_diff_reference", "returncode": 0},
                    ],
                },
            ],
        },
    )

    result = module.verify_stage6_return(
        e2e_template=template,
        last_run=last_run,
        evidence_verify_json=verify_json,
        target_fy=2026,
        release_exception_reason="publication_lag",
        mature_year_proof_json=proof,
        release_exception_record=exception_record,
    )

    assert result["ok"] is False
    assert any(
        (
            "mature-year proof JSON basis must be "
            "mature_year_retroactive_strict_target_pdf_and_operator_reviewable_acquisition"
        )
        in error
        for error in result["errors"]
    )
    assert "mature-year proof case FY2025 target_pdf_auto_yield_pct must be numeric" in result["errors"]
    assert "mature-year proof case FY2025 operator_reviewable_yield_pct must be numeric" in result["errors"]
    assert "mature-year proof JSON must include at least one passing fiscal year before target_fy" in result["errors"]


def test_verify_stage6_return_rejects_unmeasured_kpi_and_blank_signoff(tmp_path: Path) -> None:
    module = _load_module()
    template = tmp_path / "eidp-operator-e2e-template.md"
    template.write_text(
        """# EIDP 業務員 PC E2E 記録テンプレート

| KPI | Target | Actual | 判定 |
| --- | ---: | ---: | --- |
| `ship_readiness_rc` | 0 | | pass / watch / fail |
| strict target PDF 自動取得率 | >= 60% | | pass / watch / fail |
| 推定手作業率 | <= 30% | | pass / watch / fail |

| 判定項目 | 結果 |
| --- | --- |
| Stage 2-5c Windows VM gate 済み | yes / no |
| 業務員 PC 1 サイクル完了 | yes / no |
| KPI owner 承認 | yes / no |
| Runbook 修正反映済み | yes / no |
| 残 P0/P1 bug | none / exists |

結論:

```text
READY / RC_ONLY / NOT_READY
```

Owner sign-off:

```text
Name:
Date:
Decision:
```

業務員 sign-off:

```text
Name:
Date:
Decision:
```
""",
        encoding="utf-8",
    )
    last_run = tmp_path / "last_run.json"
    _write_json(
        last_run,
        {
            "status": "success",
            "finished_at": "2026-05-17T01:02:03+00:00",
            "dry_run": False,
            "current_fy": 2026,
            "school_type": "専門学校",
            "target_pdf_auto_yield_pct": None,
            "operator_reviewable_yield_pct": None,
            "target_pdf_excel_ready_yield_pct": None,
            "ship_gate_status": "not_measured",
        },
    )
    verify_json = tmp_path / "stage6-evidence-verify.json"
    _write_json(
        verify_json,
        {
            "ok": True,
            "missing_required_labels": [],
            "present_labels": ["build_info", "diagnostics"],
        },
    )

    result = module.verify_stage6_return(
        e2e_template=template,
        last_run=last_run,
        evidence_verify_json=verify_json,
        target_fy=2026,
    )

    assert result["ok"] is False
    assert "last_run target_pdf_auto_yield_pct must be numeric for final return evidence" in result["errors"]
    assert "last_run ship_gate_status must be measured" in result["errors"]
    assert "evidence verifier JSON missing labels: last_run, stage6_recovery, weekly_run_logs" in result["errors"]
    assert "E2E template Owner sign-off: Name is blank" in result["errors"]
    assert "E2E template 業務員 sign-off: Decision is blank" in result["errors"]


def test_verify_stage6_return_rejects_below_threshold_and_non_ready_decision(tmp_path: Path) -> None:
    module = _load_module()
    template = tmp_path / "eidp-operator-e2e-template.md"
    template.write_text(
        _complete_template()
        .replace(
            "| strict target PDF 自動取得率 | >= 60% | 67.5 | pass |",
            "| strict target PDF 自動取得率 | >= 60% | 55.0 | watch |",
        )
        .replace("```text\nREADY\n```", "```text\nRC_ONLY\n```")
        .replace("Decision: READY", "Decision: RC_ONLY", 1)
        .replace("| KPI owner 承認 | yes |", "| KPI owner 承認 | no |"),
        encoding="utf-8",
    )
    last_run = tmp_path / "last_run.json"
    _write_json(
        last_run,
        {
            "status": "success",
            "finished_at": "2026-05-17T01:02:03+00:00",
            "dry_run": False,
            "current_fy": 2026,
            "school_type": "専門学校",
            "target_pdf_auto_yield_pct": 55.0,
            "operator_reviewable_yield_pct": 65.0,
            "target_pdf_excel_ready_yield_pct": 55.0,
            "ship_gate_status": "pass",
        },
    )
    verify_json = tmp_path / "stage6-evidence-verify.json"
    _write_json(
        verify_json,
        {
            "ok": True,
            "missing_required_labels": [],
            "present_labels": ["build_info", "diagnostics", "last_run", "stage6_recovery", "weekly_run_logs"],
        },
    )

    result = module.verify_stage6_return(
        e2e_template=template,
        last_run=last_run,
        evidence_verify_json=verify_json,
        target_fy=2026,
    )

    assert result["ok"] is False
    assert "last_run target_pdf_auto_yield_pct below release threshold: 55.0 < 60.0" in result["errors"]
    assert "last_run estimated manual workload above release threshold: 35.0 > 30.0" in result["errors"]
    assert "E2E template KPI verdict must be pass: strict target PDF 自動取得率" in result["errors"]
    assert "E2E template release row must be yes: KPI owner 承認" in result["errors"]
    assert "E2E template release conclusion must be READY for the selected release path" in result["errors"]
    assert "E2E template Owner sign-off: Decision must be READY for the selected release path" in result["errors"]


def test_verify_stage6_return_rejects_missing_windows_vm_gate_row(tmp_path: Path) -> None:
    module = _load_module()
    template, last_run, verify_json = _write_complete_artifacts(tmp_path)
    template.write_text(
        _complete_template().replace("| Stage 2-5c Windows VM gate 済み | yes |\n", ""),
        encoding="utf-8",
    )

    result = module.verify_stage6_return(
        e2e_template=template,
        last_run=last_run,
        evidence_verify_json=verify_json,
        target_fy=2026,
    )

    assert result["ok"] is False
    assert "E2E template release row missing or malformed: Stage 2-5c Windows VM gate 済み" in result["errors"]


def test_verify_stage6_return_rejects_missing_ocr_scope_decision(tmp_path: Path) -> None:
    module = _load_module()
    template, last_run, verify_json = _write_complete_artifacts(tmp_path)
    template.write_text(
        _complete_template().replace("| OCR scope 決定 | core_non_ocr_only |\n", ""),
        encoding="utf-8",
    )

    result = module.verify_stage6_return(
        e2e_template=template,
        last_run=last_run,
        evidence_verify_json=verify_json,
        target_fy=2026,
    )

    assert result["ok"] is False
    assert "E2E template release row missing or malformed: OCR scope 決定" in result["errors"]


def test_verify_stage6_return_rejects_unresolved_ocr_scope_decision(tmp_path: Path) -> None:
    module = _load_module()
    template, last_run, verify_json = _write_complete_artifacts(tmp_path)
    template.write_text(
        _complete_template().replace("| OCR scope 決定 | core_non_ocr_only |", "| OCR scope 決定 | pending |"),
        encoding="utf-8",
    )

    result = module.verify_stage6_return(
        e2e_template=template,
        last_run=last_run,
        evidence_verify_json=verify_json,
        target_fy=2026,
    )

    assert result["ok"] is False
    assert (
        "E2E template OCR scope 決定 must be core_non_ocr_only or ocr_addon_verified: pending"
        in result["errors"]
    )


def test_verify_stage6_return_rejects_ocr_addon_scope_without_sha256(tmp_path: Path) -> None:
    module = _load_module()
    template, last_run, verify_json = _write_complete_artifacts(tmp_path)
    template.write_text(
        _complete_template().replace(
            "| OCR scope 決定 | core_non_ocr_only |",
            "| OCR scope 決定 | ocr_addon_verified |",
        ),
        encoding="utf-8",
    )

    result = module.verify_stage6_return(
        e2e_template=template,
        last_run=last_run,
        evidence_verify_json=verify_json,
        target_fy=2026,
    )

    assert result["ok"] is False
    assert "E2E template row missing or malformed: OCR add-on ZIP sha256" in result["errors"]


def test_verify_stage6_return_accepts_ocr_addon_scope_with_sha256(tmp_path: Path) -> None:
    module = _load_module()
    template, last_run, verify_json = _write_complete_artifacts(tmp_path)
    template.write_text(
        _complete_template()
        .replace(
            "| OCR scope 決定 | core_non_ocr_only |",
            "| OCR scope 決定 | ocr_addon_verified |",
        )
        .replace(
            "| KPI owner 承認 | yes |",
            "| OCR add-on ZIP sha256 | aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa |\n"
            "| KPI owner 承認 | yes |",
        ),
        encoding="utf-8",
    )

    result = module.verify_stage6_return(
        e2e_template=template,
        last_run=last_run,
        evidence_verify_json=verify_json,
        target_fy=2026,
    )

    assert result["ok"] is True
    assert result["errors"] == []


def test_verify_stage6_return_rejects_missing_runbook_correction_row(tmp_path: Path) -> None:
    module = _load_module()
    template, last_run, verify_json = _write_complete_artifacts(tmp_path)
    template.write_text(
        _complete_template().replace("| Runbook 修正反映済み | yes |\n", ""),
        encoding="utf-8",
    )

    result = module.verify_stage6_return(
        e2e_template=template,
        last_run=last_run,
        evidence_verify_json=verify_json,
        target_fy=2026,
    )

    assert result["ok"] is False
    assert "E2E template release row missing or malformed: Runbook 修正反映済み" in result["errors"]


def test_verify_stage6_return_rejects_legacy_go_release_conclusion(tmp_path: Path) -> None:
    module = _load_module()
    template, last_run, verify_json = _write_complete_artifacts(tmp_path)
    template.write_text(
        _complete_template()
        .replace("```text\nREADY\n```", "```text\ngo\n```")
        .replace("Decision: READY", "Decision: go", 1),
        encoding="utf-8",
    )

    result = module.verify_stage6_return(
        e2e_template=template,
        last_run=last_run,
        evidence_verify_json=verify_json,
        target_fy=2026,
    )

    assert result["ok"] is False
    assert "E2E template release conclusion must be one of READY, RC_ONLY, NOT_READY" in result["errors"]
    assert "E2E template Owner sign-off: Decision must be one of READY, RC_ONLY, NOT_READY" in result["errors"]


def test_verify_stage6_return_rejects_invalid_signoff_dates(tmp_path: Path) -> None:
    module = _load_module()
    template, last_run, verify_json = _write_complete_artifacts(tmp_path)
    template.write_text(
        _complete_template()
        .replace("Date: 2026-05-17", "Date: 2026/05/17", 1)
        .replace("Date: 2026-05-17", "Date: 2026-02-30", 1),
        encoding="utf-8",
    )

    result = module.verify_stage6_return(
        e2e_template=template,
        last_run=last_run,
        evidence_verify_json=verify_json,
        target_fy=2026,
    )

    assert result["ok"] is False
    assert "E2E template Owner sign-off: Date must be YYYY-MM-DD" in result["errors"]
    assert "E2E template 業務員 sign-off: Date must be YYYY-MM-DD" in result["errors"]


def test_verify_stage6_return_rejects_placeholder_signoff_names(tmp_path: Path) -> None:
    module = _load_module()
    template, last_run, verify_json = _write_complete_artifacts(tmp_path)
    template.write_text(
        _complete_template()
        .replace("Name: Aiko Tanaka", "Name: Example Owner")
        .replace("Name: Kenji Sato", "Name: Example Operator"),
        encoding="utf-8",
    )

    result = module.verify_stage6_return(
        e2e_template=template,
        last_run=last_run,
        evidence_verify_json=verify_json,
        target_fy=2026,
    )

    assert result["ok"] is False
    assert "E2E template Owner sign-off: Name must not be a placeholder" in result["errors"]
    assert "E2E template 業務員 sign-off: Name must not be a placeholder" in result["errors"]


def test_verify_stage6_return_rejects_shorthand_placeholder_signoff_names(tmp_path: Path) -> None:
    module = _load_module()
    template, last_run, verify_json = _write_complete_artifacts(tmp_path)
    template.write_text(
        _complete_template()
        .replace("Name: Aiko Tanaka", "Name: TBD")
        .replace("Name: Kenji Sato", "Name: N/A"),
        encoding="utf-8",
    )

    result = module.verify_stage6_return(
        e2e_template=template,
        last_run=last_run,
        evidence_verify_json=verify_json,
        target_fy=2026,
    )

    assert result["ok"] is False
    assert "E2E template Owner sign-off: Name must not be a placeholder" in result["errors"]
    assert "E2E template 業務員 sign-off: Name must not be a placeholder" in result["errors"]


def test_verify_stage6_return_rejects_future_signoff_dates(tmp_path: Path) -> None:
    module = _load_module()
    template, last_run, verify_json = _write_complete_artifacts(tmp_path)
    template.write_text(
        _complete_template().replace("Date: 2026-05-17", "Date: 2999-01-01"),
        encoding="utf-8",
    )

    result = module.verify_stage6_return(
        e2e_template=template,
        last_run=last_run,
        evidence_verify_json=verify_json,
        target_fy=2026,
    )

    assert result["ok"] is False
    assert "E2E template Owner sign-off: Date must not be in the future" in result["errors"]
    assert "E2E template 業務員 sign-off: Date must not be in the future" in result["errors"]


def test_verify_stage6_return_rejects_signoff_dates_before_last_run_finished_date(tmp_path: Path) -> None:
    module = _load_module()
    template, last_run, verify_json = _write_complete_artifacts(tmp_path)
    _write_json(
        last_run,
        {
            "status": "success",
            "finished_at": "2026-05-18T01:02:03+00:00",
            "dry_run": False,
            "current_fy": 2026,
            "school_type": "専門学校",
            "target_pdf_auto_yield_pct": 67.5,
            "operator_reviewable_yield_pct": 72.0,
            "target_pdf_excel_ready_yield_pct": 67.5,
            "ship_gate_status": "pass",
        },
    )

    result = module.verify_stage6_return(
        e2e_template=template,
        last_run=last_run,
        evidence_verify_json=verify_json,
        target_fy=2026,
    )

    assert result["ok"] is False
    assert (
        "E2E template Owner sign-off: Date must be on or after last_run finished_at date"
        in result["errors"]
    )
    assert (
        "E2E template 業務員 sign-off: Date must be on or after last_run finished_at date"
        in result["errors"]
    )
