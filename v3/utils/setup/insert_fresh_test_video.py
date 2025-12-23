#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
新しいテスト用 YouTube Live 動画を DB に挿入
"""

import sqlite3
from datetime import datetime, timedelta

DB_PATH = "data/video_list.db"

# テスト用の新しい動画情報
TEST_VIDEO = {
    "video_id": "TEST_LIVE_NEW_20251223",  # 新しいテスト ID
    "title": "【テスト配信】YouTube Live 自動投稿テスト",
    "video_url": "https://www.youtube.com/watch?v=TEST_LIVE_NEW_20251223",
    "published_at": (datetime.now() - timedelta(minutes=5)).isoformat(),  # 5分前
    "channel_name": "テストチャンネル",
    "thumbnail_url": None,
    "content_type": None,  # ← 未判定
    "live_status": None,   # ← 未判定
    "source": "youtube"
}

try:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO videos (
            video_id, title, video_url, published_at, channel_name,
            thumbnail_url, content_type, live_status, source
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        TEST_VIDEO["video_id"],
        TEST_VIDEO["title"],
        TEST_VIDEO["video_url"],
        TEST_VIDEO["published_at"],
        TEST_VIDEO["channel_name"],
        TEST_VIDEO["thumbnail_url"],
        TEST_VIDEO["content_type"],
        TEST_VIDEO["live_status"],
        TEST_VIDEO["source"]
    ))

    conn.commit()
    conn.close()

    print(f"✅ テスト動画を挿入しました:")
    print(f"   video_id: {TEST_VIDEO['video_id']}")
    print(f"   title: {TEST_VIDEO['title']}")
    print(f"   content_type: {TEST_VIDEO['content_type']} (未判定)")
    print(f"   live_status: {TEST_VIDEO['live_status']} (未判定)")
    print(f"\n📝 次のステップ:")
    print(f"   1. アプリケーションを起動して on_enable() を実行")
    print(f"   2. YouTube Live プラグインが動画を自動判定")
    print(f"   3. 新規判定があれば自動投稿処理が実行される")

except sqlite3.IntegrityError:
    print(f"❌ テスト動画は既に存在します: {TEST_VIDEO['video_id']}")
except Exception as e:
    print(f"❌ エラー: {e}")
