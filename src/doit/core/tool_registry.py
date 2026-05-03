# src/doit/core/tool_registry.py [NEW v1]
from typing import Dict, Any, Callable, Optional
import jsonschema

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, Dict[str, Any]] = {}

    def register(self, name: str, description: str, input_schema: Dict[str, Any], handler: Callable):
        self._tools[name] = {
            "name": name,
            "description": description,
            "input_schema": input_schema,
            "handler": handler
        }

    def get_tool(self, name: str) -> Optional[Dict[str, Any]]:
        return self._tools.get(name)

    def list_tools_for_prompt(self) -> str:
        """Generates single-line string for PromptBuilder injection."""
        parts = []
        for tool in self._tools.values():
            desc = tool["description"].replace("\n", " ").strip()
            params = ", ".join(tool["input_schema"].get("properties", {}).keys())
            parts.append(f"{tool['name']}({params}): {desc}")
        return " | ".join(parts)

    def validate_params(self, tool_name: str, params: Dict[str, Any]) -> bool:
        tool = self.get_tool(tool_name)
        if not tool:
            raise ValueError(f"Unknown tool: {tool_name}")
        jsonschema.validate(instance=params, schema=tool["input_schema"])
        return True

    def execute(self, tool_name: str, params: Dict[str, Any], **context) -> Dict[str, Any]:
        tool = self.get_tool(tool_name)
        if not tool:
            raise ValueError(f"Unknown tool: {tool_name}")
        # Execute with context (e.g., Playwright page)
        return tool["handler"](params, **context)