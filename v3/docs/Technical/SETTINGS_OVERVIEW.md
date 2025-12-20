# Streamnotify v3 設定項目一覧（概要）

このドキュメントは `settings.env.example` のセクション順に、主要な設定項目の目的と利用条件を簡潔にまとめたものです。詳細なサンプル値やコメントは `settings.env.example` を参照してください。

## 基本設定
- `YOUTUBE_CHANNEL_ID`: 監視対象のYouTubeチャンネルID（UC形式推奨）。
- `POLL_INTERVAL_MINUTES`: RSSポーリング間隔（分）。
- `APP_MODE`: 動作モード。仕様v1.0準拠:
  - `selfpost`: 完全手動投稿モード（GUI操作で投稿対象を選択）
  - `autopost`: 完全自動投稿モード（環境変数とロジックのみで制御）
  - `dry_run`: テストモード（投稿実行なし）
  - `collect`: 収集モード（投稿機能オフ）
- `DEBUG_MODE`: 詳細ログの有効化。**v3.1.0:** `true` で詳細な DEBUG ログを表示、`false` で INFO ログのみ。
- `TIMEZONE`: タイムゾーン。`system` でOS設定に追従。
- `BLUESKY_USERNAME` / `BLUESKY_PASSWORD`: Bluesky認証情報。
- `BLUESKY_POST_ENABLED`: Blueskyへの投稿有効可否。

## Bluesky 機能拡張
- `BLUESKY_*_TEMPLATE_PATH` 系: 投稿テンプレートファイルのパス。
- `BLUESKY_IMAGE_PATH`: 画像未設定時の共通画像パス。
- Twitch系は「準備中」のため、`settings.env` ではコメントアウト推奨。

## ロググ設定拡張プラグイン
- `LOG_LEVEL_CONSOLE` / `LOG_LEVEL_FILE`: グローバルログレベル（デフォルト: INFO）。
- `LOG_RETENTION_DAYS`: ローテーション保持日数（デフォルト: 14）。
- 個別ロガー上書き（オプション）: `LOG_LEVEL_APP` / `LOG_LEVEL_AUDIT` / `LOG_LEVEL_THUMBNAILS` / `LOG_LEVEL_TUNNEL` / `LOG_LEVEL_YOUTUBE` / `LOG_LEVEL_NICONICO` / `LOG_LEVEL_GUI` / `LOG_LEVEL_POST_ERROR` / `LOG_LEVEL_POST`。
  - 各値を指定すると `LOG_LEVEL_FILE` をオーバーライドします。未指定時は `LOG_LEVEL_FILE` の値を使用。

## ニコニコ動画　連携プラグイン
- `NICONICO_USER_ID`: 監視対象のユーザーID（数値）。
- `NICONICO_USER_NAME`: ニコニコユーザー名（テンプレートで投稿者として表示、省略可）。未設定時は自動取得を試みます（優先順位: RSS > 静画API > ユーザーページ > ユーザーID）。
- `NICONICO_LIVE_POLL_INTERVAL`: RSS ポーリング間隔（分、デフォルト: 10）。**注記**: RSS は録画済み動画のみ対応。生放送は非対応。
- `TEMPLATE_NICO_NEW_VIDEO_PATH`: ニコニコ新着動画投稿用テンプレート。

## 画像自動リサイズ機能（v3.1.0+）
画像の自動リサイズ・最適化に関する設定。詳細は [IMAGE_RESIZE_GUIDE.md](../Guides/IMAGE_RESIZE_GUIDE.md) を参照。
- `IMAGE_RESIZE_TARGET_WIDTH` / `IMAGE_RESIZE_TARGET_HEIGHT`: リサイズターゲットサイズ（ピクセル）。
- `IMAGE_OUTPUT_QUALITY_INITIAL`: JPEG初期出力品質（1-100、デフォルト: 90）。
- `IMAGE_SIZE_TARGET`: ファイルサイズ目標値（バイト、デフォルト: 800,000）。
- `IMAGE_SIZE_THRESHOLD`: ファイルサイズ品質低下開始閾値（バイト、デフォルト: 900,000）。
- `IMAGE_SIZE_LIMIT`: ファイルサイズ最終上限（バイト、デフォルト: 1,000,000）。

## YouTubeAPI 連携プラグイン
- `YOUTUBE_API_KEY`: UC以外の識別子対応・ライブ詳細取得で使用。未導入時は不要。

## YouTubeLive プラグイン
YouTube Live 自動投稿モード（all / schedule / live / archive / off、デフォルト: off）
- 動作モード:`YOUTUBE_LIVE_AUTO_POST_MODE`:
- `all`: 予約枠・配信・アーカイブすべてを投稿
- `schedule`: 予約枠と配信開始のみ投稿
- `live`: 配信開始・配信終了のみ投稿
- `archive`: アーカイブ公開のみ投稿
- `off`: YouTube Live 自動投稿を行わない

### YouTube Live ポーリング間隔（分単位、デフォルト: 15）
ライブ中の動画をこの間隔でチェックし、終了を検知します
- `YOUTUBE_LIVE_POLL_INTERVAL`=
- ⚠️ 有効範囲: 最短15分～最長60分（範囲外の値は自動調整されます）
- 推奨値: 15分（最短）～30分（標準）～60分（最長）
- 注意: `YOUTUBE_LIVE_AUTOPOST_MODE` が `all` または `live` の場合のみ有効

# ライブ開始時の自動投稿を有効にするか（true/false、デフォルト: true）
# ⚠️ 廃止予定: YOUTUBE_LIVE_AUTO_POST_MODE を使用してください
# YouTube RSS または API でライブ開始を検知した時に、自動的に Bluesky へ投稿します
YOUTUBE_LIVE_AUTO_POST_START=true

# ライブ終了時の自動投稿を有効にするか（true/false、デフォルト: true）
# ⚠️ 廃止予定: YOUTUBE_LIVE_AUTOPOST_MODE を使用してください
# API ポーリングでライブ終了を検知した時に、自動的に Bluesky へ投稿します
YOUTUBE_LIVE_AUTO_POST_END=true

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
- **v3.3.0 での更新 (2025-12-20 実装済み):**
  - ✅ AUTOPOST 機能仕様v1.0: SELFPOST/AUTOPOST 統合設定、安全弁（閾値・間隔）機能
  - ✅ YouTube Live 統合MODE: 5段階制御で YOUTUBE_LIVE_AUTO_POST_START/END フラグを統一
  - ✅ AUTOPOST フィルタ: 4種類の動画種別（Normal/Shorts/Member/Premiere）を個別制御
  - ✅ セーフモード起動: 投稿マークリセット検知で AUTOPOST を自動抑止
- **v3.1.0 での更新 (2025-12-17 実装済み):**
  - ✅ DEBUG_MODE: `true`/`false` で DEBUG ログを完全制御
  - ✅ Bluesky画像投稿: 自動リサイズ、AspectRatio設定で レターボックス解消
  - ✅ ドライラン機能: `APP_MODE=dry_run` または GUI の「🧪 投稿テスト」で投稿をシミュレート
  - ✅ アセット管理: テンプレート・画像は初回のみ配置、以降は追加のみ
