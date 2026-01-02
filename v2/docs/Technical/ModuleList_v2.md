# Stream notify on Bluesky - v2 モジュール一覧

## コアロジック・主要機能モジュール

| ファイル名 | 種類 | 主な用途・役割 | インポート先 |
|-----------|------|-----------------|---------|
| `main_v2.py` | コア | アプリ起動・メインループ・GUI統合・プラグイン管理 | 単体実行（エントリーポイント） |
| `config.py` | コア | 設定読み込み・バリデーション（拡張設定項目対応） | main_v2.py |
| `database.py` | コア | SQLite 操作・動画管理（拡張カラム対応、**content_type/live_status 値正規化**） | main_v2.py、youtube_rss.py、bluesky_plugin.py |
| `youtube_rss.py` | コア | RSS 取得・パース | main_v2.py |
| `plugin_interface.py` | コア | NotificationPlugin 抽象基底クラス（プラグイン定義） | すべてのプラグイン |
| `plugin_manager.py` | コア | プラグイン自動検出・読み込み・管理 | main_v2.py |
| `bluesky_core.py` | ユーティリティ | Bluesky 投稿機能の本体（ログイン・投稿・Facet構築） | bluesky_plugin.py |
| `gui_v2.py` | コア | GUI フレーム統合・動画選択・投稿実行・統計表示 | main_v2.py |
| `image_manager.py` | ユーティリティ | 画像ダウンロード・保存・フォーマット変換・リトライ対応 | bluesky_core.py、niconico_plugin.py |
| `logging_config.py` | ユーティリティ | ロギング統合設定（ロギングプラグイン対応） | main_v2.py |
| `utils_v2.py` | ユーティリティ | 共通関数（日時フォーマット・リトライ・URLバリデーション） | bluesky_core.py、config.py ほか |

## 設定ファイル・テンプレート

| ファイル名 | 説明 |
|-----------|------|
| `settings.env` | 実行時設定（YouTube チャンネル ID、Bluesky 認証情報、拡張設定項目など） |
| `settings.env.example` | settings.env テンプレート |
| `templates/youtube/yt_new_video_template.txt` | YouTube 新着動画投稿用 Jinja2 テンプレート |
| `templates/youtube/yt_offline_template.txt` | YouTube放送終了投稿用 Jinja2 テンプレート |
| `templates/youtube/yt_online_template.txt` | YouTube放送開始投稿用 Jinja2 テンプレート |
| `templates/niconico/nico_new_video_template.txt` | ニコニコ動画投稿用 Jinja2 テンプレート |

## プラグインモジュール（plugins/）

| ファイル名 | 種類 | 主な用途・役割 |
|-----------|------|-----------------|
| `bluesky_plugin.py` | 投稿プラグイン | Bluesky 画像添付・テンプレート拡張機能（自動ロード）|
| `youtube_api_plugin.py` | サイト連携プラグイン | YouTube Data API 連携（UC以外チャンネルID対応、自動ロード） |
| `youtube_live_plugin.py` | サイト連携プラグイン | YouTube ライブ/アーカイブ判定・通知
（youtube_api_plugin.py に依存、自動ロード） |
| `niconico_plugin.py` | サイト連携プラグイン | ニコニコ動画 RSS 監視・新着通知（自動ロード） |
| `logging_plugin.py` | 機能拡張プラグイン | ロギング統合管理（環境変数によるログレベル制御、自動ロード） |

## サムネイル・画像処理モジュール（thumbnails/）

| ファイル名 | 説明 |
|-----------|------|
| `__init__.py` | パッケージ初期化・Niconico OGP URL 取得 |
| `image_re_fetch_module.py` | 画像未設定動画のサムネイル再ダウンロード・DB更新 |
| `niconico_ogp_utils.py` | Niconico OGP 取得ユーティリティ |
| `niconico_ogp_backfill.py` | Niconico OGP 情報バックフィル処理 |
| `youtube_thumb_utils.py` | YouTube サムネイル取得ユーティリティ |
| `youtube_thumb_backfill.py` | YouTube サムネイル情報バックフィル処理 |

## データ・ログディレクトリ

| パス | 説明 |
|-----|------|
| `data/video_list.db` | SQLite データベース（拡張カラム対応）|
| `logs/app.log` | アプリケーション一般ログ（AppLogger、バニラ）|
| `logs/error.log` | エラーログ（AppLogger、バニラ）|
| `logs/post.log` | Bluesky 投稿ログ（PostLogger、プラグイン導入時）|
| `logs/post_error.log` | Bluesky 投稿エラーログ（PostErrorLogger、プラグイン導入時）|
| `logs/niconico.log` | ニコニコ動画監視ログ（NiconicoLogger、プラグイン導入時）|
| `logs/youtube.log` | YouTube 監視ログ（YouTubeLogger、プラグイン導入時）|
| `logs/audit.log` | 監査ログ（AuditLogger、プラグイン導入時）|
| `logs/thumbnails.log` | サムネイル処理ログ（ThumbnailsLogger、プラグイン導入時）|
| `logs/gui.log` | GUI 操作ログ（GUILogger、プラグイン導入時）|
| `logs/tunnel.log` | トンネル接続ログ（TunnelLogger、プラグイン導入時）|
| `images/` | 投稿用画像ディレクトリ (プラグイン導入時) |
| `templates/` | 投稿用テンプレートディレクトリ (プラグイン導入時) |

## 外部依存ライブラリ

| パッケージ | 用途 |
|-----------|------|
| `python-dotenv` | .env ファイル読み込み |
| `feedparser` | RSS パース |
| `atproto` | Bluesky API |
| `requests` | HTTP リクエスト |
| `Pillow` | 画像処理（サムネイル保存、リサイズ） |
| `beautifulsoup4` | HTML パース（OGP取得） |
| `pytz, tzlocal` | タイムゾーン管理 |
| `jinja2` | テンプレート処理（Bluesky機能拡張プラグイン用） |

## Assetディレクトリによるテンプレート・画像管理

| ファイル名 | 説明 |
|-----------|------|
| `asset_manager.py` | Asset ディレクトリからテンプレート・画像を自動配置（プラグイン導入時） |

- `Asset/` ディレクトリに全サービス・全プラグイン用テンプレート/画像を保管
- プラグイン導入時に必要なファイルを Asset から本番ディレクトリに自動コピー（実装完了: 2025-12）
- main_v2.py で自動コピー処理を実行
- 追加済みファイルはプラグイン削除後も残る（手動削除推奨）
