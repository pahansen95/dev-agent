from typing import TextIO, Dict, Any, Callable, Optional
import logging
import sys

from .facade import InterpreterFacade

logger = logging.getLogger(__name__)

class InterpreterSessionCommandHandler:

  """Handler for interpreter session CLI commands."""

  def __init__(self, interpreter_facade: InterpreterFacade, stdout: TextIO = sys.stdout):
    """
        Initialize the handler.
        
        Args:
            interpreter_facade: The interpreter facade
            stdout: The output stream (default: sys.stdout)
        """
    self.facade = interpreter_facade
    self.stdout = stdout

  def handle_create(self, name: str) -> bool:
    """
        Handle 'create' command.
        
        Args:
            name: The session name
            
        Returns:
            True if successful, False otherwise
        """
    result = self.facade.create_session(name)
    if result["success"]:
      self.stdout.write(f"Session created: {name}\n")
      self.stdout.write(f"Session ID: {result['session_id']}\n")
      return True
    else:
      self.stdout.write(f"Failed to create session: {result['error']}\n")
      return False

  def handle_list(self) -> bool:
    """
        Handle 'list' command.
        
        Returns:
            True if successful, False otherwise
        """
    result = self.facade.list_sessions()
    if result["success"]:
      sessions = result["sessions"]
      if sessions:
        self.stdout.write("Active sessions:\n")
        for session in sessions:
          self.stdout.write(f"  ID: {session['id']}, Name: {session['name']}\n")
          self.stdout.write(f"    Kernels: {session['kernel_count']}\n")
          if "path" in session and session["path"]:
            self.stdout.write(f"    Path: {session['path']}\n")
      else:
        self.stdout.write("No active sessions\n")
      return True
    else:
      self.stdout.write(f"Failed to list sessions: {result['error']}\n")
      return False

  def handle_delete(self, reference: str) -> bool:
    """
        Handle 'delete' command.
        
        Args:
            reference: The session reference (name or ID)
            
        Returns:
            True if successful, False otherwise
        """
    result = self.facade.delete_session(reference)
    if result["success"]:
      self.stdout.write(f"Session deleted: {reference}\n")
      return True
    else:
      self.stdout.write(f"Failed to delete session: {result['error']}\n")
      return False

  def handle_get(self, reference: str) -> bool:
    """
        Handle 'get' command.
        
        Args:
            reference: The session reference (name or ID)
            
        Returns:
            True if successful, False otherwise
        """
    result = self.facade.get_session(reference)
    if result["success"]:
      session = result["session"]
      self.stdout.write(f"Session ID: {session['id']}\n")
      self.stdout.write(f"Session Name: {session['name']}\n")
      self.stdout.write(f"Created At: {session['created_at']}\n")
      self.stdout.write(f"Last Activity: {session['last_activity']}\n")
      self.stdout.write(f"Kernel Count: {session['kernel_count']}\n")
      if "path" in session and session["path"]:
        self.stdout.write(f"Path: {session['path']}\n")
      return True
    else:
      self.stdout.write(f"Failed to get session: {result['error']}\n")
      return False

