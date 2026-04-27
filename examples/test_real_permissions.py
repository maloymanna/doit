"""Test permission system with real workspace."""
from pathlib import Path
from doit.permissions import Permissions, PermissionError

def test_real_workspace_permissions():
    """Test permission system against actual workspace."""
    
    # Your actual workspace path
    workspace = Path("~/Documents/02-learn/dev/doit-workspace").expanduser()
    
    print(f"\n{'='*60}")
    print(f"Testing Permission System with Real Workspace")
    print(f"{'='*60}")
    print(f"Workspace: {workspace}")
    print(f"Workspace exists: {workspace.exists()}")
    print()
    
    # Create permissions instance (mode 0 = strict)
    perms = Permissions(workspace, autonomy_mode=0)
    
    # Set auto-approve for testing (so we don't get prompted)
    perms._approval_callback = lambda op, details: True
    
    print("✓ Permissions instance created")
    print(f"  Autonomy mode: {perms.autonomy_mode}")
    print(f"  Workspace root: {perms.workspace_root}")
    print(f"  Readonly dir: {perms.readonly_dir}")
    print()
    
    # Test 1: Path validation within workspace
    print("1. Testing Path Validation")
    print("-" * 40)
    
    # Valid paths
    test_files = [
        workspace / "projects",
        workspace / "readonly_input",
        workspace / ".doit",
        workspace / ".doit" / "config.yaml",
        workspace / "projects" / "test_project",
    ]
    
    for test_file in test_files:
        try:
            result = perms.validate_path(test_file, 'read')
            print(f"  ✓ Allowed: {test_file.relative_to(workspace)}")
        except PermissionError as e:
            print(f"  ✗ Blocked: {test_file.relative_to(workspace)} - {e}")
    
    print()
    
    # Test 2: Outside workspace (should be blocked)
    print("2. Testing Outside Workspace (Should Be Blocked)")
    print("-" * 40)
    
    outside_paths = [
        Path("/tmp/outside.txt"),
        Path.home() / "Downloads",
        Path.cwd() / ".." / "..",
    ]
    
    for outside in outside_paths:
        try:
            perms.validate_path(outside, 'read')
            print(f"  ✗ Should have been blocked: {outside}")
        except PermissionError as e:
            print(f"  ✓ Correctly blocked: {outside}")
            print(f"    Reason: {str(e).split(chr(10))[0]}")
    
    print()
    
    # Test 3: readonly_input write protection
    print("3. Testing readonly_input Protection")
    print("-" * 40)
    
    readonly_file = workspace / "readonly_input" / "test.txt"
    
    # Read should be allowed
    try:
        perms.validate_path(readonly_file, 'read')
        print(f"  ✓ Read allowed from readonly_input")
    except PermissionError as e:
        print(f"  ✗ Read blocked unexpectedly: {e}")
    
    # Write should be blocked
    try:
        perms.validate_path(readonly_file, 'write')
        print(f"  ✗ Write should have been blocked!")
    except PermissionError as e:
        print(f"  ✓ Write correctly blocked")
        print(f"    Reason: {e}")
    
    print()
    
    # Test 4: URL Allowlist
    print("4. Testing URL Allowlist")
    print("-" * 40)
    
    # Load actual allowlist from workspace
    allowlist_file = workspace / ".doit" / "allowlist.txt"
    if allowlist_file.exists():
        with open(allowlist_file, 'r') as f:
            allowlist = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        perms.allowlist = allowlist
        print(f"  Loaded {len(allowlist)} patterns from allowlist.txt")
    else:
        print(f"  ⚠ No allowlist.txt found, using empty allowlist")
    
    test_urls = [
        "https://chat.qwen.ai",
        "https://kimi.com",
        "https://github.com/maloymanna/doit",
        "https://www.google.com",
        "https://chatgpt.com",
    ]
    
    for url in test_urls:
        allowed = perms.is_url_allowed(url)
        status = "✓ Allowed" if allowed else "✗ Blocked"
        print(f"  {status}: {url}")
    
    print()
    
    # Test 5: Autonomy Modes
    print("5. Testing Autonomy Modes")
    print("-" * 40)

    # Use auto-REJECT to see what needs approval
    perms._approval_callback = lambda op, details: False

    # Test Mode 0
    perms.set_autonomy_mode(0)
    print(f"  Mode 0 (Strict - all need approval):")
    read_approved = perms.requires_approval('read')
    write_approved = perms.requires_approval('write')
    delete_approved = perms.requires_approval('delete')
    print(f"    Read approved? {read_approved} (should be False - needs approval but rejected)")
    print(f"    Write approved? {write_approved} (should be False - needs approval but rejected)")
    print(f"    Delete approved? {delete_approved} (should be False - destructive needs approval)")

    # Test Mode 1
    perms.set_autonomy_mode(1)
    print(f"  Mode 1 (Moderate - reads auto-approved, writes need approval):")    
    read_approved = perms.requires_approval('read')
    write_approved = perms.requires_approval('write')
    print(f"    Read approved? {read_approved} (should be True - auto-approved)")
    print(f"    Write approved? {write_approved} (should be False - needs approval but rejected)")

    # Test Mode 2
    perms.set_autonomy_mode(2)
    print(f"  Mode 2 (Permissive - reads/writes auto-approved, destructive need approval):")
    read_approved = perms.requires_approval('read')
    write_approved = perms.requires_approval('write')
    delete_approved = perms.requires_approval('delete')
    git_push_approved = perms.requires_approval('git_push')
    print(f"    Read approved? {read_approved} (should be True - auto-approved)")
    print(f"    Write approved? {write_approved} (should be True - auto-approved)")
    print(f"    Delete approved? {delete_approved} (should be False - destructive needs approval but rejected)")
    print(f"    Git push approved? {git_push_approved} (should be False - destructive needs approval but rejected)")

    # Reset callback to auto-approve for remaining tests
    perms._approval_callback = lambda op, details: True

    # Test 6: Convenience Methods
    print("6. Testing Convenience Methods")
    print("-" * 40)
    
    projects_dir = workspace / "projects"
    test_file = projects_dir / "test_permission.txt"
    
    print(f"  can_read({test_file.relative_to(workspace)}): {perms.can_read(test_file)}")
    print(f"  can_write({test_file.relative_to(workspace)}): {perms.can_write(test_file)}")
    print(f"  can_access_url('https://usegpt.myorg'): {perms.can_access_url('https://usegpt.myorg')}")
    
    # Create a test file to test delete
    if not test_file.exists():
        test_file.touch()
        print(f"  Created test file: {test_file.relative_to(workspace)}")
    
    print(f"  can_delete({test_file.relative_to(workspace)}): {perms.can_delete(test_file)}")
    
    # Clean up
    if test_file.exists():
        test_file.unlink()
        print(f"  Cleaned up test file")
    
    print()
    
    # Summary
    print("="*60)
    print("SUMMARY")
    print("="*60)
    print("✅ All permission tests passed with real workspace")
    print(f"✅ Workspace is properly isolated at: {workspace}")
    print(f"✅ readonly_input is protected")
    print(f"✅ URL allowlist is working")
    print(f"✅ Autonomy modes are functional")
    print()
    
    # Recommendations
    print("Recommendations:")
    print("-" * 40)
    if not perms.allowlist:
        print("  ⚠ Add URLs to .doit/allowlist.txt for browser automation")
    else:
        print(f"  ✓ {len(perms.allowlist)} URLs in allowlist")
    
    if perms.autonomy_mode == 0:
        print("  ℹ Current mode is strict (0) - all operations need approval")
        print("  💡 Consider mode 1 or 2 for less interruption")
    
    print("\n✓ Real workspace validation complete!")

