# v2 設計メモ（YouTube → Bluesky）

## 1. 目的
- 特定の YouTube チャンネルの新着動画を検知し、指定した Bluesky アカウントに自動投稿する常駐ボットを提供する。
- Windows 10 以降、および Debian/Ubuntu 系 Linux 上で、Python 3.10+ を用いて動作することを目標とする。

## 2. 対象範囲（スコープ）

### 2.1 v2 で実装する機能
- YouTube チャンネル 1 件の新着動画検知（RSS ベース）。
- 新着動画情報のローカル DB（SQLite）への保存。
- 未投稿動画の Bluesky への自動投稿（テンプレート対応、投稿ログ記録：app.log/post.log/post_error.log）。
- ポーリング間隔（5〜30 分）のユーザー指定と常駐動作。
- YouTube Data API を用いた詳細取得や、ライブ／アーカイブ判定。
- ニコニコ動画の新着動画検知（RSS ベース）。
- 統合ロギング（環境変数によるログレベル制御）。
- 画像管理・サムネイル再取得機能。
- GUI による動画選択・投稿管理。

### 2.2 v2 では実装しない機能
- Twitch 配信開始・終了検知と通知。
- 設定GUI Web UI（Tkinter GUI として実装済み）。
- トンネル（Cloudflare/ngrok/Tailscale） → 現在実装済み（トンネル通信プラグイン）。
- Discord 通知 → プラグインアーキテクチャとして設計中（今後対応予定）。

## 3. アーキテクチャ概要


### 3.1 コンポーネント
- 設定レイヤー（config）
  - `settings.env` から各種設定を読み込み、`DEBUG_MODE` や `APP_MODE` もサポート。
  - `POLL_INTERVAL_MINUTES` のバリデーション（5〜30 分）。

- データ取得レイヤー（YouTube RSS）
  - `YOUTUBE_CHANNEL_ID` から RSS URL を生成。
  - RSS をポーリングして `video_id`, `title`, `published_at` などを取得。

- ストレージレイヤー（SQLite）
  - `data/video_list.db` を用意し、動画情報を保存。
  - DBカラム拡張（`selected_for_post`, `scheduled_at`, `thumbnail_url`, `content_type`, `live_status`, `is_premiere`, `image_mode`, `image_filename` など）に対応。
  - `video_id` のユニーク制約で新着判定、`posted_to_bluesky` フラグで投稿済み管理。

- 通知レイヤー（Bluesky, プラグインアーキテクチャ対応）
  - `PluginManager` によるプラグイン自動ロード。
  - DB の未投稿動画を `bluesky_plugin.py` にマッピングして Bluesky へ投稿。
  - RichText（Facet）対応、URLリンク化、画像添付、DRY RUN（テスト投稿）機能あり。

- GUIレイヤー
  - Tkinterベースの統合GUI（動画選択・予約・投稿・ドライラン・統計表示）。
  - 動画の選択・予約・投稿はGUIから操作。

- メインループ
  - 設定読み込み → DB 初期化 → GUI起動 → 無限ループで以下を繰り返す：
    1. RSS 取得 → DB 更新
    2. DB から未投稿動画取得 → GUIで選択 → Bluesky投稿（プラグイン経由）→ フラグ更新
    3. ポーリング間隔分 sleep

### 3.2 将来拡張の方針
- YouTube 以外のサービス（Twitch）は「TwitchAPI連携プラグイン」として追加する。
- ライブ配信・アーカイブ判定、YouTube Data API 連携などは「YouTubeAPI連携プラグイン」による拡張とする。

### 3.2.1 プラグイン実装状況（v2.1以降）

#### ✅ 実装済みプラグイン

| プラグイン名 | ファイル | 機能 | 管理方式 |
|------------|---------|------|--------|
| **Bluesky 投稿プラグイン** | `plugins/bluesky_plugin.py` | Bluesky への投稿実装（画像添付対応） | 自動ロード |
| **YouTube API プラグイン** | `plugins/youtube_api_plugin.py` | チャンネルID解決、動画詳細取得、ライブ判定 | 自動ロード |
| **YouTube Live プラグイン** | `plugins/youtube_live_plugin.py` | YouTube ライブ/アーカイブ判定 | 自動ロード |
| **Niconico プラグイン** | `plugins/niconico_plugin.py` | ニコニコ動画 RSS 監視・通知 | 自動ロード |
| **ロギング設定プラグイン** | `plugins/logging_plugin.py` | 統合ロギング・ログレベル管理 | 自動ロード |

