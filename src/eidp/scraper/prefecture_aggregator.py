"""Prefecture-level aggregator parsers (Sprint 8.3.a).

Promoted from ``scripts/spike_pref_aggregator.py``. The spike was a
read-only investigation; this module is the production path consumed by
``eidp prefecture-aggregate`` and other ingest workflows.

What this module does
---------------------
For each Japanese prefecture's official aggregation artifact
(typically a PDF or XLSX listing 確認大学等 in that prefecture:
universities, prefectural vocational schools, and private vocational schools
in scope of the 高等教育の修学支援新制度), parse out:

  * school_name (raw + NFKC-normalized)
  * address / operator metadata
  * disclosure URL — including hidden URLs that live as PDF hyperlink
    annotations on the school name cell (Saitama / Miyagi style).
    pdfplumber's text-extraction silently misses those, so we use
    PyMuPDF's ``page.get_links()`` to recover them.
  * MEXT 学校番号 when the prefecture publishes one (Osaka).

Match each parsed school to the existing ``school`` row by:

  1. school_code (highest priority, gold standard for Osaka)
  2. exact name within prefecture
  3. NFKC-normalized name
  4. operator + substring overlap
  5. unique substring overlap within prefecture (Aichi index style)

Build a writer-plan describing per-school recommended actions
(``add`` / ``upgrade`` / ``noop`` / ``review``) so the apply step is
auditable.

Out of scope for 8.3.a
----------------------
* Writer-plan execution / DB writes — that lives behind the
  ``prefecture-aggregate --apply`` CLI in 8.3.c.
* Network fetching of prefecture artifacts — assumed downloaded.
"""

from __future__ import annotations

import json
import re
import unicodedata
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import pdfplumber
from sqlalchemy.orm import Session

# --- Domain types ---------------------------------------------------------


@dataclass
class PrefSchool:
    """One school as parsed out of a prefecture artifact."""

    pref: str
    school_name_raw: str
    school_name_norm: str
    address: str
    operator_kind: str
    operator_name: str
    operator_address: str
    disclosure_url: str | None
    school_code: str | None = None  # MEXT 学校番号 (Osaka has it)
    remarks: str = ""


@dataclass
class MatchResult:
    pref_school: PrefSchool
    db_school_id: int | None
    match_strategy: str  # school_code | exact | nfkc | operator_pref | substring_pref | none
    db_school_name: str | None
    has_existing_url: bool
    is_new_url_candidate: bool


@dataclass
class PrefReport:
    pref: str
    pdf_path: str
    extracted_total: int = 0
    extracted_with_url: int = 0
    db_matched: int = 0
    db_unmatched: int = 0
    match_by_strategy: dict[str, int] = field(default_factory=dict)
    existing_url_coverage: int = 0
    new_url_candidates: int = 0
    url_quality_distribution: dict[str, int] = field(default_factory=dict)
    action_distribution: dict[str, int] = field(default_factory=dict)
    quality_upgrade_candidates: int = 0
    sample_unmatched: list[dict[str, Any]] = field(default_factory=list)
    sample_new_urls: list[dict[str, Any]] = field(default_factory=list)
    records: list[dict[str, Any]] = field(default_factory=list)


# --- Helpers --------------------------------------------------------------


_URL_RE = re.compile(r"https?://[^\s　 ]+")

# Disclosure-keyword heuristics for URL quality classification.
_DISCLOSURE_KEYWORDS = (
    "disclos", "joho", "kyufu", "shien", "youken", "yoken",
    "info", "support", "schoolguide", "valuation",
    "kakunin", "shinsei", "musho",
)


def norm(s: str | None) -> str:
    """NFKC-normalized + whitespace-stripped string."""
    if not s:
        return ""
    s = unicodedata.normalize("NFKC", s)
    s = s.replace("​", "")
    s = re.sub(r"\s+", "", s)
    return s.strip()


def extract_url(cell: str | None) -> str | None:
    """Pull the first URL out of a free-text cell, or None."""
    if not cell:
        return None
    m = _URL_RE.search(cell)
    return m.group(0) if m else None


