# AUTOPOST Logic Documentation - Quick Reference

**Date:** 2025年12月20日
**Version:** v3.3.0
**Status:** ✅ 仕様v1.0対応・検証済み

> **注意**: このドキュメントは簡易版です。詳細は以下を参照してください：
> - [AUTOPOST_SELFPOST_機能仕様書.md](./AUTOPOST_SELFPOST_機能仕様書.md) - 仕様v1.0（必読）
> - [COMPREHENSIVE_AUTOPOST_LOGIC.md](./COMPREHENSIVE_AUTOPOST_LOGIC.md) - 包括的な解析ドキュメント

---

## 概要

v3 の Autopost 機能は、複数のプラットフォーム（YouTube、YouTubeLive、Niconico）から動画・配信情報を自動収集し、設定に基づいて Bluesky に自動投稿する機能を提供します。

### 対応プラットフォーム

| プラットフォーム | プラグイン | 機能 | Autopost |
|:--|:--|:--|:--:|
| YouTube | `youtube_api_plugin` | 新着動画検出 | ✅ |
| YouTubeLive | `youtube_live_plugin` | ライブ/アーカイブ判定・自動投稿 | ✅ |
| Niconico | `niconico_plugin` | RSS監視・新着投稿 | ✅ |

---

## 動作モード（4種類・仕様v1.0）

### SELFPOST（完全手動投稿モード）
- 設定: `APP_MODE=selfpost`
- 動作: RSS 取得 + **GUI での手動投稿**
- 用途: ユーザーが GUI 操作で投稿対象を選択・確認してから投稿
- 特徴: AUTOPOST ロジックは一切実行されない（完全手動制御）

### AUTOPOST（完全自動投稿モード）
- 設定: `APP_MODE=autopost` + AUTOPOST 環境変数設定
- 動作: RSS 取得 + **自動投稿**（設定ルールのみで制御）
- 用途: 投稿を完全に自動化したい場合
- 特徴: 人間の介入なし、安全弁機構による抑止あり
- 環境変数:
  - `AUTOPOST_INTERVAL_MINUTES`: 投稿間隔（デフォルト: 5分）
  - `AUTOPOST_LOOKBACK_MINUTES`: 安全チェック時間窓（デフォルト: 30分）
  - `AUTOPOST_UNPOSTED_THRESHOLD`: 未投稿動画の安全上限（デフォルト: 20件）
  - `AUTOPOST_INCLUDE_NORMAL`/`SHORTS`/`MEMBER_ONLY`/`PREMIERE`: 投稿対象フィルタ

### DRY_RUN（テストモード）
- 設定: `APP_MODE=dry_run`
- 動作: RSS 取得 + **投稿シミュレーション**（実投稿なし）
- 用途: 投稿内容確認・動作テスト
- 特徴: Bluesky に実際には投稿しない

### COLLECT（収集専用）
- 設定: `APP_MODE=collect` または DB 未作成
- 動作: **RSS 取得のみ**（投稿機能完全オフ）
- 用途: 動画情報の収集フェーズのみ
- 特徴: GUI の投稿ボタンがすべて無効化される

---

## YouTubeLive イベント投稿

### ステージ 1: スケジュール（予定）
- **データ**: RSS で検知、キャッシュに登録
- **DB 状態**: `live_status="upcoming"`, `content_type="live"`

### ステージ 2: 開始
- **検知**: API ポーリングで `live_status="live"` を確認
- **自動投稿**: `yt_online_template.txt` で投稿
- **設定**: `YOUTUBE_LIVE_AUTO_POST_MODE` が "all" または "schedule" の場合に有効

### ステージ 3: 終了
- **検知**: API ポーリングで `live_status="completed"` を確認
- **自動投稿**: `yt_offline_template.txt` で投稿
- **設定**: `YOUTUBE_LIVE_AUTO_POST_MODE` が "all" または "live" の場合に有効
- **ポーリング間隔**: `YOUTUBE_LIVE_POLL_INTERVAL=15` (分、15～60分範囲)
- **注記**: ポーリングは MODE が "all" または "live" の場合のみ実行

### ステージ 4: アーカイブ
- **判定**: 配信終了後、公開されたアーカイブを検知
- **DB 状態**: `content_type="archive"`, `live_status=null`
- **投稿**: `yt_archive_template.txt` で投稿
- **設定**: `YOUTUBE_LIVE_AUTO_POST_MODE` が "all" または "archive" の場合に投稿

---

## YouTube Live 統合MODE制御（仕様v1.0）

`YOUTUBE_LIVE_AUTO_POST_MODE` で5段階制御：

| MODE | 予約枠 | 配信開始 | 配信終了 | アーカイブ | 用途 |
|:--|:--:|:--:|:--:|:--:|:--|
| `all` | ✅ | ✅ | ✅ | ✅ | すべてのイベントを投稿 |
| `schedule` | ✅ | ✅ | ❌ | ❌ | 配信告知・開始のみ投稿 |
| `live` | ❌ | ✅ | ✅ | ❌ | 配信開始・終了のみ投稿 |
| `archive` | ❌ | ❌ | ❌ | ✅ | アーカイブ公開のみ投稿 |
| `off` | ❌ | ❌ | ❌ | ❌ | YouTube Live 投稿を行わない |

**ポーリング有効条件**: MODE が "all" または "live" の場合のみポーリングが実行される

---

## Niconico 自動投稿

