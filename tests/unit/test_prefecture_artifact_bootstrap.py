from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

script = Path(__file__).resolve().parents[2] / "scripts" / "download_prefecture_artifacts.py"
spec = importlib.util.spec_from_file_location("download_prefecture_artifacts", script)
assert spec is not None
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules["download_prefecture_artifacts"] = module
spec.loader.exec_module(module)


def test_artifact_selection_includes_registered_supported_artifacts() -> None:
    rows = [
        {
            "pref_key": "hokkaido",
            "verified_status": "url_found",
            "artifact_url": "https://www.pref.hokkaido.lg.jp/r8.pdf",
        },
        {
            "pref_key": "osaka",
            "verified_status": "spiked",
            "artifact_url": "https://www.pref.osaka.lg.jp/r8.xlsx",
        },
        {
            "pref_key": "aichi",
            "verified_status": "downloaded",
            "artifact_url": "https://www.pref.aichi.jp/soshiki/shigaku/kikanyoukenkakunin.html",
        },
        {
            "pref_key": "niigata",
            "verified_status": "downloaded",
            "artifact_url": "https://www.pref.niigata.lg.jp/r7.pdf",
        },
        {
            "pref_key": "yamagata",
            "verified_status": "url_found",
            "artifact_url": "https://www.pref.yamagata.jp/r8.pdf",
        },
        {
            "pref_key": "kumamoto",
            "verified_status": "downloaded",
            "artifact_url": "https://www.pref.kumamoto.jp/r7.pdf",
        },
        {
            "pref_key": "hiroshima",
            "verified_status": "url_found",
            "artifact_url": "https://www.pref.hiroshima.lg.jp/soshiki/44/605623.html",
        },
        {
            "pref_key": "kyoto",
            "verified_status": "url_found",
            "artifact_url": "https://www.pref.kyoto.jp/bunkyo/documents/taisyoukou-itiran070924.pdf",
        },
        {
            "pref_key": "iwate",
            "verified_status": "url_found",
            "artifact_url": "https://www.pref.iwate.jp/kyouikubunka/kyouiku/1031406/1032859.html",
        },
        {
            "pref_key": "toyama",
            "verified_status": "url_found",
            "artifact_url": "https://www.pref.toyama.jp/1119/kurashi/kyouiku/gakkou/shuugakushien/kj00020807.html",
        },
        {
            "pref_key": "fukushima",
            "verified_status": "url_found",
            "artifact_url": "https://www.pref.fukushima.lg.jp/uploaded/attachment/705531.pdf",
        },
        {
            "pref_key": "ishikawa",
            "verified_status": "url_found",
            "artifact_url": "https://www.pref.ishikawa.lg.jp/soumu/documents/2026_kikanyoukenkakunin20260401.pdf",
        },
        {
            "pref_key": "yamanashi",
            "verified_status": "url_found",
            "artifact_url": "https://www.pref.yamanashi.jp/shigaku-kgk/koutousyuugaku/ichiran.html",
        },
        {
            "pref_key": "gifu",
            "verified_status": "url_found",
            "artifact_url": "https://www.pref.gifu.lg.jp/page/22667.html",
        },
        {
            "pref_key": "mie",
            "verified_status": "url_found",
            "artifact_url": "https://www.pref.mie.lg.jp/common/content/001153973.pdf",
        },
        {
            "pref_key": "shiga",
            "verified_status": "url_found",
            "artifact_url": "https://www.pref.shiga.lg.jp/file/attachment/5557400.pdf",
        },
        {
            "pref_key": "nara",
            "verified_status": "url_found",
            "artifact_url": "https://www.pref.nara.lg.jp/n056/53083.html",
        },
        {
            "pref_key": "shimane",
            "verified_status": "url_found",
            "artifact_url": "https://www.pref.shimane.lg.jp/education/kyoiku/shugaku_shien/list/taishoukikan.html",
        },
        {
            "pref_key": "okayama",
            "verified_status": "url_found",
            "artifact_url": "https://www.pref.okayama.jp/page/626761.html",
        },
        {
            "pref_key": "tokushima",
            "verified_status": "url_found",
            "artifact_url": "https://www.pref.tokushima.lg.jp/file/attachment/1008445.pdf",
        },
        {
            "pref_key": "kagawa",
            "verified_status": "url_found",
            "artifact_url": "https://www.pref.kagawa.lg.jp/somugakuji/sigaku/keigen/w1mhal190827170447.html",
        },
        {
            "pref_key": "ehime",
            "verified_status": "url_found",
            "artifact_url": "https://www.pref.ehime.jp/uploaded/attachment/156605.xlsx",
        },
        {
            "pref_key": "kochi",
            "verified_status": "url_found",
            "artifact_url": "https://www.pref.kochi.lg.jp/doc/hutankeigen/",
        },
        {
            "pref_key": "saga",
            "verified_status": "url_found",
            "artifact_url": "https://www.pref.saga.lg.jp/kiji00370455/index.html",
        },
        {
            "pref_key": "nagasaki",
            "verified_status": "url_found",
            "artifact_url": "https://www.pref.nagasaki.jp/doc/page-679908.html",
        },
    ]

    targets = module.select_targets(rows)
    pref_keys = {row["pref_key"] for row in targets}

    assert "hokkaido" in module.SUPPORTED_PARSERS
    assert "osaka" in module.SUPPORTED_PARSERS
    assert "aichi" in module.SUPPORTED_PARSERS
    assert "niigata" in module.SUPPORTED_PARSERS
    assert "yamagata" in module.SUPPORTED_PARSERS
    assert "kumamoto" in module.SUPPORTED_PARSERS
    assert "hiroshima" in module.SUPPORTED_PARSERS
    assert "kyoto" in module.SUPPORTED_PARSERS
    assert "iwate" in module.SUPPORTED_PARSERS
    assert "toyama" in module.SUPPORTED_PARSERS
    assert "fukushima" in module.SUPPORTED_PARSERS
    assert "ishikawa" in module.SUPPORTED_PARSERS
    assert "yamanashi" in module.SUPPORTED_PARSERS
    assert "gifu" in module.SUPPORTED_PARSERS
    assert "mie" in module.SUPPORTED_PARSERS
    assert "shiga" in module.SUPPORTED_PARSERS
    assert "nara" in module.SUPPORTED_PARSERS
    assert "shimane" in module.SUPPORTED_PARSERS
    assert "okayama" in module.SUPPORTED_PARSERS
    assert "tokushima" in module.SUPPORTED_PARSERS
    assert "kagawa" in module.SUPPORTED_PARSERS
    assert "ehime" in module.SUPPORTED_PARSERS
    assert "kochi" in module.SUPPORTED_PARSERS
    assert "saga" in module.SUPPORTED_PARSERS
    assert "nagasaki" in module.SUPPORTED_PARSERS
    assert "url_found" in module.DOWNLOADABLE_STATUSES
    assert pref_keys == {
        "hokkaido",
        "osaka",
        "aichi",
        "niigata",
        "yamagata",
        "kumamoto",
        "hiroshima",
        "kyoto",
        "iwate",
        "toyama",
        "fukushima",
        "ishikawa",
        "yamanashi",
        "gifu",
        "mie",
        "shiga",
        "nara",
        "shimane",
        "okayama",
        "tokushima",
        "kagawa",
        "ehime",
        "kochi",
        "saga",
        "nagasaki",
    }


def test_artifact_download_targets_include_supplemental_urls() -> None:
    row = {
        "pref_key": "hyogo",
        "artifact_url": "https://pref.example/current.pdf",
        "artifact_format": "pdf",
        "supplemental_artifact_urls": "https://pref.example/r1.pdf|https://pref.example/r2.xlsx",
    }

    assert module.artifact_download_targets(row) == [
        ("https://pref.example/current.pdf", "hyogo.pdf"),
        ("https://pref.example/r1.pdf", "hyogo__01.pdf"),
        ("https://pref.example/r2.xlsx", "hyogo__02.xlsx"),
    ]


def test_artifact_download_targets_ignore_blank_supplemental_values() -> None:
    row = {
        "pref_key": "tokyo",
        "artifact_url": "https://pref.example/current",
        "artifact_format": "pdf",
        "supplemental_artifact_urls": " | not-a-url | https://pref.example/r1.htm",
    }

    assert module.artifact_download_targets(row) == [
        ("https://pref.example/current", "tokyo.pdf"),
        ("https://pref.example/r1.htm", "tokyo__01.html"),
    ]
