#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
YouTube重複登録動画の管理・整理モジュール

同じタイトル+チャンネル名の動画が複数登録されている場合、
優先度ロジックに基づいて保持するものを決定し、それ以外を削除する。

優先度：
1. アーカイブ（最も優先度が高い）
2. ライブ（アーカイブがない場合）
3. プレミア公開（ライブがない場合で、現在時刻以降またはプレミア開始時刻から10分以内）
4. 通常動画（最も優先度が低い）
"""

import sqlite3
import logging
from pathlib import Path

logger = logging.getLogger("AppLogger")

__author__ = "mayuneco(mayunya)"
__copyright__ = "Copyright (C) 2025 mayuneco(mayunya)"
__license__ = "GPLv2"


def _get_db_path():
    """データベースパスを相対パスから解決"""
    v3_root = Path(__file__).parent.parent.parent
    return v3_root / "data" / "video_list.db"


def check_duplicate_videos(db_path=None, limit=20):
    """
    YouTube重複登録動画をチェック

    同じタイトル+チャンネル名で複数登録されている動画を検出して表示

    Args:
        db_path: データベースパス（None の場合は自動解決）
        limit: 表示上限件数

    Returns:
        dict: {
            'duplicate_groups': [重複グループリスト],
            'same_video_id_duplicates': [同一video_idの重複リスト]
        }
    """
    if db_path is None:
        db_path = _get_db_path()

    # v3 ルートをパスに追加（youtube_dedup_priority インポート用）
    import sys
    from pathlib import Path
    v3_root = Path(__file__).parent.parent.parent
    if str(v3_root) not in sys.path:
        sys.path.insert(0, str(v3_root))

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # ============================================
    # 1. 同じtitle+channel_nameで複数登録されている動画
    # ============================================
    cursor.execute('''
    SELECT title, channel_name, COUNT(*) as cnt, GROUP_CONCAT(video_id, ',') as video_ids,
           GROUP_CONCAT(content_type, ',') as content_types,
           GROUP_CONCAT(live_status, ',') as live_statuses,
           GROUP_CONCAT(CAST(is_premiere AS TEXT), ',') as premieres
    FROM videos
    WHERE source = 'youtube'
    GROUP BY title, channel_name
    HAVING cnt > 1
    ORDER BY cnt DESC
    LIMIT ?
    ''', (limit,))

    duplicate_groups = [dict(row) for row in cursor.fetchall()]

    print("=== YouTubeの重複登録されている動画 ===\n")

    if not duplicate_groups:
        print("重複登録はありません ✅\n")
    else:
        for row in duplicate_groups:
            print(f"タイトル: {row['title'][:60]}")
            print(f"  登録数: {row['cnt']}")
            print(f"  video_ids: {row['video_ids']}")
            print(f"  content_types: {row['content_types']}")
            print(f"  live_statuses: {row['live_statuses']}")
            print(f"  premieres: {row['premieres']}")
            print()

    # ============================================
    # 2. 同じvideo_idで複数のlive_statusを持つケース
    # ============================================
    cursor.execute('''
    SELECT video_id, title, COUNT(*) as cnt,
           GROUP_CONCAT(DISTINCT live_status) as live_statuses,
           GROUP_CONCAT(DISTINCT content_type) as content_types
    FROM videos
    WHERE source = 'youtube'
    GROUP BY video_id
    HAVING cnt > 1
    ORDER BY cnt DESC
    LIMIT ?
    ''', (limit,))

    same_video_id_duplicates = [dict(row) for row in cursor.fetchall()]

    print("=== 同じvideo_idで複数のlive_statusを持つケース ===\n")

    if not same_video_id_duplicates:
        print("同一video_idの重複はありません ✅\n")
    else:
        for row in same_video_id_duplicates:
            print(f"Video ID: {row['video_id']}")
            print(f"  タイトル: {row['title'][:60]}")
            print(f"  登録数: {row['cnt']}")
            print(f"  live_statuses: {row['live_statuses']}")
            print(f"  content_types: {row['content_types']}")
            print()

    conn.close()

    return {
        'duplicate_groups': duplicate_groups,
        'same_video_id_duplicates': same_video_id_duplicates
    }


def cleanup_youtube_duplicates_with_priority(db_path=None):
    """
    YouTube重複登録動画をクリーンアップ（優先度ロジック適用）

    同じタイトル+チャンネル名の動画が複数登録されている場合、
    優先度に基づいて最優先の動画を保持し、それ以外を削除

    Args:
        db_path: データベースパス（None の場合は自動解決）

    Returns:
        dict: {
            'total_deleted': 削除した件数,
            'registered_to_cache': deleted_videos.json に登録した件数,
            'duplicate_groups': 処理したグループ数
        }
    """
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from youtube_core.youtube_dedup_priority import get_video_priority, select_best_video

    if db_path is None:
        db_path = _get_db_path()

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # deleted_video_cache を初期化
    try:
        from deleted_video_cache import get_deleted_video_cache
        deleted_cache = get_deleted_video_cache()
    except ImportError:
        logger.warning("⚠️ deleted_video_cache モジュールが見つかりません")
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

    return {
        'total_deleted': total_deleted,
        'registered_to_cache': registered_to_cache,
        'duplicate_groups': len(duplicate_groups)
    }


if __name__ == "__main__":
    import sys

    # コマンドラインから実行する場合
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "cleanup":
            cleanup_youtube_duplicates_with_priority()
        elif command == "check":
            check_duplicate_videos()
        else:
            print(f"使用方法: python {sys.argv[0]} [check|cleanup]")
            sys.exit(1)
    else:
        # デフォルトはチェック + クリーンアップ
        check_duplicate_videos()
        print("\n" + "=" * 50 + "\n")
        cleanup_youtube_duplicates_with_priority()
