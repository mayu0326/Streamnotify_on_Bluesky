# Stream notify on Bluesky - v3 モジュール一覧

**最終更新**: 2025-12-22
**対象バージョン**: v3.2.0+

---

## コアロジック・主要機能モジュール

| ファイル名 | 種類 | 主な用途・役割 | インポート先 |
|-----------|------|-----------------|---------|
| `main_v3.py` | コア | アプリ起動・メインループ・GUI統合・プラグイン管理・AssetManager 統合 | 単体実行（エントリーポイント） |
| `config.py` | コア | 設定読み込み・バリデーション（AUTOPOST・重複投稿防止設定対応） | main_v3.py |
| `database.py` | コア | SQLite 操作・動画管理（YouTube 重複排除・重複投稿検知対応） | main_v3.py、youtube_rss.py、bluesky_plugin.py |
| `youtube_rss.py` | コア | YouTube RSS 取得・パース | main_v3.py |
| `plugin_interface.py` | コア | NotificationPlugin 抽象基底クラス（プラグイン定義） | すべてのプラグイン |
| `plugin_manager.py` | コア | プラグイン自動検出・読み込み・管理 | main_v3.py |
| `bluesky_core.py` | ユーティリティ | Bluesky 投稿機能の本体（ログイン・投稿・Facet構築・Rich Text対応） | bluesky_plugin.py |
| `gui_v3.py` | コア | GUI フレーム統合・動画選択・投稿実行・統計表示・**フィルタリング・重複投稿防止・バックアップ復元** | main_v3.py |
| `image_manager.py` | ユーティリティ | 画像ダウンロード・保存・フォーマット変換・リトライ対応 | bluesky_core.py、niconico_plugin.py |
| `logging_config.py` | ユーティリティ | ロギング統合設定（ロギングプラグイン対応） | main_v3.py |
| `utils_v3.py` | ユーティリティ | 共通関数（日時フォーマット・リトライ・URLバリデーション） | bluesky_core.py、config.py ほか |

---

## テンプレート・テキスト処理モジュール（v3.1.0+）

| ファイル名 | 種類 | 主な用途・役割 | インポート先 |
|-----------|------|-----------------|---------|
| `template_utils.py` | ユーティリティ | Jinja2 テンプレート処理・レンダリング・必須キー検証・フォールバック機能 | bluesky_plugin.py、template_editor_dialog.py |
| `bluesky_template_manager.py` | ユーティリティ | テンプレート選択・キャッシング管理（複数テンプレート対応） | bluesky_plugin.py |
| `template_editor_dialog.py` | GUI | テンプレート編集ダイアログ（Tkinter） | gui_v3.py |

---

## 画像処理・最適化モジュール（v3.1.0+）

| ファイル名 | 種類 | 主な用途・役割 | インポート先 |
|-----------|------|-----------------|---------|
| `image_processor.py` | ユーティリティ | 画像リサイズ・JPEG品質最適化・Bluesky 推奨サイズ自動選定 | bluesky_core.py |

---

## データ管理・キャッシュモジュール

| ファイル名 | 種類 | 主な用途・役割 | インポート先 |
|-----------|------|-----------------|---------|
| `deleted_video_cache.py` | ユーティリティ | 削除済み動画除外リスト管理（JSON ファイルベース、サービス別管理） | database.py、youtube_rss.py |
| `youtube_dedup_priority.py` | ユーティリティ | YouTube 動画優先度ロジック（新動画 > アーカイブ > 通常動画） | database.py |
| `youtube_live_cache.py` | ユーティリティ | YouTube Live 状態キャッシング（配信中・終了検知） | youtube_live_plugin.py |
| `backup_manager.py` | ユーティリティ | DB・テンプレート・設定の ZIP バックアップ/復元 | gui_v3.py |
| `asset_manager.py` | ユーティリティ | Asset ディレクトリからプラグイン用テンプレート・画像を自動配置 | main_v3.py |

---

## 設定ファイル・テンプレート（v3.2.0 対応）

