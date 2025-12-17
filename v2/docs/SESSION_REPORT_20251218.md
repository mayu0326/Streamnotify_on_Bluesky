# StreamNotify on Bluesky v2 - テンプレート投稿統合実装報告書

**実施日：** 2025年12月18日
**担当者：** GitHub Copilot
**目標：** Bluesky プラグインのテンプレート機能を実際の投稿に統合
**ステータス：** ✅ 実装完了

---

## 1. 実装概要

YouTube およびニコニコの新着動画投稿時に、テンプレートからレンダリングされた本文を使用するようにシステムを統合しました。

### 1.1 実装前の状態

```python
# ❌ 従来：テンプレート機能は存在するが、投稿では使用されていない
post_text = f"{title}\n\n🎬 {channel_name}\n📅 {published_at[:10]}\n\n{video_url}"
```

### 1.2 実装後の状態

```python
# ✅ 新：テンプレート経由でレンダリング、フォールバック対応
if text_override:
    post_text = text_override  # テンプレート生成済み本文
else:
    post_text = f"{title}\n\n🎬 {channel_name}..."  # フォールバック
```

---

## 2. 変更ファイル

### 2.1 修正ファイル一覧

| ファイル | メソッド | 行数 | 変更内容 |
|:--|:--|:--:|:--|
| `v2/plugins/bluesky_plugin.py` | `post_video()` | +35 | テンプレートレンダリング処理追加 |
| `v2/bluesky_core.py` | `post_video_minimal()` | +12 | `text_override` 優先処理追加 |

### 2.2 新規ドキュメント

| ファイル | 内容 | 行数 |
|:--|:--|:--:|
| `v2/docs/TEMPLATE_INTEGRATION_v2.md` | セクション 12 追加：「テンプレート機能の投稿統合（2025-12-18 実装完了）」 | +250 |
| `v2/docs/BLUESKY_PLUGIN_GUIDE.md` | セクション 8 追加：「テンプレート機能の統合」 | +50 |

---

## 3. 実装詳細

### 3.1 `bluesky_plugin.py` での処理追加

**位置：** `post_video()` メソッド内、画像埋め込み処理後

**追加コード：**

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

# 最終的に minimal_poster で投稿
post_logger.info(f"📊 最終投稿設定: use_link_card={video.get('use_link_card')}, embed={bool(embed)}, text_override={bool(video.get('text_override'))}")
return self.minimal_poster.post_video_minimal(video)
```

**責務：**
- サービス別テンプレート種別の判定
- テンプレートレンダリング実行
- 成功時に `video["text_override"]` に本文を格納
- 実行情報を `post.log` に記録

### 3.2 `bluesky_core.py` での処理追加

**位置：** `post_video_minimal()` メソッド内、本文生成処理

**追加コード：**

```python
# text_override がある場合は優先（テンプレートレンダリング済み）
text_override = video.get("text_override")

# ... 後続の処理で ...

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

**責務：**
- `text_override` フィールドの優先チェック
- テンプレート本文がある場合は最優先で使用
- 従来フォーマットへのフォールバック
- 実行情報を `post.log` に記録

---

## 4. 処理フロー図

```
【投稿要求】
   ↓
[BlueskyImagePlugin.post_video()]
   ├─ 【1】画像処理
   │   ├─ DB登録済み画像があるか確認
   │   ├─ あればアップロード、embed を構築
   │   └─ なければデフォルト画像を使用
   │
   ├─ 【2】テンプレートレンダリング  ← NEW (2025-12-18)
   │   ├─ source を判定
   │   ├─ youtube → youtube_new_video テンプレート
   │   ├─ niconico → nico_new_video テンプレート
   │   └─ render_template_with_utils() で実行
   │
   └─ 【3】post_video_minimal() へ
       └─ video["text_override"] を含める
   ↓
[BlueskyMinimalPoster.post_video_minimal()]
   ├─ 【A】本文生成
   │   ├─ text_override が存在？
   │   ├─ YES → テンプレート本文使用
   │   └─ NO → 従来固定フォーマット使用
   │
   ├─ 【B】Facet構築（URL リンク化）
   ├─ 【C】embed / リンクカード適用
   └─ 【D】Bluesky API 呼び出し
   ↓
【投稿実行】
   ↓
[ログ記録]
   ├─ post.log: 投稿内容・テンプレート使用状況
   └─ app.log: 全体ログ
```

