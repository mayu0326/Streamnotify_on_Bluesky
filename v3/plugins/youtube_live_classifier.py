# -*- coding: utf-8 -*-

"""
YouTubeLive 分類層（Classifier）

YouTube API データから content_type と live_status を純粋に分類する責務
"""

import logging
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger("AppLogger")

__author__ = "mayuneco(mayunya)"
__copyright__ = "Copyright (C) 2025 mayuneco(mayunya)"
__license__ = "GPLv2"


class YouTubeLiveClassifier:
    """
    分類層 - YouTube API データから動画の種別と状態を判定

    【責務】
    - YouTube API 詳細情報 → (content_type, live_status, is_premiere) に分類
    - liveStreamingDetails などの API フィールドを解析
    - pure_video, live_archive などの判定ロジックをカプセル化

    【責務 OUT】
    - API 呼び出し → YouTubeAPIPlugin で実装
    - DB 更新 → YouTubeLiveStore で実装
    - 遷移判定 → YouTubeLivePoller で実装
    - 投稿判定 → YouTubeLiveAutoPoster で実装

    ★ ポイント ★
    - __init__(api_plugin=...) で YouTubeAPIPlugin を依存注入
    - classify() メソッドがエントリポイント
    - api_plugin._classify_video_core() に委譲（既存ロジック再利用）
    """

    def __init__(self, api_plugin=None):
        """
        初期化

        Args:
            api_plugin: YouTubeAPIPlugin インスタンス（分類ロジック取得用）
        """
        self.api_plugin = api_plugin

    def classify(self, details: Dict[str, Any]) -> Tuple[str, Optional[str], bool]:
        """
        YouTube API データから動画を分類

        Args:
            details: YouTube API videos.list の詳細情報

        Returns:
            (content_type, live_status, is_premiere)
              - content_type: "video" | "live" | "archive"
              - live_status: None | "upcoming" | "live" | "completed"
              - is_premiere: bool
        """
        if self.api_plugin is None:
            logger.error("❌ api_plugin が未設定です")
            return "video", None, False

        if not details:
            logger.warning("⚠️ details が空です")
            return "video", None, False

        try:
            # api_plugin の既存分類ロジックを再利用
            content_type, live_status, is_premiere = self.api_plugin._classify_video_core(details)
            return content_type, live_status, is_premiere
        except AttributeError:
            logger.error("❌ api_plugin._classify_video_core() が見つかりません")
            return "video", None, False
        except Exception as e:
            logger.error(f"❌ 分類ロジックエラー: {e}")
            return "video", None, False
