# Owner False-Reject Review Worklist

Archive: `logs/win-v547-86c848f-canary/stage6-evidence-20260621-054545.zip`
Release Forecast: `NOT_READY`
Strict Excel-ready yield: `12/50` (`24.0%`), required `60.0%`.
Rows requiring owner worksheet decision: `53`

This worklist is read-only. It organizes the CSV worksheet; it does not fill decisions, approve rejected rows, or allow any row into Excel.

## How To Use

- Start with `needs_operator_review` rows; they are the highest-risk rows for false rejects.
- Confirm `correct_reject` rows only after checking the official page/PDF evidence.
- Fill only `decision`, `reviewer`, `reviewed_at`, and `notes` in the CSV worksheet.
- Notes are required for `false_reject` and `needs_operator_review` decisions.
- Keep old-year, unknown-year, non-target, school-mismatch, and low-confidence rows out of Excel.

## Suggested Decision Counts

| Suggested decision | Rows |
| --- | ---: |
| `needs_operator_review` | 29 |
| `correct_reject` | 24 |

## 1. Inspect official evidence before deciding (`29` rows)

### `classified_non_target` (`8` rows)

Review question: Did the classifier mark any target application form as non-target?
False-reject signal: PDF is a target application form despite the non-target classification.

#### `3a0f8397307c16d4` / school `11`

- Reason: `classified_non_target`
- PDF type: `non_target`
- Detected fiscal year: ``
- Discovery method: `school_domain_override`
- Anchor: ``
- Suggested basis: Non-target rejection is not obviously safe from anchor/URL evidence; operator must inspect the official PDF/page before confirming correct_reject or false_reject.
- Page URL: <https://www.nkz.ac.jp/clginfo/oi/oiC-d_nursingpublichealth_13.html>
- PDF URL: <https://www.nkz.ac.jp/clginfo/oi/pdf/oiC-d_nursingpublichealth_13.pdf>

#### `9e251721aa515c6b` / school `13`

- Reason: `classified_non_target`
- PDF type: `non_target`
- Detected fiscal year: ``
- Discovery method: `school_domain_override`
- Anchor: 1年
- Suggested basis: Non-target rejection is not obviously safe from anchor/URL evidence; operator must inspect the official PDF/page before confirming correct_reject or false_reject.
- Page URL: <https://www.sanko.ac.jp/disclosure/sapporo-med/>
- PDF URL: <https://www.sanko.ac.jp/disclosure/sapporo-med/care_01.pdf>

#### `f36afe0d6149df33` / school `16`

- Reason: `classified_non_target`
- PDF type: `non_target`
- Detected fiscal year: ``
- Discovery method: `school_domain_override`
- Anchor: 1年
- Suggested basis: Non-target rejection is not obviously safe from anchor/URL evidence; operator must inspect the official PDF/page before confirming correct_reject or false_reject.
- Page URL: <https://www.sanko.ac.jp/disclosure/chiba-med/>
- PDF URL: <https://www.sanko.ac.jp/disclosure/chiba-med/bd5084288531bf11ed0bde63319cabe61e4d609d.pdf>

#### `e06645c66c9ec7fa` / school `17`

- Reason: `classified_non_target`
- PDF type: `non_target`
- Detected fiscal year: ``
- Discovery method: `school_domain_override`
- Anchor: 3年
- Suggested basis: Non-target rejection is not obviously safe from anchor/URL evidence; operator must inspect the official PDF/page before confirming correct_reject or false_reject.
- Page URL: <https://www.sanko.ac.jp/disclosure/tokyo-fukushi/>
- PDF URL: <https://www.sanko.ac.jp/disclosure/tokyo-fukushi/childhood_studies_03.pdf>

#### `b9cf312d643233eb` / school `18`

- Reason: `classified_non_target`
- PDF type: `non_target`
- Detected fiscal year: ``
- Discovery method: `school_domain_override`
- Anchor: 1年
- Suggested basis: Non-target rejection is not obviously safe from anchor/URL evidence; operator must inspect the official PDF/page before confirming correct_reject or false_reject.
- Page URL: <https://www.sanko.ac.jp/disclosure/tokyo-med/>
- PDF URL: <https://www.sanko.ac.jp/disclosure/tokyo-med/8ce42f9cadd6b0cbc1c4155e0b9bf3b38678ddaf.pdf>

