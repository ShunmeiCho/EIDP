"""Sprint 8.3.a — prefecture aggregator parser regression.

Synthesizes minimal PDFs at test time using PyMuPDF so the test is
self-contained (no committed binary fixtures, no /tmp dependencies).
The Saitama-style hyperlink-annotation path is the headline contract:
without ``extract_pdf_annotation_links`` the URL would be silently
dropped, costing ~36 schools per prefecture run.
"""

from __future__ import annotations

from pathlib import Path

import fitz  # type: ignore[import-not-found]
import pytest

from eidp.scraper.prefecture_aggregator import (
    PARSERS,
    PREF_KEY_TO_DB,
    classify_url_quality,
    extract_pdf_annotation_links,
    extract_url,
    norm,
    parse,
    parse_5col,
    parse_tokyo,
    recommend_action,
)


# ---------------------------------------------------------------------------
# Helpers — generate minimal PDFs at test time
# ---------------------------------------------------------------------------


def _make_5col_pdf_with_annotation(path: Path, schools: list[dict]) -> None:
    """Build a tiny 5-column PDF mimicking Saitama. Each row holds:
        [school_name, address, operator_name, operator_address, 備考]
    Schools whose ``url`` field is set produce a clickable hyperlink
    annotation rectangle on the school-name cell — the same delivery
    pattern Saitama uses for the 36 schools that pdfplumber's plain
    text extraction misses.
    """
    doc = fitz.open()
    page = doc.new_page(width=600, height=800)

    # Header row first.
    headers = ["学校名", "住所", "設置者の名称", "設置者の住所", "備考"]
    rows = [headers] + [
        [s["name"], s["address"], s["operator"], s["op_address"], s.get("notes", "")]
        for s in schools
    ]

    col_widths = [180, 110, 110, 110, 90]  # x widths
    col_xs: list[float] = []
    x = 20.0
    for w in col_widths:
        col_xs.append(x)
        x += w

    row_height = 30
    y = 50
    for row_idx, row in enumerate(rows):
        for ci, value in enumerate(row):
            cell_x = col_xs[ci]
            cell_y = y
            # Draw cell rectangle so pdfplumber can detect table.
            rect = fitz.Rect(cell_x, cell_y, cell_x + col_widths[ci], cell_y + row_height)
            page.draw_rect(rect, color=(0, 0, 0), width=0.5)
            page.insert_text(
                (cell_x + 4, cell_y + 18),
                str(value),
                fontsize=8,
                fontname="japan",
            )
        # Add hyperlink annotation on data rows where school name carries a URL
        if row_idx > 0:
            school = schools[row_idx - 1]
            url = school.get("url")
            if url:
                name_rect = fitz.Rect(
                    col_xs[0], y, col_xs[0] + col_widths[0], y + row_height,
                )
                page.insert_link({
                    "kind": fitz.LINK_URI,
                    "from": name_rect,
                    "uri": url,
                })
        y += row_height

    doc.save(str(path))
    doc.close()


def _make_8col_tokyo_pdf(path: Path, schools: list[dict]) -> None:
    """Build a tiny 8-column Tokyo-style PDF.

    Columns:
      [#, 種別, 学校名, 住所, 設置者種別, 設置者名称, 設置者住所, 備考]
    URL goes into the 備考 column (col 7) as plain text — Tokyo's pattern.
    """
    doc = fitz.open()
    page = doc.new_page(width=900, height=900)

    headers = ["#", "種別", "学校名", "住所", "設置者種別", "設置者名称", "設置者住所", "備考"]
    rows = [headers] + [
        [
            str(i + 1),
            s.get("kind", "専"),
            s["name"],
            s["address"],
            s.get("operator_kind", ""),
            s["operator"],
            s["op_address"],
            s.get("url", ""),
        ]
        for i, s in enumerate(schools)
    ]

    col_widths = [40, 50, 160, 120, 90, 130, 130, 220]
    col_xs: list[float] = []
    x = 20.0
    for w in col_widths:
        col_xs.append(x)
        x += w

    row_height = 30
    y = 50
    for row in rows:
        for ci, value in enumerate(row):
            cell_x = col_xs[ci]
            cell_y = y
            rect = fitz.Rect(cell_x, cell_y, cell_x + col_widths[ci], cell_y + row_height)
            page.draw_rect(rect, color=(0, 0, 0), width=0.5)
            page.insert_text(
                (cell_x + 4, cell_y + 18),
                str(value),
                fontsize=7,
                fontname="japan",
            )
        y += row_height

    doc.save(str(path))
    doc.close()


