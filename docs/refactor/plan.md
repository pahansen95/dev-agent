# DevAgent Interpreter - DDD Refactoring Project Plan

## 1. Basis for Refactor

### What & Why

The DevAgent Interpreter currently implements a modular architecture that successfully provides a computational bridge between agent intelligence and project reality. However, as the system grows in complexity, several challenges have emerged:

1. **Implicit Domain Concepts**: Core domain concepts like Sessions and Kernels exist but are not explicitly modeled with appropriate behaviors.
2. **Scattered Business Logic**: Domain rules are distributed across multiple modules rather than centralized within domain objects.
3. **Technical vs. Semantic Boundaries**: The system is organized by technical concerns rather than semantic boundaries.
4. **Limited Testability**: Direct coupling to infrastructure makes testing more complex than necessary.
5. **Inconsistent Error Handling**: Mixture of approaches for handling errors (sometimes returning None, sometimes exceptions).

Domain-Driven Design (DDD) offers a solution to these challenges by providing:

- Rich domain models with encapsulated behavior
- Clear bounded contexts with explicit boundaries
- Separation of domain logic from infrastructure concerns
- Event-driven communication between contexts
- Consistent patterns for handling domain operations

### Architectural References

This refactoring plan is informed by the following project documents:

1. **[docs/HierarchicalDomainDesign.md](docs/HierarchicalDomainDesign.md)**: Outlines the formal framework for systematically translating semantic intent into computational systems.
2. **[docs/AgentInterpreterArchitecture.md](docs/AgentInterpreterArchitecture.md)**: Describes the detailed design of the DevAgent Interpreter as a foundational computational bridge.
3. **[docs/AgenticDeveloperArchitecture.md](docs/AgenticDeveloperArchitecture.md)**: Provides the broader context of the Agentic Developer architecture.

## 2. Comprehensive DDD Architecture

The proposed Domain-Driven Design architecture reorganizes the DevAgent Interpreter around core domain concepts and explicit bounded contexts, while maintaining its core purpose as a computational bridge enabling development agents to interact with software projects.

### Ubiquitous Language

To establish a shared language for the domain, we define:

- **Session**: A persistent computational environment containing multiple kernels
- **Kernel**: An executable process that interprets and runs code
- **Workspace**: A directory where a kernel operates, aligned with project structure
- **Reference**: An identifier (by name or ID) pointing to a computational resource
- **Execution**: The process of running code in a kernel and capturing results

### Bounded Contexts

The system is divided into four primary bounded contexts:

#### 1. Session Management Context
Responsible for managing the lifecycle of computational sessions.

#### 2. Kernel Execution Context
Responsible for kernel process management and code execution.

#### 3. Reference Resolution Context
Responsible for translating various reference forms to concrete resources.

#### 4. Persistence Context
Responsible for durable storage and recovery of system state.

### Domain Model

#### Value Objects

```
SessionId:
  - Value (string)
  - Generate() -> SessionId

KernelId:
  - Value (string)
  - Generate() -> KernelId

Reference:
  - Type (enum: SESSION, KERNEL)
  - NameComponent (string, optional)
  - IdComponent (string, optional)
  - Path (string, optional)
  - Resolve() -> ResolvedReference

ExecutionResult:
  - Success (boolean)
  - Stdout (string)
  - Error (string, optional)
  - Outputs (list)
  - ExecutionTime (float)
```

#### Entities and Aggregates

```
Session (Aggregate Root):
  - Id (SessionId)
  - Name (string)
  - CreatedAt (timestamp)
  - LastActivity (timestamp)
  - Kernels (collection of Kernel)
  - AddKernel(Kernel)
  - GetKernel(KernelId) -> Kernel
  - ListKernels() -> List<Kernel>
  - UpdateLastActivity()

Kernel (Entity):
  - Id (KernelId)
  - Name (string)
  - Type (string)
  - Status (enum: ALIVE, DEAD)
  - WorkspacePath (string)
  - Start() -> boolean
  - Execute(code) -> ExecutionResult
  - Interrupt() -> boolean
  - Restart() -> boolean
  - Shutdown() -> boolean
```

#### Domain Events

```
SessionCreated:
  - SessionId
  - Name
  - Timestamp

KernelCreated:
  - KernelId
  - SessionId
  - KernelType
  - Timestamp

KernelStarted:
  - KernelId
  - Timestamp

KernelShutdown:
  - KernelId
  - Timestamp

CodeExecuted:
  - KernelId
  - Success
  - ExecutionTime
  - Timestamp

SessionDeleted:
  - SessionId
  - Timestamp
```

### Domain Services

Key domain services include:

```
ReferenceResolutionService:
  - ResolveReference(string) -> Reference

SessionFactory:
  - CreateSession(name) -> Session

KernelFactory:
  - CreateKernel(sessionId, name, type) -> Kernel

ExecutionService:
  - ExecuteCode(kernelId, code) -> ExecutionResult
```

### Repository Interfaces

```
SessionRepository:
  - Save(Session)
  - FindById(SessionId) -> Session
  - FindByName(string) -> Session
  - Delete(SessionId) -> boolean
  - ListAll() -> List<Session>

KernelRepository:
  - Save(Kernel)
  - FindById(KernelId) -> Kernel
  - FindBySessionId(SessionId) -> List<Kernel>
  - FindByName(SessionId, string) -> Kernel
  - Delete(KernelId) -> boolean
```

### Application Services

```
InterpreterApplicationService:
  - CreateSession(name) -> SessionId
  - GetSession(reference) -> Session
  - ListSessions() -> List<SessionDTO>
  - DeleteSession(reference) -> boolean
  - CreateKernel(sessionRef, kernelName, kernelType) -> KernelId
  - GetKernel(reference) -> Kernel
  - ListKernels(sessionRef) -> List<KernelDTO>
  - DeleteKernel(reference) -> boolean
  - ExecuteCode(reference, code) -> ExecutionResult
```

### Infrastructure Services

```
FileSystemManager:
  - EnsureDirectoryStructure()
  - CreateSessionDirectory(SessionId) -> Path
  - CreateKernelDirectory(SessionId, KernelId) -> Path
  - AtomicWriteJson(Path, object)
  - AtomicReadJson(Path) -> object
  - CreateSymlink(source, target)
  - RemoveDirectory(Path)

EventBus:
  - Publish(DomainEvent)
  - Subscribe<T extends DomainEvent>(handler)
  - Unsubscribe<T extends DomainEvent>(handler)
```

## 3. Gap Analysis: Current vs. Future State

### Conceptual Gaps

| Aspect | Current Architecture | DDD Future State | Gap |
|--------|---------------------|------------------|-----|
| **Domain Model** | Anemic model focused on data | Rich domain model with behavior | Need to extract and encapsulate domain behavior |
| **Boundaries** | Module-based (technical) | Context-based (semantic) | Need to reorganize code around domain contexts |
| **Invariants** | Spread across modules | Enforced within aggregates | Need to centralize invariant enforcement |
| **Communication** | Direct method calls | Event-driven + method calls | Need to implement domain event system |
| **Error Handling** | Inconsistent patterns | Consistent domain exceptions | Need to standardize error handling |

### Structural Gaps

| Component | Current Implementation | DDD Implementation | Gap |
|-----------|------------------------|-------------------|-----|
| **Session** | Data container with minimal behavior | Aggregate root with encapsulated behavior | Need to transform into proper aggregate |
| **Kernel** | Controller-centric implementation | Entity with domain behavior | Need to separate domain logic from infrastructure |
| **Registry** | Mixed concerns: name resolution, lifecycle | Clear separation of concerns | Need to extract distinct services |
| **Persistence** | Direct filesystem operations | Repository pattern | Need to abstract persistence behind repositories |
| **API** | Mixes domain and application logic | Clean separation of concerns | Need to create application services layer |

### Implementation Gaps

| Feature | Current State | Target State | Gap |
|---------|--------------|--------------|-----|
| **Domain Events** | Non-existent | Comprehensive event system | Implement event bus and domain events |
| **Value Objects** | Primitive types | Encapsulated value objects | Create value objects for domain concepts |
| **Error Model** | Mixed patterns | Domain-specific exceptions | Define exception hierarchy |
| **Testing** | Limited domain-focused tests | Comprehensive domain testing | Add domain-focused test suite |
| **Configuration** | Scattered | Centralized configuration | Implement configuration management |

## 4. Milestones and Tasks

### Milestone 1: Domain Model Foundation (2 weeks)
Focus on establishing the core domain model components without changing the existing system.

#### Task 1.1: Define Value Objects (3 days)
Create immutable value objects to represent core domain concepts.

