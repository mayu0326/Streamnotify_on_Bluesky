# StreamNotify on Bluesky v2 - 設計方針メモ（更新版）

> **対象**: v2 の仕様確定と、v3+ への拡張ロードマップの境界を明確にするドキュメント
> **読者想定**: 開発チーム（人間＋AI）
> **最終更新**: 2025-12-17 (DB正規化対応)

---

## 1. 基本方針：「コア」と「エクステンション」の分離

StreamNotify v2 は以下の二層構造を採用する：

### 1.1 コア（バニラ状態、プラグイン未導入）
- **機能範囲**
  - YouTube RSS ポーリング＆RSS解析
  - ローカルDB（SQLite `data/video_list.db`）への動画情報保存
  - テキスト＋URL による Bluesky 投稿
  - ログファイル記録（`logs/app.log`, `logs/error.log`）
  - Tkinter GUI による動画表示・選択・投稿実行・統計表示

- **責務**
  - RSS から新着動画を検出し、DB に保存（`video_id` で重複判定）
  - 投稿対象を DB から取得し、簡潔なテンプレートで投稿
  - ユーザーの運用フローをサポート

- **実装ファイル**
  - `main_v2.py`: エントリーポイント・メインループ
  - `config.py`: 設定読み込み・バリデーション
  - `database.py`: SQLite操作・テーブル管理
  - `youtube_rss.py`: RSS 取得・パース
  - `bluesky_core.py`: Bluesky 投稿処理（ログイン・URL Facet構築）
  - `gui_v2.py`: Tkinter GUI
  - `logging_config.py`: ロギング設定

### 1.2 エクステンション（プラグイン）
- **機能範囲**
  - YouTube Data API 連携（ライブ判定、詳細情報取得）
  - ニコニコ動画 RSS 監視
  - 画像添付・テンプレート処理拡張
  - 統合ロギング管理

- **責務**
  - コアの NotificationPlugin インターフェース を実装し、`plugins/` ディレクトリに配置
  - 自動ロード・有効化される
  - コア機能を拡張するが、コアの責務を奪わない

- **実装ファイル**
  - `plugins/bluesky_plugin.py`: Bluesky投稿プラグイン
  - `plugins/youtube_api_plugin.py`: YouTube API連携
  - `plugins/youtube_live_plugin.py`: ライブ判定
  - `plugins/niconico_plugin.py`: ニコニコ監視
  - `plugins/logging_plugin.py`: ロギング拡張

---

## 2. テンプレート機能：API安定化とUI分離

### 2.1 テンプレートAPI（コアで固定）

テンプレートは Jinja2 形式とし、以下の `event_context` dict を常に受け取れることを保証する：

| キー名 | 型 | 説明 | 来源 | 変更禁止 |
|--------|----|----|------|---------|
| `title` | str | 動画タイトル | DB `videos.title` | ✅ |
| `video_id` | str | YouTube/ニコニコ等の動画ID | DB `videos.video_id` | ✅ |
| `video_url` | str | 動画URL | DB `videos.video_url` | ✅ |
| `channel_name` | str | チャンネル名 | DB `videos.channel_name` | ✅ |
| `published_at` | str | 公開日時（ISO 8601） | DB `videos.published_at` | ✅ |
| `source` | str | 動画配信元（"youtube" / "niconico" など）。小文字で統一 | DB `videos.source` | ✅ |
| `content_type` | str | コンテンツ種別。値は "video" / "live" / "archive" / "none" のいずれか。source と組み合わせて利用 | DB `videos.content_type` | ✅ |
| `live_status` | str or None | ライブ配信の状態。値は null / "none" / "upcoming" / "live" / "completed" のいずれか。content_type != "live" の場合は null を期待 | DB `videos.live_status` | ✅ |
| `image_filename` | str | 保存済みサムネイル画像ファイル名 | DB `videos.image_filename` | ✅ |
| `posted_at` | str | Bluesky投稿日時（ISO 8601、未投稿時はNone） | DB `videos.posted_at` | ✅ |

**拡張ルール**（v3+ で新しいキーを追加する場合）
- 既存キーの**削除・型変更は禁止**
- 新規キーの追加は OK だが、テンプレートファイルとドキュメントを同時に更新する
- 後方互換性を維持（古いテンプレートファイルも動作するように）

**補足：source と content_type の使い分け**
- `source`: 「どのプラットフォームからの動画か」（"youtube", "niconico" など）
- `content_type`: 「コンテンツの形式は何か」（"video", "live", "archive", "none"）
→ テンプレートで両者を組み合わせて利用（例：`{{ source }}/{{ content_type }}`）

### 2.2 テンプレートファイルの置き場所と命名規則

