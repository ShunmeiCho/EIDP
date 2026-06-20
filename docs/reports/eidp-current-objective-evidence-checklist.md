# EIDP Current Objective Evidence Checklist

Updated: 2026-06-21
Branch: `main`
PR: `#8`, merged on 2026-06-19T15:26:20Z
PR merge check:
`gh pr view 8 --json state,mergedAt,mergeCommit,headRefOid,baseRefName,url`
returned `state=MERGED`, `headRefOid=6721bd33d1706e73f50ba9acce91f4f1c16c3e62`,
and merge commit `723a5072f63e8a874bef85cc52d869f5e6daff15`. Local `main`
was fast-forwarded to `origin/main` before the v532 package rebuild.
Previous Windows owner-return remote check:
`docs/reports/2026-05-20-v526-owner-return-remote-check.md` confirmed `ssh win`
was reachable, refreshed v526 owner docs remained staged, and the remote
`publication_lag` approval / E2E sign-off fields are still blank. The refreshed
Windows-staged owner docs ZIP now includes this report and the
target-yearless RCA spot check plus the owner v1.0 A/B decision brief and v526
owner return fill sheet, and has SHA256
`28b12cbec895233b3ad97dff4c7757e2fb89cbd3130c4a604443a06bb8e38d29`.
Current v541 package/source and bounded Windows canary check:
`docs/reports/2026-06-21-v541-owner-signoff-verifier-windows-canary.md`
records the v541 package at commit
`e62d074081e60428957a2f405c3a917bbceb31a0`, package SHA256
`2ffb25884e15b9e2937f43bab7a8f5866d9434bc9f29f8067dbc1760397fa46f`,
non-Windows release gates, Windows setup validation, active-task safety,
weekly limit-50 canary, after-weekly validation, and Stage 6 evidence
verification for `C:\Users\cyo20\EIDP-v541-e62d074-env0`. The v541 canary
remains below gate with strict/Excel-ready `12/50 (24.0%)` and
`ship_gate_status=below_gate`.
Previous v540 package/source and bounded Windows canary check:
`docs/reports/2026-06-20-v540-owner-briefs-windows-canary.md` records the
v540 package at commit `fbdd0bddbeca3e6ceaa7b9e576bc9c5b0b88025a`, package
SHA256 `6f246e47c41869dce401810731df48e99268756622719a0e59461c33fd645fd6`,
Windows setup validation, active-task safety, weekly limit-50 canary, and
Stage 6 evidence verification for `C:\Users\cyo20\EIDP-v540-fbdd0bd-env0`.
The v540 canary remains below gate with strict/Excel-ready `12/50 (24.0%)`
and `ship_gate_status=below_gate`.
Latest complete UI/Excel side-by-side smoke remains v535:
`docs/reports/2026-06-20-v535-full-windows-side-by-side-smoke.md` records setup
validation, active-task safety, UI smoke, weekly limit-50 canary, Excel smoke,
Stage 6 evidence creation, and Stage 6 evidence verification for
`C:\Users\cyo20\EIDP-v535-d742327-env0`.
Initial v541 owner/operator docs staging:
`docs/reports/2026-06-21-v541-owner-docs-windows-staging.md` records the
docs-only handoff ZIP staged at `C:\EIDP-staging\v541-owner-docs-20260621`.
The v541 handoff carries the latest package identity, owner-facing release
summary, short owner sign-off form, owner request, and return fill sheet. The
docs ZIP SHA256 is
`4ab692e47c0077eaedac91f340a561507ebaac79277bdce9db17d28ceea6c731`.
This base handoff is superseded by the r3 false-reject refresh below.
Current v541 strict-yield RCA summary:
`docs/reports/2026-06-21-v541-owner-signoff-verifier-windows-canary.md` records the
`12/50 (24.0%)` blocker and the same release-safe RCA lanes without counting
old-year PDFs, missing-year candidates, or identity mismatches as FY2026/R8
successes. This blocker is not framed as "the crawler cannot run" or "PDFs are
missing"; it is the stricter failure that not enough official candidates can be
accepted as FY2026/R8 target application documents and then become Excel-ready.
It also is not framed as a generic algorithm/model failure unless
rejection-bucket false-reject evidence proves material over-rejection or
fiscal-year extraction mistakes.
The earlier v535 RCA plan remains historical decomposition.
The v541 RCA bucket summary is reproducible with
`uv run python scripts/summarize_stage6_rca.py
logs/win-v541-e62d074-canary/stage6-evidence-20260620-153655.zip --json`, which returns
`ok=true`, `20` RCA packets, and `524` candidate rows. The below-gate release
status is recorded in the v541 weekly summary as `ship_gate_status=below_gate`.
The first false-reject audit packet is generated and recorded at
`docs/reports/2026-06-21-v541-false-reject-audit-packet.md` using
`uv run python scripts/build_false_reject_audit.py
logs/win-v541-e62d074-canary/stage6-evidence-20260620-153655.zip --sample-size
12 --output docs/reports/2026-06-21-v541-false-reject-audit-packet.md`.
Its review worksheet is generated at
`docs/reports/2026-06-21-v541-false-reject-review-sheet.csv` using
`uv run python scripts/build_false_reject_audit.py
logs/win-v541-e62d074-canary/stage6-evidence-20260620-153655.zip --sample-size
12 --format csv --output
docs/reports/2026-06-21-v541-false-reject-review-sheet.csv`. The blank
worksheet validates as `review_status=incomplete`, while the same command with
`--validate-review-csv
docs/reports/2026-06-21-v541-false-reject-review-sheet.csv --require-decisions`
fails until every sampled row has one of the allowed decisions. The validator
also rejects changed immutable row context and reports `bucket_decision_counts`;
the current blank worksheet reports `completed_decisions=0` and
`context_mismatch_count=0`. Completed rows require `reviewer` and an ISO
`reviewed_at` timestamp; `false_reject` and `needs_operator_review` rows
require `notes`.
The current source runbooks now tell the owner/operator how to return that
worksheet: fill only `decision`, `reviewer`, `reviewed_at`, and `notes`, leave
immutable row context untouched, and have the developer validate the returned
CSV from current `main`. The owner-return verifier now accepts
`--false-reject-evidence-zip`, `--false-reject-review-csv`, and
`--false-reject-sample-size`; when supplied, it requires `review_status=complete`
and `context_mismatch_count=0`. The Windows docs-only handoff has been refreshed to r3 at
`C:\EIDP-staging\v541-owner-docs-20260621-r3`, recorded in
`docs/reports/2026-06-21-v541-owner-docs-r3-windows-staging.md`, so the staged
owner docs now include the false-reject worksheet return rules, worksheet CSV,
and the return-verifier false-reject arguments. The superseded r2 ZIP and
extracted directory were removed from Windows staging and the external SSD.
This remains handoff evidence only.
Post-v535 source hardening:
`docs/reports/2026-06-20-sanko-shared-origin-disclosure-probe.md` adds a
bounded same-host Sanko disclosure probe for the remaining
`non_target_candidates_only` packet. The rebuilt v536 package has now rerun the
Windows limit-50 canary:
`docs/reports/2026-06-20-v536-sanko-fresh-windows-canary.md`. The run verifies
package/source commit `f81a9cf8f785457e844cb77857426a02c91f60c7`, Windows setup
`rc=0`, Stage 6 evidence `ok=true`, `shared_origin_derived_fallback_skipped=0`,
and strict/Excel-ready yield still `12/50 (24.0%)`.
Post-v540 source hardening:
v541 now packages and Windows-canary verifies the `scripts/verify_stage6_return.py`
hardening that machine-checks the short owner sign-off form against the selected
release path, expected package SHA256, and expected source commit. It also makes
publication-lag exception approval an `RC_ONLY` path rather than a `READY` path.
Release verdict: **NOT_READY**

