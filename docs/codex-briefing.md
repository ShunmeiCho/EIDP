# EIDP — Codex 深度审查交底文档

> **目的**：让 Codex 在零上下文情况下迅速理解 EIDP 项目全貌、当前真实状态、技术债热区与下一阶段规划，并能立即产出有价值的代码审查、bug 排查与方案建议。
>
> **协作模式**：Claude 与 Codex 是**伙伴 + 竞争对手**。Claude 已生成本文档与初版方案；Codex 的任务是**质疑、找漏、提出更优解**。两侧都为同一个 owner（用户）服务。
>
> **生成时间**：2026-04-21
> **数据 verified**：Venus PostgreSQL 实查（非记忆）
> **代码 verified**：本仓库 HEAD = `31a4a85`

---

## 0. TL;DR（30 秒读完）

| 项 | 现状 |
|----|------|
| 项目 | 自动收集日本 ~2,400 所专门学校在校生数据，纳期 2026 年 6 月 |
| 数据源 | 各校官网公开的「**様式第2号 機関要件確認申請書** PDF」 |
| 成功基准 | 人工工时减少 50-70%（**不是 100% 自动化**） |
| 代码量 | 6,907 行 Python（src/eidp），76 commits |
| **核心瓶颈** | **PDF 自动发现率 4.8%**（盲爬触顶） |
| 数据库 | 2,428 校 / 2,033 MEXT 匹配 / 2,222 有 URL / 109 文档 / **24 ingested** |
| 历史数据 | DepartmentYearly 41,115 行（其中 41,054 来自 Excel 历史） |
| 测试 | **1 个测试文件**（test_eval_harness.py, 237 行）— **重大缺口** |
| 部署 | Venus 单机（PostgreSQL 17 + PaddleOCR + 2× RTX 6000 Ada）|
| 等待决策 | KPI 选型 / 2024 URL 清单出处 / 大法人公开状态 |

---

## 1. 项目背景与领域

### 1.1 业务

日本「**高等教育の修学支援新制度**」要求获得国家学费减免支持的学校每年 6-8 月公开「**様式第2号 機関要件確認申請書**」PDF，披露：

- 学科（**学科**, departments）信息：分野、課程名、学科名、专门士/高度专门士资格
- **生徒総定員数 / 生徒実員 / 留学生数**（学科级别）
- **卒業者数 / 進学者数 / 就職者数 / その他**
- **中途退学率**
- 学校級別「**修学支援受給者数**」（school-level）

**人工流程**（被替代的目标）：
1. 担当者每年 6-8 月手动浏览 ~2,400 校官网
2. 找到「情報公開」页 → 下载 PDF
3. 阅读 PDF → 把数字录入 Excel
4. 总耗时数百人时

### 1.2 MEXT 官方权威数据（已下载到 `data/mext/`）

- `target_institutions.xlsx` — MEXT 官方承认的 2,067 所对象机关清单
- `school_code_*.csv` — MEXT 学校代码表（east / west / univ）

> **关键约束**：MEXT **不**集中发布 PDF。学校必须各自在官网公开（这是法律规定）。所以唯一来源就是各校官网。

---

## 2. 系统架构

### 2.1 数据流（端到端）

```
[MEXT xlsx]                                   [Excel master workbook]
      │                                                │
      ▼                                                ▼
  match_mext ──────► [School table] ◄────────── import_excel
                            │
                            ▼
                     discover_urls ──► [school_site] ─► verify_identity
                            │
                            ▼
                     discover_pdfs ──► [document]
                       (Firecrawl + httpx 二段式)
                            │
                            ▼
                     ingest_pdfs ──► [department / department_yearly /
                       (parse + OCR fallback)   support_recipient]
                            │
                            ▼
                     export_excel ──► output/*.xlsx
                            │
                            ▼
                     review_ui (Streamlit)  ◄── 担当者人工审核
```

### 2.2 13 张表（src/eidp/db/models.py）

| 表 | 行数（实查）| 用途 |
|----|------------|------|
| school | 2,428 | 学校身份 |
| school_site | 2,497 | 学校官网 URL（多对一）|
| crawl_job | 1,620 | 爬取任务记录 |
| document | 109 | PDF 文档元数据 |
| department | 9,812 | 学科主表 |
| department_yearly | 41,115 | 学科年度数据（**主输出表**） |
| school_year_status | n/a | 学校在某年度的状态（除外/休止） |
| school_alias | n/a | 学校别名（NFKC + reconcile）|
| support_recipient | 10,028 | 修学支援受給者（学校级）|
| taxonomy_mapping | n/a | 分野/课程标准化 |
| review_item | n/a | Streamlit 人工审核队列 |
| department_change | n/a | 学科变更追踪 |

