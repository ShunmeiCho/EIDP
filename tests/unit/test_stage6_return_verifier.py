from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


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

結論:

```text
READY
```

Owner sign-off:

```text
Name: Owner Name
Date: 2026-05-17
Decision: READY
```

業務員 sign-off:

```text
Name: Operator Name
Date: 2026-05-17
Decision: READY
```
"""


def _complete_exception_template() -> str:
    return _complete_template().replace(
        "| 推定手作業率 | <= 30% | 28.0 | pass |",
        "| 推定手作業率 | <= 30% | 100.0 | watch |\n"
        "| release exception reason | `publication_lag` | publication_lag | pass |\n"
        "| mature-year proof JSON | ok=true | logs/mature-year-proof.json | pass |\n"
        "| mature-year proof years | at least one FY before target_fy | 2025, 2024, 2023 | pass |",
    )


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
            "target_pdf_auto_yield_pct": 67.5,
            "operator_reviewable_yield_pct": 72.0,
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


def _write_mature_year_proof(tmp_path: Path, *, ok: bool = True, **case_overrides: object) -> Path:
    proof = tmp_path / "mature-year-proof.json"
    case = {
        "fiscal_year": 2025,
        "ok": ok,
        "target_pdf_auto_denominator_count": 1625,
        "target_pdf_auto_denominator_scope": "target_missing_schools_before_run",
        "target_pdf_auto_yield_pct": 67.5,
        "operator_reviewable_yield_pct": 72.0,
        "ship_gate_status": "pass",
        "results": [
            {"name": "retroactive_weekly_discovery", "returncode": 0},
        ],
    }
    case.update(case_overrides)
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
| Approver | Owner Name |
| Approval date | 2026-05-19 |
| Release scope | v1.0 may ship on mature FY2025 production-scale proof only |
| FY2026/R8 status acknowledged | yes |
| Required follow-up | Re-run FY2026/R8 strict-yield upper-bound proof when R8 target-form publication baseline exists |
""",
        encoding="utf-8",
    )
    return record


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
            "target_pdf_auto_yield_pct": 67.5,
            "operator_reviewable_yield_pct": 72.0,
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
    assert "E2E template Excel output file proof must include an .xlsx workbook path" in result["errors"]


def test_verify_stage6_return_cli_emits_json_and_success(tmp_path: Path, capsys) -> None:
    module = _load_module()
    template, last_run, verify_json = _write_complete_artifacts(tmp_path)

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
            "--json",
        ]
    )

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["inputs"]["min_target_pdf_auto_yield"] == 60.0
    assert payload["inputs"]["max_manual_workload"] == 30.0
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
            "target_pdf_auto_yield_pct": 22.0,
            "operator_reviewable_yield_pct": 0.0,
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
    assert any("accepted KPI verdict watch: strict target PDF 自動取得率" in warning for warning in result["warnings"])


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
            "target_pdf_auto_yield_pct": None,
            "operator_reviewable_yield_pct": None,
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
            "target_pdf_auto_yield_pct": 22.0,
            "operator_reviewable_yield_pct": 0.0,
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
            "target_pdf_auto_yield_pct": 22.0,
            "operator_reviewable_yield_pct": 0.0,
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
            "target_pdf_auto_yield_pct": None,
            "operator_reviewable_yield_pct": None,
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
            "target_pdf_auto_yield_pct": 55.0,
            "operator_reviewable_yield_pct": 65.0,
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
    assert "E2E template release conclusion must be READY for release approval" in result["errors"]
    assert "E2E template Owner sign-off: Decision must be READY for release approval" in result["errors"]


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
