# Active Goal Completion Audit — EIDP Rolling Automation

Date: 2026-05-07
Latest update: 2026-05-12
Branch: `sprint8-handoff-finalize`
Latest Mac-verifier-clean Windows package commit: `871de0b4a2b505b7be040adb05d8f720b9fda147` (`eidp-windows-v271.zip`; Windows E2E pending)
Latest Windows setup-verified package commit: `e7c6c9ca6b95961b05acc6d56da19a41de320226` (`eidp-windows-v245.zip`)
Latest Windows focused replay proof: `d2beff605d168431d2b35f8cbe5a891ea9ab9c0b` (`eidp-windows-v244.zip`, school `769`)

## 2026-05-11 Codex Manual Discovery RCA Consolidation

The manual/Codex discovery workflow has been consolidated into
`docs/runbooks/discovery-codex-manual-rca.md`. The runbook fixes the operating
order for future manual investigations: official-index handoff first,
registered disclosure page second, bounded same-site navigation third, and
SERP only as a last fallback for a named school. Each investigation must end in
one structured outcome label (`accepted_target_pdf`,
`publication_lag_latest_public`, `needs_operator_review`,
`no_target_candidate_found`, or site/infrastructure failure) and, when useful,
be promoted into an existing `data/discovery-gold-set/entries/*.json` entry.

A current Saitama 51-school evidence view was rebuilt from the full v231
Windows bounded acquisition run. This proves Layer 0 is intact for the bounded
Saitama sample: all 51 scoped schools have `prefecture_aggregator` disclosure
URLs. Layer 1 remains the bottleneck, and the final DB/status count is stricter
than the discovery evidence bucket:

- discovery-stage `accepted_target_pdf=2` / `accepted_downloaded=2`
  (schools `757`, `784`)
- final `target_pdf_auto_acquired_count=2` and `excel_ready=2`
  (schools `757`, `784`; school `72` is now rejected before target ingestion)
- `publication_lag_or_old_target_pdf=40`
- `non_target_candidates_only=8`
- `site_fetch_error_only=1`
- `no_pdf_candidates=0`

The v229 correction is intentionally conservative: school `95`
(`さいたまIT・WEB専門学校`) had been accepted in v228 because the PDF body
contained `完成年度は2026年度`. That is a program completion year, not filing or
target-FY evidence. The full v229 run now rejects that stale
`2025年度申請書（様式第2号）` candidate as `fiscal_year_mismatch:2025`.
The subsequent v230 package adds a guard for the school `72` false positive:
`職業実践専門課程等の基本情報` PDFs are now pre-filtered/classified as
`non_target` unless they also contain strong support-system confirmation-form
markers. A v230 targeted Windows replay for school `72` returned `downloaded=0`
and left `document` count at `0`.
The v231 package fixes the next RCA boundary from school `793`: list-based CMS
pages no longer let the first `2025年度` form inherit a preceding `2026年度`
syllabus link as year evidence. `様式第2号の1～4` full form ranges are also
treated as target-form hints, so stale full-form ranges can be rejected before
download as `fiscal_year_mismatch:*`.
The v232 package closes two review-bound false-negative RCA edges from the same
Saitama evidence. First, support-only image PDFs such as school `761`
`R7修学支援に関する資料` no longer become `fiscal_year_mismatch:*` just because
the anchor or URL contains an old generic year; stale candidate-year fallback
now requires a body-confirmed target PDF or a target application-form hint.
Second, dense WordPress link-button blocks no longer mix sibling anchor text
such as `実務経験のある教員の授業一覧` into a year-bearing support PDF's own
anchor context. A Windows v232 targeted replay over schools `761` and `763`
therefore routes both image-only support/form candidates to
`target_fiscal_year_not_detected` for review instead of stale publication-lag
or pre-download non-target buckets.
The v233 package restores release-gate coverage for the
`no_target_candidate_found` discovery outcome after the 入間看護 gold-set entry
was correctly reclassified as `publication_lag_latest_public`. A bounded
current-code replay against the official 東京モード学園 homepage produced
`no_candidates_found`, and that case is now tracked as
`tokyo-mode-gakuen-no-candidates-2026`.
The v234 package closes a rendered-HTML false-negative edge: a static
current-year non-target PDF such as `2026年度 学校案内` no longer suppresses
the JS-rendered fallback that may reveal the real
`令和8年度 高等教育の修学支援新制度 確認申請書` candidate.
The v235 package closes a second discovery crowd-out edge from the same real
Saitama evidence family: pre-filtered adjacent PDFs such as current-year news,
open-campus, entrance-exam, and student `A様式1` application forms no longer
consume the bounded top-10 download attempts before a lower-ranked target form
can be tried.
The v236 package closes the next same-family network waste edge found in the
v235 Windows evidence: English `subject_*.pdf` / `subject-*.pdf` disclosure
files, which are usually syllabus/course-list PDFs, are now rejected before
download unless the link also carries a target confirmation-form hint.
The v237 package closes the residual subject-link contamination from the same
all-japan evidence: `subject_*.pdf` / `subject-*.pdf` filenames no longer become
old-year target-like candidates just because their enclosing block inherited
adjacent `academic_support` or `修学支援新制度様式2号` text.
The v238/v239 packages close the next exposed all-japan non-target layer:
department `info_*.pdf`, `grade_manage.pdf`, `goal_policies.pdf`,
`regulation.pdf`, `donation.pdf`, and `remuneration.pdf` are now rejected before
download when they lack local target-form URL hints.

A fresh Windows v235 package replay was then run on
`C:\Users\cyo20\EIDP-v235-864ae14` from the shipped ZIP
(`git_commit=864ae148d0d4bc75abb1800298daa71191b2dfdd`, SHA256
`6b645f2128e0715af0fdeb68cd1bcf595ecf910786dadc1fb49849c3b02319ba`).
The replay was bounded to Saitama official-index URLs only:
`--pref saitama --skip-known-url-discovery --url-search off
--school-url-crawl off --discovery-methods prefecture_aggregator
--batch-size 60 --rate-limit 0.5 --request-timeout 15`. It did not run
nationwide SERP discovery.

- Windows setup/after-setup validation passed: `school_count=2418`,
  `school_fiscal_year_status_count=2418`, `sqlite_integrity_check=ok`,
  `uq_document_file_hash` present, and `build_dirty=false`.
- Official Saitama aggregation matched the expected Layer 0 result:
  `extracted=58`, `matched=51`, `added=51`.
- PDF discovery improved from the previous bounded Saitama evidence:
  `crawled=51`, `found=50`, `downloaded=3`, `failed=4`,
  `skipped=724`, `prefiltered=418`, and `cached_rejections=103`.
- The three accepted strict FY2026 targets were schools `757`
  (`上尾中央看護専門学校`), `760` (`入間看護専門学校`), and `784`
  (`専門学校埼玉自動車大学校`). Ingest processed all three documents and
  produced `yearly_upserted=8`; `rebuild-school-year-tasks` produced
  `excel_ready=3`.
- School-level evidence summary for the 51 scoped sites:
  `accepted_target_pdf=3`, `publication_lag_or_old_target_pdf=40`,
  `target_form_without_year_evidence=3`, `non_target_candidates_only=4`,
  and `site_fetch_error_only=1`.
- The package remains below the product ship gate:
  `target_pdf_auto_acquired_count=3`,
  `target_pdf_auto_denominator_count=2418`,
  `target_pdf_auto_yield_pct=0.1`, and
  `ship_gate_status=below_gate`.

Operator-facing diagnosis was also run after replay. Core and after-setup
validation passed; after-bootstrap diagnostics were intentionally not applicable
to this bounded developer replay because it invoked `bootstrap_pdf_pipeline.py`
directly with a custom progress file rather than the UI/batch wrapper that writes
`logs/bootstrap-pdfs-*`.

For v236 packaging, `scripts/build_windows_zip.py --skip-download --out-zip
dist/eidp-windows-v236.zip --latest-alias` produced a clean ZIP with SHA256
`6048c334385cc2c3cc2393ee5209e2c78d2f0fb84139f536c2109cc08aec4bef`.
Both `dist/eidp-windows-v236.zip` and `dist/eidp-windows.zip` passed
`scripts/verify_windows_distribution.py --json` with `git_dirty=false`,
`entry_count=3027`, `wheel_count=78`, 17 discovery gold-set entries, and 47
downloadable supported prefecture seeds. A local extracted-install validation
also passed, and the extracted source contains the `subject_` / `subject-`
pre-download tokens.

A targeted Windows v236 replay then validated that the shipped ZIP uses the new
subject pre-download guard in the real operator runtime. Fresh extraction
`C:\Users\cyo20\EIDP-v236-2e90d7c` passed setup and after-setup validation
with `school_count=2418`, `school_fiscal_year_status_count=2418`,
`sqlite_integrity_check=ok`, `uq_document_file_hash` present, and
`build_commit=2e90d7c540c88704dbf4f617597530f888f36ea1`. The replay was
bounded to Saitama official-index data and the two affected all-japan schools
(`291`, `486`): it downloaded the current Saitama artifact, applied
`prefecture-aggregate --pref saitama --apply` (`extracted=58`, `matched=51`,
`added=51`), and then ran `discover-pdfs` with
`--discovery-method prefecture_aggregator --school-id 291 --school-id 486`.
The pulled evidence has `254` rows. Among `subject_` / `subject-` URLs, the
existing v235 overlap of `39` school+URL pairs changed from
`classified_non_target=30`, `fiscal_year_mismatch=8`, and
`pre_filtered_non_target_hint=1` to `pre_filtered_non_target_hint=31` and the
same `fiscal_year_mismatch=8`. Across the full v236 targeted replay, `116/124`
subject rows are now pre-download `pre_filtered_non_target_hint`; the remaining
`8` are anchor-contaminated old-year target-like rows where adjacent
`academic_support` / `修学支援新制度様式2号` context still dominates. No
`Document` rows were created for schools `291` or `486`. This proves the v236
fix removes the subject-PDF download/classification waste without accepting any
new target PDF.

For v237 packaging, `scripts/build_windows_zip.py --skip-download --out-zip
dist/eidp-windows-v237.zip --latest-alias` produced a clean ZIP with SHA256
`30a8fc52caefee981db4bd3096a6964f591724f8dae2d79a8cfdc9fa92507751`.
Both `dist/eidp-windows-v237.zip` and `dist/eidp-windows.zip` passed
`scripts/verify_windows_distribution.py --json` with `git_dirty=false`,
`entry_count=3027`, `wheel_count=78`, 17 discovery gold-set entries, and 47
downloadable supported prefecture seeds. A local extracted-install validation
also passed. Fresh Windows extraction `C:\Users\cyo20\EIDP-v237-502b7ad`
passed setup and after-setup validation with `school_count=2418`,
`school_fiscal_year_status_count=2418`, `sqlite_integrity_check=ok`,
`uq_document_file_hash` present, and
`build_commit=502b7ad182fd5a0fe99303012e008c9197763f49`. The same bounded
Saitama/291/486 replay produced `254` evidence rows. Across all
`subject_` / `subject-` URLs, `124/124` are now pre-download
`pre_filtered_non_target_hint` with `pdf_type=non_target`, and no `Document`
rows were created for schools `291` or `486`. This closes the v236 residual
`8` anchor-contaminated subject rows without accepting any new target PDF.

For v238 packaging, `scripts/build_windows_zip.py --skip-download --out-zip
dist/eidp-windows-v238.zip --latest-alias` produced SHA256
`b61ca90751ee2302282e6a29ee8e2ed15f89995a7378a21c7e4eaef2ffc64afb`
with `git_commit=9dd5db9a2fe95bae0707ddf32863de9cf1723109` and
`git_dirty=false`. The same Windows 291/486 replay showed that
`info_*.pdf`, `grade_manage.pdf`, and `goal_policies.pdf` were pre-download
non-targets, but freeing those candidates exposed the next lower-ranked
download-time non-target set: `classified_non_target=18`, all
`regulation.pdf`, `donation.pdf`, or `remuneration.pdf`.

For v239 packaging, `scripts/build_windows_zip.py --skip-download --out-zip
dist/eidp-windows-v239.zip --latest-alias` produced SHA256
`c93cb4e42398035d1c1f8ed9a0258af0f5217f2094db87e62bbd443f0e4ee8e5`.
Both `dist/eidp-windows-v239.zip` and `dist/eidp-windows.zip` passed
`scripts/verify_windows_distribution.py --json` with `git_dirty=false`,
`entry_count=3027`, `wheel_count=78`, 17 discovery gold-set entries, and 47
downloadable supported prefecture seeds. A local extracted-install validation
also passed. Fresh Windows extraction `C:\Users\cyo20\EIDP-v239-1f03fff`
passed setup and after-setup validation with `school_count=2418`,
`school_fiscal_year_status_count=2418`, `sqlite_integrity_check=ok`,
`uq_document_file_hash` present, and
`build_commit=1f03fffd4d1cd39fc5e0ab0ec09f873d28f2e5e5`. The same bounded
Saitama/291/486 replay produced `1106` evidence rows and `classified_non_target=0`.
All observed all-japan disclosure-neighbor families were pre-download
non-targets: `subject_` / `subject-` (`396` rows), `info_` (`116`),
`grade_manage` (`48`), `goal_policies` (`2`), and governance PDFs
(`regulation.pdf`, `donation.pdf`, `remuneration.pdf`; `52`). No `Document`
rows were created for schools `291` or `486`.

During this RCA, a classification defect was found in
`discovery_evidence_summary.py`: old-year `image_only` PDFs with both system
hints and target application-form hints, such as `修学支援` plus `様式第2号`,
are now bucketed as `publication_lag_or_old_target_pdf`. Weak image-only hints
such as support-only `R7修学支援に関する資料`, form-only `様式2号`, or generic
MEXT support boilerplate years such as `2020年度の在学生から対象` remain
`target_form_without_year_evidence`. This keeps strict target-year success
unchanged while surfacing the correct operator action: latest-public old-year
forms require review, not automatic current-year acceptance.

For v240 packaging, `scripts/build_windows_zip.py --skip-download --out-zip
dist/eidp-windows-v240.zip --latest-alias` produced SHA256
`de1117a486bada414ec682a7045559446c4ba78088ab28043bad25e430dd1902`
with `git_commit=2dcc7f8362af991e8639b99ffebd34b78250f755` and
`git_dirty=false`. `scripts/verify_windows_distribution.py` passed with
`entry_count=3027`, `wheel_count=78`, 17 discovery gold-set entries, and 47
downloadable supported prefecture seeds. Local extracted-install validation
passed. Fresh Windows extraction `C:\Users\cyo20\EIDP-v240-2dcc7f8` passed
setup/after-setup validation with `school_count=2418`,
`school_fiscal_year_status_count=2418`, `sqlite_integrity_check=ok`,
`uq_document_file_hash` present, and
`build_commit=2dcc7f8362af991e8639b99ffebd34b78250f755`.

The v240 full bounded Saitama official-index replay used the same developer
scope as v239: `--pref saitama --skip-known-url-discovery --url-search off
--school-url-crawl off --discovery-methods prefecture_aggregator
--batch-size 60 --rate-limit 0.5 --request-timeout 15`. It parsed
`extracted=58`, `matched=51`, and `added=51` school sites, then crawled `51`
registered sites and found PDF candidates on `50`. The final acquisition
result did not improve strict target yield: `downloaded=3`, ingest
`processed=3`, `yearly_upserted=8`, `target_pdf_auto_acquired_count=3`,
`target_pdf_auto_yield_pct=0.1`, and `ship_gate_status=below_gate`.

The v240 pre-download layer did reduce download-time noise: evidence rows grew
from v239 `1846` to v240 `1968` because bounded attempts reached deeper
candidate sets, while `pre_filtered_non_target_hint` rose `1217 -> 1416`,
`classified_non_target` fell `230 -> 169`, and
`target_fiscal_year_not_detected` fell `51 -> 27`. URL-level replay diff shows
`86` v239 `classified_non_target` rows, `26` v239
`target_fiscal_year_not_detected` rows, and `1` v239 `not_pdf_magic` row moved
to pre-download non-target rejection. The DB result stayed unchanged at the
same three current-year `Document` rows for schools `757`, `760`, and `784`.
This is useful network/CPU hygiene, but not a ship-gate improvement.

The remaining v240 `classified_non_target=169` rows show token tuning is now
past the high-ROI phase. The largest residual families are site-family or
structure problems rather than generic vocabulary misses: O-Hara numbered
public-disclosure PDFs such as `2025-1-01-01-1.pdf`, Sanko school-specific
course/hash PDFs, Arsnet course-code PDFs such as `R8_1A1_0420.pdf`, and
school-specific survey/organization/career-support PDFs. Further broad
negative tokens risk suppressing valid lower-ranked target forms. The next
meaningful discovery work should be site-family rules or manual RCA/gold-set
promotion for those families, not unrestricted token expansion.

For v241 packaging, `scripts/build_windows_zip.py --skip-download --out-zip
dist/eidp-windows-v241.zip --latest-alias` produced SHA256
`d175e174630ee2f833a27a2884525278447163bd20ac095f8b10a9bc0c6be439`
with `git_commit=0994401073c5dceec749290def574492be50b801` and
`git_dirty=false`. The ZIP verifier and local extracted-install validator
passed. Fresh Windows extraction `C:\Users\cyo20\EIDP-v241-0994401` passed
setup/after-setup validation with `school_count=2418`,
`school_fiscal_year_status_count=2418`, `sqlite_integrity_check=ok`,
`uq_document_file_hash` present, and
`build_commit=0994401073c5dceec749290def574492be50b801`.

The v241 full bounded Saitama official-index replay used the same developer
scope as v240: `--pref saitama --skip-known-url-discovery --url-search off
--school-url-crawl off --discovery-methods prefecture_aggregator
--batch-size 60 --rate-limit 0.5 --request-timeout 15`. It again parsed
`extracted=58`, `matched=51`, and `added=51` school sites, crawled `51`
registered sites, found PDF candidates on `50`, downloaded `3`, and rebuilt
status with `target_pdf_auto_acquired_count=3`,
`target_pdf_auto_yield_pct=0.1`, and `ship_gate_status=below_gate`.
The accepted current-year documents are still the same three schools:
`757` (`上尾中央看護専門学校`), `760` (`入間看護専門学校`), and `784`
(`専門学校埼玉自動車大学校`).

The v241 site-family pre-download guard moved another `130` overlapping
v240 evidence rows to `pre_filtered_non_target_hint`
(`115` from `classified_non_target`, `7` from
`target_fiscal_year_not_detected`, `7` from `fiscal_year_mismatch:2025`, and
`1` from `fiscal_year_mismatch:2019`). In aggregate,
`classified_non_target` fell from v240 `169` to v241 `125`, and
`target_fiscal_year_not_detected` fell from `27` to `21`. This is still not a
ship-gate improvement: evidence rows expanded from `1968` to `5580`, skipped
candidates from `1809` to `5418`, cached rejections from `596` to `2813`, and
prefiltered rows from `1117` to `2550`. Most of the new depth is site-family
churn, especially O-Hara numbered public-disclosure PDFs. The next
yield work should therefore change candidate budgeting/prioritization and
site-family target-form derivation, not keep adding broad negative tokens.

For v242 packaging, `scripts/build_windows_zip.py --skip-download --out-zip
dist/eidp-windows-v242.zip --latest-alias` produced SHA256
`0812e4aa807b15b7af11409ccb606c4e2d4ac68b7370ed36a805e4770bcd7afb`
with `git_commit=0511e6730ded05871d48202f61eea3765ac0a046` and
`git_dirty=false`. The ZIP verifier passed with `entry_count=3027`,
`wheel_count=78`, 17 discovery gold-set entries, and 47 downloadable supported
prefecture seeds. Local extracted-install validation also passed. Fresh
Windows extraction `C:\Users\cyo20\EIDP-v242-0511e67` passed setup and
after-setup validation with `school_count=2418`,
`school_fiscal_year_status_count=2418`, `sqlite_integrity_check=ok`,
`uq_document_file_hash` present, and the expected `department_change` void
columns present.

A first v242 developer replay attempt produced an inconsistent
`pdf_discovery_start sites=0` despite the SQLite database containing 51
`prefecture_aggregator` `SchoolSite` rows. That run was discarded as invalid:
the same packaged environment then showed `sites=51` through a direct
`run_pdf_discovery` call, the packaged `eidp discover-pdfs` CLI with
`--batch-size 1`, and a clean replay from a separate fresh extraction
`C:\Users\cyo20\EIDP-v242-replay-0511e67`.

The valid v242 full bounded Saitama official-index replay used the same scope
as v241: `--pref saitama --skip-known-url-discovery --url-search off
--school-url-crawl off --discovery-methods prefecture_aggregator
--batch-size 60 --rate-limit 0.5 --request-timeout 15`. It again parsed
`extracted=58`, `matched=51`, and `added=51`, then crawled `51` registered
sites and found PDF candidates on `50`. Final strict target yield stayed
unchanged: `downloaded=3`, ingest `processed=3`, `yearly_upserted=8`,
`target_pdf_auto_acquired_count=3`, `target_pdf_auto_yield_pct=0.1`, and
`ship_gate_status=below_gate`. The accepted documents are still schools `757`,
`760`, and `784`.

The v242 candidate-prioritization budget is therefore a runtime/noise fix, not
a yield fix. It keeps target-like and form-like candidates ahead of generic PDFs
but caps generic candidate scans at 80 per school. Compared with v241, the
valid Saitama replay reduced evidence rows `5580 -> 1324`, unique rejected PDF
URLs `2766 -> 1100`, skipped candidates `5418 -> 1166`, cached rejections
`2813 -> 224`, and prefiltered rows `2550 -> 886`. The new counters show
`candidate_budget_limited=8` and `candidate_budget_dropped=6487`. Rejection
distribution after budgeting remained structurally similar for the meaningful
classes: `target_fiscal_year_not_detected=21`,
`classified_non_target=129`, and `fiscal_year_mismatch=334`.

Interpretation: v242 proves the previous v241 diagnosis was correct. The next
high-ROI discovery work is not broader negative-token tuning; it is either
manual RCA/gold-set promotion for real target-form derivation on the remaining
families, or a different official-site navigation strategy for the 48/51 scoped
Saitama schools where strict current-FY target PDFs still are not acquired.

- Regression coverage:
  `test_summarize_pdf_discovery_evidence_treats_image_only_old_target_application_hints_as_publication_lag`,
  `test_summarize_pdf_discovery_evidence_keeps_weak_image_only_form_or_support_hints_in_review`,
  `test_summarize_pdf_discovery_evidence_keeps_generic_higher_ed_boilerplate_image_only_in_review`,
  `test_pre_download_rejects_site_family_non_target_url_shapes`,
  `test_pre_download_site_family_guard_keeps_sanko_target_form_shape`, and
  `test_pre_download_site_family_guard_keeps_local_target_application_hint`.
  v242 adds
  `test_run_pdf_discovery_prioritizes_target_like_candidate_before_prefilter_noise`
  and
  `test_run_pdf_discovery_limits_general_candidate_scan_without_hiding_formish_target`.
- Verification:
  `uv run pytest tests/unit/test_discovery_evidence_summary.py -q -k image_only`
  → `2 passed`;
  `uv run pytest tests/unit/test_discovery_evidence_summary.py
  tests/unit/test_school_fiscal_year_status.py
  tests/unit/test_review_school_year_tasks.py -q` → `72 passed`;
  `uv run pytest tests/unit/test_pdf_discovery.py -q` →
  `90 passed, 5 warnings`; `uv run pytest tests/unit -q` →
  `1191 passed, 5 warnings`. `uv run ruff check
  src/eidp/scraper/pdf_discovery.py tests/unit/test_pdf_discovery.py` passed,
  as did local ZIP verification, local extracted validation, Windows
  setup/after-setup validation, and the clean Windows v242 Saitama bounded
  replay above.

For v243 packaging, `scripts/build_windows_zip.py --skip-download --out-zip
dist/eidp-windows-v243.zip --latest-alias` produced SHA256
`b60b5643d537673de6abe5b7ff04654991993207542eb63e0c80f50945b0ad25`
with `git_commit=8e7baef7d15f639fb424fa810b0b7b5090ab6bb8` and
`git_dirty=false`. `scripts/verify_windows_distribution.py` passed with
`entry_count=3028`, `wheel_count=78`, 18 discovery gold-set entries, and 47
downloadable supported prefecture seeds. Fresh Windows extraction
`C:\Users\cyo20\EIDP-v243-8e7baef` passed setup and after-setup validation
with `school_count=2418`, `school_fiscal_year_status_count=2418`,
`sqlite_integrity_check=ok`, `uq_document_file_hash` present, the expected
`department_change` void columns present, `build_commit` matching the package
commit, and `build_dirty=false`.

A focused Windows v243 replay then validated the packaged O-Hara table-header
candidate derivation in the real operator runtime. The replay seeded school
`212` with the registered disclosure page `https://www.o-hara.ac.jp/about/joho/`
and ran strict FY2026 discovery against that single site. It produced
`crawled=1`, `found=1`, `downloaded=0`, `skipped=198`, `prefiltered=187`,
`candidate_budget_limited=1`, and `candidate_budget_dropped=1640`. The packaged
evidence predicts
`https://www.o-hara.ac.jp/about/joho/pdf/2025-1-37-01-5.pdf`, matching the new
gold-set entry exactly as `publication_lag_latest_public`. This is a Windows
package proof for the manual-success-to-agent pattern, but not a strict
current-FY yield improvement because the visible O-Hara form remains FY2025.

The v244 package closes one strict-yield false negative in school `769`
(`公益社団法人地域医療振興協会さいたま看護専門学校`). v242 rejected
`http://www.saitama-kango.jp/wp/wp-content/uploads/2025/06/申請書_0602_資料A.pdf`
as `fiscal_year_mismatch:2025` because the WordPress upload path contains
`2025/06`. Manual inspection showed the PDF body is a target
`様式第2号` form, while the internal 2025/2026 dates are committee/term dates,
not explicit fiscal-year labels. Current code now preserves the existing safety
boundary: explicit stale labels such as `2025年度` or `令和7年度` still reject,
but a bare upload/calendar year no longer overrides
`prefecture_index_current_year` when the PDF body classifies as target. A
focused current-code replay for school `769` produced `downloaded=1` with
`year_evidence=prefecture_index_current_year`; ingestion processed the document,
preserved `document_fiscal_year=2026` despite parser-visible internal 2025
dates, wrote `yearly_upserted=1`, and status rebuild raised the copied Saitama
DB to `excel_ready=4`.

For v244 packaging, `scripts/build_windows_zip.py --skip-download --out-zip
dist/eidp-windows-v244.zip --latest-alias` produced SHA256
`fecc714573983c0ca00fcd3775c84fb6b680307cd8daf71432839d193887775e`
with `git_commit=d2beff605d168431d2b35f8cbe5a891ea9ab9c0b` and
`git_dirty=false`. `scripts/verify_windows_distribution.py` passed with
`entry_count=3029`, `wheel_count=78`, 19 discovery gold-set entries, and 47
downloadable supported prefecture seeds. Fresh Windows extraction
`C:\Users\cyo20\EIDP-v244-d2beff6` passed setup and after-setup validation
with `school_count=2418`, `school_fiscal_year_status_count=2418`,
`sqlite_integrity_check=ok`, `uq_document_file_hash` present, and
`build_dirty=false`. A Windows v244 focused replay for school `769` then
validated the packaged fix: PDF discovery returned `downloaded=1`, ingestion
returned `processed=1` / `yearly_upserted=1`, status rebuild returned
`excel_ready=1` on the fresh package DB, and
`eval-discovery-gold --pdf-evidence` reported `exact_matches=1` /
`failed_predictions=0` for the new gold-set entry.

## 2026-05-12 v244 Full Saitama Replay and v245/v246 Rolling-Year Hardening

A full bounded Windows v244 Saitama replay showed that the v244
upload/calendar-year trust fix improved raw acquisition but also exposed new
strictness risks. The replay used the packaged v244 ZIP at
`C:\Users\cyo20\EIDP-v244-full-d2beff6` with official-index scope only
(`--pref saitama --skip-known-url-discovery --url-search off
--school-url-crawl off --discovery-methods prefecture_aggregator
--batch-size 60`). Step 2 extracted `58` official rows, matched `51`, and
added `51` `prefecture_aggregator` URLs. PDF discovery then crawled `51`
sites, found `50`, downloaded `11`, and final status rebuild counted
`target_pdf_auto_acquired_count=7` / `target_pdf_auto_yield_pct=0.3` against
the full `2418` active-specialty-school denominator. The ship gate correctly
remained `below_gate`.

The important finding is that the `7` status count was not fully trustworthy.
Gold-set evaluation of the same evidence produced `exact_matches=6`,
`failed_predictions=2`, and `missing_entries=11`. The failures were not
packaging defects; they were discovery correctness defects:

- school `760` (`入間看護専門学校`) was accepted from a WordPress Download
  Manager wrapper whose anchor explicitly said `様式２（R6年度分申請）`. The
  official-index current-year trust must not override that stale FY2024 label.
- school `95` (`さいたまIT・WEB専門学校`) correctly rejected the known
  `shugakushien_shinsei2025-1-2.pdf` publication-lag PDF, but also downloaded
  an adjacent student tuition-reduction PDF
  (`jyugyoryo-genmen2025_2.pdf`). Ingest marked it `school_mismatch`, so it did
  not become `excel_ready`, but discovery should reject it before download.
- school `782` (`専門学校越生自動車大学校`) was counted as current-year success
  because `令和七年度` was not parsed as FY2025. This has been promoted into
  `data/discovery-gold-set/entries/ogose-auto-publication-lag-2026.json` so it
  remains a regression fixture.

The v245 source fix (`e7c6c9c`) closes those false-positive classes locally:
romanized stale era labels such as `R6年度` are explicit stale fiscal-year
labels, kanji era labels such as `令和七年度` parse to western fiscal years, and
student tuition-reduction links such as `授業料減免` / `jyugyoryo-genmen` are
pre-download rejected unless they also contain a target-form hint. The focused
unit and gold-set gates passed, and the full unit suite passed
(`1200 passed`). A v245 ZIP was built from `e7c6c9c`, Mac verification passed
with SHA256
`a7475140f83ea1dabbb38b3fa8f40e8676dc7cb1b0a1c8e71efd5c03ae52af62`, and a
fresh Windows extraction `C:\Users\cyo20\EIDP-v245-e7c6c9c` completed
`EIDP-setup.bat` with `school_count=2418`, `school_fiscal_year_status_count=2418`,
`sqlite_integrity_check=ok`, `uq_document_file_hash` present, and
`build_dirty=false`. SSH availability ended before a clean focused replay could
be completed, so v245 is setup-verified but not focused-replay verified.

The subsequent v246 package (`2406da4`) is the latest Mac-verifier-clean ZIP.
It adds a rolling-year regression matrix so the PDF gate is not hard-coded to
FY2026: FY2026 western-year labels, FY2027 romanized Reiwa labels, and FY2028
kanji Reiwa labels are all tested as stale/current according to the configured
target fiscal year. `scripts/verify_windows_distribution.py` passed for
`dist/eidp-windows-v246.zip` with SHA256
`d2555e87bbf2d572c790fdf4417fa7703d91b38568d6b6fd3b979c0b0e898cfe`,
`git_commit=2406da413a888cb9086fedc45ecc85a3172e8e5a`, `git_dirty=false`,
`entry_count=3030`, `wheel_count=78`, `20` discovery gold-set entries, and
`47` downloadable supported prefecture seeds. Windows E2E for v246 is still
pending and must not be inferred from the Mac verifier.

v247 (`9c5e8ef`) keeps the same non-SSH boundary and adds three Stage-6
preflight hardening changes: `import-excel` now surfaces invalid fiscal-year
skips with operator-readable Japanese output, English-only renewal-form wording
is no longer a target-application hint, and the packaged runbook/verifier
contract now requires SQLite quarantine recovery guidance. `dist/eidp-windows-v247.zip`
and the latest alias `dist/eidp-windows.zip` both passed
`scripts/verify_windows_distribution.py --json` with SHA256
`c40e9a93fbbbbe3a7fcfdfb49f92052a0fbc82440b08eb0c057e3ec70f29dc3f`,
`git_commit=9c5e8ef2f57f837f31109687daf65c3d2a7e06d7`, `git_dirty=false`,
`entry_count=3030`, `wheel_count=78`, `20` discovery gold-set entries, and
`47` downloadable supported prefecture seeds. Windows E2E for v247 is still
pending and must not be inferred from the Mac verifier.

v248 (`8970c10`) further tightens candidate year evidence so publication dates
such as `2025年7月18日 更新確認申請書` or `令和7年7月18日 更新確認申請書` no
longer become stale fiscal-year evidence. Explicit fiscal-year labels
(`2025年度`, `令和7年度`) and PDF filename years such as
`2025koushinshinseisyo.pdf` still reject as stale. `dist/eidp-windows-v248.zip`
and the latest alias `dist/eidp-windows.zip` both passed
`scripts/verify_windows_distribution.py --json` with SHA256
`3829dec7448df5c26911d084862220bd12caa605b314425b7c4fd750a4ac816c`,
`git_commit=8970c105d1679fa232360f2dab70b9954a9397a7`, `git_dirty=false`,
`entry_count=3030`, `wheel_count=78`, `20` discovery gold-set entries, and
`47` downloadable supported prefecture seeds. Windows E2E for v248 is still
pending and must not be inferred from the Mac verifier.

