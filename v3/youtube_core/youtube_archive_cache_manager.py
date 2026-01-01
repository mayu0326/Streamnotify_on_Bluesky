# -*- coding: utf-8 -*-
"""
YouTube アーカイブキャッシュ管理

配信終了 → アーカイブ化の検知・管理用キャッシュ

【用途】
- ライブ配信が終了してアーカイブになった時を検知
- アーカイブ化通知投稿の対象をリストアップ
- 投稿済みのアーカイブを記録（重複投稿防止）
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger("AppLogger")

__author__ = "mayuneco(mayunya)"
__copyright__ = "Copyright (C) 2025 mayuneco(mayunya)"
__license__ = "GPLv2"

ARCHIVE_CACHE_FILE = "data/youtube_archive_cache.json"


class YouTubeArchiveCacheManager:
    """YouTube アーカイブキャッシュを管理"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """初期化"""
        if self._initialized:
            return

        self.cache_file = Path(ARCHIVE_CACHE_FILE)
        self.archive_videos: Dict[str, Dict[str, Any]] = {}
        self._load_cache()
        self._initialized = True

    def _load_cache(self) -> None:
        """キャッシュをファイルから読み込む"""
        try:
            # ディレクトリを作成
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)

            if self.cache_file.exists():
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.archive_videos = data.get('archive_videos', {})
                logger.debug(f"📂 アーカイブキャッシュ読み込み: {len(self.archive_videos)} 件")
            else:
                self.archive_videos = {}
                logger.debug("📂 アーカイブキャッシュが存在しません（新規作成）")

        except json.JSONDecodeError as e:
            logger.error(f"❌ アーカイブキャッシュ JSON 解析エラー: {e}")
            self.archive_videos = {}
        except Exception as e:
            logger.error(f"❌ アーカイブキャッシュ読み込みエラー: {e}")
            self.archive_videos = {}

    def _save_cache(self) -> bool:
        """キャッシュをファイルに保存"""
        try:
            # ディレクトリを作成
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)

            data = {
                'archive_videos': self.archive_videos,
                'last_updated': datetime.now().isoformat()
            }

            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            logger.debug(f"✅ アーカイブキャッシュ保存: {len(self.archive_videos)} 件")
            return True

        except Exception as e:
            logger.error(f"❌ アーカイブキャッシュ保存エラー: {e}")
            return False

    def add_archive_video(self, video_id: str, db_data: Dict[str, Any], api_details: Dict[str, Any]) -> bool:
        """
        アーカイブ動画をキャッシュに追加

        Args:
            video_id: 動画ID
            db_data: DB 登録用データ（title, channel_name など）
            api_details: YouTube API から取得した詳細情報

        Returns:
            bool: 追加成功フラグ
        """
        try:
            # API から分類情報を取得して検証
            from plugins.youtube_api_plugin import YouTubeAPIPlugin
            api_plugin = YouTubeAPIPlugin()
            content_type, live_status, _ = api_plugin._classify_video_core(api_details)

            # アーカイブでない場合は拒否
            if content_type != "archive":
                logger.warning(f"⚠️ アーカイブキャッシュ追加拒否: content_type は archive である必要があります（{video_id} → {content_type}）")
                return False

            # ★ 詳細な配信時間情報を抽出
            live_details = YouTubeAPIPlugin.extract_live_streaming_details(api_details)

            # ★ UTC → JST 変換
            scheduled_start_jst = self._convert_utc_to_jst(live_details.get("scheduled_start_time")) if live_details.get("scheduled_start_time") else None
            scheduled_end_jst = self._convert_utc_to_jst(live_details.get("scheduled_end_time")) if live_details.get("scheduled_end_time") else None
            actual_start_jst = self._convert_utc_to_jst(live_details.get("actual_start_time")) if live_details.get("actual_start_time") else None
            actual_end_jst = self._convert_utc_to_jst(live_details.get("actual_end_time")) if live_details.get("actual_end_time") else None

            # キャッシュエントリを作成（JST で保存）
            cache_entry = {
                "video_id": video_id,
                "db_data": db_data,
                "api_details": api_details,
                "added_at": datetime.now().isoformat(),
                "posted": False,
                # ★ 配信時間情報を JST で保存
                "scheduled_start_time": scheduled_start_jst,
                "scheduled_end_time": scheduled_end_jst,
                "actual_start_time": actual_start_jst,
                "actual_end_time": actual_end_jst,
            }

            self.archive_videos[video_id] = cache_entry
            logger.info(f"✅ アーカイブキャッシュに追加: {video_id}")
            logger.debug(f"   配信時間 (JST): {actual_start_jst} → {actual_end_jst}")

            # 即座に保存
            self._save_cache()
            return True

        except Exception as e:
            logger.error(f"❌ アーカイブキャッシュ追加エラー: {video_id} - {e}")
            return False

    def get_archive_video(self, video_id: str) -> Optional[Dict[str, Any]]:
        """
        アーカイブ動画をキャッシュから取得

        Args:
            video_id: 動画ID

        Returns:
            Dict: キャッシュエントリ、なければ None
        """
        return self.archive_videos.get(video_id)

    def get_unposted_archives(self) -> List[Dict[str, Any]]:
        """
        未投稿のアーカイブ動画をリストアップ

        Returns:
            List[Dict]: 未投稿のアーカイブエントリリスト
        """
        return [
            entry for entry in self.archive_videos.values()
            if not entry.get("posted", False)
        ]

    def mark_as_posted(self, video_id: str) -> bool:
        """
        アーカイブ動画を投稿済みにマーク

        Args:
            video_id: 動画ID

        Returns:
            bool: 更新成功フラグ
        """
        if video_id not in self.archive_videos:
            logger.warning(f"⚠️ アーカイブキャッシュに見つかりません: {video_id}")
            return False

        try:
            self.archive_videos[video_id]["posted"] = True
            self.archive_videos[video_id]["posted_at"] = datetime.now().isoformat()
            self._save_cache()
            logger.info(f"✅ アーカイブ投稿済みにマーク: {video_id}")
            return True

        except Exception as e:
            logger.error(f"❌ アーカイブ投稿済みマーク失敗: {video_id} - {e}")
            return False

    def delete_archive_video(self, video_id: str) -> bool:
        """
        アーカイブ動画をキャッシュから削除

        Args:
            video_id: 動画ID

        Returns:
            bool: 削除成功フラグ
        """
        if video_id not in self.archive_videos:
            logger.debug(f"ℹ️ アーカイブキャッシュに見つかりません: {video_id}")
            return False

        try:
            del self.archive_videos[video_id]
            self._save_cache()
            logger.info(f"✅ アーカイブキャッシュから削除: {video_id}")
            return True

        except Exception as e:
            logger.error(f"❌ アーカイブキャッシュ削除失敗: {video_id} - {e}")
            return False

    def clear_old_entries(self, days: int = 30) -> int:
        """
        30日以上前のアーカイブエントリをクリア

        Args:
            days: 保持する日数

        Returns:
            int: 削除したエントリ数
        """
        from datetime import datetime, timedelta

        try:
            cutoff = datetime.now() - timedelta(days=days)
            deleted_count = 0

            video_ids_to_delete = [
                vid for vid, entry in self.archive_videos.items()
                if entry.get("posted", False)  # 投稿済みのみ削除
                and datetime.fromisoformat(entry.get("posted_at", entry.get("added_at", ""))) < cutoff
            ]

            for video_id in video_ids_to_delete:
                del self.archive_videos[video_id]
                deleted_count += 1

            if deleted_count > 0:
                self._save_cache()
                logger.info(f"✅ {deleted_count} 件の古いアーカイブエントリをクリア")

            return deleted_count

        except Exception as e:
            logger.error(f"❌ アーカイブエントリクリア失敗: {e}")
            return 0

    def get_all_archives(self) -> List[Dict[str, Any]]:
        """
        すべてのアーカイブ動画を取得

        Returns:
            List[Dict]: アーカイブエントリリスト
        """
        return list(self.archive_videos.values())

    def _convert_utc_to_jst(self, utc_datetime_str: str) -> Optional[str]:
        """
        UTC ISO 8601 形式を JST に変換

        Args:
            utc_datetime_str: UTC 日時文字列（例: "2025-12-28T18:00:00Z"）

        Returns:
            JST 日時文字列（例: "2025-12-29 03:00:00"）、失敗時は None
        """
        try:
            if not utc_datetime_str:
                return None

            from datetime import datetime, timezone, timedelta
            utc_time = datetime.fromisoformat(utc_datetime_str.replace('Z', '+00:00'))
            jst_time = utc_time.astimezone(timezone(timedelta(hours=9))).replace(tzinfo=None)
            return jst_time.strftime('%Y-%m-%d %H:%M:%S')
        except Exception as e:
            logger.warning(f"⚠️ UTC→JST 変換失敗: {utc_datetime_str} - {e}")
            return utc_datetime_str


def get_youtube_archive_cache_manager() -> YouTubeArchiveCacheManager:
    """アーカイブキャッシュマネージャーのインスタンスを取得"""
    return YouTubeArchiveCacheManager()