```
templates/
├── youtube/
│   ├── yt_new_video_template.txt      # YouTube新着動画用（バニラ状態では使用）
│   ├── yt_online_template.txt         # YouTube配信開始用（YouTube Liveプラグイン）
│   └── yt_offline_template.txt        # YouTube配信終了用（YouTube Liveプラグイン）
└── niconico/
    └── nico_new_video_template.txt    # ニコニコ新着動画用（ニコニコプラグイン）
                                       # ご注意: ユーザー名は自動取得（優先順位: RSS > 静画API > ユーザーページ > 環境変数 > ユーザーID）
                                       #        取得されたユーザー名は settings.env に自動保存
```

**ファイル形式**
- 文字コード: UTF-8（BOM なし）
- 改行: LF
- テンプレート記法: Jinja2（`{{ key }}` で `event_context` のキーを参照）

**例**（YouTube新着動画）
```jinja2
{{ title }}

🎬 {{ channel_name }}
📅 {{ published_at }}

{{ video_url }}
```

### 2.3 テンプレート編集・UIについて

- **v2 での扱い**
  テンプレートファイルはテキストエディタで手動編集とする
  コア仕様には「プレビュー機能」「エディタUI」を含めない

- **v3+ での扱い**（FUTURE_ROADMAP参照）
  - テンプレートエディタを GUI タブまたは Web UI として追加可能
  - ただし API(`event_context` の形)は v2 と互換のまま
  - エディタはあくまで「作成・編集の利便性向上」であり、コアではない

---

## 3. データベース設計：「動画テーブル」と「周辺テーブル」の境界

### 3.1 コアテーブル: `videos`（v2で確定）

