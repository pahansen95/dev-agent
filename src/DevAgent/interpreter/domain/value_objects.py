from dataclasses import dataclass, field
import uuid
from typing import Optional, Literal, List, Union
from pathlib import Path
import time
from enum import Enum

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

class KernelStatus(Enum):

  """Possible states for a kernel."""
  STARTING = "starting"
  RUNNING = "running"
  STOPPING = "stopping"
  STOPPED = "stopped"
  FAILED = "failed"

@dataclass(frozen=True)
class Reference:

  """Value object representing a reference to a computational resource."""
  type: Literal["session", "kernel"]
  name_component: Optional[str] = None
  id_component: Optional[str] = None
  path: Optional[Path] = None

  @classmethod
  def parse(cls, reference_string: str) -> 'Reference':
    """
        Parse a reference string into a Reference object.
        
        Formats supported:
        - "session_name" -> session by name
        - "sid-xxxxxxxx" -> session by ID
        - "session_name/kernel_name" -> kernel by name within session
        - "kid-xxxxxxxx" -> kernel by ID
        """
    # Session/Kernel format (e.g. "main/python")
    if "/" in reference_string:
      session_name, kernel_name = reference_string.split("/", 1)
      return cls(type="kernel", name_component=kernel_name, id_component=None, path=None)

    # Kernel ID format (e.g. "kid-12345678")
    if reference_string.startswith("kid-"):
      return cls(type="kernel", name_component=None, id_component=reference_string, path=None)

    # Session ID format (e.g. "sid-12345678")
    if reference_string.startswith("sid-"):
      return cls(type="session", name_component=None, id_component=reference_string, path=None)

    # Session name format (e.g. "main")
    return cls(type="session", name_component=reference_string, id_component=None, path=None)

@dataclass(frozen=True)
class ExecutionResult:

  """Value object representing the result of code execution."""
  success: bool
  stdout: str = ""
  error: Optional[str] = None
  outputs: List = field(default_factory=list)
  execution_time: float = 0.0
