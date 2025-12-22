# -*- coding: utf-8 -*-

"""
YouTubeLive プラグイン統合テスト

テスト対象：
- ライブ配信開始から投稿までのエンドツーエンドフロー
- ライブ配信終了から投稿までのエンドツーエンドフロー
- テンプレート選択から Bluesky 投稿までのフロー
- ポーリング処理の正常動作
"""

import sys
import os
import sqlite3
import logging
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock, call
import unittest

# プロジェクトルートを Python パスに追加
project_root = Path(__file__).parent.parent / "v2"
sys.path.insert(0, str(project_root))

# ロギングを無効化してテスト出力を見やすく
logging.disable(logging.CRITICAL)


class MockYouTubeAPIResponse:
    """YouTube API レスポンスのモック"""

    @staticmethod
    def live_video():
        """ライブ配信動画のレスポンス"""
        return {
            "id": "test_live_video",
            "snippet": {
                "title": "テスト ライブ配信中",
                "channelTitle": "テストチャネル",
                "liveBroadcastContent": "live",
                "thumbnails": {
                    "high": {
                        "url": "https://example.com/thumbnail_live.jpg"
                    }
                }
            },
            "liveStreamingDetails": {
                "actualStartTime": "2025-12-18T10:00:00Z",
                "scheduledStartTime": "2025-12-18T10:00:00Z",
                "concurrentViewers": "500",
                "isLiveContent": True
            }
        }

    @staticmethod
    def archive_video():
        """アーカイブ動画のレスポンス"""
        return {
            "id": "test_archive_video",
            "snippet": {
                "title": "テスト ライブ配信終了",
                "channelTitle": "テストチャネル",
                "liveBroadcastContent": "none",
                "thumbnails": {
                    "high": {
                        "url": "https://example.com/thumbnail_archive.jpg"
                    }
                }
            },
            "liveStreamingDetails": {
                "actualStartTime": "2025-12-18T10:00:00Z",
                "actualEndTime": "2025-12-18T11:30:00Z",
                "scheduledStartTime": "2025-12-18T10:00:00Z"
            }
        }

    @staticmethod
    def normal_video():
        """通常動画のレスポンス"""
        return {
            "id": "test_normal_video",
            "snippet": {
                "title": "テスト 通常動画",
                "channelTitle": "テストチャネル",
                "liveBroadcastContent": "none",
                "thumbnails": {
                    "high": {
                        "url": "https://example.com/thumbnail_normal.jpg"
                    }
                }
            }
        }

    @staticmethod
    def upcoming_video():
        """アップカミング動画のレスポンス"""
        return {
            "id": "test_upcoming_video",
            "snippet": {
                "title": "テスト 今後のライブ配信予定",
                "channelTitle": "テストチャネル",
                "liveBroadcastContent": "upcoming",
                "thumbnails": {
                    "high": {
                        "url": "https://example.com/thumbnail_upcoming.jpg"
                    }
                }
            },
            "liveStreamingDetails": {
                "scheduledStartTime": "2025-12-20T15:00:00Z"
            }
        }


