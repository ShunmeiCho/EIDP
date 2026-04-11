# URL Discovery Test Report - 50 Schools

**Date**: 2026-04-11
**Dataset**: sample/2025専門学校無償化情報公開まとめ.xlsx (sheet: 採録状況)
**Total schools in dataset**: 2,212 across 47 prefectures
**Test batch size**: 50

---

## 1. Sampling Methodology

### Stratified sampling approach:
- 1 school per prefecture (47 schools) -- all 47 prefectures represented
- 3 additional schools from Tokyo (largest concentration: 278 schools)
- Preference given to schools with 2025年度 status = 〇 (successfully collected before)

### Result:
- All 50 selected schools had 2025年度 status = 〇
- Coverage: 47/47 prefectures (100%)
- Diverse school types: nursing, IT, beauty, business, culinary, agriculture, music, aviation, childcare, rehabilitation, design
- Mix of operators: national chains (大原学園 = 14 schools), regional groups, public/prefectural, small independent schools

---

## 2. Search Results Summary

### Overall Metrics

| Metric | Count | Percentage |
|--------|-------|------------|
| High confidence (>= 0.90) | 43 | 86% |
| Medium confidence (0.85 - 0.89) | 7 | 14% |
| Low confidence (< 0.85) | 0 | 0% |
| Failed completely | 0 | 0% |
| HTTP 200 confirmed | 50 | 100% |

### Confidence Distribution Detail

| Confidence Score | Count | Schools |
|-----------------|-------|---------|
| 0.95 | 35 | Most schools with dedicated domains or clear Ohara subpages |
| 0.90 | 8 | Schools with name changes, generic names, or corp sites |
| 0.85 | 7 | Government-hosted pages, group sites, or rebranded schools |

---

## 3. URL Type Classification

| URL Type | Count | Examples |
|----------|-------|---------|
| Dedicated school domain | 25 (50%) | ise-riyoubiyou.jp, siw.ac.jp, kose-ac.jp |
| Corporation subpage | 19 (38%) | o-hara.ac.jp/senmon/school/kyoto/, esp.ac.jp/tokyo/ |
| Government page | 3 (6%) | pref.yamaguchi.lg.jp, pref.kochi.lg.jp, pref.akita.lg.jp |
| Corporation top page | 3 (6%) | akatuka.ac.jp, mito.ac.jp, ksb.ac.jp |

### Key Observations by URL Type:

**Dedicated school domains (50%)** -- Highest confidence. These are standalone websites for a single school. Common patterns: `{school-abbreviation}.ac.jp` or `{school-name}.ac.jp`. Always the best match.

**Corporation subpages (38%)** -- High confidence. Large school groups (particularly 大原学園 with 14 schools) host all campuses under one domain with `/school/{campus}/` paths. These are still official pages with full school information.

**Government pages (6%)** -- Medium confidence. Public/prefectural schools (秋田県立衛生看護学院, 山口県立萩看護学校, 高知県立幡多看護専門学校) often have no dedicated domain and are hosted as subpages on prefectural government websites.

**Corporation top pages (6%)** -- Medium confidence. Some schools (赤塚学園, 八文字学園) only have a group-level site that covers multiple schools or departments.

---

## 4. Search Pattern Effectiveness

| Query Pattern | Times Used as Primary | Success Rate |
|---------------|----------------------|-------------|
| School name only | 30 | 100% |
| School name + prefecture | 12 | 100% |
| School name + corporation | 8 | 100% |

### Analysis:

- **School name only** was sufficient in 60% of cases. When a school has a unique name (e.g., 伊勢理容美容専門学校, KCS大分情報専門学校), the first search result was almost always the official site.
- **School name + prefecture** was needed for schools with generic names (e.g., 大原簿記公務員専門学校 exists in many prefectures) or when the school name alone returned too many portal/directory results.
- **School name + corporation** was useful for schools within large groups (e.g., distinguishing 大原 schools, 穴吹 schools) where the group name helped disambiguate.

### First-result accuracy:
In 48 out of 50 cases (96%), the top web search result was either the official school page or the official school page on a group/government site. The remaining 2 cases had the official site as the 2nd result (with a portal directory as 1st).

