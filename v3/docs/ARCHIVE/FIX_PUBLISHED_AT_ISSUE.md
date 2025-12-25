# 重大バグ修正: published_at が API データで更新されない問題

**問題レベル**: 🔴 **本番公開不可の重大問題**
**修正日**: 2025-12-24
**対象ファイル**:
- `youtube_rss.py` (RSS 追加時の既存動画更新)
- `database.py` (update_published_at の強化・エラーハンドリング)
- `plugins/youtube_live_plugin.py` (YouTubeLive 判定時の API 日時反映)

---

## 🔴 問題の本質

### 症状
YouTube の LIVE/Schedule 動画において：
- RSS 検出時に `published_at` が固定される
- YouTube API から取得した `scheduledStartTime`（より正確）がデータベースに反映されない
- **結果**: 投稿に表示される配信予定日時 ≠ 実際の配信予定日時

### 根本原因

| ファイル | 行 | 問題 |
|:--|:--|:--|
| `youtube_rss.py` | 181-183 | `api_scheduled_start_time != video["published_at"]` で比較。既に `final_published_at` として新しい値が DB に保存されているため、比較対象が一致しない |
| `database.py` | 1047 | エラーハンドリングが不足。DB ロック時の リトライが実装されていない |

---

## ✅ 修正内容

### 1️⃣ `youtube_rss.py` (既存動画の日時更新)

**修正前** (問題のある比較):
```python
if api_scheduled_start_time and api_scheduled_start_time != video["published_at"]:
    # video["published_at"] は RSS の値 → 既に DB に保存された final_published_at とは異なる
    database.update_published_at(video["video_id"], api_scheduled_start_time)
```

**修正後** (DB から実際の値を取得して比較):
```python
if api_scheduled_start_time:
    # DB から現在の published_at を取得して比較（確実な比較）
    cursor.execute("SELECT published_at FROM videos WHERE video_id = ?", (video["video_id"],))
    row = cursor.fetchone()
    db_published_at = row[0]

    if api_scheduled_start_time != db_published_at:
        database.update_published_at(video["video_id"], api_scheduled_start_time)
        logger.info(f"✅ 既存動画の published_at を API データで上書きしました")
```

### 2️⃣ `database.py` (リトライと詳細ログ強化)

**修正内容**:
- 🔄 DB ロック時のリトライ機構を実装
- 🧪 エラーハンドリングの詳細化
- 📝 API 優先度ログの出力強化

```python
def update_published_at(self, video_id: str, published_at: str) -> bool:
    # リトライループを追加
    for attempt in range(DB_RETRY_MAX):
        try:
            # DB ロック時は 0.5 秒待機してリトライ
        except sqlite3.OperationalError as e:
            if "locked" in str(e).lower() and attempt < DB_RETRY_MAX - 1:
                logger.debug(f"DB ロック中。{attempt + 1}/{DB_RETRY_MAX} リトライします...")
                time.sleep(0.5)
                continue
```

### 3️⃣ `plugins/youtube_live_plugin.py` (Live 判定時の API 日時反映)

**新規追加**: YouTube Live/Archive として判定された動画について、API から取得した `scheduledStartTime` を DB に反映

```python
# API から取得した日時を DB に反映
if live_details.get("scheduledStartTime"):
    api_published_at = live_details["scheduledStartTime"]
elif live_details.get("actualStartTime"):
    api_published_at = live_details["actualStartTime"]

if api_published_at:
    # DB の既存値と異なれば上書き
    database.update_published_at(video_id, api_published_at)
```

---

## 🧪 検証方法

### テストケース

```
1. YouTube LIVE 予約枠を RSS で検出
   RSS published_at: 2025-12-18 09:00:00Z

2. YouTube API から scheduledStartTime を取得
   API scheduledStartTime: 2025-12-28 18:00:00Z ← 実際の配信予定時刻

3. DB を確認
   旧（バグ）: published_at = 2025-12-18 09:00:00Z （RSS 値で固定）
   新（修正）: published_at = 2025-12-28 18:00:00Z ← API 値で更新
```

### ログ出力確認

**修正後は以下のログが出力されます**:

```
✅ 既存動画の published_at を API データで上書きしました: [動画名]
   旧: 2025-12-18T09:00:00Z
   新: 2025-12-28T18:00:00Z

✅ [★重要] published_at を API データで更新: video_id
   旧: 2025-12-18T09:00:00Z → 新: 2025-12-28T18:00:00Z
```

---

## 📋 修正一覧

| ファイル | 行数 | 変更内容 |
|:--|:--|:--|
| `youtube_rss.py` | 14 | `import sqlite3` を追加 |
| `youtube_rss.py` | 181-191 | 既存動画の API 日時更新ロジックを再実装 |
| `database.py` | 710-763 | `update_published_at()` に リトライとエラーハンドリングを追加 |
| `plugins/youtube_live_plugin.py` | 128-160 | YouTube Live 判定時の API 日時反映ロジックを追加 |

---

## ⚠️ 影響範囲

- **YouTube LIVE**: ✅ 修正完了（RSS + API 優先度対応）
- **YouTube Archive**: ✅ 修正完了（RSS + API 優先度対応）
- **YouTube 通常動画**: ✅ 修正完了（RSS + API 優先度対応）
- **Niconico**: 影響なし（API 統合されていない）

---

## 🚀 公開前チェックリスト

- [ ] ログファイル(`v3/logs/app.log`) で API 日時更新ログを確認
- [ ] DB(`v3/data/video_list.db`) の `published_at` が API データで更新されているか確認
- [ ] Bluesky への投稿で配信予定日時が正確に表示されているか確認
- [ ] DB ロック時の リトライが正常に動作しているか確認（高負荷テスト）

---

**修正者**: mayuneco(mayunya)
**修正日時**: 2025-12-24
**ステータス**: ✅ 実装完了、テスト待機
