# EIDP Windows 運用ランブック

対象: EIDP を利用する業務員
運用環境: 業務員 1 名の Windows PC
基本操作: ZIP を解凍し、`.bat` ファイルをダブルクリックして使う

通常は `C:\EIDP` 直下の `EIDP-setup.bat` と `EIDP-start.bat` だけを使います。
問題が起きた場合だけ `EIDP-diagnose.bat` で診断ファイルを作成します。
`scripts\*.bat` は管理者向けの詳細入口です。

このランブックは Windows 版 EIDP の業務手順です。ターミナル、SSH、SQL の操作は不要です。

## 対象年度と学校URL

EIDP は年度ごとに使い捨てるツールではありません。

- 対象年度は日本の年度（4月始まり）から自動で決まります。
- 2026年度は `2026年度（令和8年度）`、2027年度は `2027年度（令和9年度）` と表示されます。
- 管理者が明示的に固定したい場合だけ `詳細 operator` の `設定` で対象年度を変更します。
- 令和表記は現在の政府・学校ページ検索に必要なため既定で使います。将来、公式の元号表記が変わった場合は
  `設定` で和暦名、検索用ローマ字、開始年度を手動で変更します。

一度登録した学校URLは翌年度以降も再利用します。毎年、同じ学校URLを入力し直す必要はありません。

ただし、登録するURLは年度PDFそのものより、できるだけ学校の `情報公開`、`学校紹介`、法人の公開情報ページなど、
毎年新しいPDFへのリンクが置かれるページを使ってください。PDFファイル直リンクだけを登録すると、
翌年度にファイル名が変わった場合は新しいPDFを見つけられないことがあります。

## 1. 必要なもの

PC:

- Windows 11
- CPU 2 コア以上
- メモリ 4GB 以上
- 空き容量 5GB 以上

受け取るファイル:

- `eidp-windows.zip` — 必須
- `eidp-ocr-addon-windows.zip` — 任意。画像 PDF を OCR で読み取る場合だけ使います
- `eidp-playwright-addon-windows.zip` — 任意。学校公式サイトの自動 URL 補完で
  Scrapling/Chromium を使う場合だけ使います

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
3. `C:\EIDP\EIDP-setup.bat` をダブルクリックします。
4. 黒い画面が開き、初回セットアップが始まります。
5. `Setup completed` と表示されたら、何かキーを押して画面を閉じます。

初回セットアップで行われること:

- EIDP 専用の Python 環境を作成します。
- 同梱済みの wheelhouse からオフラインで必要な部品を入れます。
- `data\eidp.sqlite3` を作成します。
- `data\master.xlsx` から学校マスタを取り込みます。
- `学校別タスク` の初期行を作成します。
- Windows タスクスケジューラに週次実行を登録します。

Windows の権限設定によっては、タスクスケジューラ登録だけ失敗することがあります。
その場合でも EIDP 本体のセットアップが完了していれば利用できます。
画面の `週次URL/PDF再取得` に警告が出た場合は、毎週そのボタンから手動で再取得してください。
自動実行が必要な場合だけ、管理者にセットアップログを共有してください。

もう一度 `EIDP-setup.bat` を実行しても構いません。環境が壊れた場合の修復にも使います。
前回のセットアップが異常終了して `.setup.lock` だけが残った場合、2時間以上古いロックは自動で復旧します。

## 3. 通常起動

1. `C:\EIDP\EIDP-start.bat` をダブルクリックします。
2. ブラウザで EIDP 画面が開きます。
3. 開かない場合は、ブラウザで次を開きます。

```text
http://localhost:8501
```

画面左のサイドバーに `業務員クイック` が表示されます。
最初に開くページは `学校別タスク` です。

`学校別タスク` の見出し直下に、次のような実行中パッケージ情報が表示されます。

```text
実行中のパッケージ: commit=xxxxxxx / branch=... / dirty=false / built=...
```

新しい ZIP を検証するときは、まずこの行をスクリーンショットに含めてください。
この行が表示されない、または管理者から案内された commit と違う場合は、古い ZIP または古い起動中プロセスを
見ている可能性があります。その場合はブラウザを閉じ、黒い起動画面も閉じてから `EIDP-start.bat` を起動し直してください。

