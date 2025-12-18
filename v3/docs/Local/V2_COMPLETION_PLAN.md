# v3 完了計画 - YouTubeLive プラグイン完成

**策定日**: 2025-12-18
**対象バージョン**: v3.3.0

---

## 📋 v3 完了の定義

**YouTubeLive プラグインの完成をもって v3 完了とする**

### 完了条件

以下の2つの機能が実装され、テスト済みであること：

1. ✅ **ライブ開始/終了の自動検知** - **✅ 完了・テスト済み (2025-12-18)**
   - RSS または API ポーリングでライブ開始を検知 ✅
   - API 定期ポーリングでライブ終了を検知 ✅
   - DB の `live_status` を自動更新 ✅

2. ✅ **ライブイベント用テンプレート自動適用** - **✅ 完了・テスト済み (2025-12-18)**
   - `yt_online_template.txt`: ライブ開始時 ✅
   - `yt_offline_template.txt`: ライブ終了時 ✅
   - イベント種別に応じて自動選択 ✅

### リリース予定

- **バージョン**: v3.3.0
- **リリース日**: 2025-12-18 ✅ **実装完了・全テストパス**

---

## 🔄 v3 への繰り下げ機能

以下の機能は v3 では実装せず、v3 で実装予定：

### 3. 一括投稿スケジュール機能
- 複数動画の分散投稿（15分間隔など）
- Bluesky API レート制限対策
- **実装予定**: v3

### 4. GUI 機能拡張
- 動画フィルタ・検索機能
- 統計詳細表示
- クイック投稿テンプレート
- メモリ効率向上（遅延画像読み込み）
- **実装予定**: v3

### 5. バックアップ・復元機能
- DB・テンプレート・設定の一括エクスポート/インポート
- ZIP形式での圧縮保存
- API キー除外オプション
- **実装予定**: v3

### その他（v3予定）
- RSS 手動更新ボタン
- 重複投稿防止オプション
- 投稿テンプレート動的変数（`{{ current_date }}`など）

---

## 📦 実装計画

### Phase 1: ライブ開始検知（最優先）

**実装ファイル**:
- `v3/youtube_rss.py`: RSS 監視強化
- `v3/plugins/youtube_live_plugin.py`: 自動投稿ロジック

**主要機能**:
```python
# RSS で新着動画を検知 → API で詳細確認 → ライブ判定 → 自動投稿
def fetch_youtube_rss_with_live_check(channel_id, api_plugin):
    videos = fetch_youtube_rss(channel_id)
    for video in videos:
        details = api_plugin._fetch_video_detail(video["video_id"])
        if details:
            content_type, live_status, _ = classify(details)
            if live_status == "live":
                auto_post_live_start(video)
```

### Phase 2: ライブ終了検知

**実装ファイル**:
- `v3/plugins/youtube_live_plugin.py`: 定期ポーリング機能
- `v3/main_v3.py`: スケジューリング統合

**主要機能**:
```python
# DB から live_status='live' の動画を取得 → API で状態確認 → 終了検知 → 自動投稿
def poll_live_status():
    live_videos = db.get_videos_by_live_status("live")
    for video in live_videos:
        details = api_plugin._fetch_video_detail(video_id)
        if is_completed(details):
            db.update_video_status(video_id, "archive", "completed")
            auto_post_live_end(video)
```

**ポーリング間隔**:
- デフォルト: 5分
- 設定可能: `YOUTUBE_LIVE_POLL_INTERVAL` (分単位)

### Phase 3: テンプレート統合

**既存ファイル（配置済み）**:
- `Asset/templates/youtube/yt_online_template.txt`: ライブ開始テンプレート ✅ 配置済み
- `Asset/templates/youtube/yt_offline_template.txt`: ライブ終了テンプレート ✅ 配置済み
- `templates/youtube/yt_online_template.txt`: 実行時テンプレート ✅ 配置済み
- `templates/youtube/yt_offline_template.txt`: 実行時テンプレート ✅ 配置済み

**テンプレート選択ロジック**:
```python
def _select_template(video, event_type):
    template_map = {
        "live_start": "templates/youtube/yt_online_template.txt",
        "live_end": "templates/youtube/yt_offline_template.txt",
        "new_video": "templates/youtube/yt_new_video_template.txt",
    }
    return template_map.get(event_type, default_template)
```

---

## 🧪 テスト計画

### 単体テスト

```python
# test_scripts/test_youtube_live_detection.py

def test_live_start_detection():
    """ライブ開始検知のテスト"""
    # RSS で新着検知 → API で live_status="live" → DB 保存 → 自動投稿

def test_live_end_detection():
    """ライブ終了検知のテスト"""
    # DB に live_status="live" → API で "completed" → DB 更新 → 自動投稿

def test_template_selection():
    """テンプレート自動選択のテスト"""
    # イベント種別 → 正しいテンプレートが選択される
```

### 統合テスト

```python
# test_scripts/test_youtube_live_integration.py

def test_full_live_workflow():
    """ライブ配信の完全ワークフロー"""
    # 1. ライブ予定検知
    # 2. ライブ開始検知 → yt_online_template で投稿
    # 3. ライブ終了検知 → yt_offline_template で投稿
    # 4. アーカイブ化確認
```

---

## 📄 ドキュメント更新

### 更新ファイル

- [x] `v3/docs/References/FUTURE_ROADMAP_v3.md`
  - Phase 2: YouTubeLive プラグイン完成を明記
  - Phase 3: v3 繰り下げ機能を追加

