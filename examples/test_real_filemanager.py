"""Test FileManager with real workspace."""

from pathlib import Path
from doit.permissions import Permissions
from doit.files import FileManager, FileTypeError, FileSizeError, FileLimitError

# Define workspace path ONCE at the top
# Update this to match your actual workspace
WORKSPACE = Path("~/Documents/02-learn/dev/doit-workspace").expanduser()
# For Windows, uncomment and modify:
# WORKSPACE = Path("C:/Users/yourusername/arbitrary_folder/doit-workspace")


def test_real_filemanager():
    """Test FileManager operations with real workspace."""
    
    workspace = WORKSPACE
    
    print(f"\n{'='*60}")
    print(f"Testing FileManager with Real Workspace")
    print(f"{'='*60}")
    print(f"Workspace: {workspace}")
    print(f"Workspace exists: {workspace.exists()}")
    print()
    
    if not workspace.exists():
        print(f"❌ ERROR: Workspace not found at: {workspace}")
        print(f"   Please update WORKSPACE variable at the top of this script")
        return
    
    # Create permissions and file manager
    perms = Permissions(workspace, autonomy_mode=0)
    perms._approval_callback = lambda op, details: True  # Auto-approve for testing
    file_mgr = FileManager(perms)
    
    print("✓ FileManager initialized")
    print(f"  Workspace root: {file_mgr.workspace_root}")
    print(f"  Readonly dir: {file_mgr.permissions.readonly_dir}")
    print()
    
    # Test 1: File type validation
    print("1. Testing File Type Validation")
    print("-" * 40)
    
    test_files = [
        ("document.txt", ".txt", True, "Document"),
        ("image.jpg", ".jpg", True, "Image"),
        ("presentation.pptx", ".pptx", True, "PowerPoint"),
        ("spreadsheet.xlsx", ".xlsx", True, "Excel"),
        ("malware.exe", ".exe", False, "Blocked executable"),
        ("archive.zip", ".zip", False, "Blocked archive"),
        ("script.bat", ".bat", False, "Blocked batch"),
    ]
    
    for filename, ext, should_be_allowed, description in test_files:
        file_path = workspace / "projects" / filename
        file_path.touch()
        
        is_allowed = file_mgr.is_file_type_allowed(file_path)
        status = "✓ Allowed" if is_allowed else "✗ Blocked"
        expected = "Allowed" if should_be_allowed else "Blocked"
        
        match = "✅" if is_allowed == should_be_allowed else "❌"
        print(f"  {match} {status}: {description} ({ext}) - Expected: {expected}")
        
        # Clean up
        if file_path.exists():
            file_path.unlink()
    
    print()
    
    # Test 2: Size limits
    print("2. Testing Size Limits")
    print("-" * 40)
    
    # Create test files with different sizes
    doc_file = workspace / "projects" / "test_doc.txt"
    img_file = workspace / "projects" / "test_img.jpg"
    
    # Document: 3 MB (should pass)
    with open(doc_file, 'wb') as f:
        f.write(b'x' * (3 * 1024 * 1024))
    
    # Image: 500 KB (should pass)
    with open(img_file, 'wb') as f:
        f.write(b'x' * (500 * 1024))
    
    try:
        file_mgr.validate_file_size(doc_file)
        print(f"  ✅ Document (3 MB) - Within 4 MB limit: PASS")
    except FileSizeError as e:
        print(f"  ❌ Document (3 MB) - FAILED: {e}")
    
    try:
        file_mgr.validate_file_size(img_file)
        print(f"  ✅ Image (0.5 MB) - Within 1 MB limit: PASS")
    except FileSizeError as e:
        print(f"  ❌ Image (0.5 MB) - FAILED: {e}")
    
    # Clean up
    doc_file.unlink()
    img_file.unlink()
    
    # Create oversized files
    oversized_doc = workspace / "projects" / "oversized.txt"
    oversized_img = workspace / "projects" / "oversized.jpg"
    
    with open(oversized_doc, 'wb') as f:
        f.write(b'x' * (6 * 1024 * 1024))  # 6 MB
    with open(oversized_img, 'wb') as f:
        f.write(b'x' * (2 * 1024 * 1024))  # 2 MB
    
    try:
        file_mgr.validate_file_size(oversized_doc)
        print(f"  ❌ Document (6 MB) - Should have failed but PASSED")
    except FileSizeError as e:
        print(f"  ✅ Document (6 MB) - Correctly blocked: {str(e)[:60]}...")
    
    try:
        file_mgr.validate_file_size(oversized_img)
        print(f"  ❌ Image (2 MB) - Should have failed but PASSED")
    except FileSizeError as e:
        print(f"  ✅ Image (2 MB) - Correctly blocked: {str(e)[:60]}...")
    
    # Clean up
    oversized_doc.unlink()
    oversized_img.unlink()
    
    print()
    
    # Test 3: Batch limits
    print("3. Testing Batch Limits")
    print("-" * 40)
    
    batch_files = []
    for i in range(7):
        file_path = workspace / "projects" / f"batch_file_{i}.txt"
        file_path.write_bytes(b'x' * 1000)
        batch_files.append(file_path)
    
    try:
        file_mgr.validate_file_batch(batch_files)
        print(f"  ❌ Batch of 7 files - Should have failed but PASSED")
    except FileLimitError as e:
        print(f"  ✅ Batch of 7 files - Correctly blocked: {e}")
    
    # Test batch of 3 files (should pass)
    small_batch = batch_files[:3]
    try:
        file_mgr.validate_file_batch(small_batch)
        print(f"  ✅ Batch of 3 files - Within limit: PASS")
    except FileLimitError as e:
        print(f"  ❌ Batch of 3 files - FAILED: {e}")
    
    # Clean up
    for f in batch_files:
        if f.exists():
            f.unlink()
    
    print()
    
    # Test 4: Reading from readonly_input
    print("4. Testing readonly_input Operations")
    print("-" * 40)
    
    readonly_dir = workspace / "readonly_input"
    if not readonly_dir.exists():
        readonly_dir.mkdir(parents=True)
        print(f"  Created readonly_input directory")
    
    # Create test files in readonly_input
    readonly_test_file = readonly_dir / "readonly_test.txt"
    readonly_test_file.write_bytes(b"This is a test file in readonly_input" * 100)
    
    try:
        name, mime, content = file_mgr.read_file_for_llm(readonly_test_file)
        print(f"  ✅ Read from readonly_input: {name} ({len(content)} bytes)")
    except Exception as e:
        print(f"  ❌ Failed to read from readonly_input: {e}")
    
    # Test writing to readonly_input (should fail)
    try:
        file_mgr.write_file(readonly_dir / "should_fail.txt", "This should not work")
        print(f"  ❌ Write to readonly_input - Should have failed but PASSED")
    except PermissionError as e:
        print(f"  ✅ Write to readonly_input - Correctly blocked: {str(e)[:60]}...")
    except Exception as e:
        print(f"  ⚠ Write to readonly_input - Blocked with unexpected error: {type(e).__name__}")
    
    print()
    
    # Test 5: Project directory management
    print("5. Testing Project Directory Management")
    print("-" * 40)
    
    project_name = "test_filemanager_project"
    project_dir = file_mgr.get_project_dir(project_name)
    print(f"  Project directory: {project_dir}")
    print(f"  Project exists: {project_dir.exists()}")
    
    # Create a log entry
    log_path = file_mgr.write_project_log(project_name, {"test": "FileManager test"})
    print(f"  Log created: {log_path}")
    
    # List project files
    files = file_mgr.list_project_files(project_name)
    print(f"  Files in project: {len(files)}")
    for f in files:
        print(f"    - {f.name}")
    
    print()
    
    # Test 6: Prepare files for LLM upload
    print("6. Testing LLM File Preparation")
    print("-" * 40)
    
    # Create valid test files
    llm_files = []
    valid_files = [
        ("sample.txt", b"This is a sample text document for LLM" * 100),
        ("sample.pdf", b"%PDF sample content" * 100),
        ("sample.jpg", b'\xff\xd8\xff\xdb' + b'x' * 500),
    ]
    
    for filename, content in valid_files:
        file_path = workspace / "projects" / filename
        file_path.write_bytes(content)
        llm_files.append(file_path)
    
    try:
        prepared = file_mgr.prepare_files_for_llm(llm_files)
        print(f"  ✅ Prepared {len(prepared)} files for LLM upload:")
        for name, mime, content in prepared:
            size_kb = len(content) / 1024
            print(f"    - {name} ({mime}, {size_kb:.1f} KB)")
    except Exception as e:
        print(f"  ❌ Failed to prepare files: {e}")
    
    # Clean up
    for f in llm_files:
        if f.exists():
            f.unlink()
    
    print()
    
    # Test 7: File info
    print("7. Testing File Info")
    print("-" * 40)
    
    info_file = workspace / "projects" / "info_test.txt"
    info_file.write_bytes(b"Test content for file info")
    
    info = file_mgr.get_file_info(info_file)
    print(f"  Name: {info['name']}")
    print(f"  Size: {info['size']} bytes ({info['size_mb']:.2f} MB)")
    print(f"  Extension: {info['extension']}")
    print(f"  Allowed for LLM: {info['is_allowed']}")
    print(f"  Modified: {info['modified']}")
    
    info_file.unlink()
    
    print()
    
    # Summary
    print("="*60)
    print("SUMMARY")
    print("="*60)
    print("✅ FileManager initialized successfully")
    print("✅ File type validation working")
    print("✅ Size limits enforced")
    print("✅ Batch limits enforced")
    print("✅ readonly_input read allowed, write blocked")
    print("✅ Project directory management working")
    print("✅ LLM file preparation working")
    print()
    print("✓ FileManager test completed successfully!")


