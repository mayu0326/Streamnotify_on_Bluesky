#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""API と DB 保存を直接テスト"""

import sys
sys.path.insert(0, '.')

from database import get_database
from config import get_config
import logging
from datetime import datetime

# ロギング初期化
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("AppLogger")

# YouTube API 直接呼び出し
def test_api_and_db():
    """API から取得してそのまま DB に保存"""

    from utils_v3 import fetch_youtube_api

    db = get_database()
    config = get_config("settings.env")

    video_id = "MBCuCVqH9u4"

    print("=" * 70)
    print(f"🔍 テスト: {video_id}")
    print("=" * 70)

    # 1. API から取得
    print(f"\n1️⃣ YouTube API から取得...")

    api_key = config.youtube_api_key
    if not api_key:
        print("❌ API キーが設定されていません")
        return

    try:
        video_data = fetch_youtube_api(video_id, api_key)

        if not video_data:
            print("❌ API から取得できませんでした")
            return

        print(f"✅ API から取得\n")

        snippet = video_data.get("snippet", {})

        print(f"📝 取得データ:")
        print(f"  • id: {video_data.get('id')}")
        print(f"  • title: {snippet.get('title', 'N/A')[:60]}...")
        print(f"  • channelTitle: {snippet.get('channelTitle', 'N/A')}")
        print(f"  • publishedAt: {snippet.get('publishedAt', 'N/A')}")

        # 2. DB に保存
        print(f"\n2️⃣ DB に保存...")

        success = db.insert_video(
            video_id=video_id,
            title=snippet.get("title", "【新着動画】"),
            video_url=f"https://www.youtube.com/watch?v={video_id}",
            published_at=snippet.get("publishedAt", datetime.now().isoformat()),
            channel_name=snippet.get("channelTitle", ""),
            content_type="video",
            source="youtube"
        )

        print(f"\n📊 結果: {success}")

        if success:
            print("✅ 成功！")
        else:
            print("❌ 失敗")
            # 原因特定
            all_videos = db.get_all_videos()
            found = False
            for v in all_videos:
                if v.get("video_id") == video_id:
                    print(f"\n⚠️ 理由: 既に DB に存在")
                    print(f"  既存: {v.get('title')[:60]}...")
                    found = True
                    break

            if not found:
                print(f"\n❓ 不明な理由で失敗")
                print(f"   → logs/app.log を確認してください")

    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_api_and_db()
