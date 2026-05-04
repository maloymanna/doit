# src/doit/plugins/high_level.py [NEW v1]
import difflib
from pathlib import Path
from typing import Dict, Any

EXCEL_DIFF_SCHEMA = {
    "type": "object",
    "properties": {
        "file1": {"type": "string"},
        "file2": {"type": "string"},
        "output": {"type": "string"}
    },
    "required": ["file1", "file2", "output"],
    "additionalProperties": False
}

def excel_diff(params: Dict[str, Any], **ctx) -> Dict[str, Any]:
    """UC6: Compare two CSV/TSV reports and output a diff summary."""
    try:
        def read_lines(p): return Path(p).read_text().splitlines()
        diff = list(difflib.unified_diff(read_lines(params["file1"]), read_lines(params["file2"]), n=0))
        Path(params["output"]).parent.mkdir(parents=True, exist_ok=True)
        Path(params["output"]).write_text("\n".join(diff), encoding="utf-8")
        return {"status": "ok", "output": f"Diff saved to {params['output']} ({len(diff)} changes)"}
    except Exception as e:
        return {"status": "error", "output": str(e)}

SCREENSHOT_SCHEMA = {
    "type": "object",
    "properties": {"path": {"type": "string"}, "full_page": {"type": "boolean"}},
    "required": ["path"], "additionalProperties": False
}

def screenshot_save(params: Dict[str, Any], **ctx) -> Dict[str, Any]:
    """UC3: Capture screenshot and save locally."""
    page = ctx.get("page")
    if not page: return {"status": "error", "output": "No browser context"}
    try:
        Path(params["path"]).parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=params["path"], full_page=params.get("full_page", False))
        return {"status": "ok", "output": f"Saved to {params['path']}"}
    except Exception as e:
        return {"status": "error", "output": str(e)}

EMAIL_DRAFT_SCHEMA = {
    "type": "object",
    "properties": {"template_path": {"type": "string"}, "updates": {"type": "string"}},
    "required": ["template_path", "updates"], "additionalProperties": False
}

def draft_email(params: Dict[str, Any], **ctx) -> Dict[str, Any]:
    """UC5: Load template, inject NL updates, return draft text."""
    try:
        template = Path(params["template_path"]).read_text(encoding="utf-8")
        # Simple placeholder replacement (expand to Jinja later)
        draft = template.replace("{{UPDATES}}", params["updates"])
        return {"status": "ok", "output": draft[:1000]}
    except Exception as e:
        return {"status": "error", "output": str(e)}