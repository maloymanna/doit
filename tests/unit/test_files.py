"""Unit tests for file operations."""

import pytest
import tempfile
from pathlib import Path
from doit.permissions import Permissions, PermissionError
from doit.files import FileManager, FileTypeError, FileSizeError, FileLimitError, FileError


class TestFileTypeValidation:
    """Test file type validation for LLM uploads."""
    
    def test_allowed_document_types(self, temp_workspace, file_manager):
        """Should allow document file types."""
        allowed_extensions = ['.txt', '.pdf', '.doc', '.docx', '.ppt', '.pptx', '.xls', '.xlsx', '.rtf']
        
        for ext in allowed_extensions:
            file_path = temp_workspace / f"test{ext}"
            file_path.touch()
            assert file_manager.is_file_type_allowed(file_path) is True
    
    def test_allowed_image_types(self, temp_workspace, file_manager):
        """Should allow image file types."""
        allowed_extensions = ['.jpg', '.jpeg', '.png']
        
        for ext in allowed_extensions:
            file_path = temp_workspace / f"test{ext}"
            file_path.touch()
            assert file_manager.is_file_type_allowed(file_path) is True
    
    def test_blocked_file_types(self, temp_workspace, file_manager):
        """Should block dangerous file types."""
        blocked_extensions = ['.exe', '.bat', '.msi', '.zip', '.sh', '.pyc']
        
        for ext in blocked_extensions:
            file_path = temp_workspace / f"test{ext}"
            file_path.touch()
            assert file_manager.is_file_type_allowed(file_path) is False
    
    def test_validate_file_type_passes(self, temp_workspace, file_manager):
        """validate_file_type should not raise for allowed types."""
        file_path = temp_workspace / "test.txt"
        file_path.touch()
        
        # Should not raise
        file_manager.validate_file_type(file_path)
    
    def test_validate_file_type_raises_for_blocked(self, temp_workspace, file_manager):
        """validate_file_type should raise FileTypeError for blocked types."""
        file_path = temp_workspace / "test.exe"
        file_path.touch()
        
        with pytest.raises(FileTypeError) as exc:
            file_manager.validate_file_type(file_path)
        assert ".exe" in str(exc.value)


class TestFileSizeValidation:
    """Test file size limits."""
    
    def test_document_size_limit(self, temp_workspace, file_manager):
        """Document size limit is 4 MB."""
        file_path = temp_workspace / "test.txt"
        
        # Create 3 MB file (should pass)
        with open(file_path, 'wb') as f:
            f.write(b'x' * (3 * 1024 * 1024))
        file_manager.validate_file_size(file_path)
        
        # Create 5 MB file (should fail)
        with open(file_path, 'wb') as f:
            f.write(b'x' * (5 * 1024 * 1024))
        with pytest.raises(FileSizeError):
            file_manager.validate_file_size(file_path)
    
    def test_image_size_limit(self, temp_workspace, file_manager):
        """Image size limit is 1 MB."""
        file_path = temp_workspace / "test.jpg"
        
        # Create 500 KB file (should pass)
        with open(file_path, 'wb') as f:
            f.write(b'x' * (500 * 1024))
        file_manager.validate_file_size(file_path)
        
        # Create 2 MB file (should fail)
        with open(file_path, 'wb') as f:
            f.write(b'x' * (2 * 1024 * 1024))
        with pytest.raises(FileSizeError):
            file_manager.validate_file_size(file_path)
    
    def test_get_size_limit_by_type(self, file_manager):
        """Should return correct size limit based on file type."""
        doc_file = Path("test.txt")
        img_file = Path("test.jpg")
        
        assert file_manager.get_file_size_limit(doc_file) == 4 * 1024 * 1024
        assert file_manager.get_file_size_limit(img_file) == 1 * 1024 * 1024


