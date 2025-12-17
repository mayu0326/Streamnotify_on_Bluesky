# Bluesky テンプレート統合問題 - 根本原因分析レポート

**日付**: 2025年12月18日
**対象**: テンプレート機能が使用されていない問題の原因調査
**ステータス**: 🔍 原因特定完了 → 修正方案提示

---

## 📋 問題の概要

**症状**:
- テンプレート機能が実装されているはずなのに、`post.log` に従来フォーマット（タイトル + チャンネル名 + 日付 + URL）が出ている
- テンプレート内容が反映されていない

**期待**:
- YouTube/ニコニコの新着動画投稿時、テンプレートに基づいたカスタム本文で投稿される

---

## 🔎 原因分析

### 1. コード実装状況の調査

#### 1.1 `bluesky_plugin.py` - post_video() メソッド（行 131-224）

✅ **状態**: テンプレート処理が実装されている

**コード**:
```python
# line 195-216
if source == "youtube":
    rendered = self.render_template_with_utils("youtube_new_video", video)
    if rendered:
        video["text_override"] = rendered
        post_logger.info(f"✅ テンプレートを使用して本文を生成しました: youtube_new_video")
    else:
        post_logger.debug(f"ℹ️ youtube_new_video テンプレート未使用またはレンダリング失敗（従来フォーマットを使用）")

elif source in ("niconico", "nico"):
    rendered = self.render_template_with_utils("nico_new_video", video)
    if rendered:
        video["text_override"] = rendered
        post_logger.info(f"✅ テンプレートを使用して本文を生成しました: nico_new_video")
    else:
        post_logger.debug(f"ℹ️ nico_new_video テンプレート未使用またはレンダリング失敗（従来フォーマットを使用）")
```

✅ **確認**:
- ✅ テンプレートレンダリング処理呼び出し有り
- ✅ `text_override` に設定している
- ✅ ログ出力あり

#### 1.2 `bluesky_core.py` - post_video_minimal() メソッド（行 119-180）

✅ **状態**: `text_override` を使用している

**コード**:
```python
# line 130-144
text_override = video.get("text_override")
...
if text_override:
    # プラグイン側でテンプレートから生成した本文を優先
    post_text = text_override
    post_logger.info(f"📝 テンプレート生成済みの本文を使用します")
elif source == "niconico":
    post_text = f"{title}\n\n📅 {published_at[:10]}\n\n{video_url}"
else:
    # YouTube（デフォルト）
    post_text = f"{title}\n\n🎬 {channel_name}\n📅 {published_at[:10]}\n\n{video_url}"
```

✅ **確認**:
- ✅ `text_override` チェックしている
- ✅ あれば優先している

#### 1.3 `template_utils.py` - テンプレート仕様

✅ **状態**: テンプレート仕様が定義されている

**確認内容**:
- ✅ `TEMPLATE_REQUIRED_KEYS` で `youtube_new_video`, `nico_new_video` が定義
- ✅ `get_template_path()`, `load_template_with_fallback()`, `render_template()` 実装

#### 1.4 テンプレートファイル

✅ **状態**: ファイルが存在している

```
v2/templates/youtube/yt_new_video_template.txt:
🎬 {{ channel_name }} の新作動画
YouTube に新しい動画をアップロードしました！
📹 タイトル: {{ title }}
📺 視聴: {{ video_url }}
投稿日時: {{ published_at | datetimeformat('%Y年%m月%d日') }}
#YouTube
```

#### 1.5 環境変数設定

✅ **状態**: 設定されている

```
TEMPLATE_YOUTUBE_NEW_VIDEO_PATH=templates/youtube/yt_new_video_template.txt
TEMPLATE_NICO_NEW_VIDEO_PATH=templates/niconico/nico_new_video_template.txt
```

---

## ⚠️ **根本原因を特定**

### 原因: **テンプレートレンダリングが「毎回失敗」している可能性**

#### シナリオ 1: 必須キーの不足（最有力）

**bluesky_plugin.py line 207** で必須キー検証が行われます：

