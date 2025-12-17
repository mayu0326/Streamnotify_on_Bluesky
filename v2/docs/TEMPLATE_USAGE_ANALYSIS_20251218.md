# テンプレート投稿統合 - 使用状況分析レポート

**実施日：** 2025年12月18日
**対象バージョン：** v2.1.0+
**ステータス：** 🔍 調査完了 → ⚠️ 問題特定 → 🔧 修正案提示

---

## 1. 実装状況サマリ

### 1.1 テンプレート統合の実装状況

| コンポーネント | 実装状態 | 詳細 |
|:--|:--:|:--|
| `template_utils.py` | ✅ 完全実装 | テンプレート読み込み・検証・レンダリング機能完備 |
| `bluesky_plugin.py::post_video()` | ✅ 完全実装 | テンプレートレンダリング処理を追加（行195-216） |
| `bluesky_core.py::post_video_minimal()` | ✅ 完全実装 | `text_override` 優先処理を追加 |
| テンプレートファイル | ✅ 配置完了 | `templates/youtube/yt_new_video_template.txt` など存在 |
| 環境変数設定 | ✅ 定義済み | `TEMPLATE_YOUTUBE_NEW_VIDEO_PATH` など定義 |

### 1.2 投稿フローの分類

v2 では **2つの投稿フロー** が存在します：

#### フロー A：プラグイン経由（推奨） ✅ テンプレート対応済み

```
【GUI または auto_post モード】
   ↓
plugin_manager.post_video_with_all_enabled(video)
   ↓
BlueskyImagePlugin.post_video(video)
   ├─ 画像処理
   ├─ テンプレートレンダリング ← ★ ココで render_template_with_utils() を呼び出し
   │  ├─ render_template_with_utils("youtube_new_video", video)
   │  ├─ video["text_override"] をセット
   │  └─ post.log に情報を記録
   └─ BlueskyMinimalPoster.post_video_minimal(video) へ
   ↓
BlueskyMinimalPoster.post_video_minimal(video)
   ├─ text_override が存在？ → YES: テンプレート本文を使用
   └─ Bluesky API 呼び出し
```

#### フロー B：直接呼び出し ❌ テンプレート非対応

```
【GUI - 投稿設定ウィンドウ（プラグイン未導入または非使用時）】
   ↓
GUI.post_video() 内の条件分岐
   ├─ use_plugin = False または bluesky_core のみ利用
   └─ bluesky_core.post_video_minimal(video) 直接呼び出し
   ↓
BlueskyMinimalPoster.post_video_minimal(video)
   ├─ text_override は設定されていない ← 問題！
   ├─ 従来固定フォーマットを使用
   └─ テンプレートが使われない
```

---

## 2. 問題特定

### 2.1 「テンプレートが使われていない」の原因

#### 原因 1: GUI で直接呼び出しされている場合 ⚠️

**現象：**
- GUI の投稿設定ウィンドウで「投稿」ボタンを押した場合
- `bluesky_core.post_video_minimal()` が直接呼び出される
- テンプレートレンダリングが実行されない

