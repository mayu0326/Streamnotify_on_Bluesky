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

# PIL (Pillow) をインポート
from PIL import Image

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


# ============ 画像リサイズ設定（環境変数から読み込み） ============
def _load_image_resize_config():
    """環境変数から画像リサイズ設定を読み込む

    Returns:
        dict: 画像リサイズ設定
    """
    try:
        config = {
            "target_width": int(get_env_setting("IMAGE_RESIZE_TARGET_WIDTH") or "1280"),
            "target_height": int(get_env_setting("IMAGE_RESIZE_TARGET_HEIGHT") or "800"),
            "quality_initial": int(get_env_setting("IMAGE_OUTPUT_QUALITY_INITIAL") or "90"),
            "size_target": int(get_env_setting("IMAGE_SIZE_TARGET") or "800000"),
            "size_threshold": int(get_env_setting("IMAGE_SIZE_THRESHOLD") or "900000"),
            "size_limit": int(get_env_setting("IMAGE_SIZE_LIMIT") or "1000000"),
        }
        logger.debug(f"🔧 画像リサイズ設定を環境変数から読み込み: {config}")
        return config
    except ValueError as e:
        logger.warning(f"⚠️ 画像リサイズ設定の値が無効: {e}")
        # デフォルト値で返す
        return {
            "target_width": 1280,
            "target_height": 800,
            "quality_initial": 90,
            "size_target": 800_000,
            "size_threshold": 900_000,
            "size_limit": 1_000_000,
        }


# グローバル設定を読み込み
_IMAGE_CONFIG = _load_image_resize_config()

# 定数として再エクスポート（下位互換性維持）
IMAGE_RESIZE_TARGET_WIDTH = _IMAGE_CONFIG["target_width"]
IMAGE_RESIZE_TARGET_HEIGHT = _IMAGE_CONFIG["target_height"]
IMAGE_OUTPUT_QUALITY_INITIAL = _IMAGE_CONFIG["quality_initial"]
IMAGE_SIZE_TARGET = _IMAGE_CONFIG["size_target"]
IMAGE_SIZE_THRESHOLD = _IMAGE_CONFIG["size_threshold"]
IMAGE_SIZE_LIMIT = _IMAGE_CONFIG["size_limit"]


