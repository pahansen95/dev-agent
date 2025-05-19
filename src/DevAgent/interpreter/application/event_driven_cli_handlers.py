from typing import TextIO, Dict, Any, Callable, Optional
import logging
import sys
import time

from .event_driven_facade import EventDrivenInterpreterFacade

logger = logging.getLogger(__name__)

class EventDrivenSessionCommandHandler:

  """Handler for event-driven interpreter session CLI commands."""

  def __init__(self, interpreter_facade: EventDrivenInterpreterFacade, stdout: TextIO = sys.stdout):
    """
        Initialize the handler.
        
        Args:
            interpreter_facade: The event-driven interpreter facade
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
      return True
    else:
      self.stdout.write(f"Failed to get session: {result['error']}\n")
      return False

class EventDrivenKernelCommandHandler:

  """Handler for event-driven interpreter kernel CLI commands."""

  def __init__(self, interpreter_facade: EventDrivenInterpreterFacade, stdout: TextIO = sys.stdout):
    """
        Initialize the handler.
        
        Args:
            interpreter_facade: The event-driven interpreter facade
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
      self.stdout.write(f"Kernel is starting in the background and will persist across CLI invocations.\n")
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
          status_text = kernel["status"].upper()
          if kernel["is_reconciled"]:
            status_text += " (reconciled)"
          else:
            status_text += " (reconciling...)"

          self.stdout.write(f"  ID: {kernel['id']}, Name: {kernel['name']}, Type: {kernel['kernel_type']}\n")
          self.stdout.write(f"    Status: {status_text}, Desired: {kernel['desired_status'].upper()}\n")

          if kernel["process_id"]:
            self.stdout.write(f"    Process ID: {kernel['process_id']}\n")
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
    result = self.facade.kernel_status(reference)
    if result["success"]:
      kernel = result["kernel"]
      status_text = kernel["status"].upper()
      if kernel["is_reconciled"]:
        status_text += " (reconciled)"
      else:
        status_text += " (reconciling...)"

      self.stdout.write(f"Kernel ID: {kernel['id']}\n")
      self.stdout.write(f"Kernel Name: {kernel['name']}\n")
      self.stdout.write(f"Kernel Type: {kernel['kernel_type']}\n")
      self.stdout.write(f"Status: {status_text}\n")
      self.stdout.write(f"Desired Status: {kernel['desired_status'].upper()}\n")
      self.stdout.write(f"Session ID: {kernel['session_id']}\n")
      self.stdout.write(f"Session Name: {kernel['session_name']}\n")
      self.stdout.write(f"Created At: {kernel['created_at']}\n")
      self.stdout.write(f"Last Activity: {kernel['last_activity']}\n")

      if kernel["process_id"]:
        self.stdout.write(f"Process ID: {kernel['process_id']}\n")

      if "health_metrics" in kernel and kernel["health_metrics"]:
        self.stdout.write("Health Metrics:\n")
        for key, value in kernel["health_metrics"].items():
          self.stdout.write(f"  {key}: {value}\n")

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

    # Check kernel status first
    status_result = self.facade.kernel_status(reference)
    if not status_result["success"]:
      self.stdout.write(f"Failed to get kernel status: {status_result['error']}\n")
      return False

    kernel = status_result["kernel"]

    # If kernel is not running, ensure it's started
    if kernel["status"] != "running":
      if kernel["desired_status"] != "running":
        # Update desired status to running
        self.stdout.write(f"Requesting kernel start...\n")
        # Use the start handler to request kernel start
        self.handle_start(reference)
      else:
        self.stdout.write(f"Kernel is starting up, please wait...\n")

      # Wait for kernel to start
      max_attempts = 30 # More attempts for slow startup
      for i in range(max_attempts):
        status_result = self.facade.kernel_status(reference)
        if status_result["success"] and status_result["kernel"]["status"] == "running":
          self.stdout.write(f"Kernel is now running\n")
          break

        if i % 2 == 0: # Print dot every second (since sleep is 0.5)
          self.stdout.write(".")

        time.sleep(0.5)

        # If we've waited a long time, give more info
        if i == 15:
          self.stdout.write("\nStill waiting for kernel to start...\n")

      self.stdout.write("\n")

      # Final status check - if still not running, we'll try to execute anyway as the
      # execute_code method will attempt reconnection
      status_result = self.facade.kernel_status(reference)
      if status_result["success"] and status_result["kernel"]["status"] != "running":
        self.stdout.write(f"Warning: Kernel status is {status_result['kernel']['status']}. Attempting execution anyway...\n")

    # Execute code
    self.stdout.write(f"Executing code in kernel {reference}...\n")
    result = self.facade.execute_code(reference, code)

    if result["success"]:
      if result["stdout"]:
        self.stdout.write(result["stdout"])
        if not result["stdout"].endswith("\n"):
          self.stdout.write("\n")

      if result["outputs"]:
        for output in result["outputs"]:
          # Handle different output types
          output_type = output.get("type", "")
          if output_type == "stream":
            name = output.get("name", "")
            text = output.get("text", "")
            if name == "stderr":
              self.stdout.write(f"STDERR: {text}")
            else:
              self.stdout.write(text)
          elif output_type == "execute_result":
            data = output.get("data", {})
            if "text/plain" in data:
              self.stdout.write(data["text/plain"] + "\n")
            else:
              self.stdout.write("[Display data not shown in CLI]\n")
          elif output_type == "display_data":
            data = output.get("data", {})
            if "text/plain" in data:
              self.stdout.write(data["text/plain"] + "\n")
            else:
              self.stdout.write("[Display data not shown in CLI]\n")
          elif output_type == "error":
            ename = output.get("ename", "")
            evalue = output.get("evalue", "")
            traceback = output.get("traceback", [])

            if traceback:
              self.stdout.write("\n".join(traceback) + "\n")
            else:
              self.stdout.write(f"Error: {ename}: {evalue}\n")

      self.stdout.write(f"Execution completed in {result['execution_time']:.3f}s\n")

      # Update status to show it's definitely running now
      kernel_info = self.facade.get_kernel(reference)
      if kernel_info["success"]:
        kernel = kernel_info["kernel"]
        self.stdout.write(f"Kernel status: {kernel['status'].upper()}\n")

      return True
    else:
      if result["error"]:
        self.stdout.write(f"Execution failed: {result['error']}\n")

        # If execution failed, might need to restart the kernel
        if "not alive" in result["error"].lower() or "failed to start" in result["error"].lower():
          self.stdout.write(f"Attempting to restart the kernel...\n")
          if self.handle_restart(reference):
            self.stdout.write(f"Kernel restarted. Please try executing the code again.\n")
          else:
            self.stdout.write(f"Failed to restart the kernel. Try running 'start' command first.\n")

      return False

  def handle_restart(self, reference: str) -> bool:
    """
        Handle 'restart' command.
        
        Args:
            reference: The kernel reference
            
        Returns:
            True if successful, False otherwise
        """
    self.stdout.write(f"Restarting kernel {reference}...\n")
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

  def handle_start(self, reference: str) -> bool:
    """
        Handle 'start' command.

        Args:
            reference: The kernel reference

        Returns:
            True if successful, False otherwise
        """
    # First get kernel status
    status_result = self.facade.kernel_status(reference)
    if not status_result["success"]:
      self.stdout.write(f"Failed to get kernel status: {status_result['error']}\n")
      return False

    kernel = status_result["kernel"]
    if kernel["status"] == "running":
      self.stdout.write(f"Kernel is already running: {reference}\n")
      return True

    # Get kernel info
    kernel_info = self.facade.get_kernel(reference)
    if not kernel_info["success"]:
      self.stdout.write(f"Failed to get kernel: {kernel_info['error']}\n")
      return False

    # Update desired status if needed
    if kernel["desired_status"] != "running":
      # We need to update desired status through kernel façade
      self.stdout.write(f"Updating desired status to RUNNING...\n")
      # Execute a trivial command to set desired status
      self.facade.execute_code(reference, "")

    self.stdout.write(f"Starting kernel {reference}...\n")

    # Wait for kernel to start with progress indicators
    max_attempts = 30
    for i in range(max_attempts):
      status_result = self.facade.kernel_status(reference)

      if status_result["success"]:
        current_status = status_result["kernel"]["status"]
        if current_status == "running":
          self.stdout.write(f"\nKernel started successfully: {reference}\n")
          return True

        # Show status updates
        if i % 4 == 0: # Every 2 seconds
          self.stdout.write(f"\rCurrent status: {current_status.upper()}{'.' * (i % 4 + 1)}     ")

      time.sleep(0.5)

    # Execute a simple code to trigger actual kernel start if still not running
    self.stdout.write(f"\nExecuting simple code to initiate kernel...\n")
    result = self.facade.execute_code(reference, "1+1")

    # Final status check
    status_result = self.facade.kernel_status(reference)
    if status_result["success"] and status_result["kernel"]["status"] == "running":
      self.stdout.write(f"Kernel started: {reference}\n")
      return True
    else:
      self.stdout.write(f"Kernel start initiated in background. Run 'status {reference}' to check progress.\n")
      return True

  def handle_stop(self, reference: str) -> bool:
    """
        Handle 'stop' command.

        Args:
            reference: The kernel reference

        Returns:
            True if successful, False otherwise
        """
    # First get kernel
    kernel_info = self.facade.get_kernel(reference)
    if not kernel_info["success"]:
      self.stdout.write(f"Failed to get kernel: {kernel_info['error']}\n")
      return False

    kernel = kernel_info["kernel"]
    if kernel["status"] == "stopped":
      self.stdout.write(f"Kernel is already stopped: {reference}\n")
      return True

    # Update desired status to STOPPED
    self.stdout.write(f"Stopping kernel {reference}...\n")

    # First try graceful shutdown through the kernel
    try:
      # Try to execute shutdown command using code execution
      self.stdout.write(f"Attempting graceful shutdown...\n")
      shutdown_code = """import os
import signal
import sys

# Send SIGTERM to ourselves (more graceful than _exit)
os.kill(os.getpid(), signal.SIGTERM)
"""
      result = self.facade.execute_code(reference, shutdown_code)

      # If we got an error, the kernel might have already stopped
      if "error" in result and result["error"]:
        # Continue to check status
        pass
      else:
        # Wait briefly before forcing shutdown
        time.sleep(1.0)
    except Exception as e:
      self.stdout.write(f"Graceful shutdown attempt failed: {e}\n")

    # Now use the delete method which forces kernel shutdown
    self.stdout.write(f"Forcing kernel shutdown...\n")
    delete_result = self.facade.delete_kernel(reference)

    if delete_result["success"]:
      self.stdout.write(f"Kernel stopped: {reference}\n")
      return True
    else:
      # Wait a bit and check status again
      time.sleep(0.5)
      status_result = self.facade.kernel_status(reference)

      if not status_result["success"]:
        # Kernel might have been deleted altogether
        self.stdout.write(f"Kernel stopped and deleted: {reference}\n")
        return True
      elif status_result["kernel"]["status"] != "running":
        self.stdout.write(f"Kernel stopped: {reference}\n")
        return True
      else:
        self.stdout.write(f"Kernel stop initiated. Run 'status {reference}' to check progress.\n")

        # Try other shutdown methods as backup if we're still here
        try:
          # Try process termination via execute code
          self.facade.execute_code(reference, "import os; os._exit(0)")
        except:
          pass

        return True

  def handle_status(self, reference: str) -> bool:
    """
        Handle 'status' command.
        
        Args:
            reference: The kernel reference
            
        Returns:
            True if successful, False otherwise
        """
    return self.handle_get(reference)
