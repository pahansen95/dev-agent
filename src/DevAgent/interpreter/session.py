"""
Session management for the DevAgent Interpreter.

This module provides the Session class representing a persistent computational 
environment and the SessionManager class that orchestrates session lifecycles.
"""

import os
import time
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Set

from . import fs
from .kernel import KernelController, ExecutionResult

logger = logging.getLogger(__name__)

class Session:

  """A persistent computational environment with multiple kernels."""

  def __init__(self, id: str, name: str, path: Path, registry):
    """Initialize a session."""
    self.id = id
    self.name = name
    self.path = path
    self.registry = registry
    self.kernels_path = path / "kernels"
    logger.debug(f"Initialized session: {id} ({name})")

  def create_kernel(self, name: str, kernel_type: str = "python3") -> KernelController:
    """Create a new kernel in this session."""
    # Check if kernel with this name already exists
    existing_kernels = self.list_kernels()
    for kernel in existing_kernels:
      if kernel["name"] == name:
        logger.warning(f"Kernel with name {name} already exists in session {self.id}")
        kernel_id = kernel["id"]
        controller = self.registry.get_kernel_controller(kernel_id, self.path)
        if controller:
          return controller
        # If controller not found but kernel exists in metadata, remove it
        self._remove_kernel_from_metadata(kernel_id)

    # Generate kernel ID
    kernel_id = self.registry.generate_kernel_id()

    # Create the kernel
    controller = self.registry.create_kernel_controller(kernel_id=kernel_id, name=name, kernel_type=kernel_type, session_id=self.id, session_path=self.path)

    # Update session metadata
    self._add_kernel_to_metadata(kernel_id, name)

    # Register in registry and create symlinks
    self.registry.register_kernel(f"{self.name}/{name}", kernel_id)
    fs.create_symlink(self.registry.base_dir / "by-name" / self.name / name, self.path / "kernels" / kernel_id)

    return controller

  def get_kernel(self, reference: str) -> Optional[KernelController]:
    """Get a kernel by name or ID."""
    # If reference is a kernel name, not an ID
    if not reference.startswith("kid-"):
      # Check if it's a direct name
      kernel_id = None
      for kernel in self.list_kernels():
        if kernel["name"] == reference:
          kernel_id = kernel["id"]
          break

      # If not found as direct name, try the full reference
      if not kernel_id:
        full_name = f"{self.name}/{reference}"
        kernel_id = self.registry.lookup_kernel(full_name)
    else:
      # Reference is already a kernel ID
      kernel_id = reference

    if not kernel_id:
      logger.debug(f"No kernel found for reference: {reference} in session {self.id}")
      return None

    # Get controller
    controller = self.registry.get_kernel_controller(kernel_id, self.path)
    return controller

  def list_kernels(self) -> List[Dict[str, Any]]:
    """List all kernels in this session."""
    metadata = self._get_metadata()
    return metadata.get("kernels", [])

  def delete_kernel(self, reference: str) -> bool:
    """Delete a kernel from this session."""
    # Get kernel ID
    kernel = self.get_kernel(reference)
    if not kernel:
      logger.warning(f"Kernel not found for deletion: {reference}")
      return False

    kernel_id = kernel.id
    kernel_name = kernel.name

    # Delete from registry
    return self.registry.delete_kernel(kernel_id=kernel_id, session_id=self.id, session_path=self.path, kernel_name=kernel_name)

  def execute(self, kernel_reference: str, code: str) -> ExecutionResult:
    """Execute code in a kernel."""
    # Get the kernel
    kernel = self.get_kernel(kernel_reference)
    if not kernel:
      raise ValueError(f"Kernel not found: {kernel_reference}")

    # Execute the code
    result = kernel.execute(code)

    # Update session metadata with last activity
    self._update_last_activity()

    return result

  def _get_metadata(self) -> Dict[str, Any]:
    """Get session metadata."""
    metadata_path = self.path / "metadata.json"
    return fs.atomic_read_json(metadata_path, {})

  def _update_metadata(self, updates: Dict[str, Any]) -> None:
    """Update session metadata."""
    metadata_path = self.path / "metadata.json"
    with fs.FileLock(metadata_path):
      metadata = self._get_metadata()
      metadata.update(updates)
      fs.atomic_write_json(metadata_path, metadata)

  def _update_last_activity(self) -> None:
    """Update the last activity timestamp."""
    self._update_metadata({"last_activity": time.time()})

  def _add_kernel_to_metadata(self, kernel_id: str, kernel_name: str) -> None:
    """Add a kernel to session metadata."""
    metadata_path = self.path / "metadata.json"
    with fs.FileLock(metadata_path):
      metadata = self._get_metadata()

      # Check if kernels list exists
      if "kernels" not in metadata:
        metadata["kernels"] = []

      # Check if kernel already exists
      for kernel in metadata["kernels"]:
        if kernel.get("id") == kernel_id:
          # Already exists, update name
          kernel["name"] = kernel_name
          break
      else:
        # Doesn't exist, add it
        metadata["kernels"].append({"id": kernel_id, "name": kernel_name})

      # Update last activity
      metadata["last_activity"] = time.time()

      fs.atomic_write_json(metadata_path, metadata)

  def _remove_kernel_from_metadata(self, kernel_id: str) -> None:
    """Remove a kernel from session metadata."""
    metadata_path = self.path / "metadata.json"
    with fs.FileLock(metadata_path):
      metadata = self._get_metadata()

      # Remove kernel from list
      if "kernels" in metadata:
        metadata["kernels"] = [k for k in metadata["kernels"] if k.get("id") != kernel_id]

      # Update last activity
      metadata["last_activity"] = time.time()

      fs.atomic_write_json(metadata_path, metadata)

  def shutdown(self) -> None:
    """Shutdown all kernels in this session."""
    for kernel in self.list_kernels():
      kernel_id = kernel.get("id")
      if kernel_id:
        self.registry.shutdown_kernel(kernel_id)