**コード位置：** [gui_v2.py](gui_v2.py#L1312) 行1312

```python
else:
    # テキスト + URLリンク投稿
    if self.bluesky_core:
        logger.info(f"📤 コア機能で投稿（URLリンク）: {video['title']}")
        # ★ dry_run フラグを設定
        if hasattr(self.bluesky_core, 'set_dry_run'):
            self.bluesky_core.set_dry_run(dry_run)
        success = self.bluesky_core.post_video_minimal(video)  # ← 直接呼び出し、テンプレートなし
```

**影響：**
- UI 経由の手動投稿ではテンプレートが使用されない
- ユーザーは固定フォーマットでしか投稿できない

#### 原因 2: auto_post モードでプラグインが有効化されていない可能性

**現象：**
- `main_v2.py` の auto_post 処理（行238）は `plugin_manager.post_video_with_all_enabled()` を呼び出している
- これはプラグイン経由のため **理論的にはテンプレート対応**
- ただし、プラグインが無効化されていると動作しない

**コード位置：** [main_v2.py](main_v2.py#L238) 行238

```python
results = plugin_manager.post_video_with_all_enabled(selected_video)
```

**確認項目：**
- `BlueskyImagePlugin` が実際に `enable_plugin()` されているか
- `post_logger` に「✅ テンプレートを使用して本文を生成しました」が出力されているか

### 2.2 症状の分類

| 投稿方法 | テンプレート状態 | 原因 | 対応 |
|:--|:--:|:--|:--|
| **GUI 手動投稿** | ❌ 使用されない | 直接呼び出し | 修正案 A 参照 |
| **auto_post モード** | ✅ 使用される（はず） | プラグイン経由 | 確認・検証 |
| **プラグイン経由（API）** | ✅ 使用される | 正常 | 問題なし |

---

## 3. テンプレート実装の確認

### 3.1 bluesky_plugin.py の実装確認

**行195-216: テンプレートレンダリング処理**

```python
# ============ テンプレートレンダリング（新着動画投稿用） ============
# YouTube / ニコニコの新着動画投稿時にテンプレートを使用
source = video.get("source", "youtube").lower()
rendered = ""

if source == "youtube":
    # YouTube 新着動画用テンプレート
    rendered = self.render_template_with_utils("youtube_new_video", video)
    if rendered:
        video["text_override"] = rendered
        post_logger.info(f"✅ テンプレートを使用して本文を生成しました: youtube_new_video")
    else:
        post_logger.debug(f"ℹ️ youtube_new_video テンプレート未使用またはレンダリング失敗（従来フォーマットを使用）")
elif source in ("niconico", "nico"):
    # ニコニコ新着動画用テンプレート
    rendered = self.render_template_with_utils("nico_new_video", video)
    if rendered:
        video["text_override"] = rendered
        post_logger.info(f"✅ テンプレートを使用して本文を生成しました: nico_new_video")
    else:
        post_logger.debug(f"ℹ️ nico_new_video テンプレート未使用またはレンダリング失敗（従来フォーマットを使用）")
```

**確認結果：** ✅ 実装済み

### 3.2 bluesky_core.py の実装確認

**テンプレート本文優先処理**

```python
# text_override がある場合は優先（テンプレートレンダリング済み）
text_override = video.get("text_override")
...
if text_override:
    # プラグイン側でテンプレートから生成した本文を優先
    post_text = text_override
    post_logger.info(f"📝 テンプレート生成済みの本文を使用します")
elif source == "niconico":
    post_text = f"{title}\n\n📅 {published_at[:10]}\n\n{video_url}"
else:
    post_text = f"{title}\n\n🎬 {channel_name}\n📅 {published_at[:10]}\n\n{video_url}"
```

**確認結果：** ✅ 実装済み

### 3.3 必須キー検証

**`template_utils.py` の定義**

```python
TEMPLATE_REQUIRED_KEYS = {
    "youtube_new_video": ["title", "video_id", "video_url", "channel_name"],
    "nico_new_video": ["title", "video_id", "video_url", "channel_name"],
}
```

**video 辞書に必要なキー：**
- `title` - 動画タイトル
- `video_id` - YouTube ID または sm00000000
- `video_url` - 動画 URL
- `channel_name` - チャンネル名

**確認結果：** ✅ 定義済み

---

## 4. 修正案

### 修正案 A: GUI の直接呼び出しをプラグイン経由に変更（推奨）

**目的：** 手動投稿もテンプレートを使用するように統一

**変更ファイル：** [gui_v2.py](gui_v2.py#L1310-L1320)

**現在のコード（問題あり）：**

```python
else:
    # テキスト + URLリンク投稿
    if self.bluesky_core:
        logger.info(f"📤 コア機能で投稿（URLリンク）: {video['title']}")
        if hasattr(self.bluesky_core, 'set_dry_run'):
            self.bluesky_core.set_dry_run(dry_run)
        success = self.bluesky_core.post_video_minimal(video)  # ← テンプレート非対応
        if success and not dry_run:
            self.db.mark_as_posted(video["video_id"])
```

**修正後のコード（推奨）：**

```python
else:
    # テキスト + URLリンク投稿（プラグイン経由でテンプレート対応）
    if self.plugin_manager:
        logger.info(f"📤 プラグイン経由で投稿（テンプレート対応）: {video['title']}")
        video["use_image"] = False  # 画像なしモード
        # ★ dry_run フラグを渡す
        results = self.plugin_manager.post_video_with_all_enabled(video, dry_run=dry_run)
        success = any(results.values())  # 任意のプラグイン成功で OK
        if success and not dry_run:
            self.db.mark_as_posted(video["video_id"])
    elif self.bluesky_core:
        # フォールバック：プラグインがない場合はコア機能を直接呼び出し
        logger.info(f"📤 コア機能で投稿（テンプレート非対応）: {video['title']}")
        if hasattr(self.bluesky_core, 'set_dry_run'):
            self.bluesky_core.set_dry_run(dry_run)
        success = self.bluesky_core.post_video_minimal(video)
        if success and not dry_run:
            self.db.mark_as_posted(video["video_id"])
```

**効果：**
- ✅ GUI 手動投稿もテンプレートを使用
- ✅ プラグインなしの場合のフォールバック対応
- ✅ 投稿フローが一本化される

### 修正案 B: auto_post での動作確認

**確認手順：**

1. `settings.env` で以下を設定
   ```bash
   OPERATION_MODE=auto_post
   TEMPLATE_YOUTUBE_NEW_VIDEO_PATH=templates/youtube/yt_new_video_template.txt
   ```

2. `post.log` で以下のログを確認
   ```
   [INFO] ✅ テンプレートを使用して本文を生成しました: youtube_new_video
   [INFO] 📝 テンプレート生成済みの本文を使用します
   ```

3. テンプレートが使用されていない場合の確認
   ```
   - プラグイン有効化ログを確認: [INFO] ✅ Bluesky 拡張機能プラグインを有効化しました
   - video 辞書の必須キーをデバッグ出力: post_logger.debug(f"video keys: {video.keys()}")
   - render_template_with_utils() の戻り値をチェック
   ```

### 修正案 C: テンプレートが読み込めない場合の診断

**デバッグ手順：**

1. `settings.env` で `DEBUG_MODE=true` に設定
2. 以下を `bluesky_plugin.py` の `render_template_with_utils()` 直後に追加

```python
post_logger.debug(f"🔍 テンプレートレンダリング診断:")
post_logger.debug(f"   template_type: {template_type}")
post_logger.debug(f"   event_context keys: {event_context.keys()}")
post_logger.debug(f"   rendered length: {len(rendered)}")
post_logger.debug(f"   rendered[:100]: {rendered[:100]}")
```

3. `logs/post.log` で出力を確認

---

## 5. テンプレート使用状況の確認フロー

```
【投稿実行】
   ↓
【Step 1】投稿フロー判定
   ├─ GUI 手動投稿？
   ├─ auto_post モード？
   └─ API 経由？
   ↓
【Step 2】プラグイン有効化確認
   ├─ BlueskyImagePlugin が enable_plugin() されているか？
   │  └─ logs/app.log で "✅ Bluesky 拡張機能プラグインを有効化しました" を確認
   └─ プラグインがない場合は従来フォーマット使用
   ↓
【Step 3】テンプレートレンダリング
   ├─ source が "youtube" または "niconico"？
   ├─ 必須キー完備？（title, video_id, video_url, channel_name）
   └─ テンプレートファイルが存在？（templates/youtube/yt_new_video_template.txt など）
   ↓
【Step 4】ログ確認
   ├─ post.log に以下のいずれかが出力されているか確認
   │  ├─ "✅ テンプレートを使用して本文を生成しました" → テンプレート使用
   │  ├─ "ℹ️ テンプレート未使用またはレンダリング失敗" → フォールバック
   │  └─ "⚠️ 必須キー不足" → キーが不足
   └─ "📝 テンプレート生成済みの本文を使用します" → テンプレート本文が適用
```

---

## 6. 動作検証チェックリスト

| 項目 | 確認方法 | 期待結果 | 状態 |
|:--|:--|:--|:--:|
| プラグイン有効化 | app.log で "✅ Bluesky 拡張機能プラグイン" | 出力される | ⏳ |
| テンプレートレンダリング | post.log で "✅ テンプレートを使用" | 出力される | ⏳ |
| テンプレート本文適用 | post.log で "📝 テンプレート生成済み" | 出力される | ⏳ |
| 投稿本文確認 | Bluesky で投稿内容を確認 | テンプレート形式 | ⏳ |
| フォールバック動作 | テンプレート未設定時 | 従来フォーマット使用 | ⏳ |

---

## 7. 推奨アクション

### 即座に実施すべき対応

1. **修正案 A を適用** - GUI の直接呼び出しをプラグイン経由に変更
   - ファイル: `gui_v2.py` 行1310-1320
   - 優先度: 🔴 高

2. **auto_post モードで検証** - テンプレートが実際に使用されているか確認
   - 検証手順: 修正案 B 参照
   - 優先度: 🔴 高

3. **ログを詳細化** - デバッグ用の詳細ログを追加
   - 検証手順: 修正案 C 参照
   - 優先度: 🟡 中

### 今後の改善

- [ ] GUI で「投稿方法」（プラグイン使用/非使用）を選択可能にする
- [ ] テンプレート状態をリアルタイムで GUI に表示
- [ ] テンプレートプレビュー機能の実装

---

**著作権**: Copyright (C) 2025 mayuneco(mayunya)
**ライセンス**: GPLv2
