# StreamNotify on Bluesky - v3

> **対象バージョン**: v3.0.0（初期実装）
> **最終更新**: 2025-12-19
> **注記**: YouTubeLiveプラグイン完成時に v3.3.0 へ更新予定

YouTube チャンネルの新着動画を Bluesky に自動投稿するアプリケーションです。
（Twitch / ニコニコなどの対応はプラグインで拡張予定）

## 概要

- このプロジェクトは、特定の YouTube チャンネルの新着動画を RSS で監視し、Bluesky に自動投稿する常駐ボットです。
- 設定ファイルで簡単にカスタマイズでき、将来的にはプラグインで複数の配信プラットフォームに対応予定です。

## 主な機能

- **YouTube RSS 監視**: 指定チャンネルの新着動画を自動検出
- **Bluesky 自動投稿**: 動画情報を指定フォーマットで Bluesky へ投稿
- **ローカル DB**: SQLite で動画情報・投稿状態を管理
- **Tkinter GUI**: 動画一覧表示・手動投稿・統計表示に対応
- **プラグイン拡張**: ニコニコ / YouTube Live / ロギング拡張などに対応（将来計画含む）
- **テンプレートカスタマイズ**: 設定ファイル＋テンプレートファイルで投稿形式をカスタマイズ可能

---

## 🚀 クイックスタート

まずはバニラ状態（コア機能のみ）で試してみてください。慣れてきたらプラグインで拡張できます。

### 1. クローン＆セットアップ

```bash
git clone https://github.com/yourusername/Streamnotify_on_Bluesky.git
cd Streamnotify_on_Bluesky/v3

# 仮想環境作成
python -m venv venv
source venv/bin/activate  # Linux/WSL: source venv/bin/activate

# パッケージ インストール
pip install -r requirements.txt
```

### 2. 設定ファイルを編集

```bash
cp settings.env.example settings.env
# テキストエディタで settings.env を開き、以下4つを設定：
# - YOUTUBE_CHANNEL_ID: YouTubeチャンネルID（UC から始まる）
# - BLUESKY_USERNAME: Blueskyハンドル（例: yourname.bsky.social）
# - BLUESKY_PASSWORD: Blueskyアプリパスワード（Web版設定から生成）
# - POLL_INTERVAL_MINUTES: 監視間隔（分、最小値5）
```

### 3. 起動

```bash
python main_v3.py
```

GUI が起動し、YouTube RSS から新着動画を取得して表示します。
GUI から動画を選択して「投稿」ボタンを押すと Bluesky へ投稿されます。

> ℹ️ **GUI の動作**
> - GUI を最小化しても、バックグラウンドで動作を続けます。
> - GUI を完全に閉じる（ウィンドウのバツボタンをクリック）と、アプリケーションは終了します。

---

## プロジェクト構成

### v3（推奨）

```
v3/
├── main_v3.py              # アプリケーションのエントリポイント
├── config.py               # 設定読み込み・バリデーション
├── database.py             # SQLite 操作＆DB正規化
├── youtube_rss.py          # YouTube RSS 取得・パース
├── bluesky_core.py         # Bluesky HTTP API 本体（ログイン・投稿・Facet構築）
├── gui_v3.py               # GUI フレーム統合（動画選択・投稿・統計表示）
├── image_manager.py        # 画像ダウンロード・保存・リトライ
├── logging_config.py       # ロギング統合設定
├── plugin_interface.py     # NotificationPlugin 抽象基底クラス
├── plugin_manager.py       # プラグイン自動検出・読み込み・管理
├── utils_v3.py             # ユーティリティ関数
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
├── images/                 # 投稿用画像ディレクトリ（プラグイン導入時）
│   ├── default/
│   │   └── noimage.png         # デフォルト画像（画像未設定時）
│   ├── YouTube/                # YouTube 動画サムネイル保存先
│   ├── Niconico/               # ニコニコ動画サムネイル保存先
│   └── Twitch/                 # Twitch 放送画像保存先
│
├── templates/              # 投稿テンプレート
│   ├── youtube/
│   │   ├── yt_new_video_template.txt    # 新着動画投稿用
│   │   ├── yt_online_template.txt       # YouTube 配信開始用（プラグイン時）
│   │   └── yt_offline_template.txt      # YouTube 配信終了用（プラグイン時）
│   └── niconico/
│       └── nico_new_video_template.txt  # ニコニコ新着動画投稿用（プラグイン時）
│
├── Asset/                  # プラグイン用テンプレート・画像保管所
│   │                       # 全サービス・全プラグイン用テンプレート/画像を保管
│   │                       # プラグイン導入時に必要なファイルを本番ディレクトリに自動コピー
│
├── docs/                   # 設計ドキュメント
│   ├── README_GITHUB_v3.md
│   ├── DOCS_CLEANUP_PLAN.md       # ドキュメント整理計画（この整理の記録）
│   ├── Technical/                 # 技術資料（アーキテクチャ・仕様）
│   │   ├── ARCHITECTURE_AND_DESIGN.md    # ★ メインドキュメント
│   │   ├── PLUGIN_SYSTEM.md
│   │   ├── TEMPLATE_SYSTEM.md
│   │   ├── DELETED_VIDEO_CACHE.md
│   │   ├── RICHTEXT_FACET_SPECIFICATION.md
│   │   ├── ASSET_MANAGER_INTEGRATION_v3.md
│   │   ├── YOUTUBE_API_CACHING_IMPLEMENTATION.md
│   │   ├── ModuleList_v3.md
│   │   ├── DEVELOPMENT_GUIDELINES.md
│   │   ├── SETTINGS_OVERVIEW.md
│   │   └── VERSION_MANAGEMENT.md
│   ├── Guides/                    # ユーザーガイド・使い方
│   │   ├── DEBUG_DRY_RUN_GUIDE.md        # デバッグ・トラブルシューティング
│   │   ├── IMAGE_RESIZE_GUIDE.md         # 画像処理の使い方
│   │   └── SESSION_REPORTS.md            # 進捗記録・セッションレポート
│   ├── References/                # 参考資料
│   │   ├── FUTURE_ROADMAP_v3.md
│   │   ├── YouTube新着動画app（初期構想案）.md
│   │   └── 投稿テンプレートの引数.md
│   ├── ARCHIVE/                   # 実装計画・記録（完了後）
│   │   ├── TEMPLATE_IMPLEMENTATION_CHECKLIST.md
│   │   ├── youtube_live_classification_plan.md
│   │   └── DOCS_CLEANUP_COMPLETION_REPORT.md
│   └── Local/                     # AI生成レポート・一時作業ファイル
│       ├── LINK_CORRECTION_REPORT.md
│       ├── README_LINK_VERIFICATION_REPORT.md
│       └── （その他作業用一時ファイル）
│
└── __pycache__/            # Python キャッシュ（Git 管理外）
```

