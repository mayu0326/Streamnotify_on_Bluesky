#!/usr/bin/env python
# -*- coding: utf-8 -*-

from plugins.youtube.youtube_api_plugin import YouTubeAPIPlugin

api_plugin = YouTubeAPIPlugin()

print("🗑️ YouTube API キャッシュをクリア中...")
api_plugin.clear_video_detail_cache()
print("✅ キャッシュをクリアしました")
