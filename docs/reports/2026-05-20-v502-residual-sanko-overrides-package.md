# v502 Residual Sanko URL Override Package Evidence

Date: 2026-05-20
Branch: `sprint8-handoff-finalize`
Package: `dist/eidp-windows-v502.zip`
Package source commit: `dd1524c48240890a8260795b54259342d7648867`
Package SHA256: `6764d4ee67dfd4db42272e87cbebb1b3c63c743d8388004b607b9b8590b41c05`

## Verdict

`MAC_SIDE_PACKAGE_VERIFIED_AND_PARTIAL_WINDOWS_VALIDATED_BELOW_GATE`.

v502 packages the v501 limit-50 RCA follow-up that removes the remaining
`non_target_candidates_only` Sanko corporation-root bucket from the bounded
FY2026/R8 canary. It is not v1.0 approval, and it is not yet the latest full
Windows-smoke package. v501 remains the latest package with complete Windows
setup, validate, recovery, OCR runtime, UI, Excel, and Stage 6 bundle evidence
until v502 full smoke finishes.

## Change

- `data/url-discovery/school_domain_overrides.csv`: added 2 exact Sanko school
  site rows for the residual v501 corporation-root cases.
- `tests/unit/test_url_discovery.py`: extended the checked-in Sanko override
  coverage test to include those rows.

| Residual URL | Purpose |
| --- | --- |
| `https://www.sanko.ac.jp/okinawa-sports/` | Replaces Sanko corporation-root crawling for the Okinawa resort/sports school |
| `https://www.sanko.ac.jp/tachikawa-beauty/` | Replaces Sanko corporation-root crawling for the Tokyo beauty/bridal school |

## Verification

| Check | Result |
| --- | --- |
| Live URL/title probe | Both candidate URLs returned HTTP `200` and matching Sanko school titles on 2026-05-20 |
| CSV duplicate check | `106` rows, `106` unique `(prefecture, corporation, school, domain_url)` keys, `0` duplicates |
| Targeted URL discovery test | `uv run pytest tests/unit/test_url_discovery.py::test_checked_in_school_domain_overrides_cover_sanko_exact_school_sites -q` -> `1 passed` |
| URL discovery suite | `uv run pytest tests/unit/test_url_discovery.py -q` -> `28 passed` |
| URL + weekly target-year suites | `uv run pytest tests/unit/test_url_discovery.py tests/unit/test_run_weekly_target_year_discovery.py -q` -> `58 passed` |
| Ruff on touched test | `uv run ruff check tests/unit/test_url_discovery.py` -> pass |
| v502 core verifier | `logs/win-v502-stage6-v502-verify-windows-distribution-20260520.json` -> `ok=true` |
| v502 core + OCR add-on verifier | `logs/win-v502-stage6-v502-verify-windows-distribution-with-ocr-addon-20260520.json` -> core `ok=true`, OCR add-on `ok=true` |
| v502 full non-Windows release gate | `logs/win-v502-stage6-v502-non-windows-release-gates-20260520.json` -> `ok=true`, package/source fresh, full unit suite `1880 passed` |
| v502 Windows setup/validate/recovery | `logs/win-v502-stage6-v502-preflight-20260520.json`, `logs/win-v502-stage6-v502-env0-validate-after-setup-20260520.json`, and `logs/win-v502-stage6-v502-env0-recovery-expected-v485-clean-20260520.json` -> `ok=true`; active lane remains v485 |
| v502 Windows limit-50 canary | `logs/win-v502-stage6-v502-last-run-after-weekly-canary-limit50-20260520.json` -> strict/Excel-ready `10.0%`, operator-reviewable `84.0%`, `ship_gate_status=below_gate` |

## v501 To v502 Limit-50 Delta

| Metric | v501 | v502 |
| --- | ---: | ---: |
| Strict / Excel-ready FY2026 yield | `10.0%` | `10.0%` |
| Operator-reviewable yield | `80.0%` | `84.0%` |
| RCA `non_target_candidates_only` bucket | `2` | `0` |
| RCA `target_form_without_year_evidence` bucket | `3` | `4` |

v502 confirms the residual Sanko URL fix moved the last Sanko corporation-root
false-discovery cases out of `non_target_candidates_only`. The strict FY2026/R8
release line remains blocked because the canary is still below `60.0%`.

## Remaining v502 Windows Work

v502 full Windows smoke is still pending because the Windows OpenSSH service
started resetting new SSH sessions after the partial canary. The remaining
automated checks are UI smoke, Stage 6 evidence-bundle collect/verify, final
recovery probe, and local evidence pullback. This is an environment transport
blocker, not evidence that v502 package behavior failed.
