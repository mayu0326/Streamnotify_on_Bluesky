# YouTube Live 判定ロジック整理・実装計画

**作成日**: 2025-12-18
**対象バージョン**: v3
**ステータス**: 計画段階

---

## 📋 現状分析

### 既存実装の状態

#### 1. YouTubeAPIPlugin._classify_video()（v3/plugins/youtube_api_plugin.py）
- `snippet.liveBroadcastContent` で第一判定
- `liveStreamingDetails` 存在時、タイムスタンプ（actualEndTime → actualStartTime → scheduledStartTime）で優先判定
- プレミア判定ロジックがある
- **ただし、仕様に記載されたコメントが不足している**

#### 2. YouTubeLivePlugin._classify_live()（v3/plugins/youtube_live_plugin.py）
- `_classify_video()` と完全に同じロジック
- 意図的な重複（プラグイン独立性）と見られるが、保守性に課題

#### 3. sync_live_events()（YouTubeLivePlugin）
- search.list で `eventType="live" | "completed"` の動画IDを取得
- 各ID を `post_video()` に渡す
- **高コスト（100ユニット/回）の注意がコメントとして存在**

---

## ✅ 判定仕様の適合性確認

提供仕様と現在のコードを比較して、**ほぼ一致している** ことを確認：

| 項目 | 現行コード | 仕様への適合 |
|------|---------|-----------|
| `content_type` の 3 値 | ✓ | 完全一致 |
| `live_status` の 4 値 | ✓ | 完全一致 |
| `is_premiere` フラグ | ✓ | 完全一致 |
| API フィールド読み取り | ✓ | 完全一致 |
| 判定優先順序 | ✓ | 完全一致 |

**結論**: ロジックは既に仕様に沿っている。主な作業は「コメント充実」と「重複排除」。

---

## 🔧 判定フロー仕様（参照）

### フィールド定義

各動画について、以下の 3 つのフィールドで種別を表現：

- **`content_type`**: `"video" | "live" | "archive"`
  - `"video"`: 通常動画（プレミア公開後を含む）
  - `"live"`: ライブ配信（現在ライブ中 or 予約枠）
  - `"archive"`: ライブ配信のアーカイブ

- **`live_status`**: `None | "upcoming" | "live" | "completed"`
  - `None`: 通常動画（ライブ関連ではない）
  - `"upcoming"`: 予約済みライブ（まだ開始前）
  - `"live"`: 配信中のライブ
  - `"completed"`: 配信終了後のアーカイブ

- **`is_premiere`**: `bool`
  - `True`: プレミア公開系のコンテンツ（プレミア前枠・プレミア済み動画を含む）
  - `False`: それ以外

### 使用する YouTube Data API フィールド

`videos.list` のレスポンスから以下を使用：

```
- snippet.liveBroadcastContent
  値: "none" | "live" | "upcoming"

- liveStreamingDetails
  ├─ actualStartTime
  ├─ actualEndTime
  └─ scheduledStartTime

- status.uploadStatus
  値: "uploaded" | "processed" | "live" など
```

### 判定ロジック（仕様 1-6）

#### 仕様 1. 基本のフロー

```python
snippet = details.get("snippet", {})
status = details.get("status", {})
live = details.get("liveStreamingDetails", {})
broadcast_type = snippet.get("liveBroadcastContent", "none")
```

#### 仕様 2. 通常動画（live ではない）

- **条件**:
  - `broadcast_type == "none"` かつ `liveStreamingDetails` が存在しない、または
  - 最終的にどのライブ条件にもマッチしない場合

- **結果**:
  - `content_type = "video"`
  - `live_status = None`
  - `is_premiere = False`（※プレミア判定に該当する場合のみ True にする）

#### 仕様 3. プレミア公開の判定

- **条件**:
  - `live` が存在し、かつ
  - `status.uploadStatus == "processed"` で、
  - `broadcast_type in ("live", "upcoming")`

- **結果**:
  - `is_premiere = True`

