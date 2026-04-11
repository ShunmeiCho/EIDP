# EIDP Data Quality Report

Date: 2026-04-11
Source files:
- `sample/◆2025専門学校無償化情報公開まとめ.xlsx`
- `sample/20250826更新版_競合校の在校生数.xlsx`

---

## 1. Baseline Reconciliation (Problem #6)

### Sheet: `採録状況`

Total data rows (excluding header): **2212**

| Key strategy | Unique count |
|---|---|
| (都道府県, 法人名, 学校名) 3-col key | **2212** |
| (法人名, 学校名) 2-col key | **2211** |

**Discrepancy: 1 school**

The single collision is:

| 法人名 | 学校名 | 都道府県 |
|---|---|---|
| 大原学園 | 横浜情報ITクリエイター専門学校 | 千葉県, 神奈川県 |

### Interpretation

The same school `横浜情報ITクリエイター専門学校` (operated by `大原学園`) appears under two different prefectures: `千葉県` and `神奈川県`. This is almost certainly a data-entry error -- the "横浜" in the school name indicates it should be `神奈川県`. The `千葉県` entry is likely a misclassification.

### Recommendation

- Use the 3-column key `(都道府県, 法人名, 学校名)` as the canonical primary key for school identity.
- Flag the `大原学園 / 横浜情報ITクリエイター専門学校` duplicate for manual correction.
- The 2-col key `(法人名, 学校名)` is nearly sufficient but should not be used as a sole identifier because a 法人 could legitimately operate identically named schools in different prefectures.

---

## 2. Status Value Analysis (Problem #9)

### 2025年度 column (column index 9, 0-based)

Total rows: 2212, Distinct values: 15

| Status value | Count | Category |
|---|---|---|
| `〇` | 943 | Active target - data successfully collected |
| `△` | 804 | Active target - partially collected / incomplete |
| `None` (blank) | 288 | Edge case - not yet processed or unknown |
| `対象外` | 130 | Excluded - not subject to disclosure |
| `学校なし` | 22 | Excluded - school no longer exists at expected URL |
| `リンクミス` | 7 | Edge case - URL/link error, data inaccessible |
| `△（不足）` | 6 | Active target - collected but with missing fields |
| `職実代用` | 4 | Edge case - using vocational practice report as substitute |
| `統合` | 2 | Excluded - school merged into another |
| `不足` | 1 | Edge case - data insufficient |
| `閉校` | 1 | Excluded - school closed |
| `△（前年データ）` | 1 | Edge case - using prior year data instead of current |
| `職実` | 1 | Edge case - vocational practice data only |
| `前年データ` | 1 | Edge case - prior year data reused |
| `日付は変更されるが内容同じ` | 1 | Edge case - timestamp changed but content unchanged |

### Categorization Summary

| Category | Statuses | Count | % |
|---|---|---|---|
| **Active targets** | `〇`, `△`, `△（不足）` | 1753 | 79.3% |
| **Excluded** | `対象外`, `学校なし`, `統合`, `閉校` | 155 | 7.0% |
| **Edge cases** | `None`, `リンクミス`, `職実代用`, `不足`, `△（前年データ）`, `職実`, `前年データ`, `日付は変更されるが内容同じ` | 304 | 13.7% |

### Cross-Year Trends

Key observations across all years (2019-2025):
- `〇` (complete) peaked at 1670 in 2021, declined to 943 in 2025.
- `△` (partial) did not exist until 2020 (33), exploded to 804 by 2025. This suggests the collection process tracks incomplete records more carefully in recent years.
- `対象外` grew from 6 (2019) to 130 (2025), reflecting expanding awareness of non-target schools.
- The blank (`None`) count dropped from 1677 (2019) to 288 (2025), indicating the tracking list has been progressively filled in.
- Various ad-hoc statuses (`職実代用`, `リンクミス`, `欠損データ`, `一部職実`, etc.) appear inconsistently across years. There is no controlled vocabulary -- operators create free-text labels.

### Recommendation

- Formalize a status enum with at most 6 values: `完了`, `一部取得`, `未処理`, `対象外`, `閉校/統合`, `エラー`.
- Map all existing free-text statuses to the enum, preserving the original text in a separate `備考` (notes) column.

---

## 3. Multi-Header Parsing Test (Problem #8)

### Sheet: `学科別` Structure

- 83 columns total, 2-row header, 9759 data rows (rows 2-9760).
- Row 0: Year labels in merged cells (only the leftmost cell of each year group is non-None).
- Row 1: Sub-metric labels repeated per year.

### Column Layout

**Meta columns (cols 0-6, no year group):**

| Col | Header |
|---|---|
| 0 | 都道府県 |
| 1 | 法人名 |
| 2 | 学校名 |
| 3 | 課程名 |
| 4 | 学科名 |
| 5 | 昼夜 |
| 6 | 年限 |

**Year-grouped columns:**

