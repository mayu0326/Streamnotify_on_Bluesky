# ドキュメント統合 - 削除対象リスト

**作成日**: 2025-12-18
**ステータス**: 削除前確認リスト

---

## 削除対象ドキュメント

### フェーズ1 統合済み（削除予定）

#### グループ1: テンプレート関連（11個中9個を削除）

これらは TEMPLATE_SYSTEM.md に統合済みです：

```
v2/docs/
  ❌ TEMPLATE_SPECIFICATION_v2.md (統合済み → 削除)
  ❌ TEMPLATE_INTEGRATION_v2.md (統合済み → 削除)
  ❌ TEMPLATE_USER_GUIDE.md (統合済み → 削除)
  ❌ TEMPLATE_SETTINGS_ENV.md (統合済み → 削除)
  ❌ TEMPLATE_SUMMARY.md (統合済み → 削除)
  ❌ TEMPLATE_PATH_RESOLUTION_ROOT_CAUSE.md (統合済み → 削除)
  ❌ BLUESKY_TEMPLATE_INTEGRATION_ANALYSIS.md (統合済み → 削除)
  ❌ BLUESKY_TEMPLATE_FIX_FINAL_REPORT.md (統合済み → 削除)
  ❌ TEMPLATE_VALIDATION_REPORT.md (統合済み → 削除)
  ✅ TEMPLATE_IMPLEMENTATION_CHECKLIST.md (維持：実装チェックリスト)
  ✅ TEMPLATE_SYSTEM.md (新規：統合版)
```

**削除コマンド**:

```bash
cd v2/docs
rm -f \
  TEMPLATE_SPECIFICATION_v2.md \
  TEMPLATE_INTEGRATION_v2.md \
  TEMPLATE_USER_GUIDE.md \
  TEMPLATE_SETTINGS_ENV.md \
  TEMPLATE_SUMMARY.md \
  TEMPLATE_PATH_RESOLUTION_ROOT_CAUSE.md \
  BLUESKY_TEMPLATE_INTEGRATION_ANALYSIS.md \
  BLUESKY_TEMPLATE_FIX_FINAL_REPORT.md \
  TEMPLATE_VALIDATION_REPORT.md
```

#### グループ2: キャッシュ関連（3個すべて削除）

これらは DELETED_VIDEO_CACHE.md に統合済みです：

```
v2/docs/
  ❌ DELETED_VIDEO_CACHE_DESIGN.md (統合済み → 削除)
  ❌ DELETED_VIDEO_CACHE_IMPLEMENTATION_REPORT.md (統合済み → 削除)
  ❌ DELETED_VIDEO_CACHE_INTEGRATION_TESTS.md (統合済み → 削除)
  ✅ DELETED_VIDEO_CACHE.md (新規：統合版)
```

**削除コマンド**:

```bash
cd v2/docs
rm -f \
  DELETED_VIDEO_CACHE_DESIGN.md \
  DELETED_VIDEO_CACHE_IMPLEMENTATION_REPORT.md \
  DELETED_VIDEO_CACHE_INTEGRATION_TESTS.md
```

#### グループ3: アーキテクチャ関連（3個削除、1個要確認）

これらは ARCHITECTURE_AND_DESIGN.md に統合済みです：

```
v2/docs/
  ❌ ARCHITECTURE_v2.md (統合済み → 削除)
  ❌ PLUGIN_ARCHITECTURE_v2.md (統合済み → 削除)
  ❌ v2_DESIGN_POLICY.md (統合済み → 削除)
  ⚠️ PLUGIN_MANAGER_INTEGRATION_v2.md (内容は統合済み → 削除予定)
  ⚠️ v2_DESIGN_POLICY_UPDATED.md (DESIGN_POLICY.md の更新版、要確認)
  ✅ ARCHITECTURE_AND_DESIGN.md (新規：統合版)
```

**削除コマンド**:

```bash
cd v2/docs
rm -f \
  ARCHITECTURE_v2.md \
  PLUGIN_ARCHITECTURE_v2.md \
  v2_DESIGN_POLICY.md \
  PLUGIN_MANAGER_INTEGRATION_v2.md
```

**要確認**:
- `v2_DESIGN_POLICY_UPDATED.md`: DESIGN_POLICY.md の更新版のため、内容を ARCHITECTURE_AND_DESIGN.md と比較してから判断

#### グループ4: プラグイン関連（2個削除予定）

これらは PLUGIN_SYSTEM.md に統合済みです：

```
v2/docs/
  ❌ BLUESKY_PLUGIN_GUIDE.md (統合済み → 削除)
  ❌ BLUESKY_PLUGIN_FALLBACK_FIXED_SETTINGS.md (統合済み → 削除)
  ✅ PLUGIN_SYSTEM.md (新規：統合版)
```

**削除コマンド**:

```bash
cd v2/docs
rm -f \
  BLUESKY_PLUGIN_GUIDE.md \
  BLUESKY_PLUGIN_FALLBACK_FIXED_SETTINGS.md
```

#### グループ5: セッションレポート関連（2個削除）

これらは SESSION_REPORTS.md に統合済みです：

```
v2/docs/
  ❌ SESSION_REPORT_20251217.md (統合済み → 削除)
  ❌ SESSION_REPORT_20251218.md (統合済み → 削除)
  ✅ SESSION_REPORTS.md (新規：統合版)
```

**削除コマンド**:

```bash
cd v2/docs
rm -f \
  SESSION_REPORT_20251217.md \
  SESSION_REPORT_20251218.md
```

---

## 削除対象外（維持するドキュメント）

以下のドキュメントは削除せず、参照更新のみを行います：

