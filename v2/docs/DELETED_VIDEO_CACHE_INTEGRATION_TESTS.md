# 削除済み動画ブラックリスト - 統合テスト手順

**テスト対象**: 削除済み動画ブラックリスト機能（v2.1.1+）

---

## テスト環境セットアップ

### 前提条件
- Python 3.9+
- v2/ ディレクトリで実行
- settings.env が正しく設定されている（YouTube チャンネル ID など）

### テストデータ準備

```bash
# 1. v2/ ディレクトリに移動
cd v2/

# 2. DB とログをリセット（初期化）
rm -f data/video_list.db
rm -f data/deleted_videos.json
rm -rf logs/*

# 3. アプリケーション起動
python main_v2.py
```

---

## テスト 1: ブラックリスト JSON 初期化

**目的**: アプリケーション起動時にブラックリスト JSON が正しく作成されるか

### 実行手順

```bash
# 1. アプリケーションを起動
python main_v2.py

# 2. ログで確認
grep "ブラックリスト" logs/app.log

# 期待される出力:
# [INFO] ✅ ブラックリストを読み込みました: data/deleted_videos.json
# または
# [DEBUG] ブラックリスト JSON が存在しません。新規作成します: data/deleted_videos.json

# 3. JSON ファイルを確認
cat data/deleted_videos.json

# 期待される内容:
# {
#   "youtube": [],
#   "niconico": [],
#   "twitch": []
# }
```

### 結果判定
- ✅ **成功**: JSON ファイルが存在し、デフォルト構造になっている
- ❌ **失敗**: JSON ファイルが存在しない、または形式が異なる

---

## テスト 2: RSS 動画の DB 保存とブラックリスト検証

**目的**: RSS から取得した動画が正しく DB に保存されるか

### 実行手順

```bash
# 1. アプリケーション起動（GUI）
python main_v2.py

# 2. 「🔄 取得」ボタンをクリック（または自動実行）
# → RSS から動画が DB に保存される

# 3. ログで確認
grep "保存完了" logs/app.log

# 期待される出力例:
# [INFO] ✅ 保存完了: 新規 5, 既存 12

# 4. DB に動画が保存されたか確認
python -c "from database import get_database; db = get_database(); \
videos = db.get_all_videos(); print(f'Total: {len(videos)} 件')"
```

### 結果判定
- ✅ **成功**: 新規動画が DB に追加される
- ❌ **失敗**: 新規動画が追加されない、またはエラーが発生

---

## テスト 3: 動画削除とブラックリスト登録

**目的**: GUI から動画を削除したとき、ブラックリストに正しく登録されるか

### 実行手順

```bash
# 1. GUI から 1-2 件の動画を選択（☑️ をクリック）

# 2. 「🗑️ 削除」ボタンをクリック

# 3. 確認ダイアログで「はい」をクリック

# 4. ログで確認
grep "削除\|ブラックリスト" logs/app.log

# 期待される出力例:
# [INFO] ✅ 動画を削除しました: yt123abc
# [INFO] ✅ ブラックリストに追加しました: yt123abc (source: youtube)
# [DEBUG] ✅ ブラックリストを保存しました: data/deleted_videos.json

# 5. JSON ファイルで削除済み ID が記録されているか確認
cat data/deleted_videos.json

# 期待される内容例:
# {
#   "youtube": ["yt123abc", "yt456def"],
#   "niconico": [],
#   "twitch": []
# }
```

### 結果判定
- ✅ **成功**:
  - ログに削除とブラックリスト登録が表示される
  - JSON に削除済み ID が記録されている
  - DB から動画が削除されている（確認コマンド下記）

```bash
# DB から削除されたか確認
python -c "from database import get_database; db = get_database(); \
result = db.video_exists('yt123abc'); print(f'Exists: {result}')"
# 期待: Exists: False
```

- ❌ **失敗**: 削除処理が失敗するか、ブラックリストに登録されない

---

## テスト 4: ブラックリスト確認（RSS 重複判定）

**目的**: 削除した動画が RSS で再度検出されても、DB に入らないか

### 実行手順

```bash
# 1. テスト 3 で削除した動画の ID を記録
# 例: yt123abc

# 2. 削除済み JSON で ID が記録されているか確認
grep "yt123abc" data/deleted_videos.json

# 3. RSS 取得処理を再実行（5 分待つか、手動トリガー）
# → 同じ動画が RSS に再度含まれている場合、スキップされるか確認

# 4. ログで確認
grep "ブラックリスト登録済み\|ブラックリスト確認\|保存完了" logs/app.log

# 期待される出力例:
# [INFO] ⏭️ ブラックリスト登録済みのため、スキップします: [Video Title]
# [INFO] ✅ 保存完了: 新規 0, 既存 12, ブラックリスト 1
```

### 結果判定
- ✅ **成功**:
  - ブラックリストに登録されている動画は RSS で来ても無視される
  - ログに「ブラックリスト」が表示される
  - DB に再度挿入されない

```bash
# DB に再度挿入されていないか確認
python -c "from database import get_database; db = get_database(); \
result = db.video_exists('yt123abc'); print(f'Exists: {result}')"
# 期待: Exists: False
```

- ❌ **失敗**: 削除済み動画が再度 DB に挿入される

---

## テスト 5: 複数削除と一括ブラックリスト登録

**目的**: 複数の動画を同時に削除したとき、全て正しくブラックリストに登録されるか

### 実行手順