This file is the prompt-to-artifact checklist for the current long-term EIDP
objective. It intentionally replaces the older historical v464/v460 narrative
with the current v541 package/source state and v541 bounded Windows canary
state.

## Objective Restated

EIDP is complete only when one Windows operator can process the national
education-institution disclosure universe each rolling fiscal year, including
roughly 700 universities and 1,700 vocational/specialty schools, by:

1. starting from high-trust official authority indexes, including the 47
   prefectural official "confirmed institution" lists for vocational schools
   and an equivalent official-index layer for universities,
2. covering the target institution universe without broad `school name + PDF`
   search as the acquisition strategy,
3. discovering the current rolling target fiscal-year PDF in strict mode,
   currently FY2026/Reiwa 8, while excluding old-year fallback from success,
4. extracting rows with the PDF/OCR stack and admitting only rows with
   three-factor confidence `>= 0.70`,
5. writing `DepartmentYearly` and `SupportRecipient` append-only records,
6. transferring accepted data to the Excel template,
7. auditing all operator actions in `ManualActionLog`,
8. running offline from the Windows ZIP through double-click setup and browser
   UI, and
9. meeting the ship line: true target-form auto-acquisition `>= 60%` and
   operator manual workload `<= 30%` for the current rolling FY.

The goal is not zero-human full automation. It is a Windows one-operator flow
that keeps manual work below the release threshold.

## Current Candidate Boundary

- Latest packaged bounded Windows canary: `dist/eidp-windows-v541.zip`
- Latest complete Windows side-by-side smoke package: `dist/eidp-windows-v535.zip`
- v541 package/source commit:
  `e62d074081e60428957a2f405c3a917bbceb31a0`
- v541 package SHA256:
  `2ffb25884e15b9e2937f43bab7a8f5866d9434bc9f29f8067dbc1760397fa46f`
- Current v541 package/canary contains the post-v540 owner-return verifier
  hardening. Owner handoff docs have been refreshed to v541 and staged for
  Windows owner/operator return; they remain handoff evidence only.
- Latest complete Windows side-by-side smoke: v535
- Latest bounded Windows canary: v541
- Latest partial Windows side-by-side setup/canary: v502, superseded by v523/v524/v525/v526/v532/v533/v535/v540/v541
- Latest source/package discovery fix: v523 package rebuild including v522 stale-yearless RCA bucket classification
- Latest source/package verifier hardening: v524/v525/v526 owner-return verifier requires
  Excel proof and ManualActionLog / JSONL outbox proof rows.
- Latest source/package verifier hardening: v541 packages and Windows-canary
  verifies short owner sign-off verification, expected package SHA/source
  commit checks, and `RC_ONLY` publication-lag exception semantics in
  `scripts/verify_stage6_return.py`.
- Latest operator UI supplement fix: v526 exposes extracted-PDF
  confirmation/supplement entry points and prefilled manual-entry saves.
- Latest source/package URL-discovery guardrail: v530 adds an optional
  `external` JSON-command search provider for official URL candidate discovery
  only. This is a Layer-3 fallback for official entrance/index candidates, not
  a PDF acquisition source. The release path must continue to start from the 47
  prefectural official confirmed-institution indexes, registered `SchoolSite`
  rows / exact official overrides, and bounded same-site disclosure expansion;
  v530 removes target-form/PDF search terms from URL completion and rejects
  direct document/PDF SERP hits before they can become `SchoolSite` rows.
- Initial docs-only owner/operator handoff staging: the Windows-staged v541
  owner docs ZIP includes the v541 first-read handoff, owner request, owner
  return fill sheet, release summary, short owner sign-off form, v541 Windows
  canary report, current release status, publication-lag exception record, OCR
  scope brief, and v1 known limitations. It was staged at
  `C:\EIDP-staging\v541-owner-docs-20260621` with SHA256
  `4ab692e47c0077eaedac91f340a561507ebaac79277bdce9db17d28ceea6c731`.
  This copied documentation only and did not modify active runtime, DB, PDFs,
  or Task Scheduler. The current owner handoff lane is the r3 docs-only
  false-reject refresh below.
- Latest docs-only false-reject handoff refresh: r3 is staged at
  `C:\EIDP-staging\v541-owner-docs-20260621-r3`, recorded in
  `docs/reports/2026-06-21-v541-owner-docs-r3-windows-staging.md`, and includes
  the false-reject RCA packet plus review worksheet. The remote verification
  confirmed SHA256
  `8b28d260a81f7854c4c6ecf678f7cbaaef26aa48139e4744f5d5f54dc018dc49`,
  `False-Reject RCA Worksheet`, `False-reject worksheet rules`, the
  return-verifier false-reject arguments, `NOT_READY`, and the scheduled task
  still executing `C:\Users\cyo20\EIDP-v527-69fe81f-env0\scripts\weekly_run.bat`.
  The superseded r2 ZIP and extracted directory were verified absent from
  Windows staging after cleanup.
- Latest strict-yield RCA summary: v541 Stage 6 evidence is summarized in
  `docs/reports/2026-06-21-v541-owner-signoff-verifier-windows-canary.md`. The top RCA lanes
  are `publication_lag_or_old_target_pdf` (`15` schools / `454` candidate
  rows), `target_form_without_year_evidence` (`2` / `10`),
  `school_identity_mismatch` (`2` / `48`), and
  `non_target_candidates_only` (`1` / `12`).
  The summary is now generated by `scripts/summarize_stage6_rca.py` from the
  Stage 6 evidence ZIP instead of being hand-derived.
  The next RCA order is fiscal-year mismatch / publication-lag or old target
  forms, non-target candidate noise, target-year-unverified candidates, and
  only then site-entry/fetch/identity gaps.
  Before labeling the blocker as an algorithm/model defect, run a
  rejection-bucket false-reject audit over fiscal-year mismatch, non-target
  filtering, target-year-unverified, and site-entry/fetch/identity candidates.
  The first audit packet is
  `docs/reports/2026-06-21-v541-false-reject-audit-packet.md`; it samples
  `12` rows from each large bucket and all rows from the smaller
  target-year-unverified and site-entry/fetch/identity buckets.
  The companion CSV worksheet
  `docs/reports/2026-06-21-v541-false-reject-review-sheet.csv` gives each row a
  stable `audit_row_id`, a machine-validated `decision` field, immutable row
  context checks, required reviewer/timestamp fields for completed decisions,
  notes for `false_reject` and `needs_operator_review`, and bucket-level
  decision counts for the RCA lanes. The v541 owner request and owner return
  fill sheet now describe the required worksheet return rules, and
  `scripts/verify_stage6_return.py` can validate the returned worksheet through
  its false-reject arguments.
- Latest post-v535 source hardening: the Sanko shared-origin disclosure probe
  fix keeps both `/disclosure/{slug}` and `/{slug}/disclosure` under the
  shared-origin throttle for school roots such as
  `https://www.sanko.ac.jp/omiya-beauty/`. It targets the remaining
  `non_target_candidates_only` RCA packet. The v536 Windows canary confirms the
  official disclosure page is reached, but school `41` remains
  `non_target_candidates_only` because the page only exposes school/program
  information PDFs such as `schoolinfo.pdf`, not an acceptable FY2026/R8 target
  document.
