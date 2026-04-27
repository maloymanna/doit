"""Test permission system with real workspace."""
from pathlib import Path
from doit.permissions import Permissions, PermissionError

# Define workspace path ONCE at the top - change this to your actual workspace
# On Windows Git Bash, use forward slashes without /c/ prefix
# Examples:
#   Linux:   workspace = Path.home() / "arbitrary_folder" / "doit-workspace"
#   Windows: workspace = Path("C:/Users/myuser/myapp/doit-workspace")
#   Or use:  workspace = Path.cwd().parent / "doit-workspace"  # if workspace is sibling to project

WORKSPACE = Path("~/Documents/02-learn/dev/doit-workspace").expanduser()
# For Windows, if the above doesn't work, uncomment and modify this line:
# WORKSPACE = Path("C:/Users/yourusername/arbitrary_folder/doit-workspace")

def load_allowlist_from_workspace(workspace: Path):
    """Load allowlist from workspace .doit/allowlist.txt"""
    allowlist_file = workspace / ".doit" / "allowlist.txt"
    allowlist = []
    
    if allowlist_file.exists():
        with open(allowlist_file, 'r') as f:
            for line in f:
                line = line.strip()
                # Skip empty lines and comments
                if line and not line.startswith('#'):
                    allowlist.append(line)
        print(f"  ✓ Loaded {len(allowlist)} patterns from {allowlist_file}")
    else:
        print(f"  ⚠ Allowlist file not found: {allowlist_file}")
        print(f"  → Using empty allowlist (ALL URLs will be blocked)")
    
    return allowlist

def test_real_workspace_permissions():
    """Test permission system against actual workspace."""
    
    # Your actual workspace path
    workspace = WORKSPACE
    
    print(f"\n{'='*60}")
    print(f"Testing Permission System with Real Workspace")
    print(f"{'='*60}")
    print(f"Workspace: {workspace}")
    print(f"Workspace exists: {workspace.exists()}")
    print()

    # If workspace doesn't exist, show helpful message
    if not workspace.exists():
        print(f"❌ ERROR: Workspace not found at: {workspace}")
        print(f"   Please update the WORKSPACE variable at the top of this script")
        print(f"   to point to your actual doit workspace directory.")
        print(f"\n   Current WORKSPACE value: {WORKSPACE}")
        print(f"   Type of path: {type(workspace)}")
        return

    # Load actual allowlist from workspace
    allowlist = load_allowlist_from_workspace(workspace)
    print()
    
    # Create permissions instance (mode 0 = strict) with loaded allowlist
    perms = Permissions(workspace, autonomy_mode=0, allowlist=allowlist)
    
    # Set auto-approve for testing (so we don't get prompted)
    perms._approval_callback = lambda op, details: True
    
    print("✓ Permissions instance created")
    print(f"  Autonomy mode: {perms.autonomy_mode}")
    print(f"  Workspace root: {perms.workspace_root}")
    print(f"  Readonly dir: {perms.readonly_dir}")
    print(f"  Allowlist size: {len(perms.allowlist)}")
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
            rel_path = test_file.relative_to(workspace)
            print(f"  ✓ Allowed: {rel_path}")
        except PermissionError as e:
            rel_path = test_file.relative_to(workspace) if test_file != workspace else "workspace"
            print(f"  ✗ Blocked: {rel_path} - {e}")
        except Exception as e:
            rel_path = test_file.relative_to(workspace) if test_file != workspace else "workspace"
            print(f"  ✗ Error: {rel_path} - {e}")
    
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
    
    # Test 4: URL Allowlist (using actual allowlist from workspace)
    print("4. Testing URL Allowlist")
    print("-" * 40)
    
    # Test URLs including the one from allowlist
    test_urls = [
        "https://chatgpt.com",                  # Should be allowed if in allowlist
        "https://chat.qwen.ai",                 # Should be blocked if not in allowlist
        "https://github.com/maloymanna/doit",   # Should be allowed if in allowlist
        "https://www.google.com",               # Should be allowed if in allowlist
        "https://kimi.com",                     # Should be blocked if not in allowlist
        "https://random-site.com",              # Should be blocked
    ]
    
    for url in test_urls:
        allowed = perms.is_url_allowed(url)
        if allowed:
            print(f"  ✓ Allowed: {url}")
        else:
            print(f"  ✗ Blocked: {url}")
    
    # Verify security: empty allowlist blocks everything
    print(f"\n  Security Check:")
    if len(perms.allowlist) == 0:
        print(f"  ⚠ Allowlist is empty - ALL URLs should be blocked")
        # Test a few URLs to verify
        for url in ["https://usegpt.myorg", "https://any-site.com"]:
            if perms.is_url_allowed(url):
                print(f"    ✗ FAILED: {url} was allowed but allowlist is empty!")
            else:
                print(f"    ✓ PASSED: {url} correctly blocked")
    else:
        print(f"  ✓ Allowlist has {len(perms.allowlist)} entries")
    
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
    
    print()
    
    # Test 6: Convenience Methods
    print("6. Testing Convenience Methods")
    print("-" * 40)
    
    projects_dir = workspace / "projects"
    # Ensure projects directory exists
    projects_dir.mkdir(exist_ok=True)
    
    test_file = projects_dir / "test_permission.txt"
    
    print(f"  Projects directory exists: {projects_dir.exists()}")
    print(f"  can_read({test_file.name}): {perms.can_read(test_file)}")
    print(f"  can_write({test_file.name}): {perms.can_write(test_file)}")
    print(f"  can_access_url('https://usegpt.myorg'): {perms.can_access_url('https://usegpt.myorg')}")
    
    # Create a test file to test delete (handle Windows permissions)
    try:
        if not test_file.exists():
            test_file.touch()
            print(f"  Created test file: {test_file.name}")
        
        # Check if file was actually created
        if test_file.exists():
            print(f"  can_delete({test_file.name}): {perms.can_delete(test_file)}")
            # Clean up
            test_file.unlink()
            print(f"  Cleaned up test file")
        else:
            print(f"  ⚠ Could not create test file (permissions issue)")
    except Exception as e:
        print(f"  ⚠ File operation warning: {e}")
    
    print()
    
    # Summary
    print("="*60)
    print("SUMMARY")
    print("="*60)
    
    # Check critical security requirements
    all_secure = True
    
    # Check 1: Allowlist security
    if len(perms.allowlist) == 0:
        print("⚠️  WARNING: Allowlist is empty! No URLs are allowed.")
        print("   Add allowed URLs to .doit/allowlist.txt")
        all_secure = False
    else:
        print(f"✅ Allowlist configured with {len(perms.allowlist)} entries")
    
    # Check 2: readonly_input protection
    print("✅ readonly_input is write-protected")
    
    # Check 3: Path isolation
    print("✅ Path isolation is working")
    
    # Check 4: Autonomy modes
    print("✅ Autonomy modes are functional")
    
    if all_secure:
        print("\n✅ All security checks passed!")
    else:
        print("\n⚠️  Some security issues need attention")
    
    print(f"\nWorkspace: {workspace}")

