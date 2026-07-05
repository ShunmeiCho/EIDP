# Rung 1a — 大原札幌校 FY2025 master-diff 结果

**Result: `PASS_WITH_CAPACITY_RECONCILIATION`**

单个人工确认的大原官方 PDF → 表格级抽取 → actual `MasterMetricRow`(pin 身份,非 master)→ 对 `data/master.xlsx`(只读)diff。管线端到端打穿,集成测试 `tests/integration/test_ohara_rung1a_master_diff.py` 在真实数据上通过。

## Pin(authority = URL / human_confirmed_official_pdf）

| 字段 | 值 |
|---|---|
| school_key(法人名) | 大原学園 |
| campus_key(学校名) | 大原簿記情報専門学校札幌校 |
| fiscal_year | 2025 |
| source | `pdf/2025-1-01-01-5.pdf`(確認申請書,含全 6 学科表) |
| authority_basis | `human_confirmed_official_pdf`(URL 定年度+文件;PDF 学校名头佐证;master 仅作 expected-output) |

master.xlsx **从不用于反推身份**(避免 fake success)。

## Hard gate(通过)

| 指标 | 结果 |
|---|---|
| dept 覆盖 | **6/6**(单份 part-5 含全学科) |
| ambiguous_key | **0** |
| missing_actual / unexpected_actual | **0 / 0** |
| **在籍者数(在校生数)** | **6/6 exact_match** |
| **留学生数** | **6/6 exact_match** |

所有 actual 值带 `page/table/row/col` evidence。

## Reconciliation(不阻塞,待 owner)

`収容定員`(master)vs `生徒総定員数`(PDF 確認申請書)在 3 个正在改定员的学科上背离,**抽取器读的都是对的**(带 evidence),双向差异排除任何缩放 bug:

| 学科 | master 収容定員 | PDF 生徒総定員数 | 说明 |
|---|---|---|---|
| 文化教養\|ビジネスコミュニケーション | 80 | 40 | 募集停止(在籍0);認可定员未改,申請已减 |
| 商業実務\|ビジネスキャリア2年制 | 140 | 120 | 入学定员进一步下调,master 滞后 |
| 商業実務\|会計システム4年制 | 90 | 100 | 4年制 ramp,官方已达 100 |

处理:进 capacity reconciliation report(`classification=capacity_cross_source_delta`, `operator_decision=needs_owner_decision`);**不自动覆盖 master、不进最终 Excel authoritative output**。

## 待 owner 的并行决策(非阻塞)

目标 Excel「競合校の在校生数」核心是在校生数(已 diff=0)。定員列口径请 owner 确认:

- **A.** 沿用 master 既有 `収容定員`,PDF 定員仅作参考
- **B.** 采用 PDF `生徒/学生総定員数` 更新定員
- **C.** master 収容定員 与 PDF 生徒総定員数 分两列保留
- **D.** 競合校在校生数 Excel 不使用定員,差异只做对账记录

推荐默认 **D 或 A**(owner 未定前不让 PDF 定员覆盖 master)。

## 下一步

Rung 1b(3 校):在籍+留学生 diff=0 为硬门,capacity 继续 reconciliation;并行发上面的 owner 定員口径问题。