class TestFileBatchValidation:
    """Test batch file validation."""
    
    def test_max_files_limit(self, temp_workspace, file_manager):
        """Should reject more than 5 files."""
        files = []
        for i in range(6):
            file_path = temp_workspace / f"test{i}.txt"
            file_path.touch()
            files.append(file_path)
        
        with pytest.raises(FileLimitError) as exc:
            file_manager.validate_file_batch(files)
        assert "5" in str(exc.value)
    
    def test_batch_with_mixed_types(self, temp_workspace, file_manager):
        """Should validate all files in batch."""
        files = [
            temp_workspace / "doc1.txt",
            temp_workspace / "image.jpg",
            temp_workspace / "doc2.pdf",
        ]
        for f in files:
            f.touch()
        
        # Should pass for allowed types
        file_manager.validate_file_batch(files)
        
        # Add blocked file
        files.append(temp_workspace / "bad.exe")
        with open(files[-1], 'wb') as f:
            f.write(b'x' * 100)
        
        with pytest.raises(FileTypeError):
            file_manager.validate_file_batch(files)


class TestFileOperations:
    """Test read/write/delete operations."""
    
    def test_read_file_text(self, temp_workspace, file_manager):
        """Should read text file correctly."""
        file_path = temp_workspace / "test.txt"
        content = "Hello, World!"
        file_path.write_text(content)
        
        result = file_manager.read_file(file_path, as_text=True)
        assert result == content
    
    def test_read_file_binary(self, temp_workspace, file_manager):
        """Should read binary file correctly."""
        file_path = temp_workspace / "test.bin"
        content = b'\x00\x01\x02\x03'
        file_path.write_bytes(content)
        
        result = file_manager.read_file(file_path, as_text=False)
        assert result == content
    
    def test_read_file_not_found(self, temp_workspace, file_manager):
        """Should raise error for missing file."""
        file_path = temp_workspace / "missing.txt"
        
        with pytest.raises(FileError):
            file_manager.read_file(file_path)
    
    def test_write_file_text(self, temp_workspace, file_manager):
        """Should write text file correctly."""
        file_path = temp_workspace / "output.txt"
        content = "Test content"
        
        result = file_manager.write_file(file_path, content, as_text=True)
        assert result.exists()
        assert result.read_text() == content
    
    def test_write_file_binary(self, temp_workspace, file_manager):
        """Should write binary file correctly."""
        file_path = temp_workspace / "output.bin"
        content = b'\x00\x01\x02\x03'
        
        result = file_manager.write_file(file_path, content, as_text=False)
        assert result.exists()
        assert result.read_bytes() == content
    
    def test_write_file_creates_directories(self, temp_workspace, file_manager):
        """Should create parent directories when writing."""
        file_path = temp_workspace / "subdir" / "nested" / "output.txt"
        content = "Test"
        
        result = file_manager.write_file(file_path, content)
        assert result.exists()
    
    def test_delete_file(self, temp_workspace, file_manager):
        """Should delete file with approval."""
        # Override approval callback to auto-approve
        file_manager.permissions._approval_callback = lambda op, details: True
        
        file_path = temp_workspace / "to_delete.txt"
        file_path.touch()
        
        result = file_manager.delete_file(file_path)
        assert result is True
        assert not file_path.exists()
    
    def test_delete_file_not_found(self, temp_workspace, file_manager):
        """Should return False for missing file."""
        file_path = temp_workspace / "missing.txt"
        
        result = file_manager.delete_file(file_path)
        assert result is False


class TestProjectManagement:
    """Test project directory operations."""
    
    def test_get_project_dir_creates(self, temp_workspace, file_manager):
        """Should create project directory if it doesn't exist."""
        project_dir = file_manager.get_project_dir("test_project")
        assert project_dir.exists()
        assert project_dir.name == "test_project"
    
    def test_get_project_log_path(self, temp_workspace, file_manager):
        """Should return path to log file."""
        log_path = file_manager.get_project_log_path("test_project", "chat.jsonl")
        assert log_path.parent.name == "test_project"
        assert log_path.name == "chat.jsonl"
    
    def test_write_project_log(self, temp_workspace, file_manager):
        """Should append JSON to project log."""
        log_path = file_manager.write_project_log("test_project", {"message": "Hello"})
        
        assert log_path.exists()
        content = log_path.read_text()
        assert "Hello" in content
        assert "timestamp" in content
    
    def test_list_project_files(self, temp_workspace, file_manager):
        """Should list files in project directory."""
        project_dir = file_manager.get_project_dir("test_project")
        (project_dir / "file1.txt").touch()
        (project_dir / "file2.txt").touch()
        
        files = file_manager.list_project_files("test_project")
        assert len(files) == 2


