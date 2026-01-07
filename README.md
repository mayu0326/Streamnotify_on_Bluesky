# StreamNotify on Bluesky

- YouTube チャンネルの新着動画を Bluesky に自動投稿するアプリケーションです。
- YouTube動画に対応。YouTube Live（モジュール）、ニコニコ、Twitch などはプラグインで対応

## 概要

- このプロジェクトは、YouTube・Niconico・Twitch など複数の配信プラットフォームを監視し、  \
Bluesky に自動投稿する常駐ボットです。
- プラグインアーキテクチャにより、新しいプラットフォーム・通知先の対応は  \
拡張プラグインで実現できます。
- **v3（次世代版）**: GUI 大幅拡張、既存機能強化、YouTube Live 完全対応（モジュール化） \
- **v2（安定版）**: YouTube RSS 監視、Bluesky 投稿機能強化、基本 GUI、YouTube Live 対応、  \
テンプレート管理、画像処理パイプライン、プラグイン拡張 、ニコニコ動画対応

## 主な機能

### v3（推奨）
- **複数プラットフォーム監視**: YouTube、Niconico に対応（Twitch は準備中）
- **高度なフィルタリング**: タイトル検索、配信元別、投稿状態、コンテンツタイプ  \
（🎬 動画/📹 アーカイブ/🔴 配信/ プレミア公開）
- **マルチテンプレート対応**: YouTube（新着/Live/Archive）、Niconico（新着）
- **YouTube 優先度ベース重複排除**: 特定条件を満たすか否かで自動判定
- **拡張 GUI**: 複合フィルタリング、動画統計表示、Websub、プラグイン状態表示
- **テンプレートシステム**: プラットフォーム別・イベント別にテンプレート選択可能
- **AssetManager**: プラグイン導入時にテンプレート・画像を自動配置
- **画像処理パイプライン**: サムネイル自動取得・リサイズ・最適化・キャッシング

### v2（安定版）
- **YouTubeRSS&Websub 監視**: 指定チャンネルの新着動画を自動検出(webhook対応)
- **YouTube Live 判定・投稿**: ライブ配信の開始・終了を自動検出して投稿
- **YouTube API キャッシング**: API 呼び出し回数削減のためのローカルキャッシュ
- **ライブ配信対応**: YouTube Live の自動判定・投稿(予約枠＆アーカイブ対応)
- **ニコニコIDからユーザー名取得**： ニコニコ動画のユーザー名を自動取得
- **ニコニコ動画 RSS 監視**: 指定ユーザーの新着動画を自動検出
- **動画重複登録抑止のための制御**： 削除済み動画の除外リスト管理
- **画像処理パイプライン**: サムネイル自動取得・リサイズ・最適化・キャッシング
- **Bluesky 自動投稿**: 動画情報を指定フォーマットで Bluesky へ投稿
- **テンプレート管理**: プラットフォーム別・イベント別にテンプレート選択可能
- **プラグイン拡張**: YouTube Live・YouTube API・Niconico・ロギング拡張に対応
- **投稿内容カスタマイズ**: 設定で投稿形式(画像・リンクカード、予約投稿)をカスタマイズ可能
- **ローカル DB**: SQLite で動画情報・投稿状態を管理
- **Tkinter GUI**: 動画一覧表示・手動投稿・統計表示に対応

