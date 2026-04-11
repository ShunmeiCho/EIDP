# MEXT School Code Matching Report

Date: 2026-04-11
Status: Research / Investigation

---

## 1. MEXT School Code Data

### Source
- Official page: https://www.mext.go.jp/b_menu/toukei/mext_01087.html
- Version: R7 (2025) May 1 confirmed edition (令和7年5月1日時点 確定版)
- Published: 2025-12-26

### Downloaded Files
| File | Description | Size |
|------|-------------|------|
| `school_code_east.csv` | East Japan (Hokkaido - Mie) all school types | 4.3MB |
| `school_code_west.csv` | West Japan (Shiga - Okinawa) all school types | 3.1MB |
| `school_code_univ.csv` | Universities, junior colleges, technical colleges | 144KB |

### CSV Fields (12 columns)
| # | Field | Example |
|---|-------|---------|
| 0 | School Code (学校コード) | `H113310400202` |
| 1 | School Type (学校種) | `H1(専修)` |
| 2 | Prefecture Code (都道府県番号) | `13(東京都)` |
| 3 | Establishment Type (設置区分) | `3(私)` |
| 4 | Main/Branch (本分校) | `1(本)` |
| 5 | School Name (学校名) | `HAL東京` |
| 6 | Address (学校所在地) | full address |
| 7 | Postal Code (郵便番号) | `1600023` |
| 8 | Record Date (属性情報設定年月日) | `2020/12/22` |
| 9 | Abolition Date (属性情報廃止年月日) | empty if active |
| 10 | Legacy Survey Number (旧学校調査番号) | `013501` |
| 11 | Migration Code (移行後の学校コード) | empty or successor code |

### School Code Format
- 13-character alphanumeric code
- First character: school type (A=kindergarten, B=elementary, C=middle, D=high, E=special, F=university, G=kosen, H=senshu/misc)
- Second character: sub-type (1=main type, 2=sub-type)
- Characters 3-4: prefecture code
- Remaining: serial number

### Key Properties
- Once assigned, a school code is **never changed** and **never reused**
- When a school is abolished, the abolition date is recorded but the code is preserved
- When a school is reorganized, a migration code points to the successor
- Data is updated annually (confirmed edition ~December, provisional ~May)

### School Type Counts in East+West CSV
| Type | Count |
|------|-------|
| B1 (Elementary) | 19,725 |
| C1 (Middle) | 10,271 |
| A1 (Kindergarten) | 9,741 |
| A2 (Certified centers) | 7,771 |
| D1 (High school) | 5,093 |
| **H1 (Senshu/Vocational)** | **3,244** |
| E1 (Special support) | 1,212 |
| H2 (Misc schools) | 1,138 |
| C2 (Compulsory) | 262 |
| D2 (Secondary) | 61 |

Active (non-abolished) senshu gakko: **2,974**

---

## 2. Target Institution List (修学支援新制度 対象機関リスト)

### Source
- Official page: https://www.mext.go.jp/a_menu/koutou/hutankeigen/1421838.htm
- Version: As of April 1, 2026 (令和8年4月1日現在)
- File: `target_institutions.xlsx`

### Institution Counts
| Type | Count |
|------|-------|
| **Vocational schools (専門学校)** | **2,071** |
| Universities (大学) | 773 |
| Junior colleges (短期大学) | 243 |
| Technical colleges (高等専門学校) | 61 |
| **Total** | **3,148** |

### By Category (establishment type)
| Category | Count |
|----------|-------|
| Private vocational (専門学校/私立) | 1,855 |
| Private university (大学/私立) | 588 |
| Private junior college (短大/私立) | 226 |
| Public vocational (専門学校/公立) | 169 |
| Public university (大学/公立) | 102 |
| National university (大学/国立) | 82 |
| National kosen (高専/国立) | 52 |
| National vocational (専門学校/国立) | 46 |
| Public junior college (短大/公立) | 15 |
| Other | 9 |

### Key Finding
The target institution list **already includes MEXT school codes** (column A). This is critical -- it means the school code is the canonical identifier used across both datasets.

---

## 3. Matching Results: Our Excel vs MEXT School Codes

### Data
- Our source: `sample/2025専門学校無償化情報公開まとめ.xlsx`, sheet `採録状況`
- Total schools in our list: **2212**
- Covering all 47 prefectures

### Match Rates

| Strategy | Matched | Rate |
|----------|---------|------|
| A. Exact name match | 1879 | 84.9% |
| B. Fuzzy match (NFKC normalization) | +134 | +6.1% |
| C. Prefecture + partial name | +1 | +0.0% |
| **Cumulative** | **2014** | **91.0%** |
| Unmatched | 198 | 9.0% |

### Fuzzy Match Analysis
Most fuzzy matches were caused by full-width vs half-width character differences:
- `HAL東京` vs `HAL東京` (half-width vs full-width Latin)
- `&` vs `＆` (half-width vs full-width ampersand)
- `IT` vs `ＩＴ` (half-width vs full-width)

