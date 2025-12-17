# Bluesky プラグイン実装ガイド

**このドキュメントは、Bluesky プラグイン開発の技術資料です。**
実装済みの仕様と設計パターンを記録しており、将来の拡張機能実装の参考になります。

---

## 📋 目次

1. [Rich Text Facet（リンク化）](#1-rich-text-facetリンク化)
2. [画像付き投稿](#2-画像付き投稿)
3. [リンクカード埋め込み](#3-リンクカード埋め込み)
4. [DRY RUN（投稿テスト）機能](#4-dry-run投稿テスト機能)
5. [GUI投稿設定ウィンドウ](#5-gui投稿設定ウィンドウ)
6. [実装チェックリスト](#6-実装チェックリスト)
7. [トラブルシューティング](#7-トラブルシューティング)

---

## 1. Rich Text Facet（リンク化）

### ✅ 問題と解決

**問題**：投稿本文に YouTube URL を含めても、Bluesky でリンク化されず、テキストのままだった。

**原因**：Bluesky API は X（旧 Twitter）と異なり、**テキストに含まれる URL を自動的にリンク化しない**。代わりに、**Rich Text フォーマット（Facet）** で URL の位置を明示的に指定する必要がある。

### 🔧 実装方法

#### HTTP API で直接実装（推奨）

**atproto ライブラリの依存性を排除**し、`requests` で Bluesky API を直接呼び出す。

```python
# 認証
POST https://bsky.social/xrpc/com.atproto.server.createSession

# 投稿（Rich Text 対応）
POST https://bsky.social/xrpc/com.atproto.repo.createRecord
```

#### Facet の構造

Rich Text Facet の正確な構築が必須：

```json
{
  "index": {
    "byteStart": 42,     // UTF-8 バイトオフセット
    "byteEnd": 67        // 排他的（含まない）
  },
  "features": [
    {
      "$type": "app.bsky.richtext.facet#link",  // 完全な型名
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

    # URL パターンにマッチするすべての URL を検出
    for match in re.finditer(r'https?://[^\s]+', text):
        url = match.group(0)

        # UTF-8 バイト位置を計算
        byte_start = len(text[:match.start()].encode('utf-8'))
        byte_end = len(text[:match.end()].encode('utf-8'))

        facets.append({
            "index": {
                "byteStart": byte_start,
                "byteEnd": byte_end
            },
            "features": [
                {
                    "$type": "app.bsky.richtext.facet#link",
                    "uri": url
                }
            ]
        })

    return facets
```

#### byteStart/byteEnd の計算

**UTF-8 エンコード後のバイト位置を使用**

```python
text = "【動画】https://example.com"

# 「【動画】」= 12 バイト（UTF-8 マルチバイト）
# 「https://example.com」= 21 バイト

byte_start = len(text[:match.start()].encode('utf-8'))  # = 12
byte_end = len(text[:match.end()].encode('utf-8'))      # = 33
```

#### Bluesky API へのリクエスト

```python
import requests
from datetime import datetime, timezone

def post_with_facets(text: str, facets: list, user_did: str, access_token: str):
    """Facet を含めて投稿"""

    # ISO 8601 形式の createdAt
    created_at = datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')

    post_record = {
        "$type": "app.bsky.feed.post",
        "text": text,
        "createdAt": created_at,
        "facets": facets  # Rich Text 情報
    }

    response = requests.post(
        "https://bsky.social/xrpc/com.atproto.repo.createRecord",
        json={
            "repo": user_did,
            "collection": "app.bsky.feed.post",
            "record": post_record
        },
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
    )

    return response.json()
```

### ✨ 実装のポイント

| 項目 | 注意点 |
|------|--------|
| **UTF-8 バイト位置** | 日本語等のマルチバイト文字に対応 |
| **byteEnd** | 排他的（含まない）なので注意 |
| **$type の完全名** | `app.bsky.richtext.facet#link` 完全に指定 |
| **createdAt** | ISO 8601 形式（`Z` タイムゾーン） |
| **複数 URL** | すべての URL を facets 配列に追加 |

### 📊 実装チェックリスト

- ✅ HTTP API で直接実装（atproto ライブラリ不要）
- ✅ UTF-8 バイトオフセットで Facet を構築
- ✅ `$type` に完全な型名 `app.bsky.richtext.facet#link` を指定
- ✅ `createdAt` を ISO 8601 形式で設定
- ✅ `facets` を post_record に含める
- ✅ エラーハンドリング実装
- ✅ 複数 URL への対応

### 📚 参考資料

- **Bluesky Rich Text ドキュメント**: https://docs.bsky.app/docs/advanced-guides/post-richtext
- **AT Protocol**: https://atproto.com/
- **Bluesky Public API**: https://docs.bsky.app/

---

## 2. 画像付き投稿

### 📋 基本的な制限事項

| 項目 | 仕様 |
|------|------|
| **最大画像数** | 1投稿あたり最大4枚 |
| **1画像あたりの最大サイズ** | 1,000,000バイト（1MB） |
| **推奨アスペクト比** | 16:9（ランドスケープ）、4:5（ポートレート）、1:1（スクエア） |
| **MIME Type** | image/png、image/webp、image/jpeg等 |

### 🆕 2.1 画像自動リサイズ機能（v2.1.0+）

画像投稿が有効な場合、**すべての画像がこの処理を自動で経由します**。

#### 処理フロー

```
元画像（任意サイズ・フォーマット）
    ↓
1. 元画像情報取得（解像度・フォーマット・ファイルサイズ）
    ↓
2. アスペクト比判定＆リサイズ
    ├─ 横長（≥1.3）→ 3:2に統一＋中央トリミング
    ├─ 正方形/やや横長（0.8-1.3）→ 長辺1280px以下に縮小のみ
    └─ 縦長（<0.8）→ 長辺1280px以下に縮小のみ
    ↓
3. JPEG品質90で出力
    ↓
4. ファイルサイズチェック
    ├─ 900KB以下 → OK
    └─ 900KB超過 → 品質を段階的に低下して再圧縮
    ↓
5. 最終確認
    ├─ 1MB以下 → アップロード
    └─ 1MB超過 → スキップ（テキスト＋URLのみで投稿）
```

#### 設定・定数

```python
# v2/plugins/bluesky_plugin.py（行33-39）
IMAGE_RESIZE_TARGET_WIDTH = 1280       # 横長画像のターゲット幅
IMAGE_RESIZE_TARGET_HEIGHT = 800       # 横長画像のターゲット高さ（3:2）
IMAGE_OUTPUT_QUALITY_INITIAL = 90      # 初期JPEG品質
IMAGE_SIZE_TARGET = 800_000            # 目標ファイルサイズ（800KB）
IMAGE_SIZE_THRESHOLD = 900_000         # 品質低下の開始閾値（900KB）
IMAGE_SIZE_LIMIT = 1_000_000           # 最終上限（1MB）
```

#### パターン詳細

##### パターン1: 横長画像（幅/高さ ≥ 1.3）

**例**: 1920×1440（アスペクト比1.33）

```
元画像: 1920×1440
  ↓ 短辺=1440 を基準に縮小
  ↓ ターゲット比率（1280÷800=1.6）に寄せる
1024×800（幅が目標より大きい）
  ↓ 中央トリミング
1280×800（完成）
```

**メソッド**: `_resize_to_aspect_ratio()`
- 短辺を基準に縮小
- 目標アスペクト比に寄せる
- 中央トリミング（上下左右均等）

##### パターン2: 正方形～やや横長（0.8 ≤ 幅/高さ < 1.3）

**例**: 1600×1600（正方形）、1280×1000（やや横長）

```
元画像: 1600×1600
  ↓ 長辺=1600 なので 1280×1280 に縮小のみ
  ↓ アスペクト比を維持
1280×1280（完成、拡大なし）
```

**メソッド**: `_resize_to_max_dimension()`
- 長辺が1280以下になるまで等比縮小
- **小さい画像は拡大しない**

##### パターン3: 縦長画像（幅/高さ < 0.8）

**例**: 800×1600（縦長）

```
元画像: 800×1600
  ↓ 長辺=1600 なので 640×1280 に縮小のみ
640×1280（完成、拡大なし）
```

パターン2と同じ処理（長辺基準）

#### ファイルサイズ管理

| 段階 | 基準 | 内容 |
|------|------|------|
| 1 | 初期出力 | JPEG品質90で出力 |
| 2 | 800KB | 理想的なファイルサイズ |
| 3 | 900KB | この値超過で品質低下開始 |
| 4 | 品質段階 | 90→85→75→65→55→50 |
| 5 | 1MB | 最終上限（超過時はスキップ） |

#### ログ出力例

**成功ケース**:
```
DEBUG   📏 元画像: 1920×1440 (JPEG, 2150.5KB, アスペクト比: 1.33)
DEBUG   🔄 パターン1（横長）: 3:2に統一+中央トリミング
DEBUG      リサイズ後: 1280×800
DEBUG      JPEG品質90: 320.2KB
INFO    ✅ 画像リサイズ完了: 1920×1440 (2150.5KB) → 1280×800 (320.2KB)
```

**品質低下ケース**:
```
DEBUG   📏 元画像: 1600×1200 (JPEG, 5000.0KB, アスペクト比: 1.33)
DEBUG   🔄 パターン1（横長）: 3:2に統一+中央トリミング
DEBUG      リサイズ後: 1280×800
DEBUG      JPEG品質90: 950.5KB
INFO    ⚠️  ファイルサイズが 900KB を超過: 950.5KB
DEBUG      JPEG品質85: 850.2KB
INFO    ✅ 品質85で 1MB 以下に圧縮: 850.2KB
```

**スキップケース**:
```
ERROR   ❌ ファイルサイズの最適化に失敗しました（1MB超過）
WARNING ⚠️  画像リサイズ失敗のため、この投稿では画像添付をスキップします
```

この場合、テキスト＋URLリンクカードのみで投稿

#### 実装メソッド

| メソッド | 行数 | 用途 |
|---------|------|------|
| `_resize_image()` | 92 | メイン処理（全体調整） |
| `_resize_to_aspect_ratio()` | 44 | 横長画像 → 3:2トリミング |
| `_resize_to_max_dimension()` | 28 | 長辺基準で等比縮小 |
| `_encode_jpeg()` | 26 | PIL → JPEG変換 |
| `_optimize_image_quality()` | 28 | 品質低下で再圧縮 |

#### 設定の変更方法

**ターゲット解像度を変更**:
```python
# v2/plugins/bluesky_plugin.py
IMAGE_RESIZE_TARGET_WIDTH = 1920
IMAGE_RESIZE_TARGET_HEIGHT = 1080
```

**品質段階を変更**:
```python
# _optimize_image_quality() メソッド内
quality_levels = [80, 70, 60, 50]  # より積極的に低下
```

**サイズ上限を変更**:
```python
IMAGE_SIZE_THRESHOLD = 1_800_000   # 再圧縮開始を1.8MBに
IMAGE_SIZE_LIMIT = 2_000_000       # 最終上限を2MBに
```

#### トラブルシューティング

**Q: 画像が「スキップ」され続ける**

A: ログで以下を確認:
1. `📏 元画像:` で元のサイズを確認
2. `品質50でも 1MB 超過` が出ていないか
3. 出ている場合は、`IMAGE_SIZE_LIMIT` をまず上げて試す

**Q: 品質が落ちている気がする**

A:
1. ログで `JPEG品質XX:` の値を確認
2. 品質90で900KB以下なら品質低下は起きていない
3. 品質85以下なら、元画像が大きすぎる可能性

**Q: 小さい画像が拡大される**

A: 拡大は **しません**
- パターン2・3（正方形/縦長）で、元画像が1280px以下なら拡大しない

### 🔄 画像付き投稿の処理フロー

Bluesky APIでの画像投稿には、以下の2ステップが必要です：

#### **ステップ1：画像をBlobとしてアップロード**

```
POST /xrpc/com.atproto.repo.uploadBlob
```

- ヘッダに `Content-Type`（MIME Type）を指定
- 認証トークン（`Authorization: Bearer [accessJwt]`）を含める
- 画像のバイナリデータを送信
- 成功時に`blob`メタデータが返される

**返されるレスポンス例：**

```json
{
  "blob": {
    "$type": "blob",
    "ref": {
      "$link": "bafkreibabalobzn6cd366ukcsjycp4yymjymgfxcv6xczmlgpemzkz3cfa"
    },
    "mimeType": "image/png",
    "size": 760898
  }
}
```

#### **ステップ2：取得したBlobを投稿に埋め込み**

取得したBlobを`app.bsky.embed.images`にセットして投稿を作成します。

### 2.2 Python実装例（atprotoライブラリ）

**方法1：詳細に実装する場合**

```python
from atproto import Client, models

client = Client()
client.login('ユーザID', 'パスワード')

# 画像ファイルを読み込み
with open('image.png', 'rb') as f:
    img_data = f.read()

# Blob をアップロード
upload = client.upload_blob(img_data)

# 画像オブジェクトを作成
images = [
    models.AppBskyEmbedImages.Image(
        alt='画像の説明',
        image=upload.blob
    )
]

# Embed オブジェクトを作成
embed = models.AppBskyEmbedImages.Main(images=images)

# 投稿を作成
post = models.AppBskyFeedPost.Record(
    text='投稿するテキスト',
    embed=embed,
    created_at=client.get_current_time_iso()
)

client.app.bsky.feed.post.create(client.me.did, post)
```

**方法2：シンプルに実装する場合（推奨）**

```python
from atproto import Client

client = Client()
client.login('ユーザID', 'パスワード')

# 画像ファイルを読み込み
with open('image.png', 'rb') as f:
    img_data = f.read()

# ワンステップで投稿
client.send_image(
    text='投稿するテキスト',
    image=img_data,
    image_alt='画像の説明'
)
```

### 📌 重要なポイント

1. **Alt テキストは必須** - 各画像に対して`alt`フィールドが必須です
2. **EXIFメタデータの削除推奨** - アップロード前にメタデータをストリップすることを推奨しています
3. **Blobの有効期限** - アップロード後、投稿に参照されないBlobは数分〜数時間で自動削除されます
4. **アスペクト比の指定** - 画像の幅・高さを取得して埋め込むと、レイアウトが最適化されます

```python
from PIL import Image

# アスペクト比を取得して指定
with Image.open('image.png') as im:
    width, height = im.size

# Embed作成時に追加
embed = {
    "images": [{
        "alt": "説明",
        "image": blob,
        "aspectRatio": {
            "width": width,
            "height": height
        }
    }]
}
```

### 2.3 HTTP 実装例（依存性最小化）

**直接 HTTP API を呼び出す場合**:

```python
import requests
from pathlib import Path

def upload_and_post_image(access_token: str, user_did: str, text: str, image_path: str):
    """画像をアップロードして投稿"""

    # ステップ1: 画像をBlobとしてアップロード
    with open(image_path, 'rb') as f:
        image_data = f.read()

    blob_response = requests.post(
        "https://bsky.social/xrpc/com.atproto.repo.uploadBlob",
        data=image_data,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "image/jpeg"  # 実装で自動判定
        }
    )

    blob = blob_response.json()["blob"]

    # ステップ2: 投稿を作成（画像埋め込み付き）
    post_record = {
        "$type": "app.bsky.feed.post",
        "text": text,
        "createdAt": "2025-12-17T09:55:16Z",
        "embed": {
            "$type": "app.bsky.embed.images",
            "images": [{
                "image": blob,
                "alt": "Posted image"
            }]
        }
    }

    requests.post(
        "https://bsky.social/xrpc/com.atproto.repo.createRecord",
        json={
            "repo": user_did,
            "collection": "app.bsky.feed.post",
            "record": post_record
        },
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
    )
```

### 📚 参考資料

- **公式ドキュメント：** https://docs.bsky.app/docs/advanced-guides/posts
- **Blob仕様：** https://atproto.com/specs/blob
- **atproto Python ライブラリ：** `pip install atproto`

---

## 3. リンクカード埋め込み

### 📋 概要

リンクカード（外部 embed）は、投稿の下部に URL のプレビューを表示する機能です。
OGP（Open Graph Protocol）メタデータを取得して、タイトル・説明・サムネイル画像を表示します。

### ⚠️ embed フィールドの Union 型制限

Bluesky の `embed` フィールドは **1種類のembedのみ** を保持できます（Union 型）：

```json
// ❌ これはできない（複数の embed）
{
  "embed": {
    "$type": "app.bsky.embed.external"  // リンクカード
  },
  "embed": {
    "$type": "app.bsky.embed.images"    // 画像（重複不可）
  }
}

// ✅ これはできる（embed は1つのみ）
{
  "embed": {
    "$type": "app.bsky.embed.external"  // リンクカード「または」
  }
}
```

### 🎯 3シナリオの条件分岐

| シナリオ | 状態 | テキスト | URLハイパーリンク | 画像embed | リンクcard embed |
|---------|------|--------|-----------------|----------|-----------------|
| **1** | プラグインなし | ✅ | ✅ | ❌ | ✅ |
| **2** | プラグイン＋画像有効 | ✅ | ✅ | ✅ | ❌ |
| **3** | プラグイン＋画像無効 | ✅ | ✅ | ❌ | ✅ |

#### シナリオ1: プラグイン無しの場合

**処理**:
```
テキスト投稿
├─ URLをハイパーリンク化（Facet）
└─ URLをリンクカードとして埋め込み（external embed）
```

**実装**:
```python
# bluesky_v2.py
def post_video_minimal(self, video: dict) -> bool:
    # ...
    use_link_card = video.get("use_link_card", True)  # デフォルト: True

    if use_link_card and video_url:
        embed = self._build_external_embed(video_url)
    else:
        embed = video.get("embed")
    # ...
```

#### シナリオ2: プラグインあり + 画像投稿有効

**処理**:
```
テキスト投稿
├─ URLをハイパーリンク化（Facet）
├─ 画像を embed として埋め込み（images embed）
└─ リンクカードは「使用しない」
```

**実装**:
```python
# bluesky_plugin.py
def post_video(self, video: dict) -> bool:
    # ... 画像処理 ...

    if embed:  # 画像がある場合
        video["embed"] = embed
        video["use_link_card"] = False  # リンクカード機能を無効化

    return self.minimal_poster.post_video_minimal(video)
```

#### シナリオ3: プラグインあり + 画像投稿無効

**処理**:
```
テキスト投稿
├─ URLをハイパーリンク化（Facet）
└─ URLをリンクカードとして埋め込み（external embed）
    （画像 embed は「使用しない」）
```

**実装**:
```python
# bluesky_plugin.py
def post_video(self, video: dict) -> bool:
    # ... 画像処理 ...

    if not embed:  # 画像がない場合
        video["use_link_card"] = True  # リンクカード機能を有効化
    else:
        video["use_link_card"] = False

    return self.minimal_poster.post_video_minimal(video)
```

### 🔧 実装方法

#### 1. OGP メタデータ取得

```python
import requests
from bs4 import BeautifulSoup

def fetch_ogp_data(url: str) -> dict:
    """URL から OGP メタデータを取得"""
    try:
        resp = requests.get(url, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")

        og_title = soup.find("meta", property="og:title")
        og_desc = soup.find("meta", property="og:description")
        og_image = soup.find("meta", property="og:image")

        return {
            "title": og_title["content"] if og_title else "No title",
            "description": og_desc["content"] if og_desc else "No description",
            "image_url": og_image["content"] if og_image else None
        }
    except Exception as e:
        post_logger.warning(f"⚠️ OGP 取得失敗: {e}")
        return None
```

#### 2. 画像アップロード（OGP 画像用）

```python
def upload_image_blob(image_url: str) -> dict:
    """OGP 画像を Blob としてアップロード"""
    try:
        # 画像をダウンロード
        img_resp = requests.get(image_url, timeout=10)
        img_resp.raise_for_status()

        # Bluesky にアップロード
        upload_resp = requests.post(
            "https://bsky.social/xrpc/com.atproto.repo.uploadBlob",
            headers={
                "Content-Type": img_resp.headers.get("Content-Type", "image/jpeg"),
                "Authorization": f"Bearer {self.access_token}"
            },
            data=img_resp.content
        )
        return upload_resp.json()["blob"]
    except Exception as e:
        post_logger.warning(f"⚠️ 画像アップロード失敗: {e}")
        return None
```

#### 3. リンクカード embed 構築

```python
def build_external_embed(url: str) -> dict:
    """リンクカード embed を構築"""
    ogp_data = fetch_ogp_data(url)
    if not ogp_data:
        return None

    embed = {
        "$type": "app.bsky.embed.external",
        "external": {
            "uri": url,
            "title": ogp_data["title"][:100],  # 最大100文字
            "description": ogp_data["description"][:256]  # 最大256文字
        }
    }

    # 画像がある場合は Blob をアップロード
    if ogp_data.get("image_url"):
        blob = upload_image_blob(ogp_data["image_url"])
        if blob:
            embed["external"]["thumb"] = blob

    return embed
```

### 📌 重要なポイント

| 項目 | 説明 |
|------|------|
| **OGP タグの完全性** | `og:title` と `og:description` が必須 |
| **画像サイズ制限** | OGP 画像は 1MB 以下 |
| **リンクカードの表示** | Bluesky クライアント側で OGP が有効なページのみ表示 |
| **embed の Union 型** | 画像 OR リンクカード、どちらか一方のみ |
| **DRY RUN 対応** | DRY RUN 時はダミー embed を返す |
| **use_link_card フラグ** | 画像有無に応じて適切に設定する必要あり |

---

## 4. DRY RUN（投稿テスト）機能

### 📋 概要

DRY RUN（投稿テスト）機能により、実際には Bluesky に投稿せず、**投稿処理をシミュレート** することができます。
これにより、本投稿前にテンプレート・リサイズ処理・リンクカード設定などの確認ができます。

### ✅ v2.1.0+ での実装

#### 実装コンポーネント

| ファイル | 実装内容 |
|---------|--------|
| `plugins/bluesky_plugin.py` | `set_dry_run()` メソッド追加 |
| `bluesky_v2.py` | `set_dry_run()` メソッド追加、ダミーデータ返却 |
| `plugin_manager.py` | `post_video_with_all_enabled()` に `dry_run` パラメータ追加 |
| `gui_v2.py` | 投稿設定ウィンドウで「🧪 投稿テスト」ボタン実装 |

#### フラグの伝播フロー

```
GUI: 「🧪 投稿テスト」ボタン をクリック
  ↓
gui_v2.py: _execute_post(dry_run=True) を呼び出し
  ↓
plugin_manager.post_video_with_all_enabled(video, dry_run=True)
  ↓
bluesky_plugin.set_dry_run(True) 実行
  ↓
bluesky_v2.set_dry_run(True) 実行
  ↓
投稿処理実行
  ├─ テキスト・Facet は通常通り構築
  ├─ 画像処理は通常通り実行（リサイズ・品質最適化）
  ├─ Blob アップロードはダミーデータで代替
  └─ API.createRecord は実行「しない」
  ↓
結果: ログに投稿内容が記録され、DB は更新「されない」
```

#### 実装方法

**1. プラグインに `set_dry_run()` メソッドを追加**

```python
# plugins/bluesky_plugin.py
def set_dry_run(self, dry_run: bool):
    """ドライランモードを設定"""
    self.dry_run = dry_run
    if hasattr(self.minimal_poster, 'set_dry_run'):
        self.minimal_poster.set_dry_run(dry_run)
    logger.info(f"🧪 Bluesky プラグイン DRY RUN モード: {dry_run}")
```

**2. コアモジュールに `set_dry_run()` メソッドを追加**

```python
# bluesky_v2.py
def set_dry_run(self, dry_run: bool):
    """ドライランモードを設定"""
    self.dry_run = dry_run
    logger.info(f"🧪 Bluesky コア DRY RUN モード: {dry_run}")
```

**3. API呼び出し時に DRY RUN チェック**

```python
# bluesky_v2.py::post_video_minimal()
def post_video_minimal(self, video: dict) -> bool:
    # ... 投稿データ構築 ...

    if self.dry_run:
        post_logger.info(f"🧪 [DRY RUN] 投稿をシミュレート")
        post_logger.info(f"投稿テキスト: {post_data['record']['text'][:100]}...")
        return True  # ★ API呼び出しはしない

    # 通常投稿
    response = requests.post(
        "https://bsky.social/xrpc/com.atproto.repo.createRecord",
        # ...
    )
    return response.status_code == 200
```

**4. Blob アップロード時のダミーデータ**

```python
# bluesky_v2.py::_upload_blob()
def _upload_blob(self, file_path: str) -> tuple:
    # DRY RUN モード時はダミー blob を返す
    if self.dry_run:
        post_logger.info(f"🧪 [DRY RUN] 画像アップロード（スキップ）: {file_path}")
        dummy_blob = {
            "$type": "blob",
            "mimeType": "image/jpeg",
            "size": 143948,
            "link": {"$link": "bafkreidummy_for_test"}
        }
        return (dummy_blob, 1200, 627)  # ★ タプルで返す

    # 通常のアップロード処理
    # ...
```

**5. プラグインマネージャーで dry_run フラグを伝播**

```python
# plugin_manager.py
def post_video_with_all_enabled(self, video: dict, dry_run: bool = False) -> Dict[str, bool]:
    """
    すべての有効なプラグインで動画をポスト

    Args:
        video: 動画情報辞書
        dry_run: DRY RUN モード（デフォルト: False）
    """
    results = {}

    for plugin_name, plugin in self.enabled_plugins.items():
        # ★ dry_run フラグをプラグインに設定
        if hasattr(plugin, 'set_dry_run'):
            plugin.set_dry_run(dry_run)

        # 投稿実行
        result = plugin.post_video(video)
        results[plugin_name] = result

    return results
```

**6. GUI から DRY RUN フラグを渡す**

```python
# gui_v2.py
def _execute_post(self, dry_run=False):
    """投稿を実行"""
    # ...
    if use_image:
        # ★ dry_run フラグを渡す
        results = self.plugin_manager.post_video_with_all_enabled(
            video_with_settings,
            dry_run=dry_run
        )
    else:
        # ★ dry_run フラグを設定
        if hasattr(self.bluesky_core, 'set_dry_run'):
            self.bluesky_core.set_dry_run(dry_run)

    # ...
```

#### DRY RUN vs 本投稿の動作比較

| 動作 | DRY RUN | 本投稿 |
|------|--------|--------|
| テキスト構築 | ✅ 実行 | ✅ 実行 |
| Facet 構築 | ✅ 実行 | ✅ 実行 |
| 画像リサイズ | ✅ 実行 | ✅ 実行 |
| 画像品質最適化 | ✅ 実行 | ✅ 実行 |
| Blob アップロード | ❌ ダミーデータ | ✅ 実行 |
| API.createRecord | ❌ スキップ | ✅ 実行 |
| DB 更新 | ❌ 更新なし | ✅ selected=False 更新 |
| ユーザーフィードバック | 🧪 テスト完了 | ✅ 投稿完了 |

#### ログ出力例

**DRY RUN 実行時:**
```
2025-12-17 10:15:30,001 [INFO] 🧪 Bluesky プラグイン DRY RUN モード: True
2025-12-17 10:15:30,150 [INFO] 🧪 [DRY RUN] 画像アップロード（スキップ）: /path/to/image.jpg
2025-12-17 10:15:30,200 [INFO] 🧪 [DRY RUN] 投稿をシミュレート
2025-12-17 10:15:30,201 [INFO] 投稿テキスト: 【Twitch同時配信】新着動画です...
2025-12-17 10:15:30,202 [INFO] 🧪 投稿テスト完了
```

#### 実装ファイル

| ファイル | 行数 | 実装内容 |
|---------|------|--------|
| `plugins/bluesky_plugin.py` | 446-451 | `set_dry_run()` メソッド |
| `bluesky_v2.py` | 60-62, 215-235 | `set_dry_run()` メソッド、ダミーデータ戻り値 |
| `plugin_manager.py` | 220-240 | `dry_run` パラメータ伝播 |
| `gui_v2.py` | 1263-1330 | 「🧪 投稿テスト」ボタン実装 |

---

## 5. GUI投稿設定ウィンドウ

### 📋 概要

投稿設定ウィンドウ（`PostSettingsWindow`）により、ユーザーは投稿前に以下を調整できます：

- **画像添付の有無** - 画像を含める / テキスト+URLのみ
- **画像リサイズ設定** - 小さい画像を拡大するか
- **投稿方法の選択** - 本投稿 / テスト投稿
- **画像プレビュー表示** - 実際に投稿される画像を確認

### ✅ v2.1.0+ での実装

#### GUI レイアウト

```
┌───────────────────────────────────────────────────────────────┐
│ 投稿設定 - [動画タイトル]                                    │
├───────────────────────────────────────────────────────────────┤
│                                                               │
│ ☑ 画像を添付する                                              │
│                                                               │
│ ☑ 小さい画像を拡大する                                        │
│                                                               │
│ ┌─ プレビュー ─────────────────────────────────────────────┐  │
│ │  [画像サムネイル 100×67px]                               │  │
│ │                                                           │  │
│ │  元画像: 1280×720px (132.1KB)                            │  │
│ │  投稿時: 1200×627px (140.6KB)                            │  │
│ │  投稿方法: 画像 + テキスト（AspectRatio付き）            │  │
│ └─────────────────────────────────────────────────────────┘  │
│                                                               │
├───────────────────────────────────────────────────────────────┤
│ [✅ 投稿] [🧪 投稿テスト] [❌ キャンセル]                     │
└───────────────────────────────────────────────────────────────┘
```

#### 実装方法

**1. 投稿設定ウィンドウクラス定義**

```python
# gui_v2.py
class PostSettingsWindow:
    """投稿前の設定を調整するウィンドウ"""

    def __init__(self, parent, video, image_path, plugin_manager, db):
        self.window = tk.Toplevel(parent)
        self.window.title(f"投稿設定 - {video['title'][:40]}")
        self.window.geometry("600x500")
        self.window.resizable(False, False)

        self.video = video
        self.image_path = image_path
        self.plugin_manager = plugin_manager
        self.db = db

        # チェックボックス状態
        self.use_image_var = tk.BooleanVar(value=True)
        self.resize_small_var = tk.BooleanVar(value=True)

        self._setup_ui()

    def _setup_ui(self):
        """UI をセットアップ"""
        # チェックボックス
        ttk.Checkbutton(
            self.window,
            text="画像を添付する",
            variable=self.use_image_var,
            command=self._on_image_toggle
        ).pack(pady=10)

        ttk.Checkbutton(
            self.window,
            text="小さい画像を拡大する",
            variable=self.resize_small_var
        ).pack(pady=5)

        # プレビューフレーム
        preview_frame = ttk.LabelFrame(self.window, text="プレビュー")
        preview_frame.pack(pady=10, padx=10, fill="both", expand=True)

        # 画像プレビュー
        self._load_preview_image(preview_frame)

        # 投稿方法情報
        info_frame = ttk.Frame(preview_frame)
        info_frame.pack(pady=5)

        self.info_label = ttk.Label(info_frame, text="")
        self.info_label.pack()

        # ボタン
        button_frame = ttk.Frame(self.window)
        button_frame.pack(pady=10)

        ttk.Button(
            button_frame,
            text="✅ 投稿",
            command=self._post
        ).pack(side="left", padx=5)

        ttk.Button(
            button_frame,
            text="🧪 投稿テスト",
            command=self._dry_run
        ).pack(side="left", padx=5)

        ttk.Button(
            button_frame,
            text="❌ キャンセル",
            command=self.window.destroy
        ).pack(side="left", padx=5)

        # 初期表示
        self._update_info_label()

    def _load_preview_image(self, parent):
        """投稿される画像のプレビューを表示"""
        if not self.image_path or not Path(self.image_path).exists():
            ttk.Label(parent, text="（画像なし）").pack()
            return

        try:
            img = Image.open(self.image_path)
            original_size = img.size

            # 100×67px のサムネイル生成
            img.thumbnail((100, 67), Image.Resampling.LANCZOS)
            self.preview_photo = ImageTk.PhotoImage(img)

            preview_label = ttk.Label(parent, image=self.preview_photo)
            preview_label.pack(pady=5)

            # サイズ情報を表示
            size_info = f"元画像: {original_size[0]}×{original_size[1]}px"
            ttk.Label(parent, text=size_info, font=("Arial", 9)).pack()
        except Exception as e:
            logger.warning(f"プレビュー生成失敗: {e}")

    def _update_info_label(self):
        """投稿方法情報を更新"""
        if self.use_image_var.get():
            text = "投稿方法: 画像 + テキスト（AspectRatio付き）"
        else:
            text = "投稿方法: テキスト + URLリンクカード"
        self.info_label.config(text=text)

    def _on_image_toggle(self):
        """画像添付チェックボックスの変更イベント"""
        self._update_info_label()

    def _post(self):
        """本投稿を実行"""
        self._execute_post(dry_run=False)

    def _dry_run(self):
        """投稿テストを実行"""
        self._execute_post(dry_run=True)

    def _execute_post(self, dry_run=False):
        """投稿を実行"""
        use_image = self.use_image_var.get()
        resize_small = self.resize_small_var.get()

        # 動画情報に設定を付加
        video_with_settings = dict(self.video)
        video_with_settings["use_image"] = use_image
        video_with_settings["resize_small_images"] = resize_small
        video_with_settings["image_source"] = "database"

        try:
            if use_image and self.image_path:
                # 画像添付投稿
                results = self.plugin_manager.post_video_with_all_enabled(
                    video_with_settings,
                    dry_run=dry_run
                )
            else:
                # テキスト+URLのみ
                if hasattr(self.bluesky_core, 'set_dry_run'):
                    self.bluesky_core.set_dry_run(dry_run)
                results = {"text_only": True}

            # 成功メッセージ
            msg = f"{'✅ 投稿テスト完了' if dry_run else '✅ 投稿完了'}\n\n"
            msg += f"{self.video['title'][:60]}...\n\n"
            msg += f"投稿方法: {'画像' if use_image else 'URLリンクカード'}"
            messagebox.showinfo("成功", msg)

            # 本投稿の場合、DB を更新
            if not dry_run:
                self.db.update_selection(
                    self.video["video_id"],
                    selected=False,
                    scheduled_at=None
                )
                logger.info(f"選択状態を更新: {self.video['video_id']} (selected=False)")

            # 窓を閉じる（テスト投稿でも本投稿でも）
            self.window.destroy()

        except Exception as e:
            messagebox.showerror("エラー", f"投稿処理エラー:\n{str(e)}")
            logger.error(f"投稿処理エラー: {e}", exc_info=True)
```

**2. GUI メインから投稿設定ウィンドウを起動**

```python
# gui_v2.py::_on_post_settings_clicked()
def _on_post_settings_clicked(self):
    """投稿設定ボタン（📤 投稿設定）が クリックされた"""
    selection = self.tree.selection()
    if not selection:
        messagebox.showwarning("警告", "動画を選択してください")
        return

    item_id = selection[0]
    video_id = self.tree.item(item_id)["values"][0]

    # DB から動画情報を取得
    video = self.db.get_video_by_id(video_id)
    if not video:
        messagebox.showerror("エラー", f"動画が見つかりません: {video_id}")
        return

    # 画像パスを取得（存在すれば）
    image_path = None
    if video.get("image_path"):
        image_path = video["image_path"]

    # 投稿設定ウィンドウを起動
    PostSettingsWindow(
        parent=self.root,
        video=video,
        image_path=image_path,
        plugin_manager=self.plugin_manager,
        db=self.db
    )
```

**3. GUI メインのボタン配置**

```python
# gui_v2.py::_setup_toolbar()
button_frame = ttk.Frame(self.root)
button_frame.pack(side="top", fill="x", padx=5, pady=5)

ttk.Button(
    button_frame,
    text="🧪 投稿テスト",
    command=self._on_post_test_clicked
).pack(side="left", padx=2)

ttk.Button(
    button_frame,
    text="📤 投稿設定",
    command=self._on_post_settings_clicked
).pack(side="left", padx=2)
```

#### 投稿設定ウィンドウの機能

| 機能 | 説明 | 実装済み |
|------|------|--------|
| チェックボックス | 画像添付の有無を選択 | ✅ |
| チェックボックス | 小さい画像を拡大するか | ✅ |
| 画像プレビュー | 100×67px のサムネイル表示 | ✅ |
| サイズ情報 | 元画像のサイズを表示 | ✅ |
| 投稿方法表示 | 選択状態に応じて表示更新 | ✅ |
| 本投稿ボタン | 実際に投稿を実行 | ✅ |
| 投稿テストボタン | DRY RUN で投稿をシミュレート | ✅ |
| キャンセル | ウィンドウを閉じる | ✅ |

#### ログ出力例

**投稿テスト実行時:**
```
2025-12-17 10:15:30,001 [INFO] 🧪 投稿テスト開始: video_id=-Vnx9CUo
2025-12-17 10:15:30,050 [INFO] ✅ 投稿テスト完了
```

**本投稿実行時:**
```
2025-12-17 10:20:15,001 [INFO] ✅ 投稿開始: video_id=-Vnx9CUo
2025-12-17 10:20:15,150 [INFO] ✅ Bluesky 投稿成功
2025-12-17 10:20:15,151 [INFO] 選択状態を更新: -Vnx9CUo (selected=False)
2025-12-17 10:20:15,152 [INFO] ✅ 投稿完了
```

#### 実装ファイル

| ファイル | 行数 | 実装内容 |
|---------|------|--------|
| `gui_v2.py` | 1100-1333 | PostSettingsWindow クラス |
| `gui_v2.py` | 150-200 | ボタンイベント実装 |

---

## 6. 実装チェックリスト

### Rich Text Facet（リンク化）

| 項目 | 状態 | 確認 |
|------|------|------|
| HTTP API で実装 | ✅ | `requests` ライブラリのみ |
| UTF-8 バイトオフセット計算 | ✅ | 日本語 URL 対応 |
| Facet 構造が正確 | ✅ | `$type` = `app.bsky.richtext.facet#link` |
| ISO 8601 形式 createdAt | ✅ | `2025-12-05T09:55:16Z` |
| エラーハンドリング | ✅ | 失敗時も graceful degradation |

### 画像付き投稿

| 項目 | 状態 |
|------|------|
| ライブラリ | ✅ atproto（シンプル実装） / HTTP API（直接実装） |
| Alt テキスト | ✅ 必須実装 |
| EXIFデータ | ✅ ストリップ推奨 |
| アスペクト比 | ✅ 16:9、4:5、1:1 対応 |
| 最大サイズ | ✅ 1MB/画像 |
| **画像自動リサイズ機能** | **✅ v2.1.0+ で実装済み** |

### 画像自動リサイズ機能（v2.1.0+）

| 項目 | 状態 |
|------|------|
| 定数化・設定可能 | ✅ `IMAGE_RESIZE_TARGET_*` 等 |
| アスペクト比別処理 | ✅ 3パターン実装 |
| 横長画像（≥1.3） | ✅ 3:2統一+中央トリミング |
| 正方形/やや横長（0.8-1.3） | ✅ 長辺基準縮小のみ |
| 縦長（<0.8） | ✅ 長辺基準縮小のみ |
| JPEG品質90初期出力 | ✅ 実装済み |
| 900KB超過で品質低下 | ✅ 段階的圧縮 |
| 1MB上限超過でスキップ | ✅ リンクカードのみで投稿 |
| 詳細ログ記録 | ✅ 変換前後の情報 |
| DRY RUN対応 | ✅ テスト可能 |

### リンクカード埋め込み

| 項目 | 状態 |
|------|------|
| OGP メタデータ取得 | ✅ 実装済み |
| 画像 Blob アップロード | ✅ 実装済み |
| 条件分岐ロジック | ✅ 3シナリオ実装済み |
| シナリオ1（プラグインなし） | ✅ リンクカード有効化 |
| シナリオ2（プラグイン+画像有効） | ✅ リンクカード無効化 |
| シナリオ3（プラグイン+画像無効） | ✅ リンクカード有効化 |
| use_link_card フラグ | ✅ 適切に制御 |
| Union 型制限対応 | ✅ 画像 OR リンクカード |

---

## 7. トラブルシューティング

### リンク化されない場合

**原因1：UTF-8 バイト位置が不正**
```python
# ❌ 文字数でカウント（不正）
byte_start = len(text[:match.start()])

# ✅ UTF-8 バイト位置でカウント（正正）
byte_start = len(text[:match.start()].encode('utf-8'))
```

**原因2：createdAt の形式が不正**
```python
# ❌ 不正なフォーマット
"createdAt": "2025-12-05 09:55:16"

# ✅ ISO 8601 形式
"createdAt": "2025-12-05T09:55:16Z"
```

**原因3：$type が不完全**
```python
# ❌ 不正
"$type": "link"

# ✅ 正正
"$type": "app.bsky.richtext.facet#link"
```

### 画像がアップロードできない場合

**原因1：MIME Type が指定されていない**
```python
# ❌ 不正
response = requests.post(url, data=img_data)

# ✅ 正正
response = requests.post(
    url,
    data=img_data,
    headers={"Content-Type": "image/png"}
)
```

**原因2：画像サイズが大きすぎる**
- 最大 1MB（1,000,000 バイト）
- 圧縮処理を追加

**原因3：Alt テキストが不足**
```python
# ❌ 不正
"images": [{"image": blob}]

# ✅ 正正
"images": [{"image": blob, "alt": "画像の説明"}]
```

---

## 📝 実装ファイル

- `v2/plugins/bluesky_plugin.py`: Bluesky 画像添付拡張プラグイン（画像リサイズ＆投稿）
- `v2/bluesky_v2.py`: Bluesky コア認証・投稿管理（Rich Text Facet＆リンクカード）
- `v2/image_manager.py`: 画像ファイル管理

---

## 📚 関連ドキュメント

- [IMAGE_RESIZE_GUIDE.md](./IMAGE_RESIZE_GUIDE.md) - 画像自動リサイズ機能の詳細ガイド
- [IMAGE_RESIZE_IMPLEMENTATION.md](./IMAGE_RESIZE_IMPLEMENTATION.md) - 実装詳細と設定方法
- [IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md) - リンクカード実装計画

---

## 🔗 外部参考資料

- **Bluesky AT Protocol**: https://atproto.com/
- **Bluesky Public API**: https://docs.bsky.app/
- **Rich Text 仕様**: https://docs.bsky.app/docs/advanced-guides/post-richtext
- **Blob API**: https://docs.bsky.app/docs/api/com-atproto-repo-upload-blob
- **atproto Python**: https://github.com/MarshalX/atproto
- **Pillow (PIL)**: https://pillow.readthedocs.io/
- **BeautifulSoup4**: https://www.crummy.com/software/BeautifulSoup/

---

## 🚀 将来の拡張

このガイドを基に、以下の拡張が可能です：

- [ ] **複数の Rich Text 機能** - メンション（@）、ハッシュタグ（#）対応
- [ ] **動画埋め込み** - YouTube、Niconico の動画プレビュー
- [ ] **引用投稿** - 他の投稿への引用機能
- [ ] **スレッド投稿** - 複数投稿の連続投稿
- [ ] **リアクション機能** - リプライ・リポスト・いいね への対応
- [ ] **画像フォーマット対応** - WebP、AVIF 等の新フォーマット
- [ ] **顔認識トリミング** - AI による自動トリミング位置最適化
- [ ] **複数画像一括処理** - 複数画像の同時リサイズ

---

**このドキュメントは v2.1.0+ 実装済みの統合技術資料です。
プラグイン開発・保守時の参考にしてください。**
