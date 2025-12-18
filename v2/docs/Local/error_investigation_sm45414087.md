# エラー調査報告書：Niconico ID が YouTube Plugin に渡される問題

**調査日**: 2025-12-18  
**エラー内容**: `sm45414087` (Niconico 動画ID) が YouTube API Plugin に渡され、API 呼び出しに失敗

---

## 🔍 問題の特定

### エラーログの再現

```
2025-12-18 07:30:17,642 [ERROR] ❌ YouTube API: 動画詳細取得に失敗しました: sm45414087
2025-12-18 07:30:18,093 [ERROR] ❌ YouTube Live: 動画詳細取得に失敗しました: sm45414087
```

### データ流の追跡

ログから、以下のフローが確認されます：

```
GUI で Niconico 動画を選択
  ↓
plugin_manager.post_video_with_all_enabled(video) が呼ばれる
  ↓
すべての有効なプラグインに動画情報が渡される
  ├─ YouTubeAPIPlugin.post_video(video) ← sm45414087 を受け取る ❌ 失敗
  ├─ YouTubeLivePlugin.post_video(video) ← sm45414087 を受け取る ❌ 失敗
  ├─ NiconicoPlugin.post_video(video) ← sm45414087 を受け取る ✅ 成功
  └─ BlueskyPlugin.post_video(video) ← sm45414087 を受け取る ✅ 成功（投稿ログ確認）
```

### ログから見える実行状況

**post.log より**:
```
2025-12-18 07:30:18,093 [INFO] 🔍 post_video 開始: use_image=True, resize_small_images=True, image_filename=sm45414087.jpeg
2025-12-18 07:30:18,093 [INFO] 💾 DB登録済み画像を使用: sm45414087.jpeg
2025-12-18 07:30:20,956 [INFO] 投稿済みフラグを更新しました: sm45414087 (投稿日時: 2025-12-18 07:30:20)
```

→ **Bluesky への投稿は成功している**

**error.log より**:
```
2025-12-18 07:30:17,642 [ERROR] ❌ YouTube API: 動画詳細取得に失敗しました: sm45414087
2025-12-18 07:30:18,093 [ERROR] ❌ YouTube Live: 動画詳細取得に失敗しました: sm45414087
```

→ **YouTube Plugin が Niconico ID を処理しようとして失敗**

---

## 🎯 根本原因

### 問題の本質

**`YouTubeAPIPlugin.post_video()` に video_id 形式の検証がないため、Niconico の動画ID（`sm45414087`）を受け取ると YouTube API 呼び出しを試みて失敗する。**

### コード分析

**v2/plugins/youtube_api_plugin.py, lines 87-98:**

```python
def post_video(self, video: Dict[str, Any]) -> bool:
    """動画情報を取得し、分類結果付きで DB に保存"""
    video_id = video.get("video_id") or video.get("id")
    if not video_id:
        logger.error("❌ YouTube API: video_id が指定されていません")
        return False

    details = self._fetch_video_detail(video_id)  # ← ★ 検証なし
    if not details:
        logger.error(f"❌ YouTube API: 動画詳細取得に失敗しました: {video_id}")
        return False
    # ... (以降の処理)
```

**問題点**:
1. video_id の形式チェックがない
2. YouTube ID 形式（11文字の英数字）であることを確認していない
3. Niconico ID（`sm[数字]`）や他形式の ID が渡されても、API 呼び出しを試みる
4. 失敗してエラーログを出すだけで、その後のリソース無駄遣いを防いでいない

---

## 📊 設計上の欠陥

### 問題 1: 呼び出し側の実装

**v2/plugin_manager.py, lines 214-240:**

```python
def post_video_with_all_enabled(self, video: dict, dry_run: bool = False) -> Dict[str, bool]:
    """
    すべての有効なプラグインで動画をポスト
    """
    results = {}

    for plugin_name, plugin in self.enabled_plugins.items():
        try:
            # ★ dry_run フラグをプラグインに設定
            if hasattr(plugin, 'set_dry_run'):
                plugin.set_dry_run(dry_run)

            success = plugin.post_video(video)  # ← ★ プラグインが対応するかどうか確認なし
            results[plugin_name] = success
            # ...
```

**欠陥**:
- すべての有効なプラグインに同じ video データを渡している
- プラグインが対応する platform / video_id 形式を確認していない
- 各プラグインが「自分で処理できるか」を自律的に判定している（本来は呼び出し側が判定すべき）

### 問題 2: プラグイン側の防御不足

**YouTubeAPIPlugin / YouTubeLivePlugin:**
- video_id の形式検証がない
- 「自分が対応できる形式かどうか」の事前チェックなし
- Niconico ID を受け取ると、無条件に YouTube API 呼び出しを試みる

**一方、NiconicoPlugin:**
- 同じ問題が無い（Niconico ID 形式だけを処理する）

---

## ✅ 解決策

### 短期対策：YouTubePlugin に video_id 検証を追加

**YouTubeAPIPlugin.post_video() に以下の検証を追加:**