| Year | Start col | End col | Sub-columns | Count |
|---|---|---|---|---|
| 2019年度 | 7 | 16 | 収定, 在籍, 留学生, 卒業, 進学, 就職, その他, 前年在籍, 中退, 中退率 | **10** |
| 2020年度 | 17 | 27 | 収定, 在籍, 留学生, 卒業, 進学, 就職, その他, 前年在籍, 中退, 中退率, **備考** | **11** |
| 2021年度 | 28 | 38 | (same 11 as 2020) | **11** |
| 2022年度 | 39 | 49 | (same 11) | **11** |
| 2023年度 | 50 | 60 | (same 11) | **11** |
| 2024年度 | 61 | 71 | (same 11) | **11** |
| 2025年度 | 72 | 82 | (same 11) | **11** |

**Critical irregularity:** 2019 has 10 sub-columns (no `備考`), while 2020-2025 each have 11 sub-columns (includes `備考`). Any naive parser that assumes uniform column count per year will misalign starting from column 17.

### Parsing Function

```python
def parse_gakka_headers(row0, row1):
    """
    Parse 2-row merged header of 学科別 sheet into flat column names.
    
    Args:
        row0: First header row (year labels, mostly None due to merged cells)
        row1: Second header row (sub-metric labels)
    
    Returns:
        List of flat column names like '2019_収定', '2019_在籍', etc.
        Meta columns (0-6) retain their row1 names as-is.
    """
    ncols = len(row0)
    flat = []
    
    # Forward-fill year labels from row0
    current_year = None
    year_for_col = []
    for i in range(ncols):
        if row0[i] is not None:
            current_year = str(row0[i]).replace('年度', '')
        year_for_col.append(current_year)
    
    for i in range(ncols):
        sub = row1[i]
        year = year_for_col[i]
        
        if year is None:
            # Meta column (cols 0-6)
            flat.append(str(sub) if sub else f'col_{i}')
        else:
            sub_str = str(sub) if sub else f'unknown_{i}'
            flat.append(f'{year}_{sub_str}')
    
    return flat
```

### Test Output (verified against actual data)

Columns 0-6: `都道府県, 法人名, 学校名, 課程名, 学科名, 昼夜, 年限`

Columns 7-16 (2019 block, 10 cols):
`2019_収定, 2019_在籍, 2019_留学生, 2019_卒業, 2019_進学, 2019_就職, 2019_その他, 2019_前年在籍, 2019_中退, 2019_中退率`

Columns 17-27 (2020 block, 11 cols):
`2020_収定, 2020_在籍, 2020_留学生, 2020_卒業, 2020_進学, 2020_就職, 2020_その他, 2020_前年在籍, 2020_中退, 2020_中退率, 2020_備考`

Pattern continues identically for 2021-2025 (11 cols each).

---

## 4. Sheet Year Comparison (Problem #10)

### `学科別` Year Coverage

Years present: **2019, 2020, 2021, 2022, 2023, 2024, 2025** (7 years)

Sub-metrics per year: 収定, 在籍, 留学生, 卒業, 進学, 就職, その他, 前年在籍, 中退, 中退率, (備考 from 2020+)

Total data rows: **9759**

### `在籍のみ抜粋` Year Coverage

Years present: **2019, 2020, 2021, 2022, 2023, 2024** (6 years)

Sub-metrics: Two groups
- 在籍者数: 2019-2024
- 留学生数: 2019-2024

Total data rows: **9244**
Total columns: **19** (7 meta + 6 在籍 + 6 留学生)

### Discrepancy

| Dimension | 学科別 | 在籍のみ抜粋 | Delta |
|---|---|---|---|
| Year range | 2019-2025 | 2019-2024 | **2025 missing from 在籍のみ抜粋** |
| Metrics | 10-11 per year | 2 per year (在籍 + 留学生) | 在籍のみ抜粋 is a filtered subset |
| Data rows | 9759 | 9244 | 515 fewer rows in 在籍のみ抜粋 |

### Interpretation

1. **Missing 2025:** `在籍のみ抜粋` has not been updated with 2025 data yet, while `学科別` already includes it. This is a synchronization gap -- the extract sheet lags behind the master sheet.

2. **Fewer rows:** The 515-row difference suggests `在籍のみ抜粋` filters out departments that have no enrollment data across any year (all-null rows), or departments from schools with certain excluded statuses.

3. **Metric reduction:** `在籍のみ抜粋` intentionally extracts only `在籍` (enrollment) and `留学生` (international students) from the full 10-11 metrics available in `学科別`. This is a purpose-built reporting view, not a full data copy.

### Recommendation

- Automate `在籍のみ抜粋` generation from `学科別` to prevent synchronization lag.
- Document the filtering criteria that cause the 515-row difference.
- Add 2025 data to `在籍のみ抜粋` or generate it programmatically.

---

