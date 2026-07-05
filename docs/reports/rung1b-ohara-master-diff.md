# Rung 1b — 大原 3 校 FY2025 master-diff 结果

**Result: `RUNG_1B_PASS_WITH_RECONCILIATION`**（对抗审查 6 透镜全 `refuted` 确认,0 fake-success;见文末)

3 个风险分型的人工确认大原官方 PDF → 表格级抽取 → actual `MasterMetricRow`(pin 身份,非 master)→ 学科身份对齐 → 对 `data/master.xlsx`(只读)diff。集成测试 `tests/integration/test_ohara_rung1b_master_diff.py` 在真实数据上 4/4 通过。

master.xlsx **从不用于反推 PDF 身份或数值**(避免 fake success)。

## 3 校选择理由（确定性风险准则,非按结果预筛）

| code | campus_key | risk_flags | 选择理由 |
|---|---|---|---|
| 03 | 大原医療福祉専門学校 | `obvious_match` | 名称独特,无兄弟碰撞;基线干净路径 |
| 08 | 大原ビジネス公務員専門学校**山形校** | `sibling_school_risk`, `field_label_variation` | 与 06 盛岡校同基名(pin 判别);兼测 コース 后缀 + 分野 交叉分类 |
| 16 | 東京アニメーター学院専門学校 | `field_label_variation` | 分野「文化教養」无中点(测中点折叠);留学生 2/1/1 非零(实测 intl 门);master 含 2 空白 legacy 学科 |

06 盛岡校(`sibling_school_risk`)作为 08 的兄弟对照 pair-mate 一并 pin,用于**从另一侧证明 pin 不串校**,并记录为 master 数据发现——不计入 3 校门禁。

## 每校 authority_basis（URL 权威 / human_confirmed_official_pdf）

四校 `source_type` 均为 `human_confirmed_official_pdf`,证据链一致:
- `source_page` = `https://www.o-hara.ac.jp/about/joho/`（大原公示索引页)
- `pdf_url` = 该页解析出的绝对 URL(URL 选定文件)
- `url_year_hint` = `2025`（年度由 URL/路径编码,权威)
- `pdf_text_school_hint` = 从確認申請書 学校名 头读出(仅身份佐证);兄弟校 06/08 由此头消歧
- master 不作身份来源(不出现在 `authority_basis`)

## Hard gate（3 校通过：在籍 + 留学生 diff=0）

| code | dept 覆盖 | ambiguous | missing / unexpected | 在籍 | 留学生 | gate |
|---|---|---|---|---|---|---|
| 03 | 4/4 | 0 | 0 / 0 | exact | exact | `pass_with_reconciliation` |
| 08 | 4/4 | 0 | 0 / 0 | exact | exact | `pass_with_reconciliation` |
| 16 | 3/3 | 0 | 0 / 0 | exact | exact | `pass` |

所有 actual 值带 `page/table/row/col` evidence。06 盛岡校 = `fail`(见「master 发现」)。

## diff 分类表（对齐后,真实数据）

| code | exact_match | value_mismatch | missing | unexpected | ambiguous |
|---|---|---|---|---|---|
| 03 | 10 | 2 (capacity) | 0 | 0 | 0 |
| 08 | 11 | 1 (capacity) | 0 | 0 | 0 |
| 16 | 9 | 0 | 0 | 0 | 0 |
| 06 | 11 | 1 (**enrollment**) | 0 | 0 | 0 |

## Reconciliation（非阻塞,待 owner）

**Capacity(収容定員 vs 生徒総定員数,承 Rung 1a 口径):**
- 03: `医療事務2年制` 160→80、`介護福祉` 60→40
- 08: `税理士・ビジネス学科(ビジネス)` master 空白 → PDF 80

**分野 taxonomy(本 Rung 新增,承 owner 决策「学科键优先 + 分野转对账」):**
- 08: `公務員学科1年制`、`公務員学科2年制` —— master 归 `文化教養`,PDF 归 `商業実務`;学科名与数值全同,仅分野分类分歧。`classification=field_taxonomy_cross_source_delta`, `operator_decision=needs_owner_decision`。

两类对账均**不覆盖 master、不进最终 Excel authoritative output**。

## 本 Rung 落地的两处原则性修复（TDD red→green）

1. **`master_loader` 跳过空白在籍学科**(`9b3d117`)：master 某学科该 FY `在籍` 为空白(None,非 0)= 非在读 FY 行(legacy/停办),不再吐幻影行。0(募集停止仍在籍0)≠ None。→ 16 由 fail 转 clean pass。
2. **学科身份对齐 + コース 规范化**(`e8bfc30`)：`department_key` 剥离尾部 `コース`(PDF `(ビジネスコース)` ↔ master `（ビジネス）`);`align_department_fields` 在学科键校内两侧唯一时折叠分野前缀,使等值按学科对齐,分野分歧转 `TaxonomyReconciliationRow`;学科键同侧碰撞则保留 `分野|学科`(碰撞保护不变)。→ 08 由 fail 转 pass_with_reconciliation。

