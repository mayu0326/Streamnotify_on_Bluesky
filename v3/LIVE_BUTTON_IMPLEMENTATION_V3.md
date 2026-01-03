# GUI Live ボタン実装修正（v3 API プラグイン対応）

**更新日**: 2026-01-03
**バージョン**: v3.3.0+
**対象ファイル**: `v3/gui_v3.py`

---

## 修正概要

v3では YouTube Live プラグインはプラグインとしてではなく、**YouTube API プラグイン内の Live モジュール**として実装されました。これに対応するため、GUI の 2 つのボタン処理を修正しました。

### 修正対象

1. **🎬 Live判定ボタン** → `classify_youtube_live_manually()`
2. **🎬 Live設定ボタン** → `youtube_live_settings()`

---

## 修正内容

### 1. Live判定ボタン（`classify_youtube_live_manually()`）

#### 修正前（v3.2.x 以前）
```python
# YouTubeLive プラグインを取得（存在しない）
youtube_live_plugin = self.plugin_manager.get_plugin("youtube_live_plugin")
if not youtube_live_plugin:
    messagebox.showinfo("情報", "YouTube Live プラグインが導入されていません。\n\n将来的に対応予定です。")
    return
```

#### 修正後（v3.3.0+）
```python
# YouTube API プラグインを取得
youtube_api_plugin = self.plugin_manager.get_plugin("youtube_api_plugin")
if not youtube_api_plugin:
    messagebox.showinfo("情報", "YouTube API プラグインが導入されていません。\nYOUTUBE_API_KEY を settings.env に設定してください。")
    return

# Live モジュールを取得してポーリングを実行
from plugins.youtube.live_module import get_live_module
live_module = get_live_module(plugin_manager=self.plugin_manager)
processed_count = live_module.poll_lives()
```

#### 動作フロー
```
ボタンクリック
  ↓
YouTube API プラグイン確認
  ↓
Live モジュール読み込み
  ↓
live_module.poll_lives() 実行
  ↓
登録済みの Live 動画をポーリング
 - 配信開始検知 (schedule → live)
 - 配信終了検知 (live → completed)
 - アーカイブ公開検知 (completed → archive)
  ↓
結果を表示・DB 再読込
```

### 2. Live設定ボタン（`youtube_live_settings()`）

#### 修正前
```python
# YouTubeLive プラグインを取得（存在しない）
youtube_live_plugin = self.plugin_manager.get_plugin("youtube_live_plugin")
if not youtube_live_plugin:
    messagebox.showinfo("情報", "YouTube Live プラグインが導入されていません。\n\n将来的に対応予定です。")
    return
```

#### 修正後
```python
# YouTube API プラグインを取得
youtube_api_plugin = self.plugin_manager.get_plugin("youtube_api_plugin")
if not youtube_api_plugin:
    messagebox.showinfo("情報", "YouTube API プラグインが導入されていません。\nYOUTUBE_API_KEY を settings.env に設定してください。")
    return
```

#### 設定の意味

この設定パネルは SELFPOST モードでの個別フラグ制御を可能にします：

| 設定項目 | 説明 | デフォルト |
|:--|:--|:--|
| **📌 予約枠（upcoming）** | YouTube Live の放送枠が立った時に投稿 | true |
| **🔴 配信中・終了（live/completed）** | ライブ配信の開始・終了時に投稿 | true |
| **🎬 アーカイブ公開** | ライブ終了後、ビデオとして保存された時に投稿 | true |
| **⏱️ 投稿遅延** | 配信開始後、いつ投稿するか (即座 / 5分後 / 30分後) | immediate |
| **⭐ プレミア配信** | プレミア配信（ライブ試聴会）を投稿対象に含める | true |

---

## 技術仕様

### Live モジュールの構造

```
v3/plugins/youtube/
├── youtube_api_plugin.py      # 親プラグイン
└── live_module.py             # Live 機能をカプセル化（単独で使用可能）
    ├── LiveModule クラス
    │   ├── poll_lives()       # ポーリング実行（イベント検知・投稿）
    │   ├── register_from_classified()  # 分類結果をDB登録
    │   └── ...
    └── get_live_module()      # インスタンス取得関数
```