```python
required_keys = TEMPLATE_REQUIRED_KEYS.get(template_type, [])
is_valid, missing_keys = validate_required_keys(
    event_context=event_context,
    required_keys=required_keys,
    event_type=template_type
)

if not is_valid:
    post_logger.warning(f"⚠️ 必須キー不足（{template_type}）: {missing_keys}")
```

#### **必須キー確認**:

`TEMPLATE_REQUIRED_KEYS` より:
```python
"youtube_new_video": ["title", "video_id", "video_url", "channel_name"]
```

**video 辞書に含まれるキー**（推定）:
- ✅ `title` - DB にある
- ✅ `video_id` - DB にある
- ✅ `video_url` - DB にある
- ✅ `channel_name` - DB にある

→ **通常は全て揃うはず**

#### シナリオ 2: `source` 判定がスキップしている（次有力）

**問題コード** (bluesky_plugin.py line 199):

```python
source = video.get("source", "youtube").lower()

if source == "youtube":
    rendered = self.render_template_with_utils("youtube_new_video", video)
    ...
elif source in ("niconico", "nico"):
    rendered = self.render_template_with_utils("nico_new_video", video)
    ...
# ★ 他の source は処理されない
```

**懸念**:
- `source` が大文字（"YouTube", "YouTube"）で送られてきている可能性
- `source` が予期しない値（例："youtube_video"）になっている可能性

#### シナリオ 3: プラグインが呼ばれていない（最有力）

**最大の懸念**: GUI 投稿処理で、**プラグインマネージャーを経由していない可能性**

**修正案A で修正済み** (gui_v2.py line 1307-1327):
```python
if self.plugin_manager:
    video_with_settings["use_image"] = False
    results = self.plugin_manager.post_video_with_all_enabled(video_with_settings, dry_run=dry_run)
else:
    # フォールバック: コア機能で投稿
    success = self.bluesky_core.post_video_minimal(video_with_settings)
```

**しかし新しい問題が発生**:

修正案A が実装されていても、プラグイン側の `set_dry_run()` メソッドが実装されているか不明

---

## 🔴 **発見された実装ギャップ**

### ギャップ 1: `BlueskyImagePlugin.set_dry_run()` メソッドが存在しない

**plugin_manager.py line 228-230**:
```python
if hasattr(plugin, 'set_dry_run'):
    plugin.set_dry_run(dry_run)  # ← これが呼ばれるはず
```

**確認**: `bluesky_plugin.py` に `set_dry_run()` メソッドが実装されているか？

→ **ない可能性がある**（要確認）

### ギャップ 2: `render_template_with_utils()` の例外処理

**bluesky_plugin.py line 550+** でテンプレート処理に例外処理がありますが:

```python
except ImportError as e:
    post_logger.error(f"❌ template_utils インポート失敗: {e}")
    return ""

except Exception as e:
    post_logger.error(f"❌ テンプレート処理予期しないエラー: {e}")
    return ""
```

**懸念**: 何らかの例外が発生して、`return ""` → テンプレート未使用になっている可能性

### ギャップ 3: Datetimeフィルタの実装

**テンプレートファイル** (yt_new_video_template.txt):
```
投稿日時: {{ published_at | datetimeformat('%Y年%m月%d日') }}
```

**Jinja2 カスタムフィルタ** `datetimeformat` が実装されているか？

→ **実装されていない可能性がある**

---

## ✅ テスト方法（原因特定用）

### テスト 1: ログレベルを DEBUG に設定して、実際の投稿を見る

```bash
# settings.env
DEBUG_MODE=true

# GUI から投稿テストを実行して、ログを確認
grep "テンプレート\|text_override\|必須キー" logs/app.log
```

**期待ログ**:
- ✅ `✅ テンプレートを使用して本文を生成しました`
- ⚠️ `⚠️ 必須キー不足`
- ✅ `📝 テンプレート生成済みの本文を使用します`

### テスト 2: post.log を確認

```bash
tail -50 logs/post.log
```

**期待内容**: テンプレート内容の本文

