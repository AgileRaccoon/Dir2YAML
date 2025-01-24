import json
import os

class ConfigManager:
    def __init__(self, config_path="config.json"):
        self.config_path = config_path

    def load_config(self):
        """
        config.json を読み込み、辞書形式で返す。
        存在しない場合は空の辞書を返す。
        """
        if not os.path.exists(self.config_path):
            return {}
        with open(self.config_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def save_config(self, config_data):
        """
        config_data (dict) を JSON ファイルに書き込む。
        """
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(config_data, f, ensure_ascii=False, indent=4)
