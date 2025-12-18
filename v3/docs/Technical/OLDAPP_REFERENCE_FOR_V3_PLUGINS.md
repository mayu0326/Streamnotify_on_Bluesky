# OLD_App 既存実装リファレンス

> **対象**: v3 プラグイン開発向け参考資料
> **最終更新**: 2025-12-18

このドキュメントは、OLD_App における Twitch EventSub・トンネル関連の既存実装を **v3 プラグイン開発の参考資料** として整理したものです。

コード流用ではなく、実装思想・パターンの参考にしてください。

---

## 1. eventsub.py 概要

### 用途
- Twitch OAuth トークン管理
- EventSub Webhook 署名検証
- Twitch API 呼び出し
- イベントタイムスタンプ検証

### 主要クラス・関数

| 関数名 | 機能 | 引数 | 戻り値 |
|:--|:--|:--|:--|
| `get_app_access_token()` | アクセストークン取得 | logger_to_use | (token, expires_at) |
| `get_valid_app_access_token()` | キャッシュ版トークン取得 | logger_to_use | token |
| `get_broadcaster_id(username)` | ユーザー名→ID変換 | username, logger_to_use | broadcaster_id |
| `setup_broadcaster_id()` | BROADCASTER_ID 初期化 | logger_to_use | None（内部更新） |
| `verify_signature(request)` | Webhook 署名検証 | request | bool |
| `get_channel_information(broadcaster_id)` | チャンネル情報取得 | broadcaster_id, logger_to_use | {title, game_name, ...} |

### 実装上の工夫

#### トークンキャッシング
```python
# グローバル変数でトークンを保持
TWITCH_APP_ACCESS_TOKEN = None
TWITCH_APP_ACCESS_TOKEN_EXPIRES_AT = 0

def get_valid_app_access_token():
    global TWITCH_APP_ACCESS_TOKEN, TWITCH_APP_ACCESS_TOKEN_EXPIRES_AT

    # 期限切れチェック
    if not TWITCH_APP_ACCESS_TOKEN or time.time() > TWITCH_APP_ACCESS_TOKEN_EXPIRES_AT:
        # 再取得
        TWITCH_APP_ACCESS_TOKEN, TWITCH_APP_ACCESS_TOKEN_EXPIRES_AT = get_app_access_token()

    return TWITCH_APP_ACCESS_TOKEN
```

**v3 での適用例**: `TwitchTokenManager` クラスで実装

#### 署名検証の厳密性
```python
# タイムスタンプのナノ秒対応
def parse_timestamp(ts: str):
    if '.' in ts and ts.endswith('Z'):
        main_part, fractional = ts[:-1].split('.', 1)
        fractional = fractional[:6]  # マイクロ秒まで
        dt_obj = datetime.datetime.fromisoformat(f"{main_part}.{fractional}+00:00")
    # ...
    return dt_obj.astimezone(TIMEZONE)

# 5 分以内のリクエストのみ受け入れ
delta = abs((now - event_time).total_seconds())
if delta > 300:
    return False
```

**v3 での適用例**: `TwitchAPIPlugin.verify_webhook_signature()` に統合

---

## 2. webhook_routes.py 概要

### 用途
- Flask Blueprint でのエンドポイント定義
- EventSub イベント処理ロジック
- Bluesky 投稿の実行

### 主要エンドポイント

| エンドポイント | 用途 | メソッド |
|:--|:--|:--|
| `/webhook` | Twitch EventSub Webhook | POST/GET |
| `/api/tunnel_status` | トンネル状態確認 | GET |
| `/api/tunnel_ping` | トンネル稼働確認 | GET |

### イベント処理フロー

