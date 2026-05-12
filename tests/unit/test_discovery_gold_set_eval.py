from __future__ import annotations

import json
from pathlib import Path

from eidp.scraper.discovery_gold_set import (
    DiscoveryGoldEntry,
    DiscoveryGoldPrediction,
    evaluate_discovery_gold_predictions,
    load_discovery_gold_entries,
    load_discovery_gold_predictions,
    load_discovery_gold_predictions_from_pdf_evidence,
    render_discovery_gold_eval_report,
)

GOLD_SET_DIR = Path(__file__).resolve().parents[2] / "data" / "discovery-gold-set"

AGEO_URL = "https://ageo.org/files/admission/support/study_support_system.pdf"
ECOLE_URL = "https://www.ecole-cpb.com/files/school_support_R8.pdf"
NIHON_U_TUITION_URL = "https://www.dent.nihon-u.ac.jp/hyg/pdf/campus-life/tuition/2025_study-support_01.pdf"
MASCAT_URL = "https://www.mascat.nihon-u.ac.jp/data/pdf/college/info/higher_education_support.pdf?1="
ODHS_URL = "https://odhs.info/app-def/S-101/html/koutou202507.pdf?20250711"
SIW_URL = "https://www.siw.ac.jp/wp-content/themes/bsc/dist/images/information/shugakushien_shinsei2025-1-2.pdf"


def _entry(
    *,
    entry_id: str,
    school_id: int,
    target_fiscal_year: int,
    outcome: str,
    pdf_url: str = "",
    pdf_type: str = "target",
    fiscal_year: int | None = None,
    strict_target_year_success: bool = False,
) -> DiscoveryGoldEntry:
    return DiscoveryGoldEntry(
        entry_id=entry_id,
        school_id=school_id,
        school_name="テスト専門学校",
        prefecture="東京都",
        corporation_name="",
        target_fiscal_year=target_fiscal_year,
        outcome=outcome,
        school_url="https://example.ac.jp/",
        disclosure_url="https://example.ac.jp/disclosure/",
        pdf_url=pdf_url,
        pdf_type=pdf_type,
        fiscal_year=fiscal_year,
        strict_target_year_success=strict_target_year_success,
        site_family="test",
    )


def test_evaluate_discovery_predictions_flags_missing_and_mismatched_entries() -> None:
    entries = load_discovery_gold_entries(GOLD_SET_DIR)
    predictions = [
        DiscoveryGoldPrediction(
            entry_id="ecole-matsue-nutrition-2026",
            outcome="accepted_target_pdf",
            pdf_url=ECOLE_URL,
            fiscal_year=2026,
            strict_target_year_success=True,
        ),
        DiscoveryGoldPrediction(
            entry_id="nihon-u-dental-hygienist-publication-lag-2026",
            outcome="accepted_target_pdf",
            pdf_url=NIHON_U_TUITION_URL,
            fiscal_year=2026,
            strict_target_year_success=True,
        ),
    ]

    report = evaluate_discovery_gold_predictions(entries, predictions)

    assert report.total_gold_entries == 20
    assert report.predicted_entries == 2
    assert report.exact_matches == 1
    assert report.failed_predictions == 1
    assert report.missing_entries == 18
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
                        "pdf_url": ECOLE_URL,
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
            pdf_url=ECOLE_URL,
            fiscal_year=2026,
            strict_target_year_success=True,
        )
    ]


def test_load_predictions_from_pdf_evidence_uses_target_year_for_duplicate_school_entries(
    tmp_path: Path,
) -> None:
    evidence_path = tmp_path / "discovery-evidence.jsonl"
    evidence_path.write_text(
        json.dumps(
            {
                "school_id": 1,
                "pdf_url": "https://example.ac.jp/r9.pdf",
                "reason": "accepted_downloaded",
                "pdf_type": "target",
                "extra": {"target_fiscal_year": "2027"},
            }
        ),
        encoding="utf-8",
    )
    entries = [
        _entry(
            entry_id="same-school-2026",
            school_id=1,
            target_fiscal_year=2026,
            outcome="publication_lag_latest_public",
            pdf_url="https://example.ac.jp/r8.pdf",
            fiscal_year=2025,
        ),
        _entry(
            entry_id="same-school-2027",
            school_id=1,
            target_fiscal_year=2027,
            outcome="accepted_target_pdf",
            pdf_url="https://example.ac.jp/r9.pdf",
            fiscal_year=2027,
            strict_target_year_success=True,
        ),
    ]

    predictions = load_discovery_gold_predictions_from_pdf_evidence(evidence_path, entries)

    assert predictions == [
        DiscoveryGoldPrediction(
            entry_id="same-school-2027",
            outcome="accepted_target_pdf",
            pdf_url="https://example.ac.jp/r9.pdf",
            fiscal_year=2027,
            strict_target_year_success=True,
        )
    ]