v249 (`5e3b423`) applies the same publication-date discipline to candidate
scoring. Raw target-year token containment no longer gives priority to generic
dated posts such as `2026年7月18日 更新確認申請書`; the score bonus now follows the
same strong fiscal-year hint parser used by pre-download and strict download
checks. Non-date labels such as `2026年更新確認申請書` still receive the target-year
boost. `dist/eidp-windows-v249.zip` and the latest alias `dist/eidp-windows.zip`
both passed `scripts/verify_windows_distribution.py --json` with SHA256
`963812515d8b04698e1143c44c573c6244b694c015d33fa77dfc10bbdfb0590c`,
`git_commit=5e3b4236e85e692d506a4619a56bfa99bd2d512b`, `git_dirty=false`,
`entry_count=3030`, `wheel_count=78`, `20` discovery gold-set entries, and
`47` downloadable supported prefecture seeds. Windows E2E for v249 is still
pending and must not be inferred from the Mac verifier.

v250 (`2971fee`) tightens the candidate download budget so generic English
links such as `applicationform-r8-*.pdf` are no longer promoted to the formish
priority tier by the bare token `form`. Target-like Japanese/romaji hints and
WordPress Download Manager `wpdmdl` wrappers still keep their priority, so a
low-score target wrapper is tried before generic application-form noise can
spend the `MAX_CANDIDATE_DOWNLOAD_ATTEMPTS` budget. `dist/eidp-windows-v250.zip`
and the latest alias `dist/eidp-windows.zip` both passed
`scripts/verify_windows_distribution.py --json` with SHA256
`c800b9e8fc404a19da07a3aa5bee5aed776935cc7f0002dadd1966f4f721a2a1`,
`git_commit=2971fee8ec6bebf3e03e2b711fbecf91259d3202`, `git_dirty=false`,
`entry_count=3030`, `wheel_count=78`, `20` discovery gold-set entries, and
`47` downloadable supported prefecture seeds. Windows E2E for v250 is still
pending and must not be inferred from the Mac verifier.

v251 (`21a017d`) removes the last short-lived fiscal-year bound in the PDF
manual-entry save form. The manual PDF entry UI now allows the same long-lived
supported range as the fiscal-year override workflow (`2019` through `2099`)
instead of stopping at `2030`, so future rolling target years do not exceed the
Streamlit input maximum. `dist/eidp-windows-v251.zip` and the latest alias
`dist/eidp-windows.zip` both passed `scripts/verify_windows_distribution.py
--json` with SHA256
`99dd4054aafab862e1b7112c73f1308e6bb75c4b313f21f6c77ec1b931728ede`,
`git_commit=21a017df6b2784193735d2b693a43a961a0094c6`, `git_dirty=false`,
`entry_count=3030`, `wheel_count=78`, `20` discovery gold-set entries, and
`47` downloadable supported prefecture seeds. Windows E2E for v251 is still
pending and must not be inferred from the Mac verifier.

v252 (`ea8f1e9`) makes discovery evidence and gold-set evaluation safe for
multi-year reuse. `discover-pdfs` now records `extra.target_fiscal_year` on
every evidence row, not only accepted downloads, so no-candidate, stale-year,
prefilter, and site-fetch decisions can be replayed against the correct rolling
FY. `eval-discovery-gold --pdf-evidence` now prefers `(school_id,
target_fiscal_year)` when matching evidence to gold-set entries and skips
ambiguous old evidence for duplicate school IDs rather than silently assigning
it to the wrong year. `dist/eidp-windows-v252.zip` and the latest alias
`dist/eidp-windows.zip` both passed `scripts/verify_windows_distribution.py
--json` with SHA256
`54246d648e88a2bdbb46b7f8dfad85a35e3328e32ddce1c4f633df1bdc8a19aa`,
`git_commit=ea8f1e9e0e31202f57674b527e20a35f8c51bf9b`, `git_dirty=false`,
`entry_count=3030`, `wheel_count=78`, `20` discovery gold-set entries, and
`47` downloadable supported prefecture seeds. Windows E2E for v252 is still
pending and must not be inferred from the Mac verifier.

v253 (`94251eb`) adds a package verifier gate for the v252 rolling evidence
contract. The Windows ZIP verifier now requires packaged `pdf_discovery.py` to
record `target_fiscal_year` on discovery evidence rows and packaged
`discovery_gold_set.py` to match evidence by `(school_id, target_fiscal_year)`
before falling back to unambiguous legacy school-only evidence. This makes the
non-Windows package gate catch regressions in the multi-year discovery replay
contract, not just the unit suite. `dist/eidp-windows-v253.zip` and the latest
alias `dist/eidp-windows.zip` both passed
`scripts/verify_windows_distribution.py --json` with SHA256
`221304670352d19d4e59b0650a658e0907e14eadecc3fd205dd1475416e57792`,
`git_commit=94251ebd61b9065b97ca219255439356c198d3ab`, `git_dirty=false`,
`entry_count=3030`, `wheel_count=78`, `20` discovery gold-set entries, and
`47` downloadable supported prefecture seeds. Windows E2E for v253 is still
pending and must not be inferred from the Mac verifier.

v254 (`3078755`) promotes discovery gold-set consistency from bucket-counting
to semantic validation. The committed schema now allows `pdf_type=image_only`
for review-bound image PDFs, matching existing gold-set evidence. The source
validator and Windows ZIP verifier now reject inconsistent demonstrations, for
example `accepted_target_pdf` entries without `strict_target_year_success=true`,
publication-lag entries that are not older than the target FY, or no-candidate
/ site-fetch-error entries that still carry a PDF URL. `dist/eidp-windows-v254.zip`
and the latest alias `dist/eidp-windows.zip` both passed
`scripts/verify_windows_distribution.py --json` with SHA256
`96879550ff4185400e6a71afad4fa42be1f31687dd5021dd29a9d7db09c580d5`,
`git_commit=30787551330c35916ba93629507405c1aa1c6de0`, `git_dirty=false`,
`entry_count=3030`, `wheel_count=78`, `20` discovery gold-set entries, and
`47` downloadable supported prefecture seeds. Windows E2E for v254 is still
pending and must not be inferred from the Mac verifier.

v255 (`372119b`) adds an executable expected-predictions fixture for the full
discovery gold set. The committed
`data/discovery-gold-set/expected-predictions.jsonl` now enumerates all `20`
gold-set outcomes, and `eval-discovery-gold --fail-on-regression` is gated both
for the passing full fixture and for a mutated mismatch. The Windows ZIP
verifier now requires the fixture and checks that every packaged gold-set entry
has exactly one matching expected prediction, with no missing, duplicate,
unexpected, or mismatched rows. `dist/eidp-windows-v255.zip` and the latest
alias `dist/eidp-windows.zip` both passed
`scripts/verify_windows_distribution.py --json` with SHA256
`533a4008332bb636bf19943d3520e876dc6ea97fc30bcc3191edbefb2637703b`,
`git_commit=372119b7a5bc5020a9d10845cc9799c58aec79aa`, `git_dirty=false`,
`entry_count=3031`, `wheel_count=78`, `20` discovery gold-set entries,
`20` discovery gold expected predictions, and `47` downloadable supported
prefecture seeds. Windows E2E for v255 is still pending and must not be
inferred from the Mac verifier.

v256 (`737785e`) makes the expected-predictions fixture reproducible instead of
only committed. `eidp discovery-gold-expected-predictions` now emits the
canonical JSONL fixture directly from the current gold-set entries, and the
unit gate compares that command output byte-for-byte with
`data/discovery-gold-set/expected-predictions.jsonl`. The Windows ZIP verifier
also requires the packaged CLI to expose that generator command, so future
gold-set expansions have one deterministic regeneration path plus a package
gate that catches stale fixtures. `dist/eidp-windows-v256.zip` and the latest
alias `dist/eidp-windows.zip` both passed
`scripts/verify_windows_distribution.py --json` with SHA256
`bd3008f41e1686f55217e9a5576645480644010c2b5ddb328ee4a23af5ed9bec`,
`git_commit=737785e4697ef82a63492c6d91383e7aafaedaa0`, `git_dirty=false`,
`entry_count=3031`, `wheel_count=78`, `20` discovery gold-set entries,
`20` discovery gold expected predictions, and `47` downloadable supported
prefecture seeds. Windows E2E for v256 is still pending and must not be
inferred from the Mac verifier.

v257 (`1c61781`) tightens discovery evidence replay so accepted-download rows
cannot hide a detected fiscal-year mismatch behind the configured target FY.
`eval-discovery-gold --pdf-evidence` now uses `extra.detected_fiscal_year`
first when an accepted evidence row carries it, and only falls back to
`extra.target_fiscal_year` for trusted-year cases where the PDF itself was
yearless. A focused unit test now proves that an accepted row with
`detected_fiscal_year=2025` for target FY2026 becomes a gold-set
`fiscal_year_mismatch` failure instead of a false exact match. `dist/eidp-windows-v257.zip`
and the latest alias `dist/eidp-windows.zip` both passed
`scripts/verify_windows_distribution.py --json` with SHA256
`d3ce5c23445d6f1dd48b28bea945943cfb3b0bb387dd52ff4b061435f6367edc`,
`git_commit=1c61781c2cb9920bc5903394c2d1262420dea767`, `git_dirty=false`,
`entry_count=3031`, `wheel_count=78`, `20` discovery gold-set entries,
`20` discovery gold expected predictions, and `47` downloadable supported
prefecture seeds. Windows E2E for v257 is still pending and must not be
inferred from the Mac verifier.

v258 (`1d4d284`) makes discovery gold replay understand the real
`non_target_candidates_only` evidence shape. `eval-discovery-gold
--pdf-evidence` now maps `pre_filtered_non_target_hint`,
`classified_non_target`, and `all_negative_score` rows to
`no_target_candidate_found` when no stronger target, old-year, review, or site
failure evidence exists for the same gold-set entry. A paired priority test
keeps `fiscal_year_mismatch:*` publication-lag evidence ahead of adjacent
non-target PDF noise, so old visible target forms are still distinguished from
true no-target paths. `dist/eidp-windows-v258.zip` and the latest alias
`dist/eidp-windows.zip` both passed
`scripts/verify_windows_distribution.py --json` with SHA256
`e83e5e06d98af980aaa7d20de1c1ca889299638160bcb48e619558be03885769`,
`git_commit=1d4d284dfbd2c387dbc0e459fb1bfc49f104bc70`, `git_dirty=false`,
`entry_count=3031`, `wheel_count=78`, `20` discovery gold-set entries,
`20` discovery gold expected predictions, and `47` downloadable supported
prefecture seeds. Windows E2E for v258 is still pending and must not be
inferred from the Mac verifier.

v259 (`2231a80`) lifts the v257/v258 replay semantics into the packaged
Windows ZIP gate. The distribution verifier now requires packaged
`discovery_gold_set.py` to preserve detected fiscal years ahead of configured
target FY fallback and to keep the `non_target_candidates_only` evidence
reasons (`pre_filtered_non_target_hint`, `classified_non_target`, and
`all_negative_score`) mapped into `no_target_candidate_found`. A verifier unit
test now fails a ZIP fixture that still has the older rolling-year matching
tokens but lacks those replay semantics. `dist/eidp-windows-v259.zip` and the
latest alias `dist/eidp-windows.zip` both passed
`scripts/verify_windows_distribution.py --json` with SHA256
`d31a5de8cc3d098c2685d227140b4cb5ab911360e3900c2b966ff3ac982f0f5d`,
`git_commit=2231a80ae66f9999ce747c87e6363e13b49fa187`, `git_dirty=false`,
`entry_count=3031`, `wheel_count=78`, `20` discovery gold-set entries,
`20` discovery gold expected predictions, and `47` downloadable supported
prefecture seeds. Windows E2E for v259 is still pending and must not be
inferred from the Mac verifier.

v260 (`fb181bc`) aligns discovery gold replay priority with the RCA bucket
model for mixed site-fetch failures. `eval-discovery-gold --pdf-evidence` now
keeps `site_fetch_error` ahead of `no_target_candidate_found` when the same
school has both non-target candidate noise and a page/site fetch failure. This
prevents a mixed infrastructure failure from being reported as if the school
simply had no target PDF. Accepted target PDFs, publication-lag target PDFs,
and review-bound target forms still outrank site errors. `dist/eidp-windows-v260.zip`
and the latest alias `dist/eidp-windows.zip` both passed
`scripts/verify_windows_distribution.py --json` with SHA256
`19be7a19e31309e76d1877cd8a821e0b92829090fcaf5bc5286ba4af2e54d308`,
`git_commit=fb181bc680c98e3b6869ef661baee88b8f086da9`, `git_dirty=false`,
`entry_count=3031`, `wheel_count=78`, `20` discovery gold-set entries,
`20` discovery gold expected predictions, and `47` downloadable supported
prefecture seeds. Windows E2E for v260 is still pending and must not be
inferred from the Mac verifier.

v261 (`34c77bd`) adds the package-level guard for the v260 site-fetch priority
rule. The Windows distribution verifier now requires packaged
`discovery_gold_set.py` to keep `site_fetch_error` at priority `2`, above
`no_target_candidate_found` and below accepted/publication-lag outcomes. The
focused verifier test now fails a ZIP fixture that has the rolling-year and
non-target replay tokens but omits that priority contract. `dist/eidp-windows-v261.zip`
and the latest alias `dist/eidp-windows.zip` both passed
`scripts/verify_windows_distribution.py --json` with SHA256
`2142394f9e455f61d7c16b744a3b69372a6cdea5826b8d85ebffd4f1ffedc695`,
`git_commit=34c77bd309e3fd6b39be1b0eac63dd85cf395684`, `git_dirty=false`,
`entry_count=3031`, `wheel_count=78`, `20` discovery gold-set entries,
`20` discovery gold expected predictions, and `47` downloadable supported
prefecture seeds. Windows E2E for v261 is still pending and must not be
inferred from the Mac verifier.

v262 (`1385e19`) makes publication-lag replay deterministic when multiple old
target forms are present for the same school/year. For same-priority
`publication_lag_latest_public` predictions, `eval-discovery-gold
--pdf-evidence` now keeps the highest detected fiscal year, matching the
outcome's "latest public old-year target" meaning instead of preserving
log-order accident. `dist/eidp-windows-v262.zip` and the latest alias
`dist/eidp-windows.zip` both passed
`scripts/verify_windows_distribution.py --json` with SHA256
`4afdb8a11aaf594d7b80057e446b6083bdeffd7969e3d798e03e426f01e10427`,
`git_commit=1385e19e9a005c8b9789a5452a3ccd9ed7bf913c`, `git_dirty=false`,
`entry_count=3031`, `wheel_count=78`, `20` discovery gold-set entries,
`20` discovery gold expected predictions, and `47` downloadable supported
prefecture seeds. Windows E2E for v262 is still pending and must not be
inferred from the Mac verifier.

v263 (`7abcfc4`) adds the package-level guard for the v262 stale-target
tie-break. The Windows distribution verifier now requires packaged
`discovery_gold_set.py` to include `_is_better_tie_break_prediction`, the
`publication_lag_latest_public` same-outcome guard, and the fiscal-year
comparison that keeps the latest old public target form. The focused verifier
test now fails a ZIP fixture that has the replay priority/no-target contract but
omits the stale-target tie-break. `dist/eidp-windows-v263.zip` and the latest
alias `dist/eidp-windows.zip` both passed
`scripts/verify_windows_distribution.py --json` with SHA256
`6c3b6d11ab57054aae2496b3a1460dacbd9d6950118e90ed306b7acbb9772daf`,
`git_commit=7abcfc48e849ae57357264a74a33dcc4f8fbd565`, `git_dirty=false`,
`entry_count=3031`, `wheel_count=78`, `20` discovery gold-set entries,
`20` discovery gold expected predictions, and `47` downloadable supported
prefecture seeds. Windows E2E for v263 is still pending and must not be
inferred from the Mac verifier.

v264 (`281643c`) removes a 2020s-only ceiling from PDF body fiscal-year
extraction. The extractor's western filing-date and fallback year patterns now
accept `20xx` years instead of only `2020`-`2029`, while preserving the
configured max-fiscal-year cap so unrelated future policy references remain
excluded. New tests prove `2030.6.1` and `2031年度` PDF text still resolve through
the rolling Japanese-era formatter. Verification: `tests/unit` passed with
`1235 passed, 5 warnings`, and `dist/eidp-windows-v264.zip` plus the latest
alias `dist/eidp-windows.zip` both passed
`scripts/verify_windows_distribution.py --json` with SHA256
`eedc2fde0f9e9ab0b685c08f9358c9909d3fc4f5f52f14a1b39cf4400b905adb`,
`git_commit=281643c38c5ba25980dcf8676653deeedda421f8`, `git_dirty=false`,
`entry_count=3031`, `wheel_count=78`, `20` discovery gold-set entries,
`20` discovery gold expected predictions, and `47` downloadable supported
prefecture seeds. Windows E2E for v264 is still pending and must not be
inferred from the Mac verifier.

v265 (`5a74036`) adds the package-level guard for the v264 rolling PDF
fiscal-year parser. The Windows distribution verifier now requires packaged
`src/eidp/pdf/extractor.py` to keep `_extract_fiscal_year`, the `20xx`
western filing-date/fallback patterns, the max-fiscal-year cap, and the
Japanese-era formatter path. The focused verifier test now fails a ZIP fixture
that regresses to the old `2020`-`2029` parser. `dist/eidp-windows-v265.zip`
and the latest alias `dist/eidp-windows.zip` both passed
`scripts/verify_windows_distribution.py --json` with SHA256
`18e21a1e69f528aadea2922f861d7103cb13f950c30d459719eaa8d0f305d48c`,
`git_commit=5a740365737671477bdd1807a300294223d92a7b`, `git_dirty=false`,
`entry_count=3031`, `wheel_count=78`, `20` discovery gold-set entries,
`20` discovery gold expected predictions, and `47` downloadable supported
prefecture seeds. Windows E2E for v265 is still pending and must not be
inferred from the Mac verifier.

v266 (`7701619`) tightens the PDF extractor's rolling-year parser to the
supported business range. The parser now rejects western years before 2019
instead of treating historical policy or school-history references such as
`2005年度` / `2018年度` as the document fiscal year. The same lower bound is also
packaged in the Windows distribution verifier, so a ZIP that regresses to the
old unbounded `20xx` fallback fails the release gate. Verification:
`tests/unit` passed with `1238 passed, 5 warnings`, and
`dist/eidp-windows-v266.zip` plus the latest alias `dist/eidp-windows.zip` both
passed `scripts/verify_windows_distribution.py --json` with SHA256
`cac9640a30e53cdbc5ae6b418e644d7d4cc76f37ce23a15e20fce54ccbe15488`,
`git_commit=77016195f1c0ba3cd805702daddf4baaa5fc37f8`, `git_dirty=false`,
`entry_count=3031`, `wheel_count=78`, `20` discovery gold-set entries,
`20` discovery gold expected predictions, and `47` downloadable supported
prefecture seeds. Windows E2E for v266 is still pending and must not be
inferred from the Mac verifier.

v267 (`b67b9a1`) applies the same supported-year lower bound to strict PDF
discovery's body-year detector. `_detect_fiscal_year_from_text` now ignores
pre-2019 western/Japanese fiscal years before deciding whether a PDF body proves
the target year or an old-year mismatch, so history/old-system labels such as
`2005年度` or `2018年度` no longer preempt a later valid current-year label. The
Windows distribution verifier also requires the packaged `pdf_discovery.py`
lower-bound contract. Verification: `tests/unit` passed with
`1240 passed, 5 warnings`, and `dist/eidp-windows-v267.zip` plus the latest
alias `dist/eidp-windows.zip` both passed
`scripts/verify_windows_distribution.py --json` with SHA256
`509d4fe8d76ae6e7db56a6c5a304e366f2880c34ca5b5dcd750cc42853144825`,
`git_commit=b67b9a174a91d6d1dd5dde5492ec2892ba024f20`, `git_dirty=false`,
`entry_count=3031`, `wheel_count=78`, `20` discovery gold-set entries,
`20` discovery gold expected predictions, and `47` downloadable supported
prefecture seeds. Windows E2E for v267 is still pending and must not be
inferred from the Mac verifier.

v268 (`0e034a8`) applies the supported-year lower bound to URL/anchor fiscal-year
hints as well. Candidate hint parsing and stale-year windows now start at 2019,
so pre-supported labels or filenames such as `2018年度` and `2018007.pdf` no
longer become `fiscal_year_mismatch` evidence for otherwise target-looking
confirmation-form links. The Windows distribution verifier requires the
packaged `pdf_discovery.py` candidate-window lower-bound contract. Verification:
`tests/unit` passed with `1242 passed, 5 warnings`, and
`dist/eidp-windows-v268.zip` plus the latest alias `dist/eidp-windows.zip` both
passed `scripts/verify_windows_distribution.py --json` with SHA256
`ccd9bbe502dd119e4b0f34fcbd6d46005da1a5206f636eb0112770e4291d5230`,
`git_commit=0e034a807fc7ead330290d7569261e02c20b04c4`, `git_dirty=false`,
`entry_count=3031`, `wheel_count=78`, `20` discovery gold-set entries,
`20` discovery gold expected predictions, and `47` downloadable supported
prefecture seeds. Windows E2E for v268 is still pending and must not be
inferred from the Mac verifier.

v269 (`60cbda0`) caps PDF fiscal-year parsing and strict candidate-hint parsing
at the supported maximum year `2099`. Japanese-era labels beyond the supported
range, such as `令和82年度` (= FY2100), no longer become body-year evidence or
candidate `fiscal_year_mismatch` diagnostics. The Windows distribution verifier
requires both `MIN_SUPPORTED_FISCAL_YEAR=2019` and `MAX_SUPPORTED_FISCAL_YEAR=2099`
contracts for packaged `extractor.py` and `pdf_discovery.py`. Verification:
`tests/unit` passed with `1245 passed, 5 warnings`, and
`dist/eidp-windows-v269.zip` plus the latest alias `dist/eidp-windows.zip` both
passed `scripts/verify_windows_distribution.py --json` with SHA256
`7f24b88c30a5025736fdb7300f277552f0107fa9efd78a96c2a3321763b1f007`,
`git_commit=60cbda054ee163fa7755b8835a13afbf298bab19`, `git_dirty=false`,
`entry_count=3031`, `wheel_count=78`, `20` discovery gold-set entries,
`20` discovery gold expected predictions, and `47` downloadable supported
prefecture seeds. Windows E2E for v269 is still pending and must not be
inferred from the Mac verifier.

v270 (`8900cbc`) closes the remaining configuration-layer bypass for rolling
target fiscal years. `EIDP_TARGET_FISCAL_YEAR` and `.env` settings now fail
validation outside the same supported range `[2019, 2099]` used by PDF parsing,
strict discovery, and packaged verifier contracts. This keeps the long-lived
project from silently running an unsupported fiscal-year target even if the
environment is misconfigured. The Windows distribution verifier now requires
the packaged `config.py` target-year validator contract. Verification:
`tests/unit` passed with `1248 passed, 5 warnings`, and
`dist/eidp-windows-v270.zip` plus the latest alias `dist/eidp-windows.zip` both
passed `scripts/verify_windows_distribution.py --json` with SHA256
`ed0e0a3400ecfd1f1f526787e896f9ca55474bcdf1c13a559738265ed0b0a591`,
`git_commit=8900cbc6af2d1e442d1697db01c5947ad1ed9de3`, `git_dirty=false`,
`entry_count=3031`, `wheel_count=78`, `20` discovery gold-set entries,
`20` discovery gold expected predictions, and `47` downloadable supported
prefecture seeds. Windows E2E for v270 is still pending and must not be
inferred from the Mac verifier.

v271 (`871de0b`) aligns the operator settings UI with the same rolling
target-year bounds. The settings page now uses the shared
`MIN_SUPPORTED_TARGET_FISCAL_YEAR=2019` and `MAX_SUPPORTED_TARGET_FISCAL_YEAR=2099`
constants from `config.py`, so an operator cannot save an unsupported year that
would later fail backend configuration validation. The packaged verifier also
requires those settings-page bounds, preventing the UI/backend contract from
drifting in future ZIPs. Verification: `tests/unit` passed with
`1250 passed, 5 warnings`, and `dist/eidp-windows-v271.zip` plus the latest
alias `dist/eidp-windows.zip` both passed
`scripts/verify_windows_distribution.py --json` with SHA256
`4d0dc0455c45ce40530e54621486688c11fceaf306c886cf59e8a1d6e0e53d2c`,
`git_commit=871de0b4a2b505b7be040adb05d8f720b9fda147`, `git_dirty=false`,
`entry_count=3031`, `wheel_count=78`, `20` discovery gold-set entries,
`20` discovery gold expected predictions, and `47` downloadable supported
prefecture seeds. Windows E2E for v271 is still pending and must not be
inferred from the Mac verifier.

## 2026-05-11 Current-Code Saitama Official-Index RCA

After the discovery gold-set plan correction, a bounded current-code replay was
run against a copied Saitama RCA SQLite database, limited to the 51
`prefecture_aggregator` school-site rows. This did not run SERP discovery or
nationwide crawling.

- Source DB copy: `_temp/saitama-current51-rerun-20260511-071951/data/eidp.sqlite3`
- Evidence log: `_temp/saitama-current51-rerun-20260511-071951/logs/evidence.jsonl`
- Command scope: `eidp discover-pdfs --discovery-method
  prefecture_aggregator --batch-size 60 --rate-limit 0.5
  --request-timeout 15`
- Discovery result: `crawled=51`, `found=49`, `downloaded=1`, `failed=7`,
  `skipped=348`, `cached_rejections=38`, and `prefiltered=134`.
- Evidence summary: `evidence_rows=450`, `schools_with_evidence=51`,
  `site_scope_schools=51`.
- School-level buckets: `accepted_target_pdf=1`,
  `publication_lag_or_old_target_pdf=34`, `target_form_without_year_evidence=6`,
  `non_target_candidates_only=8`, `site_fetch_error_only=1`, and
  `no_pdf_candidates=1`.
- The accepted target PDF was for school `95` (`さいたまIT・WEB専門学校`):
  `https://www.siw.ac.jp/wp-content/themes/bsc/dist/images/information/shugakushien_shinsei2025-1-2.pdf`.
  Although the URL/anchor contains 2025, the PDF text contains the current
  target-year evidence (`令和8` / `2026`), so strict mode accepted it with
  `year_evidence="pdf_text"`.
- `ingest-pdfs --document-id 1` parsed the downloaded PDF, preserved the
  prevalidated document fiscal year 2026 despite a parsed stale-year artifact,
  and created 2 FY2026 `DepartmentYearly` rows with
  `extraction_confidence=0.94`.
- `rebuild-school-year-tasks --fiscal-year 2026 --school-type 専門学校
  --discovery-evidence-log ...` produced `excel_ready=1`. The Saitama scoped
  rows now include one `confirmed_target/parsed` school, 34 publication-lag
  schools, 6 target-year-unverified schools, and the remaining no-target rows.

Interpretation at that point: the current code no longer supported the older "Saitama 51
official URLs always produce 0 downloads" statement. It proves the official
index chain can reach a true strict FY2026 target form and an Excel-ready parsed
row, but the measured rate is still only `1/51` for this bounded Saitama set.
The goal remains far below the 60-70% strict target-FY ship gate. The dominant
work is still Layer 1 improvement and operator review handling for publication
lag, target-year-unverified, and non-target-only cases.

Follow-up from the same school `95` E2E: the accepted PDF initially created
duplicate department rows because the Excel master stored the course label as
`工業` while the PDF parser emitted `工業専門課程`. `ingest.py` now normalizes
PDF-side specialized-course labels such as `工業専門課程` to the master field
label before the existing full natural-key lookup. The name-only fallback
remains disabled.

- Regression coverage:
  `test_pdf_course_name_specialized_suffix_matches_existing_field_department`.
  The test failed before the patch with `departments_created=1` and passes
  after the patch with `departments_created=0`.
- Local focused verification:
  `uv run pytest tests/unit/test_ingest_confidence_gating.py
  tests/unit/test_normal_ingest_appendonly.py tests/unit/test_manual_entry_contract.py -q`
  → `47 passed`;
  `uv run ruff check src/eidp/pipeline/ingest.py
  tests/unit/test_ingest_confidence_gating.py` → passed.
- Real-PDF E2E replay for school `95` after the patch:
  `discover-pdfs` → `downloaded=1`; `ingest-pdfs --document-id 1` →
  `departments_created=0`, `yearly_upserted=2`;
  `rebuild-school-year-tasks` → `excel_ready=1`; `export-excel` succeeded.
  The generated workbook contains 2 `さいたまIT・WEB専門学校` rows in `学科別`
  and `在籍のみ抜粋`, not the previous 4-row split, and the 2026 values are
  written onto the existing `工業` rows.

## 2026-05-11 Current-Code Official-Index Year Evidence Update

The remaining Saitama `target_fiscal_year_not_detected` case was school `757`
(`上尾中央看護専門学校`). Manual inspection showed a strong target-form PDF body
at `https://ageo.org/files/admission/support/study_support_system.pdf`, but
the PDF URL, anchor, and body omit explicit `2026` / `令和8` labels. The page
itself is linked from the current Saitama official confirmation index, whose
artifact is dated `2026-04-01`.

The crawler now carries `trusted_year_evidence="prefecture_index_current_year"`
from `SchoolSite(discovery_method="prefecture_aggregator",
url_type="disclosure")` into strict PDF download. This evidence can accept a
yearless PDF only when the downloaded body classifies as `target`; web search,
manual, and school-URL-crawl sources still need their own PDF/URL/anchor year
evidence. The rejection cache key includes this trusted evidence so an
untrusted yearless rejection cannot poison a trusted official-index retry.

- Regression coverage:
  `test_run_pdf_discovery_marks_prefecture_disclosure_as_trusted_year_evidence`
  and
  `test_download_pdf_accepts_trusted_prefecture_year_evidence_for_target_body`.
- Focused verification:
  `uv run pytest tests/unit/test_pdf_discovery.py -q` → `57 passed,
  5 warnings`; related trusted-evidence tests → `3 passed, 5 warnings`;
  `uv run ruff check src/eidp/scraper/pdf_discovery.py
  tests/unit/test_pdf_discovery.py ...` → passed.
- Real-site replay for school `757` on a copied Saitama RCA DB:
  `_temp/saitama-school757-prefindex-trusted-20260511-094155` produced
  `crawled=1`, `found=1`, `downloaded=1`, `failed=0`. The accepted evidence
  has `detected_fiscal_year=""` and
  `year_evidence="prefecture_index_current_year"`.
- Full bounded Saitama 50-site replay on the same copied DB, with school `95`
  already ingested: `_temp/saitama-current51-prefindex-trusted-20260511-094241`
  produced `crawled=50`, `found=48`, `downloaded=1`, `failed=6`, and no
  `target_fiscal_year_not_detected` bucket. The DB now has two FY2026 target
  documents across the 51 Saitama official-index schools: school `95` and
  school `757`.
- Ingest of school `757` document `2` completed and preserved the prevalidated
  FY2026 document year, but it remains `review_pending` with
  `extraction_confidence=0.64` because the PDF course label
  `看護専門課程` does not match the master course field `医療`. This improves
  strict target acquisition (`1/51` → `2/51`) but does not make school `757`
  Excel-ready yet.

## 2026-05-11 Discovery Gold-Set Update

After the Windows v150 Saitama replay proved that Layer 0 official-index
handoff is intact and Layer 1 target-PDF acquisition is the bottleneck, two
real Saitama outcomes were added to the existing discovery gold set rather than
creating a new schema:

- `saitama-it-web-accepted-2026`: school `95`
  (`さいたまIT・WEB専門学校`) captures the only current strict FY2026 success in
  the bounded Saitama official-index replay. The URL and anchor look stale
  because they contain `2025`, but the PDF body provides FY2026 evidence, so
  this path must remain `accepted_target_pdf`.
- `ageo-central-nursing-review-2026`: school `757`
  (`上尾中央看護専門学校`) captures the remaining yearless target-form candidate.
  The crawler finds `study_support_system.pdf` from the official-index site, but
  no URL, anchor, or extracted PDF-body evidence proves FY2026. It is now
  accepted only because `prefecture_index_current_year` provides auditable
  current-year evidence from the official index.
- `urawa-specialized-school-image-review-2026`: school `761`
  (`浦和専門学校`) captures the image-only old-year support-only pattern. The
  visible anchor says `R7修学支援に関する資料` and the PDF URL contains
  `shugakushien_r7.pdf`, but neither the URL nor anchor proves a target
  application form. For FY2026 it is review-bound target-year-unverified
  evidence, not a strict target-year success and not publication-lag evidence.

The gold-set summary now has 15 entries: 6 accepted target PDFs, 6 operator
review cases, 2 publication-lag latest-public cases, and 1 no-target-candidate
case. This keeps demonstration-driven discovery work as a regression/evaluation
surface for Layer 1 while preserving the official prefectural indexes as the
primary data source.

- Focused verification:
  `uv run pytest tests/unit/test_discovery_gold_set.py
  tests/unit/test_discovery_gold_set_summary.py
  tests/unit/test_discovery_gold_set_eval.py
  tests/unit/test_cli_discovery_gold_set.py
  tests/unit/test_cli_eval_discovery_gold.py
  tests/unit/test_discovery_gold_set_seed.py -q` → `22 passed`.
