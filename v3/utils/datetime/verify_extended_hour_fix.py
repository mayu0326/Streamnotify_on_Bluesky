#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
拡張時刻計算の検証スクリプト

youtube_schedule テンプレートで、日付の差分から拡張時刻（27時など）が
正しく計算されるかを検証します。

実行: python verify_extended_hour_fix.py
"""

from datetime import datetime
import sys
sys.path.insert(0, '.')

from template_utils import calculate_extended_time_for_event

def format_extended_datetime_range_test(base_date_str: str, extended_hour_or_time) -> str:
    """拡張日時範囲表示用フォーマッタ（テスト用に再実装）"""
    try:
        # base_date_str が文字列の場合のみ処理
        if not isinstance(base_date_str, str):
            return str(base_date_str)

        # 日付を解析
        base_date = datetime.strptime(base_date_str, "%Y-%m-%d").date()

        # extended_hour を整数に変換
        try:
            extended_hour = int(extended_hour_or_time)
        except (ValueError, TypeError):
            return str(extended_hour_or_time)

        # 24時間ごとに日付を計算
        display_hour = extended_hour % 24
        day_offset = extended_hour // 24

        # 基本的な表示（基準日付 + 拡張時刻）
        base_year = base_date.year
        base_month = base_date.month
        base_day = base_date.day

        if day_offset > 0:
            # 翌日以降の場合
            future_date = base_date + __import__('datetime').timedelta(days=day_offset)
            future_weekdays = ['月', '火', '水', '木', '金', '土', '日']
            future_weekday = future_weekdays[future_date.weekday()]

            # 表示: YYYY年MM月DD日EE時(YYYY年MM月DD日(E)午前/午後HH時)
            time_str = f"午前{display_hour:02d}時" if display_hour < 12 else f"午後{display_hour - 12:02d}時"

            return f"{base_year}年{base_month:02d}月{base_day:02d}日{extended_hour}時({future_date.year}年{future_date.month:02d}月{future_date.day:02d}日({future_weekday}){time_str})"
        else:
            # 当日の場合
            weekdays = ['月', '火', '水', '木', '金', '土', '日']
            weekday = weekdays[base_date.weekday()]

            time_str = f"午前{display_hour:02d}時" if display_hour < 12 else f"午後{display_hour - 12:02d}時"

            return f"{base_year}年{base_month:02d}月{base_day:02d}日({weekday}){time_str}"

    except Exception as e:
        print(f"❌ エラー: {e}")
        return str(extended_hour_or_time)

def test_case(name: str, video_dict: dict, expected_extended_hour: int, expected_date: str):
    """テストケースを実行"""
    print(f"\n{'='*60}")
    print(f"テスト: {name}")
    print(f"{'='*60}")

    print(f"入力:")
    print(f"  published_at: {video_dict.get('published_at')}")
    print(f"  created_at: {video_dict.get('created_at')}")

    calculate_extended_time_for_event(video_dict)

    extended_hour = video_dict.get("extended_hour")
    extended_display_date = video_dict.get("extended_display_date")

    print(f"出力:")
    print(f"  extended_hour: {extended_hour}")
    print(f"  extended_display_date: {extended_display_date}")

    # 検証
    success = (extended_hour == expected_extended_hour and
               extended_display_date == expected_date)

    print(f"期待値:")
    print(f"  extended_hour: {expected_extended_hour}")
    print(f"  extended_display_date: {expected_date}")

    if success:
        print(f"\n✅ テスト成功")
        # テンプレート出力を表示
        result = format_extended_datetime_range_test(extended_display_date, int(extended_hour))
        print(f"テンプレート出力: {result}")
    else:
        print(f"\n❌ テスト失敗")

    return success

def main():
    """メインテスト"""
    print("拡張時刻計算の検証")
    print("="*60)

    all_pass = True

    # テストケース 1: 朝3時（27時）- 同日扱い
    test1 = test_case(
        name="テストケース 1: published_at=2025-12-29 03:00 → 2025-12-29 27時",
        video_dict={
            "published_at": "2025-12-29T03:00:00"
        },
        expected_extended_hour=27,  # 24 + 3
        expected_date="2025-12-29"  # DB保存日付（変更なし）
    )
    all_pass = all_pass and test1

    # テストケース 2: 朝9時（33時）- 同日扱い
    test2 = test_case(
        name="テストケース 2: published_at=2025-12-29 09:00 → 2025-12-29 33時",
        video_dict={
            "published_at": "2025-12-29T09:00:00"
        },
        expected_extended_hour=33,  # 24 + 9
        expected_date="2025-12-29"
    )
    all_pass = all_pass and test2

    # テストケース 3: 昼14時（14時）- 当日扱い
    test3 = test_case(
        name="テストケース 3: published_at=2025-12-29 14:00 → 2025-12-29 14時（当日）",
        video_dict={
            "published_at": "2025-12-29T14:00:00"
        },
        expected_extended_hour=14,
        expected_date="2025-12-29"
    )
    all_pass = all_pass and test3

    # テストケース 4: 深夜0時（24時）- 同日扱い
    test4 = test_case(
        name="テストケース 4: published_at=2025-12-29 00:00 → 2025-12-29 24時",
        video_dict={
            "published_at": "2025-12-29T00:00:00"
        },
        expected_extended_hour=24,  # 24 + 0
        expected_date="2025-12-29"
    )
    all_pass = all_pass and test4

    print(f"\n{'='*60}")
    print("全体結果:")
    if all_pass:
        print("✅ すべてのテストが成功しました")
    else:
        print("❌ いくつかのテストが失敗しました")

    return 0 if all_pass else 1

if __name__ == "__main__":
    sys.exit(main())
