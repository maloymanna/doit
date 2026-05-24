#!/usr/bin/env python3
"""Minimal test: browser_trigger_download via direct dispatch (1 page, no LLM)."""
import sys
import asyncio
import http.server
import socketserver
import threading
import time
import os
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

def browser_trigger_download(params, **ctx):
    """
    Clicks a selector that triggers a download, saves file to project-relative dir.
    Python Playwright API notes:
    - context.set_default_timeout() is SYNC → do NOT await
    - expect_download yields AsyncEventInfo; .value is a COROUTINE → MUST await
    """
    page = ctx["controller"].page
    selector = params.get("selector")
    download_dir = params.get("download_dir")
    timeout_ms = params.get("timeout_ms", 30000)
    
    if not selector: return {"status": "error", "output": "Missing 'selector'"}
    if not download_dir: return {"status": "error", "output": "Missing 'download_dir'"}
    
    proj_dir = ctx["project_dir"]
    target_dir = Path(download_dir) if Path(download_dir).is_absolute() else proj_dir / download_dir
    if not str(target_dir.resolve()).startswith(str(proj_dir.resolve())):
        return {"status": "error", "output": "download_dir outside sandbox"}
    target_dir.mkdir(parents=True, exist_ok=True)
    
    async def _dl():
        # FIX #1: set_default_timeout is SYNC, do NOT await
        page.context.set_default_timeout(timeout_ms)
        
        # FIX #2: Python Playwright expect_download yields AsyncEventInfo
        # The .value property is a COROUTINE that resolves to Download → MUST await
        async with page.expect_download(timeout=timeout_ms) as download_info:
            await page.click(selector, timeout=timeout_ms)
        
        download = await download_info.value  # ✅ Await the coroutine to get Download object
        if download is None:
            return {"status": "error", "output": "Download event not triggered"}
        
        filename = download.suggested_filename or "downloaded_file"
        save_path = target_dir / filename
        await download.save_as(str(save_path))  # ✅ save_as() IS async → await OK
        return {"status": "ok", "output": f"Downloaded {filename} to {save_path}", "filename": filename}
    
    return _run_coro(ctx["loop"], _dl())

WORKSPACE = Path("~/Documents/02-learn/dev/doit-workspace").expanduser()
PROJECT = "auto-sso-test"

def _start_local_server(html_path: Path, port: int = 8766):
    """Simple HTTP server to serve test HTML."""
    original_cwd = os.getcwd()
    os.chdir(str(html_path.parent))
    handler = http.server.SimpleHTTPRequestHandler
    httpd = socketserver.TCPServer(("", port), handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.5)
    return httpd, original_cwd

def test_download():
    print("="*60)
    print("MINIMAL TEST: browser_trigger_download (1 Page, No LLM)")
    print("="*60)
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
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
        disp.register("browser_trigger_download", browser_trigger_download)
        
        # Test 1: Navigate to external page
        print("\n🔗 Navigating to external test page...")
        res_nav = disp.dispatch({
            "tool_name": "browser_navigate",
            "parameters": {"url": "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"}
        })
        print(f"   Navigate: {res_nav}")
        
        # Test 2: Local page with explicit download link
        print("\n📥 Testing browser_trigger_download with local page...")
        test_html = proj_dir / "test_download.html"
        test_html.write_text("""<!DOCTYPE html><html><head><title>Download Test</title></head><body>
  <h1>Download Test</h1>
  <a id="dl-link" href="data:text/plain;charset=utf-8,Test%20download%20content" download="test_download.txt">
    Click to Download Test File
  </a>
</body></html>""", encoding="utf-8")
        
        httpd, orig_cwd = _start_local_server(test_html, port=8766)
        test_url = "http://localhost:8766/test_download.html"
        
        res_nav2 = disp.dispatch({
            "tool_name": "browser_navigate",
            "parameters": {"url": test_url}
        })
        print(f"   Navigate: {res_nav2}")
        
        # Small delay to ensure page is fully loaded
        time.sleep(1)
        
        res_dl = disp.dispatch({
            "tool_name": "browser_trigger_download",
            "parameters": {
                "selector": "#dl-link",
                "download_dir": "output"
            }
        })
        print(f"   Download: {res_dl}")
        
        if res_dl.get("status") == "ok":
            dl_file = proj_dir / "output" / "test_download.txt"
            if dl_file.exists():
                content = dl_file.read_text(encoding="utf-8", errors="ignore")
                print(f"✅ Downloaded file content: '{content}'")
                if "Test download content" in content:
                    print("✅ VERIFIED: Download tool works correctly")
            else:
                print("⚠️ Downloaded file not found at expected path")
                out_dir = proj_dir / "output"
                if out_dir.exists():
                    print(f"   Output dir contents: {list(out_dir.iterdir())}")
        else:
            print(f"⚠️ Download failed: {res_dl.get('output')}")
        
        # Cleanup server
        os.chdir(orig_cwd)
        httpd.shutdown()
        
        print("\n✅ UNIT TEST COMPLETED")
        
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
        loop.close()

if __name__ == "__main__":
    init_session_logger(WORKSPACE)
    test_download()