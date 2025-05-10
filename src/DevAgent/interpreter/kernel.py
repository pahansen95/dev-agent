"""
Kernel controller for the DevAgent Interpreter.

This module provides the KernelController class which manages individual
kernel processes and handles direct communication with them, as well as the
ExecutionResult dataclass for standardized code execution outputs.

The KernelController uses the Jupyter Client API to manage kernels directly,
without requiring a Jupyter Server. It handles kernel lifecycle management,
code execution, output collection, and error handling.

Key features:
- Direct kernel process management (start, stop, restart, interrupt)
- Code execution with standardized result handling
- Output stream capturing (stdout, stderr)
- Rich output handling (execute results, display data)
- Error handling and reporting
- Connection state persistence
- Automatic reconnection to existing kernels
- Workspace directory management for kernel processes
"""

import os
import time
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from jupyter_client import KernelManager
from queue import Empty

logger = logging.getLogger(__name__)

@dataclass
class ExecutionResult:

  """Result of code execution in a kernel."""
  success: bool
  stdout: str = ""
  error: Optional[str] = None
  outputs: List[Dict[str, Any]] = field(default_factory=list)
  execution_time: float = 0.0

class KernelController:

  """Controls an individual kernel process."""

  def __init__(self, id: str, name: str, kernel_type: str, session_id: str, workspace_dir: Path):
    """Initialize a kernel controller."""
    self.id = id
    self.name = name
    self.kernel_type = kernel_type
    self.session_id = session_id
    self.workspace_dir = workspace_dir
    self.km = None # KernelManager
    self.kc = None # KernelClient
    self.jupyter_kernel_id = None # ID assigned by Jupyter
    self.connection_file = None # Path to connection file
    logger.debug(f"Initialized kernel controller: {id} ({name})")

  @classmethod
  def from_connection_info(cls, connection_info: Dict[str, Any], workspace_dir: Path) -> 'KernelController':
    """Create a controller from existing kernel connection info."""
    controller = cls(
      id=connection_info["kernel_id"],
      name=connection_info["name"],
      kernel_type=connection_info["kernel_type"],
      session_id=connection_info["session_id"],
      workspace_dir=workspace_dir)

    try:
      # Ensure connection file exists
      if "connection_file" not in connection_info or not connection_info["connection_file"]:
        logger.error(f"No connection file provided for kernel {controller.id}")
        return controller

      connection_file = connection_info["connection_file"]
      if not Path(connection_file).exists():
        logger.error(f"Connection file not found for kernel {controller.id}: {connection_file}")
        return controller

      # Try to connect to existing kernel
      controller.connection_file = connection_file
      controller.jupyter_kernel_id = connection_info.get("jupyter_kernel_id")

      # Create kernel manager from connection file with proper timeout
      logger.debug(f"Creating KernelManager with connection file: {connection_file}")
      controller.km = KernelManager(connection_file=connection_file)

      # Check if kernel is alive with timeout
      try:
        is_alive = controller.km.is_alive()
        if not is_alive:
          logger.debug(f"Kernel {controller.id} is not alive according to KernelManager")
          controller.km = None
          return controller
      except Exception as km_error:
        logger.error(f"Error checking if kernel {controller.id} is alive: {km_error}")
        controller.km = None
        return controller

      # Create client
      logger.debug(f"Creating client for kernel {controller.id}")
      controller.kc = controller.km.client()

      # Start channels with proper error handling
      try:
        controller.kc.start_channels()
      except Exception as sc_error:
        logger.error(f"Error starting channels for kernel {controller.id}: {sc_error}")
        controller.kc = None
        controller.km = None
        return controller

      # Wait briefly for kernel with proper error handling
      try:
        logger.debug(f"Waiting for kernel {controller.id} to be ready")
        controller.kc.wait_for_ready(timeout=5)
        logger.info(f"Successfully reconnected to kernel: {controller.id}")
        return controller
      except Exception as wfr_error:
        logger.error(f"Kernel {controller.id} not ready: {wfr_error}")
        controller.shutdown()
        controller.km = None
        controller.kc = None
    except Exception as e:
      logger.error(f"Error reconnecting to kernel {controller.id}: {e}")
      # Clean up resources on error
      if hasattr(controller, 'kc') and controller.kc:
        try:
          controller.kc.stop_channels()
        except:
          pass
        controller.kc = None

      if hasattr(controller, 'km') and controller.km:
        controller.km = None

    return controller

  def start_kernel(self) -> bool:
    """Start the kernel process."""
    try:
      # If kernel is already running, return
      if self.is_alive():
        return True

      # Set working directory and environment
      env = os.environ.copy()
      env['DEVAGENT_SESSION_ID'] = self.session_id
      env['DEVAGENT_KERNEL_ID'] = self.id

      # Create kernel manager and start kernel
      self.km = KernelManager(kernel_name=self.kernel_type)
      self.km.start_kernel(env=env, cwd=str(self.workspace_dir))

      # Save the Jupyter kernel ID and connection file
      self.jupyter_kernel_id = self.km.kernel_id
      self.connection_file = self.km.connection_file

      # Create client and connect
      self.kc = self.km.client()
      self.kc.start_channels()
      self.kc.wait_for_ready(timeout=30)

      logger.info(f"Started kernel {self.id} ({self.name}) of type {self.kernel_type}")
      return True
    except Exception as e:
      logger.error(f"Error starting kernel {self.id}: {e}")
      self.shutdown()
      raise

  def execute(self, code: str) -> ExecutionResult:
    """Execute code in the kernel."""
    if not self.is_alive():
      raise ValueError(f"Kernel {self.id} not alive")

    logger.debug(f"Executing code in kernel {self.id}: {code[:50]}...")

    # Track execution time
    start_time = time.time()

    # Send execution request
    msg_id = self.kc.execute(code)

    # Collect outputs
    outputs = []
    stdout_parts = []
    stderr_parts = []
    error = None

    # Process messages until idle
    while True:
      try:
        msg = self.kc.get_iopub_msg(timeout=1)
        msg_type = msg['msg_type']
        content = msg['content']

        if msg_type == 'stream':
          if content['name'] == 'stdout':
            stdout_parts.append(content['text'])
            outputs.append({'type': 'stream', 'name': 'stdout', 'text': content['text']})
          elif content['name'] == 'stderr':
            stderr_parts.append(content['text'])
            outputs.append({'type': 'stream', 'name': 'stderr', 'text': content['text']})

        elif msg_type == 'execute_result':
          outputs.append({'type': 'execute_result', 'data': content['data']})

        elif msg_type == 'display_data':
          outputs.append({'type': 'display_data', 'data': content['data']})

        elif msg_type == 'error':
          error = "\n".join(content['traceback'])
          outputs.append({'type': 'error', 'ename': content['ename'], 'evalue': content['evalue'], 'traceback': content['traceback']})

        elif msg_type == 'status' and content['execution_state'] == 'idle':
          # Execution completed
          break

      except Empty:
        # No more messages for now, continue waiting
        continue
      except Exception as e:
        logger.error(f"Error processing kernel messages: {e}")
        break

    # Calculate execution time
    execution_time = time.time() - start_time

    # Combine all stdout
    stdout = "".join(stdout_parts)

    # Create the result
    result = ExecutionResult(success=(error is None), stdout=stdout, error=error, outputs=outputs, execution_time=execution_time)

    logger.debug(f"Execution completed in {execution_time:.2f}s: success={result.success}")
    return result

  def interrupt(self) -> bool:
    """Interrupt the kernel's execution."""
    if not self.is_alive():
      logger.warning(f"Cannot interrupt kernel {self.id}: not alive")
      return False

    try:
      logger.info(f"Interrupting kernel {self.id}")
      self.km.interrupt_kernel()
      return True
    except Exception as e:
      logger.error(f"Error interrupting kernel {self.id}: {e}")
      return False

  def restart(self) -> bool:
    """Restart the kernel."""
    if not self.km:
      logger.info(f"Kernel {self.id} not initialized, starting fresh")
      return self.start_kernel()

    try:
      logger.info(f"Restarting kernel {self.id}")
      self.km.restart_kernel()

      # Reconnect client channels
      if self.kc:
        self.kc.stop_channels()
        self.kc.start_channels()
        self.kc.wait_for_ready(timeout=30)

      # Update jupyter kernel ID and connection file
      self.jupyter_kernel_id = self.km.kernel_id
      self.connection_file = self.km.connection_file

      return True
    except Exception as e:
      logger.error(f"Error restarting kernel {self.id}: {e}")
      # Attempt to shut down and start fresh
      self.shutdown()
      return self.start_kernel()

  def shutdown(self) -> bool:
    """Shutdown the kernel."""
    shutdown_success = True

    if self.kc:
      try:
        logger.debug(f"Stopping client channels for kernel {self.id}")
        self.kc.stop_channels()
      except Exception as e:
        logger.error(f"Error stopping channels for kernel {self.id}: {e}")
        shutdown_success = False
      finally:
        self.kc = None

    if self.km:
      try:
        logger.info(f"Shutting down kernel {self.id}")
        self.km.shutdown_kernel(now=True)
      except Exception as e:
        logger.error(f"Error shutting down kernel {self.id}: {e}")
        shutdown_success = False
      finally:
        self.km = None

    return shutdown_success

  def is_alive(self) -> bool:
    """Check if the kernel is alive."""
    return self.km is not None and self.km.is_alive()

  def get_connection_info(self) -> Dict[str, Any]:
    """Get kernel connection information."""
    return {
      "kernel_id": self.id,
      "name": self.name,
      "kernel_type": self.kernel_type,
      "session_id": self.session_id,
      "jupyter_kernel_id": self.jupyter_kernel_id,
      "connection_file": self.connection_file,
      "last_activity": time.time()
    }

  def get_metadata(self) -> Dict[str, Any]:
    """Get kernel metadata."""
    return {
      "id": self.id,
      "name": self.name,
      "kernel_type": self.kernel_type,
      "session_id": self.session_id,
      "alive": self.is_alive(),
      "jupyter_kernel_id": self.jupyter_kernel_id,
      "workspace_dir": str(self.workspace_dir)
    }
