# -*- coding: utf-8 -*-
"""
テンプレート選択ロジックのテスト

YouTubeLiveの投稿時に、正しいテンプレートが選択されているか確認
"""
import sys
import os
from pathlib import Path

# v3ディレクトリをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from database import get_database

def test_template_selection():
    """DBから YouTube Live の動画を取得して、テンプレート選択ロジックをシミュレート"""

    db = get_database("v3/data/video_list.db")
    videos = db.get_all_videos()

    print("=" * 80)
    print("🔍 テンプレート選択ロジック検証")
    print("=" * 80)

    # YouTube のライブ・アーカイブを抽出
    youtube_videos = [v for v in videos if v.get("source", "").lower() == "youtube"]

    if not youtube_videos:
        print("❌ YouTube の動画がデータベースに見つかりません")
        return

    print(f"\n📊 YouTube 動画数: {len(youtube_videos)}\n")

    for i, video in enumerate(youtube_videos[:10], 1):  # 最初の10件を表示
        print(f"\n--- 動画 #{i} ---")
        print(f"  動画ID: {video.get('video_id')}")
        print(f"  タイトル: {video.get('title', 'N/A')[:50]}")
        print(f"  source: {video.get('source', 'N/A')}")
        print(f"  classification_type: {video.get('classification_type', 'N/A')}")
        print(f"  content_type: {video.get('content_type', 'N/A')}")
        print(f"  live_status: {video.get('live_status', 'N/A')}")

        # テンプレート選択ロジック（bluesky_plugin.py より）
        source = video.get("source", "youtube").lower()
        live_status = video.get("live_status")
        classification_type = video.get("classification_type", "video")

        # テンプレート選択ロジック（修正後）
        selected_template = "unknown"

        if source == "youtube":
            # classification_type を優先判定（修正後のロジック）
            if classification_type == "live":
                selected_template = "youtube_online"
            elif classification_type == "archive":
                selected_template = "youtube_offline"
            else:
                selected_template = "youtube_new_video"
        elif source in ("niconico", "nico"):
            selected_template = "nico_new_video"

        print(f"  ✅ 選択されたテンプレート: {selected_template}")

        # 推奨テンプレート（classification_type ベース）
        if source == "youtube":
            if classification_type == "live":
                print(f"  ⚠️  推奨テンプレート: youtube_online（classification_type='live'）")
            elif classification_type == "archive":
                print(f"  ⚠️  推奨テンプレート: youtube_offline（classification_type='archive'）")
            else:
                print(f"  ℹ️  推奨テンプレート: youtube_new_video（classification_type='video'）")

if __name__ == "__main__":
    test_template_selection()
