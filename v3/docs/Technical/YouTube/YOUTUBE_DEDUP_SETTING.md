# YouTube重複排除設定ガイド

**ステータス**: ⚠️ 実装中（v3.3.0 では部分実装）
**最終更新**: 2026-01-03

---

## 概要

YouTube 動画の重複排除機能は、**複数の異なるレベルで実装されています**：

1. **RSS ポーリング時の重複チェック** (実装済み ✅)
   - 同じ `video_id` の動画は自動的に登録スキップ
   - 設定不可（自動判定）

2. **WebSub/Webhook データ到着時の優先度ベース重複排除** (実装中 ⚠️)
   - `YOUTUBE_DEDUP_ENABLED` 設定で制御予定
   - 現在は部分実装（優先度ロジックのみ存在）

3. **重複投稿防止** (`PREVENT_DUPLICATE_POSTS`) (実装済み ✅)
   - 同じ動画の再投稿を防止（DB 側で管理）

## 設定方法（将来実装予定）

### settings.env での設定

```env
# YouTube重複排除オプション（true/false、デフォルト: true）
# ⚠️ 現在は settings.env.example に記載されていますが、
#    config.py でまだ読み込まれていません（v3.3.1+ で実装予定）
YOUTUBE_DEDUP_ENABLED=true
```

### 設定値の説明（仕様）

| 値 | 動作（予定） | 用途 |
|:--|:--|:--|
| **true**（デフォルト） | 同じタイトル+チャンネルの動画は優先度ベースで管理 | 本番運用（推奨） |
| **false** | すべての動画が登録される | テスト・デバッグ |

## 有効（true）の場合の動作（仕様）

同じタイトル + チャンネル名の動画が複数ある場合、優先度に基づいて保持すべき動画を特定します。

### 優先度（高→低、v3.3.0 実装済み）

1. **アーカイブ** (`content_type="archive"`, `live_status="completed"`) - 優先度: 4
2. **ライブ予約** (`content_type="schedule"`, `live_status="upcoming"`) - 優先度: 3
3. **ライブ配信中** (`content_type="live"`, `live_status="live"`) - 優先度: 3
4. **配信終了** (`content_type="completed"`, `live_status="completed"`) - 優先度: 2
5. **通常動画** (`content_type="video"`) - 優先度: 1

**プレミア公開の特殊扱い**:
- 配信予定（未来）: 優先度 3（ライブと同等）
- 配信中（開始から10分以内）: 優先度 3
- 配信終了（10分以上過去）: 優先度 1（通常動画と同等）

### 具体例（仕様、実装は v3.3.1+ 予定）

WebSub API から 4 つのビデオが取得されたとき（**現在は実装されていません**）：

| Video ID | タイトル | Content Type | Live Status | 優先度 | 結果（予定） |
|:--|:--|:--|:--|:--|:--|
| `jVB-Pv4IZJo` | 【まゆにゃあ生放送】アプリ実装確認枠 | archive | completed | 4 | ✅ 登録 |
| `UYoKsFZ4OJI` | 【まゆにゃあ生放送】アプリ実装確認枠 | archive | completed | 4 | ⏭️ 排除（同じ優先度） |
| `58S5Pzux9BI` | 【雑談】ゆめうさサイト... | live | live | 3 | ✅ 登録 |
| `EttkV6rR8ic` | 【まゆにゃあ生放送】アプリ実装確認枠 | video | none | 1 | ⏭️ 排除（優先度低） |

**結果**: **2～3 本の動画が DB に登録される**（仕様が完成した場合）

**現在の実装状況**:
- ✅ 優先度計算ロジック（`youtube_dedup_priority.py`）は実装済み
- ⚠️ 実際のデータ取得フロー（RSS/WebSub）への統合は未実装

## 無効（false）の場合の動作（仕様）

すべての動画が登録されます。重複排除チェックはスキップされます（**実装予定**）。

### 具体例（仕様、実装は v3.3.1+ 予定）

