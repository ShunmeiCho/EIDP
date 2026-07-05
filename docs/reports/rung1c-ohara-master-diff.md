# Rung 1c — 大原学園 FY2025 master-diff acceptance

**Result: `RUNG_1C_PASS_WITH_MASTER_AUDIT_REQUIRED`** (7-school clean gate) — **10-school target NOT met**.

- 7 of the 11 enrolled candidates clear the enrollment + intl_students hard gate (diff=0, no
  ambiguity, no missing/unexpected, no loose-key collision) and form the Rung 1c gated set.
- 06 盛岡校 is a documented `master_expected_error` (owner correction), kept out of the clean gate.
- 09/10/12/13 are `department_key_error` (master short-form 学科 key vs PDF verbose 学科+コース key);
  carried as non-gate reconciliation. Reaching 10 by loosening the department key would be a false
  merge — forbidden by the adversarial contract — so the count is reported honestly, not forced.

This is the "89 unmatched" class surfacing at small scale: not a value problem, a **key-granularity**
problem between master's aggregated 学科 and the PDF's per-コース split.

## 1. Selection — candidate pool and the 7-school clean gate

Candidate pool (user-specified): `01,02,03,05,08,09,10,12,13,15,16` (11 enrolled 大原 schools) plus
`06` carried as the sibling-pair finding. All 11 were run through the hardened pipeline
(extract → convert → collision-detect → 学科 align → diff → gate → reconciliation artifacts) against
`data/master.xlsx` (red-line, read-only). Selection is **empirical**, never reverse-inferred:

| Gated (clean) | Prefecture | Records | Hard gate | Reconciliation |
|---|---|---|---|---|
| 01 大原簿記情報専門学校札幌校 | 北海道 | 18 | diff=0 (15 exact) | 3 capacity |
| 02 大原法律公務員専門学校 | 北海道 | 6 | diff=0 (6 exact) | — |
| 03 大原医療福祉専門学校 | 北海道 | 12 | diff=0 (10 exact) | 2 capacity |
| 05 大原公務員・医療事務・語学専門学校函館校 | 北海道 | 9 | diff=0 (9 exact) | — |
| 08 大原ビジネス公務員専門学校山形校 | 山形県 | 12 | diff=0 (11 exact) | 2 taxonomy + 1 capacity |
| 15 東京情報クリエイター工学院専門学校 | 東京都 | 12 | diff=0 (12 exact) | 4 taxonomy + 1 skipped |
| 16 東京アニメーター学院専門学校 | 東京都 | 9 | diff=0 (9 exact) | 2 skipped |

**Rationale.** The 7 span all the risk types the gate must survive:
- **same-prefecture sibling discrimination** — 北海道 carries four 大原 schools (01/02/03/05); each pin
  binds its own campus by URL/PDF-header, and `prefecture` (G5) is a required second key so a sibling's
  master partition can never be loaded by mistake.
- **cross-prefecture name near-collision** — 02 大原法律公務員 (北海道) vs 12 大原法律専門 (東京都):
  prefecture discriminates.
- **中点 / label variation** — 05 大原公務員・医療事務・語学…, 16 文化教養 (中点-fold).
- **taxonomy cross-source delta** — 08 公務員学科 (文化教養↔商業実務), 15 情報/クリエイター (工業↔工業関係).
- **legacy blank rows** — 15 (1), 16 (2) skipped with recorded `skip_reason` (G1).

**Why not 10.** Only 7 candidates pass the clean gate. 09/10/12/13 diverge on department-key
granularity (see §6). Forcing them in would require widening the loose key into a false merge (12/13)
or collapsing distinct 年制 into one key (10) — both are exactly the fake-success vectors the
adversarial review forbids. The honest count is 7; the remaining 4 are classified, not hidden.

## 2. Authority basis

Every pin declares `source_type = human_confirmed_official_pdf` with 4 evidence kinds
(`source_page`, `pdf_url`, `url_year_hint`, `pdf_text_school_hint`). URL/path selects the file and the
fiscal year; the PDF 学校名 header corroborates identity only. `master.xlsx` is EXPECTED-OUTPUT
authority and appears in no pin's `authority_basis` — `ALLOWED_SOURCE_TYPES` structurally excludes it.
Every gated hard-gate actual value carries `source_cell = "page=..;table=..;row=..;col=.."` provenance
(asserted in `test_rung1c_seven_gated_schools_pass_hard_gate_with_evidence`).

## 3. Diff result — all 12 candidates

