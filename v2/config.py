# -*- coding: utf-8 -*-

"""
Stream notify on Bluesky - v2 設定管理

.env から設定を読み込み、バリデーションを行う。
"""

import os
import logging
from dotenv import load_dotenv
from pathlib import Path

logger = logging.getLogger("AppLogger")

__author__ = "mayuneco(mayunya)"
__copyright__ = "Copyright (C) 2025 mayuneco(mayunya)"
__license__ = "GPLv2"

DB_PATH = "data/video_list.db"


class OperationMode:
    """動作モードの定義"""
    NORMAL = "normal"           # 通常モード（収集＋手動投稿）
    AUTO_POST = "auto_post"     # 自動投稿モード（収集＋手動・自動投稿）
    DRY_RUN = "dry_run"         # ドライランモード（デバッグ用途・投稿機能オフ）
    COLLECT = "collect"         # 収集モード（RSS取得のみ・投稿機能オフ）


class Config:
    """アプリケーション設定を管理するクラス"""

    def __init__(self, env_path=".env"):
        """
        初期化

        Args:
            env_path: settings.env ファイルのパス
        """
        load_dotenv(env_path, override=True)
        self.validate()

    def validate(self):
        """設定値をバリデーション"""

        # YouTube チャンネル ID
        self.youtube_channel_id = os.getenv("YOUTUBE_CHANNEL_ID", "").strip()

        # YouTubeAPI連携プラグイン導入フラグ（importlibで自動判定＋APIキー必須）
        try:
            import importlib.util
            plugin_exists = importlib.util.find_spec("plugins.youtube_api_plugin") is not None
        except Exception:
            plugin_exists = False

        self.youtube_api_key = os.getenv("YOUTUBE_API_KEY", "").strip()
        self.youtube_api_plugin_exists = plugin_exists

        if plugin_exists:
            if self.youtube_api_key:
                logger.info("有効なAPIキーが設定されています。")
                logger.info("YouTube連携機能を有効化しました。")
                self.youtube_api_plugin_enabled = True
            else:
                logger.info("有効なAPIキーが設定されていません。")
                logger.info("YouTube連携機能を無効化しました。")
                self.youtube_api_plugin_enabled = False
        else:
            self.youtube_api_plugin_enabled = False
            logger.info("YouTubeAPIプラグインが導入されていません。RSS取得のみで動作します。")

        if not self.youtube_channel_id:
            logger.error("YOUTUBE_CHANNEL_ID が未設定です。settings.env を確認してください。")
            raise ValueError("YOUTUBE_CHANNEL_ID is required")

        # YouTubeAPI未導入時（バリデーション段階ではINFOのみ出力。WARNINGはmain_v2で出力）
        if not plugin_exists:
            logger.info("YouTubeAPI連携プラグインが未導入です。UCから始まるチャンネルIDのみ利用可能です。")
            if not self.youtube_channel_id.startswith("UC"):
                logger.error(f"YouTubeAPI未導入時はUCから始まるIDのみ許可されます。現在のID: {self.youtube_channel_id}")
                raise ValueError("YouTubeAPI未導入時はUCから始まるIDのみ許可されます。設定を確認してください。")

        # Bluesky ユーザー名
        self.bluesky_username = os.getenv("BLUESKY_USERNAME", "").strip()
        if not self.bluesky_username:
            logger.error("BLUESKY_USERNAME が未設定です。settings.env を確認してください。")
            raise ValueError("BLUESKY_USERNAME is required")

        # Bluesky アプリパスワード
        self.bluesky_password = os.getenv("BLUESKY_PASSWORD", "").strip()
        if not self.bluesky_password:
            logger.error("BLUESKY_PASSWORD が未設定です。settings.env を確認してください。")
            raise ValueError("BLUESKY_PASSWORD is required")

        # ポーリング間隔
        try:
            self.poll_interval_minutes = int(os.getenv("POLL_INTERVAL_MINUTES", 10))
            if self.poll_interval_minutes < 5 or self.poll_interval_minutes > 30:
                logger.warning(f"ポーリング間隔が範囲外です (5〜30): {self.poll_interval_minutes}。10分に設定します。")
                self.poll_interval_minutes = 10
        except ValueError:
            logger.warning("POLL_INTERVAL_MINUTES が無効です。10分に設定します。")
            self.poll_interval_minutes = 10

        # Bluesky 投稿フラグ（デフォルト: False = ドライラン）
        post_enabled_str = os.getenv("BLUESKY_POST_ENABLED", "false").strip().lower()
        self.bluesky_post_enabled = post_enabled_str in ("true", "1", "yes", "on")

        # デバッグモード（デフォルト: False）
        debug_mode_str = os.getenv("DEBUG_MODE", "false").strip().lower()
        self.debug_mode = debug_mode_str in ("true", "1", "yes", "on")

        # 動作モードの判定
        db_exists = Path(DB_PATH).exists()
        app_mode = os.getenv("APP_MODE", "normal").strip().lower()

        # 動作モードの決定ロジック
        if not db_exists or app_mode == OperationMode.COLLECT:
            self.operation_mode = OperationMode.COLLECT
        elif app_mode == OperationMode.DRY_RUN:
            self.operation_mode = OperationMode.DRY_RUN
        elif app_mode == OperationMode.AUTO_POST and self.bluesky_post_enabled:
            self.operation_mode = OperationMode.AUTO_POST
        elif app_mode == OperationMode.NORMAL or not self.bluesky_post_enabled:
            self.operation_mode = OperationMode.NORMAL
        else:
            # デフォルトは通常モード
            self.operation_mode = OperationMode.NORMAL

        # 後方互換性のため is_collect_mode を保持
        self.is_collect_mode = (self.operation_mode == OperationMode.COLLECT)

        # 動作モードのログ出力
        self._log_operation_mode()

        # タイムゾーン（オプション）
        self.timezone = os.getenv("TIMEZONE", "system")

        # ニコニコプラグイン導入有無を検出
        try:
            import importlib.util
            self.niconico_plugin_exists = importlib.util.find_spec("plugins.niconico_plugin") is not None
        except Exception:
            self.niconico_plugin_exists = False

        # ニコニコユーザーID（オプション）
        self.niconico_user_id = os.getenv("NICONICO_USER_ID", "").strip()
        if self.niconico_plugin_exists:
            if self.niconico_user_id:
                logger.info("有効なユーザーIDが設定されています。")
                logger.info("ニコニコ連携機能を有効化しました。")
            else:
                logger.info("有効なユーザーIDが設定されていません。")
                logger.info("ニコニコ連携機能を無効化しました。")
        else:
            # バリデーション段階ではINFOのみ
            logger.info("ニコニコプラグインが導入されていません。RSS取得のみで動作します。")

        # ニコニコポーリング間隔（分）
        try:
            self.niconico_poll_interval_minutes = int(os.getenv("NICONICO_POLL_INTERVAL", "10"))
            if self.niconico_poll_interval_minutes < 5 or self.niconico_poll_interval_minutes > 60:
                logger.warning(f"ニコニコポーリング間隔が範囲外です (5〜60): {self.niconico_poll_interval_minutes}。10分に設定します。")
                self.niconico_poll_interval_minutes = 10
        except ValueError:
            logger.warning("NICONICO_POLL_INTERVAL が無効です。10分に設定します。")
            self.niconico_poll_interval_minutes = 10


    def _log_operation_mode(self):
        """現在の動作モードをログに出力"""
        mode_descriptions = {
            OperationMode.NORMAL: "通常モード（収集＋手動投稿）",
            OperationMode.AUTO_POST: "自動投稿モード（収集＋手動・自動投稿）",
            OperationMode.DRY_RUN: "ドライランモード（デバッグ用途・投稿機能オフ）",
            OperationMode.COLLECT: "収集モード（RSS取得のみ・投稿機能オフ）"
        }

        # Bluesky投稿機能の状態を判定
        if self.operation_mode in (OperationMode.COLLECT, OperationMode.DRY_RUN):
            post_status = "無効"
        elif self.bluesky_post_enabled:
            post_status = "有効"
        else:
            post_status = "無効"

        # デバッグモードの状態
        debug_status = "有効" if self.debug_mode else "無効"

        logger.info("=" * 60)
        logger.info(f"動作モード: {mode_descriptions.get(self.operation_mode, self.operation_mode)}")
        logger.info(f"Bluesky投稿機能: {post_status}")
        logger.info(f"デバッグモード: {debug_status}")
        logger.info("=" * 60)

        # モード別の詳細説明
        if self.operation_mode == OperationMode.COLLECT:
            logger.warning("📦 RSS を取得して DB に保存するだけです。Bluesky への投稿は行いません。")
        elif self.operation_mode == OperationMode.DRY_RUN:
            logger.warning("🧪 デバッグモードです。投稿のシミュレーションのみ行い、実際には投稿しません。")
        elif self.operation_mode == OperationMode.NORMAL:
            logger.info("📝 投稿対象をGUIから設定し、手動で投稿を行ってください。")
        elif self.operation_mode == OperationMode.AUTO_POST:
            logger.info("🚀 投稿対象をGUIから設定後、5分間隔で順次自動投稿します。")


def get_config(env_path="settings.env") -> Config:
    """設定オブジェクトを取得"""
    return Config(env_path)