**Implementation Details:**
```python
# src/DevAgent/interpreter/domain/value_objects.py
from dataclasses import dataclass
import uuid
from typing import Optional, Literal, Union
from pathlib import Path

@dataclass(frozen=True)
class SessionId:
    """Value object representing a unique session identifier."""
    value: str
    
    @classmethod
    def generate(cls) -> 'SessionId':
        """Generate a new unique session ID."""
        return cls(f"sid-{uuid.uuid4().hex[:8]}")
    
    def __str__(self) -> str:
        return self.value

@dataclass(frozen=True)
class KernelId:
    """Value object representing a unique kernel identifier."""
    value: str
    
    @classmethod
    def generate(cls) -> 'KernelId':
        """Generate a new unique kernel ID."""
        return cls(f"kid-{uuid.uuid4().hex[:8]}")
    
    def __str__(self) -> str:
        return self.value

@dataclass(frozen=True)
class Reference:
    """Value object representing a reference to a computational resource."""
    type: Literal["session", "kernel"]
    name_component: Optional[str] = None
    id_component: Optional[str] = None
    path: Optional[Path] = None
    
    @classmethod
    def parse(cls, reference_string: str) -> 'Reference':
        """Parse a reference string into a Reference object."""
        # Implementation details...
        pass

@dataclass(frozen=True)
class ExecutionResult:
    """Value object representing the result of code execution."""
    success: bool
    stdout: str = ""
    error: Optional[str] = None
    outputs: list = field(default_factory=list)
    execution_time: float = 0.0
```

#### Task 1.2: Define Domain Exceptions (2 days)
Create a hierarchy of domain-specific exceptions.

**Implementation Details:**
```python
# src/DevAgent/interpreter/domain/exceptions.py
class DomainError(Exception):
    """Base class for all domain-related exceptions."""
    pass

class SessionError(DomainError):
    """Base class for session-related errors."""
    pass

class KernelError(DomainError):
    """Base class for kernel-related errors."""
    pass

class SessionNotFoundError(SessionError):
    """Raised when a session cannot be found."""
    pass

class KernelNotFoundError(KernelError):
    """Raised when a kernel cannot be found."""
    pass

class ReferenceResolutionError(DomainError):
    """Raised when a reference cannot be resolved."""
    pass

class KernelExecutionError(KernelError):
    """Raised when code execution in a kernel fails."""
    pass
```

#### Task 1.3: Define Domain Events (2 days)
Create domain event classes to represent significant state changes.

**Implementation Details:**
```python
# src/DevAgent/interpreter/domain/events.py
from dataclasses import dataclass
import time
from typing import Protocol
from .value_objects import SessionId, KernelId

class DomainEvent(Protocol):
    """Interface for all domain events."""
    timestamp: float

@dataclass(frozen=True)
class SessionCreated:
    """Event raised when a new session is created."""
    session_id: SessionId
    name: str
    timestamp: float = field(default_factory=time.time)

@dataclass(frozen=True)
class KernelCreated:
    """Event raised when a new kernel is created."""
    kernel_id: KernelId
    session_id: SessionId
    kernel_type: str
    timestamp: float = field(default_factory=time.time)

@dataclass(frozen=True)
class KernelStarted:
    """Event raised when a kernel is started."""
    kernel_id: KernelId
    timestamp: float = field(default_factory=time.time)

@dataclass(frozen=True)
class CodeExecuted:
    """Event raised when code is executed in a kernel."""
    kernel_id: KernelId
    success: bool
    execution_time: float
    timestamp: float = field(default_factory=time.time)

@dataclass(frozen=True)
class SessionDeleted:
    """Event raised when a session is deleted."""
    session_id: SessionId
    timestamp: float = field(default_factory=time.time)

@dataclass(frozen=True)
class KernelShutdown:
    """Event raised when a kernel is shut down."""
    kernel_id: KernelId
    timestamp: float = field(default_factory=time.time)
```

#### Task 1.4: Define Entity and Aggregate Classes (5 days)
Create the core domain entities and aggregates with behavior.

**Implementation Details:**
```python
# src/DevAgent/interpreter/domain/model.py
from dataclasses import dataclass, field
import time
from typing import Dict, List, Optional, Set
from .value_objects import SessionId, KernelId, ExecutionResult
from .exceptions import KernelNotFoundError

@dataclass
class Kernel:
    """Entity representing a computational kernel."""
    id: KernelId
    name: str
    session_id: SessionId
    kernel_type: str
    created_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)
    _is_alive: bool = False
    
    def start(self) -> bool:
        """Start the kernel process."""
        # To be implemented by infrastructure
        pass
    
    def execute(self, code: str) -> ExecutionResult:
        """Execute code in this kernel."""
        # To be implemented by infrastructure
        pass
    
    def interrupt(self) -> bool:
        """Interrupt the kernel's execution."""
        # To be implemented by infrastructure
        pass
    
    def restart(self) -> bool:
        """Restart the kernel process."""
        # To be implemented by infrastructure
        pass
    
    def shutdown(self) -> bool:
        """Shutdown the kernel process."""
        # To be implemented by infrastructure
        pass
    
    @property
    def is_alive(self) -> bool:
        """Check if the kernel is alive."""
        return self._is_alive
    
    def update_last_activity(self) -> None:
        """Update the last activity timestamp."""
        self.last_activity = time.time()

@dataclass
class Session:
    """Aggregate root representing a computational session."""
    id: SessionId
    name: str
    created_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)
    _kernels: Dict[str, Kernel] = field(default_factory=dict)
    
    def add_kernel(self, kernel: Kernel) -> None:
        """Add a kernel to this session."""
        if str(kernel.id) in self._kernels:
            raise ValueError(f"Kernel with ID {kernel.id} already exists in session")
        self._kernels[str(kernel.id)] = kernel
        self.update_last_activity()
    
    def get_kernel(self, kernel_id: KernelId) -> Kernel:
        """Get a kernel by ID."""
        kernel = self._kernels.get(str(kernel_id))
        if not kernel:
            raise KernelNotFoundError(f"Kernel {kernel_id} not found in session {self.id}")
        return kernel
    
    def get_kernel_by_name(self, name: str) -> Optional[Kernel]:
        """Get a kernel by name."""
        for kernel in self._kernels.values():
            if kernel.name == name:
                return kernel
        return None
    
    def list_kernels(self) -> List[Kernel]:
        """List all kernels in this session."""
        return list(self._kernels.values())
    
    def remove_kernel(self, kernel_id: KernelId) -> None:
        """Remove a kernel from this session."""
        if str(kernel_id) in self._kernels:
            del self._kernels[str(kernel_id)]
            self.update_last_activity()
    
    def update_last_activity(self) -> None:
        """Update the last activity timestamp."""
        self.last_activity = time.time()
```

### Milestone 2: Infrastructure Layer (3 weeks)
Implement infrastructure services that will support the domain model.

#### Task 2.1: Implement Event Bus (4 days)
Create an event bus to handle domain events.

**Implementation Details:**
```python
# src/DevAgent/interpreter/infrastructure/event_bus.py
from collections import defaultdict
from typing import Callable, Dict, List, Type, TypeVar
import logging

from ..domain.events import DomainEvent

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=DomainEvent)

class EventBus:
    """Simple event bus for publishing and subscribing to domain events."""
    
    def __init__(self):
        self._subscribers: Dict[Type, List[Callable]] = defaultdict(list)
    
    def publish(self, event: DomainEvent) -> None:
        """Publish an event to all subscribers."""
        event_type = type(event)
        subscribers = self._subscribers.get(event_type, [])
        
        logger.debug(f"Publishing event {event_type.__name__} to {len(subscribers)} subscribers")
        
        for subscriber in subscribers:
            try:
                subscriber(event)
            except Exception as e:
                logger.error(f"Error handling event {event_type.__name__}: {e}")
    
    def subscribe(self, event_type: Type[T], handler: Callable[[T], None]) -> None:
        """Subscribe to a specific event type."""
        self._subscribers[event_type].append(handler)
        logger.debug(f"Added subscriber to {event_type.__name__}, total: {len(self._subscribers[event_type])}")
    
    def unsubscribe(self, event_type: Type[T], handler: Callable[[T], None]) -> None:
        """Unsubscribe from a specific event type."""
        if event_type in self._subscribers:
            try:
                self._subscribers[event_type].remove(handler)
                logger.debug(f"Removed subscriber from {event_type.__name__}, remaining: {len(self._subscribers[event_type])}")
            except ValueError:
                logger.warning(f"Handler not found for event type {event_type.__name__}")
```

