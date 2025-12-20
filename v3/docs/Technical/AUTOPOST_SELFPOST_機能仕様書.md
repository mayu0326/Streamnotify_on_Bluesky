# AUTOPOST / SELFPOST 機能仕様書

**正式仕様 v1.0（確定版）**

---

## 0. 目的と前提

本アプリケーションは、YouTube 動画情報を取得し、Bluesky へ投稿する機能を提供する。

投稿方式は以下の **2 つの排他的なモード**に分離される。

* **SELFPOST**：人間が操作する完全手動投稿モード
* **AUTOPOST**：人間の介入を一切行わない完全自動投稿モード

本仕様書は、AUTOPOST 機能を
**予測可能・誤操作耐性が高く・Bot運用に耐える形で定義する**ことを目的とする。

---

## 1. モード定義と排他制御

### 1.1 モード排他仕様（重要）

* SELFPOST モードと AUTOPOST モードは **同時に有効にならない**
* アプリケーションは起動時に **いずれか一方のモード**で動作する
* AUTOPOST モードから SELFPOST モードへ切り替える場合は、

  * 明示的なモード切替操作
  * またはアプリケーションの再起動
    が必要である

バックグラウンドで AUTOPOST が動作したまま SELFPOST を操作することは想定しない。

---

### 1.2 SELFPOST モード（旧 NORMAL）

* 完全手動投稿モード
* GUI 操作を前提とする
* ユーザーが以下を操作可能：

  * 投稿対象の選択（`selected_for_post`）
  * 投稿・予約投稿
  * DRY RUN
* AUTOPOST ロジックは一切実行されない

---

### 1.3 AUTOPOST モード

* 完全自動投稿モード（Bot 運用）
* 人間の判断・操作は介在しない
* 投稿可否は **ロジックと環境変数のみ**で決定される
* AUTOPOST モード中は以下を禁止する：

  * 投稿ボタン操作
  * DRY RUN
  * `selected_for_post` の編集
* GUI は起動しない、または投稿操作を完全に無効化する

---

## 2. AUTOPOST 自動投稿対象の基本条件

AUTOPOST において、以下を **すべて満たす動画のみ** が投稿候補となる。

### 2.1 必須条件

* `posted_to_bluesky = 0`
* `scheduled_at IS NULL OR scheduled_at <= now`
* ブラックリストに含まれていない
* 削除済み・取得不可動画でない

---

### 2.2 時間窓（LOOKBACK）

```text
published_at >= app_started_at - AUTOPOST_LOOKBACK_MINUTES
```

* 環境変数：

  ```env
  AUTOPOST_LOOKBACK_MINUTES=30
  ```
* デフォルト：30 分
* この時間窓は **再起動時の取りこぼし防止**を目的とする
* 過去動画を掘り起こす用途ではない

---

## 3. 動画種別ごとの自動投稿可否

### 3.1 判定対象属性（DB）

* `is_members_only`
* `is_short`
* `is_premiere`
* 通常動画（上記いずれでもないもの）

### 3.2 環境変数

```env
AUTOPOST_INCLUDE_NORMAL=true
AUTOPOST_INCLUDE_SHORTS=false
AUTOPOST_INCLUDE_MEMBER_ONLY=false
AUTOPOST_INCLUDE_PREMIERE=true
```

### 3.3 判定不能時の扱い（重要）

* 以下の属性が **NULL または未取得** の場合は false（投稿しない）扱いとする：

  * `is_members_only`
  * `is_short`
  * `is_premiere`
* 動画種別自体が判定不能な場合は投稿せず、

  * 警告ログのみ出力する
* DB マイグレーションでは、上記フラグは

  * NOT NULL
  * DEFAULT 0（false）
    を前提とする

※ YouTube Live 系の判定は、本設定とは独立して行う。

---

## 4. YouTube Live 自動投稿仕様

### 4.1 統合環境変数（新設）

```env
YOUTUBE_LIVE_AUTO_POST_MODE=all
# all / schedule / live / archive / off
```

ユーザーはこの **1 変数のみ**を設定する。

---

### 4.2 各モードの挙動

| 状態              | all | schedule | live | archive | off |
| --------------- | --- | -------- | ---- | ------- | --- |
| 予約枠（upcoming）   | 投稿  | 投稿       | 投稿   | ×       | ×   |
| 配信開始（live）      | 投稿  | ×        | 投稿   | ×       | ×   |
| 配信終了（completed） | 投稿  | ×        | 投稿   | ×       | ×   |
| アーカイブ公開         | 投稿  | ×        | ×    | 投稿      | ×   |

#### 補足（重要）

* 「アーカイブ公開」は `content_type = archive` で検知する
* 配信終了（`completed`）とアーカイブ公開は **別タイミング**で発生する可能性がある
* 同一動画に対して、`completed` 投稿とアーカイブ投稿は
  **別イベントとして扱う**

---

### 4.3 旧フラグとの後方互換（起動時のみ）

旧環境変数：

```env
YOUTUBE_LIVE_AUTO_POST_START
YOUTUBE_LIVE_AUTO_POST_END
```

#### マッピング仕様

* `YOUTUBE_LIVE_AUTO_POST_MODE` が **未設定の場合のみ**適用
* 起動時に一度だけ内部マッピングを行う

| START | END   | MODE     |
| ----- | ----- | -------- |
| true  | true  | live     |
| true  | false | schedule |
| その他   |       | off      |

* MODE が明示的に設定されている場合、旧フラグは無視する
* 旧フラグはユーザー向けには **非推奨・廃止予定**

---

## 5. AUTOPOST 安全弁仕様

### 5.1 投稿間隔制御

```env
AUTOPOST_INTERVAL_MINUTES=5
```

* 連続投稿によるスパム化を防止する
* 前回投稿から指定時間経過していない場合は投稿しない

---

### 5.2 未投稿大量検知による起動抑止

```env
AUTOPOST_UNPOSTED_THRESHOLD=20
```

以下を **すべて満たす場合**、AUTOPOST は起動しない：

* `published_at >= now - AUTOPOST_LOOKBACK_MINUTES`
* `posted_to_bluesky = 0`
* 件数 ≥ `AUTOPOST_UNPOSTED_THRESHOLD`

#### 意図補足

この判定は
「直近 LOOKBACK 時間内に未投稿動画が大量に存在する」
＝ 設定ミスやデバッグ誤爆の兆候
とみなすための安全弁であり、**古い未投稿ストックには反応しない**。

挙動：

* AUTOPOST 処理を停止
* エラーログ出力
* GUI またはポップアップで警告表示

---

### 5.3 セーフモード起動（デバッグ誤爆対策）

以下の兆候を検出した場合、AUTOPOST は **セーフモード**で起動する：

* 前回起動から短時間で `posted_to_bluesky` が大量にリセットされたと判断できる場合

セーフモードの挙動：

* 自動投稿は行わない
* 警告ログおよび UI 通知のみ行う

---

## 6. 除外ロジックとの整合

AUTOPOST は、既存のすべての除外ロジックを尊重する。

* ブラックリスト
* 削除済み動画
* 非公開・取得不可動画

SELFPOST で投稿不可なものは、AUTOPOST でも投稿不可とする。

---

## 7. 明示的にやらないこと

* AUTOPOST 中に人間が投稿対象を選択する機能
* `selected_for_post` を用いた制御
* 過去動画の一括掘り起こし投稿

---

## 8. 仕様ステータス

本仕様は **AUTOPOST / SELFPOST 機能の正式仕様 v1.0** として確定する。

---

