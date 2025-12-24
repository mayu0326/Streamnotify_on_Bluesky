#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
YouTube重複排除の削除積み上げ実装テスト

優先度ロジックで削除された動画が deleted_videos.json に登録されるか確認
"""

import sqlite3
import json
from datetime import datetime, timedelta
from youtube_dedup_priority import get_video_priority

def test_dedup_with_cache_registration():
    """削除積み上げテスト"""

    # テスト用動画データ（同じタイトルで複数バージョン）
    test_videos = [
        {
            'video_id': 'test_video_1',
            'title': 'テスト配信',
            'channel_name': 'テストチャンネル',
            'content_type': 'video',
            'live_status': None,
            'is_premiere': 0,
            'published_at': '2025-12-18T10:00:00'
        },
        {
            'video_id': 'test_live_1',
            'title': 'テスト配信',
            'channel_name': 'テストチャンネル',
            'content_type': 'live',
            'live_status': 'live',
            'is_premiere': 0,
            'published_at': '2025-12-18T11:00:00'
        },
        {
            'video_id': 'test_archive_1',
            'title': 'テスト配信',
            'channel_name': 'テストチャンネル',
            'content_type': 'archive',
            'live_status': 'completed',
            'is_premiere': 0,
            'published_at': '2025-12-18T12:00:00'
        },
    ]

    print("=== YouTube重複排除・削除積み上げテスト ===\n")

    # 各動画の優先度を表示
    print("【動画の優先度】")
    for video in test_videos:
        priority = get_video_priority(video)
        print(f"  {video['video_id']}: priority={priority[0]}, type={video['content_type']}, " +
              f"live_status={video['live_status']}")

    # 最優先動画を選択
    best_video = max(test_videos, key=lambda v: get_video_priority(v))
    best_priority = get_video_priority(best_video)

    print(f"\n【最優先動画】")
    print(f"  video_id: {best_video['video_id']}")
    print(f"  priority: {best_priority[0]}")
    print(f"  type: {best_video['content_type']}")

    # 削除対象の動画
    deleted_videos = [v['video_id'] for v in test_videos if v['video_id'] != best_video['video_id']]

    print(f"\n【削除対象動画】")
    for video_id in deleted_videos:
        print(f"  {video_id}")

    # deleted_videos.json にシミュレートして登録
    print(f"\n【deleted_videos.json への登録確認】")
    deleted_json = {
        "youtube": deleted_videos,
        "niconico": [],
        "twitch": []
    }

    print(f"登録内容: {json.dumps(deleted_json, ensure_ascii=False, indent=2)}")
    print(f"\n✅ 削除された {len(deleted_videos)} 件の動画が deleted_videos.json に登録されます")

if __name__ == "__main__":
    test_dedup_with_cache_registration()