def _source_url_sidecar(artifact_path: Path) -> Path:
    return artifact_path.with_suffix(artifact_path.suffix + ".url")


def artifact_source_url(artifact_path: Path) -> str | None:
    """Return the original download URL recorded next to a cached artifact."""
    sidecar = _source_url_sidecar(artifact_path)
    if not sidecar.is_file():
        return None
    raw = sidecar.read_text(encoding="utf-8").strip()
    parsed = urlparse(raw)
    if parsed.scheme in {"http", "https"}:
        return raw
    return None


def _looks_like_school_name(text: str) -> bool:
    normalized = norm(text)
    if not normalized or normalized.isdigit() or len(normalized) < 4:
        return False
    category = normalized.strip("()（）")
    if re.fullmatch(
        r"(?:(?:国立|公立|県立|市立|私立))?"
        r"(?:大学|短期大学|専門学校|専修学校|高等専門学校|大学校)"
        r"(?:[(（]?(?:国立|公立|県立|市立|私立)[)）]?)?",
        category,
    ):
        return False
    if any(token in normalized for token in ("確認大学等", "学校名", "名称", "所在地", "設置者")):
        return False
    return any(token in normalized for token in ("大学", "短期大学", "専門学校", "高等専門学校", "大学校", "学院"))


def clean_school_name(text: str | None) -> str:
    """Normalize visible school-name text from official index artifacts."""
    if not text:
        return ""
    cleaned = unicodedata.normalize("NFKC", text)
    cleaned = cleaned.replace("＜外部リンク＞", "")
    cleaned = cleaned.replace("(外部サイトへリンク)", "")
    cleaned = cleaned.replace("（外部サイトへリンク）", "")
    cleaned = re.sub(r"\s+", "", cleaned)
    return cleaned.strip()


def clean_cell(cell: str | None) -> str:
    if not cell:
        return ""
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", cell).replace("​", "")).strip()


def is_header(row: Sequence[str | None]) -> bool:
    """Detect repeated header / pref note rows we want to skip."""
    joined = "".join(str(c) for c in row if c)
    return any(k in joined for k in ("確認大学等", "学 校 名", "学校名"))


def classify_url_quality(url: str | None) -> str:
    """Categorise a disclosure URL into direct_pdf / disclosure / homepage / none."""
    if not url:
        return "none"
    lo = url.lower()
    if lo.endswith(".pdf"):
        return "direct_pdf"
    if any(k in lo for k in _DISCLOSURE_KEYWORDS):
        return "disclosure"
    return "homepage"


def classify_prefecture_remarks(remarks: str | None) -> list[str]:
    """Classify useful 備考 signals from official prefecture index artifacts."""
    text = norm(remarks)
    if not text:
        return []

    tags: list[str] = []
    if ("新規" in text and not any(token in text for token in ("取消", "辞退", "対象外"))) or "開校" in text:
        tags.append("new_accreditation")
    if any(token in text for token in ("名称変更", "校名変更", "改称", "旧称", "旧校名")):
        tags.append("name_change")
    if any(token in text for token in ("取消", "辞退", "廃止", "対象外", "満たさなく")):
        tags.append("withdrawal")
    if any(token in text for token in ("統合", "再編", "合併")):
        tags.append("merger_reorg")
    return tags


_QUALITY_RANK = {"direct_pdf": 3, "disclosure": 2, "homepage": 1, "none": 0}


def recommend_action(pref_quality: str, existing_qualities: list[str]) -> str:
    """Decide writer-plan action per matched school.

    Returns one of:
      * ``add``     — matched + PDF URL present + no existing URL
      * ``upgrade`` — matched + PDF URL strictly better quality than existing
      * ``noop``    — matched + PDF URL same/worse than existing, or no URL
    Caller handles ``review`` for unmatched schools.
    """
    if pref_quality == "none":
        return "noop"
    best_existing = max(
        (_QUALITY_RANK.get(q, 0) for q in existing_qualities), default=0,
    )
    if best_existing == 0:
        return "add"
    if _QUALITY_RANK[pref_quality] > best_existing:
        return "upgrade"
    return "noop"


