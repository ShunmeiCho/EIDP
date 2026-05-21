# Prefecture Official Index Structure Investigation

Date: 2026-05-06

## Conclusion

The primary discovery path should start from official confirmer indexes, not
from blind school-site search.

Target flow:

1. MEXT national target-institution list defines the active universe.
2. Prefecture official 確認大学等 pages/PDFs provide school publication URLs
   for governor-confirmed public universities, prefectural vocational schools,
   and private vocational schools.
3. EIDP crawls those school/corporation publication pages and selects only the
   configured target fiscal-year application PDF.
4. Blind school-site search remains a fallback, not the main path.

This is a long-running rolling fiscal-year system. In 2026 it targets
2026年度（令和8年度）; in 2027 it should target 2027年度（令和9年度） by
configuration, not by hard-coded R8 behavior.

Do not design any component as a one-year R8 crawler. Every run must treat the
current fiscal year as a configuration value and treat prefecture indexes as
live annual evidence. Schools can be newly confirmed, withdrawn, renamed,
merged, or moved between confirmer scopes in future years.

## Why This Matters

The old discovery posture treated each school website as the first search
surface. That caused low URL coverage and many stale PDFs because school
navigation differs widely.

The official-prefecture path is materially better:

- It starts from authoritative 確認大学等 lists.
- Many lists embed the exact publication URL or make the school name clickable.
- The 備考 column carries operational signals such as 新規認定校, 名称変更,
  辞退/取消, 統合再編.
- It gives the operator a clear evidence chain:
  都道府県一覧 -> school/corporation publication page -> selected PDF.

## Verified Structure Types

| Type | Structure | Examples | Implementation |
| --- | --- | --- | --- |
| PDF text URL column | PDF table has an explicit URL column or 備考 URL | Tokyo, Kanagawa | `parse_tokyo`, `parse_5col` |
| PDF school-name hyperlink | School name cell is clickable; URL is a PDF annotation, not table text | Saitama, Fukui, Miyagi-style, Akita partial | `extract_pdf_annotation_links` + `parse_5col` |
| PDF school-universe table | PDF table lists confirmed schools but does not publish URLs | Chiba, Ibaraki | `parse_6col_indexed`, `parse_5col`; useful for yearly universe/remarks, not URL coverage |
| HTML table/list | Official page itself has school rows; school name or publication cell is linked | Aomori, Nagano, Wakayama, Tottori, Yamaguchi, Oita, Miyazaki, Tochigi, Kagoshima | `parse_html_table` |
| XLSX code list | Prefecture publishes XLSX with MEXT school code | Osaka | school-code matching path |
| Partial official index | Official page lists schools but not every URL | Gunma | parse usable rows, leave missing URLs for fallback |
| Decentralized publication | Prefecture page points to individual school PDFs or mixed structures | Hiroshima and some unclear pages | owner review / custom parser |

## Verified Local Parse Evidence

These were downloaded only as development verification artifacts. The product
behavior remains runtime download on the Windows operator PC.

| Prefecture | Artifact | Rows parsed | URLs parsed | Notes |
| --- | --- | ---: | ---: | --- |
| Saitama | PDF annotation links | 60 | 60 | school-name hyperlinks are essential |
| Kanagawa | PDF text URL column | 76 | 75 | KUHS publication page confirmed |
| Aomori | HTML official page | 16 | 16 | current generic HTML parser works |
| Nagano | HTML official page | 43 | 38 | 備考 includes name-change signals |
| Fukui | PDF annotation/text | 13 | 7 | school-name links / HP remarks |
| Wakayama | HTML official page | 13 | 11 | generic HTML parser works |
| Tottori | HTML official page | 14 | 14 | generic HTML parser works |
| Yamaguchi | HTML official page | 18 | 18 | generic HTML parser works |
| Oita | HTML official page | 25 | 25 | generic HTML parser works |
| Miyazaki | HTML official page | 23 | 23 | 備考 includes name-change signals |
| Gunma | HTML official page | 43 | 3 | private-school URL coverage is low; fallback needed |
| Akita | PDF annotation links | 8 | 3 | parser is partial because pdfplumber splits some names |
| Chiba | PDF school-universe table | 62 | 0 | official target-year list; 備考 has new-accreditation signals |
| Ibaraki | PDF school-universe table | 45 | 0 | official school universe; no publication URLs in artifact |
| Tochigi | HTML official page | 39 | 39 | school-name links point to disclosure/home pages |
| Kagoshima | HTML official page | 23 | 23 | school-name links point to disclosure/home pages; 備考 has prior-year signals |

## 備考 Handling

The 備考 column must be preserved. It is now carried into the prefecture
writer-plan as:

- `pref_remarks`: original text
- `pref_remark_tags`: coarse tags
- `pref_has_school_change_signal`: boolean

Current tags:

- `new_accreditation`: 新規認定 / 追加
- `name_change`: 名称変更 / 校名変更 / 改称 / 旧称
- `withdrawal`: 取消 / 辞退 / 対象外 / 満たさなくなった
- `merger_reorg`: 統合 / 再編 / 合併

