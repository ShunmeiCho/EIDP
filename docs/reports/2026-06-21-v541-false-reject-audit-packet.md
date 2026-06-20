# Stage 6 False-Reject Audit Packet

Archive: `logs/win-v541-e62d074-canary/stage6-evidence-20260620-153655.zip`

Status: `READY_TO_AUDIT`
Release Forecast: `NOT_READY`
Strict Excel-ready yield: `12/50` (`24.0%`), required `60.0%`.

This packet does not relax FY2026/R8 evidence rules and does not allow rejected rows into Excel.
Generic algorithm/model failure supported: `False`.
Reason: Below-gate strict yield requires bucket-level false-reject audit; it is not by itself evidence of a generic algorithm/model failure.

## Audit Buckets

| Bucket | Rows | Unique rows | Sampled | Review question |
| --- | ---: | ---: | ---: | --- |
| `fiscal_year_mismatch` | 206 | 206 | 12 | Are these true old-year target forms, or did FY2026/R8 evidence get missed? |
| `pre_filtered_non_target_hint` | 432 | 432 | 12 | Did pre-download filtering reject any real target application form? |
| `classified_non_target` | 103 | 103 | 12 | Did the classifier mark any target application form as non-target? |
| `target_fiscal_year_not_detected` | 6 | 6 | 6 | Can trusted FY2026/R8 evidence be found in the official page, anchor, filename, or PDF body? |
| `site_entry_fetch_identity` | 11 | 11 | 11 | Is this a SiteEntry, fetch, or school-identity gap rather than a missing-publication case? |

## Review Instructions

- Mark a row `false_reject` only when official evidence proves it should have been accepted for FY2026/R8.
- Mark a row `correct_reject` when it is old-year, non-target, unknown-year, mismatched, or unsupported.
- Mark a row `needs_operator_review` when evidence exists but requires human confirmation.
- Do not count old-year PDFs, unknown-year PDFs, non-target PDFs, or school mismatches as FY2026/R8 success.

## Sample Rows

### `fiscal_year_mismatch`

False-reject signal: PDF/page/anchor contains trusted FY2026/R8 evidence but the row was rejected.

| School ID | Reason | PDF type | Year evidence | Anchor | Page URL | PDF URL |
| ---: | --- | --- | --- | --- | --- | --- |
| 3 | `fiscal_year_mismatch:2019` | `target` | school_domain_override_disclosure | 大学等における修学の支援に関する法律第７条第１項の確認に係る申請書 令和元年度(平成31年度) | `https://www.nkhs.ac.jp/about/publicindex/` | `http://mail.nkhs.ac.jp/release/2019/nkhs_application2019.pdf` |
| 5 | `fiscal_year_mismatch:2019` | `target` | school_domain_override_disclosure | 2019年度 | `https://www.nkz.ac.jp/clginfo/om/omZ-studyspt_13.html` | `https://www.nkz.ac.jp/clginfo/om/pdf/omZ-studyspt_13_19.pdf` |
| 8 | `fiscal_year_mismatch:2019` | `target` | school_domain_override_disclosure | 2019年度 | `https://www.nkz.ac.jp/clginfo/oh/ohZ-studyspt_13.html` | `https://www.nkz.ac.jp/clginfo/oh/pdf/ohZ-studyspt_13_19.pdf` |
| 11 | `fiscal_year_mismatch:2019` | `target` | school_domain_override_disclosure | 2019年度 | `https://www.nkz.ac.jp/clginfo/oi/oiZ-studyspt_13.html` | `https://www.nkz.ac.jp/clginfo/oi/pdf/oiZ-studyspt_13_19.pdf` |
| 12 | `fiscal_year_mismatch:2025` | `target` | school_domain_override_disclosure |  | `https://www.nkz.ac.jp/clginfo/ni/niZ-studyspt_13.html` | `https://www.nkz.ac.jp/clginfo/ni/pdf/niZ-studyspt_13.pdf` |
| 13 | `fiscal_year_mismatch:2019` | `target` |  | 2019年度 高等教育の修学支援新制度 申請様式 | `https://www.sanko.ac.jp/disclosure/sapporo-med/` | `https://www.sanko.ac.jp/disclosure/sapporo-med/docs/yoshiki.pdf` |
| 14 | `fiscal_year_mismatch:2019` | `target` |  | 2019年度 高等教育の修学支援新制度 申請様式 | `https://www.sanko.ac.jp/disclosure/sendai-med/` | `https://www.sanko.ac.jp/disclosure/sendai-med/docs/yoshiki.pdf` |
| 15 | `fiscal_year_mismatch:2019` | `target` |  | 2019年度 高等教育の修学支援新制度 申請様式 | `https://www.sanko.ac.jp/disclosure/omiya-med/` | `https://www.sanko.ac.jp/disclosure/omiya-med/docs/yoshiki.pdf` |
| 16 | `fiscal_year_mismatch:2019` | `target` |  | 2019年度 高等教育の修学支援新制度 申請様式 | `https://www.sanko.ac.jp/disclosure/chiba-med/` | `https://www.sanko.ac.jp/disclosure/chiba-med/docs/yoshiki.pdf` |
| 17 | `fiscal_year_mismatch:2019` | `target` |  | 2019年度 高等教育の修学支援新制度 申請様式 | `https://www.sanko.ac.jp/disclosure/tokyo-fukushi/` | `https://www.sanko.ac.jp/tokyo-fukushi/pdf/yoshiki.pdf` |
| 18 | `fiscal_year_mismatch:2019` | `target` |  | 2019年度 高等教育の修学支援新制度 申請様式 | `https://www.sanko.ac.jp/disclosure/tokyo-med/` | `https://www.sanko.ac.jp/disclosure/tokyo-med/docs/yoshiki.pdf` |
| 19 | `fiscal_year_mismatch:2019` | `target` |  | 2019年度 高等教育の修学支援新制度 申請様式 | `https://www.sanko.ac.jp/disclosure/tachikawa-child/` | `https://www.sanko.ac.jp/disclosure/tachikawa-child/docs/yoshiki2019.pdf` |

