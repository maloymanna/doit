#!/usr/bin/env python3
"""
STEP 6: Tool Invocation Validation (Dry-Run)
Tests: LLM tool selection → Parameter validation → Mock execution routing.
Zero real file I/O. Verifies the decision loop before wiring real execution.
"""
import sys
import json
import asyncio
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from doit.orchestrator import Orchestrator
from doit.core.agent_orchestrator import AgentOrchestrator
from doit.core.browser_llm_adapter import async_llm_client
from doit.core.mock_dispatcher import MockActionDispatcher
from doit.plugins.file_ops import FILE_READ_SCHEMA, FILE_WRITE_SCHEMA

WORKSPACE = Path("C:/Users/myuser/dev/doit-workspace")
URL = "https://www.usegpt.myorg"
PROJECT = "auto-sso-test"

def sync_llm_wrapper(bc, prompt: str) -> str:
    loop = asyncio.get_event_loop()
    if loop.is_closed():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(async_llm_client(bc, prompt))

def test_step6():
    print("="*60)
    print("STEP 6: Tool Invocation Validation (Dry-Run)")
    print("="*60)

    orch = Orchestrator(WORKSPACE)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        loop.run_until_complete(orch.open_chat_session(PROJECT))
        loop.run_until_complete(orch.navigate(URL))
        bc = orch.browser
        ready = loop.run_until_complete(bc.wait_for_prompt_box(timeout_ms=60000))
        if not ready:
            print("❌ Chat interface not ready."); return

        # 1. Register tools with strict schemas
        from doit.core.prompt_builder import SingleLinePromptBuilder
        builder = SingleLinePromptBuilder()
        builder.register_tool("file_read", "Reads content from a local file path", FILE_READ_SCHEMA)
        builder.register_tool("file_write", "Writes content to a local file", FILE_WRITE_SCHEMA)

        # 2. Create mock dispatcher
        mock_disp = MockActionDispatcher()

        # 3. Create orchestrator
        agent = AgentOrchestrator(
            workspace_dir=WORKSPACE,
            llm_client=lambda p: sync_llm_wrapper(bc, p),
            prompt_builder=builder,
            action_dispatcher=mock_disp
        )

        # 4. Run goal
        goal = "Read 'config.yaml', find the 'default_model' value, and write only that value to 'model_info.txt'."
        print(f"\n🎯 Goal: {goal}")
        result = agent.run(goal_query=goal, project=PROJECT, max_steps=4)

        print(f"\n🏁 Final Result: {result['status']}")
        if result['status'] == 'completed':
            print("✅ Tool invocation sequence validated successfully!")
        else:
            print(f"⚠️ Sequence ended with status: {result['status']}")

        # 5. Verify execution log
        print("\n📋 Invocation Log:")
        for i, log in enumerate(mock_disp.execution_log, 1):
            print(f"   {i}. Tool: {log['tool']} | Params: {log['params']}")
            
        # Assert correct sequence
        assert len(mock_disp.execution_log) >= 2, "Expected at least 2 tool calls"
        assert mock_disp.execution_log[0]['tool'] == 'file_read'
        assert 'config.yaml' in str(mock_disp.execution_log[0]['params'])
        assert mock_disp.execution_log[1]['tool'] == 'file_write'
        assert 'model_info.txt' in str(mock_disp.execution_log[1]['params'])
        print("\n✅ Assertion checks passed: LLM correctly selected tools & parameters.")

    except Exception as e:
        print(f"\n❌ Test Failed: {e}")
        import traceback; traceback.print_exc()
    finally:
        loop.run_until_complete(orch.close_browser())
        loop.close()

if __name__ == "__main__":
    test_step6()