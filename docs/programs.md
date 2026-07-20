# プログラム一覧

## Python

### `①_tdnetアクセスしてダウンロードする処理（月日付別フォルダ保存）.py`

- 目的: TDnet一覧取得、PDFダウンロード、一覧CSV作成
- 実行場所: GitHub Actions / PC
- 入力: TDnet一覧HTML、対象日付
- 出力: 日付別PDF、`TDnet_Sorted_*.csv`
- 呼び出し元:
  - `.github/workflows/daily_update.yml`
  - `run_auto_local.py`
- 主な引数:
  - `--target`: 単日、月、範囲
  - `--save-root`: 保存先
  - `--page-sleep`, `--pdf-sleep`: TDnetへのアクセス間隔
  - `--clean-day-folder`: 日付フォルダを消して再取得

### `②a②bは２つフリーワード検索.py`

- 目的: PDF全文検索、配布用CSV作成、表題検索
- 実行場所: GitHub Actions / PC
- サブコマンド:
  - `analyze`: PDF本文を検索
  - `distribute`: 一覧CSVと検索結果を突合
  - `title`: 一覧CSVの表題のみ検索
- 入力: ①のPDFと`TDnet_Sorted` CSV
- 出力:
  - `Analysis_Hits_free_word_*.csv`
  - `PDF_Search_Result_Distribution_free_word_*_sh.csv`
  - `Title_Hits_free_word_*.csv`
- 呼び出し元:
  - `.github/workflows/daily_update.yml`
  - `run_auto_local.py`

### `③_xbrl_financial_analyzer.py`

- 目的: TDnet XBRL ZIPの取得・解析、財務分析Excel作成
- 実行場所: GitHub Actions / PC
- 入力: TDnet一覧HTML、XBRL ZIP、`xbrl_taxonomy.py`
- 出力:
  - XBRL ZIP
  - `XBRL分析_<コード>_<会社名>.xlsx`
  - `pdf_links.json`
- 呼び出し元: `.github/workflows/daily_update.yml`または手動
- 主な引数:
  - `--target`
  - `--code`: 会社コード限定
  - `--save-root`
  - `--threshold`: 大幅変動判定の閾値

### `xbrl_taxonomy.py`

- 目的: XBRL要素名と日本語ラベルの共通定義
- 単独実行: しない
- 利用元: `③_xbrl_financial_analyzer.py`

### `④_xbrl_viewer.py`

- 目的: XBRL分析Excelを閲覧するローカルStreamlitアプリ
- 実行場所: PC
- 入力: `XBRL_DATA_ROOT`配下の日付フォルダとExcel
- 出力: ブラウザ画面、管理者のみExcelダウンロード
- 起動:

```powershell
$env:XBRL_DATA_ROOT = "$HOME\Desktop\XBRL_Data"
python -m streamlit run "④_xbrl_viewer.py"
```

- Streamlit secret: `admin_password`

### `⑤_export_json.py`

- 目的: XBRL分析ExcelをGitHub Pages用JSONへ変換
- 実行場所: GitHub Actions / PC
- 入力:
  - `XBRL_DATA_ROOT`配下のExcel
  - `pdf_links.json`
  - Yahoo Finance
  - `docs/data/stock_cache.json`
- 出力:
  - `docs/data/index.json`
  - `docs/data/detail/*.json`
  - `docs/data/stock_cache.json`
- 主な引数:
  - `--force`
  - `--target YYYYMMDD`
  - `--skip-stock`

### `⑥_pdf_text_extractor.py`

- 目的: PDF本文をページ単位で抽出し、検索用JSONを作成
- 実行場所: GitHub Actions / PC
- 入力: ①のPDFと一覧CSV
- 出力: `text_YYYYMMDD.json`
- 主な引数:
  - `--target`
  - `--save-root`
  - `--out-dir`
  - `--retention-days`（既定180日）
  - `--skip-existing`

### `keyword_search_app.py`

- 目的: TDnet PDFキーワード検索のStreamlit UI
- 実行場所: PC / Streamlitホスティング
- データモード:
  - ローカルPDF直接検索
  - ローカルJSON高速検索
  - GitHub Pages JSONのクラウド検索