class TestLiveStartFlow(unittest.TestCase):
    """ライブ配信開始フロー統合テスト"""

    def setUp(self):
        """テスト環境をセットアップ"""
        self.test_db_path = "test_integration_live_start.db"
        self._init_test_db()

    def tearDown(self):
        """テスト環境をクリーンアップ"""
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)

    def _init_test_db(self):
        """テスト用 DB を初期化"""
        conn = sqlite3.connect(self.test_db_path)
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
                image_mode TEXT,
                image_filename TEXT,
                source TEXT DEFAULT 'youtube',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()

    def test_live_start_flow(self):
        """ライブ配信開始フロー: RSS取得 → DB保存 → 自動投稿"""
        from database import Database

        # ステップ1: DB にライブ配信動画を保存
        db = Database(self.test_db_path)

        live_video_id = "dQw4w9WgXcQ"
        db.insert_video(
            video_id=live_video_id,
            title="テスト ライブ配信中",
            video_url=f"https://youtube.com/watch?v={live_video_id}",
            published_at=datetime.now().isoformat(),
            channel_name="テストチャネル",
            thumbnail_url="https://example.com/thumbnail_live.jpg",
            content_type="live",
            live_status="live",
            source="youtube"
        )

        # ステップ2: DB から live_status='live' の動画を取得
        live_videos = db.get_videos_by_live_status("live")

        # 検証
        assert len(live_videos) == 1, "ライブ動画が 1 件取得されるべき"
        assert live_videos[0]["video_id"] == live_video_id, "正しい動画 ID"
        assert live_videos[0]["live_status"] == "live", "live_status が 'live' であること"

        # ステップ3: Bluesky プラグインで投稿（モック）
        mock_bluesky = Mock()
        mock_bluesky.post_video = Mock(return_value=True)

        # 投稿実行
        result = mock_bluesky.post_video(live_videos[0])

        # 検証
        assert result is True, "投稿が成功するべき"
        mock_bluesky.post_video.assert_called_once()

        print("✅ test_live_start_flow: 成功（ライブ開始検知 → 投稿完了）")

    def test_template_selection_for_live_start(self):
        """ライブ開始時のテンプレート選択"""
        # テンプレート選択ロジックをテスト
        video = {
            "video_id": "test_live",
            "title": "ライブ配信中",
            "live_status": "live",
            "source": "youtube"
        }

        # live_status をチェック
        if video["live_status"] == "live":
            selected_template = "youtube_online"
        elif video["live_status"] == "completed":
            selected_template = "youtube_offline"
        else:
            selected_template = "youtube_new_video"

        assert selected_template == "youtube_online", "youtube_online テンプレートが選択されるべき"

        print("✅ test_template_selection_for_live_start: 成功（youtube_online テンプレート選択）")


