# YouTube重複排除設定ガイド

**ステータス**: ✅ 実装完了（v3.4.1）
**最終更新**: 2026-01-03

---

## 概要

YouTube 動画の重複排除機能は、**複数のレベルで実装されています**：

1. **RSS ポーリング時の重複排除** (実装済み ✅ v3.4.1)
   - video_id + タイトル + live_status + チャンネル名 が完全に同じ場合のみ除外
   - `YOUTUBE_DEDUP_ENABLED` 設定で制御可能

2. **WebSub/Webhook データ到着時の重複排除** (実装済み ✅ v3.4.1)
   - video_id + タイトル + live_status + チャンネル名 が完全に同じ場合のみ除外
   - `YOUTUBE_DEDUP_ENABLED` 設定で制御可能

3. **重複投稿防止** (`PREVENT_DUPLICATE_POSTS`) (実装済み ✅)
   - 同じ動画の再投稿を防止（DB 側で管理）

## 設定方法

### settings.env での設定

```env
# YouTube重複排除オプション（true/false、デフォルト: true）
# ✅ v3.4.1 で実装完了：config.py で読み込み・処理済み
YOUTUBE_DEDUP_ENABLED=true
```

### 設定値の説明

| 値 | 動作 | 用途 |
|:--|:--|:--|
| **true**（デフォルト） | video_id + タイトル + live_status + チャンネル名 が完全に同じ場合のみ除外 | 本番運用（推奨） |
| **false** | すべての動画が登録される（重複排除無効） | テスト・デバッグ |

## 有効（true）の場合の動作

video_id + タイトル + live_status + チャンネル名 が**完全に同じ場合のみ**重複と判定して除外します。

### 重複判定条件

以下の **4つすべてが同じ** 場合に除外：

1. **video_id**: YouTube の動画ID
2. **title**: 動画タイトル
3. **live_status**: ライブ配信状態（`none` / `upcoming` / `live` / `completed`）
4. **channel_name**: チャンネル名

### 重複と判定されないケース（すべて登録される）

| ケース | 理由 |
|:--|:--|
| 同じ video_id、異なる live_status | 異なるイベント状態（LIVE → completed など） |
| 同じタイトル、異なる video_id | 別の動画 |
| 同じタイトル、異なるチャンネル | 別のチャンネル |
| タイトルのみ同じ | 他の3つが異なれば別として登録 |

### メリット

- ✅ **実質的に重複がない**: 4つすべてが同じ確率はほぼゼロ
- ✅ **安全**: 異なる状態の動画は全部登録される
- ✅ **シンプル**: 判定基準が明確で理解しやすい

### 具体例（v3.4.1 実装完了）

RSS または WebSub API から 4 つのビデオが取得されたとき：

| Video ID | タイトル | live_status | チャンネル名 | 4つが同じ？ | 結果 |
|:--|:--|:--|:--|:--|:--|
| `jVB-Pv4IZJo` | 【まゆにゃあ生放送】アプリ実装確認枠 | completed | MyChannel | ✅ 同じ | ⏭️ 排除（1件目以降は除外） |
| `jVB-Pv4IZJo` | 【まゆにゃあ生放送】アプリ実装確認枠 | completed | MyChannel | ✅ 同じ | ⏭️ 排除（完全一致） |
| `58S5Pzux9BI` | 【まゆにゃあ生放送】アプリ実装確認枠 | live | MyChannel | ❌ 異なる | ✅ 登録 |
| `EttkV6rR8ic` | 【ゲーム】新作確認 | none | MyChannel | ❌ 異なる | ✅ 登録 |

**結果**: **3 本の動画が DB に登録される**

**実装状況**:
- ✅ video_id + タイトル + live_status + チャンネル名 での重複判定 (v3.4.1)
- ✅ RSS フロー での重複排除実装 (v3.4.1)
- ✅ WebSub フロー での重複排除実装 (v3.4.1)
- ✅ `YOUTUBE_DEDUP_ENABLED` による制御 (v3.4.1)

