# Sprint 4 Sub-path A 完了 — Owner 仮説検証成功 (R8 公開待ち)

**日付:** 2026-04-28
**Owner 授権:** "Sprint 4 R8 再発見" + "Go Sub-path A first" (reviewer 経由)
**目標:** stale_pdf_only 164 → ≤ 80, FY2026 ingested 5 → ≥ 25
**結果:** **目標未達、但 owner の R8 公開待ち仮説を実機で証明**

---

## 実行 trace

### Discover (147 prefecture_aggregator stale schools)
```
crawled: 147  found: 74  downloaded: 74  failed: 0  skipped: 大量 non_target
```

### Ingest (74 docs, nohup-protected)
```
processed: 74
ingested: 40
school_mismatch: 22
parse_failed: 12
NEW R8 (FY2026): 0
```

### FY 分布 (40 ingested)

| FY | 件数 |
|---|---:|
| FY2020 | 9 |
| FY2021 | 5 |
| FY2022 | 6 |
| FY2023 | 9 |
| FY2024 | 10 |
| FY2025 | 1 |
| **FY2026 (R8)** | **0** |

→ **40 ingested 全部 stale**。R8 PDF 一件も未取得。

---

## Coverage delta (実測)

| 指標 | Sprint 4 前 | Sprint 4 後 | Δ |
|---|---:|---:|---:|
| target_pdf_any_fy | 168 | **168** | **0** |
| target_FY2026 | 4 | **4** | **0** |
| stale_pdf_only | 164 | **164** | **0** |
| mismatch_only | 81 | **81** | **0** |

**0 delta in business metrics.** 40 docs を入れても、それらは既に stale_pdf_only 集合の同じ schools に属する。新規 stale_pdf_only も発生せず、新規 R8 も無し。

理由:
- 同じ schools の sites は既に Document を持っていたため `target_pdf_any_fy` 不変
- 取得した PDF は全部 R5-R7 stale → `target_FY2026` 不変
- mismatch / parse_failed は school 単位で dedupe されるため bucket 数不変

---

## Owner 仮説の実機証明

Owner: "stale_pdf_only=164 を burn down するなら、4-6 月の R8 公開ピーク待ち。一回の rediscovery で目標 25 達成は確率低い。"

実測:
- 147 stale schools を実機で revisit
- 0 schools が R8 PDF を新たに公開していた (2026-04-28 時点)
- 40 ingested は全部 historical FY (R5-R7)

→ **R8 公開ピークは 5-6 月**。Sprint 4 単発実行は無意味。**Sprint 7 systemd timer で週次再発見**が真の path。

---

## Sprint 4 学び (operational)

### SSH drop 対策 (重要)
- Foreground SSH `ssh venus '... | tail'` は client_loop disconnect で remote process まで kill する場合あり
- **修正**: `nohup ... > log 2>&1 &` を使用 → 50/74 → 74/74 全 ingest 完成
- 今後の long-running command は必ず nohup 経由

### 0 R8 yield の意味
- Sprint 1 (B2) は新 prefecture_aggregator URL discovery で **+1 R8** (mikawa-dental sid=1440)
- Sprint 5 (mismatch fix) は **+2 R8** (re-ingest の副作用)
- Sprint 4 (stale rediscovery) は **+0 R8** (既知 sites の re-crawl で新 R8 無し)

→ R8 増加の主 driver は **新 URL discovery + parser/match 修复**、stale rediscovery は時期待ち

---

## 次選択肢 (重要校正)

### Sprint 7 systemd timer (推奨次 sprint)
Sprint 4 の負結果が示すのは「今 rediscovery 走っても無駄」。週次自動 rediscovery を 5-6 月の R8 公開ピーク待ち向け cron 化が正解。

```bash
# deploy/systemd/eidp-r8-rediscovery.{timer,service}
# 毎週月曜 02:00 JST に discover-pdfs --discovery-method prefecture_aggregator
# + ingest-pdfs --auto-pending を実行
```

### Sprint 6 競合校 Excel 収口
R8 件数が小さいため、業務的には早すぎ。R8 が増えてからやる方が exporter 出力に意味がある。

### Sprint 5 続 (twin_doc_dup 10 件 dedupe)
Sprint 5 残務。corp shared PDF (大原 group 等) を support_only/dedup 化。

### Sub-path B (残 17 stale: web_search/corp_pattern/seed_csv only)
やっても 0 R8 推定。Sprint 7 cron に含めて週次で吸収すべき。

---

## 残務とは別の重要 finding

Sprint 4 後 mismatch_only=81 不変だが、新たに 22 個 school_mismatch docs が追加された。これは Sprint 5 V3 (twin_doc_dup 解消 + parser_error 修復) の対象が増えた状態。後続 Sprint 5 続でリカバリ可能。