---

## 5. 情報公開 (Information Disclosure) Page Detection

Spot-checked 5 school sites for 情報公開 links on the top page:

| School | 情報公開 Found | URL/Location |
|--------|---------------|-------------|
| さいたまIT・WEB専門学校 | Yes | /information |
| 大原簿記ビジネス公務員専門学校京都校 | Yes | /about/hyoka/ (group-level) |
| KCS大分情報専門学校 | Not on top page | May be deeper in site |
| 大阪医療看護専門学校 | Not tested (WebFetch denied) | - |
| 伊勢理容美容専門学校 | Not tested (syntax error) | - |

**Note**: 情報公開 pages are commonly located at:
- `/information` or `/info/`
- `/about/disclosure/` or `/about/hyoka/`
- Linked from footer navigation
- For Ohara schools: centralized at `o-hara.ac.jp/about/hyoka/`

---

## 6. Challenges and Edge Cases

### School Name Changes (4 schools affected)
- 大原スポーツ公務員専門学校盛岡校 --> 大原ビジネス公務員専門学校盛岡校 (April 2024)
- 大原簿記情報ビジネス医療福祉専門学校山形校 --> 山形スポーツ医療福祉専門学校 (April 2025)
- 水戸看護福祉専門学校 --> 水戸看護専門学校 (2024)
- 専門学校九州スクール・オブ・ビジネス --> 専門学校福岡ビジネス・アカデミー (April 2024)

**Impact**: Name changes reduce confidence slightly (0.85-0.90) because old names may still appear in search results, and the domain may not match the new name (e.g., ksb.ac.jp for a school no longer called "KSB").

### Large Group Schools (大原学園 pattern)
- 14 of 50 test schools (28%) belong to 大原学園
- All share the same domain: o-hara.ac.jp
- URL pattern is consistent: `/senmon/school/{campus_slug}/`
- 情報公開 is centralized at group level
- **Recommendation**: For Ohara schools, URL discovery can be pattern-based rather than search-based

### Public/Prefectural Schools
- 3 schools hosted on government sites (pref.*.lg.jp)
- No dedicated domain exists
- URL structures vary by prefecture
- These may be harder to scrape consistently

### Branded Names
- 愛媛県立農業大学校 uses branded name えひめ農業未来カレッジ with domain himekare.jp
- The official name and branded name differ significantly
- Search with official name still finds the correct site

---

## 7. Recommendations for Full-Scale Discovery (2,200 schools)

### Pattern-based shortcuts (for approximately 500+ schools):
1. **大原学園 schools (~30+ schools)**: Generate URLs as `o-hara.ac.jp/senmon/school/{slug}/` -- no search needed
2. **三幸学園 schools**: Similar pattern at `sanko.ac.jp/{campus}/`
3. **穴吹学園 schools**: Pattern at `web.anabuki-college.net/` or `web.anabukih.ac.jp/`
4. **NSG/FSG college league**: Multiple patterns but semi-predictable

### Search strategy for remaining schools:
1. Start with school name only
2. Fall back to school name + prefecture for ambiguous results
3. Use corporation name for large-group disambiguation
4. For public schools, also search `{school_name} site:pref.*.lg.jp`

### Verification pipeline:
1. HTTP status check (all should be 200)
2. Page title extraction and fuzzy match against school name
3. Check for 情報公開 link on top page or in footer
4. Flag schools where URL is a corporation/group page rather than school-specific page

### Expected success rates at scale:
- High confidence (>= 0.90): estimated 80-85% of 2,200 schools
- Medium confidence (0.85-0.89): estimated 10-15%
- Manual review needed: estimated 5-10% (closed schools, merged schools, schools without web presence)

---

## 8. Output Files

| File | Location | Description |
|------|----------|-------------|
| Test school list | data/url-discovery/test-schools-50.csv | 50 schools with stratified sampling |
| Discovered URLs | data/url-discovery/discovered-urls-50.csv | URLs with confidence scores and metadata |
| This report | docs/reports/2026-04-11-url-discovery-report.md | Analysis and recommendations |
