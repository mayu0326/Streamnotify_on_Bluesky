# -*- coding: utf-8 -*-
"""
現在の設定状況を確認するスクリプト
"""

from config import get_config

config = get_config("settings.env")

print("=" * 60)
print("📋 現在の設定状況")
print("=" * 60)

print(f"\n🎬 動作モード: {config.operation_mode}")
print(f"   - SELFPOST (手動投稿)：投稿は GUI から手動で行う")
print(f"   - AUTOPOST (自動投稿)：配信予定枠は自動で投稿される")

print(f"\n🔴 YouTube Live 自動投稿設定:")
print(f"   YOUTUBE_LIVE_AUTO_POST_MODE: {config.youtube_live_autopost_mode}")
print(f"   YOUTUBE_LIVE_AUTO_POST_SCHEDULE: {config.youtube_live_auto_post_schedule}")

print(f"\n📊 動作内容:")
if str(config.operation_mode).lower() == "selfpost":
    print(f"   ✅ SELFPOST モード = 手動投稿モード")
    print(f"   ✅ RSS から配信予定枠は自動検出・分類される")
    print(f"   ⚠️ 問題: YOUTUBE_LIVE_AUTO_POST_MODE=schedule は AUTOPOST モードのみで機能します")
    print(f"   ⚠️ SELFPOST モード では投稿は自動ではなく、GUI から手動で行う必要があります")
    print(f"\n   👉 配信予定枠を自動投稿するには：")
    print(f"      1. APP_MODE=autopost に変更")
    print(f"      2. アプリを再起動")
    print(f"      3. 次のポーリングから自動投稿が開始されます")
elif str(config.operation_mode).lower() == "autopost":
    print(f"   ✅ AUTOPOST モード = 自動投稿モード")
    print(f"   ✅ RSS から配信予定枠は自動検出・分類・投稿される")
    if config.youtube_live_autopost_mode == "schedule":
        print(f"   ✅ YOUTUBE_LIVE_AUTO_POST_MODE=schedule で配信予定枠が自動投稿されます")

print("\n" + "=" * 60)
