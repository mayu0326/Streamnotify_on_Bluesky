# よくある質問と基本的なトラブルシューティング

**対象バージョン**: v3.1.0+
**最終更新**: 2025-12-21
**ステータス**: ✅ 実装完了

---

## 📖 このドキュメントについて

このドキュメントは、**ユーザーがよく遭遇する問題とその解決方法**をまとめたガイドです。

困った時は、まずこのドキュメントを参照してください。

---

## 🔴 重大なエラー

### Q1: アプリケーションが起動しない

#### ❌ 症状

```
python main_v3.py を実行しても何も起動しない
または
エラーメッセージが表示される
```

#### ✅ 解決方法

**ステップ 1: Python のバージョンを確認**

```bash
python --version
```

**必須**: Python 3.13 以上

```
Python 3.13 以上  ← OK
Python 3.12 以下   ← NG（アップグレード必要）
```

**ステップ 2: 依存パッケージを再インストール**

```bash
pip install --upgrade -r requirements.txt
```

**ステップ 3: 仮想環境を再構築**

```bash
# 既存の仮想環境を削除
rm -rf venv  # Mac/Linux
rmdir /s venv  # Windows

# 新しい仮想環境を作成
python -m venv venv

# 有効化
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# パッケージ再インストール
pip install -r requirements.txt
```

**ステップ 4: ログファイルを確認**

```bash
# ログディレクトリを開く
cd logs

# app.log を確認
cat app.log  # or: type app.log (Windows)
```

**ステップ 5: サポート情報を収集**

```bash
python --version
pip list
# ログの最後の10行をコピー
```

---

### Q2: 「ModuleNotFoundError」エラーが表示される

#### ❌ 症状

```
ModuleNotFoundError: No module named 'xxx'
```

#### ✅ 解決方法

**原因**: 依存パッケージがインストールされていない

**対応**:

```bash
# 全パッケージを再インストール
pip install -r requirements.txt

# または特定のパッケージだけをインストール
pip install atproto feedparser requests pillow beautifulsoup4 python-dotenv
```

確認:

```bash
# インストール済みパッケージを確認
pip list

# 必要なパッケージがあるか確認
pip show atproto
```

---

## 🟠 RSS 取得エラー

### Q3: 「YouTube RSS が取得できない」

#### ❌ 症状

```
- 「動画一覧」が空のまま
- ログに「RSS取得失敗」と表示
- アプリは起動しているが動画が表示されない
```

#### ✅ 解決方法

**ステップ 1: YouTube チャンネル ID を確認**

```env
settings.env で:
YOUTUBE_CHANNEL_ID=UC開始の24文字コード
```

**チャンネル ID の形式**:
- プラグイン未導入時: `UCxxxxxxxxxxxxxxxxxxxxxx`（24文字の英数字）
- プラグイン導入時: `@handle` 使用可能
```
✅ 正しい: UCdQqdoHimaWf8VL-kqEtNiw
❌ 間違い: mayuneco
❌ 間違い: @mayuneco
❌ 間違い: https://www.youtube.com/c/mayuneco
```

チャンネル ID を確認する方法 → [YOUTUBE_SETUP_GUIDE.md](./YOUTUBE_SETUP_GUIDE.md)

**ステップ 2: インターネット接続を確認**

```bash
# 外部サイトに接続できるか確認
ping www.google.com

# YouTube が正常に機能しているか確認
curl https://www.youtube.com

# YouTube RSS が取得できるか確認
curl https://www.youtube.com/feeds/videos.xml?channel_id=UCdQqdoHimaWf8VL-kqEtNiw
```

**ステップ 3: ログで詳細を確認**

```
logs/app.log を開く
  ↓
「RSS取得」で検索
  ↓
エラーメッセージを確認
```

**よくあるエラー**:

