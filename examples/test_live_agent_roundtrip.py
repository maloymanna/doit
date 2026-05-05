#!/usr/bin/env python3
"""
BABY STEP 1: Single-Line Prompt → Live Web LLM → JSON Validation
Uses your PROVEN async_llm_client. Zero mocks. Zero orchestrator changes.
"""
import asyncio
from pathlib import Path
from doit.orchestrator import Orchestrator
from doit.core.prompt_builder import SingleLinePromptBuilder
from doit.core.json_validator import JSONValidator, ValidationError
from doit.core.browser_llm_adapter import async_llm_client

WORKSPACE = Path.home() / "Documents/02-learn/dev/doit-workspace"
URL = "https://www.usegpt.myorg"
PROJECT = "baby-step-1"

async def test_live_roundtrip():
    print("="*60)
    print("BABY STEP 1: Live Prompt → LLM → JSON Validation")
    print("="*60)

    # 1. Build single-line prompt with strict schema injection
    builder = SingleLinePromptBuilder()
    prompt = builder.build_next_step_prompt(
        goal_id="test_001",
        current_step=0,
        last_result="none",
        context_history=[]
    )
    # Append explicit instruction to guarantee valid JSON for this test
    prompt += " ||INSTRUCTION|| Return EXACTLY: {\"tool_name\": \"reply\", \"parameters\": {\"text\": \"TEST_OK\"}, \"description\": \"baby step\", \"goal_status\": \"completed\", \"rationale\": \"test\"}"

    print(f"📝 Prompt length: {len(prompt)} chars (single-line guaranteed)")

    # 2. LIVE Browser Flow (EXACTLY your test_browser_adapter.py)
    orch = Orchestrator(WORKSPACE)
    await orch.open_chat_session(PROJECT)
    await orch.navigate(URL)
    bc = await orch.ensure_browser()

    print("\n⏳ PAUSING 15s. Manually click SKIP / SSO if needed.")
    await asyncio.sleep(15)

    ready = await bc.wait_for_prompt_box(timeout_ms=60000)
    if not ready:
        raise RuntimeError("❌ Prompt box timeout")

    # 3. Send & Extract (proven adapter)
    print("📤 Sending prompt to Web LLM...")
    raw_response = await async_llm_client(bc, prompt)
    if not raw_response:
        raise RuntimeError("❌ No response extracted from Web LLM")

    # 4. JSON Validation
    print("\n🔍 Validating response...")
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
        print(parsed)
    except ValidationError as e:
        print("❌ JSON VALIDATION FAILED")
        print(f"   Error: {e.message}")
        print(f"   Raw LLM Output: {raw_response[:300]}...")
    finally:
        print("\n🔒 Closing browser (session preserved)...")
        await orch.close_browser()

if __name__ == "__main__":
    asyncio.run(test_live_roundtrip())