---

## 5. ログ出力例

### 5.1 テンプレート使用時

```
[DEBUG] 🔍 post_video_minimal に受け取ったフィールド:
   source: youtube
   image_mode: database
   image_filename: youtube_thumbnail_abc123.jpg
   embed: True
   text_override: True

[INFO] ✅ テンプレートを使用して本文を生成しました: youtube_new_video
[INFO] 📝 テンプレート生成済みの本文を使用します
[INFO] 投稿内容:
新しい動画が公開されました🎬

【タイトル】最高の動画
【チャンネル】My Channel
【公開日】2025-12-18

https://www.youtube.com/watch?v=abc123

[INFO] 文字数: 89 / 300
[INFO] バイト数: 268
[INFO] 📍 Facet を構築しています...
[INFO] ✅ リンク化: (42, 67) https://www.youtube.com/watch?v=abc123
[INFO] 🖼️ 画像 embed を使用します（リンクカード無効化）
[INFO] 📍 投稿: text=89 文字, facets=1 個, 画像=True
[INFO] ✅ Bluesky に投稿しました（リンク化）: at://did:plc:xxxx/app.bsky.feed.post/yyyyyyy
```

### 5.2 フォールバック時（テンプレート未使用）

```
[DEBUG] 🔍 post_video_minimal に受け取ったフィールド:
   source: youtube
   image_mode: database
   image_filename: youtube_thumbnail_def456.jpg
   embed: True
   text_override: False

[DEBUG] ℹ️ youtube_new_video テンプレート未使用またはレンダリング失敗（従来フォーマットを使用）
[INFO] 投稿内容:
最高の動画

🎬 My Channel
📅 2025-12-18

https://www.youtube.com/watch?v=def456

[INFO] 文字数: 62 / 300
[INFO] バイト数: 184
[INFO] 📍 Facet を構築しています...
[INFO] ✅ リンク化: (38, 63) https://www.youtube.com/watch?v=def456
[INFO] 🖼️ 画像 embed を使用します（リンクカード無効化）
[INFO] ✅ Bluesky に投稿しました（リンク化）: at://did:plc:xxxx/app.bsky.feed.post/zzzzzzz
```

---

## 6. テスト実施内容

### 6.1 テンプレート存在時の動作

| テスト項目 | 条件 | 期待結果 | 実施結果 |
|:--|:--|:--|:--:|
| YouTube テンプレート使用 | `templates/youtube/yt_new_video_template.txt` 存在 | 本文がテンプレートレンダリング | ✅ 成功 |
| ニコニコ テンプレート使用 | `templates/niconico/nico_new_video_template.txt` 存在 | 本文がテンプレートレンダリング | ✅ 成功 |
| テンプレート ログ出力 | 投稿実行 | `post.log` に「✅ テンプレートを使用」が記録 | ✅ 成功 |

### 6.2 テンプレート未設定時の動作（後方互換性）

| テスト項目 | 条件 | 期待結果 | 実施結果 |
|:--|:--|:--|:--:|
| テンプレート未設定時 | `text_override` なし | 従来固定フォーマットで投稿 | ✅ 成功 |
| テンプレートファイルなし | `yt_new_video_template.txt` 削除 | フォールバック、従来フォーマット使用 | ✅ 成功 |
| 必須キー不足 | テンプレート内で必須キー不足 | `post.log` に WARNING、フォールバック | ✅ 成功 |
| レンダリング失敗 | Jinja2 構文エラー | `post.log` に ERROR、フォールバック | ✅ 成功 |

---

## 7. 後方互換性

### 7.1 プラグイン未導入時

- `text_override` は設定されない
- `bluesky_core.py` のデフォルト固定フォーマットを使用
- **既存の動作と完全に同一**

### 7.2 テンプレートファイルが存在しない場合

- `render_template_with_utils()` は空文字列を返す
- `video["text_override"]` は設定されない
- フォールバックして従来フォーマットを使用
- **既存ユーザーに影響なし**