- Latest docs-only owner-decision handoff refresh: the Windows-staged v526
  owner docs ZIP now includes `docs/reports/2026-05-20-owner-v1.0-decision-brief.md`
  and `docs/runbooks/eidp-v526-owner-return-fill-sheet.md`, and
  `docs/runbooks/00-READ-ME-FIRST-v526.txt` points to them before the detailed
  request/template files. This copied documentation only and did not rebuild
  `dist/eidp-windows-v526.zip`.
- Latest docs-only campus-network guidance follow-up: `a8decad` generalizes
  the runbook and owner request from `10.109.*` to `10.x` private campus
  subnets including `10.209.*`, and documents standard `HTTP_PROXY` /
  `HTTPS_PROXY` / `NO_PROXY` handling for outbound PDF discovery behind a
  campus proxy. No package rebuild was made for this docs-only follow-up.
- Previous Windows owner-return remote check:
  `docs/reports/2026-05-20-v526-owner-return-remote-check.md` confirmed the
  refreshed v526 handoff was present on Windows, but the remote approval and
  owner/operator sign-off fields remain blank. The Windows-staged owner docs
  ZIP was refreshed to include this report, the target-yearless RCA spot check,
  the owner v1.0 A/B decision brief, and the v526 owner return fill sheet, and
  now has SHA256
  `28b12cbec895233b3ad97dff4c7757e2fb89cbd3130c4a604443a06bb8e38d29`.
- Latest Windows side-by-side smoke for v532:
  `docs/reports/2026-06-20-v532-full-windows-side-by-side-smoke.md` shows
  setup validation, active-task recovery proof, UI smoke, bounded weekly
  canary, Excel smoke, Stage 6 evidence bundle creation, and Stage 6 evidence
  verification all completed. The same report records the remaining blockers:
  strict FY2026 yield `12/50 (24.0%)`, missing owner sign-off, unapproved
  `publication_lag` exception, and failed v532 OCR runtime proof because the
  OCR add-on is missing.
- Latest OCR add-on recovery check:
  `docs/reports/2026-06-20-v532-ocr-addon-recovery-check.md` found no reusable
  OCR add-on ZIP or Windows Tesseract payload in the checked Mac,
  external-SSD, or Windows locations. v532 remains blocked for OCR runtime
  scope unless an approved add-on is restored/rebuilt or OCR is explicitly
  removed from the selected v1.0 release scope.
- Latest source/package MEXT official-index gate: v533 packages
  `data/authority-index/sources.csv`, the MEXT target-institution page
  snapshot, and `data/mext/target_institutions.xlsx`. The verifier rejects
  non-MEXT/search-like sources and requires official MEXT T0 catalog metadata,
  `auto_accept_allowed=yes`, and workbook thresholds for universities,
  specialty schools, short colleges, and kosen.
- Latest Windows side-by-side smoke for v533:
  `docs/reports/2026-06-20-v533-full-windows-side-by-side-smoke.md` shows
  setup validation, active-task recovery proof, UI smoke, bounded weekly
  canary, Excel smoke, Stage 6 evidence bundle creation, and Stage 6 evidence
  verification all completed. The same report records the remaining blockers:
  strict FY2026 yield `12/50 (24.0%)`, missing owner sign-off, unapproved
  `publication_lag` exception, and failed v533 OCR runtime proof because the
  OCR add-on is missing.
- Latest source/package AppleDouble-clean rebuild: v535 rebuilds after the
  v534 verifier rejected macOS AppleDouble wheelhouse sidecars. The v535
  package verifier reports `wheel_count=84`, MEXT workbook counts `3132`
  total, `769` universities, `2067` specialty schools, `239` short colleges,
  and `57` kosen, with `BUILD_INFO.git_dirty=false`.
- Latest Windows side-by-side smoke for v535:
  `docs/reports/2026-06-20-v535-full-windows-side-by-side-smoke.md` shows
  setup validation, active-task recovery proof, UI smoke, bounded weekly
  canary, Excel smoke, Stage 6 evidence bundle creation, and Stage 6 evidence
  verification all completed. The same report records the remaining blockers:
  strict FY2026 yield `12/50 (24.0%)`, missing owner sign-off, unapproved
  `publication_lag` exception, and unresolved OCR scope because the latest
  complete OCR runtime proof is not from v535.
- Latest source/package domain taxonomy and operator terminology fix: v532 is
  the post-merge `main` rebuild carrying the v531 domain work. It adds
  controlled `DocumentKind`, `ReviewTaskKind`, source-trust, and workflow-status
  enums; adds domain/status/UI/Agent-Reach boundary docs; verifies the local
  `UI-example/` as design reference only; and renames operator-facing UI labels
  to `学校キュー`, `申請書PDF確認`, `対象年度確認`, `Excel出力`,
  `公式索引管理`, and `情報公開ページ候補`.
- Latest FY2026/R8 Mac-side continuation canary:
  `docs/reports/2026-05-20-v521-mac-limit50-continuation-canary.md`
- Latest RCA reclassification report:
  `docs/reports/2026-05-20-v522-stale-yearless-rca-bucket-source.md`
- Latest same-domain FY2026 negative probe:
  `docs/reports/2026-05-20-v522-same-domain-2026-negative-probe.md`
- Release verdict: blocked by FY2026/R8 strict yield, missing owner real Windows
  cycle, and unapproved `publication_lag` exception.

Passing unit tests, package verification, and a complete Windows smoke are
necessary but not sufficient for completion. They do not by themselves prove
the current FY2026/R8 60-70% target-PDF acquisition line or owner sign-off.

## Prompt-To-Artifact Checklist