#### ⏳ 未実装プラグイン

| プラグイン名 | 予定機能 |
|------------|--------|
| **Twitch API プラグイン** | Twitch 配信開始・終了通知 |
| **Discord 通知プラグイン** | Discord へのメッセージ送信・通知 |
| **補助機能プラグイン** | 設定 GUI、ダークモード、マルチユーザー対応 |
| **PubSubHubbub プラグイン** | リアルタイム通知（RSS ポーリング の代替） |
| **データベース連携プラグイン** | PostgreSQL/MySQL サポート |

### 3.3 ディレクトリ構成
```
.
├── main_v2.py              # アプリケーションのエントリポイント
├── config.py               # 設定読み込み・バリデーション
├── database.py             # SQLite 操作
├── youtube_rss.py          # YouTube RSS 取得・パース
├── bluesky_core.py         # Bluesky HTTP API 本体（ログイン・投稿・Facet構築）
├── gui_v2.py               # GUI フレーム統合（動画選択・投稿・統計表示）
├── image_manager.py        # 画像ダウンロード・保存・リトライ
├── logging_config.py       # ロギング統合設定
├── plugin_interface.py     # NotificationPlugin 抽象基底クラス
├── plugin_manager.py       # プラグイン自動検出・読み込み・管理
├── utils_v2.py             # ユーティリティ関数
├── settings.env.example    # 設定ファイルのサンプル
├── settings.env            # 設定ファイル（要作成、Git管理外）
├── requirements.txt        # Python パッケージ依存関係
│
├── plugins/                # プラグインディレクトリ
│   ├── bluesky_plugin.py       # Bluesky 投稿プラグイン実装
│   ├── youtube_api_plugin.py   # YouTube Data API 連携プラグイン
│   ├── youtube_live_plugin.py  # YouTube ライブ/アーカイブ判定プラグイン
│   ├── niconico_plugin.py      # ニコニコ動画 RSS 監視プラグイン
│   └── logging_plugin.py       # ロギング統合管理プラグイン
│
├── thumbnails/            # サムネイル・画像処理モジュール
│   ├── __init__.py             # Niconico OGP URL 取得
│   ├── image_re_fetch_module.py # サムネイル再ダウンロード・DB更新
│   ├── niconico_ogp_utils.py   # Niconico OGP 取得ユーティリティ
│   ├── niconico_ogp_backfill.py # Niconico OGP バックフィル処理
│   ├── youtube_thumb_utils.py  # YouTube サムネイル取得ユーティリティ
│   └── youtube_thumb_backfill.py # YouTube サムネイルバックフィル処理
│
├── data/                   # データベース・キャッシュ
│   └── video_list.db           # SQLite データベース
│
├── logs/                   # ログファイル出力ディレクトリ
│   ├── app.log                 # アプリケーション一般ログ
│   ├── error.log               # エラーログ（バニラ）
│   ├── post.log                # Bluesky 投稿ログ（プラグイン導入時）
│   ├── post_error.log          # 投稿エラーログ（プラグイン導入時）
│   ├── audit.log               # 監査ログ（プラグイン導入時）
│   ├── gui.log                 # GUI 操作ログ（プラグイン導入時）
│   ├── thumbnails.log          # サムネイル処理ログ（プラグイン導入時）
│   ├── youtube.log             # YouTube 監視ログ（プラグイン導入時）
│   ├── niconico.log            # ニコニコ監視ログ（プラグイン導入時）
│   └── tunnel.log              # トンネル接続ログ（プラグイン導入時）
│
├── images/                 # 投稿用画像ディレクトリ
│   ├── default/
│   │   └── noimage.png         # デフォルト画像（画像未設定時）
│   ├── YouTube/                # YouTube 動画サムネイル保存先
│   ├── Niconico/               # ニコニコ動画サムネイル保存先
│   └── Twitch/                 # Twitch 放送画像保存先
│
├── templates/              # 投稿テンプレート（Jinja2 形式）
│   ├── youtube/
│   │   ├── yt_new_video_template.txt    # 新着動画投稿用
│   │   ├── yt_online_template.txt       # YouTube 配信開始用
│   │   └── yt_offline_template.txt      # YouTube 配信終了用
│   └── niconico/
│       └── nico_new_video_template.txt  # ニコニコ新着動画投稿用
│
├── Asset/                  # プラグイン用テンプレート・画像保管所
│   │                       # 全サービス・全プラグイン用テンプレート/画像を保管
│   │                       # プラグイン導入時に必要なファイルを本番ディレクトリに自動コピー
│   │                       # （asset_manager.py で実装完了: 2025-12）
│
├── docs/                   # 設計ドキュメント
│   ├── ARCHITECTURE_v2.md
│   ├── ModuleList_v2.md
│   ├── v2_design.md
│   └── ...
│
└── __pycache__/            # Python キャッシュ（Git 管理外）
```

