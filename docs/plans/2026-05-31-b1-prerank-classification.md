# B1 — 有界 pre-rank 分类 pass（v2.2 计划）

Status: 计划就绪（决策已锁定），待 TDD 实现
Goals: G1, G3（次要影响 G5 观测 / G12 成本）
Target file: `src/eidp/scraper/pdf_discovery.py`（+ `tests/unit/test_pdf_discovery.py`）
Base: main @ 2c6c4fb

> 本文档由 Understand→Plan→Critique workflow（`wf_18c09970-a99`）+ 三轮外部对抗审查收敛而成。
> v2.1 相对 v2：**纠正 >5MB PDF 的双取表述**（§3.1 / §6 风险 1）。
> v2.2 相对 v2.1：**cap 语义从「成功分类数」改为「网络探测尝试数」**（§3.2），新增 attempt-cap 测试（§5），修正 no-sleep / large-pdf 两条测试的造数方式（§5）。

---

## 1. 问题（已用真实代码行号坐实）

PR #3（87c20bd）给候选排序加了「以 PDF 正文检出的学校名为首要信号」的机制，但它在生产里**空转**——信号在排序时尚不存在。

单个站点在 `run_pdf_discovery`（def `3553`）的 per-site 循环里是严格线性执行：

| 阶段 | 行号 | 说明 |
|---|---|---|
| 打分 + 按 score 排序 | 3786–3789 | `_score_candidate` |
| 构建 `school_name` / `school_names`(+aliases) | 3790–3793 | |
| `viable = [score>=0 or has_target_hint]` | 3794 | |
| 锚-mismatch 过滤（`_candidate_mentions_different_school`，锚/URL 信号） | 3795–3812 | body 此刻未设 |
| **候选排序 `_prioritize_viable_candidates`** | **3813** | 读 `detected_school_name` |
| 下载循环 `for candidate in viable:` | 3871 | |
| `download_pdf(...)` → 设 `detected_school_name` | 3933/3942 → 3397 | 排序**之后** |

排序在 `3813` 执行时，所有候选 `detected_school_name == ""`（默认空串）。`_candidate_school_match_rank`（`1267`，行 `1288` 门控 body 非空且 ≥4 字符）因此塌缩回旧的 link-text 顺序（返回 1/2），正文分支（0/3）**永不触发**。→ dense 多品牌披露页（Sanko/O-Hara 风格）上 half-A 学校被错配到错误 PDF。

`_prioritize_viable_candidates`（`1297`）排序键：
- priority 组（`tier < 2`）：`(tier, school_rank, year_rank, -score, index)` — `school_rank` 是 **tier 之后第 2 键**
- general 组（`tier >= 2`）：`(school_rank, -score, index)` — `school_rank` 是**第 1 键**，封顶 `MAX_GENERAL_CANDIDATE_SCAN`

→ body rank 只能在**同 tier 内**重排（tier 天花板，见 §6 风险 2）。

---

## 2. 修法

在排序前（`3812↔3813`）插入一个**有界**的 pre-rank pass：对 dense/ambiguous 页的 priority 候选，先抓正文、跑学校名分类、写入 `detected_school_name`，让既有排序函数读到活信号。排序函数 `_prioritize_viable_candidates` **不改**。

**插入点 = `run_pdf_discovery`（3553）内 3812 与 3813 之间。**（注：`discover_pdfs_for_site`(3074–3321) 只收集候选、看不到 `viable`，不是 seam。）

---

## 3. 设计

### 3.1 新 helper（放 `_extract_pdf_sample_school_name` 附近，~1354 后）