NFKC normalization resolves these automatically.

### Unmatched Schools Analysis (198 schools)

Of the 198 unmatched schools:
- **56** were found in the target institution list (by normalized name match) but not in the school code CSV -- likely very recently registered or under different naming
- **142** were not found in either dataset

Top corporations with unmatched schools:

| Corporation | Count |
|-------------|-------|
| 三幸学園 | 26 |
| 国立病院機構 | 26 |
| 大原学園 | 15 |
| 国際総合学園 | 6 |
| 瀧澤学館 | 6 |
| 東京滋慶学園 | 3 |
| 厚生労働省 | 3 |
| 愛知県厚生農業協同組合連合会 | 3 |
| 滋慶学園 | 2 |
| 八文字学園 | 2 |

#### Root Causes for Unmatched Schools

1. **Recently renamed schools** (largest group): Schools like 三幸学園's chain have undergone name changes (e.g., added "AI", "IT", "&" variations). The MEXT school code CSV may lag behind these changes.

2. **National hospital-affiliated schools** (国立病院機構): 26 schools run by the National Hospital Organization. These appear under different naming conventions (e.g., `独立行政法人国立病院機構` prefix in MEXT vs shortened names in our list).

3. **大原学園 branch campuses**: Schools like `大原簿記公務員情報医療専門学校函館校` -- the branch suffix (函館校) may not match the MEXT registration exactly.

4. **Prefecture mismatch in our data**: A few entries like `沖縄県 / 札幌ビューティアート専門学校` appear to have data errors in our source Excel.

---

## 4. University Investigation

### Universities in the Target List
- Total universities: **773**
  - National (国立): 82
  - Public (公立): 102
  - Private (私立): 588

### University Disclosure Format

Based on web research of several university disclosure pages:

**Sample universities checked:**
1. Kindai University (近畿大学): https://www.kindai.ac.jp/about-kindai/disclosure/educational-info/school-support/
2. Tokyo Univ. of Agriculture & Technology (東京農工大学): https://www.tuat.ac.jp/outline/jyouhoukoukai/syugakushien/
3. Ibaraki University (茨城大学): https://www.ibaraki.ac.jp/student/economicsupport/excnewsys/newstudysupport/

**Key differences from vocational schools:**
- Universities publish their disclosure information on their own websites (not in a standardized aggregated format)
- The disclosure format follows MEXT-prescribed forms (様式) but the presentation varies by institution
- Typical disclosed items include:
  - Practical experience instructor ratios (実務経験のある教員による授業科目)
  - External board member composition
  - Teaching methods and content
  - Financial/management information (様式2号の4)
  - Enrollment numbers, graduation rates, employment rates
- **Format is NOT the same as vocational schools** -- universities have more complex structures (multiple faculties/departments) and different reporting requirements
- PDF formats vary significantly across universities; there is no single standardized PDF template

### Feasibility of University Data Collection
- **Difficulty: HIGH** -- each university publishes in its own format on its own website
- **Scale: 773 institutions** (vs 2,071 vocational schools)
- **Standardization: LOW** -- unlike vocational schools where prefectures often aggregate data, university data is scattered
- **Not recommended for EIDP Phase 1** -- focus on vocational schools first

---

## 5. Conclusions and Recommendations

### MEXT School Codes as Stable Identifiers: VIABLE

**Strengths:**
1. **Permanence**: Codes are never changed or reused -- a school retains its code for life
2. **Universality**: All 3,244 senshu gakko have codes (covers our 2,212 schools well)
3. **Official backing**: Maintained by MEXT, updated annually
4. **Cross-dataset linkage**: The target institution list already uses these codes
5. **High match rate**: 91.0% of our schools can be matched automatically

**Weaknesses:**
1. **Name discrepancies**: ~9% of schools have name mismatches requiring manual resolution
2. **Update lag**: CSV is published annually; recently renamed schools may not appear immediately
3. **Encoding issues**: CSV uses Shift-JIS (cp932), requiring encoding handling
4. **No API**: Only bulk CSV/Excel downloads (though edu-data.jp provides a search interface)

### Recommended Actions

1. **Adopt MEXT school code as primary key** for school identification in EIDP
2. **Build a one-time mapping table**: Manually resolve the 198 unmatched schools
3. **Use NFKC normalization** as standard preprocessing for name matching
4. **Re-download school code CSV annually** (December confirmed edition)
5. **Cross-reference with target institution list** to ensure all schools in scope are covered
6. **Defer university data collection** to a later phase

### Data Pipeline Recommendation

```
[Our Excel] --(name match)--> [MEXT School Code CSV]
                                    |
                              [school_code as PK]
                                    |
                    [Target Institution List] -- confirms eligibility
                                    |
                    [School disclosure pages] -- scrape enrollment data
```