#### `f6127fb4fac870ec` / school `20`

- Reason: `classified_non_target`
- PDF type: `non_target`
- Detected fiscal year: ``
- Discovery method: `school_domain_override`
- Anchor: 1年
- Suggested basis: Non-target rejection is not obviously safe from anchor/URL evidence; operator must inspect the official PDF/page before confirming correct_reject or false_reject.
- Page URL: <https://www.sanko.ac.jp/disclosure/yokohama-med/>
- PDF URL: <https://www.sanko.ac.jp/disclosure/yokohama-med/drug_01.pdf>

#### `4dc3324e137772b2` / school `21`

- Reason: `classified_non_target`
- PDF type: `non_target`
- Detected fiscal year: ``
- Discovery method: `school_domain_override`
- Anchor: 1年
- Suggested basis: Non-target rejection is not obviously safe from anchor/URL evidence; operator must inspect the official PDF/page before confirming correct_reject or false_reject.
- Page URL: <https://www.sanko.ac.jp/disclosure/nagoya-med/>
- PDF URL: <https://www.sanko.ac.jp/disclosure/nagoya-med/care_01.pdf>

#### `52ea4a2b283e7bef` / school `27`

- Reason: `classified_non_target`
- PDF type: `non_target`
- Detected fiscal year: ``
- Discovery method: `school_domain_override`
- Anchor: AIプログラミング＆CGクリエイター科-1年
- Suggested basis: Non-target rejection is not obviously safe from anchor/URL evidence; operator must inspect the official PDF/page before confirming correct_reject or false_reject.
- Page URL: <https://www.sanko.ac.jp/tokyo-ai/information/>
- PDF URL: <https://www.sanko.ac.jp/tokyo-ai/information/1ebc0c36a3362449ae3068e9e8eee80c468d479c.pdf>

### `pre_filtered_non_target_hint` (`6` rows)

Review question: Did pre-download filtering reject any real target application form?
False-reject signal: Anchor/page/PDF title is a target application form, not GPA/syllabus/admission/evaluation material.

#### `86200c2ac49b387a` / school `13`

- Reason: `pre_filtered_non_target_hint`
- PDF type: `non_target`
- Detected fiscal year: ``
- Discovery method: `school_domain_override`
- Anchor: 1年
- Suggested basis: Non-target rejection is not obviously safe from anchor/URL evidence; operator must inspect the official PDF/page before confirming correct_reject or false_reject.
- Page URL: <https://www.sanko.ac.jp/disclosure/sapporo-med/>
- PDF URL: <https://www.sanko.ac.jp/disclosure/sapporo-med/healthinfo_01.pdf>

#### `92587dfd41a0493f` / school `14`

- Reason: `pre_filtered_non_target_hint`
- PDF type: `non_target`
- Detected fiscal year: ``
- Discovery method: `school_domain_override`
- Anchor: 1年
- Suggested basis: Non-target rejection is not obviously safe from anchor/URL evidence; operator must inspect the official PDF/page before confirming correct_reject or false_reject.
- Page URL: <https://www.sanko.ac.jp/disclosure/sendai-med/>
- PDF URL: <https://www.sanko.ac.jp/disclosure/sendai-med/docs/care_01.pdf>

#### `faeea51e26705740` / school `16`

- Reason: `pre_filtered_non_target_hint`
- PDF type: `non_target`
- Detected fiscal year: ``
- Discovery method: `school_domain_override`
- Anchor: 1年
- Suggested basis: Non-target rejection is not obviously safe from anchor/URL evidence; operator must inspect the official PDF/page before confirming correct_reject or false_reject.
- Page URL: <https://www.sanko.ac.jp/disclosure/chiba-med/>
- PDF URL: <https://www.sanko.ac.jp/disclosure/chiba-med/docs/13e9921e812dd992dda6fe58de136c3be802eaff.pdf>

#### `b7fab3b4be5d26ca` / school `17`

