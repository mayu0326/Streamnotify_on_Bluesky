# StreamNotify on Bluesky v3 - クイックスタートガイド

**対象バージョン**: v3.1.0+
**最終更新**: 2025-12-21
**ステータス**: ✅ 実装完了

---

## 📖 このガイドについて

このドキュメントは、**初めてのユーザー向け**のクイックスタートガイドです。

最小限の設定で、**5分以内にアプリケーションを動かす**ことを目標にしています。

---

## 🎯 必須な4つのステップ

### ステップ 1: 必須情報を準備（5分）

アプリを起動する前に、以下の4つを準備してください：

| 項目 | 説明 | 確認方法 |
|:--|:--|:--|
| **YouTube チャンネル ID** | `UC` から始まる24文字 | [YOUTUBE_SETUP_GUIDE.md](./YOUTUBE_SETUP_GUIDE.md) 参照 |
| **Bluesky ハンドル** | `yourname.bsky.social` 形式 | Bluesky アプリから確認 |
| **Bluesky アプリパスワード** | Bluesky の設定画面で生成 | [BLUESKY_SETUP_GUIDE.md](./BLUESKY_SETUP_GUIDE.md) 参照 |
| **Python 3.10+** | インストール済みか確認 | ターミナルで `python --version` |

---

### ステップ 2: ファイルをダウンロード（1分）

```bash
# リポジトリをクローン
git clone https://github.com/mayu0326/Streamnotify_on_Bluesky.git
cd Streamnotify_on_Bluesky/v3
```

---

### ステップ 3: 設定ファイルを作成（2分）

```bash
# settings.env.example をコピー
cp settings.env.example settings.env
```

テキストエディタで `settings.env` を開き、以下の4項目を入力：

```env
# 必須設定（これだけで動きます）
YOUTUBE_CHANNEL_ID=UC開始の24文字コード
BLUESKY_USERNAME=yourname.bsky.social
BLUESKY_PASSWORD=アプリパスワード
POLL_INTERVAL_MINUTES=10

# その他（デフォルトのままでOK）
APP_MODE=selfpost
DEBUG_MODE=false
```

---

### ステップ 4: アプリを起動（1分）

```bash
# 仮想環境を作成・有効化
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate

# 依存パッケージをインストール
pip install -r requirements.txt

# アプリを起動
python main_v3.py
```

✅ **GUI ウィンドウが表示されたら成功です！**

---

## ✅ 起動後の動作確認

### 1️⃣ YouTube RSS が取得されているか確認

```
GUI の「動画一覧」に動画が表示されているか？
↓
【YES】→ ✅ 成功、ステップ2へ
【NO】 → 『トラブルシューティング』を参照
```

### 2️⃣ Bluesky に投稿できるか確認

```
1. 動画を1つ選択
2. 「投稿テスト」ボタンをクリック
3. ログウィンドウに「✅ 投稿テスト成功」と表示
↓
【表示された】→ ✅ 成功、本投稿へ
【表示されない】→ 『トラブルシューティング』を参照
```

### 3️⃣ 本投稿を実行

```
1. 投稿したい動画を選択
2. 「投稿実行」ボタンをクリック
3. Bluesky 上に投稿が表示される
```

✅ **おめでとうございます！基本的な機能は動作しています。**

---

## 🎓 次のステップ

### 初心者向け（基本操作を学ぶ）

1. [GUI_USER_MANUAL.md](./GUI_USER_MANUAL.md) - GUIの各機能を理解
2. [BLUESKY_SETUP_GUIDE.md](./BLUESKY_SETUP_GUIDE.md) - Bluesky認証を完全理解
3. [SETTINGS_OVERVIEW.md](./SETTINGS_OVERVIEW.md) - 設定項目を確認

### 中級者向け（テンプレート・フィルタを活用）

1. [TEMPLATE_SYSTEM.md](../Technical/TEMPLATE_SYSTEM.md) - テンプレートのカスタマイズ
2. [GUI_FILTER_AND_DUPLICATE_PREVENTION.md](../Technical/GUI_FILTER_AND_DUPLICATE_PREVENTION.md) - フィルタ機能

