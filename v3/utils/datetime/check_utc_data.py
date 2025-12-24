#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3

conn = sqlite3.connect('data/video_list.db')
cursor = conn.cursor()

# Z で終わっているデータを検索
cursor.execute("SELECT COUNT(*) FROM videos WHERE published_at LIKE '%Z'")
count = cursor.fetchone()[0]

print(f'Z で終わる published_at: {count} 件')

if count > 0:
    cursor.execute("SELECT video_id, published_at FROM videos WHERE published_at LIKE '%Z' LIMIT 5")
    rows = cursor.fetchall()
    for row in rows:
        print(f'  {row[0]}: {row[1]}')

conn.close()