def test_load_predictions_from_ambiguous_old_evidence_skips_duplicate_school_entries(
    tmp_path: Path,
) -> None:
    evidence_path = tmp_path / "old-discovery-evidence.jsonl"
    evidence_path.write_text(
        json.dumps(
            {
                "school_id": 1,
                "pdf_url": "https://example.ac.jp/r9.pdf",
                "reason": "accepted_downloaded",
                "pdf_type": "target",
                "extra": {},
            }
        ),
        encoding="utf-8",
    )
    entries = [
        _entry(entry_id="same-school-2026", school_id=1, target_fiscal_year=2026, outcome="accepted_target_pdf"),
        _entry(entry_id="same-school-2027", school_id=1, target_fiscal_year=2027, outcome="accepted_target_pdf"),
    ]

    assert load_discovery_gold_predictions_from_pdf_evidence(evidence_path, entries) == []


def test_load_predictions_from_pdf_discovery_evidence_maps_release_outcomes(tmp_path: Path) -> None:
    evidence_path = tmp_path / "discovery-evidence.jsonl"
    evidence_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "school_id": 95,
                        "pdf_url": SIW_URL,
                        "reason": "accepted_downloaded",
                        "pdf_type": "target",
                        "extra": {"target_fiscal_year": "2026", "year_evidence": "pdf_text"},
                    }
                ),
                json.dumps(
                    {
                        "school_id": 757,
                        "pdf_url": AGEO_URL,
                        "reason": "accepted_downloaded",
                        "pdf_type": "target",
                        "extra": {
                            "target_fiscal_year": "2026",
                            "year_evidence": "prefecture_index_current_year",
                        },
                    }
                ),
                json.dumps(
                    {
                        "school_id": 1721,
                        "pdf_url": ECOLE_URL,
                        "reason": "accepted_downloaded",
                        "pdf_type": "target",
                        "extra": {"target_fiscal_year": "2026"},
                    }
                ),
                json.dumps(
                    {
                        "school_id": 494,
                        "pdf_url": NIHON_U_TUITION_URL,
                        "reason": "fiscal_year_mismatch:2025",
                        "pdf_type": "target",
                    }
                ),
                json.dumps(
                    {
                        "school_id": 819,
                        "pdf_url": MASCAT_URL,
                        "reason": "target_fiscal_year_not_detected",
                        "pdf_type": "target",
                    }
                ),
                json.dumps(
                    {
                        "school_id": 760,
                        "pdf_url": "https://www.i-heiseigakuen.ac.jp/kokai/",
                        "reason": "no_candidates_found",
                        "pdf_type": None,
                    }
                ),
                json.dumps(
                    {
                        "school_id": 767,
                        "pdf_url": "https://www.kitasato-u.ac.jp/kango-gko/about/release.html",
                        "reason": "discovery_error",
                        "pdf_type": None,
                    }
                ),
                json.dumps(
                    {
                        "school_id": 763,
                        "pdf_url": ODHS_URL,
                        "reason": "target_fiscal_year_not_detected",
                        "pdf_type": "image_only",
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
            entry_id="ageo-central-nursing-review-2026",
            outcome="accepted_target_pdf",
            pdf_url=AGEO_URL,
            fiscal_year=2026,
            strict_target_year_success=True,
        ),
        DiscoveryGoldPrediction(
            entry_id="ecole-matsue-nutrition-2026",
            outcome="accepted_target_pdf",
            pdf_url=ECOLE_URL,
            fiscal_year=2026,
            strict_target_year_success=True,
        ),
        DiscoveryGoldPrediction(
            entry_id="iruma-kango-no-candidates-2026",
            outcome="no_target_candidate_found",
            pdf_url="",
            fiscal_year=None,
            strict_target_year_success=False,
        ),
        DiscoveryGoldPrediction(
            entry_id="nihon-u-dental-hygienist-publication-lag-2026",
            outcome="publication_lag_latest_public",
            pdf_url=NIHON_U_TUITION_URL,
            fiscal_year=2025,
            strict_target_year_success=False,
        ),
        DiscoveryGoldPrediction(
            entry_id="nihon-u-matsudo-dental-hygienist-review-2026",
            outcome="needs_operator_review",
            pdf_url=MASCAT_URL,
            fiscal_year=None,
            strict_target_year_success=False,
        ),
        DiscoveryGoldPrediction(
            entry_id="omiya-dental-hygienist-image-review-2026",
            outcome="needs_operator_review",
            pdf_url=ODHS_URL,
            fiscal_year=None,
            strict_target_year_success=False,
        ),
        DiscoveryGoldPrediction(
            entry_id="saitama-it-web-accepted-2026",
            outcome="accepted_target_pdf",
            pdf_url=SIW_URL,
            fiscal_year=2026,
            strict_target_year_success=True,
        ),
        DiscoveryGoldPrediction(
            entry_id="saitama-kitasato-nursing-site-fetch-error-2026",
            outcome="site_fetch_error",
            pdf_url="",
            fiscal_year=None,
            strict_target_year_success=False,
        ),
    ]