| Code | School | Pref | Status | exact | val_mis | miss | unexp | ambig | collision |
|---|---|---|---|---|---|---|---|---|---|
| 01 | 大原簿記情報札幌校 | 北海道 | pinned | 15 | 3(cap) | 0 | 0 | 0 | 0 |
| 02 | 大原法律公務員 | 北海道 | pinned | 6 | 0 | 0 | 0 | 0 | 0 |
| 03 | 大原医療福祉 | 北海道 | pinned | 10 | 2(cap) | 0 | 0 | 0 | 0 |
| 05 | 大原公務員・医療事務・語学函館校 | 北海道 | pinned | 9 | 0 | 0 | 0 | 0 | 0 |
| 08 | 大原ビジネス公務員山形校 | 山形県 | pinned | 11 | 1(cap) | 0 | 0 | 0 | 0 |
| 15 | 東京情報クリエイター工学院 | 東京都 | pinned | 12 | 0 | 0 | 0 | 0 | 0 |
| 16 | 東京アニメーター学院 | 東京都 | pinned | 9 | 0 | 0 | 0 | 0 | 0 |
| 06 | 大原ビジネス公務員盛岡校 | 岩手県 | master_finding | 11 | 1(enr) | 0 | 0 | 0 | 0 |
| 12 | 大原法律専門 | 東京都 | dept_key_error | 0 | 0 | 15 | 15 | 0 | 0 |
| 13 | 大原医療秘書福祉保育 | 東京都 | dept_key_error | 0 | 0 | 9 | 9 | 0 | 0 |
| 09 | 山形スポーツ医療福祉 | 山形県 | dept_key_error | 6 | 3 | 3 | 3 | 0 | 0 |
| 10 | 山形情報ITクリエイター | 山形県 | dept_key_error | 2 | 1 | 0 | 6 | 3 | 0 |

`val_mis(cap)` = capacity value_mismatch (reconciliation, non-blocking). `val_mis(enr)` = the 06 master Δ1.
For gated schools, capacity mismatches never touch the enrollment/intl gate (`HARD_GATE_METRICS` = {enrollment, intl_students}).

## 4. Reconciliation artifacts (non-blocking)

- **capacity_reconciliation** — 01 (3), 03 (2), 08 (1): 収容定員 vs 生徒総定員数 cross-source deltas,
  surfaced with the official PDF value, `operator_decision = needs_owner_decision`. Never zeroed.
- **taxonomy_reconciliation** — 08 公務員学科 1年制/2年制 (文化教養↔商業実務); 15 情報処理/クリエイター/
  高度情報処理/高度クリエイター (工業↔工業関係). 分野 divergence collapsed on unique 学科 identity so equal
  values still join; the divergence is recorded, not dropped.
- **skipped rows (G1)** — 15 工業|一年制専攻; 16 文化教養|漫画家プロ養成 + イラストレーション; 13 医療事務
  legacy rows. Each emitted as `SkippedDepartmentRow(skip_reason="blank_enrollment_legacy")` — recorded,
  never silently swallowed.

## 5. master_expected_error (06 盛岡校)

11/12 hard-gate comparisons exact → the pin binds 盛岡校, not sibling 山形校. The single failure is
公務員2年制 在籍 **master=91 vs official PDF raw "92人" (Δ+1)**. The extractor is proven correct; master
is a red-line file and is not edited here. Owner master-correction item (see §9), kept out of the clean gate.

## 6. department_key_error (09/10/12/13) — classified before any extractor change

Per the failure-classification rule, these were classified BEFORE touching the extractor:

- **12 大原法律専門 / 13 大原医療秘書福祉保育** — hard-gate **values match pairwise** (12: 法律行政 88/61/34;
  13: こども保育 34/13, 医療事務 25). Pure key granularity: master short-form `法律行政学科(初級事務系)` vs
  PDF verbose `法律行政学科2年制公務員初級事務系`. Fixable by an alignment fold OR an owner 学科 mapping —
  **not** by loosening the loose key (that over-merges). Cleanest reach-10 candidates.
- **10 山形情報ITクリエイター** — `ambiguous_key=3`: master short `情報IT` over-collapses PDF
  `情報IT学科(2年制)` / `(3年制)`. Needs a LESS-collapsing key (opposite direction), an owner decision.
- **09 山形スポーツ医療福祉** — mixed: `経理本科2年制` vs `経理本科2年制学科(情報)` key divergence PLUS a
  field/extractor gap (3 depts intl master=0 vs PDF=null). Needs both an alignment fold and an intl-cell fix.

