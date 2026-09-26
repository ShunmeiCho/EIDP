# EIDP Coding Standards

These are the rules a human or agent keeps in mind while writing and reviewing
code here. Each one exists because breaking it has already cost this repo a
bug, usually more than once. The incidents are listed under each rule so you
can judge edge cases by what actually went wrong.

This file holds only judgement rules. Formatting, lint, types, secrets, the lock
contract and commit format are handled by tools and by `CLAUDE.md` / `AGENTS.md`.
Domain policy (source trust tiers, fiscal-year evidence strength, red lines) is
in `docs/governance/project-rules.md`. The rules below are the code-level
habits that keep that policy true.

## Fiscal years

### 1. The target fiscal year is passed in. It is never guessed or typed as a literal.

Entry points (CLI command, Web page, runner script) read
`settings.target_fiscal_year` once and pass it down as a parameter. Library code
does not call `datetime.now()` or `current_fiscal_year()` to decide which year
is current. It does not write year literals, year ranges or year-shaped regexes
(`202[0-9]`) either. Year bounds come from `MIN/MAX_SUPPORTED_TARGET_FISCAL_YEAR`
in `src/eidp/config.py`. See also the `EIDP_TARGET_FISCAL_YEAR` red line in
`CLAUDE.md`.

Why:
- Three cross-model review rounds in a row found hardcoded year lists that did
  not move with the others: `range(2019, 2026)` in the importer (`bace380`),
  `CASE WHEN` columns for 2019-2025 in exporter SQL (`19c40a4`), and
  `BETWEEN 2019 AND 2024` in the 在籍のみ抜粋 sheet (`ee6e2c8`).
- Parsers each kept a private `_current_jst_fiscal_year()` built on
  `datetime.now(JST)`, so they ignored the configured target year
  (`5b8a8c8`). Reports had the same problem (`1292e99`).
- Entry points dropped the target year on the way down. Ingestion and bootstrap
  ingestion fell back to a different year than the caller had chosen
  (`4de0aa8`, `15bb450`), and Excel export years were not tied to the target
  FY (`504fe3e`).
- The PDF year regex `202[0-9]` would have stopped matching in FY2030
  (`281643c`). "R8" leaked from shorthand into UI labels and discovery scoring
  keywords (`31fd147`), and hardcoded 2026 values sat in review pages
  (`74ad40b`, `c120fb4`).

### 2. A year in text counts as fiscal-year evidence only when it is labelled as a fiscal year, in the scope that owns it.

A `年度` or era-`年度` label inside the link's own anchor, table row, card or
heading counts. These do not: publication or filing dates, completion or
graduation years, future term years, upload-path dates, the fetch time, and
text belonging to a neighbouring link or sibling element. When evidence is
missing, the row goes to a year-unverified state; it does not get a default
year. The evidence-strength policy is in `docs/governance/project-rules.md`
("Fiscal-Year Evidence").

Why:
- Download time was assigning fiscal years to PDFs that had no year evidence
  (`31bd877`).
- Each of these produced false target-year hits: publication dates
  (`8970c10`), completion years (`a9baf02`), future term years (`6e1a0d8`),
  upload-path dates beating the prefecture index year (`d2beff6`), and stale
  era hints from trusted indexes (`8670acc`).
- Context bled between links. Year text from one anchor or list item was
  applied to another (`db84f5c`, `db5003d`, `0ee34c6`, `cfe3ab0`), visible
  sibling text was used for empty anchors (`39b3014`), and commented-out links
  were read as evidence (`01ff8ca`).

## Revisioned data and audit

### 3. Read revisioned tables through the current-row helpers, and build each new revision from the previous one.

`CLAUDE.md` defines the append-only write contract. The read side and the
carry-forward are where it has broken:

- Every read of `DepartmentYearly`, `SupportRecipient` or `SchoolYearStatus`
  goes through `src/eidp/db/current_helpers.py` or filters `is_current`
  explicitly. Latest-fiscal-year questions use `latest_excluded_school_ids`;
  do not write a new subquery for them.
