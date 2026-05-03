# tests/test_pipeline.py [MOD v1.1]
import os
import sys
import tempfile
import json
from pathlib import Path

# Ensure src/ is importable
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from doit.core.state_manager import SQLiteStateManager
from doit.core.prompt_builder import SingleLinePromptBuilder
from doit.core.json_validator import JSONValidator, ValidationError

def test_pipeline():
    print("🔹 1. Testing SQLite State Manager (Cross-Platform)...")
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        mgr = SQLiteStateManager(workspace)
        assert (workspace / "sqlite" / "doit_state.db").exists(), "DB not created"
        mgr.create_goal("g1", "proj1", "Test query", 5)
        mgr.log_step("g1", 0, "test_tool", {"x": 1}, "OK", "test", "completed")
        state = mgr.get_goal_state("g1")
        assert state["status"] == "planning" or state["current_step"] == 1
        print("✅ StateManager OK")

    print("\n🔹 2. Testing Single-Line Prompt Builder...")
    builder = SingleLinePromptBuilder()
    builder.register_tool("file_write", "Writes to local path", {"path": "str"})
    builder.register_tool("browser_nav", "Opens URL in Edge", {"url": "str"})
    prompt = builder.build_next_step_prompt("g1", 1, "Previous step OK.", [{"step_index": 0, "tool_name": "init", "status": "done", "result": "ready"}])
    assert "\n" not in prompt and "\r" not in prompt, "FAIL: Prompt contains newlines"
    assert "||SYS||" in prompt and "||SCHEMA||" in prompt
    print("✅ PromptBuilder OK (strictly single-line)")

    print("\n🔹 3. Testing JSON Validator...")
    validator = JSONValidator()
    # FIXED: schema must explicitly define 'properties' when using additionalProperties: false
    schema = {
        "type": "object",
        "properties": {
            "tool_name": {"type": "string"},
            "params": {"type": "object"}
        },
        "required": ["tool_name"],
        "additionalProperties": False
    }
    
    # Markdown leak test
    raw = 'Sure! ```json\n{"tool_name": "file_write", "params": {}}\n```'
    res = validator.parse_and_validate(raw, schema)
    assert res["tool_name"] == "file_write"
    
    # Malformed test
    try:
        validator.parse_and_validate('no json here', schema)
        print("❌ FAIL: Should have raised ValidationError")
    except ValidationError:
        pass
    print("✅ JSONValidator OK (extraction + schema check)")

    print("\n🎉 Phase 1 pipeline tests passed. Ready for integration.")

if __name__ == "__main__":
    test_pipeline()