class SessionManager:

  """Manages the lifecycle of interpreter sessions."""

  def __init__(self, base_dir: Path, registry):
    """Initialize with base directory and registry."""
    self.base_dir = base_dir
    self.registry = registry
    self.sessions_cache = {} # Cache of active sessions
    self._scan_and_cache_sessions()
    logger.debug(f"Initialized SessionManager with base_dir={base_dir}")

  def create_session(self, name: str) -> Session:
    """Create a new session or get existing one."""
    # Check if session already exists by name
    existing_id = self.registry.lookup_session(name)
    if existing_id:
      logger.debug(f"Session already exists: {name} -> {existing_id}")
      return self.get_session(existing_id)

    # Generate new ID and create session
    session_id = self.registry.generate_session_id()
    session_path = fs.create_session_directory(self.base_dir, session_id)

    # Create session metadata
    metadata = {"id": session_id, "name": name, "created_at": time.time(), "last_activity": time.time(), "kernels": []}

    fs.atomic_write_json(session_path / "metadata.json", metadata)

    # Register and create symlinks
    self.registry.register_session(name, session_id)
    fs.create_symlink_dir(self.base_dir / "by-name" / name, session_path)

    # Create and cache session object
    session = Session(session_id, name, session_path, self.registry)
    self.sessions_cache[session_id] = session

    logger.info(f"Created new session: {name} (ID: {session_id})")
    return session

  def get_session(self, reference: str) -> Optional[Session]:
    """Get a session by name or ID."""
    # Resolve reference
    resolved = self.registry.resolve_reference(reference)
    session_id = resolved.get("session_id")

    if not session_id:
      logger.debug(f"No session found for reference: {reference}")
      return None

    # Check if session is in cache
    if session_id in self.sessions_cache:
      return self.sessions_cache[session_id]

    # Try to load session from disk
    session_path = fs.get_session_path(self.base_dir, session_id)
    if not session_path.exists():
      logger.error(f"Session path not found: {session_path}")
      return None

    # Read metadata
    metadata_path = session_path / "metadata.json"
    if not metadata_path.exists():
      logger.error(f"Session metadata not found: {metadata_path}")
      return None

    metadata = fs.atomic_read_json(metadata_path)
    session_name = metadata.get("name", session_id)

    # Create and cache session
    session = Session(session_id, session_name, session_path, self.registry)
    self.sessions_cache[session_id] = session

    return session

  def list_sessions(self) -> List[Dict[str, Any]]:
    """List all available sessions."""
    return self.registry.list_sessions()

  def delete_session(self, reference: str) -> bool:
    """Delete a session."""
    # Get session
    session = self.get_session(reference)
    if not session:
      logger.warning(f"Session not found for deletion: {reference}")
      return False

    session_id = session.id

    # Shutdown all kernels
    session.shutdown()

    # Remove from cache
    if session_id in self.sessions_cache:
      del self.sessions_cache[session_id]

    # Delete from registry
    return self.registry.delete_session(session_id)

  def shutdown(self) -> None:
    """Shutdown all sessions."""
    logger.info("Shutting down all sessions")
    for session in list(self.sessions_cache.values()):
      session.shutdown()
    self.sessions_cache.clear()

  def _scan_and_cache_sessions(self) -> None:
    """Scan for existing sessions and cache them."""
    sessions_count = 0
    sessions_dir = self.base_dir / "by-id" / "sessions"
    if sessions_dir.exists():
      for session_path in sessions_dir.glob("*"):
        metadata_path = session_path / "metadata.json"
        if metadata_path.exists():
          try:
            metadata = fs.atomic_read_json(metadata_path)
            session_id = metadata.get("id")
            session_name = metadata.get("name", session_id)

            if session_id and session_id not in self.sessions_cache:
              session = Session(session_id, session_name, session_path, self.registry)
              self.sessions_cache[session_id] = session
              sessions_count += 1
          except Exception as e:
            logger.error(f"Error loading session from {metadata_path}: {e}")

    logger.info(f"Loaded {sessions_count} sessions from disk")
