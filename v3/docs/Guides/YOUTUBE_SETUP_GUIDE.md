# YouTube チャンネル ID 設定ガイド

**対象バージョン**: v3.1.0+
**最終更新**: 2025-12-21
**ステータス**: ✅ 実装完了

---

## 📖 このガイドについて

StreamNotify で YouTube チャンネルを監視するには、**YouTube チャンネル ID** が必須です。

このドキュメントでは、チャンネル ID を見つけて設定する方法を説明します。

**対象**: YouTube チャンネルを設定するユーザー向け

---

## 🎯 チャンネル ID とは

### チャンネル ID の形式

YouTube チャンネル ID は以下の形式です：

```
UC + 22文字のランダム文字列

【例】
UC1234567890ABCDEFGHIJKLmn
UC9_abcdefghij-KLMNOPQRSTUv
```

### チャンネル名との違い

混同しやすいので注意：

| 項目 | 形式 | 例 |
|:--|:--|:--|
| **チャンネル ID**（必須） | `UC` + 22文字 | `UC1234567890ABCDEFGHIJKLmn` |
| **カスタム URL**（使える場合） | `@` + ユーザー名 | `@MyYouTubeChannel` |
| **チャンネル名** | 日本語など | `My Cool Channel` |

---

## 🔴 方法 1: YouTube Studio で確認（最も簡単）

### 手順

**Step 1: YouTube Studio にアクセス**

```
1. YouTube Studio を開く
   https://studio.youtube.com/

2. Google アカウントでログイン（チャンネル所有者のアカウント）
```

**Step 2: チャンネルメニューを開く**

```
1. 左上の「ユーザーアイコン」をクリック
2. 「チャンネルを表示」をクリック
```

**Step 3: URL からチャンネル ID を抽出**

```
アドレスバーに表示される URL を確認：

https://www.youtube.com/channel/UC1234567890ABCDEFGHIJKLmn
                              ↑↑↑ ここがチャンネル ID

UC1234567890ABCDEFGHIJKLmn をコピー
```

### スクリーンショット（テキスト版）

```
┌─ YouTube Studio ──────────────────────────────┐
│                                               │
│ ┌─ ユーザーメニュー                           │
│ │ ☐ アカウント                               │
│ │ ☐ 作成ツール                               │
│ │ ✓ チャンネルを表示              ← クリック │
│ │ ☐ チャンネル設定                           │
│ │ ☐ ログアウト                               │
│ │                                             │
│ └─────────────────────────────────────────────┘
│                                               │
│ ページ遷移:                                   │
│ アドレスバー:                                 │
│ https://www.youtube.com/channel/UC1234...   │
│                              ↓               │
│ チャンネル ID: UC1234567890ABCDEFGHIJKLmn   │
│                                               │
└───────────────────────────────────────────────┘
```

---

## 🟠 方法 2: YouTube チャンネルページから確認

### 手順

**Step 1: チャンネルページを開く**

```
1. YouTube にアクセス
   https://www.youtube.com/

2. 「ユーザーアイコン」をクリック

3. 「チャンネルを表示」をクリック
```

**Step 2: ページソースを表示**

```
1. ブラウザの右クリックメニューを開く
   → 「ページのソースを表示」（または F12）

2. Ctrl+F（Windows）/ Cmd+F（Mac）で検索
   → 「"channelId":"」 で検索

3. 検索結果から チャンネル ID を抽出

例）
"channelId":"UC1234567890ABCDEFGHIJKLmn"
```

### トラブル時の代替方法

ページソースが複雑な場合：

```
1. YouTube チャンネルページを開く
2. アドレスバーの URL を確認
   https://www.youtube.com/channel/UC1234...

3. /channel/ の後の部分がチャンネル ID
   UC1234567890ABCDEFGHIJKLmn
```

---

## 🟡 方法 3: YouTube Data API から確認

### 概要

YouTube Data API を使用して、チャンネル情報を取得することもできます。

⚠️ **注意**: この方法は上級ユーザー向けです。通常は方法 1 または 2 で十分です。

### 手順

**Step 1: API キーを取得**

```
1. Google Cloud Console を開く
   https://console.cloud.google.com/

2. 新しいプロジェクトを作成
   - プロジェクト名: 「YouTube Monitor」など

3. YouTube Data API v3 を有効化
   - 「API とサービス」 → 「ライブラリ」
   - 「YouTube Data API v3」を検索
   - 「有効化」をクリック

4. API キーを作成
   - 「認証情報」 → 「キーを作成」
   - 「API キー」を選択
```

