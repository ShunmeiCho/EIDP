# EIDP Current Release Status

Updated: 2026-05-12
Branch: `sprint8-handoff-finalize`
Current Mac-verifier-clean package: `dist/eidp-windows-v320.zip`
Package commit: `17413896efc7ed58e76a42841287d2de934d9f26`
Package SHA256: `1b5b3bfecdd581bcb48b792310acbe62a66162d99e043b9f77899c82616a7c41`

## Verdict

Status: **NOT COMPLETE**

The code and package gates are in a strong non-Windows state, but the product
goal is not proven complete. The current package has not yet passed a current
Windows operator E2E click-through, and the actual national strict target-PDF
auto-acquisition rate is not proven to be 60-70%.

## Objective Checklist

| Requirement | Current evidence | Status |
| --- | --- | --- |
| 47 prefecture official indexes seed school public URLs | v320 verifier: `prefecture_seed_rows=47`, `prefecture_seed_parser_supported=47`, `prefecture_seed_downloadable=47`, `prefecture_seed_school_rows_total=2148` | Evidence present |
| Discover and download current target-FY PDFs in strict mode | v320 verifier clean; discovery gold-set `20` entries; expected predictions `20/20 exact`; package exposes `discovery_gold_undemonstrated_pattern_sources` and the CLI can fail on undemonstrated extractor sources | Partially proven |
| Exclude stale-year fallback from auto-success | Ship gate now uses operator-reviewable coverage, while strict auto-yield remains diagnostic; gold-set includes publication-lag cases | Partially proven |
| Extract with pdfplumber/PyMuPDF/Tesseract and write only confidence >= 0.70 rows | Unit/package gates cover OCR runtime presence and confidence contracts, but no current Windows operator E2E has revalidated the whole extraction-to-Excel path on v320 | Partially proven |
| Append-only DepartmentYearly / SupportRecipient writes | Fresh non-Windows audit: targeted Ruff clean and append-only/confidence/fiscal-year tests `116 passed`; source inspection confirmed demote-plus-new-revision paths in ingest, manual entry, and fiscal-year override | Evidence present, Win E2E still missing |
| Excel template output | Package verifier includes Excel/export contracts; current operator-PC preview/download flow is not revalidated on v320 | Partially proven |
| ManualActionLog audit for operator actions | Package verifier includes audit contracts and outbox checks; current operator-PC run not revalidated on v320 | Partially proven |
| ZIP distribution, double-click setup, browser UI offline operation | v320 ZIP verifies clean on macOS packaging gate and includes both Windows runbook and operator E2E evidence template; latest Windows setup-verified evidence is older than v320 | Missing current Win proof |
| Shipping threshold: true target PDF 60-70% auto-acquired, operator manual work <=30% | v320 includes `eidp report ship-readiness --fail-on-missing-goal`, records it in `EIDP-diagnose.bat`, and packages the operator E2E evidence template; current local DB is not initialized, so real nationwide result remains unmeasured | Missing |

## Current Non-Windows Evidence

Commands run for v320:

- `uv run pytest tests/unit -q` -> `1317 passed, 5 warnings`
- `uv run eidp eval-discovery-gold --predictions data/discovery-gold-set/expected-predictions.jsonl --fail-on-regression --json` -> `20/20 exact`
- `uv run python scripts/verify_windows_distribution.py dist/eidp-windows-v320.zip` -> `OK core`
- `zipinfo -1 dist/eidp-windows-v320.zip | rg "docs/runbooks/eidp-(windows|operator-e2e-template)\.md"` -> both runbook files present
- `uv run pytest tests/unit/test_windows_packaging_spike.py tests/unit/test_windows_distribution_verifier.py -q` -> `143 passed`
- `uv run eidp report ship-readiness --json --fail-on-missing-goal` -> exit `2` with `database_not_ready` on the uninitialized local DB
- `uv run eidp discovery-gold-set --json` -> `pattern_source_counts={"wordpress_download_manager": 1}`
- `uv run eidp discovery-gold-set --json --fail-on-undemonstrated-pattern-sources` -> non-zero with the same `undemonstrated_pattern_sources` payload
- `uv run ruff check tests/unit/test_current_read_paths.py tests/unit/test_fiscal_year_override.py` -> `All checks passed`
- `uv run pytest tests/unit/test_ingest_confidence_gating.py tests/unit/test_manual_entry_contract.py tests/unit/test_fiscal_year_override.py tests/unit/test_extraction_confidence.py tests/unit/test_current_read_paths.py -q` -> `116 passed`

v320 verifier exposes the current demonstration gap:

- Demonstrated extractor source: `wordpress_download_manager`
- Not yet gold-demonstrated: `data_attribute`, `embed`, `form_action`,
  `input_control`, `meta_refresh`, `onclick`, `select_option`

## Next Required Proof

1. Run current package on Windows operator PC or VM:
   `EIDP-setup.bat` -> `EIDP-start.bat` -> browser UI smoke -> diagnostics.
2. Execute a bounded official-index discovery run and record:
   target PDFs accepted, publication-lag queue, manual-required queue, and errors.
3. Compare the measured auto-acquisition and manual workload against the
   60-70% / <=30% shipping line.
4. Only after those numbers pass should the branch be treated as release-ready.
