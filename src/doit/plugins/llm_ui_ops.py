# src/doit/plugins/llm_ui_ops.py [v1.1]
"""LLM interface-specific tools (orchestrator-only, NOT exposed to web LLM)."""
import asyncio
from pathlib import Path
from typing import Dict, Any

def _run_coro(loop: asyncio.AbstractEventLoop, coro):
    if loop.is_running():
        return asyncio.run_coroutine_threadsafe(coro, loop).result()
    return loop.run_until_complete(coro)

def llm_attach_file(params: Dict[str, Any], **ctx) -> Dict[str, Any]:
    """Attach file(s) to LLM prompt area via paper clip button."""
    file_paths = params.get("file_paths")
    timeout_ms = params.get("timeout_ms", 10000)
    
    if not file_paths:
        return {"status": "error", "output": "Missing 'file_paths' parameter"}
    
    if isinstance(file_paths, str):
        file_paths = [file_paths]
    
    proj_dir = ctx["project_dir"]
    resolved_paths = []
    for fp in file_paths:
        target = Path(fp) if Path(fp).is_absolute() else proj_dir / fp
        if not str(target.resolve()).startswith(str(proj_dir.resolve())):
            return {"status": "error", "output": f"Path outside sandbox: {fp}"}
        if not target.exists():
            return {"status": "error", "output": f"File not found: {target}"}
        resolved_paths.append(str(target.resolve()))
    
    # Operates on chat_page (Tab A), not workspace_page
    ctrl = ctx["controller"]
    page = getattr(ctrl, "chat_page", None) or ctrl.page
    
    async def _attach():
        # Safer pattern: trigger click INSIDE expect_file_chooser context
        async with page.expect_file_chooser(timeout=timeout_ms) as fc_info:
            await page.get_by_label("Attach file").first.click()
        file_chooser = await fc_info.value
        await file_chooser.set_files(resolved_paths)
        return {"status": "ok", "output": f"Attached {len(resolved_paths)} file(s)"}
    
    return _run_coro(ctx["loop"], _attach())