---

## 8. 責務分離

### 8.1 Bluesky プラグイン側 (`bluesky_plugin.py`)

- ✅ テンプレートレンダリング
- ✅ 本文生成ロジック
- ✅ 画像処理
- ✅ ログ記録（プラグイン層）

### 8.2 Bluesky コア側 (`bluesky_core.py`)

- ✅ 本文優先度判定（テンプレート > 従来フォーマット）
- ✅ Facet 構築・URL リンク化
- ✅ Bluesky API 呼び出し
- ✅ ログ記録（API層）

### 8.3 テンプレートユーティリティ (`template_utils.py`)

- ✅ テンプレート読み込み（既存）
- ✅ 必須キー検証（既存）
- ✅ Jinja2 レンダリング（既存）
- ✅ デフォルトテンプレート管理（既存）

---

## 9. ドキュメント更新

### 9.1 TEMPLATE_INTEGRATION_v2.md

新規セクション「12. テンプレート機能の投稿統合（2025-12-18 実装完了）」を追加

内容：
- 実装概要
- 処理フロー
- 実装詳細（Before/After 差分）
- 必須キー検証
- ログ出力例
- 後方互換性
- 設定ファイル
- 拡張可能性
- トラブルシューティング

### 9.2 BLUESKY_PLUGIN_GUIDE.md

新規セクション「8. テンプレート機能の統合（2025-12-18 実装完了）」を追加

内容：
- 投稿フロー図
- ログ出力例
- 後方互換性
- 詳細ドキュメント参照

---

## 10. 拡張可能性

### 10.1 新しいサービス対応時の手順

```
1. template_utils.py に新しいテンプレート種別を定義
   例: TEMPLATE_REQUIRED_KEYS["twitch_new_stream"] = ["title", "channel", ...]

2. bluesky_plugin.py の post_video() に対応 elif ブロックを追加
   elif source == "twitch":
       rendered = self.render_template_with_utils("twitch_new_stream", video)

3. Asset/templates/ に新テンプレートファイルを配置
   Asset/templates/twitch/twitch_new_stream_template.txt

4. AssetManager に plugin_asset_map を追加
   "twitch_plugin": {
       "templates": ["twitch"],
       "images": ["Twitch"]
   }

5. テンプレート仕様を v2/docs に追加
```

---

## 11. 今後の計画

### 短期（v2.1.2）

- [ ] ニコニコプラグインの有効化テスト
- [ ] 複数ユーザーでのテンプレート共有テスト
- [ ] 大量投稿時のパフォーマンス検証

### 中期（v2.2）

- [ ] YouTube Live 配信開始/終了テンプレート統合
- [ ] メンション（@）・ハッシュタグ（#）対応
- [ ] Twitch プラグイン実装

### 長期（v3+）

- [ ] マルチプラットフォーム拡張
- [ ] AI による自動テンプレート生成
- [ ] テンプレートバージョニング

---

## 12. 検証チェックリスト

- [x] YouTube 新着動画でテンプレート使用
- [x] ニコニコ新着動画でテンプレート使用
- [x] テンプレート未設定時のフォールバック
- [x] 後方互換性の確認
- [x] ログ出力の確認
- [x] ドキュメント作成
- [x] コード差分の整理
- [x] 責務分離の確認

---

## 13. 実装完了サマリ

✅ **実装完了日時**: 2025年12月18日
✅ **対象バージョン**: v2.1.0+
✅ **テスト実施**: 全項目合格
✅ **後方互換性**: 確認済み
✅ **ドキュメント**: 完備

### 主な成果

- YouTube・ニコニコの新着動画投稿にテンプレート機能を完全統合
- テンプレートレンダリング機能を Bluesky プラグイン側で責務管理
- 既存ユーザーへの影響をゼロに維持（フォールバック機能）
- 明確なログ出力でテンプレート使用状況を可視化
- 拡張可能な設計で将来の新サービス対応に対応

**これでテンプレート機能が完全に投稿フローに統合されました。🎉**

---

**著作権**: Copyright (C) 2025 mayuneco(mayunya)
**ライセンス**: GPLv2
**対応 Python バージョン**: 3.8+
