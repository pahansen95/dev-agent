from typing import List, Optional, Protocol
from .model import Session, Kernel
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