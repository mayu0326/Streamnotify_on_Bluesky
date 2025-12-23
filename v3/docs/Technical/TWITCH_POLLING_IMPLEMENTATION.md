# Twitch API ポーリング実装ガイド

**対象バージョン**: v3.x
**最終更新**: 2025-12-23
**ステータス**: 📐 設計文書（実装準備段階）
**設計思想**: ローカル完結・シンプル設定（Webhook/EventSub は不採用）

---

## 📖 目次

1. [概要](#概要)
2. [設計方針](#設計方針)
3. [Helix API 仕様](#helix-api-仕様)
4. [実装アーキテクチャ](#実装アーキテクチャ)
5. [プラグイン実装案](#プラグイン実装案)
6. [環境変数設定](#環境変数設定)
7. [動作フロー](#動作フロー)
8. [トラブルシューティング](#トラブルシューティング)

---

## 概要

### なぜ Webhook/EventSub ではなくポーリングか

| 方式 | 遅延 | インフラ | 複雑度 | 本アプリ採用 |
|:--|:--:|:--:|:--:|:--:|
| **EventSub (Webhook)** | 秒単位 | VPS 必須 | 高 | ❌ |
| **API ポーリング** | 3-5分 | 不要 | 低 | ✅ |

**採用理由**:
- ✅ ユーザーが VPS を契約する必要がない
- ✅ セキュリティ複雑さ（Webhook 署名検証）不要
- ✅ クライアント単体で完結
- ✅ YouTube RSS と同じ設計で統一できる
- ❌ リアルタイム性は諦める（3-5分遅延は許容）

---

## 設計方針

### Twitch 配信監視の粒度

#### 監視対象

配信者のID（Broadcaster ID）を複数登録：

```env
# 複数の配信者を監視（カンマ区切りまたは複数行）
TWITCH_BROADCASTER_IDS=123456,789012,345678
```

#### 監視する配信ステータス

| ステータス | 説明 | 投稿タイミング | テンプレート |
|:--|:--|:--|:--|
| **live** | 配信中 | 配信開始を検知した時 | `twitch_online_template.txt` |
| **completed** | 配信終了 | 配信終了を検知した時 | `twitch_offline_template.txt` |
| **upcoming** | 放送枠予約中 | 枠が立った時（オプション） | `twitch_schedule_template.txt` |

---

## Helix API 仕様

### 1. 認証方式

**OAuth2 Client Credentials Flow**:

```
POST https://id.twitch.tv/oauth2/token

Parameters:
  - client_id: アプリケーションID
  - client_secret: クライアントシークレット
  - grant_type: "client_credentials"

Response:
{
  "access_token": "xxx",
  "expires_in": 3600,
  "token_type": "bearer"
}
```

### 2. ストリーム状態取得 API

**エンドポイント**: `GET https://api.twitch.tv/helix/streams`

```bash
curl -H "Client-ID: <CLIENT_ID>" \
     -H "Authorization: Bearer <ACCESS_TOKEN>" \
     "https://api.twitch.tv/helix/streams?user_id=123456"
```

**レスポンス例** (配信中):

```json
{
  "data": [
    {
      "id": "41375541868",
      "user_id": "123456",
      "user_login": "example_user",
      "user_name": "ExampleUser",
      "game_id": "12345",
      "game_name": "World of Warcraft",
      "type": "live",
      "title": "New here! First time streaming!",
      "viewer_count": 1234,
      "started_at": "2023-04-20T10:11:12Z",
      "language": "en",
      "thumbnail_url": "https://static-cdn.jtvnw.net/previews-ttv/...",
      "is_mature": false
    }
  ],
  "pagination": {}
}
```

**レスポンス例** (非配信中):

```json
{
  "data": [],
  "pagination": {}
}
```

### 3. ユーザー情報取得 API

**エンドポイント**: `GET https://api.twitch.tv/helix/users`

```bash
curl -H "Client-ID: <CLIENT_ID>" \
     -H "Authorization: Bearer <ACCESS_TOKEN>" \
     "https://api.twitch.tv/helix/users?id=123456"
```

**用途**:
- Broadcaster ID からユーザー名取得
- プロフィール画像取得

---

## 実装アーキテクチャ

### 全体フロー

```
main_v3.py 起動
    ↓
plugins/twitch_api_plugin.py をロード
    ↓
TwitchAPIPlugin.is_available()
  ├─ TWITCH_CLIENT_ID が設定されているか確認
  ├─ TWITCH_CLIENT_SECRET が設定されているか確認
  ├─ TWITCH_BROADCASTER_IDS が設定されているか確認
  └─ 認証トークンを取得可能か確認
    ↓
config.TWITCH_POLL_INTERVAL ごとにポーリング開始
    ↓
各 Broadcaster ID に対して /helix/streams を呼び出し
    ↓
ストリーム状態を解析
  ├─ 前回状態と比較
  ├─ 新規配信開始 → "live" ステータスで DB に登録
  ├─ 配信終了 → "completed" ステータスで DB に登録
  └─ キャッシュを更新
    ↓
database.insert_video() で DB に登録
    ↓
プラグイン → Bluesky 投稿
```

### キャッシング戦略

配信ステータスをメモリとファイルで二重管理：

```python
# メモリキャッシュ（起動時のみ保持）
twitch_stream_cache = {
    "123456": {
        "is_live": True,
        "stream_id": "41375541868",
        "started_at": "2023-04-20T10:11:12Z",
        "title": "My Stream",
        "viewer_count": 1234
    }
}

# ファイルキャッシュ（config/ ディレクトリ）
# v2.3.0 の youtube_live_cache.py を参考に実装
```

**目的**:
- ✅ 同じ配信への重複投稿防止
- ✅ ポーリング間隔中に発火した変化の記録
- ✅ アプリ再起動後の状態復元

---

## プラグイン実装案

### ファイル構成

```
v3/
├── plugins/
│   └── twitch_api_plugin.py      # ← 新規実装
│
├── Asset/
│   └── templates/
│       └── twitch/               # ← 新規
│           ├── twitch_online_template.txt
│           ├── twitch_offline_template.txt
│           └── twitch_schedule_template.txt
│
└── settings.env
    └── TWITCH_CLIENT_ID = "..."
        TWITCH_CLIENT_SECRET = "..."
        TWITCH_BROADCASTER_IDS = "..."
        TWITCH_POLL_INTERVAL = 5
```

### プラグイン実装スケルトン

```python
# plugins/twitch_api_plugin.py

import os
import logging
import requests
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

from plugin_interface import NotificationPlugin

logger = logging.getLogger("AppLogger")
post_logger = logging.getLogger("PostLogger")


class TwitchAPIPlugin(NotificationPlugin):
    """
    Twitch API連携プラグイン（ポーリング方式）

    配信者の配信ステータスを定期的に確認し、配信開始/終了時に通知
    """

    def __init__(self):
        """プラグイン初期化"""
        self.client_id = os.getenv("TWITCH_CLIENT_ID")
        self.client_secret = os.getenv("TWITCH_CLIENT_SECRET")
        self.broadcaster_ids = os.getenv("TWITCH_BROADCASTER_IDS", "")

        self.access_token = None
        self.token_expires_at = None

        # ストリーム状態キャッシュ
        self.stream_cache: Dict[str, Dict[str, Any]] = {}

        logger.info("🔌 Twitch API プラグインを初期化しました")

    def is_available(self) -> bool:
        """
        プラグインが利用可能かどうかを判定

        必要な環境変数がすべて設定されている場合のみ有効
        """
        if not self.client_id or not self.client_secret:
            logger.debug("⚠️ Twitch API: CLIENT_ID または CLIENT_SECRET が設定されていません")
            return False

        if not self.broadcaster_ids:
            logger.debug("⚠️ Twitch API: BROADCASTER_IDS が設定されていません")
            return False

        # 認証トークン取得を試みる
        if not self._authenticate():
            logger.error("❌ Twitch API 認証失敗")
            return False

        logger.info(f"✅ Twitch API プラグインが有効です（監視対象: {len(self.broadcaster_ids.split(','))} 配信者）")
        return True

    def post_video(self, video: Dict[str, Any]) -> bool:
        """
        Twitch ストリームを Bluesky へ投稿

        video dict のスキーマ:
        {
            "title": "配信タイトル",
            "video_id": "stream_id",
            "video_url": "https://twitch.tv/...",
            "published_at": "2025-...",
            "channel_name": "配信者名",
            "platform": "twitch",
            "content_type": "live",  # or "completed"
            "viewer_count": 1234,
            "game_name": "ゲームタイトル"
        }
        """
        if video.get("platform") != "twitch":
            return False

        logger.info(f"📹 Twitch 投稿処理: {video.get('title')}")
        return True  # 最終的には Bluesky プラグインが処理

    def get_name(self) -> str:
        """プラグイン名"""
        return "TwitchAPIPlugin"

    def get_version(self) -> str:
        """プラグインバージョン"""
        return "1.0.0"

    def get_description(self) -> str:
        """プラグイン説明"""
        return "Twitch Live の配信開始・終了を Bluesky に通知（API ポーリング方式）"

    # ─────────────────────────────────────────────────
    # 内部実装（認証・API呼び出し）
    # ─────────────────────────────────────────────────

    def _authenticate(self) -> bool:
        """
        OAuth2 Client Credentials Flow で認証トークン取得
        """
        try:
            url = "https://id.twitch.tv/oauth2/token"
            params = {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "client_credentials"
            }

            response = requests.post(url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            self.access_token = data["access_token"]
            self.token_expires_at = datetime.now(timezone.utc).timestamp() + data["expires_in"]

            logger.debug("✅ Twitch 認証トークンを取得しました")
            return True

        except Exception as e:
            logger.error(f"❌ Twitch 認証エラー: {e}")
            return False

    def _is_token_expired(self) -> bool:
        """トークン有効期限をチェック"""
        if not self.token_expires_at:
            return True

        current_time = datetime.now(timezone.utc).timestamp()
        # 有効期限の 1 分前に更新
        return current_time + 60 > self.token_expires_at

    def poll_streams(self, database) -> List[Dict[str, Any]]:
        """
        登録されているすべての配信者のストリーム状態をポーリング

        新規配信/終了検知時のみ DB に保存

        Args:
            database: Database インスタンス

        Returns:
            List[dict]: 新規検知・状態変化があった配信リスト
        """
        if self._is_token_expired():
            if not self._authenticate():
                logger.error("❌ Twitch トークン更新失敗")
                return []

        changes = []
        broadcaster_ids = self.broadcaster_ids.split(',')

        for bid in broadcaster_ids:
            bid = bid.strip()
            if not bid:
                continue

            stream_info = self._get_stream_info(bid)

            if stream_info:
                # 配信中
                if bid not in self.stream_cache or not self.stream_cache[bid].get("is_live"):
                    # 新規配信開始
                    logger.info(f"🔴 配信開始検知: {stream_info['user_name']}")

                    video = self._format_stream_data(stream_info, "live")
                    database.insert_video(**video)
                    changes.append(video)

                self.stream_cache[bid] = {"is_live": True, **stream_info}
            else:
                # 非配信中
                if bid in self.stream_cache and self.stream_cache[bid].get("is_live"):
                    # 配信終了検知
                    logger.info(f"⚫ 配信終了検知: {self.stream_cache[bid].get('user_name', bid)}")

                    prev_stream = self.stream_cache[bid]
                    video = self._format_stream_data(prev_stream, "completed")
                    database.insert_video(**video)
                    changes.append(video)

                self.stream_cache[bid] = {"is_live": False}

        return changes

    def _get_stream_info(self, broadcaster_id: str) -> Optional[Dict[str, Any]]:
        """
        Helix API で配信情報を取得

        Args:
            broadcaster_id: 配信者 ID

        Returns:
            dict: ストリーム情報、または None（非配信中）
        """
        try:
            url = "https://api.twitch.tv/helix/streams"
            headers = {
                "Client-ID": self.client_id,
                "Authorization": f"Bearer {self.access_token}"
            }
            params = {"user_id": broadcaster_id}

            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            if data.get("data"):
                return data["data"][0]  # 配信中
            else:
                return None  # 非配信中

        except Exception as e:
            logger.error(f"❌ Helix API エラー (broadcaster_id={broadcaster_id}): {e}")
            return None

    def _format_stream_data(self, stream_info: Dict[str, Any], status: str) -> Dict[str, Any]:
        """
        API レスポンスを database.insert_video() の形式に変換

        Args:
            stream_info: /helix/streams のレスポンス
            status: "live" or "completed"

        Returns:
            dict: insert_video() の引数形式
        """
        return {
            "video_id": f"twitch_{stream_info['id']}",
            "title": stream_info.get("title", "配信枠"),
            "video_url": f"https://twitch.tv/{stream_info['user_login']}",
            "published_at": stream_info.get("started_at", datetime.now(timezone.utc).isoformat()),
            "channel_name": stream_info.get("user_name", ""),
            "content_type": "live",
            "live_status": status,  # "live" or "completed"
            "source": "twitch",
            "thumbnail_url": stream_info.get("thumbnail_url", ""),
        }
```

---

## 環境変数設定

### settings.env に追加

```env
# =============================
# Twitch API連携プラグインの設定
# =============================

# Twitch アプリケーション ID
# Twitch Developer Console で取得: https://dev.twitch.tv/console/apps
TWITCH_CLIENT_ID=

# Twitch クライアントシークレット
# 同じく Developer Console で発行
TWITCH_CLIENT_SECRET=

# 監視対象の配信者 Broadcaster ID（複数対応）
# カンマ区切り例: 123456,789012,345678
TWITCH_BROADCASTER_IDS=

# Twitch ポーリング間隔（分、デフォルト: 5、推奨: 5-10）
# 注意: 高頻度ポーリングは API クォータを消費するため、最小 5 分を推奨
TWITCH_POLL_INTERVAL=5

# Twitch 配信開始時の自動投稿を有効にするか
TWITCH_AUTO_POST_LIVE=true

# Twitch 配信終了時の自動投稿を有効にするか
TWITCH_AUTO_POST_OFFLINE=true

# Twitch テンプレートパス
TEMPLATE_TWITCH_ONLINE_PATH=templates/twitch/twitch_online_template.txt
TEMPLATE_TWITCH_OFFLINE_PATH=templates/twitch/twitch_offline_template.txt
```

### Broadcaster ID の取得方法

1. **Twitch Web から確認**:
   - 対象配信者のプロフィールページを開く
   - URL: `https://twitch.tv/<username>`
   - ブラウザコンソール (`F12` → Console) で以下実行:
     ```javascript
     console.log(document.querySelector('[data-test-selector="channel-header__user-id"]')?.textContent)
     ```

2. **Twitch API で取得**:
   ```bash
   curl -H "Client-ID: <YOUR_CLIENT_ID>" \
        -H "Authorization: Bearer <YOUR_TOKEN>" \
        "https://api.twitch.tv/helix/users?login=<username>"
   ```

---

## 動作フロー

### ポーリングのライフサイクル

```
アプリ起動
  ↓
TwitchAPIPlugin.is_available() = True
  ↓
[毎 5 分ごと]
  ├─ poll_streams(database) 実行
  ├─ 各配信者の /helix/streams を確認
  ├─ 前回状態と比較
  │ ├─ 配信開始検知 → insert_video(..., live_status="live")
  │ ├─ 配信終了検知 → insert_video(..., live_status="completed")
  │ └─ 変化なし → スキップ
  ├─ GUI 更新（新規動画表示）
  └─ Bluesky プラグインが自動投稿（設定に応じて）
```

### ログ出力例

```
[INFO] 🔌 Twitch API プラグインを初期化しました
[DEBUG] ✅ Twitch 認証トークンを取得しました
[INFO] ✅ Twitch API プラグインが有効です（監視対象: 3 配信者）

[毎 5 分ごと]
[INFO] 🔴 配信開始検知: ExampleUser
[INFO] 📹 Twitch 動画を保存しました: New Stream!
[INFO] 📤 Bluesky に投稿しました: https://bsky.app/...

...

[INFO] ⚫ 配信終了検知: ExampleUser
[INFO] 📹 Twitch 動画を保存しました: ExampleUser's Stream (Completed)
[INFO] 📤 Bluesky に投稿しました: https://bsky.app/...
```

---

## トラブルシューティング

### Q1: 「Twitch API プラグインが有効です」が表示されない

**A:** 以下を確認：

1. **CLIENT_ID/SECRET が設定されているか**:
   ```bash
   grep "TWITCH_CLIENT_ID" settings.env
   grep "TWITCH_CLIENT_SECRET" settings.env
   ```

2. **BROADCASTER_IDS が設定されているか**:
   ```bash
   grep "TWITCH_BROADCASTER_IDS" settings.env
   ```

3. **CLIENT_ID/SECRET が正しいか**:
   - Twitch Developer Console で再確認
   - タイプミスがないか確認

4. **ログを確認**:
   ```bash
   tail -20 logs/app.log | grep -i twitch
   ```

### Q2: ポーリングが走っていない

**A:**

1. `TWITCH_POLL_INTERVAL` が設定されているか確認
2. `is_available()` が `True` を返しているか確認
3. `main_v3.py` でポーリングスレッドが起動されているか確認

### Q3: リアルタイム性が遅い（3-5分）

**これは仕様です**。以下の理由による：

- **API ポーリング方式** を採用しているため
- YouTube RSS と同じ遅延発生
- インフラ（VPS）不要という代引交換

リアルタイム性が必須な場合：
- Twitch EventSub (Webhook) への乗り換え検討
- ただしユーザーが自力で WebSocket サーバーを構築する必要がある

### Q4: API レート制限に引っかかった

**A:**

- Twitch Helix API は **デフォルト 120 リクエスト / 分**
- 監視配信者が少ないうちは問題ない
- 大量監視の場合：
  - `TWITCH_POLL_INTERVAL` を増やす（例: 10分 → 5分ごと）
  - または複数アカウントで分散

---

## 実装ロードマップ

| マイルストーン | 内容 | 予定 |
|:--|:--|:--|
| **設計フェーズ** | 本ドキュメント | ✅ 完了 (2025-12-23) |
| **プラグイン実装** | twitch_api_plugin.py 実装 | 🔜 v3.4.0+ |
| **テンプレート追加** | Twitch 用テンプレート | 🔜 v3.4.0+ |
| **GUI 統合** | Twitch 設定画面 | 🔜 v3.5.0+ |
| **テスト・検証** | 単体テスト + 統合テスト | 🔜 v3.4.0+ |

---

## 参考資料

- [Twitch API Documentation](https://dev.twitch.tv/docs/api)
- [Helix API Reference](https://dev.twitch.tv/docs/api/reference)
- [OAuth2 ドキュメント](https://dev.twitch.tv/docs/authentication)
- [本プロジェクト - YouTube API ポーリング実装](YOUTUBE_API_CACHING_IMPLEMENTATION.md)

---

**作成日**: 2025-12-23
**ステータス**: 📐 設計文書（実装前）
**レビュー**: 未実装 - フィードバック募集中
