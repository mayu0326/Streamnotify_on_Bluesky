# インストール・セットアップガイド

**対象バージョン**: v3.3.0+
**最終更新**: 2026-01-07
**ステータス**: ✅ 実装完了

---

## 📖 このガイドについて

このドキュメントは、**StreamNotify をインストール・セットアップする詳細な手順**を説明します。

**対象**: 初心者ユーザー、OSが異なるユーザー向け

---

## 🎯 必要な環境

### システム要件

| 項目 | 要件 |
|:--|:--|
| **OS** | Windows 10以降 / Linux（Debian/Ubuntu等） |
| **Python** | 3.10 以上（3.11+ 推奨） |
| **メモリ** | 最小 512MB（推奨 1GB以上） |
| **ディスク容量** | 100MB以上の空き容量 |
| **インターネット接続** | 必須 |

### 必須アカウント

| サービス | 必須か | 説明 |
|:--|:--|:--|
| **YouTube** | ✅ 必須 | チャンネル ID 必要 |
| **Bluesky** | ✅ 必須 | ハンドル・アプリパスワード必要 |
| **GitHub** | ○ 不要 | ソースコード取得時のみ |

---

## 🎯 ステップ 1: Python をインストール

### Windows ユーザー向け

#### 方法 A: Python.org から直接ダウンロード（推奨）

1. **Python 公式サイトにアクセス**
   ```
   https://www.python.org/downloads/
   ```

2. **Python 3.11 をダウンロード**
   ```
   「Download Python 3.11.x」をクリック
   ```

3. **インストーラを実行**
   ```
   ダウンロードしたファイルをダブルクリック
   ```

4. **セットアップウィザード**
   ```
   ☑ Add Python 3.11 to PATH
   ↓
   「Install Now」をクリック
   ```

5. **確認**
   ```bash
   python --version
   # Python 3.11.x が表示されたら成功
   ```

#### 方法 B: Microsoft Store から（簡単）

```
1. Microsoft Store アプリを開く
2. 「Python」で検索
3. 「Python 3.11」をクリック
4. 「入手」をクリック
5. インストール完了を待つ
```

---

### Linux ユーザー向け（Debian/Ubuntu）

```bash
# パッケージリストを更新
sudo apt-get update

# Python 3.10+ をインストール
sudo apt-get install -y python3 python3-venv python3-pip

# 確認
python3 --version
```

### Linux ユーザー向け（CentOS/RHEL）

```bash
# Python 3.10+ をインストール
sudo yum install -y python3 python3-venv python3-pip

# 確認
python3 --version
```

---

## 🎯 ステップ 2: リポジトリをクローン

### Git を使用する場合（推奨）

```bash
# リポジトリをクローン
git clone https://github.com/mayu0326/Streamnotify_on_Bluesky.git
# ディレクトリに移動
cd Streamnotify_on_Bluesky/v3
```

### ZIP ファイルをダウンロードする場合

```
1. リポジトリページ https://github.com/mayu0326/Streamnotify_on_Bluesky にアクセス
2. 「Code」 → 「Download ZIP」をクリック
3. ZIP ファイルを解凍
4. cd Streamnotify_on_Bluesky-main/v3
```

---

## 🎯 ステップ 3: 仮想環境を作成

**仮想環境**により、他の Python プロジェクトとの依存関係の競合を防ぎます。

### Windows ユーザー向け

```bash
# 仮想環境を作成
python -m venv venv

# 仮想環境を有効化
venv\Scripts\activate

# 有効化されたか確認
# コマンドプロンプトの先頭に「(venv)」が表示されたら成功
(venv) C:\Users\YourName\...>
```

### Linux ユーザー向け

```bash
# 仮想環境を作成
python3 -m venv venv

# 仮想環境を有効化
source venv/bin/activate

# 有効化されたか確認
# ターミナルの先頭に「(venv)」が表示されたら成功
(venv) $
```

### 仮想環境を無効化する場合

```bash
# どの OS でも共通
deactivate
```

---

## 🎯 ステップ 4: 依存パッケージをインストール

**仮想環境が有効になっていることを確認してから実行してください。**

```bash
# pip を最新版に更新
pip install --upgrade pip

# requirements.txt から全パッケージをインストール
pip install -r requirements.txt
```

### インストール内容

```
以下のパッケージがインストールされます：

- atproto: Bluesky API クライアント
- feedparser: RSS フィード解析
- requests: HTTP クライアント
- Pillow: 画像処理
- beautifulsoup4: HTML/XML 解析
- python-dotenv: .env ファイル読み込み
```

### インストール確認

```bash
# インストール済みパッケージを確認
pip list

# 特定パッケージのバージョンを確認
pip show atproto
```

---

## 🎯 ステップ 5: 設定ファイルを作成

### settings.env を作成

```bash
# settings.env.example をコピー
cp settings.env.example settings.env

# テキストエディタで開く
# Windows: notepad settings.env
# macOS: nano settings.env
# Linux: vi settings.env
```

### settings.env に必須項目を入力

テキストエディタで以下を設定：