```python
def _classify_candidate_body_for_rank(
    client: HttpGetClient, candidate: PdfCandidate, *, sleep_seconds: float
) -> str:
    """Pre-rank ONLY. Sets candidate.detected_school_name (and nothing else).

    Returns one of:
      "classified"        body classified, response cacheable (<=5MB)
      "classified_large"  body classified, but >5MB => NOT cached => download_pdf may GET again
      "skipped"           not a usable PDF / already classified
      "failed"            fetch or parse error (graceful: leaves body empty)

    Read-only w.r.t. DB. Does NOT set detected_fiscal_year / pdf_type / candidate.pdf_url.
    """
    if candidate.detected_school_name:
        return "skipped"                                  # idempotent
    if not _is_safe_url(candidate.pdf_url):
        return "skipped"
    attempt_urls = _download_attempt_urls(candidate.pdf_url)   # SAME canonical sequence as download_pdf
    if not attempt_urls:
        return "skipped"
    download_url = attempt_urls[0]                         # the URL download_pdf tries first
    if not _is_safe_url(download_url):
        return "skipped"
    _sleep_before_uncached_get(client, download_url, seconds=sleep_seconds)   # no-op on cache hit
    try:
        resp = _safe_get(client, download_url)            # no kwargs -> cacheable, key == download_pdf's
        resp.raise_for_status()
    except (httpx.HTTPError, httpx.InvalidURL):
        return "failed"
    content = resp.content                                # plain GET: body already fully downloaded here
    if len(content) < 1000 or content[:5] != b"%PDF-":
        return "skipped"
    try:
        sample_text = _extract_pdf_sample_text(content)
    except Exception as e:
        log.exception("prerank_classify_failed", error=str(e), error_type=type(e).__name__)
        return "failed"
    candidate.detected_school_name = _extract_pdf_sample_school_name(sample_text)   # ONLY this field
    return "classified_large" if len(content) > RUN_SCOPED_PDF_CACHE_MAX_BYTES else "classified"
```

要点：
- **C2 cache parity**：用 `_download_attempt_urls(...)[0]`、无 kwargs。wrapper URL 的真实直链由 `_pdf_url_from_query_value` 解析为 `[0]`，正是 `download_pdf` 首先 GET 的 URL → ≤5MB 时第二次为 cache 命中。
- **H4**：只写 `detected_school_name`。不碰 `detected_fiscal_year`/`pdf_type`/`year_evidence`/`candidate.pdf_url`（后者由 `download_pdf` 在 3386 设置，保持其 attempt 逻辑完整）。
- **G12 大 PDF（v2.1 修正）**：`_safe_get` 是普通 GET（非 HEAD/streaming），拿到 `resp.content` 时 body 已全部下载完。>5MB 时 cache 不存（`_should_cache_response` 上限 `RUN_SCOPED_PDF_CACHE_MAX_BYTES`），故 `download_pdf` 之后**可能再 GET 一次**。我们仍用已下载的 body 完成分类（已付出的带宽换取排序价值），但返回 `classified_large` 让上层统计。**不声称避免双取**；不为此做 HEAD/streaming 改造（当前无此 client 协议）。

### 3.2 触发 + 有界 pass（插在 3812 与 3813 之间）

```python
# B1: bounded pre-rank body classification — only on dense/ambiguous pages
if school_names:
    priority = [c for c in viable if _candidate_download_tier(c, target_year=target_year) < 2]
    if len(priority) >= 2:                       # real target-like competition, NOT any multi-candidate
        probed = 0
        for candidate in priority:
            if candidate.detected_school_name:
                continue                         # already classified: no GET, does NOT consume a probe
            if probed >= MAX_PRERANK_CLASSIFY:   # CAP NETWORK ATTEMPTS (probes), not successes
                break
            probed += 1                          # count the attempt BEFORE the call, regardless of outcome
            status = _classify_candidate_body_for_rank(client, candidate, sleep_seconds=rate_limit)
            if status in ("classified", "classified_large"):
                stats["prerank_classified"] += 1
                if status == "classified_large":
                    stats["prerank_uncached_large"] += 1
            elif status == "skipped":
                stats["prerank_skipped"] += 1
            else:  # "failed"
                stats["prerank_failed"] += 1
```

> **为何 probe-cap 而非 classified-cap（v2.2）**：`classified` 只计成功分类，若 dense 页前若干 priority 候选 404 / 非 PDF / 解析失败，classified-cap 不会 break，循环会持续 GET → 击穿 G12。probe-cap 把上界钉在「网络尝试次数 ≤ `MAX_PRERANK_CLASSIFY`」。已分类候选 `continue` 不消耗 probe（无 GET）；其余每个候选无论结果都消耗一次 probe（保守，偏向更少尝试，对 G12 安全）。