## プロジェクト構成
<details>
```
├── README.md                    # このファイル
├── LICENSE                      # ライセンス
│
├── v3/                          # v3（推奨、次世代版）
│   ├── main_v3.py               # エントリーポイント
│   ├── gui_v3.py                # 拡張 GUI
│   ├── config.py                # 設定管理
│   ├── database.py              # SQLite 操作
│   ├── bluesky_core.py          # Bluesky 投稿処理
│   ├── plugin_manager.py        # プラグイン管理
│   ├── plugin_interface.py      # プラグイン基本インターフェース
│   ├── logging_config.py        # ロギング設定
│   ├── image_manager.py         # 画像ダウンロード・管理
│   ├── image_processor.py       # 画像リサイズ・処理
│   ├── template_utils.py        # テンプレート処理
│   ├── asset_manager.py         # アセット自動配置
│   ├── utils_v3.py              # ユーティリティ関数
│   │
│   ├── youtube_core/            # YouTube 処理モジュール（プラグインではない）
│   │   ├── youtube_rss.py           # RSS 取得・パース
│   │   ├── youtube_video_classifier.py # 動画分類（Live/Archive判定）
│   │   ├── youtube_dedup_priority.py # 重複排除ロジック
│   │   ├── youtube_websub.py        # WebSub サポート
│   │   └── __init__.py
│   │
│   ├── plugins/                 # プラグインディレクトリ
│   │   ├── bluesky_plugin.py    # Bluesky 投稿プラグイン
│   │   ├── niconico_plugin.py   # ニコニコ動画 RSS プラグイン
│   │   ├── logging_plugin.py    # ロギング統合プラグイン
│   │   └── youtube/             # YouTube 関連プラグイン
│   │       ├── youtube_api_plugin.py  # YouTube Data API プラグイン
│   │       └── __init__.py
│   │
│   ├── docs/                    # ドキュメント（4 カテゴリ体系）
│   │   ├── Technical/           # 技術資料
│   │   ├── Guides/              # ユーザーガイド
│   │   ├── References/          # 参考資料
│   │   └── Local/               # ローカル作業用
│   │
│   ├── Asset/                   # テンプレート・画像配布
│   │   ├── README.md            # AssetManager 統合ガイド
│   │   ├── templates/           # テンプレート配布元
│   │   │   ├── default/         # デフォルトテンプレート
│   │   │   ├── youtube/         # YouTube 関連
│   │   │   ├── niconico/        # ニコニコ関連
│   │   │   └── twitch/          # Twitch 関連（将来）
│   │   └── images/              # 画像配布元
│   │       ├── default/         # デフォルト画像
│   │       ├── YouTube/         # YouTube 関連
│   │       ├── Niconico/        # ニコニコ関連
│   │       └── Twitch/          # Twitch 関連（将来）
│   │
│   ├── templates/               # 実行時テンプレートディレクトリ
│   │   ├── youtube/             # YouTube テンプレート
│   │   ├── niconico/            # ニコニコテンプレート
│   │   └── .templates/          # デフォルト・フォールバック用
│   │
│   ├── images/                  # 実行時画像保存ディレクトリ
│   │   ├── default/
│   │   ├── YouTube/
│   │   └── Niconico/
│   │
│   ├── data/                    # ローカルデータ
│   │   ├── video_list.db        # SQLite データベース
│   │   └── youtube_video_detail_cache.json  # キャッシュ
│   │
│   ├── logs/                    # ログファイル出力先
│   ├── thumbnails/              # サムネイル処理ユーティリティ
│   ├── settings.env.example     # 設定ファイル例
│   └── requirements.txt         # Python 依存パッケージ
│
├── v2/                          # v2（安定版、既存ユーザー向け）
│   ├── main_v2.py
│   ├── plugins/                 # プラグインディレクトリ
│   │   ├── bluesky_plugin.py
│   │   ├── youtube_api_plugin.py
│   │   ├── youtube_live_plugin.py
│   │   ├── niconico_plugin.py
│   │   └── logging_plugin.py
│   ├── docs/                    # ドキュメント
│   ├── data/                    # ローカルデータ
│   ├── logs/                    # ログファイル
│   ├── templates/               # テンプレート
│   ├── images/                  # 画像キャッシュ
│   ├── Asset/                   # アセット配布
│   ├── settings.env.example
│   └── requirements.txt
│
├── v1/                          # v1（レガシー版、参考用）
│
└── OLD_App/                     # 旧アプリケーション（参考用）
```
</details>

## 必要な環境

- **OS**: Windows 10 以降、または Debian/Ubuntu 系 Linux
- **Python**: 3.10 以上
- **アカウント**: YouTube チャンネル、Bluesky アカウント

