#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
v3/utils内のすべてのPythonファイルのパス計算エラーを修正するスクリプト
"""

import os
import re
from pathlib import Path

REPLACEMENTS = [
    # パターン1: parent.parent / "v2" → parent.parent.parent
    {
        "pattern": r'Path\(__file__\)\.parent\.parent / ["\']v2["\']',
        "replacement": r'Path(__file__).parent.parent.parent',
        "description": "v2参照を v3 に修正（parent.parent / 'v2'）"
    },
    # パターン2: parent.parent / "v3" → parent.parent.parent
    {
        "pattern": r'Path\(__file__\)\.parent\.parent / ["\']v3["\']',
        "replacement": r'Path(__file__).parent.parent.parent',
        "description": "v3参照を v3 に修正（parent.parent / 'v3'）"
    },
    # パターン3: sys.path.insert with v2 path
    {
        "pattern": r'sys\.path\.insert\(0, str\(Path\(__file__\)\.parent\.parent / ["\']v2["\']\)\)',
        "replacement": r'sys.path.insert(0, str(Path(__file__).parent.parent.parent))',
        "description": "sys.path の v2 参照を v3 に修正"
    },
    # パターン4: 深いディレクトリの場合 parent.parent.parent / "v3"
    {
        "pattern": r'Path\(__file__\)\.parent\.parent\.parent / ["\']v3["\']',
        "replacement": r'Path(__file__).parent.parent.parent.parent',
        "description": "深いディレクトリの v3 参照を修正"
    },
    # パターン5: 相対パス "data/video_list.db" → 絶対パス
    {
        "pattern": r'DB_PATH = ["\']data/video_list\.db["\']',
        "replacement": r'DB_PATH = Path(__file__).parent.parent.parent / "data" / "video_list.db"',
        "description": "DB相対パスを絶対パスに修正"
    },
    # パターン6: sqlite3.connect() の引数を str() でラップ
    {
        "pattern": r'sqlite3\.connect\(DB_PATH\)',
        "replacement": r'sqlite3.connect(str(DB_PATH))',
        "description": "DB接続時にPathをstr化"
    }
]

def fix_file(file_path):
    """ファイルを修正"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        for rule in REPLACEMENTS:
            content = re.sub(rule['pattern'], rule['replacement'], content)
        
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        return False
    
    except Exception as e:
        print(f"  ❌ エラー: {e}")
        return False

def main():
    """メイン処理"""
    utils_dir = Path(__file__).parent
    python_files = sorted(utils_dir.glob("**/*.py"))
    
    print("=" * 70)
    print("v3/utils 内のパス計算エラーを一括修正")
    print("=" * 70)
    
    fixed_count = 0
    total_count = len(python_files)
    
    for file_path in python_files:
        # 自身を除外
        if file_path.name == "fix_all_paths.py":
            continue
        
        rel_path = file_path.relative_to(utils_dir)
        print(f"\n🔍 {rel_path}")
        
        if fix_file(file_path):
            print(f"  ✅ 修正完了")
            fixed_count += 1
        else:
            print(f"  ℹ️  変更なし")
    
    print("\n" + "=" * 70)
    print(f"📊 修正完了: {fixed_count}/{total_count} ファイル")
    print("=" * 70)

if __name__ == "__main__":
    main()
