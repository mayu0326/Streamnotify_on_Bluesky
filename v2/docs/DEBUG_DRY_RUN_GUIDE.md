# DEBUG ログとドライラン機能 ガイド

**バージョン**: v2.1.0
**実装日**: 2025年12月17日
**ステータス**: ✅ 完全実装・テスト済み

---

## 📋 目次

1. [DEBUG ログの制御](#1-debug-ログの制御)
2. [DRY RUN（ドライラン）機能](#2-dry-runドライラン機能)
3. [使用例](#3-使用例)
4. [トラブルシューティング](#4-トラブルシューティング)

---

## 1. DEBUG ログの制御

### ✅ DEBUG ログ制御（v2.1.0 - 2025-12-17 実装）

**問題**（v2.1.0前）: `DEBUG_MODE=false` に設定しても、DEBUG レベルのログが出力されていた

**解決**（v2.1.0）: `logging_plugin.py` で DEBUG_MODE 設定に完全対応

### 設定方法

#### settings.env で制御

```env
# ✅ 本番環境：DEBUG ログを非表示
DEBUG_MODE=false

# 🔧 開発環境：詳細な DEBUG ログを表示
DEBUG_MODE=true
```

#### ロギングレベルの詳細制御

```env
# コンソール出力レベル（デフォルト: INFO）
LOG_LEVEL_CONSOLE=INFO

# ファイル出力レベル（デフォルト: DEBUG）
LOG_LEVEL_FILE=DEBUG

# 個別ロガーレベル（空の場合は LOG_LEVEL_FILE を使用）
LOG_LEVEL_APP=DEBUG
LOG_LEVEL_POST=DEBUG
LOG_LEVEL_AUDIT=INFO
LOG_LEVEL_THUMBNAILS=DEBUG
```

### DEBUG_MODE=false 時の動作

```
✅ DEBUG ログが非表示
✅ INFO ログのみ表示
✅ ファイルサイズ削減
✅ ログ検索が高速化
```

**出力例:**

```
2025-12-17 10:15:30,001 [INFO] アプリケーション起動
2025-12-17 10:15:30,050 [INFO] ✅ 投稿完了: video_id=Vnx9CUo
2025-12-17 10:15:31,100 [INFO] 設定読み込み完了
```

### DEBUG_MODE=true 時の動作

```
✅ DEBUG ログが表示される
✅ テンプレートレンダリング処理の詳細
✅ 画像リサイズの詳細情報
✅ Facet 構築の詳細情報
✅ ファイル操作ログ
```

**出力例:**

```
2025-12-17 10:15:30,001 [INFO] アプリケーション起動
2025-12-17 10:15:30,050 [DEBUG] 設定読み込み: YOUTUBE_CHANNEL_ID=UCxxxxxx
2025-12-17 10:15:30,051 [DEBUG] 📐 AspectRatio を設定: 1200×627
2025-12-17 10:15:30,100 [DEBUG] 🔄 パターン1（横長）: 3:2に統一+中央トリミング
2025-12-17 10:15:30,150 [INFO] ✅ 投稿完了: video_id=Vnx9CUo
2025-12-17 10:15:31,100 [DEBUG] DB から動画 10 件を取得しました
```

### 実装ファイル

| ファイル | 実装内容 | 行数 |
|---------|--------|------|
| `plugins/logging_plugin.py` | DEBUG_MODE 対応、フィルター実装 | 120-330 |

### ロギングプラグインの構成

```python
# logging_plugin.py での実装
debug_mode = os.getenv("DEBUG_MODE", "false").lower() in ("true", "1", "yes")

# DEBUG_MODE に応じてログレベルを設定
if not debug_mode and LOG_LEVEL_FILE == "DEBUG":
    LOG_LEVEL_FILE = "INFO"

# フィルター: DEBUG_MODE=false 時は DEBUG ログをフィルタリング
class DebugAndInfoFilter(logging.Filter):
    def filter(self, record):
        if not debug_mode and record.levelno == logging.DEBUG:
            return False
        return record.levelno in (logging.DEBUG, logging.INFO)
```

---

## 2. DRY RUN（ドライラン）機能

### ✅ DRY RUN 機能（v2.1.0 - 2025-12-17 実装）

**用途**: 投稿前にテンプレート・リサイズ設定・リンクカード設定などを確認

### 使用方法

#### 方法1: GUI から実行（推奨）

**手順:**
1. メイン画面で投稿対象の動画を選択（☑️ をクリック）
2. 「📤 投稿設定」ボタンをクリック
3. 投稿設定ウィンドウが表示される
4. **「🧪 投稿テスト」ボタン** をクリック
5. 処理完了「🧪 投稿テスト完了」メッセージ表示
6. **DB は更新されない**（再試行可能）

**メリット:**
- GUI で直感的に操作可能
- 投稿方法（画像 vs リンクカード）を確認できる
- 画像プレビューで最終確認できる
- テスト投稿後も選択状態が残る（再試行可能）

#### 方法2: settings.env で実行

**設定:**
```env
APP_MODE=dry_run
```

**動作:**
- メインループで投稿処理を実行（投稿対象が DB で selected=true）
- 画像リサイズ・Facet 構築は通常通り実行
- Blob アップロード・API 呼び出しはスキップ
- ログに投稿内容が記録される

### DRY RUN での処理フロー

```
ユーザーが「🧪 投稿テスト」 をクリック
    ↓
PostSettingsWindow._execute_post(dry_run=True)
    ↓
plugin_manager.post_video_with_all_enabled(video, dry_run=True)
    ↓
各プラグインに dry_run=True を設定
    ├─ bluesky_plugin.set_dry_run(True)
    └─ bluesky_v2.set_dry_run(True)
    ↓
テキスト構築（通常通り）
    ↓
Facet 構築（通常通り）
    ↓
画像リサイズ（通常通り）
    ↓
画像品質最適化（通常通り）
    ↓
Blob アップロード（★ ダミーデータで代替）
    ↓
API.createRecord（★ スキップ）
    ↓
DB 更新（★ スキップ）
    ↓
ログ記録（通常通り）
    ↓
🧪 投稿テスト完了
```

### DRY RUN 実行時の確認項目

#### 1. テキスト形式の確認

**ログを確認:**
```
投稿テキスト: 【Twitch同時配信】新着動画です...
URL: https://youtube.com/watch?v=xxxxx
Facet: [富] 0-65 (リンク化)
```

**確認項目:**
- ✅ テキストが正確か
- ✅ 日本語が正しいか
- ✅ URL がリンク化されているか

#### 2. 画像形式の確認

**ロギング出力:**
```
📏 元画像: 1280×720 (JPEG, 132.1KB, アスペクト比: 1.78)
🔄 パターン1（横長）: 3:2に統一+中央トリミング
   リサイズ後: 1200×627
   JPEG品質90: 140.6KB
✅ 画像リサイズ完了
```

**確認項目:**
- ✅ リサイズ後のサイズが適切か
- ✅ ファイルサイズが 1MB 以下か
- ✅ アスペクト比が正確か

#### 3. 投稿方法の確認

**GUI 投稿設定ウィンドウで表示:**
```
投稿方法: 画像 + テキスト（AspectRatio付き）
```

**確認項目:**
- ✅ 画像を添付して投稿されるか
- ✅ URLがテキストに含まれているか
- ✅ リンクカードと画像の重複がないか

### DRY RUN 実行時のログ

**成功ケース:**
```
2025-12-17 10:15:30,001 [INFO] 🧪 Bluesky プラグイン DRY RUN モード: True
2025-12-17 10:15:30,050 [INFO] 🧪 [DRY RUN] 画像アップロード（スキップ）: /path/to/image.jpg
2025-12-17 10:15:30,100 [INFO] 🧪 [DRY RUN] 投稿をシミュレート
2025-12-17 10:15:30,101 [INFO] 投稿テキスト: 【Twitch同時配信】新着動画です...
2025-12-17 10:15:30,102 [INFO] 🧪 投稿テスト完了
```

**エラーケース:**
```
2025-12-17 10:15:30,001 [ERROR] ❌ テンプレートレンダリング失敗
2025-12-17 10:15:30,002 [ERROR] 投稿テキストが生成できません
2025-12-17 10:15:30,003 [ERROR] 🧪 投稿テスト失敗
```

### 実装ファイル

| ファイル | 実装内容 | 行数 |
|---------|--------|------|
| `plugin_manager.py` | dry_run パラメータ追加 | 220-240 |
| `plugins/bluesky_plugin.py` | set_dry_run() メソッド | 446-451 |
| `bluesky_v2.py` | set_dry_run() メソッド、ダミーデータ | 60-62, 215-235 |
| `gui_v2.py` | 投稿設定ウィンドウで dry_run 対応 | 1263-1330 |

---

## 3. 使用例

### 例1: 投稿テンプレートの動作確認

**手順:**
1. GUI で動画を選択
2. 「📤 投稿設定」をクリック
3. 「🧪 投稿テスト」をクリック
4. ログで投稿テキストを確認
5. 問題があれば テンプレート修正
6. 問題なければ 「✅ 投稿」で本投稿

**確認項目:**
- ✅ 動画タイトルが正確に含まれているか
- ✅ 日時形式が正確か
- ✅ URL がテキストに含まれているか

### 例2: 画像リサイズ動作の確認

**手順:**
1. GUI で画像付き動画を選択
2. 「📤 投稿設定」をクリック
3. 画像プレビューでサムネイル確認
4. 「🧪 投稿テスト」をクリック
5. ログで画像リサイズ情報を確認

**ログ確認例:**
```
📏 元画像: 1920×1440 (JPEG, 2.1MB)
🔄 パターン1（横長）: 3:2統一
   リサイズ後: 1280×800
   品質90: 950.5KB
⚠️  900KB超過
   品質85: 850.2KB ✅
✅ 画像リサイズ完了
```

### 例3: DEBUG ログで詳細情報を確認

**settings.env:**
```env
DEBUG_MODE=true
```

**実行:**
```bash
python main_v2.py
```

**ログ出力:**
```
[DEBUG] 設定読み込み: DEBUG_MODE=true
[DEBUG] 🔄 パターン1（横長）: 3:2に統一+中央トリミング
[DEBUG] リサイズ後: 1200×627
[DEBUG] JPEG品質90: 140.6KB
[DEBUG] AspectRatio を設定: 1200×627
[INFO] ✅ 投稿完了
```

---

## 4. トラブルシューティング

### Q: DRY RUN しても DB が更新されてしまう

**A:** 以下の点を確認してください:

1. **GUI の投稿設定ウィンドウを使用しているか確認**
   - ❌ CLI から直接実行
   - ✅ GUI の「🧪 投稿テスト」ボタン

2. **ボタンを間違えていないか確認**
   - ❌ 「✅ 投稿」ボタン（本投稿）
   - ✅ 「🧪 投稿テスト」ボタン（DRY RUN）

3. **ログで dry_run フラグを確認**
   ```
   ✅ [DRY RUN] 投稿をシミュレート ← DRY RUN 成功
   ✅ 投稿完了 ← 本投稿（DB更新）
   ```

### Q: DEBUG ログが表示されない

**A:** DEBUG_MODE の設定を確認してください:

**確認1: settings.env を確認**
```bash
grep DEBUG_MODE settings.env
```

**結果が以下ならば OK:**
```
DEBUG_MODE=true
```

**確認2: ロギングレベルを確認**
```env
LOG_LEVEL_FILE=DEBUG     # ファイル出力（デフォルト: DEBUG）
LOG_LEVEL_CONSOLE=DEBUG  # コンソール出力（デフォルト: INFO）
```

**コンソールにも DEBUG を出力する場合:**
```env
LOG_LEVEL_CONSOLE=DEBUG
```

**確認3: ログファイルを確認**
```bash
tail -f logs/app.log
```

**確認4: Python キャッシュをクリア**
```bash
Get-ChildItem -Recurse -Filter "*.pyc" -Force | Remove-Item -Force
Get-ChildItem -Recurse -Filter "__pycache__" -Force | Remove-Item -Force -Recurse
```

### Q: 投稿テストで「テキストが生成できません」エラー

**A:** テンプレートレンダリング失敗です:

1. **ログで詳細を確認**
```
ERROR   ❌ テンプレートレンダリング失敗
ERROR   KeyError: 'template_field_name'
```

2. **テンプレートファイルを確認**
```bash
cat templates/bluesky_post_template.txt
```

3. **動画 DB を確認**
```bash
python -c "from database import Database; db = Database(); print(db.get_video_by_id('video_id'))"
```

4. **テンプレート変数が存在するか確認**
   - ✅ `{title}` が動画 DB に存在する
   - ✅ `{url}` が正確な形式
   - ✅ `{published_at}` が ISO 8601 形式

### Q: 画像リサイズが失敗する

**A:** 画像ファイルを確認してください:

1. **ログでエラーを確認**
```
ERROR   ❌ ファイルサイズの最適化に失敗しました（1MB超過）
WARNING ⚠️  画像リサイズ失敗のため、この投稿では画像添付をスキップします
```

2. **画像ファイルのサイズを確認**
```bash
ls -lh path/to/image.jpg
```

3. **品質段階を下げる**
```python
# plugins/bluesky_plugin.py の品質段階を変更
quality_levels = [70, 60, 50, 40]  # より積極的に低下
```

4. **リサイズターゲットを下げる**
```python
IMAGE_RESIZE_TARGET_WIDTH = 1024
IMAGE_RESIZE_TARGET_HEIGHT = 576
```

---

## 📚 関連ドキュメント

- [BLUESKY_PLUGIN_GUIDE.md](./BLUESKY_PLUGIN_GUIDE.md#4-dry-run投稿テスト機能) - DRY RUN 機能の詳細
- [BLUESKY_PLUGIN_GUIDE.md](./BLUESKY_PLUGIN_GUIDE.md#5-gui投稿設定ウィンドウ) - GUI 投稿設定ウィンドウ
- [IMAGE_RESIZE_IMPLEMENTATION.md](./IMAGE_RESIZE_IMPLEMENTATION.md) - 画像リサイズ詳細
- [PLUGIN_MANAGER_INTEGRATION_v2.md](./PLUGIN_MANAGER_INTEGRATION_v2.md) - プラグイン統合

---

## ✅ テスト実績

| テスト項目 | 状態 |
|---------|------|
| DEBUG_MODE=false で DEBUG ログが非表示 | ✅ 成功 |
| DEBUG_MODE=true で DEBUG ログが表示 | ✅ 成功 |
| GUI 投稿テストで DB が更新されない | ✅ 成功 |
| DRY RUN でダミー Blob が返される | ✅ 成功 |
| テスト投稿後も選択状態が残る | ✅ 成功 |
| 本投稿で DB が正常に更新される | ✅ 成功 |

---

**作成日時:** 2025年12月17日
**ステータス:** 完全実装 ✅
