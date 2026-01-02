#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sqlite3
from plugins.youtube.youtube_api_plugin import YouTubeAPIPlugin

db_path = "data/video_list.db"
video_id = "SaKd1RqfM5A"

api_plugin = YouTubeAPIPlugin()

if api_plugin.is_available():
    print(f"🔄 {video_id} のDB情報を更新中...")

    # YouTube APIから最新情報を取得
    details = api_plugin.fetch_video_detail(video_id)

    if details:
        info = api_plugin._extract_video_info(details)
        new_published_at = info.get('published_at')

        print(f"新しい published_at: {new_published_at}")

        # DBを直接更新
        conn = sqlite3.connect(db_path, timeout=10)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE videos
            SET published_at = ?
            WHERE video_id = ?
        """, (new_published_at, video_id))

        conn.commit()

        # 更新後の状態を確認
        cursor.execute("SELECT published_at FROM videos WHERE video_id = ?", (video_id,))
        result = cursor.fetchone()
        conn.close()

        if result:
            print(f"✅ DB更新成功: {result[0]}")
        else:
            print(f"❌ 更新後の確認に失敗")
    else:
        print(f"❌ API から情報取得失敗")
else:
    print(f"❌ YouTube API プラグイン利用不可")
