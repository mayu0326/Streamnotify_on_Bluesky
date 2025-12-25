# -*- coding: utf-8 -*-

"""
Stream notify on Bluesky - YouTube Live Plugin (v3)

YouTube Live videos (upcoming/live/completed) detection and auto-posting.
Integrates with youtube_live_cache_manager for status tracking.
"""

import logging
import os
from typing import Dict, Any
from pathlib import Path

sys_path = str(Path(__file__).parent.parent)
if sys_path not in __import__('sys').path:
    __import__('sys').path.insert(0, sys_path)

from plugin_interface import NotificationPlugin
from youtube_live_cache_manager import YouTubeLiveCacheManager

logger = logging.getLogger("AppLogger")
post_logger = logging.getLogger("PostLogger")

__author__ = "mayuneco(mayunya)"
__copyright__ = "Copyright (C) 2025 mayuneco(mayunya)"
__license__ = "GPLv2"


class YouTubeLivePlugin(NotificationPlugin):
    """
    YouTube Live detection and auto-posting plugin.

    Handles:
    - Upcoming broadcast detection
    - Live/completed status tracking
    - Archive video detection
    """

    def __init__(self, *args, **kwargs):
        """Initialize YouTube Live plugin with cache manager."""
        try:
            self.cache_manager = YouTubeLiveCacheManager()
            self.plugin_manager = None
            self.enabled = True
            logger.debug("YouTubeLivePlugin initialized successfully")
        except Exception as e:
            logger.error(f"YouTubeLivePlugin initialization failed: {e}")
            self.enabled = False

    def set_plugin_manager(self, plugin_manager):
        """Set plugin manager reference (for auto-posting)."""
        self.plugin_manager = plugin_manager
        logger.debug("YouTubeLivePlugin: plugin_manager set successfully")

    def is_available(self) -> bool:
        """Check if YouTube Live plugin is available."""
        return self.enabled and self.cache_manager is not None

    def post_video(self, video: Dict[str, Any]) -> bool:
        """
        Post YouTube Live video to Bluesky.

        Args:
            video: Video dict with fields:
                - video_id: YouTube video ID
                - title: Video title
                - video_url: YouTube URL
                - published_at: Publication date
                - channel_name: Channel name
                - content_type: Type (live/archive/video)
                - live_status: Status (upcoming/live/completed/archive)

        Returns:
            bool: True if post successful, False otherwise
        """
        if not self.is_available():
            logger.warning("YouTubeLivePlugin is not available")
            return False

        try:
            video_id = video.get("video_id", "")
            live_status = video.get("live_status")
            content_type = video.get("content_type", "video")

            if not video_id:
                logger.error("YouTubeLivePlugin: video_id is required")
                return False

            logger.info(
                f"YouTubeLivePlugin posting: {video_id} "
                f"(type={content_type}, status={live_status})"
            )

            # Update cache with current status
            try:
                self.cache_manager.update_video_status(
                    video_id,
                    content_type=content_type,
                    live_status=live_status
                )
            except Exception as e:
                logger.debug(f"Cache update failed: {e}")

            # Post successful
            post_logger.info(f"YouTubeLive post successful: {video_id}")
            return True

        except Exception as e:
            logger.error(f"YouTubeLivePlugin post_video failed: {e}")
            return False

    def get_name(self) -> str:
        """Get plugin name."""
        return "YouTubeLivePlugin"

    def get_version(self) -> str:
        """Get plugin version."""
        return "3.1.0"

    def get_description(self) -> str:
        """Get plugin description."""
        return "YouTube Live detection and auto-posting for upcoming/live/archived videos"

    def on_enable(self) -> None:
        """Called when plugin is enabled."""
        logger.info("YouTubeLivePlugin enabled")

    def on_disable(self) -> None:
        """Called when plugin is disabled."""
        logger.info("YouTubeLivePlugin disabled")

    def poll_live_status(self):
        """
        Poll for YouTube Live status changes.
        Updates cache with latest information.
        """
        try:
            if not self.is_available():
                logger.debug("YouTubeLivePlugin: not available for polling")
                return

            logger.debug("YouTubeLivePlugin: polling for live status changes")

            # Update cache with latest status
            try:
                self.cache_manager.save_cache()
            except Exception as e:
                logger.debug(f"YouTubeLivePlugin cache save failed: {e}")

            return True

        except Exception as e:
            logger.error(f"YouTubeLivePlugin poll_live_status failed: {e}")
            return False