| Video ID | タイトル | 結果（予定） |
|:--|:--|:--|
| `jVB-Pv4IZJo` | 【まゆにゃあ生放送】アプリ実装確認枠 | ✅ 登録 |
| `UYoKsFZ4OJI` | 【まゆにゃあ生放送】アプリ実装確認枠 | ✅ 登録 |
| `58S5Pzux9BI` | 【雑談】ゆめうさサイト... | ✅ 登録 |
| `EttkV6rR8ic` | 【まゆにゃあ生放送】アプリ実装確認枠 | ✅ 登録 |

**結果**: **4 本の動画すべてが DB に登録される**（仕様が完成した場合）

## 使い分け

### 本番運用（推奨: true、将来実装予定）

- 同じコンテンツの重複登録を防止
- WebSub から重複データが来ても自動で管理
- ユーザー体験の向上
- **現在のステータス**: `YOUTUBE_DEDUP_ENABLED=true` でも実装がまだなため、実質的な変化なし

### テスト・デバッグ（false、将来実装予定）

- すべてのビデオを登録したい場合
- 重複排除ロジックの検証を外したい場合
- 一時的なテストランの際
- **現在のステータス**: `YOUTUBE_DEDUP_ENABLED=false` でも実装がまだなため、実質的な変化なし

---

## 現在の実装状況（v3.3.0）

### ✅ 実装済み

1. **RSS ポーリング時の `video_id` 重複チェック**
   - `database.insert_video()` で `UNIQUE` 制約により自動実装
   - 同じ `video_id` の動画は自動的に登録スキップ
   - 設定不可（常に有効）

2. **優先度計算ロジック** (`youtube_dedup_priority.py`)
   - `get_video_priority()`: 動画の優先度を計算（v3.3.0 ✅ 実装完了）
   - `should_keep_video()`: 新動画を登録すべきか判定
   - `select_best_video()`: 最優先動画を選択
   - **使用箇所**: 現在は未使用（統合待ち）

3. **重複投稿防止** (`PREVENT_DUPLICATE_POSTS`)
   - DB 側で `posted_to_bluesky` フラグで管理
   - 同じ動画の再投稿を防止（✅ v3.1.0 実装完了）

4. **手動追加時の重複排除スキップ** (`skip_dedup` パラメータ)
   - GUI から手動追加する動画は重複チェックを回避
   - 優先度に関わらず強制登録（✅ v3.3.0 実装完了）
   - 使用箇所: `gui_v3.py` の各種手動追加機能

### ⚠️ 実装中（v3.3.1+ で予定）

1. **config.py への環境変数読み込み**
   - `YOUTUBE_DEDUP_ENABLED` を config オブジェクトに追加
   - バリデーション・ログ出力

2. **WebSub/Webhook フロー への統合**
   - `youtube_core/youtube_websub.py` または RSS フロー で優先度ロジック呼び出し
   - Webhook 到着時の重複排除判定を実装
   - 設定値 `YOUTUBE_DEDUP_ENABLED` に基づいた動作切り替え

## 関連設定

### 1. YouTube重複排除 (`YOUTUBE_DEDUP_ENABLED`)
- **範囲**: RSS/Webhook データ取得時
- **対象**: 同一タイトル+チャンネルの複数動画
- **動作**: 優先度ベースで管理
- **状態**: ⚠️ 部分実装（優先度ロジックのみ）

### 2. 重複投稿防止 (`PREVENT_DUPLICATE_POSTS`)
- **範囲**: Bluesky 投稿時
- **対象**: 既に投稿済みの動画
- **動作**: 同じ動画の再投稿を防止
- **状態**: ✅ 実装完了（v3.1.0）

### 3. 手動追加時の重複排除回避
- **パラメータ**: `skip_dedup=True`
- **対象**: GUI からの手動追加
- **動作**: 優先度に関わらず強制登録
- **状態**: ✅ 実装完了（v3.3.0）

