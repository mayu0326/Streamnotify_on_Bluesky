# ログレベル抑制 - LIVE判定ボタンの過度なログ出力修正

**対象バージョン**: v3.3.0+
**修正日**: 2026-01-03
**ステータス**: ✅ 実装完了

---

## 1. 問題の背景

### 症状
LIVE判定ボタンを押すと、本来不要な初期化ログが大量出力されていました：

```
[INFO] 👤 投稿対象をGUIから設定し...
[INFO] 有効なユーザーIDが設定されています。
[INFO] ニコニコ連携機能を有効化しました。
[INFO] 📡 YouTube フィード取得モード: WebSub...
[INFO] 📡 WebSub ポーリング間隔: 5 分
```

### 期待動作
DB更新ログのみが表示されるべき：

```
[INFO] ✅ 動画ステータス更新: lOJ-6AcfdOI (content_type=archive, live_status=None)
```

### 根本原因
`config.py` の Config クラスが初期化時に以下のログを INFO レベルで出力：
- YouTube フィード取得モード設定ログ
- ニコニコユーザーID検証ログ
- ポーリング間隔設定ログ

これらは系統的な初期化メッセージであるため、DEBUG レベルで出すべき。

---

## 2. 修正内容

### 修正ファイル 1: `v3/config.py`

#### 修正 1a: ニコニコ連携機能ログ（行197-201）

**変更前:**
```python
if self.niconico_plugin_exists:
    if self.niconico_user_id:
        logger.info("有効なユーザーIDが設定されています。")
        logger.info("ニコニコ連携機能を有効化しました。")
    else:
        logger.info("有効なユーザーIDが設定されていません。")
        logger.info("ニコニコ連携機能を無効化しました。")
else:
    logger.info("ニコニコプラグインが導入されていません。RSS取得のみで動作します。")
```

**変更後:**
```python
if self.niconico_plugin_exists:
    if self.niconico_user_id:
        logger.debug("有効なユーザーIDが設定されています。")
        logger.debug("ニコニコ連携機能を有効化しました。")
    else:
        logger.debug("有効なユーザーIDが設定されていません。")
        logger.debug("ニコニコ連携機能を無効化しました。")
else:
    logger.debug("ニコニコプラグインが導入されていません。RSS取得のみで動作します。")
```

**変更理由**: システム初期化メッセージは DEBUG レベルで十分（ユーザーが DEBUG_MODE=true 時のみ表示）

#### 修正 1b: YouTube フィード取得モードログ（行107-109）

**変更前:**
```python
if self.youtube_feed_mode == "poll":
    logger.info("📡 YouTube フィード取得モード: RSS ポーリング")
elif self.youtube_feed_mode == "websub":
    logger.info("📡 YouTube フィード取得モード: WebSub（Websubサーバー HTTP API 経由）")
```

**変更後:**
```python
if self.youtube_feed_mode == "poll":
    logger.debug("📡 YouTube フィード取得モード: RSS ポーリング")
elif self.youtube_feed_mode == "websub":
    logger.debug("📡 YouTube フィード取得モード: WebSub（Websubサーバー HTTP API 経由）")
```

#### 修正 1c: ポーリング間隔ログ（行120, 131）

**変更前:**
```python
logger.info(f"📡 WebSub ポーリング間隔: {self.poll_interval_minutes} 分")
logger.info(f"📡 RSS ポーリング間隔: {self.poll_interval_minutes} 分")
```

**変更後:**
```python
logger.debug(f"📡 WebSub ポーリング間隔: {self.poll_interval_minutes} 分")
logger.debug(f"📡 RSS ポーリング間隔: {self.poll_interval_minutes} 分")
```

### 修正ファイル 2: `v3/gui_v3.py`

#### 修正: classify_youtube_live_manually() メソッド

ログレベル一時抑制コードを削除しました。config.py で DEBUG レベルに変更したため、GUI側で個別に抑制する必要がありません。

**削除されたコード:**
```python
# ★ ログレベルを一時的に抑制（config 読み込みのログを出さないため）
import logging
original_config_level = logging.getLogger("AppLogger").level
logging.getLogger("AppLogger").setLevel(logging.WARNING)

classifier = get_video_classifier(api_key=os.getenv("YOUTUBE_API_KEY"))

# ★ ログレベルを復元
logging.getLogger("AppLogger").setLevel(original_config_level)
```

**削除理由**: config.py のログレベルを DEBUG に変更したため、このような一時抑制は不要

---

## 3. 修正後の動作

### LIVE判定ボタンを押すと：

**INFO レベルのログ（デフォルト表示）:**
```
2026-01-03 10:16:44,764 [INFO] 🎬 7 件の Live 動画をキャッシュ更新・判定中...
2026-01-03 10:16:44,764 [INFO] ✅ 動画ステータス更新: lOJ-6AcfdOI (content_type=archive, live_status=None)
2026-01-03 10:16:44,765 [INFO] ✅ YouTube Live 判定完了: キャッシュ確認 7 件、API 更新 0 件、DB 更新 1 件
```

