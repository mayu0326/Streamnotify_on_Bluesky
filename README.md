# StreamNotify on Bluesky

- YouTube チャンネルの新着動画を Bluesky に自動投稿するアプリケーションです。
- YouTube動画に対応。YouTubeLive / Twitch / ニコニコなどはプラグインで対応

## 概要

- このプロジェクトは、YouTube・Niconico・Twitch など複数の配信プラットフォームを監視し、Bluesky に自動投稿する常駐ボットです。
- プラグインアーキテクチャにより、新しいプラットフォーム・通知先の対応は拡張プラグインで実現できます。
- **v3（次世代版）**: GUI 大幅拡張、既存機能強化、YouTubeLive 完全対応 \
- **v2（安定版）**: YouTube RSS 監視、Bluesky 投稿機能強化、基本 GUI、YouTube Live 対応、  \
テンプレート管理、画像処理パイプライン、プラグイン拡張 、ニコニコ動画対応

## 主な機能

### v3（推奨）
- **複数プラットフォーム監視**: YouTube、Niconico に対応（Twitch は準備中）
- **高度なフィルタリング**: タイトル検索、配信元別、投稿状態、コンテンツタイプ（🎬 動画/📹 アーカイブ/🔴 配信）
- **マルチテンプレート対応**: YouTube（新着/Live/Archive）、Niconico（新着）
- **YouTube 優先度ベース重複排除**: 新動画 > アーカイブ > 通常動画で自動判定
- **拡張 GUI**: 複合フィルタリング、動画統計表示
- **テンプレートシステム**: プラットフォーム別・イベント別にテンプレート選択可能
- **AssetManager**: プラグイン導入時にテンプレート・画像を自動配置
- **画像処理パイプライン**: サムネイル自動取得・リサイズ・最適化・キャッシング

### v2（安定版）
- **YouTube RSS 監視**: 指定チャンネルの新着動画を自動検出
- **YouTube Live 判定・投稿**: ライブ配信の開始・終了を自動検出して投稿
- **YouTube API キャッシング**: API 呼び出し回数削減のためのローカルキャッシュ
- **ライブ配信対応**: YouTube Live の自動判定・投稿
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

```
├── README.md                    # このファイル
├── LICENSE                      # ライセンス
│
├── v3/                          # v3（推奨、次世代版）
│   ├── main_v3.py               # エントリーポイント
│   ├── gui_v3.py                # 拡張 GUI（1,363 行）
│   ├── plugin_manager.py        # プラグイン管理
│   ├── plugins/                 # プラグイン実装（5 種）
│   ├── utils/                   # デバッグ・検証スクリプト
│   │   ├── database/            # DB操作・検証
│   │   ├── cache/               # キャッシュ管理
│   │   ├── classification/      # 分類・検証
│   │   ├── analysis/            # 分析・検証
│   │   └── DEBUGGING_UTILITIES.md
│   ├── docs/                    # ドキュメント（4 カテゴリ体系）
│   │   ├── Technical/           # 技術資料
│   │   ├── Guides/              # ユーザーガイド
│   │   ├── References/          # 参考資料
│   │   └── Local/               # ローカル作業用
│   ├── Asset/                   # テンプレート・画像配布
│   └── settings.env.example     # 設定ファイル例
│
├── v2/                          # v2（安定版、既存ユーザー向け）
│   │
│   ├── plugins/                 # プラグインディレクトリ
│   │   ├── bluesky_plugin.py    # Bluesky 投稿プラグイン
│   │   ├── youtube_api_plugin.py
│   │   └── ...
│   │
│   ├── docs/                    # 設計ドキュメント（4カテゴリに整理）
│   │   ├── README_GITHUB_v2.md  # ドキュメント入口
│   │   ├── Technical/           # 技術資料（アーキテクチャ・仕様）
│   │   │   ├── ARCHITECTURE_AND_DESIGN.md
│   │   │   ├── PLUGIN_SYSTEM.md
│   │   │   ├── TEMPLATE_SYSTEM.md
│   │   │   ├── YOUTUBE_API_CACHING_IMPLEMENTATION.md
│   │   │   └── ...
│   │   ├── Guides/              # ユーザーガイド（使い方・操作方法）
│   │   │   ├── DEBUG_DRY_RUN_GUIDE.md
│   │   │   ├── IMAGE_RESIZE_GUIDE.md
│   │   │   ├── SESSION_REPORTS.md
│   │   │   └── ...
│   │   ├── References/          # 参考資料（ロードマップ・構想）
│   │   │   ├── FUTURE_ROADMAP_v3.md
│   │   │   └── ...
│   │   ├── ARCHIVE/             # 実装計画・記録（完了後）
│   │   │   ├── TEMPLATE_IMPLEMENTATION_CHECKLIST.md
│   │   │   ├── youtube_live_classification_plan.md
│   │   │   └── ...
│   │   └── Local/               # AI生成レポート・一時ファイル（非公開推奨）
│   │
│   ├── data/                    # ローカルデータ
│   │   └── video_list.db        # SQLite データベース
│   │
│   ├── logs/                    # ログファイル出力先
│   │
│   ├── templates/               # 投稿テンプレート
│   │   └── .templates/
│   │
│   ├── images/                  # スクリーンショット・参考画像
│   │
│   ├── thumbnails/              # キャッシュ済み動画サムネイル
│   │
│   ├── Asset/                   # プラグイン用テンプレート・画像
│   │   └── README.md
│   │
│   └── __pycache__/             # Python キャッシュ（Git 管理外）
│
├── v1/                          # v1（レガシー版、参考用）
│
└── OLD_App/                     # 旧アプリケーション（参考用）
```