# ---------------------------------------------------------------------------
# Helper-level unit tests
# ---------------------------------------------------------------------------


def test_norm_collapses_whitespace_and_normalizes_kana():
    assert norm("テスト  学校") == "テスト学校"
    assert norm(" 　ＡＢＣ　") == "ABC"
    assert norm(None) == ""


def test_extract_url_pulls_first_https_substring():
    assert extract_url("see https://example.com/x.pdf for details") == "https://example.com/x.pdf"
    assert extract_url("no url here") is None
    assert extract_url(None) is None


def test_classify_url_quality():
    assert classify_url_quality(None) == "none"
    assert classify_url_quality("https://example.com/disclosure/r8.pdf") == "direct_pdf"
    # 'kyufu' is in the disclosure keyword list (高等教育の修学支援).
    assert classify_url_quality("https://example.com/kyufu/index.html") == "disclosure"
    assert classify_url_quality("https://example.com/shien/info") == "disclosure"
    assert classify_url_quality("https://example.com/") == "homepage"


def test_recommend_action():
    assert recommend_action("none", []) == "noop"
    assert recommend_action("direct_pdf", []) == "add"
    # PDF beats homepage
    assert recommend_action("direct_pdf", ["homepage"]) == "upgrade"
    # Same quality → noop
    assert recommend_action("homepage", ["homepage"]) == "noop"
    # PDF doesn't beat existing PDF
    assert recommend_action("direct_pdf", ["direct_pdf"]) == "noop"


# ---------------------------------------------------------------------------
# Annotation extraction (the Saitama-style headline path)
# ---------------------------------------------------------------------------


def test_extract_pdf_annotation_links_recovers_hidden_urls(tmp_path: Path):
    schools = [
        {"name": "東京テスト学院", "address": "東京都新宿区1-1",
         "operator": "学校法人テスト", "op_address": "東京都新宿区1-1",
         "url": "https://example.com/tokyo-test/"},
        # Second school has no annotation URL — must NOT show up in output.
        {"name": "見えない学校", "address": "東京都港区2-2",
         "operator": "学校法人B", "op_address": "東京都港区2-2"},
    ]
    pdf = tmp_path / "saitama_like.pdf"
    _make_5col_pdf_with_annotation(pdf, schools)

    links = extract_pdf_annotation_links(pdf)
    assert links.get(norm("東京テスト学院")) == "https://example.com/tokyo-test/"
    assert norm("見えない学校") not in links


def test_parse_5col_uses_annotation_when_no_text_url(tmp_path: Path):
    """The owner-pinned Saitama path: 5col PDF whose 備考 column is empty
    BUT whose school-name cell carries a hyperlink annotation. The parser
    must surface that URL as ``disclosure_url`` instead of dropping it."""
    schools = [
        {"name": "埼玉テスト専門学校", "address": "埼玉県さいたま市1",
         "operator": "学校法人S", "op_address": "埼玉県さいたま市1",
         "url": "https://example.com/saitama/r8.pdf"},
    ]
    pdf = tmp_path / "saitama.pdf"
    _make_5col_pdf_with_annotation(pdf, schools)

    parsed = parse_5col(pdf, "saitama")
    assert len(parsed) == 1
    assert parsed[0].pref == "saitama"
    assert parsed[0].disclosure_url == "https://example.com/saitama/r8.pdf"
    assert parsed[0].school_name_norm == norm("埼玉テスト専門学校")


