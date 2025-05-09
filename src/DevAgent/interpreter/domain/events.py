from dataclasses import dataclass, field
import time
from typing import Protocol, Any, Dict
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

@dataclass(frozen=True)
class KernelInterrupted:
    """Event raised when a kernel execution is interrupted."""
    kernel_id: KernelId
    timestamp: float = field(default_factory=time.time)

@dataclass(frozen=True)
class KernelRestarted:
    """Event raised when a kernel is restarted."""
    kernel_id: KernelId
    timestamp: float = field(default_factory=time.time)