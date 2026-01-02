#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
既存 DB データの classification_type を設定
これにより、bluesky_plugin で youtube_schedule テンプレートが使用される
"""

import sqlite3
from datetime import datetime

DB_PATH = 'data/video_list.db'

def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # classification_type が NULL のデータを取得
    cursor.execute('''
        SELECT id, video_id, title, published_at, classification_type, live_status
        FROM videos
        WHERE classification_type IS NULL
    ''')
    rows = cursor.fetchall()

    print("=" * 80)
    print("🔧 既存 DB の classification_type を設定")
    print("=" * 80)
    print(f"\n対象: {len(rows)} 件\n")

    updated_count = 0
    for row in rows:
        # published_at から時刻を判定
        try:
            pub_time = datetime.fromisoformat(row['published_at'])

            # 早朝 (00:00-12:00) であれば "schedule" と判定（27時表記対象）
            # それ以外は "video" と判定
            if pub_time.hour < 12:
                classification = "schedule"  # 拡張時刻対象
                print(f"✅ {row['title'][:50]}")
                print(f"   {row['published_at']} → classification_type='schedule' (拡張時刻対象)")
            else:
                classification = "video"
                print(f"⚪ {row['title'][:50]}")
                print(f"   {row['published_at']} → classification_type='video' (通常時刻)")

            cursor.execute(
                'UPDATE videos SET classification_type = ? WHERE id = ?',
                (classification, row['id'])
            )
            updated_count += 1

        except Exception as e:
            print(f"❌ {row['title'][:50]}: {e}")

    conn.commit()
    conn.close()

    print("\n" + "=" * 80)
    print(f"✅ 修正完了: {updated_count} 件")
    print("=" * 80)

if __name__ == "__main__":
    main()
