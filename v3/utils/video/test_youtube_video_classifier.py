# -*- coding: utf-8 -*-

"""
YouTube 動画分類モジュール - テスト・デモスクリプト

このスクリプトで YouTubeVideoClassifier の動作を確認できます。
"""

import sys
import logging
from pathlib import Path

# パス設定
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from youtube_core.youtube_video_classifier import YouTubeVideoClassifier

# テスト用の既知の動画 ID
TEST_VIDEO_IDS = {
    "dQw4w9WgXcQ": "Rick Astley - Never Gonna Give You Up (通常動画)",
    "jNQXAC9IVRw": "Me at the zoo (YouTube 初の動画、通常動画)",
    # プレミア公開やライブ関連の video_id は実際の環境で確認してください
}


def main():
    """テスト実行"""
    print("=" * 70)
    print("YouTube 動画分類モジュール - テスト")
    print("=" * 70)

    classifier = YouTubeVideoClassifier()

    # API キー確認
    if not classifier.api_key:
        print("⚠️  警告: YOUTUBE_API_KEY が設定されていません")
        print("   settings.env に YOUTUBE_API_KEY=... を追加してください")
        return

    print(f"✅ API キー: {classifier.api_key[:20]}...")
    print()

    # テスト実行
    for video_id, description in TEST_VIDEO_IDS.items():
        print("-" * 70)
        print(f"テスト: {description}")
        print(f"Video ID: {video_id}")
        print()

        result = classifier.classify_video(video_id)

        if result["success"]:
            print(f"✅ 分類成功")
            print(f"   タイプ: {result['type']}")
            print(f"   タイトル: {result['title']}")
            print(f"   プレミア公開: {result['is_premiere']}")
            print(f"   ライブ関連: {result['is_live']}")
            print(f"   公開日時: {result['published_at']}")

            # 投稿判定
            if result['type'] in ['video', 'premiere']:
                print(f"   📤 投稿対象: YES")
            else:
                print(f"   📤 投稿対象: NO（{result['type']}）")

            # 短縮判定メソッドの確認
            is_normal_or_premiere = classifier.is_normal_or_premiere(video_id)
            is_live_related = classifier.is_live_related(video_id)
            print()
            print(f"   is_normal_or_premiere(): {is_normal_or_premiere}")
            print(f"   is_live_related(): {is_live_related}")
        else:
            print(f"❌ 分類失敗")
            print(f"   エラー: {result['error']}")

        print()

    print("=" * 70)
    print("テスト完了")
    print("=" * 70)


if __name__ == "__main__":
    main()
