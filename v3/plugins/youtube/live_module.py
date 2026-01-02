# -*- coding: utf-8 -*-

"""
YouTube Live モジュール

YouTubeVideoClassifier の結果に基づいて、
- Schedule（スケジュール）
- Live（配信中）
- Completed（配信終了）
- Archive（ライブアーカイブ）

の4つの状態を一元管理し、状態遷移と自動投稿を処理する。

設計方針：
- キャッシュは最小化（状態遷移の検知と投稿判定が主目的）
- DB スキーマは既存の content_type / live_status を再利用
- PluginManager 経由で Bluesky 投稿を実行
- 戻り値は処理件数（int）で統一して、テスト・デバッグを容易化
"""

import logging
import os
from typing import Dict, Any, Optional
from datetime import datetime

from database import Database
from config import get_config

logger = logging.getLogger("AppLogger")

# 動画種別定義（YouTubeVideoClassifier と統一）
VIDEO_TYPE_SCHEDULE = "schedule"
VIDEO_TYPE_LIVE = "live"
VIDEO_TYPE_COMPLETED = "completed"
VIDEO_TYPE_ARCHIVE = "archive"

# Live ステータス定義
LIVE_STATUS_UPCOMING = "upcoming"
LIVE_STATUS_LIVE = "live"
LIVE_STATUS_COMPLETED = "completed"


