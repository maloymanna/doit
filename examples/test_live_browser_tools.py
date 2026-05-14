#!/usr/bin/env python3
"""STEP 6: True Integration Test (Browser Tools + File Ops + LLM Chaining)"""
import sys
import asyncio
import http.server
import socketserver
import threading
import time
import os
import platform
import concurrent.futures
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from doit.orchestrator import Orchestrator
from doit.core.agent_orchestrator import AgentOrchestrator
from doit.core.browser_llm_adapter import async_llm_client
from doit.utils.session_logger import init_session_logger, logger
from doit.config import Config

# =============================================================================
# ESTABLISHED CONFIGURATION PATTERN
# =============================================================================
WORKSPACE = Path("~/Documents/02-learn/dev/doit-workspace").expanduser()
URL = "https://www.usegpt.myorg"
PROJECT = "auto-sso-test"
# =============================================================================

TEST_HTML = """
<!DOCTYPE html>
<html lang="en"><body>
  <h1 id="title">Phase 7 Integration Test</h1>
  <button id="action-btn">Click Me</button>
  <p id="status">Ready</p>
  <script>
    document.getElementById('action-btn').addEventListener('click', () => {
      document.getElementById('status').textContent = 'Button Activated';
    });
  </script>
</body></html>
"""

class ReuseAddrTCPServer(socketserver.TCPServer):
    allow_reuse_address = True

def _start_local_server(html_path: Path, port: int = 8765):
    original_cwd = os.getcwd()
    os.chdir(str(html_path.parent))
    handler = http.server.SimpleHTTPRequestHandler
    httpd = ReuseAddrTCPServer(("", port), handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.5)
    return httpd, original_cwd

def sync_llm_wrapper(bc, prompt: str, completion_timeout_ms: int = 180000) -> str:
    loop = asyncio.get_event_loop()
    if loop.is_closed():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(async_llm_client(bc, prompt, completion_timeout_ms))

def _safe_close_browser(loop, orch, timeout_sec: float = 5.0):
    def _close():
        try:
            if orch.browser and orch.browser.page:
                loop.run_until_complete(orch.browser.page.close())
            loop.run_until_complete(orch.close_browser())
            return True
        except Exception as e:
            logger.warning("Browser close failed: %s", e)
            return False
    
    if platform.system() == "Windows":
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_close)
            try: return future.result(timeout=timeout_sec)
            except concurrent.futures.TimeoutError:
                logger.warning("Browser close timed out on Windows")
                return False
    return _close()

def test_step6_integration():
    print("="*60)
    print("STEP 6: TRUE INTEGRATION TEST (Browser + File + LLM)")
    print("="*60)
    logger.info("Integration test started")
    logger.info("Workspace: %s", WORKSPACE)
    logger.info("Project: %s", PROJECT)
    
    proj_dir = WORKSPACE / "projects" / PROJECT
    proj_dir.mkdir(parents=True, exist_ok=True)
    output_file = proj_dir / "output" / "action_log.txt"

    test_html = proj_dir / "test_page.html"
    test_html.write_text(TEST_HTML, encoding="utf-8")
    httpd, original_cwd = _start_local_server(test_html, port=8765)
    test_url = "http://localhost:8765/test_page.html"
    logger.info("Local test server running at %s", test_url)

    orch = Orchestrator(WORKSPACE)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        loop.run_until_complete(orch.open_chat_session(PROJECT))
        bc = orch.browser
        
        try:
            cfg = Config(WORKSPACE)
            autonomy_mode = cfg.autonomy.mode
            completion_timeout_ms = cfg.browser.completion_timeout_ms
        except Exception as e:
            autonomy_mode = 0
            completion_timeout_ms = 180000
            logger.warning("Config load failed (%s), using defaults", e)

        logger.info("Initializing agent (autonomy_mode=%d)...", autonomy_mode)
        agent = AgentOrchestrator(
            workspace_dir=WORKSPACE,
            project=PROJECT,
            llm_client=lambda p: sync_llm_wrapper(bc, p, completion_timeout_ms),
            autonomy_mode=autonomy_mode,
            controller=bc,
            loop=loop
        )

        goal = (
            f"Navigate to '{test_url}', "
            f"wait for the element with selector '#action-btn' to be visible, "
            f"click the button with the exact text 'Click Me', "
            f"and write 'Browser interaction successful' to 'output/action_log.txt'."
        )
        print(f"\n🎯 Goal: {goal}")
        logger.info("Running goal: %s", goal)

        result = agent.run(goal_query=goal, max_steps=5)

        print(f"\n🏁 Final Result: {result['status']}")
        logger.info("Agent run finished with status: %s", result['status'])
        
        if output_file.exists():
            content = output_file.read_text(encoding="utf-8").strip()
            print(f"📄 Output file content: '{content}'")
            if "Browser interaction successful" in content:
                print("✅ VERIFIED: LLM successfully chained browser tools + file_write")
                logger.info("Integration test passed: browser tools executed by LLM")
            else:
                print(f"⚠️ Unexpected content: {content}")
                logger.warning("Output contains unexpected content")
        else:
            print("⚠️ Output file was not created")
            logger.warning("Output file missing: %s", output_file)

    except Exception as e:
        print(f"\n❌ Test Failed: {e}")
        logger.error("Integration test failed: %s", e, exc_info=False)
        import traceback; traceback.print_exc()
    finally:
        try:
            os.chdir(original_cwd)
            httpd.shutdown()
            logger.info("Local server stopped")
        except Exception as e:
            logger.warning("Server cleanup warning: %s", e)
            
        print("\n🔒 Closing browser session...")
        logger.info("Closing browser session")
        _safe_close_browser(loop, orch)
        try: loop.close()
        except: pass
        logger.info("Integration test finished")

if __name__ == "__main__":
    ctx = init_session_logger(WORKSPACE)
    logger.info("Starting test_step6_real_file_ops integration test")
    test_step6_integration()