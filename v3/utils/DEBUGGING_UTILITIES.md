# デバッグ用ユーティリティ スクリプト集

v3 では、デバッグ・検証・分析用のスクリプトを `v3/utils/` ディレクトリ配下でカテゴリ別に管理しています。

## ディレクトリ構成

```
v3/utils/
├── database/                               # DB操作・検証用スクリプト
│   ├── reset_post_flag.py                 # 投稿フラグリセット
│   ├── restore_db_from_backup.py          # DB復元
│   ├── check_db.py                        # DB内容確認
│   ├── verify_db_schema.py                # スキーマ検証
│   ├── check_db_state.py                  # DB全体の状態確認
│   ├── youtube_duplicate_manager.py       # YouTube重複クリーンアップ（ユーティリティ）
│   └── youtube_dedup_priority.py          # YouTube優先度ロジック（内部モジュール）
├── cache/                                  # キャッシュ管理用スクリプト
│   ├── build_video_cache.py               # キャッシュ構築
│   └── check_cache_file.py                # キャッシュ確認
├── classification/                         # 分類・検証用スクリプト
│   ├── check_archive_classification.py    # アーカイブ分類統計
│   ├── apply_classifications.py           # 分類結果を DB に適用
│   ├── apply_classification_to_production_db.py  # 本番 DB に分類適用
│   └── check_classification_detailed.py   # 分類結果の詳細確認
└── analysis/                               # API・環境検証スクリプト
    ├── calculate_api_quota.py             # API クォータ計算
    ├── inspect_broadcast_type.py          # ブロードキャストタイプ検査
    ├── inspect_video_api_response.py      # YouTube API レスポンス検査
    └── check_env_and_cache.py             # 環境・キャッシュ整合性チェック
```

---

# デバッグ用ユーティリティ: reset_post_flag.py

## 概要
`reset_post_flag.py` は、データベース内の投稿済みフラグ (`posted_to_bluesky`) と投稿日時 (`posted_at`) を  \
リセットするためのデバッグ用スクリプトです。

## 使用方法

### 単一の動画をリセット
```bash
python reset_post_flag.py <video_id>
```

### 複数の動画をリセット
```bash
python reset_post_flag.py <video_id1> <video_id2> ...
```

### 全ての動画をリセット
```bash
python reset_post_flag.py --all
```

## 注意事項
- **アプリケーション起動中に実行しないこと**: データベースがロックされる可能性があります。
- **バックアップを取ることを推奨**: 実行前にデータベースのバックアップを作成してください。
- **デバッグ用途のみ**: 本スクリプトはデバッグ目的で使用されるべきであり、本番環境での使用は推奨されません。

### ファイルの場所
- スクリプトの場所: `v3/utils/database/reset_post_flag.py`

---

## デバッグ用ユーティリティ: restore_db_from_backup.py

### 概要
`restore_db_from_backup.py` は、データベースをバックアップファイルから復元するためのデバッグ用スクリプトです。

### 使用方法

#### バックアップから復元
```bash
python restore_db_from_backup.py
```

### 注意事項
- **バックアップファイルの存在を確認**: スクリプト実行前に、指定されたバックアップファイルが存在することを確認してください。
- **デバッグ用途のみ**: 本スクリプトはデバッグ目的で使用されるべきであり、本番環境での使用は推奨されません。

### ファイルの場所
- スクリプトの場所: `v3/utils/database/restore_db_from_backup.py`

---

## デバッグ用ユーティリティ: build_video_cache.py

### 概要
- `build_video_cache.py` は、本番データベース内の全YouTube動画をYouTube APIを利用してキャッシュに保存するスクリプトです。
- API クォータの節約と初期キャッシュの構築に使用されます。

### 使用方法

#### キャッシュを構築・更新
```bash
python v3/utils/build_video_cache.py
```

### 機能
- 本番DB (`v3/data/video_list.db`) から全YouTube動画を取得
- YouTube APIプラグインを使用して動画詳細情報を取得
- 50件ずつバッチ処理でキャッシュを構築
- API コスト（ユニット数）を表示
- キャッシュを `v3/data/youtube_video_detail_cache.json` に保存

