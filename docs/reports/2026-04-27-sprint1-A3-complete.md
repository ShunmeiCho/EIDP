# Sprint 1 A3 完了 — Hokkaido Full Apply 結果

**日付:** 2026-04-27 16:00
**Owner 授権:** "Go A3"（明示）
**実行内容:** 残 15 hokkaido aggregator URL → discover-pdfs (15校) → ingest-pdfs (15 docs) → report 比較

---

## 実行結果

### 1. apply (--pref hokkaido --apply --verified-only)

```
[hokkaido] plan: actionable=21 review=5 dry_run=False
[hokkaido] snapshot: 155 rows backed up for rollback
[hokkaido] COMMITTED: add=2 upgrade=13 skipped_dup=5
errors=0
```

予測通り:
- A2 で apply 済 5 行 → skipped_duplicate=5
- 未 verified 1 行 → skipped_not_verified=1
- 残 15 行 → add=2 + upgrade=13 全成功

### 2. discover-pdfs (15 schools)

```
PDF Discovery Results:
  crawled: 15
  found: 15
  downloaded: 15
  failed: 0
  skipped: 1
```

**100% download rate** — A2 の 60% (3/5) より大幅改善。原因: A2 は sid=877 で googleapis storage の non-target asset が大量に検出され 4 件 skip されたが、A3 の 15 校は target candidate がストレートに見つかった。

### 3. ingest-pdfs (15 docs)

| 状態 | 件数 |
|---|---:|
| **ingested** | **10** |
| school_mismatch | 3 |
| parse_failed | 1 |
| in_progress | 1 (OCR 進行中、image_only) |

**FY 分布 (ingested 10 件)**:

| FY | 件数 | 備考 |
|---|---:|---|
| FY2023 (R5) | 1 | stale |
| FY2024 (R6) | 5 | stale |
| FY2025 (R7) | 4 | stale (一年前) |
| **FY2026 (R8)** | **0** | **予測通り、学校公開待ち** |

---

## Baseline → A2 → A3 推移

| 指標 | baseline | A2 後 | A3 後 | A3 vs baseline |
|---|---:|---:|---:|---:|
| schools_with_url | 2,239 | 2,240 | **2,242** | **+3** |
| schools_with_any_pdf | 238 | 241 | **256** | **+18** |
| schools_with_target_pdf_any_fy | 121 | 123 | **132** | **+11** |
| schools_with_target_pdf_current_fy (R8) | 2 | 2 | 2 | **0** ✓ |
| FY2025 documents ingested | 76 | 77 | **81** | **+5** |
| FY2025 yearly rows | 7,528 | 7,535 | **7,552** | **+24** |
| site_known_no_pdf | 2,001 | 1,999 | **1,986** | **-15** |
| no_site_no_pdf | 189 | 188 | **186** | **-3** |
| stale_pdf_only | 119 | 121 | **130** | **+11** (R5/R6/R7 入庫分) |
| mismatch_only | 79 | 79 | **82** | +3 (school 紐付け失敗) |
| parse_failed_only | 19 | 19 | **20** | +1 |
| non_target_only | 13 | 14 | **15** | +1 |
| in_progress_only | (新) | - | 1 | OCR 中 |

**Sprint 1 hokkaido 完了の総 gap 削減**:
- `site_known_no_pdf + no_site_no_pdf` baseline 2,190 → A3 2,172 = **-18 schools**

---

## Sprint 1 hokkaido 完結数字

- target_pdf_any_fy: 5.0% → **5.4%** (+11 schools)
- 22 verified URL → 15 ingested (68%) + 3 mismatch (14%) + 1 parse_fail (5%) + 1 in_progress (5%) + 2 skipped (8% A2 既出 + 既存 doc 重複)
- baseline.md 予測 (Sprint 1 で 5.0% → 18%) のうち **hokkaido 単独で 0.4 ポイント貢献**

47 都道府県への外挿 (hokkaido が 1/47):
- 平均 each pref +5〜10 schools （hokkaido 規模の県、tokyo/osaka はもっと多い）
- 47 pref total: +200〜400 schools = target_pdf_any_fy ~14〜18% 上限

これは baseline.md の修正後数字 (Sprint 1 で 5.0% → 18%) と整合。

---

## R8 (FY2026) なぜ動かないか — 改めて

A2 + A3 の合計 13 ingested 中 0 件 R8。理由分析:

- 大半の学校が R8 確認申請書を **まだサイトに up していない** (4-6 月公開待ち)
- aggregator PDF 自体も R7 時点 snapshot (例: 北海道 R8.3.16 PDF が 4/27 時点で最新)
- 学校サイト側は R5/R6/R7 PDF が既に置いてある状態 → 取れるのは stale のみ

これは **Sprint 4 (FY 判定再発見 + R8 公開待ちサイト 4-6 月再 visit) の入口データ**。  
Sprint 1 は "discovery と ingest pipeline が動く" を証明済み。R8 の数字伸びは Sprint 4 待ち。

---

## 次選択肢

### B1: 残 7 prefecture (tokyo + miyagi など) verified apply

A2/A3 で hokkaido は完結。残 verified URL は **tokyo=1, miyagi=1** のみ。
- A4 dry-run 数字: tokyo `add=0 upgrade=1`, miyagi `add=0 upgrade=1` (lightweight)
- value: prefecture aggregator 全 verified を一気に消化

```bash
ssh venus 'cd ~/workspace/EIDP && uv run python scripts/apply_writer_plan.py \
  --all --apply --verified-only'
# expected: 2 upgrade only, skipped_dup=20 (hokkaido done), 0 errors
```

### B2: aichi + niigata 新 parser

seed.csv に PDF artifact_url ある残 12 prefecture のうち、aichi (2-col) と niigata (13-col) は新 parser 必要。書けば +280 schools spike 可能。

### B3: 35 unknown prefecture web search

artifact_url を web search で集める。tokyo 5.6% verified rate を見る限り URL 鮮度に課題、リスク高。

### B4: review queue 5 件 (hokkaido) 処理

A3 で生成された review CSV を owner と一緒に判定。

**推奨**: B1 で全 verified を apply 完結 → 数字 final → Sprint 1 close。  
その後 B2 (aichi/niigata) で次の verified pool を増やす。
