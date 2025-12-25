# v3 WebSub クライアント側実装 - 統合ガイド

**対象バージョン**: v3.4.0+
**最終更新**: 2025-12-24
**ステータス**: ✅ 実装完了

---

## 📖 概要

WebSub クライアント側の実装により、YouTube から WebSub 通知（プッシュ型）で新着動画情報を受け取り、既存の RSS ポーリングと統合して Bluesky へ投稿します。

### 🎯 主な機能

- ✅ **FastAPI Webhook サーバー** - POST /yt でプッシュ通知を受け取り
- ✅ **キュー機構** - 受け取った通知を内部キューに積む
- ✅ **統合インターフェース** - RSS と WebSub の両ソースを統一フォーマットで処理
- ✅ **テスト送信機能** - GUI からダミー通知を送信して動作確認
- ✅ **エラーハンドリング** - JSON 破損時も安全に処理
- ✅ **ステータス表示** - GUI で受信状況をリアルタイム監視

---

## 📁 新規ファイル

### 1. `websub_server.py` (380 行)

**FastAPI ベースの Webhook サーバー**

```python
from websub_server import get_websub_server

# サーバー起動
server = get_websub_server(client_id="my-websub-client-v3", port=8765)
server.run_in_thread()  # スレッドで起動

# 通知を受け取る（ポーリング）
notification = server.get_notification(timeout=0.1)
if notification:
    print(notification)  # {"channel_id": "...", "video_id": "...", ...}
```

**エンドポイント:**

| エンドポイント | メソッド | 機能 |
|:--|:--|:--|
| `/yt` | POST | YouTube WebSub 通知を受け取る |
| `/yt/test` | POST | テスト通知を送信（GUI テストパネル用） |
| `/health` | GET | ヘルスチェック・統計情報 |

**ペイロード形式:**

```json
{
  "channel_id": "UCxxxxxxxxxxxxxxx",
  "video_id": "dQw4w9WgXcQ",
  "title": "動画タイトル",
  "published_at": "2025-12-24T12:34:56+00:00",
  "thumbnail_url": "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg"
}
```

**主要メソッド:**

- `get_notification(timeout)` - キューから通知を取得
- `queue_size()` - キューサイズを確認
- `get_stats()` - 統計情報を取得
- `run_in_thread()` - スレッドで起動

### 2. `video_feed_integrator.py` (160 行)

**RSS と WebSub の統一インターフェース**

```python
from video_feed_integrator import get_feed_integrator

integrator = get_feed_integrator()

# ソース登録
integrator.register_source("rss", rss_queue)
integrator.register_source("websub", websub_queue)

# 統一フォーマットでビデオ取得
video = integrator.fetch_next_video()  # WebSub 優先
if video:
    print(video)  # {"video_id": "...", "title": "...", "source": "websub", ...}
```

**統一フォーマット:**

```python
{
    "video_id": "dQw4w9WgXcQ",
    "title": "動画タイトル",
    "channel_id": "UCxxxxxxxxxxxxxxx",
    "channel_name": "チャンネル名",  # RSS からのみ
    "video_url": "https://www.youtube.com/watch?v=...",
    "published_at": "2025-12-24T12:34:56+00:00",
    "thumbnail_url": "https://i.ytimg.com/vi/.../hqdefault.jpg",
    "source": "rss" or "websub",  # ソース識別
    "content_type": "video",
    "live_status": None,
}
```

**優先度:**
1. WebSub（即座に受け取る）
2. RSS（定期ポーリング）

### 3. `websub_test_panel.py` (280 行)

**GUI テストパネル**

GUI の設定タブに追加して、WebSub テスト通知を送信・ステータス確認。

**機能:**

- 🧪 **テスト通知送信** - ダミーペイロードで動作確認
- 📊 **ステータス表示** - キューサイズ、受信数、エラー数をリアルタイム表示
- 🗑️ **統計リセット** - 統計情報をクリア

---

## 🔧 main_v3.py への統合例

```python
from websub_server import get_websub_server
from video_feed_integrator import get_feed_integrator

# WebSub サーバー初期化
websub_server = get_websub_server(
    client_id=config.websub_client_id,
    port=config.websub_server_port
)

# フィード統合器初期化
feed_integrator = get_feed_integrator()
feed_integrator.register_source("websub", websub_server.notification_queue)

# メインループ内
video = feed_integrator.fetch_next_video(timeout=0.1)
if video:
    logger.info(f"📹 ビデオを取得 (source: {video['source']})")
    # 既存の Bluesky 投稿ロジックに渡す
```

---

## ⚙️ 設定項目

`settings.env` で以下を設定：

