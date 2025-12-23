#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
テスト用：ライブ中の動画を DB に追加
キャッシュ機構のテストをするために必要
"""

import sqlite3
from datetime import datetime

DB_PATH = "data/video_list.db"

TEST_VIDEO = {
    "video_id": "TEST_LIVE_ONGOING_20251223",
    "title": "【テスト】現在ライブ中の配信",
    "video_url": "https://www.youtube.com/watch?v=TEST_LIVE_ONGOING_20251223",
    "published_at": datetime.now().isoformat(),
    "channel_name": "テストチャンネル",
    "content_type": "live",
    "live_status": "live",  # ← ライブ中
    "source": "youtube"
}

try:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR REPLACE INTO videos (
            video_id, title, video_url, published_at, channel_name,
            content_type, live_status, source
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        TEST_VIDEO["video_id"],
        TEST_VIDEO["title"],
        TEST_VIDEO["video_url"],
        TEST_VIDEO["published_at"],
        TEST_VIDEO["channel_name"],
        TEST_VIDEO["content_type"],
        TEST_VIDEO["live_status"],
        TEST_VIDEO["source"]
    ))

    conn.commit()
    conn.close()

    print(f"✅ ライブ中のテスト動画を挿入しました:")
    print(f"   video_id: {TEST_VIDEO['video_id']}")
    print(f"   title: {TEST_VIDEO['title']}")
    print(f"   content_type: {TEST_VIDEO['content_type']}")
    print(f"   live_status: {TEST_VIDEO['live_status']}")
    print()
    print(f"📝 次のステップ:")
    print(f"   1. アプリケーションを起動")
    print(f"   2. YouTubeLive プラグインの poll_live_status() が実行")
    print(f"   3. data/youtube_live_cache.json が作成される")

except Exception as e:
    print(f"❌ エラー: {e}")