None are master errors; none are value errors (except 09's intl-null extractor gap). All are carried as
non-gate reconciliation until an owner mapping or a scoped alignment slice resolves them.

## 7. Adversarial review

Independent 3-lens refutation workflow (identity-and-pin / department-key-and-merge /
value-and-reconciliation), each lens reading the actual code+tests+manifest to REFUTE that the 7-school
clean gate is real. **Result: 0 confirmed defects; the clean gate survived every fake-success vector.**

| Lens | Vector | Verdict |
|---|---|---|
| department-key-and-merge | false merge / duplicate records / over-collapse / empty key | all **refuted** |
| identity-and-pin | master-derived identity / sibling confusion / missing prefecture | **refuted** |
| identity-and-pin | wrong campus pin (PDF header not machine-checked vs pin) | **residual_risk** |
| value-and-reconciliation | capacity-as-enrollment | **refuted** (decisive: passing 7 prove no leak) |
| value-and-reconciliation | taxonomy/capacity silently dropped | **refuted** (G4 fall-through) |
| value-and-reconciliation | blank expected rows silently skipped (harness) | **residual → FIXED** |
| value-and-reconciliation | field alias overreach | **refuted** (ambiguous_key blocks) |

**Residual actions from the review:**
- **FIXED** — the Rung 1c gated harness now passes `skipped=` to the loader and asserts every skipped
  legacy-blank row carries a `skip_reason` (honors G1 inside the acceptance path, not just the loader unit test).
- **Latent (accepted design)** — no code cross-checks the PDF-body 学校名 header against the pinned
  `campus_key`; identity rests on `human_confirmed_official_pdf` authority. A machine header-vs-pin assertion
  is a future hardening item (Rung 2), not a Rung 1c blocker.
- **Latent** — `build_reconciliation_report` emits capacity only for `value_mismatch`, not missing/unexpected;
  N/A to the clean 7 (capacity present both sides), still surfaced via `GateReport.reconciliation`. Tighten in v1.1.


Structural refutations already encoded in the suite:
- master-derived identity → `ALLOWED_SOURCE_TYPES` excludes master (`pinned_manifest.py:38`); pins cite only URL/PDF-header.
- sibling confusion → `prefecture` required (G5) + used as loader filter; 北海道 01/02/03/05 each load own partition.
- false merge / duplicate collapse → `detect_department_key_collisions` (G2) asserted `== []` for all 7 gated; 12 asserted to stay failing.
- capacity-as-enrollment → `HARD_GATE_METRICS = {enrollment, intl_students}`; capacity only in `RECONCILIATION_METRICS`.
- silent drop → G1 `SkippedDepartmentRow` + G4 `ReconciliationArtifacts` surface every skip/recon; taxonomy rows `needs_owner_decision`.
- empty department key → `department_key` returns `stripped or normalized` (G3), never `""`.

## 8. Guardrail coverage (G1–G5, all green)

| G | Guardrail | Exercised by Rung 1c |
|---|---|---|
| G1 | explicit skip_reason, no silent skip | 15/16/13 legacy blanks recorded |
| G2 | loose-key collision blocks | all 7 gated assert `collisions == []` |
| G3 | empty-key guard | no `*|` empty gakka in any partition |
| G4 | structured reconciliation artifacts | capacity/taxonomy/master-error grouped |
| G5 | prefecture required in manifest | sibling discrimination for 北海道 cohort |

## 9. Tests + status

- `tests/integration/test_ohara_rung1c_master_diff.py` — 4 tests (structure + 7-gated + 06 finding + 12 dept-key). Green.
- Regression: Rung 1a/1b integration 5/5 green; guardrail + alias unit 87 green; `mypy src` clean; `ruff` clean.

**Final status: `RUNG_1C_PASS_WITH_MASTER_AUDIT_REQUIRED`** — 7/7 gated clean; 06 master audit required;
4 department_key_error deferred. **10-school target not met by clean gate** (honest count).

## 10. Owner decisions (parallel, non-blocking)

1. **06 master correction** — 公務員2年制 在籍 91 → 92 (official PDF authoritative). Red-line: owner edits master, not the pipeline.
2. **公務員学科 / 情報 taxonomy ownership** — 文化教養 vs 商業実務 (08); 工業 vs 工業関係 (15). Which 分野 is canonical?
3. **capacity column policy** — 収容定員 vs 生徒総定員数 reconciliation direction.
4. **department-key mapping (reach-10)** — authorize a scoped alignment fold for 12/13 (value-matching) and an owner 学科 mapping for 09/10, or accept 7 as the Rung 1c gate.

## Next recommended slice

Two honest paths (owner picks):
- **(a) Accept 7 as Rung 1c**, move to Rung 2 breadth (more corporations) — locks the clean-gate discipline before scaling.
- **(b) Reach-10 slice** — TDD a value-preserving department-key alignment for 12/13 (proven key-only) + an
  owner 学科 mapping table for 09/10, then re-gate. Brings 12/13 in cleanly; 09 also needs the intl-null extractor fix.
