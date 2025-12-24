#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3

conn = sqlite3.connect('data/video_list.db')
cursor = conn.cursor()

cursor.execute('SELECT video_id, title, published_at, classification_type, live_status FROM videos WHERE video_id = ?', ('58S5Pzux9BI',))
row = cursor.fetchone()

if row:
    print('動画ID:', row[0])
    print('タイトル:', row[1])
    print('published_at:', row[2])
    print('classification_type:', row[3])
    print('live_status:', row[4])
else:
    print('見つかりません')

conn.close()
