#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
新しいYouTube配信枠の検出診断スクリプト

目的: なぜ新しい配信が検出されないかを診断
"""

import sys
import os
from pathlib import Path

# v3 モジュールを import
sys.path.insert(0, str(Path(__file__).parent.parent / "v3"))

import sqlite3
import feedparser
from datetime import datetime, timezone
from v3.config import get_config

print("=" * 60)
print("🔍 YouTube 配信枠検出診断")
print("=" * 60)

# 1. 設定確認
print("\n📋 [ステップ1] 設定確認")
print("-" * 60)
try:
    config = get_config("v3/settings.env")
    youtube_channel_id = config.youtube_channel_id
    poll_interval = config.poll_interval_minutes

    print(f"✅ YouTube チャンネルID: {youtube_channel_id}")
    print(f"✅ ポーリング間隔: {poll_interval} 分")
except Exception as e:
    print(f"❌ 設定読み込みエラー: {e}")
    sys.exit(1)

# 2. RSS フィードを直接取得
print("\n📡 [ステップ2] YouTube RSS フィード直接取得")
print("-" * 60)
try:
    rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={youtube_channel_id}"
    print(f"📍 RSS URL: {rss_url}")

    feed = feedparser.parse(rss_url)

    if feed.bozo:
        print(f"⚠️ RSS パースエラー: {feed.bozo_exception}")

    print(f"✅ エントリ数: {len(feed.entries)}")

    if feed.entries:
        print("\n📹 最新の動画/配信（上位5件）:")
        for i, entry in enumerate(feed.entries[:5], 1):
            title = entry.get('title', 'N/A')
            video_id = entry.get('id', '').split('=')[-1] if entry.get('id') else 'N/A'
            published = entry.get('published', 'N/A')

            # 配信か通常動画か判定
            video_type = "不明"
            if 'youtube.com/watch' in entry.get('link', ''):
                video_type = "通常動画"
            elif 'youtube.com/channel' in entry.get('id', ''):
                video_type = "配信/プレミア"

            print(f"  {i}. [{video_type}] {title}")
            print(f"     - ID: {video_id}")
            print(f"     - 公開: {published}")
    else:
        print("❌ RSS エントリが取得できません")

except Exception as e:
    print(f"❌ RSS 取得エラー: {e}")

# 3. データベース確認
print("\n🗄️  [ステップ3] データベース確認")
print("-" * 60)
try:
    db_path = Path(__file__).parent.parent / "v3" / "data" / "video_list.db"

    if not db_path.exists():
        print(f"❌ データベースが見つかりません: {db_path}")
    else:
        print(f"✅ データベース: {db_path}")

        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # 最新の動画を取得
        cursor.execute("""
            SELECT id, video_id, title, content_type, live_status, published_at, source
            FROM videos
            ORDER BY published_at DESC
            LIMIT 10
        """)

        rows = cursor.fetchall()
        print(f"\n📊 DB 内の最新動画（上位10件）:")

        if rows:
            for i, row in enumerate(rows, 1):
                status_str = f"{row['content_type']}/{row['live_status']}" if row['live_status'] else row['content_type']
                print(f"  {i}. {row['title'][:40]}")
                print(f"     - ID: {row['video_id']}")
                print(f"     - ステータス: {status_str}")
                print(f"     - 公開: {row['published_at']}")
                print(f"     - ソース: {row['source']}")
        else:
            print("❌ DB にビデオが登録されていません")

        conn.close()

except Exception as e:
    print(f"❌ DB 確認エラー: {e}")

# 4. YouTube Live プラグイン確認
print("\n🔌 [ステップ4] YouTube Live プラグイン状態確認")
print("-" * 60)
try:
    plugin_path = Path(__file__).parent.parent / "v3" / "plugins" / "youtube_live_plugin.py"

    if plugin_path.exists():
        print(f"✅ YouTube Live プラグイン存在: {plugin_path}")

        # ファイルから状態を確認
        with open(plugin_path, 'r', encoding='utf-8') as f:
            content = f.read()
            if "def is_available" in content:
                print("✅ is_available メソッド定義あり")
            if "YOUTUBE_API_KEY" in content:
                print("✅ YouTube API キー対応")
    else:
        print(f"❌ YouTube Live プラグイン未検出")

except Exception as e:
    print(f"❌ プラグイン確認エラー: {e}")

# 5. ログ確認
print("\n📝 [ステップ5] 最新ログ確認")
print("-" * 60)
try:
    log_dir = Path(__file__).parent.parent / "v3" / "logs"

    if log_dir.exists():
        log_files = sorted(log_dir.glob("app.log"), key=lambda x: x.stat().st_mtime, reverse=True)

        if log_files:
            latest_log = log_files[0]
            print(f"✅ ログファイル: {latest_log}")

            # 最後の50行を表示
            with open(latest_log, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                recent_lines = lines[-30:]  # 最後の30行

                print(f"\n📋 最後の30行:")
                for line in recent_lines:
                    print(line.rstrip())
        else:
            print(f"⚠️ ログファイルが見つかりません: {log_dir}")
    else:
        print(f"❌ logs ディレクトリ未検出: {log_dir}")

except Exception as e:
    print(f"❌ ログ確認エラー: {e}")

print("\n" + "=" * 60)
print("🔍 診断完了")
print("=" * 60)
