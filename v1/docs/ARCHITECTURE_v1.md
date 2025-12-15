# YouTube Notifier on Bluesky - v1 アーキテクチャ設計

## 概要

特定の YouTube チャンネルの新着動画を RSS で監視し、指定した Bluesky アカウントに自動投稿する常駐ボット。Windows / Linux 対応。

## システムアーキテクチャ

### 処理フロー

```
起動
  ↓
.env 読み込み & バリデーション（config.py）
  ↓
SQLite DB 初期化（database.py）
  ↓
Bluesky 認証情報ロード（bluesky_v1.py）
  ↓
[メインループ] POLL_INTERVAL_MINUTES ごとに以下を繰り返:
  ├─ YouTube RSS 取得（youtube_rss.py）
  ├─ 新着動画を DB に保存（database.py）
  ├─ 未投稿動画を取得（database.py）
  ├─ BLUESKY_POST_ENABLED が有効なら:
  │   └─ Bluesky に投稿（bluesky_plugin.py → bluesky_v1.py）
  ├─ 投稿済みフラグ更新（database.py）
  └─ ポーリング間隔分 sleep
  ↓
Ctrl+C で安全終了
```

## モジュール構成

### コアロジック

| ファイル名 | 役割 | 内容 |
|-----------|------|------|
| `main_v1.py` | エントリーポイント・メインループ | 起動、設定読み込み、無限ループで RSS → DB → 投稿 |
| `config.py` | 設定読み込み・バリデーション | settings.env から設定取得、値チェック（ポーリング間隔 5 分以上など） |
| `database.py` | SQLite 操作 | テーブル作成、動画の INSERT/SELECT/UPDATE、投稿済みフラグ管理 |
| `youtube_rss.py` | RSS 取得・パース | YouTube チャンネル RSS URL 生成、RSS 取得、新着動画抽出 |
| `bluesky_plugin.py` | Bluesky 投稿ラッパ | DB レコード → event_context 変換、BlueskyPoster.post_new_video() 呼び出し |

### 既存ユーティリティ（再利用）

| ファイル名 | 役割 | 内容 |
|-----------|------|------|
| `bluesky_v1.py` | Bluesky 投稿処理 | 画像アップロード、テンプレートレンダ、投稿実行、投稿履歴記録 |
| `utils_v1.py` | ユーティリティ関数 | 日時フォーマット、リトライデコレータ、URL バリデーション |

## データベース設計

### テーブル: `videos`

| カラム | 型 | 制約 | 説明 |
|--------|----|----|------|
| `id` | INTEGER | PRIMARY KEY AUTO_INCREMENT | 主キー |
| `video_id` | TEXT | UNIQUE, NOT NULL | YouTube 動画 ID |
| `title` | TEXT | NOT NULL | 動画タイトル |
| `video_url` | TEXT | NOT NULL | 動画 URL |
| `published_at` | TEXT | NOT NULL | 公開日時（ISO 8601） |
| `channel_name` | TEXT | | チャンネル名 |
| `posted_to_bluesky` | INTEGER | DEFAULT 0 | 投稿済みフラグ（0=未投稿, 1=投稿済み） |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | DB 登録日時 |

## 設定ファイル（.env）

### 必須設定項目

| 項目 | 説明 | 例 |
|-----|------|-----|
| `YOUTUBE_CHANNEL_ID` | 監視対象チャンネル ID（UC から始まる ID） | `UCxxxxxxxxxxxxxxxx` |
| `BLUESKY_USERNAME` | Bluesky ハンドル | `yourname.bsky.social` |
| `BLUESKY_PASSWORD` | Bluesky アプリパスワード | `xxxx-xxxx-xxxx-xxxx` |
| `POLL_INTERVAL_MINUTES` | ポーリング間隔（分、最小値: 5、推奨: 10） | `10` |

### オプション設定項目

| 項目 | 説明 | デフォルト |
|-----|------|-----------|
| `BLUESKY_POST_ENABLED` | Bluesky への投稿を有効にするか | `false` ||
| `TIMEZONE` | タイムゾーン設定（system で自動検出） | `system` |

## エラーハンドリング

| エラー | 対応 |
|--------|------|
| .env 未設定 | エラーログ出力して終了 |
| チャンネル ID 無効（UC から始まらない） | ワーニングログ、スキップして次のポーリングへ |
| RSS 取得失敗 | リトライ（最大 3 回、2 秒待機）、失敗時はログ記録 |
| Bluesky 投稿失敗 | ワーニングログ、未投稿状態のまま（次回ポーリングで再試行） |
| 投稿設定無効（BLUESKY_POST_ENABLED=false） | 投稿スキップ、DB への格納のみ実行 |
| DB エラー | エラーログ、クリーンアップして終了 |

## 制限事項（v1）

### RSS 方式の制限
- YouTube の仕様により、RSS で取得可能な動画は通常動画のみ（限定公開、非公開動画は含まない）
- 初回起動後の初回取得で取得されるのは、本アプリ導入以前に公開された通常動画 10 本まで
- それ以上の過去動画の遡及取得は RSS では不可能

### 監視可能のサービスの制限
- 監視対象にできるチャンネルは YouTube 限定、かつ UC から始まるチャンネル ID のみ

### YouTube仕様上の制限
- ライブ配信・動画、プレミア公開、ショート動画、アーカイブの判別不可
- 動画の詳細情報取得（再生回数、高評価数、公開日時など）不可
- UC から始まらないチャンネル ID の監視設定不可

### 他サイトとの連携は未実装
- Twitch 非対応
- ニコニコ動画/生放送 非対応

### v1では未実装の機能
- Discord 通知 非対応
- 詳細なログ設定 非対応
- 投稿への画像添付 非対応
- Docker 対応 非対応
- トンネル連携 非対応
- データベース連携 非対応
- テーマ設定（ダークモード） 非対応

## ライセンス

GNU General Public License v2.0
