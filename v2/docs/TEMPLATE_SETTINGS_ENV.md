# =============================
# Bluesky 機能拡張プラグインの設定（v2.1.0+）
# =============================

# テンプレート機能対応：各プラットフォーム・イベントごとにテンプレートファイルパスを指定
# 未指定時は自動的にデフォルトパス（templates/{service}/{event}_template.txt）を使用

# --------
# YouTube テンプレート
# --------

# 新着動画投稿用テンプレート（v2.1.0 実装済み）
# 用途: RSS 取得による新着動画通知投稿
TEMPLATE_YOUTUBE_NEW_VIDEO_PATH=templates/youtube/yt_new_video_template.txt

# YouTube Live 配信開始通知用テンプレート（v2.x 将来実装予定）
# 用途: YouTubeAPI プラグイン連携時の配信開始通知投稿
# TEMPLATE_YOUTUBE_ONLINE_PATH=templates/youtube/yt_online_template.txt

# YouTube Live 配信終了通知用テンプレート（v2.x 将来実装予定）
# 用途: YouTubeAPI プラグイン連携時の配信終了通知投稿
# TEMPLATE_YOUTUBE_OFFLINE_PATH=templates/youtube/yt_offline_template.txt

# --------
# ニコニコ テンプレート
# --------

# 新着動画投稿用テンプレート（v2.1.0 実装済み）
# 用途: RSS 取得によるニコニコ新着動画通知投稿
TEMPLATE_NICO_NEW_VIDEO_PATH=templates/niconico/nico_new_video_template.txt


# --------
# Twitch テンプレート（v3+ 将来実装予定）
# --------

# Twitch 配信開始通知用テンプレート（v3+ 将来実装予定）
# 用途: Twitch プラグイン連携時の配信開始通知投稿
# TEMPLATE_TWITCH_ONLINE_PATH=templates/twitch/twitch_online_template.txt

# Twitch 配信終了通知用テンプレート（v3+ 将来実装予定）
# 用途: Twitch プラグイン連携時の配信終了通知投稿
# TEMPLATE_TWITCH_OFFLINE_PATH=templates/twitch/twitch_offline_template.txt

# Twitch Raid 通知用テンプレート（v3+ 将来実装予定）
# 用途: Raid イベント発生時の通知投稿
# TEMPLATE_TWITCH_RAID_PATH=templates/twitch/twitch_raid_template.txt

# =============================
# Bluesky 投稿時の共通設定
# =============================

# Bluesky 投稿時に使用するデフォルト画像ファイルのパス
# 用途: 画像未設定時、または画像ダウンロード失敗時の代替画像
# BLUESKY_IMAGE_PATH=images/default/noimage.png

# =============================
# 画像自動リサイズ機能の設定（v2.1.0）
# =============================

# 横長画像のターゲット幅（ピクセル、デフォルト: 1280）
# 横長画像（幅/高さ >= 1.3）を 3:2 にリサイズする際のターゲット幅
IMAGE_RESIZE_TARGET_WIDTH=1280

# 横長画像のターゲット高さ（ピクセル、デフォルト: 800）
# 横長画像を 3:2 にリサイズする際のターゲット高さ
IMAGE_RESIZE_TARGET_HEIGHT=800

# JPEG 初期出力品質（1-100、デフォルト: 90）
# リサイズ後の JPEG 圧縮品質。値が低いほどファイルサイズが小さくなります
IMAGE_OUTPUT_QUALITY_INITIAL=90

# ファイルサイズ目標値（バイト、デフォルト: 800000）
# 理想的なファイルサイズ（800KB）。ログで参考値として表示されます
IMAGE_SIZE_TARGET=800000

# ファイルサイズ品質低下開始閾値（バイト、デフォルト: 900000）
# この値（900KB）を超えた場合、JPEG 品質を段階的に低下させて再圧縮します
IMAGE_SIZE_THRESHOLD=900000

# ファイルサイズ最終上限（バイト、デフォルト: 1000000）
# Bluesky API の上限（1MB）。超過時は画像添付をスキップします
IMAGE_SIZE_LIMIT=1000000

# =============================
# ログ設定拡張プラグインの設定
# =============================

# グローバルログレベル設定
# コンソール出力するログレベル (DEBUG, INFO, WARNING, ERROR, CRITICAL)
# LOG_LEVEL_CONSOLE=INFO

# =============================
# レガシー設定（v2.0.x の互換性のため、以下は非推奨です）
# =============================

# 以下の環境変数はレガシー形式です。
# 新しいコードは TEMPLATE_{service}_{event}_PATH 形式を使用してください。

# BLUESKY_YT_NEW_VIDEO_TEMPLATE_PATH は非推奨
# → TEMPLATE_YOUTUBE_NEW_VIDEO_PATH を使用してください

# BLUESKY_NICO_NEW_VIDEO_TEMPLATE_PATH は非推奨
# → TEMPLATE_NICO_NEW_VIDEO_PATH を使用してください
