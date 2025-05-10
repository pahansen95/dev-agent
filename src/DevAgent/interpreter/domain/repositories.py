from typing import List, Optional, Protocol
from .model import Session, Kernel, KernelRuntimeState
from .value_objects import SessionId, KernelId

class SessionRepository(Protocol):

  """Repository interface for Session aggregate."""

  def save(self, session: Session) -> None:
    """Save a session to the repository."""
    ...

  def find_by_id(self, session_id: SessionId) -> Optional[Session]:
    """Find a session by ID."""
    ...

  def find_by_name(self, name: str) -> Optional[Session]:
    """Find a session by name."""
    ...

  def delete(self, session_id: SessionId) -> bool:
    """Delete a session from the repository."""
    ...

  def list_all(self) -> List[Session]:
    """List all sessions in the repository."""
    ...

class KernelRepository(Protocol):

  """Repository interface for Kernel entity."""

  def save(self, kernel: Kernel) -> None:
    """Save a kernel to the repository."""
    ...

  def find_by_id(self, kernel_id: KernelId) -> Optional[Kernel]:
    """Find a kernel by ID."""
    ...

  def find_by_session_id(self, session_id: SessionId) -> List[Kernel]:
    """Find all kernels for a session."""
    ...

  def find_by_name(self, session_id: SessionId, name: str) -> Optional[Kernel]:
    """Find a kernel by name within a session."""
    ...

  def delete(self, kernel_id: KernelId) -> bool:
    """Delete a kernel from the repository."""
    ...

class RuntimeStateRepository(Protocol):

  """Repository interface for kernel runtime state."""

  def save(self, runtime_state: KernelRuntimeState) -> None:
    """Save runtime state to the repository."""
    ...

  def find_by_kernel_id(self, kernel_id: KernelId) -> Optional[KernelRuntimeState]:
    """Find runtime state by kernel ID."""
    ...

  def find_by_process_id(self, process_id: int) -> Optional[KernelRuntimeState]:
    """Find runtime state by process ID."""
    ...

  def find_by_session_id(self, session_id: SessionId) -> List[KernelRuntimeState]:
    """Find runtime states for all kernels in a session."""
    ...

  def delete(self, kernel_id: KernelId) -> bool:
    """Delete runtime state from the repository."""
    ...

  def list_all(self) -> List[KernelRuntimeState]:
    """List all runtime states in the repository."""
    ...

  def list_active(self) -> List[KernelRuntimeState]:
    """List all active runtime states (running kernels)."""
    ...
