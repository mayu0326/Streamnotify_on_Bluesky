# YouTubeLive 終了検出 - キャッシュ機構の実装

**実装日**: 2025-12-19
**バージョン**: v3.4.0 / v2.3.1
**ステータス**: ✅ 実装完了

---

## 📋 概要

- YouTubeLive の終了検出フローを改善し、**キャッシュ機構**を導入しました。
- DB と API データを組み合わせて管理し、ポーリング結果に基づいて段階的に DB を更新するようになります。

---

## 🔄 新しい終了検出フロー

```
main_v3.py（定期ポーリングスレッド）
    ↓ YOUTUBE_LIVE_POLL_INTERVAL ごと（15分～60分）
poll_live_status()（YouTubeLiveプラグイン）
    ↓
① DB から live_status='live' の動画を取得
    ↓
② 各動画の現在状態を API で確認
    ↓
③ DBから得られたデータと APIで確認したデータを組み合わせて、
   LIVEキャッシュとして JSON で保持（data/youtube_live_cache.json）
    ↓
④ ポーリング（上記の動画ID について）を行い、結果に基づきキャッシュを更新
    ↓
⑤ データに基づき、LIVE終了のAPIデータが取れたら終了と判定
    → キャッシュデータで本番DBを更新
    ↓
⑥ 設定に基づき自動投稿（オプション）
```

---

## 📁 新規ファイル

### `youtube_live_cache.py`

**役割**: YouTubeLive キャッシュ管理

**主要メソッド**:
- `add_live_video(video_id, db_data, api_data)` - キャッシュに新規追加
- `update_live_video(video_id, api_data)` - ポーリング結果でキャッシュ更新
- `mark_as_ended(video_id)` - 終了状態にマーク
- `remove_live_video(video_id)` - キャッシュから削除
- `get_live_video(video_id)` - キャッシュから取得
- `get_live_videos_by_status(status)` - ステータスでフィルタ

**キャッシュファイル**: `v3/data/youtube_live_cache.json`

**キャッシュエントリ構造**:
```json
{
  "dQw4w9WgXcQ": {
    "video_id": "dQw4w9WgXcQ",
    "db_data": {
      "title": "新作動画",
      "channel_name": "My Channel",
      "video_url": "https://...",
      "published_at": "2025-12-19T10:00:00",
      "thumbnail_url": "https://..."
    },
    "api_data": {
      "snippet": { ... },
      "liveStreamingDetails": { ... },
      "status": { ... }
    },
    "cached_at": "2025-12-19T10:30:00.123456",
    "status": "live",
    "poll_count": 3,
    "last_polled_at": "2025-12-19T11:00:00.654321",
    "ended_at": null
  }
}
```

---

## ⚙️ ポーリング間隔の制限

### デフォルト値の変更

| 項目 | 前 | 後 |
|:--|:--|:--|
| デフォルト | 5分 | **15分** |
| 最短 | なし | **15分**（強制） |
| 最長 | なし | **60分**（強制） |

### 設定方法

`settings.env` で指定:
```env
# 推奨値: 15分（最短）～30分（標準）～60分（最長）
YOUTUBE_LIVE_POLL_INTERVAL=15
```

### バリデーション（自動調整）

```python
# main_v3.py / main_v2.py

poll_interval_minutes = int(os.getenv("YOUTUBE_LIVE_POLL_INTERVAL", "15"))

if poll_interval_minutes < 15:
    logger.warning(f"⚠️ 最短15分に調整: {poll_interval_minutes} → 15")
    poll_interval_minutes = 15
elif poll_interval_minutes > 60:
    logger.warning(f"⚠️ 最長60分に調整: {poll_interval_minutes} → 60")
    poll_interval_minutes = 60
```

---

## 🔍 ポーリング処理の詳細

### ステップ①：DB から live_status='live' を取得

```python
live_videos = self.db.get_videos_by_live_status("live")
# → [{video_id, title, channel_name, ...}, ...]
```

### ステップ②：API で現在状態を確認

```python
details = self.api_plugin._fetch_video_detail(video_id)
# → {snippet, liveStreamingDetails, status, ...}
```

