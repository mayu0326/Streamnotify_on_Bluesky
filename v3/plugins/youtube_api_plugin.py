# -*- coding: utf-8 -*-
"""
YouTube Data API プラグイン（クォータ対応版）

- UC 以外のチャンネル識別子（ユーザー名/ハンドル）を API で解決・キャッシュ
- 動画詳細取得（ライブ/アーカイブ判定用メタデータ、バッチ対応）
- NotificationPlugin 準拠で DB へ保存
- APIコスト管理: 429対応・レート制限・コスト監視

クォータ仕様（YouTube Data API v3）
- 1日10,000ユニット
- forUsername/channels.list: 1ユニット
- search.list（ハンドル検索）: 100ユニット
- videos.list（詳細取得）: 1ユニット（最大50件/リクエスト）
"""
import os
import logging
import time
import json
from typing import Dict, Any, Optional, Tuple, List
from pathlib import Path
import requests

from plugin_interface import NotificationPlugin
from database import Database
from image_manager import get_youtube_thumbnail_url

logger = logging.getLogger("AppLogger")

API_BASE = "https://www.googleapis.com/youtube/v3"

# キャッシュファイルのパス（絶対パス対応）
_SCRIPT_DIR = Path(__file__).parent.parent  # v3/ ディレクトリ
CHANNEL_ID_CACHE_FILE = str(_SCRIPT_DIR / "data" / "youtube_channel_cache.json")
VIDEO_DETAIL_CACHE_FILE = str(_SCRIPT_DIR / "data" / "youtube_video_detail_cache.json")
CACHE_EXPIRY_DAYS = 7  # キャッシュの有効期限（日数）


