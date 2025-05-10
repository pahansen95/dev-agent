from pathlib import Path
import time
from typing import Dict, List, Optional, Any
import logging

from ..domain.model import Session, Kernel, KernelRuntimeState
from ..domain.value_objects import SessionId, KernelId, KernelStatus
from ..domain.repositories import SessionRepository, KernelRepository, RuntimeStateRepository
from ..domain.events import (SessionCreated, SessionDeleted, KernelCreated, KernelShutdown, KernelActualStateChanged, KernelDesiredStateChanged)
from .fs_manager import FileSystemManager
from .event_bus import EventBus

logger = logging.getLogger(__name__)

class FileSystemSessionRepository:

  """Implementation of SessionRepository using filesystem storage."""

  def __init__(self, fs_manager: FileSystemManager, event_bus: EventBus):
    """
        Initialize the repository.
        
        Args:
            fs_manager: The file system manager
            event_bus: The event bus for publishing events
        """
    self.fs_manager = fs_manager
    self.event_bus = event_bus
    self._cache: Dict[str, Session] = {}

  def save(self, session: Session) -> None:
    """
        Save a session to the repository.
        
        Args:
            session: The session to save
        """
    # Create session directory if it doesn't exist
    session_path = self.fs_manager.get_session_path(str(session.id))
    if not session_path.exists():
      session_path = self.fs_manager.create_session_directory(str(session.id))

      # Create registry entry and symlink
      self._register_session_name(session.name, str(session.id))
      self.fs_manager.create_symlink(self.fs_manager.base_dir / "by-name" / session.name, session_path)

    # Save session metadata
    metadata = {
      "id": str(session.id),
      "name": session.name,
      "created_at": session.created_at,
      "last_activity": session.last_activity,
      "kernels": [{
        "id": str(k.id),
        "name": k.name
      } for k in session.list_kernels()]
    }

    self.fs_manager.atomic_write_json(session_path / "metadata.json", metadata)

    # Update cache
    self._cache[str(session.id)] = session

  def find_by_id(self, session_id: SessionId) -> Optional[Session]:
    """
        Find a session by ID.
        
        Args:
            session_id: The session ID
            
        Returns:
            The session if found, None otherwise
        """
    # Check cache first
    if str(session_id) in self._cache:
      return self._cache[str(session_id)]

    # Check filesystem
    session_path = self.fs_manager.get_session_path(str(session_id))
    if not session_path.exists():
      return None

    # Load session metadata
    metadata = self.fs_manager.atomic_read_json(session_path / "metadata.json", {})
    if not metadata:
      return None

    # Create session object
    session = Session(
      id=SessionId(metadata["id"]),
      name=metadata["name"],
      created_at=metadata.get("created_at", time.time()),
      last_activity=metadata.get("last_activity", time.time()))

    # Cache and return
    self._cache[str(session_id)] = session
    return session

  def find_by_name(self, name: str) -> Optional[Session]:
    """
        Find a session by name.
        
        Args:
            name: The session name
            
        Returns:
            The session if found, None otherwise
        """
    # Look up session ID from registry
    registry = self._read_session_registry()
    session_id = registry.get(name)
    if not session_id:
      return None

    return self.find_by_id(SessionId(session_id))

  def delete(self, session_id: SessionId) -> bool:
    """
        Delete a session from the repository.
        
        Args:
            session_id: The session ID
            
        Returns:
            True if successful, False otherwise
        """
    # Find session to get name
    session = self.find_by_id(session_id)
    if not session:
      return False

    # Remove from registry
    registry = self._read_session_registry()
    if session.name in registry:
      del registry[session.name]
      self._write_session_registry(registry)

    # Remove symlink
    symlink_path = self.fs_manager.base_dir / "by-name" / session.name
    self.fs_manager.remove_directory(symlink_path)

    # Remove session directory
    session_path = self.fs_manager.get_session_path(str(session_id))
    success = self.fs_manager.remove_directory(session_path)

    # Remove from cache
    if str(session_id) in self._cache:
      del self._cache[str(session_id)]

    # Publish event
    if success:
      self.event_bus.publish(SessionDeleted(session_id, time.time()))

    return success

  def list_all(self) -> List[Session]:
    """
        List all sessions in the repository.
        
        Returns:
            List of all sessions
        """
    sessions = []
    sessions_dir = self.fs_manager.base_dir / "by-id" / "sessions"

    # Scan session directories
    for session_path in sessions_dir.glob("*"):
      metadata_path = session_path / "metadata.json"
      if metadata_path.exists():
        metadata = self.fs_manager.atomic_read_json(metadata_path)

        # Get or create session
        session_id = SessionId(metadata.get("id"))
        if str(session_id) in self._cache:
          sessions.append(self._cache[str(session_id)])
        else:
          session = Session(
            id=session_id,
            name=metadata.get("name", str(session_id)),
            created_at=metadata.get("created_at", time.time()),
            last_activity=metadata.get("last_activity", time.time()))
          self._cache[str(session_id)] = session
          sessions.append(session)

    return sessions

  def _register_session_name(self, name: str, session_id: str) -> None:
    """
        Register a session name to ID mapping.
        
        Args:
            name: The session name
            session_id: The session ID
        """
    registry = self._read_session_registry()
    registry[name] = session_id
    self._write_session_registry(registry)

  def _read_session_registry(self) -> Dict[str, str]:
    """
        Read the session registry.
        
        Returns:
            The session registry
        """
    registry_path = self.fs_manager.base_dir / "registry" / "sessions.json"
    return self.fs_manager.atomic_read_json(registry_path, {})

  def _write_session_registry(self, registry: Dict[str, str]) -> None:
    """
        Write the session registry.
        
        Args:
            registry: The session registry
        """
    registry_path = self.fs_manager.base_dir / "registry" / "sessions.json"
    self.fs_manager.atomic_write_json(registry_path, registry)