| ファイル名 | 説明 |
|-----------|------|
| `settings.env` | 実行時設定（YouTube チャンネル ID、Bluesky 認証情報、AUTOPOST 設定、テンプレートパス） |
| `settings.env.example` | settings.env テンプレート（全設定項目を記載） |
| `templates/youtube/yt_new_video_template.txt` | YouTube 新着動画投稿用 Jinja2 テンプレート |
| `templates/youtube/yt_online_template.txt` | YouTube Live 配信開始投稿用 Jinja2 テンプレート |
| `templates/youtube/yt_offline_template.txt` | YouTube Live 配信終了投稿用 Jinja2 テンプレート |
| `templates/youtube/yt_archive_template.txt` | YouTube アーカイブ投稿用 Jinja2 テンプレート（v3.1.0+） |
| `templates/youtube/yt_schedule_template.txt` | YouTube 放送枠予約通知用 Jinja2 テンプレート（v3.2.0+） |
| `templates/niconico/nico_new_video_template.txt` | ニコニコ動画投稿用 Jinja2 テンプレート |
| `templates/.templates/default_template.txt` | デフォルトテンプレート（プラグイン非導入時フォールバック） |

---

## プラグインモジュール（plugins/）

| ファイル名 | 種類 | 主な用途・役割 | 対応バージョン |
|-----------|------|-----------------|---------|
| `bluesky_plugin.py` | 投稿プラグイン | Bluesky リッチテキスト・画像添付・テンプレート拡張（自動ロード） | v3.0.0+ |
| `youtube_api_plugin.py` | サイト連携プラグイン | YouTube Data API 連携・UC以外チャンネル ID 対応（自動ロード） | v3.0.0+ |
| `youtube_live_plugin.py` | サイト連携プラグイン | YouTube Live/Archive 判定・自動投稿・ポーリング（youtube_api_plugin 依存、自動ロード） | v3.0.0+ |
| `niconico_plugin.py` | サイト連携プラグイン | ニコニコ動画 RSS 監視・新着通知・テンプレート対応（自動ロード） | v3.0.0+ |
| `logging_plugin.py` | 機能拡張プラグイン | ロギング統合管理・環境変数によるログレベル制御（自動ロード） | v3.0.0+ |

---

## サムネイル・画像処理モジュール（thumbnails/）

| ファイル名 | 説明 |
|-----------|------|
| `__init__.py` | パッケージ初期化・Niconico OGP URL 取得 |
| `image_re_fetch_module.py` | 画像未設定動画のサムネイル再ダウンロード・DB 更新 |
| `niconico_ogp_utils.py` | Niconico OGP メタデータ取得ユーティリティ |
| `niconico_ogp_backfill.py` | Niconico OGP 情報一括バックフィル処理 |
| `youtube_thumb_utils.py` | YouTube サムネイル URL 生成・取得ユーティリティ |
| `youtube_thumb_backfill.py` | YouTube サムネイル一括バックフィル処理 |

---

## データ・ログディレクトリ構成（v3.0.0+）
| ファイル名 | 説明 | ログレベル |
|-----|------|---------|
| `data/video_list.db` | SQLite データベース（YouTube 優先度・重複投稿フラグ対応） | - |
| `data/deleted_videos.json` | 削除済み動画除外リスト（サービス別） | - |
| `logs/app.log` | アプリケーション一般ログ | `LOG_LEVEL_APP` |
| `logs/error.log` | エラー詳細ログ | `LOG_LEVEL_APP` |

---

## 追加データ・ログディレクトリ構成（プラグイン導入時）

| ファイル名 | 説明 | ログレベル |
|-----|------|---------|
| `logs/post.log` | Bluesky 投稿ログ（プラグイン導入時） | `LOG_LEVEL_POST` |
| `logs/post_error.log` | 投稿エラーログ（プラグイン導入時） | `LOG_LEVEL_POST_ERROR` |
| `logs/niconico.log` | ニコニコ動画監視ログ（プラグイン導入時） | `LOG_LEVEL_NICONICO` |
| `logs/youtube.log` | YouTube 監視ログ（プラグイン導入時） | `LOG_LEVEL_YOUTUBE` |
| `logs/audit.log` | 監査ログ（プラグイン導入時） | `LOG_LEVEL_AUDIT` |
| `logs/thumbnails.log` | サムネイル処理ログ（プラグイン導入時） | `LOG_LEVEL_THUMBNAILS` |
| `logs/gui.log` | GUI 操作ログ（プラグイン導入時） | `LOG_LEVEL_GUI` |
| `logs/tunnel.log` | トンネル接続ログ（プラグイン導入時） | `LOG_LEVEL_TUNNEL` |