### v1（レガシー）

前のバージョンです。参考用に保管されています。

---

## 必要な環境

- **OS**: Windows 10 以降、または Debian/Ubuntu 系 Linux
- **Python**: 3.10 以上
- **アカウント**: YouTube チャンネル、Bluesky アカウント

---

## 詳細なインストール

### 1. リポジトリをクローン

```bash
git clone https://github.com/yourusername/Streamnotify_on_Bluesky.git
cd Streamnotify_on_Bluesky/v3
```

### 2. 仮想環境を作成（推奨）

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux / WSL / macOS
source venv/bin/activate
```

### 3. 依存パッケージをインストール

```bash
pip install -r requirements.txt
```

### 4. 設定ファイルを作成

```bash
cp settings.env.example settings.env
```

### 5. `settings.env` を編集して必須項目を設定

以下の 4 つの項目は必須です：

| 項目 | 説明 | 例 |
|-----|------|-----|
| `YOUTUBE_CHANNEL_ID` | 監視対象の YouTube チャンネル ID（UC から始まる） | `UCxxxxxxxxxxxxxxxx` |
| `BLUESKY_USERNAME` | Bluesky のハンドル名 | `yourname.bsky.social` |
| `BLUESKY_PASSWORD` | Bluesky のアプリパスワード | `xxxx-xxxx-xxxx-xxxx` |
| `POLL_INTERVAL_MINUTES` | ポーリング間隔（分、最小値 5） | `10` |

その他のオプション設定については、`settings.env` 内のコメント、または [Streamnotify v3 設定項目一覧](Technical/SETTINGS_OVERVIEW.md) を参照してください。

---

## 使用方法

### アプリケーションの起動

```bash
python main_v3.py
```

### 基本的な動き

1. **RSS 取得**: `POLL_INTERVAL_MINUTES` ごとに YouTube RSS フィードを取得
2. **新着検出**: DB と比較して新着動画を検出
3. **DB 保存**: 新着動画をローカル DB に保存
4. **GUI 表示**: Tkinter GUI で動画一覧を表示
5. **手動投稿**: GUI から動画を選択して Bluesky に投稿
6. **ログ記録**: 投稿結果をログファイルに記録

### 動作の詳細

- 起動中は `POLL_INTERVAL_MINUTES` ごとに YouTube RSS を取得し、新着動画を検知します。
- 新着動画は `data/video_list.db` に保存されます。
- **バニラ状態**: `BLUESKY_POST_ENABLED=true` かつ `APP_MODE=auto_post` で Bluesky へ自動投稿されます。
- **プラグイン導入時**: 自動投稿ロジックが拡張され、テンプレート・画像処理などが追加されます。
- Bluesky への投稿履歴ログ:
  - **バニラ状態**: `logs/app.log` に投稿結果を記録
  - **プラグイン導入時**: `logs/post.log` に投稿成功、`logs/post_error.log` にエラーを記録
- アプリケーションログは `logs/app.log` に記録されます。

### 停止方法

- 停止する場合は、GUI ウィンドウのバツボタンで閉じるか、ターミナルで `Ctrl + C` を押してください。

### GUI の主な機能

- **動画一覧表示**: DB に保存されている動画を Treeview で表示
- **動画選択**: チェックボックスで投稿対象を選択
- **投稿実行**: 選択動画を Bluesky に投稿
- **ドライラン**: 投稿をシミュレート（実際には投稿しない）
- **統計表示**: 投稿数、未投稿数などを表示
- **プラグイン状態**: 導入済みプラグイン一覧を表示

---

## プラグインについて

### バニラ状態（プラグイン未導入）

コア機能のみ動作：

- YouTube RSS 監視（通常動画のみ）
- Bluesky への投稿
- ローカル DB 管理
- 基本的なログ出力

### プラグイン導入時

以下のプラグインを導入することで機能を拡張できます：

| プラグイン | 機能 | 状態 |
|-----------|------|------|
| `youtube_live_plugin` | YouTube ライブ配信・アーカイブの判定 | ✅ v3.3.0 実装完了予定 |
| `niconico_plugin` | ニコニコ動画 RSS 監視 | 🔜 v3.x 予定 |
| `youtube_api_plugin` | YouTube Data API 連携（詳細情報取得） | 🔜 v3.x 予定 |
| `logging_plugin` | ロギング統合管理 | 🔜 v3.x 予定 |

プラグイン導入時に必要なテンプレートファイルと画像は、`Asset/` ディレクトリから自動配置されます。

---

## Assetディレクトリとテンプレート・画像管理

- `Asset/` ディレクトリに全サービス・全プラグイン用のテンプレート・画像を保管します。
- **起動時に自動配置**: アプリケーション起動時（`main_v3.py` 実行時）、必要なテンプレート・画像が `Asset/` から本番ディレクトリに自動コピーされます。
- **既存ファイル保護**: 既に存在するファイルは上書きされません（ユーザーの手動編集を保護）。
- **詳細な配置ログ**: ログ（`logs/app.log`）に配置されたファイル一覧が記録されます。

### Asset ディレクトリ構成

```
Asset/
├── templates/
│   ├── default/          # デフォルト用テンプレート
│   ├── youtube/          # YouTube 関連テンプレート
│   ├── niconico/         # ニコニコ関連テンプレート
│   └── twitch/           # Twitch 関連テンプレート（将来予定）
├── images/
│   └── default/          # デフォルト画像
└── README.md             # Asset ディレクトリの説明
```

---

## ドキュメント

詳細な情報は以下をご覧ください：

### 🔧 **Technical/** - 技術資料（開発者向け）
- [**アーキテクチャと設計方針**](Technical/ARCHITECTURE_AND_DESIGN.md) - システム構成、プラグインアーキテクチャ、データベース設計
- [**モジュール一覧**](Technical/ModuleList_v3.md) - 全コンポーネントの説明
- [**設定概要**](Technical/SETTINGS_OVERVIEW.md) - 環境変数・設定項目の詳細
- [**プラグインシステム**](Technical/PLUGIN_SYSTEM.md) - プラグイン開発方法、Rich Text Facet、画像処理
- [**テンプレートシステム**](Technical/TEMPLATE_SYSTEM.md) - テンプレートファイルの仕様・使用方法
- [**削除済み動画除外動画リスト**](Technical/DELETED_VIDEO_CACHE.md) - 除外動画リスト機能、API リファレンス
- [**Rich Text Facet 仕様**](Technical/RICHTEXT_FACET_SPECIFICATION.md) - URL・ハッシュタグリンク化の技術仕様
- [**AssetManager 統合ガイド**](Technical/ASSET_MANAGER_INTEGRATION_v3.md) - Asset 自動配置・プラグイン連携

### 📖 **Guides/** - ユーザーガイド・実装手順
- [**デバッグ・ドライラン**](Guides/DEBUG_DRY_RUN_GUIDE.md) - トラブルシューティング・操作方法
- [**画像リサイズガイド**](Guides/IMAGE_RESIZE_GUIDE.md) - 画像処理の使い方

### 📑 **References/** - 参考資料
- [**将来ロードマップ**](References/FUTURE_ROADMAP_v3.md) - v3+ の計画概要

---

## 設定ファイルについて

設定は `settings.env` で管理されます。テキストエディタで直接編集してください。

**注意**: `settings.env` には個人の ID・パスワード・API キーを記載するため、Git による公開リポジトリには含めないでください（`.gitignore` で除外済み）。

設定編集後は、アプリケーションを再起動して反映させます。

---

## トラブルシューティング

### YouTube RSS が取得できない

- YouTube サーバーの状態を確認してください
- インターネット接続を確認してください
- チャンネル ID が `UC` で始まっているか確認してください

### Bluesky に投稿できない

- `settings.env` でユーザー名とアプリパスワードが正しいか確認してください
- Bluesky のアプリパスワードは Web 版の設定画面から生成する必要があります
- `logs/app.log` でエラーメッセージを確認してください

## ライセンス

このプロジェクトは **GPL License v2** で提供されます。詳細は [LICENSE](../../LICENSE) を参照してください。

---

## サポート

質問や問題がある場合は、GitHub の Issue セクションで報告してください。

---

**最終更新**: 2025-12-19
