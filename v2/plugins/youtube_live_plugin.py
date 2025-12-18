# -*- coding: utf-8 -*-
"""
YouTubeLive 検出プラグイン

- YouTube Data API プラグインをサブ依存として利用
- ライブ/アーカイブを判定し、DB に保存する役割に特化
- NotificationPlugin 準拠
- API プラグインのキャッシュ・クォータ管理を継承
"""
import os
import logging
from typing import Dict, Any, List, Optional, Tuple
import requests

from plugin_interface import NotificationPlugin
from database import Database
from plugins.youtube_api_plugin import YouTubeAPIPlugin

logger = logging.getLogger("AppLogger")

API_BASE = "https://www.googleapis.com/youtube/v3"


class YouTubeLivePlugin(NotificationPlugin):
    """ライブ・アーカイブ判定専用プラグイン（API クォータ対応版）"""

    def __init__(self):
        # シングルトンインスタンスを利用
        self.api_plugin = YouTubeAPIPlugin()
        self.api_key = self.api_plugin.api_key
        self.channel_id = self.api_plugin.channel_id
        self.db: Database = self.api_plugin.db
        self.session = requests.Session()

    def is_available(self) -> bool:
        return bool(self.api_key and self.channel_id)

    def get_name(self) -> str:
        return "YouTubeLive 検出プラグイン"

    def get_version(self) -> str:
        return "0.2.0"

    def get_description(self) -> str:
        return "YouTubeライブ/アーカイブ判定を行いDBに格納するプラグイン（クォータ対応）"

    def post_video(self, video: Dict[str, Any]) -> bool:
        """
        ライブ/アーカイブ判定を行い DB に保存

        video: {video_id, title?, channel_name?, published_at?}

        注：API プラグインを共有利用するため、クォータ管理は api_plugin に委譲
        """
        video_id = video.get("video_id") or video.get("id")
        if not video_id:
            logger.error("❌ YouTube Live: video_id が指定されていません")
            return False

        # YouTube ID 形式の検証（Niconico など他形式のスキップ）
        if not self._is_valid_youtube_video_id(video_id):
            logger.debug(f"⏭️ YouTube Live: YouTube 形式ではない video_id をスキップ: {video_id}")
            return True  # エラーではなく「対応不可」として True を返す

        # API プラグインの _fetch_video_detail() を使用
        # キャッシュ・クォータ管理は api_plugin が担当
        details = self.api_plugin._fetch_video_detail(video_id)
        if not details:
            logger.error(f"❌ YouTube Live: 動画詳細取得に失敗しました: {video_id}")
            return False

        content_type, live_status, is_premiere = self._classify_live(details)
        snippet = details.get("snippet", {})
        title = video.get("title") or snippet.get("title", "【ライブ】")
        channel_name = video.get("channel_name") or snippet.get("channelTitle", "")
        published_at = video.get("published_at") or snippet.get("publishedAt", "")
        video_url = video.get("video_url") or f"https://www.youtube.com/watch?v={video_id}"
        thumbnail_url = snippet.get("thumbnails", {}).get("high", {}).get("url", "")

        return self.db.insert_video(
            video_id=video_id,
            title=title,
            video_url=video_url,
            published_at=published_at,
            channel_name=channel_name,
            thumbnail_url=thumbnail_url,
            content_type=content_type,
            live_status=live_status,
            is_premiere=is_premiere,
        )

    # --- ID 検証 ---
    def _is_valid_youtube_video_id(self, video_id: str) -> bool:
        """
        YouTube 動画ID 形式の検証

        YouTube 動画ID は 11 文字の英数字（A-Z, a-z, 0-9, -, _）
        例: dQw4w9WgXcQ

        Niconico ID（sm45414087）など他形式は False を返す

        Args:
            video_id: 検証対象の ID

        Returns:
            True: YouTube 形式, False: 他の形式（Niconico など）
        """
        import re
        # YouTube 動画ID: 11 文字、A-Za-z0-9-_
        if re.match(r'^[A-Za-z0-9_-]{11}$', video_id):
            return True
        return False

    # --- ライブ検出ユーティリティ ---
    def sync_live_events(self) -> None:
        """
        ライブ/アーカイブ一覧を取得しDBへ反映（search.list = 100ユニット）

        注意：search.list は非常に高コスト（100ユニット/回）
        本番運用ではキャッシュやスケジューリングの検討が必要
        """
        live_ids = self._fetch_live_video_ids(event_type="live")
        archive_ids = self._fetch_live_video_ids(event_type="completed")

        for vid in live_ids:
            self.post_video({"video_id": vid})
        for vid in archive_ids:
            self.post_video({"video_id": vid})

    def _fetch_live_video_ids(self, event_type: str) -> List[str]:
        """
        ライブイベント一覧を検索（search.list = 100ユニット）

        注：api_plugin のクォータ管理を迂回するため、ここで直接呼び出し
        本来は api_plugin._get() を使用して管理下に置くべき
        """
        params = {
            "part": "id",
            "channelId": self.channel_id,
            "eventType": event_type,
            "type": "video",
            "order": "date",
            "maxResults": 10,
            "key": self.api_key,
        }
        try:
            logger.debug(f"🔍 ライブ一覧検索: {event_type} (search.list = 100ユニット)")
            resp = self.session.get(f"{API_BASE}/search", params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            items = data.get("items", []) if data else []
            video_ids = [item.get("id", {}).get("videoId") for item in items if item.get("id", {}).get("videoId")]
            logger.info(f"✅ ライブ一覧取得成功: {len(video_ids)} 件 ({event_type})")
            return video_ids
        except requests.exceptions.Timeout:
            logger.warning(f"⏱️ タイムアウト: ライブ一覧取得 ({event_type})")
            return []
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ ライブ一覧取得エラー ({event_type}): {e}")
            return []

    def _classify_live(self, details: Dict[str, Any]) -> Tuple[str, Optional[str], bool]:
        """
        ライブ/アーカイブを判別（YouTubeAPIプラグインの詳細版と同じロジック）

        Returns:
            (content_type, live_status, is_premiere)
        """
        snippet = details.get("snippet", {})
        status = details.get("status", {})
        live = details.get("liveStreamingDetails", {})

        broadcast_type = snippet.get("liveBroadcastContent", "none")

        if broadcast_type == "none":
            return "video", None, False

        is_premiere = False

        if live:
            # プレミア公開判定
            if status.get("uploadStatus") == "processed" and broadcast_type in ("live", "upcoming"):
                is_premiere = True

            # ライブの時間的状態
            if live.get("actualEndTime"):
                return "archive", "completed", is_premiere
            elif live.get("actualStartTime"):
                return "live", "live", is_premiere
            elif live.get("scheduledStartTime"):
                return "live", "upcoming", is_premiere

        if broadcast_type == "live":
            return "live", "live", is_premiere
        elif broadcast_type == "upcoming":
            return "live", "upcoming", is_premiere

        return "video", None, False


def get_plugin():
    """PluginManager から取得するためのヘルパー"""
    return YouTubeLivePlugin()