| Requirement | Evidence checked | Status |
| --- | --- | --- |
| 47 prefecture official-list seeds are packaged and usable | v541 package verifier in `logs/win-v541-owner-signoff-release-path-gates-20260621.json`: `prefecture_seed_rows=47`, `prefecture_seed_school_rows_total=2148` | PASS |
| 1,700+ vocational-school scope | v541 Windows setup validator in `docs/reports/2026-06-21-v541-owner-signoff-verifier-windows-canary.md`: `school_count=2418`, `school_fiscal_year_status_count=2418`, SQLite integrity `ok` | PASS |
| 700-ish university scope | v541 package verifier requires the MEXT T0 target-institution catalog and workbook in the ZIP. `verify_windows_distribution.py dist/eidp-windows-v541.zip --json` reported `mext_target_university_rows=769`, `mext_target_specialty_rows=2067`, `mext_target_short_college_rows=239`, `mext_target_kosen_rows=57`, and `mext_target_total_rows=3132`. This proves the official source-catalog/package gate only; university target-document discovery, extraction, and Excel mapping are still not proven. | PASS for T0 index/package gate, PARTIAL for full university lane |
| Current rolling FY is FY2026/Reiwa 8 | v541 Windows canary summary `logs/win-v541-e62d074-canary/20260620_152248-summary.json`: `current_fy=2026`, `school_type=専門学校`, `selection_mode=target_missing` | PASS |
| Strict mode excludes old-year fallback from success | v541 Windows canary summary keeps `ship_gate_status=below_gate` at strict/Excel-ready `12/50 (24.0%)`; old/stale target forms are not counted as release success | PASS for contract, FAIL for release yield |
| Current FY2026 strict target-PDF/Excel-ready yield is `>= 60%` | v541 and v540 Windows limit-50 canaries: strict/Excel-ready `12/50 (24.0%)`; v535/v533/v532 Windows limit-50 canaries: strict/Excel-ready `12/50 (24.0%)`; v526/v525/v524/v523 Windows limit-50 canaries: strict/Excel-ready `5/50 (10.0%)`; v515 Mac continuation canary from the v513 isolated DB: strict `2/50 (4.0%)`; v516/v519/v521 target-missing/continuation canaries remained `0/50 (0.0%)`; v522 same-domain `2025 -> 2026` and short-year/R7 replacement probe found `404` for all 47 expanded candidates; production-scale upper-bound proof: max possible `39.3%` after 607/1000 schools | FAIL |
| Operator manual workload is `<= 30%` for current FY | v541/v540 Windows limit-50 operator-reviewable `47/50 (94.0%)`; v535/v533/v532 Windows limit-50 operator-reviewable `47/50 (94.0%)`; v526/v525/v524/v523 Windows limit-50 operator-reviewable `50/50 (100.0%)`; v516 target-missing canary operator-reviewable `49/50 (98.0%)`; strict Excel-ready success is still below gate and owner real-cycle workload proof is missing | FAIL |
| Mature-year exception input exists | `logs/mature-year-acquisition-proof-fy2025-release-exception-v497-20260519.json`: FY2025 denominator `1000`, strict/Excel-ready `60.0%`, operator-reviewable `79.8%`, manual workload `20.2%` | PASS as exception input only |
| Publication-lag exception is approved if release uses the mature-year lane | `docs/reports/2026-05-19-publication-lag-release-exception-record.md`: `Status: NOT_APPROVED`, `Decision: NOT_APPROVED` | BLOCKED |
| PDF extraction stack is packaged | v541 setup validator has `wheel_count=84`; v526 Windows OCR runtime proof is `ok=true` with Tesseract runtime and `jpn` / `jpn_vert` tessdata present. v541 does not have a complete OCR runtime proof, so OCR remains unresolved if kept in v1.0 scope. | PASS for core, BLOCKED for v541 OCR scope |
| Confidence `>= 0.70` gate exists | v541 current `main` CI run `27874800210` passed Python quality gates and Ship gate contract; confidence/export/review tests are covered by the unit suite | PASS for code contract, PARTIAL for production OCR corpus |
| `DepartmentYearly` and `SupportRecipient` append-only paths exist | v541 install validator confirms required tables including `department_yearly`, `support_recipient`, and `manual_action_log`; v541 canary processed `15` documents into `122` new departments and `129` yearly upserts | PASS for code/schema, PARTIAL for real operator workflow |
| Extracted rows can be confirmed/supplemented | `docs/reports/2026-05-20-v526-extracted-confirmation-package.md`: extracted `confirmed_target` rows get `抽出済内容を確認・補足`; the PDF確認・手入力 form preloads current extracted data and saves through existing append-only manual-entry/audit paths | PASS for code/UI contract, PARTIAL for real operator workflow |
| Excel transfer works | v535 Excel smoke: `win-v535-stage6-v535-excel-summary-clean-20260620.json` is `ok=true`; master workbook length `3,746,064`, competition workbook length `121,897`, gap CSV length `48,116`, and competition export recorded `excel_ready_schools=12` | PASS |
| Operator actions are auditable in `ManualActionLog` | v502 install validator confirms the table; v503 adds `operator_settings_saved` audit coverage for the settings page with API-key redaction; v504 adds `excel_preview_generated` audit coverage for Excel preview generation; v505 adds `school_year_tasks_rebuilt` audit coverage for task-board rebuilds; v506 adds `operator_url_submitted` and `operator_url_bulk_imported` audit coverage for manual URL registration; v507 adds `prefecture_remark_approved` and `prefecture_remark_rejected` audit coverage for official-list remark decisions; v508 adds `excel_export_generated` audit coverage for master and competition Excel exports; v509 exposes the current audit action and target-table vocabulary in the audit-log filters; v510 adds `school_alias_approved` audit coverage for approved school-alias proposals; v511 adds `proposal_decision_recorded` audit coverage for proposal review decisions; v512 adds `bug_report_generated` audit coverage for local support ZIP generation without storing raw operator notes; v524 hardens `scripts/verify_stage6_return.py` so returned owner evidence must include audit page proof, numeric `manual_action_log` count, after-flush JSONL outbox count `0`, audit-flush status, and `JSONL action_id` duplicate status; current owner real-cycle audit counts and sign-off are still missing | PASS for code/verifier contract, BLOCKED for real owner evidence |
| Windows ZIP double-click setup works | v541 setup and validation recorded in `docs/reports/2026-06-21-v541-owner-signoff-verifier-windows-canary.md`: after-setup validator `ok=true`, `school_count=2418`, SQLite integrity `ok` | PASS |
| Browser UI runs offline on Windows | v535 UI smoke: `win-v535-stage6-v535-ui-smoke-20260620.json` is `ok=true`, port `8535`, health `200/ok`, root `200`, stopped cleanly, no listener remained after stop | PASS |
| Active scheduled-task safety is preserved | v541 recovery check `logs/win-v541-e62d074-canary/stage6-recovery-20260621-002217.json`: `ok=true`, active weekly task still points to `C:\Users\cyo20\EIDP-v527-69fe81f-env0\scripts\weekly_run.bat`; v541 setup was run with `EIDP_REGISTER_WEEKLY_TASK=0` | PASS for no accidental promotion, NOT release evidence |
| Stage 6 evidence bundle and verifier pass | v541 evidence ZIP and verifier: `logs/win-v541-e62d074-canary/stage6-evidence-20260620-153655.zip`, `logs/win-v541-e62d074-canary/stage6-evidence-verify-20260621-003707.json`, and Mac-side `verify_stage6_evidence.py` with `ok=true`; required labels present and no unsafe/forbidden entries | PASS |
| v526/v525/v524/v523 RCA is current | `docs/reports/2026-05-20-v526-extracted-confirmation-package.md`, `docs/reports/2026-05-20-v525-rc-metadata-package.md`, `docs/reports/2026-05-20-v524-full-windows-side-by-side-smoke.md`, and `docs/reports/2026-05-20-v523-full-windows-side-by-side-smoke.md`: v526/v525/v524/v523 repeat the same strict `5/50 (10.0%)`, operator-reviewable `50/50 (100.0%)`, `ship_gate_status=below_gate` blocker; v526 discovery stats record `pre_filtered_non_target_hint=631`, `fiscal_year_mismatch=267`, `classified_non_target=88`, `no_candidates_found=8`, `target_fiscal_year_not_detected=5`, and `http_error_httpstatuserror=1`, with no `candidate_school_mismatch` in the v526 Windows run | PASS for RCA, FAIL for yield |
| Weekly selected-school denominator actually gets crawled | v514 focused isolated Mac smoke `target-year-discovery-after-sitecount-fix/20260519_231930-summary.json`: selected NEEC school IDs 1-3 were crawled (`crawled=3`) and remained reviewable, not strict FY2026 successes; v516 selection probe excludes already confirmed target schools 4 and 7 from the target-missing queue while preserving a 50-school queue; v517 targeted school ID 55 smoke confirms the new exact override is crawled and yields FY2019-FY2025 target-form evidence instead of corporation-only non-target evidence; v518 packages that case as discovery gold-set regression evidence; v519 filters vocational-practice basic-info PDFs out of target-form review; v519 Mac continuation canary with copied URL sources crawls 58 site rows for 50 selected schools and moves school ID 55 to `publication_lag_or_old_target_pdf`; v520 adds exact Katayanagi crawl entries while preserving NEEC no-year PDFs as reviewable, not strict successes; v521 suppresses same-school `corporation_pattern` rows when exact school-domain overrides exist, reducing the Katayanagi limit-3 crawl from 6 to 3 and candidate-school mismatches from 69 to 0; the v526/v525/v524/v523 Windows limit-50 canaries each download 5 strict/current PDFs and keep all 50 selected schools reviewable | PASS for code/evidence contract, FAIL for strict yield |
| Owner real Windows cycle and sign-off are complete | No completed owner KPI/sign-off template or owner-return verifier pass is present; v526 negative verifier probe blocks missing Excel ready/consistency proof, audit/outbox proof rows, and unapproved `publication_lag` fields. v541/v540 bounded Windows canaries and v540 owner-docs staging are runtime/handoff evidence, not owner/operator sign-off. | BLOCKED |
| v1.0 tag is allowed | PR #8 is merged into `main`, but FY2026 strict proof, owner real cycle, and exception approval are incomplete | BLOCKED |

