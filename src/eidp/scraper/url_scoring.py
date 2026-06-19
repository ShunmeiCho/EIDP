"""Score candidate URLs as a school's official website (v104+).

Decision layer between a SERP-style list of candidate URLs and the
SchoolSite registration step. Kept separate from any fetch / scrape code so
the scoring rules are testable in isolation and so future channels (Scrapling
stealth crawler, LLM-assisted recall, operator manual import) all flow
through the same acceptance contract.

Scoring rules (point-based, additive):

* Domain TLD bonus
    .ac.jp / .ed.jp / .lg.jp -> +3 (Japanese academic / education / local gov)
    .or.jp / .jp                -> +1
    .com / .net / .org / .info -> -1 (rarely the official school domain)

* School-name token in domain
    school name has any token of >=2 chars that appears in hostname -> +2

* Prefecture token in domain or path
    prefecture name (kanji or romaji) appears anywhere in URL -> +1

* Page title carries the school name
    full school name in title -> +2
    partial (substring or normalized variant) -> +1

* Disclosure / target form keyword visible in the page excerpt
    page contains "情報公開" / "修学支援" / "機関要件" -> +1

* Operator-friendly signal
    page text contains "公式" / "official" -> +0.5

* Hard penalties
    third-party directory hostname (gakkou-net etc.) -> -5
    SNS / blog / job-board / news-aggregator -> -5

Decision thresholds (env-tunable):

* score >= AUTO_THRESHOLD (default 6.0) -> "auto"   (register SchoolSite)
* AUTO > score >= REVIEW (4.0)          -> "review" (enqueue ReviewItem)
* score < REVIEW                         -> "reject" (log only)

Environment overrides:

* EIDP_URL_SCORE_AUTO    (float, default 6.0)
* EIDP_URL_SCORE_REVIEW  (float, default 4.0)
"""

from __future__ import annotations

import os
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Final, Literal
from urllib.parse import urlparse

from eidp.scraper.url_discovery import THIRD_PARTY_DIRECTORY_HOST_SUFFIXES

UrlScoreDecision = Literal["auto", "review", "reject"]


_ACADEMIC_TLDS: Final = (".ac.jp", ".ed.jp", ".lg.jp")
_NEUTRAL_TLDS: Final = (".or.jp", ".jp")
_NEGATIVE_TLDS: Final = (".com", ".net", ".org", ".info", ".biz")

_SNS_HOST_SUFFIXES: Final = (
    "facebook.com",
    "twitter.com",
    "x.com",
    "instagram.com",
    "youtube.com",
    "youtu.be",
    "tiktok.com",
    "linkedin.com",
    "note.com",
    "ameblo.jp",
    "fc2.com",
    "blog.livedoor.jp",
    "hatenablog.com",
    "wantedly.com",
    "rikunabi.com",
    "mynavi.jp",
    "indeed.com",
    "doda.jp",
)

_DISCLOSURE_KEYWORDS: Final = (
    "情報公開",
    "公開情報",
    "教育情報",
    "公表",
    "修学支援",
    "高等教育",
    "無償化",
    "確認申請",
    "機関要件",
)

_OFFICIAL_WORDS: Final = ("公式", "official", "公式サイト", "公式ホームページ")

_LOW_VALUE_PATH_PENALTIES: Final = (
    ("form_download", -3.0),
    ("admission", -3.0),
    ("/admis", -3.0),
    ("/enter", -2.0),
    ("application", -3.0),
    ("/archives/news", -2.0),
    ("/news", -2.0),
    ("/event", -2.0),
    ("opencampus", -2.0),
)

_PUBLIC_SCHOOL_NAME_MARKERS: Final = (
    "国立", "公立",
    "都立", "道立", "府立", "県立",
    "市立", "町立", "村立",
    "県農業大学校",
)

_DEFAULT_AUTO_THRESHOLD: Final = 6.0
_DEFAULT_REVIEW_THRESHOLD: Final = 4.0

