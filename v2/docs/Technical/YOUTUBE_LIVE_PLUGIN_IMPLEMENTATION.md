# YouTubeLive プラグイン完成実装ガイド

**対象バージョン**: v2.3.0
**最終更新**: 2025-12-18
**ステータス**: 🔄 実装予定（v2完了条件）

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

YouTubeLive プラグインは現在「枠のみ実装」状態です。v2 の完了条件として、以下の機能を実装します：

1. ✅ ライブ開始/終了の自動検知ロジック
2. ✅ ライブイベント用テンプレート自動適用
3. ✅ `live_status` の自動更新機能

**v2完了予定**: v2.3.0

---

## v2完了の定義

YouTubeLive プラグインの完成をもって **v2 完了** とします。

### v2 完了条件

以下の機能がすべて実装され、テスト済みであること：

- [🔄] ライブ開始の自動検知
  - RSS または API ポーリングでライブ開始を検知
  - DB の `live_status` を `live` に更新
  - `yt_online_template.txt` で Bluesky に自動投稿

- [🔄] ライブ終了の自動検知
  - API ポーリングでライブ終了を検知
  - DB の `live_status` を `completed` に更新
  - `yt_offline_template.txt` で Bluesky に自動投稿

- [🔄] アーカイブ化の検知
  - ライブ終了後のアーカイブ変換を検知
  - DB の `content_type` を `archive` に更新

- [🔄] テンプレート自動適用
  - イベント種別に応じて適切なテンプレートを自動選択
  - `yt_online_template.txt`: ライブ開始時
  - `yt_offline_template.txt`: ライブ終了時
  - `yt_new_video_template.txt`: 通常動画・アーカイブ

### v3 以降に繰り下げる機能

以下の機能は v3 で実装予定：

- ❌ 一括投稿スケジュール機能
- ❌ GUI 機能拡張（検索・フィルタ・統計詳細）
- ❌ バックアップ・復元機能
- ❌ RSS 手動更新ボタン
- ❌ 重複投稿防止オプション
- ❌ 投稿テンプレート動的変数

---

## 現状分析

### 実装済み機能

```python
# youtube_live_plugin.py

class YouTubeLivePlugin(NotificationPlugin):
    def __init__(self):
        # YouTube API プラグインを利用
        self.api_plugin = YouTubeAPIPlugin()
        self.api_key = self.api_plugin.api_key
        self.channel_id = self.api_plugin.channel_id
        self.db = self.api_plugin.db

    def post_video(self, video: Dict[str, Any]) -> bool:
        """
        ライブ/アーカイブ判定を行い DB に保存
        ✅ 実装済み
        """
        # API から動画詳細を取得
        # ライブ判定・分類
        # DB に保存

    def _classify_live(self, details: Dict[str, Any]) -> Tuple[str, Optional[str], bool]:
        """
        ライブ/アーカイブを判別
        ✅ 実装済み（youtube_api_plugin に委譲）
        """
        return self.api_plugin._classify_video_core(details)
```

### 未実装機能

| 機能 | 状態 | 優先度 |
|:--|:--:|:--:|
| ライブ開始の自動検知 | ❌ 未実装 | 最優先 |
| ライブ終了の自動検知 | ❌ 未実装 | 最優先 |
| テンプレート自動適用 | ❌ 未実装 | 高 |
| 定期ポーリング機能 | ❌ 未実装 | 高 |
| イベント投稿ロジック | ❌ 未実装 | 高 |

**具体的な未実装メソッド・機能**:

1. **youtube_live_plugin.py**:
   - `auto_post_live_start(video)` - ライブ開始時の自動投稿メソッド
   - `auto_post_live_end(video)` - ライブ終了時の自動投稿メソッド
   - `poll_live_status()` - ライブ中動画の定期チェックメソッド

2. **database.py**:
   - `get_videos_by_live_status(status)` - live_statusでフィルタするクエリメソッド

