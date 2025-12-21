# テンプレートシステム ユーザーガイド

**対象バージョン**: v3.1.0 以降
**最終更新**: 2025-12-21
**ステータス**: ✅ 実装完了・検証済み

---

## 📖 目次

1. [概要](#概要)
2. [基本的な使い方](#基本的な使い方)
3. [テンプレート変数リファレンス](#テンプレート変数リファレンス)
4. [テンプレート記法ガイド](#テンプレート記法ガイド)
5. [実装例](#実装例)
6. [トラブルシューティング](#トラブルシューティング)

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
| YouTube | 新着動画投稿 | YouTube 新着動画 | ✅ v3.1.0 | `yt_new_video_template.txt` |
| YouTube | 配信枠設置 | YouTube Live 予約 | ✅ v3.1.0 | `yt_schedule_template.txt` |
| YouTube | 配信開始 | YouTube Live 開始 | ✅ v3.1.0 | `yt_online_template.txt` |
| YouTube | 配信終了 | YouTube Live 終了 | ✅ v3.1.0 | `yt_offline_template.txt` |
| YouTube | アーカイブ | YouTube アーカイブ | ✅ v3.1.0 | `yt_archive_template.txt` |
| ニコニコ | 新着動画投稿 | ニコニコ 新着動画 | ✅ v3.1.0 | `nico_new_video_template.txt` |
| Twitch | 配信開始 | Twitch 配信開始 | 🔜 将来実装 | `twitch_online_template.txt` |
| Twitch | 配信終了 | Twitch 配信終了 | 🔜 将来実装 | `twitch_offline_template.txt` |

**✅** = 現在利用可能 | **🔜** = 今後実装予定

---

## 基本的な使い方

### テンプレートファイルの場所

テンプレートファイルは、アプリケーションフォルダの以下の場所に保存されます：

```
v3/
├── templates/
│   ├── youtube/                          # YouTube 用テンプレート
│   │   ├── yt_new_video_template.txt     ← 新着動画投稿用
│   │   ├── yt_schedule_template.txt      ← 配信枠設置用
│   │   ├── yt_online_template.txt        ← 配信開始用
│   │   ├── yt_offline_template.txt       ← 配信終了用
│   │   └── yt_archive_template.txt       ← アーカイブ投稿用
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

#### 方法 1: テキストエディタで直接編集（推奨）

最もシンプルな方法です。

**手順:**

1. アプリケーションフォルダを開く
2. `v3/templates/` に移動
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

### テンプレート編集後の確認

テンプレートを編集したら、以下の手順で反映されているか確認してください：

1. アプリケーション再起動
2. テンプレート処理の確認
   - `v3/logs/post.log` を開く
   - `✅ テンプレートを使用して本文を生成しました` というメッセージを検索
3. テンプレートが正しく反映されているか確認

---

## テンプレート変数リファレンス

### YouTube 新着動画通知（yt_new_video_template.txt）

**必須変数:**
- `{{ title }}` … 動画タイトル
- `{{ video_id }}` … 動画ID
- `{{ video_url }}` … 動画URL（例: https://www.youtube.com/watch?v=xxxx）
- `{{ channel_name }}` … チャンネル名
- `{{ published_at }}` … 公開日時（ISO8601形式、例: 2025-12-18T10:30:00）

**オプション変数:**
- `{{ current_date }}` … 現在の日付（v3.2.0+）
- `{{ current_datetime }}` … 現在の日時（v3.2.0+）

### YouTube 配信枠設置通知（yt_schedule_template.txt）

**必須変数:**
- `{{ title }}` … 配信タイトル
- `{{ video_url }}` … 配信URL
- `{{ channel_name }}` … チャンネル名
- `{{ live_status }}` … ライブ配信ステータス

**オプション変数:**
- `{{ published_at }}` … 配信開始予定日時
- `{{ current_date }}` … 現在の日付（v3.2.0+）
- `{{ current_datetime }}` … 現在の日時（v3.2.0+）

### YouTube 配信開始通知（yt_online_template.txt）

**必須変数:**
- `{{ title }}` … 配信タイトル
- `{{ video_url }}` … 配信URL
- `{{ channel_name }}` … チャンネル名
- `{{ live_status }}` … ライブ配信ステータス

**オプション変数:**
- `{{ published_at }}` … 配信開始日時
- `{{ current_date }}` … 現在の日付
- `{{ current_datetime }}` … 現在の日時

### YouTube アーカイブ通知（yt_archive_template.txt）

**必須変数:**
- `{{ title }}` … アーカイブタイトル
- `{{ video_url }}` … アーカイブURL
- `{{ channel_name }}` … チャンネル名

**オプション変数:**
- `{{ published_at }}` … 配信日時
- `{{ current_date }}` … 現在の日付
- `{{ current_datetime }}` … 現在の日時

### ニコニコ動画投稿通知（nico_new_video_template.txt）

**必須変数:**
- `{{ title }}` … 動画タイトル
- `{{ video_id }}` … 動画ID
- `{{ video_url }}` … 動画URL
- `{{ channel_name }}` … ユーザー名またはチャンネル名
- `{{ published_at }}` … 公開日時（ISO8601形式）

**注意**: ニコニコのユーザー名は以下の優先順位で自動取得されます：
1. RSS フィード（`<dc:creator>`）
2. ニコニコ静画 API
3. ユーザーページの og:title
4. `NICONICO_USER_NAME` 環境変数
5. ユーザーID（上記全て失敗時）

---

## テンプレート記法ガイド

### 1. 変数挿入

変数を `{{ 変数名 }}` の形式で挿入します：

```jinja2
{{ title }}
{{ video_url }}
```

### 2. フィルター（変数を加工）

変数の値を加工してから表示する場合は、フィルターを使用します：

#### 日付フォーマット

```jinja2
# 日付をフォーマット
{{ published_at | datetimeformat('%Y年%m月%d日') }}
# 結果: 2025年12月18日

# 日付と時刻をフォーマット
{{ published_at | datetimeformat('%Y年%m月%d日 %H:%M') }}
# 結果: 2025年12月18日 10:30

# 拡張時刻表示（24時以降30時までの時間表示に対応）
{{ "27:00" | extended_time }}           → "03:00"
{{ "27:00" | extended_time_display }}   → "翌日3時"

# 拡張日時範囲表示（推奨）
{{ format_extended_datetime_range(published_at | datetimeformat('%Y-%m-%d'), 27) }}
# 結果: 2025年12月21日27時(2025年12月22日(月)午前3時)
```



#### 文字列加工

```jinja2
# 文字列を大文字に
{{ title | upper }}
# 結果: NEW VIDEO TITLE

# 文字列を小文字に
{{ title | lower }}
# 結果: new video title
```

#### v3.2.0+ 新規フィルター・ヘルパー関数

```jinja2
# 現在の日付をフォーマット（v3.2.0+）
{{ current_date | format_date('%Y年%m月%d日') }}
# 結果: 2025年12月21日

# 現在の日時をフォーマット（v3.2.0+）
{{ current_datetime | format_datetime('%Y年%m月%d日 %H:%M') }}
# 結果: 2025年12月21日 14:30

# 曜日を日本語で表示（v3.2.0+）
{{ published_at | weekday }}
# 結果: 金曜日

# ランダム絵文字を挿入（v3.2.0+）
{{ | random_emoji }}
# 結果: 🎉 または 🚀 など（毎回異なる）

# 拡張日時範囲表示（24時以降30時まで対応、v3.2.0+）
{{ format_extended_datetime_range(published_at | datetimeformat('%Y-%m-%d'), 27) }}
# 結果: 2025年12月21日27時(2025年12月22日(月)午前3時)
```
- 上記例の末尾27を0～30の整数に変更することで、24時以降の任意の時間(25~30時)を指定できます。
- 30時以降は対応しないのでその点に注意してください。

**拡張日時範囲ヘルパー関数について:**
- 第1引数: 基準となる日付（`YYYY-MM-DD` 形式、`datetimeformat('%Y-%m-%d')` で生成）
- 第2引数: 拡張時刻（0～30の整数、24時以降の時間を指定）
- 戻り値: 「YYYY年MM月DD日HH時(YYYY年MM月DD日(曜日)period時)」形式の文字列
- 用途: 配信日時を拡張時刻表示する場合に推奨

### 3. 条件分岐

テンプレートで条件分岐を使用できます：

```jinja2
{% if "特定の単語" in title %}
このタイトルには「特定の単語」が含まれています
{% else %}
他のタイトルです
{% endif %}
```

**実装例:**
```jinja2
{% if "Live" in title %}
🔴 配信中！
{{ title }}
{% else %}
🎬 新作動画
{{ title }}
{% endif %}
```

---

## 実装例

### 【YouTube新着動画テンプレート実装例】

シンプル版：
```jinja2
🎬 {{ title }}
チャンネル: {{ channel_name }}
公開日: {{ published_at | datetimeformat('%Y年%m月%d日') }}
{{ video_url }}

#YouTube #新作動画
```

拡張版（フィルター・フォーマット使用）：
```jinja2
🎬 新作動画投稿！

【 {{ title }} 】

チャンネル: {{ channel_name }}
公開日: {{ published_at | datetimeformat('%Y年%m月%d日') }} ({{ published_at | weekday }})
投稿時刻: {{ current_datetime | format_datetime('%H:%M') }}

{{ | random_emoji }} 是非ご覧ください！
{{ video_url }}

#YouTube #{{ channel_name | replace(' ', '') }}
```

**出力例:**
```
🎬 新作動画投稿！

【 【新企画】Bluesky自動投稿ツール紹介 】

チャンネル: mayuneco
公開日: 2025年12月18日 (木曜日)
投稿時刻: 14:30

🚀 是非ご覧ください！
https://www.youtube.com/watch?v=xxxx

#YouTube #mayuneco
```

### 【YouTube配信開始テンプレート実装例】

```jinja2
🔴 配信開始！

{{ title }}
配信者: {{ channel_name }}
開始時刻: {{ current_datetime | format_datetime('%H:%M') }}

視聴: {{ video_url }}

#YouTube配信 #YouTubeGaming
```

### 【ニコニコ新着動画テンプレート実装例】

```jinja2
新作投稿！

{{ title }}
投稿者: {{ channel_name }}
投稿日: {{ published_at | datetimeformat('%Y年%m月%d日') }}
{{ video_url }}

#ニコニコ動画 #{{ channel_name | replace(' ', '') }}
```

### 【YouTube アーカイブテンプレート実装例】

基本版：
```jinja2
📹 ライブアーカイブ公開！

{{ title }}
配信者: {{ channel_name }}
配信日: {{ published_at | datetimeformat('%Y年%m月%d日') }}

視聴: {{ video_url }}

#YouTubeアーカイブ #見逃し配信
```

拡張時刻対応版（推奨）：
```jinja2
📹 {{ channel_name }} のアーカイブ

YouTube Live のアーカイブが公開されました！

🎬 タイトル: {{ title }}

📺 視聴: {{ video_url }}

配信日時: {{ format_extended_datetime_range(published_at | datetimeformat('%Y-%m-%d'), 27) }}  JST

#YouTubeLive #アーカイブ
```

**出力例:**
```
📹 mayuneco のアーカイブ

YouTube Live のアーカイブが公開されました！

🎬 タイトル: 【深夜配信】プロダクト開発の舞台裏

📺 視聴: https://www.youtube.com/watch?v=xxxx

配信日時: 2025年12月21日27時(2025年12月22日(月)午前3時)  JST

#YouTubeLive #アーカイブ
```

---

## トラブルシューティング

### Q: テンプレートが反映されない

**A:** 以下を確認してください：

1. **ファイルが保存されているか**
   - `v3/templates/youtube/yt_new_video_template.txt` が存在するか確認

2. **settings.env で正しく設定されているか**
   ```env
   TEMPLATE_YOUTUBE_NEW_VIDEO_PATH=templates/youtube/yt_new_video_template.txt
   TEMPLATE_NICO_NEW_VIDEO_PATH=templates/niconico/nico_new_video_template.txt
   ```

3. **アプリケーションを再起動したか**
   - テンプレート機能は起動時に読み込まれるため、アプリを再起動してください

4. **ログを確認する**
   - `v3/logs/app.log` を確認
   - `✅ テンプレートを使用して本文を生成しました` というメッセージを検索

### Q: テンプレート内で改行を使いたい

**A:** Markdown 形式で改行してください：

```jinja2
タイトル: {{ title }}

動画URL: {{ video_url }}

視聴よろしくお願いします！
```

### Q: テンプレートに絵文字を使いたい

**A:** テンプレートファイルをテキストエディタで編集し、絵文字をそのまま入力してください：

```jinja2
🎬 {{ title }}
{{ video_url }}
#YouTube
```

### Q: 複数の異なるテンプレートを使い分けたい

**A:** v3.1.0 では、プラットフォームごと（YouTube、ニコニコ）に 1 つのテンプレートを使用します。

同じプラットフォーム内で複数テンプレートを切り替えたい場合は、v3.2.0+ で実装予定です。

### Q: デフォルトテンプレートに戻したい

**A:** 以下の方法があります：

1. **テンプレートファイルを削除する**
   - `v3/templates/youtube/yt_new_video_template.txt` を削除
   - アプリを再起動すると、デフォルトフォーマットが使用されます

2. **settings.env で無効化する**
   ```env
   # この行をコメントアウト
   # TEMPLATE_YOUTUBE_NEW_VIDEO_PATH=templates/youtube/yt_new_video_template.txt
   ```

### Q: テンプレート構文エラーが発生する

**ログの確認:**
```
❌ テンプレート構文エラー: line 5, column 18: unexpected 'end of statement'
```

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

## 関連ドキュメント

- [テンプレートシステム 技術ガイド](../Technical/TEMPLATE_SYSTEM.md) - テンプレートシステムの技術仕様

---

**作成日**: 2025-12-21
**ステータス**: ✅ 実装完了・検証済み
