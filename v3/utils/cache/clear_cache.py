#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""YouTubeプラグインのキャッシュをクリア"""

import sys
import os
import json

old_version_path = r'C:\Users\Mayu\Desktop\新しいフォルダー\サムネ取得・LIVE判定が正常に動く旧バージョン'
os.chdir(old_version_path)

def main():
    cache_dir = 'data/cache'
    
    if not os.path.exists(cache_dir):
        print(f"📁 キャッシュディレクトリが存在しません: {cache_dir}")
        print(f"   （初回実行時は問題ありません）")
        return
    
    # キャッシュファイルを探す
    cache_files = []
    for root, dirs, files in os.walk(cache_dir):
        for file in files:
            if file.endswith('.json') or file.endswith('.cache'):
                cache_files.append(os.path.join(root, file))
    
    if not cache_files:
        print(f"📁 キャッシュファイルが見つかりません")
        return
    
    print("=" * 80)
    print("🗑️ YouTubeプラグインのキャッシュをクリア")
    print("=" * 80)
    print(f"\n🔍 見つかったキャッシュファイル: {len(cache_files)} 件")
    
    for cache_file in cache_files:
        try:
            os.remove(cache_file)
            print(f"  ✅ 削除: {cache_file}")
        except Exception as e:
            print(f"  ❌ 削除失敗: {cache_file} - {e}")
    
    print(f"\n✅ キャッシュクリア完了")
    print(f"\n💡 次のステップ:")
    print(f"   1. アプリケーションを再起動")
    print(f"   2. YouTubeプラグインが再度APIからデータを取得します")

if __name__ == '__main__':
    main()
