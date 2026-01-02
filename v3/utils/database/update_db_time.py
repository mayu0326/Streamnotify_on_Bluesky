#!/usr/bin/env python
# -*- coding: utf-8 -*-

from database import get_database
from plugins.youtube.youtube_api_plugin import YouTubeAPIPlugin

db = get_database()
api_plugin = YouTubeAPIPlugin()

video_id = "SaKd1RqfM5A"

if api_plugin.is_available():
    print(f"🔄 {video_id} のDB情報を更新中...")

    # YouTube APIから最新情報を取得
    details = api_plugin.fetch_video_detail(video_id)

    if details:
        info = api_plugin._extract_video_info(details)
        new_published_at = info.get('published_at')
        new_live_status = info.get('live_status')

        print(f"新しい情報:")
        print(f"  published_at: {new_published_at}")
        print(f"  live_status: {new_live_status}")

        # DBを更新
        success = db.update_video_status(video_id, "live", new_live_status)

        if success:
            print(f"✅ DB更新成功")

            # 更新後の状態を確認
            videos = db.get_all_videos()
            for v in videos:
                if v['video_id'] == video_id:
                    print(f"✅ 更新後:")
                    print(f"  published_at: {v['published_at']}")
                    print(f"  live_status: {v['live_status']}")
        else:
            print(f"❌ DB更新失敗")
    else:
        print(f"❌ API から情報取得失敗")
else:
    print(f"❌ YouTube API プラグイン利用不可")
