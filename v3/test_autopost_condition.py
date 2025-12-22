# -*- coding: utf-8 -*-
"""
YouTube Live プラグインの自動投稿判定ロジックをテスト

_should_autopost_live() の条件判定が正しくはたらくか、
テスト動画の content_type="live", live_status="upcoming" で確認
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from plugins.youtube_live_plugin import YouTubeLivePlugin
from config import Config
from database import get_database
import logging

logging.basicConfig(level=logging.DEBUG, format='%(message)s')
logger = logging.getLogger("AppLogger")

def main():
    """テストを実行"""
    
    # 設定を読み込み
    logger.info("📋 テスト開始: YouTube Live 自動投稿判定ロジック")
    logger.info("=" * 60)
    
    config = Config("settings.env")
    db = get_database()
    
    # YouTube Live プラグインを初期化
    plugin = YouTubeLivePlugin()
    
    # テスト動画を DB から取得
    all_videos = db.get_all_videos()
    test_video = None
    for v in all_videos:
        if v["video_id"] == "TEST_LIVE_20251223":
            test_video = v
            break
    
    if not test_video:
        logger.error("❌ テスト動画が見つかりません: TEST_LIVE_20251223")
        return
    
    # テスト動画情報を表示
    logger.info(f"\n📝 テスト動画情報:")
    logger.info(f"   video_id: {test_video['video_id']}")
    logger.info(f"   title: {test_video['title']}")
    logger.info(f"   content_type: {test_video['content_type']}")
    logger.info(f"   live_status: {test_video['live_status']}")
    logger.info(f"   posted_to_bluesky: {test_video['posted_to_bluesky']}")
    
    # APP_MODE と設定を表示
    logger.info(f"\n⚙️  設定情報:")
    logger.info(f"   operation_mode (APP_MODE): {config.operation_mode}")
    logger.info(f"   youtube_live_autopost_mode: {config.youtube_live_autopost_mode}")
    logger.info(f"   youtube_live_auto_post_schedule: {config.youtube_live_auto_post_schedule}")
    logger.info(f"   youtube_live_auto_post_live: {config.youtube_live_auto_post_live}")
    logger.info(f"   youtube_live_auto_post_archive: {config.youtube_live_auto_post_archive}")
    
    # テストケース
    test_cases = [
        ("live", "upcoming", "should_post", True),   # SCHEDULE フラグでチェック
        ("live", "live", "should_post", True),       # LIVE フラグでチェック
        ("archive", "completed", "should_post", True), # ARCHIVE フラグでチェック
        ("video", None, "should_skip", False),       # 通常動画はスキップ
    ]
    
    logger.info(f"\n🧪 条件判定テスト:")
    logger.info("=" * 60)
    
    for content_type, live_status, expected_desc, expected_result in test_cases:
        logger.info(f"\n▶ テストケース: content_type={content_type}, live_status={live_status}")
        
        result = plugin._should_autopost_live(content_type, live_status, config)
        
        status = "✅ PASS" if result == expected_result else "❌ FAIL"
        logger.info(f"  {status}: 期待={expected_result}, 実際={result}")
    
    # テスト動画の実際の判定結果
    logger.info(f"\n▶ テスト動画の判定:")
    result = plugin._should_autopost_live(
        test_video["content_type"],
        test_video["live_status"],
        config
    )
    
    if result:
        logger.info(f"  ✅ PASS: 自動投稿対象となります")
    else:
        logger.info(f"  ❌ FAIL: 自動投稿対象になりません")
    
    logger.info(f"\n" + "=" * 60)
    logger.info("テスト完了")

if __name__ == "__main__":
    main()
