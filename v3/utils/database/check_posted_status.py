# -*- coding: utf-8 -*-
"""テスト動画が投稿済みになっているか確認"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from database import get_database

db = get_database()
conn = db._get_connection()
cursor = conn.cursor()

# テスト動画を確認
cursor.execute("""
    SELECT video_id, title, posted_to_bluesky, posted_at
    FROM videos
    WHERE video_id=?
""", ("TEST_LIVE_20251223",))

row = cursor.fetchone()
if row:
    print(f"✅ テスト動画の投稿状態:")
    print(f"   video_id: {row[0]}")
    print(f"   title: {row[1]}")
    print(f"   posted_to_bluesky: {row[2]}")
    print(f"   posted_at: {row[3]}")
else:
    print("❌ テスト動画が見つかりません")

# live/archive で投稿済みの動画数
cursor.execute("""
    SELECT COUNT(*) FROM videos
    WHERE content_type IN ('live', 'archive') AND posted_to_bluesky=1
""")
count = cursor.fetchone()[0]
print(f"\n📊 live/archive で投稿済みの動画数: {count} 件")

conn.close()
