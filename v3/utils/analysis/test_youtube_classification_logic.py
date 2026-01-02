#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YouTube Live 分類ロジック実行テスト

既存 DB を複製し、実際の動画データに対して分類ロジックを適用
- Live/Archive/Video の判定をテスト
- 分類結果を表示
- 元 DB は保護される
"""
import sys
import os
import shutil
import sqlite3
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# v2 パスを追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# settings.env から環境変数を読み込み
env_path = Path(__file__).parent.parent.parent / "settings.env"
load_dotenv(env_path)

from plugins.youtube.youtube_api_plugin import YouTubeAPIPlugin


def duplicate_database():
    """DB を複製（テスト用）"""
    db_path = Path(__file__).parent.parent.parent / "data" / "video_list.db"
    test_db_path = Path(__file__).parent.parent.parent / "data" / "video_list_test.db"

    if not db_path.exists():
        print(f"❌ DB が見つかりません: {db_path}")
        return None

    # 既存のテスト DB があれば削除
    if test_db_path.exists():
        test_db_path.unlink()

    # 複製
    shutil.copy2(db_path, test_db_path)
    print(f"✅ DB を複製しました: {test_db_path}")

    return test_db_path


def get_videos_from_db(db_path):
    """DB から動画情報を取得"""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT video_id, title, channel_name, content_type, live_status, is_premiere, source
            FROM videos
            ORDER BY published_at DESC
            LIMIT 20
        """)

        videos = [dict(row) for row in cursor.fetchall()]
        return videos
    finally:
        conn.close()


def fetch_video_details(video_id):
    """YouTube API から動画詳細を取得（テスト用）"""
    # テスト用に API クライアントを作成
    # 実際の API キーがない場合はスキップ
    api_key = os.getenv("YOUTUBE_API_KEY", "").strip()

    if not api_key:
        print("   ⚠️  YOUTUBE_API_KEY が未設定のため API 取得をスキップします")
        return None

    try:
        plugin = YouTubeAPIPlugin()
        if not plugin.is_available():
            print("   ⚠️  YouTube API プラグインが利用不可です")
            return None

        details = plugin._fetch_video_detail(video_id)
        return details
    except Exception as e:
        print(f"   ❌ API エラー: {e}")
        return None


def classify_video(details):
    """分類ロジックを適用"""
    if not details:
        return None

    return YouTubeAPIPlugin._classify_video_core(details)


def format_classification(content_type, live_status, is_premiere):
    """分類結果をフォーマット"""
    status_str = f"{content_type}"
    if live_status:
        status_str += f" ({live_status})"
    if is_premiere:
        status_str += " [プレミア]"
    return status_str


def main():
    """メイン処理"""
    print("\n" + "="*70)
    print("🎬 YouTube Live 分類ロジック実行テスト")
    print("="*70 + "\n")

    # Step 1: DB 複製
    print("📦 Step 1: DB を複製します...\n")
    test_db_path = duplicate_database()
    if not test_db_path:
        return 1

    # Step 2: DB から動画取得
    print("\n📋 Step 2: DB から動画情報を取得します...\n")
    videos = get_videos_from_db(test_db_path)

    if not videos:
        print("❌ DB に動画が見つかりません")
        return 1

    print(f"✅ {len(videos)} 件の動画を取得しました\n")

    # Step 3: 分類ロジック適用
    print("🔍 Step 3: 分類ロジックを適用します...\n")
    print(f"{'#':<3} {'Video ID':<15} {'Title':<40} {'現在の分類':<25} {'新分類'}")
    print("-" * 110)

    classified_count = 0
    api_available = bool(os.getenv("YOUTUBE_API_KEY", "").strip())

    for i, video in enumerate(videos, 1):
        video_id = video.get("video_id")
        title = video.get("title", "")[:35]
        current_type = video.get("content_type", "?")
        current_status = video.get("live_status")
        current_premiere = video.get("is_premiere")
        source = video.get("source", "").strip().lower()

        current_str = format_classification(current_type, current_status, current_premiere)

        # YouTube の場合のみ API から詳細を取得
        if api_available and source == "youtube":
            details = fetch_video_details(video_id)
            if details:
                classification = classify_video(details)
                if classification:
                    content_type, live_status, is_premiere = classification
                    new_str = format_classification(content_type, live_status, is_premiere)
                    classified_count += 1

                    # 分類が変わったかチェック
                    changed = (content_type != current_type) or (live_status != current_status) or (is_premiere != current_premiere)
                    marker = " ⚠️ " if changed else "  ✓ "

                    print(f"{i:<3} {video_id:<15} {title:<40} {current_str:<25} {new_str}{marker}")
                else:
                    print(f"{i:<3} {video_id:<15} {title:<40} {current_str:<25} [分類エラー]")
            else:
                print(f"{i:<3} {video_id:<15} {title:<40} {current_str:<25} [API取得失敗]")
        elif api_available and source != "youtube":
            # YouTube 以外のプラットフォーム
            print(f"{i:<3} {video_id:<15} {title:<40} {current_str:<25} [{source.upper()}は対象外]")
        else:
            # API キーなしの場合は DB の値のみ表示
            print(f"{i:<3} {video_id:<15} {title:<40} {current_str:<25} [API未設定]")

    print("-" * 110)

    # Step 4: 統計表示
    print(f"\n📊 Step 4: 統計情報\n")
    print(f"✅ 取得動画数: {len(videos)} 件")
    if api_available:
        print(f"✅ 分類完了数: {classified_count} 件")
    print(f"📁 テスト DB: {test_db_path}")
    print(f"   ⚠️  このファイルは安全にテストします（元 DB は保護されます）\n")

    # Step 5: テンプレート検証
    print("📝 Step 5: テンプレートファイルの確認\n")
    template_dir = Path(__file__).parent.parent.parent / "templates" / "youtube"

    templates = {
        "yt_online_template.txt": "配信開始",
        "yt_offline_template.txt": "配信終了",
    }

    for filename, desc in templates.items():
        template_path = template_dir / filename
        if template_path.exists():
            content = template_path.read_text(encoding='utf-8')
            required_vars = ["{{ channel_name }}", "{{ title }}", "{{ video_url }}"]
            all_present = all(var in content for var in required_vars)

            status = "✅" if all_present else "❌"
            print(f"{status} {filename} ({desc})")
            if not all_present:
                print(f"   ⚠️  必須変数が不足しています")
        else:
            print(f"❌ {filename} が見つかりません")

    print("\n" + "="*70)
    if api_available and classified_count > 0:
        print(f"✅ テスト完了：{classified_count} 件の動画を分類しました")
    elif api_available:
        print("⚠️ API キーは設定されていますが、DB に動画が見つかりません")
    else:
        print("⚠️ YOUTUBE_API_KEY が設定されていないため、DB の値のみ表示しました")
    print("="*70 + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
