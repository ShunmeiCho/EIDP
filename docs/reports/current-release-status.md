# EIDP Current Release Status

Updated: 2026-06-21
Branch: `main`

Current packaged bounded Windows canary is `v547`
(`dist/eidp-windows-v547.zip`, SHA256
`f167e17b89f0ff96a45c817abcfd0403a2d487eddf3fb3a85a73d866b351de4b`).
`v547` packages commit `86c848f68e1dbde85c9b6422cfc827149940e02a` with
`git_dirty=false`. It packages the current-main false-reject worksheet guidance
hardening, where non-obvious `pre_filtered_non_target_hint` and
`classified_non_target` rows are suggested as `needs_operator_review` instead
of leaving `suggested_decision` blank. Local package verification and full
non-Windows release gates returned `ok=true`, including full unit
`2052 passed`, validator/distribution unit `196 passed`, mypy, Ruff, discovery
gold replay `45/45` exact matches, and both package verifier modes. Evidence
is recorded in `docs/reports/2026-06-21-v547-package-gates.md`,
`logs/eidp-windows-v547-distribution-verify-20260621.json`, and
`logs/eidp-windows-v547-release-gates-20260621.json`. Local v547 cleanup
evidence is recorded in `logs/eidp-v547-local-prune-20260621.json`; it removed
superseded v545 ZIP artifacts (`deleted_bytes=210931692`) and retained v546
fallback, v547 current package, and the latest alias on the external-SSD-backed
`dist/`.

`v547` completed side-by-side Windows setup and a bounded limit-50 weekly
canary at `C:\Users\cyo20\EIDP-v547-86c848f-env0`. The canary confirmed setup
`rc=0`, after-setup validator `ok=true`, active-task safety `ok=true`, weekly
canary `rc=0`, after-weekly validator `ok=true`, Stage 6 evidence verification
`ok=true`, strict/Excel-ready FY2026 yield `12/50 (24.0%)`,
operator-reviewable yield `47/50 (94.0%)`, and `ship_gate_status=below_gate`.
That `24.0%` is bounded-cohort evidence for the selected 50 target-missing
schools, not whole-database readiness. It is also not a PDF acquisition success
rate or an overall project completion rate: candidate sets were found for
`50/50` selected schools, `15` documents were downloaded and processed, and
only `12` schools reached strict target PDF plus Excel-ready. Therefore v547
proves the false-reject worksheet guidance hardening is packaged and
Windows-canary safe; it does not prove release readiness and does not support
claiming a generic algorithm/model defect. Evidence is recorded in
`docs/reports/2026-06-21-v547-windows-canary.md`,
`logs/win-v547-86c848f-canary/stage6-evidence-20260621-054545.zip`,
`logs/win-v547-86c848f-canary/stage6-evidence-verify-20260621-144556.json`,
`logs/win-v547-86c848f-canary/stage6-evidence-verify-mac-20260621.json`, and
`logs/win-v547-86c848f-canary/20260621_053425-summary.json`.

Windows cleanup after v547 retained active v527, fallback v546, and current
v547 while removing v545 transfer ZIPs and the v545 side-by-side directory
(`1,109,396,361` bytes total). Cleanup evidence is recorded in
`logs/win-v547-86c848f-canary/win-v547-cleanup-20260621.json` and
`logs/win-v547-86c848f-canary/win-v547-explicit-dir-cleanup-20260621.json`.

`v547` still has not completed OCR scope approval, owner real-cycle sign-off,
or publication-lag decision. Release Forecast remains `NOT_READY`.

Current `main` false-reject review guidance was rerun against the v547
Windows-canary Stage 6 evidence. It keeps the v547 evidence bundle fixed while
making explicit non-target-year hints owner-triage only. Running the current
script produced
`docs/reports/2026-06-21-v547-false-reject-review-summary.md`,
`docs/reports/2026-06-21-v547-false-reject-review-worklist.md`,
`docs/reports/2026-06-21-v547-false-reject-review-sheet.csv`,
`docs/reports/2026-06-21-v547-false-reject-review-validation.json`, and
`docs/reports/2026-06-21-v547-false-reject-review-validation-summary.md`: the
worklist is generated with the same `--sample-size 12` as the worksheet and
lists the `53` owner rows with page/PDF URLs. The worksheet still has
`decision=blank` for all `53` rows pending owner/operator review, but
`suggested_decision` now has `0` blanks (`24` `correct_reject`, `29`
`needs_operator_review`). `--require-decisions` fails as expected, so blank
owner decisions remain blocked and cannot support Excel output or a generic
model-failure claim.

The v547 runtime package still remains the latest completed Windows canary
package, but this regenerated worksheet is a current-`main` helper output. Use
current `main` for validating this regenerated worksheet unless a fresh package
is built and Windows-verified with the same helper revision.
Current `main` also adds a `review-audit-log` output for returned false-reject
worksheets. It emits one JSONL audit event for each validated nonblank owner
decision, with immutable worksheet context hash, reviewer, timestamp, notes,
source archive, and strict-gate forecast. This is RCA/audit handoff evidence
only: it does not write business tables, does not approve rejected rows, and
does not make any rejected row Excel-ready. The owner-return verifier now
requires `--false-reject-review-audit-log` whenever a false-reject review CSV is
submitted, and rejects audit logs that do not match regenerated audit events.

The next strict-yield action is worksheet-driven, not generic crawler work: a
high `false_reject` count means fix the specific discovery/filter rule and add
regression tests; mostly `correct_reject` rows point to publication-lag /
old-year / non-target noise and at most an explicit `RC_ONLY` exception; many
`needs_operator_review` rows mean the operator queue and evidence display need
to be improved while keeping Excel-ready gates strict.

Previous packaged bounded Windows canary is `v546`
(`dist/eidp-windows-v546.zip`, SHA256
`ece0bbf3c1e96f3bf5be6dd553f3a547244edf15ad65ea2bc38c61600887ecfd`).
`v546` packages commit `63016054f948b1f4f285c3c822197f76c25b4b7d` with
`git_dirty=false`. It packages the false-reject `review-rca-summary`
handoff hardening from current `main`; local package verification and full
non-Windows release gates returned `ok=true`, including full unit
`2052 passed`, validator/distribution unit `196 passed`, mypy, Ruff, discovery
gold replay `45/45` exact matches, and both package verifier modes. Evidence
is recorded in `docs/reports/2026-06-21-v546-rca-summary-package-gates.md`,
`logs/eidp-windows-v546-distribution-verify-20260621.json`, and
`logs/eidp-windows-v546-release-gates-20260621.json`.
Local v546 cleanup evidence is recorded in
`logs/eidp-v546-local-prune-20260621.json`; it removed superseded v544 ZIP
artifacts (`deleted_bytes=210931317`) and retained v545 fallback, v546 current
package, and the latest alias on the external-SSD-backed `dist/`.

`v546` completed side-by-side Windows setup and a bounded limit-50 weekly
canary at `C:\Users\cyo20\EIDP-v546-6301605-env0`. The canary confirmed setup
`rc=0`, after-setup validator `ok=true`, active-task safety `ok=true`, weekly
canary `rc=0`, after-weekly validator `ok=true`, Stage 6 evidence verification
`ok=true`, strict/Excel-ready FY2026 yield `12/50 (24.0%)`,
operator-reviewable yield `47/50 (94.0%)`, and `ship_gate_status=below_gate`.
That `24.0%` is bounded-cohort evidence for the selected 50 target-missing
schools, not whole-database readiness. Therefore v546 proves the
false-reject RCA-summary hardening is packaged and Windows-canary safe; it
does not prove release readiness and does not support claiming a generic
algorithm/model defect. Evidence is recorded in
`docs/reports/2026-06-21-v546-rca-summary-windows-canary.md`,
`logs/win-v546-6301605-canary/stage6-evidence-20260621-043811.zip`,
`logs/win-v546-6301605-canary/stage6-evidence-verify-20260621-133825.json`,
`logs/win-v546-6301605-canary/stage6-evidence-verify-mac-20260621.json`, and
`logs/win-v546-6301605-canary/20260621_042630-summary.json`.

Windows cleanup after v546 retained active v527, fallback v545, and current
v546 while removing v535/v536/v544 transfer ZIPs and v532/v533/v535/v536/v537/
v538/v539/v544 side-by-side directories (`7,836,187,780` bytes). Cleanup
evidence is recorded in
`logs/win-v546-6301605-canary/win-v546-cleanup-20260621.json`.

Previous packaged bounded Windows canary is `v545`
(`dist/eidp-windows-v545.zip`, SHA256
`ba4d36189d671ce59e01cf8f1bffeb0710d8d2b171376e4cbc0cb4e362f1b8d0`).
`v545` packages commit `f3eb1663c0333f296856a84f447ef2424ea77ddf` with
`git_dirty=false`. It refreshes the package from current `main` after
prioritizing trusted `SchoolSite.url_type="disclosure"` rows ahead of ordinary
school homepages during PDF discovery. Local v545 distribution evidence is
recorded in `logs/eidp-windows-v545-distribution-verify-20260621.json`; the
package verifier returned `ok=true`, with `has_runtime=true`, `wheel_count=84`,
and `BUILD_INFO.git_commit=f3eb1663c0333f296856a84f447ef2424ea77ddf`.

`v545` completed side-by-side Windows setup and a bounded limit-50 weekly
canary at `C:\Users\cyo20\EIDP-v545-f3eb166-env0`. The canary confirmed
setup `rc=0`, after-setup validator `ok=true`, active-task safety `ok=true`,
weekly canary `rc=0`, after-weekly validator `ok=true`, Stage 6 evidence
verification `ok=true`, strict/Excel-ready FY2026 yield `12/50 (24.0%)`,
operator-reviewable yield `47/50 (94.0%)`, and
`ship_gate_status=below_gate`. That `24.0%` is bounded-cohort evidence for the
selected 50 target-missing schools, not whole-database readiness. Therefore
v545 proves the trusted-disclosure-priority hardening is Windows-canary safe;
it does not prove release readiness and does not support claiming a generic
algorithm/model defect. Evidence is recorded in
`docs/reports/2026-06-21-v545-disclosure-priority-windows-canary.md`,
`logs/win-v545-f3eb166-canary/stage6-evidence-20260621-004156.zip`,
`logs/win-v545-f3eb166-canary/stage6-evidence-verify-20260621-094157.json`,
`logs/win-v545-f3eb166-canary/stage6-evidence-verify-mac-20260621.json`, and
`logs/win-v545-f3eb166-canary/20260621_003033-summary.json`.

Historical v545 note: the read-only false-reject `review-rca-summary` output
was not yet packaged into the v545 ZIP. It helped frame completed RCA as either
specific rule defects or unsupported generic model failure without relaxing
strict evidence rules or moving rejected rows into Excel. The blank worksheet
RCA summary is recorded at
`docs/reports/2026-06-21-v545-false-reject-review-rca-summary.md`; it reports
`RCA conclusion=INVALID_RETURN`, `completed_decisions=0/53`, and
`blank_decisions=53`, so below-gate yield still must not be labeled as a
generic algorithm/model defect.

Local cleanup after v545 retained v544 fallback and v545 current packages while
removing superseded v535/v536/v542/v543 local ZIPs and sidecars
(`843676935` bytes). Windows cleanup retained active v527, fallback v544, and
current v545 while removing v542/v543 transfer ZIPs and v540-v543 side-by-side
diagnostic directories (`4015573603` bytes). Cleanup evidence is recorded in
`logs/eidp-v545-local-prune-20260621.json` and
`logs/win-v545-f3eb166-canary/win-v545-cleanup-20260621.json`.

Previous packaged bounded Windows canary was `v544`
(`dist/eidp-windows-v544.zip`, SHA256
`781da0a3c1a3f4ae80536c68de2971a1ae431a01c7eb2d58001de061f62df0c1`).
`v544` packages commit `74325bc278c3e96052ef27e67cd554e426c87c60` with
`git_dirty=false`. It refreshes the package from current `main` after adding
false-reject worksheet triage guidance. Local v544 package-gate evidence is
recorded in `docs/reports/2026-06-21-v544-package-gates.md`,
`logs/eidp-windows-v544-distribution-verify-20260621.json`, and
`logs/eidp-windows-v544-release-gates-20260621.json`; the non-Windows release
gates returned `ok=true`, including full unit tests, validator/distribution
tests, mypy, Ruff, discovery gold-set checks, package verification, and
demonstrated-pattern verification.

`v544` completed side-by-side Windows setup and a bounded limit-50 weekly
canary at `C:\Users\cyo20\EIDP-v544-74325bc-env0`. The canary confirmed
setup `rc=0`, after-setup validator `ok=true`, weekly canary `rc=0`,
after-weekly validator `ok=true`, Stage 6 evidence verification `ok=true`,
strict/Excel-ready FY2026 yield `12/50 (24.0%)`, operator-reviewable yield
`47/50 (94.0%)`, and `ship_gate_status=below_gate`. That `24.0%` is
bounded-cohort evidence for the selected 50 target-missing schools, not
whole-database readiness. The after-weekly validator's global SQLite target-FY
view still reports `sqlite_target_fy_target_pdf_school_count=8` and
`sqlite_target_fy_yield_pct=0.3` across `2418` specialty schools, with
`sqlite_target_fy_operator_reviewable_school_count=40` and
`sqlite_target_fy_operator_reviewable_yield_pct=1.7`. Therefore v544 proves the
latest packaged triage-helper source is Windows-canary safe; it does not prove
release readiness. Evidence is recorded in
`docs/reports/2026-06-21-v544-triage-helper-windows-canary.md`,
`logs/win-v544-74325bc-canary/stage6-evidence-20260620-230327.zip`,
`logs/win-v544-74325bc-canary/stage6-evidence-verify-20260621-080339.json`,
`logs/win-v544-74325bc-canary/stage6-evidence-verify-mac-20260621.json`, and
`logs/win-v544-74325bc-canary/20260620_224853-summary.json`.

Previous packaged bounded Windows canary was `v543`
(`dist/eidp-windows-v543.zip`, SHA256
`c3b80835225864f57f62c33fa87cde2cdb5b2006ee2da0fdfa726cccfdc5a094`).
`v543` packages commit `6aa5735d164101cbe6ec85648bcb8b6f46168c63` with
`git_dirty=false`. It includes both `scripts/verify_stage6_return.py` and the
same-directory helper `scripts/build_false_reject_audit.py`, which is required
when owner-return validation uses `--false-reject-evidence-zip` and
`--false-reject-review-csv`. Local v543 package-gate evidence is recorded in
`docs/reports/2026-06-21-v543-package-gates.md`,
`logs/eidp-windows-v543-distribution-verify-20260621.json`, and
`logs/eidp-windows-v543-release-gates-20260621.json`; the non-Windows release
gates returned `ok=true`, including full unit tests, validator/distribution
tests, mypy, Ruff, discovery gold-set checks, package verification, and
demonstrated-pattern verification.

`v543` completed side-by-side Windows setup and a bounded limit-50 weekly
canary at `C:\Users\cyo20\EIDP-v543-6aa5735-env0`. The canary confirmed
setup `rc=0`, after-setup validator `ok=true`, active-task safety `ok=true`,
weekly canary `rc=0`, after-weekly validator `ok=true`, Stage 6 evidence
verification `ok=true`, strict/Excel-ready FY2026 yield `12/50 (24.0%)`,
operator-reviewable yield `47/50 (94.0%)`, and `ship_gate_status=below_gate`.
That `24.0%` is bounded-cohort evidence for the selected 50 target-missing
schools, not whole-database readiness. The after-weekly validator's global
SQLite target-FY view still reports `sqlite_target_fy_target_pdf_school_count=8`
and `sqlite_target_fy_yield_pct=0.3` across `2418` specialty schools, with
`sqlite_target_fy_operator_reviewable_school_count=40` and
`sqlite_target_fy_operator_reviewable_yield_pct=1.7`. Therefore v543 proves the
packaged false-reject audit helper is Windows-canary safe; it does not prove
release readiness. Evidence is recorded in
`docs/reports/2026-06-21-v543-helper-windows-canary.md`,
`logs/win-v543-6aa5735-canary/stage6-evidence-20260620-213335.zip`,
`logs/win-v543-6aa5735-canary/stage6-evidence-verify-20260621-063335.json`,
`logs/win-v543-6aa5735-canary/stage6-evidence-verify-mac-20260621.json`, and
`logs/win-v543-6aa5735-canary/20260620_212327-summary.json`.

Previous packaged bounded Windows canary before v543 was `v542`
(`dist/eidp-windows-v542.zip`, SHA256
`89ace547fcabf43f80b697024f5c13d1398244ad4d4b165160a489c8386f9ecc`).
`v542` packages commit `d98ecd7196631a00c27aff1c240ebc7969579ce7` with
`git_dirty=false`. It packages the post-v541 false-reject owner-return verifier
integration, including `--false-reject-evidence-zip`,
`--false-reject-review-csv`, and `--false-reject-sample-size` validation in
`scripts/verify_stage6_return.py`. CI run `27880148454` passed both
`Python quality gates` and `Ship gate contract` for that source commit. Local
non-Windows package gates also passed:
`logs/win-v542-false-reject-verifier-release-gates-20260621.json` records
`ok=true`, package/source freshness, `2049` unit tests, `196` distribution
validator tests, mypy, Ruff, package verification, and demonstrated-pattern
verification.

`v542` completed side-by-side Windows setup and a bounded limit-50 weekly
canary at `C:\Users\cyo20\EIDP-v542-d98ecd7-env0`. The canary confirmed
setup `rc=0`, after-setup validator `ok=true`, active-task safety `ok=true`,
weekly canary `rc=0`, after-weekly validator `ok=true`, Stage 6 evidence
verification `ok=true`, strict/Excel-ready FY2026 yield `12/50 (24.0%)`,
operator-reviewable yield `47/50 (94.0%)`, and `ship_gate_status=below_gate`.
That `24.0%` is bounded-cohort evidence for the selected 50 target-missing
schools, not whole-database readiness. The after-weekly validator's global
SQLite target-FY view still reports `sqlite_target_fy_target_pdf_school_count=8`
and `sqlite_target_fy_yield_pct=0.3` across `2418` specialty schools, with
`sqlite_target_fy_operator_reviewable_school_count=40` and
`sqlite_target_fy_operator_reviewable_yield_pct=1.7`. Therefore v542 proves the
false-reject verifier integration is packaged and Windows-canary safe; it does not
prove release readiness. Evidence is recorded in
`docs/reports/2026-06-21-v542-false-reject-verifier-windows-canary.md`,
`logs/win-v542-d98ecd7-canary/stage6-evidence-20260620-190958.zip`,
`logs/win-v542-d98ecd7-canary/stage6-evidence-verify-20260621-040959.json`,
and `logs/win-v542-d98ecd7-canary/20260620_185933-summary.json`.

The latest owner/operator handoff docs have been refreshed to v547 package
identity and the v547 false-reject review worksheet. The current handoff lane is
`C:\EIDP-staging\v547-owner-docs-20260621`, recorded in
`docs/reports/2026-06-21-v547-owner-docs-windows-staging.md`, and includes
`docs/runbooks/00-READ-ME-FIRST-v547.txt`,
`docs/runbooks/eidp-v547-release-summary.md`,
`docs/runbooks/eidp-v547-owner-signoff.md`,
`docs/runbooks/eidp-v547-owner-request-20260621.txt`,
`docs/runbooks/eidp-v547-owner-return-fill-sheet.md`,
`docs/reports/2026-06-21-v547-package-gates.md`,
`docs/reports/2026-06-21-v547-windows-canary.md`, and
`docs/reports/2026-06-21-v547-false-reject-review-sheet.csv`. It also includes
`docs/reports/2026-06-21-v547-false-reject-review-summary.md`, a read-only
triage guide that groups suggested decisions without filling the worksheet or
approving any row. The staged v547 blank worksheet validation is recorded at
`docs/reports/2026-06-21-v547-false-reject-review-validation.json`: it reports
`ok=true`, `review_status=incomplete`, `completed_decisions=0`,
`context_mismatch_count=0`, and `defect_framing.status=pending_review`. A
readable require-decisions failure summary is also recorded at
`docs/reports/2026-06-21-v547-false-reject-review-validation-summary.md`: it
reports `Validation OK=True` for the blank worksheet structure,
`completed_decisions=0/53`, `blank_decisions=53`, and `context_mismatches=0`;
the same worksheet still fails when `--require-decisions` is used. This is a
docs-only handoff and does not approve v1.0, prove an algorithm/model defect,
or replace the missing owner real-cycle evidence. The earlier v545, v544, v542,
and v541 owner-docs refreshes remain historical handoff evidence only.

Current `main` now adds a compact `false_reject_review_summary` field to
`scripts/verify_stage6_return.py` results whenever false-reject worksheet
validation is supplied. The field mirrors `review_status`, completed/blank
decision counts, context mismatch count, defect framing status, and the first
blocking CSV errors so the owner-return failure is readable without loosening
any gate. This is source-side hardening after the v545 packaged runtime; a
future package/canary is required before claiming this convenience field is
available from a Windows package.

Previous packaged bounded Windows canary was `v541` (core ZIP pruned from
`dist/` after v542 verification; SHA256 was
`2ffb25884e15b9e2937f43bab7a8f5866d9434bc9f29f8067dbc1760397fa46f`).
`v541` packages commit `e62d074081e60428957a2f405c3a917bbceb31a0` with
`git_dirty=false`. It packages the post-v540 owner-return verifier hardening:
short owner sign-off validation, expected package SHA/source commit checks, and
`RC_ONLY` semantics for the publication-lag exception path. CI run
`27874800210` passed both `Python quality gates` and `Ship gate contract` for
that source commit. It completed side-by-side Windows setup and a bounded
limit-50 canary at `C:\Users\cyo20\EIDP-v541-e62d074-env0` with
strict/Excel-ready `12/50 (24.0%)`, operator-reviewable `47/50 (94.0%)`, and
`ship_gate_status=below_gate`. Evidence is recorded in
`docs/reports/2026-06-21-v541-owner-signoff-verifier-windows-canary.md`,
`logs/win-v541-e62d074-canary/stage6-evidence-20260620-153655.zip`,
`logs/win-v541-e62d074-canary/stage6-evidence-verify-20260621-003707.json`,
and `logs/win-v541-e62d074-canary/20260620_152248-summary.json`.

Previous packaged bounded Windows canary before that was `v540` (core ZIP
pruned from `dist/` after v542 verification; SHA256 was
`6f246e47c41869dce401810731df48e99268756622719a0e59461c33fd645fd6`).
`v540` packages commit `fbdd0bddbeca3e6ceaa7b9e576bc9c5b0b88025a` with
`git_dirty=false`. It carries the post-v539 release-gate hardening for the
rolling fiscal-year owner-decision brief contract and packages that source head
into fresh Windows evidence. CI run `27871865340` passed both `Python quality
gates` and `Ship gate contract` for that packaged source commit.

`v540` completed side-by-side Windows setup and a bounded limit-50 weekly
canary at `C:\Users\cyo20\EIDP-v540-fbdd0bd-env0`. The canary confirmed
setup `rc=0`, after-setup validator `ok=true`, active-task safety `ok=true`,
weekly canary `rc=0`, after-weekly validator `ok=true`, Stage 6 evidence
verification `ok=true`, strict/Excel-ready FY2026 yield `12/50 (24.0%)`,
operator-reviewable yield `47/50 (94.0%)`, and `ship_gate_status=below_gate`.
That `24.0%` is bounded-cohort evidence for the selected 50 target-missing
schools, not whole-database readiness. The after-weekly validator's global
SQLite target-FY view still reports `sqlite_target_fy_target_pdf_school_count=8`
and `sqlite_target_fy_yield_pct=0.3` across `2418` specialty schools, with
`sqlite_target_fy_operator_reviewable_school_count=40` and
`sqlite_target_fy_operator_reviewable_yield_pct=1.7`. Therefore v540 proves
operational viability for a bounded cohort and closes the post-v539
source-to-Windows evidence gap; it does not prove release readiness.
Evidence is recorded in
`docs/reports/2026-06-20-v540-owner-briefs-windows-canary.md`,
`logs/win-v540-fbdd0bd-canary/stage6-evidence-20260620-133325.zip`,
`logs/win-v540-fbdd0bd-canary/stage6-evidence-verify-20260620-223357.json`,
and `logs/win-v540-fbdd0bd-canary/stage6-evidence-verify-mac-20260620.json`.

The post-v541 false-reject owner-return verifier integration is now packaged
and Windows-canary verified by v542. v541 and v540 remain evidence and handoff
material, not the current package/canary head.

Superseded `v539` (`dist/eidp-windows-v539.zip`, SHA256
`2c18d2808d0e6910f056a98b181a057dab95fc229faad93289dde3ed7773a7a3`)
kept FY2026/Reiwa 8 document acceptance strict while improving rejection
evidence for target-form-like PDF candidates that do not expose a target
fiscal year. It completed a bounded Windows canary with strict/Excel-ready
FY2026 yield `12/50 (24.0%)`, operator-reviewable yield `47/50 (94.0%)`, and
`ship_gate_status=below_gate`. Evidence is recorded in
`docs/reports/2026-06-20-v539-yearless-target-evidence-windows-canary.md` and
`logs/win-v539-142dfc7-canary/stage6-evidence-20260620-110538.zip`. The v539
core ZIP and sidecar have been pruned from the external-SSD-backed `dist`
directory after v540 verification.

Superseded `v538` (`dist/eidp-windows-v538.zip`, SHA256
`5d32c3c21fef227a8da13a6dab2c7b6d29e6d304363d90340af757ed0a7b7e1a`) fixed
the v537 Windows canary failure by moving PDF school-name mismatch alias
proposal logic into the packaged module
`eidp.review.pdf_school_mismatch_alias_proposals`. It completed a bounded
Windows canary with strict/Excel-ready FY2026 yield `12/50 (24.0%)`,
operator-reviewable yield `47/50 (94.0%)`, and `ship_gate_status=below_gate`.
Evidence is recorded in
`docs/reports/2026-06-20-v538-pdf-mismatch-alias-windows-canary.md` and
`logs/win-v538-stage6/stage6-evidence-20260620-094934.zip`. The v538 core ZIP
and sidecar have been pruned from the external-SSD-backed `dist` directory
after v539 verification.

Superseded `v537` (`dist/eidp-windows-v537.zip`, SHA256
`1ceeb84ae6804c4d95574ac5c11a583eb4967d0e285c5de3fe5b1fd0f1254356`) is
package/source verified, but its Windows weekly canary failed with
`ModuleNotFoundError: No module named 'pdf_school_mismatch_alias_proposals'`.
That P1 is fixed by v538. The v537 core ZIP and sidecar have been pruned from
the external-SSD-backed `dist` directory after v538 verification; its Mac-side
evidence remains recorded in `docs/reports/2026-06-20-v537-current-main-package.md`.

Previous bounded Windows canary: `v536`
(`dist/eidp-windows-v536.zip`, SHA256
`381ec169b8380cfe666a89e02a8b786d3a8cdc79dca4b420276517bbbdb0349a`).
`v536` completed a bounded Windows limit-50 canary at
`C:\Users\cyo20\EIDP-v536-f81a9cf-env0` with strict/Excel-ready FY2026 yield
`12/50 (24.0%)` and `ship_gate_status=below_gate`. Evidence is recorded in
`docs/reports/2026-06-20-v536-sanko-fresh-windows-canary.md`,
`logs/win-v536-stage6-v536-non-windows-release-gates-20260620.json`, and
`logs/win-v536-stage6/stage6-evidence-20260620-074649.zip`.

The latest complete Windows side-by-side smoke evidence remains `v535`.
The source package was `dist/eidp-windows-v535.zip` (SHA256
`72ef94f35a2cd482eb9650d1a466cb8441f7d96a660a8901710d96603e7d8e9f`);
the local ZIP was pruned from the external-SSD-backed `dist/` during the v545
cleanup after its smoke evidence had already been preserved. `v535` is
package/source verified on macOS, carries the post-v533
release-proof hardening that requires v1 evidence to stay scoped to
`専門学校`, and rebuilds after the AppleDouble wheelhouse-sidecar gate rejected
v534. The v535 ZIP contains `0` AppleDouble sidecars, `84` real wheelhouse
wheels, and `BUILD_INFO.git_commit=d742327570a08a8f9d6ade7adfc81da8940294b4`
with `git_dirty=false`. Its full non-Windows release gate passed with `2016`
unit tests, `196` Windows distribution validator tests, package/source
freshness, package verifier, and demonstrated-pattern verifier. It has now
completed Windows side-by-side smoke at
`C:\Users\cyo20\EIDP-v535-d742327-env0` for setup, active-task safety, UI,
bounded weekly canary, Excel export, Stage 6 bundle creation, and Stage 6
evidence verification. Evidence is recorded in
`docs/reports/2026-06-20-v535-appledouble-clean-package.md`,
`docs/reports/2026-06-20-v535-full-windows-side-by-side-smoke.md`,
`logs/win-v535-stage6-v535-non-windows-release-gates-20260620.json`, and
`logs/win-v535-stage6/stage6-evidence-20260620-053032.zip`.
The initial owner/operator handoff docs were staged for v541 on Windows under
`C:\EIDP-staging\v541-owner-docs-20260621`, then refreshed to r3 under
`C:\EIDP-staging\v541-owner-docs-20260621-r3` after false-reject worksheet
return rules were added. Those v541 handoffs, the v540 r2 handoff, and the v535
owner-docs staging remain historical evidence only; the current owner handoff
lane is the v544 docs-only refresh recorded above.
The v535 strict-yield RCA action plan is recorded in
`docs/reports/2026-06-20-v535-strict-yield-rca-plan.md`; it decomposes the
`12/50 (24.0%)` blocker into `publication_lag_or_old_target_pdf`,
`target_form_without_year_evidence`, `school_identity_mismatch`, and
`non_target_candidates_only` action lanes without relaxing the FY2026/R8 strict
evidence rules. The RCA summary is now reproducible from the Stage 6 evidence
ZIP with `uv run python scripts/summarize_stage6_rca.py
logs/win-v535-stage6/stage6-evidence-20260620-053032.zip --json`; the script
confirms `20` school packets, `524` candidate rows, and strict-yield conclusion
`BELOW_GATE`.
The current P0 is therefore not a generic "PDF not found" or crawler-runtime
failure. It is specifically the FY2026/R8 strict target-document to Excel-ready
yield staying below the release gate. v544 found many PDF candidates, but the
dominant rejection evidence is old-year/current-FY mismatch, non-target PDF
noise, target-form-like files without trusted year evidence, and small
site-entry/fetch/identity lanes. The next RCA pass must work those buckets in
order, without counting old-year PDFs, unknown-year documents, non-target files,
or identity mismatches as FY2026/R8 success. This also must not be simplified
to "the algorithm/model is broken" until a rejection-bucket false-reject audit
shows material over-rejection or fiscal-year extraction mistakes.
The historical v545 false-reject audit packet is recorded in
`docs/reports/2026-06-21-v545-false-reject-audit-packet.md`; it was generated
from the v545 Stage 6 evidence ZIP and samples fiscal-year mismatch,
pre-filtered non-target, classified non-target, target-year-unverified, and
site-entry/fetch/identity rows without changing release status.
The same packet now has a companion decision worksheet at
`docs/reports/2026-06-21-v545-false-reject-review-sheet.csv`. It contains stable
`audit_row_id` values and blank `decision` cells restricted to
`false_reject`, `correct_reject`, or `needs_operator_review`. It also includes
read-only `suggested_decision` / `suggested_decision_basis` guidance for obvious
old-year, non-target, yearless, and identity-risk rows; these suggestions do not
fill the actual `decision` field and cannot complete review by themselves.
Validating it with
`--require-decisions` correctly fails until the owner/operator completes the
sample review. The return validator also rejects changed row context and emits
`bucket_decision_counts`; the current blank worksheet validates as
`defect_framing.status=pending_review`, `completed_decisions=0`,
`blank_decisions=53`, and
`context_mismatch_count=0` in
`docs/reports/2026-06-21-v545-false-reject-review-validation.json`. Completed
rows require `reviewer` and an ISO `reviewed_at` timestamp, and `false_reject`
/ `needs_operator_review` rows require `notes`.
The owner/operator return runbooks now include the false-reject worksheet return
rules: only `decision`, `reviewer`, `reviewed_at`, and `notes` may be filled;
row context must remain unchanged; and completed worksheets must be validated
from current `main` before they can support an RCA claim. The owner-return
verifier now accepts `--false-reject-evidence-zip`,
`--false-reject-review-csv`, `--false-reject-review-audit-log`, and
`--false-reject-sample-size`; when supplied, it requires the worksheet to
validate with `review_status=complete`, `context_mismatch_count=0`, and a
matching regenerated audit JSONL. The Windows docs-only handoff has been refreshed to
v547 at `C:\EIDP-staging\v547-owner-docs-20260621`, recorded in
`docs/reports/2026-06-21-v547-owner-docs-windows-staging.md`, so the staged
owner docs now include the v547 false-reject worksheet return rules, read-only
review summary, row-by-row worklist, worksheet CSV, and the return-verifier
false-reject arguments.
The v545, v544, v542, and v541 handoffs remain historical evidence only. This
still does not change the release conclusion.
This false-reject owner-return verifier integration was first packaged and
Windows-canary verified in `dist/eidp-windows-v542.zip` at package commit
`d98ecd7196631a00c27aff1c240ebc7969579ce7`. CI run `27880148454` passed both
`Python quality gates` and `Ship gate contract` for that commit, and
`docs/reports/2026-06-21-v542-false-reject-verifier-windows-canary.md` records
the package/source freshness, Windows setup, bounded canary, and Stage 6
evidence verification. Current `main` has since rebuilt the package as v544,
and `docs/reports/2026-06-21-v544-triage-helper-windows-canary.md` records the
v544 Windows setup/canary evidence for that helper package. Returned
false-reject worksheets can be validated from current `main` or from a v544+
package carrying the helper.
Post-v535 source hardening adds a bounded Sanko same-host disclosure probe for
the remaining `non_target_candidates_only` RCA packet by keeping both
`/disclosure/{slug}` and `/{slug}/disclosure` under shared-origin throttling;
this is recorded in
`docs/reports/2026-06-20-sanko-shared-origin-disclosure-probe.md`. The rebuilt
v536 Windows canary now exercises this fix: `shared_origin_derived_fallback_skipped=0`,
and school `41` reaches `https://www.sanko.ac.jp/omiya-beauty/disclosure/`.
The packet remains `non_target_candidates_only` because the reached official
page exposes `schoolinfo.pdf` and school/program information PDFs rather than
an acceptable FY2026/R8 target document.

Rejected v534 (`dist/eidp-windows-v534.zip`, SHA256
`734918dbe2213723936aa9148f4260256845f7cfd5044ca0c486bdd237335c05`) is
documented in `docs/reports/2026-06-20-v534-specialty-scope-gate-package.md`.
It must not be transferred or validated on Windows.

Previous complete Windows side-by-side smoke was `v533`
(`dist/eidp-windows-v533.zip`, SHA256
`0d4ca81a9032db1d8b98bf69ba76a4181d99d6bb8cd0091de22df211dc5d5f57`).
`v533` is package/source verified on macOS, adds a package-enforced MEXT T0
target-institution official-index gate, and completed Windows side-by-side
smoke at `C:\Users\cyo20\EIDP-v533-f83f1dc-env0`. The verifier reports
`mext_target_total_rows=3132`, `mext_target_university_rows=769`,
`mext_target_specialty_rows=2067`, `mext_target_short_college_rows=239`, and
`mext_target_kosen_rows=57`. Evidence is recorded in
`docs/reports/2026-06-20-v533-mext-authority-index-package.md`,
`docs/reports/2026-06-20-v533-full-windows-side-by-side-smoke.md`,
`logs/win-v533-stage6-v533-non-windows-release-gates-20260620.json`, and
`logs/win-v533-stage6/stage6-evidence-20260619-180429.zip`.

Previous complete Windows side-by-side smoke was `v532`
(`dist/eidp-windows-v532.zip`, SHA256
`9743cc65c21ada06b6a1d6c8b50ba67cdaffa4f3942256ccd072d4469fa0d6c7`).
That same-day Windows SSH follow-up completed a fresh Windows side-by-side
smoke at `C:\Users\cyo20\EIDP-v532-723a507-env0`. Evidence is recorded in
`docs/reports/2026-06-20-v532-full-windows-side-by-side-smoke.md` and
`logs/win-v532-stage6/win-v532-stage6-side-by-side-evidence-20260620.zip`.
The local v532 core ZIP and sidecar were pruned after v534 was built using
`scripts/prune_release_artifacts.py --dist-dir dist --keep-latest 2 --apply`;
the invalid v534 core ZIP and sidecar were pruned after v535 was built using
`scripts/prune_release_artifacts.py --dist-dir dist --keep-latest 1
--keep-version 533 --apply`. The kept local core packages are v533, v535, and
v536. After v537 was built and verified, v533 was pruned with
`scripts/prune_release_artifacts.py --dist-dir dist --keep-latest 3 --apply`;
after v538 was built and Windows-validated, superseded v537 was pruned with
`scripts/prune_release_artifacts.py --dist-dir dist --keep-latest 1
--keep-version 535 --keep-version 536 --apply`. The kept local core packages
were v535, v536, and v538. After v539 was built and Windows-validated,
superseded v538 was pruned with
`scripts/prune_release_artifacts.py --dist-dir dist --keep-latest 1
--keep-version 535 --keep-version 536 --apply`. The kept local core packages
were v535, v536, and v539. After v540 was built and Windows-validated,
superseded v539 was pruned from the external-SSD-backed `dist` directory.
After v542 was built and Windows-validated, cleanup pruned superseded v540 and
v541 core ZIPs and sidecars from the external-SSD-backed `dist` directory.
v543 and v544 have now been built on the same external-SSD-backed `dist` path,
and v544 refreshed the latest alias. After v544 owner-docs staging, cleanup
removed the superseded v542 owner-doc transfer ZIP/sidecar from `dist` and
removed the v542 owner-doc ZIP/sidecar/extracted docs from `C:\EIDP-staging`.
After v545 was built and Windows-validated, cleanup retained v544 fallback,
v545 current, the latest alias, the current wheelhouse, and the historical v545
owner-doc transfer artifact while pruning local v535/v536/v542/v543 core ZIPs
and sidecars. After v547 owner-docs staging, the current owner-doc transfer
artifact is v547. Windows cleanup retained active v527, fallback v544, and
current v545 while pruning v542/v543 transfer ZIPs and v540-v543 diagnostic
side-by-side directories. Reports and Stage 6 evidence for older packages
remain preserved under `docs/` and `logs/`.

Latest complete Windows side-by-side smoke is still `v535` for setup,
active-task safety, UI, bounded weekly canary, Excel export, Stage 6 bundle
creation, and Stage 6 evidence verification. Latest packaged bounded Windows
canary is `v545`; latest owner handoff docs are v544. The Windows canary
still reports FY2026/R8 strict yield below gate (`12/50`, `24.0%`). Release is
still blocked by missing owner real
Windows cycle/sign-off, unapproved `publication_lag` exception, and unresolved
OCR scope because the latest Windows OCR runtime proof failed without the OCR
add-on. A same-day OCR recovery check found no reusable OCR add-on ZIP or
Windows Tesseract payload in the checked Mac/external-SSD/Windows locations:
`docs/reports/2026-06-20-v532-ocr-addon-recovery-check.md`. The historical
status below is kept for traceability and is superseded by this 2026-06-21
summary.

Historical package family: `v526` for the extracted-PDF
confirmation/supplement UI, package/source verification, and complete Windows
side-by-side smoke. `v525` is now the previous complete Windows side-by-side
smoke package.
Latest source-side follow-up: `v526` adds an operator task-board entry point for
already extracted PDFs and prefilled confirmation/supplement saves through the
existing PDF確認・手入力 page.
Latest docs-only owner-decision handoff follow-up: this status refresh adds the
owner v1.0 A/B decision brief and v526 owner return fill sheet to the
Windows-staged v526 owner docs ZIP, then points `00-READ-ME-FIRST-v526.txt` to
them before the detailed request/template files. Latest docs-only
campus-network follow-up: `a8decad` generalizes
campus/private subnet guidance from `10.109.*` to `10.x` including `10.209.*`,
and records that outbound PDF discovery behind a campus proxy should use
standard `HTTP_PROXY` / `HTTPS_PROXY` / `NO_PROXY` environment variables rather
than a new `EIDP_HTTP_PROXY` knob. These docs-only follow-ups did not rebuild
`dist/eidp-windows-v526.zip`.
Latest owner-return remote check:
`docs/reports/2026-05-20-v526-owner-return-remote-check.md` confirms `ssh win`
is reachable after service recovery, the refreshed v526 owner handoff remains
staged on Windows, and the remote `publication_lag` approval plus owner/operator
sign-off fields remain blank. The Windows-staged owner docs ZIP now includes
this report, the target-yearless RCA spot check, the owner v1.0 A/B decision
brief, and the v526 owner return fill sheet, and now has SHA256
`28b12cbec895233b3ad97dff4c7757e2fb89cbd3130c4a604443a06bb8e38d29`.
`v526` remains the latest package with complete OCR runtime proof. `v535` is
the latest package with complete non-OCR Windows side-by-side smoke evidence,
including setup, validate, recovery, UI, Excel, limit-50 canary, and Stage 6
bundle verification. The current owner/operator handoff docs are now
`docs/runbooks/00-READ-ME-FIRST-v547.txt`,
`docs/runbooks/eidp-v547-release-summary.md`,
`docs/runbooks/eidp-v547-owner-signoff.md`,
`docs/runbooks/eidp-v547-owner-request-20260621.txt`, and
`docs/runbooks/eidp-v547-owner-return-fill-sheet.md`; they do not approve
v1.0 and do not replace the missing owner real-cycle evidence.
`v502` and `v501` are superseded Windows evidence baselines.

The authoritative package source commit is `BUILD_INFO.json` inside the ZIP.
The authoritative package SHA256 is the versioned `.sha256` sidecar. This
tracked status file is included in release ZIPs, so exact package values below
are evidence for the named ZIP artifact, not proof that this newer status file
is already embedded in that ZIP.

Post-v480 source fixes now include checked-in weekly URL source application,
application-style year hints, critical silent-failure logging, malformed-vs-
unsafe URL classification, G4/G5 documentation drift correction, strict-yield
table/context cache fixes, ASO disclosure overrides, NSG exact school /
disclosure overrides, v485 owner-cycle helpers, final-objective audit helpers,
the FY2026 strict-yield no-go report, the side-by-side setup guard, the owner
E2E preflight checklist, and the image-pending OCR warning packaging contract
through the current `sprint8-handoff-finalize` head. Post-v489 source fixes
add a reusable strict-yield upper-bound evaluator, require that evaluator in
future Windows ZIPs, reject legacy `streamlit.main` launchers, bind the
packaged Streamlit config to `127.0.0.1` as defense in depth, and add a
dry-run-by-default `repair_streamlit_launcher.py` helper for stale extracted
launchers. Post-v492 source fixes document the Streamlit launcher hotfix path,
promote PDF classification parse failures to `log.exception`, and add
`FOR UPDATE` call shape to fiscal-year override rewrites. Post-v493 source
fixes add a verifier-accepted mature-year proof path from production-scale
`strict_yield_gap_analysis` evidence and rebuild the Windows ZIP as v494.
Post-v494 fixes add operator URL parse-failure exception logging and rebuild
the Windows ZIP as v495. Post-v495 fixes make `publication_lag` release
approval machine-verifiable by requiring an approved exception Markdown record
in `scripts/verify_stage6_return.py`, then rebuild the Windows ZIP as v496.
Post-v496 fixes harden the Streamlit launcher repair helper against symlink
escape, backup overwrite, concurrent app-lock bypass, and post-write corruption;
document v494 as superseded; and rebuild the Windows ZIP as v497.
Post-v497 fixes package the default competition Excel template and complete
v498 Windows side-by-side validation. Post-v498 fixes configure weekly Task
Scheduler retry-on-failure settings during setup and rebuild the Windows ZIP as
v499. v499 Windows validation found that `weekly_run.bat --limit 10 --json`
was not a real bounded canary because the batch wrapper ignored CLI arguments.
v500 forwards `%*`, accepts `--json`, and has fresh package/source plus Windows
side-by-side validation. Post-v500 fixes add 17 live-verified Sanko exact
school URL overrides from the v500 limit-50 RCA, then rebuild the Windows ZIP as
v501 with fresh package/source verification. v501 has since completed Windows
setup, validate, recovery, OCR runtime validation, UI smoke, Excel smoke, Stage
6 evidence-bundle verification, and a limit-50 canary; it replaced v500 as the
latest complete Windows side-by-side smoke package until v523. Post-v501 fixes add 2
residual live-verified Sanko exact school URL overrides from the v501 limit-50
RCA and rebuild the Windows ZIP as v502 with fresh package/source verification
and partial Windows side-by-side evidence. v502 removes the residual
`non_target_candidates_only` RCA bucket, but its full Windows smoke is still
pending because the Windows OpenSSH service began resetting new SSH sessions
during the follow-up smoke. Post-v502 fixes add `operator_settings_saved`
`ManualActionLog` coverage for the settings page with API-key value redaction
and rebuild the Windows ZIP as v503 with fresh Mac-side package/source
verification. Post-v503 fixes add `excel_preview_generated` `ManualActionLog`
coverage for Excel preview generation under the shared `ui_excel_preview` lock
and rebuild the Windows ZIP as v504 with fresh Mac-side package/source
verification. Post-v504 fixes add `school_year_tasks_rebuilt`
`ManualActionLog` coverage for the school-year task-board rebuild action and
rebuild the Windows ZIP as v505 with fresh Mac-side package/source
verification. Post-v505 fixes add `operator_url_submitted` and
`operator_url_bulk_imported` `ManualActionLog` coverage for manual URL
registration and CSV bulk URL import, then rebuild the Windows ZIP as v506
with fresh Mac-side package/source verification. Post-v506 fixes add
`prefecture_remark_approved` and `prefecture_remark_rejected`
`ManualActionLog` coverage for official prefecture index remark decisions,
then rebuild the Windows ZIP as v507 with fresh Mac-side package/source
verification. Post-v507 fixes add `excel_export_generated` `ManualActionLog`
coverage for administrator-triggered master and competition Excel exports,
then rebuild the Windows ZIP as v508 with fresh Mac-side package/source
verification. Post-v508 fixes surface all current `ManualActionLog`
`action_type` and `target_table` values in the audit-log page filter
dropdowns, then rebuild the Windows ZIP as v509 with fresh Mac-side
package/source verification. Post-v509 fixes add `school_alias_approved`
`ManualActionLog` coverage for operator-approved school alias proposals, then
rebuild the Windows ZIP as v510 with fresh Mac-side package/source
verification. Post-v510 fixes add `proposal_decision_recorded`
`ManualActionLog` coverage for proposal review decisions written to
`proposal_decisions.jsonl`, then rebuild the Windows ZIP as v511 with fresh
Mac-side package/source verification.
Post-v511 fixes add `bug_report_generated` `ManualActionLog` coverage for
operator-generated local support ZIPs without storing free-text operator notes,
then rebuild the Windows ZIP as v512 with fresh Mac-side package/source
verification.
Post-v512 fixes keep one Sanko per-school `/disclosure/{slug}` derived probe
under shared-origin throttling, addressing the v502 limit-50
`no_pdf_candidates` bucket for Sanko medical-secretary schools whose school
roots are sparse but whose disclosure pages live at `www.sanko.ac.jp/disclosure/<slug>/`.
The fix remains scoped to Sanko hosts so large unrelated shared origins keep
the existing throttle behavior. The Windows ZIP is rebuilt as v513 with fresh
Mac-side package/source verification.
Post-v513 fixes make weekly school-based limits crawl every selected school's
matching `SchoolSite` rows instead of capping discovery at the same number of
site rows as selected schools. This prevents selected schools from remaining in
the denominator with no crawl evidence when earlier selected schools have
multiple high-confidence URLs. The Windows ZIP is rebuilt as v514 with fresh
Mac-side package/source verification.
The follow-up v514 Mac continuation canary in
`docs/reports/2026-05-20-v514-mac-continuation-canary.md` copied the structured
v513 isolated database into `_temp/v514-mac-limit50-from-v513` and ran a bounded
limit-50 current-FY canary. It crawled 56 site rows for 50 selected schools,
found 50 candidate PDFs, downloaded 0 new strict PDFs, reported strict
`2/50 (4.0%)`, operator-reviewable `47/50 (94.0%)`, and kept
`ship_gate_status=below_gate`. A bounded same-domain `2025 -> 2026` probe over
the 11 FY2025 mismatch target PDFs found no usable FY2026/R8 PDF URL.
Post-v514 fixes add exact Sanko child-school URL overrides for
札幌こども専門学校, 仙台こども専門学校, and 大宮こども専門学校. The Windows ZIP
is rebuilt as v515 with fresh Mac-side package/source verification. The
follow-up v515 Mac continuation canary in
`docs/reports/2026-05-20-v515-sanko-child-overrides-package.md` copied the
structured v513 isolated database into `_temp/v515-mac-limit50-sanko-child` and
ran a bounded limit-50 current-FY canary. It crawled 59 site rows for 50
selected schools, found 53 candidate PDFs, downloaded 0 new strict PDFs,
reported strict `2/50 (4.0%)`, operator-reviewable `50/50 (100.0%)`, removed
the residual `non_target_candidates_only` RCA bucket, and kept
`ship_gate_status=below_gate`.
Post-v515 fixes align the weekly target-missing acquisition queue with
`SchoolFiscalYearStatus._pdf_status()`. Current-FY target PDFs in
`review_pending`, `parse_failed`, or `support_only` states are already found
and should be handled through operator review/extraction status instead of
being recrawled as target-missing schools. The Windows ZIP is rebuilt as v516
with fresh Mac-side package/source verification. A sandbox selection probe
against `_temp/v515-mac-limit50-sanko-child/data/eidp.sqlite3` now excludes
school IDs 4 and 7, which already have current-FY target documents and
Excel-ready status rows, from the limit-50 target-missing queue.
The follow-up v516 Mac target-missing canary in
`docs/reports/2026-05-20-v517-remaining-sanko-child-overrides-package.md`
crawled 57 site rows for 50 selected schools, found 53 candidate PDFs,
downloaded 0 new strict PDFs, reported strict `0/50 (0.0%)`,
operator-reviewable `49/50 (98.0%)`, kept `ship_gate_status=below_gate`, and
confirmed that school IDs 4 and 7 were absent from the RCA batch. The only
residual `non_target_candidates_only` RCA item was `東京こども専門学校`, which
had only the Sanko corporation root registered. Post-v516 fixes add the five
remaining live-verified Sanko child-school exact URL overrides for 東京, 横浜,
名古屋, 大阪, and 沖縄こども専門学校, then rebuild the Windows ZIP as v517 with
fresh Mac-side package/source verification. A targeted school ID 55 smoke now
crawls `https://www.sanko.ac.jp/tokyo-child/` and finds FY2019-FY2025 target
forms, moving the evidence from corporation-only non-target to publication-lag
style evidence; it does not create a FY2026/R8 strict success. Post-v517 fixes
add that Sanko Tokyo child-school publication-lag case to the discovery gold set
so the packaged verifier preserves it as stale/latest-public evidence instead of
strict current-year success. The Windows ZIP is rebuilt as v518 with fresh
Mac-side package/source verification.
Post-v518 fixes tighten PDF body classification so `別紙様式4` /
`職業実践専門課程等の基本情報について` PDFs remain `non_target` even when
they contain incidental `修学支援` disclosure text. The Windows ZIP is rebuilt
as v519 with fresh Mac-side package/source verification.
PR merge-chain status:
PR #1 (`backup-2026-05-05`) is closed as superseded by PR #2, not merged
separately. Remote evidence checked on 2026-05-19 showed `origin/main` at
`ec2ec94`, PR #1 head at `e3becc4`, and `e3becc4` as an ancestor of PR #2
head `a3fbf4a728917defb5ef9bff7568322deb7f99dd`. PR #2 is now the single
active landing surface; its body has been updated to remove the old
"Depends on PR #1" statement and to keep the FY2026 release blocker explicit.
PR #2 is the active landing surface. The tracked status file does not pin the
moving PR head because docs-only status commits intentionally advance it. Use
live `gh pr view 2` or the PR body for the current head/check state. `main` and
`sprint8-handoff-finalize` branch protection require `Python quality gates` and
`Ship gate contract`, and disallow force-pushes and branch deletion. Any newer
commit must let those required checks rerun before merge.
The latest recorded live PR #2 check before this status refresh showed head
`4d1c093700a51d2797a454abc2e6ce3113113dda`,
`mergeStateStatus=CLEAN`, and both required checks successful for the push and
pull_request CI runs.
Current FY2025 limit-1000 strict-yield replay after discovery, ingest, and
rebuild is:
`_temp/targeted-replay-e6c003f-nsg/strict-gap-analysis.limit1000.combined-plus-shinsei.json`.
It reports denominator `1000`, strict/excel-ready `600/1000 (60.0%)`, broad
confirmed `601/1000 (60.1%)`, operator-reviewable `798/1000 (79.8%)`, and
estimated manual workload `20.2%`. This satisfies the mature-year strict
Excel-importable ship line for the selected FY2025 production-scale replay.
v497 converted that `strict_yield_gap_analysis` artifact into a then
verifier-accepted mature-year proof JSON at
`logs/mature-year-acquisition-proof-fy2025-release-exception-v497-20260519.json`.
That proof has `ok=true`, basis
`mature_year_retroactive_strict_target_pdf_and_operator_reviewable_acquisition`,
denominator `1000`, strict/Excel-ready `60.0%`, operator-reviewable `79.8%`,
and estimated manual workload `20.2%`. Current source-side release hardening now
requires mature-year proof cases to include a `finished_at` timestamp and a
traceable evidence source/path (`last_run` or `strict_gap_analysis`), so any
future `publication_lag` approval packet must regenerate or refresh this proof
with the current toolchain before Stage 6 return verification can pass.
The explicit publication-lag approval record is prepared at
`docs/reports/2026-05-19-publication-lag-release-exception-record.md`, but its
status remains `NOT_APPROVED`; it has been refreshed to the v526 package and
Windows-smoke evidence packet, but does not unblock release until filled and
signed.
Current FY2026/R8 production-scale strict-yield proof:
`logs/win-v485-stage6/fy2026-strict-yield-upper-bound-fail-20260519.json`
and `logs/win-v485-stage6/fy2026-strict-yield-rca-20260519.json` are the
current blocking evidence. A sandbox copy of the URL-rich DB was run against a
1,000-school denominator for target FY2026. After `607/1000` denominator
schools, `document.fiscal_year=2026` was still `0`; even if every remaining
school succeeded, the maximum possible strict yield would be `39.3%`, below
the required `60.0%`. The RCA buckets are dominated by non-target 2026-hinted
materials, sibling-school mismatches, and FY2025/R7 target-form PDFs. The
sample probe
`logs/win-v485-stage6/fy2026-current-hint-target-samples-20260519.json`
checked four 2026-path target-looking PDFs and found only `令和6年度` text,
so URL/upload-date hints cannot be counted as FY2026 success. The v490
source-side upper-bound evaluator re-computed the same no-go condition in
`logs/win-v490-stage6-v490-fy2026-strict-yield-upper-bound-reeval-20260519.json`
with `status=no_go_upper_bound_below_required` and
`max_possible=393/1000 (39.3%)`; its rc is intentionally `1` for no-go
evidence.
Historical Windows active lane before the v532 recheck:
read-only SSH probes on 2026-05-19 and restored SSH probes on 2026-05-20 showed
`EIDP Weekly Run` points to
`C:\Users\cyo20\EIDP-v485-70e3db4\scripts\weekly_run.bat`, with
`C:\Users\cyo20\EIDP-v460-01e4427` retained as the fallback lane. The owner
desktop handoff includes readiness, UI, initial PDF bootstrap, weekly batch,
evidence collection, and evidence-folder shortcuts. The active v485 DB still
had `school_site_count=0` and `document_count=0` in the latest readiness
probe, so the owner must run initial PDF bootstrap before any normal weekly
cycle.
The 2026-06-20 v532 side-by-side recovery check supersedes this as the latest
active-task safety fact: `EIDP Weekly Run` points to
`C:\Users\cyo20\EIDP-v527-69fe81f-env0\scripts\weekly_run.bat`, and v532 setup
was run with `EIDP_REGISTER_WEEKLY_TASK=0`.
Fresh read-only Mac-side connectivity recheck on 2026-05-20 is recorded in
`docs/reports/2026-05-20-v522-windows-connectivity-recheck.md`. The local
`Host win` still points at stale `192.168.0.9`, while the Mac is on
`192.168.10.68`. Current ARP candidates were only `192.168.10.12` and
`192.168.10.72`; neither candidate nor stale `192.168.0.9` exposed usable
TCP/22, 135, 139, 445, 3389, 5985, or 5986. A short Bonjour/mDNS browse for
SSH, SMB, RDP, and workstation services found no usable advertised service.
After the user restarted Windows SSH, `ssh win` was usable again and v523
current-source Windows side-by-side validation completed. The earlier
connectivity report is retained as historical evidence only.
Historical v526 package candidate:
`dist/eidp-windows-v526.zip`, SHA256
`4a03e975243d1327e79470de82fe468814c42a66e2749ec32c3251176da9ebca`.
`BUILD_INFO.json` inside the ZIP records
`git_commit=5b30eb78edc331f992c1a99fdc7611174791ab87`,
`git_branch=sprint8-handoff-finalize`, and `git_dirty=false`. Mac-side package
verification is recorded in
`logs/win-v526-stage6-v526-non-windows-release-gates-20260520.json`
(`ok=true`; package/source check is fresh, full unit suite `1901 passed`,
validator/distribution unit, mypy, ruff, discovery gold, package verify, and
demonstrated-pattern package verify returned `0`). A direct core + OCR add-on
verifier probe also returned core `ok=true` and OCR add-on `ok=true` against
`dist/eidp-ocr-addon-windows-v497-smoke.zip`.

v519 includes all v518 package features plus the vocational-practice
basic-information PDF non-target filter. The package evidence is recorded in
`docs/reports/2026-05-20-v519-vocational-practice-basic-info-filter-package.md`.
After the tracked docs update,
`logs/win-v519-stage6-v519-post-docs-only-gates-20260520.json` records
`ok=true`, `docs_only_stale=true`, and full unit `1893 passed`.
A follow-up Mac-side v519 limit-50 continuation canary is recorded in
`docs/reports/2026-05-20-v519-mac-limit50-continuation-canary.md`. The usable
run copied the checked-in `data/url-discovery/` sources into the sandbox, loaded
114 school-domain overrides, inferred 5 new school overrides, crawled 58 site
rows for 50 selected target-missing schools, found 54 candidate PDFs,
downloaded 0 strict FY2026/R8 PDFs, reported strict `0/50 (0.0%)`,
operator-reviewable `50/50 (100.0%)`, and kept `ship_gate_status=below_gate`.
Its RCA batch has `16 publication_lag_or_old_target_pdf` and
`4 target_form_without_year_evidence` items. This confirms the residual Sanko
Tokyo child-school case now uses `https://www.sanko.ac.jp/tokyo-child/` and
moves to publication-lag evidence, not current-year success.

v520 is a source-side follow-up to the v519 RCA, recorded in
`docs/reports/2026-05-20-v520-katayanagi-url-boundary-package.md`. It adds exact
Katayanagi crawl entries for NEEC/NKHS and guards
`school_domain_override_disclosure` so NEEC yearless `portal/syllabus` PDFs
cannot be counted as FY2026/R8 success. The final limit-3 smoke stays strict
`0/3 (0.0%)`, operator-reviewable `3/3 (100.0%)`, and
`ship_gate_status=below_gate`; full unit reports `1895 passed`.

v521 is a source-side follow-up to v520, recorded in
`docs/reports/2026-05-20-v521-school-override-corporation-suppression-package.md`.
It suppresses same-school `corporation_pattern` rows when usable
`school_domain_override` rows are in the default discovery scope. The Katayanagi
limit-3 smoke now crawls 3 exact rows instead of 6 mixed rows, drops
`candidate_school_mismatch` from 69 to 0, keeps strict `0/3 (0.0%)`, and keeps
`ship_gate_status=below_gate`; full unit reports `1896 passed`.
A follow-up Mac-side v521 limit-50 continuation canary is recorded in
`docs/reports/2026-05-20-v521-mac-limit50-continuation-canary.md`. It loaded
checked-in URL sources, inferred 8 new school overrides, crawled 54 site rows
for 50 selected target-missing schools, found 50 candidate PDFs, downloaded 0
strict FY2026/R8 PDFs, reported strict `0/50 (0.0%)`, operator-reviewable
`50/50 (100.0%)`, `candidate_school_mismatch=0`, and
`ship_gate_status=below_gate`. Its RCA batch has
`17 publication_lag_or_old_target_pdf` and
`3 target_form_without_year_evidence` items. Compared with the v519 canary, the
same source slice now has fewer crawled rows, no failed site rows, and no
same-school corporation-root mismatch noise.

v522 is a source-side RCA hygiene follow-up to v521, recorded in
`docs/reports/2026-05-20-v522-stale-yearless-rca-bucket-source.md`. It keeps
genuine no-year target-form rows in `target_form_without_year_evidence`, but no
longer lets an explicitly stale-labeled no-year/image-only row hide a clearer
old-year target form. Recomputing the v521 limit-50 RCA batch plan moves
school ID 44 `東京ビューティ＆ブライダル専門学校` from
`target_form_without_year_evidence` to `publication_lag_or_old_target_pdf`,
changing the top 20 RCA split from `17/3` to `18/2`. This does not change
strict `0/50 (0.0%)`, operator-reviewable `50/50 (100.0%)`, or
`ship_gate_status=below_gate`; full unit reports `1897 passed`.
A bounded same-domain FY2026 negative probe is recorded in
`docs/reports/2026-05-20-v522-same-domain-2026-negative-probe.md`. It generated
38 simple `2025 -> 2026` candidate URLs and 47 expanded short-year/R7 variants
from the v521 `fiscal_year_mismatch:2025` target-form evidence. HEAD returned
`404` for all 47 expanded candidates, and ranged GET also returned `404` for
all 47. This confirms the visible FY2025 publication-lag URLs do not have a
simple same-domain FY2026/R8 replacement at probe time.

v523 was the package/source rebuild after the v520-v522 follow-ups,
recorded in
`docs/reports/2026-05-20-v523-current-head-package.md`. It was built from
clean source at commit `9a5cefc74751ec849daff86d68ff552f79f376e0`, has SHA256
`5d47ca9e016aa6aadf3608b5799c773a769af585d158813eada1f80cebe762ce`, and
records `git_dirty=false` in `BUILD_INFO.json`. The full non-Windows release
gate reports `ok=true`, full unit `1897 passed`, 47 packaged prefecture seeds,
2148 packaged prefecture school rows, and 45/45 discovery-gold expected
predictions. A direct core + OCR add-on verifier probe also returned core
`ok=true` and OCR add-on `ok=true`. After the tracked v523 status-doc update,
`logs/win-v523-stage6-v523-post-docs-only-gates-20260520.json` records
`ok=true`, `docs_only_stale=true`, and full unit `1897 passed`.

The v523 complete Windows side-by-side smoke is recorded in
`docs/reports/2026-05-20-v523-full-windows-side-by-side-smoke.md`. The ZIP and
OCR add-on were copied to `C:\EIDP-staging`, Windows SHA256 checks matched, and
the package expanded to `C:\Users\cyo20\EIDP-v523-9a5cefc-env0`. Setup and
validation are recorded in
`logs/win-v523-stage6/win-v523-stage6-v523-first-setup-env0-20260520.log`,
`logs/win-v523-stage6/win-v523-stage6-v523-env0-validate-after-setup-20260520.json`
(`ok=true`, `school_count=2418`, `school_fiscal_year_status_count=2418`,
`sqlite_integrity_check=ok`, package commit
`9a5cefc74751ec849daff86d68ff552f79f376e0`), and
`logs/win-v523-stage6/win-v523-stage6-v523-env0-recovery-expected-v485-20260520.json`
(`ok=true`, active task still v485). OCR runtime proof is
`logs/win-v523-stage6/win-v523-stage6-v523-env0-validate-ocr-runtime-20260520.json`
(`ok=true`, Tesseract `v5.4.0.20240606`, `jpn` and `jpn_vert`). UI smoke is
`logs/win-v523-stage6/win-v523-stage6-v523-ui-smoke-20260520.json`
(`ok=true`, port `8523`, health `200/ok`, root `200`, no traceback, stopped
cleanly). Excel smoke is
`logs/win-v523-stage6/win-v523-stage6-v523-excel-summary-20260520.json`
(`ok=true`, master workbook, competition workbook, and gap report generated).
The fresh FY2026/R8 limit-50 canary is recorded in
`logs/win-v523-stage6/win-v523-stage6-v523-last-run-after-weekly-canary-limit50-20260520.json`:
`status=success`, strict/Excel-ready yield `10.0%`,
operator-reviewable yield `100.0%`, and `ship_gate_status=below_gate`. The
run log records discovery `crawled=59`, `found=50`, `downloaded=5`,
`failed=0`, `candidate_school_mismatch=0`, and ingest `processed=5`,
`departments_created=106`, `yearly_upserted=107`. Stage 6 bundle proof is
`logs/win-v523-stage6/stage6-evidence-20260520-043937.zip` with SHA256
`f3e5c7df1444c777eed1e710a99a1bede613b315ca130e4102a94e03d1d4c310`, and
verifier proof is
`logs/win-v523-stage6/stage6-evidence-verify-20260520-133938.json`
(`ok=true`). The residual-cleanup dry run is
`logs/win-v523-stage6/stage6-residual-cleanup-20260520-133934.json`
(`ok=true`, `existing_count=0`, `moved_count=0`), and final recovery proof is
`logs/win-v523-stage6/stage6-recovery-20260520-133934.json` (`ok=true`,
`action_matches_expected=true`, active task still v485). v523 superseded v501
as a complete Windows side-by-side smoke package, but is itself superseded by
v524/v525/v526 and remains below the strict FY2026/R8 release line.

v518 includes all v517 package features plus the Sanko Tokyo child-school
publication-lag gold-set entry. The package verifier reports 45 discovery
gold-set entries and 45 expected predictions. After the tracked docs update,
`logs/win-v518-stage6-v518-post-docs-only-gates-20260520.json` records
`ok=true`, `docs_only_stale=true`, and full unit `1892 passed`.
The package evidence is recorded in
`docs/reports/2026-05-20-v518-gold-set-publication-lag-package.md`.

v517 includes all v516 package features plus remaining Sanko child-school exact
URL overrides for 東京, 横浜, 名古屋, 大阪, and 沖縄こども専門学校. A targeted
school ID 55 smoke confirms the new exact URL is crawled and yields FY2019-FY2025
target-form evidence instead of corporation-only non-target evidence. The
package evidence is recorded in
`docs/reports/2026-05-20-v517-remaining-sanko-child-overrides-package.md`.

v516 includes all v515 package features plus target-missing queue hardening:
the weekly runner now excludes schools that already have current-FY confirmed
target documents in the same ingest statuses used by
`SchoolFiscalYearStatus._pdf_status()`. The package evidence is recorded in
`docs/reports/2026-05-20-v516-weekly-target-missing-selection-package.md`.

v515 includes all v514 package features plus exact Sanko child-school URL
overrides for the three residual v514 RCA cases that only had the shared
corporation URL. The follow-up canary resolves the three exact school roots and
their disclosure pages, moves them into FY2025/R7 target-form evidence, and
keeps strict FY2026/R8 yield at `2/50 (4.0%)`. The package evidence is recorded
in `docs/reports/2026-05-20-v515-sanko-child-overrides-package.md`.

v514 includes all v513 package features plus weekly selected-site count
hardening: school-based weekly limits now expand the downstream PDF-discovery
site-row batch to cover every crawlable site for the selected school IDs. A
focused isolated Mac smoke after the fix crawled the previously skipped NEEC
school IDs 1-3 and kept them as `target_form_without_year_evidence`, not strict
FY2026/R8 successes. The package evidence is recorded in
`docs/reports/2026-05-20-v514-weekly-selected-site-count-package.md`.

v513 includes all v512 package features plus Sanko disclosure probe hardening:
for Sanko exact school roots such as `https://www.sanko.ac.jp/chiba-med/`, the
shared-origin throttle still allows the per-school derived probe
`https://www.sanko.ac.jp/disclosure/chiba-med`. This converts sparse-root
cases from `no_pdf_candidates` into concrete disclosure-page evidence when the
page exists, while preserving the strict rule that stale FY2025 forms do not
count as FY2026/R8 success. The package evidence is recorded in
`docs/reports/2026-05-20-v513-sanko-disclosure-probe-package.md`.

v523 has completed Windows side-by-side validation. v502 remains the historical
partial Windows side-by-side setup/canary package, and v501 remains the
historical complete Windows side-by-side smoke baseline.

v524 is a source/package and Windows side-by-side follow-up to the v523
owner-return verifier coverage audit, recorded in
`docs/reports/2026-05-20-v524-owner-return-verifier-hardening-package.md`.
It extends `scripts/verify_stage6_return.py` so a returned owner/operator
template must include Excel ready proof, always-pass Excel consistency proof,
a nonblank output-file proof block, audit page proof, `manual_action_log`
count, after-flush JSONL outbox count `0`, audit-flush status, and
`JSONL action_id` duplicate status. The red test first proved the old verifier
accepted missing Excel/audit proof; the green verifier slice reports
`14 passed`, the packaging contract slice reports `100 passed`, and the v524
non-Windows release gate reports `ok=true`, package/source fresh, and full
unit `1898 passed`. The complete v524 Windows side-by-side smoke is recorded in
`docs/reports/2026-05-20-v524-full-windows-side-by-side-smoke.md`: setup,
install validation, OCR runtime validation, UI smoke, weekly limit-50 canary,
Excel smoke, residual-cleanup dry run, active-task recovery, and Stage 6
evidence verification all returned `ok=true`. The v524 canary remains strict
`5/50 (10.0%)`, operator-reviewable `50/50 (100.0%)`, and
`ship_gate_status=below_gate`, so this does not unblock v1.0.

v526 includes all v525 package features plus the extracted-PDF
confirmation/supplement UI. The school-year task board now exposes
`抽出済内容を確認・補足` for extracted `confirmed_target` rows that still have a
latest document, and the existing PDF確認・手入力 page preloads current
`DepartmentYearly`, `Department`, and `SupportRecipient` values for that
document. The package evidence is recorded in
`docs/reports/2026-05-20-v526-extracted-confirmation-package.md`. The v526
non-Windows release gate reports `ok=true`, package/source fresh, and full unit
`1901 passed`; complete Windows side-by-side smoke also returned `ok=true` for
setup, install validation, OCR runtime validation, UI smoke, weekly limit-50
canary, Excel smoke, residual-cleanup dry run, active-task recovery, and Stage
6 evidence verification. The v526 canary remains strict `5/50 (10.0%)`,
operator-reviewable `50/50 (100.0%)`, and `ship_gate_status=below_gate`, so
this does not unblock v1.0.

v502 includes all v501 package features plus the v501 RCA follow-up residual
Sanko exact school URL overrides for the two remaining corporation-root cases.
The follow-up package and partial Windows evidence is recorded in
`docs/reports/2026-05-20-v502-residual-sanko-overrides-package.md` and
`docs/reports/2026-05-20-v502-windows-partial-side-by-side-limit50.md`.

Current v502 Windows partial side-by-side validation:
the ZIP and sidecar were copied to `C:\EIDP-staging`, Windows SHA256 matched
the Mac sidecar, and the package expanded to
`C:\Users\cyo20\EIDP-v502-dd1524c-env0`. Setup and validation are recorded in
`logs/win-v502-stage6-v502-first-setup-env0-20260520.log`,
`logs/win-v502-stage6-v502-env0-validate-after-setup-20260520.json`
(`ok=true`, `school_count=2418`, `school_fiscal_year_status_count=2418`,
`sqlite_integrity_check=ok`, package commit
`dd1524c48240890a8260795b54259342d7648867`), and
`logs/win-v502-stage6-v502-env0-recovery-expected-v485-clean-20260520.json`
(`ok=true`, `action_matches_expected=true`). A fresh FY2026/R8 limit-50
canary is recorded in
`logs/win-v502-stage6-v502-last-run-after-weekly-canary-limit50-20260520.json`:
`status=success`, strict/Excel-ready yield `10.0%`,
operator-reviewable yield `84.0%`, and `ship_gate_status=below_gate`.
The post-canary recovery probe is
`logs/win-v502-stage6-v502-recovery-probe-after-limit50-canary-clean-20260520.json`
(`ok=true`, active task still v485). The v502 limit-50 RCA no longer has a
`non_target_candidates_only` bucket; its 20 planned RCA items are
`8 no_pdf_candidates`, `8 publication_lag_or_old_target_pdf`, and
`4 target_form_without_year_evidence`. v502 full Windows smoke remains pending
because the Windows OpenSSH service began resetting new SSH sessions before UI
smoke and Stage 6 evidence-bundle verification completed.

v501 includes all v500 package features plus the v500 RCA follow-up Sanko exact
school URL overrides for medical-secretary and resort/sports schools that were
previously falling back to `https://www.sanko.ac.jp/` corporation-root crawling.
The follow-up package evidence is recorded in
`docs/reports/2026-05-20-v501-sanko-url-overrides-package.md`.

Current v501 Windows side-by-side smoke validation:
the ZIP and sidecar were copied to `C:\EIDP-staging`, Windows SHA256 matched
the Mac sidecar, and the package expanded to
`C:\Users\cyo20\EIDP-v501-d2fa01d-env0`. Setup and validation are recorded in
`logs/win-v501-stage6-v501-first-setup-env0-20260520.log`,
`logs/win-v501-stage6-v501-env0-validate-after-setup-20260520.json`
(`ok=true`, `school_count=2418`, `school_fiscal_year_status_count=2418`,
`sqlite_integrity_check=ok`, package commit
`d2fa01d4f060e803f173ecae59bfb0867dbe3afd`), and
`logs/win-v501-stage6-v501-env0-recovery-expected-v485-clean-20260520.json`
(`ok=true`, `action_matches_expected=true`). A fresh FY2026/R8 limit-50
canary is recorded in
`logs/win-v501-stage6-v501-last-run-after-weekly-canary-limit50-20260520.json`:
`status=success`, strict/Excel-ready yield `10.0%`,
operator-reviewable yield `80.0%`, and `ship_gate_status=below_gate`.
The post-canary recovery probe is
`logs/win-v501-stage6-v501-recovery-probe-lock-after-limit50-canary-20260520.json`
(`ok=true`, active task still v485). The v501 limit-50 RCA is recorded in
`docs/reports/2026-05-20-v501-windows-partial-side-by-side-limit50.md`; its
batch plan had 20 items across 45 total candidates, with buckets
`8 no_pdf_candidates`, `2 non_target_candidates_only`,
`7 publication_lag_or_old_target_pdf`, and
`3 target_form_without_year_evidence`. This improves the v500 limit-50 result
from strict/Excel-ready `4.0%` and operator-reviewable `56.0%` to `10.0%` and
`80.0%`, but remains below the strict FY2026/R8 release line.
OCR runtime proof is
`logs/win-v501-stage6-v501-validate-ocr-runtime-20260520.json` (`ok=true`,
Tesseract `5.4.0.20240606`, `jpn` and `jpn_vert`). UI smoke is
`logs/win-v501-stage6-v501-ui-smoke-20260520.json` (`ok=true`, port `8522`,
health `200/ok`, root `200`, no traceback, stopped cleanly). Excel smoke is
`logs/win-v501-stage6-v501-excel-summary-20260520.json` (`ok=true`, master
workbook, competition workbook, and gap report generated). Stage 6 bundle proof
is `logs/win-v501-stage6-v501-stage6-evidence-20260519-182045.zip` with SHA256
`2270956e1511285b6e0ad5c737faa7766ad1fd7a62e5092ae28bec5c6a186336`, and
verifier proof is
`logs/win-v501-stage6-v501-stage6-evidence-verify-20260520-032045.json`
(`ok=true`). The full v501 Windows-smoke report is
`docs/reports/2026-05-20-v501-full-windows-side-by-side-smoke.md`.

v500/v501/v502 include `EIDP-repair-launcher.bat`,
`scripts/repair_streamlit_launcher.bat`, `scripts/repair_streamlit_launcher.py`,
`scripts/evaluate_strict_yield_bound.py`, the image-pending OCR warning
verifier contract, packaged `.streamlit/config.toml` with
`address = "127.0.0.1"`, the stricter Stage 6 return verifier requiring
`--release-exception-record` when `--release-exception-reason` is used, the
hardened launcher repair helper, and the packaged default competition Excel
template required by `export-competition-excel`. v500 also configures the
registered weekly Task Scheduler entry with retry-on-failure settings
(`RestartCount=3`, `RestartInterval=30 minutes`) during setup and forwards
weekly runner CLI arguments for bounded SSH/operator canaries.

Current v500 Windows side-by-side validation:
the ZIP and sidecar were copied to `C:\EIDP-staging`, Windows SHA256 matched
the Mac sidecar, and the package expanded to
`C:\Users\cyo20\EIDP-v500-e79ac12-env0`. Setup and validation are recorded in
`logs/win-v500-stage6-v500-env0-validate-after-setup-20260520.json`
(`ok=true`, `school_count=2418`, `school_fiscal_year_status_count=2418`,
`sqlite_integrity_check=ok`) and
`logs/win-v500-stage6-v500-env0-recovery-expected-v485-clean-20260520.json`
(`ok=true`, `action_matches_expected=true`, lock not held). OCR runtime proof
is `logs/win-v500-stage6-v500-validate-ocr-runtime-20260520.json`
(`ok=true`, Tesseract `5.4.0.20240606`, `jpn`, `jpn_vert`). UI smoke is
`logs/win-v500-stage6-v500-ui-smoke-20260520.json` (`ok=true`, port `8521`,
health `200/ok`, root `200`). Weekly canary is
`logs/win-v500-stage6-v500-last-run-after-weekly-canary-limit10-20260520.json`
(`status=success`, `current_fy=2026`, `ship_gate_status=below_gate`,
`target_pdf_auto_yield_pct=50.0`, `operator_reviewable_yield_pct=100.0`);
`logs/win-v500-stage6-v500-weekly-canary-limit10-run-20260520.log` confirms
`cli_args --limit 10 --json` and rc `0`. A larger fresh FY2026 limit-50
re-probe is recorded in
`logs/win-v500-stage6-v500-last-run-after-weekly-canary-limit50-20260520.json`
and `logs/win-v500-stage6-v500-weekly-canary-limit50-run-20260520.log`:
`status=success`, denominator `50`, strict/Excel-ready yield `4.0%`,
operator-reviewable yield `56.0%`, and `ship_gate_status=below_gate`.
The limit-50 RCA is recorded in
`docs/reports/2026-05-20-v500-limit50-rca.md`; its batch plan had 20 items,
with 17 `non_target_candidates_only` and 3 `target_form_without_year_evidence`.
Excel smoke is
`logs/win-v500-stage6-v500-excel-summary-20260520.json` (`ok=true`). Stage 6
bundle proof is `logs/win-v500-stage6-v500-stage6-evidence-20260519-161653.zip`
with SHA256 `674e2fdcaf6f09611c7ffd00ecff3c714a3913b6727478dac3df1917102e2a3e`,
and verifier proof is
`logs/win-v500-stage6-v500-stage6-evidence-verify-20260520-011707.json`
(`ok=true`). The active scheduled task stayed on v485 and was verified by
`logs/win-v500-stage6-v500-recovery-probe-lock-after-canary-clean-20260520.json`.
The post-limit-50 recovery probe is
`logs/win-v500-stage6-v500-recovery-probe-lock-after-limit50-canary-20260520.json`
(`ok=true`, lock not held, active task still v485).
The version-specific owner/operator request for any future v500 real cycle is
`docs/runbooks/eidp-v500-owner-request-20260520.txt`.

Superseded v498 Windows side-by-side validation:
the ZIP and sidecar were copied to `C:\EIDP-staging`, Windows SHA256 matched
the Mac sidecar, and the package expanded to
`C:\Users\cyo20\EIDP-v498-555fe01`. Setup and validation are recorded in
`logs/win-v498-stage6-v498-validate-after-setup-20260519.json` (`ok=true`,
`school_count=2418`, `school_fiscal_year_status_count=2418`,
`sqlite_integrity_check=ok`) and in a fresh env0 setup with
`EIDP_REGISTER_WEEKLY_TASK=0`:
`logs/win-v498-stage6-v498-first-setup-env0-20260519.log`,
`logs/win-v498-stage6-v498-env0-validate-after-setup-20260519.json`, and
`logs/win-v498-stage6-v498-env0-recovery-expected-v485-20260519.json`.
OCR runtime proof is
`logs/win-v498-stage6-v498-validate-ocr-runtime-20260519.json` (`ok=true`,
Tesseract `5.4.0.20240606`, `jpn`, `jpn_vert`). UI smoke is
`logs/win-v498-stage6-v498-ui-smoke-20260519.json` (`ok=true`, port `8519`,
health `200/ok`, root `200`). Weekly canary is
`logs/win-v498-stage6-v498-weekly-canary-limit10-20260519.json` (`ok=true`,
`ship_gate_status=below_gate`), and Excel smoke is
`logs/win-v498-stage6-v498-excel-summary-20260519.json` (`ok=true`). Stage 6
bundle proof is `logs/win-v498-stage6-v498-stage6-evidence-20260519-123728.zip`
with SHA256 `9d51bfce550dd1d4dc12843b19ecb0a99e5b06cdcbca655cf4aa1088b02d8199`,
and verifier proof is
`logs/win-v498-stage6-v498-stage6-evidence-verify-20260519-213747.json`
(`ok=true`). The active scheduled task was restored to v485 and verified by
`logs/win-v498-stage6-v498-recovery-expected-v485-after-restore-20260519.json`
(`ok=true`, `action_matches_expected=true`).
Post-status Mac-side strict-yield replay:
`docs/reports/2026-05-18-fy2025-strict-yield-replay.md`. The current local
strict metric / parser / targeted discovery changes described there were an
intermediate below-gate snapshot. They are superseded by the FY2025 limit-1000
NSG/ASO replay above, which reaches `strict=600/1000 (60.0%)` on current source.
These are local replay results, not a Windows active-lane proof.
Historical v526 package support ZIP:
`dist/eidp-windows-v526.zip`
Current v526 SHA256 sidecar:
`dist/eidp-windows-v526.zip.sha256`
Current v526 package build evidence:
`dist/eidp-windows-v526.zip` was built from clean source and validated by the
full non-Windows release gate. It has also completed Windows side-by-side
setup, validation, recovery, OCR runtime proof, UI smoke, Excel smoke,
limit-50 canary, residual-cleanup dry run, and Stage 6 evidence verification.
The active production action remains v485 until an explicit promotion decision
is made.
Current release decision:
do not merge/tag v1.0 or request owner sign-off under the strict current-FY
FY2026 contract. The tracked final-objective audit at
`docs/reports/eidp-current-objective-evidence-checklist.md` does not yet prove
completion.
v526 is package/source verified, Windows side-by-side smoke validated, and
includes the v520/v521/v522 source-side follow-ups, v524 owner-return verifier
hardening, the `1.0.0rc1` metadata bump, and the extracted-PDF
confirmation/supplement UI. The v526 Windows limit-50 canary
remains below gate after v522 RCA reclassification, v502 is partially Windows
side-by-side validated historically, and v526 is the latest complete
Windows-smoke proof.
Current FY2026 production-scale strict proof and owner real Windows cycle
evidence remain incomplete. To continue,
either keep v1.0 blocked until FY2026/R8 public target PDFs become available,
or record an explicit release exception that scopes v1.0 to the mature FY2025
proof instead of the rolling FY2026 ship line.
The version-specific owner/operator request for any future v526 real cycle is
`docs/runbooks/eidp-v526-owner-request-20260520.txt`; it preserves the same
release-decision boundary and must not be treated as approval by itself.
The v526 owner/operator docs were staged on Windows under
`C:\EIDP-staging\v526-owner-docs-20260520`; the final docs ZIP SHA256 is
recorded in `docs/reports/2026-05-20-v526-owner-docs-windows-staging.md`
outside the ZIP to avoid embedding a self-referential hash, and the
post-staging recheck confirmed the active weekly task still points to
`C:\Users\cyo20\EIDP-v485-70e3db4\scripts\weekly_run.bat`.
A follow-up runtime boundary recheck is recorded in
`docs/reports/2026-05-20-v526-runtime-boundary-recheck.md`: the active weekly
task still points to v485, no Streamlit listeners remained on ports
`8523/8524/8525/8526`, and both the v526 side-by-side root and v526 staged docs
directory were present.
The current negative owner-return verifier probe is
`logs/win-v526-stage6-v526-verify-stage6-return-not-approved-exception-20260520.json`
with rc `1`: the v526 exception packet still fails because the exception record
is `NOT_APPROVED`, owner/operator KPI and sign-off rows are blank, and the Excel
and audit proof rows required by the hardened verifier are missing.
Current v480 retroactive Excel matrix:
`logs/release-gate-v480-retroactive-matrix.json`, `ok=true` for FY2025,
FY2024, and FY2023. The case logs
`logs/release-gate-v480-retroactive-fy2025-reference.json`,
`logs/release-gate-v480-retroactive-fy2024-reference.json`, and
`logs/release-gate-v480-retroactive-fy2023-reference.json` all have matching
package/source commit `d5eb1154e55f0d73454ca86618fc0a8ac00e8aef` and business
Excel diffs of `missing_rows=0`, `extra_rows=0`, `differing_fields=0`.
Current v480 Windows side-by-side preflight:
`logs/win-v480-stage6/v480-preflight-result-20260518-211343.json`, `ok=true`.
The ZIP and sidecar were copied to `C:\EIDP-staging`; Windows SHA256 matched
`130ab6957d2444d08b10430cbabec556a139a9194d7b72a9f4082ef41726c635`; the
package expanded to `%USERPROFILE%\EIDP-v480-d5eb115`; `BUILD_INFO.json`
reported `git_commit=d5eb1154e55f0d73454ca86618fc0a8ac00e8aef` and
`git_dirty=false`; `EIDP-setup.bat` returned `rc=0`; and
`scripts\validate_install.bat --after-setup --json` returned `ok=true`,
`errors=[]`, `warnings=[]`. The preflight restored `EIDP Weekly Run` to the
v460 fallback action and `stage6_recovery_check.bat` returned `ok=true` with
`action_matches_expected=true`. This is side-by-side validation only; active
Task Scheduler promotion was not performed.
Current v480 Windows UI smoke:
`logs/win-v480-stage6/v480-ui-smoke-20260518-211858.json`, `ok=true`. A
temporary Streamlit listener was started from `%USERPROFILE%\EIDP-v480-d5eb115`
on `127.0.0.1:8512`, `_stcore/health` returned `200` with content `ok`, the
root page returned HTTP `200`, and the smoke stopped the temporary process
after the check. This did not use the active `8501` operator port.
Previous full non-Windows release-gate package: `dist/eidp-windows-v478.zip`
Previous v478 non-Windows release gate output:
`_temp/v478-non-windows-release-gates.json`, `ok=true`. The ZIP was built
from `git_dirty=false` source and `BUILD_INFO.json` records the same
`34ded9fecf7ddf27f37e9c8e3eee89e624e69260` commit. This package includes the
confidence-gated ingest contract update: low-confidence DepartmentYearly and
SupportRecipient parses now route to review_pending without writing business
table rows. The packaged strict-yield gap analyzer now also reports
`low_confidence_business_row_buckets` and `url_pdf_gap_buckets`, so existing DBs
can be audited for pre-v475 low-confidence business-table residue and for
URL/PDF discovery bottlenecks. Current-source strict yield gap analyzer output:
`_temp/fy2025-targeted-discovery-current-20260518_144205/output/strict-yield-gap-analysis-v476-url-gaps.json`
records full FY2025 status-scope `strict=389/2418`, `broad=494/2418`,
`excel_ready=389/2418`, and `operator_reviewable=714/2418`; it also shows
historical low-confidence business-table residue from the pre-v475 replay:
`department_yearly=132` rows across `86` schools and `support_recipient=23` rows
across `23` schools, all `review_pending` and `is_current=false`. Future
low-confidence rows should not accumulate in Excel-facing tables before
operator review. v478 also counts `discovered` PDF candidates as
operator-reviewable workload because the UI already routes them to `PDF確認`;
on the FY2025 replay this moves operator-reviewable coverage from
`714/2418 (29.5%)` to `755/2418 (31.2%)`, while strict/excel-ready remains
`389/2418 (16.1%)`. The largest URL/PDF buckets are now explicit:
`pref_url + no_target_pdf=617`, `no_url=613`, and
`unknown + no_target_pdf=430`; therefore the next strict-yield lever is URL
coverage and PDF candidate discovery/ranking, with mixed-confidence /
partial-review handling as a secondary workflow lever.
Post-v478 current-source diagnostics add two read-only gap buckets, not a new
Windows package: `109b934` adds `school_mismatch_source_buckets`, and `2526876`
adds `site_source_gap_buckets`. Current-source analyzer outputs are
`_temp/fy2025-targeted-discovery-current-20260518_144205/output/strict-yield-gap-analysis-v479-school-mismatch.json`
and
`_temp/fy2025-targeted-discovery-current-20260518_144205/output/strict-yield-gap-analysis-v480-site-source-gaps.json`.
They keep `strict=389/2418 (16.1%)` and `operator_reviewable=755/2418 (31.2%)`
unchanged, but expose the next discovery/ranking targets: `school_mismatch` is
clustered on dense group hosts such as `www.o-hara.ac.jp=9`,
`storage-production.all-japan.dev=7`, and `www.ohara.ac.jp=4`; non-ready site
host buckets are led by `no_url/no_site=613`,
`unknown/no_target_pdf/www.o-hara.ac.jp=49`,
`unknown/no_target_pdf/www.sanko.ac.jp=40`, and
`pref_url/no_target_pdf/www.all-japan.ac.jp=14`. The parsed
`school_mismatch` samples are mostly sibling-school PDFs, so ingest school-name
guardrails should stay strict; the safe path is better candidate ranking and
URL coverage, not alias broadening.
`fd78972` adds `no_url_corporation_buckets`, with current-source output at
`_temp/fy2025-targeted-discovery-current-20260518_144205/output/strict-yield-gap-analysis-v481-no-url-corporations.json`.
The largest no-site URL coverage gaps are `国立病院機構=26`,
`有坂中央学園=8`, `山崎学園=6`, `厚生労働省=5`,
`国際ビジネス学院金沢=5`, and `平松学園=5`. This points to audited
corporation-domain / school-domain seed additions as the next offline-safe URL
coverage task. The current Mac environment has no Scrapling optional runtime
and no Brave/Google/Serper API key, so `school_url_auto_crawl` is not available
as a reliable local v1.0 unblock path.
`c7c23d1` promotes the checked-in `discovered-urls-50.csv` corporation evidence
for `八文字学園` into `data/url-discovery/corporation_domains.csv`
(`https://www.mito.ac.jp/`). A replay-DB copy smoke
(`_temp/url-seed-smoke/eidp-hachimonji-smoke.sqlite3`) showed
`infer_corporation_urls` adding the corporation-pattern URL for four currently
no-url Hachimonji schools (`420`-`423`) while leaving the existing seed CSV row
for `424` intact. This is a small offline URL-coverage improvement; it does not
change the current v478 package or the FY2025 strict replay numbers until the
URL inference and downstream PDF discovery are rerun.
`e642f75` adds a read-only proposal tool,
`scripts/propose_no_url_corporation_domains.py`, to cross-check
`no_url_corporation_buckets` against checked-in `discovered-urls-50.csv`
corporation evidence while excluding already registered `corporation_domains`.
Running it against the current v481 replay output produced `proposals=0` at
`_temp/fy2025-targeted-discovery-current-20260518_144205/output/no-url-corporation-domain-proposals-v482.json`.
That negative result means the repo-local audited corporation-root evidence has
been exhausted after the Hachimonji promotion; remaining no-url schools need new
operator-reviewed or externally verified URL evidence rather than automatic
domain guessing.
`a33cd4c` adds a dense/group-page safety improvement for downloaded candidates:
when a target-looking PDF is downloaded but its own `学校名` field names a
different school, discovery now removes the temporary file, records
`pdf_school_mismatch`, and continues to the next candidate instead of storing a
Document that ingest will later mark `school_mismatch`. This keeps existing
link-text sibling-school guardrails strict while addressing generic dense-page
cases such as All-Japan `academic_support.pdf`, where the link text does not
name the school and the mismatch is only visible inside the PDF body. Focused
verification: `uv run pytest tests/unit/test_pdf_discovery.py -q` -> `205
passed`; `uv run ruff check src/eidp/scraper/pdf_discovery.py
tests/unit/test_pdf_discovery.py` -> clean; `uv run mypy
src/eidp/scraper/pdf_discovery.py` -> clean. Current replay metrics are not
updated until the FY2025 discovery replay is rerun from this source.
`8542a32` tightens that downloaded-PDF identity check: link-stage school
matching still allows known campus-suffix variants, but a PDF body's own
`学校名` must now match the target school or an alias exactly after
normalization. A copied-DB All-Japan smoke at
`_temp/all-japan-pdf-mismatch-smoke/` deleted prior Documents for school IDs
`293`-`299` and reran targeted discovery. It produced `crawled=7`,
`downloaded=5`, `rejection_reason_pdf_school_mismatch=54`, and stored exact
body-name matches for schools `293`, `295`, `296`, `297`, and `298`; schools
`294` and `299` remained failed rather than accepting sibling/campus PDFs. This
confirms the fix removes stale `school_mismatch` writes and surfaces remaining
name-alias/ranking gaps without weakening school identity.
`f889416` adds a distinct `school_identity_mismatch` bucket for downloaded-PDF
body-name mismatches in the discovery evidence summary. Running
`eidp summarize-discovery-evidence --evidence-log
_temp/all-japan-pdf-mismatch-smoke/output/discovery-rejections.jsonl --json`
returned bucket counts `accepted_target_pdf=5` and
`school_identity_mismatch=2`, matching the copied DB result and making the two
remaining schools visible as identity/alias work rather than generic
`non_target_candidates_only`.
`1f473d3` surfaces that bucket in the operator task board as
`学校名不一致`, so the `PDF探索ログ` filter can isolate downloaded PDFs whose
body `学校名` disagrees with the target school. Focused verification:
`uv run pytest tests/unit/test_review_school_year_tasks.py -k discovery_evidence
-q` -> `4 passed`; `uv run ruff check
src/eidp/review/_pages/school_year_tasks.py
tests/unit/test_review_school_year_tasks.py` -> clean; `uv run mypy
src/eidp/review/_pages/school_year_tasks.py` -> clean.
Current-source All-Japan group-page ranking now carries nearby WordPress
`wp-block-group` school headings into generic `academic_support.pdf` candidates
and recognizes leading-form `専門学校...` school names plus ampersand school
names after NFKC normalization. A copied-DB smoke at
`_temp/all-japan-group-context-smoke/` reran school IDs `293`-`299` from a
cleaned copy of the FY2025 replay DB. It improved the All-Japan slice from the
prior exact-body smoke `downloaded=5`, `failed=2` to `downloaded=6`, `failed=0`
with accepted target PDFs for `293`, `295`, `296`, `297`, `298`, and `299`;
school `299` now resolves to the exact杉並 legal-school PDF
`.../16221134/academic_support.pdf`, and `298` keeps the exact杉並 IT-school PDF
`.../16213658/academic_support.pdf`. School `294` remains
`school_identity_mismatch`: the current target page and URL context match, but
the PDF body reports `東京IT会計プログラミング&会計専門学校`, so it still needs
operator-reviewed alias evidence rather than automatic acceptance. Focused
verification: `uv run pytest tests/unit/test_pdf_discovery.py -q` -> `209
passed`; `uv run ruff check src/eidp/scraper/pdf_discovery.py
tests/unit/test_pdf_discovery.py` -> clean; `uv run mypy
src/eidp/scraper/pdf_discovery.py` -> clean.
An expanded copied-DB smoke at `_temp/all-japan-expanded-smoke/` reran every
school with an All-Japan `school_site` (`40` sites). It produced
`downloaded=23`, `failed=15`, and evidence summary buckets
`accepted_target_pdf=23`, `school_identity_mismatch=1`,
`non_target_candidates_only=15`. The public disclosure-page slice `289`-`312`
now accepts all available exact current-year target PDFs except school `294`;
the remaining `486` / `2280`-series failures are root/corporation URL paths that
surface non-target candidates only and need separate URL/path evidence rather
than sibling-PDF broadening.
Running `ingest-pdfs`, `rebuild-school-year-tasks`, and
`analyze_strict_yield_gaps.py` on the same copied DB showed the strict/excel-ready
impact: `strict_target_parsed_schools=408/2418 (16.9%)`,
`broad_confirmed_target_schools=514/2418 (21.3%)`, and
`excel_ready_schools=408/2418 (16.9%)`. Compared with the current v481 replay
status-scope `strict=389`, `broad=494`, this local copied-DB experiment adds
`+19` strict/excel-ready schools and `+20` broad confirmed schools. The
operator-reviewable count from this copied rebuild is not comparable to v481
because the rebuild used only the scoped All-Japan evidence log, not the full
FY2025 replay discovery evidence.
Current local O-Hara follow-up gives `www.o-hara.ac.jp` a host-specific first
derived disclosure URL, `https://www.o-hara.ac.jp/about/joho/`, and lets that
single high-confidence URL bypass shared-origin derived fallback throttling.
Focused unit coverage proves both the root-site ordering and the shared-origin
throttle bypass. A copied-DB smoke at `_temp/o-hara-about-joho-smoke-small/`
reran five O-Hara root-site schools (`179`, `180`, `182`, `183`, `205`) after
deleting their existing `Document` and `CrawlJob` rows. It produced
`crawled=5`, `found=5`, `downloaded=1`, `failed=0`, and
`shared_origin_derived_fallback_skipped=0`; school `205`
`大原簿記公務員専門学校千葉校` accepted
`https://www.o-hara.ac.jp/about/joho/pdf/2025-1-29-01-5.pdf` from
`page_url=https://www.o-hara.ac.jp/about/joho/` with `year_evidence=url_hint`.
The remaining sampled failures are mostly dense-page school-name mismatch /
rename evidence issues, for example the DB target `大原簿記公務員情報医療専門学校函館校`
versus the public PDF label `大原公務員・医療事務・語学専門学校函館校`, so the next
O-Hara layer is per-school candidate selection plus operator-reviewed alias
evidence rather than broad school-name acceptance.
Current local Sanko follow-up adds `22` exact school-site overrides to
`data/url-discovery/school_domain_overrides.csv`. Each added URL was live-checked
on 2026-05-18 with HTTP `200` and a `<title>` matching the target school name;
title mismatches, HTTP `503`, and HTTP `404` candidates were excluded. A
copied-DB write smoke at `_temp/sanko-overrides-smoke/` confirmed
`infer_corporation_urls(..., data_dir=Path("data"))` adds exactly `22` Sanko
`school_domain_override` rows. Targeted discovery over those 22 schools produced
`crawled=44`, `found=44`, `downloaded=9`, `failed=22`, accepting target PDFs for
schools `16`, `23`, `25`, `31`, `37`, `54`, `59`, `60`, and `68`, for example
`https://www.sanko.ac.jp/disclosure/chiba-med/docs/yoshiki2025.pdf`. After
`ingest-pdfs`, `rebuild-school-year-tasks`, and `analyze_strict_yield_gaps.py`
on that copied DB, strict/excel-ready moved from the v481 status-scope baseline
`389/2418 (16.1%)` to `397/2418 (16.4%)`, and broad confirmed moved from
`494/2418 (20.4%)` to `503/2418 (20.8%)`. This is a real offline URL-coverage
improvement, but remaining Sanko failures still require candidate ranking,
year-evidence, or school-name evidence work.
The follow-up school-label normalization patch handles low-risk Sanko
orthographic variants such as `AI&IT` vs `AIアンドIT`, `ビューティー` vs
`ビューティ`, and full-width `＆` vs ASCII `&` consistently in discovery and
ingest. A fresh copied-DB smoke at
`_temp/sanko-school-label-smoke-20260518_181242/` over the same 22 exact-site
schools produced `crawled=22`, `found=22`, `downloaded=18`, `failed=0`, and
`candidate_school_mismatch=0`; accepted schools were `16`, `23`, `25`, `26`,
`28`, `31`, `37`, `39`, `43`, `46`, `47`, `48`, `49`, `50`, `54`, `59`, `60`,
and `68`. After ingest, rebuild, and `analyze_strict_yield_gaps.py`,
strict/excel-ready reached `404/2418 (16.7%)` and broad confirmed reached
`510/2418 (21.1%)`, a `+15` strict/excel-ready improvement over the v481
status-scope baseline and `+7` over the exact-site-only Sanko replay.
`7a418d0` adds the next safe Sanko exact-site slice and CJK variation-selector
school-name normalization. The checked-in override set now also covers
`大阪ウェディング＆ブライダル専門学校`, `東京墨田看護専門学校`,
`辻学園調理製菓専門学校`, and `辻学園栄養専門学校`; current `&IT` URLs that
appear to be rename/successor-school cases were deliberately excluded. A
copied-DB smoke at `_temp/sanko-more-overrides-smoke-20260518_182258/` showed
school IDs `77` and `78` now download their 2025 target PDFs with
`candidate_school_mismatch=0`. After targeted ingest and rebuild, IDs `67`,
`78`, and `79` were strict/excel-ready, while `77` was target-PDF
operator-reviewable (`review_pending`, 4 rows). The copied-DB status-scope
strict/excel-ready count reached `408/2418 (16.9%)`, with broad confirmed
`516/2418 (21.3%)`. This is a real small improvement but remains far below the
60-70% strict ship line.
GitHub branch protection remains unset as of 2026-05-18: read-only
`gh api repos/ShunmeiCho/EIDP/branches/main/protection` and
`gh api repos/ShunmeiCho/EIDP/branches/sprint8-handoff-finalize/protection`
both returned HTTP `404` / `Branch not protected`. No admin-side `PUT` was
performed from this Mac-side cleanup pass.
Latest GitHub-pushed v466 package source head validated by GitHub CI:
`9a5d50b556484d89b30a2c349d5ee5b01ff0f195`
Latest GitHub CI status for that v466 package source: push run `25990716165`
and pull-request run `25990716814` completed with `conclusion=success`
Latest v466 operator companion docs: `dist/eidp-v466-operator-docs-20260517.zip`,
SHA256 `71a9a8d7e6616c662b499a6bea59293aab8dd6f8eb573e94efa992c32ff6c1e8`
Latest v466 handoff manifest: `dist/eidp-v466-handoff-manifest-20260517.txt`,
SHA256 `4501cf7bd1e43616c0305480e88fa4949e0cb2fcdcbff89d0776e11dbaa061ed`
Prior Mac retroactive-matrix package: `dist/eidp-windows-v463.zip`, commit
`4de0aa8c3021cb5a2ac2e29ba5fc36a24fcc6582`, SHA256
`81ffabd2d538e5b9757d7096b383acba5b081c9ee82c389184bb59676e38e3e0`
Prior Windows side-by-side cache package: `dist/eidp-windows-v462.zip`, commit
`e1da33fa50a651f9059e9562be5bf0e381b6fa32`, SHA256
`1b783b640e6c25249dd8efd6d8355aeed986c7ecad80c72c98bd4e168360a59a`; not the
current Windows scheduled-task execution pointer
Prior post-package docs rebuild: `dist/eidp-windows-v461.zip`, commit
`b787a72bb1714b77583e4c0e904b1584fdaeba92`, SHA256
`2c0d74ab382bf179f166bdb4d775cd414a08741eca3b27ba92c2e6c7a459850b`; not the
current Windows scheduled-task execution pointer
Latest Windows-core-validated package: `dist/eidp-windows-v466.zip`
Latest Windows-transfer-proven package: `dist/eidp-windows-v466.zip`
Latest Windows-release-artifact-pruner-proven package: `dist/eidp-windows-v460.zip`
Latest Windows-recovery-parser-proven package: `dist/eidp-windows-v460.zip`
Latest Windows-evidence-verifier-proven package: `dist/eidp-windows-v464.zip`
Latest Windows-return-artifact-verifier-proven package: `dist/eidp-windows-v464.zip`
Latest Windows-disk-health-proven package: `dist/eidp-windows-v464.zip`
Latest Windows-OCR-runtime-proven package: `dist/eidp-windows-v384.zip`
Latest Windows-OCR-image-write-proven package: `dist/eidp-windows-v384.zip`
Latest Windows-setup-proven package: `dist/eidp-windows-v466.zip`
Latest Windows-target-FY-ingest-override-canary-proven package: `dist/eidp-windows-v463.zip`
Latest Windows-shared-HTTP-cache-canary-proven package: `dist/eidp-windows-v462.zip`
Latest Windows-UI-health-proven package: `dist/eidp-windows-v466.zip`
Latest Windows-default-launcher-proven package: `dist/eidp-windows-v459.zip`
Latest Windows-browser-readonly-nav-proven package: `dist/eidp-windows-v466.zip`
Latest Windows-R7-browser-Excel-proven package: `dist/eidp-windows-v464.zip`
Latest Windows-UI-write-sandbox-proven package: `dist/eidp-windows-v459.zip`
Latest Windows-bounded-backend-smoke package: `dist/eidp-windows-v459.zip`
Latest Windows-bounded-bootstrap-proven package: `dist/eidp-windows-v459.zip`
Latest historical Windows-validated package: `dist/eidp-windows-v376.zip`
Current Stage 6 evidence bundle: Plan A CLI bundle
`C:\Users\<operator>\EIDP-v460-01e4427\logs\stage6-evidence-20260516-094432.zip`
verified with `ok=true`, but the KPI remained `not_measured`; latest bounded
support bundle before that was
`C:\Users\<operator>\EIDP-v459-50152a5\logs\stage6-evidence-20260516-070115.zip`
Current post-bootstrap FY2026 weekly probe: stopped after about 9h41m because
the run repeatedly re-crawled shared corporation domains; it produced no new
`last_run.json` and is not release evidence
Current Stage 6 evidence draft: `docs/reports/eidp-v460-stage6-evidence-draft.md`
Current Stage 6 real-cycle card: `docs/runbooks/eidp-v460-real-cycle-card.md`
Current active-goal completion audit:
`docs/reports/2026-05-17-active-goal-completion-audit.md`

## Verdict

Release conclusion: **NOT_READY**

Current local package source head `34ded9fecf7ddf27f37e9c8e3eee89e624e69260` is
Mac-validated with `1803 passed`, `mypy src` clean, CI-scope Ruff clean,
Bandit high-severity clean, and
`scripts/run_non_windows_release_gates.py dist/eidp-windows-v478.zip --skip-full-unit --json`
returning `ok=true`. A clean successor package `dist/eidp-windows-v478.zip`
was built from that head without `--allow-dirty`; `BUILD_INFO.json` records
`git_dirty=false`, SHA256 is
`9abf7ab7686815130ed60eb49cd2cdfdd97887e4d6ac77e61208c822ced3e5c0`, and
`scripts/verify_windows_distribution.py` returned `ok=true`. The package also
updates the distribution verifier to enforce the confidence-gated ingest
contract, so a future ZIP that reintroduces low-confidence business-table writes
will fail package verification. It also packages a strict-yield gap analyzer
field that surfaces low-confidence business-table residue and URL/PDF discovery
buckets in existing DBs. v478 additionally aligns the operator-reviewable
metric with the UI by counting `discovered` PDF candidates as reviewable rather
than manually missing. After
this status note, the docs-only stale-package replay path must be rerun against
v478 if more status-only edits
are added. The latest
GitHub-pushed v466 package source
`9a5d50b556484d89b30a2c349d5ee5b01ff0f195` remains CI-green on GitHub. This
removes the previous CI-red blocker caused by `python -m pip download` running
without `pip` in the uv-managed environment.
The v466 package was then transferred to Windows staging as
`C:\EIDP-staging\eidp-windows-v466.zip`, SHA-checked against the same
`8712c5b...` digest, and expanded side-by-side to
`C:\Users\<operator>\EIDP-v466-9a5d50b`. `EIDP-setup.bat` returned `0`,
`scripts\validate_install.bat --after-setup --json` returned `ok=true`,
`warnings=[]`, and `errors=[]`, and `scripts\diagnose.bat` returned `0`.
Because setup rewrites the weekly scheduled task, the `EIDP Weekly Run` task was
restored to the v460 runner afterward; `scripts\stage6_recovery_check.bat` on
v460 returned `ok=true` with `action_matches_expected=true`, and a fresh
scheduled-task XML check still executes
`C:\Users\<operator>\EIDP-v460-01e4427\scripts\weekly_run.bat`.
The Mac evidence copies are
`logs/win-v466-stage6/v466-preflight-result-20260517-215028.json`
(SHA256 `c59e8fdb0e4085a64fdc0f883268f2aae7c89bb7c86771a474377c2a51458c48`),
`logs/win-v466-stage6/v466-validate-install-after-setup-20260517-215028.json`
(SHA256 `282db3597db54eb9d54ac46e5dff575e2a5025f115ee8efab7dfa5f92e4d72d7`),
`logs/win-v466-stage6/stage6-recovery-20260517-215355.json`
(SHA256 `8efd41d2d9d80fd1b1744f0515fe827f131819228f4b460d73e8da475a468e4a`),
`logs/win-v466-stage6/v466-diagnose-20260517-215028.txt`
(SHA256 `fd4d056f0a9aa785550ffd57fef128a6dd1136b6e1ec264229f63368baa7b35b`),
and `logs/win-v466-stage6/v466-setup-preflight-20260517-215028.log`
(SHA256 `dcdb878fe997076a4292cbf0bd4ce46b70068d3f27ed358f8eda4c5f134c8f46`).
This does not by itself approve release: the active Scheduled Task still points
to v460, no v466 owner/operator real cycle has produced final KPI,
audit/outbox, evidence ZIP, or sign-off artifacts, and v465 remains only a
staged stale cache/perf candidate.

v466 is now the latest Mac/non-Windows release-gate-clean, Windows setup-proven,
and Windows UI-health/read-only navigation package. After setup validation, a
v466 side-by-side UI smoke started Streamlit directly on Windows
`127.0.0.1:8511`, verified Windows-local health and Mac tunnel
`127.0.0.1:18511 -> 127.0.0.1:8511`, and clicked only the read-only quick
navigation buttons for `① 学校別タスク`, `② PDF確認・手入力`,
`③ 年度判定・修正`, `④ Excel プレビュー`, and
`⑤ 設定（年度・OCR・API）`. `output/playwright/v466-ui-smoke/summary.json`
records `ok=true`, `has_v466_build=true`, `has_target_fiscal_year=true`,
`target_fiscal_year_text=2026年度（令和8年度）`,
`has_error_traceback=false`, `nav_all_clicked=true`,
`write_actions_invoked=false`, and `weekly_invoked=false`. Screenshots
`v466-ui-smoke-00-home.png` through `v466-ui-smoke-05-settings.png` were
captured, cleanup closed local `18511` and Windows `8511`, and a fresh
scheduled-task XML check still executes the v460 weekly runner.

v464 remains the latest broader Windows side-by-side support package with R7
Excel/evidence guard/return verifier proof. v464 was built from
`9a94226b243fba691936db46c1fc11ef7c9debbd`, adds the packaged
`scripts/verify_stage6_return.py` owner-artifact verifier, and keeps the v463
explicit `target_fiscal_year` propagation through ingestion. Its SHA256 sidecar
is `6b95d9f3e06d70a0018119b2665070cf3af735e01b61920f6492234e174bd378`, and
`uv run python scripts/run_non_windows_release_gates.py
dist/eidp-windows-v464.zip --json --output logs/release-gate-v464.json`
returned `ok=true`: SHA256 sidecar matched, package/source commit matched, full
unit returned `1673 passed`, validator distribution unit returned `166 passed`,
validator mypy/Ruff passed, discovery-gold checks passed, package verification
passed, and demonstrated-pattern package verification passed.
v464 was then transferred side-by-side to Windows staging, SHA-checked against
the sidecar, extracted to `C:\Users\<operator>\EIDP-v464-9a94226`, set up with
`EIDP-setup.bat` exit `0`, and independently validated with
`scripts\validate_install.bat --after-setup --json` returning `ok=true`,
`warnings=[]`, and `errors=[]`. Because setup rewrites the weekly scheduled
task, the `EIDP Weekly Run` task was restored to the v460 runner afterward;
`scripts\stage6_recovery_check.bat` on v460 then returned `ok=true` with
`action_matches_expected=true`. The Mac copies are
`logs/win-v464-stage6/validate-install-after-setup-20260517-073352.json`
(SHA256 `b4ea61ed6eaf4c7a97fc1885ba9f4efdcf90d9bb74ba968e9e8799f443ab66e6`)
and
`logs/win-v464-stage6/post-v464-restore-stage6-recovery-20260517-073334.json`
(SHA256 `8efd41d2d9d80fd1b1744f0515fe827f131819228f4b460d73e8da475a468e4a`).
v464 has still not replaced the active scheduled-task pointer, and no v464
weekly, evidence-bundle, or owner/operator cycle has been run. A v464
side-by-side read-only UI smoke then started Streamlit on Windows
`127.0.0.1:8508`, verified Windows-local `/_stcore/health=ok`, opened a Mac
SSH tunnel on `127.0.0.1:18508`, and clicked only the quick navigation buttons
for `① 学校別タスク`, `② PDF確認・手入力`, `③ 年度判定・修正`,
`④ Excel プレビュー`, and `⑤ 設定（年度・OCR・API）`.
`output/playwright/v464-ui-smoke/summary.json` records `ok=true`,
`has_v464_build=true`, `has_japanese_ui=true`, `has_target_fiscal_year=true`,
`has_error_traceback=false`, `nav_all_clicked=true`, `write_actions_invoked=false`,
and `weekly_invoked=false`; screenshots `00-home.png` through
`04-settings.png` were captured. Cleanup stopped the remote `8508` listener and
the local `18508` tunnel, and a fresh scheduled-task check still pointed to the
v460 runner.
A process-scoped v464 FY2025/R7 browser Excel smoke then started the same
side-by-side package with `EIDP_TARGET_FISCAL_YEAR=2025` on Windows
`127.0.0.1:8509`, opened a Mac SSH tunnel on `127.0.0.1:18509`, rendered
`④ Excel プレビュー` with `対象年度: 2025年度（令和7年度）`, generated the
preview workbook, exposed `Excel ダウンロード`, and downloaded
`output/playwright/v464-r7-excel-smoke/eidp_master.xlsx`. The summary
`output/playwright/v464-r7-excel-smoke/summary.json` returned `ok=true` with
`write_actions_invoked=false` and `weekly_invoked=false`; the downloaded
workbook SHA256 is
`aff3dea57af4c6d96d8859e52748f8cecefb4e593f5da74b4f68646175937685`.
`openpyxl` verified the four sheets and data-row counts matching the UI:
`採録状況=2418`, `対象比率=10022`, `学科別=9719`, and `在籍のみ抜粋=9719`
with dimensions `2419x10`, `10023x22`, `9721x83`, and `9721x19`. Cleanup
stopped the remote `8509` listener and local `18509` tunnel, and a fresh
scheduled-task check still pointed to the v460 runner.
A diagnostic v464 evidence-bundle smoke then created
`C:\Users\<operator>\EIDP-v464-9a94226\logs\stage6-evidence-20260516-225040.zip`;
packaged verification correctly returned `ok=false` with
`missing_required_labels=["last_run"]`, proving setup/UI smoke evidence cannot
pass as Stage 6 release evidence. The Mac copies are
`logs/win-v464-stage6/stage6-evidence-20260516-225040.zip`
(SHA256 `1872e53e747ef85c89152bbeba8659a5068a5c52929e83f62398a011f198cefa`),
`logs/win-v464-stage6/stage6-evidence-verify-20260517-075050.json`
(SHA256 `a9471ba1af8236b50ab2c77a403616139c6a7bfd11fe99f36f4be24524df80dc`),
and `logs/win-v464-stage6/diagnostics-20260517-075037.txt`
(SHA256 `d58124385eba406e17a2f296f3d4aa191e05ac79790e186d46e5043c7d056ce2`).
The packaged v464 return-artifact verifier was also executed on Windows against
the current v460 Plan A `last_run.json`, verifier JSON, and still-blank E2E
template. It exited `1` and returned `ok=false`, rejecting the return because
KPI values were unmeasured and sign-off/template fields were still blank. The
Mac copy is
`logs/win-v464-stage6/verify-stage6-return-plan-a-reject-20260517-0754.json`
with SHA256
`bfab702236911a73f516a83c47e2e94ac1710e44cf6c7024885d43bc5473f310`.
The packaged v464 disk-health check
`scripts\disk_health_check.py --profile operator-win --json` returned `ok=true`,
`warn_count=0`, and `block_count=0`: app root `844.1MiB`, `data/pdfs=0B`,
`data/output=0B`, `logs=12.8KiB`, and protected
`data/audit/manual-actions.jsonl` missing because no operator action has run in
the v464 side-by-side lane. The Mac copy is
`logs/win-v464-stage6/disk-health-20260517-operator-win.json` with SHA256
`2ff02db2fff92af7f911f6c60546e7a7287c7bf059502fac4ec8d2b2d517003a`.
The v463 Mac retroactive Excel matrix
`logs/release-gate-v463-retroactive-matrix.json` also returned `ok=true` for
FY2025, FY2024, and FY2023. The references were regenerated from the frozen
v459 package wheel plus the v459 ZIP `alembic.ini`/`migrations` into
`_temp/v459-reference2-fy2025/`, `_temp/v459-reference2-fy2024/`, and
`_temp/v459-reference2-fy2023/`; v463 isolated exports matched those old-package
references with `missing_rows=0`, `extra_rows=0`, and `differing_fields=0` for
all three years. The earlier raw `data/master.xlsx` attempt was a reference
selection error, because that workbook contains later-year fields and is not a
FY-specific pass/fail reference.
After the v463 proof generation, Mac `scripts/disk_health_check.py --json` reported
`ok=true`, `warn_count=1`, and `block_count=0`: project `2.4GiB`, `dist=1.3GiB`
(`warn`), `_temp=80.9MiB` (`ok`), `logs=14.3MiB` (`ok`), protected
`data=20.0MiB`, and `.claude/worktrees=0B`. The retained v459-v464 packages and
v459-derived reference workbooks are part of the current evidence chain, so no
release-artifact pruning was performed automatically.

v463 remains the latest Windows target-FY override canary package. It was
transferred side-by-side to Windows staging, SHA-checked with
`certutil` against the sidecar, extracted to
`C:\Users\<operator>\EIDP-v463-4de0aa8`, set up with `EIDP-setup.bat` exit `0`, and
validated with `scripts\validate_install.bat --after-setup --json` returning
`ok=true`, `warnings=[]`, and `errors=[]`. Because setup rewrites the weekly
scheduled task, the `EIDP Weekly Run` task was immediately restored to the v460
runner and `scripts\stage6_recovery_check.bat` on v460 returned `ok=true` with
`action_matches_expected=true`. A v463 Windows package-local FY override canary
using a temp SQLite DB returned `ok=true`: forecast ingestion with
`settings_target_fiscal_year=2026` and scoped `target_fiscal_year=2027` wrote
`document_fiscal_year=2027` with `document_is_current_year=true`, and
retroactive ingestion with `settings_target_fiscal_year=2027` and scoped
`target_fiscal_year=2026` wrote `document_fiscal_year=2026` with
`document_is_current_year=true`. The Mac copy is
`logs/win-v463-fy-override-canary/fy-override-canary-result.json`. v463 has
still not replaced the active scheduled-task pointer, and no v463 UI-health,
weekly, evidence-bundle, or owner/operator cycle has been run.

v462 remains the latest Windows side-by-side cache package. It was transferred
side-by-side to Windows staging, SHA-checked against
the same sidecar, extracted to `C:\Users\<operator>\EIDP-v462-e1da33f`, set up with
`EIDP-setup.bat` exit `0`, and validated with
`scripts\validate_install.bat --after-setup --json` returning `ok=true`,
`warnings=[]`, and `errors=[]`. Because setup rewrites the weekly scheduled
task, the `EIDP Weekly Run` task was immediately restored to the v460 runner and
`scripts\stage6_recovery_check.bat` on v460 returned `ok=true` with
`action_matches_expected=true`. A v462 Windows package-local stub cache canary
using a copied temp SQLite DB then returned `ok=true` with `crawled=2`,
`http_cache_hits=9`, `http_cache_misses=7`, `call_count=7`, and
`shared_url_call_count=1`; the Mac copy is
`logs/win-v462-cache-canary/cache-canary-stub-result.json`. This proves the
packaged run-scoped HTTP cache behavior on Windows without touching the real
v460 runtime DB or owner-cycle state. v462 has still not replaced the active
scheduled-task pointer, and no v462 UI-health, weekly, evidence-bundle, or
owner/operator cycle has been run.

v460 remains the current Windows setup/recovery execution candidate at
`C:\Users\<operator>\EIDP-v460-01e4427`; the scheduled task has not been moved to
v461, v462, v463, or v464 as the active owner-cycle pointer. v460 was built from package snapshot
`01e44279238aaef9127ed9b578e29dc8e0070499` after the v460 Mac-side operator
workflow hardening and version-neutral E2E template update. The operator-cycle
hardening keeps Excel preview workbook handles out of Streamlit session state,
disables manual-entry row-count writes while the app lock is held, prunes stale
manual-entry widget keys for deleted rows, and closes discovery evidence
recorders through exception paths. Its SHA256 sidecar is
`ce5fa49b8c30900a33b31fd317c6846ffe5839053f2bdd1ffdeb8cca2113129c`, and
`uv run python scripts/run_non_windows_release_gates.py
dist/eidp-windows-v460.zip --json --output logs/release-gate-v460.json`
returned `ok=true` for SHA256 sidecar, package/source commit match, full unit
`1665 passed`, validator distribution unit/mypy/Ruff, discovery-gold checks,
package verify, and demonstrated-pattern package verify.
`docs/runbooks/eidp-v460-real-cycle-card.md` still carries the owner/operator
request for the final Stage 6 real-cycle run and the minimum evidence that must
come back before v1.0 can be approved.

Windows transfer of v460 to `C:\EIDP-staging` matched the sidecar SHA, and
staging retains v460 current plus v459 fallback ZIPs, with later v462/v463/v464
side-by-side proof ZIPs kept separately. Extraction to
`C:\Users\<operator>\EIDP-v460-01e4427` succeeded with BUILD_INFO commit
`01e44279238aaef9127ed9b578e29dc8e0070499`. `EIDP-setup.bat` exited `0`,
bootstrap/import completed with `school_count=2418`,
`school_fiscal_year_status_count=2418`, `sqlite_integrity_check=ok`,
`sqlite_table_count=15`, and `wheel_count=78`; packaged
`scripts\validate_install.bat --after-setup --json` returned `ok=true`.
Recovery check with expected action
`C:\Users\<operator>\EIDP-v460-01e4427\scripts\weekly_run.bat` returned `ok=true`
and `action_matches_expected=true`. The `EIDP Weekly Run` scheduled task now
executes `"C:\Users\<operator>\EIDP-v460-01e4427\scripts\weekly_run.bat"`.
Root `EIDP-diagnose.bat` wrote
`C:\Users\<operator>\EIDP-v460-01e4427\logs\diagnostics-20260516-170035.txt`; the
Mac copies under `logs/win-v460-stage6/` have SHA256
`6b4d566433db64c730737f925f0559e9b06582eed4cb0b6cd51f0623f153b445` for
diagnostics and
`41dd47aee0a304371cab5633397017f45e4f1a1d090b186986d48c49cf38acf6` for the
recovery JSON. A read-only v460 UI smoke then started Streamlit directly on
Windows `127.0.0.1:8501`, verified `_stcore/health=ok`, opened a Mac SSH tunnel
on `127.0.0.1:18506`, and clicked `① 学校別タスク`,
`② PDF確認・手入力`, `④ Excel プレビュー`, and
`⑤ 設定（年度・OCR・API）`. `output/playwright/v460-ui-smoke/summary.json`
recorded `hasV460Build=true`, `hasJapaneseUi=true`,
`hasTargetFiscalYear=true`, `hasErrorTraceback=false`, and
`navAllClicked=true`; screenshots `00-home.png` through `04-settings.png`
were captured. Cleanup closed the browser tab, removed the local tunnel, and
left no Windows listener on `8501`. A diagnostic v460 evidence-bundle smoke
then created
`C:\Users\<operator>\EIDP-v460-01e4427\logs\stage6-evidence-20260516-082906.zip`,
but packaged verification correctly returned `ok=false` with
`missing_required_labels=["last_run"]`; the Mac copies are
`logs/win-v460-stage6/stage6-evidence-20260516-082906.zip` and
`logs/win-v460-stage6/stage6-evidence-verify-20260516-172916.json`, with SHA256
`35b2042dbd50c1fd5156975876d5c35eca97c80ad1f42ab327852eef4c621f29` and
`d774b02dd31e0b71d0531f0577b9f452a1f4ca9a85bff8cad8b3fd36230a19a9`. The
post-v460 disk cleanup retained v460 current plus v459 fallback as the active
operator/fallback lane and pruned stale v454 package/deploy artifacts. A fresh
read-only v460 Windows disk-health check later reported `ok=true`,
`warn_count=0`, and `block_count=0`; the Mac copy is
`logs/win-v460-stage6/disk-health-20260517-operator-win.json` with SHA256
`4d5f4566db7cc5d3effcf8eeb63fb8ab566e64874b9e224564c05de113e700c9`. Mac-side
disk health also remained non-blocking;
later v462/v463/v464 side-by-side proof directories are not the owner-cycle lane.

Plan A CLI weekly was then run from
`C:\Users\<operator>\EIDP-v460-01e4427\scripts\weekly_run.bat` after confirming the
stale `data\.lock` marker was not held. A timestamped SQLite backup was created
first under `data\backups\plan-a\`. The weekly runner exited `0` and wrote
`data\output\last_run.json` with `status=success`, `dry_run=false`,
`current_fy=2026`, `no_crawlable_url_school_count=2418`,
`target_missing_school_count=0`, `target_pdf_auto_yield_pct=null`,
`operator_reviewable_yield_pct=null`, and `ship_gate_status=not_measured`.
`EIDP-stage6-evidence.bat` then created
`C:\Users\<operator>\EIDP-v460-01e4427\logs\stage6-evidence-20260516-094432.zip`,
and `EIDP-stage6-verify-evidence.bat` returned `ok=true`,
`missing_required_labels=[]`, with labels `build_info`, `diagnostics`,
`last_run`, `stage6_recovery`, and `weekly_run_logs`. The Mac copies under
`logs/win-v460-plan-a/` have SHA256 values: diagnostics
`040ecc9ced681c7d257f88312506b38cd0a38b130f3e51e83d7d6b2002770e46`,
`last_run.json` `91ceb1fb4869d7592d19ef3effba4b09521de81b194772ec2ea1a546f5df4b31`,
evidence ZIP `491129595c97191069708ec47386663d62321fb5ead35a827e6acbfd6aaf7e0e`,
and verifier JSON `ba295b1abaaa25eb1590f6531f734ef47600152c9ae8723d1ad6b7635fcdb0c5`.
Do not treat this Plan A evidence as release approval: it proves the CLI/evidence
chain, but the current-FY yield and workload gates still fail and the
owner/operator browser sign-off remains missing.

After that, a URL bootstrap was run on v460 to make the FY2026 probe meaningful:
the pre-bootstrap backup is
`C:\Users\<operator>\EIDP-v460-01e4427\data\backups\plan-a\eidp-before-url-bootstrap-20260516-184839.sqlite3`,
and `logs\bootstrap-pdfs-20260516-184850.log` recorded seed URL import
`imported=48`, corporation fallback `corporation_urls_inferred=296`, and
`search_found=180`. The resulting DB had `school_site_count=1838`,
`schools_with_url=1805`, `schools_with_verified_url=1312`, `Document=0`, and
`CrawlJob=0`. A second FY2026 `scripts\weekly_run.bat` then started at
`2026-05-16 19:24:43` JST, selected `1625` sites, and was stopped at
`2026-05-17 05:06` JST after about 9h41m. It did not write a new
`data\output\last_run.json` or summary; the existing `last_run.json` remains
the first Plan A success from `20260516_094344`. The incomplete probe generated
`data\output\target-year-discovery\20260516_102444-discovery-rejections.jsonl`
with `234238` lines / `101997049` bytes, mostly strict rejections and cached
non-target rows. The log showed repeated shared-domain crawls, including
O-Hara `robots.txt=152`, O-Hara `sitemap.xml=52`, O-Hara `about/joho/=283`,
Sanko `robots.txt=136`, and Jikei `post-sitemap2/3=16/16`. Treat this as a
v1.1 performance finding for run-scope corporation-domain/sitemap caching or
de-duplication, not as v1.0 release evidence or KPI failure. FY2026/R8 live
yield remains record-only during the May publication-lag window; the v1.0
algorithm evidence should remain separated from this production probe.

Follow-up on 2026-05-17: do not treat the remaining state as a pure
`HOLD waiting owner`. The v460 URL-rich weekly path can fail before owner
sign-off by never producing a fresh `last_run.json`. Use
`docs/runbooks/eidp-v466-active-promotion.md` as the explicit approval boundary
for moving the Windows Scheduled Task to v466. Source verifier support now has
an explicit `publication_lag` release-exception path for measured FY2026/R8 KPI
misses; it requires mature-year target-PDF/operator-reviewable acquisition
proof JSON and still rejects null KPI values and `ship_gate_status=not_measured`.
The mature-year proof path now also requires production-scale denominator
evidence: `target_pdf_auto_denominator_count >= 1000` and
`target_pdf_auto_denominator_scope=target_missing_schools_before_run`.
The current source tree also passed a mature-year retroactive Excel matrix,
recorded in `docs/reports/2026-05-17-current-source-retroactive-matrix.md`:
FY2025/FY2024/FY2023 returned `ok=true`, with every business-value diff
reporting `missing_rows=0`, `extra_rows=0`, and `differing_fields=0`. This is
current source Excel business-value evidence, not mature-year target-PDF
acquisition proof and not fresh v465 package evidence; v465 package freshness
still requires a clean matching source snapshot or a rebuild.
After the proof-basis tightening, the same Excel matrix JSON was exercised
through `verify_stage6_return.py` with `--release-exception-reason
publication_lag` and correctly returned `rc=1`: its basis is
`current_source_retroactive_excel_business_value_diff`, and its cases do not
carry mature-year `target_pdf_auto_yield_pct`, `operator_reviewable_yield_pct`,
or consistent `ship_gate_status` metrics. The exception path therefore cannot
approve either unmeasured owner evidence or an Excel-only mature-year proof.
`scripts/build_mature_year_acquisition_proof.py` now provides the matching proof
builder for real mature-year weekly `last_run.json` files. The current
mature-year proof audit is recorded in
`docs/reports/2026-05-17-mature-year-acquisition-proof-audit.md`: existing
FY2025 bounded artifacts were rejected because denominator was only `5` and
strict target auto yield topped out at `40.0%`; a copied URL-rich DB dry-run
found `target_missing_school_count=1625` but was not proof; a current-source
FY2025 `--limit 20` execution smoke completed with `crawled=20`, `downloaded=7`,
`processed=7`, `target_pdf_auto_yield_pct=25.0`, and
`operator_reviewable_yield_pct=65.0`, and was correctly rejected as release
proof.
After the source-side contract update, `uv run python
scripts/verify_windows_distribution.py dist/eidp-windows-v465.zip` exits `1`:
the ZIP hash and `BUILD_INFO.json` are valid, but the package lacks
the current bug-report bundle files, `release_exception_reason`,
`SHIP_GATE_EXCEPTION_REASONS`, `MATURE_YEAR_SHIP_GATE_METRIC_BASIS`,
`publication_lag`, weekly progress tokens, target-FY override tokens, and the
new packaged-doc local-user path guards. v465 remains useful as a
cache/performance-fix candidate, but it is no longer sufficient as the
current-contract release package without a rebuilt successor.
Current-source validation after the verifier/contract, packaging-guard,
bootstrap fiscal-year override, local bug-report bundle, weekly progress, and
CI pip fix:
the exact CI coverage command
`uv run pytest --cov=src/eidp --cov-report=term --cov-fail-under=80` returned
`1750 passed, 5 warnings` with total coverage `80.87%`. Focused follow-up
checks covering direct `ingest-pdfs --target-fiscal-year`, the distribution
verifier, CI/workflow, packaging, and bootstrap slices returned `117 passed`
and `121 passed`; the bug-report/UI/distribution slice returned `137 passed`;
the focused portability/runbook contract file returned `2 passed`; the
CI/portability/distribution verifier slice returned `133 passed`; the refreshed bug-signal API slice
returned `25 passed`; the weekly progress slice returned `83 passed`; ruff and
mypy passed for the touched CLI/verifier, bug-signal, weekly progress UI, and
portability files. `tests/unit/test_bug_signals.py` covered
local-only P0 detection, the P1 `weekly_run_timeout_no_last_run` detector,
`scan_bug_signals` plus the `scan_p0_bug_signals` compatibility wrapper, PII
and secret-assignment scrubbing, bundle generation, SQLite integrity checking,
and ZIP manifest validity. `scripts/run_weekly_target_year_discovery.py` now supports
`--progress-file` and `--progress-log-path`, and the school-year task UI writes
and renders `logs/weekly-rediscovery-*.json` for manual weekly rediscovery.
The shared-origin PDF discovery cache also has a production-shape stress
regression: `150` school paths on one corporation origin keep shared
`robots.txt`, `sitemap.xml`, and disclosure-page GETs to one request each;
the focused stale-rejection/cache slice returned `4 passed`. For large
same-origin groups, path-derived fallback probes are now capped per origin:
the first `3` school sites keep those probes, and later same-origin school
sites skip them. The `150`-school regression asserts
`shared_origin_derived_fallback_skipped=147`, while still allowing each school
home page to be fetched.
`uv sync --locked --extra dev --extra scraper-basic --extra pdf` now installs
`pip==26.1.1`, so the CI Windows ZIP path can satisfy
`python -m pip download`; `tests/unit/test_ci_workflow_contract.py` now asserts
that the `dev` extra retains a `pip` dependency while CI installs
`--extra dev`. The CI workflow also uses `actions/checkout@v6` and
`actions/setup-python@v6` to avoid the GitHub Actions Node 20 deprecation
warning observed on the latest remote failure run; the workflow contract test
returned `7 passed`, and Ruby YAML parsing returned `workflow yaml ok`.
The exact CI Ruff allowlist command, high-severity Bandit scan, mypy command,
and repository-facing Gitleaks scan also passed locally after the current-source
refresh, including the package-verifier local-user guard, bug-signal API naming
update, and bug-report secret-assignment scrub. The CI
allowlist now covers the release-critical `bootstrap_pdf_pipeline.py`,
`build_mature_year_acquisition_proof.py`, `collect_bug_report.py`,
`verify_stage6_return.py`, and
`ship_gate_contract.py` scripts plus `tests/unit/test_portability_contract.py`,
and `tests/unit/test_ci_workflow_contract.py` enforces that coverage. The
focused proof/verifier/ship-gate/CI contract slice returned `25 passed`, and the
full Windows packaging and distribution verifier refresh returned `86 passed`
and `124 passed`.
Public-source username portability was also tightened: local scans now return
no matches for the current developer/tester usernames in `tests`, `scripts`,
`src`, `.github`, `pyproject.toml`, and the two operator docs packaged into the
Windows ZIP after research-only scripts were changed to repo-relative paths or
`Path.home()`. The guard no longer hardcodes those usernames in public source;
`tests/unit/test_portability_contract.py` derives local usernames from the
current machine and optional `EIDP_FORBIDDEN_LOCAL_USERS`. The CI Ruff allowlist
plus `tests/unit/test_ci_workflow_contract.py` require that test file to remain
covered. `scripts/verify_windows_distribution.py` also rejects real
`C:\Users\<name>` and `/Users/<name>` path forms inside the packaged runbook and
E2E template while allowing documented placeholders such as `C:\Users\<user>`.
The latest focused refresh of the full distribution verifier returned
`124 passed`; the focused historical-runbook / `eidp_operator` / local-user
path slice returned `3 passed`; ruff and mypy also passed for the touched
verifier and portability files.
`uv run python -m py_compile` passed for those scripts, and the Windows path
scanner still returned `OK: all paths are Windows-safe` with
`checked_paths=494`.
Diagnostic successor packaging was also tested and recorded in
`docs/reports/2026-05-17-v466-diagnostic-package.md`: `dist/eidp-windows-v466-
diagnostic.zip` was built with `--allow-dirty` and without `--skip-download`,
so it exercised the same wheel-download path as CI. The build output showed
`.venv/bin/python3 -m pip download`, produced `84` accepted wheels, and wrote
SHA256 `6cfc475c9723c4712fd513c09ab615edbd7b1bb68ef357e6f0c44743c2820126`.
`verify_windows_distribution.py` reported only one blocker:
`BUILD_INFO.json git_dirty must be false`. This proves the current source
packages with the new contract tokens, including bootstrap
`--target-fiscal-year` propagation, direct `ingest-pdfs --target-fiscal-year`,
and local bug-report bundle files, but it is diagnostic only and must be rebuilt
from a clean source snapshot before release or owner transfer. A release-like dirty output name such as
`dist/eidp-windows-v466.zip` is now rejected up front; dirty ZIP builds must
include `diagnostic` or `dirty` in the filename.
A separate clean CI simulation copied the current working tree to `/tmp`,
created a temporary git commit, and ran the GitHub package path exactly enough
to exercise clean `BUILD_INFO`: `uv sync --locked --extra dev --extra
scraper-basic --extra pdf`, `download_windows_runtime.py`,
`build_windows_zip.py --out-zip dist/eidp-windows-ci.zip`,
`verify_windows_distribution.py`, and `run_non_windows_release_gates.py
--skip-full-unit`. That simulation produced clean package SHA256
`cdcd9832e64d182b06287fa9ef42af43b99eb63b6574734759833d7d61521cf0` from
temporary commit `54df409531d758adeef47d3edb6eb1cabbafaa21`, with
`git_dirty=false`, `wheel_count=84`, `entry_count=3096`, and release-gate
`ok=true`. It is not a release artifact because the commit exists only in the
temporary checkout, but it proves the pip fix and current contract additions
are sufficient for the next clean CI package path once committed and pushed.

v459 remains the latest evidence-bundle-proven, default-launcher-proven,
R7-browser-Excel-proven, bounded-weekly-proven, and UI-write-sandbox-proven
support package. Its
operator docs bundle and support evidence remain useful for checklist shaping,
but v459 is no longer the current Windows execution pointer after the v460
staging update. For v459, the root-level packaged `EIDP-start.bat` started
Streamlit on Windows `127.0.0.1:8501`, returned `_stcore/health=200` and root
HTTP `200`, and cleanup left no remaining `8501` listener. A follow-up
read-only browser navigation smoke kept Streamlit alive in a foreground SSH
session, used an SSH tunnel on Mac `127.0.0.1:18503`, clicked
`① 学校別タスク`, `② PDF確認・手入力`, `④ Excel プレビュー`, and
`⑤ 設定（年度・OCR・API）`, and wrote
`output/playwright/v459-ui-smoke/summary.json` with `hasJapaneseUi=true`,
`hasTargetFiscalYear=true`, `hasErrorTraceback=false`, and
`navAllClicked=true`; screenshots `00-home.png` through `04-settings.png` were
captured, the temporary local Playwright dependency was deleted, all tunnels
were closed, and Windows cleanup confirmed no remaining `8501` listener.
Another process-scoped FY2025/R7 browser Excel smoke then launched the same
v459 package with `EIDP_TARGET_FISCAL_YEAR=2025`, opened `④ Excel プレビュー`,
observed `2025年度（令和7年度）`, `Excel出力可 2`, and `Excel対象行 7177`,
clicked `プレビュー workbook を生成`, clicked `Excel ダウンロード`, and saved
`output/playwright/v459-r7-excel-smoke/eidp_master.xlsx`. The downloaded
workbook was `3,677,040` bytes, and local `openpyxl` verified sheets
`採録状況`, `対象比率`, `学科別`, and `在籍のみ抜粋` with dimensions `2419x10`,
`10025x22`, `9748x83`, and `9748x19`. Windows checks confirmed both checked
v459 `.env` locations were absent after the process-scoped run. Cleanup removed
the temporary local Playwright dependency, closed the tunnel, killed the
Windows Streamlit process, and confirmed no remaining local `18504` or Windows
`8501` listener.
A disposable v459 UI write/audit sandbox then copied the v459 SQLite DB under
`C:\Users\<operator>\EIDP-v459-50152a5\_temp\v459-ui-write-sandbox`, seeded
`review_item#37` for
`https://stage6-v459-ui-write-sandbox.example.invalid/`, launched the v459 UI
with `EIDP_APP_ROOT` pointed at that sandbox, rejected the candidate in
`URL候補レビュー` with reason `v459 UI reject smoke`, opened `監査ログ`, and
clicked `Outbox を flush`. Browser evidence under
`output/playwright/v459-ui-write-sandbox/` recorded the candidate before reject,
the empty URL-candidate queue after reject, `JSONL outbox 未送信 2` before
flush, and `exported=2 already_present=0 failed=0` after flush. The pulled
verifier JSON
`logs/win-v459-stage6/v459-ui-write-sandbox-result-final.json` returned
`ok=true`, `pending_outbox=0`, `jsonl_line_count=2`,
`jsonl_action_types=["stage6_v459_ui_audit_flush_smoke",
"url_candidate_rejected"]`, matching JSONL/DB action IDs, no `SchoolSite` for
the rejected URL, and real v459 runtime DB marker counts all `0`. Cleanup
removed the remote sandbox, killed Windows `8501`, closed the local `18505`
tunnel, and deleted the temporary local Playwright dependency.

The v459 URL-only bootstrap completed with all 47 prefecture seed artifacts
downloaded/aggregated, Step 2b seed URL import `imported=48`,
`school_domain_override` inferred `6`, and corporation fallback inferred `296`.
The subsequent bounded R7 weekly smoke ran with `EIDP_TARGET_FISCAL_YEAR=2025`,
`EIDP_WEEKLY_LIMIT=5`, `EIDP_WEEKLY_BATCH_SIZE=5`,
`EIDP_WEEKLY_RATE_LIMIT=0.5`, and `EIDP_WEEKLY_REQUEST_TIMEOUT=8`, exiting `0`
with `run_id=20260516_060230`, `crawled=5`, `found=5`, `downloaded=2`,
`new_document_ids=[1, 2]`, `operator_reviewable_count=5`,
`target_pdf_auto_yield_pct=40.0`, `operator_reviewable_yield_pct=100.0`, and
`ship_gate_status=pass`. `scripts\validate_install.bat --after-setup
--after-weekly --json` returned `ok=true`, `last_run_status=success`,
`sqlite_target_fy=2025`, `sqlite_target_fy_target_pdf_school_count=2`, and
`sqlite_target_fy_operator_reviewable_school_count=5`. Root
`EIDP-diagnose.bat` later exited `0` and wrote
`C:\Users\<operator>\EIDP-v459-50152a5\logs\diagnostics-20260516-160111.txt`.
The refreshed v459 evidence bundle
`C:\Users\<operator>\EIDP-v459-50152a5\logs\stage6-evidence-20260516-070115.zip`
verified with `ok=true`, `entry_count=12`, and `missing_required_labels=[]`.
The bundle, verifier JSON, and latest diagnostics were copied back to Mac under
`logs/win-v459-stage6/`; local `scripts/verify_stage6_evidence.py` returned
`ok=true` for the copied ZIP, whose SHA256 is
`c4e68ee5b5f8c1cb8b74938fb369edf4c53c00efdd5624bac3c05e51ab7caf28`.
Windows `Get-FileHash` returned the same SHA256 values for the remote ZIP,
verifier JSON, and diagnostics file as the Mac copies.
Mac cleanup retained v459 current plus v454 fallback and, after pulling the
latest evidence copy, reported `warn=0 block=0`, project `1.7GiB`,
`dist=738.8MiB`, `_temp=0B`, `logs=4.3MiB`, protected `data=20.0MiB`, and
`.claude/worktrees=0B`. Windows cleanup retained only
`EIDP-v459-50152a5` current plus `EIDP-v454-48a346b` fallback; packaged disk
health reported `warn_count=0`, `block_count=0`, `app_root_total=853.7MiB`,
`data\pdfs=1.7MiB`, `data\output=40.0KiB`, and `logs=244.0KiB`.

v458 is retained only as an intermediate superseded proof. It passed setup,
recovery, UI health, default launcher, and disk health, but its cleanup dry-run
exposed that `rotate_audit_outbox.py` and `prune_pdf_storage.py` were not in the
Windows ZIP. v459 fixes that packaging gap and supersedes v458 for Stage 6
handoff.

v456 remains historical browser-readonly-navigation-proven,
R7-browser-Excel-proven, and UI-write-sandbox-proven support, but the current
v459 lane now supersedes v456 for read-only navigation, R7 browser Excel
generation/download, and the URL-candidate reject / audit-outbox flush sandbox.
v456 was built
from package snapshot `f33ffc0e6fd801782f3e49fad3315adc64081f6f`, which keeps
the operator E2E template version-neutral so future ZIPs do not embed stale
package/SHA fields. The v456 strict non-Windows gate
`logs/release-gate-v456.json` returned `ok=true` with SHA256
`73b429bd21504b95b10cf7c45b5eda4e3bcd6bf9198cf8017f2740c89d0155d2`,
package/source commit match, `source_dirty=false`, `stale=false`, full unit
`1637 passed`, validator/distribution tests `166 passed`, validator mypy/Ruff
pass, discovery-gold expected predictions, and both package verifier modes
pass. Mac disk cleanup after v456 removed the failed v455 package/sidecar,
left retained packages v456/v454/v453, and
`scripts/disk_health_check.py --profile mac-dev` reported `warn=0 block=0` with `dist=940.2MiB`,
`_temp=0B`, protected `data=20.0MiB`, and `.claude/worktrees=0B`. Windows
transfer to `C:\EIDP-staging` matched the sidecar SHA, extraction to
`C:\Users\<operator>\EIDP-v456-f33ffc0` succeeded, and `EIDP-setup.bat` exited `0`
with `school_count=2418`, `school_fiscal_year_status_count=2418`,
`sqlite_integrity_check=ok`, and `wheel_count=78`. Independent packaged
`scripts\validate_install.bat --after-setup --json` returned `ok=true`.
Packaged disk health returned `warn_count=0`, `block_count=0`,
`app_root_total=843.0MiB`, `data\pdfs=0B`, `data\output=0B`, and `logs=3.8KiB`.
The UI health smoke started Streamlit on Windows `127.0.0.1:8501` and returned
`/_stcore/health=ok` plus root HTTP `200`, then cleanup left no listener on
`8501`. The root-level packaged `EIDP-start.bat` was also launched from
`C:\Users\<operator>\EIDP-v456-f33ffc0`; it invoked `scripts\launch.bat`, started
Streamlit on Windows `127.0.0.1:8501`, returned `_stcore/health=ok` and root
HTTP `200`, observed listener owner process `25704` before forced cleanup, and
cleanup then left no remaining `8501` listener. Recovery check with expected action
`C:\Users\<operator>\EIDP-v456-f33ffc0\scripts\weekly_run.bat` returned `ok=true`
and `action_matches_expected=true`. Windows home loose test ZIP cleanup removed
48 old `eidp-windows-v*.zip*` artifacts from `C:\Users\<operator>`, freeing about
`7.81GB`; the packaged pruner then removed v453 staging/deploy artifacts,
freeing another `1.11GB`. After v459 validation, the v456 deploy directory was
pruned and v459 current plus v454 fallback are the only retained Windows deploy
directories.
The URL-only bootstrap completed with all 47 prefecture seed artifacts
downloaded/aggregated, Step 2b seed URL import `imported=48`, and
`school_domain_override` loaded `count=6` / inferred `6`; the subsequent
bounded R7 weekly smoke ran with `EIDP_TARGET_FISCAL_YEAR=2025`,
`EIDP_WEEKLY_LIMIT=5`, `EIDP_WEEKLY_BATCH_SIZE=5`,
`EIDP_WEEKLY_RATE_LIMIT=0.5`, and `EIDP_WEEKLY_REQUEST_TIMEOUT=8`, exiting `0`
with `run_id=20260516_034531`, `crawled=5`, `found=5`, `downloaded=2`,
`new_document_ids=[1, 2]`, `operator_reviewable_count=5`,
`target_pdf_auto_yield_pct=40.0`, `operator_reviewable_yield_pct=100.0`, and
`ship_gate_status=pass`. `scripts\validate_install.bat --after-setup
--after-weekly --json` returned `ok=true`, `last_run_status=success`,
`sqlite_target_fy=2025`, `sqlite_target_fy_target_pdf_school_count=2`, and
`sqlite_target_fy_operator_reviewable_school_count=5`. A v456 evidence bundle
`logs\stage6-evidence-20260516-034752.zip` verified on Windows and Mac as
`logs/win-v456-stage6/stage6-evidence-20260516-034752.zip` with `ok=true`,
`entry_count=12`, `manifest_missing_patterns=[]`, and present labels
`bootstrap_logs`, `bootstrap_progress`, `build_info`, `diagnostics`,
`discovery_evidence`, `discovery_rca`, `last_run`, `stage6_recovery`,
`stage6_residual_cleanup`, and `weekly_run_logs`. The URL-only bootstrap
`--after-bootstrap` validator currently fails because `--skip-discover` progress
does not emit ship-gate metric keys; the weekly validator is the authoritative
bounded acquisition check for this v456 lane. A browser-level read-only
navigation smoke then ran the v456 package through `scripts\launch.bat`, opened
the Mac tunnel `127.0.0.1:18501 -> Windows 127.0.0.1:8501`, and rendered the
real Streamlit UI through Playwright. The browser title was
`EIDP Operator Console`; `output/playwright/v456-ui-smoke/browser-summary.json`
recorded `quick`, `schoolTasks`, `pdfManual`, `excelPreview`, `settings`,
`build`, and `targetFy` all `true`. Snapshots and screenshots under
`output/playwright/v456-ui-smoke/` cover `① 学校別タスク`,
`② PDF確認・手入力`, `④ Excel プレビュー`, and
`⑤ 設定（年度・OCR・API）`. Only sidebar navigation buttons were clicked; no
weekly re-fetch, workbook generation, settings save, or write action was
invoked. Cleanup closed the browser tab, stopped the local tunnel, killed the
Windows Streamlit process, and confirmed no remaining local `18501` or Windows
`8501` listener. A separate process-scoped FY2025/R7 browser Excel smoke then
launched v456 with `EIDP_TARGET_FISCAL_YEAR=2025` without writing `.env`,
rendered `④ Excel プレビュー` with `対象年度: 2025年度（令和7年度）`,
`Excel出力可 2`, and `Excel対象行 7177`, clicked
`プレビュー workbook を生成`, observed sheet row counts `採録状況=2418`,
`対象比率=10024`, `学科別=9746`, and `在籍のみ抜粋=9746`, then downloaded
`eidp_master.xlsx` to `output/playwright/v456-r7-excel-smoke/eidp-master.xlsx`.
Local `openpyxl` opened the workbook at `3,677,041` bytes with sheets
`採録状況`, `対象比率`, `学科別`, and `在籍のみ抜粋`, and dimensions `2419x10`,
`10025x22`, `9748x83`, and `9748x19`. Windows checks confirmed both checked
v456 `.env` paths were absent after the process-scoped run; cleanup closed the
browser tab, stopped the local tunnel, killed the Windows Streamlit process,
and confirmed no remaining local `18501` or Windows `8501` listener.

The v456 disposable UI write/audit sandbox then launched the same package
against a copied SQLite DB under `_temp\v456-ui-write-sandbox`, rejected seeded
`review_item#37` for `https://stage6-v456-ui-write-sandbox.example.invalid/`
with reason `v456 UI reject smoke`, opened `監査ログ`, and clicked
`Outbox を flush`. The browser reported
`exported=2 already_present=0 failed=0`. The pulled verifier JSON
`logs/win-v456-stage6/v456-ui-write-sandbox-result-final.json` returned
`ok=true`, with `pending_outbox=0`, exported
`stage6_v456_ui_audit_flush_smoke` and `url_candidate_rejected` rows, no
`SchoolSite` row for the rejected URL, matching JSONL action IDs, and real
v456 runtime DB marker counts all `0`. Screenshot/snapshot evidence is under
`output/playwright/v456-ui-write-sandbox/`; cleanup stopped Windows `8501`,
closed local `18501`, and removed the remote disposable sandbox.

After those browser smokes, packaged `scripts\diagnose.bat` wrote
`logs/win-v456-stage6/diagnostics-20260516-134458.txt`. The diagnostic preflight
returned `validate_core_rc=0`, `validate_after_setup_rc=0`,
`stage6_recovery_rc=0`, `validate_after_weekly_rc=0`,
`validate_after_weekly_ship_gate_rc=0`, and `retroactive_ship_readiness_rc=0`
for `retroactive_fiscal_year=2025`. It also reported `ship_readiness_rc=1`,
which keeps FY2026/current-year real-cycle completion explicitly open.
The short execution card `docs/runbooks/eidp-v456-real-cycle-card.md` now pins
the v456 package SHA, Windows root, red-line files, preflight commands,
real-cycle UI path, evidence-bundle commands, and owner/operator sign-off gates
for the next Stage 6 run. The docs-only package gate
`logs/release-gate-v456-docs-current-after-real-cycle-card.json` returned
`ok=true` after adding this card, using `--allow-docs-only-stale-package`
against the unchanged v456 ZIP.

v454 remains a retained fallback and historical Windows disposable UI
write/audit sandbox proof. It was built from package
snapshot `48a346bb626be749adb72d1aeb6a684903f22049`, which keeps target
application PDFs viable for RCA/operator review even when a negative path token
such as `syllabus` lowers their discovery score. The v454 strict non-Windows
gate `logs/release-gate-v454.json` returned `ok=true` with SHA256
`0bbed01d95fe320cee70b826c63e8c500303b8a62c42d325ef2481764660b2e3`,
package/source commit match, `source_dirty=false`, `stale=false`, full unit
`1635 passed`, validator/distribution tests `164 passed`, validator mypy/Ruff
pass, discovery-gold expected predictions `44/44`, and both package verifier
modes pass. Windows transfer SHA matched, the package was expanded to
`C:\Users\<operator>\EIDP-v454-48a346b`, and `EIDP-setup.bat` completed with
`school_count=2418`, `school_fiscal_year_status_count=2418`,
`sqlite_integrity_check=ok`, and `wheel_count=78`. The independent packaged
`scripts\validate_install.bat --after-setup --after-weekly --json` check later
returned `ok=true`, `errors=[]`, `warnings=[]`, `sqlite_integrity_check=ok`,
`last_run_status=success`, `sqlite_target_fy=2025`,
`sqlite_target_fy_target_pdf_school_count=2`, and
`sqlite_target_fy_operator_reviewable_school_count=5`; the captured JSON is
`logs/win-v454-stage6/v454-validate-install-after-weekly.json`. URL-only bootstrap completed
after downloading and aggregating all 47 prefecture seed artifacts; Step 2b
loaded `school_domain_overrides.csv` with `count=6` and reported
`school_override_inferred=6`. The real `scripts\weekly_run.bat` launcher then
ran with `EIDP_TARGET_FISCAL_YEAR=2025`, `EIDP_WEEKLY_LIMIT=5`,
`EIDP_WEEKLY_BATCH_SIZE=5`, `EIDP_WEEKLY_RATE_LIMIT=0.5`, and
`EIDP_WEEKLY_REQUEST_TIMEOUT=8`; it exited `0` with
`run_id=20260516_020806`, methods including `school_domain_override`,
`crawled=5`, `found=5`, `downloaded=2`, `new_document_ids=[1, 2]`,
`operator_reviewable_count=5`, `target_pdf_auto_yield_pct=40.0`,
`operator_reviewable_yield_pct=100.0`, and `ship_gate_status=pass`. The two
ingested FY2025 target PDFs were Osaka Mode and Japanese Institute Hokkaido.
The v454 RCA queue also shows both NEEC target application PDFs as
`target_form_without_year_evidence` instead of hiding them under
`non_target_candidates_only`; they remain review-only because the PDFs lack
strict FY2025 evidence. Tokyo Mode remains a yearless embedded target-form PDF.
Recovery check with explicit expected action
`C:\Users\<operator>\EIDP-v454-48a346b\scripts\weekly_run.bat` returned `ok=true`,
`action_matches_expected=true`, and `recommendations=[]`; the pulled JSON is
`logs/win-v454-stage6/stage6-recovery-20260516-113412-expected-action.json`.
Residual cleanup dry-run returned `ok=true`. After the later validator,
expected-action recovery, default launcher, browser navigation, and R7 Excel
browser proof, the refreshed evidence bundle
`logs\stage6-evidence-20260516-023620.zip` verified on both
Windows and Mac as
`logs/win-v454-stage6/stage6-evidence-20260516-023620.zip` with `ok=true`,
`entry_count=13`, no forbidden or unsafe entries, `manifest_missing_patterns=[]`, and present labels
`bootstrap_logs`, `bootstrap_progress`, `build_info`, `diagnostics`,
`discovery_evidence`, `discovery_rca`, `last_run`, `stage6_recovery`,
`stage6_residual_cleanup`, and `weekly_run_logs`. v454 direct Streamlit UI
smoke served `http://127.0.0.1:8501/` with HTTP `200`, and cleanup left no
listener on `8501`. A browser-level read-only navigation smoke then kept v454
running in a foreground SSH session, opened `127.0.0.1:18501 -> Windows
127.0.0.1:8501`, and rendered the real Streamlit UI through Playwright. The
page title became `EIDP Operator Console`, with build `48a346b` and target
display `2026年度（令和8年度）`. Snapshots were captured for `① 学校別タスク`,
`② PDF確認・手入力`, `④ Excel プレビュー`, and
`⑤ 設定（年度・OCR・API）` under `output/playwright/v454-ui-smoke/`. Only
navigation buttons were clicked; no weekly re-fetch, workbook generation,
settings save, or other write action was invoked. Cleanup stopped the Windows
Streamlit process and closed the local tunnel; both Windows `8501` and local
`18501` had no remaining listener. A separate v454 disposable UI write/audit
sandbox then launched the same package against a copied SQLite DB under
`_temp\v454-ui-write-sandbox`, rejected one seeded `URL候補レビュー` item with
reason `v454 UI reject smoke`, opened `監査ログ`, and clicked
`Outbox を flush`. The browser reported `exported=2 already_present=0 failed=0`.
The pulled verifier JSON
`logs/win-v454-stage6/v454-ui-write-sandbox-result-final.json` returned
`ok=true`, with `pending_outbox=0`, exported
`stage6_v454_ui_audit_flush_smoke` and `url_candidate_rejected` rows, no
`SchoolSite` row for the rejected URL, and real v454 runtime DB marker counts
all `0`. Screenshot/snapshot evidence is under
`output/playwright/v454-ui-write-sandbox/`; cleanup stopped Windows `8501`,
closed local `18501`, and removed the remote disposable sandbox. A separate
process-scoped FY2025/R7 browser
Excel smoke launched the same v454 package with `EIDP_TARGET_FISCAL_YEAR=2025`
without writing `.env`, rendered `④ Excel プレビュー` with
`対象年度: 2025年度（令和7年度）`, `Excel出力可 2`, `Excel対象行 7177`,
and generated an in-memory workbook with sheet row counts
`採録状況=2418`, `対象比率=10024`, `学科別=9746`, and
`在籍のみ抜粋=9746`. Playwright downloaded `eidp_master.xlsx` to
`output/playwright/v454-r7-excel-smoke/eidp-master.xlsx`; local `openpyxl`
opened the workbook at `3,677,039` bytes with sheets `採録状況`, `対象比率`,
`学科別`, and `在籍のみ抜粋`, and dimensions `2419x10`, `10025x22`,
`9748x83`, and `9748x19`. Windows checks confirmed both checked `.env` paths
were absent after the process-scoped run. This proves the current v454 browser
Excel path, while v442 remains historical support for the fuller R7 parity
workbook. The root-level packaged `EIDP-start.bat` was also launched from
`C:\Users\<operator>\EIDP-v454-48a346b`; it invoked `scripts\launch.bat`, started
Streamlit on Windows `127.0.0.1:8501`, returned `_stcore/health=ok` and root
HTTP `200` locally, and the default Mac tunnel `127.0.0.1:18501 -> Windows
127.0.0.1:8501` returned `_stcore/health=ok` plus root HTTP `200`. The test
then force-stopped the v454 Streamlit process for cleanup, so the wrapper
printed its non-zero stop message; both Windows `8501` and local `18501` had no
remaining listener afterward. Mac cleanup left `dist=754M`, `_temp=0B`, `logs=4.5M`, and protected
`data=20M`; Windows cleanup preserved v454 current
plus v453 fallback in both staging and deploy directories. v454 is still not a completed operator
real-cycle Stage 6 sign-off, and its bounded `40.0%` strict auto-yield is not
the final production 60-70% R8 gate.

v453 is the previous Windows setup/bootstrap/bounded-weekly/UI-health evidence
lane. It proved definition-list fiscal-year inheritance for NKHS and local
cleanup of RCA HTML/XML artifacts, with the same bounded `40.0%` strict
auto-yield, but it kept the NEEC negative-path target application PDFs out of
the target-year RCA bucket. See
`docs/reports/eidp-v453-stage6-evidence-draft.md`.

v452 is the previous Windows setup/bootstrap/bounded-weekly/UI-health evidence
lane. It proved exact NKZ disclosure overrides and moved the bounded canary from
v450's `0.0%` to `20.0%` strict auto-yield, but remained below the final
production gate. See `docs/reports/eidp-v452-stage6-evidence-draft.md`.

v450 is the previous Windows setup/bootstrap/bounded-weekly/UI-health evidence
lane. It proved that `school_domain_override` entered the weekly runner but
remained below gate with `downloaded=0`, `target_pdf_auto_yield_pct=0.0`, and
`ship_gate_status=below_gate`. See
`docs/reports/eidp-v450-stage6-evidence-draft.md`.

v448 is the previous Mac/non-Windows release-gate-clean, Windows transfer-proven,
setup-proven, bounded-bootstrap-proven, bounded-weekly-proven,
evidence-bundle-proven, UI-health-proven, disk-health-proven, and
release-artifact-pruner-proven package. It was built from package snapshot
`639dbbbac5b1b957bb30e419d84f909b683aedec`, which adds the read-only
`scripts/disk_health_check.py` helper and requires it in the Windows ZIP
manifest. The v448 strict non-Windows gate `logs/release-gate-v448.json`
returned `ok=true` with SHA256
`5306b983debe3aee743869d64ded5557eacb4ab70042e5e6862cdbf3a5a9a09e`,
package/source commit match, `source_dirty=false`, `stale=false`,
validator/distribution tests `164 passed`, validator mypy/Ruff pass,
discovery-gold expected predictions `44/44`, and both package verifier modes
pass. Windows transfer SHA matched, the package was expanded to
`C:\Users\<operator>\EIDP-v448-639dbbb`, and `EIDP-setup.bat` completed with
`school_count=2418`, `school_fiscal_year_status_count=2418`, and
`sqlite_integrity_check=ok`; the independent
`scripts\validate_install.bat --after-setup --json` check also returned
`ok=true`. The packaged disk-health helper returned `ok=true` after setup with
`app_root_total=843.0MiB`, `data\pdfs=0B`, `data\output=0B`, and
`logs=3.8KiB`. The v448 packaged pruner deleted only v447 staging/deploy
artifacts, freeing `1104022134` bytes while preserving v448 current plus v442
fallback. URL-only bootstrap completed after downloading and aggregating all 47
prefecture seed artifacts. The real `scripts\weekly_run.bat` launcher then ran
with trusted bounded variables `EIDP_WEEKLY_LIMIT=5`,
`EIDP_WEEKLY_BATCH_SIZE=5`, `EIDP_WEEKLY_RATE_LIMIT=0.5`, and
`EIDP_WEEKLY_REQUEST_TIMEOUT=8`; it exited `0` with `run_id=20260516_001421`,
`crawled=5`, `found=3`, `downloaded=0`, `operator_reviewable_count=1`,
`target_pdf_auto_acquired_count=0`, `target_pdf_auto_yield_pct=0.0`, and
`ship_gate_status=below_gate`. `scripts\validate_install.bat --after-setup
--after-weekly --json` returned `ok=true`, reporting `last_run_status=success`,
`sqlite_target_fy_target_pdf_school_count=0`, and
`sqlite_target_fy_operator_reviewable_school_count=1`. Recovery check and
residual cleanup dry-run both returned `ok=true`. The evidence bundle
`logs\stage6-evidence-20260516-001548.zip` verified on both Windows and Mac as
`logs/win-v448-stage6/stage6-evidence-20260516-001548.zip` with `ok=true`, no
forbidden or unsafe entries, `manifest_missing_patterns=[]`, and present labels
`bootstrap_logs`, `bootstrap_progress`, `build_info`, `diagnostics`,
`discovery_evidence`, `discovery_rca`, `last_run`, `stage6_recovery`,
`stage6_residual_cleanup`, and `weekly_run_logs`. v448 `scripts\launch.bat`
then served `/_stcore/health` and `/` with HTTP `200`, and cleanup left no
listener on `8501`; the pulled evidence is
`logs/win-v448-stage6/v448-ui-smoke-20260516-091650.json`. The final v448
disk-health check returned `ok=true` with `app_root_total=851.4MiB`,
`data\pdfs=0B`, `data\output=61.7KiB`, and `logs=123.0KiB`. Mac pruning then
deleted v446/v447 local ZIP sidecars and packages,
freeing `422489392` bytes; Mac disk health reports `project_total=1.7GiB`,
`dist=738.7MiB`, `_temp=0B`, `logs=3.4MiB`, and protected `data=20.0MiB`.
v448 is still not a completed operator real-cycle Stage 6 sign-off and still
fails the production yield gate.

v447 remains the latest bounded-bootstrap-proven, bounded-weekly-proven,
evidence-bundle-proven, and UI-health-proven package. It was built from package snapshot
`55cbc1b4007a8a0e2798cc8d79f5adbff1944391`, which adds an `os.fsync()` before
atomic text-output replacement and restores the reusable operator E2E template
to version-neutral form for future ZIPs. The v447 strict non-Windows gate
returned `ok=true` with SHA256
`cada1a77a2d52793939518c62a2433aee3fe959a21ad611a3fd37264c7a38557`,
package/source commit match, `source_dirty=false`, `stale=false`,
validator/distribution tests `164 passed`, validator mypy/Ruff pass,
discovery-gold expected predictions `44/44`, and both package verifier modes
pass. Windows transfer SHA matched, the package was expanded to
`C:\Users\<operator>\EIDP-v447-55cbc1b`, and `EIDP-setup.bat` completed with
`school_count=2418`, `school_fiscal_year_status_count=2418`, and
`sqlite_integrity_check=ok`. The packaged pruner deleted only v446 staging and
deploy artifacts, freeing `1104507037` bytes while preserving v447 current plus
v442 fallback. URL-only bootstrap completed after downloading and aggregating
all 47 prefecture seed artifacts. The real `scripts\weekly_run.bat` launcher
then ran with trusted bounded variables `EIDP_WEEKLY_LIMIT=5`,
`EIDP_WEEKLY_BATCH_SIZE=5`, `EIDP_WEEKLY_RATE_LIMIT=0.5`, and
`EIDP_WEEKLY_REQUEST_TIMEOUT=8`; it exited `0` with `run_id=20260515_234136`,
`crawled=5`, `found=3`, `downloaded=0`, `operator_reviewable_count=1`,
`target_pdf_auto_acquired_count=0`, `target_pdf_auto_yield_pct=0.0`, and
`ship_gate_status=below_gate`. The v447 bounded weekly wrote `last_run.json`,
the RCA batch plan, and the summary JSON through the fsync-hardened
`write_text_atomic` path. `scripts\validate_install.bat --after-setup
--after-weekly --json` returned `ok=true`, reporting `last_run_status=success`,
`sqlite_target_fy_target_pdf_school_count=0`, and
`sqlite_target_fy_operator_reviewable_school_count=1`. Recovery check and
residual cleanup dry-run both returned `ok=true`. The evidence bundle
`logs\stage6-evidence-20260515-234300.zip` verified on both Windows and Mac as
`logs/win-v447-stage6/stage6-evidence-20260515-234300.zip` with `ok=true`, no
forbidden or unsafe entries, `manifest_missing_patterns=[]`, and present labels
`bootstrap_logs`, `bootstrap_progress`, `build_info`, `diagnostics`,
`discovery_evidence`, `discovery_rca`, `last_run`, `stage6_recovery`,
`stage6_residual_cleanup`, and `weekly_run_logs`. v447 `scripts\launch.bat`
then served `/_stcore/health` and `/` with HTTP `200`, and cleanup left no
listener on `8501`; the pulled evidence is
`logs/win-v447-stage6/v447-ui-smoke-20260516-084930.json`.
v447 is still not a completed operator real-cycle Stage 6 sign-off and still
fails the production yield gate.

v446 is the previous Mac/non-Windows release-gate-clean, Windows transfer-proven,
and release-artifact-pruner-proven package. It was built from package snapshot
`e9f91ccbb51f82cb594be6567076df50276cc97a`, which adds
`scripts/prune_release_artifacts.py` and wires it into both the Windows ZIP
member collector and `scripts/verify_windows_distribution.py` core-required
manifest. The v446 non-Windows gate returned `ok=true` with SHA256
`e0436a08d12d09987f15f96c814de2290010714477e54ae0dcff0f290a3d3878`,
package/source commit match, `source_dirty=false`, validator/distribution tests
`164 passed`, validator mypy/Ruff pass, discovery-gold expected predictions
`44/44`, and both package verifier modes pass. Windows transfer SHA matched,
the package was expanded to `C:\Users\<operator>\EIDP-v446-e9f91cc`, and the
packaged pruner dry-run reported only three v445 candidates:
`C:\EIDP-staging\eidp-windows-v445.zip`, its `.sha256` sidecar, and
`EIDP-v445-19ceb0d`. Applying the same command deleted those three candidates
(`1103245161` bytes) and left Windows staging/deploy retention at v446 current
plus v442 fallback. At the v446 checkpoint, Mac retention kept v446 current,
v442 fallback, and the latest alias; `_temp=0B`, `.claude/worktrees=0B`,
`data=20M`, and `logs=3.6M`.
`EIDP-setup.bat` then completed on v446, imported bundled `master.xlsx`, rebuilt
FY2026 school-year tasks with `school_count=2418` and
`school_fiscal_year_status_count=2418`, and `scripts\validate_install.bat
--after-setup --json` returned `ok=true` with `sqlite_integrity_check=ok`.
Setup logs again confirmed the master-data prefecture reconciliation for
`日本工学院北海道専門学校` from `東京都` to `北海道`. URL-only bootstrap completed
with `--skip-discover --url-search off --school-url-crawl off`, downloading and
aggregating all 47 prefecture seed artifacts while avoiding a bulk PDF
discovery run. The real `scripts\weekly_run.bat` launcher then ran with trusted
bounded variables `EIDP_WEEKLY_LIMIT=5`, `EIDP_WEEKLY_BATCH_SIZE=5`,
`EIDP_WEEKLY_RATE_LIMIT=0.5`, and `EIDP_WEEKLY_REQUEST_TIMEOUT=8`; it exited
`0` with `run_id=20260515_225803`, `crawled=5`, `found=3`, `downloaded=0`,
`operator_reviewable_count=1`, `target_pdf_auto_acquired_count=0`,
`target_pdf_auto_yield_pct=0.0`, and `ship_gate_status=below_gate`.
`scripts\validate_install.bat --after-setup --after-weekly --json` returned
`ok=true`, reporting `last_run_status=success`,
`sqlite_target_fy_target_pdf_school_count=0`,
`sqlite_target_fy_operator_reviewable_school_count=1`, and
`sqlite_target_fy_yield_pct=0.0`. The v446 recovery checker was also run in its
wrapper-default action-check-skipped mode and returned `ok=true`; residual
cleanup dry-run returned `ok=true`, `existing_count=0`, and `moved_count=0`.
The evidence bundle `logs\stage6-evidence-20260515-225956.zip` verified on both
Windows and Mac as `logs/win-v446-stage6/stage6-evidence-20260515-225956.zip`
with `ok=true`, no forbidden or unsafe entries, `manifest_missing_patterns=[]`,
and present labels `bootstrap_logs`, `bootstrap_progress`, `build_info`,
`diagnostics`, `discovery_evidence`, `discovery_rca`, `last_run`,
`stage6_recovery`, `stage6_residual_cleanup`, and `weekly_run_logs`. v446 is
therefore now the latest Windows setup/bootstrap/bounded-backend/evidence-bundle
proof. A non-browser UI health smoke then launched v446 through
`scripts\launch.bat`, received HTTP `200` from
`http://127.0.0.1:8501/_stcore/health` and `http://127.0.0.1:8501/`, and
stopped the v446 listener with `listener_after_count=0`; the pulled evidence is
`logs/win-v446-stage6/v446-ui-smoke-20260516-080445.json`. A browser-level
read-only navigation smoke then kept v446 running in a foreground SSH session,
opened `127.0.0.1:18501 -> Windows 127.0.0.1:8501` with
`ClearAllForwardings=no`, and rendered the real Streamlit UI through Playwright.
The page title became `EIDP Operator Console`; snapshots captured
`① 学校別タスク` with build `e9f91cc`, `PDF確認・手入力`,
`Excel プレビュー`, and `⑤ 設定（年度・OCR・API）`. Only navigation buttons
were clicked; no weekly re-fetch, workbook generation, settings save, or other
write action was invoked. Evidence is under
`output/playwright/v446-ui-smoke/`, including `school-tasks-page.yml`,
`pdf-manual-entry-page.yml`, `excel-preview-page.yml`, `settings-page.yml`, and
`settings-page.png`. Cleanup stopped the v446 Streamlit processes and closed the
local tunnel; both Windows `8501` and local `18501` had no remaining listener.
v446 is still not a completed operator real-cycle Stage 6 sign-off.

A process-scoped v446 FY2025/R7 Excel browser probe was also attempted after the
browser navigation proof. The UI correctly rendered `2025年度（令和7年度）`, and
post-cleanup checks confirmed neither `C:\Users\<operator>\EIDP-v446-e9f91cc\.env`
nor `C:\Users\<operator>\EIDP-v446-e9f91cc.env` existed, so the target year was not
persisted. However, this fresh v446 installation was set up under FY2026 and the
FY2025 Excel preview remained at `Excel出力可 0/2418`; it therefore did not
replace the historical v442 R7 browser Excel proof. v454 now supersedes this
boundary with a process-scoped R7 browser Excel proof on the current Windows
lane.

v445 is the previous Windows setup/canary package. It was built from package snapshot
`19ceb0dee69fe7b90e32a9a90591018d9c5e773f` after the v444 canary showed that
`日本工学院北海道専門学校` was stuck with `東京都` from `採録状況`/`対象比率`, preventing
the Hokkaido prefecture aggregator from attaching the official disclosure URL.
v445 reconciles a unique school's prefecture from `学科別` during master import,
while keeping `対象比率` from mutating the canonical school prefecture. The v445
non-Windows gate returned `ok=true` with SHA256
`3cd36e11e281a4cd9646bcb865a006f5e99c9f15fae1f7700f65714aa56ba04b`,
package/source commit match, validator/distribution tests `164 passed`,
validator mypy/Ruff pass, discovery-gold expected predictions `44/44`, and both
package verifier modes pass. Windows transfer SHA matched, setup completed with
SQLite integrity ok, and setup logs confirmed
`school_prefecture_reconciled` for `日本工学院北海道専門学校` from `東京都` to `北海道`.
URL-only bootstrap then attached
`https://www.nkhs.ac.jp/about/publicindex/` as a `prefecture_aggregator`
`disclosure` URL with confidence `0.95`. The bounded 5-school weekly canary
exited `0` and improved the failure shape: `candidate_school_mismatch=0`,
`operator_reviewable_count=1`, and the RCA bucket for school id 3 became
`target_form_without_year_evidence`. It still failed the production yield gate:
`target_pdf_auto_acquired_count=0`, `target_pdf_auto_yield_pct=0.0`, and
`ship_gate_status=below_gate`, because the official page exposes 2025 and older
申請書 files but no FY2026/R8 target-form evidence yet. The v445 evidence bundle
`logs/win-v445-stage6/stage6-evidence-20260515-223848.zip` verified on both
Windows and Mac with `ok=true`, no forbidden or unsafe entries, and present
labels `bootstrap_logs`, `bootstrap_progress`, `build_info`, `diagnostics`,
`discovery_evidence`, `discovery_rca`, `last_run`, and `weekly_run_logs`; it is
still missing `stage6_recovery` and `stage6_residual_cleanup`, so v442 remains
the broader recovery/browser/R7 Excel fallback proof.

v442 remains the latest verified Stage 6 evidence-bundle/browser/R7 Excel
fallback package. It was built from package snapshot
`22f1a98ffbc3e0aeec2f658c5f1e77927045f14c`, which lets
`scripts\weekly_run.bat` keep its production default while accepting trusted
bounded-smoke environment variables such as `EIDP_WEEKLY_LIMIT`,
`EIDP_WEEKLY_BATCH_SIZE`, `EIDP_WEEKLY_RATE_LIMIT`, and
`EIDP_WEEKLY_REQUEST_TIMEOUT`. This allows Stage 6 to exercise the real
Task-Scheduler launcher and generate `logs\run-*.log` without running an
unbounded weekly crawl during validation. v441 added raw target-year discovery
rejection JSONL files to the Stage 6 evidence bundle so RCA evidence can be
rechecked without returning to the operator PC.
v440 was built from package snapshot `2f339ce82dbcfdb1a000fe378b304596823de4a6`, which
includes the v437 structured logging hardening, v438/v439 release-gate
cleanup, and v440 default cleanup for auto-generated retroactive Excel app
roots. Excel export thresholds are read per call, proposal-review write
helpers require an app lock, Stage 6 residual cleanup refuses protected runtime
files, and operator settings no longer persist `EIDP_TARGET_FISCAL_YEAR` into
`.env`. v440 also preserves provider-specific OCR extraction methods for
PaddleOCR/PyMuPDF, widens `DepartmentYearly` and `SupportRecipient` confidence
precision to `Numeric(4,3)`, makes the fiscal-year override pipeline reject
out-of-range target years directly, and audits collateral target-year
current-row demotions before replacing them. v440 widens the CLI write-lock
contract tests to cover all `cli_*.py` command modules and attribute-form
write helper calls, surfaces invalid ingest fiscal-year annotations, locks
manual-entry yearly revision reads, writes manual-entry `SchoolYearStatus` and
`SupportRecipient` rows, aligns installed-wheel app-root/data-dir defaults,
replays Stage 6 performance indexes for existing SQLite operator DBs, locks
school URL crawl-evidence JSONL appends, and configures structured JSONL
logging for the main operator entrypoints. The operator E2E template remains
package-neutral. The v442 package was built with
`uv run python scripts/build_windows_zip.py --skip-download --out-zip
dist/eidp-windows-v442.zip --latest-alias`. The build wrote
`dist/eidp-windows-v442.zip`, `dist/eidp-windows-v442.zip.sha256`, and refreshed
`dist/eidp-windows.zip`. The release gate confirmed SHA256
`4bf15f953be371b506b131ba59cf59c205259be1d7b49f084b94ddb78f66e0c7` and
`dist/eidp-windows-v442.zip.sha256` carries the same value.
`scripts/verify_windows_distribution.py dist/eidp-windows-v442.zip` returned
`ok=true` inside the v442 package gate with
`git_commit=22f1a98ffbc3e0aeec2f658c5f1e77927045f14c`, `git_dirty=false`,
`wheel_count=78`, `project_wheel_count=1`, `entry_count=3080`,
`prefecture_seed_rows=47`, `prefecture_seed_parser_supported=47`,
`prefecture_seed_downloadable=47`, `prefecture_seed_school_rows_total=2148`,
`discovery_gold_set_entries=44`, and no undemonstrated discovery pattern
sources. The v437 full gate also covers the launch-script localhost contract,
the URL-annotation URI filter, the operator review lock regressions, per-call
Excel threshold regression, protected-runtime-file residual cleanup guard,
target-fiscal-year non-persistence regression, OCR provider method regression,
confidence precision contract, fiscal-year override collateral-demotion audit
regression, and retroactive Excel app-root cleanup regression. The v440 full
unit suite also covers the expanded CLI
write-lock AST contract and the `invalid_fiscal_year` ingest regression, plus
the manual-entry row-lock, support-recipient, app-root/data-dir, and SQLite
performance-index regressions. It also covers structured JSONL logging for both
`structlog` and stdlib records, idempotent logging setup, and CLI/Streamlit/
weekly-runner logging entrypoint wiring.

The coverage gate is now machine-enforced in CI as well as locally. `uv run
pytest --cov=src/eidp --cov-report=term --cov-fail-under=80` returned
`1555 passed`, `TOTAL 14201 2836 80%`, and `Required test coverage of 80%
reached. Total coverage: 80.03%`.

`uv run python scripts/run_non_windows_release_gates.py
dist/eidp-windows-v442.zip --skip-full-unit --json --output logs/release-gate-v442.json`
returned `ok=true`. The recorded package/source freshness check reported
`package_commit=22f1a98ffbc3e0aeec2f658c5f1e77927045f14c`,
`source_commit=22f1a98ffbc3e0aeec2f658c5f1e77927045f14c`,
`source_dirty=false`, and `stale=false`; the
validator/distribution unit slice returned `164 passed`, validator mypy/Ruff
passed, discovery-gold expected predictions matched `44/44`, and both package
verifier modes passed, including `--require-demonstrated-discovery-patterns`.
v442 has Mac/non-Windows package, Stage 6 evidence-bundle, Windows
transfer/SHA, setup, recovery, non-browser UI/default launcher smoke,
URL-only bootstrap, real `weekly_run.bat` bounded canary, and full diagnostic
evidence-label proof. The ZIP and sidecar
were copied to `C:\EIDP-staging\`; Win-side `Get-FileHash` matched SHA256
`4bf15f953be371b506b131ba59cf59c205259be1d7b49f084b94ddb78f66e0c7`. The
package was expanded to `C:\Users\<operator>\EIDP-v442-22f1a98` without
overwriting v441. `EIDP-setup.bat` completed, imported bundled `master.xlsx`,
rebuilt FY2026 school-year tasks with `school_count=2418` and
`school_fiscal_year_status_count=2418`, and `scripts\validate_install.bat
--after-setup --json` returned `ok=true` with `sqlite_integrity_check=ok`.
`scripts\bootstrap_pdfs.bat --skip-discover --url-search off
--school-url-crawl off` completed with the same URL-only bootstrap shape as
v441 (`prefectures_ok=47`, `official_school_sites_added=1311`,
`seed_imported=48`, `corporation_inferred=294`) while skipping PDF discovery.
The real launcher was then run through `scripts\weekly_run.bat` with trusted
bounded environment variables `EIDP_WEEKLY_LIMIT=5`,
`EIDP_WEEKLY_BATCH_SIZE=5`, `EIDP_WEEKLY_RATE_LIMIT=0.5`, and
`EIDP_WEEKLY_REQUEST_TIMEOUT=8`; `logs\run-20260516.log` records those args
and ended `rc=0`. The weekly summary reported `dry_run=false`, `crawled=5`,
`found=3`, `downloaded=0`, `target_missing_school_count=5`,
`new_document_count=0`, and `ship_gate_status=below_gate`.
`scripts\validate_install.bat --after-setup --after-weekly --json` returned
`ok=true`, and `scripts\stage6_recovery_check.bat
C:\Users\<operator>\EIDP-v442-22f1a98\scripts\weekly_run.bat --json` returned
`ok=true` with `action_matches_expected=true`. The refreshed v442 evidence
bundle `logs\stage6-evidence-20260515-205932.zip` verified on both Windows and
Mac with `ok=true`, `manifest_missing_patterns=[]`, no forbidden entries, and
present labels `bootstrap_logs`, `bootstrap_progress`, `build_info`,
`diagnostics`, `discovery_evidence`, `discovery_rca`, `last_run`,
`stage6_recovery`, `stage6_residual_cleanup`, and `weekly_run_logs`. This is
still a bounded launcher canary and not a completed operator real-cycle Stage 6
sign-off. A v442 non-browser UI/default launcher smoke then started the app
through `scripts\launch.bat`, received HTTP `200` from
`http://127.0.0.1:8501/_stcore/health` and from `http://127.0.0.1:8501/`,
and stopped the v442 Streamlit listener; the pulled evidence file is
`logs/win-v442-stage6/v442-ui-smoke-20260516-061159.json` with `ok=true`,
`errors=[]`, and no remaining `8501` listener. A separate v442 browser-level
read-only navigation smoke kept `scripts\launch.bat` alive in an SSH session,
opened `127.0.0.1:18501 -> Windows 127.0.0.1:8501` through an SSH tunnel, and
used Playwright to render the real browser UI. The browser title was
`EIDP Operator Console`; snapshots rendered `① 学校別タスク` with build
`22f1a98`, `② PDF確認・手入力`, `④ Excel プレビュー`, and
`⑤ 設定（年度・OCR・API）` without clicking write actions such as settings
save or weekly re-fetch. The evidence files are
`logs/win-v442-stage6/v442-browser-smoke-start-20260516-061648.json`,
`logs/win-v442-stage6/v442-browser-smoke-stop-20260516-062052.json`,
`output/playwright/v442-ui-smoke/pdf-manual-entry-page.yml`,
`output/playwright/v442-ui-smoke/excel-preview-page.yml`,
`output/playwright/v442-ui-smoke/settings-page.yml`, and
`output/playwright/v442-ui-smoke/settings-page.png`; cleanup stopped the
Windows `8501` listener, closed the local tunnel, and removed the transient
`.playwright-cli` working directory. A process-scoped v442 retroactive
FY2025 browser Excel smoke then launched the same package with
`EIDP_TARGET_FISCAL_YEAR=2025` only in the `launch.bat` process environment,
opened the UI through the same tunnel, and rendered `④ Excel プレビュー` for
`2025年度（令和7年度）`. The page reported `抽出済み学校 2031` and
`Excel対象行 7150`; clicking `プレビュー workbook を生成` produced
`シート行数: 採録状況=2418 / 対象比率=10022 / 学科別=9719 /
在籍のみ抜粋=9719`, exposed `Excel ダウンロード`, and Playwright downloaded
`eidp_master.xlsx` to
`output/playwright/v442-r7-excel-smoke/eidp-master.xlsx`. Local `openpyxl`
verification opened the workbook with sheets `採録状況`, `対象比率`,
`学科別`, and `在籍のみ抜粋`, with row/column counts `2419x10`,
`10023x22`, `9721x83`, and `9721x19`. Win-side `cmd` checks reported both
`C:\Users\<operator>\EIDP-v442-22f1a98\.env` and
`C:\Users\<operator>\EIDP-v442-22f1a98.env` missing, so the retroactive target year
was not persisted. Evidence files are
`output/playwright/v442-r7-excel-smoke/excel-preview-before-generate.yml`,
`output/playwright/v442-r7-excel-smoke/excel-generating.yml`,
`output/playwright/v442-r7-excel-smoke/excel-download.yml`, and the downloaded
workbook. Cleanup closed the browser, stopped the Windows `8501` listener, and
closed the local tunnel. v441 remains the previous
fallback package with non-browser UI-smoke/default launcher proof. v441 has
Mac/non-Windows package, Stage 6 evidence-bundle, Windows
transfer/SHA, setup, recovery, non-browser UI-smoke, URL-only bootstrap, and
bounded backend canary proof. The ZIP and sidecar were copied to
`C:\EIDP-staging\`;
Win-side `Get-FileHash` matched SHA256
`53a4a237e3f4cd59becacfcc31bf7434de9a4a52a68f43e1c7478d432f8d13c9`, and a
read-only Win-side zipfile check confirmed `BUILD_INFO.git_commit` is
`33044bd28b05c69b86ad0ebe1db96672b19632d3` and that packaged
`scripts/collect_stage6_evidence.py` contains the
`*-discovery-rejections.jsonl` evidence pattern. The package was expanded to
`C:\Users\<operator>\EIDP-v441-33044bd` without overwriting v440. `EIDP-setup.bat`
completed, imported bundled `master.xlsx`, rebuilt FY2026 school-year tasks
with `school_count=2418` and `school_fiscal_year_status_count=2418`, and
`scripts\validate_install.bat --after-setup --json` returned `ok=true` with
`sqlite_integrity_check=ok`.
`scripts\stage6_recovery_check.bat
C:\Users\<operator>\EIDP-v441-33044bd\scripts\weekly_run.bat --json` returned
`ok=true` and confirmed the Task Scheduler action matches v441. A non-browser
Streamlit smoke started v441 through `scripts\launch.bat`, received HTTP `200`
from `http://127.0.0.1:8501`, and then stopped all v441-related
Python/Streamlit/cmd processes (`remaining_processes=0`). The old v438
deployment directory was removed after this smoke; at that point Windows
retained v441 as current and v440 as fallback. After v442 validation, Windows
now retains v442 as current and v441 as fallback. v441 then ran
`scripts\bootstrap_pdfs.bat --skip-discover --url-search off
--school-url-crawl off`, which completed with `prefectures_ok=47`,
`official_artifacts_parsed=55`, `official_index_rows_extracted=1951`,
`official_index_rows_matched=1774`, `official_school_sites_added=1311`,
`seed_imported=48`, and `corporation_inferred=294`, while skipping PDF
discovery. A process-local FY2026 dry-run
`run_weekly_target_year_discovery.py --dry-run --limit 24` then selected
`target_missing_school_count=24` and reduced
`no_crawlable_url_school_count` to `794`, proving the weekly runner can now
select bounded target-missing schools from the registered URLs. Finally, a
bounded actual canary
`run_weekly_target_year_discovery.py --limit 5 --batch-size 5
--request-timeout 8 --rate-limit 0.5` completed with `dry_run=false`,
`crawled=5`, `found=3`, `downloaded=0`, `failed=3`,
`target_missing_school_count=5`, `new_document_count=0`, and
`ship_gate_status=below_gate`. The refreshed v441 evidence bundle
`logs\stage6-evidence-20260515-204955.zip` verified on both Windows and Mac
with `ok=true`, no forbidden entries, and present labels `bootstrap_logs`,
`bootstrap_progress`, `build_info`, `diagnostics`, `discovery_evidence`,
`discovery_rca`, `last_run`, `stage6_recovery`, and
`stage6_residual_cleanup`. The residual-cleanup dry-run reported
`existing_count=0`, `moved_count=0`, and `ok=true` for the known interrupted
v384 smoke paths. The bundle still records missing `weekly_run_logs`, so this
remains a bounded process-local canary, not a completed operator real-cycle
Stage 6 sign-off.
v440 remains the latest package with positive current-FY acquisition, ingest,
Excel export, and stratified 24-school discovery evidence. Its Windows staging
ZIP and expanded root were removed after v442 validation to keep only current
plus previous fallback deployments, but the evidence bundle and status record
remain. The v440 ZIP and
sidecar were copied to
`C:\EIDP-staging\`; Win-side `Get-FileHash` matched SHA256
`a22f5c7ddb2c49f71264d8133e105b5857164868c4bd168e0781af7b454a237e`. The v440
package was expanded to `C:\Users\<operator>\EIDP-v440-2f339ce8` without
overwriting older deployments. `EIDP-setup.bat` completed, imported bundled
`master.xlsx`, rebuilt FY2026 school-year tasks with `school_count=2418` and
`school_fiscal_year_status_count=2418`, and `validate_windows_install.py
--after-setup --json` returned `ok=true` with `sqlite_integrity_check=ok`.
`stage6_recovery_check.bat
"C:\Users\<operator>\EIDP-v440-2f339ce8\scripts\weekly_run.bat"` returned
`ok=true`, confirmed the Task Scheduler action matches v440, and confirmed the
old v384 residual paths no longer exist. A non-browser Streamlit smoke started
the v440 review app on `127.0.0.1:8501`, received HTTP `200`, observed
`Uvicorn server started on 127.0.0.1:8501`, and then stopped the process; a
follow-up process check found no remaining v440 Streamlit/Python process. A
process-local FY2025 dry-run
`run_weekly_target_year_discovery.py --current-fy 2025 --dry-run --limit 20`
wrote `data/output/last_run.json` with `dry_run=true`, `new_document_ids=[]`,
and `ship_gate_status=not_measured`. The resulting evidence bundle
`logs/stage6-evidence-20260515-193908.zip` verified on both Windows and Mac
with `ok=true`, present labels `build_info`, `diagnostics`, `last_run`, and
`stage6_recovery`, and no forbidden or unsafe entries. This is still a
setup/UI/recovery dry-run evidence bundle, not a completed operator real-cycle
Stage 6 sign-off.

After the disk cleanup pass, v440 was advanced through a bounded Windows
bootstrap/backend canary without bulk PDF download. Running
`scripts\bootstrap_pdfs.bat --skip-discover --url-search off
--school-url-crawl off` completed and wrote
`logs\bootstrap-pdfs-20260516-044352.{log,json}`. The URL-only bootstrap
registered `school_site_rows=1653`, `schools_with_site=1624/2418`,
`document=0`, and `data\pdfs` remained `0` bytes; the registered URL sources
were `prefecture_aggregator=1311`, `corporation_pattern=294`, and
`seed_csv=48`. A second process-local FY2025 dry-run
`run_weekly_target_year_discovery.py --current-fy 2025 --dry-run --limit 20`
then wrote `target_missing_school_count=20` and
`no_crawlable_url_school_count=794`, proving the weekly runner can now select
bounded target-missing schools from the registered URLs. Finally, a bounded
actual canary
`run_weekly_target_year_discovery.py --current-fy 2025 --limit 5
--batch-size 5 --request-timeout 8 --rate-limit 0.5` completed with
`dry_run=false`, `crawled=5`, `found=3`, `downloaded=0`, `failed=3`,
`target_missing_school_count=5`, `new_document_count=0`,
`ship_gate_status=below_gate`, and a `discovery_rca` batch plan containing
`5` items. This canary increased the v440 root by less than 1 MB and left
`data\pdfs` at `0` bytes. The refreshed evidence bundle
`logs\stage6-evidence-20260515-195110.zip` verified on both Windows and Mac
with `ok=true`, present labels `bootstrap_logs`, `bootstrap_progress`,
`build_info`, `diagnostics`, `discovery_rca`, `last_run`, and
`stage6_recovery`, and no forbidden or unsafe entries. Its manifest still
records missing `weekly_run_logs` and `stage6_residual_cleanup`, so this is a
bounded diagnostic canary, not a completed operator real-cycle Stage 6
sign-off.

The same v440 Windows installation also completed a targeted FY2026 acquisition
and extraction smoke against four high-confidence `prefecture_aggregator`
disclosure URLs that were registered by the URL-only bootstrap. The targeted
command was
`eidp discover-pdfs --discovery-method prefecture_aggregator --school-id 1317
--school-id 1369 --school-id 1375 --school-id 1721 --batch-size 4
--rate-limit 0.5 --request-timeout 12`, and it returned `crawled=4`,
`found=4`, `downloaded=3`, `failed=1`, `skipped=0`, `prefiltered=0`,
`candidate_school_mismatch=0`. The three downloaded documents were target
FY2026 PDFs for school IDs `1317`, `1369`, and `1375`, with total
`data\pdfs` size still under 1 MB. Targeted ingest of document IDs `1`, `2`,
and `3` returned `processed=3`, `yearly_upserted=5`,
`departments_created=3`, `skipped=0`, and `invalid_fiscal_year=0`; two
documents ended `ingest_status=ingested` and one ended
`ingest_status=review_pending`. Rebuilding FY2026 school-year tasks returned
`rebuilt=2418` and `excel_ready=2`, and `export-excel --output
data\output\v440-targeted-fy2026-canary.xlsx` completed with row counts
`採録状況=2418`, `対象比率=10022`, `学科別=9722`, and
`在籍のみ抜粋=9722`. `report ship-readiness --fy 2026 --json` still returned
`ok=false`: `strict_target_pdf_schools=2`, `strict_target_pdf_rate=0.0008`,
`operator_reviewable_schools=2`, `estimated_manual_workload_rate=0.9992`,
and `excel_ready_rate=0.0008`. This proves the current-FY acquisition →
ingest → Excel path on Windows for a bounded positive sample; it does not
prove the 60% production yield gate.

To avoid overfitting to the positive smoke, v440 was then run against a
deterministic stratified FY2026 sample of 24 schools: one random
`prefecture_aggregator`, verified disclosure URL was selected per prefecture
from the remaining 1,308 high-confidence candidates, shuffled with seed
`20260516`, and capped at 24 schools. The command used
`eidp discover-pdfs --discovery-method prefecture_aggregator` with the 24
selected `--school-id` values, `--batch-size 24`, `--rate-limit 0.3`, and
`--request-timeout 10`. It returned `crawled=24`, `found=20`,
`downloaded=0`, `failed=3`, `skipped=232`, `prefiltered=151`,
`candidate_budget_limited=2`, `candidate_budget_dropped=179`, and
`candidate_school_mismatch=1755`. The evidence summary contained
`evidence_rows=2205`; school-level buckets were `publication_lag_or_old_target_pdf=12`,
`target_form_without_year_evidence=5`, `no_pdf_candidates=4`, and
`non_target_candidates_only=3`. The leading rejection classes were
`candidate_school_mismatch=1755`, `candidate_budget_dropped=179`,
`pre_filtered_non_target_hint=127`, `classified_non_target=60`,
`fiscal_year_mismatch:2025=25`, and
`target_fiscal_year_not_detected=12`. No additional PDFs were stored:
`data\pdfs` stayed under 1 MB. The v441 evidence collector was then run against
the v440 root to prove the new raw-evidence packaging path on real Stage 6
artifacts. The refreshed bundle
`logs\stage6-evidence-20260515-203644.zip` verified on both Windows and Mac
with `ok=true`, no forbidden entries, and present labels
`bootstrap_logs`, `bootstrap_progress`, `build_info`, `diagnostics`,
`discovery_evidence`, `discovery_rca`, `last_run`, and `stage6_recovery`.
It includes the previous weekly RCA plan, the new
`data/output/target-year-discovery/stratified-fy2026-24-discovery-rca-batch-plan.json`,
and the raw
`data/output/target-year-discovery/stratified-fy2026-24-discovery-rejections.jsonl`.
This stratified run is the strongest current signal for the next production
bottleneck: the pipeline mechanics work, but current FY2026 yield is dominated
by publication lag/old-year PDFs, target forms without trusted year evidence,
and large shared-site school-name mismatch surfaces.

The docs-only stale-package replay path remains available for status-only
follow-up commits:
`uv run python scripts/run_non_windows_release_gates.py
dist/eidp-windows-v440.zip --skip-full-unit --allow-docs-only-stale-package
--json --output logs/release-gate-v440-docs-only-stale-after-status-refresh.json`.
Treat that as a
current-source replay convenience only; it is not a Windows transfer/setup/UI
proof and it must still reject dirty tracked source or any non-doc source delta.

Mac-only v440 retroactive matrix gates passed for FY2025, FY2024, and FY2023
without SSH/Windows. The matrix run wrote
`logs/release-gate-v440-retroactive-matrix.json` with `ok=true` and
`case_count=3`. FY2025 compared against `_temp/v408-r7-cli-export.xlsx`;
FY2024 compared against
`_temp/non-windows-retroactive-fy2024-20260516-032017/output/retroactive-fy2024-export.xlsx`;
FY2023 compared against
`_temp/non-windows-retroactive-fy2023-20260516-032102/output/retroactive-fy2023-export.xlsx`.
`logs/release-gate-v440-retroactive-fy2025-reference.json`,
`logs/release-gate-v440-retroactive-fy2024-reference.json`, and
`logs/release-gate-v440-retroactive-fy2023-reference.json` all returned
`ok=true`; their validator/distribution unit slices returned `164 passed`,
their package verifiers passed, all three isolated exports wrote
`採録状況=2418`, `対象比率=10022`, `学科別=9719`, and `在籍のみ抜粋=9719`,
and all three `retroactive_excel_diff_reference` steps returned
`missing_rows=0`, `extra_rows=0`, and `differing_fields=0`. The v440 per-FY
gate JSONs also record `retroactive_excel_cleanup.ok=true` and
`removed=true`, and the fresh FY2025/FY2024/FY2023 app roots no longer exist
after the matrix run.

FY2024 and FY2023 raw-sample reference preflights were refreshed for v415 in
`docs/reports/eidp-v415-retroactive-reference-preflight.md`. Both isolated
exports succeeded with the same workbook row counts (`採録状況=2418`,
`対象比率=10022`, `学科別=9719`, `在籍のみ抜粋=9719`), while comparison against
the raw `sample/◆2025専門学校無償化情報公開まとめ.xlsx` workbook intentionally
failed. FY2024 produced `missing_rows=1097`, `extra_rows=1557`, and
`differing_fields=12548`; FY2023 produced `missing_rows=1097`,
`extra_rows=1557`, and `differing_fields=9718`. These are
reference-preparation diagnostics, not current-year yield or Stage 6 proof.

The app-code delta inherited by v415 from v410 commit
`15c88348f46ab3fbcc9383afe5830047e562b0c1` restored the documented 80% local
coverage line without using SSH/Windows, v414 added JSON Excel-diff
diagnostics on top of that source lane: `uv run pytest --cov=src/eidp
--cov-report=term-missing` returned `1520 passed` with `TOTAL 14186 2866 80%`;
`uv run mypy src` returned `Success: no issues found in 83 source files`; and
focused `ruff check` passed for the touched source/test files. This commit
covers previously weak local modules (`school_matcher.py`,
`review/populate.py`, `firecrawl_discovery.py`, `reconciler.py`,
`search_provider.py`, `pdf/ocr.py`, and `cli_reports.py`) and fixes two
source-level precision defects found while writing those tests: MEXT short
prefecture names `東京` / `大阪` / `京都` now normalize to their long Excel
forms, and Firecrawl fallback matching no longer lets a generic `専門学校` suffix
or a non-disclosure `docs/` directory pollute other schools' candidate URLs.
v415 then added a legacy Venus rediscovery asset test and widened the archived
cron/systemd `--methods` default from `prefecture_aggregator` only to the
current five-method set.

v408 remains the latest Windows-proven package for source commit
`f0c2715833b54e60fea85259e16ad0a1d9e6c106`. It was built with
`scripts/build_windows_zip.py --skip-download --out-zip
dist/eidp-windows-v408.zip --latest-alias`, and
`scripts/verify_windows_distribution.py dist/eidp-windows-v408.zip --json`
returned `ok=true` with SHA256
`61fe233e41c08b8684560778b25c36f12ad0848135e8930ef07d8fa265fbbbe2`,
`git_dirty=false`, `wheel_count=78`, `project_wheel_count=1`,
`prefecture_seed_rows=47`, `prefecture_seed_parser_supported=47`,
`prefecture_seed_downloadable=47`, `prefecture_seed_school_rows_total=2148`,
`discovery_gold_set_entries=44`, and no undemonstrated discovery pattern
sources. The sidecar SHA matched locally, the ZIP contains the
`stage6_recovery_check.py` scheduled-task XML decoder fix, and Windows SHA256
matched after transfer to `C:\Users\<operator>\eidp-windows-v408.zip`; the package
was extracted to `C:\Users\<operator>\EIDP-v408-f0c27158`. `BUILD_INFO.json`
reported commit `f0c2715833b54e60fea85259e16ad0a1d9e6c106`, branch
`sprint8-handoff-finalize`, and `git_dirty=false`.

v408 is also now setup/UI-health proven on the operator PC. Before setup,
`.venv` and `data\eidp.sqlite3` were absent and the `EIDP Weekly Run` scheduled
task still pointed to the v407 weekly runner. Running `EIDP-setup.bat` from
`C:\Users\<operator>\EIDP-v408-f0c27158` exited `0`; the setup log ended with
`Import complete.`, `School year tasks rebuilt: fiscal_year=2026
school_type=専門学校 rebuilt=2418 excel_ready=0`, `OK install:
C:\Users\<operator>\EIDP-v408-f0c27158`, and `[EIDP] Setup completed.` The standalone
install validator with `--after-setup --json` then returned `ok=true`,
`errors=[]`, `warnings=[]`, `school_count=2418`,
`school_fiscal_year_status_count=2418`, `sqlite_integrity_check=ok`,
`sqlite_table_count=15`, `wheel_count=78`, and all required runtime tables. The
scheduled task was updated to
`"C:\Users\<operator>\EIDP-v408-f0c27158\scripts\weekly_run.bat"`. A v408 packaged
recovery check against that expected action returned `task.exists=true`,
`task.error=null`, and `action_matches_expected=true`; overall `ok=false`
remained only because known old v384 smoke artifacts still exist.

The v408 Streamlit UI was then started from the same `.venv` with the launcher
environment (`EIDP_APP_ROOT`, UTF-8 settings, and `PYTHONPATH`) on Windows
`127.0.0.1:8508`. Windows-local `/_stcore/health` returned `ok`, and a Mac SSH
tunnel `127.0.0.1:18508 -> 127.0.0.1:8508` with
`-o ClearAllForwardings=no` returned `ok` for `/_stcore/health` and the
Streamlit HTML shell at `/`. The test Streamlit process and the tunnel were
stopped afterward; `18508` had no listener, and Windows `8508` had no listening
process remaining.

The packaged default launcher path was also smoke-tested on v408. Running
`EIDP-start.bat` from `C:\Users\<operator>\EIDP-v408-f0c27158` invoked
`scripts\launch.bat`, started Streamlit on default Windows port `8501`, and the
default Mac tunnel `127.0.0.1:18501 -> 127.0.0.1:8501` returned
`/_stcore/health=ok` plus the Streamlit HTML shell at `/`. The process was then
stopped intentionally; the launcher batch printed exit `-1` only because the
foreground Streamlit process was force-stopped after the health proof. macOS
`18501` had no listener afterward, and Windows `8501` had no listening process
remaining.

A Windows v408 retroactive R7/FY2025 CLI export smoke was run with process-local
`EIDP_TARGET_FISCAL_YEAR=2025`. `eidp export-excel` wrote
`C:\Users\<operator>\EIDP-v408-f0c27158\data\output\v408-r7-retroactive-export.xlsx`
with `採録状況=2418`, `対象比率=10022`, `学科別=9719`, and
`在籍のみ抜粋=9719`. The package-local `diff-excel --business-values` default
reference path still points to the absent `sample\◆2025専門学校無償化情報公開まとめ.xlsx`,
so the successful reference comparison used explicit
`--original data\master.xlsx`; it returned rc `0` while reporting the known
historical reference-workbook duplicate/key/normalization diagnostics. To prove
v408 did not regress the current R7 export path, the v408 workbook was also
compared against the already proven v407 R7 export with `--business-values
--original C:\Users\<operator>\EIDP-v407-0974b60f\data\output\v407-r7-retroactive-export.xlsx`;
that comparison returned `missing_sheets=0`, `extra_sheets=0`,
`missing_rows=0`, `extra_rows=0`, `differing_fields=0`, and zero duplicate
keys for `対象比率`, `学科別`, and `在籍のみ抜粋`. `openpyxl` opened the v408
workbook at `3,673,084` bytes with four sheets and row/column counts
`2419x10`, `10023x22`, `9721x83`, and `9721x19`.

The v408 Streamlit UI was also launched in retroactive R7/FY2025 mode on
Windows `127.0.0.1:8509` with process-local `EIDP_TARGET_FISCAL_YEAR=2025`,
and reached from macOS through an SSH tunnel `127.0.0.1:18509 ->
127.0.0.1:8509`. The browser rendered `Excel プレビュー` with
`対象年度: 2025年度（令和7年度）`, `抽出済み学校 2031`, and `Excel対象行 7150`.
Clicking `プレビュー workbook を生成` produced sheet counts
`採録状況=2418`, `対象比率=10022`, `学科別=9719`, and
`在籍のみ抜粋=9719`; clicking `Excel ダウンロード` downloaded
`_temp/v408-r7-browser-eidp_master.xlsx` with suggested filename
`eidp_master.xlsx`. `openpyxl` opened the browser workbook at `3,673,083`
bytes with four sheets and row/column counts `2419x10`, `10023x22`,
`9721x83`, and `9721x19`. After copying the Windows CLI export to
`_temp/v408-r7-cli-export.xlsx`, local `diff-excel --business-values
--original _temp/v408-r7-cli-export.xlsx _temp/v408-r7-browser-eidp_master.xlsx`
returned `missing_sheets=0`, `extra_sheets=0`, `missing_rows=0`,
`extra_rows=0`, and `differing_fields=0`, with zero duplicate keys for
`対象比率`, `学科別`, and `在籍のみ抜粋`. The Streamlit process and tunnel were
stopped afterward; macOS `18509` had no listener, and Windows `8509` had only
TIME_WAIT connections, no listening process.

The v408 browser write/audit surface was then repeated in a disposable copied-DB
sandbox at
`C:\Users\<operator>\EIDP-v408-f0c27158-ui-sandbox-20260515-02`, leaving the real
v408 runtime DB untouched. The packaged Streamlit app served Windows
`127.0.0.1:8510` with a Mac tunnel `127.0.0.1:18510 -> 127.0.0.1:8510`; health
returned `ok`. Browser click-through saved one `PDF確認・手入力` entry with reason
`stage6 v408 UI sandbox manual entry`, then applied one `年度判定・修正` override
with reason `stage6 v408 UI sandbox fiscal year override`. `監査ログ` showed
`JSONL outbox 未送信=7`; clicking `Outbox を flush` returned
`exported=7 already_present=0 failed=0`. Direct sandbox DB verification found a
manual FY2025 `DepartmentYearly` row with `capacity=40`, `enrollment=28`,
`extraction_method=manual`, `extraction_confidence=1.0`, and `verified=true`;
the override document had `fiscal_year=2025` and `fiscal_year_override=2025`;
FY2024 `DepartmentYearly`, `SupportRecipient`, and `SchoolYearStatus` rows were
marked non-current while FY2025 current rows were present; and all seven
`ManualActionLog` rows had `jsonl_exported_at_present=true`. The proof log was
written to
`C:\Users\<operator>\EIDP-v408-f0c27158-ui-sandbox-20260515-02\logs\diagnostics-v408-ui-sandbox-proof-20260515-034848.json`.
The Streamlit process and tunnel were stopped afterward; macOS `18510` had no
listener, and Windows `8510` had no listening process remaining.

A v408 non-Excel diagnostic Stage 6 evidence bundle was then generated and
verified from the active operator-PC extraction. A process-local FY2025 dry-run
weekly command wrote `data\output\last_run.json` with `status=success`,
`dry_run=true`, `current_fy=2025`, `selection_mode=target_missing`,
`new_document_ids=[]`, `ship_gate_status=not_measured`, and null yield
percentages because the denominator was `0`. The packaged recovery check wrote
`logs\stage6-recovery-20260515-040010.json` with `action_matches_expected=true`
for `C:\Users\<operator>\EIDP-v408-f0c27158\scripts\weekly_run.bat`, while overall
`ok=false` remained only because five old v384 residual smoke artifacts still
exist. The packaged residual cleanup was run in dry-run mode only and wrote
`logs\stage6-residual-cleanup-20260515-040034.json` with `existing_count=5`,
`moved_count=0`, and `errors=[]`. The v408 UI sandbox proof was copied into the
main v408 logs as
`logs\diagnostics-v408-ui-sandbox-proof-20260515-034848.txt`. Running
`scripts\collect_stage6_evidence.bat` created
`logs\stage6-evidence-20260514-190257.zip`, and
`scripts\verify_stage6_evidence.bat` wrote
`logs\stage6-evidence-verify-20260515-040322.json` with `ok=true`,
`entry_count=8`, `errors=[]`, `forbidden_entries=[]`, `unsafe_entries=[]`,
`missing_required_labels=[]`, and present labels `build_info`, `diagnostics`,
`last_run`, `stage6_recovery`, `stage6_residual_cleanup`, and
`weekly_run_logs`. The manifest still records missing `bootstrap_logs`,
`bootstrap_progress`, and `discovery_rca`, so this is verifier-accepted
diagnostic evidence, not a completed Stage 6 release sign-off.

v407 remains a supporting full non-Windows release-gate source for commit
`0974b60fb3d404678828ddfa348c74f4dd740c79`. It was built with
`scripts/build_windows_zip.py --skip-download --out-zip
dist/eidp-windows-v407.zip --latest-alias`, and
`scripts/verify_windows_distribution.py dist/eidp-windows-v407.zip --json`
returned `ok=true` with SHA256
`af48ed37d65695c044b520da78aad5307ed89b4b4a38cf27c6dc7e2737f50940`,
`git_dirty=false`, `wheel_count=78`, `project_wheel_count=1`,
`prefecture_seed_rows=47`, `prefecture_seed_parser_supported=47`,
`prefecture_seed_downloadable=47`, `prefecture_seed_school_rows_total=2148`,
`discovery_gold_set_entries=44`, and no undemonstrated discovery pattern
sources. The full non-Windows release gate also passed for v407:
package/source commit matched exactly, sidecar SHA matched, `tests/unit`
reported `1480 passed`, validator/distribution tests reported `161 passed`,
validator/distribution mypy and Ruff passed, discovery-gold expected
predictions were `44/44`, and package verification with
`--require-demonstrated-discovery-patterns` passed.

v407 was transferred to the Windows operator PC as
`C:\Users\<operator>\eidp-windows-v407.zip`; Windows SHA256 matched the sidecar and
the package was extracted to `C:\Users\<operator>\EIDP-v407-0974b60f`.
`BUILD_INFO.json` reported commit
`0974b60fb3d404678828ddfa348c74f4dd740c79`, branch
`sprint8-handoff-finalize`, and `git_dirty=false`. `EIDP-setup.bat` completed
offline wheelhouse installation, SQLite bootstrap, master import, and school
task rebuild. The install validator printed `OK install` with
`school_count=2418`, `school_fiscal_year_status_count=2418`,
`sqlite_integrity_check=ok`, `sqlite_table_count=15`, `wheel_count=78`, and the
required tables including `manual_action_log`, `department_yearly`,
`support_recipient`, and `school_site`.

A Windows v407 retroactive R7/FY2025 CLI smoke was run with process-local
`EIDP_TARGET_FISCAL_YEAR=2025`. `eidp export-excel` wrote
`C:\Users\<operator>\EIDP-v407-0974b60f\data\output\v407-r7-retroactive-export.xlsx`
with `採録状況=2418`, `対象比率=10022`, `学科別=9719`, and
`在籍のみ抜粋=9719`. `eidp diff-excel --business-values` then compared that
export against `data\master.xlsx`; it returned `diff_rc=0` and showed the
current diagnostic surface: `対象比率 original_duplicate_keys=13`,
`学科別 original_duplicate_keys=22`, and
`在籍のみ抜粋 original_duplicate_keys=22`, while all three exported sheets had
`exported_duplicate_keys=0`.

The same v407 package was then launched through the browser with process-local
`EIDP_TARGET_FISCAL_YEAR=2025` on Windows `127.0.0.1:8504` and Mac tunnel
`127.0.0.1:18504 -> 127.0.0.1:8504`. `/_stcore/health` returned `ok`. The
`Excel プレビュー` page rendered `対象年度: 2025年度（令和7年度）`,
`抽出済み学校 2031`, and `Excel対象行 7150`; clicking
`プレビュー workbook を生成` produced browser-visible sheet counts
`採録状況=2418`, `対象比率=10022`, `学科別=9719`, and
`在籍のみ抜粋=9719`, plus an `Excel ダウンロード` button. Playwright downloaded
the workbook as `_temp/v407-r7-browser-eidp_master.xlsx`; `openpyxl` opened it
at `3,673,084` bytes with sheets `採録状況`, `対象比率`, `学科別`,
and `在籍のみ抜粋`, and row/column counts `2419x10`, `10023x22`, `9721x83`,
and `9721x19`. This proves the current v407 package's R7 retroactive browser
preview/download path; it remains retroactive evidence, not FY2026 production
yield.

Non-Excel proofs of that browser download and the seeded v407 UI sandbox write
cycle were copied into the Windows v407 logs as
`logs\diagnostics-v407-r7-browser-excel-proof-20260515-024000.txt` and
`logs\diagnostics-v407-ui-sandbox-proof-20260515-023041.txt`. A refreshed
non-Excel evidence bundle, `logs\stage6-evidence-20260514-174859.zip`, was then
created with `included_count=9` and verified with `--require-label last_run`:
`ok=true`, `entry_count=10`, `present_labels=["build_info", "diagnostics",
"last_run", "stage6_recovery", "stage6_residual_cleanup", "weekly_run_logs"]`,
`forbidden_entries=[]`, `unsafe_entries=[]`, and `errors=[]`. Local ZIP
manifest inspection confirmed both v407 proof files are included. The manifest
still records missing `bootstrap_logs`, `bootstrap_progress`, and
`discovery_rca`, so this remains diagnostic evidence, but it now carries both
the R7 browser Excel proof and the seeded UI write proof without bundling Excel,
SQLite, PDFs, runtime, or wheelhouse files.

The v407 UI service was started on Windows port `8501` using the packaged
Streamlit app. Windows-local `/_stcore/health` returned `ok` once during
background startup. A second verification kept Streamlit attached to the SSH
session and forwarded Mac `127.0.0.1:18501` to Windows `127.0.0.1:8501` with
`-o ClearAllForwardings=no`; Mac-side `curl
http://127.0.0.1:18501/_stcore/health` returned `ok`, and the root page returned
the Streamlit HTML shell. This proves the default `18501 -> 8501` tunnel and
UI health path for v407, but it is still not an operator browser-click write
cycle.

The first v407 Stage 6 evidence attempt was correctly rejected. Running
`scripts\collect_stage6_evidence.bat --include-excel` produced
`logs\stage6-evidence-20260514-170328.zip`, but
`scripts\verify_stage6_evidence.bat` rejected it with
`archive contains forbidden Excel exports`, missing required label `last_run`,
and missing manifest patterns including `weekly_run_logs`, `bootstrap_logs`,
`bootstrap_progress`, `last_run`, `discovery_rca`, `stage6_recovery`, and
`stage6_residual_cleanup`. After that rejection, a non-mutating v407 weekly
dry-run was executed with process-local `EIDP_TARGET_FISCAL_YEAR=2025`:
`scripts\run_weekly_target_year_discovery.py --current-fy 2025 --dry-run
--limit 1 --batch-size 1 --rate-limit 0 --request-timeout 3` wrote
`data\output\last_run.json` and
`logs\run-v407-retroactive-dryrun-20260515.log` with `status=success`,
`dry_run=true`, `current_fy=2025`, `ship_gate_status=not_measured`, no new
documents, and no measured yield. A second non-Excel bundle,
`logs\stage6-evidence-20260514-171128.zip`, was then verified by
`logs\stage6-evidence-verify-20260515-021129.json` with `ok=true`, present
labels `build_info`, `diagnostics`, `last_run`, `stage6_recovery`,
`stage6_residual_cleanup`, and `weekly_run_logs`, and no forbidden entries. This
is structurally valid **diagnostic** evidence, not a Stage 6 release sign-off:
the bundle still lacks bootstrap/discovery RCA patterns, operator
browser-click/write evidence, and measured production yield. A v407 read-only
recovery check also returned `ok=false`: the `EIDP Weekly Run` task exists, but
scheduled-task XML parsing failed, the production action path was not verified,
and the checker still sees five old v384 smoke artifacts in `C:\Users\<operator>`.
The v407 residual cleanup was run in dry-run mode only and reported
`existing_count=5`, `moved_count=0`, `errors=[]`.

The scheduled-task XML parsing failure is fixed in source commit `f0c27158` and
packaged in v408. A regression test first reproduced the misdecode case where
`schtasks /Query /XML` emits ASCII/UTF-8 bytes while the XML declaration says
`UTF-16`; after the fix, `uv run pytest
tests/unit/test_stage6_recovery_check.py -q` returned `7 passed`, the Stage 6
tooling/distribution focused suite returned `205 passed`, and Ruff/mypy passed
for the touched files. Running the v408 packaged
`scripts\stage6_recovery_check.py` on Windows before v408 setup, against the
then-expected v407 weekly action, parsed the scheduled-task XML successfully:
`task.exists=true`, `task.error=null`, `action_matches_expected=true`, and
`execute="\"C:\\Users\\<operator>\\EIDP-v407-0974b60f\\scripts\\weekly_run.bat\""`.
The overall recovery check still returned `ok=false` only because the same five
known old v384 smoke artifacts remain in `C:\Users\<operator>`; no cleanup was
applied.

A disposable v407 UI sandbox was then created on the operator PC at
`C:\Users\<operator>\EIDP-v407-0974b60f-ui-sandbox-20260515-01` with
process-local `EIDP_APP_ROOT`, `EIDP_DATA_DIR`, `EIDP_DATABASE_URL`, and
`EIDP_TARGET_FISCAL_YEAR=2025`. The packaged Streamlit app ran on Windows
`127.0.0.1:8503` and was reached from the Mac through
`127.0.0.1:18503 -> 127.0.0.1:8503`; `/_stcore/health` returned `ok`. Browser
click-through saved one `PDF確認・手入力` row with reason
`stage6 v407 UI sandbox manual entry`, applied one `年度判定・修正` override with
reason `stage6 v407 UI sandbox fiscal year override`, generated the
`Excel プレビュー` workbook with sheet counts `採録状況=2`, `対象比率=1`,
`学科別=2`, and `在籍のみ抜粋=2`, and opened `監査ログ` where the outbox showed
`JSONL outbox 未送信=7` before `Outbox を flush` returned
`exported=7 already_present=0 failed=0`. Post-click SQLite verification in the
sandbox reported `manual_doc.ingest_status=ingested`,
`override_doc.fiscal_year=2025`, `override_doc.fiscal_year_override=2025`, a
manual FY2025 `DepartmentYearly` row with `enrollment=28`,
`extraction_method=manual`, and `verified=true`, cloned FY2025 current rows for
`DepartmentYearly`, `SupportRecipient`, and `SchoolYearStatus` while the
original FY2024 rows were marked `is_current=false`, and seven
`ManualActionLog` rows all had `jsonl_exported_at_present=true`. This is the
first v407 operator-PC browser write proof, but it is still a seeded disposable
sandbox proof rather than a real operator one-cycle sign-off.

## Current Stage 6 Boundary

The active operator-PC setup/UI lane is now the v460 extraction
`C:\Users\<operator>\EIDP-v460-01e4427`. It is Mac/non-Windows release-gate-clean,
transferred to Windows, SHA-checked, extracted, set up, after-setup validated,
recovery-parser validated, diagnostics-captured, and the scheduled task now
points to the v460 weekly runner. A direct Streamlit read-only browser smoke
also passed. It is still not Stage 6 complete because no v460 weekly run,
write-path browser flow, evidence bundle, measured yield, or owner/operator
sign-off has been captured.

Already supportable from v460 evidence: ZIP transfer and SHA256 match, clean
`BUILD_INFO.json`, `EIDP-setup.bat` completion, offline wheelhouse install,
SQLite bootstrap/import, `school_fiscal_year_status` rebuild for `2418`
schools, SQLite integrity, required-table presence, scheduled-task XML parsing,
scheduled-task action confirmation for the v460 weekly runner, diagnostics
collection, read-only Streamlit/browser navigation for the four operator quick
pages, and disk health with no warn/block findings. v460 also includes the
operator-cycle hardening for Excel preview session memory, lock-held
manual-entry controls, manual-entry stale widget cleanup, and evidence recorder
closing.

Still retained from v459 as supporting evidence: evidence bundle verification,
bounded R7 weekly smoke, Streamlit UI health/default launcher, read-only browser
navigation, R7 browser Excel preview/download, and disposable copied-DB
URL-candidate reject plus audit-outbox flush. These are bounded support only;
they must not be recorded as completed v460 one-cycle sign-off.

Still retained from v408/v407 as historical support: broader disposable sandbox
browser proofs for manual entry, fiscal-year override, Excel preview generation,
`監査ログ`, and audit-outbox flush. Historical v397/v384/v399 proofs below are
retained as supporting evidence. Old residual smoke artifacts remain diagnostic
until explicitly cleaned. Do not externally share any bundle containing Excel
exports, and do not run `stage6_residual_cleanup.py --apply` without explicit
operator/user approval.

Still missing for Stage 6: the real operator-cycle browser click-through/write
flow or an explicitly approved full-cycle copy, final KPI/yield evidence with
measured non-null rates, and owner/operator sign-off. The v460 Plan A evidence
bundle is verifier-accepted, but it is not KPI-passing evidence.

Stage 6 template fill map for the v460 evidence lane:

v460 is the current Windows execution candidate because it is the latest
Mac/non-Windows release-gate-clean package that has also been transferred,
SHA-checked, set up, recovery-checked, and pointed from Task Scheduler. v459
remains the latest browser/UI/evidence-bundle support package. The rows below
are still evidence support only until the final operator real-cycle sign-off is
captured. Future transfers should keep the same SSH/SCP or no-SSH manual
transfer discipline, with Windows-side SHA256 checking before extraction.

The v460 core ZIP predates the final handoff-doc updates and intentionally stays
frozen at SHA256
`ce5fa49b8c30900a33b31fd317c6846ffe5839053f2bdd1ffdeb8cca2113129c`. Use the
ignored companion docs bundle `dist/eidp-v460-operator-docs-20260517.zip`
and verify it with `dist/eidp-v460-operator-docs-20260517.zip.sha256`. It
contains the v460 real-cycle card, E2E template, release-status snapshot, v460
evidence draft, and the setup-entrypoint template correction. This 20260517
refresh supersedes the 20260516 companion docs for operator reading only; it
does not change the v460 core package, Windows app root, scheduled task, or
release approval gate. It was copied to
`C:\EIDP-staging\eidp-v460-operator-docs-20260517.zip`, verified on Windows
with `Get-FileHash` against its sidecar, and expanded to
`C:\EIDP-staging\v460-operator-docs-20260517` with the top-level readme
`C:\EIDP-staging\00-READ-ME-FIRST-v460.txt`. The tracked source for that
top-level readme is `docs/runbooks/00-READ-ME-FIRST-v460.txt`, with SHA256
`e7524506f4810dda199d1a1c4f4abb8d763348eef3e50ecebd99ac524abdff20`, matching
the v460 handoff manifest. The short owner/operator request is also mirrored as
tracked source at `docs/runbooks/eidp-v460-owner-request-20260516.txt`, with
SHA256 `f316bf55acdf8d7d36dd651fc49a269f8127b7ceba366aebc31c7bdf30ebb211`,
matching `dist/eidp-v460-owner-request-20260516.txt`.

A post-doc-refresh recovery check wrote
`logs/win-v460-stage6/stage6-recovery-20260517-064336.json` on the Mac side.
It returned `ok=true`, `action_matches_expected=true`, all residual paths
`exists=false`, and SHA256
`41dd47aee0a304371cab5633397017f45e4f1a1d090b186986d48c49cf38acf6`.

A focused first-read path audit over the Windows staging README, owner request,
real-cycle card, E2E template, and 20260517 manifest found no `first_setup.bat`
and no old `v460-operator-docs\` path. The expected
`v460-operator-docs-20260517` paths were present in the operator-facing entry
documents.

The post-package `.env.example` source commit `2768f02` is a future-package
configuration-documentation improvement only. It must not be used as evidence
that the current v460 Windows ZIP exposes the Step 2c school URL crawl defaults.

| Template section | Can be filled from current evidence | Still required |
| --- | --- | --- |
| 1. 実施情報 | v460 package snapshot `01e44279238aaef9127ed9b578e29dc8e0070499`; `dist/eidp-windows-v460.zip`; SHA256 `ce5fa49b8c30900a33b31fd317c6846ffe5839053f2bdd1ffdeb8cca2113129c`; extract path `C:\Users\<operator>\EIDP-v460-01e4427` | Operator/owner sign-off fields; final verifier JSON path; add-on SHA fields if used |
| 2. PC / 環境 | Current operator-PC host is `JUNMING`, user `junming`, home `C:\Users\<operator>`; fresh v460 disk health is `ok=true`, `warn_count=0`, `block_count=0` with copy `logs/win-v460-stage6/disk-health-20260517-operator-win.json`; historical environment details from v380/v384 include Windows 11 Pro build `26200`, i9-13900HK, about 32 GB RAM | Final v460/operator run should recapture locale, Defender/SmartScreen, network, free disk, and console encoding in the final diagnostics bundle |
| 3. 証跡採取コマンド | v460 hash/setup/validate/recovery diagnostics, read-only browser navigation, and a correctly rejected diagnostic evidence bundle are available; v464 R7-browser-Excel proof is available; v459 evidence-bundle/default-launcher/UI-write-sandbox proofs remain bounded support; v408/v384 historical seeded UI write proofs are retained as support for broader write paths | `EIDP-diagnose.bat` after the real click-through cycle; verifier-accepted v460 final evidence bundle from the real operator cycle |
| 4. Setup 結果 | ZIP extraction, `EIDP-setup.bat`, `.venv`, DB bootstrap, master import, `2418` fiscal-year status rows, SQLite integrity, required tables, Streamlit health, read-only navigation, and scheduled task action pointing to `C:\Users\<operator>\EIDP-v460-01e4427\scripts\weekly_run.bat` | Final setup diagnostics after the real operator cycle; optional v460 default-launcher re-smoke if the owner requests it before the real run |
| 5. 4 工程 E2E | v460 browser navigation rendered the core operator pages without invoking writes; v460 Plan A CLI weekly wrote `last_run.json` and a verifier-accepted evidence bundle; v459 bounded R7 weekly downloaded two target PDFs, v464 process-scoped R7 browser Excel preview/download produced the expected workbook with sheet data rows `2418/10022/9719/9719`, and a disposable v459 UI sandbox proved URL-candidate reject plus audit-outbox flush through the browser; v408/v384 remain historical support for manual-entry and fiscal-year-override UI writes | Complete v460 real operator-cycle click-through or approved full-cycle copy; final current-FY PDF collection metrics |
| 6. KPI 判定 | v460 Plan A recorded `ship_gate_status=not_measured`, `target_pdf_auto_yield_pct=null`, `operator_reviewable_yield_pct=null`, and `ship_readiness_rc=null` in the copied `last_run.json` because `no_crawlable_url_school_count=2418`; v459 bounded R7 canary recorded `target_pdf_auto_yield_pct=40.0`, `operator_reviewable_yield_pct=100.0`, `ship_gate_status=pass`, and `new_document_ids=[1, 2]`. FY2026 production output and final R8 yield remain unproven | v460 real click-through diagnostics and final current-year `ship_readiness_rc=0` |
| 7. 監査 / outbox | v459 disposable UI write/audit sandbox showed flush result `exported=2 already_present=0 failed=0`, `pending_outbox=0`, one seeded audit row plus one `url_candidate_rejected` row exported, matching JSONL action IDs, no `SchoolSite` for the rejected URL, and real runtime DB marker counts all `0`; v408/v407 sandboxes show broader historical surfaces | Real or approved full-cycle `manual_action_log` delta and final JSONL duplicate check |
| 8. 障害 / 回避策 | Known current hazards: v460 lacks real-cycle proof; v459 UI-write proof is sandbox-only; v459 bounded strict auto-yield is `40.0%`; v407 evidence bundle with Excel export is verifier-rejected; old v384 residual smoke artifacts still exist; SSH `ClearAllForwardings=no` is required for tunnel proof | Actual v460 full-cycle failures and screenshots/log attachments |
| 9. Release 判定 | Current status remains no-go for GA and not yet rc1-tagged | Operator one-cycle completion, KPI owner approval, runbook fix confirmation, and sign-offs |

v397 was previously transferred to the operator PC and setup-validated in the
disposable extraction
`C:\Users\<operator>\EIDP-v397-3c100c7-setup-probe`. Windows SHA256 matched the
same sidecar value, `BUILD_INFO.json` reported commit
`3c100c7aba5e812bcd791dcc227c775f1f3d93e6`, branch
`sprint8-handoff-finalize`, and `git_dirty=false`, and the setup run completed
the offline wheelhouse install, `db-bootstrap`, `import-excel`, school-year task
rebuild, and after-setup validation. The setup log ended with
`Import complete.`, `School year tasks rebuilt: fiscal_year=2026
school_type=専門学校 rebuilt=2418 excel_ready=0`, and `OK install`. The
standalone validator then returned `validate_rc=0` with `school_count=2418`,
`school_fiscal_year_status_count=2418`, `sqlite_integrity_check=ok`,
`sqlite_table_count=15`, `wheel_count=78`, and no duplicate wheel
distributions; `eidp.cli --help` returned `cli_help_rc=0`; `data\eidp.sqlite3`
exists; and the smoke harness found no residual v397 processes after cleanup.

v394 remains the latest Windows evidence-bundle verifier proof: it transferred
cleanly to the operator PC, extracted with root launchers
`EIDP-stage6-evidence.bat`, `EIDP-stage6-recovery.bat`, and
`EIDP-stage6-verify-evidence.bat`, returned the expected negative verifier
result for a missing evidence ZIP, and then verified a minimal collected
`logs\stage6-evidence-*.zip` with `VERIFY_BAT_RC=0`. The historical v401 full
non-Windows release gate passed with the then-current verifier, `1433` unit
tests, and `44` exact discovery gold-set predictions. With the current source
verifier, a read-only skip-full rerun now rejects v401 at `package_verify`
because the ZIP predates the newer Stage 6 safety and audit-outbox verifier
tokens; SHA256, validator/distribution tests, validator mypy/Ruff, gold-set
summary, and expected-prediction replay still pass. Treat v401 as a stale
package relative to the current source evidence base, not as a current
Mac-verifier-clean candidate. In that historical slice, the Windows UI health
and seeded browser-write proof had advanced to v408; v397 remains the historical read-only
quick-navigation proof across the full sidebar. The existing
`C:\Users\<operator>\EIDP-v397-3c100c7-setup-probe` disposable extraction started
Streamlit on Windows `127.0.0.1:8502`; the local SSH tunnel
`127.0.0.1:18502 -> Windows 127.0.0.1:8502` returned `/_stcore/health` as
`ok`. Browser/Playwright rendered `http://127.0.0.1:18502/` with title
`EIDP Operator Console`; the snapshot showed the default `① 学校別タスク` page,
target `2026年度（令和8年度）`, build `3c100c7`, `対象年度 要対応 2418`,
`Excel出力可 0/2418 校`, and the initial acquisition warning. The same
read-only probe clicked only the non-mutating quick navigation buttons for
`PDF確認・手入力`, `対象年度の判定・修正`, `④ Excel プレビュー`,
`⑤ 設定（年度・OCR・API）`, and back to `① 学校別タスク`; each page rendered,
the Excel page showed `対象年度: 2026年度（令和8年度） / 対象範囲: 専門学校`,
and the workbook-generation button remained disabled for empty FY2026 data.
The incremental console capture contained only verbose browser DOM notices
about password fields outside forms, not application/page errors. Historical
v384 UI evidence remains valid for setup, diagnostics, UI service, read-only
navigation, the FY2026 Excel disabled-state display, and the retroactive
FY2025/R7 Excel preview/download browser path. The v384 R7 probe ran with
process-scoped
`EIDP_TARGET_FISCAL_YEAR=2025`, showed `抽出済み学校 2031` and
`Excel対象行 7150`, generated the in-memory workbook, exposed
`Excel ダウンロード`, downloaded `eidp_master.xlsx` at `3,728,651` bytes,
and the downloaded workbook opened with sheets `採録状況`, `対象比率`,
`学科別`, and `在籍のみ抜粋`. The workbook row counts observed through
`openpyxl` were `採録状況=2419`, `対象比率=10023`, `学科別=9721`,
and `在籍のみ抜粋=9721`, including header rows; the Streamlit stdout export
counts were `採録状況=2418`, `対象比率=10022`, `学科別=9719`, and
`在籍のみ抜粋=9719`. The R7 probe was then stopped and removed; cleanup
confirmed no `8501` listener remained and the scheduled task still points at
v380. v384 now also has a sandboxed `PDF確認・手入力` browser save proof:
a disposable copied-DB extraction under
`C:\Users\<operator>\EIDP-v384-75732b0-manual-entry-sandbox` seeded one FY2026
`parse_failed` document, the tunneled UI saved one `V384手入力学科` row with
reason `v384 UI manual entry smoke`, and post-UI SQLite verification found
the document promoted to `ingested`, one manual `DepartmentYearly` row, three
`manual_entry` audit rows, zero SupportRecipient rows for that document, and
zero matching marker rows in the real runtime DB. v384 now also has a
sandboxed URL-candidate reject browser proof: the UI opened `詳細 operator`
-> `URL候補レビュー`, rejected one seeded
`https://example.com/eidp-v384-url-candidate-smoke` candidate with reason
`v384 UI reject smoke`, resolved the `ReviewItem`, emitted one
`url_candidate_rejected` audit row, created no `SchoolSite` row, and left the
real runtime DB with zero matching marker rows. v384 now also has a sandboxed
audit-outbox browser flush proof: the UI opened `詳細 operator` -> `監査ログ`, verified
`JSONL outbox 未送信` pending count `1`, clicked `Outbox を flush`, observed
`exported=1 already_present=0 failed=0`, and post-UI verification found the
seeded `stage6_v384_ui_audit_flush_smoke` row stamped as exported, one matching
JSONL row, pending count `0`, and zero matching marker rows in the real runtime
DB. v384 now also has a sandboxed `③ 年度判定・修正` browser write proof:
the UI submitted `年度を確定` with reason
`v384 UI fiscal override smoke`, moved one seeded FY2025 ingested document to
FY2026, demoted the old current `DepartmentYearly`, `SupportRecipient`, and
`SchoolYearStatus` rows, demoted a pre-existing FY2026 `DepartmentYearly` row,
inserted new FY2026 current rows, and emitted four `fiscal_year_override`
audit rows without mutating the real runtime DB. v384 now also has persistent
operator-PC environment capture, scheduler query / restore evidence, and a
package-local `eidp db-backup` smoke: the v384 sandbox reported host `JUNMING`,
Windows 11 Pro build `26200`, i9-13900HK, 32 GB visible RAM, `C:` free
`964.4` GB, `db_backup_rc=0`, backup `integrity=ok`, `sqlite_objects=35`,
`school_count=2418`, and restored `EIDP Weekly Run` back to the v380 runtime
task. v384 now also has the package-local SupportRecipient
backend ingest smoke: the v384 package runtime seeded two FY2026 target
documents, monkeypatched only the package parser boundary, called
`ingest_document` twice, and verified SupportRecipient revisions `1` and `2`
with only revision `2` current while the real runtime DB marker counts stayed
zero. v380 was transferred to the operator PC, hash-checked, extracted into a
separate directory, set up with `EIDP-setup.bat`, diagnosed, and smoke-tested
through `eidp db-backup`.
v380 also has
read-only operator-PC
environment and scheduler
evidence: host `JUNMING` is `Microsoft Windows 11 Pro` build `26200`, with a
13th Gen Intel Core i9-13900HK, about 32 GB visible RAM, `C:` free space
`1058.8` GB, and an `EIDP Weekly Run` scheduled task in `Ready` state pointing
at `C:\Users\<operator>\EIDP-v380-f6a5e6d\scripts\weekly_run.bat`. v380 also proves
the retroactive FY2025/R7 Excel preview/download browser path
with the same package. v380 has the older sandboxed URL-candidate reject
browser write path and audit-outbox browser flush path against disposable
copied databases.
v380 also has the older
`PDF確認・手入力` browser save path and `③ 年度判定・修正` browser write path
for disposable copied databases. v384 now also has a sandboxed bounded backend
bootstrap smoke for the 5-site Saitama official-index path: it downloaded the
Saitama artifact, added `51` prefecture-aggregator SchoolSite rows, crawled `5`
sites, wrote `2084` discovery evidence lines, generated an RCA batch with `5`
items, rebuilt `2418` status rows, and left the real runtime DB unchanged.
These observations are consolidated in
`docs/reports/eidp-v418-stage6-evidence-draft.md` as a draft, not a completed
operator sign-off. OCR add-on runtime proof is now stronger but still bounded:
the v380 operator install has no `ocr-addon` directory and
`detect_ocr_availability` correctly reports `can_run=false`; v381 carried the
Windows RAM-detection fix and a runtime-only probe on the operator PC returned
`cpu_count=20`, `free_ram_mb=16242`, and `ocr_auto_enable=true`; v382 added the
stricter `--require-ocr-runtime` validator gate that executes packaged
`tesseract.exe --version` and `tesseract.exe --list-langs`; and v383 adds the
TSV config file required by the OCR wrapper's TSV path. A v383 smoke OCR add-on
ZIP built from UB Mannheim Windows Tesseract `v5.4.0.20240606` plus local
`jpn.traineddata` verifies as SHA256
`bd1e2c96dcd7ac17562d44c3338fbf8da0ac21a1b1e60386073c730775e8d853`,
`entry_count=267`, and `manifest_files=266`. In a disposable operator-PC v384
extraction with the add-on, the OCR image smoke generated
`ocr_full_text="V384 OCR WRITE SMOKE 2026"` from a PNG,
`ocr_conf_values=[93,94,96,96,96]`, `ocr_avg_confidence=0.95`, inserted one
`DepartmentYearly` row through `save_manual_entries` with
`extraction_method="ocr_tesseract"`, `extraction_confidence=0.95`, and
`verified=true`, promoted the copied-DB document from `ocr_pending` to
`ingested`, and emitted three `manual_entry` audit rows for `department`,
`department_yearly`, and `document`. The real v380 runtime DB had `0` matching
marker rows after the smoke, the disposable v384 probe directory and uploads
were removed, and the weekly task was confirmed restored to the v380 runtime
path. This proves packaged add-on runtime execution, TSV output parsing, and an
OCR-sourced DepartmentYearly write in a copied DB on the latest v384 package.
Post-v383 source now also routes image-PDF ingest through the
packaged/system Tesseract TSV wrapper when available and propagates
`ocr_tesseract` confidence breakdowns to both `DepartmentYearly` and
`SupportRecipient` rows in focused unit coverage. A disposable operator-PC v384
extraction under
`C:\Users\<operator>\EIDP-v384-75732b0-ocr-runtime-probe` then expanded the v384
core ZIP plus the v383 smoke OCR add-on and ran
`runtime\python\python.exe scripts\validate_windows_install.py . --require-ocr-runtime --json`;
it returned `ok=true`, build commit
`75732b057a115afcebe35f9a40b831fac0ffa6f6`, `build_dirty=false`,
`wheel_count=78`, packaged Tesseract
`C:\Users\<operator>\EIDP-v384-75732b0-ocr-runtime-probe\ocr-addon\tesseract\tesseract.exe`,
version `tesseract v5.4.0.20240606`, and languages including `jpn` and
`jpn_vert`. This proves the latest v384 package can detect and execute the OCR
add-on on the operator PC. A follow-up disposable v384 copied-DB smoke under
`C:\Users\<operator>\EIDP-v384-75732b0-ocr-write-sandbox` used the same v384 core
ZIP plus the v383 OCR add-on, generated `data\ocr-write-smoke.png`, ran
packaged Tesseract through `run_tesseract_on_image(...)`, and returned
`ocr_full_text="V384 OCR WRITE SMOKE 2026"`, `ocr_usable_word_count=5`,
`ocr_conf_values=[93,94,96,96,96]`, and `ocr_avg_confidence=0.95`; then
`save_manual_entries(..., method="ocr_tesseract")` wrote one copied-DB
`DepartmentYearly` row with `extraction_method="ocr_tesseract"`,
`extraction_confidence=0.95`, and `verified=true`, promoted the marker
document from `ocr_pending` to `ingested`, and emitted three `manual_entry`
audit rows for `department`, `department_yearly`, and `document`. The real v380
runtime DB had `0` matching marker rows, cleanup removed the v384 OCR sandbox
and uploads, and a follow-up query confirmed `EIDP Weekly Run` was `Ready` with
action `C:\Users\<operator>\EIDP-v380-f6a5e6d\scripts\weekly_run.bat`. It still does
not prove
operator-PC real target-form OCR extraction, operator-PC SupportRecipient OCR
writes, or a full Stage 6 operator cycle. The latest bounded bootstrap proof is
the v384 Saitama 5-site sandbox; the broader 50-site bootstrap evidence remains
v342.

Release gate interpretation:

- **Process gate / v1.0-rc evidence**: a real operator-PC Stage 6 cycle proves
  setup, diagnostics, UI navigation, audit logging, Excel preview/download, and
  bounded write behavior on the handed-off Windows package. FY2025/R7
  retroactive validation may support this process evidence because it tests the
  rolling-fiscal-year mechanics against a more complete disclosure season.
- **Yield gate / v1.0 GA evidence**: current target-FY FY2026/R8 readiness must
  still reach the shipping line: true target confirmation PDFs are acquired or
  operator-reviewable at a rate sufficient for estimated manual workload
  `<=30%`. Retroactive FY2025 evidence must not be counted as FY2026/R8
  current-year yield or Excel readiness.

v376 fixes a Windows-only diagnostics bug in the retroactive fiscal-year
snapshot: the v375 ZIP passed token-based package verification, but real
Windows batch execution skipped the FY2025 `ship-readiness --fy` call because
the batch-side Python-output capture was too fragile. The v376 package moves
that logic into Python and records the retroactive JSON plus
`retroactive_ship_readiness_rc=0` in `EIDP-diagnose.bat`.
v341 keeps the v326 strict-mode fix for opaque WordPress Download
Manager wrappers, the v328 cross-school candidate rejection, the v329
actionable RCA counts, the v330 raw-control-character URL guard, and the v331
one-retry guard for transient registered-page timeouts plus structured
`discovery_error` evidence (`error_code`, `retryable`). It adds the v332
HAL東京/NKZ embed-subpage discovery demonstration and the v333 strict-year
correction: prefecture-index freshness is source/crawl evidence only and no
longer fills missing PDF/link fiscal-year evidence. v334 aligns the discovery
gold-set with that strict-year correction by reclassifying two former
prefecture-index-only auto successes as operator-review candidates. v335
tightens Codex/manual RCA outcome validation so `needs_operator_review` must
name a concrete candidate PDF and target-form evidence. v336 adds a real
Saitama CMCC RCA demonstration for a readable target-form PDF that still lacks
PDF/link FY2026 evidence. v337 adds a paired 埼玉自動車大学校 demonstration
that prevents incidental `令和8` committee-term text from becoming target-FY
evidence. v338 adds a Central Information College demonstration showing that
page update dates and officer-term dates are not target-FY evidence. v339 fixes
the ship/operator-reviewable metric so `target_year_unverified` rows (年度未確認候補)
are counted together with `publication_lag` rows instead of disappearing from
bootstrap, weekly, ship-readiness, and Windows validator calculations. Windows
setup, SQLite initialization, diagnostics, and a bounded 50-site Saitama
bootstrap have been rerun through v342 and confirm the metric fix: the current
sample now reports `operator_reviewable_count=46` from `publication_lag=38`
plus `target_year_unverified=8`. The product goal is
still not complete: browser UI read-only quick navigation now renders, but
operator-action click-through is missing, and the measured
operator-reviewable coverage / Excel readiness remain far below the shipping
line. v340 adds a demonstration-backed ARS/アルスコンピュータ publication-lag
case: current-year R8 PDFs on that page are syllabus/course-plan PDFs, while
the latest target confirmation form remains R7. This improves discovery
reproducibility. Windows v340 setup and bounded 50-site Saitama bootstrap have
been rerun and preserve the same status counts while moving the ARS R8 syllabus
PDFs into pre-download rejection evidence. v341 fixes a demonstrated Kanto
disclosure-card context leak: a visible `様式第2号` link was previously polluted
by the previous card's `事業報告書` / `財務諸表` / `役員名簿` text and ranked below
generic links. The v341 Windows package now ranks that target-form candidate
first, while strict download still routes it to review as
`image_only` / `fiscal_year_mismatch:2024`. v342 preserves demonstrated evidence
contexts that were still weak after v341: WordPress Download Manager package
titles such as 入間看護専門学校 `様式２（R6年度分申請）` now flow into the
candidate context, and image-only old-year `j2024_05a` / `様式第2号` evidence is
treated as operator-reviewable rather than dropped as generic non-target noise.
The v342 Windows bounded bootstrap confirms both fixes in packaged runtime:
current Saitama evidence evaluates as `16` exact gold-set predictions with
`0` failures, while the bootstrap remains correctly below ship gate because no
current-FY target PDFs were downloaded in the bounded 50-site sample. A separate
Tokyo official-index probe on the same v342 Windows package confirms the same
failure mode at a different prefecture boundary: the Tokyo official artifact
matched `232` school URLs and a 30-site PDF discovery sample found candidates on
all `30` sites, but still downloaded `0` strict current-FY target PDFs. v343
packages those Tokyo observations as three new source-side discovery gold-set
entries, raising the packaged gold-set from `28` to `31` entries. v344 keeps the
same discovery evidence package and removes the remaining Excel preview
confidence-threshold label drift by reading the same centralized thresholds as
the workbook exporter. v345 tightens the Tokyo gold-set regression contract by
requiring the actual observed candidate `pattern_type` for those entries
(`direct` or `wordpress`), so future replays cannot silently change the source
classification while preserving the same PDF URL. v347 moves the six
synthetic-only extractor sources (`data_attribute`, `form_action`,
`input_control`, `meta_refresh`, `onclick`, `select_option`) behind the
explicit `EIDP_PDF_DISCOVERY_EXPERIMENTAL_EXTRACTORS` flag, so the default
release surface only includes production-tracked sources that have gold-set
demonstrations. v348 adds a package verifier token gate for that default-off
experimental extractor setting, preventing future package builds from silently
turning those synthetic-only patterns back on. v349 packages the source-side
Tokyo Sanko publication-lag regression from the v348 Tokyo 20-site strict smoke,
raising the packaged discovery gold-set to `32` entries while keeping strict
target-PDF auto-success unchanged at `4`. v350 rebuilds the same runtime/data
package after the seed-count test contract update and remains clean under the
broadened rolling-FY package verifier guard. v351 rebuilds the package after
keeping the Windows validator/distribution verifier typing gate clean; runtime
discovery data is unchanged from v350. v352 packages the source-side `db-info`
readiness guard so an uninitialized SQLite file exits cleanly with `rc=2`
instead of printing a Python traceback; runtime discovery data is unchanged
from v351. v353 adds a manual-web demonstrated 聖十字看護専門学校 pattern where a
修学支援 section states `令和8年度より` target-school status immediately before a
確認申請書様式 第2号 PDF link. The default crawler now preserves that nearby
support-year context and downloads the target PDF in strict mode. The packaged
discovery gold-set rises to `33` entries and `5` strict target-year successes.
v354 adds a second manual-web accepted target case for 更生看護専門学校. Its news
definition list puts the `令和8年4月から修学支援新制度` evidence in the preceding
`dd` block and the actual PDF link in the next `dd`. The crawler now keeps that
definition-list context local, accepts April support-system start-month evidence
only when paired with target-form context, and avoids page-wide news archive
pollution. The packaged discovery gold-set rises to `34` entries and `6` strict
target-year successes.
v355 adds a manual-web demonstrated 専門学校中央情報大学校 case where the
information page lists multiple 修学支援制度 confirmation-form PDFs by fiscal
year. The existing crawler correctly chooses the `令和８年度` link over older
令和７年度/令和６年度 forms and downloads the WordPress-hosted target PDF. The
packaged discovery gold-set rises to `35` entries and `7` strict target-year
successes.
v356 adds a manual-web demonstrated 君津中央病院附属看護学校 case where a stale
empty anchor appears immediately before the visible `令和８年度` target-form
anchor. The crawler now keeps visible sibling anchor text local to the visible
anchor instead of assigning it to the empty stale PDF link. The replay now
downloads the correct `2026sinseisyo.pdf` target form. The packaged discovery
gold-set rises to `36` entries and `8` strict target-year successes.
v357 tightens HTML extraction accuracy for current Tokyo Anime public-info
pages: PDF links inside HTML comments are no longer treated as visible
publication candidates. The current page keeps an old
`07_study_support_application.pdf` link inside a comment while exposing visible
`11_confirmation_application.pdf` / `12_kakunin.pdf` links. v357 ignores the
commented stale link without changing the discovery gold-set count, preserving
historical v342 evidence replay compatibility.
v358 separates the operator-review ship gate from strict data diagnostics, and
current HEAD keeps that split while tightening the strict-data line:
`report ship-readiness --fail-on-missing-goal` gates on operator-reviewable
coverage / estimated manual workload for RC diagnostics, while `ok_strict`
requires both `strict_target_pdf` and `excel_ready` to meet the configured
strict threshold. This keeps the May publication-lag period from being blocked
by the long-term strict data metric while preserving the strict readiness signal
for later release decisions.
v359 starts the `cli.py` size-debt cleanup by moving the report subcommand tree
to `src/eidp/cli_reports.py`. The external CLI remains unchanged
(`eidp report coverage|extraction|gaps|ship-readiness`), the package verifier
now requires the new module, and `cli.py` drops from `1713` lines to `1405`.
v360 continues that cleanup by moving read-only discovery gold-set and RCA
commands to `src/eidp/cli_discovery.py`; the DB-writing
`seed-discovery-gold-sites` command stays in `cli.py` so the existing write-lock
AST gate still covers it. `cli.py` now sits at `997` lines, still above the
`800`-line target but materially reduced from the v358 baseline.
v361 finishes the current `cli.py` size-debt pass by moving read-only/tool
commands (`verify-identity`, `db-info`, `review-ui`, `operator-ui`,
`export-excel`, `export-competition-excel`, `diff-excel`, and `eval-pdf`) to
`src/eidp/cli_tools.py`. DB-writing commands remain in `cli.py` under the
write-lock AST gate. `cli.py` now sits at `753` lines, below the `800`-line
target, and the package verifier requires the new module.
v362 hardens the discovery demonstration baseline: `load_discovery_gold_entries`
now validates each committed entry against `data/discovery-gold-set/schema.json`
before constructing `DiscoveryGoldEntry` objects. The schema now rejects
unknown fields, includes the existing `windows_v320_jsonl` source kind, and the
Windows package verifier requires both the schema-validation code path and the
runtime `jsonschema` dependency. A new retroactive fiscal-year validation
runbook documents how FY2025/R7 can be used for Stage 6 rehearsal and rolling-FY
proof without counting it as FY2026/R8 yield.
v363 marks retroactive fiscal-year readiness reports explicitly. `eidp report
ship-readiness --fy 2025 --json` now emits `configured_target_fiscal_year`,
`calendar_current_fiscal_year`, `is_configured_target_fiscal_year`, and
`is_retroactive_fiscal_year`, and the text output labels retroactive runs as
retroactive validation evidence. This makes R7/FY2025 experiments safe for
pipeline and operator-flow proof while preventing those numbers from being
misreported as R8/FY2026 current-year ship yield.
v364 adds the same rolling-year proof to packaged Windows diagnostics:
`scripts\diagnose.bat` now computes the configured target FY minus one and
runs `eidp report ship-readiness --fy <previous> --json` into the diagnostics
log, recording `retroactive_fiscal_year` and `retroactive_ship_readiness_rc`.
The package verifier now rejects a ZIP whose diagnostics script omits that
retroactive FY snapshot.
v365 carries the retroactive-FY proof through to the packaged Stage 6 evidence
template. `docs/runbooks/eidp-operator-e2e-template.md` now asks the operator
to record `retroactive_fiscal_year`, `is_retroactive_fiscal_year`, and
`retroactive_ship_readiness_rc`, and the package verifier rejects ZIPs whose
template omits those fields.
v366 adds a manual-web / official-index-linked accepted target case for
愛北看護専門学校. The Aichi official-index artifact already links to the school's
support-system news page; that page states the school is a support target from
`令和8年度` and links a `確認申請書様式第2号` PDF whose filename remains
`youshiki2-r7.pdf`. This records the important production pattern where target
FY evidence is supplied by the school page context rather than by the PDF
filename. The packaged discovery gold-set rises to `37` entries and `9` strict
target-year successes, with `wordpress` pattern coverage rising to `5`.
v367 adds a manual-web / official-index-linked publication-lag case for
岩手医科大学医療専門学校. The Iwate official-index artifact links to a dense Wix
information page whose target confirmation-form section exposes links only
through `令和７年度`, while a later non-target syllabus section already contains
`令和8年度` text. The gold-set now records this as latest-public target-form
evidence that must stay visible to the operator without being counted as strict
FY2026 success. Packaged coverage rises to `38` entries and `12`
publication-lag cases, with `direct` pattern coverage rising to `6`.
v368 rebuilds the clean v367 state after the documentation update and refreshes
the operator-facing latest alias. `dist/eidp-windows-v368.zip` and
`dist/eidp-windows.zip` now have the same SHA256
`833d500360456b4b827583d0927480173d20e41700d7db88675691aa084645ad`, so the
versioned package and the default runbook package refer to the same contents.
v369 adds a manual-web / official-index-linked accepted target case for
専門学校浜松工科自動車大学校. The Shizuoka official-index artifact links to
`https://kohka-h.ac.jp/disclose`, whose WordPress disclosure page labels the
target PDF as `令和８年度 様式第２号`. The PDF body contains
`専門学校浜松工科自動車大学校`, `様式第２号`, and `修学支援`, but does not repeat
`令和8年度`; this records the production pattern where local anchor text supplies
the target-FY evidence while same-block generic documents such as 学校情報 /
学生便覧 / 組織図 / 役員名簿 must not outrank the target form. Packaged
discovery gold-set coverage rises to `39` entries, `10` strict target-year
successes, and `wordpress=6`.
v370 adds a manual-web / official-index-linked publication-lag case for
長野県公衆衛生専門学校. The Nagano official-index artifact links directly to a
prefecture-hosted support-system page. That page was updated in 2025 and lists
`令和７年度` / `令和６年度` target-form PDFs, but no `令和８年度` target-form
section. The linked `2025shinseisho2go.pdf` body contains
`長野県公衆衛生専門学校`, `様式第２号`, and `修学支援`, but does not contain
`令和8年度`; this preserves the public-school pattern where the latest public
target-form PDF must remain operator-reviewable publication-lag evidence rather
than strict FY2026 success. Packaged discovery gold-set coverage rises to `40`
entries, `13` publication-lag cases, and `direct=7`; strict target-year
successes remain `10`.
v371 preserves preceding fiscal-year heading context for paragraph and
definition-list PDF links. For Nagano-style public-school pages, a preceding
`<h3>令和７年度</h3>` now travels with the following `申請書 様式第２号` PDF link,
while the page-level update date remains excluded. The stale-year evidence is
therefore recognized as FY2025 publication-lag context and does not become
strict FY2026 success. Packaged discovery gold-set coverage remains `40`
entries, `10` strict target-year successes, `13` publication-lag cases, and
`undemonstrated_pattern_sources=[]`.
v372 adds a manual-web / official-index-linked publication-lag case for
愛生会看護専門学校. The Aichi official-index artifact links to the school's
support page, which lists `令和6年9月公表` and `令和7年9月公表` target-form
sections but no `令和8年度` target-form PDF. The latest
`support_system_2025.pdf` body contains `愛生会看護専門学校` and `様式第２号`,
while the adjacent `subject_2025.pdf` is a subject-list PDF and must not become
the target confirmation form. Packaged discovery gold-set coverage rises to
`41` entries, `14` publication-lag cases, and `direct=8`; strict target-year
successes remain `10`.
v373 adds a manual-web / official-index-linked publication-lag case for
あいち福祉医療専門学校. The Aichi official-index artifact links to a public
documents page whose `2026年度` section exposes syllabus and curriculum-map PDFs,
but no current-year target confirmation-form PDF. The latest target form remains
`2025_kakuninshinsei.pdf` under the `2025年度` section. This records the
production pattern where current-year syllabus PDFs must not outrank or replace
the latest previous-year target confirmation form. Packaged discovery gold-set
coverage rises to `42` entries, `15` publication-lag cases, and `direct=9`;
strict target-year successes remain `10`.
v374 turns that Aichi production pattern into a code-level candidate-ordering
regression guard. A page with current-year syllabus/curriculum PDFs ahead of a
previous-year target confirmation-form PDF must still rank the target form
(`2025_kakuninshinsei.pdf`) first for operator-reviewable publication-lag
handling. Packaged discovery gold-set coverage remains `42` entries, `15`
publication-lag cases, `direct=9`, and `10` strict target-year successes.
v375 closes the remaining fiscal-year-context edge introduced by the v371
heading-context repair: strong fiscal-year headings now require an explicit
fiscal-year label, weak update/publication dates no longer suppress heading
fallback, and preceding heading context is not carried across an intervening
non-year block. It also adds a manual-web / official-index-linked
尚美ミュージックカレッジ専門学校 case where the public-info page lists historical
R1-R7 support forms and the crawler must keep the latest public R7 target form
visible for FY2026 publication-lag handling. Packaged discovery gold-set
coverage rises to `43` entries, `16` publication-lag cases, `direct=10`, and
`10` strict target-year successes.
v376 preserves the v375 discovery code and package contents while fixing the
Windows diagnostics capture for retroactive FY validation. It was extracted to
`C:\Users\<operator>\EIDP-v376-d2402dc`, `EIDP-setup.bat` completed, standalone
after-setup validation returned `ok=true`, and `EIDP-diagnose.bat` wrote
`logs\diagnostics-20260513-211539.txt` with `school_count=2418`,
`sqlite_integrity_check=ok`, `ship_readiness_rc=1` for FY2026, and a successful
FY2025 retroactive section with `is_retroactive_fiscal_year=true`,
`extracted_schools=2031`, `extracted_rate=0.84`, and
`retroactive_ship_readiness_rc=0`. A separate Windows service-level UI smoke
started Streamlit headless from the v376 virtualenv on `127.0.0.1:8501`,
received `200 ok` from `/_stcore/health`, and then stopped the smoke process
without leaving a Streamlit process behind. This proves app server startup, not
operator browser click-through.

Post-v376 source-branch note: commit `e65021e` adds the manual-web / official-
index-linked 中央動物専門学校 publication-lag case. Commits `044d188`,
`4b872b0`, and `82570d9` then add safe data-migration guidance plus package
verifier gates that reject mutable runtime data and stale runbook guidance.
The current source checkout therefore reports `44` discovery gold-set entries,
`10` strict target-year successes, `17` publication-lag cases, `15`
operator-review entries, and `undemonstrated_pattern_sources=[]`, while also
enforcing a stricter ZIP hygiene contract. That source/package evidence is now
packaged in `dist/eidp-windows-v384.zip`; v381 proved the Windows runtime can
detect free RAM without `psutil`, v382 adds a packaged `--require-ocr-runtime`
gate that executes Tesseract runtime probes when an OCR add-on is present, and
v383 adds the Tesseract `configs/tsv` file required by the wrapper's TSV
parsing path. A disposable operator-PC v382 extraction without the add-on
correctly failed that gate on missing `ocr-addon` files. A disposable
operator-PC v383 extraction with the smoke add-on first proved image OCR plus a
copied-DB DepartmentYearly write via `extraction_method="ocr_tesseract"`.
The same OCR image/write path has now been repeated on v384 with core SHA256
`2707def6337f3f35c63c9933a1805271dcf75d8bf7d8ece27c09ba8de72d31c0`, returning
`ocr_full_text="V384 OCR WRITE SMOKE 2026"`, `ocr_avg_confidence=0.95`, one
copied-DB `DepartmentYearly` row, three `manual_entry` audit rows, and zero
matching real-runtime marker rows. Post-v383 source adds code-level
coverage that image-PDF ingest uses the Tesseract TSV wrapper and stores
`ocr_tesseract` confidence breakdowns on both `DepartmentYearly` and
`SupportRecipient` rows. The latest operator-PC transfer/setup/UI-health,
R7 browser Excel, and seeded browser-write evidence is now v408: the current
package rendered the
operator UI, saved `PDF確認・手入力`, applied `③ 年度判定・修正`, generated
`Excel プレビュー` in the R7 browser proof, opened `監査ログ`, and flushed the
audit outbox in a disposable sandbox. v397 remains the historical read-only quick-navigation
proof across the full sidebar, including non-mutating quick navigation clicks
and the FY2026 Excel workbook-generation disabled state for empty current data.
v384 remains supporting evidence for package-local `eidp db-backup`, Windows
environment / Task Scheduler capture, URL-candidate reject, additional
audit-outbox browser flush, additional fiscal-year override, SupportRecipient
package ingest, and additional manual-entry browser save proof on disposable
copied databases. v384 also has a sandboxed 5-site Saitama backend bootstrap
smoke that exercises official artifact download,
official-index SchoolSite writes, strict PDF discovery, ingest, and status
rebuild without mutating the real runtime DB.
Stage 6 operator workflow evidence still remains incomplete, as listed below.

## Objective Checklist

Note: this checklist keeps older v384/v397/v399/v401 evidence in historical
context where it still proves a specific workflow. For current package state,
v456 supersedes older ZIPs for core package verification, Windows setup,
scheduled-task recovery, UI-health, R7 browser Excel download, and
URL-candidate/audit-outbox UI write sandbox proof. v408/v384 remain historical
support for broader manual-entry and fiscal-year-override UI write paths. v407
remains supporting evidence for the diagnostic evidence bundle and historical
seeded UI write/Excel-preview sandbox. Full operator-action click-through
remains unverified.

| Requirement | Current evidence | Status |
| --- | --- | --- |
| 47 prefecture official indexes seed school public URLs | v342 verifier: `prefecture_seed_rows=47`, `prefecture_seed_parser_supported=47`, `prefecture_seed_downloadable=47`, `prefecture_seed_school_rows_total=2148`; Windows v384 sandboxed Saitama 5-site backend smoke downloaded the current official artifact (`saitama.pdf` plus `.url` sidecar), added `51` `SchoolSite` rows with `prefecture_aggregator`, and left the real runtime DB at `0` `SchoolSite` marker rows; Windows v342 broader Saitama run also downloaded the official artifact and added `51` `SchoolSite` rows from `58` extracted / `51` matched rows | Evidence present |
| Discover and download current target-FY PDFs in strict mode | v380 package verifier clean by default; packaged discovery gold-set `44` entries / `10` strict target-year successes / `17` publication-lag cases; v384 sandboxed Saitama 5-site backend smoke crawled `5`, downloaded `0` strict FY2026 target PDFs, produced `2084` discovery evidence lines, processed `0` PDFs, rebuilt `2418` status rows, and reported `operator_reviewable_count=5`, `operator_reviewable_yield_pct=0.2`, `target_pdf_auto_yield_pct=0.0`, `excel_ready=0`, `ship_gate_status=below_gate`, one RCA batch file with `5` items / `5` total candidates, and real runtime counts `school_site=0`, `review_item=0`, `document=0`, `status_rows=2418`; isolated Mac-side live strict-discovery sample against 44 seeded gold-set sites crawled 10 selected schools, found 10 candidate sets, downloaded 0 strict FY2026 target PDFs, failed 1 site, skipped 185 links, and after the RCA triage fix classified the scoped site set as `publication_lag_or_old_target_pdf=6`, `target_form_without_year_evidence=3`, `non_target_candidates_only=1`, `no_evidence=34`; the same isolated DB rebuilt ship readiness as `operator_reviewable_schools=9/44`, `operator_reviewable_rate=0.2045`, `strict_target_pdf_rate=0.0`, `excel_ready_schools=0`, `ok_operator_review=false`; a follow-up isolated central-animal run after source HEAD fixes preserved `https://www.chuo-a.ac.jp/disclosure/` as the seed URL, crawled `1`, found `1`, downloaded `0`, failed `0`, put `confirmation_2.pdf` first with anchor `2025年度 高等教育の修学支援新制度 申請書様式第2号`, and recorded it as `fiscal_year_mismatch:2025` / `pdf_type=target`; the scoped summary reports `publication_lag_or_old_target_pdf=1` instead of `non_target_candidates_only`; source HEAD prioritizes explicit `target_fiscal_year_not_detected` target-form evidence over older-year target evidence during RCA triage; v375 fixes the heading/update-date fiscal-year context edge and adds a 尚美 historical-support-form ordering case where the latest public R7 target form stays visible for FY2026 publication-lag handling; v374 adds a code-level guard that current-year syllabus/curriculum PDFs do not outrank the previous-year target confirmation form in Aichi-style publication-lag pages; source-side 聖十字 replay crawled `1`, found `1`, downloaded `1`, and gold-set evidence replay matched the accepted target PDF exactly; source-side 更生 replay crawled `1`, found `1`, downloaded `1`, and gold-set evidence replay matched the accepted target PDF exactly; source-side 中央情報 replay crawled `1`, found `1`, downloaded `1`, and gold-set evidence replay matched the accepted target PDF exactly; source-side 君津 replay crawled `1`, found `1`, downloaded `1`, and gold-set evidence replay matched the accepted target PDF exactly; manual-web / official-index-linked 愛北 evidence records a support-system news page with `令和8年度` context linking `youshiki2-r7.pdf` as the target confirmation form; manual-web / official-index-linked 愛生会 evidence records a support page where the latest target-form PDF is still `令和7年9月公表` and the adjacent subject-list PDF must not be treated as the target form; manual-web / official-index-linked あいち福祉医療 evidence records a public-documents page where the `2026年度` section contains syllabus PDFs but the latest target-form PDF remains `2025年度`; manual-web / official-index-linked 尚美 evidence records a public-info page where the historical support-form list currently runs through R7/FY2025 and the latest target form must remain publication-lag evidence; manual-web / official-index-linked 中央動物 evidence records a disclosure page where R8 non-target operation-plan / professional-practice PDFs coexist with a support-system `申請書様式第2号` link still labeled `2025年度`; manual-web / official-index-linked 浜松工科 evidence records an official Shizuoka index route to a WordPress disclosure page whose `令和８年度 様式第２号` anchor supplies target-FY evidence for a PDF body that contains the school name, `様式第２号`, and `修学支援` but not the fiscal-year string; manual-web / official-index-linked 長野県公衆衛生 evidence records a prefecture-hosted support page whose latest public target-form PDF is still under the `令和７年度` section and must remain publication-lag evidence; v375 additionally preserves preceding heading-year context without crossing intervening non-year blocks or treating update dates as fiscal-year evidence; manual-web / official-index-linked 岩手医科大学医療専門学校 evidence records a dense Wix page where the target confirmation-form section is still `令和７年度` even though a later syllabus section has `令和8年度`; current Tokyo Anime HTML probe ignores the commented-out old `07_study_support_application.pdf` link while keeping visible confirmation-form links; Windows v342 Saitama 50-site run crawled `50` official-index sites, found candidates on `49`, downloaded `0`, processed `0`, and produced `0` Excel-ready schools after removing false-positive prefecture-index year fill; Windows v342 Tokyo 30-site probe found candidates on all `30` sites and downloaded `0`; a source-side v348 Tokyo 20-site repeat crawled `20`, found candidates on all `20`, downloaded `0`, and reproduced the same publication-lag / stale-year / no-year target-form distribution; Windows v342 evidence proves Kanto/Iruma context fixes without accepting old-year PDFs as current-FY success | Mechanically proven, strict yield still failing at workload scale |
| Exclude stale-year fallback from auto-success | Ship gate uses operator-reviewable coverage, while strict auto-yield remains diagnostic; v380 package gold-set includes `17` publication-lag cases; Windows v333/v339/v340 evidence records prior false-success or stale-year URLs as `target_fiscal_year_not_detected` / `fiscal_year_mismatch:*` instead of `accepted_downloaded`; malformed raw URLs are recorded as `unsafe_url` instead of aborting the batch | Evidence present |
| Extract with pdfplumber/PyMuPDF/Tesseract and write only confidence >= 0.70 rows | Unit/package gates cover OCR runtime presence and confidence contracts; Windows v340 Saitama 50-site run produced no strict target PDFs, so no PDF-derived yearly rows were written; this avoids v332's false-positive `18` current rows. v383 adds package-verifier enforcement for the OCR add-on TSV config and a disposable operator-PC image smoke. v384 repeats the OCR image/write proof on the latest core package: Tesseract returned `ocr_full_text="V384 OCR WRITE SMOKE 2026"` with `ocr_conf_values=[93,94,96,96,96]` and `ocr_avg_confidence=0.95`; `save_manual_entries` wrote one copied-DB `DepartmentYearly` row with `extraction_method="ocr_tesseract"`, `extraction_confidence=0.95`, and `verified=true`, promoted the document to `ingested`, emitted three `manual_entry` audit rows, and left the real runtime DB with `0` matching marker rows. Post-v383 source coverage proves image-PDF ingest uses the Tesseract TSV wrapper and records `ocr_tesseract` confidence breakdowns on both `DepartmentYearly` and `SupportRecipient` rows when OCR TSV confidence is present | Mechanically proven for OCR runtime/TSV parsing and copied-DB DepartmentYearly write on v384, plus code-level SupportRecipient OCR confidence propagation; no current strict target-form OCR data |
| Append-only DepartmentYearly / SupportRecipient writes | Fresh full unit suite passed; source audits and targeted tests cover demote-plus-new-revision paths in ingest, manual entry, and fiscal-year override; Windows v384 `PDF確認・手入力` browser save smoke inserted one manual `DepartmentYearly` revision with `document_id=1`, `fiscal_year=2026`, `revision=1`, `is_current=1`, `extraction_method="manual"`, `extraction_confidence=1`, and `verified=1` in a disposable copied DB, promoted the document from `parse_failed` to `ingested`, emitted three `manual_entry` audit rows, and verified the real runtime DB had `0` matching document/department/yearly/audit rows. The same smoke confirmed this UI path does not write SupportRecipient rows (`support_recipient_rows_for_doc=0`). Windows v384 `③ 年度判定・修正` browser write smoke moved one seeded FY2025 ingested document to FY2026, demoted the FY2025 current `DepartmentYearly`, `SupportRecipient`, and `SchoolYearStatus` rows plus the pre-existing FY2026 target `DepartmentYearly` row, inserted new FY2026 current `DepartmentYearly`, `SupportRecipient`, and `SchoolYearStatus` rows, set `Document.fiscal_year=2026` and `fiscal_year_override=2026`, emitted four `fiscal_year_override` audit rows, and verified the real runtime DB had `0` matching document/school/department/audit rows. Windows v384 package-local backend ingest smoke then seeded two FY2026 target documents in a copied DB, monkeypatched the package parser boundary to return deterministic SupportRecipient annotations, called `ingest_document` twice, and verified two SupportRecipient rows: revision `1` demoted to `is_current=false` with `annual_total=100`, `grand_total=100`, and `extraction_confidence=0.94`; revision `2` current with `annual_total=120`, `grand_total=120`, and `extraction_confidence=1.0`; the real runtime DB had `0` matching documents, schools, and support-recipient rows. The v408 operator-PC disposable UI sandbox repeated the critical browser-write surface on the current package: `PDF確認・手入力` saved one manual FY2025 `DepartmentYearly` row with `capacity=40`, `enrollment=28`, `extraction_method=manual`, `extraction_confidence=1.0`, and `verified=true`, while `年度判定・修正` cloned current FY2025 rows for `DepartmentYearly`, `SupportRecipient`, and `SchoolYearStatus` from seeded FY2024 rows and marked the FY2024 rows `is_current=false`. v407 remains historical support for the same UI path. | DepartmentYearly Win UI E2E proven on v384, v407 sandbox, and v408 sandbox; fiscal-year override Win UI E2E proven on v384, v407 sandbox, and v408 sandbox; SupportRecipient append-only proven on v384 backend and v408 sandbox override |
| Excel template output | v384 FY2026 Excel preview correctly keeps workbook generation disabled when current-year transcribed rows are `0`; v384 retroactive FY2025/R7 browser smoke generated the in-memory workbook and downloaded `eidp_master.xlsx` with size `3,728,651` bytes after showing `抽出済み学校 2031` and `Excel対象行 7150`; the downloaded workbook opened with sheets `採録状況`, `対象比率`, `学科別`, and `在籍のみ抜粋`, and `openpyxl` reported row counts `2419`, `10023`, `9721`, and `9721` including headers; v342 package verifier also includes Excel/export contracts and centralized confidence threshold contract. Historical v408 Windows R7/FY2025 CLI export wrote `v408-r7-retroactive-export.xlsx` with `採録状況=2418`, `対象比率=10022`, `学科別=9719`, and `在籍のみ抜粋=9719`; `diff-excel --business-values --original` against the proven v407 export returned `missing_sheets=0`, `extra_sheets=0`, `missing_rows=0`, `extra_rows=0`, and `differing_fields=0`; `openpyxl` opened the v408 CLI workbook at `3,673,084` bytes with sheets `採録状況`, `対象比率`, `学科別`, `在籍のみ抜粋` and row/column counts `2419x10`, `10023x22`, `9721x83`, `9721x19`. Historical v408 also proved the R7 browser preview/download path on the real install with process-local `EIDP_TARGET_FISCAL_YEAR=2025`: the UI showed `抽出済み学校 2031`, `Excel対象行 7150`, sheet counts `採録状況=2418`, `対象比率=10022`, `学科別=9719`, and `在籍のみ抜粋=9719`; Playwright downloaded `_temp/v408-r7-browser-eidp_master.xlsx`, `openpyxl` opened `3,673,083` bytes with the same four sheet dimensions, and `diff-excel --business-values` against `_temp/v408-r7-cli-export.xlsx` returned `missing_sheets=0`, `extra_sheets=0`, `missing_rows=0`, `extra_rows=0`, and `differing_fields=0`. The v407 disposable UI sandbox also generated a small browser Excel preview workbook with sheet counts `採録状況=2`, `対象比率=1`, `学科別=2`, and `在籍のみ抜粋=2`. | R7 retroactive CLI export/diff and browser download proven on v408; FY2026 production output still pending |
| ManualActionLog audit for operator actions | v384 sandboxed URL-candidate reject browser write smoke created one `url_candidate_rejected` audit row in a disposable copied database, resolved the `ReviewItem` as rejected, created no `SchoolSite` row, and verified the real runtime DB was not mutated; v384 sandboxed audit-outbox browser flush smoke exported one seeded `stage6_v384_ui_audit_flush_smoke` row to JSONL, stamped `jsonl_exported_at`, cleared pending count to `0`, and verified the real runtime DB was not mutated; v384 `PDF確認・手入力` browser save smoke emitted three `manual_entry` audit rows for `department`, `department_yearly`, and `document`; v384 `③ 年度判定・修正` browser write smoke emitted four `fiscal_year_override` audit rows for `department_yearly`, `support_recipient`, `school_year_status`, and `document`; v342 package verifier also includes audit contracts and outbox checks. v408 disposable UI sandbox emitted seven browser-driven operator actions: three `manual_entry` rows and four `fiscal_year_override` rows; `監査ログ` showed `JSONL outbox 未送信=7`, `Outbox を flush` returned `exported=7 already_present=0 failed=0`, and post-click SQLite verification found all seven rows with `jsonl_exported_at_present=true`. v407 remains historical support for the same surface. v459 disposable UI write/audit sandbox rejected one seeded URL candidate and flushed two audit rows with `exported=2`, `pending_outbox=0`, matching JSONL action IDs, and real runtime DB marker counts `0`. | Browser operator-action audit proven for URL-candidate, audit flush, manual-entry, and fiscal-year override paths; v459 sandbox proves current URL-candidate reject/audit-outbox flush; v408 sandbox proves manual-entry/fiscal-override outbox flush |
| ZIP distribution, double-click setup, browser UI offline operation | Historical v408 core/setup/UI-health/R7-browser-Excel/UI-write package: `dist/eidp-windows-v408.zip` was built from source commit `f0c2715833b54e60fea85259e16ad0a1d9e6c106`, Mac-verified with SHA256 `61fe233e41c08b8684560778b25c36f12ad0848135e8930ef07d8fa265fbbbe2`, transferred to Windows, SHA-checked, extracted to `C:\Users\<operator>\EIDP-v408-f0c27158`, set up with `EIDP-setup.bat`, validated with `ok=true`, `school_count=2418`, `school_fiscal_year_status_count=2418`, `sqlite_integrity_check=ok`, `sqlite_table_count=15`, and `wheel_count=78`, updated the scheduled task to `C:\Users\<operator>\EIDP-v408-f0c27158\scripts\weekly_run.bat`, served Streamlit with Windows-local health `ok` plus Mac tunnel `127.0.0.1:18508 -> Windows 127.0.0.1:8508` health `ok` and root HTML retrieval, served the R7 browser Excel generation/download proof through `127.0.0.1:18509 -> Windows 127.0.0.1:8509`, and served the copied-DB UI write/audit sandbox through `127.0.0.1:18510 -> Windows 127.0.0.1:8510`. The first v407 evidence bundle with Excel export was verifier-rejected as intended; the refreshed non-Excel dry-run bundle `logs\stage6-evidence-20260514-174859.zip` verified with `ok=true` and labels `build_info`, `diagnostics`, `last_run`, `stage6_recovery`, `stage6_residual_cleanup`, and `weekly_run_logs`, and carries both the historical R7 browser Excel proof and seeded UI write proof without bundling Excel or runtime data. It remains diagnostic because `last_run` was `dry_run=true`, `ship_gate_status=not_measured`, and no yield was measured. Historical v407 additionally has a seeded disposable browser-write sandbox on the operator PC, v397 remains a browser-click read-only navigation proof, and v384 remains supporting evidence for additional disposable copied-DB UI write paths. | v408 package/setup/recovery/UI-health, R7 browser Excel proof, and sandbox browser-write/audit proof present; v407 diagnostic evidence-bundle retained as supporting evidence; real full-cycle operator workflow still missing |
| Shipping threshold: operator-reviewable coverage sufficient for operator manual work <=30%, with strict target-PDF and Excel readiness retained as GA diagnostics | `ship-readiness` reports `ok_operator_review` separately from `ok_strict`; current HEAD requires `ok_strict` to pass both `strict_target_pdf` and `excel_ready` criteria. Windows v459 bounded diagnostics report `target_pdf_auto_yield_pct=40.0`, `operator_reviewable_yield_pct=100.0`, and `ship_gate_status=pass` on the 5-school R7 canary, but this remains below the final 60-70% strict target-PDF gate and is not a production R8 measurement | Failing final strict GA gate; RC/operator-review evidence only |

## Current Non-Windows Evidence

Runbooks: `docs/runbooks/eidp-non-windows-release-gates.md`;
`docs/runbooks/eidp-retroactive-fy-validation.md`.

Historical v408 package/setup/recovery/UI-health commands:

- `uv run python scripts/build_windows_zip.py --skip-download --out-zip dist/eidp-windows-v408.zip --latest-alias`
  -> wrote `dist/eidp-windows-v408.zip`, refreshed `dist/eidp-windows.zip`,
  and wrote `dist/eidp-windows-v408.zip.sha256`.
- `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v408.zip --json`
  -> `ok=true`, commit `f0c2715833b54e60fea85259e16ad0a1d9e6c106`,
  SHA256 `61fe233e41c08b8684560778b25c36f12ad0848135e8930ef07d8fa265fbbbe2`,
  `git_dirty=false`, `wheel_count=78`, `project_wheel_count=1`,
  `prefecture_seed_rows=47`, `prefecture_seed_downloadable=47`,
  `discovery_gold_set_entries=44`, and
  `undemonstrated_pattern_sources=[]`.
- Windows v408 SHA/extract/recovery smoke:
  sidecar SHA matched on Windows, `BUILD_INFO.json` reported commit
  `f0c2715833b54e60fea85259e16ad0a1d9e6c106`, and the packaged
  `stage6_recovery_check.py` returned `task.exists=true`, `task.error=null`,
  and `action_matches_expected=true` for
  `C:\Users\<operator>\EIDP-v407-0974b60f\scripts\weekly_run.bat` before v408
  setup; overall `ok=false` remained because known v384 residual smoke
  artifacts still exist.
- Windows v408 setup and install validation:
  `EIDP-setup.bat` exited `0`, logged `OK install:
  C:\Users\<operator>\EIDP-v408-f0c27158`, and
  `validate_windows_install.py C:\Users\<operator>\EIDP-v408-f0c27158 --after-setup
  --json` returned `ok=true`, `errors=[]`, `warnings=[]`, `school_count=2418`,
  `school_fiscal_year_status_count=2418`, `sqlite_integrity_check=ok`,
  `sqlite_table_count=15`, and `wheel_count=78`.
- Windows v408 scheduled-task confirmation:
  after setup, the `EIDP Weekly Run` task execute path was
  `"C:\Users\<operator>\EIDP-v408-f0c27158\scripts\weekly_run.bat"`, and the
  packaged recovery checker returned `task.exists=true`, `task.error=null`, and
  `action_matches_expected=true` for that v408 weekly runner; overall
  `ok=false` remained only because known v384 residual smoke artifacts still
  exist.
- Windows v408 UI-health smoke:
  with launcher environment variables set, Streamlit started on Windows
  `127.0.0.1:8508`; Windows-local `/_stcore/health` returned `ok`; a Mac SSH
  tunnel `127.0.0.1:18508 -> 127.0.0.1:8508` returned `ok` for
  `/_stcore/health` and returned the Streamlit HTML shell at `/`. The test
  Streamlit process and tunnel were stopped afterward.
- Windows v408 default launcher smoke:
  `EIDP-start.bat` invoked packaged `scripts\launch.bat`, started Streamlit on
  default Windows port `8501`, and the default Mac tunnel `127.0.0.1:18501 ->
  127.0.0.1:8501` returned `/_stcore/health=ok` plus the Streamlit HTML shell at
  `/`. The foreground Streamlit process was force-stopped after the health proof,
  so the launcher printed exit `-1`; `18501` and `8501` had no listening process
  remaining afterward.
- Windows v408 R7 retroactive CLI Excel proof:
  with process-local `EIDP_TARGET_FISCAL_YEAR=2025`, `eidp export-excel`
  wrote `data\output\v408-r7-retroactive-export.xlsx` with
  `採録状況=2418`, `対象比率=10022`, `学科別=9719`, and
  `在籍のみ抜粋=9719`. `diff-excel --business-values --original
  C:\Users\<operator>\EIDP-v407-0974b60f\data\output\v407-r7-retroactive-export.xlsx
  data\output\v408-r7-retroactive-export.xlsx` returned `missing_sheets=0`,
  `extra_sheets=0`, `missing_rows=0`, `extra_rows=0`, and
  `differing_fields=0`. `openpyxl` opened the v408 workbook at `3,673,084`
  bytes with sheet dimensions `2419x10`, `10023x22`, `9721x83`, and `9721x19`.
  The default `diff-excel --business-values` reference path is still
  `sample\◆2025専門学校無償化情報公開まとめ.xlsx`, which is absent from the
  packaged ZIP; use explicit `--original data\master.xlsx` or a known-good
  export until that packaging/CLI default is corrected.
- Windows v408 R7 retroactive browser Excel proof:
  with process-local `EIDP_TARGET_FISCAL_YEAR=2025`, Streamlit started on
  Windows `127.0.0.1:8509`; a Mac SSH tunnel `127.0.0.1:18509 ->
  127.0.0.1:8509` returned `/_stcore/health=ok`; Playwright opened
  `Excel プレビュー`, observed `対象年度: 2025年度（令和7年度）`,
  `抽出済み学校 2031`, and `Excel対象行 7150`, clicked
  `プレビュー workbook を生成`, and observed sheet counts
  `採録状況=2418`, `対象比率=10022`, `学科別=9719`, and
  `在籍のみ抜粋=9719`. The download button suggested `eidp_master.xlsx` and was
  saved as `_temp/v408-r7-browser-eidp_master.xlsx`; `openpyxl` opened it at
  `3,673,083` bytes with dimensions `2419x10`, `10023x22`, `9721x83`, and
  `9721x19`. Comparing it to the copied Windows CLI export
  `_temp/v408-r7-cli-export.xlsx` with `diff-excel --business-values` returned
  `missing_sheets=0`, `extra_sheets=0`, `missing_rows=0`, `extra_rows=0`, and
  `differing_fields=0`. The Streamlit process and tunnel were stopped; `18509`
  had no listener and Windows `8509` had no listening process remaining.
- Windows v408 disposable UI write/audit sandbox proof:
  with process-local `EIDP_TARGET_FISCAL_YEAR=2025`, copied DB sandbox
  `C:\Users\<operator>\EIDP-v408-f0c27158-ui-sandbox-20260515-02`, Streamlit on
  Windows `127.0.0.1:8510`, and Mac tunnel `127.0.0.1:18510 ->
  127.0.0.1:8510`, Playwright saved one `PDF確認・手入力` manual entry and one
  `年度判定・修正` fiscal-year override. `監査ログ` showed `JSONL outbox 未送信=7`;
  clicking `Outbox を flush` returned `exported=7 already_present=0 failed=0`.
  Direct DB verification found all seven `ManualActionLog` rows with
  `jsonl_exported_at_present=true`, the manual FY2025 row written and verified,
  and the override rows cloned to FY2025 with FY2024 rows demoted. The proof log
  is
  `C:\Users\<operator>\EIDP-v408-f0c27158-ui-sandbox-20260515-02\logs\diagnostics-v408-ui-sandbox-proof-20260515-034848.json`.
  The Streamlit process and tunnel were stopped; `18510` had no listener and
  Windows `8510` had no listening process remaining.
- Windows v408 non-Excel diagnostic evidence bundle:
  process-local FY2025 dry-run weekly wrote `data\output\last_run.json` with
  `status=success`, `dry_run=true`, `selection_mode=target_missing`,
  `new_document_ids=[]`, `ship_gate_status=not_measured`, and null yield
  percentages because the denominator was `0`; the log was
  `logs\run-v408-retroactive-dryrun-20260515-040053.log`. The v408 packaged
  recovery check wrote `logs\stage6-recovery-20260515-040010.json` with
  `action_matches_expected=true` for
  `C:\Users\<operator>\EIDP-v408-f0c27158\scripts\weekly_run.bat`, while old v384
  residual artifacts kept overall `ok=false`. `scripts\stage6_residual_cleanup.bat
  --json` was dry-run only and wrote
  `logs\stage6-residual-cleanup-20260515-040034.json` with `existing_count=5`,
  `moved_count=0`, and `errors=[]`. `scripts\collect_stage6_evidence.bat`
  produced `logs\stage6-evidence-20260514-190257.zip`; packaged
  `scripts\verify_stage6_evidence.bat` wrote
  `logs\stage6-evidence-verify-20260515-040322.json` with `ok=true`,
  `entry_count=8`, `forbidden_entries=[]`, `unsafe_entries=[]`,
  `missing_required_labels=[]`, and present labels `build_info`, `diagnostics`,
  `last_run`, `stage6_recovery`, `stage6_residual_cleanup`, and
  `weekly_run_logs`. The manifest still lists missing `bootstrap_logs`,
  `bootstrap_progress`, and `discovery_rca`, so this remains diagnostic evidence.

Current v407 full release-gate/setup commands:

- `uv run python scripts/build_windows_zip.py --skip-download --out-zip dist/eidp-windows-v407.zip --latest-alias`
  -> wrote `dist/eidp-windows-v407.zip`, refreshed `dist/eidp-windows.zip`,
  and wrote `dist/eidp-windows-v407.zip.sha256`.
- `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v407.zip --json`
  -> `ok=true`, commit `0974b60fb3d404678828ddfa348c74f4dd740c79`,
  `git_dirty=false`, SHA256
  `af48ed37d65695c044b520da78aad5307ed89b4b4a38cf27c6dc7e2737f50940`,
  `entry_count=3078`, `wheel_count=78`, `prefecture_seed_rows=47`,
  `prefecture_seed_school_rows_total=2148`, `discovery_gold_set_entries=44`,
  and no warnings.
- `uv run python scripts/run_non_windows_release_gates.py dist/eidp-windows-v407.zip --json --output _temp/v407-non-windows-release-gates-full.json`
  -> `ok=true`, package/source commit matched, sidecar SHA matched, full unit
  tests reported `1480 passed`, validator/distribution unit tests reported
  `161 passed`, mypy/Ruff passed, and discovery-gold expected predictions were
  `44/44`.

Historical v401 package-verifier commands:

- `uv run python scripts/build_windows_zip.py --skip-download --out-zip dist/eidp-windows-v401.zip --latest-alias`
  -> wrote `dist/eidp-windows-v401.zip` and refreshed `dist/eidp-windows.zip`;
  both have SHA256
  `ff54f3a4c6a498ab9af89890e1ee614b31e57a87066277f1323f8f37d6f1bcf5`.
- `uv run python scripts/verify_windows_distribution.py --json dist/eidp-windows-v401.zip`
  -> `ok=true`, commit `2d9c9f690c6f955330ea49276ef1a87157ceb6cd`,
  `git_dirty=false`, `entry_count=3078`, `wheel_count=78`, `47` prefecture
  seeds, `44` discovery gold-set entries,
  `undemonstrated_pattern_sources=[]`, and no warnings.
- The current verifier intentionally rejects the older v399 ZIP because its
  packaged runbook predates the corrected tunnel troubleshooting guidance. The
  normal `EIDP-start.bat` path should use `18501 -> 8501`; only manually started
  `--server.port 8502` smokes should use `18502 -> 8502`.

Current v407 Windows setup and UI-health smoke:

- Windows transfer/setup proof:
  `C:\Users\<operator>\EIDP-v407-0974b60f` expanded the v407 core ZIP after
  confirming SHA256
  `af48ed37d65695c044b520da78aad5307ed89b4b4a38cf27c6dc7e2737f50940`.
  `BUILD_INFO.json` reported commit
  `0974b60fb3d404678828ddfa348c74f4dd740c79`, branch
  `sprint8-handoff-finalize`, and `git_dirty=false`. `EIDP-setup.bat`
  completed the offline wheelhouse install, package install, `db-bootstrap`,
  `import-excel`, school-year task rebuild, and validation. The install
  validator returned `OK install`, `school_count=2418`,
  `school_fiscal_year_status_count=2418`, `sqlite_integrity_check=ok`,
  `sqlite_table_count=15`, and `wheel_count=78`.
- Windows R7 retroactive Excel proof:
  with process-local `EIDP_TARGET_FISCAL_YEAR=2025`, `eidp export-excel`
  wrote `data\output\v407-r7-retroactive-export.xlsx` with
  `採録状況=2418`, `対象比率=10022`, `学科別=9719`, and
  `在籍のみ抜粋=9719`. `eidp diff-excel --business-values` returned
  `diff_rc=0` and reported duplicate-key diagnostics for the reference workbook
  while exported duplicate keys remained `0`.
- Windows R7 retroactive browser Excel proof:
  with process-local `EIDP_TARGET_FISCAL_YEAR=2025`, the v407 UI served on
  Windows `127.0.0.1:8504` through Mac tunnel `127.0.0.1:18504`, returned
  `/_stcore/health=ok`, generated `Excel プレビュー` with
  `抽出済み学校 2031`, `Excel対象行 7150`, and sheet counts
  `採録状況=2418`, `対象比率=10022`, `学科別=9719`,
  `在籍のみ抜粋=9719`. Playwright downloaded
  `_temp/v407-r7-browser-eidp_master.xlsx`; local `openpyxl` verification
  reported size `3,673,084` bytes, sheets `採録状況`, `対象比率`,
  `学科別`, `在籍のみ抜粋`, and row/column counts `2419x10`,
  `10023x22`, `9721x83`, `9721x19`.
- Windows UI-health proof:
  v407 Streamlit served on Windows `127.0.0.1:8501`; a Mac SSH tunnel
  `127.0.0.1:18501 -> 127.0.0.1:8501` with
  `-o ClearAllForwardings=no` returned `/_stcore/health` as `ok`, and the root
  page returned the Streamlit HTML shell.
- Stage 6 evidence verifier status:
  `scripts\verify_stage6_evidence.bat` first rejected
  `logs\stage6-evidence-20260514-170328.zip` for forbidden Excel exports and
  missing `last_run` / weekly-run / bootstrap / discovery evidence labels. After
  a process-local FY2025 dry-run weekly command wrote `data\output\last_run.json`,
  `logs\stage6-evidence-20260514-171128.zip` verified with `ok=true`, no
  forbidden entries, and present labels `build_info`, `diagnostics`, `last_run`,
  `stage6_recovery`, `stage6_residual_cleanup`, and `weekly_run_logs`. This is
  diagnostic-only because the `last_run` was `dry_run=true`,
  `ship_gate_status=not_measured`, and no operator write/yield evidence was
  collected.

Historical v399 Windows setup and UI-service smoke:

- Windows transfer/setup proof:
  `C:\Users\<operator>\EIDP-v399-12719c0-setup-probe` expanded the v399 core ZIP
  after confirming SHA256
  `bd4846796bdae16977d0aedfee6afcd56a7cee3abcaa2c9cfac5e9fabc6c6f97` and
  size `211184728`. `BUILD_INFO.json` reported commit
  `12719c0dc929d3b8727f6e8486931239e29a7145`, branch
  `sprint8-handoff-finalize`, and `git_dirty=false`. `EIDP-setup.bat`
  completed the offline wheelhouse install, package install, `db-bootstrap`,
  `import-excel`, school-year task rebuild, and validation. The log ended with
  `Import complete.`, `School year tasks rebuilt: fiscal_year=2026
  school_type=専門学校 rebuilt=2418 excel_ready=0`, and `OK install`.
  Follow-up checks returned validator `ok=true`, `school_count=2418`,
  `school_fiscal_year_status_count=2418`, `sqlite_integrity_check=ok`,
  `sqlite_table_count=15`, `wheel_count=78`,
  `duplicate_wheel_distributions={}`, and `cli_help_rc=0`.
- Windows UI-service proof:
  the same v399 extraction started Streamlit with
  `.venv\Scripts\python.exe -m streamlit run src\eidp\review\app.py
  --server.port 8502 --server.headless true --browser.gatherUsageStats false`.
  The service reported `Uvicorn server started on 0.0.0.0:8502`, Windows-local
  `curl.exe http://127.0.0.1:8502/_stcore/health` returned `ok`, `netstat`
  showed `0.0.0.0:8502 LISTENING` on PID `10104`, and `taskkill /PID 10104 /F`
  stopped it with follow-up `listening_8502=0`.
- v399 is now historical. The active setup/UI lane is v408.

Latest v397 Windows browser UI proof:

- The v397 extraction served Streamlit on Windows `127.0.0.1:8502`. The local
  tunnel `127.0.0.1:18502 -> Windows 127.0.0.1:8502` returned
  `/_stcore/health` as `ok`. Browser/Playwright rendered
  `http://127.0.0.1:18502/` with title `EIDP Operator Console`, build
  `3c100c7`, target `2026年度（令和8年度）`, `対象年度 要対応 2418`, and
  `Excel出力可 0/2418 校`. The same probe clicked only non-mutating quick
  navigation buttons for `PDF確認・手入力`, `対象年度の判定・修正`,
  `Excel プレビュー`, `設定`, and back to `① 学校別タスク`; the Excel
  workbook-generation button stayed disabled for empty FY2026 data. Captured
  console entries were verbose browser DOM notices about password fields outside
  forms, not application/page errors.

Historical v397 diagnostics hot-copy proof:

- The v398 `scripts\stage6_recovery_check.py` WMI fix was copied into the v397
  disposable extraction to validate the fix before rebuilding the ZIP. The
  first v397 `EIDP-diagnose.bat` attempt had timed out after writing only
  through `[stage6 recovery check]` in
  `logs\diagnostics-20260514-093712.txt`. After the hot-copy,
  `EIDP-diagnose.bat` completed and wrote
  `logs\diagnostics-20260514-094322.txt`. Key results were
  `validate_core_rc=0`, `validate_after_setup_rc=0`, `ship_readiness_rc=1`,
  `retroactive_fiscal_year=2025`, and `retroactive_ship_readiness_rc=0`.
  `stage6_recovery_rc=1` remained because old v384 OCR smoke files still exist
  under `C:\Users\<operator>`; the JSON showed `task.action_matches_expected=true`,
  so this is a recovery-state cleanup issue, not the previous diagnostics hang.

Historical v394 package-verifier commands:

- `uv run python scripts/build_windows_zip.py --skip-download --out-zip dist/eidp-windows-v394.zip --latest-alias`
  -> wrote `dist/eidp-windows-v394.zip` and refreshed `dist/eidp-windows.zip`;
  both have SHA256
  `62b2eae234bcdd2fea05b3da70dfcab531853bc302bf57c2c6cabff1c447a802`.
- `uv run python scripts/verify_windows_distribution.py --json dist/eidp-windows-v394.zip`
  -> `ok=true`, commit `e7cbe72afc2e09a334b7c8b96c323438d3e6bd4d`,
  `build_dirty=false`, `entry_count=3072`, `wheel_count=78`,
  root-level `EIDP-stage6-evidence.bat`, `EIDP-stage6-verify-evidence.bat`,
  and `EIDP-stage6-recovery.bat`, plus `scripts/collect_stage6_evidence.py`,
  `scripts\collect_stage6_evidence.bat`, `scripts/verify_stage6_evidence.py`,
  `scripts\verify_stage6_evidence.bat`, `scripts/stage6_recovery_check.py`,
  and `scripts\stage6_recovery_check.bat`
  included in the core ZIP contract; the packaged operator E2E template also
  requires `stage6_recovery_rc`, scheduled-task recovery evidence fields, and
  optional `logs\stage6-evidence-*.zip` attachment.
- `uv run python scripts/build_ocr_addon_zip.py --tesseract-dir _temp/ocr-addon-src/7z-extract --tessdata-dir /opt/homebrew/share/tessdata --out-zip dist/eidp-ocr-addon-windows-v383-smoke.zip`
  built an add-on from UB Mannheim Windows Tesseract `v5.4.0.20240606` plus
  local `jpn.traineddata` and the required `tessdata/configs/tsv` file;
  package verifier reported `OK ocr-addon`, SHA256
  `bd1e2c96dcd7ac17562d44c3338fbf8da0ac21a1b1e60386073c730775e8d853`,
  `entry_count=267`, and `manifest_files=266`.
- `uv run python scripts/verify_windows_distribution.py --json dist/eidp-windows.zip --ocr-addon dist/eidp-ocr-addon-windows-v383-smoke.zip --playwright-addon dist/eidp-playwright-addon-windows-v106.zip`
  -> `OK core`, `OK ocr-addon`, and `OK playwright-addon`, with matching v394
  core SHA256, `44` packaged discovery gold-set entries, `17`
  publication-lag cases, `47` prefecture seeds,
  `undemonstrated_pattern_sources=[]`, Stage 6 evidence/verification/recovery roots, the
  Stage 6 evidence/verification/recovery helper scripts, and the receiver-side
  `verify_stage6_evidence.py` checker; the packaged Windows runbook
  includes `db-backup --output $dbBackup`, `VACUUM INTO`,
  `PRAGMA wal_checkpoint(TRUNCATE)`, and `logs\stage6-evidence-*.zip`, plus the Windows-local
  `stage6-evidence-verify-*.json` verification output.
- Windows v381 runtime-only OCR RAM probe:
  disposable extraction under
  `C:\Users\<operator>\EIDP-v381-da29fee-runtime-probe` returned
  `{"app_root": "C:\\Users\\<operator>\\EIDP-v381-da29fee-runtime-probe", "cpu_count": 20, "free_ram_mb": 16242, "ocr_auto_enable": true}`;
  the probe directory and uploaded v381 ZIP/sidecar were removed after capture.
- Windows v382 OCR runtime gate negative probe:
  disposable extraction under
  `C:\Users\<operator>\EIDP-v382-cc739c8-ocr-runtime-probe` ran
  `runtime\python\python.exe scripts\validate_windows_install.py . --require-ocr-runtime --json`;
  it returned `ok=false`, build commit
  `cc739c8704e45e37928a4ac55fa006766e5012dc`, `build_dirty=false`, and the
  expected missing-file errors for `ocr-addon/tesseract/tesseract.exe` and
  `ocr-addon/tessdata/jpn.traineddata`; the probe directory and uploaded v382
  ZIP/sidecar were removed after capture.
- Windows v384 OCR image plus copied-DB write proof:
  disposable extraction under
  `C:\Users\<operator>\EIDP-v384-75732b0-ocr-write-sandbox` with the v383 smoke OCR add-on
  generated `data\ocr-write-smoke.png`, executed the packaged Tesseract binary
  through `run_tesseract_on_image(...)`, and returned
  `ocr_full_text="V384 OCR WRITE SMOKE 2026"`, `ocr_usable_word_count=5`,
  `ocr_conf_values=[93,94,96,96,96]`, and `ocr_avg_confidence=0.95`.
  The same smoke copied the real v380 DB with
  `eidp db-backup`, seeded a marker document in the copied DB, and called
  `save_manual_entries(..., method="ocr_tesseract")`; it wrote one
  `DepartmentYearly` row with `extraction_confidence=0.95` and `verified=true`,
  promoted the document from `ocr_pending` to `ingested`, and emitted three
  `manual_entry` audit rows for `department`, `department_yearly`, and
  `document`. A follow-up query against the real v380 runtime DB returned
  `0` matching marker documents, departments, and audit rows. The disposable
  v384 probe directory and uploaded ZIPs were removed after capture, and the
  scheduled task was confirmed `Ready` with action
  `C:\Users\<operator>\EIDP-v380-f6a5e6d\scripts\weekly_run.bat`.
- Windows v384 OCR runtime gate positive probe:
  disposable extraction under
  `C:\Users\<operator>\EIDP-v384-75732b0-ocr-runtime-probe` expanded
  `dist/eidp-windows-v384.zip` plus
  `dist/eidp-ocr-addon-windows-v383-smoke.zip` after confirming the v384 core
  SHA256 sidecar. It ran
  `runtime\python\python.exe scripts\validate_windows_install.py . --require-ocr-runtime --json`
  and returned `ok=true`, build commit
  `75732b057a115afcebe35f9a40b831fac0ffa6f6`, `build_dirty=false`,
  `wheel_count=78`, `ocr_tessdata_dir` under the disposable extraction,
  packaged Tesseract version `tesseract v5.4.0.20240606`, and language support
  including `jpn` and `jpn_vert`.
- Windows v384 setup and diagnostics proof:
  disposable extraction under
  `C:\Users\<operator>\EIDP-v384-75732b0-setup-probe` expanded
  `dist/eidp-windows-v384.zip` after confirming the SHA256 sidecar. It ran
  `scripts\first_setup.bat` with `setup_rc=0`; then
  `.\.venv\Scripts\python.exe scripts\validate_windows_install.py . --after-setup --json`
  returned `ok=true`, build commit
  `75732b057a115afcebe35f9a40b831fac0ffa6f6`, `build_dirty=false`,
  `wheel_count=78`, `school_count=2418`,
  `school_fiscal_year_status_count=2418`, and `sqlite_integrity_check=ok`.
  `EIDP-diagnose.bat` returned `diagnose_rc=0`; the latest diagnostics file was
  `logs\diagnostics-20260514-020156.txt` and included
  `validate_after_setup_rc=0`, FY2026 `operator_reviewable_schools=0`,
  FY2026 `excel_ready_schools=0`, FY2025
  `is_retroactive_fiscal_year=true`, and `retroactive_ship_readiness_rc=0`.
  During setup, the harness observed `task_registered_to_v384=true`, then
  restored the pre-existing `EIDP Weekly Run` scheduled task; the restored task
  contains `EIDP-v380-f6a5e6d` and does not contain
  `EIDP-v384-75732b0-setup-probe`.
- Windows v384 UI service and initial browser render proof:
  disposable extraction under
  `C:\Users\<operator>\EIDP-v384-75732b0-ui-probe` expanded and set up the same v384
  core ZIP, then started Streamlit on Windows `127.0.0.1:8501`. The remote
  service returned `health_status=200` and `health_body=ok`; a local SSH tunnel
  `127.0.0.1:18501 -> Windows 127.0.0.1:8501` also returned HTTP `200 OK` from
  `/_stcore/health`. Browser/Playwright rendered
  `http://127.0.0.1:18501/` with page title `EIDP Operator Console`; the
  accessibility snapshot showed `今週のやること`, `① 学校別タスク`,
  `対象年度: 2026年度（令和8年度）`, build
  `75732b0 / branch: sprint8-handoff-finalize`, `対象年度 要対応 2418`,
  `Excel出力可 0/2418 校`, and the initial acquisition warning. Captured console
  messages reported `Total messages: 0 (Errors: 0, Warnings: 0)`. Cleanup
  stopped the service, removed the v384 UI probe and upload files, confirmed
  `port_8501_listeners=0`, and confirmed the scheduled task still contains
  `EIDP-v380-f6a5e6d` and does not contain
  `EIDP-v384-75732b0-ui-probe`.
- Windows v384 read-only quick-navigation proof:
  a second disposable extraction under
  `C:\Users\<operator>\EIDP-v384-75732b0-ui-nav-probe` expanded and set up the same
  v384 core ZIP, started Streamlit on Windows `127.0.0.1:8501`, and used the
  same local SSH tunnel. Browser/Playwright clicked only the five non-mutating
  quick navigation buttons: `PDF確認・手入力`, `③ 年度判定・修正`,
  `④ Excel プレビュー`, `⑤ 設定（年度・OCR・API）`, and back to
  `① 学校別タスク`. The snapshots rendered `PDF確認・手入力`,
  `対象年度の判定・修正`, `Excel プレビュー` with
  `対象年度: 2026年度（令和8年度） / 対象範囲: 専門学校`, `設定` with the
  `バージョン`, `和暦 alias`, `OCR`, and `外部 API` sections, and the task
  page again. The Excel page's workbook-generation button remained disabled for
  empty FY2026 data, and the settings save button was not clicked. Incremental
  console capture reported `Total messages: 5 (Errors: 0, Warnings: 0)`.
  Cleanup stopped the service, removed the v384 UI-nav probe and upload files,
  confirmed `port_8501_listeners=0`, and confirmed the scheduled task still
  contains `EIDP-v380-f6a5e6d` and does not contain
  `EIDP-v384-75732b0-ui-nav-probe`.
- Windows v384 retroactive FY2025 Excel preview/download smoke:
  a third disposable extraction under
  `C:\Users\<operator>\EIDP-v384-75732b0-r7-excel-probe` expanded and set up the
  same v384 core ZIP. Streamlit was started with process-scoped
  `EIDP_TARGET_FISCAL_YEAR=2025` and no `.env` write, then opened through the
  SSH tunnel. The `④ Excel プレビュー` page showed
  `対象年度: 2025年度（令和7年度）`, `抽出済み学校 2031`, and `Excel対象行 7150`.
  The `プレビュー workbook を生成` button was enabled, generated the in-memory
  workbook, and exposed `Excel ダウンロード`; the browser download saved
  `eidp_master.xlsx` with size `3,728,651` bytes. The downloaded workbook
  opened with sheets `採録状況`, `対象比率`, `学科別`, and `在籍のみ抜粋`;
  `openpyxl` reported row counts `2419`, `10023`, `9721`, and `9721`
  including headers. Streamlit stdout recorded export counts
  `採録状況=2418`, `対象比率=10022`, `学科別=9719`, and `在籍のみ抜粋=9719`.
  The downloaded workbook and Playwright snapshots were removed after
  verification. Cleanup stopped the service, removed the v384 R7 Excel probe
  and upload files, confirmed no `8501` listener remained, and confirmed the
  scheduled task still points at `EIDP-v380-f6a5e6d`.
- `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v379.zip --require-demonstrated-discovery-patterns`
  now fails under the current verifier because v379 predates the
  `db-backup --output $dbBackup` runbook contract.

Latest Windows setup and backup-smoke commands:

- Windows v384 environment, Task Scheduler, and `db-backup` smoke:
  a disposable
  `C:\Users\<operator>\EIDP-v384-75732b0-backup-env-sandbox` expanded the v384
  core ZIP after confirming SHA256
  `2707def6337f3f35c63c9933a1805271dcf75d8bf7d8ece27c09ba8de72d31c0`.
  Environment capture reported host `JUNMING`, `Microsoft Windows 11 Pro`
  version `10.0.26200` build `26200`, `AMD64`, culture/UI culture `zh-CN`,
  timezone `Tokyo Standard Time`, CPU `13th Gen Intel(R) Core(TM) i9-13900HK`
  with `14` cores / `20` logical processors, `32453` MB visible RAM, and
  `C:` size `1888.7` GB / free `964.4` GB. `scripts\first_setup.bat` returned
  `setup_rc=0`; the task created by setup pointed at
  `"C:\Users\<operator>\EIDP-v384-75732b0-backup-env-sandbox\scripts\weekly_run.bat"`
  with state `Ready`, next run `05/18/2026 02:00:00`, last run
  `05/11/2026 02:00:00`, and last result `0`. The harness restored the task
  to `C:\Users\<operator>\EIDP-v380-f6a5e6d\scripts\weekly_run.bat`. The v384
  package-local command
  `.\.venv\Scripts\python.exe -m eidp.cli db-backup --output data\eidp-v384-backup-smoke.sqlite3`
  returned `db_backup_rc=0`; verification opened the backup and reported
  `backup_size=9015296`, `integrity=ok`, `sqlite_objects=35`,
  `school_count=2418`, and `school_year_status_count=17696`. Cleanup removed
  the sandbox, uploaded ZIP/sidecar, and verify script (`remaining=false` for
  all tracked probe paths).
- Windows v380 package transfer and extraction:
  transferred `dist/eidp-windows-v380.zip` and its sidecar to
  `C:\Users\<operator>\EIDP-transfer`; Windows SHA256 matched
  `1fef8d468ba2e7d882f7a3a774ccbbf071d1e1ee362ae62b8c4e458c576e5361`;
  expanded into `C:\Users\<operator>\EIDP-v380-f6a5e6d`. The packaged
  `BUILD_INFO.json` records commit
  `f6a5e6d46db7b0b836b18399e5b401362575c38d`, branch
  `sprint8-handoff-finalize`, and `git_dirty=false`.
- Windows v380 setup:
  `EIDP-setup.bat` completed, imported the master workbook, and rebuilt
  school-year tasks for FY2026 with `rebuilt=2418` and `excel_ready=0`.
  The package-local validator reported `OK install`, `school_count=2418`,
  `school_fiscal_year_status_count=2418`, `sqlite_integrity_check=ok`,
  required tables present, `document_unique_indexes` including
  `uq_document_file_hash`, and `wheel_count=78`.
- Windows v380 after-setup validator:
  `runtime\python\python.exe scripts\validate_windows_install.py . --after-setup --json`
  returned `ok=true`, no errors or warnings, the same v380 build commit,
  `master_xlsx_present=true`, `school_count=2418`,
  `school_fiscal_year_status_count=2418`, `sqlite_integrity_check=ok`, and all
  required SQLite tables.
- Windows v380 diagnostics:
  `EIDP-diagnose.bat` wrote
  `logs\diagnostics-20260513-231923.txt`. FY2026 readiness remained below gate
  with `ship_readiness_rc=1`, `strict_target_pdf_schools=0`,
  `operator_reviewable_schools=0`, `excel_ready_schools=0`, and
  `estimated_manual_workload_rate=1.0`. The retroactive FY2025 section recorded
  `is_retroactive_fiscal_year=true`, `extracted_schools=2031`,
  `extracted_rate=0.84`, `retroactive_fiscal_year=2025`, and
  `retroactive_ship_readiness_rc=0`. Because this was a fresh setup without
  discovery/bootstrap progress, both FY2026 and FY2025 operator-reviewable
  readiness remained `0`.
- Windows v380 `db-backup` smoke:
  `.\.venv\Scripts\python.exe -m eidp.cli db-backup --output data\eidp-backup-smoke.sqlite3`
  wrote a package-local backup; a Python SQLite check opened that backup and
  reported `backup_objects=35` and `integrity=ok`; the temporary smoke backup
  was removed afterward (`backup_removed=True`).
- Windows v380 UI service health smoke:
  a PowerShell harness started Streamlit from
  `C:\Users\<operator>\EIDP-v380-f6a5e6d` on `127.0.0.1:8501`,
  received `/_stcore/health` as `status=200 body=ok`, reported
  `Streamlit, version 1.57.0`, and then stopped the process. The stdout tail
  included `URL: http://127.0.0.1:8501`; stderr recorded
  `Uvicorn server started on 127.0.0.1:8501`. A follow-up process check
  returned `remaining_streamlit_processes=0` for v380. This proves app-server
  health only; browser rendering, navigation, and operator-action click-through
  still require separate evidence.
- Windows v380 browser render smoke:
  with remote Streamlit held open in the same SSH session as the tunnel,
  `ssh -o ClearAllForwardings=no -o ExitOnForwardFailure=yes
  -L 127.0.0.1:18501:127.0.0.1:8501 win ...` exposed the Windows UI to the
  Mac. The explicit `ClearAllForwardings=no` override is required because the
  local `Host win` SSH config clears command-line forwards by default. Local
  `curl http://127.0.0.1:18501/_stcore/health` returned `ok`; Playwright
  rendered `http://127.0.0.1:18501/` with title `EIDP Operator Console`, page
  heading `① 学校別タスク`, target year `2026年度（令和8年度）`, build
  `f6a5e6d`, `対象校 2418`, `Excel出力可 0/2418 校`, `URLなし 2418`, and
  the initial acquisition warning. This proves initial browser rendering on
  the current v380 package.
- Windows v380 read-only Excel preview smoke:
  the same tunneled Playwright session clicked only the non-mutating sidebar
  button `④ Excel プレビュー`. The page rendered with heading
  `Excel プレビュー`, `対象年度: 2026年度（令和8年度） / 対象範囲: 専門学校`,
  a warning that current-year transcribed rows are `0`, and the
  `プレビュー workbook を生成` button present but disabled, preventing old-year
  or empty workbook output. The temporary Playwright screenshot
  `eidp-v380-excel-preview.png` and generated snapshot files were removed
  afterward. The local tunnel was stopped, and a follow-up Windows process
  cleanup reported `streamlit_after_cleanup=0` for v380.
- Windows v380 retroactive FY2025 Excel preview/download smoke:
  the same v380 package was started with process-scoped
  `EIDP_TARGET_FISCAL_YEAR=2025` (no `.env` write) and opened through the SSH
  tunnel. The `④ Excel プレビュー` page showed `対象年度: 2025年度`,
  `抽出済み学校 2031`, and `Excel対象行 7150`. The
  `プレビュー workbook を生成` button was enabled, generated the in-memory
  workbook, and exposed `Excel ダウンロード`; the browser download suggested
  `eidp_master.xlsx` and saved
  `_temp/eidp-v380-r7-retroactive-download.xlsx` with size `3,728,651` bytes.
  Browser warning/error/pageerror events were empty. The Streamlit stdout
  recorded sheet exports `採録状況=2418`, `対象比率=10022`, `学科別=9719`,
  and `在籍のみ抜粋=9719`. The downloaded workbook, Playwright download copy,
  and temporary Streamlit launcher were removed afterward; cleanup reported
  `run_script_exists_after_cleanup=False` and
  `remaining_v380_streamlit_processes=0`, and the local tunnel had no listener.
- Windows v380 read-only quick-navigation click-through:
  the same tunnel pattern was rerun against v380 and Playwright clicked only
  the five non-mutating quick navigation buttons:
  `① 学校別タスク`, `② PDF確認・手入力`, `③ 年度判定・修正`,
  `④ Excel プレビュー`, and `⑤ 設定（年度・OCR・API）`. Each page rendered
  the expected heading or key text with no missing assertions:
  `① 学校別タスク` with `週次URL/PDF再取得` / `次に進める作業`,
  `PDF確認・手入力`, `対象年度の判定・修正`, `Excel プレビュー` with
  `プレビュー workbook を生成`, and `設定` with `バージョン` / `OCR` /
  `外部 API`. The script did not click acquisition, save, export, flush, or
  any data-mutating action. Captured browser console output contained only
  Chrome `VERBOSE` DOM messages about password fields, not warning/error or
  page-error events. The local tunnel was stopped, and a follow-up Windows
  process cleanup reported `streamlit_after_cleanup=0` for v380.
- Windows v384 browser UI URL-candidate review write smoke:
  a disposable `C:\Users\<operator>\EIDP-v384-75732b0-url-review-sandbox` was
  created from the v384 core ZIP and a copied runtime DB produced by the v380
  package-local `eidp db-backup` command. It seeded one pending
  `url_candidate` review item for `日本工学院専門学校` with candidate URL
  `https://example.com/eidp-v384-url-candidate-smoke`. The v384 Streamlit UI
  ran from the disposable extraction, and the tunneled browser opened
  `詳細 operator` -> `URL候補レビュー`, verified `確認待ち 1 件`, entered
  reject reason `v384 UI reject smoke`, clicked `却下`, and observed
  `確認待ちのURL候補はありません。`. Direct post-UI DB verification reported
  the marker review item as `status=resolved`, `resolution=rejected`,
  `notes="v384 UI reject smoke"`, one `ManualActionLog` row with
  `action_type="url_candidate_rejected"`, `target_table="review_item"`, and
  `target_id=1`, and zero `SchoolSite` rows for the candidate URL. The real
  v380 runtime DB reported zero matching review-item, audit, and school-site
  marker rows. Cleanup removed the v384 sandbox and uploaded probe files and
  confirmed `port_8501_listeners=0`.
- Windows v380 browser UI URL-candidate review write smoke:
  a disposable `C:\Users\<operator>\EIDP-v380-url-review-sandbox` was created from
  the v380 runtime database through the package-local `eidp db-backup`
  command. It seeded one pending `url_candidate` review item for
  `日本工学院専門学校` with candidate URL
  `https://example.com/eidp-v380-url-candidate-smoke`. The v380 Streamlit UI
  ran with `EIDP_APP_ROOT` pointed at that sandbox, and the tunneled browser
  opened `詳細 operator` -> `URL候補レビュー`, verified `確認待ち 1 件`,
  entered reject reason `v380 UI reject smoke`, clicked `却下`, and then
  observed `確認待ちのURL候補はありません。` with no warning/error/pageerror
  events. Direct post-UI DB verification reported `review_items=1`,
  `pending_items=0`, `resolved_rejected_items=1`, `audit_rows=1`,
  `audit_action_types=["url_candidate_rejected"]`, and
  `audit_reasons=["v380 UI reject smoke"]`; the real v380 runtime DB reported
  `runtime_matching_audit_rows=0`. The local tunnel was stopped, residual
  sandbox Streamlit processes were removed by exact PID/command-line match, and
  `sandbox_exists_after_cleanup=False` / `remaining_matching_processes=0`
  confirmed cleanup.
- Windows v384 browser UI audit-outbox flush smoke:
  a disposable `C:\Users\<operator>\EIDP-v384-75732b0-audit-sandbox` was created
  from the v384 core ZIP and a copied runtime DB produced by the v380
  package-local `eidp db-backup` command. Existing copied-runtime pending
  audit rows were stamped as already exported, then the seed inserted one
  unexported `stage6_v384_ui_audit_flush_smoke` `ManualActionLog` row with
  actor `codex-v384-ui-smoke` and reason `v384 UI audit flush smoke`. The
  v384 Streamlit UI ran from the disposable extraction, and the tunneled
  browser opened `詳細 operator` -> `監査ログ`, verified
  `JSONL outbox 未送信` with pending count `1`, clicked `Outbox を flush`,
  and observed `exported=1 already_present=0 failed=0` with the seeded action
  and actor visible. Direct post-UI DB/JSONL verification reported
  `pending_count=0`, `matching_db_rows=1`,
  `jsonl_exported_at_present=true`, `jsonl_export_error_null=true`,
  `jsonl_path=C:\Users\<operator>\EIDP-v384-75732b0-audit-sandbox\data\audit\manual-actions.jsonl`,
  `matching_outbox_rows=1`, `outbox_lines=1`,
  `outbox_action_types=["stage6_v384_ui_audit_flush_smoke"]`, and
  `outbox_actors=["codex-v384-ui-smoke"]`; the real v380 runtime DB reported
  `matching_db_rows=0` for the same marker. Cleanup removed the v384 sandbox
  and uploaded probe files and confirmed `port_8501_listeners=0`.
- Windows v380 browser UI audit-outbox flush smoke:
  a disposable `C:\Users\<operator>\EIDP-v380-ui-audit-sandbox` was created from
  the v380 runtime database through the package-local `eidp db-backup`
  command. It seeded one unexported
  `stage6_v380_ui_audit_flush_smoke` `ManualActionLog` row with actor
  `codex-v380-ui-smoke` and reason `v380 UI audit flush smoke`. The v380
  Streamlit UI ran with `EIDP_APP_ROOT` pointed at that sandbox, and the
  tunneled browser opened `詳細 operator` -> `監査ログ`, verified
  `JSONL outbox 未送信` with pending count `1`, clicked `Outbox を flush`,
  and observed `exported=1 already_present=0 failed=0` with the seeded action
  and actor visible. Browser warning/error/pageerror events were empty. Direct
  post-UI verification using `settings.data_dir` reported
  `jsonl_path=C:\Users\<operator>\EIDP-v380-ui-audit-sandbox\data\audit\manual-actions.jsonl`,
  `pending=0`, `matching_db_rows=1`, `jsonl_exported_at_present=true`,
  `matching_outbox_rows=1`, `outbox_lines=1`,
  `outbox_action_types=["stage6_v380_ui_audit_flush_smoke"]`, and
  `outbox_actors=["codex-v380-ui-smoke"]`; the real v380 runtime DB reported
  `runtime_matching_db_rows=0`. The local tunnel was stopped, residual sandbox
  Streamlit processes were removed by exact PID/command-line match, and
  `sandbox_exists_after_cleanup=False` / `remaining_matching_processes=0`
  confirmed cleanup.
- Windows v384 browser UI PDF manual-entry save smoke:
  a disposable `C:\Users\<operator>\EIDP-v384-75732b0-manual-entry-sandbox` was
  created from the v384 core ZIP and a copied runtime DB produced by the v380
  package-local `eidp db-backup` command. It seeded one FY2026 `parse_failed`
  document with source URL
  `https://example.com/eidp-v384-manual-entry-smoke.pdf`. The v384 Streamlit
  UI ran from the disposable extraction, and the tunneled browser opened
  `② PDF確認・手入力`, verified `表示 1 / 待機 1 件` with one save-eligible
  queue row for `日本工学院専門学校`, filled one department row
  (`V384手入力学科`, capacity `40`, enrollment `35`, international students
  `2`, graduates `30`, advanced `5`, employed `24`, other `1`, previous
  enrollment `36`, dropouts `1`, dropout rate `0.0278`, duration `2`) with
  reason `v384 UI manual entry smoke`, and submitted `保存`. After the
  Streamlit rerun the page showed no documents for that view. Direct post-UI
  SQLite verification reported the seeded document promoted to `ingested`, one
  `department` row, one `department_yearly` row with `document_id=1`,
  `fiscal_year=2026`, `revision=1`, `is_current=1`,
  `extraction_method="manual"`, `extraction_confidence=1`, `verified=1`, and
  three `manual_entry` audit rows targeting `department`, `department_yearly`,
  and `document`. The same check confirmed `support_recipient_rows_for_doc=0`
  and the real v380 runtime DB reported `0` matching document, department,
  yearly, audit, and support-recipient marker rows. Cleanup removed the v384
  sandbox and uploaded probe files and confirmed `port_8501_listeners=0`.
- Windows v380 browser UI PDF manual-entry save smoke:
  a disposable `C:\Users\<operator>\EIDP-v380-manual-entry-sandbox` was created
  from the v380 runtime database through the package-local `eidp db-backup`
  command. It seeded one FY2026 `parse_failed` document with source URL
  `https://example.com/eidp-v380-manual-entry-smoke.pdf`. The v380 Streamlit
  UI ran with `EIDP_APP_ROOT` pointed at that sandbox, and the tunneled browser
  opened `② PDF確認・手入力`, verified a single save-eligible queue row for
  `日本工学院専門学校`, filled one department row (`V380手入力学科`, capacity
  `40`, enrollment `35`, international students `2`, graduates `30`, advanced
  `5`, employed `24`, other `1`, previous enrollment `36`, dropouts `1`,
  dropout rate `0.0278`, duration `2`) with reason
  `v380 UI manual entry smoke`, and submitted the form. After the Streamlit
  rerun the page showed the queue empty for that view. Direct post-UI DB
  verification reported the seeded document promoted to `ingested`, one new
  `department` row, one `department_yearly` row with `document_id=1`,
  `fiscal_year=2026`, `revision=1`, `is_current=1`, `extraction_method="manual"`,
  `extraction_confidence=1`, `verified=1`, and three `manual_entry` audit rows
  targeting `department`, `department_yearly`, and `document`. The same check
  confirmed `sandbox_support_recipient_smoke_rows=0`, because this UI page does
  not write SupportRecipient records, and the real v380 runtime DB reported
  `runtime_matching_documents=0`, `runtime_matching_departments=0`,
  `runtime_matching_department_yearly=0`, and
  `runtime_matching_manual_actions=0`. The local tunnel was stopped, the
  sandbox was removed, and cleanup reported
  `sandbox_exists_after_cleanup=False`, `port_8501_open=False`, and
  `remaining_matching_processes=0`.
- Windows v384 browser UI fiscal-year override write smoke:
  a disposable
  `C:\Users\<operator>\EIDP-v384-75732b0-fiscal-override-sandbox` was created from
  the v384 core ZIP and a copied runtime DB produced by the v380
  package-local `eidp db-backup`. It seeded one FY2025 `ingested` document
  with source URL
  `https://example.com/eidp-v384-fiscal-override-smoke.pdf`, one current
  FY2025 `DepartmentYearly`, one current FY2025 `SupportRecipient`, one
  current FY2025 `SchoolYearStatus`, and one pre-existing FY2026 current
  `DepartmentYearly` for the same department. The v384 UI opened
  `③ 年度判定・修正`, selected doc#1, kept target `2026`, filled reason
  `v384 UI fiscal override smoke`, and clicked `年度を確定`; the rerun showed
  the candidate changed to
  `2026年度（令和8年度）(修正済み→2026年度（令和8年度）)`. Direct DB verification
  reported `Document.fiscal_year=2026` and `fiscal_year_override=2026`;
  source FY2025 rows were demoted; the pre-existing FY2026 `DepartmentYearly`
  was demoted; a new FY2026 current `DepartmentYearly` revision `2` was
  inserted with `document_id=1`, `capacity=40`, `enrollment=35`, and
  `extraction_method="manual"`; a new FY2026 current `SupportRecipient` was
  inserted with `annual_total=22` and `recipient_rate=0.6286`; a new FY2026
  current `SchoolYearStatus` was inserted with `status="excel_ready"`; and
  four `fiscal_year_override` audit rows targeted `department_yearly`,
  `support_recipient`, `school_year_status`, and `document`. The real v380
  runtime DB reported `matching_documents=0`, `matching_schools=0`,
  `matching_departments=0`, and `matching_audit_rows=0`. Cleanup removed the
  sandbox and upload files, left `port_8501_listeners=0`, and restored the
  scheduled task to v380.
- Windows v380 browser UI fiscal-year override write smoke:
  a disposable `C:\Users\<operator>\EIDP-v380-fiscal-override-sandbox` was created
  from the v380 runtime database through the package-local `eidp db-backup`
  command. It seeded one FY2025 `ingested` document with source URL
  `https://example.com/eidp-v380-fiscal-override-smoke.pdf`, one current
  FY2025 `DepartmentYearly` row, one current FY2025 `SupportRecipient` row,
  one current FY2025 `SchoolYearStatus` row, and one pre-existing FY2026
  current `DepartmentYearly` row for the same department. The v380 Streamlit UI
  ran with `EIDP_APP_ROOT` pointed at that sandbox, and the tunneled browser
  opened `③ 年度判定・修正`, filled reason `v380 UI fiscal override smoke`,
  and clicked `年度を確定`. Direct post-UI DB verification reported
  `Document.fiscal_year=2026` and `fiscal_year_override=2026`; the source
  FY2025 yearly, support-recipient, and school-year-status rows were demoted
  to `is_current=0`; the pre-existing FY2026 `DepartmentYearly` row was
  demoted to `is_current=0`; and new FY2026 current rows were inserted for
  `DepartmentYearly`, `SupportRecipient`, and `SchoolYearStatus`. The same
  check reported four `fiscal_year_override` audit rows targeting
  `department_yearly`, `support_recipient`, `school_year_status`, and
  `document`, all with reason `v380 UI fiscal override smoke`. The real v380
  runtime DB reported `runtime_matching_documents=0`,
  `runtime_matching_departments=0`, and `runtime_matching_audit_rows=0`. The
  local tunnel was stopped, the sandbox was removed, and cleanup observed
  `sandbox_exists=0` and only a remote `TIME_WAIT` connection for port `8501`.
- Windows v384 package-local SupportRecipient ingest append-only smoke:
  a disposable
  `C:\Users\<operator>\EIDP-v384-75732b0-support-recipient-sandbox` was created
  from the v384 core ZIP and a copied runtime DB produced by the v380
  package-local `eidp db-backup`. The smoke seeded two FY2026 target documents
  for `V384 SupportRecipient Smoke School`, pointed `EIDP_APP_ROOT` at the
  sandbox, and called the packaged `ingest_document` path twice while
  monkeypatching only the package parser boundary (`parse_pdf`) to return
  deterministic annotations containing one department row and
  SupportRecipient totals. Both ingest calls returned `support_recipient=1`,
  `support_recipient_current=1`, `yearly_upserted=1`, and `yearly_current=1`.
  Direct SQLite verification found two SupportRecipient rows:
  revision `1` had `annual_total=100`, `grand_total=100`,
  `extraction_confidence=0.94`, and `is_current=false`; revision `2` had
  `annual_total=120`, `grand_total=120`, `extraction_confidence=1.0`, and
  `is_current=true`. The smoke observed `support_recipient_count=2` and
  `current_smoke_support_recipient_count=1`. The real v380 runtime DB reported
  `matching_documents=0`, `matching_schools=0`, and
  `matching_support_recipients=0`. Cleanup restored `EIDP Weekly Run` to
  `C:\Users\<operator>\EIDP-v380-f6a5e6d\scripts\weekly_run.bat` and removed the
  sandbox, backup, uploaded ZIP/sidecar, Python smoke, PowerShell runner, and
  result JSON.
- Windows v380 sandboxed Saitama 5-site bounded backend smoke:
  a disposable `C:\Users\<operator>\EIDP-v380-backend-sandbox` was created from the
  v380 runtime database through the package-local `eidp db-backup` command.
  The package-local `scripts\bootstrap_pdf_pipeline.py` then ran with
  `EIDP_APP_ROOT` pointed at that sandbox:
  `--pref saitama --skip-known-url-discovery --url-search off
  --school-url-crawl off --discovery-methods prefecture_aggregator
  --batch-size 5 --rate-limit 0.1 --request-timeout 10`, with artifact,
  output, PDF storage, evidence-log, RCA output, progress, and lock paths all
  redirected under the sandbox. It downloaded the current Saitama official
  artifact `r080401kikanyokenlist.pdf`, extracted `58`, matched `51`, applied
  `added=51 / upgraded=0 / skipped=7 / review_items=2`, crawled `5`
  official-index disclosure sites, found candidates on all `5`, downloaded
  `0` strict FY2026 target PDFs, skipped `163`, and wrote `2084` discovery
  evidence lines. Ingest processed `0` documents, then status rebuild reported
  `rebuilt=2418`, `excel_ready=0`, `target_pdf_auto_yield_pct=0.0`,
  `operator_reviewable_count=5`, `operator_reviewable_yield_pct=0.2`, and
  `ship_gate_status=below_gate`; the generated RCA batch plan had `5` items /
  `5` total candidates. Post-run verification inside the sandbox reported
  `school_site_count=51`, `prefecture_aggregator_sites=51`,
  `review_items=2`, `documents=0`, `status_rows=2418`,
  `progress_status=succeeded`, `progress_percent=1.0`,
  `progress_ship_gate_status=below_gate`, `progress_operator_reviewable_count=5`,
  `evidence_lines=2084`, `rca_files=1`, `rca_items=5`, and
  `rca_total_candidates=5`. The real v380 runtime DB remained unchanged for
  these tables: `runtime_school_site_count=0`, `runtime_review_items=0`,
  `runtime_documents=0`, and `runtime_status_rows=2418`. The sandbox was
  removed afterward; cleanup reported `sandbox_exists_after_cleanup=False` and
  `remaining_matching_processes=0`.

Previous v379 Windows setup and UI-service commands:

- `uv run python scripts/build_windows_zip.py --skip-download --out-zip dist/eidp-windows-v379.zip --latest-alias`
  -> wrote `dist/eidp-windows-v379.zip` and refreshed `dist/eidp-windows.zip`;
  both have SHA256
  `88afc9f40feabe0dcd701fea3ccfdb870f96d1fe1e72afa9f1c66e2490fce212`.
- `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v379.zip --require-demonstrated-discovery-patterns`
  and `uv run python scripts/verify_windows_distribution.py dist/eidp-windows.zip --require-demonstrated-discovery-patterns`
  -> both `OK core`, with matching SHA256, `44` packaged discovery gold-set
  entries, `17` publication-lag cases, `47` prefecture seeds, and
  `undemonstrated_pattern_sources=[]`.
- `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v378.zip --require-demonstrated-discovery-patterns`
  now fails under the current verifier because v378 predates the WAL-safe
  backup runbook contract and the latest Stage 6 gate-token contract.
- Windows v379 setup on `C:\Users\<operator>\EIDP-v379-71e7537`:
  transferred `dist/eidp-windows-v379.zip` and its sidecar to
  `C:\Users\<operator>\EIDP-transfer`; Windows SHA256 matched
  `88afc9f40feabe0dcd701fea3ccfdb870f96d1fe1e72afa9f1c66e2490fce212`;
  expanded into a separate directory without touching v376 or v378.
  `EIDP-setup.bat` completed with build commit
  `d851de9edc16d831707b90ab4459c1de2e83434a`, `school_count=2418`,
  `school_fiscal_year_status_count=2418`, `sqlite_integrity_check=ok`,
  `document_unique_indexes` including `uq_document_file_hash`, and
  `wheel_count=78`.
- Windows v379 after-setup validator:
  `runtime\python\python.exe scripts\validate_windows_install.py . --after-setup --json`
  returned `ok=true`, no errors or warnings, the same v379 build commit,
  `master_xlsx_present=true`, `school_count=2418`,
  `school_fiscal_year_status_count=2418`, `sqlite_integrity_check=ok`, and all
  required SQLite tables.
- Windows v379 diagnostics:
  `EIDP-diagnose.bat` wrote
  `logs\diagnostics-20260513-230505.txt`. FY2026 readiness remained below gate
  with `ship_readiness_rc=1`, `strict_target_pdf_schools=0`,
  `operator_reviewable_schools=0`, `excel_ready_schools=0`, and
  `estimated_manual_workload_rate=1.0`. The retroactive FY2025 section recorded
  `is_retroactive_fiscal_year=true`, `extracted_schools=2031`,
  `extracted_rate=0.84`, `retroactive_fiscal_year=2025`, and
  `retroactive_ship_readiness_rc=0`. Because this was a fresh setup without
  discovery/bootstrap progress, both FY2026 and FY2025 operator-reviewable
  readiness remained `0`.
- Windows v379 UI service health smoke:
  a PowerShell harness started Streamlit from
  `C:\Users\<operator>\EIDP-v379-71e7537` on `127.0.0.1:8501`,
  received `/_stcore/health` as `status=200 body=ok`, reported
  `Streamlit, version 1.57.0`, and then stopped the process. The stdout tail
  included `URL: http://127.0.0.1:8501`; stderr recorded
  `Uvicorn server started on 127.0.0.1:8501`. A follow-up process check
  returned `count=0` for v379 Streamlit processes. This proves app-server
  health only; browser rendering, navigation, and operator-action click-through
  still require separate evidence.

Historical source local verification for then-current source evidence base
`c2a6f532075a8b02eb7a5853de3b3a564ab72107`:

- `uv run pytest tests/unit -q`
  -> `1449 passed, 5 warnings in 44.96s`.
- `uv run ruff check src`
  -> `All checks passed`.
- `uv run mypy src`
  -> `Success: no issues found in 83 source files`.
- Targeted RCA triage checks also passed:
  `uv run pytest tests/unit/test_discovery_evidence_summary.py -q`
  -> `14 passed in 0.36s`;
  `uv run pytest tests/unit/test_cli_discovery_rca_packet.py -q`
  -> `24 passed in 0.60s`.
- Targeted discovery entrypoint/context checks:
  `uv run pytest tests/unit/test_pdf_discovery.py tests/unit/test_cli_pdf_discovery_strict.py tests/unit/test_discovery_gold_set_seed.py tests/unit/test_url_normalization.py -q`
  -> `183 passed, 5 warnings in 12.42s`;
  `uv run pytest tests/unit/test_discovery_gold_set.py tests/unit/test_discovery_gold_set_summary.py tests/unit/test_cli_discovery_gold_set.py tests/unit/test_cli_eval_discovery_gold.py tests/unit/test_discovery_gold_set_eval.py tests/unit/test_discovery_gold_set_seed.py -q`
  -> `49 passed in 1.84s`;
  `uv run ruff check src/eidp/scraper/pdf_discovery.py src/eidp/scraper/discovery_gold_set.py tests/unit/test_pdf_discovery.py tests/unit/test_discovery_gold_set_seed.py tests/unit/test_url_normalization.py`
  -> `All checks passed`;
  `uv run mypy src/eidp/scraper/pdf_discovery.py src/eidp/scraper/discovery_gold_set.py`
  -> `Success: no issues found in 2 source files`.

Historical v401 full non-Windows release-gate commands:

- `uv run python scripts/run_non_windows_release_gates.py dist/eidp-windows-v401.zip --json --output _temp/v401-non-windows-release-gates-full.json`
  -> `ok=true`; SHA256 sidecar matched
  `ff54f3a4c6a498ab9af89890e1ee614b31e57a87066277f1323f8f37d6f1bcf5`; full
  unit passed with `1433 passed, 5 warnings`; validator/distribution unit tests
  passed with `153 passed`; validator/distribution mypy and Ruff passed,
  including `scripts/verify_stage6_evidence.py`;
  discovery gold-set reported `44` entries, `10` strict target-year successes,
  `17` publication-lag cases, and `undemonstrated_pattern_sources=[]`;
  expected-prediction replay returned `44` exact matches / `0` failures; both
  package verifier modes passed with the same v401 SHA256, `entry_count=3078`,
  and `wheel_count=78`.

Latest recorded current-verifier read-only v401 package-gate rerun:

- `uv run python scripts/run_non_windows_release_gates.py dist/eidp-windows-v401.zip --skip-full-unit --json --output _temp/v401-non-windows-release-gates-stale-current-0e7e66d.json`
  -> `ok=false`; SHA256 sidecar still matched
  `ff54f3a4c6a498ab9af89890e1ee614b31e57a87066277f1323f8f37d6f1bcf5`;
  `package_source_check` failed before downstream gates with packaged commit
  `2d9c9f690c6f955330ea49276ef1a87157ceb6cd`, source commit
  `0e7e66d25a9e77193962c4385e06e9744ab9f09f`, `source_dirty=false`,
  `stale=true`, and `results=[]`.
  This prevents mixing source test gates with an older ZIP snapshot. The same
  stale-package boundary applies to latest code-affecting source evidence base
  `4a16363d81db9bc0ab5f5607247e1a67290d9268`, because v401 packages
  `2d9c9f690c6f955330ea49276ef1a87157ceb6cd`. No new ZIP was built.
- Allow-stale diagnostic rerun for the same v401 ZIP:
  `uv run python scripts/run_non_windows_release_gates.py dist/eidp-windows-v401.zip --skip-full-unit --allow-stale-package --json --output _temp/v401-non-windows-release-gates-allow-stale-current-bb621daa.json`
  -> `ok=false`; SHA256 sidecar matched; `package_source_check` was allowed
  through with `stale=true`, but package verification then failed. The v401 ZIP
  is missing the current verifier's Stage 6 safety tokens for recovery-check
  skipped expected action, evidence Excel opt-in/exclusion, residual cleanup
  symlink/junction refusal and rename-only archival, operator-coverage ship gate
  helper, audit-outbox archive matching helper, and default `18501 -> 8501`
  tunnel health guidance in the packaged Windows/operator runbooks.

Historical v394 full non-Windows release-gate commands:

- `uv run python scripts/run_non_windows_release_gates.py dist/eidp-windows-v394.zip --json --output _temp/v394-non-windows-release-gates-full.json`
  -> `ok=true`; SHA256 sidecar matched
  `62b2eae234bcdd2fea05b3da70dfcab531853bc302bf57c2c6cabff1c447a802`; full
  unit passed with `1422 passed, 5 warnings`; validator/distribution unit tests
  passed with `153 passed`; validator/distribution mypy and Ruff passed,
  including `scripts/verify_stage6_evidence.py`;
  discovery gold-set reported `44` entries, `10` strict target-year successes,
  `17` publication-lag cases, and `undemonstrated_pattern_sources=[]`;
  expected-prediction replay returned `44` exact matches / `0` failures; both
  package verifier modes passed with the same v394 SHA256.

Historical v378 full non-Windows release-gate commands:


- `uv run python scripts/build_windows_zip.py --skip-download --out-zip dist/eidp-windows-v378.zip --latest-alias`
  -> wrote `dist/eidp-windows-v378.zip` and refreshed `dist/eidp-windows.zip`;
  both have SHA256
  `bdf1ffbae478ee32a2ae745e34960b32c57dd0b1d0689fc7c1d7d438e5092a2e`.
- `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v378.zip --require-demonstrated-discovery-patterns`
  and `uv run python scripts/verify_windows_distribution.py dist/eidp-windows.zip --require-demonstrated-discovery-patterns`
  -> both `OK core`, with matching SHA256, `44` packaged discovery gold-set
  entries, `17` publication-lag cases, `47` prefecture seeds, and
  `undemonstrated_pattern_sources=[]`.
- `uv run python scripts/run_non_windows_release_gates.py dist/eidp-windows-v378.zip --json --output _temp/v378-non-windows-release-gates.json`
  -> `ok=true`; SHA256 sidecar matched; full unit passed with
  `1385 passed, 5 warnings`; validator/distribution unit tests passed with
  `141 passed`; validator/distribution mypy and Ruff passed; discovery
  gold-set reported `44` entries, `10` strict target-year successes,
  `17` publication-lag cases, and `undemonstrated_pattern_sources=[]`;
  expected-prediction replay returned `44` exact matches / `0` failures; both
  package verifier modes passed with SHA256
  `bdf1ffbae478ee32a2ae745e34960b32c57dd0b1d0689fc7c1d7d438e5092a2e`.
- Windows v378 setup on `C:\Users\<operator>\EIDP-v378-c82af41`:
  transferred `dist/eidp-windows-v378.zip` and its sidecar to
  `C:\Users\<operator>\EIDP-transfer`; Windows SHA256 matched
  `bdf1ffbae478ee32a2ae745e34960b32c57dd0b1d0689fc7c1d7d438e5092a2e`;
  expanded into a separate directory without touching v376;
  `EIDP-setup.bat` completed with build commit
  `c82af41728a91e72cfd661d114d199175213dc9d`, `school_count=2418`,
  `school_fiscal_year_status_count=2418`, `sqlite_integrity_check=ok`,
  `document_unique_indexes` including `uq_document_file_hash`, and
  `wheel_count=78`.
- Windows v378 after-setup validator:
  `.venv\Scripts\python.exe scripts\validate_windows_install.py . --after-setup --json`
  returned `ok=true`, no errors or warnings, the same v378 build commit,
  `master_xlsx_present=true`, `school_count=2418`,
  `school_fiscal_year_status_count=2418`, `sqlite_integrity_check=ok`, and all
  required SQLite tables.
- Windows v378 diagnostics:
  `EIDP-diagnose.bat` wrote
  `logs\diagnostics-20260513-224228.txt`. FY2026 readiness remained below gate
  with `ship_readiness_rc=1`, `strict_target_pdf_schools=0`,
  `operator_reviewable_schools=0`, `excel_ready_schools=0`, and
  `estimated_manual_workload_rate=1.0`. The retroactive FY2025 section recorded
  `is_retroactive_fiscal_year=true`, `extracted_schools=2031`,
  `extracted_rate=0.84`, `retroactive_fiscal_year=2025`, and
  `retroactive_ship_readiness_rc=0`.
- Windows v378 UI service smoke attempt:
  `python -m streamlit version` returned `Streamlit, version 1.57.0`, and
  `import eidp.review.app` returned `app_import_ok`. However, SSH-launched
  `Start-Process` Streamlit attempts did not produce a usable
  `/_stcore/health` response and left empty stdout/stderr logs; follow-up
  process checks reported `remaining_python_processes=0`. Treat v378 UI
  service/browser proof as not yet established.

Latest v376 commands (historical Windows-validated package evidence):

- `uv run pytest tests/unit/test_windows_packaging_spike.py::test_diagnose_bat_collects_operator_evidence_without_mutating_data tests/unit/test_windows_distribution_verifier.py::test_verify_core_zip_rejects_diagnose_without_retroactive_fiscal_year_snapshot tests/unit/test_windows_distribution_verifier.py::test_verify_core_zip_rejects_diagnose_with_parse_time_errorlevel_capture -q`
  -> `3 passed`
- `uv run ruff check scripts/verify_windows_distribution.py tests/unit/test_windows_packaging_spike.py`
  -> `All checks passed`
- `uv run python scripts/build_windows_zip.py --skip-download --out-zip dist/eidp-windows-v376.zip --latest-alias`
  -> wrote `dist/eidp-windows-v376.zip` and refreshed `dist/eidp-windows.zip`; both have SHA256
  `8a7c9575394a37ee55ae8c566059385961cd70b8a06c768738a5529d7be9b2cd`.
- `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v376.zip --require-demonstrated-discovery-patterns`
  and `uv run python scripts/verify_windows_distribution.py dist/eidp-windows.zip --require-demonstrated-discovery-patterns`
  -> both `OK core`, with matching SHA256 and `43` packaged discovery gold-set entries.
- `uv run python scripts/run_non_windows_release_gates.py dist/eidp-windows-v376.zip --json --output _temp/v376-non-windows-release-gates-full.json`
  -> `ok=true`; SHA256 sidecar matched; full unit passed with
  `1377 passed, 5 warnings`; validator/distribution unit tests passed with
  `133 passed`; validator/distribution mypy and Ruff passed; discovery
  gold-set reported `43` entries, `10` strict target-year successes,
  `16` publication-lag cases, and `undemonstrated_pattern_sources=[]`;
  expected-prediction replay returned `43` exact matches / `0` failures; both
  package verifier modes passed with SHA256
  `8a7c9575394a37ee55ae8c566059385961cd70b8a06c768738a5529d7be9b2cd`.
- Windows v376 setup on `C:\Users\<operator>\EIDP-v376-d2402dc`:
  `EIDP-setup.bat` completed; `scripts\validate_install.bat` returned `OK install`;
  `.venv\Scripts\python.exe scripts\validate_windows_install.py . --after-setup --json`
  returned `ok=true`, `school_count=2418`,
  `school_fiscal_year_status_count=2418`, `sqlite_integrity_check=ok`, and
  `document_unique_indexes` including `uq_document_file_hash`.
- Windows v376 diagnostics:
  `EIDP-diagnose.bat` wrote `logs\diagnostics-20260513-211539.txt`; FY2026
  readiness remained below gate with `ship_readiness_rc=1`, while the
  retroactive FY2025 snapshot recorded `is_retroactive_fiscal_year=true`,
  `extracted_schools=2031`, `extracted_rate=0.84`,
  `retroactive_fiscal_year=2025`, and `retroactive_ship_readiness_rc=0`.
- Windows v376 UI service smoke:
  `.venv\Scripts\python.exe -m streamlit run src\eidp\review\app.py
  --server.port 8501 --server.address 127.0.0.1 --server.headless true`
  started successfully; `http://127.0.0.1:8501/_stcore/health` returned
  `200 ok`; the smoke process was stopped, and a follow-up process check found
  no remaining Streamlit process.
- Windows v376 SSH-tunnel UI precheck:
  with the remote Streamlit process held open, `ssh -o ClearAllForwardings=no
  -L 127.0.0.1:18501:127.0.0.1:8501 win` exposed the Windows service to the
  Mac; local `curl http://127.0.0.1:18501/_stcore/health` returned `ok`.
  The tunnel and remote Streamlit processes were then stopped, and a follow-up
  check found no remaining Streamlit process.
- Windows v376 browser render smoke:
  using temporary `playwright-core` under `/tmp` plus the installed local
  Google Chrome binary, the tunneled Windows UI rendered with title
  `EIDP Operator Console`, `body_text_len=3533`, no captured console warnings
  or page errors, and visible operator text including `今週のやること`,
  `① 学校別タスク`, `② PDF確認・手入力`, `③ 年度判定・修正`,
  `④ Excel プレビュー`, `対象年度: 2026年度（令和8年度）`,
  `build: d2402dc`, `対象校 2418`, `Excel出力可 0/2418 校`, and
  `URLなし 2418`. The temporary npm package, script, Chrome profile, and
  screenshot were removed afterward. This proves initial browser rendering, not
  a full click-through of every operator workflow.
- Windows v376 read-only quick-navigation click-through:
  the same tunneled browser path clicked the five non-mutating quick navigation
  buttons and rendered each page without captured console warnings or page
  errors. Verified headings were `① 学校別タスク` with
  `週次URL/PDF再取得` / `次に進める作業`, `PDF確認・手入力`,
  `対象年度の判定・修正`, `Excel プレビュー`, and `設定` with
  `バージョン` / `和暦 alias` / `OCR` / `外部 API`. The script did not click
  acquisition, save, export, or any data-mutating action. Temporary npm files
  were removed afterward.
- Windows v376 Excel preview disabled-state smoke:
  the tunneled browser path opened `④ Excel プレビュー` and verified the
  page rendered with no console warnings or page errors. With current FY2026
  target-year data still empty, the page showed `対象年度PDFあり 0`,
  `Excel出力可 0`, `Excel対象行 0`, `URLなし 2367`, `未採録校 2418`,
  and the operator warning that 2026 target-year transcribed rows are `0`.
  The `プレビュー workbook を生成` button was present but disabled, so the
  UI correctly prevents downloading old-year or empty workbook output.
- Windows v376 retroactive FY2025 Excel preview/download smoke:
  the same installed package was started with
  `EIDP_TARGET_FISCAL_YEAR=2025` and opened through the SSH tunnel. The
  `④ Excel プレビュー` page showed `対象年度: 2025年度（令和7年度）`,
  `抽出済み学校 2031`, `Excel対象行 7150`, and sheet counts
  `採録状況=2418 / 対象比率=10022 / 学科別=9719 / 在籍のみ抜粋=9719`.
  The `プレビュー workbook を生成` button was enabled, generated the in-memory
  workbook, and exposed `Excel ダウンロード`; the browser download produced
  `eidp_master.xlsx` with size `3,728,652` bytes. No browser console warnings
  or page errors were captured, and the temporary npm/download artifacts were
  removed afterward. This proves the Windows UI Excel preview/download path
  works for the retroactive R7 dataset, while FY2026 remains blocked by absent
  current target-year rows.
- Windows v376 ManualActionLog/outbox sandbox smoke:
  a disposable `C:\Users\<operator>\EIDP-v376-audit-sandbox` copied only the
  current v376 SQLite files, ran the package code with `EIDP_APP_ROOT` pointed
  at that sandbox, inserted one `stage6_smoke_manual_action` row via
  `log_manual_action`, committed it, and flushed `manual-actions.jsonl` via
  `flush_audit_outbox`. The smoke reported `inserted_delta=1`,
  `flush_stats={exported: 1, already_present: 0, failed: 0}`,
  `jsonl_exported_at_present=true`, `matching_outbox_rows=1`, and actor
  `codex-stage6-smoke`. The sandbox directory was removed afterward, and the
  current v376 runtime directory was not mutated.
- Windows v376 browser UI audit-outbox flush smoke:
  a second disposable sandbox `C:\Users\<operator>\EIDP-v376-ui-audit-sandbox`
  seeded one unexported `stage6_ui_audit_flush_smoke` `ManualActionLog` row,
  then started the v376 Streamlit UI against that sandbox. Through the SSH
  tunnel, the browser opened `詳細 operator` -> `監査ログ`, verified
  `JSONL outbox 未送信 1`, clicked `Outbox を flush`, and observed
  `exported=1 already_present=0 failed=0` with the row visible as
  `stage6_ui_audit_flush_smoke` by `codex-ui-smoke`. A direct post-UI DB/file
  check reported `pending=0`, `matching_db_rows=1`,
  `matching_exported_rows=1`, `matching_outbox_rows=1`, and `outbox_lines=1`.
  The remote sandbox, Streamlit process, SSH tunnel, and local Playwright temp
  files were removed afterward.
- Windows v376 browser UI URL-candidate review write smoke:
  a disposable `C:\Users\<operator>\EIDP-v376-url-review-sandbox` seeded one
  pending `url_candidate` `ReviewItem` for `日本工学院専門学校` with candidate URL
  `https://example.com/eidp-stage6-url-candidate-smoke`. The v376 Streamlit UI
  was started against that sandbox, and the tunneled browser opened
  `詳細 operator` -> `URL候補レビュー`, confirmed `確認待ち 1 件`, entered reject
  reason `stage6 UI reject smoke`, and clicked `却下`. The UI then showed
  `確認待ちのURL候補はありません。` with no browser console warnings or page
  errors. Direct post-UI DB verification reported `review_items=1`,
  `pending_items=0`, `resolved_rejected_items=1`, `audit_rows=1`, and
  `audit_action_types=["url_candidate_rejected"]`. The sandbox, Streamlit
  process, SSH tunnel, and local Playwright temp directory were removed
  afterward.
- Windows v376 Saitama 5-site bounded backend smoke:
  `bootstrap_pdf_pipeline.py --pref saitama --url-search off
  --school-url-crawl off --skip-known-url-discovery --discovery-methods
  prefecture_aggregator --batch-size 5 --rate-limit 0.1 --request-timeout 10`
  completed on `C:\Users\<operator>\EIDP-v376-d2402dc`. It downloaded the current
  Saitama artifact, extracted `58` rows, matched `51`, added `51`
  `SchoolSite` rows, crawled `5` official-index disclosure sites, found
  candidates on all `5`, downloaded `0` strict FY2026 target PDFs, produced
  `2084` discovery evidence lines, rebuilt `2418` school status rows, and
  reported `operator_reviewable_count=5`,
  `operator_reviewable_yield_pct=0.2`, `target_pdf_auto_yield_pct=0.0`, and
  `ship_gate_status=below_gate`. The progress JSON loaded as valid UTF-8 and
  after-run `validate_windows_install.py --after-setup --json` returned
  `ok=true` with `sqlite_integrity_check=ok`.
- Windows cleanup after v376 proof removed stale
  `C:\Users\<operator>\EIDP-v342-de2cfed` plus old transfer ZIPs
  `eidp-windows-v220.zip`, `v221`, `v222`, and `v375` with their sha256
  sidecars. Remaining EIDP paths are only `EIDP-v376-d2402dc` and
  `EIDP-transfer`; the transfer directory now contains only
  `eidp-windows-v376.zip` and `eidp-windows-v376.zip.sha256`. A follow-up
  process check found no remaining EIDP Streamlit/bootstrap process.

Previously retained v375 commands:

- `uv run pytest tests/unit/test_pdf_discovery.py::test_pdf_link_context_does_not_cross_intervening_non_year_block tests/unit/test_pdf_discovery.py::test_pdf_link_context_skips_update_date_before_heading_year tests/unit/test_pdf_discovery.py::test_prefecture_public_school_page_uses_heading_year_for_old_target_forms -q`
  -> `3 passed`
- `uv run pytest tests/unit/test_pdf_discovery.py::test_prioritize_viable_candidates_prefers_latest_public_stale_target_form tests/unit/test_pdf_discovery.py::test_current_year_syllabus_does_not_outrank_previous_year_target_form tests/unit/test_pdf_discovery.py::test_prioritize_viable_candidates_prefers_current_year_target_over_higher_score_stale_target -q`
  -> `3 passed`
- `uv run ruff check src/eidp/scraper/pdf_discovery.py tests/unit/test_pdf_discovery.py src/eidp/scraper/discovery_gold_set.py tests/unit/test_discovery_gold_set.py tests/unit/test_discovery_gold_set_summary.py tests/unit/test_cli_discovery_gold_set.py tests/unit/test_cli_eval_discovery_gold.py tests/unit/test_discovery_gold_set_eval.py tests/unit/test_discovery_gold_set_seed.py`
  -> `All checks passed`
- `uv run mypy src/eidp/scraper/pdf_discovery.py src/eidp/scraper/discovery_gold_set.py`
  -> `Success: no issues found in 2 source files`
- `uv run pytest tests/unit/test_pdf_discovery.py -q`
  -> `161 passed, 5 warnings`
- `uv run pytest tests/unit/test_discovery_gold_set.py tests/unit/test_discovery_gold_set_summary.py tests/unit/test_cli_discovery_gold_set.py tests/unit/test_cli_eval_discovery_gold.py tests/unit/test_discovery_gold_set_eval.py tests/unit/test_discovery_gold_set_seed.py -q`
  -> `47 passed`
- `uv run ruff check tests/unit/test_discovery_gold_set.py tests/unit/test_discovery_gold_set_summary.py tests/unit/test_cli_discovery_gold_set.py tests/unit/test_cli_eval_discovery_gold.py tests/unit/test_discovery_gold_set_eval.py tests/unit/test_discovery_gold_set_seed.py src/eidp/scraper/discovery_gold_set.py`
  -> `All checks passed`
- `uv run pytest tests/unit -q`
  -> `1377 passed, 5 warnings`
- `uv run eidp discovery-gold-set --json`
  -> `43` entries, `10` strict target-year successes, `16` publication-lag cases, `0` undemonstrated pattern sources.
- `uv run eidp eval-discovery-gold --predictions data/discovery-gold-set/expected-predictions.jsonl --fail-on-regression --json`
  -> `43` exact matches, `0` failed, `0` missing, and `0` unexpected predictions.
- `uv run python scripts/build_windows_zip.py --skip-download --out-zip dist/eidp-windows-v375.zip --latest-alias`
  -> wrote `dist/eidp-windows-v375.zip` and refreshed `dist/eidp-windows.zip`; both have SHA256
  `fa9a7c11f6d2f1efeadc4aa234965d733c8c45862f179e4e82dea65ac177ce4c`.
- `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v375.zip --require-demonstrated-discovery-patterns`
  and `uv run python scripts/verify_windows_distribution.py dist/eidp-windows.zip --require-demonstrated-discovery-patterns`
  -> both `OK core`, with matching SHA256 and `43` packaged discovery gold-set entries.
- `uv run python scripts/run_non_windows_release_gates.py dist/eidp-windows-v375.zip --json --output _temp/v375-non-windows-release-gates-full.json`
  -> `ok=true`, SHA256 sidecar matched, full unit passed with `1377 passed, 5 warnings`, distribution-verifier passed with `133 passed`, package verifier passed, and demonstrated-pattern gate passed.
- `uv run python scripts/run_non_windows_release_gates.py dist/eidp-windows-v375.zip --skip-full-unit --pdf-evidence _temp/win-v342-tokyo-probe/discovery_rejections_tokyo_v342_30.jsonl --pdf-evidence _temp/win-v342-evidence/discovery_rejections.jsonl --pdf-evidence _temp/seijuji-gold-v2/discovery_evidence.jsonl --pdf-evidence _temp/kousei-gold-v2/discovery_evidence.jsonl --pdf-evidence _temp/chuo-gold-v1/discovery_evidence.jsonl --pdf-evidence _temp/kimikan-manual-v2/discovery_evidence.jsonl --json --output _temp/v375-non-windows-release-gates-evidence.json`
  -> `ok=true`, Tokyo evidence `4` exact / `0` failures, Saitama evidence `16` exact / `0` failures, 聖十字 evidence `1` exact / `0` failures, 更生 evidence `1` exact / `0` failures, 中央情報 evidence `1` exact / `0` failures, and 君津 evidence `1` exact / `0` failures. 愛生会, あいち福祉医療, and 尚美 are expectedly absent from those older bounded evidence JSONL files because they were added from fresh manual-web / official-index traces.

Previously retained v359/v358/v357/v342 source/package evidence:

- `uv run pytest tests/unit -q` -> `1366 passed, 5 warnings`
- `uv run pytest tests/unit/test_pdf_discovery.py::test_extract_pdf_links_does_not_assign_visible_sibling_anchor_text_to_empty_anchor tests/unit/test_discovery_gold_set.py tests/unit/test_discovery_gold_set_summary.py tests/unit/test_cli_eval_discovery_gold.py tests/unit/test_cli_discovery_gold_set.py tests/unit/test_discovery_gold_set_eval.py tests/unit/test_discovery_gold_set_seed.py -q`
  -> `47 passed`
- `uv run pytest tests/unit/test_pdf_discovery.py tests/unit/test_discovery_gold_set.py tests/unit/test_discovery_gold_set_summary.py tests/unit/test_cli_eval_discovery_gold.py tests/unit/test_cli_discovery_gold_set.py tests/unit/test_discovery_gold_set_eval.py tests/unit/test_discovery_gold_set_seed.py tests/unit/test_windows_distribution_verifier.py -q`
  -> `290 passed, 5 warnings`
- `uv run ruff check tests/unit/test_discovery_gold_set.py tests/unit/test_discovery_gold_set_summary.py tests/unit/test_cli_eval_discovery_gold.py tests/unit/test_cli_discovery_gold_set.py tests/unit/test_discovery_gold_set_eval.py tests/unit/test_discovery_gold_set_seed.py`
  -> `All checks passed`
- `uv run ruff check src/eidp/scraper/pdf_discovery.py tests/unit/test_pdf_discovery.py tests/unit/test_discovery_gold_set.py tests/unit/test_discovery_gold_set_summary.py tests/unit/test_cli_eval_discovery_gold.py tests/unit/test_cli_discovery_gold_set.py tests/unit/test_discovery_gold_set_eval.py tests/unit/test_discovery_gold_set_seed.py`
  -> `All checks passed`
- `uv run mypy src/eidp/scraper/pdf_discovery.py`
  -> `Success: no issues found in 1 source file`
- Current Tokyo Anime HTML extraction probe:
  `_extract_pdf_links` against `https://www.anime.ac.jp/school/public_info/`
  -> emitted visible `11_confirmation_application.pdf` and `12_kakunin.pdf`
  candidates, and did not emit the commented-out `07_study_support_application.pdf`.
- Source-side 君津 one-school replay:
  `discover-pdfs --discovery-method discovery_gold_set --school-id 798`
  -> `crawled=1`, `found=1`, `downloaded=1`, `failed=0`, `skipped=0`,
  evidence `reason=accepted_downloaded`, `year_evidence=url_hint`,
  `pattern_type=direct`, `pdf_type=target`, and visible-anchor-local context.
- `uv run python -m eidp.cli eval-discovery-gold --pdf-evidence _temp/kimikan-manual-v2/discovery_evidence.jsonl --json`
  -> `1` exact / `0` failures for `kimikan-nursing-empty-anchor-accepted-2026`
- `uv run python scripts/build_windows_zip.py --skip-download --out-zip dist/eidp-windows-v357.zip`
  -> wrote `dist/eidp-windows-v357.zip` and checksum sidecar.
- `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v357.zip`
  -> `OK core`, build commit
  `aa10c8982a4b7f67a5a10509bbd86dbfee462b21`, `git_dirty=false`,
  `discovery_gold_set_entries=36`, `discovery_gold_expected_predictions=36`,
  `discovery_gold_undemonstrated_pattern_sources=[]`,
  `discovery_gold_pattern_sources={'direct': 5, 'embed': 1, 'wordpress': 4, 'wordpress_download_manager': 1}`,
  SHA256 `5385dd9395e295bc31b31193fd7582bd0df3678d7f6bc39abd845a6bfb32952f`.
- `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v357.zip --require-demonstrated-discovery-patterns`
  -> `OK core`, with `discovery_gold_undemonstrated_pattern_sources=[]`.
- `uv run python scripts/run_non_windows_release_gates.py dist/eidp-windows-v357.zip --json --output _temp/v357-non-windows-release-gates-full.json`
  -> `ok=true`, SHA256 sidecar matched, full unit passed, and all non-Windows gates passed.
- `uv run python scripts/run_non_windows_release_gates.py dist/eidp-windows-v357.zip --skip-full-unit --pdf-evidence _temp/win-v342-tokyo-probe/discovery_rejections_tokyo_v342_30.jsonl --pdf-evidence _temp/win-v342-evidence/discovery_rejections.jsonl --pdf-evidence _temp/seijuji-gold-v2/discovery_evidence.jsonl --pdf-evidence _temp/kousei-gold-v2/discovery_evidence.jsonl --pdf-evidence _temp/chuo-gold-v1/discovery_evidence.jsonl --pdf-evidence _temp/kimikan-manual-v2/discovery_evidence.jsonl --json --output _temp/v357-non-windows-release-gates-evidence.json`
  -> `ok=true`, Tokyo evidence `4` exact / `0` failures, Saitama evidence `16` exact / `0` failures, 聖十字 evidence `1` exact / `0` failures, 更生 evidence `1` exact / `0` failures, 中央情報 evidence `1` exact / `0` failures, and 君津 evidence `1` exact / `0` failures.

Previously retained v354 source/package evidence:

- `uv run pytest tests/unit -q` -> `1364 passed, 5 warnings`
- `uv run pytest tests/unit/test_pdf_discovery.py tests/unit/test_discovery_gold_set.py tests/unit/test_discovery_gold_set_summary.py tests/unit/test_cli_eval_discovery_gold.py tests/unit/test_cli_discovery_gold_set.py tests/unit/test_discovery_gold_set_eval.py tests/unit/test_discovery_gold_set_seed.py tests/unit/test_windows_distribution_verifier.py -q`
  -> `288 passed, 5 warnings`
- `uv run ruff check src/eidp/scraper/pdf_discovery.py tests/unit/test_pdf_discovery.py tests/unit/test_discovery_gold_set.py tests/unit/test_discovery_gold_set_summary.py tests/unit/test_cli_eval_discovery_gold.py tests/unit/test_cli_discovery_gold_set.py tests/unit/test_discovery_gold_set_eval.py tests/unit/test_discovery_gold_set_seed.py`
  -> `All checks passed`
- `uv run mypy src/eidp/scraper/pdf_discovery.py`
  -> `Success: no issues found in 1 source file`
- Source-side 更生 one-school replay:
  `discover-pdfs --discovery-method discovery_gold_set --school-id 1375`
  -> `crawled=1`, `found=1`, `downloaded=1`, `failed=0`, `skipped=0`,
  evidence `reason=accepted_downloaded`, `year_evidence=url_hint`,
  `pattern_type=direct`, `pdf_type=target`, and local `dd` anchor context.
- `uv run python -m eidp.cli eval-discovery-gold --pdf-evidence _temp/kousei-gold-v2/discovery_evidence.jsonl --json`
  -> `1` exact / `0` failures for `kousei-nursing-support-accepted-2026`
- `uv run python scripts/build_windows_zip.py --skip-download --out-zip dist/eidp-windows-v354.zip`
  -> wrote `dist/eidp-windows-v354.zip` and checksum sidecar.
- `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v354.zip`
  -> `OK core`, build commit
  `0ee34c6cbaf9a8c4f6dd1d7712a0ee51b758afb9`, `git_dirty=false`,
  `discovery_gold_set_entries=34`, `discovery_gold_expected_predictions=34`,
  `discovery_gold_undemonstrated_pattern_sources=[]`,
  `discovery_gold_pattern_sources={'direct': 4, 'embed': 1, 'wordpress': 3, 'wordpress_download_manager': 1}`,
  SHA256 `95ed537dc21beb52add6b31df0705ec9a6528c272354da68783f362b27b55dc4`.
- `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v354.zip --require-demonstrated-discovery-patterns`
  -> `OK core`, with `discovery_gold_undemonstrated_pattern_sources=[]`.
- `uv run python scripts/run_non_windows_release_gates.py dist/eidp-windows-v354.zip --json --output _temp/v354-non-windows-release-gates-full.json`
  -> `ok=true`, SHA256 sidecar matched, full unit passed, and all non-Windows gates passed.
- `uv run python scripts/run_non_windows_release_gates.py dist/eidp-windows-v354.zip --skip-full-unit --pdf-evidence _temp/win-v342-tokyo-probe/discovery_rejections_tokyo_v342_30.jsonl --pdf-evidence _temp/win-v342-evidence/discovery_rejections.jsonl --pdf-evidence _temp/seijuji-gold-v2/discovery_evidence.jsonl --pdf-evidence _temp/kousei-gold-v2/discovery_evidence.jsonl --json --output _temp/v354-non-windows-release-gates-evidence.json`
  -> `ok=true`, Tokyo evidence `4` exact / `0` failures, Saitama evidence `16` exact / `0` failures, 聖十字 evidence `1` exact / `0` failures, and 更生 evidence `1` exact / `0` failures.

- `uv run pytest tests/unit -q` -> `1363 passed, 5 warnings`
- `uv run python -m eidp.cli db-info`
  -> clean `rc=2` when the local SQLite file has no schema, with no traceback and an operator-actionable setup/import message
- `uv run pytest tests/unit/test_non_windows_release_gates.py -q`
  -> `8 passed`
- `uv run mypy scripts/run_non_windows_release_gates.py`
  -> `Success: no issues found in 1 source file`
- `uv run ruff check scripts/run_non_windows_release_gates.py tests/unit/test_non_windows_release_gates.py`
  -> `All checks passed`
- `uv run python scripts/run_non_windows_release_gates.py dist/eidp-windows-v353.zip --json --output _temp/v353-non-windows-release-gates-full.json`
  -> `ok=true`, SHA256 sidecar matched, full unit passed, and all non-Windows gates passed
- `uv run python scripts/run_non_windows_release_gates.py dist/eidp-windows-v353.zip --skip-full-unit --pdf-evidence _temp/win-v342-tokyo-probe/discovery_rejections_tokyo_v342_30.jsonl --pdf-evidence _temp/win-v342-evidence/discovery_rejections.jsonl --pdf-evidence _temp/seijuji-gold-v2/discovery_evidence.jsonl --json --output _temp/v353-non-windows-release-gates-evidence.json`
  -> `ok=true`, Tokyo evidence `4` exact / `0` failures, Saitama evidence `16` exact / `0` failures, 聖十字 evidence `1` exact / `0` failures;
  pdf-evidence replay gates allow bounded missing entries but fail on failed/unexpected predictions
- `EIDP_DATABASE_URL=sqlite:///$PWD/_temp/v348-mac-tokyo20/eidp.sqlite3 uv run python -m eidp.cli report ship-readiness --json`
  -> `ok=false`, `total_schools=2418`, `strict_target_pdf_rate=0.0`,
  `operator_reviewable_rate=0.019`, `excel_ready_rate=0.0`
- `uv run pytest tests/unit/test_pdf_discovery.py tests/unit/test_discovery_gold_set.py tests/unit/test_discovery_gold_set_summary.py tests/unit/test_cli_discovery_gold_set.py tests/unit/test_windows_distribution_verifier.py -q` -> `247 passed, 5 warnings`
- `uv run pytest tests/unit/test_windows_distribution_verifier.py -q` -> `89 passed`
- `uv run pytest tests/unit/test_windows_install_validator.py tests/unit/test_windows_distribution_verifier.py -q`
  -> `131 passed`
- `uv run mypy scripts/validate_windows_install.py scripts/verify_windows_distribution.py`
  -> `Success: no issues found in 2 source files`
- `uv run ruff check scripts/validate_windows_install.py scripts/verify_windows_distribution.py tests/unit/test_windows_install_validator.py tests/unit/test_windows_distribution_verifier.py`
  -> `All checks passed`
- `uv run pytest tests/unit/test_pdf_discovery.py tests/unit/test_url_discovery.py tests/unit/test_url_normalization.py tests/unit/test_discovery_gold_set.py tests/unit/test_discovery_gold_set_eval.py tests/unit/test_cli_eval_discovery_gold.py tests/unit/test_discovery_gold_set_summary.py -q` -> `206 passed, 5 warnings`
- `uv run pytest tests/unit/test_review_excel_preview.py tests/unit/test_excel_exporter.py tests/unit/test_windows_distribution_verifier.py -q` -> `96 passed`
- `uv run ruff check src/eidp/review/_pages/excel_preview.py tests/unit/test_review_excel_preview.py` -> `All checks passed`
- `uv run pytest tests/unit/test_discovery_gold_set.py tests/unit/test_discovery_gold_set_summary.py tests/unit/test_discovery_gold_set_seed.py tests/unit/test_discovery_gold_set_eval.py tests/unit/test_cli_discovery_gold_set.py tests/unit/test_cli_eval_discovery_gold.py -q` -> `46 passed`
- `uv run pytest tests/unit/test_discovery_gold_set.py tests/unit/test_discovery_gold_set_summary.py tests/unit/test_discovery_gold_set_eval.py tests/unit/test_cli_eval_discovery_gold.py -q` -> `36 passed`
- `uv run ruff check src/eidp/scraper/pdf_discovery.py src/eidp/scraper/discovery_evidence_summary.py src/eidp/scraper/discovery_gold_set.py tests/unit/test_pdf_discovery.py tests/unit/test_discovery_evidence_summary.py tests/unit/test_cli_eval_discovery_gold.py` -> `All checks passed`
- `uv run ruff check tests/unit/test_discovery_gold_set.py tests/unit/test_discovery_gold_set_summary.py` -> `All checks passed`
- `uv run ruff check src/eidp/config.py src/eidp/scraper/pdf_discovery.py src/eidp/scraper/discovery_gold_set.py scripts/verify_windows_distribution.py tests/unit/test_pdf_discovery.py tests/unit/test_discovery_gold_set.py tests/unit/test_cli_discovery_gold_set.py tests/unit/test_windows_distribution_verifier.py` -> `All checks passed`
- `uv run eidp discovery-gold-set --json` -> `32` entries,
  `accepted_target_pdf=4`, `needs_operator_review=15`,
  `publication_lag_latest_public=11`, `strict_target_year_successes=4`
- `uv run eidp eval-discovery-gold --predictions data/discovery-gold-set/expected-predictions.jsonl --fail-on-regression --json` -> `32` exact, `0` failures
- `uv run eidp eval-discovery-gold --pdf-evidence _temp/win-v342-tokyo-probe/discovery_rejections_tokyo_v342_30.jsonl --json` -> `4` exact, `0` failures for the Tokyo entries present in the bounded run, including `pattern_type`
- `uv run eidp eval-discovery-gold --pdf-evidence _temp/win-v342-evidence/discovery_rejections.jsonl --json` -> `16` exact, `0` failures for the Saitama evidence entries present in the bounded run
- `uv run python` bounded live HTML scan over `160` official-index school URLs
  from the v342 Tokyo/Saitama evidence SQLite DBs -> pattern sources observed:
  `direct=37059`, `wordpress=857`, `cache_busted=52`; observed examples for
  the six undemonstrated sources remained `0`. The scan wrote its local
  summary to `_temp/v345-pattern-source-live-scan-summary.json`.
- `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v342.zip` -> `OK core`
- `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v342.zip --require-demonstrated-discovery-patterns` -> expected failure for the six remaining undemonstrated sources
- `uv run python scripts/build_windows_zip.py --skip-download --out-zip dist/eidp-windows-v350.zip`
  -> wrote `dist/eidp-windows-v350.zip` and checksum sidecar.
- `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v350.zip`
  -> `OK core`, build commit
  `ac54605b0a57b94fe4b0467a74f942f3919b4f0f`, `git_dirty=false`,
  `discovery_gold_set_entries=32`, `discovery_gold_expected_predictions=32`,
  `discovery_gold_undemonstrated_pattern_sources=[]`,
  `discovery_gold_pattern_sources={'direct': 3, 'embed': 1, 'wordpress': 2, 'wordpress_download_manager': 1}`,
  SHA256 `f6c450576202409f82e524f708b62ae6174e70281e87cf411022bc8109fc6dae`.
- `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v350.zip --require-demonstrated-discovery-patterns`
  -> `OK core`, with `discovery_gold_undemonstrated_pattern_sources=[]`.
- `uv run python scripts/build_windows_zip.py --skip-download --out-zip dist/eidp-windows-v351.zip`
  -> wrote `dist/eidp-windows-v351.zip` and checksum sidecar.
- `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v351.zip`
  -> `OK core`, build commit
  `90b64c583080011bb2cd94053fe82a51b0d66ca7`, `git_dirty=false`,
  `discovery_gold_set_entries=32`, `discovery_gold_expected_predictions=32`,
  `discovery_gold_undemonstrated_pattern_sources=[]`,
  `discovery_gold_pattern_sources={'direct': 3, 'embed': 1, 'wordpress': 2, 'wordpress_download_manager': 1}`,
  SHA256 `e97d1e58360e87ededa219846a80145aed0242a5d1d1f1f6d64a6403476a94fc`.
- `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v351.zip --require-demonstrated-discovery-patterns`
  -> `OK core`, with `discovery_gold_undemonstrated_pattern_sources=[]`.
- `uv run python scripts/build_windows_zip.py --skip-download --out-zip dist/eidp-windows-v352.zip`
  -> wrote `dist/eidp-windows-v352.zip` and checksum sidecar.
- `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v352.zip`
  -> `OK core`, build commit
  `8f385f86e5a976b913d777ea80b56c00dc1c5ae7`, `git_dirty=false`,
  `discovery_gold_set_entries=32`, `discovery_gold_expected_predictions=32`,
  `discovery_gold_undemonstrated_pattern_sources=[]`,
  `discovery_gold_pattern_sources={'direct': 3, 'embed': 1, 'wordpress': 2, 'wordpress_download_manager': 1}`,
  SHA256 `2a8716d79cf2fcb42397bb126d90222ccf63e7fe72e38a3e303c5f9f6fbb5f25`.
- `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v352.zip --require-demonstrated-discovery-patterns`
  -> `OK core`, with `discovery_gold_undemonstrated_pattern_sources=[]`.
- `uv run python scripts/build_windows_zip.py --skip-download --out-zip dist/eidp-windows-v353.zip`
  -> wrote `dist/eidp-windows-v353.zip` and checksum sidecar.
- `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v353.zip`
  -> `OK core`, build commit
  `b75eecd60d0417369f58cc17f298e288c1f2d251`, `git_dirty=false`,
  `discovery_gold_set_entries=33`, `discovery_gold_expected_predictions=33`,
  `discovery_gold_undemonstrated_pattern_sources=[]`,
  `discovery_gold_pattern_sources={'direct': 3, 'embed': 1, 'wordpress': 3, 'wordpress_download_manager': 1}`,
  SHA256 `9c68738c78ded416c84696fb78606f29767c9fe4f566747f42db802cb8a827de`.
- `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v353.zip --require-demonstrated-discovery-patterns`
  -> `OK core`, with `discovery_gold_undemonstrated_pattern_sources=[]`.
- Source-side v348 strict Tokyo repeat on a copy of the v342 Tokyo aggregate DB:
  `EIDP_DATABASE_URL=sqlite:///$PWD/_temp/v348-mac-tokyo20/eidp.sqlite3 EIDP_DATA_DIR=$PWD/_temp/v348-mac-tokyo20/data uv run eidp discover-pdfs --storage-dir _temp/v348-mac-tokyo20/pdfs --batch-size 20 --rate-limit 0.2 --request-timeout 12 --discovery-method prefecture_aggregator --evidence-log _temp/v348-mac-tokyo20/discovery_rejections.jsonl`
  -> `crawled=20`, `found=20`, `downloaded=0`, `failed=4`,
  `skipped=404`, `cached_rejections=125`, `prefiltered=229`,
  `candidate_budget_limited=1`, `candidate_budget_dropped=6`,
  `rejection_reason_pre_filtered_non_target_hint=351`,
  `rejection_reason_fiscal_year_mismatch=62`,
  `rejection_reason_classified_non_target=34`,
  `rejection_reason_target_fiscal_year_not_detected=10`,
  `rejection_reason_http_error_httpstatuserror=3`, and
  `rejection_reason_not_pdf_magic=2`.
- `EIDP_DATABASE_URL=sqlite:///$PWD/_temp/v348-mac-tokyo20/eidp.sqlite3 uv run eidp summarize-discovery-evidence --evidence-log _temp/v348-mac-tokyo20/discovery_rejections.jsonl --discovery-method prefecture_aggregator --json`
  -> `468` evidence rows, pattern sources `direct=394`, `wordpress=39`,
  `cache_busted=35`, PDF type counts `target=66`, `image_only=6`,
  `non_target=385`, `unknown=5`, and `null=6`. Among the `20` crawled
  schools with evidence, buckets are `publication_lag_or_old_target_pdf=15`,
  `target_form_without_year_evidence=1`, and `non_target_candidates_only=4`.
  The command also reports `no_evidence=263` for Tokyo official-index sites
  that were in the copied aggregate DB but outside this `batch_size=20` smoke.

Post-v342 source-side gold-set expansion:

- Four Tokyo source/evidence rows have been promoted to committed discovery
  gold-set entries:
  東京俳優・映画＆放送専門学校 `conf-apl.pdf`,
  東京ダンス・俳優＆舞台芸術専門学校 `check-da.pdf`, and
  東京メディカル・スポーツ専門学校 `support2024.pdf`, plus the source-side
  v348 Tokyo Sanko publication-lag case for
  東京医療秘書歯科衛生＆IT専門学校 `yoshiki2025.pdf`.
- `uv run eidp discovery-gold-set --json` now reports `32` entries:
  `accepted_target_pdf=4`, `needs_operator_review=15`,
  `publication_lag_latest_public=11`, `no_target_candidate_found=1`,
  and `site_fetch_error=1`.
- `uv run eidp eval-discovery-gold --predictions data/discovery-gold-set/expected-predictions.jsonl --fail-on-regression --json`
  now reports `32` exact predictions with `0` failures.
- `uv run eidp eval-discovery-gold --pdf-evidence _temp/win-v342-tokyo-probe/discovery_rejections_tokyo_v342_30.jsonl --json`
  now reports `4` exact predictions with `0` failures. The remaining `28`
  missing entries are outside the Tokyo 30-site sample.
- This source-side evidence, the Excel preview threshold-label fix, and the
  Tokyo pattern-type regression contract, the Tokyo Sanko publication-lag
  regression, and the default isolation of synthetic-only extractor sources are
  packaged into the new Mac-verifier-clean `dist/eidp-windows-v351.zip`.
  It still requires a future Windows extraction
  and setup run before it can replace v342 as Windows-setup-proven.

v351 verifier exposes the current production-pattern demonstration status:

- Discovery gold-set entries: `32`
- Outcome distribution: `accepted_target_pdf=4`, `needs_operator_review=15`,
  `no_target_candidate_found=1`, `publication_lag_latest_public=11`,
  `site_fetch_error=1`
- Demonstrated extractor sources: `direct` (3), `embed` (1), `wordpress` (2),
  `wordpress_download_manager` (1)
- Production-tracked undemonstrated sources: none
- Experimental-only, default-disabled sources: `data_attribute`, `form_action`,
  `input_control`, `meta_refresh`, `onclick`, `select_option`

## Current Windows Backend Evidence

Commands and observations from `ssh win` for v342 setup and targeted discovery
probe:

- Uploaded `dist/eidp-windows-v342.zip` to
  `C:\Users\<operator>\eidp-windows-v342.zip`.
- Windows `Get-FileHash -Algorithm SHA256` ->
  `8eb3fcb785f8dbbeebc008f710af7f58bf4d91fcd4d53958b6f519a6b934b593`.
- Extracted to `C:\Users\<operator>\EIDP-v342-de2cfed`.
- `scripts\first_setup.bat` -> exit `0`; core and after-setup validators
  returned `0`, reported commit `de2cfed4f2a0f1834bc76368438bda3d80ff8413`,
  `build_dirty=false`, `school_count=2418`,
  `school_fiscal_year_status_count=2418`, `sqlite_integrity_check=ok`,
  required SQLite tables present, `department_change` void columns present,
  and `uq_document_file_hash` present.
- Windows package-local targeted Kanto probe for
  `https://kanto-koudai.com/school/#information` reports
  `best_score=2.5`,
  `best_url=https://kanto-koudai.com/school/johokokai/j2024_05a.pdf`,
  `download_pdf_type=image_only`, and
  `download_reason=fiscal_year_mismatch:2024`. The SSH console rendered the
  Japanese anchor text as mojibake, but the URL/ranking/rejection outcome proves
  the backend behavior.
- Windows package-local targeted Iruma probe for
  `https://www.i-heiseigakuen.ac.jp/kokai/` follows the application-form page
  to the WordPress Download Manager wrapper. The best candidate is
  `https://i-heiseigakuen.ac.jp/download/yousiki2/?wpdmdl=5471&refresh=...`,
  `pattern_type=wordpress_download_manager`, and strict download now rejects it
  as `target` / `fiscal_year_mismatch:2024` instead of
  `target_fiscal_year_not_detected`. The SSH console rendered the Japanese
  `様式２（R6年度分申請）` package title as mojibake, but the rejection outcome
  proves the year-context repair in the packaged runtime.

Latest bounded bootstrap evidence is v342:

Commands and observations from `ssh win` for v342 setup/bootstrap:

- `scripts\bootstrap_pdfs.bat --pref saitama --skip-known-url-discovery --url-search off --school-url-crawl off --batch-size 50 --rate-limit 0.2 --request-timeout 15` -> exit `0`.
- Official Saitama artifact downloaded; aggregate `extracted=58`,
  `matched=51`, `added=51`, `review_items=2`.
- PDF discovery: `crawled=50`, `found=49`, `downloaded=0`, `failed=3`,
  `skipped=1391`, `prefiltered=1055`, `cached_rejections=285`,
  `candidate_school_mismatch=5160`, `candidate_budget_dropped=855`,
  `rejection_reason_discovery_error=1`,
  `rejection_reason_pre_filtered_non_target_hint=1062`,
  `rejection_reason_fiscal_year_mismatch=328`,
  `rejection_reason_target_fiscal_year_not_detected=31`,
  `rejection_reason_unsafe_url=1`.
- Ingest: `processed=0`, `departments_created=0`, `yearly_upserted=0`,
  `skipped=0`.
- Rebuilt status: `excel_ready=0`, `target_pdf_auto_acquired_count=0`,
  `operator_reviewable_count=46`, `operator_reviewable_yield_pct=1.9`,
  `ship_gate_status=below_gate`.
- Diagnostics after bootstrap:
  `validate_after_bootstrap_rc=0`,
  `validate_after_bootstrap_ship_gate_rc=1`.
- Local evidence snapshot was pulled to `_temp/win-v342-evidence/`, including
  `bootstrap-pdfs-20260513-072137.log`, `bootstrap-pdfs-20260513-072137.json`,
  `bootstrap-20260513_073824-discovery-rca-batch-plan.json`,
  `discovery_rejections.jsonl`, and `eidp.sqlite3`.
- v342 evidence confirms Kanto is no longer dropped by neighboring disclosure-card
  noise: `j2024_05a.pdf` appears with `score=2.5`, `pdf_type=image_only`,
  and `reason=fiscal_year_mismatch:2024`; the status cache records school `783`
  as `target_year_unverified`.
- v342 evidence confirms the Iruma WordPress Download Manager context repair:
  `wpdmdl=5471` carries `様式２（R6年度分申請）` in `anchor_text` and is rejected
  as `target` / `fiscal_year_mismatch:2024`; the status cache records school
  `760` as `publication_lag`.
- `uv run eidp eval-discovery-gold --pdf-evidence _temp/win-v342-evidence/discovery_rejections.jsonl --json`
  reports `16` exact predictions, `0` failed predictions, and `12` missing
  entries outside the bounded Saitama sample.
- SQLite status rows from the v342 evidence DB: `none=2372`,
  `publication_lag=38`, `target_year_unverified=8`.
- Reproducible scoped summary command:
  `EIDP_DATABASE_URL=sqlite:///$PWD/_temp/win-v342-evidence/eidp.sqlite3 uv run eidp summarize-discovery-evidence --evidence-log _temp/win-v342-evidence/discovery_rejections.jsonl --discovery-method prefecture_aggregator --json`.
  It reports Saitama official-index scope `51` schools with
  `publication_lag_or_old_target_pdf=38`, `target_form_without_year_evidence=8`,
  `non_target_candidates_only=3`, `site_fetch_error_only=1`, and
  `no_evidence=1`. The `no_evidence` row is the one official-index site outside
  the bounded `batch_size=50` smoke: 埼玉福祉保育医療製菓調理専門学校
  (`school_id=2399`).
- The v342 RCA batch plan has `10` items / `50` total candidates. Bucket split:
  `target_form_without_year_evidence=8`, `non_target_candidates_only=2`.
  Representative rows show that the low strict yield is dominated by forms that
  are visible but cannot prove FY2026 from PDF/link evidence: 埼玉コンピュータ＆
  医療事務専門学校 `補正➅確認申請書（様式第2号）.pdf`,
  専門学校埼玉自動車大学校 `koutoumusyou.pdf`, 上尾中央看護専門学校
  `study_support_system.pdf`, 中央情報専門学校 `youshiki2.pdf`, and
  さいたま看護専門学校 `申請書_0602_資料A.pdf`. The two non-target-only packets
  are 大川学園医療福祉専門学校 (old-year image-only form evidence) and
  呉竹医療専門学校 (self-evaluation reports).

Additional v342 Tokyo official-index probe:

- `scripts\bootstrap_pdfs.bat --pref tokyo --skip-known-url-discovery --url-search off --school-url-crawl off --skip-discover --rate-limit 0.2 --request-timeout 15`
  -> exit `0`.
- Official Tokyo artifact downloaded from
  `https://www.seikatubunka.metro.tokyo.lg.jp/documents/d/seikatubunka/12syugakushien_kakuninko_ichiran_260401_1341`;
  aggregate `extracted=243`, `matched=232`, `added=232`, `skipped=11`.
- A targeted 30-site discovery run over the first Tokyo
  `prefecture_aggregator` sites used:
  `eidp.exe discover-pdfs --discovery-method prefecture_aggregator --batch-size 30 --rate-limit 0.2 --request-timeout 15 --evidence-log output\discovery_rejections_tokyo_v342_30.jsonl --school-id ...`
  -> exit `0`.
- PDF discovery: `crawled=30`, `found=30`, `downloaded=0`, `failed=5`,
  `skipped=524`, `cached_rejections=88`, `prefiltered=293`,
  `candidate_budget_limited=1`, `candidate_budget_dropped=6`,
  `candidate_school_mismatch=1`, `rejection_reason_pre_filtered_non_target_hint=371`,
  `rejection_reason_fiscal_year_mismatch=76`,
  `rejection_reason_target_fiscal_year_not_detected=19`,
  `rejection_reason_classified_non_target=118`,
  `rejection_reason_http_error_httpstatuserror=3`,
  `rejection_reason_not_pdf_magic=2`, and `rejection_reason_unsafe_url=2`.
- Local evidence snapshot was pulled to `_temp/win-v342-tokyo-probe/`,
  including `discovery_rejections_tokyo_v342_30.jsonl`,
  `eidp-after-tokyo-aggregate.sqlite3`, and
  `eidp-after-tokyo-discover.sqlite3`.
- Reproducible summary command:
  `EIDP_DATABASE_URL=sqlite:///$PWD/_temp/win-v342-tokyo-probe/eidp-after-tokyo-discover.sqlite3 uv run eidp summarize-discovery-evidence --evidence-log _temp/win-v342-tokyo-probe/discovery_rejections_tokyo_v342_30.jsonl --json`.
  It reports `598` evidence rows, `30` schools with evidence, PDF type counts
  `target=80`, `image_only=15`, `non_target=490`, `unknown=7`, and `null=6`,
  and school bucket counts `publication_lag_or_old_target_pdf=19`,
  `target_form_without_year_evidence=6`, `non_target_candidates_only=5`.
- Reproducible RCA command:
  `EIDP_DATABASE_URL=sqlite:///$PWD/_temp/win-v342-tokyo-probe/eidp-after-tokyo-discover.sqlite3 uv run eidp discovery-rca-batch-plan --evidence-log _temp/win-v342-tokyo-probe/discovery_rejections_tokyo_v342_30.jsonl --limit 10 --json`.
  Representative target-form-without-year-evidence rows are
  東京俳優・映画＆放送専門学校 `conf-apl.pdf`,
  東京ダンス・俳優＆舞台芸術専門学校 `check-da.pdf`, and
  東京メディカル・スポーツ専門学校 `support2024.pdf`.
- The Tokyo sample reinforces the Saitama result: official-index URL seeding is
  functioning, and low strict yield is currently dominated by publication lag,
  stale target forms, image-only / no-year target forms, and non-target
  disclosure PDFs rather than by a missing official-index URL pipeline.

Superseded bounded bootstrap evidence from v341:

Commands and observations from `ssh win` for v341 setup/bootstrap:

- `scripts\bootstrap_pdfs.bat --pref saitama --skip-known-url-discovery --url-search off --school-url-crawl off --batch-size 50 --rate-limit 0.2 --request-timeout 15` -> exit `0`.
- Official Saitama artifact downloaded; aggregate `extracted=58`,
  `matched=51`, `added=51`, `review_items=2`.
- PDF discovery: `crawled=50`, `found=49`, `downloaded=0`, `failed=3`,
  `skipped=1391`, `prefiltered=1055`, `cached_rejections=285`,
  `candidate_school_mismatch=5160`, `candidate_budget_dropped=855`,
  `rejection_reason_discovery_error=1`,
  `rejection_reason_pre_filtered_non_target_hint=1062`,
  `rejection_reason_fiscal_year_mismatch=327`,
  `rejection_reason_target_fiscal_year_not_detected=32`,
  `rejection_reason_unsafe_url=1`.
- Ingest: `processed=0`, `departments_created=0`, `yearly_upserted=0`,
  `skipped=0`.
- Rebuilt status: `excel_ready=0`, `target_pdf_auto_acquired_count=0`,
  `operator_reviewable_count=45`, `operator_reviewable_yield_pct=1.9`,
  `ship_gate_status=below_gate`.
- Diagnostics after bootstrap:
  `validate_after_bootstrap_rc=0`,
  `validate_after_bootstrap_ship_gate_rc=1`.
- Local evidence snapshot was pulled to `_temp/win-v341-evidence/`, including
  `bootstrap-pdfs-20260513-064933.log`, `bootstrap-pdfs-20260513-064933.json`,
  `bootstrap-20260513_070621-discovery-rca-batch-plan.json`,
  `discovery_rejections.jsonl`, and `eidp.sqlite3`.
- v341 evidence confirms Kanto is no longer dropped by neighboring disclosure-card
  noise: `j2024_05a.pdf` appears with `score=2.5`, `pdf_type=image_only`,
  and `reason=fiscal_year_mismatch:2024`.

Superseded bounded bootstrap evidence from v340:

Commands and observations from `ssh win` for v340 setup/bootstrap:

- Uploaded `dist/eidp-windows-v340.zip` to
  `C:\Users\<operator>\eidp-windows-v340.zip`.
- Windows `Get-FileHash -Algorithm SHA256` ->
  `4d774c10c5b0743c3eff22ac224489407f06f3653d081c7133ba8ecbed56405e`.
- Extracted to `C:\Users\<operator>\EIDP-v340-2097ad6`.
- `scripts\first_setup.bat` -> exit `0`; core and after-setup validators
  returned `0`, reported commit `2097ad6ac6f80c236494f4fa439e0c2113302920`,
  `build_dirty=false`, `school_count=2418`,
  `school_fiscal_year_status_count=2418`, `sqlite_integrity_check=ok`,
  required SQLite tables present, `department_change` void columns present,
  and `uq_document_file_hash` present.
- `scripts\bootstrap_pdfs.bat --pref saitama --skip-known-url-discovery --url-search off --school-url-crawl off --batch-size 50 --rate-limit 0.2 --request-timeout 15` -> exit `0`.
- Official Saitama artifact downloaded; aggregate `extracted=58`,
  `matched=51`, `added=51`, `review_items=2`.
- PDF discovery: `crawled=50`, `found=49`, `downloaded=0`, `failed=4`,
  `skipped=1387`, `prefiltered=1055`, `cached_rejections=286`,
  `candidate_school_mismatch=5160`, `candidate_budget_dropped=853`,
  `rejection_reason_discovery_error=1`,
  `rejection_reason_pre_filtered_non_target_hint=1060`,
  `rejection_reason_fiscal_year_mismatch=330`,
  `rejection_reason_target_fiscal_year_not_detected=31`,
  `rejection_reason_unsafe_url=1`.
- Ingest: `processed=0`, `departments_created=0`, `yearly_upserted=0`,
  `skipped=0`.
- Rebuilt status: `excel_ready=0`, `target_pdf_auto_acquired_count=0`,
  `operator_reviewable_count=45`, `operator_reviewable_yield_pct=1.9`,
  `ship_gate_status=below_gate`.
- SQLite status rows: `none=2373`, `publication_lag=38`,
  `target_year_unverified=7`; the seven 年度未確認候補 schools are
  上尾中央看護専門学校, 浦和専門学校, 大宮歯科衛生士専門学校,
  公益社団法人地域医療振興協会さいたま看護専門学校,
  埼玉コンピュータ＆医療事務専門学校, 専門学校埼玉自動車大学校,
  and 中央情報専門学校.
- Diagnostics after bootstrap:
  `validate_core_rc=0`, `validate_after_setup_rc=0`,
  `validate_after_bootstrap_rc=0`,
  `validate_after_bootstrap_ship_gate_rc=1`.
- ARS/アルスコンピュータ evidence in `discovery_rejections.jsonl`:
  the R7 target-form PDF is rejected as `fiscal_year_mismatch:2025`, while
  current-year `R8_IT_0420.pdf` and `R8_GB_0420.pdf` are rejected before
  download as `pre_filtered_non_target_hint` syllabus/course-plan PDFs.
- Local evidence snapshot was pulled to `_temp/win-v340-evidence/`, including
  `bootstrap-pdfs-20260513-061039.log`, `bootstrap-pdfs-20260513-061039.json`,
  `bootstrap-20260513_062725-discovery-rca-batch-plan.json`,
  `discovery_rejections.jsonl`, and a copy of `eidp-v340.sqlite3`.

Superseded v333 setup/bootstrap evidence:

- Uploaded `dist/eidp-windows-v333.zip` to
  `C:\Users\<operator>\eidp-windows-v333.zip`.
- Windows `Get-FileHash -Algorithm SHA256` ->
  `70211256799674031CEBE671732212D1C4F30DD6058B6EBBE48BF53DEBD83F7F`.
- Extracted to `C:\Users\<operator>\EIDP-v333-422741d`.
- `scripts\first_setup.bat` -> exit `0`; after-setup validator reported
  commit `422741d9f9cff64bdd67a9987654bd4963fdac52`,
  `build_dirty=false`, `school_count=2418`,
  `school_fiscal_year_status_count=2418`, `sqlite_integrity_check=ok`,
  required SQLite tables present, `department_change` void columns present,
  and `uq_document_file_hash` present.
- Windows `eidp discovery-gold-set --json` reports `23` entries,
  `publication_lag_latest_public=9`, and demonstrated extractor sources
  `embed` plus `wordpress_download_manager`.
- `scripts\bootstrap_pdfs.bat --pref saitama --skip-known-url-discovery --url-search off --school-url-crawl off --batch-size 50 --rate-limit 0.2 --request-timeout 15` -> exit `0`.
- Official Saitama artifact downloaded; aggregate `extracted=58`,
  `matched=51`, `added=51`, `review_items=2`.
- PDF discovery: `crawled=50`, `found=49`, `downloaded=0`, `failed=4`,
  `skipped=1380`, `prefiltered=1048`, `cached_rejections=286`,
  `candidate_school_mismatch=5160`, `candidate_budget_dropped=853`,
  `rejection_reason_discovery_error=1`,
  `rejection_reason_fiscal_year_mismatch=330`,
  `rejection_reason_target_fiscal_year_not_detected=31`,
  `rejection_reason_unsafe_url=1`.
- Ingest: `processed=0`, `departments_created=0`, `yearly_upserted=0`,
  `skipped=0`.
- Rebuilt status: `excel_ready=0`, `target_pdf_auto_acquired_count=0`,
  `operator_reviewable_count=38`, `operator_reviewable_yield_pct=1.6`,
  `ship_gate_status=below_gate`.
- Diagnostics after bootstrap:
  `validate_core_rc=0`, `validate_after_setup_rc=0`,
  `validate_after_bootstrap_rc=0`,
  `validate_after_bootstrap_ship_gate_rc=1`, `ship_readiness_rc=1`.
- Local evidence snapshot was pulled to `_temp/win-v333-evidence/`, including
  `bootstrap-pdfs-20260513-042824.log`, `bootstrap-pdfs-20260513-042824.json`,
  `diagnostics-20260513-044537.txt`, the RCA batch plan,
  `discovery_rejections.jsonl`, and a copy of `eidp.sqlite3`. SQLite checks on
  that snapshot report `2418` schools, `51` school sites, `0` documents, `0`
  PDF-derived current 2026 DepartmentYearly rows, `2418` 2026 school status
  rows, `0` Excel-ready schools, and `2` pending review items.
- The v332 false-positive downloaded URLs now appear in
  `discovery_rejections.jsonl` as `target_fiscal_year_not_detected`, for
  example 上尾中央看護専門学校 `study_support_system.pdf`, さいたま看護専門学校
  `申請書_0602_資料A.pdf`, 幸手看護専門学校
  `高等教育無償化更新確認申請書 様式第2号の1～4.pdf`, 専門学校埼玉自動車大学校
  `koutoumusyou.pdf`, and 中央情報専門学校 `youshiki2.pdf`.

## Previous Windows Bootstrap Evidence With Superseded Strict-Year Behavior

v332/v331 both showed `downloaded=7` / `excel_ready=5` on the same bounded
Saitama sample, but v333 proved those were false-positive strict-year successes:
the accepted evidence used `year_evidence=prefecture_index_current_year` with
empty `detected_fiscal_year`. That behavior is intentionally superseded by
v333.

Earlier commands and observations from `ssh win` for v331 setup/bootstrap:

- Uploaded `dist/eidp-windows-v331.zip` to
  `C:\Users\<operator>\eidp-windows-v331.zip`.
- Windows `Get-FileHash -Algorithm SHA256` ->
  `455C562901B0361E68BE6DD00084FD89F2DE33DF09670246168E910DCFB09186`.
- Extracted to `C:\Users\<operator>\EIDP-v331-9730b5a`.
- `scripts\first_setup.bat` -> exit `0`; after-setup validator reported
  commit `9730b5acc097b19d26a2b2db6a7d8212bca6483a`,
  `build_dirty=false`, `school_count=2418`,
  `school_fiscal_year_status_count=2418`, `sqlite_integrity_check=ok`,
  required SQLite tables present, `department_change` void columns present,
  and `uq_document_file_hash` present.
- Read-only v331 Windows discovery probe for the prior three
  `site_fetch_error_only` rows:
  - school `760` now returns `error=null`, `candidates=2`, best
    `https://i-heiseigakuen.ac.jp/download/yousiki2/?wpdmdl=5471&refresh=...`;
  - school `767` returns `error_code=robots_disallow_all`, `retryable=false`;
  - school `785` now returns `error=null`, `candidates=27`, best
    `https://nihon-ika.ac.jp/wp/wp-content/uploads/2025/08/⑮2025年更新確認申請書.pdf`.
  The subsequent bounded bootstrap confirms two v330 timeout rows were transient
  fetch failures, while the Kitasato row is a real robots-policy block.
- `scripts\bootstrap_pdfs.bat --pref saitama --skip-known-url-discovery --url-search off --school-url-crawl off --batch-size 50 --rate-limit 0.2 --request-timeout 15` -> exit `0`.
- Official Saitama artifact downloaded; aggregate `extracted=58`,
  `matched=51`, `added=51`, `review_items=2`.
- PDF discovery: `crawled=50`, `found=49`, `downloaded=7`, `failed=4`,
  `skipped=1235`, `prefiltered=919`, `cached_rejections=286`,
  `candidate_school_mismatch=5160`, `candidate_budget_dropped=853`,
  `rejection_reason_discovery_error=1`,
  `rejection_reason_fiscal_year_mismatch=326`,
  `rejection_reason_target_fiscal_year_not_detected=22`,
  `rejection_reason_unsafe_url=1`.
- Ingest: `processed=7`, `departments_created=12`, `yearly_upserted=18`,
  `skipped=1`.
- Rebuilt status: `excel_ready=5`, `target_pdf_auto_acquired_count=5`,
  `operator_reviewable_count=41`, `operator_reviewable_yield_pct=1.7`,
  `ship_gate_status=below_gate`.
- Diagnostics after bootstrap:
  `validate_core_rc=0`, `validate_after_setup_rc=0`,
  `validate_after_bootstrap_rc=0`,
  `validate_after_bootstrap_ship_gate_rc=1`, `ship_readiness_rc=1`.
- DB evidence after the 50-site run has `Document=7`: `5` ingested,
  `1` review-pending, and `1` school-mismatch.
- The malformed raw URL from 越生自動車大学校 was recorded as
  `unsafe_url`:
  `http://www.ogo\nsejidai.ac.jp/wordpress/wp-content/uploads/2019/08/e46236c71464104f59caea652d9567e3.pdf`.
- Evidence review confirmed stale-label rejection: the prior v324 false
  acceptance `R7確認申請書類 様式第2号` is now recorded as
  `fiscal_year_mismatch:2025`.
- The v331 RCA batch plan has `10` items / `43` actionable candidates. Top
  buckets include `target_form_without_year_evidence` for 浦和専門学校 and
  大宮歯科衛生士専門学校, `non_target_candidates_only` for several schools,
  and `publication_lag_or_old_target_pdf` for 東京IT会計公務員専門学校大宮校.

## Next Required Proof

1. Run browser UI operator click-through on the current Windows install:
   `EIDP-start.bat` -> operator pages -> Excel preview/download -> diagnostics.
2. Expand Windows official-index discovery beyond the 50-site Saitama bounded
   smoke and record target PDFs accepted, publication-lag queue,
   manual-required queue, and errors.
3. Repeat the v342 RCA batch-plan classification on a larger official-index
   sample to quantify whether low strict-target result remains dominated by
   upstream publication lag / missing PDF-year evidence rather than crawler
   false negatives.
4. Compare measured operator-reviewable coverage, manual workload, and Excel
   readiness against the shipping line; keep strict target-PDF acquisition as a
   diagnostic metric during the May publication-lag window.
5. Only after those numbers pass should the branch be treated as release-ready.