- 主要設定:
  - `TDNET_DEPLOY_MODE=cloud`: クラウド専用モード
  - 未設定または`local`: ローカルモード
- クラウド入力: `https://onokazu777.github.io/tdnet-viewer/data/text`
- ローカル入力:
  - `G:\マイドライブ\TDnet_Downloads`
  - リポジトリ内の`text_data`
- 画面から生成するファイル: `keyword_search_<開始日>_<終了日>.csv`

### `run_auto_local.py`

- 目的: ①→②A→②BをPC上で順番に実行する旧ローカルランナー
- 呼び出し元: `auto_local.bat`
- 保存先: `G:\マイドライブ\TDnet_Downloads`
- ログ: `logs/auto_local_<対象日>_<実行時刻>.log`
- 注意: XBRL分析、JSON公開、`tdnet-viewer`更新は行わない

### `run_extract_all.py`

- 目的: Google Driveにある全日付を調べ、未作成のテキストJSONだけを⑥で抽出
- 入力: `G:\マイドライブ\TDnet_Downloads`
- 出力: リポジトリ内の`text_data`
- 用途: 過去データの初回一括作成・補完

## Windowsバッチ・PowerShell

### `auto_local.bat`

カレントディレクトリとUTF-8環境を設定し、`run_auto_local.py`を実行します。

### `tdnet_catchup.ps1`

ローカル出力の不足を調べ、最大7日分を`auto_local.bat`で補完します。保存先はGoogle Driveです。

### `install_tdnet_daily_task.ps1`

Windowsタスクスケジューラへローカル取得タスクを登録します。現在の本番処理はGitHub Actionsなので、このローカルタスクは予備です。

登録対象:

- `TDnet_Daily_Auto_Local`
- `TDnet_Catchup_OnLogon`

### `remove_tdnet_daily_task.ps1`

上記2つのWindowsタスクを削除します。

### `start_streamlit_local.bat`

`keyword_search_app.py`を`127.0.0.1:8501`で起動します。`.venv\Scripts\python.exe`があれば優先して使います。

### `install_streamlit_startup_task.bat`

ログオン時に`start_streamlit_local.bat`を起動するタスク`TDnet_Streamlit_Localhost_8501`を登録します。

### `remove_streamlit_startup_task.bat`

ローカルStreamlitの自動起動タスクを削除します。

### `start_xbrl_viewer_catchup.ps1` / `.bat`

前回起動マーカーを確認し、平日の取りこぼしがあると判断した場合に`④_xbrl_viewer.py`を起動します。

注意: 名前に`catchup`がありますが、データ取得や不足データ生成は行わず、Streamlit Viewerを起動するだけです。

### `setup_rclone_gdrive.ps1`

個人Google Drive用のrclone remote `gdrive`を作成し、GitHub Secret `RCLONE_CONFIG`へ登録する内容を表示します。認証情報を含むため、出力を公開場所へ貼らないでください。

## GitHub Actions

### `.github/workflows/daily_update.yml`

- 名前: `Daily XBRL Update`
- schedule: 平日11:35、15:35、17:05、20:05、23:55 JST
- 手動入力: `target_date`
- 実行順:
  1. ① PDF取得
  2. ②A PDF検索
  3. ②B 配布CSV
  4. Google Driveアップロード
  5. ⑥ テキストJSON
  6. ③ XBRL分析
  7. `tdnet-viewer` clone
  8. ⑤ 公開JSON
  9. 既存公開データとマージ
  10. `tdnet-viewer`へpush
  11. 完了メール送信（11:35 / 15:35 / 手動のみ。Secrets未設定時はスキップ）

Google Driveアップロードと②Bは失敗しても後続処理を続けます。それ以外の主要ステップが失敗すると、その実行は失敗になります。完了メールは別ジョブ`notify`が送り、宛先は`ono@links-research.com`です。17:05 / 20:05 / 23:55ではメールを送りません。

### `.github/workflows/keepalive.yml`

- 名前: `Keep Alive`
- schedule: 毎月1日03:00 JST
- 目的: 月1回空コミットを作り、GitHubの60日無活動によるscheduled workflow停止を防ぐ

## 依存ライブラリ

`requirements.txt`:

- requests
- pandas
- beautifulsoup4
- pymupdf
- lxml
- openpyxl
- streamlit
- yfinance
