# Streamnotify v3 設定項目一覧

**対象バージョン**: v3.3.0+
**最終更新**: 2026-01-07
**ステータス**: ✅ 実装完了

---

- このドキュメントは `v3/settings.env.example` のセクション順に、主要な設定項目の目的と利用条件を簡潔にまとめたものです。\
細かいサンプル値やコメントは [settings.env.example](../../settings.env.example) を参照してください。

---

## 📋 基本設定（必須項目）

| 項目 | 説明 | 必須 | 例 |
|:--|:--|:--:|:--|
| `YOUTUBE_CHANNEL_ID` | 監視対象のYouTubeチャンネルID（UC形式） | ✅ | `UCxxxxxxxxxxxxxxxx` |
| `APP_MODE` | 動作モード | ⭕ | `selfpost` / `autopost` / `dry_run` / `collect` |
| `DEBUG_MODE` | デバッグモード | ⭕ | `true` / `false` |
| `TIMEZONE` | タイムゾーン設定 | ⭕ | `Asia/Tokyo` / `UTC` / `system` |
| `BLUESKY_USERNAME` | Blueskyハンドル | ✅ | `your-handle.bsky.social` |
| `BLUESKY_PASSWORD` | Blueskyアプリパスワード | ✅ | `xxxx-xxxx-xxxx-xxxx` |

### 動作モードの説明

| モード | 説明 | 投稿動作 |
|:--|:--|:--|
| `selfpost` | 手動投稿（GUIで選択） | ⭕ 手動のみ |
| `autopost` | 自動投稿（ロジック制御） | ⭕ 自動  |
| `dry_run` | テストモード | ❌ シミュレートのみ |
| `collect` | 収集のみ | ❌ 投稿機能オフ |

---

## 📡 YouTube フィード取得モード

### RSS ポーリング vs WebSub プッシュ通知

| 項目 | 説明 | デフォルト |
|:--|:--|:--|
| `YOUTUBE_FEED_MODE` | 取得モード（`poll` / `websub`） | `poll` |
| `YOUTUBE_RSS_POLL_INTERVAL_MINUTES` | RSS ポーリング間隔（最小10～最大60分） | `10` |
| `YOUTUBE_WEBSUB_POLL_INTERVAL_MINUTES` | WebSub ポーリング間隔（最小3～最大30分） | `5` |

### WebSub（Webhook）設定

`YOUTUBE_FEED_MODE=websub` 時に使用：

| 項目 | 説明 | 例 |
|:--|:--|:--|
| `WEBSUB_CLIENT_ID` | WebSub クライアント ID | `my-websub-client-v3` |
| `WEBSUB_CALLBACK_URL` | コールバック URL | `https://your-domain.com/webhook/youtube` |
| `WEBSUB_CLIENT_API_KEY` | クライアント API キー | （支援者限定機能） |
| `WEBSUB_LEASE_SECONDS` | 購読期間（秒） | `432000`（5日） |

---

## 🔧 オプション設定

### 投稿機能
- `BLUESKY_POST_ENABLED` (`True`/`False`, デフォルト: `True`) - Bluesky投稿有効化
- `PREVENT_DUPLICATE_POSTS` (`true`/`false`, デフォルト: `false`) - 重複投稿防止
- `YOUTUBE_DEDUP_ENABLED` (`true`/`false`, デフォルト: `true`) - YouTube重複排除（優先度ベース管理）

### AUTOPOST 設定（`APP_MODE=autopost` 時のみ）
- `AUTOPOST_INTERVAL_MINUTES` (デフォルト: 5, 範囲: 1-60) - 投稿間隔
- `AUTOPOST_LOOKBACK_MINUTES` (デフォルト: 30, 範囲: 5-1440) - 時間窓（再起動時の取りこぼし防止）
- `AUTOPOST_UNPOSTED_THRESHOLD` (デフォルト: 20, 範囲: 1-1000) - 未投稿動画大量検知閾値
- `AUTOPOST_INCLUDE_NORMAL` (デフォルト: `true`) - 通常動画を投稿
- `AUTOPOST_INCLUDE_PREMIERE` (デフォルト: `true`) - プレミア配信を投稿
- `YOUTUBE_LIVE_POST_DELAY` (デフォルト: `immediate`) - YouTube Live 投稿遅延設定

---

## 📝 テンプレート・画像設定（v3.1.0+）

### テンプレート パス
プラグイン導入時に自動配置されます。手動指定する場合：

| テンプレート | 用途 | デフォルトパス |
|:--|:--|:--|
| `TEMPLATE_YOUTUBE_NEW_VIDEO_PATH` | YouTube新着動画 | `templates/youtube/yt_new_video_template.txt` |
| `TEMPLATE_YOUTUBE_SCHEDULE_PATH` | YouTube Live予約 | `templates/youtube/yt_schedule_template.txt` |
| `TEMPLATE_YOUTUBE_ONLINE_PATH` | YouTube Live開始 | `templates/youtube/yt_online_template.txt` |
| `TEMPLATE_YOUTUBE_OFFLINE_PATH` | YouTube Live終了 | `templates/youtube/yt_offline_template.txt` |
| `TEMPLATE_YOUTUBE_ARCHIVE_PATH` | YouTubeアーカイブ | `templates/youtube/yt_archive_template.txt` |
| `TEMPLATE_NICO_NEW_VIDEO_PATH` | ニコニコ新着動画 | `templates/niconico/nico_new_video_template.txt` |

### 画像設定
- `BLUESKY_IMAGE_PATH` - 画像未設定時の代替画像（デフォルト: `images/default/noimage.png`）

