# Stream notify on Bluesky - v2 アーキテクチャ設計

## 概要

特定の YouTube チャンネルの新着動画を RSS で監視し、指定した Bluesky アカウントに自動投稿する常駐ボット。Windows / Linux 対応。

## システムアーキテクチャ

### 処理フロー

```
起動
  ↓
settings.env 読み込み & バリデーション（config.py）
  ↓
SQLite DB 初期化（database.py）
  ↓
YouTube RSS 監視初期化（youtube_rss.py）
  ↓
プラグインマネージャー初期化＆プラグイン読み込み
  └─ 自動ロード: bluesky_plugin, youtube_api_plugin, youtube_live_plugin, niconico_plugin, logging_plugin（存在時）
  ↓
GUI スレッド起動（gui_v2.py、独立して動作）
  ↓
[メインループ] POLL_INTERVAL_MINUTES ごとに以下を繰り返（GUI と並行）:
  ├─ YouTube RSS 取得＆サムネイル自動処理（thumbnails/youtube_thumb_utils.py）
  ├─ 新着動画を DB に保存（database.py）
  ├─ 収集モード（APP_MODE=collect）の場合:
  │   └─ ここで終了（投稿処理スキップ）
  ├─ 通常モード（APP_MODE=normal）の場合:
  │   ├─ GUI で選択された動画を取得（database.py）
  │   ├─ 投稿間隔チェック（POST_INTERVAL_MINUTES = 5分）
  │   └─ 投稿対象あり & 間隔OK なら:
  │       └─ Bluesky に投稿（plugin_manager.post_video_with_all_enabled()）
  │           ├─ bluesky_plugin.py → bluesky_v2.py（投稿実行）
  │           └─ 投稿済みフラグ更新（database.py）
  └─ ポーリング間隔分 sleep（1秒単位でチェック、Ctrl+C 対応）
  ↓
Ctrl+C で安全終了（ニコニコ監視停止）
```

## モジュール構成

### コアロジック

| ファイル名 | 役割 | 内容 |
|-----------|------|------|
| `main_v2.py` | エントリーポイント・メインループ | 起動、プラグイン管理、メインループで RSS → DB → 投稿（GUI と並行実行） |
| `config.py` | 設定読み込み・バリデーション | settings.env から設定取得、値チェック（ポーリング間隔 5 分以上など） |
| `database.py` | SQLite 操作 | テーブル作成、動画の INSERT/SELECT/UPDATE/DELETE、投稿済みフラグ管理、バッチ削除 |
| `youtube_rss.py` | RSS 取得・パース | YouTube チャンネル RSS URL 生成、RSS 取得、新着動画抽出 |
| `plugin_manager.py` | プラグイン管理 | プラグイン自動検出・読み込み・有効化・無効化、メソッド呼び出し |
| `plugin_interface.py` | プラグイン基本インターフェース | プラグイン基本クラス（BasePlugin） |

### 既存ユーティリティ（再利用）

| ファイル名 | 役割 | 内容 |
|-----------|------|------|
| `bluesky_v2.py` | Bluesky 投稿処理 | 画像アップロード、テンプレートレンダ、投稿実行、投稿履歴記録 |
| `logging_config.py` | ロギング設定 | ロガー初期化、ログレベル設定、ファイルローテーション管理 |
| `image_manager.py` | 画像管理 | 画像ダウンロード、形式変換、リトライ処理 |
| `utils_v2.py` | ユーティリティ関数 | 日時フォーマット、リトライデコレータ、URL バリデーション |
| `gui_v2.py` | GUI（Tkinter） | 動画一覧表示、選択、投稿実行、削除、ドライラン、統計表示 |

### プラグイン（plugins/）

| ファイル名 | 種類 | 内容 |
|-----------|------|------|
| `bluesky_plugin.py` | 機能拡張プラグイン | Bluesky 投稿ラッパ（DB レコード → event_context 変換） |
| `niconico_plugin.py`（オプション） | サイト連携プラグイン | ニコニコ動画 RSS 監視・新着通知・DB 保存（独立スレッド） |
| `youtube_api_plugin.py`（オプション） | サイト連携プラグイン | YouTube Data API 連携（チャンネルID解決、動画詳細取得） |
| `youtube_live_plugin.py`（オプション） | サイト連携プラグイン | YouTube ライブ/アーカイブ判定・通知 |
| `logging_plugin.py` | 機能拡張プラグイン | ロギング統合管理（9つのロガー） |

### 画像・サムネイル処理（thumbnails/）

