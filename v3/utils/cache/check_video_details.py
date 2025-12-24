#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
特定のビデオID詳細確認スクリプト

ビデオ SaKd1RqfM5A の詳細情報をデータベースから取得
"""

import sys
import sqlite3
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

print("=" * 70)
print("🔍 ビデオ詳細確認 (SaKd1RqfM5A)")
print("=" * 70)

try:
    db_path = Path(__file__).parent.parent.parent / "data" / "video_list.db"

    if not db_path.exists():
        print(f"❌ データベースが見つかりません: {db_path}")
        sys.exit(1)

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # ビデオを検索
    cursor.execute("""
        SELECT * FROM videos WHERE video_id = ?
    """, ("SaKd1RqfM5A",))

    row = cursor.fetchone()

    if not row:
        print("❌ ビデオが見つかりません")
        sys.exit(1)

    video = dict(row)

    print("\n📹 ビデオ詳細情報:")
    print("-" * 70)
    for key, value in video.items():
        if key == "title":
            print(f"{key:20s}: {value}")
        elif key == "content_type":
            print(f"{key:20s}: {value}")
        elif key == "live_status":
            print(f"{key:20s}: {value}")
        elif key == "published_at":
            print(f"{key:20s}: {value}")
        elif key == "source":
            print(f"{key:20s}: {value}")

    print("\n📊 分類状態:")
    print("-" * 70)
    content_type = video.get("content_type", "unknown")
    live_status = video.get("live_status")

    if content_type == "video":
        print("⚠️  content_type = 'video'（未判定）")
        print("   理由: YouTube RSS では予約枠も通常動画として表示される")
        print("")
        print("✅ 次のステップ:")
        print("   1️⃣ YouTube Live プラグインが自動判定する")
        print("   2️⃣ または、アプリケーション再起動で on_enable() が実行")
        print("   3️⃣ その後、content_type が 'live'/'archive' に更新される")
    elif content_type == "live":
        print(f"✅ content_type = 'live' (ライブ配信)")
        print(f"   live_status = '{live_status}'")
        if live_status == "upcoming":
            print("   📍 ステータス: 予約枠（配信予定）")
        elif live_status == "live":
            print("   🔴 ステータス: 配信中")
        elif live_status == "completed":
            print("   ✔️  ステータス: 配信終了")
    elif content_type == "archive":
        print(f"✅ content_type = 'archive' (アーカイブ)")
        print(f"   live_status = '{live_status}'")

    conn.close()

    print("\n" + "=" * 70)
    print("✨ 現在の YOUTUBE_LIVE_AUTO_POST_MODE = 'schedule'")
    print("   └─ 予約枠のみを投稿します")
    print("=" * 70)

except Exception as e:
    print(f"❌ エラー: {e}")
    import traceback
    traceback.print_exc()
