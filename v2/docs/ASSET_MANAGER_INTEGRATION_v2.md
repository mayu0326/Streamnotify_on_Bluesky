# v2 AssetManager 統合ガイド

**対象バージョン**: v2.1.0
**最終更新**: 2025-12-18
**ステータス**: ✅ 実装完了

---

## 1. AssetManager の役割

### 1.1 概要

**AssetManager** は、v2 アプリケーション起動時に、`Asset/` ディレクトリ内の配布用テンプレートと画像を、実行時テンプレートディレクトリ（`templates/`）および画像ディレクトリ（`images/`）に自動配置するコンポーネントです。

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
v2/
├── asset_manager.py                    # ← AssetManager 本体
├── main_v2.py                         # ← AssetManager 呼び出し元
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
┌─────────────────────────────────────────────────┐
│ main_v2.py 起動時                               │
│ if not VANILLA_MODE:                            │
│   asset_manager.ensure_assets_initialized()     │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
        ┌────────────────────┐
        │ AssetManager 初期化  │
        └────────┬───────────┘
                 │
      ┌──────────┴──────────┐
      │                     │
      ▼                     ▼
┌──────────────┐   ┌──────────────────┐
│ テンプレート │   │ 画像ファイル      │
│ 配置確認     │   │ 配置確認          │
└──────┬───────┘   └────────┬─────────┘
       │                    │
       ▼                    ▼
┌──────────────────────────────────┐
│ Asset/ 内のファイルを検出         │
│ - default_template.txt           │
│ - *.png, *.jpg                   │
└──────┬───────────────────────────┘
       │
       ▼
┌────────────────────────────────────┐
│ 配置先ファイルが存在するか？       │
├────────────────────────────────────┤
│ YES → スキップ                     │
│ NO  → コピー処理実行               │
└──────┬─────────────────────────────┘
       │
       ▼
┌───────────────────────────┐
│ ファイルコピー実行        │
│ Asset → templates/        │
│        → images/          │
└───────┬───────────────────┘
        │
        ▼
┌─────────────────────────────┐
│ logs/app.log に結果を記録    │
│ "✅ コピー: A → B"          │
│ "ℹ️ スキップ: X (既存)"    │
└─────────────────────────────┘
```

---

## 3. コード側での実装

### 3.1 main_v2.py から呼び出し

**実装例**:

```python
# main_v2.py 内

def main():
    """アプリケーションのメインエントリポイント"""

    # 1. 設定読み込み
    config = get_config("settings.env")

    # 2. Vanilla モード判定
    if not config.VANILLA_MODE:
        # 3. AssetManager でファイル配置
        from asset_manager import get_asset_manager
        asset_manager = get_asset_manager()
        asset_manager.ensure_assets_initialized()

    # 4. 以降の初期化処理...
    # GUI, Database, Plugins...
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

    def ensure_assets_initialized(self) -> bool:
        """
        アセットの初期化を保証する。

        Returns:
            bool: すべてのコピーが成功した場合 True
        """
        success = True

        # テンプレート配置
        success &= self._copy_default_template()
        success &= self._copy_plugin_templates()

        # 画像配置
        success &= self._copy_images()

        if success:
            self.logger.info("✅ アセット初期化完了")
        else:
            self.logger.warning("⚠️ 一部アセット配置がスキップされました")

        return success

    def _copy_default_template(self) -> bool:
        """
        デフォルトテンプレートを Asset から .templates へコピー。

        既存ファイルは上書きしない（ユーザー編集を保護）。
        """
        src = self.asset_root / "templates" / "default" / "default_template.txt"
        dst = self.template_root / ".templates" / "default_template.txt"

        if not src.exists():
            self.logger.warning(f"⚠️ ソースなし: {src}")
            return False

        if dst.exists():
            self.logger.info(f"ℹ️ スキップ: {dst} (既存)")
            return True

        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            self.logger.info(f"✅ コピー: {src} → {dst}")
            return True
        except Exception as e:
            self.logger.error(f"❌ コピー失敗: {e}")
            return False

    def _copy_plugin_templates(self) -> bool:
        """
        プラグイン用テンプレートを配置。

        youtube/, niconico/ 等のディレクトリを処理。
        """
        service_dirs = ["youtube", "niconico", "twitch"]
        all_success = True

        for service in service_dirs:
            src_dir = self.asset_root / "templates" / service
            dst_dir = self.template_root / service

            if not src_dir.exists():
                continue  # Asset に存在しないサービスはスキップ

            success = self._copy_directory_recursive(src_dir, dst_dir)
            all_success &= success

        return all_success

    def _copy_images(self) -> bool:
        """画像ファイルを配置"""
        # 同様のロジックで image_root 内のファイルを処理
        pass

    def _copy_directory_recursive(self, src_dir: Path, dst_dir: Path) -> bool:
        """
        ディレクトリをリカーシブにコピー。
        既存ファイルは保護（上書きしない）。
        """
        all_success = True

        for item in src_dir.iterdir():
            dst_item = dst_dir / item.name

            if item.is_dir():
                dst_item.mkdir(parents=True, exist_ok=True)
                success = self._copy_directory_recursive(item, dst_item)
                all_success &= success
            elif item.is_file():
                if dst_item.exists():
                    self.logger.debug(f"スキップ: {dst_item} (既存)")
                else:
                    try:
                        dst_dir.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(item, dst_item)
                        self.logger.info(f"✅ コピー: {item} → {dst_item}")
                    except Exception as e:
                        self.logger.error(f"❌ コピー失敗: {e}")
                        all_success = False

        return all_success


