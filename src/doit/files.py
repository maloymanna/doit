from pathlib import Path
from typing import Optional, List


class FileAccessError(Exception):
    pass


class FileManager:
    """
    Secure file access layer for doit.

    Responsibilities:
    - Enforce workspace sandbox (no traversal above workspace_root)
    - Enforce readonly_input/ as read-only
    - Provide safe read/write helpers
    - Provide safe path resolution
    """

    def __init__(self, permissions):
        self.permissions = permissions
        self.workspace_root = Path(permissions.workspace_root).resolve()
        self.readonly_root = self.workspace_root / "readonly_input"

    # ------------------------------------------------------------
    # Path resolution + sandboxing
    # ------------------------------------------------------------
    def resolve_path(self, path: str) -> Path:
        """
        Resolve a path safely inside the workspace sandbox.
        """
        p = Path(path)

        # If relative, interpret relative to workspace root
        if not p.is_absolute():
            p = self.workspace_root / p

        resolved = p.resolve()

        # Enforce sandbox: must stay inside workspace_root
        if not str(resolved).startswith(str(self.workspace_root)):
            raise FileAccessError(f"Access outside workspace forbidden: {resolved}")

        return resolved

    # ------------------------------------------------------------
    # Read-only enforcement
    # ------------------------------------------------------------
    def ensure_writable(self, path: Path):
        """
        Prevent writes to readonly_input/.
        """
        if str(path).startswith(str(self.readonly_root)):
            raise FileAccessError(f"readonly_input/ is read-only: {path}")

    # ------------------------------------------------------------
    # File operations
    # ------------------------------------------------------------
    def read_text(self, path: str, encoding="utf-8") -> str:
        p = self.resolve_path(path)
        if not p.exists():
            raise FileAccessError(f"File not found: {p}")
        return p.read_text(encoding=encoding)

    def write_text(self, path: str, data: str, encoding="utf-8"):
        p = self.resolve_path(path)
        self.ensure_writable(p)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(data, encoding=encoding)

    def read_bytes(self, path: str) -> bytes:
        p = self.resolve_path(path)
        if not p.exists():
            raise FileAccessError(f"File not found: {p}")
        return p.read_bytes()

    def write_bytes(self, path: str, data: bytes):
        p = self.resolve_path(path)
        self.ensure_writable(p)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)

    # ------------------------------------------------------------
    # Directory utilities
    # ------------------------------------------------------------
    def list_files(self, path: str) -> List[Path]:
        p = self.resolve_path(path)
        if not p.exists():
            return []
        if not p.is_dir():
            raise FileAccessError(f"Not a directory: {p}")
        return list(p.iterdir())
