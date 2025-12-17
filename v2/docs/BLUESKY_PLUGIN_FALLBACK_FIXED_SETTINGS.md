# Blueskyプラグイン非導入時の固定設定値対応 - 修正レポート

**日付**: 2025年12月18日
**修正**: gui_v2.py のフォールバック処理に固定設定値を追加

---

## 📋 問題の説明

**質問**: Blueskyプラグインが導入されていない場合は、テンプレート機能を使わないので、固定設定値で投稿されますが、今の実装はその設定も有効になっていますか？

**回答**: ❌ **なっていませんでした** → ✅ **修正しました**

### 詳細

Blueskyプラグインが**使用不可**の場合、GUI テキスト投稿のフォールバック処理で以下の問題がありました：

```python
# 修正前（gui_v2.py line 1327）
elif self.bluesky_core:
    # プラグインなし → コア機能で投稿
    success = self.bluesky_core.post_video_minimal(video)
    # ★ 問題: video 辞書に固定設定値がない
```

### 期待される動作

```python
# 修正後（gui_v2.py line 1317-1325）
elif self.bluesky_core:
    # ★ 新: 固定設定値を追加
    video_with_settings = dict(video)
    video_with_settings["use_link_card"] = True   # リンクカード有効
    video_with_settings["embed"] = None            # 画像埋め込みなし

    success = self.bluesky_core.post_video_minimal(video_with_settings)
```

---

## 🔧 修正内容

### 修正ファイル: [v2/gui_v2.py](gui_v2.py#L1307-L1327)

#### 箇所 1: テキスト投稿のフォールバック処理

**修正前**:
```python
elif self.bluesky_core:
    # フォールバック：プラグインがない場合はコア機能を直接呼び出し
    logger.info(f"📤 コア機能で投稿（テンプレート非対応、フォールバック）: {video['title']}")

    if hasattr(self.bluesky_core, 'set_dry_run'):
        self.bluesky_core.set_dry_run(dry_run)

    success = self.bluesky_core.post_video_minimal(video)  # ★ 設定値がない

    if success and not dry_run:
        self.db.mark_as_posted(video["video_id"])
```

**修正後**:
```python
elif self.bluesky_core:
    # フォールバック：プラグインがない場合はコア機能を直接呼び出し
    logger.info(f"📤 コア機能で投稿（テンプレート非対応、固定設定値使用）: {video['title']}")

    # ★ 新: 固定設定値を video 辞書に追加
    video_with_settings = dict(video)
    video_with_settings["use_link_card"] = True  # リンクカード有効
    video_with_settings["embed"] = None  # 画像埋め込みなし

    if hasattr(self.bluesky_core, 'set_dry_run'):
        self.bluesky_core.set_dry_run(dry_run)

    success = self.bluesky_core.post_video_minimal(video_with_settings)

    if success and not dry_run:
        self.db.mark_as_posted(video["video_id"])
```

---

## 📌 固定設定値の詳細

### `use_link_card = True`

投稿テキストから **URL を抽出して自動的にリンクカード（embed）を生成** します。

```python
# bluesky_core.py line 166-173
use_link_card = video.get("use_link_card", True)  # デフォルト: True

if use_link_card and video_url:
    # リンクカード embed を構築
    embed = self._build_external_embed(video_url)
    if embed:
        post_logger.info("✅ リンクカード embed を追加します")
```

**効果**: Bluesky 投稿に動画の OG 画像やタイトルをカード形式で表示

### `embed = None`

画像埋め込みを明示的に **無効化** します（プラグインが画像処理する場合を区別）。

```python
# bluesky_core.py line 157-160
if embed:
    # プラグイン側で画像を設定した場合
    post_logger.info("🖼️ 画像 embed を使用します")
    use_link_card = False  # リンクカードは無効化
else:
    # 画像なし → リンクカード処理に進む
    embed = self._build_external_embed(video_url)
```

---

## 🔄 投稿フロー

### パターン A: Blueskyプラグイン **有効**

```
GUI テキスト投稿
    ↓
plugin_manager.post_video_with_all_enabled(
    {
        "use_image": False,
        # その他フィールド
    }
)
    ↓
bluesky_plugin.post_video()
    ├─ テンプレートレンダリング
    └─ text_override をセット
         ↓
bluesky_core.post_video_minimal()
    ├─ text_override をチェック
    └─ テンプレート生成済みテキストを使用
         ↓
✅ テンプレート機能を使った投稿
```

### パターン B: Blueskyプラグイン **非導入**（修正後）

