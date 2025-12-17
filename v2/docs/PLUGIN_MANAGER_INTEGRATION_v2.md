# プラグインマネージャーの統合ガイド

## 現在の画面構成

### GUI レイアウト

```
┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│ StreamNotify on Bluesky - DB 管理                                                        │
├──────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                              │
│ [🔄 再読込] [☑️ 全選択] [☐ 全解除] | [💾 保存] [🗑️ 削除] | [🧪 投稿テスト] [📤 投稿設定] [ℹ️ 統計] [🔌 プラグイン] │
│                                                                                              │
├──────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                              │
│ ☐ │Video ID │公開日時      │配信元    │タイトル            │投稿予定/投稿日時│投稿実績│画像モード│
│ ──┼─────────┼──────────────┼──────────┼────────────────────┼──────────────┼──────┼────────│
│ ☑ │-Vnx9CUo│2025-12-15    │youtube   │[Twitch同時配信]... │2025-12-15    │✓    │import  │
│ ☑ │iB-ajHP│2025-10-29    │youtube   │[Twitch同時配信]... │未明         │✓    │import  │
│ ☐ │p4AJDhen│2025-10-29    │youtube   │[Twitch同時配信]... │未明         │✓    │import  │
│ ☐ │PpCNLENW│2025-10-28    │youtube   │[録：予定時刻]...   │未明         │✓    │import  │
│                                                                                              │
│  （スクロール可能）                                                                          │
│                                                                                              │
├──────────────────────────────────────────────────────────────────────────────────────────────┤
│  読み込み完了: 11 件の動画（選択: 0 件）                                                    │
└──────────────────────────────────────────────────────────────────────────────────────────────┘
```

**✨ v2.1.0 新機能:**
- **🧪 投稿テスト**: DRY RUN モードで投稿をシミュレート
- **📤 投稿設定**: 投稿設定ウィンドウで画像添付・リサイズ設定を調整

## 呼び出しフロー

### メインフロー

```
main_v2.py::main()
│
├─ config.py から設定読み込み
│
├─ logging_config.py でロギング初期化
│
├─ database.py からDB初期化
│
├─ plugin_manager.py でプラグイン管理システム初期化
│  └─ plugins/ ディレクトリから全プラグインを自動ロード
│
├─ youtube_rss.py からRSS取得
│
└─ GUI をマルチスレッドで起動
   │
   ├─ StreamNotifyGUI(root, db, plugin_manager)
   │  └─ setup_ui()
   │     └─ execute_post() → plugin_manager.post_video_with_all_enabled()
   │
   └─ メインループでポーリング継続
```

## プラグインマネージャーの統合ポイント

### 現在: PluginManager 統合構成（v2.1.0 実装）

```python
# main_v2.py 内の実装
from plugin_manager import PluginManager

plugin_manager = PluginManager(plugins_dir="plugins")
# プラグインディレクトリから自動ロード
plugin_manager.load_plugins_from_directory()

# GUI に渡す
gui = StreamNotifyGUI(root, db, plugin_manager)

# GUI 内で使用（複数プラグイン対応、DRY RUN 対応）
results = self.plugin_manager.post_video_with_all_enabled(video, dry_run=False)
# ★ DRY RUN: results = self.plugin_manager.post_video_with_all_enabled(video, dry_run=True)
```

## 統合実装状況（v2で実装済み）

### Step 1: plugins ディレクトリ構造 ✅

```
plugins/
  __init__.py
  bluesky_plugin.py          # Bluesky 投稿プラグイン
  youtube_api_plugin.py      # YouTube Data API 連携
  youtube_live_plugin.py     # YouTube ライブ判定
  niconico_plugin.py         # ニコニコ動画 RSS 監視
  logging_plugin.py          # ロギング統合管理
```

### Step 2: main_v2.py での PluginManager 統合 ✅

**実装内容:**

```python
from plugin_manager import PluginManager

# プラグインマネージャーの初期化
plugin_manager = PluginManager(plugins_dir="plugins")
plugin_manager.load_plugins_from_directory()
```

### Step 3: GUI での PluginManager 使用 ✅

**StreamNotifyGUI での実装:**

```python
def __init__(self, root, db, plugin_manager=None):
    self.root = root
    self.db = db
    self.plugin_manager = plugin_manager
    # ... その他の初期化

def execute_post(self):
    if not self.plugin_manager:
        messagebox.showerror("エラー", "プラグインが初期化されていません")
        return

    # 複数プラグイン対応: 有効なすべてのプラグインで投稿実行
    results = self.plugin_manager.post_video_with_all_enabled(video)
    # results: {"bluesky": True, "twitch": False, ...}
```