- [x] ✅ `v3/settings.env.example` - **2025-12-18 完了**
  - 環境変数を追加：
    - `YOUTUBE_LIVE_POLL_INTERVAL` ✅
    - `YOUTUBE_LIVE_AUTO_POST_START` ✅
    - `YOUTUBE_LIVE_AUTO_POST_END` ✅

- [x] ✅ `v3/docs/local/YOUTUBE_LIVE_PLUGIN_TESTING_COMPLETE.md` - **2025-12-18 完了**
  - テスト完了報告書

- [ ] `README.md` - 🔜 次フェーズ
  - YouTubeLive 対応を追記

- [ ] `v3/docs/README_GITHUB_v3.md` - 🔜 次フェーズ
  - YouTubeLive 対応を追記

- [ ] `v3/docs/Technical/PLUGIN_SYSTEM.md` - 🔜 次フェーズ
  - YouTubeLive プラグイン仕様を追加

### 新規ドキュメント

- [x] `v3/docs/Technical/YOUTUBE_LIVE_PLUGIN_IMPLEMENTATION.md`
  - 実装ガイド（詳細版）

---

## 📊 実装完了度

| 機能 | 状態 | 完了予定 |
|:--|:--:|:--|
| **YouTubeLive プラグイン** | ✅ **完了** | ✅ **2025-12-18** |
| ├─ ライブ開始検知 | ✅ 実装完了・テスト済み | v3.3.0 |
| ├─ ライブ終了検知 | ✅ 実装完了・テスト済み | v3.3.0 |
| └─ テンプレート自動適用 | ✅ 実装完了・テスト済み | v3.3.0 |
| **一括投稿スケジュール** | ❌ v3繰り下げ | v3 |
| **GUI 機能拡張** | ❌ v3繰り下げ | v3 |
| **バックアップ・復元** | ❌ v3繰り下げ | v3 |

---

## 🎯 実装チェックリスト

### コード実装

- [x] ✅ RSS 監視強化（`youtube_rss.py`）
  - `fetch_youtube_rss_with_live_check()` メソッドの実装
- [x] ✅ ライブ開始検知（`youtube_live_plugin.py`）
  - `auto_post_live_start(video)` メソッドの実装 - **2025-12-18 完了**
- [x] ✅ ライブ終了検知（定期ポーリング）
  - `poll_live_status()` メソッドの実装 - **2025-12-18 完了**
  - `auto_post_live_end(video)` メソッドの実装 - **2025-12-18 完了**
- [x] ✅ テンプレート自動選択ロジック
  - `bluesky_plugin.py::post_video()` に `live_status` 分岐を追加 - **2025-12-18 完了**
- [x] ✅ 自動投稿ロジック統合
  - main_v3.py に定期ポーリングスレッドを追加 - **2025-12-18 完了**
- [x] ✅ 環境変数追加（`settings.env.example`）
  - `YOUTUBE_LIVE_POLL_INTERVAL` - **2025-12-18 完了**
  - `YOUTUBE_LIVE_AUTO_POST_START` - **2025-12-18 完了**
  - `YOUTUBE_LIVE_AUTO_POST_END` - **2025-12-18 完了**
- [x] ✅ DB クエリヘルパー追加（`database.py`）
  - `get_videos_by_live_status(status)` メソッドの実装 - **2025-12-18 完了**

### テンプレート

- [x] `Asset/templates/youtube/yt_online_template.txt` 作成（配置済み）
- [x] `Asset/templates/youtube/yt_offline_template.txt` 作成（配置済み）
- [x] ✅ テンプレート自動選択ロジックの実装（`bluesky_plugin.py`）- **2025-12-18 完了**

### テスト

- [x] ✅ 単体テスト実装 - **test_youtube_live_detection.py (12/12 pass)**
- [x] ✅ 統合テスト実装 - **test_youtube_live_integration.py (10/10 pass)**
- [ ] 実環境テスト（実際のライブ配信で検証）- 🔜 次フェーズ

### ドキュメント

- [ ] README.md 更新
- [ ] README_GITHUB_v3.md 更新
- [ ] PLUGIN_SYSTEM.md 更新
- [ ] settings.env.example 更新

### リリース

- [ ] バージョン番号更新（v3.3.0）- 🔜 次フェーズ
- [ ] リリースノート作成 - 🔜 次フェーズ
- [ ] Git タグ作成 - 🔜 次フェーズ
- [ ] GitHub Release 公開 - 🔜 次フェーズ

---

## 📝 変更履歴

| 日付 | 内容 |
|:--|:--|
| 2025-12-18 | YouTubeLive プラグイン実装完了・全テストパス（22/22）|
| 2025-12-18 | テスト完了報告書作成、v3 完了状態確定 |
| 2025-12-18 | v3 繰り下げ機能整理 |

---

## ✅ v3 完了状態

**ステータス**: 🎉 **YouTubeLive プラグイン完全実装・テスト完了**

- ✅ コード実装: 7/7 完了
- ✅ テンプレート: 2/2 配置
- ✅ テスト: 22/22 パス（単体 12、統合 10）
- ✅ 環境変数: 3/3 設定
- ✅ ドキュメント: テスト報告書完成
- 🔜 次フェーズ: 実環境テスト、最終ドキュメント整備

**次回アクション**: 実環境テスト（実際のライブ配信で検証）と最終ドキュメント更新

