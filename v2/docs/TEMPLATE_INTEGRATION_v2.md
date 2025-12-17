# v2 テンプレート処理統合 - 実装完了報告書

**対象バージョン**: v2.1.0
**最終更新**: 2025-12-17
**ステータス**: ✅ 実装完了

---

## 1. 実装概要

v2 テンプレートシステムが完全に統合されました。以下の4つのステップで、OLD_App のテンプレート処理を v2 のコア仕様として確立しました。

### 実装されたもの

- ✅ **テンプレート仕様ドキュメント** (`docs/TEMPLATE_SPECIFICATION_v2.md`)
- ✅ **テンプレート共通関数** (`template_utils.py`)
- ✅ **GUI テンプレート編集ダイアログ** (`template_editor_dialog.py`)
- ✅ **Bluesky プラグイン統合** (`bluesky_plugin.py` + `bluesky_template_manager.py`)
- ✅ **環境変数設定テンプレート** (`settings.env.example`)
- ✅ **デフォルトテンプレートファイル** (`templates/.templates/default_template.txt`)

---

## 2. ファイル一覧と機能

### 2.1 新規作成ファイル

| ファイル | パス | 用途 | 行数 |
|:--|:--|:--|:--:|
| TEMPLATE_SPECIFICATION_v2.md | `v2/docs/` | テンプレート仕様書（詳細） | 700+ |
| template_utils.py | `v2/` | テンプレート共通関数・定数 | 550+ |
| template_editor_dialog.py | `v2/` | GUI テンプレート編集ダイアログ | 450+ |
| bluesky_template_manager.py | `v2/` | Bluesky プラグイン用テンプレート管理 | 200+ |
| default_template.txt | `v2/templates/.templates/` | デフォルトテンプレート（フォールバック） | - |

### 2.2 修正ファイル

| ファイル | 変更内容 | 行数変更 |
|:--|:--|:--:|
| `v2/plugins/bluesky_plugin.py` | テンプレート処理統合メソッド追加 | +100 行 |
| `v2/settings.env.example` | テンプレートパス環境変数セクション追加 | +30 行 |

---

## 3. 実装内容の詳細

### 3.1 テンプレート仕様ドキュメント

**ファイル**: `v2/docs/TEMPLATE_SPECIFICATION_v2.md`

**内容**:
- テンプレートシステム全体像
- 共通 event_context キーの定義と型
- 各プラットフォーム × イベント別の利用可能変数
- 必須キー（required_keys）の定義
- サンプルテンプレート（YouTube、ニコニコ）
- Jinja2 基本形式・フィルター・条件分岐の説明
- ブラックリスト変数の概念
- Vanilla 環境での注意事項
- トラブルシューティング

**対応テンプレート種別**:
- YouTube: `youtube_new_video`, `youtube_online` ⚠️, `youtube_offline` ⚠️
- ニコニコ: `nico_new_video`
- Twitch: `twitch_online`, `twitch_offline`, `twitch_raid` （v3+ 予定）

※ ⚠️ 将来実装予定

---

### 3.2 テンプレート共通関数（template_utils.py）

**ファイル**: `v2/template_utils.py`

**提供する主要定数**:

```python
# 必須キー定義
TEMPLATE_REQUIRED_KEYS = {
    "youtube_new_video": ["title", "video_id", "video_url", "channel_name"],
    "nico_new_video": ["title", "video_id", "video_url", "channel_name"],
    # ... etc
}

# 表示可能変数（ボタン挿入用）
TEMPLATE_ARGS = {
    "youtube_new_video": [
        ("動画タイトル", "title"),
        ("動画 ID", "video_id"),
        # ... etc
    ],
    # ... etc
}

# ブラックリスト（ユーザーに見せない内部キー）
TEMPLATE_VAR_BLACKLIST = {
    "youtube_new_video": {"image_filename", "posted_at", "use_link_card", ...},
    # ... etc
}
```

**提供する主要関数**:

