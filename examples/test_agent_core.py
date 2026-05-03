#!/usr/bin/env python3
"""Test the core agent components with mock LLM."""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.doit.core import run, StateManager, build_prompt, parse_llm_output, execute_action


def mock_llm_client(prompt: str) -> str:
    """Mock LLM for testing without browser."""
    if "check the current page" in prompt.lower():
        return '{"action": "EXTRACT_TEXT", "parameters": {}, "reason": "Need to see current content"}'
    elif "goal is complete" in prompt.lower():
        return '{"action": "FINISH", "parameters": {}, "reason": "Goal achieved"}'
    else:
        return '{"action": "ALERT_USER", "parameters": {"message": "Working on it"}, "reason": "Processing request"}'


def test_components():
    """Test individual components."""
    print("="*60)
    print("TESTING CORE COMPONENTS")
    print("="*60)
    
    # Test 1: StateManager
    print("\n1. Testing StateManager...")
    workspace = Path("/tmp/test_workspace")
    sm = StateManager(workspace, "test_project")
    state = sm.load()
    state["goal"] = "Test goal"
    sm.save(state)
    loaded = sm.load()
    assert loaded["goal"] == "Test goal"
    print("   ✓ StateManager works")
    
    # Test 2: Prompt Builder
    print("\n2. Testing Prompt Builder...")
    test_state = {
        "goal": "Navigate to example.com",
        "last_action": None,
        "last_result": None,
        "iteration": 1
    }
    prompt = build_prompt(test_state)
    assert "NAVIGATE" in prompt
    assert "example.com" in prompt
    print("   ✓ Prompt Builder works")
    
    # Test 3: JSON Parser
    print("\n3. Testing JSON Parser...")
    test_response = '{"action": "NAVIGATE", "parameters": {"url": "https://example.com"}, "reason": "Testing"}'
    parsed = parse_llm_output(test_response)
    assert parsed["action"] == "NAVIGATE"
    print("   ✓ JSON Parser works")
    
    # Test 4: Action Dispatcher
    print("\n4. Testing Action Dispatcher...")
    test_action = {"action": "ALERT_USER", "parameters": {"message": "Hello"}}
    result = execute_action(test_action)
    assert result["status"] == "alert_sent"
    print("   ✓ Action Dispatcher works")
    
    print("\n✅ All component tests passed!\n")


def test_agent_loop():
    """Test the full agent loop with mock LLM."""
    print("="*60)
    print("TESTING AGENT LOOP (Mock LLM)")
    print("="*60)
    
    workspace = Path("/tmp/test_workspace_loop")
    result = run(
        goal="Test the agent loop",
        project="test_loop",
        workspace_root=workspace,
        llm_client=mock_llm_client,
        max_iterations=3,
        verbose=True
    )
    
    print(f"\nFinal result: {result}")
    
    # Verify state files were created
    state_file = workspace / "projects" / "test_loop" / "state.json"
    history_file = workspace / "projects" / "test_loop" / "history.jsonl"
    
    print(f"\nState file: {state_file.exists()}")
    print(f"History file: {history_file.exists()}")
    
    # Clean up
    import shutil
    if workspace.exists():
        shutil.rmtree(workspace)
    
    print("\n✅ Agent loop test passed!")


if __name__ == "__main__":
    test_components()
    test_agent_loop()