### 上級者向け（自動投稿・複数プラットフォーム）

1. [OPERATION_MODES_GUIDE.md](./OPERATION_MODES_GUIDE.md) - 動作モード（自動投稿など）
2. [YOUTUBE_SETUP_GUIDE.md](./YOUTUBE_SETUP_GUIDE.md) - YouTube API連携
3. [NICONICO_SETUP_GUIDE.md](./NICONICO_SETUP_GUIDE.md) - ニコニコ連携

---

## 🐛 よくある問題と対応

### ❌ 「RSS が取得できない」

**原因**: YouTube チャンネル ID が間違っている、または YouTube が一時的に無応答

**対応**:
1. チャンネル ID が `UC` で始まっているか確認 ([YOUTUBE_SETUP_GUIDE.md](./YOUTUBE_SETUP_GUIDE.md) 参照)
2. 5分待ってから再度試す
3. ログで詳細を確認 → [DEBUG_DRY_RUN_GUIDE.md](../Technical/DEBUG_DRY_RUN_GUIDE.md)

### ❌ 「Bluesky に投稿できない」

**原因**: アプリパスワードが間違っている、または Bluesky が一時的に無応答

**対応**:
1. Bluesky アプリパスワードが正しいか確認 ([BLUESKY_SETUP_GUIDE.md](./BLUESKY_SETUP_GUIDE.md) 参照)
2. アプリパスワードを再生成
3. `settings.env` を編集して再度試す

### ❌ 「GUI が起動しない」

**原因**: Python バージョンが古い、または依存パッケージが不足

**対応**:
1. `python --version` を実行、3.10+ を確認
2. `pip install -r requirements.txt` を再実行
3. [INSTALLATION_SETUP.md](./INSTALLATION_SETUP.md) を参照

---

## 📋 チェックリスト

起動までのチェック：

- [ ] Python 3.10+ がインストールされている
- [ ] YouTube チャンネル ID (UC形式) を確認した
- [ ] Bluesky アプリパスワードを生成した
- [ ] `settings.env` に4項目を入力した
- [ ] `pip install -r requirements.txt` を実行した
- [ ] `python main_v3.py` でアプリが起動した
- [ ] YouTube RSS が取得された（動画が表示された）
- [ ] 「投稿テスト」で正常完了した

全てチェック出来たら、準備完了です！ 🎉

---

## 💡 便利な機能（参考）

| 機能 | 説明 | ドキュメント |
|:--|:--|:--|
| **投稿テスト（DRY RUN）** | 投稿をシミュレーション（実際には投稿しない） | [DEBUG_DRY_RUN_GUIDE.md](..//Technical/DEBUG_DRY_RUN_GUIDE.md) |
| **フィルタ検索** | 大量の動画から素早く見つける | [GUI_USER_MANUAL.md](./GUI_USER_MANUAL.md) |
| **重複投稿防止** | 誤った再投稿を防止 | [GUI_USER_MANUAL.md](./GUI_USER_MANUAL.md) |
| **テンプレート** | 投稿フォーマットをカスタマイズ | [TEMPLATE_SYSTEM.md](../Technical/TEMPLATE_SYSTEM.md) |

---

## 📞 さらに詳しく

より詳細な情報が必要な場合：

- **インストール詳細**: [INSTALLATION_SETUP.md](./INSTALLATION_SETUP.md)
- **トラブルシューティング**: [FAQ_TROUBLESHOOTING_BASIC.md](./FAQ_TROUBLESHOOTING_BASIC.md)
- **操作方法**: [GUI_USER_MANUAL.md](./GUI_USER_MANUAL.md)
- **ドキュメント一覧**: [README](../../../README.md)

---

**準備ができたら、[GUI_USER_MANUAL.md](./GUI_USER_MANUAL.md) へ進んでください！**

**最終更新**: 2025-12-21
