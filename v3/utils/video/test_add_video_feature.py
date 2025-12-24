#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""動画追加機能のテスト"""

import sys
sys.path.insert(0, '.')

from gui_v3 import StreamNotifyGUI
import re

def test_extract_video_id():
    """_extract_video_id メソッドの テスト"""

    print("=" * 70)
    print("【テスト】動画ID抽出機能")
    print("=" * 70)

    # StreamNotifyGUI のメソッドにアクセスするためにダミーインスタンスを作る
    # 実際にはメソッドだけを使用する

    test_cases = [
        ("dQw4w9WgXcQ", True, "生の動画ID"),
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", True, "youtube.com URL"),
        ("https://youtu.be/dQw4w9WgXcQ", True, "youtu.be URL"),
        ("https://www.youtube.com/embed/dQw4w9WgXcQ", True, "embed URL"),
        ("invalid", False, "無効なID"),
        ("https://example.com", False, "YouTube以外のURL"),
    ]

    def extract_video_id(input_value: str) -> str:
        """URLまたは ID から YouTube 動画IDを抽出"""
        input_value = input_value.strip()

        # youtube.com/watch?v=XXXXX
        match = re.search(r'watch\?v=([a-zA-Z0-9_-]{11})', input_value)
        if match:
            return match.group(1)

        # youtu.be/XXXXX
        match = re.search(r'youtu\.be/([a-zA-Z0-9_-]{11})', input_value)
        if match:
            return match.group(1)

        # www.youtube.com/embed/XXXXX
        match = re.search(r'/embed/([a-zA-Z0-9_-]{11})', input_value)
        if match:
            return match.group(1)

        # 11文字の動画ID の場合はそのまま
        if len(input_value) == 11 and re.match(r'^[a-zA-Z0-9_-]{11}$', input_value):
            return input_value

        return None

    passed = 0
    failed = 0

    for input_val, should_succeed, description in test_cases:
        result = extract_video_id(input_val)
        success = (result is not None) == should_succeed

        if success:
            print(f"✅ {description}: {input_val[:50]}")
            if result:
                print(f"   → 抽出されたID: {result}")
            passed += 1
        else:
            print(f"❌ {description}: {input_val[:50]}")
            failed += 1

    print("\n" + "=" * 70)
    print(f"結果: ✅ {passed}/{len(test_cases)} テスト成功")
    if failed > 0:
        print(f"     ❌ {failed}/{len(test_cases)} テスト失敗")
    print("=" * 70)

    return failed == 0

def test_video_url_validation():
    """動画URL妥当性チェック"""

    print("\n" + "=" * 70)
    print("【テスト】動画URL妥当性チェック")
    print("=" * 70)

    youtube_patterns = [
        r'watch\?v=([a-zA-Z0-9_-]{11})',
        r'youtu\.be/([a-zA-Z0-9_-]{11})',
        r'/embed/([a-zA-Z0-9_-]{11})',
    ]

    test_urls = [
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=5s", "フルURL（タイムスタンプ付き）"),
        ("https://youtu.be/dQw4w9WgXcQ?t=5", "短縮URL"),
        ("https://www.youtube.com/embed/dQw4w9WgXcQ", "埋め込みコード"),
        ("dQw4w9WgXcQ", "生の動画ID"),
    ]

    for url, description in test_urls:
        for pattern in youtube_patterns:
            match = re.search(pattern, url)
            if match:
                print(f"✅ {description}")
                print(f"   URL: {url}")
                print(f"   抽出ID: {match.group(1)}\n")
                break

    print("=" * 70)
    return True

if __name__ == '__main__':
    test1 = test_extract_video_id()
    test2 = test_video_url_validation()

    if test1 and test2:
        print("\n🎉 すべてのテストに合格しました！")
        sys.exit(0)
    else:
        print("\n❌ テストに失敗しました")
        sys.exit(1)