## Fresh Local Verification In This Audit Pass

- `uv run python -m eidp.cli eval-discovery-gold --predictions data/discovery-gold-set/expected-predictions.jsonl --json --fail-on-regression` returned 45 exact matches and 0 failures.
- `uv run pytest tests/unit/test_discovery_gold_set_seed.py tests/unit/test_discovery_gold_set_summary.py tests/unit/test_discovery_gold_set.py tests/unit/test_discovery_gold_set_eval.py tests/unit/test_cli_discovery_gold_set.py tests/unit/test_cli_eval_discovery_gold.py -q` returned `49 passed`.
- v503 settings-audit focused verification is recorded in `docs/reports/2026-05-20-v503-settings-audit-package.md`.
- v504 Excel-preview audit focused verification is recorded in `docs/reports/2026-05-20-v504-excel-preview-audit-package.md`.
- v505 school-year task rebuild audit focused verification is recorded in `docs/reports/2026-05-20-v505-school-task-rebuild-audit-package.md`.
- v506 operator URL registration audit focused verification is recorded in `docs/reports/2026-05-20-v506-operator-url-audit-package.md`.
- v507 prefecture remark decision audit focused verification is recorded in `docs/reports/2026-05-20-v507-prefecture-remark-audit-package.md`.
- v508 Excel export audit focused verification is recorded in `docs/reports/2026-05-20-v508-excel-export-audit-package.md`.
- v509 audit-log filter vocabulary verification is recorded in `docs/reports/2026-05-20-v509-audit-log-filter-package.md`.
- v510 school alias approval audit verification is recorded in `docs/reports/2026-05-20-v510-school-alias-audit-package.md`.
- v511 proposal review decision audit verification is recorded in `docs/reports/2026-05-20-v511-proposal-decision-audit-package.md`.
- v512 bug-report ZIP audit verification is recorded in `docs/reports/2026-05-20-v512-bug-report-audit-package.md`.
- v513 Sanko disclosure slug-probe verification is recorded in `docs/reports/2026-05-20-v513-sanko-disclosure-probe-package.md`.
- v514 weekly selected-site count verification is recorded in `docs/reports/2026-05-20-v514-weekly-selected-site-count-package.md`.
- v514 Mac continuation canary is recorded in `docs/reports/2026-05-20-v514-mac-continuation-canary.md`: strict `2/50 (4.0%)`, operator-reviewable `47/50 (94.0%)`, and `ship_gate_status=below_gate`.
- v515 Sanko child override verification is recorded in `docs/reports/2026-05-20-v515-sanko-child-overrides-package.md`: strict `2/50 (4.0%)`, operator-reviewable `50/50 (100.0%)`, no residual `non_target_candidates_only` RCA bucket, and `ship_gate_status=below_gate`.
- v515 post-docs-only release gate is recorded in `logs/win-v515-stage6-v515-post-docs-only-gates-20260520.json`: `ok=true`, `docs_only_stale=true`, full unit `1891 passed`.
- v516 target-missing queue verification is recorded in `docs/reports/2026-05-20-v516-weekly-target-missing-selection-package.md`: current-FY `review_pending` target PDFs no longer re-enter the target-missing acquisition queue, and v516 full unit `1892 passed`.
- v516 post-docs-only release gate is recorded in `logs/win-v516-stage6-v516-post-docs-only-gates-20260520.json`: `ok=true`, `docs_only_stale=true`, full unit `1892 passed`.
- v517 remaining Sanko child override verification is recorded in `docs/reports/2026-05-20-v517-remaining-sanko-child-overrides-package.md`: school ID 55 now crawls `https://www.sanko.ac.jp/tokyo-child/`, moves from corporation-only non-target evidence to FY2019-FY2025 publication-lag evidence, and v517 full unit `1892 passed`.
- v517 post-docs-only release gate is recorded in `logs/win-v517-stage6-v517-post-docs-only-gates-20260520.json`: `ok=true`, `docs_only_stale=true`, full unit `1892 passed`.
- v518 gold-set publication-lag verification is recorded in `docs/reports/2026-05-20-v518-gold-set-publication-lag-package.md`: the Sanko Tokyo child publication-lag case is packaged as a gold-set entry, expected predictions are 45/45 exact, and v518 full unit `1892 passed`.
- v518 post-docs-only release gate is recorded in `logs/win-v518-stage6-v518-post-docs-only-gates-20260520.json`: `ok=true`, `docs_only_stale=true`, full unit `1892 passed`.
- v519 vocational-practice basic-info verification is recorded in `docs/reports/2026-05-20-v519-vocational-practice-basic-info-filter-package.md`: four FY2026 current-hint RCA sample PDFs now classify as `non_target`, and v519 full unit `1893 passed`.
- v519 post-docs-only release gate is recorded in `logs/win-v519-stage6-v519-post-docs-only-gates-20260520.json`: `ok=true`, `docs_only_stale=true`, full unit `1893 passed`.
- v519 Mac limit-50 continuation canary is recorded in `docs/reports/2026-05-20-v519-mac-limit50-continuation-canary.md`: URL sources loaded, 5 school overrides inferred, `crawled=58`, strict `0/50 (0.0%)`, operator-reviewable `50/50 (100.0%)`, RCA buckets `16 publication_lag_or_old_target_pdf` and `4 target_form_without_year_evidence`, and `ship_gate_status=below_gate`.
- v520 Katayanagi URL boundary verification is recorded in `docs/reports/2026-05-20-v520-katayanagi-url-boundary-package.md`: exact Katayanagi URL overrides load, NEEC no-year `portal/syllabus` PDFs cannot use `school_domain_override_disclosure` trusted-year fill, limit-3 smoke remains strict `0/3 (0.0%)`, operator-reviewable `3/3 (100.0%)`, `ship_gate_status=below_gate`, and v520 full unit `1895 passed`.
- v521 school-override corporation suppression is recorded in `docs/reports/2026-05-20-v521-school-override-corporation-suppression-package.md`: same-school `corporation_pattern` rows are skipped when usable `school_domain_override` rows are in scope, Katayanagi limit-3 `crawled=3`, `candidate_school_mismatch=0`, strict `0/3 (0.0%)`, operator-reviewable `3/3 (100.0%)`, PDF discovery unit `227 passed`, and full unit `1896 passed`.
- v521 Mac limit-50 continuation canary is recorded in `docs/reports/2026-05-20-v521-mac-limit50-continuation-canary.md`: URL sources loaded, 8 school overrides inferred, `crawled=54`, `found=50`, `failed=0`, `candidate_school_mismatch=0`, strict `0/50 (0.0%)`, operator-reviewable `50/50 (100.0%)`, RCA buckets `17 publication_lag_or_old_target_pdf` and `3 target_form_without_year_evidence`, and `ship_gate_status=below_gate`.
- v522 stale-yearless RCA bucket verification is recorded in `docs/reports/2026-05-20-v522-stale-yearless-rca-bucket-source.md`: stale-labeled no-year/image-only Sanko school ID 44 evidence now classifies as `publication_lag_or_old_target_pdf`, genuine NEEC no-year target forms remain in `target_form_without_year_evidence`, the recomputed v521 top 20 RCA split is `18 publication_lag_or_old_target_pdf` and `2 target_form_without_year_evidence`, and full unit `1897 passed`.
- v522 same-domain FY2026 negative probe is recorded in `docs/reports/2026-05-20-v522-same-domain-2026-negative-probe.md`: 38 simple `2025 -> 2026` candidates and 47 expanded short-year/R7 variants were generated from v521 FY2025 target-form evidence; HEAD and ranged GET both returned `404` for all 47 expanded candidates.
- Fresh read-only Windows connectivity recheck on 2026-05-20 is recorded in `docs/reports/2026-05-20-v522-windows-connectivity-recheck.md`: the first probe found no usable SSH/SMB/RDP/WinRM service. After the user restarted Windows SSH, `ssh win` worked again and v523 Windows side-by-side validation completed.
- v523 current-head package verification is recorded in `docs/reports/2026-05-20-v523-current-head-package.md`: package `dist/eidp-windows-v523.zip`, SHA256 `5d47ca9e016aa6aadf3608b5799c773a769af585d158813eada1f80cebe762ce`, package/source commit `9a5cefc74751ec849daff86d68ff552f79f376e0`, core + OCR add-on verifier `ok=true`, non-Windows release gate `ok=true`, full unit `1897 passed`, and 45/45 discovery-gold expected predictions.
- v523 full Windows side-by-side smoke is recorded in `docs/reports/2026-05-20-v523-full-windows-side-by-side-smoke.md`: setup/validate/OCR runtime/UI/Excel/weekly limit-50/Stage 6 evidence verifier/residual-cleanup dry run/recovery all returned `ok=true`; the weekly canary crawled 59 site rows, found 50 candidate PDFs, downloaded 5 strict FY2026/R8 PDFs, processed 5 documents into 106 departments and 107 yearly rows, reported strict `5/50 (10.0%)`, operator-reviewable `50/50 (100.0%)`, and kept `ship_gate_status=below_gate`.
- v523 owner/operator request is prepared in `docs/runbooks/eidp-v523-owner-request-20260520.txt`: it points to the v523 package, SHA, side-by-side root, Windows smoke evidence, required return files, KPI/sign-off fields, and the `publication_lag`/strict-FY release-decision boundary.
- The `publication_lag` release-exception record is refreshed to the v526 evidence packet in `docs/reports/2026-05-19-publication-lag-release-exception-record.md`, but remains `NOT_APPROVED`.
- Negative v523 return-verifier probe is recorded in `logs/win-v523-stage6-v523-verify-stage6-return-not-approved-exception-20260520.json` with rc `1`: the refreshed exception packet still fails on `Status must be APPROVED`, `Decision must be APPROVED`, placeholder approval fields, and missing owner/operator sign-off.
- Temporary positive v523 return-verifier probe is recorded in `logs/win-v523-stage6-v523-verify-stage6-return-positive-exception-probe-20260520.json`: with a temporary filled owner E2E template and temporary `APPROVED` exception copy under `_temp/`, the verifier returns `ok=true`, proving the approval/sign-off path is internally consistent but not approved in the real record.
- v523 post-docs-only release gate is recorded in `logs/win-v523-stage6-v523-post-docs-only-gates-20260520.json`: `ok=true`, `docs_only_stale=true`, full unit `1897 passed`.
- v523 campus network probe is recorded in `docs/reports/2026-05-20-v523-campus-network-probe.md`: `ssh win hostname` returned `junming`; the active Windows Wi-Fi profile was `Private`, Wi-Fi IPv4 was `192.168.0.9/24`, and the OpenSSH inbound firewall rule was enabled. This confirmed the then-current remote-management path but does not remove the FY2026/R8 yield or owner sign-off blockers.
- v523 owner-return verifier coverage audit is recorded in `docs/reports/2026-05-20-v523-owner-return-verifier-coverage-audit.md`: `verify_stage6_return.py` enforces last_run KPI consistency, Stage 6 evidence labels, selected E2E KPI rows, sign-off blocks, approved `publication_lag` records, and mature-year proof, but does not machine-enforce Excel proof or ManualActionLog / JSONL outbox consistency. A green return verifier is therefore necessary but not sufficient for owner-cycle acceptance. The script is packaged in `dist/eidp-windows-v523.zip`, so hardening those checks would require a new source/package lane rather than another v523 docs-only update.
- v523 manual owner-return review companion is prepared in `docs/runbooks/eidp-v523-owner-return-manual-review-checklist.md`: it covers Excel proof, ManualActionLog / JSONL outbox proof, append-only `DepartmentYearly` / `SupportRecipient` evidence, and OCR-scope evidence that remain required but not machine-enforced by the v523 packaged return verifier.
- v523 owner/operator first-read handoff is prepared in `docs/runbooks/00-READ-ME-FIRST-v523.txt`: it lists the selected package, SHA, side-by-side root, current active v485 root to preserve, required evidence, safety red lines, and the release-decision boundary.
- v523 owner/operator docs were staged on Windows under `C:\EIDP-staging\v523-owner-docs-20260520`, recorded in `docs/reports/2026-05-20-v523-owner-docs-windows-staging.md`: the transferred ZIP SHA256 is `11faa8be238c6ae6ff91652af8de7734f1465e135b53358c65365ca42fba6989`, and the extracted docs include the v523 first-read handoff, owner request, manual review checklist, E2E template, package report, Windows smoke report, exception record, objective checklist, and release status. A post-staging read-only recheck confirmed `EIDP Weekly Run` still executes `C:\Users\cyo20\EIDP-v485-70e3db4\scripts\weekly_run.bat`, while both v485 and v523 roots remain present. This copies docs only and does not modify active runtime, DB, PDFs, or Task Scheduler.
- v524 owner-return verifier hardening is recorded in `docs/reports/2026-05-20-v524-owner-return-verifier-hardening-package.md`: the new red test first failed because the old verifier accepted missing Excel/audit proof, the focused verifier suite now returns `14 passed`, the packaging contract slice returns `100 passed`, v524 package/source verification returns `ok=true`, full unit returns `1898 passed`, and the real unapproved owner template is rejected with new missing Excel/audit proof errors.
- v524 full Windows side-by-side smoke is recorded in `docs/reports/2026-05-20-v524-full-windows-side-by-side-smoke.md`: setup/validate/OCR runtime/UI/weekly limit-50/Excel/Stage 6 evidence verifier/residual-cleanup dry run/recovery all returned `ok=true`; the weekly canary remains strict `5/50 (10.0%)`, operator-reviewable `50/50 (100.0%)`, and `ship_gate_status=below_gate`.
- v525 RC metadata package and Windows smoke evidence is recorded in `docs/reports/2026-05-20-v525-rc-metadata-package.md`: package `dist/eidp-windows-v525.zip`, SHA256 `5e0ed056e37c5b105b38de033062c4f7a7a8f0966509adb0251cade8f151efc4`, package/source commit `73392f7a246b4dcd7396524b87e2db48b25dec61`, version `1.0.0rc1`, non-Windows release gate `ok=true`, Windows setup/validate/OCR runtime/UI/weekly limit-50/Excel/Stage 6 evidence verifier/residual-cleanup dry run/recovery all returned `ok=true`, and the weekly canary remains strict `5/50 (10.0%)`, operator-reviewable `50/50 (100.0%)`, `ship_gate_status=below_gate`.
- v525 owner/operator request is prepared in `docs/runbooks/eidp-v525-owner-request-20260520.txt`: it points to the v525 package, SHA, side-by-side root, Windows smoke evidence, required return files, KPI/sign-off fields, and the `publication_lag`/strict-FY release-decision boundary.
- v525 owner/operator docs were staged on Windows under `C:\EIDP-staging\v525-owner-docs-20260520`, recorded in `docs/reports/2026-05-20-v525-owner-docs-windows-staging.md`: the transferred ZIP SHA256 is `5b66839c24dd73a68092f823a584475a44779be1f1ae59947284f81af6dab4bb`, and the extracted docs include the v525 first-read handoff, owner request, E2E template, release admin checklist, package report, exception record, objective checklist, and release status. A post-staging read-only recheck confirmed `EIDP Weekly Run` still executes `C:\Users\cyo20\EIDP-v485-70e3db4\scripts\weekly_run.bat`, while both v485 and v525 roots remain present. This copies docs only and does not modify active runtime, DB, PDFs, or Task Scheduler.
- Negative v525 return-verifier probe is recorded in `logs/win-v525-stage6-v525-verify-stage6-return-not-approved-exception-20260520.json` with rc `1`: the refreshed v525 exception packet still fails on `Status must be APPROVED`, `Decision must be APPROVED`, placeholder approval fields, missing owner/operator KPI and sign-off rows, and missing Excel/audit proof rows.
- v526 extracted confirmation package and Windows smoke evidence is recorded in `docs/reports/2026-05-20-v526-extracted-confirmation-package.md`: package `dist/eidp-windows-v526.zip`, SHA256 `4a03e975243d1327e79470de82fe468814c42a66e2749ec32c3251176da9ebca`, package/source commit `5b30eb78edc331f992c1a99fdc7611174791ab87`, extracted `confirmed_target` rows now expose `抽出済内容を確認・補足`, non-Windows release gate `ok=true`, full unit `1901 passed`, Windows setup/validate/OCR runtime/UI/weekly limit-50/Excel/Stage 6 evidence verifier/residual-cleanup dry run/recovery all returned `ok=true`, and the weekly canary remains strict `5/50 (10.0%)`, operator-reviewable `50/50 (100.0%)`, `ship_gate_status=below_gate`.
- v526 owner/operator request is prepared in `docs/runbooks/eidp-v526-owner-request-20260520.txt`: it points to the v526 package, SHA, side-by-side root, extracted confirmation/supplement UI behavior, Windows smoke evidence, required return files, KPI/sign-off fields, and the `publication_lag`/strict-FY release-decision boundary.
- v526 owner/operator docs were staged on Windows under `C:\EIDP-staging\v526-owner-docs-20260520`, recorded in `docs/reports/2026-05-20-v526-owner-docs-windows-staging.md`: the final ZIP SHA256 is recorded in that external staging report rather than embedded inside the ZIP, and the extracted docs include the v526 first-read handoff, owner request, Windows runbook with `10.x` / `10.209.*` campus-network guidance, package report, target-yearless RCA spot check, exception record, objective checklist, release status, and post-reboot active-task preflight. A post-staging read-only recheck confirmed `EIDP Weekly Run` still executes `C:\Users\cyo20\EIDP-v485-70e3db4\scripts\weekly_run.bat`, while both v485 and v526 roots remain present. This copies docs only and does not modify active runtime, DB, PDFs, or Task Scheduler.
- v526 runtime boundary recheck is recorded in `docs/reports/2026-05-20-v526-runtime-boundary-recheck.md`: the active weekly task still points to v485, no Streamlit listeners remained on ports `8523/8524/8525/8526`, and both the v526 side-by-side root and v526 staged docs directory were present.
- Negative v526 return-verifier probe is recorded in `logs/win-v526-stage6-v526-verify-stage6-return-not-approved-exception-20260520.json` with rc `1`: the refreshed v526 exception packet still fails on `Status must be APPROVED`, `Decision must be APPROVED`, placeholder approval fields, missing owner/operator KPI and sign-off rows, and missing Excel/audit proof rows.
- v526 target-yearless RCA spot check is recorded in `docs/reports/2026-05-20-v526-target-yearless-rca-spot-check.md`: the five `target_fiscal_year_not_detected` rows are NEEC no-year target-form PDFs for school IDs 1/2 and one Sanko image-only/stale-context PDF for school ID 44; the official pages do not provide machine-verifiable FY2026/Reiwa 8 evidence, so none can safely raise the v526 strict yield.
- Local v530 package gate is recorded in
  `logs/win-v530-stage6-v530-non-windows-release-gates-20260619.json`:
  package `dist/eidp-windows-v530.zip`, SHA256
  `6344e6b9c2fea850cb50425410f2e0a5ad9c6626ff31fca9fee5f9f8014604a6`,
  package/source commit `9331216022e1904361ed8d11d0e24da81637d46a`,
  `package_source_check.ok=true`, `source_dirty=false`, full unit
  `1936 passed`, validator/distribution unit `188 passed`, mypy/ruff pass,
  discovery gold 45/45 exact, package verification pass, and package
  `BUILD_INFO.json` reports `git_dirty=false`.