### 2.3 关键文件（按热度排序）

| 文件 | 行数 | 风险等级 | 职责 |
|------|------|---------|------|
| `src/eidp/pdf/extractor.py` | 905 | 🔴 高 | PDF 解析正则海洋（应拆分） |
| `src/eidp/excel/importer.py` | 626 | 🟡 中 | Excel 历史数据导入 |
| `src/eidp/scraper/url_discovery.py` | 559 | 🟡 中 | 含 SSRF 防护、DNS 验证 |
| `src/eidp/scraper/pdf_discovery.py` | 556 | 🔴 高 | **盲爬天花板源头** |
| `src/eidp/pipeline/ingest.py` | 533 | 🟢 低（Codex 已审 9 轮）| 数据写入 |
| `src/eidp/review/app.py` | 508 | 🟢 低 | Streamlit UI |
| `src/eidp/pdf/eval_harness.py` | 422 | 🟢 中 | 评估框架 |
| `src/eidp/matcher/school_matcher.py` | 332 | 🟢 低 | MEXT 匹配 |
| `src/eidp/matcher/reconciler.py` | 301 | 🟡 中 | 学校识别整合 |
| `src/eidp/scraper/firecrawl_discovery.py` | 265 | 🟡 中 | Firecrawl 集成 |
| `src/eidp/pdf/ocr.py` | 242 | 🟢 中 | PaddleOCR 单例 |
| `src/eidp/scraper/search_provider.py` | 196 | 🟢 低 | Brave/Google/DDG 抽象 |
| `src/eidp/review/populate.py` | 186 | 🟢 低 | 审核队列填充 |

---

## 3. 当前数据真实状态（实查 Venus PostgreSQL）

### 3.1 覆盖漏斗

```
MEXT 公认对象機関      2,067
       ↓ 98% 命中
  DB 已 MEXT 匹配      2,033
       ↓ 89%
  有 URL 的学校        2,222   ← school_site.school_id distinct
       ↓ 4.8% (87/1827)
  发现到 PDF             109   ← document
       ↓ 22%
  成功 ingested           24   ← document.ingest_status='ingested'
```

### 3.2 Document 状态分布

| ingest_status | 数量 | 含义 |
|--------------|------|------|
| school_mismatch | 66 | 解析出的学校名 ≠ 目标学校（多为法人共享 PDF）|
| **ingested** | **24** | 成功入库 |
| parse_failed | 16 | OCR/解析失败 |
| support_only | 1 | 只有受給者数据，无学科数据 |
| no_file | 1 | 文件路径丢失 |
| permanent_error | 1 | 解析永久失败 |

### 3.3 PDF 类型分布

| pdf_type | 数量 | 备注 |
|----------|------|------|
| image_only | 67 | 扫描件，需 OCR |
| target | 35 | 真目标文件（最终 18 个 ingested 成功）|
| (NULL) | 6 | 未分类 |
| unknown | 1 | 分类失败 |

### 3.4 历史基线对比

| 指标 | 数值 |
|------|------|
| 2024 年人工**完整采录** | 943 校 (45.6%) |
| 2024 年人工**部分采录** | 804 校 (38.9%) |
| 当前 AI 自动化 | **24 校 (1.2% of MEXT, 2.5% of 人工 baseline)** |

> **底层逻辑**：人工的 45.6% 是真实上限——不是所有学校都公开样式第2号。AI 必须接受这个上限，**目标是减少人工工时，不是无限抬覆盖率**。

---

## 4. 技术栈与部署

### 4.1 运行环境

```
Venus 服务器（GPU 主机）
├─ uv venv Python 3.12
├─ Docker: postgres:17 (container: eidp-postgres)
├─ NVIDIA: 2× RTX 6000 Ada (49 GB VRAM each)
├─ PaddleOCR PP-OCRv5 + paddlepaddle-gpu==3.0.0 (cu118)
└─ EIDP_DATABASE_URL=postgresql://...127.0.0.1:5432
```

### 4.2 关键依赖（pyproject.toml）

