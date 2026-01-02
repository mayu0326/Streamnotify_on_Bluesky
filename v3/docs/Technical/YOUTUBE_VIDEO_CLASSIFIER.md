# YouTube 動画分類モジュール - 実装ガイド

**対象バージョン**: v3.3.0+
**最終更新**: 2026-01-02
**ステータス**: ✅ 実装完了

---

## 概要

YouTube Data API を使って、動画が「通常動画」「プレミア公開」のいずれかを判定するモジュールです。

Live関連（スケジュール、放送中、放送終了、ライブアーカイブ）は除外し、通常動画とプレミア公開のみを対象にしています。

### キャッシュ機能

- **自動キャッシュ**: API で取得した動画詳細は自動的に `data/youtube_video_detail_cache.json` に保存
- **キャッシュ優先**: 同じ動画に対して 2 回目以降の判定はキャッシュから読み込み（API 呼び出しなし）
- **API クォータ削減**: キャッシュにより YouTube Data API のクォータ消費を大幅削減

---

## ファイル位置

```
v3/youtube_core/youtube_video_classifier.py
```

---

## 主な機能

### 1. `classify_video(video_id)` - 詳細分類

動画を以下の 7 種別に分類します：

| 種別コード | 説明 | is_live | is_premiere | 対象 |
|:--|:--|:--:|:--:|:--|
| `"video"` | 通常動画 | False | False | ✅ **対象** |
| `"premiere"` | プレミア公開 | False | True | ✅ **対象** |
| `"schedule"` | ライブ予定/スケジュール | True | - | ❌ 除外 |
| `"live"` | ライブ配信中 | True | - | ❌ 除外 |
| `"completed"` | ライブ配信終了 | True | - | ❌ 除外 |
| `"archive"` | ライブアーカイブ | True | - | ❌ 除外 |
| `"unknown"` | 判定不可 | - | - | ❌ 除外 |

**返却値の構造**:

```python
{
    "success": bool,                    # API 呼び出し成功フラグ
    "video_id": str,                    # 動画 ID
    "type": str,                        # 種別（上表参照）
    "title": str,                       # 動画タイトル
    "description": str,                 # 動画説明
    "thumbnail_url": str,               # サムネイル URL
    "is_premiere": bool,                # プレミア公開フラグ
    "is_live": bool,                    # ライブ関連フラグ
    "live_status": str or None,         # ライブステータス（upcoming, live, completed）
    "is_scheduled_start_time": bool,    # scheduledStartTime が設定されているか
    "published_at": str,                # 公開日時
    "error": str or None,               # エラーメッセージ（失敗時のみ）
}
```

### 2. `is_normal_or_premiere(video_id)` - 短縮判定

「通常動画またはプレミア公開」かどうかを True/False で返します。

```python
classifier = YouTubeVideoClassifier()
if classifier.is_normal_or_premiere("dQw4w9WgXcQ"):
    # 通常動画またはプレミア公開 → 投稿対象
else:
    # Live関連または判定失敗 → 投稿対象外
```

### 3. `is_live_related(video_id)` - ライブ関連判定

Live関連かどうかを True/False で返します。

```python
classifier = YouTubeVideoClassifier()
if classifier.is_live_related("dQw4w9WgXcQ"):
    # Live関連（スケジュール、配信中、配信終了、アーカイブ）
else:
    # 通常動画またはプレミア公開
```

---

## 使用例

### 初期化

```python
from youtube_core.youtube_video_classifier import YouTubeVideoClassifier

# API キーを自動的に環境変数から取得
classifier = YouTubeVideoClassifier()

# または API キーを明示的に指定
classifier = YouTubeVideoClassifier(api_key="YOUR_API_KEY_HERE")
```

### 例 1: 詳細分類結果を取得

```python
result = classifier.classify_video("dQw4w9WgXcQ")

if result["success"]:
    print(f"📺 動画: {result['title']}")
    print(f"   種別: {result['type']}")
    print(f"   プレミア公開: {result['is_premiere']}")
    print(f"   ライブ関連: {result['is_live']}")

    if result['type'] == "premiere":
        print("   → プレミア公開として投稿予定")
    elif result['type'] == "video":
        print("   → 通常動画として投稿予定")
    elif result['type'] == "live":
        print("   → ライブ配信中（投稿スキップ）")
else:
    print(f"❌ エラー: {result['error']}")
```