- Reason: `pre_filtered_non_target_hint`
- PDF type: `non_target`
- Detected fiscal year: ``
- Discovery method: `school_domain_override`
- Anchor: 1年
- Suggested basis: Non-target rejection is not obviously safe from anchor/URL evidence; operator must inspect the official PDF/page before confirming correct_reject or false_reject.
- Page URL: <https://www.sanko.ac.jp/disclosure/tokyo-fukushi/>
- PDF URL: <https://www.sanko.ac.jp/disclosure/tokyo-fukushi/docs/08d452f4472b178f0fddc91b9a41eb9fe7505429.pdf>

#### `48c7bea6d0b411c5` / school `19`

- Reason: `pre_filtered_non_target_hint`
- PDF type: `non_target`
- Detected fiscal year: ``
- Discovery method: `school_domain_override`
- Anchor: 学校情報
- Suggested basis: Non-target rejection is not obviously safe from anchor/URL evidence; operator must inspect the official PDF/page before confirming correct_reject or false_reject.
- Page URL: <https://www.sanko.ac.jp/disclosure/tachikawa-child/>
- PDF URL: <https://www.sanko.ac.jp/disclosure/tachikawa-child/docs/08d3435687b7165d8b22b0f0e677696975b8ac6e.pdf>

#### `d1dd4a4bfcb73eec` / school `21`

- Reason: `pre_filtered_non_target_hint`
- PDF type: `non_target`
- Detected fiscal year: ``
- Discovery method: `school_domain_override`
- Anchor: 1年
- Suggested basis: Non-target rejection is not obviously safe from anchor/URL evidence; operator must inspect the official PDF/page before confirming correct_reject or false_reject.
- Page URL: <https://www.sanko.ac.jp/disclosure/nagoya-med/>
- PDF URL: <https://www.sanko.ac.jp/disclosure/nagoya-med/docs/childcare_01.pdf>

### `site_entry_fetch_identity` (`11` rows)

Review question: Is this a SiteEntry, fetch, or school-identity gap rather than a missing-publication case?
False-reject signal: The official source points to a valid FY2026/R8 target document for the same school.

#### `cff41b0714a9200e` / school `4`

- Reason: `no_candidates_found`
- PDF type: ``
- Detected fiscal year: ``
- Discovery method: ``
- Anchor: ``
- Suggested basis: No valid candidate was found or fetch failed; inspect the official SiteEntry/disclosure page.
- Page URL: <https://www.mode.ac.jp/tokyo>
- PDF URL: <https://www.mode.ac.jp/tokyo>

#### `bb4da083a3ef33f6` / school `5`

- Reason: `no_candidates_found`
- PDF type: ``
- Detected fiscal year: ``
- Discovery method: ``
- Anchor: ``
- Suggested basis: No valid candidate was found or fetch failed; inspect the official SiteEntry/disclosure page.
- Page URL: <https://www.mode.ac.jp/osaka>
- PDF URL: <https://www.mode.ac.jp/osaka>

#### `b44dd14a9cc4f4ea` / school `6`

- Reason: `no_candidates_found`
- PDF type: ``
- Detected fiscal year: ``
- Discovery method: ``
- Anchor: ``
- Suggested basis: No valid candidate was found or fetch failed; inspect the official SiteEntry/disclosure page.
- Page URL: <https://www.mode.ac.jp/nagoya>
- PDF URL: <https://www.mode.ac.jp/nagoya>

#### `5cd47a3627fcae17` / school `7`

- Reason: `no_candidates_found`
- PDF type: ``
- Detected fiscal year: ``
- Discovery method: ``
- Anchor: ``
- Suggested basis: No valid candidate was found or fetch failed; inspect the official SiteEntry/disclosure page.
- Page URL: <https://www.hal.ac.jp/tokyo>
- PDF URL: <https://www.hal.ac.jp/tokyo>

#### `3866fd28354a97e1` / school `8`

- Reason: `no_candidates_found`
- PDF type: ``
- Detected fiscal year: ``
- Discovery method: ``
- Anchor: ``
- Suggested basis: No valid candidate was found or fetch failed; inspect the official SiteEntry/disclosure page.
- Page URL: <https://www.hal.ac.jp/osaka>
- PDF URL: <https://www.hal.ac.jp/osaka>

#### `0d0bc1d1fdce2dd1` / school `9`

