"""
CLI Facade for the Event-Driven DevAgent Interpreter.

This module provides a simplified interface for the CLI to interact with the
interpreter subsystem, abstracting away the details of the domain model,
event system, and infrastructure components.
"""

import os
import logging
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
import uuid

from ..domain.model import Session, Kernel, KernelRuntimeState
from ..domain.value_objects import SessionId, KernelId, KernelStatus, ExecutionResult
from ..domain.repositories import SessionRepository, KernelRepository, RuntimeStateRepository
from ..domain.events import (SessionCreated, KernelCreated, KernelStarted, KernelShutdown, KernelDesiredStateChanged, KernelStateReconciled)
from ..domain.factories import SessionFactory, KernelFactory
from ..infrastructure.fs_manager import FileSystemManager
from ..infrastructure.repositories import (FileSystemSessionRepository, FileSystemKernelRepository, FileSystemRuntimeStateRepository)
from ..infrastructure.fs_event_bus import FileSystemEventBus
from ..infrastructure.kernel_operator import KernelOperator
from ..infrastructure.kernel_adapter import KernelControllerAdapter

logger = logging.getLogger(__name__)

class EventDrivenInterpreterFacade:

  """
    Event-driven facade for the interpreter subsystem.
    
    This class provides a simplified interface for the CLI to interact with
    the interpreter, abstracting away the details of the domain model and
    infrastructure components.
    """

  def __init__(self, base_dir: Path, consumer_id: Optional[str] = None):
    """
        Initialize the interpreter facade.
        
        Args:
            base_dir: Base directory for all interpreter files
            consumer_id: Optional consumer ID for event bus
        """
    self.base_dir = base_dir
    self.consumer_id = consumer_id or f"cli-{uuid.uuid4().hex[:8]}"

    # Initialize infrastructure
    self.fs_manager = FileSystemManager(base_dir)
    self.fs_manager.ensure_directory_structure()

    # Initialize event bus
    self.event_bus = FileSystemEventBus(base_dir, self.consumer_id)

    # Initialize repositories
    self.session_repo = FileSystemSessionRepository(self.fs_manager, self.event_bus)
    self.kernel_repo = FileSystemKernelRepository(self.fs_manager, self.event_bus)
    self.runtime_repo = FileSystemRuntimeStateRepository(self.fs_manager, self.event_bus)

    # Initialize domain factories
    self.session_factory = SessionFactory(self.session_repo, self.event_bus)
    self.kernel_factory = KernelFactory(self.kernel_repo, self.event_bus)

    # Initialize kernel adapter
    self.kernel_adapter = KernelControllerAdapter(self.base_dir)

    # Initialize kernel operator
    self.kernel_operator = KernelOperator(base_dir=self.base_dir, event_bus=self.event_bus, runtime_repo=self.runtime_repo, kernel_repo=self.kernel_repo)

    # Start kernel operator
    self.kernel_operator.start()

    logger.info(f"Initialized interpreter facade with base_dir={base_dir}")

  def create_session(self, name: str) -> Dict[str, Any]:
    """
        Create a new session.
        
        Args:
            name: Session name
            
        Returns:
            Session metadata
        """
    # Check if session with this name already exists
    existing_session = self.session_repo.find_by_name(name)
    if existing_session:
      return {"success": True, "session_id": str(existing_session.id), "error": None}

    # Create new session
    session = self.session_factory.create_session(name)
    self.session_repo.save(session)

    # Publish event
    self.event_bus.publish(SessionCreated(session_id=session.id, name=session.name, timestamp=time.time()))

    return {"success": True, "session_id": str(session.id), "error": None}

  def get_session(self, reference: str) -> Dict[str, Any]:
    """
        Get a session by name or ID.
        
        Args:
            reference: Session name or ID
            
        Returns:
            Session metadata, or None if not found
        """
    # Try to find by ID first
    if reference.startswith("sid-"):
      session = self.session_repo.find_by_id(SessionId(reference))
    else:
      # Try to find by name
      session = self.session_repo.find_by_name(reference)

    if not session:
      return {"success": False, "session": None, "error": f"Session not found: {reference}"}

    # Get kernel count
    kernels = self.kernel_repo.find_by_session_id(session.id)

    # Convert to dict
    session_dict = {
      "id": str(session.id),
      "name": session.name,
      "created_at": session.created_at,
      "last_activity": session.last_activity,
      "kernel_count": len(kernels)
    }

    return {"success": True, "session": session_dict, "error": None}

  def list_sessions(self) -> Dict[str, Any]:
    """
        List all sessions.
        
        Returns:
            List of session metadata
        """
    sessions = self.session_repo.list_all()

    # Convert to dict
    session_dicts = []
    for session in sessions:
      # Get kernel count
      kernels = self.kernel_repo.find_by_session_id(session.id)

      session_dicts.append(
        {
          "id": str(session.id),
          "name": session.name,
          "created_at": session.created_at,
          "last_activity": session.last_activity,
          "kernel_count": len(kernels)
        })

    return {"success": True, "sessions": session_dicts, "error": None}

  def delete_session(self, reference: str) -> Dict[str, Any]:
    """
        Delete a session.
        
        Args:
            reference: Session name or ID
            
        Returns:
            True if successful, False otherwise
        """
    # Find session
    if reference.startswith("sid-"):
      session = self.session_repo.find_by_id(SessionId(reference))
    else:
      # Try to find by name
      session = self.session_repo.find_by_name(reference)

    if not session:
      return {"success": False, "error": f"Session not found: {reference}"}

    session_id = session.id

    # Get runtime states for all kernels in the session
    runtime_states = self.runtime_repo.find_by_session_id(session_id)

    # Request shutdown of all kernels
    for state in runtime_states:
      # Set desired state to STOPPED for each kernel
      state.update_desired_status(KernelStatus.STOPPED)
      self.runtime_repo.save(state)

      # Delete runtime state
      self.runtime_repo.delete(state.kernel_id)

    # Delete session
    success = self.session_repo.delete(session_id)

    if success:
      return {"success": True, "error": None}
    else:
      return {"success": False, "error": f"Failed to delete session: {reference}"}

  def create_kernel(self, session_reference: str, kernel_name: str, kernel_type: str = "python3") -> Dict[str, Any]:
    """
        Create a new kernel in a session.
        
        Args:
            session_reference: Session name or ID
            kernel_name: Kernel name
            kernel_type: Type of kernel to create
            
        Returns:
            Kernel metadata
        """
    # Find session
    if session_reference.startswith("sid-"):
      session = self.session_repo.find_by_id(SessionId(session_reference))
    else:
      # Try to find by name
      session = self.session_repo.find_by_name(session_reference)

    if not session:
      return {"success": False, "kernel_id": None, "error": f"Session not found: {session_reference}"}

    # Check if kernel with this name already exists
    existing_kernel = self.kernel_repo.find_by_name(session.id, kernel_name)

    if existing_kernel:
      # Update desired state to RUNNING
      existing_kernel.request_start()
      self.kernel_repo.save(existing_kernel)

      # Check if runtime state exists
      runtime_state = self.runtime_repo.find_by_kernel_id(existing_kernel.id)
      if not runtime_state:
        # Create runtime state
        runtime_state = KernelRuntimeState(
          kernel_id=existing_kernel.id, session_id=session.id, status=KernelStatus.STOPPED, desired_status=KernelStatus.RUNNING)
        self.runtime_repo.save(runtime_state)
      else:
        # Update desired state
        if runtime_state.desired_status != KernelStatus.RUNNING:
          runtime_state.update_desired_status(KernelStatus.RUNNING)
          self.runtime_repo.save(runtime_state)

      return {"success": True, "kernel_id": str(existing_kernel.id), "error": None}

    # Create new kernel
    kernel = self.kernel_factory.create_kernel(session, kernel_name, kernel_type)

    # Save session with the new kernel
    self.session_repo.save(session)
    self.kernel_repo.save(kernel)

    # Create runtime state
    runtime_state = KernelRuntimeState(kernel_id=kernel.id, session_id=session.id, status=KernelStatus.STOPPED, desired_status=KernelStatus.RUNNING)
    self.runtime_repo.save(runtime_state)

    # Publish events
    self.event_bus.publish(KernelCreated(kernel_id=kernel.id, session_id=session.id, kernel_type=kernel_type, name=kernel_name, timestamp=time.time()))

    self.event_bus.publish(
      KernelDesiredStateChanged(
        kernel_id=kernel.id, session_id=session.id, previous_state=KernelStatus.STOPPED, desired_state=KernelStatus.RUNNING, timestamp=time.time()))

    # Poll for events to ensure the kernel operator sees our request
    self.event_bus.poll_events()

    return {"success": True, "kernel_id": str(kernel.id), "error": None}

  def get_kernel(self, reference: str) -> Dict[str, Any]:
    """
        Get a kernel by name or ID.
        
        Args:
            reference: Kernel name or ID
            
        Returns:
            Kernel metadata, or None if not found
        """
    # Parse reference
    parts = reference.split("/", 1)
    if len(parts) == 2:
      # Format: session_ref/kernel_name
      session_ref, kernel_name = parts

      # Find session
      if session_ref.startswith("sid-"):
        session = self.session_repo.find_by_id(SessionId(session_ref))
      else:
        session = self.session_repo.find_by_name(session_ref)

      if not session:
        return {"success": False, "kernel": None, "error": f"Session not found: {session_ref}"}

      # Find kernel by name
      kernel = self.kernel_repo.find_by_name(session.id, kernel_name)
    elif reference.startswith("kid-"):
      # Format: kid-xxxxxxxx
      kernel = self.kernel_repo.find_by_id(KernelId(reference))
    else:
      # Invalid format
      return {"success": False, "kernel": None, "error": f"Invalid kernel reference: {reference}"}

    if not kernel:
      return {"success": False, "kernel": None, "error": f"Kernel not found: {reference}"}

    # Get runtime state
    runtime_state = self.runtime_repo.find_by_kernel_id(kernel.id)

    # Get session name
    session = self.session_repo.find_by_id(kernel.session_id)
    session_name = session.name if session else "Unknown"

    # Convert to dict
    kernel_dict = {
      "id": str(kernel.id),
      "name": kernel.name,
      "session_id": str(kernel.session_id),
      "session_name": session_name,
      "kernel_type": kernel.kernel_type,
      "created_at": kernel.created_at,
      "last_activity": kernel.last_activity,
      "desired_status": kernel.desired_status.value,
    }

    if runtime_state:
      kernel_dict.update(
        {
          "status": runtime_state.status.value,
          "process_id": runtime_state.process_id,
          "connection_file": runtime_state.connection_file,
          "is_alive": runtime_state.status == KernelStatus.RUNNING,
          "is_reconciled": runtime_state.is_reconciled(),
          "health_metrics": runtime_state.health_metrics
        })
    else:
      kernel_dict.update({"status": "unknown", "process_id": None, "connection_file": None, "is_alive": False, "is_reconciled": False})

    return {"success": True, "kernel": kernel_dict, "error": None}

  def list_kernels(self, session_reference: str) -> Dict[str, Any]:
    """
        List all kernels in a session.
        
        Args:
            session_reference: Session name or ID
            
        Returns:
            List of kernel metadata
        """
    # Find session
    if session_reference.startswith("sid-"):
      session = self.session_repo.find_by_id(SessionId(session_reference))
    else:
      # Try to find by name
      session = self.session_repo.find_by_name(session_reference)

    if not session:
      return {"success": False, "kernels": [], "error": f"Session not found: {session_reference}"}

    # Get kernels
    kernels = self.kernel_repo.find_by_session_id(session.id)

    # Convert to dict
    kernel_dicts = []
    for kernel in kernels:
      # Get runtime state
      runtime_state = self.runtime_repo.find_by_kernel_id(kernel.id)

      kernel_dict = {
        "id": str(kernel.id),
        "name": kernel.name,
        "session_id": str(kernel.session_id),
        "kernel_type": kernel.kernel_type,
        "created_at": kernel.created_at,
        "last_activity": kernel.last_activity,
        "desired_status": kernel.desired_status.value,
      }

      if runtime_state:
        kernel_dict.update(
          {
            "status": runtime_state.status.value,
            "process_id": runtime_state.process_id,
            "is_alive": runtime_state.status == KernelStatus.RUNNING,
            "is_reconciled": runtime_state.is_reconciled()
          })
      else:
        kernel_dict.update({"status": "unknown", "process_id": None, "is_alive": False, "is_reconciled": False})

      kernel_dicts.append(kernel_dict)

    return {"success": True, "kernels": kernel_dicts, "error": None}

  def delete_kernel(self, reference: str) -> Dict[str, Any]:
    """
        Delete a kernel.
        
        Args:
            reference: Kernel reference
            
        Returns:
            True if successful, False otherwise
        """
    # Get kernel
    kernel_info = self.get_kernel(reference)
    if not kernel_info["success"]:
      return {"success": False, "error": kernel_info["error"]}

    # Get kernel and session IDs
    kernel_id = KernelId(kernel_info["kernel"]["id"])
    session_id = SessionId(kernel_info["kernel"]["session_id"])

    # Request shutdown of kernel
    kernel = self.kernel_repo.find_by_id(kernel_id)
    if kernel:
      kernel.request_shutdown()
      self.kernel_repo.save(kernel)

    runtime_state = self.runtime_repo.find_by_kernel_id(kernel_id)
    if runtime_state:
      runtime_state.update_desired_status(KernelStatus.STOPPED)
      self.runtime_repo.save(runtime_state)

      # Wait for kernel to stop
      max_attempts = 30
      for _ in range(max_attempts):
        # Poll for events
        self.event_bus.poll_events()

        # Refresh runtime state
        runtime_state = self.runtime_repo.find_by_kernel_id(kernel_id)
        if not runtime_state or runtime_state.status == KernelStatus.STOPPED:
          break

        # Sleep a bit
        time.sleep(0.5)

    # Delete runtime state
    self.runtime_repo.delete(kernel_id)

    # Get session and remove kernel
    session = self.session_repo.find_by_id(session_id)
    if session:
      try:
        session.remove_kernel(kernel_id)
        self.session_repo.save(session)
      except:
        # Ignore exceptions
        pass

    # Delete kernel
    success = self.kernel_repo.delete(kernel_id)

    if success:
      return {"success": True, "error": None}
    else:
      return {"success": False, "error": f"Failed to delete kernel: {reference}"}

  def execute_code(self, reference: str, code: str) -> Dict[str, Any]:
    """
        Execute code in a kernel.
        
        Args:
            reference: Kernel reference
            code: Code to execute
            
        Returns:
            Execution result
        """
    # Get kernel
    kernel_info = self.get_kernel(reference)
    if not kernel_info["success"]:
      return {"success": False, "stdout": "", "error": kernel_info["error"], "outputs": [], "execution_time": 0.0}

    kernel_id = KernelId(kernel_info["kernel"]["id"])
    kernel = self.kernel_repo.find_by_id(kernel_id)
    runtime_state = self.runtime_repo.find_by_kernel_id(kernel_id)

    if not kernel:
      return {"success": False, "stdout": "", "error": f"Kernel not found: {reference}", "outputs": [], "execution_time": 0.0}

    if not runtime_state:
      return {"success": False, "stdout": "", "error": f"Runtime state not found for kernel: {reference}", "outputs": [], "execution_time": 0.0}

    # Ensure kernel is running
    if runtime_state.status != KernelStatus.RUNNING:
      # Request kernel start
      kernel.request_start()
      runtime_state.update_desired_status(KernelStatus.RUNNING)
      self.kernel_repo.save(kernel)
      self.runtime_repo.save(runtime_state)

      # Publish event
      self.event_bus.publish(
        KernelDesiredStateChanged(
          kernel_id=kernel.id, session_id=kernel.session_id, previous_state=runtime_state.status, desired_state=KernelStatus.RUNNING, timestamp=time.time()))

      # Wait for kernel to start
      max_attempts = 30
      for _ in range(max_attempts):
        # Poll for events
        self.event_bus.poll_events()

        # Refresh runtime state
        runtime_state = self.runtime_repo.find_by_kernel_id(kernel_id)
        if runtime_state and runtime_state.status == KernelStatus.RUNNING:
          break

        # Sleep a bit
        time.sleep(0.5)

      # Check if kernel started
      if not runtime_state or runtime_state.status != KernelStatus.RUNNING:
        return {"success": False, "stdout": "", "error": f"Failed to start kernel: {reference}", "outputs": [], "execution_time": 0.0}

    # Execute code using the kernel adapter
    workspace_dir = self.base_dir / "runtime" / "workspaces" / str(kernel_id)
    result = self.kernel_adapter.execute_code(kernel, code, workspace_dir)

    # Update kernel
    self.kernel_repo.save(kernel)

    return {"success": result.success, "stdout": result.stdout, "error": result.error, "outputs": result.outputs, "execution_time": result.execution_time}

  def restart_kernel(self, reference: str) -> Dict[str, Any]:
    """
        Restart a kernel.
        
        Args:
            reference: Kernel reference
            
        Returns:
            True if successful, False otherwise
        """
    # Get kernel
    kernel_info = self.get_kernel(reference)
    if not kernel_info["success"]:
      return {"success": False, "error": kernel_info["error"]}

    kernel_id = KernelId(kernel_info["kernel"]["id"])
    kernel = self.kernel_repo.find_by_id(kernel_id)
    runtime_state = self.runtime_repo.find_by_kernel_id(kernel_id)

    if not kernel:
      return {"success": False, "error": f"Kernel not found: {reference}"}

    if not runtime_state:
      return {"success": False, "error": f"Runtime state not found for kernel: {reference}"}

    # First stop the kernel
    runtime_state.update_desired_status(KernelStatus.STOPPED)
    self.runtime_repo.save(runtime_state)

    # Publish event
    self.event_bus.publish(
      KernelDesiredStateChanged(
        kernel_id=kernel.id, session_id=kernel.session_id, previous_state=runtime_state.status, desired_state=KernelStatus.STOPPED, timestamp=time.time()))

    # Wait for kernel to stop
    max_attempts = 30
    for _ in range(max_attempts):
      # Poll for events
      self.event_bus.poll_events()

      # Refresh runtime state
      runtime_state = self.runtime_repo.find_by_kernel_id(kernel_id)
      if runtime_state and runtime_state.status == KernelStatus.STOPPED:
        break

      # Sleep a bit
      time.sleep(0.5)

    # Now start the kernel
    kernel.request_start()
    runtime_state.update_desired_status(KernelStatus.RUNNING)
    self.kernel_repo.save(kernel)
    self.runtime_repo.save(runtime_state)

    # Publish event
    self.event_bus.publish(
      KernelDesiredStateChanged(
        kernel_id=kernel.id, session_id=kernel.session_id, previous_state=KernelStatus.STOPPED, desired_state=KernelStatus.RUNNING, timestamp=time.time()))

    # Wait for kernel to start
    for _ in range(max_attempts):
      # Poll for events
      self.event_bus.poll_events()

      # Refresh runtime state
      runtime_state = self.runtime_repo.find_by_kernel_id(kernel_id)
      if runtime_state and runtime_state.status == KernelStatus.RUNNING:
        return {"success": True, "error": None}

      # Sleep a bit
      time.sleep(0.5)

    return {"success": False, "error": f"Failed to restart kernel: {reference}"}

  def interrupt_kernel(self, reference: str) -> Dict[str, Any]:
    """
        Interrupt a kernel's execution.
        
        Args:
            reference: Kernel reference
            
        Returns:
            True if successful, False otherwise
        """
    # Get kernel
    kernel_info = self.get_kernel(reference)
    if not kernel_info["success"]:
      return {"success": False, "error": kernel_info["error"]}

    kernel_id = KernelId(kernel_info["kernel"]["id"])
    kernel = self.kernel_repo.find_by_id(kernel_id)
    runtime_state = self.runtime_repo.find_by_kernel_id(kernel_id)

    if not kernel:
      return {"success": False, "error": f"Kernel not found: {reference}"}

    if not runtime_state:
      return {"success": False, "error": f"Runtime state not found for kernel: {reference}"}

    # Check if kernel is running
    if runtime_state.status != KernelStatus.RUNNING:
      return {"success": False, "error": f"Kernel is not running: {reference}"}

    # Execute interrupt using the kernel adapter
    workspace_dir = self.base_dir / "runtime" / "workspaces" / str(kernel_id)
    success = self.kernel_adapter.interrupt_kernel(kernel, workspace_dir)

    if success:
      return {"success": True, "error": None}
    else:
      return {"success": False, "error": f"Failed to interrupt kernel: {reference}"}

  def kernel_status(self, reference: str) -> Dict[str, Any]:
    """
        Get the status of a kernel.
        
        Args:
            reference: Kernel reference
            
        Returns:
            Kernel status information, or None if not found
        """
    return self.get_kernel(reference)

  def shutdown(self):
    """
        Shutdown the interpreter facade.
        
        This stops the kernel operator and releases any resources.
        """
    self.kernel_operator.stop()
