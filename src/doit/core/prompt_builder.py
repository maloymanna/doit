# src/doit/core/prompt_builder.py [MOD v1.3]
import json
from typing import Dict, List, Optional

class SingleLinePromptBuilder:
    # Relaxed to prevent LLM paranoia. Removes strict verification mandate.
    # Adds clear guidance on status transitions and intervention tool.
    SYSTEM_PROMPT = (
        "||SYS|| You are a deterministic reasoning engine with ZERO execution rights. "
        "You control an external orchestrator that executes actions via a local tool registry. "
        "NEVER assume browser state, file system presence, or network access. "
        "Default to goal_status: 'in_progress' while working. Set to 'completed' ONLY when the original query is fully satisfied. "
        "If you lack critical information (paths, credentials, ambiguous instructions), use the 'request_intervention' tool to log the gap and halt. DO NOT guess. "
        "ALWAYS output strict JSON matching the provided schema. NO markdown, NO explanations, NO newlines. ||SYS||"
    )

    def __init__(self):
        self._tools: Dict[str, Dict] = {}

    def register_tool(self, name: str, description: str, input_schema: Optional[Dict] = None):
        self._tools[name] = {"desc": description, "schema": input_schema or {}}

    def _collapse(self, text: str) -> str:
        return " ".join(text.split())

    def build_next_step_prompt(self, goal_query: str, goal_id: str, current_step: int, last_result: str, context_history: List[Dict]) -> str:
        history_str = " ||HIST|| " + " | ".join(
            f"S{r['step_index']}:{r['tool_name']}->{r['status']}: {self._collapse(r.get('result', '') or '')}"
            for r in context_history
        ) if context_history else ""

        tool_str = " ||TOOLS|| " + " | ".join(
            f"{name}: {t['desc']}" for name, t in self._tools.items()
        )

        schema_str = ' ||SCHEMA|| {"type":"object","properties":{"tool_name":{"type":"string"},"parameters":{"type":"object"},"description":{"type":"string"},"goal_status":{"type":"string","enum":["in_progress","completed","blocked","requires_user_confirmation"]},"rationale":{"type":"string"},"fallback_instruction":{"type":"string"}},"required":["tool_name","parameters","description","goal_status","rationale"],"additionalProperties":false}'

        parts = [
            self.SYSTEM_PROMPT,
            f"||CTX|| goal:{goal_id} query:{self._collapse(goal_query)} step:{current_step} last:{self._collapse(last_result or 'none')}{history_str}",
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