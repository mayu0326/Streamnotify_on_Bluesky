# v3 AssetManager 統合ガイド

**対象バージョン**: v3.1.0
**最終更新**: 2025-12-18
**ステータス**: ✅ 実装完了

---

## 1. AssetManager の役割

### 1.1 概要

**AssetManager** は、v3 アプリケーション起動時に、`Asset/` ディレクトリ内の配布用テンプレートと画像を、実行時テンプレートディレクトリ（`templates/`）および画像ディレクトリ（`images/`）に自動配置するコンポーネントです。

### 1.2 主な責務

- ✅ **初期テンプレート配置**: デフォルトテンプレートを `Asset/templates/default/` から `templates/.templates/` へコピー
- ✅ **プラグイン導入時の配置**: プラグイン有効化時に、対応テンプレート・画像を自動配置
- ✅ **既存ファイル保護**: ユーザーが手動編集したテンプレートは上書きしない
- ✅ **ログ記録**: すべての配置操作を `logs/app.log` に記録

### 1.3 デザイン原則

| 原則 | 説明 |
|:--|:--|
| **非侵襲的** | ユーザーのカスタマイズテンプレートを上書きしない |
| **透過的** | 操作ログで何が配置されたかを追跡可能 |
| **遅延実行** | 不要な場合は処理を最小化 |
| **障害耐性** | ファイルコピー失敗時でもアプリケーション起動を妨げない |

---

## 2. アーキテクチャ

### 2.1 ファイル構成

```
v3/
├── asset_manager.py                    # ← AssetManager 本体
├── main_v3.py                         # ← AssetManager 呼び出し元
│
├── Asset/                             # 配布用ソースディレクトリ
│   ├── templates/
│   │   ├── default/
│   │   │   └── default_template.txt   # ← デフォルトテンプレート配布元
│   │   ├── youtube/
│   │   │   ├── yt_new_video_template.txt
│   │   │   ├── yt_online_template.txt    # 将来実装予定
│   │   │   └── yt_offline_template.txt   # 将来実装予定
│   │   ├── niconico/
│   │   │   └── nico_new_video_template.txt
│   │   └── twitch/                    # 将来実装予定
│   │       ├── twitch_online_template.txt
│   │       ├── twitch_offline_template.txt
│   │       └── twitch_raid_template.txt
│   └── images/
│       ├── default/
│       ├── YouTube/
│       └── Niconico/
│
├── templates/                         # 実行時テンプレートディレクトリ
│   ├── youtube/                       # ← ユーザーが編集
│   │   ├── yt_new_video_template.txt
│   │   ├── yt_online_template.txt
│   │   └── yt_offline_template.txt
│   ├── niconico/
│   │   └── nico_new_video_template.txt
│   └── .templates/                    # ← 共通フォールバック専用
│       └── default_template.txt       # ← Asset からコピー先
│
└── logs/
    └── app.log                        # ← 配置操作を記録
```

### 2.2 処理フロー

```
┌──────────────────────────────────────────────────┐
│ main_v3.py 起動時                                │
│ asset_manager = get_asset_manager()              │
└────────────────┬─────────────────────────────────┘
                 │
       ┌─────────┴──────────────┐
       │                        │
       ▼                        ▼
┌────────────────┐      ┌──────────────────┐
│ 自動ロード済み  │      │ 個別プラグイン   │
│ プラグイン     │      │ (YouTube等)      │
│ のアセット     │      │ のアセット配置   │
└────┬───────────┘      └────────┬─────────┘
     │                           │
     ▼                           ▼
┌────────────────────────────────────────┐
│ deploy_plugin_assets(plugin_name)      │
│ ↓                                      │
│ plugin_asset_map から対応を検出        │
│ - templates: ["youtube", "default"]   │
│ - images: ["YouTube", "default"]      │
└────┬───────────────────────────────────┘
     │
     ├─→ deploy_templates(services)  ┐
     │                               ├─→ _copy_directory_recursive()
     └─→ deploy_images(services)     ┘
     │
     ▼
┌──────────────────────────────────────┐
│ 既存ファイルをチェック               │
├──────────────────────────────────────┤
│ 存在する → スキップ（保護）         │
│ 存在しない → コピー実行              │
└────┬─────────────────────────────────┘
     │
     ▼
┌──────────────────────────────────────┐
│ ファイルコピー完了                   │
│ logs/app.log に記録                  │
│ "✅ コピー: A → B"                  │
│ "ℹ️ スキップ: X (既存)"            │
└──────────────────────────────────────┘
```

