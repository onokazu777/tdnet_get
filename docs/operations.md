# 運用・障害対応

## 通常運用

日次処理はGitHub Actionsで自動実行されます。PCを起動する必要はありません。

- 平日11:35 JST
- 平日15:35 JST（15:30前後の大量開示向け）
- 平日17:05 JST
- 平日20:05 JST
- 平日23:55 JST

完了メールは **11:35** と **15:35**（および手動実行）の後だけ送ります。

確認先:

- Actions: https://github.com/onokazu777/tdnet_get/actions
- 公開Viewer: https://onokazu777.github.io/tdnet-viewer/
- PDF・CSV: 個人Google Driveの`TDnet_Downloads`

1日に複数回実行する理由は、当日中に追加されたTDnet開示を段階的に取り込むためです。既存PDFは原則スキップし、公開データは詳細JSON名で重複を避けてマージします。

## 手動実行

1. https://github.com/onokazu777/tdnet_get/actions を開く
2. 左側の`Daily XBRL Update`を選ぶ
3. `Run workflow`を押す
4. branchは`main`
5. `target_date`を入力
6. 緑色の`Run workflow`を押す

指定例:

```text
空欄                 今日
20260717             1日
202607               1か月
20260714 20260717    日付範囲
```

範囲が広いとTDnetアクセス数、Actions実行時間、Google Drive転送量が増えます。

## 成功確認

Actionsの各ステップが緑色になっていることを確認します。

特に見る場所:

- `Run PDF downloader`: PDF・一覧CSV取得
- `Upload PDF/CSV to Google Drive`: Drive保存
- `Run XBRL analyzer`: XBRL分析
- `Push to viewer repo`: 公開データpush

Driveアップロードログの成功例:

```text
Transferred: 303 / 303, 100%
Upload done.
```

同じファイルがすでにDriveにある場合、成功しても`0 B / 0 B`になります。

GitHub Pagesはpush後に構築されるため、画面反映まで数分かかる場合があります。ブラウザに古い内容が残る場合は`Ctrl+F5`で再読み込みします。

## よくある障害

### Viewerの日付が止まった

確認順:

1. `tdnet_get`のActionsで直近の実行日時を見る
2. ワークフローが無効化されていないか見る
3. 失敗したrunの赤いステップを開く
4. `tdnet-viewer`の最新コミット日時を見る
5. GitHub Pagesの構築完了を待つ

過去の原因:

- 公開リポジトリに60日間活動がなく、GitHubがscheduled workflowを自動無効化

現在の対策:

- `keepalive.yml`が毎月空コミットを作成

無効化されていた場合:

1. Actionsで`Daily XBRL Update`を開く
2. `Enable workflow`
3. 欠けた日付範囲を`Run workflow`で実行

### Google DriveにPDF・CSVが増えない

`Upload PDF/CSV to Google Drive`のログを確認します。

主な原因:

- `RCLONE_CONFIG`未登録
- rclone設定の貼り付けミス
- Google側でrcloneのアクセス権を削除した
- refresh tokenが失効した
- Google Drive容量不足

再設定:

```powershell
powershell.exe -ExecutionPolicy Bypass -File "C:\Users\onok\Desktop\開発\tdnet_get\setup_rclone_gdrive.ps1"
```

Google認証後、生成された`rclone.conf`全文をGitHubのRepository secret `RCLONE_CONFIG`へ登録します。

Secret設定画面:

https://github.com/onokazu777/tdnet_get/settings/secrets/actions

注意: Driveアップロードは`continue-on-error`なので、ここだけ失敗してもViewer更新処理は継続します。

### `tdnet-viewer`へのpushが失敗する

`Clone viewer repo`または`Push to viewer repo`のログを確認します。

主な原因:

- `VIEWER_PAT`の期限切れ
- PATのリポジトリアクセス不足
- `tdnet-viewer`側の権限変更

対処:

1. GitHubで新しいPATを作る
2. `tdnet-viewer`への読み書き権限を付ける
3. Repository secret `VIEWER_PAT`を更新
4. 失敗日を手動再実行

### PDFはあるが検索JSONがない

`Extract PDF text to JSON`のログを確認します。

ローカルで補完する場合:

```powershell
python "⑥_pdf_text_extractor.py" `
  --target "20260717" `
  --save-root "G:\マイドライブ\TDnet_Downloads" `
  --out-dir ".\text_data" `
  --skip-existing
```

過去全体の未作成分は次で補完できます。

```powershell
python run_extract_all.py
```

ローカル作成だけではGitHub Pagesへ公開されません。公開が必要ならActionsで対象日を再実行します。

### TDnet側で対象データがない

土日・祝日、または開示がない時間帯は新規データがゼロになる場合があります。ワークフロー成功かつ`No new data`なら異常ではありません。

### GitHub Actionsが遅い

GitHubのscheduleは指定時刻ぴったりに始まらず、混雑時に遅延する場合があります。3回の定期実行のいずれかが成功していれば、通常は当日分が反映されます。

## ローカル処理

### ローカル日次タスクは必要か