#### Task 2.2: Implement Repository Interfaces (2 days)
Define interfaces for repositories.

**Implementation Details:**
```python
# src/DevAgent/interpreter/domain/repositories.py
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
```

#### Task 2.3: Implement File System Manager (4 days)
Create an abstraction over filesystem operations.

**Implementation Details:**
```python
# src/DevAgent/interpreter/infrastructure/fs_manager.py
import json
import os
import shutil
import fcntl
import logging
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

class FileLock:
    """A simple file-based lock for thread safety."""
    
    def __init__(self, path: Path):
        self.path = path
        self.lock_path = path.with_suffix(path.suffix + '.lock')
        self.lock_file = None
    
    def __enter__(self):
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
        if self.lock_file:
            try:
                fcntl.flock(self.lock_file, fcntl.LOCK_UN)
                self.lock_file.close()
                self.lock_path.unlink()
            except Exception as e:
                logger.error(f"Error releasing lock for {self.path}: {e}")

class FileSystemManager:
    """Manages filesystem operations for the interpreter."""
    
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
    
    def ensure_directory_structure(self) -> None:
        """Ensure the basic directory structure exists."""
        (self.base_dir / "by-name").mkdir(parents=True, exist_ok=True)
        (self.base_dir / "by-id" / "sessions").mkdir(parents=True, exist_ok=True)
        (self.base_dir / "registry").mkdir(parents=True, exist_ok=True)
        logger.debug(f"Ensured directory structure at {self.base_dir}")
    
    def create_session_directory(self, session_id: str) -> Path:
        """Create a session directory and return its path."""
        session_path = self.base_dir / "by-id" / "sessions" / session_id
        session_path.mkdir(parents=True, exist_ok=True)
        (session_path / "kernels").mkdir(exist_ok=True)
        logger.debug(f"Created session directory: {session_path}")
        return session_path
    
    def create_kernel_directory(self, session_path: Path, kernel_id: str) -> Path:
        """Create a kernel directory within a session and return its path."""
        kernel_path = session_path / "kernels" / kernel_id
        kernel_path.mkdir(parents=True, exist_ok=True)
        workspace_path = kernel_path / "workspace"
        workspace_path.mkdir(exist_ok=True)
        logger.debug(f"Created kernel directory: {kernel_path}")
        return kernel_path
    
    def get_session_path(self, session_id: str) -> Path:
        """Get the path to a session directory."""
        return self.base_dir / "by-id" / "sessions" / session_id
    
    def get_kernel_path(self, session_path: Path, kernel_id: str) -> Path:
        """Get the path to a kernel directory."""
        return session_path / "kernels" / kernel_id
    
    def atomic_write_json(self, path: Path, data: Dict[str, Any]) -> None:
        """Write JSON data to a file atomically."""
        # Implementation similar to current fs.py
        # ...
    
    def atomic_read_json(self, path: Path, default: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Read JSON data from a file, returning default if file doesn't exist."""
        # Implementation similar to current fs.py
        # ...
    
    def create_symlink(self, source: Path, target: Path) -> bool:
        """Create a symlink."""
        # Implementation similar to current fs.py
        # ...
    
    def create_symlink_dir(self, source: Path, target: Path) -> bool:
        """Create a directory for symlinks."""
        # Implementation similar to current fs.py
        # ...
    
    def remove_directory(self, path: Path) -> bool:
        """Remove a directory and all its contents."""
        # Implementation similar to current fs.py
        # ...
```

#### Task 2.4: Implement FileSystem Repositories (5 days)
Implement repository interfaces using filesystem persistence.

**Implementation Details:**
```python
# src/DevAgent/interpreter/infrastructure/repositories.py
from pathlib import Path
import time
from typing import Dict, List, Optional

from ..domain.model import Session, Kernel
from ..domain.value_objects import SessionId, KernelId
from ..domain.repositories import SessionRepository, KernelRepository
from .fs_manager import FileSystemManager
from .event_bus import EventBus
from ..domain.events import SessionCreated, SessionDeleted, KernelCreated, KernelShutdown

class FileSystemSessionRepository:
    """Implementation of SessionRepository using filesystem storage."""
    
    def __init__(self, fs_manager: FileSystemManager, event_bus: EventBus):
        self.fs_manager = fs_manager
        self.event_bus = event_bus
        self._cache: Dict[str, Session] = {}
    
    def save(self, session: Session) -> None:
        """Save a session to the repository."""
        # Create session directory if it doesn't exist
        session_path = self.fs_manager.get_session_path(str(session.id))
        if not session_path.exists():
            session_path = self.fs_manager.create_session_directory(str(session.id))
            
            # Create registry entry and symlink
            self._register_session_name(session.name, str(session.id))
            self.fs_manager.create_symlink_dir(
                self.fs_manager.base_dir / "by-name" / session.name,
                session_path
            )
        
        # Save session metadata
        metadata = {
            "id": str(session.id),
            "name": session.name,
            "created_at": session.created_at,
            "last_activity": session.last_activity,
            "kernels": [
                {"id": str(k.id), "name": k.name}
                for k in session.list_kernels()
            ]
        }
        
        self.fs_manager.atomic_write_json(session_path / "metadata.json", metadata)
        
        # Update cache
        self._cache[str(session.id)] = session
    
    def find_by_id(self, session_id: SessionId) -> Optional[Session]:
        """Find a session by ID."""
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
            last_activity=metadata.get("last_activity", time.time())
        )
        
        # Load kernels (minimal info, actual kernels loaded on demand)
        for kernel_info in metadata.get("kernels", []):
            # We're not populating the actual Kernel objects here, 
            # as that would be done by KernelRepository
            pass
        
        # Cache and return
        self._cache[str(session_id)] = session
        return session
    
    def find_by_name(self, name: str) -> Optional[Session]:
        """Find a session by name."""
        # Look up session ID from registry
        registry = self._read_session_registry()
        session_id = registry.get(name)
        if not session_id:
            return None
        
        return self.find_by_id(SessionId(session_id))
    
    def delete(self, session_id: SessionId) -> bool:
        """Delete a session from the repository."""
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
        """List all sessions in the repository."""
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
                        last_activity=metadata.get("last_activity", time.time())
                    )
                    self._cache[str(session_id)] = session
                    sessions.append(session)
        
        return sessions
    
    def _register_session_name(self, name: str, session_id: str) -> None:
        """Register a session name to ID mapping."""
        registry = self._read_session_registry()
        registry[name] = session_id
        self._write_session_registry(registry)
    
    def _read_session_registry(self) -> Dict[str, str]:
        """Read the session registry."""
        registry_path = self.fs_manager.base_dir / "registry" / "sessions.json"
        return self.fs_manager.atomic_read_json(registry_path, {})
    
    def _write_session_registry(self, registry: Dict[str, str]) -> None:
        """Write the session registry."""
        registry_path = self.fs_manager.base_dir / "registry" / "sessions.json"
        self.fs_manager.atomic_write_json(registry_path, registry)

class FileSystemKernelRepository:
    """Implementation of KernelRepository using filesystem storage."""
    
    # Similar implementation to FileSystemSessionRepository
    # with methods for saving, finding, and deleting kernels
    # ...
```

#### Task 2.5: Implement Kernel Controller Adapter (5 days)
Create an adapter to bridge the existing KernelController with the new domain model.

