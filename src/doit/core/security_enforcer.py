# src/doit/core/security_enforcer.py [v1.1]
import re
from pathlib import Path
from typing import Dict, Any, List
from enum import Enum

class GateDecision(Enum):
    ALLOWED = "ALLOWED"
    CONFIRM_NEEDED = "CONFIRM_NEEDED"
    BLOCKED = "BLOCKED"
    INTERVENTION_NEEDED = "INTERVENTION_NEEDED"

class SecurityEnforcer:
    DESTRUCTIVE_PATTERNS = [
        r"rm\s+-rf", r"rmdir\s+/s\s+/q", r"del\s+/s\s+/q", 
        r"Remove-Item\s+-Recurse\s+-Force", r"rd\s+/s\s+/q"
    ]

    @staticmethod
    def evaluate(action: Dict[str, Any], autonomy_mode: int, workspace_root: Path, whitelist: List[str] = None) -> Dict[str, Any]:
        tool = action.get("tool_name", "")
        params = action.get("parameters", {})
        path = params.get("path", params.get("file_path", ""))
        command = params.get("command", "")

        # 1. Path Traversal Check (Hard Block)
        if path:
            try:
                target = (workspace_root / path).resolve()
                workspace_resolved = workspace_root.resolve()
                if not str(target).startswith(str(workspace_resolved)):
                    return {"decision": GateDecision.BLOCKED, "reason": "Path traversal detected outside workspace."}
            except Exception:
                return {"decision": GateDecision.BLOCKED, "reason": "Invalid path format."}

        # 2. Destructive Command Check (3-Choice Protocol)
        for pattern in SecurityEnforcer.DESTRUCTIVE_PATTERNS:
            if command and re.search(pattern, command, re.IGNORECASE):
                return {
                    "decision": GateDecision.INTERVENTION_NEEDED,
                    "reason": f"Destructive command blocked: {command}",
                    "protocol": "3-choice"
                }

        # 3. Autonomy Matrix Evaluation (Context-rich reasons)
        if tool == "file_write":
            if path:
                target = (workspace_root / path).resolve()
                is_new = not target.exists()
                if is_new:
                    if autonomy_mode in [0, 1]:
                        return {"decision": GateDecision.CONFIRM_NEEDED, "reason": f"Write new file: {target}"}
                else:
                    if autonomy_mode == 0:
                        return {"decision": GateDecision.CONFIRM_NEEDED, "reason": f"Overwrite existing file: {target}"}
            return {"decision": GateDecision.ALLOWED}

        elif tool in ["draft_email", "save_report"]:
            if autonomy_mode == 0:
                return {"decision": GateDecision.CONFIRM_NEEDED, "reason": f"{tool} operation requires confirmation"}
            return {"decision": GateDecision.ALLOWED}

        elif tool in ["send_email", "notify_slack"]:
            if autonomy_mode < 2:
                return {"decision": GateDecision.BLOCKED, "reason": "External sends blocked in modes 0 & 1. Use draft tools instead."}
            return {"decision": GateDecision.ALLOWED}

        elif tool == "bash_execute":
            if autonomy_mode == 2:
                return {"decision": GateDecision.ALLOWED}
            cmd_base = command.split()[0] if command else ""
            is_whitelisted = cmd_base in (whitelist or [])
            if autonomy_mode == 1 and is_whitelisted:
                return {"decision": GateDecision.ALLOWED}
            return {"decision": GateDecision.CONFIRM_NEEDED, "reason": f"Execute shell command: {command}"}

        return {"decision": GateDecision.ALLOWED}