- Reason: `no_candidates_found`
- PDF type: ``
- Detected fiscal year: ``
- Discovery method: ``
- Anchor: ``
- Suggested basis: No valid candidate was found or fetch failed; inspect the official SiteEntry/disclosure page.
- Page URL: <https://www.hal.ac.jp/nagoya>
- PDF URL: <https://www.hal.ac.jp/nagoya>

#### `f5d47fcd2d8aca3e` / school `10`

- Reason: `no_candidates_found`
- PDF type: ``
- Detected fiscal year: ``
- Discovery method: ``
- Anchor: ``
- Suggested basis: No valid candidate was found or fetch failed; inspect the official SiteEntry/disclosure page.
- Page URL: <https://www.iko.ac.jp/tokyo>
- PDF URL: <https://www.iko.ac.jp/tokyo>

#### `ca15518d6c5a6647` / school `11`

- Reason: `no_candidates_found`
- PDF type: ``
- Detected fiscal year: ``
- Discovery method: ``
- Anchor: ``
- Suggested basis: No valid candidate was found or fetch failed; inspect the official SiteEntry/disclosure page.
- Page URL: <https://www.iko.ac.jp/osaka>
- PDF URL: <https://www.iko.ac.jp/osaka>

#### `54fd6f6418ad0d27` / school `12`

- Reason: `no_candidates_found`
- PDF type: ``
- Detected fiscal year: ``
- Discovery method: ``
- Anchor: ``
- Suggested basis: No valid candidate was found or fetch failed; inspect the official SiteEntry/disclosure page.
- Page URL: <https://www.iko.ac.jp/nagoya>
- PDF URL: <https://www.iko.ac.jp/nagoya>

#### `bf12a235cd7aa235` / school `20`

- Reason: `pdf_school_mismatch`
- PDF type: `target`
- Detected fiscal year: ``
- Discovery method: `school_domain_override`
- Anchor: 2026年度 高等教育の修学支援新制度 申請様式
- Suggested basis: Target-like document has school-identity risk; confirm it belongs to the same institution.
- Page URL: <https://www.sanko.ac.jp/disclosure/yokohama-med/>
- PDF URL: <https://www.sanko.ac.jp/disclosure/yokohama-med/yoshiki2026.pdf>

#### `efbe9d08dc2cfba2` / school `25`

- Reason: `pdf_school_mismatch`
- PDF type: `target`
- Detected fiscal year: ``
- Discovery method: `school_domain_override`
- Anchor: 2026年度 高等教育の修学支援新制度 申請様式
- Suggested basis: Target-like document has school-identity risk; confirm it belongs to the same institution.
- Page URL: <https://www.sanko.ac.jp/disclosure/fukuoka-med/>
- PDF URL: <https://www.sanko.ac.jp/disclosure/fukuoka-med/docs/99158211b0011c77cfb13002f8106b4eb79443a6.pdf>

### `target_fiscal_year_not_detected` (`4` rows)

Review question: Can trusted FY2026/R8 evidence be found in the official page, anchor, filename, or PDF body?
False-reject signal: Trusted FY2026/R8 evidence exists but was not propagated to verification.

#### `3df9d0a93752f3c8` / school `1`

- Reason: `target_fiscal_year_not_detected`
- PDF type: `target`
- Detected fiscal year: ``
- Discovery method: `school_domain_override`
- Anchor: 大学等における修学の支援に関する法律第7条第1項の確認に係る申請書（様式第2号）
- Suggested basis: Target-form-like row lacks trusted target-year evidence; operator must confirm official FY evidence.
- Page URL: <https://www.neec.ac.jp/portal/public/mext-scholarship/>
- PDF URL: <https://www.neec.ac.jp/assets/contents/documents/portal/syllabus/hachioji/portal_syllabus_hachioji_yoshiki.pdf>

#### `a3873ee6a0eb300e` / school `1`

