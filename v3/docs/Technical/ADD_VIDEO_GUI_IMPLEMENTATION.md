# GUI 動画追加機能 - 実装完了

**実装日**: 2025-12-24
**対応バージョン**: v3.2.0+
**ステータス**: ✅ **実装完了・テスト可能**

---

## 📋 実装内容

StreamNotify v3 GUI に「**➕ 動画追加**」機能を実装しました。

### 機能概要

YouTube の動画IDを指定して、DB に直接動画を追加できます。

```
【 GUI ツールバー 】

[🔄再読込] [🌐RSS更新] [🎬Live判定] [➕動画追加] ← 新機能！
                                    │
                                    └─ クリックでダイアログ表示
                                        ├─ 動画ID/URL 入力
                                        │  ↓
                                        ├─ YouTube API から自動取得
                                        │  または
                                        ├─ 手動入力
                                        │  ↓
                                        └─ DB に自動保存
                                           + キャッシュ追加
```

---

## 🚀 使用方法

### ステップ 1: 「➕ 動画追加」ボタンをクリック

GUI ツールバーから「➕ 動画追加」ボタンをクリック

### ステップ 2: 動画ID または URL を入力

以下のいずれかで入力可能：

- `dQw4w9WgXcQ` （動画ID）
- `https://www.youtube.com/watch?v=dQw4w9WgXcQ` （youtube.com）
- `https://youtu.be/dQw4w9WgXcQ` （短縮 URL）
- `https://www.youtube.com/embed/dQw4w9WgXcQ` （embed）

### ステップ 3: 「✅ 追加」をクリック

#### パターン A: YouTube API プラグイン有効の場合

```
①  API から動画詳細を自動取得
    ├─ タイトル
    ├─ チャンネル名
    ├─ 公開日時
    └─ コンテンツ種別

②  DB に自動保存

③  キャッシュに自動追加
    └─ youtube_video_detail_cache.json
```

**結果**: ✅ 成功メッセージ → DB 更新

#### パターン B: YouTube API プラグイン未導入の場合

```
①  手動入力ダイアログが表示

②  ユーザーが以下を入力：
    ├─ 動画ID（表示）
    ├─ タイトル*（必須）
    ├─ チャンネル名
    ├─ 公開日時*（デフォルト: 現在時刻）
    └─ コンテンツ種別

③  「💾 保存」をクリック
    └─ DB に保存
```

**結果**: ✅ 成功メッセージ → DB 更新

---

## 📊 処理フロー

```
「➕ 動画追加」ボタン
     ↓
add_video_dialog()
├─ ダイアログ作成
├─ ユーザー入力待機
     ↓
_add_video_from_id(input_value)
├─ _extract_video_id(input_value)
│  └─ URL または ID から video_id を抽出
│     ※ 複数の URL 形式に対応
     ↓
plugin_manager.get_enabled_plugins()
     ↓
━━━━━━━━━━━━━━━━━
┃ YouTube API プラグイン判定
━━━━━━━━━━━━━━━━━

【 有効の場合 】
youtube_api_plugin.fetch_video_detail(video_id)
     ↓
_fetch_video_detail()
├─ キャッシュ確認
├─ なければ API 取得
└─ _cache_video_detail() で自動保存
     ↓
post_video(video_dict) で DB 保存
     ↓
✅ 成功メッセージ → refresh_data()

【 未導入の場合 】
_add_video_manual(video_id)
     ↓
手動入力ダイアログ表示
     ↓
db.insert_video() で DB 保存
     ↓
✅ 成功メッセージ → refresh_data()
```

---

## 🔧 実装メソッド

### メイン機能

#### `add_video_dialog()`
- **役割**: 動画追加ダイアログを表示
- **入力**: ユーザーが動画ID/URL を入力
- **処理**: `_add_video_from_id()` を呼び出し
- **UI**: Toplevel ウィンドウで独立ダイアログ表示

#### `_add_video_from_id(input_value: str)`
- **役割**: 入力値から動画を追加
- **処理**:
  1. `_extract_video_id()` で video_id を抽出
  2. YouTube API プラグインを検索
  3. `fetch_video_detail()` で動画詳細を取得
  4. `post_video()` で DB 保存
  5. 成功/失敗メッセージ表示
