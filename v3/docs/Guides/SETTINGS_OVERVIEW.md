# Streamnotify v3 設定項目一覧

このドキュメントは `v3/settings.env.example` のセクション順に、主要な設定項目の目的と利用条件を簡潔にまとめたものです。詳細なサンプル値やコメントは [settings.env.example](../../settings.env.example) を参照してください。

---

## 📋 基本設定（必須項目）

| 項目 | 説明 | 必須 | 例 |
|:--|:--|:--:|:--|
| `YOUTUBE_CHANNEL_ID` | 監視対象のYouTubeチャンネルID（UC形式） | ✅ | `UCxxxxxxxxxxxxxxxx` |
| `POLL_INTERVAL_MINUTES` | YouTubeポーリング間隔（分、最小5分） | ⭕ | `10` |
| `APP_MODE` | 動作モード | ⭕ | `selfpost` / `autopost` / `dry_run` / `collect` |
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

## 🔧 オプション設定

### 一般設定
- `DEBUG_MODE` (`true`/`false`, デフォルト: `false`) - 詳細ログ表示
- `TIMEZONE` (`Asia/Tokyo` など、デフォルト: `system`) - タイムゾーン
- `BLUESKY_POST_ENABLED` (`True`/`False`) - Bluesky投稿有効化

### 投稿機能
- `PREVENT_DUPLICATE_POSTS` (`true`/`false`, デフォルト: `false`) - 重複投稿防止

### AUTOPOST 設定（`APP_MODE=autopost` 時のみ）
- `AUTOPOST_INTERVAL_MINUTES` (デフォルト: 5) - 投稿間隔
- `AUTOPOST_LOOKBACK_MINUTES` (デフォルト: 30) - 時間窓
- `AUTOPOST_UNPOSTED_THRESHOLD` (デフォルト: 20) - 未投稿閾値
- `AUTOPOST_INCLUDE_NORMAL` - 通常動画を投稿
- `AUTOPOST_INCLUDE_PREMIERE` - プレミア配信を投稿

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

### 画像リサイズ設定
- `IMAGE_RESIZE_TARGET_WIDTH` (デフォルト: 1280) - 横長画像の幅
- `IMAGE_RESIZE_TARGET_HEIGHT` (デフォルト: 800) - 横長画像の高さ
- `IMAGE_OUTPUT_QUALITY_INITIAL` (デフォルト: 90) - JPEG初期品質（1-100）
- `IMAGE_SIZE_THRESHOLD` (デフォルト: 900000バイト) - 品質低下開始閾値

---

## 🔌 プラグイン設定

### YouTubeAPI 連携プラグイン
- `YOUTUBE_API_KEY` - YouTube Data API キー（UC以外の識別子対応・ライブ詳細取得）

### YouTubeLive プラグイン（v3.4.0+）
- `YOUTUBE_LIVE_AUTO_POST_MODE` (`all` / `schedule` / `live` / `archive` / `off`, デフォルト: `off`)
- `YOUTUBE_LIVE_POLL_INTERVAL` (デフォルト: 15分、範囲: 15～60分)

### ニコニコ プラグイン
- `NICONICO_USER_ID` - 監視対象ユーザーID（数値）
- `NICONICO_USER_NAME` - ユーザー名（自動取得失敗時に使用）
- `NICONICO_POLL_INTERVAL` (デフォルト: 10分)

---

## 📊 ログ設定拡張

### グローバル設定
- `LOG_LEVEL_CONSOLE` (デフォルト: INFO) - コンソール出力レベル
- `LOG_LEVEL_FILE` (デフォルト: INFO) - ファイル出力レベル
- `LOG_RETENTION_DAYS` (デフォルト: 14) - ログファイル保持日数

### 個別ロガー設定（オプション）
- `LOG_LEVEL_APP` - アプリ全般
- `LOG_LEVEL_AUDIT` - 監査ログ
- `LOG_LEVEL_POST` - 投稿イベント
- `LOG_LEVEL_GUI` - GUI操作
- `LOG_LEVEL_YOUTUBE` - YouTube監視
- `LOG_LEVEL_NICONICO` - Niconico監視
- その他多数

---

## 🚀 将来実装予定

以下の設定は現在コメントアウト推奨です：

### Twitch プラグイン（v3.x 計画中）
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
