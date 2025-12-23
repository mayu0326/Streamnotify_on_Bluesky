#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
全動画の分類状態を集計
"""

import sys
import os
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).parent.parent / "v3"))

from v3.database import get_database

def analyze_all_videos():
    """全動画の分類状態を集計"""
    print("\n📊 全動画の分類状態を集計中...\n")
    print("=" * 70)

    db = get_database("data/video_list.db")
    all_videos = db.get_all_videos()

    print(f"📈 総動画数: {len(all_videos)}\n")

    # content_type の集計
    content_types = Counter(v.get('content_type', 'unknown') for v in all_videos)
    print("content_type 分布:")
    for ct, count in content_types.most_common():
        print(f"  {ct}: {count} 件")

    # live_status の集計
    live_statuses = Counter(v.get('live_status', 'unknown') for v in all_videos)
    print(f"\nlive_status 分布:")
    for ls, count in live_statuses.most_common():
        print(f"  {ls}: {count} 件")

    # archive の詳細
    archives = [v for v in all_videos if v.get('content_type') == 'archive']
    print(f"\n✅ アーカイブ動画: {len(archives)} 件")
    if archives:
        print("\n最新 5 件のアーカイブ動画:")
        for i, v in enumerate(archives[:5], 1):
            posted_str = "✅投稿済み" if v.get('posted_to_bluesky') else "⏳未投稿"
            print(f"  {i}. [{posted_str}] {v.get('title')[:50]}...")

    # live の詳細
    lives = [v for v in all_videos if v.get('content_type') == 'live']
    print(f"\n🔴 ライブ動画: {len(lives)} 件")
    if lives:
        print("\n最新 5 件のライブ動画:")
        for i, v in enumerate(lives[:5], 1):
            print(f"  {i}. {v.get('title')[:50]}...")

    # video (未分類) の詳細
    videos = [v for v in all_videos if v.get('content_type') == 'video']
    print(f"\n📹 通常動画（未判定）: {len(videos)} 件")
    if videos:
        print("\n最新 5 件の未判定動画:")
        for i, v in enumerate(videos[:5], 1):
            print(f"  {i}. {v.get('title')[:50]}...")

    print("\n" + "=" * 70)

if __name__ == "__main__":
    analyze_all_videos()