```
v2/docs/
  ✅ README_GITHUB_v2.md (参照更新済み)
  ✅ TEMPLATE_IMPLEMENTATION_CHECKLIST.md (独立ドキュメント)
  ✅ RICHTEXT_FACET_SPECIFICATION.md (新規・独立)
  ✅ VERSION_MANAGEMENT.md (バージョン管理)
  ✅ SETTINGS_OVERVIEW.md (設定ガイド)
  ✅ ModuleList_v2.md (モジュール一覧)
  ✅ DEBUG_DRY_RUN_GUIDE.md (トラブルシューティング)
  ✅ IMAGE_RESIZE_GUIDE.md (画像リサイズガイド)
  ✅ IMAGE_RESIZE_IMPLEMENTATION.md (実装ガイド)
  ✅ ASSET_MANAGER_INTEGRATION_v2.md (Asset管理)
  ✅ FUTURE_ROADMAP_v2.md (ロードマップ)
  ✅ IMPLEMENTATION_PLAN.md (実装計画)
  ✅ INTEGRATION_WORK_IN_PROGRESS.md (進捗レポート)
  ✅ DOCUMENTATION_CONSOLIDATION_COMPLETION_REPORT.md (統合レポート)
  ✅ DOCUMENTATION_OPTIMIZATION_ANALYSIS.md (分析ドキュメント)
  ✅ TEMPLATE_USAGE_ANALYSIS_20251218.md (分析ドキュメント)
  ✅ 投稿テンプレートの引数.md (参考資料)
  ✅ YouTube新着動画app（初期構想案）.md (参考資料)
  ✅ v2_design.md (参考資料)
  ✅ v2 設計仕様書.md (参考資料)
```

---

## 削除前確認チェックリスト

削除実施前に以下を確認してください：

### ✅ 参照検査

- [ ] README_GITHUB_v2.md の参照が全て更新されている
- [ ] 削除対象ドキュメント内の相互参照が削除対象でないか確認
- [ ] Python ファイル内のコメント参照が削除対象でないか確認

### ✅ バックアップ確認

- [ ] Git commit で現在の状態をセーブしている
- [ ] タグ付け `v2-docs-consolidation-final` 等で標識している

### ✅ 統合ドキュメント確認

- [ ] TEMPLATE_SYSTEM.md が完全か確認
- [ ] DELETED_VIDEO_CACHE.md が完全か確認
- [ ] ARCHITECTURE_AND_DESIGN.md が完全か確認
- [ ] PLUGIN_SYSTEM.md が完全か確認
- [ ] SESSION_REPORTS.md が完全か確認

---

## 削除実行ステップ

### ステップ 1: バージョンコントロール

```bash
cd /path/to/repository

# 現在の状態をコミット
git add -A
git commit -m "docs: テンプレート統合版作成（削除前）"

# バックアップタグ作成
git tag v2-docs-consolidation-final
```

### ステップ 2: 削除実行

```bash
cd v2/docs

# テンプレート関連削除
rm -f TEMPLATE_SPECIFICATION_v2.md TEMPLATE_INTEGRATION_v2.md TEMPLATE_USER_GUIDE.md \
      TEMPLATE_SETTINGS_ENV.md TEMPLATE_SUMMARY.md TEMPLATE_PATH_RESOLUTION_ROOT_CAUSE.md \
      BLUESKY_TEMPLATE_INTEGRATION_ANALYSIS.md BLUESKY_TEMPLATE_FIX_FINAL_REPORT.md \
      TEMPLATE_VALIDATION_REPORT.md

# キャッシュ関連削除
rm -f DELETED_VIDEO_CACHE_DESIGN.md DELETED_VIDEO_CACHE_IMPLEMENTATION_REPORT.md \
      DELETED_VIDEO_CACHE_INTEGRATION_TESTS.md

# アーキテクチャ関連削除
rm -f ARCHITECTURE_v2.md PLUGIN_ARCHITECTURE_v2.md v2_DESIGN_POLICY.md \
      PLUGIN_MANAGER_INTEGRATION_v2.md

# プラグイン関連削除
rm -f BLUESKY_PLUGIN_GUIDE.md BLUESKY_PLUGIN_FALLBACK_FIXED_SETTINGS.md

# セッションレポート削除
rm -f SESSION_REPORT_20251217.md SESSION_REPORT_20251218.md

# 確認
ls -la | wc -l  # ファイル数確認
```

### ステップ 3: 最終コミット

```bash
git add -A
git commit -m "docs: 統合完了に伴う旧ドキュメント削除（テンプレート、キャッシュ、アーキテクチャ、プラグイン、セッションレポート）"

# 最終ファイルリスト確認
git ls-files v2/docs/ | wc -l
```

---

## 削除後の確認

### ✅ リンク検査

```bash
# README内の参照リンク確認
grep -n "\.md" v2/docs/README_GITHUB_v2.md | head -20

# Python ファイル内の参照確認
grep -r "TEMPLATE_SPECIFICATION_v2" v2/ --exclude-dir=__pycache__
grep -r "ARCHITECTURE_v2" v2/ --exclude-dir=__pycache__
grep -r "PLUGIN_ARCHITECTURE" v2/ --exclude-dir=__pycache__

# 返り値なし = リンク切れなし = OK
```

### ✅ ファイル数確認

**統合前**: 39個
**統合後**: 22個

```bash
cd v2/docs
ls *.md | wc -l  # 22 が返ってくる
```

---

**作成日**: 2025-12-18
**ステータス**: 削除前確認リスト
**次ステップ**: 上記チェックリストを完了後、削除実行