## 無効（false）の場合の動作

すべての動画が登録されます。重複排除チェックはスキップされます。

### 具体例（v3.4.1 実装完了）

| Video ID | タイトル | live_status | チャンネル名 | 4つが同じ？ | 結果 |
|:--|:--|:--|:--|:--|:--|
| `jVB-Pv4IZJo` | 【まゆにゃあ生放送】アプリ実装確認枠 | completed | MyChannel | ✅ 同じ | ✅ 登録（重複排除無効） |
| `jVB-Pv4IZJo` | 【まゆにゃあ生放送】アプリ実装確認枠 | completed | MyChannel | ✅ 同じ | ✅ 登録（重複排除無効） |
| `58S5Pzux9BI` | 【まゆにゃあ生放送】アプリ実装確認枠 | live | MyChannel | ❌ 異なる | ✅ 登録 |
| `EttkV6rR8ic` | 【ゲーム】新作確認 | none | MyChannel | ❌ 異なる | ✅ 登録 |

**結果**: **4 本の動画すべてが DB に登録される**

## 使い分け

### 本番運用（推奨: true、✅ v3.4.1 実装完了）

- 同じコンテンツの重複登録を防止
- RSS/WebSub から重複データが来ても自動で管理
- ユーザー体験の向上
- **ステータス**: ✅ `YOUTUBE_DEDUP_ENABLED=true` で完全に機能

### テスト・デバッグ（false、✅ v3.4.1 実装完了）

- すべてのビデオを登録したい場合
- 重複排除ロジックの検証を外したい場合
- 一時的なテストランの際
- **ステータス**: ✅ `YOUTUBE_DEDUP_ENABLED=false` で重複排除を無効化できます

---

## 現在の実装状況（v3.4.1）

### ✅ 実装済み

1. **RSS ポーリング時の重複排除** (v3.4.1 ✅)
   - `youtube_core/youtube_rss.py` の `save_to_db()` メソッドで実装
   - video_id + タイトル + live_status + チャンネル名 での完全一致判定
   - `YOUTUBE_DEDUP_ENABLED` で制御可能

2. **WebSub/Webhook フロー での重複排除** (v3.4.1 ✅)
   - `youtube_core/youtube_websub.py` の `save_to_db()` メソッドで実装
   - video_id + タイトル + live_status + チャンネル名 での完全一致判定
   - `YOUTUBE_DEDUP_ENABLED` で制御可能

3. **Config への環境変数統合** (v3.4.1 ✅)
   - `config.py` に `youtube_dedup_enabled` プロパティを実装
   - `YOUTUBE_DEDUP_ENABLED` を読み込み・バリデーション
   - 起動時に INFO レベルでログ出力

4. **重複投稿防止** (`PREVENT_DUPLICATE_POSTS`) (v3.1.0 ✅)
   - DB 側で `posted_to_bluesky` フラグで管理
   - 同じ動画の再投稿を防止

5. **手動追加時の重複排除スキップ** (`skip_dedup` パラメータ) (v3.3.0 ✅)
   - GUI から手動追加する動画は重複チェックを回避
   - 優先度に関わらず強制登録
   - 使用箇所: `gui_v3.py` の各種手動追加機能

## 関連設定

### 1. YouTube重複排除 (`YOUTUBE_DEDUP_ENABLED`)
- **範囲**: RSS/Webhook データ取得時
- **対象**: video_id + タイトル + live_status + チャンネル名 が完全に同じ動画
- **動作**: 4属性完全一致判定で重複除外
- **状態**: ✅ 実装完了（v3.4.1）

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

## ログ出力例（v3.4.1 実装完了）

### RSS ポーリング時：重複を検知した場合