## インストール

### 1. リポジトリをクローン

```bash
git clone https://github.com/mayu0326/Streamnotify_on_Bluesky.git
cd Streamnotify_on_Bluesky/v3    # v3（推奨）または v2（安定版）
```

### 2. 依存パッケージをインストール

```bash
# 仮想環境の作成（推奨）
python -m venv venv

# Windows
venv\Scripts\activate

# Linux / WSL
source venv/bin/activate

# パッケージのインストール
pip install -r requirements.txt
```

### 3. 設定ファイルを作成

```bash
# settings.env.example をコピー
cp settings.env.example settings.env
```

### 4. `settings.env` を編集して必須項目を設定

以下の 4 つの項目は必須です：

| 項目 | 説明 | 例 |
|-----|------|-----|
| `YOUTUBE_CHANNEL_ID` | 監視対象の YouTube チャンネル ID（UC から始まる） | `UCxxxxxxxxxxxxxxxx` |
| `BLUESKY_USERNAME` | Bluesky のハンドル名 | `yourname.bsky.social` |
| `BLUESKY_PASSWORD` | Bluesky のアプリパスワード | `xxxx-xxxx-xxxx-xxxx` |
| `POLL_INTERVAL_MINUTES` | ポーリング間隔（分、最小値 5） | `10` |

その他のオプション設定については、 [Streamnotify v3 設定項目一覧](v3/docs/Guides/SETTINGS_OVERVIEW.md) を参照してください。

## 使用方法

### アプリケーションの起動

```bash
# v3（推奨）
python main_v3.py

# または v2（安定版）
python main_v2.py
```

### 動作モード（v3）

`settings.env` の `APP_MODE` で動作モードを選択します：

| モード | 説明 | 用途 |
|:--|:--|:--|
| `selfpost` | 完全手動投稿 | ユーザーがGUI操作で投稿対象を選択 |
| `autopost` | 完全自動投稿 | 環境変数とロジックのみで自動投稿 |
| `dry_run` | テストモード | 投稿をシミュレート（実際には投稿しない） |
| `collect` | 収集モード | RSS取得・DB保存のみ（投稿機能オフ） |

**注記**: SELFPOST と AUTOPOST は同時に有効にならないため、  \
モード切替時はアプリケーション再起動が必要です。

### 基本的な動き（SELFPOST モード）

1. **RSS 取得**: `POLL_INTERVAL_MINUTES` ごとに YouTube RSS フィードを取得
2. **新着検出**: DB と比較して新着動画を検出
3. **DB 保存**: 新着動画をローカル DB に保存
4. **GUI 表示**: Tkinter GUI で動画一覧を表示
5. **手動投稿**: GUI から動画を選択して Bluesky に投稿
6. **ログ記録**: 投稿結果をログファイルに記録

### AUTOPOST モード（自動投稿）

`APP_MODE=autopost` の場合、以下の環境変数で自動投稿を制御：

- **安全弁機構**:
  - `AUTOPOST_INTERVAL_MINUTES`: 最小投稿間隔（デフォルト: 5分）
  - `AUTOPOST_LOOKBACK_MINUTES`: 安全チェック時間窓（デフォルト: 30分）
  - `AUTOPOST_UNPOSTED_THRESHOLD`: 未投稿動画の安全上限（デフォルト: 20件）

- **動画種別フィルタ**:
  - `AUTOPOST_INCLUDE_NORMAL`: 通常動画を投稿
  - `AUTOPOST_INCLUDE_PREMIERE`: プレミア配信を投稿

詳細は [AUTOPOST機能仕様書](./v3/docs/References/AUTOPOST_SELFPOST_機能仕様書.md) を参照。

### GUI の主な機能（SELFPOST モード）