class InterpreterKernelCommandHandler:

  """Handler for interpreter kernel CLI commands."""

  def __init__(self, interpreter_facade: InterpreterFacade, stdout: TextIO = sys.stdout):
    """
        Initialize the handler.
        
        Args:
            interpreter_facade: The interpreter facade
            stdout: The output stream (default: sys.stdout)
        """
    self.facade = interpreter_facade
    self.stdout = stdout

  def handle_create(self, session_ref: str, name: str, kernel_type: str) -> bool:
    """
        Handle 'create' command.
        
        Args:
            session_ref: The session reference (name or ID)
            name: The kernel name
            kernel_type: The kernel type
            
        Returns:
            True if successful, False otherwise
        """
    result = self.facade.create_kernel(session_ref, name, kernel_type)
    if result["success"]:
      self.stdout.write(f"Kernel created: {name}\n")
      self.stdout.write(f"Kernel ID: {result['kernel_id']}\n")
      self.stdout.write(f"Kernel Type: {kernel_type}\n")
      self.stdout.write(f"In Session: {session_ref}\n")
      return True
    else:
      self.stdout.write(f"Failed to create kernel: {result['error']}\n")
      return False

  def handle_list(self, session_ref: str) -> bool:
    """
        Handle 'list' command.
        
        Args:
            session_ref: The session reference (name or ID)
            
        Returns:
            True if successful, False otherwise
        """
    result = self.facade.list_kernels(session_ref)
    if result["success"]:
      kernels = result["kernels"]
      if kernels:
        self.stdout.write(f"Kernels in session {session_ref}:\n")
        for kernel in kernels:
          status = "ALIVE" if kernel["is_alive"] else "DEAD"
          self.stdout.write(f"  ID: {kernel['id']}, Name: {kernel['name']}, Type: {kernel['kernel_type']}, Status: {status}\n")
          if "path" in kernel and kernel["path"]:
            self.stdout.write(f"    Path: {kernel['path']}\n")
      else:
        self.stdout.write(f"No kernels in session {session_ref}\n")
      return True
    else:
      self.stdout.write(f"Failed to list kernels: {result['error']}\n")
      return False

  def handle_delete(self, reference: str) -> bool:
    """
        Handle 'delete' command.
        
        Args:
            reference: The kernel reference
            
        Returns:
            True if successful, False otherwise
        """
    result = self.facade.delete_kernel(reference)
    if result["success"]:
      self.stdout.write(f"Kernel deleted: {reference}\n")
      return True
    else:
      self.stdout.write(f"Failed to delete kernel: {result['error']}\n")
      return False

  def handle_get(self, reference: str) -> bool:
    """
        Handle 'get' command.
        
        Args:
            reference: The kernel reference
            
        Returns:
            True if successful, False otherwise
        """
    result = self.facade.get_kernel(reference)
    if result["success"]:
      kernel = result["kernel"]
      status = "ALIVE" if kernel["is_alive"] else "DEAD"
      self.stdout.write(f"Kernel ID: {kernel['id']}\n")
      self.stdout.write(f"Kernel Name: {kernel['name']}\n")
      self.stdout.write(f"Kernel Type: {kernel['kernel_type']}\n")
      self.stdout.write(f"Status: {status}\n")
      self.stdout.write(f"Session ID: {kernel['session_id']}\n")
      self.stdout.write(f"Session Name: {kernel['session_name']}\n")
      self.stdout.write(f"Created At: {kernel['created_at']}\n")
      self.stdout.write(f"Last Activity: {kernel['last_activity']}\n")
      if "path" in kernel and kernel["path"]:
        self.stdout.write(f"Path: {kernel['path']}\n")
      return True
    else:
      self.stdout.write(f"Failed to get kernel: {result['error']}\n")
      return False

  def handle_execute(self, reference: str, code: str, file: Optional[str] = None) -> bool:
    """
        Handle 'execute' command.
        
        Args:
            reference: The kernel reference
            code: The code to execute
            file: The file containing code to execute (overrides code if provided)
            
        Returns:
            True if successful, False otherwise
        """
    # Read from file if provided
    if file:
      try:
        with open(file, 'r') as f:
          code = f.read()
      except Exception as e:
        self.stdout.write(f"Failed to read code from file {file}: {e}\n")
        return False

    result = self.facade.execute_code(reference, code)
    if result["success"]:
      if result["stdout"]:
        self.stdout.write(result["stdout"])
        if not result["stdout"].endswith("\n"):
          self.stdout.write("\n")

      if result["outputs"]:
        for output in result["outputs"]:
          # Handle different output types
          output_type = output.get("output_type", "")
          if output_type == "stream":
            self.stdout.write(output.get("text", ""))
          elif output_type == "display_data":
            data = output.get("data", {})
            if "text/plain" in data:
              self.stdout.write(data["text/plain"] + "\n")
            else:
              self.stdout.write("[Display data not shown in CLI]\n")
          elif output_type == "error":
            self.stdout.write(f"Error: {output.get('ename', '')}: {output.get('evalue', '')}\n")

      self.stdout.write(f"Execution time: {result['execution_time']:.3f}s\n")
      return True
    else:
      if result["error"]:
        self.stdout.write(f"Failed to execute code: {result['error']}\n")
      return False

  def handle_restart(self, reference: str) -> bool:
    """
        Handle 'restart' command.
        
        Args:
            reference: The kernel reference
            
        Returns:
            True if successful, False otherwise
        """
    result = self.facade.restart_kernel(reference)
    if result["success"]:
      self.stdout.write(f"Kernel restarted: {reference}\n")
      return True
    else:
      self.stdout.write(f"Failed to restart kernel: {result['error']}\n")
      return False

  def handle_interrupt(self, reference: str) -> bool:
    """
        Handle 'interrupt' command.
        
        Args:
            reference: The kernel reference
            
        Returns:
            True if successful, False otherwise
        """
    result = self.facade.interrupt_kernel(reference)
    if result["success"]:
      self.stdout.write(f"Kernel interrupted: {reference}\n")
      return True
    else:
      self.stdout.write(f"Failed to interrupt kernel: {result['error']}\n")
      return False