**Implementation Details:**
```python
# src/DevAgent/interpreter/infrastructure/kernel_adapter.py
from typing import Dict, Optional

from ..domain.model import Kernel
from ..domain.value_objects import KernelId, SessionId, ExecutionResult
from ...interpreter.kernel import KernelController as LegacyKernelController

class KernelControllerAdapter:
    """
    Adapter that connects the domain Kernel model to the infrastructure KernelController.
    This allows the domain model to remain pure while delegating actual kernel
    operations to the existing implementation.
    """
    
    def __init__(self):
        self._controllers: Dict[str, LegacyKernelController] = {}
    
    def get_controller(self, kernel: Kernel, workspace_dir) -> LegacyKernelController:
        """Get or create a controller for the given kernel."""
        kernel_id = str(kernel.id)
        
        # Check if we already have a controller
        if kernel_id in self._controllers:
            controller = self._controllers[kernel_id]
            if controller.is_alive():
                return controller
            else:
                # Remove dead controller
                del self._controllers[kernel_id]
        
        # Create new controller
        controller = LegacyKernelController(
            id=kernel_id,
            name=kernel.name,
            kernel_type=kernel.kernel_type,
            session_id=str(kernel.session_id),
            workspace_dir=workspace_dir
        )
        
        self._controllers[kernel_id] = controller
        return controller
    
    def start_kernel(self, kernel: Kernel, workspace_dir) -> bool:
        """Start the kernel process."""
        controller = self.get_controller(kernel, workspace_dir)
        success = controller.start_kernel()
        if success:
            kernel._is_alive = True
        return success
    
    def execute_code(self, kernel: Kernel, code: str, workspace_dir) -> ExecutionResult:
        """Execute code in the kernel."""
        controller = self.get_controller(kernel, workspace_dir)
        
        # Execute using legacy controller
        legacy_result = controller.execute(code)
        
        # Map to domain ExecutionResult
        result = ExecutionResult(
            success=legacy_result.success,
            stdout=legacy_result.stdout,
            error=legacy_result.error,
            outputs=legacy_result.outputs,
            execution_time=legacy_result.execution_time
        )
        
        # Update kernel state
        kernel.update_last_activity()
        
        return result
    
    def interrupt_kernel(self, kernel: Kernel, workspace_dir) -> bool:
        """Interrupt the kernel's execution."""
        controller = self.get_controller(kernel, workspace_dir)
        return controller.interrupt()
    
    def restart_kernel(self, kernel: Kernel, workspace_dir) -> bool:
        """Restart the kernel."""
        controller = self.get_controller(kernel, workspace_dir)
        success = controller.restart()
        kernel._is_alive = success
        return success
    
    def shutdown_kernel(self, kernel: Kernel, workspace_dir) -> bool:
        """Shutdown the kernel."""
        controller = self.get_controller(kernel, workspace_dir)
        success = controller.shutdown()
        if success:
            kernel._is_alive = False
            # Remove from controllers cache
            if str(kernel.id) in self._controllers:
                del self._controllers[str(kernel.id)]
        return success
```

### Milestone 3: Domain Services Layer (2 weeks)
Create the domain services that implement core business logic.

#### Task 3.1: Implement Reference Resolution Service (3 days)
Create a service to handle reference resolution.

**Implementation Details:**
```python
# src/DevAgent/interpreter/domain/services.py
from typing import Dict, Optional, Union
from pathlib import Path

from .value_objects import SessionId, KernelId, Reference
from .exceptions import ReferenceResolutionError
from .repositories import SessionRepository, KernelRepository

class ReferenceResolutionService:
    """Service for resolving reference strings to domain objects."""
    
    def __init__(self, session_repo: SessionRepository, kernel_repo: KernelRepository):
        self.session_repo = session_repo
        self.kernel_repo = kernel_repo
    
    def resolve_reference(self, reference_string: str) -> Dict[str, Optional[Union[str, Path]]]:
        """
        Resolve a reference string to components.
        
        Returns a dict with:
        - type: "session" or "kernel" or None
        - session_id: The session ID or None
        - kernel_id: The kernel ID or None
        - session_path: Path to the session directory or None
        - kernel_path: Path to the kernel directory or None
        """
        result = {
            "type": None, 
            "session_id": None, 
            "kernel_id": None, 
            "session_path": None, 
            "kernel_path": None
        }
        
        # Case 1: Session/Kernel format
        if "/" in reference_string:
            session_name, kernel_name = reference_string.split("/", 1)
            session = self.session_repo.find_by_name(session_name)
            
            if session:
                result["type"] = "kernel"
                result["session_id"] = str(session.id)
                
                # Look up the kernel
                kernel = session.get_kernel_by_name(kernel_name)
                if kernel:
                    result["kernel_id"] = str(kernel.id)
                
                return result
        
        # Case 2: Session name or ID
        if reference_string.startswith("sid-"):
            session = self.session_repo.find_by_id(SessionId(reference_string))
        else:
            session = self.session_repo.find_by_name(reference_string)
        
        if session:
            result["type"] = "session"
            result["session_id"] = str(session.id)
            return result
        
        # Case 3: Kernel ID directly
        if reference_string.startswith("kid-"):
            kernel = self.kernel_repo.find_by_id(KernelId(reference_string))
            if kernel:
                result["type"] = "kernel"
                result["kernel_id"] = str(kernel.id)
                result["session_id"] = str(kernel.session_id)
                return result
        
        return result
    
    def parse_reference(self, reference_string: str) -> Reference:
        """Parse a reference string into a Reference value object."""
        # Implementation details...
        pass
```

#### Task 3.2: Implement Session Factory (3 days)
Create a factory for creating well-formed Session aggregates.

**Implementation Details:**
```python
# src/DevAgent/interpreter/domain/factories.py
import time
from typing import Optional

from .model import Session, Kernel
from .value_objects import SessionId, KernelId
from .repositories import SessionRepository, KernelRepository
from .events import SessionCreated, KernelCreated
from .exceptions import SessionError

class SessionFactory:
    """Factory for creating Session aggregates."""
    
    def __init__(self, session_repo: SessionRepository, event_bus):
        self.session_repo = session_repo
        self.event_bus = event_bus
    
    def create_session(self, name: str) -> Session:
        """Create a new session with the given name."""
        # Check if session with this name already exists
        existing = self.session_repo.find_by_name(name)
        if existing:
            raise SessionError(f"Session with name '{name}' already exists")
        
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
        self.kernel_repo = kernel_repo
        self.event_bus = event_bus
    
    def create_kernel(self, session: Session, name: str, kernel_type: str = "python3") -> Kernel:
        """Create a new kernel in the given session."""
        # Check if kernel with this name already exists
        existing = session.get_kernel_by_name(name)
        if existing:
            raise ValueError(f"Kernel with name '{name}' already exists in session")
        
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
```

#### Task 3.3: Implement Kernel Execution Service (4 days)
Create a service to handle kernel execution.

**Implementation Details:**
```python
# src/DevAgent/interpreter/domain/services.py (continued)
from .model import Kernel
from .value_objects import KernelId, ExecutionResult
from .events import CodeExecuted, KernelStarted, KernelShutdown
from .exceptions import KernelError

class KernelLifecycleService:
    """Service for managing kernel lifecycle operations."""
    
    def __init__(self, kernel_repo, kernel_adapter, event_bus, fs_manager):
        self.kernel_repo = kernel_repo
        self.kernel_adapter = kernel_adapter
        self.event_bus = event_bus
        self.fs_manager = fs_manager
    
    def start_kernel(self, kernel: Kernel) -> bool:
        """Start a kernel."""
        # Get workspace directory
        session_path = self.fs_manager.get_session_path(str(kernel.session_id))
        kernel_path = self.fs_manager.get_kernel_path(session_path, str(kernel.id))
        workspace_dir = kernel_path / "workspace"
        
        # Start kernel using adapter
        success = self.kernel_adapter.start_kernel(kernel, workspace_dir)
        
        if success:
            # Update repository
            self.kernel_repo.save(kernel)
            
            # Publish event
            self.event_bus.publish(KernelStarted(kernel.id, time.time()))
        
        return success
    
    def shutdown_kernel(self, kernel: Kernel) -> bool:
        """Shutdown a kernel."""
        # Get workspace directory
        session_path = self.fs_manager.get_session_path(str(kernel.session_id))
        kernel_path = self.fs_manager.get_kernel_path(session_path, str(kernel.id))
        workspace_dir = kernel_path / "workspace"
        
        # Shutdown kernel using adapter
        success = self.kernel_adapter.shutdown_kernel(kernel, workspace_dir)
        
        if success:
            # Update repository
            self.kernel_repo.save(kernel)
            
            # Publish event
            self.event_bus.publish(KernelShutdown(kernel.id, time.time()))
        
        return success

class ExecutionService:
    """Service for executing code in kernels."""
    
    def __init__(self, kernel_repo, kernel_adapter, event_bus, fs_manager):
        self.kernel_repo = kernel_repo
        self.kernel_adapter = kernel_adapter
        self.event_bus = event_bus
        self.fs_manager = fs_manager
    
    def execute_code(self, kernel: Kernel, code: str) -> ExecutionResult:
        """Execute code in a kernel."""
        if not kernel.is_alive:
            raise KernelError(f"Kernel {kernel.id} is not alive")
        
        # Get workspace directory
        session_path = self.fs_manager.get_session_path(str(kernel.session_id))
        kernel_path = self.fs_manager.get_kernel_path(session_path, str(kernel.id))
        workspace_dir = kernel_path / "workspace"
        
        # Execute code using adapter
        result = self.kernel_adapter.execute_code(kernel, code, workspace_dir)
        
        # Update repository
        self.kernel_repo.save(kernel)
        
        # Publish event
        self.event_bus.publish(CodeExecuted(
            kernel_id=kernel.id,
            success=result.success,
            execution_time=result.execution_time,
            timestamp=time.time()
        ))
        
        return result
```

