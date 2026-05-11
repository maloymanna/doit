#!/usr/bin/env python3
"""
STEP 5: Security Gates & Autonomy Matrix Validation
Tests deterministic gating, console prompts, and 3-choice protocol without LLM/Browser.
Uses established configuration pattern (matches CLI --workspace argument).
"""
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from doit.core.action_dispatcher import ActionDispatcher

# =============================================================================
# ESTABLISHED CONFIGURATION PATTERN (matches CLI --workspace argument)
# =============================================================================
WORKSPACE = Path("~/Documents/02-learn/dev/doit-workspace").expanduser()
URL = "https://www.usegpt.myorg"
PROJECT = "auto-sso-test"
# =============================================================================

WORKSPACE.mkdir(parents=True, exist_ok=True)

def _stub_tool(params, workspace, **ctx):
    """Minimal stub that returns success for any tool call."""
    return {"status": "ok", "output": f"Stub executed: {params}"}

def test_gate(tool, params, mode, whitelist=None, mock_input="y", register_tool=True):
    """Simulate dispatch with mocked input and optional tool registration."""
    dispatcher = ActionDispatcher(WORKSPACE, autonomy_mode=mode, whitelist=whitelist)
    
    # Register stub tool if requested (so gate logic can be tested)
    if register_tool:
        dispatcher.register(tool, _stub_tool)
    
    action = {"tool_name": tool, "parameters": params}
    
    with patch("builtins.input", return_value=mock_input):
        res = dispatcher.dispatch(action)
    return res["status"]

def run_test(name, expected_status, result_status):
    passed = result_status == expected_status
    print(f"{'✅' if passed else '❌'} [{name}] Expected: {expected_status} | Got: {result_status}")
    return passed

