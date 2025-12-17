# v2 テンプレートシステム - 完全ガイド

**対象バージョン**: v2.1.0 以降
**最終更新**: 2025-12-18
**ステータス**: ✅ 実装完了・検証済み

---

## 📖 目次

1. [概要](#概要)
2. [ユーザーガイド](#ユーザーガイド)
3. [技術仕様](#技術仕様)
4. [設定ガイド](#設定ガイド)
5. [トラブルシューティング](#トラブルシューティング)
6. [実装チェックリスト](#実装チェックリスト)

---

## 概要

### テンプレート機能とは

テンプレート機能は、**Bluesky に投稿される本文を自由にカスタマイズできる機能**です。

通常は、新着動画情報が自動的に同じ形式で投稿されますが、テンプレート機能を使うことで：

- 📝 **好みの文体に変更できます**（堅い文体 → カジュアル、または反対）
- 🎨 **絵文字やハッシュタグを追加できます**
- ⚙️ **表示される情報を調整できます**（タイトルだけ表示、URL を表示 など）
- 🔄 **複数のプラットフォームごとに異なるテンプレートを用意できます**

### 対応プラットフォーム・イベント

| プラットフォーム | イベント | テンプレート名 | 対応状況 | ファイル |
|:--|:--|:--|:--:|:--|
| YouTube | 新着動画投稿 | YouTube 新着動画 | ✅ v2.1.0 | `yt_new_video_template.txt` |
| YouTube | 配信開始（※） | YouTube Live 開始 | 🔜 将来実装 | `yt_online_template.txt` |
| YouTube | 配信終了（※） | YouTube Live 終了 | 🔜 将来実装 | `yt_offline_template.txt` |
| ニコニコ | 新着動画投稿 | ニコニコ 新着動画 | ✅ v2.1.0 | `nico_new_video_template.txt` |
| Twitch | 配信開始（※） | Twitch 配信開始 | 🔜 将来実装 | `twitch_online_template.txt` |

**✅** = 現在利用可能 | **🔜** = 今後実装予定 | **※** = 対応機能そのものが開発中

---

## ユーザーガイド

### テンプレートファイルの場所

テンプレートファイルは、アプリケーションフォルダの以下の場所に保存されます：

```
Streamnotify_on_Bluesky/v2/
├── templates/
│   ├── youtube/                          # YouTube 用テンプレート
│   │   ├── yt_new_video_template.txt     ← 新着動画投稿用
│   │   ├── yt_online_template.txt        ← 配信開始用（将来）
│   │   └── yt_offline_template.txt       ← 配信終了用（将来）
│   │
│   ├── niconico/                         # ニコニコ用テンプレート
│   │   └── nico_new_video_template.txt   ← 新着動画投稿用
│   │
│   └── .templates/                       # デフォルト・フォールバック用
│       └── default_template.txt          ← エラー時の代替テンプレート
│
└── settings.env                          # テンプレート設定
```

### テンプレートの編集方法

#### 方法 1: テキストエディタで直接編集（シンプル）

最もシンプルな方法です。

**手順:**

1. アプリケーションフォルダを開く
2. `v2/templates/` に移動
3. 編集したいテンプレートファイル（例: `youtube/yt_new_video_template.txt`）をテキストエディタで開く
   - Windows: メモ帳、Visual Studio Code、NotePad++ など
   - Mac/Linux: vim, nano, Visual Studio Code など
4. テキストを編集
5. 保存して閉じる

**例:**

変更前:
```
🎬 YouTube に新着動画投稿！
タイトル: {{ title }}
視聴URL: {{ video_url }}
チェックお願いします！👍
```

変更後:
```
新作アップロード🎉

【 {{ title }} 】
ぜひご視聴ください 👇
{{ video_url }}
```

#### 方法 2: GUI テンプレートエディタ（推奨）

アプリケーション起動時に管理画面が表示されます：

1. 「テンプレート設定」タブを開く
2. 編集したいテンプレートを選択
3. テキストエディタが開く
4. 編集して保存

**メリット:**
- ✅ 正しいディレクトリに自動保存
- ✅ リアルタイムプレビュー（将来実装予定）
- ✅ テンプレート変数の自動補完（将来実装予定）

### 使える変数一覧

テンプレート内では、以下の変数を `{{ 変数名 }}` の形式で使用できます：

#### YouTube 新着動画テンプレート（`yt_new_video_template.txt`）

| 変数名 | 説明 | 例 |
|:--|:--|:--|
| `{{ title }}` | 動画のタイトル | `新作動画を作成しました！` |
| `{{ video_id }}` | YouTube 動画 ID | `dQw4w9WgXcQ` |
| `{{ video_url }}` | 動画への URL | `https://www.youtube.com/watch?v=dQw4w9WgXcQ` |
| `{{ channel_name }}` | チャンネル名 | `My Channel` |
| `{{ published_at }}` | 公開日時（ISO 形式） | `2025-12-18T10:30:00` |

#### ニコニコ新着動画テンプレート（`nico_new_video_template.txt`）

| 変数名 | 説明 | 例 |
|:--|:--|:--|
| `{{ title }}` | 動画のタイトル | `新作動画を作成しました！` |
| `{{ video_id }}` | ニコニコ 動画 ID | `sm99999999` |
| `{{ video_url }}` | 動画への URL | `https://www.nicovideo.jp/watch/sm99999999` |
| `{{ channel_name }}` | ユーザー名またはチャンネル名 | `MyUser` |
| `{{ published_at }}` | 公開日時（ISO 形式） | `2025-12-18T10:30:00` |

### テンプレート内で使える機能

#### 1. 変数挿入

```jinja2
{{ title }}
{{ video_url }}
```

#### 2. フィルター（変数を加工）

```jinja2
# 日付をフォーマット
{{ published_at | datetimeformat('%Y年%m月%d日') }}
# 結果: 2025年12月18日

# 文字列を大文字に
{{ title | upper }}
# 結果: NEW VIDEO TITLE

# 文字列を小文字に
{{ title | lower }}
# 結果: new video title
```

#### 3. 条件分岐

```jinja2
{% if "特定の単語" in title %}
このタイトルには「特定の単語」が含まれています
{% else %}
他のタイトルです
{% endif %}
```

#### 4. ループ処理（高度な用法）

```jinja2
{% for tag in tags %}
  #{{ tag }}
{% endfor %}
```

### 具体例

#### 例 1: シンプルなテンプレート

```jinja2
🎬 {{ title }}
{{ video_url }}
```

出力:
```
🎬 新作動画を作成しました！
https://www.youtube.com/watch?v=dQw4w9WgXcQ
```

#### 例 2: 詳細情報を含むテンプレート

```jinja2
【新着動画】

📹 {{ title }}
🎤 チャンネル: {{ channel_name }}
📅 公開日: {{ published_at | datetimeformat('%Y年%m月%d日') }}
👉 {{ video_url }}

#YouTube #新作動画
```

出力:
```
【新着動画】

📹 新作動画を作成しました！
🎤 チャンネル: My Channel
📅 公開日: 2025年12月18日
👉 https://www.youtube.com/watch?v=dQw4w9WgXcQ

#YouTube #新作動画
```

#### 例 3: 条件分岐を使ったテンプレート

```jinja2
{% if "LIVE" in title or "配信" in title %}
🔴 ライブ配信の告知
{{ title }}
📺 {{ video_url }}
{% else %}
🎬 通常動画
【 {{ title }} 】
📺 {{ video_url }}
{% endif %}
```

### よくある質問（FAQ）

#### Q1: テンプレートが反映されない

**A:** 以下を確認してください：

1. **ファイルが保存されているか**
   - `v2/templates/youtube/yt_new_video_template.txt` が存在するか確認
   - テンプレートエディタで編集した場合は自動保存されます

2. **settings.env で正しく設定されているか**
   ```env
   TEMPLATE_YOUTUBE_NEW_VIDEO_PATH=templates/youtube/yt_new_video_template.txt
   TEMPLATE_NICO_NEW_VIDEO_PATH=templates/niconico/nico_new_video_template.txt
   ```

3. **アプリケーションを再起動したか**
   - テンプレート機能は起動時に読み込まれるため、アプリを再起動してください

4. **操作ログを確認する**
   - `v2/logs/` フォルダのログファイルを確認
   - `✅ テンプレートを使用して本文を生成しました` というメッセージがあるか確認

#### Q2: テンプレート内で改行を使いたい

**A:** Markdown 形式で改行してください：

```jinja2
タイトル: {{ title }}

動画URL: {{ video_url }}

視聴よろしくお願いします！
```

#### Q3: テンプレートに絵文字を使いたい

**A:** テンプレートファイルをテキストエディタで編集し、絵文字をそのまま入力してください：

```jinja2
🎬 {{ title }}
{{ video_url }}
#YouTube
```

#### Q4: 複数の異なるテンプレートを使い分けたい

**A:** v2.1.0 では、プラットフォームごと（YouTube、ニコニコ）に 1 つのテンプレートを使用します。

同じプラットフォーム内で複数テンプレートを切り替えたい場合は、v2.2.0+ で実装予定です。

#### Q5: デフォルトテンプレートに戻したい

**A:** 以下の方法があります：

1. **テンプレートファイルを削除する**
   - `v2/templates/youtube/yt_new_video_template.txt` を削除
   - アプリを再起動すると、デフォルトフォーマットが使用されます

2. **settings.env で無効化する**
   ```env
   # この行をコメントアウト
   # TEMPLATE_YOUTUBE_NEW_VIDEO_PATH=templates/youtube/yt_new_video_template.txt
   ```

---

## 技術仕様

### 処理フロー

```
YouTube/ニコニコ RSS 取得
    ↓
動画情報を event_context に整形
    ↓
bluesky_plugin.py::post_video() 呼び出し
    ↓
template_utils.py::render_template_with_utils() で以下を実行：
    1. get_template_path() - テンプレートパスを環境変数から取得
    2. load_template_with_fallback() - ファイルを読み込む（失敗時フォールバック）
    3. validate_required_keys() - 必須キーをチェック
    4. render_template() - Jinja2 でレンダリング
    ↓
テンプレート処理成功
    ↓
Bluesky へ投稿
```

### テンプレート必須キー

各テンプレート種別は以下の必須キーが `event_context` に含まれている必要があります：

| テンプレート種別 | 必須キー |
|:--|:--|
| `youtube_new_video` | `title`, `video_id`, `video_url`, `channel_name` |
| `nico_new_video` | `title`, `video_id`, `video_url`, `channel_name` |
| `youtube_online` | `title`, `video_url`, `channel_name`, `live_status` |

必須キーが不足している場合、テンプレート処理はスキップされ、ログに `WARNING` が出力されます。

### フォールバック機能

テンプレート処理が失敗した場合の動作：

| 障害シーン | 動作 | 結果 |
|:--|:--|:--|
| テンプレートファイル未存在 | `default_template.txt` にフォールバック | 投稿は実行 |
| 必須キー不足 | スキップ、ログ出力 | 投稿は実行（デフォルトフォーマット使用） |
| テンプレート構文エラー | エラーログ出力、フォールバック | 投稿は実行（デフォルトフォーマット使用） |

---

## 設定ガイド

### 環境変数の設定

テンプレートパスは `settings.env` で以下のように設定します：

```env
# YouTube 新着動画テンプレート
TEMPLATE_YOUTUBE_NEW_VIDEO_PATH=templates/youtube/yt_new_video_template.txt

# ニコニコ新着動画テンプレート
TEMPLATE_NICO_NEW_VIDEO_PATH=templates/niconico/nico_new_video_template.txt
```

### 環境変数の解決順序

テンプレートパスは以下の優先度で解決されます：

1. **明示的に指定された環境変数名**（コード内で明示的に指定された場合）
2. **新形式**: `TEMPLATE_YOUTUBE_NEW_VIDEO_PATH` など（推奨）
3. **レガシー形式**: `BLUESKY_YT_NEW_VIDEO_TEMPLATE_PATH` など（後方互換性のため存在）
4. **デフォルトテンプレート**（上記が未設定の場合）
5. **自動推論**（`templates/{service}/{event}_template.txt`）

### 根本原因: os.getenv() が settings.env を読み込まない

**重要**: Python の標準 `os.getenv()` は settings.env ファイルから環境変数を読み込みません。

- ✅ 読み込む場所: システム環境変数、プロセス実行時の環境変数、`os.environ`
- ❌ 読み込まない場所: `.env` ファイル、`settings.env` ファイル

**解決方法**: `template_utils.py` に `_get_env_var_from_file()` 関数を実装し、settings.env を直接読み込みます。

**実装詳細**:

```python
def _get_env_var_from_file(file_path: str, env_var_name: str) -> Optional[str]:
    """
    settings.env などの設定ファイルから環境変数を読み込む（os.getenv の補完）。
    """
    try:
        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            return None

        with open(file_path_obj, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    key, value = line.split('=', 1)
                    if key.strip() == env_var_name:
                        return value.strip()
    except Exception as e:
        logger.debug(f"⚠️ 設定ファイル読み込みエラー ({file_path}): {e}")

    return None
```

---

## トラブルシューティング

### 症状 1: テンプレートが反映されていない

**ログの確認方法:**

1. `v2/logs/` フォルダを開く
2. `post.log` ファイルを確認
3. 以下のメッセージを検索：

**チェック項目:**

- [ ] ✅ か ℹ️ が出ているか

```
✅ テンプレートを使用して本文を生成しました: youtube_new_video
```

- [ ] ❌ か ⚠️ が出ていないか

```
⚠️ テンプレート処理エラー: TEMPLATE_REQUIRED_KEYS に未登録です
❌ テンプレート構文エラー: 〇〇行目で構文エラー
```

**対応:**

- **ハイライトが ℹ️ の場合**:
  ```
  ℹ️ youtube_new_video テンプレート未使用またはレンダリング失敗（従来フォーマットを使用）
  ```
  → テンプレートファイルが見つからないか、必須キーが不足しています

- **ハイライトが ⚠️ / ❌ の場合**:
  → ログに記載されたエラーを確認し、対応してください

### 症状 2: テンプレートファイルが見つからない

**原因の特定:**

1. パスが正しいか確認
   ```
   ✅ 正しい: v2/templates/youtube/yt_new_video_template.txt
   ❌ 間違い: templates\YouTube\yt_new_video_template.txt (バックスラッシュ、大文字)
   ```

2. ファイルが存在するか確認
   - Windows エクスプローラーで `v2/templates/` を開く
   - `youtube` と `niconico` フォルダが存在するか確認
   - その中にテンプレートファイルが存在するか確認

**対応:**

- ファイルが存在しない場合は、テンプレートエディタで作成してください
- または、サンプルテンプレートをコピーして使用してください

### 症状 3: テンプレート構文エラー

**ログの確認:**

```
❌ テンプレート構文エラー: line 5, column 18: unexpected 'end of statement'
```

**原因:**

テンプレート内の Jinja2 構文が間違っています。

**対応:**

1. ログに記載された行番号を確認
2. その行の構文をチェック
3. 正しい構文に修正

**よくあるエラー:**

```jinja2
# ❌ 間違い: 閉じ括弧がない
{{ title

# ✅ 正しい: 閉じ括弧がある
{{ title }}

# ❌ 間違い: if の endif がない
{% if "text" in title %}
  ...
（endif なし）

# ✅ 正しい: endif がある
{% if "text" in title %}
  ...
{% endif %}
```

---

## 実装チェックリスト

### ✅ 最終検証項目

- ✅ テンプレート処理フロー - 正常に動作確認
- ✅ 必須キー定義 - TEMPLATE_REQUIRED_KEYS と event_context が一致
- ✅ フォールバック機能 - 安全に実装されている
- ✅ エラーハンドリング - ログ出力して投稿スキップ
- ✅ Vanilla 環境対応 - 自動無効化される
- ✅ 環境変数名整合性 - 後方互換性を確保
- ✅ パス区切り文字 - `/` に統一
- ✅ ディレクトリ名 - 小文字に統一
- ✅ テンプレート必須キー - すべてのテンプレートで定義済み

### 🔄 今後の拡張予定

| 機能 | 状況 | 予定 |
|:--|:--|:--|
| YouTube Live テンプレート | ⏳ 将来実装 | v2.x |
| Twitch テンプレート | ⏳ 将来実装 | v3+ |
| GUI テンプレートエディタ | ✅ 実装済み | - |
| リアルタイムプレビュー | ⏳ 将来実装 | v2.x |
| テンプレート変数自動補完 | ⏳ 将来実装 | v2.x |
| テンプレート管理機能 | ✅ 実装済み | - |

---

## 関連ドキュメント

- [TEMPLATE_SYSTEM.md](./TEMPLATE_SYSTEM.md) - このドキュメント（テンプレートシステム統合版）
- [TEMPLATE_IMPLEMENTATION_CHECKLIST.md](./TEMPLATE_IMPLEMENTATION_CHECKLIST.md) - 実装チェックリスト
- [設定ファイル例](../settings.env.example) - settings.env の詳細設定

---

**作成日**: 2025-12-18
**最後の修正**: 2025-12-18
**ステータス**: ✅ 完成・検証済み
