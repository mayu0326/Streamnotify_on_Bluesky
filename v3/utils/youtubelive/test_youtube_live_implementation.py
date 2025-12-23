#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YouTube Live 実装確認テスト

以下を検証：
1. _classify_video_core() の実装
2. youtube_live_plugin が _classify_video_core() を呼び出し
3. テンプレートファイルの形式確認
4. System コメント 1-6 の統合確認
"""
import sys
import os
from pathlib import Path

# v2 パスを追加
sys.path.insert(0, str(Path(__file__).parent.parent / "v2"))

def test_classify_video_core_exists():
    """_classify_video_core() が存在するか確認"""
    from plugins.youtube_api_plugin import YouTubeAPIPlugin

    # スタティックメソッドとして存在するか
    assert hasattr(YouTubeAPIPlugin, '_classify_video_core'), \
        "YouTubeAPIPlugin に _classify_video_core() が存在しません"

    # 呼び出し可能か
    assert callable(YouTubeAPIPlugin._classify_video_core), \
        "_classify_video_core() は呼び出し可能ではありません"

    print("✅ _classify_video_core() が存在します")


def test_youtube_live_delegates_to_core():
    """youtube_live_plugin が _classify_video_core() を委譲しているか確認"""
    from plugins.youtube_live_plugin import YouTubeLivePlugin
    import inspect

    # _classify_live() メソッドのソースコードを確認
    source = inspect.getsource(YouTubeLivePlugin._classify_live)

    assert '_classify_video_core' in source, \
        "youtube_live_plugin._classify_live() が _classify_video_core() を呼び出していません"

    print("✅ youtube_live_plugin._classify_live() が _classify_video_core() に委譲されています")


def test_classify_video_core_implementation():
    """_classify_video_core() の実装を検証"""
    from plugins.youtube_api_plugin import YouTubeAPIPlugin
    import inspect

    source = inspect.getsource(YouTubeAPIPlugin._classify_video_core)

    # System コメント 1-6 の確認
    assert "System 1" in source, "System 1 コメントがありません"
    assert "System 2" in source, "System 2 コメントがありません"
    assert "System 3" in source, "System 3 コメントがありません"
    assert "System 4" in source, "System 4 コメントがありません"
    assert "System 5" in source, "System 5 コメントがありません"
    assert "System 6" in source, "System 6 コメントがありません"

    print("✅ _classify_video_core() に System コメント 1-6 が統合されています")


def test_template_files_exist_and_valid():
    """テンプレートファイルの存在・形式を確認"""
    from pathlib import Path

    base = Path(__file__).parent.parent / "v2" / "templates" / "youtube"

    templates = {
        "yt_online_template.txt": ["▶️", "YouTube Live", "{{ channel_name }}", "{{ title }}", "{{ video_url }}"],
        "yt_offline_template.txt": ["🛑", "YouTube Live", "{{ channel_name }}", "{{ title }}", "{{ video_url }}"],
    }

    for filename, expected_contents in templates.items():
        filepath = base / filename
        assert filepath.exists(), f"{filename} が存在しません"

        content = filepath.read_text(encoding='utf-8')
        for expected in expected_contents:
            assert expected in content, f"{filename} に '{expected}' が含まれていません"

    print("✅ YouTube Live テンプレートファイルが正しく作成されています")


def test_classification_logic():
    """分類ロジックの実装を確認"""
    from plugins.youtube_api_plugin import YouTubeAPIPlugin

    # テストケース: 通常動画
    details_video = {
        "snippet": {"liveBroadcastContent": "none"},
        "status": {},
        "liveStreamingDetails": {}
    }
    content_type, live_status, is_premiere = YouTubeAPIPlugin._classify_video_core(details_video)
    assert content_type == "video" and live_status is None and is_premiere is False, \
        "通常動画の分類に失敗"

    # テストケース: ライブ配信中
    details_live = {
        "snippet": {"liveBroadcastContent": "live"},
        "status": {},
        "liveStreamingDetails": {"actualStartTime": "2025-12-18T10:00:00Z"}
    }
    content_type, live_status, is_premiere = YouTubeAPIPlugin._classify_video_core(details_live)
    assert content_type == "live" and live_status == "live" and is_premiere is False, \
        "ライブ配信中の分類に失敗"

    # テストケース: アーカイブ（配信終了）
    details_archive = {
        "snippet": {"liveBroadcastContent": "live"},
        "status": {},
        "liveStreamingDetails": {"actualEndTime": "2025-12-18T11:00:00Z"}
    }
    content_type, live_status, is_premiere = YouTubeAPIPlugin._classify_video_core(details_archive)
    assert content_type == "archive" and live_status == "completed" and is_premiere is False, \
        "アーカイブ（配信終了）の分類に失敗"

    # テストケース: プレミア公開（予定）
    details_premiere = {
        "snippet": {"liveBroadcastContent": "upcoming"},
        "status": {"uploadStatus": "processed"},
        "liveStreamingDetails": {"scheduledStartTime": "2025-12-18T14:00:00Z"}
    }
    content_type, live_status, is_premiere = YouTubeAPIPlugin._classify_video_core(details_premiere)
    assert content_type == "live" and live_status == "upcoming" and is_premiere is True, \
        "プレミア公開（予定）の分類に失敗"

    print("✅ 分類ロジックが正しく動作しています（4テストケース合格）")


def main():
    """メインテスト実行"""
    print("\n🧪 YouTube Live 実装確認テストを開始します\n")

    tests = [
        ("_classify_video_core() 存在確認", test_classify_video_core_exists),
        ("youtube_live_plugin 委譲確認", test_youtube_live_delegates_to_core),
        ("_classify_video_core() 実装確認", test_classify_video_core_implementation),
        ("テンプレートファイル確認", test_template_files_exist_and_valid),
        ("分類ロジック動作確認", test_classification_logic),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        try:
            print(f"📋 {test_name}...", end=" ")
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"❌ FAILED\n   {e}")
            failed += 1
        except Exception as e:
            print(f"❌ ERROR\n   {e}")
            failed += 1

    print(f"\n{'='*60}")
    print(f"テスト結果: {passed} 合格, {failed} 失敗")
    print(f"{'='*60}\n")

    if failed == 0:
        print("🎉 すべてのテストに合格しました！")
        return 0
    else:
        print(f"⚠️ {failed} つのテストが失敗しました")
        return 1


if __name__ == "__main__":
    sys.exit(main())