```bash
# 1. GUI から 3-5 件の動画を選択（☑️ をクリック）

# 2. 「🗑️ 削除」ボタンをクリック

# 3. 確認ダイアログで「はい」をクリック

# 4. ログで確認（複数行）
grep "削除\|ブラックリスト" logs/app.log | tail -20

# 期待される出力例:
# [INFO] ✅ 動画を削除しました: yt123abc
# [INFO] ✅ ブラックリストに追加しました: yt123abc (source: youtube)
# [INFO] ✅ 動画を削除しました: yt456def
# [INFO] ✅ ブラックリストに追加しました: yt456def (source: youtube)
# [INFO] ✅ 削除完了: 2 件

# 5. JSON で全て登録されているか確認
cat data/deleted_videos.json | python -m json.tool
```

### 結果判定
- ✅ **成功**: 全ての削除済み ID が JSON に記録されている
- ❌ **失敗**: 一部の ID が登録されない、または JSON が破損している

---

## テスト 6: ブラックリスト JSON 破損時の回復

**目的**: JSON ファイルが破損していても、アプリケーションが動作し続けるか

### 実行手順

```bash
# 1. JSON ファイルを意図的に破損
echo '{"youtube": ["yt123abc"]}' > data/deleted_videos.json
# （末尾に "," を残すなど、不正な JSON）

# 2. アプリケーションを起動
python main_v2.py

# 3. ログで確認
grep "形式エラー\|リセット\|警告" logs/app.log

# 期待される出力例:
# [ERROR] ❌ ブラックリスト JSON の形式エラー: ...
# [WARNING] ブラックリスト JSON をリセットします

# 4. JSON ファイルが自動修復されているか確認
cat data/deleted_videos.json

# 期待: デフォルト構造（youtube/niconico/twitch が空配列）
```

### 結果判定
- ✅ **成功**:
  - エラーログが記録される
  - JSON が自動修復される
  - アプリケーションが継続動作する
- ❌ **失敗**: JSON エラーでアプリケーションが停止する

---

## テスト 7: ブラックリストのパフォーマンス

**目的**: 大量の削除済み動画でも処理速度に問題がないか

### 実行手順

```bash
# 1. ブラックリストに多数の ID を追加（シミュレーション）
python -c "
from deleted_video_cache import get_deleted_video_cache
cache = get_deleted_video_cache()
for i in range(1000):
    cache.add_deleted_video(f'yt_sim_{i:04d}', source='youtube')
print('1000 個の削除済み ID を追加しました')
"

# 2. ログで確認
grep "ブラックリストに追加\|保存" logs/app.log | tail -5

# 3. RSS 取得処理を実行
# → 処理時間に問題がないか観察

# 4. JSON ファイルサイズ確認
ls -lh data/deleted_videos.json

# 期待: 数 KB 程度（問題なければ 100KB 以下）
```

### 結果判定
- ✅ **成功**: 1000 件でも処理速度に問題がない、JSON ファイルが適切なサイズ
- ⚠️ **警告**: JSON ファイルが過度に大きい場合、クリーンアップ機能の追加を検討

---

## テスト 8: 自動ポストとブラックリスト

**目的**: 自動ポストモードでブラックリストが正しく機能するか

### 実行手順

```bash
# 1. settings.env で OPERATION_MODE を設定
sed -i 's/OPERATION_MODE=.*/OPERATION_MODE=auto_post/' settings.env

# 2. アプリケーションを起動（自動ポスト有効）
python main_v2.py &

# 3. RSS 取得処理を待機（5-10 分）
# 　または、test/auto_post_simulation.py でシミュレーション

# 4. ログで確認
grep "保存完了\|ブラックリスト" logs/post.log logs/app.log

# 期待: 自動ポスト中もブラックリストが参照される

# 5. 自動ポスト停止
kill %1
```

### 結果判定
- ✅ **成功**: 自動ポストモードでもブラックリスト動作に問題がない
- ❌ **失敗**: 自動ポストとブラックリストに競合がある

---

## トラブルシューティング

### Q: ブラックリスト JSON が作成されない

**原因**: data/ ディレクトリの権限不足

**解決方法**:
```bash
chmod 755 data/
chmod 644 data/*.json
```

### Q: JSON が破損して修復されない

**原因**: エラーハンドリング不足

**解決方法**:
```bash
# 手動でリセット
rm data/deleted_videos.json
# アプリケーション再起動
python main_v2.py
```

### Q: ブラックリストに ID が記録されない

**原因**: database.py の修正が反映されていない

**解決方法**:
```bash
# Python キャッシュをクリア
find . -type d -name __pycache__ -exec rm -rf {} +
find . -type f -name "*.pyc" -delete

# 再起動
python main_v2.py
```

### Q: 削除済み動画が RSS で再度 DB に入る

**原因**: youtube_rss.py の修正が反映されていない

**解決方法**: 上記と同じ（キャッシュクリア + 再起動）

---

## テスト完了チェックリスト

| テスト | 結果 | コメント |
|:--|:--:|:--|
| テスト 1: JSON 初期化 | ⬜ | |
| テスト 2: RSS 保存 | ⬜ | |
| テスト 3: 削除 & ブラックリスト | ⬜ | |
| テスト 4: ブラックリスト確認 | ⬜ | |
| テスト 5: 複数削除 | ⬜ | |
| テスト 6: JSON 破損回復 | ⬜ | |
| テスト 7: パフォーマンス | ⬜ | |
| テスト 8: 自動ポスト | ⬜ | |

**全テスト成功**: ✅ ブラックリスト機能は本番環境にデプロイ可能

---

**最終更新**: 2025-12-18
**実施者**: [名前]
**テスト環境**: [OS/Python バージョン]