---

## 3. コード側での実装

### 3.1 main_v3.py から呼び出し

**実装例**:

```python
# main_v3.py 内（実装コード）

def main():
    """アプリケーションのメインエントリポイント"""

    # AssetManager の初期化（プラグイン導入時に資源を配置）
    asset_manager = get_asset_manager()
    logger.info("📦 Asset マネージャーを初期化しました")

    # 自動ロード済みプラグインのアセット配置
    plugin_files = [f for f in os.listdir("plugins")
                    if f.endswith(".py") and not f.startswith("_")
                    and f not in ("bluesky_plugin.py", "niconico_plugin.py", ...)]  # 例外除外

    for pf in plugin_files:
        plugin_name = pf[:-3]
        plugin_manager.load_plugin(plugin_name, os.path.join("plugins", pf))
        plugin_manager.enable_plugin(plugin_name)

        # プラグイン別のアセット配置
        try:
            asset_manager.deploy_plugin_assets(plugin_name)
        except Exception as e:
            logger.warning(f"プラグイン '{plugin_name}' のアセット配置失敗: {e}")

    # YouTubeAPI プラグイン配置
    try:
        plugin_manager.load_plugin("youtube_api_plugin", ...)
        plugin_manager.enable_plugin("youtube_api_plugin")
        asset_manager.deploy_plugin_assets("youtube_api_plugin")  # ← YouTube テンプレート配置
    except Exception as e:
        logger.debug(f"YouTubeAPI プラグインのロード失敗: {e}")

    # Bluesky プラグイン配置
    try:
        plugin_manager.load_plugin("bluesky_plugin", ...)
        plugin_manager.enable_plugin("bluesky_plugin")
        asset_manager.deploy_plugin_assets("bluesky_plugin")  # ← デフォルトテンプレート配置（ここで実行）
    except Exception as e:
        logger.debug(f"Bluesky プラグインのロード失敗: {e}")

    # 以後の初期化処理...
```

### 3.2 AssetManager の内部構造

**クラス定義**:

```python
class AssetManager:
    """
    Asset ディレクトリ内のテンプレート・画像を管理し、
    実行時ディレクトリへ自動配置する。
    """

    def __init__(self):
        self.asset_root = Path(__file__).parent / "Asset"
        self.template_root = Path(__file__).parent / "templates"
        self.image_root = Path(__file__).parent / "images"
        self.logger = get_logger("AssetManager")

    def deploy_templates(self, services: list = None) -> int:
        """
        テンプレートをコピー（サービス別）

        Asset/templates/ から templates/{service}/ へコピー。
        既存ファイルは上書きしない（ユーザー編集を保護）。

        Args:
            services: コピー対象のサービス一覧 (None = すべて)
                     例: ["youtube", "default", "niconico"]

        Returns:
            int: コピーしたファイル数
        """
        logger.debug("📋 テンプレートの配置を開始します...")
        copy_count = 0

        if services is None:
            # すべてのサービスをコピー
            services = []
            if self.templates_src.exists():
                services = [d.name for d in self.templates_src.iterdir() if d.is_dir()]

        for service in services:
            src_service_dir = self.templates_src / service
            dest_service_dir = self.templates_dest / service

            if not src_service_dir.exists():
                logger.debug(f"テンプレートディレクトリが見つかりません: {src_service_dir}")
                continue

            count = self._copy_directory_recursive(src_service_dir, dest_service_dir)
            copy_count += count
            if count > 0:
                logger.info(f"✅ [{service}] {count} 個のテンプレートをコピーしました")

        if copy_count == 0:
            logger.debug("テンプレートのコピー対象がありません")

        return copy_count

    def deploy_images(self, services: list = None) -> int:
        """
        画像をコピー（サービス別）

        Asset/images/ から images/{service}/ へコピー。
        サービス名は大文字始まり: default, YouTube, Niconico など
        既存ファイルは上書きしない。

        Args:
            services: コピー対象のサービス一覧 (None = すべて)
                     例: ["default", "YouTube", "Niconico"]

        Returns:
            int: コピーしたファイル数
        """
        logger.debug("🖼️  画像の配置を開始します...")
        copy_count = 0

        if services is None:
            # すべてのサービスをコピー
            services = []
            if self.images_src.exists():
                services = [d.name for d in self.images_src.iterdir() if d.is_dir()]

        for service in services:
            src_service_dir = self.images_src / service
            dest_service_dir = self.images_dest / service

            if not src_service_dir.exists():
                logger.debug(f"画像ディレクトリが見つかりません: {src_service_dir}")
                continue

            count = self._copy_directory_recursive(src_service_dir, dest_service_dir)
            copy_count += count
            if count > 0:
                logger.info(f"✅ [{service}] {count} 個の画像をコピーしました")

        if copy_count == 0:
            logger.debug("画像のコピー対象がありません")

        return copy_count

    def deploy_plugin_assets(self, plugin_name: str) -> dict:
        """
        プラグイン導入時に必要なアセットをコピー

        plugin_asset_map に従い、プラグイン別のテンプレート・画像を配置。

        Args:
            plugin_name: プラグイン名
                        例: "youtube_api_plugin", "niconico_plugin", "bluesky_plugin"

        Returns:
            dict: {"templates": コピー数, "images": コピー数}
        """
        logger.debug(f"🔌 プラグイン '{plugin_name}' のアセット配置を確認しています...")

        results = {"templates": 0, "images": 0}

        # プラグイン別のマッピング定義
        plugin_asset_map = {
            "youtube_live_plugin": {
                "templates": ["youtube"],
                "images": ["YouTube"],
            },
            "niconico_plugin": {
                "templates": ["niconico"],
                "images": ["Niconico"],
            },
            "bluesky_plugin": {
                "templates": ["default"],      # ← デフォルトテンプレート
                "images": ["default"],
            },
            "youtube_api_plugin": {
                "templates": ["youtube"],
                "images": ["YouTube"],
            },
        }

        if plugin_name not in plugin_asset_map:
            logger.debug(f"プラグイン '{plugin_name}' はアセット定義を持ちません")
            return results

        config = plugin_asset_map[plugin_name]

        # テンプレートをコピー
        if "templates" in config and config["templates"]:
            results["templates"] = self.deploy_templates(config["templates"])

        # 画像をコピー
        if "images" in config and config["images"]:
            results["images"] = self.deploy_images(config["images"])

        total = results["templates"] + results["images"]
        if total > 0:
            logger.info(f"✅ プラグイン '{plugin_name}' の {total} 個のアセットを配置しました")
        else:
            logger.debug(f"プラグイン '{plugin_name}' のアセットはすべて配置済みです")

        return results

    def deploy_all(self) -> dict:
        """
        すべてのテンプレート・画像をコピー

        Asset/ 配下のすべてのテンプレートと画像を templates/ と images/ に配置。

        Returns:
            dict: {"templates": コピー数, "images": コピー数}
        """
        logger.info("🚀 すべてのアセットを配置しています...")

        templates_count = self.deploy_templates()
        images_count = self.deploy_images()

        logger.info(
            f"✅ アセット配置完了: テンプレート {templates_count} 個、画像 {images_count} 個"
        )

        return {"templates": templates_count, "images": images_count}


def get_asset_manager(asset_dir="Asset", base_dir=".") -> AssetManager:
    """AssetManager インスタンスを取得"""
    return AssetManager(asset_dir=asset_dir, base_dir=base_dir)
```

### 3.3 実装済みメソッド一覧

