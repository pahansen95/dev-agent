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

class SessionAlreadyExistsError(SessionError):

  """Raised when attempting to create a session that already exists."""
  pass

class KernelNotFoundError(KernelError):

  """Raised when a kernel cannot be found."""
  pass

class KernelAlreadyExistsError(KernelError):

  """Raised when attempting to create a kernel that already exists."""
  pass

class KernelExecutionError(KernelError):

  """Raised when code execution in a kernel fails."""
  pass

class ReferenceResolutionError(DomainError):

  """Raised when a reference cannot be resolved."""
  pass

class InvalidReferenceError(ReferenceResolutionError):

  """Raised when a reference format is invalid."""
  pass
