# -*- coding: utf-8 -*-

"""
Stream notify on Bluesky - v2 ロギング設定

ロギングの設定を一元管理するモジュール。
ロギングプラグインが導入されている場合は、そちらの設定を優先的に使用。
"""



import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


# --- コンソール用: exc_infoを完全に抑制するHandler ---
class NoExcInfoStreamHandler(logging.StreamHandler):
    def emit(self, record):
        orig_exc_info = record.exc_info
        orig_exc_text = record.exc_text
        record.exc_info = None
        record.exc_text = None
        try:
            super().emit(record)
        finally:
            record.exc_info = orig_exc_info
            record.exc_text = orig_exc_text

# --- CRLF→LF対応: LFでファイルを開くRotatingFileHandler ---
import io
class LFRotatingFileHandler(RotatingFileHandler):
    def _open(self):
        # encoding, errors, newline を明示的に指定
        return open(self.baseFilename, self.mode, encoding=self.encoding, errors=self.errors, newline='\n')

__author__ = "mayuneco(mayunya)"
__copyright__ = "Copyright (C) 2025 mayuneco(mayunya)"
__license__ = "GPLv2"


def _try_load_logging_plugin():
    """
    ロギングプラグインの読み込みを試みる
    
    Returns:
        LoggingPlugin or None: プラグインインスタンス、または None
    """
    try:
        # plugins/logging_plugin.py の存在確認
        plugin_path = Path(__file__).parent / "plugins" / "logging_plugin.py"
        if not plugin_path.exists():
            return None
        
        # プラグインをインポート
        from plugins.logging_plugin import get_logging_plugin
        plugin = get_logging_plugin()
        
        # プラグインが利用可能か確認
        if plugin.is_available():
            return plugin
        else:
            return None
    except Exception as e:
        # プラグインの読み込みに失敗した場合は None を返す
        print(f"Warning: ロギングプラグインの読み込みに失敗しました: {e}")
        return None


def setup_logging(debug_mode=False):
    """
    ロギングを設定
    
    ロギングプラグインが利用可能な場合はそちらを使用、
    そうでない場合はデフォルトのシンプルな設定を使用。

    Args:
        debug_mode: デバッグモードの有効/無効（True でログレベルを DEBUG に設定）

    Returns:
        logging.Logger: 設定済みのAppLoggerインスタンス
    """
    # まずロギングプラグインの読み込みを試みる
    logging_plugin = _try_load_logging_plugin()
    
    if logging_plugin:
        # プラグインが利用可能な場合
        logging_plugin.configure_logging()
        logger = logging.getLogger("AppLogger")
        logger.info(f"✅ {logging_plugin.get_name()} v{logging_plugin.get_version()} を使用してロギング設定を行いました")
        
        # デバッグモードの反映
        if debug_mode:
            _apply_debug_mode(logger)
        
        return logger
    
    # プラグインが利用できない場合は、デフォルトのシンプルな設定を使用
    os.makedirs("logs", exist_ok=True)

    logger = logging.getLogger("AppLogger")
    logger.setLevel(logging.DEBUG if debug_mode else logging.INFO)

    # 既にハンドラが設定されている場合はスキップ（重複防止）
    if logger.handlers:
        return logger


    # --- app.log: INFO以下, LF改行 ---
    app_fh = LFRotatingFileHandler(
        "logs/app.log",
        maxBytes=10*1024*1024,
        backupCount=5,
        encoding="utf-8"
    )
    app_fh.setLevel(logging.DEBUG if debug_mode else logging.INFO)
    # INFO未満（DEBUGのみ）をapp.logに出力、WARNING以上はerror.logへ
    app_fh.addFilter(lambda record: record.levelno < logging.WARNING)

    # --- error.log: WARNING以上のみ, LF改行 ---
    error_fh = LFRotatingFileHandler(
        "logs/error.log",
        maxBytes=5*1024*1024,
        backupCount=3,
        encoding="utf-8"
    )
    error_fh.setLevel(logging.WARNING)
    error_fh.addFilter(lambda record: record.levelno >= logging.WARNING)

    # --- コンソール ---
    ch = NoExcInfoStreamHandler()
    ch.setLevel(logging.DEBUG if debug_mode else logging.INFO)
    # コンソールは INFO 以下のみ出力（WARNING・ERROR は app.log / error.log のみ）
    ch.addFilter(lambda record: record.levelno < logging.WARNING)


    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    app_fh.setFormatter(formatter)
    error_fh.setFormatter(formatter)
    ch.setFormatter(formatter)

    logger.addHandler(app_fh)
    logger.addHandler(error_fh)
    logger.addHandler(ch)

    mode_msg = "デバッグモード" if debug_mode else "デフォルトのロギング設定"
    logger.info(f"ℹ️  {mode_msg}を使用しています")

    return logger


def get_logger():
    """
    設定済みのAppLoggerを取得

    Returns:
        logging.Logger: AppLoggerインスタンス
    """
    return logging.getLogger("AppLogger")


def _apply_debug_mode(logger):
    """
    全ロガーにデバッグモードを適用
    
    Args:
        logger: 対象のロガーインスタンス
    """
    # ロガーのレベルのみをDEBUGに設定（ハンドラーレベルは変更しない）
    logger.setLevel(logging.DEBUG)
    
    # ルートロガーもDEBUGに設定
    logging.getLogger().setLevel(logging.DEBUG)
    
    # 全てのロガーをデバッグモードに設定（ハンドラーレベルは変更しない）
    for loggers_dict in [logging.Logger.manager.loggerDict]:
        for logger_name in loggers_dict:
            target_logger = logging.getLogger(logger_name)
            target_logger.setLevel(logging.DEBUG)
    
    logger.debug("🔍 デバッグモードが有効になりました")
