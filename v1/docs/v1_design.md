# v1 設計メモ（YouTube → Bluesky）

## 1. 目的
- 特定の YouTube チャンネルの新着動画を検知し、指定した Bluesky アカウントに自動投稿する常駐ボットを提供する。
- Windows 10 以降、および Debian/Ubuntu 系 Linux 上で、Python 3.10+ を用いて動作することを目標とする。

## 2. 対象範囲（スコープ）

### 2.1 v1 で実装する機能
- YouTube チャンネル 1 件の新着動画検知（RSS ベース）。
- 新着動画情報のローカル DB（SQLite）への保存。
- 未投稿動画の Bluesky への自動投稿（テンプレート対応、投稿履歴 CSV 出力）。
- ポーリング間隔（5〜30 分）のユーザー指定と常駐動作。

### 2.2 v1 では実装しない機能
- Twitch / ニコニコ 連携一式（配信開始・終了、動画投稿検知など）。
- YouTube Data API を用いた詳細取得や、ライブ／アーカイブ判定。
- GUI、Web UI、Docker、トンネル（Cloudflare/ngrok/Tailscale）、Discord 通知。

## 3. アーキテクチャ概要

### 3.1 コンポーネント
- 設定レイヤー（config）
  - `.env` から各種設定を読み込む。
  - `POLL_INTERVAL_MINUTES` のバリデーション（5〜30 分）。

- データ取得レイヤー（YouTube RSS）
  - `YOUTUBE_CHANNEL_ID` から RSS URL を生成。
  - RSS をポーリングして `video_id`, `title`, `published_at` を取得。

- ストレージレイヤー（SQLite）
  - `data/youtube_notify.db` を用意し、動画情報を保存。
  - `video_id` のユニーク制約で新着判定、`posted_to_bluesky` フラグで投稿済み管理。

- 通知レイヤー（Bluesky）
  - 既存の `BlueskyPoster.post_new_video()` をプラグイン的に利用。
  - DB の未投稿動画を `event_context` にマッピングして Bluesky に投稿。

- メインループ
  - 設定読み込み → DB 初期化 → 無限ループで以下を繰り返す：
    1. RSS 取得 → DB 更新
    2. DB から未投稿動画取得 → Bluesky 投稿 → フラグ更新
    3. ポーリング間隔分 sleep

### 3.2 将来拡張の方針
- YouTube 以外のサービス（Twitch, ニコニコ等）は「別プラグイン」として追加する。
- ライブ配信・アーカイブ判定、YouTube Data API 連携などは v2 以降の拡張とする。

### 3.3 ディレクトリ構成
```
.
├── main_v1.py              # アプリケーションのエントリポイント
├── config.py               # 設定読み込み・バリデーション
├── database.py             # SQLite 操作
├── youtube_rss.py          # YouTube RSS 取得・パース
├── bluesky_plugin.py       # Bluesky 投稿ラッパ
├── bluesky_v1.py           # Bluesky 投稿処理とテンプレート処理
├── utils_v1.py             # ユーティリティ関数
├── settings.env.example    # 設定ファイルのサンプル
├── .env　　　　             # 設定ファイル（要作成、Git管理外）
├── data/                   # SQLite DB ファイル
│   └── youtube_notify.db
├── logs/                   # 投稿履歴 CSV, アプリケーションログ
│   ├── post_history.csv
│   └── app.log
└── docs/                   # 設計ドキュメント
```

## 4. モジュール構成

- `config.py`
  - `.env` 読み込み、設定値オブジェクト化、バリデーション。

- `database.py`
  - SQLite 接続管理、テーブル作成、動画の INSERT / SELECT / UPDATE。

- `youtube_rss.py`
  - RSS URL 生成、取得、パース、DB への反映。

- `bluesky_plugin.py`
  - DB レコード → `event_context` 変換 → `BlueskyPoster.post_new_video()` 呼び出し。

