# Codex-Assisted Discovery RCA Runbook

This runbook defines how Codex should manually investigate school PDF discovery
failures and turn the result into repeatable crawler behavior. The goal is not
to manually replace the crawler. The goal is:

1. start from the official-index chain,
2. manually prove one school-level outcome,
3. record the path and decision label,
4. convert only repeated patterns into code or gold-set regression entries.

Do not run nationwide SERP crawling from an agent harness. SERP is a bounded
fallback for a named school, not the primary discovery source.

## Inputs

For each school, collect these facts before opening the web:

- `school_id`
- `school_name`
- `prefecture`
- `target_fiscal_year`
- registered `SchoolSite` rows, especially
  `discovery_method="prefecture_aggregator"`
- latest `discover-pdfs` evidence rows for that school
- current school-level evidence bucket from
  `eidp summarize-discovery-evidence`

Useful local commands:

```bash
uv run eidp summarize-discovery-evidence \
  --evidence-log path/to/evidence.jsonl \
  --prefecture 埼玉県 \
  --discovery-method prefecture_aggregator \
  --json

uv run eidp discovery-gold-set --json
uv run eidp eval-discovery-gold --pdf-evidence path/to/evidence.jsonl --json
uv run eidp discovery-rca-packet \
  --school-id 95 \
  --evidence-log path/to/evidence.jsonl \
  --json
uv run eidp discovery-rca-packet \
  --school-id 95 \
  --evidence-log path/to/evidence.jsonl \
  --prompt
uv run eidp discovery-rca-batch-plan \
  --evidence-log path/to/evidence.jsonl \
  --prefecture 埼玉県 \
  --discovery-method prefecture_aggregator \
  --limit 10 \
  --include-prompts \
  --json
```

## RCA Order

Follow this order. Do not jump to broad search until the official-index path is
classified.

1. **Official index handoff**
   - Confirm the prefectural official list produced a school URL.
   - If no URL was registered, classify as Layer 0 failure.
   - If the URL exists, continue to Layer 1. Do not start SERP yet.

2. **Registered disclosure page**
   - Open the registered `SchoolSite.url`.
   - Look for links around `情報公開`, `公開情報`, `修学支援`, `高等教育`,
     `無償化`, `機関要件`, `確認申請`, and `様式第2号`.
   - Record the source page URL and exact anchor text.

3. **Same-site bounded navigation**
   - Check same-domain links that visibly look like disclosure/public info
     pages.
   - Check `robots.txt` and sitemap only for same-domain disclosure-like URLs.
   - Do not follow unrelated admission, blog, SNS, job, or third-party
     directory pages unless the official page explicitly points there.

4. **Candidate PDF inspection**
   - Prefer the PDF body over URL/anchor year hints.
   - Treat URL/anchor year hints as evidence only when they are specific and
     tied to target-form wording.
   - If the candidate is image-only, classify it as review unless OCR or trusted
     official-index context proves the target year.

5. **Last-resort bounded search**
   - Use search only for a named school and only after official-index and
     same-site routes are classified.
   - Use queries such as:
     - `{school_name} 修学支援 機関要件確認申請書`
     - `{school_name} 様式第2号 修学支援`
     - `{school_name} 情報公開 修学支援`
   - Reject third-party directory pages as truth sources. They may hint at a
     school domain, but they must not prove the PDF outcome.

## Outcome Labels

Every manual investigation must end in one of these labels.

### `accepted_target_pdf`

Use only when strict target-year success is proven.

Acceptable evidence:

- PDF text/OCR contains the configured target FY, for example `2026年度` or
  `令和8年度`.
- URL or anchor contains target-year evidence and the downloaded PDF body
  classifies as the target confirmation form.
- Current prefecture official-index disclosure context supplies trusted year
  evidence, and the downloaded PDF body classifies as target. Record
  `year_evidence="prefecture_index_current_year"`.

Do not use crawl date or the current calendar year as fiscal-year evidence.

### `publication_lag_latest_public`

Use when the latest visible target-form candidate is clearly old-year.

Examples:

- `R7修学支援に関する資料` for target FY2026.
- `令和7年度-様式2` for target FY2026.
- image-only PDFs with target-form hints but stale URL or anchor years.

This is not success. It should surface to the operator as publication lag /
latest public old-year PDF.

### `needs_operator_review`

