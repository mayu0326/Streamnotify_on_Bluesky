# -*- coding: utf-8 -*-
"""DB内のlive_statusが'live'の動画を確認"""

import sqlite3
from pathlib import Path

db_path = Path(__file__).parent / "data" / "video_list.db"

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# live_status='live'の動画を確認
cursor.execute("""
    SELECT video_id, title, content_type, live_status, published_at
    FROM videos
    WHERE live_status = 'live'
    ORDER BY published_at DESC
""")

live_videos = cursor.fetchall()

print(f"🔍 live_status='live'の動画数: {len(live_videos)}")
print()

for video in live_videos:
    print(f"  video_id: {video['video_id']}")
    print(f"  title: {video['title']}")
    print(f"  content_type: {video['content_type']}")
    print(f"  live_status: {video['live_status']}")
    print(f"  published_at: {video['published_at']}")
    print()

conn.close()

# キャッシュも確認
import json
cache_path = Path(__file__).parent / "data" / "youtube_live_cache.json"
if cache_path.exists():
    with open(cache_path, 'r', encoding='utf-8') as f:
        cache = json.load(f)
    print(f"📁 youtube_live_cache.json 内容:")
    print(f"   ファイルサイズ: {cache_path.stat().st_size} bytes")
    print(f"   キャッシュキー数: {len(cache)}")
    if cache:
        for key, value in cache.items():
            print(f"   - {key}: {value}")
    else:
        print(f"   (空)")