### ポーリング処理（poll_lives()）

Live モジュールは以下の処理を自動実行：

1. **DB から Live 関連動画を取得**
   - content_type が "schedule", "live", "completed", "archive"

2. **各動画の現在の状態を分類**
   - YouTubeVideoClassifier でAPI分類

3. **状態遷移を検知**
   - Schedule → Live: 配信開始イベント
   - Live → Completed: 配信終了イベント
   - Completed → Archive: アーカイブ公開イベント

4. **DB 更新と自動投稿**
   - 状態遷移に応じた template を適用
   - AUTOPOST モード時は自動投稿
   - SELFPOST モード時は投稿対象に追加

### 設定ファイルとの連動

環境変数（`settings.env`）から以下の値を読み込み：

```env
# YouTube API キー（必須）
YOUTUBE_API_KEY=AIzaSyDXQ9sv3...

# Live 投稿フラグ（SELFPOST モード個別制御）
YOUTUBE_LIVE_AUTO_POST_SCHEDULE=true
YOUTUBE_LIVE_AUTO_POST_LIVE=true
YOUTUBE_LIVE_AUTO_POST_ARCHIVE=true

# 投稿遅延（配信開始後いつ投稿するか）
YOUTUBE_LIVE_POST_DELAY=immediate  # immediate / delay_5min / delay_30min

# Premiere フラグ
AUTOPOST_INCLUDE_PREMIERE=true
```

---

## 使用例

### 例 1: Live ポーリングを実行

1. GUI の「🎬 Live判定」ボタンをクリック
2. "登録済みの Live 動画をポーリング中..." メッセージ表示
3. ポーリング完了 → "✅ YouTube Live ポーリング完了" メッセージ表示
4. DB が自動更新される

### 例 2: Live 設定を変更

1. GUI の「🎬 Live設定」ボタンをクリック
2. 設定パネルが表示
3. 各チェックボックス・ラジオボタンで設定変更
4. 「💾 保存して閉じる」をクリック
5. settings.env に反映、次回起動時に有効化

---

## トラブルシューティング

### Q: 「YouTube API プラグインが導入されていません」と表示される

**A**: 以下を確認してください

1. `YOUTUBE_API_KEY` が `settings.env` に設定されているか
   ```env
   YOUTUBE_API_KEY=AIzaSyDXQ9sv3...
   ```

2. YouTube API プラグインが正しく読み込まれているか
   - GUI の「プラグイン情報」で確認
   - YouTubeAPI プラグイン が ✅有効 で表示される

### Q: ポーリング実行後、何も変わらない

**A**: 以下を確認してください

1. DB に Live 動画が登録されているか
   - live_status が "upcoming", "live", "completed" の動画を確認

2. YouTube API のクォータに余裕があるか
   - 1日のクォータ: 10,000 ユニット
   - ポーリング: 動画1件あたり 1～5 ユニット

3. ログファイルで詳細を確認
   - `v3/logs/app.log` でエラーメッセージを確認

### Q: 設定を保存したのに反映されない

**A**: アプリケーション再起動が必要です

- 設定ファイル（settings.env）は起動時に読み込まれます
- 変更を反映するには、アプリケーション全体を再起動してください

---

## 関連ドキュメント

- [Live モジュール仕様](plugins/youtube/live_module.py)
- [YouTube API プラグイン](plugins/youtube/youtube_api_plugin.py)
- [TEMPLATE_SYSTEM.md](docs/Technical/TEMPLATE_SYSTEM.md) - Live テンプレート設定

---

## 実装チェックリスト

- ✅ Live判定ボタンが YouTubeAPI プラグインを参照
- ✅ Live設定ボタンが YouTubeAPI プラグインを確認
- ✅ LiveModule インポートが正しく実装
- ✅ poll_lives() 呼び出しでイベント処理
- ✅ 設定保存時のログメッセージを API プラグイン対応に更新
- ✅ エラーメッセージを新しい構造に合わせて更新
- ✅ settings.env に YOUTUBE_API_KEY が設定されている

---

**最終更新**: 2026-01-03
