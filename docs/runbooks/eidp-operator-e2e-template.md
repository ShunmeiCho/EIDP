# EIDP 業務員 PC E2E 記録テンプレート

Status: Stage 6 / v1.0 release candidate evidence template
Updated: 2026-05-19

このテンプレートは、業務員の実 PC で 1 サイクル実行した結果を記録するためのものです。
ここが未記入のままでは、EIDP Windows 版を v1.0 と判定しません。

判定上の注意:

- このテンプレートをすべて埋めることは、Windows 実機での process gate
  （v1.0-rc 候補）を確認するための条件です。
- FY2025/R7 retroactive evidence は、rolling target FY の切替と operator workflow
  の動作証明には使えますが、FY2026/R8 の current-year yield gate
  （真の対象年度 PDF 60-70% 自動取得、推定手作業 30% 以下）の証明には使いません。
- v1.0 GA 判定は、このテンプレートの完了に加えて、現在の対象年度で
  `ship_readiness_rc=0` または同等の yield evidence が確認された後に行います。
  Route A / `publication_lag` 例外を owner が承認する場合は、下記 KPI 判定の
  below-gate 行を `watch` として明示し、成熟年 proof と例外記録で補完します。
- Package-specific transfer/setup/UI evidence is recorded outside this reusable
  template in `docs/reports/current-release-status.md` and version-specific
  Stage 6 evidence drafts. Codex-driven smokes and bounded canaries are not a
  substitute for the owner/operator 1-cycle sign-off fields below.
- The next real-cycle Stage 6 should use the latest approved Windows lane from
  `docs/reports/current-release-status.md`. ZIP 内のこのテンプレートは
  自分自身の最終 SHA256 を持てないため、SHA256 は `.sha256` sidecar または
  release-status の値を転記します。
- version-specific transfer steps, package SHA256, and release-gate logs are
  recorded in the current release-status documents and may be copied here after
  execution. Treat package-embedded copies of this template as stale if they were
  built before the latest evidence lane.

## 1. 実施情報

| 項目 | 記録 |
| --- | --- |
| 実施日 | |
| 実施場所 | |
| 業務員 | |
| Owner 立会い | |
| EIDP commit / tag | |
| core ZIP ファイル名 | |
| core ZIP sha256 | |
| OCR add-on ZIP sha256 | |
| Playwright add-on ZIP sha256 | |
| `windows-distribution-verification.json` 保存場所 | |

<!-- verifier compatibility token: 現行投入候補（Mac / non-Windows gate 済み、Windows 未実証）: -->
現行投入候補（package / validation status は current release-status と
version-specific owner request を正とする）:

| 項目 | 値 |
| --- | --- |
| EIDP package snapshot | `<package git commit>` |
| core ZIP | `dist/eidp-windows-vXXX.zip` |
| core ZIP sha256 | `<copy from dist/eidp-windows-vXXX.zip.sha256>` |
| core ZIP sha256 sidecar note | `.sha256` は repo-relative path を記録する。 |
| non-Windows gate log | `logs/release-gate-vXXX-retroactive.json` or `logs/release-gate-vXXX.json` -> ok=true |
| docs-only stale gate | Use only after docs-only commits; record the exact gate JSON here. |
| Windows transfer checklist | `<version-specific real-cycle-card path>` |
| Windows extract path | `C:\Users\<user>\<EIDP-extract-dir>` |
| transferred ZIP | `C:\EIDP-staging\<core-zip-file-name>` |
| Stage 6 evidence draft | `<version-specific evidence draft path>` |
| real-cycle entrypoints | ZIP and extracted Windows root both contain `EIDP-start.bat`, `EIDP-setup.bat`, `EIDP-stage6-evidence.bat`, `EIDP-stage6-verify-evidence.bat`, `EIDP-diagnose.bat`, `scripts\weekly_run.bat`, `scripts\validate_install.bat`, `scripts\stage6_recovery_check.bat`, and `scripts\diagnose.bat` |

## 2. PC / 環境

