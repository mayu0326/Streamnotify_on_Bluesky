# v3 プラグイン拡張 実装タスクシート

> **バージョン**: v3.3.0（WebSub 実装完了）
> **最終更新**: 2026-01-03
> **ステータス**: WebSub 実装完了、Twitch/Tunnel/PubSubHubbub は計画段階

---

## ✅ WebSub/PubSubHubbub センターサーバー統合（v3.2.0 で実装完了）

### ステータス: 実装完了

**実装済み機能**:
- ✅ **WebSub Hub 構築**: FastAPI ベースのセンターサーバー
- ✅ **PubSubHubbub プロトコル対応**: YouTube RSS Hub と連携
- ✅ **クライアント管理**: subscriptions テーブルで購読者を一元管理
- ✅ **Webhook エンドポイント**: `/pubsub`, `/register`, `/videos` 等
- ✅ **認証メカニズム**: verify_token + API キー認証
- ✅ **本番運用**: 複数ユーザーへの提供実績あり

**詳細仕様**: [CENTER_SERVER_INTEGRATION_SPEC.md](../References/CENTER_SERVER_INTEGRATION_SPEC.md) を参照

---

## Phase 3-A: TwitchAPI連携プラグイン基盤（推定期間：3-4週間）

### Task 3-A-1: トークン管理クラス設計・実装

**目標**: TwitchTokenManager クラスを実装し、OAuth トークンのキャッシング・自動更新を管理

**参考元**: OLD_App/eventsub.py
- `get_app_access_token()`
- `get_valid_app_access_token()`
- グローバル変数: TWITCH_APP_ACCESS_TOKEN, TWITCH_APP_ACCESS_TOKEN_EXPIRES_AT

**成果物**:
```python
# v3/plugins/twitch/token_manager.py

class TwitchTokenManager:
    """Twitch OAuth トークン管理"""

    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.token = None
        self.expires_at = 0
        self.lock = threading.Lock()

    def get_valid_token(self) -> str:
        """有効なトークンを取得（自動更新対応）"""
        pass

    def refresh_token(self) -> Tuple[str, int]:
        """トークンを強制更新"""
        pass
```

**チェックリスト**:
- [ ] クラス定義・init メソッド実装
- [ ] get_valid_token() 実装
- [ ] refresh_token() 実装
- [ ] スレッドセーフティ確認（Lock/RLock）
- [ ] 単体テスト（テストケース：5個以上）
- [ ] ドキュメント作成

**テスト項目**:
- [ ] トークン取得成功
- [ ] トークンキャッシュ動作
- [ ] 期限切れ時の自動更新
- [ ] API エラー時のリトライ
- [ ] スレッド競合時の動作

---

### Task 3-A-2: Webhook 署名検証クラス実装

**目標**: Twitch EventSub の Webhook 署名検証をクラス化

**参考元**: OLD_App/eventsub.py
- `verify_signature(request)`
- タイムスタンプ検証
- HMAC-SHA256 署名生成

**成果物**:
```python
# v3/plugins/twitch/webhook_signature.py

class WebhookSignatureVerifier:
    """Twitch EventSub Webhook 署名検証"""

    def __init__(self, webhook_secret: str):
        self.webhook_secret = webhook_secret

    def verify(self, request: Request) -> bool:
        """Webhook 署名を検証"""
        pass

    def _parse_timestamp(self, ts_str: str) -> datetime:
        """タイムスタンプをパース"""
        pass

    def _generate_signature(self, message_id: str, timestamp: str, body: str) -> str:
        """HMAC-SHA256 署名を生成"""
        pass
```

**チェックリスト**:
- [ ] クラス定義・init メソッド実装
- [ ] verify() メソッド実装
- [ ] _parse_timestamp() 実装（ナノ秒対応）
- [ ] _generate_signature() 実装
- [ ] 時刻偏差チェック（5分以内）
- [ ] 単体テスト（テストケース：8個以上）
- [ ] ドキュメント作成

