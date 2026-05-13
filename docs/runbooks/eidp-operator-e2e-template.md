# EIDP 業務員 PC E2E 記録テンプレート

Status: Stage 6 / v1.0 release candidate evidence template
Updated: 2026-05-06

このテンプレートは、業務員の実 PC で 1 サイクル実行した結果を記録するためのものです。
ここが未記入のままでは、EIDP Windows 版を v1.0 と判定しません。

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

## 3. 証跡採取コマンド

PowerShell で実行し、exit code と出力ファイル名を記録します。パスは実際の
解凍先に合わせて置き換えます。

```powershell
cd C:\Users\<user>\<EIDP-extract-dir>
Get-FileHash C:\Users\<user>\Downloads\eidp-windows-*.zip -Algorithm SHA256
.\EIDP-setup.bat
echo $LASTEXITCODE
.\scripts\validate_install.bat --after-setup
echo $LASTEXITCODE
.\EIDP-start.bat
```

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
| `学校別タスク` 初期表示 | 業務員クイックの最初のページとして表示 | pass / fail | |
| `詳細 operator` 折りたたみ | 詳細ページは通常折りたたみ表示 | pass / fail | |

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

## 8. 障害 / 回避策

| 時刻 | 操作 | 現象 | 回避策 | 未解決 |
| --- | --- | --- | --- | --- |
| | | | | |

添付する証跡:

- `logs\run-*.log`
- `logs\diagnostics-*.txt`
- `data\output\last_run.json`
- `data\output\target-year-discovery\*-discovery-rca-batch-plan.json`
- Excel 出力ファイル
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
