#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
3つの動画が DB に何として登録されているか確認
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from database import get_database

VIDEO_IDS = [
    "q-qavmJ5FjM",
    "p4AJDhen434",
    "_uY5dZ4xSvw"
]

def check_videos_in_db():
    """DB に登録されている動画の分類を確認"""
    print("\n🔍 DB に登録されている分類を確認中...\n")
    print("=" * 80)

    db = get_database("data/video_list.db")
    all_videos = db.get_all_videos()

    for video_id in VIDEO_IDS:
        video = None
        for v in all_videos:
            if v.get("video_id") == video_id:
                video = v
                break

        if video:
            print(f"🔹 {video_id}")
            print(f"   title: {video.get('title')[:60]}")
            print(f"   content_type: {video.get('content_type')}")
            print(f"   live_status: {video.get('live_status')}")
            print(f"   posted_to_bluesky: {video.get('posted_to_bluesky')}")
            print()
        else:
            print(f"❌ {video_id} は DB に見つかりません")
            print()

    print("=" * 80)

if __name__ == "__main__":
    check_videos_in_db()
