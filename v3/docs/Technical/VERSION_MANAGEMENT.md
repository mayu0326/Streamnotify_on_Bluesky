# バージョン管理ガイド (v3.0.0)

StreamNotify on Bluesky v3 のバージョン管理は、**3層の階層構造**で実装されています。

## 📊 バージョン管理の階層構造

```
┌─────────────────────────────────────────┐
│  アプリケーション レベル (v3.0.0)      │
│       app_version.py                    │
│  - 全体の統一バージョン                 │
│  - リリース日、ステータス管理           │
│  - Git コミット・ブランチ情報（CI/CD用） │
└─────────────────────────────────────────┘
              ↓
   ┌─────────────────┬─────────────────┐
   ↓                 ↓
┌──────────────────┐  ┌──────────────────┐
│ モジュール        │  │ プラグイン        │
│ (内部ライブラリ)  │  │ (拡張機能)        │
├──────────────────┤  ├──────────────────┤
│ image_manager    │  │ logging_plugin   │
│ bluesky_core     │  │ bluesky_plugin   │
│                  │  │ youtube_api_plugin
│ 各々が独立した    │  │ youtube_live_plugin
│ バージョンを管理  │  │ niconico_plugin
│                  │  │
│ 独立した機能追加  │  │ 各々が独立した
│ で更新            │  │ バージョンを管理
└──────────────────┘  └──────────────────┘
```

---

## 1️⃣ アプリケーション レベル

### ファイル: `app_version.py`

アプリケーション全体の統一バージョン情報を管理します。

```python
__version__ = "2.1.0"                    # セマンティックバージョニング
__release_date__ = "2025-12-17"         # リリース日
__status__ = "development"               # development/alpha/beta/stable
__author__ = "mayuneco(mayunya)"
__license__ = "GPLv3"

# CI/CD で自動設定（Git タグ作成時）
__git_commit__ = ""                      # GitコミットハッシュSHA1
__git_branch__ = ""                      # Gitブランチ名
```

### 提供される関数

#### `get_version_info() -> str`
```python
from app_version import get_version_info

version_str = get_version_info()
# 戻り値例: "v3.1.0 (2025-12-17) [development]"
```

#### `get_full_version_info() -> dict`
```python
from app_version import get_full_version_info

full_info = get_full_version_info()
# {
#     "version": "2.1.0",
#     "release_date": "2025-12-17",
#     "status": "development",
#     "author": "mayuneco(mayunya)",
#     "license": "GPLv3",
#     "git_commit": "abc1234...",
#     "git_branch": "feature/local",
#     "formatted": "v3.1.0 (2025-12-17) [development]"
# }
```

### 出力例（main_v3.py での使用）

```
StreamNotify on Bluesky v3.1.0 (2025-12-17) [development]
```

### セマンティックバージョニング規則

```
v[MAJOR].[MINOR].[PATCH]

- MAJOR: 大規模な機能追加・API 変更・アーキテクチャ変更
  例) v3.x.x → v3.x.x

- MINOR: 新機能追加（後方互換性あり）
  例) v3.0.x → v3.1.x

- PATCH: バグ修正・小規模改善
  例) v3.1.0 → v3.1.1
```

### ステータスの定義

| ステータス | 説明 | 出力例 |
|-----------|------|-------|
| `development` | 開発中 | `v3.1.0 (2025-12-17) [development]` |
| `alpha` | アルファ版 | `v3.1.0 (2025-12-17) [alpha]` |
| `beta` | ベータ版 | `v3.1.0 (2025-12-17) [beta]` |
| `stable` | 安定版 | `v3.1.0 (2025-12-17)` |

---

## 2️⃣ モジュール レベル

内部ライブラリとして機能するモジュールは、独立したバージョン管理を採用します。

### bluesky_core.py

```python
__version__ = "1.0.0"
__author__ = "mayuneco(mayunya)"
__copyright__ = "Copyright (C) 2025 mayuneco(mayunya)"
__license__ = "GPLv3"
```

**役割**: Bluesky コア機能（ポスト、Rich Text Facet、認証、DRY RUN）

**バージョン更新**:
- `1.0.0` → `1.1.0` : 新しい API フィーチャー実装時
- `1.0.0` → `1.0.1` : バグ修正時

### image_manager.py

```python
__version__ = "1.0.0"
__author__ = "mayuneco(mayunya)"
__copyright__ = "Copyright (C) 2025 mayuneco(mayunya)"
__license__ = "GPLv3"
```

**役割**: サムネイル画像取得・管理、画像情報検出

**バージョン更新**:
- `1.0.0` → `1.1.0` : 新しい画像取得機能追加時
```python
import image_manager
import bluesky_core

# バージョン確認
print(image_manager.__version__)  # 1.0.0
print(bluesky_core.__version__)   # 1.0.0
```

---

## 3️⃣ プラグイン レベル

各プラグインは `get_version()` メソッドで独立したバージョンを管理します。

### プラグイン一覧と現在のバージョン

| プラグイン | バージョン | 機能 |
|-----------|:--------:|------|
| **logging_plugin** | 2.0.0 | 複数ロガー、日次ローテーション、環境変数制御 |
| **bluesky_plugin** | 1.1.0 | Bluesky 画像添付、投稿テンプレート拡張 |
| **youtube_api_plugin** | 0.2.0 | YouTube チャンネルID 解決、動画詳細取得、API クォータ管理 |
| **youtube_live_plugin** | 0.2.0 | YouTube ライブ・アーカイブ判定 |
| **niconico_plugin** | 0.4.0 | ニコニコ動画 RSS 取得、ユーザー名自動取得・自動保存、リトライ・タイムアウト対応 |