---

## テンプレート・画像・Asset ディレクトリ構成（プラグイン導入時）

| ファイル名 | 説明 |
| `images/` | 投稿用画像ディレクトリ (Asset から自動配置) |
| `images/YouTube/` | YouTube サムネイル キャッシュ |
| `images/Niconico/` | ニコニコ OGP キャッシュ |
| `templates/` | 投稿用テンプレートディレクトリ (Asset から自動配置) |
| `templates/youtube/` | YouTube テンプレート実行時コピー |
| `templates/niconico/` | ニコニコテンプレート実行時コピー |
| `templates/.templates/` | デフォルト・フォールバック用テンプレート |

---

## Asset 管理モジュール（v3.0.0+）
| ファイル名 | 説明 |
|-----|------|
| `asset_manager.py` | Asset から実行時ディレクトリへのテンプレート・画像自動配置（プラグイン導入時） |
| `Asset/templates/default/` | デフォルトテンプレート配布元 |
| `Asset/templates/youtube/` | YouTube プラグイン用テンプレート配布元 |
| `Asset/templates/niconico/` | ニコニコプラグイン用テンプレート配布元 |
| `Asset/images/default/` | デフォルト画像配布元 |
| `Asset/images/YouTube/` | YouTube 画像配布元 |
| `Asset/images/Niconico/` | ニコニコ画像配布元 |
| `Asset/README.md` | Asset 管理ガイド |

---

## 主要サードパーティライブラリ一覧
| `logs/tuバージョン | 用途 |
|-----------|-----------|------|
| `python-dotenv` | 1.0+ | settings.env ファイル読み込み |
| `feedparser` | 6.0+ | YouTube・ニコニコ RSS パース |
| `atproto` | 0.0.50+ | Bluesky AT Protocol API |
| `requests` | 2.28+ | HTTP リクエスト・API 通信 |
| `Pillow` | 9.0+ | 画像処理（サムネイル保存、リサイズ、形式変換） |
| `beautifulsoup4` | 4.10+ | HTML パース（OGP メタデータ取得） |
| `pytz` | 2021.3+ | タイムゾーン管理 |
| `tzlocal` | 4.0+ | システムタイムゾーン検出 |
| `jinja2` | 3.0+ | テンプレート処理・レンダリング |

---

## バージョン履歴・主要機能追加タイムライン

| バージョン | リリース | 主な追加・変更 |
|-----------|---------|---------|
| v3.0.0 | 2025-12-18 | AssetManager・GUI フィルタ・重複投稿防止・ドキュメント統一 |
| v3.1.0 | 2025-12-18 | フィルタプロファイル保存・DB/設定バックアップ復元 |
| v3.2.0 | 2025-12-18 | YouTube アーカイブテンプレート・放送枠予約テンプレート |

---

## 動作環境要件

| 項目 | 要件 |
|-----|------|
| Python | 3.9 以上 |
| OS | Windows 10 以降、Linux (Debian/Ubuntu)、macOS |
| メモリ | 最小 512 MB (推奨 1 GB以上) |
| ディスク容量 | 100 MB 以上（データベース・ログ・キャッシュ用） |

---

## 関連ドキュメント

- [テンプレートシステムガイド](../Technical/TEMPLATE_SYSTEM.md) - Jinja2 テンプレート仕様・カスタマイズ
- [プラグインシステムガイド](../Technical/PLUGIN_SYSTEM.md) - プラグイン開発・Rich Text Facet 実装
- [AssetManager 統合ガイド](../Technical/ASSET_MANAGER_INTEGRATION_v3.md) - テンプレート・画像自動配置
- [設定項目一覧](../Guides/SETTINGS_OVERVIEW.md) - settings.env 全設定項目
- [デバッグユーティリティ](../../utils/DEBUGGING_UTILITIES.md) - テスト・検証スクリプト
| `asset_manager.py` | Asset ディレクトリからテンプレート・画像を自動配置（プラグイン導入時） |

- `Asset/` ディレクトリに全サービス・全プラグイン用テンプレート/画像を保管
- プラグイン導入時に必要なファイルを Asset から本番ディレクトリに自動コピー（実装完了: 2025-12）
- main_v3.py で自動コピー処理を実行
- 追加済みファイルはプラグイン削除後も残る（手動削除推奨）
