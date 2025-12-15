# YouTube → Bluesky Notifier (v1)

特定の YouTube チャンネルの新着動画を検知し、指定した Bluesky アカウントに自動投稿する常駐ボットです。

## 機能概要

- YouTube チャンネル 1 件の新着動画を RSS で監視
- 新着動画情報をローカル DB（SQLite）に保存
- 未投稿動画を Bluesky に自動投稿（テンプレート対応）
- 投稿履歴を CSV に記録

## 動作環境

- **OS**
  - Windows 10 以降
  - Debian/Ubuntu 系 Linux
- **必要ソフトウェア**
  - Python 3.10 以上
- **データベース**
  - SQLite（標準ライブラリ `sqlite3` を使用）

## インストール

```bash
git clone <このリポジトリのURL>
cd <リポジトリディレクトリ>

# 仮想環境の作成（任意だが推奨）
python -m venv venv

# Windows
venv\Scripts\activate

# Linux / WSL
source venv/bin/activate

pip install -r requirements.txt
```

## 設定

1. `settings.env.example` をコピーして `.env` を作成します。

```bash
# Windows (PowerShell)
Copy-Item settings.env.example .env

# Linux / WSL
cp settings.env.example .env
```

2. `.env` を編集し、次の項目を設定します。
※下記は最低限設定が必要な項目です。他のオプションの説明は、
`.env` 内のコメントを参照してください。

- `BLUESKY_USERNAME`
  - Bluesky のハンドル名
- `BLUESKY_PASSWORD`
  - Bluesky のアプリパスワード
- `YOUTUBE_CHANNEL_ID`
  - 監視対象の YouTube チャンネル ID
- `POLL_INTERVAL_MINUTES`
  - RSS をポーリングする間隔

> ⚠️ **注意**: `.env` には個人の ID やパスワードを記載するため、
公開リポジトリには含めないでください。

### 基本的な起動方法

```bash
# 仮想環境を有効にした状態で
python main_v1.py
```

### 動作の流れ

- 起動中は `POLL_INTERVAL_MINUTES` ごとに YouTube RSS を取得し、新着動画を検知します。
- 新着動画は `data/youtube_notify.db` に保存されます。
- `BLUESKY_POST_ENABLED=true` の場合Bluesky へ自動投稿されます。
- Bluesky への投稿履歴は `logs/post_history.csv` に追記されます。
- アプリケーションログは `logs/app.log` に記録されます。

### 停止方法

停止する場合は、ターミナルで `Ctrl + C` を押してください。

## ディレクトリ構成

```
.
├── main_v1.py              # アプリケーションのエントリポイント
├── config.py               # 設定読み込み・バリデーション
├── database.py             # SQLite 操作（動画データの保存・取得）
├── youtube_rss.py          # YouTube RSS の取得・パース
├── bluesky_plugin.py       # Bluesky への投稿処理
├── bluesky_v1.py           # Bluesky 投稿処理とテンプレート処理
├── utils_v1.py             # ユーティリティ関数
├── settings.env.example    # 設定ファイルのサンプル
├── .env      　　　　       # 設定ファイル（要作成、Git管理外）
├── app_version.py          # アプリケーションバージョン情報
├── data/                   # SQLite DB ファイル（youtube_notify.db）
├── logs/                   # 投稿履歴 CSV, アプリケーションログ
│   ├── post_history.csv
│   └── app.log
└── docs/                   # 設計ドキュメント
```

## 制限事項

### RSS方式の制限
- YouTubeの仕様により、RSSで取得可能な動画は通常動画のみです。限定公開、非公開動画は含みません。
- 初回起動後の初回取得で取得されるのは、本アプリ導入以前に公開された通常動画１０本です。
それ以上の過去動画の遡及取得はRSSでは取得出来ません。

### プラグイン未導入時の制限

- 監視対象にできるチャンネルはYouTube限定、かつUCから始まるチャンネルIDのみです。

### YouTubeAPI連携プラグイン未導入時は以下の機能を利用できません。
- ライブ配信・動画、プレミア公開、ショート動画、アーカイブの判別
- 動画の詳細情報取得（再生回数、高評価数、公開日時など）
- UCから始まらないチャンネルIDの監視設定

### サイト連携プラグイン未導入の場合、下記サービスは非対応となります。
  - Twitch
  - ニコニコ動画/生放送

### 機能拡張プラグイン未導入の場合、以下の機能は非対応となります。
  - Discord 通知
  - 詳細なログ設定
  - 投稿への画像添付
  - Docker対応
  - トンネル連携
  - データベース連携
  - テーマ設定(ダークモード)

## ライセンス

本アプリケーションは **GPL License v2** で提供されます。

## 開発・貢献

- **作者**: まゆにゃ（@mayu0326）
- Issue / PR 歓迎です

## トラブルシューティング

### Python のバージョンが古い
Python 3.10 以上が必要です。`python --version` で確認してください。

### モジュールのインポートエラー
仮想環境が有効になっているか確認し、`pip install -r requirements.txt` を再実行してください。

### YouTube RSS が取得できない
- YouTubeのサーバーエラーが発生していないか確認してください。
- インターネット接続を確認してください。
- チャンネルIDがUCから始まっているか確認してください。

### Bluesky に投稿できない
- `BLUESKY_POST_ENABLED=true` が設定されているか確認してください。
- ユーザー名とアプリパスワードが正しいか確認してください。
- Bluesky のアプリパスワードは、Web 版設定画面から生成する必要があります。

### 投稿が実行されない
- `BLUESKY_POST_ENABLED` が有効になっているか確認してください。
- ログファイル（`logs/app.log`）を確認して、エラーメッセージがないか確認してください。
- 動作モードが通常モード/自動投稿モードになっているか確認してください。
（ドライランモード・蓄積モードでは投稿されません）

### タイムゾーンがおかしい
- `TIMEZONE` 設定を確認してください。
- 日本の場合は `TIMEZONE=Asia/Tokyo` を設定してください。
- `system` に設定すると、システムのタイムゾーンが使用されます。
