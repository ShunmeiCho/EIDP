# Reference URL Analysis Report

Date: 2026-04-11
Purpose: Analyze PDF publishing patterns across 4 reference Japanese school websites for the EIDP automated crawler.

---

## Executive Summary

Four reference school websites were analyzed to understand how Japanese educational institutions publish enrollment/disclosure PDFs. The analysis reveals **four distinct architectural patterns** for PDF delivery, each requiring different crawling strategies. All sites served content via server-side HTML (no SPA frameworks), and none employed aggressive anti-scraping measures. However, two sites required multi-step fetching to reach the actual PDFs.

---

## Per-Site Findings

### 1. Toho Gakuen (tohogakuen.ac.jp)

**URL**: `https://www.tohogakuen.ac.jp/about/valuation/`
**Architecture**: Single-page disclosure hub with all PDFs linked directly

| Attribute | Value |
|-----------|-------|
| HTTP Status | 200 |
| HTML Size | 100,415 chars |
| Total PDF Links | 79 |
| Target-Keyword Matches | 32 |
| JS Rendering Required | No |
| robots.txt | Fully open (`Disallow:` empty) |
| Anti-scraping | None detected |

**PDF Link Pattern**:
- All PDFs served from a dedicated `/pdf/` path prefix
- URL pattern: `https://www.tohogakuen.ac.jp/pdf/about/valuation/{category}_{school}_{year}.pdf`
- Examples:
  - `/pdf/about/valuation/support/support_toho_2025.pdf` (support system application)
  - `/pdf/about/valuation/valuation_1_2024.pdf` (self-evaluation)
  - `/pdf/about/valuation/valuation_education_1_2024.pdf` (stakeholder evaluation)
  - `/pdf/about/valuation/financial_2024.pdf` (financial info)

**HTML Structure**:
- Uses accordion-style layout (CSS class patterns matching `accordion|collapse`)
- PDF links use `<a>` tags with absolute paths starting with `/pdf/`
- Anchor text format: `PDF{year}年度` or `PDF{department_name}`
- Headings (`<h3>`) group PDFs by category (e.g., "自己評価報告書", "学校関係者評価報告書")
- Multiple schools (Toho, Movie, Onkyo, Announce) share a single disclosure page

**Download Test**: All 5 tested PDFs returned HTTP 200 with `Content-Type: application/pdf`. Sizes range 311KB-463KB.

**Key Observation**: Toho uses a naming convention where the school identifier appears in the filename (`support_toho_`, `support_movie_`, etc.). The target application form (修学支援新制度確認申請書) is under heading "大学等における修学の支援に関する法律第3条第1項の確認に係る申請書" with URL path pattern `/pdf/about/valuation/support/support_{school}_{year}.pdf`.

---

### 2. JEC - Japan Electronics College (jec.ac.jp)

**URL**: `https://www.jec.ac.jp/school-outline/disclose/`
**Architecture**: WordPress site, minimal PDF count, direct links

| Attribute | Value |
|-----------|-------|
| HTTP Status | 200 |
| HTML Size | 73,055 chars |
| Total PDF Links | 3 |
| Target-Keyword Matches | 3 (all matched) |
| JS Rendering Required | No |
| robots.txt | Fully open (Yoast SEO plugin) |
| Anti-scraping | None detected |

**PDF Link Pattern**:
- WordPress theme asset path: `/wp-content/themes/jec/assets/pdf/{filename}.pdf`
- Target document: `R7_higher-education-support-system_v3.pdf`
- Anchor text: "高等教育の修学支援新制度（高等教育無償化）令和7年度申請書様式第2号および別紙"

**HTML Structure**:
- List layout with `<a>` tags
- Only 3 PDFs on the entire disclosure page
- Clean heading structure: single `<h2>` "情報公開"
- Most disclosure items are inline HTML text, not PDFs

**Download Test**:
- `guideline.pdf`: HTTP 200, downloadable
- `regulations.pdf`: HTTP 200, downloadable
- `R7_higher-education-support-system_v3.pdf`: **HTTP 404** -- the linked file does not exist at the expected path

**Key Observation**: The target PDF link exists in the HTML but returns 404. This is a common issue -- schools update filename versions (v3, v4) but the page HTML may reference a stale version. The crawler must handle 404 gracefully and possibly attempt version-number permutation.

---

### 3. TCA - Tokyo Communication Arts (tca.ac.jp)

**URL**: `https://www.tca.ac.jp/school/public_info/`
**Architecture**: Heavy content page with many PDF links and query-string cache busting

