# プロジェクト開発ガイドライン

**最終更新**: 2026-01-03

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

**⭐** = 主要な開発用ディレクトリ

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

## � 開発時のベストプラクティス

### パスの扱い方
- **絶対パス使用**: ファイル操作では `Path()` を使用して絶対パスを構築
- **相対パス回避**: スクリプトは実行場所に依らず動作するように実装
- **パス区切り文字**: 常に `/` を使用（Windows では自動変換される）

### ログ出力
- **ログレベルの適切な使用**: DEBUG / INFO / WARNING / ERROR / CRITICAL
- **ログメッセージのフォーマット**: 絵文字プリフィックスで視認性向上
  - ✅ 成功
  - ❌ エラー
  - ⚠️ 警告
  - ℹ️ 情報
  - 🔍 デバッグ

### テスト駆動開発（TDD）のすすめ
1. 修正・実装前に `test_scripts/` でテストを作成
2. テストが FAIL することを確認
3. 実装を行う
4. テストが PASS することを確認
5. リファクタリング（必要に応じて）

---

## �📝 チェックリスト

新しいタスクを始めるときの確認:

- [ ] エラー調査のときは `v3/docs/local/` にドキュメント作成
- [ ] テストスクリプト作成のときは `test_scripts/` に配置
- [ ] 本番コード修正は `v3/` 以下で実施
- [ ] 修正完了後は `v3/docs/local/` に報告書を作成
- [ ] 関連する既存ドキュメントを参照・リンク記載

---

## 🔗 関連ドキュメント

**プロジェクト全体**:
- [README.md](../../../README.md) - プロジェクト概要
- [ARCHITECTURE_AND_DESIGN.md](../Technical/ARCHITECTURE_AND_DESIGN.md) - アーキテクチャ設計

**プラグイン開発**:
- [PLUGIN_SYSTEM.md](../Technical/PLUGIN_SYSTEM.md) - プラグイン実装ガイド
- [plugin_interface.py](../../plugin_interface.py) - プラグイン基底クラス

**テンプレート・画像管理**:
- [TEMPLATE_SYSTEM.md](../Technical/TEMPLATE_SYSTEM.md) - テンプレートシステム
- [ASSET_MANAGER_INTEGRATION_v3.md](../Technical/ASSET_MANAGER_INTEGRATION_v3.md) - アセット管理

---

## ❓ FAQ

### Q: テストスクリプトを実行するにはどうする？

**A**: ワークスペースルートで以下を実行：

```bash
python test_scripts/test_youtube_video_id_validation.py
```

### Q: 新しいプラグインを開発するとき？

**A**: 以下の手順で実施：

1. 計画書作成: `v3/docs/local/plugin_*.md`
2. プラグインコード実装: `v3/plugins/your_plugin.py`
3. テストスクリプト作成: `test_scripts/test_your_plugin.py`
4. `plugin_interface.py` を継承して実装
5. 完了報告書作成: `v3/docs/local/IMPLEMENTATION_COMPLETE_PLUGIN_*.md`

### Q: ローカルドキュメント（`v3/docs/local/`）は Git で管理する？

**A**: はい、すべて Git 管理下に置きます。実装の背景・意図を記録しておくことで、将来の保守が容易になります。

---

**バージョン**: v3.3.0 以降に対応
**ステータス**: ✅ 使用中
