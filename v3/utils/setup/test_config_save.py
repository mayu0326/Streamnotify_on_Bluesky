#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
設定ファイル保存機能のテスト
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, r"d:\Documents\GitHub\Streamnotify_on_Bluesky\v2")

# テスト用の一時設定ファイルを作成
test_settings_dir = Path(r"d:\Documents\GitHub\Streamnotify_on_Bluesky\v2\test_settings")
test_settings_dir.mkdir(exist_ok=True)

test_env_file = test_settings_dir / "test_settings.env"

print("=" * 70)
print("Test 1: 空の NICONICO_USER_NAME に値を書き込む")
print("=" * 70)

# テスト用設定ファイルを作成
with open(test_env_file, 'w', encoding='utf-8') as f:
    f.write("""# Niconico Settings
NICONICO_USER_ID=24578132
NICONICO_USER_NAME=
""")

print(f"\n【初期状態】{test_env_file}")
with open(test_env_file, 'r', encoding='utf-8') as f:
    print(f.read())

# モック版のテスト
from unittest.mock import patch, MagicMock

# データベースのモック
mock_db = MagicMock()

# プラグイン設定ファイルのパスを上書き
with patch('plugins.niconico_plugin.SETTINGS_ENV_PATH', test_env_file):
    from plugins.niconico_plugin import NiconicoPlugin

    # プラグインを初期化（NICONICO_USER_NAME は未設定）
    os.environ.pop('NICONICO_USER_NAME', None)
    plugin = NiconicoPlugin(
        user_id="24578132",
        poll_interval=10,
        db=mock_db,
        user_name=None  # 明示的に None
    )

    # 設定ファイル保存メソッドをテスト
    print(f"\n【動作】_save_user_name_to_config('まゆにゃ！') を実行")
    plugin._save_user_name_to_config("まゆにゃ！")

    print(f"\n【結果】{test_env_file}")
    with open(test_env_file, 'r', encoding='utf-8') as f:
        content = f.read()
        print(content)
        if "NICONICO_USER_NAME=まゆにゃ！" in content:
            print("\n✅ TEST PASSED: 値が正しく書き込まれました")
        else:
            print("\n❌ TEST FAILED: 値が書き込まれていません")

print("\n" + "=" * 70)
print("Test 2: 既に値がある NICONICO_USER_NAME は上書きしない")
print("=" * 70)

# テスト用設定ファイルを作成（既に値がある）
with open(test_env_file, 'w', encoding='utf-8') as f:
    f.write("""# Niconico Settings
NICONICO_USER_ID=24578132
NICONICO_USER_NAME=既存値
""")

print(f"\n【初期状態】{test_env_file}")
with open(test_env_file, 'r', encoding='utf-8') as f:
    print(f.read())

with patch('plugins.niconico_plugin.SETTINGS_ENV_PATH', test_env_file):
    from plugins.niconico_plugin import NiconicoPlugin

    os.environ.pop('NICONICO_USER_NAME', None)
    plugin = NiconicoPlugin(
        user_id="24578132",
        poll_interval=10,
        db=mock_db,
        user_name=None
    )

    print(f"\n【動作】_save_user_name_to_config('新しい値') を実行")
    plugin._save_user_name_to_config("新しい値")

    print(f"\n【結果】{test_env_file}")
    with open(test_env_file, 'r', encoding='utf-8') as f:
        content = f.read()
        print(content)
        if "NICONICO_USER_NAME=既存値" in content:
            print("\n✅ TEST PASSED: 既存値が保護されました")
        else:
            print("\n❌ TEST FAILED: 既存値が上書きされました")

print("\n" + "=" * 70)
print("Test 3: 環境変数が設定されている場合は書き込まない")
print("=" * 70)

# テスト用設定ファイルを作成（空）
with open(test_env_file, 'w', encoding='utf-8') as f:
    f.write("""# Niconico Settings
NICONICO_USER_ID=24578132
NICONICO_USER_NAME=
""")

print(f"\n【初期状態】{test_env_file}")
with open(test_env_file, 'r', encoding='utf-8') as f:
    print(f.read())

with patch('plugins.niconico_plugin.SETTINGS_ENV_PATH', test_env_file):
    from plugins.niconico_plugin import NiconicoPlugin

    os.environ['NICONICO_USER_NAME'] = '環境変数値'
    plugin = NiconicoPlugin(
        user_id="24578132",
        poll_interval=10,
        db=mock_db,
        user_name='環境変数値'
    )

    print(f"\n【動作】環境変数='環境変数値' でプラグイン初期化後、_save_user_name_to_config('新しい値') を実行")
    plugin._save_user_name_to_config("新しい値")

    print(f"\n【結果】{test_env_file}")
    with open(test_env_file, 'r', encoding='utf-8') as f:
        content = f.read()
        print(content)
        if content.count("=") == 2 and "NICONICO_USER_NAME=\n" in content:
            print("\n✅ TEST PASSED: 環境変数設定時は書き込みがスキップされました")
        else:
            print("\n❌ TEST FAILED: 書き込みが行われました")

print("\n" + "=" * 70)

# クリーンアップ
import shutil
shutil.rmtree(test_settings_dir, ignore_errors=True)