def test_load_predictions_maps_non_target_only_evidence_to_no_target_candidate(tmp_path: Path) -> None:
    evidence_path = tmp_path / "discovery-evidence.jsonl"
    evidence_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "school_id": 1,
                        "pdf_url": "https://example.ac.jp/officers.pdf",
                        "reason": "pre_filtered_non_target_hint",
                        "pdf_type": "non_target",
                    }
                ),
                json.dumps(
                    {
                        "school_id": 1,
                        "pdf_url": "https://example.ac.jp/syllabus.pdf",
                        "reason": "classified_non_target",
                        "pdf_type": "non_target",
                    }
                ),
                json.dumps(
                    {
                        "school_id": 1,
                        "pdf_url": "https://example.ac.jp/low-score.pdf",
                        "reason": "all_negative_score",
                        "pdf_type": None,
                    }
                ),
            ]
        ),
        encoding="utf-8",
    )
    entries = [
        _entry(
            entry_id="non-target-only",
            school_id=1,
            target_fiscal_year=2026,
            outcome="no_target_candidate_found",
            pdf_url="",
            fiscal_year=None,
        )
    ]

    predictions = load_discovery_gold_predictions_from_pdf_evidence(evidence_path, entries)

    assert predictions == [
        DiscoveryGoldPrediction(
            entry_id="non-target-only",
            outcome="no_target_candidate_found",
            pdf_url="",
            fiscal_year=None,
            strict_target_year_success=False,
        )
    ]


def test_load_predictions_prefers_old_target_over_non_target_candidate_noise(tmp_path: Path) -> None:
    evidence_path = tmp_path / "discovery-evidence.jsonl"
    evidence_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "school_id": 1,
                        "pdf_url": "https://example.ac.jp/officers.pdf",
                        "reason": "pre_filtered_non_target_hint",
                        "pdf_type": "non_target",
                    }
                ),
                json.dumps(
                    {
                        "school_id": 1,
                        "pdf_url": "https://example.ac.jp/r7-target.pdf",
                        "reason": "fiscal_year_mismatch:2025",
                        "pdf_type": "target",
                    }
                ),
            ]
        ),
        encoding="utf-8",
    )
    entries = [
        _entry(
            entry_id="old-target",
            school_id=1,
            target_fiscal_year=2026,
            outcome="publication_lag_latest_public",
            pdf_url="https://example.ac.jp/r7-target.pdf",
            fiscal_year=2025,
        )
    ]

    predictions = load_discovery_gold_predictions_from_pdf_evidence(evidence_path, entries)

    assert predictions == [
        DiscoveryGoldPrediction(
            entry_id="old-target",
            outcome="publication_lag_latest_public",
            pdf_url="https://example.ac.jp/r7-target.pdf",
            fiscal_year=2025,
            strict_target_year_success=False,
        )
    ]