### Milestone 4: Application Services Layer (2 weeks)
Create application services that coordinate domain operations.

#### Task 4.1: Implement DTOs (2 days)
Create Data Transfer Objects for API responses.

**Implementation Details:**
```python
# src/DevAgent/interpreter/application/dtos.py
from dataclasses import dataclass
from typing import List, Optional
import time

@dataclass
class SessionDTO:
    """Data Transfer Object for Session information."""
    id: str
    name: str
    created_at: float
    last_activity: float
    kernel_count: int
    path: Optional[str] = None

@dataclass
class KernelDTO:
    """Data Transfer Object for Kernel information."""
    id: str
    name: str
    kernel_type: str
    session_id: str
    session_name: str
    is_alive: bool
    created_at: float
    last_activity: float
    path: Optional[str] = None

@dataclass
class ExecutionResultDTO:
    """Data Transfer Object for ExecutionResult."""
    success: bool
    stdout: str
    error: Optional[str]
    outputs: List
    execution_time: float
```

#### Task 4.2: Implement Interpreter Application Service (5 days)
Create the main application service that coordinates domain operations.

**Implementation Details:**
```python
# src/DevAgent/interpreter/application/app_service.py
from typing import List, Optional

from ..domain.repositories import SessionRepository, KernelRepository
from ..domain.services import ReferenceResolutionService, ExecutionService, KernelLifecycleService
from ..domain.factories import SessionFactory, KernelFactory
from ..domain.value_objects import SessionId, KernelId, ExecutionResult
from ..domain.exceptions import SessionError, KernelError, ReferenceResolutionError
from .dtos import SessionDTO, KernelDTO, ExecutionResultDTO

class InterpreterApplicationService:
    """Main application service for the interpreter."""
    
    def __init__(
        self,
        session_repo: SessionRepository,
        kernel_repo: KernelRepository,
        session_factory: SessionFactory,
        kernel_factory: KernelFactory,
        reference_service: ReferenceResolutionService,
        execution_service: ExecutionService,
        kernel_lifecycle_service: KernelLifecycleService,
        fs_manager
    ):
        self.session_repo = session_repo
        self.kernel_repo = kernel_repo
        self.session_factory = session_factory
        self.kernel_factory = kernel_factory
        self.reference_service = reference_service
        self.execution_service = execution_service
        self.kernel_lifecycle_service = kernel_lifecycle_service
        self.fs_manager = fs_manager
    
    def create_session(self, name: str) -> str:
        """Create a new session."""
        session = self.session_factory.create_session(name)
        return str(session.id)
    
    def get_session_dto(self, reference: str) -> Optional[SessionDTO]:
        """Get a session DTO by reference."""
        # Resolve reference
        resolved = self.reference_service.resolve_reference(reference)
        
        if resolved["type"] != "session" or not resolved["session_id"]:
            return None
        
        # Get session
        session = self.session_repo.find_by_id(SessionId(resolved["session_id"]))
        if not session:
            return None
        
        # Create DTO
        return SessionDTO(
            id=str(session.id),
            name=session.name,
            created_at=session.created_at,
            last_activity=session.last_activity,
            kernel_count=len(session.list_kernels()),
            path=str(self.fs_manager.get_session_path(str(session.id)))
        )
    
    def list_sessions(self) -> List[SessionDTO]:
        """List all sessions."""
        sessions = self.session_repo.list_all()
        return [
            SessionDTO(
                id=str(session.id),
                name=session.name,
                created_at=session.created_at,
                last_activity=session.last_activity,
                kernel_count=len(session.list_kernels()),
                path=str(self.fs_manager.get_session_path(str(session.id)))
            )
            for session in sessions
        ]
    
    def delete_session(self, reference: str) -> bool:
        """Delete a session."""
        # Resolve reference
        resolved = self.reference_service.resolve_reference(reference)
        
        if resolved["type"] != "session" or not resolved["session_id"]:
            return False
        
        # Delete session
        return self.session_repo.delete(SessionId(resolved["session_id"]))
    
    def create_kernel(self, session_reference: str, kernel_name: str, kernel_type: str = "python3") -> str:
        """Create a new kernel in a session."""
        # Resolve session reference
        resolved = self.reference_service.resolve_reference(session_reference)
        
        if resolved["type"] != "session" or not resolved["session_id"]:
            raise SessionError(f"Session not found: {session_reference}")
        
        # Get session
        session = self.session_repo.find_by_id(SessionId(resolved["session_id"]))
        if not session:
            raise SessionError(f"Session not found: {session_reference}")
        
        # Create kernel
        kernel = self.kernel_factory.create_kernel(session, kernel_name, kernel_type)
        
        # Start kernel
        self.kernel_lifecycle_service.start_kernel(kernel)
        
        return str(kernel.id)
    
    # Additional methods for get_kernel_dto, list_kernels, delete_kernel, execute_code, etc.
    # ...
```

#### Task 4.3: Implement API Facade (3 days)
Create a facade to expose the application service to external consumers.

**Implementation Details:**
```python
# src/DevAgent/interpreter/application/facade.py
from typing import Dict, List, Optional, Any

from .app_service import InterpreterApplicationService
from ..domain.exceptions import DomainError, SessionError, KernelError
from ..domain.value_objects import ExecutionResult

class InterpreterFacade:
    """
    Public facade for the interpreter system.
    This is the main entry point for external clients.
    """
    
    def __init__(self, app_service: InterpreterApplicationService):
        self.app_service = app_service
    
    def create_session(self, name: str) -> Dict[str, Any]:
        """Create a new session."""
        try:
            session_id = self.app_service.create_session(name)
            return {
                "success": True,
                "session_id": session_id,
                "error": None
            }
        except SessionError as e:
            return {
                "success": False,
                "session_id": None,
                "error": str(e)
            }
        except Exception as e:
            return {
                "success": False,
                "session_id": None,
                "error": f"Unexpected error: {str(e)}"
            }
    
    def get_session(self, reference: str) -> Dict[str, Any]:
        """Get a session by reference."""
        try:
            session_dto = self.app_service.get_session_dto(reference)
            if not session_dto:
                return {
                    "success": False,
                    "session": None,
                    "error": f"Session not found: {reference}"
                }
            
            return {
                "success": True,
                "session": session_dto.__dict__,
                "error": None
            }
        except Exception as e:
            return {
                "success": False,
                "session": None,
                "error": f"Unexpected error: {str(e)}"
            }
    
    def list_sessions(self) -> Dict[str, Any]:
        """List all sessions."""
        try:
            sessions = self.app_service.list_sessions()
            return {
                "success": True,
                "sessions": [s.__dict__ for s in sessions],
                "error": None
            }
        except Exception as e:
            return {
                "success": False,
                "sessions": [],
                "error": f"Unexpected error: {str(e)}"
            }
    
    # Additional methods for delete_session, create_kernel, etc.
    # ...
    
    def execute_code(self, reference: str, code: str) -> Dict[str, Any]:
        """Execute code in a kernel."""
        try:
            result = self.app_service.execute_code(reference, code)
            return {
                "success": result.success,
                "stdout": result.stdout,
                "error": result.error,
                "outputs": result.outputs,
                "execution_time": result.execution_time
            }
        except KernelError as e:
            return {
                "success": False,
                "stdout": "",
                "error": str(e),
                "outputs": [],
                "execution_time": 0.0
            }
        except Exception as e:
            return {
                "success": False,
                "stdout": "",
                "error": f"Unexpected error: {str(e)}",
                "outputs": [],
                "execution_time": 0.0
            }
```

### Milestone 5: DDD CLI Adapter (1 week)
Adapt the CLI to work with the new DDD architecture.

#### Task 5.1: Create Command Handlers (3 days)
Implement command handlers for CLI operations.