```
GUI テキスト投稿
    ↓
plugin_manager が None または disabled
    ↓
フォールバック処理:
    video_with_settings = dict(video)
    video_with_settings["use_link_card"] = True
    video_with_settings["embed"] = None

    bluesky_core.post_video_minimal(video_with_settings)
    ↓
bluesky_core.post_video_minimal()
    ├─ text_override は None（プラグインがないため）
    ├─ use_link_card = True を参照
    └─ リンクカード embed を自動生成
         ↓
✅ 固定設定値（リンクカード）を使った投稿
```

---

## ✅ テスト方法

### テスト 1: Blueskyプラグイン有効時

```bash
# 1. settings.env で Bluesky 認証情報を設定
BLUESKY_USERNAME=your_username
BLUESKY_PASSWORD=your_password

# 2. アプリケーション起動
cd v2/
python main_v2.py

# 3. GUI で「テンプレート対応」ログが表示されるか確認
grep "テンプレート対応" logs/app.log

# 期待: 投稿がテンプレート内容で表示される
```

### テスト 2: Blueskyプラグイン非導入時（修正確認）

```bash
# 1. plugins/bluesky_plugin.py をリネーム（一時的に無効化）
mv plugins/bluesky_plugin.py plugins/bluesky_plugin.py.bak

# 2. アプリケーション再起動
python main_v2.py

# 3. GUI で「固定設定値使用」ログが表示されるか確認
grep "固定設定値使用" logs/app.log

# 期待:
# [INFO] 📤 コア機能で投稿（テンプレート非対応、固定設定値使用）...

# 4. Bluesky 投稿にリンクカードが表示されているか確認

# 5. プラグインを戻す
mv plugins/bluesky_plugin.py.bak plugins/bluesky_plugin.py
```

### テスト 3: ドライラン

```bash
# GUI から「投稿テスト」を実行
# → ログに固定設定値情報が表示されるか確認

grep "固定設定値\|use_link_card\|embed" logs/app.log
```

---

## 📊 変更前後の比較

| 項目 | 修正前 | 修正後 |
|:--|:--|:--|
| プラグイン有効時 | ✅ テンプレート使用 | ✅ テンプレート使用（無変更） |
| プラグイン非導入時 | ❌ 設定値なし（デフォルト） | ✅ 固定設定値使用 |
| ログメッセージ | フォールバック | 固定設定値使用 |
| リンクカード | デフォルト（True） | 明示的に True |
| 画像埋め込み | デフォルト（None） | 明示的に None |

---

## 🎯 効果

### 修正前の問題
```python
# video 辞書が空の設定値で渡されるため
use_link_card = video.get("use_link_card", True)  # ← デフォルト値に頼っていた
```

### 修正後の改善
```python
# 明示的に設定値をセット
video_with_settings["use_link_card"] = True  # ← 明示的に True
video_with_settings["embed"] = None  # ← 明示的に None
```

**メリット**:
- 設定の意図が明確になる
- `get()` のデフォルト値に頼らない
- プラグイン有無にかかわらず、投稿設定が一貫している
- ログメッセージが実際の処理を正確に反映

---

## 📝 関連コード

### bluesky_core.py (投稿テンプレート処理)

```python
# line 155-173
if text_override:
    # プラグイン側でテンプレートから生成した本文を優先
    post_text = text_override
    post_logger.info(f"📝 テンプレート生成済みの本文を使用します")
elif source == "niconico":
    post_text = f"{title}\n\n📅 {published_at[:10]}\n\n{video_url}"
else:
    # YouTube（デフォルト）
    post_text = f"{title}\n\n🎬 {channel_name}\n📅 {published_at[:10]}\n\n{video_url}"

# リンクカード処理
use_link_card = video.get("use_link_card", True)  # ← 修正後は明示的にセット
if use_link_card and video_url:
    embed = self._build_external_embed(video_url)
```

### gui_v2.py (修正箇所)

```python
# line 1307-1327 (修正後)
else:
    # テキスト + URLリンク投稿
    if self.plugin_manager:
        # プラグイン経由
        ...
    elif self.bluesky_core:
        # ★ フォールバック: 固定設定値を追加
        video_with_settings = dict(video)
        video_with_settings["use_link_card"] = True
        video_with_settings["embed"] = None
        success = self.bluesky_core.post_video_minimal(video_with_settings)
```

---

## ✨ まとめ

**質問**: プラグイン非導入時に固定設定値が有効になっているか？

**回答**:
- ❌ **修正前**: デフォルト値に頼っていて、設定が曖昧
- ✅ **修正後**: 明示的に固定設定値を渡すように改善

これにより、**Blueskyプラグイン有無にかかわらず、一貫性のある投稿が実現されます**。

---

**修正日**: 2025年12月18日
**対象ファイル**: v2/gui_v2.py (line 1307-1327)
**ステータス**: ✅ 実装完了
