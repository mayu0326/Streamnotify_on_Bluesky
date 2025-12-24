#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
既存のアーカイブ動画の published_at を JST に変換して更新するスクリプト

DB に登録されているアーカイブ動画のうち、published_at が UTC 形式のものを
JST に変換して保存し直します。
"""

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

DB_PATH = "data/video_list.db"


def convert_utc_to_jst(utc_datetime_str: str) -> str:
    """
    UTC ISO 8601 形式の日時を JST に変換

    Args:
        utc_datetime_str: UTC 日時文字列（例: "2025-12-28T18:00:00Z" または "2025-12-28T18:00:00+00:00"）

    Returns:
        JST 日時文字列（例: "2025-12-29 03:00:00"）
    """
    try:
        # UTC 日時をパース
        utc_time = datetime.fromisoformat(utc_datetime_str.replace('Z', '+00:00'))
        # JST（UTC+9）に変換して tzinfo を削除
        jst_time = utc_time.astimezone(timezone(timedelta(hours=9))).replace(tzinfo=None)
        return jst_time.strftime('%Y-%m-%d %H:%M:%S')
    except Exception as e:
        print(f"⚠️  UTC→JST 変換失敗、元の値を使用: {utc_datetime_str} - {e}")
        return utc_datetime_str


def is_utc_format(datetime_str: str) -> bool:
    """
    日時文字列が UTC 形式かどうかを判定

    Args:
        datetime_str: 日時文字列

    Returns:
        True: UTC 形式, False: JST 形式またはその他
    """
    if not datetime_str:
        return False

    # "Z" または "+00:00" を含む場合は UTC
    if "Z" in str(datetime_str) or "+00:00" in str(datetime_str):
        return True

    return False


def fix_archive_jst():
    """
    DB に登録されているアーカイブ動画の published_at を JST に変換
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # アーカイブ動画を取得（content_type='archive'）
        cursor.execute("""
            SELECT id, video_id, title, content_type, live_status, published_at
            FROM videos
            WHERE content_type = 'archive'
            ORDER BY published_at DESC
        """)

        archive_videos = cursor.fetchall()
        conn.close()

        if not archive_videos:
            print("ℹ️  DB にアーカイブ動画がありません")
            return 0

        print("=" * 80)
        print("🔄 既存のアーカイブ動画の JST 変換を開始します")
        print("=" * 80)
        print(f"📊 対象: {len(archive_videos)} 件のアーカイブ動画\n")

        updated_count = 0
        skipped_count = 0

        for video in archive_videos:
            video_id = video["video_id"]
            title = video["title"]
            published_at = video["published_at"]
            content_type = video["content_type"]
            live_status = video["live_status"]

            print(f"\n🎬 {title}")
            print(f"   video_id: {video_id}")
            print(f"   content_type: {content_type}")
            print(f"   live_status: {live_status}")
            print(f"   published_at: {published_at}")

            # UTC 形式かどうか判定
            if is_utc_format(published_at):
                # UTC 形式 → JST に変換
                published_at_jst = convert_utc_to_jst(published_at)
                print(f"   ⚠️  UTC 形式で保存されています")
                print(f"   変換後: {published_at_jst}")

                # DB を更新
                try:
                    conn = sqlite3.connect(DB_PATH)
                    cursor = conn.cursor()

                    cursor.execute("""
                        UPDATE videos SET published_at = ? WHERE video_id = ?
                    """, (published_at_jst, video_id))

                    conn.commit()
                    conn.close()

                    print(f"   ✅ DB を更新しました")
                    updated_count += 1

                except Exception as e:
                    print(f"   ❌ DB 更新に失敗: {e}")

            else:
                # 既に JST 形式
                print(f"   ✅ JST 形式で保存されています（変換不要）")
                skipped_count += 1

        print("\n" + "=" * 80)
        print(f"📊 処理完了")
        print(f"   ✅ 更新: {updated_count} 件")
        print(f"   ⏭️  スキップ（既に JST）: {skipped_count} 件")
        print("=" * 80)

        return updated_count

    except Exception as e:
        print(f"❌ エラー: {e}")
        return 0


if __name__ == "__main__":
    fix_archive_jst()