### `pre_filtered_non_target_hint`

False-reject signal: Anchor/page/PDF title is a target application form, not GPA/syllabus/admission/evaluation material.

| School ID | Reason | PDF type | Year evidence | Anchor | Page URL | PDF URL |
| ---: | --- | --- | --- | --- | --- | --- |
| 1 | `pre_filtered_non_target_hint` | `non_target` |  | ＧＰＡ等の客観的成績評価の指標の算出方法 | `https://www.neec.ac.jp/portal/public/mext-scholarship/` | `https://www.neec.ac.jp/assets/contents/documents/portal/tuition-guide/hachioji/portal_tuition-guide_hachioji_gpa.pdf` |
| 2 | `pre_filtered_non_target_hint` | `non_target` |  | ＧＰＡ等の客観的成績評価の指標の算出方法 | `https://www.neec.ac.jp/portal/public/mext-scholarship/` | `https://www.neec.ac.jp/assets/contents/documents/portal/tuition-guide/hachioji/portal_tuition-guide_hachioji_gpa.pdf` |
| 3 | `pre_filtered_non_target_hint` | `non_target` | school_domain_override_disclosure | 平成29年度 学校関係者評価報告書および情報公開資料 | `https://www.nkhs.ac.jp/about/publicindex/` | `http://mail.nkhs.ac.jp/release/2017/H29_nkhs_houkoku.pdf` |
| 13 | `pre_filtered_non_target_hint` | `non_target` |  | 1年 | `https://www.sanko.ac.jp/disclosure/sapporo-med/` | `https://www.sanko.ac.jp/disclosure/sapporo-med/healthinfo_01.pdf` |
| 14 | `pre_filtered_non_target_hint` | `non_target` |  | 1年 | `https://www.sanko.ac.jp/disclosure/sendai-med/` | `https://www.sanko.ac.jp/disclosure/sendai-med/docs/care_01.pdf` |
| 15 | `pre_filtered_non_target_hint` | `non_target` |  | 学校沿革 | `https://www.sanko.ac.jp/disclosure/omiya-med/` | `https://www.sanko.ac.jp/disclosure/omiya-med/docs/1fd2887cfc41529a1c403ddc63a6f4899a21468d.pdf` |
| 16 | `pre_filtered_non_target_hint` | `non_target` |  | 1年 | `https://www.sanko.ac.jp/disclosure/chiba-med/` | `https://www.sanko.ac.jp/disclosure/chiba-med/docs/13e9921e812dd992dda6fe58de136c3be802eaff.pdf` |
| 17 | `pre_filtered_non_target_hint` | `non_target` |  | 1年 | `https://www.sanko.ac.jp/disclosure/tokyo-fukushi/` | `https://www.sanko.ac.jp/disclosure/tokyo-fukushi/docs/08d452f4472b178f0fddc91b9a41eb9fe7505429.pdf` |
| 18 | `pre_filtered_non_target_hint` | `non_target` |  | 実務経験のある教員等による授業科目の一覧表 | `https://www.sanko.ac.jp/disclosure/tokyo-med/` | `https://www.sanko.ac.jp/disclosure/tokyo-med/docs/childcare_04.pdf` |
| 19 | `pre_filtered_non_target_hint` | `non_target` |  | 学校情報 | `https://www.sanko.ac.jp/disclosure/tachikawa-child/` | `https://www.sanko.ac.jp/disclosure/tachikawa-child/docs/08d3435687b7165d8b22b0f0e677696975b8ac6e.pdf` |
| 20 | `pre_filtered_non_target_hint` | `non_target` |  | 学校関係者評価委員会 報告書 | `https://www.sanko.ac.jp/disclosure/yokohama-med/` | `https://www.sanko.ac.jp/disclosure/yokohama-med/docs/kankeisya.pdf` |
| 21 | `pre_filtered_non_target_hint` | `non_target` |  | 1年 | `https://www.sanko.ac.jp/disclosure/nagoya-med/` | `https://www.sanko.ac.jp/disclosure/nagoya-med/docs/childcare_01.pdf` |

