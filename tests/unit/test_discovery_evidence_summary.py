from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from typer.testing import CliRunner

from eidp.cli import app
from eidp.db.models import Base, School, SchoolSite
from eidp.scraper.discovery_evidence_summary import (
    EvidenceScopeSite,
    load_pdf_discovery_evidence,
    summarize_pdf_discovery_evidence,
)


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows), encoding="utf-8")


def test_summarize_pdf_discovery_evidence_buckets_school_outcomes(tmp_path: Path) -> None:
    evidence_path = tmp_path / "evidence.jsonl"
    _write_jsonl(
        evidence_path,
        [
            {"school_id": 1, "reason": "classified_non_target", "pdf_type": "non_target", "pdf_url": "https://a/1.pdf"},
            {"school_id": 1, "reason": "fiscal_year_mismatch:2025", "pdf_type": "target", "pdf_url": "https://a/2.pdf"},
            {"school_id": 2, "reason": "target_fiscal_year_not_detected", "pdf_type": "target", "pdf_url": "https://b/1.pdf"},
            {"school_id": 3, "reason": "discovery_error", "pdf_url": "https://c/"},
        ],
    )

    summary = summarize_pdf_discovery_evidence(load_pdf_discovery_evidence(evidence_path))

    assert summary.school_bucket_counts == {
        "publication_lag_or_old_target_pdf": 1,
        "site_fetch_error_only": 1,
        "target_form_without_year_evidence": 1,
    }
    assert summary.reason_counts["classified_non_target"] == 1
    assert summary.reason_counts["fiscal_year_mismatch:2025"] == 1
    assert summary.pdf_type_counts["target"] == 2


def test_summarize_pdf_discovery_evidence_treats_image_only_old_target_application_hints_as_publication_lag(
    tmp_path: Path,
) -> None:
    evidence_path = tmp_path / "evidence.jsonl"
    _write_jsonl(
        evidence_path,
        [
            {
                "school_id": 1,
                "reason": "fiscal_year_mismatch:2025",
                "pdf_type": "image_only",
                "pdf_url": "https://example.ac.jp/report/09_shugakushien_r7.pdf",
                "anchor_text": "R7修学支援 様式第2号",
            },
            {
                "school_id": 2,
                "reason": "fiscal_year_mismatch:2025",
                "pdf_type": "image_only",
                "pdf_url": "https://example.ac.jp/report/R7-yoshiki-2.pdf",
                "anchor_text": "令和7年度 高等教育の修学支援新制度 様式2",
            },
        ],
    )

    summary = summarize_pdf_discovery_evidence(load_pdf_discovery_evidence(evidence_path))

    assert summary.school_bucket_counts == {"publication_lag_or_old_target_pdf": 2}
    assert [school.bucket for school in summary.school_summaries] == [
        "publication_lag_or_old_target_pdf",
        "publication_lag_or_old_target_pdf",
    ]


def test_summarize_pdf_discovery_evidence_keeps_weak_image_only_form_or_support_hints_in_review(
    tmp_path: Path,
) -> None:
    evidence_path = tmp_path / "evidence.jsonl"
    _write_jsonl(
        evidence_path,
        [
            {
                "school_id": 1,
                "reason": "fiscal_year_mismatch:2025",
                "pdf_type": "image_only",
                "pdf_url": "https://example.ac.jp/report/syllabus_yoshiki2_2025.pdf",
                "anchor_text": "シラバス 様式2号",
            },
            {
                "school_id": 2,
                "reason": "fiscal_year_mismatch:2025",
                "pdf_type": "image_only",
                "pdf_url": "https://example.ac.jp/report/09_shugakushien_r7.pdf",
                "anchor_text": "R7修学支援に関する資料",
            },
        ],
    )

    summary = summarize_pdf_discovery_evidence(load_pdf_discovery_evidence(evidence_path))

    assert summary.school_bucket_counts == {"target_form_without_year_evidence": 2}
    assert [school.bucket for school in summary.school_summaries] == [
        "target_form_without_year_evidence",
        "target_form_without_year_evidence",
    ]


def test_summarize_pdf_discovery_evidence_keeps_generic_higher_ed_boilerplate_image_only_in_review(
    tmp_path: Path,
) -> None:
    evidence_path = tmp_path / "evidence.jsonl"
    _write_jsonl(
        evidence_path,
        [
            {
                "school_id": 1,
                "reason": "fiscal_year_mismatch:2020",
                "pdf_type": "image_only",
                "pdf_url": "https://odhs.info/app-def/S-101/html/koutou202507.pdf?20250711",
                "anchor_text": (
                    "本校の申請内容について 住民税非課税世帯及びそれに準ずる世帯の学生"
                    "（2020年度の在学生（既入学者も含む）から対象）"
                    " https://www.mext.go.jp/a_menu/koutou/hutankeigen/index.htm"
                ),
            }
        ],
    )

    summary = summarize_pdf_discovery_evidence(load_pdf_discovery_evidence(evidence_path))

    assert summary.school_bucket_counts == {"target_form_without_year_evidence": 1}
    assert summary.school_summaries[0].bucket == "target_form_without_year_evidence"


