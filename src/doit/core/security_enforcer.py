# src/doit/core/security_enforcer.py [NEW v1]
from pathlib import Path
from typing import Dict, Any

class SecurityEnforcer:
    def __init__(self, workspace_dir: Path):
        # Store absolute, resolved path for strict comparison
        self.workspace = workspace_dir.resolve()

    def validate_path(self, path_str: str) -> Path:
        p = Path(path_str)
        if not p.is_absolute():
            # Resolve relative to workspace if not absolute
            resolved = (self.workspace / p).resolve()
        else:
            resolved = p.resolve()

        # Block traversal & workspace escape
        if not str(resolved).startswith(str(self.workspace)):
            raise PermissionError(f"Path {resolved} escapes workspace boundary {self.workspace}")
        
        # Additional check for '..' in relative part (though resolve usually catches it)
        # We trust resolve() on modern Python, but explicit check adds safety
        if ".." in resolved.relative_to(self.workspace).parts:
            raise PermissionError(f"Path traversal detected in {resolved}")
            
        return resolved

    def validate_call(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Scans params for paths and validates them."""
        safe_params = {}
        for k, v in params.items():
            if "path" in k.lower() and isinstance(v, str):
                try:
                    safe_params[k] = str(self.validate_path(v))
                except PermissionError as e:
                    raise e
            else:
                safe_params[k] = v
        return safe_params