| エラーメッセージ | 原因 | 対応 |
|:--|:--|:--|
| `Connection refused` | ネットワーク接続なし | インターネット接続確認 |
| `404 Not Found` | チャンネル ID が無効 | ID を再確認 |
| `Timeout` | YouTube が遅い | 5分待ってから再度実行 |
| `SSL Error` | SSL証明書の問題 | Python 再インストール |

**ステップ 4: 更新ボタンで手動実行**

GUI で [更新] ボタンをクリックして、手動で RSS 取得を試す

**ステップ 5: POLL_INTERVAL_MINUTES を確認**

```env
POLL_INTERVAL_MINUTES=10  # 最小値: 5
```

設定値が大きすぎないか確認

---

### Q4: 「ニコニコの RSS が取得できない」

#### ❌ 症状

```
- ニコニコの動画が表示されない
- ログに「ニコニコ RSS 取得失敗」と表示
```

#### ✅ 解決方法

**ステップ 1: ニコニコ ユーザー ID を確認**

```env
settings.env で:
NICONICO_USER_ID=12345678  # 8～9桁の数字
```

**ユーザー ID を確認する方法** → [NICONICO_SETUP_GUIDE.md](./NICONICO_SETUP_GUIDE.md)

**ステップ 2: プラグインが有効か確認**

GUI の [設定] → [プラグイン] で、ニコニコプラグインが有効か確認

**ステップ 3: ニコニコに接続できるか確認**

```bash
curl https://www.nicovideo.jp
```

成功時: HTML が返される
失敗時: エラーメッセージ

**ステップ 4: ログで詳細を確認**

```
logs/app.log を開く
  ↓
「niconico」で検索
  ↓
エラーメッセージを確認
```

---

## 🟠 Bluesky 投稿エラー

### Q5: 「Bluesky に投稿できない」 / 「認証失敗」

#### ❌ 症状

```
- ログに「❌ 認証失敗」と表示
- 「投稿テスト」が失敗
- Bluesky へのログインできず
```

#### ✅ 解決方法

**ステップ 1: Bluesky 認証情報を確認**

```env
settings.env で:
BLUESKY_USERNAME=yourname.bsky.social  # @を除く
BLUESKY_PASSWORD=xxxx-xxxx-xxxx-xxxx   # アプリパスワード
BLUESKY_POST_ENABLED=True
```

**チェックリスト**:

- [ ] ハンドルに `@` が含まれていないか
- [ ] アプリパスワードに余計なスペースがないか
- [ ] パスワードが完全にコピーされているか
- [ ] `BLUESKY_POST_ENABLED=True` か

**ステップ 2: アプリパスワードを再生成**

Bluesky が古いアプリパスワードを削除した可能性があります

1. Bluesky ウェブ版で App Passwords を確認
2. 古いパスワードを削除
3. 新しいアプリパスワードを生成
4. `settings.env` を更新

詳細 → [BLUESKY_SETUP_GUIDE.md](./BLUESKY_SETUP_GUIDE.md)

**ステップ 3: Bluesky にログインできるか確認**

1. ブラウザで https://bsky.app を開く
2. ハンドル・アプリパスワードでログイン
3. ログインできれば認証情報は正しい

**ステップ 4: 「投稿テスト」を実行**

GUI で [投稿テスト] ボタンをクリック
→ ログで詳細エラーを確認

**ステップ 5: ログで詳細エラーを確認**

```
logs/app.log を開く
  ↓
「Bluesky」で検索
  ↓
エラーメッセージを確認
```

**よくあるエラー**:

| エラー | 原因 | 対応 |
|:--|:--|:--|
| `Invalid credentials` | ハンドルまたはパスワードが間違い | 再確認・再生成 |
| `Unauthorized` | アプリパスワードが無効 | 再生成 |
| `Connection timeout` | Bluesky サーバーが無応答 | 5分待機 |
| `InvalidToken` | トークン有効期限切れ | アプリ再起動 |

---

### Q6: 「画像がアップロードできない」

#### ❌ 症状

```
- ログに「❌ 画像アップロード失敗」と表示
- 投稿はされているが画像がない
- 「ファイルが見つかりません」エラー
```

