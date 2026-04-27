"""Unit tests for permission system."""

import pytest
import tempfile
from pathlib import Path
from doit.permissions import Permissions, PermissionError


class TestPathValidation:
    """Test workspace path validation."""
    
    def test_path_within_workspace(self, temp_workspace):
        """Should allow paths within workspace."""
        perms = Permissions(temp_workspace)
        file_path = temp_workspace / "some_file.txt"
        file_path.touch()
        
        result = perms.validate_path(file_path, 'read')
        assert result == file_path.resolve()
    
    def test_path_outside_workspace_raises_error(self, temp_workspace):
        """Should reject paths outside workspace."""
        perms = Permissions(temp_workspace)
        outside = Path("/tmp/outside.txt")
        
        with pytest.raises(PermissionError) as exc:
            perms.validate_path(outside)
        assert "Path outside workspace" in str(exc.value)
    
    def test_readonly_input_read_allowed(self, temp_workspace):
        """Should allow reads from readonly_input."""
        readonly_dir = temp_workspace / 'readonly_input'
        readonly_dir.mkdir()
        file_path = readonly_dir / "data.txt"
        file_path.touch()
        
        perms = Permissions(temp_workspace)
        result = perms.validate_path(file_path, 'read')
        assert result == file_path.resolve()
    
    def test_readonly_input_write_blocked(self, temp_workspace):
        """Should block writes to readonly_input."""
        readonly_dir = temp_workspace / 'readonly_input'
        readonly_dir.mkdir()
        file_path = readonly_dir / "data.txt"
        
        perms = Permissions(temp_workspace)
        
        with pytest.raises(PermissionError) as exc:
            perms.validate_path(file_path, 'write')
        assert "Cannot write in readonly_input" in str(exc.value)
    
    def test_readonly_input_delete_blocked(self, temp_workspace):
        """Should block deletes from readonly_input."""
        readonly_dir = temp_workspace / 'readonly_input'
        readonly_dir.mkdir()
        file_path = readonly_dir / "data.txt"
        file_path.touch()
        
        perms = Permissions(temp_workspace)
        
        with pytest.raises(PermissionError) as exc:
            perms.validate_path(file_path, 'delete')
        assert "Cannot delete in readonly_input" in str(exc.value)
    
    def test_path_traversal_attempt_blocked(self, temp_workspace):
        """Should block path traversal attempts."""
        perms = Permissions(temp_workspace)
        malicious = temp_workspace / "subdir" / ".." / ".." / "etc" / "passwd"
        
        with pytest.raises(PermissionError):
            perms.validate_path(malicious)


class TestURLAllowlist:
    """Test URL allowlist functionality."""
    
    def test_empty_allowlist_allows_all(self, temp_workspace):
        """Empty allowlist should allow all URLs."""
        perms = Permissions(temp_workspace, allowlist=[])
        assert perms.is_url_allowed("https://any-site.com") is True
    
    def test_exact_match_allowed(self, temp_workspace):
        """Should allow exact URL matches."""
        perms = Permissions(temp_workspace, allowlist=["https://usegpt.myorg"])
        assert perms.is_url_allowed("https://usegpt.myorg") is True
        assert perms.is_url_allowed("https://other-site.com") is False
    
    def test_wildcard_match(self, temp_workspace):
        """Should support wildcard patterns."""
        perms = Permissions(temp_workspace, allowlist=["https://*.myorg/*"])
        assert perms.is_url_allowed("https://usegpt.myorg/chat") is True
        assert perms.is_url_allowed("https://other.com") is False
    
    def test_add_to_allowlist(self, temp_workspace):
        """Should allow adding new patterns."""
        perms = Permissions(temp_workspace, allowlist=[])
        perms.add_to_allowlist("https://newsite.com")
        assert perms.is_url_allowed("https://newsite.com") is True


class TestAutonomyModes:
    """Test autonomy mode behavior."""
    
    def test_mode_0_requires_approval_for_all(self, temp_workspace):
        """Mode 0: All operations require approval."""
        perms = Permissions(temp_workspace, autonomy_mode=0)
        
        # Set auto-reject for testing
        perms._approval_callback = lambda op, details: False # Always returns DENIED
        
        assert perms.requires_approval('read') is False # Means: DENIED (needs approval but was rejected)
        assert perms.requires_approval('write') is False # Means: DENIED
        assert perms.requires_approval('delete') is False # Means: DENIED
    
    def test_mode_1_auto_approves_reads(self, temp_workspace):
        """Mode 1: Reads auto-approved, writes need approval."""
        perms = Permissions(temp_workspace, autonomy_mode=1)
        perms._approval_callback = lambda op, details: True
        
        assert perms.requires_approval('read') is True  # Auto-approved
        assert perms.requires_approval('write') is True  # Requires callback
        assert perms.requires_approval('delete') is True  # Destructive
    
    def test_mode_2_auto_approves_reads_writes(self, temp_workspace):
        """Mode 2: Reads/writes auto-approved, destructive ops need approval."""
        perms = Permissions(temp_workspace, autonomy_mode=2)
        perms._approval_callback = lambda op, details: False
        
        assert perms.requires_approval('read') is True  # Auto-approved
        assert perms.requires_approval('write') is True  # Auto-approved
        assert perms.requires_approval('delete') is False  # Needs approval
    
    def test_destructive_ops_always_require_approval(self, temp_workspace):
        """Destructive operations always require approval."""
        perms = Permissions(temp_workspace, autonomy_mode=2)
        call_count = 0
        
        def approval_callback(op, details):
            nonlocal call_count
            call_count += 1
            return True
        
        perms._approval_callback = approval_callback
        
        perms.requires_approval('delete', "Delete file")
        perms.requires_approval('git_push', "Push to remote")
        perms.requires_approval('git_reset_hard', "Hard reset")
        
        assert call_count == 3
    
    def test_set_autonomy_mode_runtime(self, temp_workspace):
        """Should allow changing mode at runtime."""
        perms = Permissions(temp_workspace, autonomy_mode=0)
        assert perms.autonomy_mode == 0
        
        perms.set_autonomy_mode(2)
        assert perms.autonomy_mode == 2
        
        with pytest.raises(ValueError):
            perms.set_autonomy_mode(99)


class TestConvenienceMethods:
    """Test convenience permission methods."""
    
    def test_can_read(self, temp_workspace):
        """can_read should return boolean."""
        perms = Permissions(temp_workspace)
        file_path = temp_workspace / "file.txt"
        file_path.touch()
        
        assert perms.can_read(file_path) is True
        assert perms.can_read(Path("/outside")) is False
    
    def test_can_write_outside_workspace(self, temp_workspace):
        """can_write should return False for outside paths."""
        perms = Permissions(temp_workspace)
        assert perms.can_write(Path("/outside")) is False
    
    def test_can_delete_with_approval(self, temp_workspace):
        """can_delete should check both path and approval."""
        perms = Permissions(temp_workspace, autonomy_mode=0)
        perms._approval_callback = lambda op, details: True
        file_path = temp_workspace / "file.txt"
        file_path.touch()
        
        assert perms.can_delete(file_path) is True


# Fixture
@pytest.fixture
def temp_workspace():
    """Create a temporary workspace for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        yield workspace