| 項目 | 記録 |
| --- | --- |
| Windows version | |
| 日本語ロケール | yes / no |
| 既定 console encoding | |
| CPU core 数 | |
| RAM | |
| 空きディスク | |
| Defender 状態 | enabled / disabled |
| SmartScreen 表示 | none / shown |
| ネットワーク | 社内 / VPN / offline / other |
| Proxy / FW 影響 | none / observed |

既存環境証跡（要再確認、version-specific evidence draft から転記）:

| 項目 | 値 |
| --- | --- |
| Hostname / user | |
| Home | |
| Windows version | |
| Locale | |
| Console encoding | |
| CPU/RAM | |
| C drive free | |
| Defender | |
| SmartScreen | |
| Network / proxy | |
| Evidence JSON | |

### 2.1 実行前 preflight

Owner/operator real cycle の前に、PowerShell で以下を実行して結果を転記します。
この preflight は業務データを書き換えません。`C:` の空き容量、DNS cache、既存 lock、
Task Scheduler retry 設定を確認してから setup / weekly run に進みます。

| 項目 | 期待 | 結果 | 証跡 |
| --- | --- | --- | --- |
| Disk preflight | `Get-Volume C` の空き容量が 5GB 以上 | pass / fail | |
| DNS flush | `ipconfig /flushdns` exit code 0 | pass / fail | |
| lock-file check | `data\.lock` / `data\.lock.meta` が無い、または recovery check で安全確認済み | pass / fail | |
| Task Scheduler retry | `EIDP Weekly Run` の retry 設定と next run を確認 | pass / fail | |
| Task Scheduler retry screenshot | タスク設定画面または XML を保存 | pass / fail | |

```powershell
cd C:\Users\<user>\<EIDP-extract-dir>
$root = (Get-Location).Path
$volume = Get-Volume C
if ($volume.SizeRemaining -lt 5GB) {
  throw "C drive free space is below 5GB: $($volume.SizeRemaining)"
}

ipconfig /flushdns
echo $LASTEXITCODE

Get-ChildItem "$root\data\.lock*" -Force -ErrorAction SilentlyContinue
if ((Test-Path "$root\data\.lock") -or (Test-Path "$root\data\.lock.meta")) {
  .\scripts\stage6_recovery_check.bat .\scripts\weekly_run.bat --json
  echo $LASTEXITCODE
}

Get-ScheduledTask -TaskName "EIDP Weekly Run" | Select-Object TaskName,State
Get-ScheduledTaskInfo -TaskName "EIDP Weekly Run" |
  Select-Object LastRunTime,LastTaskResult,NextRunTime
schtasks /query /tn "EIDP Weekly Run" /xml > "$root\logs\task-scheduler-eidp-weekly-run.xml"
```

## 3. 証跡採取コマンド

PowerShell で実行し、exit code と出力ファイル名を記録します。パスは実際の
解凍先に合わせて置き換えます。

```powershell
cd C:\Users\<user>\<EIDP-extract-dir>
$zip = "C:\EIDP-staging\<core-zip-file-name>"
$expected = "<copy SHA256 from .sha256 sidecar or current-release-status>"
$actual = (Get-FileHash $zip -Algorithm SHA256).Hash.ToLowerInvariant()
if ($actual -ne $expected) { throw "SHA256 mismatch: $actual" }
.\EIDP-setup.bat
echo $LASTEXITCODE
.\scripts\validate_install.bat --after-setup
echo $LASTEXITCODE
Select-String -Path .\scripts\launch.bat -Pattern "streamlit.main| -m streamlit run"
.\EIDP-start.bat
```

Mac preflight（転送前に実施）:

```text
shasum -a 256 -c dist/eidp-windows-vXXX.zip.sha256 -> dist/eidp-windows-vXXX.zip: OK
logs/release-gate-vXXX-*.json -> ok=true
package/source freshness, source_dirty, stale/docs_only_stale, validator slice,
mypy, ruff, discovery-gold, and package verifier results are copied from the
current release-status / release-gate JSON.
```

Mac / Playwright から業務員 PC のブラウザ UI を確認する場合は、既定 launcher
port `8501` に対して local tunnel を張ります。`Host win` で
`ClearAllForwardings yes` が有効な環境では、必ずコマンドラインで上書きします。

