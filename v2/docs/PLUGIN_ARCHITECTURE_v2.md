# プラグインアーキテクチャの説明

## 概要

Streamnotify_on_Bluesky は、拡張性を重視したプラグインアーキテクチャを採用しています。
これにより、新しい通知先（Twitch、YouTube Live Chat など）を簡単に追加できます。

## 構成要素

### 1. NotificationPlugin インターフェース (`plugin_interface.py`)

すべての通知プラグインが実装すべき抽象基底クラスです。

**必須メソッド:**
- `post_video(video: Dict) -> bool`: 動画情報をポスト
- `is_available() -> bool`: プラグインが利用可能か判定
- `get_name() -> str`: プラグイン名を取得
- `get_version() -> str`: バージョンを取得

**オプションメソッド:**
- `get_description() -> str`: プラグイン説明
- `on_enable()`: 有効化時のコールバック
- `on_disable()`: 無効化時のコールバック

### 2. BlueskyPlugin (`bluesky_plugin.py`)

NotificationPlugin を実装した Bluesky 用プラグインです。
RichText（Facet）・DRY RUN対応、プラグイン自動ロード方式。

```python
from bluesky_plugin import get_bluesky_plugin

plugin = get_bluesky_plugin(
    username="your-handle.bsky.social",
    password="xxxx-xxxx-xxxx",
    dry_run=False
)

success = plugin.post_video({
    "title": "新着動画",
    "video_url": "https://youtube.com/watch?v=xxx",
    "channel_name": "チャンネル名",
    "published_at": "2025-01-01T10:00:00Z"
})
```

### 3. PluginManager (`plugin_manager.py`)

複数のプラグインを一元管理します。

**機能:**
- プラグインディレクトリからの自動検出・読み込み
- プラグインの有効化・無効化
- すべての有効プラグインでの一括ポスト

```python
from plugin_manager import PluginManager

manager = PluginManager(plugins_dir="plugins")

# プラグインの読み込み
manager.load_plugins_from_directory()

# プラグインの有効化
manager.enable_plugin("bluesky")

# すべての有効プラグインでポスト
results = manager.post_video_with_all_enabled(video_dict)
```

## 新しいプラグインの追加方法

### 1. プラグインディレクトリを作成

```
plugins/
  __init__.py
  twitch_plugin.py
  youtube_chat_plugin.py
```

### 2. NotificationPlugin を実装

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
            return False
    
    def is_available(self) -> bool:
        return self.client is not None
    
    def get_name(self) -> str:
        return "Twitch Notification Plugin"
    
    def get_version(self) -> str:
        return "1.0.0"
```

### 3. PluginManager で読み込む

```python
manager = PluginManager(plugins_dir="plugins")
manager.load_plugins_from_directory()
manager.enable_plugin("twitch")
```

## 拡張可能な設計

- **インターフェース駆動開発**: NotificationPlugin インターフェースにより、疎結合な設計
- **動的読み込み**: `importlib` を使用してプラグインを動的に読み込み
- **ライフサイクル管理**: on_enable/on_disable による初期化・終了処理
- **複数プラグイン対応**: PluginManager が複数プラグインを同時管理

## 今後の拡張例

- Discord Webhook への投稿
- Mastodon / Misskey への投稿

## デザインパターン

このアーキテクチャは以下のデザインパターンを採用しています:

1. **Strategy パターン**: NotificationPlugin インターフェース
2. **Factory パターン**: PluginManager による生成管理
3. **Observer パターン**: on_enable/on_disable コールバック
4. **Chain of Responsibility パターン**: 複数プラグインでの順次処理

## 注記

このドキュメントは旧設計を一部含みますが、基本的なアーキテクチャは現在の実装に対応しています。
詳細な最新仕様は `v2 設計仕様書.md` を参照してください。

## 実装済み情報

- **プラグイン管理**: `plugin_manager.py` が自動ロード方式をサポート
- **自動ロードプラグイン**: `bluesky_plugin.py`（Bluesky 投稿拡張）、`youtube_api_plugin.py`（YouTube API）、`youtube_live_plugin.py`（YouTube ライブ判定）、`niconico_plugin.py`（ニコニコ監視）、`logging_plugin.py`（ロギング管理）
- **Asset ディレクトリ**: テンプレート・画像管理用（プラグイン導入時の自動配置機構は `asset_manager.py` で実装完了: 2025-12）
