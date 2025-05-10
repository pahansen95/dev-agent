from typing import Dict, List, Optional, Any
import logging

from .app_service import InterpreterApplicationService
from ..domain.exceptions import DomainError, SessionError, KernelError
from ..domain.value_objects import ExecutionResult

logger = logging.getLogger(__name__)

class InterpreterFacade:

  """
    Public facade for the interpreter system.
    This is the main entry point for external clients.
    """

  def __init__(self, app_service: InterpreterApplicationService):
    """
        Initialize the facade.
        
        Args:
            app_service: The application service
        """
    self.app_service = app_service

  def create_session(self, name: str) -> Dict[str, Any]:
    """
        Create a new session.
        
        Args:
            name: The session name
            
        Returns:
            A dictionary with the session ID if successful
        """
    response = self.app_service.create_session(name)
    if response.success:
      return {"success": True, "session_id": response.session_id, "error": None}
    else:
      return {"success": False, "session_id": None, "error": response.error}

  def get_session(self, reference: str) -> Dict[str, Any]:
    """
        Get a session by reference.
        
        Args:
            reference: The session reference (name or ID)
            
        Returns:
            A dictionary with the session if found
        """
    response = self.app_service.get_session(reference)
    if response.success and response.session:
      return {"success": True, "session": response.session.__dict__, "error": None}
    else:
      return {"success": False, "session": None, "error": response.error}

  def list_sessions(self) -> Dict[str, Any]:
    """
        List all sessions.
        
        Returns:
            A dictionary with all sessions
        """
    response = self.app_service.list_sessions()
    if response.success:
      return {"success": True, "sessions": [s.__dict__ for s in response.sessions], "error": None}
    else:
      return {"success": False, "sessions": [], "error": response.error}

  def delete_session(self, reference: str) -> Dict[str, Any]:
    """
        Delete a session.
        
        Args:
            reference: The session reference (name or ID)
            
        Returns:
            A dictionary indicating success or failure
        """
    response = self.app_service.delete_session(reference)
    return {"success": response.success, "error": response.error}

  def create_kernel(self, session_reference: str, kernel_name: str, kernel_type: str = "python3") -> Dict[str, Any]:
    """
        Create a new kernel in a session.
        
        Args:
            session_reference: The session reference (name or ID)
            kernel_name: The kernel name
            kernel_type: The kernel type (default: "python3")
            
        Returns:
            A dictionary with the kernel ID if successful
        """
    response = self.app_service.create_kernel(session_reference, kernel_name, kernel_type)
    if response.success:
      return {"success": True, "kernel_id": response.kernel_id, "error": None}
    else:
      return {"success": False, "kernel_id": None, "error": response.error}

  def get_kernel(self, reference: str) -> Dict[str, Any]:
    """
        Get a kernel by reference.
        
        Args:
            reference: The kernel reference
            
        Returns:
            A dictionary with the kernel if found
        """
    response = self.app_service.get_kernel(reference)
    if response.success and response.kernel:
      return {"success": True, "kernel": response.kernel.__dict__, "error": None}
    else:
      return {"success": False, "kernel": None, "error": response.error}

  def list_kernels(self, session_reference: str) -> Dict[str, Any]:
    """
        List all kernels in a session.
        
        Args:
            session_reference: The session reference (name or ID)
            
        Returns:
            A dictionary with all kernels in the session
        """
    response = self.app_service.list_kernels(session_reference)
    if response.success:
      return {"success": True, "kernels": [k.__dict__ for k in response.kernels], "error": None}
    else:
      return {"success": False, "kernels": [], "error": response.error}

  def delete_kernel(self, reference: str) -> Dict[str, Any]:
    """
        Delete a kernel.
        
        Args:
            reference: The kernel reference
            
        Returns:
            A dictionary indicating success or failure
        """
    response = self.app_service.delete_kernel(reference)
    return {"success": response.success, "error": response.error}

  def execute_code(self, reference: str, code: str) -> Dict[str, Any]:
    """
        Execute code in a kernel.
        
        Args:
            reference: The kernel reference
            code: The code to execute
            
        Returns:
            A dictionary with the execution result
        """
    response = self.app_service.execute_code(reference, code)
    if response.success and response.result:
      return {
        "success": response.result.success,
        "stdout": response.result.stdout,
        "error": response.result.error,
        "outputs": response.result.outputs,
        "execution_time": response.result.execution_time
      }
    else:
      return {"success": False, "stdout": "", "error": response.error, "outputs": [], "execution_time": 0.0}

  def restart_kernel(self, reference: str) -> Dict[str, Any]:
    """
        Restart a kernel.
        
        Args:
            reference: The kernel reference
            
        Returns:
            A dictionary indicating success or failure
        """
    response = self.app_service.restart_kernel(reference)
    return {"success": response.success, "error": response.error}

  def interrupt_kernel(self, reference: str) -> Dict[str, Any]:
    """
        Interrupt a kernel's execution.
        
        Args:
            reference: The kernel reference
            
        Returns:
            A dictionary indicating success or failure
        """
    response = self.app_service.interrupt_kernel(reference)
    return {"success": response.success, "error": response.error}
