# -*- coding: utf-8 -*-

"""
Asset ディレクトリからのテンプレート・画像自動配置マネージャー

プラグイン導入時に Asset/ ディレクトリから本番ディレクトリへ
テンプレート・画像ファイルを自動コピーする機能を提供。
"""

import os
import shutil
import logging
from pathlib import Path

logger = logging.getLogger("AppLogger")

__author__ = "mayuneco(mayunya)"
__copyright__ = "Copyright (C) 2025 mayuneco(mayunya)"
__license__ = "GPLv2"


class AssetManager:
    """Asset ディレクトリからファイルを自動配置"""

    def __init__(self, asset_dir="Asset", base_dir="."):
        """
        初期化

        Args:
            asset_dir: Asset ディレクトリの相対パス（デフォルト: "Asset"）
            base_dir: ベースディレクトリ（デフォルト: "."）
        """
        self.asset_dir = Path(base_dir) / asset_dir
        self.base_dir = Path(base_dir)
        self.templates_src = self.asset_dir / "templates"
        self.images_src = self.asset_dir / "images"
        self.templates_dest = self.base_dir / "templates"
        self.images_dest = self.base_dir / "images"

    def _ensure_dest_dir(self, dest_path: Path) -> bool:
        """宛先ディレクトリが存在するか確認、なければ作成"""
        try:
            if not dest_path.exists():
                dest_path.mkdir(parents=True, exist_ok=True)
                logger.debug(f"ディレクトリを作成しました: {dest_path}")
            return True
        except Exception as e:
            logger.warning(f"ディレクトリ作成失敗 {dest_path}: {e}")
            return False

    def _copy_file(self, src: Path, dest: Path) -> bool:
        """ファイルをコピー（既存ファイルは上書きしない）"""
        try:
            if dest.exists():
                logger.debug(f"既に存在するため、スキップしました: {dest}")
                return True

            self._ensure_dest_dir(dest.parent)
            shutil.copy2(src, dest)
            logger.info(f"✅ ファイルをコピーしました: {src.name} -> {dest}")
            return True
        except Exception as e:
            logger.warning(f"ファイルコピー失敗 {src} -> {dest}: {e}")
            return False

    def _copy_directory_recursive(self, src_dir: Path, dest_dir: Path) -> int:
        """ディレクトリ内のファイルを再帰的にコピー"""
        copy_count = 0
        try:
            if not src_dir.exists():
                logger.debug(f"ソースディレクトリが存在しません: {src_dir}")
                return 0

            for item in src_dir.rglob("*"):
                if item.is_file():
                    # ソースからの相対パスを計算
                    rel_path = item.relative_to(src_dir)
                    dest_file = dest_dir / rel_path

                    if self._copy_file(item, dest_file):
                        copy_count += 1
        except Exception as e:
            logger.warning(f"ディレクトリコピー失敗 {src_dir} -> {dest_dir}: {e}")

        return copy_count

    def deploy_templates(self, services: list = None) -> int:
        """
        テンプレートをコピー
        
        Asset/templates/ は既に小文字で正規化されているため、
        そのまま対応するディレクトリにコピーします

        Args:
            services: コピー対象のサービス一覧（None = すべて）
                     例: ["youtube", "niconico"]

        Returns:
            コピーしたファイル数
        """
        logger.info("📋 テンプレートの配置を開始します...")
        copy_count = 0

        if services is None:
            # すべてのサービスをコピー
            services = []
            if self.templates_src.exists():
                services = [d.name for d in self.templates_src.iterdir() if d.is_dir()]

        for service in services:
            src_service_dir = self.templates_src / service
            # Asset と v2 テンプレート両方とも小文字で統一済み
            dest_service_dir = self.templates_dest / service

            if not src_service_dir.exists():
                logger.debug(f"テンプレートディレクトリが見つかりません: {src_service_dir}")
                continue

            count = self._copy_directory_recursive(src_service_dir, dest_service_dir)
            copy_count += count
            if count > 0:
                logger.info(f"✅ [{service}] {count} 個のテンプレートをコピーしました")

        if copy_count == 0:
            logger.debug("テンプレートのコピー対象がありません")

        return copy_count

    def deploy_images(self, services: list = None) -> int:
        """
        画像をコピー
        
        Asset と v2 両方とも大文字始まりで統一されています：
        - default/ (小文字のまま)
        - YouTube/, Niconico/, Twitch/ (大文字始まり)

        Args:
            services: コピー対象のサービス一覧（None = すべて）
                     例: ["default", "YouTube"]

        Returns:
            コピーしたファイル数
        """
        logger.info("🖼️  画像の配置を開始します...")
        copy_count = 0

        if services is None:
            # すべてのサービスをコピー
            services = []
            if self.images_src.exists():
                services = [d.name for d in self.images_src.iterdir() if d.is_dir()]

        for service in services:
            src_service_dir = self.images_src / service
            # Asset と v2 の両方で同じ大文字始まりのディレクトリ名を使用
            dest_service_dir = self.images_dest / service

            if not src_service_dir.exists():
                logger.debug(f"画像ディレクトリが見つかりません: {src_service_dir}")
                continue

            count = self._copy_directory_recursive(src_service_dir, dest_service_dir)
            copy_count += count
            if count > 0:
                logger.info(f"✅ [{service}] {count} 個の画像をコピーしました")

        if copy_count == 0:
            logger.debug("画像のコピー対象がありません")

        return copy_count

    def deploy_plugin_assets(self, plugin_name: str) -> dict:
        """
        プラグイン導入時に必要なアセットをコピー

        Args:
            plugin_name: プラグイン名（例: "youtube_live_plugin", "niconico_plugin"）

        Returns:
            {"templates": コピーしたテンプレート数, "images": コピーした画像数}
        """
        logger.info(f"🔌 プラグイン '{plugin_name}' のアセット配置を開始します...")

        results = {"templates": 0, "images": 0}

        # プラグイン別のマッピング定義
        plugin_asset_map = {
            "youtube_live_plugin": {
                "templates": ["youtube"],
                "images": ["youtube"],
            },
            "niconico_plugin": {
                "templates": ["niconico"],
                "images": ["niconico"],
            },
            "bluesky_plugin": {
                "templates": ["default"],
                "images": ["default"],
            },
            "youtube_api_plugin": {
                "templates": ["youtube"],
                "images": ["youtube"],
            },
        }

        if plugin_name not in plugin_asset_map:
            logger.debug(f"プラグイン '{plugin_name}' はアセット定義を持ちません")
            return results

        config = plugin_asset_map[plugin_name]

        # テンプレートをコピー
        if "templates" in config and config["templates"]:
            results["templates"] = self.deploy_templates(config["templates"])

        # 画像をコピー
        if "images" in config and config["images"]:
            results["images"] = self.deploy_images(config["images"])

        total = results["templates"] + results["images"]
        if total > 0:
            logger.info(
                f"✅ プラグイン '{plugin_name}' の {total} 個のアセットを配置しました"
            )
        else:
            logger.debug(f"プラグイン '{plugin_name}' はアセットがありません")

        return results

    def deploy_all(self) -> dict:
        """
        すべてのテンプレート・画像をコピー

        Returns:
            {"templates": コピーしたテンプレート数, "images": コピーした画像数}
        """
        logger.info("🚀 すべてのアセットを配置しています...")

        templates_count = self.deploy_templates()
        images_count = self.deploy_images()

        logger.info(
            f"✅ アセット配置完了: テンプレート {templates_count} 個、画像 {images_count} 個"
        )

        return {"templates": templates_count, "images": images_count}


def get_asset_manager(asset_dir="Asset", base_dir=".") -> AssetManager:
    """AssetManager インスタンスを取得"""
    return AssetManager(asset_dir=asset_dir, base_dir=base_dir)