# MEXT-conventional romaji for prefecture name matching against domains/paths.
_PREFECTURE_ROMAJI: Final = {
    "北海道": "hokkaido",
    "青森県": "aomori", "岩手県": "iwate", "宮城県": "miyagi", "秋田県": "akita",
    "山形県": "yamagata", "福島県": "fukushima", "茨城県": "ibaraki", "栃木県": "tochigi",
    "群馬県": "gunma", "埼玉県": "saitama", "千葉県": "chiba", "東京都": "tokyo",
    "神奈川県": "kanagawa", "新潟県": "niigata", "富山県": "toyama", "石川県": "ishikawa",
    "福井県": "fukui", "山梨県": "yamanashi", "長野県": "nagano", "岐阜県": "gifu",
    "静岡県": "shizuoka", "愛知県": "aichi", "三重県": "mie", "滋賀県": "shiga",
    "京都府": "kyoto", "大阪府": "osaka", "兵庫県": "hyogo", "奈良県": "nara",
    "和歌山県": "wakayama", "鳥取県": "tottori", "島根県": "shimane", "岡山県": "okayama",
    "広島県": "hiroshima", "山口県": "yamaguchi", "徳島県": "tokushima", "香川県": "kagawa",
    "愛媛県": "ehime", "高知県": "kochi", "福岡県": "fukuoka", "佐賀県": "saga",
    "長崎県": "nagasaki", "熊本県": "kumamoto", "大分県": "oita", "宮崎県": "miyazaki",
    "鹿児島県": "kagoshima", "沖縄県": "okinawa",
}

# School name suffixes to strip when generating hostname-match tokens.
_NAME_SUFFIX_TOKENS: Final = (
    "専門学校", "高等専門学校", "短期大学", "大学院",
    "大学", "学院", "学園", "校",
)

_KANJI_TOKEN_ALIASES: Final = {
    "北海道": ("hokkaido",),
    "青森": ("aomori",), "岩手": ("iwate",), "宮城": ("miyagi",), "秋田": ("akita",),
    "山形": ("yamagata",), "福島": ("fukushima",), "茨城": ("ibaraki",), "栃木": ("tochigi",),
    "群馬": ("gunma",), "埼玉": ("saitama",), "千葉": ("chiba",), "東京": ("tokyo",),
    "神奈川": ("kanagawa",), "新潟": ("niigata",), "富山": ("toyama",), "石川": ("ishikawa",),
    "福井": ("fukui",), "山梨": ("yamanashi",), "長野": ("nagano",), "岐阜": ("gifu",),
    "静岡": ("shizuoka",), "愛知": ("aichi",), "三重": ("mie",), "滋賀": ("shiga",),
    "京都": ("kyoto",), "大阪": ("osaka",), "兵庫": ("hyogo",), "奈良": ("nara",),
    "和歌山": ("wakayama",), "鳥取": ("tottori",), "島根": ("shimane",), "岡山": ("okayama",),
    "広島": ("hiroshima",), "山口": ("yamaguchi",), "徳島": ("tokushima",), "香川": ("kagawa",),
    "愛媛": ("ehime",), "高知": ("kochi",), "福岡": ("fukuoka",), "佐賀": ("saga",),
    "長崎": ("nagasaki",), "熊本": ("kumamoto",), "大分": ("oita",), "宮崎": ("miyazaki",),
    "鹿児島": ("kagoshima",), "沖縄": ("okinawa",),
}

_KATAKANA_TOKEN_ALIASES: Final = {
    "デザイン": ("design",),
    "テック": ("tech",),
    "ビューティ": ("beauty",),
    "ビジネス": ("business",),
    "カレッジ": ("college",),
    "コンピュータ": ("computer",),
    "アニメ": ("anime",),
    "ゲーム": ("game",),
    "ホテル": ("hotel",),
    "トラベル": ("travel",),
    "メディカル": ("medical",),
    "リハビリ": ("rehab", "rehabilitation"),
    "ファッション": ("fashion",),
    "ミュージック": ("music",),
}


