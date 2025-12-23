#!/usr/bin/env python
# -*- coding: utf-8 -*-

from v3.plugins.youtube_api_plugin import YouTubeAPIPlugin

api_plugin = YouTubeAPIPlugin()

if api_plugin.is_available():
    print("🔍 YouTube API プラグインから動画詳細を取得中...")
    details = api_plugin.fetch_video_detail("SaKd1RqfM5A")

    if details:
        print("✅ 詳細情報を取得しました:")
        print(f"  published_at: {details.get('snippet', {}).get('publishedAt')}")
        print(f"  liveStreamingDetails: {details.get('liveStreamingDetails', {})}")

        # _extract_video_info で抽出
        info = api_plugin._extract_video_info(details)
        print(f"\n抽出結果:")
        print(f"  published_at: {info.get('published_at')}")
        print(f"  live_status: {info.get('live_status')}")
    else:
        print("❌ 詳細情報が取得できません")
else:
    print("❌ YouTube API プラグインが利用不可")