- **動画一覧表示**: DB に保存されている動画を Treeview で表示
- **フィルタリング**: タイトル、投稿状態、配信元で動画を検索
- **動画選択**: チェックボックスで投稿対象を選択
- **投稿実行**: 選択動画を Bluesky に投稿
- **予約投稿**: スケジュール指定で投稿を予約
- **ドライラン**: 投稿をシミュレート（実際には投稿しない）
- **統計表示**: 投稿数、未投稿数などを表示
- **重複投稿防止**: 既投稿動画の自動検知（`PREVENT_DUPLICATE_POSTS=true`）
- **プラグイン状態**: 導入済みプラグイン一覧を表示

## 設計方針と制限事項

- このアプリケーションは、\
**ユーザーの環境だけで完結する・難しいサーバ設定を不要にする** ことを設計方針としています。  \
そのため、外部からの通信やサーバー設置、ドメイン、固定IP が必要な WebSub/Webhook ではなく、\
**RSS + API 方式** を採用しています。

### ⚠️ リアルタイム性に関する制限

この設計により、RSSモード時は以下の制限があります：

- **ラグの発生**: YouTube への動画投稿、配信枠作成から実際にこのアプリで検知され投稿されるまで、  \
**数分～数十分程度ラグが発生する場合があります**。\
これは **YouTube 側の RSS 更新タイミング** によるもので、  \
アプリ側では制御できません。

- **リアルタイム性の目安**: 通常は数分以内に検知されますが、状況により **10分程度遅れる可能性があります**。

- **WebSub/Webhook 対応**: WebSub/Webhook には、ご自身でwebhookサーバーを作られる場合に限り対応しています。

### ✅ この設計のメリット

- サーバー設置が不要
- ドメイン取得が不要
- 固定 IP が不要
- ファイアウォール設定が不要
- あなたの環境のみで完結
- **シンプルで保守しやすい**

## ドキュメント

詳細な情報は以下をご覧ください：

### 👥 ユーザーガイド
- [Bluesky 設定ガイド](v3/docs/Guides/BLUESKY_SETUP_GUIDE.md)
- [クイックスタートガイド](v3/docs/Guides/GETTING_STARTED.md)
- [GUI ユーザーマニュアル](v3/docs/Guides/GUI_USER_MANUAL.md)
- [インストール・セットアップガイド](v3/docs/Guides/INSTALLATION_SETUP.md)
- [動作モードガイド](v3/docs/Guides/OPERATION_MODES_GUIDE.md)
- [設定項目一覧](v3/docs/Guides/SETTINGS_OVERVIEW.md)
- [YouTube 設定ガイド](v3/docs/Guides/YOUTUBE_SETUP_GUIDE.md)
- [ニコニコ設定ガイド](v3/docs/Guides/NICONICO_SETUP_GUIDE.md)
- [FAQ/トラブルシューティング](v3/docs/Guides/FAQ_TROUBLESHOOTING_BASIC.md)
- [動画追加機能ガイド](v3/docs/Guides/ADD_VIDEO_GUI_FEATURE.md)
- [投稿テンプレートガイド](v3/docs/Guides/TEMPLATE_GUIDE.md)

### 🛠 技術資料
- [アーキテクチャと設計 ガイド](v3/docs/Technical/ARCHITECTURE_AND_DESIGN.md)
- [アセットマネージャー ガイド](v3/docs/Technical/ASSET_MANAGER_INTEGRATION_v3.md)
- [DEBUG ログとドライラン機能 ガイド](v3/docs/Technical/DEBUG_DRY_RUN_GUIDE.md)
- [削除済み動画除外リスト ガイド](v3/docs/Technical/VIDEO/DELETED_VIDEO_CACHE.md)
- [GUI フィルタ・重複投稿防止ガイド](v3/docs/Technical/GUI_FILTER_AND_DUPLICATE_PREVENTION.md)
- [画像リサイズ機能 ガイド](v3/docs/Technical/IMAGE_RESIZE_GUIDE.md)
- [プラグインシステム ガイド](v3/docs/Technical/PLUGIN_SYSTEM.md)
- [Bluesky リッチテキスト ガイド](v3/docs/Technical/RICHTEXT_FACET_SPECIFICATION.md)
- [テンプレートシステム ガイド](v3/docs/Technical/TEMPLATE_SYSTEM.md)
- [WebSub 実装ガイド](v3/docs/Technical/WEBSUB/WEBSUB_IMPLEMENTATION.md)
- [WebSub クライアント ガイド](v3/docs/Technical/WEBSUB/WEBSUB_CLIENT_IMPLEMENTATION.md)
- [YouTube 重複排除設定ガイド](v3/docs/Technical/YouTube/YOUTUBE_DEDUP_SETTING.md)
- [プラグイン実装タスク管理](v3/docs/Technical/V3_PLUGIN_IMPLEMENTATION_TASKS.md)
- [**Twitch API ポーリング実装ガイド**](v3/docs/Technical/TWITCH/TWITCH_POLLING_IMPLEMENTATION.md)

