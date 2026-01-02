#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YouTube Live 分類ロジック - モック データ テスト

実際の API が不要なモック データを使用して
分類ロジックの全パターンを検証
"""
import sys
from pathlib import Path

# v2 パスを追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from plugins.youtube.youtube_api_plugin import YouTubeAPIPlugin


def create_test_cases():
    """テストケースを定義"""
    return [
        {
            "name": "通常動画",
            "details": {
                "snippet": {"liveBroadcastContent": "none"},
                "status": {"uploadStatus": "processed"},
                "liveStreamingDetails": {}
            },
            "expected": ("video", None, False),
            "description": "定期配信後のアップロード動画"
        },
        {
            "name": "配信中（ライブ）",
            "details": {
                "snippet": {"liveBroadcastContent": "live"},
                "status": {"uploadStatus": "processed"},
                "liveStreamingDetails": {
                    "actualStartTime": "2025-12-18T10:00:00Z"
                }
            },
            "expected": ("live", "live", True),  # uploadStatus='processed' でプレミア判定有効
            "description": "現在配信中のライブストリーム（プレミア判定有効）"
        },
        {
            "name": "配信予定（upcoming）",
            "details": {
                "snippet": {"liveBroadcastContent": "upcoming"},
                "status": {"uploadStatus": "processed"},
                "liveStreamingDetails": {
                    "scheduledStartTime": "2025-12-19T14:00:00Z"
                }
            },
            "expected": ("live", "upcoming", True),  # uploadStatus='processed' でプレミア判定有効
            "description": "これからライブ配信予定（プレミア判定有効）"
        },
        {
            "name": "配信終了（アーカイブ）",
            "details": {
                "snippet": {"liveBroadcastContent": "live"},
                "status": {"uploadStatus": "processed"},
                "liveStreamingDetails": {
                    "actualStartTime": "2025-12-18T10:00:00Z",
                    "actualEndTime": "2025-12-18T11:30:00Z"
                }
            },
            "expected": ("archive", "completed", True),  # actualEndTime あり時は always premiere
            "description": "配信が終了してアーカイブ化（プレミア判定有効）"
        },
        {
            "name": "通常ライブ（uploadStatus なし）",
            "details": {
                "snippet": {"liveBroadcastContent": "live"},
                "status": {"uploadStatus": "uploaded"},
                "liveStreamingDetails": {
                    "actualStartTime": "2025-12-18T15:00:00Z"
                }
            },
            "expected": ("live", "live", False),
            "description": "uploadStatus!='processed' のためプレミア判定なし"
        },
        {
            "name": "プレミア公開（予定・正式）",
            "details": {
                "snippet": {"liveBroadcastContent": "upcoming"},
                "status": {"uploadStatus": "processed"},
                "liveStreamingDetails": {
                    "scheduledStartTime": "2025-12-19T19:00:00Z"
                }
            },
            "expected": ("live", "upcoming", True),
            "description": "プレミア公開予定配信（正式な判定）"
        },
        {
            "name": "liveStreamingDetails なし（broadcast_type=live）",
            "details": {
                "snippet": {"liveBroadcastContent": "live"},
                "status": {"uploadStatus": "uploaded"},
                "liveStreamingDetails": {}
            },
            "expected": ("live", "live", False),
            "description": "詳細情報がない場合のLive判定"
        },
        {
            "name": "エッジケース：liveBroadcastContent が completed",
            "details": {
                "snippet": {"liveBroadcastContent": "completed"},
                "status": {"uploadStatus": "processed"},
                "liveStreamingDetails": {}
            },
            "expected": ("video", None, False),
            "description": "completed は System 1 で none 扱い（通常動画）"
        },
        {
            "name": "エッジケース：snippet フィールド不完全",
            "details": {
                "snippet": {},
                "status": {},
                "liveStreamingDetails": {}
            },
            "expected": ("video", None, False),
            "description": 'liveBroadcastContent なし → "none" として処理'
        },
        {
            "name": "アーカイブ（通常ライブ配信の終了形）",
            "details": {
                "snippet": {"liveBroadcastContent": "live"},
                "status": {"uploadStatus": "uploaded"},
                "liveStreamingDetails": {
                    "actualStartTime": "2025-12-18T10:00:00Z",
                    "actualEndTime": "2025-12-18T11:30:00Z"
                }
            },
            "expected": ("archive", "completed", False),
            "description": "通常ライブ（uploadStatus!=processed）の終了形"
        },
    ]


def format_result(content_type, live_status, is_premiere):
    """結果をフォーマット"""
    s = content_type
    if live_status:
        s += f" ({live_status})"
    if is_premiere:
        s += " [premiere]"
    return s


def main():
    """メイン処理"""
    print("\n" + "="*80)
    print("🧪 YouTube Live 分類ロジック - モック データ テスト")
    print("="*80 + "\n")

    test_cases = create_test_cases()
    passed = 0
    failed = 0

    print(f"{'#':<3} {'テストケース':<20} {'期待値':<30} {'実際の値':<30} {'結果'}")
    print("-" * 100)

    for i, test_case in enumerate(test_cases, 1):
        name = test_case["name"]
        details = test_case["details"]
        expected = test_case["expected"]
        description = test_case["description"]

        # 分類ロジックを適用
        result = YouTubeAPIPlugin._classify_video_core(details)

        # 期待値と比較
        is_correct = result == expected

        expected_str = format_result(*expected)
        result_str = format_result(*result)
        status = "✅ PASS" if is_correct else "❌ FAIL"

        print(f"{i:<3} {name:<20} {expected_str:<30} {result_str:<30} {status}")

        if is_correct:
            passed += 1
        else:
            failed += 1
            # 詳細情報を表示
            print(f"      📝 {description}")
            print(f"         期待: {expected}")
            print(f"         実際: {result}")

    print("-" * 100)
    print(f"\n{'='*80}")
    print(f"📊 テスト結果: {passed}/{len(test_cases)} 合格")

    if failed == 0:
        print("🎉 すべてのテストケースに合格しました！")
        print("\n✨ 分類ロジック仕様:")
        print("   【System 1】 liveBroadcastContent で第一判定")
        print("   【System 2】 liveStreamingDetails フィールド検査順序")
        print("   【System 3】 プレミア公開判定（uploadStatus='processed'）")
        print("   【System 4】 liveStreamingDetails なし時の broadcast_type 判定")
        print("   【System 5】 エッジケース（フィールド欠落など）")
        print("   【System 6】 戻り値: (content_type, live_status, is_premiere)")
    else:
        print(f"⚠️  {failed} つのテストが失敗しました")

    print("="*80 + "\n")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
