# ニコニコ動画手動追加 - published_at 修正

**日付**: 2025年12月25日
**問題**: ニコニコ動画を手動で追加した際に、GUI上の公開日時がおかしい
**ステータス**: ✅ 修正完了

---

## 🔴 報告されていた問題

```
投稿日時: 2025/09/17 19:03
GUI表示: 12月24日23時8分 ← おかしい
```

### 原因

`NiconicoPlugin.get_video_details()` で、ニコニコページから公開日時を抽出する代わりに、**現在時刻** を使用していた：

```python
# ❌ 間違い
published_at = datetime.now(timezone.utc).isoformat()  # 手動追加時の"今"が記録される
```

---

## ✅ 修正内容

### 修正ファイル

- **v3/plugins/niconico_plugin.py** （Line 461～）

### 修正内容

ニコニコページから正確な公開日時を抽出するロジックを実装：

```python
# 優先度1: video:release_date メタタグ（最も正確） ← ★ 推奨
# 優先度2: article:published_time メタタグ
# 優先度3: data-initial-state JSON の createTime フィールド
# 優先度4: RSS フィード
# 優先度5: フォールバック（現在時刻）
```

### ページパース結果

ニコニコ動画ページから以下のメタタグを検出：

```html
<meta property="video:release_date" content="2025-09-17T19:03+0900" />
```

このメタタグから **正確な公開日時** `2025-09-17T19:03+0900` を抽出

---

## 📊 テスト結果

```
✅ published_at        : 2025-09-17T19:03+0900
✅ 日付が正しく 2025-09-17 です
✅ 時刻が正しく 19:03 です
✅ テスト完了
```

---

## 📝 ログ出力例

```log
[get_video_details] video:release_date から取得: 2025-09-17T19:03+0900
[get_video_details] 取得成功: sm45414087 - まゆにゃあについて説明するつくよみちゃん - published_at=2025-09-17T19:03+0900
```

---

## 🔧 修正適用箇所

1. **NiconicoPlugin.get_video_details()**
   - ニコニコページから公開日時メタタグを抽出
   - 複数のフォールバック機構を実装
   - エラー時は現在時刻をデフォルト値として使用

2. **属性名の統一**
   - `self.niconico_user_id` → `self.user_id` に統一

---

## ✨ 今後の動作

ニコニコ動画を手動で追加すると：

1. **ページからメタタグ取得**: `video:release_date` から正確な投稿日時を取得
2. **DB保存**: 正確な公開日時をDBに保存
3. **GUI表示**: 正確な公開日時がGUIに表示される

```
投稿日時: 2025/09/17 19:03
GUI表示: 9月17日19時03分 ✅ 正確に表示される
```

---

**生成ファイル**:
- test_niconico_published_at.py - 修正検証用テスト
- test_niconico_page_parse.py - ページパース確認用テスト
