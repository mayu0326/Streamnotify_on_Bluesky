# Bluesky テンプレート統合 - 根本原因分析と修正案

**対象ファイル**: v2/template_utils.py
**問題**: `os.getenv()` が settings.env から環境変数を読み込めない

---

## 🔴 根本原因

### Issue: `os.getenv()` が settings.env から環境変数を読み込まない

**現在のコード** (template_utils.py line 248-251):

```python
# 新形式: TEMPLATE_{template_type}_PATH
new_format_env_var = f"TEMPLATE_{template_type.upper()}_PATH"
env_path = os.getenv(new_format_env_var)  # ← settings.env を読まない！
if env_path:
    return env_path
```

**問題**: Python の標準 `os.getenv()` は以下からのみ読み込み：
1. システム環境変数（Windows の環境変数）
2. プロセス実行時の環境変数
3. `os.environ` に登録されている値

**settings.env ファイルは読まない**

---

## ✅ 解決方案

### 方案 A: `config.py` から設定を読む（推奨）

既に `config.py` で dotenv を使って settings.env を読み込んでいるので、そこから取得

```python
# template_utils.py 先頭部分
from config import get_config

config = get_config("settings.env")
```

### 方案 B: template_utils.py で直接 dotenv を読む

```python
from dotenv import load_dotenv
load_dotenv("settings.env")
```

### 方案 C: 環境変数を直接読み込む関数を追加

```python
def get_template_path_from_settings(template_type: str) -> Optional[str]:
    """settings.env から直接テンプレートパスを読み込む"""
    settings_path = Path("settings.env")
    if not settings_path.exists():
        return None

    env_var_name = f"TEMPLATE_{template_type.upper()}_PATH"

    with open(settings_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.startswith('#') or '=' not in line:
                continue
            key, value = line.split('=', 1)
            if key.strip() == env_var_name:
                return value.strip()

    return None
```

---

## 修正後の期待動作

**修正前**:
```
テンプレートパス: D:\...\templates\.templates\default_template.txt
                           ↑ デフォルトにフォールバック
```

**修正後**:
```
テンプレートパス: D:\...\templates\youtube\yt_new_video_template.txt
                           ↑ 正しいテンプレート
```

---

## 推奨: 方案 A + 方案 C のハイブリッド

1. **優先度 1**: config.py の設定を使う
2. **優先度 2**: settings.env を直接読む（フォールバック）
3. **優先度 3**: デフォルトテンプレート

```python
def get_template_path(...):
    # 1. 明示的に指定された env_var_name
    if env_var_name:
        # config から取得を試みる
        ...

    # 2. TEMPLATE_{template_type}_PATH 形式
    env_var_name = f"TEMPLATE_{template_type.upper()}_PATH"

    # 2.1 config から取得
    try:
        from config import get_config
        config = get_config("settings.env")
        env_path = getattr(config, env_var_name.lower(), None)
        if env_path:
            return env_path
    except:
        pass

    # 2.2 os.getenv から取得（システム環境変数）
    env_path = os.getenv(env_var_name)
    if env_path:
        return env_path

    # 2.3 settings.env から直接読み込み
    env_path = _get_env_var_from_file("settings.env", env_var_name)
    if env_path:
        return env_path

    # 3. デフォルトテンプレート
    if default_fallback:
        return default_fallback

    # 4. 推論して自動構築
    ...
```

---

## 修正実装ファイル

**ファイル**: v2/template_utils.py

**修正内容**:

1. `_get_env_var_from_file()` 関数を追加
2. `get_template_path()` を修正

```python
# ★ 新規追加関数
def _get_env_var_from_file(file_path: str, env_var_name: str) -> Optional[str]:
    """settings.env などの設定ファイルから環境変数を読み込む"""
    try:
        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            return None

        with open(file_path_obj, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    key, value = line.split('=', 1)
                    if key.strip() == env_var_name:
                        return value.strip()
    except Exception as e:
        logger.warning(f"⚠️ 設定ファイル読み込みエラー ({file_path}): {e}")

    return None
```

修正後の `get_template_path()`:

```python
def get_template_path(
    template_type: str,
    env_var_name: str = None,
    default_fallback: str = None
) -> Optional[str]:
    """..."""

    if env_var_name:
        env_path = os.getenv(env_var_name)
        if env_path:
            return env_path

    # 新形式: TEMPLATE_{template_type}_PATH
    new_format_env_var = f"TEMPLATE_{template_type.upper()}_PATH"

    # ★ 修正: 複数ソースから読み込む
    env_path = os.getenv(new_format_env_var)
    if not env_path:
        # settings.env から読み込む
        env_path = _get_env_var_from_file("settings.env", new_format_env_var)

    if env_path:
        return env_path

    # ... 以降の処理は同じ
```

---

## テスト方法

修正後、再度スクリプトを実行：

```bash
python debug_template_integration.py
```

**期待出力**:

```
テンプレートパス: D:\...\templates\youtube\yt_new_video_template.txt  ✅
テンプレートパス: D:\...\templates\niconico\nico_new_video_template.txt  ✅
```

---

## 関連するテンプレート処理の全体フロー（修正後）

```
1. GUI 「投稿」ボタン
   ↓
2. plugin_manager.post_video_with_all_enabled(video)
   ↓
3. bluesky_plugin.post_video(video)
   ↓
4. render_template_with_utils("youtube_new_video", video)
   ↓
5. get_template_path("youtube_new_video")
   ├─ os.getenv() で環境変数取得
   ├─ settings.env から読み込み  ← ★ ここで修正
   └─ 推論で自動構築
   ↓
6. load_template_with_fallback(template_path)
   ↓
7. render_template(template_obj, video)
   ↓
8. template_obj.render(video)
   ↓
9. rendered_text = "🎬 テストチャンネルの新作動画..."
   ↓
10. video["text_override"] = rendered_text
    ↓
11. minimal_poster.post_video_minimal(video)
    ↓
12. if text_override:
        post_text = text_override  ← ✅ テンプレート内容を使用
    ↓
13. Bluesky API へ投稿
```

---

**修正による効果**:

| 項目 | 修正前 | 修正後 |
|:--|:--|:--|
| テンプレートパス解決 | ❌ settings.env を読まない | ✅ settings.env から読み込む |
| テンプレート使用 | ❌ デフォルトテンプレートに フォールバック | ✅ 正しいテンプレートを使用 |
| 投稿内容 | ❌ 従来フォーマット | ✅ テンプレートに基づいた内容 |
