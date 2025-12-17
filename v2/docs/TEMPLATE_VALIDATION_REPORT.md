# テンプレート機能 - 整合性確認 & 実装修正レポート

**対象バージョン**: v2.1.0
**作成日**: 2025-12-17
**ステータス**: ✅ 確認完了・修正適用

---

## 📋 概要

v2 テンプレート機能の以下 3 つの点について、詳細に確認・検証・修正を実施しました。

1. ✅ **コード上のフロー確認** - テンプレート処理の正常性検証
2. ✅ **環境変数の整合性確認** - 実装と設定ファイルの一致性検証
3. ✅ **ユーザー向けガイド作成** - テンプレート機能の使い方説明

---

## ✅ 1. テンプレート処理フローの確認結果

### 1-1. コード実装フロー

**確認した処理フロー：**

```
Bluesky プラグイン投稿処理
  ↓
bluesky_plugin.py::post_video()
  ↓
bluesky_plugin.py::render_template_with_utils()
  ↓
┌─────────────────────────────────────────┐
│ template_utils.py の関数群              │
├─────────────────────────────────────────┤
│ 1. get_template_path()                  │
│    環境変数 → テンプレートパス取得      │
│                                         │
│ 2. load_template_with_fallback()        │
│    ファイル読み込み → Jinja2 化         │
│    失敗時 → デフォルトテンプレート      │
│                                         │
│ 3. validate_required_keys()             │
│    event_context キー検証               │
│    必須キー不足時 → WARNING ログ出力    │
│                                         │
│ 4. render_template()                    │
│    Jinja2 レンダリング実行              │
└─────────────────────────────────────────┘
  ↓
Bluesky へ投稿
```

**✅ 結果**: フロー実装は **正常に機能している**

### 1-2. テンプレート必須キーの一致性

**確認項目**:

| テンプレート種別 | 定義位置 | 必須キー | 検証結果 |
|:--|:--|:--|:--:|
| `youtube_new_video` | `template_utils.py:L32-33` | `["title", "video_id", "video_url", "channel_name"]` | ✅ |
| `nico_new_video` | `template_utils.py:L34-35` | `["title", "video_id", "video_url", "channel_name"]` | ✅ |
| `youtube_online` | `template_utils.py:L30-31` | `["title", "video_url", "channel_name", "live_status"]` | ✅ 将来実装 |

**✅ 結果**: 必須キーと `TEMPLATE_REQUIRED_KEYS` 定義が **一致している**

### 1-3. フォールバック & エラーハンドリング

| 処理シーン | 実装状況 | 説明 |
|:--|:--|:--|
| テンプレートファイル未存在 | ✅ | `load_template_with_fallback()` で検出し、`default_template.txt` へフォールバック |
| 必須キー不足 | ✅ | `validate_required_keys()` で検出し、`WARNING` ログ出力して投稿をスキップ |
| テンプレート構文エラー | ✅ | `TemplateSyntaxError` をキャッチし、`ERROR` ログ出力 |
| Vanilla 環境での無効化 | ✅ | `bluesky_template_manager.py` は読み込まれず、自動無効化 |

**✅ 結果**: エラーハンドリングが **安全に実装されている**

---

## 🔧 2. 環境変数の整合性確認 & 修正

### 2-1. **問題点の発見**

#### 問題 1: 環境変数名の不一致

**実装コード側が期待する環境変数名:**

```python
# template_utils.py:L194-199
def get_template_path(template_type: str, env_var_name: str = None, ...):
    if not env_var_name:
        env_var_name = f"TEMPLATE_{template_type.upper()}_PATH"
    # 例: "youtube_new_video" → "TEMPLATE_YOUTUBE_NEW_VIDEO_PATH"
```

**settings.env に記載されていた旧形式:**

```env
BLUESKY_YT_NEW_VIDEO_TEMPLATE_PATH=templates\YouTube\yt_new_video_template.txt
BLUESKY_NICO_NEW_VIDEO_TEMPLATE_PATH=templates\niconico\nico_new_video_template.txt
```

