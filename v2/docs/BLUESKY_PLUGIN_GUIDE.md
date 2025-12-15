# Bluesky プラグイン実装ガイド

**このドキュメントは、Bluesky プラグイン開発の技術資料です。**
実装済みの仕様と設計パターンを記録しており、将来の拡張機能実装の参考になります。

---

## 📋 目次

1. [Rich Text Facet（リンク化）](#1-rich-text-facetリンク化)
2. [画像付き投稿](#2-画像付き投稿)
3. [実装チェックリスト](#3-実装チェックリスト)
4. [トラブルシューティング](#4-トラブルシューティング)

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

### 🐍 Python実装例（atprotoライブラリ）

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

### 📚 参考資料

- **公式ドキュメント：** https://docs.bsky.app/docs/advanced-guides/posts
- **Blob仕様：** https://atproto.com/specs/blob
- **atproto Python ライブラリ：** `pip install atproto`

---

## 3. 実装チェックリスト

### Rich Text Facet（リンク化）

| 項目 | 状態 | 確認 |
|------|------|------|
| HTTP API で実装 | ✅ | `requests` ライブラリのみ |
| UTF-8 バイトオフセット計算 | ✅ | 日本語 URL 対応 |
| Facet 構造が正確 | ✅ | `$type` = `app.bsky.richtext.facet#link` |
| ISO 8601 形式 createdAt | ✅ | `2025-12-05T09:55:16Z` |
| エラーハンドリング | ✅ | 失敗時も graceful degradation |
| ロギング | ✅ | 全工程を記録 |
| 本番テスト | ✅ | 実装後 3 回の投稿で成功確認 |

### 画像付き投稿

| 項目 | 推奨 |
|------|------|
| ライブラリ | atproto（シンプル実装） |
| Alt テキスト | 必須 |
| EXIFデータ | ストリップ推奨 |
| アスペクト比 | 16:9、4:5、1:1 |
| 最大サイズ | 1MB/画像 |

---

## 4. トラブルシューティング

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

- `bluesky_plugin.py`: Bluesky 投稿処理（HTTP API 実装）
- `bluesky_v2.py`: Bluesky 認証・投稿管理
- `asset_manager.py`: テンプレート・画像自動配置

---

## 🚀 将来の拡張

このガイドを基に、以下の拡張が可能です：

- [ ] **複数の Rich Text 機能** - メンション（@）、ハッシュタグ（#）対応
- [ ] **動画埋め込み** - YouTube、Niconico の動画プレビュー
- [ ] **引用投稿** - 他の投稿への引用機能
- [ ] **スレッド投稿** - 複数投稿の連続投稿
- [ ] **リアクション機能** - リプライ・リポスト・いいね への対応

---

**このドキュメントは v2 実装済みの技術資料です。プラグイン開発時の参考にしてください。**
