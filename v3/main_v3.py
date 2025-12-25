# -*- coding: utf-8 -*-

"""
Stream notify on Bluesky - v3 メインスクリプト

特定の YouTube チャンネルの新着動画を RSS で監視し、
DB に収集。投稿対象は GUI で選択。
収集モード時は投稿なし。

GUI はマルチスレッドで動作（メインループは継続）
"""

import sys
import os
import time
import signal
import logging
import threading
import tkinter as tk
import gc
from datetime import datetime, timedelta

# バージョン情報
from app_version import get_version_info, get_full_version_info

# プラグインマネージャ関連
from plugin_manager import PluginManager

# 設定
from config import OperationMode

# アセットマネージャ
from asset_manager import get_asset_manager

# ロギング設定
from logging_config import setup_logging

# GUI クラスをインポート
from gui_v3 import StreamNotifyGUI

logger = None  # グローバル変数として後で初期化
gui_instance = None  # GUI インスタンスをグローバルで保持（プラグイン判定後のリロード用）

__author__ = "mayuneco(mayunya)"
__copyright__ = "Copyright (C) 2025 mayuneco(mayunya)"
__license__ = "GPLv2"


def run_gui(db, plugin_manager, stop_event, bluesky_core=None):
    """GUI をスレッドで実行 (プラグイン対応)"""
    global gui_instance

    root = tk.Tk()
    gui_instance = StreamNotifyGUI(root, db, plugin_manager, bluesky_core=bluesky_core)

    def on_closing():
        logger.info("管理画面が閉じられたためアプリケーションを終了します...")
        stop_event.set()

        # GUI インスタンスの参照をクリア
        global gui_instance
        try:
            # GUI オブジェクトの明示的なクリーンアップ
            if hasattr(gui_instance, 'cleanup'):
                gui_instance.cleanup()
            gui_instance = None
        except:
            pass

        # tkinter オブジェクトの破棄
        try:
            root.quit()  # mainloop をクリアに終了（destroy ではなく）
        except:
            pass

    root.protocol("WM_DELETE_WINDOW", on_closing)

    try:
        root.mainloop()
    except Exception as e:
        logger.debug(f"GUI mainloop エラー（無視）: {e}")
    finally:
        # スレッド終了時の最終クリーンアップ
        try:
            root.destroy()
        except:
            pass

        # グローバル参照をクリア
        gui_instance = None


def signal_handler(signum, frame):
    """シグナルハンドラ"""
    logger.info("\n[INFO] 管理画面が閉じられたためアプリケーションを終了します...")
    sys.exit(0)


