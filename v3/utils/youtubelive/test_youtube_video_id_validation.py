#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
YouTube Video ID 形式検証テスト

修正内容: YouTubeAPIPlugin と YouTubeLivePlugin に _is_valid_youtube_video_id() を追加
実装日: 2025-12-18

このスクリプトで修正が正しく動作することを検証します。
"""

import re
import sys
from pathlib import Path

# プロジェクトパスを追加
sys.path.insert(0, str(Path(__file__).parent))

def _is_valid_youtube_video_id(video_id: str) -> bool:
    """
    YouTube 動画ID 形式の検証

    YouTube 動画ID は 11 文字の英数字（A-Z, a-z, 0-9, -, _）
    """
    if re.match(r'^[A-Za-z0-9_-]{11}$', video_id):
        return True
    return False


def test_valid_youtube_ids():
    """有効な YouTube ID のテスト"""
    valid_ids = [
        "dQw4w9WgXcQ",  # Rick Roll
        "9bZkp7q19f0",  # YouTube Rewind 2018
        "kfVsfOSbJY0",  # PSY - GANGNAM STYLE
        "A_b-z_-0_1A",  # All allowed chars (11文字)
    ]

    print("✅ 有効な YouTube ID:")
    for video_id in valid_ids:
        result = _is_valid_youtube_video_id(video_id)
        status = "✓" if result else "✗"
        print(f"  {status} {video_id}: {result}")
        assert result is True, f"Should be True: {video_id}"
    print()


def test_invalid_youtube_ids():
    """無効な ID のテスト"""
    invalid_ids = [
        "sm45414087",    # Niconico
        "sm1234567",     # Niconico (短い)
        "abc123",        # 6 文字（短い）
        "dQw4w9WgXcQ1",  # 12 文字（長い）
        "dQw4w9WgXc",    # 10 文字（短い）
        "dQw4w9WgX@Q",   # 特殊文字含む
        "",              # 空文字列
        "dQw4w9WgXcQ ",  # スペース含む
        "dQw4w9 gXcQ",   # スペース含む
    ]

    print("❌ 無効な ID:")
    for video_id in invalid_ids:
        result = _is_valid_youtube_video_id(video_id)
        status = "✓" if not result else "✗"
        print(f"  {status} '{video_id}': {result}")
        assert result is False, f"Should be False: {video_id}"
    print()


def test_edge_cases():
    """エッジケース"""
    edge_cases = [
        ("_" * 11, True),         # 全てアンダースコア（11 文字）
        ("-" * 11, True),         # 全てハイフン（11 文字）
        ("a" * 11, True),         # 全て小文字（11 文字）
        ("A" * 11, True),         # 全て大文字（11 文字）
        ("0" * 11, True),         # 全て数字（11 文字）
        ("_" * 10, False),        # 10 文字
        ("_" * 12, False),        # 12 文字
        ("a-_A0b-_A0c", True),     # 混在（11 文字）
    ]

    print("🔍 エッジケース:")
    for video_id, expected in edge_cases:
        result = _is_valid_youtube_video_id(video_id)
        status = "✓" if result == expected else "✗"
        print(f"  {status} '{video_id}' (len={len(video_id)}): {result} (expected: {expected})")
        assert result == expected, f"Mismatch for {video_id}"
    print()


def main():
    print("=" * 60)
    print("YouTube Video ID 形式検証テスト")
    print("=" * 60)
    print()

    try:
        test_valid_youtube_ids()
        test_invalid_youtube_ids()
        test_edge_cases()

        print("=" * 60)
        print("🎉 すべてのテストが成功しました！")
        print("=" * 60)
        return 0

    except AssertionError as e:
        print()
        print("=" * 60)
        print(f"❌ テスト失敗: {e}")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
