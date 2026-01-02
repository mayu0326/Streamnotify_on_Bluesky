#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
from datetime import datetime

DB_PATH = Path(__file__).parent.parent.parent / "data" / "video_list.db"

conn = sqlite3.connect(str(DB_PATH))
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# 最近投稿された live/archive 動画を確認
cursor.execute("""
    SELECT video_id, title, content_type, live_status, posted_to_bluesky, posted_at
    FROM videos
    WHERE content_type IN ('live', 'archive')
    ORDER BY posted_at DESC
    LIMIT 5
""")

rows = cursor.fetchall()

print("📊 最近投稿された YouTube Live/Archive 動画:")
print("=" * 80)

for row in rows:
    r = dict(row)
    video_id = r["video_id"]
    title = r["title"][:40]
    content_type = r["content_type"]
    live_status = r["live_status"]
    posted = "✅ 投稿済み" if r["posted_to_bluesky"] else "❌ 未投稿"
    posted_at = r["posted_at"] if r["posted_at"] else "N/A"

    print(f"{video_id}")
    print(f"  タイトル: {title}")
    print(f"  状態: content_type={content_type}, live_status={live_status}")
    print(f"  投稿状況: {posted}")
    print(f"  投稿日時: {posted_at}")
    print()

conn.close()