#### ✅ 解決方法

**ステップ 1: デフォルト画像を確認**

```bash
ls -la images/  # Mac/Linux
dir images      # Windows
```

```
images/default/ にファイルがあるか確認
  ├─ noimage.png
  └─ etc.
```

**ステップ 2: 画像ファイルのパスを確認**

```env
settings.env で:
BLUESKY_IMAGE_PATH=images/default/noimage.png
```

パスが正しいか確認:
- スラッシュ `/` を使用（バックスラッシュ `\` ではない）
- ファイルが実際に存在するか確認

**ステップ 3: 画像ファイルの権限を確認**

```bash
# ファイルが読み取り可能か確認
ls -l images/default/noimage.png  # Mac/Linux
```

読み取り権限 `r` がない場合:

```bash
chmod 644 images/default/noimage.png
```

**ステップ 4: 画像形式を確認**

サポートされている形式:
- JPEG (.jpg, .jpeg)
- PNG (.png)

**ステップ 5: ファイルサイズを確認**

Bluesky API の上限: **1MB**

```bash
# ファイルサイズを確認
ls -lh images/default/noimage.png  # Mac/Linux
```

1MB を超える場合:
- [IMAGE_RESIZE_GUIDE.md](./IMAGE_RESIZE_GUIDE.md) を参照
- 自動リサイズを有効化

---

## 🟡 動作・パフォーマンス関連

### Q7: 「アプリが遅い・反応しない」

#### ❌ 症状

```
- GUI がカクカクしている
- ボタン クリック後に時間がかかる
- 「応答なし」と表示される
```

#### ✅ 解決方法

**ステップ 1: CPU/メモリ使用率を確認**

```bash
# Windows
tasklist /v

# Mac/Linux
top
```

**メモリ使用率が高い場合**:
- アプリを再起動
- 他のアプリを閉じる

**ステップ 2: ポーリング間隔を調整**

```env
# 現在の設定を確認
POLL_INTERVAL_MINUTES=10  # デフォルト

# 長くする（负荷低下）
POLL_INTERVAL_MINUTES=30  # 30分ごと
```

**ステップ 3: デバッグモードを無効化**

```env
DEBUG_MODE=false  # デバッグログ出力を無効化
```

DEBUG ログが多いと処理が遅くなります

**ステップ 4: データベースを最適化**

```bash
# ログフォルダを確認
ls -la logs/

# 古いログを削除
rm logs/app.log.*
```

---

### Q8: 「メモリ使用量が増え続ける」

#### ❌ 症状

```
- 時間と共にメモリ使用量が増える
- アプリの反応が遅くなる
- 最終的にクラッシュ
```

#### ✅ 解決方法

**ステップ 1: 大量の動画が蓄積していないか確認**

```
動画一覧 の統計情報を確認
  ↓
「総動画数」が数千件以上？
  ↓
古い動画を削除
```

**ステップ 2: ログファイルサイズを確認**

```bash
ls -lh logs/  # ファイルサイズ確認
```

ログファイルが数GB の場合:
- 古いログを削除: `rm logs/app.log.*`
- ログレベルを上げる: [DEBUG_DRY_RUN_GUIDE.md](./DEBUG_DRY_RUN_GUIDE.md)

**ステップ 3: データベースをクリーンアップ**

```bash
# バックアップを作成
cp data/video_list.db data/video_list.db.bak

# 投稿済み古い動画を削除
# (手動で GUI から削除)
```

**ステップ 4: 定期的に再起動**

メモリリークが疑われる場合:
- 1日1回アプリを再起動する

---

## 🟡 フィルタ・検索関連

### Q9: 「フィルタが反応しない」 / 「検索結果がない」

#### ❌ 症状

```
- タイトル検索を入力しても反応しない
- ドロップダウン操作が効かない
- 「🔄 リセット」で直ってもすぐに同じ状態
```

#### ✅ 解決方法

**ステップ 1: アプリを再起動**

```bash
アプリを終了
  ↓
