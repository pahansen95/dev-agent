"""
Filesystem operations for the DevAgent Interpreter.

This module provides the essential filesystem operations needed by the
interpreter, including directory structure management, atomic file
operations, symlink handling, path resolution, and thread-safe file access.

Key features:
- Directory structure management for sessions and kernels
- Atomic JSON file operations for reliable persistence
- Symlink creation and management for by-name access
- Path resolution utilities for sessions and kernels
- Thread-safe file operations via FileLock
- Error-resilient directory and file operations

The filesystem structure is organized as follows:
- base_dir/
  - by-id/            # Storage by ID
    - sessions/       # Session directories by ID
      - sid-*/        # Individual session directories
        - kernels/    # Kernels for this session
          - kid-*/    # Individual kernel directories
            - workspace/  # Kernel working directory
            - metadata.json  # Kernel metadata
            - connection.json # Kernel connection info
        - metadata.json  # Session metadata
  - by-name/         # Symlinks to sessions by name
    - session-name/  # Symlink to session directory
      - kernel-name/  # Symlinks to kernel directories
  - registry/        # Name-to-ID mappings
    - sessions.json  # Session name to ID mappings
    - kernels.json   # Kernel name to ID mappings
"""

import os
import json
import fcntl
import shutil
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

def ensure_directory_structure(base_dir: Path) -> None:
  """Ensure the basic directory structure exists."""
  # Create top-level directories
  (base_dir / "by-name").mkdir(parents=True, exist_ok=True)
  (base_dir / "by-id" / "sessions").mkdir(parents=True, exist_ok=True)
  (base_dir / "registry").mkdir(parents=True, exist_ok=True)
  logger.debug(f"Ensured directory structure at {base_dir}")

def create_session_directory(base_dir: Path, session_id: str) -> Path:
  """Create a session directory and return its path."""
  session_path = base_dir / "by-id" / "sessions" / session_id
  session_path.mkdir(parents=True, exist_ok=True)
  (session_path / "kernels").mkdir(exist_ok=True)
  logger.debug(f"Created session directory: {session_path}")
  return session_path

def create_kernel_directory(session_path: Path, kernel_id: str) -> Path:
  """Create a kernel directory within a session and return its path."""
  kernel_path = session_path / "kernels" / kernel_id
  kernel_path.mkdir(parents=True, exist_ok=True)
  workspace_path = kernel_path / "workspace"
  workspace_path.mkdir(exist_ok=True)
  logger.debug(f"Created kernel directory: {kernel_path}")
  return kernel_path

def get_session_path(base_dir: Path, session_id: str) -> Path:
  """Get the path to a session directory."""
  return base_dir / "by-id" / "sessions" / session_id

def get_kernel_path(session_path: Path, kernel_id: str) -> Path:
  """Get the path to a kernel directory."""
  return session_path / "kernels" / kernel_id

def atomic_write_json(path: Path, data: Dict[str, Any]) -> None:
  """Write JSON data to a file atomically."""
  # Write to a temporary file
  temp_path = path.with_suffix('.tmp')
  try:
    with open(temp_path, 'w') as f:
      json.dump(data, f, indent=2)

    # Rename atomically (atomic on Linux)
    os.rename(temp_path, path)
    logger.debug(f"Atomic write to {path}")
  except Exception as e:
    logger.error(f"Error writing to {path}: {e}")
    if temp_path.exists():
      try:
        temp_path.unlink()
      except:
        pass
    raise

def atomic_read_json(path: Path, default: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
  """Read JSON data from a file, returning default if file doesn't exist."""
  if not path.exists():
    return default or {}

  try:
    with open(path, 'r') as f:
      return json.load(f)
  except Exception as e:
    logger.error(f"Error reading from {path}: {e}")
    return default or {}

def atomic_update_json(path: Path, updates: Dict[str, Any]) -> Dict[str, Any]:
  """Update specific fields in a JSON file atomically."""
  with FileLock(path):
    data = atomic_read_json(path, {})
    data.update(updates)
    atomic_write_json(path, data)
  return data

def create_symlink(source: Path, target: Path) -> bool:
  """Create a symlink (Linux only)."""
  try:
    # Make parent directory if it doesn't exist
    source.parent.mkdir(parents=True, exist_ok=True)

    # Remove existing symlink if present
    if source.exists() or source.is_symlink():
      source.unlink()

    # Create relative symlink
    relative_path = os.path.relpath(target, source.parent)
    os.symlink(relative_path, source, target_is_dir=target.is_dir())
    logger.debug(f"Created symlink: {source} -> {relative_path}")
    return True
  except Exception as e:
    logger.error(f"Error creating symlink {source} -> {target}: {e}")
    return False

def create_symlink_dir(source: Path, target: Path) -> bool:
  """Create a directory for symlinks."""
  try:
    # Make parent directory if it doesn't exist
    source.parent.mkdir(parents=True, exist_ok=True)

    # Remove existing directory if present
    if source.exists():
      if source.is_symlink():
        source.unlink()
      else:
        shutil.rmtree(source)

    # Create directory
    source.mkdir(parents=True, exist_ok=True)
    logger.debug(f"Created symlink directory: {source}")
    return True
  except Exception as e:
    logger.error(f"Error creating symlink directory {source}: {e}")
    return False

def remove_directory(path: Path) -> bool:
  """Remove a directory and all its contents."""
  try:
    if path.exists() or path.is_symlink():
      if path.is_symlink():
        path.unlink()
      else:
        shutil.rmtree(path)
      logger.debug(f"Removed directory: {path}")
    return True
  except Exception as e:
    logger.error(f"Error removing directory {path}: {e}")
    return False

def find_session_for_kernel(base_dir: Path, kernel_id: str) -> Optional[Path]:
  """Find the session directory containing a kernel."""
  for session_dir in (base_dir / "by-id" / "sessions").glob("*"):
    kernel_path = session_dir / "kernels" / kernel_id
    if kernel_path.exists():
      return session_dir
  return None

def resolve_kernel_paths(base_dir: Path, kernel_id: str) -> tuple[Optional[Path], Optional[Path]]:
  """
  Resolve a kernel ID to session and kernel paths.
  
  Args:
      base_dir: Base directory for interpreter
      kernel_id: The kernel ID
      
  Returns:
      Tuple of (session_path, kernel_path) or (None, None) if not found
  """
  session_path = find_session_for_kernel(base_dir, kernel_id)
  if not session_path:
    return None, None
  
  kernel_path = get_kernel_path(session_path, kernel_id)
  return session_path, kernel_path

def resolve_session_reference(base_dir: Path, reference: str) -> Optional[Path]:
  """
  Resolve a session reference to a path.
  
  Args:
      base_dir: Base directory for interpreter
      reference: Session name or ID
      
  Returns:
      Path to session directory or None if not found
  """
  # If it's a session ID
  if reference.startswith("sid-"):
    return get_session_path(base_dir, reference)
  
  # Otherwise it should be a symlink in by-name
  symlink_path = base_dir / "by-name" / reference
  if symlink_path.exists() and symlink_path.is_symlink():
    return symlink_path.resolve()
  
  return None

class FileLock:

  """A simple file-based lock (Linux only)."""

  def __init__(self, path: Path):
    """Initialize with the path to protect."""
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
        self.lock_path.unlink()
      except Exception as e:
        logger.error(f"Error releasing lock for {self.path}: {e}")
