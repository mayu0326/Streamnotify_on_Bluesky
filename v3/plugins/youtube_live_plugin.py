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
from youtube_live_cache import get_youtube_live_cache

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
        self.plugin_manager = None  # ★ main_v3.py から注入される

    def is_available(self) -> bool:
        return bool(self.api_key and self.channel_id)

    def get_name(self) -> str:
        return "YouTubeLive 検出プラグイン"

    def get_version(self) -> str:
        return "0.2.0"

    def get_description(self) -> str:
        return "YouTubeライブ/アーカイブ判定を行いDBに格納するプラグイン（クォータ対応）"

    def set_plugin_manager(self, pm) -> None:
        """plugin_manager を注入（自動投稿用）"""
        self.plugin_manager = pm

    def on_enable(self) -> None:
        """
        プラグイン有効化時に実行

        RSS で登録された未判定動画（content_type="video" でも liveStreamingDetails がある場合）
        を自動検出して、正しい分類に更新する
        """
        logger.info("🔍 YouTube Live プラグイン: RSS登録動画の自動判定を開始します...")
        updated_count = self._update_unclassified_videos()
        if updated_count > 0:
            logger.info(f"✅ {updated_count} 個の動画を自動判定して更新しました")
        else:
            logger.info(f"ℹ️ 自動判定結果: 更新対象の動画はありません（既に分類済みか、分類不可）")

    def _update_unclassified_videos(self) -> int:
        """
        DB から content_type="video" の動画を取得し、
        キャッシュされた YouTube API 詳細情報を使用してライブ/アーカイブを判定・更新

        戦略:
        1️⃣ キャッシュから取得を試みる（既に API で取得済みの動画）
        2️⃣ キャッシュにない場合は API から取得（初回起動時の分類用）
        3️⃣ API エラーの場合はスキップ（コスト・エラー耐性重視）

        Returns:
            int: 更新した動画数
        """
        try:
            # 全動画取得
            all_videos = self.db.get_all_videos()

            # content_type="video" で、未だ判定されていない動画を抽出
            unclassified = [
                v for v in all_videos
                if v.get("content_type") == "video" or v.get("content_type") is None
            ]

            if not unclassified:
                logger.debug("ℹ️ 未判定動画はありません")
                return 0

            logger.info(f"📊 未判定動画: {len(unclassified)} 件を確認します（キャッシュ優先、キャッシュなければ API 取得）...")

            updated_count = 0
            skipped_no_cache = 0
            skipped_no_live = 0

            for video in unclassified:
                video_id = video.get("video_id")
                if not video_id:
                    continue

                # Niconico など非YouTube形式をスキップ
                if not self._is_valid_youtube_video_id(video_id):
                    continue

                # ⭐ ステップ 1️⃣: キャッシュから取得を試みる
                details = self.api_plugin._get_cached_video_detail(video_id)

                # ⭐ ステップ 2️⃣: キャッシュになければ API から取得
                if not details:
                    logger.debug(f"🔄 キャッシュなし、API から取得します: {video_id}")
                    try:
                        details = self.api_plugin._fetch_video_detail(video_id)
                        if details:
                            logger.debug(f"✅ API から動画詳細を取得: {video_id}")
                        else:
                            logger.debug(f"⏭️ API から詳細情報が取得できませんでした（スキップ）: {video_id}")
                            skipped_no_cache += 1
                            continue
                    except Exception as e:
                        logger.debug(f"⏭️ API エラー（スキップ）: {video_id} - {e}")
                        skipped_no_cache += 1
                        continue

                # 分類
                content_type, live_status, is_premiere = self._classify_live(details)
                logger.debug(f"📋 分類結果: {video_id} → content_type={content_type}, live_status={live_status}")

                # ライブ or アーカイブの場合のみ更新
                if content_type in ("live", "archive"):
                    success = self.db.update_video_status(video_id, content_type, live_status)
                    if success:
                        updated_count += 1
                        logger.info(f"✅ 判定更新: {video_id} → {content_type} ({live_status})")
                    else:
                        logger.error(f"❌ DB更新失敗: {video_id}")
                else:
                    logger.debug(f"⏭️ スキップ（live/archive 以外）: {video_id} → {content_type}")
                    skipped_no_live += 1

            logger.info(f"✅ 自動判定完了: 更新 {updated_count} 件、キャッシュなし {skipped_no_cache} 件、非ライブ {skipped_no_live} 件")

            # ★ 新: 判定後、自動投稿対象を検査して投稿を実行
            # APP_MODE に応じて、AUTOPOST 時は YOUTUBE_LIVE_AUTO_POST_MODE で、
            # SELFPOST 時は個別フラグで投稿判定を行う
            # 注: updated_count > 0 でなくても、既に判定済みの未投稿 live/archive 動画を自動投稿対象にする
            if True:  # 常に投稿判定を実行（updated_count と無関係）
                logger.info(f"🚀 YouTube Live 自動投稿処理を開始します（更新件数: {updated_count}）")
                try:
                    from config import get_config
                    config = get_config("settings.env")

                    # ★ plugin_manager が注入されていることを確認
                    if not hasattr(self, 'plugin_manager') or not self.plugin_manager:
                        logger.warning("⚠️ YouTube Live 自動投稿: plugin_manager が未初期化です（スキップ）")
                        logger.warning(f"   hasattr(self, 'plugin_manager')={hasattr(self, 'plugin_manager')}")
                        logger.warning(f"   self.plugin_manager={getattr(self, 'plugin_manager', None)}")
                        return updated_count

                    logger.debug(f"✅ plugin_manager 初期化確認: {self.plugin_manager}")

                    # ★ 判定後、DB から fresh に全動画を取得（更新された content_type/live_status を反映）
                    all_videos_fresh = self.db.get_all_videos()
                    logger.debug(f"📊 fresh 取得動画数: {len(all_videos_fresh)}")
                    autopost_count = 0

                    for video in all_videos_fresh:
                        video_id = video.get("video_id")
                        if not video_id:
                            continue

                        # 既投稿はスキップ
                        if video.get("posted_to_bluesky"):
                            logger.debug(f"⏭️ スキップ（既投稿）: {video_id}")
                            continue

                        content_type = video.get("content_type")
                        live_status = video.get("live_status")

                        # live または archive のみ対象
                        # 注: updated_count が 0 でも、既に判定済みの live/archive 動画を処理する
                        if content_type not in ("live", "archive"):
                            logger.debug(f"⏭️ スキップ（content_type={content_type}）: {video_id}")
                            continue

                        # 自動投稿判定（APP_MODE に応じて自動切り替え）
                        should_post = self._should_autopost_live(content_type, live_status, config)
                        logger.debug(f"📋 投稿判定: {video_id} → should_post={should_post}, content_type={content_type}, live_status={live_status}")
                        
                        if should_post:
                            logger.info(f"📤 YouTube Live 自動投稿: {video['title']} (content_type={content_type}, live_status={live_status})")
                            results = self.plugin_manager.post_video_with_all_enabled(video)
                            logger.debug(f"   投稿結果: {results}")
                            if any(results.values()):
                                self.db.mark_as_posted(video_id)
                                autopost_count += 1
                                logger.info(f"✅ YouTube Live 自動投稿成功: {video['title']}")
                            else:
                                logger.warning(f"⚠️ YouTube Live 自動投稿失敗: {video['title']}")
                        else:
                            logger.debug(f"⏭️ 投稿判定NG（フラグ未設定か APP_MODE が合致）: {video_id}")

                    if autopost_count > 0:
                        logger.info(f"✅ YouTube Live 自動投稿完了: {autopost_count} 件を投稿しました")
                    else:
                        logger.info(f"ℹ️ YouTube Live 自動投稿完了: 投稿対象なし")
                except Exception as e:
                    logger.exception(f"❌ YouTube Live 自動投稿エラー（判定は完了）: {e}")
            else:
                logger.debug(f"ℹ️ 自動投稿スキップ: updated_count={updated_count}")


            return updated_count

        except Exception as e:
            logger.error(f"❌ YouTube Live 分類処理エラー: {e}")
            return 0

    def post_video(self, video: Dict[str, Any]) -> bool:
        """
        ライブ/アーカイブ判定を行い DB に保存

        video: {video_id, title?, channel_name?, published_at?}

        注：API プラグインを共有利用するため、クォータ管理は api_plugin に委譲
        """
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

        # AUTOPOST 時の自動投稿判定（仕様 v1.0 セクション 4）
        from config import get_config
        config = get_config("settings.env")
        should_autopost = self._should_autopost_live(content_type, live_status, config)
        if not should_autopost:
            logger.debug(f"⏭️ YouTube Live: YOUTUBE_LIVE_AUTOPOST_MODE の設定により投稿スキップ（content_type={content_type}, live_status={live_status}）")

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
        ライブ/アーカイブを判別

        ⚠️ このメソッドは api_plugin の _classify_video_core() へ委譲
        （コード重複を排除し、分類仕様は youtube_api_plugin に一元化）

        Returns:
            (content_type, live_status, is_premiere)
        """
        return self.api_plugin._classify_video_core(details)

    def _should_autopost_live(self, content_type: str, live_status: Optional[str], config=None) -> bool:
        """
        YouTube Live 自動投稿判定

        APP_MODE に応じて自動的に判定ロジックを切り替える:
        - AUTOPOST モード: YOUTUBE_LIVE_AUTO_POST_MODE（統合モード値）で判定
        - SELFPOST モード: YOUTUBE_LIVE_AUTO_POST_SCHEDULE/LIVE/ARCHIVE（個別フラグ）で判定

        Args:
            content_type: コンテンツ種別（"video", "live", "archive"）
            live_status: ライブ配信状態（None, "upcoming", "live", "completed"）
            config: Config オブジェクト（省略時は読み込み）

        Returns:
            bool: 投稿すべき場合 True、スキップすべき場合 False
        """
        if config is None:
            from config import get_config
            config = get_config("settings.env")

        # ★ APP_MODE に基づいて自動的に使用するフラグを決定
        # AUTOPOST モード時のみ YOUTUBE_LIVE_AUTO_POST_MODE を使用
        if config.operation_mode == "autopost":
            mode = config.youtube_live_autopost_mode
            logger.debug(f"🔄 AUTOPOST モード: mode={mode}")
        else:
            # SELFPOST・DRY_RUN・COLLECT モード: 個別フラグを使用
            mode = ""
            logger.debug(f"🔄 SELFPOST/DRY_RUN/COLLECT モード: 個別フラグを使用")

        # ★ テーブル仕様 v1.0 セクション 4.2 参照（モード値による判定）
        if mode == "off":
            logger.debug(f"⏭️ mode='off': 投稿スキップ")
            return False

        if mode == "all":
            # すべてのイベント投稿
            result = content_type in ("video", "live", "archive")
            logger.debug(f"🔍 mode='all': content_type={content_type} → {result}")
            return result

        if mode == "schedule":
            # 予約枠のみ
            result = content_type == "live" and live_status == "upcoming"
            logger.debug(f"🔍 mode='schedule': content_type={content_type}, live_status={live_status} → {result}")
            return result

        if mode == "live":
            # 配信開始・配信終了のみ
            result = content_type == "live" and live_status in ("live", "completed")
            logger.debug(f"🔍 mode='live': content_type={content_type}, live_status={live_status} → {result}")
            return result

        if mode == "archive":
            # アーカイブ公開のみ
            result = content_type == "archive"
            logger.debug(f"🔍 mode='archive': content_type={content_type} → {result}")
            return result

        # モード値が未設定の場合 → 個別フラグで判定（SELFPOST 向け）
        if not mode or mode == "":
            logger.debug(f"🔍 個別フラグで判定: content_type={content_type}, live_status={live_status}")
            if content_type == "live":
                if live_status == "upcoming":
                    result = config.youtube_live_auto_post_schedule
                    logger.debug(f"   upcoming: youtube_live_auto_post_schedule={result}")
                    return result
                elif live_status in ("live", "completed"):
                    result = config.youtube_live_auto_post_live
                    logger.debug(f"   live/completed: youtube_live_auto_post_live={result}")
                    return result

            if content_type == "archive":
                result = config.youtube_live_auto_post_archive
                logger.debug(f"   archive: youtube_live_auto_post_archive={result}")
                return result

            logger.debug(f"⏭️ デフォルト判定: False")
            return False

        # デフォルト: off
        logger.warning(f"⚠️ YOUTUBE_LIVE_AUTOPOST_MODE が無効: {mode}。投稿スキップします。")
        return False

    # --- ライブ自動投稿ロジック ---
    def auto_post_live_start(self, video: Dict[str, Any]) -> bool:
        """
        ライブ開始時の自動投稿

        Args:
            video: 動画情報（live_status="live"）

        Returns:
            投稿成功フラグ
        """
        try:
            # Bluesky プラグインを取得
            from plugin_manager import PluginManager
            pm = PluginManager()
            bluesky_plugin = pm.get_plugin("bluesky_plugin")

            if not bluesky_plugin or not bluesky_plugin.is_available():
                logger.warning("⚠️ Bluesky プラグインが利用不可です")
                return False

            # ライブ開始テンプレート指定
            video_copy = dict(video)
            video_copy["event_type"] = "live_start"
            video_copy["live_status"] = "live"

            logger.info(f"📡 ライブ開始自動投稿を実行します: {video.get('title')}")
            return bluesky_plugin.post_video(video_copy)

        except Exception as e:
            logger.error(f"❌ ライブ開始投稿エラー: {e}")
            return False

    def auto_post_live_end(self, video: Dict[str, Any]) -> bool:
        """
        ライブ終了時の自動投稿

        Args:
            video: 動画情報（live_status="completed"）

        Returns:
            投稿成功フラグ
        """
        try:
            # Bluesky プラグインを取得
            from plugin_manager import PluginManager
            pm = PluginManager()
            bluesky_plugin = pm.get_plugin("bluesky_plugin")

            if not bluesky_plugin or not bluesky_plugin.is_available():
                logger.warning("⚠️ Bluesky プラグインが利用不可です")
                return False

            # ライブ終了テンプレート指定
            video_copy = dict(video)
            video_copy["event_type"] = "live_end"
            video_copy["live_status"] = "completed"

            logger.info(f"📡 ライブ終了自動投稿を実行します: {video.get('title')}")
            return bluesky_plugin.post_video(video_copy)

        except Exception as e:
            logger.error(f"❌ ライブ終了投稿エラー: {e}")
            return False

    def poll_live_status(self) -> None:
        """
        ライブ中の動画を定期チェックし、終了を検知

        新フロー：
        ① DB から live_status='live' の動画を取得
        ② 各動画の現在状態を API で確認
        ③ DB データと API データを組み合わせてキャッシュに保存
        ④ ポーリング（動画IDについて）を行い、キャッシュを更新
        ⑤ LIVE終了の API データが取れたら終了と判定 → キャッシュデータで本番DB更新
        ⑥ 設定に基づき自動投稿（オプション）
        """
        try:
            # ① DB から live_status='live' の動画を取得
            live_videos = self.db.get_videos_by_live_status("live")

            if not live_videos:
                logger.debug("ℹ️ ライブ中の動画がありません")
                return

            logger.info(f"🔄 {len(live_videos)} 件のライブ中動画をチェック中...")

            # キャッシュ取得
            cache = get_youtube_live_cache()

            for video in live_videos:
                video_id = video.get("video_id")
                if not video_id:
                    continue

                # ② API で現在の状態を確認
                details = self.api_plugin._fetch_video_detail(video_id)
                if not details:
                    logger.warning(f"⚠️ 動画詳細取得に失敗: {video_id}")
                    continue

                # ③ DB データと API データを組み合わせてキャッシュに保存
                cache_entry = cache.get_live_video(video_id)
                if not cache_entry:
                    # 初回追加
                    db_data = {
                        "title": video.get("title"),
                        "channel_name": video.get("channel_name"),
                        "video_url": video.get("video_url"),
                        "published_at": video.get("published_at"),
                        "thumbnail_url": video.get("thumbnail_url"),
                    }
                    cache.add_live_video(video_id, db_data, details)
                    logger.debug(f"📌 キャッシュに追加: {video_id}")
                else:
                    # ④ ポーリング結果に基づきキャッシュを更新
                    cache.update_live_video(video_id, details)
                    logger.debug(f"🔄 キャッシュを更新: {video_id}")

                # 分類ロジックで現在の状態を判定
                content_type, live_status, is_premiere = self._classify_live(details)

                # ⑤ LIVE終了の API データが取れたら終了と判定 → キャッシュデータで本番DB更新
                if live_status == "completed" or content_type == "archive":
                    logger.info(f"✅ ライブ終了を検知: {video_id} (live_status={live_status}, content_type={content_type})")

                    # キャッシュを終了状態に更新
                    cache.mark_as_ended(video_id)

                    # DB 更新（キャッシュデータを反映）
                    self.db.update_video_status(video_id, content_type, live_status)

                    # ⑥ 設定に基づき自動投稿（新仕様：YOUTUBE_LIVE_AUTOPOST_MODE）
                    from config import get_config
                    config = get_config("settings.env")
                    if self._should_autopost_live(content_type, live_status, config):
                        self.auto_post_live_end(video)
                    else:
                        logger.info(f"ℹ️ YOUTUBE_LIVE_AUTOPOST_MODE の設定により投稿スキップ（content_type={content_type}, live_status={live_status}）")

                    # 終了済み動画をキャッシュから削除
                    cache.remove_live_video(video_id)

        except Exception as e:
            logger.error(f"❌ ライブ終了チェックエラー: {e}")


def get_plugin():
    """PluginManager から取得するためのヘルパー"""
    return YouTubeLivePlugin()
