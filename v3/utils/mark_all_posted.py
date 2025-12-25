#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""全動画に投稿済みフラグを一括付与"""

import sys
from datetime import datetime
from database import get_database

def mark_all_as_posted():
    """全動画に投稿済みフラグを付与"""
    db = get_database()
    videos = db.get_all_videos()

    # 未投稿の動画を取得
    unposted = [v for v in videos if v.get('posted_to_bluesky') == 0]

    if not unposted:
        print("既に全て投稿済みです。")
        return 0

    print(f"未投稿動画: {len(unposted)}件")
    print("\n確認: 以下の動画すべてに投稿済みフラグを付けますか？")
    print(f"  - 件数: {len(unposted)}件")

    response = input("\n実行しますか？ [y/N]: ")

    if response.lower() != 'y':
        print("キャンセルしました。")
        return 0

    # フラグを付与
    success_count = 0
    for i, video in enumerate(unposted, 1):
        video_id = video['video_id']
        if db.mark_as_posted(video_id):
            success_count += 1
            print(f"  [{i}/{len(unposted)}] {video_id} - OK")
        else:
            print(f"  [{i}/{len(unposted)}] {video_id} - ERROR")

    print(f"\n完了: {success_count}/{len(unposted)}件のフラグを付与しました。")
    return success_count

if __name__ == "__main__":
    try:
        mark_all_as_posted()
    except KeyboardInterrupt:
        print("\nキャンセルしました。")
        sys.exit(1)
    except Exception as e:
        print(f"エラー: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
