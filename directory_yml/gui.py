import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox, simpledialog
from tkinter import ttk
import threading
import queue
import pyperclip
import os
import datetime

from .config_manager import ConfigManager
from .file_processing import collect_directory_structures
from .yml_generator import generate_yaml

DEFAULT_IGNORE_PATTERNS = [".env", ".htpasswd", "*.log"]

class DirectoryYmlGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Dir2YAML")
        self.root.geometry("780x730")

        self.progress_queue = queue.Queue()
        self._yaml_result = ""

        self.config_manager = ConfigManager()
        self.active_profile_name = self.config_manager.get_active_profile_name()

        # ロードしたprofile_dataを保持(比較用)
        self.loaded_profile_data = {}

        # ディレクトリ一覧などUI用
        self.directory_list = []

        # ---------- ウィジェット構築 ----------
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # ========== Profile操作 ==========
        profile_frame = tk.LabelFrame(main_frame, text="プロファイル操作", padx=10, pady=10)
        profile_frame.pack(fill="x", pady=5)

        combo_frame = tk.Frame(profile_frame)
        combo_frame.pack(side=tk.LEFT, fill="x", expand=True)

        tk.Label(combo_frame, text="プロファイル: ").pack(side=tk.LEFT)
        self.profile_selector = ttk.Combobox(combo_frame, state="readonly", width=15)
        self.profile_selector["values"] = self.config_manager.get_profile_names()
        self.profile_selector.pack(side=tk.LEFT, padx=5)
        self.profile_selector.bind("<<ComboboxSelected>>", self.on_profile_select)

        dup_button = tk.Button(combo_frame, text="複製", command=self.duplicate_current_profile)
        dup_button.pack(side=tk.LEFT, padx=5)

        rename_button = tk.Button(combo_frame, text="リネーム", command=self.rename_current_profile)
        rename_button.pack(side=tk.LEFT, padx=5)

        delete_button = tk.Button(combo_frame, text="削除", command=self.delete_current_profile)
        delete_button.pack(side=tk.LEFT, padx=5)

        button_frame = tk.Frame(profile_frame)
        button_frame.pack(side=tk.RIGHT)

        new_profile_btn = tk.Button(button_frame, text="新規プロファイル", command=self.create_new_profile)
        new_profile_btn.pack(side=tk.LEFT, padx=5)

        save_profile_btn = tk.Button(button_frame, text="保存", command=self.save_current_profile)
        save_profile_btn.pack(side=tk.LEFT, padx=5)

        # ========== Directories ==========
        dir_frame = tk.LabelFrame(main_frame, text="ディレクトリ設定", padx=10, pady=10)
        dir_frame.pack(fill="x")

        self.add_dir_button = tk.Button(dir_frame, text="ディレクトリ追加", command=self.add_directory)
        self.add_dir_button.pack(side=tk.LEFT)

        self.dir_list_frame = tk.Frame(dir_frame)
        self.dir_list_frame.pack(fill="x", padx=10, pady=5)

        # ========== Ignore Patterns ==========
        ignore_frame = tk.LabelFrame(main_frame, text="除外パターン", padx=10, pady=10)
        ignore_frame.pack(fill="x", pady=5)

        default_label_text = "デフォルト: " + ", ".join(DEFAULT_IGNORE_PATTERNS)
        tk.Label(ignore_frame, text=default_label_text).pack(anchor="w")

        row_ignore_user = tk.Frame(ignore_frame)
        row_ignore_user.pack(anchor="w", fill="x", pady=5)

        tk.Label(row_ignore_user, text="ユーザパターン(カンマ区切り): ").pack(side=tk.LEFT)
        self.ignore_entry = tk.Entry(row_ignore_user, width=50)
        self.ignore_entry.pack(side=tk.LEFT, padx=5)

        # ========== その他設定 ==========
        misc_frame = tk.LabelFrame(main_frame, text="その他設定", padx=10, pady=10)
        misc_frame.pack(fill="x", pady=5)

        tk.Label(misc_frame, text="最大ファイルサイズ[byte]: ").pack(side=tk.LEFT)
        self.file_size_spin = tk.Spinbox(
            misc_frame, from_=0, to=10_000_000_000, increment=1000, width=12
        )
        self.file_size_spin.pack(side=tk.LEFT, padx=5)

        # ========== プロジェクト名 + YAML生成など ==========
        action_frame = tk.Frame(main_frame)
        action_frame.pack(fill="x", pady=10)
        action_frame.pack_configure(anchor="center")

        tk.Label(action_frame, text="プロジェクト名:").pack(side=tk.LEFT, padx=5)
        self.project_name_entry = tk.Entry(action_frame, width=30, fg="black")
        self.project_name_entry.pack(side=tk.LEFT)

        # プレースホルダー管理
        self.project_name_placeholder = ""
        self.project_name_is_placeholder = False
        self.project_name_entry.bind("<FocusIn>", self._on_project_name_focus_in)
        self.project_name_entry.bind("<FocusOut>", self._on_project_name_focus_out)

        self.generate_button = tk.Button(action_frame, text="YAML生成", command=self.start_generate_yaml, bg="#4CAF50")
        self.generate_button.pack(side=tk.LEFT, padx=10)

        self.clear_button = tk.Button(action_frame, text="クリア", command=self.clear_yaml_result)
        self.clear_button.pack(side=tk.LEFT, padx=(30, 5))

        arrow_label = tk.Label(action_frame, text=" ➡ ", font=("Arial", 12, "bold"))
        arrow_label.pack(side=tk.LEFT, padx=5)

        self.copy_button_active_bg = "#2196F3"
        self.save_button_active_bg = "#FF9800"
        self.button_disabled_bg = "#555555"

        self.copy_button = tk.Button(
            action_frame,
            text="コピー",
            command=self.copy_to_clipboard,
            bg=self.copy_button_active_bg,
            state="disabled"
        )
        self.copy_button.pack(side=tk.LEFT, padx=5)

        self.save_button = tk.Button(
            action_frame,
            text="保存",
            command=self.save_to_file,
            bg=self.save_button_active_bg,
            state="disabled"
        )
        self.save_button.pack(side=tk.LEFT, padx=5)

        # ========== Progress Log ==========
        progress_frame = tk.LabelFrame(main_frame, text="Progress Log", padx=10, pady=10)
        progress_frame.pack(fill="both", expand=True, pady=5)

        self.progress_text = scrolledtext.ScrolledText(progress_frame, width=80, height=10)
        self.progress_text.pack(fill="both", expand=True)

        # 非同期ログ監視 & コピー保存無効
        self.check_progress_queue()
        self.disable_copy_save_buttons()

        # ウィンドウ×押下イベント
        self.root.protocol("WM_DELETE_WINDOW", self._on_window_close)

        # アクティブプロファイルセット
        if self.active_profile_name in self.config_manager.get_profile_names():
            self.profile_selector.set(self.active_profile_name)
        else:
            allp = self.config_manager.get_profile_names()
            if allp:
                self.active_profile_name = allp[0]
                self.profile_selector.set(self.active_profile_name)

        self.load_profile_to_ui(self.active_profile_name)

    def run(self):
        self.root.mainloop()

    # -------------------------------------------------------------------------
    # プロファイル操作 (切り替え / 新規 / 複製 / 保存 / リネーム / 削除)
    # -------------------------------------------------------------------------
    def on_profile_select(self, event):
        new_profile = self.profile_selector.get()
        old_profile = self.active_profile_name
        if new_profile == old_profile:
            return
        # 未保存チェック
        if not self.confirm_unsaved_changes():
            self.profile_selector.set(old_profile)
            return

        self.active_profile_name = new_profile
        self.load_profile_to_ui(new_profile)

    def create_new_profile(self):
        if not self.confirm_unsaved_changes():
            return

        new_profile = self.config_manager.create_new_profile()
        self.active_profile_name = new_profile
        self.profile_selector["values"] = self.config_manager.get_profile_names()
        self.profile_selector.set(new_profile)
        self.load_profile_to_ui(new_profile)
        self._log_progress(f"新規プロファイル '{new_profile}' を作成しました。")

    def duplicate_current_profile(self):
        if not self.confirm_unsaved_changes():
            return
        source = self.active_profile_name
        if not source:
            return

        new_profile = self.config_manager.duplicate_profile(source)
        if new_profile is None:
            messagebox.showerror("エラー", f"プロファイル '{source}' は存在しません。")
            return

        self.active_profile_name = new_profile
        self.profile_selector["values"] = self.config_manager.get_profile_names()
        self.profile_selector.set(new_profile)
        self.load_profile_to_ui(new_profile)

        self._log_progress(f"'{source}' を複製し '{new_profile}' を作成しました。")

    def save_current_profile(self):
        if not self.active_profile_name:
            return
        self.save_profile(self.active_profile_name)
        self._log_progress(f"プロファイル '{self.active_profile_name}' を保存しました。")

    def save_profile(self, profile_name):
        data = {
            "project_name": self._get_project_name_entry_str(),
            "directories": self.directory_list,
            "ignore_patterns": self.get_user_ignore_patterns(),
            "max_file_size_bytes": int(self.file_size_spin.get())
        }
        self.config_manager.save_profile_data(profile_name, data)
        self.active_profile_name = profile_name
        self.loaded_profile_data = data

    def rename_current_profile(self):
        if not self.confirm_unsaved_changes():
            return
        old_name = self.active_profile_name
        if not old_name:
            return

        new_name = simpledialog.askstring("リネーム", f"新しい名前を入力\n(現在: {old_name})")
        if not new_name:
            return

        self.save_profile(old_name)
        result = self.config_manager.rename_profile(old_name, new_name)
        if result is None:
            messagebox.showerror("エラー", f"'{new_name}' は既に存在 or リネーム元が存在しません。")
            return

        self.active_profile_name = new_name
        self.profile_selector["values"] = self.config_manager.get_profile_names()
        self.profile_selector.set(new_name)

        self._log_progress(f"プロファイル '{old_name}' を '{new_name}' にリネームしました。")
        self.load_profile_to_ui(new_name)

    def delete_current_profile(self):
        if not self.confirm_unsaved_changes():
            return
        p_name = self.active_profile_name
        if not p_name:
            return

        confirm = messagebox.askokcancel("確認", f"プロファイル '{p_name}' を削除します。よろしいですか？")
        if not confirm:
            return

        self.config_manager.delete_profile(p_name)
        self.active_profile_name = self.config_manager.get_active_profile_name()
        self.profile_selector["values"] = self.config_manager.get_profile_names()
        self.profile_selector.set(self.active_profile_name)

        self._log_progress(f"プロファイル '{p_name}' を削除しました。")
        self.load_profile_to_ui(self.active_profile_name)

    # -------------------------------------------------------------------------
    # プロファイルロード / 未保存確認
    # -------------------------------------------------------------------------
    def load_profile_to_ui(self, profile_name):
        if not profile_name or profile_name not in self.config_manager.get_profile_names():
            return

        pd = self.config_manager.load_profile_data(profile_name)
        self.directory_list = pd.get("directories", [])
        ignore_list = pd.get("ignore_patterns", [])
        max_file_size = pd.get("max_file_size_bytes", 500000)
        project_name = pd.get("project_name", "")

        self.ignore_entry.delete(0, tk.END)
        if ignore_list:
            self.ignore_entry.insert(0, ",".join(ignore_list))

        self.file_size_spin.delete(0, tk.END)
        self.file_size_spin.insert(0, str(max_file_size))

        self.update_dir_list_display()

        # プロジェクト名(placeholder対応)
        self._set_project_name_entry_str(project_name)

        self.profile_selector.set(profile_name)
        self.loaded_profile_data = {
            "project_name": project_name,
            "directories": list(self.directory_list),
            "ignore_patterns": list(ignore_list),
            "max_file_size_bytes": max_file_size
        }
        self._log_progress(f"プロファイル '{profile_name}' を読み込みました。")

    def confirm_unsaved_changes(self):
        """
        現在のUIデータが loaded_profile_data と異なる場合、
        保存/破棄/キャンセルを尋ねる
        """
        if not self.active_profile_name:
            return True
        if not self.is_profile_data_changed():
            return True

        resp = messagebox.askyesnocancel(
            "未保存の変更",
            f"現在のプロファイル '{self.active_profile_name}' に未保存の変更があります。\n\n"
            "保存しますか？ (はい=保存, いいえ=破棄, キャンセル=操作中断)"
        )
        if resp is None:
            return False
        elif resp is True:
            self.save_profile(self.active_profile_name)
            return True
        else:
            return True  # いいえ=破棄

    def is_profile_data_changed(self):
        current_data = {
            "project_name": self._get_project_name_entry_str(),
            "directories": list(self.directory_list),
            "ignore_patterns": self.get_user_ignore_patterns(),
            "max_file_size_bytes": int(self.file_size_spin.get())
        }
        return current_data != self.loaded_profile_data

    def _on_window_close(self):
        if not self.confirm_unsaved_changes():
            return
        self.root.destroy()

    # -------------------------------------------------------------------------
    # ディレクトリ操作
    # -------------------------------------------------------------------------
    def add_directory(self):
        d = filedialog.askdirectory()
        if d:
            d = os.path.abspath(d)
            if self._is_already_registered_or_sub(d):
                messagebox.showerror("エラー", f"既に登録済み、またはサブ/上位ディレクトリです: {d}")
                return
            self.directory_list.append(d)
            self.update_dir_list_display()
            # placeholder更新
            self._refresh_project_name_placeholder()

    def remove_directory(self, idx):
        del self.directory_list[idx]
        self.update_dir_list_display()
        self._refresh_project_name_placeholder()

    def update_dir_list_display(self):
        for w in self.dir_list_frame.winfo_children():
            w.destroy()

        if not self.directory_list:
            tk.Label(self.dir_list_frame, text="(ディレクトリは追加されていません)").pack(anchor="w")
        else:
            for i, d in enumerate(self.directory_list):
                row_frame = tk.Frame(self.dir_list_frame)
                row_frame.pack(anchor="w", fill="x", pady=2)

                label = tk.Label(row_frame, text=d)
                label.pack(side=tk.LEFT, padx=5)

                remove_button = tk.Button(row_frame, text="解除", command=lambda idx=i: self.remove_directory(idx))
                remove_button.pack(side=tk.LEFT)

    def _is_already_registered_or_sub(self, new_dir):
        new_abs = os.path.abspath(new_dir)
        for e in self.directory_list:
            e_abs = os.path.abspath(e)
            if new_abs == e_abs:
                return True
            c = os.path.commonprefix([new_abs, e_abs])
            if c == e_abs or c == new_abs:
                return True
        return False

    # -------------------------------------------------------------------------
    # Ignore Patterns
    # -------------------------------------------------------------------------
    def get_user_ignore_patterns(self):
        txt = self.ignore_entry.get().strip()
        arr = [x.strip() for x in txt.split(",") if x.strip()]
        return arr

    # -------------------------------------------------------------------------
    # YAML生成
    # -------------------------------------------------------------------------
    def start_generate_yaml(self):
        self.progress_text.delete("1.0", tk.END)
        if not self.directory_list:
            self._log_progress("ターゲットディレクトリが登録されていません。")
            return

        t = threading.Thread(target=self._generate_yaml_thread)
        t.daemon = True
        t.start()

    def _generate_yaml_thread(self):
        self._log_progress("走査を開始します...")

        directories = self.directory_list
        user_ignore_patterns = self.get_user_ignore_patterns()
        project_name = self._get_project_name_entry_str()

        if not project_name:
            # ユーザ入力が空ならディレクトリ名連結
            project_name = self._generate_default_project_name(directories)

        max_file_size = int(self.file_size_spin.get())
        combined_ignore = DEFAULT_IGNORE_PATTERNS + user_ignore_patterns

        structure_data = collect_directory_structures(
            directories,
            combined_ignore,
            progress_callback=self._progress_callback,
            max_file_size_bytes=max_file_size
        )
        self._log_progress("YAMLの生成を開始します...")

        yaml_text = generate_yaml(structure_data, project_name)
        self._yaml_result = yaml_text

        self._log_progress("YAML生成が完了しました。")
        self.enable_copy_save_buttons()

    def _generate_default_project_name(self, directories):
        if not directories:
            return "UnnamedProject"
        folder_names = [os.path.basename(os.path.normpath(d)) for d in directories]
        return "_".join(folder_names)

    # -------------------------------------------------------------------------
    # Progress Queue
    # -------------------------------------------------------------------------
    def check_progress_queue(self):
        while True:
            try:
                msg = self.progress_queue.get_nowait()
            except queue.Empty:
                break
            else:
                self.progress_text.insert(tk.END, msg + "\n")
                self.progress_text.see(tk.END)
        self.root.after(100, self.check_progress_queue)

    def _progress_callback(self, message):
        self.progress_queue.put(message)

    def _log_progress(self, message):
        self.progress_queue.put(message)

    # -------------------------------------------------------------------------
    # クリア / コピー / 保存
    # -------------------------------------------------------------------------
    def clear_yaml_result(self):
        self._yaml_result = ""
        self.disable_copy_save_buttons()
        self.progress_text.delete("1.0", tk.END)
        self._log_progress("YAMLをクリアしました。")

    def copy_to_clipboard(self):
        if not self._yaml_result:
            return
        pyperclip.copy(self._yaml_result)
        self._log_progress("YAMLをクリップボードにコピーしました。")

    def save_to_file(self):
        if not self._yaml_result:
            return

        # プロジェクト名 or fallback
        p_name = self._get_project_name_entry_str() or "UnnamedProject"
        # 日付(yyyy-mm-dd)
        date_str = datetime.datetime.now().strftime("%Y-%m-%d")
        default_filename = f"{p_name}_{date_str}.yml"

        file_path = filedialog.asksaveasfilename(
            defaultextension=".yml",
            initialfile=default_filename,
            filetypes=[("YAML files", "*.yml"), ("All files", "*.*")]
        )
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(self._yaml_result)
                self._log_progress(f"YAMLを保存しました: {file_path}")
            except Exception as e:
                self._log_progress(f"保存中にエラーが発生しました: {e}")

    # -------------------------------------------------------------------------
    # ボタン有効/無効
    # -------------------------------------------------------------------------
    def enable_copy_save_buttons(self):
        self.copy_button.config(state="normal", bg=self.copy_button_active_bg)
        self.save_button.config(state="normal", bg=self.save_button_active_bg)

    def disable_copy_save_buttons(self):
        self.copy_button.config(state="disabled", bg=self.button_disabled_bg)
        self.save_button.config(state="disabled", bg=self.button_disabled_bg)

    # -------------------------------------------------------------------------
    # プロジェクト名 Entry & Placeholder
    # -------------------------------------------------------------------------
    def _on_project_name_focus_in(self, event):
        if self.project_name_is_placeholder:
            self.project_name_entry.delete(0, tk.END)
            self.project_name_entry.config(fg="black")
            self.project_name_is_placeholder = False

    def _on_project_name_focus_out(self, event):
        text = self.project_name_entry.get().strip()
        if not text:
            self._refresh_project_name_placeholder()

    def _refresh_project_name_placeholder(self):
        default_name = self._generate_default_project_name(self.directory_list)
        self._set_placeholder(default_name)

    def _set_placeholder(self, text):
        self.project_name_entry.delete(0, tk.END)
        self.project_name_entry.config(fg="gray50")
        self.project_name_entry.insert(0, text)
        self.project_name_is_placeholder = True
        self.project_name_placeholder = text

    def _get_project_name_entry_str(self):
        if self.project_name_is_placeholder:
            return ""
        return self.project_name_entry.get().strip()

    def _set_project_name_entry_str(self, s):
        if not s:
            self._refresh_project_name_placeholder()
        else:
            self.project_name_entry.delete(0, tk.END)
            self.project_name_entry.config(fg="black")
            self.project_name_entry.insert(0, s)
            self.project_name_is_placeholder = False
            self.project_name_placeholder = ""
