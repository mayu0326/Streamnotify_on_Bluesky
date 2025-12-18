# Rich Text Facet 仕様書 - Bluesky投稿テキストのリンク化

**ドキュメント作成日**: 2025-12-18
**バージョン**: v3.1.0+
**対応範囲**: StreamNotify on Bluesky v3 コア機能

---

## 概要

Bluesky への投稿時に、投稿テキスト（`post_text`）内の **URL** と **ハッシュタグ** を自動的に検出し、Bluesky の Rich Text Facet として構築し、クライアント上でハイパーリンクとして表示する機能です。

この機能は **コア機能**（`bluesky_core.py`）に実装されており、**プラグイン有無にかかわらず常に有効**です。

---

## 対応する Rich Text 要素

### 1. URL Facet（リンク）

| 項目 | 値 |
|------|-----|
| **検出対象** | `http://` または `https://` で始まる URL |
| **Facet Type** | `app.bsky.richtext.facet#link` |
| **Feature 構造** | `{ "$type": "app.bsky.richtext.facet#link", "uri": "<URL>" }` |
| **実装関数** | `_build_facets_for_url()` 内の URL パターン処理 |

**例：**
```
投稿テキスト: "動画を見る: https://www.youtube.com/watch?v=abc123"
検出結果: https://www.youtube.com/watch?v=abc123 → facet#link
表示: クリックリンク化
```

### 2. Hashtag Facet（ハッシュタグ）

| 項目 | 値 |
|------|-----|
| **検出対象** | `#` で始まり、非空白文字で構成される文字列 |
| **Facet Type** | `app.bsky.richtext.facet#tag` |
| **Feature 構造** | `{ "$type": "app.bsky.richtext.facet#tag", "tag": "<タグ名>" }` |
| **実装関数** | `_build_facets_for_url()` 内のハッシュタグパターン処理 |
| **タグ名** | `#` を除いた部分（例：`#YouTube` → `YouTube`） |

**例：**
```
投稿テキスト: "配信中 #ライブ #配信 https://twitch.tv/test"
検出結果:
  - #ライブ → facet#tag (tag: "ライブ")
  - #配信 → facet#tag (tag: "配信")
  - https://twitch.tv/test → facet#link
表示: すべてクリックリンク化
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

### リンクカード完全実装例

#### 統合実装（OGP取得 + 画像アップロード + リンクカード作成）

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

### Facets と Embeds の使い分け

#### embedは1種類のみ（Union型）

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

#### 対応表

| 機能 | フィールド | 対応型 | 複数同時使用 |
|------|-----------|--------|-----------|
| URLをテキスト内でハイパーリンク化 | `facets` | `app.bsky.richtext.facet#link` | ✅ （複数URL可） |
| リンクカード（Webカード） | `embed` | `app.bsky.embed.external` | ❌ （embedは1種類） |
| 画像埋め込み | `embed` | `app.bsky.embed.images` | ✅ （最大4枚） |
| 動画埋め込み | `embed` | `app.bsky.embed.video` | ❌ （1動画のみ） |
| 引用リポスト | `embed` | `app.bsky.embed.record` | ❌ （1投稿のみ） |

#### 実装上の推奨パターン

**パターン1: ハイパーリンク + リンクカード（embed無し）**

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

**パターン2: ハイパーリンク + 画像（embed使用）**

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

**パターン3: 画像のみ（embed使用、facets無し）**

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

## 実装上の注意点

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

## 実装仕様

### 検出ロジック

#### URL パターン
```python
pattern = r'https?://[^\s]+'
```

- `http://` または `https://` で始まる
- 空白まで連続する文字をURL として認識
- マルチバイト文字を含むURLにも対応

#### ハッシュタグパターン
```python
pattern = r'(?:^|\s)(#[^\s#]+)'
```

- 行頭 (`^`) または空白 (`\s`) の直後
- `#` + 連続する非空白・非# 文字
- マルチバイト文字（日本語など）に対応

**マッチ例：**
```
入力: "配信中です #ライブ #配信"
マッチ:
  1. (^|\s) + "#ライブ"  → "#ライブ"
  2. (^|\s) + "#配信"    → "#配信"
```

### Facet 構造

#### URL Facet
```json
{
  "index": {
    "byteStart": 123,
    "byteEnd": 156
  },
  "features": [
    {
      "$type": "app.bsky.richtext.facet#link",
      "uri": "https://www.youtube.com/watch?v=abc123"
    }
  ]
}
```

#### Hashtag Facet
```json
{
  "index": {
    "byteStart": 200,
    "byteEnd": 208
  },
  "features": [
    {
      "$type": "app.bsky.richtext.facet#tag",
      "tag": "YouTube"
    }
  ]
}
```

### バイト位置計算

Bluesky API の仕様に従い、**UTF-8 ベースのバイト位置**を使用します。

**計算方法：**
```python
# byte_start: テキスト開始からマッチ開始までのバイト数
byte_start = len(text[:match.start()].encode('utf-8'))

# byte_end: テキスト開始からマッチ終了までのバイト数
byte_end = len(text[:match.end()].encode('utf-8'))
```

**マルチバイト文字の例：**
```
テキスト: "配信中 #ライブ"
         0    6 8

文字単位: 配(0) 信(1) 中(2) (空白)(3) #(4) ラ(5) イ(6) ブ(7)
バイト単位:
  配: 3バイト (0-3)
  信: 3バイト (3-6)
  中: 3バイト (6-9)
  空白: 1バイト (9-10)
  #: 1バイト (10-11)
  ラ: 3バイト (11-14)
  イ: 3バイト (14-17)
  ブ: 3バイト (17-20)

#ライブ のバイト位置: 10-20
```

---

## 実装位置

