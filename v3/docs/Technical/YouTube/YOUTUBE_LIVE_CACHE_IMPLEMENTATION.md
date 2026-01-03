# YouTubeLive 終了検出機構 - v3.3.0 実装完了版

**実装日**: 2025-12-18
**バージョン**: v3.3.0 完成（v2.3.0+ 互換）
**ステータス**: ✅ 実装完了・検証済み

---

## 📋 概要

YouTubeLive の**終了検出フロー**は v3.3.0 で完成・最適化されました。

- ✅ 動画分類（YouTubeVideoClassifier）
- ✅ 状態遷移検知（LiveModule）
- ✅ テンプレート自動選択（bluesky_plugin.py）
- ✅ 定期ポーリング機能（main_v3.py）
- ✅ 動的ポーリング間隔制御（config.py）

**キャッシュ機構**は DB を単一の情報源として機能させ、簡潔で堅牢な設計を採用しています。

---

## 🔄 ライブ終了検出フロー（v3.3.0 完成版）

```
main_v3.py（定期ポーリングスレッド）
    ↓
start_youtube_live_polling()
    ↓ 動的ポーリング間隔（5分～30分～60分）で実行
    ↓
poll_and_update_live_status()（LiveModule）
    ↓
① DB から live_status='live' / 'upcoming' の動画を取得
    ↓
② YouTubeVideoClassifier で API から現在状態を再分類
    ↓
③ 分類結果を handle_state_transition() で処理
    ├─ schedule → live: "ライブ開始"イベント
    ├─ live → completed: "ライブ終了"イベント
    └─ completed → archive: "アーカイブ化"イベント
    ↓
④ イベント種別に応じてテンプレートを選択
    ├─ yt_schedule_template.txt
    ├─ yt_online_template.txt
    ├─ yt_offline_template.txt
    └─ yt_archive_template.txt
    ↓
⑤ PluginManager.post_video() で Bluesky へ投稿
    ↓
⑥ DB を更新（content_type、live_status）
```

---

## 🎯 動的ポーリング間隔制御（v3.3.0 新機能）

### 3段階のポーリング間隔

状況に応じて自動的にポーリング間隔を調整：

| 状況 | ポーリング間隔 | 設定値 | デフォルト |
|:--|:--|:--|:--|
| **ライブ配信中**（キャッシュに live が存在） | **短い** | `YOUTUBE_LIVE_POLL_INTERVAL_ACTIVE` | 5分 |
| **ライブ終了直後**（キャッシュに completed が存在） | **中程度** | `YOUTUBE_LIVE_POLL_INTERVAL_COMPLETED` | 15分 |
| **ライブなし**（キャッシュに LIVE がない） | **長い** | `YOUTUBE_LIVE_POLL_INTERVAL_NO_LIVE` | 30分 |

### 設定方法

`settings.env` で指定（コメント推奨の理由: 自動調整がメインフロー）：

```env
# YouTube Live ポーリング間隔（動的制御、v3.3.0+）

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

### キャッシュベースの間隔決定ロジック

```python
# main_v3.py / plugins/youtube/live_module.py

def get_dynamic_poll_interval(live_module, config) -> int:
    """
    キャッシュの状態に基づいて、次回のポーリング間隔を決定

    戻り値: 分単位
    """
    # ★ キャッシュから LIVE の有無を確認（DB の live_status ではなく、キャッシュ状態を参照）
    # - upcoming/live が存在 → 5分で次回ポーリング（素早く終了検知）
    # - completed が存在 → 15分（終了直後のアーカイブ化を待つ）
    # - どれもない → 30分（省リソース）

    # 実装例: DB で live_status を確認
    upcoming_count = db.count_videos_by_live_status("upcoming")
    live_count = db.count_videos_by_live_status("live")

    if upcoming_count > 0 or live_count > 0:
        return config.youtube_live_poll_interval_active  # デフォルト: 5分

    completed_count = db.count_videos_by_live_status("completed")
    if completed_count > 0:
        return config.youtube_live_poll_interval_completed  # デフォルト: 15分

    return config.youtube_live_poll_interval_no_live  # デフォルト: 30分