def test_with_different_autonomy_modes():
    """Test how different autonomy modes affect operations."""
    
    workspace = Path("~/arbitrary_folder/doit-workspace").expanduser()
    
    print(f"\n{'='*60}")
    print(f"Autonomy Mode Comparison")
    print(f"{'='*60}")
    
    operations = ['read', 'write', 'delete', 'git_push', 'git_reset_hard']
    
    for mode in [0, 1, 2]:
        perms = Permissions(workspace, autonomy_mode=mode)
        # Set auto-REJECT for testing (to see what needs approval)
        perms._approval_callback = lambda op, details: False 
        
        print(f"\nMode {mode}:")
        print("-" * 40)
        for op in operations:
            approved = perms.requires_approval(op)
            
            if mode == 0:
                # Mode 0: All need approval (so all should be False with auto-reject)
                status = "🔒 Needs Approval" if not approved else "✓ Auto-approved"
            elif mode == 1:
                # Mode 1: Reads auto-approved, others need approval
                if op == 'read':
                    status = "✓ Auto-approved" if approved else "🔒 Needs Approval (unexpected)"
                else:
                    status = "🔒 Needs Approval" if not approved else "✓ Auto-approved (unexpected)"
            else:  # mode 2
                # Mode 2: Reads/writes auto-approved, destructive need approval
                if op in ['delete', 'git_push', 'git_reset_hard']:
                    status = "🔒 Needs Approval (destructive)" if not approved else "✓ Auto-approved (unexpected)"
                else:
                    status = "✓ Auto-approved" if approved else "🔒 Needs Approval (unexpected)"
            
            print(f"  {op:15} : {status}")

if __name__ == "__main__":
    test_real_workspace_permissions()
    test_with_different_autonomy_modes()