```bash
ssh -N -o ClearAllForwardings=no -o ExitOnForwardFailure=yes -L 127.0.0.1:18501:127.0.0.1:8501 win
curl http://127.0.0.1:18501/_stcore/health
```

手動で Streamlit を `--server.port 8502` 起動した検証だけ、local `18502` から
Windows `8502` へ転送します。通常の `EIDP-start.bat` / `scripts\launch.bat`
検証では `18501 -> 8501` を使います。

PDF 収集を実測した後に、診断ファイルを作ります。

```powershell
.\EIDP-diagnose.bat
echo $LASTEXITCODE
Get-ChildItem .\logs\diagnostics-*.txt | Sort-Object LastWriteTime -Descending | Select-Object -First 1
Get-ChildItem .\data\output\last_run.json
Get-ChildItem .\data\output\target-year-discovery\*-discovery-rca-batch-plan.json
```

`diagnostics-*.txt` から最低限以下を転記します。

- `validate_after_setup_rc`
- `validate_after_bootstrap_rc`
- `validate_after_bootstrap_ship_gate_rc`
- `ship_readiness_rc`
- `target_pdf_auto_yield_pct`
- `strict_target_pdf_auto_yield_pct`
- `target_pdf_excel_ready_yield_pct`
- `broad_target_pdf_auto_yield_pct`
- `operator_reviewable_yield_pct`
- `excel_ready`
- `ship_gate_status`
- `retroactive_fiscal_year`
- `is_retroactive_fiscal_year`
- `retroactive_ship_readiness_rc`
- `stage6_recovery_rc`
- `[stage6 recovery check]` JSON の `task.execute`
- `[stage6 recovery check]` JSON の `task.expected_action`
- `[stage6 recovery check]` JSON の `task.action_matches_expected`
  （`task.expected_action` が `null` の場合は scheduled task action path 検証を skip）
- `[stage6 recovery check]` JSON の `residual_paths`
- `[stage6 recovery check]` JSON の `recommendations`

v454 既存証跡（diagnostic-only、operator real-cycle の代替不可）:

```text
logs\run-20260516.log
data\output\last_run.json
logs\stage6-recovery-20260516-113412-expected-action.json
logs\stage6-residual-cleanup-*.json
logs\stage6-evidence-20260516-023620.zip
logs\stage6-evidence-verify-*.json
```

Default launcher smoke:

```text
EIDP-start.bat -> scripts\launch.bat -> Windows 127.0.0.1:8501
Mac tunnel 127.0.0.1:18501 -> 127.0.0.1:8501
/_stcore/health=ok; root path returned Streamlit HTML shell
The process was force-stopped after the health proof; launcher exit -1 is a stop artifact, not a startup failure.
```

## 4. Setup 結果

| 手順 | 期待 | 結果 | 証跡 |
| --- | --- | --- | --- |
| ZIP 解凍 | 任意パスで解凍できる | pass / fail | |
| `EIDP-setup.bat` | exit code 0 | pass / fail | |
| `.venv` 作成 | `.venv\Scripts\python.exe` が存在 | pass / fail | |
| DB bootstrap | `data\eidp.sqlite3` が存在 | pass / fail | |
| master import | 学校マスタが取り込まれる | pass / fail | |
| 年度タスク初期生成 | `school_fiscal_year_status` に行がある | pass / fail | |
| Task Scheduler | `EIDP Weekly Run` が登録される | pass / fail | |
| launcher entrypoint | `streamlit.main` が無く、`-m streamlit run` がある | pass / fail | |
| `launch.bat` | Streamlit 起動 | pass / fail | |
| Mac tunnel health | `http://127.0.0.1:18501/_stcore/health` が `ok` | pass / fail / n/a | |
| `学校別タスク` 初期表示 | 業務員クイックの最初のページとして表示 | pass / fail | |
| `詳細 operator` 折りたたみ | 詳細ページは通常折りたたみ表示 | pass / fail | |

v459 既存証跡（転記候補。bounded diagnostic-only。operator real-cycle の代替不可）:

| 手順 | 結果 | 証跡 |
| --- | --- | --- |
| ZIP 解凍 | pass | `%USERPROFILE%\EIDP-v459-50152a5` |
| `EIDP-setup.bat` | pass | setup completed; SQLite integrity ok |
| `.venv` 作成 | pass | `validate_windows_install.py --after-setup --json` |
| DB bootstrap / master import | pass | `school_count=2418`, `sqlite_integrity_check=ok` |
| 年度タスク初期生成 | pass | `school_fiscal_year_status_count=2418` |
| Task Scheduler recovery | pass | expected action `%USERPROFILE%\EIDP-v459-50152a5\scripts\weekly_run.bat`, `action_matches_expected=true` |
| cleanup tooling | pass | `rotate_audit_outbox.py --json` rotate false; `prune_pdf_storage.py --json` candidate count 0 |
| URL-only bootstrap | pass | 47 prefectures; `school_domain_overrides.csv` loaded; `school_override_inferred=6`; `corporation_inferred=296` |
| bounded `weekly_run.bat` canary | pass | `rc=0`, `run_id=20260516_060230`, `crawled=5`, `found=5`, `downloaded=2`, `operator_reviewable_count=5`, `ship_gate_status=pass` |
| Evidence bundle verify | pass | `%USERPROFILE%\EIDP-v459-50152a5\logs\stage6-evidence-20260516-070115.zip`, `ok=true`, `entry_count=12`, no missing required labels; Mac copy SHA256 `c4e68ee5b5f8c1cb8b74938fb369edf4c53c00efdd5624bac3c05e51ab7caf28` |
| Default launcher health | pass | root `EIDP-start.bat`, Windows `8501`, health/root HTTP 200, cleanup left no listener |
| Browser navigation | pass | `① 学校別タスク`, `② PDF確認・手入力`, `④ Excel プレビュー`, `⑤ 設定（年度・OCR・API）` rendered under `output/playwright/v459-ui-smoke/`; `summary.json` recorded `navAllClicked=true`, `hasErrorTraceback=false`; tunnel and Windows listener were cleaned up |
| R7 browser Excel | pass | process-scoped `EIDP_TARGET_FISCAL_YEAR=2025`, `Excel出力可 2`, `Excel対象行 7177`, downloaded `output/playwright/v459-r7-excel-smoke/eidp_master.xlsx`; workbook dimensions `2419x10`, `10025x22`, `9748x83`, `9748x19`; checked `.env` paths absent |
| Browser UI write/audit sandbox | pass | v459 disposable DB rejected `review_item#37` in `URL候補レビュー`, flushed `exported=2 already_present=0 failed=0`, saved `logs/win-v459-stage6/v459-ui-write-sandbox-result-final.json`, and left real runtime DB marker counts `0` |
| Disk health | pass | Mac and Win both `warn_count=0`, `block_count=0`; v459 current plus v454 fallback retained |

v456 既存証跡（historical。bounded diagnostic-only。UI write sandbox も v456 で実施済み）:

| 手順 | 結果 | 証跡 |
| --- | --- | --- |
| ZIP 解凍 | pass | `%USERPROFILE%\EIDP-v456-f33ffc0` |
| `EIDP-setup.bat` | pass | setup completed; SQLite integrity ok |
| `.venv` 作成 | pass | `validate_windows_install.py --after-setup --json` |
| DB bootstrap / master import | pass | `school_count=2418`, `sqlite_integrity_check=ok` |
| 年度タスク初期生成 | pass | `school_fiscal_year_status_count=2418` |
| Task Scheduler recovery | pass | expected action `%USERPROFILE%\EIDP-v456-f33ffc0\scripts\weekly_run.bat`, `action_matches_expected=true` |
| URL-only bootstrap | pass | 47 prefectures; `school_domain_overrides.csv` loaded with `count=6` |
| bounded `weekly_run.bat` canary | pass | `rc=0`, `crawled=5`, `found=5`, `downloaded=2`, `operator_reviewable_count=5`, `ship_gate_status=pass` |
| Evidence bundle verify | pass | `logs/win-v456-stage6/stage6-evidence-20260516-034752.zip`, all required labels present |
| Default launcher health | pass | `scripts\launch.bat`, Windows `8501`, Mac tunnel `18501 -> 8501`, health/root HTTP 200 |
| Browser navigation | pass | Historical read-only nav support under `output/playwright/v456-ui-smoke/`; superseded by current v459 nav proof |
| R7 browser Excel | pass | Historical R7 Excel browser support under `output/playwright/v456-r7-excel-smoke/`; superseded by current v459 R7 Excel proof |
| Browser UI write/audit sandbox | pass | Historical URL-candidate reject / audit flush support under `logs/win-v456-stage6/v456-ui-write-sandbox-result-final.json`; superseded by current v459 UI write/audit sandbox proof |

