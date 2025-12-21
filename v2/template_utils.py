# -*- coding: utf-8 -*-

"""
Stream notify on Bluesky - v2 テンプレート処理ユーティリティ

テンプレートの読み込み、検証、レンダリングに関する共通関数と定義を提供。

この関数群は、複数のプラグイン（Bluesky、将来の他プラグイン）で再利用可能。
Vanilla 環境では、テンプレート仕様とファイル構成が整備されるため、
プラグイン実装時にこれらの関数を即座に活用できます。
"""

import os
import logging
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any
from jinja2 import Environment, TemplateNotFound, TemplateSyntaxError

logger = logging.getLogger("AppLogger")

__author__ = "mayuneco(mayunya)"
__copyright__ = "Copyright (C) 2025 mayuneco(mayunya)"
__license__ = "GPLv2"

# ============ テンプレート種別ごとの required_keys 定義 ============

TEMPLATE_REQUIRED_KEYS = {
    # YouTube
    "youtube_new_video": ["title", "video_id", "video_url", "channel_name"],
    "youtube_online": ["title", "video_url", "channel_name", "live_status"],
    "youtube_offline": ["title", "channel_name", "live_status"],

    # ニコニコ
    "nico_new_video": ["title", "video_id", "video_url", "channel_name"],

    # Twitch（将来）
    "twitch_online": ["title", "stream_url", "broadcaster_user_name", "game_name"],
    "twitch_offline": ["broadcaster_user_name", "channel_url"],
    "twitch_raid": ["from_broadcaster_user_name", "to_broadcaster_user_name", "raid_url"],
}

# ============ テンプレート種別ごとの表示可能変数（ボタン挿入用） ============

TEMPLATE_ARGS = {
    # YouTube 新着動画
    "youtube_new_video": [
        ("動画タイトル", "title"),
        ("動画 ID", "video_id"),
        ("動画 URL", "video_url"),
        ("チャンネル名", "channel_name"),
        ("投稿日時", "published_at"),
        ("プラットフォーム", "platform"),
    ],

    # YouTube 配信開始
    "youtube_online": [
        ("配信タイトル", "title"),
        ("配信 URL", "video_url"),
        ("チャンネル名", "channel_name"),
        ("配信開始日時", "published_at"),
        ("配信ステータス", "live_status"),
    ],

    # YouTube 配信終了
    "youtube_offline": [
        ("チャンネル名", "channel_name"),
        ("配信タイトル", "title"),
        ("配信ステータス", "live_status"),
    ],

    # ニコニコ 新着動画
    # ご注意: ユーザー名は自動取得（RSS > 静画API > ユーザーページ > 環境変数 > ユーザーID）
    #        取得されたユーザー名は settings.env に自動保存されます
    "nico_new_video": [
        ("動画タイトル", "title"),
        ("動画 ID", "video_id"),
        ("動画 URL", "video_url"),
        ("投稿者名", "channel_name"),  # 自動取得・優先順位: RSS > 静画API > ユーザーページ > 環境変数 > ユーザーID
        ("投稿日時", "published_at"),
    ],

    # Twitch 配信開始（将来）
    "twitch_online": [
        ("配信タイトル", "title"),
        ("配信者表示名", "broadcaster_user_name"),
        ("配信者ログイン名", "broadcaster_user_login"),
        ("ゲーム名", "game_name"),
        ("配信 URL", "stream_url"),
        ("配信開始日時", "started_at"),
    ],

    # Twitch 配信終了（将来）
    "twitch_offline": [
        ("配信者表示名", "broadcaster_user_name"),
        ("チャンネル URL", "channel_url"),
        ("配信終了日時", "ended_at"),
    ],

    # Twitch Raid（将来）
    "twitch_raid": [
        ("Raid 元：配信者表示名", "from_broadcaster_user_name"),
        ("Raid 先：配信者表示名", "to_broadcaster_user_name"),
        ("Raid URL", "raid_url"),
    ],
}

