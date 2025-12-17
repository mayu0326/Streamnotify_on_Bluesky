# Asset ディレクトリ

## 概要

`Asset/` ディレクトリは、全プラグイン・全サービス用のテンプレートや画像を保管する場所です。

## 自動配置について

**プラグイン導入時に必要なファイルは自動でコピーされます。**

- `main_v2.py` 起動時に `asset_manager.py` が実行
- プラグインが読み込まれるたびに、該当するテンプレート・画像が自動コピー
- 既に存在するファイルは上書きされない（ユーザーの手動編集を保護）
- ファイルコピー状況は `logs/app.log` に記録される

**手動コピーは不要です。**

## ディレクトリ構成

```
Asset/
├── templates/              # テンプレート保管所
│   ├── default/           # デフォルト用テンプレート
│   ├── youtube/           # YouTube 関連（YouTube API/Live プラグイン用）
│   ├── niconico/          # ニコニコ関連（ニコニコプラグイン用）
│   └── twitch/            # Twitch 関連（将来予定）
├── images/                # 画像保管所
│   ├── default/           # デフォルト画像
│   ├── YouTube/           # YouTube 画像保管先
│   ├── Niconico/          # ニコニコ画像保管先
│   └── Twitch/            # Twitch 画像保管先
└── README.md              # このファイル
```

## 自動配置時のディレクトリ名規則

Asset から本番ディレクトリへ配置される際、以下のルールに従います：

**テンプレート:** 小文字で統一
- `Asset/templates/default/` → `templates/default/`
- `Asset/templates/youtube/` → `templates/youtube/`
- `Asset/templates/niconico/` → `templates/niconico/`
- `Asset/templates/twitch/` → `templates/twitch/`

**画像:** default画像以外は大文字始まりで統一（image_manager.py の仕様）
- `Asset/images/default/` → `images/default/`
- `Asset/images/YouTube/` → `images/YouTube/`
- `Asset/images/Niconico/` → `images/Niconico/`
- `Asset/images/Twitch/` → `images/Twitch/`

> ℹ️ **ディレクトリ名の大文字小文字は厳密に統一されており、v2 の image_manager.py 仕様に準拠

## 対応プラグイン別の配置

| プラグイン | テンプレート | 画像 |
|-----------|-----------|------|
| `youtube_api_plugin` | `templates/youtube/` | `images/YouTube/` |
| `youtube_live_plugin` | `templates/youtube/` | `images/YouTube/` |
| `niconico_plugin` | `templates/niconico/` | `images/Niconico/` |

## 手動で追加・カスタマイズする場合

1. Asset ディレクトリに新しいテンプレート・画像を追加
2. アプリケーションを再起動（または プラグインを再ロード）
3. 自動コピーされる

カスタマイズしたテンプレートは `templates/` または `images/` ディレクトリに直接編集してください。

## トラブルシューティング

### ファイルがコピーされない場合
- `logs/app.log` を確認してエラーメッセージを確認
- Asset ディレクトリが正しい場所にあるか確認
- プラグインが正しくロードされているか確認

### 古いファイルが残っている場合
- Asset から再コピーしたい場合は、既存ファイルを削除してから再起動
- または手動で `templates/` または `images/` から該当ファイルを削除

## ライセンス

**このリポジトリ全体は GPLv2 です。詳細はルートの LICENSE を参照してください。**

このディレクトリ内のすべてのアセット（テンプレート、画像、ドキュメント）は、親リポジトリの GPLv2 ライセンスの対象です。
