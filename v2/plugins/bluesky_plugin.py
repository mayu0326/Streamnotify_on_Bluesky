# -*- coding: utf-8 -*-

"""
Stream notify on Bluesky - v2 Bluesky 画像添付拡張プラグイン

Bluesky への画像添付機能を提供する拡張プラグイン。
bluesky_v2.py のコア機能（投稿・Facet・認証・ドライラン）とは独立。
"""

import logging
import sys
import re
from pathlib import Path
import os

# 親ディレクトリをパスに追加（image_manager.pyをインポートするため）
sys.path.insert(0, str(Path(__file__).parent.parent))
from image_manager import get_image_manager
from bluesky_v2 import BlueskyMinimalPoster

logger = logging.getLogger("AppLogger")
post_logger = logging.getLogger("PostLogger")

__author__ = "mayuneco(mayunya)"
__copyright__ = "Copyright (C) 2025 mayuneco(mayunya)"
__license__ = "GPLv2"


# settings.env から値を取得する簡易関数
def get_env_setting(key: str, default: str = None) -> str:
    env_path = Path(__file__).parent.parent / "settings.env"
    if not env_path.exists():
        return default
    try:
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    k, v = line.split('=', 1)
                    if k.strip() == key:
                        return v.strip()
    except Exception as e:
        logger.warning(f"⚠️ 設定ファイル読み込み失敗: {e}")
    return default

from plugin_interface import NotificationPlugin


