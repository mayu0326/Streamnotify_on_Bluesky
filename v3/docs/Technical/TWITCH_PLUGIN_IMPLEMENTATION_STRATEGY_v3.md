# Twitch プラグイン実装戦略（v3向け）

> **対象バージョン**: v3.x（将来実装予定）
> **最終更新**: 2025-12-18
> **ステータス**: 基本設計フェーズ

## 1. 概要

v3 では、OLD_App における Twitch EventSub（Webhook）統合の既存実装をリファクタリング・再構成し、以下の3つのプラグインを段階的に実装します：

1. **TwitchAPI連携プラグイン** (優先度：高) - 配信検知・メタデータ取得
2. **PubSubHubbub連携プラグイン** (優先度：中) - RSS プッシュ通知対応
3. **トンネル通信プラグイン** (優先度：中) - Webhook エンドポイント管理

本ドキュメントは OLD_App の実装（eventsub.py、webhook_routes.py、tunnel.py、tunnel_manager.py）を参考に、v3 プラグインアーキテクチャへの統合方針をまとめたものです。

---

## 2. OLD_App 既存実装の構成

### 2.1 現在の実装概要

| ファイル | 用途 | 主要機能 |
|---------|------|---------|
| `eventsub.py` | Twitch EventSub API 管理 | トークン管理、署名検証、ユーザーID取得 |
| `webhook_routes.py` | Flask Webhook ハンドラー | EventSub イベント受信・処理、Bluesky 投稿 |
| `tunnel.py` | トンネル起動・停止 | subprocess によるプロセス管理 |
| `tunnel_manager.py` | トンネルモニタリング | プロセス監視、自動再起動、URL 取得 |

### 2.2 OLD_App の EventSub 対応イベント

```
✅ stream.online      - 配信開始
✅ stream.offline     - 配信終了
✅ channel.raid       - Raid イベント
✅ webhook_callback_verification - チャレンジ検証
```

### 2.3 OLD_App のトンネル対応サービス

```
✅ Cloudflare Tunnel（推奨、無料）
✅ ngrok（有料オプション）
✅ localtunnel（シンプル）
✅ カスタムコマンド対応
```

---

## 3. v3 プラグインアーキテクチャへの統合方針

### 3.1 プラグイン分離の方針

v3 の NotificationPlugin インターフェースを活かし、以下のように機能を分割します：

```
v3/plugins/
├── twitch_api_plugin.py              # TwitchAPI連携（新規）
├── pubsub_webhook_plugin.py          # Webhook エンドポイント管理（新規）
├── tunnel_service_plugin.py          # トンネルサービス統合（新規）
└── [既存プラグイン]
```

**設計理念**:
- 各プラグインが **単一責任** を持つ（SOLID 原則）
- プラグイン間は **疎結合** に保つ
- old_App の実装は **参考実装** として活用（コード流用でなく、設計思想を継承）

### 3.2 プラグイン間の関係図

```
TwitchAPI連携プラグイン
    ↓ (配信情報取得)
    ↓
[PluginManager]
    ↓ (ビデオデータ生成)
    ↓
BlueskyプラグインやNotificationプラグイン
    ↓ (投稿実行)
    ↓
Bluesky / 他通知先

---

PubSubHubbub連携プラグイン + トンネル通信プラグイン
    ↓ (Webhook受信・ルーティング)
    ↓
EventSubハンドラー
    ↓ (イベント処理)
    ↓
TwitchAPI連携プラグイン
```

---

## 4. 各プラグインの詳細設計

### 4.1 TwitchAPI連携プラグイン（優先度：高）

#### 機能概要
- Twitch EventSub Webhook からのイベント受信・処理
- 配信開始（stream.online）、配信終了（stream.offline）の自動検知
- ユーザーメタデータ取得（タイトル、カテゴリ、言語、成熟度など）
- トークン自動更新・管理

#### クラス構成

