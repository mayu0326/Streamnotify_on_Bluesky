# -*- coding: utf-8 -*-
"""ポーリング実行中にキャッシュファイルを監視"""

import sys
import json
import time
import subprocess
import threading
from pathlib import Path

# Windows CP932対応
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

cache_path = Path(__file__).parent / "data" / "youtube_live_cache.json"

def monitor_cache():
    """キャッシュファイルを監視"""
    print("CACHE MONITOR: Started (15 sec)")
    start_time = time.time()

    while time.time() - start_time < 15:  # 15秒監視
        if cache_path.exists():
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    content = json.load(f)

                size = cache_path.stat().st_size
                keys = list(content.keys())

                elapsed = time.time() - start_time
                print(f"  [{elapsed:.1f}s] FileSize: {size} bytes, Keys: {len(keys)}")

                if keys:
                    for key in keys:
                        print(f"       - {key}")
                        if "status" in content[key]:
                            print(f"         status: {content[key].get('status')}")
            except Exception as e:
                print(f"  Error: {e}")

        time.sleep(0.5)

    print("CACHE MONITOR: Done")

# アプリ起動
print("APP: Starting...")
process = subprocess.Popen(["python", "main_py"])

# 監視スレッド開始
monitor_thread = threading.Thread(target=monitor_cache, daemon=True)
monitor_thread.start()

# 15秒後にアプリを終了
time.sleep(15)
try:
    process.terminate()
except:
    pass

print("DONE")