### `classified_non_target`

False-reject signal: PDF is a target application form despite the non-target classification.

| School ID | Reason | PDF type | Year evidence | Anchor | Page URL | PDF URL |
| ---: | --- | --- | --- | --- | --- | --- |
| 3 | `classified_non_target` | `non_target` | school_domain_override_disclosure | 情報処理科 令和6年度 | `https://www.nkhs.ac.jp/about/publicindex/` | `http://mail.nkhs.ac.jp/release/2024/HC_koukai_2024.pdf` |
| 11 | `classified_non_target` | `non_target` | school_domain_override_disclosure |  | `https://www.nkz.ac.jp/clginfo/oi/oiC-d_nursingpublichealth_13.html` | `https://www.nkz.ac.jp/clginfo/oi/pdf/oiC-d_nursingpublichealth_13.pdf` |
| 12 | `classified_non_target` | `non_target` | school_domain_override_disclosure |  | `https://www.nkz.ac.jp/clginfo/ni/niC-d_nursingpublichealth_13.html` | `https://www.nkz.ac.jp/clginfo/ni/pdf/niC-d_nursingpublichealth_13.pdf` |
| 13 | `classified_non_target` | `non_target` |  | 1年 | `https://www.sanko.ac.jp/disclosure/sapporo-med/` | `https://www.sanko.ac.jp/disclosure/sapporo-med/care_01.pdf` |
| 14 | `classified_non_target` | `non_target` |  | 学校沿革 | `https://www.sanko.ac.jp/disclosure/sendai-med/` | `https://www.sanko.ac.jp/disclosure/sendai-med/enkaku.pdf` |
| 16 | `classified_non_target` | `non_target` |  | 1年 | `https://www.sanko.ac.jp/disclosure/chiba-med/` | `https://www.sanko.ac.jp/disclosure/chiba-med/bd5084288531bf11ed0bde63319cabe61e4d609d.pdf` |
| 17 | `classified_non_target` | `non_target` |  | 3年 | `https://www.sanko.ac.jp/disclosure/tokyo-fukushi/` | `https://www.sanko.ac.jp/disclosure/tokyo-fukushi/childhood_studies_03.pdf` |
| 18 | `classified_non_target` | `non_target` |  | 1年 | `https://www.sanko.ac.jp/disclosure/tokyo-med/` | `https://www.sanko.ac.jp/disclosure/tokyo-med/8ce42f9cadd6b0cbc1c4155e0b9bf3b38678ddaf.pdf` |
| 20 | `classified_non_target` | `non_target` |  | 1年 | `https://www.sanko.ac.jp/disclosure/yokohama-med/` | `https://www.sanko.ac.jp/disclosure/yokohama-med/drug_01.pdf` |
| 21 | `classified_non_target` | `non_target` |  | 1年 | `https://www.sanko.ac.jp/disclosure/nagoya-med/` | `https://www.sanko.ac.jp/disclosure/nagoya-med/care_01.pdf` |
| 26 | `classified_non_target` | `non_target` |  | 学校沿革 | `https://www.sanko.ac.jp/disclosure/omiya-ai/` | `https://www.sanko.ac.jp/disclosure/omiya-ai/enkaku.pdf` |
| 27 | `classified_non_target` | `non_target` |  | AIプログラミング＆CGクリエイター科-1年 | `https://www.sanko.ac.jp/tokyo-ai/information/` | `https://www.sanko.ac.jp/tokyo-ai/information/1ebc0c36a3362449ae3068e9e8eee80c468d479c.pdf` |

### `target_fiscal_year_not_detected`

False-reject signal: Trusted FY2026/R8 evidence exists but was not propagated to verification.

