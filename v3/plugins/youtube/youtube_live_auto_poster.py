# -*- coding: utf-8 -*-

"""
YouTubeLive 自動投稿層

ポーリング層からのイベントを受け取り、Bluesky に投稿実行
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("AppLogger")
post_logger = logging.getLogger("PostLogger")

__author__ = "mayuneco(mayunya)"
__copyright__ = "Copyright (C) 2025 mayuneco(mayunya)"
__license__ = "GPLv2"


class YouTubeLiveAutoPoster:
    """
    自動投稿トリガー層 - イベント受信 → 自動投稿判定 → Bluesky 投稿実行

    【責務】
    - YouTubeLivePoller からイベントを受信（live_started, live_ended, archive_available）
    - 「投稿するかしないか」の最終判定を実行 (_should_autopost_event)
    - 投稿データを構築
    - plugin_manager を通じて Bluesky に投稿実行
    - 投稿後、DB の posted_to_bluesky フラグを更新（重要！）

    【責務 OUT】
    - 分類判定 → YouTubeLiveClassifier で実装
    - 状態遷移検出 → YouTubeLivePoller で実装
    - DB/キャッシュの詳細操作 → YouTubeLiveStore で実装

    自動投稿判定ロジック (_should_autopost_event) は、
    YouTubeLive 全体における唯一の投稿判定ロジック。
    """

    def __init__(self, plugin_manager=None, store=None, config=None):
        """
        初期化

        Args:
            plugin_manager: PluginManager インスタンス
            store: YouTubeLiveStore インスタンス
            config: Config オブジェクト
        """
        self.plugin_manager = plugin_manager
        self.store = store
        self.config = config

    def set_plugin_manager(self, plugin_manager) -> None:
        """
        plugin_manager を注入（YouTubeLivePlugin.on_enable() 時に呼ばれる）

        Args:
            plugin_manager: PluginManager インスタンス
        """
        self.plugin_manager = plugin_manager
        logger.debug(f"✅ YouTubeLiveAutoPoster に plugin_manager を注入しました")

    def set_config(self, config) -> None:
        """
        config を注入（YouTubeLivePlugin.on_enable() 時に呼ばれる）

        Args:
            config: Config インスタンス
        """
        self.config = config
        logger.debug(f"✅ YouTubeLiveAutoPoster に config を注入しました")

    def on_live_started(self, video_id: str, video: Dict[str, Any]) -> bool:
        """
        ライブ配信開始イベントハンドラ

        LIVE ステータスが "live" になったときに発火する。
        自動投稿設定に基づいて、Bluesky に「配信開始」通知を投稿する。

        Args:
            video_id: 動画ID
            video: 動画情報

        Returns:
            投稿成功フラグ
        """
        logger.info(f"🔴 [イベント] ライブ配信開始: {video_id}")

        # ★ 自動投稿判定が False なら早期リターン（コンポーネント未設定含む）
        if not self._should_autopost_event("live_started"):
            return False

        if self.plugin_manager is None or self.store is None:
            logger.error("❌ plugin_manager または store が未設定です")
            return False

        try:
            # 動画データ構築
            post_data = self._build_post_data(video, event_type="live_started")
            if post_data is None:
                logger.error(f"❌ 投稿データ構築失敗")
                return False

            # Bluesky 投稿
            results = self.plugin_manager.post_video_with_all_enabled(post_data)

            if any(results.values()):
                # DB 更新
                self.store.mark_as_posted(video_id)
                post_logger.info(f"✅ ライブ配信開始通知を投稿しました: {video_id}")
                return True
            else:
                logger.error(f"❌ ライブ配信開始通知の投稿に失敗: {video_id}")
                return False

        except Exception as e:
            logger.error(f"❌ ライブ配信開始処理エラー: {video_id} - {e}")
            return False

    def on_live_ended(self, video_id: str, video: Dict[str, Any]) -> bool:
        """
        ライブ配信終了イベントハンドラ

        LIVE ステータスが "live" → "completed" に遷移したときに発火する。
        自動投稿設定に基づいて、Bluesky に「配信終了」通知を投稿する。

        Args:
            video_id: 動画ID
            video: 動画情報

        Returns:
            投稿成功フラグ
        """
        logger.info(f"🔴 [イベント] ライブ配信終了: {video_id}")

        # ★ 自動投稿判定が False なら早期リターン（コンポーネント未設定含む）
        if not self._should_autopost_event("live_ended"):
            return False

        if self.plugin_manager is None or self.store is None:
            logger.error("❌ plugin_manager または store が未設定です")
            return False

        try:
            # 動画データ構築
            post_data = self._build_post_data(video, event_type="live_ended")
            if post_data is None:
                logger.error(f"❌ 投稿データ構築失敗")
                return False

            # Bluesky 投稿
            results = self.plugin_manager.post_video_with_all_enabled(post_data)

            if any(results.values()):
                # DB 更新（重要！）
                self.store.mark_as_posted(video_id)
                post_logger.info(f"✅ ライブ配信終了通知を投稿しました: {video_id}")
                return True
            else:
                logger.error(f"❌ ライブ配信終了通知の投稿に失敗: {video_id}")
                return False

        except Exception as e:
            logger.error(f"❌ ライブ配信終了処理エラー: {video_id} - {e}")
            return False

    def on_archive_available(self, video_id: str, video: Dict[str, Any]) -> bool:
        """
        アーカイブ公開イベントハンドラ

        content_type が "live" → "archive" に遷移したときに発火する。
        自動投稿設定に基づいて、Bluesky に「アーカイブ公開」通知を投稿する。

        Args:
            video_id: 動画ID
            video: 動画情報

        Returns:
            投稿成功フラグ
        """
        logger.info(f"📹 [イベント] アーカイブ公開: {video_id}")

        # ★ 自動投稿判定が False なら早期リターン（コンポーネント未設定含む）
        if not self._should_autopost_event("archive_available"):
            return False

        if self.plugin_manager is None or self.store is None:
            logger.error("❌ plugin_manager または store が未設定です")
            return False

        try:
            # 動画データ構築
            post_data = self._build_post_data(video, event_type="archive_available")
            if post_data is None:
                logger.error(f"❌ 投稿データ構築失敗")
                return False

            # Bluesky 投稿
            results = self.plugin_manager.post_video_with_all_enabled(post_data)

            if any(results.values()):
                # DB 更新
                self.store.mark_as_posted(video_id)
                post_logger.info(f"✅ アーカイブ公開通知を投稿しました: {video_id}")
                return True
            else:
                logger.error(f"❌ アーカイブ公開通知の投稿に失敗: {video_id}")
                return False

        except Exception as e:
            logger.error(f"❌ アーカイブ公開処理エラー: {video_id} - {e}")
            return False

    def _should_autopost_event(self, event_type: str) -> bool:
        """
        ★【唯一の自動投稿判定ロジック】イベント種別に基づいた自動投稿判定

        このメソッドが、YouTubeLive 全体における「投稿するかしないか」の
        最終判定を行う唯一の場所である。

        APP_MODE と YOUTUBE_LIVE_AUTO_POST_MODE の解釈もここに集約される。

        Args:
            event_type: イベント種別
                - "live_started": LIVE 配信開始
                - "live_ended": LIVE 配信終了
                - "archive_available": アーカイブ公開

        Returns:
            True: 投稿すべき
            False: 投稿スキップ
        """
        if self.config is None:
            logger.error("❌ config が未設定です")
            return False

        # AUTOPOST モード以外は自動投稿しない
        if self.config.operation_mode != "autopost":
            logger.debug(f"⏭️ AUTOPOST モードではありません: {self.config.operation_mode}")
            return False

        # YOUTUBE_LIVE_AUTO_POST_MODE に基づいて判定
        mode = self.config.youtube_live_autopost_mode

        if mode == "off":
            logger.debug(f"⏭️ mode='off': 投稿スキップ")
            return False

        if event_type == "live_started":
            # live_started: mode in ("all", "live", "schedule") で投稿
            result = mode in ("all", "live", "schedule")
            logger.debug(f"🔍 live_started 投稿判定: mode={mode} → {result}")
            return result

        if event_type == "live_ended":
            # live_ended: mode in ("all", "live") で投稿
            result = mode in ("all", "live")
            logger.debug(f"🔍 live_ended 投稿判定: mode={mode} → {result}")
            return result

        if event_type == "archive_available":
            # archive_available: mode in ("all", "archive") で投稿
            result = mode in ("all", "archive")
            logger.debug(f"🔍 archive_available 投稿判定: mode={mode} → {result}")
            return result

        logger.debug(f"⏭️ 未知のイベント: {event_type}")
        return False

    def _build_post_data(self, video: Dict[str, Any], event_type: str) -> Optional[Dict[str, Any]]:
        """
        投稿用の動画データを構築

        Args:
            video: DB から取得した動画情報
            event_type: イベント種別（"live_started", "live_ended", "archive_available"）

        Returns:
            投稿用データ、エラー時 None
        """
        if video is None:
            logger.error("❌ video が None です")
            return None

        try:
            # 動画データをコピー
            post_data = dict(video)

            # イベント種別をメタデータに追加
            post_data["_event_type"] = event_type

            # テンプレート選択用メタデータを追加
            if event_type == "live_started":
                post_data["_template_name"] = "youtube_online"
            elif event_type == "live_ended":
                post_data["_template_name"] = "youtube_offline"
            elif event_type == "archive_available":
                post_data["_template_name"] = "youtube_archive"

            logger.debug(f"✅ 投稿データ構築: {event_type}")
            return post_data

        except Exception as e:
            logger.error(f"❌ 投稿データ構築エラー: {e}")
            return None

    def get_statistics(self) -> Dict[str, int]:
        """
        投稿統計情報を取得

        Returns:
            Dict: {
                "autopost_enabled": bool,
                "mode": str
            }
        """
        stats = {
            "autopost_enabled": False,
            "mode": "off"
        }

        try:
            if self.config:
                stats["autopost_enabled"] = self.config.operation_mode == "autopost"
                stats["mode"] = self.config.youtube_live_autopost_mode

            return stats

        except Exception as e:
            logger.error(f"❌ 統計取得エラー: {e}")
            return stats
