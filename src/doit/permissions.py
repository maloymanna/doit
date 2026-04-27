"""Permission system for workspace security."""

from pathlib import Path
from typing import Optional


class PermissionError(Exception):
    """Permission related errors."""
    pass


class Permissions:
    """Enforce workspace boundaries and autonomy modes."""
    
    def __init__(self, workspace_root: Path, autonomy_mode: int = 0):
        self.workspace_root = Path(workspace_root).resolve()
        self.readonly_dir = self.workspace_root / 'readonly_input'
        self.autonomy_mode = autonomy_mode
    
    def validate_path(self, path: Path, operation: str = 'read') -> Path:
        """
        Validate that path is within workspace and respects readonly rules.
        
        Args:
            path: Path to validate
            operation: 'read', 'write', 'delete'
        
        Returns:
            Resolved path if valid
        
        Raises:
            PermissionError: If path is outside workspace or violates readonly
        """
        resolved = Path(path).resolve()
        
        # Check 1: Must be within workspace
        try:
            resolved.relative_to(self.workspace_root)
        except ValueError:
            raise PermissionError(
                f"Path outside workspace: {resolved}\n"
                f"Workspace: {self.workspace_root}"
            )
        
        # Check 2: readonly_input is read-only
        if operation in ('write', 'delete'):
            try:
                resolved.relative_to(self.readonly_dir)
                raise PermissionError(
                    f"Cannot {operation} in readonly_input: {resolved}\n"
                    f"readonly_input is protected."
                )
            except ValueError:
                pass  # Not in readonly_input, good
        
        return resolved
    
    def require_approval(self, operation: str, details: str) -> bool:
        """
        Check if operation requires approval based on autonomy mode.
        
        Args:
            operation: e.g., 'write', 'delete', 'git_push'
            details: Description of what will be done
        
        Returns:
            True if approved, False if denied
        
        Note: This would integrate with user input in CLI
        """
        # Mode 0: Everything requires approval
        if self.autonomy_mode == 0:
            return self._ask_approval(operation, details)
        
        # Mode 1: Reads auto-approved, writes need approval
        if self.autonomy_mode == 1:
            if operation == 'read':
                return True
            return self._ask_approval(operation, details)
        
        # Mode 2: Reads/writes auto-approved, destructive ops need approval
        if self.autonomy_mode == 2:
            destructive_ops = ['delete', 'git_push', 'git_reset_hard']
            if operation in destructive_ops:
                return self._ask_approval(operation, details)
            return True
        
        return False
    
    def _ask_approval(self, operation: str, details: str) -> bool:
        """Ask user for approval (placeholder for CLI integration)."""
        # This will be replaced with actual CLI prompt
        print(f"\n⚠️  Approval Required: {operation}")
        print(f"   {details}")
        response = input("   Approve? (y/N): ").lower()
        return response == 'y'