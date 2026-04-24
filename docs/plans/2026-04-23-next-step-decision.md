# EIDP 下一步决策文档（post-compact resume 指南）

> **目的**：承载跨 compact / cross-session 需要保留的关键决策 context。
> **生成时间**：2026-04-23 22:30 JST
> **Git HEAD**：`8de7fc6`
> **使用方法**：新会话恢复后 `Read` 此文件即可接上。

---

## 1. 项目状态快照（Venus DB 实查）

```
schools (active)          : 2,428
school_site (total)       : 2,663
school_site (pref_agg)    : 166  (all verified=true)
school_site (web_search)  : 1,623 (含 hotstar/baidu/wiki 污染，未修)
documents (total)         : 241    (22 小时前为 109, +132)
  ├─ pending ingest (NULL): 132
  │   ├─ target           : 118
  │   └─ image_only       :  14  (等 OCR，GPU 激活)
  └─ already ingested     :  24  ← **未变的核心业务数字**
snapshot tables           : 9  (school_site_backup_{pref}_{ts})
fy_future (>2025 污染)    : 2  (未清)
tests                     : 34/34 pass, ~5% coverage
```

**Layer 0 URL 发现真实命中率：127/132 = 96%**（远超之前盲爬 4.8%）

---

## 2. 近期 8 commits（2026-04-21 baseline `31a4a85` 之后）

```
8de7fc6 feat(p0-6b): --discovery-method filter + rollback_apply script
7b1a835 chore: AGENTS.md + gitignore skill migration notes
0d92c65 feat(layer-0): rescue_suspect_urls second-pass verifier
63554ff feat(layer-0): HTTP ownership verify + --verified-only apply gate
c6c6e36 feat(layer-0): Stage 2 dry-run writer plan + apply script
f310ff4 feat(layer-0): prefecture aggregator spike + Codex PK artifacts
0d6d0c1 fix: bound parsed fiscal years
31a4a85 security: add gitleaks config + pre-commit hook   ← baseline
```

---

## 3. Codex Adversarial Review 5 个 HIGH finding（未修）

| # | 位置 | 问题 | 修复方向 |
|---|------|------|---------|
| 1 | `scripts/apply_writer_plan.py` ~226 | `--verified-only` 非强制，`--apply` 可绕过导致 suspect URL 入库 | 改为 default-on，需 `--allow-unverified` 显式 opt-out |
| 2 | `scripts/http_verify_plan_urls.py` ~110 | `ownership_ok` 对 direct_pdf 只看 `%PDF-` magic，不验 PDF 内容含学校名 | direct_pdf 分支下载首页文本 + NFKC 匹配 school/operator name |
| 3 | `scripts/apply_writer_plan.py` ~61 | Snapshot 非 journal rollback，靠 diff 推断 inserted_ids（现在 `rollback_apply.py` 已缓解但不完整）| 加 `rollback_journal` 表记录每笔 DML 前/后 JSON + batch_id |
| 4 | `scripts/spike_pref_aggregator.py` ~468 | Spike parser 无 row-count threshold，Hyogo 只 1-2 行也写 plan（silent failure）| 加 per-pref `expected_min_rows`；低于阈值整 batch 标 `review_required=true` 不进 apply |
| 5 | `scripts/apply_writer_plan.py` ~178 | Review queue 是 per-pref CSV（每次覆盖，无去重无 status 无 owner）| 新建 `review_queue` 表 (id, school_id, url, reason, status, assigned_to, created_at) |

---

## 4. Sprint 1 Codex 欠账（6 commits 未推）

Claude 可自推 4 项（LOW 风险 + 有明确 spec）：

| # | commit message | 位置 | 风险 |
|---|---------------|------|------|
| C2 | `fix: LEFT JOIN school_year_status preserves 215 active schools in sairoku export` | `src/eidp/excel/exporter.py:63` | LOW |
| C3 | `fix: classify httpx transient errors for retry` | `src/eidp/pipeline/ingest.py:504` | LOW |
| C4 | `fix: FISCAL_YEARS as function, not module-level constant` | `src/eidp/excel/exporter.py:20-28` | LOW |
| C6a | `fix: minimum score threshold for web_search URL acceptance` | `src/eidp/scraper/url_discovery.py:332` | LOW |

需 Codex 推（非一致性/供应链敏感，Claude 设 72h fallback 窗口）：

| # | commit message | 位置 | Why Codex |
|---|---------------|------|-----------|
| C5 | `security: enable PaddleOCR model source check by default` | `src/eidp/pdf/ocr.py:77` | 供应链安全，Codex 自己标的 |
| C6b | `fix: web_search source-side filter mirrors P0-6b downstream isolation` | `src/eidp/scraper/url_discovery.py:~483` | Codex 自己 P0-6b 后续 |

---

## 5. A-F 决策矩阵（Owner 要选）