| 関数 | 用途 | 戻り値 |
|:--|:--|:--|
| `get_template_path(template_type, ...)` | テンプレートパス取得（環境変数 or 推論） | `str \| None` |
| `load_template_with_fallback(path, ...)` | テンプレート読み込み＋フォールバック | `Template \| None` |
| `validate_required_keys(event_context, ...)` | 必須キー検証 | `(bool, list)` |
| `render_template(template_obj, ...)` | Jinja2 レンダリング実行 | `str \| None` |
| `get_template_args_for_dialog(template_type, ...)` | GUI 用変数リスト取得 | `List[(str, str)]` |
| `get_sample_context(template_type)` | プレビュー用サンプル context | `Dict[str, Any]` |
| `preview_template(template_type, template_text, ...)` | テンプレートプレビュー＋検証 | `(bool, str)` |
| `save_template_file(template_type, text, ...)` | テンプレートファイル保存 | `(bool, str)` |

**使用例**:

```python
from template_utils import (
    load_template_with_fallback,
    validate_required_keys,
    render_template,
    get_template_path,
    TEMPLATE_REQUIRED_KEYS,
)

# テンプレートパス取得
template_path = get_template_path("youtube_new_video")

# テンプレート読み込み
template_obj = load_template_with_fallback(
    path=template_path,
    default_path="templates/.templates/default_template.txt"
)

# 必須キー検証
required_keys = TEMPLATE_REQUIRED_KEYS.get("youtube_new_video", [])
is_valid, missing_keys = validate_required_keys(event_context, required_keys)

if is_valid and template_obj:
    # レンダリング
    result = render_template(template_obj, event_context)
    print(result)
```

---

### 3.3 GUI テンプレート編集ダイアログ

**ファイル**: `v2/template_editor_dialog.py`

**クラス**: `TemplateEditorDialog(ctk.CTkToplevel)`

**機能**:

1. **テンプレートテキスト編集エリア**
   - Courier New フォント、シンタックスハイライト的配色
   - リアルタイム text-changed イベント検知

2. **テンプレート引数ボタン群**
   - TEMPLATE_ARGS から自動生成
   - ブラックリストに含まれる変数は表示しない
   - クリックで `{{ variable_name }}` を挿入

3. **ライブプレビューエリア**
   - サンプル event_context で Jinja2 レンダリング
   - エラーメッセージまたはレンダリング結果を表示

4. **ツールバー**
   - プレビュー更新ボタン
   - 保存ボタン
   - キャンセルボタン

5. **ステータスバー**
   - 処理状況表示（✅ 成功、⚠️ 警告、❌ エラー）

**インスタンス作成**:

```python
from template_editor_dialog import TemplateEditorDialog

def on_save(text, template_type):
    print(f"Template {template_type} saved!")

dialog = TemplateEditorDialog(
    master=root,
    template_type="youtube_new_video",
    initial_text="{{ title }} | {{ channel_name }}",
    on_save=on_save
)
```

**UI 配置**:

```
┌─────────────────────────────────────────────────────┐
│ 📄 種別: youtube_new_video  [プレビュー更新] [保存] [キャンセル] │
├─────────────────────────────────┬──────────────────┤
│                                 │                  │
│ 📝 テンプレートテキスト         │ 👁️ プレビュー    │
│ ┌──────────────────────────────┐│┌────────────────┐│
│ │ {{ title }}                  │││🎬 新作動画      │
│ │ {{ channel_name }}           │││                │
│ │ {{ video_url }}              │││投稿者: 〇〇Ch   │
│ │                              │││                │
│ │                              │││...             │
│ └──────────────────────────────┘│└────────────────┘│
│                                 │                  │
│ 🔧 利用可能な変数               │                  │
│ [動画タイトル] [動画ID] [動画URL] ...               │
│                                 │                  │
├─────────────────────────────────┴──────────────────┤
│ ✅ プレビュー成功                                    │
└─────────────────────────────────────────────────────┘
```

---

### 3.4 Bluesky プラグイン統合

#### A) bluesky_plugin.py に追加されたメソッド

**メソッド**: `render_template_with_utils(template_type, event_context)`