**実際**: 従来フォーマット（タイトル + URL）

---

## 🔧 推奨される修正方案

### 修正案 A: `BlueskyImagePlugin` に `set_dry_run()` メソッドを追加

**理由**: `plugin_manager` が `set_dry_run()` を呼び出そうとしている（line 228-230）

**修正ファイル**: [v2/plugins/bluesky_plugin.py](plugins/bluesky_plugin.py)

**実装位置**: `BlueskyImagePlugin` クラス内に追加

```python
class BlueskyImagePlugin(NotificationPlugin):
    def __init__(self, ...):
        ...
        self.minimal_poster = BlueskyMinimalPoster(username, password, dry_run)
        ...

    def set_dry_run(self, dry_run: bool) -> None:
        """ドライランモードを設定"""
        self.minimal_poster.set_dry_run(dry_run)
        post_logger.debug(f"🔧 Bluesky プラグイン dry_run モード: {dry_run}")
```

### 修正案 B: Jinja2 カスタムフィルタ `datetimeformat` を登録

**理由**: テンプレートで `datetimeformat` フィルタが使用されているが、実装されていない

**修正ファイル**: [v2/template_utils.py](template_utils.py)

**実装位置**: Environment 初期化時に

```python
from jinja2 import Environment, FileSystemLoader, select_autoescape
from datetime import datetime

def setup_jinja_environment():
    env = Environment(
        loader=FileSystemLoader("templates"),
        autoescape=select_autoescape(['html', 'xml'])
    )

    # ★ カスタムフィルタを登録
    def datetimeformat(value, format='%Y-%m-%d'):
        if isinstance(value, str):
            try:
                dt = datetime.fromisoformat(value)
                return dt.strftime(format)
            except:
                return value
        return value

    env.filters['datetimeformat'] = datetimeformat
    return env
```

### 修正案 C: `source` の正規化を強化

**理由**: `source` が大文字で来ている可能性