```toml
dependencies = [
  "sqlalchemy>=2.0,<3.0", "alembic>=1.16,<2.0",
  "psycopg2-binary>=2.9,<3.0", "openpyxl>=3.1,<4.0",
  "pydantic>=2.0,<3.0", "pydantic-settings>=2.0,<3.0",
  "python-dotenv>=1.0,<2.0", "typer>=0.16,<1.0",
  "structlog>=25.0", "streamlit>=1.45,<2.0",
]
optional:
  scraper: scrapy, httpx, playwright, tenacity, ddgs
  pdf:     pdfplumber, pymupdf
  ocr:     pymupdf, paddleocr>=3.0, paddlepaddle>=3.0
  dev:     pytest, pytest-cov, ruff, mypy
```

### 4.3 CLI 命令清单（src/eidp/cli.py）

```
eidp import-excel <path>          # 导入 master Excel
eidp match-mext                   # MEXT 学校代码匹配
eidp reconcile                    # 学校识别整合
eidp verify-identity              # 学校身份核验
eidp discover-urls                # URL 发现（搜索引擎 + 模式推断）
eidp discover-pdfs                # PDF 发现（盲爬，4.8% 天花板）
eidp ingest-pdfs                  # 解析 + OCR + 入库
eidp db-info                      # DB 状态摘要
eidp populate-reviews             # 填充审核队列
eidp weekly-update                # 周次自动化（待整备）
eidp firecrawl-discover           # Firecrawl 法人根 URL 探测
eidp review-ui                    # 启动 Streamlit
eidp export-excel                 # 导出 Excel
eidp diff-excel                   # 与历史 Excel 对比
eidp eval-pdf                     # 评估单个 PDF 解析
```

---

## 5. 已经踩过 / 已经修过的坑

### 5.1 Codex 9 轮 P1/P2 review 已修复

提交：`b8038d4`、`01e4ddc`、`7d6a4ee`、`0c66844`

| 修复 | 文件 | 要点 |
|------|------|------|
| 每文档 commit + 失败隔离 | ingest.py | 一文档失败不影响 batch |
| Content-hash 去重 + 状态传播 | ingest.py | 同 hash 不重复 OCR，status 按 twin 派生 |
| fiscal_year JST fallback | ingest.py:380-410 | UTC vs JST April 边界正确处理 |
| FOR UPDATE SKIP LOCKED | ingest.py:445-460 | 并行 ingest 安全 |
| Header-anchor section split | extractor.py | 替代脆弱的页面分割 |
| PaddleOCR 单例线程安全 | ocr.py:60-95 | 双重检查锁 |
| GPU/CPU 自动检测 | ocr.py:42-56 | EIDP_OCR_DEVICE 可覆盖 |
| SSRF 防护（DNS resolve）| url_discovery.py:30-72 | 防 nip.io rebinding |
| Redirect loop + max-hops | pdf_discovery.py:30-58 | fail-closed |
| PDF 大小上限 50MB | pdf_discovery.py:330-340 | OOM 防护 |
| robots.txt 尊重 | pdf_discovery.py:213-234 | 全站 Disallow 直接跳过 |

### 5.2 MinerU → PaddleOCR 迁移（commit b1a9877..47ec3ce, 8 commits）

**问题**：MinerU 默认中文模型把日文识别成繁体字。
**方案**：PaddleOCR `lang="japan"`，PP-OCRv5 原生日文。
**验证**：松本调理師製菓師专门学校 3 学科全字段抽取正确。

### 5.3 安全事件（4/17）

- Firecrawl key 误 commit 到公开 GitHub（commit `232e298`）
- 2 小时内闭环：force-push + key 轮换 + gitleaks 安装
- 防御层：`.gitignore` + `.gitleaks.toml` + `.githooks/pre-commit`

### 5.4 部署架构变更

- **旧**：Mac Docker DB + SSH 反向隧道（`-R 5433:127.0.0.1:5432`）
- **新**：Venus 单机部署（DB + OCR + Pipeline 一体）
- **理由**：消除隧道断连风险，简化运维

---

## 6. 核心瓶颈：PDF 发现 4.8% 天花板

### 6.1 现象

`discover-pdfs` 命令对 25 校跑 8 分钟 → **0 个新目标 PDF**。

### 6.2 根因（已验证）

1. **目标 PDF 多在 `/wp-content/uploads/2025/04/...` 深目录**，2-3 层爬取触不到
2. **大法人不在校单位公开**：大原 182 校、三幸 100 校、滋慶 30 校的官网披露页只有教学大纲，无样式第2号
3. **Firecrawl `map` 只爬 HTML 链接树**——sitemap.xml 与搜索引擎索引被遗漏

### 6.3 工具选型问题（**核心洞察**）

