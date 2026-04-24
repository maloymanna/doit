import os
from .config import Config
from .permissions import Permissions
from .logging import ProjectLogger
from .files import FileAccess
from .git_wrapper import GitWrapper
from .browser import BrowserController
from .plugins import load_plugins
from .plugins.base import TaskContext

class Orchestrator:
    def __init__(self, workspace_root: str, prompt_user_fn):
        self.config = Config(workspace_root)
        self.permissions = Permissions(self.config, prompt_user_fn)
        self.plugins = load_plugins()
        self._browser = None

    def _get_project_logger(self, project_name: str) -> ProjectLogger:
        project_root = os.path.join(self.config.workspace_root, "projects", project_name)
        return ProjectLogger(project_root)

    def _get_browser(self) -> BrowserController:
        if self._browser is None:
            pw_cfg = self.config.load_playwright_config()
            self._browser = BrowserController(pw_cfg, self.permissions, None)
        return self._browser

    def run_command(self, command_name: str, args: dict) -> dict:
        plugin = self.plugins.get(command_name)
        if not plugin:
            raise RuntimeError(f"No plugin registered for command: {command_name}")

        project_name = args.get("project_name", "default")
        logger = self._get_project_logger(project_name)
        files = FileAccess(self.permissions, logger)
        git = GitWrapper(self.permissions, logger)
        browser = self._get_browser()

        ctx = TaskContext(project_name, self.config, files, browser, git, logger)
        return plugin.run(ctx, args)
