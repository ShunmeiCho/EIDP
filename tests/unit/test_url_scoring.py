"""Tests for src/eidp/scraper/url_scoring.py."""

from __future__ import annotations

import pytest

from eidp.scraper.url_scoring import (
    UrlScore,
    UrlScoreThresholds,
    best_candidate,
    score_school_url_candidate,
    thresholds_from_env,
)


def _score(
    url: str,
    *,
    school: str = "東京デザイン専門学校",
    pref: str = "東京都",
    title: str | None = None,
    excerpt: str | None = None,
) -> UrlScore:
    return score_school_url_candidate(
        candidate_url=url,
        school_name=school,
        prefecture=pref,
        page_title=title,
        page_excerpt=excerpt,
    )


def test_invalid_scheme_is_rejected():
    s = _score("ftp://example.ac.jp/")
    assert s.decision == "reject"
    assert "invalid_url" in s.notes


def test_third_party_directory_is_rejected_with_negative_score():
    s = _score("https://www.shingakunet.com/school/SC123456/")
    assert s.decision == "reject"
    assert s.score < 0
    assert "blacklisted_third_party_directory" in s.notes


def test_sns_domain_is_rejected():
    s = _score("https://www.facebook.com/tokyo-design-school/")
    assert s.decision == "reject"
    assert "blacklisted_sns_or_jobboard" in s.notes


def test_academic_tld_with_name_token_is_auto():
    # School name carries an ASCII token that appears in the hostname; this
    # is the realistic case for vocational schools that publish a romaji
    # brand inside their official Japanese name.
    s = _score(
        "https://www.tdg.ac.jp/",
        school="東京デザイナー学院TDG",
        pref="東京都",
        title="東京デザイナー学院TDG 公式サイト",
        excerpt="本校の公式ホームページです。情報公開ページはこちら。",
    )
    assert s.decision == "auto"
    assert s.score >= 6.0
    assert "domain_tld" in s.breakdown
    assert "domain_name_match" in s.breakdown
    assert "page_title_match" in s.breakdown
    assert "disclosure_keyword" in s.breakdown


def test_kanji_area_name_matches_romanized_host():
    s = _score(
        "https://www.tokyo-design.ac.jp/",
        school="東京デザイン専門学校",
        pref="東京都",
    )
    assert s.breakdown.get("domain_name_match") == pytest.approx(2.0)
    assert "name_token=tokyo-design" in s.notes


def test_katakana_alias_matches_english_host_token():
    s = _score(
        "https://saitama-it-tech.ac.jp/",
        school="埼玉ITテック専門学校",
        pref="埼玉県",
    )
    assert s.breakdown.get("domain_name_match") == pytest.approx(2.0)


def test_neutral_jp_with_disclosure_excerpt_falls_to_review():
    s = _score(
        "https://design-school-tokyo.jp/info",
        school="東京デザイナー学院TDG",
        pref="東京都",
        title=None,
        excerpt="本校の情報公開ページです",
    )
    # +1 jp + +1 prefecture + +1 disclosure = 3.0 (<4.0 review threshold)
    assert s.score == pytest.approx(3.0)
    assert s.decision == "reject"


def test_pure_negative_tld_with_no_signals_is_reject():
    s = _score("https://random-design-blog.com/")
    assert s.decision == "reject"
    assert s.score <= 0


def test_prefecture_romaji_matches_in_path():
    s = _score(
        "https://example.ac.jp/saitama/info",
        school="埼玉ITテック専門学校",
        pref="埼玉県",
    )
    assert "prefecture_in_url" in s.breakdown


def test_prefecture_kanji_matches_in_host():
    s = _score(
        "https://saitama-design.example.ac.jp/",
        school="埼玉ITテック専門学校",
        pref="埼玉県",
    )
    assert "prefecture_in_url" in s.breakdown


def test_thresholds_validate_ordering():
    with pytest.raises(ValueError):
        UrlScoreThresholds(auto=4.0, review=6.0)


def test_thresholds_from_env_uses_defaults_when_missing():
    th = thresholds_from_env(env={})
    assert th.auto == pytest.approx(6.0)
    assert th.review == pytest.approx(4.0)


def test_thresholds_from_env_clamps_review_above_auto():
    th = thresholds_from_env(env={"EIDP_URL_SCORE_AUTO": "5.0", "EIDP_URL_SCORE_REVIEW": "8.0"})
    assert th.review == pytest.approx(5.0)


def test_thresholds_from_env_falls_back_on_garbage():
    th = thresholds_from_env(env={"EIDP_URL_SCORE_AUTO": "not-a-number"})
    assert th.auto == pytest.approx(6.0)


def test_best_candidate_picks_highest_eligible():
    a = _score(
        "https://www.tokyo-design.ac.jp/",
        title="東京デザイン専門学校 公式",
        excerpt="情報公開",
    )
    b = _score("https://random.com/")
    c = _score(
        "https://design-tokyo.jp/",
        school="東京デザイン専門学校",
        pref="東京都",
    )
    best = best_candidate([a, b, c])
    assert best is not None
    assert best.candidate_url == a.candidate_url


def test_best_candidate_returns_none_when_all_rejected():
    a = _score("https://www.shingakunet.com/")
    b = _score("https://www.facebook.com/x")
    assert best_candidate([a, b]) is None


def test_best_candidate_returns_none_for_empty_input():
    assert best_candidate([]) is None


def test_romaji_school_name_matches_lowercase_host():
    s = _score(
        "https://www.abkcollege.ac.jp/",
        school="ABK COLLEGE",
        pref="東京都",
    )
    assert "domain_name_match" in s.breakdown


def test_official_word_in_excerpt_adds_signal():
    s = _score(
        "https://example.ac.jp/",
        excerpt="このサイトは公式の情報公開ページです",
    )
    assert s.breakdown.get("official_word") == pytest.approx(0.5)
    assert s.breakdown.get("disclosure_keyword") == pytest.approx(1.0)


def test_disclosure_keyword_only_present_when_excerpt_supplied():
    s = _score("https://example.ac.jp/", excerpt=None)
    assert "disclosure_keyword" not in s.breakdown


def test_negative_tld_subtracts_one():
    s = _score(
        "https://example.com/",
        school="東京デザイン専門学校",
        pref="東京都",
    )
    assert s.breakdown.get("domain_tld") == pytest.approx(-1.0)


def test_url_score_is_frozen_dataclass():
    s = _score("https://example.ac.jp/")
    with pytest.raises((AttributeError, Exception)):
        s.score = 99.0  # type: ignore[misc]