- A new revision starts from the current row. It overwrites only the fields the
  new source actually supplies (not `None`) and carries every other column
  forward.
- If the new values equal the current row, write nothing: no revision and no
  audit churn.

Why:
- Read paths without an `is_current` filter mixed demoted history with current
  state. After a fiscal-year override, Excel and discovery kept reading the old
  state, and 対象比率 summed across revisions (`234fcb0`). The importer queried
  `revision=1` instead of the current row (`c439982`).
- `verify_identity` kept its own copy of the "excluded" subquery that filtered
  `is_current` but not the latest fiscal year. That made it a false-positive
  gate (`6c874c3`).
- Re-ingest and manual confirmation rebuilt `SupportRecipient` without
  carrying `school_number`, `prev_enrollment` and `recipient_rate` forward.
  Every re-ingest silently blanked 対象比率 in the weekly Excel (`20e360b`). The
  same carry-forward problem had already been handled once for
  `SchoolYearStatus` (`18bcd42`).
- Re-importing identical 対象比率 content still created a new revision each
  time (`6c874c3`).

### 4. Every operator action that changes state or produces an output writes its `manual_action_log` event in the same transaction, and a test asserts that event.

This covers decisions (approve, correct, reject, skip), settings saves, rebuilds,
previews, exports and bug reports, not only value edits. Use
`eidp.db.audit.log_manual_action` before the commit. Add a new `action_type` to
the audit vocabulary rather than reusing a vague one. The list of audited
action kinds is in `docs/governance/project-rules.md` ("Data Writes And Audit").

Why:
- School-code review approve, correct, reject and skip changed `School` and
  `ReviewItem` rows with no audit row (`364018c`). Department alias approvals
  (`8969ceb`) and fiscal-year override collateral demotions (`2154aee`) had the
  same gap.
- One day's sweep found nine more operator paths with no audit event: settings
  saves (`9900601`), Excel preview (`7ad57cc`), school task rebuilds
  (`22c3f7a`), operator URL registrations (`2d266c5`), prefecture remark
  decisions (`0ddc657`), Excel export (`c951655`), school alias approvals
  (`110bef2`), proposal decisions (`057bcb5`) and bug report generation
  (`51a3c77`).
- An empty manual entry backfilled `Document.fiscal_year` with no audit row
  (`43f0002`).

## Identity and matching

### 5. Match, join, dedupe and authorize on the full business identity. If more than one candidate fits, that is a review outcome, never a first match.

Never key on a field that siblings can share: a URL, a bare school name, a
department name without course, day/evening and duration, or an alias string
alone. When a looser key is added so that spelling variants join, also add the
collision check that stops it from joining two real entities. If a key maps to
more than one row, return an explicit ambiguous status and route it to review.
Do not return `.first()`.

Why:
- The verified-only apply gate used a URL-only set. One verified school
  authorized a sibling school that shared the same disclosure URL (`afe843a`,
  `docs/reports/2026-04-27-sprint1-B2-review.md`, P0).
- The alias index was "first wins", so an alias pointing at two schools
  resolved to whichever row came first (`6b3362a`).
- Similarity and substring gates promoted a parsed name to an alias of a
  different, existing school (`7f1ec5f`). A branch campus was aliased to its
  main campus, which would have written data to the wrong school (`070f948`).
  Cross-school and sibling-school PDF and homepage matches also slipped through
  (`3368047`, `8542a32`, `f14a49f`).
- On the master workbook, the `school | department | FY | metric` key has
  10,605 collisions. Even the richest key has 84, so Goal 4 was blocked until
  ambiguity was reported (`docs/reports/linux-web-v1-key-collision-audit.md`).
- Loosening `department_key` caused false merges twice. The bare コース fold
  certified different granularities as MATCH (`a7e1b16`), and `学科` collapsed
  to the 1-character key `学` (`ebe96a8`).

