# -*- coding: utf-8 -*-

"""
統合設定ウィンドウ (v3.3.0+)

全設定項目を GUI で一元管理し、settings.env のファイル破損を防止
- タブ式UI (ttk.Notebook)
- セクション単位の読み書き
- 入力バリデーション（範囲チェック、候補固定）
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import logging
import os
from pathlib import Path
from configparser import ConfigParser
import re
from datetime import datetime

logger = logging.getLogger("GUILogger")

__version__ = "1.0.0"

# コメント状態で保存すべきキー
COMMENTED_KEYS = {
    'YOUTUBE_LIVE_AUTO_POST_SCHEDULE',
    'YOUTUBE_LIVE_AUTO_POST_LIVE',
    'YOUTUBE_LIVE_AUTO_POST_ARCHIVE',
    'YOUTUBE_LIVE_POLL_INTERVAL_ACTIVE',
    'YOUTUBE_LIVE_POLL_INTERVAL_COMPLETED_MIN',
    'YOUTUBE_LIVE_POLL_INTERVAL_COMPLETED_MAX',
    'YOUTUBE_LIVE_ARCHIVE_CHECK_COUNT_MAX',
    'YOUTUBE_LIVE_ARCHIVE_CHECK_INTERVAL',
    'TEMPLATE_YOUTUBE_SCHEDULE_PATH',
    'TEMPLATE_YOUTUBE_ONLINE_PATH',
    'TEMPLATE_YOUTUBE_OFFLINE_PATH',
    'TEMPLATE_YOUTUBE_ARCHIVE_PATH',
    'TEMPLATE_TWITCH_ONLINE_PATH',
    'TEMPLATE_TWITCH_OFFLINE_PATH',
    'TEMPLATE_TWITCH_RAID_PATH',
}

# UI型定義
UI_TYPES = {
    'entry': 'Entry',
    'checkbox': 'Checkbox',
    'spinbox': 'Spinbox',
    'combobox': 'Combobox',
    'text': 'Text',
    'radiobutton': 'RadioButton',
}


class UnifiedSettingsWindow:
    """統合設定ウィンドウ

    Role:
        - settings.env をUI経由で編集・管理
        - 入力バリデーション
        - セクション単位での読み書き（ファイル破損防止）
    """

    def __init__(self, parent, initial_tab="basic", db=None):
        """
        Args:
            parent: 親ウィンドウ
            initial_tab: 初期表示タブ ("basic", "accounts", "posting", "live", "templates", "logging", "future")
            db: Database インスタンス（参考用）
        """
        self.parent = parent
        self.db = db
        self.initial_tab = initial_tab
        self.settings_dict = {}
        self.ui_vars = {}  # UI要素の値を保持 {key: tk.Variable}

        # ウィンドウ作成
        self.window = tk.Toplevel(parent)
        self.window.title("統合設定ウィンドウ")
        self.window.geometry("600x625")
        self.window.resizable(True, True)

        # 設定ファイルパス
        self.settings_file = Path("settings.env")

        # 設定を読み込み
        self._load_settings()

        # UI を構築
        self._build_ui()

        # タブをアクティブに
        self._activate_initial_tab()

        # モーダル化
        self.window.transient(parent)
        self.window.grab_set()

    def _load_settings(self):
        """settings.env から設定を読み込み"""
        try:
            if self.settings_file.exists():
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()

                        # コメント行・空行をスキップ
                        if not line or line.startswith('#'):
                            continue

                        # キー=値の形式をパース
                        if '=' in line:
                            key, value = line.split('=', 1)
                            self.settings_dict[key.strip()] = value.strip()

            logger.info("✅ settings.env を読み込みました")
        except Exception as e:
            logger.error(f"❌ settings.env の読み込みに失敗: {e}")
            messagebox.showerror("エラー", f"設定ファイルの読み込みに失敗しました:\n{e}")

    def _build_ui(self):
        """UI を構築"""
        # === ボタンパネル（上部に配置） ===
        button_frame = ttk.Frame(self.window)
        button_frame.pack(fill=tk.X, padx=5, pady=3)

        ttk.Button(
            button_frame,
            text="💾 保存して閉じる",
            command=self._save_all_settings
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            button_frame,
            text="キャンセル",
            command=self.window.destroy
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            button_frame,
            text="ℹ️ リセット",
            command=self._reset_to_defaults
        ).pack(side=tk.LEFT, padx=5)

        # === Notebook (タブ) を作成 ===
        self.notebook = ttk.Notebook(self.window)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 各タブを作成
        self._build_tab_basic()
        self._build_tab_accounts()
        self._build_tab_posting()
        self._build_tab_live()
        self._build_tab_templates()
        self._build_tab_logging()
        self._build_tab_future()

    def _build_tab_basic(self):
        """タブ 1: 基本設定"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="📋 基本設定")

        main_frame = ttk.Frame(tab, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # === APP_MODE ===
        ttk.Label(main_frame, text="APP_MODE", font=("", 10, "bold")).grid(row=0, column=0, sticky=tk.W, pady=5)
        app_mode_var = tk.StringVar(
            value=self.settings_dict.get('APP_MODE', 'selfpost')
        )
        self.ui_vars['APP_MODE'] = app_mode_var
        ttk.Combobox(
            main_frame,
            textvariable=app_mode_var,
            values=['selfpost', 'autopost', 'dry_run', 'collect'],
            state='readonly',
            width=40
        ).grid(row=0, column=1, sticky=tk.W, padx=5)
        ttk.Label(main_frame, text="アプリケーション動作モード", foreground='gray').grid(row=0, column=2, sticky=tk.W)

        # === DEBUG_MODE ===
        debug_var = tk.BooleanVar(
            value=self.settings_dict.get('DEBUG_MODE', 'false').lower() == 'true'
        )
        self.ui_vars['DEBUG_MODE'] = debug_var
        ttk.Checkbutton(
            main_frame,
            text="DEBUG_MODE (デバッグモード有効)",
            variable=debug_var
        ).grid(row=1, column=0, columnspan=3, sticky=tk.W, pady=5)

        # === TIMEZONE ===
        ttk.Label(main_frame, text="TIMEZONE", font=("", 10, "bold")).grid(row=2, column=0, sticky=tk.W, pady=5)
        timezone_var = tk.StringVar(
            value=self.settings_dict.get('TIMEZONE', 'Asia/Tokyo')
        )
        self.ui_vars['TIMEZONE'] = timezone_var
        ttk.Combobox(
            main_frame,
            textvariable=timezone_var,
            values=['Asia/Tokyo', 'UTC', 'America/New_York', 'Europe/London', 'system'],
            width=40
        ).grid(row=2, column=1, sticky=tk.W, padx=5)

        # === YOUTUBE_FEED_MODE ===
        ttk.Label(main_frame, text="YOUTUBE_FEED_MODE", font=("", 10, "bold")).grid(row=3, column=0, sticky=tk.W, pady=5)
        youtube_feed_mode_var = tk.StringVar(
            value=self.settings_dict.get('YOUTUBE_FEED_MODE', 'poll')
        )
        self.ui_vars['YOUTUBE_FEED_MODE'] = youtube_feed_mode_var
        ttk.Combobox(
            main_frame,
            textvariable=youtube_feed_mode_var,
            values=['poll', 'websub', 'auto'],
            state='readonly',
            width=40
        ).grid(row=3, column=1, sticky=tk.W, padx=5)
        ttk.Label(main_frame, text="RSS ポーリング vs WebSub", foreground='gray').grid(row=3, column=2, sticky=tk.W)

    def _build_tab_accounts(self):
        """タブ 2: アカウント・ポーリング設定（サブタブ 4分割）"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="👤 アカウント")

        # サブタブ
        sub_notebook = ttk.Notebook(tab)
        sub_notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # サブタブ 2-1: YouTube
        self._build_subtab_accounts_youtube(sub_notebook)

        # サブタブ 2-2: Niconico
        self._build_subtab_accounts_niconico(sub_notebook)

        # サブタブ 2-3: WebSub
        self._build_subtab_accounts_websub(sub_notebook)

        # サブタブ 2-4: Bluesky
        self._build_subtab_accounts_bluesky(sub_notebook)

    def _build_subtab_accounts_youtube(self, parent_notebook):
        """タブ 2-1: YouTube"""
        sub_tab = ttk.Frame(parent_notebook)
        parent_notebook.add(sub_tab, text="📺 YouTube")

        frame = ttk.Frame(sub_tab, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        # YOUTUBE_CHANNEL_ID
        ttk.Label(frame, text="YOUTUBEチャンネルID", font=("", 10, "bold")).grid(row=0, column=0, sticky=tk.W, pady=3)
        channel_id_var = tk.StringVar(
            value=self.settings_dict.get('YOUTUBE_CHANNEL_ID', '')
        )
        self.ui_vars['YOUTUBE_CHANNEL_ID'] = channel_id_var
        ttk.Entry(frame, textvariable=channel_id_var, width=50).grid(row=0, column=1, sticky=tk.W, padx=5)

        # YOUTUBE_CHANNEL_ID説明
        explanation_text = "UCで始まるチャンネルIDを入力してください。\nYouTubeの設定＞詳細設定から取得できます。"
        ttk.Label(frame, text=explanation_text, foreground='gray', wraplength=400, justify=tk.LEFT, font=("", 8)).grid(
            row=1, column=0, columnspan=3, sticky=tk.W, padx=(10, 0), pady=(0, 5)
        )

        # YOUTUBE_API_KEY
        ttk.Label(frame, text="YouTubeDataAPIキー", font=("", 10, "bold")).grid(row=2, column=0, sticky=tk.W, pady=3)
        api_key_var = tk.StringVar(
            value=self.settings_dict.get('YOUTUBE_API_KEY', '')
        )
        self.ui_vars['YOUTUBE_API_KEY'] = api_key_var
        ttk.Entry(frame, textvariable=api_key_var, width=50, show="*").grid(row=2, column=1, sticky=tk.W, padx=5)

        # YOUTUBE_API_KEY説明
        explanation_text = "YouTubeDataAPI(v3)キーを入力してください\nAPIキーはGoogle Cloud Console から取得できます。"
        ttk.Label(frame, text=explanation_text, foreground='gray', wraplength=400, justify=tk.LEFT, font=("", 8)).grid(
            row=3, column=0, columnspan=3, sticky=tk.W, padx=(10, 0), pady=(0, 5)
        )

        # YOUTUBE_RSS_POLL_INTERVAL_MINUTES
        ttk.Label(frame, text="YouTube RSS ポーリング間隔", font=("", 10, "bold")).grid(row=4, column=0, sticky=tk.W, pady=3)
        poll_interval_var = tk.StringVar(
            value=self.settings_dict.get('YOUTUBE_RSS_POLL_INTERVAL_MINUTES', '10')
        )
        self.ui_vars['YOUTUBE_RSS_POLL_INTERVAL_MINUTES'] = poll_interval_var
        ttk.Spinbox(
            frame,
            from_=1, to=120,
            textvariable=poll_interval_var,
            width=10
        ).grid(row=4, column=1, sticky=tk.W, padx=5)

        # YOUTUBE_RSS_POLL_INTERVAL説明
        explanation_text = "最小10分、最大60分。デフォルト: 10分。\nRSSはYouTubeのPubSubHubbubを利用しています。\n短期間で頻繁なポーリングはYouTube側からアクセスを拒否される可能性があります。"
        ttk.Label(frame, text=explanation_text, foreground='gray', wraplength=400, justify=tk.LEFT, font=("", 8)).grid(
            row=5, column=0, columnspan=3, sticky=tk.W, padx=(10, 0), pady=(0, 5)
        )

    def _build_subtab_accounts_niconico(self, parent_notebook):
        """タブ 2-2: Niconico"""
        sub_tab = ttk.Frame(parent_notebook)
        parent_notebook.add(sub_tab, text="ニコニコ")

        frame = ttk.Frame(sub_tab, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        # NICONICO_USER_ID
        ttk.Label(frame, text="ニコニコユーザーID", font=("", 10, "bold")).grid(row=0, column=0, sticky=tk.W, pady=5)
        nico_user_id_var = tk.StringVar(
            value=self.settings_dict.get('NICONICO_USER_ID', '')
        )
        self.ui_vars['NICONICO_USER_ID'] = nico_user_id_var
        ttk.Entry(frame, textvariable=nico_user_id_var, width=30).grid(row=0, column=1, sticky=tk.W, padx=5)

        # NICONICO_USER_ID説明
        explanation_text = "ニコニコのユーザーIDを指定してください。（数字のみ）"
        ttk.Label(frame, text=explanation_text, foreground='gray', wraplength=400, justify=tk.LEFT, font=("", 8)).grid(
            row=1, column=0, columnspan=3, sticky=tk.W, padx=(10, 0), pady=(0, 5)
        )

        # NICONICO_USER_NAME
        ttk.Label(frame, text="ニコニコユーザー名", font=("", 10, "bold")).grid(row=2, column=0, sticky=tk.W, pady=3)
        nico_user_name_var = tk.StringVar(
            value=self.settings_dict.get('NICONICO_USER_NAME', '')
        )
        self.ui_vars['NICONICO_USER_NAME'] = nico_user_name_var
        ttk.Entry(frame, textvariable=nico_user_name_var, width=30).grid(row=2, column=1, sticky=tk.W, padx=5)

        # NICONICO_USER_NAME説明
        explanation_text = ("未設定時は自動取得を試みます。\n"
                            "確実に名前を指定したい場合は入力してください。")
        ttk.Label(frame, text=explanation_text, foreground='gray', wraplength=400, justify=tk.LEFT, font=("", 8)).grid(
            row=3, column=0, columnspan=3, sticky=tk.W, padx=(10, 0), pady=(0, 5)
        )

        # NICONICO_POLL_INTERVAL
        ttk.Label(frame, text="ニコニコのポーリング間隔（分）", font=("", 10, "bold")).grid(row=4, column=0, sticky=tk.W, pady=3)
        nico_poll_interval_var = tk.StringVar(
            value=self.settings_dict.get('NICONICO_POLL_INTERVAL', '10')
        )
        self.ui_vars['NICONICO_POLL_INTERVAL'] = nico_poll_interval_var
        ttk.Spinbox(
            frame,
            from_=1, to=120,
            textvariable=nico_poll_interval_var,
            width=10
        ).grid(row=4, column=1, sticky=tk.W, padx=5)

        # NICONICO_POLL_INTERVAL説明
        explanation_text = "最小5分。デフォルト: 10分、推奨: 10分"
        ttk.Label(frame, text=explanation_text, foreground='gray', wraplength=400, justify=tk.LEFT, font=("", 8)).grid(
            row=5, column=0, columnspan=3, sticky=tk.W, padx=(10, 0), pady=(0, 5)
        )

    def _build_subtab_accounts_websub(self, parent_notebook):
        """タブ 2-3: WebSub"""
        sub_tab = ttk.Frame(parent_notebook)
        parent_notebook.add(sub_tab, text="WebSub")

        frame = ttk.Frame(sub_tab, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        # WEBSUB_CLIENT_ID
        ttk.Label(frame, text="クライアントID", font=("", 10, "bold")).grid(row=0, column=0, sticky=tk.W, pady=5)
        websub_client_id_var = tk.StringVar(
            value=self.settings_dict.get('WEBSUB_CLIENT_ID', '')
        )
        self.ui_vars['WEBSUB_CLIENT_ID'] = websub_client_id_var
        ttk.Entry(frame, textvariable=websub_client_id_var, width=40).grid(row=0, column=1, sticky=tk.W, padx=5)

        # WebSub クライアントID説明
        explanation_text = "WebSub機能は支援者限定機能です"
        ttk.Label(frame, text=explanation_text, foreground='gray', wraplength=400, justify=tk.LEFT, font=("", 8)).grid(
            row=1, column=0, columnspan=3, sticky=tk.W, padx=(10, 0), pady=(0, 5)
        )

        # WEBSUB_CALLBACK_URL
        ttk.Label(frame, text="サーバーURL", font=("", 10, "bold")).grid(row=2, column=0, sticky=tk.W, pady=3)
        websub_callback_url_var = tk.StringVar(
            value=self.settings_dict.get('WEBSUB_CALLBACK_URL', '')
        )
        self.ui_vars['WEBSUB_CALLBACK_URL'] = websub_callback_url_var
        ttk.Entry(frame, textvariable=websub_callback_url_var, width=40).grid(row=2, column=1, sticky=tk.W, padx=5)

        # WebSub サーバーURL説明
        explanation_text = "WebSub機能は支援者限定機能です"
        ttk.Label(frame, text=explanation_text, foreground='gray', wraplength=400, justify=tk.LEFT, font=("", 8)).grid(
            row=3, column=0, columnspan=3, sticky=tk.W, padx=(10, 0), pady=(0, 5)
        )

        # WEBSUB_CLIENT_API_KEY
        ttk.Label(frame, text="クライアントAPIキー", font=("", 10, "bold")).grid(row=4, column=0, sticky=tk.W, pady=3)
        websub_api_key_var = tk.StringVar(
            value=self.settings_dict.get('WEBSUB_CLIENT_API_KEY', '')
        )
        self.ui_vars['WEBSUB_CLIENT_API_KEY'] = websub_api_key_var
        ttk.Entry(frame, textvariable=websub_api_key_var, width=40, show="*").grid(row=4, column=1, sticky=tk.W, padx=5)

        # WebSub APIキー説明
        explanation_text = "WebSub機能は支援者限定機能です"
        ttk.Label(frame, text=explanation_text, foreground='gray', wraplength=400, justify=tk.LEFT, font=("", 8)).grid(
            row=5, column=0, columnspan=3, sticky=tk.W, padx=(10, 0), pady=(0, 5)
        )

        # WEBSUB_LEASE_SECONDS
        ttk.Label(frame, text="WebSub 購読期間（秒）", font=("", 10, "bold")).grid(row=6, column=0, sticky=tk.W, pady=3)
        websub_lease_var = tk.StringVar(
            value=self.settings_dict.get('WEBSUB_LEASE_SECONDS', '432000')
        )
        self.ui_vars['WEBSUB_LEASE_SECONDS'] = websub_lease_var
        ttk.Spinbox(
            frame,
            from_=86400, to=2592000,
            textvariable=websub_lease_var,
            width=15
        ).grid(row=6, column=1, sticky=tk.W, padx=5)

        # YouTube WebSub 購読期間説明
        explanation_text = "範囲: 86400(1日)～2592000(30日)、推奨: 432000(5日)"
        ttk.Label(frame, text=explanation_text, foreground='gray', wraplength=400, justify=tk.LEFT, font=("", 8)).grid(
            row=7, column=0, columnspan=3, sticky=tk.W, padx=(10, 0), pady=(0, 5)
        )

        # YOUTUBE_WEBSUB_POLL_INTERVAL_MINUTES
        ttk.Label(frame, text="YouTube WebSub ポーリング間隔", font=("", 10, "bold")).grid(row=8, column=0, sticky=tk.W, pady=3)
        youtube_websub_poll_var = tk.StringVar(
            value=self.settings_dict.get('YOUTUBE_WEBSUB_POLL_INTERVAL_MINUTES', '5')
        )
        self.ui_vars['YOUTUBE_WEBSUB_POLL_INTERVAL_MINUTES'] = youtube_websub_poll_var
        ttk.Spinbox(
            frame,
            from_=1, to=120,
            textvariable=youtube_websub_poll_var,
            width=10
        ).grid(row=8, column=1, sticky=tk.W, padx=5)

        # YouTube WebSub ポーリング間隔説明
        explanation_text = "RSSポーリングより更新が早いため、短い間隔での取得が可能ですが、\n 過度に短い設定はCDN(Cloudflare)側から接続拒否や制御の対象となる\n 可能性があります。"
        ttk.Label(frame, text=explanation_text, foreground='gray', wraplength=400, justify=tk.LEFT, font=("", 8)).grid(
            row=9, column=0, columnspan=3, sticky=tk.W, padx=(10, 0), pady=(0, 5)
        )

    def _build_subtab_accounts_bluesky(self, parent_notebook):
        """タブ 2-4: Bluesky"""
        sub_tab = ttk.Frame(parent_notebook)
        parent_notebook.add(sub_tab, text="🦋 Bluesky")

        frame = ttk.Frame(sub_tab, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        # BLUESKY_USERNAME
        ttk.Label(frame, text="BLUESKYユーザー名", font=("", 10, "bold")).grid(row=0, column=0, sticky=tk.W, pady=5)
        bluesky_username_var = tk.StringVar(
            value=self.settings_dict.get('BLUESKY_USERNAME', '')
        )
        self.ui_vars['BLUESKY_USERNAME'] = bluesky_username_var
        ttk.Entry(frame, textvariable=bluesky_username_var, width=50).grid(row=0, column=1, sticky=tk.W, padx=5)
        ttk.Label(frame, text="ハンドル(.bsky.social) or 独自ドメイン", foreground='gray').grid(row=1, column=0, columnspan=2, sticky=tk.W, padx=(10, 0))

        # BLUESKY_PASSWORD
        ttk.Label(frame, text="BLUESKYAPPパスワード", font=("", 10, "bold")).grid(row=2, column=0, sticky=tk.W, pady=5)
        bluesky_password_var = tk.StringVar(
            value=self.settings_dict.get('BLUESKY_PASSWORD', '')
        )
        self.ui_vars['BLUESKY_PASSWORD'] = bluesky_password_var
        ttk.Entry(frame, textvariable=bluesky_password_var, width=50, show="*").grid(row=2, column=1, sticky=tk.W, padx=5)
        ttk.Label(frame, text="アプリパスワード（マスク表示）", foreground='gray').grid(row=3, column=0, columnspan=2, sticky=tk.W, padx=(10, 0))
        ttk.Label(frame, text="アプリパスワードは将来的バーションでOAuthに変更予定です。", foreground='gray').grid(row=4, column=0, columnspan=2, sticky=tk.W, padx=(10, 0))


    def _build_tab_posting(self):
        """タブ 3: 投稿設定（サブタブ 3分割）"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="📤 投稿設定")

        # サブタブ
        sub_notebook = ttk.Notebook(tab)
        sub_notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # サブタブ 3-1: 投稿保護
        self._build_subtab_posting_safeguards(sub_notebook)

        # サブタブ 3-2: 自動投稿設定
        self._build_subtab_posting_autopost(sub_notebook)

        # サブタブ 3-3: 手動投稿設定
        self._build_subtab_posting_manual(sub_notebook)

    def _build_subtab_posting_safeguards(self, parent_notebook):
        """タブ 3-1: 投稿保護"""
        sub_tab = ttk.Frame(parent_notebook)
        parent_notebook.add(sub_tab, text="🔒 投稿保護")

        frame = ttk.Frame(sub_tab, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        # PREVENT_DUPLICATE_POSTS
        prevent_dup_var = tk.BooleanVar(
            value=self.settings_dict.get('PREVENT_DUPLICATE_POSTS', 'false').lower() == 'true'
        )
        self.ui_vars['PREVENT_DUPLICATE_POSTS'] = prevent_dup_var
        ttk.Checkbutton(
            frame,
            text="PREVENT_DUPLICATE_POSTS (重複投稿を防止)",
            variable=prevent_dup_var
        ).pack(anchor=tk.W, pady=3)

        # PREVENT_DUPLICATE_POSTS説明
        explanation_text = "同じ動画の再投稿を防止します"
        ttk.Label(frame, text=explanation_text, foreground='gray', wraplength=400, justify=tk.LEFT, font=("", 8)).pack(
            anchor=tk.W, padx=20, pady=(0, 5)
        )

        # YOUTUBE_DEDUP_ENABLED
        youtube_dedup_var = tk.BooleanVar(
            value=self.settings_dict.get('YOUTUBE_DEDUP_ENABLED', 'true').lower() == 'true'
        )
        self.ui_vars['YOUTUBE_DEDUP_ENABLED'] = youtube_dedup_var
        ttk.Checkbutton(
            frame,
            text="YOUTUBE_DEDUP_ENABLED (YouTube 重複排除)",
            variable=youtube_dedup_var
        ).pack(anchor=tk.W, pady=3)

        # YOUTUBE_DEDUP_ENABLED説明
        explanation_text = "優先度ベースの動画管理。LIVE/アーカイブのみ登録（デフォルト: 有効）"
        ttk.Label(frame, text=explanation_text, foreground='gray', wraplength=400, justify=tk.LEFT, font=("", 8)).pack(
            anchor=tk.W, padx=20, pady=(0, 5)
        )

        # BLUESKY_POST_ENABLED
        # （アカウントタブでも設定しているが、投稿保護タブでも表示）
        bluesky_post_enabled_var = tk.BooleanVar(
            value=self.settings_dict.get('BLUESKY_POST_ENABLED', 'True').lower() == 'true'
        )
        self.ui_vars['BLUESKY_POST_ENABLED'] = bluesky_post_enabled_var
        ttk.Checkbutton(
            frame,
            text="BLUESKY_POST_ENABLED (Bluesky への投稿を有効化)",
            variable=bluesky_post_enabled_var
        ).pack(anchor=tk.W, pady=3)

        # BLUESKY_POST_ENABLED説明
        explanation_text = "Bluesky への投稿機能の有効/無効切り替え"
        ttk.Label(frame, text=explanation_text, foreground='gray', wraplength=400, justify=tk.LEFT, font=("", 8)).pack(
            anchor=tk.W, padx=20, pady=(0, 5)
        )

    def _build_subtab_posting_autopost(self, parent_notebook):
        """タブ 3-2: 自動投稿設定"""
        sub_tab = ttk.Frame(parent_notebook)
        parent_notebook.add(sub_tab, text="🔄 自動投稿")

        frame = ttk.Frame(sub_tab, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        # AUTOPOST_INTERVAL_MINUTES
        ttk.Label(frame, text="投稿間隔", font=("", 10, "bold")).grid(row=0, column=0, sticky=tk.W, pady=3)
        autopost_interval_var = tk.StringVar(
            value=self.settings_dict.get('AUTOPOST_INTERVAL_MINUTES', '5')
        )
        self.ui_vars['AUTOPOST_INTERVAL_MINUTES'] = autopost_interval_var
        ttk.Spinbox(
            frame,
            from_=1, to=60,
            textvariable=autopost_interval_var,
            width=10
        ).grid(row=0, column=1, sticky=tk.W, padx=5)

        # 投稿間隔説明
        explanation_text = "連続投稿によるスパム化を防止（デフォルト: 5分）"
        ttk.Label(frame, text=explanation_text, foreground='gray', wraplength=400, justify=tk.LEFT, font=("", 8)).grid(
            row=1, column=0, columnspan=3, sticky=tk.W, padx=(10, 0), pady=(0, 5)
        )

        # AUTOPOST_LOOKBACK_MINUTES
        ttk.Label(frame, text="時間窓", font=("", 10, "bold")).grid(row=2, column=0, sticky=tk.W, pady=3)
        autopost_lookback_var = tk.StringVar(
            value=self.settings_dict.get('AUTOPOST_LOOKBACK_MINUTES', '30')
        )
        self.ui_vars['AUTOPOST_LOOKBACK_MINUTES'] = autopost_lookback_var
        ttk.Spinbox(
            frame,
            from_=5, to=1440,
            textvariable=autopost_lookback_var,
            width=10
        ).grid(row=2, column=1, sticky=tk.W, padx=5)

        # 時間窓説明
        explanation_text = "再起動時の取りこぼし防止を目的（デフォルト: 30分）"
        ttk.Label(frame, text=explanation_text, foreground='gray', wraplength=400, justify=tk.LEFT, font=("", 8)).grid(
            row=3, column=0, columnspan=3, sticky=tk.W, padx=(10, 0), pady=(0, 5)
        )

        # AUTOPOST_UNPOSTED_THRESHOLD
        ttk.Label(frame, text="大量検知閾値", font=("", 10, "bold")).grid(row=4, column=0, sticky=tk.W, pady=3)
        autopost_threshold_var = tk.StringVar(
            value=self.settings_dict.get('AUTOPOST_UNPOSTED_THRESHOLD', '20')
        )
        self.ui_vars['AUTOPOST_UNPOSTED_THRESHOLD'] = autopost_threshold_var
        ttk.Spinbox(
            frame,
            from_=1, to=1000,
            textvariable=autopost_threshold_var,
            width=10
        ).grid(row=4, column=1, sticky=tk.W, padx=5)

        # 大量検知閾値説明
        explanation_text = "未投稿動画がこの件数以上あると安全弁が働く（デフォルト: 20件）"
        ttk.Label(frame, text=explanation_text, foreground='gray', wraplength=400, justify=tk.LEFT, font=("", 8)).grid(
            row=5, column=0, columnspan=3, sticky=tk.W, padx=(10, 0), pady=(0, 5)
        )

        # AUTOPOST_INCLUDE_NORMAL
        autopost_normal_var = tk.BooleanVar(
            value=self.settings_dict.get('AUTOPOST_INCLUDE_NORMAL', 'true').lower() == 'true'
        )
        self.ui_vars['AUTOPOST_INCLUDE_NORMAL'] = autopost_normal_var
        ttk.Checkbutton(
            frame,
            text="通常動画を含める",
            variable=autopost_normal_var
        ).grid(row=6, column=0, columnspan=3, sticky=tk.W, pady=3)

        # 通常動画説明
        explanation_text = "通常の動画投稿も投稿対象に含める（デフォルト: 有効）"
        ttk.Label(frame, text=explanation_text, foreground='gray', wraplength=400, justify=tk.LEFT, font=("", 8)).grid(
            row=7, column=0, columnspan=3, sticky=tk.W, padx=(10, 0), pady=(0, 5)
        )

        # AUTOPOST_INCLUDE_PREMIERE
        autopost_premiere_var = tk.BooleanVar(
            value=self.settings_dict.get('AUTOPOST_INCLUDE_PREMIERE', 'true').lower() == 'true'
        )
        self.ui_vars['AUTOPOST_INCLUDE_PREMIERE'] = autopost_premiere_var
        ttk.Checkbutton(
            frame,
            text="プレミア配信を含める",
            variable=autopost_premiere_var
        ).grid(row=8, column=0, columnspan=3, sticky=tk.W, pady=3)

        # プレミア配信説明
        explanation_text = "プレミア配信も投稿対象に含める（デフォルト: 有効）"
        ttk.Label(frame, text=explanation_text, foreground='gray', wraplength=400, justify=tk.LEFT, font=("", 8)).grid(
            row=9, column=0, columnspan=3, sticky=tk.W, padx=(10, 0), pady=(0, 5)
        )

    def _build_subtab_posting_manual(self, parent_notebook):
        """タブ 3-3: 手動投稿設定"""
        sub_tab = ttk.Frame(parent_notebook)
        parent_notebook.add(sub_tab, text="🖱️ 手動投稿")

        frame = ttk.Frame(sub_tab, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        # YOUTUBE_LIVE_AUTO_POST_SCHEDULE
        youtube_live_schedule_var = tk.BooleanVar(
            value=self.settings_dict.get('YOUTUBE_LIVE_AUTO_POST_SCHEDULE', 'true').lower() == 'true'
        )
        self.ui_vars['YOUTUBE_LIVE_AUTO_POST_SCHEDULE'] = youtube_live_schedule_var
        ttk.Checkbutton(
            frame,
            text="予約枠を投稿",
            variable=youtube_live_schedule_var
        ).pack(anchor=tk.W, pady=3)

        # 予約枠説明
        explanation_text = "放送枠が立った時（upcoming/schedule状態）の予約通知投稿"
        ttk.Label(frame, text=explanation_text, foreground='gray', wraplength=400, justify=tk.LEFT, font=("", 8)).pack(
            anchor=tk.W, padx=20, pady=(0, 5)
        )

        # YOUTUBE_LIVE_AUTO_POST_LIVE
        youtube_live_live_var = tk.BooleanVar(
            value=self.settings_dict.get('YOUTUBE_LIVE_AUTO_POST_LIVE', 'true').lower() == 'true'
        )
        self.ui_vars['YOUTUBE_LIVE_AUTO_POST_LIVE'] = youtube_live_live_var
        ttk.Checkbutton(
            frame,
            text="配信中・終了を投稿",
            variable=youtube_live_live_var
        ).pack(anchor=tk.W, pady=3)

        # 配信中・終了説明
        explanation_text = "配信開始・終了時の通知投稿"
        ttk.Label(frame, text=explanation_text, foreground='gray', wraplength=400, justify=tk.LEFT, font=("", 8)).pack(
            anchor=tk.W, padx=20, pady=(0, 5)
        )

        # YOUTUBE_LIVE_AUTO_POST_ARCHIVE
        youtube_live_archive_var = tk.BooleanVar(
            value=self.settings_dict.get('YOUTUBE_LIVE_AUTO_POST_ARCHIVE', 'true').lower() == 'true'
        )
        self.ui_vars['YOUTUBE_LIVE_AUTO_POST_ARCHIVE'] = youtube_live_archive_var
        ttk.Checkbutton(
            frame,
            text="アーカイブを投稿",
            variable=youtube_live_archive_var
        ).pack(anchor=tk.W, pady=3)

        # アーカイブ説明
        explanation_text = "YouTube Live のアーカイブ（録画）が公開された時の通知投稿"
        ttk.Label(frame, text=explanation_text, foreground='gray', wraplength=400, justify=tk.LEFT, font=("", 8)).pack(
            anchor=tk.W, padx=20, pady=(0, 5)
        )

    def _build_tab_live(self):
        """タブ 4: YouTube Live（核心タブ、サブタブ 5分割）"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="🎬 Live設定")

        # サブタブ
        sub_notebook = ttk.Notebook(tab)
        sub_notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # サブタブ 4-1: 投稿タイミング
        self._build_subtab_live_timing(sub_notebook)

        # サブタブ 4-2: 投稿遅延
        self._build_subtab_live_delay(sub_notebook)

        # サブタブ 4-3: フィルタ
        self._build_subtab_live_filter(sub_notebook)

        # サブタブ 4-4: ポーリング設定
        self._build_subtab_live_polling(sub_notebook)

        # ★ 【v3.3.3】サブタブ 4-5: キャッシュ管理
        self._build_subtab_live_cache(sub_notebook)

    def _build_subtab_live_timing(self, parent_notebook):
        """タブ 4-1: 投稿タイミング"""
        sub_tab = ttk.Frame(parent_notebook)
        parent_notebook.add(sub_tab, text="⏰ タイミング")

        frame = ttk.Frame(sub_tab, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Live配信の各段階での投稿タイミング", font=("", 10, "bold")).pack(anchor=tk.W, pady=5)

        # YOUTUBE_LIVE_AUTO_POST_SCHEDULE
        youtube_live_schedule_var = self.ui_vars.get('YOUTUBE_LIVE_AUTO_POST_SCHEDULE',
            tk.BooleanVar(value=self.settings_dict.get('YOUTUBE_LIVE_AUTO_POST_SCHEDULE', 'true').lower() == 'true'))
        ttk.Checkbutton(
            frame,
            text="📌 予約枠（upcoming）を投稿",
            variable=youtube_live_schedule_var
        ).pack(anchor=tk.W, pady=5)

        # YOUTUBE_LIVE_AUTO_POST_LIVE
        youtube_live_live_var = self.ui_vars.get('YOUTUBE_LIVE_AUTO_POST_LIVE',
            tk.BooleanVar(value=self.settings_dict.get('YOUTUBE_LIVE_AUTO_POST_LIVE', 'true').lower() == 'true'))
        ttk.Checkbutton(
            frame,
            text="🔴 配信中・終了（live/completed）を投稿",
            variable=youtube_live_live_var
        ).pack(anchor=tk.W, pady=5)

        # YOUTUBE_LIVE_AUTO_POST_ARCHIVE
        youtube_live_archive_var = self.ui_vars.get('YOUTUBE_LIVE_AUTO_POST_ARCHIVE',
            tk.BooleanVar(value=self.settings_dict.get('YOUTUBE_LIVE_AUTO_POST_ARCHIVE', 'true').lower() == 'true'))
        ttk.Checkbutton(
            frame,
            text="🎬 アーカイブ公開を投稿",
            variable=youtube_live_archive_var
        ).pack(anchor=tk.W, pady=5)

    def _build_subtab_live_delay(self, parent_notebook):
        """タブ 4-2: 投稿遅延"""
        sub_tab = ttk.Frame(parent_notebook)
        parent_notebook.add(sub_tab, text="⏳ 遅延")

        frame = ttk.Frame(sub_tab, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="配信開始後、いつ投稿するか", font=("", 10, "bold")).pack(anchor=tk.W, pady=5)

        # YOUTUBE_LIVE_POST_DELAY
        post_delay_var = tk.StringVar(
            value=self.settings_dict.get('YOUTUBE_LIVE_POST_DELAY', 'immediate')
        )
        self.ui_vars['YOUTUBE_LIVE_POST_DELAY'] = post_delay_var

        ttk.Radiobutton(
            frame,
            text="⚡ 即座に投稿（検知直後）",
            variable=post_delay_var,
            value='immediate'
        ).pack(anchor=tk.W, pady=3)

        ttk.Radiobutton(
            frame,
            text="⏰ 5分後に投稿（確認後）",
            variable=post_delay_var,
            value='delay_5min'
        ).pack(anchor=tk.W, pady=3)

        ttk.Radiobutton(
            frame,
            text="🕐 30分後に投稿（安定化後）",
            variable=post_delay_var,
            value='delay_30min'
        ).pack(anchor=tk.W, pady=3)

    def _build_subtab_live_filter(self, parent_notebook):
        """タブ 4-3: フィルタ"""
        sub_tab = ttk.Frame(parent_notebook)
        parent_notebook.add(sub_tab, text="🎬 フィルタ")

        frame = ttk.Frame(sub_tab, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Live配信の種別フィルタ", font=("", 10, "bold")).pack(anchor=tk.W, pady=5)

        # AUTOPOST_INCLUDE_PREMIERE
        autopost_premiere_var = self.ui_vars.get('AUTOPOST_INCLUDE_PREMIERE',
            tk.BooleanVar(value=self.settings_dict.get('AUTOPOST_INCLUDE_PREMIERE', 'true').lower() == 'true'))
        ttk.Checkbutton(
            frame,
            text="⭐ プレミア配信を投稿",
            variable=autopost_premiere_var
        ).pack(anchor=tk.W, pady=5)

        # 非対応項目
        ttk.Separator(frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
        ttk.Label(frame, text="以下の項目は非対応です(将来的な対応予定もありません)", font=("", 9, "bold"), foreground="gray").pack(anchor=tk.W, pady=5)

        ttk.Checkbutton(frame, text="🎥 YouTube Shorts", state='disabled').pack(anchor=tk.W, pady=3)
        ttk.Checkbutton(frame, text="👥 メンバー限定動画", state='disabled').pack(anchor=tk.W, pady=3)

    def _build_subtab_live_polling(self, parent_notebook):
        """タブ 4-4: ポーリング設定"""
        sub_tab = ttk.Frame(parent_notebook)
        parent_notebook.add(sub_tab, text="🔄 ポーリング")

        frame = ttk.Frame(sub_tab, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        # YOUTUBE_LIVE_POLL_INTERVAL_ACTIVE
        ttk.Label(frame, text="ACTIVE 時のポーリング間隔", font=("", 10, "bold")).grid(row=0, column=0, sticky=tk.W, pady=5)
        active_interval_var = tk.StringVar(
            value=self.settings_dict.get('YOUTUBE_LIVE_POLL_INTERVAL_ACTIVE', '15')
        )
        self.ui_vars['YOUTUBE_LIVE_POLL_INTERVAL_ACTIVE'] = active_interval_var
        ttk.Spinbox(
            frame,
            from_=15, to=60,
            textvariable=active_interval_var,
            width=10
        ).grid(row=0, column=1, sticky=tk.W, padx=5)
        ttk.Label(frame, text="分（15-60）", foreground='gray').grid(row=0, column=2, sticky=tk.W)

        # YOUTUBE_LIVE_POLL_INTERVAL_COMPLETED_MIN
        ttk.Label(frame, text="COMPLETED のみ時：最短確認間隔", font=("", 10, "bold")).grid(row=1, column=0, sticky=tk.W, pady=5)
        completed_min_var = tk.StringVar(
            value=self.settings_dict.get('YOUTUBE_LIVE_POLL_INTERVAL_COMPLETED_MIN', '60')
        )
        self.ui_vars['YOUTUBE_LIVE_POLL_INTERVAL_COMPLETED_MIN'] = completed_min_var
        ttk.Spinbox(
            frame,
            from_=30, to=180,
            textvariable=completed_min_var,
            width=10
        ).grid(row=1, column=1, sticky=tk.W, padx=5)
        ttk.Label(frame, text="分（30-180）", foreground='gray').grid(row=1, column=2, sticky=tk.W)

        # YOUTUBE_LIVE_POLL_INTERVAL_COMPLETED_MAX
        ttk.Label(frame, text="COMPLETED のみ時：最大確認間隔", font=("", 10, "bold")).grid(row=2, column=0, sticky=tk.W, pady=5)
        completed_max_var = tk.StringVar(
            value=self.settings_dict.get('YOUTUBE_LIVE_POLL_INTERVAL_COMPLETED_MAX', '180')
        )
        self.ui_vars['YOUTUBE_LIVE_POLL_INTERVAL_COMPLETED_MAX'] = completed_max_var
        ttk.Spinbox(
            frame,
            from_=30, to=180,
            textvariable=completed_max_var,
            width=10
        ).grid(row=2, column=1, sticky=tk.W, padx=5)
        ttk.Label(frame, text="分（30-180）", foreground='gray').grid(row=2, column=2, sticky=tk.W)

        # YOUTUBE_LIVE_ARCHIVE_CHECK_COUNT_MAX
        ttk.Label(frame, text="ARCHIVE 化後の最大追跡回数", font=("", 10, "bold")).grid(row=3, column=0, sticky=tk.W, pady=5)
        archive_check_count_var = tk.StringVar(
            value=self.settings_dict.get('YOUTUBE_LIVE_ARCHIVE_CHECK_COUNT_MAX', '4')
        )
        self.ui_vars['YOUTUBE_LIVE_ARCHIVE_CHECK_COUNT_MAX'] = archive_check_count_var
        ttk.Spinbox(
            frame,
            from_=1, to=10,
            textvariable=archive_check_count_var,
            width=10
        ).grid(row=3, column=1, sticky=tk.W, padx=5)
        ttk.Label(frame, text="回（1-10）", foreground='gray').grid(row=3, column=2, sticky=tk.W)

        # YOUTUBE_LIVE_ARCHIVE_CHECK_INTERVAL
        ttk.Label(frame, text="ARCHIVE 化後の確認間隔", font=("", 10, "bold")).grid(row=4, column=0, sticky=tk.W, pady=5)
        archive_interval_var = tk.StringVar(
            value=self.settings_dict.get('YOUTUBE_LIVE_ARCHIVE_CHECK_INTERVAL', '180')
        )
        self.ui_vars['YOUTUBE_LIVE_ARCHIVE_CHECK_INTERVAL'] = archive_interval_var
        ttk.Spinbox(
            frame,
            from_=30, to=480,
            textvariable=archive_interval_var,
            width=10
        ).grid(row=4, column=1, sticky=tk.W, padx=5)
        ttk.Label(frame, text="分（30-480）", foreground='gray').grid(row=4, column=2, sticky=tk.W)

    def _build_subtab_live_cache(self, parent_notebook):
        """★ 【v3.3.3】タブ 4-5: キャッシュ管理"""
        sub_tab = ttk.Frame(parent_notebook)
        parent_notebook.add(sub_tab, text="💾 キャッシュ管理")

        frame = ttk.Frame(sub_tab, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        # タイトル
        ttk.Label(frame, text="YouTube キャッシュ管理", font=("", 10, "bold")).pack(anchor=tk.W, pady=10)
        ttk.Label(frame, text="注意：実行中は複数回実行できません（1起動1回）", foreground='red').pack(anchor=tk.W, pady=5)

        # ボタン用フレーム
        button_frame = ttk.LabelFrame(frame, text="キャッシュ操作", padding=10)
        button_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        # ボタン状態フラグ（クラス変数として保持）
        if not hasattr(self, '_cache_operation_running'):
            self._cache_operation_running = False

        # 1. LIVEキャッシュをクリア
        ttk.Button(
            button_frame,
            text="🗑️ LIVEキャッシュをクリア",
            command=self._on_clear_live_cache
        ).pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(button_frame, text="Live（schedule/live/completed/archive）のキャッシュをすべてクリア",
                  foreground='gray', font=("", 8)).pack(anchor=tk.W, padx=10, pady=2)

        # 2. Schedule キャッシュを更新
        ttk.Button(
            button_frame,
            text="📅 Schedule キャッシュを更新",
            command=self._on_update_schedule_cache
        ).pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(button_frame, text="Schedule 状態の Live がなければスキップ（1時間未満なら更新しない）",
                  foreground='gray', font=("", 8)).pack(anchor=tk.W, padx=10, pady=2)

        # 3. LIVE（upcoming/live/end）キャッシュを更新
        ttk.Button(
            button_frame,
            text="🔴 LIVE キャッシュを更新",
            command=self._on_update_live_cache
        ).pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(button_frame, text="Upcoming/Live/End 状態の Live がなければスキップ（1時間未満なら更新しない）",
                  foreground='gray', font=("", 8)).pack(anchor=tk.W, padx=10, pady=2)

        # 4. Archive キャッシュを更新
        ttk.Button(
            button_frame,
            text="🎬 Archive キャッシュを更新",
            command=self._on_update_archive_cache
        ).pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(button_frame, text="Archive 状態の Live がなければスキップ（1時間未満なら更新しない）",
                  foreground='gray', font=("", 8)).pack(anchor=tk.W, padx=10, pady=2)

        # 5. 動画（video）キャッシュを更新
        ttk.Button(
            button_frame,
            text="🎥 動画キャッシュを更新",
            command=self._on_update_video_cache
        ).pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(button_frame, text="通常動画がなければスキップ（7日以上前のキャッシュのみ更新）",
                  foreground='gray', font=("", 8)).pack(anchor=tk.W, padx=10, pady=2)

        # 6. キャッシュ強制更新
        ttk.Button(
            button_frame,
            text="⚡ キャッシュ強制更新（全件）",
            command=self._on_force_update_all_cache
        ).pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(button_frame, text="YouTube 全件キャッシュを更新（50件ごとバッチ処理、時間がかかります）",
                  foreground='red', font=("", 8)).pack(anchor=tk.W, padx=10, pady=2)

    def _on_clear_live_cache(self):
        """★ 【v3.3.3】LIVEキャッシュをクリア"""
        if self._cache_operation_running:
            messagebox.showwarning("警告", "キャッシュ操作が実行中です。終了を待ってください。")
            return

        if not messagebox.askyesno("確認", "Live（schedule/live/completed/archive）のキャッシュをクリアしますか？"):
            return

        self._cache_operation_running = True
        try:
            # DB から Live 関連をクリア
            if self.db:
                # youtube_live_cache テーブルをクリア
                try:
                    from deleted_video_cache import get_deleted_video_cache
                    deleted_cache = get_deleted_video_cache()

                    # Live 関連動画をクリア（簡略版：DB から取得して削除）
                    videos = self.db.get_all_videos()
                    live_count = 0
                    for video in videos:
                        content_type = video.get('content_type', '')
                        if content_type in ['schedule', 'live', 'completed', 'archive']:
                            # キャッシュをクリア（DB の該当レコードを削除）
                            self.db.delete_video(video['video_id'])
                            live_count += 1

                    messagebox.showinfo("完了", f"✅ {live_count} 件の Live キャッシュをクリアしました")
                    logger.info(f"[キャッシュ管理] Live キャッシュをクリア: {live_count} 件")
                except Exception as e:
                    messagebox.showerror("エラー", f"❌ キャッシュクリア中にエラー:\n{e}")
                    logger.error(f"[キャッシュ管理] エラー: {e}")
            else:
                messagebox.showwarning("警告", "DB インスタンスが利用不可です")
        finally:
            self._cache_operation_running = False

    def _on_update_schedule_cache(self):
        """★ 【v3.3.3】Schedule キャッシュを更新"""
        if self._cache_operation_running:
            messagebox.showwarning("警告", "キャッシュ操作が実行中です。終了を待ってください。")
            return

        if not messagebox.askyesno("確認", "Schedule 状態の Live キャッシュを更新しますか？\n（1時間以内の更新済みはスキップします）"):
            return

        self._cache_operation_running = True
        try:
            self._update_cache_by_type('schedule')
        finally:
            self._cache_operation_running = False

    def _on_update_live_cache(self):
        """★ 【v3.3.3】LIVE（upcoming/live/end）キャッシュを更新"""
        if self._cache_operation_running:
            messagebox.showwarning("警告", "キャッシュ操作が実行中です。終了を待ってください。")
            return

        if not messagebox.askyesno("確認", "Upcoming/Live/End 状態の Live キャッシュを更新しますか？\n（1時間以内の更新済みはスキップします）"):
            return

        self._cache_operation_running = True
        try:
            self._update_cache_by_type('live')
        finally:
            self._cache_operation_running = False

    def _on_update_archive_cache(self):
        """★ 【v3.3.3】Archive キャッシュを更新"""
        if self._cache_operation_running:
            messagebox.showwarning("警告", "キャッシュ操作が実行中です。終了を待ってください。")
            return

        if not messagebox.askyesno("確認", "Archive 状態の Live キャッシュを更新しますか？\n（1時間以内の更新済みはスキップします）"):
            return

        self._cache_operation_running = True
        try:
            self._update_cache_by_type('archive')
        finally:
            self._cache_operation_running = False

    def _on_update_video_cache(self):
        """★ 【v3.3.3】動画（video）キャッシュを更新"""
        if self._cache_operation_running:
            messagebox.showwarning("警告", "キャッシュ操作が実行中です。終了を待ってください。")
            return

        if not messagebox.askyesno("確認", "動画キャッシュを更新しますか？\n（7日以上前のキャッシュのみ更新）"):
            return

        self._cache_operation_running = True
        try:
            self._update_cache_by_type('video')
        finally:
            self._cache_operation_running = False

    def _on_force_update_all_cache(self):
        """★ 【v3.3.3】キャッシュ強制更新（全件）"""
        if self._cache_operation_running:
            messagebox.showwarning("警告", "キャッシュ操作が実行中です。終了を待ってください。")
            return

        if not messagebox.askyesno("確認", "YouTube 全件キャッシュを強制更新しますか？\n（時間がかかる場合があります）"):
            return

        self._cache_operation_running = True
        try:
            self._update_cache_by_type('all')
        finally:
            self._cache_operation_running = False

    def _update_cache_by_type(self, cache_type):
        """★ 【v3.3.3】キャッシュを種別ごとに更新（共通メソッド）"""
        from datetime import datetime, timedelta

        try:
            if not self.db:
                messagebox.showwarning("警告", "DB インスタンスが利用不可です")
                return

            # API プラグイン取得
            try:
                from plugin_manager import get_plugin_manager
                plugin_mgr = get_plugin_manager()
                youtube_api_plugin = plugin_mgr.get_plugin("youtube_api_plugin")
                if not youtube_api_plugin or not youtube_api_plugin.is_available():
                    messagebox.showerror("エラー", "❌ YouTube API プラグインが利用不可です")
                    return
            except Exception as e:
                messagebox.showerror("エラー", f"❌ プラグイン取得エラー:\n{e}")
                return

            # Classifier 取得
            try:
                from youtube_core.youtube_video_classifier import get_video_classifier
                from config import get_config
                config = get_config("settings.env")
                classifier = get_video_classifier(api_key=config.youtube_api_key)
            except Exception as e:
                messagebox.showerror("エラー", f"❌ Classifier 取得エラー:\n{e}")
                return

            updated_count = 0
            skipped_count = 0
            error_count = 0

            if cache_type == 'schedule':
                # Schedule Live のみ更新
                videos = self.db.get_all_videos()
                for video in videos:
                    content_type = video.get('content_type', '')
                    if content_type == 'schedule':
                        if self._should_update_cache(video, cache_type='live'):
                            try:
                                classifier.classify_video(video['video_id'], force_refresh=True)
                                updated_count += 1
                            except Exception as e:
                                error_count += 1
                                logger.warning(f"[キャッシュ更新] エラー ({video['video_id']}): {e}")
                        else:
                            skipped_count += 1

            elif cache_type == 'live':
                # Upcoming/Live/End Live のみ更新
                videos = self.db.get_all_videos()
                for video in videos:
                    content_type = video.get('content_type', '')
                    if content_type in ['upcoming', 'live', 'end']:
                        if self._should_update_cache(video, cache_type='live'):
                            try:
                                classifier.classify_video(video['video_id'], force_refresh=True)
                                updated_count += 1
                            except Exception as e:
                                error_count += 1
                                logger.warning(f"[キャッシュ更新] エラー ({video['video_id']}): {e}")
                        else:
                            skipped_count += 1

            elif cache_type == 'archive':
                # Archive Live のみ更新
                videos = self.db.get_all_videos()
                for video in videos:
                    content_type = video.get('content_type', '')
                    if content_type == 'archive':
                        if self._should_update_cache(video, cache_type='live'):
                            try:
                                classifier.classify_video(video['video_id'], force_refresh=True)
                                updated_count += 1
                            except Exception as e:
                                error_count += 1
                                logger.warning(f"[キャッシュ更新] エラー ({video['video_id']}): {e}")
                        else:
                            skipped_count += 1

            elif cache_type == 'video':
                # 動画のみ更新（7日以上前）
                videos = self.db.get_all_videos()
                for video in videos:
                    content_type = video.get('content_type', '')
                    if content_type == 'video':
                        if self._should_update_cache(video, cache_type='video'):
                            try:
                                classifier.classify_video(video['video_id'], force_refresh=True)
                                updated_count += 1
                            except Exception as e:
                                error_count += 1
                                logger.warning(f"[キャッシュ更新] エラー ({video['video_id']}): {e}")
                        else:
                            skipped_count += 1

            elif cache_type == 'all':
                # 全件更新（50件ごとバッチ）
                videos = self.db.get_all_videos()
                batch_size = 50
                for i in range(0, len(videos), batch_size):
                    batch = videos[i:i+batch_size]
                    for video in batch:
                        try:
                            classifier.classify_video(video['video_id'], force_refresh=True)
                            updated_count += 1
                        except Exception as e:
                            error_count += 1
                            logger.warning(f"[キャッシュ更新] エラー ({video['video_id']}): {e}")

            # 結果を表示
            message = f"✅ キャッシュ更新完了\n\n更新: {updated_count} 件"
            if skipped_count > 0:
                message += f"\nスキップ: {skipped_count} 件"
            if error_count > 0:
                message += f"\nエラー: {error_count} 件"

            messagebox.showinfo("完了", message)
            logger.info(f"[キャッシュ管理] {cache_type} キャッシュ更新完了: 更新 {updated_count}, スキップ {skipped_count}, エラー {error_count}")

        except Exception as e:
            messagebox.showerror("エラー", f"❌ キャッシュ更新中にエラー:\n{e}")
            logger.error(f"[キャッシュ管理] エラー: {e}")

    def _should_update_cache(self, video, cache_type='live'):
        """★ 【v3.3.3】キャッシュを更新すべきかチェック"""
        from datetime import datetime, timedelta

        updated_at = video.get('updated_at')
        if not updated_at:
            return True  # 更新日時がなければ更新対象

        try:
            # 更新日時を解析
            last_update = datetime.fromisoformat(updated_at)
            now = datetime.now()
            diff = now - last_update

            if cache_type == 'live':
                # Live 関連：1時間未満なら更新しない
                return diff > timedelta(hours=1)
            else:  # video
                # 動画：7日以上前なら更新
                return diff > timedelta(days=7)

        except Exception as e:
            logger.warning(f"[キャッシュ更新] 日時解析エラー: {e}")
            return True  # エラー時は更新対象

    def _build_tab_templates(self):
        """タブ 5: テンプレート・画像（サブタブ 2分割）"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="📝 テンプレート")

        # サブタブ
        sub_notebook = ttk.Notebook(tab)
        sub_notebook.pack(fill=tk.BOTH, expand=True, padx=3, pady=3)

        # サブタブ 5-1: テンプレート
        self._build_subtab_templates_files(sub_notebook)

        # サブタブ 5-2: 画像設定
        self._build_subtab_templates_images(sub_notebook)

    def _build_subtab_templates_files(self, parent_notebook):
        """タブ 5-1: テンプレートファイル"""
        sub_tab = ttk.Frame(parent_notebook)
        parent_notebook.add(sub_tab, text="📄 テンプレート")

        # スクロール対応フレーム
        canvas = tk.Canvas(sub_tab, highlightthickness=0)
        scrollbar = ttk.Scrollbar(sub_tab, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        row = 0

        # YouTube テンプレート
        ttk.Label(scrollable_frame, text="📺 YouTube", font=("", 10, "bold")).grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=5, padx=5)
        row += 1

        # TEMPLATE_YOUTUBE_SCHEDULE_PATH
        ttk.Label(scrollable_frame, text="スケジュール:", font=("", 9)).grid(row=row, column=0, sticky=tk.W, pady=2, padx=5)
        youtube_schedule_var = tk.StringVar(
            value=self.settings_dict.get('TEMPLATE_YOUTUBE_SCHEDULE_PATH', '')
        )
        self.ui_vars['TEMPLATE_YOUTUBE_SCHEDULE_PATH'] = youtube_schedule_var
        entry = ttk.Entry(scrollable_frame, textvariable=youtube_schedule_var, width=40)
        entry.grid(row=row, column=1, sticky=tk.W, padx=5)
        ttk.Button(
            scrollable_frame,
            text="🗂️",
            width=2,
            command=lambda: self._browse_file(youtube_schedule_var)
        ).grid(row=row, column=2, sticky=tk.W, padx=2)
        row += 1

        # TEMPLATE_YOUTUBE_ONLINE_PATH
        ttk.Label(scrollable_frame, text="放送開始:", font=("", 9)).grid(row=row, column=0, sticky=tk.W, pady=2, padx=5)
        youtube_online_var = tk.StringVar(
            value=self.settings_dict.get('TEMPLATE_YOUTUBE_ONLINE_PATH', '')
        )
        self.ui_vars['TEMPLATE_YOUTUBE_ONLINE_PATH'] = youtube_online_var
        entry = ttk.Entry(scrollable_frame, textvariable=youtube_online_var, width=40)
        entry.grid(row=row, column=1, sticky=tk.W, padx=5)
        ttk.Button(
            scrollable_frame,
            text="🗂️",
            width=2,
            command=lambda: self._browse_file(youtube_online_var)
        ).grid(row=row, column=2, sticky=tk.W, padx=2)
        row += 1

        # TEMPLATE_YOUTUBE_OFFLINE_PATH
        ttk.Label(scrollable_frame, text="放送終了:", font=("", 9)).grid(row=row, column=0, sticky=tk.W, pady=2, padx=5)
        youtube_offline_var = tk.StringVar(
            value=self.settings_dict.get('TEMPLATE_YOUTUBE_OFFLINE_PATH', '')
        )
        self.ui_vars['TEMPLATE_YOUTUBE_OFFLINE_PATH'] = youtube_offline_var
        entry = ttk.Entry(scrollable_frame, textvariable=youtube_offline_var, width=40)
        entry.grid(row=row, column=1, sticky=tk.W, padx=5)
        ttk.Button(
            scrollable_frame,
            text="🗂️",
            width=2,
            command=lambda: self._browse_file(youtube_offline_var)
        ).grid(row=row, column=2, sticky=tk.W, padx=2)
        row += 1

        # TEMPLATE_YOUTUBE_ARCHIVE_PATH
        ttk.Label(scrollable_frame, text="放送アーカイブ:", font=("", 9)).grid(row=row, column=0, sticky=tk.W, pady=2, padx=5)
        youtube_archive_var = tk.StringVar(
            value=self.settings_dict.get('TEMPLATE_YOUTUBE_ARCHIVE_PATH', '')
        )
        self.ui_vars['TEMPLATE_YOUTUBE_ARCHIVE_PATH'] = youtube_archive_var
        entry = ttk.Entry(scrollable_frame, textvariable=youtube_archive_var, width=40)
        entry.grid(row=row, column=1, sticky=tk.W, padx=5)
        ttk.Button(
            scrollable_frame,
            text="🗂️",
            width=2,
            command=lambda: self._browse_file(youtube_archive_var)
        ).grid(row=row, column=2, sticky=tk.W, padx=2)
        row += 1

        # Niconico テンプレート
        ttk.Label(scrollable_frame, text="ニコニコ", font=("", 10, "bold")).grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=5, padx=5)
        row += 1

        # TEMPLATE_TEMPLATE_NICO_NEW_VIDEO_PATH
        ttk.Label(scrollable_frame, text="新規動画投稿:", font=("", 9)).grid(row=row, column=0, sticky=tk.W, pady=2, padx=5)
        nico_online_var = tk.StringVar(
            value=self.settings_dict.get('TEMPLATE_NICO_NEW_VIDEO_PATH', '')
        )
        self.ui_vars['TEMPLATE_NICO_NEW_VIDEO_PATH'] = nico_online_var
        entry = ttk.Entry(scrollable_frame, textvariable=nico_online_var, width=40)
        entry.grid(row=row, column=1, sticky=tk.W, padx=5)
        ttk.Button(
            scrollable_frame,
            text="🗂️",
            width=2,
            command=lambda: self._browse_file(nico_online_var)
        ).grid(row=row, column=2, sticky=tk.W, padx=2)
        row += 1


        # Twitch テンプレート（グレーアウト）
        ttk.Label(scrollable_frame, text="Twitch（対応予定）", font=("", 10, "bold"), foreground="gray").grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=5, padx=5)
        row += 1

        ttk.Label(scrollable_frame, text="放送開始:", font=("", 9), foreground="gray").grid(row=row, column=0, sticky=tk.W, pady=2, padx=5)
        twitch_online_var = tk.StringVar(value=self.settings_dict.get('TEMPLATE_TWITCH_ONLINE_PATH', ''))
        self.ui_vars['TEMPLATE_TWITCH_ONLINE_PATH'] = twitch_online_var
        ttk.Entry(scrollable_frame, textvariable=twitch_online_var, width=40, state='disabled').grid(row=row, column=1, sticky=tk.W, padx=5)
        ttk.Button(scrollable_frame, text="🗂️", width=2, state='disabled').grid(row=row, column=2, sticky=tk.W, padx=2)
        row += 1

        ttk.Label(scrollable_frame, text="放送終了(通常):", font=("", 9), foreground="gray").grid(row=row, column=0, sticky=tk.W, pady=2, padx=5)
        twitch_offline_var = tk.StringVar(value=self.settings_dict.get('TEMPLATE_TWITCH_OFFLINE_PATH', ''))
        self.ui_vars['TEMPLATE_TWITCH_OFFLINE_PATH'] = twitch_offline_var
        ttk.Entry(scrollable_frame, textvariable=twitch_offline_var, width=40, state='disabled').grid(row=row, column=1, sticky=tk.W, padx=5)
        ttk.Button(scrollable_frame, text="🗂️", width=2, state='disabled').grid(row=row, column=2, sticky=tk.W, padx=2)
        row += 1

        ttk.Label(scrollable_frame, text="放送終了(Raid):", font=("", 9), foreground="gray").grid(row=row, column=0, sticky=tk.W, pady=2, padx=5)
        twitch_raid_var = tk.StringVar(value=self.settings_dict.get('TEMPLATE_TWITCH_RAID_PATH', ''))
        self.ui_vars['TEMPLATE_TWITCH_RAID_PATH'] = twitch_raid_var
        ttk.Entry(scrollable_frame, textvariable=twitch_raid_var, width=40, state='disabled').grid(row=row, column=1, sticky=tk.W, padx=5)
        ttk.Button(scrollable_frame, text="🗂️", width=2, state='disabled').grid(row=row, column=2, sticky=tk.W, padx=2)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def _build_subtab_templates_images(self, parent_notebook):
        """タブ 5-2: 画像設定"""
        sub_tab = ttk.Frame(parent_notebook)
        parent_notebook.add(sub_tab, text="🖼️ 画像")

        frame = ttk.Frame(sub_tab, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        # BLUESKY_IMAGE_PATH
        ttk.Label(frame, text="デフォルトnoimage画像のパス", font=("", 9, "bold")).grid(row=0, column=0, sticky=tk.W, pady=3)
        image_path_var = tk.StringVar(
            value=self.settings_dict.get('BLUESKY_IMAGE_PATH', '')
        )
        self.ui_vars['BLUESKY_IMAGE_PATH'] = image_path_var
        entry = ttk.Entry(frame, textvariable=image_path_var, width=40)
        entry.grid(row=0, column=1, sticky=tk.W, padx=3)
        ttk.Button(
            frame,
            text="📁 フォルダ選択",
            command=lambda: self._browse_directory(image_path_var)
        ).grid(row=0, column=2, sticky=tk.W, padx=3)

        # IMAGE_RESIZE_TARGET_WIDTH
        ttk.Label(frame, text="横長画像の幅", font=("", 9, "bold")).grid(row=1, column=0, sticky=tk.W, pady=3)
        image_width_var = tk.StringVar(
            value=self.settings_dict.get('IMAGE_RESIZE_TARGET_WIDTH', '1200')
        )
        self.ui_vars['IMAGE_RESIZE_TARGET_WIDTH'] = image_width_var
        ttk.Spinbox(
            frame,
            from_=100, to=3840,
            textvariable=image_width_var,
            width=10
        ).grid(row=1, column=1, sticky=tk.W, padx=3)
        ttk.Label(frame, text="px（100-3840px,デフォルト: 1200）", foreground='gray').grid(row=1, column=2, sticky=tk.W)

        # IMAGE_RESIZE_TARGET_HEIGHT
        ttk.Label(frame, text="横長画像の高さ", font=("", 9, "bold")).grid(row=2, column=0, sticky=tk.W, pady=3)
        image_height_var = tk.StringVar(
            value=self.settings_dict.get('IMAGE_RESIZE_TARGET_HEIGHT', '800')
        )
        self.ui_vars['IMAGE_RESIZE_TARGET_HEIGHT'] = image_height_var
        ttk.Spinbox(
            frame,
            from_=100, to=2160,
            textvariable=image_height_var,
            width=10
        ).grid(row=2, column=1, sticky=tk.W, padx=3)
        ttk.Label(frame, text="px（100-2160px,デフォルト: 800）", foreground='gray').grid(row=2, column=2, sticky=tk.W)

        # IMAGE_OUTPUT_QUALITY_INITIAL
        ttk.Label(frame, text="JPEG初期出力品質", font=("", 9, "bold")).grid(row=5, column=0, sticky=tk.W, pady=3)
        quality_var = tk.StringVar(
            value=self.settings_dict.get('IMAGE_OUTPUT_QUALITY_INITIAL', '90')
        )
        self.ui_vars['IMAGE_OUTPUT_QUALITY_INITIAL'] = quality_var
        ttk.Spinbox(
            frame,
            from_=1, to=100,
            textvariable=quality_var,
            width=10
        ).grid(row=5, column=1, sticky=tk.W, padx=3)
        ttk.Label(frame, text="（1-100,デフォルト: 90）", foreground='gray').grid(row=5, column=2, sticky=tk.W)

        # IMAGE_SIZE_TARGET
        ttk.Label(frame, text="ファイルサイズ目標値", font=("", 9, "bold")).grid(row=6, column=0, sticky=tk.W, pady=3)
        size_target_var = tk.StringVar(
            value=self.settings_dict.get('IMAGE_SIZE_TARGET', '800000')
        )
        self.ui_vars['IMAGE_SIZE_TARGET'] = size_target_var
        ttk.Spinbox(
            frame,
            from_=100000, to=2000000,
            textvariable=size_target_var,
            width=10
        ).grid(row=6, column=1, sticky=tk.W, padx=3)
        ttk.Label(frame, text="Bytes（800KB推奨）", foreground='gray').grid(row=6, column=2, sticky=tk.W)

        # IMAGE_SIZE_THRESHOLD
        ttk.Label(frame, text="ファイルサイズ変換閾値", font=("", 9, "bold")).grid(row=7, column=0, sticky=tk.W, pady=3)
        size_threshold_var = tk.StringVar(
            value=self.settings_dict.get('IMAGE_SIZE_THRESHOLD', '900000')
        )
        self.ui_vars['IMAGE_SIZE_THRESHOLD'] = size_threshold_var
        ttk.Spinbox(
            frame,
            from_=100000, to=2000000,
            textvariable=size_threshold_var,
            width=10
        ).grid(row=7, column=1, sticky=tk.W, padx=3)
        ttk.Label(frame, text="Bytes（900KB推奨）", foreground='gray').grid(row=7, column=2, sticky=tk.W)

        # IMAGE_SIZE_LIMIT
        ttk.Label(frame, text="ファイルサイズ上限", font=("", 9, "bold")).grid(row=8, column=0, sticky=tk.W, pady=3)
        size_limit_var = tk.StringVar(
            value=self.settings_dict.get('IMAGE_SIZE_LIMIT', '1000000')
        )
        self.ui_vars['IMAGE_SIZE_LIMIT'] = size_limit_var
        ttk.Spinbox(
            frame,
            from_=500000, to=2000000,
            textvariable=size_limit_var,
            width=10
        ).grid(row=8, column=1, sticky=tk.W, padx=3)
        ttk.Label(frame, text="Bytes（1MB推奨）", foreground='gray').grid(row=8, column=2, sticky=tk.W)

    def _build_tab_logging(self):
        """タブ 6: ログ設定"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="📋 ログ")

        # スクロール対応フレーム
        canvas = tk.Canvas(tab, highlightthickness=0)
        scrollbar = ttk.Scrollbar(tab, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        row = 0
        ttk.Label(scrollable_frame, text="ロガー設定(全般設定)", font=("", 10, "bold")).grid(row=row, column=0, columnspan=3, sticky=tk.W, pady=3, padx=5)
        row += 1

        # LOG_LEVEL_CONSOLE
        ttk.Label(scrollable_frame, text="LOG_LEVEL_CONSOLE", font=("", 9, "bold")).grid(row=row, column=0, sticky=tk.W, pady=3, padx=5)
        console_level_var = tk.StringVar(
            value=self.settings_dict.get('LOG_LEVEL_CONSOLE', 'INFO')
        )
        self.ui_vars['LOG_LEVEL_CONSOLE'] = console_level_var
        ttk.Combobox(
            scrollable_frame,
            textvariable=console_level_var,
            values=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
            state='readonly',
            width=15
        ).grid(row=row, column=1, sticky=tk.W, padx=5)
        ttk.Label(scrollable_frame, text="コンソール出力レベル", foreground='gray').grid(row=row, column=2, sticky=tk.W)
        row += 1

        # LOG_LEVEL_FILE
        ttk.Label(scrollable_frame, text="LOG_LEVEL_FILE", font=("", 9, "bold")).grid(row=row, column=0, sticky=tk.W, pady=3, padx=5)
        file_level_var = tk.StringVar(
            value=self.settings_dict.get('LOG_LEVEL_FILE', 'DEBUG')
        )
        self.ui_vars['LOG_LEVEL_FILE'] = file_level_var
        ttk.Combobox(
            scrollable_frame,
            textvariable=file_level_var,
            values=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
            state='readonly',
            width=15
        ).grid(row=row, column=1, sticky=tk.W, padx=5)
        ttk.Label(scrollable_frame, text="ファイル出力レベル", foreground='gray').grid(row=row, column=2, sticky=tk.W)
        row += 1

        # LOG_RETENTION_DAYS
        ttk.Label(scrollable_frame, text="ログファイル保持日数", font=("", 9, "bold")).grid(row=row, column=0, sticky=tk.W, pady=3, padx=5)
        retention_days_var = tk.StringVar(
            value=self.settings_dict.get('LOG_RETENTION_DAYS', '30')
        )
        self.ui_vars['LOG_RETENTION_DAYS'] = retention_days_var
        ttk.Spinbox(
            scrollable_frame,
            from_=1, to=365,
            textvariable=retention_days_var,
            width=10
        ).grid(row=row, column=1, sticky=tk.W, padx=5)
        ttk.Label(scrollable_frame, text="日(範囲：1-365日）", foreground='gray').grid(row=row, column=2, sticky=tk.W)
        row += 1

        # セパレータ
        ttk.Separator(scrollable_frame, orient=tk.HORIZONTAL).grid(row=row, column=0, columnspan=3, sticky=tk.EW, pady=10, padx=5)
        row += 1

        ttk.Label(scrollable_frame, text="個別ロガー設定", font=("", 10, "bold")).grid(row=row, column=0, columnspan=3, sticky=tk.W, pady=3, padx=5)
        row += 1
        # LOG_LEVEL_APP
        ttk.Label(scrollable_frame, text="LOG_LEVEL_APP", font=("", 9, "bold")).grid(row=row, column=0, sticky=tk.W, pady=3, padx=5)
        app_level_var = tk.StringVar(
            value=self.settings_dict.get('LOG_LEVEL_APP', 'INFO')
        )
        self.ui_vars['LOG_LEVEL_APP'] = app_level_var
        ttk.Combobox(
            scrollable_frame,
            textvariable=app_level_var,
            values=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
            state='readonly',
            width=15
        ).grid(row=row, column=1, sticky=tk.W, padx=5)
        ttk.Label(scrollable_frame, text="アプリログレベル", foreground='gray').grid(row=row, column=2, sticky=tk.W)
        row += 1

        # LOG_LEVEL_AUDIT
        ttk.Label(scrollable_frame, text="LOG_LEVEL_AUDIT", font=("", 9, "bold")).grid(row=row, column=0, sticky=tk.W, pady=3, padx=5)
        audit_level_var = tk.StringVar(
            value=self.settings_dict.get('LOG_LEVEL_AUDIT', '')
        )
        self.ui_vars['LOG_LEVEL_AUDIT'] = audit_level_var
        ttk.Combobox(
            scrollable_frame,
            textvariable=audit_level_var,
            values=['', 'DEBUG', 'INFO', 'WARNING', 'ERROR'],
            width=15
        ).grid(row=row, column=1, sticky=tk.W, padx=5)
        ttk.Label(scrollable_frame, text="監査ログレベル", foreground='gray').grid(row=row, column=2, sticky=tk.W)
        row += 1

        # LOG_LEVEL_THUMBNAILS
        ttk.Label(scrollable_frame, text="LOG_LEVEL_THUMBNAILS", font=("", 9, "bold")).grid(row=row, column=0, sticky=tk.W, pady=3, padx=5)
        thumb_level_var = tk.StringVar(
            value=self.settings_dict.get('LOG_LEVEL_THUMBNAILS', '')
        )
        self.ui_vars['LOG_LEVEL_THUMBNAILS'] = thumb_level_var
        ttk.Combobox(
            scrollable_frame,
            textvariable=thumb_level_var,
            values=['', 'DEBUG', 'INFO', 'WARNING', 'ERROR'],
            width=15
        ).grid(row=row, column=1, sticky=tk.W, padx=5)
        ttk.Label(scrollable_frame, text="サムネイル再取得ログ", foreground='gray').grid(row=row, column=2, sticky=tk.W)
        row += 1

        # LOG_LEVEL_TUNNEL
        ttk.Label(scrollable_frame, text="LOG_LEVEL_TUNNEL", font=("", 9, "bold")).grid(row=row, column=0, sticky=tk.W, pady=3, padx=5)
        tunnel_level_var = tk.StringVar(
            value=self.settings_dict.get('LOG_LEVEL_TUNNEL', '')
        )
        self.ui_vars['LOG_LEVEL_TUNNEL'] = tunnel_level_var
        ttk.Combobox(
            scrollable_frame,
            textvariable=tunnel_level_var,
            values=['', 'DEBUG', 'INFO', 'WARNING', 'ERROR'],
            width=15
        ).grid(row=row, column=1, sticky=tk.W, padx=5)
        ttk.Label(scrollable_frame, text="トンネル接続ログ", foreground='gray').grid(row=row, column=2, sticky=tk.W)
        row += 1

        # LOG_LEVEL_YOUTUBE
        ttk.Label(scrollable_frame, text="LOG_LEVEL_YOUTUBE", font=("", 9, "bold")).grid(row=row, column=0, sticky=tk.W, pady=3, padx=5)
        youtube_level_var = tk.StringVar(
            value=self.settings_dict.get('LOG_LEVEL_YOUTUBE', '')
        )
        self.ui_vars['LOG_LEVEL_YOUTUBE'] = youtube_level_var
        ttk.Combobox(
            scrollable_frame,
            textvariable=youtube_level_var,
            values=['', 'DEBUG', 'INFO', 'WARNING', 'ERROR'],
            width=15
        ).grid(row=row, column=1, sticky=tk.W, padx=5)
        ttk.Label(scrollable_frame, text="YouTube監視ログ", foreground='gray').grid(row=row, column=2, sticky=tk.W)
        row += 1

        # LOG_LEVEL_NICONICO
        ttk.Label(scrollable_frame, text="LOG_LEVEL_NICONICO", font=("", 9, "bold")).grid(row=row, column=0, sticky=tk.W, pady=3, padx=5)
        nico_level_var = tk.StringVar(
            value=self.settings_dict.get('LOG_LEVEL_NICONICO', '')
        )
        self.ui_vars['LOG_LEVEL_NICONICO'] = nico_level_var
        ttk.Combobox(
            scrollable_frame,
            textvariable=nico_level_var,
            values=['', 'DEBUG', 'INFO', 'WARNING', 'ERROR'],
            width=15
        ).grid(row=row, column=1, sticky=tk.W, padx=5)
        ttk.Label(scrollable_frame, text="Niconico監視ログ", foreground='gray').grid(row=row, column=2, sticky=tk.W)
        row += 1

        # LOG_LEVEL_GUI
        ttk.Label(scrollable_frame, text="LOG_LEVEL_GUI", font=("", 9, "bold")).grid(row=row, column=0, sticky=tk.W, pady=3, padx=5)
        gui_level_var = tk.StringVar(
            value=self.settings_dict.get('LOG_LEVEL_GUI', '')
        )
        self.ui_vars['LOG_LEVEL_GUI'] = gui_level_var
        ttk.Combobox(
            scrollable_frame,
            textvariable=gui_level_var,
            values=['', 'DEBUG', 'INFO', 'WARNING', 'ERROR'],
            width=15
        ).grid(row=row, column=1, sticky=tk.W, padx=5)
        ttk.Label(scrollable_frame, text="GUI操作ログ", foreground='gray').grid(row=row, column=2, sticky=tk.W)
        row += 1

        # LOG_LEVEL_POST
        ttk.Label(scrollable_frame, text="LOG_LEVEL_POST", font=("", 9, "bold")).grid(row=row, column=0, sticky=tk.W, pady=3, padx=5)
        post_level_var = tk.StringVar(
            value=self.settings_dict.get('LOG_LEVEL_POST', 'INFO')
        )
        self.ui_vars['LOG_LEVEL_POST'] = post_level_var
        ttk.Combobox(
            scrollable_frame,
            textvariable=post_level_var,
            values=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
            state='readonly',
            width=15
        ).grid(row=row, column=1, sticky=tk.W, padx=5)
        ttk.Label(scrollable_frame, text="投稿ログレベル", foreground='gray').grid(row=row, column=2, sticky=tk.W)
        row += 1

        # LOG_LEVEL_POST_ERROR
        ttk.Label(scrollable_frame, text="LOG_LEVEL_POST_ERROR", font=("", 9, "bold")).grid(row=row, column=0, sticky=tk.W, pady=3, padx=5)
        post_error_level_var = tk.StringVar(
            value=self.settings_dict.get('LOG_LEVEL_POST_ERROR', '')
        )
        self.ui_vars['LOG_LEVEL_POST_ERROR'] = post_error_level_var
        ttk.Combobox(
            scrollable_frame,
            textvariable=post_error_level_var,
            values=['', 'DEBUG', 'INFO', 'WARNING', 'ERROR'],
            width=15
        ).grid(row=row, column=1, sticky=tk.W, padx=5)
        ttk.Label(scrollable_frame, text="投稿エラーログ", foreground='gray').grid(row=row, column=2, sticky=tk.W)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def _build_tab_future(self):
        """タブ 7: 将来プラグイン（プレビュー）"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="🔮 将来機能")

        frame = ttk.Frame(tab, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="将来実装予定のプラグイン", font=("", 12, "bold")).pack(anchor=tk.W, pady=10)

        ttk.Label(frame, text="以下の機能は現在未実装です：", foreground='gray').pack(anchor=tk.W, pady=5)
        ttk.Label(frame, text="• Twitch API 連携").pack(anchor=tk.W)
        ttk.Label(frame, text="• ActivityPub 連携").pack(anchor=tk.W)
        ttk.Label(frame, text="• Discord 通知").pack(anchor=tk.W)

    def _activate_initial_tab(self):
        """初期タブをアクティブにする"""
        tab_map = {
            'basic': 0,
            'accounts': 1,
            'posting': 2,
            'live': 3,
            'templates': 4,
            'logging': 5,
            'future': 6,
        }

        index = tab_map.get(self.initial_tab, 0)
        self.notebook.select(index)

    def _save_all_settings(self):
        """全設定を settings.env に保存"""
        try:
            # すべての UI 変数から値を収集
            settings_to_save = {}

            for key, var in self.ui_vars.items():
                if isinstance(var, tk.BooleanVar):
                    settings_to_save[key] = str(var.get()).lower()
                else:
                    settings_to_save[key] = var.get()

            # settings.env を安全に更新
            self._update_settings_env_safely(settings_to_save)

            messagebox.showinfo(
                "成功",
                "設定を保存しました。\n\n※ アプリ再起動時に反映されます。"
            )
            logger.info("✅ 統合設定ウィンドウから設定を保存しました")
            self.window.destroy()

        except Exception as e:
            logger.error(f"❌ 設定の保存に失敗: {e}", exc_info=True)
            messagebox.showerror("エラー", f"設定の保存に失敗しました:\n{e}")

    def _update_settings_env_safely(self, settings_dict):
        """settings.env をセクション単位で安全に更新"""
        try:
            # バックアップを作成
            backup_file = self.settings_file.with_suffix('.backup')
            if self.settings_file.exists():
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    backup_content = f.read()
                with open(backup_file, 'w', encoding='utf-8') as f:
                    f.write(backup_content)
                logger.info(f"✅ settings.env のバックアップを作成: {backup_file}")

            # 既存ファイルを読み込み
            lines = []
            processed_keys = set()

            if self.settings_file.exists():
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        stripped = line.rstrip('\n')

                        # コメント行・空行は保持
                        if not stripped or stripped.startswith('#'):
                            lines.append(stripped)
                            continue

                        # キー=値の行
                        if '=' in stripped:
                            key = stripped.split('=', 1)[0].strip()

                            if key in settings_dict:
                                # 値を更新
                                value = settings_dict[key]

                                # コメント状態にすべき場合
                                if key in COMMENTED_KEYS and value.lower() == 'false':
                                    lines.append(f"#{key}={value}")
                                else:
                                    lines.append(f"{key}={value}")

                                processed_keys.add(key)
                            else:
                                # 元の行を保持
                                lines.append(stripped)
                        else:
                            lines.append(stripped)

            # 新規キーを末尾に追加
            for key, value in settings_dict.items():
                if key not in processed_keys:
                    lines.append(f"{key}={value}")

            # ファイルに書き込み
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines) + '\n')

            logger.info(f"✅ settings.env を更新しました（{len(processed_keys)}個のキー）")

        except Exception as e:
            logger.error(f"❌ settings.env の更新に失敗: {e}", exc_info=True)
            raise

    def _reset_to_defaults(self):
        """デフォルト値にリセット"""
        if messagebox.askyesno("確認", "すべての設定をデフォルト値にリセットしますか？"):
            logger.info("⚠️ 設定をデフォルト値にリセットしました")
            self.window.destroy()
            # 再度ウィンドウを開く
            UnifiedSettingsWindow(self.parent, initial_tab=self.initial_tab, db=self.db)

    def _browse_file(self, var):
        """ファイルブラウザを開く"""
        file_path = filedialog.askopenfilename(
            title="テンプレートファイルを選択",
            parent=self.window,
            filetypes=[("テンプレートファイル", "*.jinja2 *.txt *.html"), ("すべてのファイル", "*.*")]
        )
        if file_path:
            var.set(file_path)
            logger.info(f"ℹ️ ファイルを選択: {file_path}")

    def _browse_directory(self, var):
        """ディレクトリブラウザを開く"""
        dir_path = filedialog.askdirectory(
            title="画像フォルダを選択",
            parent=self.window
        )
        if dir_path:
            var.set(dir_path)
            logger.info(f"ℹ️ フォルダを選択: {dir_path}")
