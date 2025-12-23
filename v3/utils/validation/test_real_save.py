#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
実際の環境でニコニコプラグインのユーザー名自動保存機能をテスト
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, r"d:\Documents\GitHub\Streamnotify_on_Bluesky\v2")

from database import get_database
from plugins.niconico_plugin import NiconicoPlugin

# 設定ファイルの現在の状態を確認
SETTINGS_ENV = Path(r"d:\Documents\GitHub\Streamnotify_on_Bluesky\v2\settings.env")

print("=" * 70)
print("実装テスト：ニコニコプラグインのユーザー名自動保存")
print("=" * 70)

print(f"\n【Step 1】設定ファイルの初期状態を確認")
print(f"ファイル: {SETTINGS_ENV}")
with open(SETTINGS_ENV, 'r', encoding='utf-8') as f:
    lines = f.readlines()
    for i, line in enumerate(lines):
        if 'NICONICO_USER_ID' in line or 'NICONICO_USER_NAME' in line:
            print(f"  Line {i+1}: {line.rstrip()}")

print(f"\n【Step 2】ニコニコプラグインを初期化")
db = get_database(db_path="data/video_list.db")
os.environ.pop('NICONICO_USER_NAME', None)  # 環境変数をクリア

plugin = NiconicoPlugin(
    user_id="24578132",
    poll_interval=10,
    db=db,
    user_name=None
)

print(f"  User ID: {plugin.user_id}")
print(f"  Plugin available: {plugin.is_available()}")

print(f"\n【Step 3】ユーザー名を取得（優先度チェーンで自動取得）")
user_name = plugin._get_user_name()
print(f"  取得されたユーザー名: {user_name}")

print(f"\n【Step 4】設定ファイルが更新されたか確認")
with open(SETTINGS_ENV, 'r', encoding='utf-8') as f:
    lines = f.readlines()
    for i, line in enumerate(lines):
        if 'NICONICO_USER_ID' in line or 'NICONICO_USER_NAME' in line:
            print(f"  Line {i+1}: {line.rstrip()}")

# 結果判定
print(f"\n【結果】")
with open(SETTINGS_ENV, 'r', encoding='utf-8') as f:
    content = f.read()
    if f"NICONICO_USER_NAME={user_name}" in content:
        print(f"✅ SUCCESS: 設定ファイルに自動保存されました！")
        print(f"   NICONICO_USER_NAME={user_name}")
    else:
        print(f"❌ FAILED: 設定ファイルに保存されていません")

print("\n" + "=" * 70)
