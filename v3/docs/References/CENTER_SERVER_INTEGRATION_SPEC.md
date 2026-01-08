# Streamnotify WebSub センターサーバー統合仕様書

**対象バージョン**: v3.3.0+
**サーバー実装**: FastAPI WebSub Hub
**最終更新**: 2026-01-08
**ステータス**: ✅ 本番稼働中（YouTube WebSub 対応）

---

## 目次

1. [概要](#概要)
2. [WebSub ワークフロー](#websub-ワークフロー)
3. [API エンドポイント仕様](#api-エンドポイント仕様)
4. [エンドポイント詳細](#エンドポイント詳細)
5. [エラーハンドリング](#エラーハンドリング)
6. [セキュリティ](#セキュリティ)
7. [クライアント側実装](#クライアント側実装)
8. [トラブルシューティング](#トラブルシューティング)

---

## 概要

### 目的

Streamnotify WebSub センターサーバーは、複数のクライアント（ユーザーのローカル環境）に対して、  \
YouTube の新着動画情報を **PubSubHubbub プロトコル経由で一元配信** するプッシュ通知サーバーです。

### 利点

- ⚡ **リアルタイム検知**: RSS ポーリング（3-5分遅延）ではなく、YouTube から直接プッシュ通知を受け取る
- 🔄 **一元管理**: 複数のクライアントからの購読を一箇所で管理
- 📊 **効率性**: YouTube からの API 呼び出しが最小化される
- 🎯 **スケーラビリティ**: 複数ユーザーへの同時配信に対応

### 対応プラットフォーム

| プラットフォーム | ステータス | 備考 |
|:--|:--|:--|
| **YouTube** | ✅ 本番稼働中 | WebSub フルサポート（新着動画検知） |
| **Niconico** | 🔜 将来実装予定 | - |
| **Twitch** | 🔜 将来実装予定 | - |

---

## WebSub ワークフロー

```
┌─────────────────────────────────────────────────────────────────┐
│                       YouTube RSS Hub                           │
│                  (PubSubHubbub Publisher)                       │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 │ (1) Subscribe to channel feed
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│          Streamnotify WebSub Center Server                      │
│              (PubSubHubbub Hub / Subscriber)                    │
│                                                                 │
│  - 購読管理（clients, subscriptions テーブル）               │
│  - YouTube からの通知受け取り（/pubsub エンドポイント）       │
│  - クライアント登録（/register エンドポイント）                │
│  - 動画情報キャッシング（channel_id ごとの SQLite DB）       │
└────────────────┬────────────────────────────────────────────────┘
                 │
        ┌────────┴────────┬────────┬────────┐
        │                 │        │        │
   (2) Notify          (3) Store  (4) Push  │
   video info          in cache    to client│
        │                 │        │        │
        ▼                 ▼        ▼        ▼
    ┌───────────────────────────────────────────────┐
    │  Client 1              Client 2  ...  Client N  │
    │  (Streamnotify        (Streamnotify ...        │
    │   v3.3.0)             v3.3.0)                  │
    │  WEBSUB_CALLBACK_URL  WEBSUB_CALLBACK_URL      │
    └───────────────────────────────────────────────┘
        │                    │
        ▼                    ▼
    ┌────────────┐      ┌────────────┐
    │ Local DB   │      │ Local DB   │
    │(video_list)│      │(video_list)│
    └────────────┘      └────────────┘
```

### フロー詳細

#### Phase 1: 初回購読（Setup）

```
User A (Local Machine A)
    │
    ├─ settings.env で WebSub 設定
    │  - YOUTUBE_FEED_MODE=websub
    │  - WEBSUB_CALLBACK_URL=https://user-a-webhook-endpoint.local/webhook
    │  - WEBSUB_CLIENT_ID=user_a_client
    │  - WEBSUB_CLIENT_API_KEY=secret_api_key_a
    │
    └─→ POST /register
        ├─ Request:
        │  {
        │    "client_id": "user_a_client",
        │    "channel_id": "UCxxxxxx",
        │    "callback_url": "https://user-a-webhook-endpoint.local/webhook"
        │  }
        │  Header: X-Client-API-Key: secret_api_key_a
        │
        └─→ Center Server (DB: subscriptions)
            ├─ 登録: (user_a_client, UCxxxxxx, webhook_url)
            └─ Response: {"status": "ok"}
```

#### Phase 2: 新着動画通知（Push）

```
YouTube RSS Hub
    │
    └─→ POST /pubsub (XML Atom Feed)
        │
        ├─ Parse XML:
        │  - <yt:channelId>UCxxxxxx</yt:channelId>
        │  - <yt:videoId>dQw4w9WgXcQ</yt:videoId>
        │  - <title>New Video Title</title>
        │
        └─→ Center Server
            ├─ (1) SQLite に保存
            │  - DB: /home/mayuneco/webhook_app/data/subscribers/UCxxxxxx.db
            │  - Table: videos
            │  - Record: (dQw4w9WgXcQ, title, ...)
            │
            ├─ (2) 購読者を検索
            │  - Query: subscriptions WHERE channel_id = 'UCxxxxxx'
            │  - Found: [user_a_client, user_b_client, ...]
            │
            └─→ (3) 各クライアントに通知
                ├─→ POST https://user-a-webhook-endpoint.local/webhook
                │   Body: (channel_id, video_id, title 等)
                │
                ├─→ POST https://user-b-webhook-endpoint.local/webhook
                │   Body: (channel_id, video_id, title 等)
                │
                └─→ [Similar for other clients...]
```

---

## API エンドポイント仕様

### エンドポイント一覧

| メソッド | エンドポイント | 用途 | 認証 |
|:--|:--|:--|:--|
| GET/POST | `/pubsub` | WebSub verify/notify（YouTube → Server） | Verify token |
| POST | `/register` | クライアント登録（Client → Server） | API Key |
| GET | `/videos` | 動画情報取得（Client → Server） | - |
| GET | `/health` | ヘルスチェック | - |
| GET | `/client/health` | クライアント登録状況確認 | API Key |

---

## エンドポイント詳細

### データベーススキーマ

#### clients テーブル（サーバー側）

| カラム | 型 | 説明 |
|:--|:--|:--|
| id | INTEGER PRIMARY KEY | 自動採番 ID |
| client_id | TEXT UNIQUE NOT NULL | クライアント識別子 |
| apikey | TEXT NOT NULL | API 認証キー |
| created_at | TEXT | 登録日時（自動） |

#### subscriptions テーブル（サーバー側）

| カラム | 型 | 説明 |
|:--|:--|:--|
| id | INTEGER PRIMARY KEY | 自動採番 ID |
| client_id | TEXT NOT NULL | クライアント識別子 |
| channel_id | TEXT NOT NULL | YouTube チャンネル ID |
| callback_url | TEXT NOT NULL | Webhook コールバック URL |
| created_at | TEXT | 登録日時（自動） |
| 複合キー | UNIQUE | (client_id, channel_id) の組み合わせで一意 |

#### videos テーブル（channel_id ごとの SQLite DB）

各 channel_id に対して専用の SQLite DB が作成されます。
DB ファイルパス: `/home/mayuneco/webhook_app/data/subscribers/<channel_id>.db`

| カラム | 型 | デフォルト | 説明 |
|:--|:--|:--|:--|
| id | INTEGER | PRIMARY KEY（自動採番） | 自動採番 ID |
| video_id | TEXT | NOT NULL, UNIQUE | YouTube 動画 ID |
| channel_id | TEXT | NOT NULL | YouTube チャンネル ID |
| title | TEXT | | 動画タイトル |
| video_url | TEXT | NULL | 動画 URL（予約フィールド、現在未実装） |
| published_at | TEXT | NULL | 公開日時（ISO 8601 形式、現在未実装） |
| created_at | TEXT | CURRENT_TIMESTAMP | DB 登録日時（自動） |

**テーブル作成 SQL**:
```sql
CREATE TABLE IF NOT EXISTS videos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id TEXT NOT NULL UNIQUE,
    channel_id TEXT NOT NULL,
    title TEXT,
    video_url TEXT,
    published_at TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

**現在の実装状況**:
- ✅ `video_id`, `channel_id`, `title`, `created_at` は Atom XML 通知から抽出・保存
- ⚠️ `video_url`, `published_at` は将来実装（WebSubサーバー側で YouTube API 呼び出しが必要）

---

### 1. `/pubsub` - WebSub エンドポイント

YouTube RSS Hub がこのエンドポイントに対して、購読確認と新着動画通知を送信します。

#### 1.1 Verify リクエスト（GET）

YouTube が購読を確認する際に呼び出します。

**リクエスト**:
```
GET /pubsub?hub.mode=subscribe&hub.topic=https://www.youtube.com/xml/feeds/videos.xml?channel_id=UCxxxxxx&hub.challenge=xyz&hub.verify_token=neco-verify-token
```

**パラメータ**:
| パラメータ | 説明 |
|:--|:--|
| `hub.mode` | `subscribe` または `unsubscribe` |
| `hub.topic` | YouTube RSS フィード URL |
| `hub.challenge` | 検証用チャレンジトークン |
| `hub.verify_token` | 検証用トークン（固定値: `neco-verify-token`） |

**レスポンス**:
```
HTTP 200 OK
Content-Type: text/plain

xyz
```

**実装例** (Python):
```python
@app.get("/pubsub", response_class=PlainTextResponse)
async def pubsub_verify(request: Request):
    params = dict(request.query_params)
    challenge = params.get("hub.challenge")
    verify_token = params.get("hub.verify_token")

    # verify_token が提供されている場合、VERIFY_TOKEN と一致することを確認
    if verify_token and verify_token != VERIFY_TOKEN:  # VERIFY_TOKEN = "neco-verify-token"
        raise HTTPException(status_code=403, detail="verify_token mismatch")

    if challenge:
        return PlainTextResponse(content=challenge, status_code=200)

    raise HTTPException(status_code=400, detail="missing hub.challenge")
```

#### 1.2 通知リクエスト（POST）

YouTube が新着動画を検知した際に、このエンドポイントに XML フィードを POST します。

**リクエスト**:
```
POST /pubsub
Content-Type: application/atom+xml

<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:yt="http://www.youtube.com/xml/schemas/2015">
  <title>YouTube Feed</title>
  <link rel="hub" href="https://pubsubhubbub.appspot.com/"/>
  <link rel="self" href="https://www.youtube.com/xml/feeds/videos.xml?channel_id=UCxxxxxx"/>
  <id>yt:channel:UCxxxxxx</id>
  <updated>2026-01-03T10:30:00+00:00</updated>

  <entry>
    <id>yt:video:dQw4w9WgXcQ</id>
    <yt:videoId>dQw4w9WgXcQ</yt:videoId>
    <yt:channelId>UCxxxxxx</yt:channelId>
    <title>New Video Title</title>
    <link rel="alternate" href="https://www.youtube.com/watch?v=dQw4w9WgXcQ"/>
    <author>
      <name>Channel Name</name>
      <uri>http://www.youtube.com/channel/UCxxxxxx</uri>
    </author>
    <published>2026-01-03T10:30:00+00:00</published>
    <updated>2026-01-03T10:30:00+00:00</updated>
  </entry>
</feed>
```

**パース処理**:
```python
@app.post("/pubsub")
async def pubsub_notify(request: Request):
    body_bytes = await request.body()
    body_text = body_bytes.decode("utf-8", errors="ignore")

    try:
        ns = {
            "atom": "http://www.w3.org/2005/Atom",
            "yt": "http://www.youtube.com/xml/schemas/2015",
        }
        root = ET.fromstring(body_text)

        for entry in root.findall("{http://www.w3.org/2005/Atom}entry"):
            # channel_id パース
            channel_id_elem = entry.find("yt:channelId", ns)
            if channel_id_elem is not None:
                channel_id = channel_id_elem.text
            else:
                # フォールバック: author URI から抽出
                author = entry.find("{http://www.w3.org/2005/Atom}author")
                uri_elem = (
                    author.find("{http://www.w3.org/2005/Atom}uri")
                    if author is not None
                    else None
                )
                author_uri = uri_elem.text if uri_elem is not None else ""
                channel_id = author_uri.rsplit("/", 1)[-1] if author_uri else None

            # video_id パース
            video_id_elem = entry.find("yt:videoId", ns)
            if video_id_elem is not None:
                video_id = video_id_elem.text
            else:
                # フォールバック: id から抽出
                entry_id_elem = entry.find("{http://www.w3.org/2005/Atom}id")
                entry_id = entry_id_elem.text if entry_id_elem is not None else ""
                if entry_id.startswith("yt:video:"):
                    video_id = entry_id.split("yt:video:")[-1]
                else:
                    video_id = None

            # title パース
            title_elem = entry.find("{http://www.w3.org/2005/Atom}title")
            title = title_elem.text if title_elem is not None else ""

            # SQLite に保存
            insert_video(
                channel_id=channel_id,
                video_id=video_id,
                title=title,
                video_url=None,
                published_at=None,
            )

            # ★ 将来実装: 登録済みクライアントへの転送
            # subscribers = get_subscribers_for_channel(channel_id)
            # for client_id, callback_url in subscribers:
            #     forward_to_client(callback_url, channel_id, video_id, title)

    except Exception as e:
        print("XML parse error:", e)

    return {"status": "ok"}
```

**レスポンス**:
```json
HTTP 200 OK
Content-Type: application/json

{"status": "ok"}
```

---

### 2. `/register` - クライアント登録エンドポイント

クライアント（ユーザーのローカル環境）が WebSub 購読登録を要求します。

**リクエスト**:
```
POST /register
Content-Type: application/json
X-Client-API-Key: secret_api_key_a

{
  "client_id": "user_a_client",
  "channel_id": "UCxxxxxx",
  "callback_url": "https://user-a-machine.ngrok.io/webhook"
}
```

**リクエスト パラメータ**:

| フィールド | 型 | 説明 |
|:--|:--|:--|
| `client_id` | str | クライアント識別子（settings.env で指定） |
| `channel_id` | str | YouTube チャンネル ID（例: UCxxxxxx） |
| `callback_url` | URL | Webhook コールバック URL（このクライアントが受け取る URL） |

**ヘッダ**:

| ヘッダ | 説明 |
|:--|:--|
| `X-Client-API-Key` | API 認証キー（settings.env で指定） |

**認証フロー**:

```python
@app.post("/register")
async def register_subscriber(
    body: RegisterRequest,
    x_client_api_key: str = Header(..., alias="X-Client-API-Key"),
):
    # Step 1: client_id に対応する API キーを DB から取得
    expected_key = get_client_apikey(body.client_id)
    if expected_key is None:
        raise HTTPException(status_code=403, detail="Unknown client_id")

    # Step 2: 提供されたキーと比較
    if x_client_api_key != expected_key:
        raise HTTPException(status_code=401, detail="Invalid API key")

    # Step 3: 認証 OK → subscriptions テーブルに登録
    # 同じ client_id/channel_id の組み合わせは callback_url で上書き
    add_subscription(
        client_id=body.client_id,
        channel_id=body.channel_id,
        callback_url=str(body.callback_url),
    )
    return {"status": "ok"}
```

**レスポンス**:
```json
HTTP 200 OK
Content-Type: application/json

{"status": "ok"}
```

**エラーレスポンス**:

| ステータス | 説明 |
|:--|:--|
| 400 | リクエストボディが不正 |
| 401 | API キー不正（`X-Client-API-Key` が一致しない） |
| 403 | Unknown client_id（DB に登録されていない） |

---

### 3. `/videos` - 動画情報取得エンドポイント

クライアントが、センターサーバーにキャッシュされている動画情報を取得します。

#### 実装概要

このエンドポイントは、指定された `channel_id` に対応する SQLite DB から最新の動画情報を取得し、
JSON 形式で クライアントに返します。

**実装例** (Python / FastAPI):
```python
@app.get("/videos")
async def list_videos(
    channel_id: str = Query(..., description="YouTube channel ID"),
    limit: int = Query(50, ge=1, le=200),
):
    """Get videos for a specific channel from WebSub cache"""

    # channel_id に対応する DB ファイルパスを構築
    safe_channel_id = sanitize_channel_id(channel_id)
    db_path = Path(f"/home/mayuneco/webhook_app/data/subscribers/{safe_channel_id}.db")

    if not db_path.exists():
        # 該当チャンネルの動画がまだ通知されていない
        raise HTTPException(
            status_code=404,
            detail="No videos found for this channel"
        )

    try:
        conn = sqlite3.connect(str(db_path), timeout=5)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # 最新の動画から順に取得
        cur.execute(
            """
            SELECT id, video_id, channel_id, title, video_url, published_at, created_at
            FROM videos
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = cur.fetchall()
        conn.close()

        return {
            "channel_id": channel_id,
            "count": len(rows),
            "items": [dict(r) for r in rows],
        }
    except Exception as e:
        logger.error(f"Error retrieving videos for {channel_id}: {e}")
        raise HTTPException(status_code=500, detail="Database error")
```

**キーポイント**:
- DB パスは `channel_id` から安全に構築（ディレクトリトラバーサル対策）
- `video_url` と `published_at` は現在 NULL が返される可能性あり（将来実装）
- `limit` は 1-200 の範囲に制限（DB へのクエリ負荷軽減）

**リクエスト**:
```
GET /videos?channel_id=UCxxxxxx&limit=50
```

**クエリ パラメータ**:

| パラメータ | 型 | デフォルト | 説明 |
|:--|:--|:--|:--|
| `channel_id` | str | **必須** | YouTube チャンネル ID |
| `limit` | int | 50 | 取得するレコード数（1-200） |

**レスポンス**:
```json
HTTP 200 OK
Content-Type: application/json

{
  "channel_id": "UCxxxxxx",
  "count": 3,
  "items": [
    {
      "id": 1,
      "video_id": "dQw4w9WgXcQ",
      "channel_id": "UCxxxxxx",
      "title": "新作ゲーム紹介配信",
      "video_url": null,
      "published_at": null,
      "created_at": "2026-01-08T10:30:00"
    },
    {
      "id": 2,
      "video_id": "9bZkp7q19f0",
      "channel_id": "UCxxxxxx",
      "title": "企画配信 #100",
      "video_url": null,
      "published_at": null,
      "created_at": "2026-01-08T10:25:00"
    },
    {
      "id": 3,
      "video_id": "aBcD1234EfG",
      "channel_id": "UCxxxxxx",
      "title": "ライブ配信 - 雑談",
      "video_url": null,
      "published_at": null,
      "created_at": "2026-01-07T18:45:00"
    }
  ]
}
```

**フィールド説明**:

| フィールド | 型 | 説明 |
|:--|:--|:--|
| `channel_id` | string | リクエストで指定されたチャンネル ID |
| `count` | integer | 返されたアイテム数 |
| `items[].id` | integer | サーバー側の自動採番 ID |
| `items[].video_id` | string | YouTube 動画 ID（短縮 ID） |
| `items[].channel_id` | string | YouTube チャンネル ID |
| `items[].title` | string | 動画タイトル（Atom XML から抽出） |
| `items[].video_url` | string \| null | 動画 URL（現在 NULL、将来実装） |
| `items[].published_at` | string \| null | 公開日時 ISO 8601 形式（現在 NULL、将来実装） |
| `items[].created_at` | string | サーバー側の登録日時（RFC3339 形式） |

**エラーレスポンス**:

| ステータス | 説明 | 対応 |
|:--|:--|:--|
| 404 | 指定された channel_id が見つからない | YouTube からまだ動画通知を受け取っていない、または typo |
| 500 | サーバー側エラー（DB アクセス失敗等） | サーバーのログを確認（管理者に報告） |

**例: 404 レスポンス**:
```json
HTTP 404 Not Found
Content-Type: application/json

{
  "detail": "No videos found for this channel"
}
```

---

### 実装上の重要な注意事項

#### 1. データベースファイルの安全な構築

`channel_id` からファイルパスを構築する際は、**ディレクトリトラバーサル攻撃を防ぐ必要があります**。

❌ **危険な実装**:
```python
# NG: 直接 channel_id を使用
db_path = f"/home/mayuneco/webhook_app/data/subscribers/{channel_id}.db"  # UCxxxxxx/../../../etc/passwd.db
```

✅ **安全な実装**:
```python
# OK: チャンネルID を検証＆サニタイズ
def sanitize_channel_id(channel_id: str) -> str:
    # チャンネルID は UC で始まる 24 文字の固定長
    if not re.match(r'^UC[a-zA-Z0-9_-]{22}$', channel_id):
        raise ValueError(f"Invalid channel_id format: {channel_id}")
    return channel_id

safe_channel_id = sanitize_channel_id(channel_id)
db_path = Path(f"/home/mayuneco/webhook_app/data/subscribers/{safe_channel_id}.db")
```

#### 2. NULL フィールドの取り扱い

現在、`video_url` と `published_at` は常に `null` が返されます。
クライアント側での処理:

```python
# youtube_websub.py での実装例
def fetch_feed(self) -> List[Dict]:
    items = self.api_client.get_websub_videos(
        channel_id=self.channel_id,
        limit=15,
    )

    videos = []
    for item in items:
        video = {
            "video_id": item["video_id"],
            "title": item["title"],
            "channel_name": item.get("channel_name", ""),  # 将来実装時に利用可能
            "published_at": item.get("published_at"),  # 現在 None

            # WebSub データが不完全な場合は API で補完
            # → youtube_api_plugin で classification 実行
        }
        videos.append(video)

    return videos
```

#### 3. パフォーマンス考慮事項

**大量レコードの取得時**:
- `limit` パラメータは 1-200 に制限（クエリ負荷軽減）
- ページネーションの実装を検討（offset パラメータの追加）
- インデックスを `channel_id` と `created_at` に設定

**データベース接続**:
```python
# タイムアウト設定（5秒以上推奨）
conn = sqlite3.connect(str(db_path), timeout=5)

# コネクション不足防止
conn.close()  # 必ず close()
# または context manager を使用
with sqlite3.connect(str(db_path), timeout=5) as conn:
    ...
```

#### 4. WebSubサーバー側の将来拡張（シナリオB）

クライアント側が API 呼び出しを削減するには、WebSubサーバーが以下を拡張する必要があります：

**POST /pubsub で以下を追加実装**:
- YouTube API を呼び出して `channel_name` を取得
- `liveStreamingDetails` (scheduledStartTime, actualStartTime, actualEndTime) を取得
- `is_premiere` フラグを判定

```python
# WebSub サーバーの将来実装例
def post_pubsub(request):
    for video_id in parsed_videos:
        # Atom XML から基本情報を抽出
        video_data = {...}

        # ★ 新: YouTube API で追加情報を取得
        try:
            api_response = youtube.videos().list(
                part="snippet,liveStreamingDetails",
                id=video_id
            ).execute()

            video_data["channel_name"] = api_response["items"][0]["snippet"]["channelTitle"]
            video_data["scheduled_start_time"] = ...
            video_data["actual_start_time"] = ...
            video_data["is_premiere"] = ...
        except Exception:
            # API 失敗時は基本情報のみで保存
            pass

        insert_video(video_data)
```

詳細は `youtube_data_analysis_websub_vs_api.md` セクション7～8 を参照。

---

### 4. `/health` - ヘルスチェック

サーバーの稼働状況を確認します（認証不要）。

**リクエスト**:
```
GET /health
```

**レスポンス**:
```json
HTTP 200 OK
Content-Type: application/json

{"status": "ok"}
```

---

### 5. `/client/health` - クライアント登録状況確認

クライアントの登録状況と特定のチャンネル購読の有無を確認します。

**リクエスト**:
```
GET /client/health?client_id=your_client_id&channel_id=UCxxxxxx
X-Client-API-Key: your_secret_api_key
```

**クエリ パラメータ**:

| パラメータ | 型 | 必須 | 説明 |
|:--|:--|:--|:--|
| `client_id` | str | ✅ | クライアント識別子 |
| `channel_id` | str | ❌ | YouTube チャンネル ID（省略時は全体確認） |

**ヘッダ**:

| ヘッダ | 説明 |
|:--|:--|
| `X-Client-API-Key` | API 認証キー（必須） |

**実装例** (Python):
```python
@app.get("/client/health")
async def client_health(
    client_id: str = Query(...),
    channel_id: str | None = Query(None),
    x_client_api_key: str = Header(..., alias="X-Client-API-Key"),
):
    # client_id の APIキーチェック
    expected_key = get_client_apikey(client_id)
    if expected_key is None:
        raise HTTPException(status_code=403, detail="Unknown client_id")

    if x_client_api_key != expected_key:
        raise HTTPException(status_code=401, detail="Invalid API key")

    # 登録状況確認
    ensure_subscribers_db_initialized()
    conn = sqlite3.connect(SUBSCRIBERS_DB, timeout=5)
    cur = conn.cursor()

    if channel_id:
        cur.execute(
            "SELECT 1 FROM subscriptions WHERE client_id = ? AND channel_id = ?",
            (client_id, channel_id),
        )
    else:
        cur.execute(
            "SELECT 1 FROM subscriptions WHERE client_id = ?",
            (client_id,),
        )

    row = cur.fetchone()
    conn.close()

    return {
        "status": "ok",
        "client_registered": expected_key is not None,
        "subscription_exists": row is not None,
    }
```

**レスポンス**:
```json
HTTP 200 OK
Content-Type: application/json

{
  "status": "ok",
  "client_registered": true,
  "subscription_exists": true
}
```

**パラメータ説明**:

| フィールド | 説明 |
|:--|:--|
| `status` | リクエスト結果（常に "ok"） |
| `client_registered` | クライアント ID がサーバーに登録されているか |
| `subscription_exists` | channel_id が指定された場合、その購読が存在するか |

---

## エラーハンドリング

### HTTP ステータスコード

| ステータス | 原因 | 対応 |
|:--|:--|:--|
| 200 | 成功 | - |
| 400 | リクエスト形式が不正 | リクエスト内容を確認 |
| 401 | 認証失敗（API キー不正） | API キーを確認（settings.env） |
| 403 | 認可失敗（client_id 未登録） | client_id がサーバーに登録されているか確認 |
| 404 | リソースが見つからない | channel_id が正しいか確認、または動画情報がまだ同期されていない可能性 |
| 500 | サーバーエラー | サーバーのログを確認 |

### 一般的なエラーシナリオ

#### シナリオ 1: API キー不正

**現象**: `POST /register` で 401 エラー

**原因**:
- settings.env の `WEBSUB_CLIENT_API_KEY` が誤っている
- サーバーのデータベースに登録されている API キーと一致していない

**対応**:
```bash
# 1. settings.env を確認
cat v3/settings.env | grep WEBSUB_CLIENT_API_KEY

# 2. サーバーのクライアント DB を確認（サーバー管理者）
sqlite3 /home/mayuneco/webhook_app/data/subscribers_map.db
> SELECT * FROM clients WHERE client_id = 'your_client_id';
```

#### シナリオ 2: Unknown client_id

**現象**: `POST /register` で 403 エラー

**原因**:
- `WEBSUB_CLIENT_ID` がサーバーのデータベースに登録されていない

**対応**:
- サーバー管理者に `client_id` と `api_key` の登録を依頼

---

## セキュリティ

### 認証メカニズム

#### WebSub verify_token

- **用途**: YouTube がセンターサーバーの正当性を検証
- **固定値**: `neco-verify-token`
- **変更方法**: サーバー側コードの `VERIFY_TOKEN` 定数を変更

#### API キー（X-Client-API-Key）

- **用途**: クライアントがサーバーに対して自身の正当性を証明
- **格納場所**: サーバーの SQLite DB（`clients.apikey`）
- **管理方法**:
  - 一意の API キーを各クライアント用に生成
  - settings.env の `WEBSUB_CLIENT_API_KEY` に記載

### データベース保護

#### 情報の分離

**subscriptions テーブル** (購読情報):
- `client_id` (クライアント識別子)
- `channel_id` (YouTube チャンネル ID)
- `callback_url` (Webhook URL)

⚠️ **注意**: `callback_url` は平文で保存されます。  \
ネットワークトラフィックは HTTPS で暗号化してください（ngrok、Cloudflare Tunnel 等）

#### アクセス制御

| 操作 | アクセス元 | 認証 |
|:--|:--|:--|
| `/pubsub` (Verify) | YouTube | verify_token |
| `/pubsub` (Notify) | YouTube | - |
| `/register` | クライアント | API key |
| `/videos` | クライアント | - |
| `/health` | 任意 | - |

### ベストプラクティス

1. **API キーの管理**:
   - 複雑な値を使用（例: UUID4）
   - 定期的にローテーション
   - 設定ファイルに平文で記載しない（暗号化を検討）

2. **通信の暗号化**:
   - callback_url は HTTPS のみ対応
   - クライアント ↔ サーバーも HTTPS 推奨

3. **ログ出力**:
   - API キーをログに出力しない
   - callback_url も極力ログに出力しない

---

## クライアント側実装

### settings.env 設定

WebSub モードを使用する場合、`settings.env` に以下を設定します：

```env
# YouTube フィード取得モード
YOUTUBE_FEED_MODE=websub

# WebSub センターサーバー設定
WEBSUB_CLIENT_ID=your_unique_client_id
WEBSUB_CLIENT_API_KEY=your_secret_api_key
WEBSUB_CALLBACK_URL=https://your-machine-webhook-endpoint.local/webhook

# WebSub ポーリング間隔（3-30分、デフォルト: 5分）
YOUTUBE_WEBSUB_POLL_INTERVAL_MINUTES=5

# WebSub ローカルサーバーポート（デフォルト: 8765）
WEBSUB_SERVER_PORT=8765
```

### Webhook エンドポイントの実装

クライアントは、センターサーバーからプッシュ通知を受け取るための Webhook エンドポイントを実装する必要があります。

#### Flask 実装例

```python
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/webhook", methods=["POST"])
def webhook():
    """
    センターサーバーから WebSub 通知を受け取る
    """
    data = request.get_json()

    channel_id = data.get("channel_id")
    video_id = data.get("video_id")
    title = data.get("title")

    # ローカル DB に保存、または投稿キューに追加
    print(f"📺 New video: {title} ({video_id})")

    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    # 設定で指定されたポートでリッスン
    app.run(host="0.0.0.0", port=8765, debug=False)
```

#### 非同期処理

通知を受け取ったら、メインアプリケーションのキューに追加するなどして、  \
非同期で処理することを推奨します（webhook は素早く 200 OK を返すべき）。

### クライアント初期化フロー

```python
# main.py または起動時
from config import get_config

config = get_config("settings.env")

if config.youtube_feed_mode == "websub":
    # WebSub モード初期化
    websub_client = WebSubClient(
        client_id=config.websub_client_id,
        api_key=config.websub_client_api_key,
        callback_url=config.websub_callback_url,
        center_server_url="https://center-server.example.com",
    )

    # チャンネル登録
    websub_client.register_channel(config.youtube_channel_id)

    # または複数チャンネル
    for channel_id in config.youtube_channel_ids:
        websub_client.register_channel(channel_id)
```

---

## トラブルシューティング

### Q: `/register` エンドポイントで 403 Forbidden が返される

**A**: 以下を確認してください：

1. **client_id がサーバーに登録されているか**:
   ```bash
   # サーバーのデータベースを確認（サーバー管理者）
   sqlite3 /home/mayuneco/webhook_app/data/subscribers_map.db
   > SELECT * FROM clients;
   ```

2. **settings.env の WEBSUB_CLIENT_ID が正しいか**:
   ```bash
   grep WEBSUB_CLIENT_ID v3/settings.env
   ```

### Q: `/register` エンドポイントで 401 Unauthorized が返される

**A**: API キーが一致していません：

1. **settings.env の WEBSUB_CLIENT_API_KEY を確認**:
   ```bash
   grep WEBSUB_CLIENT_API_KEY v3/settings.env
   ```

2. **サーバーに登録されているキーを確認**（サーバー管理者）:
   ```bash
   sqlite3 /home/mayuneco/webhook_app/data/subscribers_map.db
   > SELECT apikey FROM clients WHERE client_id = 'your_client_id';
   ```

3. **両者が一致していることを確認** → 一致していなければ API キーを更新

### Q: 動画がセンターサーバーに到達しているが、クライアントに通知されない

**A**: 以下を確認してください：

1. **Webhook エンドポイントが正しく設定されているか**:
   ```bash
   curl -X GET "https://center-server/videos?channel_id=UCxxxxxx&limit=5"
   ```
   レスポンスが返ってくるか確認

2. **callback_url が HTTPS か**（HTTP は非対応）:
   ```bash
   grep WEBSUB_CALLBACK_URL v3/settings.env
   ```

3. **ファイアウォール設定**:
   - センターサーバーからのアウトバウンド通信が許可されているか
   - クライアントの Webhook ポートが開いているか

### Q: パフォーマンス・スケーラビリティに関する質問

**A**: 以下の最適化を検討してください：

- **SQLite のインデックス**: `channel_id` と `video_id` にインデックスを設定
- **キャッシュ戦略**: 古い動画情報は自動削除（例: 30日以上前）
- **非同期処理**: Webhook 通知を非同期キューで処理
- **データベース**: 大規模運用では PostgreSQL への移行を検討

---

## 参考資料

### 関連ドキュメント

- [YouTube データフロー調査: WebSub vs API](../local/youtube_data_analysis_websub_vs_api.md) - WebSub データ形式・API 削減シナリオの詳細
- [ARCHITECTURE_AND_DESIGN.md](ARCHITECTURE_AND_DESIGN.md) - 全体アーキテクチャ
- [PLUGIN_SYSTEM.md](PLUGIN_SYSTEM.md) - プラグイン実装方法

### 外部リソース

- [PubSubHubbub 仕様](https://pubsubhubbub.appspot.com/)
- [YouTube RSS フィード & Push Notifications](https://developers.google.com/youtube/v3/guides/push_notifications)
- [Atom Feed 仕様（RFC 4287）](https://www.rfc-editor.org/rfc/rfc4287)
- [YouTube Data API v3](https://developers.google.com/youtube/v3)

### クライアント側実装の参考

- クライアント v3.3.0+: `v3/youtube_core/youtube_websub.py` - ProductionServerAPIClient の使用例
- API 連携: `v3/plugins/youtube/youtube_api_plugin.py` - classification ロジック

---

**作成日**: 2026-01-03
**最終更新**: 2026-01-08
**ステータス**: ✅ 本番環境で稼働中（YouTube WebSub のみ対応）
**更新予定**: v4.0.0+ で Niconico/Twitch 対応予定
