# Bluesky API リンクカード仕様ガイド

## 概要

Blueskyでは、URLをテキスト内でハイパーリンク化する方法と、URLをリンクカード（Webカード）として埋め込む方法の2つの手段があります。これらは異なる仕組みで実装され、APIでの投稿時に使い分ける必要があります。

---

## 1. URLのハイパーリンク化（Facets）

### 仕組み

**Facets（リッチテキスト）** は、投稿本文内のテキスト範囲に対して装飾情報を付与する仕組みです。URLの場合は `app.bsky.richtext.facet#link` タイプを使用します。

### 実装構造

```json
{
  "$type": "app.bsky.feed.post",
  "text": "✨ example mentioning @atproto.com to share the URL 👨❤️👨 https://en.wikipedia.org/wiki/CBOR.",
  "createdAt": "2023-08-08T01:03:41.157302Z",
  "facets": [
    {
      "index": {
        "byteStart": 74,
        "byteEnd": 108
      },
      "features": [
        {
          "$type": "app.bsky.richtext.facet#link",
          "uri": "https://en.wikipedia.org/wiki/CBOR"
        }
      ]
    }
  ]
}
```

### 重要なポイント

- **byteStart / byteEnd**: UTF-8エンコーディングの**バイト位置**（文字数ではない）
  - 開始位置は**包括的**（inclusive）
  - 終了位置は**排他的**（exclusive）、つまり終了位置は含まれない
  - `byteEnd - byteStart` でリンク対象テキストの長さを計算可能

- **Unicode/絵文字への対応**: 絵文字を含むテキストでバイト位置を計算する場合、UTF-8のバイト単位で正確にカウントする必要があります

- **複数のfacets**: 1つの投稿に複数のURLやメンションを含められ、各々に対してfacetsを配列で指定

### Python実装例

```python
import re
from typing import List, Dict

def parse_urls(text: str) -> List[Dict]:
    """テキストからURLを抽出してバイト位置情報を取得"""
    spans = []
    # URLのパターンマッチ正規表現
    url_regex = rb"[$|\W](https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*[-a-zA-Z0-9@%_\+~#//=])?)"
    
    text_bytes = text.encode("UTF-8")
    for m in re.finditer(url_regex, text_bytes):
        spans.append({
            "start": m.start(1),
            "end": m.end(1),
            "url": m.group(1).decode("UTF-8"),
        })
    return spans

def parse_facets(text: str) -> List[Dict]:
    """テキストからfacetsを生成"""
    facets = []
    
    for u in parse_urls(text):
        facets.append({
            "index": {
                "byteStart": u["start"],
                "byteEnd": u["end"],
            },
            "features": [
                {
                    "$type": "app.bsky.richtext.facet#link",
                    "uri": u["url"],
                }
            ],
        })
    
    return facets

# 使用例
text = "Check out https://example.com for more info!"
post = {
    "$type": "app.bsky.feed.post",
    "text": text,
    "createdAt": "2023-08-08T01:03:41.157302Z",
    "facets": parse_facets(text)
}
```

---

## 2. リンクカード（外部embed）

### 仕組み

**外部embed** (`app.bsky.embed.external`) は、投稿の下部に「カード」形式でURLのプレビューを表示する機能です。この方法では、URLのメタデータ（タイトル、説明、サムネイル画像）をクライアント側で取得し、Blueskyサーバーに埋め込んで投稿します。

### 実装構造

```json
{
  "$type": "app.bsky.feed.post",
  "text": "post which embeds an external URL as a card",
  "createdAt": "2023-08-07T05:46:14.423045Z",
  "embed": {
    "$type": "app.bsky.embed.external",
    "external": {
      "uri": "https://bsky.app",
      "title": "Bluesky Social",
      "description": "See what's next.",
      "thumb": {
        "$type": "blob",
        "ref": {
          "$link": "bafkreiash5eihfku2jg4skhyh5kes7j5d5fd6xxloaytdywcvb3r3zrzhu"
        },
        "mimeType": "image/png",
        "size": 23527
      }
    }
  }
}
```

### 必須フィールド

| フィールド | 型 | 説明 | 必須 |
|-----------|-----|------|-----|
| `uri` | string | リンク対象のURL | ✅ |
| `title` | string | リンクのタイトル（OGP取得） | ✅ |
| `description` | string | リンクの説明文（OGP取得） | ✅ |
| `thumb` | blob | サムネイル画像（OGP画像をアップロード） | ❌ |

