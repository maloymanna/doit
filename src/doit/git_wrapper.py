class GitWrapper:
    def __init__(self, permissions, logger):
        self.permissions = permissions
        self.logger = logger

    def init_repo(self, path: str) -> None:
        pass

    def clone_repo(self, remote_url: str, path: str) -> None:
        pass

    def status(self, path: str) -> str:
        return ""

    def add_and_commit(self, path: str, message: str, files=None) -> None:
        pass

    def pull(self, path: str, remote="origin", branch="main") -> None:
        pass

    def push(self, path: str, remote="origin", branch="main") -> None:
        pass