def test_parse_5col_text_url_in_remarks_takes_priority_over_annotation(monkeypatch, tmp_path):
    """If the 備考 column already carries a plain-text URL, it wins over
    the annotation. Annotation is the fallback, not the override.

    We can't rely on pdfplumber to reliably read multibyte text out of a
    synthesized PDF, so we drive parse_5col with a stub pdfplumber and
    a stub annotation map and just verify the priority logic.
    """
    from contextlib import contextmanager

    from eidp.scraper import prefecture_aggregator as pa

    @contextmanager
    def fake_pdf_open(_path):
        class FakePage:
            def extract_tables(self):
                return [[
                    ["神奈川テスト専門学校", "横浜市", "学校法人K", "横浜市",
                     "see https://example.com/text-priority.pdf"],
                ]]

        class FakePdf:
            pages = [FakePage()]

        yield FakePdf()

    monkeypatch.setattr(pa.pdfplumber, "open", fake_pdf_open)
    monkeypatch.setattr(
        pa,
        "extract_pdf_annotation_links",
        lambda _p: {pa.norm("神奈川テスト専門学校"): "https://example.com/should-not-win.pdf"},
    )

    parsed = parse_5col(tmp_path / "fake.pdf", "kanagawa")
    assert len(parsed) == 1
    assert parsed[0].disclosure_url == "https://example.com/text-priority.pdf"


# ---------------------------------------------------------------------------
# Tokyo (8col, URL as plain text)
# ---------------------------------------------------------------------------


def test_parse_tokyo_extracts_url_from_remarks(tmp_path: Path):
    schools = [
        {"name": "東京テスト専門学校", "address": "東京都新宿区1-1",
         "operator": "学校法人T", "op_address": "東京都新宿区1-1",
         "url": "https://example.com/tokyo.pdf"},
    ]
    pdf = tmp_path / "tokyo.pdf"
    _make_8col_tokyo_pdf(pdf, schools)

    parsed = parse_tokyo(pdf)
    assert len(parsed) == 1
    assert parsed[0].pref == "tokyo"
    assert parsed[0].disclosure_url == "https://example.com/tokyo.pdf"


# ---------------------------------------------------------------------------
# Public entry point dispatch
# ---------------------------------------------------------------------------


def test_parse_dispatches_via_registry(tmp_path: Path):
    schools = [
        {"name": "宮城テスト学院", "address": "宮城県仙台市1",
         "operator": "学校法人M", "op_address": "宮城県仙台市1",
         "url": "https://example.com/miyagi/r8.pdf"},
    ]
    pdf = tmp_path / "miyagi.pdf"
    _make_5col_pdf_with_annotation(pdf, schools)

    parsed = parse("miyagi", pdf)
    assert len(parsed) == 1
    assert parsed[0].pref == "miyagi"
    assert parsed[0].disclosure_url == "https://example.com/miyagi/r8.pdf"


def test_parse_unknown_pref_raises():
    with pytest.raises(ValueError, match="No parser registered"):
        parse("nowhere", Path("/dev/null"))


def test_pref_key_to_db_covers_all_registered_parsers():
    for key in PARSERS:
        assert key in PREF_KEY_TO_DB, f"PREF_KEY_TO_DB missing entry for {key!r}"


# ---------------------------------------------------------------------------
# Match + writer-plan + apply
# ---------------------------------------------------------------------------


