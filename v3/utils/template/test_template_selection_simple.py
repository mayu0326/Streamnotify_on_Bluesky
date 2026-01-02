# -*- coding: utf-8 -*-
"""
テンプレート選択ロジックのテスト - 簡略版

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

    # YouTube のライブ・アーカイブを抽出
    youtube_videos = [v for v in videos if v.get("source", "").lower() == "youtube"]

    print("[Template Selection Test]")
    print("=" * 80)
    print("YouTube Video Count: {}".format(len(youtube_videos)))
    print()

    # テンプレート選択結果をカウント
    template_counts = {}

    for video in youtube_videos[:100]:  # 最初の100件を検査
        source = video.get("source", "youtube").lower()
        classification_type = video.get("classification_type", "video")

        # 修正後のテンプレート選択ロジック
        if source == "youtube":
            if classification_type == "live":
                selected_template = "youtube_online"
            elif classification_type == "archive":
                selected_template = "youtube_archive"
            else:
                selected_template = "youtube_new_video"
        elif source in ("niconico", "nico"):
            selected_template = "nico_new_video"
        else:
            selected_template = "unknown"

        # カウント
        if selected_template not in template_counts:
            template_counts[selected_template] = 0
        template_counts[selected_template] += 1

    print("[Template Selection Results]")
    for template, count in sorted(template_counts.items()):
        print("  {}: {} videos".format(template, count))

    # classification_type ごとの分布
    print()
    print("[Classification Type Distribution]")
    classification_counts = {}
    for video in youtube_videos[:100]:
        ct = video.get("classification_type", "video")
        if ct not in classification_counts:
            classification_counts[ct] = 0
        classification_counts[ct] += 1

    for ct, count in sorted(classification_counts.items()):
        print("  {}: {} videos".format(ct, count))

    # サンプル表示
    print()
    print("[Sample Videos]")
    for i, video in enumerate(youtube_videos[:5], 1):
        print("\n--- Video #{} ---".format(i))
        print("  ID: {}".format(video.get('video_id')))
        print("  Title: {}".format(video.get('title', 'N/A')[:50]))
        print("  classification_type: {}".format(video.get('classification_type', 'N/A')))

        ct = video.get("classification_type", "video")
        if ct == "live":
            template = "youtube_online"
        elif ct == "archive":
            template = "youtube_offline"
        else:
            template = "youtube_new_video"
        print("  -> Template: {}".format(template))

if __name__ == "__main__":
    test_template_selection()
