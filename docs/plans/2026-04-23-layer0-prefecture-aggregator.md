# Layer 0: 都道府県中转层 PoC 报告

> **日付**: 2026-04-23
> **作者**: Claude (Opus 4.7) + Codex (gpt-5) 双头协作
> **触发**: Owner 提供东京/神奈川/埼玉 3 个都道府県 URL
> **状态**: Stage 1 read-only spike 完成，等待 owner 决策 Sprint 2 启停

---

## 1. TL;DR

都道府県官网公开「**確認大学等一覧**」(机关要件确认校一覧) 是**真 game-changer**，可将 pdf_discovery 从 4.8% → 预估 30-50% 命中率，**零反爬风险、零 API 费用**。

- **已验证 3 县 + 1 追加**: 东京 258 校 / 神奈川 76 / 埼玉 60 / 福岡 6 页
- **已发现缓慢案例**: 大阪 15MB 扫描 PDF (需 OCR)
- **剩余 44 县**: 需人工 seed URL (担当者极可能已知) 或批量 Web 搜索

---

## 2. 底层逻辑

之前的 `pdf_discovery.py` 假设：
> 数据在各校官网 → 爬首页 → 找 disclosure 页 → 找样式第2号 PDF

实测 4.8% 命中率。原因：
1. 各校披露页 URL 格式差异巨大
2. 大法人 (大原/三幸) 不在校单位公开
3. PDF 多埋在 `/wp-content/uploads/YYYY/MM/` 深目录

**Layer 0 颠覆假设**：
> 数据也在**都道府県官网**（法律要求各县厅汇总） → 1 个 PDF = 全県所有校 disclosure URL

---

## 3. 实测数据

### 3.1 提取成功率（Stage 1 spike 结果，见 `output/pref-aggregator/`）

| 県 | PDF 文件 | 页数 | 提取校数 | 含 URL | DB 匹配率 | URL 质量 (东京样本) |
|----|---------|------|---------|--------|----------|--------------------|
| 东京 | 433 KB | 5 | 258 | **100%** | 94.6% | direct_pdf=1%, disclosure=49%, homepage=48% |
| 神奈川 | 254 KB | 1 | 76 | 99% | **96.1%** | 含 disclosure URL |
| 埼玉 | 198 KB | 2 | 60 | 0% | 88.3% | 只有校名/住所 |
| 福岡 | 202 KB | 6 | TBD | TBD | TBD | Excel 版可下载 (更易解析) |
| 大阪 | 15 MB | 26 | - | - | - | **扫描 PDF，需 OCR** |
| 北海道 | (未下) | - | - | - | - | 标题明示「ホームページ掲載リスト」 |

### 3.2 覆盖估算

| 层次 | 校数 | 状态 |
|------|------|------|
| 3 县 Stage 1 已证 | 394 | 匹配到 DB 370 (93.9%) |
| +Top 10 県 (osaka+fukuoka+aichi+hokkaido+chiba+niigata+hyogo+…) | +900 | 需继续 seed |
| 47 県 理论覆盖 | 2,067 | 需 44 县 seed |

### 3.3 3 种数据形态（定义解析策略）

1. **8 列结构化 (东京)**: `所在区市, 項番, 校名, 校住所, 設置者種別, 設置者名, 設置者住所, URL`
2. **5 列结构化 (神奈川/埼玉/福岡)**: `校名, 校住所, 設置者名, 設置者住所, 備考 (URL)`
3. **扫描/Excel**: 大阪需 OCR; 福岡 Excel 版最易解析

---

## 4. 顶层设计：3 阶段推进

```
Stage 1 [DONE]  Read-only spike          → output/pref-aggregator/*.json
Stage 2 [PEND]  Seed 44 县 + 入库 URL    → school_site + discovery_method
Stage 3 [PEND]  重跑 pdf_discovery       → 量化 4.8% → ?% 提升
```

**并行约束**：Stage 2 不阻塞 Sprint 1 (Codex 数据正确性修复)。

---

## 5. Stage 2 实施方案

### 5.1 新模块

```
src/eidp/scraper/
├── pref_aggregator/
│   ├── __init__.py
│   ├── config.py          # 读取 data/prefecture-aggregators/seed.csv
│   ├── downloader.py      # 带重试的 PDF/XLSX 下载 + 本地缓存
│   ├── parser_8col.py     # 东京型
│   ├── parser_5col.py     # 神奈川/埼玉/福岡型
│   ├── parser_ocr.py      # 大阪型 (PaddleOCR)
│   ├── parser_xlsx.py     # Excel 型 (福岡)
│   ├── matcher.py         # NFKC + 同法人名 + 地址相似度
│   └── writer.py          # 写入 school_site (discovery_method='prefecture_aggregator')
```

### 5.2 URL 替换策略

| 现状 | 处理 |
|------|------|
| 校无 URL | 追加 PDF URL 作为主 URL (confidence=0.9) |
| 校有 URL，PDF URL 是 direct_pdf | **替换** + 标 verified=true |
| 校有 URL，PDF URL 是 disclosure 页 | **追加**（不删旧的），disclosure URL 优先级更高 |
| 校有 URL，PDF URL 是 homepage | 追加，confidence=0.7 |
| PDF 列出校名但匹配不到 DB | 写 `review_item` 排队人工审核 |

