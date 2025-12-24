#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
修正後のテンプレートレンダリング検証
DB から取得した JST データが正しく表示されるか確認
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import sqlite3
from template_utils import calculate_extended_time_for_event

# DB から修正後のデータを取得
conn = sqlite3.connect('data/video_list.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()
cursor.execute('SELECT * FROM videos WHERE video_id = ?', ('58S5Pzux9BI',))
video_row = cursor.fetchone()
conn.close()

if not video_row:
    print("❌ 動画が見つかりません")
    sys.exit(1)

# 辞書に変換
video = dict(video_row)

print("=" * 80)
print("🔍 修正後のテンプレートレンダリング検証")
print("=" * 80)

print(f"\n🎬 {video['title']}")
print(f"   video_id: {video['video_id']}")
print(f"   published_at (DB): {video['published_at']}")

# 拡張時刻計算
calculate_extended_time_for_event(video)

extended_hour = video.get('extended_hour')
extended_date = video.get('extended_display_date')

print(f"\n✅ 拡張時刻計算結果:")
print(f"   extended_hour: {extended_hour}")
print(f"   extended_display_date: {extended_date}")

if extended_hour and extended_hour >= 24:
    print(f"\n📝 期待される表示:")
    print(f"   開始日時: {extended_date}{extended_hour}時({extended_date} 27時表記)")
    print(f"\n✅ テンプレートで期待される出力:")
    print(f"   2025年12月29日27時(2025年12月30日(火)午前3時)")
else:
    print(f"\n⚠️  通常表記")

print("\n" + "=" * 80)
