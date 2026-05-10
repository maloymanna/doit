# examples/test_step2_prompt_builder.py [MOD v1.1]
#!/usr/bin/env python3
"""
BABY STEP 2: PromptBuilder → Live LLM → JSON Validation
"""
import asyncio
import json
from pathlib import Path

# Ensure imports work
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from doit.orchestrator import Orchestrator
from doit.core.prompt_builder import SingleLinePromptBuilder
from doit.core.json_validator import JSONValidator, ValidationError
from doit.core.browser_llm_adapter import async_llm_client

WORKSPACE = Path("~/Documents/02-learn/dev/doit-workspace")
URL = "https://www.usegpt.myorg"
PROJECT = "auto-sso-test"

async def test_prompt_builder_live():
    print("="*60)
    print("BABY STEP 2: PromptBuilder → Live LLM → JSON Validation")
    print("="*60)

    builder = SingleLinePromptBuilder()
    builder.register_tool("test_reply", "Replies with a test message", {"text": {"type": "string"}})
    
    # Build prompt (FIXED: Added goal_query)
    prompt = builder.build_next_step_prompt(
        goal_query="Test goal for builder",  # ADDED
        goal_id="test_002",
        current_step=0,
        last_result="none",
        context_history=[]
    )
    
    prompt += ' ||INSTRUCTION|| Return EXACTLY: {"tool_name": "test_reply", "parameters": {"text": "BUILDER_OK"}, "description": "baby step 2", "goal_status": "completed", "rationale": "test"}'
    
    print(f"📝 Prompt length: {len(prompt)} chars")

    orch = Orchestrator(WORKSPACE)
    await orch.open_chat_session(PROJECT)
    await orch.navigate(URL)
    bc = orch.browser

    ready = await bc.wait_for_prompt_box(timeout_ms=60000)
    if not ready:
        raise RuntimeError("❌ Prompt box timeout")

    print("📤 Sending prompt to Web LLM...")
    raw_response = await async_llm_client(bc, prompt)
    if not raw_response:
        raise RuntimeError("❌ No response extracted from Web LLM")
    
    print(f"📥 Raw LLM output ({len(raw_response)} chars): {raw_response[:200]}...")

    validator = JSONValidator()
    schema = {
        "type": "object",
        "properties": {
            "tool_name": {"type": "string"},
            "parameters": {"type": "object"},
            "description": {"type": "string"},
            "goal_status": {"type": "string"},
            "rationale": {"type": "string"}
        },
        "required": ["tool_name", "parameters", "description", "goal_status", "rationale"],
        "additionalProperties": False
    }

    try:
        parsed = validator.parse_and_validate(raw_response, schema)
        print("✅ SUCCESS! Valid JSON received:")
        print(json.dumps(parsed, indent=2))
    except ValidationError as e:
        print("❌ JSON VALIDATION FAILED")
        print(f"   Error: {e.message}")
        raise
    finally:
        print("\n🔒 Closing browser (session preserved)...")
        await orch.close_browser()

if __name__ == "__main__":
    asyncio.run(test_prompt_builder_live())