- Reason: `target_fiscal_year_not_detected`
- PDF type: `target`
- Detected fiscal year: ``
- Discovery method: `school_domain_override`
- Anchor: 大学等における修学の支援に関する法律第7条第1項の確認に係る申請書（様式第2号）
- Suggested basis: Target-form-like row lacks trusted target-year evidence; operator must confirm official FY evidence.
- Page URL: <https://www.neec.ac.jp/portal/public/mext-scholarship/>
- PDF URL: <https://www.neec.ac.jp/assets/contents/documents/portal/syllabus/kamata/portal_syllabus_kamata_yoshiki.pdf>

#### `780758ff3aec558a` / school `2`

- Reason: `target_fiscal_year_not_detected`
- PDF type: `target`
- Detected fiscal year: ``
- Discovery method: `school_domain_override`
- Anchor: 大学等における修学の支援に関する法律第7条第1項の確認に係る申請書（様式第2号）
- Suggested basis: Target-form-like row lacks trusted target-year evidence; operator must confirm official FY evidence.
- Page URL: <https://www.neec.ac.jp/portal/public/mext-scholarship/>
- PDF URL: <https://www.neec.ac.jp/assets/contents/documents/portal/syllabus/hachioji/portal_syllabus_hachioji_yoshiki.pdf>

#### `ad9beff98fd03c72` / school `2`

- Reason: `target_fiscal_year_not_detected`
- PDF type: `target`
- Detected fiscal year: ``
- Discovery method: `school_domain_override`
- Anchor: 大学等における修学の支援に関する法律第7条第1項の確認に係る申請書（様式第2号）
- Suggested basis: Target-form-like row lacks trusted target-year evidence; operator must confirm official FY evidence.
- Page URL: <https://www.neec.ac.jp/portal/public/mext-scholarship/>
- PDF URL: <https://www.neec.ac.jp/assets/contents/documents/portal/syllabus/kamata/portal_syllabus_kamata_yoshiki.pdf>


## 2. Confirm suggested correct rejects (`24` rows)

### `classified_non_target` (`4` rows)

Review question: Did the classifier mark any target application form as non-target?
False-reject signal: PDF is a target application form despite the non-target classification.

#### `d947ab42934f6fba` / school `3`

- Reason: `classified_non_target`
- PDF type: `non_target`
- Detected fiscal year: ``
- Discovery method: `school_domain_override`
- Anchor: 情報処理科 令和6年度
- Suggested basis: Explicit fiscal year 2024 is not FY2026; confirm no trusted target-year evidence exists.
- Page URL: <https://www.nkhs.ac.jp/about/publicindex/>
- PDF URL: <http://mail.nkhs.ac.jp/release/2024/HC_koukai_2024.pdf>

#### `f7d6437ae0b7f715` / school `12`

- Reason: `classified_non_target`
- PDF type: `non_target`
- Detected fiscal year: `2025`
- Discovery method: `school_domain_override`
- Anchor: ``
- Suggested basis: Explicit fiscal year 2025 is not FY2026; confirm no trusted target-year evidence exists.
- Page URL: <https://www.nkz.ac.jp/clginfo/ni/niC-d_nursingpublichealth_13.html>
- PDF URL: <https://www.nkz.ac.jp/clginfo/ni/pdf/niC-d_nursingpublichealth_13.pdf>

#### `7ad33b7e698ea7d2` / school `14`

- Reason: `classified_non_target`
- PDF type: `non_target`
- Detected fiscal year: ``
- Discovery method: `school_domain_override`
- Anchor: 学校沿革
- Suggested basis: Anchor or URL contains an obvious non-target hint; confirm it is not a target application form.
- Page URL: <https://www.sanko.ac.jp/disclosure/sendai-med/>
- PDF URL: <https://www.sanko.ac.jp/disclosure/sendai-med/enkaku.pdf>

#### `eff0008bb6dbbfa4` / school `26`

- Reason: `classified_non_target`
- PDF type: `non_target`
- Detected fiscal year: ``
- Discovery method: `school_domain_override`
- Anchor: 学校沿革
- Suggested basis: Anchor or URL contains an obvious non-target hint; confirm it is not a target application form.
- Page URL: <https://www.sanko.ac.jp/disclosure/omiya-ai/>
- PDF URL: <https://www.sanko.ac.jp/disclosure/omiya-ai/enkaku.pdf>

### `fiscal_year_mismatch` (`12` rows)

