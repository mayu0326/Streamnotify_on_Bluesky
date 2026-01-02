#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
特定動画の分類状態を調査
"""

import sys
import os
import json
from pathlib import Path

# パス設定
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from database import get_database
from plugins.youtube.youtube_api_plugin import YouTubeAPIPlugin
from plugins.youtube_live_plugin import YouTubeLivePlugin

VIDEO_ID = "q-qavmJ5FjM"

def investigate_video(video_id: str):
    """動画の分類状態を調査"""
    print(f"\n🔍 動画の分類状態を調査中: {video_id}\n")
    print("=" * 70)

    # 1. DB から動画情報を取得
    db = get_database("data/video_list.db")
    all_videos = db.get_all_videos()

    video = None
    for v in all_videos:
        if v.get("video_id") == video_id:
            video = v
            break

    if not video:
        print(f"❌ DB に見つかりません: {video_id}")
        return

    print("📋 DB 登録状態:")
    print(f"  ID: {video.get('id')}")
    print(f"  video_id: {video.get('video_id')}")
    print(f"  title: {video.get('title')}")
    print(f"  content_type: {video.get('content_type', 'None')}")
    print(f"  live_status: {video.get('live_status', 'None')}")
    print(f"  published_at: {video.get('published_at')}")
    print(f"  source: {video.get('source')}")

    # 2. キャッシュから詳細情報を取得
    print("\n" + "=" * 70)
    print("🔍 キャッシュから詳細情報を検索:")

    # API プラグインの初期化
    try:
        api_plugin = YouTubeAPIPlugin()
        cached_detail = api_plugin._get_cached_video_detail(video_id)

        if cached_detail:
            print(f"  ✅ キャッシュに存在します")
            print(f"  Content Type: {cached_detail.get('contentDetails', {}).get('videoDetails', {}).get('contentType')}")
            print(f"  Live Stream Details: {bool(cached_detail.get('liveStreamingDetails'))}")

            if cached_detail.get('liveStreamingDetails'):
                live_details = cached_detail.get('liveStreamingDetails', {})
                print(f"    - actualStartTime: {live_details.get('actualStartTime')}")
                print(f"    - actualEndTime: {live_details.get('actualEndTime')}")
                print(f"    - scheduledStartTime: {live_details.get('scheduledStartTime')}")
        else:
            print(f"  ❌ キャッシュに存在しません")

            # API から直接取得を試みる
            print(f"\n  🔄 API から直接取得を試みます...")
            try:
                api_detail = api_plugin._fetch_video_detail(video_id)
                if api_detail:
                    print(f"  ✅ API から取得成功")
                    print(f"  Content Type: {api_detail.get('contentDetails', {}).get('videoDetails', {}).get('contentType')}")
                    print(f"  Live Stream Details: {bool(api_detail.get('liveStreamingDetails'))}")

                    if api_detail.get('liveStreamingDetails'):
                        live_details = api_detail.get('liveStreamingDetails', {})
                        print(f"    - actualStartTime: {live_details.get('actualStartTime')}")
                        print(f"    - actualEndTime: {live_details.get('actualEndTime')}")
                        print(f"    - scheduledStartTime: {live_details.get('scheduledStartTime')}")
                else:
                    print(f"  ⚠️ API から詳細情報を取得できませんでした")
            except Exception as e:
                print(f"  ❌ API エラー: {e}")
    except Exception as e:
        print(f"❌ API プラグイン初期化エラー: {e}")
        return

    # 3. YouTube Live キャッシュを確認
    print("\n" + "=" * 70)
    print("🔍 YouTube Live キャッシュを確認:")

    try:
        cache_file = Path("data/youtube_live_cache.json")
        if cache_file.exists():
            with open(cache_file, 'r', encoding='utf-8') as f:
                live_cache = json.load(f)

            if video_id in live_cache.get('live_videos', {}):
                live_video = live_cache['live_videos'][video_id]
                print(f"  ✅ Live キャッシュに存在")
                print(f"    - status: {live_video.get('status')}")
                print(f"    - first_detected_at: {live_video.get('first_detected_at')}")
                print(f"    - last_updated_at: {live_video.get('last_updated_at')}")
            else:
                print(f"  ℹ️ Live キャッシュには存在しません")
        else:
            print(f"  ℹ️ キャッシュファイルが存在しません")
    except Exception as e:
        print(f"  ⚠️ キャッシュ確認エラー: {e}")

    # 4. 分類ロジックをシミュレート
    print("\n" + "=" * 70)
    print("🔍 分類ロジックのシミュレーション:")

    if cached_detail or api_detail:
        details = cached_detail or api_detail
        try:
            live_plugin = YouTubeLivePlugin()
            content_type, live_status, is_premiere = live_plugin._classify_live(details)
            print(f"  分類結果:")
            print(f"    - content_type: {content_type}")
            print(f"    - live_status: {live_status}")
            print(f"    - is_premiere: {is_premiere}")
        except Exception as e:
            print(f"  ⚠️ 分類エラー: {e}")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    investigate_video(VIDEO_ID)