| School ID | Reason | PDF type | Year evidence | Anchor | Page URL | PDF URL |
| ---: | --- | --- | --- | --- | --- | --- |
| 1 | `target_fiscal_year_not_detected` | `target` | target_application_no_year | 大学等における修学の支援に関する法律第7条第1項の確認に係る申請書（様式第2号） | `https://www.neec.ac.jp/portal/public/mext-scholarship/` | `https://www.neec.ac.jp/assets/contents/documents/portal/syllabus/hachioji/portal_syllabus_hachioji_yoshiki.pdf` |
| 2 | `target_fiscal_year_not_detected` | `target` | target_application_no_year | 大学等における修学の支援に関する法律第7条第1項の確認に係る申請書（様式第2号） | `https://www.neec.ac.jp/portal/public/mext-scholarship/` | `https://www.neec.ac.jp/assets/contents/documents/portal/syllabus/hachioji/portal_syllabus_hachioji_yoshiki.pdf` |
| 40 | `target_fiscal_year_not_detected` | `image_only` | none | 2021年度 | `https://www.sanko.ac.jp/sendai-beauty/disclosure/` | `https://www.sanko.ac.jp/sendai-beauty/pdf/yoshiki2021.pdf` |
| 44 | `target_fiscal_year_not_detected` | `image_only` | none | 2019年度 | `https://www.sanko.ac.jp/tachikawa-beauty/disclosure/` | `https://www.sanko.ac.jp/tachikawa-beauty/pdf/yoshiki.pdf` |
| 1 | `target_fiscal_year_not_detected` | `target` | target_application_no_year | 大学等における修学の支援に関する法律第7条第1項の確認に係る申請書（様式第2号） | `https://www.neec.ac.jp/portal/public/mext-scholarship/` | `https://www.neec.ac.jp/assets/contents/documents/portal/syllabus/kamata/portal_syllabus_kamata_yoshiki.pdf` |
| 2 | `target_fiscal_year_not_detected` | `target` | target_application_no_year | 大学等における修学の支援に関する法律第7条第1項の確認に係る申請書（様式第2号） | `https://www.neec.ac.jp/portal/public/mext-scholarship/` | `https://www.neec.ac.jp/assets/contents/documents/portal/syllabus/kamata/portal_syllabus_kamata_yoshiki.pdf` |

### `site_entry_fetch_identity`

False-reject signal: The official source points to a valid FY2026/R8 target document for the same school.

| School ID | Reason | PDF type | Year evidence | Anchor | Page URL | PDF URL |
| ---: | --- | --- | --- | --- | --- | --- |
| 4 | `discovery_error` | `` |  |  | `https://www.mode.ac.jp/tokyo` | `https://www.mode.ac.jp/tokyo` |
| 5 | `discovery_error` | `` |  |  | `https://www.mode.ac.jp/osaka` | `https://www.mode.ac.jp/osaka` |
| 6 | `discovery_error` | `` |  |  | `https://www.mode.ac.jp/nagoya` | `https://www.mode.ac.jp/nagoya` |
| 7 | `discovery_error` | `` |  |  | `https://www.hal.ac.jp/tokyo` | `https://www.hal.ac.jp/tokyo` |
| 8 | `no_candidates_found` | `` |  |  | `https://www.hal.ac.jp/osaka` | `https://www.hal.ac.jp/osaka` |
| 9 | `no_candidates_found` | `` |  |  | `https://www.hal.ac.jp/nagoya` | `https://www.hal.ac.jp/nagoya` |
| 10 | `no_candidates_found` | `` |  |  | `https://www.iko.ac.jp/tokyo` | `https://www.iko.ac.jp/tokyo` |
| 11 | `no_candidates_found` | `` |  |  | `https://www.iko.ac.jp/osaka` | `https://www.iko.ac.jp/osaka` |
| 12 | `no_candidates_found` | `` |  |  | `https://www.iko.ac.jp/nagoya` | `https://www.iko.ac.jp/nagoya` |
| 20 | `pdf_school_mismatch` | `target` | url_hint | 2026年度 高等教育の修学支援新制度 申請様式 | `https://www.sanko.ac.jp/disclosure/yokohama-med/` | `https://www.sanko.ac.jp/disclosure/yokohama-med/yoshiki2026.pdf` |
| 25 | `pdf_school_mismatch` | `target` | url_hint | 2026年度 高等教育の修学支援新制度 申請様式 | `https://www.sanko.ac.jp/disclosure/fukuoka-med/` | `https://www.sanko.ac.jp/disclosure/fukuoka-med/docs/99158211b0011c77cfb13002f8106b4eb79443a6.pdf` |
