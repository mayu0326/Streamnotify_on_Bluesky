# YouTube Notifier on Bluesky - v1 モジュール一覧

## コアロジック・主要機能モジュール

| ファイル名 | 種類 | 主な用途・役割 | インポート先 |
|-----------|------|-----------------|---------|
| `main.py` | コア | アプリ起動・メインループ管理 | 単体実行（エントリーポイント） |
| `config.py` | コア | 設定読み込み・バリデーション | main.py |
| `database.py` | コア | SQLite 操作・動画管理 | main.py、youtube_rss.py、bluesky_plugin.py |
| `youtube_rss.py` | コア | RSS 取得・パース | main.py |
| `bluesky_plugin.py` | コア | Bluesky 投稿ラッパ | main.py |
| `bluesky_v1.py` | ユーティリティ | Bluesky 投稿処理（テンプレート・画像） | bluesky_plugin.py |
| `utils_v1.py` | ユーティリティ | 共通関数（日時フォーマット・リトライ） | bluesky_v1.py、config.py ほか |

## 設定ファイル・テンプレート

| ファイル名 | 説明 |
|-----------|------|
| `.env` | 実行時設定（YouTube チャンネル ID、Bluesky 認証情報など） |
| `settings.env.example` | .env テンプレート |

## データ・ログディレクトリ

| パス | 説明 |
|-----|------|
| `data/youtube_notify.db` | SQLite データベース |
| `logs/post_history.csv` | 投稿履歴ログ |
| `logs/app.log` | アプリケーションログ |

## 外部依存ライブラリ

| パッケージ | 用途 |
|-----------|------|
| `python-dotenv` | .env ファイル読み込み |
| `feedparser` | RSS パース |
| `atproto` | Bluesky API |
| `jinja2` | テンプレート処理 |
| `requests` | HTTP リクエスト |
| `pytz, tzlocal` | タイムゾーン管理 |