**Step 2: Python で チャンネル ID を取得**

```python
import requests

# YouTube API キー（上記で取得）
API_KEY = "YOUR_API_KEY_HERE"

# チャンネル名で検索
channel_name = "My YouTube Channel"

url = "https://www.googleapis.com/youtube/v3/search"
params = {
    "part": "snippet",
    "q": channel_name,
    "type": "channel",
    "key": API_KEY
}

response = requests.get(url, params=params)
data = response.json()

# チャンネル ID を抽出
if data["items"]:
    channel_id = data["items"][0]["id"]["channelId"]
    print(f"チャンネル ID: {channel_id}")
```

---

## 🟢 方法 4: オンラインツールを使用

### サイト 1: CJSchedule

```
1. https://www.cjschedule.com/ を開く

2. 「YouTube Channel ID」セクションを探す

3. チャンネル URL または チャンネル名を入力
   例: https://www.youtube.com/c/MyChannel

4. 「Get Channel ID」をクリック

5. チャンネル ID が表示される
```

### サイト 2: YouTube Channel ID Finder

```
1. オンラインで「YouTube Channel ID Finder」を検索

2. チャンネル URL を入力
   例: https://www.youtube.com/MyChannel

3. チャンネル ID が取得される
```

---

## ✅ チャンネル ID を設定

チャンネル ID が判明したら、settings.env に入力します。

### settings.env の編集

```bash
# テキストエディタで開く
# Windows: notepad settings.env
# macOS: nano settings.env
# Linux: vi settings.env
```

### 必須設定項目

```env
# ==========================================
# YouTube 設定（必須）
# ==========================================

# YouTube チャンネル ID（UC で始まる24文字）
# 【重要】@ から始まる URL は使用できません
YOUTUBE_CHANNEL_ID=UC1234567890ABCDEFGHIJKLmn
#                   ↑ 必ず UC で始まること

# ポーリング間隔（分単位）
# 最小値: 5、推奨値: 10、最大値: 60
POLL_INTERVAL_MINUTES=10
```

### 入力例

```env
# ✅ 正しい例
YOUTUBE_CHANNEL_ID=UC9_abcdefghij-KLMNOPQRSTUv

# ❌ 間違い: @ が含まれている
YOUTUBE_CHANNEL_ID=@MyYouTubeChannel

# ❌ 間違い: チャンネル名が入っている
YOUTUBE_CHANNEL_ID=My Cool Channel

# ❌ 間違い: URL が入っている
YOUTUBE_CHANNEL_ID=https://www.youtube.com/channel/UC1234...
```

---

## 🧪 設定の確認

### 設定が正しいか確認

```bash
# 1. settings.env が保存されているか確認
cat settings.env | grep YOUTUBE_CHANNEL_ID

# 出力例:
# YOUTUBE_CHANNEL_ID=UC1234567890ABCDEFGHIJKLmn

# 2. 形式が正しいか確認
# - UC で始まるか
# - 全角文字が含まれていないか
# - 空白がないか
```

### アプリで確認

```bash
1. アプリを起動
   python main_v3.py

2. ログで以下を確認
   ✅ YouTube チャンネル ID を認識しました: UC1234...
   ✅ RSS フィード取得開始

3. GUI の「動画一覧」に動画が表示される
   → 設定成功！
```

### ログの確認

```
【正常時のログ】
[2025-12-21 14:30:00] INFO ✅ YouTube チャンネル ID: UC1234567890ABCDEFGHIJKLmn
[2025-12-21 14:30:01] INFO 🔄 RSS フィード取得開始
[2025-12-21 14:30:02] INFO ✅ 動画 5 件を取得しました

【異常時のログ】
[2025-12-21 14:30:00] ERROR ❌ YouTube チャンネル ID が未設定です
[2025-12-21 14:30:01] ERROR ❌ RSS フィード取得失敗: チャンネル ID が無効です
```

---

## 📊 複数チャンネルを監視したい

### 注意

**現在のバージョン（v3.1.0）では、1つのチャンネルのみ対応**です。

複数チャンネルを監視したい場合は、以下の方法があります：

#### 方法 A: アプリを複数起動（推奨）

