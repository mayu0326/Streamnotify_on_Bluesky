# -*- coding: utf-8 -*-
"""
YouTubeプラグインパッケージ

サブモジュール:
- youtube_api_plugin.py - YouTube Data API統合
- youtube_live_plugin.py - YouTube Live検出・投稿統合
- youtube_live_classifier.py - Live/Archive分類ロジック
- youtube_live_store.py - キャッシュ/DB管理
- youtube_live_poller.py - ポーリング・遷移検出
- youtube_live_auto_poster.py - イベント処理・投稿判定
"""

__all__ = [
    'YouTubeAPIPlugin',
    'YouTubeLivePlugin',
]
