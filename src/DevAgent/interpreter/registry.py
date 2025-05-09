"""
Registry for the DevAgent Interpreter.

This module provides the Registry class which handles name resolution
and kernel tracking across sessions, as well as the NameRegistry class
which manages name-to-ID mappings.

The registry system forms the backbone of the interpreter's resource
management capabilities, enabling flexible naming, reference resolution,
and centralized lifecycle management for sessions and kernels.

Key features:
- Hierarchical naming system with name-to-ID mappings
- Reference resolution from various forms (name, ID, path)
- KernelController caching and management
- Session and kernel metadata tracking
- Resource listing across the entire system
- ID generation for sessions and kernels
- Resource cleanup on shutdown
- Persistent storage of registry information

The Registry provides a higher-level interface over the NameRegistry,
adding kernel controller management and session/kernel operations.
The NameRegistry handles the lower-level name-to-ID mappings and
reference resolution.
"""

import os
import time
import logging
import uuid
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from jupyter_client import MultiKernelManager

from . import fs
from .kernel import KernelController

logger = logging.getLogger(__name__)

class NameRegistry:
    """Handles name-to-ID mappings for sessions and kernels."""
    
    def __init__(self, base_dir: Path):
        """Initialize the name registry."""
        self.base_dir = base_dir
        self.sessions_registry_path = base_dir / "registry" / "sessions.json"
        self.kernels_registry_path = base_dir / "registry" / "kernels.json"
        
        # Ensure registry directories and files exist
        (base_dir / "registry").mkdir(parents=True, exist_ok=True)
        for path in [self.sessions_registry_path, self.kernels_registry_path]:
            if not path.exists():
                fs.atomic_write_json(path, {})
        
        logger.debug(f"Initialized name registry at {base_dir}")
    
    def register_session(self, name: str, session_id: str) -> None:
        """Register a session name to ID mapping."""
        with fs.FileLock(self.sessions_registry_path):
            registry = fs.atomic_read_json(self.sessions_registry_path, {})
            registry[name] = session_id
            fs.atomic_write_json(self.sessions_registry_path, registry)
        logger.debug(f"Registered session name: {name} -> {session_id}")
    
    def register_kernel(self, full_name: str, kernel_id: str) -> None:
        """Register a kernel name to ID mapping."""
        with fs.FileLock(self.kernels_registry_path):
            registry = fs.atomic_read_json(self.kernels_registry_path, {})
            registry[full_name] = kernel_id
            fs.atomic_write_json(self.kernels_registry_path, registry)
        logger.debug(f"Registered kernel name: {full_name} -> {kernel_id}")
    
    def lookup_session(self, name_or_id: str) -> Optional[str]:
        """Look up a session ID by name or return ID if already an ID."""
        # Check if it's already an ID
        if name_or_id.startswith("sid-"):
            return name_or_id
        
        # Look up in registry
        registry = fs.atomic_read_json(self.sessions_registry_path, {})
        session_id = registry.get(name_or_id)
        
        if session_id:
            logger.debug(f"Looked up session: {name_or_id} -> {session_id}")
        else:
            logger.debug(f"No session found for: {name_or_id}")
        
        return session_id
    
    def lookup_kernel(self, reference: str) -> Optional[str]:
        """Look up a kernel ID from a reference (either full name or ID)."""
        # Check if it's already an ID
        if reference.startswith("kid-"):
            return reference
        
        # Look up in registry
        registry = fs.atomic_read_json(self.kernels_registry_path, {})
        kernel_id = registry.get(reference)
        
        if kernel_id:
            logger.debug(f"Looked up kernel: {reference} -> {kernel_id}")
        else:
            logger.debug(f"No kernel found for: {reference}")
        
        return kernel_id
    
    def resolve_reference(self, reference: str) -> Dict[str, Any]:
        """
        Resolve any reference to component IDs and paths.
        
        Returns a dict with:
        - type: "session" or "kernel" or None
        - session_id: The session ID or None
        - kernel_id: The kernel ID or None
        - session_path: Path to the session directory or None
        - kernel_path: Path to the kernel directory or None
        """
        result = {"type": None, "session_id": None, "kernel_id": None, "session_path": None, "kernel_path": None}
        
        # Case 1: Session/Kernel format
        if "/" in reference:
            session_name, kernel_name = reference.split("/", 1)
            session_id = self.lookup_session(session_name)
            if session_id:
                result["type"] = "kernel"
                result["session_id"] = session_id
                result["session_path"] = fs.get_session_path(self.base_dir, session_id)
                
                # Look up the kernel ID
                full_name = f"{session_name}/{kernel_name}"
                kernel_id = self.lookup_kernel(full_name)
                if kernel_id:
                    result["kernel_id"] = kernel_id
                    result["kernel_path"] = fs.get_kernel_path(result["session_path"], kernel_id)
                    logger.debug(f"Resolved reference {reference} to kernel {kernel_id} in session {session_id}")
                    return result
                else:
                    logger.debug(f"Resolved reference {reference} to session {session_id} but kernel not found")
                    return result
        
        # Case 2: Session name or ID
        session_id = self.lookup_session(reference)
        if session_id:
            result["type"] = "session"
            result["session_id"] = session_id
            result["session_path"] = fs.get_session_path(self.base_dir, session_id)
            logger.debug(f"Resolved reference {reference} to session {session_id}")
            return result
        
        # Case 3: Kernel ID directly
        if reference.startswith("kid-"):
            result["type"] = "kernel"
            result["kernel_id"] = reference
            
            # Find associated session by scanning
            session_path = fs.find_session_for_kernel(self.base_dir, reference)
            if session_path:
                session_metadata = fs.atomic_read_json(session_path / "metadata.json", {})
                result["session_id"] = session_metadata.get("id")
                result["session_path"] = session_path
                result["kernel_path"] = fs.get_kernel_path(session_path, reference)
                logger.debug(f"Resolved reference {reference} to kernel in session {result['session_id']}")
                return result
            
            logger.debug(f"Resolved reference {reference} to kernel but couldn't find session")
            return result
        
        logger.debug(f"Could not resolve reference: {reference}")
        return result
    
    def unregister_session(self, name: str) -> None:
        """Remove a session name from registry."""
        with fs.FileLock(self.sessions_registry_path):
            registry = fs.atomic_read_json(self.sessions_registry_path, {})
            if name in registry:
                del registry[name]
                logger.debug(f"Unregistered session name: {name}")
            fs.atomic_write_json(self.sessions_registry_path, registry)
    
    def unregister_kernel(self, full_name: str) -> None:
        """Remove a kernel name from registry."""
        with fs.FileLock(self.kernels_registry_path):
            registry = fs.atomic_read_json(self.kernels_registry_path, {})
            if full_name in registry:
                del registry[full_name]
                logger.debug(f"Unregistered kernel name: {full_name}")
            fs.atomic_write_json(self.kernels_registry_path, registry)