class LiveModule:
    """
    YouTube Live 管理モジュール

    YouTubeVideoClassifier の分類結果を受け取り、
    DB 登録、状態遷移検知、自動投稿を一元処理する。
    """

    def __init__(self, db: Optional[Database] = None, plugin_manager=None):
        """
        初期化

        Args:
            db: Database インスタンス（Noneの場合は自動取得）
            plugin_manager: PluginManager インスタンス（自動投稿用）
        """
        self.db = db or self._get_db()
        self.plugin_manager = plugin_manager
        self.config = get_config("settings.env")

    def _get_db(self) -> Database:
        """Database シングルトンを取得"""
        from database import get_database
        return get_database()

    def register_from_classified(self, result: Dict[str, Any]) -> int:
        """
        YouTubeVideoClassifier の分類結果を受け取り、DB に登録

        Args:
            result: YouTubeVideoClassifier.classify_video() の戻り値
                   {
                       "success": bool,
                       "video_id": str,
                       "type": str,  # "schedule", "live", "completed", "archive"
                       "title": str,
                       "description": str,
                       "thumbnail_url": str,
                       "published_at": str,
                       "live_status": str or None,
                       ...
                   }

        Returns:
            int: 登録・更新した件数（0 = 何もしなかった、1 = 登録・更新した）
        """
        if not result.get("success"):
            logger.debug(f"⏭️  分類失敗（登録スキップ）: {result.get('error')}")
            return 0

        video_id = result.get("video_id")
        video_type = result.get("type")

        # Live 関連以外はスキップ
        if video_type not in [VIDEO_TYPE_SCHEDULE, VIDEO_TYPE_LIVE, VIDEO_TYPE_COMPLETED, VIDEO_TYPE_ARCHIVE]:
            logger.debug(f"⏭️  非Live動画（登録スキップ）: {video_type}")
            return 0

        # 基本情報を抽出
        title = result.get("title", "【ライブ】")
        channel_name = result.get("channel_name", "")
        published_at = result.get("published_at", "")
        thumbnail_url = result.get("thumbnail_url", "")
        is_premiere = result.get("is_premiere", False)

        # video_url を構築
        video_url = f"https://www.youtube.com/watch?v={video_id}"

        # 動画種別ごとの live_status マッピング
        # （YouTubeVideoClassifier の分類結果をそのまま使用）
        live_status_map = {
            VIDEO_TYPE_SCHEDULE: LIVE_STATUS_UPCOMING,
            VIDEO_TYPE_LIVE: LIVE_STATUS_LIVE,
            VIDEO_TYPE_COMPLETED: LIVE_STATUS_COMPLETED,
            VIDEO_TYPE_ARCHIVE: None  # アーカイブは live_status=None
        }
        live_status = live_status_map.get(video_type)

        # DB に登録
        logger.info(f"📝 Live動画を登録します: {title} (type={video_type}, status={live_status})")

        try:
            success = self.db.insert_video(
                video_id=video_id,
                title=title,
                video_url=video_url,
                published_at=published_at,
                channel_name=channel_name,
                thumbnail_url=thumbnail_url,
                content_type=video_type,
                live_status=live_status,
                is_premiere=is_premiere,
                source="youtube",
                skip_dedup=True  # LIVE は重複排除をスキップ（複数登録可）
            )

            if success:
                logger.info(f"✅ Live動画を登録しました: {title}")
                return 1
            else:
                logger.debug(f"⏭️  既に登録済み（スキップ）: {video_id}")
                return 0

        except Exception as e:
            logger.error(f"❌ Live動画の登録に失敗しました: {video_id} - {e}")
            return 0

    def poll_lives(self) -> int:
        """
        登録済みの Live 動画をポーリング

        処理内容：
        1. DB から Live 関連の全動画を取得
        2. 各動画の現在の状態を分類器で確認
        3. 状態遷移を検知して、以下の3つのイベントを検出・処理
           - 配信開始イベント: schedule/video → live
           - 配信終了イベント: live → completed
           - アーカイブ公開イベント: completed → archive
        4. 各イベントごとに DB 更新と自動投稿を実行

        Returns:
            int: 処理した件数（イベントを検知して処理した動画数）
        """
        try:
            # DB から Live 関連の全動画を取得
            # （content_type が "schedule", "live", "completed", "archive" のいずれか）
            all_videos = self.db.get_all_videos()
            live_videos = [
                v for v in all_videos
                if v.get("content_type") in [VIDEO_TYPE_SCHEDULE, VIDEO_TYPE_LIVE, VIDEO_TYPE_COMPLETED, VIDEO_TYPE_ARCHIVE]
            ]

            if not live_videos:
                logger.debug("ℹ️  ポーリング対象の Live 動画がありません")
                return 0

            logger.info(f"🔄 {len(live_videos)} 件の Live 動画をポーリング中...")

            processed_count = 0
            from youtube_core.youtube_video_classifier import get_video_classifier

            classifier = get_video_classifier(api_key=os.getenv("YOUTUBE_API_KEY"))

            for video in live_videos:
                video_id = video.get("video_id")
                if not video_id:
                    continue

                # 非 YouTube ID（Niconico など）をスキップ
                if not self._is_youtube_video_id(video_id):
                    continue

                # YouTube API で最新の状態を確認
                try:
                    result = classifier.classify_video(video_id)
                except Exception as e:
                    logger.debug(f"⏭️  分類エラー（スキップ）: {video_id} - {e}")
                    continue

                if not result.get("success"):
                    logger.debug(f"⏭️  分類失敗（スキップ）: {video_id}")
                    continue

                current_type = result.get("type")
                current_live_status = result.get("live_status")
                old_type = video.get("content_type")
                old_live_status = video.get("live_status")

                # ★ イベント検知: 複数の状態遷移パターンをチェック
                event_handled = False

                # イベント1: 配信開始 (schedule/video → live)
                if old_type in [VIDEO_TYPE_SCHEDULE, "video"] and current_type == VIDEO_TYPE_LIVE:
                    logger.info(f"🎬 【配信開始イベント】 {video_id}")
                    logger.info(f"   旧: type={old_type}, status={old_live_status}")
                    logger.info(f"   新: type={current_type}, status={current_live_status}")
                    self._on_live_started(video, result)
                    processed_count += 1
                    event_handled = True

                # イベント2: 配信終了 (live → completed または live → archive)
                # ★ 修正: completed だけでなく archive も含める (API のタイミングで completed を経由しないことあり)
                elif old_type == VIDEO_TYPE_LIVE and current_type in [VIDEO_TYPE_COMPLETED, VIDEO_TYPE_ARCHIVE]:
                    logger.info(f"🎬 【配信終了イベント】 {video_id}")
                    logger.info(f"   旧: type={old_type}, status={old_live_status}")
                    logger.info(f"   新: type={current_type}, status={current_live_status}")
                    self._on_live_ended(video, result, current_type, current_live_status)
                    processed_count += 1
                    event_handled = True

                # イベント3: アーカイブ公開 (completed → archive)
                # ★ 注意: _on_live_ended で既に archive に遷移した場合は処理済み
                elif old_type == VIDEO_TYPE_COMPLETED and current_type == VIDEO_TYPE_ARCHIVE:
                    logger.info(f"🎬 【アーカイブ公開イベント】 {video_id}")
                    logger.info(f"   旧: type={old_type}, status={old_live_status}")
                    logger.info(f"   新: type={current_type}, status={current_live_status}")
                    self._on_archive_available(video, result)
                    processed_count += 1
                    event_handled = True

                # イベント以外の状態遷移（表記揃えなど）
                if not event_handled and (current_type != old_type or current_live_status != old_live_status):
                    logger.info(f"📝 状態更新（イベントなし）: {video_id}")
                    logger.info(f"   旧: type={old_type}, status={old_live_status}")
                    logger.info(f"   新: type={current_type}, status={current_live_status}")
                    # DB を更新するが、自動投稿はしない
                    self.db.update_video_status(video_id, current_type, current_live_status)

            logger.info(f"✅ Live ポーリング完了: {processed_count} 件のイベントを処理しました")
            return processed_count

        except Exception as e:
            logger.error(f"❌ Live ポーリング中にエラーが発生しました: {e}")
            return 0

    def _should_autopost_live(self, content_type: str, live_status: Optional[str]) -> bool:
        """
        Live 動画の自動投稿判定

        APP_MODE に応じて自動的に判定ロジックを切り替える：
        - AUTOPOST モード: YOUTUBE_LIVE_AUTO_POST_MODE で判定
        - SELFPOST/その他: YOUTUBE_LIVE_AUTO_POST_SCHEDULE/LIVE/ARCHIVE フラグで判定

        Args:
            content_type: コンテンツ種別（"schedule", "live", "completed", "archive"）
            live_status: ライブステータス（"upcoming", "live", "completed", None）

        Returns:
            bool: 投稿すべき場合 True、投稿スキップすべき場合 False
        """
        try:
            # APP_MODE に基づいて使用するフラグを決定
            if self.config.operation_mode == "autopost":
                # AUTOPOST モード: 統合モード値を使用
                mode = self.config.youtube_live_autopost_mode
                logger.debug(f"🔍 AUTOPOST モード: mode={mode}")

                # テーブル仕様 v1.0 セクション 4.2 参照
                if mode == "off":
                    return False
                elif mode == "all":
                    return content_type in [VIDEO_TYPE_SCHEDULE, VIDEO_TYPE_LIVE, VIDEO_TYPE_COMPLETED, VIDEO_TYPE_ARCHIVE]
                elif mode == "schedule":
                    return content_type == VIDEO_TYPE_SCHEDULE and live_status == LIVE_STATUS_UPCOMING
                elif mode == "live":
                    return content_type == VIDEO_TYPE_LIVE and live_status in (LIVE_STATUS_LIVE, LIVE_STATUS_COMPLETED)
                elif mode == "archive":
                    return content_type == VIDEO_TYPE_ARCHIVE
                else:
                    logger.warning(f"⚠️  無効な mode: {mode}")
                    return False
            else:
                # SELFPOST/DRY_RUN/COLLECT モード: 個別フラグで判定
                if content_type == VIDEO_TYPE_SCHEDULE:
                    return self.config.youtube_live_auto_post_schedule
                elif content_type == VIDEO_TYPE_LIVE:
                    return self.config.youtube_live_auto_post_live
                elif content_type == VIDEO_TYPE_COMPLETED or content_type == VIDEO_TYPE_ARCHIVE:
                    return self.config.youtube_live_auto_post_archive
                else:
                    return False

        except AttributeError as e:
            logger.warning(f"⚠️  自動投稿フラグが未設定（デフォルト=False）: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ 自動投稿判定エラー: {e}")
            return False

    def _is_youtube_video_id(self, video_id: str) -> bool:
        """
        YouTube 動画 ID 形式の検証

        YouTube 動画 ID は 11 文字の英数字（A-Z, a-z, 0-9, -, _）
        Niconico ID など他形式は False を返す

        Args:
            video_id: 検証対象の ID

        Returns:
            True: YouTube 形式, False: 他の形式
        """
        import re
        return bool(re.match(r"^[A-Za-z0-9_-]{11}$", video_id))

    def _on_live_started(self, video: Dict[str, Any], result: Dict[str, Any]) -> None:
        """
        配信開始イベントハンドラ

        schedule/video → live への状態遷移を処理

        Args:
            video: DB から取得した既存の動画情報
            result: YouTubeVideoClassifier.classify_video() の戻り値
        """
        video_id = video.get("video_id")
        title = video.get("title", "【ライブ配信開始】")

        try:
            # ★ DB を更新
            self.db.update_video_status(video_id, VIDEO_TYPE_LIVE, LIVE_STATUS_LIVE)
            logger.info(f"✅ DB更新: {video_id} → type=live, status=live")

            # ★ 自動投稿判定
            should_post = self._should_autopost_live(VIDEO_TYPE_LIVE, LIVE_STATUS_LIVE)
            if not should_post:
                logger.debug(f"⏭️  配信開始の自動投稿スキップ（設定により）: {video_id}")
                return

            # ★ 自動投稿: classification_type を "live" にセットして投稿
            logger.info(f"📤 配信開始イベントを自動投稿します: {title}")
            video_copy = dict(video)
            video_copy["classification_type"] = "live"  # テンプレート selection に使用
            video_copy["content_type"] = VIDEO_TYPE_LIVE
            video_copy["live_status"] = LIVE_STATUS_LIVE

            if self.plugin_manager:
                try:
                    results = self.plugin_manager.post_video_with_all_enabled(video_copy)
                    if any(results.values()):
                        self.db.mark_as_posted(video_id)
                        logger.info(f"✅ 配信開始イベントの自動投稿に成功しました: {video_id}")
                    else:
                        logger.warning(f"⚠️  配信開始イベントの自動投稿に失敗しました: {video_id}")
                except Exception as e:
                    logger.error(f"❌ 配信開始イベント投稿エラー: {video_id} - {e}")
            else:
                logger.warning(f"⚠️  plugin_manager が初期化されていません（投稿スキップ）")

        except Exception as e:
            logger.error(f"❌ 配信開始イベントハンドラエラー: {video_id} - {e}")

    def _on_live_ended(self, video: Dict[str, Any], result: Dict[str, Any],
                       current_type: str = None, current_live_status: Optional[str] = None) -> None:
        """
        配信終了イベントハンドラ

        live → completed または live → archive への状態遷移を処理

        Args:
            video: DB から取得した既存の動画情報
            result: YouTubeVideoClassifier.classify_video() の戻り値
            current_type: 現在の type (poll_lives から渡される、デフォルトは VIDEO_TYPE_COMPLETED)
            current_live_status: 現在の live_status (poll_lives から渡される)

        処理フロー:
        1. DB を current_type に更新
        2. classification_type を "completed" にセットして自動投稿
        3. もし current_type == "archive" なら、_on_archive_available も続けて呼ぶ
        """
        # 互換性のため、current_type が指定されていなければ VIDEO_TYPE_COMPLETED を使用
        if current_type is None:
            current_type = VIDEO_TYPE_COMPLETED
        if current_live_status is None:
            current_live_status = LIVE_STATUS_COMPLETED

        video_id = video.get("video_id")
        title = video.get("title", "【ライブ配信終了】")

        try:
            # ★ DB を更新
            self.db.update_video_status(video_id, current_type, current_live_status)
            logger.info(f"✅ DB更新: {video_id} → type={current_type}, status={current_live_status}")

            # ★ 自動投稿判定
            should_post = self._should_autopost_live(current_type, current_live_status)
            if not should_post:
                logger.debug(f"⏭️  配信終了の自動投稿スキップ（設定により）: {video_id}")
                # もし current_type == archive なら、ここでも _on_archive_available は呼ばない
                return

            # ★ 自動投稿: classification_type を "completed" にセットして投稿
            logger.info(f"📤 配信終了イベントを自動投稿します: {title}")
            video_copy = dict(video)
            video_copy["classification_type"] = "completed"  # テンプレート selection に使用
            video_copy["content_type"] = current_type
            video_copy["live_status"] = current_live_status

            if self.plugin_manager:
                try:
                    results = self.plugin_manager.post_video_with_all_enabled(video_copy)
                    if any(results.values()):
                        self.db.mark_as_posted(video_id)
                        logger.info(f"✅ 配信終了イベントの自動投稿に成功しました: {video_id}")
                    else:
                        logger.warning(f"⚠️  配信終了イベントの自動投稿に失敗しました: {video_id}")
                except Exception as e:
                    logger.error(f"❌ 配信終了イベント投稿エラー: {video_id} - {e}")
            else:
                logger.warning(f"⚠️  plugin_manager が初期化されていません（投稿スキップ）")

            # ★ 【新規】current_type が archive の場合、アーカイブ公開イベントも処理
            if current_type == VIDEO_TYPE_ARCHIVE:
                logger.info(f"🎬 【続: アーカイブ公開イベント】 {video_id} (配信終了の時点でアーカイブ化)")
                self._on_archive_available(video, result)

        except Exception as e:
            logger.error(f"❌ 配信終了イベントハンドラエラー: {video_id} - {e}")

    def _on_archive_available(self, video: Dict[str, Any], result: Dict[str, Any]) -> None:
        """
        アーカイブ公開イベントハンドラ

        completed → archive への状態遷移を処理

        Args:
            video: DB から取得した既存の動画情報
            result: YouTubeVideoClassifier.classify_video() の戻り値
        """
        video_id = video.get("video_id")
        title = video.get("title", "【ライブアーカイブ公開】")

        try:
            # ★ DB を更新
            self.db.update_video_status(video_id, VIDEO_TYPE_ARCHIVE, None)  # archive は live_status=None
            logger.info(f"✅ DB更新: {video_id} → type=archive, status=None")

            # ★ 自動投稿判定
            should_post = self._should_autopost_live(VIDEO_TYPE_ARCHIVE, None)
            if not should_post:
                logger.debug(f"⏭️  アーカイブ公開の自動投稿スキップ（設定により）: {video_id}")
                return

            # ★ 自動投稿: classification_type を "archive" にセットして投稿
            logger.info(f"📤 アーカイブ公開イベントを自動投稿します: {title}")
            video_copy = dict(video)
            video_copy["classification_type"] = "archive"  # テンプレート selection に使用
            video_copy["content_type"] = VIDEO_TYPE_ARCHIVE
            video_copy["live_status"] = None

            if self.plugin_manager:
                try:
                    results = self.plugin_manager.post_video_with_all_enabled(video_copy)
                    if any(results.values()):
                        self.db.mark_as_posted(video_id)
                        logger.info(f"✅ アーカイブ公開イベントの自動投稿に成功しました: {video_id}")
                    else:
                        logger.warning(f"⚠️  アーカイブ公開イベントの自動投稿に失敗しました: {video_id}")
                except Exception as e:
                    logger.error(f"❌ アーカイブ公開イベント投稿エラー: {video_id} - {e}")
            else:
                logger.warning(f"⚠️  plugin_manager が初期化されていません（投稿スキップ）")

        except Exception as e:
            logger.error(f"❌ アーカイブ公開イベントハンドラエラー: {video_id} - {e}")

    def set_plugin_manager(self, pm) -> None:
        """
        PluginManager を注入（自動投稿用）

        Args:
            pm: PluginManager インスタンス
        """
        self.plugin_manager = pm
        logger.debug(f"✅ LiveModule に PluginManager を注入しました")


def get_live_module(db: Optional[Database] = None, plugin_manager=None) -> LiveModule:
    """
    LiveModule インスタンスを取得（シングルトンパターン推奨）

    Args:
        db: Database インスタンス
        plugin_manager: PluginManager インスタンス

    Returns:
        LiveModule インスタンス
    """
    return LiveModule(db=db, plugin_manager=plugin_manager)
