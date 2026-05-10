# examples/test_step4_goal_and_tools.py [MOD v1.2]
#!/usr/bin/env python3
"""
BABY STEP 4: Goal Decomposition & Tool Injection (Mock Loop)
Runs 4 strict phases with ZERO local execution.
"""
import sys
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from doit.core.prompt_builder import SingleLinePromptBuilder
from doit.core.json_validator import JSONValidator, ValidationError

# ... (Schemas remain the same) ...
ACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "tool_name": {"type": "string"},
        "parameters": {"type": "object"},
        "description": {"type": "string"},
        "goal_status": {"type": "string", "enum": ["in_progress", "completed", "blocked", "requires_user_confirmation"]},
        "rationale": {"type": "string"},
        "fallback_instruction": {"type": "string"}
    },
    "required": ["tool_name", "parameters", "description", "goal_status", "rationale"],
    "additionalProperties": False
}

PLAN_SCHEMA = {
    "type": "object",
    "properties": {
        "plan_steps": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "step": {"type": "integer"},
                    "tool_name": {"type": "string"},
                    "description": {"type": "string"}
                },
                "required": ["step", "tool_name", "description"]
            }
        },
        "goal_status": {"type": "string"}
    },
    "required": ["plan_steps", "goal_status"],
    "additionalProperties": False
}

def run_phase(phase_name, test_fn):
    print(f"\n{'='*60}")
    print(f"PHASE {phase_name}: {test_fn.__doc__}")
    print(f"{'='*60}")
    try:
        test_fn()
        print(f"✅ PHASE {phase_name} PASSED")
        return True
    except AssertionError as e:
        print(f"❌ PHASE {phase_name} FAILED: {e}")
        return False
    except Exception as e:
        print(f"💥 PHASE {phase_name} ERROR: {type(e).__name__}: {e}")
        return False

# ---------------------------------------------------------
# PHASE 1
# ---------------------------------------------------------
def phase1_goal_breakdown():
    """Test plan prompt generation + mock plan JSON validation"""
    builder = SingleLinePromptBuilder()
    validator = JSONValidator()
    
    goal = "Deploy v2.1 to staging, run smoke tests, notify slack channel"
    prompt = builder.build_plan_prompt(goal)
    
    assert "||GOAL||" in prompt, "Missing goal marker"
    assert "||SCHEMA||" in prompt, "Missing schema marker"
    assert "\n" not in prompt, "Plan prompt contains newlines"
    print("   ✅ Plan prompt is valid & single-line")
    
    mock_response = json.dumps({
        "plan_steps": [
            {"step": 1, "tool_name": "deploy", "description": "Push code to staging env"},
            {"step": 2, "tool_name": "test", "description": "Run automated smoke tests"},
            {"step": 3, "tool_name": "notify", "description": "Post success to Slack"}
        ],
        "goal_status": "in_progress"
    })
    
    parsed = validator.parse_and_validate(mock_response, PLAN_SCHEMA)
    assert len(parsed["plan_steps"]) == 3
    print("   ✅ Mock breakdown validated successfully")

# ---------------------------------------------------------
# PHASE 2
# ---------------------------------------------------------
def phase2_tool_injection():
    """Verify tools are correctly injected into action prompts"""
    builder = SingleLinePromptBuilder()
    
    builder.register_tool("file_read", "Reads content from local path", {"path": {"type": "string"}})
    builder.register_tool("browser_nav", "Opens URL in Edge", {"url": {"type": "string"}})
    builder.register_tool("save_draft", "Saves email draft", {"subject": {"type": "string"}, "body": {"type": "string"}})
    
    # FIXED: Added "Test Goal" as first arg
    prompt = builder.build_next_step_prompt("Test Goal Injection", "g1", 0, "none", [])
    
    assert "||TOOLS||" in prompt
    assert "file_read:" in prompt
    assert "browser_nav:" in prompt
    assert "save_draft:" in prompt
    assert "\n" not in prompt, "Tool injection broke single-line constraint"
    
    print("   ✅ All 3 tools injected correctly")
    print("   ✅ Prompt remains strictly single-line")