- `uv run eidp discovery-gold-set --json` → `total_entries=15`,
  `accepted_target_pdf=6`, `needs_operator_review=6`,
  `publication_lag_latest_public=2`, `no_target_candidate_found=1`, and
  `strict_target_year_successes=6`.
- Combined Windows evidence for school `95` and school `757` evaluated with
  `uv run eidp eval-discovery-gold --pdf-evidence
  _temp/v150-goldset-two-school-evidence.jsonl --json` → `exact_matches=2`,
  `failed_predictions=0`, `unexpected_predictions=0`.
- Full unit regression after adding the entries and updating the count-based
  tests: `uv run pytest tests/unit -q` → `1040 passed, 5 warnings`.

## 2026-05-11 PDF Fiscal-Year Diagnostic Update

The Windows v150 Saitama replay exposed one evidence-quality defect in school
`764` (`大宮理容美容専門学校`): the 2025 confirmation-form PDF was recorded as
`fiscal_year_mismatch:2029`. Manual inspection of the real PDF showed the
`2029年度` text was an officer-term end date (`2029年度定時評議員会終結時`), not
the document fiscal year. Because `_detect_fiscal_year_from_text` only applied
the strict target-year ceiling to contextual filing dates, a future western
`20xx年度` label could override the candidate link's stale-year evidence.

The detector now applies the same `max_fiscal_year` ceiling to explicit
Japanese-era and western fiscal-year labels before accepting them as PDF-body
year evidence. In strict FY2026 discovery, impossible future years such as
`2029年度` are ignored, and the existing candidate-hint fallback can correctly
classify the same PDF as `fiscal_year_mismatch:2025`.

- Regression coverage:
  `test_detect_fiscal_year_ignores_future_western_fiscal_year_labels` and
  `test_download_pdf_uses_candidate_stale_year_when_body_only_has_future_term_year`.
- Focused verification:
  `uv run pytest tests/unit/test_pdf_discovery.py -q` → `54 passed,
  5 warnings`; `uv run ruff check src/eidp/scraper/pdf_discovery.py
  tests/unit/test_pdf_discovery.py` → passed.
- Real-PDF verification:
  `_temp/omiyaribi-2025koushinshinseisyo.pdf` from
  `https://omiyaribi.ac.jp/wp/wp-content/uploads/2025/06/2025koushinshinseisyo.pdf`
  now returns `('target', 'fiscal_year_mismatch:2025')` from `download_pdf`
  under strict FY2026 mode.
- Full unit regression after the patch:
  `uv run pytest tests/unit -q` → `1042 passed, 5 warnings`.

## 2026-05-11 v151 Update

v151 packages the discovery gold-set additions and the school `764`
future-term fiscal-year diagnostic fix. It supersedes v150 for Windows operator
delivery while preserving the same strict-yield interpretation: the package is
installation-ready, but the active automation goal remains gated by strict
current-FY target PDF yield.

- Core ZIP: `dist/eidp-windows-v151.zip`
- Latest alias: `dist/eidp-windows.zip`
- Core ZIP SHA256:
  `0966345403ec8d44c18dc5c908f685528c262c849ecc31d5041a02082285e2f5`
- Core verifier with unchanged `dist/eidp-playwright-addon-windows-v106.zip`:
  `OK core`, `OK playwright-addon`,
  `git_commit=6e1a0d814c43fce785de9784ec2bf1a27db1aaf1`,
  `git_dirty=false`, `entry_count=3018`, `wheel_count=78`,
  `project_wheel_count=1`, `discovery_gold_set_entries=14`,
  47 prefecture seed rows/parser registrations/downloadable artifact URLs,
  `prefecture_seed_school_rows_total=2148`, and add-on SHA256
  `f6fe0cd095c337a81a870decb7a18e9d1f40044dd1567b017d92eda3aae1e8e8`.
- Windows remote extraction/setup smoke on host alias `win`: copied
  `eidp-windows-v151.zip`, verified the same SHA256, expanded into
  `C:\EIDP-v151-6e1a0d8`, and ran `scripts\first_setup.bat`. The bundled
  validator reported `OK install`,
  `build_commit=6e1a0d814c43fce785de9784ec2bf1a27db1aaf1`,
  `build_dirty=false`, `school_count=2418`,
  `school_fiscal_year_status_count=2418`, required SQLite tables present, and
  `wheel_count=78`. A separate `scripts\validate_windows_install.py . --json`
  run returned `ok=true` with no errors or warnings.
- Windows packaged Saitama official-index apply on that v151 extraction:
  `bootstrap_pdf_pipeline.py --pref saitama --skip-known-url-discovery
  --url-search off --school-url-crawl off --skip-discover` produced
  `extracted=58`, `matched=51`, `added=51`, `skipped=7`, and
  `review_items=2`.
- Windows packaged school `764` fiscal-year diagnostic smoke:
  `discover-pdfs --discovery-method prefecture_aggregator --school-id 764`
  produced `crawled=1`, `found=1`, `downloaded=0`, `failed=0`,
  `prefiltered=2`, `rejection_reason_fiscal_year_mismatch=7`,
  `rejection_reason_classified_non_target=1`, and
  `rejection_reason_pre_filtered_non_target_hint=2`. The evidence row for
  `2025koushinshinseisyo.pdf` is now `fiscal_year_mismatch:2025`, and no
  `2029` reject bucket remains.

## 2026-05-11 v152 Update

v152 packages the official-index trusted year-evidence rule for body-confirmed,
yearless target confirmation forms. It supersedes v151 for Windows operator
delivery while keeping the same ship-gate interpretation: Saitama strict
current-FY acquisition improves from `1/51` to `2/51`, but the result remains
far below the 60-70% automation target.

- Core ZIP: `dist/eidp-windows-v152.zip`
- Latest alias: `dist/eidp-windows.zip`
- Core ZIP SHA256:
  `1b91ee2dd1ac577a45f5d5afa8cdd4c747c5c57544c0c7ad47839a7eb0e58afb`
- Core verifier with unchanged `dist/eidp-playwright-addon-windows-v106.zip`:
  `OK core`, `OK playwright-addon`,
  `git_commit=d90d0a16d382d87f51ae3ecce433198a087eb748`,
  `git_dirty=false`, `entry_count=3018`, `wheel_count=78`,
  `project_wheel_count=1`, `discovery_gold_set_entries=14`,
  `discovery_gold_set_outcomes={"accepted_target_pdf": 6,
  "needs_operator_review": 5, "no_target_candidate_found": 1,
  "publication_lag_latest_public": 2}`, 47 prefecture seed rows/parser
  registrations/downloadable artifact URLs, `prefecture_seed_school_rows_total=2148`,
  and add-on SHA256
  `f6fe0cd095c337a81a870decb7a18e9d1f40044dd1567b017d92eda3aae1e8e8`.
- Windows remote extraction/setup smoke on host alias `win`: copied
  `eidp-windows-v152.zip`, verified the same SHA256, expanded into
  `C:\EIDP-v152-d90d0a1`, and ran `scripts\first_setup.bat`. The bundled
  validator reported `OK install`,
  `build_commit=d90d0a16d382d87f51ae3ecce433198a087eb748`,
  `build_dirty=false`, `school_count=2418`,
  `school_fiscal_year_status_count=2418`, required SQLite tables present, and
  `wheel_count=78`. A separate `scripts\validate_windows_install.py . --json`
  run returned `ok=true` with no errors or warnings.
- Windows packaged Saitama official-index apply on that v152 extraction:
  `bootstrap_pdf_pipeline.py --pref saitama --skip-known-url-discovery
  --url-search off --school-url-crawl off --skip-discover` produced
  `extracted=58`, `matched=51`, `added=51`, `skipped=7`, and
  `review_items=2`.
- Windows packaged school `757` strict discovery smoke:
  `discover-pdfs --discovery-method prefecture_aggregator --school-id 757`
  produced `crawled=1`, `found=1`, `downloaded=1`, `failed=0`, and
  `rejection_reason_classified_non_target=8`. The accepted evidence row is
  `https://ageo.org/files/admission/support/study_support_system.pdf` with
  `detected_fiscal_year=""` and
  `year_evidence="prefecture_index_current_year"`.
- Windows packaged school `757` ingest smoke:
  `ingest-pdfs --document-id 1` completed with `processed=1`,
  `departments_created=1`, and `yearly_upserted=1`. The document is preserved
  as `fiscal_year=2026`, `pdf_type=target`, `is_current_year=True`, and
  `ingest_status=review_pending`; the generated FY2026 yearly row is
  `看護専門課程` / `第一学科` with `extraction_confidence=0.64` and
  `is_current=False`. This proves packaged acquisition, not Excel readiness,
  for school `757`.

## 2026-05-11 v153 Update

v153 keeps the v152 strict acquisition behavior and fixes the next school `757`
ingest issue: the PDF spells the course field as `看護専門課程`, while the
Excel master stores the same department under the broader field `医療`. The
PDF-side course normalization now maps the exact field alias `看護` to `医療`
before full natural-key Department lookup. This prevents a duplicate
Department row for the accepted school `757` target PDF, but it still does not
make the row Excel-ready because the parsed data confidence remains below the
0.70 gate.

- Code change: `_normalize_pdf_course_name` now maps `看護専門課程` to the
  master field label `医療`. The existing no-name-only-fallback guard remains
  unchanged.
- Regression coverage:
  `test_pdf_nursing_course_name_matches_existing_medical_field_department`.
  The test failed before the patch with `departments_created=1` and passes
  after the patch with `departments_created=0`. The existing
  `工業専門課程` normalization test also remains green.
- Local verification:
  `uv run pytest tests/unit/test_ingest_confidence_gating.py -q -k
  "nursing_course_name or specialized_suffix"` → `2 passed`;
  `uv run ruff check src/eidp/pipeline/ingest.py
  tests/unit/test_ingest_confidence_gating.py` → passed;
  `uv run pytest tests/unit/test_ingest_confidence_gating.py
  tests/unit/test_normal_ingest_appendonly.py
  tests/unit/test_manual_entry_contract.py -q` → `48 passed`;
  `uv run pytest tests/unit -q` → `1045 passed, 5 warnings`.
- Known type-check caveat:
  `uv run mypy src/eidp/pipeline/ingest.py` still reports existing strict
  typing debt around the mixed-type `stats` dictionary; those errors are not
  introduced by this alias patch and were not broadened in this small fix.
- Real-site replay on a copied Saitama RCA DB:
  `_temp/saitama-school757-ingest-medical-alias-20260511-101321` produced
  `discover-pdfs` `downloaded=1`; `ingest-pdfs --document-id 2` completed with
  `processed=1`, `departments_created=0`, and `yearly_upserted=1`. The only
  school `757` Department remains `(course_name="医療",
  canonical_name="第一学科")`, and the FY2026 yearly row is attached to that
  Department with `extraction_confidence=0.64` and `is_current=False`.
- Core ZIP: `dist/eidp-windows-v153.zip`
- Latest alias: `dist/eidp-windows.zip`
- Core ZIP SHA256:
  `76b4e9420732ac287423bf492d9f0f69ff60c0532b08ea1576d7f111f07f5930`
- Core verifier with unchanged `dist/eidp-playwright-addon-windows-v106.zip`:
  `OK core`, `OK playwright-addon`,
  `git_commit=910afadeaf77002f541b5e1bc4ccb8870a56122f`,
  `git_dirty=false`, `entry_count=3018`, `wheel_count=78`,
  `project_wheel_count=1`, `discovery_gold_set_entries=14`,
  47 prefecture seed rows/parser registrations/downloadable artifact URLs,
  `prefecture_seed_school_rows_total=2148`, and add-on SHA256
  `f6fe0cd095c337a81a870decb7a18e9d1f40044dd1567b017d92eda3aae1e8e8`.
- Windows remote extraction/setup smoke on host alias `win`: copied
  `eidp-windows-v153.zip`, verified the same SHA256, expanded into
  `C:\EIDP-v153-910afad`, and ran `scripts\first_setup.bat`. The bundled
  validator reported `OK install`,
  `build_commit=910afadeaf77002f541b5e1bc4ccb8870a56122f`,
  `build_dirty=false`, `school_count=2418`,
  `school_fiscal_year_status_count=2418`, required SQLite tables present, and
  `wheel_count=78`. A separate `scripts\validate_windows_install.py . --json`
  run returned `ok=true` with no errors or warnings.
- Windows packaged school `757` strict discovery + ingest smoke:
  after Saitama official-index apply (`extracted=58`, `matched=51`,
  `added=51`), `discover-pdfs --discovery-method prefecture_aggregator
  --school-id 757` produced `downloaded=1`, and
  `ingest-pdfs --document-id 1` produced `processed=1`,
  `departments_created=0`, and `yearly_upserted=1`. The document remains
  `review_pending`, and the FY2026 yearly row remains non-current with
  `extraction_confidence=0.64`.

## 2026-05-11 v154 Update

v154 finishes the school `757` strict target path through Excel export. v152
made the yearless official-index target PDF acceptable, and v153 attached the
parsed row to the existing `医療` / `第一学科` Department. v154 fixes the
remaining confidence blocker by parsing sparse graduation rows where
`進学者数` and `その他` are blank but `卒業者数` and `就職者数` are present
on the same line (`86 人 人 86 人 人`). This gives school `757` all required
fields and moves the FY2026 row from review-only to current.

- Code change: `_parse_department_section` now keeps the graduate count when a
  graduation row has four `人` cells but only one or two numeric values. In the
  school `757` PDF this parses `graduates=86` and `employed=86`.
- Regression coverage:
  `test_graduation_row_with_blank_advanced_and_other_keeps_graduate_count`.
  The test failed before the patch with `graduates=None` and passes after the
  patch with `graduates=86`.
- Local verification:
  `uv run pytest tests/unit/test_pdf_parser_regression.py -q -k
  "blank_advanced"` → `1 passed`; `uv run pytest
  tests/unit/test_pdf_parser_regression.py -q` → `9 passed`;
  `uv run ruff check src/eidp/pdf/extractor.py
  tests/unit/test_pdf_parser_regression.py` → passed;
  real school `757` parse now returns `graduates=86` and
  `ConfidenceBreakdown(... composite=0.94)`;
  `uv run pytest tests/unit/test_pdf_parser_regression.py
  tests/unit/test_ingest_confidence_gating.py
  tests/unit/test_normal_ingest_appendonly.py
  tests/unit/test_manual_entry_contract.py -q` → `57 passed`;
  `uv run pytest tests/unit -q` → `1046 passed, 5 warnings`.
- Real-site replay on a copied Saitama RCA DB:
  `_temp/saitama-school757-current-after-graduates-20260511-102416`
  produced strict discovery `downloaded=1`; `ingest-pdfs --document-id 2`
  produced `processed=1`, `departments_created=0`, `yearly_upserted=1`,
  `yearly_current=1`, and `yearly_review_pending=0`. The FY2026 yearly row is
  attached to the existing `医療` / `第一学科` Department with
  `capacity=300`, `enrollment=263`, `graduates=86`,
  `extraction_confidence=0.94`, and `is_current=True`.
- Core ZIP: `dist/eidp-windows-v154.zip`
- Latest alias: `dist/eidp-windows.zip`
- Core ZIP SHA256:
  `fea99a950b0b671c75202cf470d4c06c6169bc299e013c0b45f3caaabe417952`
- Core verifier with unchanged `dist/eidp-playwright-addon-windows-v106.zip`:
  `OK core`, `OK playwright-addon`,
  `git_commit=26d18a9aac2cc2e89705f3de5551f7003e8091f8`,
  `git_dirty=false`, `entry_count=3018`, `wheel_count=78`,
  `project_wheel_count=1`, `discovery_gold_set_entries=14`,
  47 prefecture seed rows/parser registrations/downloadable artifact URLs,
  `prefecture_seed_school_rows_total=2148`, and add-on SHA256
  `f6fe0cd095c337a81a870decb7a18e9d1f40044dd1567b017d92eda3aae1e8e8`.
- Windows remote extraction/setup smoke on host alias `win`: copied
  `eidp-windows-v154.zip`, verified the same SHA256, expanded into
  `C:\EIDP-v154-26d18a9`, and ran `scripts\first_setup.bat`. The bundled
  validator reported `OK install`,
  `build_commit=26d18a9aac2cc2e89705f3de5551f7003e8091f8`,
  `build_dirty=false`, `school_count=2418`,
  `school_fiscal_year_status_count=2418`, required SQLite tables present, and
  `wheel_count=78`. A separate `scripts\validate_windows_install.py . --json`
  run returned `ok=true` with no errors or warnings.
- Windows packaged school `757` strict discovery → ingest → status → Excel
  smoke:
  after Saitama official-index apply (`extracted=58`, `matched=51`,
  `added=51`), `discover-pdfs --discovery-method prefecture_aggregator
  --school-id 757` produced `downloaded=1`; `ingest-pdfs --document-id 1`
  produced `processed=1`, `departments_created=0`, `yearly_upserted=1`,
  `yearly_current=1`; `rebuild-school-year-tasks --fiscal-year 2026
  --school-type 専門学校` produced `excel_ready=1`; and `export-excel
  --output output\v154_school757_export.xlsx` succeeded.
- Windows DB/XLSX verification for that packaged smoke: document `1` is
  `fiscal_year=2026`, `pdf_type=target`, `ingest_status=ingested`, and
  `is_current_year=1`; the FY2026 yearly row is
  `医療` / `第一学科`, `capacity=300`, `enrollment=263`, `graduates=86`,
  `extraction_confidence=0.94`, and `is_current=True`; the
  `school_fiscal_year_status` row is `pdf_status=confirmed_target`,
  `evidence_level=prev_year_diff`, `blocking_reason=NULL`, and
  `excel_ready=True`; the exported workbook contains one
  `上尾中央看護専門学校` row in `学科別` and one in `在籍のみ抜粋`.

## 2026-05-11 v146 Update

v146 packages the school `95` real-PDF ingestion fix and verifies it on the
remote Windows handoff path. This version does not raise nationwide strict
FY2026 yield by itself; it prevents a confirmed target PDF from splitting one
real school into duplicate departments when the PDF spells the master course
field as a specialized-course label such as `工業専門課程`.

- Core ZIP: `dist/eidp-windows-v146.zip`
- Latest alias: `dist/eidp-windows.zip`
- Core ZIP SHA256:
  `ab683820e42ca44f91319bafef2a1c6454edfb6949aaba97b8ff3c3fd0f04978`
- Core verifier with unchanged `dist/eidp-playwright-addon-windows-v106.zip`:
  `OK core`, `OK playwright-addon`,
  `git_commit=e9143866ec6b1ad1018402b02e7dae7e7c4f8a7c`,
  `git_dirty=false`, `entry_count=3016`, `wheel_count=78`,
  `project_wheel_count=1`, 47 prefecture seed rows/parser registrations/
  downloadable artifact URLs, `prefecture_seed_school_rows_total=2148`,
  `discovery_gold_set_entries=12`, and add-on SHA256
  `f6fe0cd095c337a81a870decb7a18e9d1f40044dd1567b017d92eda3aae1e8e8`.
- Windows remote extraction/setup smoke on host alias `win`: copied
  `eidp-windows-v146.zip`, verified the same SHA256, expanded into
  `C:\EIDP-v146-e914386`, and ran `scripts\first_setup.bat`. The bundled
  validator reported `ok=true`, `errors=[]`, `warnings=[]`,
  `build_commit=e9143866ec6b1ad1018402b02e7dae7e7c4f8a7c`,
  `build_dirty=false`, `school_count=2418`,
  `school_fiscal_year_status_count=2418`, required SQLite tables present, and
  `wheel_count=78`.
- Windows packaged school `95` strict target-flow smoke on the same extraction:
  `discover-pdfs --discovery-method prefecture_aggregator --school-id 95`
  downloaded 1 target PDF; `ingest-pdfs --document-id 1` produced
  `departments_created=0` and `yearly_upserted=2`;
  `rebuild-school-year-tasks --fiscal-year 2026` rebuilt 2418 rows with
  `excel_ready=1`; `export-excel` wrote
  `C:\EIDP-v146-e914386\output\v146_school95_export.xlsx`.
- Windows DB/XLSX verification for that packaged smoke: document `1` is
  `fiscal_year=2026`, `pdf_type=target`, `ingest_status=ingested`, and
  `is_current_year=1`; school `95` still has 2 master departments;
  FY2026 `DepartmentYearly` rows for the document are 2; current FY2026 rows
  are 2; `school_fiscal_year_status` is
  `pdf_status=confirmed_target`, `evidence_level=prev_year_diff`,
  `blocking_reason=NULL`, `excel_ready=1`; the exported workbook contains 2
  `さいたまIT・WEB専門学校` rows in `学科別` and 2 in `在籍のみ抜粋`.

## 2026-05-11 v147 Update

v147 tightens stale-year diagnostics for real Saitama official-index target
forms whose PDF body has no usable fiscal-year text but whose link text clearly
names an older Japanese fiscal year such as `令和7年度確認申請書`. Before this
patch, those rows could remain in `target_fiscal_year_not_detected`, which
inflates the operator's `年度未確認候補` queue. They are now classified as
`fiscal_year_mismatch:<western-year>` and therefore flow into the existing
publication-lag/old-year review lane.

- Code change: `_stale_fiscal_year_from_candidate_hint` now reuses the strong
  candidate fiscal-year parser before falling back to western-year filename
  scanning.
- Regression coverage:
  `test_download_pdf_rejects_stale_reiwa_year_from_anchor_when_body_has_no_year`.
  The test failed before the patch with `target_fiscal_year_not_detected` and
  passes after the patch with `fiscal_year_mismatch:2025`.
- Bounded real-site replay:
  `_temp/saitama-stale-anchor-replay-20260511-075410` against school `773`
  (`越谷保育専門学校`) on a copied Saitama RCA SQLite database. The replay
  produced `rejection_reason_fiscal_year_mismatch=6`,
  `rejection_reason_target_fiscal_year_not_detected=1`, and no downloads.
  The six target-form rows with anchors `令和2年度確認申請書` through
  `令和7年度確認申請書` are now `fiscal_year_mismatch:2020` through
  `fiscal_year_mismatch:2025`.
- Verification:
  `uv run pytest tests/unit/test_pdf_discovery.py -q` → `49 passed`;
  `uv run pytest tests/unit/test_pdf_discovery.py
  tests/unit/test_discovery_evidence_summary.py
  tests/unit/test_school_fiscal_year_status.py -q` → `64 passed`;
  `uv run ruff check src/eidp/scraper/pdf_discovery.py
  tests/unit/test_pdf_discovery.py` → passed;
  `uv run pytest tests/unit -q` → `1034 passed, 5 warnings`.
- Core ZIP: `dist/eidp-windows-v147.zip`
- Latest alias: `dist/eidp-windows.zip`
- Core ZIP SHA256:
  `bff5186fecc30d0c0ae64bcaa249ef6117d645331d5d36761dd2b3faab794828`
- Core verifier with unchanged `dist/eidp-playwright-addon-windows-v106.zip`:
  `OK core`, `OK playwright-addon`,
  `git_commit=b80bfcfc97a6163ccedde4d45c83099f89e59a3b`,
  `git_dirty=false`, `entry_count=3016`, `wheel_count=78`,
  `project_wheel_count=1`, 47 prefecture seed rows/parser registrations/
  downloadable artifact URLs, `prefecture_seed_school_rows_total=2148`,
  `discovery_gold_set_entries=12`, and add-on SHA256
  `f6fe0cd095c337a81a870decb7a18e9d1f40044dd1567b017d92eda3aae1e8e8`.

## 2026-05-11 v148 Update

v148 extends the v147 stale-year classification to CMS pages where the fiscal
year is rendered next to, but outside, the PDF anchor text. This is a real
pattern in Goope pages: a paragraph such as `◆2025年度(令和7年度)` is followed by
the PDF link whose anchor is only `確認申請様式`. Without adjacent block context,
strict discovery cannot tell that the candidate is an old-year target form.

- Code change: `_extract_pdf_links` now enriches the anchor text with
  fiscal-year context from the current or immediately previous simple HTML
  block (`p`, `li`, `tr`) when the CMS splits year labels from PDF links.
  The download URL is unchanged, and dedupe remains URL-based.
- Regression coverage:
  `test_download_pdf_rejects_stale_year_from_adjacent_html_context`.
  The test failed before the patch with `target_fiscal_year_not_detected` and
  passes after the patch with `fiscal_year_mismatch:2025`.
- Bounded real-site replay:
  `_temp/saitama-goope-context-replay-20260511-080216` against school `777`
  on a copied Saitama RCA SQLite database. The replay produced
  `rejection_reason_fiscal_year_mismatch=7`,
  `rejection_reason_target_fiscal_year_not_detected=0`, and no downloads. The
  seven Goope target-form links are now classified as
  `fiscal_year_mismatch:2019` through `fiscal_year_mismatch:2025` instead of
  target-year-unverified manual work.
- Verification:
  `uv run pytest tests/unit/test_pdf_discovery.py -q` → `50 passed`;
  `uv run pytest tests/unit/test_discovery_evidence_summary.py
  tests/unit/test_school_fiscal_year_status.py -q` → `15 passed`;
  `uv run ruff check src/eidp/scraper/pdf_discovery.py
  tests/unit/test_pdf_discovery.py` → passed;
  `uv run pytest tests/unit -q` → `1035 passed, 5 warnings`.
- Core ZIP: `dist/eidp-windows-v148.zip`
- Latest alias: `dist/eidp-windows.zip`
- Core ZIP SHA256:
  `59047be094e649f4cb59f98d01f9167886b33783ff4970ea0af6aa59e8133f67`
- Core verifier with unchanged `dist/eidp-playwright-addon-windows-v106.zip`:
  `OK core`, `OK playwright-addon`,
  `git_commit=b06d3419b3a2bc3c9fcabcc845a433cb8759f861`,
  `git_dirty=false`, `entry_count=3016`, `wheel_count=78`,
  `project_wheel_count=1`, 47 prefecture seed rows/parser registrations/
  downloadable artifact URLs, `prefecture_seed_school_rows_total=2148`,
  `discovery_gold_set_entries=12`, and add-on SHA256
  `f6fe0cd095c337a81a870decb7a18e9d1f40044dd1567b017d92eda3aae1e8e8`.

## 2026-05-11 v149 Update

v149 closes the remaining `令和元年度` first-year Japanese-era parsing edge
found in the Saitama official-index RCA. Before this patch, an image-only
target-form link such as `3．令和元年度確認申請書` could remain in
`target_fiscal_year_not_detected` because the fiscal-year parser accepted
numeric era years such as `令和1年度` but not the common `元年度` spelling.

- Code change: `fiscal_year_from_japanese_era_text` now parses `元年度` and
  filing dates such as `元年6月1日` as era year 1. Search tokens also include
  the first-year label, e.g. `令和元`.
- Code change: `_pdf_anchor_context_text` no longer appends the previous
  fiscal-year block when the anchor/current block already contains a fiscal
  year. This avoids mixed anchor evidence such as `令和7年度 ... 令和6年度`.
- Regression coverage:
  `test_fiscal_year_from_japanese_era_text_parses_labels_and_dates`,
  `test_era_alias_layer_can_be_reconfigured_for_future_era`,
  `test_download_pdf_rejects_reiwa_first_year_anchor_for_image_only_target`,
  and `test_extract_pdf_links_does_not_append_previous_year_when_anchor_has_year`.
- Bounded real-site replay:
  `_temp/saitama-reiwa-gannen-replay-20260511-082352` against school `773`
  on a copied Saitama RCA SQLite database. The `令和元年度確認申請書` image-only
  row is now `fiscal_year_mismatch:2019`, and the `令和7年度確認申請書` anchor is
  no longer polluted by the previous `令和6年度` label.
- Full current Saitama replay after the patch:
  `_temp/saitama-current51-v149-rerun-20260511-082438` against the same copied
  official-index RCA database. Because school `95` already had a current target
  document in the copied DB, the replay crawled 50 sites: `crawled=50`,
  `found=48`, `downloaded=0`, `failed=6`, `skipped=348`,
  `cached_rejections=36`, and `prefiltered=138`. Rejection counts were
  `classified_non_target=166`, `fiscal_year_mismatch=171`,
  `pre_filtered_non_target_hint=90`, `target_fiscal_year_not_detected=1`,
  `no_candidates_found=1`, `discovery_error=1`, `all_negative_score=10`,
  `not_pdf_magic=5`, and `http_error:HTTPStatusError=4`.
- The only remaining `target_fiscal_year_not_detected` school in that replay is
  school `757` (`上尾中央看護専門学校`) with anchor `確認申請` and PDF
  `https://ageo.org/files/admission/support/study_support_system.pdf`. This
  remains operator/OCR confirmation work unless stronger year evidence is found.
- Verification:
  `uv run pytest tests/unit/test_fiscal_year.py
  tests/unit/test_pdf_discovery.py tests/unit/test_discovery_evidence_summary.py
  tests/unit/test_school_fiscal_year_status.py -q` → `72 passed`;
  `uv run ruff check src/eidp/fiscal_year.py tests/unit/test_fiscal_year.py
  src/eidp/scraper/pdf_discovery.py tests/unit/test_pdf_discovery.py` → passed;
  `uv run pytest tests/unit -q` → `1037 passed, 5 warnings`.
- Core ZIP: `dist/eidp-windows-v149.zip`
- Latest alias: `dist/eidp-windows.zip`
- Core ZIP SHA256:
  `ca456a355781cf60e0fb3ccec06b4e3c8a2e75f1e8df42e3e9b0100a0340051b`
- Core verifier with unchanged `dist/eidp-playwright-addon-windows-v106.zip`:
  `OK core`, `OK playwright-addon`,
  `git_commit=0dc3d2e5fff5e09300e7d126f55735f90baa995e`,
  `git_dirty=false`, `entry_count=3016`, `wheel_count=78`,
  `project_wheel_count=1`, 47 prefecture seed rows/parser registrations/
  downloadable artifact URLs, `prefecture_seed_school_rows_total=2148`,
  `discovery_gold_set_entries=12`, and add-on SHA256
  `f6fe0cd095c337a81a870decb7a18e9d1f40044dd1567b017d92eda3aae1e8e8`.

## 2026-05-11 v150 Update

v150 supersedes v149 for Windows operator delivery. A remote Windows v149
packaged E2E attempt found a real CLI blocker: `first_setup.bat` succeeded,
Saitama official-index aggregation succeeded, and school `95` strict discovery
downloaded the FY2026 target PDF, but `eidp ingest-pdfs --document-id 1`
crashed while logging `さいたまIT・WEB専門学校` because the SSH/cmd console was
using a non-UTF-8 code page (`UnicodeEncodeError: 'gbk' codec can't encode
character '\u30fb'`). The bootstrap script already protected its own stdout,
but the Typer CLI entrypoint did not.

- Code change: `src/eidp/cli.py` now configures `sys.stdout` and `sys.stderr`
  with `encoding="utf-8", errors="replace"` at import time. This covers all
  installed `eidp` CLI commands, including structlog output during PDF ingest.
- Regression coverage:
  `test_configure_utf8_stdio_sets_replace_errors` in
  `tests/unit/test_cli_ingest.py`.
- Verification before packaging:
  `uv run pytest tests/unit/test_cli_ingest.py -q` → `2 passed`;
  `uv run ruff check src/eidp/cli.py tests/unit/test_cli_ingest.py` → passed;
  `uv run pytest tests/unit -q` → `1038 passed, 5 warnings`.
- Core ZIP: `dist/eidp-windows-v150.zip`
- Latest alias: `dist/eidp-windows.zip`
- Core ZIP SHA256:
  `5395b14b2f5263bc0138a04c7b2cd32ff6debffb4435bc079ff06f715672f923`
- Core verifier with unchanged `dist/eidp-playwright-addon-windows-v106.zip`:
  `OK core`, `OK playwright-addon`,
  `git_commit=d303b44c239706ccd7cdca854c3e53c9a66b3d4e`,
  `git_dirty=false`, `entry_count=3016`, `wheel_count=78`,
  `project_wheel_count=1`, 47 prefecture seed rows/parser registrations/
  downloadable artifact URLs, `prefecture_seed_school_rows_total=2148`,
  `discovery_gold_set_entries=12`, and add-on SHA256
  `f6fe0cd095c337a81a870decb7a18e9d1f40044dd1567b017d92eda3aae1e8e8`.
- Windows remote extraction/setup smoke on host alias `win`: copied
  `eidp-windows-v150.zip`, verified the same SHA256, expanded into
  `C:\EIDP-v150-d303b44`, and ran `scripts\first_setup.bat`. The bundled
  validator reported `OK install`, `build_commit=d303b44c239706ccd7cdca854c3e53c9a66b3d4e`,
  `build_dirty=false`, `school_count=2418`,
  `school_fiscal_year_status_count=2418`, required SQLite tables present, and
  `wheel_count=78`.
- Windows packaged school `95` strict target-flow smoke on that v150
  extraction: Saitama official index step produced
  `extracted=58`, `matched=51`, `added=51`, `review_items=2`; strict
  `discover-pdfs --discovery-method prefecture_aggregator --school-id 95`
  produced `downloaded=1`; `ingest-pdfs --document-id 1` completed without the
  v149 Unicode crash and produced `departments_created=0`,
  `yearly_upserted=2`; `rebuild-school-year-tasks --fiscal-year 2026`
  produced `excel_ready=1`; `export-excel --output
  output\v150_school95_export.xlsx` succeeded.