Use when the PDF shape looks like a target confirmation form, but strict
target-year evidence is missing or ambiguous.

Examples:

- yearless `study_support_system.pdf` from an untrusted source,
- image-only candidate with no OCR,
- body confirms the form shape but not the fiscal year,
- conflicting URL/anchor/body evidence.

### `no_target_candidate_found`

Use when the official path was crawled and no plausible target-form candidate
was found.

This is different from a crawler crash. Record the checked page and why the
visible PDFs are irrelevant.

### Site or infrastructure failure

Use an evidence bucket such as `site_fetch_error_only` or
`tls_certificate_verify_failed` when the page cannot be fetched. Do not relabel
this as no target.

## Recording A Gold-Set Entry

Add a new `data/discovery-gold-set/entries/*.json` entry only after the manual
path is understood. Keep the schema in `data/discovery-gold-set/schema.json`.

Minimum useful content:

- `manual_demonstration.steps`: exact human/Codex navigation path.
- `expected_result.school_url`: school homepage if known.
- `expected_result.disclosure_url`: the source page that exposed the PDF or
  proved no candidate.
- `expected_result.pdf_url`: target, stale, review, or empty result.
- `expected_result.strict_target_year_success`: `true` only for strict target
  FY success.
- `automation_pattern.reusable_rules`: the rule that should survive into code.
- `automation_pattern.anti_patterns`: what the crawler must not infer.
- `evidence.source_paths`: local or Windows evidence logs used for the
  decision.

After adding entries, run:

```bash
uv run eidp discovery-gold-set --json
uv run eidp eval-discovery-gold --pdf-evidence path/to/evidence.jsonl --json
uv run pytest tests/unit/test_discovery_gold_set.py \
  tests/unit/test_discovery_gold_set_summary.py \
  tests/unit/test_discovery_gold_set_eval.py \
  tests/unit/test_cli_discovery_gold_set.py \
  tests/unit/test_cli_eval_discovery_gold.py \
  tests/unit/test_discovery_gold_set_seed.py -q
```

## Promoting Manual Findings Into Code

Do not add a crawler rule from one anecdote unless the risk is narrow and the
rule only changes classification/evidence presentation. Prefer these promotion
levels:

1. **Evidence-only classification fix**
   - Safe for outcome labeling, operator UI, and RCA.
   - Example: old-year `image_only` PDFs with `修学支援` or `様式第2号` hints
     should be `publication_lag_or_old_target_pdf`, not
     `non_target_candidates_only`.

2. **Pre-download negative token**
   - Safe when the PDF is clearly adjacent non-target material, such as
     `役員名簿`, `学校情報`, `学校紹介`, or `授業科目`.

3. **Candidate scoring or bounded same-site navigation**
   - Use only after at least two similar gold-set entries or a focused RCA
     proves the pattern.

4. **Strict acceptance rule**
   - Highest risk. Requires target-form body validation plus reliable target
     fiscal-year evidence. Never accept stale forms to raise yield.

## Saitama Current Baseline

The current combined Saitama official-index RCA evidence has 51 scoped
`prefecture_aggregator` disclosure schools:

- `accepted_target_pdf=2`
- `publication_lag_or_old_target_pdf=38`
- `non_target_candidates_only=5`
- `no_pdf_candidates=1`
- `site_fetch_error_only=1`
- `target_form_without_year_evidence=4`

Interpretation:

- Layer 0 is not the primary failure for this bounded Saitama set: 51 official
  disclosure URLs are in DB.
- Layer 1 is the bottleneck: most failures are latest-public old-year target
  forms or review/manual cases.
- The next manual RCA should focus on the 5 `non_target_candidates_only`, the
  1 `no_pdf_candidates`, and the 1 `site_fetch_error_only` before spending time
  on the 42 publication-lag schools.

## Codex Prompt Template

Use this when asking Codex to investigate one school:

```text
Investigate EIDP discovery for school_id=<id>, target_fiscal_year=<year>.

Inputs:
- school_name=<name>
- prefecture=<prefecture>
- registered SchoolSite URLs=<urls>
- latest evidence rows=<paste or path>
- current bucket=<bucket>

Tasks:
1. Classify whether the failure is Layer 0 URL handoff, Layer 1 PDF discovery,
   strict fiscal-year evidence, PDF parsing, or true publication lag.
2. Manually inspect only the official-index URL and bounded same-site paths
   first. Use search only if those are exhausted.
3. End with exactly one outcome label:
   accepted_target_pdf / publication_lag_latest_public /
   needs_operator_review / no_target_candidate_found / site_fetch_error.
4. Return the evidence chain: source page, PDF URL if any, anchor text,
   fiscal-year evidence, and what should become a crawler rule or anti-pattern.
5. If this should enter the gold set, draft the entry fields.
```

