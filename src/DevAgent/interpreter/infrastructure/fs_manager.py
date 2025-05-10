import json
import os
import shutil
import fcntl
import logging
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

class FileLock:

  """A simple file-based lock for thread safety."""

  def __init__(self, path: Path):
    """
        Initialize a file lock.
        
        Args:
            path: The path to the file to lock
        """
    self.path = path
    self.lock_path = path.with_suffix(path.suffix + '.lock')
    self.lock_file = None

  def __enter__(self):
    """Acquire the lock."""
    try:
      self.lock_file = open(self.lock_path, 'w')
      fcntl.flock(self.lock_file, fcntl.LOCK_EX)
      return self
    except Exception as e:
      logger.error(f"Error acquiring lock for {self.path}: {e}")
      if self.lock_file:
        self.lock_file.close()
      raise

  def __exit__(self, exc_type, exc_val, exc_tb):
    """Release the lock."""
    if self.lock_file:
      try:
        fcntl.flock(self.lock_file, fcntl.LOCK_UN)
        self.lock_file.close()
        self.lock_path.unlink(missing_ok=True)
      except Exception as e:
        logger.error(f"Error releasing lock for {self.path}: {e}")

class FileSystemManager:

  """Manages filesystem operations for the interpreter."""

  def __init__(self, base_dir: Path):
    """
        Initialize the file system manager.
        
        Args:
            base_dir: The base directory for all interpreter files
        """
    self.base_dir = base_dir

  def ensure_directory_structure(self) -> None:
    """Ensure the basic directory structure exists."""
    (self.base_dir / "by-name").mkdir(parents=True, exist_ok=True)
    (self.base_dir / "by-id" / "sessions").mkdir(parents=True, exist_ok=True)
    (self.base_dir / "registry").mkdir(parents=True, exist_ok=True)
    logger.debug(f"Ensured directory structure at {self.base_dir}")

  def create_session_directory(self, session_id: str) -> Path:
    """
        Create a session directory and return its path.
        
        Args:
            session_id: The session ID
            
        Returns:
            The path to the created session directory
        """
    session_path = self.base_dir / "by-id" / "sessions" / session_id
    session_path.mkdir(parents=True, exist_ok=True)
    (session_path / "kernels").mkdir(exist_ok=True)
    logger.debug(f"Created session directory: {session_path}")
    return session_path

  def create_kernel_directory(self, session_path: Path, kernel_id: str) -> Path:
    """
        Create a kernel directory within a session and return its path.
        
        Args:
            session_path: The path to the session directory
            kernel_id: The kernel ID
            
        Returns:
            The path to the created kernel directory
        """
    kernel_path = session_path / "kernels" / kernel_id
    kernel_path.mkdir(parents=True, exist_ok=True)
    workspace_path = kernel_path / "workspace"
    workspace_path.mkdir(exist_ok=True)
    logger.debug(f"Created kernel directory: {kernel_path}")
    return kernel_path

  def get_session_path(self, session_id: str) -> Path:
    """
        Get the path to a session directory.
        
        Args:
            session_id: The session ID
            
        Returns:
            The path to the session directory
        """
    return self.base_dir / "by-id" / "sessions" / session_id

  def get_kernel_path(self, session_path: Path, kernel_id: str) -> Path:
    """
        Get the path to a kernel directory.
        
        Args:
            session_path: The path to the session directory
            kernel_id: The kernel ID
            
        Returns:
            The path to the kernel directory
        """
    return session_path / "kernels" / kernel_id

  def atomic_write_json(self, path: Path, data: Dict[str, Any]) -> None:
    """
        Write JSON data to a file atomically.
        
        Args:
            path: The path to write to
            data: The data to write
        """
    # Create parent directory if it doesn't exist
    path.parent.mkdir(parents=True, exist_ok=True)

    # Write to a temporary file first
    fd, temp_path = tempfile.mkstemp(dir=path.parent)
    try:
      with os.fdopen(fd, 'w') as f:
        json.dump(data, f, indent=2)

      # Acquire lock
      with FileLock(path):
        # Replace the file atomically
        os.replace(temp_path, path)
    except Exception as e:
      logger.error(f"Error writing JSON to {path}: {e}")
      # Clean up temp file if it still exists
      try:
        os.unlink(temp_path)
      except (OSError, FileNotFoundError):
        pass
      raise

  def atomic_read_json(self, path: Path, default: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
        Read JSON data from a file, returning default if file doesn't exist.
        
        Args:
            path: The path to read from
            default: The default value to return if the file doesn't exist
            
        Returns:
            The read data or the default
        """
    if default is None:
      default = {}

    if not path.exists():
      return default

    try:
      with FileLock(path):
        with open(path, 'r') as f:
          return json.load(f)
    except json.JSONDecodeError as e:
      logger.error(f"Error decoding JSON from {path}: {e}")
      return default
    except Exception as e:
      logger.error(f"Error reading JSON from {path}: {e}")
      return default

  def create_symlink(self, source: Path, target: Path) -> bool:
    """
        Create a symlink.
        
        Args:
            source: The source path (symlink)
            target: The target path (what the symlink points to)
            
        Returns:
            True if successful, False otherwise
        """
    try:
      source.parent.mkdir(parents=True, exist_ok=True)

      # Remove existing symlink if it exists
      if source.is_symlink() or source.exists():
        source.unlink()

      # Create relative symlink
      os.symlink(os.path.relpath(target, source.parent), source, target_is_directory=True)
      return True
    except Exception as e:
      logger.error(f"Error creating symlink from {source} to {target}: {e}")
      return False

  def remove_directory(self, path: Path) -> bool:
    """
        Remove a directory and all its contents.
        
        Args:
            path: The path to remove
            
        Returns:
            True if successful, False otherwise
        """
    try:
      if path.exists():
        shutil.rmtree(path)
      return True
    except Exception as e:
      logger.error(f"Error removing directory {path}: {e}")
      return False
