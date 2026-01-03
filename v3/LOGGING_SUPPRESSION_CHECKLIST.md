# LIVE判定ボタン - ログ出力修正の確認チェックリスト

**修正対象**: 過度なログ出力の抑制
**修正日**: 2026-01-03
**修正状況**: ✅ 完了

---

## 修正確認項目

### ✅ config.py 修正確認

- [x] 行107-109: `logger.info` → `logger.debug` (YouTube フィード取得モード)
- [x] 行120: `logger.info` → `logger.debug` (WebSub ポーリング間隔)
- [x] 行131: `logger.info` → `logger.debug` (RSS ポーリング間隔)
- [x] 行197-198: `logger.info` → `logger.debug` (ニコニコID設定)
- [x] 行200-201: `logger.info` → `logger.debug` (ニコニコ機能設定)
- [x] 行204: `logger.info` → `logger.debug` (ニコニコプラグイン未導入)

**確認済み行数**: 9箇所 → すべて logger.debug に統一

### ✅ gui_v3.py 修正確認

- [x] 一時的なログレベル抑制コード削除（setLevel/original_config_level）
- [x] classify_youtube_live_manually() メソッド簡潔化
- [x] DB 更新ログはそのまま INFO レベルで出力

---

## 期待される動作

### シナリオ 1: 通常モード（DEBUG_MODE=false）

**操作**: LIVE判定ボタンを押す

**app.log 出力イメージ**:
```
2026-01-03 10:16:44,764 [INFO] 🎬 7 件の Live 動画をキャッシュ更新・判定中...
2026-01-03 10:16:44,765 [INFO] ✅ 動画ステータス更新: lOJ-6AcfdOI (content_type=archive, live_status=None)
2026-01-03 10:16:44,766 [INFO] ✅ 動画ステータス更新: xxxx-xxxxx (content_type=live, live_status=live)
2026-01-03 10:16:44,800 [INFO] ✅ YouTube Live 判定完了: キャッシュ確認 7 件、API 更新 2 件、DB 更新 2 件
```

**期待**:
- ✅ DB 更新ログのみ表示される
- ❌ 不要な初期化ログ（有効なユーザーID、フィード取得モード等）は表示されない

### シナリオ 2: デバッグモード（DEBUG_MODE=true）

**操作**: LIVE判定ボタンを押す

**app.log 出力イメージ**:
```
2026-01-03 10:16:44,763 [DEBUG] 有効なユーザーIDが設定されています。
2026-01-03 10:16:44,763 [DEBUG] ニコニコ連携機能を有効化しました。
2026-01-03 10:16:44,763 [DEBUG] 📡 YouTube フィード取得モード: WebSub（Websubサーバー HTTP API 経由）
2026-01-03 10:16:44,763 [DEBUG] 📡 WebSub ポーリング間隔: 5 分
2026-01-03 10:16:44,764 [INFO] 🎬 7 件の Live 動画をキャッシュ更新・判定中...
2026-01-03 10:16:44,765 [DEBUG] 📡 API から取得（キャッシュ 45 分前）: lOJ-6AcfdOI
2026-01-03 10:16:44,765 [INFO] ✅ 動画ステータス更新: lOJ-6AcfdOI (content_type=archive, live_status=None)
2026-01-03 10:16:44,800 [INFO] ✅ YouTube Live 判定完了: キャッシュ確認 7 件、API 更新 2 件、DB 更新 2 件
```

**期待**:
- ✅ 初期化ログは DEBUG レベルで表示される
- ✅ キャッシュ操作の詳細ログも表示される
- ✅ DB 更新ログは INFO レベルで表示される

---

## テスト手順

### テスト実行前の準備

```bash
# v3 ディレクトリへ移動
cd v3

# settings.env を確認
cat settings.env

# YOUTUBE_API_KEY が設定されているか確認
grep "YOUTUBE_API_KEY=" settings.env
```

### テスト 1: 通常モードの検証

```bash
# DEBUG_MODE を確認（false でなければ変更）
# settings.env の以下の行を確認：
# DEBUG_MODE=false

# 古いログファイルを削除（新規テストため）
rm -f logs/app.log  # Linux/WSL
# または
del logs\app.log  # Windows

# アプリケーション起動
python main_v3.py

# GUI が起動したら：
# 1. 左パネルから LIVE 関連の動画を数個選択
# 2. 「LIVE判定」ボタンをクリック
# 3. "Live キャッシュ確認・更新を実行中..." ダイアログが出現
# 4. 処理完了メッセージが表示されるまで待機

# ログファイルを確認
tail -50 logs/app.log

# 確認事項：
# - ✅ "有効なユーザーID" ログが表示されていない
# - ✅ "YouTube フィード取得モード" ログが表示されていない
# - ✅ "ポーリング間隔" ログが表示されていない
# - ✅ "✅ 動画ステータス更新" ログが表示されている
# - ✅ "✅ YouTube Live 判定完了" ログが表示されている
```

### テスト 2: デバッグモードの検証

```bash
# settings.env を編集：
# DEBUG_MODE=true に変更

# 古いログファイルを削除
rm -f logs/app.log  # Linux/WSL
# または
del logs\app.log  # Windows

# アプリケーション再起動
python main_v3.py

# 前回と同じ操作を実施
# 1. 左パネルから LIVE 関連の動画を数個選択
# 2. 「LIVE判定」ボタンをクリック

# ログファイルを確認
tail -100 logs/app.log

# 確認事項：
# - ✅ [DEBUG] "有効なユーザーID" ログが表示されている
# - ✅ [DEBUG] "YouTube フィード取得モード" ログが表示されている
# - ✅ [DEBUG] "ポーリング間隔" ログが表示されている
# - ✅ [DEBUG] "API から取得" または "キャッシュから取得" ログが表示されている
# - ✅ [INFO] "✅ 動画ステータス更新" ログが表示されている
# - ✅ [INFO] "✅ YouTube Live 判定完了" ログが表示されている
```

---

## 修正内容の要約

### 変更ファイル

1. **v3/config.py**
   - 7 つのログ出力を `logger.info()` から `logger.debug()` に変更
   - システム初期化メッセージは DEBUG レベルが適切

2. **v3/gui_v3.py**
   - classify_youtube_live_manually() メソッドから一時的なログレベル抑制コードを削除
   - config.py の修正で不要になったため

### 修正の効果

| 項目 | 修正前 | 修正後 |
|:--|:--|:--|
| 通常モード時のログ行数 | 10+ | 3-4 |
| デバッグ情報の表示 | なし | DEBUG_MODE=true で表示 |
| DB 更新ログの明確性 | 低い（埋もれる） | 高い（目立つ） |

---

## トラブルシューティング

### Q: デバッグモードを有効にしても DEBUG ログが出ない

**A**: logger のコンフィグを確認：

```python
# logging_config.py を確認
# LOG_LEVEL_FILE が INFO になっていないか？
# logging.basicConfig(level=logging.DEBUG) が実行されているか？
```

### Q: "有効なユーザーID" ログが通常モードで出現する

**A**: 以下を確認：

```bash
# settings.env で DEBUG_MODE の値を確認
grep "^DEBUG_MODE=" settings.env

# python cache をクリア
rm -rf v3/__pycache__  # Linux/WSL
# または
rmdir v3\__pycache__  # Windows

# アプリケーション再起動
python main_v3.py
```

---

**確認日**: 2026-01-03
**確認状態**: ✅ 修正完了、テスト待機中