```python
class TwitchAPIPlugin(NotificationPlugin):
    """Twitch EventSub 統合プラグイン"""

    def __init__(self):
        self.client_id = os.getenv("TWITCH_CLIENT_ID")
        self.client_secret = os.getenv("TWITCH_CLIENT_SECRET")
        self.broadcaster_id = os.getenv("TWITCH_BROADCASTER_ID")
        self.webhook_secret = os.getenv("WEBHOOK_SECRET")
        self.token_manager = TwitchTokenManager()

    def is_available(self) -> bool:
        """Twitch API 設定が完備されているか確認"""
        return all([self.client_id, self.client_secret, self.broadcaster_id, self.webhook_secret])

    def get_stream_info(self, broadcaster_id: str) -> Dict[str, Any]:
        """Twitch API から配信情報を取得"""
        # eventsub.py:get_channel_information() の実装を参考
        pass

    def verify_webhook_signature(self, request) -> bool:
        """EventSub Webhook 署名検証（eventsub.py:verify_signature() 参考）"""
        pass

    def handle_stream_online(self, event_data: Dict) -> Dict[str, Any]:
        """stream.online イベント処理"""
        # ビデオデータ標準形式で返す
        pass

    def handle_stream_offline(self, event_data: Dict) -> Dict[str, Any]:
        """stream.offline イベント処理"""
        pass

    def post_video(self, video: Dict[str, Any]) -> bool:
        """NotificationPlugin インターフェース実装"""
        # Twitch イベント処理の結果をログ出力
        pass
```

#### 設定項目（settings.env）

```env
# Twitch EventSub Configuration
TWITCH_CLIENT_ID=xxx
TWITCH_CLIENT_SECRET=xxx
TWITCH_BROADCASTER_ID=xxx
WEBHOOK_SECRET=xxx

# EventSub Notification Settings
NOTIFY_ON_TWITCH_ONLINE=true
NOTIFY_ON_TWITCH_OFFLINE=true

# Token Management
TWITCH_TOKEN_CACHE_DIR=./data/twitch_tokens/
```

#### OLD_App からの流用・リファクタリング

| OLD_App ファイル | 利用部分 | v3 での変更 |
|:--|:--|:--|
| eventsub.py | トークン管理、署名検証、API 呼び出し | クラス化、プラグイン化 |
| webhook_routes.py | EventSub イベント処理ロジック | プラグイン内に統合 |
| — | Bluesky 投稿処理 | 別プラグイン（BlueskyPlugin）に委譲 |

#### 実装スケジュール（概算）

- **Phase 3-1**: トークン管理・署名検証機能（1-2週間）
- **Phase 3-2**: EventSub イベントハンドリング（2-3週間）
- **Phase 3-3**: テスト・ドキュメント（1-2週間）

---

### 4.2 PubSubHubbub連携プラグイン（優先度：中）

#### 機能概要
- RSS フィード更新の **プッシュ通知** 受信（ポーリング不要）
- YouTube PubSubHubbub Hub への購読登録・更新・キャンセル
- RSS 更新通知の自動処理

#### アーキテクチャ

```
PubSubHubbub Hub
    ↓ (feed update)
Webhook受信
    ↓
トンネルを経由してローカルサーバーへ配信
    ↓
[PubSubHubbubプラグイン]
    ↓ (フィード解析)
[PluginManager]
```

#### クラス構成

```python
class PubSubHubbubPlugin(NotificationPlugin):
    """PubSubHubbub 連携プラグイン"""

    def __init__(self):
        self.hub_url = "https://pubsubhubbub.appspot.com/"
        self.webhook_base_url = os.getenv("WEBHOOK_BASE_URL")  # トンネル URL
        self.callback_path = "/api/pubsub_callback"

    def is_available(self) -> bool:
        return self.webhook_base_url is not None

    def subscribe_to_feed(self, feed_url: str) -> bool:
        """PubSubHubbub Hub に購読登録"""
        pass

    def verify_callback(self, challenge: str) -> bool:
        """Hub からのチャレンジ検証"""
        pass

    def handle_feed_update(self, feed_content: str) -> Dict[str, Any]:
        """フィード更新通知処理"""
        pass

    def post_video(self, video: Dict[str, Any]) -> bool:
        """NotificationPlugin インターフェース実装"""
        pass
```

#### 設定項目