- **プレミアの時間状態に応じた扱い**:
  - プレミア公開前の予約枠 → `content_type="live"`, `live_status="upcoming"`, `is_premiere=True`
  - プレミア公開中 → `content_type="live"`, `live_status="live"`, `is_premiere=True`
  - プレミア公開後（通常の動画化） → `content_type="video"`, `live_status=None`, `is_premiere=True`

#### 仕様 4. ライブ／アーカイブの時間的状態

`liveStreamingDetails` が存在する場合、次の優先順位で判定：

**4-1. `live.actualEndTime` が存在する場合**
- 配信終了済みのアーカイブ
- `content_type = "archive"`
- `live_status = "completed"`

**4-2. `actualEndTime` は無く `actualStartTime` が存在する場合**
- 現在ライブ中
- `content_type = "live"`
- `live_status = "live"`

**4-3. `actualStartTime` も無く `scheduledStartTime` が存在する場合**
- 予約済みライブ
- `content_type = "live"`
- `live_status = "upcoming"`

このとき、仕様 3 のプレミア判定に該当する場合は、`is_premiere=True` をセット。

#### 仕様 5. `liveStreamingDetails` が無いが `liveBroadcastContent` が live/upcoming の場合

フォールバック判定（liveStreamingDetails 欠落ケース）：

- `broadcast_type == "live"`:
  - `content_type = "live"`
  - `live_status = "live"`

- `broadcast_type == "upcoming"`:
  - `content_type = "live"`
  - `live_status = "upcoming"`

#### 仕様 6. デフォルト（その他）

上記いずれにも該当しない場合：

- `content_type = "video"`
- `live_status = None`
- `is_premiere = False`

---

## 📝 実装計画

### Step 1: YouTubeAPIPlugin._classify_video() の整理

**ファイル**: `v3/plugins/youtube_api_plugin.py`

#### 実施内容

1. 現在の `_classify_video()` を `_classify_video_core()` に改名
2. `_classify_video()` は `_classify_video_core()` をラッパーとして呼び出す
3. 各 if ブロックに仕様番号付き日本語コメントを追加
4. 戻り値と例を docstring に明記

#### 擬似コード（実装イメージ）

```python
def _classify_video_core(self, details: Dict[str, Any]) -> Tuple[str, Optional[str], bool]:
    """
    動画分類ロジック（仕様 1-6 に準拠）

    判定フロー:
      1. liveBroadcastContent を読み取り → broadcast_type
      2. liveStreamingDetails の有無を確認
      3. プレミア条件（uploadStatus == "processed" + broadcast_type in live/upcoming）
      4. タイムスタンプ優先順位で時間状態を判定
      5. フォールバック

    Returns:
        (content_type, live_status, is_premiere)
        - content_type: "video" | "live" | "archive"
        - live_status: None | "upcoming" | "live" | "completed"
        - is_premiere: bool

    Examples:
        ライブ中:          ("live", "live", False)
        プレミア予約:       ("live", "upcoming", True)
        アーカイブ:        ("archive", "completed", False)
        通常動画:         ("video", None, False)
    """
    # 仕様 1. 基本のフロー
    snippet = details.get("snippet", {})
    status = details.get("status", {})
    live = details.get("liveStreamingDetails", {})
    broadcast_type = snippet.get("liveBroadcastContent", "none")

    # 仕様 2. 通常動画判定
    if broadcast_type == "none" and not live:
        return "video", None, False

    # 仕様 3. プレミア公開の判定
    is_premiere = False
    if live and status.get("uploadStatus") == "processed" and broadcast_type in ("live", "upcoming"):
        is_premiere = True

    # 仕様 4. ライブ/アーカイブの時間的状態判定
    # 優先順位: actualEndTime > actualStartTime > scheduledStartTime
    if live:
        # 4-1: actualEndTime が存在 → アーカイブ（配信終了済み）
        if live.get("actualEndTime"):
            return "archive", "completed", is_premiere
        # 4-2: actualStartTime が存在（actualEndTime なし） → ライブ中
        elif live.get("actualStartTime"):
            return "live", "live", is_premiere
        # 4-3: scheduledStartTime が存在（actualStartTime なし） → 予約済みライブ
        elif live.get("scheduledStartTime"):
            return "live", "upcoming", is_premiere

    # 仕様 5. liveStreamingDetails が無い場合のフォールバック
    if broadcast_type == "live":
        return "live", "live", is_premiere
    elif broadcast_type == "upcoming":
        return "live", "upcoming", is_premiere

    # 仕様 6. デフォルト（その他いずれにも該当しない）
    return "video", None, False


def _classify_video(self, details: Dict[str, Any]) -> Tuple[str, Optional[str], bool]:
    """
    公開 API: 動画分類ロジック

    _classify_video_core() のラッパー。
    外部プラグインからの呼び出しに対応。
    """
    return self._classify_video_core(details)
```