**Implementation Details:**
```python
# src/DevAgent/interpreter/application/cli_handlers.py
from typing import TextIO, Dict, Any, Callable

class InterpreterSessionCommandHandler:
    """Handler for interpreter session CLI commands."""
    
    def __init__(self, interpreter_facade):
        self.facade = interpreter_facade
    
    def handle_create(self, name: str, stdout: TextIO) -> bool:
        """Handle 'create' command."""
        result = self.facade.create_session(name)
        if result["success"]:
            stdout.write(f"Session created: {name}\n")
            stdout.write(f"Session ID: {result['session_id']}\n")
            return True
        else:
            stdout.write(f"Failed to create session: {result['error']}\n")
            return False
    
    def handle_list(self, stdout: TextIO) -> bool:
        """Handle 'list' command."""
        result = self.facade.list_sessions()
        if result["success"]:
            sessions = result["sessions"]
            if sessions:
                stdout.write("Active sessions:\n")
                for session in sessions:
                    stdout.write(f"  ID: {session['id']}, Name: {session['name']}\n")
                    stdout.write(f"    Kernels: {session['kernel_count']}\n")
                    if "path" in session and session["path"]:
                        stdout.write(f"    Path: {session['path']}\n")
            else:
                stdout.write("No active sessions\n")
            return True
        else:
            stdout.write(f"Failed to list sessions: {result['error']}\n")
            return False
    
    # Other command handlers...

class InterpreterKernelCommandHandler:
    """Handler for interpreter kernel CLI commands."""
    
    def __init__(self, interpreter_facade):
        self.facade = interpreter_facade
    
    def handle_create(self, session_ref: str, name: str, kernel_type: str, stdout: TextIO) -> bool:
        """Handle 'create' command."""
        result = self.facade.create_kernel(session_ref, name, kernel_type)
        if result["success"]:
            stdout.write(f"Kernel created: {name}\n")
            stdout.write(f"Kernel ID: {result['kernel_id']}\n")
            stdout.write(f"Kernel Type: {kernel_type}\n")
            stdout.write(f"In Session: {session_ref}\n")
            return True
        else:
            stdout.write(f"Failed to create kernel: {result['error']}\n")
            return False
    
    # Other command handlers...
```

#### Task 5.2: Integrate with __main__.py (4 days)
Update the CLI entry point to use the new architecture.

**Implementation Details:**
```python
# src/DevAgent/__main__.py (updates)
# ...

def handle_interpreter_session(
    # existing parameters
):
    """Handle the 'interpreter session' subcommand."""
    # Get the session action
    try:
        action = pop_arg("action")
    except Exception:
        # Show usage
        return
    
    # Create DDD infrastructure (simplified for example)
    fs_manager = FileSystemManager(base_dir_path)
    event_bus = EventBus()
    
    # Create repositories
    session_repo = FileSystemSessionRepository(fs_manager, event_bus)
    kernel_repo = FileSystemKernelRepository(fs_manager, event_bus)
    
    # Create domain services
    reference_service = ReferenceResolutionService(session_repo, kernel_repo)
    session_factory = SessionFactory(session_repo, event_bus)
    kernel_factory = KernelFactory(kernel_repo, event_bus)
    
    # Create application service
    app_service = InterpreterApplicationService(
        session_repo, kernel_repo, session_factory, kernel_factory, 
        reference_service, execution_service, kernel_lifecycle_service, fs_manager
    )
    
    # Create facade
    facade = InterpreterFacade(app_service)
    
    # Create command handler
    handler = InterpreterSessionCommandHandler(facade)
    
    # Handle different actions
    if action == "create":
        try:
            session_name = get_kwarg("name", "main")
        except:
            session_name = "main"
        
        handler.handle_create(session_name, stdout)
    
    elif action == "list":
        handler.handle_list(stdout)
    
    # Other actions...

# Similar updates for handle_interpreter_kernel
# ...
```

### Milestone 6: Testing and Validation (2 weeks)
Implement tests to ensure the new architecture works as expected.

#### Task 6.1: Create Unit Tests for Domain Model (4 days)
Write unit tests for the domain model.

**Implementation Details:**
```python
# tests/unit/interpreter/domain/test_model.py
import unittest
from unittest.mock import MagicMock
import time

from DevAgent.interpreter.domain.model import Session, Kernel
from DevAgent.interpreter.domain.value_objects import SessionId, KernelId, ExecutionResult
from DevAgent.interpreter.domain.exceptions import KernelNotFoundError

class TestSession(unittest.TestCase):
    
    def setUp(self):
        self.session_id = SessionId.generate()
        self.session = Session(
            id=self.session_id,
            name="test_session",
            created_at=time.time(),
            last_activity=time.time()
        )
    
    def test_add_kernel(self):
        # Create a kernel
        kernel_id = KernelId.generate()
        kernel = Kernel(
            id=kernel_id,
            name="test_kernel",
            session_id=self.session_id,
            kernel_type="python3"
        )
        
        # Add to session
        self.session.add_kernel(kernel)
        
        # Verify
        self.assertEqual(len(self.session.list_kernels()), 1)
        
        # Try to add again - should raise error
        with self.assertRaises(ValueError):
            self.session.add_kernel(kernel)
    
    def test_get_kernel(self):
        # Create and add kernel
        kernel_id = KernelId.generate()
        kernel = Kernel(
            id=kernel_id,
            name="test_kernel",
            session_id=self.session_id,
            kernel_type="python3"
        )
        self.session.add_kernel(kernel)
        
        # Get by ID
        retrieved = self.session.get_kernel(kernel_id)
        self.assertEqual(retrieved.id, kernel_id)
        
        # Get by name
        retrieved = self.session.get_kernel_by_name("test_kernel")
        self.assertEqual(retrieved.id, kernel_id)
        
        # Get non-existent
        with self.assertRaises(KernelNotFoundError):
            self.session.get_kernel(KernelId.generate())
        
        self.assertIsNone(self.session.get_kernel_by_name("non-existent"))
    
    # Additional tests...
```

#### Task 6.2: Create Integration Tests (5 days)
Write integration tests for the components working together.

**Implementation Details:**
```python
# tests/integration/interpreter/test_application.py
import unittest
import tempfile
import shutil
from pathlib import Path

from DevAgent.interpreter.infrastructure.fs_manager import FileSystemManager
from DevAgent.interpreter.infrastructure.event_bus import EventBus
from DevAgent.interpreter.infrastructure.repositories import FileSystemSessionRepository, FileSystemKernelRepository
from DevAgent.interpreter.domain.services import ReferenceResolutionService
from DevAgent.interpreter.domain.factories import SessionFactory, KernelFactory
from DevAgent.interpreter.application.app_service import InterpreterApplicationService

class TestInterpreterApplication(unittest.TestCase):
    
    def setUp(self):
        # Create temporary directory
        self.temp_dir = Path(tempfile.mkdtemp())
        
        # Create infrastructure
        self.fs_manager = FileSystemManager(self.temp_dir)
        self.fs_manager.ensure_directory_structure()
        self.event_bus = EventBus()
        
        # Create repositories
        self.session_repo = FileSystemSessionRepository(self.fs_manager, self.event_bus)
        self.kernel_repo = FileSystemKernelRepository(self.fs_manager, self.event_bus)
        
        # Create domain services
        self.reference_service = ReferenceResolutionService(
            self.session_repo, self.kernel_repo
        )
        
        # Create factories
        self.session_factory = SessionFactory(self.session_repo, self.event_bus)
        self.kernel_factory = KernelFactory(self.kernel_repo, self.event_bus)
        
        # Create services (mocked or simplified for tests)
        self.execution_service = MagicMock()
        self.kernel_lifecycle_service = MagicMock()
        
        # Create application service
        self.app_service = InterpreterApplicationService(
            self.session_repo,
            self.kernel_repo,
            self.session_factory,
            self.kernel_factory,
            self.reference_service,
            self.execution_service,
            self.kernel_lifecycle_service,
            self.fs_manager
        )
    
    def tearDown(self):
        # Clean up
        shutil.rmtree(self.temp_dir)
    
    def test_create_and_get_session(self):
        # Create session
        session_id = self.app_service.create_session("test_session")
        
        # Get session
        session_dto = self.app_service.get_session_dto("test_session")
        
        # Verify
        self.assertIsNotNone(session_dto)
        self.assertEqual(session_dto.id, session_id)
        self.assertEqual(session_dto.name, "test_session")
        self.assertEqual(session_dto.kernel_count, 0)
    
    def test_create_and_list_sessions(self):
        # Create sessions
        self.app_service.create_session("session1")
        self.app_service.create_session("session2")
        
        # List sessions
        sessions = self.app_service.list_sessions()
        
        # Verify
        self.assertEqual(len(sessions), 2)
        names = {s.name for s in sessions}
        self.assertEqual(names, {"session1", "session2"})
    
    # Additional integration tests...
```

#### Task 6.3: Create System Tests (5 days)
Write system tests for the entire interpreter.

