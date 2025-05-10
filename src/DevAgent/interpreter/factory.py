"""
Utility factory for creating the interpreter facade with all dependencies.
"""

import pathlib
import uuid
from typing import Optional

from .application.facade import InterpreterFacade
from .application.event_driven_facade import EventDrivenInterpreterFacade
from .application.app_service import InterpreterApplicationService
from .infrastructure.event_bus import EventBus
from .infrastructure.fs_event_bus import FileSystemEventBus
from .infrastructure.fs_manager import FileSystemManager
from .infrastructure.repositories import (
    FileSystemSessionRepository, 
    FileSystemKernelRepository,
    FileSystemRuntimeStateRepository
)
from .infrastructure.kernel_adapter import KernelControllerAdapter
from .infrastructure.kernel_operator import KernelOperator
from .domain.services import ReferenceResolutionService, KernelLifecycleService, ExecutionService
from .domain.factories import SessionFactory, KernelFactory

def create_interpreter(base_dir: pathlib.Path) -> InterpreterFacade:
  """
    Create an interpreter facade with all dependencies configured.
    
    Args:
        base_dir: The base directory for interpreter files
    
    Returns:
        An InterpreterFacade instance
    """
  # Create infrastructure components
  fs_manager = FileSystemManager(base_dir)
  fs_manager.ensure_directory_structure()

  event_bus = EventBus()

  # Create repositories
  session_repo = FileSystemSessionRepository(fs_manager, event_bus)
  kernel_repo = FileSystemKernelRepository(fs_manager, event_bus)

  # Create domain services
  reference_service = ReferenceResolutionService(session_repo, kernel_repo)

  # Create factories
  session_factory = SessionFactory(session_repo, event_bus)
  kernel_factory = KernelFactory(kernel_repo, event_bus)

  # Create kernel adapter
  kernel_adapter = KernelControllerAdapter()

  # Create execution and lifecycle services
  kernel_lifecycle_service = KernelLifecycleService(kernel_repo, kernel_adapter, event_bus, fs_manager)
  execution_service = ExecutionService(kernel_repo, kernel_adapter, event_bus, fs_manager)

  # Create application service
  app_service = InterpreterApplicationService(
    session_repo=session_repo,
    kernel_repo=kernel_repo,
    session_factory=session_factory,
    kernel_factory=kernel_factory,
    reference_service=reference_service,
    execution_service=execution_service,
    kernel_lifecycle_service=kernel_lifecycle_service,
    fs_manager=fs_manager)

  # Create and return facade
  return InterpreterFacade(app_service)

def create_event_driven_interpreter(
    base_dir: pathlib.Path, 
    consumer_id: Optional[str] = None
) -> EventDrivenInterpreterFacade:
  """
  Create an event-driven interpreter facade with all dependencies configured.
  
  This implementation uses filesystem-based event bus and persistent kernel processes.
  
  Args:
      base_dir: The base directory for interpreter files
      consumer_id: Optional consumer ID for event bus
  
  Returns:
      An EventDrivenInterpreterFacade instance
  """
  # Generate consumer ID if not provided
  if not consumer_id:
    consumer_id = f"cli-{uuid.uuid4().hex[:8]}"
  
  # Create and return the event-driven facade
  return EventDrivenInterpreterFacade(base_dir, consumer_id)