class BlueskyImagePlugin(NotificationPlugin):
    """Bluesky 画像添付拡張プラグイン（オプション機能）
    
    このプラグインは削除しても Bluesky への投稿は動作します。
    ただし、画像添付機能は無効になります。
    """
    def __init__(self, username: str, password: str, dry_run: bool = False, minimal_poster: BlueskyMinimalPoster = None):
        # 既存の BlueskyMinimalPoster が渡された場合は再ログインを避ける
        self.minimal_poster = minimal_poster if minimal_poster else BlueskyMinimalPoster(username, password, dry_run)
        self.dry_run = dry_run
        # 画像管理クラスのインスタンスを取得
        self.image_manager = get_image_manager()
        # デフォルト画像パスを設定ファイルから取得
        self.default_image_path = get_env_setting("BLUESKY_IMAGE_PATH")

    def post_video(self, video: dict) -> bool:
        """
        動画を投稿（画像添付機能付き）
        
        この post_video は main_v2.py から呼び出されません。
        プラグインマネージャー経由で実行される場合にのみ使用されます。
        """
        # DBに画像ファイルが登録されている場合、そのファイルを優先して使用
        image_filename = video.get("image_filename")
        video = dict(video)  # 元の辞書を変更しないようコピー
        if image_filename and image_filename.strip():
            post_logger.info(f"💾 DB登録済み画像を使用: {image_filename}")
            video["image_source"] = "database"
        else:
            # 画像未指定時はデフォルト画像を利用
            if self.default_image_path and Path(self.default_image_path).exists():
                post_logger.info(f"🖼️ デフォルト画像を使用: {self.default_image_path}")
                video["image_filename"] = str(self.default_image_path)
                video["image_source"] = "default"
            elif self.default_image_path:
                post_logger.warning(f"⚠️ デフォルト画像が見つかりません: {self.default_image_path}")
        # 最終的に minimal_poster で投稿
        return self.minimal_poster.post_video_minimal(video)

    def is_available(self) -> bool:
        # minimal_posterの認証状態で判定（DRY RUN時は常にTrue）
        if self.minimal_poster.dry_run:
            return True
        return self.minimal_poster.access_token is not None and self.minimal_poster.did is not None

    def get_name(self) -> str:
        return "Bluesky 機能拡張プラグイン"

    def get_version(self) -> str:
        return "1.1.0"

    def get_description(self) -> str:
        return "Bluesky への画像添付と投稿テンプレート機能を拡張（オプション）"

    def on_enable(self) -> None:
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(
                "🔍 BlueskyPlugin on_enable: dry_run=%s, token=%s, did=%s",
                self.minimal_poster.dry_run,
                bool(getattr(self.minimal_poster, "access_token", None)),
                bool(getattr(self.minimal_poster, "did", None)),
            )
        # プラグイン有効化のINFOログはPluginManager側で出力するため、ここではDEBUGのみ

    def on_disable(self) -> None:
        logger.info(f"⛔ プラグイン無効化: {self.get_name()}")

    # ============ 画像アップロード機能（拡張機能） ============
    
    def _upload_blob(self, file_path: str) -> dict:
        """
        画像をBlob としてアップロード
        
        Bluesky API: com.atproto.repo.uploadBlob
        参照: https://docs.bsky.app/docs/api/com-atproto-repo-upload-blob
        
        Args:
            file_path: 画像ファイルパス
            
        Returns:
            blob メタデータ、失敗時は None
        """
        try:
            if not Path(file_path).exists():
                post_logger.warning(f"⚠️ 画像ファイルが見つかりません: {file_path}")
                return None
            
            with open(file_path, 'rb') as f:
                image_data = f.read()
            
            # ファイルサイズチェック（1MB = 1,000,000 バイト）
            if len(image_data) > 1_000_000:
                post_logger.warning(f"⚠️ 画像ファイルが大きすぎます: {len(image_data)} bytes > 1MB")
                return None
            
            # MIME タイプを判定
            mime_type = self._get_mime_type(file_path)
            
            upload_url = "https://bsky.social/xrpc/com.atproto.repo.uploadBlob"
            headers = {
                "Authorization": f"Bearer {self.minimal_poster.access_token}",
                "Content-Type": mime_type
            }
            
            import requests
            response = requests.post(upload_url, data=image_data, headers=headers, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            blob = result.get("blob")
            
            if blob:
                post_logger.info(f"✅ 画像アップロード成功: {blob.get('mimeType')} ({len(image_data)} bytes)")
                return blob
            else:
                post_logger.warning(f"⚠️ Blob メタデータが返されませんでした")
                return None
                
        except Exception as e:
            post_logger.warning(f"⚠️ 画像アップロード失敗: {e}")
            return None
    
    def _get_mime_type(self, file_path: str) -> str:
        """ファイル拡張子から MIME タイプを判定"""
        ext = Path(file_path).suffix.lower()
        mime_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.webp': 'image/webp',
            '.gif': 'image/gif',
        }
        return mime_types.get(ext, 'image/jpeg')  # デフォルトは JPEG
    
    def _download_image(self, url: str) -> str:
        """
        URL から画像をダウンロード
        
        Args:
            url: 画像 URL
            
        Returns:
            ダウンロードしたファイルパス、失敗時は None
        """
        try:
            import tempfile
            import requests
            
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            # ファイルサイズチェック
            if len(response.content) > 1_000_000:
                post_logger.warning(f"⚠️ ダウンロード画像が大きすぎます: {len(response.content)} bytes")
                return None
            
            # 拡張子を URL から推定
            from urllib.parse import urlparse
            parsed = urlparse(url)
            path = parsed.path
            
            # クエリ文字列を削除
            if '?' in url:
                path = url.split('?')[0]
            
            ext = Path(path).suffix or '.jpg'
            
            # 一時ファイルに保存
            with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
                tmp.write(response.content)
                tmp_path = tmp.name
            
            post_logger.info(f"✅ 画像ダウンロード成功: {len(response.content)} bytes")
            return tmp_path
            
        except Exception as e:
            post_logger.warning(f"⚠️ 画像ダウンロード失敗: {e}")
            return None

    # ============ 画像取得・テンプレート機能 ============
    
    # 画像取得は ImageManager に委譲（後方互換性のため残す）
    def _get_image_bytes(self, site: str = None, mode: str = None, filename: str = None, url: str = None) -> bytes:
        """画像データを取得（ImageManagerを使用）"""
        return self.image_manager.get_image_bytes(site=site, mode=mode, filename=filename, url=url)

    # ============ テンプレート機能 ============
    
    def _render_template(self, template_path: str, context: dict) -> str:
        """Jinja2 テンプレートをレンダリング"""
        try:
            from jinja2 import Environment
            from utils_v2 import format_datetime_filter
            with open(template_path, encoding="utf-8") as f:
                template_str = f.read()
            env = Environment()
            env.filters['datetimeformat'] = format_datetime_filter
            template = env.from_string(template_str)
            return template.render(**context)
        except Exception as e:
            logger.error(f"❌ テンプレートレンダリング失敗: {e}")
            return ""


def get_bluesky_plugin(username: str, password: str, dry_run: bool = False) -> BlueskyImagePlugin:
    """Bluesky 画像添付拡張プラグインを取得"""
    return BlueskyImagePlugin(username, password, dry_run)
