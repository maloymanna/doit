# src/doit/plugins/file_ops.py [v1.7]
"""File operation tools for the agent - REAL EXECUTION (Project-Scoped)."""
from pathlib import Path
from typing import Dict, Any

FILE_READ_SCHEMA = {
    "type": "object",
    "properties": {"path": {"type": "string"}},
    "required": ["path"],
    "additionalProperties": False
}

FILE_WRITE_SCHEMA = {
    "type": "object",
    "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
    "required": ["path", "content"],
    "additionalProperties": False
}

def file_read(params: Dict[str, Any], project_dir: Path, **ctx) -> Dict[str, Any]:
    try:
        target = params.get("path") or params.get("file_path")
        if not target: return {"status": "error", "output": "Missing 'path' parameter"}
        if not Path(target).is_absolute():
            target = project_dir / target
        else:
            target = Path(target).resolve()
            
        proj_resolved = project_dir.resolve()
        if not str(target).startswith(str(proj_resolved)):
            return {"status": "error", "output": "Path outside project sandbox"}
        if not target.exists():
            return {"status": "error", "output": f"File not found: {target.relative_to(proj_resolved)}"}
            
        content = target.read_text(encoding="utf-8")
        return {"status": "ok", "output": content[:4000] + ("...[truncated]" if len(content) > 4000 else "")}
    except Exception as e:
        return {"status": "error", "output": str(e)}

def file_write(params: Dict[str, Any], project_dir: Path, **ctx) -> Dict[str, Any]:
    try:
        target = params.get("path") or params.get("file_path")
        content = params.get("content")
        if not target or content is None: return {"status": "error", "output": "Missing 'path' or 'content'"}
        if not Path(target).is_absolute():
            target = project_dir / target
        else:
            target = Path(target).resolve()
            
        if not str(target).startswith(str(project_dir.resolve())):
            return {"status": "error", "output": "Path outside project sandbox"}
            
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return {"status": "ok", "output": f"Written {len(content)} chars to {target.relative_to(project_dir)}"}
    except Exception as e:
        return {"status": "error", "output": str(e)}