python main_v3.py で再起動
```

**ステップ 2: 「🔄 リセット」ボタンをクリック**

```
フィルタパネルの「🔄 リセット」をクリック
  ↓
全フィルタが初期化
  ↓
再度検索
```

**ステップ 3: GUI ウィンドウをリサイズ**

GUI が壊れている可能性:

```
ウィンドウをドラッグして大きさ変更
  ↓
または
  ↓
ウィンドウを最小化 → 最大化
```

**ステップ 4: キャッシュをクリア**

```bash
# GUI キャッシュを削除（手動）
rm -rf ~/.local/share/streamnotify  # Linux
# (Windows/Mac は GUI から 「設定」→ 「キャッシュをクリア」)
```

---

### Q10: 「フィルタで複数キーワードが機能しない」

#### ❌ 症状

```
タイトル検索で「新作 実況」と入力
  ↓
期待: 「新作」と「実況」の両方を含む動画
実際: 何も表示されない or 予期しない結果
```

#### ✅ 解決方法

**ステップ 1: キーワード間の区切りを確認**

```
✅ 正しい: 「新作 実況」（スペース1つ）
❌ 間違い: 「新作,実況」（カンマで区切る）
❌ 間違い: 「新作　実況」（全角スペース）
```

**ステップ 2: 大文字・小文字を確認**

検索は**大文字・小文字を区別**します

```
検索: 「YouTube」
結果: 「YouTube」を含む動画のみ（「youtube」は除外）
```

**ステップ 3: 完全一致の必要性を確認**

検索は**部分一致**です

```
検索: 「新」
結果: 「新作」「新しい」「最新」など「新」を含む全て
```

---

## 🟡 設定・カスタマイズ関連

### Q11: 「テンプレートが反映されない」

#### ❌ 症状

```
- テンプレートを編集してもログで「テンプレート未使用」と表示
- 投稿フォーマットが変わらない
- デフォルトテンプレートで投稿される
```

#### ✅ 解決方法

**ステップ 1: テンプレートファイルを確認**

```bash
ls -la templates/youtube/
```

テンプレートファイルが存在するか確認:
- `yt_new_video_template.txt`
- `yt_online_template.txt`
- etc.

**ステップ 2: settings.env で設定を確認**

```env
# テンプレートパスが正しいか確認
TEMPLATE_YOUTUBE_NEW_VIDEO_PATH=templates/youtube/yt_new_video_template.txt

# パスが存在するか確認（相対パス）
```

**ステップ 3: ファイル文字コードを確認**

テンプレートファイルが **UTF-8** で保存されているか確認

**ステップ 4: アプリを再起動**

テンプレートは起動時に読み込まれます

```bash
アプリを完全に終了
  ↓
python main_v3.py で再起動
```

**ステップ 5: ログで詳細を確認**

```
logs/app.log を開く
  ↓
「テンプレート」で検索
  ↓
エラーまたはスキップメッセージを確認
```

詳細 → [TEMPLATE_SYSTEM.md](../Technical/TEMPLATE_SYSTEM.md)

---

### Q12: 「PREVENT_DUPLICATE_POSTS が機能していない」

#### ❌ 症状

```
- PREVENT_DUPLICATE_POSTS=true に設定したが重複投稿できる
- 警告が表示されない
- 同じ動画が2度投稿される
```

#### ✅ 解決方法

**ステップ 1: 設定を確認**

```env
PREVENT_DUPLICATE_POSTS=true
```

`true` / `false` の大文字小文字を確認

```
✅ PREVENT_DUPLICATE_POSTS=true
❌ PREVENT_DUPLICATE_POSTS=True
❌ PREVENT_DUPLICATE_POSTS=yes
```

**ステップ 2: アプリを再起動**

設定は起動時に読み込まれます

```bash
アプリを完全に終了
  ↓
