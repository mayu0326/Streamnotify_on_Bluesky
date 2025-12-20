# 包括的なAutopost（自動投稿）ロジック解析ドキュメント

**Date:** 2025年12月20日
**Version:** v3.x
**Status:** 完成・検証済み

---

## 📋 目次

1. [概要](#概要)
2. [動作モード体系](#動作モード体系)
3. [プラットフォーム別Autopost実装](#プラットフォーム別autopost実装)
4. [YouTubeLive イベントポスティング](#youtubelive-イベントポスティング)
5. [Niconico 自動投稿](#niconico-自動投稿)
6. [共通ロジック](#共通ロジック)
7. [フロー図](#フロー図)

---

## 概要

Streamnotify on Bluesky v3 は、複数のプラットフォーム（YouTube、YouTubeLive、Niconico）から動画・配信情報を自動収集し、設定に基づいて Bluesky に自動投稿する機能を提供します。

### 主な特徴

- ✅ **複数プラットフォーム対応**: YouTube、YouTubeLive、Niconico
- ✅ **柔軟な動作モード**: 通常、自動投稿、ドライラン、収集専用
- ✅ **プラグインベースアーキテクチャ**: 各プラットフォームをプラグインで実装
- ✅ **テンプレートシステム**: プラットフォーム別・イベント別のテンプレート対応
- ✅ **画像管理**: autopost モード専用の画像管理機構

---

## 動作モード体系

### 4つの動作モード

動作モードは `config.py` で定義され、`APP_MODE` 環境変数で制御されます。

#### 1. **NORMAL モード** (通常モード)

```
状態: 収集＋手動投稿
設定値: APP_MODE=normal
Bluesky投稿: 有効（ただし手動実行）
説明: RSS取得で DB に動画を保存し、GUI から手動で投稿を選択・実行
ユースケース: ユーザーが投稿内容を確認してから投稿したい場合
```

**実装コード** (`config.py`):
```python
class OperationMode:
    NORMAL = "normal"           # 通常モード（収集＋手動投稿）
```

#### 2. **AUTO_POST モード** (自動投稿モード)

```
状態: 収集＋自動投稿
設定値: APP_MODE=auto_post + BLUESKY_POST_ENABLED=true
Bluesky投稿: 有効（自動実行）
説明: RSS取得で DB に動画を保存し、定期的に自動選択して投稿
ユースケース: 投稿タイミングを自動化したい場合
```

**実装コード** (`config.py`):
```python
elif app_mode == OperationMode.AUTO_POST and self.bluesky_post_enabled:
    self.operation_mode = OperationMode.AUTO_POST
```

**自動投稿フロー** (`main_v3.py`):
```python
# アプリケーション起動時に自動投稿スレッドを開始
gui_thread = threading.Thread(
    target=run_gui,
    args=(db, plugin_manager, stop_event, bluesky_core),
    daemon=True
)
gui_thread.start()
```

**GUI での自動投稿実行** (`gui_v3.py`):
```python
# GUI スレッド内で定期的に実行
selected_video = self.db.get_selected_videos()
if selected_video:
    results = plugin_manager.post_video_with_all_enabled(selected_video)
```

#### 3. **DRY_RUN モード** (デバッグモード)

```
状態: 収集＋投稿シミュレーション
設定値: APP_MODE=dry_run
Bluesky投稿: 無効（シミュレーションのみ）
説明: 投稿をシミュレートするが、実際には Bluesky に投稿しない
ユースケース: 投稿内容を確認したい場合、動作テスト
```

**実装コード** (`config.py`):
```python
elif app_mode == OperationMode.DRY_RUN:
    self.operation_mode = OperationMode.DRY_RUN
```

**ドライランの無効化** (`bluesky_core.py`):
```python
bluesky_core = BlueskyMinimalPoster(
    config.bluesky_username,
    config.bluesky_password,
    dry_run=not config.bluesky_post_enabled  # 投稿を無効化
)
```

#### 4. **COLLECT モード** (収集専用モード)

```
状態: RSS取得のみ
設定値: APP_MODE=collect または DB が存在しない（初回起動）
Bluesky投稿: 無効
説明: RSS を取得して DB に保存するだけ。投稿機能は完全に無効
ユースケース: データ収集フェーズ、DB 初期化
```

**実装コード** (`config.py`):
```python
if not db_exists or app_mode == OperationMode.COLLECT:
    self.operation_mode = OperationMode.COLLECT
```

### モード判定フロー

```
┌─────────────────────────────────────┐
│ APP_MODE 環境変数を確認             │
└────────────┬────────────────────────┘
             │
    ┌────────┴────────┬──────────┬────────────┐
    │                 │          │            │
    ▼                 ▼          ▼            ▼
┌────────┐      ┌──────────┐  ┌──────┐  ┌────────┐
│ normal │      │auto_post │  │dryrun│  │collect │
└────────┘      └──────────┘  └──────┘  └────────┘
    │                 │          │           │
    │                 ▼          │           │
    │          BLUESKY_POST_     │           │
    │          ENABLED=true?     │           │
    │             Yes?           │           │
    │                 │          │           │
    │                 ▼          ▼           ▼
    └─────────────▶ NORMAL  DRY_RUN  COLLECT
```

---

## プラットフォーム別Autopost実装

### 3つの主要プラットフォーム

v3 では以下の 3 つのプラットフォームをサポートしています。

| プラットフォーム | プラグイン | 機能 | Autopost対応 |
|:--|:--|:--|:--:|
| YouTube | `youtube_api_plugin` | 新着動画検出、詳細情報取得 | ✅ |
| YouTube Live | `youtube_live_plugin` | ライブ/アーカイブ判定、自動投稿 | ✅ |
| Niconico | `niconico_plugin` | RSS監視、新着投稿 | ✅ |

---

## YouTubeLive イベントポスティング

### 概要

YouTube Live イベントの投稿は以下の 4 つのステージで構成されます。

1. **スケジュール**: 予定されたライブをキャッシュに登録
2. **開始**: ライブ配信が開始されたことを検知して投稿
3. **終了**: ライブ配信が終了したことを検知して投稿
4. **アーカイブ**: 配信終了後、アーカイブが公開された時点での処理

### ステージ 1: スケジュール（予定されたライブ）

#### データソース

YouTube API から取得した `liveStreamingDetails` より：
- `scheduledStartTime`: 予定開始時刻
- `actualStartTime`: 実際の開始時刻（ライブ開始時に設定）
- `actualEndTime`: 実際の終了時刻（ライブ終了時に設定）

#### キャッシュ管理

ファイル: `youtube_live_cache.py`

```python
# ライブ動画をキャッシュに追加
def add_live_video(video_id, title, start_time):
    live_videos[video_id] = {
        "title": title,
        "start_time": start_time,
        "status": "upcoming"        # 予定中
    }

# キャッシュをファイルに保存
def save_live_cache():
    with open(LIVE_CACHE_FILE, "w") as f:
        json.dump(live_videos, f, indent=2)
```

#### DB への永続化

ファイル: `youtube_live_plugin.py`

```python
def post_video(self, video: Dict[str, Any]) -> bool:
    # YouTubeAPI から詳細を取得
    details = self.api_plugin._fetch_video_detail(video_id)

    # ライブ/アーカイブ判定
    content_type, live_status, is_premiere = self._classify_live(details)

    # DB に保存
    return self.db.insert_video(
        video_id=video_id,
        title=title,
        content_type=content_type,      # "live", "archive", "video"
        live_status=live_status,        # "upcoming", "live", "completed"
        is_premiere=is_premiere
    )
```

#### DB スキーマ

`database.py` - videos テーブル：

```sql
CREATE TABLE videos (
    -- 基本情報
    id INTEGER PRIMARY KEY,
    video_id TEXT UNIQUE,
    title TEXT,
    video_url TEXT,

    -- コンテンツタイプ（新規フィールド）
    content_type TEXT DEFAULT 'video',  -- "video", "live", "archive"
    live_status TEXT,                   -- NULL, "upcoming", "live", "completed"
    is_premiere INTEGER DEFAULT 0,      -- 0 or 1

    -- その他
    posted_to_bluesky INTEGER DEFAULT 0,
    posted_at TEXT,
    ...
)
```

### ステージ 2: 開始（ライブ配信開始）

#### 検知方法

**方法 A: RSS フィード から検知（初期検知）**

RSS フィードで新着として検知された時点で `live_status="upcoming"` で DB に登録。
その後、API でライブ開始を確認。

**方法 B: API ポーリング から検知（継続監視）**

定期的に API でライブ中の動画をチェック：

```python
def poll_live_status(self) -> None:
    """
    ライブ中の動画を定期チェックし、終了を検知

    フロー：
    ① DB から live_status='live' の動画を取得
    ② 各動画の現在状態を API で確認
    ③ キャッシュを更新
    ④ 開始イベント検知 → 自動投稿
    """
```

#### 自動投稿実行

ファイル: `youtube_live_plugin.py`

```python
def auto_post_live_start(self, video: Dict[str, Any]) -> bool:
    """
    ライブ開始時の自動投稿

    Args:
        video: {video_id, title, live_status="live"}

    Returns:
        bool: 投稿成功フラグ
    """
    # Bluesky プラグインを取得
    from plugin_manager import PluginManager
    pm = PluginManager()
    bluesky_plugin = pm.get_plugin("bluesky_plugin")

    # ライブ開始テンプレート指定
    video_copy = dict(video)
    video_copy["event_type"] = "live_start"
    video_copy["live_status"] = "live"

    logger.info(f"📡 ライブ開始自動投稿を実行します: {video.get('title')}")
    return bluesky_plugin.post_video(video_copy)
```

#### テンプレート選択

ファイル: `bluesky_plugin.py`

```python
# event_type フィールドに基づいてテンプレートを選択
if event_type == "live_start":
    template_env = os.getenv("TEMPLATE_YOUTUBE_ONLINE_PATH")
    # ライブ開始専用テンプレート: templates/youtube/yt_online_template.txt
elif event_type == "live_end":
    template_env = os.getenv("TEMPLATE_YOUTUBE_OFFLINE_PATH")
    # ライブ終了専用テンプレート: templates/youtube/yt_offline_template.txt
```

#### 設定フラグ

ファイル: `settings.env.example`

```env
# ライブ開始時の自動投稿を有効にするか（デフォルト: true）
YOUTUBE_LIVE_AUTO_POST_START=true

# テンプレートパス
TEMPLATE_YOUTUBE_ONLINE_PATH=templates/youtube/yt_online_template.txt
```

### ステージ 3: 終了（ライブ配信終了）

#### 終了検知

API ポーリング で `live_status` が `"completed"` に変化を検知：

```python
# main_v3.py - YouTube Live 終了検知用ポーリングスレッド
def start_youtube_live_polling():
    """YouTubeLive ライブ終了検知の定期ポーリングを開始"""

    poll_interval_minutes = int(os.getenv("YOUTUBE_LIVE_POLL_INTERVAL", "15"))

    # バリデーション：最短15分、最長60分
    if poll_interval_minutes < 15:
        poll_interval_minutes = 15
    elif poll_interval_minutes > 60:
        poll_interval_minutes = 60

    # 定期ポーリングを実行
    while not stop_event.is_set():
        youtube_live_plugin.poll_live_status()
        time.sleep(poll_interval_minutes * 60)
```

#### 自動投稿実行

ファイル: `youtube_live_plugin.py`

```python
def auto_post_live_end(self, video: Dict[str, Any]) -> bool:
    """
    ライブ終了時の自動投稿

    Args:
        video: {video_id, title, live_status="completed"}

    Returns:
        bool: 投稿成功フラグ
    """
    from plugin_manager import PluginManager
    pm = PluginManager()
    bluesky_plugin = pm.get_plugin("bluesky_plugin")

    # ライブ終了テンプレート指定
    video_copy = dict(video)
    video_copy["event_type"] = "live_end"
    video_copy["live_status"] = "completed"

    logger.info(f"📡 ライブ終了自動投稿を実行します: {video.get('title')}")
    return bluesky_plugin.post_video(video_copy)
```

#### 設定フラグ

ファイル: `settings.env.example`

```env
# ライブ終了時の自動投稿を有効にするか（デフォルト: true）
YOUTUBE_LIVE_AUTO_POST_END=true

# テンプレートパス
TEMPLATE_YOUTUBE_OFFLINE_PATH=templates/youtube/yt_offline_template.txt

# ライブ終了検知の定期ポーリング間隔（分、デフォルト: 15、最短: 15、最長: 60）
YOUTUBE_LIVE_POLL_INTERVAL=15
```

### ステージ 4: アーカイブ（配信終了後）

#### アーカイブ判定

配信終了後、YouTube はアーカイブ（録画）を自動的に公開します。
アーカイブは DB に以下の状態で登録されます：

```python
content_type = "archive"        # アーカイブ
live_status = None              # ライブではない
is_premiere = 0                 # プレミア配信ではない
```

#### アーカイブテンプレート

ファイル: `bluesky_plugin.py`

```python
# content_type フィールドに基づいてテンプレートを選択
if content_type == "archive":
    template_env = os.getenv("TEMPLATE_YOUTUBE_ARCHIVE_PATH")
    # アーカイブ専用テンプレート: templates/youtube/yt_archive_template.txt
    # 未設定時は youtube_new_video テンプレートにフォールバック
```

#### 設定

ファイル: `settings.env.example`

```env
# YouTube アーカイブ投稿用テンプレート
TEMPLATE_YOUTUBE_ARCHIVE_PATH=templates/youtube/yt_archive_template.txt
```

---

## Niconico 自動投稿

### 概要

Niconico からの自動投稿は、RSS フィードの監視と DB への自動登録により実現されます。

### 実装ファイル

**プラグイン**: `plugins/niconico_plugin.py`
**DB**: `database.py`

### RSS 監視ロジック

#### 1. RSS 定期取得

```python
class NiconicoPlugin(NotificationPlugin):
    def start_monitoring(self):
        """ニコニコ RSS 監視スレッドを開始"""

        def monitor_rss():
            while not stop_event.is_set():
                # RSS フィードを取得
                entries = self.fetch_rss_feed()

                if entries:
                    # 最新動画を検索
                    video_entry = self.get_latest_video_entry()

                    # 新着判定
                    if not self.last_video_id or video_entry.get("id") != self.last_video_id:
                        # 新着動画あり
                        video = self._entry_to_video_dict(video_entry)
                        is_new = self.post_video(video)

                        if is_new:
                            logger.info(f"✅ 1 個の新着動画を保存しました")

                        self.last_video_id = video_entry.get("id")

                # ポーリング間隔待機
                time.sleep(poll_interval_minutes * 60)

        # スレッドで実行
        thread = threading.Thread(target=monitor_rss, daemon=True)
        thread.start()
```

#### 2. 新着判定

```python
# 前回取得した最後の動画ID と現在のRSS比較
if not self.last_video_id or video_entry.get("id") != self.last_video_id:
    # 新着動画あり
    is_new = self.post_video(video)
```

#### 3. DB への自動登録

```python
def post_video(self, video: Dict[str, Any]) -> bool:
    """
    動画情報を DB に保存

    Args:
        video: {video_id, title, video_url, published_at, channel_name, ...}

    Returns:
        bool: 成功時 True（新規登録）、既存の場合 False
    """

    is_new = self.db.insert_video(
        video_id=video_id,
        title=title,
        video_url=video_url,
        published_at=published_at,
        channel_name=channel_name,
        source="niconico"          # ソースを指定
    )

    if is_new:
        logger.info(f"✅ 新着動画を保存しました: {title}")

    return is_new
```

### 設定

ファイル: `settings.env.example`

```env
# 監視対象のニコニコユーザーID（数字のみ）
NICONICO_USER_ID=

# ニコニコのユーザー名（テンプレートで投稿者として表示）
NICONICO_USER_NAME=

# ニコニコのポーリング間隔（分、デフォルト: 10）
NICONICO_LIVE_POLL_INTERVAL=10

# ニコニコ新着動画投稿用テンプレート
TEMPLATE_NICO_NEW_VIDEO_PATH=templates/niconico/nico_new_video_template.txt
```

---

## 共通ロジック

### 1. プラグイン共通インターフェース

#### 実装ファイル: `plugin_interface.py`

すべてのプラグインが実装すべき抽象インターフェース：

```python
class NotificationPlugin(ABC):
    """通知プラグインの基底クラス"""

    @abstractmethod
    def is_available(self) -> bool:
        """プラグインが利用可能かどうかを判定"""
        pass

    @abstractmethod
    def post_video(self, video: Dict[str, Any]) -> bool:
        """
        動画情報を通知先にポスト

        Args:
            video: 動画情報辞書

        Returns:
            bool: ポスト成功時 True
        """
        pass

    @abstractmethod
    def get_name(self) -> str:
        """プラグイン名を取得"""
        pass

    @abstractmethod
    def get_version(self) -> str:
        """プラグインのバージョンを取得"""
        pass
```

### 2. プラグイン管理

#### 実装ファイル: `plugin_manager.py`

```python
class PluginManager:
    """プラグインのロード・管理を行う"""

    def post_video_with_all_enabled(self, video: dict, dry_run: bool = False) -> Dict[str, bool]:
        """
        有効化されているすべてのプラグインで post_video を実行

        Args:
            video: 動画情報
            dry_run: ドライランモード（投稿シミュレーション）

        Returns:
            Dict[str, bool]: {プラグイン名: 成功フラグ}
        """
        results = {}

        for plugin_name, plugin in self.enabled_plugins.items():
            if plugin.is_available():
                success = plugin.post_video(video)
                results[plugin_name] = success
                logger.info(f"投稿完了: {plugin_name} = {success}")

        return results
```

### 3. 画像管理（autopost モード）

#### 実装ファイル: `image_manager.py`

**autopost モード専用の画像管理**:

```python
class ImageManager:
    def save_image(self, video: Dict, image_data: bytes, site: str, mode: str = "autopost") -> Optional[str]:
        """
        画像をファイルに保存（autopost モード）

        Args:
            video: 動画情報
            image_data: 画像バイナリ
            site: サイト名（"YouTube", "Niconico", ...）
            mode: "autopost" または "import"

        Returns:
            str: 保存されたファイルパス、失敗時 None

        保存先:
            - autopost モード: images/{site}/autopost/{filename}
            - import モード: images/{site}/{filename}
        """

        if mode == "autopost":
            # autopost 専用ディレクトリに保存
            path = self.base_dir / site / "autopost" / filename
            path.parent.mkdir(parents=True, exist_ok=True)

            with open(path, "wb") as f:
                f.write(image_data)

            logger.info(f"✅ autopost画像保存: {path}")
            return str(path)
```

#### ディレクトリ構造

```
images/
├── YouTube/
│   ├── autopost/             ← autopost モード専用
│   │   ├── video1.jpg
│   │   ├── video2.jpg
│   │   └── ...
│   └── (その他のモード用)
│
├── Niconico/
│   ├── autopost/
│   │   ├── video1.jpg
│   │   └── ...
│   └── ...
│
└── default/
    └── noimage.png
```

### 4. テンプレートシステム

#### テンプレートパス定義

ファイル: `settings.env.example`

```env
# YouTube テンプレート
TEMPLATE_YOUTUBE_NEW_VIDEO_PATH=templates/youtube/yt_new_video_template.txt
TEMPLATE_YOUTUBE_ONLINE_PATH=templates/youtube/yt_online_template.txt
TEMPLATE_YOUTUBE_OFFLINE_PATH=templates/youtube/yt_offline_template.txt
TEMPLATE_YOUTUBE_ARCHIVE_PATH=templates/youtube/yt_archive_template.txt

# Niconico テンプレート
TEMPLATE_NICO_NEW_VIDEO_PATH=templates/niconico/nico_new_video_template.txt
```

#### テンプレート変数

**YouTube 新着動画**:
- `{{ title }}`: 動画タイトル
- `{{ video_id }}`: 動画ID
- `{{ video_url }}`: 動画URL
- `{{ channel_name }}`: チャンネル名
- `{{ published_at }}`: 公開日時

**Niconico 新着動画**:
- `{{ title }}`: 動画タイトル
- `{{ video_id }}`: 動画ID
- `{{ video_url }}`: 動画URL
- `{{ channel_name }}`: ユーザー名
- `{{ published_at }}`: 公開日時

---

## フロー図

### 全体フロー

```
┌─────────────────────────────────────────────────────────┐
│ アプリケーション起動 (main_v3.py)                      │
└────────────────────┬────────────────────────────────────┘
                     │
         ┌───────────┴───────────┐
         │                       │
         ▼                       ▼
┌────────────────────┐  ┌──────────────────────┐
│ 設定読み込み       │  │ プラグイン初期化    │
│ (config.py)        │  │ (plugin_manager.py)  │
└────────┬───────────┘  └────────┬─────────────┘
         │                      │
         │  ┌──────────────────┘
         │  │
         ▼  ▼
    ┌────────────────┐
    │ 動作モード決定  │
    │                │
    │ NORMAL/        │
    │ AUTO_POST/     │
    │ DRY_RUN/       │
    │ COLLECT        │
    └────┬───────────┘
         │
    ┌────┴────┬─────────┬──────────┐
    │          │         │          │
    ▼          ▼         ▼          ▼
  NORMAL   AUTO_POST  DRY_RUN    COLLECT
   (手動)   (自動)    (シミュレ) (収集)
    │          │         │          │
    │          ▼         │          │
    │     ┌─────────────┐│          │
    │     │ 自動投稿    ││          │
    │     │スレッド開始 ││          │
    │     └──────┬──────┘│          │
    │            │       │          │
    │            ▼       │          │
    │     ┌─────────────┐│          │
    │     │ 定期実行:  ││          │
    │     │・RSS取得  ││          │
    │     │・新着判定││          │
    │     │・自動投稿││          │
    │     └──────┬──────┘│          │
    │            │       │          │
    └────────────┴───────┴──────────┘
             │
             ▼
    ┌──────────────────┐
    │ GUI 表示         │
    │ (gui_v3.py)      │
    └────────┬─────────┘
             │
    ┌────────┴────────┐
    │                 │
    ▼                 ▼
  手動投稿      自動投稿処理
  (ユーザー)    (スレッド)
    │                 │
    └────────┬────────┘
             │
             ▼
    ┌──────────────────┐
    │ プラグイン実行  │
    │                 │
    │ ・YouTube       │
    │ ・YouTubeLive   │
    │ ・Niconico      │
    └────────┬────────┘
             │
             ▼
    ┌──────────────────┐
    │ Bluesky 投稿    │
    │ (bluesky_plugin) │
    └──────────────────┘
```

### YouTubeLive イベント投稿フロー

```
YouTubeAPI / RSS
      │
      ▼
┌───────────────────────┐
│ 新着動画検出        │
│ (youtube_api_plugin)  │
└───────┬───────────────┘
        │
        ▼
┌───────────────────────┐
│ コンテンツ判定        │
│ - video               │
│ - live (upcoming)     │
│ - live (live)         │
│ - archive             │
└───────┬───────────────┘
        │
        ├─────────────────────────────────────┐
        │                                     │
        ▼                                     ▼
  ┌──────────────────┐            ┌──────────────────┐
  │ 新規動画         │            │ ライブ予定       │
  │ (content_type=   │            │ (live_status=    │
  │  "video")        │            │  "upcoming")     │
  │                  │            │                  │
  │ → 新着テンプレ   │            │ → キャッシュ登録 │
  │   で投稿         │            │   → ポーリング開始
  └──────────────────┘            └────────┬─────────┘
                                           │
                                  ┌────────▼──────────┐
                                  │ ライブ開始検知    │
                                  │ (API ポーリング)  │
                                  │ (live_status=    │
                                  │  "live")         │
                                  └────────┬──────────┘
                                           │
                                           ▼
                                  ┌──────────────────┐
                                  │ ライブ開始投稿    │
                                  │ (yt_online_     │
                                  │  template.txt)  │
                                  │ 自動投稿実行    │
                                  └────────┬─────────┘
                                           │
                                  ┌────────▼──────────┐
                                  │ ライブ継続監視    │
                                  │ 終了検知待ち      │
                                  │ (API ポーリング)  │
                                  │ (live_status=    │
                                  │  "completed")    │
                                  └────────┬──────────┘
                                           │
                                           ▼
                                  ┌──────────────────┐
                                  │ ライブ終了投稿    │
                                  │ (yt_offline_    │
                                  │  template.txt)  │
                                  │ 自動投稿実行    │
                                  └────────┬─────────┘
                                           │
                                           ▼
                                  ┌──────────────────┐
                                  │ アーカイブ判定    │
                                  │ (content_type=   │
                                  │  "archive")      │
                                  │                  │
                                  │ → アーカイブテン │
                                  │   プレで投稿    │
                                  │   (オプション)   │
                                  └──────────────────┘
```

### Niconico 自動投稿フロー

```
Niconico RSS フィード
      │
      ▼
┌─────────────────────────┐
│ RSS 定期取得             │
│ (start_monitoring())    │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│ 最新動画を取得          │
│ (get_latest_video_     │
│  entry())              │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│ 新着判定                │
│ (last_video_id と比較)  │
└────────┬────────────────┘
         │
    ┌────┴────┐
    │ Yes     │ No
    │         │
    ▼         └────────────────────┐
┌─────────────────────────┐        │
│ 動画情報を抽出          │        │
│ (_entry_to_video_      │        │
│  dict())               │        │
└────────┬────────────────┘        │
         │                         │
         ▼                         │
┌─────────────────────────┐        │
│ DB に保存               │        │
│ (post_video())         │        │
└────────┬────────────────┘        │
         │                         │
         ▼                         │
┌─────────────────────────┐        │
│ 新着 ID をキャッシュ    │        │
└────────┬────────────────┘        │
         │                         │
         └────────┬────────────────┘
                  │
                  ▼
         ┌──────────────────┐
         │ ポーリング間隔   │
         │ (sleep)         │
         └────────┬─────────┘
                  │
                  └──► [ループ] 継続
```

---

## 8. データベース実装詳細

### 8.1 Videos テーブル定義

ファイル: `database.py` - `_init_db()` メソッド

```sql
CREATE TABLE IF NOT EXISTS videos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    video_url TEXT NOT NULL,
    published_at TEXT NOT NULL,
    channel_name TEXT,

    -- 投稿状態管理フィールド
    posted_to_bluesky INTEGER DEFAULT 0,      -- ★ Bluesky投稿済みフラグ（0/1）
    selected_for_post INTEGER DEFAULT 0,      -- GUI で選択状態
    scheduled_at TEXT,                        -- 予約投稿日時（NULL = 即座）
    posted_at TEXT,                           -- 実際の投稿日時

    -- メディア
    thumbnail_url TEXT,

    -- コンテンツ分類（YouTubeLive対応）
    content_type TEXT DEFAULT 'video',        -- "video", "live", "archive", "none"
    live_status TEXT,                         -- NULL, "none", "upcoming", "live", "completed"
    is_premiere INTEGER DEFAULT 0,            -- 0 or 1

    -- 画像管理
    image_mode TEXT,                          -- "import", "autopost"
    image_filename TEXT,

    -- ソース・タイムスタンプ
    source TEXT DEFAULT 'youtube',            -- "youtube", "niconico"
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

**重要なフィールド解説**:

| フィールド | 型 | デフォルト | 説明 |
|:--|:--|:--|:--|
| `posted_to_bluesky` | INTEGER | 0 | 投稿済みフラグ。0=未投稿、1=投稿済み |
| `selected_for_post` | INTEGER | 0 | 投稿選択フラグ。GUI チェックボックス連動 |
| `scheduled_at` | TEXT | NULL | 予約投稿日時。NULL = 即座投稿、日時指定 = スケジュール投稿 |
| `posted_at` | TEXT | NULL | 実際の投稿日時（ISO形式） |
| `source` | TEXT | 'youtube' | 投稿元プラットフォーム |

### 8.2 insert_video() 実装

ファイル: `database.py`

```python
def insert_video(self, video_id, title, video_url, published_at, channel_name="",
                 thumbnail_url="", content_type="video", live_status=None,
                 is_premiere=False, source="youtube"):
    """
    動画情報を挿入（リトライ付き、YouTube重複排除対応）

    戻り値:
        bool: 新規登録成功時 True、既存または低優先度の場合 False
    """
    # バリデーション
    content_type = self._validate_content_type(content_type)
    live_status = self._validate_live_status(live_status, content_type)

    # YouTube動画の重複チェック（優先度ロジック適用）
    if source == "youtube" and title and channel_name:
        # 既存レコード取得
        existing_videos = cursor.execute("""
            SELECT * FROM videos
            WHERE source='youtube' AND title=? AND channel_name=?
        """, (title, channel_name)).fetchall()

        if existing_videos:
            # 優先度比較：新動画 > アーカイブ > 通常動画
            # 低優先度なら False を返す → insert しない
            # 高優先度なら既存を削除して新規 insert

    # リトライループ（DB ロック対策、最大 3 回）
    for attempt in range(DB_RETRY_MAX):
        try:
            cursor.execute("""
                INSERT INTO videos (video_id, title, video_url, published_at,
                                   channel_name, thumbnail_url, content_type,
                                   live_status, is_premiere, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (video_id, title, video_url, published_at, channel_name,
                  thumbnail_url, content_type, live_status,
                  1 if is_premiere else 0, source))

            conn.commit()
            return True  # 新規登録成功

        except sqlite3.IntegrityError:
            # video_id が既に存在 → 既存レコード、投稿済みフラグは変更しない
            return False
```

**戻り値の意味**:
- **True**: 新規登録成功
- **False**: 既存レコード（投稿状態は変更しない）

**重要**: `insert_video()` は `posted_to_bluesky` を書き換えません。既存レコードの投稿状態は保持されます。

### 8.3 自動投稿対象の取得：get_selected_videos()

ファイル: `database.py`

```python
def get_selected_videos(self):
    """投稿選択された未投稿動画を取得（スケジュール順）"""
    try:
        conn = self._get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM videos
            WHERE selected_for_post = 1          -- ★ GUI で選択状態
              AND posted_to_bluesky = 0          -- ★ 未投稿のみ
              AND (scheduled_at IS NULL OR scheduled_at <= datetime('now'))  -- ★ 予約日時確認
            ORDER BY scheduled_at, published_at  -- ★ 予約順 → 新着順
            LIMIT 1                              -- ★ 1件ずつ取得
        """)

        result = cursor.fetchone()
        conn.close()
        return dict(result) if result else None  -- 1件 or None

    except Exception as e:
        logger.error(f"選択動画の取得に失敗しました: {e}")
        return None
```

**SELECT ロジック解析**:

| 条件 | 値 | 説明 |
|:--|:--|:--|
| `selected_for_post = 1` | WHERE 句 | GUI でチェックされた動画のみ |
| `posted_to_bluesky = 0` | WHERE 句 | **未投稿のみ** |
| `scheduled_at IS NULL OR scheduled_at <= datetime('now')` | WHERE 句 | 予約日時確認。NULL=即座、過去日時=投稿可能 |
| ORDER BY | `scheduled_at, published_at` | 予約順 → 新着順 |
| LIMIT 1 | 1件 | **1 件ずつ取得**（自動投稿は 1 件ずつ処理） |

**戻り値**: 1 件の dict または None

### 8.4 未投稿動画の一括取得：get_unposted_videos()

ファイル: `database.py`

```python
def get_unposted_videos(self):
    """未投稿の動画を取得"""
    try:
        conn = self._get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM videos
            WHERE posted_to_bluesky = 0        -- ★ 未投稿のみ
            ORDER BY published_at DESC         -- ★ 新着順
        """)

        videos = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return videos

    except Exception as e:
        logger.error(f"未投稿動画の取得に失敗しました: {e}")
        return []
```

**用途**: GUI で「未投稿一覧」を表示する際に使用

### 8.5 投稿済みフラグの更新：mark_as_posted()

ファイル: `database.py`

```python
def mark_as_posted(self, video_id):
    """動画を投稿済みにマーク"""
    try:
        conn = self._get_connection()
        cursor = conn.cursor()

        posted_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute("""
            UPDATE videos
            SET posted_to_bluesky = 1,          -- ★ フラグを 1 に更新
                posted_at = ?                   -- ★ 投稿日時を記録
            WHERE video_id = ?
        """, (posted_at, video_id))

        conn.commit()
        conn.close()

        post_logger.info(f"投稿済みフラグを更新しました: {video_id} (投稿日時: {posted_at})")
        return True

    except Exception as e:
        logger.error(f"投稿済みフラグの更新に失敗しました: {e}")
        return False
```

**重要**: この UPDATE で初めて `posted_to_bluesky` が 1 に設定されます。

### 8.6 重複投稿チェック：is_duplicate_post()

ファイル: `database.py`

```python
def is_duplicate_post(self, video_id: str) -> bool:
    """
    重複投稿かどうかをチェック

    Returns:
        bool: 重複投稿の場合 True、初回投稿の場合 False
    """
    try:
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT COUNT(*) FROM videos
            WHERE video_id = ? AND posted_to_bluesky = 1  -- ★ 投稿済みを検索
        """, (video_id,))

        count = cursor.fetchone()[0]
        conn.close()

        is_duplicate = count > 0
        if is_duplicate:
            logger.warning(f"⚠️ 重複投稿検知: この動画は既に投稿済みです（{video_id}）")

        return is_duplicate

    except Exception as e:
        logger.error(f"重複チェック中にエラーが発生: {e}")
        return False
```

**用途**: プラグイン側で投稿前に呼び出し、既投稿ならスキップ。

---

## 9. 自動投稿実行フロー（コード追跡）

### 9.1 main_v3.py でのフロー

ファイル: `main_v3.py` - `run_gui()` スレッド内

```python
# === 自動投稿スレッド（定期実行） ===
def run_gui(db, plugin_manager, stop_event, bluesky_core=None):
    """GUI スレッド（RSS ポーリング + 自動投稿ループ）"""

    config = get_config("settings.env")
    last_post_time = None                    # ★ 前回投稿時刻
    POST_INTERVAL_MINUTES = 5                # ★ 自動投稿間隔（5分）

    while not stop_event.is_set():
        try:
            # === RSS 取得フェーズ ===
            logger.info("[YouTube] YouTubeRSS から情報を取得しています...")
            thumb_mgr = get_youtube_thumb_manager()
            saved_count = thumb_mgr.fetch_and_ensure_images(config.youtube_channel_id)

            # === 自動投稿フェーズ ===
            if config.is_collect_mode:
                logger.info("[モード] 収集モード のため、投稿処理をスキップします。")
            else:
                now = datetime.now()

                # ★ 投稿間隔チェック（前回投稿から 5 分以上経過？）
                should_post = last_post_time is None or \
                              (now - last_post_time).total_seconds() >= POST_INTERVAL_MINUTES * 60

                if should_post:
                    # ★ 1. 投稿対象を DB から取得
                    selected_video = db.get_selected_videos()

                    if selected_video:
                        logger.info(f" 投稿対象を発見: {selected_video['title']}")

                        # ★ 2. すべての有効プラグインで投稿実行
                        results = plugin_manager.post_video_with_all_enabled(selected_video)

                        # ★ 3. 投稿成功を確認
                        success = any(results.values())

                        if success:
                            # ★ 4. DB の投稿済みフラグを更新
                            db.mark_as_posted(selected_video['video_id'])
                            last_post_time = now
                            logger.info(f" ✅ 投稿完了。次の投稿は {POST_INTERVAL_MINUTES} 分後です。")
                        else:
                            logger.warning(f" ❌ 投稿に失敗: {selected_video['title']}")
                    else:
                        logger.info("投稿対象となる動画が指定されていません。管理画面から設定してください。")
                else:
                    elapsed = (now - last_post_time).total_seconds() / 60
                    remaining = POST_INTERVAL_MINUTES - elapsed
                    logger.info(f" 投稿間隔制限中。次の投稿まで約 {remaining:.1f} 分待機。")

            # === 待機フェーズ ===
            logger.info(f"次のポーリングまで {config.poll_interval_minutes} 分待機中...")
            for _ in range(config.poll_interval_minutes * 60):
                if stop_event.is_set():
                    raise KeyboardInterrupt()
                time.sleep(1)

        except KeyboardInterrupt:
            break
```

**フロー解析**:

1. **RSS 取得**: YouTubeRSS から新着動画を取得 → DB に保存
2. **投稿間隔チェック**: 前回投稿から 5 分以上経過？
3. **DB から取得**: `db.get_selected_videos()` で 1 件取得
4. **プラグイン実行**: `plugin_manager.post_video_with_all_enabled()`
5. **投稿済みフラグ更新**: `db.mark_as_posted(video_id)`
6. **待機**: 次のポーリングまで待機

### 9.2 GUI での投稿実行

ファイル: `gui_v3.py` - 手動投稿・DRY RUN

```python
# === 手動投稿 / DRY RUN ===
def on_post_selected(self, dry_run=False):
    """GUI の [投稿] / [DRY RUN] ボタンクリック時"""

    video = self.get_selected_video_from_table()  # 選択行を取得
    if not video:
        messagebox.showwarning("警告", "動画を選択してください")
        return

    # 重複投稿チェック
    if self.db.is_duplicate_post(video["video_id"]):
        messagebox.showwarning("警告", "この動画は既に投稿済みです")
        return

    # 投稿実行
    video_with_settings = dict(video)
    # 画像設定などを追加...

    results = self.plugin_manager.post_video_with_all_enabled(
        video_with_settings,
        dry_run=dry_run
    )

    success = any(results.values())

    if success and not dry_run:
        # ★ 投稿成功時のみ DB 更新
        self.db.mark_as_posted(video["video_id"])
        messagebox.showinfo("成功", "投稿が完了しました")
    elif dry_run:
        messagebox.showinfo("DRY RUN", "投稿をシミュレートしました（実投稿なし）")
    else:
        messagebox.showerror("エラー", "投稿に失敗しました")
```

---

## 10. プラグイン側での再投稿制御

### 10.1 YouTube プラグイン（新着動画）

ファイル: `youtube_api_plugin.py` / RSS フロー

```python
# post_video() は新着検出で呼ばれる
# DB への insert 時点で重複チェックが行われている
# （既存レコード → insert_video() が False を返す → post_video() 呼ばれない）
```

**制御メカニズム**: DB の `insert_video()` で既存チェック → 既投稿なら登録しない

### 10.2 YouTubeLive プラグイン

ファイル: `youtube_live_plugin.py`

```python
def auto_post_live_start(self, video: Dict[str, Any]) -> bool:
    """ライブ開始時の自動投稿"""

    # 既に投稿済みなら実行しない
    if self.db.is_duplicate_post(video.get("video_id")):
        logger.warning(f"⚠️ ライブ開始投稿: {video.get('title')} は既に投稿済み")
        return False

    bluesky_plugin = pm.get_plugin("bluesky_plugin")
    video_copy = dict(video)
    video_copy["event_type"] = "live_start"

    return bluesky_plugin.post_video(video_copy)
```

**制御**: 明示的に `is_duplicate_post()` で再投稿をチェック

### 10.3 Niconico プラグイン

ファイル: `niconico_plugin.py`

```python
def post_video(self, video: Dict[str, Any]) -> bool:
    """動画をDB に保存（Niconico 監視フロー）"""

    is_new = self.db.insert_video(
        video_id=video_id,
        title=title,
        source="niconico"
    )

    # is_new = False なら既存レコード → return False（投稿しない）
    if is_new:
        logger.info(f"✅ 新着動画を保存しました: {title}")

    return is_new
```

**制御**: `insert_video()` の戻り値で判定。False なら投稿しない。

---

## 関連ドキュメント

- [plugin_interface.py](../../../v3/plugin_interface.py) - プラグインインターフェース定義
- [plugin_manager.py](../../../v3/plugin_manager.py) - プラグイン管理
- [config.py](../../../v3/config.py) - 設定管理
- [youtube_live_plugin.py](../../../v3/plugins/youtube_live_plugin.py) - YouTubeLive プラグイン
- [niconico_plugin.py](../../../v3/plugins/niconico_plugin.py) - Niconico プラグイン
- [bluesky_plugin.py](../../../v3/plugins/bluesky_plugin.py) - Bluesky 拡張機能プラグイン
- [database.py](../../../v3/database.py) - DB 管理
- [image_manager.py](../../../v3/image_manager.py) - 画像管理
- [PLUGIN_SYSTEM.md](./PLUGIN_SYSTEM.md) - プラグインシステム詳細
- [TEMPLATE_SYSTEM.md](./TEMPLATE_SYSTEM.md) - テンプレートシステム詳細

---

**作成日**: 2025年12月20日
**最後の修正**: 2025年12月20日
**ステータス**: ✅ 完成・検証済み