**DEBUG レベルのログ（DEBUG_MODE=true の場合のみ）:**
```
2026-01-03 10:16:44,763 [DEBUG] 有効なユーザーIDが設定されています。
2026-01-03 10:16:44,763 [DEBUG] ニコニコ連携機能を有効化しました。
2026-01-03 10:16:44,763 [DEBUG] 📡 YouTube フィード取得モード: WebSub（Websubサーバー HTTP API 経由）
2026-01-03 10:16:44,763 [DEBUG] 📡 WebSub ポーリング間隔: 5 分
```

### 動作の確認

1. **通常モード（DEBUG_MODE=false）:**
   - LIVE判定ボタンを押す
   - ✅ DB更新ログのみが表示される
   - ❌ 不要な設定ログは表示されない

2. **デバッグモード（DEBUG_MODE=true）:**
   - LIVE判定ボタンを押す
   - ✅ 詳細な DEBUG ログも表示される（必要時のみ）

---

## 4. テスト手順

### テスト 1: 通常モードでのLIIVE判定

```bash
# v3 ディレクトリへ移動
cd v3

# settings.env で DEBUG_MODE=false（デフォルト）確認
grep "DEBUG_MODE" settings.env

# アプリケーション起動
python main_v3.py

# GUI で「LIVE判定」ボタンを押す
# → app.log に以下のみ表示されることを確認：
#   - "🎬 {count} 件の Live 動画をキャッシュ更新・判定中..."
#   - "✅ 動画ステータス更新: {video_id} (...)"
#   - "✅ YouTube Live 判定完了: キャッシュ確認 {count} ..."
```

### テスト 2: デバッグモードでの詳細ログ確認

```bash
# settings.env で DEBUG_MODE=true に変更
# アプリケーション再起動
python main_v3.py

# GUI で「LIVE判定」ボタンを押す
# → app.log に以下も表示されることを確認：
#   - "[DEBUG] 有効なユーザーIDが設定されています。"
#   - "[DEBUG] 📡 YouTube フィード取得モード: ..."
#   - "[DEBUG] 📡 {モード} ポーリング間隔: {分} 分"
```

---

## 5. ログ出力の仕様

### INFO レベル（常に表示）

目的: ユーザーに必要な情報

| ログメッセージ | 対応モジュール | 用途 |
|:--|:--|:--|
| `🎬 {count} 件の Live 動画をキャッシュ更新・判定中...` | gui_v3.py | Live判定開始通知 |
| `✅ 動画ステータス更新: {id} (...)` | database.py | DB更新成功 |
| `✅ YouTube Live 判定完了: ...` | gui_v3.py | Live判定完了通知 |

### DEBUG レベル（DEBUG_MODE=true のみ表示）

目的: 開発者向けの詳細情報

| ログメッセージ | 対応モジュール | 用途 |
|:--|:--|:--|
| `有効なユーザーIDが設定されています。` | config.py | ニコニコID検証結果 |
| `📡 YouTube フィード取得モード: ...` | config.py | フィード取得方式 |
| `📡 {モード} ポーリング間隔: ...` | config.py | ポーリング間隔設定 |
| `📡 API から取得（キャッシュ {分} 分前）: {id}` | gui_v3.py | キャッシュ更新処理 |
| `📦 キャッシュから取得（{分} 分前）: {id}` | gui_v3.py | キャッシュ使用処理 |

---

## 6. 変更点サマリー

| ファイル | 変更行 | 内容 | 理由 |
|:--|:--|:--|:--|
| config.py | 107-109 | logger.info → logger.debug | フィード取得モード設定は初期化情報 |
| config.py | 120 | logger.info → logger.debug | WebSub ポーリング間隔は初期化情報 |
| config.py | 131 | logger.info → logger.debug | RSS ポーリング間隔は初期化情報 |
| config.py | 197-201 | logger.info → logger.debug | ニコニコ連携設定は初期化情報 |
| gui_v3.py | 382-393 | ログレベル抑制コード削除 | config.py 修正で不要に |

---

## 7. 影響範囲

### 機能への影響

- ✅ アプリケーション機能: **変更なし**（ログレベルの変更のみ）
- ✅ LIVE判定動作: **変更なし**
- ✅ DB更新動作: **変更なし**
- ✅ API呼び出し: **変更なし**

### ログ出力への影響

- ✅ 通常モード: **ログが大幅に減少**（初期化ログが非表示に）
- ✅ デバッグモード: **ログが増加**（DEBUG レベルも表示）
- ✅ WARNING/ERROR: **変更なし**（常に表示）

---

## 8. 関連ドキュメント

- [LIVE_BUTTON_IMPLEMENTATION_V3.md](LIVE_BUTTON_IMPLEMENTATION_V3.md) - LIVE判定ボタン実装の詳細
- [LIVE_BUTTON_CACHE_UPDATE.md](LIVE_BUTTON_CACHE_UPDATE.md) - キャッシュ更新処理の仕様
- [DEBUG_DRY_RUN_GUIDE.md](docs/Technical/DEBUG_DRY_RUN_GUIDE.md) - ログ出力とデバッグ機能

---

**修正完了日**: 2026-01-03
**テスト状況**: ✅ 実装済み、テスト待機中