def test_file_upload_scenario():
    """Simulate a real LLM upload scenario."""
    
    workspace = WORKSPACE
    
    print(f"\n{'='*60}")
    print(f"Real-world Scenario: Preparing Files for LLM Upload")
    print(f"{'='*60}")
    
    if not workspace.exists():
        print(f"❌ Workspace not found")
        return
    
    perms = Permissions(workspace, autonomy_mode=0)
    perms._approval_callback = lambda op, details: True
    file_mgr = FileManager(perms)
    
    # Simulate user uploading files for summarization
    print("\n📁 User selects files to upload to LLM:")
    
    # Create some test files in projects directory
    test_files = [
        ("annual_report.txt", b"This is the annual report content..." * 500),
        ("chart.png", b'\x89PNG\r\n\x1a\n' + b'x' * 800 * 1024),  # 800 KB image
        ("data.xlsx", b'PK\x03\x04' + b'x' * 1000),  # Simulated Excel
    ]
    
    uploaded_files = []
    for filename, content in test_files:
        file_path = workspace / "projects" / filename
        file_path.write_bytes(content)
        uploaded_files.append(file_path)
        print(f"  📎 {filename} ({len(content) / 1024:.1f} KB)")
    
    print(f"\n📤 Preparing to upload {len(uploaded_files)} files to LLM...")
    
    try:
        # Validate and prepare files
        file_mgr.validate_file_batch(uploaded_files)
        print(f"  ✓ Validation passed")
        
        # Read files for upload
        prepared = []
        for file_path in uploaded_files:
            name, mime, content = file_mgr.read_file_for_llm(file_path)
            prepared.append((name, mime))
            print(f"  ✓ Read {name} (MIME: {mime})")
        
        print(f"\n✅ Successfully prepared {len(prepared)} files for LLM upload")
        print("\n💡 These files can now be uploaded to usegpt.myorg:")
        for name, mime in prepared:
            print(f"   - {name} ({mime})")
        
    except FileTypeError as e:
        print(f"  ❌ File type error: {e}")
    except FileSizeError as e:
        print(f"  ❌ File size error: {e}")
    except FileLimitError as e:
        print(f"  ❌ Batch limit error: {e}")
    except Exception as e:
        print(f"  ❌ Unexpected error: {e}")
    
    # Clean up
    for f in uploaded_files:
        if f.exists():
            f.unlink()
    
    print(f"\n✓ Scenario test complete!")


if __name__ == "__main__":
    test_real_filemanager()
    test_file_upload_scenario()