#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sqlite3

# DB 接続
conn = sqlite3.connect("data/video_list.db")
cursor = conn.cursor()

# テスト動画を live 状態で挿入（既存データに干渉しないよう新規ID）
test_video_id = "TEST_LIVE_20251223"

cursor.execute("""
    INSERT INTO videos (
        video_id, title, video_url, published_at, channel_name,
        content_type, live_status, posted_to_bluesky, source
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
""", (
    test_video_id,
    "テスト用 YouTube Live スケジュール枠",
    f"https://www.youtube.com/watch?v={test_video_id}",
    "2025-12-23T05:25:00",
    "テストチャンネル",
    "live",
    "upcoming",
    0,  # 未投稿
    "youtube"
))

conn.commit()
print(f"✅ テスト動画を DB に挿入しました: {test_video_id}")

# 確認
cursor.execute("SELECT video_id, title, content_type, live_status, posted_to_bluesky FROM videos WHERE video_id = ?", (test_video_id,))
row = cursor.fetchone()
if row:
    print(f"   確認: video_id={row[0]}, title={row[1]}, content_type={row[2]}, live_status={row[3]}, posted={row[4]}")
else:
    print("   ❌ 挿入に失敗しました")

conn.close()