| Attribute | Value |
|-----------|-------|
| HTTP Status | 200 |
| HTML Size | 158,265 chars (full render) |
| Total PDF Links | 53 (via `a[href*=".pdf"]`) |
| Target-Keyword Matches | 2 (confirmation_application PDFs) |
| JS Rendering Required | No (jQuery only, content in raw HTML) |
| robots.txt | HTTP 404 (no robots.txt) |
| Anti-scraping | None detected |

**IMPORTANT DISCOVERY**: The initial automated fetch returned only 14,448 chars of HTML with 0 links/headings detected. A second fetch with identical headers returned the full 158,265 chars with all 53 PDF links. This suggests either:
- Cookie-based session initialization on first visit
- Server-side variability or CDN caching behavior
- The page may return a minimal shell on first request and require a follow-up

**Mitigation**: Implement retry logic -- if a page returns unexpectedly small HTML or zero PDF links, retry after a brief delay.

**PDF Link Pattern**:
- Relative paths rooted at `/school/public_info/data/`
- Year-segregated: `/school/public_info/data/{year}/{filename}.pdf`
- Evergreen (no year): `/school/public_info/data/{filename}.pdf`
- Cache-busting query strings: `?v=20250903`, `?202406`, `?20250903`
- Some relative paths without leading `/`: `data/2025/02_curriculum_supercreater_02_curriculum.pdf`

**Target Documents**:
- `/school/public_info/data/2025/11_confirmation_application.pdf?20250903` -- "大学等における修学の支援・高等教育修学支援制度"
- `/school/public_info/data/2025/11_confirmation_application_attachment.pdf` -- "大学等における修学の支援・高等教育修学支援制度（別紙）"

**HTML Structure**:
- Rich heading hierarchy: `<h1>` "情報公開", multiple `<h2>` section headings
- Sections: 学校の概要, 各学科等の教育, 教職員, キャリア教育, 学生納付金・修学支援, 学校評価, 国際交流
- PDFs nested under descriptive headings
- Accordion/collapsible sections via jQuery

**Download Test**: Both target PDFs returned HTTP 200 with `Content-Type: application/pdf`.

**Key Observation**: TCA's naming convention uses numbered prefixes (`01_`, `02_`, `07_`, `09_`, `11_`) that correspond to MEXT-mandated disclosure categories. The target document (confirmation_application) uses prefix `11_`. This numbering system appears across multiple schools in the Jikei Group.

---

### 4. NKZ - Nihon Kyoiku Zaidan / HAL Tokyo (nkz.ac.jp)

**URL**: `https://www.nkz.ac.jp/clginfo/thinfo.html`
**Architecture**: Multi-level navigation -- index page links to HTML subpages that embed PDFs

| Attribute | Value |
|-----------|-------|
| HTTP Status | 200 |
| HTML Size | 6,165 chars (index page) |
| PDF Links on Index | 0 |
| Subpage PDF Embeds | 1 per subpage (via `<embed>` tag) |
| JS Rendering Required | No (but PDFs embedded via `<embed>` not `<a>`) |
| robots.txt | HTTP 404 (no robots.txt) |
| Anti-scraping | `meta robots: noindex,nofollow` on subpages |
| nosnippet | Yes (subpages have `nosnippet` meta) |

**CRITICAL FINDING**: NKZ uses a two-tier architecture:

1. **Index page** (`thinfo.html`): Contains only `<a>` links to HTML subpages (e.g., `th/thZ-studyspt_13.html`)
2. **Subpages**: Each contains a single `<embed src="./pdf/{filename}.pdf">` tag

The index page has ZERO direct PDF links. The crawler must:
1. Parse the index page for subpage links
2. Fetch each subpage
3. Extract the PDF URL from `<embed src="...">` attributes
4. Construct absolute URL: `https://www.nkz.ac.jp/clginfo/th/pdf/thZ-studyspt_13.pdf`

**Target Document**:
- Index link text: "高等教育の修学支援新制度確認申請書"
- Index link URL: `https://www.nkz.ac.jp/clginfo/th/thZ-studyspt_13.html`
- Actual PDF URL: `https://www.nkz.ac.jp/clginfo/th/pdf/thZ-studyspt_13.pdf`
- Embed tag: `<embed src="./pdf/thZ-studyspt_13.pdf">`

**URL Pattern for subpages**:
- `th/J-evoluation_13.html` -> `th/pdf/thJ-evoluation_13.pdf` (事業報告書)
- `th/H-evoluation_13.html` -> `th/pdf/thH-evoluation_13.pdf` (自己評価報告書)
- `th/O-evoluation_13.html` -> `th/pdf/thO-evoluation_13.pdf` (学校関係者評価報告書)
- `th/thZ-studyspt_13.html` -> `th/pdf/thZ-studyspt_13.pdf` (修学支援確認申請書)
- `rgl/th-rglt.html` -> `rgl/pdf/th-rglt.pdf` (学則)

