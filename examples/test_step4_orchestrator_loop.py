#!/usr/bin/env python3
"""
BABY STEP 4: Full Orchestrator Loop Integration
Tests: Orchestrator -> PromptBuilder -> Live LLM -> JSONValidator -> StateManager
"""
import sys
import asyncio
import sqlite3
from pathlib import Path

# Add src to path for direct imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from doit.orchestrator import Orchestrator
from doit.core.agent_orchestrator import AgentOrchestrator
from doit.core.browser_llm_adapter import async_llm_client

# Configuration
WORKSPACE = Path("C:/Users/myuser/dev/doit-workspace")
URL = "https://www.usegpt.myorg"
PROJECT = "auto-sso-test"

def sync_llm_wrapper(bc, prompt: str) -> str:
    """
    Synchronous wrapper for the async LLM client.
    Must be used when the Orchestrator loop is running synchronously.
    """
    try:
        loop = asyncio.get_event_loop()
        # If the loop is closed (or doesn't exist), create a new one
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(async_llm_client(bc, prompt))
    except Exception as e:
        print(f"❌ Sync LLM Wrapper Error: {e}")
        raise

def test_step4():
    print("="*60)
    print("BABY STEP 4: Full Orchestrator Loop Integration")
    print("="*60)

    # 1. Initialize Browser Orchestrator (Async infrastructure)
    print("🚀 1. Initializing Browser Orchestrator...")
    orch = Orchestrator(WORKSPACE)
    
    # We run the browser setup in a temporary event loop since this script is sync
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        # Open Session & Navigate
        loop.run_until_complete(orch.open_chat_session(PROJECT))
        loop.run_until_complete(orch.navigate(URL))
        
        bc = orch.browser
        ready = loop.run_until_complete(bc.wait_for_prompt_box(timeout_ms=60000))
        if not ready:
            print("❌ Chat interface not ready.")
            return

        print("✅ Browser ready and session active.")

        # 2. Initialize Agent Orchestrator (Sync Loop)
        # We pass a lambda that captures the browser controller 'bc'
        agent = AgentOrchestrator(
            workspace_dir=WORKSPACE,
            llm_client=lambda prompt: sync_llm_wrapper(bc, prompt)
        )

        # 3. Run the Agent
        print("\n🤖 2. Starting Agent Orchestrator Loop...")
        print("   (Watch the browser: Agent is thinking and sending prompts)")
        
        goal_query = "Reply with a JSON object. Set tool_name to 'ack' and goal_status to 'completed'. Do not perform any actual tool execution."
        
        result = agent.run(goal=goal_query, project=PROJECT, max_steps=3)

        print(f"\n🏁 Agent Result: {result}")
        
        if result['status'] == 'completed':
            print("✅ TEST PASSED: Agent loop completed successfully!")
        else:
            print(f"⚠️ Agent loop finished with status: {result['status']}")

        # 4. Verify SQLite Logs
        print("\n🔍 3. Verifying SQLite Audit Logs...")
        db_path = WORKSPACE / "sqlite" / "doit_state.db"
        if db_path.exists():
            conn = sqlite3.connect(str(db_path))
            cursor = conn.execute("SELECT count(*) FROM steps WHERE goal_id = ?", (result['goal_id'],))
            count = cursor.fetchone()[0]
            print(f"   Found {count} logged steps for this goal.")
            
            cursor = conn.execute("SELECT tool_name, result FROM steps WHERE goal_id = ?", (result['goal_id'],))
            for row in cursor.fetchall():
                print(f"   - Tool: {row[0]} | Result: {row[1][:50]}...")
        else:
            print("   ❌ State DB not found.")

    except Exception as e:
        print(f"\n❌ Integration Test Failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n🔒 Closing browser session...")
        loop.run_until_complete(orch.close_browser())
        loop.close()

if __name__ == "__main__":
    test_step4()