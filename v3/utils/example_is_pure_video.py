# -*- coding: utf-8 -*-
"""
is_pure_video() 使用例

既存キャッシュから「純粋な動画」を判定する方法
"""

import json
from pathlib import Path
from plugins.youtube.youtube_api_plugin import YouTubeAPIPlugin

def example_check_pure_videos():
    """キャッシュから純粋な動画を判定"""

    cache_path = Path(__file__).parent / "data" / "youtube_video_detail_cache.json"

    if not cache_path.exists():
        print(f"❌ キャッシュが見つかりません: {cache_path}")
        return

    # キャッシュを読み込み
    with open(cache_path, "r", encoding="utf-8") as f:
        cache = json.load(f)

    print("=" * 70)
    print("YouTube キャッシュから「純粋な動画」を判定")
    print("=" * 70)

    pure_count = 0
    live_count = 0
    archive_count = 0
    premiere_count = 0

    for video_id, video_entry in list(cache.items())[:10]:  # 最初の10件をサンプル
        details = video_entry.get("data", {})
        snippet = details.get("snippet", {})
        title = snippet.get("title", "（タイトル未取得）")

        # is_pure_video() で判定
        is_pure = YouTubeAPIPlugin.is_pure_video(details)

        print(f"\n📹 {video_id}")
        print(f"   タイトル: {title[:50]}...")

        # 詳細情報
        live_broadcast = snippet.get("liveBroadcastContent", "none")
        has_live_details = "liveStreamingDetails" in details

        print(f"   liveBroadcastContent: {live_broadcast}")
        print(f"   liveStreamingDetails存在: {has_live_details}")

        if is_pure:
            print(f"   ✅ 判定: 【純粋な動画】")
            pure_count += 1
        else:
            # 詳細な分類
            if live_broadcast in ("live", "upcoming"):
                print(f"   ❌ 判定: 【ライブ/プレミア関連】")
                live_count += 1
            elif has_live_details:
                print(f"   ❌ 判定: 【アーカイブ/過去プレミア】")
                archive_count += 1
            else:
                print(f"   ⚠️  判定: 【その他】")
                premiere_count += 1

    print("\n" + "=" * 70)
    print("集計結果（サンプル）")
    print("=" * 70)
    print(f"✅ 純粋な動画:        {pure_count} 件")
    print(f"📊 ライブ/プレミア:  {live_count} 件")
    print(f"📹 アーカイブ:       {archive_count} 件")
    print(f"⚠️  その他:          {premiere_count} 件")
    print(f"合計:               {pure_count + live_count + archive_count + premiere_count} 件")

    print("\n💡 ポイント")
    print("   - is_pure_video() は毎回 API を呼ぶ必要がありません")
    print("   - キャッシュから直接判定できるため、高速です")
    print("   - cache の data フィールドを直接渡すだけで OK")

if __name__ == "__main__":
    example_check_pure_videos()