```sql
CREATE TABLE videos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    video_url TEXT NOT NULL,
    published_at TEXT NOT NULL,
    channel_name TEXT,
    source TEXT DEFAULT 'youtube',
    posted_to_bluesky INTEGER DEFAULT 0,
    posted_at TEXT,
    selected_for_post INTEGER DEFAULT 0,
    scheduled_at TEXT,
    thumbnail_url TEXT,
    content_type TEXT DEFAULT 'video',
    live_status TEXT,
    is_premiere INTEGER DEFAULT 0,
    image_mode TEXT,
    image_filename TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**責務**
- YouTube / ニコニコ等から取得した「視聴可能なコンテンツ」をすべて記録
- 通常動画、ライブアーカイブ、配信のアーカイブ化後のレコードなどを格納

**変更禁止（v2で確定）**
- 既存カラムの削除
- 既存カラムの型変更
- `video_id` のユニーク制約の廃止

**拡張OK（v3+）**
- 新規カラム追加（互換性維持）
- インデックス追加

**カラム値の正規化ルール（v2で実装）**

| カラム | 許可される値 | デフォルト | 説明 |
|--------|-----------|----------|------|
| `source` | "youtube", "niconico", その他（小文字） | "youtube" | 配信元を小文字で統一 |
| `content_type` | "video", "live", "archive", "none" | "video" | コンテンツ形式。"ニコニコ動画" などの値は許可しない |
| `live_status` | null, "none", "upcoming", "live", "completed" | null | ライブの状態。content_type != "live" の場合は null を推奨 |

**バリデーション（database.py で実装）**
- `INSERT` / `UPDATE` 時に上記の値をチェック
- 不正な値が与えられた場合、例外発生またはデフォルト値に置き換え
- content_type="video" で live_status が null 以外の場合は WARNING ログを出力

**補足：live_status と content_type の使い分け**
- `content_type`: 「何の種類のコンテンツか」（"video" / "live" / "archive" など）
- `live_status`: ライブの状態（"upcoming" / "live" / "completed" / "none" など）
→ `content_type="live"` の場合のみ `live_status` が "upcoming" / "live" / "completed" のいずれかとなることを期待

### 3.2 将来テーブル：ライブ・キャッシュ・イベント（v3+で追加検討）

v2 では実装しないが、将来以下のテーブル追加を想定する：

#### ケース A: 配信中の「一時的な状態情報」をキャッシュする場合
```sql
-- 配信中ライブの一時情報（配信終了後は削除）
CREATE TABLE live_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id TEXT UNIQUE NOT NULL,
    live_start_at TEXT,
    viewer_count INTEGER,
    current_title TEXT,
    status TEXT,  -- 'live', 'ending', 'completed'
    last_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```
**責務**: YouTube Live プラグインが定期的に更新し、配信終了後にスナップショットを `videos` テーブルに確定させる

#### ケース B: イベント（開始・終了・アーカイブ化）を記録する場合
```sql
-- 配信のライフサイクルイベント
CREATE TABLE live_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id TEXT NOT NULL,
    event_type TEXT,  -- 'stream_start', 'stream_end', 'archived'
    occurred_at TIMESTAMP,
    metadata TEXT,  -- JSON形式で詳細情報を格納
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```
**責務**: イベント駆動型の監視・通知にも対応可能にする

#### ケース C: 外部API（YouTube Data API など）のレスポンスキャッシュ
```sql
-- APIレスポンスキャッシュ（TTL付き）
CREATE TABLE api_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cache_key TEXT UNIQUE NOT NULL,
    payload_type TEXT,  -- 'youtube_search', 'youtube_video_detail' など
    payload JSON,
    fetched_at TIMESTAMP,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```
**責務**: API クォータ節約・レスポンス高速化

### 3.3 設定データについて

**v2 での扱い**
- 設定情報（YouTube チャンネルID、Bluesky認証情報、ポーリング間隔など）は **DB に格納しない**
- `settings.env` ファイルでのみ管理（テキストファイル）
- 理由: DB 破損時に設定まで巻き込まないための分離

**設定ファイルの構成**
- ファイル名: `settings.env`
- サンプル: `settings.env.example`
- フォーマット: `KEY=VALUE`（python-dotenv で読み込み）
- 必須項: `YOUTUBE_CHANNEL_ID`, `BLUESKY_USERNAME`, `BLUESKY_PASSWORD`, `POLL_INTERVAL_MINUTES`
- オプション項: `APP_MODE`, `DEBUG_MODE`, `TIMEZONE`, 各プラグイン設定など

**v3+ での設定管理改善案**
- 設定UI（GUI / Web）を導入する際に、内部的に設定を複数ファイルに分割可能
- ユーザーからは「統一された設定パネル」として見える設計

---

## 4. GUI と設定管理：v2の責務範囲

### 4.1 v2 GUI（gui_v2.py）の責務

**実装済み・v2で確定**
- 動画一覧表示（Treeview, DB `videos` テーブルを表示）
- 動画の複数選択（チェックボックス）
- 投稿実行（選択動画を Bluesky へ投稿）
- ドライラン（投稿をシミュレート）
- 動画削除（DB から完全削除）
- 統計表示（投稿数、未投稿数、プラグイン状態など）

**実装予定・v3+以降**
- テンプレートエディタ（GUIタブまたは Web UI として）
- 設定管理UI（アカウント設定、機能詳細設定のロード・セーブ）
- 設定バックアップ（settings.env と DB のエクスポート・インポート）

**GUI として書き込まない**
- `settings.env` への直接書き込み（破損リスク）
- プラグインの有効・無効切り替え（config.py の責務）

### 4.2 設定表示の「読み取り専用」機能（v2で検討）

GUIで設定を「表示のみ」する場合：

| 表示項目 | 来源 | 用途 |
|---------|------|------|
| APP_MODE | `config.py` | 現在の動作モード（normal / auto_post など） |
| POLL_INTERVAL_MINUTES | `config.py` | ポーリング間隔 |
| 導入済みプラグイン一覧 | `plugin_manager.py` | 有効なプラグイン（bluesky_plugin, youtube_api_plugin など） |
| DEBUG_MODE 状態 | `config.py` | デバッグログが有効かどうか |

これにより、ユーザーが「今どの設定で動いているか」を GUI から確認可能になり、安心感が増す。

### 4.3 設定ファイルの管理方針

**v2**
- 単一ファイル `settings.env`（プラグインごとに分割しない）
- テキストエディタで手動編集
- README・SETTINGS_OVERVIEW.md で詳しく説明
- 設定破損時の復旧手順をドキュメント化

**v3+**
- 内部的には複数ファイル or DB保存へ移行可能（後方互換性維持）
- 設定UI が導入されたら、エクスポート・インポート機能を提供
- ユーザーからの入口は統一化（UI or CLI）

---

## 5. プラグインAPIの安定性

### 5.1 NotificationPlugin インターフェース（変更禁止）

```python
class NotificationPlugin:
    """すべてのプラグインが実装する基本インターフェース"""

    def get_name(self) -> str:
        """プラグイン名（例: "Bluesky Posting Plugin"）"""
        pass

    def get_version(self) -> str:
        """プラグインバージョン"""
        pass

    def on_new_video(self, event_context: dict) -> None:
        """新着動画検出時のコールバック"""
        pass

    def on_live_start(self, event_context: dict) -> None:
        """配信開始検出時のコールバック（オプション）"""
        pass

    def on_live_end(self, event_context: dict) -> None:
        """配信終了検出時のコールバック（オプション）"""
        pass
