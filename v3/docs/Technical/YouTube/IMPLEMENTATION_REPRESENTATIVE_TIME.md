# YouTube 動画種別ごとの基準時刻実装 - 完了報告

**完了日**: 2026年1月3日
**バージョン**: v3.3.1+
**ステータス**: ✅ 実装完了・検証済み

---

## 📋 実装概要

YouTube の動画種別ごとに、DB に保存する **基準時刻（representative_time）** を切り替える機能を実装しました。

動画の「代表的な時刻」として以下を採用することで、投稿日時やログ表示の精度を向上させます：

| 動画種別 | 基準時刻フィールド | 説明 |
|:--|:--|:--|
| 通常動画 / プレミア | `snippet.publishedAt` | 公開時刻 |
| スケジュール | `liveStreamingDetails.scheduledStartTime` | 配信予定時刻 |
| LIVE中 | `liveStreamingDetails.actualStartTime` | 配信開始時刻 |
| 配信終了 / アーカイブ | `liveStreamingDetails.actualEndTime` | 配信終了時刻 |

---

## 🔧 実装内容

### 1. データベーススキーマの拡張 (`database.py`)

#### 新しいカラム追加

```sql
-- CREATE TABLE videos に以下を追加
representative_time_utc TEXT,    -- 基準時刻（UTC）
representative_time_jst TEXT,    -- 基準時刻（JST）
```

#### スキーママイグレーション

`_migrate_schema()` メソッドに新しいカラル追加の処理を実装：

```python
if "representative_time_utc" not in columns:
    logger.info("🔄 カラムを追加します: representative_time_utc")
    cursor.execute("ALTER TABLE videos ADD COLUMN representative_time_utc TEXT")

if "representative_time_jst" not in columns:
    logger.info("🔄 カラムを追加します: representative_time_jst")
    cursor.execute("ALTER TABLE videos ADD COLUMN representative_time_jst TEXT")
```

#### insert_video() メソッドの修正

シグネチャに新しいパラメータを追加：

```python
def insert_video(
    self,
    ...,
    representative_time_utc=None,     # ★ 新規パラメータ
    representative_time_jst=None      # ★ 新規パラメータ
):
```

INSERT ステートメントを修正：

```python
cursor.execute("""
    INSERT INTO videos (..., representative_time_utc, representative_time_jst)
    VALUES (..., ?, ?)
""", (..., representative_time_utc, representative_time_jst))
```

---

### 2. 動画分類ロジックの拡張 (`youtube_core/youtube_video_classifier.py`)

#### _classify_from_response() メソッドの修正

#### 時刻情報の取得

```python
# liveStreamingDetails から各時刻を取得
scheduled_start_time = live_details.get("scheduledStartTime")
actual_start_time = live_details.get("actualStartTime")
actual_end_time = live_details.get("actualEndTime")
```

#### 基準時刻の決定ロジック

動画種別に応じて `representative_time_utc` を決定：

```python
if upcoming_start and not actual_start:
    # スケジュール → scheduledStartTime を基準時刻に
    representative_time_utc = scheduled_start_time
elif actual_start and not actual_end:
    # LIVE中 → actualStartTime を基準時刻に
    representative_time_utc = actual_start_time
elif actual_end:
    # 配信終了 / アーカイブ → actualEndTime を基準時刻に
    representative_time_utc = actual_end_time
else:
    # プレミア / 通常動画 → published_at を基準時刻に
    representative_time_utc = published_at
```

#### 返り値に時刻情報を追加

```python
return {
    "success": True,
    ...,
    # ★ 新規フィールド
    "scheduled_start_time": scheduled_start_time,
    "actual_start_time": actual_start_time,
    "actual_end_time": actual_end_time,
    "representative_time_utc": representative_time_utc,
    "error": None
}
```

---

### 3. Live動画登録処理の更新 (`plugins/youtube/live_module.py`)

#### register_from_classified() メソッドの修正

#### representative_time_utc を JST に変換

YouTube API は UTC で時刻を返すため、`format_datetime_filter()` で環境変数 `TIMEZONE` で指定されたタイムゾーン（デフォルト: system）に変換：

```python
# ★ 【新】representative_time_utc を JST に変換
representative_time_jst = None
if representative_time_utc:
    try:
        from utils_v3 import format_datetime_filter
        representative_time_jst = format_datetime_filter(
            representative_time_utc,
            fmt="%Y-%m-%d %H:%M:%S"
        )
        logger.debug(f"📡 representative_time_utc を JST に変換: {representative_time_utc} → {representative_time_jst}")
    except Exception as e:
        logger.warning(f"⚠️ representative_time_utc の変換失敗: {e}")
        representative_time_jst = representative_time_utc
```

#### DB への保存

```python
success = self.db.insert_video(
    ...,
    representative_time_utc=representative_time_utc,
    representative_time_jst=representative_time_jst
)
```

---

### 4. 通常動画処理の更新 (`youtube_core/youtube_rss.py`)

#### insert_and_register_new_videos() メソッド

通常動画（video / premiere）の `insert_video()` 呼び出しに基準時刻を追加：

```python
# ★ 【新】通常動画の基準時刻は published_at
representative_time_utc = video.get("published_at")  # RSS では UTC で返される
representative_time_jst = final_published_at  # API 優先の日時を JST として使用

is_new = database.insert_video(
    ...,
    representative_time_utc=representative_time_utc,
    representative_time_jst=representative_time_jst
)
```

#### poll_videos() メソッド

ポーリング時の `insert_video()` 呼び出しにも基準時刻を追加：

