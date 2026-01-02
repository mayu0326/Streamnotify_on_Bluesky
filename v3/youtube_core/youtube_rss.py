# -*- coding: utf-8 -*-

"""
Stream notify on Bluesky - v3 YouTube RSS 管理

YouTube チャンネルの RSS を取得・パース・DB に保存する。
（画像処理は thumbnails/youtube_thumb_utils.py の YouTubeThumbPlugin で管理）
"""

import feedparser
import logging
import requests
import sqlite3
from typing import List, Dict
from datetime import datetime, timedelta, timezone
from image_manager import get_youtube_thumbnail_url

logger = logging.getLogger("AppLogger")

__author__ = "mayuneco(mayunya)"
__copyright__ = "Copyright (C) 2025 mayuneco(mayunya)"
__license__ = "GPLv2"

YOUTUBE_RSS_URL_TEMPLATE = "https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"


class YouTubeRSS:
    """YouTube RSS 取得・管理クラス"""

    def __init__(self, channel_id: str):
        """
        初期化

        Args:
            channel_id: YouTube チャンネル ID
        """
        self.channel_id = channel_id
        self.rss_url = YOUTUBE_RSS_URL_TEMPLATE.format(channel_id=channel_id)

    def fetch_feed(self) -> List[Dict]:
        """
        RSS フィードを取得・パース

        Returns:
            新着動画のリスト（最新順）
        """
        try:
            logger.debug(f"RSS を取得します: {self.rss_url}")
            feed = feedparser.parse(self.rss_url)

            if feed.status != 200 and feed.bozo:
                logger.warning(f"RSS 取得に警告がありました: {feed.bozo_exception}")

            videos = []
            for entry in feed.entries[:15]:  # 最新 15 件まで
                # ★ 重要: RSS の published_at は UTC 形式（例: 2025-12-28T18:00:00Z）
                # これを JST に変換してから保存
                rss_published_at = entry.published

                # UTC → JST 変換
                try:
                    utc_time = datetime.fromisoformat(rss_published_at.replace('Z', '+00:00'))
                    jst_time = utc_time.astimezone(timezone(timedelta(hours=9))).replace(tzinfo=None)
                    published_at_jst = jst_time.isoformat()
                    logger.debug(f"📡 RSS 日時を JST に変換: {rss_published_at} → {published_at_jst}")
                except Exception as e:
                    logger.warning(f"⚠️ RSS 日時の JST 変換失敗、元の値を使用: {e}")
                    published_at_jst = rss_published_at

                # ★ v3.4.0: channel_name が空の場合、キャッシュまたは API から取得
                channel_name = entry.author if hasattr(entry, "author") else ""
                if not channel_name:
                    try:
                        # YouTube API キャッシュから channelTitle を取得
                        from plugins.youtube.youtube_api_plugin import YouTubeAPIPlugin
                        api_plugin = YouTubeAPIPlugin()

                        if api_plugin.is_available():
                            # API から動画詳細を取得
                            details = api_plugin.fetch_video_detail(entry.yt_videoid)
                            if details:
                                video_info = api_plugin._extract_video_info(details)
                                channel_name = video_info.get("channel_name", "")
                                if channel_name:
                                    logger.debug(f"✅ YouTube API から channel_name を取得: {channel_name}")
                    except Exception as e:
                        logger.debug(f"⚠️ YouTube API からの channel_name 取得失敗: {e}")

                    # API でも取得できない場合はフォールバック
                    if not channel_name:
                        try:
                            from config import get_config
                            config = get_config("settings.env")
                            channel_id = config.youtube_channel_id if hasattr(config, "youtube_channel_id") else ""
                            if channel_id:
                                channel_name = f"Channel ({channel_id[:8]}...)"
                                logger.debug(f"✅ RSS の channel_name が空だったため、チャンネル ID からフォールバック: {channel_name}")
                        except Exception as e:
                            logger.debug(f"⚠️ チャンネル ID からのフォールバック失敗: {e}")

                video = {
                    "video_id": entry.yt_videoid,
                    "title": entry.title,
                    "video_url": entry.link,
                    "published_at": published_at_jst,  # ★ JST 変換済みの値を使用
                    "channel_name": channel_name,
                }
                videos.append(video)

            youtube_logger = logging.getLogger("YouTubeLogger")
            youtube_logger.info(f"RSS から {len(videos)} 個の動画を取得しました")
            return videos

        except Exception as e:
            logger.error(f"RSS 取得に失敗しました: {e}")
            return []

    def save_to_db(self, database) -> int:
        """
        RSS から取得した動画を DB に保存

        ⚠️ NOTE: 新規動画の画像ダウンロード・保存は
        thumbnails/youtube_thumb_utils.py の YouTubeThumbPlugin で実行されます。

        ★ v3.3.0+ YouTube API優先: RSS登録後、YouTube API で最新情報を確認し、
           scheduledStartTime が存在する場合は上書きします。

        Args:
            database: Database オブジェクト

        Returns:
            保存された動画数
        """
        videos = self.fetch_feed()
        saved_count = 0
        existing_count = 0
        blacklist_skip_count = 0
        youtube_logger = logging.getLogger("YouTubeLogger")

        youtube_logger.info(f"[YouTube RSS] 取得した {len(videos)} 個の動画を DB に照合しています...")

        # ★ 新: 除外動画リストを取得
        try:
            from deleted_video_cache import get_deleted_video_cache
            deleted_cache = get_deleted_video_cache()
        except ImportError:
            youtube_logger.warning("deleted_video_cache モジュールが見つかりません")
            deleted_cache = None

        # ★ 新: YouTube API プラグインを取得（API有効時のみ）
        youtube_api_plugin = None
        try:
            from plugin_manager import get_plugin_manager
            plugin_mgr = get_plugin_manager()
            youtube_api_plugin = plugin_mgr.get_plugin("youtube_api_plugin")
            if youtube_api_plugin and youtube_api_plugin.is_available():
                youtube_logger.debug("✅ YouTube API プラグイン が利用可能です（RSS の情報を API で確認します）")
            else:
                youtube_api_plugin = None
        except Exception as e:
            youtube_logger.debug(f"⚠️ YouTube API プラグイン未利用: {e}")

        # database モジュールのロガーを一時的に YouTubeLogger に切り替え
        import database as db_module
        original_logger = db_module.logger
        db_module.logger = youtube_logger

        try:
            for video in videos:
                # ★ 新: 除外動画リスト確認
                if deleted_cache and deleted_cache.is_deleted(video["video_id"], source="youtube"):
                    youtube_logger.info(f"⏭️ 除外動画リスト登録済みのため、スキップします: {video['title']}")
                    blacklist_skip_count += 1
                    continue

                # サムネイル URL を取得（多品質フォールバック）
                thumbnail_url = get_youtube_thumbnail_url(video["video_id"])

                # ★ 重要: YouTube API プラグイン を優先実行
                # API から取得した scheduledStartTime を published_at として使用
                api_published_at = None
                api_scheduled_start_time = None  # ★ 新: scheduledStartTime を別途保存（上書き判定用）

                if youtube_api_plugin:
                    try:
                        details = youtube_api_plugin.fetch_video_detail(video["video_id"])
                        if details:
                            live_details = details.get("liveStreamingDetails", {})
                            snippet = details.get("snippet", {})

                            # API優先: scheduledStartTime > actualStartTime > publishedAt
                            # ★ 重要: API の時刻は UTC なので、JST に変換してから使用
                            if live_details.get("scheduledStartTime"):
                                api_published_at = live_details["scheduledStartTime"]
                                # UTC から JST に変換（+9時間）
                                try:
                                    utc_time = datetime.fromisoformat(api_published_at.replace('Z', '+00:00'))
                                    jst_time = utc_time.astimezone(timezone(timedelta(hours=9))).replace(tzinfo=None)
                                    api_published_at_jst = jst_time.isoformat()
                                    api_scheduled_start_time = api_published_at_jst  # JST 版を保存
                                    youtube_logger.info(f"📡 API確認: scheduledStartTime を使用（UTC→JST変換）: {api_published_at} → {api_published_at_jst}")
                                except Exception as e:
                                    api_scheduled_start_time = api_published_at  # 変換失敗時は元の値を使用
                                    youtube_logger.warning(f"⚠️ UTC→JST変換失敗、元の値を使用: {e}")
                            elif live_details.get("actualStartTime"):
                                api_published_at = live_details["actualStartTime"]
                                # UTC から JST に変換
                                try:
                                    utc_time = datetime.fromisoformat(api_published_at.replace('Z', '+00:00'))
                                    jst_time = utc_time.astimezone(timezone(timedelta(hours=9))).replace(tzinfo=None)
                                    api_published_at_jst = jst_time.isoformat()
                                    api_scheduled_start_time = api_published_at_jst  # JST 版を保存
                                    youtube_logger.info(f"📡 API確認: actualStartTime を使用（UTC→JST変換）: {api_published_at} → {api_published_at_jst}")
                                except Exception as e:
                                    api_scheduled_start_time = api_published_at  # 変換失敗時は元の値を使用
                                    youtube_logger.warning(f"⚠️ UTC→JST変換失敗、元の値を使用: {e}")
                            elif snippet.get("publishedAt"):
                                api_published_at = snippet["publishedAt"]
                                youtube_logger.debug(f"📡 API確認: publishedAt を使用: {api_published_at}")
                        else:
                            youtube_logger.warning(f"⚠️ API で {video['video_id']} の詳細が取得できません（RSS 日時を使用）")
                    except Exception as e:
                        youtube_logger.warning(f"⚠️ API 確認処理でエラー（RSS日時を使用）: {e}")

                # DB に保存（published_at は API優先、なければ RSS）
                # ★ 重要: JST 変換済みの値を使用（api_scheduled_start_time）、または RSS の値（既に JST）
                final_published_at = api_scheduled_start_time if api_scheduled_start_time else video["published_at"]

                is_new = database.insert_video(
                    video_id=video["video_id"],
                    title=video["title"],
                    video_url=video["video_url"],
                    published_at=final_published_at,  # ★ API優先の日時を使用（JST 変換済み）
                    channel_name=video["channel_name"],
                    thumbnail_url=thumbnail_url,
                    source="youtube",
                )

                if is_new:
                    saved_count += 1
                    youtube_logger.debug(f"[YouTube RSS] 新動画を DB に保存しました: {video['title']}")
                else:
                    # ★ 修正3: is_new = False の場合のイベント判定ロジック改善
                    # DB に実際に存在するかを確認
                    try:
                        check_conn = database._get_connection()
                        check_cursor = check_conn.cursor()
                        check_cursor.execute("SELECT COUNT(*) FROM videos WHERE video_id = ?", (video["video_id"],))
                        db_count = check_cursor.fetchone()[0]
                        check_conn.close()

                        if db_count > 0:
                            # ★ DB に存在 → 既存動画として扱う
                            existing_count += 1
                            youtube_logger.debug(f"[YouTube RSS] 既存動画です: {video['title']}")

                            # 既存動画の場合、API データで published_at を上書き（★ 重要: API が RSS より優先）
                            # API から scheduledStartTime/actualStartTime が取得できた場合は、DB の値を上書き
                            if api_scheduled_start_time:
                                # DB の既存 published_at と異なる場合のみ上書き（無駄な更新を避ける）
                                try:
                                    conn = database._get_connection()
                                    conn.row_factory = sqlite3.Row
                                    cursor = conn.cursor()
                                    cursor.execute("SELECT published_at FROM videos WHERE video_id = ?", (video["video_id"],))
                                    row = cursor.fetchone()
                                    conn.close()

                                    if row:
                                        db_published_at = row[0] if isinstance(row, tuple) else row["published_at"]
                                        if api_scheduled_start_time != db_published_at:
                                            database.update_published_at(video["video_id"], api_scheduled_start_time)
                                            youtube_logger.info(f"✅ 既存動画の published_at を API データで上書きしました: {video['title']}")
                                            youtube_logger.debug(f"   旧: {db_published_at} → 新: {api_scheduled_start_time}")
                                except Exception as e:
                                    youtube_logger.warning(f"⚠️ 既存動画の published_at 上書きに失敗: {e}")
                        else:
                            # ★ DB に不存在 → 削除済み動画として扱う
                            blacklist_skip_count += 1
                            youtube_logger.info(f"↩️ 削除済み動画のため、スキップしました: {video['title']}")
                    except Exception as e:
                        youtube_logger.warning(f"⚠️ DB 確認処理でエラー: {e}")
                        # フォールバック: 既存動画として扱う
                        existing_count += 1

            summary = f"✅ 保存完了: 新規 {saved_count}, 既存 {existing_count}"
            if blacklist_skip_count > 0:
                summary += f", 除外動画リスト {blacklist_skip_count}"

            if saved_count > 0:
                youtube_logger.info(summary)
            elif blacklist_skip_count > 0:
                youtube_logger.info(summary)
            else:
                youtube_logger.info(f"ℹ️ 新着動画はありません")

        finally:
            # ロガーを元に戻す
            db_module.logger = original_logger

        return saved_count

    def poll_videos(self):
        """RSSフィードをポーリングし、キャッシュを更新"""
        videos = self.fetch_feed()
        for video in videos:
            video_id = video['video_id']
            if video_id not in self.deleted_cache:
                self.db.insert_video(video_id, video['title'], video['video_url'], video['published_at'], video['channel_name'])
                # キャッシュ更新を追加
                self.plugin.update_video_detail_cache(video_id, video)


def get_youtube_rss(channel_id: str) -> YouTubeRSS:
    """YouTube RSS オブジェクトを取得"""
    return YouTubeRSS(channel_id)
