from __future__ import annotations

import json
import socket
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from eidp.db.models import Base, School, SchoolSite
from eidp.scraper import url_discovery
from eidp.scraper.search_provider import SearchResult

REPO_ROOT = Path(__file__).resolve().parents[2]


def _session() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return Session(engine)


def test_is_safe_url_rejects_raw_control_characters_before_urlparse() -> None:
    assert not url_discovery._is_safe_url("https://www.\nogosejidai.ac.jp/file.pdf")
    assert not url_discovery._is_safe_url("https://example.ac.jp/\rfile.pdf")
    assert not url_discovery._is_safe_url("https://example.ac.jp/\tfile.pdf")


def test_is_safe_url_uses_bounded_cached_dns_resolution(monkeypatch) -> None:
    calls: list[tuple[str, float | None]] = []
    original_timeout = socket.getdefaulttimeout()

    def fake_getaddrinfo(host: str, *_args: object) -> list[tuple[int, int, int, str, tuple[str, int]]]:
        assert url_discovery._DNS_RESOLUTION_LOCK.locked()
        calls.append((host, socket.getdefaulttimeout()))
        return [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("93.184.216.34", 0))]

    url_discovery._resolve_host_addresses_for_safety.cache_clear()
    monkeypatch.setattr(url_discovery.socket, "getaddrinfo", fake_getaddrinfo)

    try:
        assert url_discovery._is_safe_url("https://slow-dns.example.ac.jp/disclosure/")
        assert url_discovery._is_safe_url("https://slow-dns.example.ac.jp/other/")
        assert calls == [("slow-dns.example.ac.jp", url_discovery.DNS_SAFETY_TIMEOUT_SECONDS)]
        assert socket.getdefaulttimeout() == original_timeout
    finally:
        url_discovery._resolve_host_addresses_for_safety.cache_clear()


def test_is_safe_url_refreshes_dns_cache_after_ttl_bucket_changes(monkeypatch) -> None:
    calls: list[str] = []
    bucket = 1

    def fake_cache_bucket() -> int:
        return bucket

    def fake_getaddrinfo(host: str, *_args: object) -> list[tuple[int, int, int, str, tuple[str, int]]]:
        calls.append(host)
        if len(calls) == 1:
            return [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("93.184.216.34", 0))]
        return [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("10.0.0.1", 0))]

    url_discovery._resolve_host_addresses_for_safety.cache_clear()
    monkeypatch.setattr(url_discovery, "_dns_safety_cache_bucket", fake_cache_bucket)
    monkeypatch.setattr(url_discovery.socket, "getaddrinfo", fake_getaddrinfo)

    try:
        assert url_discovery._is_safe_url("https://ttl-refresh.example.ac.jp/disclosure/")
        assert url_discovery._is_safe_url("https://ttl-refresh.example.ac.jp/other/")
        assert calls == ["ttl-refresh.example.ac.jp"]

        bucket = 2
        assert not url_discovery._is_safe_url("https://ttl-refresh.example.ac.jp/disclosure/")
        assert calls == ["ttl-refresh.example.ac.jp", "ttl-refresh.example.ac.jp"]
    finally:
        url_discovery._resolve_host_addresses_for_safety.cache_clear()


def test_is_safe_url_rejects_and_caches_dns_timeout(monkeypatch) -> None:
    calls: list[str] = []

    def fake_getaddrinfo(host: str, *_args: object) -> list[tuple[int, int, int, str, tuple[str, int]]]:
        calls.append(host)
        raise TimeoutError("dns timeout")

    url_discovery._resolve_host_addresses_for_safety.cache_clear()
    monkeypatch.setattr(url_discovery.socket, "getaddrinfo", fake_getaddrinfo)

    try:
        assert not url_discovery._is_safe_url("https://timeout.example.ac.jp/disclosure/")
        assert not url_discovery._is_safe_url("https://timeout.example.ac.jp/other/")
        assert calls == ["timeout.example.ac.jp"]
    finally:
        url_discovery._resolve_host_addresses_for_safety.cache_clear()


