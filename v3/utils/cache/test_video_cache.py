#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YouTube API ビデオ詳細キャッシング機能のテスト
"""
import sys
sys.path.insert(0, 'v2')
import time
from pathlib import Path

# settings.env から設定を読み込み
from config import get_config
try:
    config = get_config('v2/settings.env')
except Exception:
    print("❌ settings.env が読み込めません")
    sys.exit(1)

from database import get_database
from plugins.youtube_api_plugin import YouTubeAPIPlugin

print("=" * 80)
print("YouTube API ビデオ詳細キャッシング機能テスト")
print("=" * 80)

# DB から最初の5件の YouTube 動画を取得
db = get_database('v2/data/video_list.db')
conn = db._get_connection()
c = conn.cursor()
c.execute('SELECT video_id FROM videos WHERE source = "youtube" LIMIT 5')
video_ids = [row[0] for row in c.fetchall()]
conn.close()

print(f"\nテスト対象: {len(video_ids)} 件の動画")

# プラグインをテスト
try:
    api_plugin = YouTubeAPIPlugin()

    if not api_plugin.is_available():
        print("❌ YouTube API プラグインが利用可能ではありません")
        sys.exit(1)

    print("✅ YouTube API プラグインが利用可能です")

    # テスト 1: 初回取得（API からデータを取得）
    print("\n" + "=" * 80)
    print("テスト 1: 初回取得（API からデータを取得）")
    print("=" * 80)

    initial_cost = api_plugin.daily_cost
    print(f"初期 API コスト: {initial_cost}")

    for i, video_id in enumerate(video_ids[:2], 1):
        print(f"\n{i}. {video_id} を取得...")
        details = api_plugin._fetch_video_detail(video_id)
        if details:
            title = details.get("snippet", {}).get("title", "N/A")
            print(f"   ✅ 取得成功: {title[:50]}")
        else:
            print(f"   ❌ 取得失敗")

    cost_after_first = api_plugin.daily_cost
    print(f"\n初回取得後の API コスト: {cost_after_first} ({cost_after_first - initial_cost} ユニット消費)")

    # テスト 2: 2回目取得（キャッシュから取得、API コスト増加なし）
    print("\n" + "=" * 80)
    print("テスト 2: 2回目取得（キャッシュから取得）")
    print("=" * 80)

    for i, video_id in enumerate(video_ids[:2], 1):
        print(f"\n{i}. {video_id} を再度取得...")
        details = api_plugin._fetch_video_detail(video_id)
        if details:
            title = details.get("snippet", {}).get("title", "N/A")
            print(f"   ✅ キャッシュから取得: {title[:50]}")
        else:
            print(f"   ❌ 取得失敗")

    cost_after_second = api_plugin.daily_cost
    print(f"\n2回目取得後の API コスト: {cost_after_second} ({cost_after_second - cost_after_first} ユニット消費)")

    if cost_after_second == cost_after_first:
        print("✅ キャッシュから取得されたため、API コストが増加しませんでした")
    else:
        print("⚠️  予期しない API コスト増加")

    # テスト 3: バッチ取得（混合：キャッシュとAPI）
    print("\n" + "=" * 80)
    print("テスト 3: バッチ取得（キャッシュとAPI の混合）")
    print("=" * 80)

    print(f"\n取得対象: {video_ids}")
    initial_batch_cost = api_plugin.daily_cost

    batch_results = api_plugin.fetch_video_details_batch(video_ids)
    print(f"取得結果: {len(batch_results)} 件")

    cost_after_batch = api_plugin.daily_cost
    print(f"バッチ取得後の API コスト: {cost_after_batch} ({cost_after_batch - initial_batch_cost} ユニット消費)")

    # テスト 4: キャッシュファイル確認
    print("\n" + "=" * 80)
    print("テスト 4: キャッシュファイル確認")
    print("=" * 80)

    cache_file = Path('v2/data/youtube_video_detail_cache.json')
    if cache_file.exists():
        file_size = cache_file.stat().st_size
        print(f"✅ キャッシュファイルが存在します: {cache_file}")
        print(f"   ファイルサイズ: {file_size:,} bytes")

        # キャッシュ内容確認
        import json
        with open(cache_file, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
            print(f"   キャッシュに保存されている動画数: {len(cache_data)} 件")
            for video_id in list(cache_data.keys())[:3]:
                print(f"   - {video_id}")
    else:
        print(f"❌ キャッシュファイルが見つかりません: {cache_file}")

    # テスト 5: キャッシュ有効期限確認
    print("\n" + "=" * 80)
    print("テスト 5: キャッシュ有効期限確認")
    print("=" * 80)

    if video_ids:
        test_id = video_ids[0]
        timestamp = api_plugin.cache_timestamps.get(test_id, 0)
        is_valid = api_plugin._is_cache_valid(timestamp)
        print(f"動画 {test_id}:")
        print(f"  キャッシュタイムスタンプ: {timestamp}")
        print(f"  有効性: {'✅ 有効' if is_valid else '❌ 期限切れ'}")

    print("\n" + "=" * 80)
    print("✅ すべてのテストが完了しました")
    print("=" * 80)

except Exception as e:
    print(f"❌ エラーが発生しました: {e}")
    import traceback
    traceback.print_exc()
