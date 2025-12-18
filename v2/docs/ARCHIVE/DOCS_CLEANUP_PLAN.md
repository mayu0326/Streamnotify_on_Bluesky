# ドキュメント整理計画

**作成日**: 2025-12-18
**対象**: v2/docs フォルダ

---

## 📊 分析結果

### 完了したプロジェクト

#### ✅ YouTube Live 判定ロジック
- **ファイル**: `Local/youtube_live_classification_plan.md`（448行）
- **ステータス**: 完全実装完了
- **実装箇所**:
  - v2/plugins/youtube_api_plugin.py（System 1-7）
  - v2/gui_v2.py（Type 列追加）
  - v2/database.py（classification_type, broadcast_status カラム）
- **アクション**: ✅ **アーカイブ推奨**

#### ✅ テンプレートシステム統合
- **ファイル**: `Guides/TEMPLATE_IMPLEMENTATION_CHECKLIST.md`（345行）
- **ステータス**: 完全実装完了
- **実装箇所**: v2/templates/, v2/template_*.py
- **アクション**: ✅ **アーカイブ推奨**

#### ✅ YouTube API キャッシング
- **ファイル**: `Local/YOUTUBE_API_CACHING_IMPLEMENTATION.md`（？行）
- **ステータス**: 完全実装完了
- **実装箇所**: v2/plugins/youtube_api_plugin.py
- **アクション**: ✅ **アーカイブ推奨**

---

## ⚠️ 重複・古いドキュメント

### 設計仕様書の重複
| ファイル | 行数 | 内容 | 推奨アクション |
|---------|------|------|--------------|
| `Technical/v2 設計仕様書.md` | 330 | 古い仕様（バニラ状態） | 削除 |
| `Technical/v2_design.md` | 295 | メモ形式 | 削除 |
| `Technical/v2_DESIGN_POLICY_UPDATED.md` | 298 | ポリシー説明 | 削除 |
| `Technical/ARCHITECTURE_AND_DESIGN.md` | 244 | 最新アーキ | **保持** |

**結論**: `ARCHITECTURE_AND_DESIGN.md` に統一し、他は削除

### 実装完了のドキュメント

| ファイル | ステータス | アクション |
|---------|----------|-----------|
| `Guides/IMPLEMENTATION_PLAN.md` | 計画（実装完了） | 削除 |
| `Guides/IMAGE_RESIZE_GUIDE.md` | 完了 | アーカイブ |
| `Guides/IMAGE_RESIZE_IMPLEMENTATION.md` | 完了 | 削除 |
| `Guides/DEBUG_DRY_RUN_GUIDE.md` | 完了 | アーカイブ |

---

## 📁 推奨フォルダ構造

```
v2/docs/
├── README_GITHUB_v2.md          ← 統合 README
├── ARCHIVE/                     ← 完了済みプロジェクト
│   ├── youtube_live_classification_plan.md
│   ├── YOUTUBE_API_CACHING_IMPLEMENTATION.md
│   ├── TEMPLATE_IMPLEMENTATION_CHECKLIST.md
│   ├── IMAGE_RESIZE_GUIDE.md
│   └── DEBUG_DRY_RUN_GUIDE.md
├── Technical/
│   ├── ARCHITECTURE_AND_DESIGN.md       ← メインドキュメント
│   ├── PLUGIN_SYSTEM.md
│   ├── TEMPLATE_SYSTEM.md
│   ├── RICHTEXT_FACET_SPECIFICATION.md
│   ├── ASSET_MANAGER_INTEGRATION_v2.md
│   ├── DELETED_VIDEO_CACHE.md
│   ├── DEVELOPMENT_GUIDELINES.md
│   ├── SETTINGS_OVERVIEW.md
│   ├── VERSION_MANAGEMENT.md
│   ├── ModuleList_v2.md
│   └── [削除] v2 設計仕様書.md
│   └── [削除] v2_design.md
│   └── [削除] v2_DESIGN_POLICY_UPDATED.md
├── Guides/
│   ├── SESSION_REPORTS.md               ← 進捗記録
│   ├── DEVELOPMENT_GUIDELINES.md
│   └── [削除] IMPLEMENTATION_PLAN.md
│   └── [削除] IMAGE_RESIZE_IMPLEMENTATION.md
└── References/
    ├── FUTURE_ROADMAP_v2.md
    ├── YouTube新着動画app（初期構想案）.md
    └── 投稿テンプレートの引数.md
```

---

## 🎯 実施アクション

### 削除すべきファイル（古い / 重複）
1. `Technical/v2 設計仕様書.md`
2. `Technical/v2_design.md`
3. `Technical/v2_DESIGN_POLICY_UPDATED.md`
4. `Guides/IMPLEMENTATION_PLAN.md`
5. `Guides/IMAGE_RESIZE_IMPLEMENTATION.md`

### アーカイブすべきファイル（完了済み）
1. `Local/youtube_live_classification_plan.md`
2. `Local/YOUTUBE_API_CACHING_IMPLEMENTATION.md`
3. `Guides/TEMPLATE_IMPLEMENTATION_CHECKLIST.md`
4. `Guides/IMAGE_RESIZE_GUIDE.md`
5. `Guides/DEBUG_DRY_RUN_GUIDE.md`

### 保持・継続更新すべきファイル
1. `README_GITHUB_v2.md`
2. `Technical/ARCHITECTURE_AND_DESIGN.md`
3. `Technical/PLUGIN_SYSTEM.md`
4. `Technical/TEMPLATE_SYSTEM.md`
5. `Technical/RICHTEXT_FACET_SPECIFICATION.md`
6. `Guides/SESSION_REPORTS.md`
7. `References/FUTURE_ROADMAP_v2.md`

---

## 📝 整理完了の判定基準

- [ ] ARCHIVE フォルダを作成
- [ ] 完了済みドキュメントを ARCHIVE に移動
- [ ] 重複ドキュメントを削除
- [ ] README_GITHUB_v2.md で構成を明確化
- [ ] 残存ドキュメントの更新日を確認
