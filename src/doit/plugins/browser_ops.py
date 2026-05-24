# src/doit/plugins/browser_ops.py [v2.3]
"""Browser tools v2.3: Routes all operations to lazy-initialized Tab B."""
import asyncio
from pathlib import Path
from typing import Dict, Any
from urllib.parse import urlparse, unquote
import re

def _run_coro(loop: asyncio.AbstractEventLoop, coro):
    if loop.is_running():
        return asyncio.run_coroutine_threadsafe(coro, loop).result()
    return loop.run_until_complete(coro)

async def _get_ws_page(ctx):
    """Resolve workspace page (Tab B) via lazy initialization."""
    return await ctx["controller"]._ensure_workspace_page()

def browser_navigate(params, **ctx):
    url = params.get("url")
    if not url: return {"status": "error", "output": "Missing 'url'"}
    timeout = params.get("timeout_ms", 30000)
    async def _nav():
        page = await _get_ws_page(ctx)
        await page.goto(url, timeout=timeout, wait_until="domcontentloaded")
        return {"status": "ok", "output": f"Navigated to {url}"}
    return _run_coro(ctx["loop"], _nav())

def browser_fill(params, **ctx):
    selector = params.get("selector")
    value = params.get("value")
    if not selector or value is None: return {"status": "error", "output": "Missing 'selector' or 'value'"}
    async def _fill():
        page = await _get_ws_page(ctx)
        await page.fill(selector, str(value))
        return {"status": "ok", "output": f"Filled '{value}' into {selector}"}
    return _run_coro(ctx["loop"], _fill())

def browser_click_text(params, **ctx):
    text = params.get("text")
    exact = params.get("exact", False)
    if not text: return {"status": "error", "output": "Missing 'text' parameter"}
    async def _click():
        page = await _get_ws_page(ctx)
        await page.get_by_text(text, exact=exact).first.click()
        return {"status": "ok", "output": f"Clicked element with text '{text}'"}
    return _run_coro(ctx["loop"], _click())

def browser_wait_for_element(params, **ctx):
    selector = params.get("selector")
    timeout_ms = params.get("timeout_ms", 10000)
    state = params.get("state", "visible")
    if not selector: return {"status": "error", "output": "Missing 'selector' parameter"}
    async def _wait():
        page = await _get_ws_page(ctx)
        await page.wait_for_selector(selector, state=state, timeout=timeout_ms)
        return {"status": "ok", "output": f"Element '{selector}' is {state}"}
    return _run_coro(ctx["loop"], _wait())

def browser_screenshot(params, **ctx):
    # FIX: Accept both 'path' (correct) and 'save_path' (LLM hallucination) to prevent loops
    path = params.get("path") or params.get("save_path")

    if not path:
        return {"status": "error", "output": "Missing 'path' parameter. Expected 'path' (e.g., 'output/file.png')."}
    
    proj_dir = ctx["project_dir"]
    target = Path(path) if Path(path).is_absolute() else proj_dir / path
    
    # Sandbox validation
    if not str(target.resolve()).startswith(str(proj_dir.resolve())):
        return {"status": "error", "output": "Screenshot path outside sandbox"}
    target.parent.mkdir(parents=True, exist_ok=True)
    timeout = params.get("timeout_ms", 10000)

    async def _cap():
        page = await _get_ws_page(ctx)
        await page.wait_for_load_state("networkidle", timeout=timeout)
        await page.screenshot(path=str(target), full_page=True, timeout=timeout)
        return {"status": "ok", "output": f"Screenshot saved to {target}"}

    return _run_coro(ctx["loop"], _cap())

def browser_trigger_download(params, **ctx):
    # FIX: Accept common aliases to prevent LLM guessing loops
    selector = params.get("selector") or params.get("button") or params.get("css_selector")
    download_dir = params.get("download_dir")
    timeout_ms = params.get("timeout_ms", 30000)

    if not selector:
        return {"status": "error", "output": "Missing 'selector' parameter. Expected 'selector' (e.g., '#download-btn')."}
    if not download_dir:
        return {"status": "error", "output": "Missing 'download_dir' parameter. Expected 'download_dir' (e.g., 'output/downloads')."}
    
    proj_dir = ctx["project_dir"]
    target_dir = Path(download_dir) if Path(download_dir).is_absolute() else proj_dir / download_dir
    if not str(target_dir.resolve()).startswith(str(proj_dir.resolve())):
        return {"status": "error", "output": "download_dir outside sandbox"}
    target_dir.mkdir(parents=True, exist_ok=True)

    async def _dl():
        page = await _get_ws_page(ctx)
        page.context.set_default_timeout(timeout_ms)
        async with page.expect_download(timeout=timeout_ms) as download_info:
            await page.click(selector, timeout=timeout_ms)
        download = await download_info.value
        if download is None: return {"status": "error", "output": "Download event not triggered"}
        filename = download.suggested_filename or "downloaded_file"
        save_path = target_dir / filename
        await download.save_as(str(save_path))
        return {"status": "ok", "output": f"Downloaded {filename} to {save_path}", "filename": filename}

    return _run_coro(ctx["loop"], _dl())

def browser_fetch_resource(params, **ctx):
    # FIX: Accept common aliases to prevent LLM guessing loops
    url = params.get("url") or params.get("resource_url") or params.get("link")
    save_path = params.get("save_path")
    timeout_ms = params.get("timeout_ms", 30000)

    if not url:
        return {"status": "error", "output": "Missing 'url' parameter. Expected 'url'."}
    if not save_path:
        return {"status": "error", "output": "Missing 'save_path' parameter. Expected 'save_path' (e.g., 'output/file.pdf')."}

    proj_dir = ctx["project_dir"]
    target = Path(save_path) if Path(save_path).is_absolute() else proj_dir / save_path
    if not str(target.resolve()).startswith(str(proj_dir.resolve())):
        return {"status": "error", "output": "save_path outside sandbox"}
    target.parent.mkdir(parents=True, exist_ok=True)

    async def _fetch():
        page = await _get_ws_page(ctx)
        response = await page.request.get(url, timeout=timeout_ms)
        if not response.ok:
            return {"status": "error", "output": f"HTTP {response.status}: {response.url}"}

        body = await response.body()
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

        with open(save_path_final, "wb") as f: f.write(body)
        return {"status": "ok", "output": f"Saved {filename} to {save_path_final}", "filename": filename}
        
    return _run_coro(ctx["loop"], _fetch())