## Stop Conditions

Stop manual search for a school when one of these is true:

- strict target-year PDF is proven and can be replayed by `discover-pdfs`,
- latest public target-form PDF is old-year and no current-year evidence exists,
- no plausible target-form link exists after official page, same-site
  disclosure pages, robots/sitemap, and one bounded search pass,
- site fetch is blocked by TLS, robots, auth, or persistent server error.

The result should be a labeled evidence trail, not an open-ended web search.

## Single-School RCA Packet

Use this packet when Windows SSH is unavailable or when a single failed school
needs Codex-assisted manual investigation. The packet is intentionally
school-scoped. It should never expand into a prefecture-wide or nationwide SERP
run.

### Required Input Block

Collect these values before opening the web. If a value is unknown, write
`unknown`; do not infer it silently.

Generate this block directly from the configured DB when possible:

```bash
uv run eidp discovery-rca-packet \
  --school-id <id> \
  --target-fiscal-year 2026 \
  --evidence-log path/to/evidence.jsonl \
  --known-operator-note "optional note" \
  --json
```

Use `--prompt` instead of `--json` when you want a copy-paste Codex prompt
with the packet embedded.

When you have a full evidence log and need to choose the next schools to
investigate, generate a prioritized batch first:

```bash
uv run eidp discovery-rca-batch-plan \
  --evidence-log path/to/evidence.jsonl \
  --prefecture 埼玉県 \
  --discovery-method prefecture_aggregator \
  --limit 10 \
  --include-prompts \
  --json
```

The Windows initial bootstrap and weekly target-year runner write this batch
automatically when PDF discovery evidence exists:

```text
data/output/target-year-discovery/bootstrap-{timestamp}-discovery-rca-batch-plan.json
data/output/target-year-discovery/{run_id}-discovery-rca-batch-plan.json
```

For weekly runs, the same path is exposed in `data/output/last_run.json` under
`discovery_rca.batch_plan_path`. For initial bootstrap runs, it is exposed in
the latest `logs/bootstrap-pdfs-*.json` progress file under
`details.discovery_rca_batch_plan_path`.

The batch plan prioritizes `target_form_without_year_evidence`,
`non_target_candidates_only`, `no_pdf_candidates`, and fetch failures before
`publication_lag_or_old_target_pdf`, because latest-public old-year forms are
usually publication timing problems rather than immediate crawler bugs.

```json
{
  "school_id": 0,
  "school_name": "",
  "prefecture": "",
  "target_fiscal_year": 2026,
  "official_index_url": "",
  "registered_sites": [
    {
      "url": "",
      "url_type": "",
      "discovery_method": "",
      "confidence": null,
      "verified": false
    }
  ],
  "latest_bucket": "",
  "latest_evidence_rows_path": "",
  "known_operator_note": ""
}
```

### Required Output Block

Every manual/Codex investigation must end with one JSON object in this shape.
This is the bridge between human observation, gold-set entries, and future
agent behavior. Generated packets include the latest school-level bucket, top
evidence reasons, and up to 10 compact evidence rows so a copied prompt remains
useful even when the target Codex session cannot read the original JSONL file.

Save the returned object to a local JSON file and validate it before promoting
the finding into the gold set or a crawler rule:

```bash
uv run eidp discovery-rca-outcome-validate --input path/to/rca-outcome.json
```

The validator checks required fields, allowed labels, and the narrow decision
table rules that are dangerous to get wrong. For example,
`accepted_target_pdf` must include a PDF URL, fiscal-year evidence,
target-form evidence, and `operator_action="none"`.
`publication_lag_latest_public` must use
`operator_action="wait_for_publication"`.

For a batch plan, save each school result as one JSON file in the same
directory and validate the directory. When the original batch plan JSON is
available, pass it too so missing, duplicate, or extra school outputs are
rejected:

```bash
uv run eidp discovery-rca-outcome-validate \
  --input path/to/rca-outcomes/ \
  --batch-plan path/to/discovery-rca-batch-plan.json
```