- Windows DB/XLSX verification for that packaged smoke: document `1` is
  `fiscal_year=2026`, `pdf_type=target`, `ingest_status=ingested`, and
  `is_current_year=1`; school `95` has 2 master departments and 2 current
  FY2026 `DepartmentYearly` rows; `school_fiscal_year_status` is
  `pdf_status=confirmed_target`, `evidence_level=prev_year_diff`,
  `blocking_reason=NULL`, `excel_ready=1`; the exported workbook contains 2
  `さいたまIT・WEB専門学校` rows in `学科別` and 2 in `在籍のみ抜粋`.
- Windows packaged Saitama 51-site replay on the same v150 extraction:
  the database contained 51 Saitama `prefecture_aggregator` `SchoolSite` rows.
  Because school `95` already had the accepted target document, the packaged
  `discover-pdfs --discovery-method prefecture_aggregator --batch-size 60`
  command crawled the remaining 50 sites and wrote evidence to
  `C:\EIDP-v150-d303b44\logs\v150_saitama51_evidence.jsonl`. The run produced
  evidence for all 50 remaining schools, no missing official-index handoff
  rows, and no additional current-FY target downloads. Evidence rows totaled
  449: `classified_non_target=166`, `fiscal_year_mismatch=171`,
  `pre_filtered_non_target_hint=90`, `all_negative_score=10`,
  `not_pdf_magic=5`, `http_error:HTTPStatusError=4`,
  `target_fiscal_year_not_detected=1`, `no_candidates_found=1`, and
  `discovery_error=1`. The only remaining
  `target_fiscal_year_not_detected` school was `757`; school `773`
  `令和元年度確認申請書` stayed classified as `fiscal_year_mismatch:2019`, and
  school `777` adjacent-year Goope target links stayed classified as old-year
  mismatches rather than target-year-unverified work.

## 2026-05-11 v145 Update

v145 keeps the v144 strict acquisition behavior and improves the operator task
surface for the remaining `target_form_without_year_evidence` bucket. These are
schools where the crawler found a likely confirmation-form PDF but could not
prove the configured target fiscal year from PDF text or URL/link hints.

- `school_fiscal_year_status` rebuild now maps evidence bucket
  `target_form_without_year_evidence` to
  `pdf_status="target_year_unverified"`,
  `evidence_level="target_year_unverified"`, and
  `blocking_reason="target_year_unverified"`, with `excel_ready=false`.
- The task board labels the state as `年度未確認候補` and routes the next
  action to `PDF確認` with copy telling the operator to confirm the PDF body,
  OCR result, or publication year. It is counted in the existing
  `PDF確認・手入力` work lane rather than hidden inside generic
  `対象年度PDF待ち`.
- Regression coverage:
  `test_rebuild_marks_target_form_without_year_evidence_as_review_state`,
  `test_operator_labels_hide_internal_status_codes`, and
  `test_next_action_surfaces_target_year_unverified_review`.
- Local verification:
  focused red/green tests for the new status mapping and labels;
  `uv run pytest tests/unit/test_school_fiscal_year_status.py tests/unit/test_review_school_year_tasks.py -q`
  → `66 passed`;
  Ruff passed on touched runtime/test files;
  mypy passed on touched runtime modules;
  `uv run pytest tests/unit -q` → `1032 passed, 5 warnings`.
- Core ZIP: `dist/eidp-windows-v145.zip`
- Latest alias: `dist/eidp-windows.zip`
- Core ZIP SHA256:
  `6400786be10d60bde1f750c810a6d7e56e5b67a0a8f62bc1cb19ecf5b5ca0c54`
- Core verifier with unchanged `dist/eidp-playwright-addon-windows-v106.zip`:
  `OK core`, `OK playwright-addon`,
  `git_commit=7407f36f71156283cf67c45199abf2b085ab8baf`,
  `git_dirty=false`, `entry_count=3016`, `wheel_count=78`,
  47 prefecture seed rows/parser registrations/downloadable artifact URLs,
  `discovery_gold_set_entries=12`, and add-on SHA256
  `f6fe0cd095c337a81a870decb7a18e9d1f40044dd1567b017d92eda3aae1e8e8`.
- Windows remote extraction/setup smoke on host alias `win`: copied
  `eidp-windows-v145.zip`, verified the same SHA256, expanded into
  `C:\EIDP-v145-7407f36`, and ran `scripts\first_setup.bat`. The setup
  completed offline wheelhouse install, SQLite bootstrap, master Excel import,
  and FY2026 task rebuild. The bundled validator reported `OK install`,
  `build_commit=7407f36f71156283cf67c45199abf2b085ab8baf`,
  `build_dirty=false`, `school_count=2418`,
  `school_fiscal_year_status_count=2418`, required SQLite tables present, and
  `wheel_count=78`.
- Windows packaged synthetic status rebuild smoke wrote one evidence row with
  `reason="target_fiscal_year_not_detected"` and `pdf_type="target"`, ran
  `eidp rebuild-school-year-tasks --fiscal-year 2026
  --discovery-evidence-log output\v145_target_year_unverified_evidence.jsonl`,
  and queried SQLite directly. The row became
  `(1, 'no_url', 'target_year_unverified', 'target_year_unverified',
  'target_year_unverified', 0)`.

v145 does not improve strict FY2026 download yield by itself. It preserves the
remaining no-year target-form candidates as explicit operator review work
instead of losing them in the generic no-target bucket.

## 2026-05-11 v144 Update

v144 is a narrow follow-up to the v143 bounded RCA. It does not change strict
FY2026 success criteria; it improves stale target-form classification when a
school publishes a target confirmation form under a compact year-plus-serial PDF
filename.

- Root cause from the v143 45-school bounded non-Sanko rerun: school `864`
  exposed `http://www.atg-web.ac.jp/img/educational/2025007.pdf` with anchor
  text `大学等における修学の支援に関する確認申請書`. v143 still classified it as
  `target_fiscal_year_not_detected` because the year hint parser only accepted
  standalone `2025`, not `2025` followed by a serial number in the filename.
- `_fiscal_year_from_strong_candidate_hint` now accepts a `20xx` prefix followed
  by a short serial suffix before `.pdf`, but only inside the existing strong
  target-form context. This keeps role lists, syllabi, admission guides, and
  non-target files on the existing negative path.
- Regression coverage:
  `test_pre_download_detects_stale_year_prefix_serial_filename_for_target_form`.
  The new test failed before the patch and passes after the patch.
- Local verification:
  focused pre-download tests → `3 passed`;
  `uv run ruff check src/eidp/scraper/pdf_discovery.py tests/unit/test_pdf_discovery.py`
  → passed;
  `uv run mypy src/eidp/scraper/pdf_discovery.py` → passed;
  `uv run pytest tests/unit/test_pdf_discovery.py -q` →
  `48 passed, 5 warnings`;
  `uv run pytest tests/unit -q` → `1030 passed, 5 warnings`.
- Core ZIP: `dist/eidp-windows-v144.zip`
- Latest alias: `dist/eidp-windows.zip`
- Core ZIP SHA256:
  `4198cd6aca579196a3a5fb3fb1f55ec0a2df97a3a72b544f0d7195e4d45d9c68`
- Core verifier with unchanged `dist/eidp-playwright-addon-windows-v106.zip`:
  `OK core`, `OK playwright-addon`,
  `git_commit=6ad13d36d27695af907ad06ed6951bb5fa0e6261`,
  `git_dirty=false`, `entry_count=3016`, `wheel_count=78`,
  47 prefecture seed rows/parser registrations/downloadable artifact URLs,
  `discovery_gold_set_entries=12`, and add-on SHA256
  `f6fe0cd095c337a81a870decb7a18e9d1f40044dd1567b017d92eda3aae1e8e8`.
- Windows remote extraction/setup smoke on host alias `win`: copied
  `eidp-windows-v144.zip`, verified the same SHA256, expanded into
  `C:\EIDP-v144-6ad13d3`, and ran `scripts\first_setup.bat`. The setup
  completed offline wheelhouse install, SQLite bootstrap, master Excel import,
  and FY2026 task rebuild. The bundled validator reported `OK install`,
  `build_commit=6ad13d36d27695af907ad06ed6951bb5fa0e6261`,
  `build_dirty=false`, `school_count=2418`,
  `school_fiscal_year_status_count=2418`, required SQLite tables present, and
  `wheel_count=78`.
- Windows packaged regression for school `864`: inserted the official-index
  `SchoolSite`, ran packaged `discover-pdfs` with strict FY2026, and confirmed
  `2025007.pdf` is now rejected as
  `reason="fiscal_year_mismatch:2025"`, `pdf_type="target"`, with
  `extra={"pre_download": "true"}`. The one-school summary reported
  `crawled=1`, `found=1`, `downloaded=0`, `failed=0`, and
  `publication_lag_or_old_target_pdf=1`.

v144 improves one more latest-public old-year target-form path. It still keeps
the PDF out of `document` and out of Excel because it is not the configured
strict target FY2026 form.

## 2026-05-11 v143 Update

v143 supersedes the v141/v142 `nag.ac.jp/evaluation/*.html` stale-entry result.
It does not turn old-year forms into strict FY2026 success; it repairs the
registered-entry-to-school-homepage path and classifies stale target forms as
publication-lag evidence instead of no-candidate or non-target noise.

- `pdf_discovery.py` now has a bounded school-name external homepage fallback.
  When a stale umbrella/corporation official-index URL falls back to the root
  page, the crawler may follow only external homepage links whose anchor/text
  matches the current `School.school_name`. Obvious social/search hosts are
  ignored, and the existing candidate scoring / strict target-FY gates remain
  unchanged.
- `run_pdf_discovery` passes the school name into the per-site crawler so the
  fallback can make that bounded decision without widening unrelated crawls.
- The pre-download filter now classifies stale target confirmation forms on
  `/evaluation/` paths as `fiscal_year_mismatch` when strong target-form context
  is present. This fixes the v142 finding where `info-2025.pdf` was incorrectly
  treated as `pre_filtered_non_target_hint` merely because the URL path
  contained `evaluation`.
- Regression coverage:
  `test_discover_pdfs_follows_school_named_homepage_from_umbrella_root`,
  `test_run_pdf_discovery_passes_school_name_to_site_crawler`, and
  `test_pre_download_prioritizes_stale_target_form_year_over_evaluation_path`.
- Local verification for the code changes:
  `uv run ruff check src/eidp/scraper/pdf_discovery.py tests/unit/test_pdf_discovery.py`
  → passed;
  `uv run mypy src/eidp/scraper/pdf_discovery.py` → passed;
  `uv run pytest tests/unit/test_pdf_discovery.py -q` →
  `47 passed, 5 warnings`;
  `uv run pytest tests/unit -q` → `1029 passed, 5 warnings`.
- Core ZIP: `dist/eidp-windows-v143.zip`
- Latest alias: `dist/eidp-windows.zip`
- Core ZIP SHA256:
  `58183771364d50f319c7a72587e79aa79afa385d9181ce54490f378013472241`
- Core verifier with unchanged `dist/eidp-playwright-addon-windows-v106.zip`:
  `OK core`, `OK playwright-addon`,
  `git_commit=06926abc476616824919fe1e5ceba2374a621b98`,
  `git_dirty=false`, `entry_count=3016`, `wheel_count=78`,
  47 prefecture seed rows/parser registrations/downloadable artifact URLs,
  `discovery_gold_set_entries=12`, and add-on SHA256
  `f6fe0cd095c337a81a870decb7a18e9d1f40044dd1567b017d92eda3aae1e8e8`.
- Windows remote extraction/setup smoke on host alias `win`: copied
  `eidp-windows-v143.zip`, verified the same SHA256, expanded into
  `C:\EIDP-v143-06926ab`, and ran `scripts\first_setup.bat`. The setup
  completed offline wheelhouse install, SQLite bootstrap, master Excel import,
  and FY2026 task rebuild. The bundled validator reported `OK install`,
  `build_commit=06926abc476616824919fe1e5ceba2374a621b98`,
  `build_dirty=false`, `school_count=2418`,
  `school_fiscal_year_status_count=2418`, required SQLite tables present, and
  `wheel_count=78`.
- Windows targeted rerun for the four `nag.ac.jp/evaluation/*.html` stale-entry
  schools (`school_id=164,165,166,167`) confirmed the operational effect:
  packaged `discover-pdfs` logged `pdf_discovery_root_fallback` for all four,
  ended with `crawled=4`, `found=4`, `downloaded=0`, `failed=0`,
  `skipped=24`, `prefiltered=13`,
  `rejection_reason_fiscal_year_mismatch=15`,
  `rejection_reason_classified_non_target=7`,
  `rejection_reason_pre_filtered_non_target_hint=10`, and
  `rejection_reason_target_fiscal_year_not_detected=2`. The copied evidence
  summary reported `evidence rows=34`, `schools with evidence=4`, and
  `publication_lag_or_old_target_pdf=4`.
- Windows v143 bounded non-Sanko rerun on the same 45-school sample used in the
  v139 RCA ended with `crawled=45`, `found=41`, `downloaded=0`, `failed=7`,
  `skipped=159`, `cached_rejections=82`, and `prefiltered=67`. The evidence
  summary reported `publication_lag_or_old_target_pdf=34`,
  `target_form_without_year_evidence=4`, `tls_certificate_verify_failed=4`, and
  `non_target_candidates_only=3`. Compared with the v141-resummarized v139
  evidence, all 13 remaining `site_fetch_error_only` schools moved into
  `publication_lag_or_old_target_pdf`; four certificate-chain failures remained
  TLS-gated, and strict FY2026 downloads remained `0`.

v143 improves evidence quality and operator actionability for stale official
index rows. It still records `downloaded=0` for strict FY2026 because the found
target forms are latest-public old-year PDFs, not current target-year PDFs.

## 2026-05-11 v141 Update

v141 packages the TLS certificate failure classification from the v139
bounded non-Sanko acquisition RCA.

- Root cause from the remaining v139 `site_fetch_error_only` rows: four public
  school sites failed with `CERTIFICATE_VERIFY_FAILED`. A Windows packaged probe
  showed that default verification, certifi, and Windows ROOT certificate
  enumeration still failed; only `verify=False` reached HTTP 200. The product
  decision is to keep TLS verification strict and surface the failure, not to
  silently bypass certificate checks.
- `discovery_evidence_summary.py` now buckets all-`discovery_error` schools
  with certificate verification errors as `tls_certificate_verify_failed`.
- `school_fiscal_year_status` rebuild maps that bucket to
  `pdf_status="site_error"`, `evidence_level="tls_certificate_verify_failed"`,
  `blocking_reason="tls_certificate_verify_failed"`, and
  `excel_ready=false`.
- The task board labels the state as `証明書エラー` / `入口取得エラー` and
  gives the operator a certificate-confirmation next action.
- Verification for the code change:
  `uv run pytest tests/unit/test_discovery_evidence_summary.py tests/unit/test_school_fiscal_year_status.py tests/unit/test_review_school_year_tasks.py -q`
  → `69 passed`;
  Ruff passed on the touched files;
  mypy passed on the touched runtime modules;
  `uv run pytest tests/unit -q` → `1026 passed`.
- Re-summarizing the copied v139 bounded non-Sanko evidence now produces
  `tls_certificate_verify_failed=4` and reduces generic
  `site_fetch_error_only` from `17` to `13`. A copied-DB rebuild proved school
  IDs `313,314,315,316` become `site_error` with
  `tls_certificate_verify_failed`.
- Core ZIP: `dist/eidp-windows-v141.zip`
- Latest alias: `dist/eidp-windows.zip`
- Core ZIP SHA256:
  `da9fef4e7c819c19753bde547466c06c9964714d7cf5c212190fefa3731bddee`
- Core verifier with unchanged `dist/eidp-playwright-addon-windows-v106.zip`:
  `OK core`, `OK playwright-addon`,
  `git_commit=9abee545baf367db1866c24834526eb7b4a85aeb`,
  `git_dirty=false`, `entry_count=3016`, `wheel_count=78`,
  47 prefecture seed rows/parser registrations/downloadable artifact URLs,
  `discovery_gold_set_entries=12`, and add-on SHA256
  `f6fe0cd095c337a81a870decb7a18e9d1f40044dd1567b017d92eda3aae1e8e8`.
- Windows remote extraction/setup smoke on host alias `win`: copied
  `eidp-windows-v141.zip`, verified the same SHA256, expanded into
  `C:\EIDP-v141-9abee54`, and ran `scripts\first_setup.bat`. The setup
  completed offline wheelhouse install, SQLite bootstrap, master Excel import,
  and FY2026 task rebuild. The bundled validator reported `OK install`,
  `build_commit=9abee545baf367db1866c24834526eb7b4a85aeb`,
  `build_dirty=false`, `school_count=2418`,
  `school_fiscal_year_status_count=2418`, required SQLite tables present, and
  `wheel_count=78`.
- Windows packaged synthetic TLS rebuild smoke from
  `C:\EIDP-v141-9abee54`: inserted a `prefecture_aggregator` `SchoolSite`,
  wrote one `discovery_error` evidence row with
  `[SSL: CERTIFICATE_VERIFY_FAILED]`, ran
  `eidp rebuild-school-year-tasks --fiscal-year 2026
  --discovery-evidence-log=output\tls_discovery_rejections.jsonl`, and queried
  SQLite directly. The row became
  `(1, 'pref_url', 'site_error', 'tls_certificate_verify_failed',
  'tls_certificate_verify_failed', 0)`.
- Windows targeted rerun for the four remaining `nag.ac.jp/evaluation/*.html`
  stale-entry schools (`school_id=164,165,166,167`) confirmed that the packaged
  v141 root fallback also clears those stale 404s: `discover-pdfs` logged
  `pdf_discovery_root_fallback` for all four, ended with `crawled=4`,
  `failed=0`, `downloaded=0`, and
  `rejection_reason_no_candidates_found=4`. These rows are now a bounded
  `no_pdf_candidates` / deeper navigation problem, not a fetch-error class.

v141 does not weaken TLS verification and does not change the strict FY2026
yield gate. It turns one more silent/ambiguous acquisition failure class into
an auditable operator action.

## 2026-05-11 v140 Update

v140 packages the post-RCA stale official-index URL fallback.

- Root cause from the v139 non-Sanko RCA: 9 of the 17
  `site_fetch_error_only` rows were stale
  `https://www.all-japan.ac.jp/disclosure/` official-index URLs returning 404,
  even though the same-origin root page still linked the live disclosure page.
- `pdf_discovery.py` now retries the same-origin root page when the registered
  official-index URL returns 404/410 below root. The fallback is intentionally
  narrow: it does not ignore arbitrary HTTP failures, does not cross origin, and
  does not relax TLS verification.
- Regression coverage: `test_discover_pdfs_falls_back_to_origin_root_when_registered_path_is_404`.
- Local verification:
  `uv run pytest tests/unit/test_pdf_discovery.py -q` → `44 passed`;
  `uv run ruff check src/eidp/scraper/pdf_discovery.py tests/unit/test_pdf_discovery.py` → passed;
  `uv run mypy src/eidp/scraper/pdf_discovery.py` → passed;
  `uv run pytest tests/unit -q` → `1024 passed`.
- Live local probe against `https://www.all-japan.ac.jp/disclosure/` confirmed
  `pdf_discovery_root_fallback`, `result.error=None`, `candidates=626`, and a
  repair of the stale official-index URL into a crawlable disclosure surface.
- Core ZIP: `dist/eidp-windows-v140.zip`
- Latest alias: `dist/eidp-windows.zip`
- Core ZIP SHA256: `b8256b3e4e62741f98b36c339152a3b477d905426398d4603bc5e43bc5e8ddb6`
- Core verifier with unchanged `dist/eidp-playwright-addon-windows-v106.zip`:
  `OK core`, `OK playwright-addon`,
  `git_commit=06c94d63d6b01fc54499793451d4b4a3d55fd5ed`,
  `git_dirty=false`, `entry_count=3016`, `wheel_count=78`,
  47 prefecture seed rows/parser registrations/downloadable artifact URLs, and
  add-on SHA256 `f6fe0cd095c337a81a870decb7a18e9d1f40044dd1567b017d92eda3aae1e8e8`.
- Windows remote extraction/setup smoke on host alias `win`: copied
  `eidp-windows-v140.zip`, verified the same SHA256, expanded into
  `C:\EIDP-v140-06c94d6`, and ran `scripts\first_setup.bat`. The setup
  completed offline wheelhouse install, SQLite bootstrap, master Excel import,
  and FY2026 task rebuild. The bundled validator reported `OK install`,
  `build_commit=06c94d63d6b01fc54499793451d4b4a3d55fd5ed`,
  `build_dirty=false`, `school_count=2418`,
  `school_fiscal_year_status_count=2418`, required SQLite tables present, and
  `wheel_count=78`.
- Windows packaged live fallback smoke from `C:\EIDP-v140-06c94d6` against
  `https://www.all-japan.ac.jp/disclosure/` confirmed
  `pdf_discovery_root_fallback`, `error=None`, `candidates=626`, and a best
  candidate from the repaired disclosure surface.
- Windows targeted acquisition rerun for the 9 affected all-japan schools
  (`school_id=303,304,305,307,308,309,310,311,312`) confirmed the operational
  effect: all 9 stale official-index URLs logged `pdf_discovery_root_fallback`,
  `discover-pdfs` ended with `crawled=9`, `found=9`, `failed=0`,
  `downloaded=0`, `cached_rejections=80`, and
  `rejection_reason_fiscal_year_mismatch=90`. The copied evidence summary
  bucketed all 9 schools as `publication_lag_or_old_target_pdf`, replacing the
  previous `discovery_error` classification with an operator-actionable
  latest-public/old-year result.

v140 improves stale official-index URL recovery but does not change the strict
FY2026 yield gate by itself. The remaining TLS-chain failures and true
publication-lag / old-year target PDFs remain separate work or policy decisions.

## 2026-05-11 v139 Update

The v138 discovery-evidence RCA showed that publication-lag / old-year target
forms are the dominant bounded-smoke blocker. v139 consumes the PDF
discovery evidence JSONL during task rebuild and surfaces those schools as an
operator-visible review/wait state instead of leaving them indistinguishable
from generic `no_target_pdf`.

- `school_fiscal_year_status` rebuild maps evidence bucket
  `publication_lag_or_old_target_pdf` to `pdf_status="publication_lag"`,
  `evidence_level="publication_lag"`, and
  `blocking_reason="publication_lag_latest_public"`.
- This is not a target-FY success path: `excel_ready` remains false and the
  status is counted under `stale_or_old`, not `confirmed_target`.
- Production rebuild entrypoints now pass the evidence log into status rebuild:
  bootstrap Step 5, weekly discovery, CLI `rebuild-school-year-tasks`, the
  settings target-FY rebuild, and the Streamlit task-page rebuild button.
- The task board now has a dedicated `旧年度候補あり` lane and next action
  `公示待ち/再取得`, with copy that explicitly says these candidates are not
  treated as target-FY success.
- Verification for this local update: focused TDD tests for status rebuild,
  bootstrap evidence wiring, and task-board labels; `uv run pytest tests/unit`
  passed `1023` tests, and Ruff passed on the touched code/test files.
- Core ZIP: `dist/eidp-windows-v139.zip`
- Latest alias: `dist/eidp-windows.zip`
- Core ZIP SHA256: `35a67aca553d279ce834da26cde970985623ba95d587d1be0fa27655be7c6534`
- Core verifier with unchanged `dist/eidp-playwright-addon-windows-v106.zip`:
  `OK core`, `OK playwright-addon`, `git_commit=2f5b8e46163b8dd50cc6a081ffaff5b408d604f4`,
  `git_dirty=false`, `entry_count=3016`, `wheel_count=78`,
  `discovery_gold_set_entries=12`, 47 prefecture seed rows/parser
  registrations/downloadable artifact URLs, and add-on SHA256
  `f6fe0cd095c337a81a870decb7a18e9d1f40044dd1567b017d92eda3aae1e8e8`.
- Windows remote extraction/setup smoke on host alias `win`: copied
  `eidp-windows-v139.zip`, verified the same SHA256, expanded into
  `C:\EIDP-v139-2f5b8e4`, and ran `scripts\first_setup.bat`. The setup
  completed offline wheelhouse install, SQLite bootstrap, master Excel import,
  and FY2026 task rebuild. The after-setup validator reported `errors=[]`,
  `warnings=[]`, `school_count=2418`, `school_fiscal_year_status_count=2418`,
  required SQLite tables present, `sqlite_table_count=15`, and `wheel_count=78`.
- Windows packaged CLI publication-lag smoke: generated a one-row
  `output\discovery_rejections.jsonl` with `reason=fiscal_year_mismatch:2025`
  and `pdf_type=target`, ran `eidp rebuild-school-year-tasks --fiscal-year
  2026 --discovery-evidence-log output\discovery_rejections.jsonl`, and checked
  SQLite directly. The row became `(school_id=1, pdf_status=publication_lag,
  evidence_level=publication_lag, excel_ready=0,
  blocking_reason=publication_lag_latest_public)`.
- Windows Streamlit server smoke: launched the packaged review app from
  `C:\EIDP-v139-2f5b8e4`; the server reported `Local URL:
  http://localhost:8501`, and an independent Windows `Invoke-WebRequest` probe
  against `http://localhost:8501/` returned HTTP `200`.
- Windows UI click-through smoke through SSH port forwarding
  (`127.0.0.1:18501 -> win:8501`) rendered the packaged Streamlit app in a
  browser and verified the main operator pages without pressing execution
  buttons: `① 学校別タスク`, `② PDF確認・手入力`, `③ 年度判定・修正`,
  `④ Excel プレビュー`, `⑤ 設定（年度・OCR・API）`, `URL候補レビュー`,
  and `都道府県公式インデックス`. The task board showed
  `commit=2f5b8e4`, the publication-lag alert for 1 school, the
  `旧年度候補あり` lane, and after clicking `旧年度候補を表示` the filtered
  result `公示待ち/再取得 / 東京都 / 日本工学院専門学校 / id=1`.
  Excel preview stayed disabled because target-FY transfer rows are still zero.

v139 reduces operator ambiguity around latest-public old-year forms, but it
does not change the strict FY2026 yield denominator or make stale forms
Excel-ready.

### v139 bounded non-Sanko acquisition RCA

After the v139 package/UI smoke, a second Windows acquisition RCA was run on the
same fresh extraction (`C:\EIDP-v139-2f5b8e4`) to avoid repeating the previous
Tokyo/Kanagawa/Saitama Sanko-heavy sample.

Scope setup:

- Ran official-index bootstrap for `osaka,fukuoka,hokkaido,aichi,hyogo` with
  URL search and Scrapling school-URL crawl disabled, and with PDF discovery
  skipped. Official-index direct URL additions were Osaka `120`, Aichi `104`,
  and Hokkaido `97`; Fukuoka/Hyogo produced index extraction/review evidence but
  no direct `SchoolSite` URL additions in this run.
- After bootstrap Step 2b, the runtime SQLite DB contained `861` `school_site`
  rows: `prefecture_aggregator=321`, `corporation_pattern=490`, and
  `seed_csv=50`.
- Chose a bounded 45-school sample from `prefecture_aggregator` rows: 15 each
  from Hokkaido, Aichi, and Osaka, excluding known repeated high-volume groups
  `三幸`, `大原`, `滋慶`, and `コミュニケーションアート`.

Strict FY2026 discovery command:

- Packaged CLI command: `eidp discover-pdfs --discovery-method
  prefecture_aggregator --batch-size 45 --rate-limit 0.5 --request-timeout 15
  --evidence-log output\v139_bounded_non_sanko_evidence.jsonl`, with the 45
  selected `--school-id` values.
- Discovery result: `crawled=45`, `found=28`, `downloaded=0`, `failed=19`,
  `skipped=138`, `cached_rejections=2`, and `prefiltered=67`.
- Rejection counters: `fiscal_year_mismatch=89`,
  `classified_non_target=45`, `pre_filtered_non_target_hint=41`,
  `target_fiscal_year_not_detected=15`, and `discovery_error=17`.
- No `document` rows were created, so ingest was intentionally skipped.

Evidence summary:

- `uv run eidp summarize-discovery-evidence` on the copied Windows evidence
  JSONL reported `207` evidence rows across all `45` schools.
- School-level buckets: `publication_lag_or_old_target_pdf=22`,
  `site_fetch_error_only=17`, `target_form_without_year_evidence=4`, and
  `non_target_candidates_only=2`.
- After running packaged `eidp rebuild-school-year-tasks --fiscal-year 2026
  --discovery-evidence-log output\v139_bounded_non_sanko_evidence.jsonl`, the
  selected 45 schools were split into `publication_lag=22` and
  `no_target_pdf=23`. Overall FY2026 status rows in that Windows DB were
  `no_url=1559`, `no_target_pdf=837`, and `publication_lag=22`.

Interpretation:

- This run confirms the Layer 0 official-index path is not the only blocker:
  the selected schools all had official-index `SchoolSite` URLs, but strict
  FY2026 target-PDF acquisition still produced `0/45` downloads.
- The dominant actionable bucket is not random non-target noise. It is
  latest-public / old-year target forms (`22/45`) plus fetch/navigation failures
  (`17/45`), with a smaller image/layout/year-evidence bucket (`4/45`).
- v139 correctly prevents these stale candidates from becoming Excel-ready
  target-FY success and surfaces them as operator-reviewable
  `publication_lag`. The automation goal remains below the 60-70% strict
  target-FY ship gate until FY2026 forms are public at sufficient coverage or
  the product formally accepts a latest-public publication-lag workflow.

Follow-up fix from this RCA:

- The 17 `site_fetch_error_only` rows were inspected. They were not one bucket:
  nine were stale `https://www.all-japan.ac.jp/disclosure/` official-index
  URLs returning 404 even though the same-origin root page still links the live
  disclosure page; four were stale `nag.ac.jp` / `akademeia21.com` 404s; four
  were TLS certificate-chain failures on public school sites.
- `pdf_discovery.py` now retries a same-origin root page when the registered
  official-index URL returns 404/410 below root. This is deliberately narrow:
  it does not ignore arbitrary HTTP errors and does not change TLS verification.
- Fixture regression: a stale `/old/disclosure/` path returning 404 now falls
  back to `/`, follows the root `情報公開` link, and finds the target PDF.
- Live verification against `https://www.all-japan.ac.jp/disclosure/` confirmed
  the fallback logs `pdf_discovery_root_fallback`, clears `result.error`, and
  discovers `626` PDF candidates from the current disclosure surface.

## 2026-05-11 v138 Update

v138 refreshes the core Windows package after two Saitama-RCA-driven PDF
discovery fixes:

- Japanese/romaji confirmation-form attachment hints (`別紙`, `bessi`,
  `besshi`) now rank below the main confirmation form instead of tying it.
  This does not hard-reject attachments and does not loosen strict FY success.
- PDF candidate dedupe now treats percent-encoded and unencoded path variants
  as the same candidate key while preserving the original download URL.

Package evidence:

- Core ZIP: `dist/eidp-windows-v138.zip`
- Latest alias: `dist/eidp-windows.zip`
- Core ZIP SHA256: `304fd6147d39e7631793861fd79c98e53df6dde1a43e6eee17af9b464c10e0c7`
- Core verifier: `OK core`, `git_commit=5a4aeb825e516410875d31ddf1e4c4fddab448e0`,
  `git_dirty=false`, `entry_count=3016`, `wheel_count=78`,
  `prefecture_seed_rows=47`, `prefecture_seed_parser_supported=47`,
  `prefecture_seed_downloadable=47`, and `discovery_gold_set_entries=12`.
- Combined verifier with unchanged `dist/eidp-playwright-addon-windows-v106.zip`:
  `OK core` and `OK playwright-addon`; add-on SHA256 remains
  `f6fe0cd095c337a81a870decb7a18e9d1f40044dd1567b017d92eda3aae1e8e8`.
- Local regression gates for the code changes: `uv run pytest tests/unit`
  passed `1021` tests, and Ruff passed on the touched PDF discovery files.
- Windows remote extraction/setup smoke on host alias `win`: copied
  `eidp-windows-v138.zip`, verified the same SHA256, expanded into the fresh
  directory `C:\EIDP-v138-5a4aeb8`, and ran
  `scripts\validate_windows_install.py` from the bundled runtime. Pre-setup
  validation reported `errors=[]`, `warnings=[]`, `build_commit=5a4aeb825e516410875d31ddf1e4c4fddab448e0`,
  `master_xlsx_present=True`, and `wheel_count=78`.
- Windows remote first setup smoke in `C:\EIDP-v138-5a4aeb8`:
  `scripts\first_setup.bat` completed with offline wheelhouse install, SQLite
  bootstrap, master Excel import, and FY2026 task rebuild. The after-setup
  validator reported `errors=[]`, `warnings=[]`, `school_count=2418`,
  `school_fiscal_year_status_count=2418`, `sqlite_table_count=15`, and the
  required tables `school`, `school_site`, `document`, `department`,
  `department_yearly`, `manual_action_log`, and `school_fiscal_year_status`.