| メソッド | 用途 | 呼ばれるタイミング |
|:--|:--|:--|
| `deploy_templates(services)` | サービス別テンプレート配置 | deploy_plugin_assets から |
| `deploy_images(services)` | サービス別画像配置 | deploy_plugin_assets から |
| `deploy_plugin_assets(plugin_name)` | プラグイン別アセット配置 | main_v3.py でプラグイン有効化時 |
| `deploy_all()` | 全アセット一括配置 | 必要に応じて手動呼び出し可能 |
| `_copy_directory_recursive(src, dst)` | ディレクトリ再帰コピー | deploy_templates/deploy_images から |
| `_copy_file(src, dst)` | 単一ファイルコピー | _copy_directory_recursive から |
| `_ensure_dest_dir(path)` | 宛先ディレクトリ作成 | _copy_file から |
```

---

## 4. プラグイン別アセットマッピング

### 4.1 plugin_asset_map の構造

**asset_manager.py 内の定義**:

```python
plugin_asset_map = {
    "youtube_live_plugin": {
        "templates": ["youtube"],
        "images": ["YouTube"],
    },
    "niconico_plugin": {
        "templates": ["niconico"],
        "images": ["Niconico"],
    },
    "bluesky_plugin": {
        "templates": ["default"],       # ← デフォルトテンプレート（全サービス共通フォールバック）
        "images": ["default"],
    },
    "youtube_api_plugin": {
        "templates": ["youtube"],
        "images": ["YouTube"],
    },
}
```

### 4.2 プラグイン別配置一覧

| プラグイン | テンプレート | 画像 | 配置先 | 備考 |
|:--|:--|:--|:--|:--|
| `youtube_live_plugin` | youtube/ | YouTube/ | templates/youtube/  images/YouTube/ | YouTube Live 検出用 |
| `youtube_api_plugin` | youtube/ | YouTube/ | templates/youtube/  images/YouTube/ | YouTube Data API 用 |
| `niconico_plugin` | niconico/ | Niconico/ | templates/niconico/  images/Niconico/ | ニコニコ対応 |
| `bluesky_plugin` | **default/** | default/ | templates/.templates/  images/default/ | **デフォルト（フォールバック）** |

### 4.3 デフォルトテンプレート配置タイミング

**重要**: デフォルトテンプレートは **Bluesky プラグイン有効化時**に配置されます

```
main_v3.py の実行順序
  ↓
自動ロード済みプラグイン処理
  ↓
YouTubeAPI プラグイン配置  (youtube/ テンプレート配置)
  ↓
YouTubeLive プラグイン配置  (youtube/ テンプレート配置)
  ↓
Bluesky プラグイン配置  ← ★ ここで default_template.txt が templates/.templates/ へコピーされる
  ↓
✅ 初期化完了
```

---

## 5. テンプレート配置の詳細

### 5.1 デフォルトテンプレート配置フロー

**Bluesky プラグイン有効化時（初回）**:

```
asset_manager.deploy_plugin_assets("bluesky_plugin")
  ↓
plugin_asset_map["bluesky_plugin"] から ["default"] を取得
  ↓
deploy_templates(["default"])
  ↓
Asset/templates/default/ → templates/.templates/ へコピー
  ↓
.templates/default_template.txt が存在するか確認
  ├─ YES（既存） → スキップ（保護）
  └─ NO（新規） → コピー実行
  ↓
✅ templates/.templates/default_template.txt が配置完了
```

**次回以降の起動（既存ファイルがある場合）**:

```
asset_manager.deploy_plugin_assets("bluesky_plugin")
  ↓
_copy_directory_recursive が実行
  ↓
.templates/default_template.txt 存在確認
  ├─ YES → dest.exists() = True → スキップ
  │ "ℹ️ スキップ: templates/.templates/default_template.txt (既存)"
  └─ NO → コピー
  ↓
✅ ユーザー編集ファイルは保護される
```

### 5.2 バージョン更新時の動作

**Asset 内のテンプレートが更新された場合**:

```
リポジトリ更新（git pull）
  ↓
Asset/templates/default/default_template.txt が新版
  ↓
起動時に AssetManager が検出
  ↓
templates/.templates/default_template.txt はユーザー編集済み
  ↓
❌ 上書きしない（ユーザーの設定を保護）
  ↓
⚠️ ログに「更新あり」を記録
```

**ユーザーが明示的に更新を希望する場合**:

```
1. templates/.templates/default_template.txt を削除
2. アプリケーション再起動
3. AssetManager が Asset から再コピー
4. ✅ 新版が適用される
```

---

## 6. ログ出力例

### 6.1 初回起動時（プラグイン別配置）

```
[INFO] 📦 Asset マネージャーを初期化しました

[DEBUG] 🔌 プラグイン 'youtube_api_plugin' のアセット配置を確認しています...
[DEBUG] 📋 テンプレートの配置を開始します...
[DEBUG] ✅ ファイルをコピーしました: yt_new_video_template.txt -> templates/youtube/yt_new_video_template.txt
[INFO] ✅ [youtube] 1 個のテンプレートをコピーしました
[DEBUG] 🖼️  画像の配置を開始します...
[DEBUG] ✅ ファイルをコピーしました: thumbnail.png -> images/YouTube/thumbnail.png
[INFO] ✅ [YouTube] 1 個の画像をコピーしました
[INFO] ✅ プラグイン 'youtube_api_plugin' の 2 個のアセットを配置しました