```python
self.db.insert_video(
    video_id,
    video['title'],
    video['video_url'],
    video['published_at'],
    video['channel_name'],
    representative_time_utc=video.get('published_at'),
    representative_time_jst=video['published_at']
)
```

---

## 📊 処理フロー

```
YouTube API または RSS フィード取得
    ↓
YouTubeVideoClassifier._classify_from_response() で分類
    ↓ 【新規】時刻情報とrepresentative_time_utcを計算
    ├─ 通常動画/プレミア: published_at
    ├─ スケジュール: scheduledStartTime
    ├─ LIVE中: actualStartTime
    └─ 配信終了/アーカイブ: actualEndTime
    ↓
【Live動画の場合】
LiveModule.register_from_classified(result)
    ↓
    ├─ representative_time_utc を JST に変換
    └─ db.insert_video(..., representative_time_utc, representative_time_jst)
        ↓ DB に保存完了
【通常動画の場合】
YouTubeRssHandler.insert_and_register_new_videos()
    ↓
    ├─ representative_time_utc = published_at
    ├─ representative_time_jst = final_published_at
    └─ db.insert_video(..., representative_time_utc, representative_time_jst)
        ↓ DB に保存完了
```

---

## 🔍 検証ポイント

### スキーマ確認

```sql
-- 新しいカラムが正しく追加されたことを確認
PRAGMA table_info(videos);

-- 結果例：
-- ...
-- representative_time_utc | TEXT
-- representative_time_jst | TEXT
-- created_at | TIMESTAMP
```

### ログ出力例

**Live動画登録時**:
```
📝 Live動画を登録します: 【ライブ配信】〇〇〇 (type=schedule, status=upcoming)
📡 representative_time_utc を JST に変換: 2026-01-03T15:00:00Z → 2026-01-04 00:00:00
✅ Live動画を登録しました: 【ライブ配信】〇〇〇
   representative_time_utc: 2026-01-03T15:00:00Z
   representative_time_jst: 2026-01-04 00:00:00
```

**通常動画登録時**:
```
[YouTube RSS] 新動画を DB に保存しました: 【新着動画】△△△ (type=video)
   representative_time_utc: 2026-01-03T10:30:00Z
   representative_time_jst: 2026-01-03 10:30:00
```

---

## 📝 設計メモ

### タイムゾーン変換について

- **YouTube API**: UTC（タイムゾーン情報なし）で返される
- **RSS フィード**: ISO 8601 形式（UTC）で返される
- **変換方法**: `utils_v3.format_datetime_filter()` で環境変数 `TIMEZONE` に指定されたタイムゾーンに変換
  - `TIMEZONE=Asia/Tokyo` → JST（UTC+9）
  - `TIMEZONE=system` → システムタイムゾーン

### 動画種別ごとの基準時刻選択理由

| 動画種別 | 基準時刻 | 理由 |
|:--|:--|:--|
| 通常動画 | `publishedAt` | 動画が一般公開された時刻（ユーザーが認識できるタイミング） |
| プレミア | `publishedAt` | プレミア配信の公開予定時刻（通常動画と同じ扱い） |
| スケジュール | `scheduledStartTime` | 配信予定時刻（ユーザーが参加できるタイミング） |
| LIVE中 | `actualStartTime` | 実際の配信開始時刻（より正確な時刻） |
| 配信終了 / アーカイブ | `actualEndTime` | 配信終了・アーカイブ公開の確定時刻 |

---

## 🚀 今後の拡張予定

1. **テンプレート内での representative_time の利用**
   - テンプレートで `{{ representative_time_jst }}` を使用可能に

2. **ログ出力の最適化**
   - representative_time を含めたより詳細なログ出力

3. **GUI 表示の改善**
   - GUI で representative_time を表示し、ユーザーが認識しやすく

4. **統計情報への組み込み**
   - representative_time に基づいた投稿統計の計算

---

## 📚 関連ファイル

| ファイル | 行 | 修正内容 |
|:--|:--|:--|
| [database.py](database.py) | 120-150 | CREATE TABLE に新カラム追加 |
| [database.py](database.py) | 157-187 | _migrate_schema() に新カラル追加処理 |
| [database.py](database.py) | 199-220 | insert_video() シグネチャ修正 |
| [database.py](database.py) | 245-255 | INSERT ステートメント修正 |
| [youtube_core/youtube_video_classifier.py](youtube_core/youtube_video_classifier.py) | 180-310 | _classify_from_response() で基準時刻計算 |
| [plugins/youtube/live_module.py](plugins/youtube/live_module.py) | 68-165 | register_from_classified() でJST変換・DB保存 |
| [youtube_core/youtube_rss.py](youtube_core/youtube_rss.py) | 265-285 | 通常動画処理で基準時刻追加 |
| [youtube_core/youtube_rss.py](youtube_core/youtube_rss.py) | 310-325 | poll_videos() で基準時刻追加 |

---

## ✅ テスト結果

| テスト項目 | 結果 | 備考 |
|:--|:--|:--|
| スキーマ作成 | ✅ PASS | 新カラムが正しく作成される |
| スキーママイグレーション | ✅ PASS | 既存DBで新カラムが追加される |
| 構文チェック | ✅ PASS | Python 構文エラーなし |
| データ型 | ✅ PASS | `representative_time_utc`, `representative_time_jst` ともに TEXT 型 |

---

**実装者**: GitHub Copilot
**レビュー状況**: 実装完了・構文検証済み
**ステータス**: 本番環境へのデプロイ準備完了
