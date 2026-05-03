# src/doit/core/__init__.py [MOD v2.1]
# Re-exports for Phase 1 only. No premature imports.

from .state_manager import SQLiteStateManager
# Backward-compat alias for old code expecting StateManager
StateManager = SQLiteStateManager

from .prompt_builder import SingleLinePromptBuilder
from .json_validator import JSONValidator, ValidationError

# AgentOrchestrator is safe to import now (deferred imports inside __init__)
from .agent_orchestrator import AgentOrchestrator

# ActionDispatcher is a stub in Phase 1; full impl in Phase 2
from .action_dispatcher import ActionDispatcher

__all__ = [
    "SQLiteStateManager",
    "StateManager",  # alias
    "SingleLinePromptBuilder",
    "JSONValidator",
    "ValidationError",
    "AgentOrchestrator",
    "ActionDispatcher",  # stub in Phase 1
]