```python
@webhook_bp.route("/webhook", methods=["POST", "GET"])
def handle_webhook():
    # 1. 署名検証
    if not eventsub.verify_signature(request):
        return 403

    # 2. JSON パース
    data = request.get_json()

    # 3. メッセージ種別確認
    message_type = request.headers.get("Twitch-Eventsub-Message-Type")

    # 4. チャレンジ応答
    if message_type == "webhook_callback_verification":
        return challenge

    # 5. イベント処理
    if message_type == "notification":
        subscription_type = data.get("subscription", {}).get("type")

        if subscription_type == "stream.online":
            # → TwitchAPIPlugin.handle_stream_online() で処理
            pass
        elif subscription_type == "stream.offline":
            # → TwitchAPIPlugin.handle_stream_offline() で処理
            pass
        elif subscription_type == "channel.raid":
            # → TwitchAPIPlugin.handle_raid() で処理
            pass
```

### Raid イベント キャッシング（工夫例）

```python
# 直近の Raid イベントをメモリキャッシュ
raid_event_cache = {}
raid_event_cache_lock = threading.Lock()
RAID_CACHE_EXPIRE_SEC = 180

def check_raid_status(broadcaster_login):
    with raid_event_cache_lock:
        raid_entry = raid_event_cache.get(broadcaster_login)
        if raid_entry and (time.time() - raid_entry["timestamp"] <= RAID_CACHE_EXPIRE_SEC):
            return raid_entry
    return None
```

**v3 での適用例**: `EventSubEventCache` クラスの実装

---

## 3. tunnel.py 概要

### 用途
- トンネルプロセスの起動・停止
- subprocess によるプロセス管理
- ログファイルへのリダイレクト

### 主要関数

| 関数名 | 機能 |
|:--|:--|
| `start_tunnel(logger)` | トンネル起動、プロセスを返す |
| `stop_tunnel(proc, logger)` | トンネル停止 |

### 実装パターン

#### トンネルサービスの動的選択
```python
def start_tunnel(logger=None):
    tunnel_service = os.getenv("TUNNEL_SERVICE", "").lower()

    if tunnel_service in ("cloudflare", "cloudflare_domain"):
        tunnel_cmd = os.getenv("TUNNEL_CMD")
    elif tunnel_service == "cloudflare_tempurl":
        tunnel_cmd = os.getenv("CLOUDFLARE_TEMP_CMD")
    elif tunnel_service == "ngrok":
        tunnel_cmd = os.getenv("NGROK_CMD")
    elif tunnel_service == "localtunnel":
        tunnel_cmd = os.getenv("LOCALTUNNEL_CMD")
    else:
        tunnel_cmd = os.getenv("TUNNEL_CMD")

    # コマンド実行
    proc = subprocess.Popen(
        shlex.split(tunnel_cmd),
        stdout=tunnel_log,
        stderr=subprocess.STDOUT
    )
```

**v3 での適用例**: `TunnelService` 抽象基底クラス + 具体実装クラス

#### 即時終了チェック
```python
proc = subprocess.Popen(...)
time.sleep(1)  # 起動直後の安定性確認

if proc.poll() is not None:  # None = 実行中、数値 = 終了
    logger.error(f"トンネルプロセスが即時終了しました")
    # ログ確認・エラーメッセージ表示
```

#### Graceful Shutdown
```python
def stop_tunnel(proc, logger=None):
    if proc:
        try:
            proc.terminate()  # SIGTERM
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()  # SIGKILL
```

---

## 4. tunnel_manager.py 概要

### 用途
- トンネルプロセスのモニタリング
- 自動再起動機能
- Webhook URL の自動取得・更新

### 主要機能

| 関数名 | 機能 |
|:--|:--|
| `start_tunnel_and_monitor()` | トンネル起動 + モニタリングスレッド開始 |
| `stop_tunnel_and_monitor()` | トンネル停止 |
| `get_tunnel_proc()` | トンネルプロセス取得（スレッドセーフ） |
| `tunnel_monitor_loop()` | モニタリングループ（バックグラウンド） |

### 実装パターン

