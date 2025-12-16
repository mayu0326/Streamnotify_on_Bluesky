# Streamnotify on Bluesky

複数の配信プラットフォーム（Twitch、YouTube、ニコニコ動画など）の配信情報をBlueSkyに自動投稿するアプリケーションです。

## 概要

このプロジェクトは、配信開始通知や配信情報の更新をリアルタイムで検知し、Bluesky社交ネットワークに自動投稿する機能を提供します。

## 主な機能

- **マルチプラットフォーム対応**: Twitch、YouTube、ニコニコ動画などからの配信情報を監視
- **自動投稿**: 配信開始時に自動的にBlueSkyへ投稿
- **カスタマイズ可能**: 投稿テンプレートのカスタマイズが可能
- **GUI管理画面**: 設定や監視状態を一元管理
- **ログ機能**: 詳細なログ出力で問題追跡が容易

## プロジェクト構成

- `v2/` - 最新バージョン（推奨）
  - 最新の機能と改善を含む現在のメインアプリケーション

- `v1/` - 前のバージョン
  - レガシーコード（参考用）

## 必要な環境

- Python 3.8以上
- 各プラットフォームのAPIキー（Twitch、YouTube等）
- Blueskyアカウント

## インストール

1. リポジトリをクローン
```bash
git clone https://github.com/yourusername/Streamnotify_on_Bluesky.git
cd Streamnotify_on_Bluesky
```

2. 依存パッケージをインストール
```bash
pip install -r v2/requirements.txt
```

3. 設定ファイルを作成
```bash
cp v2/settings.env.example v2/settings.env
```

4. `settings.env`を編集して、APIキーと認証情報を設定

## 使用方法

### アプリケーションの起動

```bash
python v2/main_v2.py
```

### 設定

- GUI管理画面から各プラットフォームのアカウント設定
- 投稿テンプレートのカスタマイズ
- 通知設定の調整

## ドキュメント

- [アーキテクチャ](v2/docs/ARCHITECTURE_v2.md) - システムアーキテクチャの詳細
- [モジュール一覧](v2/docs/ModuleList_v2.md) - 全モジュールの説明
- [プラグイン開発ガイド](v2/docs/BLUESKY_PLUGIN_GUIDE.md) - プラグイン開発方法
- [設定概要](v2/docs/SETTINGS_OVERVIEW.md) - 設定項目の説明

## ライセンス

詳細は[LICENSE](LICENSE)を参照してください。

## 支援

問題が発生した場合やご質問がある場合は、Issuesセクションで報告してください。

---

**最終更新**: 2025年12月
