# v3 WebSub クライアント側実装 - 統合ガイド

**対象バージョン**: v3.4.0+
**最終更新**: 2026-01-03
**ステータス**: ⚠️ 部分実装（センターサーバー統合版）

---

## 📖 概要

WebSub クライアント側の実装は、**セ ンターサーバー（クラウド本番サーバー）を利用したプッシュ型**で動作します。

- ✅ **ProductionServerAPIClient** - WebSub で集積されたビデオデータを HTTP GET で取得
- ✅ **YouTube WebSub 管理** - 本番サーバーへの WebSub 購読登録
- ✅ **RSS との統合** - RSS ポーリング + WebSub HTTP GET の両ソースに対応
- ⚠️ **ローカル Webhook サーバー** - ドキュメント記載の `websub_server.py` は実装されていない（センターサーバーのため不要）

---

## 🎯 実装の違い：添付ドキュメント vs 実装現状

---

## 実装アーキテクチャの違い

### 📄 添付ドキュメント（想定）
```
YouTube → Webhook サーバー（FastAPI）→ キュー → Integrator → DB → Bluesky
          ローカルホスト:8765
```

**実装方式**: ローカル WebSub サーバー + キューイング

**必要なファイル**（ドキュメント記載、未実装）:
- `websub_server.py` - FastAPI Webhook サーバー
- `video_feed_integrator.py` - RSS + WebSub 統合
- `websub_test_panel.py` - GUI テストパネル

### ✅ 実装現状（v3.3.0+）
```
YouTube → センターサーバー（本番環境）→ ProductionServerAPIClient（HTTP GET）→ DB → Bluesky
          https://webhook.neco-server.net/videos?channel_id=...
```

**実装方式**: セ ンターサーバー経由の HTTP API（プル型）

**実装済みファイル**:
- ✅ `youtube_core/youtube_websub.py` - WebSub 管理（センターサーバー統合）
- ✅ `production_server_api_client.py` - HTTP API クライアント
- ✅ `config.py` - WebSub 設定項目の読み込み（部分的）

---

## 📁 実装済みコンポーネント

### 1. `youtube_core/youtube_websub.py` (476 行、✅ 実装済み)

**YouTubeWebSub 管理クラス**

```python
from youtube_core.youtube_websub import YouTubeWebSub

websub = YouTubeWebSub(channel_id="UCxxxxxxxxxxxxxxx")
websub.ensure_websub_registered()  # センターサーバーへの登録

videos = websub.get_websub_videos(limit=50)  # HTTP GET でビデオ取得
```

**主要メソッド**:

- `__init__(channel_id)` - YouTubeWebSub 初期化
- `_ensure_websub_registered()` - センターサーバーに WebSub 購読を登録（1回のみ）
- `get_websub_videos(limit)` - センターサーバーから WebSub で集積された動画を取得

**内部動作**:

1. 初期化時に `_api_client = ProductionServerAPIClient()` を遅延初期化
2. `_ensure_websub_registered()` で以下を実行:
   - 環境変数から `WEBSUB_CLIENT_ID`, `WEBSUB_CALLBACK_URL` を読み込み
   - `api_client.register_websub_client()` をセンターサーバーに呼び出し
   - 購読登録を 1 回のみ実行（`_websub_registered` フラグで防止）

3. `get_websub_videos()` で以下を実行:
   - ProductionServerAPIClient の `get_websub_videos(channel_id)` を呼び出し
   - センターサーバーからビデオデータを HTTP GET で取得
   - ビデオを **タイムスタンプ降順**でソート

**ペイロード形式**:

```json
{
  "video_id": "dQw4w9WgXcQ",
  "title": "動画タイトル",
  "channel_id": "UCxxxxxxxxxxxxxxx",
  "channel_name": "チャンネル名",
  "thumbnail_url": "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg",
  "published_at": "2025-12-24T12:34:56+00:00",
  "content_type": "video",
  "live_status": null
}
```

### 2. `production_server_api_client.py` (292 行、✅ 実装済み)

**センターサーバー HTTP API クライアント**