#### スレッドセーフなグローバルプロセス管理
```python
_tunnel_proc = None
_tunnel_proc_lock = threading.Lock()

def get_tunnel_proc():
    global _tunnel_proc
    with _tunnel_proc_lock:
        return _tunnel_proc

def start_tunnel_and_monitor(tunnel_logger):
    global _tunnel_proc
    with _tunnel_proc_lock:
        _tunnel_proc = start_tunnel(tunnel_logger)
```

**v3 での適用例**: `TunnelServicePlugin` のスレッド安全性

#### 自動再起動ロジック
```python
def tunnel_monitor_loop(...):
    while True:
        proc = proc_getter()

        if proc is None or proc.poll() is not None:  # 終了検出
            logger.warning("トンネルプロセスが停止しました。自動再起動します。")
            new_proc = start_tunnel(logger)
            proc_setter(new_proc)
            time.sleep(2)

            # URL 取得・更新
            if tunnel_service == "ngrok":
                url = get_ngrok_public_url()
            elif tunnel_service == "localtunnel":
                url = get_localtunnel_url_from_stdout(new_proc)

            # Webhook URL を settings.env に保存
            set_webhook_callback_url_temporary(url, env_path=env_path)
```

**v3 での適用例**: `TunnelServicePlugin.monitor()` メソッド

#### localtunnel URL の抽出
```python
import re
import select

for _ in range(20):  # 最大 10 秒待機
    ready, _, _ = select.select([proc.stdout], [], [], 0.5)
    if ready:
        line = proc.stdout.readline()
        decoded = line.decode("utf-8", errors="ignore").strip()

        # "https://xxx.loca.lt" を抽出
        match = re.search(r"(https://[a-zA-Z0-9\-]+\.loca\.lt)", decoded)
        if match:
            url = match.group(1)
            break
```

**v3 での適用例**: `LocaltunnelService.get_tunnel_url()` に統合

---

## 5. 実装上の重要ポイント

### 5.1 エラーハンドリング

OLD_App では以下の例外に対応：

```python
# API リクエストのエラーハンドリング
try:
    response = requests.post(url, params=params, timeout=20)
    response.raise_for_status()
except requests.exceptions.RequestException as e:
    logger.error(f"API リクエスト失敗: {str(e)}")
    raise

# JSON パースのエラーハンドリング
try:
    data = request.get_json()
    if data is None:
        logger.warning("Invalid JSON or empty body")
        return 400
except Exception as e:
    logger.error(f"JSON parse error: {e}")
    return 400
```

**v3 での推奨**: `try-except` ブロック内で詳細ログ記録 + カスタム例外クラス

### 5.2 ロギング

OLD_App では複数のロガーを使用：

```python
# 複数ロガーの併用
logger = logging.getLogger("AppLogger")
audit_logger = logging.getLogger("AuditLogger")
tunnel_logger = logging.getLogger("TunnelLogger")

# ログ出力時に詳細情報を含める
logger.info(f"通知受信 ({subscription_type}) for {broadcaster_user_name}")
logger.warning(f"Webhook検証チャレンジ受信: {challenge[:50]}...")
logger.error(f"Webhook受信: JSON解析エラー: {e}", exc_info=e)
```

**v3 での推奨**: `logging_plugin.py` に統合、emoji プレフィックス使用

### 5.3 タイムゾーン処理

```python
from tzlocal import get_localzone
import pytz

# システムタイムゾーン自動取得
TIMEZONE = get_localzone()

# または手動設定
TIMEZONE = pytz.timezone("Asia/Tokyo")

# タイムゾーン付きで現在時刻取得
now = datetime.datetime.now(TIMEZONE)
```

**v3 での推奨**: `config.py` に統一、各プラグイン内では `get_current_time()` を使用

### 5.4 環境変数の検証