## 5. 4 工程 E2E

### 工程 1: PDF 収集

| 指標 | 値 |
| --- | ---: |
| 対象学校数 | |
| HTTP 成功数 | |
| HTTP 失敗数 | |
| 新規 PDF 数 | |
| 重複スキップ数 | |
| school_mismatch 件数 | |

メモ:

```text

```

### 工程 2: 対象年度判定

| 指標 | 値 |
| --- | ---: |
| 対象年度 自動判定数 | |
| 年度修正 数 | |
| override 後の coverage / Excel 突合 | pass / fail |
| review_pending 文書数 | |

v408 sandbox 例（real-cycle ではない）:

| Document ID | 旧年度 | 新年度 | 理由 | audit action_id |
| --- | ---: | ---: | --- | --- |
| `2` | 2024 | 2025 | `stage6 v408 UI sandbox fiscal year override` | `4`-`7` |

override 例:

| Document ID | 旧年度 | 新年度 | 理由 | audit action_id |
| --- | ---: | ---: | --- | --- |
| | | | | |

### 工程 3: 転記 / 手入力 / OCR

| 指標 | 値 |
| --- | ---: |
| pdf_parse 成功行数 | |
| OCR 実行 PDF 数 | |
| OCR 自動成功 PDF 数 | |
| confidence >= 0.85 行数 | |
| 0.70 <= confidence < 0.85 行数 | |
| 0.50 <= confidence < 0.70 行数 | |
| confidence < 0.50 行数 | |
| 手入力件数 | |
| DepartmentChange 明示登録件数 | |
| 抽出済「確認・補足」実押し検証 | pass / fail |

> ① fix（学科二重化）実環境検証（必須・1 回）:
> 自動抽出済の 1 校で「抽出済内容を確認・補足」を実際に開き、無編集のまま保存する。
> 保存後に Excel プレビュー（学科別シート）で **その学科が二重化していない**こと（1 行のまま、
> 課程名が保持される）を目視確認し、上行に `pass`/`fail` を記入する。二重化したら release を止める。
> 根拠: ユニットテストは緑だが、この UI 経路の実データ発火は本検証で初めて閉じる。

低 confidence / 手入力 例:

| Document ID | 学校 | 学科 | confidence | 対応 | audit action_id |
| --- | --- | --- | ---: | --- | --- |
| | | | | | |

v408 sandbox 例（real-cycle ではない）:

| Document ID | 学校 | 学科 | confidence | 対応 | audit action_id |
| --- | --- | --- | ---: | --- | --- |
| `1` | `EIDP v408 sandbox 専門学校` | `V408手入力学科` | `1.0` | manual entry, verified | `1`-`3` |

### 工程 4: Excel プレビュー / 出力

| 指標 | 結果 |
| --- | --- |
| Excel preview 表示 | pass / fail |
| `data\output\*.xlsx` 生成 | pass / fail |
| 日本語 sheet 名 | pass / fail |
| 日本語セル値 | pass / fail |
| Excel 占有エラー表示 | pass / fail |
| coverage と Excel の対象比率一致 | pass / fail |
| 採録状況 sheet と current DB 一致 | pass / fail |

出力ファイル:

```text

```

v456 R7 retroactive 既存証跡（FY2026 yield ではない）:

| 指標 | 結果 |
| --- | --- |
| R7 browser download | `output/playwright/v456-r7-excel-smoke/eidp-master.xlsx`, suggested `eidp_master.xlsx` |
| Sheet counts | `採録状況=2418`, `対象比率=10024`, `学科別=9746`, `在籍のみ抜粋=9746` |
| openpyxl dimensions | `2419x10`, `10025x22`, `9748x83`, `9748x19` |
| FY persistence check | v456 root/adjacent `.env` missing after process-scoped `EIDP_TARGET_FISCAL_YEAR=2025` launch |

