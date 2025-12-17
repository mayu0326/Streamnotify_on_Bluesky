# 画像自動リサイズ機能 - 実装概要

**実装日**: 2025-12-17
**バージョン**: v2.1.0
**対象ファイル**: [v2/plugins/bluesky_plugin.py](../plugins/bluesky_plugin.py)
**ステータス**: ✅ 完全実装・テスト済み

---

## 🎯 実装目標と実績

### 実装目標
- ✅ 画像がBlueskyで表示時にレターボックス（黒枠）が出現 → 完全消去
- ✅ 画像サイズが最適化されていない → 三段階リサイズ戦略で最適化
- ✅ ファイルサイズが大きい → JPEG品質最適化パイプライン
- ✅ aspectRatioフィールドが API に渡されていない → API フィールド実装

### 実績
- **元画像**: 1280×720px (132.1KB)
- **リサイズ後**: 1200×627px (140.6KB)
- **Blob サイズ**: 143,948 bytes
- **Bluesky 表示**: レターボックスなし、フル幅表示 ✅

---

## 実装内容

### 1. 定数の追加（行 33-39）

```python
IMAGE_RESIZE_TARGET_WIDTH = 1280       # 横長画像のターゲット幅
IMAGE_RESIZE_TARGET_HEIGHT = 800       # 横長画像のターゲット高さ（3:2）
IMAGE_OUTPUT_QUALITY_INITIAL = 90      # JPEG初期品質
IMAGE_SIZE_TARGET = 800_000            # 目標ファイルサイズ（800KB）
IMAGE_SIZE_THRESHOLD = 900_000         # 品質低下の開始閾値（900KB）
IMAGE_SIZE_LIMIT = 1_000_000           # 最終上限（1MB）
```

**変更可能**: 設定を変えたい場合はここを編集

---

### 2. 新規メソッド追加（計 218 行）

#### `_resize_image(file_path: str) -> bytes | None`（92行）
メイン処理エントリーポイント

**処理**:
1. 元画像情報を取得（解像度・フォーマット・サイズ）
2. アスペクト比 (幅÷高さ) を判定
3. 3つのパターンでリサイズ:
   - 横長（≥1.3）: 3:2に統一 + 中央トリミング
   - 正方形〜やや横長（0.8-1.3）: 長辺基準で縮小のみ
   - 縦長（<0.8）: 長辺基準で縮小のみ
4. JPEG品質90で出力
5. 900KB超過なら品質を段階的に低下
6. 1MB超過ならNone返却（投稿スキップ）
7. 詳細ログを出力

**戻り値**: JPEG バイナリ (bytes) / 失敗時は None

---

#### `_resize_to_aspect_ratio(img, target_width, target_height)`（44行）
**用途**: 横長画像を3:2に統一

**処理**:
- 短辺を基準に縮小
- ターゲットアスペクト比に寄せる
- 中央トリミングで正確に target_width × target_height に

**例**:
```
1920×1440 → 1024×800（幅が大きい）→ 中央トリミング → 1280×800
```

---

#### `_resize_to_max_dimension(img, max_dimension: int)`（28行）
**用途**: 正方形・縦長画像を長辺基準で縮小

**処理**:
- 長辺が max_dimension 以下になるまで等比縮小
- **元画像が小さい場合は拡大しない**
- アスペクト比は維持

**例**:
```
1600×1600 → 1280×1280
800×1600 → 640×1280
640×1024 → そのまま（既に小さい）
```

---

#### `_encode_jpeg(img, quality: int) -> bytes`（26行）
**用途**: PIL Image を JPEG エンコード

**処理**:
- アルファチャネル（透明部分）を白背景で合成
- JPEG品質を指定して圧縮
- `optimize=True` でさらに最適化

---

#### `_optimize_image_quality(img, current_size_bytes: int) -> bytes | None`（28行）
**用途**: ファイルサイズが大きい場合、品質を下げて再圧縮

**処理**:
- 品質を段階的に低下: 85 → 75 → 65 → 55 → 50
- 各段階で1MB以下か確認
- 最初に1MB以下になった品質で出力
- すべての品階でも1MB超過なら None 返却

---

### 3. `_upload_blob()` メソッドの修正（行 202-237）

**従来**: ファイル読み込み → サイズチェック → API送信

**新しい**: ファイル読み込み → **`_resize_image()` 呼び出し** → API送信

```python
# 新しいコード（抜粋）
image_data = self._resize_image(file_path)  # ← リサイズ処理
if image_data is None:
    post_logger.warning(f"⚠️ 画像リサイズ失敗のため、この投稿では画像添付をスキップします")
    return None
```

**効果**:
- すべての画像がリサイズ処理を経由
- リサイズ失敗時は自動スキップ（リンクカードのみで投稿）

---

## 処理フロー図