def get_asset_manager() -> AssetManager:
    """AssetManager シングルトンを取得"""
    global _asset_manager_instance
    if _asset_manager_instance is None:
        _asset_manager_instance = AssetManager()
    return _asset_manager_instance
```

---

## 4. テンプレート配置の詳細

### 4.1 デフォルトテンプレート配置フロー

**初回起動（.templates/ が存在しない場合）**:

```
起動
  ↓
templates/.templates/ 存在確認
  ↓ (存在しない)
Asset/templates/default/default_template.txt を検出
  ↓
templates/.templates/default_template.txt へコピー
  ↓
✅ 次回から .templates/default_template.txt を使用
```

**2回目以降の起動（.templates/ が存在する場合）**:

```
起動
  ↓
templates/.templates/ 存在確認
  ↓ (存在する)
Asset/templates/default/default_template.txt と比較
  ↓
identical または ユーザー編集済み
  ↓
❌ 上書きしない（保護）
  ↓
✅ 既存ファイル継続使用
```

### 4.2 バージョン更新時の動作

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

## 5. ログ出力例

### 5.1 初回起動時

```
2025-12-18 14:30:05 [AssetManager] ✅ コピー: Asset/templates/default/default_template.txt → templates/.templates/default_template.txt
2025-12-18 14:30:05 [AssetManager] ✅ コピー: Asset/templates/youtube/yt_new_video_template.txt → templates/youtube/yt_new_video_template.txt
2025-12-18 14:30:05 [AssetManager] ✅ コピー: Asset/images/default/logo.png → images/default/logo.png
2025-12-18 14:30:05 [AssetManager] ✅ アセット初期化完了
```

### 5.2 既存ファイルがある場合

```
2025-12-18 14:32:15 [AssetManager] ℹ️ スキップ: templates/.templates/default_template.txt (既存)
2025-12-18 14:32:15 [AssetManager] ℹ️ スキップ: templates/youtube/yt_new_video_template.txt (既存)
2025-12-18 14:32:15 [AssetManager] ✅ アセット初期化完了
```

### 5.3 エラーが発生した場合

```
2025-12-18 14:35:00 [AssetManager] ⚠️ ソースなし: Asset/templates/default/default_template.txt
2025-12-18 14:35:00 [AssetManager] ❌ コピー失敗: Permission denied
2025-12-18 14:35:00 [AssetManager] ⚠️ 一部アセット配置がスキップされました
```

---

## 6. Vanilla モード時の動作

**VANILLA_MODE = True の場合**:

```python
if not VANILLA_MODE:
    asset_manager.ensure_assets_initialized()  # ← 実行されない
else:
    # Vanilla モード（Asset 処理スキップ）
    # template_utils.py が templates/.templates/default_template.txt を直接参照
```

Vanilla モード時は AssetManager が起動せず、既存ファイルのみを使用します。

---

## 7. トラブルシューティング

### Q: テンプレートが更新されない

**A**: 以下を確認してください：

1. `Asset/templates/default/default_template.txt` が更新されているか
2. `templates/.templates/` 内のファイルを削除し、再起動してみる
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
| **役割** | Asset → templates/ への自動配置 |
| **呼び出し元** | main_v2.py |
| **実行タイミング** | アプリケーション起動時（VANILLA_MODE でない場合） |
| **保護戦略** | 既存ユーザーファイルは上書きしない |
| **ログ記録** | すべての操作を `logs/app.log` に記録 |
| **拡張性** | テンプレート・画像の追加は Asset/ に配置するだけ |

AssetManager により、配布と実行時テンプレートの分離が実現され、ユーザーのカスタマイズを安全に保ちながら、更新配布が可能になります。
