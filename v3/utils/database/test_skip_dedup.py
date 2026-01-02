#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""修正後の DB 保存テスト"""

import sys
sys.path.insert(0, '.')

from database import get_database
from logging_config import setup_logging
import logging

setup_logging()
logger = logging.getLogger("AppLogger")

def test_manual_add():
    """手動追加（重複排除スキップ）をテスト"""

    db = get_database()

    # テスト用の動画情報（既に存在する可能性がある）
    video_id = "MBCuCVqH9u4"
    title = "テスト動画"
    channel = "テストチャンネル"

    print("=" * 70)
    print("🧪 テスト: 手動追加（重複排除スキップ）")
    print("=" * 70)

    # 1. skip_dedup=False（通常・重複排除有効）
    print("\n1️⃣ skip_dedup=False （重複排除有効）")
    success1 = db.insert_video(
        video_id=f"{video_id}_normal",
        title=title,
        video_url=f"https://www.youtube.com/watch?v={video_id}_normal",
        published_at="2025-12-24T08:00:00Z",
        channel_name=channel,
        source="youtube",
        skip_dedup=False
    )
    print(f"   結果: {success1}")

    # 2. skip_dedup=True（手動追加・重複排除スキップ）
    print("\n2️⃣ skip_dedup=True （手動追加・重複排除スキップ）")
    success2 = db.insert_video(
        video_id=f"{video_id}_manual",
        title=title,
        video_url=f"https://www.youtube.com/watch?v={video_id}_manual",
        published_at="2025-12-24T08:00:00Z",
        channel_name=channel,
        source="youtube",
        skip_dedup=True
    )
    print(f"   結果: {success2}")

    print("\n" + "=" * 70)

    if success1 and success2:
        print("✅ すべてのテストに成功しました！")
        print("   手動追加時は重複排除をスキップして強制挿入できます")
    else:
        print(f"⚠️ テスト結果:")
        print(f"   通常: {success1}")
        print(f"   手動追加: {success2}")

if __name__ == '__main__':
    test_manual_add()
