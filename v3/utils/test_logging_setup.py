# -*- coding: utf-8 -*-

"""
v3 ロギング設定の動作確認スクリプト

ロギングプラグイン非導入時に、全ロガーが正常に出力されるかテストします。
"""

import logging
import os
import sys
from pathlib import Path

# v3 ロギング設定をインポート
sys.path.insert(0, str(Path(__file__).parent))
from logging_config import setup_logging, get_logger

def test_logging_setup():
    """全ロガーが正常に動作するかテスト"""

    print("=" * 70)
    print("v3 ロギング設定テスト - プラグイン非導入時の動作確認")
    print("=" * 70)
    print()

    # ロギング設定（デバッグモード OFF）
    logger = setup_logging(debug_mode=False)
    print()

    # テスト対象のロガー
    test_loggers = [
        ("AppLogger", "アプリケーション全般"),
        ("PostLogger", "投稿ログ"),
        ("YouTubeLogger", "YouTube 関連"),
        ("NiconicoLogger", "ニコニコ関連"),
        ("GUILogger", "GUI 操作"),
        ("ThumbnailsLogger", "サムネイル処理"),
        ("AuditLogger", "監査ログ"),
        ("TunnelLogger", "トンネル接続"),
        ("PostErrorLogger", "投稿エラー"),
    ]

    print("\n📋 各ロガーへの出力テスト:")
    print("-" * 70)

    for logger_name, description in test_loggers:
        test_logger = get_logger(logger_name)

        # ハンドラーの確認
        handlers = test_logger.handlers
        handler_info = f"({len(handlers)} ハンドラー: {', '.join([type(h).__name__ for h in handlers])})"

        # ログレベルの確認
        level_name = logging.getLevelName(test_logger.level)

        print(f"\n✓ {logger_name:<20} - {description}")
        print(f"  レベル: {level_name}")
        print(f"  ハンドラー: {handler_info}")

        # テスト出力
        test_logger.info(f"ℹ️ {logger_name} からのテスト出力（INFO レベル）")
        test_logger.debug(f"🔍 {logger_name} からのテスト出力（DEBUG レベル）")
        test_logger.warning(f"⚠️ {logger_name} からのテスト出力（WARNING レベル）")

    print("\n" + "=" * 70)
    print("✅ ロギング設定テスト完了")
    print("=" * 70)
    print()
    print("📁 ログファイル出力先:")
    print("   - logs/app.log     : INFO・DEBUG ログ（サイズローテーション 10MB）")
    print("   - logs/error.log   : WARNING 以上のエラー（サイズローテーション 5MB）")
    print()
    print("🔍 確認項目:")
    print("   1. logs/app.log に全ロガーからの INFO・DEBUG ログが出力されている")
    print("   2. logs/error.log に全ロガーからの WARNING ログが出力されている")
    print("   3. コンソールに INFO ログが出力されている")
    print()

def test_logging_setup_debug_mode():
    """デバッグモード時のテスト"""

    print("\n" + "=" * 70)
    print("v3 ロギング設定テスト - デバッグモード有効時")
    print("=" * 70)
    print()

    # ロギング設定（デバッグモード ON）
    logger = setup_logging(debug_mode=True)
    print()

    test_logger = get_logger("YouTubeLogger")

    print("\n📋 デバッグモード有効時のテスト出力:")
    print("-" * 70)
    test_logger.debug("🔍 DEBUG ログ（デバッグモード有効時）")
    test_logger.info("ℹ️ INFO ログ")
    test_logger.warning("⚠️ WARNING ログ")

    print("\n" + "=" * 70)
    print("✅ デバッグモードテスト完了")
    print("=" * 70)
    print()

if __name__ == "__main__":
    # テスト実行
    test_logging_setup()

    # デバッグモードテスト
    test_logging_setup_debug_mode()

    print("\n✨ すべてのテストが完了しました")
    print("   logs/app.log と logs/error.log の内容を確認してください。")
