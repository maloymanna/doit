#!/usr/bin/env python3
"""
BABY STEP 5: Live LLM + Mock Tool Execution
Tests: PromptBuilder -> Live Browser/LLM -> JSONValidator -> MockDispatcher -> StateManager
Zero local execution. All tool calls intercepted & mocked.
"""
import sys
import asyncio
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from doit.orchestrator import Orchestrator
from doit.core.agent_orchestrator import AgentOrchestrator
from doit.core.browser_llm_adapter import async_llm_client
from doit.core.mock_dispatcher import MockActionDispatcher

# Configuration (reuses your proven persistent profile)
WORKSPACE = Path("C:/Users/myuser/dev/doit-workspace")
URL = "https://www.usegpt.myorg"
PROJECT = "auto-sso-test"

def sync_llm_wrapper(bc, prompt: str) -> str:
    """Synchronous wrapper for async LLM client."""
    loop = asyncio.get_event_loop()
    if loop.is_closed():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(async_llm_client(bc, prompt))

def test_step5():
    print("="*60)
    print("BABY STEP 5: Live LLM + Mock Tool Execution")
    print("="*60)

    # 1. Initialize Browser Orchestrator
    print("🚀 1. Initializing Browser Orchestrator...")
    orch = Orchestrator(WORKSPACE)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        loop.run_until_complete(orch.open_chat_session(PROJECT))
        loop.run_until_complete(orch.navigate(URL))
        bc = orch.browser
        ready = loop.run_until_complete(bc.wait_for_prompt_box(timeout_ms=60000))
        if not ready:
            print("❌ Chat interface not ready.")
            return
        print("✅ Browser ready and session active.")

        # 2. Create Mock Dispatcher
        mock_disp = MockActionDispatcher()

        # 3. Create Agent Orchestrator (Live LLM + Mock Dispatch)
        agent = AgentOrchestrator(
            workspace_dir=WORKSPACE,
            llm_client=lambda p: sync_llm_wrapper(bc, p),
            action_dispatcher=mock_disp
        )

        # 4. Run Live Loop
        print("\n🤖 2. Starting Agent Loop (Live LLM, Mock Execution)...")
        goal = "Read the file 'config.yaml', find the default_model value, and write it to 'model_info.txt'."
        print(f"   Goal: {goal}")
        print("   (Watch the browser: Agent is thinking and sending prompts)")
        
        result = agent.run(goal_query=goal, project=PROJECT, max_steps=5)

        print(f"\n🏁 Agent Result: {json.dumps(result, indent=2)}")
        
        if result['status'] == 'completed':
            print("✅ TEST PASSED: Agent loop completed successfully!")
        else:
            print(f"⚠️ Agent loop finished with status: {result['status']}")

        # 5. Show Mock Execution Log
        print("\n📋 Mock Execution Log:")
        for i, log in enumerate(mock_disp.execution_log, 1):
            print(f"   {i}. Tool: {log['tool']} | Params: {log['params']}")

    except Exception as e:
        print(f"\n❌ Integration Test Failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n🔒 Closing browser session...")
        loop.run_until_complete(orch.close_browser())
        loop.close()

if __name__ == "__main__":
    test_step5()