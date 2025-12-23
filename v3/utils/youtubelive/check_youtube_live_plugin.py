#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
YouTube Live プラグイン機能確認スクリプト

目的: YouTube Live プラグインがライブ配信を検出できるかを確認
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "v3"))

from v3.config import get_config

print("=" * 70)
print("📺 YouTube Live プラグイン機能確認")
print("=" * 70)

try:
    config = get_config("v3/settings.env")

    print("\n📋 [YouTube Live プラグイン設定]")
    print("-" * 70)

    # 設定を確認
    print(f"✅ YouTube チャンネルID: {config.youtube_channel_id}")
    print(f"✅ YouTube API キー: {'設定あり' if config.youtube_api_key else '⚠️ 未設定'}")

    if hasattr(config, 'youtube_live_auto_post_mode'):
        print(f"✅ YouTube Live 自動投稿モード: {config.youtube_live_auto_post_mode}")
    else:
        print(f"⚠️ youtube_live_auto_post_mode: 未設定（デフォルト: off）")

    if hasattr(config, 'youtube_live_poll_interval'):
        print(f"✅ YouTube Live ポーリング間隔: {config.youtube_live_poll_interval} 分")
    else:
        print(f"⚠️ youtube_live_poll_interval: 未設定（デフォルト: 15 分）")

    # YouTube API キーが設定されているかチェック
    print("\n📡 [YouTube API キー確認]")
    print("-" * 70)

    if not config.youtube_api_key:
        print("""
❌ YouTube API キーが設定されていません。

新しいライブ配信をリアルタイムで検出するには、YouTube Data API v3 キーが必須です。

📌 設定方法：
1. Google Cloud Console (https://console.cloud.google.com) にアクセス
2. YouTube Data API v3 を有効化
3. API キーを作成
4. settings.env に以下を追加：
   YOUTUBE_API_KEY=あなたのAPIキー
5. アプリケーションを再起動

⏱️ 一度設定すれば、YouTube Live プラグインが自動的にライブ配信を検出します。
""")
    else:
        print(f"✅ YouTube API キーが設定されています")
        print("""
✨ YouTube Live プラグインが有効になります！
- 新しいライブ配信をリアルタイムで検出
- 配信開始・終了を自動ポスト（設定で有効化可能）
- YouTube Live ポーリングが動作開始
""")

    print("\n📝 [推奨設定]")
    print("-" * 70)
    print("""
settings.env で以下を設定することをお勧めします：

# YouTube Live 自動投稿モード（配信開始・終了時に自動ポスト）
YOUTUBE_LIVE_AUTO_POST_MODE=all

# YouTube Live ポーリング間隔（最短15分、推奨30分）
YOUTUBE_LIVE_POLL_INTERVAL=15
""")

except Exception as e:
    print(f"❌ エラー: {e}")

print("\n" + "=" * 70)
