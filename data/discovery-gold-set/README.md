# Discovery Gold Set

This directory records manual or Codex-assisted demonstrations for finding a
school's public confirmation PDF before turning the path into crawler logic.
The operational manual/Codex RCA procedure lives in
`docs/runbooks/discovery-codex-manual-rca.md`.

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

The committed `expected-predictions.jsonl` file is the complete expected
prediction fixture for the current gold set. It is intentionally checked into
git so release gates can prove the evaluator itself still catches missing or
mismatched entries:

```bash
uv run eidp eval-discovery-gold \
  --predictions data/discovery-gold-set/expected-predictions.jsonl \
  --fail-on-regression \
  --json
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

To prepare one failed school for Codex-assisted manual RCA, emit the
single-school input packet from the configured DB:

```bash
uv run eidp discovery-rca-packet \
  --school-id <id> \
  --evidence-log path/to/discovery-evidence.jsonl \
  --json
```

Use `--prompt` on the same command to emit a copy-paste Codex investigation
prompt instead of the raw packet JSON. The packet includes the latest bucket,
top evidence reasons, and up to 10 compact evidence rows for that school.

For a prioritized list of schools to hand to Codex next:

```bash
uv run eidp discovery-rca-batch-plan \
  --evidence-log path/to/discovery-evidence.jsonl \
  --prefecture 埼玉県 \
  --discovery-method prefecture_aggregator \
  --limit 10 \
  --include-prompts \
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
- Image-only old-year support PDFs whose URL or anchor explicitly says `R7` or
  `令和7年度`, which should remain review-bound unless the URL or anchor also
  contains target application-form hints such as `様式第2号` or `確認申請`.
- Official-index disclosure pages where stale-looking URL/anchor hints must be
  overridden only by PDF-body current-year evidence.
- Official-index support pages where a yearless confirmation form is accepted
  only after the PDF body classifies as target and the current-year prefecture
  index supplies auditable year evidence.
- Disclosure tables where every link says only `PDF` but the same-column header
  identifies `確認申請書`; the header must apply only to that column, while
  neighboring syllabus, grade-policy, and course-list columns remain non-target.
