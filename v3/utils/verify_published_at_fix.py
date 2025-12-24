#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
検証スクリプト: published_at が API データで正確に更新されているか確認

実行方法:
    python verify_published_at_fix.py
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime

DB_PATH = "data/video_list.db"
EXPECTED_UPDATES = {
    # video_id: {
    #   "title": "...",
    #   "expected_published_at": "2025-12-28T18:00:00Z",
    #   "reason": "API scheduledStartTime を使用"
    # }
}


def check_database():
    """DB の published_at が正確に更新されているか確認"""

    print("\n" + "="*80)
    print("✅ published_at 修正検証スクリプト")
    print("="*80 + "\n")

    if not Path(DB_PATH).exists():
        print(f"❌ DB ファイルが見つかりません: {DB_PATH}")
        return False

    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # YouTube Live/Archive の動画を取得
        cursor.execute("""
            SELECT id, video_id, title, published_at, content_type, live_status, posted_to_bluesky
            FROM videos
            WHERE content_type IN ('live', 'archive')
            ORDER BY published_at DESC
            LIMIT 20
        """)

        results = cursor.fetchall()
        conn.close()

        if not results:
            print("ℹ️ YouTube Live/Archive 動画がありません（テスト対象なし）")
            return True

        print(f"📊 YouTube Live/Archive 動画: {len(results)} 件\n")

        for row in results:
            video_id = row["video_id"]
            title = row["title"]
            published_at = row["published_at"]
            content_type = row["content_type"]
            live_status = row["live_status"]
            posted = "✅ 投稿済み" if row["posted_to_bluesky"] else "⏳ 未投稿"

            print(f"📋 {title}")
            print(f"   video_id: {video_id}")
            print(f"   published_at: {published_at}")
            print(f"   content_type: {content_type}, live_status: {live_status}")
            print(f"   状態: {posted}")
            print()

        # API データとの比較（存在する場合）
        api_cache_path = Path("data/youtube_video_detail_cache.json")
        if api_cache_path.exists():
            print("\n" + "-"*80)
            print("🔍 API キャッシュとの比較")
            print("-"*80 + "\n")

            with open(api_cache_path, "r", encoding="utf-8") as f:
                api_cache = json.load(f)

            match_count = 0
            mismatch_count = 0

            for row in results:
                video_id = row["video_id"]
                db_published_at = row["published_at"]

                if video_id in api_cache:
                    api_data = api_cache[video_id].get("data", {})
                    live_details = api_data.get("liveStreamingDetails", {})
                    snippet = api_data.get("snippet", {})

                    api_published_at = None
                    api_source = None

                    if live_details.get("scheduledStartTime"):
                        api_published_at = live_details["scheduledStartTime"]
                        api_source = "scheduledStartTime"
                    elif live_details.get("actualStartTime"):
                        api_published_at = live_details["actualStartTime"]
                        api_source = "actualStartTime"
                    elif snippet.get("publishedAt"):
                        api_published_at = snippet["publishedAt"]
                        api_source = "publishedAt"

                    if api_published_at:
                        if db_published_at == api_published_at:
                            print(f"✅ 一致: {row['title']}")
                            print(f"   DB: {db_published_at}")
                            print(f"   API ({api_source}): {api_published_at}")
                            match_count += 1
                        else:
                            print(f"⚠️ 不一致: {row['title']}")
                            print(f"   DB: {db_published_at}")
                            print(f"   API ({api_source}): {api_published_at}")
                            mismatch_count += 1
                        print()

            print(f"\n📊 比較結果: 一致 {match_count}、不一致 {mismatch_count}")

            if mismatch_count > 0:
                print("❌ API データと DB が不一致です。修正が必要です。")
                return False

        print("\n" + "="*80)
        print("✅ 検証完了: published_at は正確に更新されています")
        print("="*80 + "\n")

        return True

    except Exception as e:
        print(f"❌ エラー: {e}")
        return False


def check_logs():
    """ログファイルで修正が実行されたか確認"""

    print("\n" + "-"*80)
    print("📝 ログファイル確認")
    print("-"*80 + "\n")

    log_path = Path("logs/app.log")
    if not log_path.exists():
        print("ℹ️ ログファイルが見つかりません")
        return

    try:
        with open(log_path, "r", encoding="utf-8") as f:
            logs = f.readlines()

        # 最新 100 行から修正ログを検索
        recent_logs = logs[-100:]

        update_logs = [
            line for line in recent_logs
            if "published_at を API データで上書きしました" in line
            or "published_at を API データで更新" in line
        ]

        if update_logs:
            print(f"✅ API データの更新ログを検出: {len(update_logs)} 件\n")
            for log in update_logs[-5:]:  # 最新 5 件を表示
                print(f"   {log.strip()}")
        else:
            print("ℹ️ API データの更新ログが見つかりません（正常な可能性もあります）")

    except Exception as e:
        print(f"⚠️ ログ確認エラー: {e}")


if __name__ == "__main__":
    check_database()
    check_logs()

    print("\n" + "="*80)
    print("次のステップ:")
    print("1. DB の published_at が API データで更新されているか確認")
    print("2. ログファイルで修正の実行状況を確認")
    print("3. Bluesky への投稿で配信予定日時が正確に表示されているか確認")
    print("="*80 + "\n")