**テスト項目**:
- [ ] 有効な署名の認証
- [ ] 無効な署名の拒否
- [ ] タイムスタンプ偏差（5分以上）での拒否
- [ ] ナノ秒形式のタイムスタンプ対応
- [ ] タイムゾーン混在対応

---

### Task 3-A-3: EventSub イベントハンドラー実装

**目標**: stream.online / stream.offline / channel.raid イベントを処理

**参考元**: OLD_App/webhook_routes.py
- `handle_webhook()`
- イベント種別分岐
- Twitch API メタデータ取得

**成果物**:
```python
# v3/plugins/twitch/eventsub_handler.py

class EventSubEventHandler:
    """Twitch EventSub イベント処理"""

    def __init__(self, token_manager: TwitchTokenManager):
        self.token_manager = token_manager

    def handle_stream_online(self, event_data: Dict) -> Dict[str, Any]:
        """stream.online イベント処理"""
        pass

    def handle_stream_offline(self, event_data: Dict) -> Dict[str, Any]:
        """stream.offline イベント処理"""
        pass

    def handle_channel_raid(self, event_data: Dict) -> Dict[str, Any]:
        """channel.raid イベント処理"""
        pass

    def get_channel_info(self, broadcaster_id: str) -> Dict[str, Any]:
        """Twitch API からチャンネル情報取得"""
        pass
```

**チェックリスト**:
- [ ] handle_stream_online() 実装
- [ ] handle_stream_offline() 実装
- [ ] handle_channel_raid() 実装
- [ ] get_channel_info() 実装
- [ ] 標準ビデオデータ形式への変換
- [ ] 単体テスト（テストケース：10個以上）
- [ ] ドキュメント作成

**テスト項目**:
- [ ] stream.online イベント処理
- [ ] stream.offline イベント処理
- [ ] channel.raid イベント処理
- [ ] メタデータ取得失敗時のフォールバック
- [ ] ビデオデータ形式の検証

---

### Task 3-A-4: TwitchAPIPlugin クラス実装

**目標**: v3 の NotificationPlugin インターフェースに対応

**参考元**: plugin_interface.py

**成果物**:
```python
# v3/plugins/twitch_api_plugin.py

class TwitchAPIPlugin(NotificationPlugin):
    """Twitch EventSub 統合プラグイン"""

    def is_available(self) -> bool:
        """Twitch API 設定が完備されているか"""
        pass

    def post_video(self, video: Dict[str, Any]) -> bool:
        """ビデオを投稿（ログ出力のみ）"""
        pass

    def get_name(self) -> str:
        return "TwitchAPIPlugin"

    def get_version(self) -> str:
        return "1.0.0"

    # 追加メソッド
    def verify_webhook_signature(self, request: Request) -> bool:
        pass

    def handle_eventsub_event(self, event_data: Dict) -> Dict[str, Any]:
        pass
```

**チェックリスト**:
- [ ] is_available() 実装
- [ ] post_video() 実装
- [ ] get_name() / get_version() 実装
- [ ] verify_webhook_signature() 実装
- [ ] handle_eventsub_event() 実装
- [ ] 統合テスト（テストケース：5個以上）
- [ ] ドキュメント作成

**テスト項目**:
- [ ] プラグイン読み込み成功
- [ ] is_available() の判定
- [ ] Webhook 署名検証統合
- [ ] イベント処理統合

---

### Task 3-A-5: TwitchAPIPlugin の単体テスト作成

**目標**: TwitchAPIPlugin の全機能をテストカバー

**テストファイル**: `tests/test_twitch_api_plugin.py`

**テストケース概要**:

```python
def test_is_available_with_all_env_vars():
    """全ての必須環境変数が設定されている場合"""
    pass

def test_is_available_missing_client_id():
    """TWITCH_CLIENT_ID が未設定"""
    pass

def test_verify_webhook_signature_valid():
    """有効な署名の検証成功"""
    pass

def test_verify_webhook_signature_invalid():
    """無効な署名の検証失敗"""
    pass

def test_handle_stream_online_event():
    """stream.online イベント処理"""
    pass

def test_handle_stream_offline_event():
    """stream.offline イベント処理"""
    pass

def test_get_channel_info_api_success():
    """チャンネル情報取得成功"""
    pass

def test_get_channel_info_api_failure():
    """チャンネル情報取得失敗時のフォールバック"""
    pass

def test_token_auto_refresh():
    """トークン自動更新"""
    pass

def test_plugin_load_from_manager():
    """PluginManager からのロード"""
    pass
```

**チェックリスト**:
- [ ] テストファイル作成
- [ ] pytest 設定確認
- [ ] 全テストケース実装
- [ ] モック・フィクスチャ設定
- [ ] テスト実行確認（10/10 パス）
- [ ] カバレッジ確認（90% 以上）

---

## Phase 3-B: トンネル通信プラグイン基盤（推定期間：3-4週間）

### Task 3-B-1: TunnelService 抽象基底クラス設計

**目標**: 各トンネルサービス（Cloudflare、ngrok、localtunnel）の統一インターフェース

**参考元**: OLD_App/tunnel.py、tunnel_manager.py

**成果物**:
```python
# v3/plugins/tunnel/tunnel_service.py

from abc import ABC, abstractmethod
from typing import Tuple
from subprocess import Popen

class TunnelService(ABC):
    """トンネルサービス基底クラス"""

    @abstractmethod
    def start(self, logger) -> Tuple[Popen, str]:
        """トンネル起動

        Returns:
            (プロセス, トンネル URL)
        """
        pass

    @abstractmethod
    def stop(self, proc: Popen):
        """トンネル停止"""
        pass

    @abstractmethod
    def get_url(self, proc: Popen) -> str:
        """トンネル URL を取得"""
        pass

    @abstractmethod
    def get_name(self) -> str:
        """サービス名を取得"""
        pass
```

**チェックリスト**:
- [ ] 抽象基底クラス定義
- [ ] 抽象メソッド定義（start, stop, get_url, get_name）
- [ ] ドキュメント作成

---

### Task 3-B-2: Cloudflare Tunnel 実装

**目標**: Cloudflare Tunnel の統合

**参考元**: OLD_App/tunnel.py (Cloudflare セクション)

**成果物**:
```python
# v3/plugins/tunnel/cloudflare_tunnel.py

class CloudflareTunnel(TunnelService):
    """Cloudflare Tunnel 実装"""

    def __init__(self, tunnel_cmd: str):
        self.tunnel_cmd = tunnel_cmd

    def start(self, logger) -> Tuple[Popen, str]:
        """cloudflare tunnel コマンドを実行"""
        pass

    def stop(self, proc: Popen):
        """プロセスを終了"""
        pass

    def get_url(self, proc: Popen) -> str:
        """ログファイルから URL を抽出"""
        pass

    def get_name(self) -> str:
        return "CloudflareTunnel"
```

**チェックリスト**:
- [ ] __init__() 実装
- [ ] start() 実装
- [ ] stop() 実装（graceful shutdown）
- [ ] get_url() 実装
- [ ] ログファイル監視実装
- [ ] テスト実装（3-4 テストケース）

---

### Task 3-B-3: ngrok Tunnel 実装

**目標**: ngrok の統合

**参考元**: OLD_App/tunnel.py (ngrok セクション)

**成果物**:
```python
# v3/plugins/tunnel/ngrok_tunnel.py

class NgrokTunnel(TunnelService):
    """ngrok 実装"""

    def __init__(self, tunnel_cmd: str):
        self.tunnel_cmd = tunnel_cmd

    def start(self, logger) -> Tuple[Popen, str]:
        """ngrok http コマンドを実行"""
        pass

    def get_url(self, proc: Popen) -> str:
        """ngrok API または stdout から URL を取得"""
        # OLD_App: get_ngrok_public_url() 参考
        pass

    def get_name(self) -> str:
        return "NgrokTunnel"
```