**Download Test**: PDF at `https://www.nkz.ac.jp/clginfo/th/pdf/thZ-studyspt_13.pdf` returned HTTP 200, `application/pdf`, 482KB.

**Key Observation**: NKZ subpages display "現在、表示できません。" (Currently cannot be displayed) as a fallback for browsers that don't support `<embed>`. The `_13` suffix in filenames appears to be a version/revision indicator. All subpages carry `noindex,nofollow` meta tags, indicating the school explicitly does not want these pages indexed by search engines.

---

## Common Patterns Across Sites

### PDF Delivery Architectures (4 types identified)

| Type | Description | Sites | Crawl Strategy |
|------|-------------|-------|----------------|
| **A - Direct Link** | PDFs linked via `<a href>` on disclosure page | Toho, JEC, TCA | Single-page parse, extract `a[href*=".pdf"]` |
| **B - Embedded PDF** | PDFs embedded via `<embed>` on subpages | NKZ | Two-step: index -> subpage -> extract embed src |
| **C - Query-string URLs** | PDF URLs contain cache-busting params | TCA | Strip query params for dedup, keep for fetching |
| **D - WordPress paths** | PDFs in theme/upload directories | JEC | Handle `/wp-content/` path patterns |

### Disclosure Page URL Patterns

Schools use consistent URL path patterns for their disclosure pages:

```
/about/valuation/           (Toho)
/school-outline/disclose/   (JEC)
/school/public_info/        (TCA)
/clginfo/thinfo.html        (NKZ)
```

Common path segments for disclosure pages:
- `info`, `information`, `joho`
- `public`, `koukai`, `disclose`
- `valuation`, `hyouka`, `evaluation`
- `clginfo`, `school-outline`

### Target Document Identification

The target document (高等教育の修学支援新制度 機関要件確認申請書) appears under various labels:

| Site | Anchor Text / Link Text |
|------|------------------------|
| Toho | (heading) "大学等における修学の支援に関する法律第3条第1項の確認に係る申請書" |
| JEC | "高等教育の修学支援新制度（高等教育無償化）令和7年度申請書様式第2号および別紙" |
| TCA | "大学等における修学の支援・高等教育修学支援制度" |
| NKZ | "高等教育の修学支援新制度確認申請書" |

### PDF Filename Patterns for Target Document

```
support_{school}_{year}.pdf                              (Toho)
R7_higher-education-support-system_v3.pdf                (JEC)
11_confirmation_application.pdf                          (TCA)
thZ-studyspt_13.pdf                                      (NKZ)
```

Common filename segments:
- `support`, `shien`, `studyspt`
- `confirmation`, `application`, `shinsei`
- `higher-education`, `koutoukyouiku`
- Year indicators: `2024`, `2025`, `R7` (Reiwa 7)

---

## Recommended CSS Selectors

### Primary Strategy (covers ~80% of sites)

```python
# Direct PDF links in <a> tags
SELECTORS_PRIMARY = [
    'a[href$=".pdf"]',          # Exact .pdf ending
    'a[href*=".pdf?"]',         # .pdf with query params
    'a[href*=".pdf#"]',         # .pdf with fragment
]

# Embedded PDFs (for NKZ-type sites)
SELECTORS_EMBED = [
    'embed[src*=".pdf"]',       # <embed> with PDF src
    'object[data*=".pdf"]',     # <object> with PDF data
    'iframe[src*=".pdf"]',      # <iframe> with PDF src
]
```

### Fallback Strategy (raw HTML regex)

For cases where BeautifulSoup misses PDFs (e.g., dynamically constructed URLs or unusual attributes):

```python
import re
PDF_REGEX = re.compile(r'["\']([^"\']*\.pdf[^"\']*)["\']', re.IGNORECASE)
```

### Multi-Level Navigation Detection

```python
# Links to subpages that may contain embedded PDFs
SUBPAGE_SELECTORS = [
    'a[href*="studyspt"]',
    'a[href*="support"]',
    'a[href*="shinsei"]',
]
```

---

## Recommended Keyword Weights

For scoring PDF relevance to the target document (修学支援新制度確認申請書):

### Tier 1 - High Confidence (weight: 10)
Keywords that strongly indicate the target document:
- `修学支援` (study support)
- `確認申請` (confirmation application)
- `機関要件` (institutional requirements)

### Tier 2 - Medium Confidence (weight: 5)
Keywords that appear in related context:
- `高等教育` (higher education)
- `新制度` (new system)
- `無償化` (free education)
- `申請書` (application form)
- `様式第2号` (form no. 2)