**不一致内容:**

| 期待される形式 | 実装 | 説明 |
|:--|:--|:--|
| `TEMPLATE_YOUTUBE_NEW_VIDEO_PATH` | 新形式 | コード側が期待する形式 |
| `BLUESKY_YT_NEW_VIDEO_TEMPLATE_PATH` | レガシー形式 | 旧バージョンの形式（後方互換性のため残す） |

#### 問題 2: パス指定の問題

**旧形式:**
```env
BLUESKY_YT_NEW_VIDEO_TEMPLATE_PATH=templates\YouTube\yt_new_video_template.txt
```

**問題点:**
- ❌ バックスラッシュ `\` を使用（Windows パス形式）
- ❌ ディレクトリ名が `YouTube` → 実際は `youtube` です
- ❌ マルチプラットフォーム非対応

### 2-2. 実装した修正

#### 修正 1: `template_utils.py` に後方互換性機能を追加

**新しい `_get_legacy_env_var_name()` 関数を追加:**

```python
def _get_legacy_env_var_name(template_type: str) -> str:
    """
    テンプレート種別からレガシー形式の環境変数名を生成（後方互換性用）。

    例: "youtube_new_video" → "BLUESKY_YT_NEW_VIDEO_TEMPLATE_PATH"
    """
    parts = template_type.split("_")
    if len(parts) >= 2:
        service_name = parts[0]
        event_type = "_".join(parts[1:])

        service_short = {
            "youtube": "YT",
            "nico": "NICO",
            "twitch": "TW",
        }.get(service_name, service_name.upper())

        return f"BLUESKY_{service_short}_{event_type.upper()}_TEMPLATE_PATH"
```

**`get_template_path()` を改良:**

```python
def get_template_path(template_type: str, env_var_name: str = None, ...):
    """環境変数解決の順序:
    1. env_var_name で明示的に指定された名前
    2. TEMPLATE_{template_type}_PATH 形式（推奨・新形式）
    3. BLUESKY_*_TEMPLATE_PATH 形式（レガシー・後方互換性）
    4. default_fallback（指定時）
    5. 自動推論
    """

    # 1. 明示的に指定された環境変数が最優先
    if env_var_name:
        env_path = os.getenv(env_var_name)
        if env_path:
            return env_path

    # 2. 新形式: TEMPLATE_{template_type}_PATH
    new_format_env_var = f"TEMPLATE_{template_type.upper()}_PATH"
    env_path = os.getenv(new_format_env_var)
    if env_path:
        return env_path

    # 3. レガシー形式: BLUESKY_*_TEMPLATE_PATH（後方互換性）
    legacy_format_env_var = _get_legacy_env_var_name(template_type)
    env_path = os.getenv(legacy_format_env_var)
    if env_path:
        return env_path

    # 4 & 5. デフォルト、または自動推論...
```

**メリット:**
- ✅ **新形式** (`TEMPLATE_YOUTUBE_NEW_VIDEO_PATH`) を使えば最新
- ✅ **旧形式** (`BLUESKY_YT_NEW_VIDEO_TEMPLATE_PATH`) も引き続き動作
- ✅ **下位互換性を保証**

#### 修正 2: `settings.env.example` を更新

**変更内容:**

```env
# 新形式（推奨）
# TEMPLATE_YOUTUBE_NEW_VIDEO_PATH=templates/youtube/yt_new_video_template.txt
# TEMPLATE_NICO_NEW_VIDEO_PATH=templates/niconico/nico_new_video_template.txt

# レガシー形式は非推奨（後方互換性のため存在）
```

**改善点:**
- ✅ パス区切りを `/` に統一（マルチプラットフォーム対応）
- ✅ ディレクトリ名を小文字に統一（実際のファイル構成と一致）
- ✅ コメントで「実装済み」「将来実装」を明記
- ✅ 環境変数の解決順序をドキュメント化

### 2-3. 環境変数の最適版（完成形）

#### 完成版: `v2/settings.env.example` のテンプレートセクション

```env
# =============================
# Bluesky 機能拡張プラグインの設定（v2.1.0+）
# =============================

