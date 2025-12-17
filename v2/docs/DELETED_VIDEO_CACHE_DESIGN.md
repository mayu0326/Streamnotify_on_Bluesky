# 削除済み動画ブラックリスト機能 - 設計・実装ガイド

**対象バージョン：** v2.1.1+
**実施日：** 2025年12月18日
**ステータス：** 🔧 実装準備完了

---

## 1. 要件分析

### 1.1 ユースケース

**シナリオ：** ユーザーが GUI から「動画を削除」

```
【状態 1】DB に動画 "yt123abc" が存在
   ↓
【ユーザー操作】GUI の「削除」ボタンをクリック
   ↓
【状態 2】DB から削除、ブラックリスト JSON に追記
   └─ data/deleted_videos.json:
      {
        "youtube": ["yt123abc"],
        "niconico": []
      }
   ↓
【状態 3】次の RSS チェック時、同じ動画が再度来ても
   └─ ブラックリストに存在 → 「削除済み」と判定 → DB に入れない
```

### 1.2 必須要件

| 要件 | 詳細 |
|:--|:--|
| 保存先 | `v2/data/deleted_videos.json`（DB ではなく JSON ファイル） |
| 形式 | `{"youtube": ["id1", "id2"], "niconico": ["sm00000"], ...}` |
| 読み書き | JSON 操作モジュールで抽象化 |
| エラー処理 | JSON 破損時もアプリ落とさない（WARNING/ERROR ログのみ） |
| 初期化 | ファイルなければ自動作成 |
| スコープ | アプリケーション全体で共有（シングルトン パターン） |

---

## 2. 実装設計

### 2.1 モジュール構成

```
v2/
├── deleted_video_cache.py        ← 新規作成: ブラックリスト管理
├── database.py                    ← 修正: delete_video() 時にブラックリストに追記
├── youtube_rss.py                 ← 修正: 新着判定前にブラックリスト確認
└── gui_v2.py                      ← 修正: 削除時にブラックリスト連携
```

### 2.2 deleted_video_cache.py（新規）

**責務：**
- ブラックリスト JSON の読み書き
- サービス別（youtube/niconico）の ID 管理
- エラー耐性（JSON 破損時も継続動作）

**API 仕様：**

```python
class DeletedVideoCache:
    """削除済み動画キャッシュ管理"""

    def __init__(self, cache_file: str = "data/deleted_videos.json"):
        """初期化（ファイルなければ作成）"""

    def is_deleted(self, video_id: str, source: str = "youtube") -> bool:
        """動画 ID がブラックリストに含まれているか"""

    def add_deleted_video(self, video_id: str, source: str = "youtube") -> bool:
        """ブラックリストに ID を追加"""

    def remove_deleted_video(self, video_id: str, source: str = "youtube") -> bool:
        """ブラックリストから ID を削除"""

    def get_deleted_count(self, source: str = None) -> int:
        """削除済み動画数を取得"""

    def clear_all_deleted() -> bool:
        """全ブラックリストをクリア"""
```

### 2.3 統合ポイント

#### 2.3.1 database.py への変更

**`delete_video()` メソッド**

```python
def delete_video(self, video_id: str) -> bool:
    """
    動画を削除（ブラックリスト連携付き）

    Args:
        video_id: 削除対象の動画 ID

    Returns:
        削除成功の可否
    """
    try:
        # 1. DB から削除
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM videos WHERE video_id = ?", (video_id,))
        self.conn.commit()

        # 2. ブラックリストに追加
        from deleted_video_cache import get_deleted_video_cache
        cache = get_deleted_video_cache()

        # source を事前に取得して渡す
        cursor.execute("SELECT source FROM videos WHERE video_id = ?", (video_id,))
        row = cursor.fetchone()
        source = row[0] if row else "youtube"

        cache.add_deleted_video(video_id, source=source)
        logger.info(f"✅ 動画を削除しました: {video_id} → ブラックリストに登録")
        return True
    except Exception as e:
        logger.error(f"❌ 動画削除に失敗: {video_id}: {e}")
        return False
```

#### 2.3.2 youtube_rss.py への変更

**`save_to_db()` メソッド**

```python
def save_to_db(self, database) -> int:
    """RSS 動画を DB に保存（ブラックリスト確認付き）"""
    videos = self.fetch_feed()
    saved_count = 0
    existing_count = 0
    blacklist_skip_count = 0

    from deleted_video_cache import get_deleted_video_cache
    deleted_cache = get_deleted_video_cache()

    for video in videos:
        # ★ 新: ブラックリスト確認
        if deleted_cache.is_deleted(video["video_id"], source="youtube"):
            logger.info(f"⏭️ ブラックリスト登録済みのため、スキップします: {video['video_id']}")
            blacklist_skip_count += 1
            continue

        # 既存ロジック（DB に存在するか確認）
        if database.video_exists(video["video_id"]):
            existing_count += 1
            continue

        # DB に追加
        if database.add_video(video):
            saved_count += 1

    logger.info(f"RSS 保存完了: 新規 {saved_count}, 既存 {existing_count}, ブラックリスト {blacklist_skip_count}")
    return saved_count
```