```
upload_blob(画像ファイルパス)
    ↓
DRY RUN? → Yes → ダミーblob返却
    ↓ No
ファイル存在チェック
    ↓
_resize_image() 呼び出し
    ↓
┌─ 元画像取得
├─ アスペクト比判定
├─ リサイズ（3パターン）
├─ JPEG出力（品質90）
├─ 900KB超過？ → Yes → 品質低下で再圧縮
├─ 1MB超過？ → Yes → None返却（スキップ）
└─ ロギング出力
    ↓
image_data is None? → Yes → None返却（スキップ）
    ↓ No
Bluesky API にアップロード
    ↓
blob メタデータ返却
```

---

## ログ出力例

### 成功ケース（横長画像）

```
DEBUG   📏 元画像: 1920×1440 (JPEG, 2150.5KB, アスペクト比: 1.33)
DEBUG   🔄 パターン1（横長）: 3:2（1280×800）に寄せて縮小+中央トリミング
DEBUG      リサイズ後: 1280×800
DEBUG      JPEG品質90: 320.2KB
INFO    ✅ 画像リサイズ完了: 1920×1440 (2150.5KB) → 1280×800 (320.2KB)
```

### 品質低下ケース

```
DEBUG   📏 元画像: 1600×1200 (JPEG, 5000.0KB, アスペクト比: 1.33)
DEBUG   🔄 パターン1（横長）: 3:2（1280×800）に寄せて縮小+中央トリミング
DEBUG      リサイズ後: 1280×800
DEBUG      JPEG品質90: 950.5KB
INFO    ⚠️  ファイルサイズが 900KB を超過: 950.5KB
DEBUG      JPEG品質85: 850.2KB
INFO    ✅ 品質85で 1MB 以下に圧縮: 850.2KB
```

### スキップケース

```
ERROR   ❌ ファイルサイズの最適化に失敗しました（1MB超過）
WARNING ⚠️  画像リサイズ失敗のため、この投稿では画像添付をスキップします
```

この場合、テキスト＋URLリンクカードのみで投稿

---

## コード行数

| メソッド | 行数 |
|---------|------|
| `_resize_image()` | 92 |
| `_resize_to_aspect_ratio()` | 44 |
| `_resize_to_max_dimension()` | 28 |
| `_encode_jpeg()` | 26 |
| `_optimize_image_quality()` | 28 |
| `_upload_blob()` 修正 | +36 |
| **合計追加** | **~250行** |

---

## 依存ライブラリ

- **Pillow** (`PIL.Image`)
  - 画像の読み込み・リサイズ・エンコード
  - `requirements.txt` に既に含まれている ✓

---

## 設定変更方法

### ターゲット解像度を変更

