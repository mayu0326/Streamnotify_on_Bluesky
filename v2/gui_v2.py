# -*- coding: utf-8 -*-

"""
Stream notify on Bluesky - v2 GUI（改善版）

DB の動画一覧を表示し、投稿対象をチェックボックスで選択・スケジュール管理。
tkinter を使用（標準ライブラリのみ）
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime, timedelta
import logging
import os
import sys
import calendar
from database import get_database
from image_manager import get_image_manager
from pathlib import Path

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

logger = logging.getLogger("GUILogger")

__author__ = "mayuneco(mayunya)"
__copyright__ = "Copyright (C) 2025 mayuneco(mayunya)"
__license__ = "GPLv2"


class StreamNotifyGUI:
    """Stream notify GUI（統合版, プラグイン対応）"""

    def __init__(self, root, db, plugin_manager=None, bluesky_core=None):
        self.root = root
        self.root.title("StreamNotify on Bluesky - DB 管理")
        self.root.geometry("1400x750")

        self.db = db
        self.plugin_manager = plugin_manager
        self.bluesky_core = bluesky_core  # コア機能へのアクセス
        self.image_manager = get_image_manager()  # 画像管理クラスを初期化
        self.selected_rows = set()

        self.setup_ui()
        self.refresh_data()

    def setup_ui(self):
        """UI を構築"""

        # === 上部: ツールバー ===
        toolbar = ttk.Frame(self.root)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

        ttk.Button(toolbar, text="🔄 再読込", command=self.refresh_data).pack(side=tk.LEFT, padx=2)
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=2)
        ttk.Button(toolbar, text="☑️ すべて選択", command=self.select_all).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="☐ すべて解除", command=self.deselect_all).pack(side=tk.LEFT, padx=2)
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=2)
        ttk.Button(toolbar, text="💾 選択を保存", command=self.save_selection).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="🗑️ 削除", command=self.delete_selected).pack(side=tk.LEFT, padx=2)
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=2)
        ttk.Button(toolbar, text="🧪 投稿テスト", command=self.dry_run_post).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="📤 投稿設定", command=self.execute_post).pack(side=tk.LEFT, padx=2)
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=2)
        ttk.Button(toolbar, text="ℹ️ 統計", command=self.show_stats).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="🔧 プラグイン", command=self.show_plugins).pack(side=tk.LEFT, padx=2)

        table_frame = ttk.Frame(self.root)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        columns = ("Select", "Video ID", "Published", "Source", "Title", "Date", "Posted", "Image Mode", "Image File")
        self.tree = ttk.Treeview(table_frame, columns=columns, height=20, show="headings")

        self.tree.column("Select", width=50, anchor=tk.CENTER)
        self.tree.column("Video ID", width=110)
        self.tree.column("Published", width=130)
        self.tree.column("Source", width=120, anchor=tk.CENTER)
        self.tree.column("Title", width=400)
        self.tree.column("Date", width=150)
        self.tree.column("Posted", width=60, anchor=tk.CENTER)
        self.tree.column("Image Mode", width=80, anchor=tk.CENTER)
        self.tree.column("Image File", width=180)

        self.tree.heading("Select", text="☑️")
        self.tree.heading("Video ID", text="Video ID")
        self.tree.heading("Published", text="公開日時")
        self.tree.heading("Source", text="配信元")
        self.tree.heading("Title", text="タイトル")
        self.tree.heading("Date", text="投稿予定/投稿日時")
        self.tree.heading("Posted", text="投稿実績")
        self.tree.heading("Image Mode", text="画像モード")
        self.tree.heading("Image File", text="画像ファイル")

        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.bind("<Button-1>", self.on_tree_click)
        self.tree.bind("<Double-1>", self.on_tree_double_click)

        # 右クリックメニュー
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="⏰ 予約日時を設定", command=self.context_edit_scheduled)
        self.context_menu.add_command(label="🖼️ 画像を設定", command=self.context_edit_image)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="🗑️ 削除", command=self.context_delete)
        self.context_menu.add_command(label="❌ 選択解除", command=self.context_deselect)

        self.tree.bind("<Button-3>", self.show_context_menu)

        status_frame = ttk.Frame(self.root)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=5)

        self.status_label = ttk.Label(status_frame, text="準備完了", relief=tk.SUNKEN)
        self.status_label.pack(fill=tk.X)

    def refresh_data(self):
        """DB から最新データを取得して表示"""
        for item in self.tree.get_children():
            self.tree.delete(item)

        videos = self.db.get_all_videos()
        self.selected_rows.clear()

        for video in videos:
            checked = "☑️" if video.get("selected_for_post") else "☐"
            # 投稿済みの場合は投稿日時を表示、未投稿の場合は予約日時を表示
            if video.get("posted_to_bluesky"):
                # 新しい方式: posted_at がある場合はそれを表示
                if video.get("posted_at"):
                    date_info = video.get("posted_at")
                else:
                    # 古いデータベース: posted_at がない場合は "不明" と表示
                    date_info = "不明"
            else:
                # 未投稿の場合は予約日時を表示
                date_info = video.get("scheduled_at") or "（未設定）"
            source = video.get("source") or ""
            image_mode = video.get("image_mode") or ""
            image_filename = video.get("image_filename") or ""

            self.tree.insert("", tk.END, values=(
                checked,                         # Select
                video["video_id"],              # Video ID
                video["published_at"][:10],     # Published
                source,                          # Source
                video["title"][:100],           # Title
                date_info[:16] if date_info != "（未設定）" else date_info, # Date (Posted or Scheduled)
                "✓" if video.get("posted_to_bluesky") else "–",  # Posted
                image_mode,                      # Image Mode
                image_filename                   # Image File
            ), iid=video["video_id"], tags=("even" if len(self.tree.get_children()) % 2 == 0 else "odd",))

            if video.get("selected_for_post"):
                self.selected_rows.add(video["video_id"])

        self.tree.tag_configure("even", background="#f0f0f0")
        self.tree.tag_configure("odd", background="white")

        self.status_label.config(text=f"読み込み完了: {len(videos)} 件の動画（選択: {len(self.selected_rows)} 件）")

    def on_tree_click(self, event):
        """Treeview の「選択」列をクリックしてチェック状態をトグル"""
        item_id = self.tree.identify_row(event.y)
        col = self.tree.identify_column(event.x)

        if not item_id or col != "#1":
            return

        if item_id in self.selected_rows:
            self.selected_rows.remove(item_id)
            new_checked = "☐"
        else:
            self.selected_rows.add(item_id)
            new_checked = "☑️"

        values = list(self.tree.item(item_id, "values"))
        values[0] = new_checked
        self.tree.item(item_id, values=values)

    def on_tree_double_click(self, event):
        """Treeview の列をダブルクリックして編集"""
        item_id = self.tree.identify_row(event.y)
        col = self.tree.identify_column(event.x)

        if not item_id:
            return

        # 予約日時列
        if col == "#6":
            self.edit_scheduled_time(item_id)
        # 画像モード列または画像ファイル列
        elif col in ("#8", "#9"):
            self.edit_image_file(item_id)

    def select_all(self):
        """すべてを選択"""
        self.selected_rows.clear()
        for item in self.tree.get_children():
            self.selected_rows.add(item)
            values = list(self.tree.item(item, "values"))
            values[0] = "☑️"
            self.tree.item(item, values=values)

    def deselect_all(self):
        """すべてを解除"""
        self.selected_rows.clear()
        for item in self.tree.get_children():
            values = list(self.tree.item(item, "values"))
            values[0] = "☐"
            self.tree.item(item, values=values)

    def save_selection(self):
        """選択状態を DB に保存"""
        try:
            for video_id in self.selected_rows:
                self.db.update_selection(video_id, selected=True)
                logger.info(f"動画の選択状態を更新: {video_id} (selected=True)")
            for item in self.tree.get_children():
                if item not in self.selected_rows:
                    self.db.update_selection(item, selected=False)
                    logger.info(f"動画の選択状態を更新: {item} (selected=False)")
            messagebox.showinfo("成功", "選択状態を保存しました。")
            self.refresh_data()
        except Exception as e:
            messagebox.showerror("エラー", f"保存中にエラーが発生しました:\n{e}")

    def edit_scheduled_time(self, item_id):
        """予約日時をダイアログで編集"""
        videos = self.db.get_all_videos()
        video = next((v for v in videos if v["video_id"] == item_id), None)
        if not video:
            messagebox.showerror("エラー", "動画情報が見つかりません。")
            return

        edit_window = tk.Toplevel(self.root)
        edit_window.title(f"投稿日時設定 - {item_id}")
        edit_window.geometry("480x400")
        edit_window.resizable(False, False)

        ttk.Label(edit_window, text=f"動画: {item_id}", font=("Arial", 10, "bold")).pack(pady=4)
        ttk.Label(edit_window, text="予約投稿日時を設定します", foreground="gray").pack(pady=1)

        # 前回投稿日時情報を表示
        if video.get("posted_to_bluesky"):
            if video.get("posted_at"):
                prev_post_info = f"前回投稿日時: {video.get('posted_at')}"
            else:
                prev_post_info = "前回投稿日時: 不明"
        else:
            prev_post_info = "前回投稿日時: 投稿されていません"

        ttk.Label(edit_window, text=prev_post_info, foreground="blue", font=("Arial", 9)).pack(pady=2)

        # メインフレーム（スクロール対応）
        main_frame = ttk.Frame(edit_window)
        main_frame.pack(fill=tk.BOTH, padx=8, pady=4)

        # === 日付選択 ===
        date_frame = ttk.LabelFrame(main_frame, text="📅 日付を選択", padding=8)
        date_frame.pack(fill=tk.X, pady=3)

        # 現在の予約日時またはデフォルト値を取得
        if video.get("scheduled_at"):
            try:
                selected_date = datetime.fromisoformat(video.get("scheduled_at")).date()
            except:
                selected_date = datetime.now().date()
        else:
            selected_date = datetime.now().date()

        year_var = tk.StringVar(value=str(selected_date.year))
        month_var = tk.StringVar(value=str(selected_date.month))
        day_var = tk.StringVar(value=str(selected_date.day))

        # 日付Spinbox
        date_control_frame = ttk.Frame(date_frame)
        date_control_frame.pack(pady=4, fill=tk.X)

        year_spin = ttk.Spinbox(date_control_frame, from_=2024, to=2030, width=4, textvariable=year_var, font=("Arial", 11))
        year_spin.pack(side=tk.LEFT, padx=3, fill=tk.X, expand=True)
        ttk.Label(date_control_frame, text="年", width=2).pack(side=tk.LEFT, padx=2)

        month_spin = ttk.Spinbox(date_control_frame, from_=1, to=12, width=4, textvariable=month_var, font=("Arial", 11))
        month_spin.pack(side=tk.LEFT, padx=3, fill=tk.X, expand=True)
        ttk.Label(date_control_frame, text="月", width=2).pack(side=tk.LEFT, padx=2)

        day_spin = ttk.Spinbox(date_control_frame, from_=1, to=31, width=4, textvariable=day_var, font=("Arial", 11))
        day_spin.pack(side=tk.LEFT, padx=3, fill=tk.X, expand=True)
        ttk.Label(date_control_frame, text="日", width=2).pack(side=tk.LEFT, padx=2)

        def update_calendar(*args):
            """日の妥当性をチェック"""
            try:
                year = int(year_var.get())
                month = int(month_var.get())
                day = int(day_var.get())

                # 日の妥当性チェック
                if day > calendar.monthrange(year, month)[1]:
                    day = calendar.monthrange(year, month)[1]
                    day_var.set(str(day))
            except:
                return

        year_spin.bind('<KeyRelease>', update_calendar)
        month_spin.bind('<KeyRelease>', update_calendar)
        day_spin.bind('<KeyRelease>', update_calendar)

        # === 時間選択 ===
        time_frame = ttk.LabelFrame(main_frame, text="🕐 時間を選択", padding=8)
        time_frame.pack(fill=tk.X, pady=3)

        # 現在の時間またはデフォルト値を取得
        if video.get("scheduled_at"):
            try:
                selected_time = datetime.fromisoformat(video.get("scheduled_at")).time()
            except:
                selected_time = (datetime.now() + timedelta(minutes=5)).time()
        else:
            selected_time = (datetime.now() + timedelta(minutes=5)).time()

        hour_var = tk.StringVar(value=f"{selected_time.hour:02d}")
        minute_var = tk.StringVar(value=f"{selected_time.minute:02d}")

        time_control_frame = ttk.Frame(time_frame)
        time_control_frame.pack(pady=4, fill=tk.X)

        hour_spin = ttk.Spinbox(time_control_frame, from_=0, to=23, width=4, textvariable=hour_var, format="%02.0f", font=("Arial", 11))
        hour_spin.pack(side=tk.LEFT, padx=3, fill=tk.X, expand=True)
        ttk.Label(time_control_frame, text="時", width=2).pack(side=tk.LEFT, padx=2)

        minute_spin = ttk.Spinbox(time_control_frame, from_=0, to=59, width=4, textvariable=minute_var, format="%02.0f", font=("Arial", 11))
        minute_spin.pack(side=tk.LEFT, padx=3, fill=tk.X, expand=True)
        ttk.Label(time_control_frame, text="分", width=2).pack(side=tk.LEFT, padx=2)

        # クイック設定
        quick_frame = ttk.LabelFrame(main_frame, text="⚡ クイック設定", padding=8)
        quick_frame.pack(fill=tk.X, pady=3)

        def set_quick_time(minutes_offset):
            """クイック設定で時刻を更新"""
            quick_dt = datetime.now() + timedelta(minutes=minutes_offset)
            year_var.set(str(quick_dt.year))
            month_var.set(str(quick_dt.month))
            day_var.set(str(quick_dt.day))
            hour_var.set(f"{quick_dt.hour:02d}")
            minute_var.set(f"{quick_dt.minute:02d}")

        quick_btn_frame1 = ttk.Frame(quick_frame)
        quick_btn_frame1.pack(fill=tk.X, pady=2)
        ttk.Button(quick_btn_frame1, text="5分後", width=18, command=lambda: set_quick_time(5)).pack(side=tk.LEFT, padx=1, expand=True)
        ttk.Button(quick_btn_frame1, text="15分後", width=18, command=lambda: set_quick_time(15)).pack(side=tk.LEFT, padx=1, expand=True)

        quick_btn_frame2 = ttk.Frame(quick_frame)
        quick_btn_frame2.pack(fill=tk.X, pady=2)
        ttk.Button(quick_btn_frame2, text="30分後", width=18, command=lambda: set_quick_time(30)).pack(side=tk.LEFT, padx=1, expand=True)
        ttk.Button(quick_btn_frame2, text="1時間後", width=18, command=lambda: set_quick_time(60)).pack(side=tk.LEFT, padx=1, expand=True)

        # ボタン
        button_frame = ttk.Frame(edit_window)
        button_frame.pack(fill=tk.X, pady=6, padx=8)

        def save_time():
            """保存"""
            try:
                year = int(year_var.get())
                month = int(month_var.get())
                day = int(day_var.get())
                hour = int(hour_var.get())
                minute = int(minute_var.get())

                scheduled = datetime(year, month, day, hour, minute).strftime("%Y-%m-%d %H:%M")
                self.db.update_selection(item_id, selected=True, scheduled_at=scheduled)
                logger.info(f"動画の選択状態を更新: {item_id} (selected=True, scheduled={scheduled})")
                self.selected_rows.add(item_id)
                messagebox.showinfo("成功", f"予約日時を設定しました。\n{scheduled}\n\n「選択を保存」ボタンで確定してください。")
                edit_window.destroy()
                # 画像設定ダイアログを開くか確認
                if messagebox.askyesno("次のステップ", "画像を設定しますか？"):
                    self.edit_image_file(item_id)
            except Exception as e:
                messagebox.showerror("エラー", f"無効な日時です:\n{e}")

        def clear_selection():
            """選択解除"""
            self.db.update_selection(item_id, selected=False, scheduled_at=None, image_mode=None, image_filename=None)
            logger.info(f"動画の選択状態を更新: {item_id} (selected=False, scheduled=None)")
            self.selected_rows.discard(item_id)
            messagebox.showinfo("成功", "この動画の選択を解除しました。")
            edit_window.destroy()
            self.refresh_data()

        ttk.Button(button_frame, text="✅ 保存", command=save_time).pack(side=tk.LEFT, padx=4, expand=True, fill=tk.X)
        ttk.Button(button_frame, text="❌ 選択解除", command=clear_selection).pack(side=tk.LEFT, padx=4, expand=True, fill=tk.X)
        ttk.Button(button_frame, text="✕ キャンセル", command=edit_window.destroy).pack(side=tk.LEFT, padx=4, expand=True, fill=tk.X)

    def show_context_menu(self, event):
        """右クリックメニューを表示"""
        item_id = self.tree.identify_row(event.y)
        if item_id:
            self.tree.selection_set(item_id)
            self.current_context_item = item_id
            self.context_menu.post(event.x_root, event.y_root)

    def context_edit_scheduled(self):
        """コンテキストメニューから予約日時を編集"""
        if hasattr(self, 'current_context_item'):
            self.edit_scheduled_time(self.current_context_item)

    def context_edit_image(self):
        """コンテキストメニューから画像を設定"""
        if hasattr(self, 'current_context_item'):
            self.edit_image_file(self.current_context_item)

    def context_deselect(self):
        """コンテキストメニューから選択解除"""
        if hasattr(self, 'current_context_item'):
            item_id = self.current_context_item
            self.db.update_selection(item_id, selected=False, scheduled_at=None, image_mode=None, image_filename=None)
            logger.info(f"動画の選択状態を更新: {item_id} (selected=False, scheduled=None)")
            self.selected_rows.discard(item_id)
            messagebox.showinfo("成功", "この動画の選択を解除しました。")
            self.refresh_data()

    def edit_image_file(self, item_id):
        """画像ファイルをダイアログで編集（コンパクト版）"""
        videos = self.db.get_all_videos()
        video = next((v for v in videos if v["video_id"] == item_id), None)
        if not video:
            messagebox.showerror("エラー", "動画情報が見つかりません。")
            return

        site = video.get("source", "YouTube")  # デフォルトはYouTube
        site_dir = self._normalize_site_dir(site)

        image_window = tk.Toplevel(self.root)
        image_window.title(f"画像ファイル設定 - {item_id}")
        image_window.geometry("550x450")
        image_window.resizable(False, False)

        ttk.Label(image_window, text=f"動画ID: {item_id}", font=("Arial", 10, "bold")).pack(pady=5)
        ttk.Label(image_window, text=f"配信元: {site} | タイトル: {video['title'][:40]}...", foreground="gray").pack(pady=2)

        # 画像ファイル選択フレーム
        image_frame = ttk.LabelFrame(image_window, text=f"画像ファイル指定 ({site_dir}/import)", padding=10)
        image_frame.pack(pady=5, padx=10, fill=tk.BOTH, expand=True)

        image_path_var = tk.StringVar(value=video.get("image_filename") or "")

        # ファイル名入力
        file_select_frame = ttk.Frame(image_frame)
        file_select_frame.pack(fill=tk.X, pady=5)

        ttk.Label(file_select_frame, text="ファイル名:").pack(side=tk.LEFT, padx=5)
        image_entry = ttk.Entry(file_select_frame, textvariable=image_path_var, width=35)
        image_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        def browse_image():
            """ファイルブラウザで画像を選択"""
            initialdir = os.path.abspath(f"images/{site_dir}/import")
            if not os.path.exists(initialdir):
                os.makedirs(initialdir, exist_ok=True)
            filetypes = [("画像ファイル", "*.png;*.jpg;*.jpeg;*.gif;*.webp"), ("すべて", "*")]
            path = filedialog.askopenfilename(title="画像を選択", initialdir=initialdir, filetypes=filetypes)
            if path and os.path.commonpath([initialdir, os.path.abspath(path)]) == initialdir:
                image_path_var.set(os.path.basename(path))
            elif path:
                messagebox.showerror("エラー", f"{site}/importディレクトリ内の画像のみ指定できます")

        ttk.Button(file_select_frame, text="📂 参照", command=browse_image).pack(side=tk.LEFT, padx=2)

        # 登録済み画像表示
        current_image_var = tk.StringVar(value=video.get("image_filename") or "（未登録）")
        current_frame = ttk.LabelFrame(image_frame, text="登録されている画像", padding=5)
        current_frame.pack(fill=tk.X, pady=5)
        ttk.Label(current_frame, textvariable=current_image_var, foreground="blue").pack(anchor=tk.W)

        # URLからダウンロードフレーム
        url_frame = ttk.LabelFrame(image_frame, text="URLから画像をダウンロード", padding=5)
        url_frame.pack(fill=tk.X, pady=5)

        url_var = tk.StringVar(value=video.get("thumbnail_url") or "")

        url_input_frame = ttk.Frame(url_frame)
        url_input_frame.pack(fill=tk.X)

        ttk.Label(url_input_frame, text="URL:").pack(side=tk.LEFT, padx=2)
        url_entry = ttk.Entry(url_input_frame, textvariable=url_var, width=35)
        url_entry.pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)

        def download_from_url():
            """URLから画像をダウンロード"""
            url = url_var.get().strip()
            if not url:
                messagebox.showwarning("警告", "URLを入力してください。")
                return

            # YouTube動画の場合、ロガーを切り替え
            import image_manager as im_module
            import logging
            original_logger = im_module.logger
            if site_dir == "YouTube":
                im_module.logger = logging.getLogger("YouTubeLogger")

            try:
                # ダウンロード
                filename = self.image_manager.download_and_save_thumbnail(
                    thumbnail_url=url,
                    site=site_dir,
                    video_id=item_id,
                    mode="import"
                )
            finally:
                im_module.logger = original_logger

            if filename:
                image_path_var.set(filename)
                current_image_var.set(filename)
                image_window.destroy()  # ダイアログを先に閉じる
                messagebox.showinfo("成功", f"画像をダウンロードしました。\n{filename}")
            else:
                messagebox.showerror("エラー", "画像のダウンロードに失敗しました。")

        ttk.Button(url_input_frame, text="⬇️ ダウンロード", command=download_from_url).pack(side=tk.LEFT, padx=2)

        # 自動取得／バックフィルフレーム
        auto_frame = ttk.LabelFrame(image_frame, text="自動取得/バックフィル", padding=5)
        auto_frame.pack(fill=tk.X, pady=5)

        def run_youtube_thumbnail_fetch():
            """YouTube動画の場合、高品質サムネイルを取得してDB反映"""
            if site_dir != "YouTube":
                messagebox.showinfo("情報", "YouTube動画のみ対応の機能です。")
                return
            try:
                from image_manager import get_youtube_thumbnail_url
            except Exception as e:
                messagebox.showerror("エラー", f"モジュール読み込みに失敗しました: {e}")
                return

            thumb_url = get_youtube_thumbnail_url(item_id)
            if not thumb_url:
                messagebox.showwarning("警告", "YouTubeサムネイルURLを取得できませんでした。")
                return

            # ロガーを一時的に切り替え
            import image_manager as im_module
            import logging
            original_logger = im_module.logger
            im_module.logger = logging.getLogger("YouTubeLogger")

            try:
                filename = self.image_manager.download_and_save_thumbnail(
                    thumbnail_url=thumb_url,
                    site=site_dir,
                    video_id=item_id,
                    mode="import",
                )
            finally:
                im_module.logger = original_logger

            if filename:
                # DB更新時のロガーも切り替え
                import database as db_module
                db_original_logger = db_module.logger
                db_module.logger = logging.getLogger("YouTubeLogger")

                try:
                    self.db.update_thumbnail_url(item_id, thumb_url)
                    self.db.update_image_info(item_id, image_mode="import", image_filename=filename)
                finally:
                    db_module.logger = db_original_logger

                image_path_var.set(filename)
                current_image_var.set(filename)
                image_window.destroy()  # ダイアログを先に閉じる
                messagebox.showinfo("成功", f"YouTubeサムネイルを取得しました。\n{filename}")
            else:
                messagebox.showerror("エラー", "画像のダウンロードに失敗しました。")

        def run_niconico_ogp_fetch():
            """ニコニコ動画の場合、OGPから即時取得してDB反映"""
            if site_dir != "Niconico":
                messagebox.showinfo("情報", "ニコニコ動画のみ対応の機能です。")
                return
            try:
                from thumbnails.niconico_ogp_backfill import fetch_thumbnail_url
            except Exception as e:
                messagebox.showerror("エラー", f"モジュール読み込みに失敗しました: {e}")
                return

            thumb_url = fetch_thumbnail_url(item_id)
            if not thumb_url:
                messagebox.showwarning("警告", "OGPからサムネイルURLを取得できませんでした。")
                return

            filename = self.image_manager.download_and_save_thumbnail(
                thumbnail_url=thumb_url,
                site=site_dir,
                video_id=item_id,
                mode="import",
            )
            if filename:
                self.db.update_thumbnail_url(item_id, thumb_url)
                self.db.update_image_info(item_id, image_mode="import", image_filename=filename)
                image_path_var.set(filename)
                current_image_var.set(filename)
                image_window.destroy()  # ダイアログを先に閉じる
                messagebox.showinfo("成功", f"OGPから画像を取得しました。\n{filename}")
            else:
                messagebox.showerror("エラー", "画像のダウンロードに失敗しました。")

        def run_redownload_all():
            """画像未設定の動画を再ダウンロード（全体）"""
            if not messagebox.askyesno("確認", "画像未設定の動画をまとめて再ダウンロードしますか？"):
                return
            try:
                from thumbnails.image_re_fetch_module import redownload_missing_images
                redownload_missing_images(dry_run=False)
                messagebox.showinfo("完了", "再ダウンロードを実行しました。ログを確認してください。")
            except Exception as e:
                messagebox.showerror("エラー", f"再ダウンロードに失敗しました: {e}")

        # 動画ソースに応じて適切なボタンを表示
        if site_dir == "YouTube":
            ttk.Button(auto_frame, text="YouTubeサムネイル取得", command=run_youtube_thumbnail_fetch).pack(side=tk.LEFT, padx=3, expand=True, fill=tk.X)
        elif site_dir == "Niconico":
            ttk.Button(auto_frame, text="OGPから取得 (ニコニコ)", command=run_niconico_ogp_fetch).pack(side=tk.LEFT, padx=3, expand=True, fill=tk.X)

        ttk.Button(auto_frame, text="未設定画像を再ダウンロード", command=run_redownload_all).pack(side=tk.LEFT, padx=3, expand=True, fill=tk.X)

        # ボタン
        button_frame = ttk.Frame(image_window)
        button_frame.pack(pady=10, padx=10, fill=tk.X)

        def save_image():
            """画像設定を保存"""
            image_filename = image_path_var.get().strip() or None
            image_mode = "import" if image_filename else None

            # 画像ファイルの存在確認
            if image_filename:
                image_path = os.path.join("images", site_dir, "import", image_filename)
                if not os.path.exists(image_path):
                    if not messagebox.askyesno("確認", f"画像ファイル '{image_filename}' が見つかりません。\nそれでも設定しますか？"):
                        return

            self.db.update_image_info(item_id, image_mode=image_mode, image_filename=image_filename)
            messagebox.showinfo("成功", f"画像ファイルを設定しました。\n画像: {image_filename or '（指定なし）'}\n\n「選択を保存」ボタンで確定してください。")
            image_window.destroy()
            self.refresh_data()

        def clear_image():
            """画像設定をクリア"""
            image_path_var.set("")
            current_image_var.set("（未登録）")
            self.db.update_image_info(item_id, image_mode=None, image_filename=None)
            messagebox.showinfo("成功", "画像ファイルを削除しました。")
            image_window.destroy()
            self.refresh_data()

        def preview_image():
            """画像をプレビュー（別ウィンドウ）"""
            filename = image_path_var.get().strip()
            if not filename:
                messagebox.showinfo("情報", "画像が登録されていません。")
                return

            image_info = self.image_manager.get_image_info(site_dir, "import", filename)
            if not image_info:
                messagebox.showerror("エラー", f"画像ファイル '{filename}' が見つかりません。")
                return

            # プレビューウィンドウを作成（画像表示 + 情報）
            preview_window = tk.Toplevel(image_window)
            preview_window.title(f"画像プレビュー - {filename}")
            preview_window.geometry("520x520")
            preview_window.resizable(False, False)

            # 画像表示
            image_path = image_info['path']
            has_pillow = True
            try:
                from PIL import Image, ImageTk, ImageOps  # type: ignore
            except ImportError:
                has_pillow = False

            img_label = ttk.Label(preview_window)
            img_label.pack(pady=10)

            if has_pillow:
                try:
                    with Image.open(image_path) as img_obj:
                        img_obj = ImageOps.exif_transpose(img_obj)
                        img_obj.thumbnail((480, 320), Image.Resampling.LANCZOS)
                        photo = ImageTk.PhotoImage(img_obj)
                        img_label.configure(image=photo)
                        img_label.image = photo  # GC防止
                except Exception as e:
                    ttk.Label(preview_window, text=f"画像の読み込みに失敗しました: {e}", foreground="red").pack(pady=5)
            else:
                ttk.Label(preview_window, text="Pillow が未インストールのため画像表示できません。\n`pip install Pillow` を実行してください。", foreground="red", wraplength=480).pack(pady=5)

            ttk.Label(preview_window, text="画像情報", font=("Arial", 12, "bold")).pack(pady=5)

            info_frame = ttk.Frame(preview_window, padding=10)
            info_frame.pack(fill=tk.BOTH, expand=True)

            # 情報を表示
            ttk.Label(info_frame, text=f"ファイル名:", font=("Arial", 9, "bold")).grid(row=0, column=0, sticky=tk.W, pady=3)
            ttk.Label(info_frame, text=image_info['filename']).grid(row=0, column=1, sticky=tk.W, pady=3, padx=10)

            ttk.Label(info_frame, text=f"形式:", font=("Arial", 9, "bold")).grid(row=1, column=0, sticky=tk.W, pady=3)
            ttk.Label(info_frame, text=image_info['format']).grid(row=1, column=1, sticky=tk.W, pady=3, padx=10)

            ttk.Label(info_frame, text=f"ファイルサイズ:", font=("Arial", 9, "bold")).grid(row=2, column=0, sticky=tk.W, pady=3)
            ttk.Label(info_frame, text=f"{image_info['file_size_mb']} MB").grid(row=2, column=1, sticky=tk.W, pady=3, padx=10)

            if image_info.get('width') and image_info.get('height'):
                ttk.Label(info_frame, text=f"解像度:", font=("Arial", 9, "bold")).grid(row=3, column=0, sticky=tk.W, pady=3)
                ttk.Label(info_frame, text=f"{image_info['width']} x {image_info['height']}").grid(row=3, column=1, sticky=tk.W, pady=3, padx=10)

                ttk.Label(info_frame, text=f"モード:", font=("Arial", 9, "bold")).grid(row=4, column=0, sticky=tk.W, pady=3)
                ttk.Label(info_frame, text=image_info.get('mode', 'N/A')).grid(row=4, column=1, sticky=tk.W, pady=3, padx=10)
            else:
                ttk.Label(info_frame, text="※ Pillow未インストールのため解像度情報は取得できません",
                         foreground="gray", wraplength=350).grid(row=3, column=0, columnspan=2, pady=10)

            ttk.Label(info_frame, text=f"パス:", font=("Arial", 9, "bold")).grid(row=5, column=0, sticky=tk.W, pady=3)
            path_label = ttk.Label(info_frame, text=image_info['path'], foreground="blue", cursor="hand2", wraplength=320)
            path_label.grid(row=5, column=1, sticky=tk.W, pady=3, padx=10)

            def open_folder():
                """フォルダを開く"""
                import subprocess
                folder_path = os.path.dirname(image_info['path'])
                subprocess.Popen(f'explorer "{folder_path}"')

            path_label.bind("<Button-1>", lambda e: open_folder())

            ttk.Button(preview_window, text="閉じる", command=preview_window.destroy).pack(pady=10)

        ttk.Button(button_frame, text="✅ 保存", command=save_image).pack(side=tk.LEFT, padx=3, expand=True, fill=tk.X)
        ttk.Button(button_frame, text="🔍 プレビュー", command=preview_image).pack(side=tk.LEFT, padx=3, expand=True, fill=tk.X)
        ttk.Button(button_frame, text="❌ クリア", command=clear_image).pack(side=tk.LEFT, padx=3, expand=True, fill=tk.X)
        ttk.Button(button_frame, text="✕ キャンセル", command=image_window.destroy).pack(side=tk.LEFT, padx=3, expand=True, fill=tk.X)

    def _normalize_site_dir(self, site: str) -> str:
        """サイト名をディレクトリ表記に正規化"""
        if not site:
            return "YouTube"
        s = site.lower()
        if s == "youtube":
            return "YouTube"
        if s == "niconico" or s == "nico" or s.startswith("nico"):
            return "Niconico"
        if s == "twitch":
            return "Twitch"
        return site

    def dry_run_post(self):
        """ドライラン：投稿設定ウィンドウを表示（ドライランモード）"""
        if not self.selected_rows:
            messagebox.showwarning("警告", "投稿対象の動画がありません。\n\n☑️ をクリックして選択してください。")
            return

        videos = self.db.get_all_videos()
        selected = [v for v in videos if v["video_id"] in self.selected_rows]

        if not selected:
            messagebox.showwarning("警告", "投稿対象の動画がありません。\n\n選択して保存してから実行してください。")
            return

        msg = f"""