3. **bluesky_plugin.py**:
   - `post_video()` 内のテンプレート選択ロジックに `live_status` 分岐が未実装
   - 現在は `source` ("youtube"/"niconico") のみでテンプレートを選択

4. **main_v2.py**:
   - 定期ポーリングループ（スレッド起動）が未実装
   - `poll_live_status()` を定期実行する仕組みがない

5. **settings.env.example**:
   - `YOUTUBE_LIVE_POLL_INTERVAL` - ポーリング間隔設定
   - `YOUTUBE_LIVE_AUTO_POST_START` - ライブ開始自動投稿ON/OFF
   - `YOUTUBE_LIVE_AUTO_POST_END` - ライブ終了自動投稿ON/OFF

6. **テンプレートファイル**:
   - ✅ `yt_online_template.txt` - 配置済み
   - ✅ `yt_offline_template.txt` - 配置済み
   - ❌ テンプレート自動選択ロジック - 未実装

---

## 実装要件

### 1. ライブ開始の自動検知

#### 要件

- RSS または API ポーリングでライブ配信開始を検知
- DB の `live_status` を `upcoming` → `live` に更新
- Bluesky に `yt_online_template.txt` で自動投稿

#### 実装方針

**Option A: RSS + API 併用（推奨）**
- RSS で新着動画を検知
- `post_video()` で API 詳細取得
- `live_status` が `live` の場合は自動投稿

**Option B: API 定期ポーリング**
- `search.list` API で `eventType=live` を定期実行
- コスト: 100 ユニット/回
- 高頻度実行は API クォータを消費

#### 推奨実装

**RSS + API 併用**を採用：
- RSS で新着を検知（コスト 0）
- API で詳細確認（コスト 1 ユニット/動画）
- クォータ効率が最良

### 2. ライブ終了の自動検知

#### 要件

- API ポーリングでライブ配信終了を検知
- DB の `live_status` を `live` → `completed` に更新
- Bluesky に `yt_offline_template.txt` で自動投稿

#### 実装方針

**定期ポーリング**：
- `live_status = 'live'` の動画を定期的に API チェック
- `liveBroadcastContent` が `none` に変化したら終了検知
- コスト: 1 ユニット/動画

#### ポーリング間隔

- デフォルト: **5分ごと**
- 設定可能: `YOUTUBE_LIVE_POLL_INTERVAL` (分単位)

### 3. テンプレート自動適用

#### 要件

イベント種別に応じて適切なテンプレートを自動選択：

| イベント | テンプレート | タイミング |
|:--|:--|:--|
| ライブ開始 | `yt_online_template.txt` | `live_status`: `upcoming` → `live` |
| ライブ終了 | `yt_offline_template.txt` | `live_status`: `live` → `completed` |
| 通常動画 | `yt_new_video_template.txt` | RSS 新着検知時 |
| アーカイブ | `yt_new_video_template.txt` | 同上 |

#### 実装方針

```python
def _select_template(self, video: Dict[str, Any], event_type: str) -> str:
    """
    イベント種別に応じてテンプレートパスを返す

    Args:
        video: 動画情報
        event_type: "live_start" / "live_end" / "new_video"

    Returns:
        テンプレートファイルパス
    """
    template_map = {
        "live_start": "templates/youtube/yt_online_template.txt",
        "live_end": "templates/youtube/yt_offline_template.txt",
        "new_video": "templates/youtube/yt_new_video_template.txt",
    }
    return template_map.get(event_type, "templates/youtube/yt_new_video_template.txt")
```

---

## 実装計画

### Phase 1: ライブ開始検知（最優先）

#### 1.1 RSS 監視強化

```python
# youtube_rss.py に追加

def fetch_youtube_rss_with_live_check(channel_id: str, api_plugin=None) -> List[Dict]:
    """
    RSS 取得 + ライブ状態チェック

    新着動画を検知したら、API でライブ判定を実施
    """
    videos = fetch_youtube_rss(channel_id)

    if api_plugin and api_plugin.is_available():
        for video in videos:
            details = api_plugin._fetch_video_detail(video["video_id"])
            if details:
                content_type, live_status, is_premiere = api_plugin._classify_video_core(details)
                video["content_type"] = content_type
                video["live_status"] = live_status
                video["is_premiere"] = is_premiere

    return videos
```

