#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3

conn = sqlite3.connect('data/video_list.db')
cursor = conn.cursor()

cursor.execute('SELECT video_id, published_at FROM videos WHERE video_id = ?', ('58S5Pzux9BI',))
result = cursor.fetchone()

print("DB に保存されている値:")
if result:
    print(f"  video_id: {result[0]}")
    print(f"  published_at: {result[1]}")
else:
    print("  該当する動画が見つかりません")

conn.close()