Review question: Are these true old-year target forms, or did FY2026/R8 evidence get missed?
False-reject signal: PDF/page/anchor contains trusted FY2026/R8 evidence but the row was rejected.

#### `3cb382458707332d` / school `3`

- Reason: `fiscal_year_mismatch:2019`
- PDF type: `target`
- Detected fiscal year: ``
- Discovery method: `school_domain_override`
- Anchor: 大学等における修学の支援に関する法律第７条第１項の確認に係る申請書 令和元年度(平成31年度)
- Suggested basis: Detected fiscal year 2019 is not FY2026; confirm no trusted target-year evidence exists.
- Page URL: <https://www.nkhs.ac.jp/about/publicindex/>
- PDF URL: <http://mail.nkhs.ac.jp/release/2019/nkhs_application2019.pdf>

#### `c5d11e711cf6a18d` / school `5`

- Reason: `fiscal_year_mismatch:2019`
- PDF type: `target`
- Detected fiscal year: ``
- Discovery method: `school_domain_override`
- Anchor: 2019年度
- Suggested basis: Detected fiscal year 2019 is not FY2026; confirm no trusted target-year evidence exists.
- Page URL: <https://www.nkz.ac.jp/clginfo/om/omZ-studyspt_13.html>
- PDF URL: <https://www.nkz.ac.jp/clginfo/om/pdf/omZ-studyspt_13_19.pdf>

#### `df992e72e0e366f4` / school `8`

- Reason: `fiscal_year_mismatch:2019`
- PDF type: `target`
- Detected fiscal year: ``
- Discovery method: `school_domain_override`
- Anchor: 2019年度
- Suggested basis: Detected fiscal year 2019 is not FY2026; confirm no trusted target-year evidence exists.
- Page URL: <https://www.nkz.ac.jp/clginfo/oh/ohZ-studyspt_13.html>
- PDF URL: <https://www.nkz.ac.jp/clginfo/oh/pdf/ohZ-studyspt_13_19.pdf>

#### `b17a21c6ee336dcf` / school `11`

- Reason: `fiscal_year_mismatch:2019`
- PDF type: `target`
- Detected fiscal year: ``
- Discovery method: `school_domain_override`
- Anchor: 2019年度
- Suggested basis: Detected fiscal year 2019 is not FY2026; confirm no trusted target-year evidence exists.
- Page URL: <https://www.nkz.ac.jp/clginfo/oi/oiZ-studyspt_13.html>
- PDF URL: <https://www.nkz.ac.jp/clginfo/oi/pdf/oiZ-studyspt_13_19.pdf>

#### `384cc4a975e6b398` / school `12`

- Reason: `fiscal_year_mismatch:2025`
- PDF type: `target`
- Detected fiscal year: `2025`
- Discovery method: `school_domain_override`
- Anchor: ``
- Suggested basis: Detected fiscal year 2025 is not FY2026; confirm no trusted target-year evidence exists.
- Page URL: <https://www.nkz.ac.jp/clginfo/ni/niZ-studyspt_13.html>
- PDF URL: <https://www.nkz.ac.jp/clginfo/ni/pdf/niZ-studyspt_13.pdf>

#### `f04863211f5bfa35` / school `13`

- Reason: `fiscal_year_mismatch:2019`
- PDF type: `target`
- Detected fiscal year: ``
- Discovery method: `school_domain_override`
- Anchor: 2019年度 高等教育の修学支援新制度 申請様式
- Suggested basis: Detected fiscal year 2019 is not FY2026; confirm no trusted target-year evidence exists.
- Page URL: <https://www.sanko.ac.jp/disclosure/sapporo-med/>
- PDF URL: <https://www.sanko.ac.jp/disclosure/sapporo-med/docs/yoshiki.pdf>

#### `f2e126bb58a1da01` / school `14`

- Reason: `fiscal_year_mismatch:2019`
- PDF type: `target`
- Detected fiscal year: ``
- Discovery method: `school_domain_override`
- Anchor: 2019年度 高等教育の修学支援新制度 申請様式
- Suggested basis: Detected fiscal year 2019 is not FY2026; confirm no trusted target-year evidence exists.
- Page URL: <https://www.sanko.ac.jp/disclosure/sendai-med/>
- PDF URL: <https://www.sanko.ac.jp/disclosure/sendai-med/docs/yoshiki.pdf>