- **エラー時**: `_add_video_manual()` で手動入力ダイアログ表示

#### `_extract_video_id(input_value: str) -> str`
- **役割**: URL または動画ID から video_id を抽出
- **対応形式**:
  - `dQw4w9WgXcQ` → そのまま返却
  - `https://www.youtube.com/watch?v=XXXXX` → XXXXX 抽出
  - `https://youtu.be/XXXXX` → XXXXX 抽出
  - `https://www.youtube.com/embed/XXXXX` → XXXXX 抽出
- **返却値**: 11 文字の video_id または None
- **正規表現**: `[a-zA-Z0-9_-]{11}`

#### `_add_video_manual(video_id: str)`
- **役割**: 手動入力ダイアログを表示
- **入力フィールド**:
  - 動画ID（読み取り専用）
  - タイトル*（必須）
  - チャンネル名
  - 公開日時*（デフォルト: 現在時刻）
  - コンテンツ種別（video/live/archive/none）
- **保存処理**: `db.insert_video()` で DB 保存

#### `_video_exists(video_id: str) -> bool`
- **役割**: 動画が DB に存在するか確認
- **処理**: `db.get_all_videos()` で全動画と比較
- **戻り値**: True（存在）/ False（未登録）

---

## ✅ 自動キャッシュ登録について

**Q: 仮にそれが動画だった場合このキャッシュにも追加されますか？**

**A: はい、自動的にキャッシュに追加されます**

### キャッシュ追加処理

```
_add_video_from_id()
     ↓
youtube_api_plugin.fetch_video_detail(video_id)
     ↓
_fetch_video_detail(video_id)
├─ キャッシュ確認
│  └─ ヒット → キャッシュから返却
│
├─ キャッシュミス
│  └─ API で取得
│     ↓
│     _cache_video_detail(video_id, details)
│     ├─ メモリに保存: self.video_detail_cache[video_id] = details
│     ├─ タイムスタンプ記録: self.cache_timestamps[video_id] = time.time()
│     └─ JSON 永続化: _save_video_detail_cache()
│
└─ 詳細情報を返却

キャッシュファイル: v3/data/youtube_video_detail_cache.json
```

### キャッシュの有効期限

- **メモリ**: アプリケーション実行中は有効
- **ファイル**: `youtube_video_detail_cache.json` に永続保存

### キャッシュの再利用

次回、同じ動画ID でアクセスする場合：
```
→ _fetch_video_detail() 呼び出し
  └─ キャッシュから即座に返却（API 呼び出しなし）
     └─ レート制限消費なし
```

---

## 🐛 エラーハンドリング

### エラー 1: 不正な動画ID / URL 形式

**メッセージ**: ❌ 有効な YouTube 動画IDが見つかりませんでした

**原因**:
- URL 形式が未対応
- 11 文字以外の動画ID

**対応**: 以下のいずれかで入力
- `dQw4w9WgXcQ`
- `https://www.youtube.com/watch?v=dQw4w9WgXcQ`
- `https://youtu.be/dQw4w9WgXcQ`

### エラー 2: YouTube API での取得失敗

**メッセージ**: ⚠️ YouTube API での取得に失敗しました

**原因**:
- API キーが無効
- ネットワーク接続エラー
- API クォータ超過
- 動画が削除/プライベート化

**対応**:
- YouTube API プラグイン の設定確認
- API キーが有効か確認
- またはユーザーが手動入力ダイアログで情報を入力

### エラー 3: 動画は既に登録

**メッセージ**: ⚠️ この動画は既に登録されています

**原因**: 同じ video_id が既に DB に存在

**対応**:
- 既存エントリを削除してから追加
- または、RSS ポーリングの自動重複排除で対応

---

## 📝 ログ出力例

### 成功時

```
🔍 動画追加を開始: dQw4w9WgXcQ
✅ 抽出された動画ID: dQw4w9WgXcQ
🌐 YouTube API から動画情報を取得: dQw4w9WgXcQ
✅ 動画情報を取得しました: dQw4w9WgXcQ
✅ 動画を追加しました: dQw4w9WgXcQ
```