---

### Step 2: YouTubeLivePlugin._classify_live() の整理

**ファイル**: `v3/plugins/youtube_live_plugin.py`

#### 実施内容

1. `_classify_live()` を修正：`self.api_plugin._classify_video_core()` を呼び出すように変更
2. コメントを以下の内容に統一：
   - 「YouTubeAPIPlugin の共通分類ロジックを利用」
   - 仕様参照番号（1-6）を付与

#### 擬似コード（実装イメージ）

```python
def _classify_live(self, details: Dict[str, Any]) -> Tuple[str, Optional[str], bool]:
    """
    ライブ/アーカイブ分類（YouTubeAPIPlugin の共通ロジックを利用）

    仕様 1-6 に基づいて、(content_type, live_status, is_premiere) を返す。

    詳細な判定ロジックは api_plugin._classify_video_core() を参照。

    Returns:
        (content_type, live_status, is_premiere)

    Examples:
        ライブ中:          ("live", "live", False)
        プレミア予約:       ("live", "upcoming", True)
        アーカイブ:        ("archive", "completed", False)
        通常動画:         ("video", None, False)
    """
    # YouTubeAPIPlugin の共通分類ロジック（仕様 1-6）を利用
    return self.api_plugin._classify_video_core(details)
```

---

### Step 3: sync_live_events() のコメント充実

**ファイル**: `v3/plugins/youtube_live_plugin.py`

#### 実施内容

既存コメント（簡潔）を以下に拡張：

```python
def sync_live_events(self) -> None:
    """
    ライブ/アーカイブ一覧を取得しDBへ反映（search.list = 100ユニット/回）

    ⚠️ 重要な制限事項：
      - search.list は非常に高コスト（100ユニット/回）
      - 日次クォータ（10,000ユニット）から考えると、本メソッドは最大 100 回程度しか実行できない
      - 本番運用では以下の対策が必須：

    📋 推奨される対策：
      1. スケジューリング: 1日1回程度など、呼び出し頻度を制限
      2. キャッシング: 最後の実行日時を記録し、重複呼び出しを避ける
      3. モニタリング: 日次コスト管理で過度な呼び出しを検知

    参考: YouTube Data API v3 クォータ配分
      - 日次上限: 10,000ユニット
      - search.list: 100ユニット/回
      - videos.list: 1ユニット/回
    """
    live_ids = self._fetch_live_video_ids(event_type="live")
    archive_ids = self._fetch_live_video_ids(event_type="completed")

    for vid in live_ids:
        self.post_video({"video_id": vid})
    for vid in archive_ids:
        self.post_video({"video_id": vid})
```

---

### Step 4: _fetch_live_video_ids() のコメント充実

**ファイル**: `v3/plugins/youtube_live_plugin.py`

#### 実施内容

既存コメントを以下に拡張：