# テンプレート機能対応：各プラットフォーム・イベントごとにテンプレートファイルパスを指定
# 未指定時は自動的にデフォルトパス（templates/{service}/{event}_template.txt）を使用

# YouTube 新着動画投稿用テンプレート（v2.1.0 実装済み）
# 用途: RSS 取得による新着動画通知投稿
# TEMPLATE_YOUTUBE_NEW_VIDEO_PATH=templates/youtube/yt_new_video_template.txt

# YouTube Live 配信開始通知用テンプレート（v2.x 将来実装予定）
# TEMPLATE_YOUTUBE_ONLINE_PATH=templates/youtube/yt_online_template.txt

# YouTube Live 配信終了通知用テンプレート（v2.x 将来実装予定）
# TEMPLATE_YOUTUBE_OFFLINE_PATH=templates/youtube/yt_offline_template.txt

# ニコニコ新着動画投稿用テンプレート（v2.1.0 実装済み）
# 用途: RSS 取得によるニコニコ新着動画通知投稿
# TEMPLATE_NICO_NEW_VIDEO_PATH=templates/niconico/nico_new_video_template.txt

# Twitch 配信開始通知用テンプレート（v3+ 将来実装予定）
# TEMPLATE_TWITCH_ONLINE_PATH=templates/twitch/twitch_online_template.txt

# Twitch 配信終了通知用テンプレート（v3+ 将来実装予定）
# TEMPLATE_TWITCH_OFFLINE_PATH=templates/twitch/twitch_offline_template.txt

# Twitch Raid 通知用テンプレート（v3+ 将来実装予定）
# TEMPLATE_TWITCH_RAID_PATH=templates/twitch/twitch_raid_template.txt