@dataclass(frozen=True)
class UrlScoreThresholds:
    auto: float = _DEFAULT_AUTO_THRESHOLD
    review: float = _DEFAULT_REVIEW_THRESHOLD

    def __post_init__(self) -> None:
        if not (0 <= self.review <= self.auto):
            raise ValueError(
                f"thresholds must satisfy 0 <= review <= auto, "
                f"got review={self.review} auto={self.auto}",
            )


@dataclass(frozen=True)
class UrlScore:
    candidate_url: str
    score: float
    decision: UrlScoreDecision
    breakdown: dict[str, float] = field(default_factory=dict)
    notes: tuple[str, ...] = field(default_factory=tuple)


def thresholds_from_env(env: dict[str, str] | None = None) -> UrlScoreThresholds:
    """Read EIDP_URL_SCORE_* overrides; fall back to defaults on parse error."""
    src = env if env is not None else os.environ
    auto = _float_or_default(src.get("EIDP_URL_SCORE_AUTO"), _DEFAULT_AUTO_THRESHOLD)
    review = _float_or_default(src.get("EIDP_URL_SCORE_REVIEW"), _DEFAULT_REVIEW_THRESHOLD)
    if review > auto:
        review = auto
    return UrlScoreThresholds(auto=auto, review=review)


def _float_or_default(raw: str | None, fallback: float) -> float:
    if raw is None or raw.strip() == "":
        return fallback
    try:
        return float(raw)
    except ValueError:
        return fallback


def _normalize(text: str | None) -> str:
    if not text:
        return ""
    return unicodedata.normalize("NFKC", text).strip()


_SCRIPT_BOUNDARY_RE = re.compile(
    # Split between distinct Japanese scripts and ASCII so
    # "東京デザイン" yields ["東京", "デザイン"] for hostname matching.
    r"(?<=[一-鿿])(?=[゠-ヿ぀-ゟA-Za-z0-9])"
    r"|(?<=[゠-ヿ])(?=[一-鿿぀-ゟA-Za-z0-9])"
    r"|(?<=[぀-ゟ])(?=[一-鿿゠-ヿA-Za-z0-9])"
    r"|(?<=[A-Za-z0-9])(?=[一-鿿゠-ヿ぀-ゟ])",
)


def _name_tokens(school_name: str) -> tuple[str, ...]:
    """Return distinctive tokens from a school name for hostname matching.

    Strips noise suffixes such as "専門学校" then splits on whitespace,
    common separators, and script boundaries so "東京デザイン専門学校"
    yields ("東京", "デザイン") rather than the full unsplit string which
    never appears in a hostname.
    """
    base = _normalize(school_name)
    for suffix in sorted(_NAME_SUFFIX_TOKENS, key=len, reverse=True):
        if base.endswith(suffix):
            base = base[: -len(suffix)]
            break
    if not base:
        return ()
    separator_split = re.split(r"[\s・　\-_]+", base)
    tokens: list[str] = []
    for part in separator_split:
        if not part:
            continue
        sub = _SCRIPT_BOUNDARY_RE.split(part)
        tokens.extend(s for s in sub if s)
    return tuple(t for t in tokens if len(t) >= 2)


def _romaji_tokens(school_name: str) -> tuple[str, ...]:
    """Lowercase ASCII tokens already inside the school name."""
    base = _normalize(school_name)
    parts = re.findall(r"[A-Za-z][A-Za-z0-9]+", base)
    return tuple(p.lower() for p in parts if len(p) >= 2)


