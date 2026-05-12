#!/usr/bin/env python3
"""STEP 6: Real File Operations Test (Project-Scoped Sandbox)"""
import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from doit.orchestrator import Orchestrator
from doit.core.agent_orchestrator import AgentOrchestrator
from doit.core.browser_llm_adapter import async_llm_client
from doit.utils.session_logger import init_session_logger, logger

# =============================================================================
# ESTABLISHED CONFIGURATION PATTERN
# =============================================================================
WORKSPACE = Path("~/Documents/02-learn/dev/doit-workspace").expanduser()
URL = "https://www.usegpt.myorg"
PROJECT = "auto-sso-test"
# =============================================================================

def sync_llm_wrapper(bc, prompt: str) -> str:
    loop = asyncio.get_event_loop()
    if loop.is_closed():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(async_llm_client(bc, prompt))

def test_step6():
    print("="*60)
    print("STEP 6: Real File Operations Test (Project-Scoped)")
    print("="*60)
    # Audit trail (tees to session.log)
    logger.info("STEP 6: Real File Operations Test (Project-Scoped)")
    logger.info("Workspace: %s", WORKSPACE)
    logger.info("URL: %s", URL)
    logger.info("Project: %s", PROJECT)
    
    proj_dir = WORKSPACE / "projects" / PROJECT
    proj_dir.mkdir(parents=True, exist_ok=True)
    input_dir = proj_dir / "input"
    input_dir.mkdir(exist_ok=True)
    config_file = input_dir / "config.yaml"
    config_file.write_text("browser:\n  default_model: GPT-5.1\n  timeout_ms: 60000\nlogging:\n  level: INFO", encoding="utf-8")

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

        logger.info("Browser ready. Initializing agent...")
        agent = AgentOrchestrator(
            workspace_dir=WORKSPACE,
            project=PROJECT,
            llm_client=lambda p: sync_llm_wrapper(bc, p),
            autonomy_mode=1
        )

        goal = "Read 'input/config.yaml', find the 'default_model' value, and write only that value to 'output/model_info.txt'."
        print(f"\n🎯 Goal: {goal}")
        logger.info("Running goal: %s", goal)

        result = agent.run(goal_query=goal, max_steps=5)

        print(f"\n🏁 Final Result: {result['status']}")
        logger.info("Agent run finished with status: %s", result['status'])
        
        output_file = proj_dir / "output" / "model_info.txt"
        if output_file.exists():
            content = output_file.read_text(encoding="utf-8").strip()
            print(f"📄 Output file content: '{content}'")
            if "GPT-5.1" in content:
                print("✅ VERIFIED: Output contains expected value at correct project path")
                logger.info("Output file verified successfully")
            else:
                print(f"⚠️ Unexpected content: {content}")
                logger.warning("Output file contains unexpected content: %s", content)
        else:
            print("⚠️ Output file was not created")
            logger.warning("Output file missing: %s", output_file)

    except Exception as e:
        print(f"\n❌ Test Failed: {e}")
        logger.error("Test step6 failed: %s", e, exc_info=False)
        import traceback; traceback.print_exc()
    finally:
        if config_file.exists(): config_file.unlink()
        logger.info("Cleaned up test config file")
        
        print("\n🔒 Closing browser session...")
        logger.info("Closing browser session")
        loop.run_until_complete(orch.close_browser())
        loop.close()

if __name__ == "__main__":
    ctx = init_session_logger(WORKSPACE)  # ✅ Pass workspace to route sessions correctly
    logger.info("Starting test_step6_real_file_ops")
    test_step6()
    logger.info("Test execution finished")