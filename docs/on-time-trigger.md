# 時刻どおり起動する（外部cron）

GitHub Actions の `schedule` は混雑時に **数十分〜数時間遅れる**ことがあります。  
本番の起動は、外部cronから `workflow_dispatch` を叩く方式にします。

## 方式の概要

```text
cron-job.org（など）
  平日 11:35 / 15:35 / 17:05 / 20:05 / 23:55 JST
    → GitHub API (workflow_dispatch, slot指定)
      → Daily XBRL Update
```

- メールは `1135` と `1535` の枠だけ送る
- 同じ枠の二重起動はマーカーでスキップ
- GitHub側の `schedule` は予備（遅延時の救済）

## 1. GitHub PAT を作る

1. https://github.com/settings/tokens?type=beta を開く（Fine-grained token）
2. **Generate new token**
3. 設定例:
   - Token name: `tdnet-cron-dispatch`
   - Expiration: 90日など（期限切れ前に更新）
   - Resource owner: `onokazu777`
   - Repository access: **Only select repositories** → `tdnet_get`
   - Permissions → Repository permissions:
     - **Actions**: Read and write
     - **Contents**: Read-only（なくても可だが Read 推奨）
4. 発行されたトークンを控える（再表示できない）

> Classic token でも可。その場合 scope は `repo` と `workflow`。

## 2. cron-job.org でジョブを作る

1. https://cron-job.org/ で無料アカウント作成
2. **Create cronjob** を5つ作る（下表）

### 共通設定

| 項目 | 値 |
|---|---|
| URL | `https://api.github.com/repos/onokazu777/tdnet_get/actions/workflows/daily_update.yml/dispatches` |
| Schedule | 下表の各時刻（タイムゾーン **Asia/Tokyo**） |
| Request method | **POST** |
| Enabled | Yes |

**Headers**

```text
Accept: application/vnd.github+json
Authorization: Bearer ここにPAT
X-GitHub-Api-Version: 2022-11-28
Content-Type: application/json
```

**Request body**（枠ごとに `slot` だけ変える）

```json
{"ref":"main","inputs":{"slot":"1135","target_date":"","force":"false"}}
```

### 5つのジョブ

| タイトル例 | 時刻 (JST・平日) | body の slot |
|---|---|---|
| tdnet-1135 | 月〜金 11:35 | `1135` |
| tdnet-1535 | 月〜金 15:35 | `1535` |
| tdnet-1705 | 月〜金 17:05 | `1705` |
| tdnet-2005 | 月〜金 20:05 | `2005` |
| tdnet-2355 | 月〜金 23:55 | `2355` |

cron-job.org のスケジュール例（サイトのUIに合わせて設定）:

- Every day of the week: Mon–Fri
- Time: 11:35 など

## 3. 動作確認

PowerShell（PATを一時的に環境変数へ）:

```powershell
$env:TDNET_DISPATCH_TOKEN = "github_pat_xxxx"   # 発行したPAT
cd "C:\Users\onok\Desktop\開発\tdnet_get"
.\scripts\trigger_daily_update.ps1 -Slot 1135
```

成功すると HTTP 204 で、すぐ Actions に run が現れます。

https://github.com/onokazu777/tdnet_get/actions

## 4. メール

| slot | メール |
|---|---|
| 1135 | 送る |
| 1535 | 送る |
| 1705 / 2005 / 2355 | 送らない |
| 画面から Run workflow（slot空欄） | 送る（確認用） |

## 5. 注意

- PAT の有効期限が切れると外部cronは全部失敗する → 期限前に更新
- PAT を README や Issue に貼らない
- cron-job.org 側の実行履歴で 204 / 401 / 403 を確認できる
- GitHub の schedule が遅れて同じ枠を叩いても、枠マーカーで2回目はスキップされる
