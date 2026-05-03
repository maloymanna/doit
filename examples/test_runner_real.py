#!/usr/bin/env python3
"""Test the complete agent orchestrator with real browser (async runner)."""

import asyncio
from pathlib import Path
from doit.orchestrator import Orchestrator
from doit.core.runner import run
from doit.core.browser_llm_adapter import async_llm_client
from doit.core.state_manager import StateManager

# ============================================================
# CONFIGURATION - Change these for your setup
# ============================================================

WORKSPACE = Path.home() / "Documents/02-learn/dev/doit-workspace"
URL = "https://www.usegpt.myorg"
PROJECT = "auto-sso-test"  # Reuse existing persistent profile

print("\n" + "="*70)
print("RUNNING: test_runner_real.py - Real Browser Agent Loop")
print("="*70)
print(f"Workspace: {WORKSPACE}")
print(f"URL: {URL}")
print(f"Project: {PROJECT}")
print("="*70)


async def setup_browser():
    """Initialize browser and return controller."""
    orch = Orchestrator(WORKSPACE)
    await orch.open_chat_session(PROJECT)
    await orch.navigate(URL)
    bc = orch.browser
    ready = await bc.wait_for_prompt_box(timeout_ms=120000)
    if not ready:
        raise Exception("Timeout waiting for chat interface")
    print("✓ Chat interface ready\n")
    return orch, bc


async def test_agent_loop():
    """Test agent orchestrator with a real world goal."""
    print("\n" + "="*70)
    print("TEST: Agent Loop with Real Browser - Weather Forecast Goal")
    print("="*70)

    orch, bc = await setup_browser()
    try:
        # Define async LLM client using the browser adapter
        async def llm_client(prompt: str) -> str:
            return await async_llm_client(bc, prompt)

        goal = "Find the weather forecast for the next 7 days in Paris and summarize it."

        # IMPORTANT: await the run() function (async runner)
        result = await run(
            goal=goal,
            project=PROJECT,
            workspace_root=WORKSPACE,
            llm_client=llm_client,
            max_iterations=15,
            verbose=True
        )

        # Verify state and history were created
        sm = StateManager(WORKSPACE, PROJECT)
        final_state = sm.load()
        history = sm.load_history()
        iterations = final_state.get("iteration", 0)

        print(f"\n📈 Total iterations executed: {iterations}")
        print(f"📊 History entries: {len(history)}")
        print(f"🏁 Final result: {result}")

        if result["status"] in ["completed", "max_iterations_reached"]:
            print("\n✅ Agent orchestrator test completed!")
        else:
            print(f"\n❌ Agent loop failed: {result['status']}")

    finally:
        await orch.close_browser()


if __name__ == "__main__":
    asyncio.run(test_agent_loop())