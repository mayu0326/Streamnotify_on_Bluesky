#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
同じ video_id の複数登録を調査
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "v3"))

from database import get_database

VIDEO_ID = "q-qavmJ5FjM"

def check_duplicates(video_id: str):
    """同じ video_id の複数登録を確認"""
    print(f"\n🔍 同じ video_id の複数登録を確認中: {video_id}\n")
    print("=" * 70)

    db = get_database("data/video_list.db")
    all_videos = db.get_all_videos()

    matching = [v for v in all_videos if v.get("video_id") == video_id]

    print(f"📊 マッチした件数: {len(matching)}\n")

    for i, video in enumerate(matching, 1):
        print(f"--- 登録 #{i} ---")
        print(f"  id: {video.get('id')}")
        print(f"  video_id: {video.get('video_id')}")
        print(f"  title: {video.get('title')}")
        print(f"  content_type: {video.get('content_type')}")
        print(f"  live_status: {video.get('live_status')}")
        print(f"  published_at: {video.get('published_at')}")
        print(f"  posted_to_bluesky: {video.get('posted_to_bluesky')}")
        print(f"  source: {video.get('source')}")
        print()

    if len(matching) > 1:
        print("⚠️ 複数登録が見つかりました！")
    else:
        print("✅ 登録は1件のみです")

    print("=" * 70)

if __name__ == "__main__":
    check_duplicates(VIDEO_ID)