def get_env_setting(key: str, default=None):
    """settings.env から設定値を取得（汎用関数）"""
    try:
        settings_path = Path("settings.env")
        if not settings_path.exists():
            return default
        with open(settings_path, 'r', encoding='utf-8') as f:
            for line in f:
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
        # GUI から use_image フラグが指定されている場合は優先
        use_image = video.get("use_image", True)  # デフォルトは画像添付
        resize_small_images = video.get("resize_small_images", True)  # デフォルトはリサイズ有効

        post_logger.info(f"🔍 post_video 開始: use_image={use_image}, resize_small_images={resize_small_images}, image_filename={video.get('image_filename')}")

        # DBに画像ファイルが登録されている場合、そのファイルを優先して使用
        image_filename = video.get("image_filename")
        image_mode = video.get("image_mode")
        source = video.get("source", "YouTube").lower()
        video = dict(video)  # 元の辞書を変更しないようコピー
        embed = None

        # use_image=False の場合は画像添付を強制的にスキップ
        if not use_image:
            post_logger.info(f"🔗 GUI設定により、リンクカード投稿モード")
            video["use_link_card"] = True
            video["embed"] = None
        elif image_filename and image_filename.strip():
            # ファイル名から完全パスを構築
            image_path = self._resolve_image_path(image_filename, image_mode, source)
            post_logger.info(f"💾 DB登録済み画像を使用: {image_filename}")
            video["image_source"] = "database"
            # 画像ファイルをアップロードして embed を取得
            if image_path and Path(image_path).exists():
                blob = self._upload_blob(image_path, resize_small_images=resize_small_images)
                if blob:
                    embed = self._build_image_embed(blob)
                    post_logger.info(f"✅ 画像埋め込みの準備完了")
            else:
                post_logger.warning(f"⚠️ 画像ファイルが見つかりません: {image_filename} (検索パス: {image_path})")
        else:
            # 画像未指定時はデフォルト画像を利用
            if self.default_image_path and Path(self.default_image_path).exists():
                post_logger.info(f"🖼️ デフォルト画像を使用: {self.default_image_path}")
                video["image_filename"] = str(self.default_image_path)
                video["image_source"] = "default"
                # デフォルト画像をアップロードして embed を取得
                blob = self._upload_blob(str(self.default_image_path), resize_small_images=resize_small_images)
                if blob:
                    embed = self._build_image_embed(blob)
                    post_logger.info(f"✅ デフォルト画像埋め込みの準備完了")
            elif self.default_image_path:
                post_logger.warning(f"⚠️ デフォルト画像が見つかりません: {self.default_image_path}")

        # embed が取得できた場合は video に追加
        if embed:
            video["embed"] = embed
            video["use_link_card"] = False  # 画像を優先（リンクカードは無効化）
            post_logger.info(f"🖼️ 画像埋め込み: {embed}")
        else:
            # 画像がない場合、リンクカード機能を有効化
            video["use_link_card"] = True  # リンクカード機能を有効化
            post_logger.info(f"🔗 リンクカード機能を有効化します（画像なし）")

        # 最終的に minimal_poster で投稿
        post_logger.info(f"📊 最終投稿設定: use_link_card={video.get('use_link_card')}, embed={bool(embed)}")
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

    # ============ ファイルパス解決機能 ============

    def _resolve_image_path(self, image_filename: str, image_mode: str = None, source: str = "youtube") -> str:
        """
        画像ファイル名から完全パスを構築

        Args:
            image_filename: 画像ファイル名（\"video_id.jpg\" など）
            image_mode: 画像モード（\"import\" など）
            source: ソース名（\"youtube\" \"niconico\" など）

        Returns:
            完全パス、見つからない場合は None
        """
        if not image_filename:
            return None

        # ソース名を正規化
        if source.lower() in ("youtube", "yt"):
            site_dir = "YouTube"
        elif source.lower() in ("niconico", "nico"):
            site_dir = "Niconico"
        elif source.lower() == "twitch":
            site_dir = "Twitch"
        else:
            site_dir = "YouTube"

        # モードを正規化（デフォルトは \"import\"）
        if not image_mode:
            image_mode = "import"

        # パスを構築
        base_path = Path("images") / site_dir / image_mode / image_filename
        return str(base_path)

    # ============ 画像アップロード機能（拡張機能） ============

    def _upload_blob(self, file_path: str, resize_small_images: bool = True) -> dict:
        """
        画像をBlob としてアップロード

        Bluesky API: com.atproto.repo.uploadBlob
        参照: https://docs.bsky.app/docs/api/com-atproto-repo-upload-blob

        処理フロー:
        1. 画像ファイルを読み込む
        2. resize_small_images=True の場合、_resize_image() で自動リサイズ・最適化
        3. resize_small_images=False の場合、元の画像をそのまま使用
        4. Bluesky API にアップロード

        Args:
            file_path: 画像ファイルパス
            resize_small_images: 画像をリサイズするか（Falseの場合はオリジナル画像を使用）

        Returns:
            blob メタデータ、失敗時は None
        """
        try:
            # DRY RUN モード時はダミーの blob を返す
            if self.dry_run:
                post_logger.info(f"🧪 [DRY RUN] 画像アップロード（スキップ）: {file_path}")
                return {
                    "$type": "blob",
                    "mimeType": "image/jpeg",
                    "size": 1000,
                    "link": {"$link": "bafkreidummy"}
                }

            if not Path(file_path).exists():
                post_logger.warning(f"⚠️ 画像ファイルが見つかりません: {file_path}")
                return None

            # ========== 画像処理 ==========
            if resize_small_images:
                # リサイズして最適化
                post_logger.info(f"📏 画像をリサイズして最適化します")
                image_data = self._resize_image(file_path)
                if image_data is None:
                    # リサイズ失敗 → この投稿では画像添付をスキップ
                    post_logger.warning(f"⚠️ 画像リサイズ失敗のため、この投稿では画像添付をスキップします")
                    return None
                mime_type = 'image/jpeg'
            else:
                # オリジナル画像をそのまま使用
                post_logger.info(f"📷 オリジナル画像をそのまま使用します（リサイズなし）")
                with open(file_path, 'rb') as f:
                    image_data = f.read()

                # MIME タイプを判定
                from PIL import Image
                try:
                    img = Image.open(file_path)
                    img_format = img.format or "JPEG"
                    mime_type = f'image/{img_format.lower()}'
                except:
                    mime_type = 'image/jpeg'

            # アクセストークンが存在することを確認
            if not self.minimal_poster.access_token:
                post_logger.error(f"❌ Bluesky認証に失敗しています。画像はアップロードできません")
                return None

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

    # ============ 画像リサイズ機能 ============

    def _resize_image(self, file_path: str) -> bytes:
        """
        画像をリサイズして最適化（アスペクト比別処理）

        処理フロー:
        1. 元画像の情報を取得（解像度・フォーマット・ファイルサイズ）
        2. アスペクト比に基づいて3パターンで処理:
           - 横長（幅/高さ ≥ 1.3）: 3:2（1280×800）に寄せて縮小+中央トリミング
           - 正方形〜やや横長（0.8〜1.3）: アスペクト比維持、長辺1280px以下に縮小のみ
           - 縦長（幅/高さ < 0.8）: アスペクト比維持、長辺1280px以下に縮小のみ
        3. JPEG品質90で出力
        4. ファイルサイズ確認 → 900KB超過なら品質低下して再圧縮
        5. 最終的に1MB超過ならNoneを返す（投稿スキップ）

        Args:
            file_path: 画像ファイルパス

        Returns:
            リサイズ・最適化済みの JPEG バイナリ、失敗時は None
        """
        try:
            from PIL import Image
            import io

            if not Path(file_path).exists():
                post_logger.warning(f"⚠️ 画像ファイルが見つかりません: {file_path}")
                return None

            # ========== 元画像の情報取得 ==========
            with open(file_path, 'rb') as f:
                original_data = f.read()
            original_size_bytes = len(original_data)

            img = Image.open(file_path)
            original_width, original_height = img.size
            original_format = img.format or "Unknown"

            aspect_ratio = original_width / original_height if original_height > 0 else 1.0

            post_logger.debug(f"📏 元画像: {original_width}×{original_height} ({original_format}, {original_size_bytes / 1024:.1f}KB, アスペクト比: {aspect_ratio:.2f})")

            # ========== アスペクト比に基づいた処理 ==========
            # 元画像のアスペクト比を維持したまま、長辺が1280以下になるようにリサイズのみ
            # （Blueskyは自動的に適切に表示してくれるため、クロップは行わない）
            resized_img = self._resize_to_max_dimension(img, _IMAGE_CONFIG["target_width"])
            post_logger.debug(f"🔄 アスペクト比維持: 長辺{_IMAGE_CONFIG['target_width']}px以下にリサイズ")

            resized_width, resized_height = resized_img.size
            post_logger.debug(f"   リサイズ後: {resized_width}×{resized_height}")

            # ========== JPEG 出力（初期品質） ==========
            jpeg_data = self._encode_jpeg(resized_img, _IMAGE_CONFIG["quality_initial"])
            current_size_bytes = len(jpeg_data)
            post_logger.debug(f"   JPEG品質{_IMAGE_CONFIG['quality_initial']}: {current_size_bytes / 1024:.1f}KB")

            # ========== ファイルサイズチェック＆品質調整 ==========
            if current_size_bytes > _IMAGE_CONFIG["size_threshold"]:
                # 閾値超過 → 品質を段階的に下げて再圧縮
                post_logger.info(f"⚠️ ファイルサイズが {_IMAGE_CONFIG['size_threshold'] / 1024:.0f}KB を超過: {current_size_bytes / 1024:.1f}KB")
                jpeg_data = self._optimize_image_quality(resized_img, current_size_bytes)

                if jpeg_data is None:
                    post_logger.error(f"❌ ファイルサイズの最適化に失敗しました（{_IMAGE_CONFIG['size_limit']}バイト超過）")
                    return None

                current_size_bytes = len(jpeg_data)

            # ========== 最終チェック ==========
            if current_size_bytes > _IMAGE_CONFIG["size_limit"]:
                post_logger.error(f"❌ 最終的なファイルサイズが上限を超えています: {current_size_bytes / 1024:.1f}KB")
                return None

            # ========== ログ出力 ==========
            post_logger.info(
                f"✅ 画像リサイズ完了: {original_width}×{original_height} ({original_size_bytes / 1024:.1f}KB) "
                f"→ {resized_width}×{resized_height} ({current_size_bytes / 1024:.1f}KB)"
            )

            return jpeg_data

        except Exception as e:
            post_logger.error(f"❌ 画像リサイズ失敗: {e}")
            return None

    def _resize_to_aspect_ratio(self, img, target_width: int, target_height: int):
        """
        アスペクト比を指定値に寄せて縮小+中央トリミング

        ターゲットのアスペクト比に合わせるため、元画像が相対的に横長ならば幅を基準に縮小し、
        縦長ならば高さを基準に縮小してから中央トリミングを行う

        Args:
            img: PIL Image オブジェクト
            target_width: ターゲット幅
            target_height: ターゲット高さ

        Returns:
            トリミング後の PIL Image オブジェクト
        """
        original_width, original_height = img.size

        # ターゲットのアスペクト比
        target_ratio = target_width / target_height

        # 元画像のアスペクト比
        current_ratio = original_width / original_height

        if current_ratio > target_ratio:
            # 元画像がターゲットより横長 → 幅を基準に縮小（高さがターゲット以下になる）
            new_width = target_width
            new_height = int(target_width / current_ratio)
        else:
            # 元画像がターゲットより縦長 → 高さを基準に縮小（幅がターゲット以下になる）
            new_height = target_height
            new_width = int(target_height * current_ratio)

        # 縮小
        img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # 中央トリミング
        left = (new_width - target_width) // 2
        top = (new_height - target_height) // 2
        right = left + target_width
        bottom = top + target_height

        img_cropped = img_resized.crop((left, top, right, bottom))

        return img_cropped

    def _resize_to_max_dimension(self, img, max_dimension: int):
        """
        アスペクト比を維持したまま、長辺が max_dimension 以下になるように縮小

        元画像がターゲットより小さい場合は拡大せずそのまま返す

        Args:
            img: PIL Image オブジェクト
            max_dimension: 最大長辺（ピクセル）

        Returns:
            縮小後（または元のまま）の PIL Image オブジェクト
        """
        width, height = img.size
        max_current = max(width, height)

        if max_current <= max_dimension:
            # 既に小さいので拡大しない
            return img

        # 縮小比を計算
        scale = max_dimension / max_current
        new_width = int(width * scale)
        new_height = int(height * scale)

        img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        return img_resized

    def _encode_jpeg(self, img, quality: int) -> bytes:
        """
        PIL Image を JPEG でエンコードしてバイナリを返す

        Args:
            img: PIL Image オブジェクト
            quality: JPEG品質（1-95）

        Returns:
            JPEG バイナリ
        """
        import io

        # RGBに変換（PNG等のアルファチャネルを削除）
        if img.mode in ('RGBA', 'LA', 'P'):
            # 白背景で合成
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')

        buffer = io.BytesIO()
        img.save(buffer, format='JPEG', quality=quality, optimize=True)
        return buffer.getvalue()

    def _optimize_image_quality(self, img, current_size_bytes: int) -> bytes:
        """
        画像の品質を段階的に下げて再圧縮（ファイルサイズを上限未満に）

        Args:
            img: PIL Image オブジェクト
            current_size_bytes: 現在のバイナリサイズ

        Returns:
            最適化された JPEG バイナリ、失敗時は None
        """
        # 品質を段階的に下げてテスト: 85, 75, 65, 55, 50
        quality_levels = [85, 75, 65, 55, 50]

        for quality in quality_levels:
            jpeg_data = self._encode_jpeg(img, quality)
            size_bytes = len(jpeg_data)

            post_logger.debug(f"   JPEG品質{quality}: {size_bytes / 1024:.1f}KB")

            if size_bytes <= _IMAGE_CONFIG["size_limit"]:
                post_logger.info(f"✅ 品質{quality}で {_IMAGE_CONFIG['size_limit'] / 1024:.0f}KB 以下に圧縮: {size_bytes / 1024:.1f}KB")
                return jpeg_data

        # すべての品質レベルでも上限を超えた
        post_logger.error(f"❌ 品質{quality_levels[-1]}でも {_IMAGE_CONFIG['size_limit'] / 1024:.0f}KB を超えています")
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

    def _build_image_embed(self, blob: dict) -> dict:
        """
        Blob メタデータから画像埋め込み（embed）オブジェクトを構築

        Bluesky API: app.bsky.embed.images
        参照: https://docs.bsky.app/docs/advanced-guides/posts

        Args:
            blob: uploadBlob で返されたメタデータ

        Returns:
            embed オブジェクト
        """
        if not blob:
            return None

        return {
            "$type": "app.bsky.embed.images",
            "images": [
                {
                    "image": blob,
                    "alt": "Posted image"
                }
            ]
        }

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
