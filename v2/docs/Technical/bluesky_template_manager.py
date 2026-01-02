# -*- coding: utf-8 -*-

"""
Stream notify on Bluesky - v2 Bluesky プラグイン用テンプレート管理

Bluesky プラグインのテンプレート機能を管理し、GUI から簡単に
テンプレート編集ダイアログを呼び出すためのインターフェース。

テンプレート保存後、自動的にプラグイン側で反映されます（v2.x 以降）。

注意: Vanilla 環境では Bluesky プラグイン無効のため、
      このモジュールも読み込まれません。
      テンプレート仕様と UI は備わっていますが、実行されません。
"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any
import sys

logger = logging.getLogger("AppLogger")
post_logger = logging.getLogger("PostLogger")

__author__ = "mayuneco(mayunya)"
__copyright__ = "Copyright (C) 2025 mayuneco(mayunya)"
__license__ = "GPLv2"


class BlueskyTemplateManager:
    """Bluesky プラグイン用テンプレート管理クラス

    テンプレート編集ダイアログの呼び出しとファイル管理を行う。
    """

    def __init__(self):
        """初期化"""
        self.logger = logger

    def open_template_editor(
        self,
        master_window,
        template_type: str,
        initial_text: str = "",
        on_save_callback=None
    ) -> None:
        """
        テンプレート編集ダイアログを開く。

        Args:
            master_window: 親ウィンドウ（tkinter.Tk or customtkinter.CTk）
            template_type: テンプレート種別（例: "youtube_new_video"）
            initial_text: 初期テンプレートテキスト
            on_save_callback: 保存時のコールバック (optional)

        例:
            manager = BlueskyTemplateManager()

            def on_template_saved(text, template_type):
                print(f"Template {template_type} saved!")

            manager.open_template_editor(
                master_window=root,
                template_type="youtube_new_video",
                initial_text="{{ title }} | {{ channel_name }}",
                on_save_callback=on_template_saved
            )
        """
        try:
            from template_editor_dialog import TemplateEditorDialog

            # デフォルトコールバックの定義
            if on_save_callback is None:
                def on_save_callback(text, template_type):
                    post_logger.info(f"✅ テンプレート編集ダイアログからの保存: {template_type}")
                    # 自動的にファイルに保存
                    self._save_template_file(template_type, text)

            # ダイアログを開く
            dialog = TemplateEditorDialog(
                master=master_window,
                template_type=template_type,
                initial_text=initial_text,
                on_save=on_save_callback
            )

            self.logger.debug(f"🔍 テンプレート編集ダイアログを開きました: {template_type}")

        except ImportError as e:
            self.logger.error(f"❌ template_editor_dialog インポート失敗: {e}")
            raise

        except Exception as e:
            self.logger.error(f"❌ テンプレート編集ダイアログ起動エラー: {e}")
            raise

    def _save_template_file(self, template_type: str, template_text: str) -> bool:
        """
        テンプレートをファイルに保存する内部メソッド。

        Args:
            template_type: テンプレート種別
            template_text: テンプレートテキスト

        Returns:
            保存成功フラグ
        """
        try:
            from template_utils import save_template_file

            success, message = save_template_file(template_type, template_text)

            if success:
                post_logger.info(message)
            else:
                post_logger.error(message)

            return success

        except Exception as e:
            self.logger.error(f"❌ テンプレート保存エラー: {e}")
            return False

    def get_template_text(self, template_type: str) -> Optional[str]:
        """
        指定されたテンプレートファイルのテキストを読み込む。

        Args:
            template_type: テンプレート種別

        Returns:
            テンプレートテキスト、ファイルがない場合は None
        """
        try:
            from template_utils import get_template_path

            template_path = get_template_path(template_type)

            if not template_path or not Path(template_path).exists():
                self.logger.warning(f"⚠️ テンプレートファイルが見つかりません: {template_type}")
                return None

            with open(template_path, encoding="utf-8") as f:
                text = f.read()

            self.logger.debug(f"✅ テンプレート読み込み成功: {template_type}")
            return text

        except Exception as e:
            self.logger.error(f"❌ テンプレート読み込みエラー: {e}")
            return None


# グローバルインスタンス
_template_manager = None


def get_bluesky_template_manager() -> BlueskyTemplateManager:
    """グローバル BlueskyTemplateManager インスタンスを取得（シングルトン）"""
    global _template_manager
    if _template_manager is None:
        _template_manager = BlueskyTemplateManager()
    return _template_manager


# ============ GUI 統合用ユーティリティ ============


def open_template_editor_from_gui(
    master_window,
    template_type: str,
    parent_callback=None
) -> None:
    """
    GUI（gui_v2.py など）から簡単にテンプレート編集ダイアログを開くヘルパー関数。

    Args:
        master_window: 親ウィンドウ
        template_type: テンプレート種別
        parent_callback: ダイアログ閉じる時の親ウィンドウコールバック (optional)

    例:
        # gui_v2.py の TemplateEditorFrame 等で
        from bluesky_template_manager import open_template_editor_from_gui

        open_template_editor_from_gui(
            master_window=self.root,
            template_type="youtube_new_video",
            parent_callback=self.on_template_updated
        )
    """
    manager = get_bluesky_template_manager()
    initial_text = manager.get_template_text(template_type) or ""

    def on_save_with_callback(text, ttype):
        manager._save_template_file(ttype, text)
        if parent_callback:
            parent_callback(ttype)

    manager.open_template_editor(
        master_window=master_window,
        template_type=template_type,
        initial_text=initial_text,
        on_save_callback=on_save_with_callback
    )


if __name__ == "__main__":
    """モジュールテスト"""
    print("BlueskyTemplateManager - v2.1.0")
    print("=" * 50)

    manager = get_bluesky_template_manager()
    print(f"✅ BlueskyTemplateManager 初期化完了")

    # テンプレート読み込みテスト
    text = manager.get_template_text("youtube_new_video")
    if text:
        print(f"✅ テンプレート読み込み成功 ({len(text)} 文字)")
    else:
        print(f"ℹ️ テンプレートファイルが見つかりません")

    print("=" * 50)