```env
# PubSubHubbub Configuration
PUBSUB_ENABLED=true
WEBHOOK_BASE_URL=https://xxx.ngrok.io  # トンネル URL

# Feed URLs
YOUTUBE_FEED_URLS=https://www.youtube.com/feeds/videos.xml?channel_id=UCxxx

# Subscription Management
PUBSUB_CACHE_DIR=./data/pubsub_subscriptions/
```

#### 実装スケジュール

- **Phase 4-1**: Hub 連携・購読登録（1-2週間）
- **Phase 4-2**: コールバック処理・フィード解析（2週間）
- **Phase 4-3**: テスト・ドキュメント（1-2週間）

---

### 4.3 トンネル通信プラグイン（優先度：中）

#### 機能概要
- Cloudflare Tunnel、ngrok、localtunnel の統一インターフェース提供
- トンネルプロセスの起動・停止・監視
- トンネル URL の自動取得・更新
- Webhook エンドポイント登録の自動化

#### クラス構成

```python
class TunnelServicePlugin(NotificationPlugin):
    """トンネルサービス統合プラグイン"""

    def __init__(self):
        self.tunnel_service = os.getenv("TUNNEL_SERVICE")  # cloudflare, ngrok, localtunnel
        self.tunnel_process = None
        self.tunnel_url = None

    def is_available(self) -> bool:
        return self.tunnel_service is not None

    def start_tunnel(self) -> str:
        """トンネル起動、URL を返す（tunnel.py 参考）"""
        pass

    def stop_tunnel(self) -> bool:
        """トンネル停止"""
        pass

    def get_tunnel_url(self) -> str:
        """トンネル URL 取得（自動更新対応）"""
        pass

    def register_webhook_url(self, url: str) -> bool:
        """Twitch EventSub へ Webhook URL を登録"""
        # 自動登録ロジック
        pass

    def post_video(self, video: Dict[str, Any]) -> bool:
        """NotificationPlugin インターフェース実装"""
        # ログ出力のみ
        pass
```

#### トンネルサービス抽象化

```python
class TunnelService(ABC):
    """トンネルサービスの基底クラス"""

    @abstractmethod
    def start(self, logger) -> Tuple[Process, str]:
        """トンネル起動、(プロセス, URL) を返す"""
        pass

    @abstractmethod
    def stop(self, proc: Process):
        """トンネル停止"""
        pass

class CloudflareTunnel(TunnelService):
    """Cloudflare Tunnel 実装"""
    pass

class NgrokTunnel(TunnelService):
    """ngrok 実装"""
    pass

class LocaltunnelService(TunnelService):
    """localtunnel 実装"""
    pass
```

#### 設定項目

```env
# Tunnel Configuration
TUNNEL_SERVICE=cloudflare  # cloudflare, ngrok, localtunnel

# Cloudflare Tunnel
TUNNEL_CMD=cloudflare tunnel --url http://localhost:5000

# ngrok
NGROK_CMD=ngrok http 5000
NGROK_AUTH_TOKEN=xxx

# localtunnel
LOCALTUNNEL_CMD=lt --port 5000 --subdomain xxx
```

#### OLD_App からの流用

| ファイル | 機能 | 変更 |
|:--|:--|:--|
| tunnel.py | プロセス起動・停止 | クラス化、各サービス別実装 |
| tunnel_manager.py | モニタリング・自動再起動 | TunnelServicePlugin に統合 |

#### 実装スケジュール

- **Phase 3-4**: 基本的なトンネル起動・停止（1-2週間）
- **Phase 3-5**: URL 自動取得・トラッキング（1-2週間）
- **Phase 3-6**: EventSub 自動登録（1-2週間）
- **Phase 3-7**: テスト・ドキュメント（1-2週間）

---

## 5. Webhook エンドポイント管理戦略

### 5.1 エンドポイント設計

v3 では **プラグイン統合型 Web フレームワーク**を使用（FastAPI 推奨）：

