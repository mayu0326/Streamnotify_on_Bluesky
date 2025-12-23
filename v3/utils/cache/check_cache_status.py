#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
キャッシュ状態確認スクリプト

YouTube Live 判定後のキャッシュ状態を確認
"""

import sys
import json
from pathlib import Path

print("=" * 70)
print("📦 キャッシュ状態確認")
print("=" * 70)

# キャッシュファイルパス
cache_file = Path(__file__).parent.parent / "v3" / "youtube_video_detail_cache.json"

print(f"\n📍 キャッシュファイル: {cache_file}")
print("-" * 70)

if not cache_file.exists():
    print("❌ キャッシュファイルが見つかりません（初回作成時は後で生成されます）")
else:
    try:
        with open(cache_file, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)

        print(f"✅ キャッシュファイル存在")
        print(f"📊 キャッシュ件数: {len(cache_data)} 件")

        # 最新のキャッシュ3件を表示
        if cache_data:
            import time
            from datetime import datetime

            # タイムスタンプでソート
            sorted_items = sorted(
                cache_data.items(),
                key=lambda x: x[1].get("timestamp", 0),
                reverse=True
            )

            print("\n📅 最新のキャッシュ（上位3件）:")
            print("-" * 70)

            for video_id, cache_item in sorted_items[:3]:
                timestamp = cache_item.get("timestamp", 0)
                data = cache_item.get("data", {})
                title = data.get("snippet", {}).get("title", "N/A")[:50]

                cache_time = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")

                print(f"\n  🎬 {video_id}")
                print(f"     タイトル: {title}...")
                print(f"     キャッシュ時刻: {cache_time}")

                # liveStreamingDetails を確認
                live_details = data.get("liveStreamingDetails", {})
                if live_details:
                    status = "未定"
                    if "actualStartTime" in live_details:
                        status = "配信中/完了"
                    elif "scheduledStartTime" in live_details:
                        status = "予約枠"

                    print(f"     ライブ情報: {status}")

    except json.JSONDecodeError as e:
        print(f"❌ キャッシュファイルが破損しています: {e}")
    except Exception as e:
        print(f"❌ エラー: {e}")

print("\n" + "=" * 70)
print("✨ キャッシュは自動的に更新・保存されます")
print("=" * 70)
