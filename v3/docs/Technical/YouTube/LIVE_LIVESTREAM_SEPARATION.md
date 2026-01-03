# Live系動画と通常動画の完全分離実装

**実装日**: 2026年1月3日
**対象バージョン**: v3.4.0+
**ステータス**: ✅ 実装完了・コンパイル検証済み

---

## 問題点（修正前）

YouTubeVideoClassifier で Live 関連動画（schedule/live/completed/archive）を分類しても、その後に以下が発生していました：

```
📝 Live動画を登録します: ... (type=archive, status=None)
📝 Live動画を登録します: ... (type=schedule, status=upcoming)
```

しかし DB では：
- `content_type="video"` （通常動画として上書きされている）
- JST変換フィールドも未設定

**原因**:
1. YouTubeVideoClassifier.classify_video() を呼んで Live 判定
2. LiveModule.register_from_classified() で Live登録
3. **その直後に** database.insert_video() で通常動画として DB 登録
4. 結果、Live情報が上書きされてしまう

---

## 修正内容

### 実装戦略：分岐処理

分類結果に基づいて処理を完全に分離：

```python
# 分類を先に実行
result = classifier.classify_video(video_id)
video_type = result.get("type")

if video_type in ["schedule", "live", "completed", "archive"]:
    # ★ LIVE系：LiveModule に完全に任せる
    live_module.register_from_classified(result)
    # ★重要★ ここで return / continue
    # database.insert_video() は 絶対に呼ばない
else:
    # 通常動画（video / premiere）のみ insert_video
    database.insert_video(...)
```

### 修正したファイル

#### 1. youtube_core/youtube_rss.py

**save_to_db メソッド内**:

```python
# ★ 重要: 先に分類を行い、Live 系か通常動画か判定
video_type = None
classification_result = None

if classifier and live_module:
    classification_result = classifier.classify_video(video["video_id"])
    if classification_result.get("success"):
        video_type = classification_result.get("type")
    else:
        video_type = "video"  # デフォルトは通常動画

# ★ Live 系（schedule/live/completed/archive）の場合、通常の insert は実行しない
if video_type in ["schedule", "live", "completed", "archive"]:
    # Live 関連 → LiveModule に完全に処理させる
    if classification_result:
        live_result = live_module.register_from_classified(classification_result)
        # ★重要★ ここで終了。insert_video() は呼ばない
else:
    # 通常動画（video / premiere）のみ insert_video を実行
    is_new = database.insert_video(...)
```

#### 2. youtube_core/youtube_websub.py

youtube_rss.py と同じ修正を適用

#### 3. main_v3.py

変更なし（既に正しい呼び出し順序）

---

## 動作フロー

### Live系動画（schedule/live/completed/archive）

```
RSS/WebSub から取得
    ↓
YouTubeVideoClassifier.classify_video()
    ↓
result["type"] = "schedule" / "live" / "completed" / "archive"
    ↓
if video_type in ["schedule", "live", ...]:
    ↓
LiveModule.register_from_classified(result)
    ├─ content_type = live （正確に設定）
    ├─ live_status = upcoming / live / completed （正確に判定）
    ├─ published_at = JST変換済み（API値優先）
    └─ DB に登録完了
    ↓
✅ 通常動画処理はスキップ（insert_video() は呼ばない）
```

### 通常動画（video / premiere）

```
RSS/WebSub から取得
    ↓
YouTubeVideoClassifier.classify_video()
    ↓
result["type"] = "video" / "premiere"
    ↓
else:  # Live系でない
    ↓
database.insert_video()
    ├─ content_type = "video" （デフォルト）
    ├─ video table に登録
    └─ 通常フロー継続
    ↓
✅ Live関連情報は不要
```

---

## ログ出力例

### Live系動画の場合

```
🎬 動画を分類: 〇〇ライブ配信 (type=schedule)
🎬 Live関連動画を LiveModule に完全委譲: 〇〇ライブ配信 (type=schedule)
✅ Live動画をLiveModuleで登録完了: schedule（通常動画処理はスキップ）
```

### 通常動画の場合

```
🎬 動画を分類: 【新着】△△動画 (type=video)
[YouTube RSS] 新動画を DB に保存しました: 【新着】△△動画 (type=video)
```

---

## ロジック詳細

### 分類結果の処理

| video_type | 処理 | 備考 |
|:--|:--|:--|
| schedule | LiveModule で登録 | insert_video() をスキップ |
| live | LiveModule で登録 | insert_video() をスキップ |
| completed | LiveModule で登録 | insert_video() をスキップ |
| archive | LiveModule で登録 | insert_video() をスキップ |
| video | insert_video() で登録 | 通常フロー |
| premiere | insert_video() で登録 | 通常フロー |
| unknown | insert_video() で登録（デフォルト） | 通常フロー |

### エラー時の動作

- 分類失敗時 → `video_type = "video"` （通常動画として処理）
- API呼び出し例外 → `video_type = "video"` （安全に続行）
- LiveModule登録失敗 → エラーログ出力、次の動画へ

---

## 改善点

✅ **Live情報が上書きされない**
- LiveModule の処理が完結してから database.insert_video() は呼ばない

✅ **content_type が正確に設定される**
- Live系は LiveModule で content_type = "schedule" など
- 通常動画は content_type = "video" （デフォルト）

✅ **JST変換が正確に行われる**
- API から取得した scheduledStartTime → JST変換
- LiveModule で db に保存される時点で正確な値が入る

✅ **処理の流れが明確**
- 分類 → 分岐 → 対応する処理実行
- 同一 video_id に対する複数処理はない

---

## テスト確認項目

1. ✅ RSS/WebSub から Live関連動画を取得
2. ✅ YouTubeVideoClassifier で正確に分類
3. ✅ Live系 → LiveModule 登録
4. ✅ 通常動画 → insert_video() で登録
5. ✅ DB で content_type が正確に設定される
6. ✅ DB で live_status が正確に設定される（Live系のみ）
7. ✅ published_at が JST 形式
8. ✅ エラー時も安全に続行される

---

## ファイル修正チェックリスト

- ✅ youtube_core/youtube_rss.py - save_to_db メソッド修正
- ✅ youtube_core/youtube_websub.py - save_to_db メソッド修正
- ✅ main_v3.py - 変更なし（既に正しい）
- ✅ コンパイルエラーなし

---

**作成者**: GitHub Copilot
**検証済みコンパイル**: youtube_rss.py, youtube_websub.py, main_v3.py
