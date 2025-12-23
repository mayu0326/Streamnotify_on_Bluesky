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
__license__ = "GPLv3"


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
    except Exception as e:
        logger.debug(f"YouTubeAPI プラグインのロード失敗: {e}")

    # YouTubeLive 検出プラグインを手動でロード・有効化
    try:
        plugin_manager.load_plugin("youtube_live_plugin", os.path.join("plugins", "youtube_live_plugin.py"))
        asset_manager.deploy_plugin_assets("youtube_live_plugin")

        # ★ YouTube Live プラグインに plugin_manager を注入（自動投稿用）
        # ★ IMPORTANT: enable_plugin() より前に注入する必要がある（on_enable で自動投稿ロジックが実行されるため）
        live_plugin = plugin_manager.get_plugin("youtube_live_plugin")
        if live_plugin:
            live_plugin.set_plugin_manager(plugin_manager)

        # ★ 注入完了後に有効化（on_enable() が呼ばれる）
        plugin_manager.enable_plugin("youtube_live_plugin")

        # ★ プラグイン判定後に GUI を自動リロード
        if gui_instance:
            logger.debug("🔄 YouTube Live プラグイン判定後、GUI を再読込します...")
            try:
                gui_instance.refresh_data()
                logger.info("✅ GUI を自動更新しました")
            except Exception as e:
                logger.debug(f"⚠️ GUI 自動更新に失敗（無視）: {e}")
    except Exception as e:
        logger.debug(f"YouTubeLive 検出プラグインのロード失敗: {e}")


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

    stop_event = threading.Event()
    gui_thread = threading.Thread(target=run_gui, args=(db, plugin_manager, stop_event, bluesky_core), daemon=True)
    gui_thread.start()
    logger.info("✅ アプリケーションの起動が完了しました。 管理画面を開きます。")

    # ===== YouTube Live 終了検知用の定期ポーリングスレッド =====
    def start_youtube_live_polling():
        """YouTubeLive ライブ終了検知の定期ポーリングを開始"""
        import time

        # ポーリング間隔（分） - 最短15分、最長1時間に制限
        poll_interval_minutes = int(os.getenv("YOUTUBE_LIVE_POLL_INTERVAL", "15"))

        # バリデーション：最短15分、最長60分
        if poll_interval_minutes < 15:
            logger.warning(f"⚠️ YOUTUBE_LIVE_POLL_INTERVAL={poll_interval_minutes} は短すぎます（最短15分）")
            poll_interval_minutes = 15
        elif poll_interval_minutes > 60:
            logger.warning(f"⚠️ YOUTUBE_LIVE_POLL_INTERVAL={poll_interval_minutes} は長すぎます（最長60分）")
            poll_interval_minutes = 60

        # ★ 修正: 旧フラグではなく新 MODE 変数で判定
        # YOUTUBE_LIVE_AUTO_POST_MODE が "all" または "live" の場合のみポーリング有効
        mode = os.getenv("YOUTUBE_LIVE_AUTO_POST_MODE", "off").lower()
        if mode not in ("all", "live"):
            logger.info(f"ℹ️ YOUTUBE_LIVE_AUTO_POST_MODE={mode} のためライブ終了検知は無効です")
            return

        logger.info(f"📡 YouTubeLive ライブ終了検知ポーリングを開始します（間隔: {poll_interval_minutes} 分）")

        while not stop_event.is_set():
            try:
                live_plugin = plugin_manager.get_plugin("youtube_live_plugin")
                if live_plugin and live_plugin.is_available():
                    logger.debug("🔄 YouTubeLive ライブ終了チェック実行...")
                    live_plugin.poll_live_status()
                else:
                    logger.debug("ℹ️ YouTubeLive プラグインが利用不可")
            except Exception as e:
                logger.error(f"❌ ライブ終了チェックエラー: {e}")

            # 待機
            for _ in range(poll_interval_minutes * 60):
                if stop_event.is_set():
                    break
                time.sleep(1)

    # ライブ終了検知スレッド開始
    live_polling_thread = threading.Thread(target=start_youtube_live_polling, daemon=True)
    live_polling_thread.start()

    polling_count = 0
    last_post_time = None
    autopost_warning_shown = False  # セーフモード警告フラグ
    safe_mode_enabled = False       # セーフモード有効フラグ（仕様 5.3）

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

            logger.info("[YouTube] YouTubeRSS から情報を取得しています...")
            # YouTube RSS フェッチ・DB 保存・画像自動処理
            from thumbnails.youtube_thumb_utils import get_youtube_thumb_manager
            thumb_mgr = get_youtube_thumb_manager()
            saved_count = thumb_mgr.fetch_and_ensure_images(config.youtube_channel_id)

            # ★ 新: YouTube RSS 取得後、YouTube Live プラグインで自動分類を実行
            # 配信予定枠などが正しく content_type="live", live_status="upcoming" として分類される
            if saved_count > 0 or polling_count == 1:  # 新規動画があるか初回ポーリング時に実行
                try:
                    live_plugin = plugin_manager.get_plugin("youtube_live_plugin")
                    if live_plugin and live_plugin.is_available():
                        logger.info(f"🔍 YouTube Live プラグイン: 未判定動画を自動分類中...")
                        updated = live_plugin._update_unclassified_videos()
                        if updated > 0:
                            logger.info(f"✅ YouTube Live 自動分類: {updated} 件更新（配信予定枠など検出）")
                except Exception as e:
                    logger.debug(f"⚠️ YouTube Live プラグインの自動分類エラー: {e}")

            if config.is_collect_mode:
                logger.info("[モード] 収集モード のため、投稿処理をスキップします。")
            elif config.operation_mode == OperationMode.SELFPOST:
                # === SELFPOST モード（手動投稿のみ）===
                logger.info("[モード] SELFPOST モード。投稿対象を GUI から設定してください。")
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
                        results = plugin_manager.post_video_with_all_enabled(selected_video)
                        success = any(results.values())

                        if success:
                            # DB を投稿済みにマーク
                            db.mark_as_posted(selected_video['video_id'])
                            last_post_time = now
                            logger.info(f"✅ AUTOPOST 成功。次の投稿は {config.autopost_interval_minutes} 分後です。")
                        else:
                            logger.error(f"❌ AUTOPOST 投稿失敗: {selected_video['title']}")
                    else:
                        logger.info("🤖 AUTOPOST: 投稿対象動画がありません。")
                else:
                    elapsed = (now - last_post_time).total_seconds() / 60
                    remaining = config.autopost_interval_minutes - elapsed
                    logger.info(f"🤖 AUTOPOST: 投稿間隔制限中。次の投稿まで約 {remaining:.1f} 分待機。")

            logger.info(f"次のポーリングまで {config.poll_interval_minutes} 分待機中...")
            # 待機中も stop_event をチェック（1秒間隔）
            for _ in range(config.poll_interval_minutes * 60):
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