# --- Hyperlink annotation extraction (Saitama-style) ----------------------


def extract_pdf_annotation_links(pdf_path: Path) -> dict[str, str]:
    """Extract hyperlink annotations keyed by anchor text (school name).

    Some prefecture PDFs (Saitama, partial Aichi) embed disclosure URLs as
    clickable hyperlink annotations on the school name cell rather than as
    plain text in the 備考 column. pdfplumber's text extraction does not
    surface those annotations; PyMuPDF's ``page.get_links()`` does.

    This is THE owner-mandated path for Saitama in Sprint 8.3 — without
    it, the 36 schools whose URLs are annotation-only would be silently
    dropped on every run.
    """
    import fitz  # type: ignore[import-untyped]  # pymupdf

    out: dict[str, str] = {}
    doc = fitz.open(pdf_path)
    try:
        for page in doc:
            for link in page.get_links():
                uri = link.get("uri") or ""
                rect = link.get("from")
                if not uri or not rect:
                    continue
                anchor_text = page.get_text("text", clip=rect).strip()
                if not anchor_text:
                    continue
                key = norm(anchor_text)
                if key and key not in out:
                    out[key] = uri
    finally:
        doc.close()
    return out


# --- Per-prefecture parsers -----------------------------------------------


def parse_tokyo(pdf_path: Path) -> list[PrefSchool]:
    """Tokyo: 8-column tables. URL = col[7]."""
    out: list[PrefSchool] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables():
                for row in table:
                    if not row or len(row) < 8 or is_header(row):
                        continue
                    school_name = clean_school_name(row[2])
                    if not _looks_like_school_name(school_name):
                        continue
                    out.append(PrefSchool(
                        pref="tokyo",
                        school_name_raw=school_name,
                        school_name_norm=norm(school_name),
                        address=(row[3] or "").strip(),
                        operator_kind=(row[4] or "").strip(),
                        operator_name=(row[5] or "").strip(),
                        operator_address=(row[6] or "").strip(),
                        disclosure_url=extract_url(row[7]),
                        remarks=(row[7] or "").strip(),
                    ))
    return out


def parse_5col(pdf_path: Path, pref: str) -> list[PrefSchool]:
    """Kanagawa / Saitama / Miyagi style: 5-column tables.

    URL priority:
      1. plain-text URL in 備考 column (col 4)
      2. PDF hyperlink annotation on the school-name cell — recovers
         ~36 Saitama schools that pdfplumber alone cannot see.
    """
    annotation_links = extract_pdf_annotation_links(pdf_path)

    out: list[PrefSchool] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables():
                for row in table:
                    if not row or len(row) < 5 or is_header(row):
                        continue
                    school_name = clean_school_name(row[0])
                    if not _looks_like_school_name(school_name):
                        continue

                    url = extract_url(row[4])
                    if not url:
                        url = annotation_links.get(norm(school_name))

                    out.append(PrefSchool(
                        pref=pref,
                        school_name_raw=school_name,
                        school_name_norm=norm(school_name),
                        address=(row[1] or "").strip(),
                        operator_kind="",
                        operator_name=(row[2] or "").strip(),
                        operator_address=(row[3] or "").strip(),
                        disclosure_url=url,
                        remarks=(row[4] or "").strip(),
                    ))
    return out


def parse_6col_indexed(pdf_path: Path, pref: str) -> list[PrefSchool]:
    """Chiba-style PDF: 6-column table with a leading row number column.

    Layout:
      [No, school_name, address, operator_name, operator_address, remarks]

    Some prefectures publish useful school-universe and 備考 signals in this
    format even when no disclosure URL is printed in the table.
    """
    annotation_links = extract_pdf_annotation_links(pdf_path)

    out: list[PrefSchool] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables():
                for row in table:
                    if not row or len(row) < 6 or is_header(row):
                        continue
                    school_name = clean_school_name(row[1])
                    if not _looks_like_school_name(school_name):
                        continue

                    remarks = (row[5] or "").strip()
                    url = extract_url(remarks)
                    if not url:
                        url = annotation_links.get(norm(school_name))

                    out.append(PrefSchool(
                        pref=pref,
                        school_name_raw=school_name,
                        school_name_norm=norm(school_name),
                        address=(row[2] or "").strip(),
                        operator_kind="",
                        operator_name=(row[3] or "").strip(),
                        operator_address=(row[4] or "").strip(),
                        disclosure_url=url,
                        remarks=remarks,
                    ))
    return out


