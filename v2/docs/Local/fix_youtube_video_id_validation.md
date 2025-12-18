# YouTube Video ID 形式検証の実装

**実装日**: 2025-12-18
**対象**: v2/plugins/youtube_api_plugin.py, v2/plugins/youtube_live_plugin.py
**ステータス**: ✅ 完了

---

## 🎯 実装内容

### 問題
Niconico の動画ID（`sm45414087`）が YouTube Plugin に渡されて API 呼び出しに失敗し、エラーログノイズとクォータ無駄遣いが発生していた。

### 解決方針
**短期対策**: YouTubePlugin に video_id 形式検証を追加し、YouTube 形式以外をスキップ

---

## 🔧 実装変更

### 1. YouTubeAPIPlugin

**ファイル**: `v2/plugins/youtube_api_plugin.py`

#### 変更 1-1: post_video() に検証を追加

```python
def post_video(self, video: Dict[str, Any]) -> bool:
    """動画情報を取得し、分類結果付きで DB に保存"""
    video_id = video.get("video_id") or video.get("id")
    if not video_id:
        logger.error("❌ YouTube API: video_id が指定されていません")
        return False

    # YouTube ID 形式の検証（Niconico など他形式のスキップ）
    if not self._is_valid_youtube_video_id(video_id):
        logger.debug(f"⏭️ YouTube API: YouTube 形式ではない video_id をスキップ: {video_id}")
        return True  # エラーではなく「対応不可」として True を返す

    details = self._fetch_video_detail(video_id)
    # ... 以下既存ロジック
```

**ポイント**:
- YouTube 形式でない場合、`True` を返す（成功ではなく「対応不可」）
- エラーログではなく `DEBUG` レベルのログで記録
- API 呼び出し前に検証するため、不要なクォータ消費を防止

#### 変更 1-2: _is_valid_youtube_video_id() メソッドを追加

```python
def _is_valid_youtube_video_id(self, video_id: str) -> bool:
    """
    YouTube 動画ID 形式の検証

    YouTube 動画ID は 11 文字の英数字（A-Z, a-z, 0-9, -, _）
    例: dQw4w9WgXcQ

    Niconico ID（sm45414087）など他形式は False を返す

    Args:
        video_id: 検証対象の ID

    Returns:
        True: YouTube 形式, False: 他の形式（Niconico など）
    """
    import re
    # YouTube 動画ID: 11 文字、A-Za-z0-9-_
    if re.match(r'^[A-Za-z0-9_-]{11}$', video_id):
        return True
    return False
```

**検証ルール**:
- 11 文字の英数字
- 使用可能文字: A-Z, a-z, 0-9, -, _
- 例: `dQw4w9WgXcQ` ✅、`sm45414087` ❌

---

### 2. YouTubeLivePlugin

**ファイル**: `v2/plugins/youtube_live_plugin.py`

#### 変更 2-1: post_video() に検証を追加

```python
def post_video(self, video: Dict[str, Any]) -> bool:
    """
    ライブ/アーカイブ判定を行い DB に保存
    ...
    """
    video_id = video.get("video_id") or video.get("id")
    if not video_id:
        logger.error("❌ YouTube Live: video_id が指定されていません")
        return False

    # YouTube ID 形式の検証（Niconico など他形式のスキップ）
    if not self._is_valid_youtube_video_id(video_id):
        logger.debug(f"⏭️ YouTube Live: YouTube 形式ではない video_id をスキップ: {video_id}")
        return True  # エラーではなく「対応不可」として True を返す

    # API プラグインの _fetch_video_detail() を使用
    # キャッシュ・クォータ管理は api_plugin が担当
    details = self.api_plugin._fetch_video_detail(video_id)
    # ... 以下既存ロジック
```

#### 変更 2-2: _is_valid_youtube_video_id() メソッドを追加

YouTubeAPIPlugin と同じ検証ロジック（重複排除は中期対策で予定）

---

## ✅ 修正の効果

### Before（修正前）

