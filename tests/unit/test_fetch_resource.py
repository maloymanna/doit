#!/usr/bin/env python3
"""Test browser_fetch_resource: Fetch direct PDF URL and save locally (no inline display)."""
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

def browser_fetch_resource(params, **ctx):
    """
    Fetches a direct resource URL (PDF, image, etc.) and saves to project dir.
    Uses browser's fetch() to preserve auth/cookies from current session.
    """
    url = params.get("url")
    save_path = params.get("save_path")
    timeout_ms = params.get("timeout_ms", 30000)
    
    if not url or not save_path:
        return {"status": "error", "output": "Missing 'url' or 'save_path'"}
    
    proj_dir = ctx["project_dir"]
    target = Path(save_path) if Path(save_path).is_absolute() else proj_dir / save_path
    if not str(target.resolve()).startswith(str(proj_dir.resolve())):
        return {"status": "error", "output": "save_path outside sandbox"}
    target.parent.mkdir(parents=True, exist_ok=True)
    
    page = ctx["controller"].page
    
    async def _fetch():
        # Use page's request context to inherit session cookies/auth
        response = await page.request.get(url, timeout=timeout_ms)
        if not response.ok:
            return {"status": "error", "output": f"HTTP {response.status}: {response.url}"}
        
        # Get raw bytes (works for PDF, images, binaries)
        body = await response.body()
        
        # Extract filename from Content-Disposition or URL
        content_disp = response.headers.get("content-disposition", "")
        if "filename=" in content_disp:
            import re
            match = re.search(r'filename\*=UTF-8\'\'([^\s;]+)|filename="([^"]+)"|filename=([^\s;]+)', content_disp)
            filename = (match.group(1) or match.group(2) or match.group(3)) if match else None
        else:
            from urllib.parse import urlparse, unquote
            filename = unquote(Path(urlparse(url).path).name) or "downloaded_resource"
        
        save_path_final = target if target.suffix else target / filename
        if save_path_final.is_dir():
            save_path_final = save_path_final / filename
        
        # Write binary content
        with open(save_path_final, "wb") as f:
            f.write(body)
        
        return {"status": "ok", "output": f"Saved {filename} to {save_path_final}", "filename": filename}
    
    return _run_coro(ctx["loop"], _fetch())

WORKSPACE = Path("~/Documents/02-learn/dev/doit-workspace").expanduser()
PROJECT = "auto-sso-test"  # Reuse persistent context

def test_fetch_resource():
    print("="*60)
    print("TEST: browser_fetch_resource (Direct PDF Download)")
    print("="*60)
    
    # Manual loop management (NOT asyncio.run) for _run_coro compatibility
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        orch = Orchestrator(WORKSPACE)
        loop.run_until_complete(orch.open_chat_session(PROJECT))
        bc = orch.browser
        
        proj_dir = WORKSPACE / "projects" / PROJECT
        proj_dir.mkdir(parents=True, exist_ok=True)
        
        disp = ActionDispatcher(WORKSPACE, proj_dir, controller=bc, loop=loop)
        disp.autonomy = 2  # Permissive for testing
        disp.whitelist = []
        
        # Register tools
        disp.register("browser_navigate", browser_navigate)
        disp.register("browser_fetch_resource", browser_fetch_resource)
        
        # Test: Fetch the dummy PDF directly (bypasses inline browser display)
        print("\n📥 Fetching dummy.pdf via browser_fetch_resource...")
        res = disp.dispatch({
            "tool_name": "browser_fetch_resource",
            "parameters": {
                "url": "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf",
                "save_path": "output/dummy_fetched.pdf"
            }
        })
        print(f"   Fetch result: {res}")
        
        if res.get("status") == "ok":
            pdf_file = proj_dir / "output" / "dummy_fetched.pdf"
            if pdf_file.exists():
                # Verify it's a valid PDF by checking header
                with open(pdf_file, "rb") as f:
                    header = f.read(4)
                if header == b"%PDF":
                    file_size = pdf_file.stat().st_size
                    print(f"✅ SUCCESS: Valid PDF saved ({file_size} bytes)")
                    print(f"   Location: {pdf_file}")
                else:
                    print(f"⚠️ File exists but invalid PDF header: {header}")
            else:
                print("⚠️ Downloaded file not found at expected path")
                # List output dir for debugging
                out_dir = proj_dir / "output"
                if out_dir.exists():
                    print(f"   Output dir contents: {[f.name for f in out_dir.iterdir()]}")
        else:
            print(f"⚠️ Fetch failed: {res.get('output')}")
        
        print("\n✅ TEST COMPLETED")
        
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
    test_fetch_resource()