### 実装例：logging_plugin

```python
class LoggingPlugin(NotificationPlugin):
    """ロギング拡張プラグイン"""

    def get_name(self) -> str:
        return "ロギング設定拡張プラグイン"

    def get_version(self) -> str:
        return "2.0.0"

    def get_description(self) -> str:
        return "旧版の高機能なロギング設定を提供..."
```

### 利用方法

```python
from plugins.logging_plugin import get_logging_plugin

plugin = get_logging_plugin()
print(f"{plugin.get_name()} v{plugin.get_version()}")
# 出力: ロギング設定拡張プラグイン v3.0.0
```

### プラグインマネージャーでの表示

```python
from plugin_manager import PluginManager

manager = PluginManager()
for plugin in manager.enabled_plugins:
    print(f"✅ {plugin.get_name()} v{plugin.get_version()}")
```

出力例:
```
✅ ロギング設定拡張プラグイン v3.0.0
✅ Bluesky 機能拡張プラグイン v1.1.0
✅ YouTubeAPI 連携プラグイン v0.2.0
✅ YouTubeLive 検出プラグイン v0.2.0
✅ ニコニコ動画 RSS取得プラグイン v0.3.0
```

---

## 📝 バージョン更新ガイドライン

### 更新タイミング

1. **新機能追加** → **MINOR** を +1
   ```
   例) logging_plugin: 2.0.0 → 2.1.0（新しいロガー追加）
   ```

2. **バグ修正・小規模改善** → **PATCH** を +1
   ```
   例) youtube_api_plugin: 0.2.0 → 0.2.1（タイムアウト処理改善）
   ```

3. **大規模リファクタリング・API 変更** → **MAJOR** を +1
   ```
   例) bluesky_plugin: 1.1.0 → 2.0.0（投稿フロー大幅変更）
   ```

### 更新手順

#### 2. プラグインのバージョン更新

**例: niconico_plugin で機能改善**

```python
# plugins/niconico_plugin.py

class NiconicoPlugin(NotificationPlugin):
    """ニコニコ動画 RSS取得プラグイン"""

    def get_version(self) -> str:
        return "0.4.0"  # 0.3.0 → 0.4.0

    def get_description(self) -> str:
        return "ニコニコ動画の新着を RSS 監視（キャッシュ機能追加）"
```

#### 3. アプリケーションのバージョン更新

**例: 複数のプラグイン・モジュール更新後**

```python
# app_version.py

__version__ = "2.2.0"          # 2.1.0 → 2.2.0
__release_date__ = "2025-12-25"  # 更新日
__status__ = "development"
```

### チェックリスト

- [ ] 対象ファイルのバージョン番号を更新
- [ ] `__version__` または `get_version()` を修正
- [ ] 機能説明（docstring、get_description）を更新
- [ ] テストで動作確認
- [ ] Git に commit & push
- [ ] 関連ドキュメント（FUTURE_ROADMAP など）を更新

---

## 🔄 CI/CD とバージョン管理

### 現在の状態（v3.1.0）

- ✅ アプリケーションバージョン機能実装完了
- ✅ モジュール独立バージョン管理実装完了
- ✅ プラグイン独立バージョン管理実装完了
- ⏳ CI/CD 自動更新（Git タグ作成時）は後で実装予定

### 将来の CI/CD 統合（予定）

Git タグ作成時に自動でこれらを実行：

```bash
# Git タグ作成
git tag -a v3.2.0 -m "v3.2.0 release"

# 自動処理（CI/CD パイプライン）
1. app_version.py の __version__ 自動更新
2. __git_commit__、__git_branch__ 自動設定
3. CHANGELOG 自動生成
4. リリースノート作成
```

---

## 📚 関連ドキュメント

- [ARCHITECTURE_AND_DESIGN.md](./ARCHITECTURE_AND_DESIGN.md) - アーキテクチャ全体（統合版）
- [PLUGIN_SYSTEM.md](./PLUGIN_SYSTEM.md) - プラグインシステム（統合版）
- [FUTURE_ROADMAP_v3.md](../References/FUTURE_ROADMAP_v3.md) - 開発予定

---

## 📞 質問・トラブルシューティング

### Q: 各プラグインのバージョンが異なるのはなぜ？

**A:** 各プラグインは独立して開発・更新されるため、異なるバージョンを持つことは正常です。  \
これにより、特定のプラグインだけを更新・改善することが可能になります。

### Q: アプリケーションバージョンとプラグインバージョンの関係は？

**A:**
- **アプリケーション (app_version.py)**: 全体の統一バージョン。リリース時に管理
- **プラグイン**: 個別の機能コンポーネント。独立して更新可能

例えば、アプリケーション v3.1.0 には、logging_plugin v3.0.0 と bluesky_plugin v1.1.0 が含まれています。

### Q: バージョン更新時の命名規則は？

**A:** セマンティックバージョニング (Semantic Versioning) を採用：
- `v[MAJOR].[MINOR].[PATCH]`
- 例) `v3.1.0`、`1.1.0`、`0.3.0`

---

**最終更新**: 2025-12-17 (v3.1.0)
