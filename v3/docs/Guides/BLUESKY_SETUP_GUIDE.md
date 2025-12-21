# Bluesky 認証設定ガイド

**対象バージョン**: v3.1.0+
**最終更新**: 2025-12-21
**ステータス**: ✅ 実装完了

---

## 📖 このガイドについて

このドキュメントは、Bluesky の認証設定（ハンドル・アプリパスワード取得）を詳細に解説します。

**所要時間**: 約10分

---

## 📋 必要な情報

StreamNotify で Bluesky に投稿するには、以下の2つが必要です：

| 項目 | 説明 | 例 |
|:--|:--|:--|
| **Bluesky ハンドル** | Bluesky アカウントのユーザー名 | `yourname.bsky.social` |
| **アプリパスワード** | アプリ用の専用パスワード | `xxxx-xxxx-xxxx-xxxx` |

⚠️ **重要**: 通常のパスワードではなく、**アプリ専用のパスワード**を使用します。

---

## 🎯 ステップ 1: Bluesky アカウント確認

### すでに Bluesky アカウントがある場合

1. Bluesky アプリ（iOS/Android）またはウェブ版（bsky.app）を開く
2. 右上の**プロフィールアイコン**をタップ
3. **「@ハンドル」** が表示される

**ハンドルの例**:
```
@yourname.bsky.social    ← これがハンドル
@john.bsky.social
@streaming-channel.bsky.social
```

### まだ Bluesky アカウントがない場合

1. https://bsky.app へアクセス
2. 「Create new account」をクリック
3. メールアドレスを入力
4. 確認メールからアカウント作成を完了

✅ アカウント作成後、**ハンドルが決定**されます

---

## 🎯 ステップ 2: アプリパスワードを生成

### ⚠️ 重要な注意事項

> **通常のパスワード（ログイン用）ではなく、アプリパスワード（専用パスワード）を生成してください。**

**理由**:
- セキュリティ: 通常パスワードを外部アプリに渡さない
- 制限: アプリパスワードは特定アプリのみで有効
- 無効化: 不要になったら個別に削除可能

---

### アプリパスワード取得手順（ウェブ版）

#### 1️⃣ Bluesky ウェブ版を開く

```
https://bsky.app にアクセス
```

#### 2️⃣ 設定画面を開く

```
右上のプロフィールアイコン
  ↓
「⚙️ Settings」をクリック
```

#### 3️⃣ アプリパスワード管理ページを開く

```
左メニューの「プライバシーとセキュリティ」をクリック
  ↓
「アプリパスワード」をクリック
```

#### 4️⃣ アプリパスワードを生成
- アプリパスワードは一度しか表示されません。

```
「アプリパスワードを追加」をクリック
  ↓
アプリ名を入力: 「StreamNotify」（推奨）
  ↓
「Create」をクリック
```

#### 5️⃣ パスワードを確認・保存

```
表示されたパスワード（例: xxxx-xxxx-xxxx-xxxx）をコピー
  ↓
テキストエディタに一時保存
  ↓
settings.env に貼り付け
```

✅ **アプリパスワード生成完了**

---

### アプリパスワード取得手順（モバイルアプリ）

#### 1️⃣ プロフィール画面を開く

```
Bluesky アプリを開く
  ↓
左下の「😊 プロフィールアイコン」をタップ
```

#### 2️⃣ 設定を開く

```
上部の「⚙️ Settings」をタップ
```

#### 3️⃣ アプリパスワード管理ページを開く

```
左メニューの「プライバシーとセキュリティ」をクリック
  ↓
「アプリパスワード」をクリック
```

#### 4️⃣ アプリパスワードを生成
- アプリパスワードは一度しか表示されません。

```
「アプリパスワードを追加」をクリック
  ↓
アプリ名を入力: 「StreamNotify」（推奨）
  ↓
「Create」をクリック
```

#### 5️⃣ パスワードを確認・保存

```
表示されたパスワード（例: xxxx-xxxx-xxxx-xxxx）をコピー
  ↓
メモアプリに一時保存
  ↓
settings.env に貼り付け

```
✅ **アプリパスワード生成完了**

---

## 🎯 ステップ 3: settings.env に設定

アプリパスワードが取得できたら、以下のように `settings.env` に入力します：

### テンプレート

```env
# Bluesky 設定
BLUESKY_USERNAME=yourname.bsky.social
BLUESKY_PASSWORD=xxxx-xxxx-xxxx-xxxx
BLUESKY_POST_ENABLED=True
```

### 具体例

```env
# Bluesky 設定
BLUESKY_USERNAME=streaming-channel.bsky.social
BLUESKY_PASSWORD=abcd-efgh-ijkl-mnop
BLUESKY_POST_ENABLED=True
```

### 各項目の説明

| 項目 | 説明 | 必須 |
|:--|:--|:--|
| `BLUESKY_USERNAME` | Bluesky ハンドル（@を除く） | ✅ 必須 |
| `BLUESKY_PASSWORD` | アプリパスワード（xxxx-xxxx-xxxx-xxxx形式） | ✅ 必須 |
| `BLUESKY_POST_ENABLED` | Bluesky 投稿を有効にするか（True/False） | ✅ 必須 |

---

## ✅ 設定確認テスト

### テスト 1: 認証情報の確認

