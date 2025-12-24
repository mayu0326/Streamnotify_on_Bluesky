# -*- coding: utf-8 -*-

"""
GUI 動画追加機能のテスト

動画追加ダイアログが正常に動作することを確認します。
"""

import sys
import os
from pathlib import Path

# パスを追加
sys.path.insert(0, str(Path(__file__).parent))

from database import get_database
from plugin_manager import PluginManager

def test_extract_video_id():
    """動画ID抽出のテスト"""
    print("=" * 80)
    print("テスト: 動画ID抽出機能")
    print("=" * 80)

    from gui_v3 import StreamNotifyGUI
    import tkinter as tk

    root = tk.Tk()
    root.withdraw()  # 画面を非表示

    db = get_database()
    gui = StreamNotifyGUI(root, db)

    test_cases = [
        ("dQw4w9WgXcQ", "dQw4w9WgXcQ", "動画IDのみ"),
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ", "youtube.com URL"),
        ("https://youtu.be/dQw4w9WgXcQ", "dQw4w9WgXcQ", "youtu.be URL"),
        ("https://www.youtube.com/embed/dQw4w9WgXcQ", "dQw4w9WgXcQ", "embed URL"),
        ("invalid", None, "不正な形式"),
    ]

    for input_val, expected, description in test_cases:
        result = gui._extract_video_id(input_val)
        status = "✅" if result == expected else "❌"
        print(f"{status} {description}")
        print(f"   入力: {input_val}")
        print(f"   期待値: {expected}")
        print(f"   結果: {result}")
        print()

    root.destroy()

def test_video_exists():
    """動画存在確認のテスト"""
    print("=" * 80)
    print("テスト: 動画存在確認")
    print("=" * 80)

    from gui_v3 import StreamNotifyGUI
    import tkinter as tk

    root = tk.Root()
    root.withdraw()  # 画面を非表示

    db = get_database()
    gui = StreamNotifyGUI(root, db)

    # DB内の最初の動画を取得
    all_videos = db.get_all_videos()
    if all_videos:
        first_video = all_videos[0]
        video_id = first_video.get("video_id")

        exists = gui._video_exists(video_id)
        status = "✅" if exists else "❌"
        print(f"{status} 動画存在確認: {video_id}")
        print(f"   結果: {exists}")
    else:
        print("⚠️ DBに動画がありません")

    root.destroy()

if __name__ == "__main__":
    try:
        test_extract_video_id()
        print()
        test_video_exists()
        print()
        print("=" * 80)
        print("✅ すべてのテストが完了しました")
        print("=" * 80)
    except Exception as e:
        print(f"❌ テストエラー: {e}")
        import traceback
        traceback.print_exc()