| ファイル名 | 役割 | 内容 |
|-----------|------|------|
| `youtube_thumb_utils.py` | YouTube サムネイル自動処理 | YouTube RSS 取得→DB保存→サムネイル自動ダウンロード を統合処理 |
| `youtube_thumb_backfill.py` | YouTube サムネイル再取得 | DB内で画像未設定の YouTube 動画のサムネイル再ダウンロード（スタンドアロン） |
| `niconico_ogp_utils.py` | ニコニコ OGP 取得 | ニコニコ動画ページのメタタグから OGP サムネイル URL を抽出 |
| `niconico_ogp_backfill.py` | ニコニコ サムネイル一括補完 | DB内で thumbnail_url / image_filename が空のニコニコ動画を一括処理（スタンドアロン） |
| `image_re_fetch_module.py` | 統合サムネイル再取得 | 全ソース（YouTube/Niconico）の画像未設定動画をまとめて再ダウンロード（スタンドアロン） |

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
| `source` | TEXT | DEFAULT 'YouTube' | 動画配信元（YouTube, Niconico など） |
| `posted_to_bluesky` | INTEGER | DEFAULT 0 | 投稿済みフラグ（0=未投稿, 1=投稿済み） |
| `posted_at` | TEXT | | 投稿実行日時（ISO 8601） |
| `selected_for_post` | INTEGER | DEFAULT 0 | 投稿選択フラグ |
| `scheduled_at` | TEXT | | 予約投稿日時 |
| `thumbnail_url` | TEXT | | サムネイル URL |
| `content_type` | TEXT | DEFAULT 'video' | コンテンツ種別（video/live/archive） |
| `live_status` | TEXT | | ライブの状態（upcoming/live/completed） |
| `is_premiere` | INTEGER | DEFAULT 0 | プレミア公開フラグ（0=通常, 1=プレミア） |
| `image_mode` | TEXT | | 画像モード（import, autopost など） |
| `image_filename` | TEXT | | 画像ファイル名 |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | DB 登録日時 |

## 設定ファイル（settings.env）


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
| `BLUESKY_POST_ENABLED` | Bluesky への投稿を有効にするか | `false` |
| `NOTIFY_ON_YT_NEWVIDEO` | YouTube 新着動画投稿時に Bluesky へ通知するか | `False` |
| `YOUTUBE_API_KEY` | YouTube Data API キー（UC 以外のチャンネル識別子対応・ライブ詳細取得用。APIクォータ: 1日10,000ユニット。search.listは1回100ユニット消費（高コスト）。キャッシュ機構あり） | *(任意)* |
| `TIMEZONE` | タイムゾーン設定（system で自動検出） | `system` |
| `DEBUG_MODE` | デバッグモード（true/false、デフォルト: false） | `false` |
| `APP_MODE` | 動作モード（normal, auto_post, dry_run, collect） | `normal` |

## エラーハンドリング

| エラー | 対応 |
|--------|------|
| settings.env 未設定 | エラーログ出力して終了 |
| チャンネル ID 無効（UC から始まらない） | ワーニングログ、スキップして次のポーリングへ |
| RSS 取得失敗 | リトライ（最大 3 回、2 秒待機）、失敗時はログ記録 |
| Bluesky 投稿失敗 | ワーニングログ、未投稿状態のまま（次回ポーリングで再試行） |
| 投稿設定無効（BLUESKY_POST_ENABLED=false） | 投稿スキップ、DB への格納のみ実行 |
| DB エラー | エラーログ、クリーンアップして終了 |

## ロギング設定

### logging_plugin.py による統合ロギング管理

v2 では `logging_plugin.py` により、複数のロガーを一元管理します。

| ロガー名 | 出力先 | デフォルトレベル | 環境変数 | 説明 |
|----------|--------|-----------------|---------|------|
| `AppLogger` | `logs/app.log`, `logs/error.log` | DEBUG（ファイル）, INFO（コンソール） | `LOG_LEVEL_APP` | アプリケーション一般ログ |
| `GUILogger` | `logs/gui.log` | DEBUG | `LOG_LEVEL_GUI` | GUI 操作ログ（動画削除、選択操作等） |
| `PostLogger` | `logs/post.log` | DEBUG | `LOG_LEVEL_POST` | Bluesky 投稿処理ログ（成功） |
| `PostErrorLogger` | `logs/post_error.log` | WARNING | `LOG_LEVEL_POST` | 投稿エラーログ |
| `AuditLogger` | `logs/audit.log` | INFO | `LOG_LEVEL_AUDIT` | 監査ログ（投稿履歴等） |
| `ThumbnailsLogger` | `logs/thumbnails.log` | DEBUG | `LOG_LEVEL_THUMBNAILS` | サムネイル再取得処理ログ |
| `tunnel.logger` | `logs/tunnel.log` | DEBUG | `LOG_LEVEL_TUNNEL` | トンネル接続ログ |
| `YouTubeLogger` | `logs/youtube.log` | DEBUG | `LOG_LEVEL_YOUTUBE` | YouTube 監視ログ |
| `NiconicoLogger` | `logs/niconico.log` | DEBUG | `LOG_LEVEL_NICONICO` | ニコニコ動画監視ログ |