def _hostname_match_tokens(school_name: str) -> tuple[str, ...]:
    tokens: list[str] = []
    # ASCII brand tokens already present in the school name are strong enough
    # on their own (e.g. "TDG", "ABK"). Japanese aliases are noisier: single
    # tokens such as "tokyo" or "design" match many unrelated sites, so use
    # them only as adjacent combinations from the school name.
    tokens.extend(_romaji_tokens(school_name))

    alias_groups = [_hostname_aliases_for_name_token(token) for token in _name_tokens(school_name)]
    for start in range(len(alias_groups)):
        parts: list[str] = []
        for group in alias_groups[start : start + 3]:
            if not group:
                break
            parts.append(group[0])
            if len(parts) >= 2:
                tokens.append("-".join(parts))
                tokens.append("".join(parts))

    deduped: list[str] = []
    seen: set[str] = set()
    for token in tokens:
        normalized = token.lower()
        if len(normalized) < 2 or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(normalized)
    return tuple(deduped)


def _hostname_aliases_for_name_token(token: str) -> tuple[str, ...]:
    ascii_tokens = tuple(t.lower() for t in re.findall(r"[A-Za-z][A-Za-z0-9]+", token) if len(t) >= 2)
    return (
        *ascii_tokens,
        *_KANJI_TOKEN_ALIASES.get(token, ()),
        *_KATAKANA_TOKEN_ALIASES.get(token, ()),
    )


def _host_suffix_match(host: str, suffix: str) -> bool:
    return host == suffix or host.endswith("." + suffix)


def _looks_publicly_operated_school(school_name: str) -> bool:
    normalized = _normalize(school_name)
    return any(marker in normalized for marker in _PUBLIC_SCHOOL_NAME_MARKERS)


def _is_stable_homepage_path(path: str) -> bool:
    if any(marker in path for marker, _penalty in _LOW_VALUE_PATH_PENALTIES):
        return False
    segments = [segment for segment in path.strip("/").split("/") if segment]
    if len(segments) > 1:
        return False
    return not any("." in segment for segment in segments)


def _looks_like_document_url(path: str, query: str) -> bool:
    return path.endswith(".pdf") or ".pdf" in query


