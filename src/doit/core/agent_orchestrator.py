# src/doit/core/agent_orchestrator.py [MOD v1.2]
import uuid
import logging
from pathlib import Path
from typing import Callable, Optional, Any, Dict

from .state_manager import SQLiteStateManager
from .prompt_builder import SingleLinePromptBuilder
from .json_validator import JSONValidator, ValidationError

logger = logging.getLogger(__name__)

class AgentOrchestrator:
    def __init__(self, 
                 workspace_dir: Path,
                 llm_client: Optional[Callable[[str], str]] = None,
                 action_dispatcher: Optional[Any] = None,
                 prompt_builder: Optional[SingleLinePromptBuilder] = None,
                 validator: Optional[JSONValidator] = None):
        self.workspace = workspace_dir
        self.state_mgr = SQLiteStateManager(workspace_dir)
        self.llm = llm_client
        self.builder = prompt_builder or SingleLinePromptBuilder()
        self.validator = validator or JSONValidator()
        
        # Deferred import + stub fallback for action_dispatcher
        if action_dispatcher is None:
            from .action_dispatcher import ActionDispatcher
            self.dispatcher = ActionDispatcher(workspace_dir)
        else:
            self.dispatcher = action_dispatcher

        # Default schema for next-action validation
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

    def run(self, goal_query: str, project: str, max_steps: int = 15) -> dict:
        goal_id = f"goal_{uuid.uuid4().hex[:8]}"
        logger.info(f"[ORC] Starting goal {goal_id} | Query: {goal_query}")
        
        self.state_mgr.create_goal(goal_id, project, goal_query, max_steps)
        self.state_mgr.update_goal_status(goal_id, "in_progress")

        last_result = "None"
        current_step = 0

        while current_step < max_steps:
            # Build context
            history = self.state_mgr.get_recent_context(goal_id, limit=5)
            prompt = self.builder.build_next_step_prompt(goal_id, current_step, last_result, history)
            
            # Audit
            self.state_mgr.log_audit(goal_id, "prompt_sent", prompt, "")

            # LLM Call (mock if not provided)
            if self.llm is None:
                # Mock response for testing
                raw_response = '{"tool_name": "stub_tool", "parameters": {}, "description": "test", "goal_status": "completed", "rationale": "mock"}'
            else:
                raw_response = self.llm(prompt)
            
            self.state_mgr.log_audit(goal_id, "llm_response", prompt, raw_response[:200])

            # Validate JSON
            try:
                action = self.validator.parse_and_validate(raw_response, self.next_action_schema)
            except ValidationError as e:
                logger.warning(f"[ORC] JSON validation failed: {e.message}. Retrying...")
                self.state_mgr.log_audit(goal_id, "retry_parse", "", e.raw)
                last_result = f"PARSE_ERROR: {e.message}"
                continue

            # Dispatch
            logger.info(f"[ORC] Step {current_step} -> Tool: {action['tool_name']}")
            try:
                result = self.dispatcher.dispatch(action)
                self.state_mgr.log_step(goal_id, current_step, action['tool_name'], action['parameters'], result.get("output", ""), action["rationale"])
            except Exception as e:
                result = {"status": "error", "output": str(e)}
                self.state_mgr.log_step(goal_id, current_step, action['tool_name'], action['parameters'], str(e), action["rationale"], "failed")

            last_result = result.get("output", "completed")
            goal_status = action.get("goal_status", "in_progress")

            if goal_status in ("completed", "blocked", "requires_user_confirmation"):
                self.state_mgr.update_goal_status(goal_id, goal_status)
                logger.info(f"[ORC] Goal {goal_id} status: {goal_status}")
                return {"goal_id": goal_id, "status": goal_status, "final_result": last_result}

            current_step += 1

        self.state_mgr.update_goal_status(goal_id, "blocked", step=max_steps)
        return {"goal_id": goal_id, "status": "blocked", "reason": "Max steps exceeded"}