### OGP（Open Graph Protocol）の取得

OGPは、HTMLの`<meta>`タグを通じてWebページのメタデータを提供する標準です。Blueskyではこれらのメタデータを活用してリンクカードを生成します。

#### 主要なOGPタグ

```html
<meta property="og:title" content="ページタイトル" />
<meta property="og:description" content="ページの説明" />
<meta property="og:image" content="https://example.com/image.png" />
<meta property="og:image:type" content="image/png" />
<meta property="og:image:width" content="1200" />
<meta property="og:image:height" content="630" />
<meta property="og:image:alt" content="画像の代替テキスト" />
```

#### Python実装例（OGP取得）

```python
import requests
from bs4 import BeautifulSoup
from typing import Dict, Optional

def fetch_ogp_data(url: str) -> Dict[str, Optional[str]]:
    """URLからOGPデータを取得"""
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"Error fetching URL: {e}")
        return {
            "title": "",
            "description": "",
            "image_url": None
        }
    
    soup = BeautifulSoup(resp.text, "html.parser")
    
    # OGPタグを解析
    title_tag = soup.find("meta", property="og:title")
    description_tag = soup.find("meta", property="og:description")
    image_tag = soup.find("meta", property="og:image")
    
    return {
        "title": title_tag["content"] if title_tag else "",
        "description": description_tag["content"] if description_tag else "",
        "image_url": image_tag["content"] if image_tag else None
    }
```

### 画像アップロード（Blob化）

Blueskyのリンクカードにサムネイル画像を含める場合、画像をBlueskyのサーバーにアップロードし、返された**blob**オブジェクトを使用します。

#### APIエンドポイント

```
POST https://bsky.social/xrpc/com.atproto.repo.uploadBlob
```

#### リクエストヘッダ

```
Content-Type: <画像のMIMEタイプ>（例：image/png, image/jpeg）
Authorization: Bearer <アクセストークン>
```

#### リクエストボディ

画像ファイルのバイナリデータをそのまま送信

#### レスポンス例

```json
{
  "blob": {
    "$type": "blob",
    "ref": {
      "$link": "bafkreiash5eihfku2jg4skhyh5kes7j5d5fd6xxloaytdywcvb3r3zrzhu"
    },
    "mimeType": "image/png",
    "size": 23527
  }
}
```

#### Python実装例（画像アップロード）

```python
import requests
from typing import Dict, Optional

def upload_blob(access_token: str, image_bytes: bytes, mime_type: str) -> Optional[Dict]:
    """画像をBlueskyにアップロード"""
    try:
        resp = requests.post(
            "https://bsky.social/xrpc/com.atproto.repo.uploadBlob",
            headers={
                "Content-Type": mime_type,
                "Authorization": f"Bearer {access_token}",
            },
            data=image_bytes,
        )
        resp.raise_for_status()
        return resp.json()["blob"]
    except requests.RequestException as e:
        print(f"Error uploading blob: {e}")
        return None
```

### 画像サイズ制限

- 最大サイズ: **1,000,000バイト（約1MB）**
- 推奨フォーマット: PNG, JPEG, WebP
- メタデータ削除の推奨: EXIF情報やその他のメタデータは投稿前に削除することが推奨されています

---

## 3. リンクカード完全実装例

### 統合実装（OGP取得 + 画像アップロード + リンクカード作成）