### 実行結果例
```
================================================================================
本番 DB の動画詳細をキャッシュに保存
================================================================================
対象: 150 件の YouTube 動画

✅ YouTube API プラグインが利用可能です

🔄 バッチ取得でキャッシュを構築中...

バッチ 1: 50 件を処理 (1-50/150)
  API コスト: 50 ユニット

... (省略)

✅ キャッシュ構築完了
  キャッシュサイズ: 150 件
  合計 API コスト: 150 ユニット

💾 キャッシュをファイルに保存中...
✅ キャッシュを保存しました
   ファイル: v3/data/youtube_video_detail_cache.json
   ファイルサイズ: 250,456 bytes (244.4 KB)

次回以降、このキャッシュが利用されます！
API コスト削減: 150 件 × 1 ユニット = 150 ユニット節約可能 ✅
```

### 注意事項
- **YouTube APIキーが必須**: `v2/settings.env` に `YOUTUBE_API_KEY` を設定してください。
- **APIクォータの確認**: 実行前にYouTube API のクォータを確認してください。
- **アプリケーション起動中に実行しないこと**: データベースがロックされる可能性があります。
- **デバッグ用途**: 本スクリプトはキャッシュ初期化・テスト目的で使用してください。

### ファイルの場所
- スクリプトの場所: `v3/utils/cache/build_video_cache.py`

---

# DB操作・検証用スクリプト（`database/` カテゴリ）

## 1. reset_post_flag.py

### 概要
データベース内の投稿済みフラグ (`posted_to_bluesky`) と投稿日時 (`posted_at`) をリセットするデバッグ用スクリプト。

### 使用方法

#### 単一の動画をリセット
```bash
python v3/utils/database/reset_post_flag.py <video_id>
```

#### 複数の動画をリセット
```bash
python v3/utils/database/reset_post_flag.py <video_id1> <video_id2> ...
```

#### 全ての動画をリセット
```bash
python v3/utils/database/reset_post_flag.py --all
```

### 機能
- 指定した動画の投稿フラグをリセット（1 → 0）
- 投稿日時をクリア（NULL に設定）
- 複数動画の一括リセット対応
- 全動画の一括リセット対応（確認プロンプト付き）
- 実行前に現在のステータスを表示

### 注意事項
- **アプリケーション起動中に実行しないこと**: データベースがロックされる可能性があります。
- **バックアップを取ることを推奨**: 実行前にデータベースのバックアップを作成してください。
- **デバッグ用途のみ**: 本スクリプトはデバッグ目的で使用されるべきであり、本番環境での使用は推奨されません。

### ファイルの場所
- スクリプトの場所: `v3/utils/database/reset_post_flag.py`

---

## 2. restore_db_from_backup.py

### 概要
データベースをバックアップファイルから復元するためのデバッグ用スクリプト。

### 使用方法

#### バックアップから復元
```bash
python v3/utils/database/restore_db_from_backup.py
```

### 出力例
```
✅ バックアップから復元しました
   Source: v3/data/video_list.backup_20251218_104027.db
   Dest:   v3/data/video_list.db
```

### 注意事項
- **バックアップファイルの存在を確認**: スクリプト実行前に、指定されたバックアップファイルが存在することを確認してください。
- **デバッグ用途のみ**: 本スクリプトはデバッグ目的で使用されるべきであり、本番環境での使用は推奨されません。

### ファイルの場所
- スクリプトの場所: `v3/utils/database/restore_db_from_backup.py`

---

# キャッシュ管理用スクリプト（`cache/` カテゴリ）

## 1. build_video_cache.py

### 概要
- 本番データベース内の全YouTube動画をYouTube APIを利用してキャッシュに保存するスクリプト。
- API クォータの節約と初期キャッシュの構築に使用されます。

### 使用方法

#### キャッシュを構築・更新
```bash
python v3/utils/cache/build_video_cache.py
```

### 機能
- 本番DB (`v3/data/video_list.db`) から全YouTube動画を取得
- YouTube APIプラグインを使用して動画詳細情報を取得
- 50件ずつバッチ処理でキャッシュを構築
- API コスト（ユニット数）を表示
- キャッシュを `v3/data/youtube_video_detail_cache.json` に保存

### 実行結果例
```
================================================================================
本番 DB の動画詳細をキャッシュに保存
================================================================================
対象: 150 件の YouTube 動画

✅ YouTube API プラグインが利用可能です

🔄 バッチ取得でキャッシュを構築中...

バッチ 1: 50 件を処理 (1-50/150)
  API コスト: 50 ユニット

... (省略)

✅ キャッシュ構築完了
  キャッシュサイズ: 150 件
  合計 API コスト: 150 ユニット

💾 キャッシュをファイルに保存中...
✅ キャッシュを保存しました
   ファイル: v3/data/youtube_video_detail_cache.json
   ファイルサイズ: 250,456 bytes (244.4 KB)

次回以降、このキャッシュが利用されます！
API コスト削減: 150 件 × 1 ユニット = 150 ユニット節約可能 ✅
```