class TestFileInfo:
    """Test file metadata methods."""
    
    def test_get_file_info(self, temp_workspace, file_manager):
        """Should return file metadata."""
        file_path = temp_workspace / "test.txt"
        file_path.write_text("content")
        
        info = file_manager.get_file_info(file_path)
        
        assert info['exists'] is True
        assert info['name'] == "test.txt"
        assert info['extension'] == ".txt"
        assert info['is_allowed'] is True
        assert info['size'] > 0
    
    def test_get_file_info_not_exists(self, temp_workspace, file_manager):
        """Should return exists=False for missing file."""
        info = file_manager.get_file_info(temp_workspace / "missing.txt")
        assert info['exists'] is False

class TestReadonlyInput:
    """Test file operations with readonly_input directory."""
    
    def test_read_from_readonly_input_allowed(self, temp_workspace, permissions, file_manager):
        """Should allow reading allowed file types from readonly_input."""
        readonly_dir = temp_workspace / 'readonly_input'
        readonly_dir.mkdir(exist_ok=True)
        
        # Create test files in readonly_input
        test_files = [
            ('document.txt', b'Hello World' * 100),  # Text file
            ('image.jpg', b'\xff\xd8\xff\xdb' + b'x' * 500),  # Simulated JPEG
            ('data.pdf', b'%PDF' + b'x' * 1000),  # Simulated PDF
        ]
        
        for filename, content in test_files:
            file_path = readonly_dir / filename
            file_path.write_bytes(content)
        
        # Read and validate each file
        for filename, _ in test_files:
            file_path = readonly_dir / filename
            # Should be readable
            name, mime, content = file_manager.read_file_for_llm(file_path)
            assert name == filename
            assert len(content) > 0
            print(f"  ✓ Read allowed: {filename}")
    
    def test_readonly_input_respects_file_type_limits(self, temp_workspace, permissions, file_manager):
        """Should enforce file type restrictions in readonly_input."""
        readonly_dir = temp_workspace / 'readonly_input'
        readonly_dir.mkdir(exist_ok=True)
        
        # Create blocked file type in readonly_input
        blocked_file = readonly_dir / 'malware.exe'
        blocked_file.write_bytes(b'fake executable')
        
        # Should NOT be allowed (blocked file type)
        with pytest.raises(FileTypeError) as exc:
            file_manager.read_file_for_llm(blocked_file)
        assert ".exe" in str(exc.value)
        
        # Create allowed file but with wrong extension
        fake_pdf = readonly_dir / 'fake.txt'
        fake_pdf.write_bytes(b'%PDF fake content')
        
        # Should be allowed as .txt (text file)
        name, mime, content = file_manager.read_file_for_llm(fake_pdf)
        assert name == 'fake.txt'
        assert mime == 'text/plain'
    
    def test_readonly_input_respects_size_limits(self, temp_workspace, permissions, file_manager):
        """Should enforce size limits in readonly_input."""
        readonly_dir = temp_workspace / 'readonly_input'
        readonly_dir.mkdir(exist_ok=True)
        
        # Create oversized document (6 MB)
        oversized_doc = readonly_dir / 'oversized.txt'
        oversized_doc.write_bytes(b'x' * (6 * 1024 * 1024))
        
        with pytest.raises(FileSizeError) as exc:
            file_manager.read_file_for_llm(oversized_doc)
        assert "exceeds limit" in str(exc.value)
        
        # Create oversized image (2 MB)
        oversized_img = readonly_dir / 'oversized.jpg'
        oversized_img.write_bytes(b'x' * (2 * 1024 * 1024))
        
        with pytest.raises(FileSizeError) as exc:
            file_manager.read_file_for_llm(oversized_img)
        assert "exceeds limit" in str(exc.value)
    
    def test_readonly_input_batch_limits(self, temp_workspace, permissions, file_manager):
        """Should enforce batch limits when reading from readonly_input."""
        readonly_dir = temp_workspace / 'readonly_input'
        readonly_dir.mkdir(exist_ok=True)
        
        # Create 7 files in readonly_input (exceeds limit of 5)
        files = []
        for i in range(7):
            file_path = readonly_dir / f'file{i}.txt'
            file_path.write_bytes(b'content')
            files.append(file_path)
        
        with pytest.raises(FileLimitError) as exc:
            file_manager.validate_file_batch(files)
        assert "5" in str(exc.value)
        
        # Batch of 3 files should work
        small_batch = files[:3]
        file_manager.validate_file_batch(small_batch)  # Should not raise
    
    def test_cannot_write_to_readonly_input(self, temp_workspace, permissions, file_manager):
        """Should NOT allow writing to readonly_input directory."""
        readonly_dir = temp_workspace / 'readonly_input'
        readonly_dir.mkdir(exist_ok=True)
        
        write_path = readonly_dir / 'should_not_be_written.txt'
        
        # This should raise PermissionError - the test PASSES if the exception is raised
        with pytest.raises(PermissionError) as exc_info:
            file_manager.write_file(write_path, "This should fail")
        
        # Verify the error message indicates readonly_input protection
        assert "Cannot write in readonly_input" in str(exc_info.value)

    def test_cannot_delete_from_readonly_input(self, temp_workspace, permissions, file_manager):
        """Should NOT allow deleting from readonly_input directory."""
        readonly_dir = temp_workspace / 'readonly_input'
        readonly_dir.mkdir(exist_ok=True)
        
        # Create a file
        file_path = readonly_dir / 'to_delete.txt'
        file_path.write_bytes(b'content')
        
        # Override approval callback to auto-approve
        file_manager.permissions._approval_callback = lambda op, details: True
        
        # This should raise PermissionError - the test PASSES if the exception is raised
        with pytest.raises(PermissionError) as exc_info:
            file_manager.delete_file(file_path)
        
        # Verify the error message indicates readonly_input protection
        assert "Cannot delete in readonly_input" in str(exc_info.value)
    
    def test_allowed_files_mixed_with_readonly(self, temp_workspace, permissions, file_manager):
        """Should allow reading mix of allowed files from readonly_input."""
        readonly_dir = temp_workspace / 'readonly_input'
        readonly_dir.mkdir(exist_ok=True)
        projects_dir = temp_workspace / 'projects'
        projects_dir.mkdir(exist_ok=True)
        
        # Create files in readonly_input
        readonly_files = []
        allowed_types = ['.txt', '.pdf', '.jpg']
        for i, ext in enumerate(allowed_types):
            file_path = readonly_dir / f'readonly_file{i}{ext}'
            file_path.write_bytes(b'x' * 1000)
            readonly_files.append(file_path)
        
        # Prepare batch for LLM upload
        prepared = file_manager.prepare_files_for_llm(readonly_files)
        
        assert len(prepared) == 3
        for name, mime, content in prepared:
            assert 'readonly_file' in name
            assert len(content) > 0
        
        print(f"  ✓ Successfully prepared {len(prepared)} files from readonly_input")

# Fixtures
@pytest.fixture
def temp_workspace():
    """Create a temporary workspace for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        # Create required directories
        (workspace / '.doit').mkdir()
        (workspace / 'projects').mkdir()
        (workspace / 'readonly_input').mkdir()
        yield workspace


@pytest.fixture
def permissions(temp_workspace):
    """Create permissions instance with auto-approve."""
    perms = Permissions(temp_workspace, autonomy_mode=0)
    perms._approval_callback = lambda op, details: True
    return perms


@pytest.fixture
def file_manager(permissions):
    """Create FileManager instance."""
    return FileManager(permissions)