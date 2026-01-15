# -*- coding: utf-8 -*-

"""
Batch Schedule Manager - 複数動画の投稿スケジュール管理

複数の動画に対して、指定した間隔で投稿予定時刻を自動計算・管理します。
"""

from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
import logging
import sqlite3
from pathlib import Path

logger = logging.getLogger("ScheduleManager")

__author__ = "mayuneco(mayunya)"
__copyright__ = "Copyright (C) 2025 mayuneco(mayunya)"
__license__ = "GPLv2"
__version__ = "1.0.0"


class BatchScheduleManager:
    """複数動画の投稿スケジュール管理"""

    # スケジュール間隔の制約（Bluesky API レート制限に対応）
    MIN_INTERVAL_MINUTES = 5
    MAX_INTERVAL_MINUTES = 60

    def __init__(self, db):
        """
        初期化

        Args:
            db: Database インスタンス
        """
        self.db = db
        logger.info(f"🔄 BatchScheduleManager v{__version__} を初期化しました")

    def validate_interval(self, interval: int) -> Tuple[bool, str]:
        """
        投稿間隔の妥当性チェック（5～60分）

        Args:
            interval: 投稿間隔（分単位）

        Returns:
            (True/False, メッセージ) のタプル
        """
        if not isinstance(interval, int):
            return False, f"❌ 間隔は整数で指定してください（入力: {interval}）"

        if interval < self.MIN_INTERVAL_MINUTES:
            return (
                False,
                f"❌ 間隔は {self.MIN_INTERVAL_MINUTES} 分以上である必要があります（入力: {interval} 分）",
            )

        if interval > self.MAX_INTERVAL_MINUTES:
            return (
                False,
                f"❌ 間隔は {self.MAX_INTERVAL_MINUTES} 分以下である必要があります（入力: {interval} 分）",
            )

        return True, f"✅ 間隔 {interval} 分は有効です"

    def calculate_schedule(
        self,
        video_ids: List[str],
        start_time: datetime,
        interval_minutes: int,
    ) -> Dict[str, datetime]:
        """
        複数動画の投稿予定日時を計算

        Args:
            video_ids: 投稿対象の動画ID リスト
            start_time: 最初の投稿予定時刻
            interval_minutes: 投稿間隔（分、5～60）

        Returns:
            {video_id: scheduled_datetime} の辞書

        例:
            calculate_schedule(
                ['id1', 'id2', 'id3'],
                datetime(2026, 1, 7, 14, 0),
                interval_minutes=10
            )
            →
            {
                'id1': 2026-01-07 14:00,
                'id2': 2026-01-07 14:10,
                'id3': 2026-01-07 14:20
            }
        """
        # 間隔の妥当性チェック
        is_valid, msg = self.validate_interval(interval_minutes)
        if not is_valid:
            logger.error(msg)
            return {}

        if not video_ids:
            logger.warning("⚠️  動画ID リストが空です")
            return {}

        schedule = {}
        for i, video_id in enumerate(video_ids):
            scheduled_at = start_time + timedelta(minutes=interval_minutes * i)
            schedule[video_id] = scheduled_at
            logger.debug(
                f"📅 計算: {video_id} → {scheduled_at.strftime('%Y-%m-%d %H:%M:%S')}"
            )

        logger.info(f"✅ スケジュール計算完了: {len(schedule)} 件")
        return schedule

    def apply_schedule(
        self, schedule: Dict[str, datetime], force_overwrite: bool = False
    ) -> Dict[str, bool]:
        """
        計算したスケジュールを DB に適用

        Args:
            schedule: {video_id: scheduled_datetime} の辞書
            force_overwrite: True の場合、既存スケジュールを上書き

        Returns:
            {video_id: 成功/失敗} の辞書
        """
        if not schedule:
            logger.warning("⚠️  適用対象のスケジュールがありません")
            return {}

        results = {}
        for video_id, scheduled_at in schedule.items():
            try:
                scheduled_at_str = scheduled_at.strftime("%Y-%m-%d %H:%M:%S")

                # 既存スケジュール確認
                existing = self.db.get_video(video_id)
                if existing and existing.get("scheduled_at") and not force_overwrite:
                    logger.warning(
                        f"⚠️  {video_id} は既にスケジュール済みです（上書きなし）"
                    )
                    results[video_id] = False
                    continue

                # DB に更新
                self.db.update_selection(
                    video_id, selected=True, scheduled_at=scheduled_at_str
                )
                results[video_id] = True
                logger.info(f"✅ スケジュール保存: {video_id} → {scheduled_at_str}")

            except Exception as e:
                logger.error(f"❌ スケジュール保存失敗 {video_id}: {e}")
                results[video_id] = False

        success_count = sum(1 for v in results.values() if v)
        logger.info(f"📊 スケジュール適用完了: {success_count}/{len(results)} 件")
        return results

    def get_scheduled_videos(self) -> List[Dict]:
        """
        スケジュール済みの投稿予定動画を取得（未投稿のみ）

        Returns:
            スケジュール済み動画のリスト（scheduled_at の昇順）
        """
        try:
            conn = self.db._get_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT * FROM videos
                WHERE selected_for_post = 1
                  AND posted_to_bluesky = 0
                  AND scheduled_at IS NOT NULL
                ORDER BY scheduled_at ASC
            """
            )

            videos = [dict(row) for row in cursor.fetchall()]
            conn.close()

            logger.debug(f"🔍 スケジュール済み動画: {len(videos)} 件")
            return videos

        except Exception as e:
            logger.error(f"❌ スケジュール済み動画の取得に失敗: {e}")
            return []

    def get_next_scheduled_video(self) -> Optional[Dict]:
        """
        次に投稿する動画を取得（scheduled_at <= now の最初のもの）

        Returns:
            次に投稿すべき動画（なければ None）
        """
        try:
            conn = self.db._get_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT * FROM videos
                WHERE selected_for_post = 1
                  AND posted_to_bluesky = 0
                  AND scheduled_at IS NOT NULL
                  AND scheduled_at <= datetime('now')
                ORDER BY scheduled_at ASC
                LIMIT 1
            """
            )

            result = cursor.fetchone()
            conn.close()

            if result:
                video = dict(result)
                logger.info(
                    f"📅 次の投稿対象: {video['video_id']} ({video.get('title', 'N/A')})"
                )
                return video
            else:
                logger.debug("ℹ️  投稿予定時刻に到達した動画はありません")
                return None

        except Exception as e:
            logger.error(f"❌ 次の投稿動画の取得に失敗: {e}")
            return None

    def get_next_schedule_time(self) -> Optional[datetime]:
        """
        次のスケジュール投稿予定時刻を取得

        Returns:
            次の投稿予定時刻（なければ None）
        """
        try:
            scheduled_videos = self.get_scheduled_videos()
            if not scheduled_videos:
                return None

            next_video = scheduled_videos[0]
            next_time_str = next_video.get("scheduled_at")

            if next_time_str:
                next_time = datetime.fromisoformat(next_time_str)
                logger.debug(
                    f"⏱️  次のスケジュール時刻: {next_time.strftime('%Y-%m-%d %H:%M:%S')}"
                )
                return next_time

            return None

        except Exception as e:
            logger.error(f"❌ 次のスケジュール時刻取得に失敗: {e}")
            return None

    def cancel_schedule(self, video_id: str) -> bool:
        """
        指定動画のスケジュールをキャンセル

        Args:
            video_id: キャンセル対象の動画ID

        Returns:
            成功: True、失敗: False
        """
        try:
            self.db.update_selection(video_id, selected=False, scheduled_at=None)
            logger.info(f"✅ スケジュール取消: {video_id}")
            return True

        except Exception as e:
            logger.error(f"❌ スケジュール取消失敗 {video_id}: {e}")
            return False

    def cancel_all_schedule(self) -> int:
        """
        全スケジュール動画をキャンセル

        Returns:
            キャンセルした件数
        """
        try:
            scheduled_videos = self.get_scheduled_videos()
            cancel_count = 0

            for video in scheduled_videos:
                if self.cancel_schedule(video["video_id"]):
                    cancel_count += 1

            logger.info(f"✅ 全スケジュール取消完了: {cancel_count} 件")
            return cancel_count

        except Exception as e:
            logger.error(f"❌ 全スケジュール取消に失敗: {e}")
            return 0

    def get_schedule_stats(self) -> Dict[str, int]:
        """
        スケジュール統計情報を取得

        Returns:
            {
                "total_scheduled": スケジュール済み件数,
                "pending": 待機中件数,
                "overdue": 予定時刻超過件数
            }
        """
        try:
            conn = self.db._get_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # 全スケジュール件数
            cursor.execute(
                """
                SELECT COUNT(*) as cnt FROM videos
                WHERE selected_for_post = 1
                  AND posted_to_bluesky = 0
                  AND scheduled_at IS NOT NULL
            """
            )
            total = cursor.fetchone()["cnt"]

            # 待機中（未来）
            cursor.execute(
                """
                SELECT COUNT(*) as cnt FROM videos
                WHERE selected_for_post = 1
                  AND posted_to_bluesky = 0
                  AND scheduled_at IS NOT NULL
                  AND scheduled_at > datetime('now')
            """
            )
            pending = cursor.fetchone()["cnt"]

            # 超過（過去）
            cursor.execute(
                """
                SELECT COUNT(*) as cnt FROM videos
                WHERE selected_for_post = 1
                  AND posted_to_bluesky = 0
                  AND scheduled_at IS NOT NULL
                  AND scheduled_at <= datetime('now')
            """
            )
            overdue = cursor.fetchone()["cnt"]

            conn.close()

            stats = {"total_scheduled": total, "pending": pending, "overdue": overdue}
            logger.debug(f"📊 スケジュール統計: {stats}")
            return stats

        except Exception as e:
            logger.error(f"❌ スケジュール統計取得に失敗: {e}")
            return {"total_scheduled": 0, "pending": 0, "overdue": 0}