def score_school_url_candidate(
    *,
    candidate_url: str,
    school_name: str,
    prefecture: str | None,
    page_title: str | None = None,
    page_excerpt: str | None = None,
    thresholds: UrlScoreThresholds | None = None,
) -> UrlScore:
    """Score a candidate URL and decide auto / review / reject.

    Never raises on bad input; returns a 0.0 reject score with notes
    describing why so callers can log without try/except.
    """
    th = thresholds or thresholds_from_env()
    breakdown: dict[str, float] = {}
    notes: list[str] = []

    parsed = urlparse(candidate_url)
    host = (parsed.hostname or "").lower()
    path = (parsed.path or "").lower()
    if not host or parsed.scheme not in {"http", "https"}:
        return UrlScore(
            candidate_url=candidate_url, score=0.0, decision="reject",
            breakdown={"invalid_url": 0.0}, notes=("invalid_url",),
        )
    if _looks_like_document_url(path, parsed.query.lower()):
        return UrlScore(
            candidate_url=candidate_url,
            score=-5.0,
            decision="reject",
            breakdown={"document_url": -5.0},
            notes=("document_url_not_school_site",),
        )

    # Hard penalties first — short circuit.
    if any(_host_suffix_match(host, s) for s in THIRD_PARTY_DIRECTORY_HOST_SUFFIXES):
        return UrlScore(
            candidate_url=candidate_url, score=-5.0, decision="reject",
            breakdown={"third_party_directory": -5.0},
            notes=("blacklisted_third_party_directory",),
        )
    if any(_host_suffix_match(host, s) for s in _SNS_HOST_SUFFIXES):
        return UrlScore(
            candidate_url=candidate_url, score=-5.0, decision="reject",
            breakdown={"sns_or_jobboard": -5.0},
            notes=("blacklisted_sns_or_jobboard",),
        )

    # Domain TLD bonus.
    tld_bonus = 0.0
    for tld in _ACADEMIC_TLDS:
        if host.endswith(tld):
            tld_bonus = 3.0
            break
    if tld_bonus == 0.0:
        for tld in _NEUTRAL_TLDS:
            if host.endswith(tld):
                tld_bonus = 1.0
                break
    if tld_bonus == 0.0:
        for tld in _NEGATIVE_TLDS:
            if host.endswith(tld):
                tld_bonus = -1.0
                break
    if tld_bonus != 0.0:
        breakdown["domain_tld"] = tld_bonus

    # School-name token in hostname.
    name_tokens = _name_tokens(school_name)
    host_match_tokens = _hostname_match_tokens(school_name)
    name_match = 0.0
    matched_tokens: list[str] = []
    for token in host_match_tokens:
        if token in host:
            name_match = 2.0
            matched_tokens.append(token)
            break
    if name_match:
        breakdown["domain_name_match"] = name_match
        notes.append("name_token=" + matched_tokens[0])

    # Prefecture token in domain or path.
    pref_bonus = 0.0
    if prefecture:
        pref_norm = _normalize(prefecture)
        pref_romaji = _PREFECTURE_ROMAJI.get(pref_norm)
        if pref_romaji and pref_romaji in host + path:
            pref_bonus = 1.0
        elif pref_norm and pref_norm in host + path:
            pref_bonus = 1.0
    if pref_bonus:
        breakdown["prefecture_in_url"] = pref_bonus

    # Page title match.
    title = _normalize(page_title)
    title_bonus = 0.0
    if title:
        normalized_school = _normalize(school_name)
        if normalized_school and normalized_school in title:
            title_bonus = 2.0
        else:
            for token in name_tokens:
                if token in title:
                    title_bonus = 1.0
                    break
    if title_bonus:
        breakdown["page_title_match"] = title_bonus

    # Disclosure keyword in page excerpt.
    excerpt = _normalize(page_excerpt)
    if excerpt and any(kw in excerpt for kw in _DISCLOSURE_KEYWORDS):
        breakdown["disclosure_keyword"] = 1.0

    # "公式" word.
    if excerpt and any(w.lower() in excerpt.lower() for w in _OFFICIAL_WORDS):
        breakdown["official_word"] = 0.5

    # News, event, and admissions/download pages are often official but are
    # poor stable SchoolSite anchors for target-year PDF discovery. Keep them
    # reviewable when other signals are strong; do not auto-register them.
    path_penalty = 0.0
    for marker, penalty in _LOW_VALUE_PATH_PENALTIES:
        if marker in path:
            path_penalty = min(path_penalty, penalty)
    if path_penalty:
        breakdown["low_value_path"] = path_penalty
        notes.append("low_value_path")

    # A clean official homepage or one-segment school root is a stable anchor
    # for later PDF discovery even when the homepage itself does not mention
    # the disclosure keywords.
    if tld_bonus >= 3.0 and title_bonus >= 1.0 and not path_penalty and _is_stable_homepage_path(path):
        breakdown["stable_homepage_path"] = 1.0

    score = sum(breakdown.values())

    if score >= th.auto:
        decision: UrlScoreDecision = "auto"
    elif score >= th.review:
        decision = "review"
    else:
        decision = "reject"

    if decision == "auto" and host.endswith(".lg.jp") and not _looks_publicly_operated_school(school_name):
        decision = "review"
        notes.append("local_government_requires_review")

    return UrlScore(
        candidate_url=candidate_url, score=score, decision=decision,
        breakdown=breakdown, notes=tuple(notes),
    )


def best_candidate(scores: list[UrlScore]) -> UrlScore | None:
    """Return the strongest actionable candidate.

    Prefer auto-safe candidates over review-only candidates. Review caps such
    as private-school ``.lg.jp`` hits can still carry high evidence scores,
    but they should not block a lower-scoring official school-domain URL from
    being registered automatically.
    """
    if not scores:
        return None
    auto = [s for s in scores if s.decision == "auto"]
    if auto:
        return max(auto, key=lambda s: s.score)
    review = [s for s in scores if s.decision == "review"]
    if review:
        return max(review, key=lambda s: s.score)
    return None