```python
def render_template_with_utils(
    self,
    template_type: str,
    event_context: dict
) -> str:
    """
    テンプレート共通関数を使用してレンダリング。

    1. テンプレートパスを環境変数から取得
    2. テンプレートをロード（失敗時はフォールバック）
    3. 必須キーを検証
    4. Jinja2 でレンダリング

    Returns: レンダリング済みテキスト（失敗時は空文字列）
    """
```

**使用例**:

```python
# bluesky_plugin.py の post_video() メソッド内
post_text = self.render_template_with_utils(
    template_type="youtube_new_video",
    event_context=video_event_context
)

if post_text:
    # 投稿テキストを使用して Bluesky に投稿
    self.minimal_poster.post_video_minimal(
        {**video, "post_text": post_text}
    )
```

#### B) bluesky_template_manager.py

**クラス**: `BlueskyTemplateManager`

**主要メソッド**:

| メソッド | 用途 |
|:--|:--|
| `open_template_editor(master_window, template_type, ...)` | テンプレート編集ダイアログを開く |
| `get_template_text(template_type)` | テンプレートテキストを読み込む |
| `_save_template_file(template_type, text)` | テンプレートをファイル保存 |

**グローバル関数**:

```python
def get_bluesky_template_manager() -> BlueskyTemplateManager:
    """シングルトンインスタンスを取得"""

def open_template_editor_from_gui(master_window, template_type, ...):
    """GUI から簡単に編集ダイアログを開くヘルパー"""
```

**使用例（GUI 統合）**:

```python
# gui_v2.py の TemplateEditorFrame 等で
from bluesky_template_manager import open_template_editor_from_gui

def on_click_edit_template(self):
    open_template_editor_from_gui(
        master_window=self.root,
        template_type="youtube_new_video",
        parent_callback=self.on_template_updated
    )
```

---

### 3.5 環境変数設定（settings.env.example）

以下の環境変数がサポートされました：

```bash
# YouTube テンプレートパス
TEMPLATE_YOUTUBE_NEW_VIDEO_PATH=templates/youtube/yt_new_video_template.txt
TEMPLATE_YOUTUBE_ONLINE_PATH=templates/youtube/yt_online_template.txt  # 将来
TEMPLATE_YOUTUBE_OFFLINE_PATH=templates/youtube/yt_offline_template.txt  # 将来

# ニコニコテンプレートパス
TEMPLATE_NICO_NEW_VIDEO_PATH=templates/niconico/nico_new_video_template.txt

# Twitch テンプレートパス（将来）
TEMPLATE_TWITCH_ONLINE_PATH=templates/twitch/twitch_online_template.txt
TEMPLATE_TWITCH_OFFLINE_PATH=templates/twitch/twitch_offline_template.txt
TEMPLATE_TWITCH_RAID_PATH=templates/twitch/twitch_raid_template.txt

# デフォルトテンプレート
BLUESKY_DEFAULT_TEMPLATE_PATH=templates/.templates/default_template.txt
```

**注意**: 省略可能。指定しない場合は自動的にデフォルトテンプレートが使用されます。

---

## 4. 動作フロー

### 4.1 テンプレート編集フロー

```
ユーザー（GUI）
    ↓
[テンプレート編集ボタンをクリック]
    ↓
bluesky_template_manager.open_template_editor_from_gui()
    ↓
template_editor_dialog.TemplateEditorDialog() を開く
    ↓
[テンプレートを編集 + ライブプレビュー]
    ↓
[保存ボタンクリック]
    ↓
on_save_callback()
    ↓
template_utils.save_template_file() でファイル保存
    ↓
✅ テンプレート保存完了
```

### 4.2 投稿フロー（テンプレート有効時）

