# UI Example Review

Date: 2026-06-19

Reviewed local artifact:

- `UI-example/EIDP 運用コンソール.dc.html`
- `UI-example/EIDP 運用コンソール (standalone).html`
- `UI-example/support.js`

The `UI-example/` directory is currently untracked. It is treated as a design
reference, not a production dependency.

## Confirmed Strengths

- The example is an operator console, not a marketing page or generic crawler
  UI.
- The left navigation and persistent target fiscal year context are a good
  fit for weekly operation.
- The dashboard shows production KPIs, weekly status, and operator to-dos in a
  scannable way.
- The school table is dense and task-oriented, which fits a 2400-institution
  workload.
- The PDF review screen uses a two-pane layout with queue, document preview,
  extracted values, confidence, and manual action controls.
- The fiscal-year review and Excel preview screens match the current EIDP
  workbench direction.

## Required Adjustments Before Reuse

| Current example wording | Required project wording |
| --- | --- |
| `収集・学校別タスク` | `学校キュー` |
| `PDF確認・手入力` | `申請書PDF確認` |
| `年度判定・修正` | `対象年度確認` |
| `Excelプレビュー` | `Excel出力` |
| `DB転記済` | Prefer `学科データ確定` or `Excel出力可` depending on context |

The example also lacks first-class pages for:

- `公式索引管理`
- `学校詳細`
- `学科変更レビュー`
- `監査ログ`

Those should be added before using the example as the canonical UI blueprint.

## Production Suitability

The example must not be copied directly into the Windows operator package:

- `support.js` is a generated runtime and uses dynamic logic execution.
- The dc runtime loads React, ReactDOM, and Babel from `unpkg.com` when not
  already available.
- The dc HTML references Google Fonts.
- The standalone HTML is about 7.1 MB and bundles runtime/fonts for preview.
- It is not connected to EIDP's Streamlit session, DB lock, audit logging, or
  release verifier contracts.

## Decision

Use `UI-example/` as a visual and workflow reference only. The production path
remains Streamlit pages backed by EIDP's existing DB, lock, audit, and release
gate contracts.

Immediate reuse targets:

1. Adopt the dashboard/workbench layout concept in docs and future Streamlit UI
   work.
2. Keep the current small UI-label rename already applied in the product.
3. Add missing `公式索引管理`, `学校詳細`, `学科変更レビュー`, and `監査ログ`
   structure before a larger UI rewrite.
