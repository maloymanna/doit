# src/doit/core/action_dispatcher.py [v1]
# Minimal stub for Phase 1 compatibility. Full implementation in Phase 2.
from typing import Dict, Any, Callable, Optional
from pathlib import Path

class ActionDispatcher:
    """
    Stub dispatcher for Phase 1. 
    Full tool routing + security enforcement implemented in Phase 2.
    """
    def __init__(self, workspace_dir: Path, tool_registry: Optional[Any] = None):
        self.workspace = workspace_dir
        self.tool_registry = tool_registry
        self._handlers: Dict[str, Callable] = {}

    def register_handler(self, tool_name: str, handler: Callable):
        """Register a tool handler (used in Phase 2)."""
        self._handlers[tool_name] = handler

    def dispatch(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """
        Stub dispatch: returns a placeholder result.
        In Phase 2, this will route to tool_registry + security_enforcer.
        """
        tool_name = action.get("tool_name", "unknown")
        return {
            "status": "stub",
            "output": f"[STUB] Tool '{tool_name}' not yet implemented. Phase 2 pending.",
            "tool_name": tool_name,
            "parameters": action.get("parameters", {})
        }