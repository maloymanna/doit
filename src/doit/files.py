import os

class FileAccess:
    def __init__(self, permissions, logger):
        self.permissions = permissions
        self.logger = logger

    def read_file(self, path: str) -> bytes:
        self.permissions.can_read(path)
        with open(path, "rb") as f:
            data = f.read()
        self.logger.log("file_read", {"path": path}, autonomy_mode=0, approved=None)
        return data

    def write_file(self, path: str, content: bytes) -> None:
        self.permissions.can_write(path)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(content)
        self.logger.log("file_write", {"path": path}, autonomy_mode=0, approved=None)
