#!/usr/bin/env python3
"""
BABY STEP 2: PromptBuilder → Live LLM → JSON Validation
Uses your PROVEN async_llm_client. Zero mocks. Zero orchestrator changes.
Persistent profile: auto-sso-test (reuses SSO session).
"""
import asyncio
from pathlib import Path
from doit.orchestrator import Orchestrator
from doit.core.prompt_builder import SingleLinePromptBuilder
from doit.core.json_validator import JSONValidator, ValidationError
from doit.core.browser_llm_adapter import async_llm_client

# Use same persistent profile as your working tests
WORKSPACE = Path("C:/Users/myuser/dev/doit-workspace")
URL = "https://www.usegpt.myorg"
PROJECT = "auto-sso-test"  # Reuses your proven persistent session

async def test_prompt_builder_live():
    print("="*60)
    print("BABY STEP 2: PromptBuilder → Live LLM → JSON Validation")
    print("="*60)

    # 1. Build single-line prompt with strict schema injection
    builder = SingleLinePromptBuilder()
    
    # Register a simple test tool so it appears in the prompt
    builder.register_tool(
        "test_reply", 
        "Replies with a test message", 
        {"text": {"type": "string"}}
    )
    
    prompt = builder.build_next_step_prompt(
        goal_id="test_002",
        current_step=0,
        last_result="none",
        context_history=[]
    )
    
    # Append explicit instruction to guarantee valid JSON for this test
    prompt += " ||INSTRUCTION|| Return EXACTLY this JSON and nothing else: {\"tool_name\": \"test_reply\", \"parameters\": {\"text\": \"BUILDER_OK\"}, \"description\": \"baby step 2\", \"goal_status\": \"completed\", \"rationale\": \"test\"}"
    
    print(f"📝 Prompt length: {len(prompt)} chars")
    print(f"   Single-line check: {'✅ PASS' if '\n' not in prompt else '❌ FAIL'}")
    print(f"   First 100 chars: {prompt[:100]}...")

    # 2. LIVE Browser Flow (EXACTLY your proven adapter)
    orch = Orchestrator(WORKSPACE)
    await orch.open_chat_session(PROJECT)
    await orch.navigate(URL)
    bc = orch.browser

    # No manual pause - persistent profile should already be logged in
    # If SKIP banner appears, we can add programmatic handling later
    # For now, just wait for prompt box with timeout
    ready = await bc.wait_for_prompt_box(timeout_ms=60000)
    if not ready:
        raise RuntimeError("❌ Prompt box timeout")

    # 3. Send & Extract (proven adapter)
    print("📤 Sending prompt to Web LLM...")
    raw_response = await async_llm_client(bc, prompt)
    if not raw_response:
        raise RuntimeError("❌ No response extracted from Web LLM")
    
    print(f"📥 Raw LLM output ({len(raw_response)} chars): {raw_response[:200]}...")

    # 4. JSON Validation
    print("\n🔍 Validating response...")
    validator = JSONValidator()
    
    # Schema must match what we injected in the prompt
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
        import json
        print(json.dumps(parsed, indent=2))
        
        # Verify the injected instruction was followed
        if parsed.get("tool_name") == "test_reply" and parsed.get("parameters", {}).get("text") == "BUILDER_OK":
            print("✅ LLM followed injected instruction exactly!")
        else:
            print("⚠ LLM returned valid JSON but didn't follow exact instruction (still a pass)")
            
    except ValidationError as e:
        print("❌ JSON VALIDATION FAILED")
        print(f"   Error: {e.message}")
        print(f"   Raw LLM Output: {raw_response[:300]}...")
        raise
    finally:
        print("\n🔒 Closing browser (session preserved)...")
        await orch.close_browser()

if __name__ == "__main__":
    asyncio.run(test_prompt_builder_live())