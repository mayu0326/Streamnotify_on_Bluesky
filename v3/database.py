# -*- coding: utf-8 -*-

"""
Stream notify on Bluesky - v3 データベース管理

SQLite データベースの操作を行う。
マルチプロセスアクセス対策：タイムアウト + リトライ
"""

import sqlite3
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger("AppLogger")
post_logger = logging.getLogger("PostLogger")

__author__ = "mayuneco(mayunya)"
__copyright__ = "Copyright (C) 2025 mayuneco(mayunya)"
__license__ = "GPLv2"

DB_PATH = "data/video_list.db"
DB_TIMEOUT = 10
DB_RETRY_MAX = 3

# バリデーション用の許可リスト
VALID_CONTENT_TYPES = {"video", "live", "archive", "none"}
VALID_LIVE_STATUSES = {None, "none", "upcoming", "live", "completed"}


class Database:
    """SQLite データベースを管理するクラス"""

    _instance = None

    def __new__(cls, db_path=DB_PATH):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, db_path=DB_PATH):
        """
        初期化

        Args:
            db_path: データベースファイルのパス
        """
        if hasattr(self, '_initialized') and self._initialized:
            return
        self.db_path = db_path
        self.is_first_run = not Path(db_path).exists()
        self._ensure_directory()
        self._init_db()
        self._migrate_schema()
        self._initialized = True

    def _ensure_directory(self):
        """ディレクトリを作成"""
        os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)

    def _validate_content_type(self, content_type: str) -> str:
        """content_type を検証し、正規化する

        Args:
            content_type: 検証する content_type の値

        Returns:
            正規化されたcontent_type（デフォルト値は "video"）
        """
        if content_type not in VALID_CONTENT_TYPES:
            logger.warning(f"⚠️ 不正な content_type: '{content_type}' → デフォルト値 'video' に置き換えます")
            return "video"
        return content_type

    def _validate_live_status(self, live_status, content_type: str) -> object:
        """live_status を検証し、正規化する

        Args:
            live_status: 検証する live_status の値
            content_type: 対応する content_type

        Returns:
            正規化された live_status
        """
        if live_status not in VALID_LIVE_STATUSES:
            logger.warning(f"⚠️ 不正な live_status: '{live_status}' → None に置き換えます")
            return None

        # content_type="video" で live_status が null 以外の場合は警告
        if content_type == "video" and live_status is not None:
            logger.warning(f"⚠️ content_type='video' で live_status='{live_status}' が設定されています。content_type != 'live' の場合は live_status=None を推奨します")

        return live_status

    def _get_connection(self):
        """タイムアウト付きで DB 接続を取得"""
        conn = sqlite3.connect(self.db_path, timeout=DB_TIMEOUT)
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_db(self):
        """データベースとテーブルを初期化"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS videos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    video_id TEXT UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    video_url TEXT NOT NULL,
                    published_at TEXT NOT NULL,
                    channel_name TEXT,
                    posted_to_bluesky INTEGER DEFAULT 0,
                    selected_for_post INTEGER DEFAULT 0,
                    scheduled_at TEXT,
                    posted_at TEXT,
                    thumbnail_url TEXT,
                    content_type TEXT DEFAULT 'video',
                    live_status TEXT,
                    is_premiere INTEGER DEFAULT 0,
                    is_short INTEGER DEFAULT 0,
                    is_members_only INTEGER DEFAULT 0,
                    image_mode TEXT,
                    image_filename TEXT,
                    source TEXT DEFAULT 'youtube',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.commit()
            conn.close()


        except Exception as e:
            logger.error(f"DB 初期化エラー: {e}")
            raise

    def _migrate_schema(self):
        """既存 DB のスキーマをマイグレーション"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("PRAGMA table_info(videos)")
            columns = {row[1] for row in cursor.fetchall()}

            # AUTOPOST 動画種別フラグ（仕様 v1.0）
            if "is_short" not in columns:
                logger.info("🔄 カラムを追加します: is_short")
                cursor.execute("ALTER TABLE videos ADD COLUMN is_short INTEGER DEFAULT 0")

            if "is_members_only" not in columns:
                logger.info("🔄 カラムを追加します: is_members_only")
                cursor.execute("ALTER TABLE videos ADD COLUMN is_members_only INTEGER DEFAULT 0")

            if "classification_type" not in columns:
                logger.info("🔄 カラムを追加します: classification_type")
                cursor.execute("ALTER TABLE videos ADD COLUMN classification_type TEXT")

            if "broadcast_status" not in columns:
                logger.info("🔄 カラムを追加します: broadcast_status")
                cursor.execute("ALTER TABLE videos ADD COLUMN broadcast_status TEXT")

            conn.commit()
            conn.close()

        except Exception as e:
            logger.error(f"スキーママイグレーションエラー: {e}")
            raise

    def insert_video(self, video_id, title, video_url, published_at, channel_name="", thumbnail_url="", content_type="video", live_status=None, is_premiere=False, source="youtube", skip_dedup=False):
        """
        動画情報を挿入（リトライ付き、YouTube重複排除対応）

        Args:
            video_id: 動画ID
            title: タイトル
            video_url: 動画URL
            published_at: 公開日時
            channel_name: チャンネル名
            thumbnail_url: サムネイルURL
            content_type: コンテンツ種別（"video"/"live"/"archive"/"none"）
            live_status: ライブ配信状態（null/"none"/"upcoming"/"live"/"completed"）
            is_premiere: プレミア配信フラグ
            source: 配信元（"youtube"/"niconico"など）
            skip_dedup: 重複排除をスキップするか（手動追加時 True）
        """
        # バリデーション
        content_type = self._validate_content_type(content_type)
        live_status = self._validate_live_status(live_status, content_type)

        # YouTube重複排除設定を確認（config から読み込み）
        youtube_dedup_enabled = True  # デフォルト: True
        try:
            from config import get_config
            config = get_config("settings.env")
            youtube_dedup_enabled = config.youtube_dedup_enabled
        except Exception:
            pass  # 設定読み込み失敗時はデフォルト値を使用

        # YouTube動画の重複チェック（優先度ロジック適用）
        # ★ skip_dedup=True なら重複チェックをスキップ（手動追加時の強制挿入）
        # ★ youtube_dedup_enabled=False なら重複チェックをスキップ（設定で無効化）
        if not skip_dedup and youtube_dedup_enabled and source == "youtube" and title and channel_name:
            try:
                import sys
                from pathlib import Path
                sys.path.insert(0, str(Path(__file__).parent / 'utils' / 'database'))
                from youtube_dedup_priority import get_video_priority, should_keep_video

                conn = self._get_connection()
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                cursor.execute("""
                    SELECT * FROM videos
                    WHERE source='youtube' AND title=? AND channel_name=?
                """, (title, channel_name))

                existing_videos = [dict(row) for row in cursor.fetchall()]
                conn.close()

                if existing_videos:
                    # 新しい動画の優先度と既存動画の優先度を比較
                    new_video = {
                        'video_id': video_id,
                        'content_type': content_type,
                        'live_status': live_status,
                        'is_premiere': 1 if is_premiere else 0,
                        'published_at': published_at
                    }

                    if not should_keep_video(new_video, existing_videos):
                        logger.debug(f"⏭️ YouTube重複排除: より優先度の高い動画が既に登録されています（{title}）")
                        return False

                    # 優先度が高い場合は既存の低優先度動画を削除
                    existing_priority = max(get_video_priority(v) for v in existing_videos)
                    new_priority = get_video_priority(new_video)

                    if new_priority > existing_priority:
                        # 既存動画から低優先度のものを削除
                        ids_to_delete = [
                            v['id'] for v in existing_videos
                            if get_video_priority(v) < new_priority
                        ]
                        if ids_to_delete:
                            try:
                                from deleted_video_cache import get_deleted_video_cache
                                deleted_cache = get_deleted_video_cache()
                            except ImportError:
                                deleted_cache = None

                            conn = self._get_connection()
                            cursor = conn.cursor()
                            for del_id in ids_to_delete:
                                # video_id を取得してから削除
                                cursor.execute("SELECT video_id FROM videos WHERE id=?", (del_id,))
                                row = cursor.fetchone()
                                if row:
                                    deleted_video_id = row[0]

                                    # DB から削除
                                    cursor.execute("DELETE FROM videos WHERE id=?", (del_id,))
                                    logger.debug(f"✅ 削除: 優先度が低い動画 ID={del_id}, video_id={deleted_video_id}")

                                    # deleted_videos.json に登録
                                    if deleted_cache:
                                        try:
                                            deleted_cache.add_deleted_video(deleted_video_id, source=source)
                                        except Exception as e:
                                            logger.warning(f"削除動画キャッシュへの登録失敗: {e}")

                            conn.commit()
                            conn.close()
                    else:
                        # 優先度が同じか低い場合はスキップ
                        return False

            except ImportError:
                logger.warning("youtube_dedup_priority モジュールが見つかりません")
            except Exception as e:
                logger.warning(f"重複チェック処理でエラー: {e}")
                # エラー時は続行して挿入を試みる

        for attempt in range(DB_RETRY_MAX):
            try:
                conn = self._get_connection()
                cursor = conn.cursor()

                logger.debug(f"  [DEBUG] 挿入前チェック: video_id={video_id}, title={title[:50]}, channel_name={repr(channel_name)}")
                cursor.execute("""
                    INSERT INTO videos (video_id, title, video_url, published_at, channel_name, thumbnail_url, content_type, live_status, is_premiere, source)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (video_id, title, video_url, published_at, channel_name, thumbnail_url, content_type, live_status, 1 if is_premiere else 0, source))

                conn.commit()
                conn.close()
                logger.info(f"動画を保存しました: {title}")
                return True

            except sqlite3.IntegrityError as e:
                conn.close()
                logger.debug(f"⚠️ 動画は既に保存されています: {video_id} (IntegrityError: {e})")
                return False

            except sqlite3.OperationalError as e:
                conn.close()
                if "locked" in str(e).lower() and attempt < DB_RETRY_MAX - 1:
                    logger.debug(f"DB ロック中。{attempt + 1}/{DB_RETRY_MAX} リトライします...")
                    time.sleep(0.5)
                    continue
                else:
                    logger.error(f"❌ DB エラー (Operational): {e}")
                    return False

            except Exception as e:
                logger.error(f"❌ 予期しないエラー ({type(e).__name__}): {e}")
                if 'conn' in locals():
                    conn.close()
                return False

            except Exception as e:
                logger.error(f"動画の保存に失敗しました: {e}")
                return False

        return False

    def get_unposted_videos(self):
        """未投稿の動画を取得"""
        try:
            conn = self._get_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT * FROM videos WHERE posted_to_bluesky = 0
                ORDER BY published_at DESC
            """)

            videos = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return videos

        except Exception as e:
            logger.error(f"未投稿動画の取得に失敗しました: {e}")
            return []

    def get_selected_videos(self):
        """投稿選択された未投稿動画を取得（スケジュール順）"""
        try:
            conn = self._get_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT * FROM videos
                WHERE selected_for_post = 1 AND posted_to_bluesky = 0
                  AND (scheduled_at IS NULL OR scheduled_at <= datetime('now'))
                ORDER BY scheduled_at, published_at
                LIMIT 1
            """)

            result = cursor.fetchone()
            conn.close()
            return dict(result) if result else None

        except Exception as e:
            logger.error(f"選択動画の取得に失敗しました: {e}")
            return None

    def get_all_videos(self):
        """全動画を取得（GUI 用）- すべてのカラムを返す"""
        try:
            conn = self._get_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT id, video_id, published_at, title, posted_to_bluesky,
                       selected_for_post, scheduled_at, posted_at, video_url, channel_name, thumbnail_url,
                       content_type, live_status, is_premiere, source, image_mode, image_filename,
                       classification_type, broadcast_status
                FROM videos
                ORDER BY published_at DESC
            """)

            videos = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return videos

        except Exception as e:
            logger.error(f"全動画の取得に失敗しました: {e}")
            return []

    def get_video_by_id(self, video_id: str) -> dict:
        """
        指定された video_id の動画を取得

        Args:
            video_id: YouTube 動画 ID

        Returns:
            動画情報辞書、見つからない場合は None
        """
        try:
            conn = self._get_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT * FROM videos WHERE video_id = ?
            """, (video_id,))

            result = cursor.fetchone()
            conn.close()
            return dict(result) if result else None

        except Exception as e:
            logger.error(f"動画取得に失敗しました ({video_id}): {e}")
            return None

    def count_unposted_in_lookback(self, lookback_minutes: int) -> int:
        """
        LOOKBACK 時間窓内の未投稿動画数をカウント（AUTOPOST 起動抑止判定用）

        Args:
            lookback_minutes: 何分さかのぼるか

        Returns:
            int: 件数
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # published_at >= now - lookback_minutes AND posted_to_bluesky = 0
            cursor.execute("""
                SELECT COUNT(*) FROM videos
                WHERE posted_to_bluesky = 0
                  AND published_at >= datetime('now', ? || ' minutes')
            """, (f"-{lookback_minutes}",))

            count = cursor.fetchone()[0]
            conn.close()
            return count

        except Exception as e:
            logger.error(f"未投稿動画カウント に失敗しました: {e}")
            return 0

    def get_autopost_candidates(self, config) -> list:
        """
        AUTOPOST の投稿対象となる動画をフィルタリングして取得

        Args:
            config: Config オブジェクト（AUTOPOST 環境変数を含む）

        Returns:
            List[Dict]: 条件を満たす動画リスト
        """
        try:
            conn = self._get_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # 基本 WHERE 条件
            where_clauses = [
                "posted_to_bluesky = 0",
                f"published_at >= datetime('now', '-{config.autopost_lookback_minutes} minutes')"
            ]

            # 動画種別フィルタ（仕様 v1.0 セクション 3）
            # ⚠️ メンバー限定・ショート動画は現在のところ区別が難しいため、非対応扱い
            # 今後の実装時に以下を有効化
            type_conditions = []

            if config.autopost_include_normal:
                # メンバー限定とショート動画を除外して、通常動画のみ投稿
                type_conditions.append("(is_short = 0 AND is_members_only = 0 AND is_premiere = 0)")

            # ⚠️ 以下は非対応のためコメントアウト
            # if config.autopost_include_shorts:
            #     type_conditions.append("(is_short = 1)")
            # if config.autopost_include_member_only:
            #     type_conditions.append("(is_members_only = 1)")

            if config.autopost_include_premiere:
                type_conditions.append("(is_premiere = 1)")

            # どの種別も有効でない場合は空リスト
            if not type_conditions:
                return []

            type_filter = " OR ".join(type_conditions)
            where_clauses.append(f"({type_filter})")

            # DELETE された動画を除外
            from deleted_video_cache import get_deleted_video_cache
            try:
                deleted_cache = get_deleted_video_cache()
                deleted_ids = deleted_cache.get_deleted_video_ids()
                if deleted_ids:
                    placeholders = ",".join("?" * len(deleted_ids))
                    where_clauses.append(f"video_id NOT IN ({placeholders})")
            except ImportError:
                pass  # モジュールなければスキップ

            where_clause = " AND ".join(where_clauses)

            cursor.execute(f"""
                SELECT * FROM videos
                WHERE {where_clause}
                ORDER BY published_at DESC
            """, deleted_ids if 'deleted_ids' in locals() else [])

            videos = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return videos

        except Exception as e:
            logger.error(f"AUTOPOST 対象取得に失敗: {e}")
            return []

    def get_videos_by_live_status(self, live_status: str):
        """
        指定された live_status の動画を取得

        Args:
            live_status: "upcoming" / "live" / "completed"

        Returns:
            List[Dict]: 該当する動画情報リスト
        """
        try:
            conn = self._get_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM videos WHERE live_status = ?
                ORDER BY published_at DESC
                """,
                (live_status,)
            )
            videos = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return videos
        except Exception as e:
            logger.error(f"live_status={live_status} の動画取得に失敗: {e}")
            return []

    def mark_as_posted(self, video_id):
        """動画を投稿済みにマーク"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            posted_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("""
                UPDATE videos SET posted_to_bluesky = 1, posted_at = ? WHERE video_id = ?
            """, (posted_at, video_id))

            conn.commit()
            conn.close()
            post_logger.info(f"投稿済みフラグを更新しました: {video_id} (投稿日時: {posted_at})")
            return True

        except Exception as e:
            logger.error(f"投稿済みフラグの更新に失敗しました: {e}")
            return False

    def is_duplicate_post(self, video_id: str) -> bool:
        """
        重複投稿かどうかをチェック

        同じ動画がすでに投稿されている場合は True を返す

        Args:
            video_id: 動画ID

        Returns:
            bool: 重複投稿の場合 True、初回投稿の場合 False
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT COUNT(*) FROM videos
                WHERE video_id = ? AND posted_to_bluesky = 1
            """, (video_id,))

            count = cursor.fetchone()[0]
            conn.close()

            is_duplicate = count > 0
            if is_duplicate:
                logger.warning(f"⚠️ 重複投稿検知: この動画は既に投稿済みです（{video_id}）")

            return is_duplicate

        except Exception as e:
            logger.error(f"重複チェック中にエラーが発生: {e}")
            return False

    def update_selection(self, video_id, selected: bool, scheduled_at: str = None, image_mode: str = None, image_filename: str = None):
        """動画の投稿選択状態・予約日時・画像指定を更新"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # 動的にSQLを組み立て（後方互換: 画像指定がなければ従来通り）
            sql = "UPDATE videos SET selected_for_post = ?, scheduled_at = ?"
            params = [1 if selected else 0, scheduled_at]
            if image_mode is not None:
                sql += ", image_mode = ?"
                params.append(image_mode)
            if image_filename is not None:
                sql += ", image_filename = ?"
                params.append(image_filename)
            sql += " WHERE video_id = ?"
            params.append(video_id)

            cursor.execute(sql, params)
            conn.commit()
            conn.close()
            # ログはGUI層で出力するため、ここでは出力しない
            return True

        except Exception as e:
            logger.error(f"動画の選択状態の更新に失敗: {e}")
            return False

    def update_thumbnail_url(self, video_id: str, thumbnail_url: str) -> bool:
        """サムネイルURLを更新"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute(
                """
                UPDATE videos
                SET thumbnail_url = ?
                WHERE video_id = ?
                """,
                (thumbnail_url, video_id),
            )

            conn.commit()
            conn.close()
            logger.info(f"✅ サムネイルURL更新: {video_id} -> {thumbnail_url}")
            return True
        except Exception as e:
            logger.error(f"サムネイルURL更新に失敗: {video_id} - {e}")
            return False

    def get_videos_without_image(self):
        """画像が設定されていない動画を取得（サムネイルURLがある動画のみ）"""
        try:
            conn = self._get_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT id, video_id, title, source, thumbnail_url, image_mode, image_filename
                FROM videos
                WHERE thumbnail_url IS NOT NULL
                  AND thumbnail_url != ''
                  AND (image_filename IS NULL OR image_filename = '')
                ORDER BY published_at DESC
            """)

            videos = [dict(row) for row in cursor.fetchall()]
            conn.close()
            logger.info(f"📊 画像なし動画: {len(videos)}件")
            return videos

        except Exception as e:
            logger.error(f"画像なし動画の取得に失敗: {e}")
            return []

    def update_image_info(self, video_id: str, image_mode: str, image_filename: str) -> bool:
        """動画の画像情報を更新"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE videos
                SET image_mode = ?, image_filename = ?
                WHERE video_id = ?
            """, (image_mode, image_filename, video_id))

            conn.commit()
            conn.close()
            logger.info(f"✅ 画像情報更新: {video_id} → {image_filename}")
            return True

        except Exception as e:
            logger.error(f"画像情報の更新に失敗: {video_id} - {e}")
            return False

    def update_video_status(self, video_id: str, content_type: str = None, live_status = None) -> bool:
        """動画のコンテンツ種別とライブ配信状態を更新

        Args:
            video_id: 動画ID
            content_type: コンテンツ種別
            live_status: ライブ配信状態

        Returns:
            更新成功フラグ
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # 更新対象のカラムを動的に組み立て
            update_parts = []
            params = []

            # content_type を更新する場合
            if content_type is not None:
                content_type = self._validate_content_type(content_type)
                update_parts.append("content_type = ?")
                params.append(content_type)

            # live_status を更新する場合
            if live_status is not None:
                # content_type が指定されていない場合は、既存の値を取得
                if content_type is None:
                    cursor.execute("SELECT content_type FROM videos WHERE video_id = ?", (video_id,))
                    row = cursor.fetchone()
                    content_type = row[0] if row else "video"

                live_status = self._validate_live_status(live_status, content_type)
                update_parts.append("live_status = ?")
                params.append(live_status)

            if not update_parts:
                return True

            params.append(video_id)
            sql = f"UPDATE videos SET {', '.join(update_parts)} WHERE video_id = ?"
            cursor.execute(sql, params)

            conn.commit()
            conn.close()
            logger.info(f"✅ 動画ステータス更新: {video_id} (content_type={content_type}, live_status={live_status})")
            return True

        except Exception as e:
            logger.error(f"動画ステータス更新に失敗: {video_id} - {e}")
            return False

    def update_published_at(self, video_id: str, published_at: str) -> bool:
        """
        ★ YouTube API 優先: 既存動画の published_at を API データで上書き

        RSS で登録された動画の published_at を、YouTube API から取得した
        scheduledStartTime（より正確な配信予定時刻）で上書きする。

        ⚠️ **重要**: このメソッドは LIVE 動画の配信予定日時精度を決定する。
                 絶対に失敗してはいけない。

        Args:
            video_id: 動画ID
            published_at: 更新後の published_at（ISO 8601形式）

        Returns:
            更新成功フラグ
        """
        if not video_id or not published_at:
            logger.error(f"❌ update_published_at: 必須パラメータが不足しています（video_id={video_id}, published_at={published_at}）")
            return False

        for attempt in range(DB_RETRY_MAX):
            try:
                conn = self._get_connection()
                cursor = conn.cursor()

                # 現在の値を取得
                cursor.execute("SELECT published_at FROM videos WHERE video_id = ?", (video_id,))
                row = cursor.fetchone()
                if not row:
                    logger.debug(f"⚠️ 動画が見つかりません: {video_id}")
                    conn.close()
                    return False

                old_published_at = row[0]

                # published_at を更新
                cursor.execute("""
                    UPDATE videos SET published_at = ? WHERE video_id = ?
                """, (published_at, video_id))

                affected_rows = cursor.rowcount
                conn.commit()
                conn.close()

                if affected_rows == 0:
                    logger.error(f"❌ 動画更新に失敗（ロー数=0）: {video_id}")
                    return False

                if old_published_at != published_at:
                    logger.info(f"✅ [★重要] published_at を API データで更新: {video_id}")
                    logger.info(f"   旧: {old_published_at}")
                    logger.info(f"   新: {published_at}")
                else:
                    logger.debug(f"ℹ️ published_at は変わっていません（既に同じ値）: {video_id}")

                return True

            except sqlite3.OperationalError as e:
                conn.close()
                if "locked" in str(e).lower() and attempt < DB_RETRY_MAX - 1:
                    logger.debug(f"DB ロック中。{attempt + 1}/{DB_RETRY_MAX} リトライします...")
                    time.sleep(0.5)
                    continue
                else:
                    logger.error(f"❌ DB エラー（published_at 更新失敗）: {video_id} - {e}")
                    return False

            except Exception as e:
                logger.error(f"❌ published_at 更新に予期しないエラー: {video_id} - {e}")
                return False

        logger.error(f"❌ published_at 更新に失敗（リトライ上限）: {video_id}")
        return False

    def delete_video(self, video_id: str) -> bool:
        """動画をDBから削除（除外動画リスト連携付き）"""
        for attempt in range(DB_RETRY_MAX):
            try:
                conn = sqlite3.connect(self.db_path, timeout=DB_TIMEOUT)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                # 削除前に source を取得
                cursor.execute("SELECT source FROM videos WHERE video_id = ?", (video_id,))
                row = cursor.fetchone()
                source = row["source"] if row else "youtube"

                # DB から削除
                cursor.execute("DELETE FROM videos WHERE video_id = ?", (video_id,))
                conn.commit()
                conn.close()

                # ★ 新: 除外動画リストに追加
                try:
                    from deleted_video_cache import get_deleted_video_cache
                    cache = get_deleted_video_cache()
                    cache.add_deleted_video(video_id, source=source)
                except ImportError:
                    logger.warning("deleted_video_cache モジュールが見つかりません")
                except Exception as e:
                    logger.error(f"除外動画リスト登録エラー: {video_id} - {e}")

                logger.info(f"✅ 動画を削除しました: {video_id}")
                return True

            except sqlite3.OperationalError as e:
                if "locked" in str(e).lower() and attempt < DB_RETRY_MAX - 1:
                    logger.debug(f"DB ロック中。{attempt + 1}/{DB_RETRY_MAX} リトライします...")
                    time.sleep(0.5)
                    continue
                else:
                    logger.error(f"動画削除に失敗: {video_id} - {e}")
                    return False

            except Exception as e:
                logger.error(f"動画削除エラー: {video_id} - {e}")
                return False

        return False

    def delete_videos_batch(self, video_ids: list) -> int:
        """複数の動画をDBから削除

        Args:
            video_ids: 削除対象の動画ID リスト

        Returns:
            削除した数
        """
        deleted_count = 0
        for video_id in video_ids:
            if self.delete_video(video_id):
                deleted_count += 1

        return deleted_count

    def get_video_statistics(self) -> Dict[str, int]:
        """
        動画統計情報を取得（デバッグ・監視用）

        Returns:
            {
                "total": 総動画数,
                "unposted": 未投稿数,
                "posted": 投稿済み数,
                "selected": 投稿選択済み数,
                "scheduled": 予約投稿待ち数,
                "live": ライブ関連,
                "archive": アーカイブ,
                "video": 通常動画
            }
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            stats = {}

            # 総動画数
            cursor.execute("SELECT COUNT(*) FROM videos")
            stats["total"] = cursor.fetchone()[0]

            # 未投稿数
            cursor.execute("SELECT COUNT(*) FROM videos WHERE posted_to_bluesky = 0")
            stats["unposted"] = cursor.fetchone()[0]

            # 投稿済み数
            cursor.execute("SELECT COUNT(*) FROM videos WHERE posted_to_bluesky = 1")
            stats["posted"] = cursor.fetchone()[0]

            # 投稿選択済み数
            cursor.execute("SELECT COUNT(*) FROM videos WHERE selected_for_post = 1")
            stats["selected"] = cursor.fetchone()[0]

            # 予約投稿待ち数
            cursor.execute("""
                SELECT COUNT(*) FROM videos
                WHERE selected_for_post = 1 AND scheduled_at IS NOT NULL
                  AND scheduled_at > datetime('now')
            """)
            stats["scheduled"] = cursor.fetchone()[0]

            # コンテンツ種別別
            cursor.execute("SELECT COUNT(*) FROM videos WHERE content_type = 'live'")
            stats["live"] = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM videos WHERE content_type = 'archive'")
            stats["archive"] = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM videos WHERE content_type = 'video'")
            stats["video"] = cursor.fetchone()[0]

            conn.close()
            return stats

        except Exception as e:
            logger.error(f"動画統計取得エラー: {e}")
            return {"error": str(e)}


def get_database(db_path=DB_PATH) -> Database:
    """データベースオブジェクトを取得"""
    return Database(db_path)