| Path | 含义 | 对应动作 | 今天 ingested 增长 | DB 污染风险 | 回滚难度 |
|------|------|---------|-----------------|-----------|---------|
| **A** | 业务优先，全量 ingest | `eidp ingest-pdfs` 跑完 132 文档 | 24 → ~120-140 | 🔴 中（无 dept 回滚）| 🔴 高 |
| **B** | 先修所有 HIGH + Sprint 1 | 6-8 patch 后再 ingest | 0 | 🟢 零 | 🟢 纯代码 |
| **C** | 按 planner 6 phase 走 | MVP 2.5-6 周 | 0 | 🟢 零 | 🟢 纯代码 |
| **D** | 等 Codex `--xhigh` consult 结果 | 不动作 | 0 | 🟢 零 | 🟢 |
| **E** | 先盘清风险收益（已执行）| 出了决策矩阵（本文档）| 0 | 🟢 零 | 🟢 |
| **F** | 分批验证式 ingest | `eidp ingest-pdfs --batch-size 5` → 人工抽检 → 扩 | 24 → ~29 首批 | 🟢 可控 | 🟢 5 行 SQL |

---

## 6. Claude 推荐：**Path F（分批）**

### 为什么

1. Owner「越快越好，很急」≠「越鲁莽越好」
2. `rollback_apply.py` 只保护 `school_site`，**不能回滚 `document`/`department`/`department_yearly`**——全量 A 是无刹车
3. 分批用真实数据反向 verify Codex Finding #2（ownership_ok 不查内容）的担忧——5 条 ingested 后看 `department_yearly` 新行就知道 target 分类器可信不
4. 5 分钟抽检 + 5 分钟扩 20 + 10 分钟扩 132 = **30 分钟内全部 ingested**，比 A 慢不了多少但风险可控

### F 的具体 5 步（等 Owner 批准后执行）

```
Step 1 [5 min]: eidp ingest-pdfs --batch-size 5
Step 2 [10 min]: SELECT * FROM department_yearly WHERE created_at > NOW()-INTERVAL '5 min';
                 人工抽检 5 所学校的学科、在校生数、中退率
Step 3 [如果 5/5 正确]: eidp ingest-pdfs --batch-size 20
Step 4 [如果 20/20 正确]: eidp ingest-pdfs --batch-size 200 (all remaining)
Step 5 [报告]: 汇总 ingested 最终数 + dept_yearly 新增数 + OCR 成功率
```

### F 唯一的反对理由

30 分钟人工抽检时间。如果 Owner 嫌慢，可以降级到 A——但必须先写 `dept_rollback.py`（~30 分钟编码 + 测试，才有刹车）。

---

## 7. Sprint 1 补丁预案（与 F 并行，不依赖）

Claude 可主动推的 4 项（按难度升序）：

1. **C4 FISCAL_YEARS 函数化** — 20 行 diff，最简单
2. **C2 LEFT JOIN 修复** — 1 行 SQL + 1 个回归测试
3. **C3 httpx transient** — 加 `TRANSIENT_EXCEPTIONS` 常量 + 替换 except
4. **C6a score threshold** — 加 `MIN_ACCEPTABLE_SCORE=1.5` 常量 + 低分进 review_queue

预估总工时 1-2 hour，可与 F 交叉执行。

---

## 8. 仍需 Owner 答复的 5 个问题

1. **A/B/C/D/E/F 选哪个？**（Claude 推荐 F）
2. Codex 72h fallback 窗口 — Claude 是否可在 Codex 不推时推保守版 C5/C6b？
3. 1,600 条 web_search 污染清理的 mass DML 何时授权？（非紧急，可延后）
4. 担当者 review UI 演示档期（等 ingested ≥100 再做，F 半小时内可达）
5. 33 个未 seed 都道府県：WebSearch 批量探 vs 担当者手动补？

---

## 9. Venus 关键操作命令速查

```bash
# 查 DB 状态
ssh venus "docker exec eidp-postgres psql -U eidp -d eidp -t -c \"<SQL>\""

# 执行 ingest（需 Owner 授权 mass DML）
ssh venus "cd /home/junming/workspace/EIDP && \
  EIDP_DATABASE_URL='postgresql://eidp:eidp@127.0.0.1:5432/eidp' \
  .venv/bin/eidp ingest-pdfs --batch-size N"

# 回滚 Layer 0 apply
ssh venus "cd /home/junming/workspace/EIDP && \
  EIDP_DATABASE_URL='postgresql://eidp:eidp@127.0.0.1:5432/eidp' \
  .venv/bin/python scripts/rollback_apply.py --apply"

# 看 nohup discover-pdfs 日志
ssh venus "tail -f /tmp/eidp_discover_*.log"
```

---

## 10. 关键 output 文件（compact 后需重新定位）

```
output/pref-aggregator/
├── summary.json                    # 9 县 spike 汇总
├── {tokyo,kanagawa,...}.json       # 每县 records[] 审计
├── writer-plan-summary.json        # 207 actionable 汇总
├── {pref}-writer-plan.json         # 每县 Stage 2 writer 操作清单
├── url-verification-summary.json   # 167/207 HTTP verify 结果
├── url-verification-20260423_175940.json  # 逐 URL verify 详情
├── review-queue/{pref}-review.csv  # 40 条 suspect 人工队列
└── apply-report-20260423_181143.json   # apply 落地报告（166 rows committed）
```

---

## 11. 下次会话启动 prompt 建议

```
继续 EIDP 项目。读取 docs/plans/2026-04-23-next-step-decision.md 了解决策 context。
当前等待 Owner 选 A-F 之一。Claude 推荐 F。
HEAD=8de7fc6，ingested=24（未变）。Layer 0 URL 命中率 96%。
5 个 Codex HIGH + 6 个 Sprint 1 commit 未修。
```