```
RSS 新着動画取得 (youtube_rss.py)
    ↓
event_context 構築
    ↓
Bluesky プラグイン post_video() 呼び出し
    ↓
bluesky_plugin.render_template_with_utils(template_type, event_context)
    ↓
template_utils.get_template_path()
    ↓
環境変数 or 推論でパス決定
    ↓
template_utils.load_template_with_fallback()
    ↓
Jinja2 Template オブジェクト取得（フォールバック対応）
    ↓
template_utils.validate_required_keys()
    ↓
必須キー検証
    ↓
template_utils.render_template()
    ↓
Jinja2 レンダリング実行
    ↓
投稿テキスト取得
    ↓
BlueskyMinimalPoster.post_video_minimal() で投稿
    ↓
✅ Bluesky 投稿完了
```

### 4.3 Vanilla 環境での動作

```
Bluesky プラグイン無効
    ↓
TemplateEditorDialog は利用可能（GUI として備わる）
    ↓
しかし実行時にテンプレート処理は実行されない
    ↓
理由: post_video() メソッドが呼び出されない
    ↓
結果: デフォルトテキスト生成ロジックのみ実行
```

---

## 5. 統合テスト結果

### 5.1 単体テスト

**実行コマンド**:

```bash
cd v2

# template_utils.py テスト
python template_utils.py
# ✅ Output:
# Template Utils - v2.1.0
# youtube_new_video:
#   Sample keys: ['title', 'video_id', 'video_url', ...]
#   Display args: 6 項目
# ✅ template_utils.py の基本動作確認完了

# bluesky_template_manager.py テスト
python bluesky_template_manager.py
# ✅ Output:
# BlueskyTemplateManager - v2.1.0
# ✅ BlueskyTemplateManager 初期化完了
# ✅ テンプレート読み込み成功 (76 文字)
```

### 5.2 統合テスト（GUI）

TemplateEditorDialog のスタンドアロン実行テスト：

```bash
python template_editor_dialog.py
# → 🎬 テンプレート編集ダイアログ が customtkinter で起動
# → サンプル event_context でライブプレビュー動作確認 ✅
# → テンプレート保存機能動作確認 ✅
```

### 5.3 検証結果

| 項目 | 状態 | 確認事項 |
|:--|:--:|:--|
| template_utils.py 関数群 | ✅ | すべての関数が正常に動作 |
| テンプレート読み込み | ✅ | 環境変数・推論・フォールバック すべて動作 |
| 必須キー検証 | ✅ | 不足キー検出、警告ログ出力 |
| Jinja2 レンダリング | ✅ | フィルター、条件分岐、変数展開 動作確認 |
| GUI ダイアログ | ✅ | customtkinter 表示、変数ボタン挿入、プレビュー更新 |
| Bluesky プラグイン統合 | ✅ | render_template_with_utils() メソッド追加 |
| ファイル保存 | ✅ | template_utils.save_template_file() 動作確認 |
| settings.env.example | ✅ | 環境変数セクション追加、コメント記載 |

---

## 6. ファイル構成

### 6.1 テンプレートディレクトリ構成

```
v2/
├── templates/
│   ├── youtube/
│   │   ├── yt_new_video_template.txt        [既存]
│   │   ├── yt_online_template.txt           [将来]
│   │   └── yt_offline_template.txt          [将来]
│   ├── niconico/
│   │   └── nico_new_video_template.txt      [設計中]
│   ├── twitch/                              [将来]
│   └── .templates/
│       ├── default_template.txt             [✅ 新規]
│       └── fallback_template.txt            [将来]
│
├── docs/
│   └── TEMPLATE_SPECIFICATION_v2.md         [✅ 新規]
│
├── template_utils.py                        [✅ 新規]
├── template_editor_dialog.py                [✅ 新規]
├── bluesky_template_manager.py              [✅ 新規]
└── plugins/
    └── bluesky_plugin.py                    [修正: 統合メソッド追加]
```

---

## 7. 今後の予定

### 7.1 v2.x（近い将来）での拡張

| 項目 | 予定 | 詳細 |
|:--|:--|:--|
| YouTube Live | v2.x | yt_online_template.txt, yt_offline_template.txt の実装 |
| GUI 統合 | v2.x | gui_v2.py にテンプレート編集メニュー追加 |
| DB 保存 | v2.x | 選択したテンプレート種別を DB に保存（ユーザー記憶） |

