# Discovery Gold-Set Agent Redesign

Date: 2026-05-11
Branch: `sprint8-handoff-finalize`

## Decision

Discovery should move from broad speculative crawling to:

1. manual or Codex-assisted demonstrations,
2. structured gold-set entries,
3. reusable discovery patterns,
4. agent/pipeline implementation,
5. Windows yield verification.

The ingest layer already follows this shape through `data/gold-set/` and the
PDF evaluation harness. The discovery layer did not, which made URL/PDF
discovery depend on heuristics before enough successful examples existed.

## Current Evidence

Windows v136 samples show the split clearly:

- Saitama 5-school URL crawl: 5/5 auto-registered, strict FY2026 PDF downloads
  0, FY2025 control downloads 4.
- Tokyo 10-school URL crawl: 9/10 auto-registered, strict FY2026 PDF downloads
  0, FY2025 control downloads 3.
- Cross-prefecture 25-school URL crawl: 23/25 auto-registered, strict FY2026
  PDF downloads 0, FY2025 control downloads 15.

This means the crawler can often find official Sanko disclosure paths and can
download target confirmation PDFs when the public latest form is FY2025. Strict
FY2026 correctly refuses those stale forms. The remaining work is not just more
crawling; it is learning and encoding successful discovery demonstrations,
publication-lag classification, and operator review paths.

## New Artifact

`data/discovery-gold-set/` is the discovery-side counterpart to
`data/gold-set/`.

- `schema.json` defines the v0.1 entry shape.
- `entries/*.json` records manual/Codex-assisted demonstrations.
- Entries distinguish true target-year success from latest-public
  publication-lag evidence.

The initial prototype entries are:

- `sanko-osaka-med-2025.json`: accepted FY2025 target confirmation form.
- `sanko-yokohama-sweets-publication-lag-2026.json`: strict FY2026 rejection
  with FY2025 latest-public control success.
- `ecole-matsue-nutrition-2026.json`: accepted FY2026 form from a dedicated
  school-support page with a `令和８年度` anchor.
- `kokufuku-shin-kokusai-fukushi-2026.json`: accepted FY2026 form from a
  WordPress disclosure post where the PDF filename is opaque and the anchor
  context carries the year.
- `ncad-niigata-design-2025.json`: accepted FY2025 form from a structured
  information page that also contains adjacent 役員名簿 and 授業科目 PDFs.
- `bit-toyama-information-business-review-2026.json`: target-looking form from
  a dense information page, routed to operator review because FY2026 is not
  proven.
- `nihon-u-dental-hygienist-publication-lag-2026.json`: visible latest-public
  target form is a FY2025 PDF on a tuition/support page, so strict FY2026
  remains rejected.
- `nihon-u-matsudo-dental-hygienist-review-2026.json`: stable
  `higher_education_support.pdf` link proves target-form shape but has no
  reliable fiscal-year evidence.
- `ast-kansai-keiri-review-2026.json`: direct AST `jyouhoukokai` PDF for
  関西経理専門学校 needs review because the target-form body is yearless.
- `ast-kansai-ika-review-2026.json`: direct AST `jyouhoukokai` PDF for
  関西医科専門学校 follows the same yearless target-form review pattern.

## Implementation Direction

Phase 1 is complete when the repository has a schema and prototype entries.

Phase 2 should use Codex/Claude-assisted web work to collect 20-30 entries:

- accepted target PDF,
- publication lag,
- no target candidate found,
- needs operator review.

Phase 3 should convert repeated patterns into a deterministic agent:

- derive known site-family disclosure pages,
- separate stale latest-public forms from target-year success,
- pre-filter adjacent disclosure PDFs before download,
- emit reviewable evidence for operator UI.

Phase 4 should evaluate discovery against the gold set before Windows release.
The local comparison surface is `uv run eidp eval-discovery-gold --predictions
path/to/predictions.jsonl --json`; crawler or agent output must match gold-set
entry IDs, outcomes, PDF URLs, fiscal years, and strict target-year decisions
before a Windows yield run is treated as meaningful. Existing `discover-pdfs`
evidence JSONL can also be evaluated with `--pdf-evidence`, which maps
`accepted_downloaded`, `fiscal_year_mismatch:*`,
`target_fiscal_year_not_detected`, and `no_candidates_found` into the gold-set
prediction buckets.

Phase 5 should run the bounded Windows yield gate again and compare:

- true target-FY acquisition rate,
- stale latest-public rate,
- no-candidate rate,
- review workload.

## Non-Goals

- Do not loosen strict FY2026 mode to count FY2025 forms as success.
- Do not require the Windows operator to use Codex or Claude Code directly.
- Do not run nationwide SERP crawling from the agent harness.

Codex/Claude is a development-side tool for turning manual discovery into a
gold set and then into code. The Windows operator experience should remain ZIP
extraction, setup, browser UI, and optional API-key configuration.
