# Streamnotify v2 設定項目一覧（概要）

このドキュメントは `settings.env.example` のセクション順に、主要な設定項目の目的と利用条件を簡潔にまとめたものです。詳細なサンプル値やコメントは `settings.env.example` を参照してください。

## 基本設定
- `YOUTUBE_CHANNEL_ID`: 監視対象のYouTubeチャンネルID（UC形式推奨）。
- `POLL_INTERVAL_MINUTES`: RSSポーリング間隔（分）。
- `APP_MODE`: 動作モード `normal|auto_post|dry_run|collect`。
- `DEBUG_MODE`: 詳細ログの有効化。**v2.1.0:** `true` で詳細な DEBUG ログを表示、`false` で INFO ログのみ。
- `TIMEZONE`: タイムゾーン。`system` でOS設定に追従。
- `BLUESKY_USERNAME` / `BLUESKY_PASSWORD`: Bluesky認証情報。
- `BLUESKY_POST_ENABLED`: Blueskyへの投稿有効可否。

## Bluesky 機能拡張（準備中）
- `BLUESKY_*_TEMPLATE_PATH` 系: 投稿テンプレートファイルのパス。
- `BLUESKY_IMAGE_PATH`: 画像未設定時の共通画像パス。
- 現時点では「準備中」のため、`settings.env` ではコメントアウト推奨。

## ログ設定拡張
- `LOG_LEVEL_CONSOLE` / `LOG_LEVEL_FILE`: ログレベル。
- `LOG_RETENTION_DAYS`: ローテーション保持日数。
- 個別ロガー上書き: `LOG_LEVEL_APP` / `LOG_LEVEL_AUDIT` / `LOG_LEVEL_THUMBNAILS` など。

## ニコニコ動画プラグイン
- `NICONICO_USER_ID`: 監視対象のユーザーID（数値）。
- `NICONICO_LIVE_POLL_INTERVAL`: ポーリング間隔（分）。

## YouTubeAPI 連携プラグイン
- `YOUTUBE_API_KEY`: UC以外の識別子対応・ライブ詳細取得で使用。未導入時は不要。

## YouTubeLive 検出プラグイン
- 追加設定が必要になった場合に拡張予定（現状設定なし）。

## 動画投稿通知拡張（未実装）
- `NOTIFY_ON_*`: Twitch/YouTube/Niconicoの各通知の有効可否。
- `DISCORD_NOTIFY_ENABLED`: Discord通知の有効化。

## TwitchAPI 連携（未実装）
- `TWITCH_CLIENT_ID` / `TWITCH_CLIENT_SECRET`: アプリ認証情報。
- `TWITCH_BROADCASTER_ID` / `TWITCH_BROADCASTER_ID_CONVERTED`: 対象配信者設定。
- Webhook系: `WEBHOOK_CALLBACK_URL` ほか、`WEBHOOK_SECRET`、`SECRET_LAST_ROTATED`。
- リトライ系: `RETRY_MAX` / `RETRY_WAIT`。

## トンネル通信（未実装）
- `TUNNEL_SERVICE`, `TUNNEL_CMD`, `CLOUDFLARE_TEMP_*`, `NGROK_*`, `LOCALTUNNEL_*`, `CUSTOM_TUNNEL_CMD`。
- 未設定の場合はトンネルを起動しません。

---
補足:
- 実運用では `settings.env.example` を最新基準として参照し、`settings.env` は必要項目のみ有効化してください。
- **v2.1.0 での更新 (2025-12-17 実装済み):**
  - ✅ DEBUG_MODE: `true`/`false` で DEBUG ログを完全制御
  - ✅ Bluesky画像投稿: 自動リサイズ、AspectRatio設定で レターボックス解消
  - ✅ ドライラン機能: `APP_MODE=dry_run` または GUI の「🧪 投稿テスト」で投稿をシミュレート
  - ✅ アセット管理: テンプレート・画像は初回のみ配置、以降は追加のみ