### 例 2: 投稿判定（短縮版）

```python
video_id = "dQw4w9WgXcQ"

if classifier.is_normal_or_premiere(video_id):
    # 通常動画またはプレミア公開 → Bluesky に投稿
    bluesky.post_video(video_id)
else:
    # Live関連 → スキップ
    logger.info(f"⏭️ ライブ関連のため投稿スキップ: {video_id}")
```

### 例 3: AUTOPOST で使用

```python
from config import get_config
from youtube_core.youtube_video_classifier import YouTubeVideoClassifier

config = get_config("settings.env")
classifier = YouTubeVideoClassifier()

# 新着動画をチェック
for video in db.get_autopost_candidates(config):
    result = classifier.classify_video(video["video_id"])

    if not result["success"]:
        logger.warning(f"⚠️ 分類失敗: {video['video_id']}")
        continue

    # プレミア公開を別テンプレートで投稿
    if result['type'] == "premiere":
        template = load_template("premiere_template.txt")
    elif result['type'] == "video":
        template = load_template("video_template.txt")
    else:
        # Live関連は投稿対象外
        continue

    # Bluesky に投稿
    post_to_bluesky(template, video, result)
```

---

## API キーの設定

### 方法 1: 環境変数（推奨）

`settings.env` に以下を設定：

```env
YOUTUBE_API_KEY=YOUR_API_KEY_HERE
```

### 方法 2: 明示的に指定

```python
classifier = YouTubeVideoClassifier(api_key="YOUR_API_KEY_HERE")
```

---

## 判定ロジック（詳細）

### ステップ 1: liveStreamingDetails の確認

```
liveStreamingDetails が存在？
  ├─ YES:
  │   ├─ scheduledStartTime 存在かつ actualStartTime なし？
  │   │   └─ YES → "schedule"（ライブ予定）
  │   ├─ actualStartTime 存在かつ actualEndTime なし？
  │   │   └─ YES → "live"（配信中）
  │   └─ actualEndTime 存在？
  │       └─ YES → "completed"（配信終了）
  └─ NO: ステップ 2 へ
```

### ステップ 2: isLiveContent の確認

```
contentDetails.isLiveContent == true？
  ├─ YES → "archive"（ライブアーカイブ）
  └─ NO: ステップ 3 へ
```

### ステップ 3: liveBroadcastContent の確認

```
liveBroadcastContent == "premiere"？
  ├─ YES → "premiere"（プレミア公開）
  └─ NO: ステップ 4 へ
```

### ステップ 4: デフォルト

```
→ "video"（通常動画）
```

---

## エラーハンドリング

### エラー 1: API キーが設定されていない

```python
result = classifier.classify_video("dQw4w9WgXcQ")
# {
#     "success": False,
#     "type": "unknown",
#     "error": "YouTube API キーが設定されていません"
# }
```

**対応**: `settings.env` に `YOUTUBE_API_KEY` を設定してください。

### エラー 2: 動画が見つからない

```python
result = classifier.classify_video("INVALID_ID")
# {
#     "success": False,
#     "type": "unknown",
#     "error": "動画が見つかりません（video_id: INVALID_ID）"
# }
```

**対応**: 動画 ID が正しいか確認してください。

### エラー 3: API 呼び出し失敗

```python
result = classifier.classify_video("dQw4w9WgXcQ")
# {
#     "success": False,
#     "type": "unknown",
#     "error": "API 呼び出し失敗: ..."
# }
```

**対応**: ネットワーク接続、API キーの有効性、API クォータを確認してください。

---

## 統合ポイント（GUI・AUTOPOST）

### GUI からの使用

[gui_v3.py](../../gui_v3.py) の動画投稿機能内：

```python
# [投稿] ボタン押下時
def on_post_video(self):
    video = self.get_selected_video()

    # ★ YouTube API で種別を確認
    classifier = YouTubeVideoClassifier()
    result = classifier.classify_video(video["video_id"])

    if result["success"]:
        if result["type"] not in ["video", "premiere"]:
            messagebox.showwarning(
                "投稿不可",
                f"この動画はライブ関連のため投稿できません: {result['type']}"
            )
            return

    # テンプレート選択（プレミア公開 vs 通常動画）
    if result.get("is_premiere"):
        template_name = "premiere_template"
    else:
        template_name = "video_template"

    # 投稿実行
    self.post_to_bluesky(video, template_name)
```

