# -*- coding: utf-8 -*-
"""
YouTube RSS フィード直接確認スクリプト

YouTube RSS を取得して、実際に何が入っているか確認する
"""

import feedparser
import json
from datetime import datetime

# ユーザーのチャンネルID（settings.envから読み込み）
from config import get_config
config = get_config("settings.env")
channel_id = config.youtube_channel_id

if not channel_id:
    print("❌ チャンネル ID が設定されていません")
    exit(1)

print(f"📡 YouTube RSS フィード確認")
print(f"チャンネル ID: {channel_id}")
print("=" * 60)

# RSS フィードを取得
rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
print(f"RSS URL: {rss_url}\n")

feed = feedparser.parse(rss_url)

print(f"ステータス: {feed.status}")
if feed.bozo:
    print(f"⚠️ 警告: {feed.bozo_exception}")

print(f"\nRSS エントリー数: {len(feed.entries)}\n")

if not feed.entries:
    print("❌ RSS エントリーが見つかりません")
    exit(1)

# 最新15件を表示
print(f"最新15件の動画情報:")
print("-" * 60)

for i, entry in enumerate(feed.entries[:15], 1):
    video_id = entry.get("yt_videoid", "N/A")
    title = entry.get("title", "N/A")
    published = entry.get("published", "N/A")

    print(f"\n[{i}] {title}")
    print(f"    Video ID: {video_id}")
    print(f"    Published: {published}")
    print(f"    Link: {entry.get('link', 'N/A')}")

    # ラッシュな詳細情報があるか確認
    if hasattr(entry, '__dict__'):
        keys = list(entry.keys())
        live_related = [k for k in keys if 'live' in k.lower() or 'broadcast' in k.lower()]
        if live_related:
            print(f"    ライブ関連キー: {live_related}")

print("\n" + "=" * 60)
print("📝 メモ:")
print("- YouTube RSS は配信枠作成後、反映されるまで15分～1時間かかることがあります")
print("- 反映が遅い場合は、YouTube API で直接確認してください")
print("- 'upcoming' や 'live' というテキストが title に含まれている場合もあります")
