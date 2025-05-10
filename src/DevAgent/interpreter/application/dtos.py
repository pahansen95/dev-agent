from dataclasses import dataclass, field
from typing import List, Optional, Any, Dict
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
  outputs: List[Any]
  execution_time: float

@dataclass
class ResponseDTO:

  """Base Data Transfer Object for API responses."""
  success: bool
  error: Optional[str] = None

@dataclass
class SessionResponseDTO(ResponseDTO):

  """Response DTO for session operations."""
  session: Optional[SessionDTO] = None
  session_id: Optional[str] = None

@dataclass
class SessionListResponseDTO(ResponseDTO):

  """Response DTO for listing sessions."""
  sessions: List[SessionDTO] = field(default_factory=list)

@dataclass
class KernelResponseDTO(ResponseDTO):

  """Response DTO for kernel operations."""
  kernel: Optional[KernelDTO] = None
  kernel_id: Optional[str] = None

@dataclass
class KernelListResponseDTO(ResponseDTO):

  """Response DTO for listing kernels."""
  kernels: List[KernelDTO] = field(default_factory=list)

@dataclass
class ExecutionResponseDTO(ResponseDTO):

  """Response DTO for code execution."""
  result: Optional[ExecutionResultDTO] = None