`TDnet_Daily_Auto_Local`は、①と②をPCで実行してGoogle Driveへ保存する旧経路です。現在はGitHub Actionsが同じPDF・CSVを直接Google Driveへ保存するため、通常は無効で問題ありません。

ローカルタスクを有効にすると、同じ日のデータをPCとActionsが重複取得します。

削除する場合:

```powershell
powershell.exe -ExecutionPolicy Bypass -File ".\remove_tdnet_daily_task.ps1"
```

予備として残す場合は、無効のまま保持できます。

### 他のPCでローカル取得する

Google Drive for Desktopで同じ`TDnet_Downloads`を同期しているPCなら、別PCでも`auto_local.bat` / `run_auto_local.py`を実行できます。

- 保存先の既定値は`G:\マイドライブ\TDnet_Downloads`
- ドライブ文字が違う場合は`run_auto_local.py`の`SAVE_ROOT`を合わせる
- ローカル実行はPDF・CSVをDriveへ保存するだけで、`tdnet-viewer`は更新しない

セットアップと起動手順は[READMEの「他のPCでローカル取得する」](../README.md#他のpcでローカル取得する)を参照してください。

### ローカルStreamlit

起動:

```powershell
.\start_streamlit_local.bat
```

URL:

```text
http://localhost:8501
```

停止は、起動したPython/Streamlitプロセスを終了します。

## 完了メール設定

`Daily XBRL Update`のうち、**11:35** と **15:35**（および手動実行）が終わると、成功・失敗どちらでも `ono@links-research.com` へメールを送ります。17:05 / 20:05 / 23:55 では送りません。

目的は「更新しました。チェックしてください」の案内です。本文には結果、対象日、ActionsのRun URL、Viewer URLを含めます。

### 必要なSecrets

https://github.com/onokazu777/tdnet_get/settings/secrets/actions

| 名前 | 内容 |
|---|---|
| `MAIL_SMTP_SERVER` | SMTPサーバ（Googleなら `smtp.gmail.com`） |
| `MAIL_SMTP_PORT` | `587`（推奨）または `465` |
| `MAIL_USERNAME` | SMTP認証ユーザー（送信元。例: `ono.happy@gmail.com`） |
| `MAIL_PASSWORD` | SMTPパスワード（Googleならアプリパスワード。スペースなし） |

未設定の場合、更新ジョブは通常どおり実行され、メール送信だけスキップされます。

### Google Workspace / Gmail の例

1. **送信元**にするGoogleアカウント（例: `ono.happy@gmail.com`）でログインする
2. 2段階認証を有効にする
3. [アプリパスワード](https://myaccount.google.com/apppasswords)を発行する
4. Secretsへ次を登録する

```text
MAIL_SMTP_SERVER = smtp.gmail.com
MAIL_SMTP_PORT   = 587
MAIL_USERNAME    = ono.happy@gmail.com
MAIL_PASSWORD    = 発行した16桁（スペース削除）
```

5. 宛先 `ono@links-research.com` はワークフロー側に固定済み
6. Actionsで`Daily XBRL Update`を手動実行し、メール受信を確認する

`535 BadCredentials` が出る場合は、通常のログインパスワードを入れていないか、送信元と違うアカウントのアプリパスワードになっていないかを確認してください。

## 認証情報の管理

値を次の場所へ貼らないでください。

- README、Markdown、Python、YAML
- Issue、Pull Request
- チャット、メール
- Actionsログ

管理対象:

| 認証情報 | 保存場所 |
|---|---|
| Google Drive rclone設定 | GitHub Secret `RCLONE_CONFIG` |
| viewer push用PAT | GitHub Secret `VIEWER_PAT` |
| 完了メールSMTP | GitHub Secret `MAIL_SMTP_*` |
| ④管理者パスワード | Streamlit secrets `admin_password` |

認証情報を誤って公開した場合は、文字列を削除するだけでなく、GoogleまたはGitHub側で権限・トークンを失効させて再発行します。

## 変更後の確認

取得・解析コードまたはworkflowを変更した場合:

1. 単日を指定して`Run workflow`
2. Actionsの全ステップを確認
3. Google Driveの対象日フォルダを確認
4. `tdnet-viewer`のコミットを確認
5. GitHub Pagesの最新日を確認
6. キーワード検索のクラウドモードを確認

## 定期点検

月1回程度:

- `Daily XBRL Update`が直近の平日に成功しているか
- `Keep Alive`が成功しているか
- Google Drive容量
- `VIEWER_PAT`の有効期限
- `RCLONE_CONFIG`でDrive接続できるか
- GitHub Pagesの最新日

## 既知の注意点

- rcloneの共有Google Drive client IDは廃止予定の警告が出る場合があります。停止時期が近づいたら、自分のGoogle CloudプロジェクトでDrive APIのclient IDを作成してrclone設定を更新します。
- `④_xbrl_viewer.py`とGitHub Pages版Viewerは別物です。
- `start_xbrl_viewer_catchup.ps1`は不足データを取得せず、④を起動するだけです。
- Streamlitクラウド版の公開URLは現在このリポジトリに記録されていません。URLが分かったらREADMEの「公開先・管理画面」へ追記します。
