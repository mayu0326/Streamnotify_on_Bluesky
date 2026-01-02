# -*- coding: utf-8 -*-

"""
Stream notify on Bluesky - v3 YouTube WebSub 管理（Webhook版）

WebSub（Webhook）経由で本番サーバーから動画情報を取得・DB に保存する。
（画像処理は thumbnails/youtube_thumb_utils.py の YouTubeThumbPlugin で管理）

★ v3.3.0+ WebSub版：RSS の代わりに ProductionServerAPIClient を使用
"""

import logging
import os
from typing import List, Dict
from datetime import datetime, timedelta, timezone
from image_manager import get_youtube_thumbnail_url

logger = logging.getLogger("AppLogger")

__author__ = "mayuneco(mayunya)"
__copyright__ = "Copyright (C) 2025 mayuneco(mayunya)"
__license__ = "GPLv3"

class YouTubeWebSub:
    """YouTube WebSub 取得・管理クラス（ProductionServerAPIClient を使用）"""

    def __init__(self, channel_id: str):
        """
        初期化

        Args:
            channel_id: YouTube チャンネル ID
        """
        self.channel_id = channel_id
        self._api_client = None
        self._websub_registered = False  # WebSub 登録済みフラグ

    def _get_api_client(self):
        """ProductionServerAPIClient を取得（遅延初期化）"""
        if self._api_client is None:
            try:
                from production_server_api_client import get_production_api_client
                self._api_client = get_production_api_client()
            except ImportError as e:
                logger.warning(f"⚠️ ProductionServerAPIClient のインポート失敗: {e}")
                return None
            except Exception as e:
                logger.warning(f"⚠️ ProductionServerAPIClient の初期化失敗: {e}")
                return None
        return self._api_client

    def _ensure_websub_registered(self):
        """
        必要なら WebSub サーバーの /register に購読登録を 1 回だけ投げる。

        - settings.env / 環境変数 から:
          - WEBSUB_CLIENT_ID
          - WEBSUB_CALLBACK_URL
          を読み込む前提。
        """
        if self._websub_registered:
            return

        import os

        clientid = os.getenv("WEBSUB_CLIENT_ID")
        callbackurl = os.getenv("WEBSUB_CALLBACK_URL")

        if not clientid or not callbackurl:
            logger.warning(
                "⚠️ WebSub register をスキップ: "
                "WEBSUBCLIENTID または WEBSUBCALLBACKURL が未設定です"
            )
            return

        api_client = self._get_api_client()
        if api_client is None:
            logger.error("❌ WebSub register をスキップ: ProductionServerAPIClient が利用不可です")
            return

        # ProductionServerAPIClient 側の /register 呼び出しメソッドを利用
        try:
            ok = api_client.register_websub_client(
                clientid=clientid,
                channelid=self.channel_id,
                callbackurl=callbackurl,
            )
        except AttributeError:
            # メソッドがまだ実装されていないなど
            logger.error("❌ WebSub register 失敗: register_websub_client メソッドが見つかりません")
            return

        if ok:
            # debugモードに応じたログ出力
            debug_mode = os.getenv("DEBUG_MODE", "false").lower() == "true"
            if debug_mode:
                logger.info(
                    f"✅ WebSub register 成功: clientid={clientid}, "
                    f"channelid={self.channel_id}, callbackurl={callbackurl}"
                )
            else:
                logger.info("✅ WebSub register 成功: websubサーバーへの登録に成功しました")
            self._websub_registered = True
        else:
            logger.warning("⚠️ WebSub register が失敗しました（ログを確認してください）")

    def fetch_feed(self) -> List[Dict]:
        """
        WebSub（ProductionServerAPI）からビデオ情報を取得・パース

        Returns:
            新着動画のリスト（最新順）
        """
        try:
            # まず WebSub 登録を保証する（成功すれば以降の呼び出しではスキップ）
            self._ensure_websub_registered()

            api_client = self._get_api_client()
            if api_client is None:
                logger.error("❌ ProductionServerAPIClient が利用不可（WebSub経由の取得失敗）")
                return []

            youtube_logger = logging.getLogger("YouTubeLogger")
            logger.debug(f"📡 WebSub から動画情報を取得します（チャンネル: {self.channel_id}）")

            # ProductionServerAPI から動画を取得
            items = api_client.get_websub_videos(
                channel_id=self.channel_id,
                limit=15,  # 最新 15 件まで
            )

            if not items:
                youtube_logger.debug("ℹ️ WebSub から動画情報を取得できませんでした")
                return []

            videos = []
            for item in items:
                try:
                    # API レスポンスから必要な情報を抽出
                    video_id = item.get("video_id", "")
                    title = item.get("title", "（タイトル不明）")
                    video_url = (
                        item.get("video_url")
                        or item.get("url")
                        or f"https://www.youtube.com/watch?v={video_id}"
                    )
                    published_at = item.get("published_at", "")
                    channel_name = item.get("channel_name", "")

                    if not video_id:
                        logger.warning(f"⚠️ video_id が不正です。アイテムをスキップします: {item}")
                        continue

                    # ★ 重要: WebSub から取得した published_at は JST 形式（またはUTC）
                    # 形式を統一するため、必要に応じて JST に変換
                    published_at_jst = self._ensure_jst_format(published_at)

                    video = {
                        "video_id": video_id,
                        "title": title,
                        "video_url": video_url,
                        "published_at": published_at_jst,
                        "channel_name": channel_name,
                    }
                    videos.append(video)

                except Exception as e:
                    logger.warning(f"⚠️ WebSub アイテムのパース失敗: {e}")
                    continue

            youtube_logger.info(f"📡 WebSub から {len(videos)} 個の動画を取得しました")
            return videos

        except Exception as e:
            logger.error(f"❌ WebSub 取得に失敗しました: {e}")
            return []

    def _ensure_jst_format(self, published_at: str) -> str:
        """
        published_at を JST 形式に統一

        Args:
            published_at: 日時文字列（UTC またはISO形式）

        Returns:
            JST 形式の日時文字列
        """
        if not published_at:
            return ""

        try:
            # 既に JST 形式か確認（+09:00 または Z でなければ JST と仮定）
            if "+09:00" in published_at or published_at.endswith("+9:00"):
                return published_at

            # UTC → JST 変換
            utc_time = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
            jst_time = utc_time.astimezone(timezone(timedelta(hours=9))).replace(tzinfo=None)
            published_at_jst = jst_time.isoformat()
            logger.debug(f"📡 WebSub 日時を JST に変換: {published_at} → {published_at_jst}")
            return published_at_jst

        except Exception as e:
            logger.warning(f"⚠️ WebSub 日時の JST 変換失敗、元の値を使用: {e}")
            return published_at

    def save_to_db(self, database) -> int:
        """
        WebSub から取得した動画を DB に保存

        ⚠️ NOTE: 新規動画の画像ダウンロード・保存は
        thumbnails/youtube_thumb_utils.py の YouTubeThumbPlugin で実行されます。

        ★ v3.3.0+ YouTube API優先: WebSub登録後、YouTube API で最新情報を確認し、
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

        youtube_logger.info(f"[YouTube WebSub] 取得した {len(videos)} 個の動画を DB に照合しています...")

        # 除外動画リストを取得
        try:
            from deleted_video_cache import get_deleted_video_cache

            deleted_cache = get_deleted_video_cache()
        except ImportError:
            youtube_logger.warning("deleted_video_cache モジュールが見つかりません")
            deleted_cache = None

        # YouTube API プラグインを取得（API有効時のみ）
        youtube_api_plugin = None
        try:
            from plugin_manager import get_plugin_manager
            plugin_mgr = get_plugin_manager()
            youtube_api_plugin = plugin_mgr.get_plugin("youtube_api_plugin")
            if youtube_api_plugin and youtube_api_plugin.is_available():
                youtube_logger.debug(
                    "✅ YouTube API プラグイン が利用可能です（WebSub の情報を API で確認します）"
                )
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
                # 除外動画リスト確認
                if deleted_cache and deleted_cache.is_deleted(video["video_id"], source="youtube"):
                    youtube_logger.info(
                        f"⏭️ 除外動画リスト登録済みのため、スキップします: {video['title']}"
                    )
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
                                    utc_time = datetime.fromisoformat(
                                        api_published_at.replace("Z", "+00:00")
                                    )
                                    jst_time = utc_time.astimezone(
                                        timezone(timedelta(hours=9))
                                    ).replace(tzinfo=None)
                                    api_published_at_jst = jst_time.isoformat()
                                    api_scheduled_start_time = api_published_at_jst
                                    youtube_logger.info(
                                        f"📡 API確認: scheduledStartTime を使用（UTC→JST変換）:"
                                        f" {api_published_at} → {api_published_at_jst}"
                                    )
                                except Exception as e:
                                    api_scheduled_start_time = api_published_at
                                    youtube_logger.warning(
                                        f"⚠️ UTC→JST変換失敗、元の値を使用: {e}"
                                    )
                            elif live_details.get("actualStartTime"):
                                api_published_at = live_details["actualStartTime"]
                                # UTC から JST に変換
                                try:
                                    utc_time = datetime.fromisoformat(
                                        api_published_at.replace("Z", "+00:00")
                                    )
                                    jst_time = utc_time.astimezone(
                                        timezone(timedelta(hours=9))
                                    ).replace(tzinfo=None)
                                    api_published_at_jst = jst_time.isoformat()
                                    api_scheduled_start_time = api_published_at_jst
                                    youtube_logger.info(
                                        f"📡 API確認: actualStartTime を使用（UTC→JST変換）:"
                                        f" {api_published_at} → {api_published_at_jst}"
                                    )
                                except Exception as e:
                                    api_scheduled_start_time = api_published_at
                                    youtube_logger.warning(
                                        f"⚠️ UTC→JST変換失敗、元の値を使用: {e}"
                                    )
                            elif snippet.get("publishedAt"):
                                api_published_at = snippet["publishedAt"]
                                youtube_logger.debug(
                                    f"📡 API確認: publishedAt を使用: {api_published_at}"
                                )
                    except Exception as e:
                        youtube_logger.debug(f"⚠️ YouTube API での詳細取得失敗: {e}")

                # 最終的に使用する published_at を決定
                final_published_at = (
                    api_scheduled_start_time if api_scheduled_start_time else video["published_at"]
                )

                is_new = database.insert_video(
                    video_id=video["video_id"],
                    title=video["title"],
                    video_url=video["video_url"],
                    published_at=final_published_at,
                    channel_name=video["channel_name"],
                    thumbnail_url=thumbnail_url,
                    source="youtube",
                )

                if is_new:
                    saved_count += 1
                    youtube_logger.debug(f"[YouTube WebSub] 新規動画を保存: {video['title']}")
                else:
                    existing_count += 1
                    # 既存動画の場合、API データで published_at を上書き（★ 重要: API が WebSub より優先）
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

        summary = f"新規 {saved_count} 件 / 既存 {existing_count} 件"
        if blacklist_skip_count > 0:
            summary += f" / 除外 {blacklist_skip_count} 件"
        youtube_logger.info(f"[YouTube WebSub] 保存結果: {summary}")

        return saved_count

    def poll_videos(self):
        """WebSub からポーリングし、キャッシュを更新"""
        videos = self.fetch_feed()
        for video in videos:
            video_id = video['video_id']
            if video_id not in self.deleted_cache:
                self.db.insert_video(video_id, video['title'], video['video_url'], video['published_at'], video['channel_name'])
                # キャッシュ更新を追加
                self.plugin.update_video_detail_cache(video_id, video)


def get_youtube_websub(channel_id: str) -> YouTubeWebSub:
    """YouTubeWebSub インスタンスを取得するヘルパー"""
    return YouTubeWebSub(channel_id)