### AUTOPOST での使用

[main_v3.py](../../main_v3.py) の AUTOPOST ループ内：

```python
def autopost_loop():
    classifier = YouTubeVideoClassifier()

    while running:
        # LOOKBACK 時間窓内の未投稿動画を取得
        videos = db.get_autopost_candidates(config)

        for video in videos:
            # ★ 種別を判定
            result = classifier.classify_video(video["video_id"])

            if not result["success"]:
                logger.warning(f"⚠️ 分類失敗: {video['video_id']}")
                continue

            # Live関連はスキップ
            if result["is_live"]:
                logger.info(f"⏭️ ライブ関連のため投稿スキップ: {video['video_id']}")
                continue

            # 通常動画またはプレミア公開として投稿
            template = "premiere_template" if result["is_premiere"] else "video_template"
            post_video(video, template, result)
```

---

## トラブルシューティング

### Q: API キーがあるのに「キーが設定されていない」と言われる

**A**: 以下を確認：

1. `settings.env` に `YOUTUBE_API_KEY=...` が記載されているか
2. 空白やコメント行になっていないか
3. アプリケーションを再起動したか（環境変数の読み込みは起動時）

### Q: すべての動画が "unknown" で判定される

**A**: 以下を確認：

1. API キーが有効か（Google Cloud Console で確認）
2. YouTube Data API が有効化されているか
3. API クォータが残っているか

### Q: 一部の動画が正しく分類されない

**A**: 以下を確認：

1. `logs/app.log` でエラーメッセージを確認
2. YouTube API が API レスポンスを正しく返しているか
3. 動画が削除されていないか、非公開になっていないか

---

## 性能考慮事項

### API クォータ消費

- **初回判定**: 1 回の `classify_video()` 呼び出し = YouTube Data API クォータ **1** 消費
- **キャッシュ利用**: 同じ動画への 2 回目以降の判定 = クォータ **0** 消費（ファイルから読み込み）
- **日次クォータ**: 10,000（デフォルト、申請で増加可）
- **推奨**: 投稿時の判定に使用、定期ポーリングは避ける

### キャッシュの詳細

#### キャッシュファイル位置

```
v3/data/youtube_video_detail_cache.json
```

#### キャッシュ構造

```json
{
  "video_id_1": {
    "data": { /* YouTube API レスポンス */ },
    "cached_at": 1234567890
  },
  "video_id_2": { ... }
}
```

#### キャッシュの仕組み

1. **初期化時**: `_load_cache()` で既存キャッシュを読み込む
2. **classify_video() 呼び出し時**:
   - キャッシュに存在？ → キャッシュから読み込み（API なし）
   - キャッシュに未存在？ → API で取得して、キャッシュに保存
3. **ファイル保存**: `_save_cache()` で JSON ファイルに書き込み

#### キャッシュ削除

キャッシュを削除したい場合：

```bash
rm v3/data/youtube_video_detail_cache.json
```

次回起動時に自動的に再生成されます。

### レガシーのキャッシング戦略（削除予定）

以下の `@lru_cache` 実装は使用していません（ファイルベースキャッシュのため）：

```python
# ❌ 使用していない（参考のため記載）
from functools import lru_cache

class YouTubeVideoClassifier:
    @lru_cache(maxsize=1000)
    def classify_video_cached(self, video_id: str):
        return self.classify_video(video_id)
```

---

## 今後の拡張予定

- [x] キャッシュ機能（同一動画の重複 API 呼び出し削減） ✅ **v3.3.0で実装**
- [ ] バッチ処理（複数動画を一度に判定）
- [ ] オフライン判定（RSS / DB から推測）
- [ ] 判定結果の DB 保存
- [ ] キャッシュ有効期限管理（CACHE_EXPIRY_DAYS に基づく自動削除）

---

## ライセンス

**GPLv2** - 詳細は [LICENSE](../../../LICENSE) を参照