### コアファイル: `bluesky_core.py`

**クラス:** `BlueskyMinimalPoster`

**メソッド:** `_build_facets_for_url(self, text: str) -> list`

**呼び出し元:** `post_video_minimal()` 内

```python
def post_video_minimal(self, video: dict) -> bool:
    # ...
    post_logger.info("📍 Facet を構築しています...")
    facets = self._build_facets_for_url(post_text)  # ← ここで呼び出し
    # ...
```

---

## 使用フロー

### 1. 投稿テキスト組み立て

テンプレート機能またはデフォルトテキスト生成で `post_text` を作成：

```python
if text_override:
    # テンプレート生成済み本文（ハッシュタグ含む）
    post_text = text_override
else:
    # デフォルトテキスト
    post_text = f"{title}\n\n🎬 {channel_name}\n📅 {published_at[:10]}\n\n{video_url}"
```

### 2. Facet 検出と構築

```python
facets = self._build_facets_for_url(post_text)
```

戻り値：
- URL facet 0〜N個 + Hashtag facet 0〜N個 を含むリスト
- 要素がない場合は `None`

### 3. 投稿 API への送信

```python
post_record = {
    "$type": "app.bsky.feed.post",
    "text": post_text,
    "createdAt": created_at,
}

if facets:
    post_record["facets"] = facets  # ← facets を追加

# 画像がある場合は embed も追加
if embed:
    post_record["embed"] = embed

# API 送信
response = requests.post(post_url, json=post_record, ...)
```

---

## 対応要件チェック

### ✅ 機能

- [x] URL を自動検出
- [x] ハッシュタグを自動検出
- [x] 複数の URL / ハッシュタグに対応
- [x] マルチバイト文字（日本語など）対応
- [x] UTF-8 ベースのバイト位置計算
- [x] 既存の画像 embed との共存

### ✅ 実装

- [x] `bluesky_core.py` のコア機能化
- [x] プラグイン有無に関わらず常に有効
- [x] テンプレート出力のハッシュタグも対応
- [x] 非テンプレート投稿のハッシュタグも対応

### ✅ テスト

- [x] 基本的なハッシュタグ検出
- [x] URL とハッシュタグの混在
- [x] 日本語ハッシュタグ
- [x] バイト位置計算の正確性
- [x] 実投稿での動作確認

---

## ロギング

### ログレベル: INFO

投稿時に以下のログが出力されます：

```
📍 Facet を構築しています...
  🔗 URL 検出: https://www.youtube.com/watch?v=abc123
     バイト位置: 244 - 287
  #️⃣  ハッシュタグ検出: #YouTube (タグ: YouTube)
     バイト位置: 322 - 330
📍 投稿: text=171 文字, facets=2 個, 画像=True
```

---

## 制限事項と注意

### 1. ハッシュタグの有効性

ハッシュタグは以下の形式のみ検出：
- `#` で始まる
- 空白を含まない
- 非空白文字で構成

**検出されない例：**
```
# YouTube        ← # と次の単語に空白がある
#ライブ中です     ← （実際には検出されます）
##YouTube        ← # が2つ以上
```

### 2. URL の有効性

URL は以下のパターンのみ検出：
- `http://` または `https://` で始まる
- 空白までの文字列

**検出されない例：**
```
ftp://example.com     ← http/https 以外
example.com           ← プロトコル省略
```

### 3. 複数バイト文字

日本語を含む投稿も正しく処理されます：

```
投稿: "配信中 #ライブ https://test.jp"
→ 両方とも正しく検出、バイト位置も正確
```

---

## API 仕様参考

- **Bluesky Rich Text Facet**: https://docs.bsky.app/docs/advanced-guides/post-richtext
- **atProto Facet Model**: https://atproto.blue/en/latest/atproto/atproto_client.models.app.bsky.richtext.facet.html

---

## 関連API エンドポイント

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

## トラブルシューティング

| 問題 | 原因 | 解決策 |
|------|------|--------|
| リンクカードが表示されない | OGPメタデータが取得できていない | サイトのog:title, og:descriptionを確認 |
| バイト位置エラー（facets） | UTF-8バイト数の計算ミス | UTF-8エンコード後にバイト位置を計算 |
| 画像アップロード失敗 | ファイルサイズが1MBを超過 | 画像を圧縮してサイズを削減 |
| embedが複数表示されない | embed = union（1種類のみ） | 画像かリンクカード、どちらかに統一 |
| タイムスタンプ不正 | Z記号忘れやタイムゾーン混在 | ISO 8601形式で末尾にZ を付ける |

---

## API 仕様参考

- **Bluesky Rich Text Facet**: https://docs.bsky.app/docs/advanced-guides/post-richtext
- **Bluesky API 公式ドキュメント - Posts**: https://docs.bsky.app/docs/advanced-guides/posts
- **Bluesky API 公式ドキュメント - Creating a post**: https://docs.bsky.app/blog/create-post
- **Open Graph Protocol**: https://ogp.me/
- **atProto Facet Model**: https://atproto.blue/en/latest/atproto/atproto_client.models.app.bsky.richtext.facet.html
- **AT Protocol Lexicon - app.bsky.embed.external**: https://atproto.blue/en/latest/atproto/atproto_client.models.app.bsky.embed.external.html

---

## 今後の拡張予定

- [ ] メンション（@）対応
- [ ] 絵文字の詳細処理
- [ ] カスタムハッシュタグルール
- [ ] ハッシュタグのバリデーション強化
- [ ] リンクカード画像の自動最適化
- [ ] OGP取得のキャッシング機構

---

**最終更新**: 2025-12-18 11:00
**更新者**: StreamNotify Development
**統合内容**: Rich Text Facet + リンクカード（external embed）仕様書統合版

