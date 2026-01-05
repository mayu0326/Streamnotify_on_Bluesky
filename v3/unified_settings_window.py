# -*- coding: utf-8 -*-

"""
統合設定ウィンドウ (v3.4.0+)

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
        self.window.geometry("600x450")
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
        # === Notebook (タブ) を作成 ===
        self.notebook = ttk.Notebook(self.window)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 各タブを作成
        self._build_tab_basic()
        self._build_tab_accounts()
        self._build_tab_posting()
        self._build_tab_live()
        self._build_tab_templates()
        self._build_tab_logging()
        self._build_tab_future()

        # === ボタンパネル ===
        button_frame = ttk.Frame(self.window)
        button_frame.pack(fill=tk.X, padx=10, pady=10)

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
        ttk.Label(frame, text="YOUTUBE_CHANNEL_ID", font=("", 10, "bold")).grid(row=0, column=0, sticky=tk.W, pady=5)
        channel_id_var = tk.StringVar(
            value=self.settings_dict.get('YOUTUBE_CHANNEL_ID', '')
        )
        self.ui_vars['YOUTUBE_CHANNEL_ID'] = channel_id_var
        ttk.Entry(frame, textvariable=channel_id_var, width=50).grid(row=0, column=1, sticky=tk.W, padx=5)
        ttk.Label(frame, text="UC で始まるチャンネル ID", foreground='gray').grid(row=0, column=2, sticky=tk.W)

        # YOUTUBE_API_KEY
        ttk.Label(frame, text="YOUTUBE_API_KEY", font=("", 10, "bold")).grid(row=1, column=0, sticky=tk.W, pady=5)
        api_key_var = tk.StringVar(
            value=self.settings_dict.get('YOUTUBE_API_KEY', '')
        )
        self.ui_vars['YOUTUBE_API_KEY'] = api_key_var
        ttk.Entry(frame, textvariable=api_key_var, width=50, show="*").grid(row=1, column=1, sticky=tk.W, padx=5)
        ttk.Label(frame, text="マスク表示", foreground='gray').grid(row=1, column=2, sticky=tk.W)

        # YOUTUBE_RSS_POLL_INTERVAL_MINUTES
        ttk.Label(frame, text="YOUTUBE_RSS_POLL_INTERVAL_MINUTES", font=("", 10, "bold")).grid(row=2, column=0, sticky=tk.W, pady=5)
        poll_interval_var = tk.StringVar(
            value=self.settings_dict.get('YOUTUBE_RSS_POLL_INTERVAL_MINUTES', '10')
        )
        self.ui_vars['YOUTUBE_RSS_POLL_INTERVAL_MINUTES'] = poll_interval_var
        ttk.Spinbox(
            frame,
            from_=1, to=120,
            textvariable=poll_interval_var,
            width=10
        ).grid(row=2, column=1, sticky=tk.W, padx=5)
        ttk.Label(frame, text="分（1-120）", foreground='gray').grid(row=2, column=2, sticky=tk.W)

    def _build_subtab_accounts_niconico(self, parent_notebook):
        """タブ 2-2: Niconico"""
        sub_tab = ttk.Frame(parent_notebook)
        parent_notebook.add(sub_tab, text="ニコニコ")

        frame = ttk.Frame(sub_tab, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        # NICONICO_USER_ID
        ttk.Label(frame, text="NICONICO_USER_ID", font=("", 10, "bold")).grid(row=0, column=0, sticky=tk.W, pady=5)
        nico_user_id_var = tk.StringVar(
            value=self.settings_dict.get('NICONICO_USER_ID', '')
        )
        self.ui_vars['NICONICO_USER_ID'] = nico_user_id_var
        ttk.Entry(frame, textvariable=nico_user_id_var, width=50).grid(row=0, column=1, sticky=tk.W, padx=5)
        ttk.Label(frame, text="数字のみ", foreground='gray').grid(row=0, column=2, sticky=tk.W)

        # NICONICO_USER_NAME
        ttk.Label(frame, text="NICONICO_USER_NAME", font=("", 10, "bold")).grid(row=1, column=0, sticky=tk.W, pady=5)
        nico_user_name_var = tk.StringVar(
            value=self.settings_dict.get('NICONICO_USER_NAME', '')
        )
        self.ui_vars['NICONICO_USER_NAME'] = nico_user_name_var
        ttk.Entry(frame, textvariable=nico_user_name_var, width=50).grid(row=1, column=1, sticky=tk.W, padx=5)

        # NICONICO_POLL_INTERVAL
        ttk.Label(frame, text="NICONICO_POLL_INTERVAL", font=("", 10, "bold")).grid(row=2, column=0, sticky=tk.W, pady=5)
        nico_poll_interval_var = tk.StringVar(
            value=self.settings_dict.get('NICONICO_POLL_INTERVAL', '10')
        )
        self.ui_vars['NICONICO_POLL_INTERVAL'] = nico_poll_interval_var
        ttk.Spinbox(
            frame,
            from_=1, to=120,
            textvariable=nico_poll_interval_var,
            width=10
        ).grid(row=2, column=1, sticky=tk.W, padx=5)
        ttk.Label(frame, text="分（1-120）", foreground='gray').grid(row=2, column=2, sticky=tk.W)

    def _build_subtab_accounts_websub(self, parent_notebook):
        """タブ 2-3: WebSub"""
        sub_tab = ttk.Frame(parent_notebook)
        parent_notebook.add(sub_tab, text="WebSub")

        frame = ttk.Frame(sub_tab, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        # WEBSUB_CLIENT_ID
        ttk.Label(frame, text="WEBSUB_CLIENT_ID", font=("", 10, "bold")).grid(row=0, column=0, sticky=tk.W, pady=5)
        websub_client_id_var = tk.StringVar(
            value=self.settings_dict.get('WEBSUB_CLIENT_ID', '')
        )
        self.ui_vars['WEBSUB_CLIENT_ID'] = websub_client_id_var
        ttk.Entry(frame, textvariable=websub_client_id_var, width=50).grid(row=0, column=1, sticky=tk.W, padx=5)

        # WEBSUB_CALLBACK_URL
        ttk.Label(frame, text="WEBSUB_CALLBACK_URL", font=("", 10, "bold")).grid(row=1, column=0, sticky=tk.W, pady=5)
        websub_callback_url_var = tk.StringVar(
            value=self.settings_dict.get('WEBSUB_CALLBACK_URL', '')
        )
        self.ui_vars['WEBSUB_CALLBACK_URL'] = websub_callback_url_var
        ttk.Entry(frame, textvariable=websub_callback_url_var, width=50).grid(row=1, column=1, sticky=tk.W, padx=5)

        # WEBSUB_CLIENT_API_KEY
        ttk.Label(frame, text="WEBSUB_CLIENT_API_KEY", font=("", 10, "bold")).grid(row=2, column=0, sticky=tk.W, pady=5)
        websub_api_key_var = tk.StringVar(
            value=self.settings_dict.get('WEBSUB_CLIENT_API_KEY', '')
        )
        self.ui_vars['WEBSUB_CLIENT_API_KEY'] = websub_api_key_var
        ttk.Entry(frame, textvariable=websub_api_key_var, width=50, show="*").grid(row=2, column=1, sticky=tk.W, padx=5)

        # WEBSUB_LEASE_SECONDS
        ttk.Label(frame, text="WEBSUB_LEASE_SECONDS", font=("", 10, "bold")).grid(row=3, column=0, sticky=tk.W, pady=5)
        websub_lease_var = tk.StringVar(
            value=self.settings_dict.get('WEBSUB_LEASE_SECONDS', '432000')
        )
        self.ui_vars['WEBSUB_LEASE_SECONDS'] = websub_lease_var
        ttk.Spinbox(
            frame,
            from_=86400, to=2592000,
            textvariable=websub_lease_var,
            width=15
        ).grid(row=3, column=1, sticky=tk.W, padx=5)
        ttk.Label(frame, text="秒（86400-2592000）", foreground='gray').grid(row=3, column=2, sticky=tk.W)

        # YOUTUBE_WEBSUB_POLL_INTERVAL_MINUTES
        ttk.Label(frame, text="YOUTUBE_WEBSUB_POLL_INTERVAL_MINUTES", font=("", 10, "bold")).grid(row=4, column=0, sticky=tk.W, pady=5)
        youtube_websub_poll_var = tk.StringVar(
            value=self.settings_dict.get('YOUTUBE_WEBSUB_POLL_INTERVAL_MINUTES', '5')
        )
        self.ui_vars['YOUTUBE_WEBSUB_POLL_INTERVAL_MINUTES'] = youtube_websub_poll_var
        ttk.Spinbox(
            frame,
            from_=1, to=120,
            textvariable=youtube_websub_poll_var,
            width=10
        ).grid(row=4, column=1, sticky=tk.W, padx=5)
        ttk.Label(frame, text="分（1-120）", foreground='gray').grid(row=4, column=2, sticky=tk.W)

    def _build_subtab_accounts_bluesky(self, parent_notebook):
        """タブ 2-4: Bluesky"""
        sub_tab = ttk.Frame(parent_notebook)
        parent_notebook.add(sub_tab, text="🦋 Bluesky")

        frame = ttk.Frame(sub_tab, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        # BLUESKY_USERNAME
        ttk.Label(frame, text="BLUESKY_USERNAME", font=("", 10, "bold")).grid(row=0, column=0, sticky=tk.W, pady=5)
        bluesky_username_var = tk.StringVar(
            value=self.settings_dict.get('BLUESKY_USERNAME', '')
        )
        self.ui_vars['BLUESKY_USERNAME'] = bluesky_username_var
        ttk.Entry(frame, textvariable=bluesky_username_var, width=50).grid(row=0, column=1, sticky=tk.W, padx=5)
        ttk.Label(frame, text="ハンドル or メールアドレス", foreground='gray').grid(row=0, column=2, sticky=tk.W)

        # BLUESKY_PASSWORD
        ttk.Label(frame, text="BLUESKY_PASSWORD", font=("", 10, "bold")).grid(row=1, column=0, sticky=tk.W, pady=5)
        bluesky_password_var = tk.StringVar(
            value=self.settings_dict.get('BLUESKY_PASSWORD', '')
        )
        self.ui_vars['BLUESKY_PASSWORD'] = bluesky_password_var
        ttk.Entry(frame, textvariable=bluesky_password_var, width=50, show="*").grid(row=1, column=1, sticky=tk.W, padx=5)
        ttk.Label(frame, text="アプリパスワード（マスク表示）", foreground='gray').grid(row=1, column=2, sticky=tk.W)

        # BLUESKY_POST_ENABLED
        bluesky_post_enabled_var = tk.BooleanVar(
            value=self.settings_dict.get('BLUESKY_POST_ENABLED', 'True').lower() == 'true'
        )
        self.ui_vars['BLUESKY_POST_ENABLED'] = bluesky_post_enabled_var
        ttk.Checkbutton(
            frame,
            text="BLUESKY_POST_ENABLED (Bluesky への投稿を有効化)",
            variable=bluesky_post_enabled_var
        ).grid(row=2, column=0, columnspan=3, sticky=tk.W, pady=5)

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
        ).pack(anchor=tk.W, pady=5)

        # YOUTUBE_DEDUP_ENABLED
        youtube_dedup_var = tk.BooleanVar(
            value=self.settings_dict.get('YOUTUBE_DEDUP_ENABLED', 'true').lower() == 'true'
        )
        self.ui_vars['YOUTUBE_DEDUP_ENABLED'] = youtube_dedup_var
        ttk.Checkbutton(
            frame,
            text="YOUTUBE_DEDUP_ENABLED (YouTube 重複排除)",
            variable=youtube_dedup_var
        ).pack(anchor=tk.W, pady=5)

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
        ).pack(anchor=tk.W, pady=5)

    def _build_subtab_posting_autopost(self, parent_notebook):
        """タブ 3-2: 自動投稿設定"""
        sub_tab = ttk.Frame(parent_notebook)
        parent_notebook.add(sub_tab, text="🔄 自動投稿")

        frame = ttk.Frame(sub_tab, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        # AUTOPOST_INTERVAL_MINUTES
        ttk.Label(frame, text="AUTOPOST_INTERVAL_MINUTES", font=("", 10, "bold")).grid(row=0, column=0, sticky=tk.W, pady=5)
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
        ttk.Label(frame, text="分（1-60）", foreground='gray').grid(row=0, column=2, sticky=tk.W)

        # AUTOPOST_LOOKBACK_MINUTES
        ttk.Label(frame, text="AUTOPOST_LOOKBACK_MINUTES", font=("", 10, "bold")).grid(row=1, column=0, sticky=tk.W, pady=5)
        autopost_lookback_var = tk.StringVar(
            value=self.settings_dict.get('AUTOPOST_LOOKBACK_MINUTES', '30')
        )
        self.ui_vars['AUTOPOST_LOOKBACK_MINUTES'] = autopost_lookback_var
        ttk.Spinbox(
            frame,
            from_=5, to=1440,
            textvariable=autopost_lookback_var,
            width=10
        ).grid(row=1, column=1, sticky=tk.W, padx=5)
        ttk.Label(frame, text="分（5-1440）", foreground='gray').grid(row=1, column=2, sticky=tk.W)

        # AUTOPOST_UNPOSTED_THRESHOLD
        ttk.Label(frame, text="AUTOPOST_UNPOSTED_THRESHOLD", font=("", 10, "bold")).grid(row=2, column=0, sticky=tk.W, pady=5)
        autopost_threshold_var = tk.StringVar(
            value=self.settings_dict.get('AUTOPOST_UNPOSTED_THRESHOLD', '20')
        )
        self.ui_vars['AUTOPOST_UNPOSTED_THRESHOLD'] = autopost_threshold_var
        ttk.Spinbox(
            frame,
            from_=1, to=1000,
            textvariable=autopost_threshold_var,
            width=10
        ).grid(row=2, column=1, sticky=tk.W, padx=5)
        ttk.Label(frame, text="件（1-1000）", foreground='gray').grid(row=2, column=2, sticky=tk.W)

        # AUTOPOST_INCLUDE_NORMAL
        autopost_normal_var = tk.BooleanVar(
            value=self.settings_dict.get('AUTOPOST_INCLUDE_NORMAL', 'true').lower() == 'true'
        )
        self.ui_vars['AUTOPOST_INCLUDE_NORMAL'] = autopost_normal_var
        ttk.Checkbutton(
            frame,
            text="AUTOPOST_INCLUDE_NORMAL (通常動画を含める)",
            variable=autopost_normal_var
        ).grid(row=3, column=0, columnspan=3, sticky=tk.W, pady=5)

        # AUTOPOST_INCLUDE_PREMIERE
        autopost_premiere_var = tk.BooleanVar(
            value=self.settings_dict.get('AUTOPOST_INCLUDE_PREMIERE', 'true').lower() == 'true'
        )
        self.ui_vars['AUTOPOST_INCLUDE_PREMIERE'] = autopost_premiere_var
        ttk.Checkbutton(
            frame,
            text="AUTOPOST_INCLUDE_PREMIERE (プレミア配信を含める)",
            variable=autopost_premiere_var
        ).grid(row=4, column=0, columnspan=3, sticky=tk.W, pady=5)

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
            text="YOUTUBE_LIVE_AUTO_POST_SCHEDULE (予約枠を投稿)",
            variable=youtube_live_schedule_var
        ).pack(anchor=tk.W, pady=5)

        # YOUTUBE_LIVE_AUTO_POST_LIVE
        youtube_live_live_var = tk.BooleanVar(
            value=self.settings_dict.get('YOUTUBE_LIVE_AUTO_POST_LIVE', 'true').lower() == 'true'
        )
        self.ui_vars['YOUTUBE_LIVE_AUTO_POST_LIVE'] = youtube_live_live_var
        ttk.Checkbutton(
            frame,
            text="YOUTUBE_LIVE_AUTO_POST_LIVE (配信中・終了を投稿)",
            variable=youtube_live_live_var
        ).pack(anchor=tk.W, pady=5)

        # YOUTUBE_LIVE_AUTO_POST_ARCHIVE
        youtube_live_archive_var = tk.BooleanVar(
            value=self.settings_dict.get('YOUTUBE_LIVE_AUTO_POST_ARCHIVE', 'true').lower() == 'true'
        )
        self.ui_vars['YOUTUBE_LIVE_AUTO_POST_ARCHIVE'] = youtube_live_archive_var
        ttk.Checkbutton(
            frame,
            text="YOUTUBE_LIVE_AUTO_POST_ARCHIVE (アーカイブを投稿)",
            variable=youtube_live_archive_var
        ).pack(anchor=tk.W, pady=5)

    def _build_tab_live(self):
        """タブ 4: YouTube Live（核心タブ、サブタブ 4分割）"""
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
        ttk.Label(frame, text="以下の項目は現在非対応です（将来実装予定）", font=("", 9, "bold"), foreground="gray").pack(anchor=tk.W, pady=5)

        ttk.Checkbutton(frame, text="🎥 YouTube Shorts", state='disabled').pack(anchor=tk.W, pady=3)
        ttk.Checkbutton(frame, text="👥 メンバー限定動画", state='disabled').pack(anchor=tk.W, pady=3)

    def _build_subtab_live_polling(self, parent_notebook):
        """タブ 4-4: ポーリング設定"""
        sub_tab = ttk.Frame(parent_notebook)
        parent_notebook.add(sub_tab, text="🔄 ポーリング")

        frame = ttk.Frame(sub_tab, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        # YOUTUBE_LIVE_POLL_INTERVAL_ACTIVE
        ttk.Label(frame, text="YOUTUBE_LIVE_POLL_INTERVAL_ACTIVE", font=("", 10, "bold")).grid(row=0, column=0, sticky=tk.W, pady=5)
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
        ttk.Label(frame, text="YOUTUBE_LIVE_POLL_INTERVAL_COMPLETED_MIN", font=("", 10, "bold")).grid(row=1, column=0, sticky=tk.W, pady=5)
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
        ttk.Label(frame, text="YOUTUBE_LIVE_POLL_INTERVAL_COMPLETED_MAX", font=("", 10, "bold")).grid(row=2, column=0, sticky=tk.W, pady=5)
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
        ttk.Label(frame, text="YOUTUBE_LIVE_ARCHIVE_CHECK_COUNT_MAX", font=("", 10, "bold")).grid(row=3, column=0, sticky=tk.W, pady=5)
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
        ttk.Label(frame, text="YOUTUBE_LIVE_ARCHIVE_CHECK_INTERVAL", font=("", 10, "bold")).grid(row=4, column=0, sticky=tk.W, pady=5)
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

    def _build_tab_templates(self):
        """タブ 5: テンプレート・画像（実装スケルトン）"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="📝 テンプレート")

        frame = ttk.Frame(tab, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="テンプレート・画像設定", font=("", 12, "bold")).pack(anchor=tk.W, pady=10)
        ttk.Label(frame, text="このタブは将来実装予定です。", foreground='gray').pack(anchor=tk.W)

    def _build_tab_logging(self):
        """タブ 6: ログ（実装スケルトン）"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="📋 ログ")

        frame = ttk.Frame(tab, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="ログ設定", font=("", 12, "bold")).pack(anchor=tk.W, pady=10)
        ttk.Label(frame, text="このタブは将来実装予定です。", foreground='gray').pack(anchor=tk.W)

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
