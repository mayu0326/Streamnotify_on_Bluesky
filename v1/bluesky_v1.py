# -*- coding: utf-8 -*-

"""
YouTube Notifier on Bluesky - v1 Bluesky プラグイン

Bluesky へのポスト機能を提供。
Rich Text フォーマットで URL をリンク化。
"""

import logging
import re

logger = logging.getLogger("AppLogger")

__author__ = "mayuneco(mayunya)"
__copyright__ = "Copyright (C) 2025 mayuneco(mayunya)"
__license__ = "GPLv2"


class BlueskyPlugin:
    """Bluesky に投稿するプラグイン"""

    def __init__(self, username: str, password: str, dry_run: bool = False):
        """
        初期化

        Args:
            username: Bluesky ユーザー名（@xxx.bsky.social）
            password: Bluesky アプリパスワード
            dry_run: ドライラン（実際には投稿しない）
        """
        self.username = username
        self.password = password
        self.dry_run = dry_run
        self.client = None

        if dry_run:
            logger.info("🧪 BlueskyPlugin は DRY RUN モードで動作します。実際には投稿しません。")
        else:
            self._login()

    def _login(self):
        """Bluesky にログイン"""
        try:
            from atproto import Client

            self.client = Client()
            self.client.login(self.username, self.password)
            logger.info(f"✅ Bluesky にログインしました: {self.username}")
        except ImportError as e:
            logger.error(f"❌ atproto ライブラリのインポート失敗: {e}")
            logger.error("   以下を実行してください: pip install --upgrade atproto")
            raise
        except Exception as e:
            logger.error(f"❌ Bluesky ログイン失敗: {e}")
            raise

    def _find_urls_with_byte_positions(self, text: str) -> list:
        """
        テキストから URL を抽出（バイト位置を正確に計算）

        Args:
            text: テキスト

        Returns:
            [{'url': url, 'byte_start': int, 'byte_end': int}, ...]
        """
        pattern = r'https?://[^\s]+'
        urls = []

        for match in re.finditer(pattern, text):
            # バイト位置を計算（UTF-8）
            byte_start = len(text[:match.start()].encode('utf-8'))
            byte_end = len(text[:match.end()].encode('utf-8'))

            urls.append({
                'url': match.group(),
                'byte_start': byte_start,
                'byte_end': byte_end,
                'char_start': match.start(),
                'char_end': match.end()
            })

            logger.info(f"  🔗 URL 検出: {match.group()}")
            logger.info(f"     バイト位置: {byte_start:3d} - {byte_end:3d}")
            logger.info(f"     文字位置: {match.start():3d} - {match.end():3d}")

        return urls

    def _build_facets(self, text: str) -> list:
        """
        Facet リストを構築（URL をリンク化）

        Args:
            text: ポスト本文

        Returns:
            Facet のリスト
        """
        try:
            from atproto.models.com.atproto.richtext import Facet
            from atproto.models.com.atproto.richtext.facet import Link
        except ImportError as e:
            logger.error(f"❌ Rich Text モジュール取得失敗: {e}")
            logger.error("   atproto のバージョンを確認してください: pip show atproto")
            return None

        urls = self._find_urls_with_byte_positions(text)

        if not urls:
            logger.info("  📍 URL が見つかりませんでした")
            return None

        facets = []

        for url_info in urls:
            try:
                # Facet を構築
                # 重要: byteStart と byteEnd は UTF-8 バイトオフセット
                facet = Facet(
                    index={
                        'byteStart': url_info['byte_start'],
                        'byteEnd': url_info['byte_end']
                    },
                    features=[
                        Link(uri=url_info['url'])
                    ]
                )
                facets.append(facet)
                logger.info(f"  ✅ Facet 作成: bytes {url_info['byte_start']}-{url_info['byte_end']} → {url_info['url']}")
            except Exception as e:
                logger.error(f"  ❌ Facet 作成失敗: {e}")
                continue

        return facets if facets else None

    def post_video(self, video: dict) -> bool:
        """
        動画をポスト（URL をリンク化）

        Args:
            video: 動画情報
                - title: 動画タイトル
                - video_url: 動画 URL
                - published_at: 公開日時
                - channel_name: チャンネル名

        Returns:
            True: 成功、False: 失敗
        """
        try:
            title = video.get("title", "【新着動画】")
            video_url = video.get("video_url", "")
            channel_name = video.get("channel_name", "")
            published_at = video.get("published_at", "")

            if not video_url:
                logger.error("❌ video_url が見つかりません")
                return False

            # ポスト本文を構成（Bluesky は 300 文字制限）
            post_text = f"{title}\n\n🎬 {channel_name}\n📅 {published_at[:10]}\n\n{video_url}"

            logger.info(f"投稿内容:\n{post_text}")
            logger.info(f"文字数: {len(post_text)} / 300")
            logger.info(f"バイト数: {len(post_text.encode('utf-8'))}")

            if self.dry_run:
                logger.info(f"[DRY RUN] Bluesky ポスト\n{post_text}")
                return True

            # 実際に投稿
            if not self.client:
                logger.error("❌ Bluesky クライアントが初期化されていません")
                return False

            try:
                # Facet を構築してリンク化
                logger.info("📍 Facet を構築しています...")
                facets = self._build_facets(post_text)

                if facets:
                    logger.info(f"📍 投稿: text={len(post_text)} 文字, facets={len(facets)} 個")
                    logger.info(f"   詳細: {[f.index for f in facets]}")

                    # AT Protocol の仕様に従って送信
                    response = self.client.send_post(
                        text=post_text,
                        facets=facets
                    )
                    logger.info(f"✅ Bluesky に投稿しました（リンク化）: {video_url}")
                else:
                    logger.warning("⚠️ Facet なしで投稿します")
                    response = self.client.send_post(text=post_text)
                    logger.info(f"✅ Bluesky に投稿しました（リンクなし）: {video_url}")

                return True

            except TypeError as e:
                logger.error(f"❌ send_post() パラメータエラー: {e}")
                logger.error("   atproto のバージョンが古い可能性があります")
                logger.error("   実行: pip install --upgrade atproto")
                return False
            except Exception as e:
                logger.error(f"❌ Bluesky API エラー: {e}", exc_info=True)
                return False

        except Exception as e:
            logger.error(f"投稿処理中にエラーが発生しました: {e}", exc_info=True)
            return False


def get_bluesky_plugin(username: str, password: str, dry_run: bool = False) -> BlueskyPlugin:
    """Bluesky プラグインを取得"""
    return BlueskyPlugin(username, password, dry_run)
