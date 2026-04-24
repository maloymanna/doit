import os

class Permissions:
    def __init__(self, config, prompt_user_fn):
        self.config = config
        self.prompt_user = prompt_user_fn

    @property
    def workspace_root(self) -> str:
        return self.config.workspace_root

    @property
    def readonly_input_dir(self) -> str:
        cfg = self.config.load_config()
        return os.path.join(self.workspace_root, cfg.get("readonly_input_dir", "readonly_input"))

    def _normalize(self, path: str) -> str:
        return os.path.abspath(path)

    def check_path(self, path: str) -> None:
        p = self._normalize(path)
        if not p.startswith(self.workspace_root):
            raise RuntimeError(f"Path outside workspace: {p}")

    def can_read(self, path: str) -> bool:
        self.check_path(path)
        return True

    def can_write(self, path: str) -> bool:
        self.check_path(path)
        if self._normalize(path).startswith(self._normalize(self.readonly_input_dir)):
            raise RuntimeError("Cannot write into readonly_input")
        return True

    def can_delete(self, path: str, recursive: bool = False) -> bool:
        self.check_path(path)
        return False

    def ensure_url_allowed(self, url: str) -> None:
        pass