### 設定環境変数

- `LOG_LEVEL_CONSOLE`: コンソール出力レベル（デフォルト: INFO）
- `LOG_LEVEL_FILE`: ファイル出力レベル（デフォルト: DEBUG）
- `LOG_RETENTION_DAYS`: ログファイル保持日数（デフォルト: 14日）
- `LOG_LEVEL_*`: 個別ロガーレベル（空の場合は `LOG_LEVEL_FILE` を使用）

### ログファイル

- `logs/app.log`: アプリケーション一般ログ（日次ローテーション）
- `logs/error.log`: エラーログのみ（日次ローテーション）
- `logs/gui.log`: GUI 操作ログ（動画選択、削除操作等、日次ローテーション）
- `logs/post.log`: Bluesky 投稿成功ログ（日次ローテーション）
- `logs/post_error.log`: 投稿エラーログ（日次ローテーション）
- `logs/audit.log`: 監査ログ（日次ローテーション）
- `logs/thumbnails.log`: サムネイル処理ログ（日次ローテーション）
- `logs/tunnel.log`: トンネル接続ログ（日次ローテーション）
- `logs/youtube.log`: YouTube 監視ログ（日次ローテーション）
- `logs/niconico.log`: ニコニコ動画監視ログ（日次ローテーション）

## 画像管理

### image_manager.py による統合画像管理

`image_manager.py` は以下の機能を提供します：

- **ダウンロード**: URL から画像を HTTP で取得
- **保存**: `images/` ディレクトリにサービス別に保存（YouTube, Niconico など）
- **フォーマット変換**: 複数の画像形式（JPEG, PNG, WebP など）対応
- **リトライ**: 失敗時は最大 3 回リトライ（指数バックオフ）
- **エラーハンドリング**: ダウンロード失敗時は代替画像（noimage.png）を使用

### サムネイル再取得・補完

#### YouTube サムネイル自動取得（RSS ポーリング時）

RSS フェッチ時に新規動画が見つかると、以下の処理が自動実行されます：

1. **サムネイル URL の取得**（image_manager.py）
   - `get_youtube_thumbnail_url()` で複数品質から最適なサムネイル URL を取得
   - 優先度: maxres (1280x720) → sd (640x480) → hq (480x360) → mq (320x180) → default (120x90)
   - URL 取得に失敗した場合は「サムネイル URL なし」として DB に保存

2. **DB への保存**（youtube_rss.py → database.py）
   - 新規動画レコード作成時に `thumbnail_url` カラムに URL を保存

3. **画像ダウンロード**（thumbnails/youtube_thumb_utils.py）
   - メインループ内で `fetch_and_ensure_images()` が実行
   - `thumbnail_url` があり `image_filename` が未設定の動画に対してのみ処理
   - 画像を `images/YouTube/import/` に保存
   - DB の `image_mode` を "import"、`image_filename` をファイル名に更新

**トラブルシューティング:**
- 「サムネイルが取得されていない」場合：
  - `youtube.log` で「サムネイル取得失敗」を確認
  - `youtube_thumb_backfill.py --execute` で手動補完を実行

#### YouTube サムネイル再取得（手動）
`thumbnails/youtube_thumb_backfill.py` は、DB内で画像が未設定の YouTube 動画をスタンドアロン処理します：

```bash
# ドライラン（テスト、実際の変更は行わない）
python -m thumbnails.youtube_thumb_backfill

# 実行（実際にダウンロード・DB更新）
python -m thumbnails.youtube_thumb_backfill --execute

# 詳細ログ表示
python -m thumbnails.youtube_thumb_backfill --execute --verbose
```

#### ニコニコサムネイル一括補完
`thumbnails/niconico_ogp_backfill.py` は、DB内で thumbnail_url / image_filename が空のニコニコ動画を一括処理します：

