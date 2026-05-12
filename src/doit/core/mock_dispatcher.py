# src/doit/core/mock_dispatcher.py [MOD v1.2]
from typing import Dict, Any, List
from doit.utils.session_logger import logger

class MockActionDispatcher:
    def __init__(self):
        self.execution_log: List[Dict[str, Any]] = []

    def dispatch(self, action: Dict[str, Any]) -> Dict[str, Any]:
        tool = action.get("tool_name", "unknown")
        params = action.get("parameters", {})
        path = params.get("path", params.get("file_path", ""))

        self.execution_log.append({"tool": tool, "params": params})
        logger.__init__("🤖 Tool: %s | Params: %s", tool, params)

        # ✅ Context-aware mock responses to break the loop
        if tool == "file_read":
            if "config.yaml" in path:
                # Return content that actually contains the key the goal asks for
                return {"status": "ok", "output": "browser:\n  default_model: GPT-5.1\n  timeout_ms: 60000\nlogging:\n  level: INFO"}
            return {"status": "ok", "output": f"Content of '{path}': [Simulated file data]"}
            
        elif tool == "file_write":
            return {"status": "ok", "output": f"Successfully wrote {len(params.get('content', ''))} chars to '{path}'."}
            
        return {"status": "ok", "output": "Operation completed."}