**注記**: これら 3 つの機能は独立して動作し、組み合わせて使用できます。

## ログ出力例

### 有効時（true、v3.3.1+ 予定）

```
🔄 YouTube WebSub フロー開始...

📊 同一コンテンツ検知: 【まゆにゃあ生放送】アプリ実装確認枠
  ├─ archive (priority=4): jVB-Pv4IZJo
  ├─ archive (priority=4): UYoKsFZ4OJI → ⏭️ 重複排除（同じ優先度）
  ├─ live (priority=3): 58S5Pzux9BI → ✅ 登録
  └─ video (priority=1): EttkV6rR8ic → ⏭️ 重複排除（優先度低）

✅ WebSub フロー完了: 2 個の動画を登録しました
```

### 無効時（false、v3.3.1+ 予定）

```
🔄 YouTube WebSub フロー開始...

📊 同一コンテンツ検知: 【まゆにゃあ生放送】アプリ実装確認枠
  ├─ archive (priority=4): jVB-Pv4IZJo → ✅ 登録
  ├─ archive (priority=4): UYoKsFZ4OJI → ✅ 登録
  ├─ live (priority=3): 58S5Pzux9BI → ✅ 登録
  └─ video (priority=1): EttkV6rR8ic → ✅ 登録

⚠️ 重複排除が無効のため、4 個の動画をすべて登録しました
```

### 現在の出力（実装前）

```
🔄 YouTube RSS フロー開始...
  ├─ video_id: xxxxxxx → ✅ 登録
  ├─ video_id: yyyyyyy → ✅ 登録
  ...

✅ RSS フロー完了
```

**注記**: WebSub フロー での重複排除は v3.3.1+ で実装予定のため、  \
現在はこのログが出力されません。

## トラブルシューティング

### Q: `YOUTUBE_DEDUP_ENABLED` を設定したが効果がない

**A**: 現在この機能は部分実装のため、設定しても効果がありません。

**原因**:
- ✅ `youtube_dedup_priority.py` の優先度計算ロジックは完成
- ⚠️ `config.py` が環境変数を読み込んでいない
- ⚠️ RSS/WebSub フロー での統合がまだ

**対応方法**:
- v3.3.1+ のリリースを待機してください
- または、GitHub Issues で実装要望を上げてください

### Q: Webhook から 4 本の動画が取得されたのに、すべて登録された

**A**: 重複排除機能がまだ実装されていないためです。

**原因**:
- RSS ポーリング時は `video_id` の UNIQUE 制約で自動的に重複チェック
- WebSub/Webhook フロー の優先度ベース重複排除はまだ未実装

**対応方法**:
- 一時的に RSS ポーリング（`YOUTUBE_FEED_MODE=poll`）を使用
- または、重複動画を手動で削除

### Q: 設定を変更したが反映されない

**A**: 設定が実装されていないため、変更は反映されません。

**対応方法**:
- v3.3.1+ の実装完了を待つ
- または、開発ブランチ（`feature/dedup-complete`）の利用を検討

---

## 実装チェックリスト（v3.3.1+ 向け）

実装が完了していない部分は以下の通りです：

- [ ] `config.py` に `self.youtube_dedup_enabled` プロパティを追加
- [ ] `settings.env.example` の説明を実装状況に合わせて更新
- [ ] `youtube_core/youtube_rss.py` に優先度フィルタリング機能を追加
- [ ] `youtube_core/youtube_websub.py` に優先度フィルタリング機能を追加
- [ ] `database.insert_video()` の `skip_dedup` パラメータと `YOUTUBE_DEDUP_ENABLED` を連動
- [ ] ログ出力を実装（優先度レベルでのフィルタリング結果）
- [ ] 単体テストを追加（`youtube_dedup_priority.py` の動作確認）
- [ ] 統合テストを追加（RSS/WebSub フロー での実運用確認）

---

**最終更新**: 2026-01-03
**対象版**: v3.3.0 （2026-01-03 現在）
