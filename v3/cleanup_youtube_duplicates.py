#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
YouTube重複登録動画の整理スクリプト（優先度ロジック適用版）

同じタイトル+チャンネル名の動画が複数登録されている場合、
優先度ロジックに基づいて保持するものを決定し、それ以外を削除する。

優先度：
1. アーカイブ（最も優先度が高い）
2. ライブ（アーカイブがない場合）
3. プレミア公開（ライブがない場合で、現在時刻以降またはプレミア開始時刻から10分以内）
4. 通常動画（最も優先度が低い）
"""

import sqlite3
from youtube_dedup_priority import get_video_priority, select_best_video

def cleanup_youtube_duplicates_with_priority():
    """YouTube動画の重複をクリーンアップ（優先度ロジック適用、deleted_videos.json に登録）"""
    conn = sqlite3.connect('data/video_list.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # deleted_video_cache を初期化
    try:
        from deleted_video_cache import get_deleted_video_cache
        deleted_cache = get_deleted_video_cache()
    except ImportError:
        print("⚠️ deleted_video_cache モジュールが見つかりません")
        deleted_cache = None

    # 同じタイトル+チャンネル名で複数登録されている動画を検出
    cursor.execute('''
    SELECT title, channel_name, COUNT(*) as cnt,
           GROUP_CONCAT(id) as ids
    FROM videos
    WHERE source = 'youtube'
    GROUP BY title, channel_name
    HAVING cnt > 1
    ORDER BY cnt DESC
    ''')

    duplicate_groups = cursor.fetchall()
    print(f"=== YouTube重複動画クリーンアップ（優先度ロジック適用）===\n")
    print(f"重複グループ数: {len(duplicate_groups)}\n")

    total_deleted = 0
    registered_to_cache = 0

    for group in duplicate_groups:
        title = group['title']
        channel_name = group['channel_name']
        cnt = group['cnt']
        ids = list(map(int, group['ids'].split(',')))

        print(f"【重複グループ】")
        print(f"  タイトル: {title[:60]}")
        print(f"  チャンネル: {channel_name}")
        print(f"  登録数: {cnt}")

        # 各IDの動画情報を取得
        videos = []
        for vid_id in ids:
            cursor.execute("""
                SELECT id, video_id, content_type, live_status, is_premiere, published_at
                FROM videos
                WHERE id=?
            """, (vid_id,))
            row = cursor.fetchone()
            if row:
                videos.append({
                    'id': row['id'],
                    'video_id': row['video_id'],
                    'content_type': row['content_type'],
                    'live_status': row['live_status'],
                    'is_premiere': row['is_premiere'],
                    'published_at': row['published_at']
                })

        # 各動画の優先度を表示
        print("  動画の優先度:")
        for v in videos:
            priority = get_video_priority(v)
            print(f"    ID={v['id']:3d}, video_id={v['video_id']}, type={v['content_type']:10s}, " +
                  f"live_status={str(v['live_status']):10s}, premiere={v['is_premiere']}, priority={priority[0]}")

        # 最優先の動画を選択
        best_video = select_best_video(videos)
        best_priority = get_video_priority(best_video)

        print(f"  ✅ 保持: ID={best_video['id']:3d}, video_id={best_video['video_id']} (priority={best_priority[0]})")

        # それ以外を削除
        deleted_count = 0
        for v in videos:
            if v['id'] != best_video['id']:
                cursor.execute("DELETE FROM videos WHERE id = ?", (v['id'],))
                priority = get_video_priority(v)
                print(f"  ❌ 削除: ID={v['id']:3d}, video_id={v['video_id']} (priority={priority[0]})")

                # deleted_videos.json に登録
                if deleted_cache:
                    try:
                        deleted_cache.add_deleted_video(v['video_id'], source='youtube')
                        print(f"     📌 deleted_videos.json に登録")
                        registered_to_cache += 1
                    except Exception as e:
                        print(f"     ⚠️ 登録失敗: {e}")

                deleted_count += 1
                total_deleted += 1

        print()

    conn.commit()
    conn.close()

    print(f"\n=== 結果 ===")
    print(f"削除した動画: {total_deleted}件")
    print(f"deleted_videos.json に登録: {registered_to_cache}件")
    print(f"クリーンアップ対象グループ: {len(duplicate_groups)}グループ")

if __name__ == "__main__":
    cleanup_youtube_duplicates_with_priority()