def test_load_predictions_prefers_accepted_body_year_over_stale_url_hint(tmp_path: Path) -> None:
    evidence_path = tmp_path / "discovery-evidence.jsonl"
    evidence_path.write_text(
        json.dumps(
            {
                "school_id": 95,
                "pdf_url": SIW_URL,
                "reason": "accepted_downloaded",
                "pdf_type": "target",
                "extra": {
                    "target_fiscal_year": "2026",
                    "detected_fiscal_year": "2026",
                    "year_evidence": "pdf_text",
                },
            }
        ),
        encoding="utf-8",
    )

    predictions = load_discovery_gold_predictions_from_pdf_evidence(
        evidence_path,
        load_discovery_gold_entries(GOLD_SET_DIR),
    )

    assert predictions == [
        DiscoveryGoldPrediction(
            entry_id="saitama-it-web-accepted-2026",
            outcome="accepted_target_pdf",
            pdf_url=SIW_URL,
            fiscal_year=2026,
            strict_target_year_success=True,
        )
    ]


def test_load_predictions_preserves_detected_year_mismatch_on_accepted_download(tmp_path: Path) -> None:
    evidence_path = tmp_path / "discovery-evidence.jsonl"
    evidence_path.write_text(
        json.dumps(
            {
                "school_id": 1721,
                "pdf_url": ECOLE_URL,
                "reason": "accepted_downloaded",
                "pdf_type": "target",
                "extra": {
                    "target_fiscal_year": "2026",
                    "detected_fiscal_year": "2025",
                    "year_evidence": "pdf_text",
                },
            }
        ),
        encoding="utf-8",
    )

    predictions = load_discovery_gold_predictions_from_pdf_evidence(
        evidence_path,
        load_discovery_gold_entries(GOLD_SET_DIR),
    )
    report = evaluate_discovery_gold_predictions(load_discovery_gold_entries(GOLD_SET_DIR), predictions)

    assert predictions == [
        DiscoveryGoldPrediction(
            entry_id="ecole-matsue-nutrition-2026",
            outcome="accepted_target_pdf",
            pdf_url=ECOLE_URL,
            fiscal_year=2025,
            strict_target_year_success=True,
        )
    ]
    assert report.failed_predictions == 1
    assert report.failures == [
        {
            "entry_id": "ecole-matsue-nutrition-2026",
            "reasons": ["fiscal_year_mismatch"],
        }
    ]


def test_load_predictions_keeps_yearless_target_candidate_in_review(tmp_path: Path) -> None:
    evidence_path = tmp_path / "discovery-evidence.jsonl"
    evidence_path.write_text(
        json.dumps(
            {
                "school_id": 757,
                "pdf_url": AGEO_URL,
                "reason": "target_fiscal_year_not_detected",
                "pdf_type": "target",
            }
        ),
        encoding="utf-8",
    )

    predictions = load_discovery_gold_predictions_from_pdf_evidence(
        evidence_path,
        load_discovery_gold_entries(GOLD_SET_DIR),
    )

    assert predictions == [
        DiscoveryGoldPrediction(
            entry_id="ageo-central-nursing-review-2026",
            outcome="needs_operator_review",
            pdf_url=AGEO_URL,
            fiscal_year=None,
            strict_target_year_success=False,
        )
    ]


def test_render_discovery_gold_eval_report_outputs_json_payload() -> None:
    report = evaluate_discovery_gold_predictions(
        load_discovery_gold_entries(GOLD_SET_DIR),
        [
            DiscoveryGoldPrediction(
                entry_id="ecole-matsue-nutrition-2026",
                outcome="accepted_target_pdf",
                pdf_url=ECOLE_URL,
                fiscal_year=2026,
                strict_target_year_success=True,
            )
        ],
    )

    payload = json.loads(render_discovery_gold_eval_report(report))

    assert payload["total_gold_entries"] == 20
    assert payload["exact_matches"] == 1
    assert payload["missing_entries"] == 19
