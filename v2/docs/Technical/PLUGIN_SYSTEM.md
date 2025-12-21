# v2 プラグインシステム - 完全実装ガイド

**対象バージョン**: v2.1.0+
**最終更新**: 2025-12-18
**ステータス**: ✅ 実装完了・検証済み

---

## 📖 目次

1. [概要](#概要)
2. [Rich Text Facet（リンク化）](#rich-text-facetリンク化)
3. [画像付き投稿](#画像付き投稿)
4. [リンクカード埋め込み](#リンクカード埋め込み)
5. [DRY RUN 機能](#dry-run機能)
6. [GUI投稿設定](#gui投稿設定)
7. [Bluesky プラグイン非導入時](#bluesky-プラグイン非導入時)
8. [トラブルシューティング](#トラブルシューティング)

---

## 概要

このドキュメントは、Bluesky プラグイン実装の技術資料です。実装済みの仕様と設計パターンを記録しており、将来の拡張機能実装の参考になります。

### 対象デバイス

- Windows / Linux 環境
- Python 3.9+
- Bluesky API v1

---

## Rich Text Facet（リンク化）

### 問題と解決

**問題**:
投稿本文に YouTube URL を含めても、Bluesky でリンク化されず、テキストのままだった。

**原因**:
Bluesky API は X（旧 Twitter）と異なり、**テキストに含まれる URL を自動的にリンク化しない**。代わりに、**Rich Text フォーマット（Facet）** で URL の位置を明示的に指定する必要がある。

### 実装方法

#### HTTP API で直接実装（推奨）

**atproto ライブラリの依存性を排除**し、`requests` で Bluesky API を直接呼び出します。

```python
# 認証
POST https://bsky.social/xrpc/com.atproto.server.createSession

# 投稿（Rich Text 対応）
POST https://bsky.social/xrpc/com.atproto.repo.createRecord
```

#### Facet の構造

Rich Text Facet の正確な構築が必須:

```json
{
  "index": {
    "byteStart": 42,     // UTF-8 バイトオフセット
    "byteEnd": 67        // 排他的（含まない）
  },
  "features": [
    {
      "$type": "app.bsky.richtext.facet#link",
      "uri": "https://..."
    }
  ]
}
```

#### createdAt の正しい形式

```python
from datetime import datetime, timezone

# ✅ 正しい（ISO 8601）
created_at = datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')
# 結果: "2025-12-05T09:55:16Z"

# ❌ 間違い
"createdAt": "Fri, 05 Dec 2025 09:55:00 GMT"  # HTTP日付形式は使用不可
```

#### Facet 構築の実装例

```python
import re

def build_facets(text: str) -> list:
    """URL を検出して Facet を構築"""
    facets = []

    # URL パターンマッチング
    url_pattern = r'https?://[^\s]+'

    for match in re.finditer(url_pattern, text):
        start_idx = match.start()
        end_idx = match.end()

        # UTF-8 バイトオフセットに変換
        byte_start = len(text[:start_idx].encode('utf-8'))
        byte_end = len(text[:end_idx].encode('utf-8'))

        facets.append({
            "index": {"byteStart": byte_start, "byteEnd": byte_end},
            "features": [{
                "$type": "app.bsky.richtext.facet#link",
                "uri": match.group()
            }]
        })

    return facets
```

### ハッシュタグ Facet

ハッシュタグもリンク化することができます:

```python
def build_hashtag_facets(text: str) -> list:
    """ハッシュタグを検出して Facet を構築"""
    facets = []

    # ハッシュタグパターン
    hashtag_pattern = r'(?:^|\s)(#[^\s#]+)'

    for match in re.finditer(hashtag_pattern, text):
        tag = match.group(1)  # # を含む
        start_idx = match.start(1)
        end_idx = match.end(1)

        byte_start = len(text[:start_idx].encode('utf-8'))
        byte_end = len(text[:end_idx].encode('utf-8'))

        facets.append({
            "index": {"byteStart": byte_start, "byteEnd": byte_end},
            "features": [{
                "$type": "app.bsky.richtext.facet#tag",
                "tag": tag[1:]  # # を除去して保存
            }]
        })

    return facets
```

---

## 画像付き投稿

### 画像リサイズの三段階戦略

`image_processor.py` で公開推奨サイズを実装:

```python
_RECOMMENDED_SIZES = {
    "portrait": {"width": 800, "height": 1000},   # 4:5 (アスペクト比 < 0.8)
    "square": {"width": 1000, "height": 1000},    # 1:1 (0.8 ≤ アスペクト比 ≤ 1.25)
    "landscape": {"width": 1200, "height": 627},  # 16:9 (アスペクト比 > 1.25)
}
```

#### アスペクト比に基づいた自動リサイズ

```python
def resize_image(file_path: str) -> bytes:
    """アスペクト比に基づいた自動リサイズ"""
    img = Image.open(file_path)

    # アスペクト比を計算
    aspect_ratio = img.width / img.height

    # 三段階の判定
    if aspect_ratio < 0.8:        # 縦長
        target_size = (800, 1000)
    elif aspect_ratio <= 1.25:    # 正方形
        target_size = (1000, 1000)
    else:                          # 横長
        target_size = (1200, 627)

    # Lanczos高品質リサイズ
    resized_img = img.resize(target_size, Image.Resampling.LANCZOS)

    # JPEG出力
    output = BytesIO()
    resized_img.save(output, format='JPEG', quality=90)
    return output.getvalue()
```

### JPEG 品質最適化パイプライン

段階的な品質低下によるファイルサイズ最適化:

```python
def _optimize_image_quality(binary_data: bytes) -> bytes:
    """ファイルサイズが900KB以下になるまで品質を下げる"""
    quality_levels = [90, 85, 75, 65, 55, 50]

    for quality in quality_levels:
        if len(binary_data) <= 900 * 1024:  # 900KB以下
            return binary_data

        # 品質を低下させて再度エンコード
        img = Image.open(BytesIO(binary_data))
        output = BytesIO()
        img.save(output, format='JPEG', quality=quality)
        binary_data = output.getvalue()

    return binary_data
```

### AspectRatio フィールド

`bluesky_plugin.py` で画像埋め込み時に aspectRatio を設定:

```python
def _build_image_embed(self, blob: dict, width: int = None, height: int = None) -> dict:
    """画像埋め込みを構築（aspectRatio付き）"""
    image_obj = {
        "image": blob,
        "alt": "投稿画像"
    }

    # アスペクト比を設定
    if width and height:
        image_obj["aspectRatio"] = {
            "width": width,
            "height": height
        }

    return {
        "$type": "com.atproto.repo.strongRef",
        "uri": blob["link"]["uri"],
        "cid": blob["link"]["cid"],
        "image": image_obj
    }
```

---

## リンクカード埋め込み

### リンクカード非表示の実装

プラグイン非導入時はリンクカードを無効化:

```python
# bluesky_core.py

def post_video_minimal(self, video: dict) -> bool:
    """Bluesky にテキスト + URL で投稿"""

    # リンクカード設定を確認（プラグイン非導入時は False）
    use_link_card = video.get("via_plugin", True)

    if use_link_card:
        # Link Card を有効化（プラグイン版）
        embed = self._build_link_card(video_url)
    else:
        # Link Card を無効化（プラグイン非導入時）
        embed = None

    # 投稿実行
    return self._post_to_bluesky(post_text, embed, blob)
```

---

## DRY RUN 機能

### 投稿テスト（本投稿なし）

```python
# GUI から DRY RUN ボタン
def on_dry_run_post(self):
    """投稿テスト（本投稿なし）"""

    video = self.get_selected_video()

    if self.bluesky_core:
        self.bluesky_core.set_dry_run(True)  # ★ DRY RUN 有効化

    results = self.plugin_manager.post_video_with_all_enabled(
        video,
        dry_run=True  # ★ 本投稿なし
    )

    if any(results.values()):
        logger.info("✅ 投稿テスト成功（本投稿なし）")
    else:
        logger.error("❌ 投稿テスト失敗")
```

### ログ出力

DRY RUN 時のログ出力:

```
🧪 [DRY RUN] テキスト投稿をシミュレートします
📝 本文: 【新着動画】...
📊 テキスト長: 142 文字
📸 画像: thumbnail.jpg (1.2 MB)
🧪 [DRY RUN] 投稿をシミュレート完了（本投稿なし）
```

---

## GUI 投稿設定

### 投稿設定ウィンドウ

```
┌─ 投稿設定 ───────────────────────────┐
│ ☑ 画像を添付する                     │
│ ☐ リンクカードを表示                 │
│                                     │
│ 画像リサイズ:                         │
│ ○ 自動（推奨）                       │
│ ○ 1200×627 (16:9)                   │
│ ○ 800×1000 (4:5)                    │
│ ○ 1000×1000 (1:1)                   │
│                                     │
│ JPEG 品質: [████████░░] 90          │
│                                     │
│ [確認] [キャンセル]                  │
└─────────────────────────────────────┘
```

---

## Bluesky プラグイン非導入時

### 固定設定値の適用

プラグインが導入されていない場合、GUI テキスト投稿のフォールバック処理で固定設定値を使用します:

```python
# gui_v2.py

elif self.bluesky_core:
    # フォールバック：プラグインがない場合はコア機能を直接呼び出し
    logger.info(f"📤 コア機能で投稿（テンプレート非対応、固定設定値使用）")

    # ★ 固定設定値を video 辞書に追加
    video_with_settings = dict(video)
    video_with_settings["use_link_card"] = True      # リンクカード有効
    video_with_settings["embed"] = None              # 画像埋め込みなし
    video_with_settings["via_plugin"] = False        # プラグイン経由ではない

    if hasattr(self.bluesky_core, 'set_dry_run'):
        self.bluesky_core.set_dry_run(dry_run)

    success = self.bluesky_core.post_video_minimal(video_with_settings)

    if success and not dry_run:
        self.db.mark_as_posted(video["video_id"])
```

### 設定値の説明

| 設定 | 値 | 説明 |
|:--|:--|:--|
| `use_link_card` | True | Bluesky でリンクカードを表示 |
| `embed` | None | 画像埋め込みなし |
| `via_plugin` | False | プラグイン経由ではない |

---

## トラブルシューティング

### 症状 1: リンクがリンク化されない

**原因**: Facet の位置計算が正確でない

**対応**:
1. UTF-8 バイトオフセットが正しいか確認
2. `byteStart` と `byteEnd` が排他的範囲になっているか確認
3. ログで Facet 情報を確認: `grep "facet" logs/post.log`

### 症状 2: 画像がレターボックス表示される

**原因**: アスペクト比の計算が正確でない

**対応**:
1. 元画像のサイズを確認: `identify -verbose image.jpg`
2. アスペクト比計算: `width / height`
3. リサイズ後のサイズが推奨値と一致しているか確認

### 症状 3: DRY RUN なのに投稿されている

**原因**: `set_dry_run()` が呼ばれていない

**対応**:
1. ログで確認: `grep "DRY RUN" logs/app.log`
2. `gui_v2.py` の `on_dry_run_post()` が正しく呼ばれているか確認
3. Bluesky プラグインの `set_dry_run()` が実装されているか確認

---

**作成日**: 2025-12-18
**最後の修正**: 2025-12-18
**ステータス**: ✅ 完成・検証済み