```
[INFO] 🔄 YouTube RSS フィードを取得しています...
[INFO] 📊 RSS 取得件数: 15件
[DEBUG] 🎬 動画：{{ video_id }} - {{ title }}
[DEBUG] ℹ️ published_at: 2025-12-20T10:00:00Z
[DEBUG] ℹ️ channel_name: MyChannel
[DEBUG] ℹ️ content_type: video
[DEBUG] 重複検知ロジック実行中...
[DEBUG] グループキー作成: ('dQw4w9WgXcQ', 'Python 最新機能', 'none', 'MyChannel')
[DEBUG] グループサイズ: 1件 (重複なし)
[DEBUG] 📊 重複検知（完全一致）: video_id=dQw4w9WgXcQ, title=Python 最新機能, live_status=none, channel=MyChannel → 3件中1件を使用
[DEBUG] 他の重複エントリはスキップされました
[INFO] ✅ 1件の動画を DB に保存しました
```

### WebSub/Webhook 受信時：重複を検知した場合

```
[INFO] 📬 WebSub イベント受信
[INFO] 🔄 WebSub フィードを処理しています...
[DEBUG] グループキー作成: ('E4z8jyiYh9E', 'YouTube Live 配信', 'upcoming', 'YourChannel')
[DEBUG] グループサイズ: 2件 (重複あり)
[DEBUG] 📊 重複検知（完全一致）: video_id=E4z8jyiYh9E, title=YouTube Live 配信, live_status=upcoming, channel=YourChannel → 2件中1件を使用
[DEBUG] 他の重複エントリはスキップされました
[INFO] ✅ 1件の動画を DB に保存しました
```

### YOUTUBE_DEDUP_ENABLED=false の場合：すべて登録

```
[INFO] ℹ️ YouTube 重複排除が無効化されています
[INFO] 📊 収集件数: 15件（重複排除なし、すべて登録されます）
[DEBUG] 🎬 保存: video_id=dQw4w9WgXcQ → DB に登録
[DEBUG] 🎬 保存: video_id=dQw4w9WgXcQ → DB に登録（重複ですが登録）
[INFO] ✅ 15件の動画を DB に保存しました
```

---

## トラブルシューティング（v3.4.1 実装完了版）

### Q1: 重複する動画が DB に登録されている

**A**: 以下を確認してください：

1. **YOUTUBE_DEDUP_ENABLED を確認**
   - `settings.env` で `YOUTUBE_DEDUP_ENABLED=true` になっているか確認
   - 起動時のログに "ℹ️ YouTube 重複排除が有効化されています" と出ているか確認

2. **重複の条件を再確認**
   - 重複判定は以下 **4つの属性すべてが一致** した場合のみ
     - `video_id`: 動画ID
     - `title`: 動画タイトル
     - `live_status`: ライブ配信状態（"none", "upcoming", "live", "completed"）
     - `channel_name`: チャンネル名
   - これらのいずれか 1 つでも異なれば、別の動画として登録されます

3. **手動追加の確認**
   - GUI から手動追加した動画か確認
   - 手動追加時は重複チェックをスキップするため、重複が登録される可能性があります
   - 目的の動作であれば問題ありません

4. **ログで確認**
   - `logs/app.log` で "📊 重複検知（完全一致）" というメッセージを検索
   - "〇件中1件を使用" と表示されていれば、重複排除は正常に機能しています

### Q2: 同じ動画が複数登録されている

**A**: これは以下の条件下では正常な動作です：

1. **タイトルが異なる場合**
   ```
   ❌ 重複判定されない例
   | video_id | title | live_status | channel |
   | --------- | ----- | ----------- | ------- |
   | abc123 | "Python 最新機能" | none | MyChannel |
   | abc123 | "Python 最新機能 Part2" | none | MyChannel |
   → タイトルが異なるため、別の動画として登録されます
   ```

2. **live_status が異なる場合**
   ```
   ❌ 重複判定されない例
   | video_id | title | live_status | channel |
   | --------- | ----- | ----------- | ------- |
   | E4z8jyiYh9E | "YouTube Live 配信" | upcoming | MyChannel |
   | E4z8jyiYh9E | "YouTube Live 配信" | live | MyChannel |
   → live_status が異なるため、別の動画として登録されます
   ```

