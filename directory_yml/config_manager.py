import json
import os

CONFIG_VERSION = "1.0.0"  # バージョン表記

class ConfigManager:
    def __init__(self, config_path="config.json"):
        self.config_path = config_path
        self.config_data = {}
        self.load_config()

    def load_config(self):
        """
        config.json を読み込み、辞書形式で self.config_data に格納する。
        - 存在しない場合はデフォルト構造を初期化
        - バージョン表記がない/古い場合は migrate して保存
        """
        if not os.path.exists(self.config_path):
            # ファイルが無い場合はデフォルト構造
            self.config_data = {
                "config_version": CONFIG_VERSION,
                "profiles": {
                    "profile1": {
                        "project_name": "",
                        "directories": [],
                        "ignore_patterns": [],
                        "max_file_size_bytes": 500000
                    }
                },
                "active_profile": "profile1"
            }
            self.save_config(self.config_data)
            return

        with open(self.config_path, "r", encoding="utf-8") as f:
            try:
                self.config_data = json.load(f)
            except json.JSONDecodeError:
                # JSONとして読み込めない場合 → 諦めて新規
                self._init_default()
                return

        # バージョンチェック
        if "config_version" not in self.config_data:
            # バージョンが無い → migrate_old_formatを試みる
            self.config_data["config_version"] = "0.0.0"
            # migrate内でうまく変換できなければ、最終的に空構造に
            self.migrate_old_format()
        elif self.config_data["config_version"] != CONFIG_VERSION:
            # 既存バージョンが古い or 異なる
            self.migrate_old_format()

        # active_profile が無い場合の補填
        if "active_profile" not in self.config_data:
            if self.get_profile_names():
                self.config_data["active_profile"] = self.get_profile_names()[0]
            else:
                self._init_default()

        self.save_config(self.config_data)

    def _init_default(self):
        """デフォルトの構造を生成し保存"""
        self.config_data = {
            "config_version": CONFIG_VERSION,
            "profiles": {
                "profile1": {
                    "project_name": "",
                    "directories": [],
                    "ignore_patterns": [],
                    "max_file_size_bytes": 500000
                }
            },
            "active_profile": "profile1"
        }
        self.save_config(self.config_data)

    def migrate_old_format(self):
        """
        旧フォーマット or バージョン相違を対象に、
        新形式 (config_version='1.0.0') に変換する。
        
        - バージョン無い場合は '0.0.0' とみなし、下記キーを引っ張れるなら profile1 に移行する
        - 失敗しても続行(空構造に上書き)
        """
        old_config_version = self.config_data.get("config_version", "0.0.0")
        if old_config_version == CONFIG_VERSION:
            return  # 既に最新

        # もし profiles が既にある場合 → それはそれでOKとしてバージョンだけ合わせる
        if "profiles" not in self.config_data or not isinstance(self.config_data["profiles"], dict):
            # 旧フォーマットからキーを引っ張れるか試す
            directories = self.config_data.pop("directories", None)
            ignore_patterns = self.config_data.pop("ignore_patterns", None)
            max_file_size_bytes = self.config_data.pop("max_file_size_bytes", None)

            if isinstance(directories, list) or isinstance(ignore_patterns, list) or isinstance(max_file_size_bytes, int):
                # とりあえず何か1つでも該当キーがあれば、profile1を作る
                directories = directories if isinstance(directories, list) else []
                ignore_patterns = ignore_patterns if isinstance(ignore_patterns, list) else []
                max_file_size_bytes = max_file_size_bytes if isinstance(max_file_size_bytes, int) else 500000

                self.config_data["profiles"] = {
                    "profile1": {
                        "project_name": "",
                        "directories": directories,
                        "ignore_patterns": ignore_patterns,
                        "max_file_size_bytes": max_file_size_bytes
                    }
                }
                self.config_data["active_profile"] = "profile1"
            else:
                # まったく見当たらない → 空初期化
                self._init_default()
                return

        # バージョンを更新
        self.config_data["config_version"] = CONFIG_VERSION
        self.save_config(self.config_data)

    def save_config(self, config_data):
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(config_data, f, ensure_ascii=False, indent=4)

    # -----------------------------
    # プロファイル操作用 ヘルパー
    # -----------------------------
    def get_profile_names(self):
        return list(self.config_data.get("profiles", {}).keys())

    def get_active_profile_name(self):
        return self.config_data.get("active_profile", "")

    def set_active_profile(self, profile_name):
        if profile_name in self.get_profile_names():
            self.config_data["active_profile"] = profile_name
            self.save_config(self.config_data)

    def load_profile_data(self, profile_name):
        return self.config_data.get("profiles", {}).get(profile_name, {})

    def save_profile_data(self, profile_name, data):
        self.config_data.setdefault("profiles", {})
        self.config_data["profiles"][profile_name] = data
        self.config_data["active_profile"] = profile_name
        self.save_config(self.config_data)

    def create_new_profile(self):
        existing = self.get_profile_names()
        base_name = "profile"
        max_num = 0
        for pname in existing:
            if pname.startswith(base_name):
                try:
                    num = int(pname[len(base_name):])
                    if num > max_num:
                        max_num = num
                except ValueError:
                    pass
        new_num = max_num + 1
        new_name = f"{base_name}{new_num}"

        default_data = {
            "project_name": "",
            "directories": [],
            "ignore_patterns": [],
            "max_file_size_bytes": 500000
        }
        self.save_profile_data(new_name, default_data)
        return new_name

    def duplicate_profile(self, source_profile_name):
        if source_profile_name not in self.get_profile_names():
            return None
        src_data = self.load_profile_data(source_profile_name)

        # 新しい名前を "xxxのコピー", 既に存在すれば連番
        base_new_name = f"{source_profile_name}のコピー"
        new_name = base_new_name
        idx = 2
        while new_name in self.get_profile_names():
            new_name = f"{base_new_name}({idx})"
            idx += 1

        import copy
        new_data = copy.deepcopy(src_data)

        self.save_profile_data(new_name, new_data)
        return new_name

    def rename_profile(self, old_name, new_name):
        if new_name in self.get_profile_names():
            return None
        if old_name not in self.get_profile_names():
            return None

        data = self.load_profile_data(old_name)
        self.config_data["profiles"][new_name] = data
        del self.config_data["profiles"][old_name]

        if self.config_data["active_profile"] == old_name:
            self.config_data["active_profile"] = new_name

        self.save_config(self.config_data)
        return new_name

    def delete_profile(self, profile_name):
        if profile_name not in self.get_profile_names():
            return

        all_profiles = self.get_profile_names()
        if len(all_profiles) == 1 and all_profiles[0] == profile_name:
            self._init_default()
        else:
            del self.config_data["profiles"][profile_name]
            if self.config_data["active_profile"] == profile_name:
                remain = self.get_profile_names()
                if remain:
                    self.config_data["active_profile"] = remain[0]
        self.save_config(self.config_data)
