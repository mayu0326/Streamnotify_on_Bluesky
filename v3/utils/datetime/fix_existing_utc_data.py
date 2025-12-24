#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
既存 DB のすべての UTC データを JST に変換
（RSS/API から UTC が保存されているすべてのエントリを修正）
"""

import sqlite3
from datetime import datetime, timedelta, timezone

DB_PATH = 'data/video_list.db'

def convert_utc_to_jst(utc_str):
    """UTC 文字列を JST に変換"""
    try:
        # UTC を解析
        utc_time = datetime.fromisoformat(utc_str.replace('Z', '+00:00'))
        # JST に変換
        jst_time = utc_time.astimezone(timezone(timedelta(hours=9))).replace(tzinfo=None)
        return jst_time.isoformat()
    except:
        return utc_str  # 変換失敗時はそのまま

def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # UTC データを検出（Z が含まれている）
    cursor.execute('SELECT id, video_id, title, published_at FROM videos WHERE published_at LIKE "%Z"')
    rows = cursor.fetchall()

    print("=" * 80)
    print("🔧 既存 DB の UTC → JST 変換")
    print("=" * 80)
    print(f"\n修正対象: {len(rows)} 件\n")

    converted_count = 0
    for row in rows:
        old_value = row['published_at']
        new_value = convert_utc_to_jst(old_value)

        if old_value != new_value:
            cursor.execute('UPDATE videos SET published_at = ? WHERE id = ?', (new_value, row['id']))
            converted_count += 1
            print(f"✅ {row['title']}")
            print(f"   旧: {old_value}")
            print(f"   新: {new_value}\n")

    conn.commit()
    conn.close()

    print("=" * 80)
    print(f"✅ 修正完了: {converted_count} 件")
    print("=" * 80)

if __name__ == "__main__":
    main()