**Implementation Details:**
```python
# tests/system/test_interpreter.py
import unittest
import subprocess
import tempfile
import os
import json
from pathlib import Path

class TestInterpreterCLI(unittest.TestCase):
    
    def setUp(self):
        # Create temporary directory
        self.temp_dir = tempfile.mkdtemp()
        self.base_dir = Path(self.temp_dir) / ".devagent"
        
        # Environment for subprocess calls
        self.env = os.environ.copy()
        self.env["PYTHONPATH"] = os.getcwd()
    
    def tearDown(self):
        # Clean up
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def run_cli(self, args):
        """Run CLI command and return (stdout, stderr, return_code)."""
        cmd = ["python", "-m", "DevAgent"] + args + ["--dir", str(self.base_dir)]
        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            env=self.env, universal_newlines=True
        )
        stdout, stderr = process.communicate()
        return stdout, stderr, process.returncode
    
    def test_create_session(self):
        # Create session
        stdout, stderr, rc = self.run_cli(["interpreter", "session", "create", "--name=test_session"])
        
        # Verify
        self.assertEqual(rc, 0)
        self.assertIn("Session created: test_session", stdout)
        
        # List sessions
        stdout, stderr, rc = self.run_cli(["interpreter", "session", "list"])
        
        # Verify
        self.assertEqual(rc, 0)
        self.assertIn("test_session", stdout)
    
    def test_create_and_use_kernel(self):
        # Create session
        self.run_cli(["interpreter", "session", "create", "--name=test_session"])
        
        # Create kernel
        stdout, stderr, rc = self.run_cli([
            "interpreter", "kernel", "create",
            "--session=test_session",
            "--name=test_kernel"
        ])
        
        # Verify
        self.assertEqual(rc, 0)
        self.assertIn("Kernel created: test_kernel", stdout)
        
        # Execute code
        stdout, stderr, rc = self.run_cli([
            "interpreter", "kernel", "execute",
            "--ref=test_session/test_kernel",
            "--code=print('hello world')"
        ])
        
        # Verify
        self.assertEqual(rc, 0)
        self.assertIn("hello world", stdout)
    
    # Additional system tests...
```

### Milestone 7: Migration and Deployment (2 weeks)
Implement the migration strategy and deploy the new architecture.

#### Task 7.1: Create Migration Scripts (5 days)
Develop scripts to migrate existing data to the new format.

**Implementation Details:**
```python
# src/DevAgent/interpreter/migration.py
import json
import shutil
import time
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class DataMigrator:
    """Migrates data from old format to new DDD-based format."""
    
    def __init__(self, old_base_dir: Path, new_base_dir: Path):
        self.old_base_dir = old_base_dir
        self.new_base_dir = new_base_dir
    
    def migrate(self) -> bool:
        """Perform the migration."""
        logger.info(f"Starting migration from {self.old_base_dir} to {self.new_base_dir}")
        
        try:
            # Create new directory structure
            self._ensure_directory_structure()
            
            # Migrate sessions
            self._migrate_sessions()
            
            # Migrate registries
            self._migrate_registries()
            
            # Migrate symlinks
            self._migrate_symlinks()
            
            logger.info("Migration completed successfully")
            return True
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            return False
    
    def _ensure_directory_structure(self) -> None:
        """Ensure the new directory structure exists."""
        (self.new_base_dir / "by-name").mkdir(parents=True, exist_ok=True)
        (self.new_base_dir / "by-id" / "sessions").mkdir(parents=True, exist_ok=True)
        (self.new_base_dir / "registry").mkdir(parents=True, exist_ok=True)
    
    def _migrate_sessions(self) -> None:
        """Migrate session data."""
        sessions_dir = self.old_base_dir / "by-id" / "sessions"
        if not sessions_dir.exists():
            logger.warning(f"Sessions directory not found: {sessions_dir}")
            return
        
        # Process each session
        for session_path in sessions_dir.glob("*"):
            session_id = session_path.name
            
            # Read metadata
            metadata_path = session_path / "metadata.json"
            if not metadata_path.exists():
                logger.warning(f"Session metadata not found: {metadata_path}")
                continue
            
            try:
                with open(metadata_path, "r") as f:
                    metadata = json.load(f)
            except Exception as e:
                logger.error(f"Error reading session metadata from {metadata_path}: {e}")
                continue
            
            # Create new session directory
            new_session_path = self.new_base_dir / "by-id" / "sessions" / session_id
            new_session_path.mkdir(parents=True, exist_ok=True)
            (new_session_path / "kernels").mkdir(exist_ok=True)
            
            # Copy metadata (no changes needed for basic fields)
            with open(new_session_path / "metadata.json", "w") as f:
                json.dump(metadata, f, indent=2)
            
            # Process each kernel
            kernels_dir = session_path / "kernels"
            if kernels_dir.exists():
                for kernel_path in kernels_dir.glob("*"):
                    self._migrate_kernel(kernel_path, new_session_path / "kernels" / kernel_path.name)
    
    def _migrate_kernel(self, old_kernel_path: Path, new_kernel_path: Path) -> None:
        """Migrate a single kernel."""
        new_kernel_path.mkdir(parents=True, exist_ok=True)
        (new_kernel_path / "workspace").mkdir(exist_ok=True)
        
        # Copy metadata and connection info
        metadata_path = old_kernel_path / "metadata.json"
        connection_path = old_kernel_path / "connection.json"
        
        if metadata_path.exists():
            shutil.copy(metadata_path, new_kernel_path / "metadata.json")
        
        if connection_path.exists():
            shutil.copy(connection_path, new_kernel_path / "connection.json")
        
        # Copy workspace content
        old_workspace = old_kernel_path / "workspace"
        new_workspace = new_kernel_path / "workspace"
        
        if old_workspace.exists() and old_workspace.is_dir():
            for item in old_workspace.glob("*"):
                if item.is_file():
                    shutil.copy(item, new_workspace / item.name)
                elif item.is_dir():
                    shutil.copytree(item, new_workspace / item.name)
    
    def _migrate_registries(self) -> None:
        """Migrate registry files."""
        # Copy session registry
        old_session_registry = self.old_base_dir / "registry" / "sessions.json"
        new_session_registry = self.new_base_dir / "registry" / "sessions.json"
        
        if old_session_registry.exists():
            shutil.copy(old_session_registry, new_session_registry)
        else:
            with open(new_session_registry, "w") as f:
                json.dump({}, f)
        
        # Copy kernel registry
        old_kernel_registry = self.old_base_dir / "registry" / "kernels.json"
        new_kernel_registry = self.new_base_dir / "registry" / "kernels.json"
        
        if old_kernel_registry.exists():
            shutil.copy(old_kernel_registry, new_kernel_registry)
        else:
            with open(new_kernel_registry, "w") as f:
                json.dump({}, f)
    
    def _migrate_symlinks(self) -> None:
        """Migrate symlinks."""
        old_by_name = self.old_base_dir / "by-name"
        new_by_name = self.new_base_dir / "by-name"
        
        if not old_by_name.exists():
            return
        
        # Process each named session
        for session_link in old_by_name.glob("*"):
            if not session_link.is_dir():
                continue
            
            session_name = session_link.name
            new_session_link = new_by_name / session_name
            new_session_link.mkdir(exist_ok=True)
            
            # Read session registry to find session ID
            registry_path = self.new_base_dir / "registry" / "sessions.json"
            try:
                with open(registry_path, "r") as f:
                    registry = json.load(f)
            except Exception:
                registry = {}
            
            session_id = registry.get(session_name)
            if not session_id:
                continue
            
            # Process each kernel link
            for kernel_link in session_link.glob("*"):
                if not kernel_link.is_symlink():
                    continue
                
                kernel_name = kernel_link.name
                
                # Find target in new structure
                try:
                    target = kernel_link.resolve()
                    relative_path = target.relative_to(self.old_base_dir)
                    new_target = self.new_base_dir / relative_path
                    
                    # Create new symlink
                    new_kernel_link = new_session_link / kernel_name
                    if new_kernel_link.exists():
                        new_kernel_link.unlink()
                    
                    os.symlink(
                        os.path.relpath(new_target, new_kernel_link.parent),
                        new_kernel_link,
                        target_is_directory=True
                    )
                except Exception as e:
                    logger.error(f"Error creating symlink for {kernel_name}: {e}")
```

#### Task 7.2: Implement Parallel Running (4 days)
Create a mechanism to run both old and new architectures side by side.