### 注意事項
- **YouTube APIキーが必須**: `v2/settings.env` に `YOUTUBE_API_KEY` を設定してください。
- **APIクォータの確認**: 実行前にYouTube API のクォータを確認してください。
- **アプリケーション起動中に実行しないこと**: データベースがロックされる可能性があります。
- **デバッグ用途**: 本スクリプトはキャッシュ初期化・テスト目的で使用してください。

### ファイルの場所
- スクリプトの場所: `v3/utils/cache/build_video_cache.py`

### 概要
Niconico 動画をデータベースから取得して確認するスクリプト。

### 使用方法
```bash
python v3/utils/database/check_db.py
```

### 出力例
```
Video ID: sm12345678
Title: ニコニコ動画のサンプル
Channel Name: 投稿者名
Source: niconico
```

---

## 2. verify_db_schema.py

### 概要
データベーススキーマを検証し、テーブルカラムと分類結果の分布を確認するスクリプト。

### 使用方法
```bash
python v3/utils/database/verify_db_schema.py
```

### 出力内容
- **スキーマ表示**: 全カラムの型と制約条件
- **分類タイプ分布**: `classification_type` の分布
- **サンプルデータ**: 先頭5件の動画情報

### 確認項目
- テーブル構造が最新か
- 新しい分類タイプが追加されているか
- NULL値が期待通りか

---

## 3. youtube_duplicate_manager.py

### 概要
- YouTube重複登録動画の管理・整理ユーティリティモジュール。
- 同じタイトル+チャンネル名で複数登録されている動画を検出し、優先度ロジックに基づいて保持する動画を決定します。

**機能：**
- `check_duplicate_videos()` - 重複登録動画をチェック・表示
- `cleanup_youtube_duplicates_with_priority()` - 重複動画をクリーンアップ（優先度ロジック適用）

### 使用方法

#### 重複動画をチェック（表示のみ）
```bash
python v3/utils/database/youtube_duplicate_manager.py check
```

#### 重複動画をクリーンアップ
```bash
python v3/utils/database/youtube_duplicate_manager.py cleanup
```

#### 両方を実行
```bash
python v3/utils/database/youtube_duplicate_manager.py
```

### 優先度ロジック

動画の優先度は以下の順序で決定されます（高い順）：

1. **アーカイブ**（`content_type='archive'` または `live_status='completed'`）- 最も優先度が高い
2. **ライブ**（`content_type='live'` または `live_status='live'/'upcoming'`）
3. **プレミア公開**（`is_premiere=1` かつ開始予定時刻から10分以内）
4. **通常動画**（`content_type='video'`）- 最も優先度が低い

### 出力例

**チェック結果：**
```
=== YouTubeの重複登録されている動画 ===

タイトル: 新作動画を作成しました！
  登録数: 3
  video_ids: dQw4w9WgXcQ,abc123def456,xyz789
  content_types: video,live,archive
  live_statuses: none,live,completed
  premieres: 0,0,0
```

**クリーンアップ結果：**
```
【重複グループ】
  タイトル: 新作動画を作成しました！
  チャンネル: My Channel
  登録数: 3

  動画の優先度:
    ID=  1, video_id=dQw4w9WgXcQ, type=video    , live_status=none      , premiere=0, priority=1
    ID=  2, video_id=abc123def456, type=live     , live_status=live      , premiere=0, priority=3
    ID=  3, video_id=xyz789, type=archive  , live_status=completed , premiere=0, priority=4

  ✅ 保持: ID=  3, video_id=xyz789 (priority=4)
  ❌ 削除: ID=  1, video_id=dQw4w9WgXcQ (priority=1)
     📌 deleted_videos.json に登録
  ❌ 削除: ID=  2, video_id=abc123def456 (priority=3)
     📌 deleted_videos.json に登録

=== 結果 ===
削除した動画: 2件
deleted_videos.json に登録: 2件
クリーンアップ対象グループ: 1グループ
```

### 特徴

- ✅ **削除時に `deleted_videos.json` に自動登録** - 除外動画リストに自動追加される
- ✅ **優先度に基づいた自動選択** - 最も価値のある動画を保持
- ✅ **Pythonモジュール化** - 他のコードから `from youtube_duplicate_manager import ...` で利用可能
- ✅ **任意のディレクトリから実行可能** - パスを自動解決