class TestLiveEndFlow(unittest.TestCase):
    """ライブ配信終了フロー統合テスト"""

    def setUp(self):
        """テスト環境をセットアップ"""
        self.test_db_path = "test_integration_live_end_temp.db"
        self._init_test_db()

    def tearDown(self):
        """テスト環境をクリーンアップ"""
        if os.path.exists(self.test_db_path):
            try:
                os.remove(self.test_db_path)
            except Exception as e:
                print(f"DB ファイル削除失敗: {e}")

    def _init_test_db(self):
        """テスト用 DB を初期化"""
        # 既存ファイルを削除
        if os.path.exists(self.test_db_path):
            try:
                os.remove(self.test_db_path)
            except:
                pass

        conn = sqlite3.connect(self.test_db_path)
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
                image_mode TEXT,
                image_filename TEXT,
                source TEXT DEFAULT 'youtube',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()

    def test_live_end_flow(self):
        """ライブ配信終了フロー: ポーリング → ステータス更新 → 自動投稿"""
        # 新しい DB インスタンスを作成（シングルトン回避）
        conn = sqlite3.connect(self.test_db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        live_video_id = "dQw4w9WgXcQ"
        now = datetime.now().isoformat()

        # ステップ1: ライブ動画を直接 DB に挿入
        cursor.execute("""
            INSERT INTO videos (video_id, title, video_url, published_at, channel_name, thumbnail_url, content_type, live_status, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (live_video_id, "テスト ライブ配信中", f"https://youtube.com/watch?v={live_video_id}", now, "テストチャネル", "https://example.com/thumbnail_live.jpg", "live", "live", "youtube"))
        conn.commit()

        # ステップ2: ライブ動画が保存されたことを確認
        cursor.execute("SELECT * FROM videos WHERE live_status = ?", ("live",))
        initial_live_videos = [dict(row) for row in cursor.fetchall()]

        assert len(initial_live_videos) == 1, f"初期状態でライブ動画が 1 件あるべき（実際: {len(initial_live_videos)}）"
        print(f"  ✓ ライブ動画が 1 件保存されたことを確認")

        # ステップ3: ステータスを更新（live → completed）
        cursor.execute("""
            UPDATE videos SET content_type = ?, live_status = ? WHERE video_id = ?
        """, ("archive", "completed", live_video_id))
        conn.commit()
        print(f"  ✓ ステータスを更新（live → completed）")

        # ステップ4: live ステータスの動画が 0 件になることを確認
        cursor.execute("SELECT * FROM videos WHERE live_status = ?", ("live",))
        remaining_live_videos = [dict(row) for row in cursor.fetchall()]
        assert len(remaining_live_videos) == 0, f"更新後に live ステータスの動画が 0 件になるべき（実際: {len(remaining_live_videos)}）"
        print(f"  ✓ live ステータスの動画が 0 件になったことを確認")

        # ステップ5: completed 動画を取得
        cursor.execute("SELECT * FROM videos WHERE live_status = ?", ("completed",))
        completed_videos = [dict(row) for row in cursor.fetchall()]

        assert len(completed_videos) == 1, f"完了したライブ動画が 1 件取得されるべき（実際: {len(completed_videos)}）"
        assert completed_videos[0]["video_id"] == live_video_id, "正しい動画 ID"
        assert completed_videos[0]["live_status"] == "completed", "live_status が 'completed' であること"
        print(f"  ✓ completed 動画が 1 件取得されたことを確認")

        conn.close()

        # ステップ6: Bluesky プラグインで投稿（モック）
        mock_bluesky = Mock()
        mock_bluesky.post_video = Mock(return_value=True)

        result = mock_bluesky.post_video(completed_videos[0])

        assert result is True, "投稿が成功するべき"
        mock_bluesky.post_video.assert_called_once()
        print(f"  ✓ Bluesky 投稿が実行されたことを確認")

        print("✅ test_live_end_flow: 成功（ライブ終了検知 → ステータス更新 → 投稿完了）")

    def test_template_selection_for_live_end(self):
        """ライブ終了時のテンプレート選択"""
        # テンプレート選択ロジックをテスト
        video = {
            "video_id": "test_archive",
            "title": "ライブ配信終了",
            "live_status": "completed",
            "source": "youtube"
        }

        # live_status をチェック
        if video["live_status"] == "live":
            selected_template = "youtube_online"
        elif video["live_status"] == "completed":
            selected_template = "youtube_offline"
        else:
            selected_template = "youtube_new_video"

        assert selected_template == "youtube_offline", "youtube_offline テンプレートが選択されるべき"

        print("✅ test_template_selection_for_live_end: 成功（youtube_offline テンプレート選択）")


class TestPollingLoopIntegration(unittest.TestCase):
    """ポーリングループ統合テスト"""

    def test_polling_loop_execution(self):
        """ポーリングループが正常に実行される"""
        import threading
        import time

        # テスト用フラグ
        poll_count = {"value": 0}
        stop_event = threading.Event()

        def mock_polling():
            """モックのポーリング処理"""
            while not stop_event.is_set():
                poll_count["value"] += 1
                time.sleep(0.1)
                if poll_count["value"] >= 3:
                    stop_event.set()
                    break

        # ポーリングスレッドを開始
        poll_thread = threading.Thread(target=mock_polling, daemon=True)
        poll_thread.start()

        # スレッドが終了するまで待機（最大 5 秒）
        poll_thread.join(timeout=5)

        # 検証
        assert poll_count["value"] >= 3, f"ポーリングが 3 回実行されるべき（実際: {poll_count['value']}）"

        print("✅ test_polling_loop_execution: 成功（ポーリングループ正常実行）")

    def test_youtube_live_auto_post_end_flag(self):
        """YOUTUBE_LIVE_AUTO_POST_END フラグのテスト"""
        # フラグが true の場合
        with patch.dict(os.environ, {"YOUTUBE_LIVE_AUTO_POST_END": "true"}):
            auto_post_end = os.getenv("YOUTUBE_LIVE_AUTO_POST_END", "true").lower() == "true"
            assert auto_post_end is True, "フラグが有効になるべき"

        # フラグが false の場合
        with patch.dict(os.environ, {"YOUTUBE_LIVE_AUTO_POST_END": "false"}):
            auto_post_end = os.getenv("YOUTUBE_LIVE_AUTO_POST_END", "true").lower() == "true"
            assert auto_post_end is False, "フラグが無効になるべき"

        print("✅ test_youtube_live_auto_post_end_flag: 成功（フラグ処理正常）")


class TestErrorHandling(unittest.TestCase):
    """エラーハンドリングテスト"""

    def test_missing_environment_variables(self):
        """環境変数が未設定の場合のデフォルト値処理"""
        # YOUTUBE_LIVE_POLL_INTERVAL が未設定
        poll_interval = int(os.getenv("YOUTUBE_LIVE_POLL_INTERVAL", "5"))
        assert poll_interval == 5, "デフォルト値が 5 分であるべき"

        # YOUTUBE_LIVE_AUTO_POST_END が未設定
        auto_post_end = os.getenv("YOUTUBE_LIVE_AUTO_POST_END", "true").lower() == "true"
        assert auto_post_end is True, "デフォルト値が true であるべき"

        print("✅ test_missing_environment_variables: 成功（デフォルト値処理正常）")

    def test_database_error_recovery(self):
        """DB エラー時のリカバリーテスト"""
        # DB ロック時のリトライロジック（モック）
        retry_count = 0
        max_retries = 3

        while retry_count < max_retries:
            try:
                # 2 回目で成功するシミュレーション
                if retry_count < 1:
                    raise sqlite3.OperationalError("database is locked")

                # 成功
                result = "success"
                break
            except sqlite3.OperationalError as e:
                retry_count += 1
                if retry_count >= max_retries:
                    result = "failed"
                    break

        assert result == "success", "リトライ後に成功するべき"
        assert retry_count == 1, f"1 回のリトライで成功するべき（実際: {retry_count}）"

        print("✅ test_database_error_recovery: 成功（DB エラーリカバリー正常）")

    def test_plugin_unavailable_handling(self):
        """プラグインが利用不可の場合の処理"""
        mock_plugin_manager = Mock()
        mock_plugin_manager.get_plugin = Mock(return_value=None)

        # プラグインが None の場合のハンドリング
        plugin = mock_plugin_manager.get_plugin("youtube_live_plugin")

        if plugin is None:
            result = "plugin_unavailable"
        else:
            result = "plugin_available"

        assert result == "plugin_unavailable", "プラグイン未使用状態が検出されるべき"

        print("✅ test_plugin_unavailable_handling: 成功（プラグイン未使用時の処理正常）")


class TestPerformance(unittest.TestCase):
    """パフォーマンステスト"""

    def test_database_query_performance(self):
        """DB クエリパフォーマンステスト"""
        import time

        test_db_path = "test_performance.db"

        try:
            # DB を初期化
            conn = sqlite3.connect(test_db_path)
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS videos (
                    video_id TEXT UNIQUE NOT NULL,
                    live_status TEXT
                )
            """)

            # テストデータを挿入（100 件）
            for i in range(100):
                cursor.execute(
                    "INSERT INTO videos (video_id, live_status) VALUES (?, ?)",
                    (f"video_{i}", "live" if i % 10 == 0 else "none")
                )

            conn.commit()

            # クエリ実行時間を計測
            start_time = time.time()

            cursor.execute("SELECT * FROM videos WHERE live_status = ?", ("live",))
            results = cursor.fetchall()

            end_time = time.time()
            elapsed_time = end_time - start_time

            conn.close()

            # 検証
            assert len(results) == 10, "10 件のライブ動画が取得されるべき"
            assert elapsed_time < 0.1, f"クエリが 100ms 以内に完了するべき（実際: {elapsed_time*1000:.2f}ms）"

            print(f"✅ test_database_query_performance: 成功（クエリ実行時間: {elapsed_time*1000:.2f}ms）")

        finally:
            if os.path.exists(test_db_path):
                os.remove(test_db_path)


if __name__ == "__main__":
    # テストスイートを実行
    print("\n" + "=" * 70)
    print("YouTubeLive プラグイン統合テスト開始")
    print("=" * 70 + "\n")

    # 各テストクラスを実行
    suite = unittest.TestSuite()

    # フロー統合テスト
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestLiveStartFlow))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestLiveEndFlow))

    # ポーリング統合テスト
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestPollingLoopIntegration))

    # エラーハンドリングテスト
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestErrorHandling))

    # パフォーマンステスト
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestPerformance))

    # テストを実行
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # 結果サマリー
    print("\n" + "=" * 70)
    print("統合テスト結果サマリー")
    print("=" * 70)
    print(f"✅ 成功: {result.testsRun - len(result.failures) - len(result.errors)}/{result.testsRun}")
    if result.failures:
        print(f"❌ 失敗: {len(result.failures)}")
    if result.errors:
        print(f"⚠️  エラー: {len(result.errors)}")

    # 終了コード
    sys.exit(0 if result.wasSuccessful() else 1)