@pytest.fixture()
def db_session(tmp_path):
    """SQLite engine bootstrapped via 8.1 path so ORM constraints match prod."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session as SqlSession

    from eidp.db.sqlite_bootstrap import bootstrap_sqlite

    db_path = tmp_path / "agg.sqlite3"
    engine = create_engine(f"sqlite:///{db_path}", future=True)
    bootstrap_sqlite(engine)
    with SqlSession(engine) as session:
        yield session
    engine.dispose()


def test_match_school_exact_then_nfkc_then_substring(db_session):
    """Three different schools, three different match strategies."""
    from eidp.db.models import School
    from eidp.scraper.prefecture_aggregator import (
        PrefSchool,
        build_indices,
        match_school,
    )

    s1 = School(prefecture="埼玉県", corporation_name="学校法人A", school_name="埼玉専門学校", status="active")
    s2 = School(prefecture="埼玉県", corporation_name="学校法人B", school_name="ＮＦＫＣ専門学校", status="active")
    s3 = School(prefecture="埼玉県", corporation_name="学校法人C", school_name="さいたまテクノロジー専門学校", status="active")
    db_session.add_all([s1, s2, s3])
    db_session.commit()

    school_index, site_index = build_indices(db_session, "saitama")

    exact = PrefSchool(
        pref="saitama", school_name_raw="埼玉専門学校", school_name_norm=norm("埼玉専門学校"),
        address="", operator_kind="", operator_name="", operator_address="",
        disclosure_url="https://example.com/a.pdf",
    )
    nfkc = PrefSchool(
        pref="saitama", school_name_raw="NFKC専門学校", school_name_norm=norm("NFKC専門学校"),
        address="", operator_kind="", operator_name="", operator_address="",
        disclosure_url=None,
    )
    sub = PrefSchool(
        pref="saitama", school_name_raw="株式会社XYZ さいたまテクノロジー専門学校",
        school_name_norm=norm("株式会社XYZ さいたまテクノロジー専門学校"),
        address="", operator_kind="", operator_name="", operator_address="",
        disclosure_url="https://example.com/c.html",
    )

    r_exact = match_school(exact, school_index, site_index)
    r_nfkc = match_school(nfkc, school_index, site_index)
    r_sub = match_school(sub, school_index, site_index)

    assert r_exact.match_strategy == "exact"
    assert r_exact.db_school_id == s1.id
    assert r_exact.is_new_url_candidate is True

    assert r_nfkc.match_strategy == "nfkc"
    assert r_nfkc.db_school_id == s2.id

    assert r_sub.match_strategy == "substring_pref"
    assert r_sub.db_school_id == s3.id


def test_apply_writer_plan_inserts_new_school_site(db_session):
    """An ``add`` action with a matched school produces a SchoolSite row
    keyed to discovery_method='prefecture_aggregator'."""
    from eidp.db.models import School, SchoolSite
    from eidp.scraper.prefecture_aggregator import PrefReport, apply_writer_plan

    s = School(prefecture="埼玉県", corporation_name="学校法人A", school_name="埼玉専門学校", status="active")
    db_session.add(s)
    db_session.commit()

    report = PrefReport(pref="saitama", pdf_path="(synthetic)")
    report.records = [{
        "db_school_id": s.id,
        "db_school_name": s.school_name,
        "pdf_school_name": s.school_name,
        "pdf_school_code": None,
        "pdf_address": "",
        "pdf_operator": "",
        "pref_url": "https://example.com/saitama-test/r8.pdf",
        "url_quality": "direct_pdf",
        "match_strategy": "exact",
        "existing_urls": [],
        "existing_url_quality": [],
        "is_new_url_candidate": True,
        "quality_upgrade_candidate": False,
        "recommended_action": "add",
    }]

    stats = apply_writer_plan(db_session, report)
    db_session.commit()
    assert stats == {"added": 1, "upgraded": 0, "skipped": 0}

    sites = db_session.query(SchoolSite).filter(SchoolSite.school_id == s.id).all()
    assert len(sites) == 1
    site = sites[0]
    assert site.url == "https://example.com/saitama-test/r8.pdf"
    assert site.discovery_method == "prefecture_aggregator"
    assert float(site.confidence) == 0.95


def test_apply_writer_plan_upgrade_replaces_lower_quality_url(db_session):
    """An ``upgrade`` action repoints the lowest-quality existing site
    to the prefecture-sourced URL."""
    from eidp.db.models import School, SchoolSite
    from eidp.scraper.prefecture_aggregator import PrefReport, apply_writer_plan

    s = School(prefecture="埼玉県", corporation_name="学校法人A", school_name="埼玉専門学校", status="active")
    db_session.add(s)
    db_session.commit()
    db_session.add(SchoolSite(
        school_id=s.id, url="https://example.com/", url_type="homepage",
        discovery_method="seed", confidence=0.5,
    ))
    db_session.commit()

    report = PrefReport(pref="saitama", pdf_path="(synthetic)")
    report.records = [{
        "db_school_id": s.id,
        "db_school_name": s.school_name,
        "pdf_school_name": s.school_name,
        "pdf_school_code": None,
        "pdf_address": "",
        "pdf_operator": "",
        "pref_url": "https://example.com/disclosure/r8.pdf",
        "url_quality": "direct_pdf",
        "match_strategy": "exact",
        "existing_urls": ["https://example.com/"],
        "existing_url_quality": ["homepage"],
        "is_new_url_candidate": False,
        "quality_upgrade_candidate": True,
        "recommended_action": "upgrade",
    }]

    stats = apply_writer_plan(db_session, report)
    db_session.commit()
    assert stats["upgraded"] == 1

    sites = db_session.query(SchoolSite).filter(SchoolSite.school_id == s.id).all()
    assert len(sites) == 1
    assert sites[0].url == "https://example.com/disclosure/r8.pdf"
    assert sites[0].discovery_method == "prefecture_aggregator"


def test_apply_writer_plan_skips_review_and_noop(db_session):
    """Unmatched (``review``) and equal-or-worse-quality (``noop``)
    actions must NEVER write."""
    from eidp.db.models import SchoolSite
    from eidp.scraper.prefecture_aggregator import PrefReport, apply_writer_plan

    report = PrefReport(pref="saitama", pdf_path="(synthetic)")
    report.records = [
        {
            "db_school_id": None, "db_school_name": None, "pdf_school_name": "未登録校",
            "pdf_school_code": None, "pdf_address": "", "pdf_operator": "",
            "pref_url": "https://example.com/lost.pdf", "url_quality": "direct_pdf",
            "match_strategy": "none", "existing_urls": [], "existing_url_quality": [],
            "is_new_url_candidate": False, "quality_upgrade_candidate": False,
            "recommended_action": "review",
        },
        {
            "db_school_id": 99, "db_school_name": "X", "pdf_school_name": "X",
            "pdf_school_code": None, "pdf_address": "", "pdf_operator": "",
            "pref_url": "https://example.com/", "url_quality": "homepage",
            "match_strategy": "exact", "existing_urls": ["https://example.com/x.pdf"],
            "existing_url_quality": ["direct_pdf"],
            "is_new_url_candidate": False, "quality_upgrade_candidate": False,
            "recommended_action": "noop",
        },
    ]

    stats = apply_writer_plan(db_session, report)
    db_session.commit()
    assert stats == {"added": 0, "upgraded": 0, "skipped": 2}
    assert db_session.query(SchoolSite).count() == 0


def test_aggregate_dispatches_parse_and_match(monkeypatch, db_session, tmp_path):
    """End-to-end: ``aggregate`` ties parse → build_indices → match →
    build_report. We stub parse() so we don't depend on a real PDF."""
    from contextlib import contextmanager

    from eidp.db.models import School
    from eidp.scraper import prefecture_aggregator as pa

    s = School(prefecture="埼玉県", corporation_name="学校法人A", school_name="埼玉専門学校", status="active")
    db_session.add(s)
    db_session.commit()

    @contextmanager
    def fake_pdf_open(_path):
        class FakePage:
            def extract_tables(self):
                return [[
                    ["埼玉専門学校", "埼玉県", "学校法人A", "埼玉県", ""],
                ]]

        class FakePdf:
            pages = [FakePage()]

        yield FakePdf()

    monkeypatch.setattr(pa.pdfplumber, "open", fake_pdf_open)
    monkeypatch.setattr(
        pa, "extract_pdf_annotation_links",
        lambda _p: {pa.norm("埼玉専門学校"): "https://example.com/agg.pdf"},
    )

    report = pa.aggregate(db_session, "saitama", tmp_path / "fake.pdf")
    assert report.extracted_total == 1
    assert report.db_matched == 1
    assert report.action_distribution.get("add") == 1
    assert report.records[0]["recommended_action"] == "add"