### 注意事項

- **アプリケーション非起動時に実行**: DB ロックを回避するため、アプリケーション起動中には実行しないでください。
- **バックアップ推奨**: 削除操作を伴うため、実行前にデータベースのバックアップを作成してください。
- **デバッグ用途**: 過去に登録された重複を整理するためのメンテナンスツールです。RSS取得時の新規重複チェックは `database.py` の `insert_video()` で自動的に行われます。

### ファイルの場所
- スクリプト: `v3/utils/database/youtube_duplicate_manager.py`
- 内部依存: `v3/utils/database/youtube_dedup_priority.py`

---

## 4. youtube_dedup_priority.py

### 概要
- YouTube動画の優先度ロジックを計算する内部モジュール。
- `database.py` の RSS新規登録時チェック と `youtube_duplicate_manager.py` の重複クリーンアップで使用されます。

**提供関数：**
- `get_video_priority(video)` - 動画の優先度を計算（タプル形式）
- `should_keep_video(video, existing_videos)` - 新規動画を登録すべきか判定
- `select_best_video(videos)` - 複数動画から最優先を選択

### 役割

| 処理 | 用途 | タイミング |
|:--|:--|:--|
| **新規登録時チェック（`database.insert_video`）** | RSS取得時に重複を防止 | リアルタイム |
| **重複クリーンアップ（`youtube_duplicate_manager`）** | 過去の重複を整理 | 定期メンテナンス |

### 優先度計算ロジック

```python
# 優先度が大きいほど、より重要な動画
優先度 4: アーカイブ（content_type='archive' または live_status='completed'）
優先度 3: ライブ（content_type='live' または live_status='live'/'upcoming'）
優先度 3: プレミア公開（is_premiere=1 かつ開始予定時刻から10分以内）
優先度 1: 通常動画（content_type='video'）
```

### 使用例（Pythonコード）

```python
from utils.database.youtube_dedup_priority import get_video_priority, should_keep_video

# 新しい動画の優先度を計算
new_video = {
    "video_id": "abc123",
    "content_type": "archive",
    "live_status": "completed",
    "is_premiere": 0,
    "published_at": "2025-12-18T10:00:00"
}
priority = get_video_priority(new_video)
print(priority)  # (4, 'archive', 'abc123')

# 既存の動画と比較
existing_videos = [
    {"video_id": "xyz789", "content_type": "video", "live_status": None, ...}
]
should_keep = should_keep_video(new_video, existing_videos)
print(should_keep)  # True（新動画の優先度が高い）
```

### ファイルの場所
- モジュール: `v3/utils/database/youtube_dedup_priority.py`
- 依存される場所:
  - `v3/database.py`（RSS新規登録時）
  - `v3/utils/database/youtube_duplicate_manager.py`（重複クリーンアップ時）

---

## 5. check_db_state.py

## 3. check_db_state.py

### 概要
データベース全体の状態を確認するスクリプト。動画総数、プラットフォーム別統計、NULL値などを表示。

### 使用方法
```bash
python v3/utils/database/check_db_state.py
```

### 出力例
```
Total videos in DB: 250

By source:
  youtube: 200
  niconico: 50

YouTube video samples:
  dQw4w9WgXcQ | YouTube Video Title | youtube | video
  ...

Videos with NULL source:
  Count: 0
```

---

# キャッシュ管理用スクリプト（`cache/` カテゴリ）

## 1. check_cache_file.py

### 概要
- YouTube API キャッシュファイルの状態を確認するスクリプト。
- ファイルサイズ、キャッシュ件数、サンプルデータを表示。

### 使用方法
```bash
python v3/utils/cache/check_cache_file.py
```

### 出力例
```
================================================================================
キャッシュファイル確認
================================================================================
✅ ファイルが存在します: .../v3/data/youtube_video_detail_cache.json
   ファイルサイズ: 1,234,567 bytes (1205.6 KB)

📊 キャッシュ統計:
   キャッシュ件数: 250 件

📋 サンプル（最初の3件）:
   1. dQw4w9WgXcQ
      タイトル: YouTube Video Title
      キャッシュ時刻: 1702900000
   ...
```

### 確認内容
- キャッシュファイルが正常に機能しているか
- キャッシュサイズが適切か
- キャッシュが最新データを含んでいるか