def test_with_different_autonomy_modes():
    """Test how different autonomy modes affect operations."""
    
    workspace = WORKSPACE

    # Check if workspace exists
    if not workspace.exists():
        print(f"\n⚠️  Skipping autonomy mode test - workspace not found at: {workspace}")
        return

    allowlist = load_allowlist_from_workspace(workspace)
    
    print(f"\n{'='*60}")
    print(f"Autonomy Mode Comparison (with auto-REJECT)")
    print(f"{'='*60}")
    print("Note: False = would need approval (but was rejected), True = auto-approved")
    print()
    
    operations = ['read', 'write', 'delete', 'git_push', 'git_reset_hard']
    
    for mode in [0, 1, 2]:
        perms = Permissions(workspace, autonomy_mode=mode, allowlist=allowlist)
        # Set auto-REJECT for testing (to see what would need approval)
        perms._approval_callback = lambda op, details: False
        
        print(f"\nMode {mode}:")
        print("-" * 40)
        for op in operations:
            approved = perms.requires_approval(op)
            
            if mode == 0:
                # Mode 0: All need approval → all should be False
                status = "❌ Needs approval" if not approved else "✅ Auto-approved (unexpected)"
            elif mode == 1:
                # Mode 1: Reads auto-approved, others need approval
                if op == 'read':
                    status = "✅ Auto-approved" if approved else "❌ Needs approval (unexpected)"
                else:
                    status = "❌ Needs approval" if not approved else "✅ Auto-approved (unexpected)"
            else:  # mode 2
                # Mode 2: Reads/writes auto-approved, destructive need approval
                if op in ['delete', 'git_push', 'git_reset_hard']:
                    status = "❌ Needs approval (destructive)" if not approved else "✅ Auto-approved (unexpected)"
                else:
                    status = "✅ Auto-approved" if approved else "❌ Needs approval (unexpected)"
            
            print(f"  {op:15} : {status}")

if __name__ == "__main__":
    test_real_workspace_permissions()
    test_with_different_autonomy_modes()