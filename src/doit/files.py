"""File operations with permission checks and LLM upload constraints."""

from pathlib import Path
from typing import Optional, List, BinaryIO, Tuple
import mimetypes
from datetime import datetime
import shutil

from .permissions import Permissions, PermissionError


class FileError(Exception):
    """File operation related errors."""
    pass


class FileTypeError(FileError):
    """Unsupported file type."""
    pass


class FileSizeError(FileError):
    """File size exceeds limit."""
    pass


class FileLimitError(FileError):
    """Too many files for operation."""
    pass


class FileManager:
    """
    File operations with permission checks and LLM upload constraints.
    
    Features:
    - Permission checks for all operations
    - File type validation for LLM uploads
    - Size limits per file type
    - Max file count limits
    - Project directory management
    - Safe read/write operations
    """
    
    # Allowed file types for LLM upload
    ALLOWED_FILE_TYPES = {
        # Documents
        '.txt': 'text/plain',
        '.rtf': 'application/rtf',
        '.pdf': 'application/pdf',
        '.doc': 'application/msword',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.ppt': 'application/vnd.ms-powerpoint',
        '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        '.xls': 'application/vnd.ms-excel',
        '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        # Images
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
    }
    
    # Blocked file types (security)
    BLOCKED_FILE_TYPES = {
        '.exe', '.bat', '.msi', '.zip', '.rar', '.7z',
        '.sh', '.pyc', '.dll', '.so', '.dylib',
    }
    
    # Size limits (in bytes)
    DOCUMENT_MAX_SIZE = 4 * 1024 * 1024   # 4 MB
    IMAGE_MAX_SIZE = 1 * 1024 * 1024      # 1 MB
    MAX_FILES_PER_UPLOAD = 5
    
    def __init__(self, permissions: Permissions):
        """
        Initialize FileManager with permission checker.
        
        Args:
            permissions: Permissions instance for workspace validation
        """
        self.permissions = permissions
        self.workspace_root = permissions.workspace_root
    
    # ========== File Type Validation ==========
    
    @classmethod
    def get_file_extension(cls, file_path: Path) -> str:
        """Get lowercase file extension including dot."""
        return file_path.suffix.lower()
    
    @classmethod
    def is_file_type_allowed(cls, file_path: Path) -> bool:
        """Check if file type is allowed for LLM upload."""
        ext = cls.get_file_extension(file_path)
        
        # Blocked types take precedence
        if ext in cls.BLOCKED_FILE_TYPES:
            return False
        
        return ext in cls.ALLOWED_FILE_TYPES
    
    @classmethod
    def validate_file_type(cls, file_path: Path) -> None:
        """Validate file type, raise FileTypeError if not allowed."""
        if not cls.is_file_type_allowed(file_path):
            ext = cls.get_file_extension(file_path)
            raise FileTypeError(
                f"File type '{ext}' not allowed. "
                f"Allowed types: {', '.join(cls.ALLOWED_FILE_TYPES.keys())}"
            )
    
    @classmethod
    def get_file_size_limit(cls, file_path: Path) -> int:
        """Get size limit for file type."""
        ext = cls.get_file_extension(file_path)
        if ext in ['.jpg', '.jpeg', '.png']:
            return cls.IMAGE_MAX_SIZE
        return cls.DOCUMENT_MAX_SIZE
    
    @classmethod
    def validate_file_size(cls, file_path: Path) -> None:
        """Validate file size, raise FileSizeError if exceeds limit."""
        size = file_path.stat().st_size
        limit = cls.get_file_size_limit(file_path)
        
        if size > limit:
            size_mb = size / (1024 * 1024)
            limit_mb = limit / (1024 * 1024)
            raise FileSizeError(
                f"File '{file_path.name}' size ({size_mb:.2f} MB) exceeds "
                f"limit for this file type ({limit_mb:.2f} MB)"
            )
    
    @classmethod
    def validate_file_batch(cls, file_paths: List[Path]) -> None:
        """
        Validate a batch of files for upload.
        
        Raises:
            FileLimitError: If too many files
            FileTypeError: If any file type not allowed
            FileSizeError: If any file exceeds size limit
        """
        if len(file_paths) > cls.MAX_FILES_PER_UPLOAD:
            raise FileLimitError(
                f"Cannot upload more than {cls.MAX_FILES_PER_UPLOAD} files at once. "
                f"Got {len(file_paths)} files."
            )
        
        for file_path in file_paths:
            cls.validate_file_type(file_path)
            cls.validate_file_size(file_path)
    
    # ========== Project Directory Management ==========
    
    def get_project_dir(self, project_name: str) -> Path:
        """Get project directory path (creates if needed)."""
        project_dir = self.workspace_root / "projects" / project_name
        project_dir.mkdir(parents=True, exist_ok=True)
        return project_dir
    
    def get_project_log_path(self, project_name: str, log_name: str = "session.jsonl") -> Path:
        """Get path for project log file."""
        project_dir = self.get_project_dir(project_name)
        return project_dir / log_name
    
    # ========== Safe Read Operations ==========
    
    def read_file(self, file_path: Path, as_text: bool = True) -> str | bytes:
        """
        Read file contents with permission check.
        
        Args:
            file_path: Path to file (must be within workspace)
            as_text: If True, return as string; if False, return as bytes
        
        Returns:
            File contents as string or bytes
        
        Raises:
            PermissionError: If file is outside workspace
            FileError: If file cannot be read
        """
        # Validate path
        resolved = self.permissions.validate_path(file_path, 'read')
        
        if not resolved.exists():
            raise FileError(f"File not found: {resolved}")
        
        try:
            if as_text:
                return resolved.read_text(encoding='utf-8')
            else:
                return resolved.read_bytes()
        except Exception as e:
            raise FileError(f"Failed to read file {resolved}: {e}")
    
    def read_file_for_llm(self, file_path: Path) -> Tuple[str, str, bytes]:
        """
        Read file and validate for LLM upload.
        
        Returns:
            Tuple of (file_name, mime_type, content_bytes)
        
        Raises:
            FileTypeError: If file type not allowed
            FileSizeError: If file too large
            PermissionError: If file outside workspace
        """
        # Validate path
        resolved = self.permissions.validate_path(file_path, 'read')
        
        # Validate for LLM upload
        self.validate_file_type(resolved)
        self.validate_file_size(resolved)
        
        # Get mime type
        ext = self.get_file_extension(resolved)
        mime_type = self.ALLOWED_FILE_TYPES.get(ext, 'application/octet-stream')
        
        # Read content
        content = self.read_file(resolved, as_text=False)
        
        return resolved.name, mime_type, content
    
    # ========== Safe Write Operations ==========
    
    def write_file(self, file_path: Path, content: str | bytes, as_text: bool = True) -> Path:
        """
        Write file contents with permission check.
        
        Args:
            file_path: Path to file (must be within workspace)
            content: Content to write (string or bytes)
            as_text: If True, content is string; if False, content is bytes
        
        Returns:
            Resolved path that was written
        
        Raises:
            PermissionError: If file is outside workspace or in readonly_input
            FileError: If file cannot be written
        """
        # Validate path (write operation)
        resolved = self.permissions.validate_path(file_path, 'write')
        
        # Ensure parent directory exists
        resolved.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            if as_text:
                resolved.write_text(content, encoding='utf-8')
            else:
                resolved.write_bytes(content)
            return resolved
        except Exception as e:
            raise FileError(f"Failed to write file {resolved}: {e}")
    
    def write_project_log(self, project_name: str, data: dict, log_name: str = "session.jsonl") -> Path:
        """
        Append JSON data to project log file.
        
        Args:
            project_name: Project name
            data: Dictionary to write as JSON line
            log_name: Log file name
        
        Returns:
            Path to log file
        """
        import json
        
        log_path = self.get_project_log_path(project_name, log_name)
        
        # Add timestamp
        data['timestamp'] = datetime.now().isoformat()
        
        # Append to log file
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(data) + '\n')
        
        return log_path
    
    # ========== Delete Operations ==========
    
    def delete_file(self, file_path: Path, require_approval: bool = True) -> bool:
        """
        Delete a file with permission check.
        
        Args:
            file_path: Path to file
            require_approval: If True, check autonomy mode for approval
        
        Returns:
            True if deleted successfully
        
        Raises:
            PermissionError: If file is outside workspace or in readonly_input
            FileError: If file cannot be deleted
        """
        resolved = self.permissions.validate_path(file_path, 'delete')
        
        if not resolved.exists():
            return False
        
        # Check approval if required
        if require_approval:
            if not self.permissions.requires_approval('delete', f"Delete file: {resolved}"):
                raise PermissionError(f"Delete not approved: {resolved}")
        
        try:
            resolved.unlink()
            return True
        except Exception as e:
            raise FileError(f"Failed to delete file {resolved}: {e}")
    
    def delete_directory(self, dir_path: Path, recursive: bool = False, require_approval: bool = True) -> bool:
        """
        Delete a directory with permission check.
        
        Args:
            dir_path: Path to directory
            recursive: If True, delete all contents
            require_approval: If True, check autonomy mode for approval
        
        Returns:
            True if deleted successfully
        
        Raises:
            PermissionError: If directory is outside workspace or in readonly_input
            FileError: If directory cannot be deleted
        """
        resolved = self.permissions.validate_path(dir_path, 'delete')
        
        if not resolved.exists():
            return False
        
        if not resolved.is_dir():
            raise FileError(f"Not a directory: {resolved}")
        
        # Check approval with recursive flag
        op_name = 'recursive_delete' if recursive else 'delete'
        if require_approval:
            details = f"Delete {'recursive ' if recursive else ''}directory: {resolved}"
            if not self.permissions.requires_approval(op_name, details):
                raise PermissionError(f"Delete not approved: {resolved}")
        
        try:
            if recursive:
                shutil.rmtree(resolved)
            else:
                resolved.rmdir()
            return True
        except Exception as e:
            raise FileError(f"Failed to delete directory {resolved}: {e}")
    
    # ========== Directory Listing ==========
    
    def list_files(self, dir_path: Path, pattern: str = "*") -> List[Path]:
        """
        List files in directory with permission check.
        
        Args:
            dir_path: Directory path
            pattern: Glob pattern (default: "*")
        
        Returns:
            List of file paths (relative to workspace)
        """
        resolved = self.permissions.validate_path(dir_path, 'read')
        
        if not resolved.exists():
            return []
        
        if not resolved.is_dir():
            raise FileError(f"Not a directory: {resolved}")
        
        return list(resolved.glob(pattern))
    
    def list_project_files(self, project_name: str) -> List[Path]:
        """List all files in a project directory."""
        project_dir = self.get_project_dir(project_name)
        return self.list_files(project_dir)
    
    # ========== File Info ==========
    
    def get_file_info(self, file_path: Path) -> dict:
        """Get file metadata (size, type, etc.)."""
        resolved = self.permissions.validate_path(file_path, 'read')
        
        if not resolved.exists():
            return {'exists': False}
        
        stat = resolved.stat()
        ext = self.get_file_extension(resolved)
        
        return {
            'exists': True,
            'name': resolved.name,
            'path': str(resolved),
            'size': stat.st_size,
            'size_mb': stat.st_size / (1024 * 1024),
            'extension': ext,
            'is_allowed': self.is_file_type_allowed(resolved),
            'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
            'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
        }
    
    # ========== Batch Operations for LLM ==========
    
    def prepare_files_for_llm(self, file_paths: List[Path]) -> List[Tuple[str, str, bytes]]:
        """
        Prepare multiple files for LLM upload.
        
        Validates all files first, then reads them.
        
        Args:
            file_paths: List of file paths to prepare
        
        Returns:
            List of (file_name, mime_type, content_bytes)
        
        Raises:
            FileLimitError: If too many files
            FileTypeError: If any file type not allowed
            FileSizeError: If any file too large
        """
        # Validate all files first
        self.validate_file_batch(file_paths)
        
        # Then read all files
        results = []
        for file_path in file_paths:
            name, mime, content = self.read_file_for_llm(file_path)
            results.append((name, mime, content))
        
        return results