# src/doit/plugins/browser_ops.py [NEW v1]
from typing import Dict, Any

NAVIGATE_SCHEMA = {
    "type": "object",
    "properties": {"url": {"type": "string"}},
    "required": ["url"],
    "additionalProperties": False
}

SCRAPE_SCHEMA = {
    "type": "object",
    "properties": {
        "selector": {"type": "string"},
        "attribute": {"type": "string", "default": "innerText"},
        "full_page": {"type": "boolean", "default": False}
    },
    "required": [],
    "additionalProperties": False
}

def browser_navigate(params: Dict[str, Any], **ctx) -> Dict[str, Any]:
    page = ctx.get("page")
    if not page: 
        return {"status": "error", "output": "No browser page context provided"}
    try:
        page.goto(params["url"], wait_until="domcontentloaded", timeout=10000)
        return {"status": "ok", "output": f"Navigated to {params['url']}"}
    except Exception as e:
        return {"status": "error", "output": f"Navigation failed: {e}"}

def browser_scrape(params: Dict[str, Any], **ctx) -> Dict[str, Any]:
    page = ctx.get("page")
    if not page: 
        return {"status": "error", "output": "No browser page context provided"}
    try:
        selector = params.get("selector")
        attr = params.get("attribute", "innerText")
        
        if selector:
            el = page.query_selector(selector)
            if not el: 
                return {"status": "error", "output": f"Element missing: {selector}"}
            text = el.get_attribute(attr) if attr != "innerText" else el.inner_text()
        else:
            text = page.inner_text("body")
            
        return {"status": "ok", "output": str(text)[:3000]}
    except Exception as e:
        return {"status": "error", "output": f"Scrape failed: {e}"}