```
1. 別の フォルダで settings.env を分ける
2. チャンネル ID ごとに settings.env を管理
3. 各 settings.env でアプリを起動

【例】
フォルダ A: YOUTUBE_CHANNEL_ID=UC_ChannelA
フォルダ B: YOUTUBE_CHANNEL_ID=UC_ChannelB

起動方法:
Terminal 1: cd folder_a && python main_v3.py
Terminal 2: cd folder_b && python main_v3.py
```

#### 方法 B: 将来のバージョンを待つ

複数チャンネル対応は [FUTURE_ROADMAP_v3.md](../References/FUTURE_ROADMAP_v3.md) で計画中です。

---

## 🎯 YouTube API キーの設定（オプション）

### API キーが必要な場合

YouTube API キーを設定すると、以下が可能になります：

```
✅ @ で始まるカスタム URL でチャンネルを指定
✅ チャンネル情報の詳細取得
✅ ライブ配信の自動判定精度向上
✅ API リクエストの削減（キャッシング）
```

### API キーの設定方法

**Step 1: API キーを取得（前述の方法 3 参照）**

**Step 2: settings.env に設定**

```env
# YouTube Data API キー（オプション）
# 未設定の場合は RSS フィードのみで動作します
YOUTUBE_API_KEY=AIzaSyDxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### API キーのセキュリティ

```
⚠️ 注意: API キーは秘密鍵です

❌ GitHub に commit しない
❌ 公開リポジトリに push しない
❌ 他人に共有しない

✅ settings.env は .gitignore に追加
✅ ローカルマシンのみで管理
✅ 不正使用検知後は即座に再生成
```

---

## 🐛 よくあるエラー

### ❌ 「チャンネル ID が見つかりません」

**原因**: チャンネル ID の形式が正しくない

**対応**:
```
✓ UC で始まっているか確認
✓ 全角文字が含まれていないか確認
✓ 空白がないか確認
✓ settings.env を保存したか確認
```

### ❌ 「RSS フィード取得失敗」

**原因 1**: インターネット接続がない

```
対応: インターネット接続を確認
```

**原因 2**: チャンネル ID が無効

```
対応: YouTube Studio で正確なチャンネル ID を確認
```

**原因 3**: YouTube RSS が一時的に利用不可

```
対応: 1時間後に再試行（YouTube 側の問題の可能性）
```

### ❌ 「動画一覧が表示されない」

**原因**: チャンネルが非公開、または動画がない

```
対応:
1. チャンネルが公開されているか確認
2. 動画が1件以上あるか確認
3. チャンネル ID が正しいか確認
```

---

## 💡 トラブルシューティング

### チャンネル ID が不明な場合

```
以下のいずれかを試してください：

【方法】
1. YouTube にログイン
2. チャンネル設定 → 基本情報
3. チャンネル URL をコピー
   例: https://www.youtube.com/channel/UC1234...
4. /channel/ の後を抽出
```

### チャンネルがカスタム URL を使用している場合

```
例: https://www.youtube.com/@MyChannel

この場合:
✗ @MyChannel は使用できません
✓ 必ず /channel/UC... の形式に変換してください

変換方法:
1. 上記 URL にアクセス
2. ページソースから channelId を抽出
3. または YouTube Studio で確認
```

---

## ✅ セットアップ完了チェック

```
☑ YouTube チャンネル ID を確認した
   例: UC1234567890ABCDEFGHIJKLmn

☑ settings.env に入力した
   YOUTUBE_CHANNEL_ID=UC1234567890ABCDEFGHIJKLmn

☑ settings.env を保存した
   （テキストエディタで Ctrl+S）

☑ ファイルを確認した
   cat settings.env | grep YOUTUBE_CHANNEL_ID

☑ アプリを起動した
   python main_v3.py

☑ GUI に動画が表示された
   → セットアップ完了！🎉
```

---

## 📞 さらにサポートが必要な場合

以下のドキュメントを参照してください：

- [GETTING_STARTED.md](./GETTING_STARTED.md) - クイックスタート
- [INSTALLATION_SETUP.md](./INSTALLATION_SETUP.md) - インストールガイド
- [FAQ_TROUBLESHOOTING_BASIC.md](./FAQ_TROUBLESHOOTING_BASIC.md) - よくある質問

---

**最終更新**: 2025-12-21
