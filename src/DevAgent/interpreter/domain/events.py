from dataclasses import dataclass, field
import time
from typing import Protocol, Any, Dict, Optional
from .value_objects import SessionId, KernelId, KernelStatus

class DomainEvent(Protocol):

  """Interface for all domain events."""
  timestamp: float

# Session Events

@dataclass(frozen=True)
class SessionCreated:

  """Event raised when a new session is created."""
  session_id: SessionId
  name: str
  timestamp: float = field(default_factory=time.time)

@dataclass(frozen=True)
class SessionDeleted:

  """Event raised when a session is deleted."""
  session_id: SessionId
  timestamp: float = field(default_factory=time.time)

# Kernel Lifecycle Events

@dataclass(frozen=True)
class KernelCreated:

  """Event raised when a new kernel is created."""
  kernel_id: KernelId
  session_id: SessionId
  kernel_type: str
  name: str
  timestamp: float = field(default_factory=time.time)

@dataclass(frozen=True)
class KernelStarted:

  """Event raised when a kernel is started."""
  kernel_id: KernelId
  session_id: SessionId
  process_id: Optional[int] = None
  connection_file: Optional[str] = None
  timestamp: float = field(default_factory=time.time)

@dataclass(frozen=True)
class KernelShutdown:

  """Event raised when a kernel is shut down."""
  kernel_id: KernelId
  session_id: SessionId
  timestamp: float = field(default_factory=time.time)

@dataclass(frozen=True)
class KernelInterrupted:

  """Event raised when a kernel execution is interrupted."""
  kernel_id: KernelId
  session_id: SessionId
  timestamp: float = field(default_factory=time.time)

@dataclass(frozen=True)
class KernelRestarted:

  """Event raised when a kernel is restarted."""
  kernel_id: KernelId
  session_id: SessionId
  process_id: Optional[int] = None
  connection_file: Optional[str] = None
  timestamp: float = field(default_factory=time.time)

# Kernel Execution Events

@dataclass(frozen=True)
class CodeExecuted:

  """Event raised when code is executed in a kernel."""
  kernel_id: KernelId
  session_id: SessionId
  success: bool
  execution_time: float
  timestamp: float = field(default_factory=time.time)

# Dual-State Model Events

@dataclass(frozen=True)
class KernelDesiredStateChanged:

  """Event raised when the desired state of a kernel changes."""
  kernel_id: KernelId
  session_id: SessionId
  previous_state: KernelStatus
  desired_state: KernelStatus
  timestamp: float = field(default_factory=time.time)

@dataclass(frozen=True)
class KernelActualStateChanged:

  """Event raised when the actual state of a kernel changes."""
  kernel_id: KernelId
  session_id: SessionId
  previous_state: KernelStatus
  actual_state: KernelStatus
  process_id: Optional[int] = None
  connection_file: Optional[str] = None
  health_metrics: Optional[Dict[str, Any]] = None
  timestamp: float = field(default_factory=time.time)

@dataclass(frozen=True)
class KernelStateReconciled:

  """Event raised when the kernel's actual state is reconciled with desired state."""
  kernel_id: KernelId
  session_id: SessionId
  state: KernelStatus
  process_id: Optional[int] = None
  connection_file: Optional[str] = None
  timestamp: float = field(default_factory=time.time)

@dataclass(frozen=True)
class KernelHealthChecked:

  """Event raised when a kernel's health is checked."""
  kernel_id: KernelId
  session_id: SessionId
  is_healthy: bool
  metrics: Dict[str, Any]
  process_id: Optional[int] = None
  timestamp: float = field(default_factory=time.time)

# Runtime State Management Events

@dataclass(frozen=True)
class KernelProcessStarted:

  """Event raised when a kernel process is started."""
  kernel_id: KernelId
  session_id: SessionId
  process_id: int
  connection_file: str
  jupyter_kernel_id: str
  timestamp: float = field(default_factory=time.time)

@dataclass(frozen=True)
class KernelProcessExited:

  """Event raised when a kernel process exits."""
  kernel_id: KernelId
  session_id: SessionId
  process_id: int
  exit_code: Optional[int] = None
  error_message: Optional[str] = None
  timestamp: float = field(default_factory=time.time)

@dataclass(frozen=True)
class KernelProcessDetached:

  """Event raised when a kernel process is detached from its parent."""
  kernel_id: KernelId
  session_id: SessionId
  process_id: int
  timestamp: float = field(default_factory=time.time)

@dataclass(frozen=True)
class KernelReconnected:

  """Event raised when an existing kernel process is reconnected to."""
  kernel_id: KernelId
  session_id: SessionId
  process_id: int
  connection_file: str
  timestamp: float = field(default_factory=time.time)