### ステップ③：キャッシュに DB + API データを保存

```python
# 初回
cache_entry = cache.get_live_video(video_id)
if not cache_entry:
    db_data = {
        "title": video.get("title"),
        "channel_name": video.get("channel_name"),
        "video_url": video.get("video_url"),
        "published_at": video.get("published_at"),
        "thumbnail_url": video.get("thumbnail_url"),
    }
    cache.add_live_video(video_id, db_data, details)
    # → data/youtube_live_cache.json に保存
```

### ステップ④：ポーリング結果でキャッシュ更新

```python
# 2回目以降
cache.update_live_video(video_id, details)
# → poll_count + 1、last_polled_at 更新
```

### ステップ⑤：終了判定 → DB 更新

```python
content_type, live_status, is_premiere = self._classify_live(details)

if live_status == "completed" or content_type == "archive":
    # キャッシュを終了状態に更新
    cache.mark_as_ended(video_id)

    # DB 更新
    self.db.update_video_status(video_id, content_type, live_status)

    # 終了済み動画をキャッシュから削除
    cache.remove_live_video(video_id)
```

### ステップ⑥：自動投稿（オプション）

```python
auto_post_end = os.getenv("YOUTUBE_LIVE_AUTO_POST_END", "true").lower() == "true"
if auto_post_end:
    self.auto_post_live_end(video)  # → Bluesky へ投稿
```

---

## 📊 キャッシュ操作のログ出力例

### 初回ポーリング時

```
🔄 3 件のライブ中動画をチェック中...
📌 キャッシュに追加: dQw4w9WgXcQ
✅ LIVE キャッシュに追加: dQw4w9WgXcQ
```

### 2回目ポーリング時

```
🔄 3 件のライブ中動画をチェック中...
🔄 キャッシュを更新: dQw4w9WgXcQ
✅ キャッシュ更新: dQw4w9WgXcQ (ポーリング: 2 回)
```

### ライブ終了検知時

```
✅ ライブ終了を検知: dQw4w9WgXcQ (live_status=completed, content_type=archive)
✅ キャッシュを終了状態に更新: dQw4w9WgXcQ
✅ キャッシュから削除: dQw4w9WgXcQ
📡 ライブ終了自動投稿を実行します: 新作動画
```

---

## 🎯 ポーリング間隔の推奨値

| シナリオ | 推奨値 | 理由 |
|:--|:--|:--|
| 短時間ライブ（1時間未満） | 15分 | 終了検知を素早く |
| 標準ライブ（1～3時間） | 30分 | バランス型 |
| 長時間ライブ（3時間以上） | 60分 | API クォータ節約 |

---

## ✅ チェックリスト

実装確認項目:
- ✅ `youtube_live_cache.py` を v3、v2 に作成
- ✅ `youtube_live_plugin.py` の `poll_live_status()` をキャッシュ対応
- ✅ `main_v3.py` と `main_v2.py` のポーリング間隔を 15～60分に制限
- ✅ `settings.env.example` をドキュメント化
- ✅ デフォルト値を 15分に変更
- ✅ ログ出力を整備

---

## 📝 関連ファイル

| ファイル | 変更内容 |
|:--|:--|
| `v3/youtube_live_cache.py` | 新規作成 |
| `v2/youtube_live_cache.py` | 新規作成 |
| `v3/plugins/youtube_live_plugin.py` | `poll_live_status()` 更新、インポート追加 |
| `v2/plugins/youtube_live_plugin.py` | `poll_live_status()` 更新、インポート追加 |
| `v3/main_v3.py` | ポーリング間隔バリデーション追加 |
| `v2/main_v2.py` | ポーリング間隔バリデーション追加 |
| `v3/settings.env.example` | 設定項目ドキュメント更新 |
| `v2/settings.env.example` | 設定項目ドキュメント更新 |

---

## 🔗 参考資料

- [YouTubeLive プラグイン実装](../Technical/YOUTUBE_LIVE_PLUGIN_IMPLEMENTATION.md)
- [YouTube API プラグイン実装](../Technical/PLUGIN_SYSTEM.md)
