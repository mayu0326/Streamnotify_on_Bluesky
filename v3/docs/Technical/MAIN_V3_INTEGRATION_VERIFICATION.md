# main_v3.py ⟷ YouTubeLivePlugin v0.3.0 統合検証ガイド

**検証日**: 2025-12-26
**バージョン**: v0.3.0
**ステータス**: ✅ 統合完了・検証済み

---

## 1. 統合検証チェックリスト

### ✅ チェック #1: プラグイン初期化フロー

**実装場所**: [main_v3.py](../../main_v3.py#L199-L212)

```python
# YouTubeLive 検出プラグインを手動でロード・有効化
try:
    plugin_manager.load_plugin("youtube_live_plugin", os.path.join("plugins", "youtube_live_plugin.py"))
    asset_manager.deploy_plugin_assets("youtube_live_plugin")

    # ★ YouTube Live プラグインに依存を注入（自動投稿用）
    live_plugin = plugin_manager.get_plugin("youtube_live_plugin")
    if live_plugin:
        live_plugin.set_plugin_manager(plugin_manager)
        live_plugin.set_config(config)  # ★ 新: config も注入

    # ★ 注入完了後に有効化（on_enable() が呼ばれる）
    plugin_manager.enable_plugin("youtube_live_plugin")
```

**検証項目**:
- ✅ ロード → アセット配置 → 依存注入 → 有効化の順序が正しい
- ✅ `set_plugin_manager(plugin_manager)` が呼ばれている
- ✅ `set_config(config)` が呼ばれている（新規）
- ✅ `enable_plugin()` が最後に実行され、`on_enable()` トリガーされる

**期待される動作**:
- YouTubeLivePlugin v0.3.0 の `on_enable()` が一度だけ実行される
- AutoPoster と Poller が plugin_manager と config を参照可能になる
- 自動投稿判定ロジックが初期化される

---

### ✅ チェック #2: 定期ポーリングスレッド（poll_live_status）

**実装場所**: [main_v3.py](../../main_v3.py#L341-L354)

```python
live_plugin = plugin_manager.get_plugin("youtube_live_plugin")
if live_plugin and live_plugin.is_available():
    logger.info(f"🔄 YouTubeLive ポーリング実行...（現在の間隔: {current_interval} 分）")

    try:
        # ★ Issue #2 修正: 両メソッドを呼び出す
        live_plugin.poll_live_status()
        live_plugin.process_ended_cache_entries()
```

**検証項目**:
- ✅ `poll_live_status()` が呼ばれている
- ✅ `process_ended_cache_entries()` が呼ばれている（新規）

**期待される動作**:
1. `poll_live_status()` → YouTubeLivePoller が API をポーリング
2. `process_ended_cache_entries()` → Poller が ended_cache を処理
3. AutoPoster が completed 動画を検出して自動投稿判定

---

### ✅ チェック #3: 動的ポーリング間隔制御

**実装場所**: [main_v3.py](../../main_v3.py#L308-L370)

```python
# 動的ポーリング間隔の取得（仕様 v1.0 セクション 5）
poll_interval_active = int(os.getenv("YOUTUBE_LIVE_POLL_INTERVAL_ACTIVE", "5"))
poll_interval_completed = int(os.getenv("YOUTUBE_LIVE_POLL_INTERVAL_COMPLETED", "15"))
poll_interval_no_live = int(os.getenv("YOUTUBE_LIVE_POLL_INTERVAL_NO_LIVE", "30"))

# バリデーション：有効範囲 5～60分
```

**変更内容**:
| 項目 | 旧 | 新 |
|:--|:--|:--|
| ポーリング間隔タイプ | 単一（固定） | 3種類（動的） |
| 環境変数 | `YOUTUBE_LIVE_POLL_INTERVAL` | `POLL_INTERVAL_ACTIVE/COMPLETED/NO_LIVE` |
| 最小値 | 15分 | 5分（仕様に準拠） |
| 動的制御 | なし | キャッシュ状態に応じて自動選択 |

**仕様 v1.0 セクション 5 への準拠**:
- ✅ LIVE 配信中: POLL_INTERVAL_ACTIVE（推奨5分）
- ✅ 配信完了直後: POLL_INTERVAL_COMPLETED（推奨15分）
- ✅ LIVE なし: POLL_INTERVAL_NO_LIVE（推奨30分、省リソース）

---

### ✅ チェック #4: 直接依存の排除

**検証方法**: github では YouTubeLivePoller, Store, Classifier, AutoPoster の直接インスタンス化を検索

```bash
grep -n "YouTubeLivePoller\|YouTubeLiveStore\|YouTubeLiveClassifier\|YouTubeLiveAutoPoster" v3/main_v3.py
```

**結果**: ❌ マッチなし（直接依存なし）

**確認内容**:
- ✅ YouTubeLivePoller を直接インスタンス化していない
- ✅ YouTubeLiveStore を直接インスタンス化していない
- ✅ YouTubeLiveClassifier を直接インスタンス化していない
- ✅ YouTubeLiveAutoPoster を直接インスタンス化していない
- ✅ すべて YouTubeLivePlugin の内部実装として扱われている

**期待される動作**: 4層モジュールは YouTubeLivePlugin 内部で管理され、外部からは統合ハブ経由でのみアクセス可能

---

## 2. 修正サマリー

### Issue #1: config が依存注入されていない ❌ → ✅ 固定

**問題**:
```python
live_plugin.set_plugin_manager(plugin_manager)
# ← config が注入されていない
plugin_manager.enable_plugin("youtube_live_plugin")
```

**解決**:
```python
live_plugin.set_plugin_manager(plugin_manager)
live_plugin.set_config(config)  # ★ 追加
plugin_manager.enable_plugin("youtube_live_plugin")
```

**影響**:
- AutoPoster が operation_mode を参照できるようになった
- Poller が auto-post フラグを参照できるようになった

---

### Issue #2: process_ended_cache_entries() が呼ばれていない ❌ → ✅ 固定

**問題**:
```python
live_plugin.poll_live_status()
# ← process_ended_cache_entries() が呼ばれていない
last_poll_time = current_time
```

**解決**:
```python
live_plugin.poll_live_status()
live_plugin.process_ended_cache_entries()  # ★ 追加
last_poll_time = current_time
```

**影響**:
- Poller が ended_cache の処理を実行
- AutoPoster が completed 動画を検出可能に
- ライブ終了後の自動投稿が機能するようになった

---

### Issue #3: ポーリング間隔が仕様と不一致 ⚠️ → ✅ 固定

**問題**:
```python
poll_interval_minutes = int(os.getenv("YOUTUBE_LIVE_POLL_INTERVAL", "15"))
# 固定値、最小15分では LIVE 終了検知が遅い
```

**解決**:
```python
poll_interval_active = int(os.getenv("YOUTUBE_LIVE_POLL_INTERVAL_ACTIVE", "5"))
poll_interval_completed = int(os.getenv("YOUTUBE_LIVE_POLL_INTERVAL_COMPLETED", "15"))
poll_interval_no_live = int(os.getenv("YOUTUBE_LIVE_POLL_INTERVAL_NO_LIVE", "30"))

# キャッシュ状態に応じて動的に選択
```

**影響**:
- LIVE 配信中は 5分間隔で素早く終了を検知
- 配信完了後は 15分間隔でアーカイブ化を検知
- LIVE がない場合は 30分間隔で省リソース化
- 仕様 v1.0 セクション 5 に完全準拠

---

## 3. 環境変数の更新

### settings.env.example への反映

```env
# 旧（削除）
# YOUTUBE_LIVE_POLL_INTERVAL=15

# 新（追加）
# YouTube Live ポーリング間隔（動的制御、仕様 v1.0 セクション 5）

# LIVE 配信中のポーリング間隔（分単位、デフォルト: 5）
YOUTUBE_LIVE_POLL_INTERVAL_ACTIVE=5

# LIVE 完了後のポーリング間隔（分単位、デフォルト: 15）
YOUTUBE_LIVE_POLL_INTERVAL_COMPLETED=15

# LIVE なし時のポーリング間隔（分単位、デフォルト: 30）
YOUTUBE_LIVE_POLL_INTERVAL_NO_LIVE=30
```

---

## 4. テスト手順

### 単体テスト

```bash
cd v3

# YouTubeLive プラグインのテスト
python -m pytest tests/test_youtube_live_plugin.py -v

# 統合テスト
python -m pytest tests/test_integration_main_v3.py::test_youtube_live_plugin_integration -v
```

### 統合テスト（手動）

```bash
# 1. settings.env を確認
#    - YOUTUBE_LIVE_AUTO_POST_MODE=all または live
#    - YOUTUBE_LIVE_POLL_INTERVAL_ACTIVE=5
#    - YOUTUBE_API_KEY が設定されている

# 2. アプリケーション起動
python main_v3.py

# 3. ログ確認
tail -f logs/app.log | grep YouTubeLive

# 期待されるログ出力:
# ✅ YouTubeLive 動的ポーリングを開始します（アクティブ: 5分、...）
# ✅ YouTubeLive ポーリング実行...（現在の間隔: 5 分）
# ✅ YouTubeLive ポーリング完了（polling + processing）
```

### 動的ポーリング間隔の検証

```bash
# キャッシュ監視スクリプト
python v3/utils/cache/view_youtube_live_cache.py

# 期待される動作:
# 1. LIVE キャッシュあり → 5分間隔
# 2. Completed キャッシュあり → 15分間隔
# 3. LIVE キャッシュなし → 30分間隔
```

---

## 5. 互換性確認

### YouTubeLivePlugin v0.3.0 との完全互換

| インターフェース | main_v3.py での使用 | 仕様準拠 |
|:--|:--|:--|
| `on_enable()` | ✅ enable_plugin() で自動呼び出し | ✅ v0.3.0 |
| `set_plugin_manager()` | ✅ 呼ばれている | ✅ v0.3.0 |
| `set_config()` | ✅ 呼ばれている | ✅ v0.3.0 |
| `is_available()` | ✅ 呼ばれている | ✅ v0.3.0 |
| `poll_live_status()` | ✅ 呼ばれている | ✅ v0.3.0 |
| `process_ended_cache_entries()` | ✅ 呼ばれている | ✅ v0.3.0 |
| `post_video()` | ✅ GUI から呼ばれる | ✅ v0.3.0 |

---

## 6. 既知の制限

### アーキテクチャの制限

1. **プラグインの複数インスタンス化**
   - YouTubeLivePlugin は singleton として実装されている（複数チャンネル監視不可）
   - 将来の複数チャンネル対応時には PluginManager 側の修正が必要

2. **動的ポーリング間隔の細粒度制御**
   - 3段階の間隔のみ対応（ACTIVE/COMPLETED/NO_LIVE）
   - より細かい制御（例: 配信残り時間に応じた調整）は将来実装予定

3. **キャッシュ状態の可視化**
   - ポーリング間隔選択のロジックは内部実装に依存
   - キャッシュ内容の詳細は admin CLI や debugger で確認推奨

---

## 7. 今後の拡張計画

| 機能 | ステータス | 優先度 |
|:--|:--|:--|
| YouTubeLive 終了イベントの Webhook 通知 | 🔜 将来実装 | 中 |
| 複数チャンネルの YouTube Live 監視 | 🔜 将来実装 | 低 |
| ポーリング間隔の AI ベース最適化 | 🔜 将来実装 | 低 |

---

## 8. トラブルシューティング

### Q: YouTubeLive ポーリングが実行されない

**A**: 以下を確認してください：

1. `YOUTUBE_LIVE_AUTO_POST_MODE=all` または `live` か確認
2. `YOUTUBE_API_KEY` が設定されているか確認
3. `logs/app.log` で YouTube Live プラグイン初期化エラーを確認
4. `YouTubeLive 動的ポーリングを開始します` というログが出ているか確認

### Q: ポーリング間隔が変わらない

**A**: キャッシュ状態をチェック：

```bash
python v3/utils/cache/view_youtube_live_cache.py
```

- キャッシュが空の場合: 30分間隔（設計通り）
- キャッシュに upcoming/live がある場合: 5分間隔でなければバグ
- キャッシュに completed がある場合: 15分間隔でなければバグ

### Q: process_ended_cache_entries() が呼ばれている形跡がない

**A**: ログレベルを DEBUG に上げて確認：

```python
# settings.env
DEBUG_MODE=true
LOG_LEVEL_YOUTUBE=DEBUG
```

```bash
grep -i "processing\|ended_cache\|process_ended" logs/app.log
```

期待されるログ:
```
🔄 YouTubeLive ポーリング実行...
✅ YouTubeLive ポーリング完了（polling + processing）
```

---

## 関連ドキュメント

- [YouTubeLivePlugin Complete Specification v0.3.0](YOUTUBE_LIVE_PLUGIN_COMPLETE_SPECIFICATION.md)
- [4層アーキテクチャ設計](YOUTUBE_LIVE_PLUGIN_COMPLETE_SPECIFICATION.md#1-4層モジュール構造)
- [YouTubeLive ポーリング仕様 v1.0](YOUTUBE_LIVE_PLUGIN_COMPLETE_SPECIFICATION.md#仕様-v10)

---

**作成日**: 2025-12-26
**最後の修正**: 2025-12-26
**ステータス**: ✅ 検証完了