### 3.3 常量 + 计数器

- `MAX_PRERANK_CLASSIFY = 3`（与 `MAX_CANDIDATE_DOWNLOAD_ATTEMPTS` / `MAX_GENERAL_CANDIDATE_SCAN` 并列，G8 可配置）。
- stats 初始化（在 `candidate_school_mismatch` 初始化附近，~3600）新增：
  `prerank_classified`, `prerank_skipped`, `prerank_failed`, `prerank_uncached_large`（均初始 0）。

---

## 4. 决策（已锁定）

| # | 决策 | 选定 |
|---|---|---|
| 1 | 触发语义 | `school_names` 非空 **且** priority(tier<2) 候选 **≥2**。接受边界：单候选且 body 是 sibling 时不触发，仍由 post-download `pdf_school_mismatch` 安全网兜底（正确 tradeoff）。 |
| 2 | `MAX_PRERANK_CLASSIFY` | **3**（第一版目标是证明 dense 错配下降，非最大覆盖；后续按 stats 决定是否升 5）。 |
| 3 | 限流秒数 | 复用 `rate_limit`（不硬编码 1s）；测试覆盖 cache hit 不 sleep。 |

---

## 5. TDD 测试矩阵（RED 先行）

| 测试 | 守护 | 断言 |
|---|---|---|
| `test_prerank_promotes_target_before_download` | 核心 bug | 2 个同 tier、等分、平局/通用锚、sibling-first 输入；fake body(sibling/target)；`download_calls[0] == target`（当前 main 红） |
| `test_prerank_cache_parity_small_wrapper_pdf` | **C2** | candidate.pdf_url 为 query-wrapper、解析后 ≤5MB；assert 该 resolved URL 全程**仅 1 次**网络 GET（pre-rank 写、download 命中） |
| `test_prerank_large_pdf_may_double_fetch_and_is_counted` | **G12** | monkeypatch `_extract_pdf_sample_text` + 把 `RUN_SCOPED_PDF_CACHE_MAX_BYTES` 调到极小值，令小 fake PDF 走 large 分支（**勿**造真 >5MB 喂 pdfplumber，慢且脆）；assert 仍分类、`stats["prerank_uncached_large"] >= 1`；**不**断言单次 GET |
| `test_prerank_does_not_set_fiscal_year` | **H4** | pre-rank 后 `candidate.detected_fiscal_year is None`（FY 仍由 download_pdf 的 strict 路径独占） |
| `test_prerank_skipped_for_single_priority_candidate` | **H3/G12** | 普通单 priority 候选校 → `stats["prerank_classified"] == 0`，零额外 GET |
| `test_prerank_caps_attempts_when_candidates_skip_or_fail` | **G12 attempt-cap** | dense 页 ≥4 个 priority 候选、前若干 404/非PDF/解析失败；assert 网络 GET 次数 ≤ `MAX_PRERANK_CLASSIFY`（cap 计的是探测尝试数，非成功数） |
| `test_pdf_school_mismatch_safety_net_preserved` | H3-net | 单候选 body≠target → 仍走 post-download `pdf_school_mismatch` 拒绝（保住安全网覆盖；必要时单独建测试） |
| `test_prerank_no_sleep_on_cache_hit` | 决策 3 | 用**第二个 candidate、同 resolved URL、body 为空**（**勿**复用同一 candidate——helper 会因 `detected_school_name` 已存在直接返回 skipped，不发 GET）；assert 该 GET 命中 cache 且不触发 sleep |
| 夹具前置断言 | NFKC | `_candidate_body_matches_target(target, school_names) is True`（归一化 sanity，避免测试因 NFKC 失配而红/绿错因） |
| 夹具前置断言 | tier 天花板 | 两候选 `_candidate_download_tier(...) < 2` 且同值 |
| 更新既有断言 | 回归 | `test_pdf_discovery.py` 现有顺序/计数/证据断言（1033 顺序 + 1035 计数 + 1031/1039/1040 mismatch 证据）按重排后**逐条**修正或迁移；PR body 显式说明这是 B1 有意翻转 |