3. **チャンネル名が異なる場合**
   ```
   ❌ 重複判定されない例
   | video_id | title | live_status | channel |
   | --------- | ----- | ----------- | ------- |
   | abc123 | "Python 最新機能" | none | MyChannel |
   | abc123 | "Python 最新機能" | none | OtherChannel |
   → チャンネル名が異なるため、別の動画として登録されます
   ```

これらの場合は正常な動作です。重複排除は **完全一致** のみを対象としているため、意図した動作です。

### Q3: `YOUTUBE_DEDUP_ENABLED=false` に設定したが、重複が登録されない

**A**: これは正常な動作です。以下をご確認ください：

1. **既存動画の UNIQUE 制約は残る**
   - `YOUTUBE_DEDUP_ENABLED=false` は、4属性グループによる重複排除のみを無効化
   - DB 層の `UNIQUE (video_id)` 制約は常に有効
   - 同じ `video_id` は自動的に登録スキップされます

2. **そのため以下の動作になります**
   - `video_id` が同じ → 登録スキップ（DB の UNIQUE 制約）
   - 4属性の組み合わせが異なる → 登録される（グループ重複排除が無効なため）
   - ただし `video_id` が同じため、実質的には 1 件のみ登録される

### Q4: ログに重複検知メッセージが出ない

**A**: 以下の理由が考えられます：

1. **実際に重複がない**
   - RSS/WebSub から受け取った動画に重複がない場合、メッセージは出ません
   - これは正常な動作です

2. **ログレベルが INFO 以上に設定されていない**
   - `LOG_LEVEL_YOUTUBE=DEBUG` に設定して、詳細ログを有効化
   - `settings.env` で確認してください

3. **重複排除が無効化されている**
   - `YOUTUBE_DEDUP_ENABLED=false` になっていないか確認
   - 無効の場合、グループ重複排除メッセージは出ません

---

## 実装チェックリスト（v3.4.1 完了）

✅ すべての実装が完了しました：

- [x] `config.py` に `self.youtube_dedup_enabled` プロパティを追加 (v3.4.1)
- [x] `settings.env.example` の説明を実装状況に合わせて更新 (v3.4.1)
- [x] `youtube_core/youtube_rss.py` に重複排除フィルタリング機能を追加 (v3.4.1)
- [x] `youtube_core/youtube_websub.py` に重複排除フィルタリング機能を追加 (v3.4.1)
- [x] `YOUTUBE_DEDUP_ENABLED` で RSS/WebSub フロー の重複排除を制御 (v3.4.1)
- [x] ログ出力を実装（重複検知時の詳細ログ） (v3.4.1)

## 実装の詳細

### RSS フロー (`youtube_core/youtube_rss.py`)
- Lines 143-181: 重複排除ロジック実装
- グループキー: `(video_id, title, "none", channel_name)`
- 重複検知時のログ出力あり

### WebSub フロー (`youtube_core/youtube_websub.py`)
- Lines 283-325: 重複排除ロジック実装
- グループキー: `(video_id, title, live_status, channel_name)`
- 重複検知時のログ出力あり

### Config 統合 (`config.py`)
- Lines 146-151: `youtube_dedup_enabled` プロパティ実装
- 環境変数 `YOUTUBE_DEDUP_ENABLED` を読み込み
- デフォルト: `True`

---

## 関連ファイル

- [config.py](../../config.py) - `youtube_dedup_enabled` プロパティ
- [youtube_rss.py](../../../youtube_core/youtube_rss.py) - RSS 重複排除実装
- [youtube_websub.py](../../../youtube_core/youtube_websub.py) - WebSub 重複排除実装
- [settings.env.example](../../../settings.env.example) - 設定ファイルサンプル

---

**最終更新**: 2026-01-03
**対象版**: v3.4.1 （2026-01-03 現在）
**ステータス**: ✅ 実装完了・本番運用中