## 実装完了状況のまとめ

✅ **完全実装済み:**
- plugins ディレクトリでのプラグイン自動ロード
- 全プラグインの自動ロード・自動有効化
- main_v2.py での PluginManager 統合
- StreamNotifyGUI への PluginManager 統合
- 複数プラグイン対応の投稿機構
- 動画削除機能（DB完全削除）

## GUIコンポーネント詳細

### 左上ツールバー

| ボタン | 機能 | 呼び出し |
|--------|------|--------|
| 🔄 再読込 | DB 最新データを読み込み | `refresh_data()` |
| ☑️ 全選択 | すべての動画を選択 | `select_all()` |
| ☐ 全解除 | すべての選択を解除 | `deselect_all()` |
| 💾 保存 | 選択状態を DB に保存 | `save_selection()` |
| 🗑️ 削除 | 選択した動画を DB から削除 | `delete_selected()` |
| 🧪 投稿テスト | 投稿をテスト実行 | `dry_run_post()` |
| 📤 投稿設定 | 投稿設定ウィンドウを表示 | `execute_post()` |
| ℹ️ 統計 | 投稿数、投稿予定、未処理などの統計情報を表示 | `show_stats()` |
| 🔌 プラグイン | 導入プラグイン一覧と有効/無効状態を表示 | `show_plugins()` |

### 中央テーブル (Treeview)

| 列 | 説明 | 機能 |
|----|------|------|
| ☐ | チェック状態 | クリック: ON/OFF トグル |
| Video ID | 動画ID | 表示のみ |
| 公開日時 | 公開日時（YYYY-MM-DD形式） | 表示のみ |
| 配信元 | 動画の配信元（youtube、niconico など） | 表示のみ |
| タイトル | 動画タイトル（可変長） | 表示のみ |
| 投稿予定/投稿日時 | 未投稿時は投稿予定、投稿済み時は投稿日時 | ダブルクリック: 編集ダイアログ |
| 投稿実績 | 投稿済みフラグ（✓または–） | 表示のみ |
| 画像モード | 画像モード（import など） | 表示のみ |
| 画像ファイル | 画像ファイル名 | 表示のみ |

### ダイアログ

#### 投稿日時設定ダイアログ

📌 **機能:**
- **前回投稿日時表示**:
  - 投稿済み → `posted_at` カラムの値を表示
  - 投稿済みだが `posted_at` がない → 「前回投稿日時: 不明」と表示
  - 未投稿 → 「前回投稿日時: 投稿されていません」と表示
- 📅 日付選択（年/月/日）- Spinbox で直感的に設定
- 🕐 時間選択（時/分）- Spinbox で直感的に設定
- ⚡ クイック設定ボタン:
  - 5分後、15分後、30分後、1時間後
- ボタン:
  - ✅ 保存 - 予約日時を保存してDB反映
  - ❌ 選択解除 - この動画の選択を解除
  - ✕ キャンセル - ダイアログを閉じる

**実装特徴:**
- カレンダー自動調整機能（月の日数に応じて日付を自動修正）
- 予約日時設定後、画像設定ダイアログに進むか確認
- 時間を設定すると、自動的に選択状態がONになる

```
┌──────────────────────────────────┐
│ 投稿日時設定 - Vnx9CUowOI        │
├──────────────────────────────────┤
│ 動画: Vnx9CUowOI                 │
│ 予約投稿日時を設定します         │
│ 前回投稿日時: 2025-12-12 09:30   │
│                                  │
│ 📅 日付を選択                    │
│ [2025] 年 [12] 月 [12] 日       │
│                                  │
│ 🕐 時間を選択                    │
│ [17] 時 [09] 分                 │
│                                  │
│ ⚡ クイック設定                  │
│ [5分後] [15分後]                 │
│ [30分後] [1時間後]               │
│                                  │
│ [✅ 保存] [❌ 選択解除] [✕ キャンセル] │
└──────────────────────────────────┘
```

#### 統計情報ダイアログ

```
📊 統計情報
━━━━━━━━━━━━━━━━━
総動画数:     11
投稿済み:     10
投稿予定:     0
未処理:       1

📌 操作方法
━━━━━━━━━━━━━━━━━
1. 「☑️」をクリック → 投稿対象を選択
2. 「投稿予定/投稿日時」をダブルクリック → 投稿日時を設定
3. 「💾 選択を保存」 → DB に反映
4. 「🧪 投稿テスト」 → テスト実行
5. 「📤 投稿設定」 → 投稿設定

⚠️ 注意
━━━━━━━━━━━━━━━━━
投稿済みフラグに関わらず投稿できます。
重複投稿にご注意ください。
```