```python
import requests
from bs4 import BeautifulSoup
from typing import Dict, Optional
from datetime import datetime, timezone

class BlueskyLinkCardBuilder:
    """Blueskyリンクカード作成クラス"""
    
    def __init__(self, access_token: str, pds_url: str = "https://bsky.social"):
        self.access_token = access_token
        self.pds_url = pds_url
    
    def fetch_ogp_data(self, url: str) -> Dict[str, Optional[str]]:
        """URLからOGPデータを取得"""
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"Error fetching URL: {e}")
            return {"title": "", "description": "", "image_url": None}
        
        soup = BeautifulSoup(resp.text, "html.parser")
        
        title_tag = soup.find("meta", property="og:title")
        desc_tag = soup.find("meta", property="og:description")
        img_tag = soup.find("meta", property="og:image")
        
        # og:imageがURLの場合、相対URLを絶対URLに変換
        img_url = img_tag["content"] if img_tag else None
        if img_url and "://" not in img_url:
            # URLスキームがない場合、ベースURLを付加
            from urllib.parse import urljoin
            img_url = urljoin(url, img_url)
        
        return {
            "title": title_tag["content"] if title_tag else "",
            "description": desc_tag["content"] if desc_tag else "",
            "image_url": img_url
        }
    
    def upload_blob(self, image_bytes: bytes, mime_type: str) -> Optional[Dict]:
        """画像をBlueskyにアップロード"""
        try:
            resp = requests.post(
                f"{self.pds_url}/xrpc/com.atproto.repo.uploadBlob",
                headers={
                    "Content-Type": mime_type,
                    "Authorization": f"Bearer {self.access_token}",
                },
                data=image_bytes,
            )
            resp.raise_for_status()
            return resp.json()["blob"]
        except requests.RequestException as e:
            print(f"Error uploading blob: {e}")
            return None
    
    def fetch_image(self, image_url: str) -> Optional[tuple]:
        """画像URLから画像データを取得"""
        try:
            resp = requests.get(image_url, timeout=10)
            resp.raise_for_status()
            mime_type = resp.headers.get("Content-Type", "image/png")
            return resp.content, mime_type
        except requests.RequestException as e:
            print(f"Error fetching image: {e}")
            return None
    
    def build_external_embed(self, url: str) -> Optional[Dict]:
        """リンクカードembedを作成"""
        # OGPデータ取得
        ogp_data = self.fetch_ogp_data(url)
        
        embed_data = {
            "uri": url,
            "title": ogp_data["title"],
            "description": ogp_data["description"],
        }
        
        # 画像がある場合、アップロード
        if ogp_data["image_url"]:
            image_result = self.fetch_image(ogp_data["image_url"])
            if image_result:
                image_bytes, mime_type = image_result
                blob = self.upload_blob(image_bytes, mime_type)
                if blob:
                    embed_data["thumb"] = blob
        
        return {
            "$type": "app.bsky.embed.external",
            "external": embed_data
        }

# 使用例
builder = BlueskyLinkCardBuilder(access_token="your_access_token")
embed = builder.build_external_embed("https://example.com")
print(embed)
```

---

## 4. Facets と Embeds の使い分け

### embedは1種類のみ（Union型）

Blueskyの投稿では、**embed フィールドは1つの種類のembedのみを保持できます**（Union型）。複数のembedを同時に持つことはできません。

```json
// ❌ これはできない（embed は1つのみ）
{
  "embed": {
    "$type": "app.bsky.embed.external",  // リンクカード
    "external": { ... }
  },
  "embed": {
    "$type": "app.bsky.embed.images",    // 画像（重複のため不可）
    "images": [ ... ]
  }
}

// ✅ これはできる（embed は1つ）
{
  "embed": {
    "$type": "app.bsky.embed.images",
    "images": [ ... ]
  }
}
```

### 対応表

| 機能 | フィールド | 対応型 | 複数同時使用 |
|------|-----------|--------|-----------|
| URLをテキスト内でハイパーリンク化 | `facets` | `app.bsky.richtext.facet#link` | ✅ （複数URL可） |
| リンクカード（Webカード） | `embed` | `app.bsky.embed.external` | ❌ （embedは1種類） |
| 画像埋め込み | `embed` | `app.bsky.embed.images` | ✅ （最大4枚） |
| 動画埋め込み | `embed` | `app.bsky.embed.video` | ❌ （1動画のみ） |
| 引用リポスト | `embed` | `app.bsky.embed.record` | ❌ （1投稿のみ） |

### 実装上の推奨パターン

#### パターン1: ハイパーリンク + リンクカード（embed無し）

```python
post = {
    "$type": "app.bsky.feed.post",
    "text": "Check out this link: https://example.com",
    "createdAt": get_timestamp(),
    "facets": parse_facets("Check out this link: https://example.com"),
    "embed": builder.build_external_embed("https://example.com")
}
```

本文にはURLが記載され、さらに下部にリンクカードが表示されます。

#### パターン2: ハイパーリンク + 画像（embed使用）