class Registry:

  """Coordinates between name registry and kernel operations."""

  def __init__(self, base_dir: Path):
    """Initialize the registry."""
    self.base_dir = base_dir

    # Ensure registry directories exist
    (base_dir / "registry").mkdir(parents=True, exist_ok=True)

    # Initialize name registry
    self.name_registry = NameRegistry(base_dir)

    # Multi-kernel manager for active kernels
    self.mkm = MultiKernelManager()

    # In-memory cache of kernel controllers
    self.kernel_controllers = {}

    logger.debug(f"Initialized registry at {base_dir}")

  def generate_session_id(self) -> str:
    """Generate a unique session ID."""
    return f"sid-{uuid.uuid4().hex[:8]}"

  def generate_kernel_id(self) -> str:
    """Generate a unique kernel ID."""
    return f"kid-{uuid.uuid4().hex[:8]}"

  # Delegate name registry operations
  def register_session(self, name: str, session_id: str) -> None:
    """Register a session name to ID mapping."""
    self.name_registry.register_session(name, session_id)

  def register_kernel(self, full_name: str, kernel_id: str) -> None:
    """Register a kernel name to ID mapping."""
    self.name_registry.register_kernel(full_name, kernel_id)

  def lookup_session(self, name_or_id: str) -> Optional[str]:
    """Look up a session ID by name or return ID if already an ID."""
    return self.name_registry.lookup_session(name_or_id)

  def lookup_kernel(self, reference: str) -> Optional[str]:
    """Look up a kernel ID from a reference (either full name or ID)."""
    return self.name_registry.lookup_kernel(reference)

  def resolve_reference(self, reference: str) -> Dict[str, Any]:
    """Resolve any reference to component IDs and paths."""
    return self.name_registry.resolve_reference(reference)

  def get_kernel_controller(self, kernel_id: str, session_path: Path) -> Optional[KernelController]:
    """
    Get or create a KernelController for a kernel ID.
    
    Args:
        kernel_id: The kernel ID
        session_path: Path to the session directory
        
    Returns:
        KernelController or None if not found
    """
    # Check if we already have a controller for this kernel
    if kernel_id in self.kernel_controllers:
        controller = self.kernel_controllers[kernel_id]
        if controller.is_alive():
            return controller
        else:
            # Kernel is dead, remove from cache
            del self.kernel_controllers[kernel_id]
    
    # Get the kernel directory
    kernel_path = fs.get_kernel_path(session_path, kernel_id)
    if not kernel_path.exists():
        logger.error(f"Kernel directory not found: {kernel_path}")
        return None
    
    # Read kernel metadata
    metadata_path = kernel_path / "metadata.json"
    connection_path = kernel_path / "connection.json"
    
    if not metadata_path.exists():
        logger.error(f"Kernel metadata not found: {metadata_path}")
        return None
    
    metadata = fs.atomic_read_json(metadata_path)
    
    # Create workspace directory if it doesn't exist
    workspace_path = kernel_path / "workspace"
    workspace_path.mkdir(exist_ok=True)
    
    # Create controller based on connection info
    if connection_path.exists():
        # Try to reconnect to existing kernel
        connection_info = fs.atomic_read_json(connection_path)
        connection_info["kernel_id"] = kernel_id
        connection_info["name"] = metadata.get("name", "unknown")
        connection_info["kernel_type"] = metadata.get("kernel_type", "python3")
        connection_info["session_id"] = metadata.get("session_id")
        
        # Create controller from connection info
        controller = KernelController.from_connection_info(connection_info, workspace_path)
    else:
        # Create a new controller
        controller = KernelController(
            id=kernel_id,
            name=metadata.get("name", "unknown"),
            kernel_type=metadata.get("kernel_type", "python3"),
            session_id=metadata.get("session_id"),
            workspace_dir=workspace_path)
    
    # Cache the controller
    self.kernel_controllers[kernel_id] = controller
    return controller

  def create_kernel_controller(self, kernel_id: str, name: str, kernel_type: str, 
                               session_id: str, session_path: Path) -> KernelController:
    """
    Create a new KernelController.
    
    Args:
        kernel_id: The kernel ID
        name: The kernel name
        kernel_type: The kernel type
        session_id: The session ID
        session_path: Path to the session directory
        
    Returns:
        KernelController
    """
    # Create kernel directory
    kernel_path = fs.create_kernel_directory(session_path, kernel_id)
    workspace_path = kernel_path / "workspace"
    
    # Create metadata
    metadata = {
        "id": kernel_id,
        "name": name,
        "kernel_type": kernel_type,
        "session_id": session_id,
        "created_at": time.time(),
        "last_activity": time.time()
    }
    
    fs.atomic_write_json(kernel_path / "metadata.json", metadata)
    
    # Create controller
    controller = KernelController(
        id=kernel_id,
        name=name,
        kernel_type=kernel_type,
        session_id=session_id,
        workspace_dir=workspace_path)
    
    # Start the kernel
    controller.start_kernel()
    
    # Save connection info
    fs.atomic_write_json(kernel_path / "connection.json", controller.get_connection_info())
    
    # Cache the controller
    self.kernel_controllers[kernel_id] = controller
    
    logger.info(f"Created new kernel controller: {kernel_id} ({name})")
    return controller

  def shutdown_kernel(self, kernel_id: str) -> bool:
    """Shutdown a specific kernel."""
    controller = self.kernel_controllers.get(kernel_id)
    if controller:
        success = controller.shutdown()
        if success:
            del self.kernel_controllers[kernel_id]
        return success
    return False

  def shutdown_all(self) -> None:
    """Shutdown all managed kernels."""
    logger.info(f"Shutting down all kernels: {len(self.kernel_controllers)}")
    for kernel_id, controller in list(self.kernel_controllers.items()):
        controller.shutdown()
    self.kernel_controllers.clear()

  def list_sessions(self) -> List[Dict[str, Any]]:
    """List all sessions."""
    sessions = []
    sessions_dir = self.base_dir / "by-id" / "sessions"
    
    # Scan session directories
    for session_path in sessions_dir.glob("*"):
        metadata_path = session_path / "metadata.json"
        if metadata_path.exists():
            metadata = fs.atomic_read_json(metadata_path)
            
            # Find reverse mapping (ID to name)
            session_id = metadata.get("id")
            name = metadata.get("name", session_id)
            
            sessions.append({
                "id": session_id,
                "name": name,
                "path": str(session_path),
                "created_at": metadata.get("created_at"),
                "last_activity": metadata.get("last_activity"),
                "kernels": metadata.get("kernels", [])
            })
    
    return sessions

  def list_kernels(self, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """List all kernels, optionally filtered by session."""
    kernels = []
    sessions_dir = self.base_dir / "by-id" / "sessions"
    
    # If session_id provided, only look in that session
    if session_id:
        session_paths = [sessions_dir / session_id]
    else:
        session_paths = list(sessions_dir.glob("*"))
    
    # Scan kernels in sessions
    for session_path in session_paths:
        if not session_path.exists():
            continue
        
        session_metadata = fs.atomic_read_json(session_path / "metadata.json", {})
        session_id = session_metadata.get("id")
        
        for kernel_path in (session_path / "kernels").glob("*"):
            metadata_path = kernel_path / "metadata.json"
            if metadata_path.exists():
                metadata = fs.atomic_read_json(metadata_path)
                
                # Check if kernel is alive
                kernel_id = metadata.get("id")
                controller = self.kernel_controllers.get(kernel_id)
                is_alive = controller is not None and controller.is_alive()
                
                kernels.append({
                    "id": kernel_id,
                    "name": metadata.get("name", kernel_id),
                    "kernel_type": metadata.get("kernel_type"),
                    "session_id": session_id,
                    "path": str(kernel_path),
                    "created_at": metadata.get("created_at"),
                    "last_activity": metadata.get("last_activity"),
                    "alive": is_alive
                })
    
    return kernels

  def delete_session(self, session_id: str) -> bool:
    """Delete a session and all its kernels."""
    logger.info(f"Deleting session: {session_id}")
    
    # Get session path
    session_path = fs.get_session_path(self.base_dir, session_id)
    if not session_path.exists():
        logger.error(f"Session path not found: {session_path}")
        return False
    
    # Get session metadata
    metadata_path = session_path / "metadata.json"
    if metadata_path.exists():
        metadata = fs.atomic_read_json(metadata_path)
        session_name = metadata.get("name")
        
        # Remove symlinks
        if session_name:
            symlink_path = self.base_dir / "by-name" / session_name
            fs.remove_directory(symlink_path)
            
            # Remove from registry
            self.name_registry.unregister_session(session_name)
        
        # Shutdown all kernels in the session
        for kernel_item in metadata.get("kernels", []):
            kernel_id = kernel_item.get("id")
            if kernel_id:
                self.shutdown_kernel(kernel_id)
                
                # Remove kernel from registry
                kernel_name = kernel_item.get("name")
                if kernel_name and session_name:
                    full_name = f"{session_name}/{kernel_name}"
                    self.name_registry.unregister_kernel(full_name)
    
    # Remove session directory
    return fs.remove_directory(session_path)

  def delete_kernel(self, kernel_id: str, session_id: str, session_path: Path, kernel_name: Optional[str] = None) -> bool:
    """Delete a kernel."""
    logger.info(f"Deleting kernel: {kernel_id}")
    
    # Shutdown the kernel
    self.shutdown_kernel(kernel_id)
    
    # Get kernel path
    kernel_path = fs.get_kernel_path(session_path, kernel_id)
    if not kernel_path.exists():
        logger.error(f"Kernel path not found: {kernel_path}")
        return False
    
    # Update session metadata
    metadata_path = session_path / "metadata.json"
    if metadata_path.exists():
        with fs.FileLock(metadata_path):
            metadata = fs.atomic_read_json(metadata_path)
            
            # Filter out this kernel
            metadata["kernels"] = [k for k in metadata.get("kernels", []) if k.get("id") != kernel_id]
            
            # Update last activity
            metadata["last_activity"] = time.time()
            
            fs.atomic_write_json(metadata_path, metadata)
            
            # Get session name for registry
            session_name = metadata.get("name")
    
    # Remove from registry
    if kernel_name and session_name:
        full_name = f"{session_name}/{kernel_name}"
        self.name_registry.unregister_kernel(full_name)
    
    # Remove symlink
    if kernel_name and session_name:
        symlink_path = self.base_dir / "by-name" / session_name / kernel_name
        if symlink_path.exists() or symlink_path.is_symlink():
            try:
                symlink_path.unlink()
            except Exception as e:
                logger.error(f"Error removing symlink {symlink_path}: {e}")
    
    # Remove kernel directory
    return fs.remove_directory(kernel_path)
