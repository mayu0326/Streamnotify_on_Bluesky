# GUI から動画追加機能の使用方法

## 実装内容

- GUI の ツールバーに **「➕ 動画追加」** ボタンを追加しました。\
このボタンから、YouTube の動画IDを指定して直接動画を追加できます。

**v3.4.0+ での変更**: YouTube Live 機能は youtube_api_plugin に統合されました。\
これにより、動画追加時のライブ判定がより正確になります。

## 対応プラットフォーム

| プラットフォーム | 必要なプラグイン | 状態 |
|:--|:--|:--:|
| **YouTube** | youtube_api_plugin | ✅ 対応 |
| **ニコニコ動画** | niconico_plugin | ⚠️ プラグイン必須 |

**ニコニコプラグイン未導入時**: ニコニコ動画追加機能は使用不可です

## 使用方法

### 1. 「➕ 動画追加」ボタンをクリック

GUI のツールバーから「➕ 動画追加」ボタンをクリックします。

```
[🔄再読込] [🌐RSS更新] [🎬Live判定] [➕動画追加]  ← このボタン
```

#### 📌 フィード取得ボタンの表示変更

settings.env の `YOUTUBE_FEED_MODE` 設定により、フィード更新ボタンのテキストが変わります：

| 設定値 | ボタン表示 | 説明 |
|:--|:--|:--|
| `poll` | 🌐 **RSS更新** | RSS ポーリング方式（デフォルト） |
| `websub` | 📡 **新着取得** | WebSub サーバー方式（プッシュ型） |

**例：settings.env で `YOUTUBE_FEED_MODE=websub` に設定した場合**
```
[🔄再読込] [📡新着取得] [🎬Live判定] [➕動画追加]
          ↑ 「RSS更新」から「新着取得」に変わる
```

### 2. プラットフォームを選択

ダイアログで追加したい動画のプラットフォームを選択します：

- **YouTube**: YouTube 動画（推奨）
- **Niconico**: ニコニコ動画（niconico_plugin 必須）

### 3. 動画IDまたは URL を入力

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
①  youtube_api_plugin から動画詳細を自動取得
    ├─ タイトル
    ├─ チャンネル名
    ├─ 公開日時
    └─ コンテンツ種別（video/live/archive）
       ※ Live ステータスも同時に判定（youtube_api_plugin の統合機能）

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
    ├─ コンテンツ種別（video/live/archive/none）
    └─ Live ステータス（none/upcoming/live/completed）

②  ユーザーが情報を入力して「💾 保存」

③  DB に保存
```

**ニコニコプラグイン が有効の場合:**
```
①  niconico_plugin から動画詳細を自動取得
    ├─ タイトル
    ├─ チャンネル名（投稿者名）
    ├─ 公開日時
    └─ サムネイル画像

② DB に自動保存

③ キャッシュに自動追加
```

**ニコニコプラグイン が未導入の場合:**
```
⚠️ ニコニコプラグインが有効化されていません

💡 対応方法:
1. niconico_plugin を有効化してください
2. settings.env で NICONICO_USER_ID を設定してください
   例: NICONICO_USER_ID=12345678
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
- youtube_api_plugin が有効化されていない
- API キーが無効 （settings.env の YOUTUBE_API_KEY）
- API クォータ超過
- ネットワーク接続エラー

**対応:**
1. youtube_api_plugin が有効か確認（GUI プラグイン状態表示）
2. API キーが設定されているか確認
3. 手動入力ダイアログで情報を入力して保存

### エラー 3: 動画は既に存在

```
⚠️ この動画は既に登録されています
```

**原因:** 同じ video_id が既に DB に存在

**対応:** 該当動画を削除してから追加、または RSS ポーリングの重複排除で自動処理

### エラー 4: ニコニコプラグイン未導入（ニコニコ動画追加時）

```
⚠️ ニコニコプラグインが有効化されていません
💡 ニコニコユーザーIDを settings.env で設定してください
```

**原因:**
- niconico_plugin が有効化されていない
- NICONICO_USER_ID が settings.env に設定されていない

**対応:**
1. settings.env で以下を設定：
   ```env
   NICONICO_USER_ID=12345678
   NICONICO_POLL_INTERVAL=10
   ```
2. アプリケーションを再起動
3. niconico_plugin が自動的に読み込まれます

### エラー 5: 不正なニコニコ動画ID

```
❌ 有効なニコニコ動画IDが見つかりませんでした
(例: sm123456789)
```

**対応:** ニコニコ動画の URL または `sm123456789` / `so123456789` 形式の動画ID を入力してください

## 自動キャッシュ登録について

**「仮にそれが動画だった場合このキャッシュにも追加されますか？」への回答:**

✅ **自動的にキャッシュに追加されます**

### 処理フロー

```
add_video_dialog() で入力ダイアログ表示
    ↓
_extract_video_id() で動画IDを抽出
    ↓
━━━━━━━━━━━━━━━━━━━━━━━━━━
┃  youtube_api_plugin 有効判定
━━━━━━━━━━━━━━━━━━━━━━━━━━

┌──有効──────────────────────────┐
│ _add_youtube_video() 実行        │
│ ↓                             │
│ youtube_api_plugin から動画詳細取得
│ ├─ _fetch_video_detail()       │
│ ├─ _classify_video_core()      │
│ │  (ライブ判定を含む)          │
│ ↓                             │
│ DB に直接保存                   │
│ (insert_video)                │
│ ↓                             │
│ キャッシュ自動更新              │
│ (youtube_video_detail_cache.json)│
│ ↓                             │
│ ✅ 成功メッセージ               │
└──────────────────────────────┘

┌──未導入─────────────────────────┐
│ _add_video_manual() で手動入力   │
│ ↓                              │
│ ユーザーが情報を入力             │
│ ↓                              │
│ DB に保存                        │
│ ↓                              │
│ ✅ 成功メッセージ                │
└──────────────────────────────┘
```