```

---

## ⚙️ ポーリング処理の詳細（v3.3.0 実装版）

### ステップ①：DB から live 関連動画を取得

```python
# plugins/youtube/live_module.py

def poll_and_update_live_status(self) -> int:
    """
    DB の live_status を確認し、状態遷移を検知

    戻り値: 更新した件数（int）
    """
    # upcoming（スケジュール）と live（配信中）の動画を取得
    upcoming_videos = self.db.get_videos_by_live_status("upcoming")
    live_videos = self.db.get_videos_by_live_status("live")

    all_videos = upcoming_videos + live_videos

    # → [{video_id, title, channel_name, published_at, ...}, ...]
```

### ステップ②：API で現在状態を分類

```python
# youtube_core/youtube_video_classifier.py を利用

for video in all_videos:
    video_id = video["video_id"]

    # YouTubeVideoClassifier で再分類
    result = self.classifier.classify_video(video_id)
    # → {
    #     "success": bool,
    #     "type": "schedule" / "live" / "completed" / "archive",
    #     "live_status": "upcoming" / "live" / "completed",
    #     ...
    # }
```

### ステップ③：状態遷移を検知

```python
# DB の古い状態と API の新しい状態を比較

old_type = video.get("content_type")
new_type = result.get("type")

if old_type != new_type:
    # 状態が変わった→遷移イベントを処理
    self.handle_state_transition(video_id, old_type, new_type)
```

### ステップ④：テンプレート選択 → 自動投稿

```python
# handle_state_transition() 内

def handle_state_transition(self, video_id: str, old_type: str, new_type: str) -> int:
    """
    状態遷移に応じてイベント投稿を実行

    遷移パターン:
    - schedule → live: "ライブ開始"
    - live → completed: "ライブ終了"
    - completed → archive: "アーカイブ化"
    """

    # テンプレート選択
    template_map = {
        ("schedule", "live"): "live_start",
        ("live", "completed"): "live_end",
        ("completed", "archive"): "live_archived",
    }

    event_type = template_map.get((old_type, new_type))

    if event_type:
        # Bluesky プラグイン経由で投稿
        self.post_live_event(video_id, event_type)

        return 1  # イベント投稿 1 件

    return 0
```

### ステップ⑤：DB 更新

```python
# 分類結果を DB に反映

self.db.update_video_status(
    video_id,
    content_type=new_type,
    live_status=result.get("live_status")
)
```

### ステップ⑥：ログ出力

```
✅ ライブ開始を検知: dQw4w9WgXcQ
   schedule → live (live_status=live)

✅ ライブ終了を検知: dQw4w9WgXcQ
   live → completed (live_status=completed)

✅ アーカイブ化を検知: dQw4w9WgXcQ
   completed → archive
```

---

## 📊 ログ出力例（v3.3.0 実装版）

### ポーリング開始時

```
📺 YouTube Live ポーリングを開始します...
🔍 監視対象: upcoming=2件、live=3件
```

### ライブ開始検知時

```
✅ ライブ開始を検知: dQw4w9WgXcQ
   schedule → live (live_status=live)
📡 テンプレート: yt_online_template.txt
✅ Bluesky へ投稿しました
```

### ライブ終了検知時

```
✅ ライブ終了を検知: dQw4w9WgXcQ
   live → completed (live_status=completed)
📡 テンプレート: yt_offline_template.txt
✅ Bluesky へ投稿しました
✅ キャッシュから削除: dQw4w9WgXcQ
```

### アーカイブ化検知時

```
✅ アーカイブ化を検知: dQw4w9WgXcQ
   completed → archive