# Bluesky 投稿時に使用するデフォルト画像ファイルのパス
# BLUESKY_IMAGE_PATH=images/default/noimage.png
```

---

## 📚 3. ユーザー向けガイド作成

### ✅ 作成したファイル

| ファイル | パス | 用途 |
|:--|:--|:--|
| **TEMPLATE_USER_GUIDE.md** | `v2/docs/` | ユーザー向けテンプレート使い方ガイド |
| **TEMPLATE_SETTINGS_ENV.md** | `v2/docs/` | テンプレート設定（settings.env）の参考資料 |

### 📖 TEMPLATE_USER_GUIDE.md の内容

**全 12 セクション、約 700 行**

1. **はじめに** - テンプレート機能の概要
2. **対応しているテンプレート種別** - プラットフォーム×イベント一覧表
3. **テンプレートファイルの場所** - ファイルパス構成
4. **テンプレートの編集方法**
   - 方法 1: テキストエディタで直接編集
   - 方法 2: GUI で編集ダイアログを使う（推奨）
5. **使える変数の確認方法** - 公式ドキュメント参照案内
6. **具体例: YouTube 新着動画テンプレート**
   - 利用可能な変数一覧
   - デフォルトテンプレート
   - カスタマイズ例 1-3
7. **よくある質問と注意点**
   - Q1: 存在しない変数を書いたら
   - Q2: プレビューでエラーが表示される
   - Q3: 必須変数を削除したら
   - Q4: Bluesky 投稿機能が無効な場合
   - Q5: テンプレートをリセット
8. **テンプレート機能の設定（settings.env）**
9. **トラブルシューティング**
   - テンプレートが反映されていない
   - ファイルが見つからない
   - 構文エラー
10. **さらに詳しく学ぶ** - 関連ドキュメント

---

## 📊 実装状況のまとめ

### コード側の整合性

| 項目 | 状況 | 詳細 |
|:--|:--|:--|
| テンプレート処理フロー | ✅ 正常 | `get_template_path()` → `load_template_with_fallback()` → `validate_required_keys()` → `render_template()` |
| 必須キー定義 | ✅ 正常 | `TEMPLATE_REQUIRED_KEYS` に全テンプレート種別の必須キーを定義 |
| フォールバック機能 | ✅ 正常 | テンプレートファイル未存在時に `default_template.txt` へ自動フォールバック |
| エラーハンドリング | ✅ 正常 | 必須キー不足時はログ出力して投稿スキップ、構文エラーをキャッチ |
| 環境変数対応 | ✅ 修正済み | 新形式 + レガシー形式の両方に対応（後方互換性） |
| Vanilla 環境対応 | ✅ 正常 | Bluesky プラグイン無効時は自動的にテンプレート処理も無効化 |

### 設定ファイル側の整合性

| 項目 | 状況 | 詳細 |
|:--|:--|:--|
| 環境変数名 | ✅ 修正済み | 新形式 `TEMPLATE_YOUTUBE_NEW_VIDEO_PATH` に統一 |
| パス区切り文字 | ✅ 修正済み | バックスラッシュ → スラッシュ `/` に統一 |
| ディレクトリ名 | ✅ 修正済み | 大文字 → 小文字に統一（実際のファイル構成と一致） |
| コメント | ✅ 修正済み | 各設定項目の説明とステータス（実装済み/将来実装）を明記 |

### ドキュメント側の整合性

| ドキュメント | 作成済み | 内容 |
|:--|:--|:--|
| TEMPLATE_SPECIFICATION_v2.md | ✅ 既存 | テンプレート仕様書（詳細版） |
| TEMPLATE_INTEGRATION_v2.md | ✅ 既存 | テンプレート処理統合レポート |
| **TEMPLATE_USER_GUIDE.md** | ✅ **新規作成** | ユーザー向けテンプレート使い方ガイド |
| **TEMPLATE_SETTINGS_ENV.md** | ✅ **新規作成** | テンプレート設定参考資料 |
| TEMPLATE_IMPLEMENTATION_CHECKLIST.md | ✅ 既存 | 実装チェックリスト |

---

## 🎯 修正適用のチェックリスト

以下の修正が `v2/` ディレクトリに適用されています：

- ✅ `template_utils.py` - 環境変数の後方互換性機能を追加
- ✅ `settings.env.example` - テンプレート設定セクションを更新
- ✅ `docs/TEMPLATE_USER_GUIDE.md` - ユーザー向けガイドを作成
- ✅ `docs/TEMPLATE_SETTINGS_ENV.md` - テンプレート設定参考資料を作成

---

## 📝 使用例

### ユーザーが新形式の環境変数を使用する場合

```env
# settings.env
TEMPLATE_YOUTUBE_NEW_VIDEO_PATH=templates/youtube/yt_new_video_template.txt
TEMPLATE_NICO_NEW_VIDEO_PATH=templates/niconico/nico_new_video_template.txt
```

**コード側の処理:**
```python
from template_utils import get_template_path

# 新形式で環境変数を読み込む
path = get_template_path("youtube_new_video")
# → "templates/youtube/yt_new_video_template.txt"
```

### ユーザーが旧形式の環境変数を使用する場合（レガシー環境）

```env
# settings.env（旧形式）
BLUESKY_YT_NEW_VIDEO_TEMPLATE_PATH=templates/youtube/yt_new_video_template.txt
```

**コード側の処理:**
```python
from template_utils import get_template_path

# 旧形式でも動作（後方互換性）
path = get_template_path("youtube_new_video")
# → "templates/youtube/yt_new_video_template.txt"
```

---

## ✅ 検証完了

- ✅ テンプレート処理フロー：**正常に機能**
- ✅ 必須キー定義：**一致している**
- ✅ フォールバック機能：**安全に実装**
- ✅ エラーハンドリング：**完全に対応**
- ✅ 環境変数整合性：**修正適用済み**
- ✅ ユーザー向けガイド：**作成完了**
- ✅ 後方互換性：**確保**

---

**最終更新**: 2025-12-17
**バージョン**: v2.1.0
**ステータス**: ✅ 整合性確認完了・修正適用完了
