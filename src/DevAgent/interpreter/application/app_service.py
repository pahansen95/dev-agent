from typing import List, Optional, Dict, Any
import logging
from pathlib import Path

from ..domain.repositories import SessionRepository, KernelRepository
from ..domain.services import ReferenceResolutionService, ExecutionService, KernelLifecycleService
from ..domain.factories import SessionFactory, KernelFactory
from ..domain.value_objects import SessionId, KernelId, ExecutionResult
from ..domain.exceptions import SessionError, KernelError, ReferenceResolutionError
from ..domain.model import Session, Kernel
from .dtos import SessionDTO, KernelDTO, ExecutionResultDTO
from .dtos import SessionResponseDTO, SessionListResponseDTO, KernelResponseDTO, KernelListResponseDTO, ExecutionResponseDTO

logger = logging.getLogger(__name__)

class InterpreterApplicationService:

  """Main application service for the interpreter."""

  def __init__(
      self, session_repo: SessionRepository, kernel_repo: KernelRepository, session_factory: SessionFactory, kernel_factory: KernelFactory,
      reference_service: ReferenceResolutionService, execution_service: ExecutionService, kernel_lifecycle_service: KernelLifecycleService, fs_manager):
    """
        Initialize the application service.
        
        Args:
            session_repo: The session repository
            kernel_repo: The kernel repository
            session_factory: The session factory
            kernel_factory: The kernel factory
            reference_service: The reference resolution service
            execution_service: The execution service
            kernel_lifecycle_service: The kernel lifecycle service
            fs_manager: The filesystem manager
        """
    self.session_repo = session_repo
    self.kernel_repo = kernel_repo
    self.session_factory = session_factory
    self.kernel_factory = kernel_factory
    self.reference_service = reference_service
    self.execution_service = execution_service
    self.kernel_lifecycle_service = kernel_lifecycle_service
    self.fs_manager = fs_manager

  def create_session(self, name: str) -> SessionResponseDTO:
    """
        Create a new session.
        
        Args:
            name: The session name
            
        Returns:
            A response DTO containing the session ID if successful
        """
    try:
      session = self.session_factory.create_session(name)
      return SessionResponseDTO(success=True, session_id=str(session.id))
    except SessionError as e:
      logger.error(f"Failed to create session: {e}")
      return SessionResponseDTO(success=False, error=str(e))
    except Exception as e:
      logger.exception(f"Unexpected error creating session: {e}")
      return SessionResponseDTO(success=False, error=f"Unexpected error: {str(e)}")

  def get_session(self, reference: str) -> SessionResponseDTO:
    """
        Get a session by reference.
        
        Args:
            reference: The session reference (name or ID)
            
        Returns:
            A response DTO containing the session if found
        """
    try:
      session = self.reference_service.resolve_to_session(reference)
      if not session:
        return SessionResponseDTO(success=False, error=f"Session not found: {reference}")

      session_dto = self._create_session_dto(session)
      return SessionResponseDTO(success=True, session=session_dto)
    except Exception as e:
      logger.exception(f"Unexpected error getting session: {e}")
      return SessionResponseDTO(success=False, error=f"Unexpected error: {str(e)}")

  def list_sessions(self) -> SessionListResponseDTO:
    """
        List all sessions.
        
        Returns:
            A response DTO containing all sessions
        """
    try:
      sessions = self.session_repo.list_all()
      session_dtos = [self._create_session_dto(session) for session in sessions]
      return SessionListResponseDTO(success=True, sessions=session_dtos)
    except Exception as e:
      logger.exception(f"Unexpected error listing sessions: {e}")
      return SessionListResponseDTO(success=False, error=f"Unexpected error: {str(e)}")

  def delete_session(self, reference: str) -> SessionResponseDTO:
    """
        Delete a session.
        
        Args:
            reference: The session reference (name or ID)
            
        Returns:
            A response DTO indicating success or failure
        """
    try:
      session = self.reference_service.resolve_to_session(reference)
      if not session:
        return SessionResponseDTO(success=False, error=f"Session not found: {reference}")

      success = self.session_repo.delete(session.id)
      return SessionResponseDTO(success=success, error=None if success else "Failed to delete session")
    except Exception as e:
      logger.exception(f"Unexpected error deleting session: {e}")
      return SessionResponseDTO(success=False, error=f"Unexpected error: {str(e)}")

  def create_kernel(self, session_reference: str, kernel_name: str, kernel_type: str = "python3") -> KernelResponseDTO:
    """
        Create a new kernel in a session.
        
        Args:
            session_reference: The session reference (name or ID)
            kernel_name: The kernel name
            kernel_type: The kernel type (default: "python3")
            
        Returns:
            A response DTO containing the kernel ID if successful
        """
    try:
      session = self.reference_service.resolve_to_session(session_reference)
      if not session:
        return KernelResponseDTO(success=False, error=f"Session not found: {session_reference}")

      kernel = self.kernel_factory.create_kernel(session, kernel_name, kernel_type)

      # Start the kernel
      self.kernel_lifecycle_service.start_kernel(kernel)

      return KernelResponseDTO(success=True, kernel_id=str(kernel.id))
    except KernelError as e:
      logger.error(f"Failed to create kernel: {e}")
      return KernelResponseDTO(success=False, error=str(e))
    except Exception as e:
      logger.exception(f"Unexpected error creating kernel: {e}")
      return KernelResponseDTO(success=False, error=f"Unexpected error: {str(e)}")

  def get_kernel(self, reference: str) -> KernelResponseDTO:
    """
        Get a kernel by reference.
        
        Args:
            reference: The kernel reference
            
        Returns:
            A response DTO containing the kernel if found
        """
    try:
      kernel = self.reference_service.resolve_to_kernel(reference)
      if not kernel:
        return KernelResponseDTO(success=False, error=f"Kernel not found: {reference}")

      kernel_dto = self._create_kernel_dto(kernel)
      return KernelResponseDTO(success=True, kernel=kernel_dto)
    except Exception as e:
      logger.exception(f"Unexpected error getting kernel: {e}")
      return KernelResponseDTO(success=False, error=f"Unexpected error: {str(e)}")

  def list_kernels(self, session_reference: str) -> KernelListResponseDTO:
    """
        List all kernels in a session.
        
        Args:
            session_reference: The session reference (name or ID)
            
        Returns:
            A response DTO containing all kernels in the session
        """
    try:
      session = self.reference_service.resolve_to_session(session_reference)
      if not session:
        return KernelListResponseDTO(success=False, error=f"Session not found: {session_reference}")

      kernels = self.kernel_repo.find_by_session_id(session.id)
      kernel_dtos = [self._create_kernel_dto(kernel) for kernel in kernels]
      return KernelListResponseDTO(success=True, kernels=kernel_dtos)
    except Exception as e:
      logger.exception(f"Unexpected error listing kernels: {e}")
      return KernelListResponseDTO(success=False, error=f"Unexpected error: {str(e)}")

  def delete_kernel(self, reference: str) -> KernelResponseDTO:
    """
        Delete a kernel.
        
        Args:
            reference: The kernel reference
            
        Returns:
            A response DTO indicating success or failure
        """
    try:
      kernel = self.reference_service.resolve_to_kernel(reference)
      if not kernel:
        return KernelResponseDTO(success=False, error=f"Kernel not found: {reference}")

      # Shutdown the kernel if it's alive
      if kernel.is_alive:
        self.kernel_lifecycle_service.shutdown_kernel(kernel)

      success = self.kernel_repo.delete(kernel.id)
      return KernelResponseDTO(success=success, error=None if success else "Failed to delete kernel")
    except Exception as e:
      logger.exception(f"Unexpected error deleting kernel: {e}")
      return KernelResponseDTO(success=False, error=f"Unexpected error: {str(e)}")

  def execute_code(self, reference: str, code: str) -> ExecutionResponseDTO:
    """
        Execute code in a kernel.
        
        Args:
            reference: The kernel reference
            code: The code to execute
            
        Returns:
            A response DTO containing the execution result
        """
    try:
      kernel = self.reference_service.resolve_to_kernel(reference)
      if not kernel:
        return ExecutionResponseDTO(success=False, error=f"Kernel not found: {reference}")

      result = self.execution_service.execute_code(kernel, code)
      result_dto = ExecutionResultDTO(
        success=result.success, stdout=result.stdout, error=result.error, outputs=result.outputs, execution_time=result.execution_time)

      return ExecutionResponseDTO(success=True, result=result_dto)
    except KernelError as e:
      logger.error(f"Failed to execute code: {e}")
      return ExecutionResponseDTO(success=False, error=str(e))
    except Exception as e:
      logger.exception(f"Unexpected error executing code: {e}")
      return ExecutionResponseDTO(success=False, error=f"Unexpected error: {str(e)}")

  def restart_kernel(self, reference: str) -> KernelResponseDTO:
    """
        Restart a kernel.
        
        Args:
            reference: The kernel reference
            
        Returns:
            A response DTO indicating success or failure
        """
    try:
      kernel = self.reference_service.resolve_to_kernel(reference)
      if not kernel:
        return KernelResponseDTO(success=False, error=f"Kernel not found: {reference}")

      success = self.kernel_lifecycle_service.restart_kernel(kernel)
      return KernelResponseDTO(success=success, error=None if success else "Failed to restart kernel")
    except KernelError as e:
      logger.error(f"Failed to restart kernel: {e}")
      return KernelResponseDTO(success=False, error=str(e))
    except Exception as e:
      logger.exception(f"Unexpected error restarting kernel: {e}")
      return KernelResponseDTO(success=False, error=f"Unexpected error: {str(e)}")

  def interrupt_kernel(self, reference: str) -> KernelResponseDTO:
    """
        Interrupt a kernel's execution.
        
        Args:
            reference: The kernel reference
            
        Returns:
            A response DTO indicating success or failure
        """
    try:
      kernel = self.reference_service.resolve_to_kernel(reference)
      if not kernel:
        return KernelResponseDTO(success=False, error=f"Kernel not found: {reference}")

      success = self.kernel_lifecycle_service.interrupt_kernel(kernel)
      return KernelResponseDTO(success=success, error=None if success else "Failed to interrupt kernel")
    except KernelError as e:
      logger.error(f"Failed to interrupt kernel: {e}")
      return KernelResponseDTO(success=False, error=str(e))
    except Exception as e:
      logger.exception(f"Unexpected error interrupting kernel: {e}")
      return KernelResponseDTO(success=False, error=f"Unexpected error: {str(e)}")

  def _create_session_dto(self, session: Session) -> SessionDTO:
    """
        Create a SessionDTO from a Session entity.
        
        Args:
            session: The session entity
            
        Returns:
            A SessionDTO
        """
    session_path = self.fs_manager.get_session_path(str(session.id))
    kernels = self.kernel_repo.find_by_session_id(session.id)

    return SessionDTO(
      id=str(session.id),
      name=session.name,
      created_at=session.created_at,
      last_activity=session.last_activity,
      kernel_count=len(kernels),
      path=str(session_path))

  def _create_kernel_dto(self, kernel: Kernel) -> KernelDTO:
    """
        Create a KernelDTO from a Kernel entity.
        
        Args:
            kernel: The kernel entity
            
        Returns:
            A KernelDTO
        """
    session_path = self.fs_manager.get_session_path(str(kernel.session_id))
    kernel_path = self.fs_manager.get_kernel_path(session_path, str(kernel.id))

    # Find session name
    session = self.session_repo.find_by_id(kernel.session_id)
    session_name = session.name if session else str(kernel.session_id)

    return KernelDTO(
      id=str(kernel.id),
      name=kernel.name,
      kernel_type=kernel.kernel_type,
      session_id=str(kernel.session_id),
      session_name=session_name,
      is_alive=kernel.is_alive,
      created_at=kernel.created_at,
      last_activity=kernel.last_activity,
      path=str(kernel_path))
