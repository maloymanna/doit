# src/doit/plugins/file_ops.py [NEW v1]
"""File operation tools for the agent."""
from pathlib import Path
from typing import Dict, Any

FILE_READ_SCHEMA = {
    "type": "object",
    "properties": {"path": {"type": "string"}},
    "required": ["path"],
    "additionalProperties": False
}

def file_read(params: Dict[str, Any], workspace: Path, **ctx) -> Dict[str, Any]:
    """Reads content from a local file path."""
    try:
        # Resolve relative to workspace or absolute
        target = workspace / params["path"] if not Path(params["path"]).is_absolute() else Path(params["path"])
        if not target.exists():
            return {"status": "error", "output": f"File not found: {target}"}
        return {"status": "ok", "output": target.read_text(encoding="utf-8")}
    except Exception as e:
        return {"status": "error", "output": str(e)}

FILE_WRITE_SCHEMA = {
    "type": "object",
    "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
    "required": ["path", "content"],
    "additionalProperties": False
}

def file_write(params: Dict[str, Any], workspace: Path, **ctx) -> Dict[str, Any]:
    """Writes content to a local file path."""
    try:
        target = workspace / params["path"] if not Path(params["path"]).is_absolute() else Path(params["path"])
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(params["content"], encoding="utf-8")
        return {"status": "ok", "output": f"Successfully wrote {len(params['content'])} chars to {target}"}
    except Exception as e:
        return {"status": "error", "output": str(e)}