🧪 ドライラン モード

以下の {len(selected)} 件をテスト実行します：

"""
        for v in selected[:5]:
            msg += f"  ✓ {v['title'][:50]}...\n"

        if len(selected) > 5:
            msg += f"  ... ほか {len(selected) - 5} 件\n"

        msg += """
投稿設定ウィンドウで「ドライラン」をクリックすると、
ログ出力のみで実際には投稿されません。
        """

        if messagebox.askyesno("確認", msg):
            for video in selected:
                post_window = PostSettingsWindow(
                    self.root, video, self.db, self.plugin_manager, self.bluesky_core
                )
                self.root.wait_window(post_window.window)

    def execute_post(self):
        """投稿設定：投稿設定ウィンドウを表示"""
        if not self.plugin_manager:
            messagebox.showerror("エラー", "プラグインマネージャが初期化されていません。再起動してください。")
            return

        if not self.selected_rows:
            messagebox.showwarning("警告", "投稿対象の動画がありません。\n\n☑️ をクリックして選択してください。")
            return

        videos = self.db.get_all_videos()
        selected = [v for v in videos if v["video_id"] in self.selected_rows]

        if not selected:
            messagebox.showwarning("警告", "投稿対象の動画がありません。\n\n選択して保存してから実行してください。")
            return

        # 各動画について投稿設定ウィンドウを表示
        for video in selected:
            post_window = PostSettingsWindow(
                self.root, video, self.db, self.plugin_manager, self.bluesky_core
            )
            self.root.wait_window(post_window.window)

    def show_stats(self):
        """統計情報を表示"""
        videos = self.db.get_all_videos()

        total = len(videos)
        posted = sum(1 for v in videos if v["posted_to_bluesky"])
        selected = sum(1 for v in videos if v["selected_for_post"])
        unposted = total - posted

        stats = f"""