```python
def _fetch_live_video_ids(self, event_type: str) -> List[str]:
    """
    ライブイベント一覧を検索（search.list = 100ユニット/回）

    Args:
        event_type: "live" (ライブ中) または "completed" (配信終了)

    Returns:
        動画IDのリスト

    ⚠️ 高コスト操作：
      - search.list は 1回あたり 100ユニット消費
      - 代替手段が無いため、使用は慎重に
      - 本番運用では sync_live_events() への呼び出し頻度を制限すること

    注意: api_plugin のクォータ管理を迂回するため、ここで直接 API 呼び出しを行う。
          理想的には、今後 api_plugin._get() を拡張して search.list に対応させるべき。
    """
    params = {
        "part": "id",
        "channelId": self.channel_id,
        "eventType": event_type,
        "type": "video",
        "order": "date",
        "maxResults": 10,
        "key": self.api_key,
    }
    try:
        logger.debug(f"🔍 ライブ一覧検索: {event_type} (search.list = 100ユニット)")
        resp = self.session.get(f"{API_BASE}/search", params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        items = data.get("items", []) if data else []
        video_ids = [item.get("id", {}).get("videoId") for item in items if item.get("id", {}).get("videoId")]
        logger.info(f"✅ ライブ一覧取得成功: {len(video_ids)} 件 ({event_type})")
        return video_ids
    except requests.exceptions.Timeout:
        logger.warning(f"⏱️ タイムアウト: ライブ一覧取得 ({event_type})")
        return []
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ ライブ一覧取得エラー ({event_type}): {e}")
        return []
```

---

## 📊 ファイル修正対象・優先度一覧

| # | ファイル | メソッド/処理 | 修正内容 | 優先度 |
|---|---------|-----------|--------|------|
| 1 | `youtube_api_plugin.py` | `_classify_video_core()` (新規) | 仕様 1-6 実装、コメント充実 | 🔴 高 |
| 2 | `youtube_api_plugin.py` | `_classify_video()` | `_classify_video_core()` を呼び出すラッパー化 | 🔴 高 |
| 3 | `youtube_live_plugin.py` | `_classify_live()` | `api_plugin._classify_video_core()` 呼び出しに変更 | 🔴 高 |
| 4 | `youtube_live_plugin.py` | `sync_live_events()` | コメント拡張（クォータ注意） | 🟡 中 |
| 5 | `youtube_live_plugin.py` | `_fetch_live_video_ids()` | コメント拡張（高コスト警告） | 🟡 中 |

---

## 🎯 期待するアウトプット（完成形）

実装完了後、以下が達成される：

✅ **仕様準拠性**
- YouTubeAPIPlugin._classify_video_core() が仕様 1-6 に完全準拠
- YouTubeLivePlugin._classify_live() が共通ロジックを利用

✅ **保守性**
- 各判定ブロックに仕様番号コメント（`## 仕様 N`）を付与
- 1年後も判定意図が分かるレベルのドキュメント

✅ **コード重複排除**
- YouTubeAPIPlugin と YouTubeLivePlugin の判定ロジックが一元化
- バグ修正時の二重修正が不要に

✅ **クォータ管理の透明性**
- search.list の高コスト（100ユニット/回）が明記
- スケジューリング・キャッシング対策の指針が記載

---

## 🚀 実装進行状況（チェックリスト）

- [ ] `_classify_video_core()` を `youtube_api_plugin.py` に実装
- [ ] `_classify_video()` を `_classify_video_core()` のラッパーに変更
- [ ] `_classify_live()` を `api_plugin._classify_video_core()` 呼び出しに変更
- [ ] `sync_live_events()` にコメント追加
- [ ] `_fetch_live_video_ids()` にコメント追加
- [ ] コード動作検証（既存ユニットテストがあれば実行）
- [ ] 実装完了確認

---

## � 制約事項：Niconico Live（ニコニコ生放送）は実装不可

**ステータス**: ❌ **技術的に実装不可（RSS では情報提供されていない）**

ニコニコ動画の RSS フィード（`https://www.nicovideo.jp/user/{USER_ID}/video?rss=2.0`）は**録画済み動画のみ**を提供するため：

- ✅ YouTube Live テンプレート: **実装可能**（YouTube Data API に `liveStreamingDetails` 存在）
- ❌ Niconico Live テンプレート: **実装不可**（RSS に情報なし、公開 API なし）

ライブ配信情報取得には、HTML スクレイピングか非公開 API の利用が必要となり、いずれも不安定・非推奨のため、本実装では対応しません。

---

## �📚 参考資料

- **API 仕様**: `v3/plugins/youtube_api_plugin.py` に埋め込まれたクォータ情報
- **プラグイン interface**: `v3/plugin_interface.py`
- **DB スキーマ**: `v3/database.py` の `insert_video()` メソッド

