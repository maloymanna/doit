#!/usr/bin/env python3
"""Regression test: Verifies Phase 5 security gates + tool registration + state validation."""
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from doit.core.action_dispatcher import ActionDispatcher
from doit.core.state_manager import SQLiteStateManager, VALID_STATUSES
from doit.core.prompt_builder import SingleLinePromptBuilder

# =============================================================================
# ESTABLISHED CONFIGURATION PATTERN (matches CLI --workspace argument)
# =============================================================================
WORKSPACE = Path("~/Documents/02-learn/dev/doit-workspace").expanduser()
URL = "https://www.usegpt.myorg"
PROJECT = "auto-sso-test"
# =============================================================================

WORKSPACE.mkdir(parents=True, exist_ok=True)

def _stub_tool(params, project_dir, **ctx):
    """Minimal stub that returns success for any tool call."""
    return {"status": "ok", "output": f"Stub executed: {params}"}

def run_test(name, fn):
    try:
        fn()
        print(f"✅ [{name}]")
        return True
    except Exception as e:
        print(f"❌ [{name}] {e}")
        return False

def test_tool_injection():
    builder = SingleLinePromptBuilder()
    builder.register_tool("file_read", "Reads file", {})
    builder.register_tool("file_write", "Writes file", {})
    prompt = builder.build_next_step_prompt("test", "g1", 0, "none", [])
    assert "||TOOLS||" in prompt
    assert "file_read:" in prompt and "file_write:" in prompt
    assert "request_intervention:" not in prompt
    assert "\n" not in prompt

def test_security_gates():
    # Create a dummy project dir for the test to match dispatcher signature
    project_dir = WORKSPACE / "projects" / "reg_test_project"
    project_dir.mkdir(parents=True, exist_ok=True)
    
    # Update constructor call to match ActionDispatcher v2.5 signature (workspace, project_dir)
    dispatcher = ActionDispatcher(WORKSPACE, project_dir, autonomy_mode=0)
    dispatcher.register("file_read", _stub_tool)
    dispatcher.register("file_write", _stub_tool)
    
    with patch("builtins.input", return_value="y"):
        res = dispatcher.dispatch({"tool_name":"file_write","parameters":{"path":"new.txt","content":"x"}})
        assert res["status"] == "ok"
        
    with patch("builtins.input", return_value="n"):
        res = dispatcher.dispatch({"tool_name":"file_write","parameters":{"path":"new2.txt","content":"x"}})
        assert res["status"] == "blocked"

def test_state_validation():
    mgr = SQLiteStateManager(WORKSPACE)
    mgr.create_goal("reg_01", "test", "validate", 3)
    mgr.update_goal_status("reg_01", "in_progress")
    mgr.update_goal_status("reg_01", "requires_user_confirmation")
    try:
        mgr.update_goal_status("reg_01", "INVALID_STATUS")
        raise AssertionError("Should have raised ValueError")
    except ValueError:
        pass

if __name__ == "__main__":
    print("="*60)
    print("PHASE 5 REGRESSION TEST")
    print("="*60)
    print(f"Workspace: {WORKSPACE}")
    print(f"URL: {URL}")
    print(f"Project: {PROJECT}")
    print()
    results = [
        run_test("Tool Injection & Prompt Generation", test_tool_injection),
        run_test("Security Gates (Confirm/Block)", test_security_gates),
        run_test("State Manager Validation", test_state_validation),
    ]
    print(f"\n{'✅ ALL PASSED' if all(results) else '⚠️  SOME FAILED'}")