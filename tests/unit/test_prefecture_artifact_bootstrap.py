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
    }