[DEBUG] 🔌 プラグイン 'bluesky_plugin' のアセット配置を確認しています...
[DEBUG] 📋 テンプレートの配置を開始します...
[DEBUG] ✅ ファイルをコピーしました: default_template.txt -> templates/.templates/default_template.txt
[INFO] ✅ [default] 1 個のテンプレートをコピーしました
[INFO] ✅ プラグイン 'bluesky_plugin' の 1 個のアセットを配置しました
```

### 6.2 既存ファイルがある場合（2回目起動）

```
[INFO] 📦 Asset マネージャーを初期化しました

[DEBUG] 🔌 プラグイン 'youtube_api_plugin' のアセット配置を確認しています...
[DEBUG] 📋 テンプレートの配置を開始します...
[DEBUG] 既に存在するため、スキップしました: templates/youtube/yt_new_video_template.txt
[DEBUG] テンプレートのコピー対象がありません
[DEBUG] 🖼️  画像の配置を開始します...
[DEBUG] 既に存在するため、スキップしました: images/YouTube/thumbnail.png
[DEBUG] 画像のコピー対象がありません
[DEBUG] プラグイン 'youtube_api_plugin' のアセットはすべて配置済みです

[DEBUG] 🔌 プラグイン 'bluesky_plugin' のアセット配置を確認しています...
[DEBUG] 📋 テンプレートの配置を開始します...
[DEBUG] 既に存在するため、スキップしました: templates/.templates/default_template.txt
[DEBUG] テンプレートのコピー対象がありません
[DEBUG] プラグイン 'bluesky_plugin' のアセットはすべて配置済みです
```

### 6.3 エラーが発生した場合

```
[WARNING] ディレクトリ作成失敗 templates/youtube: Permission denied
[WARNING] ファイルコピー失敗 Asset/templates/youtube/yt_new_video_template.txt -> templates/youtube/yt_new_video_template.txt: Permission denied
[WARNING] プラグイン 'youtube_api_plugin' のアセット配置失敗: Permission denied
```

---

## 7. トラブルシューティング

### Q: テンプレートが更新されない

**A**: 以下を確認してください：

1. `Asset/templates/` 内のテンプレートが更新されているか
2. プラグインが正しく有効化されているか
3. `logs/app.log` でエラーメッセージを確認

### Q: 既存テンプレートが上書きされた

**A**: AssetManager は既存ファイルを保護する設計ですが、意図的に上書きしたい場合：

1. `templates/.templates/` または該当ファイルを削除
2. アプリケーションを再起動
3. Asset からの自動配置が実行されます

### Q: ファイルコピーが失敗する

**A**: 以下を確認してください：

1. `Asset/` ディレクトリが存在し、読み取り権限があるか
2. `templates/` および `images/` ディレクトリに書き込み権限があるか
3. ディスク容量が不足していないか
4. ファイルがロックされていないか（別プロセスで開かれていない）

---

## 8. まとめ

| 項目 | 説明 |
|:--|:--|
| **役割** | Asset → templates/ への段階的自動配置 |
| **呼び出し元** | main_v3.py（プラグイン有効化時） |
| **実行タイミング** | プラグイン導入・有効化時に個別配置 |
| **配置方式** | `deploy_plugin_assets(plugin_name)` でプラグイン別に配置 |
| **デフォルト配置** | Bluesky プラグイン有効化時に実行 |
| **保護戦略** | 既存ユーザーファイルは上書きしない（`dest.exists()` チェック） |
| **ログ記録** | すべての操作を `logs/app.log` に記録 |
| **拡張性** | テンプレート・画像の追加は Asset/ に配置、plugin_asset_map に登録 |

AssetManager により、配布と実行時テンプレートの分離が実現され、以下が可能になります：
- 🔐 ユーザーのカスタマイズテンプレートを安全に保護
- 📦 プラグイン導入時に必要なアセットのみ自動配置
- 🔄 バージョン更新時に新テンプレート配布が容易
- 🛠️ 既存ユーザー環境への影響を最小化

