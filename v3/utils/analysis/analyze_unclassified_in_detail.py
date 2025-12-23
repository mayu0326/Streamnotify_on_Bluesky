#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
content_type="video" の動画の分類結果を詳しく調査
"""

import sys
import os
import json
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).parent.parent / "v3"))

from database import get_database
from plugins.youtube_api_plugin import YouTubeAPIPlugin
from plugins.youtube_live_plugin import YouTubeLivePlugin

def analyze_unclassified_videos():
    """未判定動画を詳しく分析"""
    print("\n🔍 content_type='video' の動画を分析中...\n")
    print("=" * 80)

    db = get_database("data/video_list.db")
    api_plugin = YouTubeAPIPlugin()
    live_plugin = YouTubeLivePlugin()

    all_videos = db.get_all_videos()
    unclassified = [
        v for v in all_videos
        if v.get("content_type") == "video" or v.get("content_type") is None
    ]

    print(f"📊 content_type='video' の動画: {len(unclassified)} 件\n")

    # 分類結果を集計
    classification_results = {}
    has_live_stream_details = 0
    no_live_stream_details = 0

    for video in unclassified[:50]:  # 最初の 50 件を分析
        video_id = video.get("video_id")
        if not video_id:
            continue

        # キャッシュから詳細情報を取得
        details = api_plugin._get_cached_video_detail(video_id)

        if not details:
            print(f"❌ [{video_id}] キャッシュなし: {video.get('title')[:50]}")
            continue

        # liveStreamingDetails の有無を確認
        has_live = bool(details.get('liveStreamingDetails'))
        if has_live:
            has_live_stream_details += 1
        else:
            no_live_stream_details += 1

        # 分類
        try:
            content_type, live_status, is_premiere = live_plugin._classify_live(details)

            key = f"{content_type}_{live_status}"
            if key not in classification_results:
                classification_results[key] = []

            classification_results[key].append({
                'video_id': video_id,
                'title': video.get('title')[:50],
                'has_live_details': has_live
            })

            print(f"📋 [{content_type}/{live_status}] {video_id}: {video.get('title')[:50]}")
        except Exception as e:
            print(f"❌ 分類エラー [{video_id}]: {e}")

    print("\n" + "=" * 80)
    print("📊 分類結果の集計:")
    for key, videos in classification_results.items():
        print(f"  {key}: {len(videos)} 件")

    print(f"\n📊 liveStreamingDetails 統計:")
    print(f"  あり: {has_live_stream_details} 件")
    print(f"  なし: {no_live_stream_details} 件")

    print("\n" + "=" * 80)

if __name__ == "__main__":
    analyze_unclassified_videos()