---

# 分類関連スクリプト（`classification/` カテゴリ）

## 1. check_archive_classification.py

### 概要
- 本番DB内の動画分類結果をサマリー表示するスクリプト。
- コンテンツタイプ、ライブステータス、プレミア公開フラグ別に統計を表示。

### 使用方法
```bash
python v3/utils/classification/check_archive_classification.py
```

### 出力例
```
================================================================================
本番 DB の分類結果サマリー
================================================================================

📊 コンテンツタイプ別集計:
  video: 180 件
  live: 50 件
  archive: 20 件

📊 ライブステータス別集計:
  (通常動画): 180 件
  upcoming: 10 件
  live: 30 件
  completed: 30 件

📊 プレミア公開フラグ別集計:
  通常配信: 240 件
  プレミア公開: 10 件

🎬 Archive に分類された動画:
  1. dQw4w9WgXcQ | Archive Video Title | status=completed | ✗
  ...

🎬 Live に分類された動画（最新5件）:
  1. abcdefghijk | Live Video Title | status=live | ✓プレミア
  ...
```

### 確認項目
- 各分類タイプの動画数が期待値か
- プレミア公開動画の数が正確か
- ライブステータスの分布が正常か

---

# API分析用スクリプト（`analysis/` カテゴリ）

## 1. calculate_api_quota.py

### 概要
YouTube Data API のクォータ使用量を計算し、安全性と推奨実行タイミングを表示するスクリプト。

### 使用方法
```bash
python v3/utils/analysis/calculate_api_quota.py
```

### 出力例
```
================================================================================
📊 YouTube Data API クォータ計算
================================================================================

【DB 統計情報】

✅ 全動画数: 250 件
✅ YouTube 動画: 200 件

【プラットフォーム別】

  youtube       200 件 ( 80.0%)
  niconico       50 件 ( 20.0%)

【API コスト計算】

videos.list（動画詳細取得）:
  YouTube 動画数: 200 件
  1 動画 = 1 ユニット
  小計: 200 ユニット

channels.list（チャンネルID解決）:
  初回アクセス時のみ: 1 ユニット
  小計: 1 ユニット

【合計 API コスト】

  videos.list: 200 ユニット
  channels.list: 1 ユニット
  ────────────────────
  合計: 201 ユニット

【日次クォータ（10,000ユニット）との比較】

  使用量: 201 ユニット
  利用可能: 10000 ユニット
  残余: 9799 ユニット
  使用率: 2.01%

✅ クォータ内！【安全】
   9799 ユニットの余裕があります

【推奨実行タイミング】

✅ 【推奨】 毎日実行可能
   クォータの 50% 以下のため、安全に毎日実行できます

【API 効率分析】

効率: 200 動画 / 201 ユニット = 0.99 動画/ユニット
```

### 確認内容
- YouTube API のクォータ使用量
- 安全な実行頻度
- キャッシュ構築の可否判定

---

## 2. inspect_broadcast_type.py

### 概要
- YouTube APIレスポンスの `liveBroadcastContent` と `liveStreamingDetails` を確認し、  \
分類ロジックの入力値を検証するスクリプト。

### 使用方法
```bash
python v3/utils/analysis/inspect_broadcast_type.py
```

### 出力例
```
確認対象: 10 件
================================================================================
✅ YouTube API プラグインが利用可能です

dQw4w9WgXcQ:
  liveBroadcastContent: none
  uploadStatus: processed
  liveStreamingDetails: False

abcdefghijk:
  liveBroadcastContent: live
  uploadStatus: processed
  liveStreamingDetails: True
    - actualEndTime: False
    - actualStartTime: True
    - scheduledStartTime: True
```

### 確認項目
- 各動画の API レスポンス形式
- 分類ロジックの入力値が正確か
- ブロードキャストタイプと時間情報の関連性

---

# 実行方法の一覧

