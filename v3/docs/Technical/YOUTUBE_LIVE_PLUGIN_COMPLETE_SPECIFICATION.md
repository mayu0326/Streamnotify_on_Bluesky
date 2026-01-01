# YouTubeLive プラグイン - 完全実装仕様書

**バージョン**: v0.3.0（4層分割版）
**対象バージョン**: v3.1.0+
**最終更新**: 2025-12-30（4層構造の責務統合完了）
**ステータス**: ✅ 4層分割完了・キャッシュ戦略統合完了

---

## 📖 目次

1. [概要](#概要)
2. [4層モジュール構造](#4層モジュール構造)
3. [YouTubeLiveClassifier（分類層）](#youtubelive-classifier分類層)
4. [YouTubeLiveStore（ストレージ層）](#youtubelive-storeストレージ層)
5. [YouTubeLivePoller（ポーリング層）](#youtubelive-pollerポーリング層)
6. [YouTubeLiveAutoPoster（自動投稿層）](#youtubeliveautopostter自動投稿層)
7. [キャッシュシステムの仕様](#キャッシュシステムの仕様)
8. [分類ロジック（ライブ/アーカイブ判定）](#分類ロジックライブアーカイブ判定)
9. [ポーリングフロー](#ポーリングフロー)
10. [自動投稿メカニズム](#自動投稿メカニズム)
11. [状態遷移制御](#状態遷移制御)
12. [データベース統合](#データベース統合)
13. [エラーハンドリング](#エラーハンドリング)
14. [実装チェックリスト](#実装チェックリスト)

---

## 概要

### 🎯 目的

YouTubeLive プラグインは、YouTube の **ライブ配信（LIVE）** と **アーカイブ（Archive）** を自動判定し、以下の機能を提供します：

- ✅ RSS で登録された動画を API で判定（LIVE/Archive/通常動画）
- ✅ ライブ状態を定期ポーリング（upcoming → live → completed → archive の段階的追跡）
- ✅ 状態遷移を検出して Bluesky に自動投稿
- ✅ キャッシュを用いた API クォータの最適化
- ✅ APP_MODE に応じた柔軟な投稿制御（AUTOPOST/SELFPOST）

### 🏗️ 4層責務分担（新設計）

| レイヤー | クラス名 | 責務 |
|:--|:--|:--|
| **分類層** | YouTubeLiveClassifier | YouTube API データ → content_type/live_status の純粋分類 |
| **ストレージ層** | YouTubeLiveStore | DB・キャッシュの読み書き（ロジックなし） |
| **ポーリング層** | YouTubeLivePoller | 状態監視 + 遷移検出 + **キャッシュ戦略管理** |
| **自動投稿層** | YouTubeLiveAutoPoster | イベント処理 + 投稿判定（唯一の判定点） |

**補助コンポーネント**:
- **YouTubeAPIPlugin**: 4層が共有する YouTube Data API 連携
- **YouTubeLiveCache**: Poller と Store が共有するキャッシュ管理（JSON ファイル）
- **Database**: 最終的な永続化レイヤー（SQLite）

---

## 4層モジュール構造

### 処理フロー全体図

```
main_v3.py 起動
    ↓
YouTubeLivePlugin 初期化（またはプラグイン有効化）
    ↓
各レイヤーのインスタンス生成:
  - Classifier: API分類ロジック
  - Store: DB/キャッシュ操作
  - Poller: 状態監視＋キャッシュ戦略
  - AutoPoster: 自動投稿判定
    ↓
【初期化時】
_update_unclassified_videos()
  1. Store: DB から content_type="video" の動画を取得
  2. Poller: _get_video_detail_with_cache() でキャッシュ優先取得
  3. Classifier: API データから分類
  4. Store: DB を content_type/live_status で更新
  5. AutoPoster: 自動投稿判定 → 投稿実行
    ↓
【定期ポーリング（15分または5分間隔）】
poll_live_status()
  1. Store: DB から live_status='upcoming'/'live'/'completed' の動画を取得
  2. Poller: _get_video_detail_with_cache(video_id) で最新 details を取得（キャッシュ優先）
  3. Classifier: classify(details) で (new_content_type, new_live_status) を決定
  4. Poller: _detect_state_transitions(video, new_content_type, new_live_status) で遷移検出
  5. 遷移あり → Store: DB + キャッシュを更新
  6. AutoPoster: イベントリスナー経由で自動投稿判定
  7. Poller: _process_ended_cache_entries() で終了済み動画を処理
    ↓
【結果】
Bluesky に自動投稿
```

### 層間データフロー

```
外部 (DB/Cache/API)
    ↓
Store: DB から動画リスト取得
    ↓
Poller: _get_video_detail_with_cache(video_id)
  ├─ Cache Check → Hit: キャッシュ返却
  ├─ Miss: API 呼び出し
  └─ LIVE 状態 → 自動的に cache に登録
    ↓
Classifier: classify(details)
  └─ content_type/live_status 分類
    ↓
Poller: _detect_state_transitions(video, new_content_type, new_live_status)
  ├─ old_status (from DB) vs new_status (from API)
  └─ Compare → Transition Detected
    ↓
Store: (遷移あり時のみ)
  ├─ DB Update
  ├─ Cache Update
  └─ Cache Save
    ↓
AutoPoster: イベント受け取り
  ├─ _should_autopost_event() 判定
  └─ Plugin Manager → Bluesky 投稿
```

---

## YouTubeLiveClassifier（分類層）

YouTube API データから content_type と live_status を純粋に分類する責務

### クラス定義

```python
class YouTubeLiveClassifier:
    """YouTube API データから LIVE/Archive を分類する純粋層"""
```

### 主要メソッド

#### `classify(details: Dict) → (str, Optional[str], bool)`

**責務**: YouTube API 詳細情報 → (content_type, live_status, is_premiere)

**入力パラメータ**:
- `details` (Dict): YouTube API からの動画詳細情報
  - `liveStreamingDetails` (Optional[Dict]): ライブ配信関連情報
  - `status.uploadStatus` (str): "uploaded" など
  - `snippet.liveBroadcastContent` (str): "live"/"upcoming"/"none"

**出力**:
- `content_type` (str): "video" | "live" | "archive"
  - **"video"**: 通常の投稿動画（LIVE 属性なし）
  - **"live"**: LIVE 配信または LIVE アーカイブ
  - **"archive"**: LIVE 終了後のアーカイブ（終了確定）
- `live_status` (Optional[str]): None | "upcoming" | "live" | "completed"
  - **None**: 通常動画（content_type="video"）
  - **"upcoming"**: 放送予定中（LIVE 枠作成済み）
  - **"live"**: 放送中
  - **"completed"**: 放送終了（終了確定）
- `is_premiere` (bool): プレミア配信フラグ

**分類ロジック**:

| 条件 | content_type | live_status |
|:--|:--|:--|
| liveStreamingDetails なし | video | None |
| liveStreamingDetails あり + actualEndTime なし + actualStartTime なし | live | upcoming |
| liveStreamingDetails あり + actualStartTime あり + actualEndTime なし | live | live |
| liveStreamingDetails あり + actualEndTime あり | archive | completed |

---

## YouTubeLiveStore（ストレージ層）

DB とキャッシュの読み書き操作を提供（ロジック判定なし）

### クラス定義

```python
class YouTubeLiveStore:
    """DB・キャッシュの純粋データアクセス層"""
```

### 主要メソッド

#### DB 操作

**`get_unclassified_videos() → List[Dict]`**
- 目的: Poller による分類対象を取得
- 条件: content_type = "video"（未分類）
- フィルタ: 公開後 7 日以内

**`update_video_classification(video_id, content_type, live_status) → bool`**
- 目的: DB のコンテンツ種別とライブ状態を更新
- 条件: 入力値の妥当性チェック
- 副作用: キャッシュには更新しない（Poller が制御）

**`mark_as_posted(video_id) → bool`**
- 目的: 動画を投稿済みにマーク
- 用途: AutoPoster が投稿成功時に呼び出し

**`get_video_by_id(video_id) → Dict`**
- 目的: 指定動画の DB レコードを取得
- 返却: すべてのカラム（現在の状態を完全に知るため）

**`get_videos_by_live_status(status) → List[Dict]`**
- 目的: 特定の live_status の動画をすべて取得
- 引数: "upcoming" / "live" / "completed"

#### キャッシュ操作

**`add_live_video_to_cache(video_id, db_data, api_data) → bool`**
- 目的: LIVE 開始時にキャッシュに登録
- 用途: _get_video_detail_with_cache() がこの登録データを返す

**`update_cache_entry(video_id, api_data) → bool`**
- 目的: 既存キャッシュエントリを更新
- 条件: 状態変化検出時のみ呼び出し

**`get_live_videos_by_status(status) → List[Dict]`**
- 目的: キャッシュから指定状態の動画を取得

**`mark_as_ended_in_cache(video_id) → bool`**
- 目的: 終了動画をキャッシュ内で "ended" 状態に変更

**`clear_ended_videos_from_cache() → int`**
- 目的: 終了済みキャッシュのクリーンアップ
- 仕様: cache_manager 内部で期限管理（自動削除）
- 返却: 削除した動画数

---

## YouTubeLivePoller（ポーリング層）

状態監視 + 遷移検出 + **キャッシュ戦略管理**（Poller が キャッシュ使用判断を内化）

### クラス定義

```python
class YouTubeLivePoller:
    """
    ポーリング層 - 状態監視 + 遷移検出 + キャッシュ戦略

    【キャッシュ戦略】
    _get_video_detail_with_cache():
      1. APIプラグインのキャッシュチェック（5分有効）
      2. キャッシュ miss → API 呼び出し
      3. LIVE 状態なら自動的にキャッシュに登録
      4. 詳細情報を返す

    poll_unclassified_videos():
      - キャッシュヘルパーで効率化

    poll_live_status():
      - キャッシュヘルパーで最新状態を取得
      - 状態変化検出
      - 状態変化時のみ Cache + DB を更新

    process_ended_cache_entries():
      - 終了済みキャッシュから未投稿の動画を検出
    """
```

### 主要メソッド

#### `poll_unclassified_videos() → int`

DB から未分類動画を取得して分類・更新

**処理順序**:
1. Store.get_unclassified_videos() で DB から content_type="video" の動画を取得
2. _get_video_detail_with_cache() でキャッシュ優先取得
3. Classifier で分類
4. Store で DB 更新
5. AutoPoster のイベントリスナーで投稿判定

#### `poll_live_status() → None`

LIVE/upcoming 状態の動画をポーリング（メインポーリング処理）

**処理順序**:
1. Store から live_status='upcoming'/'live'/'completed' の動画を取得
2. **各動画について以下を実行**:
   - _get_video_detail_with_cache(video_id) で最新 details を取得（キャッシュ優先）
   - Classifier.classify(details) で (new_content_type, new_live_status) を決定
   - _detect_state_transitions(video, new_content_type, new_live_status) で遷移検出
   - 遷移あり → Store で DB + キャッシュを更新
   - イベント発火（on_live_started, on_live_ended, on_archive_available）
3. process_ended_cache_entries() で終了済み動画を処理

#### `process_ended_cache_entries() → None`

終了済みキャッシュから未投稿の動画を検出・投稿

**処理順序**:
1. キャッシュから status='ended' の動画を取得
2. 各動画について DB の posted_to_bluesky フラグを確認
3. 未投稿なら _get_video_detail_with_cache() でアーカイブ確認
4. イベント発火（on_archive_available）
5. キャッシュをクリーンアップ（clear_ended_videos_from_cache）

#### `_get_video_detail_with_cache(video_id) → Dict | None` ★ キャッシュ戦略

キャッシュ優先でデータ取得（API 呼び出し削減）

**処理**:
1. API プラグイン._get_cached_video_detail(video_id) → キャッシュ確認
2. キャッシュ hit → キャッシュ返却
3. キャッシュ miss → API プラグイン._fetch_video_detail(video_id)
4. API エラー → None
5. LIVE 状態なら自動的に Cache に登録

#### `_detect_state_transitions(video, new_content_type, new_live_status) → bool`

DB の旧状態と API の新状態を比較して遷移検出

**処理**:
1. video (DB) から old_content_type と old_live_status を取得
2. 新旧を比較：
   - old_live_status != new_live_status → 遷移あり
   - old_content_type != new_content_type → 遷移あり
3. 遷移パターンを判定：
   - None → "upcoming" (scheduled)
   - "upcoming" → "live" (started)
   - "live" → "completed" (ended)
   - "completed" → "completed" (no change, archive stable)
4. **遷移あり時に**：
   - Store.update_video_classification() で DB 更新
   - Store.update_cache_entry() でキャッシュ更新
   - _emit_event() でイベント発火
5. 遷移検出結果を返却 (True: 遷移あり, False: 遷移なし)

**返却値**: bool
- True: 状態遷移が発生した
- False: 状態に変化がない（ポーリング間隔短縮の判定に使用）

#### `_emit_event(event_name, video_id, video_data) → None`

状態遷移イベントを発火

**イベント種別**:
- `"live_started"`: upcoming → live への遷移
- `"live_ended"`: live → completed への遷移
- `"archive_available"`: completed 確定時の再確認

---

## YouTubeLiveAutoPoster（自動投稿層）

イベント処理 + 投稿判定（**唯一の自動投稿判定点**）

### クラス定義

```python
class YouTubeLiveAutoPoster:
    """
    自動投稿層 - イベント受け取り + 投稿判定 + 実行

    Poller からのイベントを受け取り、_should_autopost_event() で
    唯一の投稿判定を行う。
    """
```

### 主要メソッド

#### `on_live_started(video_id, video_data) → bool`

ライブ開始イベント処理

**処理**:
1. イベント入力: video_id, content_type="live", live_status="live"
2. _should_autopost_event("live_start", video_data) で判定
3. 判定結果に応じて：
   - true: plugin_manager.post_video(video_data) を実行
   - false: スキップ、ログ出力
4. 成功時: Store.mark_as_posted(video_id)

#### `on_live_ended(video_id, video_data) → bool`

ライブ終了イベント処理

**処理**:
1. イベント入力: video_id, content_type="archive", live_status="completed"
2. _should_autopost_event("live_end", video_data) で判定
3. 判定結果に応じて：
   - true: plugin_manager.post_video(video_data) を実行
   - false: スキップ
4. 成功時: Store.mark_as_posted(video_id)
5. Store.mark_as_ended_in_cache(video_id) で終了マーク

#### `on_archive_available(video_id, video_data) → bool`

アーカイブ化イベント処理

**処理**:
1. イベント入力: video_id, アーカイブ確認完了
2. DB で posted_to_bluesky を確認
3. 未投稿なら _should_autopost_event("archive_available", video_data) で判定
4. 判定結果に応じて：
   - true: plugin_manager.post_video(video_data) を実行
   - false: スキップ
5. 成功時: Store.mark_as_posted(video_id)

#### `_should_autopost_event(event_type, video_data) → bool` ★ 唯一の投稿判定点

投稿すべきかを判定する**唯一の判定点**

**引数**:
- `event_type` (str): "live_start" / "live_end" / "archive_available"
- `video_data` (Dict): 動画情報（content_type, live_status, is_premiere 等を含む）

**判定ロジック**:

| 条件 | 判定内容 |
|:--|:--|
| APP_MODE != autopost | False → 手動モードでは自動投稿なし |
| YOUTUBE_LIVE_AUTO_POST_MODE == "off" | False → YouTube Live 自動投稿無効 |
| YOUTUBE_LIVE_AUTO_POST_MODE == "all" | True → 全イベント投稿 |
| YOUTUBE_LIVE_AUTO_POST_MODE == "schedule" | event_type == "live_start" ? True : False |
| YOUTUBE_LIVE_AUTO_POST_MODE == "live" | event_type in ["live_start", "live_end"] ? True : False |
| YOUTUBE_LIVE_AUTO_POST_MODE == "archive" | event_type == "archive_available" ? True : False |
| 個別フラグ（SELFPOST時） | YOUTUBE_LIVE_AUTO_POST_SCHEDULE 等で判定 |
| 投稿禁止条件（重複投稿等） | False → DB で既投稿確認 |

**返却値**: bool
- True: 投稿を実行
- False: スキップ

---

---

RSS で登録された未判定動画を API で判定し、DB を更新

**処理フロー**：

```
step1: DB から content_type="video" の動画一覧を取得
step2: 各動画について以下を実行
  2a: キャッシュから API データを取得を試みる
  2b: キャッシュなければ API から新規取得
  2c: API エラーならスキップ
  2d: 取得した API データから content_type, live_status を分類
  2e: 取得した日時を UTC→JST に変換して DB を更新
  2f: タイトル、チャンネル名、サムネイルなどのメタデータも更新
  2g: 判定後、自動投稿判定を実行（content_type='live' or 'archive' の場合）
step3: 判定統計をログ出力
```

**戻り値**: 更新した動画数

**コード例**：

```python
def _update_unclassified_videos(self) -> int:
    all_videos = self.db.get_all_videos()
    unclassified = [
        v for v in all_videos
        if v.get("content_type") == "video" or v.get("content_type") is None
    ]

    logger.info(f"📊 未判定動画: {len(unclassified)} 件を確認します...")
    updated_count = 0

    for video in unclassified:
        video_id = video.get("video_id")

        # キャッシュ優先で取得
        details = self.api_plugin._get_cached_video_detail(video_id)

        # キャッシュなければ API から取得
        if not details:
            try:
                details = self.api_plugin._fetch_video_detail(video_id)
            except Exception as e:
                logger.debug(f"⏭️ API エラー（スキップ）: {video_id} - {e}")
                continue

        # 分類
        content_type, live_status, is_premiere = self._classify_live(details)

        # DB 更新（life or archive のみ）
        if content_type in ("live", "archive"):
            success = self.db.update_video_status(
                video_id, content_type, live_status
            )
            if success:
                updated_count += 1
                logger.info(f"✅ 判定更新: {video_id} → {content_type}")

    return updated_count
```

---

##### 4. `post_video(video: Dict) → bool`

個別の動画情報を受け取り、LIVE/Archive を判定して DB に保存

**パラメータ**：
```python
video = {
    "video_id": "dQw4w9WgXcQ",      # 必須
    "title": "動画タイトル",          # オプション（API から取得）
    "channel_name": "チャンネル名",    # オプション（API から取得）
    "published_at": "2025-12-30 ...",  # オプション（API から取得）
    "video_url": "https://...",        # オプション（API から構築）
}
```

**処理内容**：
1. video_id が YouTube 形式か検証（11字英数字）
2. API から動画詳細を取得
3. _classify_live() で判定
4. DB に insert_video() で保存

**戻り値**:
- `True` : 保存成功または非YouTube形式（対応不可）
- `False` : API エラーなど

---

##### 5. `poll_live_status() → None`

定期的に実行される状態遷移検出メイン処理

**実行間隔**:
- YouTubeLive ポーリング: 15分（終了済み動画がある場合は5分）
- 設定で制御可能

**処理の全体像**:

```
① DB から live_status='upcoming'/'live' の動画を取得
   └─ キャッシュから status='live' の未登録動画も取得

② 各動画について以下を実行
   2a: API で最新状態を確認（リトライ最大3回）
   2b: 分類ロジックで new_live_status を判定
   2c: キャッシュの有効期限をチェック
   2d: キャッシュがなければ新規追加、あれば更新
   2e: キャッシュをファイルに保存

③ old_status → new_status の遷移パターンに応じて処理
   3a: upcoming → live
       └─ auto_post_live_start() でライブ開始を投稿
   3b: live → completed
       └─ auto_post_live_end() でライブ終了を投稿
   3c: completed → archive
       └─ auto_post_archive_available() でアーカイブ化を投稿
   3d: 状態遷移なし（upcoming のまま、live のまま）
       └─ 投稿スキップ

④ 終了済みエントリを処理
   └─ _process_ended_cache_entries() で未投稿の動画を検出・投稿

⑤ 1時間以上経過した終了済みエントリをクリーンアップ
```

**詳細コード**（状態遷移検出部分）：

```python
def poll_live_status(self) -> None:
    # ① DB から取得
    upcoming_videos = self.db.get_videos_by_live_status("upcoming")
    live_videos = self.db.get_videos_by_live_status("live")
    all_live_videos = upcoming_videos + live_videos

    cache = get_youtube_live_cache()

    for video in all_live_videos:
        video_id = video.get("video_id")
        old_live_status = video.get("live_status")  # 前の状態

        # ② API で最新状態を確認
        details = self.api_plugin._fetch_video_detail_bypass_cache(video_id)
        if not details:
            logger.warning(f"❌ 動画詳細取得に失敗: {video_id}")
            continue

        # ③ 新しい状態を判定
        content_type, new_live_status, is_premiere = self._classify_live(details)

        # ④ キャッシュ管理
        cache_entry = cache.get_live_video(video_id)
        if not cache_entry or not cache._is_cache_entry_valid(video_id):
            cache.add_live_video(video_id, {...}, details)
        else:
            cache.update_live_video(video_id, details)
        cache._save_cache()

        # ⑤ 状態遷移パターンの処理
        config = get_config("settings.env")

        if old_live_status == "upcoming" and new_live_status == "live":
            # ⭐ ライブ開始
            logger.info(f"🚀 ライブ開始を検知: {video_id}")
            self.db.update_video_status(video_id, content_type, new_live_status)
            if self._should_autopost_live(content_type, new_live_status, config):
                self.auto_post_live_start(video)

        elif old_live_status == "live" and new_live_status == "completed":
            # ⭐ ライブ終了
            logger.info(f"✅ ライブ終了を検知: {video_id}")
            cache.mark_as_ended(video_id)
            self.db.update_video_status(video_id, content_type, new_live_status)
            if self._should_autopost_live(content_type, new_live_status, config):
                self.auto_post_live_end(video)

        elif old_live_status == "completed" and content_type == "archive":
            # ⭐ アーカイブ化
            logger.info(f"📼 アーカイブ化を検知: {video_id}")
            self.db.update_video_status(video_id, content_type, "completed")
            if self._should_autopost_live(content_type, "completed", config):
                self.auto_post_archive_available(video)
```

---

##### 6. `_should_autopost_live(content_type, live_status, config) → bool`

投稿するべきかを判定

**ロジック**:

1. **APP_MODE が `autopost` の場合**:
   - `YOUTUBE_LIVE_AUTO_POST_MODE` の値で判定
   - `mode="off"` → 投稿スキップ
   - `mode="all"` → すべて投稿
   - `mode="schedule"` → 予約枠のみ（upcoming）
   - `mode="live"` → 配信開始・終了のみ（live/completed）
   - `mode="archive"` → アーカイブのみ

2. **APP_MODE が `selfpost` など他の場合**:
   - 個別フラグで判定
   - `YOUTUBE_LIVE_AUTO_POST_SCHEDULE` (upcoming 時)
   - `YOUTUBE_LIVE_AUTO_POST_LIVE` (live/completed 時)
   - `YOUTUBE_LIVE_AUTO_POST_ARCHIVE` (archive 時)

**コード例**：

```python
def _should_autopost_live(self, content_type: str, live_status: Optional[str], config=None) -> bool:
    if config is None:
        from config import get_config
        config = get_config("settings.env")

    # AUTOPOST か SELFPOST で分岐
    if config.operation_mode == "autopost":
        mode = config.youtube_live_autopost_mode
    else:
        mode = ""  # 個別フラグで判定

    # 統合モード値での判定
    if mode == "off":
        return False
    elif mode == "all":
        return content_type in ("video", "live", "archive")
    elif mode == "schedule":
        return content_type == "live" and live_status == "upcoming"
    elif mode == "live":
        return content_type == "live" and live_status in ("live", "completed")
    elif mode == "archive":
        return content_type == "archive"

    # 個別フラグで判定（mode=="" または mode未設定）
    if content_type == "live":
        if live_status == "upcoming":
            return config.youtube_live_auto_post_schedule
        elif live_status in ("live", "completed"):
            return config.youtube_live_auto_post_live
    elif content_type == "archive":
        return config.youtube_live_auto_post_archive

    return False
```

---

##### 7. 自動投稿メソッド

###### 7a. `auto_post_live_start(video) → bool`

ライブ開始の自動投稿

```python
def auto_post_live_start(self, video: Dict[str, Any]) -> bool:
    from plugin_manager import PluginManager
    pm = PluginManager()
    bluesky_plugin = pm.get_plugin("bluesky_plugin")

    if not bluesky_plugin or not bluesky_plugin.is_available():
        logger.warning("⚠️ Bluesky プラグインが利用不可です")
        return False

    video_copy = dict(video)
    video_copy["event_type"] = "live_start"
    video_copy["content_type"] = "live"
    video_copy["classification_type"] = "live"  # ★ テンプレート選択用

    success = bluesky_plugin.post_video(video_copy)

    if success:
        video_id = video.get("video_id")
        self.db.mark_as_posted(video_id)  # ★ 投稿フラグを立てる
        logger.info(f"✅ ライブ開始通知を投稿し、DB を更新しました: {video_id}")
    else:
        logger.warning(f"⚠️ ライブ開始投稿に失敗しました: {video.get('video_id')}")

    return success
```

###### 7b. `auto_post_live_end(video) → bool`

ライブ終了の自動投稿

```python
def auto_post_live_end(self, video: Dict[str, Any]) -> bool:
    from plugin_manager import PluginManager
    pm = PluginManager()
    bluesky_plugin = pm.get_plugin("bluesky_plugin")

    if not bluesky_plugin or not bluesky_plugin.is_available():
        logger.warning("⚠️ Bluesky プラグインが利用不可です")
        return False

    video_copy = dict(video)
    video_copy["event_type"] = "live_end"
    video_copy["live_status"] = "completed"
    video_copy["content_type"] = "live"
    video_copy["classification_type"] = "completed"  # ★ yt_offline テンプレート選択用

    success = bluesky_plugin.post_video(video_copy)

    if success:
        video_id = video.get("video_id")
        self.db.mark_as_posted(video_id)
        logger.info(f"✅ ライブ終了通知を投稿し、DB を更新しました: {video_id}")
    else:
        logger.warning(f"⚠️ ライブ終了投稿に失敗しました: {video.get('video_id')}")

    return success
```

###### 7c. `auto_post_archive_available(video) → bool`

アーカイブ化の自動投稿（新規実装）

```python
def auto_post_archive_available(self, video: Dict[str, Any]) -> bool:
    from plugin_manager import PluginManager
    pm = PluginManager()
    bluesky_plugin = pm.get_plugin("bluesky_plugin")

    if not bluesky_plugin or not bluesky_plugin.is_available():
        logger.warning("⚠️ Bluesky プラグインが利用不可です")
        return False

    video_copy = dict(video)
    video_copy["event_type"] = "archive_available"
    video_copy["live_status"] = "completed"
    video_copy["content_type"] = "archive"
    video_copy["classification_type"] = "archive"  # ★ yt_archive テンプレート選択用

    success = bluesky_plugin.post_video(video_copy)

    if success:
        video_id = video.get("video_id")
        self.db.mark_as_posted(video_id)
        logger.info(f"✅ アーカイブ化通知を投稿し、DB を更新しました: {video_id}")
    else:
        logger.warning(f"⚠️ アーカイブ化通知投稿に失敗しました: {video.get('video_id')}")

    return success
```

---

##### 8. `_process_ended_cache_entries(cache) → None`

終了済みキャッシュエントリから未投稿の動画を検出して投稿処理を実行

**背景**: ポーリング処理で「live」から「completed」に状態遷移した動画がありますが、そのエントリがキャッシュに「ended」状態で残ります。これらの未投稿動画を最後に検出・投稿するための処理です。

```python
def _process_ended_cache_entries(self, cache) -> None:
    config = get_config("settings.env")

    ended_videos = cache.get_live_videos_by_status("ended")
    if not ended_videos:
        logger.debug("ℹ️ 終了済みキャッシュエントリはありません")
        return

    logger.info(f"🔍 {len(ended_videos)} 件の終了済みキャッシュエントリをチェック...")

    for cache_entry in ended_videos:
        video_id = cache_entry.get("video_id")

        # DB での投稿フラグを確認
        conn = self.db._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT posted_to_bluesky, live_status, content_type FROM videos WHERE video_id = ?",
            (video_id,)
        )
        row = cursor.fetchone()
        conn.close()

        if not row:
            # DB に登録されていない場合
            posted_flag = 0
            live_status = "completed"
            content_type = "archive"
        else:
            posted_flag = row[0]
            live_status = row[1] or "completed"
            content_type = row[2] or "archive"

        # 未投稿の場合のみ投稿処理を実行
        if not posted_flag:
            logger.info(f"📌 終了済みキャッシュから投稿対象を検出: {video_id}")

            if self._should_autopost_live(content_type, live_status, config):
                # 投稿用データを構築
                video_data = {
                    "video_id": video_id,
                    "title": cache_entry.get("db_data", {}).get("title", "Unknown"),
                    "channel_name": cache_entry.get("db_data", {}).get("channel_name", "Unknown"),
                    "video_url": cache_entry.get("db_data", {}).get("video_url", ""),
                    "published_at": cache_entry.get("db_data", {}).get("published_at", ""),
                    "thumbnail_url": cache_entry.get("db_data", {}).get("thumbnail_url", ""),
                    "live_status": live_status,
                    "content_type": content_type,
                }

                logger.info(f"📡 終了済みキャッシュから自動投稿を実行: {video_id}")

                if live_status == "completed" or content_type == "archive":
                    self.auto_post_live_end(video_data)
                elif live_status == "live":
                    self.auto_post_live_start(video_data)
```

---

### ヘルパーメソッド

#### `_is_valid_youtube_video_id(video_id) → bool`

YouTube 形式の video_id か検証（11字の英数字）

```python
def _is_valid_youtube_video_id(self, video_id: str) -> bool:
    import re
    if re.match(r'^[A-Za-z0-9_-]{11}$', video_id):
        return True
    return False
```

#### `_convert_utc_to_jst(utc_datetime_str) → str`

UTC ISO 8601 → JST に変換

```python
def _convert_utc_to_jst(self, utc_datetime_str: str) -> str:
    try:
        utc_time = datetime.fromisoformat(utc_datetime_str.replace('Z', '+00:00'))
        jst_time = utc_time.astimezone(timezone(timedelta(hours=9))).replace(tzinfo=None)
        return jst_time.strftime('%Y-%m-%d %H:%M:%S')
    except Exception as e:
        logger.warning(f"⚠️ UTC→JST 変換失敗: {utc_datetime_str} - {e}")
        return utc_datetime_str
```

#### `_classify_live(details) → (content_type, live_status, is_premiere)`

YouTube API データから LIVE/Archive を判定

**実装**: YouTubeAPIPlugin の `_classify_video_core()` へ委譲

```python
def _classify_live(self, details: Dict[str, Any]) -> Tuple[str, Optional[str], bool]:
    return self.api_plugin._classify_video_core(details)
```

---

## 実装チェックリスト

### ✅ 4層構造の実装完了

#### 分類層（YouTubeLiveClassifier）
- ✅ YouTube API データ → content_type/live_status の純粋分類
- ✅ ロジック判定なし（API データを分類結果に変換のみ）

#### ストレージ層（YouTubeLiveStore）
- ✅ DB 読み書き（get_unclassified_videos, update_video_classification など）
- ✅ キャッシュ読み書き（add_live_video_to_cache, update_cache_entry など）
- ✅ 渡されたデータをそのまま保存/取得（ロジックなし）

#### ポーリング層（YouTubeLivePoller）
- ✅ 状態監視 + 遷移検出（_detect_state_transitions で old → new）
- ✅ キャッシュ戦略管理（_get_video_detail_with_cache で API 呼び出し削減）
- ✅ poll_unclassified_videos() で RSS 登録動画を分類
- ✅ poll_live_status() で upcoming → live → completed → archive を追跡
- ✅ process_ended_cache_entries() で終了済みキャッシュを処理

#### 自動投稿層（YouTubeLiveAutoPoster）
- ✅ イベントハンドラ（on_live_started, on_live_ended, on_archive_available）
- ✅ _should_autopost_event() が唯一の投稿判定点
- ✅ APP_MODE と YOUTUBE_LIVE_AUTO_POST_MODE での判定

### ✅ キャッシュ戦略の実装完了

- ✅ _get_video_detail_with_cache() でキャッシュ優先データ取得
- ✅ キャッシュ有効期限管理（5分）
- ✅ 状態変化時のみ Cache + DB を更新
- ✅ API クォータ大幅削減（5分ポーリングで3回分削減）

---

## まとめ

### 4層アーキテクチャの完成

**Classifier** → **Store** → **Poller** → **AutoPoster** の4層で責務を明確に分離：

1. **Classifier**: 純粋分類
2. **Store**: 純粋 CRUD
3. **Poller**: 状態遷移検出 + キャッシュ戦略
4. **AutoPoster**: 投稿判定（唯一の判定点）

---

### YouTubeLiveCache クラス

ライブ配信の状態を JSON で管理し、ポーリング結果を追跡するためのシステム

#### キャッシュファイルの場所

```
v3/data/youtube_live_cache.json
```

#### キャッシュのデータ構造

```json
{
  "58S5Pzux9BI": {
    "video_id": "58S5Pzux9BI",
    "db_data": {
      "title": "【雑談】ゆめうさサイト＆まゆねこアプリ公開配信",
      "channel_name": "まゆにゃあ",
      "video_url": "https://www.youtube.com/watch?v=58S5Pzux9BI",
      "published_at": "2025-12-29 03:00:00",
      "thumbnail_url": "https://i.ytimg.com/vi/58S5Pzux9BI/hqdefault_live.jpg"
    },
    "api_data": {
      "kind": "youtube#video",
      "snippet": {
        "title": "【雑談】ゆめうさサイト＆まゆねこアプリ公開配信",
        "channelTitle": "まゆにゃあ",
        "publishedAt": "2025-12-29T21:25:15Z"
      },
      "liveStreamingDetails": {
        "scheduledStartTime": "2025-12-29T12:00:00Z",
        "actualStartTime": "2025-12-29T12:05:30Z",
        "actualEndTime": "2025-12-29T14:30:00Z",
        "concurrentViewers": "500"
      }
    },
    "cached_at": "2025-12-30T07:53:08.026000",
    "status": "ended",
    "poll_count": 3,
    "last_polled_at": "2025-12-30T08:08:15.123456",
    "ended_at": "2025-12-30T07:53:08.026000",
    "scheduled_start_time": "2025-12-29T12:00:00Z"
  }
}
```

#### キャッシュのステータス種類

| ステータス | 説明 | 有効期限 |
|:--|:--|:--|
| `"live"` | ライブ配信中または配信予定 | 5分 |
| `"ended"` | ライブ配信が終了済み | なし（1時間経過で削除） |

#### 有効期限チェック

```python
LIVE_CACHE_EXPIRY_SECONDS = 5 * 60  # 5分
```

キャッシュエントリが5分以上経過すると期限切れと判定され、DB ポーリング結果を反映しなくなります。

---

### キャッシュ管理メソッド

#### `add_live_video(video_id, db_data, api_data) → bool`

新しいライブ動画をキャッシュに追加

```python
cache = get_youtube_live_cache()
cache.add_live_video(
    video_id="dQw4w9WgXcQ",
    db_data={
        "title": "Live Stream",
        "channel_name": "Channel",
        ...
    },
    api_data={
        "snippet": {...},
        "liveStreamingDetails": {...}
    }
)
cache._save_cache()  # ファイルに保存
```

#### `update_live_video(video_id, api_data) → bool`

キャッシュ内の動画データをポーリング結果で更新

```python
cache.update_live_video("dQw4w9WgXcQ", updated_api_data)
cache._save_cache()
```

#### `mark_as_ended(video_id) → bool`

動画をライブ終了状態に更新

```python
cache.mark_as_ended("dQw4w9WgXcQ")
cache._save_cache()
```

#### `get_live_videos_by_status(status) → List[Dict]`

ステータスでフィルタして取得

```python
# ライブ中の動画
live_videos = cache.get_live_videos_by_status("live")

# 終了済みの動画
ended_videos = cache.get_live_videos_by_status("ended")
```

#### `clear_ended_videos(max_age_seconds=3600) → int`

1時間以上経過した終了済み動画をクリーンアップ

```python
count = cache.clear_ended_videos(max_age_seconds=3600)
logger.info(f"クリーンアップ: {count} 件削除")
```

---

## 分類ロジック（ライブ/アーカイブ判定）

### 分類メソッド

YouTubeAPIPlugin の `_classify_video_core()` へ委譲

**入力**: YouTube API の videos.list 応答

**出力**: (content_type, live_status, is_premiere)

### content_type の種類

| 値 | 説明 | API フラグ |
|:--|:--|:--|
| `"video"` | 通常の動画（LIVE ではない） | liveStreamingDetails なし |
| `"live"` | LIVE 配信 | liveStreamingDetails あり、actualEndTime なし |
| `"archive"` | LIVE アーカイブ | liveStreamingDetails あり、actualEndTime あり |

### live_status の種類

| 値 | 説明 | API フラグ | content_type |
|:--|:--|:--|:--|
| `None` | 不明（通常動画） | - | video |
| `"upcoming"` | 配信予定 | scheduledStartTime あり | live |
| `"live"` | 配信中 | actualStartTime あり | live |
| `"completed"` | 配信終了 | actualEndTime あり | live or archive |

### 分類フロー

```
step1: API データから liveStreamingDetails を抽出
step2: 以下の条件で判定

【フロー1】liveStreamingDetails がない場合
  → content_type="video", live_status=None

【フロー2】liveStreamingDetails がある場合
  step2a: actualEndTime（配信終了時刻）をチェック
    ✅ あり → アーカイブ
      └─ content_type="archive", live_status="completed"
    ❌ なし → ライブ配信（進行中または予定）
      step2b: actualStartTime（配信開始時刻）をチェック
        ✅ あり → 配信中
          └─ content_type="live", live_status="live"
        ❌ なし → 配信予定
          └─ content_type="live", live_status="upcoming"

【フロー3】是否premiere フラグ
  step3: is_premiere = bool(liveStreamingDetails.get("actualEndTime") and "premiere" in snippet.get("title", "").lower())
```

---

## ポーリングフロー

### ポーリング間隔の決定

```python
# YouTubeLive ライブ終了検知ポーリング（main_v3.py で実行）

# キャッシュ内に「live」状態のエントリがあるか確認
live_count = len(cache.get_live_videos_by_status("live"))

if live_count > 0:
    # LIVE 配信中：5分間隔で検査（短い）
    interval = 5
else:
    # LIVE なし：15分間隔で検査（長い）
    interval = 15

# 設定で上書き可能
# YOUTUBE_LIVE_POLL_INTERVAL_ACTIVE=5
# YOUTUBE_LIVE_POLL_INTERVAL_COMPLETED=15
# YOUTUBE_LIVE_POLL_INTERVAL_NO_LIVE=30
```

### 状態遷移を図で見る

```
time=0min
┌─────────────────────────┐
│ 【予約状態】            │
│ live_status="upcoming"  │
│ content_type="live"     │
│ poll_count=1            │
└─────────────────────────┘
        ↓ ポーリング (5分間隔)
time=15min
┌─────────────────────────┐
│ 【配信中】              │
│ live_status="live"      │
│ content_type="live"     │
│ poll_count=4            │
│ >>> 自動投稿実行        │
│ >>> mark_as_posted()    │
└─────────────────────────┘
        ↓ ポーリング (5分間隔)
time=90min
┌─────────────────────────┐
│ 【配信終了】            │
│ live_status="completed" │
│ content_type="live"     │ ★ 終了告知時は content_type="live"
│ poll_count=16           │
│ >>> 自動投稿実行        │
│ >>> cache.mark_as_ended() │
└─────────────────────────┘
        ↓ ポーリング (5分間隔)
time=95min
┌─────────────────────────┐
│ 【アーカイブ化】        │
│ live_status="completed" │
│ content_type="archive"  │ ★ アーカイブ化後は content_type="archive"
│ poll_count=17           │
│ status="ended"          │
│ >>> 自動投稿実行        │
└─────────────────────────┘
        ↓ 1時間経過で
time=155min
        削除
```

---

## 自動投稿メカニズム

### テンプレート選択ロジック

YouTubeLive プラグインは Bluesky プラグインに以下の情報を渡します：

```python
video["event_type"] = "live_start" | "live_end" | "archive_available"
video["classification_type"] = "live" | "completed" | "archive"
```

Bluesky プラグインはこれらの情報に基づいてテンプレートを選択します：

| event_type | classification_type | テンプレート | 内容 |
|:--|:--|:--|:--|
| `"live_start"` | `"live"` | `yt_online_template.txt` | ライブ開始通知 |
| `"live_end"` | `"completed"` | `yt_offline_template.txt` | ライブ終了通知 |
| `"archive_available"` | `"archive"` | `yt_archive_template.txt` | アーカイブ公開通知 |

### 投稿フロー

```
1. 状態遷移を検出
   ├─ upcoming → live
   ├─ live → completed
   └─ completed → archive

2. _should_autopost_live() で投稿判定

3. 投稿判定=True の場合
   ├─ auto_post_live_start() または
   ├─ auto_post_live_end() または
   └─ auto_post_archive_available() を実行

4. 各メソッド内
   ├─ Bluesky プラグインを取得
   ├─ event_type, classification_type を設定
   ├─ bluesky_plugin.post_video() を実行
   ├─ 投稿成功時のみ db.mark_as_posted() を実行
   └─ ログを出力
```

---

## 状態遷移制御

### 重要な設計ポイント

**ライブ終了 → アーカイブ化の段階的遷移**

```
問題: API は「終了したライブ」を即座に「アーカイブ」に分類しない
     場合がある。段階的に情報が更新されることがある。

対策: 2つのポーリングに分ける

ポーリング#1
┌─────────────────────────┐
│ old_status="live"       │
│ new_status="completed"  │
│ API content_type="archive"（可能性）
│                         │
│ >>> content_type を "live" で上書き
│ >>> DB: content_type="live"
│ >>> 自動投稿実行（ライブ終了通知）
└─────────────────────────┘

ポーリング#2（5分後）
┌─────────────────────────┐
│ old_status="completed"  │
│ new_status="completed"  │
│ API content_type="archive"
│                         │
│ >>> content_type="archive" を確定
│ >>> DB: content_type="archive"
│ >>> 自動投稿実行（アーカイブ化通知）
└─────────────────────────┘
```

**実装コード**:

```python
if old_live_status == "live" and new_live_status == "completed":
    # 終了検知時点では content_type を "live" のままにする
    logger.info(f"📋 【状態遷移制御】 live → completed: content_type を 'live' のまま保持")
    content_type = "live"  # API の分類結果を上書き
    self.auto_post_live_end(video)

elif old_live_status == "completed" and content_type == "archive":
    # 前回のポーリングで completed に更新済みで、今回 archive に分類
    logger.info(f"📋 【状態遷移制御】 completed → archive: アーカイブ化が確定")
    self.auto_post_archive_available(video)
```

---

## データベース統合

### DB スキーマの拡張カラム

| カラム | 型 | 説明 |
|:--|:--|:--|
| `content_type` | TEXT | "video", "live", "archive" のいずれか |
| `live_status` | TEXT | None, "upcoming", "live", "completed" のいずれか |
| `posted_to_bluesky` | INTEGER | 1=投稿済み, 0=未投稿 |

### DB 更新のタイミング

```python
# 初期化時
db.update_video_status(video_id, content_type, live_status)

# ポーリング時
db.update_video_status(video_id, content_type, new_live_status)

# 投稿後
db.mark_as_posted(video_id)  # posted_to_bluesky = 1

# 日時更新
db.update_published_at(video_id, api_published_at_jst)

# メタデータ更新
db.update_video_metadata(video_id, title=..., channel_name=..., thumbnail_url=...)
```

---

## エラーハンドリング

### API エラーの扱い

```
API 呼び出しエラー
  ↓
リトライロジック（最大3回）
  ├─ 1回目失敗 → 2秒待機 → 2回目試行
  ├─ 2回目失敗 → 2秒待機 → 3回目試行
  └─ 3回目失敗 → ログ出力 → スキップ
```

### キャッシュエラーの扱い

```
キャッシュ保存失敗
  ↓
例外をキャッチして続行（処理を中断しない）
  ↓
ログ出力（警告レベル）
```

### Bluesky 投稿エラー

```
投稿失敗
  ↓
posted_to_bluesky フラグを立てない（DB 更新なし）
  ↓
ログで失敗を記録
  ↓
次のポーリングで再試行の余地あり
```

---

## 実装チェックリスト

### ✅ 実装済み機能

- ✅ RSS 登録動画の自動判定（on_enable）
- ✅ キャッシュを用いたポーリング状態追跡
- ✅ upcoming → live → completed → archive の段階的追跡
- ✅ 状態遷移の検出と自動投稿トリガー
- ✅ APP_MODE に応じた柔軟な投稿制御
- ✅ ライブ開始通知（auto_post_live_start）
- ✅ ライブ終了通知（auto_post_live_end）
- ✅ アーカイブ化通知（auto_post_archive_available）
- ✅ 終了済みキャッシュエントリの処理（_process_ended_cache_entries）
- ✅ キャッシュの有効期限管理（5分）
- ✅ ポーリング間隔の動的制御（5分/15分）
- ✅ API クォータの最適化（キャッシュ優先）
- ✅ UTC → JST 日時変換
- ✅ Niconico など非YouTube形式の判定スキップ

### 🔄 進行中の機能

- 🔄 テンプレートの自動選択（Bluesky プラグイン側で実装）

### 🔮 将来実装予定

- 🔮 複数チャンネルの同時監視
- 🔮 LIVE 継続中の定期更新通知
- 🔮 視聴者数の追跡
- 🔮 コメント監視機能

---

## まとめ

YouTubeLive プラグインは、以下の3つの層で構成されています：

1. **分類層** (`_classify_live`): 動画情報から LIVE/Archive を判定
2. **ポーリング層** (`poll_live_status`): 状態遷移を検出
3. **投稿層** (`auto_post_*`): 状態遷移に応じて Bluesky に自動投稿

このアーキテクチャにより、YouTube のライブ配信を柔軟に監視し、状態に応じた通知を Bluesky に投稿することができます。

---

**作成日**: 2025-12-30
**最後の修正**: 2025-12-30（4層分割 + キャッシュ戦略統合完了）
**ステータス**: ✅ 完成・検証済み（4層分割版）
**担当**: mayuneco(mayunya)