Historical Mac retroactive Excel matrix（FY2026 yield ではない。Windows 実走時の比較基準）:

| FY | Gate log | 判定 | Business diff | Export rows |
| ---: | --- | --- | --- | --- |
| 2025 | `logs/release-gate-v437-retroactive-fy2025-reference.json` | pass | `missing_rows=0`, `extra_rows=0`, `differing_fields=0` | `採録状況=2418`, `対象比率=10022`, `学科別=9719`, `在籍のみ抜粋=9719` |
| 2024 | `logs/release-gate-v437-retroactive-fy2024-reference.json` | pass | `missing_rows=0`, `extra_rows=0`, `differing_fields=0` | `採録状況=2418`, `対象比率=10022`, `学科別=9719`, `在籍のみ抜粋=9719` |
| 2023 | `logs/release-gate-v437-retroactive-fy2023-reference.json` | pass | `missing_rows=0`, `extra_rows=0`, `differing_fields=0` | `採録状況=2418`, `対象比率=10022`, `学科別=9719`, `在籍のみ抜粋=9719` |

## 6. KPI 判定

> publication_lag 例外を使う場合の verdict 記入指針:
> FY2026/R8 が未公開で below-gate になる行（`ship_readiness_rc` / `strict target PDF 自動取得率` /
> `推定手作業率` / `Excel ready 率`）は、目標未達でも **`watch`** と記入する（`fail` ではない）。
> `verify_stage6_return.py` は publication_lag 下でこれらの `watch` を受理する（各行 `pass` / `watch` のみ可、`fail` は不可）。
> 例外を使わない通常 GA では従来どおり `pass` 必須。

| KPI | Target | Actual | 判定 |
| --- | ---: | ---: | --- |
| 新規 PDF 取得数 | 記録値 | | pass / watch / fail |
| 対象年度 自動判定成功率 | >= 90% | | pass / watch / fail |
| OCR 自動成功率 | >= 70% | | pass / watch / fail |
| HTTP 成功率 | >= 95% | | pass / watch / fail |
| Excel 整合性 | 100% | | pass / watch / fail |
| 業務員週次作業時間 | <= 4h | | pass / watch / fail |
| 手入力件数 | 記録値 | | pass / watch / fail |
| review_pending 残件 | 記録値 | | pass / watch / fail |
| `ship_readiness_rc` | 0 | | pass / watch / fail |
| strict target PDF 自動取得率 | >= 60% | | pass / watch / fail |
| 推定手作業率 | <= 30% | | pass / watch / fail |
| release exception reason | blank or `publication_lag` | | pass / watch / fail |
| mature-year proof JSON | required when exception is used | | pass / watch / fail |
| mature-year proof years | at least one FY before current target FY | | pass / watch / fail |
| Excel ready 率 | >= 60% | | pass / watch / fail |
| retroactive FY 診断年度 | 記録値 | | pass / watch / fail |
| retroactive FY marker | `is_retroactive_fiscal_year=true` | | pass / watch / fail |
| `retroactive_ship_readiness_rc` | 記録値 | | pass / watch / fail |
| `stage6_recovery_rc` | 0 | | pass / watch / fail |
| Stage 6 scheduled task action | `expected_action=null`なら skip / production path 指定時は `action_matches_expected=true` | | pass / watch / fail |
| interrupted smoke residue | `residual_paths[].exists=false` | | pass / watch / fail |
| residual cleanup log | `logs\stage6-residual-cleanup-*.json` if cleanup was needed | | pass / watch / fail |

Version-specific diagnostic-only KPI snapshot（real-cycle ではない）:

| KPI | Actual | 判定 |
| --- | ---: | --- |
| `last_run.json status` | `success` | diagnostic pass |
| `dry_run` | bounded real `weekly_run.bat` canary | bounded canary |
| `current_fy` | `2025` | retroactive R7 only |
| `selection_mode` | bounded target-missing school set | diagnostic pass |
| `crawled` | `5` | diagnostic only |
| `found` | `5` | diagnostic pass |
| `downloaded` | `2` | bounded pass |
| `new_document_count` | `2` | bounded pass |
| `target_pdf_auto_yield_pct` / `strict_target_pdf_auto_yield_pct` | `40.0` | below final 60-70% gate |
| `broad_target_pdf_auto_yield_pct` | `40.0` | discovery reach only |
| `ship_gate_status` | `below_gate` | strict weekly basis |
| scheduled task recovery | `ok=true`, `action_matches_expected=true` | pass |
| evidence bundle verify | `ok=true`, `entry_count=12` | pass |

KPI メモ:

```text

```

## 7. 監査 / outbox

| 項目 | 結果 |
| --- | --- |
| 監査ログページ表示 | pass / fail |
| manual_action_log 件数 | |
| JSONL outbox 未送信件数 | |
| audit-flush 実行 | pass / fail / not needed |
| JSONL action_id 重複 | none / observed |

v459 sandbox 既存証跡（real-cycle ではない、operator real-cycle の代替不可）:

| 項目 | 結果 |
| --- | --- |
| 監査ログページ表示 | pass |
| manual_action_log 件数 | `2` |
| JSONL outbox 未送信件数 | before flush `2`, after flush `0` |
| audit-flush 実行 | `exported=2 already_present=0 failed=0` |
| JSONL export stamp | both rows exported; `jsonl_export_error=null` |
| JSONL action_id consistency | DB action IDs match JSONL action IDs |
| real runtime DB marker counts | all `0` |

v408 sandbox 既存証跡（broader UI write paths、real-cycle ではない）:

| 項目 | 結果 |
| --- | --- |
| 監査ログページ表示 | pass |
| manual_action_log 件数 | `7` |
| JSONL outbox 未送信件数 | before flush `7` |
| audit-flush 実行 | `exported=7 already_present=0 failed=0` |
| JSONL export stamp | all seven rows `jsonl_exported_at_present=true` |

## 8. 障害 / 回避策

| 時刻 | 操作 | 現象 | 回避策 | 未解決 |
| --- | --- | --- | --- | --- |
| | | | | |

既知の diagnostic-only 障害 / 注意:

| 時刻 | 操作 | 現象 | 回避策 | 未解決 |
| --- | --- | --- | --- | --- |
| | | | | |

Version-specific setup/UI/recovery/launcher 証跡（operator real-cycle ではない）:

| 時刻 | 操作 | 現象 | 回避策 | 未解決 |
| --- | --- | --- | --- | --- |
| | | Copy concrete rows from the version-specific Stage 6 evidence draft after execution. | | |

添付する証跡:

- `logs\run-*.log`
- `logs\diagnostics-*.txt`
- `logs\stage6-evidence-*.zip`
- `logs\stage6-evidence-verify-*.json`
- `logs\stage6-recovery-*.json`
- `data\output\last_run.json`
- `data\output\target-year-discovery\*-discovery-rca-batch-plan.json`
- Excel 出力ファイル（個人情報を含む可能性があるため、管理者共有用
  `logs\stage6-evidence-*.zip` には入れない）
- 失敗画面の screenshot
- Defender / SmartScreen screenshot

## 9. Release 判定

結論と sign-off の `Decision` は `READY` / `RC_ONLY` / `NOT_READY` のいずれかで記入する。
sign-off の `Date` は `YYYY-MM-DD` 形式で記入する。
`verify_stage6_return.py` は release approval 用なので、`READY` 以外は通過させない。

| 判定項目 | 結果 |
| --- | --- |
| Stage 2-5c Windows VM gate 済み | yes / no |
| 業務員 PC 1 サイクル完了 | yes / no |
| KPI owner 承認 | yes / no |
| Runbook 修正反映済み | yes / no |
| 残 P0/P1 bug | none / exists |

結論:

```text
READY / RC_ONLY / NOT_READY
```

Owner sign-off:

```text
Name:
Date: YYYY-MM-DD
Decision:
```

業務員 sign-off:

```text
Name:
Date: YYYY-MM-DD
Decision:
```