📊 統計情報
━━━━━━━━━━━━━━━━━
総動画数:     {total}
投稿済み:     {posted}
投稿予定:     {selected}
未処理:       {unposted}

📌 操作方法
━━━━━━━━━━━━━━━━━
1. 「☑️」をクリック → 投稿対象を選択
2. 「投稿予定/投稿日時」をダブルクリック → 投稿日時を設定
3. 「💾 選択を保存」 → DB に反映
4. 「🧪 投稿テスト」 → テスト実行
5. 「📤 投稿設定」 → 投稿設定

⚠️ 注意
━━━━━━━━━━━━━━━━━
投稿済みフラグに関わらず投稿できます。
重複投稿にご注意ください。
        """
        messagebox.showinfo("統計情報", stats)

    def show_plugins(self):
        """導入プラグイン情報を表示"""
        if not self.plugin_manager:
            messagebox.showinfo("プラグイン情報", "プラグインマネージャーが初期化されていません。")
            return

        loaded = self.plugin_manager.get_loaded_plugins()
        enabled = self.plugin_manager.get_enabled_plugins()

        if not loaded:
            messagebox.showinfo("プラグイン情報", "導入されているプラグインがありません。")
            return

        # プラグイン情報を整形（固定幅で見やすく）
        info_lines = ["🔧 導入プラグイン一覧"]
        info_lines.append("-" * 65)
        info_lines.append("")

        for plugin_name, plugin in loaded.items():
            is_enabled = plugin_name in enabled
            status = "✅有効" if is_enabled else "⚪無効"
            name = plugin.get_name()
            version = plugin.get_version()
            description = plugin.get_description()

            # 説明文が長い場合は折り返す
            desc_lines = []
            desc = description
            max_width = 58
            while len(desc) > max_width:
                # 最後のスペースで分割
                idx = desc.rfind(" ", 0, max_width)
                if idx == -1:
                    idx = max_width
                desc_lines.append(desc[:idx])
                desc = desc[idx:].lstrip()
            if desc:
                desc_lines.append(desc)

            info_lines.append(f"【{name}】 {status}")
            info_lines.append(f"  バージョン: v{version}")
            for i, desc_line in enumerate(desc_lines):
                if i == 0:
                    info_lines.append(f"  説明: {desc_line}")
                else:
                    info_lines.append(f"         {desc_line}")
            info_lines.append("")

        info_text = "\n".join(info_lines)

        # Toplevel ウィンドウで表示（スクロール機能付き）
        info_window = tk.Toplevel(self.root)
        info_window.title("プラグイン情報")
        info_window.geometry("700x500")

        # テキストウィジェット
        text_frame = ttk.Frame(info_window)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        text_widget = tk.Text(text_frame, wrap=tk.WORD, font=("Courier New", 9), height=25, width=80)
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=text_widget.yview)
        text_widget.configure(yscroll=scrollbar.set)

        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        text_widget.insert(tk.END, info_text)
        text_widget.config(state=tk.DISABLED)

        # 閉じるボタン
        button_frame = ttk.Frame(info_window)
        button_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Button(button_frame, text="閉じる", command=info_window.destroy).pack(side=tk.RIGHT)

    def validate_datetime(self, date_string):
        """日時形式をバリデーション"""
        try:
            datetime.fromisoformat(date_string)
            return True
        except ValueError:
            return False

    def delete_selected(self):
        """ツールバーから選択した動画をDBから削除"""
        if not self.selected_rows:
            messagebox.showwarning("警告", "削除対象の動画がありません。\n\n☑️ をクリックして選択してください。")
            return

        videos = self.db.get_all_videos()
        selected = [v for v in videos if v["video_id"] in self.selected_rows]

        if not selected:
            messagebox.showwarning("警告", "削除対象の動画がありません。")
            return

        # 確認ダイアログ
        msg = f"""
