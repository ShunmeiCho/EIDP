from __future__ import annotations

from eidp.scraper.url_normalization import normalize_candidate_url


def test_normalize_candidate_url_drops_wpdmdl_refresh_cache_buster() -> None:
    first = "https://i-heiseigakuen.ac.jp/download/yousiki2/?wpdmdl=5471&refresh=abc"
    second = "https://i-heiseigakuen.ac.jp/download/yousiki2/?refresh=def&wpdmdl=5471"

    assert normalize_candidate_url(first) == normalize_candidate_url(second)
    assert normalize_candidate_url(first) == "https://i-heiseigakuen.ac.jp/download/yousiki2?wpdmdl=5471"


def test_normalize_candidate_url_keeps_non_wpdmdl_refresh_parameter() -> None:
    url = "https://example.ac.jp/download/form.pdf?refresh=abc"

    assert normalize_candidate_url(url) == "https://example.ac.jp/download/form.pdf?refresh=abc"