# ============ ユーザーに見せない内部キー（ブラックリスト） ============

TEMPLATE_VAR_BLACKLIST = {
    "youtube_new_video": {
        "is_premiere",           # プレミア判定フラグ
        "image_mode",            # 画像モード
        "image_filename",        # キャッシュ済み画像ファイル名
        "posted_at",             # DB 用
        "selected_for_post",     # DB 用
        "use_link_card",         # 内部用
        "embed",                 # 内部用
        "image_source",          # 内部用
    },

    "youtube_online": {
        "is_premiere",
        "image_mode",
        "image_filename",
        "posted_at",
        "selected_for_post",
        "use_link_card",
        "embed",
        "image_source",
    },

    "youtube_offline": {
        "image_mode",
        "image_filename",
        "posted_at",
        "selected_for_post",
        "use_link_card",
        "embed",
        "image_source",
    },

    "nico_new_video": {
        "image_mode",
        "image_filename",
        "posted_at",
        "selected_for_post",
        "use_link_card",
        "embed",
        "image_source",
    },

    # Twitch（将来）
    "twitch_online": {
        "image_mode",
        "image_filename",
        "use_link_card",
        "embed",
    },

    "twitch_offline": {
        "use_link_card",
        "embed",
    },

    "twitch_raid": {
        "use_link_card",
        "embed",
    },
}

# ============ デフォルトテンプレートパス ============

TEMPLATE_ROOT = Path(__file__).parent / "templates"
DEFAULT_TEMPLATE_DIR = TEMPLATE_ROOT / ".templates"
DEFAULT_TEMPLATE_PATH = DEFAULT_TEMPLATE_DIR / "default_template.txt"
FALLBACK_TEMPLATE_PATH = DEFAULT_TEMPLATE_DIR / "fallback_template.txt"

# ============ ユーティリティ関数 ============


def _get_env_var_from_file(file_path: str, env_var_name: str) -> Optional[str]:
    """
    settings.env などの設定ファイルから環境変数を読み込む（os.getenv の補完）。

    Python の os.getenv() は .env ファイルから環境変数を読み込まないため、
    ここで手動でファイルを読んで、settings.env から値を取得します。

    Args:
        file_path: 設定ファイルパス（例: "settings.env"）
        env_var_name: 環境変数名（例: "TEMPLATE_YOUTUBE_NEW_VIDEO_PATH"）

    Returns:
        環境変数の値、見つからない場合は None
    """
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
        logger.debug(f"⚠️ 設定ファイル読み込みエラー ({file_path}): {e}")

    return None


def _get_legacy_env_var_name(template_type: str) -> str:
    """
    テンプレート種別からレガシー形式の環境変数名を生成（後方互換性用）。

    Args:
        template_type: テンプレート種別（例: "youtube_new_video"）

    Returns:
        レガシー形式の環境変数名
        例: "youtube_new_video" → "BLUESKY_YT_NEW_VIDEO_TEMPLATE_PATH"
            "nico_new_video" → "BLUESKY_NICO_NEW_VIDEO_TEMPLATE_PATH"
    """
    parts = template_type.split("_")
    if len(parts) >= 2:
        service_name = parts[0]
        event_type = "_".join(parts[1:])

        # ショートカット生成
        service_short = {
            "youtube": "YT",
            "nico": "NICO",
            "niconico": "NICO",
            "twitch": "TW",
        }.get(service_name, service_name.upper())

        legacy_var = f"BLUESKY_{service_short}_{event_type.upper()}_TEMPLATE_PATH"
        return legacy_var

    return f"BLUESKY_{template_type.upper()}_TEMPLATE_PATH"