#### 2.3.3 gui_v2.py への変更

**削除処理**

```python
def on_delete_selected():
    """選択動画を削除"""
    selection = self.tree.selection()
    if not selection:
        messagebox.showwarning("警告", "削除対象を選択してください")
        return

    if messagebox.askyesno("確認", "選択した動画を削除しますか？"):
        for item_id in selection:
            video_id = self.tree.item(item_id, "values")[0]

            # ★ 修正: DB 削除時にブラックリスト追加
            if self.db.delete_video(video_id):  # delete_video() 内でブラックリスト登録
                logger.info(f"✅ 削除完了: {video_id}")
            else:
                logger.error(f"❌ 削除失敗: {video_id}")

        self.refresh()  # リスト更新
```

---

## 3. deleted_video_cache.py - 実装コード

```python
# -*- coding: utf-8 -*-

"""
Stream notify on Bluesky - 削除済み動画ブラックリスト管理

削除済み動画の ID をサービス別に JSON ファイルで管理。
新着動画検出時にこのリストをチェック。
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger("AppLogger")

__author__ = "mayuneco(mayunya)"
__copyright__ = "Copyright (C) 2025 mayuneco(mayunya)"
__license__ = "GPLv2"

# グローバル キャッシュインスタンス
_deleted_video_cache = None


class DeletedVideoCache:
    """削除済み動画キャッシュ管理"""

    def __init__(self, cache_file: str = "data/deleted_videos.json"):
        """
        初期化

        Args:
            cache_file: ブラックリスト JSON ファイルのパス
        """
        self.cache_file = Path(cache_file)
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        self.data = {}
        self._load()

    def _load(self) -> None:
        """JSON ファイルから読み込み"""
        if not self.cache_file.exists():
            logger.debug(f"ブラックリスト JSON が存在しません。新規作成します: {self.cache_file}")
            self._create_default()
            self._save()
            return

        try:
            with open(self.cache_file, "r", encoding="utf-8") as f:
                self.data = json.load(f)
            logger.info(f"✅ ブラックリストを読み込みました: {self.cache_file}")
        except json.JSONDecodeError as e:
            logger.error(f"❌ ブラックリスト JSON の形式エラー: {e}")
            self._create_default()
            self._save()
        except Exception as e:
            logger.error(f"❌ ブラックリスト読み込みエラー: {e}")
            self._create_default()

    def _save(self) -> bool:
        """JSON ファイルに保存"""
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
            logger.debug(f"✅ ブラックリストを保存しました: {self.cache_file}")
            return True
        except Exception as e:
            logger.error(f"❌ ブラックリスト保存エラー: {e}")
            return False

    def _create_default(self) -> None:
        """デフォルト構造を作成"""
        self.data = {
            "youtube": [],
            "niconico": [],
            "twitch": [],
        }
        logger.debug("ブラックリストをリセットしました")

    def is_deleted(self, video_id: str, source: str = "youtube") -> bool:
        """
        動画 ID がブラックリストに含まれているか

        Args:
            video_id: チェック対象の動画 ID
            source: サービス名（"youtube", "niconico" など）

        Returns:
            True: ブラックリストに含まれている（削除済み）
            False: ブラックリストに含まれていない
        """
        source_lower = source.lower()
        if source_lower not in self.data:
            return False

        is_blacklisted = video_id in self.data[source_lower]
        if is_blacklisted:
            logger.debug(f"⏭️ ブラックリスト確認: {video_id} (source: {source})")
        return is_blacklisted

    def add_deleted_video(self, video_id: str, source: str = "youtube") -> bool:
        """
        ブラックリストに ID を追加

        Args:
            video_id: 追加対象の動画 ID
            source: サービス名

        Returns:
            成功の可否
        """
        source_lower = source.lower()

        # サービスキーがなければ作成
        if source_lower not in self.data:
            self.data[source_lower] = []

        # 重複チェック
        if video_id in self.data[source_lower]:
            logger.debug(f"既にブラックリスト登録済みです: {video_id} (source: {source})")
            return True

        # リストに追加
        self.data[source_lower].append(video_id)
        logger.info(f"✅ ブラックリストに追加しました: {video_id} (source: {source})")

        # 保存
        return self._save()

    def remove_deleted_video(self, video_id: str, source: str = "youtube") -> bool:
        """
        ブラックリストから ID を削除

        Args:
            video_id: 削除対象の動画 ID
            source: サービス名

        Returns:
            成功の可否
        """
        source_lower = source.lower()

        if source_lower not in self.data:
            logger.debug(f"サービス '{source}' はブラックリストに存在しません")
            return False

        if video_id not in self.data[source_lower]:
            logger.debug(f"動画 ID '{video_id}' はブラックリスト登録されていません")
            return False

        # リストから削除
        self.data[source_lower].remove(video_id)
        logger.info(f"🗑️ ブラックリストから削除しました: {video_id} (source: {source})")

        # 保存
        return self._save()

    def get_deleted_count(self, source: Optional[str] = None) -> int:
        """
        削除済み動画数を取得

        Args:
            source: サービス名（None の場合は全体）

        Returns:
            削除済み動画数
        """
        if source is None:
            # 全サービスの合計
            return sum(len(ids) for ids in self.data.values())

        source_lower = source.lower()
        return len(self.data.get(source_lower, []))

    def clear_all_deleted(self) -> bool:
        """全ブラックリストをクリア"""
        try:
            self._create_default()
            self._save()
            logger.info("✅ ブラックリストをクリアしました")
            return True
        except Exception as e:
            logger.error(f"❌ ブラックリストクリアエラー: {e}")
            return False

    def get_deleted_videos(self, source: Optional[str] = None) -> dict:
        """
        ブラックリストの内容を取得

        Args:
            source: サービス名（None の場合は全体）

        Returns:
            ブラックリストデータ
        """
        if source is None:
            return dict(self.data)

        source_lower = source.lower()
        return {source_lower: self.data.get(source_lower, [])}


def get_deleted_video_cache(cache_file: str = "data/deleted_videos.json") -> DeletedVideoCache:
    """グローバル キャッシュインスタンスを取得（シングルトン）"""
    global _deleted_video_cache
    if _deleted_video_cache is None:
        _deleted_video_cache = DeletedVideoCache(cache_file)
    return _deleted_video_cache
```