🗑️ 削除確認

以下の {len(selected)} 件の動画をDBから完全削除します：

"""
        for v in selected[:5]:
            msg += f"  × {v['title'][:50]}...\n"

        if len(selected) > 5:
            msg += f"  ... ほか {len(selected) - 5} 件\n"

        msg += """
この操作は取り消せません。
本当に削除してもよろしいですか？
        """

        if not messagebox.askyesno("確認", msg, icon=messagebox.WARNING):
            logger.info(f"❌ 削除操作をキャンセルしました（{len(selected)}件選択中）")
            return

        # 削除実行
        logger.info(f"🗑️ {len(selected)} 件の動画削除を開始します")
        deleted_count = self.db.delete_videos_batch([v["video_id"] for v in selected])

        if deleted_count > 0:
            logger.info(f"✅ {deleted_count} 件の動画を削除しました（GUI操作）")
            self.selected_rows.clear()
            self.refresh_data()
            messagebox.showinfo("成功", f"{deleted_count} 件の動画を削除しました。")
        else:
            logger.error(f"❌ 動画の削除に失敗しました（{len(selected)}件リクエスト）")
            messagebox.showerror("エラー", "動画の削除に失敗しました。")

    def context_delete(self):
        """右クリックメニューから動画を削除"""
        if not hasattr(self, 'current_context_item'):
            messagebox.showerror("エラー", "削除対象が見つかりません。")
            return

        item_id = self.current_context_item
        videos = self.db.get_all_videos()
        video = next((v for v in videos if v["video_id"] == item_id), None)

        if not video:
            messagebox.showerror("エラー", "動画情報が見つかりません。")
            return

        # 確認ダイアログ
        msg = f"""
