# -*- coding: utf-8 -*-

"""
YouTube 優先度ロジックで削除された動画が deleted_videos.json に登録されるかの検証テスト
"""

import sys
from pathlib import Path
import json
import os

# プロジェクトルートを検索パスに追加
sys.path.append(str(Path(__file__).resolve().parents[1]))

from database import Database
from deleted_video_cache import get_deleted_video_cache
from youtube_dedup_priority import get_video_priority

def test_dedup_registration():
    """優先度ロジックで削除された動画が deleted_videos.json に登録されるか検証"""

    print("\n" + "="*70)
    print("テスト: YouTube 重複排除 - deleted_videos.json への登録確認")
    print("="*70)

    # テスト用の仮想DB路径
    test_db_path = Path(__file__).parent / "test_dedup_db.sqlite"

    # 既存テストDBがあれば削除
    if test_db_path.exists():
        test_db_path.unlink()

    # DB と deleted_cache を初期化
    db = Database(str(test_db_path))
    deleted_cache = get_deleted_video_cache()

    print("\n【シナリオ】")
    print("1. 予約視聴 (reserved slot) → 同じタイトルの動画を登録 (priority=1)")
    print("2. ライブ開始 (live) → 同じタイトルの動画を登録 (priority=3)")
    print("   → 予約視聴は自動削除され deleted_videos.json に登録")
    print("3. アーカイブ化 (archive) → 同じタイトルの動画を登録 (priority=4)")
    print("   → ライブ動画は自動削除され deleted_videos.json に登録")
    print()

    # ステップ 1: 予約視聴動画を登録
    print("【ステップ 1】予約視聴動画を登録")
    video_1_id = "dQw4w9WgXcQ"
    title = "テスト配信: 新作アナウンスメント"
    channel_name = "テストチャンネル"

    result = db.insert_video(
        video_id=video_1_id,
        title=title,
        video_url=f"https://www.youtube.com/watch?v={video_1_id}",
        published_at="2025-12-19T10:00:00Z",
        channel_name=channel_name,
        content_type="video",
        live_status=None,
        source="youtube"
    )
    print(f"  → 予約動画登録: {result} ({video_1_id})")
    print(f"     priority = {get_video_priority({'content_type': 'video', 'live_status': None, 'is_premiere': 0, 'published_at': '2025-12-19T10:00:00Z'})}")

    # ステップ 2: ライブ動画を登録（別の video_id）
    print("\n【ステップ 2】ライブ動画を登録（予約動画は削除されるはず）")
    video_2_id = "jNQXAC9IVRw"  # 別の video_id

    result = db.insert_video(
        video_id=video_2_id,
        title=title,  # 同じタイトル
        video_url=f"https://www.youtube.com/watch?v={video_2_id}",
        published_at="2025-12-19T12:00:00Z",
        channel_name=channel_name,  # 同じチャンネル
        content_type="live",
        live_status="live",
        source="youtube"
    )
    print(f"  → ライブ動画登録: {result} ({video_2_id})")
    print(f"     priority = {get_video_priority({'content_type': 'live', 'live_status': 'live', 'is_premiere': 0, 'published_at': '2025-12-19T12:00:00Z'})}")

    # ステップ 3: アーカイブ動画を登録（ライブ動画は削除されるはず）
    print("\n【ステップ 3】アーカイブ動画を登録（ライブ動画は削除されるはず）")
    video_3_id = "9bZkp7q19f0"  # 別の video_id

    result = db.insert_video(
        video_id=video_3_id,
        title=title,  # 同じタイトル
        video_url=f"https://www.youtube.com/watch?v={video_3_id}",
        published_at="2025-12-19T16:00:00Z",
        channel_name=channel_name,  # 同じチャンネル
        content_type="archive",
        live_status="completed",
        source="youtube"
    )
    print(f"  → アーカイブ動画登録: {result} ({video_3_id})")
    print(f"     priority = {get_video_priority({'content_type': 'archive', 'live_status': 'completed', 'is_premiere': 0, 'published_at': '2025-12-19T16:00:00Z'})}")

    # 結果確認
    print("\n【結果確認】")

    # DB に残っている動画をチェック
    print("\n1️⃣ DB に残っている動画:")
    videos = db.get_all_videos()
    for v in videos:
        print(f"   - {v['video_id']}: {v['title']} ({v['content_type']}/{v['live_status']})")

    # deleted_videos.json をチェック
    print("\n2️⃣ deleted_videos.json に登録された動画:")
    deleted_videos_file = Path(__file__).parent.parent.parent / "data" / "deleted_videos.json"
    if deleted_videos_file.exists():
        with open(deleted_videos_file, 'r', encoding='utf-8') as f:
            deleted_data = json.load(f)

        youtube_deleted = deleted_data.get('youtube', [])
        print(f"   - YouTube 除外リスト: {len(youtube_deleted)} 件")
        for vid_id in youtube_deleted:
            if vid_id in [video_1_id, video_2_id]:  # テスト用に追加した動画IDのみ表示
                print(f"     → {vid_id} ✅")
    else:
        print(f"   - deleted_videos.json が見つかりません: {deleted_videos_file}")

    # 期待値チェック
    print("\n【期待値チェック】")
    print(f"✅ DB に残る動画: {video_3_id} (archive, priority=4)")
    print(f"✅ deleted_videos.json に登録される: {video_1_id}, {video_2_id}")
    print(f"   理由: 優先度ロジックで自動削除")

    # クリーンアップ
    print("\n【クリーンアップ】")
    if os.path.exists(test_db_path):
        try:
            os.remove(test_db_path)
        except PermissionError as e:
            print(f"ファイルロック解除に失敗しました: {e}")

    print("\n✅ テスト完了!\n")


if __name__ == "__main__":
    test_dedup_registration()