- `main_v1.py`
  - アプリ起動エントリポイント。メインループと終了処理のみを担当。

- `bluesky_v1.py`
  - Bluesky 投稿処理とテンプレート処理の実装。
  - 画像アップロード、テンプレートレンダリング、投稿実行。

- `utils_v1.py`
  - ユーティリティ関数群（日時フォーマット、リトライ処理など）。

## 5. 設定と環境

### 5.1 設定ファイル
- 設定ファイル名: `.env`
- サンプルファイル: `settings.env.example`

### 5.2 必須設定項目
- `YOUTUBE_CHANNEL_ID` - 監視対象の YouTube チャンネル ID（UC から始まる ID）
- `BLUESKY_USERNAME` - Bluesky のハンドル名
- `BLUESKY_PASSWORD` - Bluesky のアプリパスワード
- `POLL_INTERVAL_MINUTES` - ポーリング間隔（最小値: 5、推奨: 10）

### 5.3 オプション設定項目
- `BLUESKY_POST_ENABLED` - Bluesky への投稿を有効にするか（true/false、デフォルト: false）
- `TIMEZONE` - タイムゾーン設定（例: Asia/Tokyo、デフォルト: system）

### 5.4 動作環境
- OS: Windows 10 以降 / Debian/Ubuntu 系 Linux。
- 言語: Python 3.10+
- DB: SQLite（標準ライブラリ `sqlite3` 使用）。

## 6. ライセンスと公開方針

- ライセンスはリポジトリ全体を GPL v2 とする（既存コードと同一）。
- 利用者固有の ID・パスワード・API キーは `.env` にのみ記載し、
公開リポジトリには含めない。
- README に、利用者が自分の ID を取得・設定する手順を簡潔に記載する。

## 7. 制限事項と既知の課題

### 7.1 RSS 方式の制限
- YouTube の仕様により、RSS で取得可能な動画は通常動画のみ（限定公開、非公開動画は含まない）。
- 初回起動後の初回取得で取得されるのは、本アプリ導入以前に公開された通常動画 10 本まで。
- それ以上の過去動画の遡及取得は RSS では不可能。

### 7.2 チャンネル ID の制限
- プラグイン未導入時は、UC から始まるチャンネル ID のみ監視可能。

### 7.3 YouTube API 連携プラグイン未導入時の制限
- ライブ配信・動画、プレミア公開、ショート動画、アーカイブの判別不可。
- 動画の詳細情報取得（再生回数、高評価数、公開日時など）不可。
- UC から始まらないチャンネル ID の監視設定不可。

### 7.4 その他のプラグイン未導入時の制限
- サイト連携プラグイン未導入: Twitch、ニコニコ動画/生放送は非対応。
- 機能拡張プラグイン未導入: Discord 通知、画像添付、Docker 対応、トンネル連携、データベース連携、テーマ設定（ダークモード）は非対応。

## 8. トラブルシューティング指針

### 8.1 YouTube RSS が取得できない場合
- YouTube サーバーエラーの確認。
- インターネット接続の確認。
- チャンネル ID が UC から始まっているか確認。

### 8.2 Bluesky に投稿できない場合
- `BLUESKY_POST_ENABLED=true` が設定されているか確認。
- ユーザー名とアプリパスワードが正しいか確認。
- Bluesky のアプリパスワードは、Web 版設定画面から生成する必要がある。

### 8.3 投稿が実行されない場合
- `BLUESKY_POST_ENABLED` が有効になっているか確認。
- ログファイル（`logs/app.log`）でエラーメッセージを確認。
- 動作モードが通常モード/自動投稿モードになっているか確認（ドライランモード・蓄積モードでは投稿されない）。

### 8.4 タイムゾーンの問題
- `TIMEZONE` 設定を確認（日本の場合は `Asia/Tokyo`）。
- `system` に設定すると、システムのタイムゾーンが使用される。