**チェックリスト**:
- [ ] __init__() 実装
- [ ] start() 実装
- [ ] get_url() 実装
- [ ] API エンドポイント（http://localhost:4040/api/tunnels）対応
- [ ] テスト実装（3-4 テストケース）

---

### Task 3-B-4: localtunnel 実装

**目標**: localtunnel の統合

**参考元**: OLD_App/tunnel_manager.py (localtunnel URL 抽出ロジック)

**成果物**:
```python
# v3/plugins/tunnel/localtunnel_service.py

class LocaltunnelService(TunnelService):
    """localtunnel 実装"""

    def start(self, logger) -> Tuple[Popen, str]:
        """lt コマンドを実行"""
        pass

    def get_url(self, proc: Popen) -> str:
        """stdout から https://xxx.loca.lt を抽出"""
        # OLD_App: re.search(r"(https://[a-zA-Z0-9\-]+\.loca\.lt)") 参考
        pass

    def get_name(self) -> str:
        return "LocaltunnelService"
```

**チェックリスト**:
- [ ] __init__() 実装
- [ ] start() 実装
- [ ] get_url() 実装（regex パターン）
- [ ] stdout 監視実装（select.select()）
- [ ] テスト実装（3-4 テストケース）

---

### Task 3-B-5: TunnelServicePlugin 実装

**目標**: プラグインとしてトンネルサービスを統合

**成果物**:
```python
# v3/plugins/tunnel_service_plugin.py

class TunnelServicePlugin(NotificationPlugin):
    """トンネルサービス統合プラグイン"""

    def __init__(self):
        self.tunnel_service = self._create_tunnel_service()
        self.tunnel_proc = None
        self.tunnel_url = None

    def is_available(self) -> bool:
        return self.tunnel_service is not None

    def start_tunnel(self) -> str:
        """トンネル起動、URL を返す"""
        pass

    def stop_tunnel(self) -> bool:
        """トンネル停止"""
        pass

    def get_tunnel_url(self) -> str:
        """トンネル URL 取得"""
        pass

    def _create_tunnel_service(self) -> TunnelService:
        """環境変数に応じて TunnelService インスタンスを生成"""
        pass

    def post_video(self, video: Dict[str, Any]) -> bool:
        """NotificationPlugin インターフェース実装"""
        pass
```

**チェックリスト**:
- [ ] __init__() 実装
- [ ] is_available() 実装
- [ ] start_tunnel() 実装
- [ ] stop_tunnel() 実装
- [ ] get_tunnel_url() 実装
- [ ] _create_tunnel_service() 実装
- [ ] 統合テスト

---

### Task 3-B-6: トンネル監視・自動再起動機能

**目標**: バックグラウンドでトンネルをモニタリング、自動再起動

**参考元**: OLD_App/tunnel_manager.py (tunnel_monitor_loop)

**成果物**:
```python
# v3/plugins/tunnel_service_plugin.py に追加

class TunnelServicePlugin(NotificationPlugin):

    def _start_monitor_thread(self):
        """モニタリングスレッド起動"""
        monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True
        )
        monitor_thread.start()

    def _monitor_loop(self):
        """トンネルプロセスを監視"""
        while self.monitoring:
            proc = self.tunnel_proc

            if proc is None or proc.poll() is not None:
                logger.warning("トンネルプロセスが停止。自動再起動します。")

                # 再起動
                new_url = self.start_tunnel()

                # settings.env を更新
                self._update_webhook_url(new_url)

            time.sleep(10)  # 10 秒ごとにチェック
```

