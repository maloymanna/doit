# src/doit/core/agent_orchestrator.py [v4.5]
import uuid
import logging
from pathlib import Path
from typing import Callable, Optional, Any, Dict, List

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
                 llm_client: Optional[Callable[[str], str]] = None,
                 action_dispatcher: Optional[Any] = None,
                 prompt_builder: Optional[SingleLinePromptBuilder] = None,
                 validator: Optional[JSONValidator] = None,
                 autonomy_mode: int = 0,
                 whitelist: Optional[List[str]] = None):
        self.workspace = workspace_dir
        self.llm = llm_client
        self.builder = prompt_builder or SingleLinePromptBuilder()
        self.validator = validator or JSONValidator()
        self.state_mgr = SQLiteStateManager(workspace_dir)

        from ..plugins.file_ops import FILE_READ_SCHEMA, FILE_WRITE_SCHEMA, file_read, file_write
        self.builder.register_tool("file_read", "Reads content from a local file path")
        self.builder.register_tool("file_write", "Writes content to a local file")

        if action_dispatcher is None:
            self.dispatcher = ActionDispatcher(workspace_dir, autonomy_mode=autonomy_mode, whitelist=whitelist)
        else:
            self.dispatcher = action_dispatcher

        self.dispatcher.register("file_read", file_read)
        self.dispatcher.register("file_write", file_write)
        self.builder.register_tool("request_intervention", "Halts loop for user clarification")
        self.dispatcher.register("request_intervention", request_intervention)

        # Matches v2.0 prompt builder schema
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

    def run(self, goal_query: str, project: str, max_steps: int = 5) -> dict:
        if not self.llm:
            raise RuntimeError("AgentOrchestrator requires an llm_client.")

        goal_id = f"goal_{uuid.uuid4().hex[:8]}"
        self.state_mgr.create_goal(goal_id, project, goal_query, max_steps)
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