**验证序列**（Mac-side）：
```bash
EIDP_DATABASE_URL='sqlite:///./data/test_prerank.sqlite3' uv run pytest tests/unit/test_pdf_discovery.py::test_prerank_promotes_target_before_download -q   # RED→GREEN
EIDP_DATABASE_URL='sqlite:///./data/test_prerank.sqlite3' uv run pytest tests/unit/test_pdf_discovery.py tests/unit/test_candidate_school_selection.py -q
uv run pytest tests/unit/test_cli_write_lock_contract.py -q   # AST 门禁仍绿，无新写助手条目
uv run mypy src
uv run ruff check src scripts/build_windows_zip.py scripts/run_non_windows_release_gates.py
EIDP_DATABASE_URL='sqlite:///./data/test_prerank.sqlite3' uv run pytest -q
uv run bandit -r src -ll
```

---

## 6. 契约安全 & 风险

### 契约安全（精确表述）
- **B1 新增代码（helper + pass）无任何 DB Session 写**：只改内存 `PdfCandidate.detected_school_name`（dataclass 字段，非 DB 行）。无 revision++、不碰红线文件、不读写 `EIDP_TARGET_FISCAL_YEAR`、无原始 SQL。
- 宿主 `run_pdf_discovery` **照旧**写 CrawlJob/Document——B1 既不增也不减这些写。**不**把整个发现流程描述为只读。
- 因 B1 代码只读 w.r.t. DB → 无需 `_require_app_lock`/`acquire_lock`，`WRITE_HELPER_CALLS` AST 门禁（`test_cli_write_lock_contract.py`）无需新增条目，G10 `test_*_returns_lock_busy_without_writing` 不适用。
- `_safe_get` 保留 SSRF `_is_safe_url` 检查（每跳）；正文文本仅喂既有 `_extract_pdf_sample_*`（NFKC+regex，已 vetted），无新 prompt/markup 面。

### 风险
1. **>5MB 双取（v2.1 修正后的准确表述）**：plain GET 无法预知大小，>5MB 第一次下载已发生且不缓存，`download_pdf` 可能再下一次。**不规避、统计并接受**：由 `MAX_PRERANK_CLASSIFY=3` 封顶、以 `prerank_uncached_large` 计量。
2. **tier 天花板**：body rank 仅在同 tier 内重排；若锚/URL 把 sibling 放入更强 tier、target 入更弱 tier，body 无法跨 tier 提升 target。RED 夹具须把两候选钉在同一 tier 并断言。
3. **top-N 截断**：target 若排在 score 序的 N 名之外则不被分类、保留旧 rank。夹具须把 target 置于前 N。
4. **G12 wall-clock**：dense 页最坏每校 3×(GET+pdfplumber 解析 pages[:5]) + 最多 3×`rate_limit` sleep（首取非命中）。上界由 §3.2 的 **probe-cap**（网络尝试 ≤ `MAX_PRERANK_CLASSIFY`）保证，**不随 dense 页候选数膨胀**。实现后仍应在代表性 batch 上 spot-check 周次 wall-clock(<30min) 与带宽(<2GB)，再认 G12 GREEN。
5. **既有安全网覆盖**：target 先下载成功可能短路下载循环 → sibling 不再下载 → 原 `pdf_school_mismatch` 证据路径在该夹具失去覆盖；须用专门单候选测试保住其覆盖。

---

## 7. 实现顺序（Mac-side TDD）

1. 写 §5 全部测试（RED）→ 跑、确认核心测试红、回归绿。
2. 加常量 + stats 计数器。
3. 加 `_classify_candidate_body_for_rank` helper。
4. 插入 §3.2 有界 pass。
5. 逐条修正既有失效断言。
6. 跑 §5 验证序列全绿 → refactor → 重建/部署按 EIDP Windows 流程（本计划仅限 Mac-side 业务逻辑层）。
