# -*- coding: utf-8 -*-
"""
YouTube Live キャッシュ管理モジュール

ライブ配信のキャッシュ操作を一元管理：
- キャッシュの登録・更新・削除
- キャッシュの取得・検索
- ファイル永続化
"""

import json
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path

logger = logging.getLogger("AppLogger")

__author__ = "mayuneco(mayunya)"
__copyright__ = "Copyright (C) 2025 mayuneco(mayunya)"
__license__ = "GPLv2"

CACHE_FILE = "data/youtube_live_cache.json"


class YouTubeLiveCacheManager:
    """YouTube Live キャッシュ管理"""

    def __init__(self, cache_file: str = CACHE_FILE):
        """
        初期化

        Args:
            cache_file: キャッシュファイルのパス
        """
        self.cache_file = Path(cache_file)
        self.cache_data: Dict[str, Any] = {}
        self._load_cache()

    def _load_cache(self) -> None:
        """キャッシュファイルから読み込み"""
        try:
            # ディレクトリを作成（なければ）
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)

            if self.cache_file.exists():
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    self.cache_data = json.load(f)
                logger.debug(f"✅ キャッシュを読み込みました: {len(self.cache_data)} 件 ({self.cache_file})")
            else:
                logger.debug(f"ℹ️ キャッシュファイルが存在しません（初回）: {self.cache_file}")
                self.cache_data = {}
        except Exception as e:
            logger.warning(f"⚠️ キャッシュ読み込みエラー: {e}、空の状態で初期化")
            self.cache_data = {}

    def _save_cache(self) -> bool:
        """キャッシュファイルに保存

        Returns:
            bool: 保存成功フラグ
        """
        try:
            # ディレクトリを作成（なければ）
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)

            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache_data, f, indent=2, ensure_ascii=False)
            logger.debug(f"💾 キャッシュを保存しました: {len(self.cache_data)} 件 ({self.cache_file})")
            return True
        except Exception as e:
            logger.error(f"❌ キャッシュ保存エラー: {e}")
            return False

    def add_live_video(self, video_id: str, db_data: Dict[str, Any], api_details: Dict[str, Any]) -> bool:
        """
        ライブ動画をキャッシュに追加

        ⚠️ 重要：upcoming（予約枠）と live（配信中）のみを保存
        archive（アーカイブ）と video（通常動画）は動画用キャッシュに格納すること

        Args:
            video_id: 動画ID
            db_data: DB から取得した情報
            api_details: YouTube API から取得した詳細情報

        Returns:
            bool: 成功フラグ
        """
        try:
            # ステータスを判定
            from plugins.youtube.youtube_api_plugin import YouTubeAPIPlugin
            api_plugin = YouTubeAPIPlugin()
            content_type, live_status, _ = api_plugin._classify_video_core(api_details)

            # ⚠️ upcoming と live のみを Live キャッシュに保存
            if live_status not in ("upcoming", "live"):
                logger.warning(
                    f"⚠️ Live キャッシュに非対応: {video_id} (live_status={live_status})"
                    f"\n   → 動画用キャッシュ (youtube_video_detail_cache.json) に格納してください"
                )
                return False

            if video_id in self.cache_data:
                logger.warning(f"⚠️ キャッシュに既に存在: {video_id}、更新します")
                self.cache_data[video_id]["db_data"] = db_data
                self.cache_data[video_id]["api_details"] = api_details
            else:
                self.cache_data[video_id] = {
                    "video_id": video_id,
                    "db_data": db_data,
                    "api_details": api_details,
                    "status": "live",  # live, ended
                    "live_status": live_status,  # upcoming, live
                    "created_at": self._now_str(),
                    "updated_at": self._now_str(),
                }
                logger.info(f"✅ Live キャッシュに追加: {video_id} (status={live_status})")

            return self._save_cache()
        except Exception as e:
            logger.error(f"❌ Live キャッシュ追加エラー: {video_id} - {e}")
            return False

    def update_live_video(self, video_id: str, api_details: Dict[str, Any]) -> bool:
        """
        ライブ動画のキャッシュを更新（API 詳細情報で上書き）

        Args:
            video_id: 動画ID
            api_details: 最新の YouTube API 詳細情報

        Returns:
            bool: 成功フラグ
        """
        try:
            if video_id not in self.cache_data:
                logger.warning(f"⚠️ キャッシュに存在しません: {video_id}")
                return False

            self.cache_data[video_id]["api_details"] = api_details
            self.cache_data[video_id]["updated_at"] = self._now_str()
            logger.debug(f"🔄 キャッシュを更新: {video_id}")

            return self._save_cache()
        except Exception as e:
            logger.error(f"❌ キャッシュ更新エラー: {video_id} - {e}")
            return False

    def mark_as_ended(self, video_id: str) -> bool:
        """
        ライブを終了状態にマーク

        Args:
            video_id: 動画ID

        Returns:
            bool: 成功フラグ
        """
        try:
            if video_id not in self.cache_data:
                logger.warning(f"⚠️ キャッシュに存在しません: {video_id}")
                return False

            self.cache_data[video_id]["status"] = "ended"
            self.cache_data[video_id]["ended_at"] = self._now_str()
            logger.info(f"✅ ライブ終了をマーク: {video_id}")

            return self._save_cache()
        except Exception as e:
            logger.error(f"❌ ライブ終了マークエラー: {video_id} - {e}")
            return False

    def get_live_video(self, video_id: str) -> Optional[Dict[str, Any]]:
        """
        キャッシュから動画情報を取得

        Args:
            video_id: 動画ID

        Returns:
            Dict: キャッシュエントリ、見つからない場合は None
        """
        return self.cache_data.get(video_id)

    def get_all_live_videos(self) -> List[Dict[str, Any]]:
        """
        すべてのライブ動画キャッシュを取得

        Returns:
            List[Dict]: キャッシュエントリリスト
        """
        return list(self.cache_data.values())

    def get_live_videos_by_status(self, status: str) -> List[Dict[str, Any]]:
        """
        ステータス別にライブ動画キャッシュを取得

        Args:
            status: ステータス（"live" または "ended"）

        Returns:
            List[Dict]: マッチしたエントリリスト
        """
        return [v for v in self.cache_data.values() if v.get("status") == status]

    def has_active_live(self) -> bool:
        """
        アクティブなLIVE または upcoming ビデオがあるか確認

        キャッシュに 'upcoming' または 'live' ステータスのビデオが存在する場合 True

        Returns:
            bool: アクティブなLIVEビデオがある場合 True
        """
        active_statuses = ("live", "upcoming")
        return any(v.get("status") in active_statuses for v in self.cache_data.values())

    def has_completed_live(self) -> bool:
        """
        完了/終了したLIVEビデオがあるか確認

        キャッシュに 'completed' ステータスのビデオが存在する場合 True

        Returns:
            bool: 完了したLIVEビデオがある場合 True
        """
        return any(v.get("status") == "completed" for v in self.cache_data.values())

    def delete_live_video(self, video_id: str) -> bool:
        """
        キャッシュから動画を削除

        Args:
            video_id: 動画ID

        Returns:
            bool: 成功フラグ
        """
        try:
            if video_id not in self.cache_data:
                logger.warning(f"⚠️ キャッシュに存在しません: {video_id}")
                return False

            del self.cache_data[video_id]
            logger.info(f"✅ キャッシュから削除: {video_id}")

            return self._save_cache()
        except Exception as e:
            logger.error(f"❌ キャッシュ削除エラー: {video_id} - {e}")
            return False

    def delete_all_ended(self) -> int:
        """
        すべての終了済みライブをキャッシュから削除

        Returns:
            int: 削除した件数
        """
        try:
            ended_videos = [v for v in self.cache_data.values() if v.get("status") == "ended"]
            deleted_count = 0

            for video in ended_videos:
                video_id = video.get("video_id")
                if self.delete_live_video(video_id):
                    deleted_count += 1

            logger.info(f"✅ 終了済みライブを削除: {deleted_count} 件")
            return deleted_count
        except Exception as e:
            logger.error(f"❌ 終了済みライブ削除エラー: {e}")
            return 0

    def clear_cache(self) -> bool:
        """
        キャッシュをすべてクリア

        Returns:
            bool: 成功フラグ
        """
        try:
            self.cache_data.clear()
            logger.info("🗑️ キャッシュをクリアしました")
            return self._save_cache()
        except Exception as e:
            logger.error(f"❌ キャッシュクリアエラー: {e}")
            return False

    def remove_video(self, video_id: str) -> bool:
        """
        キャッシュから動画を削除（delete_live_video() のエイリアス）

        Args:
            video_id: 動画ID

        Returns:
            bool: 成功フラグ
        """
        return self.delete_live_video(video_id)

    def _now_str(self) -> str:
        """現在時刻を ISO 8601 形式で取得"""
        from datetime import datetime
        return datetime.now().isoformat()


# シングルトン
_cache_manager_instance: Optional[YouTubeLiveCacheManager] = None


def get_youtube_live_cache_manager(cache_file: str = CACHE_FILE) -> YouTubeLiveCacheManager:
    """
    YouTubeLiveCacheManager インスタンスを取得（シングルトン）

    Args:
        cache_file: キャッシュファイルのパス

    Returns:
        YouTubeLiveCacheManager: インスタンス
    """
    global _cache_manager_instance
    if _cache_manager_instance is None:
        _cache_manager_instance = YouTubeLiveCacheManager(cache_file)
    return _cache_manager_instance
