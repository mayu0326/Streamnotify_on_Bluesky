#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
修正検証スクリプト
"""
import sqlite3

db_path = 'data/video_list.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

video_id = '58S5Pzux9BI'

# 修正前の値を確認
cursor.execute('SELECT published_at FROM videos WHERE video_id = ?', (video_id,))
row = cursor.fetchone()

print('=' * 90)
print('✅ 修正検証スクリプト')
print('=' * 90)
print()
print(f'確認対象: {video_id}')
print()
print(f'現在の DB published_at: {row[0] if row else "Not found"}')
print()
print('修正内容:')
print('  ① api_scheduled_start_time を別途保存')
print('  ② 上書きロジックで api_scheduled_start_time を使用（API publishedAt ではなく）')
print('  ③ API scheduledStartTime/actualStartTime を優先して比較')
print()
print('期待値:')
print('  現在:  2025-12-23T19:30:44+00:00 (RSS published_at)')
print('  目標:  2025-12-28T18:00:00Z (API scheduledStartTime)')
print()
print('修正を反映させるには:')
print('  1. youtube_rss.py の save_to_db() を実行')
print('  2. または RSS ポーリング処理を実行')
print()

conn.close()
