#!/usr/bin/env python3
"""
STEP 6: Real File Operations Test
Tests: Real file_read/file_write execution within workspace sandbox.
Uses established configuration (no env vars) for CLI alignment.
"""
import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from doit.orchestrator import Orchestrator
from doit.core.agent_orchestrator import AgentOrchestrator
from doit.core.browser_llm_adapter import async_llm_client
from doit.plugins.file_ops import FILE_READ_SCHEMA, FILE_WRITE_SCHEMA, file_read, file_write

# =============================================================================
# ESTABLISHED CONFIGURATION PATTERN (matches CLI --workspace argument)
# =============================================================================
WORKSPACE = Path("C:/Users/myuser/dev/doit-workspace").expanduser()
URL = "https://www.usegpt.myorg"
PROJECT = "auto-sso-test"
# =============================================================================

def sync_llm_wrapper(bc, prompt: str) -> str:
    """Synchronous wrapper for async LLM client."""
    loop = asyncio.get_event_loop()
    if loop.is_closed():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(async_llm_client(bc, prompt))

def test_step6():
    print("="*60)
    print("STEP 6: Real File Operations Test")
    print("="*60)
    print(f"Workspace: {WORKSPACE}")
    
    # Setup test files
    readonly_dir = WORKSPACE / "readonly_input"
    readonly_dir.mkdir(parents=True, exist_ok=True)
    config_file = readonly_dir / "config.yaml"
    config_file.write_text("browser:\n  default_model: GPT-5.1\n  timeout_ms: 60000\nlogging:\n  level: INFO", encoding="utf-8")
    print(f"✅ Created test config: {config_file}")

    orch = Orchestrator(WORKSPACE)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        # Browser setup
        loop.run_until_complete(orch.open_chat_session(PROJECT))
        loop.run_until_complete(orch.navigate(URL))
        bc = orch.browser
        ready = loop.run_until_complete(bc.wait_for_prompt_box(timeout_ms=60000))
        if not ready:
            print("❌ Chat interface not ready."); return
        print("✅ Browser ready")

        # Create dispatcher with REAL tools
        from doit.core.action_dispatcher import ActionDispatcher
        dispatcher = ActionDispatcher(WORKSPACE, autonomy_mode=1)  # Mode 1 = auto for safe ops
        dispatcher.register("file_read", file_read)
        dispatcher.register("file_write", file_write)

        # Create orchestrator with real dispatcher
        agent = AgentOrchestrator(
            workspace_dir=WORKSPACE,
            llm_client=lambda p: sync_llm_wrapper(bc, p),
            action_dispatcher=dispatcher,
            autonomy_mode=1
        )

        # Run goal with REAL file I/O
        goal = "Read 'readonly_input/config.yaml', find the 'default_model' value, and write only that value to 'projects/output/model_info.txt'."
        print(f"\n🎯 Goal: {goal}")
        result = agent.run(goal_query=goal, project=PROJECT, max_steps=5)

        print(f"\n🏁 Final Result: {result['status']}")
        
        # Verify output file was created with correct content
        output_file = WORKSPACE / "projects" / "output" / "model_info.txt"
        if output_file.exists():
            content = output_file.read_text(encoding="utf-8").strip()
            print(f"📄 Output file content: '{content}'")
            if "GPT-5.1" in content:
                print("✅ VERIFIED: Output contains expected 'default_model' value")
            else:
                print(f"⚠️ Output doesn't contain 'GPT-5.1' (got: {content})")
        else:
            print("⚠️ Output file was not created")

        if result['status'] == 'completed':
            print("✅ TEST PASSED: Real file ops loop completed successfully!")
        else:
            print(f"⚠️ Loop finished with status: {result['status']}")

    except Exception as e:
        print(f"\n❌ Test Failed: {e}")
        import traceback; traceback.print_exc()
    finally:
        # Cleanup
        if config_file.exists():
            config_file.unlink()
        output_file = WORKSPACE / "projects" / "output" / "model_info.txt"
        if output_file.exists():
            output_file.unlink()
        print("\n🔒 Closing browser session...")
        loop.run_until_complete(orch.close_browser())
        loop.close()

if __name__ == "__main__":
    test_step6()