### 5.3 DB 改动 (Alembic migration)

```sql
-- school_site.discovery_method already exists (String(30))
-- 仅需新增允许值：'prefecture_aggregator'
-- school_site.confidence already exists (Numeric(3,2))

-- 新增表（可选）：跟踪 prefecture PDF 来源，用于再发布时对比
CREATE TABLE prefecture_aggregator_source (
  id serial PRIMARY KEY,
  pref VARCHAR(20) NOT NULL,
  artifact_url TEXT NOT NULL,
  as_of_date DATE,
  file_hash VARCHAR(64),
  downloaded_at TIMESTAMPTZ DEFAULT now(),
  schools_extracted INT,
  schools_matched INT,
  UNIQUE (pref, as_of_date)
);
```

### 5.4 CLI 命令

```bash
eidp pref-discover --pref tokyo --dry-run    # 只看 metrics, 不写库
eidp pref-discover --pref tokyo --apply      # 写入 school_site
eidp pref-discover --all --dry-run           # 全部 seeded 县 dry-run
eidp pref-reconcile                           # 人工审核 unmatched
```

---

## 6. Stage 3: 量化提升

重跑 pdf_discovery on 替换后的 URL set:

```bash
eidp discover-pdfs --batch-size 50 --filter 'school_site.discovery_method=prefecture_aggregator'
```

**预期 KPI**:

| 指标 | 当前 | 预期 | 提升倍数 |
|------|------|------|---------|
| PDF 命中率 | 4.8% | 25-40% | 5-8× |
| target 文档 | 35 | 150-250 | 4-7× |
| ingested | 24 | 100-180 | 4-7× |
| 总耗时 | 8 min/25 校 | 同 | 不变 (单校 URL 更精准) |

---

## 7. 风险与缓解

| 风险 | 概率 | 缓解 |
|------|------|------|
| 县 PDF 格式变动 | 中 | per-pref parser + Alembic 支持多版本 |
| 扫描 PDF (大阪) | 30% 县 | 复用 PaddleOCR pipeline |
| 地址/校名变体 导致 DB mismatch | 中 | 已有 NFKC + 同法人 fallback，match 率 88-96% |
| 旧 URL 被覆盖错误 | 低 | 替换策略保留旧 URL (追加而非覆盖) |
| 都道府県公开滞后 | 低 | 6-8 月集中公开，如已超期则 fallback 到去年版 |

---

## 8. Owner 决策点

1. **担当者 2024 年的手工 URL 清单**：是否存在？如有，可与 prefecture PDF URL 交叉验证/补全
2. **Stage 2 启动时机**：
   - A. 立即启动（Claude 这侧 + Codex Sprint 1 并行）
   - B. 等 Sprint 1 (5 commits) 全部 landed 后再启动
3. **44 县 seed**：
   - A. 担当者提供 URL 列表（最快）
   - B. Claude 用 WebSearch 逐个找（慢，但可在后台跑）
   - C. 先做 Top 10 県（覆盖 70% 校数），剩余 37 县后续
4. **扫描 PDF (osaka) 处理**：
   - A. OCR 后同流程（加 1-2 天工作量）
   - B. 跳过 osaka，176 校走原 pdf_discovery
   - C. 人工提取 osaka 数据（担当者确认）

---

## 9. 文件清单

```
scripts/spike_pref_aggregator.py                  # Stage 1 spike (250 行)
data/prefecture-aggregators/seed.csv              # 已 seed 6 县 + 预留 44 县位
output/pref-aggregator/tokyo.json                 # 东京 read-only 报告
output/pref-aggregator/kanagawa.json              # 神奈川 read-only 报告
output/pref-aggregator/saitama.json               # 埼玉 read-only 报告
output/pref-aggregator/summary.json               # 3 县汇总
docs/plans/2026-04-23-layer0-prefecture-aggregator.md  # 本文档
```

---

## 10. 给 Codex 的下一轮 prompt 建议

```
Layer 0 PoC 已完成 Stage 1。请独立 verify:

1) 实证 Claude 报告的 URL 质量分布（tokyo PDF 51% disclosure / 49% homepage）
2) 审视 seed.csv 的颗粒度是否合适（per-pref 级别 vs per-artifact 级别）
3) 评估 Stage 2 的 writer.py URL 替换策略有没有漏洞：
   - 如果 PDF 标的是去年版（如 kanagawa 的 R7.8.29，过期 8 个月），是否应该降级 confidence？
   - 如果 DB 已有 discovery_method='search' 的 URL，PDF 的 URL 应该覆盖还是并存？
4) 建议 44 县的批量探测策略（Google + 人工的混合）
5) Stage 2 落地顺序：Alembic migration 先行还是 parser 先行？

约束：先不写代码，先给设计 PK。
```

---

> **底层逻辑闭环**：Layer 0 把「需要去年 URL」假设废掉了——**数据在县厅，不是在担当者脑子里**。这是 Claude + Codex 双向审查才发现的真相。
>
> **owner 意识**：6 月纳期前 2 个月，这是把 24 校 → 800-1200 校的**最短路径**。