- Windows remote add-on smoke: extracted unchanged
  `eidp-playwright-addon-windows-v106.zip` into the v138 directory, re-ran
  `first_setup.bat`, and confirmed offline installation of
  `scrapling==0.4.7` and `playwright==1.58.0`. The add-on validator
  `--require-playwright-addon` passed with `errors=[]` and `warnings=[]`.
- Windows remote browser smoke: with `EIDP_APP_ROOT=C:\EIDP-v138-5a4aeb8`,
  `scrapling_available=True`, `PLAYWRIGHT_BROWSERS_PATH` pointed to
  `C:\EIDP-v138-5a4aeb8\playwright-addon\ms-playwright`, and bundled Chromium
  launched headless against a `data:` page with `playwright_title=eidp-ok`.
- Windows remote official-index ingestion smoke for Tokyo/Kanagawa/Saitama:
  `bootstrap_pdf_pipeline.py --pref saitama,tokyo,kanagawa --url-search off
  --school-url-crawl off --batch-size 1 --skip-discover --no-lock` completed
  the official-index URL stages. Results: Tokyo `extracted=243`,
  `matched=232`, `added=232`; Kanagawa `extracted=76`, `matched=71`,
  `added=70`; Saitama `extracted=58`, `matched=51`, `added=51`.
  Step 2b added 50 seed URLs and 498 corporation-pattern URLs.
- Windows remote strict FY2026 60-site PDF discovery smoke with the `.bat`
  equivalent UTF-8 environment (`PYTHONIOENCODING=utf-8`, `PYTHONUTF8=1`):
  `crawled=60`, `found=55`, `downloaded=3`, `failed=6`, `skipped=389`,
  `cached_rejections=46`, and `prefiltered=216`. Rejection leaders were
  `fiscal_year_mismatch=149`, `classified_non_target=122`,
  `pre_filtered_non_target_hint=135`, and
  `target_fiscal_year_not_detected=12`.
- Windows remote ingest/status smoke on those 3 downloaded PDFs:
  `ingest-pdfs` processed 3 documents; 1 target PDF was parsed and made
  Excel-ready, while 2 image-only PDFs were parked as `ocr_pending` because the
  OCR add-on is not installed in the core+Playwright package. The parsed target
  row was 東京呉竹医療専門学校 (`pdf_type=target`, `ingest_status=ingested`,
  `yearly_upserted=4`, `support_recipient=1`). After rebuilding FY2026 task
  status, totals were `school_sites_total=901`, `documents_total=3`,
  `excel_ready=1`, `pdf_status_counts=[('confirmed_target', 1), ('image_pending', 2), ('none', 2415)]`,
  and top blocking reasons were `no_url=1523`, `no_target_pdf=892`,
  `ocr_pending=2`.
- Windows remote discovery-evidence RCA on the same 60-site v138 smoke:
  `evidence_rows=429`, `schools_with_evidence=60`, `site_scope_schools=60`.
  School buckets were `accepted_target_pdf=3`,
  `publication_lag_or_old_target_pdf=44`,
  `target_form_without_year_evidence=5`, `site_fetch_error_only=3`,
  `non_target_candidates_only=3`, and `no_pdf_candidates=2`. This means 44/60
  schools had a target-form-looking PDF for another/publication-lag year, while
  strict FY2026 correctly refused to count it as success.

Interpretation: v138 is the current packaged handoff candidate for the
candidate-ranking/dedupe fixes. It now has Windows extraction/setup/add-on
smoke coverage and a matching bounded PDF crawl/ingest yield smoke. The bounded
strict FY2026 yield remains far below the 60-70% automation gate, and the RCA
shows the dominant blocker is publication lag / old-year target forms rather
than missing official-index URL ingestion.

## 2026-05-11 v137 Update

v137 refreshes the Windows handoff package after adding discovery gold-set
packaging and verifier contract checks. The ZIP now carries the deterministic
`data/discovery-gold-set/` regression surface and the verifier parses the
packaged JSON entries instead of checking filenames only.

- Core ZIP: `dist/eidp-windows-v137.zip`
- Latest alias: `dist/eidp-windows.zip`
- Core ZIP SHA256: `17f76efe01c56ce5042fcc81928e533059feafa0b15508723b42dbbdeda5aefe`
- Core verifier: `OK core`, `git_commit=c9bb155ff6e98979275296980b8f942e6a0b4e87`,
  `git_dirty=false`, `entry_count=3016`, `wheel_count=78`,
  `prefecture_seed_rows=47`, `prefecture_seed_parser_supported=47`,
  `prefecture_seed_downloadable=47`,
  `discovery_gold_set_entries=12`, and discovery gold-set outcomes
  `accepted_target_pdf=4`, `needs_operator_review=5`,
  `no_target_candidate_found=1`, `publication_lag_latest_public=2`.
- Playwright/Scrapling add-on: `dist/eidp-playwright-addon-windows-v106.zip`
- Add-on SHA256: `f6fe0cd095c337a81a870decb7a18e9d1f40044dd1567b017d92eda3aae1e8e8`
- Combined verifier: `OK core` and `OK playwright-addon`; the add-on verifier
  reported `entry_count=637` and `manifest_files=636`.
- Windows remote extraction smoke on host alias `win`: copied
  `eidp-windows-v137.zip`, verified the same SHA256, expanded into the fresh
  directory `C:\EIDP-v137-c9bb155`, and ran
  `scripts\validate_windows_install.py` from the bundled runtime. Result:
  `OK install`, `build_commit=c9bb155ff6e98979275296980b8f942e6a0b4e87`,
  `build_dirty=false`, `master_xlsx_present=True`, and `wheel_count=78`.
- Windows remote first setup smoke in `C:\EIDP-v137-c9bb155`: `scripts\first_setup.bat`
  completed with offline wheelhouse install, SQLite bootstrap, master Excel
  import, and task rebuild. Validator reported `errors=[]`, `warnings=[]`,
  `school_count=2418`, `school_fiscal_year_status_count=2418`,
  `sqlite_table_count=15`, and required tables including `school_site`,
  `document`, `department_yearly`, and `manual_action_log`.
- Windows remote add-on smoke: extracted the Playwright/Scrapling add-on into
  the same fresh directory, re-ran `first_setup.bat`, and confirmed offline
  installation of `scrapling==0.4.7` and `playwright==1.58.0`.
- Windows remote browser smoke: with `EIDP_APP_ROOT=C:\EIDP-v137-c9bb155`,
  `scrapling_available=True`, `PLAYWRIGHT_BROWSERS_PATH` pointed to
  `playwright-addon\ms-playwright`, and bundled Chromium launched headless
  against a `data:` page with `playwright_title=eidp-ok`.
- Windows remote official-index ingestion smoke for Tokyo/Kanagawa/Saitama:
  `bootstrap_pdf_pipeline.py --pref saitama,tokyo,kanagawa --url-search off
  --school-url-crawl off --batch-size 1 --skip-discover` completed the
  official-index URL stages. Results: Tokyo `extracted=243`, `matched=232`,
  `added=232`; Kanagawa `extracted=76`, `matched=71`, `added=70`; Saitama
  `extracted=58`, `matched=51`, `added=51`. Step 2b added 50 seed URLs and
  498 corporation-pattern URLs.
- Windows remote strict FY2026 60-site PDF discovery smoke with the `.bat`
  equivalent UTF-8 environment (`PYTHONIOENCODING=utf-8`, `PYTHONUTF8=1`):
  `crawled=60`, `found=55`, `downloaded=3`, `failed=6`, `skipped=389`,
  `cached_rejections=46`, and `prefiltered=217`. Rejection leaders were
  `fiscal_year_mismatch=154`, `classified_non_target=121`,
  `pre_filtered_non_target_hint=132`, and
  `target_fiscal_year_not_detected=13`.
- Windows remote ingest/status smoke on those 3 downloaded PDFs:
  `ingest-pdfs` processed 3 documents; 1 target PDF was parsed and made
  Excel-ready, while 2 image-only PDFs were parked as `ocr_pending` because the
  OCR add-on is not installed in the core+Playwright package. The parsed target
  row was 東京呉竹医療専門学校 (`pdf_type=target`, `ingest_status=ingested`,
  `yearly_count_for_doc=4`, `support_count_for_doc=1`). After rebuilding
  FY2026 task status, coverage totals were `schools_total=2418`,
  `schools_with_url=895`, `schools_with_any_pdf=3`,
  `schools_with_target_pdf_current_fy=1`, and
  `schools_with_current_fy_extracted=1`.
- Windows remote Saitama Layer 0 -> Layer 1 RCA on the 51
  `prefecture_aggregator` Saitama URLs: Saitama official-index URL ingestion
  is present (`SAITAMA_PREF_SITES=51`, `SAITAMA_DOCUMENTS=0` before the run).
  A targeted strict FY2026 `discover-pdfs` run over those 51 school IDs
  completed with `crawled=51`, `found=45`, `downloaded=0`, `failed=7`,
  `skipped=399`, `cached_rejections=31`, and `prefiltered=214`. Evidence
  buckets for the 51 schools were: `publication_lag_or_old_target_pdf=40`,
  `site_fetch_error_only=5`, `non_target_candidates_only=3`,
  `target_form_without_year_evidence=2`, and `no_pdf_candidates=1`. Reason
  leaders were `fiscal_year_mismatch=186`, `classified_non_target=140`,
  `pre_filtered_non_target_hint=89`, and
  `target_fiscal_year_not_detected=10`.
- Windows direct PowerShell caveat: a direct `eidp discover-pdfs` SSH invocation
  without UTF-8 environment variables crashed while logging a Japanese URL with
  `UnicodeEncodeError: 'gbk' codec can't encode character`. The packaged
  `.bat` paths set `PYTHONIOENCODING=utf-8` and `PYTHONUTF8=1`, and the same
  command succeeded once those variables were set manually.

Interpretation: v137 moves the handoff package from "core ZIP verified" to
"core ZIP, discovery gold-set contract, extracted Windows setup, and optional
Scrapling/Playwright browser add-on verified, plus bounded Windows acquisition
RCA". The Saitama RCA confirms the current break is primarily Layer 1
(official URL -> strict target-FY PDF), not Layer 0 official-index URL
ingestion. This improves release-handoff confidence but does not close the
product yield gate. The active goal still requires either a broader Windows
acquisition run that proves true target-FY PDF automation reaches the 60-70%
line, or an explicit publication-lag policy that keeps latest-public stale forms
separate from target-FY success.

## 2026-05-10 v136 Update

v136 is now the current Windows handoff candidate on `sprint8-handoff-finalize`.
The branch has been pushed to `origin/sprint8-handoff-finalize`; `main` remains
unchanged pending real Windows yield acceptance.

- Core ZIP: `dist/eidp-windows-v136.zip`
- Core ZIP SHA256: `6a712770fabdd00bd724deafb6de63f7806198df50d632630eb6608a4d83096a`
- Playwright/Scrapling add-on: `dist/eidp-playwright-addon-windows-v106.zip`
- Add-on SHA256: `f6fe0cd095c337a81a870decb7a18e9d1f40044dd1567b017d92eda3aae1e8e8`
- Windows setup/validator: passed on a clean v136 extraction; validator reported
  `errors=[]`, `warnings=[]`, `school_count=2418`, and
  `school_fiscal_year_status_count=2418`.
- Saitama 5-school URL crawl: `attempted=5`, `auto_registered=5`, `errors=0`,
  with 5 `school` URLs and 10 auxiliary `disclosure` URLs registered.
- Strict FY2026 PDF discovery on the same 5 schools: `downloaded=0`. Evidence
  rows were all rejected as non-target or stale, led by `classified_non_target=102`
  and `fiscal_year_mismatch:2025=10`.
- FY2025 control run on the same 5 schools: 4 target confirmation PDFs were
  accepted into `document`, proving the URL/PDF chain can download and classify
  the public latest target forms when the sites publish FY2025 material.
- Tokyo 10-school URL crawl control: 9 auto-registered, 1 queued for review,
  0 errors. The auto set includes both non-Sanko schools (日本工学院, 東京モード学園,
  HAL東京, 首都医校) and Sanko schools.
- Strict FY2026 PDF discovery on the Tokyo auto set: `downloaded=0` across
  9 schools / 15 registered URLs. Evidence contained 105 rejection rows:
  `classified_non_target=48`, `pre_filtered_non_target_hint=29`, and 20 stale
  target-form mismatches across FY2025-FY2020.
- FY2025 control run on the same Tokyo auto set: 3 target confirmation PDFs were
  accepted into `document`, all Sanko 2025 `yoshiki2025.pdf` forms.
- Cross-prefecture 25-school URL crawl control (神奈川/大阪/愛知/福岡/北海道):
  23 auto-registered, 2 queued for review, 0 errors. Strict FY2026 discovery on
  those 23 schools / 40 registered URLs downloaded 0 target PDFs; FY2025 control
  downloaded 15 target PDFs. This is the strongest current evidence that the
  URL-discovery layer works for common Sanko patterns, while the public latest
  confirmation forms in this sample are still FY2025, not FY2026.

Interpretation: v136 closes the packaging, URL crawl, Scrapling static-html, URL
review, and review-metric issues found in the v134 audit. The remaining release
gate is not packaging readiness; it is target-year policy/yield. The sampled
Sanko pages currently expose 2025 confirmation forms, while strict FY2026 mode
correctly refuses to count those stale forms as success. Non-Sanko Tokyo
schools in the small sample did not expose target confirmation candidates on the
pages discovered by the crawler.

## Objective Restatement

Build EIDP into a durable annual automation system for collecting each
university/vocational school's official 修学支援新制度 confirmation PDF,
verifying the configured target fiscal year, extracting department/student
figures into the DB, and producing the Excel outputs through a Windows
operator UI with minimal manual work.

This is not a one-year R8 project. The same system must roll from FY2026
to FY2027 and later by changing or deriving `target_fiscal_year`.

## Prompt-To-Artifact Checklist

| Requirement | Current evidence | Status |
| --- | --- | --- |
| Rolling target fiscal year, not hard-coded R8 | `src/eidp/config.py` uses `settings.target_fiscal_year`; `src/eidp/fiscal_year.py` derives Japanese fiscal year by April boundary and formats `2026年度（令和8年度）`. Production runners are `run_weekly_target_year_discovery.py` and `target_year_acquisition_plan.py`; R8-named scripts left in `scripts/` are compatibility wrappers. `settings_page.py` now lets the operator change target FY / era alias / OCR / API settings and rebuilds all active `school_fiscal_year_status` rows when target FY changes. | Mostly covered locally: runtime and active entrypoints are rolling; settings changes no longer leave stale task rows. Remaining R8 strings are compatibility wrappers, historical reports/plans, or FY2026 test fixtures. |
| Start from official government/prefecture indexes where possible | `data/prefecture-aggregators/seed.csv`; `src/eidp/scraper/prefecture_aggregator.py`; `scripts/verify_windows_distribution.py` now reads the ZIP seed/parser source and gates 47 prefecture rows, 47 parser registrations, and 47 downloadable official artifact URLs. Latest verifier details include `prefecture_seed_rows=47`, `prefecture_seed_parser_supported=47`, `prefecture_seed_downloadable=47`, `prefecture_seed_with_school_link_signal=37`, `prefecture_seed_supplemental_rows=1`, `prefecture_seed_school_rows_total=2148`. Windows bounded bootstrap smoke on v73 downloaded/parsed all 47 official indexes and produced `official_index_rows_extracted=1948`, `official_index_rows_matched=1770`, `official_school_sites_added=1306`, plus 48 seed URLs and 295 corporation-pattern URLs before the 25-site PDF crawl. Latest Windows v138 three-pref smoke produced Tokyo `added=232`, Kanagawa `added=70`, and Saitama `added=51`. | Release-gated for nationwide official-index bootstrap presence, and official-index URL yield is proven through Windows smokes. Full target-year PDF crawling/ingestion still has to prove 60-70% strict-FY yield. |
| Show source chain / why a PDF was found | `src/eidp/review/_pages/pdf_manual_entry.py` shows selected PDF, source page, confidence, and discovery evidence log; `school_year_tasks.py` now labels crawl entry source quality. | Mostly covered locally; Windows click-through not revalidated after latest UI. |
| Minimize manual URL entry | `school_year_tasks.py` has UI buttons for initial URL/PDF bootstrap and weekly rediscovery; `URL追加` supports reusable page URLs and CSV bulk import. Web search now rejects known third-party directory/government-index URLs before registering `school_site`. Initial-bootstrap completion now preserves official-index yield details (`official_index_rows_extracted`, `official_index_rows_matched`, URL added/upgraded counts, and no-new-URL prefectures) for the operator UI. | Partial: manual entry is reduced and the reason for low yield is more visible, but prefectures without school-publication links and schools whose official page is not discoverable still need fallback discovery/operator review. |
| Avoid counting stale old-year PDFs as success | `pdf_discovery.py` strict target-FY mode; `target_year_status.py`; `excel_preview.py` warns when target FY data is missing; `school_fiscal_year_status.py` tracks stale fallback separately. `pdf_discovery.py` also pre-filters clear non-target public documents, decoded wrapper-URL filenames, and explicit stale fiscal-year link hints such as `令和7年度`, `r07`, and `2025年度` before download, while preserving post-download target-year checks for ambiguous confirmation forms. v94 additionally accepts a PDF whose body classifies as the target confirmation form when the target-year evidence appears in the official URL or anchor text instead of the PDF body; URL-year evidence alone still cannot save non-target PDFs such as student A forms or syllabi. v95 tightens the remaining image-only edge: target-year text alone no longer admits ambiguous image-only admission guides unless the URL/anchor strongly names the target confirmation form. v139 also turns evidence bucket `publication_lag_or_old_target_pdf` into `pdf_status="publication_lag"` / `blocking_reason="publication_lag_latest_public"` for operator review, while keeping `excel_ready=false`. v152 can also accept a body-confirmed yearless target form when the source `SchoolSite` is a current prefecture official-index disclosure URL, recording `year_evidence=prefecture_index_current_year`; the same PDF remains review/reject-bound from untrusted sources. | Covered locally and packaged through v154. Windows v139 CLI smoke proved the publication-lag status row; Windows v154 packaged smoke proves school `757` moves from review to accepted target via `prefecture_index_current_year` and then through ingest/status/export with `extraction_confidence=0.94`. |
| Make PDF確認 usable | `school_year_tasks.py` now works as the main operator task board: progress bar, work-lane buttons for URL gaps / target-year PDF wait / stale PDFs / PDF確認・手入力 / dept changes / Excel preview, preserved filters, and a CSV export for the visible source chain (`取得入口`, registration method, reusable URL, PDF URL/year, and status labels). `PDF確認・手入力` now adds queue-level next-action summaries, year buckets, editable/read-only counts, action-lane filtering (`作業レーン`), focused-doc auto expansion, evidence panel, explicit fiscal-year evidence summaries that distinguish PDF body evidence from URL/link hints, candidate-table `年度根拠` / `PDF本文年度` columns sourced from crawler JSONL, PDF preview/download, lock handling, and manual entry save path. Latest AppTest smoke renders a focused PDF review row through `render()`, OCR availability, discovery JSONL, and the PDF route info panel without exceptions. | Improved locally with UI wiring tests; user still needs final real-workload UI feedback. |
| Review school-universe changes from official remarks | `src/eidp/review/_pages/prefecture_remarks.py` now has dedicated page for official index coverage and `prefecture_remark` review items. The distribution verifier now proves the packaged official-index seed is nationwide rather than partial. | Covered locally with tests and package gate; real operator review of remark workload remains pending. |
| Excel output should use current target FY | `excel_preview.py` blocks preview generation when target-FY data is zero and shows gap metrics; `competition_exporter.py` defaults business export to `settings.target_fiscal_year`, rejects empty target-year business export, and no longer carries the old auto-select-most-populated-year helper. | Core code covered locally; remaining risk is Windows UI click-through and real template/operator validation. |
| Windows operator delivery | `dist/eidp-windows-v232.zip` rebuilt at commit `db84f5ca22a2ed3018e9fcb03153a4c1a231219e`, verifier `OK core`, `git_dirty=false`, SHA256 `33e14cefa01c75ea2f84ce149ac943939c998a34761aaa1ffed3fa8cd289bc64`, wheelhouse 78 wheels, 47 prefecture seed rows/parser registrations/downloadable artifact URLs, `prefecture_seed_school_rows_total=2148`, 16 packaged discovery gold-set entries, packaged OCR/runtime/export/audit gates from v218, the SQLite-backed `--require-ship-gate` validator, diagnostics that preserve strict bootstrap/weekly ship-gate return codes with delayed `%ERRORLEVEL%` capture, the `import-excel` `invalid_year` warning surface, RCA packet rows that preserve `school_id` for Codex/manual follow-up, same-origin WordPress Download Manager PDF candidate extraction for `wpdmdl` links, root fallback when a registered school publication URL resolves to non-HTML content, school-specific disclosure-link prioritization for dense corporation roots, stricter year-evidence filtering that ignores non-filing `完成年度` labels, a `職業実践専門課程等の基本情報` non-target guard, list-item year-context isolation, stale full-form range pre-filtering, support-only image PDF review-bound routing, and per-link `div` context isolation. The latest alias `dist/eidp-windows.zip` has the same SHA256. `dist/eidp-playwright-addon-windows-v106.zip` verifies with SHA256 `f6fe0cd095c337a81a870decb7a18e9d1f40044dd1567b017d92eda3aae1e8e8`, `entry_count=637`, and `manifest_files=636`. Remote Windows v232 smoke on a fresh `C:\Users\cyo20\EIDP-v232-db84f5c` extraction proves setup success: `school_count=2418`, `school_fiscal_year_status_count=2418`, `sqlite_integrity_check=ok`, `department_change` void columns present, and `uq_document_file_hash` present. A v230 targeted replay for school `72` produced `downloaded=0`, `rejection_reason_pre_filtered_non_target_hint=3`, and no `document` row for that school. A v231 targeted replay for school `793` produced `downloaded=0`, `rejection_reason_fiscal_year_mismatch=5`, `rejection_reason_pre_filtered_non_target_hint=5`, and evidence rows for `2-1_2-4.pdf` as `fiscal_year_mismatch:2025` with `pre_download=true`. A full real bounded Saitama official-index acquisition on fresh `C:\Users\cyo20\EIDP-v231-full-e42df2b` produced official-index `extracted=58`, `matched=51`, `added=51`, crawl `found=50`, `downloaded=2`, `failed=5`, `skipped=391`, `prefiltered=198`, ingest `processed=2`, `yearly_upserted=7`, and rebuild `target_pdf_auto_acquired_count=2`, `target_pdf_auto_yield_pct=0.1`, `ship_gate_status=below_gate`; the `--require-ship-gate` validator correctly returned rc `1`. | Latest v232 package verifier, Windows clean extraction/setup smoke, school `72` false-positive replay, school `793` stale-year context replay, and full real Saitama bounded acquisition all passed mechanically. Deployment is healthy, but real strict automation yield remains far below the 60-70% ship gate. Execution-button UI E2E, broader real-workload yield, and remaining false-negative RCA are still incomplete. |
| Universities ~700 and vocational schools ~1700 | UI filters support `専門学校` / `大学`; official index parsers can parse mixed lists. | Not complete: full university rollout is explicitly v1.2; only pilot scope is planned. |

Update: v235 supersedes v234 for packaged artifact verification. The v235 ZIP
at commit `864ae148d0d4bc75abb1800298daa71191b2dfdd` verifies with SHA256
`6b645f2128e0715af0fdeb68cd1bcf595ecf910786dadc1fb49849c3b02319ba`, 3,027
entries, 78 wheels, and 17 discovery gold-set entries covering all five
release-relevant outcomes. Remote Windows setup smoke remains proven on the
v233 extraction `C:\Users\cyo20\EIDP-v233-b4b6324`; v235 has the same setup
surface and Python-only discovery fallback/download-attempt changes.

## Latest Verification Evidence

- 2026-05-12 v235 Windows package refresh →
  commit `864ae148d0d4bc75abb1800298daa71191b2dfdd` packages the pre-filtered
  candidate attempt fix. Pre-filtered current-year news/open-campus and student
  `A様式1` application-form PDFs no longer consume the bounded download-attempt
  budget before a lower-ranked target form can be tried. Verification:
  `uv run pytest tests/unit/test_pdf_discovery.py -q` → `83 passed, 5
  warnings`; `uv run pytest tests/unit -q` → `1184 passed, 5 warnings`;
  `uv run ruff check src/eidp/scraper/pdf_discovery.py
  tests/unit/test_pdf_discovery.py` → all checks passed. The v235 ZIP
  `dist/eidp-windows-v235.zip` verifies with SHA256
  `6b645f2128e0715af0fdeb68cd1bcf595ecf910786dadc1fb49849c3b02319ba`,
  3,027 entries, 78 wheels, 17 discovery gold-set entries, and BUILD_INFO
  `git_commit=864ae148d0d4bc75abb1800298daa71191b2dfdd`,
  `git_dirty=false`; `dist/eidp-windows.zip` has the same SHA256. Extracted
  package validation on `_temp/v235-extract-3wYG7p` returned `ok=true`,
  `master_xlsx_present=true`, and `wheel_count=78`.
- 2026-05-12 v234 Windows package refresh →
  commit `f5d7f542638adcff1a606fbe8fc1092443d71230` packages the rendered-HTML
  fallback fix. Static current-year PDFs that do not have a target application
  hint no longer block JS-rendered discovery. Verification:
  `uv run pytest tests/unit/test_pdf_discovery.py -q` → `79 passed, 5
  warnings`; `uv run pytest tests/unit -q` → `1180 passed, 5 warnings`;
  `uv run ruff check src/eidp/scraper/pdf_discovery.py
  tests/unit/test_pdf_discovery.py` → all checks passed. The v234 ZIP
  `dist/eidp-windows-v234.zip` verifies with SHA256
  `d640d4ac3d41cc27e2019726a72be60adb0bc9ecac08a4bd05a9a5dc883ba762`,
  3,027 entries, 78 wheels, 17 discovery gold-set entries, and BUILD_INFO
  `git_commit=f5d7f542638adcff1a606fbe8fc1092443d71230`,
  `git_dirty=false`; `dist/eidp-windows.zip` has the same SHA256. Extracted
  package validation on `_temp/v234-extract-6E9hl5` returned `ok=true`,
  `master_xlsx_present=true`, and `wheel_count=78`.
- 2026-05-12 v233 Windows package refresh →
  commit `b4b6324a9ad506ba832286dbc306fee1465be9b5` packages the restored
  `no_target_candidate_found` gold-set coverage. A bounded current-code replay
  seeded `東京モード学園` (`https://www.mode.ac.jp/tokyo`) and produced
  `no_candidates_found`; the new
  `tokyo-mode-gakuen-no-candidates-2026` entry keeps the release verifier from
  losing that failure bucket after the 入間看護 case moved to
  `publication_lag_latest_public`. Verification:
  `uv run pytest tests/unit -q` → `1179 passed, 5 warnings`;
  focused gold-set tests → `23 passed`; `uv run ruff check` on the touched
  gold-set/test files → all checks passed. The v233 ZIP
  `dist/eidp-windows-v233.zip` verifies with SHA256
  `b153232ec8809ca1efee065420e1fa3b4bfc252e8dd8fd85a39eb0e95462d092`,
  3,027 entries, 78 wheels, 17 discovery gold-set entries, and BUILD_INFO
  `git_dirty=false`; `dist/eidp-windows.zip` has the same SHA256. Remote
  Windows fresh extraction `C:\Users\cyo20\EIDP-v233-b4b6324` ran
  `EIDP-setup.bat` successfully. The packaged `--after-setup --json`
  validator returned `ok=true`, `school_count=2418`,
  `school_fiscal_year_status_count=2418`, `sqlite_integrity_check=ok`,
  `department_change` void columns present, and `uq_document_file_hash`
  present.
- 2026-05-12 v232 Windows package refresh →
  commit `db84f5ca22a2ed3018e9fcb03153a4c1a231219e` packages two Saitama
  review-bound RCA fixes after the v231 full-run evidence exposed schools `761`
  and `763` as image-only support/form candidates. Stale candidate-year
  fallback now requires either a body-confirmed target PDF or a target
  application-form hint, so generic old-year support text such as `R7修学支援`
  or MEXT boilerplate `2020年度の在学生から対象` no longer becomes
  `fiscal_year_mismatch:*`. PDF anchor context also treats `<div>` link-button
  blocks as bounded containers and stops appending the whole current block when
  the anchor already has year context, preventing sibling text such as
  `実務経験のある教員の授業一覧` from pre-filtering the wrong PDF. Verification:
  `uv run pytest tests/unit/test_pdf_discovery.py -q` → `78 passed, 5
  warnings`; `uv run pytest tests/unit -q` → `1177 passed, 5 warnings`;
  `uv run ruff check src/eidp/scraper/pdf_discovery.py
  tests/unit/test_pdf_discovery.py` → all checks passed. The v232 ZIP
  `dist/eidp-windows-v232.zip` verifies with SHA256
  `33e14cefa01c75ea2f84ce149ac943939c998a34761aaa1ffed3fa8cd289bc64`,
  3,026 entries, 78 wheels, 16 discovery gold-set entries, 47 prefecture seed
  rows, 2,148 prefecture seed school rows, and BUILD_INFO `git_dirty=false`;
  `dist/eidp-windows.zip` has the same SHA256. Remote Windows fresh extraction
  `C:\Users\cyo20\EIDP-v232-db84f5c` ran `EIDP-setup.bat` successfully and the
  packaged non-bootstrap validator returned `ok=true`. Using the v231
  Saitama-seeded SQLite as targeted replay input under the v232 code,
  `discover-pdfs --discovery-method prefecture_aggregator --school-id 761
  --school-id 763` returned `downloaded=0`, `found=2`, `skipped=8`,
  `rejection_reason_target_fiscal_year_not_detected=5`,
  `rejection_reason_pre_filtered_non_target_hint=3`, and
  `rejection_reason_classified_non_target=3`. The copied-back Windows evidence
  records school `761`
  `https://urasen.jp/wp/wp-content/themes/urawa/assets/pdf/about/report/09_shugakushien_r7.pdf`
  with anchor `R7修学支援に関する資料`, `pdf_type=image_only`, reason
  `target_fiscal_year_not_detected`, and school `763`
  `https://odhs.info/app-def/S-101/html/koutou202507.pdf?20250711` with
  `pdf_type=image_only`, reason `target_fiscal_year_not_detected`.
- 2026-05-12 v231 Windows package refresh →
  commit `e42df2b464dd11db9b00403bfaff15287ea1df9c` packages two list-form
  RCA fixes from the Saitama school `793` evidence: `<li>` candidates now use
  the nearest fiscal-year heading instead of inheriting a previous list item,
  and `様式第2号の1～4` full form ranges are target-form hints for stale-year
  pre-filtering. Verification: `uv run pytest tests/unit/test_pdf_discovery.py
  -q` → `75 passed, 5 warnings`; `uv run ruff check
  src/eidp/scraper/pdf_discovery.py tests/unit/test_pdf_discovery.py` → all
  checks passed; `uv run python scripts/verify_windows_distribution.py
  dist/eidp-windows-v231.zip --json` and the same command against
  `dist/eidp-windows.zip` → `ok=true`, SHA256
  `4542fe1d06a5758d8dce55a585abb5b9cceecf48fc79043b8939964841e43453`,
  3,026 entries, 78 wheels, 16 discovery gold-set entries, 47 prefecture seed
  rows, 2,148 prefecture seed school rows, BUILD_INFO `git_dirty=false`.
  Remote Windows fresh extraction `C:\Users\cyo20\EIDP-v231-e42df2b` verified
  the ZIP checksum, and `EIDP-setup.bat` completed with the packaged validator
  reporting `school_count=2418`, `school_fiscal_year_status_count=2418`,
  `sqlite_integrity_check=ok`, `department_change` void columns present, and
  `uq_document_file_hash` present. After Saitama official-index apply, a
  package-level `discover-pdfs --discovery-method prefecture_aggregator
  --school-id 793` replay returned `downloaded=0`; evidence
  `data\output\v231-school793.jsonl` records
  `https://aiko.ac.jp/data/ybc/2025/2-1_2-4.pdf` as
  `fiscal_year_mismatch:2025` with `pre_download=true`.
  A subsequent fresh full Saitama bounded acquisition on
  `C:\Users\cyo20\EIDP-v231-full-e42df2b` completed successfully:
  official-index `extracted=58`, `matched=51`, `added=51`, crawl
  `found=50`, `downloaded=2`, `failed=5`, `skipped=391`,
  `prefiltered=198`, ingest `processed=2`, `yearly_upserted=7`, and
  rebuild `target_pdf_auto_acquired_count=2`,
  `target_pdf_auto_yield_pct=0.1`, `ship_gate_status=below_gate`.
  Evidence summary: 449 rows across 51 schools, school buckets
  `accepted_target_pdf=2`, `publication_lag_or_old_target_pdf=40`,
  `non_target_candidates_only=8`, `site_fetch_error_only=1`; school `72`
  no longer appears as an accepted target. The non-release validator path
  returned `ok=true`, while `--require-ship-gate` correctly returned rc `1`.