# ---------------------------------------------------------
# PHASE 3
# ---------------------------------------------------------
def phase3_tool_usage_in_breakdown():
    """Verify mock LLM returns steps that match injected tool schemas"""
    builder = SingleLinePromptBuilder()
    validator = JSONValidator()
    
    builder.register_tool("deploy", "Pushes to environment", {"env": {"type": "string", "enum": ["staging", "prod"]}, "tag": {"type": "string"}})
    builder.register_tool("test", "Runs test suite", {"suite": {"type": "string"}, "threads": {"type": "integer"}})
    builder.register_tool("notify", "Sends alert", {"channel": {"type": "string"}})
    
    mock_step = json.dumps({
        "tool_name": "deploy",
        "parameters": {"env": "staging", "tag": "v2.1.0"},
        "description": "Deploy to staging",
        "goal_status": "in_progress",
        "rationale": "First step in plan"
    })
    
    deploy_schema = {
        "type": "object",
        "properties": {
            "tool_name": {"type": "string"},
            "parameters": {
                "type": "object",
                "properties": {"env": {"type": "string", "enum": ["staging", "prod"]}, "tag": {"type": "string"}},
                "required": ["env", "tag"],
                "additionalProperties": False
            },
            "description": {"type": "string"},
            "goal_status": {"type": "string", "enum": ["in_progress", "completed"]},
            "rationale": {"type": "string"}
        },
        "required": ["tool_name", "parameters", "description", "goal_status", "rationale"],
        "additionalProperties": False
    }
    
    parsed = validator.parse_and_validate(mock_step, deploy_schema)
    assert parsed["tool_name"] == "deploy"
    print("   ✅ Tool usage matches schema exactly")
    
    invalid_mock = mock_step.replace('"staging"', '"production"')
    try:
        validator.parse_and_validate(invalid_mock, deploy_schema)
        assert False, "Should have failed validation"
    except ValidationError:
        print("   ✅ Correctly rejected invalid enum parameter")

# ---------------------------------------------------------
# PHASE 4
# ---------------------------------------------------------
def phase4_state_management():
    """Simulate orchestrator loop: prompt -> mock LLM -> validate -> update state"""
    builder = SingleLinePromptBuilder()
    validator = JSONValidator()
    builder.register_tool("step_tool", "Mock step", {"id": {"type": "integer"}})
    
    state = {
        "current_step": 0,
        "history": [],
        "status": "in_progress",
        "max_steps": 3
    }
    
    mock_responses = [
        {"tool_name": "step_tool", "parameters": {"id": 1}, "description": "Init", "goal_status": "in_progress", "rationale": "Start"},
        {"tool_name": "step_tool", "parameters": {"id": 2}, "description": "Process", "goal_status": "in_progress", "rationale": "Mid"},
        {"tool_name": "step_tool", "parameters": {"id": 3}, "description": "Finish", "goal_status": "completed", "rationale": "Done"}
    ]
    
    loop_count = 0
    for mock_resp in mock_responses:
        if state["current_step"] >= state["max_steps"]:
            state["status"] = "blocked"
            break
            
        # FIXED: Added "Simulated goal" as first arg
        prompt = builder.build_next_step_prompt("Simulated goal", "sim_01", state["current_step"], "ok", state["history"])
        
        raw = json.dumps(mock_resp)
        action = validator.parse_and_validate(raw, ACTION_SCHEMA)
        
        state["history"].append({
            "step_index": state["current_step"],
            "tool_name": action["tool_name"],
            "status": "success",
            "result": action["description"]
        })
        state["current_step"] += 1
        state["status"] = action["goal_status"]
        loop_count += 1
        
        if state["status"] == "completed":
            print(f"   ✅ Loop exited on step {loop_count} with status 'completed'")
            break
            
    assert loop_count == 3, f"Expected 3 steps, got {loop_count}"
    assert len(state["history"]) == 3
    assert state["status"] == "completed"
    print("   ✅ State history correctly tracked across 3 steps")
    print("   ✅ Loop terminated correctly on 'completed' status")

# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------
if __name__ == "__main__":
    print("🚀 BABY STEP 4: Goal Decomposition & Tool Injection (Mock Loop)")
    
    results = []
    results.append(run_phase("1", phase1_goal_breakdown))
    results.append(run_phase("2", phase2_tool_injection))
    results.append(run_phase("3", phase3_tool_usage_in_breakdown))
    results.append(run_phase("4", phase4_state_management))
    
    print("\n" + "="*60)
    if all(results):
        print("🎉 ALL 4 PHASES PASSED.")
    else:
        print("⚠️  Some phases failed.")
    print("="*60)