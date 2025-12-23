#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
テスト用：実際の archive 動画を live に変更してテスト
ポーリング機構のテスト用
"""

import sqlite3

DB_PATH = "data/video_list.db"

try:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1つの archive 動画を live に変更（テスト用）
    cursor.execute("""
        SELECT video_id FROM videos
        WHERE content_type = 'archive'
        LIMIT 1
    """)

    result = cursor.fetchone()
    if result:
        video_id = result[0]
        cursor.execute("""
            UPDATE videos
            SET live_status = 'live'
            WHERE video_id = ?
        """, (video_id,))

    # 変更された動画を確認
    cursor.execute("""
        SELECT video_id, title, content_type, live_status
        FROM videos
        WHERE live_status = 'live'
        LIMIT 1
    """)

    row = cursor.fetchone()
    if row:
        conn.commit()
        print(f"✅ テスト用に live 状態に変更しました:")
        print(f"   video_id: {row[0]}")
        print(f"   title: {row[1][:40]}")
        print(f"   content_type: {row[2]}")
        print(f"   live_status: {row[3]}")
        print()
        print(f"📝 次のステップ:")
        print(f"   1. アプリケーションを起動")
        print(f"   2. YouTubeLive プラグインの poll_live_status() が実行")
        print(f"   3. キャッシュが作成・更新される")
    else:
        print("❌ archive 動画がありません")

    conn.close()

except Exception as e:
    print(f"❌ エラー: {e}")