```python
# 起動時に必須環境変数をチェック
TWITCH_CLIENT_ID = os.getenv("TWITCH_CLIENT_ID")
if not TWITCH_CLIENT_ID:
    logger.critical("TWITCH_CLIENT_ID is not set.")
    raise ValueError("TWITCH_CLIENT_ID is required")
```

**v3 での推奨**: `TwitchAPIPlugin.is_available()` で実施

---

## 6. v3 プラグイン開発での流用方針

### 6.1 直接流用するコード（最小限）

| 元ファイル | 元機能 | v3 での流用 | 形式 |
|:--|:--|:--|:--|
| eventsub.py | タイムスタンプ解析 | TwitchAPIPlugin | 実装参考 |
| eventsub.py | 署名検証 | TwitchAPIPlugin | 実装参考 |
| webhook_routes.py | イベント処理ロジック | TwitchAPIPlugin | 実装参考 |
| tunnel.py | プロセス起動・停止 | TunnelServicePlugin | ほぼコピー |
| tunnel_manager.py | モニタリング・再起動 | TunnelServicePlugin | ほぼコピー |

### 6.2 リファクタリングが必要な箇所

| 元コード | 理由 | v3 での改善 |
|:--|:--|:--|
| グローバル変数（TWITCH_APP_ACCESS_TOKEN） | 管理しにくい | クラス変数に変更 |
| Flask Blueprint | 古い Web フレームワーク | FastAPI への移行を検討 |
| print() デバッグ | ロギング未実装 | logging モジュール統一 |
| 環境変数の直接参照 | バリデーション不足 | config.py に統一 |

---

## 7. テスト用コード例

### 7.1 Twitch EventSub Webhook シミュレーション

```python
# tests/mocks/twitch_eventsub_mock.py

import json
import hmac
import hashlib
from datetime import datetime

class TwitchEventSubMock:
    """EventSub Webhook テスト用モック"""

    def __init__(self, webhook_secret):
        self.webhook_secret = webhook_secret

    def generate_signature(self, message_id, timestamp, body):
        """Webhook 署名を生成"""
        hmac_message = f"{message_id}{timestamp}{body}"
        signature = "sha256=" + hmac.new(
            self.webhook_secret.encode(),
            hmac_message.encode(),
            hashlib.sha256
        ).hexdigest()
        return signature

    def create_stream_online_event(self):
        """stream.online イベントを生成"""
        return {
            "subscription": {
                "type": "stream.online",
                "version": "1",
                "status": "enabled",
                "cost": 1,
                "condition": {"broadcaster_user_id": "123456"},
                "transport": {"method": "webhook", "callback": "https://example.com/webhook"},
                "created_at": "2023-11-20T10:11:12Z"
            },
            "event": {
                "id": "event_001",
                "broadcaster_user_id": "123456",
                "broadcaster_user_login": "test_user",
                "broadcaster_user_name": "Test User",
                "type": "live",
                "started_at": datetime.now().isoformat() + "Z"
            }
        }
```

---

## 8. 参考ファイル一覧

```
OLD_App/
├── eventsub.py                 # Twitch API・署名検証
├── webhook_routes.py           # EventSub イベント処理
├── tunnel.py                   # トンネルプロセス管理
├── tunnel_manager.py           # トンネルモニタリング
└── utils/
    ├── utils.py                # 汎用ユーティリティ
    └── [その他 utility 関数]
```

---

## 9. 進行状況トラッキング

| 機能 | 参考元 | v3 実装状況 | 予定 |
|:--|:--|:--|:--|
| トークン管理 | eventsub.py | ⏳ 準備中 | Phase 3-A |
| 署名検証 | eventsub.py | ⏳ 準備中 | Phase 3-A |
| イベント処理 | webhook_routes.py | ⏳ 準備中 | Phase 3-C |
| トンネル起動・停止 | tunnel.py | ⏳ 準備中 | Phase 3-B |
| トンネルモニタリング | tunnel_manager.py | ⏳ 準備中 | Phase 3-B |
