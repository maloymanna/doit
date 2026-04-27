"""Permission system for workspace security and autonomy management."""

from pathlib import Path
from typing import Optional, List, Callable
from urllib.parse import urlparse
import fnmatch


class PermissionError(Exception):
    """Permission related errors."""
    pass


class Permissions:
    """
    Enforce workspace boundaries and autonomy modes.
    
    Features:
    - Path validation (no escape from workspace)
    - readonly_input protection
    - URL allowlist checking
    - Autonomy mode state machine (0, 1, 2)
    - Approval request mechanism
    """
    
    def __init__(self, workspace_root: Path, autonomy_mode: int = 0, allowlist: Optional[List[str]] = None):
        """
        Initialize permissions for a workspace.
        
        Args:
            workspace_root: Root directory of the workspace
            autonomy_mode: 0=strict, 1=moderate, 2=permissive
            allowlist: List of allowed URL patterns
        """
        self.workspace_root = Path(workspace_root).resolve()
        self.readonly_dir = self.workspace_root / 'readonly_input'
        self.autonomy_mode = autonomy_mode
        self.allowlist = allowlist or []
        self._approval_callback: Optional[Callable] = None
    
    def set_approval_callback(self, callback: Callable[[str, str], bool]):
        """
        Set a callback function for asking user approval.
        
        The callback should take (operation: str, details: str) and return bool.
        """
        self._approval_callback = callback
    
    # ========== Path Validation ==========
    
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
    
    def is_path_allowed(self, path: Path, operation: str = 'read') -> bool:
        """Return True if path operation is allowed (no exception)."""
        try:
            self.validate_path(path, operation)
            return True
        except PermissionError:
            return False
    
    # ========== URL Allowlist ==========
    
    def is_url_allowed(self, url: str) -> bool:
        """
        Check if URL is in allowlist.
        
        Supports wildcard patterns like:
        - https://usegpt.myorg
        - https://github.com/*
        - *://*.myorg/*
        """
        if not self.allowlist:
            return True  # No restrictions if allowlist is empty
        
        parsed = urlparse(url)
        normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        
        for pattern in self.allowlist:
            # Handle wildcard patterns
            if '*' in pattern:
                if fnmatch.fnmatch(normalized, pattern):
                    return True
            else:
                if normalized == pattern or url == pattern:
                    return True
            
            # Also check without trailing slash
            if pattern.endswith('/'):
                if normalized == pattern[:-1]:
                    return True
        
        return False
    
    def add_to_allowlist(self, pattern: str):
        """Add a URL pattern to the allowlist."""
        if pattern not in self.allowlist:
            self.allowlist.append(pattern)
    
    # ========== Autonomy Mode ==========
    
    def set_autonomy_mode(self, mode: int):
        """Change autonomy mode at runtime."""
        if mode not in [0, 1, 2]:
            raise ValueError(f"Invalid autonomy mode: {mode}. Must be 0, 1, or 2")
        self.autonomy_mode = mode
    
    def requires_approval(self, operation: str, details: str = "") -> bool:
        """
        Check if operation requires approval based on autonomy mode.
        
        Args:
            operation: e.g., 'read', 'write', 'delete', 'git_push', 'git_reset_hard'
            details: Description of what will be done
        
        Returns:
            True if operation is APPROVED, False if DENIED
        """
        # Destructive operations always require approval regardless of mode
        destructive_ops = ['delete', 'git_push', 'git_reset_hard', 'recursive_delete']
        
        if operation in destructive_ops:
            return self._ask_approval(operation, details)
        
        # Mode 0: Everything requires approval
        if self.autonomy_mode == 0:
            return self._ask_approval(operation, details)
        
        # Mode 1: Reads auto-approved, writes need approval
        if self.autonomy_mode == 1:
            if operation == 'read':
                return True # Auto-approved
            return self._ask_approval(operation, details)
        
        # Mode 2: Reads/writes auto-approved, destructive ops already handled
        if self.autonomy_mode == 2:
            return True # Auto-approved for non-destructive
        
        # Default to requiring approval
        return self._ask_approval(operation, details)
    
    def _ask_approval(self, operation: str, details: str) -> bool:
        """Ask for approval using callback or fallback to input."""
        if self._approval_callback:
            return self._approval_callback(operation, details)
        
        # Fallback to console input (for testing/debugging)
        print(f"\n⚠️  Approval Required: {operation}")
        if details:
            print(f"   {details}")
        response = input("   Approve? (y/N): ").lower()
        return response == 'y'
    
    # ========== Convenience Methods ==========
    
    def can_read(self, path: Path) -> bool:
        """Check if file can be read."""
        return self.is_path_allowed(path, 'read')
    
    def can_write(self, path: Path) -> bool:
        """Check if file can be written."""
        return self.is_path_allowed(path, 'write')
    
    def can_delete(self, path: Path) -> bool:
        """Check if file/directory can be deleted."""
        if not self.is_path_allowed(path, 'delete'):
            return False
        return self.requires_approval('delete', f"Delete: {path}")
    
    def can_access_url(self, url: str) -> bool:
        """Check if URL can be accessed."""
        allowed = self.is_url_allowed(url)
        if not allowed:
            return self.requires_approval('url_access', f"URL not in allowlist: {url}")
        return True
    
    @classmethod
    def non_interactive(cls, workspace_root: Path, autonomy_mode: int = 0) -> 'Permissions':
        """
        Create permissions instance for non-interactive mode.
        Returns auto-approvals for all operations (for testing).
        """
        perms = cls(workspace_root, autonomy_mode)
        # Override approval to auto-approve
        perms._approval_callback = lambda op, details: True
        return perms