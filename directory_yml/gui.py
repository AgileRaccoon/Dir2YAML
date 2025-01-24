import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox
import threading
import queue
import pyperclip
import os

from .config_manager import ConfigManager
from .file_processing import collect_directory_structures
from .yml_generator import generate_yaml

DEFAULT_IGNORE_PATTERNS = [".env", ".htpasswd", "*.log"]

class DirectoryYmlGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Dir2YAML")
        self.root.geometry("550x600")

        self.progress_queue = queue.Queue()
        self._yaml_result = ""

        # ロード
        self.config_manager = ConfigManager()
        self.config_data = self.config_manager.load_config()

        # ディレクトリ一覧・最大ファイルサイズ等の設定読み込み
        self.directory_list = self.config_data.get("directories", [])
        self.user_ignore_patterns = self.config_data.get("ignore_patterns", [])
        self.max_file_size_bytes = self.config_data.get("max_file_size_bytes", 50000)

        # コピー/保存 ボタン有効時の色を保持
        self.copy_button_active_bg = "#2196F3"
        self.save_button_active_bg = "#FF9800"
        # 無効時の色
        self.button_disabled_bg = "#555555"

        main_frame = tk.Frame(self.root)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # --- Directories セクション ---
        dir_frame = tk.LabelFrame(main_frame, text="Directories", padx=10, pady=10)
        dir_frame.pack(fill="x")

        self.add_dir_button = tk.Button(
            dir_frame, text="ディレクトリ追加", command=self.add_directory
        )
        self.add_dir_button.pack(side=tk.LEFT)

        self.dir_list_frame = tk.Frame(dir_frame)
        self.dir_list_frame.pack(fill="x", padx=10, pady=5)
        self.update_dir_list_display()

        # --- Ignore Patterns セクション ---
        ignore_frame = tk.LabelFrame(main_frame, text="除外パターン", padx=10, pady=10)
        ignore_frame.pack(fill="x", pady=5)

        default_label_text = "デフォルト: " + ", ".join(DEFAULT_IGNORE_PATTERNS)
        tk.Label(ignore_frame, text=default_label_text).pack(anchor="w")

        row_ignore_user = tk.Frame(ignore_frame)
        row_ignore_user.pack(anchor="w", fill="x", pady=5)

        tk.Label(row_ignore_user, text="ユーザパターン: ").pack(side=tk.LEFT)
        self.ignore_entry = tk.Entry(row_ignore_user, width=50)
        self.ignore_entry.insert(0, ",".join(self.user_ignore_patterns))
        self.ignore_entry.pack(side=tk.LEFT, padx=5)

        self.register_ignore_button = tk.Button(
            row_ignore_user,
            text="登録",
            command=self.register_ignore_patterns
        )
        self.register_ignore_button.pack(side=tk.LEFT)

        # --- YAML生成、プロジェクト名、クリア、→、コピー、保存を横一列に ---
        button_frame = tk.Frame(main_frame)
        button_frame.pack(fill="x", pady=10)
        button_frame.pack_configure(anchor="center")

        # プロジェクト名のラベル + Entry
        tk.Label(button_frame, text="プロジェクト名:").pack(side=tk.LEFT, padx=5)
        self.project_name_entry = tk.Entry(button_frame, width=20)
        self.project_name_entry.pack(side=tk.LEFT)

        # YAML生成ボタン
        self.generate_button = tk.Button(
            button_frame,
            text="YAML生成",
            command=self.start_generate_yaml,
            bg="#4CAF50",
        )
        self.generate_button.pack(side=tk.LEFT, padx=10)

        # クリアボタン
        self.clear_button = tk.Button(
            button_frame,
            text="クリア",
            command=self.clear_yaml_result
        )
        self.clear_button.pack(side=tk.LEFT, padx=(30,5))

        # 矢印ラベル (クリア -> コピー の間)
        arrow_label = tk.Label(button_frame, text=" ➡ ", font=("Arial", 12, "bold"))
        arrow_label.pack(side=tk.LEFT, padx=5)

        # コピーボタン (初期は無効)
        self.copy_button = tk.Button(
            button_frame,
            text="コピー",
            command=self.copy_to_clipboard,
            bg=self.copy_button_active_bg,
            state="disabled"
        )
        self.copy_button.pack(side=tk.LEFT, padx=5)

        # 保存ボタン (初期は無効)
        self.save_button = tk.Button(
            button_frame,
            text="保存",
            command=self.save_to_file,
            bg=self.save_button_active_bg,
            state="disabled"
        )
        self.save_button.pack(side=tk.LEFT, padx=5)

        # --- Progress Log ---
        progress_frame = tk.LabelFrame(main_frame, text="Progress Log", padx=10, pady=10)
        progress_frame.pack(fill="both", expand=True, pady=5)

        self.progress_text = scrolledtext.ScrolledText(progress_frame, width=80, height=10)
        self.progress_text.pack(fill="both", expand=True)

        self.check_progress_queue()
        
        self.disable_copy_save_buttons()

    def run(self):
        self.root.mainloop()

    # -------------------------------------------
    # Directories: 追加・削除
    # -------------------------------------------
    def add_directory(self):
        dir_path = filedialog.askdirectory()
        if dir_path:
            dir_path = os.path.abspath(dir_path)
            if self._is_already_registered_or_sub(dir_path):
                messagebox.showerror("エラー", f"既に登録済み、またはサブ/上位ディレクトリです: {dir_path}")
                return
            self.directory_list.append(dir_path)
            self.update_dir_list_display()

    def remove_directory(self, idx):
        del self.directory_list[idx]
        self.update_dir_list_display()

    def update_dir_list_display(self):
        for widget in self.dir_list_frame.winfo_children():
            widget.destroy()

        if not self.directory_list:
            tk.Label(self.dir_list_frame, text="(ディレクトリは追加されていません)").pack(anchor="w")
        else:
            for i, d in enumerate(self.directory_list):
                row_frame = tk.Frame(self.dir_list_frame)
                row_frame.pack(anchor="w", fill="x", pady=2)

                label = tk.Label(row_frame, text=d)
                label.pack(side=tk.LEFT, padx=5)

                remove_button = tk.Button(
                    row_frame, text="解除", command=lambda idx=i: self.remove_directory(idx)
                )
                remove_button.pack(side=tk.LEFT)

    def _is_already_registered_or_sub(self, new_dir):
        new_abs = os.path.abspath(new_dir)
        for existing in self.directory_list:
            existing_abs = os.path.abspath(existing)
            if new_abs == existing_abs:
                return True
            common = os.path.commonprefix([new_abs, existing_abs])
            if common == existing_abs or common == new_abs:
                return True
        return False

    # -------------------------------------------
    # Ignore Patterns 登録
    # -------------------------------------------
    def register_ignore_patterns(self):
        user_ignore_str = self.ignore_entry.get().strip()
        user_ignore_list = [p.strip() for p in user_ignore_str.split(",") if p.strip()]

        self.config_data["directories"] = self.directory_list
        self.config_data["ignore_patterns"] = user_ignore_list
        self.config_data["max_file_size_bytes"] = self.max_file_size_bytes

        self.config_manager.save_config(self.config_data)
        self.user_ignore_patterns = user_ignore_list

        self._log_progress("除外パターンを登録しました。")

    # -------------------------------------------
    # YAML生成
    # -------------------------------------------
    def start_generate_yaml(self):
        # ログをクリア
        self.progress_text.delete("1.0", tk.END)

        user_ignore_str = self.ignore_entry.get().strip()
        user_ignore_list = [p.strip() for p in user_ignore_str.split(",") if p.strip()]
        self.user_ignore_patterns = user_ignore_list

        # config再保存
        self.config_data["directories"] = self.directory_list
        self.config_data["ignore_patterns"] = user_ignore_list
        self.config_data["max_file_size_bytes"] = self.max_file_size_bytes
        self.config_manager.save_config(self.config_data)
        
        if self.directory_list == []:
            self._log_progress("ターゲットディレクトリが登録されていません。")
            return

        # スレッド起動
        t = threading.Thread(
            target=self._generate_yaml_thread,
            args=(user_ignore_list,)
        )
        t.daemon = True
        t.start()

    def _generate_yaml_thread(self, user_ignore_list):
        self._log_progress("走査を開始します...")

        combined_ignore = DEFAULT_IGNORE_PATTERNS + user_ignore_list
        structure_data = collect_directory_structures(
            self.directory_list,
            combined_ignore,
            progress_callback=self._progress_callback,
            max_file_size_bytes=self.max_file_size_bytes
        )

        self._log_progress("YAMLの生成を開始します...")

        # プロジェクト名: ユーザ入力があれば優先、無ければ自動生成
        proj_name_input = self.project_name_entry.get().strip()
        if proj_name_input:
            project_name = proj_name_input
        else:
            project_name = self._generate_default_project_name(self.directory_list)

        yaml_text = generate_yaml(structure_data, project_name)
        self._yaml_result = yaml_text

        self._log_progress("YAML生成が完了しました。")

        # コピー/保存ボタンを有効化
        self.enable_copy_save_buttons()

    def _generate_default_project_name(self, directories):
        if not directories:
            return "UnnamedProject"
        folder_names = []
        for d in directories:
            name = os.path.basename(os.path.normpath(d))
            folder_names.append(name)
        return "_".join(folder_names) if len(folder_names) > 1 else folder_names[0]

    # -------------------------------------------
    # チェック / コールバック
    # -------------------------------------------
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

    # -------------------------------------------
    # クリア / コピー / 保存
    # -------------------------------------------
    def clear_yaml_result(self):
        """
        生成済みYAMLを破棄し、コピー&保存ボタンを無効化。
        """
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
        if len(self.directory_list) == 1:
            dir_name = os.path.basename(os.path.normpath(self.directory_list[0]))
            default_filename = f"{dir_name}.yml"
        else:
            default_filename = "directories.yml"

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

    # -------------------------------------------
    # ボタン有効/無効化のユーティリティ
    # -------------------------------------------
    def enable_copy_save_buttons(self):
        self.copy_button.config(
            state="normal",
            bg=self.copy_button_active_bg
        )
        self.save_button.config(
            state="normal",
            bg=self.save_button_active_bg
        )

    def disable_copy_save_buttons(self):
        self.copy_button.config(
            state="disabled",
            bg=self.button_disabled_bg
        )
        self.save_button.config(
            state="disabled",
            bg=self.button_disabled_bg
        )
