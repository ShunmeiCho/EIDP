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
        "known_operator_note": "Win SSH disconnected; continue manual RCA on Mac.",
    }