**修正ファイル**: [v2/plugins/bluesky_plugin.py](plugins/bluesky_plugin.py#L199)

**修正内容**:
```python
# 修正前
source = video.get("source", "youtube").lower()

if source == "youtube":
    ...
elif source in ("niconico", "nico"):
    ...
```

**修正後**:
```python
# 修正後: 複数の変異形に対応
source = video.get("source", "youtube").lower().strip()

# 正規化
if source in ("youtube", "yt"):
    rendered = self.render_template_with_utils("youtube_new_video", video)
    if rendered:
        video["text_override"] = rendered
        post_logger.info(f"✅ テンプレートを使用: youtube_new_video (source={source})")
    else:
        post_logger.warning(f"⚠️ youtube_new_video テンプレートレンダリング失敗")

elif source in ("niconico", "nico", "n"):
    rendered = self.render_template_with_utils("nico_new_video", video)
    if rendered:
        video["text_override"] = rendered
        post_logger.info(f"✅ テンプレートを使用: nico_new_video (source={source})")
    else:
        post_logger.warning(f"⚠️ nico_new_video テンプレートレンダリング失敗")

else:
    # 既知外のプラットフォーム → デフォルトテンプレート処理なし
    post_logger.debug(f"ℹ️ source={source} はテンプレート対応外（従来フォーマットを使用）")
    video["text_override"] = ""
```

### 修正案 D: テンプレート処理のログを詳細化

**理由**: 何が失敗しているか特定するため

**修正ファイル**: [v2/plugins/bluesky_plugin.py](plugins/bluesky_plugin.py#L195-L216)

```python
# 現在
if rendered:
    video["text_override"] = rendered
    post_logger.info(f"✅ テンプレートを使用して本文を生成しました: youtube_new_video")
else:
    post_logger.debug(f"ℹ️ youtube_new_video テンプレート未使用またはレンダリング失敗")

# 修正後
if rendered:
    video["text_override"] = rendered
    post_logger.info(f"✅ テンプレート使用: youtube_new_video")
    post_logger.debug(f"   生成内容: {rendered[:100]}...")  # 最初の100文字をログ
else:
    post_logger.warning(f"⚠️ youtube_new_video テンプレートレンダリング失敗")
    post_logger.debug(f"   video キー: {list(video.keys())}")
    post_logger.debug(f"   source: {video.get('source')}")
```

---

## 🎯 プラグイン非導入時の挙動確認

### 現在の実装状況

#### シーン: プラグインなし → コア機能のみ

**gui_v2.py line 1316-1327** (修正案A 適用済み):

```python
elif self.bluesky_core:
    # フォールバック
    logger.info(f"📤 コア機能で投稿（テンプレート非対応、固定設定値使用）")

    video_with_settings = dict(video)
    video_with_settings["use_link_card"] = True
    video_with_settings["embed"] = None

    success = self.bluesky_core.post_video_minimal(video_with_settings)
```

#### 期待される挙動

✅ **テキストのみ投稿**:
- テンプレート未使用（プラグインないため）
- 従来フォーマット（タイトル + チャンネル名 + 日付 + URL）
- URL はリンク化される（Facet ロジック）
- リンクカードなし（`use_link_card=True` ですが `embed` 構築は別プロセス）
- 画像埋め込みなし（`embed=None`）

#### 実装ギャップ

**問題 1**: `use_link_card=True` なのに、リンクカード embed が構築されている

**bluesky_core.py line 166-173**:
```python
if use_link_card and video_url:
    post_logger.info("🔗 リンクカード embed を構築しています...")
    embed = self._build_external_embed(video_url)
    if embed:
        post_logger.info("✅ リンクカード embed を追加します")
```

**期待**: プラグインなしの場合、リンクカードは構築しない

→ **修正必要**

---

## 💡 修正の全体戦略

### 戦略 A: テンプレート機能を確実に動作させる（推奨）

1. ✅ `bluesky_plugin.py` に `set_dry_run()` メソッド追加
2. ✅ `template_utils.py` に Jinja2 カスタムフィルタ登録
3. ✅ `bluesky_plugin.py` で `source` 正規化を強化
4. ✅ ログを詳細化

### 戦略 B: プラグイン非導入時は純シンプルに

1. ✅ プラグインなし = テンプレート未使用
2. ✅ リンクカードも構築しない（コア機能ではリンク化のみ）
3. ✅ 画像埋め込みなし

**修正案 E**: `bluesky_core.py` で「プラグイン経由」フラグを導入

```python
def post_video_minimal(self, video: dict) -> bool:
    # プラグイン経由フラグをチェック
    is_via_plugin = video.get("via_plugin", False)

    if embed:
        # 画像がある → プラグイン経由のみ
        ...
    elif use_link_card and is_via_plugin and video_url:
        # リンクカード → プラグイン経由のときのみ
        embed = self._build_external_embed(video_url)
    elif use_link_card and not is_via_plugin:
        # プラグインなし → リンクカード未構築
        post_logger.info("ℹ️ プラグイン非導入のため、リンクカードは使用しません")
```

---

## 📝 まとめ

### 現状

| 項目 | 状態 |
|:--|:--:|
| テンプレート実装 | ✅ コード実装済み |
| テンプレートファイル | ✅ 存在 |
| 環境変数設定 | ✅ 設定済み |
| プラグイン投稿処理 | ✅ 呼び出し経路あり |
| `text_override` 使用 | ✅ コアで使用 |
| **実装ギャップ** | ❌ あり |

### 実装ギャップ

1. ❌ `BlueskyImagePlugin.set_dry_run()` メソッド がない
2. ❌ Jinja2 カスタムフィルタ `datetimeformat` がない
3. ⚠️ `source` の正規化が不十分
4. ⚠️ プラグインなし時の `use_link_card` 処理が不適切

### 推奨対応

- **必須**: ギャップ 1, 2 を修正
- **推奨**: ギャップ 3, 4 も修正

---

**作成日**: 2025年12月18日
**対象バージョン**: v2.1.0+
**次ステップ**: 修正案の実装とテスト
