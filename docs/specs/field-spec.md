# EIDP Field Specification (Frozen)

Date: 2026-04-11
Status: FROZEN (Step 1 complete)

---

## Output File 1: 専門学校無償化情報公開まとめ.xlsx

Sheet order: 採録状況 → 対象比率 → 学科別 → 在籍のみ抜粋

### Sheet 1: 採録状況
| Column | Type | Description |
|--------|------|-------------|
| 都道府県 | str | Prefecture name |
| 法人名 | str | Corporation name |
| 学校名 | str | School name |
| 2019年度 | str | Collection status (〇/△/blank/対象外/学校なし/etc.) |
| 2020年度 | str | Same |
| 2021年度 | str | Same |
| 2022年度 | str | Same |
| 2023年度 | str | Same |
| 2024年度 | str | Same |
| 2025年度 | str | Same |

Status values (15 distinct, free-text): 〇, △, △（不足）, △（前年データ）, 対象外, 学校なし, 統合, 閉校, リンクミス, 職実, 職実代用, 不足, 前年データ, 日付は変更されるが内容同じ, (blank)

Rows: 2,212

### Sheet 2: 対象比率

### Sheet 3: 学科別
Multi-row header (row 1 = year groups, row 2 = field names).
7 key columns + 7 year blocks.

| Key Columns | Type |
|-------------|------|
| 都道府県 | str |
| 法人名 | str |
| 学校名 | str |
| 課程名 | str |
| 学科名 | str |
| 昼夜 | str (昼/夜) |
| 年限 | int |

| Year Block Fields (per year) | Type | Note |
|-----------------------------|------|------|
| 収定 | int | Capacity |
| 在籍 | int | Enrollment |
| 留学生 | int | International students |
| 卒業 | int | Graduates |
| 進学 | int | Advanced to higher ed |
| 就職 | int | Employed |
| その他 | int | Other |
| 前年在籍 | int | Previous year enrollment |
| 中退 | int | Dropouts |
| 中退率 | float | Dropout rate |
| 備考 | str | Notes (2020-2025 only, NOT in 2019) |

Year blocks: 2019 (10 cols, no 備考), 2020-2025 (11 cols each, with 備考)
Total columns: 7 + 10 + (6 * 11) = 83

Rows: 9,759

### Sheet 4: 在籍のみ抜粋
Point-in-time snapshot. NOT a live derived view.

| Columns | Count |
|---------|-------|
| Key columns (same as 学科別) | 7 |
| 在籍者数 per year (2019-2024) | 6 |
| 留学生数 per year (2019-2024) | 6 |
| **Total** | **19** |

Generation rule: all rows from 学科別 at generation time, column-reduced, one year behind.
Rows: 9,244 (based on previous snapshot)

### Sheet 2: 対象比率 (detail)
| Column | Type | Description |
|--------|------|-------------|
| 番号 | int | Serial number |
| 年度 | str | Fiscal year |
| 学校番号 | str | School number |
| 都道府県 | str | Prefecture |
| 法人名 | str | Corporation |
| 学校名 | str | School name |
| 前年在籍 | int | Previous year total enrollment |
| 前半期 | int | First half recipients |
| 第Ⅰ区分 | int | Category I |
| 第Ⅱ区分 | int | Category II |
| 第Ⅲ区分 | int | Category III |
| 第Ⅳ区分 | int | Category IV |
| 後半期 | int | Second half recipients |
| 第Ⅰ区分 | int | Category I (2nd half) |
| 第Ⅱ区分 | int | Category II (2nd half) |
| 第Ⅲ区分 | int | Category III (2nd half) |
| 第Ⅳ区分 | int | Category IV (2nd half) |
| 年間 | int | Annual total |
| 家計急変多子世帯 | int | Household emergency multi-child |
| 総計 | int | Grand total |
| 備考 | str | Notes |
| 受給比率 | float | Recipient rate |

Rows: ~10,057 (multi-year, school-level)

---

## Output File 2: 競合校の在校生数.xlsx

16 sheets total:
- 1 summary sheet: 学校単位での比較
- 1 group analysis: 滋慶
- 14 field category sheets

### Field Categories (14)
1. 放送・演劇スタッフ
2. 声優演劇・ミュージックアーティスト・ダンス
3. マンガ・アニメ
4. ゲーム
5. CG映像
6. デザイン
7. コンイベ・音響芸術
8. IT
9. ホテル・観光・情報ビジネス
10. 建築
11. 自動車
12. テクその他
13. スポーツ
14. 鍼灸・柔整

### Sheet A: 学校単位での比較 (Summary, 32 columns)

3-row header (rows 3-5). Two side-by-side school comparison blocks.

| Row | Columns |
|-----|---------|
| 3 | (blank, blank), 2019, _, 2020, _, ..., 2025, _, (blank, blank), 2019, _, ..., 2025, _ |
| 4 | (blank, school name), 在籍数, 留学生, 在籍数, 留学生, ..., (blank, school name), 在籍数, 留学生, ... |
| 5 | (blank, blank), 前年比, 留学生比率, 前年比, 留学生比率, ... |

Per year: 2 columns (在籍数, 留学生) in row 4 / (前年比, 留学生比率) in row 5
Structure: 2 key cols + 7 years * 2 = 16 cols per block. Two blocks separated by 2 blank cols. Total: 16 + 2 + 16 - 2 (shared separator) = 32 columns exactly.

Rows: 49

### Sheet B: 滋慶 (Group Analysis, 18 columns)

3-row header (rows 3-5).

| Column | Description |
|--------|-------------|
| Col 1 | School name (東京コミュニケーションアート etc.) |
| Col 2 | Department name |
| Col 3 | 該当分野 (field category label, e.g., マンガ・アニメ, ゲーム) |
| Col 4 | Duration (年限: 4年制, 3年制, etc.) |
| Cols 5-18 | Per year (2019-2025): 在籍数, 留学生 (2 cols * 7 years = 14) |

Row 5 shows: 前年比, 留学生比率 (derived values)
Rows: 73

### Sheet C: Per-category sheets (14 sheets, 18 columns each)

Same column count as 滋慶 (18) but the 該当分野 column is replaced by an additional key column.

| Column | Description |
|--------|-------------|
| Col 1 | School name |
| Col 2 | Department name |
| Col 3 | Duration (年限) |
| Col 4 | (blank or additional identifier) |
| Cols 5-18 | Per year (2019-2025): 在籍数, 留学生 (row 4) / 前年比, 留学生比率 (row 5) |

Total: 4 key + 14 data = 18 columns.
Classification is determined by sheet name, not by a column value.

---

## DB Table Count: 12

school, school_site, crawl_job, document, department, department_change,
department_yearly, school_year_status, school_alias, support_recipient,
taxonomy_mapping, review_item