def main():
    """メインエントリポイント (v3: プラグインアーキテクチャ対応)"""
    global logger
    global gui_instance

    # バージョン情報をコンソールに出力
    print(f"StreamNotify on Bluesky {get_version_info()}")

    try:
        from config import get_config
        config = get_config("settings.env")
        logger = setup_logging(debug_mode=config.debug_mode)
        logger.info(f"StreamNotify on Bluesky {get_version_info()}")
        logger.info(f"動作モードは: {config.operation_mode} に設定されています。")
    except Exception as e:
        print(f"設定の読み込みに失敗しました: {e}")
        sys.exit(1)

    try:
        logger.info("データベースを準備しています...")
        from database import get_database
        db = get_database()
        if db.is_first_run:
            logger.info("🆕 初回起動です。収集モードで動作します。")
        logger.info("データベースを読み込みました")
    except Exception as e:
        logger.error(f"データベースの読み込みに失敗しました: {e}")
        sys.exit(1)

    # ★ 新: 削除済み動画除外リストを初期化
    try:
        from deleted_video_cache import get_deleted_video_cache
        deleted_cache = get_deleted_video_cache()
        total_deleted = deleted_cache.get_deleted_count()
        if total_deleted > 0:
            logger.info(f"🔒 除外動画リストから削除済み動画 {total_deleted} 件を読み込みました")
        else:
            logger.debug("除外動画リストはクリア状態です")
    except ImportError:
        logger.warning("deleted_video_cache モジュールが見つかりません")
    except Exception as e:
        logger.error(f"除外動画リストの初期化に失敗しました: {e}")

    try:
        logger.info("[YouTube] YouTubeRSS の取得を準備しています...")
        from youtube_rss import get_youtube_rss
        yt_rss = get_youtube_rss(config.youtube_channel_id)
        logger.info("[YouTube] RSS の取得準備を完了しました")
    except Exception as e:
        logger.error(f"[YouTube] YouTubeRSS の取得に失敗しました: {e}")
        sys.exit(1)

    plugin_manager = PluginManager(plugins_dir="plugins")
    loaded_names = set()

    # Asset マネージャーの初期化（プラグイン導入時に資源を配置）
    asset_manager = get_asset_manager()
    logger.info("📦 Asset マネージャーを初期化しました")

    plugin_files = [f for f in os.listdir("plugins") if f.endswith(".py") and not f.startswith("_") and f not in ("bluesky_plugin.py", "niconico_plugin.py", "youtube_api_plugin.py", "youtube_live_plugin.py")]
    for pf in plugin_files:
        plugin_name = pf[:-3]
        if plugin_name in loaded_names:
            continue
        plugin_manager.load_plugin(plugin_name, os.path.join("plugins", pf))
        # 自動ロードされたプラグインを有効化
        plugin_manager.enable_plugin(plugin_name)

        # プラグイン別のアセット配置
        try:
            asset_manager.deploy_plugin_assets(plugin_name)
        except Exception as e:
            logger.warning(f"プラグイン '{plugin_name}' のアセット配置失敗: {e}")

        loaded_names.add(plugin_name)

    # YouTubeAPI プラグインを手動でロード・有効化
    try:
        plugin_manager.load_plugin("youtube_api_plugin", os.path.join("plugins", "youtube_api_plugin.py"))
        plugin_manager.enable_plugin("youtube_api_plugin")
        asset_manager.deploy_plugin_assets("youtube_api_plugin")
        youtube_api_plugin_available = True
        logger.debug("✅ YouTubeAPI プラグインを有効化しました")
    except Exception as e:
        logger.debug(f"YouTubeAPI プラグインのロード失敗: {e}")
        youtube_api_plugin_available = False

    # YouTubeLive 検出プラグインを手動でロード・有効化
    youtube_live_plugin_available = False  # ★ 新: LIVE関連機能の有効化フラグ
    try:
        live_plugin_loaded = plugin_manager.load_plugin("youtube_live_plugin", os.path.join("plugins", "youtube_live_plugin.py"))

        # ★ 新: プラグイン読み込み成功時のみ以降の処理を実行
        if live_plugin_loaded is not None:
            asset_manager.deploy_plugin_assets("youtube_live_plugin")

            # ★ YouTube Live プラグインに plugin_manager を注入（自動投稿用）
            # ★ IMPORTANT: enable_plugin() より前に注入する必要がある（on_enable で自動投稿ロジックが実行されるため）
            live_plugin = plugin_manager.get_plugin("youtube_live_plugin")
            if live_plugin:
                live_plugin.set_plugin_manager(plugin_manager)

            # ★ 注入完了後に有効化（on_enable() が呼ばれる）
            plugin_manager.enable_plugin("youtube_live_plugin")
            youtube_live_plugin_available = True  # ★ 新: フラグを有効化

            # ★ プラグイン判定後に GUI を自動リロード
            if gui_instance:
                logger.debug("🔄 YouTube Live プラグイン判定後、GUI を再読込します...")
                try:
                    gui_instance.refresh_data()
                    logger.info("✅ GUI を自動更新しました")
                except Exception as e:
                    logger.debug(f"⚠️ GUI 自動更新に失敗（無視）: {e}")
        else:
            logger.warning("⚠️ YouTubeLive プラグインが見つかりません。LIVE関連の検出機能は無効化されます。")
    except Exception as e:
        logger.debug(f"YouTubeLive 検出プラグインのロード失敗: {e}")
        logger.warning("⚠️ YouTubeLive プラグインのロードに失敗しました。LIVE関連の検出機能は無効化されます。")


    if config.youtube_api_plugin_exists:
        if config.youtube_api_plugin_enabled:
            logger.info("[YouTubeAPI] 有効なAPIキーを確認しました。連携機能を有効化します。")
        else:
            logger.info("[YouTubeAPI] APIキーが未設定のため連携機能を無効化します。")
    else:
        # ロギング設定後に警告を出力（error.logにも記録される）
        logger.warning("[YouTubeAPI] プラグインが未導入です。UCから始まるチャンネルIDのみ利用可能です。")

    # Bluesky コア機能をロード（プラグインマネージャーには登録しない - 内部ライブラリとして機能）
    try:
        from bluesky_core import BlueskyMinimalPoster
        bluesky_core = BlueskyMinimalPoster(
            config.bluesky_username,
            config.bluesky_password,
            dry_run=not config.bluesky_post_enabled
        )
        logger.info(f"✅ Bluesky コア機能を初期化しました（テキスト投稿 + URLリンク化）")
    except Exception as e:
        logger.warning(f"⚠️  Bluesky コア機能の初期化に失敗しました: {e}")
        bluesky_core = None

    # Bluesky 拡張機能プラグイン（画像添付・テンプレート）をロード
    # プラグインがない場合でも、コア機能（テキスト投稿）は引き続き利用可能
    bluesky_plugin_available = False
    try:
        from plugins.bluesky_plugin import BlueskyImagePlugin
        bluesky_image_plugin = BlueskyImagePlugin(
            config.bluesky_username,
            config.bluesky_password,
            dry_run=not config.bluesky_post_enabled,
            minimal_poster=bluesky_core
        )
        plugin_manager.loaded_plugins["bluesky_image_plugin"] = bluesky_image_plugin
        plugin_manager.enable_plugin("bluesky_image_plugin")
        asset_manager.deploy_plugin_assets("bluesky_plugin")
        bluesky_plugin_available = True
        logger.info(f"✅ Bluesky 拡張機能プラグインを有効化しました（画像添付機能: 有効）")
    except Exception as e:
        logger.warning(f"⚠️  Bluesky 拡張機能プラグインの導入に失敗しました: {e}")
        logger.info(f"ℹ️ プラグインがない場合でも、コア機能（テキスト投稿 + URLリンク化）は利用可能です")

    if config.niconico_plugin_exists:
        try:
            from plugins.niconico_plugin import NiconicoPlugin
            niconico_plugin = NiconicoPlugin(
                user_id=config.niconico_user_id,
                poll_interval=config.niconico_poll_interval_minutes,
                db=db,
                user_name=os.getenv("NICONICO_USER_NAME")
            )
            plugin_manager.loaded_plugins["niconico_plugin"] = niconico_plugin

            if niconico_plugin.is_available():
                logger.info("[ニコニコ連携] 有効なユーザーIDを確認しました。連携機能を有効化します。")
                plugin_manager.enable_plugin("niconico_plugin")
                asset_manager.deploy_plugin_assets("niconico_plugin")
                niconico_plugin.start_monitoring()
            else:
                logger.info("[ニコニコ連携] ユーザーIDが有効でないため連携機能を無効化します。")
        except Exception as e:
            logger.warning(f"[ニコニコ連携] 初期化エラー: {type(e).__name__}: {e}", exc_info=True)
    else:
        logger.info("[ニコニコ連携] ニコニコ連携プラグインは導入されていません。")

    # ===== WebSub 初期化（API 経由でセンターサーバーから取得） =====
    # ローカルクライアント側は Web サーバー不要（すべての外部通信はセンターサーバーが処理）
    websub_manager = None
    logger.info("ℹ️ WebSub データはセンターサーバー API 経由で取得します（ローカル Web サーバー不使用）")

    stop_event = threading.Event()
    gui_thread = threading.Thread(target=run_gui, args=(db, plugin_manager, stop_event, bluesky_core), daemon=True)
    gui_thread.start()

    # YouTube Live 設定を整形（複数行を連続出力させない - スレッド安全性確保）
    live_settings = (
        f"📋 現在の YouTube Live 投稿設定:\n"
        f"   - 予約枠投稿: {'有効' if config.youtube_live_auto_post_schedule else '無効'}\n"
        f"   - 配信中/終了投稿: {'有効' if config.youtube_live_auto_post_live else '無効'}\n"
        f"   - アーカイブ投稿: {'有効' if config.youtube_live_auto_post_archive else '無効'}\n"
        f"   - 投稿遅延: {config.youtube_live_post_delay}\n"
        f"   - プレミア配信投稿: {'有効' if config.autopost_include_premiere else '無効'}"
    )
    logger.info(live_settings)

    logger.info("✅ アプリケーションの起動が完了しました。 管理画面を開きます。")

    # ===== YouTube Live 終了検知用の定期ポーリングスレッド =====
    def start_youtube_live_polling():
        """YouTubeLive ライブ終了検知の定期ポーリングを開始（動的間隔対応）"""
        import time

        # ★ 新: プラグイン未導入時は処理をスキップ
        if not youtube_live_plugin_available:
            logger.info("ℹ️ YouTubeLive プラグインが未導入のため、ライブ終了検知は無効です")
            return

        # デフォルトポーリング間隔（分）
        poll_interval_base = int(os.getenv("YOUTUBE_LIVE_POLL_INTERVAL", "15"))

        # 動的間隔の設定（環境変数で上書き可能）
        poll_interval_active_live = int(os.getenv("YOUTUBE_LIVE_POLL_INTERVAL_ACTIVE", "5"))      # LIVE中: 5分
        poll_interval_completed = int(os.getenv("YOUTUBE_LIVE_POLL_INTERVAL_COMPLETED", "15"))    # 完了後: 15分
        poll_interval_no_live = int(os.getenv("YOUTUBE_LIVE_POLL_INTERVAL_NO_LIVE", "30"))        # LIVE なし: 30分

        # バリデーション：最短5分、最長60分に制限
        for interval_name, interval_var in [
            ("active", poll_interval_active_live),
            ("completed", poll_interval_completed),
            ("no_live", poll_interval_no_live)
        ]:
            if interval_var < 5:
                logger.warning(f"⚠️ ポーリング間隔({interval_name})={interval_var} は短すぎます（最短5分）")
            elif interval_var > 60:
                logger.warning(f"⚠️ ポーリング間隔({interval_name})={interval_var} は長すぎます（最長60分）")

        # ★ 修正: 旧フラグではなく新 MODE 変数で判定
        # YOUTUBE_LIVE_AUTO_POST_MODE が "all" または "live" の場合のみポーリング有効
        mode = os.getenv("YOUTUBE_LIVE_AUTO_POST_MODE", "off").lower()
        if mode not in ("all", "live"):
            logger.info(f"ℹ️ YOUTUBE_LIVE_AUTO_POST_MODE={mode} のためライブ終了検知は無効です")
            return

        logger.info(f"📡 YouTubeLive ライブ終了検知ポーリング: 動的間隔対応")
        logger.info(f"   - LIVE中: {poll_interval_active_live} 分")
        logger.info(f"   - 完了後: {poll_interval_completed} 分")
        logger.info(f"   - LIVE なし: {poll_interval_no_live} 分")

        while not stop_event.is_set():
            try:
                live_plugin = plugin_manager.get_plugin("youtube_live_plugin")
                if live_plugin and live_plugin.is_available():
                    logger.debug("🔄 YouTubeLive ライブ終了チェック実行...")
                    live_plugin.poll_live_status()
                else:
                    logger.debug("ℹ️ YouTubeLive プラグインが利用不可")

                # ★ 新: キャッシュの状態に応じてポーリング間隔を動的変更
                from youtube_live_cache_manager import YouTubeLiveCacheManager
                cache_mgr = YouTubeLiveCacheManager()

                if cache_mgr.has_active_live():
                    # LIVE中 → 短い間隔でポーリング
                    current_interval = poll_interval_active_live
                    logger.debug(f"📡 LIVE 中のため {current_interval} 分間隔でポーリングします")
                elif cache_mgr.has_completed_live():
                    # 完了後 → 中程度の間隔でポーリング
                    current_interval = poll_interval_completed
                    logger.debug(f"📡 LIVE 完了のため {current_interval} 分間隔でポーリングします")
                else:
                    # LIVE なし → 長い間隔でポーリング
                    current_interval = poll_interval_no_live
                    logger.debug(f"📡 LIVE なしのため {current_interval} 分間隔でポーリングします")

            except Exception as e:
                logger.error(f"❌ ライブ終了チェックエラー: {e}")
                # エラー時はデフォルト間隔を使用
                current_interval = poll_interval_base

            # 待機（動的間隔を使用）
            for _ in range(current_interval * 60):
                if stop_event.is_set():
                    break
                time.sleep(1)

    # ライブ終了検知スレッド開始
    live_polling_thread = threading.Thread(target=start_youtube_live_polling, daemon=True)
    live_polling_thread.start()

    # ===== WebSub 購読スレッド =====
    def start_websub_subscription():
        """WebSub 購読を開始（定期更新含む）"""
        if not websub_manager:
            logger.info("ℹ️ WebSub マネージャーが初期化されていません")
            return

        # 購読開始
        success = websub_manager.subscribe()
        if not success:
            logger.warning("⚠️ WebSub 購読に失敗しました")
            if config.youtube_feed_mode == "websub":
                logger.error("❌ WebSub モード指定ですが購読失敗のため、ポーリングモードにフォールバックします")
                config.youtube_feed_mode = "poll"
            return

        logger.info("✅ YouTube WebSub を購読しました")

        # 購読期間の70%経過後に自動更新（再購読）
        while not stop_event.is_set():
            renew_interval = config.websub_lease_seconds * 0.7
            logger.debug(f"🔄 次回 WebSub 更新: {renew_interval/3600:.1f} 時間後")

            # 待機
            for _ in range(int(renew_interval)):
                if stop_event.is_set():
                    break
                time.sleep(1)

            if stop_event.is_set():
                break

            # 再購読（更新）
            logger.debug("� WebSub を更新しています...")
            success = websub_manager.subscribe()
            if success:
                logger.info("✅ WebSub を更新しました")
            else:
                logger.warning("⚠️ WebSub 更新に失敗しました")

    # WebSub 購読スレッド開始
    if websub_manager:
        websub_subscription_thread = threading.Thread(target=start_websub_subscription, daemon=True)
        websub_subscription_thread.start()
        logger.info("✅ WebSub 購読スレッドを開始しました")

    polling_count = 0
    last_post_time = None
    autopost_warning_shown = False  # セーフモード警告フラグ
    safe_mode_enabled = False       # セーフモード有効フラグ（仕様 5.3）

    # ★ 新: 初期化完了待機
    # WebSub 購読スレッドが実行されるまで2秒待つ
    # （購読ファイルの書き込み完了を待つため）
    logger.info("🔄 初期化プロセスの完了を待機中... (2秒)")
    time.sleep(2)

    # ★ 新: セーフモード起動判定（仕様 5.3）
    # 起動時に posted_to_bluesky=0 かつ posted_at IS NOT NULL の件数をチェック
    # これは「投稿マーク自体がリセットされた」異常を検知する
    if config.operation_mode == OperationMode.AUTOPOST:
        try:
            import sqlite3
            conn = sqlite3.connect(db.db_path, timeout=10)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM videos WHERE posted_to_bluesky = 0 AND posted_at IS NOT NULL"
            )
            reset_count = cursor.fetchone()[0]
            conn.close()

            if reset_count > 0:
                safe_mode_enabled = True
                logger.error(f"❌ セーフモード起動: posted_to_bluesky の大量リセットを検知（{reset_count} 件）")
                logger.warning(f"⚠️  AUTOPOST は抑止されます。DB の状態を確認して、手動リセットしてください。")
        except Exception as e:
            logger.warning(f"セーフモード判定エラー（続行）: {e}")

    try:
        while not stop_event.is_set():
            polling_count += 1
            logger.info(f"\n=== ポーリング #{polling_count} ===")
            logger.info(f"実行時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

            # ===== フィード取得モード別処理 =====
            # WebSub/Hybrid: センターサーバー API 優先 → 失敗時は RSS フォールバック
            # Poll: RSS ポーリング直接実行

            should_fetch_rss = True
            websub_processed_count = 0
            center_server_available = False

            if config.youtube_feed_mode in ("websub", "hybrid"):
                # ★ WebSub/Hybrid モード: センターサーバーから完全に取得
                logger.info(f"📡 フィード取得モード: {config.youtube_feed_mode.upper()}（センターサーバー API から取得）")

                try:
                    from production_server_api_client import get_production_api_client

                    prod_api = get_production_api_client()

                    # ★ ステップ1: ヘルスチェック
                    logger.debug("🔍 センターサーバーのヘルスチェック中...")
                    if not prod_api.verify_connection():
                        logger.warning("❌ センターサーバーへの接続に失敗しました")
                        center_server_available = False
                    else:
                        logger.debug("✅ センターサーバー疎通確認成功")
                        center_server_available = True

                        # ★ ステップ2: API から WebSub データ取得
                        logger.debug(f"📥 API から WebSub データを取得中（channel_id={config.youtube_channel_id}）...")
                        websub_videos_from_api = prod_api.get_websub_videos(
                            channel_id=config.youtube_channel_id,
                            limit=50
                        )

                        if websub_videos_from_api:
                            logger.info(f"✅ API から {len(websub_videos_from_api)} 件のビデオを取得しました")
                            logger.info(f"📋 取得したビデオIDリスト: {[v.get('video_id') for v in websub_videos_from_api]}")

                            # ★ ステップ3: 各動画を処理（RSS フロー と同じ）
                            from thumbnails.youtube_thumb_utils import get_youtube_thumb_manager
                            from youtube_rss import YouTubeRSS

                            thumb_mgr = get_youtube_thumb_manager()

                            for api_video in websub_videos_from_api:
                                try:
                                    video_id = api_video.get("video_id")
                                    thumbnail_url = api_video.get("thumbnail_url", "")
                                    logger.info(f"🔄 処理中: {video_id}")

                                    # API データから content_type と live_status を取得
                                    # API に含まれていない場合はデフォルト値を使用
                                    content_type = api_video.get("content_type", "video")
                                    live_status = api_video.get("live_status")
                                    title = api_video.get("title", "")
                                    channel_name = api_video.get("channel_name", "")  # API には channel_name が含まれていない

                                    logger.info(f"  📝 タイトル: {title}")
                                    logger.info(f"  🏷️ type={content_type}, status={live_status}")

                                    # DB に保存
                                    logger.info(f"  💾 DB 保存試行: {video_id}")
                                    # video_url が None の場合は標準 YouTube URL に置き換え
                                    video_url = api_video.get("video_url")
                                    if not video_url:
                                        video_url = f"https://www.youtube.com/watch?v={video_id}"

                                    logger.info(f"  📍 video_url: {video_url}")
                                    is_new = db.insert_video(
                                        video_id=video_id,
                                        title=title,
                                        video_url=video_url,
                                        published_at=api_video.get("published_at", datetime.now().isoformat()),
                                        channel_name=channel_name,
                                        thumbnail_url=thumbnail_url,
                                        content_type=content_type,
                                        live_status=live_status,
                                        source="youtube"
                                    )
                                    logger.info(f"  💾 DB 保存結果: is_new={is_new}")

                                    if is_new:
                                        logger.info(f"✅ 新規ビデオを登録: {video_id}")

                                        # ★ ステップ4: サムネイル取得（API データに thumbnail_url がない場合は自動取得）
                                        if thumbnail_url:
                                            try:
                                                thumb_mgr.ensure_image_download(video_id, thumbnail_url)
                                                logger.info(f"📸 サムネイル取得（API データから）: {video_id}")
                                            except Exception as e:
                                                logger.warning(f"⚠️ サムネイル取得エラー({video_id}): {e}")
                                        else:
                                            # thumbnail_url がない場合は image_manager から自動取得
                                            logger.info(f"🔍 YouTube API から サムネイル URL を自動取得中({video_id})...")
                                            try:
                                                from image_manager import get_youtube_thumbnail_url
                                                thumb_url = get_youtube_thumbnail_url(video_id)
                                                if thumb_url:
                                                    logger.info(f"📸 サムネイル取得（image_manager から）: {video_id}")
                                                    thumb_mgr.ensure_image_download(video_id, thumb_url)
                                                    # DB 更新
                                                    db.update_thumbnail_url(video_id, thumb_url)
                                                else:
                                                    logger.debug(f"⚠️ サムネイル URL が取得できません: {video_id}")
                                            except Exception as e:
                                                logger.warning(f"⚠️ サムネイル取得失敗({video_id}): {e}")

                                        # ★ ステップ5: YouTube Live 判定（YouTube API プラグインで content_type と live_status を判定）
                                        logger.info(f"🎬 YouTube Live 自動判定を実行中({video_id})...")
                                        try:
                                            enabled_plugins = plugin_manager.get_enabled_plugins()
                                            yt_api_plugin = enabled_plugins.get("youtube_api_plugin")
                                            if yt_api_plugin:
                                                # YouTube API から動画詳細を取得して判定
                                                video_detail = yt_api_plugin.fetch_video_detail(video_id)
                                                if video_detail:
                                                    from plugins.youtube_api_plugin import YouTubeAPIPlugin
                                                    content_type, live_status, is_premiere = YouTubeAPIPlugin._classify_video_core(video_detail)
                                                    if content_type or live_status:
                                                        logger.info(f"🎬 動画種別を判定: {video_id} → type={content_type}, status={live_status}")
                                                        db.update_video_status(video_id, content_type=content_type, live_status=live_status)
                                                else:
                                                    logger.debug(f"⚠️ YouTube API から動画詳細が取得できません: {video_id}")
                                            else:
                                                logger.debug(f"ℹ️ YouTube API プラグインが有効でないため、自動判定はスキップします: {video_id}")
                                        except Exception as e:
                                            logger.warning(f"⚠️ YouTube Live 判定エラー({video_id}): {e}")

                                        websub_processed_count += 1
                                    else:
                                        logger.debug(f"ℹ️ 既存動画: {video_id}")

                                except Exception as e:
                                    logger.error(f"❌ API ビデオ処理エラー({api_video.get('video_id', '?')}): {e}")

                            # WebSub モード時は RSS フェッチしない
                            if config.youtube_feed_mode == "websub":
                                should_fetch_rss = False
                        else:
                            logger.warning("⚠️ API からビデオが取得できません")
                            # Hybrid モードでは RSS にフォールバック
                            should_fetch_rss = True

                except Exception as e:
                    logger.error(f"❌ API 処理エラー: {e}")
                    # フォールバック: RSS ポーリング
                    should_fetch_rss = True

                # フォールバック判定: ヘルスチェック失敗時
                if not center_server_available:
                    logger.warning("⚠️ センターサーバーが利用不可のため、RSS ポーリングにフォールバック")
                    should_fetch_rss = True

            else:
                # Poll モード: RSS ポーリング直接実行
                logger.info(f"📡 フィード取得モード: POLL（RSS ポーリング直接実行）")
                should_fetch_rss = True

            if should_fetch_rss:
                logger.info("[YouTube] YouTubeRSS から情報を取得しています...")
                # YouTube RSS フェッチ・DB 保存・画像自動処理
                from thumbnails.youtube_thumb_utils import get_youtube_thumb_manager
                thumb_mgr = get_youtube_thumb_manager()
                saved_count = thumb_mgr.fetch_and_ensure_images(config.youtube_channel_id)
            else:
                saved_count = 0  # WebSub 待機中は 0

            # ★ 新: YouTube RSS 取得後、YouTube Live プラグインで自動分類を実行
            # 配信予定枠などが正しく content_type="live", live_status="upcoming" として分類される
            # ★ 重要: collect モード時は判定処理をスキップ（collect は投稿機能を一切実行しない）
            if config.is_collect_mode:
                logger.info("[モード] 収集モード のため、判定・投稿処理をスキップします。")
            elif youtube_live_plugin_available and (saved_count > 0 or websub_processed_count > 0 or polling_count == 1):  # ★ 新: WebSub 処理後も実行
                try:
                    api_plugin = plugin_manager.get_plugin("youtube_api_plugin")
                    if api_plugin and api_plugin.is_available():
                        logger.info(f"🔍 YouTube API プラグイン: 未判定動画を自動分類中...")
                        unclassified = [v for v in db.get_all_videos() if v.get("content_type") == "video"]
                        updated_count = 0
                        for video in unclassified:
                            try:
                                details = api_plugin._get_cached_video_detail(video["video_id"])
                                if details:
                                    content_type, live_status, is_premiere = api_plugin._classify_video_core(details)
                                    db.update_video_status(video["video_id"], content_type, live_status)
                                    updated_count += 1
                            except Exception as ve:
                                logger.debug(f"動画分類エラー {video.get('video_id')}: {ve}")
                        if updated_count > 0:
                            logger.info(f"✅ YouTube API 自動分類: {updated_count} 件更新（配信予定枠など検出）")
                except Exception as e:
                    logger.debug(f"⚠️ YouTube API プラグインの自動分類エラー: {e}")

            if config.is_collect_mode:
                logger.info("[モード] 収集モード のため、投稿処理をスキップします。")
                # ★ collect モード: 初回ポーリング後に自動終了
                logger.info("✅ 初回ポーリング完了。collect モードのため、アプリケーションを自動終了します。")
                raise KeyboardInterrupt()
            elif config.operation_mode == OperationMode.SELFPOST:
                # === SELFPOST モード（手動投稿 + YouTube Live 自動投稿）===
                logger.info("[モード] SELFPOST モード。通常動画は GUI から設定、YouTube Live は自動投稿。")

                # ★ YouTube Live 個別フラグでの自動投稿（SELFPOST 向け）
                if youtube_live_plugin_available:
                    try:
                        live_plugin = plugin_manager.get_plugin("youtube_live_plugin")
                        if live_plugin and live_plugin.is_available():
                            # YouTube Live 未投稿動画を取得
                            unclassified_videos = db.get_videos_by_live_status("upcoming")
                            unclassified_videos += db.get_videos_by_live_status("live")
                            unclassified_videos += db.get_videos_by_live_status("completed")

                            for video in unclassified_videos:
                                if video["posted_to_bluesky"] == 1:
                                    continue  # 既投稿なのでスキップ

                                # 個別フラグをチェック
                                should_post = False
                                if video.get("live_status") == "upcoming" and config.youtube_live_auto_post_schedule:
                                    should_post = True
                                elif video.get("live_status") == "live" and config.youtube_live_auto_post_live:
                                    should_post = True
                                elif video.get("live_status") == "completed" and config.youtube_live_auto_post_archive:
                                    should_post = True

                                if should_post:
                                    # 投稿実行
                                    logger.info(f"📤 YouTube Live 自動投稿（SELFPOST 向け）: {video['title'][:50]}")
                                    try:
                                        results = plugin_manager.post_video_with_all_enabled(video, dry_run=not config.bluesky_post_enabled)
                                        if any(results.values()) or not config.bluesky_post_enabled:
                                            db.mark_as_posted(video["video_id"])
                                            if config.bluesky_post_enabled:
                                                logger.info(f"✅ YouTube Live 投稿成功: {video['title'][:50]}")
                                            else:
                                                logger.info(f"🧪 YouTube Live ドライラン完了（投稿済みフラグ登録）: {video['title'][:50]}")
                                        else:
                                            logger.warning(f"⚠️  YouTube Live 投稿失敗: {video['title'][:50]}")
                                    except Exception as e:
                                        logger.error(f"❌ YouTube Live 投稿エラー: {e}")

                    except Exception as e:
                        logger.debug(f"⚠️ YouTube Live 自動投稿処理エラー: {e}")

                logger.info("[モード] 通常動画は GUI から設定して投稿してください。")
            elif config.operation_mode == OperationMode.AUTOPOST:
                # === AUTOPOST モード（完全自動投稿）===
                logger.info("[モード] AUTOPOST モード。自動投稿ロジックを実行します。")

                # ★ セーフモードチェック（仕様 5.3）
                if safe_mode_enabled:
                    logger.error("❌ セーフモード中: AUTOPOST は抑止されています。")
                    continue

                # 安全弁 1: 未投稿大量検知
                unposted_count = db.count_unposted_in_lookback(config.autopost_lookback_minutes)
                if unposted_count >= config.autopost_unposted_threshold:
                    logger.error(f"❌ 安全弁 1 発動: LOOKBACK 時間内に未投稿動画が {unposted_count} 件存在（閾値: {config.autopost_unposted_threshold} 件）")
                    logger.warning(f"⚠️  設定エラーまたはデバッグ誤爆の可能性があります。AUTOPOST を起動抑止します。")
                    if not autopost_warning_shown:
                        # GUI にポップアップで通知（可能な場合）
                        autopost_warning_shown = True
                    continue  # このポーリングをスキップ

                # 安全弁解除
                autopost_warning_shown = False

                # 投稿間隔チェック
                now = datetime.now()
                should_post = last_post_time is None or \
                              (now - last_post_time).total_seconds() >= config.autopost_interval_minutes * 60

                if should_post:
                    # 動画種別フィルタリング付きで候補を取得
                    candidates = db.get_autopost_candidates(config)

                    if candidates:
                        # 最初の候補を選択（優先度順）
                        selected_video = candidates[0]
                        logger.info(f"🤖 AUTOPOST 対象を発見: {selected_video['title']}")

                        # 重複チェック（念のため）
                        if db.is_duplicate_post(selected_video['video_id']):
                            logger.warning(f"⚠️  この動画は既に投稿済みです（{selected_video['title']}）")
                            continue

                        # プラグイン実行
                        results = plugin_manager.post_video_with_all_enabled(selected_video, dry_run=not config.bluesky_post_enabled)
                        success = any(results.values()) or not config.bluesky_post_enabled

                        if success:
                            # DB を投稿済みにマーク
                            db.mark_as_posted(selected_video['video_id'])
                            last_post_time = now
                            if config.bluesky_post_enabled:
                                logger.info(f"✅ AUTOPOST 成功。次の投稿は {config.autopost_interval_minutes} 分後です。")
                            else:
                                logger.info(f"🧪 AUTOPOST ドライラン完了（投稿済みフラグ登録）。次の投稿は {config.autopost_interval_minutes} 分後です。")
                        else:
                            logger.error(f"❌ AUTOPOST 投稿失敗: {selected_video['title']}")
                    else:
                        logger.info("🤖 AUTOPOST: 投稿対象動画がありません。")
                else:
                    elapsed = (now - last_post_time).total_seconds() / 60
                    remaining = config.autopost_interval_minutes - elapsed
                    logger.info(f"🤖 AUTOPOST: 投稿間隔制限中。次の投稿まで約 {remaining:.1f} 分待機。")

            # ログメッセージの表示内容を実際の待機間隔に合わせる
            if config.youtube_feed_mode in ("websub", "hybrid") and websub_manager and websub_manager.is_subscribed():
                wait_interval_seconds = config.websub_poll_interval_minutes * 60
                logger.info(f"📡 WebSub モード: {config.websub_poll_interval_minutes} 分ごとに API をチェックします...")
            else:
                wait_interval_seconds = config.poll_interval_minutes * 60
                logger.info(f"📋 ポーリング モード: {config.poll_interval_minutes} 分ごとに RSS をチェックします...")

            # 待機中も stop_event をチェック（1秒間隔）
            # ★ 新: WebSub モード時は待機間隔を短くして、プッシュ通知をすぐ反映
            # WebSub 有効 → 10秒間隔でチェック
            # ポーリングのみ → poll_interval_minutes で待機
            if config.youtube_feed_mode in ("websub", "hybrid") and websub_manager and websub_manager.is_subscribed():
                # WebSub モード: websub_poll_interval_minutes で待機（理想: 1分）
                logger.debug(f"📡 WebSub モード確認済み: {config.websub_poll_interval_minutes} 分間隔で API チェック")
            else:
                logger.debug(f"📋 ポーリングモード: {config.poll_interval_minutes} 分間隔で RSS チェック")

            for _ in range(wait_interval_seconds):
                if stop_event.is_set():
                    raise KeyboardInterrupt()
                time.sleep(1)

    except KeyboardInterrupt:
        if "niconico_plugin" in plugin_manager.loaded_plugins:
            try:
                niconico_plugin = plugin_manager.loaded_plugins.get("niconico_plugin")
                if niconico_plugin and niconico_plugin.is_available():
                    logger.debug("[ニコニコプラグイン] 監視停止中...")
                    niconico_plugin.stop_monitoring()
            except Exception as plugin_error:
                logger.debug(f"[ニコニコプラグイン停止] エラー: {plugin_error}")
        logger.info("🛑 アプリケーションをシャットダウン中...")
        stop_event.set()
        gui_instance = None  # GUI インスタンスをクリア
        gui_thread.join(timeout=5)  # GUI スレッドの終了を待つ（最大5秒）
        gc.collect()  # 強制ガベージコレクション
        sys.exit(0)
    except Exception as e:
        logger.error(f"[予期せぬエラー] {type(e).__name__}: {e}", exc_info=True)
        if "niconico_plugin" in plugin_manager.loaded_plugins:
            try:
                niconico_plugin = plugin_manager.loaded_plugins.get("niconico_plugin")
                if niconico_plugin and niconico_plugin.is_available():
                    logger.debug("[ニコニコプラグイン] 監視停止中...")
                    niconico_plugin.stop_monitoring()
            except Exception as plugin_error:
                logger.debug(f"[ニコニコプラグイン停止] エラー: {plugin_error}")
        logger.info("🛑 アプリケーションをシャットダウン中...")
        stop_event.set()
        gui_instance = None  # GUI インスタンスをクリア
        gui_thread.join(timeout=5)  # GUI スレッドの終了を待つ（最大5秒）
        gc.collect()  # 強制ガベージコレクション
        sys.exit(1)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    if sys.platform.startswith('win'):
        signal.signal(signal.SIGBREAK, signal_handler)
    main()
