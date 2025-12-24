#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
from pathlib import Path

DB_PATH = "data/video_list.db"

def check_published_at():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # DB に保存されている published_at の値を確認
        cursor.execute("SELECT video_id, title, published_at FROM videos ORDER BY published_at DESC LIMIT 5")

        rows = cursor.fetchall()
        conn.close()

        print("=" * 70)
        print("📊 DB に保存されている published_at の値")
        print("=" * 70)

        if not rows:
            print("⚠️  DB に動画がありません")
            return

        for video_id, title, published_at in rows:
            print(f"\n🎬 {title}")
            print(f"   video_id: {video_id}")
            print(f"   published_at: {published_at}")

            # UTC か JST か判定
            if "Z" in str(published_at) or "+" in str(published_at):
                print(f"   ⚠️  UTC形式で保存されています（JST変換が行われていない）")
            elif "T" in str(published_at) and len(str(published_at)) == 19:
                # ISO format YYYY-MM-DD HH:MM:SS
                print(f"   ✅ ISO形式で保存されています（JST の可能性あり）")

        print("\n" + "=" * 70)

    except Exception as e:
        print(f"❌ エラー: {e}")

if __name__ == "__main__":
    check_published_at()