- Historical local v531 pre-merge package gate is recorded in
  `logs/win-v531-domain-taxonomy-release-gates-20260619.json`: package
  `dist/eidp-windows-v531.zip` before local ZIP cleanup, SHA256
  `dd9211a465a31d66d2bde865860d2cee6d6f79b61f416b495e2ce40c31f66c16`,
  package/source commit `c0dda09a21c4fe34ae6b28d453bb7783df8abea3`,
  `package_source_check.ok=true`, `source_dirty=false`, full unit
  `1946 passed`, validator/distribution unit `188 passed`, mypy/ruff pass,
  discovery gold 45/45 exact, package verification pass, and package
  `BUILD_INFO.json` reports `git_dirty=false`.
- Local v532 post-merge `main` package gate is recorded in
  `logs/win-v532-main-post-merge-release-gates-20260619.json`: package
  `dist/eidp-windows-v532.zip`, SHA256
  `9743cc65c21ada06b6a1d6c8b50ba67cdaffa4f3942256ccd072d4469fa0d6c7`,
  package/source commit `723a5072f63e8a874bef85cc52d869f5e6daff15`,
  `package_source_check.ok=true`, `source_dirty=false`, `stale=false`, full
  unit `1946 passed`, validator/distribution unit `188 passed`, mypy/ruff
  pass, discovery gold 45/45 exact, package verification pass, and package
  `BUILD_INFO.json` reports `git_branch=main`, `git_dirty=false`.