```python
from production_server_api_client import get_production_api_client

api_client = get_production_api_client()

# WebSub 購読登録
api_client.register_websub_client(
    clientid="my-client-id",
    channelid="UCxxxxxxxxxxxxxxx",
    callbackurl="https://your-server.com/yt"
)

# WebSub で集積されたビデオ取得
videos = api_client.get_websub_videos(
    channel_id="UCxxxxxxxxxxxxxxx",
    limit=50
)
```

**主要メソッド**:

| メソッド | 動作 | 実装状況 |
|:--|:--|:--|
| `get_websub_videos(channel_id, limit)` | HTTP GET でビデオ取得 | ✅ 実装済み |
| `register_websub_client(clientid, channelid, callbackurl)` | WebSub 購読登録 | ✅ 実装済み |
| `verify_connection()` | センターサーバー接続確認 | ✅ 実装済み |
| `_verify_connection()` | 初期化時の接続テスト | ✅ 実装済み |

**エンドポイント**:

| エンドポイント | メソッド | 用途 | 実装 |
|:--|:--|:--|:--|
| `/videos` | GET | WebSub 集積ビデオ取得 | ✅ |
| `/register` | POST | WebSub 購読登録 | ✅ |
| `/health` | GET | ヘルスチェック | ✅ |

**ベース URL**:

```env
# 本番環境（デフォルト）
https://webhook.neco-server.net

# ローカル開発（オプション）
http://192.168.100.14:8000

# 環境変数で指定
WEBSUB_BASE_URL=https://your-server.com
```

### 3. `youtube_core/youtube_rss.py` (⚠️ 部分統合)

**YouTube RSS ポーリング（既存機能）**

```python
from youtube_core.youtube_rss import YouTubeRSS

rss = YouTubeRSS(channel_id="UCxxxxxxxxxxxxxxx")
videos = rss.fetch_rss_videos()  # RSS ポーリング
```

**統合状況**:
- ✅ RSS ポーリング自体は既存実装
- ⚠️ RSS + WebSub の統一フォーマット化は未実装
- ⚠️ 優先度制御（WebSub 優先）は未実装

---

## 🔧 実装状況の詳細

### ✅ 実装済み

1. **ProductionServerAPIClient** - HTTP API クライアント
   - `get_websub_videos(channel_id, limit)` - ビデオ取得 ✅
   - `register_websub_client(...)` - 購読登録 ✅
   - `verify_connection()` - 接続確認 ✅

2. **YouTubeWebSub** - WebSub 管理クラス
   - `ensure_websub_registered()` - 購読登録フロー ✅
   - `get_websub_videos(limit)` - ビデオ取得フロー ✅
   - ProductionServerAPIClient との統合 ✅

3. **config.py** - 設定項目（部分的）
   - `WEBSUB_CLIENT_ID` - 読み込み可能
   - `WEBSUB_CLIENT_API_KEY` - 読み込み可能
   - `WEBSUB_BASE_URL` - 環境変数でサポート

### ⚠️ 実装中 / 未実装

1. **config.py の完全統合**
   - `youtube_feed_mode="websub"` 時の自動初期化
   - WebSub 設定値の一括バリデーション（部分的）

2. **RSS + WebSub の統合フロー**
   - ❌ `video_feed_integrator.py` は未実装
   - ❌ RSS と WebSub ビデオを統一フォーマットで処理する機構がない
   - ❌ 優先度制御（WebSub を優先）の未実装

3. **main_v3.py への統合**
   - ⚠️ WebSub フロー が main_v3.py で呼び出されているか不明
   - ⚠️ RSS + WebSub の動的選択ロジックが未実装

4. **GUI テストパネル**
   - ❌ `websub_test_panel.py` は未実装
   - ❌ GUI からのテスト通知送信機能なし
   - ❌ リアルタイムステータス表示なし

---

## 🔧 main_v3.py への統合状況

添付ドキュメント記載のコード：

```python
from websub_server import get_websub_server
from video_feed_integrator import get_feed_integrator

websub_server = get_websub_server(...)  # これは未実装
feed_integrator = get_feed_integrator()  # これは未実装
```

実装現状：

```python
# 代わりに以下を使用
from youtube_core.youtube_websub import YouTubeWebSub
from production_server_api_client import ProductionServerAPIClient

websub = YouTubeWebSub(channel_id=config.youtube_channel_id)
websub.ensure_websub_registered()  # セ ンターサーバー登録

videos = websub.get_websub_videos(limit=50)  # HTTP GET 取得
```

