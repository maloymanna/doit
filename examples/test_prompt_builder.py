#!/usr/bin/env python3
"""Test Prompt Builder - uses state structure from StateManager."""

import json
import tempfile
from pathlib import Path
from doit.core.state_manager import StateManager
from doit.core.prompt_builder import build_prompt, build_simple_prompt


def test_prompt_builder():
    print("\n" + "="*60)
    print("TEST 2: Prompt Builder")
    print("="*60)
    
    # Test 2.1: Build prompt with empty state
    print("\n2.1 Testing with empty state...")
    empty_state = {
        "goal": "",
        "last_action": None,
        "last_result": None,
        "iteration": 0,
        "conversation_history": []
    }
    
    prompt = build_prompt(empty_state)
    
    assert isinstance(prompt, str)
    assert len(prompt) > 100
    assert "CURRENT GOAL" in prompt
    assert "ITERATION" in prompt
    assert "AVAILABLE ACTIONS" in prompt
    print("   ✓ Empty state prompt generated")
    
    # Test 2.2: Build prompt with goal and iteration
    print("\n2.2 Testing with goal and iteration...")
    goal_state = {
        "goal": "Navigate to example.com and extract the title",
        "last_action": None,
        "last_result": None,
        "iteration": 3,
        "conversation_history": []
    }
    
    prompt = build_prompt(goal_state)
    
    assert "Navigate to example.com" in prompt
    assert "ITERATION\n3" in prompt or "ITERATION\n\n3" in prompt
    print("   ✓ Goal and iteration included")
    
    # Test 2.3: Build prompt with last action and result
    print("\n2.3 Testing with last action and result...")
    action_state = {
        "goal": "Test goal",
        "last_action": {"action": "NAVIGATE", "parameters": {"url": "https://example.com"}},
        "last_result": {"status": "navigated", "url": "https://example.com"},
        "iteration": 1,
        "conversation_history": []
    }
    
    prompt = build_prompt(action_state)
    
    assert "NAVIGATE" in prompt
    assert "https://example.com" in prompt
    assert "navigated" in prompt
    print("   ✓ Last action and result included")
    
    # Test 2.4: Build prompt with conversation history
    print("\n2.4 Testing with conversation history...")
    history_state = {
        "goal": "Test goal",
        "last_action": None,
        "last_result": None,
        "iteration": 2,
        "conversation_history": [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
            {"role": "user", "content": "Help me"}
        ]
    }
    
    prompt = build_prompt(history_state)
    
    assert "CONVERSATION HISTORY" in prompt
    assert "USER: Hello" in prompt or "user: Hello" in prompt
    assert "ASSISTANT: Hi there" in prompt or "assistant: Hi there" in prompt
    print("   ✓ Conversation history included")
    
    # Test 2.5: Simple prompt builder
    print("\n2.5 Testing simple prompt builder...")
    simple = build_simple_prompt("Test goal", "Additional context")
    
    assert "Test goal" in simple
    assert "Additional context" in simple
    assert "NAVIGATE" in simple
    assert "JSON" in simple
    print("   ✓ Simple prompt builder works")
    
    print("\n✅ Prompt Builder tests passed!\n")


def test_prompt_with_real_state_manager():
    """Test prompt builder using actual StateManager saved state."""
    print("\n" + "="*60)
    print("TEST 2b: Prompt Builder with Real StateManager")
    print("="*60)
    
    temp_dir = tempfile.mkdtemp()
    workspace = Path(temp_dir)
    
    try:
        # Create real state via StateManager
        sm = StateManager(workspace, "prompt_test")
        state = sm.load()
        state["goal"] = "Extract the main heading from the current page"
        state["iteration"] = 2
        state["last_action"] = {"action": "NAVIGATE", "parameters": {"url": "https://example.com"}}
        state["last_result"] = {"status": "navigated", "page": "example.com"}
        sm.save(state)
        
        # Build prompt from the saved state
        loaded_state = sm.load()
        prompt = build_prompt(loaded_state)
        
        # Verify prompt contains the state data
        assert "Extract the main heading" in prompt
        assert "NAVIGATE" in prompt
        assert "example.com" in prompt
        assert "navigated" in prompt
        
        print("✓ Prompt builder works with StateManager data")
        
    finally:
        import shutil
        shutil.rmtree(temp_dir)
    
    print("\n✅ Real StateManager integration test passed!\n")


if __name__ == "__main__":
    test_prompt_builder()
    test_prompt_with_real_state_manager()