🗑️ 削除確認

以下の動画をDBから完全削除します：

タイトル: {video['title'][:60]}...
動画ID: {item_id}

この操作は取り消せません。
削除してもよろしいですか？
        """

        if not messagebox.askyesno("確認", msg, icon=messagebox.WARNING):
            logger.info(f"❌ 削除操作をキャンセルしました: {item_id}")
            return

        # 削除実行
        logger.info(f"🗑️ 動画削除を実行: {item_id} ({video['title'][:40]}...)")
        if self.db.delete_video(item_id):
            logger.info(f"✅ 動画を削除しました: {item_id}（右クリックメニュー操作）")
            self.selected_rows.discard(item_id)
            self.refresh_data()
            messagebox.showinfo("成功", f"動画を削除しました。\n{item_id}")
        else:
            logger.error(f"❌ 動画削除に失敗: {item_id}")
            messagebox.showerror("エラー", "動画の削除に失敗しました。")


class PostSettingsWindow:
    """投稿設定ウィンドウ - 動画の投稿設定を詳細に管理"""

    def __init__(self, parent, video, db, plugin_manager=None, bluesky_core=None):
        """
        投稿設定ウィンドウを初期化

        Args:
            parent: 親ウィンドウ
            video: 選択されたビデオレコード
            db: Database インスタンス
            plugin_manager: PluginManager インスタンス
            bluesky_core: Bluesky コア機能インスタンス
        """
        self.parent = parent
        self.video = video
        self.db = db
        self.plugin_manager = plugin_manager
        self.bluesky_core = bluesky_core
        self.result = None  # 確定時の設定結果

        # ウィンドウを作成
        self.window = tk.Toplevel(parent)
        self.window.title(f"📤 投稿設定 - {video['title'][:50]}...")
        self.window.geometry("700x620")
        self.window.resizable(False, False)

        self._build_ui()
        self.window.transient(parent)
        self.window.grab_set()

    def _build_ui(self):
        """UI を構築"""
        # === メインフレーム ===
        main_frame = ttk.Frame(self.window)
        main_frame.pack(fill=tk.X, expand=False, padx=10, pady=10, side=tk.TOP)

        # === 1. 動画情報 ===
        info_frame = ttk.LabelFrame(main_frame, text="📹 動画情報", padding=10)
        info_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(info_frame, text="タイトル:", font=("", 10, "bold")).grid(row=0, column=0, sticky=tk.W)
        title_label = ttk.Label(
            info_frame, text=self.video["title"], foreground="darkblue", wraplength=550
        )
        title_label.grid(row=0, column=1, sticky=tk.W, columnspan=2)

        ttk.Label(info_frame, text="ソース:", font=("", 10, "bold")).grid(row=1, column=0, sticky=tk.W)
        source_text = self.video.get("source", "youtube").upper()
        ttk.Label(info_frame, text=source_text, foreground="darkgreen").grid(row=1, column=1, sticky=tk.W)

        ttk.Label(info_frame, text="公開日時:", font=("", 10, "bold")).grid(row=2, column=0, sticky=tk.W)
        ttk.Label(info_frame, text=self.video.get("published_at", "不明")).grid(row=2, column=1, sticky=tk.W)

        # === 2. 投稿実績と投稿予約を1列に統合 ===
        status_frame = ttk.LabelFrame(main_frame, text="📊 投稿状況", padding=10)
        status_frame.pack(fill=tk.X, pady=(0, 10))

        # 投稿実績
        posted_status = "✅ 投稿済み" if self.video.get("posted_to_bluesky") else "❌ 未投稿"
        posted_date = self.video.get("posted_at", "—")
        posted_info = f"投稿実績: {posted_status} ({posted_date})"
        ttk.Label(status_frame, text=posted_info, font=("", 10)).pack(anchor=tk.W, pady=(0, 5))

        # 投稿予約
        scheduled_at = self.video.get("scheduled_at")
        if scheduled_at:
            schedule_text = f"投稿予約: 予約あり ({scheduled_at})"
            schedule_color = "darkgreen"
        else:
            schedule_text = f"投稿予約: 予約なし"
            schedule_color = "gray"

        ttk.Label(status_frame, text=schedule_text, foreground=schedule_color, font=("", 10)).pack(anchor=tk.W)

        # === 3. DB 画像の設定 + プレビュー（左右配置） ===
        image_frame = ttk.LabelFrame(main_frame, text="🖼️ DB画像の設定", padding=10)
        image_frame.pack(fill=tk.X, pady=(0, 5))

        # 画像情報フレーム（左側）
        image_info_frame = ttk.Frame(image_frame)
        image_info_frame.pack(fill=tk.X, expand=True)

        image_filename = self.video.get("image_filename")
        if image_filename:
            image_text = f"✅ ファイル: {image_filename}"
            image_color = "darkblue"
        else:
            image_text = "❌ なし"
            image_color = "gray"

        ttk.Label(image_info_frame, text=image_text, foreground=image_color, font=("", 10, "bold")).pack(anchor=tk.W)

        # 画像情報詳細（左側）
        if image_filename:
            self._display_image_preview(image_info_frame, image_filename)

        # === 4. 投稿方法の選択 ===
        post_method_frame = ttk.LabelFrame(main_frame, text="📋 投稿方法", padding=10)
        post_method_frame.pack(fill=tk.X, pady=(0, 10))

        self.use_image_var = tk.BooleanVar(value=True if image_filename else False)

        # 画像がない場合は強制的に URLリンクカード
        if not image_filename:
            self.use_image_var.set(False)
            ttk.Radiobutton(
                post_method_frame,
                text="🔗 URLリンクカード（画像なし）",
                variable=self.use_image_var,
                value=False,
                state=tk.DISABLED,
            ).pack(anchor=tk.W, pady=5)
            ttk.Label(post_method_frame, text="⚠️ DB画像がないため、URLリンクカードのみ利用可能", foreground="orange").pack(
                anchor=tk.W, padx=20
            )
        else:
            ttk.Radiobutton(
                post_method_frame,
                text="🖼️ 画像を添付",
                variable=self.use_image_var,
                value=True,
            ).pack(anchor=tk.W, pady=5)
            ttk.Radiobutton(
                post_method_frame,
                text="🔗 URLリンクカード",
                variable=self.use_image_var,
                value=False,
            ).pack(anchor=tk.W, pady=5)

        # === 5. 小さい画像の加工設定 ===
        small_image_frame = ttk.LabelFrame(main_frame, text="🎨 小さい画像の加工", padding=10)
        small_image_frame.pack(fill=tk.X, pady=(0, 10))

        self.resize_small_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            small_image_frame,
            text="小さい画像も自動加工する（リサイズ・圧縮）",
            variable=self.resize_small_var,
        ).pack(anchor=tk.W, pady=5)
        ttk.Label(
            small_image_frame,
            text="✓: すべての画像を加工 / ✗: 大きい画像のみ加工",
            foreground="gray",
            font=("", 9),
        ).pack(anchor=tk.W, padx=5)

        # === ボタンフレーム（常に下部に固定） ===
        button_frame = ttk.Frame(self.window)
        button_frame.pack(fill=tk.X, padx=10, pady=10, side=tk.BOTTOM)

        ttk.Button(button_frame, text="✅ 確定して投稿", command=self._confirm_and_post).pack(
            side=tk.RIGHT, padx=5
        )
        ttk.Button(button_frame, text="❌ キャンセル", command=self.window.destroy).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="🧪 ドライラン", command=self._dry_run).pack(side=tk.RIGHT, padx=5)

    def _display_image_preview(self, parent_frame, image_filename):
        """画像プレビューを表示（右横配置）"""
        if not PIL_AVAILABLE:
            ttk.Label(parent_frame, text="⚠️ PIL (Pillow) がインストールされていないため、プレビューは表示できません", foreground="orange").pack(anchor=tk.W, pady=5)
            return

        try:
            # 画像ファイルの完全パスを構築
            site = self.video.get("source", "youtube").capitalize()
            image_path = Path("images") / site / "import" / image_filename

            if not image_path.exists():
                # autopost フォルダも試す
                image_path = Path("images") / site / "autopost" / image_filename

            if not image_path.exists():
                ttk.Label(parent_frame, text=f"⚠️ 画像ファイルが見つかりません: {image_filename}", foreground="orange").pack(anchor=tk.W, pady=5)
                return

            # 画像情報と画像を左右に配置するフレーム
            preview_container = ttk.Frame(parent_frame)
            preview_container.pack(fill=tk.X, pady=5)

            # 左側：画像情報
            info_frame = ttk.Frame(preview_container)
            info_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

            with Image.open(image_path) as img_info:
                width, height = img_info.size
                size_kb = image_path.stat().st_size / 1024
                info_text = f"解像度: {width}×{height} px\nサイズ: {size_kb:.1f} KB"
                ttk.Label(info_frame, text=info_text, foreground="gray", font=("", 9), justify=tk.LEFT).pack(anchor=tk.W)

            # 右側：プレビュー画像
            preview_frame = ttk.Frame(preview_container)
            preview_frame.pack(side=tk.RIGHT)

            # 画像を開く
            with Image.open(image_path) as img:
                # サムネイルサイズに縮小（最大 100x67）
                img.thumbnail((100, 67), Image.Resampling.LANCZOS)

                # PIL Image を tkinter PhotoImage に変換
                from PIL import ImageTk
                photo = ImageTk.PhotoImage(img)

                # ラベルに表示
                preview_label = tk.Label(preview_frame, image=photo, bg="lightgray", relief=tk.SUNKEN)
                preview_label.image = photo  # ガベージコレクション対策
                preview_label.pack()

        except Exception as e:
            logger.warning(f"画像プレビュー表示エラー: {e}")
            ttk.Label(parent_frame, text=f"⚠️ 画像の読み込みに失敗: {str(e)[:50]}", foreground="orange").pack(anchor=tk.W, pady=5)

    def _confirm_and_post(self):
        """設定を確定して投稿を実行"""
        use_image = self.use_image_var.get()
        resize_small = self.resize_small_var.get()

        self.result = {
            "use_image": use_image,
            "resize_small_images": resize_small,
            "video": self.video,
        }

        # 投稿実行
        self._execute_post(dry_run=False)

    def _dry_run(self):
        """ドライラン実行"""
        self.result = {
            "use_image": self.use_image_var.get(),
            "resize_small_images": self.resize_small_var.get(),
            "video": self.video,
        }
        self._execute_post(dry_run=True)

    def _execute_post(self, dry_run=False):
        """投稿を実行"""
        try:
            video = self.video
            use_image = self.result["use_image"]
            resize_small = self.result["resize_small_images"]

            mode_str = "画像" if use_image else "URLリンクカード"
            dry_str = "【ドライラン】" if dry_run else ""

            logger.info(f"{dry_str}投稿開始: {video['title'][:40]}... (投稿方法: {mode_str})")

            if self.plugin_manager:
                enabled_plugins = self.plugin_manager.get_enabled_plugins()
                if enabled_plugins and use_image:
                    # プラグイン経由で画像添付投稿
                    for plugin in enabled_plugins:
                        plugin.dry_run = dry_run
                        plugin.config.get("resize_small_images", True)
                        logger.info(f"📤 プラグイン経由で投稿: {plugin.__class__.__name__}")
                        results = self.plugin_manager.post_video_with_all_enabled(video)
                        logger.info(f"投稿結果: {results}")
                        if any(results.values()) and not dry_run:
                            self.db.mark_as_posted(video["video_id"])
                else:
                    # テキスト + URLリンク投稿
                    if self.bluesky_core:
                        logger.info(f"📤 コア機能で投稿（URLリンク）: {video['title']}")
                        success = self.bluesky_core.post_video_minimal(video)
                        if success and not dry_run:
                            self.db.mark_as_posted(video["video_id"])
            else:
                messagebox.showerror("エラー", "プラグインマネージャが初期化されていません")
                return

            msg = f"{'✅ ドライラン完了' if dry_run else '✅ 投稿完了'}\n\n{video['title'][:60]}...\n\n投稿方法: {mode_str}"
            messagebox.showinfo("成功", msg)

            if not dry_run:
                self.db.update_selection(video["video_id"], selected=False, scheduled_at=None)
                logger.info(f"選択状態を更新: {video['video_id']} (selected=False)")
                self.window.destroy()

        except Exception as e:
            logger.error(f"投稿エラー: {e}", exc_info=True)
            messagebox.showerror("エラー", f"投稿に失敗しました:\n{str(e)}")
