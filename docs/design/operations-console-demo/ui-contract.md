# UI Contract Seed

This file captures the design contract implied by the demo prototype. It is not
a schema migration and does not replace the production domain model.

## Pages

| Page id | Operator label | Purpose |
| --- | --- | --- |
| `dashboard` | `ダッシュボード` | Annual progress, weekly run status, KPI and queue summary |
| `school_queue` | `公式PDF収集` | School-by-school collection lane and next action |
| `pdf_review` | `PDF抽出・確認` | PDF evidence, extraction confidence, manual confirmation |
| `fiscal_year_review` | `年度判定・前年差分` | Target-year evidence and year-over-year sanity check |
| `excel_export` | `競合校Excel更新` | Excel-ready gate, export preview, blocked rows |
| `settings` | `設定` | OCR, thresholds, operator options, environment settings |

Production naming may use more domain-specific labels such as `学校キュー`,
`申請書PDF確認`, and `Excel出力`, but the prototype pages define the current
demo flow.

## Status Labels

The prototype status language should map to controlled production state, not
raw UI strings.

| Prototype label | Production concept |
| --- | --- |
| `Excel出力可` | `workbook_ready` / `excel_ready` |
| `人の確認が必要` | `review_required` |
| `公開待ち` | `target_document_not_yet_published` |
| `PDF検出済` | `target_document_candidate_found` |
| `低信頼度` | `low_confidence_review` |
| `年度不明` | `target_document_year_unverified` |
| `学科変更` | `program_change_review` |
| `画像PDF・OCR` | `extraction_ocr_required` |
| `令和8年度と確認` | `target_document_confirmed` |
| `Excel出力対象` | `workbook_export_candidate` |

## ViewModel Targets

Streamlit pages should render from page-level ViewModels rather than scattered
ad hoc SQL queries.

```python
@dataclass
class DashboardViewModel:
    target_school_count: int
    pdf_detected_count: int
    excel_ready_count: int
    human_review_count: int
    publication_pending_count: int
    weekly_new_pdf_count: int
    pipeline_steps: list[PipelineStep]
    todo_cards: list[TodoCard]
```

```python
@dataclass
class SchoolQueueRowViewModel:
    school_id: int
    school_name: str
    prefecture: str
    current_lane: str
    next_action: str
    source_label: str
    confidence_label: str | None
    action_label: str
```

```python
@dataclass
class PdfReviewViewModel:
    document_id: int
    school_name: str
    source_url: str
    file_name: str
    confidence: float
    confidence_band: str
    fiscal_year_label: str
    departments: list[DepartmentDiffRow]
    primary_action_label: str
    primary_action_enabled: bool
```

```python
@dataclass
class ExcelExportViewModel:
    output_file_name: str
    updated_school_count: int
    exportable_count: int
    pending_review_count: int
    unresolved_program_change_count: int
    publication_pending_count: int
    gate_message: str
    rows: list[ExcelPreviewRow]
```

## Action Rules

Prototype buttons are visual. Production actions must always use:

- DB transaction boundaries
- validation before writes
- audit logging
- app lock checks
- structured operator error messages
- append-only evidence where applicable
