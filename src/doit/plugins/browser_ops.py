# src/doit/plugins/browser_ops.py [v2.1]
"""Low-level deterministic browser tools for Phase 7 UCs (Multi-Page Routing)."""
import asyncio
from pathlib import Path
from typing import Dict, Any, List

def _run_coro(loop: asyncio.AbstractEventLoop, coro):
    """Execute async coroutine safely whether loop is running or not."""
    if loop.is_running():
        fut = asyncio.run_coroutine_threadsafe(coro, loop)
        return fut.result()
    return loop.run_until_complete(coro)

def _get_tool_page(ctx: Dict) -> Any:
    """Resolve target page: workspace_page > fallback to chat page."""
    ctrl = ctx["controller"]
    return getattr(ctrl, "workspace_page", None) or ctrl.page

def browser_navigate(params: Dict[str, Any], **ctx) -> Dict[str, Any]:
    page = _get_tool_page(ctx)
    url = params.get("url")
    if not url: return {"status": "error", "output": "Missing 'url' parameter"}
    timeout = params.get("timeout_ms", 30000)

    async def _nav():
        await page.goto(url, timeout=timeout, wait_until="domcontentloaded")
        return {"status": "ok", "output": f"Navigated to {url}"}

    return _run_coro(ctx["loop"], _nav())

def browser_fill(params: Dict[str, Any], **ctx) -> Dict[str, Any]:
    page = _get_tool_page(ctx)
    selector = params.get("selector")
    value = params.get("value")
    if not selector or value is None: return {"status": "error", "output": "Missing 'selector' or 'value'"}

    async def _fill():
        await page.fill(selector, str(value))
        return {"status": "ok", "output": f"Filled '{value}' into {selector}"}

    return _run_coro(ctx["loop"], _fill())

def browser_click_text(params: Dict[str, Any], **ctx) -> Dict[str, Any]:
    page = _get_tool_page(ctx)
    text = params.get("text")
    exact = params.get("exact", False)
    if not text: return {"status": "error", "output": "Missing 'text' parameter"}

    async def _click():
        locator = page.get_by_text(text, exact=exact)
        await locator.first.click()
        return {"status": "ok", "output": f"Clicked element with text '{text}'"}

    return _run_coro(ctx["loop"], _click())

def browser_wait_for_element(params: Dict[str, Any], **ctx) -> Dict[str, Any]:
    page = _get_tool_page(ctx)
    selector = params.get("selector")
    timeout_ms = params.get("timeout_ms", 10000)
    state = params.get("state", "visible")
    if not selector: return {"status": "error", "output": "Missing 'selector' parameter"}

    async def _wait():
        await page.wait_for_selector(selector, state=state, timeout=timeout_ms)
        return {"status": "ok", "output": f"Element '{selector}' is {state}"}

    return _run_coro(ctx["loop"], _wait())

def browser_screenshot(params: Dict[str, Any], **ctx) -> Dict[str, Any]:
    page = _get_tool_page(ctx)
    path = params.get("path")
    if not path: return {"status": "error", "output": "Missing 'path' parameter"}
    
    proj_dir = ctx["project_dir"]
    target_path = Path(path) if Path(path).is_absolute() else proj_dir / path
    if not str(target_path.resolve()).startswith(str(proj_dir.resolve())):
        return {"status": "error", "output": "Screenshot path outside project sandbox"}
    target_path.parent.mkdir(parents=True, exist_ok=True)

    selector = params.get("selector")
    full_page = params.get("full_page", True)
    timeout_ms = params.get("timeout_ms", 10000)

    async def _cap():
        await page.wait_for_load_state("networkidle", timeout=timeout_ms)
        if selector:
            el = await page.query_selector(selector)
            if not el: return {"status": "error", "output": f"Selector not found: {selector}"}
            await el.screenshot(path=str(target_path), timeout=timeout_ms)
        else:
            await page.screenshot(path=str(target_path), full_page=full_page, timeout=timeout_ms)
        return {"status": "ok", "output": f"Screenshot saved to {target_path}"}

    return _run_coro(ctx["loop"], _cap())

def browser_trigger_download(params: Dict[str, Any], **ctx) -> Dict[str, Any]:
    page = _get_tool_page(ctx)
    selector = params.get("selector")
    download_dir = params.get("download_dir")
    timeout_ms = params.get("timeout_ms", 30000)
    
    if not selector: return {"status": "error", "output": "Missing 'selector' parameter"}
    if not download_dir: return {"status": "error", "output": "Missing 'download_dir' parameter"}
    
    proj_dir = ctx["project_dir"]
    target_dir = Path(download_dir) if Path(download_dir).is_absolute() else proj_dir / download_dir
    if not str(target_dir.resolve()).startswith(str(proj_dir.resolve())):
        return {"status": "error", "output": "download_dir outside project sandbox"}
    target_dir.mkdir(parents=True, exist_ok=True)

    async def _dl():
        await page.context.set_default_timeout(timeout_ms)
        async with page.expect_download(timeout=timeout_ms) as dl_info:
            await page.click(selector, timeout=timeout_ms)
        download = await dl_info.value
        filename = download.suggested_filename or "downloaded_file"
        save_path = target_dir / filename
        await download.save_as(str(save_path))
        return {"status": "ok", "output": f"Downloaded {filename} to {save_path}", "filename": filename}

    return _run_coro(ctx["loop"], _dl())

def browser_upload_files(params: Dict[str, Any], **ctx) -> Dict[str, Any]:
    page = _get_tool_page(ctx)
    selector = params.get("selector")
    file_paths = params.get("file_paths")
    
    if not selector: return {"status": "error", "output": "Missing 'selector' parameter"}
    if not file_paths: return {"status": "error", "output": "Missing 'file_paths' parameter"}
    
    if isinstance(file_paths, str):
        file_paths = [file_paths]
    
    proj_dir = ctx["project_dir"]
    resolved_paths = []
    for fp in file_paths:
        target = Path(fp) if Path(fp).is_absolute() else proj_dir / fp
        if not str(target.resolve()).startswith(str(proj_dir.resolve())):
            return {"status": "error", "output": f"File path outside project sandbox: {fp}"}
        if not target.exists():
            return {"status": "error", "output": f"File not found: {target}"}
        resolved_paths.append(str(target.resolve()))

    async def _up():
        await page.set_input_files(selector, resolved_paths)
        return {"status": "ok", "output": f"Uploaded {len(resolved_paths)} file(s)"}

    return _run_coro(ctx["loop"], _up())