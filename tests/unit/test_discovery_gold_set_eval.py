from __future__ import annotations

import json
from pathlib import Path

from eidp.scraper.discovery_gold_set import (
    DiscoveryGoldPrediction,
    evaluate_discovery_gold_predictions,
    load_discovery_gold_entries,
    load_discovery_gold_predictions,
    load_discovery_gold_predictions_from_pdf_evidence,
    render_discovery_gold_eval_report,
)

GOLD_SET_DIR = Path(__file__).resolve().parents[2] / "data" / "discovery-gold-set"


def test_evaluate_discovery_predictions_flags_missing_and_mismatched_entries() -> None:
    entries = load_discovery_gold_entries(GOLD_SET_DIR)
    predictions = [
        DiscoveryGoldPrediction(
            entry_id="ecole-matsue-nutrition-2026",
            outcome="accepted_target_pdf",
            pdf_url="https://www.ecole-cpb.com/files/school_support_R8.pdf",
            fiscal_year=2026,
            strict_target_year_success=True,
        ),
        DiscoveryGoldPrediction(
            entry_id="nihon-u-dental-hygienist-publication-lag-2026",
            outcome="accepted_target_pdf",
            pdf_url="https://www.dent.nihon-u.ac.jp/hyg/pdf/campus-life/tuition/2025_study-support_01.pdf",
            fiscal_year=2026,
            strict_target_year_success=True,
        ),
    ]

    report = evaluate_discovery_gold_predictions(entries, predictions)

    assert report.total_gold_entries == 10
    assert report.predicted_entries == 2
    assert report.exact_matches == 1
    assert report.failed_predictions == 1
    assert report.missing_entries == 8
    assert report.unexpected_predictions == 0
    assert report.failures[0]["entry_id"] == "nihon-u-dental-hygienist-publication-lag-2026"
    assert report.failures[0]["reasons"] == [
        "outcome_mismatch",
        "fiscal_year_mismatch",
        "strict_target_year_success_mismatch",
    ]


def test_load_discovery_predictions_accepts_jsonl(tmp_path: Path) -> None:
    predictions_path = tmp_path / "predictions.jsonl"
    predictions_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "entry_id": "ecole-matsue-nutrition-2026",
                        "outcome": "accepted_target_pdf",
                        "pdf_url": "https://www.ecole-cpb.com/files/school_support_R8.pdf",
                        "fiscal_year": 2026,
                        "strict_target_year_success": True,
                    }
                ),
                "",
            ]
        ),
        encoding="utf-8",
    )

    predictions = load_discovery_gold_predictions(predictions_path)

    assert predictions == [
        DiscoveryGoldPrediction(
            entry_id="ecole-matsue-nutrition-2026",
            outcome="accepted_target_pdf",
            pdf_url="https://www.ecole-cpb.com/files/school_support_R8.pdf",
            fiscal_year=2026,
            strict_target_year_success=True,
        )
    ]


def test_load_predictions_from_pdf_discovery_evidence_maps_release_outcomes(tmp_path: Path) -> None:
    evidence_path = tmp_path / "discovery-evidence.jsonl"
    evidence_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "school_id": 1721,
                        "pdf_url": "https://www.ecole-cpb.com/files/school_support_R8.pdf",
                        "reason": "accepted_downloaded",
                        "pdf_type": "target",
                        "extra": {"target_fiscal_year": "2026"},
                    }
                ),
                json.dumps(
                    {
                        "school_id": 494,
                        "pdf_url": "https://www.dent.nihon-u.ac.jp/hyg/pdf/campus-life/tuition/2025_study-support_01.pdf",
                        "reason": "fiscal_year_mismatch:2025",
                        "pdf_type": "target",
                    }
                ),
                json.dumps(
                    {
                        "school_id": 819,
                        "pdf_url": "https://www.mascat.nihon-u.ac.jp/data/pdf/college/info/higher_education_support.pdf?1=",
                        "reason": "target_fiscal_year_not_detected",
                        "pdf_type": "target",
                    }
                ),
                json.dumps(
                    {
                        "school_id": 999999,
                        "pdf_url": "https://example.invalid/ignored.pdf",
                        "reason": "accepted_downloaded",
                        "pdf_type": "target",
                    }
                ),
            ]
        ),
        encoding="utf-8",
    )

    predictions = load_discovery_gold_predictions_from_pdf_evidence(
        evidence_path,
        load_discovery_gold_entries(GOLD_SET_DIR),
    )

    assert predictions == [
        DiscoveryGoldPrediction(
            entry_id="ecole-matsue-nutrition-2026",
            outcome="accepted_target_pdf",
            pdf_url="https://www.ecole-cpb.com/files/school_support_R8.pdf",
            fiscal_year=2026,
            strict_target_year_success=True,
        ),
        DiscoveryGoldPrediction(
            entry_id="nihon-u-dental-hygienist-publication-lag-2026",
            outcome="publication_lag_latest_public",
            pdf_url="https://www.dent.nihon-u.ac.jp/hyg/pdf/campus-life/tuition/2025_study-support_01.pdf",
            fiscal_year=2025,
            strict_target_year_success=False,
        ),
        DiscoveryGoldPrediction(
            entry_id="nihon-u-matsudo-dental-hygienist-review-2026",
            outcome="needs_operator_review",
            pdf_url="https://www.mascat.nihon-u.ac.jp/data/pdf/college/info/higher_education_support.pdf?1=",
            fiscal_year=None,
            strict_target_year_success=False,
        ),
    ]


def test_render_discovery_gold_eval_report_outputs_json_payload() -> None:
    report = evaluate_discovery_gold_predictions(
        load_discovery_gold_entries(GOLD_SET_DIR),
        [
            DiscoveryGoldPrediction(
                entry_id="ecole-matsue-nutrition-2026",
                outcome="accepted_target_pdf",
                pdf_url="https://www.ecole-cpb.com/files/school_support_R8.pdf",
                fiscal_year=2026,
                strict_target_year_success=True,
            )
        ],
    )

    payload = json.loads(render_discovery_gold_eval_report(report))

    assert payload["total_gold_entries"] == 10
    assert payload["exact_matches"] == 1
    assert payload["missing_entries"] == 9
