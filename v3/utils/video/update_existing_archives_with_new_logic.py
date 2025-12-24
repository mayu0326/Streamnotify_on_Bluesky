#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
既存のアーカイブデータを新しい時刻判定ロジックで再更新

- DB に登録済みのアーカイブ（content_type='archive'）を取得
- YouTube API から最新情報を取得
- 新しい判定ロジック（actualEndTime vs publishedAt）を適用
- DB を更新
"""

import sqlite3
import os
import logging
from datetime import datetime, timezone
from pathlib import Path

# ロギング設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DB_PATH = "data/video_list.db"

def convert_utc_to_jst(utc_datetime_str: str) -> str:
    """UTC ISO 8601 を JST スペース区切り形式に変換"""
    try:
        from datetime import timedelta
        # "Z" または "+00:00" を処理
        utc_time = datetime.fromisoformat(utc_datetime_str.replace('Z', '+00:00'))
        jst_time = utc_time.astimezone(timezone(timedelta(hours=9)))
        return jst_time.strftime('%Y-%m-%d %H:%M:%S')
    except Exception as e:
        logger.error(f"❌ UTC→JST 変換エラー: {utc_datetime_str} - {e}")
        return utc_datetime_str


def get_archive_api_details(video_id: str, api_key: str) -> dict:
    """YouTube API からアーカイブ詳細を取得"""
    try:
        import requests
        url = "https://www.googleapis.com/youtube/v3/videos"
        params = {
            "part": "snippet,liveStreamingDetails",
            "id": video_id,
            "key": api_key
        }
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()

        data = response.json()
        if "items" and len(data["items"]) > 0:
            return data["items"][0]
        else:
            logger.warning(f"⚠️ API: 動画が見つかりません ({video_id})")
            return None
    except Exception as e:
        logger.error(f"❌ API エラー: {video_id} - {e}")
        return None


def determine_archive_published_at(details: dict) -> str:
    """
    アーカイブの published_at を新しいロジックで判定

    - actualEndTime と publishedAt のうち、現在時刻に近い方を採用
    - どちらか一方のみの場合はそれを採用
    """
    if not details:
        return None

    live_details = details.get("liveStreamingDetails", {})
    snippet = details.get("snippet", {})

    actual_end_time = live_details.get("actualEndTime")
    published_at = snippet.get("publishedAt")

    if actual_end_time and published_at:
        # 現在時刻に最も近い方を採用
        try:
            now = datetime.now(timezone.utc)
            end_time_dt = datetime.fromisoformat(actual_end_time.replace('Z', '+00:00'))
            pub_time_dt = datetime.fromisoformat(published_at.replace('Z', '+00:00'))

            end_delta = abs((end_time_dt - now).total_seconds())
            pub_delta = abs((pub_time_dt - now).total_seconds())

            if pub_delta < end_delta:
                logger.debug(f"📡 アーカイブ判定: publishedAt を採用（pub_delta={pub_delta}秒 < end_delta={end_delta}秒）")
                return published_at
            else:
                logger.debug(f"📡 アーカイブ判定: actualEndTime を採用（end_delta={end_delta}秒 <= pub_delta={pub_delta}秒）")
                return actual_end_time
        except Exception as e:
            logger.debug(f"⚠️ 時刻差分計算エラー: {e}、publishedAt にフォールバック")
            return published_at or actual_end_time
    elif published_at:
        logger.debug(f"📡 アーカイブ判定: publishedAt を使用（actualEndTime なし）")
        return published_at
    elif actual_end_time:
        logger.debug(f"📡 アーカイブ判定: actualEndTime を使用（publishedAt なし）")
        return actual_end_time

    return None


def update_existing_archives():
    """既存のアーカイブデータを新ロジックで更新"""
    from plugins.youtube_api_plugin import YouTubeAPIPlugin

    try:
        api_plugin = YouTubeAPIPlugin()
        if not api_plugin.is_available():
            logger.error("❌ YouTube API キーが設定されていません")
            return

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # DB に登録済みのアーカイブを取得
        cursor.execute("""
            SELECT id, video_id, title, published_at, content_type, live_status
            FROM videos
            WHERE content_type = 'archive'
            ORDER BY published_at DESC
        """)

        archives = cursor.fetchall()
        conn.close()

        logger.info(f"📊 処理対象: {len(archives)} 件のアーカイブ")

        updated_count = 0
        skipped_count = 0

        for idx, (db_id, video_id, title, db_published_at, content_type, live_status) in enumerate(archives, 1):
            logger.info(f"\n[{idx}/{len(archives)}] 処理中: {title}")
            logger.info(f"   video_id: {video_id}")
            logger.info(f"   DB の published_at: {db_published_at}")

            # API から最新情報を取得
            details = get_archive_api_details(video_id, api_plugin.api_key)
            if not details:
                logger.warning(f"⏭️ スキップ: API データ取得失敗")
                skipped_count += 1
                continue

            # 新しいロジックで published_at を決定
            api_published_at = determine_archive_published_at(details)
            if not api_published_at:
                logger.warning(f"⏭️ スキップ: publishedAt 情報なし")
                skipped_count += 1
                continue

            # UTC → JST 変換
            api_published_at_jst = convert_utc_to_jst(api_published_at)

            logger.info(f"   API の published_at (UTC): {api_published_at}")
            logger.info(f"   API の published_at (JST): {api_published_at_jst}")

            # DB と比較
            if api_published_at_jst != db_published_at:
                logger.info(f"   ✅ 更新対象: {db_published_at} → {api_published_at_jst}")

                # DB を更新
                try:
                    conn = sqlite3.connect(DB_PATH)
                    cursor = conn.cursor()
                    cursor.execute(
                        "UPDATE videos SET published_at = ? WHERE id = ?",
                        (api_published_at_jst, db_id)
                    )
                    conn.commit()
                    conn.close()

                    logger.info(f"   ✅ DB 更新完了")
                    updated_count += 1
                except Exception as e:
                    logger.error(f"   ❌ DB 更新失敗: {e}")
                    skipped_count += 1
            else:
                logger.info(f"   ℹ️ スキップ（既に同じ値）")
                skipped_count += 1

        logger.info(f"\n" + "=" * 80)
        logger.info(f"📊 処理完了")
        logger.info(f"   ✅ 更新: {updated_count} 件")
        logger.info(f"   ⏭️ スキップ: {skipped_count} 件")
        logger.info(f"=" * 80)

    except Exception as e:
        logger.error(f"❌ 処理エラー: {e}")


if __name__ == "__main__":
    logger.info("=" * 80)
    logger.info("🔄 既存アーカイブデータの再更新を開始します")
    logger.info("=" * 80)
    update_existing_archives()
