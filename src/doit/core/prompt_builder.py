# src/doit/core/prompt_builder.py [v2.1]
import json
from typing import Dict, List, Optional

class SingleLinePromptBuilder:
    SYSTEM_PROMPT = (
        "||SYS|| You propose actions. An orchestrator executes them. "
        "Output ONLY strict single-line JSON matching ||SCHEMA||. "
        "Use ONLY tools listed in ||TOOLS||. "
        "Set goal_status to 'completed' ONLY when the query is fully satisfied. "
        "If a tool fails, adapt your next action. NO markdown, NO extra fields. ||SYS||"
    )
    REINFORCEMENT_INTERVAL = 4  # Re-inject SYS prompt every N turns

    def __init__(self):
        self._tools: Dict[str, Dict] = {}

    def register_tool(self, name: str, description: str, input_schema: Optional[Dict] = None):
        self._tools[name] = {"desc": description}

    def _clean(self, text: str) -> str:
        # Strip newlines, collapse whitespace, escape delimiter collisions
        return " ".join(text.split()).replace("||", "\\|\\|").replace("[", "\\[").replace("]", "\\]")

    def build_next_step_prompt(self, goal_query: str, goal_id: str, current_step: int, last_result: str, context_history: List[Dict]) -> str:
        # 1. Format last_result with explicit delimiters
        clean_last = self._clean(last_result or "none")
        last_str = f"last:[RESULT]{clean_last}[/RESULT]"

        # 2. Build history
        history_str = ""
        if context_history:
            entries = []
            for h in context_history:
                step = h.get("step_index", "?")
                tool = h.get("tool_name", "unknown")
                res = self._clean(h.get("result", "none"))
                entries.append(f"S{step}:{tool}->ok:[RESULT]{res}[/RESULT]")
            history_str = " ||HIST|| " + " | ".join(entries)

        # 3. Build tools
        tool_str = " ||TOOLS|| " + " | ".join(f"{n}: {t['desc']}" for n, t in self._tools.items())

        # 4. Minimal 3-field schema
        schema_str = ' ||SCHEMA|| {"type":"object","properties":{"tool_name":{"type":"string"},"parameters":{"type":"object"},"goal_status":{"type":"string","enum":["in_progress","completed","blocked"]}},"required":["tool_name","parameters","goal_status"],"additionalProperties":false}'

        # 5. Assemble parts
        parts = [
            f"||CTX|| query:{self._clean(goal_query)} step:{current_step} {last_str}{history_str}",
            tool_str,
            schema_str,
            "||USER|| Return NEXT ACTION as single-line JSON ONLY."
        ]

        # 6. Conditional system prompt injection (Turn 0 + reinforcement)
        if current_step == 0 or (current_step % self.REINFORCEMENT_INTERVAL == 0):
            parts.insert(0, self.SYSTEM_PROMPT)

        return " ".join(parts)

    def build_plan_prompt(self, goal_query: str) -> str:
        return " ".join([
            self.SYSTEM_PROMPT,
            f"||GOAL|| {self._clean(goal_query)}",
            '||SCHEMA|| {"type":"object","properties":{"plan_steps":{"type":"array","items":{"type":"object","properties":{"step":{"type":"integer"},"tool_name":{"type":"string"},"description":{"type":"string"}}}}},"required":["plan_steps"]}',
            "||USER|| Return plan as single-line JSON ONLY."
        ])