#!/usr/bin/env python3
"""STEP 8: LLM Integration Test for browser_screenshot & browser_fetch_resource"""
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
PROJECT = "auto-sso-test"
LLM_URL = "https://www.usegpt.myorg"

def sync_llm_wrapper(bc, prompt: str, completion_timeout_ms: int = 180000) -> str:
    loop = asyncio.get_event_loop()
    if loop.is_closed():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(async_llm_client(bc, prompt, completion_timeout_ms))

def test_browser_ops_integration():
    print("="*60)
    print("STEP 8: LLM INTEGRATION TEST (Screenshot + Fetch Resource)")
    print("="*60)
    logger.info("Integration test started")
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        orch = Orchestrator(WORKSPACE)
        loop.run_until_complete(orch.open_chat_session(PROJECT))
        bc = orch.browser
        
        # Navigate Tab A to LLM UI (Tab A stays here permanently)
        loop.run_until_complete(orch.navigate(LLM_URL))
        ready = loop.run_until_complete(bc.wait_for_prompt_box(timeout_ms=60000))
        if not ready:
            print("❌ Chat interface not ready"); return

        try:
            cfg = Config(WORKSPACE)
            autonomy_mode = cfg.autonomy.mode
            completion_timeout = cfg.browser.completion_timeout_ms
        except:
            autonomy_mode = 0; completion_timeout = 30000

        agent = AgentOrchestrator(
            workspace_dir=WORKSPACE, project=PROJECT,
            llm_client=lambda p: sync_llm_wrapper(bc, p, completion_timeout),
            autonomy_mode=autonomy_mode, controller=bc, loop=loop
        )

        goal = (
            "1. Navigate to 'https://httpbin.org/html', take a full-page screenshot and save it to 'output/httpbin_ss.png'. "
            "2. Then navigate to 'https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf' and fetch it directly, saving to 'output/dummy_fetched.pdf'. "
            "Set goal_status to 'completed' only after both files are successfully saved."
        )
        print(f"\n🎯 Goal: {goal}")
        result = agent.run(goal_query=goal, max_steps=6)
        print(f"\n🏁 Final Result: {result['status']}")

        proj_dir = WORKSPACE / "projects" / PROJECT
        ss_file = proj_dir / "output" / "httpbin_ss.png"
        pdf_file = proj_dir / "output" / "dummy_fetched.pdf"

        ss_ok = ss_file.exists() and ss_file.stat().st_size > 1000
        pdf_ok = pdf_file.exists() and pdf_file.stat().st_size > 100

        if ss_ok and pdf_ok:
            print(f"✅ VERIFIED: Screenshot ({ss_file.stat().st_size} bytes) + PDF ({pdf_file.stat().st_size} bytes) saved")
        else:
            print(f"⚠️ Partial/Failed: Screenshot={ss_ok}, PDF={pdf_ok}")

    except Exception as e:
        print(f"\n❌ Test Failed: {e}")
        import traceback; traceback.print_exc()
    finally:
        print("\n🔒 Closing browser session...")
        try: loop.run_until_complete(orch.close_browser())
        except: pass
        loop.close()

if __name__ == "__main__":
    init_session_logger(WORKSPACE)
    test_browser_ops_integration()