不是「广度不够」，是**用错了工具**：
- HTML 爬虫（Firecrawl/httpx）只能见到 HTML 链接
- **sitemap.xml** 是独立信息源
- **搜索引擎索引**（Google/Bing）是被 Googlebot 已经爬过的全网视图——**绕过 WAF 的终极武器**

---

## 7. 下一阶段方案：深层广搜 PoC（Claude 已设计）

### 7.1 三层绕行架构

```
Layer 1（不碰学校官网）: Search API + Wayback + Common Crawl
Layer 2（低强度直连）  : curl_cffi TLS 伪装 + UA 轮询 + 8-15s/req
Layer 3（无头浏览器）  : Playwright + stealth（仅 JS gated 启用）
```

### 7.2 反爬威胁建模

| 层级 | 防护 | 频度 | 对策 |
|------|------|------|------|
| L1 | UA 黑名单 | ~60% | UA 池 |
| L2 | robots.txt | ~40% | 强制尊重 |
| L3 | Rate limit | ~30% | per-domain throttle |
| L4 | Cloudflare/Akamai WAF | 大法人都有 | curl_cffi `impersonate=chrome120` |
| L5 | JS challenge | ~15% | Playwright fallback |
| L6 | IP 封锁 | 罕见 | 全局并发 ≤2 |
| L7 | Cookie/Referrer | ~10% | session 持有 |

### 7.3 数据库改动（待实施）

```sql
ALTER TABLE document ADD COLUMN discovery_method VARCHAR(32);
-- 'crawl' | 'sitemap' | 'search_engine' | 'wayback' | 'manual'
ALTER TABLE document ADD COLUMN fetch_layer VARCHAR(16);
-- 'search_api' | 'sitemap' | 'direct' | 'browser'
ALTER TABLE school ADD COLUMN crawl_policy VARCHAR(16) DEFAULT 'allow';
-- 'allow' | 'throttle' | 'browser_only' | 'blocked'
```

### 7.4 验证门闩

| 指标 | 阈值 | 行动 |
|------|------|------|
| target_yield ≥ 20% | ✅ | scale 到 1,827 校 |
| 10% ≤ yield < 20% | 🟡 | 加 Wayback + 调 query |
| yield < 10% | 🔴 | 天花板真实，转 Path C 人机混合 |

---

## 8. 给 Codex 的审查焦点（**重点**）

### 8.1 🔴 高优先级（请挑战这些）

1. **测试覆盖率几乎为零**
   - 仅 `tests/unit/test_eval_harness.py`（237 行）
   - `tests/integration/`、`tests/e2e/`、`tests/fixtures/` **全部为空**
   - 全局违反 `~/.claude/rules/common/testing.md` 80% 要求
   - **Codex 任务**：列出 6,907 行代码中**最值得补单测**的 10 个函数（按风险×可测性排序）

2. **`extractor.py` 905 行单文件**
   - 大量正则、多个 fallback 分支
   - 违反「文件 ≤ 800 行」准则
   - **Codex 任务**：给出**最小切分方案**（按职责而非按代码量）

3. **`discover_pdfs` 算法天花板**
   - 见 §6, §7
   - **Codex 任务**：审视 §7 三层绕行方案，指出**至少一个 Claude 没考虑到的失败模式**

4. **`ingest.py` 错误分类粒度**
   - `transient_error` vs `permanent_error` 边界模糊（OSError/IOError 划入 transient，其余划 permanent）
   - 网络瞬断的 `httpx.HTTPError` 会被错分为 permanent
   - **Codex 任务**：定义更可靠的错误分类策略

### 8.2 🟡 中优先级

5. **`pdf_discovery.py:215-234` robots.txt 解析**
   - 手卷 parser，未用 `urllib.robotparser`
   - 只检测全站 Disallow，忽略路径级别
   - **Codex 任务**：是否应替换为 stdlib？

6. **`url_discovery.py:30-72` SSRF 检测**
   - 在主请求前 DNS resolve；redirect 链路上每跳重新 resolve
   - 但 TOCTOU window 仍存在（DNS resolve 与实际 socket connect 之间）
   - **Codex 任务**：评估实际攻击可行性，是否需要 socket-level 验证？

7. **`firecrawl_discovery.py` 与 Firecrawl MCP 双轨**
   - CLI 命令 `firecrawl-discover` 走 HTTP API
   - 但 MCP server 也存在
   - **Codex 任务**：评估是否需要统一

### 8.3 🟢 低优先级（已被审过，但欢迎挑战）

