#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
既存の YouTube 動画の published_at を YouTube API から取得した scheduledStartTime で更新
"""

import sys
from pathlib import Path

# v3 ディレクトリをパスに追加
v3_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(v3_path))

import sqlite3
from database import get_database
from plugins.youtube.youtube_api_plugin import YouTubeAPIPlugin

print("=" * 80)
print("🔄 既存 YouTube 動画の published_at を更新")
print("=" * 80)

DB_PATH = v3_path / "data" / "video_list.db"

if not DB_PATH.exists():
    print(f"❌ DB ファイルが見つかりません: {DB_PATH}")
    sys.exit(1)

print(f"✅ DB パス: {DB_PATH}\n")

try:
    # YouTube API プラグイン初期化
    api_plugin = YouTubeAPIPlugin()

    if not api_plugin.is_available():
        print("❌ YouTube API プラグインが利用不可です。API キーを設定してください。")
        sys.exit(1)

    print("✅ YouTube API プラグイン: 初期化完了\n")

    # DB から YouTube 動画を取得
    db = get_database(str(DB_PATH))
    all_videos = db.get_all_videos()

    # YouTube 動画のみをフィルタ
    youtube_videos = [v for v in all_videos if v.get('source') == 'youtube']
    print(f"📊 DB の YouTube 動画: {len(youtube_videos)} 件\n")

    updated_count = 0

    for video in youtube_videos:
        video_id = video['video_id']

        # YouTube API から動画詳細を取得
        details = api_plugin.fetch_video_detail(video_id)
        if not details:
            print(f"⏭️  {video_id}: API から取得失敗（スキップ）")
            continue

        live_details = details.get("liveStreamingDetails", {})
        snippet = details.get("snippet", {})

        # 優先順位で published_at を取得
        new_published_at = None
        source = ""

        if live_details.get("scheduledStartTime"):
            new_published_at = live_details["scheduledStartTime"]
            source = "scheduledStartTime (配信予定時刻)"
        elif live_details.get("actualStartTime"):
            new_published_at = live_details["actualStartTime"]
            source = "actualStartTime (配信開始時刻)"
        elif snippet.get("publishedAt"):
            new_published_at = snippet["publishedAt"]
            source = "publishedAt (公開日時)"

        if new_published_at:
            old_published_at = video['published_at']

            # DB を更新
            conn = sqlite3.connect(str(DB_PATH))
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE videos
                SET published_at = ?
                WHERE video_id = ?
            """, (new_published_at, video_id))

            conn.commit()
            conn.close()

            print(f"✅ {video_id}: 更新完了")
            print(f"   タイトル: {video['title'][:50]}")
            print(f"   旧: {old_published_at}")
            print(f"   新: {new_published_at} ({source})")
            print()

            updated_count += 1
        else:
            print(f"⏭️  {video_id}: 有効な時刻情報がない（スキップ）")
            print()

    print("=" * 80)
    print(f"🎉 更新完了: {updated_count} 件")
    print("=" * 80)

except Exception as e:
    print(f"❌ エラー: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