```

**変更禁止**
- メソッド名の変更
- パラメータの削除

**拡張OK**
- 新規メソッドの追加
- `event_context` キーの追加（新しいプラグインが必要とする場合）

### 5.2 プラグインローディング（plugin_manager.py）

```python
# plugins/ ディレクトリをスキャン
# NotificationPlugin を実装したクラスを自動検出
# インスタンス化＆登録
```

**v2で確定**
- 自動検出・自動ロード
- 環境変数で有効・無効制御（例: `YOUTUBE_API_KEY` が未設定なら youtube_api_plugin は無効）
- 起動時にロード済みプラグイン一覧をログ出力

---

## 6. ライブ配信対応の段階的実装

### 6.1 v2: 通常動画のみ対応

コア機能は「YouTube RSS で取得できる通常動画」のみを対象とする。

```python
# youtube_rss.py の責務
# - RSS フィード取得
# - 新着動画抽出
# - DB へ記録（content_type="video" として固定）
```

ライブ配信はプラグインによる拡張扱い。

### 6.2 v2.x: YouTube Live プラグイン登場

```python
# plugins/youtube_live_plugin.py
# - YouTube Data API で配信開始・終了を検知
# - live_cache テーブルを使用（一時情報）
# - 配信終了後、videos テーブルに content_type="archive" として確定
```

### 6.3 v3: ライブデータの統合管理

この段階で `live_events` や `live_cache` を正式に導入し、イベント駆動型の監視に対応。

---

## 7. ロギング設定（logging_config.py + logging_plugin.py）

### 7.1 v2 のデフォルト（プラグイン未導入時）

```
logs/
├── app.log              # アプリ全般のログ（INFO以上）
└── error.log            # エラーのみ（WARNING以上）
```

**出力設定**
- ファイル: DEBUG レベル（詳細）
- コンソール: INFO レベル（簡潔）
- 改行コード: LF（統一）

### 7.2 v2 + logging_plugin.py（プラグイン導入時）

複数のロガーが別々のログファイルを管理：

```
logs/
├── app.log              # アプリケーション全般
├── post.log             # Bluesky投稿成功
├── post_error.log       # Bluesky投稿エラー
├── youtube.log          # YouTube監視
├── niconico.log         # ニコニコ監視
├── gui.log              # GUI操作
├── audit.log            # 監査ログ
├── thumbnails.log       # サムネイル処理
└── tunnel.log           # トンネル接続（将来）
```

**ログレベル制御**
- 環境変数: `LOG_LEVEL_CONSOLE`, `LOG_LEVEL_FILE`
- デバッグモード: `DEBUG_MODE=true` で全ロガーが DEBUG レベルに上昇

---

## 8. 今後のバージョンロードマップ（概要）

### v2.x（バグ修正・軽微な改善）
- テンプレート機能の安定化
- サムネイル取得の改善
- ロギングの細調整
- **DB正規化（content_type / live_status のバリデーション）**

### v3（大型機能拡張）
- テンプレートエディタ（GUI タブ or Web UI）
- ライブ配信統合管理（live_events, live_cache テーブル正式導入）
- Web UI 試験版（Tkinter に並行して提供）
- 設定管理UI（settings.env の読み書き）

### v4+（さらなる拡張）
- Discord・Twitch 連携
- PubSubHubbub 対応（リアルタイム通知）
- PostgreSQL/MySQL サポート
- マルチアカウント対応

---

## 9. 実装ガイドライン：AIが読んでも迷わないルール

以下を厳守することで、人間開発者＋AI開発ツール（Claude, Copilot等）が齟齬なく実装できる：

1. **ファイル名は完全一致**
   - `bluesky_core.py`, `gui_v2.py` など、このドキュメントに書いた名前をそのまま使用
   - リネームは this.md にも反映

2. **クラス名・メソッド名は完全一致**
   - `NotificationPlugin`, `get_name()` など、インターフェースを変えない

3. **DB カラム名は完全一致**
   - `video_id`, `posted_to_bluesky` など、既存カラムは削除・リネームしない
   - 新規追加時は別カラムとして扱う

4. **DB カラム値は正規化を厳守**
   - `source`: 小文字（"youtube", "niconico" など）
   - `content_type`: 許可リスト値のみ（"video", "live", "archive", "none"）
   - `live_status`: 許可リスト値またはnull（"upcoming", "live", "completed", "none"）

5. **環境変数名は完全一致**
   - `YOUTUBE_CHANNEL_ID`, `BLUESKY_POST_ENABLED` など
   - 新規追加時は README・SETTINGS_OVERVIEW に記載

6. **テンプレートAPI（event_context キー）の互換性**
   - 既存キーは削除・型変更禁止
   - 新規キー追加時はドキュメント更新と同時

7. **コメント・ドキュメントは実装と同時更新**
   - 仕様変更時は、このドキュメント→ソースコード→README の順に同期

---

## 10. 問い合わせ・レビュー

このドキュメントに対する質問・提案・修正は、以下の形で：

- **仕様の疑問**: Issue / Discussion
- **実装の相談**: PR のコメント or code review
- **ドキュメント改善**: 「ここが読みにくい」も遠慮なく

**更新予定**
- v2 公開前: 最終レビュー
- v2.x: マイナーアップデート（DB正規化対応）
- v3 企画: 大幅改定