## 5. Competition Taxonomy Reverse-Engineering (Problem #4 partial)

### Source: `20250826更新版_競合校の在校生数.xlsx`

16 sheets total. 1 is a school-level summary (`学校単位での比較`), 1 is a group-level analysis (`滋慶`), and 14 are field/discipline category sheets.

### Category Sheets Summary

| Category | Dept entries | Unique schools | Exact match in 学科別 | Fuzzy match | Unmatched |
|---|---|---|---|---|---|
| 放送・演劇スタッフ | 13 | 8 | 11 | 2 | 0 |
| 声優演劇・ミュージックアーティスト・ダンス | 19 | 10 | 16 | 2 | 1 |
| マンガ・アニメ | 13 | 10 | 10 | 3 | 0 |
| ゲーム | 13 | 9 | 9 | 3 | 1 |
| CG映像 | 9 | 7 | 7 | 1 | 1 |
| デザイン | 22 | 12 | 20 | 1 | 1 |
| コンイベ・音響芸術 | 11 | 7 | 8 | 1 | 2 |
| IT | 23 | 13 | 19 | 1 | 3 |
| ホテル・観光・情報ビジネス | 13 | 15 | 10 | 1 | 2 |
| 建築 | 15 | 9 | 14 | 1 | 0 |
| 自動車 | 12 | 7 | 11 | 1 | 0 |
| テクその他 | 17 | 8 | 17 | 0 | 0 |
| スポーツ | 13 | 6 | 10 | 3 | 0 |
| 鍼灸・柔整 | 13 | 6 | 13 | 0 | 0 |

**Total across categories:** 206 dept entries, ~140 unique schools

**学科別 reference set:** 5074 unique department names

### Match Quality

- **Exact matches:** High overall. Most competition department names appear verbatim in the `学科別` master list.
- **Fuzzy matches:** Caused by year-specific suffixes (e.g., `漫画・イラスト科※2025年新設` -> `漫画・イラスト科`) or duration qualifiers (`スポーツトレーナー科3年制` -> `スポーツトレーナー科`).
- **Unmatched names:** Mostly HAL-style composite department names like `CG・デザイン・アニメ4年制（CG映像）` which bundle multiple fields into one department name not found in the disclosure data, plus informal aggregation labels like `※3年制学科合計`.

### School Name Discrepancy

The competition file uses abbreviated school names (e.g., `日本工学院（蒲田）`, `日本工学院（八王子）`) while `学科別` uses full formal names (e.g., `日本工学院専門学校`, `日本工学院八王子専門学校`). Any automated cross-referencing will require a school name mapping table.

### Competition Categories as Department Taxonomy

The 14 category sheets represent the competitor's internal classification of vocational fields:

1. **Entertainment/Media:** 放送・演劇スタッフ, 声優演劇・ミュージックアーティスト・ダンス, コンイベ・音響芸術
2. **Creative/Design:** マンガ・アニメ, CG映像, デザイン
3. **Technology:** ゲーム, IT
4. **Business/Service:** ホテル・観光・情報ビジネス
5. **Engineering:** 建築, 自動車, テクその他
6. **Health/Sports:** スポーツ, 鍼灸・柔整

This taxonomy does not map 1:1 to the `課程名` (curriculum type) field in `学科別`, which uses MEXT-standard categories like `工業`, `商業実務`, `教育・社会福祉`, `医療`, etc. A mapping layer is required between the competition analysis taxonomy and the official curriculum classification.

### 滋慶 Group Analysis

The `滋慶` sheet tracks 7 departments across Jikei group schools. These departments are cross-category (the `該当分野` column maps one department to multiple competition categories, e.g., `マンガ・アニメ、ゲーム、CG映像、デザイン、IT、カーデザイン`). This means the competition analysis sometimes counts the same department's enrollment across multiple category sheets.

---

## Summary of Key Findings

1. **Primary key:** The 3-col key `(都道府県, 法人名, 学校名)` is effectively unique (2212 unique out of 2212 rows). One data-entry error (`大原学園/横浜情報ITクリエイター専門学校` listed under both `千葉県` and `神奈川県`) should be corrected.

2. **Status vocabulary:** 15 distinct free-text values in the 2025年度 column. No controlled vocabulary exists. The system needs an enum with clear mapping rules.

3. **Header parsing:** The `学科別` sheet has an asymmetric 2-row header: 2019 has 10 sub-columns while 2020-2025 each have 11 (adding `備考`). Naive uniform-width parsing will break. The provided `parse_gakka_headers()` function handles this via forward-filling.

4. **Year synchronization gap:** `在籍のみ抜粋` lacks 2025 data present in `学科別`. It also has 515 fewer rows, suggesting filtering that should be documented and automated.

5. **Competition taxonomy:** 14 competitive field categories covering 206 department-level entries. ~85% match exactly to `学科別` department names. School names require a lookup table due to abbreviated vs. formal name differences.