```python
def post_video(self, video: Dict[str, Any]) -> bool:
    """動画情報を取得し、分類結果付きで DB に保存"""
    video_id = video.get("video_id") or video.get("id")
    if not video_id:
        logger.error("❌ YouTube API: video_id が指定されていません")
        return False

    # ★ 追加: YouTube ID 形式の検証
    if not self._is_valid_youtube_video_id(video_id):
        logger.debug(f"⏭️ YouTube API: YouTube 形式ではない video_id をスキップ: {video_id}")
        return True  # False でなく True を返す（エラーではなく「対応不可」）

    details = self._fetch_video_detail(video_id)
    if not details:
        logger.error(f"❌ YouTube API: 動画詳細取得に失敗しました: {video_id}")
        return False
    # ...


def _is_valid_youtube_video_id(self, video_id: str) -> bool:
    """
    YouTube 動画ID 形式の検証
    
    YouTube 動画ID: 11 文字の英数字（A-Z, a-z, 0-9, -_）
    例: dQw4w9WgXcQ
    
    Niconico ID は返す: sm45414087 など
    """
    import re
    # YouTube 動画ID: 11 文字、A-Za-z0-9-_
    if re.match(r'^[A-Za-z0-9_-]{11}$', video_id):
        return True
    return False
```

### 中期対策：プラグインマネージャーにプラットフォーム判定を追加

**プラグイン側に platform を明示させる:**

```python
# plugin_interface.py に追加
class NotificationPlugin(ABC):
    @abstractmethod
    def get_supported_platforms(self) -> List[str]:
        """
        このプラグインが対応するプラットフォーム
        
        Returns:
            プラットフォーム名のリスト
            例: ["YouTube", "YouTube Live"]
        
        デフォルト（オーバーライドなし）: None （すべてのプラットフォームに対応）
        """
        return None  # デフォルトはすべてに対応


# プラグイン実装側
class YouTubeAPIPlugin(NotificationPlugin):
    def get_supported_platforms(self) -> List[str]:
        return ["YouTube"]

class NiconicoPlugin(NotificationPlugin):
    def get_supported_platforms(self) -> List[str]:
        return ["Niconico"]

class BlueskyPlugin(NotificationPlugin):
    def get_supported_platforms(self) -> List[str]:
        return None  # すべてのプラットフォームに対応
```

**プラグインマネージャーで判定:**

```python
def post_video_with_all_enabled(self, video: dict, dry_run: bool = False) -> Dict[str, bool]:
    results = {}
    video_platform = video.get("platform")  # DB から取得

    for plugin_name, plugin in self.enabled_plugins.items():
        try:
            # ★ プラットフォーム対応確認
            supported_platforms = plugin.get_supported_platforms() if hasattr(plugin, 'get_supported_platforms') else None
            if supported_platforms is not None and video_platform not in supported_platforms:
                logger.debug(f"⏭️ {plugin_name}: プラットフォーム未対応（{video_platform}）")
                results[plugin_name] = True  # スキップ（成功ではなく「対応不可」）
                continue

            if hasattr(plugin, 'set_dry_run'):
                plugin.set_dry_run(dry_run)

            success = plugin.post_video(video)
            results[plugin_name] = success
            # ...
```

### 長期対策：database.py に platform フィールドを確実に格納

**問題**: 現在、DB に platform 情報が完全に格納されているか不確実

**対策**:
- database.py の `insert_video()` で platform を必須フィールドにする
- GUI から post_video_with_all_enabled() を呼び出すとき、video に platform を必ず含める

---

## 🐛 現在の影響

### 負の影響

1. **エラーログノイズ**：毎回 Niconico 動画を投稿するたびに YouTube Plugin エラーが出力
2. **API コスト無駄遣い**：YouTube Data API クォータが無駄に消費される（1ユニット/失敗）
3. **処理時間浪費**：不要な API 呼び出しでタイムアウト待機

### 実際のコスト

本ログから：
```
2025-12-18 07:30:17,642 [INFO] 💰 API コスト: video detail: sm45414087 = 1ユニット (累計: 1/10000)
2025-12-18 07:30:18,092 [INFO] 💰 API コスト: video detail: sm45414087 = 1ユニット (累計: 2/10000)
```

→ 1つの Niconico 動画投稿で **2ユニット** 浪費（YouTubeAPIPlugin + YouTubeLivePlugin）

---

## 📋 今後の対策チェックリスト

- [ ] **短期**: `_is_valid_youtube_video_id()` をYouTubePlugin に追加
- [ ] **短期**: YouTubeLivePlugin にも同じ検証を追加
- [ ] **中期**: `get_supported_platforms()` を plugin_interface に追加
- [ ] **中期**: 各プラグイン実装で `get_supported_platforms()` をオーバーライド
- [ ] **中期**: plugin_manager.post_video_with_all_enabled() で platform 判定を追加
- [ ] **長期**: database.py で platform を必須フィールドに
- [ ] **長期**: GUI から post_video_with_all_enabled() 呼び出し時に platform を必ず含める

---

## 参考

### 現在のファイル構造

- `v2/plugins/youtube_api_plugin.py`: 短期対策適用対象
- `v2/plugins/youtube_live_plugin.py`: 短期対策適用対象
- `v2/plugin_interface.py`: 中期対策適用対象
- `v2/plugin_manager.py`: 中期対策適用対象
- `v2/gui_v2.py`: 長期対策適用対象
- `v2/database.py`: 長期対策適用対象

