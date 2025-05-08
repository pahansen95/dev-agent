"""
The Dev Agent's API

Provides a clean interface to the ontology graph and kernel management.
"""
from __future__ import annotations
from .ontology import OntologyGraph, Node, Stage
from .interpreter import ServerController, SessionManager
from .core import *
import os, atexit, time

class API(Protocol):

  @classmethod
  def factory(cls, *args, **kwds) -> API:
    ...

class OntologyAPI(API):

  """Python API for ontology graph operations."""

  @staticmethod
  def init() -> OntologyGraph:
    """Create a new, empty ontology graph."""
    return OntologyGraph()

  @staticmethod
  def load(data: dict) -> OntologyGraph:
    """Load an ontology graph from a dict."""
    return OntologyGraph.from_dict(data)

  @staticmethod
  def dump(graph: OntologyGraph) -> dict:
    """Serialize the ontology graph to a dict."""
    return graph.to_dict()

  @staticmethod
  def info(graph: OntologyGraph) -> tuple[int, int]:
    """Return (node_count, edge_count) of the graph."""
    return len(graph), len(graph.query())

  @staticmethod
  def add_node(
    graph: OntologyGraph,
    nid: str,
    label: str,
    kind: str = "concept",
    meta: dict | None = None,
  ) -> None:
    """Add a node to the graph."""
    if meta is None:
      meta = {}
    # Handling for kind should now map to proper Stage enums when appropriate
    if hasattr(Stage, kind.upper()):
      stage = getattr(Stage, kind.upper())
      graph.add_node(Node(nid, label, stage, set(), meta))
    else:
      graph.add_node(Node(nid, label, Stage.INTENT, set(), meta))

  @staticmethod
  def add_edge(graph: OntologyGraph, src: str, rel: str, dst: str) -> None:
    """Add an edge to the graph."""
    graph.add_edge(src, rel, dst)

from .interpreter import ServerController
import os
from pathlib import Path
from typing import Dict, Any, Optional, Union

class InterpreterServerAPI(API):

  """Python API for interpreter server operations."""

  def __init__(self, controller: ServerController):
    """
        Initialize with a ServerController instance.
        
        Parameters
        ----------
        controller : ServerController
            The server controller to use for operations
        """
    self.controller = controller

  @classmethod
  def factory(cls, base_dir: Union[str, Path] = None) -> InterpreterServerAPI:
    """
        Create an InterpreterServerAPI instance with a ServerController.
        
        Parameters
        ----------
        base_dir : Union[str, Path], optional
            Base directory for server files, defaults to current working directory
            
        Returns
        -------
        InterpreterAPI
            An initialized InterpreterAPI instance
        """
    if base_dir is None:
      base_dir = os.getcwd()
    controller = ServerController(pathlib.Path(base_dir))
    return cls(controller)

  def up(self, server_url: Optional[str] = None) -> Dict[str, Any]:
    """
        Start the Jupyter server and return connection information.
        
        Parameters
        ----------
        server_url : Optional[str], optional
            Server URL specification (unix:///path/to/socket.sock or tcp://host:port)
            
        Returns
        -------
        Dict[str, Any]
            Connection information including server URI
            
        Raises
        ------
        RuntimeError
            If server fails to start
        """
    return self.controller.up(server_url)

  def down(self) -> bool:
    """
        Stop the Jupyter server if running.
            
        Returns
        -------
        bool
            True if server was stopped, False if it was not running
        """
    return self.controller.down()

  def status(self) -> Dict[str, Any]:
    """
        Get current Jupyter server status.
            
        Returns
        -------
        Dict[str, Any]
            Status information including:
            - running: bool - Whether server is running
            - connection_info: Dict - Connection details if running
            - pid: int - Process ID if running
            - last_start_time: float - Timestamp of last start
            - last_error: Optional[str] - Last error message
        """
    return self.controller.status()

  def purge(self) -> bool:
    """
        Stop the Jupyter server and remove all state files.
            
        Returns
        -------
        bool
            True if purge was successful
        """
    return self.controller.purge()

