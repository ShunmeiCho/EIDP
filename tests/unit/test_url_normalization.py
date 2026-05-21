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


def test_normalize_candidate_url_drops_tracking_query_parameters() -> None:
    url = (
        "https://example.ac.jp/disclosure/form.pdf"
        "?utm_source=newsletter&b=2&gclid=abc&utm_medium=email&a=1"
    )

    assert normalize_candidate_url(url) == "https://example.ac.jp/disclosure/form.pdf?a=1&b=2"


def test_normalize_candidate_url_keeps_non_tracking_query_parameters() -> None:
    url = "https://example.ac.jp/download.php?file=form.pdf&token=abc&utm_campaign=ignored"

    assert normalize_candidate_url(url) == "https://example.ac.jp/download.php?file=form.pdf&token=abc"


def test_normalize_candidate_url_is_idempotent_after_tracking_drop() -> None:
    url = "HTTPS://Example.ac.jp//Disclosure//form.pdf?utm_source=x&z=9&a=1#section"
    once = normalize_candidate_url(url)

    assert normalize_candidate_url(once) == once