python main_v3.py で再起動
```

**ステップ 3: 投稿テストモードではないか確認**

DRY RUN モードでは重複チェックが無効化されます

```env
APP_MODE=selfpost  # ← これであること
❌ APP_MODE=dry_run  # これではチェック無効
```

**ステップ 4: 動画が投稿済みか確認**

```
GUI で 「投稿状態」 が 「投稿済み」 か確認
  ↓
未投稿になっていれば DB が同期していない可能性
```

**ステップ 5: ログで詳細を確認**

```
logs/app.log を開く
  ↓
「重複」で検索
  ↓
チェックロジックが実行されているか確認
```

詳細 → [GUI_FILTER_AND_DUPLICATE_PREVENTION.md](../Technical/GUI_FILTER_AND_DUPLICATE_PREVENTION.md)

---

## 🟢 その他の問題

### Q13: 「ログに警告（⚠️）が多い」

#### ❌ 症状

```
ログに多数の「⚠️ 警告」メッセージが表示される
アプリは動作しているが大丈夫？
```

#### ✅ 解決方法

警告は**エラーではなく情報**です

**よくある警告と意味**:

| 警告 | 意味 | 対応 |
|:--|:--|:--|
| `⚠️ テンプレートファイル未検出` | デフォルトテンプレートを使用 | 問題なし |
| `⚠️ プラグイン読み込み失敗` | プラグインが無効化 | 機能が制限される可能性 |
| `⚠️ ファイルが見つかりません` | 画像などが無い | その機能は利用不可 |

---

### Q14: 「ポート番号が使用中」エラー

#### ❌ 症状

```
エラー: Address already in use: (port) 5000
または同様のポート関連エラー
```

#### ✅ 解決方法

別のプロセスがポートを使用しています

**ステップ 1: 既存プロセスを終了**

```bash
# 既存の StreamNotify を終了
# GUI から [終了] ボタンをクリック
```

**ステップ 2: ポートが解放されるまで待機**

```bash
5秒～10秒待機
  ↓
アプリを再起動
```

**ステップ 3: 強制的に解放（高度）**

```bash
# Windows
netstat -ano | findstr :5000
taskkill /PID <PID> /F

# Mac/Linux
lsof -i :5000
kill -9 <PID>
```

---

## 📋 トラブルシューティングチェックリスト

問題が発生した時の確認順序：

1. [ ] エラーメッセージ・ログを確認した
2. [ ] 設定ファイル（settings.env）を確認した
3. [ ] アプリを再起動した
4. [ ] インターネット接続を確認した
5. [ ] Python/パッケージを再インストールした
6. [ ] この FAQ で該当する項目を探した
7. [ ] 関連ドキュメントを参照した
8. [ ] ログファイルの詳細を確認した

---

## 📞 さらなるサポート

| 問題の種類 | 参照ドキュメント |
|:--|:--|
| **インストール・セットアップ** | [GETTING_STARTED.md](./GETTING_STARTED.md), [INSTALLATION_SETUP.md](./INSTALLATION_SETUP.md) |
| **ログの詳細確認** | [DEBUG_DRY_RUN_GUIDE.md](../Technical/DEBUG_DRY_RUN_GUIDE.md) |
| **GUI 操作** | [GUI_USER_MANUAL.md](./GUI_USER_MANUAL.md) |
| **テンプレート問題** | [TEMPLATE_SYSTEM.md](../Technical/TEMPLATE_SYSTEM.md) |
| **YouTube 設定** | [YOUTUBE_SETUP_GUIDE.md](./YOUTUBE_SETUP_GUIDE.md) |
| **Bluesky 認証** | [BLUESKY_SETUP_GUIDE.md](./BLUESKY_SETUP_GUIDE.md) |
| **画像処理** | [IMAGE_RESIZE_GUIDE.md](../Technical/IMAGE_RESIZE_GUIDE.md) |

---

**見つからない問題の場合は、ログファイル（logs/app.log）の内容をコピーして保存しておくと、今後のサポートに役立ちます。**

**最終更新**: 2025-12-21