class FileSystemKernelRepository:

  """Implementation of KernelRepository using filesystem storage."""

  def __init__(self, fs_manager: FileSystemManager, event_bus: EventBus):
    """
        Initialize the repository.
        
        Args:
            fs_manager: The file system manager
            event_bus: The event bus for publishing events
        """
    self.fs_manager = fs_manager
    self.event_bus = event_bus
    self._cache: Dict[str, Kernel] = {}

  def save(self, kernel: Kernel) -> None:
    """
        Save a kernel to the repository.
        
        Args:
            kernel: The kernel to save
        """
    # Get session path
    session_path = self.fs_manager.get_session_path(str(kernel.session_id))
    if not session_path.exists():
      raise ValueError(f"Session {kernel.session_id} does not exist")

    # Create kernel directory if it doesn't exist
    kernel_path = self.fs_manager.get_kernel_path(session_path, str(kernel.id))
    if not kernel_path.exists():
      kernel_path = self.fs_manager.create_kernel_directory(session_path, str(kernel.id))

      # Create symlink in session's by-name directory
      session_by_name_path = self.fs_manager.base_dir / "by-name"
      session_registry = self._read_session_registry()
      for name, session_id in session_registry.items():
        if session_id == str(kernel.session_id):
          # Create symlink from by-name/session_name/kernel_name to kernel directory
          self.fs_manager.create_symlink(session_by_name_path / name / kernel.name, kernel_path)
          break

    # Save kernel metadata
    metadata = {
      "id": str(kernel.id),
      "name": kernel.name,
      "session_id": str(kernel.session_id),
      "kernel_type": kernel.kernel_type,
      "created_at": kernel.created_at,
      "last_activity": kernel.last_activity,
      "desired_status": kernel.desired_status.value,
      "is_alive": kernel.is_alive
    }

    self.fs_manager.atomic_write_json(kernel_path / "metadata.json", metadata)

    # Update cache
    self._cache[str(kernel.id)] = kernel

  def find_by_id(self, kernel_id: KernelId) -> Optional[Kernel]:
    """
        Find a kernel by ID.
        
        Args:
            kernel_id: The kernel ID
            
        Returns:
            The kernel if found, None otherwise
        """
    # Check cache first
    if str(kernel_id) in self._cache:
      return self._cache[str(kernel_id)]

    # Find session containing this kernel
    sessions_dir = self.fs_manager.base_dir / "by-id" / "sessions"
    for session_path in sessions_dir.glob("*"):
      kernel_path = session_path / "kernels" / str(kernel_id)
      if kernel_path.exists():
        return self._load_kernel_from_path(kernel_path)

    return None

  def find_by_session_id(self, session_id: SessionId) -> List[Kernel]:
    """
        Find all kernels for a session.
        
        Args:
            session_id: The session ID
            
        Returns:
            List of kernels
        """
    kernels = []
    session_path = self.fs_manager.get_session_path(str(session_id))
    if not session_path.exists():
      return []

    kernels_dir = session_path / "kernels"
    for kernel_path in kernels_dir.glob("*"):
      if kernel_path.is_dir():
        kernel = self._load_kernel_from_path(kernel_path)
        if kernel:
          kernels.append(kernel)

    return kernels

  def find_by_name(self, session_id: SessionId, name: str) -> Optional[Kernel]:
    """
        Find a kernel by name within a session.
        
        Args:
            session_id: The session ID
            name: The kernel name
            
        Returns:
            The kernel if found, None otherwise
        """
    # Find all kernels in the session
    kernels = self.find_by_session_id(session_id)

    # Find the kernel with the given name
    for kernel in kernels:
      if kernel.name == name:
        return kernel

    return None

  def delete(self, kernel_id: KernelId) -> bool:
    """
        Delete a kernel from the repository.
        
        Args:
            kernel_id: The kernel ID
            
        Returns:
            True if successful, False otherwise
        """
    # Find the kernel to get session ID and name
    kernel = self.find_by_id(kernel_id)
    if not kernel:
      return False

    # Remove kernel directory
    session_path = self.fs_manager.get_session_path(str(kernel.session_id))
    kernel_path = self.fs_manager.get_kernel_path(session_path, str(kernel_id))

    # Remove symlinks
    session_registry = self._read_session_registry()
    for name, session_id in session_registry.items():
      if session_id == str(kernel.session_id):
        symlink_path = self.fs_manager.base_dir / "by-name" / name / kernel.name
        if symlink_path.exists() or symlink_path.is_symlink():
          try:
            symlink_path.unlink()
          except Exception as e:
            logger.error(f"Error removing symlink {symlink_path}: {e}")

    # Remove kernel directory
    success = self.fs_manager.remove_directory(kernel_path)

    # Remove from cache
    if str(kernel_id) in self._cache:
      del self._cache[str(kernel_id)]

    # Publish event
    if success:
      self.event_bus.publish(KernelShutdown(kernel_id, time.time()))

    return success

  def _load_kernel_from_path(self, kernel_path: Path) -> Optional[Kernel]:
    """
        Load a kernel from the filesystem.
        
        Args:
            kernel_path: The path to the kernel directory
            
        Returns:
            The kernel if loaded successfully, None otherwise
        """
    metadata_path = kernel_path / "metadata.json"
    if not metadata_path.exists():
      return None

    metadata = self.fs_manager.atomic_read_json(metadata_path, {})
    if not metadata:
      return None

    kernel_id = KernelId(metadata["id"])

    # Check if we have it in cache
    if str(kernel_id) in self._cache:
      return self._cache[str(kernel_id)]

    # Create kernel object
    kernel = Kernel(
      id=kernel_id,
      name=metadata["name"],
      session_id=SessionId(metadata["session_id"]),
      kernel_type=metadata["kernel_type"],
      created_at=metadata.get("created_at", time.time()),
      last_activity=metadata.get("last_activity", time.time()),
      desired_status=KernelStatus(metadata.get("desired_status", "running")),
      _is_alive=metadata.get("is_alive", False))

    # Add to cache
    self._cache[str(kernel_id)] = kernel
    return kernel

  def _read_session_registry(self) -> Dict[str, str]:
    """
        Read the session registry.
        
        Returns:
            The session registry
        """
    registry_path = self.fs_manager.base_dir / "registry" / "sessions.json"
    return self.fs_manager.atomic_read_json(registry_path, {})