```python
# v3/plugins/webhooks/twitch_webhook.py

from fastapi import APIRouter, Request, HTTPException
from typing import Dict, Any

router = APIRouter(prefix="/webhooks")

@router.post("/twitch")
async def handle_twitch_webhook(request: Request) -> Dict[str, Any]:
    """Twitch EventSub Webhook エンドポイント"""

    # TwitchAPIPlugin から署名検証関数を取得
    plugin = PluginManager.get_plugin("TwitchAPIPlugin")

    if not plugin.verify_webhook_signature(request):
        raise HTTPException(status_code=403, detail="Invalid signature")

    event_data = await request.json()

    # イベント処理を plugin に委譲
    result = plugin.handle_event(event_data)

    return {"status": "success", "result": result}

@router.post("/pubsub")
async def handle_pubsub_webhook(request: Request) -> Dict[str, Any]:
    """PubSubHubbub コールバックエンドポイント"""

    plugin = PluginManager.get_plugin("PubSubHubbubPlugin")

    event_data = await request.json()
    result = plugin.handle_feed_update(event_data)

    return {"status": "success", "result": result}
```

### 5.2 既存 Flask 実装との共存戦略

OLD_App の Flask 実装（webhook_routes.py）は参考にし、v3 では FastAPI への段階的な移行を推奨：

| フェーズ | 実装 | 互換性 |
|:--|:--|:--|
| v3.x | 既存 Flask 継承（webhook_routes.py → v3/plugins 配下へ移動） | ✅ 100% |
| v3.x+ | FastAPI への段階的移行 | ⚠️ 移行期間中は両対応 |
| v4.x | FastAPI に統一 | ✅ 新機能追加 |

---

## 6. 実装ロードマップ

### Phase 3（v3.x）- 既存機能の段階的統合

**Phase 3-A: TwitchAPI連携プラグイン基盤**
- [ ] TwitchTokenManager 実装
- [ ] TwitchAPIPlugin クラス設計・実装
- [ ] eventsub.py の機能を TwitchAPIPlugin に統合
- [ ] 単体テスト（10+ テストケース）

**Phase 3-B: トンネル通信プラグイン基盤**
- [ ] TunnelService 抽象基底クラス設計
- [ ] Cloudflare Tunnel 実装
- [ ] ngrok 実装
- [ ] localtunnel 実装
- [ ] TunnelServicePlugin 実装
- [ ] 単体テスト

**Phase 3-C: Webhook ハンドリングの統合**
- [ ] EventSub イベント処理ロジック（webhook_routes.py）→ TwitchAPIPlugin に移行
- [ ] Webhook エンドポイント（Flask/FastAPI）に plugin インターフェース適用
- [ ] 統合テスト

**Phase 3-D: PubSubHubbub 連携プラグイン基盤**
- [ ] PubSubHubbubPlugin クラス設計・実装
- [ ] Hub 購読ロジック実装
- [ ] コールバック処理
- [ ] 単体テスト

### Phase 4（v4.x 以降）- FastAPI への統一・拡張

- [ ] FastAPI への移行
- [ ] REST API の公開（管理画面向け）
- [ ] Web UI（ダッシュボード）との統合
- [ ] Prometheus メトリクス公開

---

## 7. ファイル構成（v3 での新規追加）

```
v3/
├── plugins/
│   ├── twitch_api_plugin.py          # TwitchAPI連携プラグイン（新規）
│   ├── pubsub_webhook_plugin.py      # PubSubHubbub連携プラグイン（新規）
│   ├── tunnel_service_plugin.py      # トンネル通信プラグイン（新規）
│   │
│   ├── twitch/                       # Twitch サポートファイル（新規）
│   │   ├── token_manager.py          # トークン管理
│   │   ├── eventsub_handler.py       # EventSub イベント処理
│   │   └── webhook_signature.py      # 署名検証
│   │
│   ├── tunnel/                       # トンネルサポートファイル（新規）
│   │   ├── tunnel_service.py         # 抽象基底クラス
│   │   ├── cloudflare_tunnel.py      # Cloudflare 実装
│   │   ├── ngrok_tunnel.py           # ngrok 実装
│   │   └── localtunnel_service.py    # localtunnel 実装
│   │
│   └── webhooks/                     # Webhook ハンドラー（新規）
│       ├── __init__.py
│       ├── twitch_webhook.py         # Twitch EventSub エンドポイント
│       └── pubsub_webhook.py         # PubSubHubbub エンドポイント
│
└── data/
    ├── twitch_tokens/                # トークンキャッシュ（新規）
    └── pubsub_subscriptions/         # 購読管理（新規）
```

