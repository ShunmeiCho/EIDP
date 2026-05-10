# Discovery Gold Set

This directory records manual or Codex-assisted demonstrations for finding a
school's public confirmation PDF before turning the path into crawler logic.

The goal is to stop treating discovery as broad blind crawling. Each entry
captures:

- what the operator or Codex tried,
- which page or PDF proved useful,
- which clues made the result reusable,
- whether the result is true target-year success or only the latest public
  stale-year form.

`entries/*.json` are intentionally small and append-only. A future discovery
agent should learn from these demonstrations, then emit structured candidates
that can be compared with this gold set.

To inspect the current release-relevant buckets locally:

```bash
uv run eidp discovery-gold-set --json
```

To emit the bounded school/site inputs that should be used for a gold-set PDF
discovery run:

```bash
uv run eidp discovery-gold-run-plan --json
```

`discover-pdfs` reads candidate sites from the database, so seed the committed
gold-set school sites before running the bounded PDF discovery pass. The command
is a dry-run by default:

```bash
uv run eidp seed-discovery-gold-sites --gold-set-dir data/discovery-gold-set
uv run eidp seed-discovery-gold-sites --gold-set-dir data/discovery-gold-set --apply
uv run eidp discover-pdfs --discovery-method discovery_gold_set --evidence-log _temp/discovery-gold-evidence.jsonl
```

To evaluate crawler or agent output against the gold set, write one JSON object
per line with `entry_id`, `outcome`, `pdf_url`, `fiscal_year`, and
`strict_target_year_success`, then run:

```bash
uv run eidp eval-discovery-gold --predictions path/to/predictions.jsonl --json
```

Existing `discover-pdfs` evidence logs can be evaluated directly:

```bash
uv run eidp eval-discovery-gold --pdf-evidence path/to/discovery-evidence.jsonl --json
```

For root-cause analysis outside the gold-set entries, summarize a discovery
evidence log into school-level buckets:

```bash
uv run eidp summarize-discovery-evidence \
  --evidence-log path/to/discovery-evidence.jsonl \
  --prefecture 埼玉県 \
  --discovery-method prefecture_aggregator \
  --json
```

Use `--fail-on-regression` in CI or release checks when missing, unexpected, or
mismatched predictions should block the run.

Current v0.1 seed coverage:

- Sanko disclosure pages with stale latest-public FY2025 controls.
- Dedicated school-support pages with Reiwa-year anchors.
- WordPress disclosure posts with opaque upload PDF filenames.
- Structured information pages with many adjacent non-target PDFs.
- Dense information pages where the target-form anchor is surrounded by
  adjacent school-evaluation, syllabus, and teacher-list PDFs.
- University-affiliated vocational school tuition or school-information pages
  that expose target-looking support PDFs without reliable target-year proof.
- Direct `jyouhoukokai` PDFs whose body proves the target-form shape but whose
  URL and anchor context require operator review before strict FY acceptance.
- Official-index disclosure pages that crawl successfully but expose no PDF
  candidates, so the operator sees a true manual-required case rather than a
  hidden crawler error.
- Image-only support PDFs that look target-related but must remain in review
  until OCR or page context proves the target fiscal year.
