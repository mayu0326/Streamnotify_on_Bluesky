#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
指定した動画ID の YouTube API データを確認するスクリプト
"""

import sys
from pathlib import Path

# v3 ディレクトリをパスに追加
v3_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(v3_path))

# 設定を読み込み
from config import get_config
config = get_config(str(v3_path / "settings.env"))

from plugins.youtube_api_plugin import YouTubeAPIPlugin
import json

print("=" * 80)
print("🔍 YouTube API - 動画詳細確認")
print("=" * 80)

# コマンドラインから video_id を取得
if len(sys.argv) < 2:
    print("❌ 使用方法: python check_video_api_details.py <video_id>")
    print("   例: python check_video_api_details.py 58S5Pzux9BI")
    sys.exit(1)

video_id = sys.argv[1]
print(f"\n🎬 Video ID: {video_id}\n")

try:
    # YouTube API プラグイン初期化
    api_plugin = YouTubeAPIPlugin()
    
    if not api_plugin.is_available():
        print("❌ YouTube API キーが設定されていません。")
        print("   settings.env で YOUTUBE_API_KEY を設定してください。")
        sys.exit(1)
    
    # YouTube API から動画詳細を取得
    details = api_plugin.fetch_video_detail(video_id)
    
    if not details:
        print(f"❌ 動画詳細取得に失敗しました: {video_id}")
        sys.exit(1)
    
    snippet = details.get("snippet", {})
    live_details = details.get("liveStreamingDetails", {})
    status = details.get("status", {})
    
    print("📋 基本情報:")
    print(f"  タイトル: {snippet.get('title')}")
    print(f"  チャンネル: {snippet.get('channelTitle')}")
    print(f"  liveBroadcastContent: {snippet.get('liveBroadcastContent')}")
    print()
    
    print("⏰ ライブ配信詳細 (liveStreamingDetails):")
    print(f"  scheduledStartTime: {live_details.get('scheduledStartTime')}")
    print(f"  actualStartTime: {live_details.get('actualStartTime')}")
    print(f"  actualEndTime: {live_details.get('actualEndTime')}")
    print()
    
    print("📅 公開日時:")
    print(f"  publishedAt: {snippet.get('publishedAt')}")
    print()
    
    print("📊 ステータス:")
    print(f"  uploadStatus: {status.get('uploadStatus')}")
    print()
    
    # 分類結果を確認
    content_type, live_status, is_premiere = api_plugin._classify_video(details)
    print("🏷️ 分類結果:")
    print(f"  content_type: {content_type}")
    print(f"  live_status: {live_status}")
    print(f"  is_premiere: {is_premiere}")
    print()
    
    # 優先順位での日時決定
    print("✅ 優先順位で選択される published_at:")
    if live_details.get("scheduledStartTime"):
        print(f"  → scheduledStartTime: {live_details['scheduledStartTime']} ⭐")
    elif live_details.get("actualStartTime"):
        print(f"  → actualStartTime: {live_details['actualStartTime']} ⭐")
    elif snippet.get("publishedAt"):
        print(f"  → publishedAt: {snippet['publishedAt']} ⭐")
    else:
        print(f"  → （値がありません）")
    
    print("\n" + "=" * 80)

except Exception as e:
    print(f"❌ エラー: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
