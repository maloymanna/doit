from pathlib import Path
import yaml

DEFAULT_CONFIG = {
    "workspace_root": None,
    "default_ui_url": None,
    "model_name": "GPT-5.1",
    "playwright": {
        "headless": False,
        "timeout_ms": 20000,
        "launch_args": ["--disable-blink-features=AutomationControlled"]
    }
}


class Config:
    """
    Minimal config helper used by Orchestrator.
    Exposes:
      - self.data (dict)
      - self.config_dir (Path)
    Creates <workspace>/.doit/ and a config.yaml if missing.
    """

    def __init__(self, workspace_root):
        self.workspace_root = Path(workspace_root).resolve()
        self.config_dir = self.workspace_root / ".doit"
        self.config_dir.mkdir(parents=True, exist_ok=True)

        self.config_file = self.config_dir / "config.yaml"
        if not self.config_file.exists():
            # write defaults with workspace_root filled in
            defaults = dict(DEFAULT_CONFIG)
            defaults["workspace_root"] = str(self.workspace_root)
            self._write_yaml(self.config_file, defaults)
            self.data = defaults
        else:
            self.data = self._read_yaml(self.config_file)
            # ensure workspace_root present
            if not self.data.get("workspace_root"):
                self.data["workspace_root"] = str(self.workspace_root)
                self._write_yaml(self.config_file, self.data)

    def _read_yaml(self, path: Path):
        try:
            with path.open("r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception:
            return {}

    def _write_yaml(self, path: Path, data: dict):
        with path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(data, f)

    def get(self, key, default=None):
        return self.data.get(key, default)
