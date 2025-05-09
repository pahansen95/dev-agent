import time
from typing import Optional

from .model import Session, Kernel
from .value_objects import SessionId, KernelId
from .repositories import SessionRepository, KernelRepository
from .events import SessionCreated, KernelCreated
from .exceptions import SessionError, SessionAlreadyExistsError, KernelAlreadyExistsError

class SessionFactory:
    """Factory for creating Session aggregates."""
    
    def __init__(self, session_repo: SessionRepository, event_bus):
        """
        Initialize the factory.
        
        Args:
            session_repo: The session repository
            event_bus: The event bus for publishing events
        """
        self.session_repo = session_repo
        self.event_bus = event_bus
    
    def create_session(self, name: str) -> Session:
        """
        Create a new session with the given name.
        
        Args:
            name: The session name
            
        Returns:
            The created session
            
        Raises:
            SessionAlreadyExistsError: If a session with the given name already exists
        """
        # Check if session with this name already exists
        existing = self.session_repo.find_by_name(name)
        if existing:
            raise SessionAlreadyExistsError(f"Session with name '{name}' already exists")
        
        # Generate session ID
        session_id = SessionId.generate()
        
        # Create session
        session = Session(
            id=session_id,
            name=name,
            created_at=time.time(),
            last_activity=time.time()
        )
        
        # Save to repository
        self.session_repo.save(session)
        
        # Publish event
        self.event_bus.publish(SessionCreated(session_id, name))
        
        return session

class KernelFactory:
    """Factory for creating Kernel entities."""
    
    def __init__(self, kernel_repo: KernelRepository, event_bus):
        """
        Initialize the factory.
        
        Args:
            kernel_repo: The kernel repository
            event_bus: The event bus for publishing events
        """
        self.kernel_repo = kernel_repo
        self.event_bus = event_bus
    
    def create_kernel(self, session: Session, name: str, kernel_type: str = "python3") -> Kernel:
        """
        Create a new kernel in the given session.
        
        Args:
            session: The session to create the kernel in
            name: The kernel name
            kernel_type: The kernel type (default: "python3")
            
        Returns:
            The created kernel
            
        Raises:
            KernelAlreadyExistsError: If a kernel with the given name already exists in the session
        """
        # Check if kernel with this name already exists
        existing = session.get_kernel_by_name(name)
        if existing:
            raise KernelAlreadyExistsError(f"Kernel with name '{name}' already exists in session")
        
        # Generate kernel ID
        kernel_id = KernelId.generate()
        
        # Create kernel
        kernel = Kernel(
            id=kernel_id,
            name=name,
            session_id=session.id,
            kernel_type=kernel_type,
            created_at=time.time(),
            last_activity=time.time()
        )
        
        # Add to session
        session.add_kernel(kernel)
        
        # Save to repository
        self.kernel_repo.save(kernel)
        
        # Publish event
        self.event_bus.publish(KernelCreated(kernel_id, session.id, kernel_type))
        
        return kernel