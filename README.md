# StreamNotify on Bluesky

YouTube チャンネルの新着動画を Bluesky に自動投稿するアプリケーションです。
（Twitch / ニコニコなどの対応はプラグインで拡張予定）

## 概要

このプロジェクトは、特定の YouTube チャンネルの新着動画を RSS で監視し、Bluesky に自動投稿する常駐ボットです。
設定ファイルで簡単にカスタマイズでき、将来的にはプラグインで複数の配信プラットフォームに対応予定です。

## 主な機能

- **YouTube RSS 監視**: 指定チャンネルの新着動画を自動検出
- **Bluesky 自動投稿**: 動画情報を指定フォーマットで Bluesky へ投稿
- **ローカル DB**: SQLite で動画情報・投稿状態を管理
- **Tkinter GUI**: 動画一覧表示・手動投稿・統計表示に対応
- **プラグイン拡張**: ニコニコ / YouTube Live / ロギング拡張などに対応（将来計画含む）
- **テンプレートカスタマイズ**: 設定ファイル＋テンプレートファイルで投稿形式をカスタマイズ可能

## プロジェクト構成

```
.
├── v2/                    # v2（推奨、現在のメインアプリケーション）
│   ├── main_v2.py
│   ├── config.py
│   ├── database.py
│   ├── youtube_rss.py
│   ├── bluesky_core.py
│   ├── gui_v2.py
│   ├── requirements.txt
│   ├── settings.env.example
│   ├── plugins/           # プラグインディレクトリ
│   ├── docs/              # 設計ドキュメント
│   └── ...
│
├── v1/                    # v1（レガシー、参考用）
│
└── README.md              # このファイル
```

## 必要な環境

- **OS**: Windows 10 以降、または Debian/Ubuntu 系 Linux
- **Python**: 3.10 以上
- **アカウント**: YouTube チャンネル、Bluesky アカウント

## インストール

### 1. リポジトリをクローン

```bash
git clone https://github.com/yourusername/Streamnotify_on_Bluesky.git
cd Streamnotify_on_Bluesky/v2
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

その他のオプション設定については、`settings.env` 内のコメント、または [Streamnotify v2 設定項目一覧](v2/docs/Technical/SETTINGS_OVERVIEW.md) を参照してください。

## 使用方法

### アプリケーションの起動

```bash
python main_v2.py
```

### 基本的な動き

1. **RSS 取得**: `POLL_INTERVAL_MINUTES` ごとに YouTube RSS フィードを取得
2. **新着検出**: DB と比較して新着動画を検出
3. **DB 保存**: 新着動画をローカル DB に保存
4. **GUI 表示**: Tkinter GUI で動画一覧を表示
5. **手動投稿**: GUI から動画を選択して Bluesky に投稿
6. **ログ記録**: 投稿結果をログファイルに記録

### GUI の主な機能

- **動画一覧表示**: DB に保存されている動画を Treeview で表示
- **動画選択**: チェックボックスで投稿対象を選択
- **投稿実行**: 選択動画を Bluesky に投稿
- **ドライラン**: 投稿をシミュレート（実際には投稿しない）
- **統計表示**: 投稿数、未投稿数などを表示
- **プラグイン状態**: 導入済みプラグイン一覧を表示

## ドキュメント

詳細な情報は以下をご覧ください：

### 📚 コア設計・アーキテクチャ

- [アーキテクチャと設計方針](v2/docs/Technical/ARCHITECTURE_AND_DESIGN.md) - システム構成とデータベース設計の詳細
- [モジュール一覧](v2/docs/Technical/ModuleList_v2.md) - 全コンポーネントの説明
- [設定概要](v2/docs/Technical/SETTINGS_OVERVIEW.md) - 環境変数・設定項目の詳細
- [プラグインシステム](v2/docs/Technical/PLUGIN_SYSTEM.md) - プラグイン開発方法、Rich Text Facet、画像処理

### 🎨 テンプレート・キャッシュ・セッション

- [テンプレートシステム](v2/docs/Technical/TEMPLATE_SYSTEM.md) - テンプレートファイルの仕様・使用方法
- [削除済み動画ブラックリスト](v2/docs/Technical/DELETED_VIDEO_CACHE.md) - ブラックリスト機能、API リファレンス
- [セッション実装レポート](v2/docs/Guides/SESSION_REPORTS.md) - 2025-12-17～18 実装内容・テスト結果

### 📋 ユーザーガイド・トラブルシューティング

- [デバッグ・ドライラン](v2/docs/Guides/DEBUG_DRY_RUN_GUIDE.md) - トラブルシューティング
- [テンプレート実装チェックリスト](v2/docs/Guides/TEMPLATE_IMPLEMENTATION_CHECKLIST.md) - テンプレート導入手順
- [画像リサイズガイド](v2/docs/Guides/IMAGE_RESIZE_GUIDE.md) - 画像処理の使用方法

### 🚀 その他・参考資料

- [将来ロードマップ](v2/docs/References/FUTURE_ROADMAP_v2.md) - v3+ の計画概要
- [Rich Text Facet 仕様](v2/docs/Technical/RICHTEXT_FACET_SPECIFICATION.md) - URL・ハッシュタグリンク化の技術仕様
- [AssetManager 統合ガイド](v2/docs/Technical/ASSET_MANAGER_INTEGRATION_v2.md) - Asset 自動配置・プラグイン連携の詳細
- [Asset ディレクトリ README](v2/Asset/README.md) - ユーザー向けの Asset 管理方法

### 📂 全ドキュメント構成

ドキュメントは以下のカテゴリに整理されています：

- **Technical/** - 技術資料（アーキテクチャ・仕様・設計）
- **Guides/** - ユーザーガイド（実装手順・操作方法）
- **References/** - 参考資料（ロードマップ・構想案）
- **Local/** - ローカル作業用（内部用・非公開推奨）

詳細は [v2/docs/README_GITHUB_v2.md](v2/docs/README_GITHUB_v2.md) を参照してください。

## 設定ファイルについて

設定は `settings.env` で管理されます。テキストエディタで直接編集してください。

**注意**: `settings.env` には個人の ID・パスワード・API キーを記載するため、Git による公開リポジトリには含めないでください（`.gitignore` で除外済み）。

設定編集後は、アプリケーションを再起動して反映させます。

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

詳細は [DEBUG_DRY_RUN_GUIDE.md](v2/docs/DEBUG_DRY_RUN_GUIDE.md) を参照してください。

## ライセンス

**このリポジトリ全体は GPLv2 です。詳細はルートの [LICENSE](LICENSE) を参照してください。**

このプロジェクトは **GPL License v2** で提供されます。

- **v2/**: アプリケーション本体（GPLv2）
- **v1/**: レガシー版アプリケーション（GPLv2）
- **OLD_App/**: 旧バージョン（GPLv2）
- **その他ファイル・ドキュメント**: すべて GPLv2 の対象

詳細は [LICENSE](LICENSE) を参照してください。

## 開発・貢献

このプロジェクトは GitHub でオープンソース化されています。

- **Issue 報告**: 不具合や機能リクエストは Issue セクションでお願いします
- **Pull Request**: 改善提案や機能追加は PR でお願いします

詳細な開発ガイドは [CONTRIBUTING.md](CONTRIBUTING.md)（準備中）を参照してください。

## サポート

質問や問題がある場合は、GitHub の Issue セクションで報告してください。

---

**最終更新**: 2025-12-17