def parse_7col_hokkaido(pdf_path: Path, pref: str = "hokkaido") -> list[PrefSchool]:
    """Hokkaido style: 7-col table, URL in col[5] (ホームページURL column)."""
    out: list[PrefSchool] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables():
                for row in table:
                    if not row or len(row) < 7 or is_header(row):
                        continue
                    school_name = clean_school_name(row[0])
                    if not _looks_like_school_name(school_name) or "確認大学" in school_name:
                        continue
                    out.append(PrefSchool(
                        pref=pref,
                        school_name_raw=school_name,
                        school_name_norm=norm(school_name),
                        address=(row[1] or "").strip(),
                        operator_kind="",
                        operator_name=(row[2] or "").strip(),
                        operator_address=(row[3] or "").strip(),
                        disclosure_url=extract_url(row[5]),
                        remarks=(row[6] or "").strip(),
                    ))
    return out


@dataclass
class _HtmlLink:
    text: str
    href: str


@dataclass
class _HtmlCell:
    text: str
    links: list[_HtmlLink] = field(default_factory=list)


class _TableLinkExtractor(HTMLParser):
    """Extract HTML tables plus anchor text/hrefs from prefecture index pages."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tables: list[list[list[_HtmlCell]]] = []
        self.all_links: list[_HtmlLink] = []
        self._table: list[list[_HtmlCell]] | None = None
        self._row: list[_HtmlCell] | None = None
        self._cell_text: list[str] | None = None
        self._cell_links: list[_HtmlLink] | None = None
        self._anchor_href: str | None = None
        self._anchor_text: list[str] | None = None
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in {"script", "style"}:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        if tag == "table":
            self._table = []
        elif tag == "tr" and self._table is not None:
            self._row = []
        elif tag in {"td", "th"} and self._row is not None:
            self._cell_text = []
            self._cell_links = []
        elif tag == "a":
            href = dict(attrs).get("href")
            if href:
                self._anchor_href = href
                self._anchor_text = []

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        if self._cell_text is not None:
            self._cell_text.append(data)
        if self._anchor_text is not None:
            self._anchor_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"script", "style"} and self._skip_depth:
            self._skip_depth -= 1
            return
        if self._skip_depth:
            return
        if tag == "a" and self._anchor_href is not None:
            text = _clean_html_text("".join(self._anchor_text or []))
            link = _HtmlLink(text=text, href=self._anchor_href)
            self.all_links.append(link)
            if self._cell_links is not None:
                self._cell_links.append(link)
            self._anchor_href = None
            self._anchor_text = None
        elif tag in {"td", "th"} and self._row is not None and self._cell_text is not None:
            self._row.append(_HtmlCell(
                text=_clean_html_text("".join(self._cell_text)),
                links=list(self._cell_links or []),
            ))
            self._cell_text = None
            self._cell_links = None
        elif tag == "tr" and self._table is not None and self._row is not None:
            if any(cell.text or cell.links for cell in self._row):
                self._table.append(self._row)
            self._row = None
        elif tag == "table" and self._table is not None:
            if self._table:
                self.tables.append(self._table)
            self._table = None


def _clean_html_text(value: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", value)).strip()


def _absolute_http_url(href: str, base_url: str | None) -> str | None:
    href = href.strip()
    if not href or href.startswith("#"):
        return None
    parsed = urlparse(href)
    if parsed.scheme and parsed.scheme not in {"http", "https"}:
        return None
    candidate = urljoin(base_url, href) if base_url else href
    parsed_candidate = urlparse(candidate)
    if parsed_candidate.scheme in {"http", "https"} and parsed_candidate.netloc:
        return candidate
    return None


def _cell_url(cell: _HtmlCell, base_url: str | None) -> str | None:
    for link in cell.links:
        url = _absolute_http_url(link.href, base_url)
        if url:
            return url
    return extract_url(cell.text)


def _row_remarks(headers: list[str], cells: list[_HtmlCell]) -> str:
    texts = [cell.text for cell in cells]
    if headers and len(headers) == len(texts):
        for idx, header in enumerate(headers):
            if "備考" in norm(header):
                return texts[idx]
    tagged = [text for text in texts if classify_prefecture_remarks(text)]
    return " / ".join(tagged)


def parse_html_table(html_path: Path, pref: str, *, base_url: str | None = None) -> list[PrefSchool]:
    """Generic official-index HTML parser.

    Some prefectures publish the 確認大学等 index directly as an HTML table/list
    where the school name itself is a hyperlink. This parser turns those rows
    into the same PrefSchool shape as the PDF table parsers.
    """
    source_url = base_url or artifact_source_url(html_path)
    html = html_path.read_text(encoding="utf-8", errors="replace")
    extractor = _TableLinkExtractor()
    extractor.feed(html)

    out: list[PrefSchool] = []
    seen: set[tuple[str, str | None]] = set()

    for table in extractor.tables:
        headers: list[str] = []
        for cells in table:
            texts = [cell.text for cell in cells]
            if is_header(texts):
                headers = texts
                continue

            school_idx: int | None = None
            school_name = ""
            for idx, cell in enumerate(cells):
                link_name = next(
                    (clean_school_name(link.text) for link in cell.links if _looks_like_school_name(link.text)),
                    "",
                )
                if link_name:
                    school_idx = idx
                    school_name = link_name
                    break
                if _looks_like_school_name(cell.text):
                    school_idx = idx
                    school_name = clean_school_name(cell.text)
                    break
            if school_idx is None:
                continue

            row_url = _cell_url(cells[school_idx], source_url)
            if not row_url:
                row_url = next((_cell_url(cell, source_url) for cell in cells if _cell_url(cell, source_url)), None)

            key = (norm(school_name), row_url)
            if key in seen:
                continue
            seen.add(key)

            out.append(PrefSchool(
                pref=pref,
                school_name_raw=school_name,
                school_name_norm=norm(school_name),
                address=texts[school_idx + 1] if len(texts) > school_idx + 1 else "",
                operator_kind="",
                operator_name=texts[school_idx + 2] if len(texts) > school_idx + 2 else "",
                operator_address=texts[school_idx + 3] if len(texts) > school_idx + 3 else "",
                disclosure_url=row_url,
                remarks=_row_remarks(headers, cells),
            ))

    for link in extractor.all_links:
        if not _looks_like_school_name(link.text):
            continue
        url = _absolute_http_url(link.href, source_url)
        school_name = clean_school_name(link.text)
        key = (norm(school_name), url)
        if key in seen:
            continue
        seen.add(key)
        out.append(PrefSchool(
            pref=pref,
            school_name_raw=school_name,
            school_name_norm=norm(school_name),
            address="",
            operator_kind="",
            operator_name="",
            operator_address="",
            disclosure_url=url,
        ))

    return out


# --- Parser registry ------------------------------------------------------

# Public registry of supported prefectures and their parser callables. A
# CLI / pipeline layer can iterate this dict; each value is
# (parser_callable, expected_pref_key).
PARSERS: dict[str, Callable[[Path], list[PrefSchool]]] = {
    "tokyo": parse_tokyo,
    "kanagawa": lambda p: parse_5col(p, "kanagawa"),
    "saitama": lambda p: parse_5col(p, "saitama"),
    "miyagi": lambda p: parse_5col(p, "miyagi"),
    "fukuoka": lambda p: parse_5col(p, "fukuoka"),
    "hyogo": lambda p: parse_5col(p, "hyogo"),
    "shizuoka": lambda p: parse_5col(p, "shizuoka"),
    "okinawa": lambda p: parse_5col(p, "okinawa"),
    "hokkaido": parse_7col_hokkaido,
    "akita": lambda p: parse_5col(p, "akita"),
    "aomori": lambda p: parse_html_table(p, "aomori"),
    "chiba": lambda p: parse_6col_indexed(p, "chiba"),
    "fukui": lambda p: parse_5col(p, "fukui"),
    "gunma": lambda p: parse_html_table(p, "gunma"),
    "ibaraki": lambda p: parse_5col(p, "ibaraki"),
    "tochigi": lambda p: parse_html_table(p, "tochigi"),
    "kagoshima": lambda p: parse_html_table(p, "kagoshima"),
    "miyazaki": lambda p: parse_html_table(p, "miyazaki"),
    "nagano": lambda p: parse_html_table(p, "nagano"),
    "wakayama": lambda p: parse_html_table(p, "wakayama"),
    "tottori": lambda p: parse_html_table(p, "tottori"),
    "yamaguchi": lambda p: parse_html_table(p, "yamaguchi"),
    "oita": lambda p: parse_html_table(p, "oita"),
}


# Mapping pref-key (URL-safe) -> Japanese prefecture name as stored on
# School.prefecture.
PREF_KEY_TO_DB = {
    "tokyo": "東京都",
    "kanagawa": "神奈川県",
    "saitama": "埼玉県",
    "osaka": "大阪府",
    "fukuoka": "福岡県",
    "hyogo": "兵庫県",
    "shizuoka": "静岡県",
    "okinawa": "沖縄県",
    "miyagi": "宮城県",
    "hokkaido": "北海道",
    "niigata": "新潟県",
    "aichi": "愛知県",
    "akita": "秋田県",
    "aomori": "青森県",
    "chiba": "千葉県",
    "fukui": "福井県",
    "gunma": "群馬県",
    "ibaraki": "茨城県",
    "tochigi": "栃木県",
    "kagoshima": "鹿児島県",
    "miyazaki": "宮崎県",
    "nagano": "長野県",
    "wakayama": "和歌山県",
    "tottori": "鳥取県",
    "yamaguchi": "山口県",
    "oita": "大分県",
}


def parse(pref: str, artifact_path: Path) -> list[PrefSchool]:
    """Public entry point — dispatch on ``pref`` to the right parser."""
    parser = PARSERS.get(pref)
    if parser is None:
        raise ValueError(
            f"No parser registered for prefecture {pref!r}. "
            f"Available: {sorted(PARSERS)}"
        )
    return parser(artifact_path)


# --- Matching (DB lookup) -------------------------------------------------


def build_indices(session: Session, pref: str) -> tuple[dict[str, Any], dict[int, list[str]]]:
    """Pre-build (school_index, site_index) for a single prefecture.

    Done once per pref so per-school ``match_school`` is O(1) lookup
    instead of O(N) DB hits — the spike's perf work, preserved.
    """
    from eidp.db.models import School, SchoolSite

    db_pref = PREF_KEY_TO_DB.get(pref, pref)
    schools = (
        session.query(School)
        .filter(School.prefecture == db_pref, School.status == "active")
        .all()
    )
    school_index: dict[str, Any] = {"_all": schools}
    for s in schools:
        school_index[f"name:{s.school_name}"] = s
        school_index[f"nfkc:{norm(s.school_name)}"] = s
        if s.school_code:
            school_index[f"code:{s.school_code}"] = s

    school_ids = [s.id for s in schools]
    sites = (
        session.query(SchoolSite)
        .filter(SchoolSite.school_id.in_(school_ids))
        .all() if school_ids else []
    )
    site_index: dict[int, list[str]] = {}
    for site in sites:
        site_index.setdefault(site.school_id, []).append(site.url)
    return school_index, site_index


def match_school(
    pref_school: PrefSchool,
    school_index: dict[str, Any],
    site_index: dict[int, list[str]],
) -> MatchResult:
    """Cascading match: school_code → exact → nfkc → operator+substring →
    substring(unique). Returns the strongest hit or ``strategy='none'``."""
    match = None
    strategy = "none"

    if pref_school.school_code:
        by_code = school_index.get(f"code:{pref_school.school_code}")
        if by_code is not None:
            match, strategy = by_code, "school_code"

    if match is None:
        exact = school_index.get(f"name:{pref_school.school_name_raw}")
        if exact is not None:
            match, strategy = exact, "exact"

    if match is None:
        nfkc = school_index.get(f"nfkc:{pref_school.school_name_norm}")
        if nfkc is not None:
            match, strategy = nfkc, "nfkc"

    if match is None and pref_school.operator_name:
        op_norm = norm(pref_school.operator_name)
        cand = [
            s for s in school_index["_all"]
            if norm(s.corporation_name) == op_norm
            and (norm(s.school_name) in pref_school.school_name_norm
                 or pref_school.school_name_norm in norm(s.school_name))
        ]
        if len(cand) == 1:
            match, strategy = cand[0], "operator_pref"

    if match is None:
        cand = [
            s for s in school_index["_all"]
            if len(norm(s.school_name)) >= 6
            and (norm(s.school_name) in pref_school.school_name_norm
                 or pref_school.school_name_norm in norm(s.school_name))
        ]
        if len(cand) == 1:
            match, strategy = cand[0], "substring_pref"

    existing_urls = site_index.get(match.id, []) if match else []
    has_url = bool(existing_urls)
    is_new = bool(pref_school.disclosure_url and match and not has_url)

    return MatchResult(
        pref_school=pref_school,
        db_school_id=match.id if match else None,
        match_strategy=strategy,
        db_school_name=match.school_name if match else None,
        has_existing_url=has_url,
        is_new_url_candidate=is_new,
    )


# --- Writer-plan ----------------------------------------------------------


def build_report(
    pref: str,
    artifact_path: Path,
    results: list[MatchResult],
    site_index: dict[int, list[str]],
) -> PrefReport:
    """Assemble a PrefReport with per-school records + aggregate stats.

    The ``records`` list is the writer-plan: one entry per parsed school
    with ``recommended_action`` set to add / upgrade / noop / review.
    Apply step (Sprint 8.3.c) consumes this without re-running parsing.
    """
    rep = PrefReport(pref=pref, pdf_path=str(artifact_path))
    by_strat: dict[str, int] = {}
    quality_dist: dict[str, int] = {}
    action_dist: dict[str, int] = {}

    for r in results:
        rep.extracted_total += 1
        if r.pref_school.disclosure_url:
            rep.extracted_with_url += 1
        if r.db_school_id is not None:
            rep.db_matched += 1
        else:
            rep.db_unmatched += 1
        by_strat[r.match_strategy] = by_strat.get(r.match_strategy, 0) + 1

        url_quality = classify_url_quality(r.pref_school.disclosure_url)
        quality_dist[url_quality] = quality_dist.get(url_quality, 0) + 1
        remark_tags = classify_prefecture_remarks(r.pref_school.remarks)

        existing_urls = site_index.get(r.db_school_id, []) if r.db_school_id else []
        if existing_urls:
            rep.existing_url_coverage += 1
        existing_qualities = [classify_url_quality(u) for u in existing_urls]

        if r.match_strategy == "none":
            action = "review"
        else:
            action = recommend_action(url_quality, existing_qualities)
        action_dist[action] = action_dist.get(action, 0) + 1
        if action == "upgrade":
            rep.quality_upgrade_candidates += 1

        if r.is_new_url_candidate:
            rep.new_url_candidates += 1
            if len(rep.sample_new_urls) < 5:
                rep.sample_new_urls.append({
                    "school": r.db_school_name,
                    "url": r.pref_school.disclosure_url,
                })
        if r.match_strategy == "none" and len(rep.sample_unmatched) < 5:
            rep.sample_unmatched.append({
                "pdf_name": r.pref_school.school_name_raw,
                "operator": r.pref_school.operator_name,
            })

        rep.records.append({
            "db_school_id": r.db_school_id,
            "db_school_name": r.db_school_name,
            "pdf_school_name": r.pref_school.school_name_raw,
            "pdf_school_code": r.pref_school.school_code,
            "pdf_address": r.pref_school.address,
            "pdf_operator": r.pref_school.operator_name,
            "pref_url": r.pref_school.disclosure_url,
            "pref_remarks": r.pref_school.remarks,
            "pref_remark_tags": remark_tags,
            "pref_has_school_change_signal": bool(remark_tags),
            "url_quality": url_quality,
            "match_strategy": r.match_strategy,
            "existing_urls": existing_urls,
            "existing_url_quality": existing_qualities,
            "is_new_url_candidate": r.is_new_url_candidate,
            "quality_upgrade_candidate": (action == "upgrade"),
            "recommended_action": action,
        })

    rep.match_by_strategy = by_strat
    rep.url_quality_distribution = quality_dist
    rep.action_distribution = action_dist
    return rep


def aggregate(
    session: Session,
    pref: str,
    artifact_path: Path,
) -> PrefReport:
    """Top-level entry: parse + match + report. No DB writes — apply in
    Sprint 8.3.c."""
    parsed = parse(pref, artifact_path)
    school_index, site_index = build_indices(session, pref)
    results = [match_school(p, school_index, site_index) for p in parsed]
    return build_report(pref, artifact_path, results, site_index)


def apply_writer_plan(session: Session, report: PrefReport) -> dict[str, int]:
    """Apply ``add`` / ``upgrade`` recommendations from a PrefReport.

    Sprint 8.3 contract: ``add`` inserts a new SchoolSite with
    ``discovery_method='prefecture_aggregator'`` and ``confidence=0.95``.
    ``upgrade`` updates the existing site to point at the better URL
    (preserves historical urls via SchoolSite append? — no, current
    SchoolSite has no revision contract; we just overwrite the URL of
    the lowest-quality existing site, since prefecture data is the
    authoritative source for disclosure URL).

    Caller is responsible for ``session.commit()`` so we sit inside a
    larger transaction if needed.
    """
    from eidp.db.models import ReviewItem, SchoolSite

    stats = {"added": 0, "upgraded": 0, "skipped": 0}
    for record in report.records:
        action = record["recommended_action"]
        school_id = record["db_school_id"]
        new_url = record["pref_url"]
        remark_tags = record.get("pref_remark_tags") or []
        remarks = record.get("pref_remarks") or ""

        if school_id and remark_tags:
            existing_item = (
                session.query(ReviewItem)
                .filter(
                    ReviewItem.item_type == "prefecture_remark",
                    ReviewItem.reference_table == "school",
                    ReviewItem.reference_id == school_id,
                    ReviewItem.status == "pending",
                    ReviewItem.evidence_url == new_url,
                )
                .first()
            )
            if existing_item is None:
                session.add(ReviewItem(
                    item_type="prefecture_remark",
                    reference_id=school_id,
                    reference_table="school",
                    status="pending",
                    priority=2,
                    proposal_value=json.dumps(
                        {"tags": remark_tags, "remarks": remarks},
                        ensure_ascii=False,
                    ),
                    proposal_reason="都道府県の確認大学等一覧の備考欄に注意信号があります。",
                    proposal_source="prefecture_aggregator",
                    evidence_url=new_url,
                ))
                stats["review_items"] = stats.get("review_items", 0) + 1

        if action == "noop" or action == "review" or not school_id or not new_url:
            stats["skipped"] += 1
            continue

        if action == "add":
            session.add(SchoolSite(
                school_id=school_id,
                url=new_url,
                url_type="disclosure",
                discovery_method="prefecture_aggregator",
                confidence=0.95,
            ))
            stats["added"] += 1
        elif action == "upgrade":
            # Find the lowest-quality existing site for this school and
            # repoint it; alternative would be marking it inactive but
            # SchoolSite has no soft-delete column today.
            existing_sites = (
                session.query(SchoolSite)
                .filter(SchoolSite.school_id == school_id)
                .all()
            )
            if existing_sites:
                worst = min(
                    existing_sites,
                    key=lambda s: _QUALITY_RANK.get(classify_url_quality(s.url), 0),
                )
                worst.url = new_url
                worst.discovery_method = "prefecture_aggregator"
                worst.confidence = 0.95
                worst.url_type = "disclosure"
            stats["upgraded"] += 1
    return stats