初回起動時に `URLなし` が全校分表示される場合は、学校URLの初期取得がまだ終わっていません。
`学校別タスク` ページの `初回URL/PDF取得を開始` ボタンを押してください。
この操作で対応済みの都道府県の確認大学等一覧から学校URLを登録し、対象年度PDFの探索を開始します。
一覧PDF内の学校名リンクに埋め込まれたURLも自動で読み取ります。
同梱済みの既知URLリストと法人ドメイン推定も補助入口として登録します。
未対応の都道府県や未掲載校だけ、`学校別タスク` の `URL追加`
から公式の情報公開ページを補足してください。
学校数が多いため、完了まで数十分かかることがあります。

業務でよく使うページ:

- `学校別タスク` — 学校ごとの対象年度PDFの進捗と次に行う作業の確認
- `PDF確認・手入力` — 画像 PDF、低信頼度、解析失敗、旧年度fallback の確認と手入力
- `年度判定・修正` — 年度判定が誤っている PDF の年度修正
- `Excel プレビュー` — 出力前確認と Excel ダウンロード
- `監査ログ` — 手入力、年度修正、outbox 状態の確認

`詳細 operator` は通常は折りたたまれています。必要な場合だけ開きます。
詳細確認用ページ:

- `設定`
- `データ状況（詳細）`
- `マッチング提案`
- `URL追加`
- `Excel出力（管理者向け）`
- `マッチング漏れ`
- `除外PDF`
- `学校コード`
- `処理履歴`

## 4. 週次自動実行

初回セットアップ後、毎週月曜 02:00 に自動で週次処理が実行されます。

週次処理で行うこと:

- 登録済みの都道府県由来URL、既知URLリスト、法人ドメイン推定、業務員が追加した公式URLから
  新しい対象年度 PDF を探します。
- 新しく見つかった PDF だけを取り込みます。
- 処理結果を `data\output\last_run.json` に保存します。
- PDF探索で失敗証跡が出た場合、管理者向けの Codex RCA キューを
  `data\output\target-year-discovery\{run_id}-discovery-rca-batch-plan.json`
  に保存します。
- 実行ログを `logs\run-YYYYMMDD.log` に保存します。

週次処理で行わないこと:

- Excel ファイルの自動生成はしません。

Excel は、業務員が画面で確認した後に `Excel プレビュー` ページから作成します。

週次処理中に画面を開いている場合:

- 画面上部に `週次処理中、編集は一時停止` と表示されます。
- この間、手入力や年度修正などの書き込み操作はできません。
- 処理が終わると通常状態に戻ります。

手動で週次処理を実行したい場合:

1. 画面の `学校別タスク` を開きます。
2. `週次URL/PDF再取得を開始` を押します。
3. 完了後、画面の最終実行結果を確認します。

`scripts\weekly_run.bat` は管理者向けの復旧入口です。通常の業務では使いません。

## 4.2 困ったときの診断ファイル

セットアップ、起動、初回URL/PDF取得、週次処理で問題が起きた場合:

1. `C:\EIDP\EIDP-diagnose.bat` をダブルクリックします。
2. 黒い画面に `Diagnostics collected` と表示されたら閉じます。
3. `C:\EIDP\logs\diagnostics-YYYYMMDD-HHMMSS.txt` を管理者に共有します。

診断ファイルに含まれるもの:

- build 情報
- インストール検証結果
- `last_run.json`
- 週次タスク登録警告
- 最新の初回URL/PDF取得進行状況
- 最新の初回URL/PDF取得ログ末尾

診断ファイルは読み取り専用の情報収集です。DB、PDF、Excel、設定は変更しません。

## 4.3 設定

通常は変更不要です。管理者だけが確認します。

`詳細 operator` の `設定` で変更できる項目:

- 対象年度（西暦）
- 和暦表示・検索 alias（既定は令和）
- OCR 自動処理（自動判定 / 常に使う / 使わない）
- OCR の最小 CPU 数、最小空きメモリ、Tesseract path
- 学校URL検索 provider と API key
- Firecrawl API key

設定は `C:\EIDP\.env` に保存されます。
対象年度を変更して保存すると、学校別タスクも同時に再計算されます。
年度や API key を変更した後の初回取得・週次処理は、新しい設定で実行されます。
画面のサイドバー表示だけは再読み込み後に新しい表示へ揃います。

## 5. PDF 確認・手入力

通常は先に `学校別タスク` ページを開きます。
学校ごとに `次の作業` を確認し、`PDF確認`、`OCR/手入力`、`手入力` になっている学校だけ
`PDF確認・手入力` ページで作業します。

`PDF確認・手入力` ページでは、対象年度PDFと旧年度fallbackを区別して表示します。
旧年度fallbackは Excel 成果には含めず、対象年度PDFの公示待ちまたは再取得対象として扱います。

表示される主な状態:

- `ocr_pending` — 画像 PDF のため OCR または手入力が必要
- `parse_failed` — PDF 解析に失敗
- `review_pending` — 数字の信頼度が低く確認が必要
- `school_mismatch` — PDF と学校の対応に確認が必要
- `旧年度fallback` — 対象年度PDFが未取得で、前年以前のPDFだけ見つかっている

作業の流れ:

1. `学校別タスク` で対象の学校と `次の作業` を確認します。
2. `PDF確認・手入力` で同じ学校の PDF を選びます。
3. 年度バッジが対象年度か旧年度かを確認します。
4. PDF プレビューまたはダウンロードで原本を確認します。
5. OCR 結果がある場合は、入力欄に候補値として表示されます。
6. 原本と照合して、必要な数字を修正します。
7. `保存` を押します。

注意:

- 通常の数字訂正では、学科変更記録は作りません。
- `新設`、`廃科`、`名称変更`、`統合` と明示できる場合だけ、学科変更として記録します。
- 保存した操作は監査ログに残ります。

## 6. 対象年度判定の修正

`年度判定・修正` ページでは、PDF の年度判定を修正できます。

使う場面:

- 対象年度 PDF なのに別年度として登録された
- 別年度 PDF なのに対象年度として登録された

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
5. `EIDP-start.bat` で起動し直します。
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
- 対象年度の修正
- 学科変更の明示登録
- audit outbox の flush

監査データの扱い:

- DB の `manual_action_log` が唯一の権威です。
- `data\audit\manual-actions.jsonl` は DB から出力される outbox です。
- outbox 出力に失敗した場合は、次回 flush で再送されます。

週次処理中は outbox flush も停止されます。

## 10. トラブルシュート

### 画面が開かない

1. `EIDP-start.bat` をもう一度実行します。
2. ブラウザで `http://localhost:8501` を開きます。
3. まだ開かない場合は `logs` フォルダ内の最新ログを確認します。

### 初回セットアップが失敗した

1. PC を再起動します。
2. `EIDP-setup.bat` を再実行します。
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
   `eidp-playwright-addon-windows.zip` も作成します。後者は Playwright、
   Chromium、Scrapling の wheel を含みます。
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
8. 業務員 PC で `EIDP-setup.bat` が完走することを確認します。

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
- `EIDP-setup.bat`
- `EIDP-start.bat`
- `first_setup.bat`
- `launch.bat`
- `weekly_run.bat`
- lock 表示
- Excel 出力
- Excel 占有エラー
- OCR add-on
- Playwright/Scrapling add-on
- Defender / SmartScreen

## 14. 既知の問題と対処（2026-05-06 Win VM 試運転で発見）

業務員 PC への配布 ZIP は試運転を経て、以下の問題に対応済みです。
過去の配布 ZIP（v0.x 前期）を引き続き使う場合や、試運転中に類似の
症状が出た場合の対処メモとしてください。

### 14.1 cmd ウィンドウが「一閃即閉じ」する

| 症状 | 原因 | 対処 |
|------|------|------|
| `first_setup.bat` をダブルクリックすると一瞬で閉じる、エラーメッセージが見えない | `.bat` の改行が LF（Mac/Linux 形式）になっており cmd.exe が解析不能 | 最新 ZIP（2026-05-06 以降）を使えば自動で CRLF に変換済み。古い ZIP の場合は PowerShell で `.bat` を再保存し直す。 |
| `'nt' は内部または外部のコマンドでは...` のような無関係な単語のエラーが続く | 同上 | 同上 |
| Defender / SmartScreen に阻まれる（"Windows によって PC が保護されました"） | ZIP に MOTW（Mark-of-the-Web、ダウンロード元の印）が付いている | 解凍前に PowerShell で `Unblock-File <ZIP>`、解凍後に `Get-ChildItem -Recurse <展開先> | Unblock-File` を実行 |

PowerShell でまとめて：

```powershell
Unblock-File "$env:USERPROFILE\Downloads\eidp-windows.zip"
Expand-Archive "$env:USERPROFILE\Downloads\eidp-windows.zip" -DestinationPath C:\workspace\EIDP -Force
Get-ChildItem C:\workspace\EIDP -Recurse | Unblock-File
```

### 14.2 `[first_setup] dependency install failed` で停止する

| 症状 | 原因 | 対処 |
|------|------|------|
| `uv pip install` が `No solution found when resolving dependencies` で失敗、`greenlet` / `watchdog` / `colorama` / `tzdata` などが見つからないと表示 | Mac/Linux 上で `pip download --platform win_amd64` を回した際、PEP 508 マーカ条件付きの間接依存が wheelhouse から漏れた | 最新 `requirements-windows.txt` には Windows 限定の間接依存を明示している（2026-05-06 修正）。古い ZIP の場合は build host で再ダウンロードして wheelhouse に追記 |