---

## 8. テスト戦略

### 8.1 単体テスト

```python
# tests/test_twitch_api_plugin.py

def test_twitch_api_plugin_availability():
    """API設定完備時の is_available() テスト"""
    pass

def test_verify_webhook_signature():
    """Webhook 署名検証テスト"""
    pass

def test_handle_stream_online():
    """stream.online イベント処理テスト"""
    pass

def test_token_auto_refresh():
    """トークン自動更新テスト"""
    pass
```

### 8.2 統合テスト

```python
# tests/integration/test_twitch_integration.py

def test_full_twitch_flow():
    """
    1. TwitchAPIPlugin 初期化
    2. Webhook 受信シミュレーション
    3. イベント処理
    4. Bluesky 投稿
    """
    pass
```

### 8.3 E2E テスト（Twitch Sandbox 環境）

- Twitch EventSub Sandbox での実テスト
- 配信開始・終了の自動検知確認
- Webhook 署名検証・チャレンジ応答確認

---

## 9. 参考資料・依存関係

### 9.1 Twitch API ドキュメント
- [Twitch EventSub Documentation](https://dev.twitch.tv/docs/eventsub)
- [Twitch API Authentication](https://dev.twitch.tv/docs/authentication)

### 9.2 トンネルサービス
- [Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-applications/)
- [ngrok](https://ngrok.com/)
- [localtunnel](https://github.com/localtunnel/localtunnel)

### 9.3 PubSubHubbub
- [PubSubHubbub Specification](https://pubsubhubbub.appspot.com/)
- [YouTube RSS Feeds](https://www.youtube.com/feeds/videos.xml?channel_id=...)

### 9.4 v3 関連ドキュメント
- [PLUGIN_SYSTEM.md](./PLUGIN_SYSTEM.md)
- [ARCHITECTURE_AND_DESIGN.md](./ARCHITECTURE_AND_DESIGN.md)
- [DEVELOPMENT_GUIDELINES.md](./DEVELOPMENT_GUIDELINES.md)

---

## 10. 既知の制約・課題

### 10.1 Twitch EventSub

- **レート制限**: 1 秒当たりの API 呼び出し数に上限あり
- **Webhook 署名有効期限**: 5 分以内（タイムスタンプチェック）
- **サブスクリプション失効**: 10 日以上リスポンスなしで自動失効

### 10.2 トンネルサービス

- **Cloudflare**: 無料、安定性が高い（推奨）
- **ngrok**: 有料化の傾向、フリープラン制限あり
- **localtunnel**: 単純だがサービス停止のリスク

### 10.3 PubSubHubbub

- **遅延**: リアルタイム性は保証されない（数秒～数分の遅延あり）
- **ハブ停止**: PubSubHubbub Hub が停止した場合のフォールバック必要

---

## 11. マイグレーション パス

### OLD_App → v3 への移行ガイド

**Step 1**: OLD_App の eventsub.py・webhook_routes.py を v3/plugins/ に参考資料として配置

**Step 2**: TwitchAPIPlugin を段階的に実装（既存コードを参照）

**Step 3**: テスト環境で OLD_App と v3 の両方を並行運用（互換性確認）

**Step 4**: 本番環境への段階的切り替え

**Step 5**: 動作確認後に OLD_App を廃止予定

---

## 12. まとめ

本ドキュメントは、v3 における **Twitch プラグイン拡張** の基本設計をまとめたものです。

### 主な特徴

✅ **OLD_App の知見を活用**: 既成実装（eventsub.py、webhook_routes.py、tunnel.py）の設計思想を継承
✅ **プラグイン化**: 各機能を独立したプラグインとして実装（スケーラビリティ向上）
✅ **段階的実装**: Phase 3 → Phase 4 にかけて段階的に拡張
✅ **テスト重視**: 単体テスト・統合テスト・E2E テストを組み込み

### 次のステップ

1. 本ドキュメントのレビュー・フィードバック
2. TwitchAPIPlugin の詳細設計・実装開始
3. テストケース作成
4. OLD_App との互換性テスト
