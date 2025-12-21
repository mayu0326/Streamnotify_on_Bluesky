# プロジェクト開発ガイドライン

**最終更新**: 2025-12-18

---

## 📁 ファイル配置ガイドライン

### テストスクリプト

**配置先**: `test_scripts/`（ワークスペースのルート）

**ルール**:
- すべてのテストスクリプトはプロジェクトルートの `test_scripts/` ディレクトリに配置
- 命名規則: `test_*.py`
- ドキュメント（エラー調査、実装計画など）の検証用スクリプトもここに配置

**例**:
```
test_scripts/
  ├── test_youtube_video_id_validation.py
  ├── check_db.py
  ├── test_config_save.py
  └── ...
```

**理由**:
- プロジェクト全体のテストを一元管理
- v3/ を本番コードのみにして保つ
- CI/CD パイプラインで一括実行可能

---

### ドキュメント（調査・実装記録）

**配置先**: `v3/docs/local/`

**ルール**:
- エラー調査報告書
- 実装計画書
- 修正完了報告書
など、設計・変更履歴に関するドキュメントはすべて `v3/docs/local/` に配置

**命名規則**: わかりやすい英語または日本語
- `error_investigation_*.md` - エラー調査
- `*_plan.md` - 実装計画
- `IMPLEMENTATION_COMPLETE_*.md` - 修正完了報告
- `fix_*.md` - 修正内容説明

**例**:
```
v3/docs/local/
  ├── error_investigation_sm45414087.md
  ├── youtube_live_classification_plan.md
  ├── fix_youtube_video_id_validation.md
  ├── IMPLEMENTATION_COMPLETE_VIDEO_ID_VALIDATION.md
  └── ...
```

**理由**:
- v3 のローカル開発ドキュメントを集約
- 実装の背景・意図が残る
- プロジェクトのナレッジ蓄積

---

### ソースコード（本番）

**配置先**: `v3/` 以下の適切なディレクトリ

**ルール**:
- プラグイン: `v3/plugins/`
- ユーティリティ: `v3/utils/` など
- ファイル作成・修正のときはこの構造を守る

---

## 📋 ワークスペース構造の概要

```
Streamnotify_on_Bluesky/
  ├── v3/                           ← 本番コード
  │   ├── plugins/                  ← プラグイン実装
  │   ├── docs/                     ← プロジェクトドキュメント
  │   │   └── local/                ← ローカル調査・実装記録 ★
  │   ├── main_v3.py
  │   ├── config.py
  │   └── ...
  │
  ├── test_scripts/                 ← テストスクリプト一覧 ★
  │   ├── test_youtube_video_id_validation.py
  │   ├── check_db.py
  │   └── ...
  │
  ├── OLD_App/                      ← レガシー版
  ├── v1/                           ← バージョン 1
  └── ...
```

**★** = 今後使用するディレクトリ

---

## 🛠️ 開発ワークフロー

### 1. バグ・エラー調査のとき

1. **調査実施**
   - エラーログを分析
   - コード確認
   - 根本原因特定

2. **ドキュメント作成** → `v3/docs/local/error_investigation_*.md`
   - エラー内容
   - 原因分析
   - 解決策（短期/中期/長期）

3. **テストスクリプト作成** → `test_scripts/test_*.py`
   - 再現テスト
   - 修正後の検証テスト

### 2. 機能実装・修正のとき

1. **計画書作成** → `v3/docs/local/*_plan.md`
   - 実装内容
   - 対象ファイル
   - 期待するアウトプット

2. **コード実装** → `v3/` 以下
   - プラグイン、ユーティリティなど

3. **テスト実施** → `test_scripts/test_*.py` で検証

4. **完了報告書作成** → `v3/docs/local/IMPLEMENTATION_COMPLETE_*.md`
   - 実装内容
   - テスト結果
   - 改善指標

---

## 📝 チェックリスト

新しいタスクを始めるときの確認:

- [ ] エラー調査のときは `v3/docs/local/` にドキュメント作成
- [ ] テストスクリプト作成のときは `test_scripts/` に配置
- [ ] 本番コード修正は `v3/` 以下で実施
- [ ] 修正完了後は `v3/docs/local/` に報告書を作成
- [ ] 関連する既存ドキュメントを参照・リンク記載

---

## 参考

**現在進行中のタスク**:
1. YouTube Live 判定ロジック整理
   - 計画書: `v3/docs/local/youtube_live_classification_plan.md`

2. Niconico ID エラーの修正（完了）
   - 調査: `v3/docs/local/error_investigation_sm45414087.md`
   - 実装: `v3/docs/local/fix_youtube_video_id_validation.md`
   - 完了: `v3/docs/local/IMPLEMENTATION_COMPLETE_VIDEO_ID_VALIDATION.md`
   - テスト: `test_scripts/test_youtube_video_id_validation.py`

