# Bluesky リンク化 完全ガイド

## ✅ 問題解決完了

**YouTube URL が Bluesky で正式なリンク（クリック可能）として表示されるようになりました。**

---

## 📋 問題と原因

### 問題
投稿本文に YouTube URL を含めても、Bluesky でリンク化されず、テキストのままだった。

### 原因
Bluesky API は X（旧 Twitter）と異なり、**テキストに含まれる URL を自動的にリンク化しない**。

代わりに、**Rich Text フォーマット（Facet）** で URL の位置を明示的に指定する必要がある。

---

## ✨ 解決方法

### 1. HTTP API で直接実装

**atproto ライブラリの依存性を排除**し、`requests` で Bluesky API を直接呼び出す。

```python
# 認証
POST https://bsky.social/xrpc/com.atproto.server.createSession

# 投稿（Rich Text 対応）
POST https://bsky.social/xrpc/com.atproto.repo.createRecord
```

### 2. Rich Text Facet の正確な構築

**重要な仕様：**

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

### 3. createdAt の正しい形式

```python
# ❌ 間違い
"createdAt": "Fri, 05 Dec 2025 09:55:00 GMT"

# ✅ 正しい（ISO 8601）
"createdAt": "2025-12-05T09:55:00Z"
```

---

## 🔑 実装の重要ポイント

### byteStart/byteEnd の計算

**UTF-8 エンコード後のバイト位置を使用**

```python
text = "【動画】https://example.com"

# 「【動画】」= 12 バイト（UTF-8 マルチバイト）
# 「https://example.com」= 21 バイト

byte_start = len(text[:match.start()].encode('utf-8'))  # = 12
byte_end = len(text[:match.end()].encode('utf-8'))      # = 33
```

### Facet の送信

```python
post_record = {
    "$type": "app.bsky.feed.post",
    "text": post_text,
    "createdAt": created_at,
    "facets": facets  # Rich Text 情報
}

response = requests.post(
    "https://bsky.social/xrpc/com.atproto.repo.createRecord",
    json={
        "repo": self.did,
        "collection": "app.bsky.feed.post",
        "record": post_record
    },
    headers={
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
)
```

---

## 📚 参考資料

- **Bluesky 公式ドキュメント**: https://docs.bsky.app/docs/advanced-guides/post-richtext
- **PHP 実装例**: https://www.spokenlikeageek.com/2023/11/08/posting-to-bluesky-via-the-api-from-php-part-three-links/

---

## 🎯 実装チェックリスト

- ✅ HTTP API で直接実装（atproto ライブラリ不要）
- ✅ UTF-8 バイトオフセットで Facet を構築
- ✅ `$type` に完全な型名 `app.bsky.richtext.facet#link` を指定
- ✅ `createdAt` を ISO 8601 形式で設定
- ✅ `facets` を post_record に含める
- ✅ エラーハンドリング強化

---

## 🚀 動作確認

期待されるログ：

```
📍 Facet を構築しています...
  🔗 URL 検出: https://www.youtube.com/watch?v=xxxxx
     バイト位置: 42 - 67
  ✅ Facet 作成: bytes 42-67 → https://www.youtube.com/watch?v=xxxxx
📍 投稿: text=97 文字, facets=1 個
   facets: [{'byteStart': 42, 'byteEnd': 67}]
✅ Bluesky に投稿しました（リンク化）
```

Bluesky での表示：
- ✅ URL がクリック可能なリンクになっている
- ✅ リンク先のプレビュー（OG タグ）が表示される可能性がある

---

## 📝 実装ファイル

- `bluesky_plugin.py`: Bluesky 投稿処理（HTTP API 実装）
- `requirements.txt`: 依存ライブラリ

---

## 🎉 完成！

YouTube Notifier on Bluesky で、動画投稿時に Bluesky にリンク化された投稿が自動投稿されるようになりました。