def test_import_seed_urls_reads_utf8_sig_csv(tmp_path: Path, monkeypatch) -> None:
    csv_path = tmp_path / "discovered-urls-50.csv"
    csv_path.write_text(
        "\ufeffprefecture,corporation,school_name,url_candidate_1,url_type,confidence,http_status\n"
        "東京都,学校法人テスト,日本語専門学校,https://example.edu/disclosure/,disclosure_page,0.9,200\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(url_discovery, "_is_safe_url", lambda url: True)

    session = _session()
    try:
        session.add(
            School(
                id=1,
                prefecture="東京都",
                corporation_name="学校法人テスト",
                school_name="日本語専門学校",
                status="active",
            )
        )
        session.commit()

        stats = url_discovery.import_seed_urls(session, csv_path)
        site = session.query(SchoolSite).one()

        assert stats == {"imported": 1, "skipped_no_school": 0, "skipped_existing": 0}
        assert site.url == "https://example.edu/disclosure/"
        assert site.discovery_method == "seed_csv"
    finally:
        session.close()


def test_load_corporation_domains_reads_utf8_sig_csv(tmp_path: Path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    csv_dir = data_dir / "url-discovery"
    csv_dir.mkdir(parents=True)
    (csv_dir / "corporation_domains.csv").write_text(
        "\ufeffcorporation_name,domain_url,notes\n"
        "学校法人テスト,https://corp.example,日本語メモ\n",
        encoding="utf-8",
    )
    domains = url_discovery._load_corporation_domains(data_dir=data_dir)

    assert domains == {"学校法人テスト": "https://corp.example"}


def test_load_school_domain_overrides_reads_utf8_sig_csv(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    csv_dir = data_dir / "url-discovery"
    csv_dir.mkdir(parents=True)
    (csv_dir / "school_domain_overrides.csv").write_text(
        "\ufeffprefecture,corporation_name,school_name,domain_url,url_type,confidence,notes\n"
        "東京都,日本教育財団,東京モード学園,https://www.mode.ac.jp/tokyo,school,0.95,multi-brand\n",
        encoding="utf-8",
    )

    overrides = url_discovery._load_school_domain_overrides(data_dir=data_dir)

    assert len(overrides) == 1
    assert overrides[0].school_name == "東京モード学園"
    assert overrides[0].domain_url == "https://www.mode.ac.jp/tokyo"
    assert overrides[0].confidence == 0.95


def test_checked_in_school_domain_overrides_cover_nkz_multibrand_schools() -> None:
    overrides = url_discovery._load_school_domain_overrides(data_dir=REPO_ROOT / "data")
    by_school = {
        (override.prefecture, override.school_name, override.domain_url)
        for override in overrides
    }

    expected = {
        ("東京都", "HAL東京", "https://www.nkz.ac.jp/clginfo/thinfo.html"),
        ("大阪府", "HAL大阪", "https://www.nkz.ac.jp/clginfo/ohinfo.html"),
        ("愛知県", "HAL名古屋", "https://www.nkz.ac.jp/clginfo/nhinfo.html"),
        ("東京都", "首都医校", "https://www.nkz.ac.jp/clginfo/siinfo.html"),
        ("大阪府", "大阪医専", "https://www.nkz.ac.jp/clginfo/oiinfo.html"),
        ("愛知県", "名古屋医専", "https://www.nkz.ac.jp/clginfo/niinfo.html"),
    }

    assert expected <= by_school


def test_checked_in_school_domain_overrides_cover_sanko_exact_school_sites() -> None:
    overrides = url_discovery._load_school_domain_overrides(data_dir=REPO_ROOT / "data")
    by_school = {
        (override.prefecture, override.school_name, override.domain_url)
        for override in overrides
    }

    expected = {
        ("千葉県", "千葉医療秘書&IT専門学校", "https://www.sanko.ac.jp/chiba-med/"),
        ("兵庫県", "神戸元町医療秘書専門学校", "https://www.sanko.ac.jp/kobe-med/"),
        ("福岡県", "福岡医療秘書福祉専門学校", "https://www.sanko.ac.jp/fukuoka-med/"),
        ("埼玉県", "大宮みらいAIアンドIT専門学校", "https://www.sanko.ac.jp/omiya-ai/"),
        ("東京都", "東京みらいAIアンドIT専門学校", "https://www.sanko.ac.jp/tokyo-ai/"),
        ("沖縄県", "沖縄みらいAIアンドIT専門学校", "https://www.sanko.ac.jp/okinawa-ai/"),
        ("千葉県", "千葉リゾート＆スポーツ専門学校", "https://www.sanko.ac.jp/chiba-sports/"),
        ("福岡県", "福岡リゾート＆スポーツ専門学校", "https://www.sanko.ac.jp/fukuoka-sports/"),
        ("北海道", "札幌ビューティアート専門学校", "https://www.sanko.ac.jp/sapporo-beauty/"),
        ("埼玉県", "大宮ビューティ＆ブライダル専門学校", "https://www.sanko.ac.jp/omiya-beauty/"),
        ("千葉県", "千葉ビューティ＆ブライダル専門学校", "https://www.sanko.ac.jp/chiba-beauty/"),
        ("東京都", "東京ビューティアート専門学校", "https://www.sanko.ac.jp/tokyo-beauty/"),
        ("神奈川県", "横浜ビューティアート専門学校", "https://www.sanko.ac.jp/yokohama-beauty/"),
        ("愛知県", "名古屋ビューティアート専門学校", "https://www.sanko.ac.jp/nagoya-beauty/"),
        ("大阪府", "大阪ビューティアート専門学校", "https://www.sanko.ac.jp/osaka-beauty/"),
        ("広島県", "広島ビューティ＆ブライダル専門学校", "https://www.sanko.ac.jp/hiroshima-beauty/"),
        ("福岡県", "福岡ビューティアート専門学校", "https://www.sanko.ac.jp/fukuoka-beauty/"),
        ("沖縄県", "沖縄ビューティ＆ブライダル専門学校", "https://www.sanko.ac.jp/okinawa-beauty/"),
        ("千葉県", "千葉こども専門学校", "https://www.sanko.ac.jp/chiba-child/"),
        ("兵庫県", "神戸元町こども専門学校", "https://www.sanko.ac.jp/kobe-child/"),
        ("福岡県", "福岡こども専門学校", "https://www.sanko.ac.jp/fukuoka-child/"),
        ("福岡県", "福岡ウェディング＆ブライダル専門学校", "https://www.sanko.ac.jp/fukuoka-bridal/"),
    }

    assert expected <= by_school


def test_checked_in_corporation_domains_cover_hachimonji_group() -> None:
    domains = url_discovery._load_corporation_domains(data_dir=REPO_ROOT / "data")

    assert domains["八文字学園"] == "https://www.mito.ac.jp/"


def test_infer_corporation_urls_prefers_school_domain_overrides(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    csv_dir = data_dir / "url-discovery"
    csv_dir.mkdir(parents=True)
    (csv_dir / "corporation_domains.csv").write_text(
        "corporation_name,domain_url,notes\n"
        "日本教育財団,https://www.nkz.ac.jp/,group portal\n",
        encoding="utf-8",
    )
    (csv_dir / "school_domain_overrides.csv").write_text(
        "prefecture,corporation_name,school_name,domain_url,url_type,confidence,notes\n"
        "東京都,日本教育財団,東京モード学園,https://www.mode.ac.jp/tokyo,school,0.95,mode\n"
        "大阪府,日本教育財団,大阪モード学園,https://www.mode.ac.jp/osaka,school,0.95,mode\n",
        encoding="utf-8",
    )
    session = _session()
    try:
        session.add_all(
            [
                School(
                    id=1,
                    prefecture="東京都",
                    corporation_name="日本教育財団",
                    school_name="東京モード学園",
                    school_type="専門学校",
                    status="active",
                ),
                School(
                    id=2,
                    prefecture="大阪府",
                    corporation_name="日本教育財団",
                    school_name="大阪モード学園",
                    school_type="専門学校",
                    status="active",
                ),
                School(
                    id=3,
                    prefecture="東京都",
                    corporation_name="日本教育財団",
                    school_name="HAL東京",
                    school_type="専門学校",
                    status="active",
                ),
            ]
        )
        session.commit()

        stats = url_discovery.infer_corporation_urls(session, data_dir=data_dir)
        sites = session.query(SchoolSite).order_by(SchoolSite.school_id.asc()).all()

        assert stats["inferred"] == 3
        assert stats["school_override_inferred"] == 2
        assert stats["skipped_has_url"] == 2
        assert [(site.school_id, site.url, site.discovery_method) for site in sites] == [
            (1, "https://www.mode.ac.jp/tokyo", "school_domain_override"),
            (2, "https://www.mode.ac.jp/osaka", "school_domain_override"),
            (3, "https://www.nkz.ac.jp/", "corporation_pattern"),
        ]
    finally:
        session.close()


def test_infer_school_domain_override_adds_alongside_existing_corporation_root(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    csv_dir = data_dir / "url-discovery"
    csv_dir.mkdir(parents=True)
    (csv_dir / "corporation_domains.csv").write_text(
        "corporation_name,domain_url,notes\n"
        "日本教育財団,https://www.nkz.ac.jp/,group portal\n",
        encoding="utf-8",
    )
    (csv_dir / "school_domain_overrides.csv").write_text(
        "prefecture,corporation_name,school_name,domain_url,url_type,confidence,notes\n"
        "東京都,日本教育財団,東京モード学園,https://www.mode.ac.jp/tokyo,school,0.95,mode\n",
        encoding="utf-8",
    )
    session = _session()
    try:
        session.add(
            School(
                id=1,
                prefecture="東京都",
                corporation_name="日本教育財団",
                school_name="東京モード学園",
                school_type="専門学校",
                status="active",
            )
        )
        session.add(
            SchoolSite(
                school_id=1,
                url="https://www.nkz.ac.jp/",
                url_type="corporation",
                discovery_method="corporation_pattern",
                confidence=0.5,
            )
        )
        session.commit()

        stats = url_discovery.infer_corporation_urls(session, data_dir=data_dir)
        sites = session.query(SchoolSite).order_by(SchoolSite.confidence.desc()).all()

        assert stats["school_override_inferred"] == 1
        assert [(site.url, site.discovery_method) for site in sites] == [
            ("https://www.mode.ac.jp/tokyo", "school_domain_override"),
            ("https://www.nkz.ac.jp/", "corporation_pattern"),
        ]
    finally:
        session.close()


def test_infer_school_domain_override_allows_multiple_urls_for_same_school(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    csv_dir = data_dir / "url-discovery"
    csv_dir.mkdir(parents=True)
    (csv_dir / "corporation_domains.csv").write_text(
        "corporation_name,domain_url,notes\n"
        "日本教育財団,https://www.nkz.ac.jp/,group portal\n",
        encoding="utf-8",
    )
    (csv_dir / "school_domain_overrides.csv").write_text(
        "prefecture,corporation_name,school_name,domain_url,url_type,confidence,notes\n"
        "東京都,日本教育財団,東京モード学園,https://www.mode.ac.jp/tokyo,school,0.95,brand homepage\n"
        "東京都,日本教育財団,東京モード学園,"
        "https://www.nkz.ac.jp/clginfo/tm/tmZ-studyspt_13.html,disclosure,0.98,target form page\n",
        encoding="utf-8",
    )
    session = _session()
    try:
        session.add(
            School(
                id=1,
                prefecture="東京都",
                corporation_name="日本教育財団",
                school_name="東京モード学園",
                school_type="専門学校",
                status="active",
            )
        )
        session.commit()

        stats = url_discovery.infer_corporation_urls(session, data_dir=data_dir)
        sites = session.query(SchoolSite).order_by(SchoolSite.confidence.desc(), SchoolSite.url.asc()).all()

        assert stats["school_override_inferred"] == 2
        assert stats["skipped_has_url"] == 1
        assert [(site.url, site.url_type, float(site.confidence)) for site in sites] == [
            (
                "https://www.nkz.ac.jp/clginfo/tm/tmZ-studyspt_13.html",
                "disclosure",
                0.98,
            ),
            ("https://www.mode.ac.jp/tokyo", "school", 0.95),
        ]
    finally:
        session.close()


def test_search_and_discover_registers_best_result(tmp_path: Path, monkeypatch) -> None:
    import time as time_module

    class FakeProvider:
        def name(self) -> str:
            return "fake"

        def search(self, query: str, count: int = 5) -> list[SearchResult]:
            return [
                SearchResult(
                    title="日本語専門学校 情報公開",
                    url="https://example.edu/disclosure/",
                    description="高等教育の修学支援新制度",
                )
            ]

    import eidp.scraper.search_provider as search_provider

    monkeypatch.setattr(search_provider, "create_provider", lambda **_kwargs: FakeProvider())
    monkeypatch.setattr(url_discovery, "_is_safe_url", lambda url: True)
    monkeypatch.setattr(time_module, "sleep", lambda _seconds: None)

    session = _session()
    try:
        session.add(
            School(
                id=1,
                prefecture="東京都",
                corporation_name="学校法人テスト",
                school_name="日本語専門学校",
                status="active",
            )
        )
        session.commit()

        evidence_path = tmp_path / "url_search_evidence.jsonl"
        stats = url_discovery.search_and_discover(session, batch_size=1, evidence_path=evidence_path)
        site = session.query(SchoolSite).one()
        evidence = json.loads(evidence_path.read_text(encoding="utf-8").splitlines()[0])

        assert stats == {"searched": 1, "found": 1, "no_result": 0, "errors": 0}
        assert site.url == "https://example.edu/disclosure/"
        assert site.discovery_method == "web_search"
        assert site.confidence > 0.9
        assert evidence["school_id"] == 1
        assert evidence["query"] == "日本語専門学校 情報公開 高等教育 修学支援"
        assert evidence["result_url"] == "https://example.edu/disclosure/"
        assert evidence["decision"] == "accepted"
        assert evidence["reason"] == "registered_school_site"
    finally:
        session.close()


def test_search_and_discover_uses_stable_school_order(monkeypatch) -> None:
    import time as time_module

    class FakeProvider:
        queries: list[str] = []

        def name(self) -> str:
            return "fake"

        def search(self, query: str, count: int = 5) -> list[SearchResult]:
            self.queries.append(query)
            return []

    provider = FakeProvider()

    import eidp.scraper.search_provider as search_provider

    monkeypatch.setattr(search_provider, "create_provider", lambda **_kwargs: provider)
    monkeypatch.setattr(url_discovery, "_is_safe_url", lambda url: True)
    monkeypatch.setattr(time_module, "sleep", lambda _seconds: None)

    session = _session()
    try:
        session.add_all(
            [
                School(
                    id=3,
                    prefecture="東京都",
                    corporation_name="法人C",
                    school_name="C専門学校",
                    school_type="専門学校",
                    status="active",
                ),
                School(
                    id=1,
                    prefecture="東京都",
                    corporation_name="法人A",
                    school_name="A専門学校",
                    school_type="専門学校",
                    status="active",
                ),
                School(
                    id=2,
                    prefecture="東京都",
                    corporation_name="法人B",
                    school_name="B専門学校",
                    school_type="専門学校",
                    status="active",
                ),
            ]
        )
        session.commit()

        stats = url_discovery.search_and_discover(session, batch_size=3, rate_limit_delay=0)

        assert stats == {"searched": 3, "found": 0, "no_result": 3, "errors": 0}
        assert provider.queries[0] == "A専門学校 情報公開 高等教育 修学支援"
        assert provider.queries[5] == "B専門学校 情報公開 高等教育 修学支援"
        assert provider.queries[10] == "C専門学校 情報公開 高等教育 修学支援"
    finally:
        session.close()


def test_search_and_discover_rejects_low_confidence_results(tmp_path: Path, monkeypatch) -> None:
    import time as time_module

    class FakeProvider:
        queries: list[str] = []

        def name(self) -> str:
            return "fake"

        def search(self, query: str, count: int = 5) -> list[SearchResult]:
            self.queries.append(query)
            return [
                SearchResult(
                    title="一般的なお知らせ",
                    url="https://unrelated.example/news/",
                    description="学校とは無関係のページ",
                )
            ]

    provider = FakeProvider()

    import eidp.scraper.search_provider as search_provider

    monkeypatch.setattr(search_provider, "create_provider", lambda **_kwargs: provider)
    monkeypatch.setattr(url_discovery, "_is_safe_url", lambda url: True)
    monkeypatch.setattr(time_module, "sleep", lambda _seconds: None)

    session = _session()
    try:
        session.add(
            School(
                id=1,
                prefecture="東京都",
                corporation_name="学校法人テスト",
                school_name="日本語専門学校",
                school_type="専門学校",
                status="active",
            )
        )
        session.commit()

        evidence_path = tmp_path / "url_search_evidence.jsonl"
        stats = url_discovery.search_and_discover(session, batch_size=1, evidence_path=evidence_path)
        evidence_rows = [
            json.loads(line) for line in evidence_path.read_text(encoding="utf-8").splitlines()
        ]

        assert stats == {"searched": 1, "found": 0, "no_result": 1, "errors": 0}
        assert session.query(SchoolSite).count() == 0
        assert provider.queries == url_discovery.search_queries_for_school(session.get(School, 1))
        assert len(evidence_rows) == len(provider.queries)
        assert {row["decision"] for row in evidence_rows} == {"rejected"}
        assert {row["reason"] for row in evidence_rows} == {"low_confidence"}
        assert all(row["result_url"] == "https://unrelated.example/news/" for row in evidence_rows)
    finally:
        session.close()


def test_search_and_discover_skips_third_party_directories_when_official_result_exists(
    tmp_path: Path,
    monkeypatch,
) -> None:
    import time as time_module

    class FakeProvider:
        def name(self) -> str:
            return "fake"

        def search(self, query: str, count: int = 5) -> list[SearchResult]:
            return [
                SearchResult(
                    title="日本語専門学校 | 資料請求",
                    url="https://shingakunet.com/gakko/SC000001/",
                    description="日本語専門学校の学校情報",
                ),
                SearchResult(
                    title="日本語専門学校 情報公開",
                    url="https://example.ac.jp/disclosure/",
                    description="高等教育の修学支援新制度",
                ),
            ]

    import eidp.scraper.search_provider as search_provider

    monkeypatch.setattr(search_provider, "create_provider", lambda **_kwargs: FakeProvider())
    monkeypatch.setattr(url_discovery, "_is_safe_url", lambda url: True)
    monkeypatch.setattr(time_module, "sleep", lambda _seconds: None)

    session = _session()
    try:
        session.add(
            School(
                id=1,
                prefecture="東京都",
                corporation_name="学校法人テスト",
                school_name="日本語専門学校",
                school_type="専門学校",
                status="active",
            )
        )
        session.commit()

        evidence_path = tmp_path / "url_search_evidence.jsonl"
        stats = url_discovery.search_and_discover(session, batch_size=1, evidence_path=evidence_path)
        site = session.query(SchoolSite).one()
        evidence_rows = [
            json.loads(line) for line in evidence_path.read_text(encoding="utf-8").splitlines()
        ]

        assert stats == {"searched": 1, "found": 1, "no_result": 0, "errors": 0}
        assert site.url == "https://example.ac.jp/disclosure/"
        assert any(row["reason"] == "third_party_directory_domain" for row in evidence_rows)
        assert evidence_rows[-1]["decision"] == "accepted"
        assert evidence_rows[-1]["result_url"] == "https://example.ac.jp/disclosure/"
    finally:
        session.close()


def test_search_and_discover_rejects_government_index_as_school_site(
    tmp_path: Path,
    monkeypatch,
) -> None:
    import time as time_module

    class FakeProvider:
        def name(self) -> str:
            return "fake"

        def search(self, query: str, count: int = 5) -> list[SearchResult]:
            return [
                SearchResult(
                    title="日本語専門学校 修学支援対象校",
                    url="https://www.mext.go.jp/a_menu/koutou/hutankeigen/index.htm",
                    description="日本語専門学校 高等教育の修学支援新制度",
                )
            ]

    import eidp.scraper.search_provider as search_provider

    monkeypatch.setattr(search_provider, "create_provider", lambda **_kwargs: FakeProvider())
    monkeypatch.setattr(url_discovery, "_is_safe_url", lambda url: True)
    monkeypatch.setattr(time_module, "sleep", lambda _seconds: None)

    session = _session()
    try:
        session.add(
            School(
                id=1,
                prefecture="東京都",
                corporation_name="学校法人テスト",
                school_name="日本語専門学校",
                school_type="専門学校",
                status="active",
            )
        )
        session.commit()

        evidence_path = tmp_path / "url_search_evidence.jsonl"
        stats = url_discovery.search_and_discover(session, batch_size=1, evidence_path=evidence_path)
        evidence_rows = [
            json.loads(line) for line in evidence_path.read_text(encoding="utf-8").splitlines()
        ]

        assert stats == {"searched": 1, "found": 0, "no_result": 1, "errors": 0}
        assert session.query(SchoolSite).count() == 0
        assert {row["reason"] for row in evidence_rows} == {"government_index_domain"}
        assert {row["decision"] for row in evidence_rows} == {"rejected"}
    finally:
        session.close()


def test_search_and_discover_accepts_corporation_description_match(monkeypatch) -> None:
    import time as time_module

    class FakeProvider:
        def name(self) -> str:
            return "fake"

        def search(self, query: str, count: int = 5) -> list[SearchResult]:
            return [
                SearchResult(
                    title="情報公開",
                    url="https://corp.example/disclosure/",
                    description="学校法人テストが公開する高等教育の修学支援新制度",
                )
            ]

    import eidp.scraper.search_provider as search_provider

    monkeypatch.setattr(search_provider, "create_provider", lambda **_kwargs: FakeProvider())
    monkeypatch.setattr(url_discovery, "_is_safe_url", lambda url: True)
    monkeypatch.setattr(time_module, "sleep", lambda _seconds: None)

    session = _session()
    try:
        session.add(
            School(
                id=1,
                prefecture="東京都",
                corporation_name="学校法人テスト",
                school_name="東京デザイン学院",
                school_type="専門学校",
                status="active",
            )
        )
        session.commit()

        stats = url_discovery.search_and_discover(session, batch_size=1)
        site = session.query(SchoolSite).one()

        assert stats == {"searched": 1, "found": 1, "no_result": 0, "errors": 0}
        assert site.url == "https://corp.example/disclosure/"
        assert site.confidence >= url_discovery.SEARCH_RESULT_MIN_CONFIDENCE
    finally:
        session.close()


def test_search_queries_use_university_terms_for_universities() -> None:
    school = School(
        id=1,
        prefecture="東京都",
        corporation_name="公立大学法人テスト",
        school_name="東京都立大学",
        school_type="大学",
        status="active",
    )

    queries = url_discovery.search_queries_for_school(school)

    assert "東京都立大学 情報公開 高等教育 修学支援" in queries
    assert "東京都立大学 確認申請書 様式第2号" in queries
    assert "公立大学法人テスト 東京都立大学 情報公開" in queries
    assert all("専門学校" not in query for query in queries)
    assert queries[-1] == "東京都立大学 公式"


def test_search_queries_keep_vocational_homepage_terms_for_senmon() -> None:
    school = School(
        id=1,
        prefecture="東京都",
        corporation_name="学校法人テスト",
        school_name="東京デザイン学院",
        school_type="専門学校",
        status="active",
    )

    queries = url_discovery.search_queries_for_school(school)

    assert "東京デザイン学院 専門学校" in queries
    assert "学校法人テスト 東京デザイン学院 情報公開" in queries


def test_search_queries_add_ampersand_variant_for_and_named_schools() -> None:
    school = School(
        id=1,
        prefecture="埼玉県",
        corporation_name="三幸学園",
        school_name="大宮みらいAIアンドIT専門学校",
        school_type="専門学校",
        status="active",
    )

    queries = url_discovery.search_queries_for_school(school)

    assert "大宮みらいAI&IT専門学校 情報公開" in queries
    assert "三幸学園 大宮みらいAI&IT専門学校 情報公開" in queries
    assert "大宮みらいAI&IT専門学校 公式" in queries


def test_search_queries_support_junior_college_and_kosen_terms() -> None:
    junior_college = School(
        id=1,
        prefecture="東京都",
        corporation_name="学校法人テスト",
        school_name="東京短期カレッジ",
        school_type="短期大学",
        status="active",
    )
    kosen = School(
        id=2,
        prefecture="東京都",
        corporation_name="学校法人テスト",
        school_name="東京工業高専",
        school_type="高等専門学校",
        status="active",
    )

    assert "東京短期カレッジ 短期大学" in url_discovery.search_queries_for_school(junior_college)
    assert "東京工業高専 高等専門学校" in url_discovery.search_queries_for_school(kosen)


def test_verify_urls_sync_does_not_stamp_prefecture_aggregator_verified_at(monkeypatch) -> None:
    class FakeResponse:
        status_code = 200
        headers: dict[str, str] = {}
        url = "https://example.ac.jp/disclosure/"

    class FakeClient:
        def __init__(self, **_kwargs):  # noqa: ANN001
            pass

        def __enter__(self):  # noqa: ANN204
            return self

        def __exit__(self, *_args):  # noqa: ANN002, ANN204
            return None

        def head(self, _url: str) -> FakeResponse:
            return FakeResponse()

    monkeypatch.setattr(url_discovery.httpx, "Client", FakeClient)
    monkeypatch.setattr(url_discovery, "_is_safe_url", lambda _url: True)

    session = _session()
    try:
        session.add(
            SchoolSite(
                school_id=1,
                url="https://example.ac.jp/disclosure/",
                url_type="disclosure",
                discovery_method="prefecture_aggregator",
            )
        )
        session.flush()

        stats = url_discovery.verify_urls_sync(session, batch_size=1)
        site = session.query(SchoolSite).one()

        assert stats == {"checked": 1, "ok": 1, "failed": 0, "timeout": 0}
        assert site.http_status == 200
        assert site.verified is True
        assert site.last_checked is not None
        assert site.verified_at is None
    finally:
        session.close()


def test_verify_urls_sync_uses_stable_site_order(monkeypatch) -> None:
    calls: list[str] = []

    class FakeResponse:
        status_code = 200
        headers: dict[str, str] = {}

        def __init__(self, url: str) -> None:
            self.url = url

    class FakeClient:
        def __init__(self, **_kwargs):  # noqa: ANN001
            pass

        def __enter__(self):  # noqa: ANN204
            return self

        def __exit__(self, *_args):  # noqa: ANN002, ANN204
            return None

        def head(self, url: str) -> FakeResponse:
            calls.append(url)
            return FakeResponse(url)

    monkeypatch.setattr(url_discovery.httpx, "Client", FakeClient)
    monkeypatch.setattr(url_discovery, "_is_safe_url", lambda _url: True)

    session = _session()
    try:
        session.add_all(
            [
                SchoolSite(school_id=3, url="https://example.ac.jp/school-3/"),
                SchoolSite(school_id=1, url="https://example.ac.jp/school-1/"),
                SchoolSite(school_id=2, url="https://example.ac.jp/school-2/"),
            ]
        )
        session.flush()

        stats = url_discovery.verify_urls_sync(session, batch_size=3)

        assert stats == {"checked": 3, "ok": 3, "failed": 0, "timeout": 0}
        assert calls == [
            "https://example.ac.jp/school-1/",
            "https://example.ac.jp/school-2/",
            "https://example.ac.jp/school-3/",
        ]
    finally:
        session.close()
