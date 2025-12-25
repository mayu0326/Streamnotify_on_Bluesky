# YouTube WebSub 通知機能 - 実装ガイド

**対象バージョン**: v3.4.0+
**最終更新**: 2025-12-24
**ステータス**: ✅ 実装完了

---

## 📖 目次

1. [概要](#概要)
2. [WebSub とは](#websub-とは)
3. [導入手順](#導入手順)
4. [設定方法](#設定方法)
5. [フィード取得モード](#フィード取得モード)
6. [トンネル設定](#トンネル設定)
7. [トラブルシューティング](#トラブルシューティング)

---

## 概要

YouTube チャンネルの新着動画情報を、従来の **RSS ポーリング** ではなく **YouTube の WebSub 通知（プッシュ型）** で受け取る機能を実装しました。

### メリット

| 特徴 | RSS ポーリング | WebSub | メリット |
|:--|:--:|:--:|:--|
| リアルタイム性 | ⏱️ 数分のラグ | ⚡ ほぼリアルタイム | **WebSub が優位** |
| 負荷（API呼び出し） | 📊 定期的 | 📡 イベント時のみ | **WebSub が優位** |
| セットアップ | ✅ 簡単 | 📝 やや複雑 | **RSS が優位** |
| 安定性 | ✅ 高い | 🔄 フォールバック機能 | **同等** |

### 3つの動作モード

```
┌─────────────┬──────────────────────┬──────────────────────────────┐
│ モード      │ 説明                 │ 用途                         │
├─────────────┼──────────────────────┼──────────────────────────────┤
│ poll        │ RSS ポーリング        │ トンネル不要（従来方式）   │
│ websub      │ WebSub プッシュ       │ リアルタイム対応必須         │
│ hybrid      │ WebSub + ポーリング   │ フォールバック対応（推奨） │
└─────────────┴──────────────────────┴──────────────────────────────┘
```

---

## WebSub とは

### PubSubHubbub（パブサブハブハブ）

WebSub（旧称 PubSubHubbub）は、**Atom/RSS フィードの更新をプッシュで配信する仕組み**です。

#### 従来の RSS ポーリング

```
┌─────────────────────────────┐
│ あなたのアプリケーション    │
└────────────┬────────────────┘
             │
   5分ごとに │ RSS を取得？
             │
             ↓
     ┌────────────────┐
     │ YouTube RSS    │
     │ フィード       │
     └────────────────┘
```

**問題**: 常に RSS を確認し続ける必要がある → ラグが発生

#### WebSub プッシュ通知

```
┌────────────────────────────────┐
│ YouTube チャンネル             │
│ （新着動画投稿）               │
└─────────────┬──────────────────┘
              │
   プッシュ   │ 通知を送信
   通知       ↓
     ┌────────────────────────────┐
     │ WebSub ハブ                │
     │ （YouTube のハブサーバー）  │
     └─────────────┬──────────────┘
                   │
                   │ プッシュ通知
                   ↓
     ┌────────────────────────────┐
     │ あなたのサーバー           │
     │ Webhook エンドポイント     │
     │ /webhook/youtube           │
     └────────────────────────────┘
```

**メリット**: リアルタイムで動画情報を受け取れる

---

## 導入手順

### ステップ 1: settings.env の設定

#### 1-1 フィード取得モードを選択

```env
# poll: RSS ポーリング（従来方式、トンネル不要）
# websub: WebSub プッシュ（推奨、トンネル必須）
# hybrid: WebSub + ポーリング併用（推奨、フォールバック対応）

YOUTUBE_FEED_MODE=hybrid
```

#### 1-2 WebSub 設定（websub/hybrid モード用）

```env
# コールバック URL（トンネルを通じた HTTPS URL）
WEBSUB_CALLBACK_URL=https://your-tunnel-url.ngrok.io/webhook/youtube

# ローカルサーバーポート（デフォルト: 8765）
WEBSUB_SERVER_PORT=8765

# 購読期間（秒、デフォルト: 5日 = 432000秒）
# 範囲: 1日（86400秒）～ 30日（2592000秒）
WEBSUB_LEASE_SECONDS=432000

# ポーリング間隔（websub/hybrid モード時のバックアップ、デフォルト: 10分）
POLL_INTERVAL_MINUTES=10
```

### ステップ 2: トンネル設定（WebSub/Hybrid モード用）

WebSub を使用する場合、**HTTPS で公開可能なコールバック URL** が必須です。

#### オプション A: ngrok（推奨・簡単）

```bash
# 1. ngrok をダウンロード（https://ngrok.com）

# 2. トンネルを開始
.\ngrok http 8765

# 出力例:
# Forwarding  https://abc123.ngrok.io -> http://localhost:8765

# 3. settings.env に設定
WEBSUB_CALLBACK_URL=https://abc123.ngrok.io/webhook/youtube
```

**メリット**: セットアップ簡単、自動 HTTPS

#### オプション B: Cloudflare Tunnel

```bash
# 1. Cloudflare アカウントを作成
#    https://dash.cloudflare.com

# 2. ターミナルで実行
cloudflared tunnel --url http://localhost:8765

# 出力例:
# Your quick tunnel has been created! Visit it at (it may take some time to be reachable):
# https://xxx-yyy-zzz.trycloudflare.com

# 3. settings.env に設定
WEBSUB_CALLBACK_URL=https://xxx-yyy-zzz.trycloudflare.com/webhook/youtube
```

#### オプション C: Docker + トンネル

```bash
docker run -p 8765:8765 your-app
# その後、ngrok/Cloudflare で トンネル化
```

### ステップ 3: アプリケーション起動

```bash
python main_v3.py
```

**ログで確認**:

```
✅ WebSub マネージャーを初期化しました
   モード: hybrid
   コールバック: https://abc123.ngrok.io/webhook/youtube

🔔 YouTube WebSub を購読しています...
ハブ: https://pubsubhubbub.appspot.com
トピック: https://www.youtube.com/feeds/videos.xml?channel_id=UCxxxxxx
コールバック: https://abc123.ngrok.io/webhook/youtube

✅ WebSub 購読に成功しました（ステータス: 202）
```

---

## 設定方法

### GUI からの設定変更（v3.4.0+）

1. アプリケーション起動
2. **「🔧 プラグイン」ボタン → 「📡 WebSub 設定」タブ**
3. フィード取得モードを選択
4. コールバック URL を入力
5. **「購読する」ボタンでテスト購読**

### 設定値の説明

| 項目 | 値 | 説明 |
|:--|:--|:--|
| `YOUTUBE_FEED_MODE` | poll / websub / hybrid | フィード取得方式 |
| `WEBSUB_CALLBACK_URL` | https://... | YouTube がプッシュ通知を送信する URL |
| `WEBSUB_SERVER_PORT` | 1024～65535 | ローカルサーバーがリッスンするポート |
| `WEBSUB_LEASE_SECONDS` | 86400～2592000 | 購読有効期間 |
| `POLL_INTERVAL_MINUTES` | 5～30 | ポーリング間隔（バックアップ用） |

---

## フィード取得モード

### モード 1: poll（RSS ポーリング）

```
┌─────────────────────────────────┐
│ main_v3.py ポーリングループ    │
│                                 │
│ 1. 10分ごとに YouTube RSS 取得 │
│ 2. DB に保存                    │
│ 3. 10分待機                     │
└─────────────────────────────────┘
```

**特徴**:
- ✅ トンネル不要
- ✅ シンプル
- ❌ リアルタイム性に欠ける（数分～10分ラグ）

**推奨環境**:
- ローカル環境テスト
- ネットワークが限定的
- リアルタイム対応不要

### モード 2: websub（WebSub プッシュ）

```
┌────────────────────────────────┐
│ YouTube チャンネル             │
│ 新着動画投稿                   │
└─────────┬──────────────────────┘
          │
          └─→ WebSub ハブ
              │
              └─→ HTTPS Webhook
                  /webhook/youtube
                  │
                  └─→ DB に保存
                      GUI 更新
```

**特徴**:
- ✅ リアルタイム（秒単位）
- ✅ API 呼び出し少ない
- ❌ トンネル設定必須
- ❌ Webhook エンドポイント必須

**推奨環境**:
- 本番環境
- リアルタイム対応必須
- ネットワーク環境が整備されている

### モード 3: hybrid（ハイブリッド）

```
┌──────────────────────────────────────┐
│ 並行実行                             │
│                                      │
│ 1. WebSub 購読（プッシュ待機）       │
│ 2. 定期ポーリング（バックアップ）    │
│                                      │
│ メリット:                            │
│ - WebSub 失敗時でもポーリングで対応 │
│ - 取りこぼし防止                     │
└──────────────────────────────────────┘
```

**特徴**:
- ✅ 最も安全（フォールバック機能）
- ✅ リアルタイム対応
- ❌ トンネル設定が必要

**推奨環境**: **本番環境**（最もバランスが良い）

---

## トンネル設定

### ngrok を使用する場合（推奨）

#### Windows

```batch
# ngrok をダウンロード＆解凍
# https://ngrok.com/download

# コマンドプロンプトで実行
cd ngrok_directory
.\ngrok http 8765
```

#### Linux / Mac

```bash
# Homebrew でインストール
brew install ngrok

# トンネルを開始
ngrok http 8765
```

#### 出力

```
ngrok                                                                              (Ctrl+C to quit)

Build v3.5.0
...
Forwarding  https://abc123.ngrok.io -> http://localhost:8765
Status      online

Web Interface                 http://127.0.0.1:4040
Forwarding                    https://abc123.ngrok.io -> http://localhost:8765
```

**設定**:

```env
WEBSUB_CALLBACK_URL=https://abc123.ngrok.io/webhook/youtube
WEBSUB_SERVER_PORT=8765
```

### Cloudflare Tunnel を使用する場合

```bash
# インストール
npm install -g cloudflared
# または
brew install cloudflare/cloudflare/cloudflared

# トンネルを開始
cloudflared tunnel --url http://localhost:8765
```

**設定**:

```env
WEBSUB_CALLBACK_URL=https://xxx-yyy-zzz.trycloudflare.com/webhook/youtube
WEBSUB_SERVER_PORT=8765
```

---

## トラブルシューティング

### Q1: WebSub 購読に失敗する

**原因**:
- コールバック URL が間違っている
- トンネルが起動していない
- HTTPS でない
- YouTube のハブサーバーに接続できない

**対応**:

```
1. トンネルが起動しているか確認
   $ ngrok http 8765

2. コールバック URL を確認
   WEBSUB_CALLBACK_URL=https://xxx.ngrok.io/webhook/youtube
   （http:// ではなく https:// か確認）

3. YouTube ハブサーバーに疎通確認
   $ curl https://pubsubhubbub.appspot.com

4. ログを確認
   $ grep "WebSub" logs/app.log
```

### Q2: Webhook が呼ばれない（プッシュ通知が来ない）

**原因**:
- 購読がまだ完了していない（24時間待つ）
- Webhook エンドポイントが 200 OK を返していない
- YouTube がエンドポイントに到達できない

**対応**:

```
1. 購読状態を確認
   GUI から「🔧 プラグイン」→「WebSub 設定」で状態を確認

2. Webhook エンドポイントのログを確認
   $ grep "webhook/youtube" logs/app.log

3. 手動で購読テスト
   GUI から「購読する」ボタンで再購読

4. ポーリングで代替
   YOUTUBE_FEED_MODE=hybrid で、ポーリングをバックアップに設定
```

### Q3: トンネル URL が頻繁に変わる

**原因**: ngrok の無料版は毎回新しい URL が発行される

**対応**:

```
方法 1: ngrok Pro に有料アップグレード（固定 URL）
方法 2: Cloudflare Tunnel を使用（無料で固定 URL）
方法 3: 独自ドメインを設定（Cloudflare など）
```

### Q4: WebSub モード時、新着動画が遅延する

**原因**:
- YouTube の WebSub ハブのキャッシュ遅延
- ローカルネットワークの遅延
- トンネルの遅延

**対応**:

```
1. ハイブリッドモードを使用
   YOUTUBE_FEED_MODE=hybrid
   （ポーリングがバックアップになる）

2. ポーリング間隔を短縮
   POLL_INTERVAL_MINUTES=5

3. ネットワーク遅延を確認
   $ ping ngrok-server
```

---

## 詳細なログ出力

### WebSub 関連のログを抽出

```bash
# Linux / Mac
grep -E "(WebSub|webhook|購読)" logs/app.log

# Windows PowerShell
Select-String -Pattern "(WebSub|webhook|購読)" logs/app.log
```

### ログレベルを上げる

```env
LOG_LEVEL_APP=DEBUG
DEBUG_MODE=true
```

---

## よくある質問（FAQ）

### Q: WebSub と ポーリングはどちらを使うべき？

**A**: 以下の基準で判断してください：

- **ローカル環境・テスト** → `poll`（トンネル不要）
- **本番環境・リアルタイム必須** → `hybrid`（推奨）
- **細かい制御** → `websub`（上級）

### Q: WebSub 購読は自動で更新される？

**A**: はい。購読期間の 70% 経過時に自動更新されます。

```
購読期間: 5日（432000秒）
↓
70% 経過: 3.5日 後
↓
自動更新: 再度 WebSub 購読
```

### Q: ポーリング間隔を短くしても大丈夫？

**A**: WebSub モード時は無視されます。Hybrid モード時は短くできます。

```env
YOUTUBE_FEED_MODE=hybrid
POLL_INTERVAL_MINUTES=5  # 最短 5分（バックアップ用）
```

### Q: 複数チャンネルを監視できる？

**A**: 現在は 1 チャンネルのみ対応です。複数チャンネル監視は v3.5.0+ を参照してください。

---

## 関連ファイル

- `youtube_websub.py` - WebSub マネージャー実装
- `websub_webhook_handler.py` - Webhook ハンドラー実装
- `websub_settings_panel.py` - GUI 設定パネル
- `config.py` - 設定管理（WebSub 設定追加）
- `main_v3.py` - メインループ統合

---

## 技術仕様

### WebSub フロー

#### 購読

```
POST https://pubsubhubbub.appspot.com

hub.mode=subscribe
hub.topic=https://www.youtube.com/feeds/videos.xml?channel_id=xxx
hub.callback=https://your-domain.com/webhook/youtube
hub.lease_seconds=432000
hub.secret=<random-secret>
```

#### チャレンジ検証

```
GET https://your-domain.com/webhook/youtube?
  hub.mode=subscribe
  &hub.topic=...
  &hub.challenge=<challenge>
  &hub.lease_seconds=432000

レスポンス: <challenge> をそのまま返す
```

#### 通知ペイロード

```
POST https://your-domain.com/webhook/youtube

X-Hub-Signature: sha1=<hmac-sha1>

Body: Atom XML format
```

### HMAC 署名検証

```python
import hmac
import hashlib

# ペイロードから HMAC-SHA1 を計算
expected_digest = hmac.new(
    secret.encode('utf-8'),
    body,
    hashlib.sha1
).hexdigest()

# X-Hub-Signature ヘッダーと比較
actual_digest = signature.split("=")[1]
assert hmac.compare_digest(expected_digest, actual_digest)
```

---

**作成日**: 2025-12-24
**最後の修正**: 2025-12-24
**ステータス**: ✅ 完成・検証済み
