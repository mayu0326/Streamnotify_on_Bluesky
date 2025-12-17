# -*- coding: utf-8 -*-
"""
ニコニコ動画 RSS取得プラグイン

- ニコニコ動画の新着を監視
- RSS ポーリング方式で実装
- リトライ・タイムアウト対応
- NotificationPlugin 準拠
"""

import os
import logging
import time
import re
from typing import Dict, Any, Optional
from threading import Thread, Event
import feedparser
from socket import timeout as socket_timeout
import requests
import xml.etree.ElementTree as ET
from image_manager import get_image_manager
from thumbnails import get_niconico_ogp_url

from plugin_interface import NotificationPlugin
from database import Database

logger = logging.getLogger("NiconicoLogger")

# 定数
RSS_TIMEOUT = 10  # RSS 取得タイムアウト（秒）
RSS_RETRY_MAX = 3  # リトライ回数
RSS_RETRY_WAIT = 2  # リトライ待機時間（秒）
NICONICO_USER_ID_PATTERN = r'^\d+$'  # ユーザーID は数字のみ


class NiconicoPlugin(NotificationPlugin):
    """ニコニコ動画 RSS取得プラグイン"""

    def __init__(self, user_id: str, poll_interval: int, db: Database, user_name: str = None):
        """
        初期化

        Args:
            user_id: 監視対象のニコニコユーザーID（数字のみ）
            poll_interval: ポーリング間隔（分）
            db: Database インスタンス
            user_name: ニコニコユーザー名（display用。省略時はIDから推測）
        """
        self.user_id = user_id.strip() if user_id else ""
        self.user_name = user_name or os.getenv("NICONICO_USER_NAME", "") or self.user_id
        self.poll_interval_min = max(int(poll_interval), 5)  # 最小 5 分
        self.poll_interval_sec = self.poll_interval_min * 60
        self.db = db
        self.shutdown_event = Event()
        self._monitor_thread = None
        self.last_video_id = None
        self._validation_error = None
        self.image_manager = get_image_manager()

        # バリデーション
        self._validate_user_id()

    def _validate_user_id(self):
        """ユーザーID をバリデーション"""
        if not self.user_id:
            self._validation_error = "ユーザーID が空です"
            logger.warning(f"[バリデーション] {self._validation_error}")
            return

        if not re.match(NICONICO_USER_ID_PATTERN, self.user_id):
            self._validation_error = f"ユーザーID は数字のみである必要があります: {self.user_id}"
            logger.warning(f"[バリデーション] {self._validation_error}")
            return

        logger.debug(f"[バリデーション] ユーザーID OK: {self.user_id}")
        self._validation_error = None

    def is_available(self) -> bool:
        """プラグインが利用可能か判定"""
        return bool(self.user_id and not self._validation_error)

    def get_name(self) -> str:
        return "ニコニコ動画 RSS取得プラグイン"

    def get_version(self) -> str:
        return "0.3.0"

    def get_description(self) -> str:
        return "ニコニコ動画の新着を RSS 監視するプラグイン（リトライ・タイムアウト対応）"

    def start_monitoring(self):
        """監視スレッドを開始"""
        if not self.is_available():
            logger.warning(f"[起動エラー] プラグインが利用不可です: {self._validation_error}")
            return

        if self._monitor_thread is None or not self._monitor_thread.is_alive():
            self.shutdown_event.clear()
            self._monitor_thread = Thread(target=self._monitor_loop, daemon=True)
            self._monitor_thread.start()
            logger.info(f"[監視スレッド開始] ユーザーID={self.user_id}, ポーリング間隔={self.poll_interval_min}分")
        else:
            logger.debug("[監視スレッド] 既に実行中です")

    def stop_monitoring(self):
        """監視スレッドを停止"""
        if self._monitor_thread and self._monitor_thread.is_alive():
            logger.debug("[監視スレッド停止] シグナル送信中...")
            self.shutdown_event.set()
            self._monitor_thread.join(timeout=10)
            logger.info("[監視スレッド停止] 完了")
        else:
            logger.debug("[監視スレッド停止] スレッドが実行していません")

    def _monitor_loop(self):
        """監視ループ（スレッド実行用）"""
        logger.info("[監視ループ] 開始")
        app_logger = logging.getLogger("AppLogger")
        niconico_logger = logging.getLogger("NiconicoLogger")
        while not self.shutdown_event.is_set():
            try:
                logger.info("[ニコニコ] ニコニコ動画から RSS を取得しています...")
                app_logger.info("[ニコニコ] ニコニコ動画から RSS を取得しています...")

                # 動画をチェック
                video_entry = self.get_latest_video_entry()
                if video_entry:
                    if not self.last_video_id or video_entry.get("id") != self.last_video_id:
                        # ニコニコ RSS の取得・照合・判定ログ（新着動画がある場合のみ）
                        niconico_logger.info(f"[ニコニコ RSS] 1 個の動画を DB に照合しています...")

                        video = self._entry_to_video_dict(video_entry)
                        is_new = self.post_video(video)
                        if is_new:
                            niconico_logger.info(f"✅ 1 個の新着動画を保存しました")
                        else:
                            niconico_logger.info(f"ℹ️ 新着動画はありません（既存: 1 個）")
                        self.last_video_id = video_entry.get("id")
                        logger.debug(f"[ラストID更新] video_id={self.last_video_id}")
                    else:
                        logger.debug("[監視] 新着動画なし")
                else:
                    logger.debug("[監視] RSS エントリ取得失敗")

            except Exception as e:
                logger.error(f"[監視ループエラー] {e}", exc_info=True)
                app_logger.error(f"[ニコニコ監視エラー] {e}", exc_info=True)

            # ポーリング間隔待機（割り込み可能）
            logger.debug(f"[待機] {self.poll_interval_min}分間ポーリング待機中...")
            self.shutdown_event.wait(self.poll_interval_sec)

        logger.info("[監視ループ] 終了")

    # ...existing code...

    def get_latest_video_entry(self) -> Optional[Dict[str, Any]]:
        """
        ユーザーの最新動画 RSS エントリを取得（リトライ対応）

        Returns:
            dict または None
        """
        url = f"https://www.nicovideo.jp/user/{self.user_id}/video?rss=2.0"
        logger.debug(f"[RSS取得] 動画: {url}")
        return self._fetch_rss_with_retry(url, kind="video")

    def _fetch_rss_with_retry(self, url: str, kind: str = "video") -> Optional[Dict[str, Any]]:
        """
        RSS を取得（リトライロジック付き）

        Args:
            url: RSS フィード URL
            kind: "video"

        Returns:
            dict または None
        """
        for attempt in range(1, RSS_RETRY_MAX + 1):
            try:
                logger.debug(f"[RSS取得試行] {attempt}/{RSS_RETRY_MAX}")

                # feedparser は timeout パラメータに対応していないため、
                # 基本的なエラーハンドリングのみ実装
                feed = feedparser.parse(url)

                # feedparser のエラーチェック
                if hasattr(feed, 'bozo_exception') and feed.bozo_exception:
                    raise feed.bozo_exception

                if feed.entries:
                    entry = feed.entries[0]
                    result = {
                        "id": entry.get("id", ""),
                        "title": entry.get("title", ""),
                        "link": entry.get("link", ""),
                        "published": entry.get("published", ""),
                        "author": entry.get("author", ""),
                    }
                    logger.debug(f"[RSS取得成功] entry_id={result.get('id')}")
                    return result

                logger.debug(f"[RSS取得] エントリなし（フィード空）")
                return None

            except Exception as e:
                logger.warning(f"[RSS取得エラー] 試行 {attempt}/{RSS_RETRY_MAX}: {type(e).__name__}: {e}")

                if attempt < RSS_RETRY_MAX:
                    logger.debug(f"[リトライ待機] {RSS_RETRY_WAIT}秒待機中...")
                    time.sleep(RSS_RETRY_WAIT)
                else:
                    logger.error(f"[RSS取得失敗] 最大リトライ回数に達しました")
                    return None

        return None

    def _entry_to_video_dict(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """
        RSS エントリを video dict に変換（動画専用）

        Args:
            entry: feedparser エントリ

        Returns:
            video dict（DB insert 用）
        """
        import re
        from email.utils import parsedate_to_datetime
        title = entry.get("title", "")
        link = entry.get("link", "")
        published = entry.get("published", "")
        # ニコニコのRSSにはauthorフィールドがないため、設定済みのユーザー名を使用
        author = self.user_name

        # ニコニコ動画IDをlinkから抽出
        video_id = ""
        m = re.search(r'/watch/([a-z]{2}\d+)', link)
        if m:
            video_id = m.group(1)
        else:
            # フォールバック: idフィールドの末尾がsm等ならそれを使う
            id_field = entry.get("id", "")
            m2 = re.search(r'/watch/([a-z]{2}\d+)', id_field)
            if m2:
                video_id = m2.group(1)
            else:
                video_id = id_field  # それでもなければそのまま

        # publishedをISO8601に変換
        published_at = published
        try:
            dt = parsedate_to_datetime(published)
            published_at = dt.isoformat()
        except Exception:
            pass

        video = {
            "video_id": video_id,
            "title": title,
            "video_url": link,
            "published_at": published_at,
            "channel_name": author,
            "content_type": "video",
            "source": "niconico",
            "thumbnail_url": self._fetch_thumbnail_url(video_id) or "",
        }

        logger.debug(f"[エントリ変換] video_id={video_id}, title={title}, author={author}")
        return video

    def post_video(self, video: Dict[str, Any]) -> bool:
        """
        ビデオ情報を DB に保存

        Args:
            video: {video_id, title, video_url, published_at?, channel_name?, content_type?, source?}

        Returns:
            bool: 成功時 True（新規登録）、既存の場合 False
        """
        video_id = video.get("video_id")
        if not video_id:
            logger.error("[post_video] video_id が指定されていません")
            return False

        title = video.get("title", "[ニコニコ]")
        video_url = video.get("video_url", "")
        published_at = video.get("published_at", "")
        channel_name = video.get("channel_name", "")
        content_type = video.get("content_type", "video")
        thumbnail_url = video.get("thumbnail_url", "")

        try:
            # database モジュールのロガーを一時的に NiconicoLogger に切り替え
            import database as db_module
            original_db_logger = db_module.logger
            niconico_logger = logging.getLogger("NiconicoLogger")
            db_module.logger = niconico_logger

            try:
                logger.debug(f"[DB保存] video_id={video_id}, title={title}")
                is_new = self.db.insert_video(
                    video_id=video_id,
                    title=title,
                    video_url=video_url,
                    published_at=published_at,
                    channel_name=channel_name,
                    thumbnail_url=thumbnail_url,
                    content_type=content_type,
                    source="niconico",
                )
                if is_new:
                    logger.debug(f"[DB保存成功] video_id={video_id}")
                    # 新規登録の場合のみ画像処理を実行
                    if thumbnail_url:
                        self._ensure_image_download(video_id, thumbnail_url)
                else:
                    logger.debug(f"[DB保存] 既存レコード（スキップ）: video_id={video_id}")
                return is_new
            finally:
                # ロガーを元に戻す
                db_module.logger = original_db_logger
        except Exception as e:
            logger.error(f"[DB保存エラー] {type(e).__name__}: {e}", exc_info=True)
            return False

    def _ensure_image_download(self, video_id: str, thumbnail_url: str):
        """DBに画像ファイルがなければダウンロードして登録"""
        try:
            # database と image_manager のロガーを一時的に NiconicoLogger に切り替え
            import database as db_module
            import image_manager as im_module

            original_db_logger = db_module.logger
            original_im_logger = im_module.logger
            niconico_logger = logging.getLogger("NiconicoLogger")
            db_module.logger = niconico_logger
            im_module.logger = niconico_logger

            try:
                videos = self.db.get_all_videos()
                video = next((v for v in videos if v.get("video_id") == video_id), None)
                if video and video.get("image_filename"):
                    return

                filename = self.image_manager.download_and_save_thumbnail(
                    thumbnail_url=thumbnail_url,
                    site="Niconico",
                    video_id=video_id,
                    mode="import",
                )
                if filename:
                    self.db.update_image_info(video_id, image_mode="import", image_filename=filename)
                    logger.info(f"[自動画像取得] {video_id} -> {filename}")
            finally:
                # ロガーを元に戻す
                db_module.logger = original_db_logger
                im_module.logger = original_im_logger
        except Exception as e:
            logger.warning(f"[自動画像取得失敗] {video_id}: {e}")

    def _fetch_thumbnail_url(self, video_id: str) -> Optional[str]:
        """ニコニコ動画のOGP画像URLを取得（常にOGPを使用）"""
        if not video_id:
            return None

        ogp_url = get_niconico_ogp_url(video_id)
        if ogp_url:
            return ogp_url
        return None

    def on_interval(self):
        """定期実行（プラグインマネージャから呼び出される場合用）"""
        # 監視スレッドで処理しているため、ここでは何もしない
        pass