```env
# WebSub クライアント ID（自家サーバー用）
# Webhook リクエストの識別に使用（任意の文字列で可）
WEBSUB_CLIENT_ID=my-websub-client-v3

# WebSub コールバック URL（websub/hybrid モード用）
# YouTube がプッシュ通知を送信するエンドポイント URL
WEBSUB_CALLBACK_URL=https://your-server.com/yt

# WebSub ローカルサーバーポート
WEBSUB_SERVER_PORT=8765
```

---

## 🧪 テスト実行

### 1. ローカルテスト

```bash
# WebSub サーバーを起動
python -m uvicorn websub_server:app --host 0.0.0.0 --port 8765
```

### 2. テスト通知を送信

```bash
curl -X POST http://localhost:8765/yt/test \
  -H "Content-Type: application/json" \
  -d '{
    "channel_id": "UCxxxxxxxxxxxxxxx",
    "video_id": "dQw4w9WgXcQ",
    "title": "テスト動画"
  }'
```

### 3. ステータス確認

```bash
curl http://localhost:8765/health
```

応答例：
```json
{
  "status": "healthy",
  "client_id": "my-websub-client-v3",
  "queue_size": 1,
  "stats": {
    "received": 5,
    "processed": 3,
    "errors": 0,
    "last_received_at": "2025-12-24T12:34:56.123456"
  }
}
```

---

## 🛡️ エラーハンドリング

### JSON パースエラー

```python
try:
    body = await request.json()
except json.JSONDecodeError as e:
    logger.error(f"JSON パースエラー: {e}")
    # 統計に記録
    stats["errors"] += 1
    return {"status": "error"}
```

### キュー追加失敗

```python
try:
    self.notification_queue.put_nowait(notification)
except Exception as e:
    logger.error(f"キューへの追加失敗: {e}")
    stats["errors"] += 1
```

### ペイロード検証

```python
# 必須フィールド検証
if not channel_id or not video_id or not title:
    logger.warning(f"必須フィールド不足")
    return None
```

---

## 📊 統計情報

サーバーは以下の統計を管理：

```python
{
    "received": 0,              # 受信通知数
    "processed": 0,             # 処理済み通知数
    "errors": 0,                # エラー数
    "last_received_at": None,   # 最後の受信時刻
    "last_error_at": None,      # 最後のエラー時刻
    "last_error_message": None  # 最後のエラーメッセージ
}
```

`/health` エンドポイントで確認可能。

---

## 🔌 既存ロジックとの統合

### 従来（RSS ポーリングのみ）

```
YouTube RSS → RSS Parser → DB → GUI → Bluesky
```

### 新規（RSS + WebSub）

```
┌─ YouTube RSS → RSS Parser ─┐
│                              ├─ Feed Integrator ─ DB ─ GUI ─ Bluesky
└─ YouTube WebSub ────────────┘
     (Webhook /yt)
         ↓
      Queue
```

**統合ポイント:**

1. `video_feed_integrator.fetch_next_video()` で両ソースを統一フォーマット化
2. ソース優先度自動判定（WebSub > RSS）
3. 既存の Bluesky 投稿ロジックは変更なし

---

## ⚠️ 注意事項

### 1. WebSub サーバーは自動起動されない

`main_v3.py` で以下を追加する必要があります：

```python
if config.youtube_feed_mode in ("websub", "hybrid"):
    websub_server = get_websub_server(
        client_id=config.websub_client_id,
        port=config.websub_server_port
    )
    websub_server.run_in_thread()  # スレッドで起動
```

### 2. ポート開放が必須

WebSub 通知を受け取るには、WEBSUB_CALLBACK_URL にアクセス可能である必要があります。

- **自家サーバー**: トンネル経由（ngrok、Cloudflare Tunnel など）
- **クラウド**: 固定 IP + ファイアウォール設定

### 3. HTTPS 必須

YouTube WebSub は HTTPS エンドポイントのみをサポート。

---

## 📚 関連ドキュメント

- [WEBSUB_IMPLEMENTATION.md](WEBSUB_IMPLEMENTATION.md) - WebSub プロトコル詳細
- [settings.env.example](../settings.env.example) - 設定項目
- [requirements.txt](../requirements.txt) - 依存ライブラリ

---

## 次のステップ

1. **main_v3.py に統合** - WebSub サーバー初期化コードを追加
2. **GUI に統合** - websub_test_panel.py を GUI に組み込み
3. **テスト実行** - ローカルで動作確認
4. **本番デプロイ** - トンネル経由で YouTube から通知を受け取り

---

**作成日**: 2025-12-24
**最終更新**: 2025-12-24
**ステータス**: ✅ 実装完了
