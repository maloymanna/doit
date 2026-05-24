# src/doit/core/agent_orchestrator.py [v4.9 ]
import uuid
import logging
# === < Phase 7 > ===
import asyncio
from typing import Optional
# === < / Phase 7 > ===
from pathlib import Path
from typing import Callable, Any, Dict, List

from .state_manager import SQLiteStateManager, VALID_STATUSES
from .prompt_builder import SingleLinePromptBuilder
from .json_validator import JSONValidator, ValidationError
from .action_dispatcher import ActionDispatcher

logger = logging.getLogger(__name__)

def request_intervention(params: Dict, **ctx) -> Dict:
    return {"status": "intervention_required", "output": f"Clarification needed: {params.get('missing_context', 'Unknown')}"}

class AgentOrchestrator:
    def __init__(self, 
                 workspace_dir: Path,
                 project: str,
                 llm_client: Optional[Callable[[str], str]] = None,
                 action_dispatcher: Optional[Any] = None,
                 prompt_builder: Optional[SingleLinePromptBuilder] = None,
                 validator: Optional[JSONValidator] = None,
                 # === < Phase 7 > ===
                 # Config-driven values (caller reads from config.yaml via config.py)
                 autonomy_mode: int = 0,
                 whitelist: Optional[List[str]] = None,
                 controller: Optional[Any] = None,
                 loop: Optional[asyncio.AbstractEventLoop] = None):
                 # === < / Phase 7 > ===
        self.workspace = workspace_dir
        self.project = project
        self.project_dir = workspace_dir / "projects" / project
        self.project_dir.mkdir(parents=True, exist_ok=True)
        
        self.llm = llm_client
        self.builder = prompt_builder or SingleLinePromptBuilder()
        self.validator = validator or JSONValidator()
        self.state_mgr = SQLiteStateManager(workspace_dir)

        # UNCONDITIONALLY register core tools to builder
        self.builder.register_tool("file_read", "Reads content from a file relative to project dir")
        self.builder.register_tool("file_write", "Writes content to a file relative to project dir")
        self.builder.register_tool("request_intervention", "Halts loop for user clarification")
        
        # === < Phase 7 > ===
        self.builder.register_tool("browser_navigate", "Navigates browser to a URL")
        self.builder.register_tool("browser_fill", "Fills a form field by CSS selector")
        self.builder.register_tool("browser_click_text", "Clicks an element by visible text")
        self.builder.register_tool("browser_wait_for_element", "Waits for a selector to be visible")
        self.builder.register_tool("browser_screenshot", "Captures full-page screenshot | params: {\"path\": \"relative/path.png\"}")
        self.builder.register_tool("browser_trigger_download", 
            "Clicks a selector to trigger file download | params: {\"selector\": \"string\", \"download_dir\": \"string\"}")        
        self.builder.register_tool("browser_fetch_resource", 
            "Fetches direct resource URL and saves to project dir | params: {\"url\": \"string\", \"save_path\": \"string\"}")
        # === < / Phase 7 > ===

        # Initialize dispatcher
        if action_dispatcher is None:
            # === < Phase 7 > ===
            # Matches v4.7 dispatcher init pattern + Phase 7 controller/loop injection
            self.dispatcher = ActionDispatcher(workspace_dir, self.project_dir, controller, loop)
            # === < / Phase 7 > ===
        else:
            self.dispatcher = action_dispatcher

        # === < Phase 7 > ===
        # Explicitly assign config-driven autonomy & whitelist (never hardcoded)
        self.dispatcher.autonomy = autonomy_mode
        self.dispatcher.whitelist = whitelist or []
        # === < / Phase 7 > ===

        # Register implementations
        from ..plugins.file_ops import file_read, file_write
        self.dispatcher.register("file_read", file_read)
        self.dispatcher.register("file_write", file_write)
        self.dispatcher.register("request_intervention", request_intervention)
        
        # === < Phase 7 > ===
        from ..plugins.browser_ops import (
            browser_navigate, browser_fill, browser_click_text, browser_wait_for_element,
            browser_screenshot, browser_trigger_download, browser_fetch_resource
        )
        self.dispatcher.register("browser_navigate", browser_navigate)
        self.dispatcher.register("browser_fill", browser_fill)
        self.dispatcher.register("browser_click_text", browser_click_text)
        self.dispatcher.register("browser_wait_for_element", browser_wait_for_element)
        self.dispatcher.register("browser_screenshot", browser_screenshot)
        self.dispatcher.register("browser_trigger_download", browser_trigger_download)
        self.dispatcher.register("browser_fetch_resource", browser_fetch_resource)

        # === < Phase 7.1 > ===
        # Register LLM UI tools (orchestrator-only, NOT added to builder)
        from ..plugins.llm_ui_ops import llm_attach_file
        self.dispatcher.register("llm_attach_file", llm_attach_file)
        # Do NOT call self.builder.register_tool() for this
        # === < / Phase 7.1 > ===

        # === < / Phase 7 > ===

        self.expected_schema = {
            "type": "object",
            "properties": {
                "tool_name": {"type": "string"},
                "parameters": {"type": "object"},
                "goal_status": {"type": "string", "enum": ["in_progress", "completed", "blocked"]}
            },
            "required": ["tool_name", "parameters", "goal_status"],
            "additionalProperties": False
        }

    # === < Phase 7 > ===
    # max_steps now defaults to None, reads from config.yaml if not provided
    def run(self, goal_query: str, max_steps: Optional[int] = None) -> dict:
        if max_steps is None:
            try:
                from ..config import Config
                cfg = Config(self.workspace)
                max_steps = cfg.autonomy.global_max_iterations
                logger.debug("Using config-driven max_steps: %d", max_steps)
            except Exception as e:
                max_steps = 10  # Safe fallback matching config.yaml default
                logger.warning("Config load failed for max_steps (%s), using default: %d", e, max_steps)
    # === < / Phase 7 > ===
        
        if not self.llm:
            raise RuntimeError("AgentOrchestrator requires an llm_client.")

        goal_id = f"goal_{uuid.uuid4().hex[:8]}"
        self.state_mgr.create_goal(goal_id, self.project, goal_query, max_steps)
        self.state_mgr.update_goal_status(goal_id, "in_progress")

        last_result = "None"
        history: List[Dict] = []

        for step in range(max_steps):
            prompt = self.builder.build_next_step_prompt(
                goal_query=goal_query, goal_id=goal_id, current_step=step,
                last_result=last_result, context_history=history
            )
            self.state_mgr.log_audit(goal_id, "prompt_sent", prompt, "")

            try:
                raw_response = self.llm(prompt)
                self.state_mgr.log_audit(goal_id, "llm_response", prompt, raw_response[:200])
            except Exception as e:
                self.state_mgr.update_goal_status(goal_id, "blocked")
                return {"goal_id": goal_id, "status": "blocked", "reason": f"LLM Call Failed: {e}"}

            try:
                action = self.validator.parse_and_validate(raw_response, self.expected_schema)
            except ValidationError as e:
                last_result = f"Invalid JSON: {e.message}"
                history.append({"step_index": step, "tool_name": "parse_error", "status": "error", "result": last_result})
                continue

            try:
                result = self.dispatcher.dispatch(action)
            except Exception as e:
                result = {"status": "error", "output": str(e)}

            tool_name = action.get("tool_name", "unknown")
            self.state_mgr.log_step(goal_id, step, tool_name, action.get("parameters", {}), 
                                    result.get("output", ""), rationale="", status=result.get("status", "completed"))
            last_result = result.get("output", "completed")

            if result.get("status") == "intervention_required":
                print(f"\n🛑 INTERVENTION: {last_result}")
                # === < Phase 7 > ===
                logger.error("Intervention triggered: %s", last_result)
                # === < / Phase 7 > ===
                self.state_mgr.update_goal_status(goal_id, "requires_user_confirmation")
                return {"goal_id": goal_id, "status": "requires_user_confirmation", "reason": last_result}

            history.append({"step_index": step, "tool_name": tool_name, "status": result.get("status", "ok"), "result": last_result})

            status = action.get("goal_status")
            if status not in VALID_STATUSES:
                status = "in_progress"

            if status in ("completed", "blocked"):
                self.state_mgr.update_goal_status(goal_id, status)
                return {"goal_id": goal_id, "status": status, "final_result": last_result}

        self.state_mgr.update_goal_status(goal_id, "blocked")
        return {"goal_id": goal_id, "status": "blocked", "reason": "Max steps exceeded"}