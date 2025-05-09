"""
API for the DevAgent Interpreter.

This module provides the InterpreterAPI class which is the primary entry point 
for external consumers to interact with the interpreter. The API offers a complete
suite of operations for managing sessions and kernels, including creation, retrieval,
listing, and deletion of these resources, as well as code execution within kernels.

The InterpreterAPI handles all the complexity of session and kernel management,
including reference resolution (by name or ID), resource lifecycle management,
and maintaining the filesystem-based persistence layer.

Key responsibilities:
- Session management (create, get, list, delete)
- Kernel management across sessions (create, get, list, delete)
- Code execution in kernels
- Reference resolution (session/kernel names or IDs)
- Resource cleanup on shutdown
"""

import os
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

from . import fs
from .kernel import KernelController, ExecutionResult
from .registry import Registry
from .session import Session, SessionManager

logger = logging.getLogger(__name__)

class InterpreterAPI:

  """Primary entry point for the DevAgent Interpreter."""

  def __init__(self, base_dir: Optional[Path] = None):
    """
        Initialize with base directory for all interpreter data.
        
        Args:
            base_dir: Base directory path. If None, uses current directory.
        """
    # Set up base directory
    if base_dir is None: self.base_dir = base_dir
    else: self.base_dir = Path(os.getcwd())
    self.base_dir.mkdir(parents=True, exist_ok=True)

    # Ensure directory structure
    fs.ensure_directory_structure(self.base_dir)

    # Create registry and session manager
    self.registry = Registry(self.base_dir)
    self.session_manager = SessionManager(self.base_dir, self.registry)

    logger.info(f"Initialized InterpreterAPI with base_dir={self.base_dir}")

  def create_session(self, name: str) -> Session:
    """
        Create a new session.
        
        Args:
            name: Human-readable name for the session
            
        Returns:
            Session object
        """
    return self.session_manager.create_session(name)

  def get_session(self, reference: str) -> Optional[Session]:
    """
        Get a session by name or ID.
        
        Args:
            reference: Session name or ID
            
        Returns:
            Session object or None if not found
        """
    return self.session_manager.get_session(reference)

  def list_sessions(self) -> List[Dict[str, Any]]:
    """
        List all available sessions.
        
        Returns:
            List of session descriptors (dicts with id, name, path, etc.)
        """
    return self.session_manager.list_sessions()

  def delete_session(self, reference: str) -> bool:
    """
        Delete a session.
        
        Args:
            reference: Session name or ID
            
        Returns:
            True if deleted, False if not found
        """
    return self.session_manager.delete_session(reference)

  def create_kernel(self, session_reference: str, kernel_name: str, kernel_type: str = "python3") -> KernelController:
    """
        Create a new kernel in a session.
        
        Args:
            session_reference: Session name or ID
            kernel_name: Human-readable name for the kernel
            kernel_type: Type of kernel (default: "python3")
            
        Returns:
            KernelController for the new kernel
            
        Raises:
            ValueError: If session not found
        """
    session = self.get_session(session_reference)
    if not session:
      raise ValueError(f"Session not found: {session_reference}")

    return session.create_kernel(kernel_name, kernel_type)

  def get_kernel(self, reference: str) -> Optional[KernelController]:
    """
        Get a kernel by reference (session/kernel or kernel_id).
        
        Args:
            reference: Session/kernel name or kernel ID
            
        Returns:
            KernelController or None if not found
        """
    # Parse reference to find session and kernel
    if "/" in reference:
      # Session/kernel format
      session_name, kernel_name = reference.split("/", 1)
      session = self.get_session(session_name)
      if not session:
        logger.warning(f"Session not found: {session_name}")
        return None

      return session.get_kernel(kernel_name)
    elif reference.startswith("kid-"):
      # Direct kernel ID
      resolved = self.registry.resolve_reference(reference)
      session_id = resolved.get("session_id")
      kernel_id = resolved.get("kernel_id")

      if not session_id or not kernel_id:
        logger.warning(f"Could not resolve kernel reference: {reference}")
        return None

      session = self.get_session(session_id)
      if not session:
        logger.warning(f"Session not found for kernel: {reference}")
        return None

      return session.get_kernel(kernel_id)
    else:
      # Ambiguous reference - could be session name or kernel name
      # Try as session name first
      session = self.get_session(reference)
      if session:
        # It's a session, but we need a kernel
        logger.warning(f"Reference is a session, not a kernel: {reference}")
        return None

      # Try finding in all sessions (first match)
      for session_info in self.list_sessions():
        session = self.get_session(session_info["id"])
        if not session:
          continue

        kernel = session.get_kernel(reference)
        if kernel:
          return kernel

      logger.warning(f"No kernel found for reference: {reference}")
      return None

  def list_kernels(self, session_reference: Optional[str] = None) -> List[Dict[str, Any]]:
    """
        List all kernels, optionally filtered by session.
        
        Args:
            session_reference: Session name or ID (optional)
            
        Returns:
            List of kernel descriptors
        """
    if session_reference:
      session = self.get_session(session_reference)
      if not session:
        logger.warning(f"Session not found: {session_reference}")
        return []

      return session.list_kernels()
    else:
      # List all kernels across all sessions
      return self.registry.list_kernels()

  def delete_kernel(self, reference: str) -> bool:
    """
        Delete a kernel.
        
        Args:
            reference: Session/kernel name or kernel ID
            
        Returns:
            True if deleted, False if not found
        """
    # Get the kernel
    if "/" in reference:
      # Session/kernel format
      session_name, kernel_name = reference.split("/", 1)
      session = self.get_session(session_name)
      if not session:
        logger.warning(f"Session not found: {session_name}")
        return False

      return session.delete_kernel(kernel_name)
    else:
      # Direct kernel ID or name
      kernel = self.get_kernel(reference)
      if not kernel:
        logger.warning(f"Kernel not found: {reference}")
        return False

      # Find the session
      resolved = self.registry.resolve_reference(kernel.id)
      session_id = resolved.get("session_id")
      if not session_id:
        logger.warning(f"Session not found for kernel: {reference}")
        return False

      session = self.get_session(session_id)
      if not session:
        logger.warning(f"Session not found for kernel: {reference}")
        return False

      return session.delete_kernel(kernel.id)

  def execute_code(self, reference: str, code: str) -> ExecutionResult:
    """
        Execute code in a kernel.
        
        Args:
            reference: Session/kernel name or kernel ID
            code: Code to execute
            
        Returns:
            ExecutionResult with stdout, error, etc.
            
        Raises:
            ValueError: If kernel not found
        """
    # Get the kernel
    if "/" in reference:
      # Session/kernel format
      session_name, kernel_name = reference.split("/", 1)
      session = self.get_session(session_name)
      if not session:
        raise ValueError(f"Session not found: {session_name}")

      return session.execute(kernel_name, code)
    else:
      # Direct kernel ID or name
      kernel = self.get_kernel(reference)
      if not kernel:
        raise ValueError(f"Kernel not found: {reference}")

      return kernel.execute(code)

  def shutdown(self) -> None:
    """Shutdown all sessions and kernels."""
    logger.info("Shutting down interpreter")
    self.session_manager.shutdown()
    self.registry.shutdown_all()
