# YouTube Live Event Logic - Quick Reference

**Date:** 2025年12月20日
**Version:** v3.x
**Status:** ✅ 完成・検証済み

> **注意**: このドキュメントは簡易版です。詳細な実装ドキュメントは以下を参照してください：
> - [COMPREHENSIVE_AUTOPOST_LOGIC.md](./COMPREHENSIVE_AUTOPOST_LOGIC.md) - 包括的な解析ドキュメント（推奨）

---

## YouTubeLive イベント投稿の 4 段階

### ステージ 1: スケジュール（予定されたライブ）

**タイミング**: RSS フィード取得時
**ファイル**: `youtube_live_cache.py`, `database.py`

```python
# キャッシュに追加
def add_live_video(video_id, title, start_time):
    live_videos[video_id] = {
        "title": title,
        "start_time": start_time,
        "status": "upcoming"        # 予定中
    }

# DB に保存
content_type = "live"               # ライブ配信
live_status = "upcoming"            # 予定中
is_premiere = False                 # 通常のライブ
```

**DB 状態**:
```
content_type = "live"
live_status = "upcoming"
```

---

### ステージ 2: 開始（ライブ配信開始）

**タイミング**: RSS フィード検知または API ポーリング
**ファイル**: `youtube_live_plugin.py`

#### 検知方法
- **RSS フィード**: 新着として検知された時点で DB に登録
- **API ポーリング**: 定期的に API で `live_status` を確認

#### 自動投稿実行

```python
def auto_post_live_start(self, video: Dict[str, Any]) -> bool:
    """
    ライブ開始時の自動投稿

    テンプレート: TEMPLATE_YOUTUBE_ONLINE_PATH
    ファイル: templates/youtube/yt_online_template.txt
    """
    video_copy = dict(video)
    video_copy["event_type"] = "live_start"
    video_copy["live_status"] = "live"

    return bluesky_plugin.post_video(video_copy)
```

**DB 状態更新**:
```
content_type = "live"
live_status = "live"
```

**設定**:
```env
YOUTUBE_LIVE_AUTO_POST_START=true       # ライブ開始投稿有効
TEMPLATE_YOUTUBE_ONLINE_PATH=...        # テンプレート
```

---

### ステージ 3: 終了（ライブ配信終了）

**タイミング**: API ポーリングで `live_status="completed"` を検知
**ファイル**: `youtube_live_plugin.py`, `main_v3.py`

#### ポーリング設定

```python
# main_v3.py
poll_interval_minutes = int(os.getenv("YOUTUBE_LIVE_POLL_INTERVAL", "15"))

# バリデーション: 最短 15 分、最長 60 分
if poll_interval_minutes < 15:
    poll_interval_minutes = 15
elif poll_interval_minutes > 60:
    poll_interval_minutes = 60
```

#### 自動投稿実行

```python
def auto_post_live_end(self, video: Dict[str, Any]) -> bool:
    """
    ライブ終了時の自動投稿

    テンプレート: TEMPLATE_YOUTUBE_OFFLINE_PATH
    ファイル: templates/youtube/yt_offline_template.txt
    """
    video_copy = dict(video)
    video_copy["event_type"] = "live_end"
    video_copy["live_status"] = "completed"

    return bluesky_plugin.post_video(video_copy)
```

**DB 状態更新**:
```
content_type = "live"
live_status = "completed"
```

**設定**:
```env
YOUTUBE_LIVE_AUTO_POST_END=true                 # ライブ終了投稿有効
YOUTUBE_LIVE_POLL_INTERVAL=15                   # ポーリング間隔（分）
TEMPLATE_YOUTUBE_OFFLINE_PATH=...               # テンプレート
```

---

### ステージ 4: アーカイブ（配信終了後）

**タイミング**: 配信終了後、アーカイブ公開時
**ファイル**: `youtube_live_plugin.py`, `bluesky_plugin.py`

#### 判定ロジック

YouTube API が自動的にアーカイブを生成：
```
配信終了 → API で content_type="archive" を検知
```

**DB 状態**:
```
content_type = "archive"            # アーカイブ
live_status = null                  # ライブではない
```

#### テンプレート選択

```python
if content_type == "archive":
    template_env = os.getenv("TEMPLATE_YOUTUBE_ARCHIVE_PATH")
    # テンプレート: templates/youtube/yt_archive_template.txt
    # 未設定時: youtube_new_video テンプレートにフォールバック
```

**設定**:
```env
TEMPLATE_YOUTUBE_ARCHIVE_PATH=...    # アーカイブテンプレート
```

---

## ライブイベント投稿フロー

```
YouTubeAPI / RSS
    │
    ├─── RSS 新着検知 ──────┐
    │                      │
    ▼                      ▼
【予定中】                【予定中】
live_status=          content_type=
"upcoming"            "live"
    │                      │
    │ API ポーリング開始    │
    │                      │
    ▼                      ▼
【開始検知】              【開始検知】
live_status=          live_status=
"live"                "live"
    │                      │
    ├──────────────────────┘
    │
    ▼ [自動投稿]
📤 yt_online_template.txt で投稿
    │
    │ 監視継続（API ポーリング）
    │
    ▼
【終了検知】
live_status=
"completed"
    │
    ▼ [自動投稿]
📤 yt_offline_template.txt で投稿
    │
    ▼
【アーカイブ判定】
content_type=
"archive"
    │
    ▼ [投稿（オプション）]
📤 yt_archive_template.txt で投稿
```

---

## 重要なパラメータ

### DB 関連

| フィールド | 値 | 説明 |
|:--|:--|:--|
| `content_type` | "live" / "archive" / "video" | コンテンツ種別 |
| `live_status` | "upcoming" / "live" / "completed" / null | ライブ状態 |
| `is_premiere` | 0 / 1 | プレミア配信フラグ |

### 環境変数

| 変数 | デフォルト | 説明 |
|:--|:--|:--|
| `YOUTUBE_LIVE_AUTO_POST_START` | true | ライブ開始投稿 |
| `YOUTUBE_LIVE_AUTO_POST_END` | true | ライブ終了投稿 |
| `YOUTUBE_LIVE_POLL_INTERVAL` | 15 | ポーリング間隔（分） |
| `TEMPLATE_YOUTUBE_ONLINE_PATH` | - | 開始テンプレート |
| `TEMPLATE_YOUTUBE_OFFLINE_PATH` | - | 終了テンプレート |
| `TEMPLATE_YOUTUBE_ARCHIVE_PATH` | - | アーカイブテンプレート |

---

## テンプレート変数

すべてのテンプレートで以下の変数が利用可能：

```jinja2
{{ title }}             # 動画タイトル
{{ video_id }}          # 動画ID
{{ video_url }}         # 動画URL
{{ channel_name }}      # チャンネル名
{{ published_at }}      # 公開日時
{{ live_status }}       # ライブ状態（開始時に表示）
{{ event_type }}        # イベント種別（live_start/live_end）
```

---

## 参考ドキュメント

📚 **詳細な実装ドキュメント**:
- [COMPREHENSIVE_AUTOPOST_LOGIC.md](./COMPREHENSIVE_AUTOPOST_LOGIC.md) ⭐ **推奨**（YouTubeLive詳細）
- [PLUGIN_SYSTEM.md](./PLUGIN_SYSTEM.md)（プラグイン実装）
- [TEMPLATE_SYSTEM.md](./TEMPLATE_SYSTEM.md)（テンプレート）

---

**作成日**: 2025年12月20日
**ステータス**: ✅ 完成・検証済み