### 6. Each business definition lives in one place, and both sides of a comparison call it.

Normalizers (school name, course, department key), "current row" or "latest
year" queries, confidence thresholds and their labels, join keys and gate
criteria each have one owner module. Other code imports it. If you find a
second copy, delete it and call the owner; do not "fix" the copy. Always
normalize both sides of a lookup with the same function.

Why:
- The Excel master and the PDF ingest normalized course names differently
  (`工業` vs `工業専門課程`). An accepted PDF created duplicate department rows
  and split one school's workbook output into 4 rows (`e914386`). The fix moved
  the normalizer into `src/eidp/department_normalization.py` for both sides
  (`691b010`).
- Exact-string school lookup across sheets lost 661 対象比率 rows and 247
  学科別 rows (`docs/manual-intervention-log.md` §2). Parser whitespace made
  7 mismatch documents fail identity (`2038abc`). Excel diff soft keys were not
  normalized (`0e3f983`).
- The コース collision guard existed in `excel/master_diff` but not in the two
  pipeline diff engines, which produced the 2026-07 false merge. The join core
  was then extracted to `src/eidp/pipeline/department_join.py` (`cb08333`).
- Four near-duplicate "latest excluded schools" subqueries were replaced by one
  helper (`234fcb0`). A caller that still kept its own version was wrong
  (`6c874c3`).
- Confidence thresholds were retyped as literals (`2128202`), including a
  hardcoded 0.85 SR confidence (`59fb3b7`). Preview confidence labels had
  drifted too (`b76da32`).

## Failure visibility and writes

### 7. Nothing disappears silently. Every input row leaves a stage as output or as a counted reject with a reason, and every caught exception becomes a visible outcome.

Joins that feed reports keep the master side (a LEFT JOIN from the entity
table) and show missing data as NULL, not as a missing row. Rows a parser or
exporter cannot place go to a gap or reject output with a business reason.
Stale gap files are rewritten even when the new result is empty. An `except`
block must log with a traceback and set a status or reason code, or re-raise.
Returning an empty default is not enough. Unknown enum or config values fail
fast. This is the code-level form of goal G3 in `CLAUDE.md`.

Why:
- An inner join to `school_year_status` dropped every school without a status
  row from 採録状況 (`eaf5f5e`).
- A single-block parser dropped every school in the right-hand comparison block
  (`c0b7ffd`). `no_fy_data` rows were dropped from the gap report (`4580f6d`),
  and a zero-gap run left the previous gap CSV in place (`c4ad0cd`).
- A redirect-loop error was swallowed by an outer `except`, so a site reported
  0 PDF candidates when it had 1 (`eac66d2`). Dashboard counts and the fiscal
  year sidebar swallowed exceptions and showed a clean screen over real
  failures (`e23e149`).
- An unknown search provider was skipped silently (`19c40a4`). An unknown entry
  method silently took the OCR branch and was written into
  `extraction_method` (`5b62d52`).

### 8. Writes happen only when the caller explicitly asked for them, and only after every check has passed.

Batch and CLI writers are dry-run by default. `--apply` is the only switch that
writes; there is no `--no-dry-run` style second path. An apply step names the
exact input artifact that was reviewed (for example a verification file) and
never picks the "latest" one. Inside a write function, run every validation and
every no-op short-circuit before the first mutation of the DB or filesystem.

Why:
- `prefecture-aggregate --no-dry-run` without `--apply` called
  `apply_writer_plan()` and committed (`02ae97f`, P0).
- Apply picked the latest verification artifact automatically. A new
  verification batch silently changed the scope of an owner-approved apply
  (`7fd6bae`).
- `save_manual_entries(entries=[])` backfilled `Document.fiscal_year` before
  reaching its empty-input return (`43f0002`). The unknown-method case in
  `5b62d52` wrote before it validated.