## 4. モジュール構成

### コアロジック

- `main_v2.py`
  - GUI統合・プラグイン対応のメインエントリポイント。
  - メインループ、GUI起動、プラグイン管理、終了処理。

- `config.py`
  - `settings.env` 読み込み、設定値オブジェクト化、バリデーション。
  - `DEBUG_MODE`, `APP_MODE` など追加設定項目対応。

- `database.py`
  - SQLite 接続管理、テーブル作成、動画の INSERT / SELECT / UPDATE。
  - DBカラム拡張（`selected_for_post`, `scheduled_at` など）対応。

- `youtube_rss.py`
  - RSS URL 生成、取得、パース、DB への反映。

- `plugin_interface.py`
  - NotificationPlugin 抽象基底クラス（すべてのプラグインが実装）。

- `plugin_manager.py`
  - プラグインの自動検出・読み込み・管理。

### Bluesky 投稿関連

- `bluesky_core.py`
  - Bluesky HTTP API 本体（`BlueskyMinimalPoster` クラス）。
  - ログイン、投稿実行、Facet構築、DRY RUN 対応。
  - 拡張用ラッパー `BlueskyPlugin` クラスも含む（bluesky_plugin.py から利用）。

- `plugins/bluesky_plugin.py`
  - Bluesky 投稿プラグイン実装（プラグイン自動ロード）。
  - `bluesky_core.py` の `BlueskyMinimalPoster` API を利用。
  - 画像添付、DB登録済み画像の優先利用対応。

### GUI・画像管理・ロギング関連

- `gui_v2.py`
  - Tkinter ベースの統合 GUI。
  - 動画一覧表示、選択、投稿実行、投稿テスト、統計表示。

- `image_manager.py`
  - 画像ダウンロード・保存・フォーマット変換。
  - リトライ機構、エラーハンドリング。

- `logging_config.py`
  - ロギング統合設定（ロギングプラグイン対応）。

- `plugins/logging_plugin.py`
  - ロギング統合管理プラグイン。
  - 環境変数によるログレベル個別制御、日次ローテーション。

### プラグイン（自動ロード）

- `plugins/youtube_api_plugin.py`
  - YouTube Data API 連携。
  - チャンネルID解決、動画詳細取得。

- `plugins/youtube_live_plugin.py`
  - YouTube ライブ/アーカイブ判定プラグイン。

- `plugins/niconico_plugin.py`
  - ニコニコ動画 RSS 監視・通知プラグイン。

### サムネイル・画像処理

- `thumbnails/__init__.py`
  - Niconico OGP URL 取得、画像再ダウンロード、バックフィル処理の統合インターフェース。

- `thumbnails/image_re_fetch_module.py`
  - 画像未設定動画のサムネイル再ダウンロード・DB更新。

- `thumbnails/niconico_ogp_utils.py`
  - Niconico OGP 取得ユーティリティ。

- `thumbnails/niconico_ogp_backfill.py`
  - Niconico OGP 情報バックフィル処理。

- `thumbnails/youtube_thumb_utils.py`
  - YouTube サムネイル取得ユーティリティ。

- `thumbnails/youtube_thumb_backfill.py`
  - YouTube サムネイルバックフィル処理。

### ユーティリティ

