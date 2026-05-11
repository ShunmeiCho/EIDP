from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from typer.testing import CliRunner

from eidp.cli import app
from eidp.db.models import Base, School, SchoolSite


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows), encoding="utf-8")


def test_discovery_rca_packet_cli_outputs_single_school_input_packet(tmp_path: Path, monkeypatch) -> None:
    evidence_path = tmp_path / "evidence.jsonl"
    _write_jsonl(
        evidence_path,
        [
            {
                "school_id": 95,
                "reason": "target_fiscal_year_not_detected",
                "pdf_type": "target",
                "pdf_url": "https://www.siw.ac.jp/information/shugakushien.pdf",
            },
            {
                "school_id": 999,
                "reason": "accepted_downloaded",
                "pdf_type": "target",
                "pdf_url": "https://other.example.ac.jp/r8.pdf",
            },
        ],
    )
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(
            School(
                id=95,
                school_name="さいたまIT・WEB専門学校",
                prefecture="埼玉県",
                corporation_name="東京滋慶学園",
                school_type="専門学校",
                status="active",
            )
        )
        session.add_all(
            [
                SchoolSite(
                    school_id=95,
                    url="https://www.siw.ac.jp/information",
                    url_type="disclosure",
                    discovery_method="prefecture_aggregator",
                    confidence=0.95,
                    verified=True,
                ),
                SchoolSite(
                    school_id=95,
                    url="https://www.siw.ac.jp/",
                    url_type="school",
                    discovery_method="operator_manual",
                    confidence=None,
                    verified=False,
                ),
            ]
        )
        session.commit()

    import eidp.db.session as db_session

    monkeypatch.setattr(db_session, "SessionLocal", lambda: Session(engine))

    result = CliRunner().invoke(
        app,
        [
            "discovery-rca-packet",
            "--school-id",
            "95",
            "--target-fiscal-year",
            "2026",
            "--evidence-log",
            str(evidence_path),
            "--known-operator-note",
            "Win SSH disconnected; continue manual RCA on Mac.",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload == {
        "school_id": 95,
        "school_name": "さいたまIT・WEB専門学校",
        "prefecture": "埼玉県",
        "target_fiscal_year": 2026,
        "official_index_url": "https://www.siw.ac.jp/information",
        "registered_sites": [
            {
                "url": "https://www.siw.ac.jp/information",
                "url_type": "disclosure",
                "discovery_method": "prefecture_aggregator",
                "confidence": 0.95,
                "verified": True,
            },
            {
                "url": "https://www.siw.ac.jp/",
                "url_type": "school",
                "discovery_method": "operator_manual",
                "confidence": None,
                "verified": False,
            },
        ],
        "latest_bucket": "target_form_without_year_evidence",
        "latest_evidence_rows_path": str(evidence_path),
        "latest_evidence_row_count": 1,
        "latest_evidence_top_reasons": [["target_fiscal_year_not_detected", 1]],
        "latest_evidence_rows": [
            {
                "reason": "target_fiscal_year_not_detected",
                "pdf_type": "target",
                "pdf_url": "https://www.siw.ac.jp/information/shugakushien.pdf",
                "page_url": "",
                "anchor_text": "",
                "pattern_type": "",
                "score": None,
                "extra": {},
            }
        ],
        "known_operator_note": "Win SSH disconnected; continue manual RCA on Mac.",
    }


def test_discovery_rca_packet_cli_outputs_copy_paste_prompt(tmp_path: Path, monkeypatch) -> None:
    evidence_path = tmp_path / "evidence.jsonl"
    _write_jsonl(
        evidence_path,
        [
            {
                "school_id": 95,
                "reason": "target_fiscal_year_not_detected",
                "pdf_type": "target",
                "pdf_url": "https://www.siw.ac.jp/information/shugakushien.pdf",
            },
        ],
    )
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(
            School(
                id=95,
                school_name="さいたまIT・WEB専門学校",
                prefecture="埼玉県",
                corporation_name="東京滋慶学園",
                school_type="専門学校",
                status="active",
            )
        )
        session.add(
            SchoolSite(
                school_id=95,
                url="https://www.siw.ac.jp/information",
                url_type="disclosure",
                discovery_method="prefecture_aggregator",
                confidence=0.95,
                verified=True,
            )
        )
        session.commit()

    import eidp.db.session as db_session

    monkeypatch.setattr(db_session, "SessionLocal", lambda: Session(engine))

    result = CliRunner().invoke(
        app,
        [
            "discovery-rca-packet",
            "--school-id",
            "95",
            "--target-fiscal-year",
            "2026",
            "--evidence-log",
            str(evidence_path),
            "--prompt",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Investigate this EIDP school as a single-school RCA packet." in result.output
    assert "Do not run broad SERP crawling." in result.output
    assert '"school_id": 95' in result.output
    assert '"latest_bucket": "target_form_without_year_evidence"' in result.output
    assert '"latest_evidence_rows"' in result.output
    assert "https://www.siw.ac.jp/information/shugakushien.pdf" in result.output
    assert "Return exactly one Required Output Block JSON object." in result.output


def test_discovery_rca_batch_plan_prioritizes_manual_rca_buckets(tmp_path: Path, monkeypatch) -> None:
    evidence_path = tmp_path / "evidence.jsonl"
    _write_jsonl(
        evidence_path,
        [
            {
                "school_id": 1,
                "reason": "fiscal_year_mismatch:2025",
                "pdf_type": "target",
                "pdf_url": "https://a.example.ac.jp/r7.pdf",
            },
            {
                "school_id": 2,
                "reason": "target_fiscal_year_not_detected",
                "pdf_type": "target",
                "pdf_url": "https://b.example.ac.jp/support.pdf",
            },
            {
                "school_id": 3,
                "reason": "no_candidates_found",
                "pdf_url": "https://c.example.ac.jp/kokai/",
            },
        ],
    )
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        for school_id, name, url in [
            (1, "A専門学校", "https://a.example.ac.jp/kokai/"),
            (2, "B専門学校", "https://b.example.ac.jp/kokai/"),
            (3, "C専門学校", "https://c.example.ac.jp/kokai/"),
        ]:
            session.add(
                School(
                    id=school_id,
                    school_name=name,
                    prefecture="埼玉県",
                    corporation_name=f"法人{school_id}",
                    school_type="専門学校",
                    status="active",
                )
            )
            session.add(
                SchoolSite(
                    school_id=school_id,
                    url=url,
                    url_type="disclosure",
                    discovery_method="prefecture_aggregator",
                    confidence=0.9,
                    verified=True,
                )
            )
        session.commit()

    import eidp.db.session as db_session

    monkeypatch.setattr(db_session, "SessionLocal", lambda: Session(engine))

    result = CliRunner().invoke(
        app,
        [
            "discovery-rca-batch-plan",
            "--evidence-log",
            str(evidence_path),
            "--prefecture",
            "埼玉県",
            "--discovery-method",
            "prefecture_aggregator",
            "--target-fiscal-year",
            "2026",
            "--limit",
            "2",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["total_candidates"] == 3
    assert [item["bucket"] for item in payload["items"]] == [
        "target_form_without_year_evidence",
        "no_pdf_candidates",
    ]
    assert [item["packet"]["school_id"] for item in payload["items"]] == [2, 3]
    assert payload["items"][0]["packet"]["official_index_url"] == "https://b.example.ac.jp/kokai/"


def test_discovery_rca_batch_plan_can_include_copy_paste_prompts(tmp_path: Path, monkeypatch) -> None:
    evidence_path = tmp_path / "evidence.jsonl"
    _write_jsonl(
        evidence_path,
        [
            {
                "school_id": 2,
                "reason": "target_fiscal_year_not_detected",
                "pdf_type": "target",
                "pdf_url": "https://b.example.ac.jp/support.pdf",
            }
        ],
    )
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(
            School(
                id=2,
                school_name="B専門学校",
                prefecture="埼玉県",
                corporation_name="法人B",
                school_type="専門学校",
                status="active",
            )
        )
        session.add(
            SchoolSite(
                school_id=2,
                url="https://b.example.ac.jp/kokai/",
                url_type="disclosure",
                discovery_method="prefecture_aggregator",
                confidence=0.9,
                verified=True,
            )
        )
        session.commit()

    import eidp.db.session as db_session

    monkeypatch.setattr(db_session, "SessionLocal", lambda: Session(engine))

    result = CliRunner().invoke(
        app,
        [
            "discovery-rca-batch-plan",
            "--evidence-log",
            str(evidence_path),
            "--prefecture",
            "埼玉県",
            "--discovery-method",
            "prefecture_aggregator",
            "--target-fiscal-year",
            "2026",
            "--limit",
            "1",
            "--include-prompts",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert len(payload["items"]) == 1
    prompt = payload["items"][0]["prompt"]
    assert "Investigate this EIDP school as a single-school RCA packet." in prompt
    assert "Do not run broad SERP crawling." in prompt
    assert '"school_id": 2' in prompt
    assert '"latest_bucket": "target_form_without_year_evidence"' in prompt
