# v3 GUI Live 実装修正 - クイックガイド

**実装日**: 2026-01-03
**対応対象**: v3.3.0+

---

## 修正内容サマリー

GUI の 2 つの Live ボタン処理を、v3 で統合された **YouTube API プラグイン内の Live モジュール**に対応させました。

### 修正項目

| ボタン | メソッド | 修正内容 |
|:--|:--|:--|
| **🎬 Live判定** | `classify_youtube_live_manually()` | YouTubeAPI プラグイン + live_module.poll_lives() を使用 |
| **🎬 Live設定** | `youtube_live_settings()` | YouTubeAPI プラグイン存在確認に変更 |

---

## 動作確認方法

### 前提条件

- ✅ `YOUTUBE_API_KEY` が `settings.env` に設定されている
- ✅ YouTube API プラグインが正常にロードされている（プラグイン情報で確認可）

### 確認手順

1. **GUI を起動**
   ```bash
   python main_v3.py
   ```

2. **プラグイン状態を確認**
   - 「プラグイン情報」ボタンをクリック
   - `YouTubeAPI 連携プラグイン` が ✅有効 で表示されることを確認

3. **Live ポーリングを実行**
   - 「🎬 Live判定」ボタンをクリック
   - メッセージが表示されてポーリング開始
   - 完了メッセージが表示されて DB が更新される

4. **Live 設定を確認**
   - 「🎬 Live設定」ボタンをクリック
   - 投稿タイミング設定パネルが表示される

---

## ログメッセージ（参考）

### ポーリング実行時

```
[INFO] YouTube Live ポーリング完了: 3 件のイベントを処理
[INFO] 🎬 【配信開始イベント】 dQw4w9WgXcQ
[INFO] 🎬 【配信終了イベント】 jNQXAC9IVRw
[INFO] 🎬 【アーカイブ公開イベント】 9bZkp7q19f0
```

### 設定保存時

```
[INFO] ✅ YouTube Live 設定を保存しました（API プラグイン経由）
```

---

## トラブルシューティング

### 問題: ImportError が表示される

```
Live モジュールのインポートに失敗しました。
v3 の plugins/youtube/live_module.py が正しくインストールされていることを確認してください。
```

**対応**:
- `v3/plugins/youtube/live_module.py` が存在することを確認
- ファイルが破損していないか確認
- Python パスが正しく設定されているか確認

### 問題: YouTube API プラグインが見つからない

```
YouTube API プラグインが導入されていません。
YOUTUBE_API_KEY を settings.env に設定してください。
```

**対応**:
1. `settings.env` を開く
2. 以下の行を探して API キーを設定
   ```env
   YOUTUBE_API_KEY=AIzaSyDXQ9sv3...
   ```
3. アプリを再起動

---

## 関連ファイル

| ファイル | 説明 |
|:--|:--|
| `v3/gui_v3.py` | GUI メイン（修正対象） |
| `v3/plugins/youtube/live_module.py` | Live 処理を実装 |
| `v3/plugins/youtube/youtube_api_plugin.py` | API プラグイン（親） |
| `v3/LIVE_BUTTON_IMPLEMENTATION_V3.md` | 詳細仕様書 |

---

**最後の確認**: すべての修正が完了し、テスト可能な状態です。