**Implementation Details:**
```python
# src/DevAgent/interpreter/compat.py
import os
from pathlib import Path
from typing import Dict, Any, Optional, Union

from .application.facade import InterpreterFacade
from .. import api

class DualModeInterpreter:
    """
    Compatibility layer that can operate in both old and new mode.
    This allows for a gradual migration from the old architecture to the new DDD architecture.
    """
    
    def __init__(self, base_dir: Path, use_ddd: bool = True):
        self.base_dir = base_dir
        self.use_ddd = use_ddd
        
        # Flag file to control mode
        self.flag_file = base_dir / ".use_ddd"
        
        # Initialize based on flag file or parameter
        if self.flag_file.exists():
            self.use_ddd = True
        elif use_ddd:
            # Create flag file
            self.flag_file.touch()
        
        # Initialize appropriate implementation
        if self.use_ddd:
            # Initialize DDD-based implementation
            self.ddd_interpreter = self._create_ddd_interpreter()
            self.legacy_interpreter = None
        else:
            # Initialize legacy implementation
            self.legacy_interpreter = api.InterpreterAPI(base_dir)
            self.ddd_interpreter = None
    
    def _create_ddd_interpreter(self) -> InterpreterFacade:
        """Create the DDD-based interpreter with all dependencies."""
        # This would create the complete DDD object graph
        # with all required dependencies (similar to what we
        # did in __main__.py)
        # ...
        return facade
    
    def set_mode(self, use_ddd: bool) -> None:
        """Change the operating mode."""
        if use_ddd == self.use_ddd:
            return
        
        # Update mode
        self.use_ddd = use_ddd
        
        # Update flag file
        if use_ddd:
            self.flag_file.touch()
        elif self.flag_file.exists():
            self.flag_file.unlink()
        
        # Reinitialize
        if use_ddd:
            # Initialize DDD-based implementation
            self.ddd_interpreter = self._create_ddd_interpreter()
            self.legacy_interpreter = None
        else:
            # Initialize legacy implementation
            self.legacy_interpreter = api.InterpreterAPI(self.base_dir)
            self.ddd_interpreter = None
    
    # Delegate methods to appropriate implementation
    def create_session(self, name: str) -> Dict[str, Any]:
        """Create a new session."""
        if self.use_ddd:
            return self.ddd_interpreter.create_session(name)
        else:
            try:
                session = self.legacy_interpreter.create_session(name)
                return {
                    "success": True,
                    "session_id": session.id,
                    "error": None
                }
            except Exception as e:
                return {
                    "success": False,
                    "session_id": None,
                    "error": str(e)
                }
    
    def get_session(self, reference: str) -> Dict[str, Any]:
        """Get a session by reference."""
        if self.use_ddd:
            return self.ddd_interpreter.get_session(reference)
        else:
            try:
                session = self.legacy_interpreter.get_session(reference)
                if not session:
                    return {
                        "success": False,
                        "session": None,
                        "error": f"Session not found: {reference}"
                    }
                
                return {
                    "success": True,
                    "session": {
                        "id": session.id,
                        "name": session.name,
                        "path": str(session.path)
                    },
                    "error": None
                }
            except Exception as e:
                return {
                    "success": False,
                    "session": None,
                    "error": str(e)
                }
    
    # Additional methods for other operations...
```

#### Task 7.3: Implement Documentation and Guides (5 days)
Create documentation and guides for the new architecture.

**Implementation Details:**
```
# docs/DDDArchitecture.md

# DevAgent Interpreter DDD Architecture

## Overview

The DevAgent Interpreter has been refactored to follow Domain-Driven Design principles, providing a more robust, maintainable, and extensible architecture. This document describes the new architecture, its components, and how they interact.

## Core Concepts

### Ubiquitous Language

The DDD architecture establishes a shared language for the domain:

- **Session**: A persistent computational environment containing multiple kernels
- **Kernel**: An executable process that interprets and runs code
- **Workspace**: A directory where a kernel operates, aligned with project structure
- **Reference**: An identifier (by name or ID) pointing to a computational resource
- **Execution**: The process of running code in a kernel and capturing results

### Bounded Contexts

The system is divided into four primary bounded contexts:

1. **Session Management Context**: Manages the lifecycle of computational sessions
2. **Kernel Execution Context**: Manages kernel processes and code execution
3. **Reference Resolution Context**: Translates various reference forms to concrete resources
4. **Persistence Context**: Handles durable storage and recovery of system state

## Architecture Layers

### Domain Layer

The domain layer contains the core domain model and business logic:

- **Value Objects**: Immutable objects representing domain concepts (SessionId, KernelId, Reference)
- **Entities**: Objects with identity and lifecycle (Kernel)
- **Aggregates**: Clusters of entities and value objects with consistency boundaries (Session)
- **Domain Services**: Stateless operations that don't belong to a specific entity (ReferenceResolutionService)
- **Domain Events**: Notifications of significant state changes (SessionCreated, KernelStarted)

### Application Layer

The application layer orchestrates domain objects to fulfill use cases:

- **Application Services**: Coordinate domain objects and provide a facade to the domain
- **DTOs**: Data transfer objects for communicating with external systems
- **Command Handlers**: Process commands from the user interface

### Infrastructure Layer

The infrastructure layer provides implementations for interfaces defined in the domain layer:

- **Repositories**: Store and retrieve domain objects
- **Persistence**: Handle data storage and retrieval
- **External Services**: Integrate with external systems

### Presentation Layer

The presentation layer handles user interaction:

- **API**: Exposes functionality to external systems
- **CLI**: Command-line interface for user interaction

## Key Components

### Domain Model

- **Session**: Aggregate root representing a computational environment
- **Kernel**: Entity representing a computational kernel
- **Reference**: Value object representing a reference to a computational resource
- **ExecutionResult**: Value object representing the result of code execution

### Domain Services

- **ReferenceResolutionService**: Resolves references to domain objects
- **ExecutionService**: Executes code in kernels
- **KernelLifecycleService**: Manages kernel lifecycle operations

### Application Services

- **InterpreterApplicationService**: Coordinates domain operations
- **InterpreterFacade**: Provides a simple interface to external systems

### Infrastructure Services

- **FileSystemManager**: Manages filesystem operations
- **EventBus**: Handles domain event publishing and subscription
- **FileSystemSessionRepository**: Persists sessions to the filesystem
- **FileSystemKernelRepository**: Persists kernels to the filesystem

## Usage Examples

### Creating a Session

```python
# Using the facade
result = interpreter_facade.create_session("my_session")
if result["success"]:
    session_id = result["session_id"]
    print(f"Created session: {session_id}")
else:
    print(f"Failed to create session: {result['error']}")
```

### Executing Code

```python
# Using the facade
result = interpreter_facade.execute_code("my_session/my_kernel", "print('hello world')")
if result["success"]:
    print(f"Output: {result['stdout']}")
else:
    print(f"Error: {result['error']}")
```

## Migration Guide

To migrate from the old architecture to the new DDD architecture:

1. Use the `DataMigrator` to convert existing data:
   ```python
   migrator = DataMigrator(old_base_dir, new_base_dir)
   success = migrator.migrate()
   ```

2. Use the compatibility layer during transition:
   ```python
   interpreter = DualModeInterpreter(base_dir)
   # Use new architecture
   interpreter.set_mode(True)
   ```

3. Update client code to use the new facade interface.

## Additional Resources

- [Domain-Driven Design](https://dddcommunity.org/)
- [Hierarchical Domain Design](docs/HierarchicalDomainDesign.md)
- [Agent Interpreter Architecture](docs/AgentInterpreterArchitecture.md)
```

## 5. References and Further Information

### Domain-Driven Design Resources

- **Evans, Eric.** "Domain-Driven Design: Tackling Complexity in the Heart of Software" - The seminal book on DDD concepts.
- **Vernon, Vaughn.** "Implementing Domain-Driven Design" - Practical guidance on applying DDD.
- **Fowler, Martin.** "Patterns of Enterprise Application Architecture" - Complementary design patterns.

### Python DDD Resources

- **Python DDD Example**: [GitHub - iktakahiro/dddpy](https://github.com/iktakahiro/dddpy)
- **Python Clean Architecture**: [GitHub - pcah/python-clean-architecture](https://github.com/pcah/python-clean-architecture)

### Additional Project Context

- This refactoring follows the principles outlined in the Hierarchical Domain Design (HDD) document, which emphasizes semantic fidelity, layered descent, and structural traceability.
- The Agent Interpreter Architecture document provides the conceptual foundation for the interpreter as a computational bridge.
- The changes are aligned with the broader Agentic Developer architecture, ensuring that the interpreter effectively serves its role in the larger system.

### Implementation Considerations

- **Backward Compatibility**: The migration strategy includes both data migration and a compatibility layer to ensure a smooth transition.
- **Testing Strategy**: The testing approach covers all layers of the architecture, from unit tests of the domain model to system tests of the complete interpreter.
- **Performance Implications**: The DDD architecture introduces additional layers of abstraction, which may have a minor impact on performance. However, the improvements in maintainability and extensibility outweigh this cost.
- **Future Extensions**: The new architecture is designed to accommodate future extensions, such as additional kernel types, more sophisticated reference resolution, and integration with other components of the Agentic Developer system.