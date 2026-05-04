# src/doit/core/agent_orchestrator.py [MOD v3]
import uuid
import logging
import sys
from pathlib import Path
from typing import Callable, Optional, Any, Dict, Set

from .state_manager import SQLiteStateManager
from .prompt_builder import SingleLinePromptBuilder
from .json_validator import JSONValidator, ValidationError

logger = logging.getLogger(__name__)
DESTRUCTIVE_TOOLS = {"file_write", "file_delete", "browser_navigate"}  # Expand as needed

class AgentOrchestrator:
    def __init__(self, 
                 workspace_dir: Path,
                 llm_client: Optional[Callable[[str], str]] = None,
                 action_dispatcher: Optional[Any] = None,
                 page: Optional[Any] = None,
                 prompt_builder: Optional[SingleLinePromptBuilder] = None,
                 validator: Optional[JSONValidator] = None,
                 autonomy_mode: int = 0,
                 dry_run: bool = False):
        self.workspace = workspace_dir
        self.state_mgr = SQLiteStateManager(workspace_dir)
        self.llm = llm_client
        self.builder = prompt_builder or SingleLinePromptBuilder()
        self.validator = validator or JSONValidator()
        self.autonomy = autonomy_mode
        self.dry_run = dry_run
        
        # Wire Dispatcher
        if action_dispatcher is None:
            from .action_dispatcher import ActionDispatcher
            self.dispatcher = ActionDispatcher(workspace_dir, page=page)
        else:
            self.dispatcher = action_dispatcher

        # Register high-level tools
        from ..plugins.high_level import excel_diff, EXCEL_DIFF_SCHEMA, screenshot_save, SCREENSHOT_SCHEMA, draft_email, EMAIL_DRAFT_SCHEMA
        self.dispatcher.registry.register("excel_diff", "Compares two reports and saves diff.", EXCEL_DIFF_SCHEMA, excel_diff)
        self.dispatcher.registry.register("screenshot_save", "Captures browser screenshot.", SCREENSHOT_SCHEMA, screenshot_save)
        self.dispatcher.registry.register("draft_email", "Generates email draft from template.", EMAIL_DRAFT_SCHEMA, draft_email)
        
        # Update prompt builder with all tools
        for name, t in self.dispatcher.registry._tools.items():
            self.builder.register_tool(name, t["description"], t["input_schema"])

        self.next_action_schema = {
            "type": "object",
            "properties": {
                "tool_name": {"type": "string"},
                "parameters": {"type": "object"},
                "description": {"type": "string"},
                "goal_status": {"type": "string", "enum": ["in_progress", "completed", "blocked", "requires_user_confirmation"]},
                "rationale": {"type": "string"},
                "fallback_instruction": {"type": "string"}
            },
            "required": ["tool_name", "parameters", "description", "goal_status", "rationale"],
            "additionalProperties": False
        }

    def _require_confirmation(self, action: Dict) -> bool:
        if self.autonomy == 2: return False
        if self.autonomy == 0: return True
        return action.get("tool_name") in DESTRUCTIVE_TOOLS

    def run(self, goal_query: str, project: str, max_steps: int = 15) -> dict:
        goal_id = f"goal_{uuid.uuid4().hex[:8]}"
        logger.info(f"[ORC] Starting goal {goal_id} | DryRun:{self.dry_run} | Autonomy:{self.autonomy}")
        
        self.state_mgr.create_goal(goal_id, project, goal_query, max_steps)
        self.state_mgr.update_goal_status(goal_id, "in_progress")

        last_result = "None"
        current_step = 0

        while current_step < max_steps:
            history = self.state_mgr.get_recent_context(goal_id, limit=5)
            prompt = self.builder.build_next_step_prompt(goal_id, current_step, last_result, history)
            self.state_mgr.log_audit(goal_id, "prompt_sent", prompt, "")

            raw_response = self.llm(prompt) if self.llm else '{"tool_name":"excel_diff","parameters":{"file1":"a.csv","file2":"b.csv","output":"diff.txt"},"description":"test","goal_status":"completed","rationale":"mock"}'
            self.state_mgr.log_audit(goal_id, "llm_response", prompt, raw_response[:200])

            try:
                action = self.validator.parse_and_validate(raw_response, self.next_action_schema)
            except ValidationError as e:
                logger.warning(f"[ORC] JSON validation failed: {e.message}. Retrying...")
                last_result = f"PARSE_ERROR: {e.message}"
                continue

            # Confirmation Gate
            if self._require_confirmation(action):
                print(f"\n🔒 Require approval for: {action['tool_name']} | {action.get('description')}")
                if input("Proceed? (y/N): ").strip().lower() != "y":
                    return {"goal_id": goal_id, "status": "blocked", "reason": "User declined"}

            logger.info(f"[ORC] Step {current_step} -> Tool: {action['tool_name']}")
            
            if self.dry_run:
                result = {"status": "ok", "output": f"[DRY-RUN] Would execute {action['tool_name']}"}
            else:
                try:
                    result = self.dispatcher.dispatch(action)
                except Exception as e:
                    result = {"status": "error", "output": str(e)}
                    
            self.state_mgr.log_step(goal_id, current_step, action['tool_name'], action['parameters'], result.get("output", ""), action["rationale"])
            last_result = result.get("output", "completed")
            goal_status = action.get("goal_status", "in_progress")

            if goal_status in ("completed", "blocked", "requires_user_confirmation"):
                self.state_mgr.update_goal_status(goal_id, goal_status)
                return {"goal_id": goal_id, "status": goal_status, "final_result": last_result}

            current_step += 1

        self.state_mgr.update_goal_status(goal_id, "blocked", step=max_steps)
        return {"goal_id": goal_id, "status": "blocked", "reason": "Max steps exceeded"}