When those tags exist on a matched school, `apply_writer_plan` creates a
pending `review_item` with `item_type='prefecture_remark'`. This gives the
operator a durable school-change review queue without changing the schema.

For long-term operation, these remarks are not one-off notes. They are annual
change signals:

- new schools must appear as target-year tasks even if they were absent last year,
- withdrawals/cancellations must stop those schools from being counted as missing PDFs,
- name changes must update matching aliases before Excel comparison,
- mergers/reorganizations must trigger department/school review before export.

## Current Seed Status

Ready for runtime bootstrap:

- Tokyo
- Kanagawa
- Saitama
- Osaka
- Fukuoka
- Hokkaido
- Hyogo
- Shizuoka
- Miyagi
- Okinawa (old R3 artifact; needs newer owner check)
- Aomori
- Akita (partial parser)
- Fukui
- Gunma (partial URL coverage)
- Chiba (school universe only; no URL coverage)
- Ibaraki (school universe only; no URL coverage)
- Tochigi
- Kagoshima
- Nagano
- Wakayama
- Tottori
- Yamaguchi
- Oita
- Miyazaki

Candidate official pages found but not yet parser-verified:

- Kyoto: https://www.pref.kyoto.jp/bunkyo/syugakusien.html
- Kumamoto: https://www.pref.kumamoto.jp/soshiki/143/58492.html
- Yamagata: https://www.pref.yamagata.jp/020023/bunkyo/shigaku/shien/kikanyoukenkakunin.html
- Fukushima: https://www.pref.fukushima.lg.jp/sec/01155c/koutoukyouikusyuugakusienn.html
- Ishikawa: https://www.pref.ishikawa.lg.jp/soumu/bunkyo/shigaku/mushoka.html
- Yamanashi: https://www.pref.yamanashi.jp/shigaku-kgk/shugaku.html
- Gifu: https://www.pref.gifu.lg.jp/page/444244.html
- Mie: https://www.pref.mie.lg.jp/SHIGAKU/HP/m0204800067.htm
- Shiga: https://www.pref.shiga.lg.jp/ippan/kosodatekyouiku/kyouiku/303118.html
- Nara: https://www.pref.nara.jp/53680.htm
- Shimane: https://www.pref.shimane.lg.jp/education/kyoiku/gakko/shigaku/shuugakushiennsinnseido.html
- Okayama: https://www.pref.okayama.jp/page/628722.html
- Tokushima: https://www.pref.tokushima.lg.jp/ippannokata/kyoiku/gakkokyoiku/5030224/
- Ehime: https://www.pref.ehime.jp/page/14085.html
- Kochi: https://www.pref.kochi.lg.jp/doc/2019092000161/
- Saga: https://www.pref.saga.lg.jp/kiji00371013/index.html
- Nagasaki: https://www.pref.nagasaki.jp/bunrui/kanko-kyoiku-bunka/gakkokyoiku/shigaku-shinko/syuugakusien/
- Kagawa: https://www.pref.kagawa.lg.jp/nodai/prospectus/kyoikujoho/taisyoukikan.html

Needs owner/manual structure confirmation:

- Toyama: search found the department page, not yet the specific 確認大学等 index.
- Hiroshima: appears decentralized; may publish individual 様式第2号 links.
- Kagawa: current found page is school-level for 香川県立農業大学校, not a full prefecture-wide index.
- Okinawa: seed has an old R3 PDF; likely newer page exists and must be checked.

## Product Build Implications

Windows deployment should not ship a frozen PDF corpus. It should ship:

- parser registry,
- seed CSV of official confirmer pages/artifacts,
- UI button for initial/weekly acquisition,
- progress file/log display,
- evidence trail for accepted and rejected PDF candidates.

The operator action should be:

1. Open EIDP.
2. Click initial URL/PDF acquisition or let weekly task run.
3. Review the school task board.
4. Open PDF confirmation only for exceptions.

Manual URL entry should exist as fallback, not as the expected path.

The yearly loop should be:

1. Compute `target_fiscal_year` from the current date/config.
2. Download the latest official MEXT/prefecture confirmer lists.
3. Diff against last run's school universe and publication URLs.
4. Create tasks for new, missing, withdrawn, renamed, and changed schools.
5. Crawl publication pages and accept only PDFs confirmed for the target fiscal year.
6. Keep rejected/stale PDFs as evidence, not as completion.

## Remaining Work

1. Add parser verification for the candidate official pages above.
2. Add custom parsers for decentralized/partial pages after owner confirms structure.
3. Add a UI view for `prefecture_remark` review items.
4. Add an evidence panel showing:
   - official index source,
   - school publication URL,
   - selected PDF URL,
   - rejected candidate URLs and reasons.
5. Continue strict target-fiscal-year gating so stale 2025 PDFs do not count
   as 2026 results.
6. Add annual school-universe diffing from MEXT/prefecture indexes so new and
   withdrawn schools are handled automatically across years.
