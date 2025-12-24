#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
対象動画の classification_type を schedule に修正
"""

import sqlite3
from datetime import datetime

conn = sqlite3.connect('data/video_list.db')
cursor = conn.cursor()

# 対象動画の情報を確認
cursor.execute('SELECT id, video_id, title, published_at, live_status, classification_type FROM videos WHERE video_id = ?', ('58S5Pzux9BI',))
row = cursor.fetchone()

if row:
    video_id, title, pub_at, live_status, classification_type = row[1], row[2], row[3], row[4], row[5]

    print("=" * 80)
    print("🔧 対象動画の classification_type を修正")
    print("=" * 80)
    print(f"\n動画ID: {video_id}")
    print(f"タイトル: {title}")
    print(f"published_at: {pub_at}")
    print(f"live_status: {live_status}")
    print(f"修正前 classification_type: {classification_type}")

    # live_status が "upcoming" なので "schedule" に設定
    cursor.execute('UPDATE videos SET classification_type = ? WHERE video_id = ?', ('schedule', '58S5Pzux9BI'))
    conn.commit()

    print(f"修正後 classification_type: schedule")
    print("\n✅ 修正完了")
    print("=" * 80)
else:
    print("❌ 動画が見つかりません")

conn.close()