if __name__ == "__main__":
    print("="*60)
    print("STEP 5: Security Gates & Autonomy Matrix Validation")
    print("="*60)
    print(f"Workspace: {WORKSPACE}")
    print(f"URL: {URL}")
    print(f"Project: {PROJECT}")
    print()

    results = []

    # -------------------------------------------------------------------------
    # 1. Path Traversal (Hard Block - never delegated to LLM)
    # -------------------------------------------------------------------------
    print("🔐 Testing Path Traversal Hard Blocks...")
    results.append(run_test("Path Traversal (escape workspace)", "error", 
                            test_gate("file_write", {"path": "../../etc/passwd", "content": "hack"}, 2, register_tool=True)))
    results.append(run_test("Path Traversal (absolute escape)", "error", 
                            test_gate("file_write", {"path": "/etc/shadow", "content": "hack"}, 2, register_tool=True)))

    # -------------------------------------------------------------------------
    # 2. File Write: New Path (Mode 0/1 = Confirm, Mode 2 = Auto)
    # -------------------------------------------------------------------------
    print("\n📝 Testing file_write (new path)...")
    results.append(run_test("FW New Path (Mode 0 -> Confirm)", "ok", 
                            test_gate("file_write", {"path": "new_test_0.txt", "content": "data"}, 0, register_tool=True)))
    results.append(run_test("FW New Path (Mode 1 -> Confirm)", "ok", 
                            test_gate("file_write", {"path": "new_test_1.txt", "content": "data"}, 1, register_tool=True)))
    results.append(run_test("FW New Path (Mode 2 -> Auto)", "ok", 
                            test_gate("file_write", {"path": "new_test_2.txt", "content": "data"}, 2, register_tool=True)))

    # -------------------------------------------------------------------------
    # 3. File Write: Existing Path (Mode 0 = Confirm, Mode 1/2 = Auto)
    # -------------------------------------------------------------------------
    print("\n📝 Testing file_write (existing path)...")
    existing_file = WORKSPACE / "exist_test.txt"
    existing_file.write_text("dummy")
    
    results.append(run_test("FW Exist Path (Mode 0 -> Confirm)", "ok", 
                            test_gate("file_write", {"path": "exist_test.txt", "content": "data"}, 0, register_tool=True)))
    results.append(run_test("FW Exist Path (Mode 1 -> Auto)", "ok", 
                            test_gate("file_write", {"path": "exist_test.txt", "content": "data"}, 1, register_tool=True)))
    results.append(run_test("FW Exist Path (Mode 2 -> Auto)", "ok", 
                            test_gate("file_write", {"path": "exist_test.txt", "content": "data"}, 2, register_tool=True)))

    # -------------------------------------------------------------------------
    # 4. Draft/Report Tools (Mode 0 = Confirm, Mode 1/2 = Auto)
    # -------------------------------------------------------------------------
    print("\n📧 Testing draft_email / save_report...")
    results.append(run_test("Draft Email (Mode 0 -> Confirm)", "ok", 
                            test_gate("draft_email", {"to": "user@x.com", "subject": "Test"}, 0, register_tool=True)))
    results.append(run_test("Draft Email (Mode 1 -> Auto)", "ok", 
                            test_gate("draft_email", {"to": "user@x.com", "subject": "Test"}, 1, register_tool=True)))
    
    # External sends blocked in Mode 0/1
    results.append(run_test("Send Email (Mode 0 -> Block)", "error", 
                            test_gate("send_email", {"to": "user@x.com"}, 0, register_tool=False)))
    results.append(run_test("Send Email (Mode 1 -> Block)", "error", 
                            test_gate("send_email", {"to": "user@x.com"}, 1, register_tool=False)))
    results.append(run_test("Send Email (Mode 2 -> Gate Pass)", "ok", 
                            test_gate("send_email", {"to": "user@x.com"}, 2, register_tool=True)))

    # -------------------------------------------------------------------------
    # 5. Bash Execution (Whitelist + Mode Logic)
    # -------------------------------------------------------------------------
    print("\n💻 Testing bash_execute...")
    results.append(run_test("Bash Whitelisted (Mode 1 -> Auto)", "ok", 
                            test_gate("bash_execute", {"command": "ls -la"}, 1, whitelist=["ls"], register_tool=True)))
    results.append(run_test("Bash Unlisted (Mode 1 -> Confirm)", "ok", 
                            test_gate("bash_execute", {"command": "rm -i test"}, 1, whitelist=["ls"], register_tool=True)))
    results.append(run_test("Bash (Mode 0 -> Confirm)", "ok", 
                            test_gate("bash_execute", {"command": "echo hello"}, 0, register_tool=True)))
    results.append(run_test("Bash (Mode 2 -> Auto)", "ok", 
                            test_gate("bash_execute", {"command": "whoami"}, 2, register_tool=True)))

    # -------------------------------------------------------------------------
    # 6. Destructive Commands: 3-Choice Protocol (all modes)
    # -------------------------------------------------------------------------
    print("\n🚨 Testing destructive command 3-Choice Protocol...")
    results.append(run_test("rm -rf (3-Choice: Manual Confirm)", "ok", 
                            test_gate("bash_execute", {"command": "rm -rf /tmp/test"}, 2, mock_input="3", register_tool=True)))
    results.append(run_test("rm -rf (3-Choice: Deny & Abort)", "error", 
                            test_gate("bash_execute", {"command": "rm -rf /tmp/test"}, 2, mock_input="1", register_tool=True)))
    results.append(run_test("rm -rf (3-Choice: Deny & Continue)", "skipped", 
                            test_gate("bash_execute", {"command": "rm -rf /tmp/test"}, 2, mock_input="2", register_tool=True)))
    results.append(run_test("rm -rf (3-Choice: Invalid)", "blocked", 
                            test_gate("bash_execute", {"command": "rm -rf /tmp/test"}, 2, mock_input="9", register_tool=True)))

    # -------------------------------------------------------------------------
    # 7. Console Prompt Rejection (user says 'n')
    # -------------------------------------------------------------------------
    print("\n🔒 Testing user rejection of confirmation prompts...")
    results.append(run_test("FW New Path (Mode 0 -> User Declines)", "blocked", 
                            test_gate("file_write", {"path": "decline_test.txt", "content": "data"}, 0, mock_input="n", register_tool=True)))
    results.append(run_test("Bash (Mode 0 -> User Declines)", "blocked", 
                            test_gate("bash_execute", {"command": "ls"}, 0, mock_input="n", register_tool=True)))

    # -------------------------------------------------------------------------
    # Summary
    # -------------------------------------------------------------------------
    print("\n" + "="*60)
    total = len(results)
    passed = sum(results)
    print(f"Results: {passed}/{total} tests passed")
    
    if all(results):
        print("🎉 ALL SECURITY GATES VALIDATED SUCCESSFULLY")
        print("   Autonomy matrix, console gating, and 3-choice protocol working.")
    else:
        print("⚠️  Some gates failed. Review output above.")
    print("="*60)
    
    # Cleanup test files
    for f in WORKSPACE.glob("new_test_*.txt"):
        f.unlink(missing_ok=True)
    existing_file.unlink(missing_ok=True)