class YouTubeAPIPlugin(NotificationPlugin):
    """YouTube Data API 連携プラグイン（クォータ対応）"""

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized') and self._initialized:
            return

        # 設定から読み込み（環境変数の前に config から読み込みを試みる）
        try:
            from config import get_config
            config = get_config("settings.env")
            self.api_key = config.youtube_api_key or os.getenv("YOUTUBE_API_KEY", "")
            self.channel_identifier = config.youtube_channel_id or os.getenv("YOUTUBE_CHANNEL_ID", "")
        except Exception:
            # フォールバック: 環境変数から直接読み込み
            self.api_key = os.getenv("YOUTUBE_API_KEY", "")
            self.channel_identifier = os.getenv("YOUTUBE_CHANNEL_ID", "")

        self.api_key = self.api_key.strip()
        self.channel_identifier = self.channel_identifier.strip()

        self.db = Database()
        self.channel_id: Optional[str] = None
        self.session = requests.Session()

        # APIコスト管理
        self.daily_quota = 10000
        self.daily_cost = 0
        self.last_request_time = 0
        self.request_interval = 0.5  # 秒（リクエスト間最小間隔）

        # ビデオ詳細キャッシュ
        self.video_detail_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_timestamps: Dict[str, float] = {}

        # キャッシュ読み込み
        self._load_channel_cache()
        self._load_video_detail_cache()

        # チャンネルID解決（キャッシュからまず確認）
        if self.api_key and self.channel_identifier:
            self.channel_id = self._resolve_channel_id(self.channel_identifier)
            if self.channel_id:
                # UC形式またはAPIで解決済み
                if self.channel_identifier.startswith("UC"):
                    logger.info(f"✅ YouTube API: UC形式IDのためAPIアクセスは不要です: {self.channel_id}")
                else:
                    logger.info(f"✅ YouTube API: チャンネルIDを解決しました: {self.channel_id}")
            else:
                logger.warning("⚠️ YouTube API: チャンネルIDの解決に失敗しました。UC形式のID、または有効な API キーを確認してください.")
        self._initialized = True

    def is_available(self) -> bool:
        return bool(self.api_key and self.channel_id)

    def get_name(self) -> str:
        return "YouTubeAPI 連携プラグイン"

    def get_version(self) -> str:
        return "0.2.0"

    def get_description(self) -> str:
        return "YouTube Data API でチャンネル解決と動画詳細取得を行うプラグイン（クォータ対応）"

    def post_video(self, video: Dict[str, Any]) -> bool:
        """動画情報を取得し、分類結果付きで DB に保存"""
        video_id = video.get("video_id") or video.get("id")
        if not video_id:
            logger.error("❌ YouTube API: video_id が指定されていません")
            return False

        # YouTube ID 形式の検証（Niconico など他形式のスキップ）
        if not self._is_valid_youtube_video_id(video_id):
            logger.debug(f"⏭️ YouTube API: YouTube 形式ではない video_id をスキップ: {video_id}")
            return True  # エラーではなく「対応不可」として True を返す

        details = self._fetch_video_detail(video_id)
        if not details:
            logger.error(f"❌ YouTube API: 動画詳細取得に失敗しました: {video_id}")
            return False

        content_type, live_status, is_premiere = self._classify_video(details)

        snippet = details.get("snippet", {})
        live_details = details.get("liveStreamingDetails", {})

        title = video.get("title") or snippet.get("title", "【新着動画】")
        channel_name = video.get("channel_name") or snippet.get("channelTitle", "")
        video_url = video.get("video_url") or f"https://www.youtube.com/watch?v={video_id}"

        # ★ 重要修正: published_at を YouTube API から取得
        # Live/Schedule の場合は scheduledStartTime を優先
        # その次に actualStartTime、最後に publishedAt（RSS日時）
        published_at = None
        if live_details.get("scheduledStartTime"):
            published_at = live_details["scheduledStartTime"]
            logger.debug(f"✅ scheduledStartTime を使用: {published_at}")
        elif live_details.get("actualStartTime"):
            published_at = live_details["actualStartTime"]
            logger.debug(f"✅ actualStartTime を使用: {published_at}")
        elif snippet.get("publishedAt"):
            published_at = snippet["publishedAt"]
            logger.debug(f"✅ publishedAt (RSS/API) を使用: {published_at}")
        else:
            published_at = video.get("published_at", "")
            logger.debug(f"⚠️ video.published_at を使用（フォールバック）: {published_at}")

        # サムネイル URL を取得（複数品質から最適なものを選択）
        thumbnail_url = get_youtube_thumbnail_url(video_id)
        if not thumbnail_url:
            # フォールバック: API から取得したもの
            thumbnail_url = snippet.get("thumbnails", {}).get("high", {}).get("url", "")

        return self.db.insert_video(
            video_id=video_id,
            title=title,
            video_url=video_url,
            published_at=published_at,
            channel_name=channel_name,
            thumbnail_url=thumbnail_url,
            content_type=content_type,
            live_status=live_status,
            is_premiere=is_premiere,
        )

    # --- キャッシュ機構 ---
    def _load_channel_cache(self) -> None:
        """チャンネルID解決結果をキャッシュから読み込み"""
        try:
            cache_path = Path(CHANNEL_ID_CACHE_FILE)
            if cache_path.exists():
                with open(cache_path, "r", encoding="utf-8") as f:
                    cache = json.load(f)
                    identifier_key = f"channel_identifier:{self.channel_identifier}"
                    if identifier_key in cache:
                        self.channel_id = cache[identifier_key]
                        logger.info(f"📦 チャンネルIDをキャッシュから読み込みました: {self.channel_id}")
        except Exception as e:
            logger.warning(f"⚠️ チャンネルキャッシュ読み込みエラー: {e}")

    def _save_channel_cache(self) -> None:
        """チャンネルID解決結果をキャッシュに保存"""
        try:
            cache_path = Path(CHANNEL_ID_CACHE_FILE)
            cache_path.parent.mkdir(exist_ok=True)

            cache = {}
            if cache_path.exists():
                with open(cache_path, "r", encoding="utf-8") as f:
                    cache = json.load(f)

            identifier_key = f"channel_identifier:{self.channel_identifier}"
            cache[identifier_key] = self.channel_id

            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(cache, f, ensure_ascii=False, indent=2)

            logger.info(f"💾 チャンネルIDをキャッシュに保存しました")
        except Exception as e:
            logger.error(f"❌ チャンネルキャッシュ保存エラー: {e}")

    # --- ビデオ詳細キャッシュ機構 ---
    def _load_video_detail_cache(self) -> None:
        """ビデオ詳細をキャッシュから読み込み"""
        try:
            cache_path = Path(VIDEO_DETAIL_CACHE_FILE)
            if cache_path.exists():
                with open(cache_path, "r", encoding="utf-8") as f:
                    cache_data = json.load(f)
                    # { video_id: { "data": {...}, "timestamp": 1234567890.0 } }
                    for video_id, entry in cache_data.items():
                        self.video_detail_cache[video_id] = entry.get("data", {})
                        self.cache_timestamps[video_id] = entry.get("timestamp", 0)

                logger.info(f"📦 ビデオ詳細キャッシュを読み込みました: {len(self.video_detail_cache)} 件")
        except Exception as e:
            logger.warning(f"⚠️ ビデオ詳細キャッシュ読み込みエラー: {e}")

    def _save_video_detail_cache(self) -> None:
        """ビデオ詳細キャッシュをファイルに保存"""
        try:
            cache_path = Path(VIDEO_DETAIL_CACHE_FILE)
            cache_path.parent.mkdir(exist_ok=True)

            cache_data = {}
            for video_id, details in self.video_detail_cache.items():
                cache_data[video_id] = {
                    "data": details,
                    "timestamp": self.cache_timestamps.get(video_id, time.time())
                }

            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)

            logger.debug(f"💾 ビデオ詳細キャッシュを保存しました: {len(cache_data)} 件")
        except Exception as e:
            logger.error(f"❌ ビデオ詳細キャッシュ保存エラー: {e}")

    def _is_cache_valid(self, timestamp: float) -> bool:
        """キャッシュの有効性を確認（有効期限チェック）"""
        expiry_seconds = CACHE_EXPIRY_DAYS * 24 * 60 * 60
        return (time.time() - timestamp) < expiry_seconds

    def _get_cached_video_detail(self, video_id: str) -> Optional[Dict[str, Any]]:
        """キャッシュからビデオ詳細を取得（有効期限チェック付き）"""
        if video_id in self.video_detail_cache:
            timestamp = self.cache_timestamps.get(video_id, 0)
            if self._is_cache_valid(timestamp):
                logger.debug(f"📦 キャッシュから取得: {video_id}")
                return self.video_detail_cache[video_id]
            else:
                # 期限切れなので削除
                logger.debug(f"🗑️ キャッシュが期限切れ: {video_id}")
                del self.video_detail_cache[video_id]
                del self.cache_timestamps[video_id]
        return None

    def _cache_video_detail(self, video_id: str, details: Dict[str, Any]) -> None:
        """ビデオ詳細をキャッシュに保存"""
        self.video_detail_cache[video_id] = details
        self.cache_timestamps[video_id] = time.time()

    def update_video_detail_cache(self, video_id: str, video_details: dict):
        """動画詳細キャッシュを更新"""
        self.video_detail_cache[video_id] = video_details
        self.cache_timestamps[video_id] = time.time()
        self._save_video_detail_cache()

    def clear_video_detail_cache(self) -> None:
        """ビデオ詳細キャッシュをクリア"""
        self.video_detail_cache.clear()
        self.cache_timestamps.clear()
        logger.info(f"✅ ビデオ詳細キャッシュをクリアしました")

    # --- レート制限・リクエスト管理 ---
    def _throttle_request(self) -> None:
        """リクエスト間隔を制御（スロットリング）"""
        now = time.time()
        elapsed = now - self.last_request_time
        if elapsed < self.request_interval:
            sleep_time = self.request_interval - elapsed
            logger.debug(f"⏳ API レート制限: {sleep_time:.2f}秒待機")
            time.sleep(sleep_time)
        self.last_request_time = time.time()

    def _check_quota(self, cost: int) -> bool:
        """コスト超過を事前チェック"""
        if self.daily_cost + cost > self.daily_quota:
            logger.error(f"❌ 日次クォータ超過予測: 現在 {self.daily_cost}/{self.daily_quota} ユニット使用済み。"
                         f"追加 {cost} ユニット必要ですが、超過します")
            return False
        return True

    def _record_cost(self, cost: int, operation: str) -> None:
        """APIコストを記録・ログ出力"""
        self.daily_cost += cost
        logger.info(f"💰 API コスト: {operation} = {cost}ユニット (累計: {self.daily_cost}/{self.daily_quota})")

        if self.daily_cost >= self.daily_quota * 0.8:
            logger.warning(f"⚠️ 日次クォータが 80% に到達しました。使用済み: {self.daily_cost}/{self.daily_quota}")

    # --- API通信（エラーハンドリング・バックオフ付き） ---
    def _get(self, path: str, params: Dict[str, Any], expected_cost: int, operation: str, max_retries: int = 3) -> Optional[Dict[str, Any]]:
        """
        API呼び出し（エクスポーネンシャルバックオフ対応）

        Args:
            path: エンドポイント
            params: クエリパラメータ
            expected_cost: 予想コスト（ユニット）
            operation: 操作名（ログ出力用）
            max_retries: リトライ上限

        Returns:
            JSONレスポンス、失敗時は None
        """
        if not self._check_quota(expected_cost):
            return None

        params_with_key = {**params, "key": self.api_key}
        url = f"{API_BASE}/{path}"

        for attempt in range(max_retries):
            try:
                self._throttle_request()

                logger.debug(f"🔌 API リクエスト開始: {operation} (試行 {attempt + 1}/{max_retries})")
                resp = self.session.get(url, params=params_with_key, timeout=15)

                # 429: Over Quota または Rate Limit
                if resp.status_code == 429:
                    retry_after = int(resp.headers.get("Retry-After", 60))
                    logger.warning(f"⏸️ 429 Rate Limit 受信: {retry_after}秒待機後リトライ")

                    if attempt < max_retries - 1:
                        time.sleep(retry_after)
                        continue
                    else:
                        logger.error(f"❌ {operation}: リトライ上限に達しました")
                        return None

                resp.raise_for_status()
                self._record_cost(expected_cost, operation)
                logger.debug(f"✅ API リクエスト成功: {operation}")
                return resp.json()

            except requests.exceptions.Timeout:
                logger.warning(f"⏱️ タイムアウト: {operation} (試行 {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    backoff = 2 ** attempt  # 1, 2, 4秒
                    logger.info(f"⏳ {backoff}秒待機後リトライ...")
                    time.sleep(backoff)
                else:
                    logger.error(f"❌ {operation}: タイムアウトで最終失敗")
                    return None

            except requests.exceptions.RequestException as e:
                logger.error(f"❌ API エラー ({operation}): {e}")
                if attempt < max_retries - 1:
                    backoff = 2 ** attempt
                    logger.info(f"⏳ {backoff}秒待機後リトライ...")
                    time.sleep(backoff)
                else:
                    return None

        return None

    # --- チャンネルID解決 ---
    def _resolve_channel_id(self, identifier: str) -> Optional[str]:
        """
        UC以外のユーザー名/ハンドルを API で UCxx... に解決

        キャッシュ先読み後、forUsername APIで解決・キャッシュ保存
        （search.list は高コストのため未使用）
        """
        if identifier.startswith("UC"):
            return identifier

        # キャッシュから確認
        if self.channel_id:
            return self.channel_id

        logger.info(f"🔍 チャンネルID解決開始: {identifier}")

        # forUsername で解決（1ユニット）
        data = self._get(
            "channels",
            {"part": "id", "forUsername": identifier},
            expected_cost=1,
            operation=f"forUsername: {identifier}"
        )
        if data:
            items = data.get("items", [])
            if items:
                channel_id = items[0].get("id")
                if channel_id:
                    self.channel_id = channel_id
                    self._save_channel_cache()
                    return channel_id

        # forUsername で見つからない場合はエラー（search.list は使用しない）
        logger.error(f"❌ チャンネルID解決失敗: {identifier}（チャンネルIDが正しくありません）")
        return None

    # --- 動画詳細取得 ---
    def _fetch_video_detail(self, video_id: str) -> Optional[Dict[str, Any]]:
        """単一動画の詳細を取得（キャッシュ優先、1ユニット）"""
        # まずキャッシュを確認
        cached = self._get_cached_video_detail(video_id)
        if cached:
            return cached

        # キャッシュなし→API から取得
        data = self._get(
            "videos",
            {
                "part": "snippet,contentDetails,liveStreamingDetails,status",
                "id": video_id,
                "maxResults": 1,
            },
            expected_cost=1,
            operation=f"video detail: {video_id}"
        )
        items = data.get("items", []) if data else []
        if items:
            details = items[0]
            # キャッシュに保存
            self._cache_video_detail(video_id, details)
            return details

        return None

    def fetch_video_detail(self, video_id: str) -> Optional[Dict[str, Any]]:
        """
        単一動画の詳細を取得（キャッシュ優先、1ユニット）

        投稿直前の最新情報確認用 public メソッド
        キャッシュの有効期限が切れていれば自動的に API で再取得します

        Args:
            video_id: YouTube 動画 ID

        Returns:
            動画詳細情報（API レスポンスの item）、取得失敗時は None
        """
        return self._fetch_video_detail(video_id)

    def fetch_video_details_batch(self, video_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        最大50件の動画詳細をバッチ取得（キャッシュ優先、1ユニット）

        Args:
            video_ids: 動画IDのリスト（最大50件）

        Returns:
            {video_id: details} の辞書
        """
        if not video_ids:
            return {}

        results = {}
        to_fetch = []

        # キャッシュから取得可能な分を抽出
        for video_id in video_ids:
            cached = self._get_cached_video_detail(video_id)
            if cached:
                results[video_id] = cached
            else:
                to_fetch.append(video_id)

        if not to_fetch:
            logger.debug(f"📦 全動画がキャッシュから取得されました: {len(results)} 件")
            return results

        logger.debug(f"🔍 キャッシュ外の動画を API から取得: {len(to_fetch)} 件")

        # 50件ずつ分割してAPI取得
        for i in range(0, len(to_fetch), 50):
            batch = to_fetch[i:i+50]
            batch_str = ",".join(batch)

            data = self._get(
                "videos",
                {
                    "part": "snippet,contentDetails,liveStreamingDetails,status",
                    "id": batch_str,
                    "maxResults": 50,
                },
                expected_cost=1,
                operation=f"batch video details: {len(batch)} 件"
            )

            if data:
                for item in data.get("items", []):
                    video_id = item.get("id")
                    if video_id:
                        results[video_id] = item
                        # キャッシュに保存
                        self._cache_video_detail(video_id, item)

        return results

    # --- ID 検証 ---
    def _is_valid_youtube_video_id(self, video_id: str) -> bool:
        """
        YouTube 動画ID 形式の検証

        YouTube 動画ID は 11 文字の英数字（A-Z, a-z, 0-9, -, _）
        例: dQw4w9WgXcQ

        Niconico ID（sm45414087）など他形式は False を返す

        Args:
            video_id: 検証対象の ID

        Returns:
            True: YouTube 形式, False: 他の形式（Niconico など）
        """
        import re
        # YouTube 動画ID: 11 文字、A-Za-z0-9-_
        if re.match(r'^[A-Za-z0-9_-]{11}$', video_id):
            return True
        return False

    # --- 分類ロジック（コア・共通部分） ---
    @staticmethod
    def is_pure_video(details: Dict[str, Any]) -> bool:
        """
        【キャッシュから判定】「純粋な動画」（通常のファイルアップロード）か判定

        ライブ配信・アーカイブ・プレミア公開を除いた、
        「純粋に動画ファイルとしてアップロードされた通常動画」のみを判定します。

        既存キャッシュ（youtube_video_detail_cache.json）の情報を使用するため、
        毎回 API を呼ぶ必要はありません。

        ★ 判定基準（YouTube API 仕様）:
          1. snippet.liveBroadcastContent == "none"
          2. liveStreamingDetails フィールドが存在しない

        この両方を満たす場合のみ「純粋な動画」です。

        Args:
            details: YouTube API videos.list で取得した動画詳細（キャッシュから直接使用）

        Returns:
            bool: True = 純粋な動画（通常アップロード）
                  False = ライブ/アーカイブ/プレミア/その他

        Example:
            ```python
            # キャッシュから取得した詳細情報で判定
            is_pure = YouTubeAPIPlugin.is_pure_video(cached_details)

            if is_pure:
                print("✅ 通常動画")
            else:
                print("❌ ライブ/アーカイブ/プレミア")
            ```
        """
        # 条件1: snippet.liveBroadcastContent == "none"
        snippet = details.get("snippet", {})
        live_broadcast_content = snippet.get("liveBroadcastContent", "none")

        if live_broadcast_content != "none":
            # "live", "upcoming", "completed" のいずれか
            # → ライブ/プレミア関連
            return False

        # 条件2: liveStreamingDetails フィールドが存在しない
        has_live_streaming_details = "liveStreamingDetails" in details

        if has_live_streaming_details:
            # liveStreamingDetails がある
            # = 過去に一度でもライブ配信またはプレミア公開されたことがある
            # → アーカイブ/終了したプレミア
            return False

        # ✅ 両条件を満たす = 純粋な動画
        return True

    @staticmethod
    def is_live_archive(details: Dict[str, Any]) -> bool:
        """
        【キャッシュから判定】ライブ配信アーカイブか判定

        終了したライブ配信（生放送）のアーカイブを識別します。

        ★ 判定基準:
          1. liveStreamingDetails が存在する
          2. concurrentViewers プロパティが存在する、または過去に存在した形跡がある

        【注意】 2025年時点では、キャッシュに concurrentViewers が保存されない場合が多いため、
        以下の代替判定を使用します:
          - actualStartTime と actualEndTime が両方存在する
          - 配信時間が記録されている（= ライブ配信特有の動作）

        Args:
            details: YouTube API videos.list で取得した動画詳細（キャッシュから直接使用）

        Returns:
            bool: True = ライブ配信アーカイブ
                  False = 通常動画またはプレミア公開アーカイブ

        Example:
            ```python
            is_archive = YouTubeAPIPlugin.is_live_archive(cached_details)
            if is_archive:
                print("📹 ライブ配信アーカイブ")
            ```
        """
        live = details.get("liveStreamingDetails", {})

        if not live:
            # liveStreamingDetails がない = 通常動画
            return False

        # 判定基準: actualStartTime と actualEndTime が存在
        # ライブ配信は開始～終了の時間帯が記録される
        has_actual_start = "actualStartTime" in live
        has_actual_end = "actualEndTime" in live

        # 将来的に concurrentViewers が含まれる可能性に対応
        has_concurrent_viewers = "concurrentViewers" in live

        # ライブ配信 = actualStartTime と actualEndTime がある、
        # または concurrentViewers がある
        is_live = (has_actual_start and has_actual_end) or has_concurrent_viewers

        return is_live

    @staticmethod
    def is_premiere_archive(details: Dict[str, Any]) -> bool:
        """
        【キャッシュから判定】プレミア公開アーカイブか判定

        プレミア公開（予約公開）のアーカイブを識別します。

        ★ 判定基準:
          1. liveStreamingDetails が存在する
          2. concurrentViewers プロパティが一度も含まれていない

        【注意】 2025年時点では、キャッシュに concurrentViewers が保存されない場合が多いため、
        直接判定が難しいです。以下の情報が役立つ場合があります:
          - snippet の description（プレミア公開の宣伝テキスト）
          - scheduledStartTime の有無

        現在の実装では、「liveStreamingDetails がある」ことのみで
        プレミア公開の可能性を示唆します。

        Args:
            details: YouTube API videos.list で取得した動画詳細（キャッシュから直接使用）

        Returns:
            bool: True = プレミア公開アーカイブの可能性
                  False = 通常動画またはライブ配信アーカイブ

        Example:
            ```python
            is_premiere = YouTubeAPIPlugin.is_premiere_archive(cached_details)
            if is_premiere:
                print("🎥 プレミア公開アーカイブ")
            ```
        """
        # is_live_archive() と is_premiere_archive() は相互に排他的な判定をすべきなので、
        # 同じく liveStreamingDetails の判定で分けない
        #
        # 現在の実装では両者が同時に True になるため、
        # ここではコンセプト提示に留める

        live = details.get("liveStreamingDetails", {})

        if not live:
            # liveStreamingDetails がない = 通常動画
            return False

        # 【現在は判定不可】
        # concurrentViewers が保存されていないため、厳密な判定ができません
        #
        # 理想的な判定基準:
        # - concurrentViewers が存在しない = プレミア公開
        # - concurrentViewers が存在する = ライブ配信
        #
        # ただし、将来的に API データ取得時に concurrentViewers を確認することで、
        # より精密な判定が可能になります

        return False

    def _classify_video_core(self, details: Dict[str, Any]) -> Tuple[str, Optional[str], bool]:
        """
        【統合分類ロジック】動画の種別と状態を判別（content_type, live_status, is_premiere）

        新しい分類メソッド（is_pure_video, is_live_archive, is_premiere_archive）と
        既存の時間情報ベース判定を組み合わせた統合分類ロジックです。

        ★ 判定優先度（上から順）:
          1. 新規フローバック: is_pure_video() → "video"
          2. ライブアーカイブ: is_live_archive() → "archive"
          3. プレミアアーカイブ: 代替判定（future）
          4. タイムスタンプベース判定: actualStartTime/actualEndTime/scheduledStartTime
          5. liveBroadcastContent ベース判定: "live", "upcoming", "completed"
          6. デフォルト: "video"

        Args:
            details: YouTube API videos.list で取得した動画詳細

        Returns:
            (content_type, live_status, is_premiere)
              - content_type: "video" | "live" | "archive"
              - live_status: None | "upcoming" | "live" | "completed"
              - is_premiere: bool
        """
        snippet = details.get("snippet", {})
        live = details.get("liveStreamingDetails", {})
        status = details.get("status", {})

        # ★ 判定フロー 1: 純粋な動画（新フロー）
        if self.is_pure_video(details):
            return "video", None, False

        # ★ 判定フロー 2: ライブ配信アーカイブ（新フロー）
        if self.is_live_archive(details):
            return "archive", "completed", False

        # ★ 判定フロー 3: プレミア公開アーカイブ（将来拡張）
        # if self.is_premiere_archive(details):
        #     return "archive", "completed", True

        # ★ 判定フロー 4: liveStreamingDetails ベース（既存フロー）
        if live:
            # プレミア公開フラグ判定
            broadcast_type = snippet.get("liveBroadcastContent", "none")
            is_premiere = status.get("uploadStatus") == "processed" and broadcast_type in ("live", "upcoming")

            # タイムスタンプから状態判定（精度優先）
            if live.get("actualEndTime"):
                # 配信終了 → アーカイブ
                return "archive", "completed", is_premiere
            elif live.get("actualStartTime"):
                # 配信中
                return "live", "live", is_premiere
            elif live.get("scheduledStartTime"):
                # 配信予定
                return "live", "upcoming", is_premiere

        # ★ 判定フロー 5: liveBroadcastContent ベース（補助判定）
        broadcast_type = snippet.get("liveBroadcastContent", "none")
        if broadcast_type == "live":
            return "live", "live", False
        elif broadcast_type == "upcoming":
            return "live", "upcoming", False
        elif broadcast_type == "completed":
            return "archive", "completed", False

        # ★ デフォルト
        return "video", None, False

    def _classify_video(self, details: Dict[str, Any]) -> Tuple[str, Optional[str], bool]:
        """
        動画の種別と状態を判別（content_type, live_status, is_premiere）

        ⚠️ このメソッドは _classify_video_core() へ委譲（後方互換性のためラッパー保持）

        Returns:
            (content_type, live_status, is_premiere)
        """
        return self._classify_video_core(details)

    def on_enable(self) -> None:
        """プラグイン有効化時"""
        logger.info(f"   日次クォータ: {self.daily_quota} ユニット")

    def on_disable(self) -> None:
        """プラグイン無効化時"""
        logger.info(f"⛔ プラグイン無効化: {self.get_name()}")
        logger.info(f"   本日の API コスト: {self.daily_cost}/{self.daily_quota} ユニット")
        # 終了時にキャッシュを保存
        self._save_video_detail_cache()

    def poll_and_update_cache(self):
        """ポーリングごとにキャッシュを更新"""
        for video_id, video_details in self.video_detail_cache.items():
            # APIから最新情報を取得（仮の関数名: fetch_video_details）
            updated_details = self.fetch_video_details(video_id)
            if updated_details:
                self.update_video_detail_cache(video_id, updated_details)

    def _extract_video_info(self, details: Dict[str, Any]) -> Dict[str, Any]:
        """
        API取得した raw動画詳細情報を video dict 形式へ変換（投稿直前確認用）

        Args:
            details: API の videos.list レスポンス内の item

        Returns:
            {published_at, live_status, ...} の辞書
        """
        try:
            snippet = details.get("snippet", {})
            live_details = details.get("liveStreamingDetails", {})

            # 放送開始予定日時
            published_at = None
            if live_details.get("scheduledStartTime"):
                published_at = live_details["scheduledStartTime"]
            elif live_details.get("actualStartTime"):
                published_at = live_details["actualStartTime"]
            elif snippet.get("publishedAt"):
                published_at = snippet["publishedAt"]

            # ステータス判定
            classification_type, live_status, _ = self._classify_video_core(details)

            # テンプレート用：日付と時間を抽出
            scheduled_start_date = ""
            scheduled_start_time = ""
            scheduled_start_iso = live_details.get("scheduledStartTime")

            if scheduled_start_iso:
                try:
                    # ISO 8601 形式から日付と時間を抽出
                    # 例: "2025-12-29T27:00:00Z" → date="2025-12-29", time="27:00"
                    dt_part = scheduled_start_iso.split("T")[0]  # "2025-12-29"
                    time_part = scheduled_start_iso.split("T")[1] if "T" in scheduled_start_iso else ""

                    if time_part:
                        time_part = time_part.split(":")[0] + ":" + time_part.split(":")[1]  # "27:00"

                    scheduled_start_date = dt_part
                    scheduled_start_time = time_part
                except Exception as e:
                    logger.warning(f"⚠️ 日付時刻抽出エラー: {scheduled_start_iso} - {e}")

            return {
                "published_at": published_at,
                "live_status": live_status,
                "classification_type": classification_type,
                "title": snippet.get("title"),
                "channel_name": snippet.get("channelTitle"),
                "scheduled_start_time": scheduled_start_iso,  # ISO形式のフル日時
                "scheduled_start_date": scheduled_start_date,  # テンプレート用日付
                "scheduled_start_time_hhmm": scheduled_start_time,  # テンプレート用時間
            }
        except Exception as e:
            logger.error(f"❌ 動画情報抽出エラー: {e}")
            return {}

    @staticmethod
    def extract_live_streaming_details(details: Dict[str, Any]) -> Dict[str, Any]:
        """
        liveStreamingDetails オブジェクトから詳細な配信時間情報を抽出

        【取得フィールド】
        - scheduledStartTime: 配信予定開始時刻
        - scheduledEndTime: 配信予定終了時刻
        - actualStartTime: 実際の配信開始時刻
        - actualEndTime: 実際の配信終了時刻

        【ユースケース】
        1. actualEndTime 存在判定 → 配信終了確認
        2. actualStartTime + scheduledStartTime → 配信予定時刻の精密度向上
        3. actualEndTime 未存在 + actualStartTime 存在 → 配信中判定

        Args:
            details: API の videos.list で取得した動画詳細辞書

        Returns:
            Dict[str, Any]: 配信時間情報
                {
                    "scheduled_start_time": "2025-12-24T15:00:00Z",
                    "scheduled_end_time": "2025-12-24T17:00:00Z",
                    "actual_start_time": "2025-12-24T15:02:30Z",
                    "actual_end_time": "2025-12-24T16:58:15Z",
                    "is_live_running": bool,
                    "is_archived": bool,
                }
        """
        try:
            live = details.get("liveStreamingDetails", {})

            scheduled_start = live.get("scheduledStartTime")
            scheduled_end = live.get("scheduledEndTime")
            actual_start = live.get("actualStartTime")
            actual_end = live.get("actualEndTime")

            # 配信状態判定
            is_live_running = bool(actual_start and not actual_end)
            is_archived = bool(actual_end)  # actualEndTime が存在 = 配信終了（アーカイブ化済み）

            logger.debug(f"⏱️ 配信時間情報抽出:")
            logger.debug(f"   scheduled: {scheduled_start} - {scheduled_end}")
            logger.debug(f"   actual: {actual_start} - {actual_end}")
            logger.debug(f"   状態: live_running={is_live_running}, archived={is_archived}")

            return {
                "scheduled_start_time": scheduled_start,
                "scheduled_end_time": scheduled_end,
                "actual_start_time": actual_start,
                "actual_end_time": actual_end,
                "is_live_running": is_live_running,
                "is_archived": is_archived,
            }

        except Exception as e:
            logger.error(f"❌ 配信時間情報抽出エラー: {e}")
            return {
                "scheduled_start_time": None,
                "scheduled_end_time": None,
                "actual_start_time": None,
                "actual_end_time": None,
                "is_live_running": False,
                "is_archived": False,
            }

    @staticmethod
    def extract_best_published_at(details: Dict[str, Any]) -> Optional[str]:
        """
        動画の「公開日時」として最適な値を抽出（優先順）

        【優先順】
        1. liveStreamingDetails.scheduledStartTime（配信予定時刻が最優先）
        2. liveStreamingDetails.actualStartTime（実際の配信開始時刻）
        3. snippet.publishedAt（RSS で取得した公開日時）

        【用途】
        - DB の published_at カラムに格納
        - ポーリング・ソート・API キャッシュの参照に使用

        Args:
            details: API の videos.list で取得した動画詳細辞書

        Returns:
            ISO 8601 形式の日時文字列（UTC+Z）、なければ None
        """
        try:
            live = details.get("liveStreamingDetails", {})
            snippet = details.get("snippet", {})

            # 優先順で取得
            scheduled_start = live.get("scheduledStartTime")
            if scheduled_start:
                logger.debug(f"📅 published_at: scheduledStartTime を採用 → {scheduled_start}")
                return scheduled_start

            actual_start = live.get("actualStartTime")
            if actual_start:
                logger.debug(f"📅 published_at: actualStartTime を採用 → {actual_start}")
                return actual_start

            published_at = snippet.get("publishedAt")
            if published_at:
                logger.debug(f"📅 published_at: snippet.publishedAt を採用 → {published_at}")
                return published_at

            logger.warning("⚠️ 公開日時が見つかりません")
            return None

        except Exception as e:
            logger.error(f"❌ 公開日時抽出エラー: {e}")
            return None

    @staticmethod
    def is_archive_transitioned(old_details: Optional[Dict[str, Any]], new_details: Dict[str, Any]) -> bool:
        """
        ライブ配信 → アーカイブへの状態遷移を検知

        【検知条件】
        ✅ 新しい詳細情報で:
           - actualEndTime が存在している
           - actualStartTime が存在している（配信は実施された）
           - liveBroadcastContent が "none" に変化した

        【参考】
        - old_details がない場合は "Live 状態 → Archive 状態" への単純転換として判定

        Args:
            old_details: 以前に取得した詳細情報（キャッシュなど）
            new_details: 現在取得した詳細情報

        Returns:
            bool: Archive への遷移が検知された場合 True
        """
        try:
            new_live = new_details.get("liveStreamingDetails", {})
            new_snippet = new_details.get("snippet", {})

            # 新しい詳細で配信終了を確認
            actual_end = new_live.get("actualEndTime")
            actual_start = new_live.get("actualStartTime")
            broadcast_type = new_snippet.get("liveBroadcastContent", "none")

            if not actual_end or not actual_start:
                logger.debug("📊 Archive 遷移: 条件不足（actualEnd または actualStart なし）")
                return False

            # 旧詳細がある場合は状態遷移を確認
            if old_details:
                old_live = old_details.get("liveStreamingDetails", {})
                old_broadcast_type = old_details.get("snippet", {}).get("liveBroadcastContent", "none")

                # old: live/upcoming, new: none（＋actualEnd） = Archive 化遷移
                if old_broadcast_type in ("live", "upcoming") and broadcast_type == "none" and actual_end:
                    logger.info(f"🔔 Archive 遷移検知: {old_broadcast_type} → {broadcast_type}（actualEnd={actual_end}）")
                    return True
                # old では actualEnd がなかったが new にある = Archive 化
                elif not old_live.get("actualEndTime") and actual_end:
                    logger.info(f"🔔 Archive 遷移検知: actualEndTime が新たに設定（{actual_end}）")
                    return True
            else:
                # old がない場合は、actualEnd の存在で Archive と判定
                if actual_end and broadcast_type == "none":
                    logger.info(f"🔔 Archive 遷移検知（初回）: actualEnd={actual_end}, broadcast_type={broadcast_type}")
                    return True

            logger.debug(f"📊 Archive 遷移なし: actualEnd={actual_end}, broadcast_type={broadcast_type}")
            return False

        except Exception as e:
            logger.error(f"❌ Archive 遷移検知エラー: {e}")
            return False


def get_plugin():
    """PluginManager から取得するためのヘルパー"""
    return YouTubeAPIPlugin()
