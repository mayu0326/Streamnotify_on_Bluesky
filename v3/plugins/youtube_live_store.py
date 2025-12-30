# -*- coding: utf-8 -*-

"""
YouTubeLive ストレージ層（DB + キャッシュ統合）

データベース操作とキャッシュ操作を統一インターフェースで提供
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

logger = logging.getLogger("AppLogger")

__author__ = "mayuneco(mayunya)"
__copyright__ = "Copyright (C) 2025 mayuneco(mayunya)"
__license__ = "GPLv2"


class YouTubeLiveStore:
    """
    ストレージ層 - DB とキャッシュの読み書きを提供

    【責務】
    - DB への読み書き（get_video_by_id, update_video_classification など）
    - キャッシュの読み書き（add_live_video_to_cache, get_live_videos_by_status など）
    - 渡されたデータをそのまま保存/取得する（ロジックなし）

    【責務 OUT】
    - 状態遷移の判定 → YouTubeLivePoller で実装
    - 自動投稿するかの判定 → YouTubeLiveAutoPoster で実装
    - 分類ロジック → YouTubeLiveClassifier で実装
    - キャッシュを使うかの判断 → YouTubeLivePoller で実装

    ★ ポイント ★
    - Poller は _get_video_detail_with_cache() でキャッシュ優先フローを内化
    - Store はあくまでデータアクセス層、キャッシュ判断ロジックは持たない
    - Poller が Store メソッドを呼び出す形で、責務が一方向フロー化
    """

    def __init__(self, database=None, cache_manager=None):
        """
        初期化

        Args:
            database: Database インスタンス
            cache_manager: YouTubeLiveCacheManager インスタンス
        """
        self.database = database
        self.cache_manager = cache_manager

    # ==================== DB 操作 ====================

    def get_unclassified_videos(self) -> List[Dict[str, Any]]:
        """
        分類されていない動画を取得（content_type == "video"）

        RSS で登録されたばかりの動画で、まだ LIVE 判定されていないもの

        Returns:
            List[Dict]: 未分類動画リスト
        """
        if self.database is None:
            logger.error("❌ database が未設定です")
            return []

        try:
            videos = self.database.get_videos_by_content_type("video")
            logger.debug(f"📋 未分類動画: {len(videos)}件")
            return videos
        except Exception as e:
            logger.error(f"❌ 未分類動画取得に失敗: {e}")
            return []

    def update_video_classification(
        self,
        video_id: str,
        content_type: str,
        live_status: Optional[str] = None
    ) -> bool:
        """
        動画の分類情報を更新（DB）

        Args:
            video_id: 動画ID
            content_type: コンテンツ種別（"video", "live", "archive"）
            live_status: ライブ配信状態（None, "upcoming", "live", "completed"）

        Returns:
            更新成功フラグ
        """
        if self.database is None:
            logger.error("❌ database が未設定です")
            return False

        try:
            success = self.database.update_video_status(
                video_id=video_id,
                content_type=content_type,
                live_status=live_status
            )
            if success:
                logger.info(
                    f"✅ 分類更新: {video_id} → "
                    f"content_type={content_type}, live_status={live_status}"
                )
            return success
        except Exception as e:
            logger.error(f"❌ 分類更新に失敗: {video_id} - {e}")
            return False

    def update_video_metadata(self, video_id: str, **metadata) -> bool:
        """
        動画メタデータを更新（DB）

        Args:
            video_id: 動画ID
            **metadata: 更新する項目（title, channel_name, thumbnail_url など）

        Returns:
            更新成功フラグ
        """
        if self.database is None:
            logger.error("❌ database が未設定です")
            return False

        try:
            success = self.database.update_video_metadata(video_id, **metadata)
            if success:
                logger.info(f"✅ メタデータ更新: {video_id}")
            return success
        except Exception as e:
            logger.error(f"❌ メタデータ更新に失敗: {video_id} - {e}")
            return False

    def get_video_by_id(self, video_id: str) -> Optional[Dict[str, Any]]:
        """
        動画情報を ID から取得（DB）

        Args:
            video_id: 動画ID

        Returns:
            動画データ辞書、見つからない場合 None
        """
        if self.database is None:
            logger.error("❌ database が未設定です")
            return None

        try:
            all_videos = self.database.get_all_videos()
            for v in all_videos:
                if v.get("video_id") == video_id:
                    return v
            return None
        except Exception as e:
            logger.error(f"❌ 動画取得に失敗: {video_id} - {e}")
            return None

    def get_videos_by_live_status(self, live_status: str) -> List[Dict[str, Any]]:
        """
        ライブ配信状態で動画を取得（DB）

        Args:
            live_status: "upcoming", "live", "completed"

        Returns:
            該当する動画リスト
        """
        if self.database is None:
            logger.error("❌ database が未設定です")
            return []

        try:
            videos = self.database.get_videos_by_live_status(live_status)
            logger.debug(f"📋 live_status={live_status} の動画: {len(videos)}件")
            return videos
        except Exception as e:
            logger.error(f"❌ live_status={live_status} の動画取得に失敗: {e}")
            return []

    def mark_as_posted(self, video_id: str) -> bool:
        """
        動画を投稿済みにマーク（DB）

        Args:
            video_id: 動画ID

        Returns:
            更新成功フラグ
        """
        if self.database is None:
            logger.error("❌ database が未設定です")
            return False

        try:
            success = self.database.mark_as_posted(video_id)
            if success:
                logger.info(f"✅ 投稿済みフラグ更新: {video_id}")
            return success
        except Exception as e:
            logger.error(f"❌ 投稿済みフラグ更新に失敗: {video_id} - {e}")
            return False

    # ==================== キャッシュ操作 ====================

    def add_live_video_to_cache(self, video_id: str, db_data: Dict[str, Any], api_data: Dict[str, Any]) -> bool:
        """
        LIVE 動画をキャッシュに追加

        Args:
            video_id: 動画ID
            db_data: DB から取得したデータ
            api_data: YouTube API から取得したデータ

        Returns:
            追加成功フラグ
        """
        if self.cache_manager is None:
            logger.debug("ℹ️ cache_manager が未設定です（キャッシュ機能をスキップ）")
            return False

        try:
            self.cache_manager.add_live_video(video_id, db_data, api_data)
            logger.debug(f"✅ キャッシュに追加: {video_id}")
            return True
        except Exception as e:
            logger.error(f"❌ キャッシュ追加に失敗: {video_id} - {e}")
            return False

    def update_cache_entry(self, video_id: str, api_data: Dict[str, Any]) -> bool:
        """
        キャッシュエントリを更新（API データ更新）

        Args:
            video_id: 動画ID
            api_data: 最新の YouTube API データ

        Returns:
            更新成功フラグ
        """
        if self.cache_manager is None:
            logger.debug("ℹ️ cache_manager が未設定です")
            return False

        try:
            self.cache_manager.update_live_video(video_id, api_data)
            logger.debug(f"✅ キャッシュ更新: {video_id}")
            return True
        except Exception as e:
            logger.error(f"❌ キャッシュ更新に失敗: {video_id} - {e}")
            return False

    def get_live_videos_by_status(self, status: str) -> List[Dict[str, Any]]:
        """
        キャッシュから LIVE 動画を状態で取得

        Args:
            status: "live" or "ended"

        Returns:
            該当する動画リスト（キャッシュデータ）
        """
        if self.cache_manager is None:
            logger.debug("ℹ️ cache_manager が未設定です")
            return []

        try:
            videos = self.cache_manager.get_live_videos_by_status(status)
            logger.debug(f"📋 キャッシュ: status={status} の動画 {len(videos)}件")
            return videos
        except Exception as e:
            logger.error(f"❌ キャッシュ取得に失敗: {e}")
            return []

    def mark_as_ended_in_cache(self, video_id: str) -> bool:
        """
        キャッシュ内の LIVE 動画を終了状態にマーク

        Args:
            video_id: 動画ID

        Returns:
            更新成功フラグ
        """
        if self.cache_manager is None:
            logger.debug("ℹ️ cache_manager が未設定です")
            return False

        try:
            self.cache_manager.mark_as_ended(video_id)
            logger.debug(f"✅ キャッシュで終了状態にマーク: {video_id}")
            return True
        except Exception as e:
            logger.error(f"❌ キャッシュマーク失敗: {video_id} - {e}")
            return False

    def clear_ended_videos_from_cache(self) -> int:
        """
        キャッシュから期限切れの終了 LIVE を削除

        Returns:
            削除した数
        """
        if self.cache_manager is None:
            logger.debug("ℹ️ cache_manager が未設定です")
            return 0

        try:
            count = self.cache_manager.clear_ended_videos()
            if count > 0:
                logger.info(f"✅ キャッシュから {count}個の終了 LIVE を削除")
            return count
        except Exception as e:
            logger.error(f"❌ キャッシュクリア失敗: {e}")
            return 0
