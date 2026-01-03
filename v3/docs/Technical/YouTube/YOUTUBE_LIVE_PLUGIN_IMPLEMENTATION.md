# YouTubeLive プラグイン完成実装ガイド

**対象バージョン**: v3.3.0+（v2.3.0 以降の統合改善）
**最終更新**: 2026-01-03
**ステータス**: ✅ v3.3.0 で統合・最適化完了

---

## 📖 目次

1. [概要](#概要)
2. [v2完了の定義](#v2完了の定義)
3. [現状分析](#現状分析)
4. [実装要件](#実装要件)
5. [実装計画](#実装計画)
6. [技術仕様](#技術仕様)
7. [テスト計画](#テスト計画)
8. [リリース計画](#リリース計画)

---

## 概要

YouTubeLive プラグインの実装は **v2.3.0 で完成** し、v3.3.0 でさらに最適化・統合されました。\
本ドキュメントは、その最終的な実装状況と v3.3.0+ での改善内容を記録します。

### 実装完了の機能

1. ✅ ライブ開始/終了の自動検知ロジック
2. ✅ ライブイベント用テンプレート自動適用
3. ✅ `live_status` の自動更新機能
4. ✅ v3.3.0: プラグインアーキテクチャ統合・動的ポーリング間隔制御

**完成**: v2.3.0（2025-12-18）
**統合改善**: v3.3.0（2026-01-03）

---

## v2.3.0 完了・v3.3.0 統合

YouTubeLive プラグインの完成をもって **v2 完了** とし、v3.3.0 で統合改善が実施されました。

### v2.3.0 で実装された機能

以下の機能がすべて実装され、テスト済みであること：

- [✅] ライブ開始の自動検知
  - RSS または API ポーリングでライブ開始を検知
  - DB の `live_status` を `live` に更新
  - `yt_online_template.txt` で Bluesky に自動投稿

- [✅] ライブ終了の自動検知
  - API ポーリングでライブ終了を検知
  - DB の `live_status` を `completed` に更新
  - `yt_offline_template.txt` で Bluesky に自動投稿

- [✅] アーカイブ化の検知
  - ライブ終了後のアーカイブ変換を検知
  - DB の `content_type` を `archive` に更新

- [✅] テンプレート自動適用
  - イベント種別に応じて適切なテンプレートを自動選択
  - `yt_online_template.txt`: ライブ開始時
  - `yt_offline_template.txt`: ライブ終了時
  - `yt_new_video_template.txt`: 通常動画・アーカイブ

### v3.3.0 で追加された改善

- [✅] **プラグイン構成の統合**: `youtube_live_plugin.py` → `plugins/youtube/live_module.py` へリファクタリング
- [✅] **動的ポーリング間隔制御**: キャッシュ状態に応じた最適なポーリング間隔の自動調整
- [✅] **テンプレートパス統合**: `templates/youtube/` 配下で一元管理
- [✅] **ステータス分類の統合**: `content_type` + `live_status` による多段階分類の最適化
- [✅] **テンプレート動的変数（配信時間情報など）**: 拡張時間表示や変数の追加
- [✅] **テンプレートの追加・更新**: YouTubeLive 放送枠予約通知（upcoming イベント対応）

**注記**: テンプレート動的変数（配信時間情報など）は v3.2.0+ で既に実装済みです。
詳細は [TEMPLATE_SYSTEM.md](../TEMPLATE_SYSTEM.md) を参照してください。

その他の GUI 機能拡張やバックアップ機能については、プロジェクト全体のロードマップを参照してください。

**参考**: [将来ロードマップ](../../References/FUTURE_ROADMAP_v3.md)

---

## 現状分析（v3.3.0 実装完了版）

### 実装済み機能

v3.3.0 では以下の構造に統合・最適化されました：

#### 1. YouTubeVideoClassifier（youtube_core/ 配下）

```python
# youtube_core/youtube_video_classifier.py

class YouTubeVideoClassifier:
    """
    YouTube Data API を使った動画種別分類

    ✅ 完成機能:
    - 動画種別の自動分類: schedule / live / completed / archive / video / premiere
    - representative_time の自動計算（基準時刻）
    - キャッシュによるAPI効率化
    """

    def classify_video(self, video_id: str) -> Dict[str, Any]:
        """
        動画を分類し、以下を返す：
        {
            "success": bool,
            "video_id": str,
            "type": str,  # "schedule", "live", "completed", "archive", "video", "premiere"
            "title": str,
            "thumbnail_url": str,
            "published_at": str,
            "live_status": str,  # "upcoming" / "live" / "completed" / None
            "representative_time_utc": str,  # ★ 基準時刻（UTC）
            "representative_time_jst": str,  # ★ 基準時刻（JST）
        }
        """
```

#### 2. YouTubeAPIPlugin（plugins/youtube/youtube_api_plugin.py）

```python
# plugins/youtube/youtube_api_plugin.py

class YouTubeAPIPlugin(NotificationPlugin):
    """
    YouTube Data API 連携プラグイン（クォータ対応版）

    ✅ 完成機能:
    - UC以外のチャンネル識別子（ハンドル）をAPIで解決
    - 動画詳細取得とキャッシング
    - APIコスト管理（429対応・レート制限）
    - ローカルキャッシュと API 効率化
    """

    def post_video(self, video: Dict[str, Any]) -> bool:
        """
        動画情報を処理し DB に保存
        ✅ 実装済み: 詳細取得→分類→DB保存
        """
```

#### 3. LiveModule（plugins/youtube/live_module.py）

```python
# plugins/youtube/live_module.py

class LiveModule:
    """
    YouTube Live 管理モジュール

    ✅ 完成機能:
    - YouTubeVideoClassifier の分類結果を受け取り DB 登録
    - 状態遷移を検知し Bluesky 自動投稿
    - イベント種別ごとのテンプレート自動選択
    - 動的ポーリング間隔制御
    """

    def register_from_classified(self, result: Dict[str, Any]) -> int:
        """分類結果を DB に登録（1 件分）"""

    def poll_and_update_live_status(self) -> int:
        """
        DB の live_status='live' 動画をポーリングし状態遷移を検知
        ✅ 実装済み: 定期ポーリング＋自動投稿
        """

    def handle_state_transition(self, video_id: str, old_type: str, new_type: str) -> int:
        """
        状態遷移（schedule→live→completed）を処理
        ✅ 実装済み: テンプレート選択＋投稿実行
        """
```

### 実装状況一覧

| 機能 | ステータス | 実装箇所 | 備考 |
|:--|:--:|:--|:--|
| **分類アルゴリズム** | ✅ 実装 | YouTubeVideoClassifier | スケジュール/ライブ/終了/アーカイブ等を判定 |
| **API 詳細取得** | ✅ 実装 | YouTubeAPIPlugin | キャッシング機能付き |
| **ライブ開始検知** | ✅ 実装 | LiveModule | RSS + API で検知 |
| **ライブ終了検知** | ✅ 実装 | LiveModule.poll_and_update_live_status() | 定期ポーリング実装済み |
| **状態遷移検知** | ✅ 実装 | LiveModule.handle_state_transition() | 完全実装 |
| **テンプレート選択** | ✅ 実装 | bluesky_plugin.py | イベント種別で自動選択 |
| **自動投稿** | ✅ 実装 | bluesky_plugin.py | PluginManager 経由で投稿実行 |
| **DB 保存** | ✅ 実装 | database.py | content_type / live_status の更新 |
| **定期ポーリング** | ✅ 実装 | main_v3.py | スレッド + タイマーで実行 |
| **動的ポーリング間隔** | ✅ 実装 | config.py | キャッシュ状態で自動調整 |
| **テンプレートファイル** | ✅ 配置 | Asset/templates/youtube/ | online / offline テンプレート配置済み |
| **DB クエリメソッド** | ✅ 実装 | database.py | get_videos_by_live_status() 等 |
| **環境変数** | ✅ 実装 | settings.env.example | YOUTUBE_LIVE_* 関連を完全整備 |

---

## 実装要件（完成版）

### 1. ライブ開始の自動検知 ✅ 完成

#### 実装内容

**RSS + API 併用方式（採用済み）**
- RSS で新着動画を検知
- YouTubeVideoClassifier で分類（schedule/live/completed等）
- LiveModule で状態遷移を検知
- schedule → live への遷移時に自動投稿実行

#### 実装モジュール

```python
# youtube_core/youtube_video_classifier.py
# → schedule / live / completed を判定

# plugins/youtube/live_module.py
# → register_from_classified(result) で DB 登録
# → handle_state_transition() で状態遷移を検知→投稿

# bluesky_plugin.py
# → イベント種別でテンプレートを自動選択
```

#### ポーリング費用

- RSS: コスト 0
- API 詳細取得: 1 ユニット/動画
- 定期チェック: 1 ユニット/ポーリング

**月間推定**: 日3本 × 30日 × 1 ユニット = 90 ユニット（日額: 3 ユニット程度）

### 2. ライブ終了の自動検知 ✅ 完成

#### 実装内容

**定期ポーリング方式（実装済み）**
- DB の live_status='live' 動画を定期的に確認
- YouTubeVideoClassifier でライブ状態を再判定
- completed / archive への遷移を検知
- 自動投稿実行

#### 実装モジュール

```python
# plugins/youtube/live_module.py
def poll_and_update_live_status(self) -> int:
    """
    DB の live_status='live' 動画をポーリング

    戻り値: 更新件数
    実装: YOUTUBE_LIVE_POLL_INTERVAL_ACTIVE 等で間隔を動的制御
    """
```

#### ポーリング間隔（動的制御）

| 状況 | ポーリング間隔 | 設定値 | デフォルト |
|:--|:--|:--|:--|
| ライブ配信中（キャッシュに live が存在） | **短い** | `YOUTUBE_LIVE_POLL_INTERVAL_ACTIVE` | 5分 |
| ライブ終了直後（キャッシュに completed が存在） | **中程度** | `YOUTUBE_LIVE_POLL_INTERVAL_COMPLETED` | 15分 |
| ライブなし（キャッシュに LIVE が無い） | **長い** | `YOUTUBE_LIVE_POLL_INTERVAL_NO_LIVE` | 30分 |

**月間推定**: 最悪ケース 4本同時 LIVE × 1h = 4 ユニット × 30日 = 120 ユニット（日額: 4 ユニット程度）

### 3. テンプレート自動適用 ✅ 完成

#### イベント種別ごとのテンプレート選択

| イベント | テンプレート | 判定条件 | 実装 |
|:--|:--|:--|:--|
| **ライブ予約** | `yt_schedule_template.txt` | type="schedule" | ✅ 実装 |
| **ライブ開始** | `yt_online_template.txt` | schedule → live | ✅ 実装 |
| **ライブ終了** | `yt_offline_template.txt` | live → completed | ✅ 実装 |
| **アーカイブ** | `yt_archive_template.txt` | type="archive" | ✅ 実装 |
| **通常動画** | `yt_new_video_template.txt` | type="video" | ✅ 実装 |

#### テンプレート選択ロジック（実装済み）

```python
# bluesky_plugin.py

def post_video(self, video: Dict[str, Any]) -> bool:
    """
    動画情報に基づいて適切なテンプレートを選択

    選択基準（優先度順）:
    1. content_type / live_status から判定
    2. representative_time で基準時刻を自動計算
    3. 該当テンプレートファイルを読み込み
    4. Jinja2 でレンダリング
    5. Bluesky へ投稿
    """
    event_type = self._determine_event_type(video)
    template_path = self._get_template_path(event_type)
    rendered = template_utils.render_template_with_utils(template_path, video)
    # ... 投稿実行
```

---

## 実装計画（v3.3.0 完成記録）

### Phase 1: ライブ開始検知 ✅ 完成

#### 1.1 RSS 監視強化 ✅ 実装完了

```python
# youtube_core/youtube_rss.py

def fetch_and_classify_videos(channel_id: str, classifier=None) -> List[Dict]:
    """
    RSS 取得 + ライブ状態分類

    ✅ 実装済み:
    - RSS フィード取得
    - YouTubeVideoClassifier で分類
    - schedule/live/completed 等を判定
    - representative_time を計算
    """
    videos = fetch_youtube_rss(channel_id)

    if classifier:
        for video in videos:
            result = classifier.classify_video(video["video_id"])
            if result.get("success"):
                # 分類結果を video に統合
                video.update(result)

    return videos
```

#### 1.2 自動投稿ロジック ✅ 実装完了

```python
# plugins/youtube/live_module.py

def register_from_classified(self, result: Dict[str, Any]) -> int:
    """
    YouTubeVideoClassifier の分類結果を DB に登録

    ✅ 実装済み:
    - result から動画情報を抽出
    - schedule/live/completed 等に分類
    - DB に insert → update
    - 状態遷移をログ出力
    """

def handle_state_transition(self, video_id: str, old_type: str, new_type: str) -> int:
    """
    状態遷移時に自動投稿

    ✅ 実装済み:
    - old_type → new_type への遷移を検知
    - イベント種別からテンプレートを決定
    - PluginManager.post_video() で投稿実行
    """
    if old_type == "schedule" and new_type == "live":
        # ライブ開始イベント
        return self._post_live_start_event(video_id)
    elif old_type == "live" and new_type in ["completed", "archive"]:
        # ライブ終了イベント
        return self._post_live_end_event(video_id)
    # ...
```

### Phase 2: ライブ終了検知 ✅ 完成

#### 2.1 定期ポーリング機能 ✅ 実装完了

```python
# plugins/youtube/live_module.py

def poll_and_update_live_status(self) -> int:
    """
    ライブ中の動画を定期チェックし、終了を検知

    ✅ 実装済み:
    - DB から live_status='live' の動画を取得
    - YouTubeVideoClassifier で再分類
    - completed/archive への遷移を検知
    - 自動投稿実行

    戻り値: 更新した件数
    """
    live_videos = self.db.get_videos_by_live_status("live")
    update_count = 0

    for video in live_videos:
        video_id = video["video_id"]
        result = self.classifier.classify_video(video_id)

        if result.get("success"):
            new_type = result.get("type")
            if new_type in ["completed", "archive"]:
                # 状態遷移を処理
                self.handle_state_transition(video_id, "live", new_type)
                update_count += 1

    return update_count
```

#### 2.2 スケジューリング ✅ 実装完了

```python
# main_v3.py

def start_youtube_live_polling(plugin_manager, config):
    """
    ライブポーリングを定期実行

    ✅ 実装済み:
    - LiveModule インスタンス取得
    - 動的ポーリング間隔で定期実行
    - 状態遷移を検知→投稿
    - エラー時にリトライ
    """
    import threading
    import time

    def polling_loop():
        while True:
            try:
                live_module = plugin_manager.get_plugin("live_module")
                if live_module:
                    # ポーリング間隔を動的取得
                    interval = get_dynamic_poll_interval(live_module, config)
                    live_module.poll_and_update_live_status()

                    time.sleep(interval * 60)
            except Exception as e:
                logger.error(f"❌ ライブポーリングエラー: {e}")
                time.sleep(60)

    thread = threading.Thread(target=polling_loop, daemon=True)
    thread.start()
    logger.info("✅ ライブポーリングスレッドを開始しました")
```

### Phase 3: テンプレート統合 ✅ 完成

#### 3.1 Asset ディレクトリのテンプレート ✅ 配置完了

```
Asset/templates/youtube/
  ├── yt_new_video_template.txt    # ✅ 配置済み
  ├── yt_online_template.txt        # ✅ 配置済み
  ├── yt_offline_template.txt       # ✅ 配置済み
  └── yt_schedule_template.txt      # ✅ 配置済み（v3.2.0+）

templates/youtube/  ← 実行時ディレクトリ（自動配置）
  ├── yt_new_video_template.txt    # ✅ 配置済み
  ├── yt_online_template.txt        # ✅ 配置済み
  ├── yt_offline_template.txt       # ✅ 配置済み
  └── yt_schedule_template.txt      # ✅ 配置済み
```

#### 3.2 テンプレート選択ロジック ✅ 実装完了

```python
# bluesky_plugin.py

def _determine_event_type(self, video: Dict[str, Any]) -> str:
    """
    動画情報からイベント種別を判定

    ✅ 実装済み:
    - content_type / live_status から判定
    - representative_time で基準時刻を確定
    """
    content_type = video.get("content_type", "video")
    live_status = video.get("live_status")

    if content_type == "schedule" and live_status == "upcoming":
        return "live_schedule"
    elif content_type == "live" and live_status == "live":
        return "live_start"
    elif content_type == "completed" and live_status == "completed":
        return "live_end"
    elif content_type == "archive":
        return "archive"
    else:
        return "new_video"

def _get_template_path(self, event_type: str) -> str:
    """イベント種別からテンプレートパスを取得"""
    template_map = {
        "live_schedule": "templates/youtube/yt_schedule_template.txt",
        "live_start": "templates/youtube/yt_online_template.txt",
        "live_end": "templates/youtube/yt_offline_template.txt",
        "archive": "templates/youtube/yt_archive_template.txt",
        "new_video": "templates/youtube/yt_new_video_template.txt",
    }
    return template_map.get(event_type, "templates/youtube/yt_new_video_template.txt")
```

#### 3.3 テンプレートサンプル

**yt_schedule_template.txt**（v3.2.0+）:
```jinja2
📺 YouTube Live が予定されています

【 {{ title }} 】

配信予定時刻: {{ representative_time_jst }}

{{ video_url }}

#YouTube #Live配信
```

**yt_online_template.txt**:
```jinja2
🔴 配信開始！

【 {{ title }} 】

📺 {{ video_url }}

#YouTube #Live配信
```

**yt_offline_template.txt**:
```jinja2
配信終了しました 🎉

【 {{ title }} 】

アーカイブはこちら 👇
{{ video_url }}

#YouTube #配信アーカイブ
```

**yt_archive_template.txt**:
```jinja2
ライブアーカイブが公開されました

【 {{ title }} 】

ぜひご視聴ください 👇
{{ video_url }}

#YouTube #ライブアーカイブ
```

---

## 技術仕様（v3.3.0 実装版）

### 動画分類仕様（YouTubeVideoClassifier）

YouTube Data API の `liveStreamingDetails` を基に、以下の 6 種類に分類：

```
┌─ 通常動画 ──────────────────────────┐
│ - liveStreamingDetails: 無し        │
│ - type: "video" / "premiere"        │
└────────────────────────────────────┘

┌─ ライブ配信（4 段階） ───────────────┐
│ 1. Schedule（予約枠）               │
│    - scheduledStartTime: 有り        │
│    - actualStartTime: 無し           │
│    - type: "schedule"               │
│    - live_status: "upcoming"        │
│                                    │
│ 2. Live（配信中）                  │
│    - actualStartTime: 有り           │
│    - actualEndTime: 無し             │
│    - type: "live"                  │
│    - live_status: "live"           │
│                                    │
│ 3. Completed（配信終了直後）       │
│    - actualEndTime: 有り             │
│    - type: "completed"             │
│    - live_status: "completed"      │
│                                    │
│ 4. Archive（アーカイブ化）         │
│    - type: "archive"               │
│    - live_status: null             │
└────────────────────────────────────┘
```

### データベーススキーマ（v3.3.0 版）

```sql
-- videos テーブル（実装済み）
CREATE TABLE videos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    video_url TEXT NOT NULL,
    published_at TEXT NOT NULL,           -- RSS/API から取得
    channel_name TEXT,
    posted_to_bluesky INTEGER DEFAULT 0,
    selected_for_post INTEGER DEFAULT 0,
    scheduled_at TEXT,
    posted_at TEXT,
    thumbnail_url TEXT,

    -- ★ Live 対応カラム
    content_type TEXT DEFAULT 'video',       -- "video"/"premiere"/"schedule"/"live"/"completed"/"archive"
    live_status TEXT,                        -- null/"upcoming"/"live"/"completed"
    representative_time_utc TEXT,            -- ★ 基準時刻（UTC）
    representative_time_jst TEXT,            -- ★ 基準時刻（JST）

    is_premiere INTEGER DEFAULT 0,
    is_short INTEGER DEFAULT 0,
    is_members_only INTEGER DEFAULT 0,
    image_mode TEXT,
    image_filename TEXT,
    source TEXT DEFAULT 'youtube',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### DB クエリヘルパー（実装済み）

```python
# database.py

class Database:
    def get_videos_by_live_status(self, live_status: str) -> List[Dict]:
        """
        live_status で動画をフィルタリング

        Args:
            live_status: "upcoming" / "live" / "completed"

        Returns:
            該当する動画情報リスト
        """

    def get_videos_by_content_type(self, content_type: str) -> List[Dict]:
        """
        content_type で動画をフィルタリング

        Args:
            content_type: "video"/"schedule"/"live"/"completed"/"archive" 等

        Returns:
            該当する動画情報リスト
        """

    def update_video_status(self, video_id: str, content_type: str = None, live_status = None) -> bool:
        """
        content_type と live_status を更新

        Args:
            video_id: 動画ID
            content_type: コンテンツ種別
            live_status: ライブ配信状態

        Returns:
            更新成功フラグ
        """
```

### 環境変数設定（実装済み）

```bash
# settings.env の YouTube Live 関連設定

# =============================
# YouTube Live 自動投稿モード（AUTOPOST 用、v3.4.0+）
# =============================

# AUTOPOST 時の YouTube Live 投稿モード
# all: 予約枠・配信・アーカイブすべてを投稿
# schedule: 予約枠のみ投稿
# live: 予約枠と配信開始・配信終了のみ投稿
# archive: アーカイブ公開のみ投稿
# off: YouTube Live 自動投稿を行わない
#YOUTUBE_LIVE_AUTO_POST_MODE=off

# SELFPOST モード向け個別制御
#YOUTUBE_LIVE_AUTO_POST_SCHEDULE=true    # 予約枠を自動投稿
#YOUTUBE_LIVE_AUTO_POST_LIVE=true        # 配信開始・終了を自動投稿
#YOUTUBE_LIVE_AUTO_POST_ARCHIVE=true     # アーカイブを自動投稿

# =============================
# YouTube Live ポーリング間隔（動的制御、v3.4.0+）
# =============================

# LIVE 配信中のポーリング間隔（分、デフォルト: 5）
# upcoming/live 状態の動画がキャッシュにある場合に使用
YOUTUBE_LIVE_POLL_INTERVAL_ACTIVE=5

# LIVE 完了後のポーリング間隔（分、デフォルト: 15）
# completed 状態の動画がキャッシュにある場合に使用
YOUTUBE_LIVE_POLL_INTERVAL_COMPLETED=15

# LIVE なし時のポーリング間隔（分、デフォルト: 30）
# キャッシュに LIVE がない場合に使用（省リソース）
YOUTUBE_LIVE_POLL_INTERVAL_NO_LIVE=30
```

### YouTube Live イベント判定ロジック

```python
# plugins/youtube/live_module.py

class LiveModule:
    def determine_event_transition(self, old_result: Dict, new_result: Dict) -> Optional[str]:
        """
        状態遷移からイベント種別を判定

        遷移パターン:
        - schedule → live: "live_start"
        - live → completed: "live_end"
        - completed → archive: "live_archived"
        - schedule → upcoming: "schedule_confirmed"（予約確定）

        Returns: イベント種別 or None（遷移なし）
        """
        old_type = old_result.get("type")
        new_type = new_result.get("type")

        if old_type == "schedule" and new_type == "live":
            return "live_start"
        elif old_type == "live" and new_type == "completed":
            return "live_end"
        elif old_type == "completed" and new_type == "archive":
            return "live_archived"

        return None
```

---

## テスト計画（v3.3.0 実装済み検証版）

### 単体テスト ✅ 実装完了

```python
# tests/ 配下のテストスクリプト

def test_youtube_video_classifier():
    """YouTubeVideoClassifier の動画分類テスト"""
    # ✅ 検証項目:
    # - schedule（予約）と upcoming の判定
    # - live（配信中）と live_status の判定
    # - completed（終了）と completed の判定
    # - archive（アーカイブ）の判定
    # - representative_time の計算精度

def test_live_module_registration():
    """LiveModule の DB 登録テスト"""
    # ✅ 検証項目:
    # - YouTubeVideoClassifier 結果の DB 登録
    # - content_type / live_status の正確な保存
    # - 重複チェック

def test_live_module_state_transition():
    """LiveModule の状態遷移検知テスト"""
    # ✅ 検証項目:
    # - schedule → live への遷移検知
    # - live → completed への遷移検知
    # - completed → archive への遷移検知
    # - 遷移イベントの自動投稿実行

def test_template_selection():
    """テンプレート自動選択テスト"""
    # ✅ 検証項目:
    # - schedule: yt_schedule_template.txt
    # - live_start: yt_online_template.txt
    # - live_end: yt_offline_template.txt
    # - archive: yt_archive_template.txt
    # - new_video: yt_new_video_template.txt

def test_dynamic_poll_interval():
    """動的ポーリング間隔制御テスト"""
    # ✅ 検証項目:
    # - キャッシュに live がある場合: 5分
    # - キャッシュに completed がある場合: 15分
    # - ライブなし場合: 30分
    # - 間隔の動的切替
```

### 統合テスト ✅ 実装完了

```python
# tests/ 配下の統合テストスクリプト

def test_full_live_workflow():
    """ライブ配信の完全ワークフローテスト"""
    # ✅ 以下を順序立てて検証:
    # 1. RSS で新着動画を検知
    # 2. YouTubeVideoClassifier で schedule に分類
    # 3. LiveModule で DB に登録
    # 4. Bluesky に yt_schedule_template で投稿
    # 5. API ポーリングで live への遷移を検知
    # 6. Bluesky に yt_online_template で投稿
    # 7. API ポーリングで completed への遷移を検知
    # 8. Bluesky に yt_offline_template で投稿
    # 9. completed → archive への遷移を検知
    # 10. Bluesky に yt_archive_template で投稿
    # 11. 各イベントのログが正確に記録されているか確認

def test_api_quota_management():
    """API クォータ管理テスト"""
    # ✅ 検証項目:
    # - 月間 API 消費量の推定値
    # - キャッシュ効果による削減量
    # - 動的ポーリング間隔による削減量

def test_multi_concurrent_live():
    """複数ライブが同時に存在する場合のテスト"""
    # ✅ 検証項目:
    # - 複数の live_status='live' 動画を同時管理
    # - ポーリング時の DB ロック回避
    # - 各ライブの独立した状態遷移検知
```

### 実環境テスト（実施済み）

| テスト項目 | 実施日 | 結果 | 備考 |
|:--|:--|:--|:--|
| ライブ予約の検知 | 2025-12-18 | ✅ 成功 | schedule タイプを正確に分類 |
| ライブ開始の検知 | 2025-12-18 | ✅ 成功 | schedule → live への遷移を検知・投稿 |
| ライブ終了の検知 | 2025-12-18 | ✅ 成功 | live → completed への遷移を検知・投稿 |
| テンプレート選択 | 2025-12-18 | ✅ 成功 | イベント種別で適切なテンプレートを選択 |
| 複数ライブ同時管理 | 2025-12-18 | ✅ 成功 | 複数 live を独立管理可能 |
| API クォータ管理 | 2025-12-18 | ✅ 成功 | 日額 4～5 ユニット程度に抑制 |
| 定期ポーリング実行 | 2025-12-18 | ✅ 成功 | 5分間隔で正確に実行 |

---

## リリース・統合履歴

### v2.3.0 リリース（2025-12-18）

#### 新機能
- ✅ YouTubeLive プラグイン完成
  - ライブ開始/終了の自動検知
  - テンプレート自動適用
  - 定期ポーリング機能

#### バージョンアップ
- `app_version.py`: v2.1.0 → v2.3.0
- リリース日: 2025-12-18

#### ドキュメント更新
- [✅] FUTURE_ROADMAP_v2.md（Phase 2 完了マーク）
- [✅] README.md（YouTubeLive 対応を追記）
- [✅] README_GITHUB_v2.md（同上）
- [✅] PLUGIN_SYSTEM.md（YouTubeLive プラグイン仕様追加）

---

### v3.3.0 統合改善（2026-01-03）

#### 改善内容
- [✅] **プラグイン構成の最適化**
  - `youtube_live_plugin.py` の機能を `plugins/youtube/live_module.py` に統合
  - プラグインアーキテクチャの統一

- [✅] **動的ポーリング間隔制御**
  - キャッシュ状態に応じてポーリング間隔を自動調整
  - リソース消費を最適化しながら応答性を維持
  - 設定値: `YOUTUBE_LIVE_POLL_INTERVAL_ACTIVE`（デフォルト: 5分）
  - 設定値: `YOUTUBE_LIVE_POLL_INTERVAL_COMPLETED`（デフォルト: 15分）
  - 設定値: `YOUTUBE_LIVE_POLL_INTERVAL_NO_LIVE`（デフォルト: 30分）

- [✅] **テンプレートパス整理**
  - すべてのテンプレートを `templates/youtube/` で一元管理
  - v3 ドキュメント体系に統一

#### ドキュメント更新
- [✅] TEMPLATE_SYSTEM.md（テンプレート最適化を記録）
- [✅] ASSET_MANAGER_INTEGRATION_v3.md（アセット管理を更新）
- [✅] 本ドキュメント（統合状況を反映）

---

## チェックリスト（v3.3.0 完成検証）

### 実装済み機能

- [✅] **動画分類ロジック**（youtube_core/youtube_video_classifier.py）
  - schedule / live / completed / archive を判定
  - representative_time の自動計算
  - キャッシング機能

- [✅] **YouTube API プラグイン**（plugins/youtube/youtube_api_plugin.py）
  - UC以外のチャンネル識別子解決
  - 動画詳細取得
  - APIコスト管理（429対応）
  - ローカルキャッシング

- [✅] **LiveModule**（plugins/youtube/live_module.py）
  - 分類結果の DB 登録
  - 状態遷移検知
  - 自動投稿ロジック
  - 定期ポーリング機能
  - 動的ポーリング間隔制御

- [✅] **DB ヘルパーメソッド**（database.py）
  - `get_videos_by_live_status()`
  - `get_videos_by_content_type()`
  - `update_video_status()`

- [✅] **テンプレートシステム**（bluesky_plugin.py）
  - イベント種別の自動判定
  - テンプレートパスの自動選択
  - Jinja2 レンダリング

- [✅] **テンプレートファイル**（Asset/templates/youtube/）
  - yt_schedule_template.txt
  - yt_online_template.txt
  - yt_offline_template.txt
  - yt_archive_template.txt

### 環境変数・設定済み

- [✅] YOUTUBE_LIVE_POLL_INTERVAL_ACTIVE （デフォルト: 5分）
- [✅] YOUTUBE_LIVE_POLL_INTERVAL_COMPLETED （デフォルト: 15分）
- [✅] YOUTUBE_LIVE_POLL_INTERVAL_NO_LIVE （デフォルト: 30分）
- [✅] TEMPLATE_* パス関連の設定

### テスト・検証済み

- [✅] ユニットテスト（動画分類、DB操作、テンプレート選択）
- [✅] 統合テスト（全体ワークフロー）
- [✅] 実環境テスト（実際のライブ配信で検証）
  - schedule → live への遷移
  - live → completed への遷移
  - 複数 LIVE の同時管理
  - テンプレート選択精度
  - API クォータ管理

### ドキュメント更新済み

- [✅] v3 YOUTUBE_LIVE_PLUGIN_IMPLEMENTATION.md （本ファイル）
- [✅] TEMPLATE_SYSTEM.md
- [✅] ASSET_MANAGER_INTEGRATION_v3.md
- [✅] README.md （YouTubeLive 対応を記載）
- [✅] settings.env.example（動的ポーリング設定を追加）

---

**最終更新**: 2026-01-03
**ステータス**: ✅ v3.3.0 で統合・最適化完了
**次のマイルストーン**: v3.4.0+ での追加機能実装
