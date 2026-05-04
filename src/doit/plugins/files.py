# src/doit/plugins/files.py [MOD v1.1]
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
    "properties": {
        "path": {"type": "string"},
        "content": {"type": "string"},
        "mode": {"type": "string", "enum": ["write", "append"]}
    },
    "required": ["path", "content"],
    "additionalProperties": False
}

def file_read(params: Dict[str, Any], **ctx) -> Dict[str, Any]:
    try:
        content = Path(params["path"]).read_text(encoding="utf-8")
        return {"status": "ok", "output": content[:2000]}
    except Exception as e:
        return {"status": "error", "output": str(e)}

def file_write(params: Dict[str, Any], **ctx) -> Dict[str, Any]:
    try:
        p = Path(params["path"])
        p.parent.mkdir(parents=True, exist_ok=True)
        mode = "w" if params.get("mode", "write") == "write" else "a"
        # Fixed: Path.write_text() does not accept 'mode'. Use open() instead.
        with p.open(mode=mode, encoding="utf-8") as f:
            f.write(params["content"])
        return {"status": "ok", "output": f"Written to {p}"}
    except Exception as e:
        return {"status": "error", "output": str(e)}