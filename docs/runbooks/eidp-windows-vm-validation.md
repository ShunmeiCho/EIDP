# EIDP Windows VM 検証チェックリスト

Status: Sprint 8.5.b / 8.7 validation gate
Updated: 2026-05-06

このチェックリストは、`eidp-windows.zip` を Windows VM でオフライン検証するための実行手順です。

Mac の unit test は業務ロジックと packaging shape の確認です。Windows 配布可用性は、この VM 検証を通すまで確定しません。

## 0. 前提

VM:

- Windows 11
- 日本語ロケール
- 既定コンソールが UTF-8 でない状態でも確認する
- Windows Defender 有効
- ネットワーク切断
- 社内ファイルサーバ相当の共有フォルダから ZIP を受け取れること

検証する ZIP:

- `eidp-windows.zip`
- 任意: `eidp-ocr-addon-windows.zip`
- 任意: `eidp-playwright-addon-windows.zip`

VM に渡す前の Mac preflight:

```text
uv run python scripts/verify_windows_distribution.py dist/eidp-windows.zip \
  --ocr-addon dist/eidp-ocr-addon-windows.zip \
  --playwright-addon dist/eidp-playwright-addon-windows.zip \
  --json > dist/windows-distribution-verification.json
```

`OK core`、`OK ocr-addon`、`OK playwright-addon` が出てから VM に渡す。
optional add-on を配布しない場合は、その `--ocr-addon` / `--playwright-addon`
引数を省略する。
JSON 出力には各 ZIP の `sha256` と `size_bytes` が含まれるため、配布時の
checksum 記録として保管する。

記録するもの:

- ZIP checksum
- 実行日時
- VM OS version
- Defender / SmartScreen 表示
- 失敗時のスクリーンショット
- `logs\run-*.log`
- `data\output\last_run.json`

## 1. Stage 2 — Offline Setup

目的: ネット切断状態で初回セットアップが完走すること。

手順:

1. VM のネットワークを切断する。
2. ZIP を空白入りパスにも展開して確認する。

```text
C:\Program Files\EIDP
```

3. `scripts\first_setup.bat` をダブルクリックする。
4. 完了後、次を確認する。

機械検査:

```text
"C:\Program Files\EIDP\scripts\validate_install.bat" --after-setup
```

確認項目:

- `.venv\Scripts\python.exe` が存在する
- `data\eidp.sqlite3` が存在する
- `data\eidp.sqlite3` に `school_fiscal_year_status` テーブルがある
- `data\master.xlsx` が存在する、または master import 済みである
- `wheelhouse\` からオフライン install されている
- `runtime\python\python.exe` が存在する
- `runtime\uv.exe` が存在する
- Windows タスクスケジューラに `EIDP Weekly Run` が登録されている

合格条件:

- ネットワークなしで `first_setup.bat` が exit code 0
- Python import error がない
- DB bootstrap error がない
- master import error がない

## 2. Stage 2b — UI 起動

目的: 業務員が UI を開けること。

手順:

1. `scripts\launch.bat` をダブルクリックする。
2. ブラウザで `http://localhost:8501` を開く。
3. サイドバーを確認する。

確認項目:

- サイドバー上部に `業務員クイック` が表示される
- `学校別タスク` が最初のページとして表示される
- `PDF確認・手入力` が表示される
- `年度判定・修正` が表示される
- `Excel プレビュー` が表示される
- `監査ログ` が表示される
- `詳細 operator` は折りたたみ表示で、旧 `データ状況` は詳細側にある
- 日本語が文字化けしていない

合格条件:

- Streamlit が起動する
- 学校別タスク page が表示される
- UTF-8 関連の文字化けがない

## 3. Stage 3 — Weekly + Lock + last_run

目的: 週次処理が Windows 上で動き、UI と排他制御されること。

手順:

1. UI を開いたままにする。
2. `scripts\weekly_run.bat` をダブルクリックする。
3. 実行中に UI を確認する。
4. 実行完了後に出力を確認する。

機械検査:

```text
"C:\Program Files\EIDP\scripts\validate_install.bat" --after-setup --after-weekly
```

確認項目:

- UI に `週次処理中、編集は一時停止` が表示される
- 実行中に手入力保存や年度判定修正ができない
- `logs\run-YYYYMMDD.log` が作成される
- `%DATE%` ロケールに依存しない日付ファイル名になっている
- `data\output\last_run.json` が作成される
- `last_run.json` に `status=success`、`run_id`、`started_at`、`finished_at` がある
- `last_run.json` に `current_fy`、`selection_mode`、`target_missing_school_count` がある
- `selection_mode` は通常 `target_missing`
- Excel は自動生成されない

合格条件:

- weekly run exit code 0
- lock 表示が UI に出る
- 完了後 UI が通常状態に戻る
- `last_run.json` が読み取れる

## 4. Stage 4 — Excel Preview / File Lock

目的: Excel 出力と、Excel が開いたままの失敗表示を確認すること。

手順:

1. UI の `Excel プレビュー` を開く。
2. プレビュー内容を表示する。
3. Excel を出力する。
4. 出力ファイルを Excel で開いたまま、もう一度出力する。

確認項目:

- `data\output\*.xlsx` が生成される
- 日本語 sheet 名が文字化けしない
- 日本語セル値が文字化けしない
- ファイル占有時に `Excelを閉じてから再実行してください` が表示される

合格条件:

- 通常出力が成功
- ファイル占有時に operator-facing エラーが出る
- Python traceback を業務員に直接見せない

## 5. Stage 5 — OCR Add-On

目的: OCR add-on がある場合に画像 PDF を処理できること。

手順:

1. `eidp-ocr-addon-windows.zip` を Stage 2 と同じ場所に解凍する。
2. 次を確認する。

```text
C:\Program Files\EIDP\ocr-addon\tesseract\tesseract.exe
C:\Program Files\EIDP\ocr-addon\tessdata\jpn.traineddata
```

機械検査:

```text
"C:\Program Files\EIDP\scripts\validate_install.bat" --after-setup --require-ocr-addon
```

3. UI を再起動する。
4. `PDF確認・手入力` の OCR banner を確認する。
5. image PDF サンプルを処理する。

確認項目:

- OCR add-on 利用可能 banner が表示される
- CPU/RAM 条件を満たす VM では auto ON
- 低スペック条件では auto OFF
- `extraction_method="ocr_tesseract"` の行が保存される
- `confidence_breakdown` が表示される
- confidence < 0.70 は手入力キューに残る

合格条件:

- Tesseract subprocess が実行できる
- `jpn.traineddata` が見つかる
- OCR 結果が DB と UI に反映される
- 低 confidence が Excel に流入しない

## 6. Stage 5b — Optional Playwright Add-On

目的: Playwright add-on がなくても core ZIP が起動し、ある場合は検知できること。

手順:

1. Playwright add-on なしで UI を起動する。
2. PDF discovery が HTTP-first で動くことを確認する。
3. 必要時だけ `eidp-playwright-addon-windows.zip` を解凍する。

機械検査:

```text
"C:\Program Files\EIDP\scripts\validate_install.bat" --after-setup --require-playwright-addon
```

確認項目:

- Playwright/Chromium 不在で core UI が落ちない
- 不在時は警告表示に留まる
- add-on 展開後、`playwright-addon\ms-playwright\` が存在する

合格条件:

- Playwright add-on は v1.0 core 起動の必須条件になっていない

## 7. Stage 5c — Defender / SmartScreen

目的: 社内配布として実行可能であること。

手順:

1. `first_setup.bat`、`launch.bat`、`weekly_run.bat`、`validate_install.bat`、`uninstall.bat` を実行する。
2. Defender / SmartScreen 表示を記録する。
3. 許可手順が必要なら runbook に追記する。

確認項目:

- `.bat`
- `runtime\python\python.exe`
- `runtime\uv.exe`
- `ocr-addon\tesseract\tesseract.exe`

合格条件:

- 社内手順で実行許可できる
- ブロック時の operator-facing 手順が runbook に反映されている

## 8. 判定

Alpha 解除:

- Stage 2 から Stage 5c まで VM で通過

Beta 解除 / v1.0 候補:

- 業務員実 PC で 1 サイクル通過
- KPI を owner が承認
- runbook の不明点が解消済み
- `docs/runbooks/eidp-operator-e2e-template.md` が記入済み

未合格時:

- 失敗ステージ
- 表示されたエラー
- `logs\run-*.log`
- `last_run.json`
- 再現手順

を添えて修正 issue に戻す。
