# EIDP Domain Vocabulary

EIDP is an official-disclosure pipeline, not a generic crawler. New code and UI
copy should name the business object and workflow state first, then the
technical mechanism only when it matters for implementation.

## Naming Rule

- Prefer stable domain objects over transient implementation actions.
- Keep legacy database table names stable until an explicit migration phase.
- New status values, review task kinds, document kinds, and source trust tiers
  must be registered in the domain taxonomy before production use.
- Search-derived or agent-derived findings are candidates only. They cannot
  become official evidence until verified against an official source or approved
  by an operator.

## Core Terms

| Preferred name | Japanese operator label | Meaning | Legacy or discouraged name |
| --- | --- | --- | --- |
| `Institution` | 学校 | Education institution. Covers specialty schools now and universities later. | `School` for new domain APIs |
| `InstitutionType` | 学校種別 | Specialty school, university, junior college, technical college, etc. | Free-form `school_type` strings |
| `OperatingBody` | 設置者 / 法人 | Corporation, municipality, or other body operating the institution. | Ad hoc `corporation` naming |
| `Authority` | 確認者 / 所管機関 | MEXT, prefecture, ministry, municipality, or other confirming authority. | `prefecture` when the source is not strictly a prefecture |
| `AuthorityIndex` | 確認大学等一覧 | Official authority-published institution list. | `prefecture_aggregator` as a domain term |
| `AuthorityIndexEntry` | 一覧掲載校 | One institution row in an authority index artifact. | `PrefSchool` |
| `AuthorityIndexIngestionPlan` | 公式索引取込計画 | Planned inserts/updates from parsed authority index rows. | `PrefReport` |
| `SiteEntry` | 情報公開ページ | Reusable official disclosure entry page for an institution or operating body. | Generic `url`, `school_site` in new domain APIs |
| `DocumentCandidate` | PDF候補 | A candidate PDF not yet accepted as the target disclosure document. | `candidate_pdf` without trust/status |
| `DisclosureDocument` | 公開資料 | Any downloaded disclosure document. | Generic `Document` in user-facing copy |
| `TargetDocument` | 機関要件確認申請書 | The target application form PDF used for annual metrics. | Generic `pdf` / `document` |
| `Program` | 学科・コース | Program/course unit extracted from the form. | `Department` in new domain APIs |
| `ProgramAnnualMetrics` | 学科別年度データ | Annual capacity, enrollment, international students, graduates, dropouts, etc. | `DepartmentYearly` in new domain APIs |
| `SupportRecipientMetrics` | 対象比率データ | Support recipient counts and rates. | Ambiguous `SupportRecipient` in user-facing copy |
| `ReviewTask` | 確認待ちタスク | Operator-facing task with a concrete next action. | `ReviewItem` in user-facing copy |
| `EvidenceEvent` | 証拠イベント | Recorded evidence for discovery, download, extraction, review, and export. | Generic `log` |
| `WorkbookExport` | Excel出力 | Master or competition workbook output. | Generic `exporter` |

## Current Compatibility Boundary

The current database and many ORM classes still use `School`, `SchoolSite`,
`Document`, `Department`, `DepartmentYearly`, `SupportRecipient`, and
`ReviewItem`. That is acceptable for the release branch. New operator-facing
copy, service names, documentation, and adapter APIs should use the preferred
terms above.

Physical table renames are deferred until after the domain vocabulary, UI copy,
tests, and compatibility adapters are stable.

## Authority Index Source Hierarchy

| Tier | Source | Production role |
| --- | --- | --- |
| T0 | MEXT authority index | Highest-trust official source |
| T1 | Prefecture or confirming-authority index | Primary scalable source for 2400-school coverage |
| T2 | Official institution or operating-body disclosure page | Main document discovery surface |
| T3 | Operator-approved official entry | Accepted after human confirmation |
| T4 | Search or external research candidate | Candidate queue only, never auto-accepted |
| T5 | Untrusted or third-party source | Audit/reference only |

## Agent-Reach Boundary

Agent-Reach belongs outside the production pipeline. It may help a developer or
administrator investigate a blocked institution, but its output is `T4` external
research evidence until EIDP verifies it against an official domain or an
operator explicitly approves it.