def get_template_path(
    template_type: str,
    env_var_name: str = None,
    default_fallback: str = None
) -> Optional[str]:
    """
    環境変数からテンプレートパスを取得、なければデフォルトを返す。

    Args:
        template_type: テンプレート種別（例: "youtube_new_video"）
        env_var_name: 環境変数名（省略時は自動生成）
                     例: "TEMPLATE_YOUTUBE_NEW_VIDEO_PATH" （推奨）
                         or "BLUESKY_YT_NEW_VIDEO_TEMPLATE_PATH" （レガシー）
        default_fallback: フォールバック先デフォルトパス

    Returns:
        テンプレートファイルパス（文字列）、見つからない場合は None

    環境変数の解決順序:
        1. env_var_name で明示的に指定された名前
        2. TEMPLATE_{template_type}_PATH 形式
        3. BLUESKY_*_TEMPLATE_PATH 形式（レガシー）
        4. default_fallback（指定時）
        5. 自動推論（service_short と event_type から）
    """
    # 明示的に指定された環境変数名が最優先
    if env_var_name:
        env_path = os.getenv(env_var_name)
        if env_path:
            return env_path

    # 新形式: TEMPLATE_{template_type}_PATH
    new_format_env_var = f"TEMPLATE_{template_type.upper()}_PATH"

    # ★ 修正: 複数ソースから読み込む
    # 優先度 1: os.getenv（システム環境変数）
    env_path = os.getenv(new_format_env_var)

    # 優先度 2: settings.env から直接読み込む
    if not env_path:
        env_path = _get_env_var_from_file("settings.env", new_format_env_var)
        if env_path:
            logger.debug(f"✅ settings.env から読み込み: {new_format_env_var} = {env_path}")

    if env_path:
        return env_path

    # レガシー形式: BLUESKY_*_TEMPLATE_PATH（後方互換性）
    # 例: youtube_new_video → BLUESKY_YT_NEW_VIDEO_TEMPLATE_PATH
    legacy_format_env_var = _get_legacy_env_var_name(template_type)

    # 優先度 1: os.getenv（システム環境変数）
    env_path = os.getenv(legacy_format_env_var)

    # 優先度 2: settings.env から直接読み込む
    if not env_path:
        env_path = _get_env_var_from_file("settings.env", legacy_format_env_var)
        if env_path:
            logger.debug(f"✅ settings.env から読み込み（レガシー形式）: {legacy_format_env_var} = {env_path}")

    if env_path:
        return env_path

    # デフォルトフォールバック
    if default_fallback:
        return default_fallback

    # ここからは推論：テンプレート種別から自動構築を試みる
    # 例: "youtube_new_video" → "templates/youtube/yt_new_video_template.txt"
    parts = template_type.split("_")
    if len(parts) >= 2:
        service_name = parts[0]
        event_type = "_".join(parts[1:])

        # ショートカット生成
        service_short = {
            "youtube": "yt",
            "nico": "nico",
            "niconico": "nico",
            "twitch": "twitch",
        }.get(service_name, service_name)

        template_filename = f"{service_short}_{event_type}_template.txt"
        template_path = TEMPLATE_ROOT / service_name / template_filename

        if template_path.exists():
            return str(template_path)

    return None