- 2026-05-12 v230 Windows package refresh →
  commit `855f714596a42286fda656076c3231bca9634972` packages the
  `職業実践専門課程等の基本情報` non-target guard found from the v229 school
  `72` false positive. Verification: `uv run pytest
  tests/unit/test_pdf_discovery.py -q` → `73 passed, 5 warnings`; `uv run
  ruff check src/eidp/scraper/pdf_discovery.py tests/unit/test_pdf_discovery.py`
  → all checks passed; `uv run python scripts/verify_windows_distribution.py
  dist/eidp-windows-v230.zip --json` and the same command against
  `dist/eidp-windows.zip` → `ok=true`, SHA256
  `eae8ba6b4c26489179ee1c963547f7050151adcb01f488f67c3624bf92ff5314`,
  3,026 entries, 78 wheels, 16 discovery gold-set entries, 47 prefecture seed
  rows, 2,148 prefecture seed school rows, BUILD_INFO `git_dirty=false`.
  Remote Windows fresh extraction `C:\Users\cyo20\EIDP-v230-855f714` verified
  the ZIP checksum, and `EIDP-setup.bat` completed with the packaged validator
  reporting `school_count=2418`, `school_fiscal_year_status_count=2418`,
  `sqlite_integrity_check=ok`, `department_change` void columns present, and
  `uq_document_file_hash` present. After Saitama official-index apply, a
  package-level `discover-pdfs --discovery-method prefecture_aggregator
  --school-id 72` replay returned `downloaded=0`; evidence
  `data\output\v230-school72.jsonl` records
  `shokugyouzissen_sweets_patissier_.pdf` as
  `pre_filtered_non_target_hint`, and the Windows SQLite document count for
  school `72` remained `0`.
- 2026-05-12 v229 Windows package refresh →
  commit `a9baf02d9277685e93f39290075d05de5c81d51e` packages two
  strict-year correctness fixes: English `renewal confirmation application`
  hints require a support-system context, and explicit body year labels such as
  `完成年度は2026年度` no longer count as target-FY filing evidence.
  Verification: `uv run pytest tests/unit/test_pdf_discovery.py -q` →
  `72 passed, 5 warnings`; `uv run ruff check
  src/eidp/scraper/pdf_discovery.py tests/unit/test_pdf_discovery.py` → all
  checks passed; `uv run python scripts/verify_windows_distribution.py
  dist/eidp-windows-v229.zip --json` and the same command against
  `dist/eidp-windows.zip` → `ok=true`, SHA256
  `ad2120d5f12df8e8c32c10f7bbe9a7ab9e19c73856d963c01fafd6b5b0d25a37`,
  3,026 entries, 78 wheels, 16 discovery gold-set entries, 47 prefecture seed
  rows, 2,148 prefecture seed school rows, BUILD_INFO `git_dirty=false`.
  Remote Windows fresh extraction `C:\Users\cyo20\EIDP-v229-a9baf02` verified
  the ZIP checksum, and `EIDP-setup.bat` completed with the packaged validator
  reporting `school_count=2418`, `school_fiscal_year_status_count=2418`,
  `sqlite_integrity_check=ok`, `department_change` void columns present, and
  `uq_document_file_hash` present. A separate
  `scripts\validate_install.bat --after-setup --json` run returned `ok=true`
  for the same extraction. After Saitama official-index apply, a targeted
  package-level `discover-pdfs --discovery-method prefecture_aggregator
  --school-id 95` replay returned `downloaded=0`; evidence
  `data\output\v229-school95.jsonl` records
  `shugakushien_shinsei2025-1-2.pdf` as
  `fiscal_year_mismatch:2025` instead of the v228 false-positive accepted row.
  A full remote Windows bounded Saitama official-index acquisition on the same
  extraction then completed successfully with evidence
  `data\output\bootstrap-v229-saitama-real.jsonl`: official-index
  `extracted=58`, `matched=51`, crawl `found=50`, `downloaded=3`,
  `failed=5`, `skipped=371`, `prefiltered=163`, ingest `processed=3`,
  `yearly_upserted=7`, and status rebuild
  `target_pdf_auto_acquired_count=2`, `target_pdf_auto_yield_pct=0.1`,
  `ship_gate_status=below_gate`. The packaged validator returned `ok=true`
  without `--require-ship-gate`; with `--require-ship-gate` it correctly
  returned rc `1` because the strict yield is below the 60% product gate.
- 2026-05-12 v228 Windows package refresh →
  commit `3148000df5d9c2568365f95cc9dd2c3eaaa1c066` packages bounded
  school-specific disclosure-link prioritization for dense corporation roots,
  stale `/school/disclosure` → live `/disclosure/school` path inversion, and
  a guard preventing `.pdf?query` links from consuming HTML subpage crawl
  budget. Verification: `uv run pytest tests/unit/test_pdf_discovery.py -q`
  → `68 passed, 5 warnings`; `uv run ruff check
  src/eidp/scraper/pdf_discovery.py tests/unit/test_pdf_discovery.py` → all
  checks passed; `uv run pytest tests/unit -q` → `1166 passed, 5 warnings`;
  `uv run python scripts/verify_windows_distribution.py
  dist/eidp-windows-v228.zip --json` and the same command against
  `dist/eidp-windows.zip` → `ok=true`, SHA256
  `b9543ecec169bac4f4981a03abc9145324b28f0dd79e1a9935f4a65696836e12`,
  3,026 entries, 78 wheels, 16 discovery gold-set entries, 47 prefecture seed
  rows, 2,148 prefecture seed school rows, BUILD_INFO `git_dirty=false`.
  Remote Windows fresh extraction `C:\Users\cyo20\EIDP-v228-3148000` verified
  the ZIP checksum, and `EIDP-setup.bat` completed with the packaged validator
  reporting `school_count=2418`, `school_fiscal_year_status_count=2418`,
  `sqlite_integrity_check=ok`, `department_change` void columns present, and
  `uq_document_file_hash` present. A separate
  `scripts\validate_install.bat --after-setup --json` run returned `ok=true`
  for the same extraction. A copied-DB rerun for v226 Saitama school `15`
  now reaches `https://www.sanko.ac.jp/disclosure/omiya-med/` and records
  the school-specific 2025 target form as `fiscal_year_mismatch:2025`, proving
  that this case is publication lag rather than a corporation-page-only
  non-target miss.
  A full remote Windows bounded Saitama official-index acquisition on the same
  extraction then completed successfully with evidence log
  `data\output\bootstrap-v228-saitama-real.jsonl`: official-index
  `extracted=58`, `matched=51`, `added=51`; crawl `crawled=51`, `found=50`,
  `downloaded=3`, `failed=5`, `skipped=364`, `cached_rejections=36`,
  `prefiltered=158`; ingest `processed=3`, `yearly_upserted=9`; status rebuild
  `target_pdf_auto_acquired_count=3`, `target_pdf_auto_yield_pct=0.1`,
  `ship_gate_status=below_gate`. Validator evidence after bootstrap:
  `scripts\validate_install.bat --after-setup --after-bootstrap --json`
  returned `ok=true`, while the same command with `--require-ship-gate`
  returned rc `1`, as expected for below-gate yield. The v228 evidence summary
  buckets are `accepted_target_pdf=3`,
  `publication_lag_or_old_target_pdf=39`, `non_target_candidates_only=8`, and
  `site_fetch_error_only=1`.
- 2026-05-12 v227 Windows package refresh →
  commit `df99e7223de12cddaebe506e9dc87413f206817d` packages root fallback when
  a registered school publication URL returns non-HTML content, such as an
  image landing asset instead of a disclosure page. Verification:
  `uv run pytest tests/unit/test_pdf_discovery.py -q` → `65 passed, 5 warnings`;
  `uv run ruff check src/eidp/scraper/pdf_discovery.py
  tests/unit/test_pdf_discovery.py` → all checks passed; `uv run pytest
  tests/unit -q` → `1164 passed, 5 warnings`; `uv run python
  scripts/verify_windows_distribution.py dist/eidp-windows-v227.zip --json`
  and the same command against `dist/eidp-windows.zip` → `ok=true`, SHA256
  `450fa7e157cfe4702f9136ed8d56feb965f05117310cbc702118b9ea7cc936f2`,
  3,026 entries, 78 wheels, 16 discovery gold-set entries, 47 prefecture seed
  rows, 2,148 prefecture seed school rows, BUILD_INFO `git_dirty=false`.
  Remote Windows fresh extraction `C:\Users\cyo20\EIDP-v227-df99e72` verified
  the ZIP checksum, and `EIDP-setup.bat` completed with the packaged validator
  reporting `school_count=2418`, `school_fiscal_year_status_count=2418`,
  `sqlite_integrity_check=ok`, `department_change` void columns present, and
  `uq_document_file_hash` present. A separate
  `scripts\validate_install.bat --after-setup --json` run returned `ok=true`
  for the same extraction. A copied-DB rerun for v226 Saitama school `754`
  now follows the root page, reaches the disclosure page, and records old-year
  target-form evidence including `fiscal_year_mismatch:2021`,
  `fiscal_year_mismatch:2023`, `fiscal_year_mismatch:2024`, and
  `fiscal_year_mismatch:2025` instead of `no_candidates_found`.
- 2026-05-12 v226 Windows package refresh →
  commit `f5f59efdc1fde22cdb4db5717bee4bfab11a090e` packages same-origin
  WordPress Download Manager PDF candidate extraction (`data-downloadurl` /
  `wpdmdl`) and final-response URL handling for redirected school pages.
  Verification: `uv run pytest tests/unit` → `1163 passed, 5 warnings`;
  `uv run python scripts/verify_windows_distribution.py
  dist/eidp-windows-v226.zip --json` and the same command against
  `dist/eidp-windows.zip` → `ok=true`, SHA256
  `d13f1bbae84b8857a78224d7c3c7e809ecd8c2bbc617eece2a1fc300acab566f`,
  3,026 entries, 78 wheels, 16 discovery gold-set entries, 47 prefecture seed
  rows, 2,148 prefecture seed school rows, BUILD_INFO `git_dirty=false`.
  A copied-DB rerun for v224 Saitama school `760` now discovers two
  `wordpress_download_manager` candidates and records them as target
  `fiscal_year_mismatch:2024` / `fiscal_year_mismatch:2023` instead of
  `no_candidates_found`, proving the RCA bucket is accurate for this WordPress
  Download Manager pattern. Remote Windows fresh extraction
  `C:\Users\cyo20\EIDP-v226-f5f59ef` verified the ZIP checksum, and
  `EIDP-setup.bat` completed with the packaged validator reporting
  `school_count=2418`, `school_fiscal_year_status_count=2418`,
  `sqlite_integrity_check=ok`, `department_change` void columns present, and
  `uq_document_file_hash` present. A separate
  `scripts\validate_install.bat --after-setup --json` run returned `ok=true`
  for the same extraction. A real bounded Saitama official-index acquisition
  run on this extraction produced official-index `extracted=58`, `matched=51`,
  `added=51`, crawl `found=49`, `downloaded=3`, ingest `processed=3`,
  `yearly_upserted=9`, and status rebuild `target_pdf_auto_acquired_count=3`,
  `target_pdf_auto_yield_pct=0.1`, `ship_gate_status=below_gate`. The
  non-release validator path returned `ok=true`, while `--require-ship-gate`
  correctly returned rc `1`.
- 2026-05-12 v225 Windows package refresh →
  commit `6791637ce273a6275ab786ed096ecf13b9b845bd` packages the
  `import-excel` `invalid_year` warning surface and the discovery RCA packet
  fix that preserves `school_id` inside compact `latest_evidence_rows`.
  Verification: `uv run pytest tests/unit` → `1161 passed, 5 warnings`;
  `uv run python scripts/verify_windows_distribution.py
  dist/eidp-windows-v225.zip --json` and the same command against
  `dist/eidp-windows.zip` → `ok=true`, SHA256
  `455f3fbfc2bbe72a595329404b7c8e8a8fb98726459a2f9073fc4653163f364d`,
  3,026 entries, 78 wheels, 16 discovery gold-set entries, 47 prefecture seed
  rows, 2,148 prefecture seed school rows, BUILD_INFO `git_dirty=false`.
  A local regeneration of the v224 Saitama RCA batch plan using the copied
  Windows v224 SQLite DB and evidence JSONL proves compact rows now preserve
  school identity, for example school `15` packet evidence row IDs are
  `[15, 15, 15, 15, 15]`. Remote Windows fresh extraction
  `C:\Users\cyo20\EIDP-v225-6791637` verified the ZIP checksum, and
  `EIDP-setup.bat` completed with the packaged validator reporting
  `school_count=2418`, `school_fiscal_year_status_count=2418`,
  `sqlite_integrity_check=ok`, `department_change` void columns present, and
  `uq_document_file_hash` present. A separate
  `scripts\validate_install.bat --after-setup --json` run returned `ok=true`
  for the same extraction.
- 2026-05-12 v224 Windows package and real Saitama official-index RCA →
  commit `1e890e9016c9e979e19eff09b8dc5f85ef6bd2f4` extends the target-form
  link hint set so `更新確認申請書` / renewal-confirmation application anchors
  can be accepted when the source is trusted official-index evidence instead
  of being pre-filtered as generic disclosure material. Verification:
  `uv run pytest tests/unit` → `1160 passed, 5 warnings`; `uv run python
  scripts/verify_windows_distribution.py dist/eidp-windows-v224.zip --json`
  and the same command against `dist/eidp-windows.zip` → `ok=true`,
  SHA256 `d178f7ac738fca8ab3f94f3aaf24dc1fb6f669d048f976b44ad1deafa1b654b2`,
  3,026 entries, 78 wheels, 16 discovery gold-set entries, 47 prefecture seed
  rows, 2,148 prefecture seed school rows, BUILD_INFO `git_dirty=false`.
  Remote Windows fresh extraction `C:\Users\cyo20\EIDP-v224-1e890e9` verified
  the ZIP checksum and `first_setup.bat` completed with `school_count=2418`,
  `school_fiscal_year_status_count=2418`, `sqlite_integrity_check=ok`,
  `department_change` void columns present, and `uq_document_file_hash`
  present. A real Saitama official-index run with
  `scripts\bootstrap_pdfs.bat --pref saitama --skip-known-url-discovery
  --url-search off --school-url-crawl off --batch-size 60 --rate-limit 0.5`
  created `logs\bootstrap-pdfs-20260511-232235.log` and `.json`, applied
  Saitama official-index URLs (`extracted=58`, `matched=51`, `added=51`),
  crawled `51` sites, found `49`, downloaded `3`, ingested `3`, upserted `9`
  target-year rows, and wrote RCA plan
  `data\output\target-year-discovery\bootstrap-20260511_233857-discovery-rca-batch-plan.json`
  with `10` items / `48` candidates. The accepted target PDFs were schools
  `757`, `95`, and `784`; school `784`
  `https://www.saijidai.ac.jp/sys/wp-content/themes/saijidai/pdf/evaluation/koutoumusyou.pdf`
  is the v224 regression proof for the new `更新確認申請書` hint. The same run
  still records `target_pdf_auto_acquired_count=3`,
  `target_pdf_auto_denominator_count=2418`, `target_pdf_auto_yield_pct=0.1`,
  and `ship_gate_status=below_gate`. `validate_install.bat --after-setup
  --after-bootstrap --json` returned `ok=true`; the same command with
  `--require-ship-gate` returned rc `1`; `diagnose.bat` wrote
  `logs\diagnostics-20260512-001612.txt` and recorded
  `validate_after_bootstrap_ship_gate_rc=1`. A manual/Codex sample check of
  rejected current-looking rows confirmed `applicationform-r8.pdf` is a
  student `授業料等減免の対象者の認定` A-form, not an institution confirmation
  application, and the sampled `academic_support.pdf` begins with
  `実務経験のある教員等による授業科目` / `理事の複数配置` material rather than a
  current target-year confirmation main form. These samples should stay
  rejected or review-bound; broad token loosening would pollute target success.
- 2026-05-11 v223 Windows package and remote smoke →
  commit `0dce42cdc6d87cbbebbc70e27820069156457ff2` fixes a Windows batch
  diagnostic defect found during v222 smoke: `diagnose.bat` used parse-time
  `%ERRORLEVEL%` inside parenthesized blocks, so a failed
  `--require-ship-gate` validation was recorded as rc `0`. The script now uses
  delayed `!ERRORLEVEL!` capture for all embedded validator calls, and the
  distribution verifier rejects ZIPs missing that contract. Verification:
  `uv run pytest tests/unit` → `1158 passed, 5 warnings`; `uv run python
  scripts/verify_windows_distribution.py dist/eidp-windows-v223.zip --json`
  and the same command against `dist/eidp-windows.zip` → `ok=true`,
  SHA256 `425f7a215332bc37cb91f8f316c2b479728f0f2def9de6ad81ee29bf387300cb`,
  3,026 entries, 78 wheels, 16 discovery gold-set entries, 47 prefecture seed
  rows, 2,148 prefecture seed school rows, BUILD_INFO `git_dirty=false`.
  Remote Windows fresh extraction `C:\Users\cyo20\EIDP-v223-0dce42c` verified
  the ZIP checksum, `first_setup.bat` completed with `school_count=2418`,
  `school_fiscal_year_status_count=2418`, `sqlite_integrity_check=ok`,
  `department_change` void columns present, and `uq_document_file_hash`
  present. A lock smoke proved `db-bootstrap --sqlite` and
  `rebuild-school-year-tasks` return rc `5` while `data\.lock` is held.
  Bounded `scripts\bootstrap_pdfs.bat --pref saitama --batch-size 0` created
  `logs\bootstrap-pdfs-20260511-225600.log` and `.json`, applied Saitama
  official-index URLs (`matched=51`, `added=51`), and recorded
  `ship_gate_status=below_gate`, `target_pdf_auto_yield_pct=0.0`.
  `validate_install.bat --after-setup --after-bootstrap --json` returned
  `ok=true`; the same command with `--require-ship-gate` returned rc `1` and
  `ok=false` with `bootstrap ship_gate_status must be pass...`. The v223
  diagnostic file now records `validate_after_bootstrap_ship_gate_rc=1`.
- 2026-05-11 v220 local package refresh →
  commit `d0d62c9bc98e8af9f6bec1723da611ce6e9ca3c6` extends the operator
  diagnostic package so `EIDP-diagnose.bat` records both regular validation
  and strict `--require-ship-gate` validation for bootstrap and weekly evidence.
  The diagnostic output now includes `validate_after_bootstrap_ship_gate_rc` and
  `validate_after_weekly_ship_gate_rc`, so a support/audit review can see
  whether deployment really passed the SQLite-backed ship gate without asking
  the operator to run extra commands. Verification: `uv run pytest
  tests/unit/test_windows_distribution_verifier.py -q` → `58 passed`;
  `uv run ruff check scripts/verify_windows_distribution.py
  tests/unit/test_windows_distribution_verifier.py` → passed.
- v220 Windows ZIP artifacts were rebuilt locally at commit
  `d0d62c9bc98e8af9f6bec1723da611ce6e9ca3c6`: `dist/eidp-windows-v220.zip`
  and latest alias `dist/eidp-windows.zip` both have SHA256
  `034e1faf06c955d9bf4163bdb9fb7b3b8e1a465499274d1ea06033321b53e3cb`.
  `uv run python scripts/verify_windows_distribution.py
  dist/eidp-windows-v220.zip --json` and the same command against
  `dist/eidp-windows.zip` returned `ok=true`, `errors=[]`, and `warnings=[]`,
  with 3,026 ZIP entries, 78 wheels, 16 packaged discovery gold-set entries,
  and BUILD_INFO `git_dirty=false`. An extracted-install check at
  `/tmp/eidp-v220-extract` returned `ok=true`, `errors=[]`, `warnings=[]`,
  `master_xlsx_present=true`, and `wheel_count=78`.
- 2026-05-11 v219 local package refresh →
  commit `a857515b60306d4c427ec317450ea0a42f3c054a` adds a stricter Windows
  release gate: `scripts/validate_windows_install.py --require-ship-gate` no
  longer trusts bootstrap/weekly JSON alone. For bootstrap, the validator now
  recomputes active `専門学校` target-FY coverage directly from
  `data/eidp.sqlite3` and rejects a logged `ship_gate_status="pass"` when the
  SQLite coverage is below the 60% gate. For weekly runs, it validates
  `last_run.json` against the timestamped summary and checks
  `summary.after.coverage` against SQLite current coverage, preventing stale
  `last_run.json` from masquerading as a passed deployment. The bootstrap
  progress payload now also records `current_fy`.
  Verification: `uv run pytest tests/unit/test_windows_install_validator.py
  tests/unit/test_windows_distribution_verifier.py -q` → `97 passed`;
  `uv run pytest tests/unit -q` → `1151 passed, 5 warnings`; `uv run ruff
  check scripts/validate_windows_install.py scripts/verify_windows_distribution.py
  scripts/bootstrap_pdf_pipeline.py tests/unit/test_windows_install_validator.py
  tests/unit/test_windows_distribution_verifier.py tests/unit/test_bootstrap_pdf_pipeline.py`
  → passed.
- v219 Windows ZIP artifacts were rebuilt locally at commit
  `a857515b60306d4c427ec317450ea0a42f3c054a`: `dist/eidp-windows-v219.zip`
  and latest alias `dist/eidp-windows.zip` both have SHA256
  `ac2358f69f0e13dbf3f2e1e0beaf85607ccc67473f24206206c5b1dfc4cca747`.
  `uv run python scripts/verify_windows_distribution.py
  dist/eidp-windows-v219.zip --json` and the same command against
  `dist/eidp-windows.zip` returned `ok=true`, `errors=[]`, and `warnings=[]`,
  with 3,026 ZIP entries, 78 wheels, 16 packaged discovery gold-set entries,
  and BUILD_INFO `git_dirty=false`. An extracted-install check at
  `/tmp/eidp-v219-extract` returned `ok=true`, `errors=[]`, `warnings=[]`,
  `master_xlsx_present=true`, and `wheel_count=78`.
- 2026-05-11 v218 local package refresh →
  commit `10043b45954578e9ccbf32d9b96961aa5082758b` hardens the Windows
  install validator's actual SQLite setup gate further: `--after-setup` now
  requires the objective-critical `support_recipient`, `department_change`, and
  `review_item` tables, records/fails on actual `PRAGMA integrity_check`, and
  verifies the `department_change` void columns plus `document.uq_document_file_hash`
  unique index. The distribution verifier gates the packaged validator contract
  through `support_recipient`, `sqlite_integrity_check`, `PRAGMA integrity_check`,
  `department_change missing column`, and `uq_document_file_hash` tokens. This
  builds on the v216 CLI deployment-report
  hardening: `eidp report ... --json` returns `error="database_not_ready"` with
  exit code 2 when the DB schema is missing, instead of leaking a SQLAlchemy
  traceback. The core ZIP also continues to require
  `src/eidp/excel/competition_exporter.py` and preserve the target-FY business
  export contract: default to `settings.target_fiscal_year`, reject empty
  target-year business exports with `TargetFiscalYearDataMissingError`, filter
  `gap_report_for_export(..., school_type="専門学校")`, and return target-year
  readiness metrics. Verification: `uv run pytest
  tests/unit/test_windows_install_validator.py
  tests/unit/test_windows_distribution_verifier.py -q` → `95 passed`;
  `uv run pytest tests/unit -q` → `1149 passed, 5 warnings`; `uv run ruff
  check scripts/validate_windows_install.py scripts/verify_windows_distribution.py
  tests/unit/test_windows_install_validator.py
  tests/unit/test_windows_distribution_verifier.py` → passed.
- v218 Windows ZIP artifacts were rebuilt locally at commit
  `10043b45954578e9ccbf32d9b96961aa5082758b`: `dist/eidp-windows-v218.zip`
  and latest alias `dist/eidp-windows.zip` both have SHA256
  `de4cae750b78bfdcc15f558868be02b8f6e504f942c71fd8f819fc7a2f0d5890`.
  `uv run python scripts/verify_windows_distribution.py
  dist/eidp-windows-v218.zip --json` returned `ok=true`, `errors=[]`, and
  `warnings=[]`, with 3,026 ZIP entries, 78 wheels, 16 packaged discovery
  gold-set entries, and BUILD_INFO `git_dirty=false`. An extracted-install
  check at `/tmp/eidp-v218-extract` returned `ok=true`, `errors=[]`,
  `warnings=[]`, `master_xlsx_present=true`, and `wheel_count=78`.
- 2026-05-11 v214 local package refresh →
  commit `8969ceb3f6325a6c71a6ccd63a7fcb3164ec1291` fixes an operator audit
  gap: approving a department-alias proposal now writes
  `ManualActionLog(action_type="dept_alias_approved")` against
  `department_change`. The distribution verifier also gates packaged
  operator-action audit contracts for school-code review, URL-candidate
  review, department alias approval/void, manual entry, and fiscal-year
  override. Verification: `uv run pytest tests/unit/test_operator_proposals.py
  tests/unit/test_review_app.py tests/unit/test_review_url_candidate_review.py
  tests/unit/test_manual_entry_contract.py tests/unit/test_fiscal_year_override.py
  tests/unit/test_windows_distribution_verifier.py -q` → `114 passed`;
  `uv run ruff check src/eidp/review/operator_pages.py
  tests/unit/test_operator_proposals.py scripts/verify_windows_distribution.py
  tests/unit/test_windows_distribution_verifier.py` → passed; `uv run pytest
  tests/unit -q` → `1140 passed, 5 warnings`.
- 2026-05-11 v213 local package refresh →
  commit `5fdd27577a5893d922a5c1612d7d56ed1aaae7da` adds a release verifier
  gate for packaged SQLite bootstrap data-loss safeguards, following the v212
  OCR runtime/availability gate. The core ZIP must
  now contain `src/eidp/db/sqlite_bootstrap.py` with orphaned-sidecar refusal,
  SQLite `integrity_check`, additive upgrade columns, and document hash uniqueness
  safeguards; v212 also gated `src/eidp/ocr/tesseract.py` and
  `src/eidp/ocr/availability.py` for the add-on path, Japanese tessdata,
  Tesseract subprocess wrapper, and operator-facing OCR availability checks.
  Verification: `uv run pytest tests/unit/test_windows_distribution_verifier.py
  tests/unit/test_sqlite_bootstrap.py tests/unit/test_windows_install_validator.py -q`
  → `111 passed`; OCR/verifier related tests previously returned `87 passed`;
  `uv run ruff check scripts/verify_windows_distribution.py
  tests/unit/test_windows_distribution_verifier.py` → passed; `uv run pytest
  tests/unit -q` → `1139 passed, 5 warnings`.
- 2026-05-11 v211 local package refresh →
  commit `aec802a3f05fab00128d86435af0ef65e21aebab` keeps the operator UI
  school scope vocational-only (`専門学校`) so the Streamlit task board, PDF
  manual-entry page, and Excel preview denominators match the current v1
  ship-gate scope instead of mixing universities into the operator denominator.
  Verification: `uv run pytest tests/unit/test_review_school_scope.py
  tests/unit/test_target_year_status.py tests/unit/test_review_excel_preview.py
  tests/unit/test_review_pdf_manual_entry.py
  tests/unit/test_review_school_year_tasks.py -q` → `111 passed`; `uv run ruff
  check src/eidp/review/school_scope.py
  tests/unit/test_review_school_scope.py` → passed; `uv run pytest tests/unit
  -q` → `1131 passed, 5 warnings`.
- v211 Windows ZIP artifacts were rebuilt locally at commit
  `aec802a3f05fab00128d86435af0ef65e21aebab`: `dist/eidp-windows-v211.zip`
  and latest alias `dist/eidp-windows.zip` both have SHA256
  `9e386ee1c7a793d13fc96e7236517e2ba8d3d56a4ac226b7f0da1090d2b8f98c`.
  `uv run python scripts/verify_windows_distribution.py
  dist/eidp-windows-v211.zip --json` and the same command for
  `dist/eidp-windows.zip` both returned `ok=true`, `errors=[]`, and
  `warnings=[]`, with 47 prefecture seed rows, 47 parser registrations, 47
  downloadable official artifact URLs, 2,148 official seed school rows, 78
  wheels, and 16 packaged discovery gold-set entries. An extracted-install
  check at `_temp/verify-v211-install-aec802a-20260511174307` returned
  `ok=true`, `errors=[]`, and `warnings=[]`.
- `uv run eidp discovery-gold-set --json` currently reports `total_entries=16`,
  `strict_target_year_successes=6`, `operator_review_entries=6`,
  `publication_lag_entries=2`, and outcome counts
  `accepted_target_pdf=6`, `needs_operator_review=6`,
  `publication_lag_latest_public=2`, `no_target_candidate_found=1`, and
  `site_fetch_error=1`. This is useful as a regression surface, but it is not a
  substitute for the 60-70% real strict-FY yield gate.
- Security-only review of `sprint8-handoff-finalize` reported no HIGH or
  MEDIUM security vulnerabilities across subprocess use, unsafe
  deserialization, SQL injection, SSRF, path traversal, Streamlit HTML, XXE,
  hardcoded secrets, RCA prompt-injection defenses, gold-set JSON loading, and
  Windows batch/PowerShell quoting. This review explicitly excludes
  operational/data-loss risks such as SQLite upgrade paths, integrity checks,
  and atomic writes, which remain tracked outside the security surface.
- Current blocker remains real Windows validation for the latest package:
  `nc -G 3 -vz 192.168.0.9 22` still times out from macOS, so v211 has not yet
  replaced the older v154 Windows extraction/setup/Saitama E2E smoke as the
  latest real Windows proof. The active goal therefore remains incomplete until
  Windows connectivity and a broader strict target-FY yield run are restored.
- `sprint8-handoff-finalize` remains the active handoff branch; `main` is
  intentionally unchanged until the yield gate is met.
- `uv run pytest tests/unit/test_pdf_parser_regression.py -q -k "blank_advanced"` → `1 passed`; `uv run pytest tests/unit/test_pdf_parser_regression.py -q` → `9 passed`; `uv run ruff check src/eidp/pdf/extractor.py tests/unit/test_pdf_parser_regression.py` → passed; real school `757` parse now returns `graduates=86` and confidence composite `0.94`; `uv run pytest tests/unit/test_pdf_parser_regression.py tests/unit/test_ingest_confidence_gating.py tests/unit/test_normal_ingest_appendonly.py tests/unit/test_manual_entry_contract.py -q` → `57 passed`; `uv run pytest tests/unit -q` → `1046 passed, 5 warnings`.
- Current-code school `757` post-graduation-parser replay →
  `_temp/saitama-school757-current-after-graduates-20260511-102416`
  produced strict discovery `downloaded=1`, then `ingest-pdfs --document-id 2`
  produced `processed=1`, `departments_created=0`, `yearly_upserted=1`,
  `yearly_current=1`, and `yearly_review_pending=0`. The FY2026 yearly row is
  attached to the existing `医療` / `第一学科` Department with `capacity=300`,
  `enrollment=263`, `graduates=86`, `extraction_confidence=0.94`, and
  `is_current=True`.
- `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v154.zip --playwright-addon dist/eidp-playwright-addon-windows-v106.zip --json` → `OK core`, `OK playwright-addon`, `git_commit=26d18a9aac2cc2e89705f3de5551f7003e8091f8`, `git_dirty=false`, `entry_count=3018`, `wheel_count=78`, `project_wheel_count=1`, `discovery_gold_set_entries=14`, 47 prefecture seed rows/parser registrations/downloadable artifact URLs, `prefecture_seed_school_rows_total=2148`, core SHA256 `fea99a950b0b671c75202cf470d4c06c6169bc299e013c0b45f3caaabe417952`, add-on SHA256 `f6fe0cd095c337a81a870decb7a18e9d1f40044dd1567b017d92eda3aae1e8e8`.
- Windows v154 clean extraction/setup smoke →
  SHA256 matched on Windows, `C:\EIDP-v154-26d18a9` extracted cleanly,
  `first_setup.bat` completed, the setup validator reported `OK install`,
  `build_commit=26d18a9aac2cc2e89705f3de5551f7003e8091f8`,
  `build_dirty=false`, `school_count=2418`,
  `school_fiscal_year_status_count=2418`, required tables present, and
  `wheel_count=78`. A standalone
  `scripts\validate_windows_install.py . --json` run returned `ok=true` with
  no errors or warnings.
- Windows v154 packaged Saitama official-index and school `757` E2E smoke →
  Saitama apply produced `extracted=58`, `matched=51`, `added=51`, and
  `review_items=2`. `discover-pdfs --discovery-method prefecture_aggregator
  --school-id 757` produced `downloaded=1`; `ingest-pdfs --document-id 1`
  produced `processed=1`, `departments_created=0`, `yearly_upserted=1`, and
  `yearly_current=1`; `rebuild-school-year-tasks --fiscal-year 2026
  --school-type 専門学校` produced `excel_ready=1`; `export-excel --output
  output\v154_school757_export.xlsx` succeeded; DB/XLSX inspection found one
  `上尾中央看護専門学校` row in `学科別` and one in `在籍のみ抜粋`.
- `uv run pytest tests/unit/test_ingest_confidence_gating.py -q -k "nursing_course_name or specialized_suffix"` → `2 passed`; `uv run ruff check src/eidp/pipeline/ingest.py tests/unit/test_ingest_confidence_gating.py` → passed; `uv run pytest tests/unit/test_ingest_confidence_gating.py tests/unit/test_normal_ingest_appendonly.py tests/unit/test_manual_entry_contract.py -q` → `48 passed`; `uv run pytest tests/unit -q` → `1045 passed, 5 warnings`.
- Current-code school `757` ingest replay →
  `_temp/saitama-school757-ingest-medical-alias-20260511-101321` produced
  strict discovery `downloaded=1`, then `ingest-pdfs --document-id 2`
  produced `processed=1`, `departments_created=0`, and `yearly_upserted=1`.
  The existing Department remains `(course_name="医療",
  canonical_name="第一学科")`, and the FY2026 yearly row is attached to that
  Department with `extraction_confidence=0.64` / `is_current=False`.