## 📚 YouTube関連資料
- [YouTube API キャッシュ実装](v3/docs/Technical/YouTube/YOUTUBE_API_CACHING_IMPLEMENTATION.md)
- [YouTube Live 動画分類機構](v3/docs/Technical/YouTube/YOUTUBE_LIVE_CACHE_IMPLEMENTATION.md)

### 💡 設計思想・アーキテクチャ
- [**Streamnotify 設計思想とアーキテクチャ哲学**](v3/docs/References/DESIGN_PHILOSOPHY.md)（⭐ 必読）
- [OLD_App 既存実装リファレンス](v3/docs/Technical/OLDAPP_REFERENCE_FOR_V3_PLUGINS.md)

### 関連資料
- [AUTOPOST_SELFPOST_機能仕様書.md](v3/docs/References/AUTOPOST_SELFPOST_機能仕様書.md)
- [開発ガイドライン](v3/docs/References/DEVELOPMENT_GUIDELINES.md)
- [**将来実装機能ロードマップ**](v3/docs/References/FUTURE_ROADMAP_v3.md)（⭐ 更新：v3.1.0以降の方針確定版）
- [初期構想案](v3/docs/References/INITIAL_CONCEPT.md)
- [バージョン管理ガイド](v3/docs/Technical/VERSION_MANAGEMENT.md)
- [モジュール一覧](v3/docs/References/ModuleList_v3.md)


## 設定ファイルについて

設定は `settings.env` で管理されます。テキストエディタで直接編集してください。

**注意**: `settings.env` には個人の ID・パスワード・API キーを記載するため、  \
Git による公開リポジトリには含めないでください（`.gitignore` で除外済み）。

設定編集後は、アプリケーションを再起動して反映させます。

### バージョン選択ガイド

| バージョン | 推奨用途 | 特徴 | 状態 |
|:--|:--|:--|:--|
| **v3（推奨）** | 新規ユーザー、複合投稿 | 最新機能、複合プラグイン、拡張 GUI | 🚀 本番（最新） |
| **v2（安定版）** | 既存ユーザー、シンプル運用 | 安定動作、YouTube Live 対応 | ✅ 本番（安定） |
| **v1（レガシー）** | 参考・学習用 | 最初期実装 | 📚 参考用 |

詳細は [v3/docs/References/FUTURE_ROADMAP_v3.md](v3/docs/References/FUTURE_ROADMAP_v3.md) を参照してください。

## リリースノート

- [リリースノート一覧](./Release_Notes/)

## 既知の不具合・仕様

### ✅ LIVE とアーカイブの再登録（仕様）

**状況**: GUI で LIVE と判定された動画がアーカイブに変わるなど、  \
コンテンツ種別が変わった場合、別エントリとして DB に再登録されます。

**影響**: 同じ動画の以前のエントリにあった以下の情報が失われます：
- サムネイル画像の登録情報
- 投稿記録（Bluesky への投稿済みフラグ）
- 予約投稿時間
- 投稿日時

**これは仕様です** - ユーザーが LIVE と Archive の両方に投稿したい場合に対応するための設計です。

