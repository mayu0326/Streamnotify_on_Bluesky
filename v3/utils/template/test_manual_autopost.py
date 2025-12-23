# -*- coding: utf-8 -*-
"""
YouTube Live プラグインの自動投稿ロジックをテスト

既に判定済みの live_status="upcoming" 動画で、
YouTube Live プラグインの _should_autopost_live() が
正しく True を返すかを確認する。
"""

import sys
import os
from pathlib import Path

# パスを追加
sys.path.insert(0, str(Path(__file__).parent))

from plugins.youtube_live_plugin import YouTubeLivePlugin
from config import Config
from database import get_database
from plugin_manager import PluginManager
from logging_config import get_logger
import logging

get_logger()
logger = logging.getLogger("AppLogger")

def test_should_autopost_live():
    """_should_autopost_live() メソッドをテスト"""

    # 設定を読み込み
    config = Config("settings.env")
    db = get_database()

    # YouTube Live プラグインを初期化
    plugin = YouTubeLivePlugin()
    plugin_manager = PluginManager()
    plugin_manager.load_plugin("bluesky_plugin", os.path.join("plugins", "bluesky_plugin.py"))
    plugin_manager.enable_plugin("bluesky_plugin")

    # plugin_manager を注入
    plugin.set_plugin_manager(plugin_manager)

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

    logger.info(f"📋 テスト動画情報:")
    logger.info(f"   video_id: {test_video['video_id']}")
    logger.info(f"   content_type: {test_video['content_type']}")
    logger.info(f"   live_status: {test_video['live_status']}")
    logger.info(f"   posted_to_bluesky: {test_video['posted_to_bluesky']}")

    # _should_autopost_live() をテスト
    logger.info(f"\n🧪 _should_autopost_live() をテスト中...")
    should_post = plugin._should_autopost_live(test_video)

    if should_post:
        logger.info(f"✅ テスト PASSED: 自動投稿対象となります")
        logger.info(f"\n📝 投稿処理をシミュレート:")

        # 実際に投稿してみる
        if plugin.plugin_manager:
            results = plugin.plugin_manager.post_video_with_all_enabled(test_video)
            logger.info(f"   Bluesky プラグイン: {results.get('bluesky_plugin', False)}")

            if any(results.values()):
                logger.info(f"✅ 投稿成功")
                # 投稿済みフラグを立てる
                db.mark_as_posted(test_video["video_id"])
                logger.info(f"✅ 投稿済みフラグを更新しました")
            else:
                logger.error(f"❌ 投稿失敗（すべてのプラグインで失敗）")
        else:
            logger.error(f"❌ plugin_manager が None です")
    else:
        logger.error(f"❌ テスト FAILED: 自動投稿対象になりません")
        logger.info(f"\n📊 設定確認:")
        logger.info(f"   APP_MODE: {config.app_mode}")
        logger.info(f"   YOUTUBE_LIVE_AUTO_POST_MODE: {config.youtube_live_auto_post_mode}")
        logger.info(f"   YOUTUBE_LIVE_AUTO_POST_SCHEDULE: {config.youtube_live_auto_post_schedule}")
        logger.info(f"   YOUTUBE_LIVE_AUTO_POST_LIVE: {config.youtube_live_auto_post_live}")
        logger.info(f"   YOUTUBE_LIVE_AUTO_POST_ARCHIVE: {config.youtube_live_auto_post_archive}")

if __name__ == "__main__":
    test_should_autopost_live()