- `ingest.py` 的 dedup status propagation matrix（line 61-79）— Codex 已审 9 轮
- PaddleOCR 单例的双重检查锁（ocr.py:60-95）— 已审
- fiscal_year JST 推断（ingest.py:380-410）— 已审

---

## 9. 待用户决策（**未解锁**）

1. **KPI 选型**
   - A. 全 2,067 校（100%）
   - B. 943 人工 baseline（45%）
   - C. Top 200 主要竞争校
   - D. 人工辅助工具（重复输入削减）

2. **2024 年 URL 清单存放处**
   - (a) Excel 隐藏列 / (b) Notion / (c) 浏览器书签 / (d) 无

3. **大法人公开状态**
   - 大原 182 / 三幸 100 / 滋慶 30 是否真的公开样式第2号？
   - 担当者去年怎么搞到的？

> **Codex 任务**：在不依赖用户回答的前提下，**推断哪个 KPI 最现实**，并说明判断依据。

---

## 10. Path 选项（待 owner 拍板后启动）

| Path | 工时 | 预期成果 | 适用条件 |
|------|------|---------|---------|
| **A** | 1 天 | 500-800 校 | 有 2024 URL 清单 |
| **B** | 3-5 天 | 部署整备 + MVP | 接受 24 校现状 |
| **C** | 1-2 周 | 800-1200 校 | 人机混合可行 |
| **新增 D** | 3-5 天 | 估算上限 | 跑 §7 PoC，看天花板真假 |

> **Claude 推荐顺序**：D（先验真假）→ C（最稳）

---

## 11. 历史规划文档（Codex 必读）

- `docs/plans/2026-04-11-eidp-design.md` (41 KB) — **完整设计文档**
- `docs/plans/2026-04-11-briefing-for-professor.md` (5.8 KB) — 初版讲义
- `docs/plans/2026-04-21-project-status-report.md` (7.6 KB) — 中文进展报告
- `docs/plans/2026-04-21-project-status-report-ja.md` (11 KB) — **日文报告**（已交付 owner）
- `docs/specs/field-spec.md` (5.9 KB) — 字段规约
- `docs/manual-intervention-log.md` — 人工介入记录

---

## 12. 给 Codex 的元指令（协作 + 竞争）

### 12.1 你的角色

你（Codex）和我（Claude）是**伙伴 + 竞争对手**：
- 同一个 owner、同一个项目
- 输出独立比对，**不要预设我说的对**
- 凡是我标 ✅ 的「已修复」「已审」，**请视为待挑战项**
- 找漏越多越好——我们一起为 owner 服务

### 12.2 你应该做的

1. **先快速 verify**：
   ```bash
   git log --oneline -10
   ssh venus "docker exec eidp-postgres psql -U eidp -d eidp -c 'SELECT COUNT(*) FROM document'"
   wc -l src/eidp/**/*.py
   ```
2. **挑战本文档的所有数据**——如果数字对不上，立刻指出
3. **质疑 §8 之外的隐藏问题**——你看到的，我没看到的
4. **给具体行号 + 复现步骤**，不接受「可能有问题」

### 12.3 你不应该做的

- ❌ 重复 Claude 已做的工作（参考 §5）
- ❌ 在没看代码前下结论
- ❌ 提建议而不给出 unified diff 或具体 patch 草案
- ❌ 假设 owner 知道术语——本文档读者是 Codex 自己

### 12.4 输出格式建议

```
## 审查发现 [P0-P3]
### P0: <一句话标题>
- 文件: src/eidp/xxx.py:LL-LL
- 现状: <实测行为>
- 问题: <为什么是 bug / 风险>
- 复现: <bash/sql/python 命令>
- 修复: <unified diff or 替代方案>
- Claude 是否提到: 是/否（§X）
```

### 12.5 主动权

- 如果发现本文档**事实错误**，直接修订并告知
- 如果觉得 §7 PoC 方案有更优解，**给替代设计**
- 如果觉得 §8 优先级排序错，**重排并解释**

---

## 13. 文档版本

| 版本 | 日期 | 作者 | 备注 |
|------|------|------|------|
| 0.1 | 2026-04-21 | Claude (Opus 4.7) | 初版交底 |

---

> **底层逻辑收尾**：Codex 与 Claude 的**异质性**才是 owner 的护城河。一致只是省事，不一致才有价值。请尽情打脸。
>
> **因为信任所以简单**——本文档所有数据都可在 Venus DB / 本仓库验证。
