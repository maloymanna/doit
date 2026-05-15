#!/usr/bin/env python3
"""Test llm_attach_file: Provides context via UI attachment, validates LLM extraction."""
import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from doit.orchestrator import Orchestrator
from doit.core.agent_orchestrator import AgentOrchestrator
from doit.core.browser_llm_adapter import async_llm_client
from doit.utils.session_logger import init_session_logger, logger
from doit.config import Config

WORKSPACE = Path("~/Documents/02-learn/dev/doit-workspace").expanduser()
PROJECT = "attach-context-test"

def sync_llm_wrapper(bc, prompt: str, completion_timeout_ms: int = 180000) -> str:
    loop = asyncio.get_event_loop()
    if loop.is_closed():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(async_llm_client(bc, prompt, completion_timeout_ms))

def test_attach_context():
    print("="*60)
    print("TEST: LLM Attachment Context Extraction")
    print("="*60)
    logger.info("Attachment context test started")
    
    proj_dir = WORKSPACE / "projects" / PROJECT
    proj_dir.mkdir(parents=True, exist_ok=True)
    context_file = proj_dir / "context_data.txt"
    context_file.write_text("PROJECT_STATUS: GREEN\nBUDGET_REMAINING: $42,500\nDEADLINE: 2026-06-15", encoding="utf-8")
    
    orch = Orchestrator(WORKSPACE)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        # 1. Open session & navigate to LLM
        loop.run_until_complete(orch.open_chat_session(PROJECT))
        loop.run_until_complete(orch.navigate("https://www.usegpt.myorg"))
        bc = orch.browser
        
        ready = loop.run_until_complete(bc.wait_for_prompt_box(timeout_ms=60000))
        if not ready:
            print("❌ Chat interface not ready"); return

        # 2. Load config & init agent
        try:
            cfg = Config(WORKSPACE)
            autonomy_mode = cfg.autonomy.mode
            completion_timeout_ms = cfg.browser.completion_timeout_ms
        except:
            autonomy_mode = 0; completion_timeout_ms = 180000

        agent = AgentOrchestrator(
            workspace_dir=WORKSPACE, project=PROJECT,
            llm_client=lambda p: sync_llm_wrapper(bc, p, completion_timeout_ms),
            autonomy_mode=autonomy_mode, controller=bc, loop=loop
        )

        # 3. Attach file BEFORE agent loop (orchestrator-only step)
        print("\n📎 Attaching context file...")
        attach_res = agent.dispatcher.dispatch({
            "tool_name": "llm_attach_file",
            "parameters": {"file_paths": ["context_data.txt"]}
        })
        print(f"   Attach result: {attach_res}")
        if attach_res.get("status") != "ok":
            print("⚠️ Attachment failed. Continuing anyway for prompt test."); return

        # 4. Run agent with goal referencing attachment
        goal = (
            "Additional context is in the attached file. "
            "Extract the value of BUDGET_REMAINING and write it to 'output/budget.txt'."
        )
        print(f"\n🎯 Goal: {goal}")
        result = agent.run(goal_query=goal, max_steps=5)
        print(f"\n🏁 Final Result: {result['status']}")

        # 5. Verify output
        out_file = proj_dir / "output" / "budget.txt"
        if out_file.exists():
            content = out_file.read_text(encoding="utf-8").strip()
            print(f"📄 Output: '{content}'")
            if "$42,500" in content or "42500" in content:
                print("✅ VERIFIED: LLM read attached context and extracted correct value")
                logger.info("Attachment context test passed")
            else:
                print(f"⚠️ Unexpected content: {content}")
        else:
            print("⚠️ Output file not created")

    except Exception as e:
        print(f"\n❌ Test Failed: {e}")
        logger.error("Test failed: %s", e, exc_info=False)
        import traceback; traceback.print_exc()
    finally:
        if context_file.exists(): context_file.unlink()
        print("\n🔒 Closing session...")
        try: loop.run_until_complete(orch.close_browser())
        except: pass
        loop.close()

if __name__ == "__main__":
    ctx = init_session_logger(WORKSPACE)
    test_attach_context()