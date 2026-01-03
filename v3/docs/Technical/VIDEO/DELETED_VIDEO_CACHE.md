# v3 削除済み動画除外リスト - 完全ガイド

**対象バージョン**: v3.1.1+
**最終更新**: 2025-12-18
**ステータス**: ✅ 実装完了・検証済み

---

## 📖 目次

1. [概要](#概要)
2. [要件分析](#要件分析)
3. [実装設計](#実装設計)
4. [API リファレンス](#apiリファレンス)
5. [統合ポイント](#統合ポイント)
6. [テスト手順](#テスト手順)
7. [トラブルシューティング](#トラブルシューティング)

---

## 概要

### 背景

**問題**:
ユーザーが GUI から「削除」した動画が、次の RSS チェック時に「新規動画」と誤認されて再度 DB に挿入される

**解決**:
- ✅ 除外動画リスト JSON（`data/deleted_videos.json`）で削除済み ID を管理
- ✅ RSS 取得時に除外動画リストをチェック → 該当動画をスキップ
- ✅ サービス別（YouTube/Niconico）ID 分類対応
- ✅ JSON 破損時も自動修復でアプリ落とさない

### 機能

| 機能 | 説明 |
|:--|:--|
| **除外動画リスト管理** | JSON ファイルで削除済み ID を永続化 |
| **自動チェック** | RSS 取得時に自動的に除外動画リストと照合 |
| **エラー耐性** | JSON 破損時も自動修復、アプリ落とさない |
| **ロギング** | 削除・追加時に詳細ログを記録 |
| **サービス分類** | YouTube、Niconico など複数サービスに対応 |

---

## 要件分析

### ユースケース

```
【状態 1】DB に動画 "yt123abc" が存在
   ↓
【ユーザー操作】GUI の「削除」ボタンをクリック
   ↓
【状態 2】DB から削除、除外動画リスト JSON に追記
   └─ data/deleted_videos.json:
      {
        "youtube": ["yt123abc"],
        "niconico": []
      }
   ↓
【状態 3】次の RSS チェック時、同じ動画が再度来ても
   └─ 除外動画リストに存在 → 「削除済み」と判定 → DB に入れない
```

### 必須要件

| 要件 | 詳細 |
|:--|:--|
| 保存先 | `v3/data/deleted_videos.json`（DB ではなく JSON ファイル） |
| 形式 | `{"youtube": ["id1", "id2"], "niconico": ["sm00000"], ...}` |
| 読み書き | JSON 操作モジュールで抽象化 |
| エラー処理 | JSON 破損時もアプリ落とさない（WARNING/ERROR ログのみ） |
| 初期化 | ファイルなければ自動作成 |
| スコープ | アプリケーション全体で共有（シングルトンパターン） |

---

## 実装設計

### モジュール構成

```
v3/
├── deleted_video_cache.py        ← 新規作成: 除外動画リスト管理
├── database.py                    ← 修正: delete_video() 時に除外動画リストに追記
├── youtube_rss.py                 ← 修正: 新着判定前に除外動画リスト確認
└── gui_v3.py                      ← 修正: 削除時に除外動画リスト連携
```

### ファイル構成

#### deleted_video_cache.py（新規作成）

**責務**:
- 除外動画リスト JSON の読み書き
- サービス別（youtube/niconico）の ID 管理
- エラー耐性（JSON 破損時も継続動作）

**データ構造**:
```json
{
  "youtube": ["yt_id_1", "yt_id_2"],
  "niconico": ["sm12345678"],
  "twitch": []
}
```

**特徴**:
- 自動初期化（ファイルなければ作成）
- JSON 破損時の自動修復
- エラーハンドリング充実（アプリ落とさない）
- ロギング完備（emoji 付き）

---

## API リファレンス

### DeletedVideoCache クラス

```python
from deleted_video_cache import get_deleted_video_cache

# シングルトン取得
cache = get_deleted_video_cache()
```

### メソッド

#### `is_deleted(video_id: str, source: str = "youtube") -> bool`

動画 ID が除外動画リストに含まれているか確認

**パラメータ**:
- `video_id` (str): チェック対象の動画 ID
- `source` (str): サービス名（"youtube", "niconico", "twitch"）

**戻り値**:
- `True`: 除外動画リストに含まれている
- `False`: 含まれていない
**ログ出力**:
- リストに含まれている場合: DEBUG レベルで `⏭️ 除外動画リスト確認: {video_id}`
- 含まれていない場合: ログ出力なし

**動作**:
- サービス名を小文字に正規化
- サービスキーが存在しない場合: False を返す
- リスト内の ID と完全一致で判定
**例**:
```python
if cache.is_deleted("yt123abc", source="youtube"):
    print("この動画は削除済みです")
else:
    print("新規動画として処理")
```

#### `add_deleted_video(video_id: str, source: str = "youtube") -> bool`

除外動画リストに ID を追加

**パラメータ**:
- `video_id` (str): 追加対象の動画 ID
- `source` (str): サービス名

**戻り値**:
- `True`: 追加成功（または既に含まれている場合も True）
- `False`: 追加失敗（ファイル保存エラー等）

**ログ出力**:
- 新規追加時: INFO レベルで `✅ 除外動画リストに追加しました`
- 既に含まれている場合: DEBUG レベルで `既に除外動画リスト登録済みです`

**動作**:
- 指定したサービスキーが存在しなければ自動作成
- 重複チェック後、リストに追加して JSON ファイルに保存

**例**:
```python
if cache.add_deleted_video("yt123abc", source="youtube"):
    logger.info("✅ 除外動画リストに追加しました")
else:
    logger.warning("⚠️ 除外動画リストへの追加に失敗しました")
```

#### `remove_deleted_video(video_id: str, source: str = "youtube") -> bool`

除外動画リストから ID を削除

**パラメータ**:
- `video_id` (str): 削除対象の動画 ID
- `source` (str): サービス名

**戻り値**:
- `True`: 削除成功
- `False`: 削除失敗（含まれていない、サービス未存在等）

**ログ出力**:
- 削除成功時: INFO レベルで `🗑️ 除外動画リストから削除しました`
- 失敗時: DEBUG レベルで詳細メッセージ

**動作**:
- サービスキーが存在するか確認
- 動画 ID がリストに含まれているか確認
- リストから削除して JSON ファイルに保存

**例**:
```python
if cache.remove_deleted_video("yt123abc", source="youtube"):
    logger.info("✅ 除外動画リストから削除しました")
else:
    logger.warning("⚠️ 除外動画リストから削除できません")
```

#### `get_deleted_count(source: str = None) -> int`

削除済み動画数を取得

**パラメータ**:
- `source` (str, optional): サービス名。None の場合は全サービスの合計

**戻り値**:
- (int): 削除済み動画の件数

**動作**:
- `source=None` の場合: すべてのサービスの ID 数を合計
- `source=\"youtube\"` の場合: YouTube のみの ID 数
- サービスキーが存在しない場合: 0 を返す

**例**:
```python
yt_count = cache.get_deleted_count("youtube")        # YouTube のみ
nico_count = cache.get_deleted_count("niconico")      # Niconico のみ
total_count = cache.get_deleted_count()              # 全サービスの合計
print(f"削除済み: YouTube {yt_count}, Niconico {nico_count}, 合計 {total_count}")
```

#### `clear_all_deleted() -> bool`

全除外動画リストをクリア（デフォルト構造にリセット）

**戻り値**:
- `True`: クリア成功
- `False`: クリア失敗

**ログ出力**:
- 成功時: INFO レベルで `✅ 除外動画リストをクリアしました`
- 失敗時: ERROR レベルで詳細メッセージ

**動作**:
- `{\"youtube\": [], \"niconico\": [], \"twitch\": []}` の状態にリセット
- JSON ファイルに保存

**例**:
```python
if cache.clear_all_deleted():
    logger.info("✅ 除外動画リストをクリアしました")
else:
    logger.error("❌ 除外動画リストのクリアに失敗")
```
```

---

## 統合ポイント

### database.py - `delete_video()` メソッド

**変更内容**:

削除時に自動的に除外動画リストに登録し、画像情報を返却

```python
def delete_video(self, video_id: str) -> dict:
    """動画をDBから削除（除外動画リスト連携付き・画像情報付き返却）

    返却される辞書で、呼び出し元（GUI）が画像ファイルの削除を判断できるようにする。

    Returns:
        {
            "success": bool,           # 削除成功フラグ
            "image_filename": str,     # 削除対象の画像ファイル名
            "source": str,             # 配信元（youtube / niconico など）
        }
    """

    result = {"success": False, "image_filename": None, "source": "youtube"}

    # 削除前に video_id, source, image_filename, image_mode を取得
    cursor.execute(
        "SELECT source, image_filename, image_mode FROM videos WHERE video_id = ?",
        (video_id,)
    )
    row = cursor.fetchone()

    if row:
        result["source"] = row["source"] or "youtube"
        result["image_filename"] = row["image_filename"]  # None でも OK（呼び出し元で判定）

    # DB から削除
    cursor.execute("DELETE FROM videos WHERE video_id = ?", (video_id,))
    result["success"] = True

    # ★ 新: 除外動画リストに追加
    try:
        from deleted_video_cache import get_deleted_video_cache
        cache = get_deleted_video_cache()
        cache.add_deleted_video(video_id, source=result["source"])
    except Exception as e:
        logger.error(f"除外動画リスト登録エラー: {video_id} - {e}")

    logger.info(f"✅ 動画を削除しました: {video_id}")
    return result
```

**戻り値の仕様**:
- `success`: 削除成功フラグ
- `image_filename`: 削除時に画像も削除する必要があるかを GUI が判定するため
- `source`: サービス別の画像ディレクトリを特定するため

### youtube_rss.py など - RSS 取得時の除外動画リストチェック

**変更内容**:

RSS から取得した動画を DB に追加する前に除外動画リストをチェック

```python
from deleted_video_cache import get_deleted_video_cache

def save_to_db(self, videos: list) -> tuple:
    """RSS 動画を DB に保存"""

    new_count = 0
    existing_count = 0

    for video in videos:
        video_id = video["video_id"]
        source = video.get("source", "youtube")

        # ★ 新: 除外動画リスト確認
        cache = get_deleted_video_cache()
        if cache.is_deleted(video_id, source=source):
            logger.debug(f"⏭️ スキップ（削除済み）: {video_id}")
            continue

        # 既存チェック
        if self.db.video_exists(video_id):
            existing_count += 1
            logger.debug(f"既存: {video_id}")
        else:
            # 新規保存
            self.db.insert_video(video)
            new_count += 1
            logger.info(f"✅ 新規保存: {video_id}")

    return new_count, existing_count
```

**特徴**:
- 除外動画リストに含まれている動画は DEBUG レベルで `⏭️ スキップ（削除済み）` をログ出力
- RSS で何度来ても DB に追加されない
- サービス別（YouTube / Niconico など）に正確に判定

### gui_v3.py - 削除ボタンクリック時

**変更内容**:

GUI から削除時に自動的に除外動画リストに登録し、画像ファイルも削除

```python
def on_delete_video(self):
    """動画削除ボタン"""

    selected_item = self.video_list.selection()
    if not selected_item:
        return

    video_id = self.video_list.item(selected_item, "values")[0]

    # DB から削除（自動的に除外動画リスト登録・画像情報返却）
    result = self.db.delete_video(video_id)

    if result["success"]:
        # 画像ファイルも削除（必要な場合）
        if result["image_filename"]:
            self.image_manager.delete_image(result["image_filename"], result["source"])

        self.refresh_video_list()
        logger.info(f"✅ 削除完了: {video_id}")
    else:
        logger.error(f"❌ 削除失敗: {video_id}")
```

**特徴**:
- `delete_video()` が辞書を返すため、画像ファイル情報を取得可能
- GUI は画像ファイル削除の判断を容易に実行
- 除外動画リスト登録は `database.py` 内で自動実行

---

## テスト手順

### テスト環境セットアップ

```bash
# 1. v3/ ディレクトリに移動
cd v3/

# 2. DB とログをリセット（初期化）
rm -f data/video_list.db
rm -f data/deleted_videos.json
rm -rf logs/*

# 3. アプリケーション起動
python main_v3.py
```

### テスト 1: 除外動画リスト JSON 初期化

**目的**: アプリケーション起動時に除外動画リスト JSON が正しく作成されるか

**実行**:

```bash
# アプリケーションを起動
python main_v3.py

# ログで確認
grep "除外動画リスト" logs/app.log

# JSON ファイルを確認
cat data/deleted_videos.json
```

**期待結果**:
- ✅ JSON ファイルが存在
- ✅ デフォルト構造（`{"youtube": [], "niconico": []}`）

### テスト 2: RSS 動画の DB 保存

**目的**: RSS から取得した動画が正しく DB に保存されるか

**実行**:

```bash
# アプリケーション起動（GUI）
python main_v3.py

# 「🔄 取得」ボタンをクリック
# → RSS から動画が DB に保存される

# ログで確認
grep "保存完了" logs/app.log

# DB 確認
python -c "from database import get_database; db = get_database(); \
videos = db.get_all_videos(); print(f'合計: {len(videos)} 件')"
```

**期待結果**:
- ✅ 新規動画が DB に追加される
- ✅ ログに「保存完了」メッセージ

### テスト 3: 動画削除と除外動画リスト登録

**目的**: GUI から動画を削除したとき、除外動画リストに正しく登録されるか

**実行**:

```bash
# 1. GUI でビデオリストから動画を選択
# 2. 「🗑️ 削除」ボタンをクリック
# 3. ログで確認
grep "削除完了" logs/app.log
grep "除外動画リスト登録" logs/app.log

# 4. JSON ファイルを確認
cat data/deleted_videos.json
# → 削除した動画 ID が youtube または niconico 配列に含まれている
```

**期待結果**:
- ✅ DB から動画が削除される
- ✅ `data/deleted_videos.json` にビデオ ID が追加される
- ✅ ログに削除メッセージが出力される

### テスト 4: 除外動画リスト動画のスキップ

**目的**: 削除済み動画が RSS で再度来ても、DB に追加されないか

**実行**:

```bash
# 1. テスト 3 で削除した動画の ID をメモ（例: "yt123abc"）
# 2. 「🔄 取得」ボタンをクリック（RSS 更新）
# 3. ログで確認
grep "スキップ（削除済み）" logs/app.log
# → ビデオ ID が含まれている

# 4. DB 確認
python -c "from database import get_database; db = get_database(); \
video = db.get_video('yt123abc'); print('DB に含まれている' if video else 'DB に含まれていない')"
```

**期待結果**:
- ✅ ログに「スキップ（削除済み）」メッセージが出力される
- ✅ DB に削除済み動画が再追加されない

---

## トラブルシューティング

### 症状 1: JSON ファイルが作成されない

**ログ確認**:

```bash
grep "除外動画リスト" logs/app.log
grep "ERROR" logs/app.log | grep "deleted_videos"
```

**原因と対応**:

| 原因 | 対応 |
|:--|:--|
| `data/` ディレクトリが存在しない | 手動で `data/` ディレクトリを作成 |
| ファイル書き込み権限がない | ディレクトリの権限を確認・変更 |
| ディスク容量不足 | ディスク容量を確認 |

### 症状 2: 削除した動画が再度 DB に追加される

**確認事項**:

```bash
# 1. JSON ファイルが正しく作成されているか
cat data/deleted_videos.json

# 2. 削除時に除外動画リストに登録されているか
grep "✅ 除外動画リストに追加" logs/app.log

# 3. RSS チェック時に除外動画リストを確認しているか
grep "⏭️ スキップ（削除済み）" logs/app.log
```

**対応**:

- ✅ JSON ファイルに動画 ID が含まれているか確認
- ✅ ログに「✅ 除外動画リストに追加」メッセージが出力されているか確認
- ✅ RSS 取得時に「⏭️ スキップ（削除済み）」ログが出力されているか確認
- ❌ 出力されていない場合は、youtube_rss.py など RSS 取得モジュールの `is_deleted()` チェック実装を確認

### 症状 3: JSON ファイルが破損している

**確認**:

```bash
# JSON ファイルが有効か確認
python -c "import json; json.load(open('data/deleted_videos.json'))"
```

**出力**:
- ✅ エラーなし：正常
- ❌ `json.JSONDecodeError`：ファイル破損

**対応**:

自動修復機能が働きます（ログで確認）：

```bash
grep "除外動画リスト JSON の形式エラー" logs/app.log
```

ログに以下が出力されます：

```
❌ 除外動画リスト JSON の形式エラー: ...
⚠️ 除外動画リスト JSON をリセットします
```

ただし、自動修復後もエラーが続く場合は、ファイルを手動で削除してください：

```bash
rm -f data/deleted_videos.json
# アプリケーション再起動 → 新規作成される
```

---

**作成日**: 2025-12-18
**最後の修正**: 2026-01-03
**ステータス**: ✅ 完成・検証済み