### 画像リサイズ設定（v3.1.0+）
| 項目 | 説明 | デフォルト |
|:--|:--|:--|
| `IMAGE_RESIZE_TARGET_WIDTH` | 横長画像のターゲット幅 | `1280`px |
| `IMAGE_RESIZE_TARGET_HEIGHT` | 横長画像のターゲット高さ | `800`px |
| `IMAGE_OUTPUT_QUALITY_INITIAL` | JPEG初期品質 | `90`（1-100） |
| `IMAGE_SIZE_TARGET` | ファイルサイズ理想値 | `800000`バイト |
| `IMAGE_SIZE_THRESHOLD` | 品質低下開始閾値 | `900000`バイト |
| `IMAGE_SIZE_LIMIT` | ファイルサイズ最終上限 | `1000000`バイト（1MB） |

---

## 🔌 プラグイン設定

### YouTubeAPI 連携プラグイン
- `YOUTUBE_API_KEY` - YouTube Data API キー（UC以外の識別子対応・ライブ詳細取得に使用）

### YouTubeLive プラグイン（v3.4.0+）

#### 自動投稿モード設定
- `YOUTUBE_LIVE_AUTO_POST_MODE` (`all` / `schedule` / `live` / `archive` / `off`, デフォルト: `off`) - AUTOPOST時用統合設定
- `YOUTUBE_LIVE_AUTO_POST_SCHEDULE` (`true`/`false`, デフォルト: `true`) - SELFPOST向け: 予約枠の自動投稿
- `YOUTUBE_LIVE_AUTO_POST_LIVE` (`true`/`false`, デフォルト: `true`) - SELFPOST向け: 配信中/終了の自動投稿
- `YOUTUBE_LIVE_AUTO_POST_ARCHIVE` (`true`/`false`, デフォルト: `true`) - SELFPOST向け: アーカイブの自動投稿

#### ポーリング間隔設定（動的制御、v3.3.0+改訂版）
キャッシュ状態に応じて自動調整（ACTIVE → COMPLETED → ARCHIVE → NO_LIVE）

| 項目 | 説明 | デフォルト | 範囲 |
|:--|:--|:--|:--|
| `YOUTUBE_LIVE_POLL_INTERVAL_ACTIVE` | ACTIVE時の間隔 | `15` | 15-60分 |
| `YOUTUBE_LIVE_POLL_INTERVAL_COMPLETED_MIN` | COMPLETED最短間隔 | `60` | 30-180分 |
| `YOUTUBE_LIVE_POLL_INTERVAL_COMPLETED_MAX` | COMPLETED最大間隔 | `180` | 30-180分 |
| `YOUTUBE_LIVE_ARCHIVE_CHECK_COUNT_MAX` | ARCHIVE追跡回数 | `4` | 1-10回 |
| `YOUTUBE_LIVE_ARCHIVE_CHECK_INTERVAL` | ARCHIVE確認間隔 | `180` | 30-480分 |

### ニコニコ プラグイン
- `NICONICO_USER_ID` - 監視対象ユーザーID（数値）
- `NICONICO_USER_NAME` - ユーザー名（テンプレートで投稿者として表示、自動取得失敗時に使用）
- `NICONICO_POLL_INTERVAL` (デフォルト: `10`分、最小5分)

---

## 📊 ログ設定拡張

### グローバル設定
- `LOG_LEVEL_CONSOLE` (デフォルト: INFO) - コンソール出力レベル
- `LOG_LEVEL_FILE` (デフォルト: INFO) - ファイル出力レベル
- `LOG_RETENTION_DAYS` (デフォルト: 14) - ログファイル保持日数

### 個別ロガー設定（オプション）
ログレベル値: DEBUG, INFO, WARNING, ERROR, CRITICAL

| 項目 | 説明 |
|:--|:--|
| `LOG_LEVEL_APP` | アプリケーション全般・エラーログ |
| `LOG_LEVEL_AUDIT` | 監査ログ |
| `LOG_LEVEL_THUMBNAILS` | サムネイル再取得 |
| `LOG_LEVEL_TUNNEL` | トンネル接続 |
| `LOG_LEVEL_YOUTUBE` | YouTube監視 |
| `LOG_LEVEL_NICONICO` | Niconico監視 |
| `LOG_LEVEL_GUI` | GUI操作 |
| `LOG_LEVEL_POST_ERROR` | 投稿エラー |
| `LOG_LEVEL_POST` | 投稿イベント |

---

## 🚀 将来実装予定

以下の設定は現在コメントアウト推奨です：

### Twitch プラグイン（v4.x 計画中）
- `TWITCH_CLIENT_ID` / `TWITCH_CLIENT_SECRET`
- `TWITCH_BROADCASTER_ID`
- Webhook系設定
- `RETRY_MAX` / `RETRY_WAIT`

### トンネル通信（計画中）
- `TUNNEL_SERVICE` / `TUNNEL_CMD`
- Cloudflare / ngrok / LocalTunnel 設定

### 動画投稿通知拡張（計画中）
- Discord通知設定

---

## ✅ セットアップチェックリスト

初回セットアップ時：

- [ ] `YOUTUBE_CHANNEL_ID` を設定（UC形式確認）
- [ ] `BLUESKY_USERNAME` と `BLUESKY_PASSWORD` を設定
- [ ] `APP_MODE=selfpost` で起動テスト
- [ ] `DEBUG_MODE=true` で詳細ログ確認
- [ ] `AUTOPOST_*` は `APP_MODE=autopost` 以外では無視されることを理解

詳細は [INSTALLATION_SETUP.md](./INSTALLATION_SETUP.md) を参照してください。