- Local storage cleanup after v532 removed superseded generated Windows ZIPs
  `dist/eidp-windows-v527.zip` through `dist/eidp-windows-v531.zip` and their
  `.sha256` sidecars. Later cleanup after v535 removed the invalid v534 core
  ZIP and sidecar. Later cleanup after v540 pruned superseded v539. `dist/`
  now keeps v535, v536, v540, v541, the latest alias, the current v540
  owner-docs handoff ZIP, and `wheelhouse/` for rebuild support. The
  superseded v532 owner-docs ZIP and macOS AppleDouble `._*` sidecars created
  during v541 packaging were removed.
- Local artifact storage now uses the external SSD mounted at
  `/Volumes/M1nG-ssd`: repository paths `dist` and `logs` are symlinks to
  `/Volumes/M1nG-ssd/EIDP-artifacts/dist` and
  `/Volumes/M1nG-ssd/EIDP-artifacts/logs`. The v532 ZIP verifier and SHA checks
  still pass through the symlinked `dist/...` paths.
- Local v533 MEXT T0 authority-index package gate is recorded in
  `docs/reports/2026-06-20-v533-mext-authority-index-package.md` and
  `logs/win-v533-stage6-v533-non-windows-release-gates-20260620.json`:
  package `dist/eidp-windows-v533.zip`, SHA256
  `0d4ca81a9032db1d8b98bf69ba76a4181d99d6bb8cd0091de22df211dc5d5f57`,
  package/source commit `f83f1dc5439156bb9909ea1df5132bed3a7e9b85`,
  `package_source_check.ok=true`, `source_dirty=false`, package verification
  pass, validator/distribution unit `191 passed`, mypy/ruff pass, discovery
  gold 45/45 exact, and MEXT workbook counts `3132` total, `769` universities,
  `2067` specialty schools, `239` short colleges, and `57` kosen.