def test_summarize_pdf_discovery_evidence_buckets_tls_certificate_failures(tmp_path: Path) -> None:
    evidence_path = tmp_path / "evidence.jsonl"
    _write_jsonl(
        evidence_path,
        [
            {
                "school_id": 1,
                "reason": "discovery_error",
                "pdf_url": "https://tls.example/",
                "extra": {
                    "error": (
                        "[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: "
                        "unable to get local issuer certificate (_ssl.c:1010)"
                    )
                },
            }
        ],
    )

    summary = summarize_pdf_discovery_evidence(load_pdf_discovery_evidence(evidence_path))

    assert summary.school_bucket_counts == {"tls_certificate_verify_failed": 1}
    assert summary.school_summaries[0].bucket == "tls_certificate_verify_failed"


def test_summarize_pdf_discovery_evidence_includes_scope_sites_without_evidence(tmp_path: Path) -> None:
    evidence_path = tmp_path / "evidence.jsonl"
    _write_jsonl(
        evidence_path,
        [{"school_id": 1, "reason": "no_candidates_found", "pdf_url": "https://a/"}],
    )

    summary = summarize_pdf_discovery_evidence(
        load_pdf_discovery_evidence(evidence_path),
        site_scope=[
            EvidenceScopeSite(school_id=1, school_name="A", site_url="https://a/"),
            EvidenceScopeSite(school_id=2, school_name="B", site_url="https://b/"),
        ],
    )

    assert summary.site_scope_schools == 2
    assert summary.school_bucket_counts == {"no_evidence": 1, "no_pdf_candidates": 1}
    assert [school.bucket for school in summary.school_summaries] == ["no_pdf_candidates", "no_evidence"]


def test_summarize_discovery_evidence_cli_reads_configured_db_scope(tmp_path: Path, monkeypatch) -> None:
    evidence_path = tmp_path / "evidence.jsonl"
    _write_jsonl(
        evidence_path,
        [{"school_id": 1, "reason": "fiscal_year_mismatch:2025", "pdf_type": "target", "pdf_url": "https://a/1.pdf"}],
    )
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add_all(
            [
                School(
                    id=1,
                    school_name="A",
                    prefecture="埼玉県",
                    corporation_name="法人A",
                    school_type="専門学校",
                    status="active",
                ),
                School(
                    id=2,
                    school_name="B",
                    prefecture="埼玉県",
                    corporation_name="法人B",
                    school_type="専門学校",
                    status="active",
                ),
                SchoolSite(
                    school_id=1,
                    url="https://a/",
                    discovery_method="prefecture_aggregator",
                    url_type="disclosure",
                ),
                SchoolSite(
                    school_id=2,
                    url="https://b/",
                    discovery_method="prefecture_aggregator",
                    url_type="disclosure",
                ),
            ]
        )
        session.commit()

    import eidp.db.session as db_session

    monkeypatch.setattr(db_session, "SessionLocal", lambda: Session(engine))

    result = CliRunner().invoke(
        app,
        [
            "summarize-discovery-evidence",
            "--evidence-log",
            str(evidence_path),
            "--prefecture",
            "埼玉県",
            "--discovery-method",
            "prefecture_aggregator",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["site_scope_schools"] == 2
    assert payload["school_bucket_counts"] == {
        "no_evidence": 1,
        "publication_lag_or_old_target_pdf": 1,
    }


def test_load_pdf_discovery_site_scope_can_filter_school_type() -> None:
    from eidp.scraper.discovery_evidence_summary import load_pdf_discovery_site_scope

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add_all(
            [
                School(
                    id=1,
                    school_name="A",
                    prefecture="埼玉県",
                    corporation_name="法人A",
                    school_type="専門学校",
                    status="active",
                ),
                School(
                    id=2,
                    school_name="B",
                    prefecture="埼玉県",
                    corporation_name="法人B",
                    school_type="大学",
                    status="active",
                ),
                SchoolSite(school_id=1, url="https://a/", discovery_method="prefecture_aggregator"),
                SchoolSite(school_id=2, url="https://b/", discovery_method="prefecture_aggregator"),
            ]
        )
        session.commit()

        scope = load_pdf_discovery_site_scope(
            session,
            prefecture="埼玉県",
            discovery_method="prefecture_aggregator",
            school_type="専門学校",
        )

    assert [site.school_id for site in scope] == [1]