class FileSystemRuntimeStateRepository(RuntimeStateRepository):

  """Implementation of RuntimeStateRepository using filesystem storage."""

  def __init__(self, fs_manager: FileSystemManager, event_bus: EventBus):
    """
        Initialize the repository.
        
        Args:
            fs_manager: The file system manager
            event_bus: The event bus for publishing events
        """
    self.fs_manager = fs_manager
    self.event_bus = event_bus
    self.runtime_states_dir = fs_manager.base_dir / "runtime" / "kernels"
    self.runtime_states_dir.mkdir(parents=True, exist_ok=True)
    self._pid_cache: Dict[int, str] = {} # Maps PIDs to kernel IDs
    self._cache: Dict[str, KernelRuntimeState] = {}

  def save(self, runtime_state: KernelRuntimeState) -> None:
    """
        Save runtime state to the repository.
        
        Args:
            runtime_state: The runtime state to save
        """
    # Get previous state if it exists
    previous_state = None
    if str(runtime_state.kernel_id) in self._cache:
      previous_state = self._cache[str(runtime_state.kernel_id)]

    # Detect state changes
    state_changed = previous_state is None or previous_state.status != runtime_state.status
    desired_state_changed = previous_state is None or previous_state.desired_status != runtime_state.desired_status

    # Serialize state
    kernel_id_str = str(runtime_state.kernel_id)
    state_data = {
      "kernel_id": kernel_id_str,
      "session_id": str(runtime_state.session_id),
      "status": runtime_state.status.value,
      "desired_status": runtime_state.desired_status.value,
      "process_id": runtime_state.process_id,
      "connection_file": runtime_state.connection_file,
      "jupyter_kernel_id": runtime_state.jupyter_kernel_id,
      "health_metrics": runtime_state.health_metrics,
      "last_health_check": runtime_state.last_health_check,
      "last_reconciliation": runtime_state.last_reconciliation
    }

    # Write state file
    state_path = self.runtime_states_dir / f"{kernel_id_str}.json"
    self.fs_manager.atomic_write_json(state_path, state_data)

    # Update cache
    self._cache[kernel_id_str] = runtime_state

    # Update PID cache if process ID is set
    if runtime_state.process_id is not None:
      self._pid_cache[runtime_state.process_id] = kernel_id_str

    # Publish events if state changed
    if state_changed:
      previous_status = previous_state.status if previous_state else KernelStatus.STOPPED
      self.event_bus.publish(
        KernelActualStateChanged(
          kernel_id=runtime_state.kernel_id,
          session_id=runtime_state.session_id,
          previous_state=previous_status,
          actual_state=runtime_state.status,
          process_id=runtime_state.process_id,
          connection_file=runtime_state.connection_file,
          health_metrics=runtime_state.health_metrics,
          timestamp=time.time()))

    if desired_state_changed:
      previous_desired_status = previous_state.desired_status if previous_state else KernelStatus.STOPPED
      self.event_bus.publish(
        KernelDesiredStateChanged(
          kernel_id=runtime_state.kernel_id,
          session_id=runtime_state.session_id,
          previous_state=previous_desired_status,
          desired_state=runtime_state.desired_status,
          timestamp=time.time()))

  def find_by_kernel_id(self, kernel_id: KernelId) -> Optional[KernelRuntimeState]:
    """
        Find runtime state by kernel ID.
        
        Args:
            kernel_id: The kernel ID
            
        Returns:
            The runtime state if found, None otherwise
        """
    # Check cache first
    if str(kernel_id) in self._cache:
      return self._cache[str(kernel_id)]

    # Check filesystem
    state_path = self.runtime_states_dir / f"{str(kernel_id)}.json"
    if not state_path.exists():
      return None

    # Load state
    state_data = self.fs_manager.atomic_read_json(state_path, {})
    if not state_data:
      return None

    # Create runtime state object
    runtime_state = self._deserialize_runtime_state(state_data)

    # Add to cache
    if runtime_state:
      self._cache[str(kernel_id)] = runtime_state
      if runtime_state.process_id is not None:
        self._pid_cache[runtime_state.process_id] = str(kernel_id)

    return runtime_state

  def find_by_process_id(self, process_id: int) -> Optional[KernelRuntimeState]:
    """
        Find runtime state by process ID.
        
        Args:
            process_id: The process ID
            
        Returns:
            The runtime state if found, None otherwise
        """
    # Check PID cache first
    if process_id in self._pid_cache:
      kernel_id_str = self._pid_cache[process_id]
      if kernel_id_str in self._cache:
        return self._cache[kernel_id_str]

    # Search all runtime states
    for state_path in self.runtime_states_dir.glob("*.json"):
      state_data = self.fs_manager.atomic_read_json(state_path, {})
      if state_data.get("process_id") == process_id:
        runtime_state = self._deserialize_runtime_state(state_data)
        if runtime_state:
          kernel_id_str = str(runtime_state.kernel_id)
          self._cache[kernel_id_str] = runtime_state
          self._pid_cache[process_id] = kernel_id_str
          return runtime_state

    return None

  def find_by_session_id(self, session_id: SessionId) -> List[KernelRuntimeState]:
    """
        Find runtime states for all kernels in a session.
        
        Args:
            session_id: The session ID
            
        Returns:
            List of runtime states
        """
    session_id_str = str(session_id)
    runtime_states = []

    # Search all runtime states
    for state_path in self.runtime_states_dir.glob("*.json"):
      state_data = self.fs_manager.atomic_read_json(state_path, {})
      if state_data.get("session_id") == session_id_str:
        runtime_state = self._deserialize_runtime_state(state_data)
        if runtime_state:
          kernel_id_str = str(runtime_state.kernel_id)
          self._cache[kernel_id_str] = runtime_state
          if runtime_state.process_id is not None:
            self._pid_cache[runtime_state.process_id] = kernel_id_str
          runtime_states.append(runtime_state)

    return runtime_states

  def delete(self, kernel_id: KernelId) -> bool:
    """
        Delete runtime state from the repository.
        
        Args:
            kernel_id: The kernel ID
            
        Returns:
            True if successful, False otherwise
        """
    kernel_id_str = str(kernel_id)

    # Remove from PID cache if present
    if kernel_id_str in self._cache and self._cache[kernel_id_str].process_id is not None:
      process_id = self._cache[kernel_id_str].process_id
      if process_id in self._pid_cache:
        del self._pid_cache[process_id]

    # Remove from cache
    if kernel_id_str in self._cache:
      del self._cache[kernel_id_str]

    # Remove state file
    state_path = self.runtime_states_dir / f"{kernel_id_str}.json"
    if state_path.exists():
      try:
        state_path.unlink()
        return True
      except Exception as e:
        logger.error(f"Error deleting runtime state file {state_path}: {e}")
        return False

    return True # No file to delete, still successful

  def list_all(self) -> List[KernelRuntimeState]:
    """
        List all runtime states in the repository.
        
        Returns:
            List of all runtime states
        """
    runtime_states = []

    # Search all runtime states
    for state_path in self.runtime_states_dir.glob("*.json"):
      state_data = self.fs_manager.atomic_read_json(state_path, {})
      runtime_state = self._deserialize_runtime_state(state_data)
      if runtime_state:
        kernel_id_str = str(runtime_state.kernel_id)
        self._cache[kernel_id_str] = runtime_state
        if runtime_state.process_id is not None:
          self._pid_cache[runtime_state.process_id] = kernel_id_str
        runtime_states.append(runtime_state)

    return runtime_states

  def list_active(self) -> List[KernelRuntimeState]:
    """
        List all active runtime states (running or starting kernels).
        
        Returns:
            List of active runtime states
        """
    # Get all runtime states first
    all_states = self.list_all()

    # Filter active states
    active_states = [state for state in all_states if state.status in {KernelStatus.RUNNING, KernelStatus.STARTING}]

    return active_states

  def _deserialize_runtime_state(self, data: Dict[str, Any]) -> Optional[KernelRuntimeState]:
    """
        Deserialize runtime state from data.
        
        Args:
            data: The serialized data
            
        Returns:
            The deserialized runtime state, or None if invalid
        """
    try:
      return KernelRuntimeState(
        kernel_id=KernelId(data["kernel_id"]),
        session_id=SessionId(data["session_id"]),
        status=KernelStatus(data["status"]),
        desired_status=KernelStatus(data["desired_status"]),
        process_id=data.get("process_id"),
        connection_file=data.get("connection_file"),
        jupyter_kernel_id=data.get("jupyter_kernel_id"),
        health_metrics=data.get("health_metrics", {}),
        last_health_check=data.get("last_health_check", time.time()),
        last_reconciliation=data.get("last_reconciliation", time.time()))
    except Exception as e:
      logger.error(f"Error deserializing runtime state: {e}")
      return None
