# ADR-2026-07 — EIDP v1 架构:Python core + FastAPI + PostgreSQL + React(校内内网多人 Web)

**Status: DRAFT**（待 owner 批准 + Rung 1c 硬门通过;在此之前不实现 React/FastAPI/PostgreSQL)

本 ADR 是架构方向草案,**不改变** `ADR-2026-07-linux-web-pivot.md` 的状态,也**不触动** /goal、release gates、Windows 轨道或现有 Streamlit 代码。它记录会议后两项新前提带来的目标架构。

## Context

1. 部署从 Windows 单机 ZIP 转向 **研究室 Linux 服务器 + 浏览器访问**(会议:「Webベースで構築」「研究室の Linux サーバーに配置」「ユーザーはブラウザのみで操作」)。
2. 使用人数从 **1 人转为多人**。
3. 使用者与服务器在**同一校内内网 IP 段**内,不走公网。
4. 现有 Rung 1a/1b 抽取/diff 核心已在 Python 中证明可行(field aliases、table-grid extractor、master loader、master diff、capacity/taxonomy reconciliation、pre-Rung1c guardrails,2177 tests)。

## Decision

### D1. Python 保留为核心后端与抽取引擎
`eidp-core`(table_grid_extractor / field_aliases / master_loader / master_diff / capacity·taxonomy reconciliation / excel export / audit / validation)**继续 Python**。不重写为 TS/Node/Go——无收益、只增风险。Python 角色从「整个应用」收敛为「领域核心 + API backend + extraction worker」。

### D2. FastAPI 作为 API 层
认证/会话、路由、任务状态、权限、audit、导出编排。

### D3. PostgreSQL 取代 SQLite(多人生产)
- 生产/多人:PostgreSQL(并发、事务、锁、访问控制)。
- 开发/测试/fixture/local smoke:SQLite 可留。
- 保持 **SQLAlchemy 抽象层**,业务代码不直接依赖 SQLite 特性,便于渐进迁移。

### D4. React/TypeScript 作为多人生产 UI
review table、diff table、PDF intake、上传/下载、状态流转。

### D5. Streamlit 降级为内部/开发原型
保留作 extractor 输出查看、master diff 调试、Rung 1c/2 viewer、PoC;**不作为**多人生产 UI 的最终形态。短期不删除。

### D6. 旧 HTML/standalone/`support.js` 仅作设计参考
`.dc.html` 原型与 generated `support.js` 是设计意图参考,**不得**当作 React 生产代码复制;React UI 是同一设计意图的重新实现。

### D7. 部署模型 —— 校内内网 Web 系统(关键表述,必须写明)
> **EIDP v1 Web 版不是 Linux 桌面应用。用户使用自己的电脑,通过校内内网浏览器访问 EIDP。Linux 服务器承担计算、存储、抽取、diff、Excel 生成。用户不直接操作 Linux 文件系统,不通过 SSH/VNC/远程桌面使用,UI 中不出现服务器路径。**

内网边界:Linux server 内网 IP(10./172./192.168.);Nginx 只监听内网 + 网段 allowlist;FastAPI 不直接暴露公网;PostgreSQL 仅本机/内网受控;PDF storage 不开放目录访问。内网**不能省略**:登录、角色权限、audit log、上传限制、文件权限、并发锁、备份。

### D8. 多人域对象与并发
users / roles(admin·operator·reviewer·viewer)/ ReviewAssignment / ReviewLock / Job·JobStatus / AuditEvent / PdfIntakeItem / ExtractionRun / ReconciliationItem / WorkbookExport。
并发规则:同一 PDF/学校/学科 review task 同时仅一人可编辑,他人只读或申请接管;所有修改写 audit log;Excel export 需 reviewer/admin 批准。

### D9. UI 页面优先级(围绕真实工作流,Dashboard 后置)
`PDF Intake → Extraction Jobs → Extraction Review → Reconciliation → Double Check → Excel Export/Download → Audit → Admin`。
- Extraction Review 是 Rung 1a/1b 成果进入 UI 之处:显示学科/在籍/留学生 + page/table/row/col evidence + confidence + diff;可确认/修正/标记 needs_owner_decision·master_expected_error·taxonomy_reconciliation。
- Reconciliation 页面显式呈现 capacity/taxonomy/master_expected_error(不藏在报告里),状态 needs_owner_decision/accepted/rejected/deferred/resolved。
- Double Check:用户在 Copilot/NotebookLM 侧处理 PDF → 导出 CSV/XLSX → 上传 EIDP 对照(EIDP **不**自动上传 PDF 到外部);TRUE/FALSE + mismatch list。
- Excel Export:生成→下载(不在服务器直接编辑),每次导出记 export_id/生成者/时间/学校数/排除项/文件 hash/下载链接。

### D10. 迁移方式 —— 包裹而非重写
先稳核心,再抽 `eidp-core`(UI 无关),再 FastAPI 包 API,再 React 调 API,最后 PostgreSQL 承接多人状态。保证现有 Rung 1a/1b diff 证据与 2177 tests 继续有效。

## Guardrail(执行红线)
**在 Rung 1c 硬门通过或明确指示前,不实现 React/FastAPI/PostgreSQL。** 当前 sprint 只做:Python core + Rung 1c + guardrails + owner capacity/taxonomy 决策 + structured reconciliation artifacts。

## Phase 路线
- **A(当前)**:Python core、Rung 1c 10 校、guardrails、owner 决策、reconciliation artifacts。
- **B**:FastAPI skeleton + PostgreSQL schema + intake/extraction/diff/export/audit API。
- **C**:React UI(Intake / Review / Reconciliation / Double Check / Export)。
- **D**:多人运行(users/roles / review locks / job queue / audit / export approval)。
- **E**:Linux 部署(systemd/Docker Compose / Nginx 内网反代 / PostgreSQL / file storage / backup / 内网访问测试)。

## Consequences
- 优点:保留已验证 Python 核心;UI/并发/多人交给合适技术;内网前提简化安全但不省治理。
- 成本:引入 JS/TS 前端 + Postgres 运维 + API 边界;需 SQLAlchemy 迁移与 schema 设计。
- 风险:核心未稳前做 UI = 漂亮外壳 → 故 Rung 1c 先行。

## References
- 会议纪要:Webベース構築 / 研究室 Linux サーバー / ブラウザのみ操作 / 校内内网;系统 + Copilot/NotebookLM 双重抽取 + Excel TRUE/FALSE + XLOOKUP;图片 PDF 作例外。
- `docs/reports/rung1a-ohara-master-diff.md`、`docs/reports/rung1b-ohara-master-diff.md`。
- FastAPI(Python type hints / OpenAPI / 文件上传 / 后台任务)、PostgreSQL(ACID/MVCC/并发)、SQLAlchemy(ORM 抽象)、React(组件/列表/事件/状态)。