---

## 4. 統合チェックリスト

| 項目 | 修正ファイル | 状態 |
|:--|:--|:--:|
| ブラックリスト モジュール作成 | `deleted_video_cache.py` | ⏳ |
| DB 削除処理 修正 | `database.py::delete_video()` | ⏳ |
| RSS 新着判定 修正 | `youtube_rss.py::save_to_db()` | ⏳ |
| GUI 削除処理 修正 | `gui_v2.py::on_delete_selected()` | ⏳ |
| ブラックリスト JSON 自動作成 | `data/deleted_videos.json` | ⏳ |
| ドキュメント作成 | `docs/DELETED_VIDEO_CACHE.md` | ⏳ |

---

## 5. ログ出力例

### 初回起動（ブラックリスト作成）

```
[INFO] ✅ ブラックリストを読み込みました: data/deleted_videos.json
[DEBUG] ブラックリスト JSON が存在しません。新規作成します: data/deleted_videos.json
[DEBUG] ✅ ブラックリストを保存しました: data/deleted_videos.json
```

### 動画削除時

```
[INFO] ✅ 動画を削除しました: yt123abc → ブラックリストに登録
[INFO] ✅ ブラックリストに追加しました: yt123abc (source: youtube)
[DEBUG] ✅ ブラックリストを保存しました: data/deleted_videos.json
```

### RSS 取得時（ブラックリスト確認）

```
[INFO] RSS から 15 個の動画を取得しました
[DEBUG] ⏭️ ブラックリスト確認: yt123abc (source: youtube)
[INFO] RSS 保存完了: 新規 3, 既存 10, ブラックリスト 2
```

---

## 6. テスト手順

### テスト 1: ブラックリスト JSON 作成

```bash
# 初回起動
python main_v2.py

# 確認: data/deleted_videos.json が作成されているか
ls -la data/deleted_videos.json
cat data/deleted_videos.json
# 出力:
# {
#   "youtube": [],
#   "niconico": [],
#   "twitch": []
# }
```

### テスト 2: 動画削除とブラックリスト登録

```bash
# 1. GUI から動画を削除
# 2. logs/app.log を確認
grep "ブラックリストに追加" logs/app.log
# 出力: ✅ ブラックリストに追加しました: yt123abc

# 3. JSON を確認
cat data/deleted_videos.json
# 出力:
# {
#   "youtube": ["yt123abc"],
#   ...
# }
```

### テスト 3: ブラックリスト確認（RSS チェック時）

```bash
# 1. RSS 取得（同じ動画が再度来る状況をシミュレート）
# 2. logs/app.log を確認
grep "ブラックリスト確認\|保存完了" logs/app.log
# 出力:
# ⏭️ ブラックリスト確認: yt123abc
# RSS 保存完了: 新規 3, 既存 10, ブラックリスト 1
```

---

## 7. 今後の拡張

- [ ] ブラックリスト UI表示（削除済み動画数をステータスバーに表示）
- [ ] ブラックリスト リストア機能（削除した動画を復活させる）
- [ ] 期限付きブラックリスト（例：30日後に自動削除）
- [ ] ユーザー定義のスキップリスト

---

**著作権**: Copyright (C) 2025 mayuneco(mayunya)
**ライセンス**: GPLv2
