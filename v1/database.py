# -*- coding: utf-8 -*-

"""
YouTube Notifier on Bluesky - v1 データベース管理

SQLite データベースの操作を行う。
マルチプロセスアクセス対策：タイムアウト + リトライ
"""

import sqlite3
import logging
import os
import time
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("AppLogger")

__author__ = "mayuneco(mayunya)"
__copyright__ = "Copyright (C) 2025 mayuneco(mayunya)"
__license__ = "GPLv2"

DB_PATH = "data/video_list.db"
DB_TIMEOUT = 10
DB_RETRY_MAX = 3


class Database:
    """SQLite データベースを管理するクラス"""

    def __init__(self, db_path=DB_PATH):
        """
        初期化

        Args:
            db_path: データベースファイルのパス
        """
        self.db_path = db_path
        self.is_first_run = not Path(db_path).exists()
        self._ensure_directory()
        self._init_db()
        self._migrate_schema()

    def _ensure_directory(self):
        """ディレクトリを作成"""
        os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)

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
                    thumbnail_url TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.commit()
            conn.close()

            if self.is_first_run:
                logger.info(f"✓ 新規 DB を作成しました: {self.db_path}")
            else:
                logger.info(f"✓ DB を初期化しました: {self.db_path}")

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

            required_columns = {
                "selected_for_post": "INTEGER DEFAULT 0",
                "scheduled_at": "TEXT",
                "thumbnail_url": "TEXT"
            }

            migration_needed = False

            for col_name, col_def in required_columns.items():
                if col_name not in columns:
                    logger.info(f"🔄 カラムを追加します: {col_name}")
                    try:
                        cursor.execute(f"ALTER TABLE videos ADD COLUMN {col_name} {col_def}")
                        migration_needed = True
                    except sqlite3.OperationalError as e:
                        logger.warning(f"カラム追加スキップ（既に存在？）: {col_name} - {e}")

            if migration_needed:
                conn.commit()
                logger.info("✅ DB スキーマのマイグレーションが完了しました")

            conn.close()

        except Exception as e:
            logger.error(f"スキーママイグレーションエラー: {e}")
            raise

    def insert_video(self, video_id, title, video_url, published_at, channel_name="", thumbnail_url=""):
        """
        動画情報を挿入（リトライ付き）
        """
        for attempt in range(DB_RETRY_MAX):
            try:
                conn = self._get_connection()
                cursor = conn.cursor()

                cursor.execute("""
                    INSERT INTO videos (video_id, title, video_url, published_at, channel_name, thumbnail_url)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (video_id, title, video_url, published_at, channel_name, thumbnail_url))

                conn.commit()
                conn.close()
                logger.info(f"動画を保存しました: {title}")
                return True

            except sqlite3.IntegrityError:
                conn.close()
                logger.debug(f"動画は既に保存されています: {video_id}")
                return False

            except sqlite3.OperationalError as e:
                conn.close()
                if "locked" in str(e).lower() and attempt < DB_RETRY_MAX - 1:
                    logger.debug(f"DB ロック中。{attempt + 1}/{DB_RETRY_MAX} リトライします...")
                    time.sleep(0.5)
                    continue
                else:
                    logger.error(f"DB エラー: {e}")
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
                       selected_for_post, scheduled_at, video_url, channel_name, thumbnail_url
                FROM videos
                ORDER BY published_at DESC
            """)

            videos = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return videos

        except Exception as e:
            logger.error(f"全動画の取得に失敗しました: {e}")
            return []

    def mark_as_posted(self, video_id):
        """動画を投稿済みにマーク"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE videos SET posted_to_bluesky = 1 WHERE video_id = ?
            """, (video_id,))

            conn.commit()
            conn.close()
            logger.info(f"投稿済みフラグを更新しました: {video_id}")
            return True

        except Exception as e:
            logger.error(f"投稿済みフラグの更新に失敗しました: {e}")
            return False

    def update_selection(self, video_id, selected: bool, scheduled_at: str = None):
        """動画の投稿選択状態と予約日時を更新"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE videos 
                SET selected_for_post = ?, scheduled_at = ?
                WHERE video_id = ?
            """, (1 if selected else 0, scheduled_at, video_id))

            conn.commit()
            conn.close()
            logger.info(f"動画の選択状態を更新しました: {video_id} (selected={selected}, scheduled={scheduled_at})")
            return True

        except Exception as e:
            logger.error(f"動画の選択状態の更新に失敗しました: {e}")
            return False


def get_database(db_path=DB_PATH) -> Database:
    """データベースオブジェクトを取得"""
    return Database(db_path)
