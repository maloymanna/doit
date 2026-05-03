# src/doit/core/action_dispatcher.py [MOD v2.2]
from pathlib import Path
from typing import Dict, Any, Optional
import logging
from .tool_registry import ToolRegistry
from .security_enforcer import SecurityEnforcer

# Direct module imports bypass Windows __init__.py namespace resolution quirks
from doit.plugins.files import (
    file_read, FILE_READ_SCHEMA,
    file_write, FILE_WRITE_SCHEMA
)
from doit.plugins.browser_ops import (
    browser_navigate, NAVIGATE_SCHEMA,
    browser_scrape, SCRAPE_SCHEMA
)

logger = logging.getLogger(__name__)

class ActionDispatcher:
    def __init__(self, workspace_dir: Path, page: Optional[Any] = None):
        self.workspace = workspace_dir
        self.page = page  # Playwright page object
        self.registry = ToolRegistry()
        self.security = SecurityEnforcer(workspace_dir)
        self._register_tools()

    def _register_tools(self):
        # File Tools
        self.registry.register("file_read", "Reads text content from a local file. Truncates output.", FILE_READ_SCHEMA, file_read)
        self.registry.register("file_write", "Writes text content to a local file. Creates dirs.", FILE_WRITE_SCHEMA, file_write)
        
        # Browser Tools
        self.registry.register("browser_navigate", "Opens URL in current tab. Waits for load.", NAVIGATE_SCHEMA, browser_navigate)
        self.registry.register("browser_scrape", "Extracts text/attr from page or selector.", SCRAPE_SCHEMA, browser_scrape)

    def dispatch(self, action: Dict[str, Any]) -> Dict[str, Any]:
        tool_name = action.get("tool_name")
        params = action.get("parameters", {})
        logger.info(f"[DISPATCH] -> {tool_name}")
        
        # 1. Security Check (Path Traversal, Allowlist)
        try:
            params = self.security.validate_call(tool_name, params)
        except PermissionError as e:
            return {"status": "error", "output": f"Security: {e}"}

        # 2. Schema Validation
        try:
            self.registry.validate_params(tool_name, params)
        except Exception as e:
            return {"status": "error", "output": f"Invalid params: {e}"}

        # 3. Execution
        try:
            context = {"page": self.page}
            return self.registry.execute(tool_name, params, **context)
        except Exception as e:
            return {"status": "error", "output": f"Exec failed: {e}"}