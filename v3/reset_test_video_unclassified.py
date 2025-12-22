# -*- coding: utf-8 -*-
"""
YouTube Live 自動投稿の正確なテスト

RSS で新規取得された動画が、正しく自動投稿されるかテストする
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from database import get_database

db = get_database()
conn = db._get_connection()
cursor = conn.cursor()

# テスト動画を「新規判定状態」に戻す（投稿フラグをリセット）
cursor.execute("""
    UPDATE videos 
    SET posted_to_bluesky=0, content_type=NULL, live_status=NULL 
    WHERE video_id=?
""", ("TEST_LIVE_20251223",))
conn.commit()

# 確認
cursor.execute("""
    SELECT video_id, title, content_type, live_status, posted_to_bluesky 
    FROM videos 
    WHERE video_id=?
""", ("TEST_LIVE_20251223",))

row = cursor.fetchone()
if row:
    print(f"✅ テスト動画をリセット:")
    print(f"   video_id: {row[0]}")
    print(f"   title: {row[1]}")
    print(f"   content_type: {row[2]}")
    print(f"   live_status: {row[3]}")
    print(f"   posted_to_bluesky: {row[4]}")
    print(f"\n📝 これで on_enable() 時に「未判定動画」として自動判定されます")
else:
    print("❌ テスト動画が見つかりません")

conn.close()
