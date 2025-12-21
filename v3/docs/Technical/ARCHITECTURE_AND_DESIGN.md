# v3 アーキテクチャと設計方針 - 完全ガイド

**対象バージョン**: v3.1.0+
**最終更新**: 2025-12-18
**ステータス**: ✅ 実装完了・検証済み

---

## 📖 目次

1. [基本方針](#基本方針)
2. [システムアーキテクチャ](#システムアーキテクチャ)
3. [プラグインアーキテクチャ](#プラグインアーキテクチャ)
4. [データベース設計](#データベース設計)
5. [モジュール構成](#モジュール構成)
6. [テンプレートAPI](#テンプレートapi)
7. [プラグイン統合](#プラグイン統合)

---

## 基本方針

### 「コア」と「エクステンション」の分離

StreamNotify v3 は以下の二層構造を採用します：

#### 1. コア（バニラ状態、プラグイン未導入）

**機能範囲**:
- YouTube RSS ポーリング＆RSS解析
- ローカルDB（SQLite `data/video_list.db`）への動画情報保存
- テキスト＋URL による Bluesky 投稿
- ログファイル記録（`logs/app.log`, `logs/error.log`）
- Tkinter GUI による動画表示・選択・投稿実行・統計表示

**責務**:
- RSS から新着動画を検出し、DB に保存（`video_id` で重複判定）
- 投稿対象を DB から取得し、簡潔なテンプレートで投稿
- ユーザーの運用フローをサポート

**実装ファイル**:
- `main_v3.py`: エントリーポイント・メインループ
- `config.py`: 設定読み込み・バリデーション
- `database.py`: SQLite操作・テーブル管理
- `youtube_rss.py`: RSS 取得・パース
- `bluesky_core.py`: Bluesky 投稿処理（ログイン・URL Facet構築）
- `gui_v3.py`: Tkinter GUI
- `logging_config.py`: ロギング設定

#### 2. エクステンション（プラグイン）

**機能範囲**:
- YouTube Data API 連携（ライブ判定、詳細情報取得）
- ニコニコ動画 RSS 監視
- 画像添付・テンプレート処理拡張
- 統合ロギング管理

**責務**:
- コアの NotificationPlugin インターフェース を実装し、`plugins/` ディレクトリに配置
- 自動ロード・有効化される
- コア機能を拡張するが、コアの責務を奪わない

**実装ファイル**:
- `plugins/bluesky_plugin.py`: Bluesky投稿プラグイン
- `plugins/youtube_api_plugin.py`: YouTube API連携
- `plugins/youtube_live_plugin.py`: ライブ判定
- `plugins/niconico_plugin.py`: ニコニコ監視
- `plugins/logging_plugin.py`: ロギング拡張

---

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
GUI スレッド起動（gui_v3.py、独立して動作）
  ↓
[メインループ] POLL_INTERVAL_MINUTES ごとに以下を繰り返（GUI と並行）:
  ├─ YouTube RSS 取得＆サムネイル自動処理
  ├─ 新着動画を DB に保存
  ├─ 収集モード（APP_MODE=collect）の場合:
  │   └─ ここで終了（投稿処理スキップ）
  ├─ 通常モード（APP_MODE=normal）の場合:
  │   ├─ GUI で選択された動画を取得
  │   ├─ 投稿間隔チェック
  │   └─ 投稿対象あり & 間隔OK なら:
  │       └─ Bluesky に投稿
  │           ├─ bluesky_plugin.py → bluesky_core.py（投稿実行）
  │           └─ 投稿済みフラグ更新
  └─ ポーリング間隔分 sleep
  ↓
Ctrl+C で安全終了
```

### GUI レイアウト（v3.1.0+）

```
┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│ StreamNotify on Bluesky - DB 管理                                                        │
├──────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                              │
│ [🔄 再読込] [☑️ 全選択] [☐ 全解除] | [💾 保存] [🗑️ 削除] | [🧪 投稿テスト] [📤 投稿設定] [ℹ️ 統計] [🔌 プラグイン] │
│                                                                                              │
├──────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                              │
│ ☐ │Video ID │公開日時      │配信元    │タイトル            │投稿予定/投稿日時│投稿実績│画像モード│
│ ──┼─────────┼──────────────┼──────────┼────────────────────┼──────────────┼──────┼────────│
│ ☑ │-Vnx9CUo│2025-12-15    │youtube   │[Twitch同時配信]... │2025-12-15    │✓    │import  │
│ ☑ │iB-ajHP│2025-10-29    │youtube   │[Twitch同時配信]... │未明         │✓    │import  │
│ ☐ │p4AJDhen│2025-10-29    │youtube   │[Twitch同時配信]... │未明         │✓    │import  │
│ ☐ │PpCNLENW│2025-10-28    │youtube   │[録：予定時刻]...   │未明         │✓    │import  │
│                                                                                              │
│  （スクロール可能）                                                                          │
│                                                                                              │
├──────────────────────────────────────────────────────────────────────────────────────────────┤
│  読み込み完了: 11 件の動画（選択: 0 件）                                                    │
└──────────────────────────────────────────────────────────────────────────────────────────────┘
```

**✨ v3.1.0 新機能:**
- **🧪 投稿テスト**: DRY RUN モードで投稿をシミュレート
- **📤 投稿設定**: 投稿設定ウィンドウで画像添付・リサイズ設定を調整
- **🔌 プラグイン**: プラグイン管理画面

---

## プラグインアーキテクチャ

### NotificationPlugin インターフェース

すべての通知プラグインが実装すべき抽象基底クラスです。

**必須メソッド**:

```python
class NotificationPlugin(ABC):
    @abstractmethod
    def post_video(self, video: Dict[str, Any]) -> bool:
        """動画情報をポスト"""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """プラグインが利用可能か判定"""
        pass

    @abstractmethod
    def get_name(self) -> str:
        """プラグイン名を取得"""
        pass

    @abstractmethod
    def get_version(self) -> str:
        """バージョンを取得"""
        pass
```

**オプションメソッド**:
- `get_description() -> str`: プラグイン説明
- `on_enable()`: 有効化時のコールバック
- `on_disable()`: 無効化時のコールバック

### PluginManager（プラグイン管理システム）

複数のプラグインを一元管理します。

**機能**:
- プラグインディレクトリからの自動検出・読み込み
- プラグインの有効化・無効化
- すべての有効プラグインでの一括ポスト

**使用例**:

```python
from plugin_manager import PluginManager

manager = PluginManager(plugins_dir="plugins")

# プラグインの読み込み
manager.load_plugins_from_directory()

# プラグインの有効化
manager.enable_plugin("bluesky")

# すべての有効プラグインでポスト
results = manager.post_video_with_all_enabled(video_dict)

# DRY RUN モード
results = manager.post_video_with_all_enabled(video_dict, dry_run=True)
```

### プラグインディレクトリ構造

```
plugins/
  __init__.py
  bluesky_plugin.py          # Bluesky 投稿プラグイン
  youtube_api_plugin.py      # YouTube Data API 連携
  youtube_live_plugin.py     # YouTube ライブ判定
  niconico_plugin.py         # ニコニコ動画 RSS 監視
  logging_plugin.py          # ロギング統合管理
```

### 新しいプラグインの追加方法

#### 1. プラグインクラスを実装

```python
# plugins/twitch_plugin.py

from plugin_interface import NotificationPlugin

class TwitchPlugin(NotificationPlugin):
    def __init__(self):
        self.client = None
        # 初期化処理

    def post_video(self, video: dict) -> bool:
        """Twitch に投稿"""
        try:
            # ポスト処理
            return True
        except Exception as e:
            logger.error(f"❌ Twitch 投稿失敗: {e}")
            return False

    def is_available(self) -> bool:
        """Twitch OAuth トークンが設定されているか"""
        return os.getenv("TWITCH_OAUTH_TOKEN") is not None

    def get_name(self) -> str:
        return "TwitchPlugin"

    def get_version(self) -> str:
        return "1.0.0"

    def get_description(self) -> str:
        return "Twitch チャットに動画を投稿"
```

#### 2. PluginManager が自動ロード

`plugins/` ディレクトリに配置すると、自動的に検出・ロードされます。

---

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
| `source` | TEXT | DEFAULT 'youtube' | 動画配信元（youtube, niconico など）小文字 |
| `posted_to_bluesky` | INTEGER | DEFAULT 0 | 投稿済みフラグ（0=未投稿, 1=投稿済み） |
| `posted_at` | TEXT | | 投稿実行日時（ISO 8601） |
| `content_type` | TEXT | DEFAULT 'video' | コンテンツ種別（"video", "live", "archive", "none"） |
| `live_status` | TEXT | DEFAULT NULL | ライブ配信状態（null, "upcoming", "live", "completed"） |
| `image_filename` | TEXT | | 保存済みサムネイル画像ファイル名 |
| `thumbnail_url` | TEXT | | サムネイル画像の URL |

**値の正規化** (database.py で実施):
- `source`: すべて小文字（"youtube", "niconico"）
- `content_type`: "video", "live", "archive", "none" のいずれか
- `live_status`: null, "none", "upcoming", "live", "completed" のいずれか

---

## モジュール構成

### コアロジック

| ファイル名 | 役割 | 説明 |
|-----------|------|------|
| `main_v3.py` | エントリーポイント・メインループ | 起動、プラグイン管理、メインループで RSS → DB → 投稿 |
| `config.py` | 設定読み込み・バリデーション | settings.env から設定取得、値チェック |
| `database.py` | SQLite 操作 | テーブル作成、INSERT/SELECT/UPDATE/DELETE、値正規化 |
| `youtube_rss.py` | RSS 取得・パース | YouTube チャンネル RSS URL 生成、RSS 取得、新着動画抽出 |
| `plugin_manager.py` | プラグイン管理 | プラグイン自動検出・読み込み・有効化・無効化 |
| `plugin_interface.py` | プラグイン基本インターフェース | プラグイン基本クラス（NotificationPlugin） |

### ユーティリティ

| ファイル名 | 役割 | 説明 |
|-----------|------|------|
| `bluesky_core.py` | Bluesky 投稿処理 | 画像アップロード、テンプレートレンダ、投稿実行 |
| `logging_config.py` | ロギング設定 | ロガー初期化、ログレベル設定、ファイルローテーション |
| `image_manager.py` | 画像管理 | 画像ダウンロード、形式変換、リトライ処理 |
| `image_processor.py` | 画像リサイズ処理 | 三段階リサイズ戦略、JPEG品質最適化 |
| `utils_v3.py` | ユーティリティ関数 | 日時フォーマット、リトライデコレータ |
| `gui_v3.py` | GUI（Tkinter） | 動画一覧表示、選択、投稿実行、削除 |

### プラグイン

| ファイル名 | 種類 | 説明 |
|-----------|------|------|
| `bluesky_plugin.py` | 機能拡張 | Bluesky 投稿ラッパ |
| `niconico_plugin.py` | サイト連携 | ニコニコ動画 RSS 監視 |
| `youtube_api_plugin.py` | サイト連携 | YouTube Data API 連携 |
| `youtube_live_plugin.py` | サイト連携 | YouTube ライブ判定（実験的） |
| `logging_plugin.py` | 機能拡張 | ロギング統合管理 |

---

## テンプレートAPI

### API安定化とUI分離

テンプレートは Jinja2 形式とし、以下の `event_context` dict を常に受け取れることを保証します：

### event_context キー定義

| キー名 | 型 | 説明 | 変更禁止 |
|--------|----|----|---------|
| `title` | str | 動画タイトル | ✅ |
| `video_id` | str | YouTube/ニコニコ等の動画ID | ✅ |
| `video_url` | str | 動画URL | ✅ |
| `channel_name` | str | チャンネル名 | ✅ |
| `published_at` | str | 公開日時（ISO 8601） | ✅ |
| `source` | str | 動画配信元（小文字："youtube", "niconico"） | ✅ |
| `content_type` | str | コンテンツ種別（"video", "live", "archive", "none"） | ✅ |
| `live_status` | str or None | ライブ配信の状態（null, "upcoming", "live", "completed"） | ✅ |
| `image_filename` | str | 保存済みサムネイル画像ファイル名 | ✅ |
| `posted_at` | str | Bluesky投稿日時（ISO 8601、未投稿時はNone） | ✅ |

### テンプレートファイル置き場所

```
templates/
├── youtube/
│   ├── yt_new_video_template.txt      # YouTube新着動画用
│   ├── yt_online_template.txt         # YouTube配信開始用（将来）
│   └── yt_offline_template.txt        # YouTube配信終了用（将来）
└── niconico/
    └── nico_new_video_template.txt    # ニコニコ新着動画用
```

### 拡張ルール

- **既存キーの削除・型変更は禁止**
- **新規キーの追加は OK** だが、テンプレートファイルとドキュメントを同時に更新
- **後方互換性を維持**（古いテンプレートファイルも動作するように）

---

## プラグイン統合

### main_v3.py での PluginManager 統合

```python
# main_v3.py 内の実装
from plugin_manager import PluginManager

plugin_manager = PluginManager(plugins_dir="plugins")
# プラグインディレクトリから自動ロード
plugin_manager.load_plugins_from_directory()

# GUI に渡す
gui = StreamNotifyGUI(root, db, plugin_manager)

# GUI 内で使用
results = self.plugin_manager.post_video_with_all_enabled(video, dry_run=False)
# DRY RUN: results = self.plugin_manager.post_video_with_all_enabled(video, dry_run=True)
```

### 呼び出しフロー

```
main_v3.py::main()
│
├─ config.py から設定読み込み
├─ logging_config.py でロギング初期化
├─ database.py からDB初期化
├─ plugin_manager.py でプラグイン管理システム初期化
│  └─ plugins/ ディレクトリから全プラグインを自動ロード
├─ youtube_rss.py からRSS取得
└─ GUI をマルチスレッドで起動
   ├─ StreamNotifyGUI(root, db, plugin_manager)
   │  └─ setup_ui()
   │     └─ execute_post() → plugin_manager.post_video_with_all_enabled()
   └─ メインループでポーリング継続
```

---

**作成日**: 2025-12-18
**最後の修正**: 2025-12-18
**ステータス**: ✅ 完成・検証済み

