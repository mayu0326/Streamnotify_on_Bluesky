# Rich Text Facet 仕様書 - Bluesky投稿テキストのリンク化

**ドキュメント作成日**: 2025-12-18
**バージョン**: v2.1.0+
**対応範囲**: StreamNotify on Bluesky v2 コア機能

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

## 今後の拡張予定

- [ ] メンション（@）対応
- [ ] 絵文字の詳細処理
- [ ] カスタムハッシュタグルール
- [ ] ハッシュタグのバリデーション強化

---

**最終更新**: 2025-12-18 04:50
**更新者**: StreamNotify Development