### Tier 3 - Low Confidence (weight: 2)
Keywords that indicate the right page section:
- `情報公開` (information disclosure)
- `学校情報` (school information)
- `教育情報` (education information)

### Tier 4 - Negative (weight: -3)
Keywords that indicate wrong document type:
- `シラバス` (syllabus)
- `カリキュラム` (curriculum)
- `学則` (school regulations)
- `事業報告` (business report)
- `自己評価` (self-evaluation) -- related but different document
- `財務` (financial)

### URL Path Keyword Scoring

```python
URL_KEYWORDS_POSITIVE = [
    ("support", 8),
    ("shien", 8),
    ("studyspt", 8),
    ("confirmation", 7),
    ("application", 5),
    ("shinsei", 5),
    ("higher-education", 5),
]

URL_KEYWORDS_NEGATIVE = [
    ("syllabus", -5),
    ("curriculum", -5),
    ("career", -3),
    ("profession", -3),
    ("diploma", -3),
]
```

---

## Anti-Scraping Observations

### Summary

| Measure | Toho | JEC | TCA | NKZ |
|---------|------|-----|-----|-----|
| robots.txt restrictive | No | No | N/A (404) | N/A (404) |
| Cloudflare/WAF | No | No | No | No |
| JavaScript required | No | No | No | No |
| CAPTCHA | No | No | No | No |
| Rate limiting observed | No | No | No | No |
| noindex/nofollow meta | No | No | No | **Yes** (subpages) |
| Session/cookie gating | No | No | **Possible** | No |
| HTTP 403 responses | No | No | No | No |

### Detailed Notes

1. **No aggressive anti-scraping**: None of the 4 sites employ Cloudflare, CAPTCHAs, or JavaScript-based bot detection. This is expected for public educational disclosure pages mandated by MEXT.

2. **TCA session behavior**: The first HTTP request to TCA's disclosure page may return a truncated response (~14KB vs ~158KB). This could be a cookie initialization, CDN warm-up, or PHP session behavior. Mitigation: implement retry with 1-2 second delay.

3. **NKZ noindex/nofollow**: Subpages carry `<meta name="robots" content="noindex,nofollow" />` and `<meta name="robots" content="nosnippet" />`. These are directives for search engine crawlers but do NOT block HTTP requests. The PDFs themselves have no access restrictions.

4. **Standard User-Agent sufficient**: All sites responded normally to a standard Chrome-like User-Agent. No need for specialized headers.

5. **No rate limiting detected**: All requests completed without 429 (Too Many Requests) responses. However, for the full 2400-school crawl, implement polite delays (1-2 seconds between requests to the same domain).

---

## Recommendations for Crawler Design

### 1. Multi-Strategy PDF Extraction

The crawler should implement a cascade of extraction methods:

```
1. Try a[href*=".pdf"] selectors first (handles Toho, JEC, TCA)
2. Try embed/object/iframe selectors (handles NKZ pattern)
3. Fallback to raw HTML regex for edge cases
4. If zero PDFs found, check for subpage links and follow them
```

### 2. Retry Logic for Inconsistent Responses

```
If HTML size < 20KB AND zero PDF links found:
  Wait 2 seconds
  Re-fetch with cookies from first request
  Re-parse
```

### 3. Target Document Scoring

For each PDF found, compute a relevance score:

```
score = sum(keyword_weight for keyword in matched_keywords)
       + sum(url_keyword_weight for url_keyword in matched_url_patterns)
       + (5 if under relevant heading)
       + (-10 if clearly wrong document type)
```

Select the PDF with the highest score. If score < threshold (e.g., 5), flag for manual review.

### 4. URL Normalization

- Strip query parameters for deduplication
- Resolve relative URLs against the page base URL
- Handle both `/path/file.pdf` and `path/file.pdf` (with and without leading slash)
- Normalize URL-encoded Japanese characters

### 5. Polite Crawling

- Respect `robots.txt` where present
- 1-2 second delay between requests to the same domain
- Standard browser User-Agent header
- Accept-Language: ja (Japanese content preference)

---

## Appendix: Raw Data

Analysis scripts and JSON results stored at:
- `scripts/analyze_reference_urls.py` -- main analysis script
- `scripts/analyze_zero_pdf_sites.py` -- deep analysis of TCA and NKZ
- `scripts/analyze_nkz_subpages.py` -- NKZ subpage navigation analysis
- `scripts/analyze_nkz_pdf_embed.py` -- NKZ embed pattern and TCA debug
- `scripts/reference_url_analysis_results.json` -- structured JSON results from main analysis
