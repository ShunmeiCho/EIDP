# EIDP Windows 運用ランブック

対象: EIDP を利用する業務員
運用環境: 業務員 1 名の Windows PC
基本操作: ZIP を解凍し、`.bat` ファイルをダブルクリックして使う

このランブックは Windows 版 EIDP の業務手順です。ターミナル、SSH、SQL の操作は不要です。

## 1. 必要なもの

PC:

- Windows 11
- CPU 2 コア以上
- メモリ 4GB 以上
- 空き容量 5GB 以上

受け取るファイル:

- `eidp-windows.zip` — 必須
- `eidp-ocr-addon-windows.zip` — 任意。画像 PDF を OCR で読み取る場合だけ使います

配布元:

- 原則: 社内ファイルサーバ
- 予備: USB メモリ
- 非推奨: クラウド共有リンク

推奨する解凍先:

```text
C:\EIDP
```

空白を含むフォルダでも動く設計ですが、迷った場合は `C:\EIDP` を使ってください。

## 2. 初回セットアップ

1. `eidp-windows.zip` を受け取ります。
2. ZIP を `C:\EIDP` に解凍します。
3. `C:\EIDP\scripts\first_setup.bat` をダブルクリックします。
4. 黒い画面が開き、初回セットアップが始まります。
5. 完了したら画面を閉じます。

初回セットアップで行われること:

- EIDP 専用の Python 環境を作成します。
- 同梱済みの wheelhouse からオフラインで必要な部品を入れます。
- `data\eidp.sqlite3` を作成します。
- `data\master.xlsx` から学校マスタを取り込みます。
- Windows タスクスケジューラに週次実行を登録します。

もう一度 `first_setup.bat` を実行しても構いません。環境が壊れた場合の修復にも使います。

## 3. 通常起動

1. `C:\EIDP\scripts\launch.bat` をダブルクリックします。
2. ブラウザで EIDP 画面が開きます。
3. 開かない場合は、ブラウザで次を開きます。

```text
http://localhost:8501
```

画面左のサイドバーに 12 ページが表示されます。

業務でよく使うページ:

- `データ状況` — 採録済み、要レビュー、解析失敗の全体確認
- `PDF確認・手入力` — 画像 PDF、低信頼度、解析失敗の確認と手入力
- `R8 override` — 年度判定が誤っている PDF の年度修正
- `Excel プレビュー` — 出力前確認と Excel ダウンロード
- `監査ログ` — 手入力、年度修正、outbox 状態の確認

詳細確認用ページ:

- `マッチング提案`
- `URL追加`
- `Excel出力`
- `マッチング漏れ`
- `除外PDF`
- `学校コード`
- `処理履歴`

## 4. 週次自動実行

初回セットアップ後、毎週月曜 02:00 に自動で週次処理が実行されます。

週次処理で行うこと:

- 都道府県集約サイトなどから新しい R8 PDF を探します。
- 新しく見つかった PDF だけを取り込みます。
- 処理結果を `data\output\last_run.json` に保存します。
- 実行ログを `logs\run-YYYYMMDD.log` に保存します。

週次処理で行わないこと:

- Excel ファイルの自動生成はしません。

Excel は、業務員が画面で確認した後に `Excel プレビュー` ページから作成します。

週次処理中に画面を開いている場合:

- 画面上部に `週次処理中、編集は一時停止` と表示されます。
- この間、手入力や年度修正などの書き込み操作はできません。
- 処理が終わると通常状態に戻ります。

手動で週次処理を実行したい場合:

1. `C:\EIDP\scripts\weekly_run.bat` をダブルクリックします。
2. 完了後、`logs\run-YYYYMMDD.log` と `data\output\last_run.json` を確認します。

## 5. PDF 確認・手入力

`PDF確認・手入力` ページでは、確認が必要な PDF が一覧で表示されます。

表示される主な状態:

- `ocr_pending` — 画像 PDF のため OCR または手入力が必要
- `parse_failed` — PDF 解析に失敗
- `review_pending` — 数字の信頼度が低く確認が必要
- `school_mismatch` — PDF と学校の対応に確認が必要

作業の流れ:

1. 一覧から PDF を選びます。
2. PDF プレビューまたはダウンロードで原本を確認します。
3. OCR 結果がある場合は、入力欄に候補値として表示されます。
4. 原本と照合して、必要な数字を修正します。
5. `保存` を押します。

注意:

- 通常の数字訂正では、学科変更記録は作りません。
- `新設`、`廃科`、`名称変更`、`統合` と明示できる場合だけ、学科変更として記録します。
- 保存した操作は監査ログに残ります。

## 6. R8 年度判定の修正

`R8 override` ページでは、PDF の年度判定を修正できます。

使う場面:

- R8 PDF なのに別年度として登録された
- 別年度 PDF なのに R8 として登録された

作業の流れ:

1. 修正対象の PDF を選びます。
2. 正しい年度を入力します。
3. 理由を入力します。
4. 保存します。

保存すると、次の 4 種類のデータが一貫して修正されます。

- `Document`
- `DepartmentYearly`
- `SupportRecipient`
- `SchoolYearStatus`

この修正は append-only 方式です。古い行を直接書き換えるのではなく、履歴を残したまま新しい revision を作ります。

## 7. Excel プレビューと出力

`Excel プレビュー` ページで Excel の内容を確認してから出力します。

作業の流れ:

1. `Excel プレビュー` ページを開きます。
2. シートごとの内容を確認します。
3. 未マッチ、欠損、要確認の表示を確認します。
4. 問題なければダウンロードします。

出力先:

```text
C:\EIDP\data\output\
```

ブラウザのダウンロードボタンから取得することもできます。

Excel が開いたまま再出力した場合:

- 保存に失敗することがあります。
- 画面に `Excelを閉じてから再実行してください` と表示された場合は、Excel を閉じてから再度出力してください。

## 8. OCR add-on の適用

画像 PDF を OCR で読み取る場合だけ使います。

適用手順:

1. `eidp-ocr-addon-windows.zip` を受け取ります。
2. `C:\EIDP` に解凍します。
3. 次の配置になっていることを確認します。

```text
C:\EIDP\ocr-addon\tesseract\tesseract.exe
C:\EIDP\ocr-addon\tessdata\jpn.traineddata
```

4. EIDP 画面を開いている場合は閉じます。
5. `launch.bat` で起動し直します。
6. `PDF確認・手入力` ページの OCR 表示を確認します。

OCR 自動実行の目安:

- CPU 2 コア以上
- 空きメモリ 4GB 以上

この条件を満たさない PC では、自動 OCR は OFF になります。単一 PDF の手動 OCR は可能です。

OCR は補助機能です。低信頼度の結果は自動で手入力キューに入ります。

## 9. 監査ログ

`監査ログ` ページでは、業務員による操作履歴を確認できます。

記録される主な操作:

- 手入力
- R8 年度修正
- 学科変更の明示登録
- audit outbox の flush

監査データの扱い:

- DB の `manual_action_log` が唯一の権威です。
- `data\audit\manual-actions.jsonl` は DB から出力される outbox です。
- outbox 出力に失敗した場合は、次回 flush で再送されます。

週次処理中は outbox flush も停止されます。

## 10. トラブルシュート

### 画面が開かない

1. `launch.bat` をもう一度実行します。
2. ブラウザで `http://localhost:8501` を開きます。
3. まだ開かない場合は `logs` フォルダ内の最新ログを確認します。

### 初回セットアップが失敗した

1. PC を再起動します。
2. `first_setup.bat` を再実行します。
3. 失敗が続く場合は、表示されたエラー画面と `logs` フォルダを管理者へ共有します。

### Defender または SmartScreen で止まる

社内配布 ZIP であることを確認してください。管理者が指定する手順に従って実行を許可します。

管理者確認用:

- 配布元が社内ファイルサーバであること
- ZIP の checksum が配布時の値と一致すること
- `.bat`、`python.exe`、`uv.exe`、`tesseract.exe` が社内許可済みであること

### Excel 出力に失敗する

Excel で同じファイルを開いている可能性があります。Excel を閉じてから再実行してください。

### OCR が使えない

次のファイルがあるか確認します。

```text
C:\EIDP\ocr-addon\tesseract\tesseract.exe
C:\EIDP\ocr-addon\tessdata\jpn.traineddata
```

ファイルがない場合は、OCR add-on ZIP をもう一度 `C:\EIDP` に解凍してください。

### ネットワークで PDF が取れない

社内プロキシやファイアウォールで学校サイトへのアクセスが制限されている可能性があります。

この場合:

- 手動で PDF を入手できる場合は `PDF確認・手入力` で対応します。
- 管理者にプロキシ設定または許可リストの確認を依頼します。

## 11. 配布手順（管理者向け）

1. `eidp-windows.zip` を作成します。
2. 必要に応じて `eidp-ocr-addon-windows.zip` と
   `eidp-playwright-addon-windows.zip` も作成します。
3. 配布前検査を実行します。

```text
uv run python scripts/verify_windows_distribution.py dist/eidp-windows.zip \
  --ocr-addon dist/eidp-ocr-addon-windows.zip \
  --playwright-addon dist/eidp-playwright-addon-windows.zip \
  --json > dist/windows-distribution-verification.json
```

任意 add-on を配布しない場合は、その引数を省略します。

4. `eidp-windows.zip` と検査 JSON を社内ファイルサーバに置きます。
5. 任意 add-on ZIP も同じ場所に置きます。
6. 検査 JSON の `sha256` を checksum 記録として保管します。
7. 業務員へ配布場所を伝えます。
8. 業務員 PC で `first_setup.bat` が完走することを確認します。

配布優先順位:

1. 社内ファイルサーバ
2. USB メモリ
3. クラウド共有リンク

## 12. アンインストール

1. `C:\EIDP\scripts\uninstall.bat` をダブルクリックします。
2. Windows タスクスケジューラの週次実行が解除されます。

重要:

- `uninstall.bat` は `data\` を削除しません。
- 業務データを削除する場合は、管理者確認後に手動で行ってください。

## 13. 検証状況

このランブックの対象機能は、Mac の unit test だけでは本番利用可能とは判断しません。

リリース判定:

- Mac unit test 通過: 業務ロジックの確認
- Windows VM オフライン検証通過: alpha 解除
- 業務員 PC で 1 サイクル通過: v1.0 リリース判定

業務員 PC で 1 サイクル実行するときは、次のテンプレートに KPI と証跡を記録します。

```text
docs/runbooks/eidp-operator-e2e-template.md
```

Windows VM で確認する項目:

- ZIP 解凍
- `first_setup.bat`
- `launch.bat`
- `weekly_run.bat`
- lock 表示
- Excel 出力
- Excel 占有エラー
- OCR add-on
- Defender / SmartScreen