| カテゴリ | スクリプト | 目的 |
|:--|:--|:--|
| **DB操作** | `database/reset_post_flag.py` | 投稿フラグのリセット |
| | `database/restore_db_from_backup.py` | DB のバックアップ復元 |
| | `database/check_db.py` | Niconico 動画確認 |
| | `database/verify_db_schema.py` | スキーマ検証 |
| | `database/check_db_state.py` | DB全体の状態確認 |
| | `database/youtube_duplicate_manager.py` | YouTube重複クリーンアップ（ユーティリティ） |
| | `database/youtube_dedup_priority.py` | YouTube優先度ロジック（内部モジュール） |
| **キャッシュ** | `cache/build_video_cache.py` | キャッシュの初期化・再構築 |
| | `cache/check_cache_file.py` | キャッシュファイル確認 |
| **分類・検証** | `classification/check_archive_classification.py` | アーカイブ分類統計表示 |
| | `classification/apply_classifications.py` | 分類結果を DB に適用 |
| | `classification/apply_classification_to_production_db.py` | 本番 DB に分類を適用 |
| | `classification/check_classification_detailed.py` | 分類結果の詳細確認 |
| **分析・検証** | `analysis/calculate_api_quota.py` | API クォータ計算 |
| | `analysis/inspect_broadcast_type.py` | API レスポンス検証 |
| | `analysis/inspect_video_api_response.py` | YouTube API レスポンス詳細検査 |
| | `analysis/check_env_and_cache.py` | 環境・キャッシュ整合性チェック |

---

# 注意事項（全スクリプト共通）

- ✅ **アプリケーション非起動時に実行**: DB ロックを回避するため、v3アプリケーション起動中には実行しないでください。
- ✅ **バックアップを推奨**: DB を変更するスクリプト（`reset_post_flag.py` など）は、実行前にバックアップを作成してください。
- ✅ **デバッグ用途**: 本スクリプトはすべてデバッグ・検証目的で設計されています。本番環境での定期実行は推奨されません。
- ✅ **環境変数設定**: `v2/settings.env` に必要な設定（YouTube API キーなど）があることを確認してください。

---

# 分類検証スクリプト（`classification/` カテゴリ）

## 3. apply_classifications.py

### 概要
YouTube Video Intelligence API (ベータ版) の分類結果を実際にデータベースに適用するスクリプト。

### 使用方法
```bash
python v3/utils/classification/apply_classifications.py
```

### 動作
- `youtube_video_detail_cache.json` から動画情報を取得
- 既存の `classification_type` が `unknown` の動画に対して、新しい分類値を適用
- DB を更新

### 注意事項
- **キャッシュファイルが必須**: 事前に `build_video_cache.py` でキャッシュを構築しておいてください。
- **バックアップ推奨**: DB 更新前にバックアップを取ってください。

---

## 4. apply_classification_to_production_db.py

### 概要
テスト用 DB での分類結果を本番 DB に適用するスクリプト。

### 使用方法
```bash
python v3/utils/classification/apply_classification_to_production_db.py
```

### 動作
- テスト DB から分類情報を取得
- 本番 DB にマップして適用

### 注意事項
- **テスト DB と本番 DB の両方が必要**: 事前に両方の DB を準備しておいてください。
- **本番環境への影響**: このスクリプトは本番 DB を直接変更するため、実行前に十分な検証を行ってください。

---

## 5. check_classification_detailed.py

### 概要
分類結果の詳細情報を表示するスクリプト。各動画の分類値と分類根拠を確認できます。

### 使用方法
```bash
python v3/utils/classification/check_classification_detailed.py
```

### 出力例
```
================================================================================
分類結果 - 詳細情報
================================================================================

Total Videos: 100

Classification Type Distribution:
- video: 85
- live: 10
- archive: 5
- none: 0
- unknown: 0
```

### 確認項目
- 各動画の分類タイプ
- API の信頼度スコア
- 分類の偏り（バイアスチェック）

---

# 分析検証スクリプト（`analysis/` カテゴリ - 拡張）

## 6. inspect_video_api_response.py

### 概要
YouTube Data API のレスポンス全体を検査し、API の返却値形式と階層構造を確認するスクリプト。

### 使用方法
```bash
python v3/utils/analysis/inspect_video_api_response.py
```

### 確認項目
- API レスポンス構造の完全性
- 各フィールドのデータ形式
- ネストされたオブジェクトの存在確認

---

## 7. check_env_and_cache.py

### 概要
環境変数とキャッシュファイルの整合性をチェックするスクリプト。API キー設定やキャッシュの有効性を確認できます。

### 使用方法
```bash
python v3/utils/analysis/check_env_and_cache.py
```

### チェック内容
-  `settings.env` の存在確認
-  YouTube API キーの設定状況
-  キャッシュファイル (`youtube_video_detail_cache.json`) の存在と形式
-  キャッシュの有効期限チェック
-  DB との整合性確認

### 確認項目
- 環境設定の完全性
- キャッシュと DB の一貫性
- API 呼び出しの準備状況