**チェックリスト**:
- [ ] _start_monitor_thread() 実装
- [ ] _monitor_loop() 実装
- [ ] スレッドセーフティ確認
- [ ] settings.env 自動更新
- [ ] テスト実装

---


---

## 完了チェックリスト（全体）

### Phase 3-A 完了条件
- [ ] TwitchTokenManager: 単体テスト 5/5 パス
- [ ] WebhookSignatureVerifier: 単体テスト 8/8 パス
- [ ] EventSubEventHandler: 単体テスト 10/10 パス
- [ ] TwitchAPIPlugin: 単体テスト 5/5 パス
- [ ] 統合テスト: 5/5 パス
- [ ] ドキュメント完成

### Phase 3-B 完了条件
- [ ] TunnelService: 抽象クラス定義完了
- [ ] CloudflareTunnel: テスト 3/3 パス
- [ ] NgrokTunnel: テスト 3/3 パス
- [ ] LocaltunnelService: テスト 3/3 パス
- [ ] TunnelServicePlugin: 統合テスト 5/5 パス
- [ ] 自動再起動ロジック: 機能確認済み

---

## ドキュメント作成タスク

| ドキュメント | 内容 | 担当 |
|:--|:--|:--|
| TwitchAPIPlugin ガイド | 使用方法・設定 | 開発者 |
| TunnelServicePlugin ガイド | トンネル設定ガイド | 開発者 |
| Webhook エンドポイント | API 仕様書 | 開発者 |
| 実装ガイド | プラグイン開発のベストプラクティス | 開発者 |

---

## 依存関係グラフ

```
Phase 3-A (TwitchAPI)
    ├─ TokenManager
    ├─ SignatureVerifier
    ├─ EventSubHandler
    └─ TwitchAPIPlugin

Phase 3-B (Tunnel)
    ├─ TunnelService (abstract)
    ├─ CloudflareTunnel
    ├─ NgrokTunnel
    ├─ LocaltunnelService
    └─ TunnelServicePlugin
        └─ Monitor Thread

Phase 3-C (Webhook Integration)
    ├─ TwitchAPIPlugin ← Phase 3-A 依存
    └─ Flask Webhook Handler
```

---

## リスク・対策

| リスク | 対策 |
|:--|:--|
| Twitch API レート制限 | キャッシング・バッチ処理 |
| トンネルサービス停止 | フェイルオーバー実装 |
| テストカバレッジ不足 | ユニット・統合・E2E 全段階でテスト |

---

## 📝 更新履歴

### 2026-01-03: v3.3.0 実装完了を反映

**変更内容**:
- ✅ WebSub/PubSubHubbub センターサーバー実装を「完了」に移動（v3.2.0+）
  - YouTube RSS Feed WebSub Hub: 本番運用実績あり
  - 複数ユーザーへの提供中
  - 詳細: [CENTER_SERVER_INTEGRATION_SPEC.md](../References/CENTER_SERVER_INTEGRATION_SPEC.md)

- 📋 Phase 3-C を「将来計画」（v4.0.0+）に再分類(Phase から除外)
  - Twitch EventSub WebSub 化（Q1 2026）
  - ニコニコ WebSub 対応（Q2 2026）
  - セキュリティ監査・マルチテナント強化（Q2-Q3 2026）

- 📊 実装スケジュールを更新
  - WebSub 展開は完了
  - Twitch/Tunnel の実装予定時期を更新

**根拠**:
- WebSub 機能: 複数ユーザーが現在利用中
- 設定項目: settings.env.example に20+ のWebSub 関連パラメータ
- 参考ドキュメント: [CENTER_SERVER_INTEGRATION_SPEC.md](../References/CENTER_SERVER_INTEGRATION_SPEC.md)、[FUTURE_ROADMAP_v3.md](../References/FUTURE_ROADMAP_v3.md)

### 2025-12-18: 初版作成

初期計画として、Twitch/Tunnel/PubSubHubbub の実装タスクを定義。
