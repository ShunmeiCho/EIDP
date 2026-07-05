# Linux/Web v1 Reviewed-Row Key Collision Audit

Date: 2026-07-05

Branch: `integration/linux-web-v1`

Input:

- Master workbook: `/Users/shunmei/workspace/EIDP/data/master.xlsx`
- Sheet: `学科別`
- Mode: read-only scan.
- Reviewed-row sample: not available in this worktree (`data/web-intake` absent).

## Result

Do not start Goal 4 yet.

The current reviewed-row key is not stable enough for Copilot/NotebookLM TRUE/FALSE comparison. Goal 3D must harden reviewed/master diff keys before external double-check import is added.

## Full Master Projection

The scan projected 9,759 master department rows into 204,939 metric rows across `capacity`, `enrollment`, and `intl_students` for FY2019-FY2025.

| Key | Unique keys | Collision count | Max collision size |
| --- | ---: | ---: | ---: |
| K1 `school_name | department_name | fiscal_year | metric` | 193,326 | 10,605 | 4 |
| K2 `school_name | course_name | department_name | fiscal_year | metric` | 193,326 | 10,605 | 4 |
| K3 `school_name | field_category | course_name | department_name | day_or_evening | duration_years | fiscal_year | metric` | 204,372 | 546 | 3 |

K2 is identical to K1 in this scan because the master sheet does not expose a separate PDF-style `course_name`; master column `課程名` is currently treated as `field_category`.

## Non-Empty Expected Values Only

After excluding blank expected metric values, 114,180 metric rows remained.

| Key | Unique keys | Collision count | Max collision size |
| --- | ---: | ---: | ---: |
| K1 `school_name | department_name | fiscal_year | metric` | 108,760 | 5,030 | 4 |
| K2 `school_name | course_name | department_name | fiscal_year | metric` | 108,760 | 5,030 | 4 |
| K3 `school_name | field_category | course_name | department_name | day_or_evening | duration_years | fiscal_year | metric` | 114,093 | 84 | 3 |
| K3 + `corporation_name` | 114,102 | 75 | 3 |
| K3 + `prefecture | corporation_name` | 114,102 | 75 | 3 |

## Collision Examples

K1 collision example:

- School: `仙台大原簿記情報公務員専門学校`
- Department: `税理士会計士`
- FY/metric: `2019 capacity`
- Master rows: 3419, 3420, 3421, 3422
- Values: 40, 30, 45, 50
- Distinguishing field: `年限` differs (`4`, `3`, `2.4`, `2`).

K3 collision example:

- School: `ECCコンピュータ専門学校`
- Field: `工業`
- Department: `マルチメディア研究学科(Webデザイン)`
- Day/duration: `昼`, `3`
- FY/metric: `2019 capacity`
- Master rows: 3288, 3289
- Values: 108, 60
- Available K3 fields are still identical.

K3 collision example:

- School: `専門学校ヒコ・みづのジュエリーカレッジ`
- Field: `文化教養`
- Department: `ジュエリーデザイン科(ジュエリープロダクト)`
- Day/duration: `昼`, `2`
- FY/metric: `2025 capacity`
- Master rows: 4193, 4202, 4207
- Values: 60, 30, 30
- Available K3 fields are still identical.

## Decision

Goal 4 is blocked by key instability.

Open Goal 3D first:

- Preserve `field_category` and `course_name` through extraction review and normalized review reports.
- Add master row identity (`master_row_id` or source row number) to expected rows.
- Detect duplicate reviewed/master keys and report them as ambiguous instead of silently choosing one row.
- Require `operator_mapping_id` or a master row mapping when K3 is still ambiguous.
- Keep final Excel export, Copilot/NotebookLM import, and XLOOKUP out of scope.

Release Forecast remains `NOT_READY`.
