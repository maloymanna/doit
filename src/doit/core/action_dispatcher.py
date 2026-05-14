# src/doit/core/action_dispatcher.py [v2.7]
import sys
# === < Phase 7 > ===
import asyncio
# === < / Phase 7 > ===
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from .security_enforcer import SecurityEnforcer, GateDecision
from doit.utils.session_logger import logger

# === < Phase 7 > ===
def _safe_run_async(loop: asyncio.AbstractEventLoop, coro):
    """Execute async coroutine safely whether loop is running or not."""
    if loop.is_running():
        future = asyncio.run_coroutine_threadsafe(coro, loop)
        return future.result()
    return loop.run_until_complete(coro)
# === < / Phase 7 > ===

class ActionDispatcher:
    # === < Phase 7 > ===
    # Signature aligned with v2.6 + Phase 7 async/controller injection
    def __init__(self, workspace_dir: Path, project_dir: Path, 
                 controller=None, loop=None):
    # === < / Phase 7 > ===
        self.workspace = workspace_dir
        self.project_dir = project_dir
        # === < Phase 7 > ===
        self.controller = controller          # Optional: BrowserController for browser_ops
        self.loop = loop                      # Optional: asyncio loop for async bridging
        # === < / Phase 7 > ===
        
        # Defaults (explicitly overridden by AgentOrchestrator from config.yaml)
        self.autonomy = 0
        self.whitelist = []
        
        self.enforcer = SecurityEnforcer()
        self._tools: Dict[str, Callable] = {}

    def register(self, name: str, func: Callable):
        self._tools[name] = func

    def dispatch(self, action: Dict[str, Any]) -> Dict[str, Any]:
        sec_result = self.enforcer.evaluate(action, self.autonomy, self.project_dir, self.whitelist)
        decision = sec_result["decision"]
        
        logger.debug("Security gate: tool=%s, mode=%d, decision=%s, reason=%s", 
                     action.get("tool_name"), self.autonomy, decision.name, sec_result.get("reason", ""))

        if decision == GateDecision.BLOCKED:
            print(f"\n🚫 BLOCKED: {sec_result['reason']}")
            logger.warning("Security gate blocked: %s", sec_result['reason'])
            return {"status": "error", "output": f"Security Gate Blocked: {sec_result['reason']}"}

        if decision == GateDecision.INTERVENTION_NEEDED:
            return self._handle_3_choice(action, sec_result)

        if decision == GateDecision.CONFIRM_NEEDED:
            if not self._confirm(f"🔒 {sec_result['reason']} Proceed? (y/n): "):
                return {"status": "blocked", "output": "User declined action."}

        tool_name = action.get("tool_name")
        if tool_name in self._tools:
            try:
                params = action.get("parameters", {})
                # === < Phase 7 > ===
                ctx = {"controller": self.controller, "loop": self.loop, "project_dir": self.project_dir}
                # === < / Phase 7 > ===
                return self._tools[tool_name](params, **ctx)
            except Exception as e:
                logger.error("Tool execution failed: %s", e, exc_info=False)
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
        cmd = action['parameters'].get('command', '')
        logger.warning("3-choice safety protocol: %s %s", action['tool_name'], cmd)
        
        print("\n" + "="*60)
        print("🚨 CRITICAL SAFETY GATE: Destructive command blocked")
        print(f"Action: {action['tool_name']} {cmd}")
        print(f"Risk: Irreversible data loss")
        print("\nChoose:")
        print("1. Deny & Abort Goal (status: blocked)")
        print("2. Deny & Continue (skip this step, log warning)")
        print("3. Confirm you manually executed it (proceed as success)")
        try:
            choice = input("Choice (1/2/3): ").strip()
        except (EOFError, KeyboardInterrupt):
            choice = "1"

        if choice == "1": 
            logger.info("User chose: Deny & Abort")
            return {"status": "error", "output": "Aborted by user."}
        elif choice == "2": 
            logger.info("User chose: Deny & Continue")
            return {"status": "skipped", "output": "Skipped per user request."}
        elif choice == "3": 
            logger.info("User chose: Manual execution confirmed")
            return {"status": "ok", "output": "Manually executed by user. Proceeding."}
        logger.warning("Invalid 3-choice input: %s", choice)
        return {"status": "blocked", "output": "Invalid choice."}