#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ハッシュタグ Facet 検出テスト
"""
import sys
from pathlib import Path

# v2 ディレクトリを sys.path に追加
v2_dir = Path(__file__).parent
sys.path.insert(0, str(v2_dir))

# bluesky_core をインポート
from bluesky_core import BlueskyMinimalPoster
import logging

# ロギング設定
logging.basicConfig(
    level=logging.DEBUG,
    format="[%(levelname)s] %(name)s: %(message)s"
)

print("=" * 70)
print("【ハッシュタグ Facet 検出テスト】")
print("=" * 70)
print()

# テスト用テキスト
test_cases = [
    # ケース1: 基本的なハッシュタグ
    "新作動画をアップロードしました\n\n#YouTube #新作",

    # ケース2: URL とハッシュタグの両方
    "動画: https://www.youtube.com/watch?v=test123\n\n#YouTube #配信",

    # ケース3: 日本語ハッシュタグ
    "配信中です #配信中 #ライブ\n\nhttps://twitch.tv/test",

    # ケース4: テンプレート出力例
    "🎬 テストチャンネル の新作動画\n\nYouTube に新しい動画をアップロードしました！\n\n📹 タイトル: 新作動画\n\n📺 視聴: https://www.youtube.com/watch?v=abc123\n\n投稿日時: 2025年12月18日\n\n#YouTube",
]

# BlueskyMinimalPoster のインスタンスを作成（dry_run = True）
poster = BlueskyMinimalPoster(
    username="test@example.com",
    password="test_password",
    dry_run=True
)

for i, text in enumerate(test_cases, 1):
    print(f"【テストケース {i}】")
    print(f"テキスト:\n{text}")
    print()

    # Facet を構築
    facets = poster._build_facets_for_url(text)

    print(f"検出結果:")
    if facets:
        print(f"  ✅ Facet 数: {len(facets)}")
        for j, facet in enumerate(facets, 1):
            feature = facet["features"][0]
            byte_start = facet["index"]["byteStart"]
            byte_end = facet["index"]["byteEnd"]

            # テキストの該当部分を表示
            detected_text = text.encode('utf-8')[byte_start:byte_end].decode('utf-8')

            if feature["$type"] == "app.bsky.richtext.facet#link":
                print(f"  【{j}】URL Facet")
                print(f"       テキスト: {detected_text}")
                print(f"       URI: {feature['uri']}")
                print(f"       バイト位置: {byte_start}-{byte_end}")
            elif feature["$type"] == "app.bsky.richtext.facet#tag":
                print(f"  【{j}】Hashtag Facet")
                print(f"       テキスト: {detected_text}")
                print(f"       タグ: {feature['tag']}")
                print(f"       バイト位置: {byte_start}-{byte_end}")
    else:
        print(f"  ℹ️ Facet が検出されませんでした")
    print()
    print("-" * 70)
    print()