### API 取得失敗 → 手動入力

```
🔍 動画追加を開始: https://www.youtube.com/watch?v=dQw4w9WgXcQ
✅ 抽出された動画ID: dQw4w9WgXcQ
🌐 YouTube API から動画情報を取得: dQw4w9WgXcQ
⚠️ YouTube API での取得に失敗しました: dQw4w9WgXcQ
✅ 動画を手動追加しました: dQw4w9WgXcQ
```

---

## 📁 ファイル修正箇所

### `v3/gui_v3.py`

#### 修正 1: ツールバーに「➕ 動画追加」ボタン追加

```python
# Line 70: ボタンを追加
ttk.Button(toolbar, text="➕ 動画追加", command=self.add_video_dialog).pack(side=tk.LEFT, padx=2)
```

#### 追加メソッド（Line 1909～2158）

- `add_video_dialog()` - ダイアログ表示
- `_add_video_from_id(input_value)` - API 取得＆ DB 保存
- `_video_exists(video_id)` - 動画存在確認
- `_extract_video_id(input_value)` - URL/ID から video_id 抽出
- `_add_video_manual(video_id)` - 手動入力ダイアログ

---

## 🧪 テスト方法

### 実装確認

1. GUI を起動
2. ツールバーの「➕ 動画追加」ボタンを確認
3. ボタンをクリック
4. ダイアログが表示されることを確認

### 動画ID 抽出テスト

```python
from gui_v3 import StreamNotifyGUI
import tkinter as tk

root = tk.Tk()
root.withdraw()
gui = StreamNotifyGUI(root, db)

# テスト 1: 動画ID のみ
assert gui._extract_video_id("dQw4w9WgXcQ") == "dQw4w9WgXcQ"

# テスト 2: youtube.com URL
assert gui._extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"

# テスト 3: youtu.be URL
assert gui._extract_video_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

# テスト 4: 不正な形式
assert gui._extract_video_id("invalid") is None

root.destroy()
```

### 動画追加テスト

1. YouTube 動画の URL を用意（例: https://www.youtube.com/watch?v=dQw4w9WgXcQ）
2. 「➕ 動画追加」ボタンをクリック
3. URL を入力して「✅ 追加」をクリック
4. DB に動画が追加されたか確認
5. `youtube_video_detail_cache.json` にキャッシュが追加されたか確認

---

## 🔄 連携システム

### 他のプラグインとの連携

```
動画追加
     ↓
youtube_api_plugin.post_video()
     ↓
database.insert_video()
├─ YouTube 優先度ベース重複排除
├─ deleted_video_cache との連携
     ↓
youtube_live_plugin (オプション)
├─ Live/Archive 判定
└─ 自動投稿判定
     ↓
bluesky_plugin (オプション)
└─ 自動投稿処理
```

### RSS ポーリングとの関係

```
RSS ポーリング
├─ 新着動画検出
└─ insert_video()
     ↓
━━━━━━━━━━━━━━━━━━
┃ UNIQUE 制約で重複排除
━━━━━━━━━━━━━━━━━━

手動追加した動画も RSS で発見
→ video_id の UNIQUE 制約で自動判定
→ 既存として扱われる
```

---

## 🎯 今後の拡張予定

- [ ] **一括追加**: CSV/JSON から複数動画を一括登録
- [ ] **プレイリスト追加**: YouTube プレイリスト URL から全動画追加
- [ ] **ドラッグ&ドロップ**: URL をドラッグして追加
- [ ] **スケジュール登録**: 特定時刻に自動投稿
- [ ] **キャッシュ管理**: GUI からキャッシュをクリア/更新

---

## 📌 重要な設計原則

1. **自動キャッシュ追加**: API 取得時は自動的にキャッシュに追加
2. **手動フォールバック**: API 失敗時は手動入力ダイアログで対応
3. **重複排除**: UNIQUE 制約と RSS ポーリングで自動処理
4. **ログ記録**: すべての操作を `logs/post.log` に記録
5. **エラーメッセージ**: 日本語でわかりやすく表示

---

**実装完了**: 2025-12-24
**対応バージョン**: v3.2.0+
**ステータス**: ✅ 本番環境対応可能