- `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v153.zip --playwright-addon dist/eidp-playwright-addon-windows-v106.zip --json` → `OK core`, `OK playwright-addon`, `git_commit=910afadeaf77002f541b5e1bc4ccb8870a56122f`, `git_dirty=false`, `entry_count=3018`, `wheel_count=78`, `project_wheel_count=1`, `discovery_gold_set_entries=14`, 47 prefecture seed rows/parser registrations/downloadable artifact URLs, `prefecture_seed_school_rows_total=2148`, core SHA256 `76b4e9420732ac287423bf492d9f0f69ff60c0532b08ea1576d7f111f07f5930`, add-on SHA256 `f6fe0cd095c337a81a870decb7a18e9d1f40044dd1567b017d92eda3aae1e8e8`.
- Windows v153 clean extraction/setup smoke →
  SHA256 matched on Windows, `C:\EIDP-v153-910afad` extracted cleanly,
  `first_setup.bat` completed, the setup validator reported `OK install`,
  `build_commit=910afadeaf77002f541b5e1bc4ccb8870a56122f`,
  `build_dirty=false`, `school_count=2418`,
  `school_fiscal_year_status_count=2418`, required tables present, and
  `wheel_count=78`. A standalone
  `scripts\validate_windows_install.py . --json` run returned `ok=true` with
  no errors or warnings.
- Windows v153 packaged Saitama official-index and school `757` smoke →
  Saitama apply produced `extracted=58`, `matched=51`, `added=51`, and
  `review_items=2`. `discover-pdfs --discovery-method prefecture_aggregator
  --school-id 757` produced `downloaded=1`; `ingest-pdfs --document-id 1`
  produced `processed=1`, `departments_created=0`, and `yearly_upserted=1`.
  The document remains `review_pending` and the FY2026 yearly row has
  `extraction_confidence=0.64`.
- `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v152.zip --playwright-addon dist/eidp-playwright-addon-windows-v106.zip --json` → `OK core`, `OK playwright-addon`, `git_commit=d90d0a16d382d87f51ae3ecce433198a087eb748`, `git_dirty=false`, `entry_count=3018`, `wheel_count=78`, `project_wheel_count=1`, `discovery_gold_set_entries=14`, `discovery_gold_set_outcomes={"accepted_target_pdf": 6, "needs_operator_review": 5, "no_target_candidate_found": 1, "publication_lag_latest_public": 2}`, 47 prefecture seed rows/parser registrations/downloadable artifact URLs, `prefecture_seed_school_rows_total=2148`, core SHA256 `1b91ee2dd1ac577a45f5d5afa8cdd4c747c5c57544c0c7ad47839a7eb0e58afb`, add-on SHA256 `f6fe0cd095c337a81a870decb7a18e9d1f40044dd1567b017d92eda3aae1e8e8`.
- Windows v152 clean extraction/setup smoke →
  SHA256 matched on Windows, `C:\EIDP-v152-d90d0a1` extracted cleanly,
  `first_setup.bat` completed, the setup validator reported `OK install`,
  `build_commit=d90d0a16d382d87f51ae3ecce433198a087eb748`,
  `build_dirty=false`, `school_count=2418`,
  `school_fiscal_year_status_count=2418`, required tables present, and
  `wheel_count=78`. A standalone
  `scripts\validate_windows_install.py . --json` run returned `ok=true` with
  no errors or warnings.
- Windows v152 packaged Saitama official-index and school `757`
  trusted-year smoke →
  Saitama apply produced `extracted=58`, `matched=51`, `added=51`, and
  `review_items=2`. `discover-pdfs --discovery-method prefecture_aggregator
  --school-id 757` produced `crawled=1`, `found=1`, `downloaded=1`,
  `failed=0`, and accepted
  `https://ageo.org/files/admission/support/study_support_system.pdf` with
  `detected_fiscal_year=""` and
  `year_evidence=prefecture_index_current_year`. `ingest-pdfs --document-id 1`
  produced `processed=1`, `departments_created=1`, `yearly_upserted=1`; the
  document remains `review_pending` and the yearly row has
  `extraction_confidence=0.64`.
- `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v151.zip --playwright-addon dist/eidp-playwright-addon-windows-v106.zip --json` → `OK core`, `OK playwright-addon`, `git_commit=6e1a0d814c43fce785de9784ec2bf1a27db1aaf1`, `git_dirty=false`, `entry_count=3018`, `wheel_count=78`, `project_wheel_count=1`, `discovery_gold_set_entries=14`, 47 prefecture seed rows/parser registrations/downloadable artifact URLs, `prefecture_seed_school_rows_total=2148`, core SHA256 `0966345403ec8d44c18dc5c908f685528c262c849ecc31d5041a02082285e2f5`, add-on SHA256 `f6fe0cd095c337a81a870decb7a18e9d1f40044dd1567b017d92eda3aae1e8e8`.
- Windows v151 clean extraction/setup smoke →
  SHA256 matched on Windows, `C:\EIDP-v151-6e1a0d8` extracted cleanly,
  `first_setup.bat` completed, the setup validator reported `OK install`,
  `build_commit=6e1a0d814c43fce785de9784ec2bf1a27db1aaf1`,
  `build_dirty=false`, `school_count=2418`,
  `school_fiscal_year_status_count=2418`, required tables present, and
  `wheel_count=78`. A standalone
  `scripts\validate_windows_install.py . --json` run returned `ok=true` with
  no errors or warnings.
- Windows v151 packaged Saitama official-index and school `764` diagnostic
  smoke →
  Saitama apply produced `extracted=58`, `matched=51`, `added=51`, and
  `review_items=2`. `discover-pdfs --discovery-method prefecture_aggregator
  --school-id 764` produced `crawled=1`, `found=1`, `downloaded=0`,
  `failed=0`, and no `2029` reject bucket. The
  `2025koushinshinseisyo.pdf` evidence row is now
  `fiscal_year_mismatch:2025`.
- Focused v150 CLI encoding regression, Ruff, and full unit suite after the
  Windows codepage-safe CLI patch →
  `uv run pytest tests/unit/test_cli_ingest.py -q` → `2 passed`;
  `uv run ruff check src/eidp/cli.py tests/unit/test_cli_ingest.py` →
  passed; `uv run pytest tests/unit -q` → `1038 passed, 5 warnings`.
- `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v150.zip --playwright-addon dist/eidp-playwright-addon-windows-v106.zip --json` → `OK core`, `OK playwright-addon`, `git_commit=d303b44c239706ccd7cdca854c3e53c9a66b3d4e`, `git_dirty=false`, `entry_count=3016`, `wheel_count=78`, 47 prefecture seed rows/parser registrations/downloadable artifact URLs, `prefecture_seed_school_rows_total=2148`, core SHA256 `5395b14b2f5263bc0138a04c7b2cd32ff6debffb4435bc079ff06f715672f923`, add-on SHA256 `f6fe0cd095c337a81a870decb7a18e9d1f40044dd1567b017d92eda3aae1e8e8`.
- Windows v150 clean extraction/setup smoke →
  SHA256 matched on Windows, `C:\EIDP-v150-d303b44` extracted cleanly,
  `first_setup.bat` completed, validator reported `OK install`,
  `build_commit=d303b44c239706ccd7cdca854c3e53c9a66b3d4e`,
  `build_dirty=false`, `school_count=2418`,
  `school_fiscal_year_status_count=2418`, required tables present, and
  `wheel_count=78`.
- Windows v150 packaged school `95` target-PDF-to-Excel smoke →
  Saitama official-index step produced `extracted=58`, `matched=51`,
  `added=51`; strict `discover-pdfs --school-id 95` downloaded 1 target PDF;
  `ingest-pdfs --document-id 1` completed without the v149
  `UnicodeEncodeError` and produced `departments_created=0`,
  `yearly_upserted=2`; `rebuild-school-year-tasks` produced
  `excel_ready=1`; `export-excel` wrote
  `C:\EIDP-v150-d303b44\output\v150_school95_export.xlsx`.
- Windows v150 DB/XLSX verification →
  document `1` is `fiscal_year=2026`, `pdf_type=target`,
  `ingest_status=ingested`, and `is_current_year=1`; school `95` has 2 master
  departments and 2 current FY2026 yearly rows; status is
  `confirmed_target` / `prev_year_diff` / `excel_ready=1`; the workbook has 2
  `さいたまIT・WEB専門学校` rows in `学科別` and 2 in `在籍のみ抜粋`.
- Windows v150 packaged Saitama 51-site replay →
  `C:\EIDP-v150-d303b44` held 51 Saitama `prefecture_aggregator`
  `SchoolSite` rows; after the existing school `95` accepted document, the
  packaged 50-site `discover-pdfs` replay produced evidence for every remaining
  official-index site and no additional target downloads. Evidence rows:
  `449`; reason buckets: `classified_non_target=166`,
  `fiscal_year_mismatch=171`, `pre_filtered_non_target_hint=90`,
  `all_negative_score=10`, `not_pdf_magic=5`,
  `http_error:HTTPStatusError=4`, `target_fiscal_year_not_detected=1`,
  `no_candidates_found=1`, and `discovery_error=1`.
- Discovery gold-set expansion from that replay →
  added `saitama-it-web-accepted-2026` and
  `ageo-central-nursing-review-2026`; `uv run eidp discovery-gold-set --json`
  now reports `total_entries=14`, `accepted_target_pdf=6`,
  `needs_operator_review=5`, and `strict_target_year_successes=6`.
  Focused gold-set tests passed, a two-school current evidence eval produced
  `exact_matches=2`, and full unit regression passed with
  `1045 passed, 5 warnings`.
- Current-code Saitama official-index trusted-year replay →
  `_temp/saitama-current51-prefindex-trusted-20260511-094241` crawled the 50
  remaining Saitama official-index sites after the school `95` accepted
  document was already present. It produced one additional target download:
  school `757` with `year_evidence=prefecture_index_current_year`. The copied
  DB now has two FY2026 target documents across the 51 Saitama
  `prefecture_aggregator` schools: school `95` and school `757`. Ingest of
  school `757` completed but remains review-bound (`ingest_status=review_pending`,
  `extraction_confidence=0.64`) because of a master/PDF course-label mismatch.
- Saitama school `764` future-term year diagnostic fix →
  the real `2025koushinshinseisyo.pdf` previously produced
  `fiscal_year_mismatch:2029` because an officer-term `2029年度` label was
  accepted as PDF-body fiscal-year evidence. Current code applies the strict
  target-year ceiling to explicit western/Japanese fiscal-year labels and the
  same real PDF now returns `('target', 'fiscal_year_mismatch:2025')`.
  Focused PDF discovery tests passed (`54 passed`), Ruff passed, and full unit
  regression passed with `1042 passed, 5 warnings`.
- Focused v149 first-year Japanese-era regression, Saitama school `773`
  replay, full current Saitama replay, Ruff, and full unit suite after the
  `元年度` parser patch →
  `uv run pytest tests/unit/test_fiscal_year.py
  tests/unit/test_pdf_discovery.py tests/unit/test_discovery_evidence_summary.py
  tests/unit/test_school_fiscal_year_status.py -q` → `72 passed`;
  `uv run ruff check src/eidp/fiscal_year.py tests/unit/test_fiscal_year.py
  src/eidp/scraper/pdf_discovery.py tests/unit/test_pdf_discovery.py` →
  passed; `uv run pytest tests/unit -q` → `1037 passed, 5 warnings`.
- Saitama school `773` replay at
  `_temp/saitama-reiwa-gannen-replay-20260511-082352` →
  `令和元年度確認申請書` is now `fiscal_year_mismatch:2019`, and the
  `令和7年度確認申請書` anchor is no longer polluted by previous-year context.
- Full current Saitama replay at
  `_temp/saitama-current51-v149-rerun-20260511-082438` →
  `crawled=50`, `found=48`, `downloaded=0`, `failed=6`, `skipped=348`,
  `cached_rejections=36`, `prefiltered=138`, and
  `rejection_reason_target_fiscal_year_not_detected=1`. The only remaining
  target-year-unverified school is `757`.
- `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v149.zip --playwright-addon dist/eidp-playwright-addon-windows-v106.zip --json` → `OK core`, `OK playwright-addon`, `git_commit=0dc3d2e5fff5e09300e7d126f55735f90baa995e`, `git_dirty=false`, `entry_count=3016`, `wheel_count=78`, 47 prefecture seed rows/parser registrations/downloadable artifact URLs, `prefecture_seed_school_rows_total=2148`, core SHA256 `ca456a355781cf60e0fb3ccec06b4e3c8a2e75f1e8df42e3e9b0100a0340051b`, add-on SHA256 `f6fe0cd095c337a81a870decb7a18e9d1f40044dd1567b017d92eda3aae1e8e8`.
- Focused v148 adjacent-context regression, Saitama Goope replay, Ruff, and
  full unit suite after the CMS adjacent-year context patch →
  `uv run pytest tests/unit/test_pdf_discovery.py::test_download_pdf_rejects_stale_year_from_adjacent_html_context -q`
  failed before the patch with `target_fiscal_year_not_detected` and passed
  after the patch; `uv run pytest tests/unit/test_pdf_discovery.py -q` →
  `50 passed`; `uv run pytest tests/unit/test_discovery_evidence_summary.py
  tests/unit/test_school_fiscal_year_status.py -q` → `15 passed`;
  `uv run ruff check src/eidp/scraper/pdf_discovery.py
  tests/unit/test_pdf_discovery.py` → passed;
  `uv run pytest tests/unit -q` → `1035 passed, 5 warnings`.
- Saitama school `777` Goope replay at
  `_temp/saitama-goope-context-replay-20260511-080216` →
  `rejection_reason_fiscal_year_mismatch=7` and
  `rejection_reason_target_fiscal_year_not_detected=0`; the seven adjacent
  year target-form links are now `fiscal_year_mismatch:2019` through
  `fiscal_year_mismatch:2025`.
- `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v148.zip --playwright-addon dist/eidp-playwright-addon-windows-v106.zip --json` → `OK core`, `OK playwright-addon`, `git_commit=b06d3419b3a2bc3c9fcabcc845a433cb8759f861`, `git_dirty=false`, `entry_count=3016`, `wheel_count=78`, 47 prefecture seed rows/parser registrations/downloadable artifact URLs, `prefecture_seed_school_rows_total=2148`, core SHA256 `59047be094e649f4cb59f98d01f9167886b33783ff4970ea0af6aa59e8133f67`, add-on SHA256 `f6fe0cd095c337a81a870decb7a18e9d1f40044dd1567b017d92eda3aae1e8e8`.
- Focused v147 stale-anchor regression, Saitama replay, Ruff, and full unit
  suite after the Japanese-era stale-target hint patch →
  `uv run pytest tests/unit/test_pdf_discovery.py::test_download_pdf_rejects_stale_reiwa_year_from_anchor_when_body_has_no_year -q`
  failed before the patch with `target_fiscal_year_not_detected` and passed
  after the patch; `uv run pytest tests/unit/test_pdf_discovery.py -q` →
  `49 passed`; `uv run pytest tests/unit/test_pdf_discovery.py
  tests/unit/test_discovery_evidence_summary.py
  tests/unit/test_school_fiscal_year_status.py -q` → `64 passed`;
  `uv run ruff check src/eidp/scraper/pdf_discovery.py
  tests/unit/test_pdf_discovery.py` → passed;
  `uv run pytest tests/unit -q` → `1034 passed, 5 warnings`.
- Saitama school `773` replay at
  `_temp/saitama-stale-anchor-replay-20260511-075410` →
  `rejection_reason_fiscal_year_mismatch=6` and
  `rejection_reason_target_fiscal_year_not_detected=1`; the six old-year
  target-form anchors from `令和2年度確認申請書` through
  `令和7年度確認申請書` are now `fiscal_year_mismatch:2020` through
  `fiscal_year_mismatch:2025`.
- `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v147.zip --playwright-addon dist/eidp-playwright-addon-windows-v106.zip --json` → `OK core`, `OK playwright-addon`, `git_commit=b80bfcfc97a6163ccedde4d45c83099f89e59a3b`, `git_dirty=false`, `entry_count=3016`, `wheel_count=78`, 47 prefecture seed rows/parser registrations/downloadable artifact URLs, `prefecture_seed_school_rows_total=2148`, core SHA256 `bff5186fecc30d0c0ae64bcaa249ef6117d645331d5d36761dd2b3faab794828`, add-on SHA256 `f6fe0cd095c337a81a870decb7a18e9d1f40044dd1567b017d92eda3aae1e8e8`.
- Focused v146 ingest regression tests, Ruff, and full unit suite after the
  course-name normalization patch →
  `uv run pytest tests/unit/test_ingest_confidence_gating.py::test_pdf_course_name_specialized_suffix_matches_existing_field_department -q`
  → `1 passed`;
  `uv run pytest tests/unit/test_ingest_confidence_gating.py tests/unit/test_normal_ingest_appendonly.py tests/unit/test_manual_entry_contract.py -q`
  → `47 passed`; `uv run ruff check src/eidp/pipeline/ingest.py
  tests/unit/test_ingest_confidence_gating.py` → passed;
  `uv run pytest tests/unit -q` → `1033 passed, 5 warnings`.
- `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v146.zip --playwright-addon dist/eidp-playwright-addon-windows-v106.zip --json` → `OK core`, `OK playwright-addon`, `git_commit=e9143866ec6b1ad1018402b02e7dae7e7c4f8a7c`, `git_dirty=false`, `entry_count=3016`, `wheel_count=78`, 47 prefecture seed rows/parser registrations/downloadable artifact URLs, `prefecture_seed_school_rows_total=2148`, core SHA256 `ab683820e42ca44f91319bafef2a1c6454edfb6949aaba97b8ff3c3fd0f04978`, add-on SHA256 `f6fe0cd095c337a81a870decb7a18e9d1f40044dd1567b017d92eda3aae1e8e8`.
- Windows v146 clean extraction/setup smoke →
  SHA256 matched on Windows, `C:\EIDP-v146-e914386` extracted cleanly,
  `first_setup.bat` completed, validator reported `ok=true`,
  `errors=[]`, `warnings=[]`,
  `build_commit=e9143866ec6b1ad1018402b02e7dae7e7c4f8a7c`,
  `build_dirty=false`, `school_count=2418`,
  `school_fiscal_year_status_count=2418`, required tables present, and
  `wheel_count=78`.
- Windows v146 packaged school `95` target-PDF-to-Excel smoke →
  `discover-pdfs` downloaded the strict FY2026 target PDF;
  `ingest-pdfs --document-id 1` produced `departments_created=0` and
  `yearly_upserted=2`; `rebuild-school-year-tasks --fiscal-year 2026`
  rebuilt `2418` rows with `excel_ready=1`; DB verification showed
  `pdf_status=confirmed_target`, `DepartmentYearly` FY2026 rows `2`, and
  the exported workbook contained 2 `さいたまIT・WEB専門学校` rows in `学科別`
  and 2 in `在籍のみ抜粋`.
- `uv run mypy src/eidp/pipeline/ingest.py` was not a passing v146 gate:
  it still reports pre-existing annotation/type debt around the ingest stats
  dict and related call sites. This does not change the runtime/test evidence
  above, but it remains type-cleanup work.
- Windows v145 target-year-unverified status smoke →
  synthetic target-form/no-year evidence rebuilt school `1` into
  `(1, 'no_url', 'target_year_unverified', 'target_year_unverified',
  'target_year_unverified', 0)`, proving packaged DB status, evidence level,
  blocking reason, and non-Excel-ready behavior.
- `uv run pytest tests/unit/test_pdf_discovery.py::test_pre_download_detects_stale_year_prefix_serial_filename_for_target_form -q`
  failed before the v144 patch because `2025007.pdf` under a strong target-form
  anchor returned no pre-download rejection.
- Focused v144 pre-download tests, Ruff, mypy, `uv run pytest tests/unit/test_pdf_discovery.py -q`,
  and `uv run pytest tests/unit -q` after the serial-filename patch →
  `3 passed`, Ruff passed, mypy passed, `48 passed, 5 warnings`, and
  `1030 passed, 5 warnings`.
- `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v144.zip --playwright-addon dist/eidp-playwright-addon-windows-v106.zip` → `OK core`, `OK playwright-addon`, `git_commit=6ad13d36d27695af907ad06ed6951bb5fa0e6261`, `git_dirty=false`, `entry_count=3016`, `wheel_count=78`, 47 prefecture seed rows/parser registrations/downloadable artifact URLs, core SHA256 `4198cd6aca579196a3a5fb3fb1f55ec0a2df97a3a72b544f0d7195e4d45d9c68`, add-on SHA256 `f6fe0cd095c337a81a870decb7a18e9d1f40044dd1567b017d92eda3aae1e8e8`.
- Windows v144 clean extraction/setup smoke →
  SHA256 matched on Windows, `C:\EIDP-v144-6ad13d3` extracted cleanly,
  `first_setup.bat` completed, validator reported `OK install`,
  `build_commit=6ad13d36d27695af907ad06ed6951bb5fa0e6261`,
  `build_dirty=false`, `school_count=2418`,
  `school_fiscal_year_status_count=2418`, required tables present, and
  `wheel_count=78`.
- Windows v144 school-864 packaged regression →
  `2025007.pdf` under anchor `大学等における修学の支援に関する確認申請書`
  is now evidence row `reason=fiscal_year_mismatch:2025`,
  `pdf_type=target`, `extra.pre_download=true`; one-school summary was
  `crawled=1`, `found=1`, `downloaded=0`, `failed=0`, and
  `publication_lag_or_old_target_pdf=1`.
- `uv run ruff check src/eidp/scraper/pdf_discovery.py tests/unit/test_pdf_discovery.py`,
  `uv run mypy src/eidp/scraper/pdf_discovery.py`,
  `uv run pytest tests/unit/test_pdf_discovery.py -q`, and
  `uv run pytest tests/unit -q` after the v143 homepage-fallback and stale
  target-form classification changes → Ruff/mypy passed,
  `47 passed, 5 warnings`, and `1029 passed, 5 warnings`.
- `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v143.zip --playwright-addon dist/eidp-playwright-addon-windows-v106.zip` → `OK core`, `OK playwright-addon`, `git_commit=06926abc476616824919fe1e5ceba2374a621b98`, `git_dirty=false`, `entry_count=3016`, `wheel_count=78`, 47 prefecture seed rows/parser registrations/downloadable artifact URLs, core SHA256 `58183771364d50f319c7a72587e79aa79afa385d9181ce54490f378013472241`, add-on SHA256 `f6fe0cd095c337a81a870decb7a18e9d1f40044dd1567b017d92eda3aae1e8e8`.
- Windows v143 clean extraction/setup smoke →
  SHA256 matched on Windows, `C:\EIDP-v143-06926ab` extracted cleanly,
  `first_setup.bat` completed, validator reported `OK install`,
  `build_commit=06926abc476616824919fe1e5ceba2374a621b98`,
  `build_dirty=false`, `school_count=2418`,
  `school_fiscal_year_status_count=2418`, required tables present, and
  `wheel_count=78`.
- Windows v143 targeted `nag.ac.jp` stale-entry homepage-fallback rerun →
  after inserting the four official-index `SchoolSite` rows for school IDs
  `164,165,166,167`, packaged `discover-pdfs` logged
  `pdf_discovery_root_fallback` for all four stale `/evaluation/*.html` URLs
  and ended with `crawled=4`, `found=4`, `downloaded=0`, `failed=0`,
  `rejection_reason_fiscal_year_mismatch=15`,
  `rejection_reason_classified_non_target=7`,
  `rejection_reason_pre_filtered_non_target_hint=10`, and
  `rejection_reason_target_fiscal_year_not_detected=2`. The copied evidence
  summary reported `evidence rows=34`, `schools with evidence=4`, and
  `publication_lag_or_old_target_pdf=4`.
- Windows v143 bounded non-Sanko 45-school rerun →
  `crawled=45`, `found=41`, `downloaded=0`, `failed=7`,
  `rejection_reason_fiscal_year_mismatch=190`,
  `rejection_reason_discovery_error=4`, and evidence buckets
  `publication_lag_or_old_target_pdf=34`,
  `target_form_without_year_evidence=4`,
  `tls_certificate_verify_failed=4`, `non_target_candidates_only=3`.
  Diffing against the v141-resummarized v139 evidence showed 13 schools moved
  from generic site-fetch failure to publication-lag evidence.
- `uv run pytest tests/unit/test_discovery_evidence_summary.py tests/unit/test_school_fiscal_year_status.py tests/unit/test_review_school_year_tasks.py -q`
  after the TLS classification change → `69 passed`.
- `uv run pytest tests/unit -q` after the TLS classification change →
  `1026 passed`.
- `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v141.zip --playwright-addon dist/eidp-playwright-addon-windows-v106.zip` → `OK core`, `OK playwright-addon`, `git_commit=9abee545baf367db1866c24834526eb7b4a85aeb`, `git_dirty=false`, `entry_count=3016`, `wheel_count=78`, 47 prefecture seed rows/parser registrations/downloadable artifact URLs, core SHA256 `da9fef4e7c819c19753bde547466c06c9964714d7cf5c212190fefa3731bddee`, add-on SHA256 `f6fe0cd095c337a81a870decb7a18e9d1f40044dd1567b017d92eda3aae1e8e8`.
- Windows v141 clean extraction/setup/TLS-status smoke →
  SHA256 matched on Windows, `C:\EIDP-v141-9abee54` extracted cleanly,
  `first_setup.bat` completed, validator reported `OK install`,
  `build_commit=9abee545baf367db1866c24834526eb7b4a85aeb`,
  `school_count=2418`, `school_fiscal_year_status_count=2418`, required
  tables present, and a packaged synthetic TLS evidence rebuild produced
  `(1, 'pref_url', 'site_error', 'tls_certificate_verify_failed',
  'tls_certificate_verify_failed', 0)`.
- Windows v141 targeted `nag.ac.jp` stale-entry rerun →
  after inserting the four official-index `SchoolSite` rows for school IDs
  `164,165,166,167`, packaged `discover-pdfs` logged
  `pdf_discovery_root_fallback` for all four stale `/evaluation/*.html` URLs
  and ended with `crawled=4`, `found=0`, `downloaded=0`, `failed=0`, and
  `rejection_reason_no_candidates_found=4`.
- Re-summarizing the v139 bounded non-Sanko evidence after v141 code changes →
  `publication_lag_or_old_target_pdf=22`,
  `site_fetch_error_only=13`, `tls_certificate_verify_failed=4`,
  `target_form_without_year_evidence=4`, and `non_target_candidates_only=2`.
- `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v140.zip --playwright-addon dist/eidp-playwright-addon-windows-v106.zip` → `OK core`, `OK playwright-addon`, `git_commit=06c94d63d6b01fc54499793451d4b4a3d55fd5ed`, `git_dirty=false`, `entry_count=3016`, `wheel_count=78`, 47 prefecture seed rows/parser registrations/downloadable artifact URLs, core SHA256 `b8256b3e4e62741f98b36c339152a3b477d905426398d4603bc5e43bc5e8ddb6`, add-on SHA256 `f6fe0cd095c337a81a870decb7a18e9d1f40044dd1567b017d92eda3aae1e8e8`.
- Windows v140 clean extraction/setup/fallback smoke →
  SHA256 matched on Windows, `C:\EIDP-v140-06c94d6` extracted cleanly,
  `first_setup.bat` completed, validator reported `OK install`,
  `school_count=2418`, `school_fiscal_year_status_count=2418`, required
  tables present, and the packaged live probe of
  `https://www.all-japan.ac.jp/disclosure/` produced
  `pdf_discovery_root_fallback`, `error=None`, and `candidates=626`.
- Windows v140 targeted all-japan rerun →
  after Osaka/Aichi official-index bootstrap, the 9 affected all-japan school
  IDs crawled with `failed=0` and `downloaded=0`; evidence rows were
  `fiscal_year_mismatch:2025=90`, and the summary bucketed all 9 schools as
  `publication_lag_or_old_target_pdf` instead of `discovery_error`.
- `uv run pytest tests/unit` after the post-v138 publication-lag status/UI
  wiring → `1023 passed`.
- `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v139.zip --playwright-addon dist/eidp-playwright-addon-windows-v106.zip` → `OK core`, `OK playwright-addon`, `git_commit=2f5b8e46163b8dd50cc6a081ffaff5b408d604f4`, `git_dirty=false`, `entry_count=3016`, `wheel_count=78`, 47 prefecture seed rows/parser registrations/downloadable artifact URLs, core SHA256 `35a67aca553d279ce834da26cde970985623ba95d587d1be0fa27655be7c6534`, add-on SHA256 `f6fe0cd095c337a81a870decb7a18e9d1f40044dd1567b017d92eda3aae1e8e8`.
- Windows v139 clean extraction/setup/status/UI-server smoke →
  SHA256 matched on Windows, `C:\EIDP-v139-2f5b8e4` extracted cleanly,
  `first_setup.bat` completed, validator reported `errors=[]`, `warnings=[]`,
  `school_count=2418`, `school_fiscal_year_status_count=2418`, and required
  tables present. Packaged CLI publication-lag rebuild produced
  `(school_id=1, pdf_status=publication_lag, evidence_level=publication_lag,
  excel_ready=0, blocking_reason=publication_lag_latest_public)`, and the
  packaged Streamlit server returned HTTP `200` on `http://localhost:8501/`.
- Windows v139 Browser click-through smoke via SSH tunnel →
  settings page displayed `commit=2f5b8e4`; PDF confirmation, year correction,
  Excel preview, URL candidate review, and prefecture official-index pages
  rendered; `旧年度候補あり` filtered to one `公示待ち/再取得` task; Excel
  workbook generation remained disabled for zero target-FY rows.
- Windows v139 bounded non-Sanko official-index acquisition RCA →
  official-index bootstrap for Osaka/Fukuoka/Hokkaido/Aichi/Hyogo produced
  `prefecture_aggregator=321` runtime `SchoolSite` URLs, then a 45-school
  Hokkaido/Aichi/Osaka sample excluding the known repeated high-volume groups
  crawled `45` sites with `downloaded=0`. Evidence buckets were
  `publication_lag_or_old_target_pdf=22`, `site_fetch_error_only=17`,
  `target_form_without_year_evidence=4`, and `non_target_candidates_only=2`.
  Rebuilding FY2026 status from that evidence produced `publication_lag=22`
  and `no_target_pdf=23` within the sample.
- Post-RCA stale official-index URL fix →
  `uv run pytest tests/unit/test_pdf_discovery.py -q` passed `44` tests,
  `uv run ruff check src/eidp/scraper/pdf_discovery.py
  tests/unit/test_pdf_discovery.py` passed, `uv run mypy
  src/eidp/scraper/pdf_discovery.py` passed, and `uv run pytest tests/unit -q`
  passed `1024` tests. A live probe of
  `https://www.all-japan.ac.jp/disclosure/` confirmed same-origin root fallback
  and `626` discovered candidates.
- `uv run pytest tests/unit` after the v138 PDF discovery fixes →
  `1021 passed`.
- `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v138.zip --playwright-addon dist/eidp-playwright-addon-windows-v106.zip` → `OK core`, `OK playwright-addon`, `git_commit=5a4aeb825e516410875d31ddf1e4c4fddab448e0`, `git_dirty=false`, `entry_count=3016`, `wheel_count=78`, 47 prefecture seed rows/parser registrations/downloadable artifact URLs, add-on SHA256 `f6fe0cd095c337a81a870decb7a18e9d1f40044dd1567b017d92eda3aae1e8e8`.
- Windows v138 clean extraction/setup/add-on/browser smoke →
  `errors=[]`, `warnings=[]`, `school_count=2418`,
  `school_fiscal_year_status_count=2418`, required tables present,
  `scrapling_version=0.4.7`, and `playwright_title=eidp-ok`.
- Windows v138 three-pref official-index ingestion smoke →
  Tokyo `added=232`, Kanagawa `added=70`, Saitama `added=51`,
  seed URLs `50`, corporation-pattern URLs `498`.
- Windows v138 60-site strict FY2026 PDF discovery/ingest smoke →
  `crawled=60`, `found=55`, `downloaded=3`, `failed=6`,
  `prefiltered=216`, `fiscal_year_mismatch=149`,
  `classified_non_target=122`, `pre_filtered_non_target_hint=135`,
  `target_fiscal_year_not_detected=12`, then ingest `processed=3`,
  `yearly_upserted=4`, `skipped=2`, and task rebuild `excel_ready=1`.
- Windows v138 discovery-evidence RCA for the same 60-site scope →
  `accepted_target_pdf=3`, `publication_lag_or_old_target_pdf=44`,
  `target_form_without_year_evidence=5`, `site_fetch_error_only=3`,
  `non_target_candidates_only=3`, and `no_pdf_candidates=2`.
- Windows v136 Saitama 5-school URL crawl → `attempted=5`,
  `auto_registered=5`, `errors=0`, `unavailable=0`; database check found 5
  `school` URLs plus 10 `disclosure` URLs for the 5 sampled schools.