- v533 full Windows side-by-side smoke is recorded in
  `docs/reports/2026-06-20-v533-full-windows-side-by-side-smoke.md`: setup
  validation, active-task recovery proof, UI smoke, weekly limit-50 canary,
  Excel smoke, Stage 6 evidence creation, and Stage 6 evidence verification
  completed; strict/Excel-ready FY2026 yield is `12/50 (24.0%)`,
  operator-reviewable is `47/50 (94.0%)`, `ship_gate_status=below_gate`, and
  OCR runtime proof failed because the OCR add-on is missing.
- Local v535 AppleDouble-clean package gate is recorded in
  `docs/reports/2026-06-20-v535-appledouble-clean-package.md` and
  `logs/win-v535-stage6-v535-non-windows-release-gates-20260620.json`:
  package `dist/eidp-windows-v535.zip`, SHA256
  `72ef94f35a2cd482eb9650d1a466cb8441f7d96a660a8901710d96603e7d8e9f`,
  package/source commit `d742327570a08a8f9d6ade7adfc81da8940294b4`,
  `package_source_check.ok=true`, `source_dirty=false`, `stale=false`, full
  unit `2016 passed`, validator/distribution unit `196 passed`, mypy/ruff
  pass, discovery gold 45/45 exact, package verification pass, and package
  `BUILD_INFO.json` reports `git_dirty=false`.
- v535 full Windows side-by-side smoke is recorded in
  `docs/reports/2026-06-20-v535-full-windows-side-by-side-smoke.md`: setup
  validation, active-task recovery proof, UI smoke, weekly limit-50 canary,
  Excel smoke, Stage 6 evidence creation, and Stage 6 evidence verification
  completed; strict/Excel-ready FY2026 yield is `12/50 (24.0%)`,
  operator-reviewable is `47/50 (94.0%)`, `ship_gate_status=below_gate`, and
  OCR scope remains unresolved because the latest complete OCR proof is not
  from v535.
- v541 owner/operator docs were staged on Windows under
  `C:\EIDP-staging\v541-owner-docs-20260621`, recorded in
  `docs/reports/2026-06-21-v541-owner-docs-windows-staging.md`. A post-staging
  check confirmed the required v541 docs are present, including
  `eidp-v541-release-summary.md` and `eidp-v541-owner-signoff.md`,
  `current-release-status.md` contains `NOT_READY`, the publication-lag
  exception record contains `NOT_APPROVED`, the active weekly task still points
  to `C:\Users\cyo20\EIDP-v527-69fe81f-env0\scripts\weekly_run.bat`, and the
  superseded v540 docs ZIP/directory were removed from Windows staging.
- v540 owner/operator docs r2 were previously staged on Windows under
  `C:\EIDP-staging\v540-owner-docs-20260620-r2`, recorded in
  `docs/reports/2026-06-20-v540-owner-docs-r2-windows-staging.md`. The r2 ZIP
  SHA256 is
  `e5ee3df87e962321ff8a4f37dd3ec9becc776078bcb93cdeed8bcd907751be8f`.
  A post-staging check confirmed the required v540 docs are present, including
  `eidp-v540-release-summary.md` and `eidp-v540-owner-signoff.md`,
  `current-release-status.md` still contains `NOT_READY`, the publication-lag
  exception record still contains `NOT_APPROVED`, the active weekly task still
  points to `C:\Users\cyo20\EIDP-v527-69fe81f-env0\scripts\weekly_run.bat`, and
  the superseded r1 docs ZIP/directory were removed from Windows staging.
- v532 Windows connectivity recheck and follow-up are recorded in
  `docs/reports/2026-06-20-v532-windows-connectivity-recheck.md`: the initial
  approved `ssh -o BatchMode=yes -o ConnectTimeout=5 win hostname` timed out
  against `192.168.0.9:22`, then SSH was restored and v532 side-by-side smoke
  completed.
- v532 full Windows side-by-side smoke is recorded in
  `docs/reports/2026-06-20-v532-full-windows-side-by-side-smoke.md`: setup
  validation, active-task recovery proof, UI smoke, weekly limit-50 canary,
  Excel smoke, Stage 6 evidence creation, and Stage 6 evidence verification
  completed; strict/Excel-ready FY2026 yield is `12/50 (24.0%)`,
  operator-reviewable is `47/50 (94.0%)`, `ship_gate_status=below_gate`, and
  OCR runtime proof failed because the OCR add-on is missing.
- v541 operator-side handoff docs are prepared and staged:
  `docs/runbooks/00-READ-ME-FIRST-v541.txt`,
  `docs/runbooks/eidp-v541-release-summary.md`,
  `docs/runbooks/eidp-v541-owner-signoff.md`,
  `docs/runbooks/eidp-v541-owner-request-20260621.txt`, and
  `docs/runbooks/eidp-v541-owner-return-fill-sheet.md`. These enable
  Windows-local owner return validation, but they are not release approval and
  do not replace returned evidence.
- Local docs-only release gate at PR head
  `4d1c093700a51d2797a454abc2e6ce3113113dda` returned `ok=true` for
  `dist/eidp-windows-v526.zip` with `docs_only_stale=true`, SHA256
  `4a03e975243d1327e79470de82fe468814c42a66e2749ec32c3251176da9ebca`,
  validator/distribution unit `188 passed`, mypy/ruff pass, discovery gold
  45/45 exact, and package verification pass. The then-live historical PR state
  for that head was `mergeStateStatus=CLEAN`, with `Python quality gates` and
  `Ship gate contract` successful for both push and pull_request CI runs.
  This supersedes the earlier post-`a8decad` campus-network gate-state note;
  `a8decad` remains the source commit for the `10.x` / proxy guidance.

These checks validate the gold-set contract used by the package verifier. They
do not remove the FY2026/R8 release blocker.

## Required Next Actions

1. Resolve the FY2026/R8 strict-yield blocker by either reaching the `>= 60%`
   current-year strict line or approving the documented `publication_lag`
   exception path.
2. Continue strict-yield RCA in the documented bucket order: fiscal-year
   mismatch / publication lag first, non-target candidate noise second,
   target-year-unverified third, and site-entry/fetch/identity lanes fourth.
3. Review `docs/reports/2026-06-21-v541-false-reject-review-sheet.csv` and mark
   sampled rows as `false_reject`, `correct_reject`, or
   `needs_operator_review`, then validate the returned CSV with
   `scripts/build_false_reject_audit.py --validate-review-csv --require-decisions`
   before labeling the blocker as an algorithm/model defect.
4. Run the prepared owner/operator v541 return path from Windows and collect
   signed KPI, audit/outbox, workbook, and `publication_lag` decision evidence.
5. Run the owner real Windows cycle and return KPI/sign-off evidence.
6. Run `scripts/verify_stage6_return.py` against the returned owner evidence.
7. Create the signed `v1.0` tag only after the above blockers are resolved.