#### 1.2 自動投稿ロジック

```python
# youtube_live_plugin.py に追加

def auto_post_live_start(self, video: Dict[str, Any]) -> bool:
    """
    ライブ開始時の自動投稿

    Args:
        video: 動画情報（live_status="live"）

    Returns:
        投稿成功フラグ
    """
    # テンプレート選択
    template_path = self._select_template(video, "live_start")

    # Bluesky プラグイン呼び出し
    if self.bluesky_plugin and self.bluesky_plugin.is_available():
        video["template_path"] = template_path
        return self.bluesky_plugin.post_video(video)

    return False
```

### Phase 2: ライブ終了検知

#### 2.1 定期ポーリング機能

```python
# youtube_live_plugin.py に追加

def poll_live_status(self) -> None:
    """
    ライブ中の動画を定期チェックし、終了を検知

    - DB から live_status='live' の動画を取得
    - API で現在の状態を確認
    - 終了していれば DB 更新 + 自動投稿
    """
    live_videos = self.db.get_videos_by_live_status("live")

    for video in live_videos:
        video_id = video["video_id"]
        details = self.api_plugin._fetch_video_detail(video_id)

        if not details:
            continue

        content_type, live_status, is_premiere = self._classify_live(details)

        # ライブ終了検知
        if live_status == "completed" or content_type == "archive":
            self.db.update_video_status(video_id, content_type, live_status)
            self.auto_post_live_end(video)
```

#### 2.2 スケジューリング

```python
# main_v2.py に追加

def start_live_polling(plugin_manager, interval_minutes=5):
    """
    ライブ終了検知のための定期ポーリングを開始

    Args:
        plugin_manager: プラグインマネージャー
        interval_minutes: ポーリング間隔（分）
    """
    import threading
    import time

    def polling_loop():
        while True:
            try:
                live_plugin = plugin_manager.get_plugin("youtube_live_plugin")
                if live_plugin and live_plugin.is_available():
                    live_plugin.poll_live_status()
            except Exception as e:
                logger.error(f"ライブポーリングエラー: {e}")

            time.sleep(interval_minutes * 60)

    thread = threading.Thread(target=polling_loop, daemon=True)
    thread.start()
```

### Phase 3: テンプレート統合

#### 3.1 Asset ディレクトリのテンプレート（配置済み）

```
Asset/templates/youtube/
  ├── yt_new_video_template.txt    # ✅ 既存
  ├── yt_online_template.txt        # ✅ 既存（配置済み）
  └── yt_offline_template.txt       # ✅ 既存（配置済み）

templates/youtube/  ← 実行時ディレクトリ（自動配置済み）
  ├── yt_new_video_template.txt    # ✅ 配置済み
  ├── yt_online_template.txt        # ✅ 配置済み
  └── yt_offline_template.txt       # ✅ 配置済み
```

#### 3.2 テンプレートサンプル

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

---

## 技術仕様

### データベーススキーマ

```sql
-- videos テーブル（既存）
CREATE TABLE videos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    video_url TEXT NOT NULL,
    published_at TEXT NOT NULL,
    channel_name TEXT,
    posted_to_bluesky INTEGER DEFAULT 0,
    selected_for_post INTEGER DEFAULT 0,
    scheduled_at TEXT,
    posted_at TEXT,
    thumbnail_url TEXT,
    content_type TEXT DEFAULT 'video',       -- "video" / "live" / "archive"
    live_status TEXT,                        -- null / "upcoming" / "live" / "completed"
    is_premiere INTEGER DEFAULT 0,
    image_mode TEXT,
    image_filename TEXT,
    source TEXT DEFAULT 'youtube',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 追加クエリヘルパー（database.py）
def get_videos_by_live_status(self, live_status: str) -> List[Dict]:
    """
    指定された live_status の動画を取得

    Args:
        live_status: "upcoming" / "live" / "completed"

    Returns:
        動画情報リスト
    """
```

