# -*- coding: utf-8 -*-
"""
YouTubeLive 統合ハブ（4層モジュール統合版）

4層アーキテクチャの統合ポイント：
  - YouTubeLiveClassifier: 分類ロジック
  - YouTubeLiveStore: DB/キャッシュアクセス
  - YouTubeLivePoller: ポーリング + 遷移検出
  - YouTubeLiveAutoPoster: イベント処理 + 投稿判定

YouTubeLivePlugin（このクラス）の役割：
  - 各4層の初期化とインスタンス生成
  - 依存関係の解決と注入
  - public API の提供（on_enable, poll_live_status など）
  - plugin_manager, config の調整
"""

import os
import sys
import logging
from typing import Dict, Any, Optional
from pathlib import Path

from plugin_interface import NotificationPlugin
from database import Database, get_database
from plugins.youtube_api_plugin import YouTubeAPIPlugin
from youtube_live_cache import get_youtube_live_cache

# プラグインディレクトリを sys.path に追加（内部モジュール読み込み用）
plugin_dir = str(Path(__file__).parent)
if plugin_dir not in sys.path:
    sys.path.insert(0, plugin_dir)

# 4層モジュール
from youtube_live_classifier import YouTubeLiveClassifier
from youtube_live_store import YouTubeLiveStore
from youtube_live_poller import YouTubeLivePoller
from youtube_live_auto_poster import YouTubeLiveAutoPoster

logger = logging.getLogger("AppLogger")

__author__ = "mayuneco(mayunya)"
__copyright__ = "Copyright (C) 2025 mayuneco(mayunya)"
__license__ = "GPLv2"


