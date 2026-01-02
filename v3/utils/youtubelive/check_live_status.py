#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent / "data" / "video_list.db"

conn = sqlite3.connect(str(DB_PATH))
cursor = conn.cursor()

# live_status の分布を確認
cursor.execute("SELECT live_status, COUNT(*) FROM videos GROUP BY live_status")
rows = cursor.fetchall()

print("📊 live_status の分布:")
print("=" * 60)
for status, count in rows:
    status_name = status if status else "NULL"
    print(f"  {status_name}: {count} 件")

# live_status='live' の動画を確認
cursor.execute("SELECT COUNT(*) FROM videos WHERE live_status='live'")
live_count = cursor.fetchone()[0]
print(f"\n🔄 ライブ中の動画: {live_count} 件")

if live_count > 0:
    cursor.execute("SELECT video_id, title FROM videos WHERE live_status='live' LIMIT 3")
    for video_id, title in cursor.fetchall():
        print(f"  - {video_id}: {title[:40]}")

conn.close()