#### `a1fd7d974bb54106` / school `15`

- Reason: `fiscal_year_mismatch:2019`
- PDF type: `target`
- Detected fiscal year: ``
- Discovery method: `school_domain_override`
- Anchor: 2019年度 高等教育の修学支援新制度 申請様式
- Suggested basis: Detected fiscal year 2019 is not FY2026; confirm no trusted target-year evidence exists.
- Page URL: <https://www.sanko.ac.jp/disclosure/omiya-med/>
- PDF URL: <https://www.sanko.ac.jp/disclosure/omiya-med/docs/yoshiki.pdf>

#### `41ce6f5be8cb7656` / school `16`

- Reason: `fiscal_year_mismatch:2019`
- PDF type: `target`
- Detected fiscal year: ``
- Discovery method: `school_domain_override`
- Anchor: 2019年度 高等教育の修学支援新制度 申請様式
- Suggested basis: Detected fiscal year 2019 is not FY2026; confirm no trusted target-year evidence exists.
- Page URL: <https://www.sanko.ac.jp/disclosure/chiba-med/>
- PDF URL: <https://www.sanko.ac.jp/disclosure/chiba-med/docs/yoshiki.pdf>

#### `1e0e4e9b972f490b` / school `17`

- Reason: `fiscal_year_mismatch:2019`
- PDF type: `target`
- Detected fiscal year: ``
- Discovery method: `school_domain_override`
- Anchor: 2019年度 高等教育の修学支援新制度 申請様式
- Suggested basis: Detected fiscal year 2019 is not FY2026; confirm no trusted target-year evidence exists.
- Page URL: <https://www.sanko.ac.jp/disclosure/tokyo-fukushi/>
- PDF URL: <https://www.sanko.ac.jp/tokyo-fukushi/pdf/yoshiki.pdf>

#### `1d1718b95989c199` / school `18`

- Reason: `fiscal_year_mismatch:2019`
- PDF type: `target`
- Detected fiscal year: ``
- Discovery method: `school_domain_override`
- Anchor: 2019年度 高等教育の修学支援新制度 申請様式
- Suggested basis: Detected fiscal year 2019 is not FY2026; confirm no trusted target-year evidence exists.
- Page URL: <https://www.sanko.ac.jp/disclosure/tokyo-med/>
- PDF URL: <https://www.sanko.ac.jp/disclosure/tokyo-med/docs/yoshiki.pdf>

#### `2e16d212cdfc3f0a` / school `19`

- Reason: `fiscal_year_mismatch:2019`
- PDF type: `target`
- Detected fiscal year: ``
- Discovery method: `school_domain_override`
- Anchor: 2019年度 高等教育の修学支援新制度 申請様式
- Suggested basis: Detected fiscal year 2019 is not FY2026; confirm no trusted target-year evidence exists.
- Page URL: <https://www.sanko.ac.jp/disclosure/tachikawa-child/>
- PDF URL: <https://www.sanko.ac.jp/disclosure/tachikawa-child/docs/yoshiki2019.pdf>

### `pre_filtered_non_target_hint` (`6` rows)

Review question: Did pre-download filtering reject any real target application form?
False-reject signal: Anchor/page/PDF title is a target application form, not GPA/syllabus/admission/evaluation material.

#### `890ca0d7454ed0a2` / school `1`

- Reason: `pre_filtered_non_target_hint`
- PDF type: `non_target`
- Detected fiscal year: ``
- Discovery method: `school_domain_override`
- Anchor: ＧＰＡ等の客観的成績評価の指標の算出方法
- Suggested basis: Anchor or URL contains an obvious non-target hint; confirm it is not a target application form.
- Page URL: <https://www.neec.ac.jp/portal/public/mext-scholarship/>
- PDF URL: <https://www.neec.ac.jp/assets/contents/documents/portal/tuition-guide/hachioji/portal_tuition-guide_hachioji_gpa.pdf>

#### `41b0fe496d74d992` / school `2`