```env
# ========================================
# 必須設定（これだけは入力必須）
# ========================================

# YouTube チャンネル ID（UC で始まる24文字）
YOUTUBE_CHANNEL_ID=UCxxxxxxxxxxxxxxxxxx

# Bluesky ハンドル（@を除く）
BLUESKY_USERNAME=yourname.bsky.social

# Bluesky アプリパスワード
BLUESKY_PASSWORD=xxxx-xxxx-xxxx-xxxx

# ポーリング間隔（分）
POLL_INTERVAL_MINUTES=10

# ========================================
# 基本設定（デフォルトのままでOK）
# ========================================

APP_MODE=selfpost
DEBUG_MODE=false
BLUESKY_POST_ENABLED=True
TIMEZONE=system

# その他はコメントアウトしたままでOK
```

### 設定値の確認

| 項目 | 値 | 参照 |
|:--|:--|:--|
| `YOUTUBE_CHANNEL_ID` | `UC` で始まる24文字 | [YOUTUBE_SETUP_GUIDE.md](./YOUTUBE_SETUP_GUIDE.md) |
| `BLUESKY_USERNAME` | Bluesky ハンドル（@除く） | [BLUESKY_SETUP_GUIDE.md](./BLUESKY_SETUP_GUIDE.md) |
| `BLUESKY_PASSWORD` | アプリパスワード | [BLUESKY_SETUP_GUIDE.md](./BLUESKY_SETUP_GUIDE.md) |

---

## 🎯 ステップ 6: 初回実行テスト

### アプリケーションを起動

```bash
# 仮想環境が有効か確認
# (仮想環境) $ という形式で実行

# アプリを起動
python main_v3.py
```

### 起動時の動作確認

```
期待される出力:
[2025-12-21 14:30:00] INFO ✅ Bluesky にログインしました
[2025-12-21 14:30:01] INFO 📦 プラグインを読み込んでいます
[2025-12-21 14:30:02] INFO 📊 GUI を起動しています

GUI ウィンドウが開く
```

### エラーが出た場合

```
以下を確認:
1. Python バージョン: python --version
2. pip パッケージ: pip list
3. 設定ファイル: cat settings.env
4. ログファイル: cat logs/app.log
```

---

## 🐛 インストール時のよくあるエラー

### ❌ 「command not found: python」

**原因**: Python がインストールされていない、または PATH に追加されていない

**対応**:
```bash
python3 --version  # python3 を試す
# または Python を再インストール（ステップ 1 参照）
```

### ❌ 「No module named 'pip'」

**原因**: pip がインストールされていない

**対応**:
```bash
# Python とともに pip を再インストール
python -m ensurepip --upgrade
```

### ❌ 「Permission denied」（Mac/Linux）

**原因**: ディレクトリ権限がない

**対応**:
```bash
sudo chown -R $USER:$USER ./
```

### ❌ 「requirements.txt not found」

**原因**: 正しいディレクトリにいない

**対応**:
```bash
# v3 ディレクトリにいることを確認
pwd  # 現在のディレクトリを表示
cd v3  # v3 に移動
```

---

## ✅ セットアップ完了チェック

インストール後、以下を確認してください：

```
セットアップ完了確認リスト:

☑ Python 3.10+ がインストールされている
  確認: python --version

☑ 仮想環境が作成されている
  確認: ls venv/ (または dir venv)

☑ 依存パッケージがインストールされている
  確認: pip list | grep atproto

☑ settings.env が作成されている
  確認: cat settings.env

☑ 必須4項目が入力されている
  確認: grep YOUTUBE_CHANNEL_ID settings.env

☑ アプリが起動する
  確認: python main_v3.py → GUI が表示される

☑ YouTube RSS が取得される
  確認: GUI の「動画一覧」に動画が表示される

☑ Bluesky 投稿テストが成功する
  確認: 動画を選択 → [投稿テスト] → ログに ✅

全てのチェックが完了したら、セットアップ完了です！🎉
```

---

## 📞 トラブルシューティング

より詳細なトラブルシューティングは：

- [GETTING_STARTED.md](./GETTING_STARTED.md) - クイックスタート
- [FAQ_TROUBLESHOOTING_BASIC.md](./FAQ_TROUBLESHOOTING_BASIC.md) - よくある質問

---

## 🔄 日常的な使用方法

### アプリを起動する（毎回）

```bash
# 1. コマンドプロンプト/ターミナルを開く
# 2. StreamNotify ディレクトリに移動
cd Streamnotify_on_Bluesky/v3

# 3. 仮想環境を有効化
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 4. アプリを起動
python main_v3.py
```

### ショートカットを作成（Windows）

毎回コマンド入力するのが面倒な場合、バッチファイルを作成：

```bash
# run.bat ファイルを作成
@echo off
cd /d %~dp0
venv\Scripts\activate.bat
python main_v3.py
pause
```

このファイルをダブルクリックでアプリ起動

---

**セットアップが完了したら、[GETTING_STARTED.md](./GETTING_STARTED.md) へ進んでください！**

**最終更新**: 2025-12-21
