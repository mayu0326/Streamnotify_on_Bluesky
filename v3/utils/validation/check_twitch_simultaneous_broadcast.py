#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
「Twitch同時配信」動画で liveStreamingDetails を持つものを確認
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from database import get_database
from plugins.youtube.youtube_api_plugin import YouTubeAPIPlugin

def check_twitch_simultaneous_broadcast():
    """「Twitch同時配信」と書かれている動画を確認"""
    print("\n🔍 「Twitch同時配信」と書かれている動画を確認中...\n")
    print("=" * 80)

    db = get_database("data/video_list.db")
    api_plugin = YouTubeAPIPlugin()

    all_videos = db.get_all_videos()

    # 「Twitch同時配信」を含む動画を抽出
    twitch_simultaneous = [
        v for v in all_videos
        if "Twitch同時配信" in v.get("title", "")
    ]

    print(f"📊 「Twitch同時配信」を含む動画: {len(twitch_simultaneous)} 件\n")

    has_live_streaming = 0
    no_live_streaming = 0

    for video in twitch_simultaneous[:30]:  # 最初の 30 件を確認
        video_id = video.get("video_id")
        title = video.get("title")
        content_type = video.get("content_type")
        live_status = video.get("live_status")

        # キャッシュから詳細情報を取得
        details = api_plugin._get_cached_video_detail(video_id)

        if details:
            has_live = bool(details.get('liveStreamingDetails'))
            if has_live:
                has_live_streaming += 1
                live_details = details.get('liveStreamingDetails', {})
                print(f"✅ [{content_type}/{live_status}] {video_id}")
                print(f"   タイトル: {title[:60]}")
                print(f"   liveStreamingDetails: 存在")
                print(f"     - actualStartTime: {live_details.get('actualStartTime')}")
                print(f"     - actualEndTime: {live_details.get('actualEndTime')}")
                print()
            else:
                no_live_streaming += 1
                print(f"❌ [{content_type}/{live_status}] {video_id}")
                print(f"   タイトル: {title[:60]}")
                print(f"   liveStreamingDetails: なし")
                print()
        else:
            print(f"⚠️ [{content_type}/{live_status}] {video_id}")
            print(f"   タイトル: {title[:60]}")
            print(f"   キャッシュなし")
            print()

    print("=" * 80)
    print(f"📊 liveStreamingDetails 統計:")
    print(f"  あり: {has_live_streaming} 件 ✅")
    print(f"  なし: {no_live_streaming} 件 ⚠️")
    print("\n💡 「Twitch同時配信」動画で liveStreamingDetails があれば、")
    print("   YouTube Live ロジックで正しく分類されるはずです。")

if __name__ == "__main__":
    check_twitch_simultaneous_broadcast()