```python
post = {
    "$type": "app.bsky.feed.post",
    "text": "Check out this link: https://example.com",
    "createdAt": get_timestamp(),
    "facets": parse_facets("Check out this link: https://example.com"),
    "embed": {
        "$type": "app.bsky.embed.images",
        "images": [image_blob_data]
    }
}
```

リンクカードembedを使わず、代わりに画像を表示します。

#### パターン3: 画像のみ（embed使用、facets無し）

```python
post = {
    "$type": "app.bsky.feed.post",
    "text": "Beautiful photo!",
    "createdAt": get_timestamp(),
    "embed": {
        "$type": "app.bsky.embed.images",
        "images": [image_blob_data]
    }
}
```

URLハイパーリンクもリンクカードも不要な場合。

---

## 5. 実装上の注意点

### UTF-8バイト位置の計算

Facetsのバイト位置計算時、JavaScriptやPythonのネイティブ文字列関数は**文字単位**でカウントします。emoji含む場合は特に注意：

```python
# ❌ 間違い（文字数でカウント）
text = "Hello 👨 World"
start = text.index("👨")  # 6
end = start + 1            # 7

# ✅ 正しい（UTF-8バイト数でカウント）
text = "Hello 👨 World"
text_bytes = text.encode("UTF-8")
# b'Hello \xf0\x9f\x91\xa8 World'
# 絵文字は4バイト
start = len("Hello ".encode("UTF-8"))  # 6
end = len("Hello 👨".encode("UTF-8"))  # 10
```

### タイムスタンプ形式

投稿時の`createdAt`フィールドは**ISO 8601形式**で、末尾に `Z` を付ける必要があります：

```python
from datetime import datetime, timezone

# ✅ 正しい形式
now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
# 結果: "2023-08-08T01:03:41.157302Z"
```

### OGP取得時のタイムアウト

Webサイトからのメタデータ取得時、タイムアウトを設定して無限待機を防ぐ：

```python
# タイムアウト10秒
resp = requests.get(url, timeout=10)
```

### 画像フォーマットとメタデータ

アップロード前に、EXIF情報などのメタデータを削除することが推奨されています：

```python
from PIL import Image
import io

# PILで画像を再保存することでメタデータを削除
def strip_image_metadata(image_bytes: bytes) -> bytes:
    img = Image.open(io.BytesIO(image_bytes))
    # メタデータなしで再保存
    output = io.BytesIO()
    # EXIF情報を持たないフォーマットで保存
    img.save(output, format=img.format, exif=b"")
    return output.getvalue()
```

---

## 6. 関連API エンドポイント

### 投稿作成

```
POST /xrpc/com.atproto.repo.createRecord

Body:
{
  "repo": "did:...",
  "collection": "app.bsky.feed.post",
  "record": { /* post object */ }
}
```

### 画像アップロード

```
POST /xrpc/com.atproto.repo.uploadBlob

Headers:
- Content-Type: <mime-type>
- Authorization: Bearer <token>

Body: <binary-image-data>
```

### セッション作成

```
POST /xrpc/com.atproto.server.createSession

Body:
{
  "identifier": "user.bsky.social",
  "password": "app-password"
}
```

---

## 7. トラブルシューティング

| 問題 | 原因 | 解決策 |
|------|------|--------|
| リンクカードが表示されない | OGPメタデータが取得できていない | サイトのog:title, og:descriptionを確認 |
| バイト位置エラー（facets） | UTF-8バイト数の計算ミス | UTF-8エンコード後にバイト位置を計算 |
| 画像アップロード失敗 | ファイルサイズが1MBを超過 | 画像を圧縮してサイズを削減 |
| embedが複数表示されない | embed = union（1種類のみ） | 画像かリンクカード、どちらかに統一 |
| タイムスタンプ不正 | Z記号忘れやタイムゾーン混在 | ISO 8601形式で末尾にZ を付ける |

---

## 参考資料

- [Bluesky API 公式ドキュメント - Posts](https://docs.bsky.app/docs/advanced-guides/posts)
- [Bluesky API 公式ドキュメント - Rich Text](https://docs.bsky.app/docs/advanced-guides/post-richtext)
- [Bluesky API 公式ドキュメント - Creating a post](https://docs.bsky.app/blog/create-post)
- [Open Graph Protocol](https://ogp.me/)
- [AT Protocol Lexicon - app.bsky.embed.external](https://atproto.blue/en/latest/atproto/atproto_client.models.app.bsky.embed.external.html)