- OGP メタタグからサムネイル URL を取得（高解像度 1280x720）
- 画像を `images/Niconico/import` に保存
- DB の thumbnail_url / image_mode / image_filename を更新

```bash
# ドライラン（テスト、実際の変更は行わない）
python -m thumbnails.niconico_ogp_backfill

# 実行（実際にダウンロード・DB更新）
python -m thumbnails.niconico_ogp_backfill --execute

# 最大 15 件に制限して実行
python -m thumbnails.niconico_ogp_backfill --execute --limit 10

# 詳細ログ表示
python -m thumbnails.niconico_ogp_backfill --execute --verbose
```

#### 統合サムネイル再取得
`thumbnails/image_re_fetch_module.py` は、全ソース（YouTube/Niconico）の画像未設定動画をまとめて再ダウンロードします：

```bash
# ドライラン（テスト、実際の変更は行わない）
python -m thumbnails.image_re_fetch_module

# 実行（実際にダウンロード・DB更新）
python -m thumbnails.image_re_fetch_module --execute

# 詳細ログ表示
python -m thumbnails.image_re_fetch_module --execute --verbose
```

## プラグインシステム

### プラグインアーキテクチャ

`plugin_manager.py` により、プラグインの自動検出・読み込み・管理を実現します。

プラグインは以下の方式で動作します：

1. **自動ロードプラグイン**: `main_v2.py` 起動時に `plugins/` ディレクトリから自動検出・読み込み
   - `bluesky_plugin.py`: Bluesky 投稿拡張機能（常時読み込み・有効化）
   - `youtube_api_plugin.py`: YouTube Data API 連携（常時読み込み・有効化）
   - `youtube_live_plugin.py`: YouTube ライブ/アーカイブ判定（常時読み込み・有効化、youtube_api_plugin に依存）
   - `niconico_plugin.py`: ニコニコ動画監視（常時読み込み・有効化、別スレッドで監視開始）
   - `logging_plugin.py`: ロギング統合管理（常時読み込み・有効化）

2. **オプショナルプラグイン**: インストール有無で動作切り替え
   - プラグインが存在しない場合は、自動的にバニラ構成にフォールバック

### プラグインの責務分離

| プラグイン | 実行スレッド | 責務 |
|-----------|-----------|------|
| bluesky_plugin | メインループスレッド | 投稿処理ラッパ、event_context 変換 |
| niconico_plugin | 独立スレッド | RSS 監視、新着動画 DB 保存、スケジューリング |
| youtube_api_plugin | メインループスレッド | チャンネルID解決、動画詳細取得（キャッシュ機構あり） |
| logging_plugin | 初期化時 | ロギング設定、9つのロガー管理 |

## GUI（gui_v2.py）

`gui_v2.py` は Tkinter ベースの統合 GUI を提供します：

- **動画一覧表示**: データベース内の動画を表形式で表示
- **動画選択**: チェックボックスで投稿対象を選択
- **投稿実行**: 選択した動画を Bluesky へ投稿
- **ドライラン**: 投稿をシミュレート（実際には投稿しない）
- **動画削除**: DB からの完全削除（ツールバー・右クリックメニュー対応）
- **統計表示**: 投稿数、投稿予定、未処理などの統計情報を表示
- **プラグイン表示**: 導入プラグイン一覧と有効/無効状態を表示

### RSS 方式の制限
- YouTube の仕様により、RSS で取得可能な動画は通常動画のみ（限定公開、非公開動画は含まない）
- 初回起動後の初回取得で取得されるのは、本アプリ導入以前に公開された通常動画 15 本まで
- それ以上の過去動画の遡及取得は RSS では不可能

### 機能実装状況

#### 常時利用可能
- **YouTube RSS 監視**: RSS 経由での新着動画検出
- **Bluesky 投稿**: 選択した動画を Bluesky へ投稿
- **GUI 管理**: Tkinter による動画管理・選択・削除

#### プラグイン導入時に利用可能
- **YouTube API 連携**: チャンネルID解決、動画詳細取得（ライブ判定、プレミア判定等）
- **ニコニコ動画 RSS 監視**: ニコニコ動画の新着検出（niconico_plugin.py）
- **YouTube ライブ判定**: ライブ/アーカイブ判別（youtube_live_plugin.py）
- **ロギング**: 9つのロガーによる詳細なログ出力

#### 非対応機能
- Discord 通知（旧版で実装、v2 では削除）
- Twitch 連携（実装予定）
- トンネル通信（実装予定）
- テーマ設定（実装予定）

## ライセンス

GNU General Public License v2.0
