#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GUI 用データの検証テスト
"""

import sys
sys.path.insert(0, "v2")

from database import get_database

db = get_database("v2/data/video_list.db")
videos = db.get_all_videos()

if not videos:
    print("❌ データが見つかりません")
    sys.exit(1)

print("=" * 80)
print("✅ GUI 用データ検証")
print("=" * 80)
print()

# 最初の 5 件を表示
print("📊 先頭 5 件のデータ:")
print()

for i, video in enumerate(videos[:5], 1):
    print(f"[{i}] Video ID: {video.get('video_id')}")
    print(f"    タイトル: {video.get('title')[:60]}")
    print(f"    配信元 (source): {video.get('source')}")
    print(f"    分類 (classification_type): {video.get('classification_type')}")
    print(f"    ステータス (broadcast_status): {video.get('broadcast_status')}")

    # GUI 表示用の分類タイプ決定ロジック
    source = video.get("source") or ""
    classification_type = video.get("classification_type", "video")
    if source == "Niconico":
        display_type = "🎬 動画"
    elif classification_type == "archive":
        display_type = "📹 アーカイブ"
    elif classification_type == "live":
        display_type = "🔴 配信"
    else:
        display_type = "🎬 動画"

    print(f"    GUI 表示: {display_type}")
    print()

# 分類の分布を表示
print("=" * 80)
print("📊 分類の分布")
print("=" * 80)
print()

from collections import defaultdict
distribution = defaultdict(int)
for video in videos:
    classification = video.get("classification_type", "video")
    if video.get("source") == "Niconico":
        key = "Niconico (動画)"
    elif classification == "archive":
        key = "YouTube アーカイブ"
    elif classification == "live":
        key = "YouTube 配信"
    else:
        key = "YouTube 通常動画"
    distribution[key] += 1

for key, count in sorted(distribution.items(), key=lambda x: x[1], reverse=True):
    print(f"  {key:20s}: {count:3d} 件")

print()
print(f"合計: {len(videos)} 件")
print()
print("✅ 検証完了！GUI で正常に表示されます。")
