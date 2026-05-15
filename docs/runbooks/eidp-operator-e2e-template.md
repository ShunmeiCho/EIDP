# EIDP 業務員 PC E2E 記録テンプレート

Status: Stage 6 / v1.0 release candidate evidence template
Updated: 2026-05-15

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
- v408 では ZIP / setup / UI health / R7 Excel / sandbox UI write / non-Excel
  diagnostic evidence bundle まで実証済みです。ただし sandbox と dry-run は
  業務員 PC 1 サイクル sign-off の代替ではありません。下表の「v408 既存証跡」
  は転記補助であり、空欄のまま残る real-cycle / owner fields を埋める必要があります。
- 次の real-cycle Stage 6 は、明示的に v408 lane 継続を選ぶ場合を除き、
  `docs/reports/current-release-status.md` が示す最新の Mac / non-Windows
  release-gate-clean ZIP を転送して、下表の実施情報をその ZIP の値で埋めます。
  ZIP 内のこのテンプレートは自分自身の最終 SHA256 を持てないため、SHA256 は
  `.sha256` sidecar または release-status の値を転記します。
- version-specific transfer steps, package SHA256, and release-gate logs are
  recorded in the current transfer checklist / release-status documents. Do not
  hard-code those values into this reusable template before packaging.

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

v408 既存証跡（転記候補、real-cycle sign-off ではない）:

| 項目 | 値 |
| --- | --- |
| EIDP commit | `f0c2715833b54e60fea85259e16ad0a1d9e6c106` |
| core ZIP | `dist/eidp-windows-v408.zip` |
| core ZIP sha256 | `61fe233e41c08b8684560778b25c36f12ad0848135e8930ef07d8fa265fbbbe2` |
| Windows extract path | `C:\Users\cyo20\EIDP-v408-f0c27158` |
| transferred ZIP | `C:\Users\cyo20\eidp-windows-v408.zip` |

現行投入候補（Mac / non-Windows gate 済み、Windows 未実証）:

| 項目 | 値 |
| --- | --- |
| EIDP package snapshot | `docs/reports/current-release-status.md` から転記 |
| core ZIP | `dist/eidp-windows-vXXX.zip` |
| core ZIP sha256 | `.sha256` sidecar または release-status から転記 |
| core ZIP sha256 sidecar note | `.sha256` は repo-relative path を記録する。ZIP を `C:\EIDP-staging\` に平置きした場合は、sidecar の digest 値と `Get-FileHash` の結果を比較する。 |
| non-Windows gate log | `logs/release-gate-vXXX-retroactive.json` |
| retroactive matrix log | `logs/release-gate-vXXX-retroactive-matrix.json` if used |
| Windows transfer checklist | current version-specific checklist |
| Windows extract path | 未実施 |
| transferred ZIP | 未実施 |

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

v408 既存証跡（要再確認）:

| 項目 | 値 |
| --- | --- |
| Hostname / user | `JUNMING` / `junming` |
| Home | `C:\Users\cyo20` |
| Historical Windows version | Windows 11 Pro build `26200` |
| Historical CPU/RAM | i9-13900HK / about 32 GB RAM |
| 未確認の現行項目 | locale, console encoding, free disk, Defender, SmartScreen, network/proxy |

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

v408 既存証跡（diagnostic-only）:

```text
logs\diagnostics-v408-ui-sandbox-proof-20260515-034848.txt
logs\run-v408-retroactive-dryrun-20260515-040053.log
logs\stage6-recovery-20260515-040010.json
logs\stage6-residual-cleanup-20260515-040034.json
logs\stage6-evidence-20260514-190257.zip
logs\stage6-evidence-verify-20260515-040322.json
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
| `first_setup.bat` | exit code 0 | pass / fail | |
| `.venv` 作成 | `.venv\Scripts\python.exe` が存在 | pass / fail | |
| DB bootstrap | `data\eidp.sqlite3` が存在 | pass / fail | |
| master import | 学校マスタが取り込まれる | pass / fail | |
| 年度タスク初期生成 | `school_fiscal_year_status` に行がある | pass / fail | |
| Task Scheduler | `EIDP Weekly Run` が登録される | pass / fail | |
| `launch.bat` | Streamlit 起動 | pass / fail | |
| Mac tunnel health | `http://127.0.0.1:18501/_stcore/health` が `ok` | pass / fail / n/a | |
| `学校別タスク` 初期表示 | 業務員クイックの最初のページとして表示 | pass / fail | |
| `詳細 operator` 折りたたみ | 詳細ページは通常折りたたみ表示 | pass / fail | |

v408 既存証跡（転記候補）:

| 手順 | 結果 | 証跡 |
| --- | --- | --- |
| ZIP 解凍 | pass | `C:\Users\cyo20\EIDP-v408-f0c27158` |
| `EIDP-setup.bat` | pass | `logs\setup-v408-20260515.log` |
| `.venv` 作成 | pass | `validate_windows_install.py --after-setup --json` |
| DB bootstrap / master import | pass | `school_count=2418`, `sqlite_integrity_check=ok` |
| 年度タスク初期生成 | pass | `school_fiscal_year_status_count=2418`, `excel_ready=0` |
| Task Scheduler | pass | execute path `C:\Users\cyo20\EIDP-v408-f0c27158\scripts\weekly_run.bat` |
| Streamlit health | pass | Windows `8508`, Mac tunnel `18508 -> 8508`, `/_stcore/health=ok` |
| Default launcher health | pass | `EIDP-start.bat`, Windows `8501`, Mac tunnel `18501 -> 8501`, `/_stcore/health=ok` |

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

v408 R7 retroactive 既存証跡（FY2026 yield ではない）:

| 指標 | 結果 |
| --- | --- |
| R7 CLI export | `data\output\v408-r7-retroactive-export.xlsx` |
| R7 browser download | `_temp/v408-r7-browser-eidp_master.xlsx`, suggested `eidp_master.xlsx` |
| Sheet counts | `採録状況=2418`, `対象比率=10022`, `学科別=9719`, `在籍のみ抜粋=9719` |
| openpyxl dimensions | `2419x10`, `10023x22`, `9721x83`, `9721x19` |
| Browser vs CLI business diff | `missing_sheets=0`, `extra_sheets=0`, `missing_rows=0`, `extra_rows=0`, `differing_fields=0` |

現行 package Mac retroactive Excel matrix（FY2026 yield ではない。Windows 実走時の比較基準）:

| FY | Gate log | 判定 | Business diff | Export rows |
| ---: | --- | --- | --- | --- |
| 2025 | | | | |
| 2024 | | | | |
| 2023 | | | | |

## 6. KPI 判定

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
| Excel ready 率 | >= 60% | | pass / watch / fail |
| retroactive FY 診断年度 | 記録値 | | pass / watch / fail |
| retroactive FY marker | `is_retroactive_fiscal_year=true` | | pass / watch / fail |
| `retroactive_ship_readiness_rc` | 記録値 | | pass / watch / fail |
| `stage6_recovery_rc` | 0 | | pass / watch / fail |
| Stage 6 scheduled task action | `expected_action=null`なら skip / production path 指定時は `action_matches_expected=true` | | pass / watch / fail |
| interrupted smoke residue | `residual_paths[].exists=false` | | pass / watch / fail |
| residual cleanup log | `logs\stage6-residual-cleanup-*.json` if cleanup was needed | | pass / watch / fail |

v408 diagnostic-only KPI snapshot:

| KPI | Actual | 判定 |
| --- | ---: | --- |
| `last_run.json status` | `success` | diagnostic pass |
| `dry_run` | `true` | diagnostic only |
| `current_fy` | `2025` | retroactive only |
| `ship_gate_status` | `not_measured` | not release evidence |
| `new_document_ids` | `[]` | diagnostic only |
| `target_pdf_auto_yield_pct` | `null` | not measured |
| `operator_reviewable_yield_pct` | `null` | not measured |
| `stage6_recovery_rc` | `1` | watch: residual artifacts remain |
| scheduled task action | `action_matches_expected=true` | pass |
| interrupted smoke residue | `existing_count=5` | watch |
| residual cleanup mode | `dry_run`, `moved_count=0` | intentional |

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

v408 sandbox 既存証跡（real-cycle ではない）:

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

既知の v408 diagnostic-only 障害 / 注意:

| 時刻 | 操作 | 現象 | 回避策 | 未解決 |
| --- | --- | --- | --- | --- |
| 2026-05-15 | `stage6_recovery_check` | old v384 residual smoke artifacts make overall `ok=false` | cleanup dry-run recorded only; no `--apply` without approval | yes |
| 2026-05-15 | `collect_stage6_evidence` | manifest missing `bootstrap_logs`, `bootstrap_progress`, `discovery_rca` | accepted by current verifier with required labels, but keep diagnostic-only | yes |
| 2026-05-15 | UI write proof | copied-DB sandbox, not real operator cycle | repeat on approved full-cycle / real cycle | yes |

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

| 判定項目 | 結果 |
| --- | --- |
| Stage 2-5c Windows VM gate 済み | yes / no |
| 業務員 PC 1 サイクル完了 | yes / no |
| KPI owner 承認 | yes / no |
| Runbook 修正反映済み | yes / no |
| 残 P0/P1 bug | none / exists |

結論:

```text
go / no-go / beta continue
```

Owner sign-off:

```text
Name:
Date:
Decision:
```

業務員 sign-off:

```text
Name:
Date:
Decision:
```
