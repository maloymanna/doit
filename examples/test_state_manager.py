#!/usr/bin/env python3
"""Test StateManager - no dependencies on other components."""

import json
import shutil
import tempfile
from pathlib import Path
from doit.core.state_manager import StateManager   # Changed from src.doit.core


def test_state_manager():
    print("\n" + "="*60)
    print("TEST 1: StateManager")
    print("="*60)
    
    # Create temporary workspace
    temp_dir = tempfile.mkdtemp()
    workspace = Path(temp_dir)
    project_name = "test_project"
    
    try:
        # Test 1.1: Initialize and load default state
        print("\n1.1 Testing default state...")
        sm = StateManager(workspace, project_name)
        state = sm.load()
        
        assert isinstance(state, dict)
        assert "goal" in state
        assert "last_action" in state
        assert "last_result" in state
        assert "iteration" in state
        assert "conversation_history" in state
        assert state["goal"] == ""
        assert state["last_action"] is None
        assert state["iteration"] == 0
        print("   ✓ Default state created correctly")
        
        # Test 1.2: Save and load state
        print("\n1.2 Testing save and load...")
        state["goal"] = "Test goal"
        state["iteration"] = 5
        state["last_action"] = {"action": "TEST", "parameters": {}}
        state["last_result"] = {"status": "ok"}
        
        sm.save(state)
        loaded_state = sm.load()
        
        assert loaded_state["goal"] == "Test goal"
        assert loaded_state["iteration"] == 5
        assert loaded_state["last_action"]["action"] == "TEST"
        assert loaded_state["last_result"]["status"] == "ok"
        print("   ✓ Save and load working")
        
        # Test 1.3: Append and load history
        print("\n1.3 Testing history...")
        entry1 = {"iteration": 1, "action": "TEST", "result": "ok"}
        entry2 = {"iteration": 2, "action": "FINISH", "result": "done"}
        
        sm.append_history(entry1)
        sm.append_history(entry2)
        
        history = sm.load_history()
        assert len(history) == 2
        assert history[0]["iteration"] == 1
        assert history[1]["iteration"] == 2
        print("   ✓ History working")
        
        # Test 1.4: Project directory created
        print("\n1.4 Testing directory creation...")
        project_dir = workspace / "projects" / project_name
        assert project_dir.exists()
        assert (project_dir / "state.json").exists()
        assert (project_dir / "history.jsonl").exists()
        print("   ✓ Directories created correctly")
        
        # Test 1.5: Clear state
        print("\n1.5 Testing clear...")
        sm.clear()
        assert not (project_dir / "state.json").exists()
        assert not (project_dir / "history.jsonl").exists()
        
        # Reload gives default state
        new_state = sm.load()
        assert new_state["goal"] == ""
        print("   ✓ Clear working")
        
        print("\n✅ StateManager tests passed!\n")
        
    finally:
        # Cleanup
        shutil.rmtree(temp_dir)


def test_multiple_projects():
    """Test that different projects have separate state."""
    print("\n" + "="*60)
    print("TEST 1b: Multiple Projects")
    print("="*60)
    
    temp_dir = tempfile.mkdtemp()
    workspace = Path(temp_dir)
    
    try:
        sm1 = StateManager(workspace, "project_alpha")
        sm2 = StateManager(workspace, "project_beta")
        
        state1 = sm1.load()
        state2 = sm2.load()
        
        state1["goal"] = "Alpha goal"
        state2["goal"] = "Beta goal"
        
        sm1.save(state1)
        sm2.save(state2)
        
        # Reload and verify separation
        loaded1 = sm1.load()
        loaded2 = sm2.load()
        
        assert loaded1["goal"] == "Alpha goal"
        assert loaded2["goal"] == "Beta goal"
        
        # Check directory structure
        assert (workspace / "projects" / "project_alpha").exists()
        assert (workspace / "projects" / "project_beta").exists()
        
        print("✓ Multiple projects have separate state")
        
    finally:
        shutil.rmtree(temp_dir)
    
    print("\n✅ Multiple projects test passed!\n")


if __name__ == "__main__":
    test_state_manager()
    test_multiple_projects()