def load_template_with_fallback(
    path: str,
    default_path: str = None,
    template_type: str = "unknown"
) -> Optional[Any]:
    """
    テンプレートファイルを読み込み、失敗時はデフォルトにフォールバック。

    Args:
        path: 読み込み対象のテンプレートファイルパス
        default_path: フォールバック先のデフォルトテンプレートパス
        template_type: テンプレート種別（ログ出力用）

    Returns:
        Jinja2 Template オブジェクト、失敗時は None

    ログ出力:
        - 成功時: DEBUG レベル
        - フォールバック: WARNING レベル
        - エラー: ERROR レベル
    """
    if not path:
        logger.warning(f"⚠️ テンプレートパスが指定されていません（種別: {template_type}）")
        path = default_path or str(DEFAULT_TEMPLATE_PATH)

    try:
        # ★ 相対パス → 絶対パス変換（TEMPLATE_ROOT 基準）
        template_path = Path(path)
        logger.debug(f"🔍 初期パス: {path}, is_absolute={template_path.is_absolute()}")
        logger.debug(f"   TEMPLATE_ROOT={TEMPLATE_ROOT}, TEMPLATE_ROOT.parent={TEMPLATE_ROOT.parent}")

        if not template_path.is_absolute():
            # 相対パスの場合は TEMPLATE_ROOT を基準に解決
            template_path = TEMPLATE_ROOT.parent / path  # v2 ディレクトリ基準
            logger.debug(f"🔍 相対パスを絶対パスに変換: {path} → {template_path}")

        # ファイルの存在確認
        logger.debug(f"🔍 テンプレートファイル存在確認: {template_path}")
        logger.debug(f"   exists={template_path.exists()}")

        if not template_path.exists():
            logger.warning(f"⚠️ テンプレートファイルが見つかりません: {template_path}")
            if default_path:
                logger.info(f"🔄 デフォルトテンプレートにフォールバック: {default_path}")
                path = default_path
                # フォールバック時も相対パス → 絶対パス変換を試みる
                template_path = Path(path)
                if not template_path.is_absolute():
                    template_path = TEMPLATE_ROOT.parent / path
                    logger.debug(f"🔍 フォールバック時に相対パスを絶対パスに変換: {path} → {template_path}")
                logger.debug(f"🔍 フォールバック先ファイル存在確認: {template_path} (exists={template_path.exists()})")
            else:
                logger.warning(f"❌ フォールバックパスも指定されていません")
                return None

        # ファイル読み込み
        logger.debug(f"🔍 ファイルを開く: {template_path}")
        with open(template_path, encoding="utf-8") as f:
            template_str = f.read()

        # Jinja2 Environment でテンプレート化
        env = Environment()
        # フィルターを登録（format_datetime_filter は別途提供）
        from utils_v2 import format_datetime_filter
        env.filters["datetimeformat"] = format_datetime_filter

        template_obj = env.from_string(template_str)

        logger.debug(f"✅ テンプレート読み込み成功: {path} (種別: {template_type})")
        return template_obj

    except FileNotFoundError as e:
        logger.error(f"❌ テンプレートファイル読み込みエラー: {template_path} (path={path})")
        logger.error(f"   詳細: ファイルが見つかりません - {e}")
        if default_path and path != default_path:
            logger.info(f"🔄 デフォルトテンプレートにフォールバック: {default_path}")
            return load_template_with_fallback(
                default_path,
                default_path=None,
                template_type=template_type
            )
        return None

    except TemplateSyntaxError as e:
        logger.error(f"❌ テンプレート構文エラー: {template_path} - {e}")
        return None

    except Exception as e:
        import traceback
        logger.error(f"❌ テンプレート読み込み予期しないエラー: {type(e).__name__}: {e}")
        logger.error(f"   パス: {template_path}")
        logger.error(f"   トレースバック: {traceback.format_exc()}")
        return None


def validate_required_keys(
    event_context: dict,
    required_keys: List[str],
    event_type: str = "unknown"
) -> Tuple[bool, Optional[List[str]]]:
    """
    event_context に必須キーが存在するか検証。

    Args:
        event_context: 投稿イベント情報（辞書）
        required_keys: 必須キー一覧
        event_type: イベント種別（ログ出力用）

    Returns:
        (検証成功フラグ, 不足キー一覧)
        - 成功時: (True, None)
        - 失敗時: (False, ["key1", "key2", ...])

    ログ出力:
        - 成功時: DEBUG レベル
        - 失敗時: WARNING レベル
    """
    if not required_keys:
        logger.debug(f"✅ 必須キーなし（種別: {event_type}）")
        return True, None

    missing_keys = [key for key in required_keys if key not in event_context or event_context[key] is None]

    if not missing_keys:
        logger.debug(f"✅ 必須キー検証成功（種別: {event_type}、キー数: {len(required_keys)}）")
        return True, None
    else:
        logger.warning(f"⚠️ 必須キー不足（種別: {event_type}）: {missing_keys}")
        return False, missing_keys