**復旧方法**:
- **サムネイル再登録**: アプリ再起動 → YouTube API データ取得 → 自動更新
- **手動で急ぐ場合**: YouTubeデータAPI の手動取得またはサムネイル手動再登録機能を使用

詳細は [GUI フィルタ・重複投稿防止ガイド](v3/docs/Technical/GUI_FILTER_AND_DUPLICATE_PREVENTION.md) を参照してください。

### ⚠️ YouTube Live スケジュール枠の予定時刻変更（仕様）

**状況**: YouTube Live のスケジュール枠で配信予定時刻が変更された場合、  \
DB の `published_at` は新しい時刻に更新されますが、  \
**Bluesky への通知投稿は発生しません**。

**理由**: 投稿のトリガーは `content_type` と `live_status` の状態遷移のみ監視しており、  \
`published_at`（予定時刻）の変化は監視対象外であるため。

**具体例**:
- 初期状態: `schedule`（予定時刻: AM 1:00）
- ポーリング後: `schedule`（予定時刻: AM 1:30 に更新）
- **投稿**: ❌ されません（状態遷移がないため）
- **DB**: ✅ `published_at` は AM 1:30 に更新されます

**これは仕様です** - 予定時刻の微調整は投稿対象外として設計されています。

**解決方法**:
- YouTube Live の配信が実際に開始される（`schedule` → `live` に遷移）と、投稿が発火します
- 予定時刻変更の通知が必要な場合は、手動で Bluesky に投稿してください

### ⚠️ YouTube API レート制限

**状況**: YouTube Data API のクォータ消費により、RSS 取得が失敗する場合があります。

**対応方法**:
- `settings.env` で `POLL_INTERVAL_MINUTES` を増やしてください（デフォルト: 5分 → 推奨: 10分以上）
- API キーが無い場合は、RSS フィードのみの監視でレート制限の影響を回避できます

詳細は [YOUTUBE_API_CACHING_IMPLEMENTATION.md](v3/docs/Technical/YouTube/YOUTUBE_API_CACHING_IMPLEMENTATION.md) を参照してください。

## トラブルシューティング

### YouTube RSS が取得できない

- YouTube サーバーの状態を確認してください
- インターネット接続を確認してください
- チャンネル ID が `UC` で始まっているか確認してください

### Bluesky に投稿できない

- `settings.env` でユーザー名とアプリパスワードが正しいか確認してください
- Bluesky のアプリパスワードは Web 版の設定画面から生成する必要があります
- `logs/app.log` でエラーメッセージを確認してください

### ログファイルの確認

- **app.log**: アプリケーション全般のログ
- **error.log**: エラーのみを記録
- その他のログファイル：プラグイン導入時に自動生成

詳細は [DEBUG ログとドライラン機能 ガイド](v3/docs/Technical/DEBUG_DRY_RUN_GUIDE.md) を参照してください。

## ライセンス

**このリポジトリ全体は GPLv2 です。詳細はルートの [LICENSE](LICENSE) を参照してください。**

このプロジェクトは **GPL License v2** で提供されます。