- Windows v136 strict FY2026 PDF discovery for the same 5-school sample →
  `downloaded=0`; rejection evidence was dominated by `classified_non_target=102`
  and stale-year buckets such as `fiscal_year_mismatch:2025=10`.
- Windows v136 FY2025 control run for the same 5-school sample → 4 target
  confirmation PDFs accepted into `document`, proving the acquisition chain works
  for the public latest year while strict FY2026 refuses stale success.
- Windows v136 Tokyo 10-school URL crawl →
  `attempted=10`, `auto_registered=9`, `review_enqueued=1`, `errors=0`.
  Auto results included 4 non-Sanko schools and 5 Sanko schools.
- Windows v136 strict FY2026 PDF discovery for the Tokyo auto set →
  `crawled=15`, `found=11`, `downloaded=0`, `failed=1`, `skipped=100`;
  evidence rows: `classified_non_target=48`, `pre_filtered_non_target_hint=29`,
  stale `fiscal_year_mismatch:*` rows = 20, and `no_candidates_found=4`.
- Windows v136 FY2025 control run for the Tokyo auto set →
  `downloaded=3`; DB rows were inserted for school IDs 17, 18, and 19 using
  Sanko `yoshiki2025.pdf` target confirmation forms.
- Windows v136 cross-prefecture 25-school URL crawl →
  `attempted=25`, `auto_registered=23`, `review_enqueued=2`, `errors=0`.
- Windows v136 strict FY2026 PDF discovery for those 23 auto schools →
  `crawled=40`, `found=34`, `downloaded=0`, `failed=2`, `skipped=332`;
  evidence rows: `classified_non_target=230`, `pre_filtered_non_target_hint=40`,
  stale `fiscal_year_mismatch:*` rows = 61, `target_fiscal_year_not_detected=9`,
  and `no_candidates_found=6`.
- Windows v136 FY2025 control run for the same cross-prefecture auto set →
  `downloaded=15`, all accepted target PDFs were Sanko latest-public FY2025
  forms.
- `uv run pytest -q` → `841 passed, 5 warnings`
- `uv run pytest tests/unit/test_pdf_discovery.py tests/unit/test_review_pdf_manual_entry.py -q` → `70 passed, 5 warnings`, including a Streamlit AppTest focused PDF確認 render smoke with discovery JSONL evidence
- `uv run ruff check tests/unit/test_review_pdf_manual_entry.py src/eidp/review/_pages/pdf_manual_entry.py src/eidp/scraper/pdf_discovery.py tests/unit/test_pdf_discovery.py` → passed
- `uv run mypy src/eidp/review/_pages/pdf_manual_entry.py src/eidp/scraper/pdf_discovery.py` → passed
- `uv run ruff check src/eidp/scraper/pdf_discovery.py src/eidp/review/_pages/pdf_manual_entry.py tests/unit/test_pdf_discovery.py tests/unit/test_review_pdf_manual_entry.py` → passed
- `uv run mypy src/eidp/scraper/pdf_discovery.py src/eidp/review/_pages/pdf_manual_entry.py` → passed
- `uv run pytest tests/unit/test_review_pdf_manual_entry.py -q` → `40 passed, 5 warnings`
- `uv run ruff check src/eidp/review/_pages/pdf_manual_entry.py tests/unit/test_review_pdf_manual_entry.py` → passed
- `uv run mypy src/eidp/review/_pages/pdf_manual_entry.py` → passed
- `uv run pytest tests/unit/test_review_school_year_tasks.py -q` → `48 passed`
- `uv run ruff check src/eidp/review/_pages/school_year_tasks.py tests/unit/test_review_school_year_tasks.py` → passed
- `uv run mypy src/eidp/review/_pages/school_year_tasks.py` → passed
- `uv run python scripts/build_windows_zip.py --skip-download --out-zip dist/eidp-windows-v102.zip --latest-alias` → wrote versioned ZIP, automatic checksum sidecar, and refreshed `dist/eidp-windows.zip`
- `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v102.zip` → `OK core`, `git_commit=3dc8aa98ba7e19b4813449858eb56ad25e4ea3c6`, `git_dirty=false`, `sha256=7ac5512fa81838289eb5e6e773f4ad30bedb1e166eb8f8f230f36ee15db294a5`, `entry_count=2994`, `wheel_count=82`, `prefecture_seed_rows=47`, `prefecture_seed_parser_supported=47`, `prefecture_seed_downloadable=47`
- `uv run python scripts/verify_windows_distribution.py dist/eidp-windows.zip` → `OK core`, `git_commit=3dc8aa98ba7e19b4813449858eb56ad25e4ea3c6`, `git_dirty=false`, `sha256=7ac5512fa81838289eb5e6e773f4ad30bedb1e166eb8f8f230f36ee15db294a5`, `entry_count=2994`, `wheel_count=82`, `prefecture_seed_rows=47`, `prefecture_seed_parser_supported=47`, `prefecture_seed_downloadable=47`
- Extracted v102 ZIP smoke (`_temp/v102-extract-H4hMSp`) using the packaged `scripts/validate_windows_install.py` → `OK install`, `build_commit=3dc8aa98ba7e19b4813449858eb56ad25e4ea3c6`, `build_branch=sprint8-handoff-finalize`, `build_dirty=false`, `master_xlsx_present=True`, `wheel_count=82`
- `uv run pytest tests/unit/test_pdf_discovery.py -q` → `30 passed, 5 warnings`
- `uv run ruff check src/eidp/scraper/pdf_discovery.py tests/unit/test_pdf_discovery.py src/eidp/review/operator_pages.py` → passed
- `uv run mypy src/eidp/scraper/pdf_discovery.py` → passed
- v95 strict real-site retest for Saitama `school_id=780` after image-only guard → `crawled=1`, `found=1`, `downloaded=0`, `skipped=9`; `2026syakai-isikai.pdf` rejected as `target_application_not_detected`
- Saitama 80-site diagnostic smoke before the v95 image-only guard (`_temp/bootstrap-mac-v94-saitama-OM2lEc`), scope `--pref saitama --url-search off --batch-size 80` → official index `extracted=58`, `matched=51`, `official_school_sites_added=51`, crawl `crawled=80`, `found=71`, `downloaded=1`, `failed=7`, `skipped=607`, `prefiltered=251`, `cached_rejections=114`, ingest `processed=1`, `yearly_upserted=0`; manual inspection showed the single download was `2026年度 社会人・医療機関推薦選抜募集要項`, not the target confirmation form.
- `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v95.zip` → `OK core`, `git_commit=2822c3cde62214b578b1c4d3093586be1667dfcc`, `git_dirty=false`, `sha256=2ad26209bf3ffccbf22855ca74d29e5bb60e18de3dbd0cc520118ffb1c653263`, `entry_count=2994`, `wheel_count=82`, `prefecture_seed_rows=47`, `prefecture_seed_parser_supported=47`, `prefecture_seed_downloadable=47`
- `uv run python scripts/verify_windows_distribution.py dist/eidp-windows.zip` → `OK core`, `git_commit=2822c3cde62214b578b1c4d3093586be1667dfcc`, `git_dirty=false`, `sha256=2ad26209bf3ffccbf22855ca74d29e5bb60e18de3dbd0cc520118ffb1c653263`, `entry_count=2994`, `wheel_count=82`, `prefecture_seed_rows=47`, `prefecture_seed_parser_supported=47`, `prefecture_seed_downloadable=47`
- Extracted v95 ZIP smoke (`_temp/v95-extract-hQKm0m`) using the packaged `scripts/validate_windows_install.py` → `OK install`, `build_commit=2822c3cde62214b578b1c4d3093586be1667dfcc`, `build_branch=sprint8-handoff-finalize`, `build_dirty=false`, `master_xlsx_present=True`, `wheel_count=82`
- `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v94.zip` → `OK core`, `git_commit=cb53ac502b81e1a23f262f25fa7126dc096e7366`, `git_dirty=false`, `sha256=66b42d015076a39b45f720d0484c89ef88aafb4bf7dd064029d67a378ddd031f`, `entry_count=2994`, `wheel_count=82`, `prefecture_seed_rows=47`, `prefecture_seed_parser_supported=47`, `prefecture_seed_downloadable=47`
- `uv run python scripts/verify_windows_distribution.py dist/eidp-windows.zip` → `OK core`, `git_commit=cb53ac502b81e1a23f262f25fa7126dc096e7366`, `git_dirty=false`, `sha256=66b42d015076a39b45f720d0484c89ef88aafb4bf7dd064029d67a378ddd031f`, `entry_count=2994`, `wheel_count=82`, `prefecture_seed_rows=47`, `prefecture_seed_parser_supported=47`, `prefecture_seed_downloadable=47`
- Extracted v94 ZIP smoke (`_temp/v94-extract-ZzPjsf`) using the packaged `scripts/validate_windows_install.py` → `OK install`, `build_commit=cb53ac502b81e1a23f262f25fa7126dc096e7366`, `build_branch=sprint8-handoff-finalize`, `build_dirty=false`, `master_xlsx_present=True`, `wheel_count=82`
- `uv run pytest tests/unit/test_bootstrap_pdf_pipeline.py tests/unit/test_review_school_year_tasks.py -q` → `69 passed`
- `uv run pytest tests/unit/test_windows_install_validator.py tests/unit/test_windows_distribution_verifier.py -q` → `56 passed`
- `uv run pytest tests/unit/test_review_school_year_tasks.py tests/unit/test_settings_page.py -q` → `52 passed`
- `uv run pytest tests/unit/test_review_school_year_tasks.py -q` → `47 passed`, including Streamlit AppTests proving the task-board package identity caption renders and the task-board settings shortcut opens the settings page
- `uv run ruff check src/eidp/review/_pages/school_year_tasks.py tests/unit/test_review_school_year_tasks.py` → passed
- `uv run mypy src/eidp/review/_pages/school_year_tasks.py` → passed
- `uv run pytest tests/unit/test_windows_install_validator.py tests/unit/test_windows_distribution_verifier.py -q` → `55 passed`
- `uv run ruff check scripts/validate_windows_install.py scripts/verify_windows_distribution.py tests/unit/test_windows_install_validator.py tests/unit/test_windows_distribution_verifier.py` → passed
- `uv run mypy scripts/validate_windows_install.py scripts/verify_windows_distribution.py` → passed
- `uv run pytest tests/unit/test_review_pdf_manual_entry.py tests/unit/test_review_pdf_manual_entry_confidence.py -q` → `47 passed, 5 warnings`
- `uv run mypy src/eidp/review/_pages/pdf_manual_entry.py` → passed
- `uv run pytest tests/unit/test_operator_pages.py tests/unit/test_review_school_year_tasks.py -q` → `62 passed`
- Chrome headless CDP smoke on isolated Streamlit app → HTTP `200`, home page rendered, `初回URL/PDF取得を開始` computed style changed from transparent to `rgb(0, 0, 0)` background / `rgb(255, 255, 255)` text, screenshot captured at `_temp/ui-smoke-20260507-120558/ui-smoke-home-rendered.png`
- `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v93.zip` → `OK core`, `git_commit=1029cc780d667cb0e02e66adf7abc51b5fefe235`, `git_dirty=false`, `sha256=357043f8288f8ed496c0fceac293e0c33848b889d870b42116e074a9b76584c0`, `entry_count=2994`, `wheel_count=82`, `prefecture_seed_rows=47`, `prefecture_seed_parser_supported=47`, `prefecture_seed_downloadable=47`
- `uv run python scripts/verify_windows_distribution.py dist/eidp-windows.zip` → `OK core`, `git_commit=1029cc780d667cb0e02e66adf7abc51b5fefe235`, `git_dirty=false`, `sha256=357043f8288f8ed496c0fceac293e0c33848b889d870b42116e074a9b76584c0`, `entry_count=2994`, `wheel_count=82`, `prefecture_seed_rows=47`, `prefecture_seed_parser_supported=47`, `prefecture_seed_downloadable=47`
- Extracted v93 ZIP smoke (`_temp/v93-extract-cdA9iZ`) using the packaged `scripts/validate_windows_install.py` → `OK install`, `build_commit=1029cc780d667cb0e02e66adf7abc51b5fefe235`, `build_branch=sprint8-handoff-finalize`, `build_dirty=false`, `master_xlsx_present=True`, `wheel_count=82`
- `uv run pytest tests/unit/test_settings_page.py -q` → `7 passed`
- `uv run pytest tests/unit/test_review_app.py tests/unit/test_review_school_year_tasks.py tests/unit/test_windows_packaging_spike.py tests/unit/test_windows_distribution_verifier.py -q` → `131 passed`
- `uv run pytest tests/unit/test_windows_packaging_spike.py tests/unit/test_windows_distribution_verifier.py tests/unit/test_windows_install_validator.py -q` → `106 passed`
- `uv run pytest tests/unit/test_windows_distribution_verifier.py -q` → `35 passed`
- `uv run ruff check src/eidp/review/_pages/settings_page.py tests/unit/test_settings_page.py src/eidp/review/operator_pages.py scripts/bootstrap_pdf_pipeline.py tests/unit/test_bootstrap_pdf_pipeline.py` → passed
- `uv run ruff check scripts/verify_windows_distribution.py tests/unit/test_windows_distribution_verifier.py` → passed
- `uv run mypy src/eidp/review/_pages/settings_page.py` → passed
- `uv run mypy scripts/verify_windows_distribution.py` → passed
- Streamlit AppTest with isolated SQLite smoke DB → home page zero exceptions; Settings page navigation zero exceptions; `設定を保存` button present
- `uv run python scripts/verify_windows_distribution.py dist/eidp-windows.zip --json` on v80 → `ok=true`, `git_commit=b3821f4e77c7207860ca6b6f2a67acb84b1c9c44`, `git_dirty=false`, `sha256=4d7b291b2b67fbcfd1e82643f995a6e2dcbe47e1206320d4ca888e1b3b24c253`, `prefecture_seed_rows=47`, `prefecture_seed_parser_supported=47`, `prefecture_seed_downloadable=47`, no warnings
- Latest bounded online bootstrap smoke (`_temp/bootstrap-mac-v92-saitama-uElU7k`), scope `--pref saitama --url-search off --batch-size 30` → `status=succeeded`, official Saitama index `extracted=58`, `matched=51`, `official_school_sites_added=51`, seed URLs `50`, crawl `crawled=30`, `found=25`, `downloaded=0`, `failed=3`, `skipped=226`, `prefiltered=116`, `cached_rejections=24`, ingest `processed=0`, status rows `rebuilt=2418`. Evidence reason counts: `target_fiscal_year_not_detected=86`, `pre_filtered_non_target_hint=44`, `fiscal_year_mismatch:2025=41`, `fiscal_year_mismatch:2024=21`, `classified_non_target=12`, plus smaller old-year buckets. Manual text spot-check confirmed `applicationform-r8.pdf` is student A様式1 and `R8_1A1_0420.pdf` is a syllabus, so these R8-named rejects are correct non-target decisions.
- Previous bounded online bootstrap smoke for the unchanged acquisition pipeline (`_temp/bootstrap-smoke-v88-SAF911`), scope `--pref tokyo,kanagawa,saitama --skip-known-url-discovery --url-search off --batch-size 3 --skip-ingest` → `status=succeeded`, artifacts downloaded `3/3`, official index rows `extracted=377`, `matched=354`, `official_school_sites_added=353`, DB `school_sites=353`, crawl `crawled=3`, `found=3`, `downloaded=0`, `failed=0`, `skipped=21`, `prefiltered=15`, `cached_rejections=2`, documents `0`, prefecture remark review items `2`
- Previous bounded online smoke rejection evidence for the unchanged acquisition pipeline → `fiscal_year_mismatch:2025=3`, `fiscal_year_mismatch:2024=2`, `fiscal_year_mismatch:2023=2`, `fiscal_year_mismatch:2022=2`, `fiscal_year_mismatch:2021=2`, `fiscal_year_mismatch:2020=2`, `fiscal_year_mismatch:2019=1`, `target_fiscal_year_not_detected=3`, `pre_filtered_non_target_hint=1`; this proves old-year candidates are rejected, not counted as target-year success, on the sampled live sites.
- `uv run ruff check src/eidp/scraper/pdf_discovery.py tests/unit/test_pdf_discovery.py` → passed
- `uv run mypy src/eidp/scraper/pdf_discovery.py` → passed
- `uv run pytest tests/unit/test_pdf_discovery.py -q` → `24 passed, 5 warnings`
- `uv run ruff check scripts/bootstrap_pdf_pipeline.py src/eidp/review/_pages/school_year_tasks.py tests/unit/test_bootstrap_pdf_pipeline.py tests/unit/test_review_school_year_tasks.py` → passed
- `uv run mypy scripts/bootstrap_pdf_pipeline.py src/eidp/review/_pages/school_year_tasks.py` → passed
- `uv run pytest tests/unit/test_bootstrap_pdf_pipeline.py tests/unit/test_review_school_year_tasks.py -q` → `59 passed`
- `uv run pytest tests/unit/test_windows_distribution_verifier.py -q` → `34 passed`
- `uv run ruff check scripts/verify_windows_distribution.py tests/unit/test_windows_distribution_verifier.py` → passed
- `uv run mypy scripts/verify_windows_distribution.py` → passed
- `uv run python scripts/verify_windows_distribution.py dist/eidp-windows.zip --json` → `ok=true`, `prefecture_seed_rows=47`, `prefecture_seed_parser_supported=47`, `prefecture_seed_downloadable=47`, no warnings
- `uv run pytest tests/unit/test_review_prefecture_remarks.py tests/unit/test_review_school_year_tasks.py -q` → `34 passed`
- `uv run ruff check src/eidp/review/_pages/prefecture_remarks.py tests/unit/test_review_prefecture_remarks.py src/eidp/review/_pages/school_year_tasks.py tests/unit/test_review_school_year_tasks.py` → passed
- `uv run mypy src/eidp/review/_pages/prefecture_remarks.py src/eidp/review/_pages/school_year_tasks.py` → passed
- `uv run pytest tests/unit/test_competition_exporter.py -q` → `11 passed`
- `uv run mypy src/eidp/excel/competition_exporter.py` → passed
- `uv run pytest tests/unit/test_review_school_year_tasks.py tests/unit/test_operator_pages.py -q` → `54 passed`
- `uv run mypy src/eidp/review/_pages/school_year_tasks.py` → passed
- `uv run pytest tests/unit/test_review_pdf_manual_entry.py tests/unit/test_review_pdf_manual_entry_confidence.py -q` → `44 passed, 5 warnings`
- `uv run mypy src/eidp/review/_pages/pdf_manual_entry.py` → passed
- Windows remote ZIP smoke on v73 → SHA256 `fee2aa1b810acbdeb080fc0452174339b4559f3a6347f23cea04c6e79df5a448`, `settings_page.py` present, decoded wrapper-URL hint filtering present, strong fiscal-year hint filter present, `entry_count=2992`, `BuildCommit=02ab507a347f9540e10d0d206c52f3d7b52751a0`
- Windows remote setup smoke on v73 clean extraction → `setup_exit=0`, validator reported `OK install`, `school_count: 2418`, `school_fiscal_year_status_count: 2418`, `wheel_count: 82`
- Windows remote bounded Step 3 smoke on v73 clean install → `status=succeeded`, 47 official indexes parsed, `official_index_rows_extracted=1948`, `official_index_rows_matched=1770`, `official_school_sites_added=1306`, 25 school sites crawled, `downloaded=0`, `failed=1`, `skipped=160`, `cached_rejections=46`, `prefiltered=87`
- Windows v72-to-v73 rejection evidence comparison on the same 25-site smoke scope → total rejection rows stayed `183`, `http_error` fell `10 -> 5`, `pre_filtered_non_target_hint` rose `41 -> 55`, and `target_fiscal_year_not_detected` fell `78 -> 70`
- Windows remote ZIP smoke on v72 → SHA256 `63dfac3aef2759387986c92619f9b810ac06c5c91ee96dd0ff7994e7770b1b8a`, `settings_page.py` present, `pre_filtered_non_target_hint` code present, strong fiscal-year hint filter present, `launch.bat` has no stale `"RC=-1"` token, `entry_count=2992`, `BuildCommit=edd0a4514297ded842bd6bc68df50acb8ee973b9`
- Windows remote setup smoke on v72 clean extraction → `setup_exit=0`, validator reported `OK install`, `school_count: 2418`, `school_fiscal_year_status_count: 2418`, `wheel_count: 82`
- Windows remote bounded Step 3 smoke on v72 clean install → `status=succeeded`, 47 official indexes parsed, `official_index_rows_extracted=1948`, `official_index_rows_matched=1770`, `official_school_sites_added=1306`, 25 school sites crawled, `downloaded=0`, `failed=1`, `skipped=155`, `cached_rejections=46`, `prefiltered=74`
- Windows remote ZIP smoke on v71 → SHA256 `b9f154ea80c96252947b8bcd9955122ee304c3726c5ae3b74e32c26c85f5a5d9`, `settings_page.py` present, `pre_filtered_non_target_hint` code present, `launch.bat` has no stale `"RC=-1"` token, `entry_count=2992`, `BuildCommit=69fcdb87c0fdee1643cdf22eece773a302f231a8`
- Windows remote setup smoke on v71 clean extraction → `setup_exit=0`, validator reported `OK install`, `school_count: 2418`, `school_fiscal_year_status_count: 2418`, `wheel_count: 82`
- Windows remote bounded Step 3 smoke on v71 clean install → `status=succeeded`, 47 official indexes parsed, `official_index_rows_extracted=1948`, `official_index_rows_matched=1770`, `official_school_sites_added=1306`, 25 school sites crawled, `downloaded=0`, `failed=1`, `skipped=133`, `cached_rejections=46`, `prefiltered=41`
- Windows remote ZIP smoke on v70 → SHA256 `0b1a219e9c86148b5942da85944a49345c43ce0df59a0df16caf58681b6ac6a7`, `settings_page.py` present, `launch.bat` present, `cached_rejections` code present, `MAX_DISCOVERY_EXTRA_PAGES` fanout bound present, `BuildCommit=c671ea3de404815251924977f24791665d4a236d`
- Windows remote setup smoke on v70 clean extraction → `setup_exit=0`, validator reported `OK install`, `school_count: 2418`, `school_fiscal_year_status_count: 2418`, `wheel_count: 82`
- Windows remote setup smoke on v69 clean extraction → `setup_exit=0`, validator reported `OK install`, `school_count: 2418`, `school_fiscal_year_status_count: 2418`, `wheel_count: 82`
- Windows remote bounded Step 3 cache smoke on v69 clean install → stopped after cache behavior proof, progress reached `crawled=9`, `skipped=40`, `cached_rejections=16`; this confirms repeated old/non-target corporation PDFs are no longer downloaded/classified once per school.
- Windows remote setup smoke on v67 code path → `SETUP_EXIT=0`, `IMPORT_OK`, SQLite DB present, `SCHOOL_COUNT=2418`, `TASK_COUNT=2418`
- Windows remote official-index yield smoke on v67 smoke install → `BOOTSTRAP_SKIP_DISCOVER_EXIT=0`, 47 official indexes parsed, `official_index_rows_extracted=1948`, `official_index_rows_matched=1770`, `official_school_sites_added=1306`, `SCHOOL_SITE_TOTAL=1649`, `SCHOOL_SITE_BY_METHOD=[('corporation_pattern', 295), ('prefecture_aggregator', 1306), ('seed_csv', 48)]`

## Missing Before Goal Can Be Marked Complete

1. Decide and validate the target-year acceptance policy.
   v137/v136 prove the URL crawl and PDF chain can acquire published FY2025 target
   confirmation PDFs on the sampled Saitama schools, while strict FY2026 mode
   correctly rejects those stale FY2025 forms. v138 extends this with a 60-site
   Windows RCA where 44/60 schools fall into
   `publication_lag_or_old_target_pdf`. The goal cannot be marked complete until
   either FY2026/R8 forms are publicly available at sufficient yield, or the
   product explicitly accepts a publication-lag policy that records latest-public
   FY2025 forms separately from true target-FY success. v139 implements and
   packages that separate reviewable status, but it does not by itself satisfy
   the strict target-FY yield gate.
2. Validate a broader Windows bootstrap yield beyond bounded samples.
   v138 includes a 60-site Windows PDF crawl/ingest smoke, v137 includes a
   targeted 51-site Saitama official-index RCA, and v139 adds a separate
   45-school Hokkaido/Aichi/Osaka non-Sanko official-index RCA. These show
   official-index URL ingestion works, but strict FY2026 target-PDF acquisition
   remains far below the 60-70% automation gate. The next proof needs either a
   broader Windows initial acquisition run or a product decision that treats
   latest-public FY2025 publication-lag forms as a separate reviewable state
   rather than target-FY success.
3. Run the latest Windows UI flow against a real downloaded target-FY
   acquisition result. v139 has a browser click-through for read-only
   navigation and the publication-lag lane. Still missing: clicking the initial
   bootstrap button, weekly rediscovery button, PDF review drill-down with real
   downloaded target PDFs, and Excel preview after target-FY rows exist.
4. Keep R-0 naming debt controlled: compatibility wrappers and historical
   reports may keep R8 wording, but new production entrypoints must use
   target-year naming.
5. Decide university scope: keep as gated pilot for v1.1, or start the v1.2
   parser/discovery track.
6. Validate the UI with real operator feedback; current tests prove wiring and
   business rules, not usability under real workload.

## Current Conclusion

The project is materially closer to the intended automation architecture:
official government indexes are now the primary acquisition surface, stale PDFs
are demoted, target-FY tasking is visible, and Windows packaging is refreshed.

The active goal is **not complete**. v249 is the latest Mac-verifier-clean
Windows ZIP candidate, but its Windows E2E remains pending. v245 is the latest
fresh Windows setup-verified package, and v244 remains the latest package with
a focused Windows replay proof. The latest full bounded Windows acquisition
RCA is now v244 and still proves strict FY2026 yield far below the ship gate:
the v244 Saitama official-index run covered `51` official-index school URLs,
found PDF candidates on `50` sites, downloaded `11` PDFs, and counted `7`
schools as current target-PDF auto acquired after ingest/status rebuild, but
gold-set evaluation exposed false positives in the discovery/status count.
Those false positives are fixed in v245/v246/v247/v248/v249 and covered by Mac-side tests, but
they require a new Windows replay before they can be counted as packaged
runtime evidence. v240 and v241
reduced download-time non-target waste (`classified_non_target` fell from v239
`230` to v240 `169` and then v241 `125`, and
`target_fiscal_year_not_detected` fell from `51` to `27` and then `21`) but
did not change the final current-year document count or ship-gate status. v241
also proved that pre-filter gains can expose much deeper same-site non-target
queues: evidence rows expanded to `5580`, skipped candidates to `5418`, and
prefiltered rows to `2550`, dominated by site-family disclosure-PDF families
rather than generic missing negative tokens. v230
pre-filters the earlier school `72` `職業実践専門課程等の基本情報` false positive
as `non_target` in a targeted Windows replay. v231 also prevents school `793`
stale `2025年度` full-form links from inheriting a preceding `2026年度` syllabus
context. v232 additionally
keeps schools `761` and `763` review-bound by preventing support-only
image PDFs from being mislabeled as old target publication-lag evidence or
pre-filtered due to sibling-link text. The v228 school `95` false positive is
also rejected because its only 2026 body evidence was `完成年度`. v233 restores
`no_target_candidate_found` coverage in the packaged discovery gold set after
the 入間看護 entry was reclassified to publication-lag. v234 keeps JS-rendered
fallback active when static HTML only exposes current-year non-target PDFs.
v235 prevents those pre-filtered adjacent PDFs from exhausting the bounded
download-attempt budget before lower-ranked target forms are tried.
v236 additionally pre-filters English `subject_*.pdf` / `subject-*.pdf`
syllabus/course-list PDFs; a targeted Windows replay on schools `291` and `486`
proved that the v235 overlapping subject set moved from `30` download-time
`classified_non_target` rows to pre-download rejection without creating any new
`Document` rows.
v237 closes the remaining subject anchor-contamination edge: the same targeted
Windows replay now shows `124/124` subject rows as pre-download
`pre_filtered_non_target_hint/non_target`, with no `Document` rows for schools
`291` or `486`.
v238/v239 additionally move the all-japan department-info and governance
families (`info_`, `grade_manage`, `goal_policies`, `regulation`, `donation`,
`remuneration`) to pre-download rejection; the latest targeted Windows replay
has `classified_non_target=0` on schools `291` and `486`.
v240 extends the same evidence-backed pre-download policy to financial
statements, education/course, objective-indicator, plan/policy, and student
form families exposed by the full Saitama replay, but the residual failures
concentrate in site-family patterns such as O-Hara numbered disclosure PDFs
and Sanko/Arsnet course/hash documents. v241 adds guarded site-family
pre-download rejection for the first observed O-Hara/Sanko/Kanto/Honda/Arsnet
families, but the unchanged `3/2418` auto-acquired count means the next
meaningful lever is candidate prioritization/derivation from known site
families rather than more broad rejection terms. v242 implements that candidate
prioritization/budget lever: full Saitama evidence rows fell from v241 `5580`
to `1324`, skipped candidates from `5418` to `1166`, cached rejections from
`2813` to `224`, and pre-filtered rows from `2550` to `886`, with
`candidate_budget_limited=8` and `candidate_budget_dropped=6487`; the accepted
current-year count still stayed `3/2418`, so v242 is a runtime/noise
improvement rather than a yield improvement.
v243 packages and Windows-validates the next manual-success-to-agent pattern:
use the same-column `確認申請書` table header and the nearest school section
heading before ranking O-Hara group candidates. A focused Windows v243 replay
for school `212` produced `crawled=1`, `found=1`, `downloaded=0`,
`skipped=198`, `prefiltered=187`, `candidate_budget_limited=1`, and
`candidate_budget_dropped=1640`; the new gold-set entry exactly predicts
`https://www.o-hara.ac.jp/about/joho/pdf/2025-1-37-01-5.pdf` as
`publication_lag_latest_public` for FY2026. This fixes the
`non_target_candidates_only` RCA bucket for that O-Hara school-family case but
does not raise strict FY2026 yield because the visible form is still FY2025.
v244 adds one strict-yield recovery: school `769`
now accepts the target `申請書_0602_資料A.pdf` because a bare WordPress
`/uploads/2025/06/` path is treated as an upload/calendar date, not an
explicit stale fiscal-year label, when the PDF body is target and the
prefecture official index supplies `prefecture_index_current_year`. Explicit
stale labels such as `2025年度` and `令和7年度` still reject. The focused replay
downloaded and ingested the document, wrote `yearly_upserted=1`, and raised the
copied Saitama DB status to `excel_ready=4`; the fresh Windows v244 package
replay also validated `downloaded=1`, `processed=1`, `yearly_upserted=1`, and
gold-set `exact_matches=1` for this new entry.
The full v244 Saitama replay then proved the next correction direction:
official-index current-year trust was too strong when the candidate itself had
explicit stale-year labels (`R6年度分申請`, `令和七年度`) or was an adjacent
student tuition-reduction form. v245/v246/v247/v248/v249 correct those false-positive classes
and expand the discovery gold-set to `20` entries, including the new
`ogose-auto-publication-lag-2026` fixture. v246 further adds a
rolling-target-year matrix across FY2026-FY2028, so the guard is a persistent
fiscal-year rule rather than a one-year FY2026 patch. v247 additionally removes
low-value English renewal-form hints and adds operator-facing import/runbook
hardening. v248 additionally prevents ordinary publication dates from being
misread as stale fiscal-year labels, and v249 prevents those dates from
inflating candidate priority. These fixes are Mac-tested and
package-verifier-clean, but Windows focused/full replay remains the next
required evidence step.
The deployment layer is
healthy
(`first_setup.bat`, SQLite integrity/schema checks, bootstrap wrapper
log/progress capture, non-release validator, and `diagnose.bat` all pass), but
the product gate correctly fails with `ship_gate_status=below_gate` and
`target_pdf_auto_yield_pct=0.1`.

v140-v154 closed the earlier fetch/navigation, stale-year, year-evidence, and
school `757` extraction issues. v150 proved school `95` target PDF discovery,
ingest, status rebuild, and Excel export on Windows. v152-v154 moved school
`757` through trusted official-index year evidence, extraction confidence
`0.94`, status rebuild, and Excel export. v224 added one real false-negative
closure from the current Saitama evidence: school `784`
`更新確認申請書` now downloads and ingests via
`year_evidence=prefecture_index_current_year`, but v229 then removed the
school `95` false-positive caused by treating a program completion year as
target-FY evidence. v226-v228 improved RCA quality for remaining misses by
turning WordPress Download Manager, non-HTML registered-page, and dense
corporation root cases into explicit old-year fiscal mismatch evidence instead
of `no_candidates_found` or corporation-level non-target buckets.

The remaining blockers are target-year yield/policy, broader discovery RCA for
the dominant rejection buckets (`fiscal_year_mismatch:*`,
`classified_non_target`, and `pre_filtered_non_target_hint`), extraction/OCR
quality on any newly accepted PDFs, real operator UI validation, and the
explicit university rollout decision. Current evidence does not justify broad
token loosening: sampled current-looking rejects such as `applicationform-r8.pdf`
are student A-forms, and sampled `academic_support.pdf` begins with disclosure
sub-forms rather than a current target-year confirmation main form.