## データフロー

### 選択→保存→投稿

```
1. ユーザーがテーブルで ☑️ をクリック
   ↓
   StreamNotifyGUI.on_tree_click()
   self.selected_rows に追加

2. ユーザーが「💾 保存」ボタンをクリック
   ↓
   StreamNotifyGUI.save_selection()
   → db.update_selection()

3. ユーザーが「📤 投稿設定」をクリック
   ↓
   StreamNotifyGUI.execute_post()
   → plugin_manager.post_video_with_all_enabled(video)
   → 各プラグインの post_video() を実行
   → db.mark_as_posted() で DB 更新

```

### 選択→保存→削除

```
1. ユーザーがテーブルで ☑️ をクリックして選択
   ↓
   StreamNotifyGUI.on_tree_click()
   self.selected_rows に追加

2. ユーザーが「🗑️ 削除」ボタンをクリック
   ↓
   StreamNotifyGUI.delete_selected()
   → 確認ダイアログを表示
   → db.delete_videos_batch() で DB から削除
   → self.selected_rows から削除
   → テーブルを再読み込み

```

※ 削除操作は確認ダイアログで警告し、取り消せない旨を表示します。
  個別削除は右クリックメニューから「🗑️ 削除」で可能です。

### 投稿テスト（DRY RUN） → 投稿設定ウィンドウ フロー（v2.1.0）

```
1. ユーザーが「🧪 投稿テスト」または「📤 投稿設定」をクリック
   ↓
   StreamNotifyGUI._on_post_settings_clicked()
   → PostSettingsWindow を起動

2. PostSettingsWindow で設定を調整
   ├─ ☑ 画像を添付する (True/False)
   ├─ ☑ 小さい画像を拡大する (True/False)
   ├─ 画像プレビュー表示
   └─ 投稿方法を表示

3. ユーザーが「✅ 投稿」をクリック
   ↓
   PostSettingsWindow._execute_post(dry_run=False)
   → plugin_manager.post_video_with_all_enabled(video, dry_run=False)
   → 各プラグインの post_video() を実行
   → db.update_selection(selected=False) で DB 更新
   ↓
   「✅ 投稿完了」メッセージ表示
   ↓
   ウィンドウを閉じる

   または

   ユーザーが「🧪 投稿テスト」をクリック
   ↓
   PostSettingsWindow._execute_post(dry_run=True)
   → plugin_manager.post_video_with_all_enabled(video, dry_run=True)
   → 画像リサイズ・Facet構築は実行
   → Blob アップロード・API 呼び出しはスキップ
   → DB は更新されない
   ↓
   「🧪 投稿テスト完了」メッセージ表示
   ↓
   ウィンドウを閉じる

```

**関連ドキュメント:**
- [BLUESKY_PLUGIN_GUIDE.md#4-dry-run投稿テスト機能](./BLUESKY_PLUGIN_GUIDE.md#4-dry-run投稿テスト機能) - DRY RUN 機能の詳細
- [BLUESKY_PLUGIN_GUIDE.md#5-gui投稿設定ウィンドウ](./BLUESKY_PLUGIN_GUIDE.md#5-gui投稿設定ウィンドウ) - GUI 投稿設定ウィンドウの詳細

---

## 拡張可能性

PluginManager を使用することで:

- 🔌 **新しい通知先を追加**: `plugins/` に新しいプラグインを追加するだけ
- 📋 **複数プラグイン対応**: 同時に複数の通知先へ投稿可能
- 🎯 **動的有効化**: 実行時にプラグインを有効/無効化可能
- 🔄 **ライフサイクル管理**: on_enable/on_disable コールバック

## Assetディレクトリによるテンプレート・画像管理

- `Asset/` ディレクトリに全サービス・全プラグイン用テンプレート/画像を保管
- プラグイン導入時に必要なファイルを Asset から本番ディレクトリに自動コピー（実装完了: 2025-12）
- `asset_manager.py` で自動配置を実行、main_v2.py で呼び出し
- 既存ファイルは上書きされない（ユーザー編集を保護）
- 追加済みファイルはプラグイン削除後も残る（手動削除推奨）

## 参考資料

- `plugin_interface.py` - NotificationPlugin インターフェース
- `plugin_manager.py` - PluginManager 実装
- `docs/PLUGIN_ARCHITECTURE.md` - 詳細ドキュメント