最新 build_windows_zip.py を使えば再現しません。発見された wheel:

- `greenlet`（sqlalchemy 用）
- `watchdog`（streamlit 用）
- `colorama`（typer / click 用）
- `tzdata`（pandas 用）
- `pywin32`（streamlit 一部機能で要求されることあり）

### 14.3 `.venv` が既に存在するため `uv venv` が失敗する

| 症状 | 原因 | 対処 |
|------|------|------|
| `A virtual environment already exists at .venv. Use --clear to replace it` | 以前の `first_setup.bat` 実行で `.venv` が作成済み | 最新 `first_setup.bat` は `uv venv --clear` を使用して再実行可能。古い ZIP の場合は `Remove-Item .venv -Recurse -Force` の後で再実行 |

### 14.4 Streamlit が起動しない／HTTP 接続できない

| 症状 | 原因 | 対処 |
|------|------|------|
| `launch.bat` を二重起動すると 2 つのプロセスが port 8501 を取り合う | Win cmd では `&` での連結が POSIX シェルと挙動が異なる | 既存 streamlit プロセスを停止: `Get-Process -Name python | Stop-Process -Force` してから再起動 |
| `localhost:8501` に繋がらない、`192.168.0.x:8501` には繋がる | `--server.headless true` で起動した場合 IPv6 / loopback 解決問題 | ブラウザで `http://localhost:8501` を試した後、駄目なら `http://127.0.0.1:8501` |

### 14.5 SSH 鍵認証で接続できない（管理者アカウント）

| 症状 | 原因 | 対処 |
|------|------|------|
| `ssh-copy-id` 後も `Permission denied (publickey)` | 業務員アカウントが Administrators グループ所属の場合、Win sshd は `~/.ssh/authorized_keys` を読まず `C:\ProgramData\ssh\administrators_authorized_keys` を読む | 公開鍵を `administrators_authorized_keys` に書き込み、`icacls` で `Administrators:F` と `SYSTEM:F` のみを残す。`Restart-Service sshd` |

PowerShell（管理者モード）：

```powershell
$pubkey = "ssh-rsa AAAA...your-mac-pubkey..."
$dst = "C:\ProgramData\ssh\administrators_authorized_keys"
Add-Content -Path $dst -Value $pubkey
icacls $dst /inheritance:r /grant "Administrators:F" /grant "SYSTEM:F"
Restart-Service sshd
```

### 14.6 「業務員傻瓜式部署」の前提

最新 ZIP を使う限り、業務員側の操作は次の 3 ステップのみで完了します：

1. ZIP をダウンロード
2. 解凍（Defender / SmartScreen の警告は最初の 1 回だけ「実行」を選択）
3. `EIDP-setup.bat` をダブルクリック → 完了メッセージを待つ

それ以上の手作業（CRLF 変換、wheelhouse 追加、`.venv` 削除、ACL 修正など）は、本ランブックを書き終えた時点で全て build pipeline 側で済んでいます。
業務員に渡る前に管理者側でこの章のチェックリストに従って ZIP の品質を確認してください。

### 14.7 リモートからの HTTP アクセスが「業務員 PC では繋がる、外からは繋がらない」

| 症状 | 原因 | 対処 |
|------|------|------|
| `http://localhost:8501` は業務員 PC のブラウザで開く、`http://<業務員 PC の LAN IP>:8501` は外部マシンから繋がらない | Windows Defender Firewall が `python.exe` の inbound を初回 prompt まで遮断する。`launch.bat` の python は `.venv\Scripts\python.exe` で、毎回 ZIP 設置先が変わると別実行ファイル扱いになり再 prompt | 通常運用は問題なし — 業務員は localhost で開けば OK。LAN 経由の運用が必要な場合のみ管理者 PowerShell で許可:<br><br>`New-NetFirewallRule -DisplayName "EIDP Streamlit" -Direction Inbound -Action Allow -Program "C:\workspace\EIDP\.venv\Scripts\python.exe" -Profile Private`<br><br>install 場所が異なれば `-Program` を実際のパスに合わせる |

このパターンは初回 `launch.bat` 実行時に Defender ポップアップが出ることがあるが、業務員が「アクセスを許可する」を選択するだけで永続化される。CI / VM 検証では事前にルールを追加しておくのが楽。