```
ユーザーが Niconico 動画を投稿選択
    ↓
plugin_manager.post_video_with_all_enabled(video)
    ↓
YouTubeAPIPlugin.post_video(sm45414087)
    → API 呼び出し ❌ 失敗
    → エラーログ出力: "❌ YouTube API: 動画詳細取得に失敗しました: sm45414087"
    → クォータ 1 ユニット消費
    ↓
YouTubeLivePlugin.post_video(sm45414087)
    → API 呼び出し ❌ 失敗
    → エラーログ出力: "❌ YouTube Live: 動画詳細取得に失敗しました: sm45414087"
    → クォータ 1 ユニット消費
    ↓
(NiconicoPlugin, BlueskyPlugin は正常処理)
```

**コスト**: 2 ユニット/投稿（無駄）

### After（修正後）

```
ユーザーが Niconico 動画を投稿選択
    ↓
plugin_manager.post_video_with_all_enabled(video)
    ↓
YouTubeAPIPlugin.post_video(sm45414087)
    → 形式検証: sm45414087 は YouTube 形式ではない ❌
    → True を返す（対応不可）
    → DEBUG ログ出力: "⏭️ YouTube API: YouTube 形式ではない video_id をスキップ: sm45414087"
    → API 呼び出しなし、クォータ消費なし ✅
    ↓
YouTubeLivePlugin.post_video(sm45414087)
    → 形式検証: sm45414087 は YouTube 形式ではない ❌
    → True を返す（対応不可）
    → DEBUG ログ出力: "⏭️ YouTube Live: YouTube 形式ではない video_id をスキップ: sm45414087"
    → API 呼び出しなし、クォータ消費なし ✅
    ↓
(NiconicoPlugin, BlueskyPlugin は正常処理)
```

**コスト**: 0 ユニット/投稿（無駄排除） ✅

---

## 📊 改善指標

| 項目 | Before | After | 改善度 |
|------|--------|-------|------|
| クォータ消費（1 Niconico 投稿） | 2 ユニット | 0 ユニット | **100% 削減** |
| エラーログノイズ | 毎回発生 | なし | **完全排除** |
| 処理時間 | API タイムアウト待機 | 即座に判定 | **大幅短縮** |

---

## 🧪 動作検証

### テストケース

#### TC-1: YouTube ID（有効）

```python
video_id = "dQw4w9WgXcQ"  # 有効な YouTube ID
result = plugin._is_valid_youtube_video_id(video_id)
# Expected: True ✅
# 動作: API 呼び出しを実行
```

#### TC-2: Niconico ID

```python
video_id = "sm45414087"  # Niconico ID
result = plugin._is_valid_youtube_video_id(video_id)
# Expected: False ✅
# 動作: スキップ（True を返す）
```

#### TC-3: 不正な形式（短い）

```python
video_id = "abc123"  # 6 文字（不正）
result = plugin._is_valid_youtube_video_id(video_id)
# Expected: False ✅
# 動作: スキップ（True を返す）
```

#### TC-4: 空文字列

```python
video_id = ""  # 空文字列
result = plugin._is_valid_youtube_video_id(video_id)
# Expected: False ✅
# 動作: post_video() の前の段階で error を返す
```

---

## 📋 中期対策への展望

本実装は **短期対策** です。以下が中期対策で検討予定：

1. **コード重複排除**
   - 共通メソッド `_is_valid_youtube_video_id()` を plugin_manager または共有モジュールに統合
   - YouTubeAPIPlugin と YouTubeLivePlugin が同じ実装を使用

2. **プラットフォーム判定の一元化**
   - `get_supported_platforms()` を plugin_interface に追加
   - plugin_manager で platform ベースの判定

3. **DB schema 強化**
   - platform フィールドを必須化
   - GUI から post_video_with_all_enabled() 呼び出し時に platform を確実に渡す

---

## 参考

- **エラー調査報告書**: v2/docs/local/error_investigation_sm45414087.md
- **YouTube ID 形式**: [YouTube Data API - Video Resource](https://developers.google.com/youtube/v3/docs/videos)
  - Video ID: 11 文字の英数字（A-Z, a-z, 0-9, -, _）
