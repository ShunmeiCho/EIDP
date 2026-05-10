# Discovery Gold-Set Agent Redesign

Date: 2026-05-11
Branch: `sprint8-handoff-finalize`

## Decision

Discovery should move from broad speculative crawling to a layered flow:

1. prefecture/government official indexes as the primary URL source,
2. operator-manual evidence where the official index is absent or stale,
3. corporation/CMS pattern candidates with body validation,
4. bounded same-site graph crawl,
5. SERP as the last fallback, never as the main data source.

Manual or Codex-assisted demonstrations remain important, but their role is
pattern discovery and regression evaluation, not replacing the official-index
chain. The ingest layer already follows this shape through `data/gold-set/` and
the PDF evaluation harness; the discovery layer now has the matching
`data/discovery-gold-set/` surface and should use it to evaluate proposed
crawler/agent behavior before broad Windows yield runs.

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
crawling; it is first proving where the official-index chain breaks, then using
gold-set demonstrations to prevent regressions while improving that layer.

## Existing Artifact

`data/discovery-gold-set/` is the discovery-side counterpart to
`data/gold-set/`.

- `schema.json` defines the v0.1 entry shape.
- `entries/*.json` records manual/Codex-assisted demonstrations.
- Entries distinguish true target-year success, latest-public publication-lag
  evidence, no-candidate outcomes, and operator-review cases. The schema is
  already richer than a minimal URL/PDF list and should be reused rather than
  replaced.

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
- `iruma-kango-no-candidates-2026.json`: Saitama official-index disclosure URL
  crawls successfully but emits `no_candidates_found`, proving this bucket is a
  first-class manual-required outcome.
- `omiya-dental-hygienist-image-review-2026.json`: Saitama official-index URL
  exposes an image-only target-looking PDF that remains review-bound because
  strict FY2026 evidence is not text-detectable.

## P0 Root-Cause Direction

The immediate P0 is the Saitama official-index RCA, not adding more manual
gold-set entries. The official Saitama artifact already shows:

- `extracted_total=60`
- `extracted_with_url=60`
- `db_matched=53`
- `new_url_candidates=53`
- URL quality: `disclosure=36`, `homepage=24`

The current RCA database contains 71 Saitama schools and 51
`SchoolSite(discovery_method="prefecture_aggregator")` rows for Saitama. All 51
are `url_type="disclosure"`. That proves Layer 0 is present for this bounded
RCA: the official-index URLs are entering the database.

The 2026-05-11 current-code 51-site strict FY2026 PDF discovery replay shows
the break is Layer 1:

- `crawled=51`
- `found=49`
- `downloaded=1`
- `failed=7`
- `skipped=348`
- `cached_rejections=38`
- `prefiltered=134`
- `Document` rows after the RCA: `1`
- ingest of that document created 2 current FY2026 `DepartmentYearly` rows
  with `extraction_confidence=0.94` and one `school_fiscal_year_status`
  `excel_ready=1` row.

School-level buckets:

- 1 school: `accepted_target_pdf`
- 34 schools: `publication_lag_or_old_target_pdf`
- 8 schools: `non_target_candidates_only`
- 6 schools: `target_form_without_year_evidence`
- 1 school: `site_fetch_error_only`
- 1 school: `no_pdf_candidates`

This means the current Saitama bottleneck is not official-index URL ingress. It
is official URL to strict target-FY PDF acquisition. Current code can acquire at
least one true strict FY2026 target form from the official-index chain, but the
dominant bucket remains latest-public old-year target forms and review/manual
cases, far below the 60-70% ship gate.

## Implementation Direction

Phase 1 is already complete: the repository has the discovery gold-set schema,
prototype entries, and evaluation commands.

Phase 2 should expand the existing entries to 40-60 stratified cases, not a
flat 20-30 sample. If the goal is to claim 75%+ discovery automation, collect
80-120 cases. Stratify by both `site_family` and `outcome`:

- accepted strict target-FY PDF,
- publication lag / latest-public old-year target form,
- no target candidate found,
- needs operator review,
- target form without reliable year evidence,
- site fetch/TLS/robots failure,
- non-target candidates only.

Phase 3 should convert repeated patterns into deterministic candidate
generators plus body/evidence validation, not treat URL templates as truth:

- derive known site-family disclosure pages,
- separate stale latest-public forms from target-year success,
- pre-filter adjacent disclosure PDFs before download,
- emit reviewable evidence for operator UI.

Phase 4 should evaluate discovery against the gold set before Windows release.
The bounded run inputs are emitted by `uv run eidp discovery-gold-run-plan
--json`; this keeps the next test run scoped to the committed demonstrations
instead of ad hoc broad crawling.
Because `discover-pdfs` reads `SchoolSite` rows from the database, the bridge
command is `uv run eidp seed-discovery-gold-sites --gold-set-dir
data/discovery-gold-set --apply`. It writes `discovery_method=
"discovery_gold_set"` sites from the committed demonstrations, after which the
bounded pass can run with `uv run eidp discover-pdfs --discovery-method
discovery_gold_set --evidence-log _temp/discovery-gold-evidence.jsonl`.
The local comparison surface is `uv run eidp eval-discovery-gold --predictions
path/to/predictions.jsonl --json`; crawler or agent output must match gold-set
entry IDs, outcomes, PDF URLs, fiscal years, and strict target-year decisions
before a Windows yield run is treated as meaningful. Existing `discover-pdfs`
evidence JSONL can also be evaluated with `--pdf-evidence`, which maps
`accepted_downloaded`, `fiscal_year_mismatch:*`,
`target_fiscal_year_not_detected`, and `no_candidates_found` into the gold-set
prediction buckets. CI or release checks should add `--fail-on-regression` so
missing, unexpected, or mismatched predictions return a non-zero exit code
instead of only printing a report.

The Saitama root-cause check should use the evidence summary command before
changing crawler heuristics:

```bash
uv run eidp summarize-discovery-evidence \
  --evidence-log _temp/saitama-rca-current/logs/prefecture_pdf_evidence.jsonl \
  --prefecture 埼玉県 \
  --discovery-method prefecture_aggregator \
  --json
```

The 2026-05-11 current-code replay against a copied v92 Saitama DB crawled all
51 `prefecture_aggregator` school sites and produced 423 evidence rows:

- 40 schools: `publication_lag_or_old_target_pdf`
- 5 schools: `site_fetch_error_only`
- 3 schools: `non_target_candidates_only`
- 2 schools: `target_form_without_year_evidence`
- 1 school: `no_pdf_candidates`

This means the immediate Saitama bottleneck is not official-index URL ingress.
The dominant bucket is latest-public or old-year target PDFs, while strict
FY2026 correctly downloads 0.

Phase 5 should run the bounded Windows yield gate again and compare:

- true target-FY acquisition rate,
- stale latest-public rate,
- no-candidate rate,
- review workload.

Operator UI capture also needs to preserve three fields when a human finds a
PDF manually: the URL, the path used to find it, and the result label. A bare
`SchoolSite` insert is not enough to train or evaluate the discovery agent.

## Non-Goals

- Do not loosen strict FY2026 mode to count FY2025 forms as success.
- Do not require the Windows operator to use Codex or Claude Code directly.
- Do not run nationwide SERP crawling from the agent harness.

Codex/Claude is a development-side tool for turning manual discovery into a
gold set and then into code. The Windows operator experience should remain ZIP
extraction, setup, browser UI, and optional API-key configuration.
