# GUI から動画追加機能の使用方法

## 実装内容

GUI の ツールバーに **「➕ 動画追加」** ボタンを追加しました。このボタンから、YouTube の動画IDを指定して直接動画を追加できます。

## 使用方法

### 1. 「➕ 動画追加」ボタンをクリック

GUI のツールバーから「➕ 動画追加」ボタンをクリックします。

```
[🔄再読込] [🌐RSS更新] [🎬Live判定] [➕動画追加]  ← このボタン
```

### 2. 動画IDまたは URL を入力

以下のいずれかの形式で入力できます：

#### パターン 1: 動画ID（11文字）
```
dQw4w9WgXcQ
```

#### パターン 2: youtube.com/watch?v= URL
```
https://www.youtube.com/watch?v=dQw4w9WgXcQ
```

#### パターン 3: youtu.be 短縮 URL
```
https://youtu.be/dQw4w9WgXcQ
```

#### パターン 4: embed URL
```
https://www.youtube.com/embed/dQw4w9WgXcQ
```

### 3. 「✅ 追加」をクリック

入力した動画IDから以下の処理が自動実行されます：

**YouTube API プラグイン が有効の場合:**
```
①  API から動画詳細を自動取得
    ├─ タイトル
    ├─ チャンネル名
    ├─ 公開日時
    └─ コンテンツ種別（video/live/archive）

② DB に自動保存

③ キャッシュに自動追加（youtube_video_detail_cache.json）
```

**YouTube API プラグイン が未導入の場合:**
```
①  手動入力ダイアログが表示
    ├─ 動画ID（表示）
    ├─ タイトル*（必須）
    ├─ チャンネル名
    ├─ 公開日時*（必須、デフォルト: 現在時刻）
    └─ コンテンツ種別（video/live/archive/none）

②  ユーザーが情報を入力して「💾 保存」

③  DB に保存
```

## 処理フロー図

```
「➕ 動画追加」ボタン
    ↓
ダイアログ表示（動画ID/URL入力）
    ↓
動画IDを抽出
    ↓
━━━━━━━━━━━━━━━━━━━━━━━
┃  YouTube API プラグイン判定
━━━━━━━━━━━━━━━━━━━━━━━

┌──有効─────────────────────┐
│ YouTube API から動画詳細取得 │
│ ↓                       │
│ post_video() で DB 保存  │
│ ↓                       │
│ 自動キャッシュ追加        │
│ ↓                       │
│ ✅ 成功メッセージ         │
└─────────────────────────┘

┌──未導入────────────────────┐
│ 手動入力ダイアログ表示      │
│ ↓                        │
│ ユーザー入力 → DB 保存    │
│ ↓                        │
│ ✅ 成功メッセージ         │
└──────────────────────────┘
```

## エラーハンドリング

### エラー 1: 不正な動画ID / URL 形式

```
❌ 有効な YouTube 動画IDが見つかりませんでした
```

**対応:** YouTube 動画の URL または 11 文字の動画ID を入力してください

### エラー 2: YouTube API での取得失敗

```
⚠️ YouTube API での取得に失敗しました
手動で動画情報を入力してください
```

**原因:**
- API キーが無効
- API クォータ超過
- ネットワーク接続エラー

**対応:** 手動入力ダイアログで情報を入力して保存

### エラー 3: 動画は既に存在

```
⚠️ この動画は既に登録されています
```

**原因:** 同じ video_id が既に DB に存在

**対応:** 該当動画を削除してから追加、または RSS ポーリングの重複排除で自動処理

## 自動キャッシュ登録について

**「仮にそれが動画だった場合このキャッシュにも追加されますか？」への回答:**

✅ **自動的にキャッシュに追加されます**

### 処理フロー

```
add_video_dialog()
    ↓
_add_video_from_id()
    ↓
youtube_api_plugin.fetch_video_detail(video_id)
    ↓
_fetch_video_detail() 実行
    │
    ├─ キャッシュ確認
    │   ├─ YES → キャッシュから返却
    │   └─ NO ↓
    │
    ├─ API で取得
    │
    └─ _cache_video_detail() で保存
       ├─ memory: self.video_detail_cache
       └─ JSON: youtube_video_detail_cache.json
```

### キャッシュファイルの場所

```
v3/data/youtube_video_detail_cache.json
```

### キャッシュの内容例

```json
{
  "_uY5dZ4xSvw": {
    "kind": "youtube#video",
    "etag": "...",
    "id": "_uY5dZ4xSvw",
    "snippet": {
      "title": "【新作】...",
      "channelTitle": "チャンネル名"
    },
    "liveStreamingDetails": {...}
  }
}
```

## 実装されたメソッド一覧

### メイン機能

| メソッド | 用途 |
|:--|:--|
| `add_video_dialog()` | ダイアログ表示（動画ID/URL 入力） |
| `_add_video_from_id()` | API 取得＆ DB 保存処理 |
| `_extract_video_id()` | URL から動画ID を抽出 |
| `_add_video_manual()` | 手動入力ダイアログ表示 |
| `_video_exists()` | DB 内の動画存在確認 |

### 動画ID 抽出対応 URL パターン

| URL 形式 | 例 | 抽出可 |
|:--|:--|:--:|
| 動画ID のみ | `dQw4w9WgXcQ` | ✅ |
| youtube.com watch | `https://www.youtube.com/watch?v=dQw4w9WgXcQ` | ✅ |
| youtu.be | `https://youtu.be/dQw4w9WgXcQ` | ✅ |
| embed | `https://www.youtube.com/embed/dQw4w9WgXcQ` | ✅ |

## 今後の拡張予定

- [ ] 複数動画の一括追加（CSV インポート）
- [ ] YouTube プレイリスト から一括追加
- [ ] ドラッグ&ドロップ URL 入力
- [ ] 定期的なキャッシュ更新機能

---

**実装日**: 2025-12-24
**対応バージョン**: v3.2.0+
**ステータス**: ✅ 実装完了
