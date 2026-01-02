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
- **チャンネル ID**（必須）: 固有の識別子。`UC` で始まる24文字の英数字。
- **チャンネル名**: ユーザーが設定する名前。例: `My Channel`。

### カスタム URL との違い
- **カスタム URL**: `@` で始まるユーザー名形式。例: `@MyYouTubeChannel`
- **ニックネーム**: `@` で始まるユーザー名形式。例: `@MyYouTubeChannel`
- **チャンネル ID** は `カスタム URL` や`ニックネーム`とは異なるものです。

### 注意点
- プラグイン未導入時はチャンネル ID のみ対応します。  \
プラグイン導入時はハンドル名、カスタムIDが使用可能ですが、APIリクエストによる変換が必要なので  \
基本的にはチャンネル ID の使用を推奨します。

---

## 🔴 方法 1: YouTube で確認（最も簡単）

### 手順

**Step 1: YouTube にアクセス**

```
1. YouTube を開く
   https://youtube.com/

2. Google アカウントでログイン（チャンネル所有者のアカウント）
```

**Step 2: チャンネルメニューを開く**

```
1. 左上の「ユーザーアイコン」をクリック
2. 「設定」をクリック
3.　「アカウントタブ」YouTube チャンネル項目のチャンネル欄を見つける
4. 「詳細設定を表示」をクリック
5. チャンネル ID が表示される
```
---

# 🟡 方法 2: YouTube Data API から確認

### 概要

YouTube Data API を使用して、チャンネル情報を取得することもできます。

⚠️ **注意**: この方法は上級ユーザー向けです。通常は方法 1 で取得できます。

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

### 入力例(プラグイン無しの場合)

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

**現在のバージョン（v3.3.0）では、1つのチャンネルのみ対応**です。

複数チャンネルを監視したい場合は、以下の方法があります：

#### アプリを複数起動（推奨）

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

---

## 🎯 YouTube API キーの設定（オプション）

### API キーが必要な場合

YouTube API キーを設定すると、以下が可能になります：

```
✅ @ で始まるカスタム URL でチャンネルを指定
✅ チャンネル情報の詳細取得
✅ ライブ配信の自動判定精度向上
✅ API リクエストの削減（情報のキャッシュ）
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
2. 設定 → アカウント → 詳細設定
3. チャンネル URL をコピー
```

### チャンネルがカスタム URL やハンドルを使用している場合
- プラグインを導入するか、上記の方法でチャンネル ID を取得してください。

```
例: https://www.youtube.com/@MyChannel

この場合:
✗ @MyChannel は使用できません
✗ @handle も使用できません
✓ 必ず /channel/UC... の形式に変換してください

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
