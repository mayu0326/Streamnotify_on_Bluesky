# -*- coding: utf-8 -*-
"""テスト動画の投稿済みフラグをリセット"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from database import get_database

db = get_database()
conn = db._get_connection()
cursor = conn.cursor()

# テスト動画をリセット
cursor.execute("UPDATE videos SET posted_to_bluesky=0 WHERE video_id=?", ("TEST_LIVE_20251223",))
conn.commit()

# 確認
cursor.execute("SELECT video_id, posted_to_bluesky, content_type, live_status FROM videos WHERE video_id=?", ("TEST_LIVE_20251223",))
row = cursor.fetchone()
if row:
    print(f"✅ テスト動画をリセット: video_id={row[0]}, posted={row[1]}, content_type={row[2]}, live_status={row[3]}")
else:
    print("❌ テスト動画が見つかりません")

conn.close()
