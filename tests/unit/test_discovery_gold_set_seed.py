from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from typer.testing import CliRunner

from eidp.cli import app
from eidp.db.models import Base, School, SchoolSite
from eidp.scraper.discovery_gold_set import (
    load_discovery_gold_entries,
    seed_discovery_gold_sites,
)

GOLD_SET_DIR = Path(__file__).resolve().parents[2] / "data" / "discovery-gold-set"
SAMPLE_ENTRY_ID = "ecole-matsue-nutrition-2026"


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_seed_discovery_gold_sites_dry_run_does_not_write() -> None:
    session = _session()
    entries = [entry for entry in load_discovery_gold_entries(GOLD_SET_DIR) if entry.entry_id == SAMPLE_ENTRY_ID]

    stats = seed_discovery_gold_sites(session, entries, apply=False, safe_url_checker=lambda _url: True)

    assert stats == {
        "applied": False,
        "schools_to_create": 1,
        "sites_to_add": 1,
        "sites_existing": 0,
        "invalid_site_urls": 0,
    }
    assert session.query(School).count() == 0
    assert session.query(SchoolSite).count() == 0


def test_seed_discovery_gold_sites_apply_writes_school_and_site() -> None:
    session = _session()
    entries = [entry for entry in load_discovery_gold_entries(GOLD_SET_DIR) if entry.entry_id == SAMPLE_ENTRY_ID]

    stats = seed_discovery_gold_sites(session, entries, apply=True, safe_url_checker=lambda _url: True)
    session.commit()

    assert stats == {
        "applied": True,
        "schools_to_create": 1,
        "sites_to_add": 1,
        "sites_existing": 0,
        "invalid_site_urls": 0,
    }
    school = session.get(School, 1721)
    assert school is not None
    assert school.school_name == "松江栄養調理製菓専門学校"
    site = session.query(SchoolSite).filter(SchoolSite.school_id == 1721).one()
    assert site.url == "https://www.ecole-cpb.com/school-support"
    assert site.url_type == "disclosure"
    assert site.discovery_method == "discovery_gold_set"
    assert float(site.confidence) == 0.99
    assert site.verified is True


def test_seed_discovery_gold_sites_is_idempotent_on_existing_site() -> None:
    session = _session()
    entries = [entry for entry in load_discovery_gold_entries(GOLD_SET_DIR) if entry.entry_id == SAMPLE_ENTRY_ID]

    seed_discovery_gold_sites(session, entries, apply=True, safe_url_checker=lambda _url: True)
    session.commit()
    stats = seed_discovery_gold_sites(session, entries, apply=True, safe_url_checker=lambda _url: True)
    session.commit()

    assert stats == {
        "applied": True,
        "schools_to_create": 0,
        "sites_to_add": 0,
        "sites_existing": 1,
        "invalid_site_urls": 0,
    }
    assert session.query(SchoolSite).count() == 1


def test_seed_discovery_gold_sites_rejects_unsafe_site_url_before_writing() -> None:
    session = _session()
    [entry] = [entry for entry in load_discovery_gold_entries(GOLD_SET_DIR) if entry.entry_id == SAMPLE_ENTRY_ID]
    unsafe_entry = replace(entry, disclosure_url="https://127.0.0.1/admin", school_url="")

    stats = seed_discovery_gold_sites(session, [unsafe_entry], apply=True, safe_url_checker=lambda _url: False)
    session.commit()

    assert stats == {
        "applied": True,
        "schools_to_create": 0,
        "sites_to_add": 0,
        "sites_existing": 0,
        "invalid_site_urls": 1,
    }
    assert session.query(School).count() == 0
    assert session.query(SchoolSite).count() == 0


def test_seed_discovery_gold_sites_fails_fast_on_semantically_invalid_entry() -> None:
    session = _session()
    [entry] = [entry for entry in load_discovery_gold_entries(GOLD_SET_DIR) if entry.entry_id == SAMPLE_ENTRY_ID]
    invalid_entry = replace(entry, disclosure_url="file:///etc/passwd", school_url="")

    with pytest.raises(ValueError, match="seed site URL must be an absolute http"):
        seed_discovery_gold_sites(session, [invalid_entry], apply=True, safe_url_checker=lambda _url: True)

    assert session.query(School).count() == 0
    assert session.query(SchoolSite).count() == 0


def test_seed_discovery_gold_sites_checks_normalized_site_url() -> None:
    session = _session()
    [entry] = [entry for entry in load_discovery_gold_entries(GOLD_SET_DIR) if entry.entry_id == SAMPLE_ENTRY_ID]
    seen_urls: list[str] = []

    def reject(url: str) -> bool:
        seen_urls.append(url)
        return False

    stats = seed_discovery_gold_sites(
        session,
        [replace(entry, disclosure_url="https://127.0.0.1/admin#fragment", school_url="")],
        apply=False,
        safe_url_checker=reject,
    )

    assert seen_urls == ["https://127.0.0.1/admin"]
    assert stats["invalid_site_urls"] == 1
    assert session.query(School).count() == 0
    assert session.query(SchoolSite).count() == 0


def test_seed_discovery_gold_sites_cli_applies_when_requested(monkeypatch) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    import eidp.db.session as db_session

    monkeypatch.setattr(db_session, "SessionLocal", lambda: Session(engine))
    monkeypatch.setattr("eidp.scraper.url_discovery._is_safe_url", lambda _url: True)

    result = CliRunner().invoke(
        app,
        [
            "seed-discovery-gold-sites",
            "--gold-set-dir",
            str(GOLD_SET_DIR),
            "--apply",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["applied"] is True
    assert payload["schools_to_create"] == 28
    assert payload["sites_to_add"] == 28
    assert payload["invalid_site_urls"] == 0
    with Session(engine) as session:
        assert session.query(SchoolSite).filter(SchoolSite.discovery_method == "discovery_gold_set").count() == 28