- `utils_v2.py`
  - ユーティリティ関数群（日時フォーマット、リトライ処理など）。


## 5. 設定と環境

### 5.1 設定ファイル
- 設定ファイル名: `settings.env`
- サンプルファイル: `settings.env.example`


### 5.2 必須設定項目
- `YOUTUBE_CHANNEL_ID` - 監視対象の YouTube チャンネル ID（UC から始まる ID）
- `BLUESKY_USERNAME` - Bluesky のハンドル名
- `BLUESKY_PASSWORD` - Bluesky のアプリパスワード
- `POLL_INTERVAL_MINUTES` - ポーリング間隔（最小値: 5、推奨: 10）

### 5.3 オプション設定項目
- `BLUESKY_POST_ENABLED` - Bluesky への投稿を有効にするか（true/false、デフォルト: false）
- `NOTIFY_ON_YT_NEWVIDEO` - 動画検出時に Bluesky へ自動投稿するか（True/False、デフォルト: False）
- `YOUTUBE_API_KEY` - YouTube Data API キー（UC 以外のチャンネル識別子対応・ライブ詳細取得用、未設定可）
- `TIMEZONE` - タイムゾーン設定（例: Asia/Tokyo、デフォルト: system）
- `DEBUG_MODE` - デバッグモード（true/false、デフォルト: false）
- `APP_MODE` - 動作モード（normal, auto_post, dry_run, collect）

### 5.4 動作環境
- OS: Windows 10 以降 / Debian/Ubuntu 系 Linux。
- 言語: Python 3.10+
- DB: SQLite（標準ライブラリ `sqlite3` 使用）。

## 6. ライセンスと公開方針

- ライセンスはリポジトリ全体を GPL v2 とする（既存コードと同一）。
- 利用者固有の ID・パスワード・API キーは `settings.env` にのみ記載し、
公開リポジトリには含めない。
- README に、利用者が自分の ID を取得・設定する手順を簡潔に記載する。

## 7. 制限事項と既知の課題

### 7.1 RSS 方式の制限
- YouTube の仕様により、RSS で取得可能な動画は通常動画のみ（限定公開、非公開動画は含まない）。
- 初回起動後の初回取得で取得されるのは、本アプリ導入以前に公開された通常動画 15 本まで。
- それ以上の過去動画の遡及取得は RSS では不可能。

### 7.2 チャンネル ID の制限
- プラグイン未導入時は、UC から始まるチャンネル ID のみ監視可能。

### 7.3 YouTubeAPI連携プラグイン未導入時の制限
- ライブ配信・動画、プレミア公開、ショート動画、アーカイブの判別不可。
- 動画の詳細情報取得（再生回数、高評価数、公開日時など）不可。
- UC から始まらないチャンネル ID の監視設定不可。

### 7.4 その他のプラグイン未導入時の制限
- サイト連携系プラグイン未導入: Twitch、ニコニコ動画、YouTubeLive は非対応。
- 機能拡張系プラグイン未導入: Discord 通知、画像添付、投稿テンプレート、トンネル連携、データベース連携、テーマ設定（ダークモード）は非対応。

## 8. トラブルシューティング指針

### 8.1 YouTube RSS が取得できない場合
- YouTube サーバーエラーの確認。
- インターネット接続の確認。
- チャンネル ID が UC から始まっているか確認。

### 8.2 Bluesky に投稿できない場合
- `BLUESKY_POST_ENABLED=true` または `NOTIFY_ON_YT_NEWVIDEO=True` が設定されているか確認。
- ユーザー名とアプリパスワードが正しいか確認。
- Bluesky のアプリパスワードは、Web 版設定画面から生成する必要がある。

### 8.3 投稿が実行されない場合
- `BLUESKY_POST_ENABLED` または `NOTIFY_ON_YT_NEWVIDEO` が有効になっているか確認。
- ログファイル（`logs/app.log`）でエラーメッセージを確認。
- 動作モードが通常モード/自動投稿モードになっているか確認（ドライランモード・収集モードでは投稿されない）。

### 8.4 タイムゾーンの問題
- `TIMEZONE` 設定を確認（日本の場合は `Asia/Tokyo`）。
- `system` に設定すると、システムのタイムゾーンが使用される。