**問題点**:
- `main_v3.py` で WebSub フロー が実際に呼び出されているか確認が必要
- RSS + WebSub の統合フロー がない

---

## ⚙️ 設定項目

`settings.env` で以下を設定：

```env
# YouTube フィード取得モード（poll / websub / hybrid）
# poll: RSS ポーリングのみ（既存）
# websub: WebSub HTTP GET のみ（センターサーバー）
# hybrid: RSS + WebSub（将来実装予定）
YOUTUBE_FEED_MODE=poll

# WebSub クライアント ID（センターサーバー）
# Webhook リクエストの識別に使用
WEBSUB_CLIENT_ID=

# WebSub コールバック URL（センターサーバー）
# YouTube がプッシュ通知を送信するエンドポイント
# WEBSUB_CALLBACK_URL=

# WebSub クライアント API キー（センターサーバー）
# センターサーバー HTTP API の認証キー
WEBSUB_CLIENT_API_KEY=

# WebSub 購読期間（秒、デフォルト: 432000 = 5日）
# YouTube への購読リクエストで指定する有効期間
# 範囲: 86400（1日）～ 2592000（30日）
# 推奨: 432000（5日）- 定期的に自動更新される
WEBSUB_LEASE_SECONDS=432000

```

---

## 🧪 テスト実行

### 1. 接続確認

```python
from production_server_api_client import get_production_api_client

api_client = get_production_api_client()
is_connected = api_client.verify_connection()
print(f"接続状態: {'✅ OK' if is_connected else '❌ 失敗'}")
```

### 2. WebSub ビデオ取得テスト

```python
from youtube_core.youtube_websub import YouTubeWebSub

websub = YouTubeWebSub(channel_id="UCxxxxxxxxxxxxxxx")
websub.ensure_websub_registered()

videos = websub.get_websub_videos(limit=10)
for video in videos:
    print(f"📹 {video['title']} ({video['video_id']})")
```

### 3. ログ確認

```bash
# logs/app.log でセンターサーバー接続状況を確認
grep -E "✅|❌|Websubサーバー" logs/app.log | tail -20
```

---

## 🛡️ エラーハンドリング

### HTTP 接続エラー

```python
try:
    videos = api_client.get_websub_videos(channel_id)
except requests.ConnectionError as e:
    logger.error(f"❌ センターサーバー接続失敗: {e}")
    # フォールバック: RSS ポーリングに切り替え
```

### API レスポンスエラー

```python
if response.status_code != 200:
    logger.warning(f"⚠️ API エラー: ステータス {response.status_code}")
    # 過去のビデオキャッシュを使用、または RSS ポーリングに切り替え
```

### JSON パースエラー

```python
try:
    data = response.json()
except json.JSONDecodeError:
    logger.error(f"❌ JSON パース失敗")
    # デフォルト空リスト返却
```

### 購読登録エラー

```python
if not api_client.register_websub_client(...):
    logger.warning(f"⚠️ WebSub 購読登録失敗")
    # RSS ポーリングで継続
```

---

## 📊 統計情報

ProductionServerAPIClient が管理する統計：

```python
{
    "connected": bool,          # センターサーバー接続状態
    "base_url": str,            # 接続先 URL
    "last_request_at": str,     # 最後のリクエスト時刻
    "last_error": str,          # 最後のエラーメッセージ
    "videos_fetched": int       # 取得したビデオ数（累計）
}
```

ログで確認：

```bash
# 接続状態を確認
grep "✅ Websubサーバー" logs/app.log

# エラーを確認
grep "❌\|⚠️" logs/app.log | grep -i websub
```

---

## 🔌 既存ロジックとの統合状況

### 従来（RSS ポーリングのみ）

```
YouTube RSS → youtube_core.youtube_rss.YouTubeRSS → DB → GUI → Bluesky
```

### 現在（RSS + WebSub HTTP GET、未統合）

```
YouTube RSS ───────────────────────┐
                                    ├─ ??? （統合ロジック未実装）→ DB → GUI → Bluesky
YouTube WebSub → ProductionServerAPIClient.get_websub_videos() ┘
```

**問題点**:

1. **RSS と WebSub ビデオのフォーマット統一がない**
   - RSS: `youtube_rss.YouTubeRSS.fetch_rss_videos()` の出力
   - WebSub: `youtube_websub.YouTubeWebSub.get_websub_videos()` の出力
   - フォーマットが異なり、DB 投入時に差分処理が必要

2. **優先度制御がない**
   - WebSub が来ている場合は WebSub を優先
   - RSS は フォールバック用
   - これを自動判定する機構がない

3. **main_v3.py での呼び出し**
   - RSS ポーリング: ✅ `youtube_rss.fetch_rss_videos()` で呼び出し
   - WebSub HTTP GET: ⚠️ 呼び出し箇所不明（main_v3.py に統合されているか確認必要）

**実装予定**（添付ドキュメント記載）:
- ❌ `video_feed_integrator.py` で RSS + WebSub を統一フォーマットで処理
- ❌ WebSub 優先の優先度制御
- ❌ ソース識別フラグ付与（`source: "rss"` or `"websub"`）

---

## ⚠️ 注意事項

### 1. セ ンターサーバー接続が必須

WebSub データ取得には、本番サーバーへのネットワーク接続が必須です。

```env
# 本番環境（デフォルト）
WEBSUB_BASE_URL=https://webhook.neco-server.net

# ローカル開発
WEBSUB_BASE_URL=http://192.168.100.14:8000
```

### 2. RSS + WebSub の統合がまだ

現在のコードは以下の 2 つの独立したフロー が存在：

- **RSS ポーリング**: `config.youtube_feed_mode == "poll"` → YouTube RSS から取得
- **WebSub HTTP GET**: YouTube WebSub を手動で呼び出す → ProductionServerAPIClient から取得

**これら 2 つを統合するロジックが未実装**

### 3. ローカル WebSub サーバーは実装されていない

添付ドキュメント記載の以下は **実装されていません**：

- ❌ `websub_server.py` - FastAPI Webhook サーバー
- ❌ `video_feed_integrator.py` - 統合インターフェース
- ❌ `websub_test_panel.py` - GUI テストパネル

代わりに、**セ ンターサーバー経由の HTTP API（ProductionServerAPIClient）**を使用しています。

### 4. HTTPS 必須

YouTube WebSub 購読には HTTPS が必須です（ローカルテストはできません）。

---

## 🔧 実装チェックリスト（次のステップ）

### 緊急度: 高（v3.5.0 推奨）

- [ ] `main_v3.py` で WebSub フロー が実際に実行されているか確認
- [ ] RSS + WebSub フロー の統合ロジック実装（`video_feed_integrator.py`）
- [ ] YouTube Data API による LIVE 判定と同期
- [ ] エラー時の RSS フォールバック実装

### 緊急度: 中（v3.5.0+）

- [ ] `config.py` で WebSub 設定の完全バリデーション
- [ ] WebSub リトライロジック実装
- [ ] GUI ダッシュボードに WebSub ステータス表示追加

### 緊急度: 低（将来予定）

- [ ] ローカル WebSub サーバー実装（自家インフラ用）
- [ ] WebSub test パネル実装
- [ ] WebSub 統計情報の永続化

---

## 📚 関連ドキュメント

- [WEBSUB_IMPLEMENTATION.md](WEBSUB_IMPLEMENTATION.md) - WebSub プロトコル詳細
- [CENTER_SERVER_INTEGRATION_SPEC.md](../References/CENTER_SERVER_INTEGRATION_SPEC.md) - セ ンターサーバー仕様
- [settings.env.example](../../settings.env.example) - 設定項目
- [requirements.txt](../../requirements.txt) - 依存ライブラリ

---

## 次のステップ

1. **main_v3.py の確認** - WebSub フロー が実際に実行されているか確認
2. **RSS + WebSub 統合** - 統一フォーマット・優先度制御を実装
3. **テスト実行** - ローカル開発環境で RSS + WebSub の動作確認
4. **本番デプロイ** - セ ンターサーバーから WebSub ビデオを取得

---

**作成日**: 2025-12-24
**最終更新**: 2026-01-03
**対象版**: v3.3.0 以上
**ステータス**: ⚠️ 部分実装（センターサーバー統合版）
