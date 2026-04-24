import os
import yaml

class Config:
    def __init__(self, workspace_root: str):
        self.workspace_root = os.path.abspath(workspace_root)
        self.doit_dir = os.path.join(self.workspace_root, ".doit")
        self.config_path = os.path.join(self.doit_dir, "config.yaml")
        self.allowlist_path = os.path.join(self.doit_dir, "allowlist.txt")
        self.autonomy_mode_path = os.path.join(self.doit_dir, "autonomy_mode")
        self.playwright_config_path = os.path.join(self.doit_dir, "playwright_config.yaml")

    def ensure_dirs(self):
        os.makedirs(self.doit_dir, exist_ok=True)

    def load_config(self) -> dict:
        if not os.path.exists(self.config_path):
            return {}
        with open(self.config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def save_config(self, data: dict) -> None:
        self.ensure_dirs()
        with open(self.config_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f)

    def load_playwright_config(self) -> dict:
        if not os.path.exists(self.playwright_config_path):
            return {}
        with open(self.playwright_config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def get_autonomy_mode(self) -> int:
        try:
            with open(self.autonomy_mode_path, "r", encoding="utf-8") as f:
                return int(f.read().strip())
        except FileNotFoundError:
            return 0

    def set_autonomy_mode(self, mode: int) -> None:
        self.ensure_dirs()
        with open(self.autonomy_mode_path, "w", encoding="utf-8") as f:
            f.write(str(mode))

    def get_max_iterations_limit(self) -> int:
        cfg = self.load_config()
        return int(cfg.get("max_iterations_limit", 20))