class InterpreterAPI(API):

  """
    Main entry point for the DevAgent Interpreter.
    
    This class integrates server and session management, providing a unified
    interface for creating sessions, executing code, and managing the interpreter
    lifecycle.
    """

  def __init__(self, base_dir: Optional[Union[str, Path]] = None):
    """
        Initialize the interpreter API.
        
        Parameters
        ----------
        base_dir : str or Path, optional
            Base directory for interpreter state and sessions
        """

    self.base_dir = pathlib.Path(base_dir or os.getcwd())
    logger.info(f"Initializing InterpreterAPI with base_dir={self.base_dir}")

    # Initialize components
    self.server_controller = ServerController(base_dir)
    self.session_manager = SessionManager(base_dir)
    self.server_running = False

    # Register shutdown handler
    atexit.register(self.shutdown)

  def start(self) -> InterpreterAPI:
    """
        Start the interpreter server.
        
        Returns
        -------
        InterpreterAPI
            Self for method chaining
        """
    if not self.server_running:
      logger.info("Starting interpreter server")
      try:
        # Start the server
        connection_info = self.server_controller.up()
        self.server_running = True
        logger.info(f"Server started with connection info: {connection_info}")
      except Exception as e:
        logger.error(f"Failed to start server: {str(e)}")
        raise RuntimeError(f"Failed to start interpreter server: {str(e)}")
    else:
      logger.debug("Server already running")

    return self

  def ensure_server_running(self) -> None:
    """Ensure the server is running, starting it if needed."""
    if not self.server_running:
      self.start()

  def create_session(self, session_id: str = "main", kernel_name: str = "python3") -> Dict[str, Any]:
    """
        Create a new session.
        
        Parameters
        ----------
        session_id : str, default="main"
            Unique identifier for the session
        kernel_name : str, default="python3"
            Name of the kernel to use
            
        Returns
        -------
        Dict[str, Any]
            Session information
        """
    self.ensure_server_running()

    try:
      logger.info(f"Creating session: {session_id}")
      session = self.session_manager.create_session(session_id, kernel_name)

      return {"id": session.id, "status": "active", "created_at": time.time()}
    except Exception as e:
      logger.error(f"Failed to create session {session_id}: {str(e)}")
      raise RuntimeError(f"Failed to create session: {str(e)}")

  def get_session(self, session_id: str = "main") -> Optional[Dict[str, Any]]:
    """
        Get information about an existing session.
        
        Parameters
        ----------
        session_id : str, default="main"
            Unique identifier for the session
            
        Returns
        -------
        Optional[Dict[str, Any]]
            Session information or None if not found
        """
    session = self.session_manager.get_session(session_id)
    if session:
      return {"id": session.id, "status": "active", "kernel_name": session.kernel.kernel_name if session.kernel else None}
    return None

  def list_sessions(self) -> List[str]:
    """
        List all active session IDs.
        
        Returns
        -------
        List[str]
            List of session IDs
        """
    return self.session_manager.list_sessions()

  def execute(self, code: str, session_id: str = "main") -> Dict[str, Any]:
    """
        Execute code in a session.
        
        Parameters
        ----------
        code : str
            Code to execute
        session_id : str, default="main"
            Session identifier
            
        Returns
        -------
        Dict[str, Any]
            Execution result with stdout and error information
        """
    self.ensure_server_running()

    # Get or create session
    session = self.session_manager.get_session(session_id)
    if not session:
      logger.info(f"Session {session_id} not found, creating new session")
      session = self.session_manager.create_session(session_id)

    # Execute code
    try:
      logger.debug(f"Executing code in session {session_id}")
      stdout, error = session.execute(code)

      result = {"success": error is None, "stdout": stdout, "error": error}
      return result
    except Exception as e:
      logger.error(f"Execution error in session {session_id}: {str(e)}")
      return {"success": False, "stdout": "", "error": f"Internal error: {str(e)}"}

  def interrupt(self, session_id: str = "main") -> bool:
    """
        Interrupt the execution in a session.
        
        Parameters
        ----------
        session_id : str, default="main"
            Session identifier
            
        Returns
        -------
        bool
            True if interrupt succeeded
        """
    session = self.session_manager.get_session(session_id)
    if session:
      return session.interrupt()
    return False

  def restart_session(self, session_id: str = "main") -> bool:
    """
        Restart a session's kernel.
        
        Parameters
        ----------
        session_id : str, default="main"
            Session identifier
            
        Returns
        -------
        bool
            True if restart succeeded
        """
    session = self.session_manager.get_session(session_id)
    if session:
      return session.restart()
    return False

  def close_session(self, session_id: str) -> bool:
    """
        Close a specific session.
        
        Parameters
        ----------
        session_id : str
            Session identifier
            
        Returns
        -------
        bool
            True if session was closed
        """
    return self.session_manager.shutdown_session(session_id)

  def server_status(self) -> Dict[str, Any]:
    """
        Get the current server status.
        
        Returns
        -------
        Dict[str, Any]
            Server status information
        """
    status = self.server_controller.status()
    status['active_sessions'] = len(self.list_sessions())
    return status

  def shutdown(self) -> None:
    """
        Shut down the interpreter completely.
        
        This stops all sessions and the server.
        """
    logger.info("Shutting down interpreter")

    # Shut down sessions first
    try:
      self.session_manager.shutdown()
    except Exception as e:
      logger.error(f"Error shutting down sessions: {str(e)}")

    # Then shut down server
    if self.server_running:
      try:
        self.server_controller.down()
        self.server_running = False
        logger.info("Server stopped")
      except Exception as e:
        logger.error(f"Error shutting down server: {str(e)}")

# Public module surface
__all__ = [
  "OntologyAPI",
  "InterpreterServerAPI",
]