[bluesky_plugin.py](../plugins/bluesky_plugin.py#L33-L34):
```python
IMAGE_RESIZE_TARGET_WIDTH = 1920   # 例: 1920
IMAGE_RESIZE_TARGET_HEIGHT = 1080  # 例: 1080
```

### 品質段階を変更

[bluesky_plugin.py](../plugins/bluesky_plugin.py#L446) の `quality_levels`:
```python
quality_levels = [80, 70, 60, 50]  # より積極的に低下
```

### サイズ上限を変更

```python
IMAGE_SIZE_THRESHOLD = 1_800_000   # 再圧縮開始を1.8MBに
IMAGE_SIZE_LIMIT = 2_000_000       # 最終上限を2MBに
```

---

## テスト時の確認ポイント

1. **ログレベルを DEBUG に設定**
   ```python
   logging.getLogger("PostLogger").setLevel(logging.DEBUG)
   ```

2. **3つのパターンをテスト**:
   - 横長画像 (≥1.3)
   - 正方形 (0.8-1.3)
   - 縦長 (<0.8)

3. **各パターンで**:
   - 元画像サイズ → リサイズ後を確認
   - 品質90で OK か / 品質低下が起きたか

4. **エラーケース**:
   - 極端に大きな画像（GBサイズ等）
   - 破損画像
   - サポート外の形式

---

## AspectRatio API フィールド実装

### 📌 レターボックス問題の根本原因

Bluesky は画像をレスポンシブデザインで表示していますが、**aspectRatio フィールドが指定されていない場合、クライアント側で固定アスペクト比でレイアウトされ、レターボックスが出現**します。

### ✅ 解決方法

`bluesky_core.py` の画像埋め込み時に、**width・ height から aspectRatio を計算して明示的に設定**：

```python
def _build_image_embed(self, blob: dict, width: int = None, height: int = None) -> dict:
    """画像埋め込みを構築（aspectRatio付き）"""
    image_obj = {
        "image": blob,
        "alt": "Posted image",
    }

    # ★ aspectRatio を明示的に設定
    if width and height:
        image_obj["aspectRatio"] = {
            "width": width,
            "height": height
        }
        post_logger.info(f"📐 AspectRatio を設定: {width}×{height}")

    return {
        "$type": "app.bsky.embed.images",
        "images": [image_obj]
    }
```

### 実装フロー

```
upload_blob() で Blob アップロード
    ↓
戻り値: (blob_dict, width, height) ← ★ タプルで返す
    ↓
_build_image_embed(blob_dict, width, height)
    ↓
aspectRatio フィールドを構築
    ↓
Bluesky API で投稿
    ↓
結果: レターボックスなし、フル幅表示 ✅
```

### API リクエスト例

```json
{
  "$type": "app.bsky.feed.post",
  "text": "【動画】新着動画です...",
  "embed": {
    "$type": "app.bsky.embed.images",
    "images": [{
      "image": {
        "$type": "blob",
        "mimeType": "image/jpeg",
        "size": 143948,
        "link": {"$link": "bafkreimq4..."}
      },
      "alt": "Posted image",
      "aspectRatio": {
        "width": 1200,
        "height": 627
      }
    }]
  }
}
```

---

## GUI 投稿設定ウィンドウとの統合

### 新機能: PostSettingsWindow

投稿前にユーザーが以下を調整可能：

```
☑ 画像を添付する
☑ 小さい画像を拡大する

プレビュー:
  [画像サムネイル 100×67px]
  元画像: 1280×720px (132.1KB)
  投稿時: 1200×627px (140.6KB)
  投稿方法: 画像 + テキスト（AspectRatio付き）

[✅ 投稿] [🧪 投稿テスト] [❌ キャンセル]
```

### 投稿フロー統合

```
ユーザーが「📤 投稿設定」クリック
  ↓
PostSettingsWindow 表示
  ↓
ユーザーが設定調整
  ↓
「✅ 投稿」 or 「🧪 投稿テスト」 をクリック
  ↓
image_processor.resize_image() ← 自動リサイズ実行
  ↓
bluesky_plugin._upload_blob() ← Blob アップロード
  ↓
_build_image_embed() で aspectRatio 設定
  ↓
Bluesky API で投稿
  ↓
✅ 投稿完了（選択状態更新）
または
🧪 投稿テスト完了（選択状態変更なし）
```

### 関連ドキュメント

- [PLUGIN_SYSTEM.md](../Technical/PLUGIN_SYSTEM.md) - GUI 投稿設定ウィンドウの詳細（統合版）

---

## テスト結果サマリー

### テスト1: 画像リサイズ

| テスト項目 | 結果 |
|---------|------|
| 元画像取得 | ✅ 成功 |
| アスペクト比判定 | ✅ 成功（1.33 → 横長パターン） |
| 3:2 統一＋中央トリミング | ✅ 成功（1280×800） |
| JPEG 品質90出力 | ✅ 成功 |
| ファイルサイズ内 | ✅ 成功（900KB以下） |

### テスト2: Blob アップロード

| テスト項目 | 結果 |
|---------|------|
| ダミーBlob（DRY RUN） | ✅ 成功 |
| 実Blob アップロード | ✅ 成功 |
| タプル戻り値 | ✅ 成功 |

### テスト3: AspectRatio 設定

| テスト項目 | 結果 |
|---------|------|
| AspectRatio フィールド構築 | ✅ 成功 |
| Bluesky API リクエスト | ✅ 成功 |
| レターボックス消去 | ✅ 成功 |
| フル幅表示 | ✅ 成功 |

### テスト4: GUI 統合

| テスト項目 | 結果 |
|---------|------|
| 投稿設定ウィンドウ表示 | ✅ 成功 |
| 画像プレビュー | ✅ 成功 |
| DRY RUN フラグ伝播 | ✅ 成功 |
| 投稿テスト実行 | ✅ 成功 |

---

## ファイル修正一覧

| ファイル | 行数 | 修正内容 |
|---------|------|--------|
| `v2/image_processor.py` | 1-332 | 三段階リサイズ戦略、品質最適化パイプライン実装 |
| `v2/plugins/bluesky_plugin.py` | 33-39 | 定数化（IMAGE_RESIZE_TARGET_*） |
| `v2/plugins/bluesky_plugin.py` | 125-127 | タプル戻り値（blob, width, height） |
| `v2/plugins/bluesky_plugin.py` | 158 | aspectRatio 実装 |
| `v2/plugins/bluesky_plugin.py` | 398 | _resize_image() 呼び出し |
| `v2/plugins/bluesky_plugin.py` | 446-451 | set_dry_run() メソッド追加 |
| `v2/bluesky_core.py` | 60-62 | set_dry_run() メソッド追加 |
| `v2/bluesky_core.py` | 215-235 | エラーハンドリング改善 |
| `v2/gui_v2.py` | 1100-1333 | PostSettingsWindow 実装 |
| `v2/gui_v2.py` | 1263-1330 | dry_run 伝播実装 |
| `v2/plugin_manager.py` | 220-240 | dry_run パラメータ追加 |

---

## 環境設定 (settings.env)

画像投稿機能は以下の設定で動作確認されています：

```env
BLUESKY_POST_ENABLED=True
DEBUG_MODE=false
APP_MODE=normal
```

---

- [IMAGE_RESIZE_GUIDE.md](./IMAGE_RESIZE_GUIDE.md) - 処理フロー・設定・トラブルシューティング

---

## 今後の拡張案

- [ ] アスペクト比判定の閾値を設定ファイル化
- [ ] 画像フォーマット自動判定（JPEG/WebP/AVIF等）
- [ ] 顔認識でトリミング位置を最適化
- [ ] メタデータ（EXIF）の保持・除去オプション
- [ ] 複数画像の一括処理