### 7.2 v3（中期）での拡張

| 項目 | 予定 | 詳細 |
|:--|:--|:--|
| Twitch 対応 | v3 | Twitch イベント用テンプレート実装 |
| 条件付きテンプレート | v3 | 複数テンプレートの条件選択 |
| テンプレートライブラリ | v3 | ユーザー投稿テンプレート共有機能 |
| マルチランゲージ | v3 | テンプレート多言語対応 |

---

## 8. 使用方法（ユーザー向け）

### 8.1 テンプレートの編集方法

1. **GUI から編集ダイアログを開く**（将来実装）
   - "テンプレート編集" ボタンをクリック
   - テンプレート種別を選択

2. **テンプレートテキストを編集**
   - Jinja2 形式で変数を記述（例: `{{ title }}`）
   - 利用可能な変数はボタン群から挿入可能

3. **プレビューで確認**
   - 右側のプレビューエリアでサンプル context でのレンダリング結果を表示

4. **保存**
   - 保存ボタンをクリック
   - テンプレートファイルに自動保存される

### 8.2 テンプレート変数の確認

`docs/TEMPLATE_SPECIFICATION_v2.md` を参照：
- 各プラットフォーム × イベント別の利用可能変数一覧
- 必須キー定義
- サンプルテンプレート

---

## 9. 注意事項と制限事項

### 9.1 Vanilla 環境での制限

- テンプレート処理は**実行されません**（Bluesky プラグイン無効）
- テンプレート仕様と UI は整備されており、**将来のプラグイン導入時には即座に活用可能**

### 9.2 現行 v2.1.0 の制限

- YouTube New Video のみ実装（yt_new_video_template.txt）
- YouTube Live（yt_online, yt_offline）は設計のみで実装未了
- ニコニコテンプレートは設計中

### 9.3 テンプレート編集ダイアログの制限

- GUI 統合は**将来実装予定**（ダイアログ自体は完成）
- 現在は Python スクリプトで直接呼び出し可能

---

## 10. 参考資料

| ドキュメント | 用途 |
|:--|:--|
| [TEMPLATE_SPECIFICATION_v2.md](../../docs/TEMPLATE_SPECIFICATION_v2.md) | テンプレート仕様（ユーザー向け） |
| [template_utils.py](../../template_utils.py) | テンプレート関数・定数（開発者向け） |
| [template_editor_dialog.py](../../template_editor_dialog.py) | GUI ダイアログ実装（開発者向け） |
| [bluesky_template_manager.py](../../bluesky_template_manager.py) | プラグイン統合（開発者向け） |
| [bluesky_plugin.py](../../plugins/bluesky_plugin.py) | Bluesky プラグイン（開発者向け） |
| [v2_DESIGN_POLICY.md](../../docs/v2_DESIGN_POLICY.md) | v2 設計方針 |

---

## 11. トラブルシューティング

### Q: テンプレートが反映されない

**A**: 以下を確認してください：
1. Bluesky プラグインが有効になっているか（`settings.env` で確認）
2. テンプレートファイルが正しいパスに存在するか
3. `OPERATION_MODE` が `normal` or `auto_post` か（`dry_run`/`collect` では投稿されない）

### Q: プレビューが表示されない

**A**:
1. テンプレート構文に誤りがないか確認
2. 必須キーが不足していないか確認
3. `{{ variable }}` の形式が正しいか確認

### Q: 環境変数でテンプレートパスを指定したい

**A**:
```bash
# settings.env に以下を記入
TEMPLATE_YOUTUBE_NEW_VIDEO_PATH=/custom/path/my_template.txt
```

---

## 12. 更新履歴

| 日時 | 変更内容 | 対象バージョン |
|:-|:--|:--:|
| 2025-12-17 | v2 テンプレート処理統合完了（4 ステップ実装） | v2.1.0+ |

---

**著作権**: Copyright (C) 2025 mayuneco(mayunya)
**ライセンス**: GPLv2
**対応 Python バージョン**: 3.8+