```bash
# settings.env が正しく設定されているか確認
BLUESKY_USERNAME=yourname.bsky.social  # ← @ を除く
BLUESKY_PASSWORD=xxxx-xxxx-xxxx-xxxx    # ← コピペミスがないか
BLUESKY_POST_ENABLED=True               # ← True であること
```

### テスト 2: 接続テスト

```
1. アプリを起動
2. GUI の「投稿テスト」ボタンをクリック
3. ログを確認
```

**成功時のログ**:
```
✅ Bluesky にログインしました: yourname.bsky.social
✅ 投稿テスト成功（本投稿なし）
```

**失敗時のログ**:
```
❌ Bluesky ログイン失敗: 認証情報が不正です
```

---

## 🐛 よくあるエラーと対応

### ❌ 「認証情報が不正です」

**原因**: ハンドルまたはパスワードが間違っている

**対応**:
1. ハンドルに `@` が含まれていないか確認
   ```env
   ❌ BLUESKY_USERNAME=@yourname.bsky.social  # @ を削除
   ✅ BLUESKY_USERNAME=yourname.bsky.social
   ```

2. パスワードの形式を確認
   ```env
   ✅ BLUESKY_PASSWORD=xxxx-xxxx-xxxx-xxxx  # ハイフン4つで区切られている
   ```

3. パスワードが完全にコピーできているか確認
   ```
   # 末尾に余計なスペースがないか？
   # 一文字落としていないか？
   ```

### ❌ 「ハンドルが見つかりません」

**原因**: Bluesky ハンドルが正しくない

**対応**:
1. Bluesky アプリで自分のハンドルを確認
2. プロフィール → ハンドルを正確にコピー
3. `settings.env` に貼り付け（@を除く）

### ❌ 「アプリパスワードが無効です」

**原因**: アプリパスワードが削除されている可能性

**対応**:
1. Bluesky 設定 → App Passwords を確認
2. 削除されていないか確認
3. 必要に応じて新しいアプリパスワードを生成
4. `settings.env` を更新

### ❌ 「接続がタイムアウトしました」

**原因**: インターネット接続が不安定、または Bluesky サーバーが無応答

**対応**:
1. インターネット接続を確認
2. 5分待ってから再度試す
3. Bluesky ウェブ版が動作しているか確認

---

## 🔒 セキュリティに関する注意

### ✅ 推奨事項

1. **複数のアプリパスワードを作成する**
   ```
   - StreamNotify 用
   - 他のアプリ用
   ```

2. **定期的に確認**
   - 不要なアプリパスワードは削除

3. **settings.env を保護**
   - 公開リポジトリに含めない
   - Git の `.gitignore` に追加済み（デフォルト）

### ❌ してはいけないこと

- 通常のパスワードを `settings.env` に入力しない
- GitHub などに `settings.env` をコミットしない
- アプリパスワードを他人と共有しない

---

## 📱 複数アプリでの使い分け

同じ Bluesky アカウントで複数のアプリを使う場合：

```
Bluesky 設定 → App Passwords
  ↓
複数のアプリパスワードを生成
  ├─ StreamNotify
  ├─ 他のボット
  └─ etc.
  ↓
各アプリで異なるパスワードを使用
  ↓
不要になったら個別削除
```

**メリット**:
- 各アプリを独立管理
- 問題が発生した場合、そのアプリだけ無効化
- セキュリティが向上

---

## ✨ 設定完了後

### 次のステップ

1. [GETTING_STARTED.md](./GETTING_STARTED.md) - クイックスタートに戻る
2. [GUI_USER_MANUAL.md](./GUI_USER_MANUAL.md) - GUI の使い方を学ぶ
3. [SETTINGS_OVERVIEW.md](./SETTINGS_OVERVIEW.md) - その他の設定項目を確認

### 投稿テスト

```
1. アプリを起動
2. 動画を1つ選択
3. 「投稿テスト」ボタンをクリック
4. ログで成功を確認
5. Bluesky で投稿を確認
```

---

## 📋 チェックリスト

Bluesky 設定が完了したか確認：

- [ ] Bluesky アカウントがある
- [ ] Bluesky ハンドルを確認した（@を除く）
- [ ] ウェブ版の設定から App Passwords ページを開いた
- [ ] 「StreamNotify」という名前でアプリパスワードを生成した
- [ ] パスワードを確認・保存した
- [ ] `settings.env` に ハンドル を入力した
- [ ] `settings.env` に アプリパスワード を入力した
- [ ] `BLUESKY_POST_ENABLED=True` と設定した
- [ ] アプリを起動して「投稿テスト」で成功を確認した

全てチェック出来たら、設定完了です！ ✅

---

## 📞 トラブルシューティング

より詳しいトラブルシューティングは：

- [FAQ_TROUBLESHOOTING_BASIC.md](./FAQ_TROUBLESHOOTING_BASIC.md) - 基本的なトラブルシューティング
- [DEBUG_DRY_RUN_GUIDE.md](..//Technical/DEBUG_DRY_RUN_GUIDE.md) - ログの確認方法

---

**Bluesky 設定が完了したら、[GETTING_STARTED.md](./GETTING_STARTED.md) に戻って次のステップへ進んでください！**

**最終更新**: 2025-12-21