```json
{
  "school_id": 0,
  "target_fiscal_year": 2026,
  "layer": "layer_1_pdf_discovery",
  "outcome": "needs_operator_review",
  "source_page_url": "",
  "candidate_pdf_url": "",
  "anchor_text": "",
  "fiscal_year_evidence": "",
  "target_form_evidence": "",
  "negative_evidence": "",
  "checked_paths": [],
  "search_queries_used": [],
  "operator_action": "review_pdf",
  "gold_set_entry_recommended": false,
  "candidate_rule": "",
  "anti_pattern": "",
  "confidence": "medium"
}
```

Allowed `layer` values:

- `layer_0_official_index_handoff`
- `layer_1_pdf_discovery`
- `layer_2_pdf_body_or_ocr`
- `layer_3_operator_or_search_fallback`
- `site_infrastructure_failure`

Allowed `operator_action` values:

- `none`
- `review_pdf`
- `manual_url_entry`
- `wait_for_publication`
- `site_access_followup`

### Decision Table

Use this table to keep outcomes consistent across Codex sessions.

| Evidence found | Layer | Outcome | Operator action |
| --- | --- | --- | --- |
| No official-index URL or registered school site exists | `layer_0_official_index_handoff` | `no_target_candidate_found` | `manual_url_entry` |
| Official URL exists and PDF body/OCR proves target FY plus target-form wording | `layer_1_pdf_discovery` or `layer_2_pdf_body_or_ocr` | `accepted_target_pdf` | `none` |
| Official URL exists, target-form candidate is latest public but body/URL/anchor proves old FY only | `layer_1_pdf_discovery` | `publication_lag_latest_public` | `wait_for_publication` |
| Target-form shape exists but year is missing, conflicting, or image-only without OCR proof | `layer_2_pdf_body_or_ocr` | `needs_operator_review` | `review_pdf` |
| Only adjacent non-target PDFs are visible, such as 役員名簿, 授業科目, 学校情報, 学校紹介, 学校案内, 募集要項 | `layer_1_pdf_discovery` | `no_target_candidate_found` | `manual_url_entry` |
| Page fetch fails because of TLS, robots, auth, repeated 403/429/503/418, or server error | `site_infrastructure_failure` | `needs_operator_review` | `site_access_followup` |
| Named-school bounded search finds a school-domain disclosure URL after official paths are exhausted | `layer_3_operator_or_search_fallback` | classify by PDF/body evidence | record query and add review if not strict |

Important distinction:

- `no_target_candidate_found` means the official path was checked and no
  plausible target-form candidate was visible.
- `needs_operator_review` means a plausible target-form candidate exists but
  strict target-year acceptance is not proven.
- `publication_lag_latest_public` means the target-form candidate is real but
  stale for the configured target FY.

### Search Boundaries

Codex may use web search only after the official-index URL, registered
`SchoolSite` rows, same-domain disclosure paths, robots, and sitemap have been
classified.

When search is used:

- one named school at a time,
- at most three query variants,
- inspect only top school-domain or official-domain results,
- third-party directories are hints for a domain, never truth sources,
- record every query in `search_queries_used`.

### Promotion Rules

Manual findings do not automatically become crawler rules.

- Add a gold-set entry when the case is a new site family, a previous bug
  regression, or a release-relevant outcome bucket.
- Add code only after at least two similar gold-set entries show the same
  reusable pattern, unless the change is a narrow evidence-label or
  pre-download negative-token fix.
- Never promote a rule that accepts target FY without PDF body/OCR evidence,
  trusted current official-index context, or another auditable year source.
- Keep broad SERP discovery outside this flow; bounded search is fallback
  evidence collection, not the primary data source.

### Copy-Paste Prompt

```text
Investigate this EIDP school as a single-school RCA packet. Do not run broad
SERP crawling.

Input:
<paste Required Input Block JSON>

Tasks:
1. Classify the failure layer before searching.
2. Check official-index and registered SchoolSite URLs first.
3. Check bounded same-domain disclosure/public-info paths before named-school
   search.
4. Inspect candidate PDF body/OCR evidence before accepting target FY.
5. Return exactly one Required Output Block JSON object.
6. If the case should enter data/discovery-gold-set, draft the entry fields and
   explain the reusable rule and anti-pattern.
```