- Reason: `pre_filtered_non_target_hint`
- PDF type: `non_target`
- Detected fiscal year: ``
- Discovery method: `school_domain_override`
- Anchor: ＧＰＡ等の客観的成績評価の指標の算出方法
- Suggested basis: Anchor or URL contains an obvious non-target hint; confirm it is not a target application form.
- Page URL: <https://www.neec.ac.jp/portal/public/mext-scholarship/>
- PDF URL: <https://www.neec.ac.jp/assets/contents/documents/portal/tuition-guide/hachioji/portal_tuition-guide_hachioji_gpa.pdf>

#### `f44f85bdb3ddbe5e` / school `3`

- Reason: `pre_filtered_non_target_hint`
- PDF type: `non_target`
- Detected fiscal year: ``
- Discovery method: `school_domain_override`
- Anchor: 平成29年度 学校関係者評価報告書および情報公開資料
- Suggested basis: Anchor or URL contains an obvious non-target hint; confirm it is not a target application form.
- Page URL: <https://www.nkhs.ac.jp/about/publicindex/>
- PDF URL: <http://mail.nkhs.ac.jp/release/2017/H29_nkhs_houkoku.pdf>

#### `bec72ddf215ab524` / school `15`

- Reason: `pre_filtered_non_target_hint`
- PDF type: `non_target`
- Detected fiscal year: ``
- Discovery method: `school_domain_override`
- Anchor: 学校沿革
- Suggested basis: Anchor or URL contains an obvious non-target hint; confirm it is not a target application form.
- Page URL: <https://www.sanko.ac.jp/disclosure/omiya-med/>
- PDF URL: <https://www.sanko.ac.jp/disclosure/omiya-med/docs/1fd2887cfc41529a1c403ddc63a6f4899a21468d.pdf>

#### `0ec110e311ebf5fa` / school `18`

- Reason: `pre_filtered_non_target_hint`
- PDF type: `non_target`
- Detected fiscal year: ``
- Discovery method: `school_domain_override`
- Anchor: 実務経験のある教員等による授業科目の一覧表
- Suggested basis: Anchor or URL contains an obvious non-target hint; confirm it is not a target application form.
- Page URL: <https://www.sanko.ac.jp/disclosure/tokyo-med/>
- PDF URL: <https://www.sanko.ac.jp/disclosure/tokyo-med/docs/childcare_04.pdf>

#### `d0e7003699d11129` / school `20`

- Reason: `pre_filtered_non_target_hint`
- PDF type: `non_target`
- Detected fiscal year: ``
- Discovery method: `school_domain_override`
- Anchor: 学校関係者評価委員会 報告書
- Suggested basis: Anchor or URL contains an obvious non-target hint; confirm it is not a target application form.
- Page URL: <https://www.sanko.ac.jp/disclosure/yokohama-med/>
- PDF URL: <https://www.sanko.ac.jp/disclosure/yokohama-med/docs/kankeisya.pdf>

### `target_fiscal_year_not_detected` (`2` rows)

Review question: Can trusted FY2026/R8 evidence be found in the official page, anchor, filename, or PDF body?
False-reject signal: Trusted FY2026/R8 evidence exists but was not propagated to verification.

#### `9654c51f02f8d03a` / school `40`

- Reason: `target_fiscal_year_not_detected`
- PDF type: `image_only`
- Detected fiscal year: ``
- Discovery method: `seed_csv`
- Anchor: 2021年度
- Suggested basis: Explicit fiscal year 2021 is not FY2026; confirm the row is not target-year evidence.
- Page URL: <https://www.sanko.ac.jp/sendai-beauty/disclosure/>
- PDF URL: <https://www.sanko.ac.jp/sendai-beauty/pdf/yoshiki2021.pdf>

#### `53081162229f7ef3` / school `44`

- Reason: `target_fiscal_year_not_detected`
- PDF type: `image_only`
- Detected fiscal year: ``
- Discovery method: `school_domain_override`
- Anchor: 2019年度
- Suggested basis: Explicit fiscal year 2019 is not FY2026; confirm the row is not target-year evidence.
- Page URL: <https://www.sanko.ac.jp/tachikawa-beauty/disclosure/>
- PDF URL: <https://www.sanko.ac.jp/tachikawa-beauty/pdf/yoshiki.pdf>
