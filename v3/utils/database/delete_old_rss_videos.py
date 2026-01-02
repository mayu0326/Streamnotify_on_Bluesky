#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
RSS で古い日時で登録された YouTube 動画を削除
新規登録時に YouTube API で正しい日時を取得するようにする
"""

import sys
from pathlib import Path

# v3 ディレクトリをパスに追加
v3_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(v3_path))

import sqlite3
from database import get_database

print("=" * 80)
print("🗑️  RSS で古い日時で登録された YouTube 動画を削除")
print("=" * 80)

DB_PATH = v3_path / "data" / "video_list.db"

if not DB_PATH.exists():
    print(f"❌ DB ファイルが見つかりません: {DB_PATH}")
    sys.exit(1)

print(f"✅ DB パス: {DB_PATH}\n")

if len(sys.argv) < 2:
    print("❌ 使用方法: python delete_old_rss_videos.py <video_id1> [video_id2] ...")
    print("   例: python delete_old_rss_videos.py 58S5Pzux9BI")
    sys.exit(1)

video_ids = sys.argv[1:]

try:
    db = get_database(str(DB_PATH))
    
    print(f"🎬 削除対象の動画ID: {video_ids}\n")
    
    for video_id in video_ids:
        # DB から動画情報を取得
        all_videos = db.get_all_videos()
        video = next((v for v in all_videos if v['video_id'] == video_id), None)
        
        if not video:
            print(f"❌ {video_id}: DB に見つかりません")
            continue
        
        print(f"📝 削除予定:")
        print(f"   タイトル: {video['title'][:50]}")
        print(f"   現在の published_at: {video['published_at']}")
        print(f"   投稿状態: {'✅ 投稿済み' if video['posted_to_bluesky'] else '❌ 未投稿'}")
        print()
        
        # 削除実行
        result = db.delete_video(video_id)
        
        if result:
            print(f"✅ {video_id}: 削除完了")
            print(f"   → 次回 RSS 更新時に YouTube API から正しい日時で再登録されます\n")
        else:
            print(f"❌ {video_id}: 削除失敗\n")
    
    print("=" * 80)
    print("📌 注意:")
    print("   削除後、次回のポーリング時に YouTube RSS から再度検出されます。")
    print("   その時点で YouTube API プラグインが")
    print("   scheduledStartTime を使用して正しい日時で登録します。")
    print("=" * 80)

except Exception as e:
    print(f"❌ エラー: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
