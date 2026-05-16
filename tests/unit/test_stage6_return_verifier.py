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

| 判定項目 | 結果 |
| --- | --- |
| 業務員 PC 1 サイクル完了 | yes |
| KPI owner 承認 | yes |
| 残 P0/P1 bug | none |

結論:

```text
go
```

Owner sign-off:

```text
Name: Owner Name
Date: 2026-05-17
Decision: go
```

業務員 sign-off:

```text
Name: Operator Name
Date: 2026-05-17
Decision: go
```
"""


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
| 業務員 PC 1 サイクル完了 | yes / no |
| KPI owner 承認 | yes / no |
| 残 P0/P1 bug | none / exists |

結論:

```text
go / no-go / beta continue
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


def test_verify_stage6_return_rejects_below_threshold_and_non_go_decision(tmp_path: Path) -> None:
    module = _load_module()
    template = tmp_path / "eidp-operator-e2e-template.md"
    template.write_text(
        _complete_template()
        .replace(
            "| strict target PDF 自動取得率 | >= 60% | 67.5 | pass |",
            "| strict target PDF 自動取得率 | >= 60% | 55.0 | watch |",
        )
        .replace("go\n```", "no-go\n```")
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
    assert "E2E template release conclusion must be go" in result["errors"]