- **v3/**: アプリケーション本体（GPLv2）
- **v2/**: アプリケーション本体（GPLv2）
- **v1/**: レガシー版アプリケーション（GPLv2）
- **OLD_App/**: 旧バージョン（GPLv2）
- **その他ファイル・ドキュメント**: すべて GPLv2 の対象

詳細は [LICENSE](LICENSE) を参照してください。

## バージョン履歴

#### v3.4.0 一括投稿スケジュール機能（現在準備中）
複数動画の分散投稿スケジュール機能を実装。Bluesky API レート制限に対応。

- 📌 複数動画の一括選択
- 📌 スケジュール間隔の設定（5分～60分）
- 📌 スケジュール確認・編集・キャンセル機能

#### v3.3.0 YouTubeLiveに関する認識精度向上とUI改善（2026-01-06）
- ✅ YouTube Live 判定ロジックの改善
- ✅ YouTube API キャッシュ機構の最適化
- ✅ websub 通知の安定性向上およびセキュリティ強化
- 予約枠設定・LIVE中・終了後・アーカイブ化を検出する動的ポーリング間隔の設定
- 🚀 UI 最適化による操作性向上
- GUIからの設定変更・設定切り替え機能
- 投稿テンプレート作成・編集機能
- 🐛 軽微なバグ修正

#### v3.2.0 フィルタプロファイル保存機能（2025-12-18）
- フィルタ条件の保存機能を追加しました
- フィルタリング処理のパフォーマンスが向上しました
- 動画追加機能を追加しました（GUI の「➕ 動画追加」ボタン）
- YouTube API/手動入力による動画登録機能を実装しました
- youtube_video_detail_cache.json による自動キャッシング対応
- DB 操作の最適化を行いました
- wwbsub 機能に対応しました(v3のみ/センターサーバー方式)

## 🎉 v3.1.0 プロジェクト整理完了
- GUI フィルタ・検索機能、重複投稿防止オプションを追加しました。
- GUI からのDB及び設定バックアップ・復元機能を追加しました。

### v3.0.0 AssetManager と 初期状態投入（2025-12-18）
- v2.x との互換性最適化：
- **AssetManagerを導入**: テンプレート・画像管理を自動化。
- **GUI からの操作性向上**：ソースフィルタリング対応
- **動画登録の重複抑止**: YouTube 優先度ベースの重複排除
- **ドキュメント統一**: 30+ ファイルを 4 カテゴリ体系に再構成

### v2.3.0 YouTube Live プラグイン実装完了（2025-12-18）

v2 で YouTube Live プラグインの実装が完全に完了しました。以下の機能がv2で確立されました：

- ✅ YouTube Live/Archive/Normal判定ロジック
- ✅ Live開始/終了の自動ポーリング・自動投稿
- ✅ テンプレート選択・投稿（yt_online_template.txt / yt_offline_template.txt）
- ✅ DB拡張（live_status, content_type）
- ✅ 全テスト完了（単体 12、統合 10）

**注記**: v3 では YouTube Live 判定がプラグインではなく `youtube_core/` モジュールとして実装され、より高度な動画分類機能を提供します。

#### v2.1.0 Bluesky 投稿の安定性向上（2025-12-17）

- Bluesky 投稿の安定性を向上。
- 画像自動リサイズ機能を追加し、Bluesky の要件に適合。
- DRY RUN 機能を追加し、投稿をシミュレート可能に。
- 投稿設定ウィンドウを追加し、GUI で投稿設定を簡単に変更可能に。

#### v2.0.0 プラグインアーキテクチャ導入（2025-12-16）

- プラグインアーキテクチャを導入し、拡張性を大幅に向上。YouTube 動画判定 対応。
- SQLite データベースを導入し、動画情報と投稿状態を効率的に管理。
- 投稿テンプレートのカスタマイズ機能を追加。

#### v1.1.0 バグ修正とパフォーマンス改善（2025-12-15）

- バグ修正とパフォーマンス改善、ロギングシステム強化。
- Niconico 動画対応とサムネイル管理機能を追加。

#### v1.0.0 初期リリース（2025-12-15）

- Streamnotify on Bluesky の最初のバージョン。
- YouTube RSS 監視と Bluesky 投稿の基本機能を実装。

## 開発・貢献

このプロジェクトは Git でオープンソース化されます。

- **Issue 報告**: 不具合や機能リクエストは Issue セクションでお願いします
- **Pull Request**: 改善提案や機能追加は PR でお願いします

詳細な開発ガイドは [v3/CONTRIBUTING.md](v3/docs/CONTRIBUTING.md)（v3）または [v2/CONTRIBUTING.md](v2/CONTRIBUTING.md)（v2）を参照してください。

## サポート

質問や問題がある場合は、Git の Issue セクションで報告してください。

---

**最終更新**: 2025-12-26