def render_template(
    template_obj: Any,
    event_context: dict,
    template_type: str = "unknown"
) -> Optional[str]:
    """
    Jinja2 テンプレートをレンダリング。

    Args:
        template_obj: Jinja2 Template オブジェクト
        event_context: 投稿イベント情報
        template_type: テンプレート種別（ログ出力用）

    Returns:
        レンダリング済みテキスト、失敗時は None

    ログ出力:
        - 成功時: DEBUG レベル
        - 失敗時: ERROR レベル
    """
    if not template_obj:
        logger.error(f"❌ テンプレートオブジェクトが None です（種別: {template_type}）")
        return None

    try:
        rendered_text = template_obj.render(**event_context)
        logger.debug(f"✅ テンプレートレンダリング成功（種別: {template_type}）")
        return rendered_text

    except Exception as e:
        logger.error(f"❌ テンプレートレンダリングエラー（種別: {template_type}）: {e}")
        return None


def get_template_args_for_dialog(
    template_type: str,
    blacklist: bool = True
) -> List[Tuple[str, str]]:
    """
    テンプレート編集ダイアログ用に、表示可能な変数リストを取得。

    Args:
        template_type: テンプレート種別
        blacklist: ブラックリストを適用するか（デフォルト: True）

    Returns:
        [(変数表示名, 変数キー), ...] のリスト
    """
    args = TEMPLATE_ARGS.get(template_type, [])

    if blacklist:
        blacklist_set = TEMPLATE_VAR_BLACKLIST.get(template_type, set())
        # ブラックリストに含まれるキーを除外
        args = [
            (display_name, key)
            for display_name, key in args
            if key not in blacklist_set
        ]

    return args


def get_sample_context(
    template_type: str
) -> Dict[str, Any]:
    """
    テンプレート編集ダイアログのプレビュー用サンプル event_context を取得。

    Args:
        template_type: テンプレート種別

    Returns:
        サンプル event_context 辞書
    """
    # サンプルデータ集
    sample_contexts = {
        "youtube_new_video": {
            "title": "新作ゲーム実況【part 1】",
            "video_id": "dQw4w9WgXcQ",
            "video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "channel_name": "〇〇チャンネル",
            "published_at": "2025-12-17T15:30:00Z",
            "platform": "YouTube",
            "source": "youtube",
            "content_type": "video",
            "live_status": None,
        },

        "youtube_online": {
            "title": "今夜は雑談配信！",
            "video_url": "https://www.youtube.com/watch?v=example",
            "channel_name": "〇〇チャンネル",
            "published_at": "2025-12-17T20:00:00Z",
            "platform": "YouTube",
            "source": "youtube",
            "content_type": "live",
            "live_status": "live",
        },

        "youtube_offline": {
            "title": "今夜は雑談配信！",
            "channel_name": "〇〇チャンネル",
            "platform": "YouTube",
            "source": "youtube",
            "content_type": "live",
            "live_status": "completed",
        },

        "nico_new_video": {
            "title": "【ゆっくり解説】最新ゲーム",
            "video_id": "sm12345678",
            "video_url": "https://www.nicovideo.jp/watch/sm12345678",
            "channel_name": "投稿者名",
            "published_at": "2025-12-17T10:00:00Z",
            "platform": "Niconico",
            "source": "niconico",
            "content_type": "video",
            "live_status": None,
        },

        "nico_online": {
            "title": "ニコ生配信中",
            "video_url": "https://live.nicovideo.jp/watch/lv1234567",
            "channel_name": "投稿者名",
            "platform": "Niconico",
            "source": "niconico",
            "content_type": "live",
            "live_status": "live",
        },

        "nico_offline": {
            "channel_name": "投稿者名",
            "title": "ニコ生配信中",
            "platform": "Niconico",
            "source": "niconico",
            "content_type": "live",
            "live_status": "completed",
        },

        # Twitch（将来）
        "twitch_online": {
            "title": "ゲーム配信開始！",
            "stream_url": "https://twitch.tv/example_user",
            "broadcaster_user_name": "配信者名",
            "broadcaster_user_login": "example_user",
            "game_name": "Just Chatting",
            "started_at": "2025-12-17T19:00:00Z",
            "platform": "Twitch",
            "source": "twitch",
            "content_type": "live",
            "live_status": "live",
        },

        "twitch_offline": {
            "broadcaster_user_name": "配信者名",
            "channel_url": "https://twitch.tv/example_user",
            "ended_at": "2025-12-17T21:30:00Z",
            "platform": "Twitch",
            "source": "twitch",
            "content_type": "live",
            "live_status": "completed",
        },
    }

    return sample_contexts.get(
        template_type,
        {
            "title": "サンプルタイトル",
            "channel_name": "サンプル投稿者",
            "video_url": "https://example.com/video",
            "platform": "Unknown",
            "source": "unknown",
            "content_type": "video",
            "live_status": None,
        }
    )


