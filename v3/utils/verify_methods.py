#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""メソッド検証スクリプト"""

import ast
import sys

def check_gui_methods():
    """gui_v3.py のメソッドを検証"""

    with open('gui_v3.py', 'r', encoding='utf-8-sig') as f:
        tree = ast.parse(f.read())

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == 'StreamNotifyGUI':
            methods = [m.name for m in node.body if isinstance(m, ast.FunctionDef)]

            required_methods = [
                'add_video_dialog',
                '_add_video_from_id',
                '_video_exists',
                '_extract_video_id',
                '_add_video_manual'
            ]

            print("=" * 70)
            print("StreamNotifyGUI クラスの検証")
            print("=" * 70)
            print(f"✅ 総メソッド数: {len(methods)}\n")

            all_found = True
            for method in required_methods:
                if method in methods:
                    print(f"  ✅ {method}")
                else:
                    print(f"  ❌ {method} が見つかりません")
                    all_found = False

            print("\n" + "=" * 70)
            if all_found:
                print("✅ すべてのメソッドが正しく配置されています！")
                return True
            else:
                print("❌ 一部のメソッドが見つかりません")
                return False

    print("❌ StreamNotifyGUI クラスが見つかりません")
    return False

if __name__ == '__main__':
    success = check_gui_methods()
    sys.exit(0 if success else 1)
