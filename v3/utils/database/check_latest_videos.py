#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DB の最新の動画情報を確認するスクリプト
"""

import sys
from pathlib import Path

# v3 ディレクトリをパスに追加
v3_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(v3_path))

import sqlite3
from datetime import datetime

# DB パス
DB_PATH = v3_path / "data" / "video_list.db"

print("=" * 80)
print("📊 DB の最新動画情報確認")
print("=" * 80)

if not DB_PATH.exists():
    print(f"❌ DB ファイルが見つかりません: {DB_PATH}")
    sys.exit(1)

print(f"✅ DB パス: {DB_PATH}\n")

try:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 最新の10件を取得
    cursor.execute("""
        SELECT 
            id, 
            video_id, 
            title, 
            published_at, 
            content_type, 
            live_status,
            posted_to_bluesky,
            created_at
        FROM videos
        ORDER BY published_at DESC
        LIMIT 10
    """)

    rows = cursor.fetchall()
    
    print(f"📋 最新の動画（上位10件）:\n")
    
    for i, row in enumerate(rows, 1):
        status_str = f"{row['content_type']}/{row['live_status']}" if row['live_status'] else row['content_type']
        posted = "✅ 投稿済み" if row['posted_to_bluesky'] else "❌ 未投稿"
        
        print(f"{i}. {row['title'][:50]}")
        print(f"   - ID: {row['video_id']}")
        print(f"   - ステータス: {status_str}")
        print(f"   - 公開日時: {row['published_at']}")
        print(f"   - 投稿状態: {posted}")
        print(f"   - DB登録日: {row['created_at']}")
        print()

    conn.close()
    
    print("=" * 80)

except Exception as e:
    print(f"❌ エラー: {e}")
    sys.exit(1)