抽取器主路径未动(承隔离红线);两处修复均在 Rung diff 路径。

## master 数据发现（06 盛岡校 = `master_expected_error`,非抽取错）

`公務員2年制` 在籍:master=**91** vs 官方 PDF 原始单元格 **`raw='92人'`**(Δ+1)。抽取器读的 92 **正确**;master 有 +1 转录误差。其余 11/12 全 exact → **pin 正确绑定盛岡校,未串山形校**;唯一失败点即该 master 误差。

- 红线禁编辑 `data/master.xlsx` → 06 无法在本 Rung 达成 diff=0,记为 owner master-correction 项(91→92)。
- 在籍是硬门,**不**降级为对账(与 capacity/分野 不同:在籍是同概念应等值,分歧即数据错)。

## Adversarial review 结论（`rung1b-adversarial-review` workflow,6 透镜 + 综合,7 agent 独立复算)

**综合判定:`RUNG_1B_PASS_WITH_RECONCILIATION` —— 6 个假成功向量全部 `refuted`,0 confirmed。**

各 agent 不采信本报告,独立复算(重跑集成测试 4 passed、dry-run、raw pdfplumber evidence、绕过 loader 直读 `master.xlsx`):

| 透镜 | 判定 | 关键证据 |
|---|---|---|
| master 反推身份/数值 | `refuted` | actual 侧全程只读 PDF;**06 的 actual=92(PDF)≠ expected=91(master)是内建反推守卫**——若反推会读成 91 假通过 |
| 分野折叠假合并 | `refuted` | 08 公務員学科两侧学科名 byte-identical、值全等,是同一学科换分野归类,非两个不同学科;03/16 分野本就一致,折叠为 no-op |
| コース 过度规范化 | `refuted` | 全大原语料 compose collision=0;门禁集只走括号第二分支,1:1 映到同一真实学科 |
| loader 空白跳过隐藏缺失 | `refuted` | 16 的 2 空白学科经 master 多年 phase-out(2022 募集停止→None),2025 PDF 确实只列 3 学科;抽取 3 records 与 master 3 活跃学科双射 |
| 兄弟校串行 | `refuted` | `master_loader` col2 学校名精确 `!=` 过滤;山形/盛岡行集不相交;错 pin 炸 12 missing+12 unexpected,绝不静默通过 |
| 定員混入在籍 / 静默丢对账 | `refuted` | 03 医療事務抽取 enrollment=70(=master 在籍)非 80(PDF 定員);capacity/taxonomy 全部 `needs_owner_decision` 显式出账 |

**5 处 latent 稳健性缺口（真实大原数据未触发,Rung 1c 前加固,不影响本 Rung claim):**
1. loader 空白跳过盲区:PDF 有 + 抽取器漏 + master 空白 三者共现时不可见 → 加「抽取 record 数 == PDF 自身学科表数」的 master-无关交叉校验。
2. `*|学科` 折叠依赖「学科名在校内唯一标识学科」不变式 → 折叠前断言两侧 raw 学科名相等。
3. bare-コース 无条件剥离 + `department_key('コース')==''` 退化 → 加空键守卫 + CI 语料碰撞断言。
4. `rung_gate` 的 capacity missing/unexpected 落空档(良性)→ reconcile-metric 非 exact 一律入对账。
5. `prefecture` 未用,兄弟判别仅靠 col2 → prefecture 必填或断言 学校名唯一。

综合建议:**进入 Rung 1c,并在越过 Rung 1c 前加固上述 5 项**;06 的 92-vs-91 判别断言永久保留为反推回归守卫。

## owner 待决策（并行,非阻塞）

1. **定員列口径**（承 Rung 1a A/B/C/D,仍未定）。
2. **分野归属**（新增）：`公務員学科` 目标 Excel 归 `文化教養`(master)还是 `商業実務`(官方 PDF)?推荐以官方 PDF 分野为准或双列并存。
3. **06 master 修正**：`公務員2年制` 在籍 91→92(以官方 PDF 为权威)。

## 下一步 / Rung 1c 建议

- Rung 1c(10 校 = 最小 gold set):扩样验证 loader None-skip 与学科对齐在更多校区的稳健性;统计 `master_expected_error` 类(如 06)出现率,量化 master 数据质量。
- 将 `risk_flags` / `expected_master_filter` 提升为 `pinned_manifest` loader 一等字段(本 Rung 暂作 manifest 文档化元数据)。
- 建立 master 数据质量回流:抽取器可证正确、master 分歧的项,汇总成 owner 修正队列。
