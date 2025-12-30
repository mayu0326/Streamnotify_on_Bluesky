# -*- coding: utf-8 -*-

"""
YouTubeLive ポーリング層

LIVE 動画の状態遷移を監視し、イベントを発火
"""

import logging
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime, timedelta

logger = logging.getLogger("AppLogger")

__author__ = "mayuneco(mayunya)"
__copyright__ = "Copyright (C) 2025 mayuneco(mayunya)"
__license__ = "GPLv2"


class YouTubeLivePoller:
    """
    ポーリング層 - LIVE 動画の状態を監視し、状態遷移イベントを発火

    【責務】
    - DB 内の upcoming/live/completed 動画をポーリング
    - YouTubeLive 専用キャッシュを活用して API 呼び出しを削減
    - API から最新データを取得（キャッシュ優先）
    - 前回状態（DB）と新状態（API）を比較
    - 状態遷移（live_started, live_ended, archive_available, status_changed）を検出
    - イベント発火とキャッシュ更新を実行

    【キャッシュ戦略】
    - _get_video_detail_with_cache() で「キャッシュ優先 → API」の統一フロー実装
    - 初回取得時に LIVE 動画をキャッシュに登録
    - 状態変化に応じてキャッシュを更新：
      - LIVE 開始/update_cache_entry() で更新
      - LIVE 終了/mark_as_ended_in_cache() で ended 状態に
      - アーカイブ化/cache_manager.remove_video() で削除

    【責務 OUT】
    - 分類判定 → YouTubeLiveClassifier.classify() で実装
    - 自動投稿判定 → YouTubeLiveAutoPoster._should_autopost_event() で実装
    - DB/キャッシュの読み書き詳細 → YouTubeLiveStore で実装
    - キャッシュを使うかどうかの判断は Poller が管理（Store は単なる委譲先）

    状態比較ロジックはここに集約される。
    """

    def __init__(self, classifier=None, store=None, api_plugin=None, config=None):
        """
        初期化

        Args:
            classifier: YouTubeLiveClassifier インスタンス
            store: YouTubeLiveStore インスタンス
            api_plugin: YouTubeAPIPlugin インスタンス
            config: Config オブジェクト
        """
        self.classifier = classifier
        self.store = store
        self.api_plugin = api_plugin
        self.config = config

        # イベントリスナー登録用
        self._event_listeners = {
            "live_started": [],
            "live_ended": [],
            "archive_available": [],
            "status_changed": []
        }

    def register_listener(self, event_name: str, callback: Callable) -> bool:
        """
        イベントリスナーを登録

        Args:
            event_name: イベント名（"live_started", "live_ended", "archive_available", "status_changed"）
            callback: コールバック関数 fn(video_id, video_data)

        Returns:
            登録成功フラグ
        """
        if event_name not in self._event_listeners:
            logger.warning(f"⚠️ 未知のイベント: {event_name}")
            return False

        self._event_listeners[event_name].append(callback)
        logger.debug(f"✅ リスナー登録: {event_name}")
        return True

    def _emit_event(self, event_name: str, video_id: str, video_data: Dict[str, Any]) -> None:
        """
        イベントを発火

        登録されたすべてのリスナーを呼び出す

        Args:
            event_name: イベント名
            video_id: 動画ID
            video_data: 動画データ
        """
        logger.debug(f"📢 イベント発火: {event_name} ({video_id})")

        for callback in self._event_listeners.get(event_name, []):
            try:
                callback(video_id, video_data)
            except Exception as e:
                logger.error(f"❌ リスナー実行エラー: {event_name} - {e}")

    # ==================== キャッシュ対応ヘルパー ====================

    def _get_video_detail_with_cache(self, video_id: str, bypass_cache: bool = False) -> Optional[Dict[str, Any]]:
        """
        YouTubeLive 専用キャッシュ + YouTube Data API をラップした取得関数

        優先順位:
        1) bypass_cache=True の場合、キャッシュをスキップして API から直接取得
        2) api_plugin._get_cached_video_detail(video_id) でキャッシュを確認
        3) キャッシュがなければ api_plugin._fetch_video_detail(video_id) で取得
        4) 初回取得した詳細が LIVE（特に upcoming）であれば、
           キャッシュに登録（初期化時の登録）

        Args:
            video_id: 動画ID
            bypass_cache: キャッシュをバイパスして API から直接取得するか

        Returns:
            YouTube API 詳細データ、取得失敗時 None
        """
        if self.api_plugin is None:
            logger.error("❌ api_plugin が未設定です")
            return None

        try:
            # ★ ステップ 0: キャッシュバイパスオプション
            if bypass_cache:
                logger.debug(f"🔄 キャッシュをバイパスして API から取得: {video_id}")
                api_details = self.api_plugin._fetch_video_detail_bypass_cache(video_id)
                if api_details is None:
                    logger.warning(f"⚠️ API 詳細取得失敗 (bypass): {video_id}")
                    return None
                return api_details

            # ステップ 1: キャッシュを確認
            cached_details = self.api_plugin._get_cached_video_detail(video_id)
            if cached_details is not None:
                logger.debug(f"💾 キャッシュヒット: {video_id}")
                return cached_details

            # ステップ 2: API から取得
            logger.debug(f"🔄 API 取得: {video_id}")
            api_details = self.api_plugin._fetch_video_detail(video_id)
            if api_details is None:
                logger.debug(f"⚠️ API 詳細取得失敗: {video_id}")
                return None

            # ステップ 3: LIVE（特に upcoming）であればキャッシュに登録
            try:
                content_type, live_status, _ = self.classifier.classify(api_details)
                if content_type == "live":
                    # LIVE 動画の場合、DB データを取得して一緒にキャッシュに登録
                    db_video = self.store.get_video_by_id(video_id)
                    if db_video:
                        self.store.add_live_video_to_cache(video_id, db_video, api_details)
                        logger.debug(f"💾 キャッシュ登録: {video_id} (content_type=live)")
            except Exception as e:
                logger.warning(f"⚠️ キャッシュ登録スキップ: {video_id} - {e}")

            return api_details

        except Exception as e:
            logger.error(f"❌ 動画詳細取得エラー: {video_id} - {e}")
            return None

    def _get_videos_detail_with_cache_batch(self, video_ids: List[str], bypass_cache: bool = False) -> Dict[str, Dict[str, Any]]:
        """
        ★ バッチ処理用ラップ: キャッシュ + YouTube Data API バッチ取得

        複数の動画IDに対して、キャッシュ優先でデータを取得します。
        キャッシュにない分だけ API バッチ呼び出しを行い、API コストを削減します。

        実装戦略:
        1. bypass_cache=True の場合、全ビデオを API から直接取得
        2. キャッシュから取得可能な video_id を抽出
        3. キャッシュミスの video_id をリストアップ
        4. キャッシュミス分を fetch_video_details_batch() で一括取得（1ユニット/50本）
        5. キャッシュヒット + API 結果をマージして返却

        Args:
            video_ids: 取得対象の動画ID リスト
            bypass_cache: キャッシュをバイパスして API から直接取得するか

        Returns:
            {video_id: details} の辞書（キャッシュと API結果を統合）
        """
        if not video_ids:
            return {}

        if self.api_plugin is None:
            logger.error("❌ api_plugin が未設定です")
            return {}

        results = {}

        # ★ ステップ 0: キャッシュバイパスオプション
        if bypass_cache:
            logger.debug(f"🔄 キャッシュをバイパスして API から直接取得: {len(video_ids)} 件")
            try:
                api_results = self.api_plugin.fetch_video_details_batch(video_ids)
                return api_results
            except Exception as e:
                logger.error(f"❌ バッチ API 取得失敗: {e}")
                return {}

        cache_hits = []
        cache_misses = []

        # ★ ステップ 1: キャッシュを確認
        for video_id in video_ids:
            cached_details = self.api_plugin._get_cached_video_detail(video_id)
            if cached_details is not None:
                results[video_id] = cached_details
                cache_hits.append(video_id)
            else:
                cache_misses.append(video_id)

        logger.debug(f"📦 バッチ処理: キャッシュヒット={len(cache_hits)}, API取得={len(cache_misses)}")

        # ★ ステップ 2: キャッシュミス分を API バッチ取得（1 ユニット/50本）
        if cache_misses:
            try:
                api_results = self.api_plugin.fetch_video_details_batch(cache_misses)
                results.update(api_results)

                # キャッシュヒット時と同様、LIVE 動画をキャッシュに登録
                for video_id, details in api_results.items():
                    try:
                        content_type, live_status, _ = self.classifier.classify(details)
                        if content_type == "live":
                            db_video = self.store.get_video_by_id(video_id)
                            if db_video:
                                self.store.add_live_video_to_cache(video_id, db_video, details)
                                logger.debug(f"💾 キャッシュ登録: {video_id} (バッチ API)")
                    except Exception as e:
                        logger.warning(f"⚠️ キャッシュ登録スキップ: {video_id} - {e}")

            except Exception as e:
                logger.error(f"❌ バッチ API 呼び出しエラー: {e}")

        logger.debug(f"📦 バッチ処理完了: 合計 {len(results)} 件取得")
        return results

    def poll_unclassified_videos(self) -> int:
        """
        未分類の動画を取得して分類（★ バッチ処理版）

        RSS 登録直後で未分類の動画に対して、YouTube API から詳細データを取得し、
        LIVE/Archive/通常動画に分類する。

        バッチ処理により、複数動画を 1 API ユニットで取得し、API コストを削減します。

        Returns:
            分類した動画数
        """
        if self.store is None or self.classifier is None or self.api_plugin is None:
            logger.error("❌ 必要なコンポーネントが未設定です")
            return 0

        try:
            unclassified = self.store.get_unclassified_videos()
            if not unclassified:
                logger.debug("ℹ️ 未分類動画はありません")
                return 0

            # ★ ステップ 1: 未分類動画の video_id リストを収集
            video_ids = [v.get("video_id") for v in unclassified if v.get("video_id")]
            logger.debug(f"📦 バッチ処理開始: 未分類 {len(video_ids)} 件")

            # ★ ステップ 2: バッチで詳細データ取得（キャッシュ + API）
            details_map = self._get_videos_detail_with_cache_batch(video_ids)

            # ★ ステップ 3: 分類と DB 更新を実行
            classified_count = 0
            for video in unclassified:
                video_id = video.get("video_id")
                if not video_id or video_id not in details_map:
                    logger.debug(f"⚠️ 詳細データ取得失敗、スキップ: {video_id}")
                    continue

                try:
                    details = details_map[video_id]

                    # 分類実行
                    content_type, live_status, is_premiere = self.classifier.classify(details)

                    # DB 更新
                    if self.store.update_video_classification(video_id, content_type, live_status):
                        logger.info(f"✅ 分類完了: {video_id} → {content_type}/{live_status}")
                        classified_count += 1

                        # API から取得した published_at で上書き
                        if "snippet" in details and "publishedAt" in details["snippet"]:
                            published_at = details["snippet"]["publishedAt"]
                            try:
                                self.store.database.update_published_at(video_id, published_at)
                            except Exception as e:
                                logger.warning(f"⚠️ published_at 更新失敗: {video_id} - {e}")

                except Exception as e:
                    logger.error(f"❌ 分類処理エラー: {video_id} - {e}")
                    continue

            logger.info(f"📋 未分類動画分類完了: {classified_count}/{len(unclassified)}件")
            return classified_count

        except Exception as e:
            logger.error(f"❌ 未分類動画ポーリングエラー: {e}")
            return 0

    def poll_live_status(self) -> Dict[str, Any]:
        """
        LIVE 動画の状態を定期的にポーリング（★ バッチ処理版）

        DB に登録されている upcoming/live/completed 動画に対して、
        最新の状態を API から取得し、状態遷移を検出。

        バッチ処理により、複数動画を 1 API ユニットで取得し、API コストを削減します。

        Returns:
            Dict: {
                "total_polled": int,
                "live_started": int,
                "live_ended": int,
                "archived": int,
                "status_changed": int
            }
        """
        if self.store is None or self.classifier is None or self.api_plugin is None:
            logger.error("❌ 必要なコンポーネントが未設定です")
            return {
                "total_polled": 0,
                "live_started": 0,
                "live_ended": 0,
                "archived": 0,
                "status_changed": 0
            }

        results = {
            "total_polled": 0,
            "live_started": 0,
            "live_ended": 0,
            "archived": 0,
            "status_changed": 0
        }

        try:
            # DB から LIVE 関連動画を取得
            upcoming_videos = self.store.get_videos_by_live_status("upcoming")
            live_videos = self.store.get_videos_by_live_status("live")
            completed_videos = self.store.get_videos_by_live_status("completed")

            all_videos = upcoming_videos + live_videos + completed_videos
            logger.debug(f"📊 ポーリング対象: upcoming={len(upcoming_videos)}, live={len(live_videos)}, completed={len(completed_videos)}")

            if not all_videos:
                logger.debug("ℹ️ ポーリング対象の LIVE 動画はありません")
                return results

            # ★ ステップ 1: すべての LIVE 関連動画の video_id リストを収集
            video_ids = [v.get("video_id") for v in all_videos if v.get("video_id")]
            logger.debug(f"📦 バッチ処理開始: LIVE 動画 {len(video_ids)} 件")

            # ★ ステップ 2: バッチで詳細データ取得（キャッシュ + API）
            # ⭐ upcoming/live は最新データが必須のため bypass_cache=True
            has_active_live = len(upcoming_videos) > 0 or len(live_videos) > 0
            bypass_cache = has_active_live  # upcoming/live がある場合は必ず最新データを取得
            details_map = self._get_videos_detail_with_cache_batch(video_ids, bypass_cache=bypass_cache)

            # ★ ステップ 3: 状態遷移検出と処理
            for video in all_videos:
                video_id = video.get("video_id")
                if not video_id or video_id not in details_map:
                    logger.debug(f"⚠️ 詳細データ取得失敗、スキップ: {video_id}")
                    continue

                try:
                    details = details_map[video_id]

                    # 分類（最新状態取得）
                    new_content_type, new_live_status, is_premiere = self.classifier.classify(details)

                    # ★ 状態遷移検出
                    events = self._detect_state_transitions(video, new_content_type, new_live_status)

                    results["total_polled"] += 1

                    # イベント発火
                    if events["is_live_started"]:
                        results["live_started"] += 1
                        self._emit_event("live_started", video_id, video)
                        logger.info(f"🔴 ライブ配信開始を検出: {video_id}")
                        # キャッシュ更新: LIVE 開始時
                        if new_content_type == "live":
                            self.store.update_cache_entry(video_id, details)

                    if events["is_live_ended"]:
                        results["live_ended"] += 1
                        self._emit_event("live_ended", video_id, video)
                        logger.info(f"🔴 ライブ配信終了を検出: {video_id}")
                        # キャッシュ更新: LIVE 終了時（キャッシュ内で ended にマーク）
                        self.store.mark_as_ended_in_cache(video_id)

                    if events["is_archived"]:
                        results["archived"] += 1
                        self._emit_event("archive_available", video_id, video)
                        logger.info(f"📹 アーカイブ公開を検出: {video_id}")
                        # キャッシュ削除: アーカイブ化時（LIVE キャッシュは不要になる）
                        try:
                            if self.store and self.store.cache_manager:
                                self.store.cache_manager.remove_video(video_id)
                                logger.debug(f"💾 キャッシュ削除: {video_id} (アーカイブ化)")
                        except Exception as e:
                            logger.warning(f"⚠️ キャッシュ削除失敗: {video_id} - {e}")

                    if events["status_changed"]:
                        results["status_changed"] += 1
                        # DB 更新
                        self.store.update_video_classification(video_id, new_content_type, new_live_status)
                        # キャッシュ更新: その他の状態変化時
                        if new_content_type == "live":
                            self.store.update_cache_entry(video_id, details)

                except Exception as e:
                    logger.error(f"❌ ポーリング処理エラー: {video_id} - {e}")
                    continue

            # キャッシュクリア（期限切れ終了 LIVE を削除）
            try:
                cleared_count = self.store.clear_ended_videos_from_cache()
                if cleared_count > 0:
                    logger.info(f"🗑️ キャッシュクリア: {cleared_count}個")
            except Exception as e:
                logger.warning(f"⚠️ キャッシュクリア失敗: {e}")

            logger.info(
                f"✅ ポーリング完了: "
                f"total={results['total_polled']}, "
                f"started={results['live_started']}, "
                f"ended={results['live_ended']}, "
                f"archived={results['archived']}, "
                f"changed={results['status_changed']}"
            )

            return results

        except Exception as e:
            logger.error(f"❌ LIVE ポーリングエラー: {e}")
            return results

    def _detect_state_transitions(
        self,
        video: Dict[str, Any],
        new_content_type: str,
        new_live_status: Optional[str]
    ) -> Dict[str, bool]:
        """
        前の状態と新しい状態から遷移イベントを検出（内部メソッド）

        旧状態（DB 内）と新状態（API から取得）を比較して、
        どのイベントを発火するか判定する。

        Args:
            video: DB から取得した現在の動画情報
            new_content_type: API から取得した新しい content_type
            new_live_status: API から取得した新しい live_status

        Returns:
            Dict: {
                "is_live_started": bool,
                "is_live_ended": bool,
                "is_archived": bool,
                "status_changed": bool
            }
        """
        events = {
            "is_live_started": False,
            "is_live_ended": False,
            "is_archived": False,
            "status_changed": False
        }

        if video is None:
            logger.warning(f"⚠️ video が None です")
            return events

        try:
            video_id = video.get("video_id")
            old_content_type = video.get("content_type", "video")
            old_live_status = video.get("live_status")

            logger.debug(
                f"🔍 状態遷移検出: {video_id} "
                f"({old_content_type}/{old_live_status}) → "
                f"({new_content_type}/{new_live_status})"
            )

            # 遷移判定ロジック
            if old_content_type == "video" and new_content_type == "live":
                # 通常動画 → LIVE 配信（初回判定）
                if new_live_status == "upcoming":
                    events["status_changed"] = True
                    logger.debug(f"状態遷移: {video_id} video → live(upcoming)")
                elif new_live_status == "live":
                    events["is_live_started"] = True
                    logger.debug(f"状態遷移: {video_id} video → live(live)")

            elif old_content_type == "live" and new_content_type == "archive":
                # LIVE 配信 → アーカイブ（配信終了 + アーカイブ公開の両方を示す）
                events["is_archived"] = True
                logger.debug(f"状態遷移: {video_id} live → archive")

            elif old_content_type == "live" and new_content_type == "completed":
                # ★ 新規: LIVE 配信 → completed（配信終了・新分類形式）
                # v3.3.0 から content_type が 5カテゴリに統一されたため、このパターンが追加
                events["is_live_ended"] = True
                logger.debug(f"状態遷移: {video_id} live → completed (新分類形式)")

            elif old_content_type == "live" and new_live_status == "completed":
                # LIVE ステータス: live → completed（配信終了）
                if old_live_status != "completed":
                    events["is_live_ended"] = True
                    logger.debug(f"状態遷移: {video_id} live_status={old_live_status} → completed")

            elif old_content_type == "schedule" and new_content_type == "live":
                # ★ 新規: 予約枠 → LIVE 配信中（配信開始）
                if new_live_status == "live":
                    events["is_live_started"] = True
                    logger.debug(f"状態遷移: {video_id} schedule → live")

            else:
                # その他の状態変化
                if old_content_type != new_content_type or old_live_status != new_live_status:
                    events["status_changed"] = True
                    logger.debug(f"状態変化: {video_id} その他の遷移")

            return events

        except Exception as e:
            logger.error(f"❌ 状態遷移検出エラー: {e}")
            return events

    def process_ended_cache_entries(self) -> int:
        """
        キャッシュ内の ended（終了）動画を処理（★ バッチ処理版）

        キャッシュ内で "ended" 状態になった動画（= 配信終了後の LIVE）に対して、
        DB から最新の状態を再取得し、アーカイブ化を確認する。

        バッチ処理により、複数動画を 1 API ユニットで取得し、API コストを削減します。

        Returns:
            処理した動画数
        """
        if self.store is None or self.api_plugin is None:
            logger.error("❌ 必要なコンポーネントが未設定です")
            return 0

        try:
            ended_videos = self.store.get_live_videos_by_status("ended")
            if not ended_videos:
                logger.debug("ℹ️ ended キャッシュエントリがありません")
                return 0

            logger.info(f"📋 ended キャッシュエントリ処理: {len(ended_videos)}個")

            # ★ ステップ 1: ended 動画の video_id リストを収集
            video_ids = [v.get("video_id") for v in ended_videos if v.get("video_id")]
            logger.debug(f"📦 バッチ処理開始: ended 動画 {len(video_ids)} 件")

            # ★ ステップ 2: バッチで詳細データ取得（キャッシュ + API）
            details_map = self._get_videos_detail_with_cache_batch(video_ids)

            # ★ ステップ 3: アーカイブ化確認と処理
            processed_count = 0
            for cache_entry in ended_videos:
                video_id = cache_entry.get("video_id")
                if not video_id or video_id not in details_map:
                    logger.debug(f"⚠️ 詳細データ取得失敗、スキップ: {video_id}")
                    continue

                try:
                    # DB から現在の状態を確認
                    db_video = self.store.get_video_by_id(video_id)
                    if db_video is None:
                        logger.warning(f"⚠️ DB に見つかりません: {video_id}")
                        continue

                    details = details_map[video_id]

                    # 分類
                    new_content_type, new_live_status, _ = self.classifier.classify(details)

                    # アーカイブ化を確認
                    if new_content_type == "archive":
                        # アーカイブ化を検出
                        self.store.update_video_classification(video_id, "archive", None)
                        self._emit_event("archive_available", video_id, db_video)
                        logger.info(f"📹 アーカイブ化を検出: {video_id}")
                        processed_count += 1

                        # キャッシュから削除
                        try:
                            if self.store and self.store.cache_manager:
                                self.store.cache_manager.remove_video(video_id)
                                logger.debug(f"💾 キャッシュ削除: {video_id} (アーカイブ化確認)")
                        except Exception as e:
                            logger.warning(f"⚠️ キャッシュ削除失敗: {video_id} - {e}")

                except Exception as e:
                    logger.error(f"❌ ended エントリ処理エラー: {video_id} - {e}")
                    continue

            logger.info(f"✅ ended 処理完了: {processed_count}/{len(ended_videos)}個")
            return processed_count

        except Exception as e:
            logger.error(f"❌ ended キャッシュ処理エラー: {e}")
            return 0

    def get_statistics(self) -> Dict[str, int]:
        """
        現在の監視対象動画統計

        Returns:
            Dict: {
                "upcoming": int,
                "live": int,
                "completed": int,
                "cached": int
            }
        """
        stats = {
            "upcoming": 0,
            "live": 0,
            "completed": 0,
            "cached": 0
        }

        try:
            if self.store:
                stats["upcoming"] = len(self.store.get_videos_by_live_status("upcoming"))
                stats["live"] = len(self.store.get_videos_by_live_status("live"))
                stats["completed"] = len(self.store.get_videos_by_live_status("completed"))

                if self.store.cache_manager:
                    stats["cached"] = len(self.store.cache_manager.get_live_videos())

            return stats

        except Exception as e:
            logger.error(f"❌ 統計取得エラー: {e}")
            return stats