# ============ ユーザー向けプレビュー/検証関数 ============


def preview_template(
    template_type: str,
    template_text: str,
    event_context: Dict[str, Any] = None
) -> Tuple[bool, str]:
    """
    ユーザーがテンプレート編集ダイアログで入力したテンプレートをプレビュー。

    Args:
        template_type: テンプレート種別
        template_text: ユーザーが入力したテンプレートテキスト
        event_context: プレビュー用 event_context（省略時はサンプル）

    Returns:
        (成功フラグ, プレビューテキスト or エラーメッセージ)
    """
    if event_context is None:
        event_context = get_sample_context(template_type)

    try:
        env = Environment()
        from utils_v2 import format_datetime_filter
        env.filters["datetimeformat"] = format_datetime_filter

        template_obj = env.from_string(template_text)
        rendered = template_obj.render(**event_context)

        logger.debug(f"✅ プレビューレンダリング成功: {template_type}")
        return True, rendered

    except TemplateSyntaxError as e:
        error_msg = f"❌ テンプレート構文エラー (行 {e.lineno}): {e.message}"
        logger.warning(error_msg)
        return False, error_msg

    except Exception as e:
        error_msg = f"❌ プレビュー生成エラー: {str(e)}"
        logger.warning(error_msg)
        return False, error_msg


# ============ テンプレートファイル操作 ============


def save_template_file(
    template_type: str,
    template_text: str,
    output_path: str = None
) -> Tuple[bool, str]:
    """
    ユーザーが編集したテンプレートをファイルに保存。

    Args:
        template_type: テンプレート種別
        template_text: テンプレートテキスト
        output_path: 保存先パス（省略時は推論）

    Returns:
        (成功フラグ, メッセージ)
    """
    if not output_path:
        output_path = get_template_path(template_type)

    if not output_path:
        error_msg = f"❌ テンプレート保存先が決定できません（種別: {template_type}）"
        logger.error(error_msg)
        return False, error_msg

    try:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(template_text)

        success_msg = f"✅ テンプレートを保存しました: {output_path}"
        logger.info(success_msg)
        return True, success_msg

    except Exception as e:
        error_msg = f"❌ テンプレート保存エラー: {str(e)}"
        logger.error(error_msg)
        return False, error_msg


if __name__ == "__main__":
    # ユーティリティのテスト実行
    print("Template Utils - v2.1.0")
    print("=" * 50)

    # テスト: サンプル context を表示
    for template_type in ["youtube_new_video", "nico_new_video"]:
        sample = get_sample_context(template_type)
        print(f"\n{template_type}:")
        print(f"  Sample keys: {list(sample.keys())}")

        args = get_template_args_for_dialog(template_type)
        print(f"  Display args: {len(args)} 項目")

    print("\n" + "=" * 50)
    print("✅ template_utils.py の基本動作確認完了")
