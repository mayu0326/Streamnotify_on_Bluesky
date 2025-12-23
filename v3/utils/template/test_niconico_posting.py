#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ニコニコ動画投稿テスト

投稿失敗ログのデバッグ用スクリプト
"""

import sys
import os
from pathlib import Path

# v2 ディレクトリをパスに追加
v2_path = Path(__file__).parent.parent / "v2"
sys.path.insert(0, str(v2_path))
os.chdir(str(v2_path))

# v2 ディレクトリから相対的にインポート
from v2.plugins.youtube_api_plugin import YouTubeAPIPlugin
from v2.plugins.youtube_live_plugin import YouTubeLivePlugin
from v2.plugins.niconico_plugin import NiconicoPlugin
from v2.plugin_manager import PluginManager
import logging

# ロギング設定
logging.basicConfig(level=logging.DEBUG, format='[%(levelname)s] %(name)s: %(message)s')

# テスト用のニコニコ動画データ
test_video = {
    'video_id': 'sm45414087',
    'id': 'sm45414087',
    'title': 'まぶたにまぶたについて説明するつくよみちゃん',
    'channel_name': 'つくよみ',
    'published_at': '2025-09-07',
    'platform': 'Niconico',
    'video_url': 'https://www.nicovideo.jp/watch/sm45414087'
}

print("=" * 60)
print("ニコニコ投稿テスト")
print("=" * 60)
print(f"\nテスト動画:")
print(f"  Video ID: {test_video['video_id']}")
print(f"  Platform: {test_video['platform']}")
print(f"  Title: {test_video['title']}")
print()

# 各プラグインのテスト
print("YouTube API プラグイン:")
try:
    youtube_api = YouTubeAPIPlugin()
    result = youtube_api.post_video(test_video)
    print(f"  結果: {result}")
except Exception as e:
    print(f"  エラー: {e}")

print("\nYouTube Live プラグイン:")
try:
    youtube_live = YouTubeLivePlugin()
    result = youtube_live.post_video(test_video)
    print(f"  結果: {result}")
except Exception as e:
    print(f"  エラー: {e}")

print("\nニコニコプラグイン:")
try:
    niconico = NiconicoPlugin(
        user_id="00000000",
        poll_interval=60,
        db=None,
        user_name="Test User"
    )
    result = niconico.post_video(test_video)
    print(f"  結果: {result}")
except Exception as e:
    print(f"  エラー: {e}")

print("\n" + "=" * 60)
print("完了")
print("=" * 60)
