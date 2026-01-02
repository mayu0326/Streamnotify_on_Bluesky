# -*- coding: utf-8 -*-
"""実際のアーカイブ動画を live_status='live' に変更"""

import sqlite3
from pathlib import Path

db_path = Path(__file__).parent / "data" / "video_list.db"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# まず、テスト用の偽動画IDを削除
cursor.execute("DELETE FROM videos WHERE video_id = ?", ("TEST_LIVE_ONGOING_20251223",))
print(f"✅ テスト用動画を削除しました")

# -Vnx9CUowOI を確認
cursor.execute("""
    SELECT video_id, title, content_type, live_status
    FROM videos
    WHERE video_id = ?
""", ("-Vnx9CUowOI",))

row = cursor.fetchone()
if row:
    print(f"📺 現在の状態: {row[2]}/{row[3]}")

    # live_status を 'live' に更新
    cursor.execute("""
        UPDATE videos
        SET live_status = 'live'
        WHERE video_id = ?
    """, ("-Vnx9CUowOI",))

    print(f"✅ -Vnx9CUowOI を live_status='live' に更新しました")
else:
    print(f"❌ 動画が見つかりません")

conn.commit()
conn.close()

# 確認
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

cursor.execute("""
    SELECT video_id, title, content_type, live_status
    FROM videos
    WHERE live_status = 'live'
""")

live_videos = cursor.fetchall()
print(f"\n🔍 現在のlive_status='live'の動画:")
for v in live_videos:
    print(f"  - {v['video_id']}: {v['content_type']}/{v['live_status']} ({v['title']})")

conn.close()
