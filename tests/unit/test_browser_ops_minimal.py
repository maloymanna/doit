#!/usr/bin/env python3
"""Minimal browser ops test: sync tools + async Playwright, NO asyncio.run()."""
import sys
import asyncio
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from doit.orchestrator import Orchestrator
from doit.core.action_dispatcher import ActionDispatcher
from doit.utils.session_logger import init_session_logger, logger

# === Sync tool helpers (NO async def, return dicts) ===
def _run_coro(loop, coro):
    """Bridge sync tool to async Playwright. Works when loop is NOT running."""
    return loop.run_until_complete(coro)

def browser_navigate(params, **ctx):
    page = ctx["controller"].page
    url = params.get("url")
    if not url: return {"status": "error", "output": "Missing 'url'"}
    timeout = params.get("timeout_ms", 30000)
    async def _nav():
        await page.goto(url, timeout=timeout, wait_until="domcontentloaded")
        return {"status": "ok", "output": f"Navigated to {url}"}
    return _run_coro(ctx["loop"], _nav())

def browser_screenshot(params, **ctx):
    page = ctx["controller"].page
    path = params.get("path")
    if not path: return {"status": "error", "output": "Missing 'path'"}
    proj_dir = ctx["project_dir"]
    target = Path(path) if Path(path).is_absolute() else proj_dir / path
    if not str(target.resolve()).startswith(str(proj_dir.resolve())):
        return {"status": "error", "output": "Path outside sandbox"}
    target.parent.mkdir(parents=True, exist_ok=True)
    timeout = params.get("timeout_ms", 10000)
    async def _cap():
        await page.wait_for_load_state("networkidle", timeout=timeout)
        await page.screenshot(path=str(target), full_page=True, timeout=timeout)
        return {"status": "ok", "output": f"Saved to {target}"}
    return _run_coro(ctx["loop"], _cap())

WORKSPACE = Path("~/Documents/02-learn/dev/doit-workspace").expanduser()
PROJECT = "auto-sso-test"

def test_minimal():
    """NOT async: use manual loop management for _run_coro compatibility."""
    print("="*60)
    print("MINIMAL TEST: Single Page, No LLM")
    print("="*60)
    
    # Create loop manually (NOT running yet)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        # Run async setup
        orch = Orchestrator(WORKSPACE)
        loop.run_until_complete(orch.open_chat_session(PROJECT))
        bc = orch.browser
        
        proj_dir = WORKSPACE / "projects" / PROJECT
        proj_dir.mkdir(parents=True, exist_ok=True)
        
        disp = ActionDispatcher(WORKSPACE, proj_dir, controller=bc, loop=loop)
        disp.autonomy = 2
        disp.whitelist = []
        
        # Register tools
        disp.register("browser_navigate", browser_navigate)
        disp.register("browser_screenshot", browser_screenshot)
        
        # 1. Navigate FIRST
        print("\n🔗 Navigating to httpbin.org...")
        res_nav = disp.dispatch({
            "tool_name": "browser_navigate",
            "parameters": {"url": "https://httpbin.org/html"}
        })
        print(f"   Result: {res_nav}")
        if res_nav.get("status") != "ok":
            print("⚠️ Navigate failed"); return
        
        # 2. THEN screenshot
        print("\n📸 Taking screenshot...")
        res_ss = disp.dispatch({
            "tool_name": "browser_screenshot",
            "parameters": {"path": "output/minimal_test.png"}
        })
        print(f"   Result: {res_ss}")
        
        if res_ss.get("status") == "ok":
            ss_file = proj_dir / "output" / "minimal_test.png"
            if ss_file.exists() and ss_file.stat().st_size > 0:
                print(f"✅ SUCCESS: Screenshot saved to {ss_file}")
            else:
                print("⚠️ File missing or empty")
        
    except Exception as e:
        print(f"\n❌ Failed: {e}")
        logger.error("Test failed: %s", e, exc_info=False)
        import traceback; traceback.print_exc()
    finally:
        print("\n🔒 Closing...")
        try:
            loop.run_until_complete(orch.close_browser())
        except:
            pass
        loop.close()  # Critical: release loop resources

if __name__ == "__main__":
    init_session_logger(WORKSPACE)
    test_minimal()  # Call sync function, NOT asyncio.run()