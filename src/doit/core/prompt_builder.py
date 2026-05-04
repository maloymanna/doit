# src/doit/core/prompt_builder.py [MOD v2]
import json
from typing import Dict, List, Optional

class SingleLinePromptBuilder:
    SYSTEM_PROMPT = (
        "||SYS|| You are a deterministic reasoning engine with ZERO execution rights. "
        "You control an external orchestrator that executes actions via a local tool registry. "
        "NEVER assume browser state, file system presence, or network access. "
        "ALWAYS output strict JSON matching the provided schema. NO markdown, NO explanations, NO newlines. "
        "If context is missing or ambiguous, request clarification via the fallback_instruction field. ||SYS||"
    )

    def __init__(self):
        self._tools: Dict[str, Dict] = {}

    def register_tool(self, name: str, description: str, input_schema: Optional[Dict] = None):
        """Register tool for dynamic injection into prompts."""
        self._tools[name] = {"desc": description, "schema": input_schema or {}}

    def _collapse(self, text: str) -> str:
        """Strip all newlines and collapse whitespace to guarantee single-line output."""
        return " ".join(text.split())

    def build_next_step_prompt(self, goal_id: str, current_step: int, last_result: str, context_history: List[Dict]) -> str:
        # Build history string safely
        history_str = " ||HIST|| " + " | ".join(
            f"S{r['step_index']}:{r['tool_name']}->{r['status']}: {self._collapse(r.get('result', '') or '')}"
            for r in context_history
        ) if context_history else ""

        # Build tool registry string
        tool_str = " ||TOOLS|| " + " | ".join(
            f"{name}: {self._collapse(t['desc'])}" for name, t in self._tools.items()
        )

        # Clean, valid JSON schema (no trailing spaces, strictly single-line)
        schema_str = ' ||SCHEMA|| {"type":"object","properties":{"tool_name":{"type":"string"},"parameters":{"type":"object"},"description":{"type":"string"},"goal_status":{"type":"string","enum":["in_progress","completed","blocked","requires_user_confirmation"]},"rationale":{"type":"string"},"fallback_instruction":{"type":"string"}},"required":["tool_name","parameters","description","goal_status","rationale"],"additionalProperties":false}'

        parts = [
            self.SYSTEM_PROMPT,
            f"||CTX|| goal:{goal_id} step:{current_step} last:{self._collapse(last_result or 'none')}{history_str}",
            tool_str,
            schema_str,
            "||USER|| Return NEXT ACTION as single-line JSON ONLY."
        ]
        return self._collapse(" ".join(parts))

    def build_plan_prompt(self, goal_query: str) -> str:
        schema_str = ' ||SCHEMA|| {"type":"object","properties":{"plan_steps":{"type":"array","items":{"type":"object","properties":{"step":{"type":"integer"},"tool_name":{"type":"string"},"description":{"type":"string"}},"required":["step","tool_name","description"]}},"goal_status":{"type":"string"}},"required":["plan_steps","goal_status"],"additionalProperties":false}'
        return self._collapse(
            self.SYSTEM_PROMPT + 
            " ||GOAL|| " + self._collapse(goal_query) + 
            schema_str + 
            " ||REQ|| Return structured plan as single-line JSON ONLY."
        )