## 必要な環境

- **OS**: Windows 10 以降、または Debian/Ubuntu 系 Linux
- **Python**: 3.10 以上
- **アカウント**: YouTube チャンネル、Bluesky アカウント

## インストール

### 1. リポジトリをクローン

```bash
git clone https://git.neco-server.net/mayuneco/Streamnotify_on_Bluesky.git
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

その他のオプション設定については、`settings.env` 内のコメント、または [Streamnotify v3 設定項目一覧](v3/docs/Technical/SETTINGS_OVERVIEW.md) を参照してください。

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

**注記**: SELFPOST と AUTOPOST は同時に有効にならないため、モード切替時はアプリケーション再起動が必要です。

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
  - `AUTOPOST_INCLUDE_SHORTS`: YouTube Shorts を投稿
  - `AUTOPOST_INCLUDE_MEMBER_ONLY`: メンバー限定動画を投稿
  - `AUTOPOST_INCLUDE_PREMIERE`: プレミア配信を投稿

詳細は [AUTOPOST機能仕様書](v3/docs/Technical/AUTOPOST_SELFPOST_機能仕様書.md) を参照。

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

## ドキュメント

詳細な情報は以下をご覧ください：

### 📚 コア設計・アーキテクチャ

- [アーキテクチャと設計方針](v3/docs/Technical/ARCHITECTURE_AND_DESIGN.md) - システム構成とデータベース設計の詳細
- [モジュール一覧](v3/docs/Technical/ModuleList_v3.md) - 全コンポーネントの説明
- [設定概要](v3/docs/Technical/SETTINGS_OVERVIEW.md) - 環境変数・設定項目の詳細
- [プラグインシステム](v3/docs/Technical/PLUGIN_SYSTEM.md) - プラグイン開発方法、Rich Text Facet、画像処理
- [YouTube API キャッシング](v3/docs/Technical/YOUTUBE_API_CACHING_IMPLEMENTATION.md) - キャッシング機能の技術仕様

### 🎨 テンプレート・キャッシュ・デバッグ

- [テンプレートシステム](v3/docs/Technical/TEMPLATE_SYSTEM.md) - テンプレートファイルの仕様・使用方法
- [削除済み動画除外リスト](v3/docs/Technical/DELETED_VIDEO_CACHE.md) - 除外動画リスト機能、API リファレンス
- [デバッグ用ユーティリティ](v3/utils/DEBUGGING_UTILITIES.md) - デバッグスクリプト、検証スクリプトの使用方法

### 📋 ユーザーガイド・トラブルシューティング

- [デバッグ・ドライラン](v3/docs/Guides/DEBUG_DRY_RUN_GUIDE.md) - トラブルシューティング・操作方法
- [画像リサイズガイド](v3/docs/Guides/IMAGE_RESIZE_GUIDE.md) - 画像処理の使い方

### 🚀 その他・参考資料

- [将来ロードマップ](v3/docs/References/FUTURE_ROADMAP_v3.md) - v3+ の計画概要
- [Rich Text Facet 仕様](v3/docs/Technical/RICHTEXT_FACET_SPECIFICATION.md) - URL・ハッシュタグリンク化の技術仕様
- [AssetManager 統合ガイド](v3/docs/Technical/ASSET_MANAGER_INTEGRATION_v3.md) - Asset 自動配置・プラグイン連携の詳細

## 設定ファイルについて

設定は `settings.env` で管理されます。テキストエディタで直接編集してください。

**注意**: `settings.env` には個人の ID・パスワード・API キーを記載するため、Git による公開リポジトリには含めないでください（`.gitignore` で除外済み）。

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

## デバッグ・ユーティリティスクリプトについて

デバッグ・検証・分析スクリプトを `v3/utils/` 配下に体系的に整理しました：

- ✅ **database/**: DB操作・検証スクリプト（5ファイル）
- ✅ **cache/**: キャッシュ管理スクリプト（2ファイル）
- ✅ **classification/**: 分類・検証スクリプト（4ファイル）
- ✅ **analysis/**: API・環境検証スクリプト（4ファイル）
- ✅ **DEBUGGING_UTILITIES.md**: 包括的ドキュメント（200+ 行）

詳細は [v3/utils/DEBUGGING_UTILITIES.md](v3/utils/DEBUGGING_UTILITIES.md) を参照してください。

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

詳細は [DEBUG ログとドライラン機能 ガイド](v3/docs/Guides/DEBUG_DRY_RUN_GUIDE.md) を参照してください。

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

#### v3.3.0 一括投稿スケジュール機能（現在準備中）

複数動画の分散投稿スケジュール機能を実装。Bluesky API レート制限に対応。

- 📌 複数動画の一括選択
- 📌 スケジュール間隔の設定（5分～60分）
- 📌 スケジュール確認・編集・キャンセル機能
- 🚀 UI 最適化による操作性向上

#### v3.2.0 フィルタプロファイル保存機能（2025-12-18）
- フィルタ条件の保存機能を追加しました
- フィルタリング処理のパフォーマンスが向上しました

## 🎉 v3.1.0 プロジェクト整理完了
- GUI フィルタ・検索機能、重複投稿防止オプションを追加しました。
- GUI からのDB及び設定バックアップ・復元機能を追加しました。

### v3.0.0 AssetManager と 初期状態投入（2025-12-18）
- v2.x との互換性最適化：
- **AssetManagerを導入**: テンプレート・画像管理を自動化。
- **GUI からの操作性向上**：ソースフィルタリング対応
- **動画登録の重複抑止**: YouTube 優先度ベースの重複排除
- **ドキュメント統一**: 30+ ファイルを 4 カテゴリ体系に再構成

### v2.3.0 YouTubeLiveプラグイン実装完了（2025-12-18）

YouTubeLiveプラグインの実装が完全に完了しました。以下の機能がv2で確立されました：

- ✅ YouTube Live/Archive/Normal判定ロジック
- ✅ Live開始/終了の自動ポーリング・自動投稿
- ✅ テンプレート選択・投稿（yt_online_template.txt / yt_offline_template.txt）
- ✅ DB拡張（live_status, content_type）
- ✅ 全テスト完了（単体 12、統合 10）

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

詳細な開発ガイドは [v3/CONTRIBUTING.md](v3/CONTRIBUTING.md)（v3）または [v2/CONTRIBUTING.md](v2/CONTRIBUTING.md)（v2）を参照してください。

## サポート

質問や問題がある場合は、Git の Issue セクションで報告してください。

---

**最終更新**: 2025-12-19
