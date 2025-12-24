#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
テンプレートレンダリング検証スクリプト
拡張時刻の計算と表示形式が正確か確認
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from template_utils import calculate_extended_time_for_event

# テストケース: API から返された JST 時刻
test_videos = [
    {
        "title": "テスト配信 1 - 早朝 3 時",
        "video_id": "test_0300",
        "published_at": "2025-12-29T03:00:00",  # JST 早朝 3 時
        "channel_name": "テストチャンネル",
    },
    {
        "title": "テスト配信 2 - 午前 10 時",
        "video_id": "test_1000",
        "published_at": "2025-12-29T10:00:00",  # JST 午前 10 時
        "channel_name": "テストチャンネル",
    },
    {
        "title": "テスト配信 3 - 午後 18 時",
        "video_id": "test_1800",
        "published_at": "2025-12-29T18:00:00",  # JST 午後 6 時
        "channel_name": "テストチャンネル",
    },
]

print("=" * 80)
print("🔍 拡張時刻テンプレートレンダリング検証")
print("=" * 80)

for video in test_videos:
    print(f"\n🎬 {video['title']}")
    print(f"   published_at: {video['published_at']}")

    try:
        # 関数は video_dict に直接追加する設計（None を返す）
        calculate_extended_time_for_event(video)

        extended_hour = video.get('extended_hour')
        extended_date = video.get('extended_display_date')

        print(f"   ✅ 計算成功:")
        print(f"      extended_hour: {extended_hour}")
        print(f"      extended_display_date: {extended_date}")

        if extended_hour and extended_hour >= 24:
            print(f"   📝 テンプレート出力例:")
            print(f"      開始日時: {extended_date}→{extended_hour}時(27時表記)")
        else:
            print(f"   📝 テンプレート出力例:")
            print(f"      開始日時: {extended_date}→{extended_hour}時(通常表記)")

    except Exception as e:
        print(f"   ❌ エラー: {e}")

print("\n" + "=" * 80)