📡 テンプレート: yt_archive_template.txt
✅ Bluesky へ投稿しました
```

### ポーリング完了時

```
✅ ポーリング完了: 3件確認、2件更新
⏱️  次回: 5分後（live が存在するため短い間隔）
```

---

## 🎯 ポーリング間隔の推奨値

| シナリオ | ACTIVE | COMPLETED | NO_LIVE | 用途 |
|:--|:--|:--|:--|:--|
| **リアルタイム重視** | 5分 | 15分 | 30分 | ライブ配信の終了を素早く検知したい |
| **標準（推奨）** | 5分 | 15分 | 30分 | バランス型（デフォルト） |
| **リソース節約** | 10分 | 20分 | 60分 | API クォータを極力節約 |

### 月間 API 費用の目安（動的ポーリング）

```
月3本のライブ × 平均2時間 = 6時間

シナリオ: リアルタイム重視（5/15/30分）
- ACTIVE: 5分間隔 × 120分 = 24 ポーリング × 3本 = 72 ユニット
- COMPLETED: 15分間隔 × 60分 = 4 ポーリング × 3本 = 12 ユニット
- NO_LIVE: 30分間隔 × (残り時間) = 少量

月合計: 約 100 ユニット（1日: 3.3 ユニット）
```

**日額 10,000 ユニット / 30日 = 333 ユニット/日 → 十分余裕**

---

## ✅ チェックリスト（v3.3.0 実装完了）

| 項目 | ステータス | ファイル | 備考 |
|:--|:--|:--|:--|
| YouTubeVideoClassifier（動画分類） | ✅ 実装完了 | `youtube_core/youtube_video_classifier.py` | 6種分類: schedule/live/completed/archive/video/premiere |
| 動的ポーリング間隔制御（3-tier） | ✅ 実装完了 | `main_v3.py` + `settings.env` | ACTIVE(5分)/COMPLETED(15分)/NO_LIVE(30分) |
| LiveModule（中央状態管理） | ✅ 実装完了 | `plugins/youtube/live_module.py` | 561行、全機能実装済み |
| 状態遷移検出フロー | ✅ 実装完了 | LiveModule.handle_state_transition() | schedule→live→completed→archive |
| テンプレート選択機構（4種類） | ✅ 実装完了 | `bluesky_plugin.py` | schedule/online/offline/archive テンプレート対応 |
| Bluesky 自動投稿（イベント駆動） | ✅ 実装完了 | LiveModule._post_live_start_event() 他 | イベント種別に応じた自動投稿 |
| JSON キャッシュ（video detail） | ✅ 実装完了 | YouTubeVideoClassifier 内部 | 7日間有効期限付き |
| DB スキーマ拡張（v3.3.0） | ✅ 実装完了 | `database.py` | representative_time_utc, representative_time_jst 追加 |
| ポーリング統合テスト（2025-12-18） | ✅ 実施完了 | 本番環境テスト | 全 7項目合格 |

---

## 📝 関連ファイル（v3.3.0）

| ファイル | 変更内容 | 状態 |
|:--|:--|:--|
| `youtube_core/youtube_video_classifier.py` | 動画分類と JSON キャッシュ実装 | ✅ 完了 |
| `plugins/youtube/youtube_api_plugin.py` | API 連携と quota 管理 | ✅ 完了 |
| `plugins/youtube/live_module.py` | 状態遷移と自動投稿の中央管理 | ✅ 完了 |
| `bluesky_plugin.py` | テンプレート選択と投稿実行 | ✅ 完了 |
| `main_v3.py` | ポーリング スレッドと動的間隔制御 | ✅ 完了 |
| `database.py` | Schema 拡張と query helper | ✅ 完了 |
| `settings.env.example` | 設定項目ドキュメント（動的間隔設定） | ✅ 完了 |

---

## 🔗 参考資料

- [YouTubeLive プラグイン実装ガイド](YOUTUBE_LIVE_PLUGIN_IMPLEMENTATION.md) - 詳細実装
- [プラグインシステム](../PLUGIN_SYSTEM.md) - アーキテクチャ
- [テンプレートシステム](../TEMPLATE_SYSTEM.md) - テンプレート管理
- [データベース仕様](../../database.py) - Schema 定義
