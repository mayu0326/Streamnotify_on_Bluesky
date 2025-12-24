#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""動画追加 DB 保存デバッグスクリプト"""

import sys
sys.path.insert(0, '.')

from database import get_database
from plugin_manager import PluginManager
from config import get_config
from logging_config import setup_logging
import logging

# ロギング初期化
setup_logging()
logger = logging.getLogger("AppLogger")

def debug_insert_video():
    """DB 保存をデバッグ"""

    db = get_database()
    config = get_config("settings.env")

    # YouTube API プラグイン取得
    pm = PluginManager()
    plugins = pm.get_enabled_plugins()

    youtube_api_plugin = None
    for plugin_name, plugin_instance in plugins.items():
        if "youtube_api" in plugin_name.lower():
            youtube_api_plugin = plugin_instance
            break

    if not youtube_api_plugin:
        print("❌ YouTube API プラグインが見つかりません")
        return

    video_id = "MBCuCVqH9u4"

    print(f"🔍 デバッグ開始: {video_id}")
    print("=" * 70)

    # API から動画情報を取得
    print(f"\n1️⃣ YouTube API から動画情報を取得...")
    video_details = youtube_api_plugin.fetch_video_detail(video_id)

    if not video_details:
        print("❌ API から情報取得失敗")
        return

    print(f"✅ API レスポンス取得\n")

    snippet = video_details.get("snippet", {})

    print(f"📝 取得データ:")
    print(f"  • title: {snippet.get('title', 'N/A')[:60]}...")
    print(f"  • channelTitle: {snippet.get('channelTitle', 'N/A')}")
    print(f"  • publishedAt: {snippet.get('publishedAt', 'N/A')}")

    # DB に保存を試みる
    print(f"\n2️⃣ DB に保存を試みます...")

    success = db.insert_video(
        video_id=video_id,
        title=snippet.get("title", "【新着動画】"),
        video_url=f"https://www.youtube.com/watch?v={video_id}",
        published_at=snippet.get("publishedAt", ""),
        channel_name=snippet.get("channelTitle", ""),
        content_type="video",
        source="youtube"
    )

    print(f"✅ insert_video() 戻り値: {success}\n")

    if success:
        print("✅ DB 保存成功！")
    else:
        print("❌ DB 保存失敗")
        print("\n🔍 理由を調査...")

        # DB 内に既に存在するか確認
        all_videos = db.get_all_videos()
        for video in all_videos:
            if video.get("video_id") == video_id:
                print(f"⚠️ 理由: 既に DB に存在しています")
                print(f"  • title: {video.get('title')[:60]}...")
                print(f"  • content_type: {video.get('content_type')}")
                print(f"  • live_status: {video.get('live_status')}")
                break
        else:
            print(f"❓ 理由不明: DB には存在しないのに保存失敗")
            print(f"  → database.py の insert_video() のロジックを確認してください")

if __name__ == '__main__':
    debug_insert_video()
