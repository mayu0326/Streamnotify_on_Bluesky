# -*- coding: utf-8 -*-

"""
Stream notify on Bluesky - v3 バックアップ・復元管理

DB・テンプレート・設定を ZIP 形式で一括エクスポート/インポート
"""

import os
import shutil
import logging
import zipfile
from pathlib import Path
from datetime import datetime
from typing import Dict, Tuple

logger = logging.getLogger("AppLogger")

__author__ = "mayuneco(mayunya)"
__copyright__ = "Copyright (C) 2025 mayuneco(mayunya)"
__license__ = "GPLv3"


class BackupManager:
    """バックアップ・復元を管理するクラス"""

    def __init__(self, base_dir="."):
        """
        初期化

        Args:
            base_dir: アプリケーションベースディレクトリ
        """
        self.base_dir = Path(base_dir)
        self.db_path = self.base_dir / "data" / "video_list.db"
        self.templates_dir = self.base_dir / "templates"
        self.settings_file = self.base_dir / "settings.env"
        self.youtube_cache_file = self.base_dir / "data" / "youtube_video_detail_cache.json"
        self.deleted_videos_file = self.base_dir / "data" / "deleted_videos.json"
        self.images_dir = self.base_dir / "images"

    def create_backup(
        self,
        backup_file: str,
        include_api_keys: bool = False,
        include_passwords: bool = False,
        include_images: bool = False
    ) -> Tuple[bool, str]:
        """
        バックアップを作成（DB + テンプレート + 設定を ZIP に圧縮）

        Args:
            backup_file: 保存先ファイルパス（.zip）
            include_api_keys: settings.env に API キーを含めるか
            include_passwords: settings.env にパスワードを含めるか
            include_images: images/ フォルダを含めるか

        Returns:
            (成功フラグ, メッセージ)
        """
        try:
            backup_path = Path(backup_file)

            # バックアップディレクトリが存在しない場合は作成
            backup_path.parent.mkdir(parents=True, exist_ok=True)

            logger.info(f"🔄 バックアップを作成しています: {backup_file}")

            # タイムスタンプを一度だけ生成（全ファイルで統一）
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_prefix = f"backup_{timestamp}"

            with zipfile.ZipFile(backup_path, "w", zipfile.ZIP_DEFLATED) as zf:
                # DB をバックアップ
                if self.db_path.exists():
                    arcname = f"{backup_prefix}/data/video_list.db"
                    zf.write(self.db_path, arcname=arcname)
                    logger.debug(f"✅ DB をバックアップ: {self.db_path}")
                else:
                    logger.warning(f"⚠️ DB ファイルが見つかりません: {self.db_path}")

                # YouTube キャッシュをバックアップ
                if self.youtube_cache_file.exists():
                    arcname = f"{backup_prefix}/data/youtube_video_detail_cache.json"
                    zf.write(self.youtube_cache_file, arcname=arcname)
                    logger.debug(f"✅ YouTube キャッシュをバックアップ: {self.youtube_cache_file}")
                else:
                    logger.warning(f"⚠️ YouTube キャッシュファイルが見つかりません: {self.youtube_cache_file}")

                # 削除済み動画リストをバックアップ
                if self.deleted_videos_file.exists():
                    arcname = f"{backup_prefix}/data/deleted_videos.json"
                    zf.write(self.deleted_videos_file, arcname=arcname)
                    logger.debug(f"✅ 削除済み動画リストをバックアップ: {self.deleted_videos_file}")
                else:
                    logger.warning(f"⚠️ 削除済み動画リストが見つかりません: {self.deleted_videos_file}")

                # テンプレートをバックアップ
                if self.templates_dir.exists():
                    for template_file in self.templates_dir.rglob("*"):
                        if template_file.is_file():
                            rel_path = template_file.relative_to(self.base_dir)
                            arcname = f"{backup_prefix}/{rel_path}"
                            zf.write(template_file, arcname=arcname)
                    logger.debug(f"✅ テンプレートをバックアップ: {self.templates_dir}")
                else:
                    logger.warning(f"⚠️ テンプレートディレクトリが見つかりません: {self.templates_dir}")

                # settings.env をバックアップ（オプション）
                if self.settings_file.exists():
                    settings_content = self._prepare_settings_for_backup(
                        include_api_keys=include_api_keys,
                        include_passwords=include_passwords
                    )
                    arcname = f"{backup_prefix}/settings.env"
                    zf.writestr(arcname, settings_content)
                    logger.debug(f"✅ 設定ファイルをバックアップ: {self.settings_file}")
                else:
                    logger.warning(f"⚠️ 設定ファイルが見つかりません: {self.settings_file}")

                # images/ フォルダをバックアップ（オプション）
                if include_images and self.images_dir.exists():
                    for image_file in self.images_dir.rglob("*"):
                        if image_file.is_file():
                            rel_path = image_file.relative_to(self.base_dir)
                            arcname = f"{backup_prefix}/{rel_path}"
                            zf.write(image_file, arcname=arcname)
                    logger.debug(f"✅ 画像フォルダをバックアップ: {self.images_dir}")
                elif include_images:
                    logger.warning(f"⚠️ 画像ディレクトリが見つかりません: {self.images_dir}")

            backup_size_mb = backup_path.stat().st_size / (1024 * 1024)
            logger.info(f"✅ バックアップ作成完了: {backup_file} ({backup_size_mb:.2f} MB)")

            return True, f"バックアップを作成しました\n\nファイル: {backup_file}\nサイズ: {backup_size_mb:.2f} MB"

        except Exception as e:
            logger.error(f"❌ バックアップ作成に失敗: {e}")
            return False, f"バックアップ作成に失敗しました:\n{e}"

    def restore_backup(self, backup_file: str) -> Tuple[bool, str]:
        """
        バックアップから復元

        Args:
            backup_file: バックアップファイルパス（.zip）

        Returns:
            (成功フラグ, メッセージ)
        """
        try:
            backup_path = Path(backup_file)

            if not backup_path.exists():
                logger.error(f"❌ バックアップファイルが見つかりません: {backup_file}")
                return False, f"バックアップファイルが見つかりません:\n{backup_file}"

            if not zipfile.is_zipfile(backup_path):
                logger.error(f"❌ 無効な ZIP ファイル: {backup_file}")
                return False, f"無効な ZIP ファイルです:\n{backup_file}"

            logger.info(f"🔄 バックアップから復元しています: {backup_file}")

            # 復元用の一時ディレクトリ
            temp_dir = self.base_dir / ".backup_restore_temp"
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
            temp_dir.mkdir(parents=True, exist_ok=True)

            # ZIP を解凍
            with zipfile.ZipFile(backup_path, "r") as zf:
                zf.extractall(temp_dir)
                logger.debug(f"✅ ZIP を解凍: {temp_dir}")

            # 復元対象ディレクトリを特定（backup_YYYYMMdd_HHMMSS/ のような形式）
            backup_dirs = [d for d in temp_dir.iterdir() if d.is_dir() and d.name.startswith("backup_")]

            if not backup_dirs:
                logger.error(f"❌ バックアップディレクトリが見つかりません")
                shutil.rmtree(temp_dir)
                return False, "バックアップファイルの形式が無効です"

            backup_restore_dir = backup_dirs[0]

            # DB を復元
            db_backup = backup_restore_dir / "data" / "video_list.db"
            if db_backup.exists():
                self.db_path.parent.mkdir(parents=True, exist_ok=True)

                # 既存 DB をバックアップ
                if self.db_path.exists():
                    backup_db = self.db_path.parent / f"video_list.db.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    shutil.copy2(self.db_path, backup_db)
                    logger.debug(f"✅ 既存 DB をバックアップ: {backup_db}")

                shutil.copy2(db_backup, self.db_path)
                logger.debug(f"✅ DB を復元: {self.db_path}")
            else:
                logger.warning(f"⚠️ バックアップに DB が含まれていません")

            # YouTube キャッシュを復元
            youtube_cache_backup = backup_restore_dir / "data" / "youtube_video_detail_cache.json"
            if youtube_cache_backup.exists():
                self.youtube_cache_file.parent.mkdir(parents=True, exist_ok=True)

                # 既存キャッシュをバックアップ
                if self.youtube_cache_file.exists():
                    backup_cache = self.youtube_cache_file.parent / f"youtube_video_detail_cache.json.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    shutil.copy2(self.youtube_cache_file, backup_cache)
                    logger.debug(f"✅ 既存 YouTube キャッシュをバックアップ: {backup_cache}")

                shutil.copy2(youtube_cache_backup, self.youtube_cache_file)
                logger.debug(f"✅ YouTube キャッシュを復元: {self.youtube_cache_file}")
            else:
                logger.warning(f"⚠️ バックアップに YouTube キャッシュが含まれていません")

            # 削除済み動画リストを復元
            deleted_videos_backup = backup_restore_dir / "data" / "deleted_videos.json"
            if deleted_videos_backup.exists():
                self.deleted_videos_file.parent.mkdir(parents=True, exist_ok=True)

                # 既存リストをバックアップ
                if self.deleted_videos_file.exists():
                    backup_deleted = self.deleted_videos_file.parent / f"deleted_videos.json.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    shutil.copy2(self.deleted_videos_file, backup_deleted)
                    logger.debug(f"✅ 既存削除済み動画リストをバックアップ: {backup_deleted}")

                shutil.copy2(deleted_videos_backup, self.deleted_videos_file)
                logger.debug(f"✅ 削除済み動画リストを復元: {self.deleted_videos_file}")
            else:
                logger.warning(f"⚠️ バックアップに削除済み動画リストが含まれていません")

            # テンプレートを復元
            templates_backup = backup_restore_dir / "templates"
            if templates_backup.exists():
                if self.templates_dir.exists():
                    backup_templates = self.base_dir / f"templates.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    shutil.move(str(self.templates_dir), str(backup_templates))
                    logger.debug(f"✅ 既存テンプレートをバックアップ: {backup_templates}")

                shutil.copytree(templates_backup, self.templates_dir)
                logger.debug(f"✅ テンプレートを復元: {self.templates_dir}")
            else:
                logger.warning(f"⚠️ バックアップにテンプレートが含まれていません")

            # settings.env を復元
            settings_backup = backup_restore_dir / "settings.env"
            if settings_backup.exists():
                if self.settings_file.exists():
                    backup_settings = self.base_dir / f"settings.env.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    shutil.copy2(self.settings_file, backup_settings)
                    logger.debug(f"✅ 既存設定ファイルをバックアップ: {backup_settings}")

                shutil.copy2(settings_backup, self.settings_file)
                logger.debug(f"✅ 設定ファイルを復元: {self.settings_file}")
            else:
                logger.warning(f"⚠️ バックアップに設定ファイルが含まれていません")

            # images/ フォルダを復元（存在する場合）
            images_backup = backup_restore_dir / "images"
            if images_backup.exists():
                if self.images_dir.exists():
                    backup_images = self.base_dir / f"images.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    shutil.move(str(self.images_dir), str(backup_images))
                    logger.debug(f"✅ 既存画像フォルダをバックアップ: {backup_images}")

                shutil.copytree(images_backup, self.images_dir)
                logger.debug(f"✅ 画像フォルダを復元: {self.images_dir}")
            else:
                logger.debug(f"ℹ️ バックアップに画像フォルダが含まれていません")

            # 一時ディレクトリをクリーンアップ
            shutil.rmtree(temp_dir)

            logger.info(f"✅ バックアップから復元完了")
            return True, "バックアップから復元しました\n\n⚠️ アプリケーションを再起動してください"

        except Exception as e:
            logger.error(f"❌ バックアップ復元に失敗: {e}")
            return False, f"バックアップ復元に失敗しました:\n{e}"

    def _prepare_settings_for_backup(
        self,
        include_api_keys: bool = False,
        include_passwords: bool = False
    ) -> str:
        """
        settings.env を バックアップ用に準備（機密情報除外オプション）

        Args:
            include_api_keys: API キーを含めるか
            include_passwords: パスワードを含めるか

        Returns:
            処理済み settings.env の内容
        """
        try:
            with open(self.settings_file, "r", encoding="utf-8") as f:
                content = f.read()

            lines = []
            for line in content.split("\n"):
                # コメント行はそのまま
                if line.strip().startswith("#"):
                    lines.append(line)
                    continue

                # 空行はそのまま
                if not line.strip():
                    lines.append(line)
                    continue

                # 機密情報をチェック＆除外
                if "=" in line:
                    key, value = line.split("=", 1)
                    key_upper = key.strip().upper()

                    # API キーを除外（YouTubeチャンネルID・ニコニコユーザーID・Twitchキー含む）
                    if not include_api_keys:
                        if any(k in key_upper for k in ["API_KEY", "CLIENT_ID", "CLIENT_SECRET", "YOUTUBE_API_KEY", "YOUTUBE_CHANNEL_ID", "NICONICO_USER_ID", "TWITCH_CLIENT_ID", "TWITCH_CLIENT_SECRET", "TWITCH_BROADCASTER"]):
                            lines.append(f"# 【バックアップ時に除外】{key}=")
                            logger.debug(f"  🔐 除外: {key.strip()}")
                            continue

                    # パスワードを除外
                    if not include_passwords:
                        if any(k in key_upper for k in ["PASSWORD", "APP_PASSWORD", "WEBHOOK_SECRET"]):
                            lines.append(f"# 【バックアップ時に除外】{key}=")
                            logger.debug(f"  🔒 除外: {key.strip()}")
                            continue

                lines.append(line)

            result = "\n".join(lines)

            # 除外したものをログに記録
            if not include_api_keys or not include_passwords:
                excluded_count = sum(1 for line in result.split("\n") if "【バックアップ時に除外】" in line)
                if excluded_count > 0:
                    logger.info(f"✅ 設定ファイルから {excluded_count} 個の機密情報を除外しました")

            return result

        except Exception as e:
            logger.warning(f"⚠️ settings.env の処理に失敗: {e}")
            # エラー時は元のコンテンツを返す
            with open(self.settings_file, "r", encoding="utf-8") as f:
                return f.read()


def get_backup_manager(base_dir=".") -> BackupManager:
    """BackupManager インスタンスを取得"""
    return BackupManager(base_dir)