### キャッシュ階層

youtube_api_plugin は3段階のキャッシング戦略を採用しています：

```
_fetch_video_detail(video_id)
    │
    ├─ ★ メモリキャッシュ確認
    │   ├─ YES → キャッシュから返却 → 検証完了
    │   └─ NO ↓
    │
    ├─ ★ JSON ファイルキャッシュ確認
    │   ├─ YES → JSON から読み込み → メモリキャッシュに追加
    │   └─ NO ↓
    │
    ├─ YouTube API で取得
    │
    └─ _cache_video_detail() で保存
       ├─ メモリ: self.video_detail_cache
       └─ JSON ファイル: youtube_video_detail_cache.json
```

**優先度**: メモリキャッシュ > JSON キャッシュ > YouTube API

## 実装されたメソッド一覧

### メイン機能

| メソッド | 用途 | 詳細 |
|:--|:--|:--|
| `add_video_dialog()` | ダイアログ表示（動画ID/URL 入力） | ツールバー「➕ 動画追加」ボタンで呼び出し |
| `_add_video_from_id()` | プラットフォーム別の処理分岐 | YouTube / Niconico を判定 |
| `_add_youtube_video()` | YouTube API 連携して動画追加 | youtube_api_plugin を使用 |
| `_add_niconico_video()` | ニコニコ動画を追加 | niconico_plugin 必須 |
| `_extract_video_id()` | YouTube URL から動画ID を抽出 | youtube.com / youtu.be / embed に対応 |
| `_extract_niconico_video_id()` | ニコニコ URL から動画ID を抽出 | nicovideo.jp / nico.ms に対応 |
| `_add_video_manual()` | 手動入力ダイアログ表示 | API 取得失敗時のフォールバック |
| `_video_exists()` | DB 内の動画存在確認 | 重複チェック用 |

### 動画ID 抽出対応 URL パターン

#### YouTube

| URL 形式 | 例 | 抽出可 |
|:--|:--|:--:|
| 動画ID のみ | `dQw4w9WgXcQ` | ✅ |
| youtube.com watch | `https://www.youtube.com/watch?v=dQw4w9WgXcQ` | ✅ |
| youtu.be | `https://youtu.be/dQw4w9WgXcQ` | ✅ |
| embed | `https://www.youtube.com/embed/dQw4w9WgXcQ` | ✅ |

#### ニコニコ動画

| URL 形式 | 例 | 抽出可 |
|:--|:--|:--:|
| 動画ID のみ（sm形式） | `sm123456789` | ✅ |
| 動画ID のみ（so形式） | `so123456789` | ✅ |
| nicovideo.jp URL | `https://www.nicovideo.jp/watch/sm123456789` | ✅ |
| nico.ms 短縮 URL | `https://nico.ms/sm123456789` | ✅ |

**注記**: ニコニコプラグイン未導入時は ニコニコ ID の抽出に失敗します

## 今後の拡張予定

- [ ] 複数動画の一括追加（CSV インポート）
- [ ] YouTube プレイリスト から一括追加
- [ ] ドラッグ&ドロップ URL 入力
- [ ] 定期的なキャッシュ更新機能

---

**実装日**: 2025-12-24
**対応バージョン**: v3.2.0+
**最終更新**: 2026-01-03
**ステータス**: ✅ 実装完了（v3.4.0+ 準拠）

---

## 最新更新内容（v3.4.0+）

### プラグイン構造の変更

- v3.4.0 で YouTube Live 機能が youtube_api_plugin に統合されました
- youtube_live_plugin（独立プラグイン）は廃止
- youtube_api_plugin が以下の機能を統合：
  - 動画詳細取得（title, channel, published_at など）
  - ライブ判定（video/live/archive/schedule の分類）
  - 状態遷移検知（upcoming → live → completed）
  - キャッシュ管理（3段階階層化）

### 動画追加時の判定精度向上

動画追加時に youtube_api_plugin の `_classify_video_core()` メソッドを使用することで、以下が正確に判定されます：

#### コンテンツ種別 (content_type)
- `video`: 通常動画
- `live`: ライブ配信
- `archive`: ライブアーカイブ
- `schedule`: 予約枠
- `none`: 判定不可

#### ライブステータス (live_status)
- `upcoming`: 配信予定
- `live`: 配信中
- `completed`: 配信終了
- `none`: 該当なし

### キャッシュ自動管理の改善

3段階のキャッシング戦略により、API 呼び出しを最小化：

1. **メモリキャッシュ**: セッション中の動画詳細を保持
2. **JSON ファイルキャッシュ**: `v3/data/youtube_video_detail_cache.json` に永続化
3. **YouTube API**: キャッシュが無い場合のみ呼び出し

この設計により、同じ動画を複数回追加する場合、実質 0 コストで追加可能です。
