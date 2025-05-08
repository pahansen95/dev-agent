"""
DevAgent Interpreter Session Management

This module provides the core session functionality for the DevAgent Interpreter,
implementing a computational bridge between agent and project.

Key components:
- KernelController: Manages a Jupyter kernel process and communication
- Session: Represents a persistent computational environment
- SessionManager: Coordinates multiple sessions

These components work together to provide a robust execution environment
for development agents to interact with projects.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Tuple, Any, Union
from pathlib import Path
import os
import json
import time
import logging
from jupyter_client import KernelManager

# Set up logging
logger = logging.getLogger(__name__)

class KernelController:

  """
    Manages a single Jupyter kernel process and handles communication with it.
    
    This class encapsulates the lifecycle of a kernel (start, execute, shutdown)
    and provides a simplified interface for code execution.
    """

  def __init__(self, kernel_name: str = "python3"):
    """
        Initialize a kernel controller.
        
        Parameters
        ----------
        kernel_name : str
            Name of the Jupyter kernel to use (default: "python3")
        """
    self.kernel_name = kernel_name
    self.km = None
    self.kc = None
    logger.debug(f"Initialized KernelController with kernel_name={kernel_name}")

  def start_kernel(self, env: Optional[Dict[str, str]] = None, cwd: Optional[str] = None) -> bool:
    """
        Start the kernel process.
        
        Parameters
        ----------
        env : Dict[str, str], optional
            Environment variables for the kernel
        cwd : str, optional
            Working directory for the kernel
            
        Returns
        -------
        bool
            True if kernel started successfully
        """
    logger.info(f"Starting kernel: {self.kernel_name}")
    try:
      self.km = KernelManager(kernel_name=self.kernel_name)
      self.km.start_kernel(env=env, cwd=cwd)
      self.kc = self.km.client()
      self.kc.start_channels()

      # Wait for kernel to be ready
      logger.debug("Waiting for kernel to be ready...")
      self.kc.wait_for_ready(timeout=60)
      logger.info(f"Kernel started successfully with id: {self.km.kernel_id}")
      return True
    except Exception as e:
      logger.error(f"Error starting kernel: {str(e)}")
      # Clean up if partial initialization
      self.shutdown()
      raise

  def is_alive(self) -> bool:
    """
        Check if the kernel is running.
        
        Returns
        -------
        bool
            True if kernel is alive
        """
    return self.km is not None and self.km.is_alive()

  def execute(self, code: str) -> Tuple[str, Optional[str]]:
    """
        Execute code in the kernel and return stdout and error.
        
        Parameters
        ----------
        code : str
            Code to execute
            
        Returns
        -------
        Tuple[str, Optional[str]]
            (stdout, error) where error is None if execution succeeded
        """
    if not self.is_alive():
      logger.warning("Kernel not alive, starting new kernel")
      self.start_kernel()

    logger.debug(f"Executing code: {code[:50]}...")

    # Send execution request
    msg_id = self.kc.execute(code)

    # Collect outputs
    stdout = []
    error = None

    # Process messages until idle
    while True:
      try:
        msg = self.kc.get_iopub_msg(timeout=1)
        msg_type = msg['msg_type']

        if msg_type == 'stream' and msg['content']['name'] == 'stdout':
          stdout.append(msg['content']['text'])
          logger.debug(f"Stdout: {msg['content']['text'][:50]}...")
        elif msg_type == 'stream' and msg['content']['name'] == 'stderr':
          stdout.append(msg['content']['text'])
          logger.debug(f"Stderr: {msg['content']['text'][:50]}...")
        elif msg_type == 'error':
          error = "\n".join(msg['content']['traceback'])
          logger.warning(f"Execution error: {msg['content']['ename']}")
        elif msg_type == 'status' and msg['content']['execution_state'] == 'idle':
          logger.debug("Execution completed")
          break
      except Exception as e:
        logger.debug(f"Error or timeout getting message: {str(e)}")
        break

    return ("".join(stdout), error)

  def interrupt(self) -> bool:
    """
        Interrupt the kernel's execution.
        
        Returns
        -------
        bool
            True if interrupt succeeded
        """
    if self.km:
      logger.info("Interrupting kernel")
      self.km.interrupt_kernel()
      return True
    return False

  def restart(self) -> bool:
    """
        Restart the kernel.
        
        Returns
        -------
        bool
            True if restart succeeded
        """
    if self.km:
      logger.info("Restarting kernel")
      self.km.restart_kernel()
      return True
    return False

  def shutdown(self) -> None:
    """Clean shutdown of the kernel."""
    logger.info("Shutting down kernel")
    if self.kc:
      logger.debug("Stopping client channels")
      self.kc.stop_channels()
      self.kc = None

    if self.km:
      logger.debug("Shutting down kernel manager")
      self.km.shutdown_kernel(now=True)
      self.km = None

class Session:

  """
    A persistent computational environment for DevAgent.
    
    Sessions maintain state between executions and provide a consistent
    context for development operations.
    """

  def __init__(self, session_id: str, base_dir: Optional[Union[str, Path]] = None):
    """
        Initialize a session.
        
        Parameters
        ----------
        session_id : str
            Unique identifier for the session
        base_dir : str or Path, optional
            Base directory for session storage
        """
    self.id = session_id
    self.base_dir = Path(base_dir or os.getcwd())
    self.kernel = None

    # Create session directory structure
    self.session_dir = self.base_dir / ".devagent" / "sessions" / session_id
    self.session_dir.mkdir(parents=True, exist_ok=True)
    self.state_file = self.session_dir / "state.json"

    logger.info(f"Initialized session: {session_id} in {self.session_dir}")

  def initialize(self, kernel_name: str = "python3") -> Session:
    """
        Initialize the session with a kernel.
        
        Parameters
        ----------
        kernel_name : str
            Name of the kernel to use
            
        Returns
        -------
        Session
            Self for method chaining
        """
    logger.info(f"Initializing session: {self.id}")
    self.kernel = KernelController(kernel_name=kernel_name)

    # Set working directory to session dir by default
    cwd = str(self.session_dir)

    # Initialize with environment variables
    env = os.environ.copy()
    env['DEVAGENT_SESSION_ID'] = self.id
    env['DEVAGENT_SESSION_DIR'] = cwd

    # Start the kernel
    self.kernel.start_kernel(env=env, cwd=cwd)

    # Initialize state tracking
    self._save_state()
    return self

  def execute(self, code: str) -> Tuple[str, Optional[str]]:
    """
        Execute code in this session.
        
        Parameters
        ----------
        code : str
            Code to execute
            
        Returns
        -------
        Tuple[str, Optional[str]]
            (stdout, error) where error is None if execution succeeded
        """
    if not self.kernel:
      logger.info(f"Session {self.id} has no kernel, initializing")
      self.initialize()

    logger.debug(f"Session {self.id} executing code")
    result = self.kernel.execute(code)

    # Update last activity time
    self._save_state()

    return result

  def interrupt(self) -> bool:
    """
        Interrupt the current execution.
        
        Returns
        -------
        bool
            True if interrupt succeeded
        """
    if self.kernel:
      return self.kernel.interrupt()
    return False

  def restart(self) -> bool:
    """
        Restart the session's kernel.
        
        Returns
        -------
        bool
            True if restart succeeded
        """
    if self.kernel:
      return self.kernel.restart()
    return False

  def _save_state(self) -> None:
    """Save session state to disk."""
    logger.debug(f"Saving state for session: {self.id}")
    state = {"id": self.id, "last_activity": time.time(), "kernel_name": self.kernel.kernel_name if self.kernel else None}

    with open(self.state_file, "w") as f:
      json.dump(state, f)

  def _load_state(self) -> Dict[str, Any]:
    """
        Load session state from disk.
        
        Returns
        -------
        Dict[str, Any]
            Session state dictionary
        """
    if self.state_file.exists():
      logger.debug(f"Loading state for session: {self.id}")
      with open(self.state_file, "r") as f:
        return json.load(f)
    return {"id": self.id}

  def shutdown(self) -> None:
    """Clean up the session."""
    logger.info(f"Shutting down session: {self.id}")
    if self.kernel:
      self.kernel.shutdown()
      self.kernel = None
    self._save_state()

class SessionManager:

  """
    Manages multiple interpreter sessions.
    
    Provides functionality to create, retrieve, and manage sessions,
    acting as the main entry point for session operations.
    """

  def __init__(self, base_dir: Optional[Union[str, Path]] = None):
    """
        Initialize the session manager.
        
        Parameters
        ----------
        base_dir : str or Path, optional
            Base directory for session storage
        """
    self.base_dir = Path(base_dir or os.getcwd())
    self.sessions: Dict[str, Session] = {}
    logger.info(f"Initialized SessionManager with base_dir={self.base_dir}")

  def create_session(self, session_id: str, kernel_name: str = "python3") -> Session:
    """
        Create a new session or return existing one.
        
        Parameters
        ----------
        session_id : str
            Unique identifier for the session
        kernel_name : str
            Name of the kernel to use
            
        Returns
        -------
        Session
            The created or existing session
        """
    logger.info(f"Creating session: {session_id}")
    if session_id in self.sessions:
      logger.debug(f"Session {session_id} already exists")
      return self.sessions[session_id]

    session = Session(session_id, self.base_dir).initialize(kernel_name)
    self.sessions[session_id] = session
    return session

  def get_session(self, session_id: str) -> Optional[Session]:
    """
        Get an existing session.
        
        Parameters
        ----------
        session_id : str
            Unique identifier for the session
            
        Returns
        -------
        Optional[Session]
            The session if it exists, None otherwise
        """
    if session_id in self.sessions:
      logger.debug(f"Retrieved existing session: {session_id}")
      return self.sessions[session_id]

    # Check if state exists on disk
    state_file = self.base_dir / ".devagent" / "sessions" / session_id / "state.json"
    if state_file.exists():
      logger.info(f"Found session state on disk for {session_id}, reinitializing")
      # Reconnect to existing session
      session = Session(session_id, self.base_dir)
      state = session._load_state()
      kernel_name = state.get("kernel_name", "python3")
      session.initialize(kernel_name)
      self.sessions[session_id] = session
      return session

    logger.debug(f"Session not found: {session_id}")
    return None

  def list_sessions(self) -> List[str]:
    """
        List all active session IDs.
        
        Returns
        -------
        List[str]
            List of session IDs
        """
    return list(self.sessions.keys())

  def shutdown_session(self, session_id: str) -> bool:
    """
        Shut down a specific session.
        
        Parameters
        ----------
        session_id : str
            Unique identifier for the session
            
        Returns
        -------
        bool
            True if session was shut down
        """
    if session_id in self.sessions:
      logger.info(f"Shutting down session: {session_id}")
      self.sessions[session_id].shutdown()
      del self.sessions[session_id]
      return True
    return False

  def shutdown(self) -> None:
    """Shut down all sessions."""
    logger.info("Shutting down all sessions")
    for session_id in list(self.sessions.keys()):
      self.shutdown_session(session_id)
    self.sessions.clear()
