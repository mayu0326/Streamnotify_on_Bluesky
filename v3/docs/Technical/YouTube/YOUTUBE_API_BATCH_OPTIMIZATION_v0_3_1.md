# YouTube Data API バッチ処理最適化 - v0.3.1 実装ガイド

**対象バージョン**: YouTubeLive プラグイン v0.3.1
**最終更新**: 2025-12-27
**ステータス**: ✅ 実装完了・検証済み

---

## 📖 目次

1. [概要](#概要)
2. [最適化の課題](#最適化の課題)
3. [実装戦略](#実装戦略)
4. [アーキテクチャ](#アーキテクチャ)
5. [実装詳細](#実装詳細)
6. [パフォーマンス測定](#パフォーマンス測定)
7. [ログ出力](#ログ出力)
8. [トラブルシューティング](#トラブルシューティング)

---

## 概要

### バッチ処理最適化の目的

YouTube Data API の**日次クォータ消費を最小化**するため、複数の動画詳細を効率的に取得します。

### 改善前（個別取得）

```
poll_unclassified_videos() の処理:
  ├─ 未分類動画：20件
  ├─ ループで動画ごとに API 呼び出し
  │  ├─ _get_video_detail_with_cache(video_id_1) → 1 ユニット
  │  ├─ _get_video_detail_with_cache(video_id_2) → 1 ユニット
  │  ├─ ...
  │  └─ _get_video_detail_with_cache(video_id_20) → 1 ユニット
  └─ 合計: 20 ユニット (キャッシュミス時)

poll_live_status() の処理:
  ├─ LIVE 関連動画：upcoming=5, live=3, completed=2 (計10件)
  ├─ ループで動画ごとに API 呼び出し
  │  └─ 合計: 10 ユニット (キャッシュミス時)

process_ended_cache_entries() の処理:
  ├─ ended キャッシュ：8件
  └─ 合計: 8 ユニット (キャッシュミス時)

1ポーリングサイクルコスト: 20 + 10 + 8 = 38 ユニット ❌
```

### 改善後（バッチ取得）

```
poll_unclassified_videos() の処理:
  ├─ 未分類動画：20件
  ├─ 動画 ID 20個を収集
  ├─ fetch_video_details_batch([id_1, ..., id_20]) → 1 ユニット
  └─ 詳細を一括取得

poll_live_status() の処理:
  ├─ LIVE 関連動画：10件
  ├─ 動画 ID 10個を収集
  ├─ fetch_video_details_batch([id_1, ..., id_10]) → 1 ユニット
  └─ 詳細を一括取得

process_ended_cache_entries() の処理:
  ├─ ended キャッシュ：8件
  ├─ 動画 ID 8個を収集
  ├─ fetch_video_details_batch([id_1, ..., id_8]) → 1 ユニット
  └─ 詳細を一括取得

1ポーリングサイクルコスト: 1 + 1 + 1 = 3 ユニット ✅

削減率: 38 → 3 ユニット = **92% 削減**
```

---

## 最適化の課題

### 課題 1: API ユニット浪費

**現状**:
- 各ポーリング方法で動画ごとに `videos.list` API を呼び出し
- YouTube Data API は **1回のリクエストで最大50個の動画詳細を取得可能**なのに、1個ずつ取得していた
- 毎回 1 ユニット消費（複数動画の場合も1ユニット）

**影響**:
- 日次クォータ（10,000 ユニット）を無駄に消費
- ポーリング本数が増えるにつれてコストが線形に増加

### 課題 2: キャッシュヒット率の低さ

**現状**:
- 個別取得時にキャッシュヒット率が不十分
- バッチ取得時は複数動画を同時にキャッシュするため、ヒット率が向上

### 課題 3: ネットワーク遅延の累積

**現状**:
- 20個の動画を取得する場合、20回のラウンドトリップが必要
- バッチ処理により、最大 20回 → 1回に削減可能（50個以下の場合）

---

## 実装戦略

### 戦略の流れ

```
ステップ 1: 動画 ID リストを収集
   ├─ poll_unclassified_videos() で未分類動画の ID を集める
   ├─ poll_live_status() で upcoming/live/completed 動画の ID を集める
   └─ process_ended_cache_entries() で ended 動画の ID を集める

ステップ 2: バッチ用キャッシュラッパを呼び出し
   ├─ _get_videos_detail_with_cache_batch(video_ids)
   ├─ キャッシュにある動画を確認
   ├─ キャッシュミスの動画のみを fetch_video_details_batch() で取得
   └─ キャッシュヒット + API 結果をマージして返却

ステップ 3: 詳細データを処理（ループ）
   ├─ 分類、DB 更新、イベント発火など
   └─ 従来のロジックはそのまま（変更なし）
```

### キャッシュ戦略

**優先順序**:
1. YouTubeAPIPlugin の video_detail_cache を確認
2. キャッシュミスの動画のみ API 呼び出し
3. API 取得後、キャッシュに登録

**メリット**:
- キャッシュヒット時は API ユニット 0（全キャッシュ）
- キャッシュミスが多い場合は、複数動画を 1 ユニットで取得

---

## アーキテクチャ

### 3層構造

```
┌──────────────────────────────────────────────────────────────┐
│ YouTubeLivePoller (Layer 3: Application Logic)             │
├──────────────────────────────────────────────────────────────┤
│ poll_unclassified_videos()                                   │
│ poll_live_status()                                           │
│ process_ended_cache_entries()                                │
│                                                              │
│ ★ 動画 ID を収集 → _get_videos_detail_with_cache_batch()   │
└────────┬─────────────────────────────────────────────────────┘
         │
┌────────▼──────────────────────────────────────────────────────┐
│ YouTubeLivePoller._get_videos_detail_with_cache_batch()      │
│ (Layer 2: Cache-aware Batch Wrapper)                        │
├────────────────────────────────────────────────────────────────┤
│ 1. 動画 ID リストを受け取る                                   │
│ 2. YouTubeAPIPlugin._get_cached_video_detail() で            │
│    キャッシュを確認                                           │
│ 3. キャッシュミスの ID のみを fetch_video_details_batch()    │
│    で取得                                                      │
│ 4. キャッシュヒット + API 結果をマージして返却                 │
└────────┬─────────────────────────────────────────────────────┘
         │
┌────────▼───────────────────────────────────────────────────────┐
│ YouTubeAPIPlugin.fetch_video_details_batch()                 │
│ (Layer 1: Raw API Batch Fetcher)                            │
├───────────────────────────────────────────────────────────────┤
│ 1. video_ids を受け取る（最大50個）                           │
│ 2. 50個ずつ分割して API 呼び出し                              │
│    ├─ comma_separated_ids = ",".join(video_ids[i:i+50])     │
│    ├─ API: videos.list(id=comma_separated_ids)              │
│    └─ 1 ユニット消費                                        │
│ 3. レスポンスをキャッシュに保存                                │
│ 4. {video_id: details} を返却                               │
└───────────────────────────────────────────────────────────────┘
```

### データフロー

```
poll_unclassified_videos()
  ├─ 未分類動画を取得
  ├─ video_ids = [id_1, id_2, ..., id_N] ← 動画 ID を収集
  ├─ details_map = _get_videos_detail_with_cache_batch(video_ids)
  │  ├─ キャッシュから: {id_1: details_1, id_3: details_3}
  │  ├─ API から: {id_2: details_2, id_4: details_4} ← 1 ユニット
  │  └─ マージ: {id_1, id_2, id_3, id_4}
  └─ for video in unclassified:
     └─ details = details_map[video.video_id] ← 詳細を使用
```

---

## 実装詳細

### 1. YouTubeAPIPlugin.fetch_video_details_batch()

**ファイル**: `v3/plugins/youtube_api_plugin.py` (Line 491+)

**メソッドシグネチャ**:
```python
def fetch_video_details_batch(self, video_ids: List[str]) -> Dict[str, Dict[str, Any]]:
    """
    最大50件の動画詳細をバッチ取得（キャッシュ優先、1ユニット）

    Args:
        video_ids: 動画IDのリスト（最大50件）

    Returns:
        {video_id: details} の辞書
    """
```

**実装戦略**:
```python
# ★ ステップ 1: キャッシュを確認
for video_id in video_ids:
    cached = self._get_cached_video_detail(video_id)
    if cached:
        results[video_id] = cached  # キャッシュヒット
    else:
        to_fetch.append(video_id)   # キャッシュミス

# ★ ステップ 2: キャッシュミスを API で取得（50個ずつ）
for i in range(0, len(to_fetch), 50):
    batch = to_fetch[i:i+50]
    batch_str = ",".join(batch)  # "id1,id2,id3,...,id50"

    data = self._get(
        "videos",
        {
            "part": "snippet,contentDetails,liveStreamingDetails,status",
            "id": batch_str,  # ★ 複数 ID をカンマ区切りで指定
            "maxResults": 50,
        },
        expected_cost=1,  # 50個まで 1 ユニット
        operation=f"batch video details: {len(batch)} 件"
    )

    # ★ ステップ 3: レスポンスをキャッシュに保存
    for item in data.get("items", []):
        video_id = item.get("id")
        results[video_id] = item
        self._cache_video_detail(video_id, item)

return results  # キャッシュ + API 結果をマージ
```

**キーポイント**:
- キャッシュミスの動画のみ API 呼び出し
- 50個ずつ分割して複数バッチを処理可能（100個の動画 → 2 ユニット）
- API レスポンスを自動的にキャッシュに保存

### 2. YouTubeLivePoller._get_videos_detail_with_cache_batch()

**ファイル**: `v3/plugins/youtube_live_poller.py` (Line 164+)

**メソッドシグネチャ**:
```python
def _get_videos_detail_with_cache_batch(self, video_ids: List[str]) -> Dict[str, Dict[str, Any]]:
    """
    ★ バッチ処理用ラッパー: キャッシュ + YouTube Data API バッチ取得

    Args:
        video_ids: 取得対象の動画ID リスト

    Returns:
        {video_id: details} の辞書（キャッシュと API結果を統合）
    """
```

**実装戦略**:
```python
# ★ ステップ 1: キャッシュを確認
for video_id in video_ids:
    cached_details = self.api_plugin._get_cached_video_detail(video_id)
    if cached_details is not None:
        results[video_id] = cached_details  # キャッシュヒット
        cache_hits.append(video_id)
    else:
        cache_misses.append(video_id)       # キャッシュミス

# ★ ステップ 2: キャッシュミスを API バッチ取得
if cache_misses:
    api_results = self.api_plugin.fetch_video_details_batch(cache_misses)
    results.update(api_results)

    # ★ ステップ 3: LIVE 動画をキャッシュに登録
    for video_id, details in api_results.items():
        content_type, live_status, _ = self.classifier.classify(details)
        if content_type == "live":
            db_video = self.store.get_video_by_id(video_id)
            if db_video:
                self.store.add_live_video_to_cache(video_id, db_video, details)

return results  # 統合済みデータ
```

**キーポイント**:
- キャッシュとAPI結果を効率的にマージ
- LIVE 動画をキャッシュに自動登録
- 詳細なログ出力でキャッシュヒット率を追跡

### 3. poll_unclassified_videos() の改修

**改修内容**: ループを廃止し、バッチ処理を導入

**改修前**:
```python
for video in unclassified:
    video_id = video.get("video_id")
    details = self._get_video_detail_with_cache(video_id)  # ★ 1個ずつ
    # ...分類処理
```

**改修後**:
```python
# ★ ステップ 1: 動画 ID リストを収集
video_ids = [v.get("video_id") for v in unclassified if v.get("video_id")]

# ★ ステップ 2: バッチで詳細取得
details_map = self._get_videos_detail_with_cache_batch(video_ids)

# ★ ステップ 3: 詳細をマップから取得（ループ）
for video in unclassified:
    video_id = video.get("video_id")
    if video_id not in details_map:
        continue

    details = details_map[video_id]
    # ...分類処理（従来のロジックそのまま）
```

### 4. poll_live_status() の改修

**改修内容**: 3つの状態（upcoming, live, completed）を統合してバッチ取得

**改修前**:
```python
all_videos = upcoming_videos + live_videos + completed_videos
for video in all_videos:
    video_id = video.get("video_id")
    details = self._get_video_detail_with_cache(video_id)  # ★ 1個ずつ
    # ...状態遷移検出
```

**改修後**:
```python
# ★ ステップ 1: すべての LIVE 関連動画の ID を収集
all_videos = upcoming_videos + live_videos + completed_videos
video_ids = [v.get("video_id") for v in all_videos if v.get("video_id")]

# ★ ステップ 2: バッチで詳細取得（未分類よりコストが低い）
details_map = self._get_videos_detail_with_cache_batch(video_ids)

# ★ ステップ 3: 詳細をマップから取得（ループ）
for video in all_videos:
    video_id = video.get("video_id")
    if video_id not in details_map:
        continue

    details = details_map[video_id]
    # ...状態遷移検出（従来のロジックそのまま）
```

### 5. process_ended_cache_entries() の改修

**改修内容**: キャッシュ内の ended 動画をバッチ処理

**改修前**:
```python
for cache_entry in ended_videos:
    video_id = cache_entry.get("video_id")
    details = self._get_video_detail_with_cache(video_id)  # ★ 1個ずつ
    # ...アーカイブ化確認
```

**改修後**:
```python
# ★ ステップ 1: ended 動画の ID を収集
video_ids = [v.get("video_id") for v in ended_videos if v.get("video_id")]

# ★ ステップ 2: バッチで詳細取得
details_map = self._get_videos_detail_with_cache_batch(video_ids)

# ★ ステップ 3: 詳細をマップから取得（ループ）
for cache_entry in ended_videos:
    video_id = cache_entry.get("video_id")
    if video_id not in details_map:
        continue

    details = details_map[video_id]
    # ...アーカイブ化確認（従来のロジックそのまま）
```

---

## パフォーマンス測定

### 測定項目

#### 1. API ユニット消費

**測定方法**:
- YouTubeAPIPlugin の `daily_cost` 属性を確認
- ポーリング前後の差分を計算

**ログ出力**:
```
✅ API コスト（1ポーリングサイクル）
   未分類: 1 ユニット（20動画を バッチ取得）
   LIVE: 1 ユニット（10動画を バッチ取得）
   ended: 1 ユニット（8動画を バッチ取得）
   合計: 3 ユニット
```

#### 2. キャッシュヒット率

**測定方法**:
```
キャッシュヒット率 = (キャッシュヒット数) / (全動画数) * 100%

例:
   video_ids = [id_1, ..., id_20]
   キャッシュ確認: 12個がキャッシュに存在
   キャッシュミス: 8個が API から取得
   ヒット率 = 12 / 20 = 60%
```

**ログ出力**:
```
📦 バッチ処理: キャッシュヒット=12, API取得=8
   ヒット率: 60%
```

#### 3. ネットワーク遅延削減

**測定方法**:
- ポーリング処理の実行時間を記録
- API 呼び出し回数を記録

**効果**:
```
個別取得（20動画）:
   API 呼び出し: 20回（キャッシュミス時）
   ネットワークラウンドトリップ: 20回

バッチ取得（20動画）:
   API 呼び出し: 1回（50個以下の場合）
   ネットワークラウンドトリップ: 1回

削減: 20回 → 1回（95%削減）
```

### シナリオ別コスト試算

#### シナリオ 1: キャッシュが完全にヒットする場合

```
未分類: 20動画（前回ポーリングで取得済み）
   キャッシュヒット: 20/20
   API コスト: 0 ユニット

LIVE: 10動画（キャッシュから取得）
   キャッシュヒット: 10/10
   API コスト: 0 ユニット

ended: 8動画
   キャッシュヒット: 8/8
   API コスト: 0 ユニット

1ポーリングサイクル合計: 0 ユニット（理想的）
```

#### シナリオ 2: キャッシュがすべてミスする場合（初期状態）

```
未分類: 20動画
   キャッシュ: 0/20
   API: 20動画 → 50個以下 → 1 ユニット

LIVE: 10動画
   キャッシュ: 0/10
   API: 10動画 → 50個以下 → 1 ユニット

ended: 8動画
   キャッシュ: 0/8
   API: 8動画 → 50個以下 → 1 ユニット

1ポーリングサイクル合計: 3 ユニット（最大コスト）
```

#### シナリオ 3: キャッシュ混在（現実的）

```
未分類: 20動画
   キャッシュ: 10/20
   API: 10動画 → 1 ユニット

LIVE: 10動画
   キャッシュ: 8/10
   API: 2動画 → 1 ユニット

ended: 8動画
   キャッシュ: 5/8
   API: 3動画 → 1 ユニット

1ポーリングサイクル合計: 3 ユニット
```

**注**: 実装では、キャッシュミスの動画のみ API 呼び出しするため、
複数のバッチをまとめて 1 API 呼び出しで処理可能。

#### シナリオ 4: 大規模監視（100動画以上）

```
未分類: 100動画
   API: 100動画 → 50個ずつ 2バッチ → 2 ユニット

LIVE: 50動画
   API: 50動画 → 1バッチ → 1 ユニット

ended: 30動画
   API: 30動画 → 1バッチ → 1 ユニット

1ポーリングサイクル合計: 4 ユニット（効率的）
```

---

## ログ出力

### 詳細ログの例

#### poll_unclassified_videos() のログ

```
[DEBUG] 📦 バッチ処理開始: 未分類 20 件
[DEBUG] 💾 キャッシュヒット: video_id_1
[DEBUG] 💾 キャッシュヒット: video_id_2
[DEBUG] ...
[DEBUG] 📦 バッチ処理: キャッシュヒット=10, API取得=10
[DEBUG] 🔍 キャッシュ外の動画を API から取得: 10 件
[DEBUG] 📦 全動画がキャッシュから取得されました: 10 件
[DEBUG] 💾 キャッシュ登録: video_id_11 (バッチ API)
[DEBUG] 💾 キャッシュ登録: video_id_12 (バッチ API)
[DEBUG] ...
[INFO] ✅ API コスト（バッチ）: 1 ユニット / 10 動画
[INFO] ✅ 分類完了: video_id_1 → video/None
[INFO] ✅ 分類完了: video_id_2 → live/upcoming
[INFO] ...
[INFO] 📋 未分類動画分類完了: 20/20件
```

#### poll_live_status() のログ

```
[DEBUG] 📊 ポーリング対象: upcoming=5, live=3, completed=2
[DEBUG] 📦 バッチ処理開始: LIVE 動画 10 件
[DEBUG] 📦 バッチ処理: キャッシュヒット=8, API取得=2
[DEBUG] ✅ API コスト（バッチ）: 1 ユニット / 2 動画
[INFO] 🔴 ライブ配信開始を検出: video_id_upcoming_1
[INFO] 🔴 ライブ配信終了を検出: video_id_live_1
[INFO] ...
[INFO] ✅ ポーリング完了: total=10, started=2, ended=1, archived=0, changed=3
```

#### process_ended_cache_entries() のログ

```
[INFO] 📋 ended キャッシュエントリ処理: 8個
[DEBUG] 📦 バッチ処理開始: ended 動画 8 件
[DEBUG] 📦 バッチ処理: キャッシュヒット=3, API取得=5
[INFO] 📹 アーカイブ化を検出: video_id_ended_1
[INFO] 📹 アーカイブ化を検出: video_id_ended_2
[INFO] ...
[INFO] ✅ ended 処理完了: 5/8個
```

### API コスト追跡ログ

```
[INFO] ✅ API コスト（YouTubeLive ポーリング）
   未分類: 1 ユニット
   LIVE: 1 ユニット
   ended: 1 ユニット
   本日の合計: 15 ユニット / 10000
```

---

## トラブルシューティング

### 症状 1: API ユニットが削減されない

**原因**: キャッシュミスが多い、またはバッチ処理が実行されていない

**対応**:
1. ログを確認: `📦 バッチ処理: キャッシュヒット=`
2. キャッシュヒット率が 0 の場合は、キャッシュ初期化直後の可能性
3. 複数ポーリングサイクル後に、ヒット率が向上することを確認

### 症状 2: 詳細データが取得できない

**原因**: API エラー、またはネットワーク問題

**対応**:
1. ログで API エラーを確認: `❌ バッチ API 呼び出しエラー`
2. YouTube API クォータを確認
3. API キーが有効か確認

### 症状 3: キャッシュに登録されない

**原因**: キャッシュマネージャーがない、または LIVE 動画がない

**対応**:
1. ログを確認: `⚠️ キャッシュ登録スキップ`
2. LIVE 動画が存在するか確認
3. キャッシュマネージャーが初期化されているか確認

---

## 検証チェックリスト

- ✅ `_get_videos_detail_with_cache_batch()` メソッド実装
- ✅ `poll_unclassified_videos()` をバッチ処理に改修
- ✅ `poll_live_status()` をバッチ処理に改修
- ✅ `process_ended_cache_entries()` をバッチ処理に改修
- ✅ 既存の分類・状態遷移ロジックは変更なし
- ✅ ログ出力でバッチ処理を追跡可能
- ✅ API ユニット削減を検証

---

## 今後の改善予定

1. **動的キャッシュ有効期限**: API から取得した動画の状態が頻繁に変わる場合の検出
2. **キャッシュウォーミング**: 起動時に頻繁にアクセスされる動画をプリロード
3. **API エラー時のリトライ**: バッチ処理失敗時の個別フォールバック

---

**作成日**: 2025-12-27
**最後の修正**: 2025-12-27
**ステータス**: ✅ 完成・検証済み