class YouTubeLivePlugin(NotificationPlugin):
    """
    YouTubeLive 検出・自動投稿統合ハブ

    【責務】
    - YouTubeAPIPlugin から api_key, channel_id, db を取得
    - 4層モジュール（Classifier, Store, Poller, AutoPoster）を初期化
    - 依存注入: plugin_manager, config, db
    - 公開メソッド: on_enable(), poll_live_status(), process_ended_cache_entries()

    【非責務】
    - 分類ロジック（→ YouTubeLiveClassifier）
    - DB/キャッシュ操作（→ YouTubeLiveStore）
    - ポーリングと遷移検出（→ YouTubeLivePoller）
    - イベント処理と投稿判定（→ YouTubeLiveAutoPoster）
    """

    def __init__(self):
        """
        初期化

        依存関係の解決フロー:
        1. YouTubeAPIPlugin（シングルトン）から api_key, channel_id, db を取得
        2. YouTubeLiveStore 初期化（DB + キャッシュへのアクセス）
        3. YouTubeLiveClassifier 初期化（API データ取得）
        4. YouTubeLivePoller 初期化（ポーリング + 遷移検出）
        5. YouTubeLiveAutoPoster 初期化（イベント処理）
        6. Poller に AutoPoster のイベントハンドラを登録
        """
        # ★ ステップ 1: YouTubeAPI プラグインから基本情報を取得
        self.api_plugin = YouTubeAPIPlugin()
        self.api_key = self.api_plugin.api_key
        self.channel_id = self.api_plugin.channel_id
        self.db: Database = self.api_plugin.db

        # ★ ステップ 2: Store 初期化（DB + キャッシュアクセス層）
        self.store = YouTubeLiveStore(
            database=self.db,
            cache_manager=get_youtube_live_cache()
        )

        # ★ ステップ 3: Classifier 初期化（分類層）
        self.classifier = YouTubeLiveClassifier(
            api_plugin=self.api_plugin
        )

        # ★ ステップ 4: Poller 初期化（ポーリング + 遷移検出層）
        self.poller = YouTubeLivePoller(
            classifier=self.classifier,
            store=self.store,
            api_plugin=self.api_plugin
        )

        # ★ ステップ 5: AutoPoster 初期化（投稿判定層）
        self.autoposter = YouTubeLiveAutoPoster(
            store=self.store
        )

        # ★ ステップ 6: イベントリスナー登録
        # （plugin_manager, config は on_enable() 時に注入される）
        self.poller.register_listener("live_started", self.autoposter.on_live_started)
        self.poller.register_listener("live_ended", self.autoposter.on_live_ended)
        self.poller.register_listener("archive_available", self.autoposter.on_archive_available)

        # main_v3.py から注入される
        self.plugin_manager = None
        self.config = None

    def is_available(self) -> bool:
        """プラグイン利用可能か判定"""
        return bool(self.api_key and self.channel_id)

    def get_name(self) -> str:
        return "YouTubeLive 検出プラグイン"

    def get_version(self) -> str:
        return "0.3.0"

    def get_description(self) -> str:
        return "YouTubeライブ/アーカイブ判定を行いDBに格納するプラグイン（4層統合版）"

    def set_plugin_manager(self, pm) -> None:
        """plugin_manager を注入（自動投稿用）

        Args:
            pm: PluginManager インスタンス
        """
        self.plugin_manager = pm
        # AutoPoster に plugin_manager を設定
        if self.autoposter:
            self.autoposter.set_plugin_manager(pm)

    def set_config(self, config) -> None:
        """config を注入（自動投稿設定用）

        Args:
            config: Config インスタンス
        """
        self.config = config
        # AutoPoster に config を設定
        if self.autoposter:
            self.autoposter.set_config(config)
        # Poller に config を設定
        if self.poller:
            self.poller.set_config(config)

    def on_enable(self) -> None:
        """
        プラグイン有効化時に実行

        RSS で登録された未分類動画（content_type="video"）を
        Poller.poll_unclassified_videos() で自動判定する
        """
        logger.info("🔍 YouTubeLive プラグイン (v0.3.0): 初期化開始")

        if not self.is_available():
            logger.warning("⚠️ YouTubeLivePlugin は利用できません（api_key/channel_id 不足）")
            return

        # ★ Poller に委譲: 未分類動画の自動判定
        updated_count = self.poller.poll_unclassified_videos()

        if updated_count > 0:
            logger.info(f"✅ {updated_count} 個の動画を自動判定して更新しました")
        else:
            logger.info("ℹ️ 自動判定結果: 更新対象の動画はありません")

    def poll_live_status(self) -> None:
        """
        メインポーリング処理（定期呼び出し）

        LIVE/upcoming 状態の動画をポーリングし、
        状態遷移を検出して自動投稿を実行する

        【処理フロー】
        1. Store から live_status='upcoming'/'live'/'completed' の動画を取得
        2. 各動画について:
           - Poller._get_video_detail_with_cache() でキャッシュ優先取得
           - Classifier.classify() で分類
           - Poller._detect_state_transitions() で遷移検出
           - 遷移あり → Store で更新
           - イベント発火 → AutoPoster へ
        3. 終了済みキャッシュ処理

        用途: main_v3.py から POLL_INTERVAL_MINUTES ごとに呼ばれる
        """
        if not self.is_available():
            logger.warning("⚠️ YouTubeLivePlugin は利用できません")
            return

        # ★ Poller に完全委譲
        self.poller.poll_live_status()

    def process_ended_cache_entries(self) -> None:
        """
        終了済みキャッシュから未投稿の動画を検出・投稿

        【処理フロー】
        1. キャッシュから status='ended' の動画を取得
        2. DB で posted_to_bluesky フラグを確認
        3. 未投稿なら API でアーカイブを再確認
        4. イベント発火 → AutoPoster へ
        5. キャッシュをクリーンアップ

        用途: 配信終了後のアーカイブ化を検出して未投稿動画を投稿
        """
        if not self.is_available():
            logger.warning("⚠️ YouTubeLivePlugin は利用できません")
            return

        # ★ Poller に委譲
        self.poller.process_ended_cache_entries()

    def post_video(self, video: Dict[str, Any]) -> bool:
        """
        NotificationPlugin インターフェース準拠メソッド

        動画情報を受け取って Bluesky に投稿
        （このプラグインではほぼ使用されない。イベント駆動が主流）

        Args:
            video: 動画情報辞書

        Returns:
            bool: 投稿成功時 True
        """
        if not self.plugin_manager:
            logger.warning("⚠️ plugin_manager が設定されていません")
            return False

        # ★ plugin_manager 経由で Bluesky プラグインに投稿
        try:
            result = self.plugin_manager.post_video_with_enabled_plugins(video)
            return any(result.values()) if result else False
        except Exception as e:
            logger.error(f"❌ 投稿失敗: {e}")
            return False

    def on_disable(self) -> None:
        """プラグイン無効化時に実行"""
        logger.info("🛑 YouTubeLivePlugin を無効化します")


def get_plugin():
    """PluginManager から取得するためのヘルパー"""
    return YouTubeLivePlugin()
