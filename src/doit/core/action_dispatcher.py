# src/doit/core/action_dispatcher.py [MOD v2.3]
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from .security_enforcer import SecurityEnforcer, GateDecision

class ActionDispatcher:
    def __init__(self, workspace_dir: Path, autonomy_mode: int = 0, whitelist: Optional[List[str]] = None):
        self.workspace = workspace_dir
        self.autonomy = autonomy_mode
        self.whitelist = whitelist or []
        self.enforcer = SecurityEnforcer()
        self._tools: Dict[str, Callable] = {}

    def register(self, name: str, func: Callable):
        self._tools[name] = func

    def dispatch(self, action: Dict[str, Any]) -> Dict[str, Any]:
        # 1. Security Evaluation (Pre-Execution)
        sec_result = self.enforcer.evaluate(action, self.autonomy, self.workspace, self.whitelist)
        decision = sec_result["decision"]

        if decision == GateDecision.BLOCKED:
            print(f"\n🚫 BLOCKED: {sec_result['reason']}")
            return {"status": "error", "output": f"Security Gate Blocked: {sec_result['reason']}"}

        if decision == GateDecision.INTERVENTION_NEEDED:
            return self._handle_3_choice(action, sec_result)

        if decision == GateDecision.CONFIRM_NEEDED:
            if not self._confirm(f"🔒 {sec_result['reason']} Proceed? (y/n): "):
                return {"status": "blocked", "output": "User declined action."}

        # 2. Execution
        tool_name = action.get("tool_name")
        if tool_name in self._tools:
            try:
                params = action.get("parameters", {})
                return self._tools[tool_name](params, workspace=self.workspace)
            except Exception as e:
                return {"status": "error", "output": f"Execution failed: {str(e)}"}
        return {"status": "error", "output": f"Tool '{tool_name}' not registered."}

    def _confirm(self, prompt: str) -> bool:
        try:
            choice = input(prompt).strip().lower()
            return choice in ['y', 'yes']
        except (EOFError, KeyboardInterrupt):
            print("\n⛔ Interrupted. Treating as 'No'.")
            return False

    def _handle_3_choice(self, action: Dict, sec_result: Dict) -> Dict:
        print("\n" + "="*60)
        print("🚨 CRITICAL SAFETY GATE: Destructive command blocked")
        print(f"Action: {action['tool_name']} {action['parameters'].get('command', '')}")
        print(f"Risk: Irreversible data loss")
        print("\nChoose:")
        print("1. Deny & Abort Goal (status: blocked)")
        print("2. Deny & Continue (skip this step, log warning)")
        print("3. Confirm you manually executed it (proceed as success)")
        try:
            choice = input("Choice (1/2/3): ").strip()
        except (EOFError, KeyboardInterrupt):
            choice = "1"

        if choice == "1": return {"status": "error", "output": "Aborted by user."}
        elif choice == "2": return {"status": "skipped", "output": "Skipped per user request."}
        elif choice == "3": return {"status": "ok", "output": "Manually executed by user. Proceeding."}
        return {"status": "blocked", "output": "Invalid choice."}