### RSS 監視フロー
1. **定期取得**: RSS フィードを `NICONICO_POLL_INTERVAL` 間隔で取得
2. **新着判定**: 前回の `last_video_id` と比較
3. **DB 登録**: 新着動画を自動的に DB に保存
4. **テンプレート投稿**: `nico_new_video_template.txt` で投稿

### 設定
```env
NICONICO_USER_ID=              # 監視対象ユーザーID
NICONICO_USER_NAME=            # 表示名（自動取得/手動指定）
NICONICO_POLL_INTERVAL=10 # ポーリング間隔（分）
TEMPLATE_NICO_NEW_VIDEO_PATH=  # テンプレートパス
```

---

## 画像管理（autopost モード専用）

### ディレクトリ構造
```
images/
├── YouTube/
│   ├── autopost/              ← autopost 専用
│   │   ├── video1.jpg
│   │   └── video2.jpg
├── Niconico/
│   ├── autopost/
│   │   └── ...
└── default/
    └── noimage.png
```

### 実装
- **ファイル**: `image_manager.py`
- **モード**: `"autopost"` / `"import"`
- **保存先**: `images/{site}/autopost/{filename}`

---

## プラグインインターフェース

すべてのプラグインが実装すべき抽象インターフェース:

```python
class NotificationPlugin(ABC):
    def is_available(self) -> bool:
        """プラグインが利用可能かどうかを判定"""

    def post_video(self, video: Dict[str, Any]) -> bool:
        """動画情報を投稿"""

    def get_name(self) -> str:
        """プラグイン名"""

    def get_version(self) -> str:
        """プラグインバージョン"""
```

---

## 重要なファイル

| ファイル | 役割 |
|:--|:--|
| `config.py` | 動作モード判定・設定管理 |
| `plugin_manager.py` | プラグイン管理・post_video 統合実行 |
| `plugins/youtube_live_plugin.py` | YouTubeLive 検知・自動投稿 |
| `plugins/niconico_plugin.py` | Niconico RSS 監視・自動投稿 |
| `plugins/bluesky_plugin.py` | Bluesky 投稿（テンプレート・画像） |
| `image_manager.py` | 画像管理（autopost モード専用） |
| `database.py` | 動画情報永続化 |
| `youtube_live_cache.py` | ライブキャッシュ管理 |
| `main_v3.py` | 全体初期化・スレッド管理 |

---

## 環境変数（重要な設定・仕様v1.0準拠）

```env
# 動作モード（仕様v1.0）
APP_MODE=selfpost                       # selfpost/autopost/dry_run/collect

# YouTube
YOUTUBE_CHANNEL_ID=UC...                # 監視対象チャンネル
YOUTUBE_API_KEY=...                     # YouTube Data API キー（オプション）

# YouTubeLive（仕様v1.0・統合MODE制御）
YOUTUBE_LIVE_AUTO_POST_MODE=all         # all/schedule/live/archive/off
YOUTUBE_LIVE_POLL_INTERVAL=15           # ポーリング間隔（15～60分、MODE="all"|"live"時のみ有効）

# AUTOPOST 環境変数（APP_MODE=autopost 時）
AUTOPOST_INTERVAL_MINUTES=5             # 投稿間隔（分、範囲: 1-60）
AUTOPOST_LOOKBACK_MINUTES=30            # 安全チェック時間窓（分、範囲: 5-1440）
AUTOPOST_UNPOSTED_THRESHOLD=20          # 未投稿動画安全上限（件、範囲: 1-1000）
AUTOPOST_INCLUDE_NORMAL=true            # 通常動画を投稿
AUTOPOST_INCLUDE_SHORTS=false           # YouTube Shorts を投稿
AUTOPOST_INCLUDE_MEMBER_ONLY=false      # メンバー限定動画を投稿
AUTOPOST_INCLUDE_PREMIERE=true          # プレミア配信を投稿

# Niconico
NICONICO_USER_ID=...                    # 監視対象ユーザーID
NICONICO_POLL_INTERVAL=10          # ポーリング間隔（分）

# Bluesky
BLUESKY_USERNAME=...                    # ハンドル名
BLUESKY_PASSWORD=...                    # アプリパスワード
BLUESKY_POST_ENABLED=true               # 投稿機能有効化

# テンプレート
TEMPLATE_YOUTUBE_NEW_VIDEO_PATH=...
TEMPLATE_YOUTUBE_ONLINE_PATH=...
TEMPLATE_YOUTUBE_OFFLINE_PATH=...
TEMPLATE_YOUTUBE_ARCHIVE_PATH=...
TEMPLATE_NICO_NEW_VIDEO_PATH=...
```

---

## 参考ドキュメント

📚 **AUTOPOST/SELFPOST 仕様**:
- [AUTOPOST_SELFPOST_機能仕様書.md](./AUTOPOST_SELFPOST_機能仕様書.md) ⭐ **仕様v1.0（必読）**

📚 **詳細な実装ドキュメント**:
- [COMPREHENSIVE_AUTOPOST_LOGIC.md](./COMPREHENSIVE_AUTOPOST_LOGIC.md) ⭐ **推奨**（詳細な実装解析）
- [PLUGIN_SYSTEM.md](./PLUGIN_SYSTEM.md)（プラグインシステム）
- [TEMPLATE_SYSTEM.md](./TEMPLATE_SYSTEM.md)（テンプレートシステム）
- [SETTINGS_OVERVIEW.md](./SETTINGS_OVERVIEW.md)（設定項目一覧）

---

**更新日**: 2025年12月20日
**仕様版**: v1.0
**ステータス**: ✅ 仕様v1.0対応・完全準拠