### 環境変数

```bash
# settings.env に追加

# YouTube Live ポーリング間隔（分単位、デフォルト: 5）
YOUTUBE_LIVE_POLL_INTERVAL=5

# ライブ開始時の自動投稿を有効にする（true/false）
YOUTUBE_LIVE_AUTO_POST_START=true

# ライブ終了時の自動投稿を有効にする（true/false）
YOUTUBE_LIVE_AUTO_POST_END=true
```

---

## テスト計画

### 単体テスト

```python
# test_scripts/test_youtube_live_detection.py

def test_live_start_detection():
    """ライブ開始検知のテスト"""
    # RSS で新着を検知
    # API で live_status="live" を確認
    # DB に保存
    # 自動投稿が実行されるか確認

def test_live_end_detection():
    """ライブ終了検知のテスト"""
    # DB に live_status="live" の動画を用意
    # API で live_status="completed" を確認
    # DB 更新
    # 自動投稿が実行されるか確認

def test_template_selection():
    """テンプレート自動選択のテスト"""
    # イベント種別ごとに正しいテンプレートが選択されるか確認
```

### 統合テスト

```python
# test_scripts/test_youtube_live_integration.py

def test_full_live_workflow():
    """ライブ配信の完全ワークフローテスト"""
    # 1. ライブ予定動画を検知
    # 2. ライブ開始を検知
    # 3. Bluesky に投稿（yt_online_template）
    # 4. ライブ終了を検知
    # 5. Bluesky に投稿（yt_offline_template）
    # 6. アーカイブ化を確認
```

---

## リリース計画

### v2.3.0 リリース内容

#### 新機能
- ✅ YouTubeLive プラグイン完成
  - ライブ開始/終了の自動検知
  - テンプレート自動適用
  - 定期ポーリング機能

#### バージョンアップ
- `app_version.py`: v2.1.0 → v2.3.0
- リリース日: 2025-12-XX（実装完了後）

#### ドキュメント更新
- [x] FUTURE_ROADMAP_v2.md（Phase 2 完了マーク）
- [ ] README.md（YouTubeLive 対応を追記）
- [ ] README_GITHUB_v2.md（同上）
- [ ] PLUGIN_SYSTEM.md（YouTubeLive プラグイン仕様追加）

---

## チェックリスト

### 実装

- [ ] RSS 監視強化（`youtube_rss.py`）
- [ ] ライブ開始検知（`youtube_live_plugin.py`）
- [ ] ライブ終了検知（定期ポーリング）
- [ ] テンプレート自動選択ロジック
- [ ] 自動投稿ロジック統合
- [ ] 環境変数追加（`settings.env.example`）
- [ ] DB クエリヘルパー追加（`database.py`）

### テンプレート

- [x] `Asset/templates/youtube/yt_online_template.txt` 作成（配置済み）
- [x] `Asset/templates/youtube/yt_offline_template.txt` 作成（配置済み）
- [ ] テンプレート選択ロジックの実装（`bluesky_plugin.py`）

### テスト

- [ ] 単体テスト実装
- [ ] 統合テスト実装
- [ ] 実環境でのテスト（実際のライブ配信で検証）

### ドキュメント

- [ ] README.md 更新
- [ ] README_GITHUB_v2.md 更新
- [ ] PLUGIN_SYSTEM.md 更新
- [ ] settings.env.example 更新

### リリース

- [ ] バージョン番号更新（v2.3.0）
- [ ] リリースノート作成
- [ ] Git タグ作成
- [ ] GitHub Release 公開

---

**最終更新**: 2025-12-18
**ステータス**: 🔄 実装予定（v2完了条件）
**次回更新**: 実装開始時
